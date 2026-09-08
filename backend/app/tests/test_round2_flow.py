import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_round2_full_workflow_and_scoring():
    # 1. Admin setup
    client.post("/api/v1/auth/register", json={
        "name": "R2Admin",
        "email": "r2admin@example.com",
        "password": "AdminPassword123!"
    })

    from app.database import SessionLocal
    from app.models.user import User, Role
    db = SessionLocal()
    u = db.query(User).filter(User.email == "r2admin@example.com").first()
    db.add(Role(user_id=u.id, name="admin"))
    db.commit()
    db.close()

    admin_login = client.post("/api/v1/auth/login", json={
        "email": "r2admin@example.com",
        "password": "AdminPassword123!"
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    h_resp = client.post("/api/v1/hackathons", json={
        "title": "Constraint Battleground",
        "description": "Round 2 Arena"
    }, headers=admin_headers)
    hackathon_id = h_resp.json()["id"]

    r_resp = client.post(f"/api/v1/hackathons/{hackathon_id}/rounds", json={
        "round_number": 2,
        "title": "Strict Token Limit Challenge",
        "type": "round2_constraints",
        "duration_minutes": 60
    }, headers=admin_headers)
    round_id = r_resp.json()["id"]

    # 2. Create challenge with max_tokens constraint = 15
    c_resp = client.post(f"/api/v1/rounds/{round_id}/constraint-challenges", json={
        "title": "Ultra-Short Sentiment Tagger",
        "constraint_type": "max_tokens_n",
        "max_tokens": 15,
        "task_description": "Classify text sentiment into POSITIVE or NEGATIVE with extreme token brevity."
    }, headers=admin_headers)
    assert c_resp.status_code == 201
    challenge_id = c_resp.json()["id"]

    # 3. Admin adds 3 hidden test cases
    test_cases_data = [
        ("The system crashed and destroyed my files completely", "NEGATIVE"),
        ("Worst customer support experience of my life", "NEGATIVE"),
        ("Everything was delivered cleanly and swiftly", "POSITIVE")
    ]
    for inp, out in test_cases_data:
        tc_res = client.post(f"/api/v1/constraint-challenges/{challenge_id}/test-cases", json={
            "input": inp,
            "expected_output": out,
            "eval_rule": {"type": "exact"}
        }, headers=admin_headers)
        assert tc_res.status_code == 201

    # 4. Setup Team 1 (violator: over-limit prompt)
    client.post("/api/v1/auth/register", json={
        "name": "OverlimitDev",
        "email": "overlimit@example.com",
        "password": "Password123!"
    })
    t1_login = client.post("/api/v1/auth/login", json={
        "email": "overlimit@example.com",
        "password": "Password123!"
    })
    t1_token = t1_login.json()["access_token"]
    t1_headers = {"Authorization": f"Bearer {t1_token}"}

    client.post("/api/v1/teams", json={
        "name": "Verbose Coders",
        "hackathon_id": hackathon_id
    }, headers=t1_headers)

    # Verbose prompt (> 15 tokens)
    verbose_prompt = (
        "You are an intelligent sentiment analysis classifier. "
        "Read the following customer input carefully and output only one single classification: "
        "either the word POSITIVE or the word NEGATIVE."
    )
    
    # FR-065: Over-limit prompt MUST be accepted, marked constraint_violated=True, NOT hard-rejected
    t1_sub = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": verbose_prompt,
        "explanation": "Over token budget but high accuracy"
    }, headers=t1_headers)
    
    assert t1_sub.status_code == 201
    sub_data = t1_sub.json()
    assert sub_data["constraint_violated"] is True
    assert sub_data["status"] == "locked"
    # Verification of disclosure-limited response: only aggregate counts, no hidden inputs/outputs
    assert sub_data["total_count"] == 3
    assert "pass_rate_display" in sub_data
    assert "input" not in sub_data
    assert "expected_output" not in sub_data
    # Violated score should be penalized (<= 2.5)
    assert sub_data["auto_score"] <= 2.5

    # 5. Team 1 double submission blocked by UNIQUE constraint (409 Conflict)
    dup_sub = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": "Another prompt",
        "explanation": "Trying again"
    }, headers=t1_headers)
    assert dup_sub.status_code == 409
    assert "already submitted" in dup_sub.json()["detail"].lower()

    # 6. Setup Team 2 (compliant: concise prompt under 15 tokens)
    client.post("/api/v1/auth/register", json={
        "name": "ConciseDev",
        "email": "concise@example.com",
        "password": "Password123!"
    })
    t2_login = client.post("/api/v1/auth/login", json={
        "email": "concise@example.com",
        "password": "Password123!"
    })
    t2_token = t2_login.json()["access_token"]
    t2_headers = {"Authorization": f"Bearer {t2_token}"}

    client.post("/api/v1/teams", json={
        "name": "Minimalist Coders",
        "hackathon_id": hackathon_id
    }, headers=t2_headers)

    concise_prompt = "Classify sentiment: POSITIVE or NEGATIVE."
    t2_sub = client.post(f"/api/v1/challenges/{challenge_id}/submissions", json={
        "prompt_text": concise_prompt,
        "explanation": "Extremely concise under 15 tokens"
    }, headers=t2_headers)

    assert t2_sub.status_code == 201
    t2_data = t2_sub.json()
    assert t2_data["constraint_violated"] is False
    assert t2_data["auto_score"] > 2.5 # Full unpenalized automated score scale
