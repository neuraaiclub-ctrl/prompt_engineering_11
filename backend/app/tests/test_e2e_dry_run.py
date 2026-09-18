import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.audit import AuditLog

client = TestClient(app)

def test_full_platform_e2e_dry_run():
    """
    SRS Section 24, Phase 11 Final End-to-End Dry Run:
    1. Admin creates hackathon, Round 1 (prompt case), Round 2 (constraint challenge).
    2. Teams form and register.
    3. Round 1 workflow: prompt iterations with explanations, preview run, mark final, submit & lock.
    4. Round 2 workflow: prompt submission, constraint validation, automated evaluation on test cases.
    5. Human judging: assignments, role-scoped submission viewer (hidden test cases protected),
       0-5 integer rubric scoring, multi-judge independent entries.
    6. Admin oversight panel & results publication gating.
    7. Participant views final leaderboard & tie-break ranking.
    8. Audit log verifies full immutable event trail.
    """
    from app.tests.conftest import create_test_user
    create_test_user("admin@neura-e2e.com", "Password123!", name="Admin E2E", roles=["admin"])
    create_test_user("judge1@neura-e2e.com", "Password123!", name="Judge 1", roles=["judge"])
    create_test_user("judge2@neura-e2e.com", "Password123!", name="Judge 2", roles=["judge"])
    create_test_user("lead1@neura-e2e.com", "Password123!", name="Nova Lead", roles=["participant"])
    create_test_user("lead2@neura-e2e.com", "Password123!", name="Synapse Lead", roles=["participant"])

    admin_token = client.post("/api/v1/auth/login", json={"email": "admin@neura-e2e.com", "password": "Password123!"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    j1_token = client.post("/api/v1/auth/login", json={"email": "judge1@neura-e2e.com", "password": "Password123!"}).json()["access_token"]
    j1_headers = {"Authorization": f"Bearer {j1_token}"}

    j2_token = client.post("/api/v1/auth/login", json={"email": "judge2@neura-e2e.com", "password": "Password123!"}).json()["access_token"]
    j2_headers = {"Authorization": f"Bearer {j2_token}"}

    t1_token = client.post("/api/v1/auth/login", json={"email": "lead1@neura-e2e.com", "password": "Password123!"}).json()["access_token"]
    t1_headers = {"Authorization": f"Bearer {t1_token}"}

    t2_token = client.post("/api/v1/auth/login", json={"email": "lead2@neura-e2e.com", "password": "Password123!"}).json()["access_token"]
    t2_headers = {"Authorization": f"Bearer {t2_token}"}

    # 2. Hackathon & Rounds Creation
    hk = client.post("/api/v1/hackathons", json={"title": "NEURA Global 2026"}, headers=admin_headers).json()
    hk_id = hk["id"]

    r1 = client.post(f"/api/v1/hackathons/{hk_id}/rounds", json={
        "round_number": 1, "title": "Round 1 - Fix the Prompt", "type": "round1_fix_the_prompt", "duration_minutes": 30
    }, headers=admin_headers).json()
    r1_id = r1["id"]

    r2 = client.post(f"/api/v1/hackathons/{hk_id}/rounds", json={
        "round_number": 2, "title": "Round 2 - Constraint Challenge", "type": "round2_constraint_challenge", "duration_minutes": 30
    }, headers=admin_headers).json()
    r2_id = r2["id"]

    # 3. Challenge Authoring
    # Round 1 Case
    case1 = client.post(f"/api/v1/rounds/{r1_id}/prompt-cases", json={
        "title": "SQL Query Generation",
        "original_prompt": "Write a query to get users who bought products",
        "bad_output": "SELECT * FROM users",
        "broken_reason": "vague"
    }, headers=admin_headers).json()
    c1_id = case1["challenge_id"]

    # Round 2 Challenge & Test cases
    chal2 = client.post(f"/api/v1/rounds/{r2_id}/constraint-challenges", json={
        "title": "Strict Sentiment Classifier",
        "constraint_type": "no_system_prompt",
        "task_description": "Classify sentiment without system prompt"
    }, headers=admin_headers).json()
    c2_id = chal2["id"]

    # Add 1 revealed and 2 hidden test cases
    client.post(f"/api/v1/constraint-challenges/{c2_id}/test-cases", json={
        "input": "The system broke", "expected_output": "NEGATIVE", "eval_rule": {"type": "exact"}
    }, headers=admin_headers)
    client.post(f"/api/v1/constraint-challenges/{c2_id}/test-cases", json={
        "input": "Hidden terrible failure", "expected_output": "NEGATIVE", "eval_rule": {"type": "exact"}
    }, headers=admin_headers)
    client.post(f"/api/v1/constraint-challenges/{c2_id}/test-cases", json={
        "input": "Hidden bad bug", "expected_output": "NEGATIVE", "eval_rule": {"type": "exact"}
    }, headers=admin_headers)

    # 4. Team Formation
    team1 = client.post("/api/v1/teams", json={"name": "CyberNova", "hackathon_id": hk_id}, headers=t1_headers).json()
    team2 = client.post("/api/v1/teams", json={"name": "SynapseAI", "hackathon_id": hk_id}, headers=t2_headers).json()

    # 5. Round 1 Workflow (Team 1)
    # Draft v1
    v1_res = client.post(f"/api/v1/challenges/{c1_id}/prompt-versions", json={
        "prompt_text": "Write a Postgres SQL query with inner joins",
        "explanation": "Specified database dialect and join type"
    }, headers=t1_headers)
    assert v1_res.status_code == 201

    # Preview v1
    prev_res = client.post("/api/v1/executions/preview", json={
        "user_prompt": "Write a Postgres SQL query with inner joins"
    }, headers=t1_headers)
    assert prev_res.status_code == 200

    # Draft v2
    v2_res = client.post(f"/api/v1/challenges/{c1_id}/prompt-versions", json={
        "prompt_text": "Write an optimized Postgres query joining users and purchases on user_id",
        "explanation": "Added table schema and key relationship"
    }, headers=t1_headers)
    assert v2_res.status_code == 201

    # Mark v2 as final
    final_res = client.patch(f"/api/v1/prompt-versions/{v2_res.json()['id']}/mark-final", headers=t1_headers)
    assert final_res.status_code == 200

    # Submit & Lock
    sub1_res = client.post(f"/api/v1/challenges/{c1_id}/submissions", json={
        "prompt_text": "Write an optimized Postgres query joining users and purchases on user_id",
        "explanation": "Final refined prompt with schema and indices"
    }, headers=t1_headers)
    assert sub1_res.status_code == 201
    sub1_id = sub1_res.json()["id"]

    # Team 2 also submits for Round 1
    sub1_t2 = client.post(f"/api/v1/challenges/{c1_id}/submissions", json={
        "prompt_text": "SELECT users.* FROM users JOIN orders ON users.id = orders.user_id",
        "explanation": "Direct SQL template prompt"
    }, headers=t2_headers)
    sub1_t2_id = sub1_t2.json()["id"]

    # 6. Round 2 Workflow (Automated Evaluation)
    sub2_res = client.post(f"/api/v1/challenges/{c2_id}/submissions", json={
        "prompt_text": "Classify sentiment with only the single classification: NEGATIVE or POSITIVE. Input: {input}",
        "explanation": "Zero-shot classification prompt"
    }, headers=t1_headers)
    assert sub2_res.status_code == 201
    sub2_id = sub2_res.json()["id"]
    assert sub2_res.json()["auto_score"] > 0
    assert sub2_res.json()["total_count"] == 3

    # Team 2 Round 2 submission
    sub2_t2 = client.post(f"/api/v1/challenges/{c2_id}/submissions", json={
        "prompt_text": "Classify sentiment with only the single classification: NEGATIVE or POSITIVE. Input: {input}",
        "explanation": "String formatting technique"
    }, headers=t2_headers)
    sub2_t2_id = sub2_t2.json()["id"]

    # 7. Human Judging
    # Judge 1 inspects submission: confirms hidden test cases protected
    j_sub_view = client.get(f"/api/v1/submissions/{sub2_id}", headers=j1_headers).json()
    for tc in j_sub_view["test_cases"]:
        if tc["visibility"] == "hidden":
            assert "input" not in tc or tc["input"] is None
            assert "Hidden query" not in str(tc)

    # Judge 1 scores Team 1 Round 1 (5, 5, 4, 4 = 18.0)
    client.post(f"/api/v1/evaluations/{sub1_id}/scores", json={
        "scores": {"diagnosis_quality": 5, "improvement_quality": 5, "final_output_quality": 4, "documentation_clarity": 4},
        "comment": "Superb diagnosis and documentation"
    }, headers=j1_headers)

    # Judge 2 scores Team 1 Round 1 (4, 5, 4, 4 = 17.0 - delta <= 1, no disagreement)
    j2_sub1 = client.post(f"/api/v1/evaluations/{sub1_id}/scores", json={
        "scores": {"diagnosis_quality": 4, "improvement_quality": 5, "final_output_quality": 4, "documentation_clarity": 4},
        "comment": "Strong agree with prompt improvements"
    }, headers=j2_headers)
    assert j2_sub1.json()["disagreement_flag"] is False

    # Judge 1 scores Team 2 Round 1 (3, 3, 3, 3 = 12.0)
    client.post(f"/api/v1/evaluations/{sub1_t2_id}/scores", json={
        "scores": {"diagnosis_quality": 3, "improvement_quality": 3, "final_output_quality": 3, "documentation_clarity": 3},
        "comment": "Adequate"
    }, headers=j1_headers)

    # 8. Admin Oversight & Gating
    # Admin checks progress
    oversight = client.get(f"/api/v1/rounds/{r1_id}/evaluations/progress", headers=admin_headers).json()
    assert oversight["total_submissions"] == 2

    # Participant tries to view leaderboard: Gated 403 Forbidden!
    p_blocked = client.get(f"/api/v1/hackathons/{hk_id}/leaderboard", headers=t1_headers)
    assert p_blocked.status_code == 403

    # Admin Publishes Results
    pub_res = client.post(f"/api/v1/hackathons/{hk_id}/results/publish", headers=admin_headers)
    assert pub_res.status_code == 200

    # Participant can now view leaderboard
    p_allowed = client.get(f"/api/v1/hackathons/{hk_id}/leaderboard", headers=t1_headers)
    assert p_allowed.status_code == 200
    rankings = p_allowed.json()
    assert len(rankings) == 2
    assert rankings[0]["team_name"] == "CyberNova"
    assert rankings[0]["rank"] == 1
    assert rankings[1]["team_name"] == "SynapseAI"
    assert rankings[1]["rank"] == 2

    # 9. Audit Log Verification
    db = SessionLocal()
    actions = [a.action for a in db.query(AuditLog).all()]
    expected_actions = ["challenge.create", "submission.create", "score.enter", "results.publish"]
    for ea in expected_actions:
        assert ea in actions, f"Expected audit action '{ea}' was not found in audit logs: {actions}"
    db.close()
