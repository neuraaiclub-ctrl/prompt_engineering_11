from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_negative_rbac_permissions():
    # Register regular participant
    client.post("/api/v1/auth/register", json={
        "name": "Regular User",
        "email": "regular@example.com",
        "password": "Password123!"
    })
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "regular@example.com",
        "password": "Password123!"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Participant attempting Admin Hackathon creation -> Expect 403 Forbidden
    create_hk = client.post("/api/v1/hackathons", json={"title": "Unauthorized Hackathon"}, headers=headers)
    assert create_hk.status_code == 403

    # 2. Participant attempting Admin Audit Log access -> Expect 403 Forbidden
    audit_resp = client.get("/api/v1/admin/audit-log", headers=headers)
    assert audit_resp.status_code == 403

    # 3. Participant attempting Role Grant -> Expect 403 Forbidden
    role_grant = client.post("/api/v1/users/some-id/roles", json={"role_name": "admin"}, headers=headers)
    assert role_grant.status_code == 403
