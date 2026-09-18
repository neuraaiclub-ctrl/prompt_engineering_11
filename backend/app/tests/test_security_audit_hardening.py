import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db, SessionLocal
from app.models.user import User, Role
from app.models.team import Team, TeamMember
from app.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    is_legacy_hash,
    create_access_token,
    revoke_token,
    is_token_revoked
)
from app.core.rate_limiter import check_rate_limit

client = TestClient(app)

def test_security_headers_present():
    """Verify HTTP security headers are injected on responses."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")

def test_cors_whitelist_enforced():
    """Verify allowed origins receive CORS headers and disallowed origins do not get credentials."""
    # Permitted origin
    resp_allowed = client.get("/", headers={"Origin": "http://127.0.0.1:5500"})
    assert resp_allowed.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"
    assert resp_allowed.headers.get("access-control-allow-credentials") == "true"

    # Disallowed origin
    resp_disallowed = client.get("/", headers={"Origin": "http://malicious-site.attacker.com"})
    assert resp_disallowed.headers.get("access-control-allow-origin") != "http://malicious-site.attacker.com"

def test_password_hashing_pbkdf2_and_legacy_compatibility():
    """Verify salted PBKDF2 hashing, random salts, and legacy hash verification."""
    password = "Secur3P@ssw0rd!2026"
    
    # 1. PBKDF2 generation and format
    h1 = hash_password(password)
    assert h1.startswith("pbkdf2_sha256$100000$")
    assert not is_legacy_hash(h1)

    # 2. Salt uniqueness (two hashes of same password must not match)
    h2 = hash_password(password)
    assert h1 != h2

    # 3. Constant-time verification
    assert verify_password(password, h1) is True
    assert verify_password("WrongPassword", h1) is False

    # 4. Backward compatibility with legacy SHA-256 hash
    legacy_salted = f"{settings.SECRET_KEY}:{password}"
    import hashlib
    legacy_hash = hashlib.sha256(legacy_salted.encode("utf-8")).hexdigest()
    assert is_legacy_hash(legacy_hash) is True
    assert verify_password(password, legacy_hash) is True
    assert verify_password("WrongPassword", legacy_hash) is False

def test_transparent_password_hash_upgrade_on_login():
    """Verify legacy SHA-256 password hash is transparently upgraded to PBKDF2 on login."""
    db: Session = SessionLocal()
    import uuid, hashlib
    user_email = f"legacy_{uuid.uuid4().hex[:6]}@neura.io"
    password = "LegacyPassword123!"
    legacy_hash = hashlib.sha256(f"{settings.SECRET_KEY}:{password}".encode("utf-8")).hexdigest()

    user = User(
        name="Legacy User",
        email=user_email,
        password_hash=legacy_hash,
        status="active"
    )
    db.add(user)
    db.flush()
    db.add(Role(user_id=user.id, name="participant"))
    db.commit()
    user_id = user.id
    db.close()

    # Login with legacy credentials
    login_resp = client.post("/api/v1/auth/login", json={
        "email": user_email,
        "password": password
    })
    assert login_resp.status_code == 200

    # Verify user record has now upgraded to PBKDF2
    db2: Session = SessionLocal()
    updated_user = db2.query(User).filter(User.id == user_id).first()
    assert updated_user is not None
    assert updated_user.password_hash.startswith("pbkdf2_sha256$100000$")
    assert verify_password(password, updated_user.password_hash) is True
    db2.close()

def test_token_revocation_on_logout():
    """Verify that logging out revokes the access token and blocks further access."""
    email = f"logout_test_{int(time.time())}@neura.io"
    pwd = "ValidPassword123!"

    from app.tests.conftest import create_test_user
    create_test_user(email, pwd, name="Logout Tester", roles=["participant"])

    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200
    token = login.json()["access_token"]

    # Verify token works
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200

    # Logout with token
    logout_resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Token must now be rejected
    revoked_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_resp.status_code == 401

def test_team_detail_idor_bola_defense():
    """Verify non-members cannot see team invite_code or member email addresses."""
    # Seed admin login
    admin_login = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN1_EMAIL,
        "password": settings.ADMIN1_PASSWORD
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin registers Team Alpha
    suffix = str(int(time.time()))[-4:]
    t_alpha = client.post("/api/v1/teams/admin/register", json={
        "team_name": f"Alpha Team {suffix}",
        "college": "MIT",
        "members": ["Alice Alpha", "Alan Alpha"]
    }, headers=admin_headers)
    assert t_alpha.status_code == 201
    alpha_team_id = t_alpha.json()["team"]["id"]
    alice_email = t_alpha.json()["credentials"]["email"]
    alice_password = t_alpha.json()["credentials"]["password"]
    alice_login = client.post("/api/v1/auth/login", json={"email": alice_email, "password": alice_password})
    alice_token = alice_login.json()["access_token"]

    # Admin registers Team Beta
    t_beta = client.post("/api/v1/teams/admin/register", json={
        "team_name": f"Beta Team {suffix}",
        "college": "Stanford",
        "members": ["Bob Beta", "Betty Beta"]
    }, headers=admin_headers)
    assert t_beta.status_code == 201
    bob_email = t_beta.json()["credentials"]["email"]
    bob_password = t_beta.json()["credentials"]["password"]
    bob_login = client.post("/api/v1/auth/login", json={"email": bob_email, "password": bob_password})
    bob_token = bob_login.json()["access_token"]

    # 1. Bob (Team Beta) queries Team Alpha -> IDOR attempt!
    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    bob_view = client.get(f"/api/v1/teams/{alpha_team_id}", headers=bob_headers)
    assert bob_view.status_code == 200
    bob_data = bob_view.json()

    # Invite code MUST be None / masked for non-member
    assert bob_data.get("invite_code") is None
    # Member emails MUST be None / masked for non-member
    for m in bob_data.get("members", []):
        assert m.get("email") is None

    # 2. Alice (Team Alpha member) queries Team Alpha -> legitimately allowed
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    alice_view = client.get(f"/api/v1/teams/{alpha_team_id}", headers=alice_headers)
    assert alice_view.status_code == 200
    alice_data = alice_view.json()
    assert alice_data.get("invite_code") is not None
    assert any(m.get("email") is not None for m in alice_data.get("members", []))

    # 3. Admin queries Team Alpha -> legitimately allowed
    admin_view = client.get(f"/api/v1/teams/{alpha_team_id}", headers=admin_headers)
    assert admin_view.status_code == 200
    admin_data = admin_view.json()
    assert admin_data.get("invite_code") is not None

def test_rubric_scoring_discrete_validation():
    """Verify rubric scoring rejects non-rubric values (5, 15, 25, 101, -10, 999)."""
    judge_login = client.post("/api/v1/auth/login", json={
        "email": settings.JUDGE1_EMAIL,
        "password": settings.JUDGE1_PASSWORD
    })
    judge_token = judge_login.json()["access_token"]
    judge_headers = {"Authorization": f"Bearer {judge_token}"}

    # Test invalid score values
    invalid_values = [5.0, 15.0, 25.0, -10.0, 101.0, 999.0]
    for bad_val in invalid_values:
        resp = client.post("/api/v1/arena/judge/score", json={
            "submission_id": "dummy-sub-id",
            "clarity_score": bad_val,
            "specificity_score": 10.0,
            "context_score": 10.0
        }, headers=judge_headers)
        assert resp.status_code == 422, f"Expected 422 for invalid score {bad_val}"

def test_request_payload_size_limit():
    """Verify requests with Content-Length exceeding 2MB receive HTTP 413."""
    # 2.5 MB content length simulation
    oversized_length = str(2500000)
    resp = client.post(
        "/api/v1/auth/login",
        content=b"{}",
        headers={"Content-Length": oversized_length, "Content-Type": "application/json"}
    )
    assert resp.status_code == 413
    assert "2MB" in resp.text

def test_sliding_window_rate_limiter():
    """Verify rate limiter sliding window rejects excessive calls with HTTP 429."""
    test_key = f"test_rate_limit_{time.time()}"
    
    # 3 requests allowed in 2-second window
    for _ in range(3):
        allowed, _ = check_rate_limit(test_key, limit=3, window_seconds=2)
        assert allowed is True

    # 4th request must be throttled
    allowed, retry_after = check_rate_limit(test_key, limit=3, window_seconds=2)
    assert allowed is False
    assert retry_after >= 1

def test_sql_injection_payload_resilience():
    """Verify SQL injection payloads in auth and team query parameters are safely handled."""
    sqli_payloads = [
        "' OR '1'='1",
        "admin'--",
        "'; DROP TABLE users; --",
        "' UNION SELECT id, email, password_hash FROM users --"
    ]
    for payload in sqli_payloads:
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@neura.io",
            "password": payload
        })
        # Must fail safely with 401 Unauthorized or 422 Unprocessable Entity, NEVER 500
        assert resp.status_code in [401, 422]
