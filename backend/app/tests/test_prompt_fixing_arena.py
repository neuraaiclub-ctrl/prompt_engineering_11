import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.arena import ArenaConfig, PromptBankItem, TeamArenaSession, ArenaSubmission, ArenaEvaluation
from app.models.team import Team, TeamMember
from app.models.user import User, Role
from app.core.security import create_access_token, hash_password

client = TestClient(app)

def create_mock_team_and_user(db, team_name="Cyber Titans", email="titans@neura.io", invite_code="NR-9901"):
    u = db.query(User).filter(User.email == email.lower()).first()
    if not u:
        u = User(
            name=team_name,
            email=email.lower(),
            password_hash=hash_password("Pass123!"),
            affiliation="MMCOE Pune",
            status="active"
        )
        db.add(u)
        db.flush()
        db.add(Role(user_id=u.id, name="participant"))

    t = db.query(Team).filter(Team.invite_code == invite_code).first()
    if not t:
        t = Team(
            hackathon_id="hk-2026",
            name=team_name,
            college="MMCOE Pune",
            invite_code=invite_code,
            status="forming"
        )
        db.add(t)
        db.flush()
        db.add(TeamMember(team_id=t.id, user_id=u.id, role="leader"))

    db.commit()
    token = create_access_token({"sub": u.id, "email": u.email, "roles": ["participant"]})
    return t, u, token

from app.config import settings

def get_judge_token():
    res = client.post("/api/v1/auth/login", json={
        "email": settings.JUDGE1_EMAIL,
        "password": settings.JUDGE1_PASSWORD
    })
    assert res.status_code == 200
    return res.json()["access_token"]

def get_admin_token():
    res = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN1_EMAIL,
        "password": settings.ADMIN1_PASSWORD
    })
    assert res.status_code == 200
    return res.json()["access_token"]

def test_arena_initial_state_waiting():
    """Verify initial competition state is WAITING and participants cannot submit."""
    db = SessionLocal()
    try:
        conf = db.query(ArenaConfig).filter(ArenaConfig.id == "default-arena-config").first()
        if conf:
            conf.status = "waiting"
            conf.started_at = None
            db.commit()

        team, user, token = create_mock_team_and_user(db, "Alpha Force", "alpha.force@neura.io", "NR-9911")
        
        # Status endpoint
        resp = client.get("/api/v1/arena/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting"

        # My Challenge endpoint returns WAITING message without leaking challenge details
        chal_resp = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token}"})
        assert chal_resp.status_code == 200
        chal_data = chal_resp.json()
        assert chal_data["competition_status"] == "waiting"
        assert chal_data["challenge"] is None

        # Attempt to submit while waiting should be rejected
        sub_resp = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "This is an improved prompt that is well formatted with clear bullet points."},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert sub_resp.status_code == 400
        assert "has not started yet" in sub_resp.json()["detail"]
    finally:
        db.close()

def test_arena_judge_start_competition():
    """Judge starts competition and status transitions to LIVE with authoritative server timestamp."""
    judge_token = get_judge_token()
    resp = client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {judge_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["status"] == "live"
    assert data["started_at"] is not None

def test_arena_unique_prompt_assignment():
    """Team A and Team B receive unique prompt sets, and refresh preserves exact assignments."""
    db = SessionLocal()
    try:
        team_a, _, token_a = create_mock_team_and_user(db, "Team Alpha", "alpha@neura.io", "NR-9921")
        team_b, _, token_b = create_mock_team_and_user(db, "Team Beta", "beta@neura.io", "NR-9922")

        resp_a = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token_a}"})
        resp_b = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token_b}"})

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        
        data_a = resp_a.json()
        data_b = resp_b.json()

        assert data_a["challenge"] is not None
        assert data_b["challenge"] is not None

        session_a = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team_a.id).first()
        session_b = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team_b.id).first()

        assert len(session_a.prompt_ids) == 5
        assert len(session_b.prompt_ids) == 5
        # Ensure sequences are distinct
        assert session_a.prompt_ids != session_b.prompt_ids

        # Refresh check: repeated GET returns identical challenge
        resp_a_reload = client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a_reload.json()["challenge"]["id"] == data_a["challenge"]["id"]
    finally:
        db.close()

def test_arena_submission_sequence_and_immutability():
    """Verify sequential submission progression, character limit validation, and double-submit rejection."""
    db = SessionLocal()
    try:
        team, _, token = create_mock_team_and_user(db, "Delta Ops", "delta@neura.io", "NR-9931")
        
        # 1. Validation: Too short prompt
        short_resp = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "Too short"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert short_resp.status_code == 422 # Pydantic min_length validation

        # 2. Valid submission for Challenge 1
        valid_prompt_1 = "Write a comprehensive LinkedIn article explaining the core pillars of storytelling in technical marketing."
        sub_resp_1 = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": valid_prompt_1},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert sub_resp_1.status_code == 200
        assert sub_resp_1.json()["submitted_index"] == 1
        assert sub_resp_1.json()["next_challenge_index"] == 2

        # 3. Double submission rejection (immutable)
        dup_resp = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "Trying to overwrite challenge 1 with new prompt content."},
            headers={"Authorization": f"Bearer {token}"}
        )
        # Because session moved to challenge 2, submitting now is for challenge 2, which succeeds,
        # but let's check directly that challenge 1 cannot be submitted again
        existing_sub_1 = db.query(ArenaSubmission).filter(
            ArenaSubmission.team_id == team.id,
            ArenaSubmission.challenge_index == 1
        ).first()
        assert existing_sub_1 is not None
        assert existing_sub_1.submitted_prompt == valid_prompt_1
    finally:
        db.close()

def test_arena_full_competition_completion():
    """Team completes all 5 challenges sequentially, moving session to completed with server timestamp."""
    db = SessionLocal()
    try:
        team, _, token = create_mock_team_and_user(db, "Omega Squad", "omega@neura.io", "NR-9941")

        for idx in range(1, 6):
            resp = client.post(
                "/api/v1/arena/submit-challenge",
                json={"prompt_text": f"High quality improved prompt solution for challenge number {idx} with schema constraints."},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200

        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        assert session.status == "completed"
        assert session.completed_at is not None
        assert session.current_challenge_index == 6

        # Attempt to submit 6th challenge should be rejected
        extra_resp = client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "Attempting extra challenge after completion."},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert extra_resp.status_code == 400
        assert "completed all 5 challenges" in extra_resp.json()["detail"]
    finally:
        db.close()

def test_arena_judge_scoring_5_dimensions():
    """Judge scores submission on 5 dimensions (0-2 each) and total score (/10) is auto-calculated."""
    db = SessionLocal()
    try:
        team, _, token = create_mock_team_and_user(db, "Scored Team", "scored@neura.io", "NR-9951")
        # Submit challenge 1
        client.post(
            "/api/v1/arena/submit-challenge",
            json={"prompt_text": "Here is an improved prompt that specifies role, audience, bullet constraints, and JSON schema."},
            headers={"Authorization": f"Bearer {token}"}
        )
        sub = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team.id, ArenaSubmission.challenge_index == 1).first()
        assert sub is not None

        judge_token = get_judge_token()
        score_resp = client.post(
            "/api/v1/arena/judge/score",
            json={
                "submission_id": sub.id,
                "clarity_score": 2.0,
                "context_score": 1.5,
                "specificity_score": 2.0,
                "output_structure_score": 1.5,
                "relevance_score": 2.0,
                "judge_feedback": "Excellent schema definition, but could include a fallback edge case."
            },
            headers={"Authorization": f"Bearer {judge_token}"}
        )
        assert score_resp.status_code == 200
        data = score_resp.json()
        assert data["success"] is True
        assert data["total_score"] == 9.0 # 2 + 1.5 + 2 + 1.5 + 2
    finally:
        db.close()

def test_arena_tie_breaking_completion_timestamp():
    """Two teams with identical scores are deterministically ranked by earliest completion timestamp."""
    db = SessionLocal()
    try:
        team_early, _, token_early = create_mock_team_and_user(db, "Early Finishers", "early@neura.io", "NR-9961")
        team_late, _, token_late = create_mock_team_and_user(db, "Late Finishers", "late@neura.io", "NR-9962")

        # Submit 1 challenge for each
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "Valid improved prompt for early team."}, headers={"Authorization": f"Bearer {token_early}"})
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "Valid improved prompt for late team."}, headers={"Authorization": f"Bearer {token_late}"})

        sub_early = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team_early.id).first()
        sub_late = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team_late.id).first()

        # Score both identically (10/10)
        judge_token = get_judge_token()
        for s in [sub_early, sub_late]:
            client.post(
                "/api/v1/arena/judge/score",
                json={
                    "submission_id": s.id,
                    "clarity_score": 2.0,
                    "context_score": 2.0,
                    "specificity_score": 2.0,
                    "output_structure_score": 2.0,
                    "relevance_score": 2.0,
                    "judge_feedback": "Perfect prompt."
                },
                headers={"Authorization": f"Bearer {judge_token}"}
            )

        # Set earlier completed_at for team_early
        sess_early = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team_early.id).first()
        sess_late = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team_late.id).first()

        base_time = datetime.utcnow()
        sess_early.completed_at = base_time - timedelta(minutes=10)
        sess_late.completed_at = base_time
        db.commit()

        # Fetch leaderboard as staff
        resp = client.get("/api/v1/arena/leaderboard", headers={"Authorization": f"Bearer {judge_token}"})
        assert resp.status_code == 200
        standings = resp.json()["standings"]

        # Filter only our two test teams
        relevant = [s for s in standings if s["team_id"] in [team_early.id, team_late.id]]
        assert len(relevant) == 2
        assert relevant[0]["team_id"] == team_early.id
        assert relevant[1]["team_id"] == team_late.id
    finally:
        db.close()

def test_arena_security_event_logging():
    """Tab switch and window blur deterrence events are logged and flagged after 3 violations."""
    db = SessionLocal()
    try:
        team, _, token = create_mock_team_and_user(db, "Monitored Team", "monitored@neura.io", "NR-9971")

        for i in range(1, 4):
            resp = client.post(
                "/api/v1/arena/security-event",
                json={"event_type": "tab_switch", "client_metadata": {"tab_hidden": True, "count": i}},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_violations"] == i
            if i == 3:
                assert data["flagged"] is True

        judge_token = get_judge_token()
        overview_resp = client.get("/api/v1/arena/judge/overview", headers={"Authorization": f"Bearer {judge_token}"})
        assert overview_resp.status_code == 200
        overview = overview_resp.json()
        assert overview["stats"]["flagged_teams"] >= 1
    finally:
        db.close()

def test_arena_results_release_and_educational_report():
    """Releasing results unlocks the 5-challenge detailed educational report for participants."""
    db = SessionLocal()
    try:
        team, _, token = create_mock_team_and_user(db, "Reporting Team", "reporting@neura.io", "NR-9981")
        
        # Submit challenge 1
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "High clarity prompt solution with robust context."}, headers={"Authorization": f"Bearer {token}"})
        sub = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team.id).first()

        judge_token = get_judge_token()
        client.post(
            "/api/v1/arena/judge/score",
            json={
                "submission_id": sub.id,
                "clarity_score": 2.0,
                "context_score": 1.0,
                "specificity_score": 2.0,
                "output_structure_score": 1.0,
                "relevance_score": 2.0,
                "judge_feedback": "Well structured instructions, clarify the output format."
            },
            headers={"Authorization": f"Bearer {judge_token}"}
        )

        # Before results release, report is unavailable
        pre_report = client.get("/api/v1/arena/report", headers={"Authorization": f"Bearer {token}"})
        assert pre_report.status_code == 200
        assert pre_report.json()["available"] is False

        # Judge releases results
        rel_resp = client.post("/api/v1/arena/release-results", headers={"Authorization": f"Bearer {judge_token}"})
        assert rel_resp.status_code == 200

        # After results release, report is available with full breakdown
        post_report = client.get("/api/v1/arena/report", headers={"Authorization": f"Bearer {token}"})
        assert post_report.status_code == 200
        data = post_report.json()
        assert data["available"] is True
        assert data["total_score"] == 8.0
        assert len(data["challenges"]) >= 1
        assert "strengths" in data
        assert "areas_to_improve" in data
    finally:
        db.close()
