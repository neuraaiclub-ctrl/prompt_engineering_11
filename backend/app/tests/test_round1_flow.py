import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_round1_full_workflow():
    # 1. Admin login & Hackathon / Round creation
    from app.tests.conftest import create_test_user
    create_test_user("r1admin@example.com", "AdminPassword123!", name="R1Admin", roles=["admin"])

    admin_login = client.post("/api/v1/auth/login", json={
        "email": "r1admin@example.com",
        "password": "AdminPassword123!"
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    h_resp = client.post("/api/v1/hackathons", json={
        "title": "Fix The Prompt Arena",
        "description": "Round 1 testing"
    }, headers=admin_headers)
    hackathon_id = h_resp.json()["id"]

    r_resp = client.post(f"/api/v1/hackathons/{hackathon_id}/rounds", json={
        "round_number": 1,
        "title": "Round 1: Prompt Repair",
        "type": "round1_fix_prompt",
        "duration_minutes": 45
    }, headers=admin_headers)
    round_id = r_resp.json()["id"]

    # 2. Case Authoring with All 6 Broken-Reason Taxonomy values
    taxonomy_reasons = [
        "vague",
        "no_format_specified",
        "contradictory",
        "no_role_context",
        "missing_edge_cases",
        "other"
    ]
    created_cases = []
    for reason in taxonomy_reasons:
        c_resp = client.post(f"/api/v1/rounds/{round_id}/prompt-cases", json={
            "title": f"Case on {reason}",
            "original_prompt": f"Extract info with {reason} issue",
            "bad_output": "Failed raw response",
            "broken_reason": reason,
            "difficulty": "medium"
        }, headers=admin_headers)
        assert c_resp.status_code == 201
        created_cases.append(c_resp.json())

    test_case_item = created_cases[0]
    challenge_id = test_case_item["challenge_id"]

    # 3. Setup Participant and Team
    create_test_user("r1part@example.com", "PartPassword123!", name="R1Participant", roles=["participant"])
    part_login = client.post("/api/v1/auth/login", json={
        "email": "r1part@example.com",
        "password": "PartPassword123!"
    })
    part_token = part_login.json()["access_token"]
    part_headers = {"Authorization": f"Bearer {part_token}"}

    team_resp = client.post("/api/v1/teams", json={
        "name": "Prompt Hackers",
        "hackathon_id": hackathon_id
    }, headers=part_headers)
    assert team_resp.status_code == 201

    # 4. Attempt to create version with BLANK explanation -> MUST RETURN 422
    blank_resp = client.post(f"/api/v1/challenges/{challenge_id}/prompt-versions", json={
        "prompt_text": "Updated prompt without explanation",
        "explanation": ""
    }, headers=part_headers)
    assert blank_resp.status_code == 422
    assert "explanation is required" in blank_resp.json()["detail"].lower()

    whitespace_resp = client.post(f"/api/v1/challenges/{challenge_id}/prompt-versions", json={
        "prompt_text": "Updated prompt with whitespace explanation",
        "explanation": "    "
    }, headers=part_headers)
    assert whitespace_resp.status_code == 422

    # 5. Create 3 valid versions with explanations
    v1_resp = client.post(f"/api/v1/challenges/{challenge_id}/prompt-versions", json={
        "prompt_text": "Version 1: Clarified role and context",
        "explanation": "Added persona definition to reduce vagueness"
    }, headers=part_headers)
    assert v1_resp.status_code == 201
    v1_data = v1_resp.json()
    assert v1_data["version_number"] == 1
    v1_id = v1_data["id"]

    v2_resp = client.post(f"/api/v1/challenges/{challenge_id}/prompt-versions", json={
        "prompt_text": "Version 2: Enforced JSON structure",
        "explanation": "Specified exact output JSON schema"
    }, headers=part_headers)
    assert v2_resp.status_code == 201
    v2_data = v2_resp.json()
    assert v2_data["version_number"] == 2
    v2_id = v2_data["id"]

    v3_resp = client.post(f"/api/v1/challenges/{challenge_id}/prompt-versions", json={
        "prompt_text": "Version 3: Added boundary handling",
        "explanation": "Handled empty text edge case"
    }, headers=part_headers)
    assert v3_resp.status_code == 201
    v3_data = v3_resp.json()
    assert v3_data["version_number"] == 3
    v3_id = v3_data["id"]

    # 6. Explicit mark-final action on Version 2
    mark_resp = client.patch(f"/api/v1/prompt-versions/{v2_id}/mark-final", headers=part_headers)
    assert mark_resp.status_code == 200

    # Verify version history states
    hist_resp = client.get(f"/api/v1/challenges/{challenge_id}/prompt-versions", headers=part_headers)
    assert hist_resp.status_code == 200
    versions = hist_resp.json()
    assert len(versions) == 3
    v_map = {v["id"]: v["is_final"] for v in versions}
    assert v_map[v2_id] is True
    assert v_map[v1_id] is False
    assert v_map[v3_id] is False

    # 7. Submit and Lock
    sub_resp = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": "Version 2: Enforced JSON structure",
        "explanation": "Final chosen iteration for submission",
        "final_version_id": v2_id
    }, headers=part_headers)
    assert sub_resp.status_code == 201
    assert sub_resp.json()["status"] == "locked"

    # 8. Duplicate Submission blocked with 409
    dup_sub = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": "Another try",
        "explanation": "Should be blocked"
    }, headers=part_headers)
    assert dup_sub.status_code == 409

    # 9. Attempting to add a new version after lock MUST RETURN 423 LOCKED
    v4_locked = client.post(f"/api/v1/challenges/{challenge_id}/prompt-versions", json={
        "prompt_text": "Post-lock sneaky prompt",
        "explanation": "Trying to bypass lock"
    }, headers=part_headers)
    assert v4_locked.status_code == 423
    assert "locked" in v4_locked.json()["detail"].lower()
