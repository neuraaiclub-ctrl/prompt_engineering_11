import pytest
import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.execution import Submission
from app.models.evaluation import Evaluation

client = TestClient(app)

def test_concurrency_20_teams_runoff_and_duplicate_rejection():
    """
    SRS Section 22.7, FR-044, FR-066:
    Live runoff simulation: 20 teams submitting concurrently.
    - Zero duplicate submissions permitted per team (409 Conflict).
    - Queue/adapter executes all automated evaluations reliably.
    - Zero database corruption or state leakage.
    """
    db = SessionLocal()

    from app.tests.conftest import create_test_user
    create_test_user("admin_runoff@load.com", "Password123!", name="Admin Runoff", roles=["admin"])

    admin_token = client.post("/api/v1/auth/login", json={"email": "admin_runoff@load.com", "password": "Password123!"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Setup Hackathon & Round 2 Constraint Challenge
    hk = client.post("/api/v1/hackathons", json={"title": "Runoff Hackathon"}, headers=admin_headers).json()
    rnd = client.post(f"/api/v1/hackathons/{hk['id']}/rounds", json={
        "round_number": 2,
        "title": "Runoff Constraint",
        "type": "round2_constraint_challenge",
        "duration_minutes": 15
    }, headers=admin_headers).json()

    chal = client.post(f"/api/v1/rounds/{rnd['id']}/constraint-challenges", json={
        "title": "Runoff Token Limiter",
        "constraint_type": "max_tokens_n",
        "max_tokens": 20,
        "task_description": "Summarize input in under 20 tokens"
    }, headers=admin_headers).json()
    challenge_id = chal["id"]

    # Add 2 hidden test cases
    client.post(f"/api/v1/constraint-challenges/{challenge_id}/test-cases", json={
        "input": "User query Alpha", "expected_output": "POSITIVE", "eval_rule": {"type": "exact"}
    }, headers=admin_headers)
    client.post(f"/api/v1/constraint-challenges/{challenge_id}/test-cases", json={
        "input": "User query Beta", "expected_output": "POSITIVE", "eval_rule": {"type": "exact"}
    }, headers=admin_headers)

    # 3. Create 20 Teams and authenticate their team leads
    team_sessions = []
    for i in range(1, 21):
        email = f"team_lead_{i}@load.com"
        create_test_user(email, "Password123!", name=f"Leader {i}", roles=["participant"])
        t_login = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"}).json()
        token = t_login["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        t_res = client.post("/api/v1/teams", json={"name": f"Runoff Squad {i}", "hackathon_id": hk["id"]}, headers=headers)
        team_sessions.append((headers, f"Concise summary for squad {i}"))

    # 4. Concurrent execution: 20 teams submitting simultaneously via ThreadPoolExecutor
    def submit_team(args):
        hdrs, prompt = args
        return client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
            "prompt_text": prompt,
            "explanation": "Concurrent runoff submission test"
        }, headers=hdrs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(submit_team, team_sessions))

    # Assert all 20 submissions succeeded (status 201)
    status_codes = [r.status_code for r in results]
    assert all(code == 201 for code in status_codes), f"Not all submissions succeeded: {status_codes}"

    # 5. Immediate duplicate submission attempt for all 20 teams (Must ALL be rejected with 409 Conflict)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        dup_results = list(executor.map(submit_team, team_sessions))

    dup_status_codes = [r.status_code for r in dup_results]
    assert all(code == 409 for code in dup_status_codes), f"Duplicate submissions were not blocked: {dup_status_codes}"

    # 6. Verify Database Integrity: Exactly 20 submissions and 20 automated evaluations exist
    db = SessionLocal()
    total_subs = db.query(Submission).filter(Submission.challenge_id == challenge_id).count()
    assert total_subs == 20, f"Expected exactly 20 submissions, found {total_subs}"

    total_evals = db.query(Evaluation).filter(Evaluation.type == "automated").count()
    # At least 20 automated evaluations from this challenge
    chal_subs = db.query(Submission).filter(Submission.challenge_id == challenge_id).all()
    sub_ids = [s.id for s in chal_subs]
    matching_evals = db.query(Evaluation).filter(Evaluation.submission_id.in_(sub_ids), Evaluation.type == "automated").count()
    assert matching_evals == 20, f"Expected 20 automated evals for the challenge, found {matching_evals}"
    db.close()
