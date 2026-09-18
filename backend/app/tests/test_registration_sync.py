import pytest
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_admin_headers():
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin1@neura.io",
        "password": "NeuraAdmin2026!Alpha"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_csv_import_normalization_and_idempotent_sync():
    """
    Tests importing CSV registrations, normalization, idempotent upsert on re-import,
    and missing source row flagging.
    """
    admin_headers = get_admin_headers()

    csv_data_1 = (
        "Timestamp,Registration ID,Team Name,Member 1 Name,Member 1 Email,College,Course,Year\n"
        "2026-09-17 10:00:00,REG-101,Cyber Avengers,Tony Stark,tony.stark@stark.io,MIT,CS,2026\n"
        "2026-09-17 10:01:00,REG-102,Cyber Avengers,Steve Rogers,steve.rogers@avengers.io,MIT,CS,2026\n"
    )

    # 1. Initial Import
    res1 = client.post(
        "/api/v1/admin/registrations/import",
        files={"file": ("batch1.csv", csv_data_1.encode("utf-8"), "text/csv")},
        headers=admin_headers
    )
    assert res1.status_code == 200
    r1 = res1.json()
    assert r1["created"] == 2
    assert r1["updated"] == 0

    # 2. Idempotent Re-Import (Same Data) -> 0 created, 2 unchanged
    res2 = client.post(
        "/api/v1/admin/registrations/import",
        files={"file": ("batch1.csv", csv_data_1.encode("utf-8"), "text/csv")},
        headers=admin_headers
    )
    assert res2.status_code == 200
    r2 = res2.json()
    assert r2["created"] == 0
    assert r2["unchanged"] == 2

    # 3. Import payload with missing row -> record flagged for review, not deleted
    csv_data_2 = (
        "Timestamp,Registration ID,Team Name,Member 1 Name,Member 1 Email,College,Course,Year\n"
        "2026-09-17 10:00:00,REG-101,Cyber Avengers,Tony Stark,tony.stark@stark.io,MIT,CS,2026\n"
    )
    res3 = client.post(
        "/api/v1/admin/registrations/import",
        files={"file": ("batch2.csv", csv_data_2.encode("utf-8"), "text/csv")},
        headers=admin_headers
    )
    assert res3.status_code == 200
    r3 = res3.json()
    assert r3["flagged"] >= 1

    # Verify steer.rogers record still exists and is flagged
    list_res = client.get("/api/v1/admin/registrations", headers=admin_headers)
    regs = list_res.json()
    steve = next(r for r in regs if r["email"] == "steve.rogers@avengers.io")
    assert steve["flagged_for_review"] is True

def test_registration_lifecycle_verify_reject_disable():
    """
    Tests registration status state transitions: Verify, Reject, Disable.
    """
    admin_headers = get_admin_headers()

    csv_data = (
        "Timestamp,Registration ID,Team Name,Participant Name,Email,College\n"
        "2026-09-17 11:00:00,REG-201,Matrix Team,Neo,neo@matrix.io,Zion Inst\n"
        "2026-09-17 11:01:00,REG-202,Matrix Team,Trinity,trinity@matrix.io,Zion Inst\n"
    )

    client.post(
        "/api/v1/admin/registrations/import",
        files={"file": ("matrix.csv", csv_data.encode("utf-8"), "text/csv")},
        headers=admin_headers
    )

    list_res = client.get("/api/v1/admin/registrations", headers=admin_headers)
    neo_reg = next(r for r in list_res.json() if r["email"] == "neo@matrix.io")
    trinity_reg = next(r for r in list_res.json() if r["email"] == "trinity@matrix.io")

    # Verify Neo
    v_res = client.post(f"/api/v1/admin/registrations/{neo_reg['id']}/verify", headers=admin_headers)
    assert v_res.status_code == 200
    assert v_res.json()["registration_status"] == "VERIFIED"

    # Reject Trinity
    r_res = client.post(f"/api/v1/admin/registrations/{trinity_reg['id']}/reject", headers=admin_headers)
    assert r_res.status_code == 200
    assert r_res.json()["registration_status"] == "REJECTED"

    # Try login as rejected user -> 401/403 Forbidden
    login_rej = client.post("/api/v1/auth/login", json={"email": "trinity@matrix.io", "password": "Pass123!"})
    assert login_rej.status_code in [401, 403]

def test_admin_registration_export_csv():
    """
    Tests CSV export endpoint.
    """
    admin_headers = get_admin_headers()
    exp_res = client.get("/api/v1/admin/registrations/export", headers=admin_headers)
    assert exp_res.status_code == 200
    assert "text/csv" in exp_res.headers["content-type"]
    assert "Registration ID" in exp_res.text

def test_non_admin_forbidden_registration_endpoints():
    """
    Ensures non-admin roles are forbidden from accessing registration sync/admin APIs.
    """
    # Create non-admin participant headers
    csv_data = "Timestamp,Registration ID,Team Name,Participant Name,Email\n2026-09-17,REG-99,Team Test,Test User,user99@test.io\n"
    client.post("/api/v1/admin/registrations/import", files={"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")}, headers=get_admin_headers())
    reg_list = client.get("/api/v1/admin/registrations", headers=get_admin_headers()).json()
    reg = next(r for r in reg_list if r["email"] == "user99@test.io")
    prov = client.post(f"/api/v1/admin/registrations/{reg['id']}/provision", headers=get_admin_headers()).json()

    p_login = client.post("/api/v1/auth/login", json={"email": "user99@test.io", "password": prov["credentials"]["password"]})
    p_token = p_login.json()["access_token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}

    # Participant attempt to access admin registrations list -> 403
    forbidden_list = client.get("/api/v1/admin/registrations", headers=p_headers)
    assert forbidden_list.status_code == 403

    # Participant attempt to trigger sync -> 403
    forbidden_sync = client.post("/api/v1/admin/registrations/sync", headers=p_headers)
    assert forbidden_sync.status_code == 403
