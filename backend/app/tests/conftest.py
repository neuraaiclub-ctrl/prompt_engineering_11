import pytest
import os
from app.database import Base, engine, SessionLocal
from app.models.user import User, Role
from app.core.security import hash_password

@pytest.fixture(autouse=True, scope="module")
def setup_test_db():
    """Drop and recreate all tables for a clean test suite execution."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.database import seed_initial_data
    seed_initial_data()
    yield

@pytest.fixture(autouse=True)
def reset_mock_provider():
    """Reset AI provider mock before and after each test."""
    from app.core.ai_adapter import AIProviderAdapter, MockLLMProvider
    AIProviderAdapter.mock_provider = MockLLMProvider()
    yield
    AIProviderAdapter.mock_provider = MockLLMProvider()

def create_test_user(email: str, password: str = "Password123!", name: str = "Test User", roles: list = None):
    if roles is None:
        roles = ["participant"]
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if not existing:
            u = User(
                name=name,
                email=email.lower(),
                password_hash=hash_password(password),
                affiliation="Test Affiliation",
                status="active"
            )
            db.add(u)
            db.flush()
            for r in roles:
                db.add(Role(user_id=u.id, name=r))
            db.commit()
            db.refresh(u)
            return u
        return existing
    finally:
        db.close()
