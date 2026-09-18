from fastapi.testclient import TestClient
from app.main import app
from app.tests.conftest import create_test_user

client = TestClient(app)

def test_team_lifecycle_and_locks():
    # 1. Admin setup hackathon & round
    create_test_user("admin@example.com", "Pass123!", name="Admin User", roles=["admin"])
    
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "Pass123!"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    hk = client.post("/api/v1/hackathons", json={"title": "Test Hackathon 2026"}, headers=admin_headers).json()
    rnd = client.post(f"/api/v1/hackathons/{hk['id']}/rounds", json={"type": "round1_fix_the_prompt"}, headers=admin_headers).json()

    # 2. Register User 1 & Create Team
    create_test_user("u1@example.com", "Pass123!", name="User 1", roles=["participant"])
    u1_token = client.post("/api/v1/auth/login", json={"email": "u1@example.com", "password": "Pass123!"}).json()["access_token"]
    u1_headers = {"Authorization": f"Bearer {u1_token}"}

    team = client.post("/api/v1/teams", json={"name": "Neural Ninjas", "hackathon_id": hk["id"]}, headers=u1_headers).json()
    assert team["name"] == "Neural Ninjas"
    invite_code = team["invite_code"]

    # 3. Attempting to create second team when already on one -> Expect 409 Conflict
    create_2nd = client.post("/api/v1/teams", json={"name": "Second Team", "hackathon_id": hk["id"]}, headers=u1_headers)
    assert create_2nd.status_code == 409

    # 4. User 2 joins team via invite code
    create_test_user("u2@example.com", "Pass123!", name="User 2", roles=["participant"])
    u2_token = client.post("/api/v1/auth/login", json={"email": "u2@example.com", "password": "Pass123!"}).json()["access_token"]
    u2_headers = {"Authorization": f"Bearer {u2_token}"}

    join_res = client.post("/api/v1/teams/join", json={"invite_code": invite_code}, headers=u2_headers)
    assert join_res.status_code == 200

    # 5. User 2 attempting to join another team -> Expect 409 Conflict
    join_another = client.post("/api/v1/teams/join", json={"invite_code": "NR-9999"}, headers=u2_headers)
    assert join_another.status_code == 409

    # 6. Admin starts round -> Locks teams
    start_rnd = client.post(f"/api/v1/rounds/{rnd['id']}/start", headers=admin_headers)
    assert start_rnd.status_code == 200

    # 7. User 3 attempting to join team after lock -> Expect 423 Locked
    create_test_user("u3@example.com", "Pass123!", name="User 3", roles=["participant"])
    u3_token = client.post("/api/v1/auth/login", json={"email": "u3@example.com", "password": "Pass123!"}).json()["access_token"]
    u3_headers = {"Authorization": f"Bearer {u3_token}"}

    join_locked = client.post("/api/v1/teams/join", json={"invite_code": invite_code}, headers=u3_headers)
    assert join_locked.status_code == 423
