import time
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.team import Team, TeamMember
from app.models.arena import (
    ArenaConfig,
    PromptBankItem,
    TeamArenaSession,
    ArenaSubmission,
    ArenaEvaluation,
    ArenaSecurityEvent
)
from app.models.audit import AuditLog
from app.core.security import hash_password

from app.config import settings
from app.core.security import create_access_token

client = TestClient(app)

def get_admin_token():
    res = client.post("/api/v1/auth/login", json={"email": settings.ADMIN1_EMAIL, "password": settings.ADMIN1_PASSWORD})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_judge_token():
    res = client.post("/api/v1/auth/login", json={"email": settings.JUDGE1_EMAIL, "password": settings.JUDGE1_PASSWORD})
    assert res.status_code == 200
    return res.json()["access_token"]

def create_competition_team(db, team_name, email, invite_code, members):
    team = Team(
        hackathon_id="hk-2026",
        name=team_name,
        college="Tech Institute",
        invite_code=invite_code,
        status="locked"
    )
    db.add(team)
    db.flush()

    user = User(
        name=team_name,
        email=email.lower(),
        password_hash=hash_password("Pass12345!"),
        status="active"
    )
    db.add(user)
    db.flush()

    db.add(Role(user_id=user.id, name="participant"))
    db.add(TeamMember(team_id=team.id, user_id=user.id, role="leader"))
    db.commit()

    token = create_access_token({"sub": user.id, "email": user.email, "roles": ["participant"]})
    return team, user, token

def test_two_member_team_registration_and_uniqueness():
    """Admins can register 2-member teams with unique team names and distinct members."""
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Valid 2-member team registration
    t1_res = client.post(
        "/api/v1/teams/admin/register",
        json={
            "team_name": "Quantum Duo",
            "college": "IIT Bombay",
            "members": ["Arjun Rao", "Neha Sharma"]
        },
        headers=headers
    )
    assert t1_res.status_code == 201
    t1_data = t1_res.json()
    assert t1_data["team"]["name"] == "Quantum Duo"
    assert len(t1_data["team"]["members"]) == 2

    # 2. Duplicate team name rejection
    dup_name_res = client.post(
        "/api/v1/teams/admin/register",
        json={
            "team_name": "quantum duo",
            "college": "Another College",
            "members": ["Pooja V.", "Karan S."]
        },
        headers=headers
    )
    assert dup_name_res.status_code == 409

    # 3. Duplicate member within same team rejection
    same_member_res = client.post(
        "/api/v1/teams/admin/register",
        json={
            "team_name": "Cloned Minds",
            "college": "BITS Pilani",
            "members": ["Rohan Sen", "rohan sen"]
        },
        headers=headers
    )
    assert same_member_res.status_code == 422

    # 4. Member already in another team rejection
    cross_member_res = client.post(
        "/api/v1/teams/admin/register",
        json={
            "team_name": "Infiltrators",
            "college": "IIT Delhi",
            "members": ["Arjun Rao", "Divya Pillai"] # Arjun is already in Quantum Duo
        },
        headers=headers
    )
    assert cross_member_res.status_code == 409

def test_multi_team_unique_question_sets():
    """Multiple concurrent teams receive uniquely assigned 5-question sets with persistent reload state."""
    db = SessionLocal()
    try:
        # Start competition
        judge_token = get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        assigned_sequences = []
        tokens = []

        for i in range(5):
            t_name = f"Competitive Team {i+1}_{int(time.time()*1000)}"
            t_email = f"team_{i+1}_{int(time.time()*1000)}@neura.io"
            code = f"CD-{i+1}0"
            team, user, token = create_competition_team(db, t_name, t_email, code, ["Member A", "Member B"])
            tokens.append(token)

            resp = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["challenge"] is not None
            assert data["current_challenge_index"] == 1

            session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
            assert len(session.prompt_ids) == 5
            assigned_sequences.append(tuple(session.prompt_ids))

        # Guarantee server-side uniqueness across all teams
        assert len(set(assigned_sequences)) == len(assigned_sequences)

        # Refresh check: participant reloading gets identical current challenge
        reload_resp = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {tokens[0]}"})
        assert reload_resp.status_code == 200
        assert reload_resp.json()["challenge"]["id"] == assigned_sequences[0][0]
    finally:
        db.close()

def test_participant_serializer_never_leaks_diagnostic_info():
    """Participant challenge response must strictly omit internal diagnostic reasons, test keys, or improvements."""
    db = SessionLocal()
    try:
        t_name = f"Safe Participant_{int(time.time()*1000)}"
        t_email = f"safe_{int(time.time()*1000)}@neura.io"
        team, user, token = create_competition_team(db, t_name, t_email, "SF-8812", ["M1", "M2"])

        judge_token = get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        resp = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        chal = resp.json()["challenge"]

        # Public fields
        assert "original_bad_prompt" in chal
        assert "bad_output_evidence" in chal
        assert "title" in chal

        # Protected diagnostic fields that MUST NOT leak to participants
        assert "flawed_reasons" not in chal
        assert "expected_improvements" not in chal
        assert "hidden_tests" not in chal
        assert "expected_answer" not in chal
    finally:
        db.close()

def test_five_characteristic_scoring_model_0_10_20():
    """Submitted prompts are evaluated on Clarity, Specificity, Context, Output Format, Constraints (0/10/20 each = max 100)."""
    db = SessionLocal()
    try:
        t_name = f"Rubric Team_{int(time.time()*1000)}"
        t_email = f"rubric_{int(time.time()*1000)}@neura.io"
        team, user, token = create_competition_team(db, t_name, t_email, "RB-4411", ["M1", "M2"])

        judge_token = get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        # Submit challenge 1
        prompt = "You are a senior data engineer. Write a Python function with type hints and doctests that parses customer logs."
        sub_resp = client.post("/api/v1/arena/submit-challenge", json={"prompt_text": prompt}, headers={"Authorization": f"Bearer {token}"})
        assert sub_resp.status_code == 200

        sub = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team.id, ArenaSubmission.challenge_index == 1).first()

        # Judge scores submission using official 0/10/20 rubric:
        # Clarity: 20, Specificity: 20, Context: 10, Output Format: 20, Constraints: 10 => 80/100
        score_resp = client.post(
            "/api/v1/arena/judge/score",
            json={
                "submission_id": sub.id,
                "clarity_score": 20.0,
                "specificity_score": 20.0,
                "context_score": 10.0,
                "output_format_score": 20.0,
                "constraints_score": 10.0,
                "judge_feedback": "Exceptional clarity and schema definition."
            },
            headers={"Authorization": f"Bearer {judge_token}"}
        )
        assert score_resp.status_code == 200
        data = score_resp.json()
        assert data["success"] is True
        assert data["total_score"] == 80.0

        # Check participant score dashboard endpoint
        dash_resp = client.get("/api/v1/arena/my-results", headers={"Authorization": f"Bearer {token}"})
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["total_score"] == 80.0
        assert dash["average_score"] == 16.0 # 80 / 5
        assert len(dash["challenges"]) == 1
        assert dash["challenges"][0]["characteristics"]["clarity"] == 20.0
        assert dash["challenges"][0]["characteristics"]["specificity"] == 20.0
        assert dash["challenges"][0]["characteristics"]["output_format"] == 20.0
    finally:
        db.close()

def test_server_side_team_elimination_and_submission_rejection():
    """Eliminated teams are barred from further submissions, marked eliminated in session, and audited."""
    db = SessionLocal()
    try:
        t_name = f"Disqualified Team_{int(time.time()*1000)}"
        t_email = f"disq_{int(time.time()*1000)}@neura.io"
        team, user, token = create_competition_team(db, t_name, t_email, "DQ-1212", ["M1", "M2"])

        judge_token = get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        # Submit challenge 1 before elimination
        sub_resp = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "Valid prompt before getting flagged for unauthorized material."},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert sub_resp.status_code == 200

        # Judge eliminates team for academic integrity breach
        elim_resp = client.post(
            "/api/v1/arena/judge/eliminate",
            json={
                "team_id": team.id,
                "reason": "Repeated unauthorized multi-tab switching and unauthorized proctoring breach."
            },
            headers={"Authorization": f"Bearer {judge_token}"}
        )
        assert elim_resp.status_code == 200
        assert elim_resp.json()["status"] == "eliminated"

        # Verify audit log
        audit = db.query(AuditLog).filter(
            AuditLog.action == "arena.team_eliminated",
            AuditLog.target_id == team.id
        ).first()
        assert audit is not None
        assert "proctoring" in audit.audit_metadata["reason"]

        # Attempt to submit challenge 2 must be rejected with 403 Forbidden
        blocked_resp = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "Trying to submit challenge 2 after elimination."},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert blocked_resp.status_code == 403
        assert "eliminated" in blocked_resp.json()["detail"].lower()

        # Challenge retrieval returns elimination notice
        chal_resp = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token}"})
        assert chal_resp.status_code == 200
        assert chal_resp.json()["is_eliminated"] is True
    finally:
        db.close()

def test_deterministic_tie_breaking_by_earliest_completion_timestamp():
    """Ties in average score are deterministically broken by earliest final submission timestamp."""
    db = SessionLocal()
    try:
        judge_token = get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        # Team A (Early Finishers)
        team_a, _, token_a = create_competition_team(db, f"Early Alpha_{int(time.time()*1000)}", f"early_{int(time.time()*1000)}@neura.io", "EA-1010", ["A1", "A2"])
        # Team B (Late Finishers)
        team_b, _, token_b = create_competition_team(db, f"Late Beta_{int(time.time()*1000)}", f"late_{int(time.time()*1000)}@neura.io", "LB-2020", ["B1", "B2"])

        # Submit 1 challenge for both
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "Valid prompt for early team."}, headers={"Authorization": f"Bearer {token_a}"})
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "Valid prompt for late team."}, headers={"Authorization": f"Bearer {token_b}"})

        sub_a = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team_a.id).first()
        sub_b = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team_b.id).first()

        # Score both identically: 100/100
        for s in [sub_a, sub_b]:
            client.post(
                "/api/v1/arena/judge/score",
                json={
                    "submission_id": s.id,
                    "clarity_score": 20.0,
                    "specificity_score": 20.0,
                    "context_score": 20.0,
                    "output_format_score": 20.0,
                    "constraints_score": 20.0
                },
                headers={"Authorization": f"Bearer {judge_token}"}
            )

        # Explicitly set server completion timestamp
        now = datetime.utcnow()
        session_a = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team_a.id).first()
        session_b = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team_b.id).first()

        session_a.completed_at = now - timedelta(minutes=10) # 10 mins earlier
        session_b.completed_at = now # later
        db.commit()

        # Release results
        client.post("/api/v1/arena/release-results", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        lb_resp = client.get("/api/v1/arena/leaderboard", headers={"Authorization": f"Bearer {judge_token}"})
        assert lb_resp.status_code == 200
        standings = lb_resp.json()["standings"]

        standing_a = next(s for s in standings if s["team_id"] == team_a.id)
        standing_b = next(s for s in standings if s["team_id"] == team_b.id)

        # Both have identical score
        assert standing_a["total_score"] == standing_b["total_score"]
        # Team A MUST have higher rank due to earlier timestamp
        assert standing_a["rank"] < standing_b["rank"]
    finally:
        db.close()

def test_eliminated_team_excluded_from_podium():
    """Eliminated team cannot occupy Rank 1, 2, or 3 even if its raw score was higher."""
    db = SessionLocal()
    try:
        judge_token = get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})

        # Team High (Eliminated)
        team_high, _, token_high = create_competition_team(db, f"High Cheater_{int(time.time()*1000)}", f"high_{int(time.time()*1000)}@neura.io", "HC-9090", ["H1", "H2"])
        # Team Honest (Active)
        team_honest, _, token_honest = create_competition_team(db, f"Honest Victor_{int(time.time()*1000)}", f"honest_{int(time.time()*1000)}@neura.io", "HV-8080", ["V1", "V2"])

        # Submit challenges
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "High score prompt submission."}, headers={"Authorization": f"Bearer {token_high}"})
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "Honest prompt submission."}, headers={"Authorization": f"Bearer {token_honest}"})

        sub_high = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team_high.id).first()
        sub_honest = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team_honest.id).first()

        # Score High Team: 100/100, Honest Team: 80/100
        client.post("/api/v1/arena/judge/score", json={"submission_id": sub_high.id, "clarity_score": 20.0, "specificity_score": 20.0, "context_score": 20.0, "output_format_score": 20.0, "constraints_score": 20.0}, headers={"Authorization": f"Bearer {judge_token}"})
        client.post("/api/v1/arena/judge/score", json={"submission_id": sub_honest.id, "clarity_score": 20.0, "specificity_score": 20.0, "context_score": 10.0, "output_format_score": 20.0, "constraints_score": 10.0}, headers={"Authorization": f"Bearer {judge_token}"})

        # Eliminate High Team
        client.post("/api/v1/arena/judge/eliminate", json={"team_id": team_high.id, "reason": "Cheating confirmed."}, headers={"Authorization": f"Bearer {judge_token}"})

        # Check leaderboard
        lb_resp = client.get("/api/v1/arena/leaderboard", headers={"Authorization": f"Bearer {judge_token}"})
        standings = lb_resp.json()["standings"]

        standing_high = next(s for s in standings if s["team_id"] == team_high.id)
        standing_honest = next(s for s in standings if s["team_id"] == team_honest.id)

        assert standing_high["is_eliminated"] is True
        assert standing_high["rank"] is None
        assert standing_high["podium"] is None

        assert standing_honest["is_eliminated"] is False
        assert standing_honest["rank"] is not None
    finally:
        db.close()

def test_anti_cheat_event_logging_comprehensive():
    """Anti-cheat proctoring events are captured, stored in DB, and aggregated in Judge Overview."""
    db = SessionLocal()
    try:
        t_name = f"Proctored Team_{int(time.time()*1000)}"
        t_email = f"proctored_{int(time.time()*1000)}@neura.io"
        team, user, token = create_competition_team(db, t_name, t_email, "PC-3322", ["P1", "P2"])

        events_to_test = ["TAB_SWITCH", "WINDOW_BLUR", "FULLSCREEN_EXIT", "COPY_ATTEMPT", "PASTE_ATTEMPT"]

        for ev in events_to_test:
            res = client.post(
                "/api/v1/arena/security-event",
                json={
                    "event_type": ev,
                    "client_metadata": {"browser": "Chrome", "screen": "1920x1080"}
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert res.status_code == 200

        # Verify DB records
        logged = db.query(ArenaSecurityEvent).filter(ArenaSecurityEvent.team_id == team.id).all()
        types = [l.event_type for l in logged]
        for ev in events_to_test:
            assert ev in types

        # Check Judge Overview reflects flagged team
        judge_token = get_judge_token()
        overview = client.get("/api/v1/arena/judge/overview", headers={"Authorization": f"Bearer {judge_token}"}).json()
        flagged_events = [e for e in overview["security_events"] if e["team_name"] == team.name]
        assert len(flagged_events) >= 5
    finally:
        db.close()
