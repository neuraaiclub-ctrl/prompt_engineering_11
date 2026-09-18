import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.score import Score

client = TestClient(app)

def test_atomic_rubric_scoring_and_boundary_validation():
    """
    SRS Section 9 & 18, FR-082:
    Atomic server-side validation of 0-5 integer scale.
    Rejects out-of-range, fractional, or invalid values with 422.
    Guarantees no partial writes.
    """
    # 1. Setup Admin & Judge
    from app.tests.conftest import create_test_user
    create_test_user("judge1@rubric.com", "Password123!", name="Judge One", roles=["judge"])
    create_test_user("admin@rubric.com", "Password123!", name="Admin Rubric", roles=["admin"])

    judge_token = client.post("/api/v1/auth/login", json={"email": "judge1@rubric.com", "password": "Password123!"}).json()["access_token"]
    judge_headers = {"Authorization": f"Bearer {judge_token}"}

    admin_token = client.post("/api/v1/auth/login", json={"email": "admin@rubric.com", "password": "Password123!"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Setup Hackathon, Round 1, Case, Participant Team & Submission
    hk = client.post("/api/v1/hackathons", json={"title": "Rubric Test Hackathon"}, headers=admin_headers).json()
    rnd = client.post(f"/api/v1/hackathons/{hk['id']}/rounds", json={
        "round_number": 1,
        "title": "Round 1",
        "type": "round1_fix_the_prompt",
        "duration_minutes": 30
    }, headers=admin_headers).json()

    case_res = client.post(f"/api/v1/rounds/{rnd['id']}/prompt-cases", json={
        "title": "Rubric Case",
        "original_prompt": "Buggy prompt",
        "bad_output": "Bad output",
        "broken_reason": "vague"
    }, headers=admin_headers).json()
    challenge_id = case_res["challenge_id"]

    # Participant team
    create_test_user("dev@rubric.com", "Password123!", name="Dev", roles=["participant"])
    p_token = client.post("/api/v1/auth/login", json={"email": "dev@rubric.com", "password": "Password123!"}).json()["access_token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}

    client.post("/api/v1/teams", json={"name": "Rubric Team", "hackathon_id": hk["id"]}, headers=p_headers)

    sub_res = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": "Clean prompt",
        "explanation": "Clear role and output format"
    }, headers=p_headers)
    assert sub_res.status_code == 201
    submission_id = sub_res.json()["id"]

    # 3. Test Invalid Scores (Must return 422 and perform zero writes)
    invalid_payloads = [
        # Out of range (< 0)
        {"scores": {"diagnosis_quality": -1, "improvement_quality": 3, "final_output_quality": 4, "documentation_clarity": 5}},
        # Out of range (> 5)
        {"scores": {"diagnosis_quality": 6, "improvement_quality": 3, "final_output_quality": 4, "documentation_clarity": 5}},
        # Fractional value (5.5)
        {"scores": {"diagnosis_quality": 4, "improvement_quality": 5.5, "final_output_quality": 4, "documentation_clarity": 3}},
        # Non-numeric value ("five")
        {"scores": {"diagnosis_quality": 4, "improvement_quality": "five", "final_output_quality": 4, "documentation_clarity": 3}},
        # Missing dimension
        {"scores": {"diagnosis_quality": 4, "improvement_quality": 3, "final_output_quality": 4}}
    ]

    for payload in invalid_payloads:
        resp = client.post(f"/api/v1/evaluations/{submission_id}/scores", json=payload, headers=judge_headers)
        assert resp.status_code == 422, f"Expected 422 for payload {payload}, got {resp.status_code}"

    # Atomic write check: ensure NO Score rows were created from failed attempts
    db = SessionLocal()
    scores_count = db.query(Score).count()
    db.close()
    assert scores_count == 0, f"Expected 0 score rows after failed attempts, found {scores_count}"

    # 4. Test Valid Boundary Scores: 0 and 5
    valid_boundary_payload = {
        "scores": {
            "diagnosis_quality": 0,
            "improvement_quality": 5,
            "final_output_quality": 0,
            "documentation_clarity": 5
        },
        "comment": "Boundary evaluation test"
    }
    valid_resp = client.post(f"/api/v1/evaluations/{submission_id}/scores", json=valid_boundary_payload, headers=judge_headers)
    assert valid_resp.status_code == 201
    vdata = valid_resp.json()
    assert vdata["judge_score"] == 10.0 # 0 + 5 + 0 + 5

    # Check persistence in DB
    db = SessionLocal()
    saved_scores = db.query(Score).all()
    assert len(saved_scores) == 4
    dim_map = {s.dimension: s.value for s in saved_scores}
    assert dim_map["diagnosis_quality"] == 0.0
    assert dim_map["improvement_quality"] == 5.0
    assert dim_map["final_output_quality"] == 0.0
    assert dim_map["documentation_clarity"] == 5.0
    db.close()
