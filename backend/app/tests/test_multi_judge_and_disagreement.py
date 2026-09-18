import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.evaluation import Evaluation
from app.models.score import Score

client = TestClient(app)

def test_multi_judge_independent_scores_and_disagreement_flag():
    """
    SRS Section 9, FR-083, FR-085, FR-086, FR-096:
    Multiple judges score independently.
    Leaderboard aggregates average per dimension.
    Delta >= 2 points on any dimension sets disagreement_flag = True.
    """
    from app.tests.conftest import create_test_user
    create_test_user("admin_multi@judging.com", "Password123!", name="Admin Multi", roles=["admin"])
    create_test_user("alice@judging.com", "Password123!", name="Judge Alice", roles=["judge"])
    create_test_user("bob@judging.com", "Password123!", name="Judge Bob", roles=["judge"])

    admin_token = client.post("/api/v1/auth/login", json={"email": "admin_multi@judging.com", "password": "Password123!"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    j1_token = client.post("/api/v1/auth/login", json={"email": "alice@judging.com", "password": "Password123!"}).json()["access_token"]
    j1_headers = {"Authorization": f"Bearer {j1_token}"}

    j2_token = client.post("/api/v1/auth/login", json={"email": "bob@judging.com", "password": "Password123!"}).json()["access_token"]
    j2_headers = {"Authorization": f"Bearer {j2_token}"}

    # 2. Setup Hackathon, Round 1, Case, Team & Submission
    hk = client.post("/api/v1/hackathons", json={"title": "Judging Hackathon"}, headers=admin_headers).json()
    rnd = client.post(f"/api/v1/hackathons/{hk['id']}/rounds", json={
        "round_number": 1,
        "title": "Round 1 Diagnostics",
        "type": "round1_fix_the_prompt",
        "duration_minutes": 30
    }, headers=admin_headers).json()

    case_res = client.post(f"/api/v1/rounds/{rnd['id']}/prompt-cases", json={
        "title": "Taxonomy Challenge",
        "original_prompt": "Sort the user inputs",
        "bad_output": "Random order",
        "broken_reason": "no_format_specified"
    }, headers=admin_headers).json()
    challenge_id = case_res["challenge_id"]

    create_test_user("dev_multi@judging.com", "Password123!", name="Team Dev", roles=["participant"])
    p_token = client.post("/api/v1/auth/login", json={"email": "dev_multi@judging.com", "password": "Password123!"}).json()["access_token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}

    t_res = client.post("/api/v1/teams", json={"name": "Quantum Solvers", "hackathon_id": hk["id"]}, headers=p_headers)
    team_id = t_res.json()["id"]

    sub_res = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": "Sort the inputs ascending formatted as strict JSON array",
        "explanation": "Added output format specification"
    }, headers=p_headers)
    submission_id = sub_res.json()["id"]

    # 3. Judge 1 scores the submission (Total 16: 5, 4, 4, 3)
    j1_payload = {
        "scores": {
            "diagnosis_quality": 5,
            "improvement_quality": 4,
            "final_output_quality": 4,
            "documentation_clarity": 3
        },
        "comment": "Solid identification of missing format"
    }
    j1_res = client.post(f"/api/v1/evaluations/{submission_id}/scores", json=j1_payload, headers=j1_headers)
    assert j1_res.status_code == 201
    assert j1_res.json()["judge_score"] == 16.0
    assert j1_res.json()["disagreement_flag"] is False

    # 4. Judge 2 scores the submission with a >= 2 point delta on diagnosis_quality (3 vs 5) and output (2 vs 4)
    # Total 12: 3, 4, 2, 3
    j2_payload = {
        "scores": {
            "diagnosis_quality": 3, # Delta = 2.0
            "improvement_quality": 4, # Delta = 0.0
            "final_output_quality": 2, # Delta = 2.0
            "documentation_clarity": 3  # Delta = 0.0
        },
        "comment": "Output could still be improved"
    }
    j2_res = client.post(f"/api/v1/evaluations/{submission_id}/scores", json=j2_payload, headers=j2_headers)
    assert j2_res.status_code == 201
    assert j2_res.json()["judge_score"] == 12.0
    assert j2_res.json()["disagreement_flag"] is True

    # 5. Verify both evaluations persisted independently in DB
    db = SessionLocal()
    evals = db.query(Evaluation).filter(Evaluation.submission_id == submission_id, Evaluation.type == "human").all()
    assert len(evals) == 2
    for ev in evals:
        assert ev.disagreement_flag is True
        assert len(ev.scores) == 4
    db.close()

    # 6. Check Admin Oversight Progress Panel
    prog_res = client.get(f"/api/v1/rounds/{rnd['id']}/evaluations/progress", headers=admin_headers)
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["total_submissions"] == 1
    sub_prog = prog_data["submissions_progress"][0]
    assert sub_prog["judges_count"] == 2
    assert sub_prog["average_score"] == 14.0 # (16 + 12) / 2
    assert sub_prog["disagreement_flag"] is True

    # 7. Check Leaderboard Cache (Round 1 human score average = 14.0)
    lb_res = client.get(f"/api/v1/hackathons/{hk['id']}/leaderboard", headers=admin_headers)
    assert lb_res.status_code == 200
    lb_data = lb_res.json()
    assert len(lb_data) == 1
    entry = lb_data[0]
    assert entry["team_name"] == "Quantum Solvers"
    assert entry["round1_score"] == 14.0
    assert entry["round1_human_score"] == 14.0
    assert entry["total_score"] == 14.0

    # 8. Test consensus resolution: Judge 2 updates score to 4, 4, 3, 3 (delta <= 1 everywhere)
    j2_updated = {
        "scores": {
            "diagnosis_quality": 4, # Delta = 1.0
            "improvement_quality": 4, # Delta = 0.0
            "final_output_quality": 3, # Delta = 1.0
            "documentation_clarity": 3  # Delta = 0.0
        },
        "comment": "Re-evaluated after reviewing case taxonomy"
    }
    j2_update_res = client.post(f"/api/v1/evaluations/{submission_id}/scores", json=j2_updated, headers=j2_headers)
    assert j2_update_res.status_code == 201
    assert j2_update_res.json()["disagreement_flag"] is False

    # Check progress panel again: disagreement_flag is now False
    prog_res2 = client.get(f"/api/v1/rounds/{rnd['id']}/evaluations/progress", headers=admin_headers)
    assert prog_res2.json()["submissions_progress"][0]["disagreement_flag"] is False
    assert prog_res2.json()["submissions_progress"][0]["average_score"] == 15.0 # (16 + 14) / 2
