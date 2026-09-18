import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_direct_registration_disabled_returns_403():
    """
    Public self-registration must be disabled and return 403 Forbidden.
    """
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Public Registrant",
        "email": "public@example.com",
        "password": "Password123!"
    })
    assert reg_resp.status_code == 403
    assert "managed through the official registration form" in reg_resp.json()["detail"]

def test_imported_participant_provision_and_login_flow():
    """
    Tests full imported participant lifecycle: CSV import -> Admin verification -> Account provisioning -> Participant login.
    """
    # 1. Admin Login
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin1@neura.io",
        "password": "NeuraAdmin2026!Alpha"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Import CSV Registration Payload
    csv_content = (
        "Timestamp,Registration ID,Team Name,Member 1 Name,Member 1 Email,College,Course,Year\n"
        "2026-09-17 10:00:00,REG-9901,Quantum Hackers,Alice Smith,alice.quantum@example.com,MIT,CS,2026\n"
    )

    import_resp = client.post(
        "/api/v1/admin/registrations/import",
        files={"file": ("registrations.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=admin_headers
    )
    assert import_resp.status_code == 200
    report = import_resp.json()
    assert report["created"] == 1

    # 3. Get Registration List
    list_resp = client.get("/api/v1/admin/registrations", headers=admin_headers)
    assert list_resp.status_code == 200
    regs = list_resp.json()
    reg = next(r for r in regs if r["email"] == "alice.quantum@example.com")
    assert reg["team_name"] == "Quantum Hackers"

    # 4. Provision Account & Generate Password
    prov_resp = client.post(f"/api/v1/admin/registrations/{reg['id']}/provision", headers=admin_headers)
    assert prov_resp.status_code == 200
    creds = prov_resp.json()["credentials"]
    assert creds["email"] == "alice.quantum@example.com"
    password = creds["password"]

    # 5. Login as Provisioned Participant
    participant_login = client.post("/api/v1/auth/login", json={
        "email": "alice.quantum@example.com",
        "password": password
    })
    assert participant_login.status_code == 200
    p_token = participant_login.json()["access_token"]
    assert p_token is not None

    # 6. Verify User Profile
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {p_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice.quantum@example.com"
