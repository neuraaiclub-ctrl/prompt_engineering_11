import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_login_flow():
    email = "testparticipant@example.com"
    password = "SecurePassword123!"

    # 1. Register User
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Test Participant",
        "email": email,
        "password": password,
        "affiliation": "AI Lab"
    })
    assert reg_resp.status_code == 201
    assert reg_resp.json()["email"] == email

    # 2. Duplicate Registration -> Expect 409 Conflict
    dup_resp = client.post("/api/v1/auth/register", json={
        "name": "Test Participant",
        "email": email,
        "password": password
    })
    assert dup_resp.status_code == 409

    # 3. Login User
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token is not None

    # 4. Fetch Profile using Token
    profile_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile_resp.status_code == 200
    assert profile_resp.json()["name"] == "Test Participant"
