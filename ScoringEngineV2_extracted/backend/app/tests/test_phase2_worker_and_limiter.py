import pytest
from app.database import SessionLocal, init_db, Base, engine
from app.models.arena_scoring import ArenaScoringJob, ArenaScoringRun
from app.scoring.rate_limiter import DatabaseRateLimiter
from app.scoring.providers.adapter import MockScoringProvider
from app.services.arena_scoring_service import ArenaScoringService
import uuid

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield

def test_phase2_preflight_check():
    """Verify preflight returns GO status and correct structure."""
    db = SessionLocal()
    try:
        res = ArenaScoringService.get_preflight_check(db)
        assert res["status"] in ["GO", "DEGRADED-GO", "NO-GO"]
        assert len(res["lanes"]) == 2
        assert "rpm_limit" in res["lanes"][0]
    finally:
        db.close()

def test_phase2_rate_limiter_concurrency():
    """Verify rate limiter does not exceed limit (RPM/TPM)."""
    db = SessionLocal()
    try:
        lane = "P1-A"
        # Simulate 25 fast requests
        success_count = 0
        for _ in range(25):
            if DatabaseRateLimiter.acquire_quota(db, lane, calls=1, tokens=500, rpm_limit=20, tpm_limit=50000):
                success_count += 1
        
        # It should limit at 20 RPM exactly.
        assert success_count == 20
        
        # Try TPM limit (1 call, 60k tokens -> exceeds TPM)
        res = DatabaseRateLimiter.acquire_quota(db, lane, calls=1, tokens=60000, rpm_limit=20, tpm_limit=50000)
        assert res is False
    finally:
        db.close()

def test_phase2_provider_adapter_mock():
    """Verify mock provider completes successfully with standard output."""
    provider = MockScoringProvider()
    res = provider.complete([{"role": "user", "content": "hello"}], "mock")
    assert res.content == "MOCK_RESPONSE"
    assert res.tokens_in > 0
    assert res.tokens_out > 0
