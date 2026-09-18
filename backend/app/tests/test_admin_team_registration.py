import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def get_admin_headers():
    # Authenticate using seeded Admin 1
    res = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN1_EMAIL,
        "password": settings.ADMIN1_PASSWORD
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert "admin" in res.json()["user"]["roles"]
    return {"Authorization": f"Bearer {token}"}

def test_seeded_admin_and_judge_accounts():
    """Verify all three Admin accounts and Judge account authenticate properly."""
    # Admin 1
    res1 = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN1_EMAIL,
        "password": settings.ADMIN1_PASSWORD
    })
    assert res1.status_code == 200
    assert "admin" in res1.json()["user"]["roles"]

    # Admin 2
    res2 = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN2_EMAIL,
        "password": settings.ADMIN2_PASSWORD
    })
    assert res2.status_code == 200
    assert "admin" in res2.json()["user"]["roles"]

    # Admin 3
    res3 = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN3_EMAIL,
        "password": settings.ADMIN3_PASSWORD
    })
    assert res3.status_code == 200
    assert "admin" in res3.json()["user"]["roles"]

    # Judge 1
    res_judge = client.post("/api/v1/auth/login", json={
        "email": settings.JUDGE1_EMAIL,
        "password": settings.JUDGE1_PASSWORD
    })
    assert res_judge.status_code == 200
    assert "judge" in res_judge.json()["user"]["roles"]

def test_admin_register_team_success():
    """Admin successfully registers team with college, members, and receives credentials."""
    headers = get_admin_headers()
    payload = {
        "team_name": "Cyber Mavericks",
        "college": "MMCOE Pune",
        "members": ["Rohan Sharma", "Ananya Deshmukh", "Vikram Joshi"]
    }

    res = client.post("/api/v1/teams/admin/register", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["team"]["name"] == "Cyber Mavericks"
    assert data["team"]["college"] == "MMCOE Pune"
    assert len(data["team"]["members"]) == 3
    assert "@neura.io" in data["credentials"]["email"]
    assert len(data["credentials"]["password"]) >= 10

    # Test that the team leader can immediately login with the generated credentials
    login_res = client.post("/api/v1/auth/login", json={
        "email": data["credentials"]["email"],
        "password": data["credentials"]["password"]
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "participant" in login_data["user"]["roles"]

def test_admin_register_team_forbidden_for_non_admin():
    """Non-admin (participant) calling admin register receives 403 Forbidden."""
    admin_headers = get_admin_headers()
    t_res = client.post("/api/v1/teams/admin/register", json={
        "team_name": "Norm Team",
        "college": "Zion",
        "members": ["Normal Participant"]
    }, headers=admin_headers)
    creds = t_res.json()["credentials"]
    token = client.post("/api/v1/auth/login", json={
        "email": creds["email"],
        "password": creds["password"]
    }).json()["access_token"]

    p_headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "team_name": "Hacker Team",
        "college": "Unknown",
        "members": ["Hacker 1"]
    }

    res = client.post("/api/v1/teams/admin/register", json=payload, headers=p_headers)
    assert res.status_code == 403

def test_admin_register_team_duplicate_team_name():
    """Registering with an already existing team name returns 409 Conflict."""
    headers = get_admin_headers()
    payload = {
        "team_name": "Unique Mavericks",
        "college": "COEP Pune",
        "members": ["Aarav Patel", "Sanya Mir"]
    }

    res1 = client.post("/api/v1/teams/admin/register", json=payload, headers=headers)
    assert res1.status_code == 201

    # Attempt to register again with same team name
    res2 = client.post("/api/v1/teams/admin/register", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()

def test_admin_register_team_duplicate_member_in_same_team():
    """Entering the same member name twice in one team returns 422."""
    headers = get_admin_headers()
    payload = {
        "team_name": "Dupe Member Team",
        "college": "IIT Bombay",
        "members": ["Karan Mehta", "karan mehta"] # duplicate case-insensitive
    }

    res = client.post("/api/v1/teams/admin/register", json=payload, headers=headers)
    assert res.status_code == 422
    assert "duplicate member" in res.json()["detail"].lower()

def test_admin_register_team_member_already_in_another_team():
    """A member already registered in another participating team cannot be registered again."""
    headers = get_admin_headers()
    team1_payload = {
        "team_name": "First Alpha Team",
        "college": "VJTI Mumbai",
        "members": ["Sunil Gavaskar", "Kapil Dev"]
    }
    res1 = client.post("/api/v1/teams/admin/register", json=team1_payload, headers=headers)
    assert res1.status_code == 201

    team2_payload = {
        "team_name": "Second Beta Team",
        "college": "BITS Pilani",
        "members": ["Sunil Gavaskar", "Rahul Dravid"] # Sunil already in team 1
    }
    res2 = client.post("/api/v1/teams/admin/register", json=team2_payload, headers=headers)
    assert res2.status_code == 409
    assert "already associated with another participating team" in res2.json()["detail"].lower()

def test_admin_register_team_validation_limits():
    """Blank names, empty college, or team size < 1 or > 4 returns 422."""
    headers = get_admin_headers()

    # Empty team name
    res1 = client.post("/api/v1/teams/admin/register", json={
        "team_name": "",
        "college": "Test College",
        "members": ["Member 1"]
    }, headers=headers)
    assert res1.status_code == 422

    # Empty college
    res2 = client.post("/api/v1/teams/admin/register", json={
        "team_name": "Valid Name",
        "college": "",
        "members": ["Member 1"]
    }, headers=headers)
    assert res2.status_code == 422

    # More than 4 members
    res3 = client.post("/api/v1/teams/admin/register", json={
        "team_name": "Too Many Members",
        "college": "Test College",
        "members": ["M1", "M2", "M3", "M4", "M5"]
    }, headers=headers)
    assert res3.status_code == 422

def test_get_all_teams_admin():
    """Admin can query all registered teams with member counts and college."""
    headers = get_admin_headers()
    res = client.get("/api/v1/teams/admin/all", headers=headers)
    assert res.status_code == 200
    teams = res.json()
    assert isinstance(teams, list)
    assert len(teams) > 0
    first = teams[0]
    assert "college" in first
    assert "members" in first
    assert "login_email" in first
    # Passwords must NOT be in the table list
    assert "password" not in first
