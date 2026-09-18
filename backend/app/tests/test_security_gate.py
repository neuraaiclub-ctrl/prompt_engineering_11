import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.audit import AuditLog

client = TestClient(app)

def test_security_gate_hidden_test_cases_and_broken_reason():
    """
    SRS Section 11.1 Threat Model & Section 22.9 Standing Security Contract:
    1. Participant token NEVER receives TestCase input, expected_output, or eval_rule.
    2. Direct GET /api/v1/test-cases/{id} returns 404 indistinguishably to participants.
    3. Every test case access denial is logged in the immutable AuditLog.
    4. Participant NEVER receives internal broken_reason in prompt-case response.
    5. Admin CAN view test case details and broken_reason.
    """
    # 1. Register and login Admin
    from app.tests.conftest import create_test_user
    create_test_user("secadmin@example.com", "AdminPassword123!", name="SecAdmin", roles=["admin"])

    admin_login = client.post("/api/v1/auth/login", json={
        "email": "secadmin@example.com",
        "password": "AdminPassword123!"
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Register and login Participant
    create_test_user("secpart@example.com", "PartPassword123!", name="SecParticipant", roles=["participant"])
    part_login = client.post("/api/v1/auth/login", json={
        "email": "secpart@example.com",
        "password": "PartPassword123!"
    })
    part_token = part_login.json()["access_token"]
    part_headers = {"Authorization": f"Bearer {part_token}"}

    # 3. Admin creates a hackathon & round
    h_resp = client.post("/api/v1/hackathons", json={
        "title": "Security Hackathon",
        "description": "Security testing arena"
    }, headers=admin_headers)
    hackathon_id = h_resp.json()["id"]

    r_resp = client.post(f"/api/v1/hackathons/{hackathon_id}/rounds", json={
        "round_number": 2,
        "title": "Constraint Arena",
        "type": "round2_constraints",
        "duration_minutes": 60
    }, headers=admin_headers)
    round_id = r_resp.json()["id"]

    # 4. Admin creates a constraint challenge and a hidden test case
    c_resp = client.post(f"/api/v1/rounds/{round_id}/constraint-challenges", json={
        "title": "Sentiment Classifier Under 30 Tokens",
        "constraint_type": "max_tokens_n",
        "max_tokens": 30,
        "task_description": "Classify sentiment in 1 word"
    }, headers=admin_headers)
    assert c_resp.status_code == 201
    challenge_id = c_resp.json()["id"]

    tc_resp = client.post(f"/api/v1/constraint-challenges/{challenge_id}/test-cases", json={
        "input": "TOP_SECRET_CLASSIFIED_INPUT: The server exploded unexpectedly",
        "expected_output": "NEGATIVE",
        "eval_rule": {"type": "exact"}
    }, headers=admin_headers)
    assert tc_resp.status_code == 201
    tc_id = tc_resp.json()["id"]

    # 5. Admin creates Round 1 PromptCase with broken_reason
    r1_round = client.post(f"/api/v1/hackathons/{hackathon_id}/rounds", json={
        "round_number": 1,
        "title": "Fix The Prompt",
        "type": "round1_fix_prompt",
        "duration_minutes": 45
    }, headers=admin_headers).json()["id"]

    pc_resp = client.post(f"/api/v1/rounds/{r1_round}/prompt-cases", json={
        "title": "Buggy Summarizer",
        "original_prompt": "Summarize this quickly",
        "bad_output": "I am unable to answer",
        "broken_reason": "no_role_context",
        "difficulty": "easy"
    }, headers=admin_headers)
    assert pc_resp.status_code == 201
    case_id = pc_resp.json()["id"]

    # -------------------------------------------------------------
    # GATE TEST 1: Participant GET constraint challenge - test details omitted
    # -------------------------------------------------------------
    part_chal = client.get(f"/api/v1/constraint-challenges/{challenge_id}", headers=part_headers)
    assert part_chal.status_code == 200
    pdata = part_chal.json()
    assert "input" not in pdata
    assert "expected_output" not in pdata
    assert "eval_rule" not in pdata
    assert "TOP_SECRET" not in str(pdata)
    assert pdata["hidden_test_count"] == 1

    # -------------------------------------------------------------
    # GATE TEST 2: Direct GET /api/v1/test-cases/{tc_id} as Participant returns 404
    # Indistinguishable from non-existent ID
    # -------------------------------------------------------------
    leak_probe = client.get(f"/api/v1/test-cases/{tc_id}", headers=part_headers)
    assert leak_probe.status_code == 404
    assert leak_probe.json()["detail"] == "Test case not found"
    assert "TOP_SECRET" not in leak_probe.text

    non_existent_probe = client.get("/api/v1/test-cases/non-existent-uuid-99999", headers=part_headers)
    assert non_existent_probe.status_code == 404
    assert non_existent_probe.json()["detail"] == "Test case not found"

    # -------------------------------------------------------------
    # GATE TEST 3: Access denial recorded in immutable AuditLog
    # -------------------------------------------------------------
    db = SessionLocal()
    audit_entry = db.query(AuditLog).filter(
        AuditLog.action == "testcase.access_denied",
        AuditLog.target_id == tc_id
    ).first()
    assert audit_entry is not None
    assert audit_entry.target_type == "TestCase"
    db.close()

    # -------------------------------------------------------------
    # GATE TEST 4: Admin CAN view test case details
    # -------------------------------------------------------------
    admin_probe = client.get(f"/api/v1/test-cases/{tc_id}", headers=admin_headers)
    assert admin_probe.status_code == 200
    adata = admin_probe.json()
    assert adata["input"] == "TOP_SECRET_CLASSIFIED_INPUT: The server exploded unexpectedly"
    assert adata["expected_output"] == "NEGATIVE"

    # -------------------------------------------------------------
    # GATE TEST 5: Participant GET prompt case - broken_reason omitted
    # -------------------------------------------------------------
    part_case = client.get(f"/api/v1/prompt-cases/{case_id}", headers=part_headers)
    assert part_case.status_code == 200
    assert "broken_reason" not in part_case.json()

    # Admin GET prompt case - broken_reason included
    admin_case = client.get(f"/api/v1/prompt-cases/{case_id}", headers=admin_headers)
    assert admin_case.status_code == 200
    assert admin_case.json()["broken_reason"] == "no_role_context"
