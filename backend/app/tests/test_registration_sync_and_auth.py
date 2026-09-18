import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, Role
from app.models.registration import Registration
from app.models.team import Team, TeamMember
from app.core.security import hash_password

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    db = SessionLocal()
    # Ensure seeded admin account exists and is clean
    admin = db.query(User).filter(User.email == "admin1@neura.io").first()
    if not admin:
        admin = User(
            name="Admin Vance",
            email="admin1@neura.io",
            password_hash=hash_password("NeuraAdmin2026!Alpha"),
            status="active"
        )
        db.add(admin)
        db.flush()
        db.add(Role(user_id=admin.id, name="admin"))
        db.commit()
    yield
    db.close()

def get_admin_token():
    resp = client.post("/api/v1/auth/login", json={"email": "admin1@neura.io", "password": "NeuraAdmin2026!Alpha"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_public_registration_disabled():
    """FR-AUTH-01: Public direct participant registration must be disabled with 403 Forbidden."""
    resp = client.post("/api/v1/auth/register", json={
        "name": "Unauthorized User",
        "email": "unauthorized@example.com",
        "password": "Password123!"
    })
    assert resp.status_code == 403
    assert "detail" in resp.json()
    assert "official registration form" in resp.json()["detail"].lower()

def test_csv_import_and_idempotent_sync():
    """FR-SYNC-01: Admin can upload CSV file and idempotently sync registration records."""
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    csv_content = (
        "Registration ID,Team Name,Participant Name,Email,College\n"
        "REG-SA-101,Quantum Hackers,Alice Smith,alice.sa@quantum.io,MIT\n"
        "REG-SA-102,Quantum Hackers,Bob Jones,bob.sa@quantum.io,MIT\n"
    )
    file_tuple = ("registrations.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")

    resp = client.post("/api/v1/admin/registrations/import", files={"file": file_tuple}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["created"] == 2
    assert data["invalid"] == 0

    # Repeat import to verify idempotency
    file_tuple_2 = ("registrations.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    resp2 = client.post("/api/v1/admin/registrations/import", files={"file": file_tuple_2}, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["created"] == 0
    assert data2["unchanged"] == 2

def test_registration_verification_and_provisioning():
    """FR-ADMIN-01: Admin can verify registration and provision runtime credentials."""
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Import single record first
    csv_content = "Registration ID,Team Name,Participant Name,Email,College\nREG-SA-201,Cyber Knights,Charlie Brown,charlie.sa@cyber.io,Stanford\n"
    file_tuple = ("registrations.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    client.post("/api/v1/admin/registrations/import", files={"file": file_tuple}, headers=headers)

    # Get registrations list
    list_resp = client.get("/api/v1/admin/registrations", headers=headers)
    assert list_resp.status_code == 200
    regs = list_resp.json()
    target_reg = next(r for r in regs if r["email"] == "charlie.sa@cyber.io")
    assert target_reg["registration_status"] == "PENDING"


    # Verify registration
    verify_resp = client.post(f"/api/v1/admin/registrations/{target_reg['id']}/verify", headers=headers)
    assert verify_resp.status_code == 200
    ver_data = verify_resp.json()
    assert ver_data["registration_status"] == "VERIFIED"
    assert ver_data["account_status"] == "ACTIVE"
    assert ver_data["team_id"] is not None
    assert ver_data["user_id"] is not None

def test_imported_user_login():
    """FR-AUTH-02: Authenticate imported and verified participant."""
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Provision user credentials
    csv_content = "Registration ID,Team Name,Participant Name,Email,College\nREG-301,Data Dynamos,Diana Prince,diana@datadynamos.io,Berkeley\n"
    file_tuple = ("registrations.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    client.post("/api/v1/admin/registrations/import", files={"file": file_tuple}, headers=headers)

    regs = client.get("/api/v1/admin/registrations", headers=headers).json()
    target = next(r for r in regs if r["email"] == "diana@datadynamos.io")

    prov_resp = client.post(f"/api/v1/admin/registrations/{target['id']}/provision", headers=headers)
    assert prov_resp.status_code == 200
    prov_data = prov_resp.json()
    temp_pwd = prov_data["temporary_password"]

    # Login with provisioned credentials
    login_resp = client.post("/api/v1/auth/login", json={"email": "diana@datadynamos.io", "password": temp_pwd})
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == "diana@datadynamos.io"
    assert login_data["user"]["team_id"] is not None

def test_unverified_or_disabled_login_rejected():
    """FR-AUTH-03: Login for unverified or disabled accounts must be rejected."""
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Import record (status PENDING)
    csv_content = "Registration ID,Team Name,Participant Name,Email,College\nREG-401,Shadow Ops,Eve Adams,eve@shadow.io,Harvard\n"
    file_tuple = ("registrations.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    client.post("/api/v1/admin/registrations/import", files={"file": file_tuple}, headers=headers)

    # Attempt login on unverified/unprovisioned user
    login_resp = client.post("/api/v1/auth/login", json={"email": "eve@shadow.io", "password": "Password123!"})
    assert login_resp.status_code in [401, 403]
    assert "Invalid credentials" in login_resp.json()["detail"]
