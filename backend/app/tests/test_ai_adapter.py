import pytest
from app.core.ai_adapter import AIProviderAdapter, MockLLMProvider, AIProviderError

def test_ai_adapter_normal_execution():
    AIProviderAdapter.use_mock = True
    AIProviderAdapter.mock_provider = MockLLMProvider()

    res = AIProviderAdapter.execute(
        user_prompt="Classify sentiment in one word: The system broke completely.",
        system_prompt=None,
        model="gpt-4o-mini"
    )
    assert res["status"] == "success"
    assert res["output_text"] == "NEGATIVE"
    assert res["token_count_prompt"] > 0
    assert res["token_count_output"] > 0
    assert res["latency_ms"] >= 0
    assert res["error"] is None

def test_ai_adapter_timeout_handling():
    mock = MockLLMProvider()
    mock.should_timeout = True
    AIProviderAdapter.mock_provider = mock

    res = AIProviderAdapter.execute(
        user_prompt="Slow long generation prompt",
        model="gpt-4o-mini"
    )
    assert res["status"] == "timeout"
    assert res["output_text"] is None
    assert "timed out" in res["error"].lower()

def test_ai_adapter_transient_error_single_retry():
    mock = MockLLMProvider()
    mock.should_fail_transient = True
    mock.attempts = 0
    AIProviderAdapter.mock_provider = mock

    # First attempt raises transient 503, second attempt succeeds
    res = AIProviderAdapter.execute(
        user_prompt="Summarize findings",
        model="gpt-4o-mini"
    )
    assert res["status"] == "success"
    assert mock.attempts == 2 # Proves it retried exactly once
    assert res["output_text"] is not None

def test_ai_adapter_content_safety_rejection_no_retry():
    mock = MockLLMProvider()
    mock.should_fail_safety = True
    mock.attempts = 0
    AIProviderAdapter.mock_provider = mock

    # Content safety errors must NEVER be retried
    res = AIProviderAdapter.execute(
        user_prompt="Dangerous unsafe input",
        model="gpt-4o-mini"
    )
    assert res["status"] == "error"
    assert mock.attempts == 1 # Proves it did NOT retry
    assert "safety filters" in res["error"].lower()
