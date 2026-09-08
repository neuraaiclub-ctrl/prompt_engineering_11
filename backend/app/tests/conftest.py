import pytest
import os
from app.database import Base, engine

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

