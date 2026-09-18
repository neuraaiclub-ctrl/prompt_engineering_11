from fastapi.testclient import TestClient
from app.main import app
from app.tests.conftest import create_test_user

client = TestClient(app)

def test_server_authoritative_timer():
    create_test_user("timeradmin@example.com", "Pass123!", name="Timer Admin", roles=["admin"])

    admin_login = client.post("/api/v1/auth/login", json={"email": "timeradmin@example.com", "password": "Pass123!"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create Hackathon & 10-second Round
    hk = client.post("/api/v1/hackathons", json={"title": "Timer Test Hackathon"}, headers=admin_headers).json()
    rnd = client.post(f"/api/v1/hackathons/{hk['id']}/rounds", json={"type": "round1_fix_the_prompt", "duration_seconds": 10}, headers=admin_headers).json()

    # Pre-start Timer Check
    t0 = client.get(f"/api/v1/rounds/{rnd['id']}/timer").json()
    assert t0["remaining_seconds"] == 10
    assert t0["is_expired"] is False

    # Start Round
    client.post(f"/api/v1/rounds/{rnd['id']}/start", headers=admin_headers)

    # Fetch Timer immediately
    t1 = client.get(f"/api/v1/rounds/{rnd['id']}/timer").json()
    assert t1["status"] == "active"
    assert t1["remaining_seconds"] <= 10
    assert t1["server_time"] is not None
