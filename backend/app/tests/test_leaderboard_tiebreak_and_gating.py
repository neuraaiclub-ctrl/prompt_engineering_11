import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.hackathon import Hackathon, Round
from app.models.challenge import Challenge, PromptCase, Constraint
from app.models.team import Team, TeamMember
from app.models.execution import Submission
from app.models.evaluation import Evaluation
from app.models.score import Score
from app.models.leaderboard import LeaderboardEntry
from app.core.scoring import recompute_leaderboard

client = TestClient(app)

def test_leaderboard_gating_and_deterministic_tiebreak():
    """
    SRS Section 10, FR-087-091, FR-097, FR-101:
    - Results gated behind admin publish (403 for participant until published).
    - Deterministic 4-step tie-breaking:
        1. Total score DESC
        2. Round 2 % passed DESC
        3. Round 1 human score DESC
        4. Earlier final submission timestamp ASC
    - CSV and JSON exports.
    - Recomputation latency verification.
    """
    from app.tests.conftest import create_test_user
    create_test_user("admin_lb@tiebreak.com", "Password123!", name="Admin LB", roles=["admin"])
    p_user = create_test_user("part_lb@tiebreak.com", "Password123!", name="Part LB", roles=["participant"])
    p_user_id = p_user.id

    admin_token = client.post("/api/v1/auth/login", json={"email": "admin_lb@tiebreak.com", "password": "Password123!"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    part_token = client.post("/api/v1/auth/login", json={"email": "part_lb@tiebreak.com", "password": "Password123!"}).json()["access_token"]
    part_headers = {"Authorization": f"Bearer {part_token}"}

    # 2. Setup Hackathon, Round 1 and Round 2
    hk_res = client.post("/api/v1/hackathons", json={"title": "Tiebreak Hackathon"}, headers=admin_headers)
    hk_id = hk_res.json()["id"]

    rnd1_res = client.post(f"/api/v1/hackathons/{hk_id}/rounds", json={
        "round_number": 1, "title": "Round 1", "type": "round1_fix_the_prompt", "duration_minutes": 30
    }, headers=admin_headers)
    r1_id = rnd1_res.json()["id"]

    rnd2_res = client.post(f"/api/v1/hackathons/{hk_id}/rounds", json={
        "round_number": 2, "title": "Round 2", "type": "round2_constraint_challenge", "duration_minutes": 30
    }, headers=admin_headers)
    r2_id = rnd2_res.json()["id"]

    # Challenges
    c1 = client.post(f"/api/v1/rounds/{r1_id}/prompt-cases", json={
        "title": "Case 1", "original_prompt": "orig", "bad_output": "bad", "broken_reason": "vague"
    }, headers=admin_headers).json()["challenge_id"]

    c2 = client.post(f"/api/v1/rounds/{r2_id}/constraint-challenges", json={
        "title": "Constraint 1", "constraint_type": "valid_json_always", "task_description": "task"
    }, headers=admin_headers).json()["id"]

    # 3. Create 4 teams with specifically constructed tie-break scores
    # Team Alpha: Total = 30 (Outright winner by Tier 1)
    # Team Beta: Total = 25, R2 pass rate = 1.0 (Wins Tier 2 tie against Gamma & Delta)
    # Team Gamma: Total = 25, R2 pass rate = 0.5, R1 score = 15 (Wins Tier 3 tie against Delta)
    # Team Delta: Total = 25, R2 pass rate = 0.5, R1 score = 10, earlier time (Tier 4)
    # Team Epsilon: Total = 25, R2 pass rate = 0.5, R1 score = 10, later time
    db = SessionLocal()
    now = datetime.utcnow()

    teams_spec = [
        ("Team Alpha", 15.0, 15.0, 1.0, 15.0, now - timedelta(minutes=10)),
        ("Team Beta", 12.5, 12.5, 1.0, 12.5, now - timedelta(minutes=20)),
        ("Team Gamma", 15.0, 10.0, 0.5, 15.0, now - timedelta(minutes=30)),
        ("Team Delta", 10.0, 15.0, 0.5, 10.0, now - timedelta(minutes=40)),
        ("Team Epsilon", 10.0, 15.0, 0.5, 10.0, now - timedelta(minutes=15)) # Later submission than Delta
    ]

    import uuid
    for name, r1_s, r2_s, r2_pr, r1_human, sub_time in teams_spec:
        team = Team(hackathon_id=hk_id, name=name, invite_code=str(uuid.uuid4())[:8])
        db.add(team)
        db.flush()

        # Round 1 submission & evaluation
        sub1 = Submission(challenge_id=c1, team_id=team.id, prompt_text="r1 prompt", explanation="expl", status="locked", submitted_at=sub_time)
        db.add(sub1)
        db.flush()
        ev1 = Evaluation(submission_id=sub1.id, type="human", status="submitted", judge_score=r1_human)
        db.add(ev1)

        # Round 2 submission & evaluation
        sub2 = Submission(challenge_id=c2, team_id=team.id, prompt_text="r2 prompt", explanation="expl", status="locked", submitted_at=sub_time)
        db.add(sub2)
        db.flush()
        ev2 = Evaluation(
            submission_id=sub2.id,
            type="automated",
            status="completed",
            auto_score=r2_s,
            pass_count=int(r2_pr * 10),
            total_count=10,
            format_compliant="true"
        )
        db.add(ev2)

    # Link p_user to Team Beta
    b_team = db.query(Team).filter(Team.name == "Team Beta").first()
    db.add(TeamMember(team_id=b_team.id, user_id=p_user_id, role="member"))
    db.commit()
    db.close()

    # 4. Gating Test: Participant MUST receive 403 Forbidden before publication
    part_before = client.get(f"/api/v1/hackathons/{hk_id}/leaderboard", headers=part_headers)
    assert part_before.status_code == 403
    assert "not been published" in part_before.json()["detail"].lower()

    # Admin CAN view leaderboard before publication
    admin_before = client.get(f"/api/v1/hackathons/{hk_id}/leaderboard", headers=admin_headers)
    assert admin_before.status_code == 200

    # 5. Measure Recomputation Latency
    db = SessionLocal()
    start_t = time.perf_counter()
    entries = recompute_leaderboard(hk_id, db)
    elapsed_ms = (time.perf_counter() - start_t) * 1000
    db.close()
    assert elapsed_ms < 100.0, f"Leaderboard recomputation took {elapsed_ms}ms, exceeds 100ms budget"

    # 6. Admin Publishes Results (FR-101)
    pub_res = client.post(f"/api/v1/hackathons/{hk_id}/results/publish", headers=admin_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["results_published"] is True

    # Participant can now view leaderboard (200 OK)
    part_after = client.get(f"/api/v1/hackathons/{hk_id}/leaderboard", headers=part_headers)
    assert part_after.status_code == 200
    lb = part_after.json()
    assert len(lb) == 5

    # 7. Verify Deterministic Tie-Breaking Order
    # Expected Rank 1: Team Alpha (Total 30.0)
    assert lb[0]["team_name"] == "Team Alpha"
    assert lb[0]["rank"] == 1
    assert lb[0]["total_score"] == 30.0

    # Expected Rank 2: Team Beta (Total 25.0, R2 pass rate 1.0 > 0.5)
    assert lb[1]["team_name"] == "Team Beta"
    assert lb[1]["rank"] == 2
    assert lb[1]["total_score"] == 25.0
    assert lb[1]["round2_pass_rate"] == 1.0

    # Expected Rank 3: Team Gamma (Total 25.0, R2 pass rate 0.5, R1 human 15.0 > 10.0)
    assert lb[2]["team_name"] == "Team Gamma"
    assert lb[2]["rank"] == 3
    assert lb[2]["total_score"] == 25.0
    assert lb[2]["round1_human_score"] == 15.0

    # Expected Rank 4: Team Delta (Total 25.0, R2 pass rate 0.5, R1 human 10.0, submitted 40m ago < 15m ago)
    assert lb[3]["team_name"] == "Team Delta"
    assert lb[3]["rank"] == 4

    # Expected Rank 5: Team Epsilon (Total 25.0, R2 pass rate 0.5, R1 human 10.0, submitted later than Delta)
    assert lb[4]["team_name"] == "Team Epsilon"
    assert lb[4]["rank"] == 5

    # 8. Test CSV Export (FR-097)
    csv_res = client.get(f"/api/v1/hackathons/{hk_id}/results/export?format=csv", headers=admin_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    csv_content = csv_res.text
    assert "Rank,Team Name,Total Score" in csv_content
    assert "Team Alpha" in csv_content
    assert "Team Beta" in csv_content

    # 9. Test JSON Export (FR-097)
    json_res = client.get(f"/api/v1/hackathons/{hk_id}/results/export?format=json", headers=admin_headers)
    assert json_res.status_code == 200
    json_content = json_res.json()
    assert json_content["hackathon_id"] == hk_id
    assert len(json_content["rankings"]) == 5
    assert json_content["rankings"][0]["team_name"] == "Team Alpha"
