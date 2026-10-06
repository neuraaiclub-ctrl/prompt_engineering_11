import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.main import app
from app.database import SessionLocal
from app.models.arena import ArenaConfig, ArenaSubmission
from app.models.team import Team, TeamMember
from app.models.user import User, Role
from app.core.security import create_access_token, hash_password
from app.config import settings

client = TestClient(app)

def _get_judge_token():
    return client.post("/api/v1/auth/login", json={
        "email": settings.JUDGE1_EMAIL, "password": settings.JUDGE1_PASSWORD
    }).json()["access_token"]

def _make_team(db, name, email, code):
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(name=name, email=email, password_hash=hash_password("Pass123!"), affiliation="X", status="active")
        db.add(u); db.flush()
        db.add(Role(user_id=u.id, name="participant"))
    
    t = db.query(Team).filter(Team.invite_code == code).first()
    if not t:
        t = Team(hackathon_id="hk-2026", name=name, college="X", invite_code=code, status="forming")
        db.add(t); db.flush()
        db.add(TeamMember(team_id=t.id, user_id=u.id, role="leader"))
    db.commit()
    return create_access_token({"sub": u.id, "email": u.email, "roles": ["participant"]})

@pytest.fixture(autouse=True)
def reset_arena(setup_test_db):
    db = SessionLocal()
    try:
        conf = db.query(ArenaConfig).filter(ArenaConfig.id == "default-arena-config").first()
        if conf:
            conf.status = "waiting"
            conf.started_at = None
            conf.ended_at = None
            conf.results_released_at = None
            conf.marks_per_challenge = 100
        db.commit()
    finally:
        db.close()

def test_p0_defect_1_score_scale_and_defect_2_schema_compat():
    """Defect #1 (marks=100) and Defect #2 (schema compat for output_format/constraints)."""
    db = SessionLocal()
    try:
        jt = _get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {jt}"})
        tok = _make_team(db, "P0 T1", "p01@neura.io", "P0-01")
        
        client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {tok}"})
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "A"*20}, headers={"Authorization": f"Bearer {tok}"})
        
        sub = db.query(ArenaSubmission).first()
        
        # Using output_format_score and constraints_score directly
        r = client.post("/api/v1/arena/judge/score", json={
            "submission_id": sub.id,
            "clarity_score": 20.0,
            "specificity_score": 20.0,
            "context_score": 20.0,
            "output_format_score": 20.0,
            "constraints_score": 20.0,
            "judge_feedback": "Great"
        }, headers={"Authorization": f"Bearer {jt}"})
        assert r.status_code == 200
        assert r.json()["total_score"] == 100.0
        
        # Test 500 max_score in report
        client.post("/api/v1/arena/end", headers={"Authorization": f"Bearer {jt}"})
        client.post("/api/v1/arena/release-results", headers={"Authorization": f"Bearer {jt}"})
        
        rpt = client.get("/api/v1/arena/report", headers={"Authorization": f"Bearer {tok}"})
        assert rpt.status_code == 200
        assert rpt.json()["max_score"] == 500
    finally:
        db.close()

def test_p0_defect_4_and_13_diagnosis_notes_and_1500_char_limit():
    """Defect #4 (diagnosis_notes saved) and Defect #13 (1500 max chars)."""
    db = SessionLocal()
    try:
        jt = _get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {jt}"})
        tok = _make_team(db, "P0 T2", "p02@neura.io", "P0-02")
        
        client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {tok}"})
        
        # Over 1500 limit
        r_fail = client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "A" * 1501}, headers={"Authorization": f"Bearer {tok}"})
        assert r_fail.status_code == 422
        
        # Valid with diagnosis_notes
        r = client.post("/api/v1/arena/submit-challenge", json={
            "prompt_text": "Valid prompt text here.",
            "diagnosis_notes": "We fixed the length."
        }, headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        
        sub = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == db.query(Team).filter(Team.invite_code=="P0-02").first().id).first()
        assert sub.diagnosis_notes == "We fixed the length."
    finally:
        db.close()

def test_p0_defect_6_judge_overview_contract():
    """Defect #6 (stats->metrics, ISO timestamps, is_evaluated)."""
    db = SessionLocal()
    try:
        jt = _get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {jt}"})
        tok = _make_team(db, "P0 T3", "p03@neura.io", "P0-03")
        
        client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {tok}"})
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "A"*20}, headers={"Authorization": f"Bearer {tok}"})
        
        # Log a security event
        client.post("/api/v1/arena/security-event", json={
            "event_type": "tab_switch",
            "client_metadata": {"browser": "test"}
        }, headers={"Authorization": f"Bearer {tok}"})
        
        r = client.get("/api/v1/arena/judge/overview", headers={"Authorization": f"Bearer {jt}"})
        assert r.status_code == 200
        data = r.json()
        
        # stats -> metrics
        assert "metrics" in data
        assert "stats" not in data
        
        assert "flagged_teams_count" in data["metrics"]
        
        # Check ISO timestamp and is_evaluated
        if data["submissions"]:
            sub = data["submissions"][0]
            assert "T" in sub["submitted_at"] # ISO-8601 indicator
            assert "is_evaluated" in sub
            assert "has_evaluated" not in sub
            
        if data["security_events"]:
            ev = data["security_events"][0]
            assert "T" in ev["timestamp"]
            assert "metadata" in ev # Mapped from client_metadata
    finally:
        db.close()

def test_p0_defect_7_and_8_state_machine_guards():
    """Defect #7 (no early release) and Defect #8 (no double start)."""
    jt = _get_judge_token()
    
    # Not completed yet, release should fail
    r_rel = client.post("/api/v1/arena/release-results", headers={"Authorization": f"Bearer {jt}"})
    assert r_rel.status_code == 400
    assert "completed" in r_rel.json()["detail"]
    
    # Start it
    client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {jt}"})
    
    # Try starting again -> should fail since not 'waiting'
    r_start2 = client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {jt}"})
    assert r_start2.status_code == 400
    assert "waiting" in r_start2.json()["detail"]

def test_p0_defect_11_my_results_leakage():
    """Defect #11 (/my-results securely gated during live)."""
    db = SessionLocal()
    try:
        jt = _get_judge_token()
        client.post("/api/v1/arena/start", json={"confirm": True}, headers={"Authorization": f"Bearer {jt}"})
        tok = _make_team(db, "P0 T4", "p04@neura.io", "P0-04")
        
        client.get("/api/v1/arena/my-challenge", headers={"Authorization": f"Bearer {tok}"})
        client.post("/api/v1/arena/submit-challenge", json={"prompt_text": "A"*20}, headers={"Authorization": f"Bearer {tok}"})
        
        sub = db.query(ArenaSubmission).first()
        client.post("/api/v1/arena/judge/score", json={
            "submission_id": sub.id,
            "clarity_score": 20.0, "specificity_score": 20.0, "context_score": 20.0,
            "output_format_score": 20.0, "constraints_score": 20.0
        }, headers={"Authorization": f"Bearer {jt}"})
        
        # It's still LIVE, results not released yet
        r = client.get("/api/v1/arena/my-results", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        data = r.json()
        
        # Should be masked
        assert data["results_released"] is False
        assert data["total_score"] is None
        assert data["challenges"] == []
    finally:
        db.close()
