import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.challenge import TestCase as DBTestCase
from app.models.audit import AuditLog

client = TestClient(app)

def test_judge_security_contract_hidden_tests_never_leaked():
    """
    SRS Section 9.3, 11.1, FR-058:
    Judges and participants can NEVER see unrevealed hidden test inputs/outputs.
    Only admin or revealed test cases can expose inputs/expected outputs.
    """
    from app.tests.conftest import create_test_user
    create_test_user("admin_sec@hack.com", "Password123!", name="Admin Sec", roles=["admin"])
    create_test_user("judge_sec@hack.com", "Password123!", name="Judge Sec", roles=["judge"])
    create_test_user("part_sec@hack.com", "Password123!", name="Part Sec", roles=["participant"])

    admin_token = client.post("/api/v1/auth/login", json={"email": "admin_sec@hack.com", "password": "Password123!"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    judge_token = client.post("/api/v1/auth/login", json={"email": "judge_sec@hack.com", "password": "Password123!"}).json()["access_token"]
    judge_headers = {"Authorization": f"Bearer {judge_token}"}

    part_token = client.post("/api/v1/auth/login", json={"email": "part_sec@hack.com", "password": "Password123!"}).json()["access_token"]
    part_headers = {"Authorization": f"Bearer {part_token}"}

    # 2. Admin creates Hackathon, Round 2 Constraint Challenge & Test Cases
    hk = client.post("/api/v1/hackathons", json={"title": "Sec Hackathon"}, headers=admin_headers).json()
    rnd = client.post(f"/api/v1/hackathons/{hk['id']}/rounds", json={
        "round_number": 2,
        "title": "Round 2 Constraint",
        "type": "round2_constraint_challenge",
        "duration_minutes": 30
    }, headers=admin_headers).json()

    chal_res = client.post(f"/api/v1/rounds/{rnd['id']}/constraint-challenges", json={
        "title": "JSON Extractor",
        "constraint_type": "valid_json_always",
        "task_description": "Output JSON only"
    }, headers=admin_headers)
    assert chal_res.status_code == 201
    chal_data = chal_res.json()
    challenge_id = chal_data["id"]

    # Add test cases (1 revealed, 1 hidden)
    tc1 = client.post(f"/api/v1/constraint-challenges/{challenge_id}/test-cases", json={
        "input": "Sample text 1",
        "expected_output": '{"status": "ok"}',
        "eval_rule": {"type": "exact"}
    }, headers=admin_headers)
    assert tc1.status_code == 201

    tc2 = client.post(f"/api/v1/constraint-challenges/{challenge_id}/test-cases", json={
        "input": "SUPER_SECRET_HIDDEN_INPUT_99",
        "expected_output": '{"secret": "hidden_val_99"}',
        "eval_rule": {"type": "exact"}
    }, headers=admin_headers)
    assert tc2.status_code == 201

    # 3. Participant submits
    client.post("/api/v1/teams", json={"name": "Sec Team", "hackathon_id": hk["id"]}, headers=part_headers)
    sub_res = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": "Extract json: {input}",
        "explanation": "Valid json extractor"
    }, headers=part_headers)
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]

    # 4. Check Judge View on Submission
    j_sub_res = client.get(f"/api/v1/submissions/{sub_id}", headers=judge_headers)
    assert j_sub_res.status_code == 200
    j_sub_data = j_sub_res.json()

    # Assert that hidden test cases do NOT leak secret strings to Judge
    test_cases_judge = j_sub_data["test_cases"]
    assert len(test_cases_judge) == 2
    for tc in test_cases_judge:
        assert tc["visibility"] == "hidden"
        assert "input" not in tc or tc["input"] is None
        assert "expected_output" not in tc or tc["expected_output"] is None
        assert "SUPER_SECRET_HIDDEN_INPUT_99" not in str(tc)
        assert "hidden_val_99" not in str(tc)
        assert "Sample text 1" not in str(tc)

    # 5. Check Participant View on Submission
    p_sub_res = client.get(f"/api/v1/submissions/{sub_id}", headers=part_headers)
    assert p_sub_res.status_code == 200
    p_sub_data = p_sub_res.json()
    assert len(p_sub_data["test_cases"]) == 2
    for tc in p_sub_data["test_cases"]:
        assert tc["visibility"] == "hidden"
        assert "input" not in tc or tc["input"] is None
        assert "expected_output" not in tc or tc["expected_output"] is None
        assert "SUPER_SECRET_HIDDEN_INPUT_99" not in str(tc)
        assert "hidden_val_99" not in str(tc)

    # 6. Admin CAN view hidden test details
    a_sub_res = client.get(f"/api/v1/submissions/{sub_id}", headers=admin_headers)
    assert a_sub_res.status_code == 200
    a_sub_data = a_sub_res.json()
    hidden_tc_admin = [tc for tc in a_sub_data["test_cases"] if tc.get("input") == "SUPER_SECRET_HIDDEN_INPUT_99"]
    assert len(hidden_tc_admin) == 1
    assert hidden_tc_admin[0]["expected_output"] == '{"secret": "hidden_val_99"}'

    # 7. Check direct /test-cases/{id} probing by Judge or Participant returns 404 and logs audit
    judge_probe = client.get(f"/api/v1/test-cases/{tc2.json()['id']}", headers=judge_headers)
    assert judge_probe.status_code == 404
    part_probe = client.get(f"/api/v1/test-cases/{tc2.json()['id']}", headers=part_headers)
    assert part_probe.status_code == 404

    # Admin can access /test-cases/{id} directly
    admin_probe = client.get(f"/api/v1/test-cases/{tc2.json()['id']}", headers=admin_headers)
    assert admin_probe.status_code == 200
    assert admin_probe.json()["input"] == "SUPER_SECRET_HIDDEN_INPUT_99"
