import pytest
from app.scoring.checks import run_deterministic_check
from app.scoring.harness import ScoringHarness
from app.scoring.providers.adapter import MockScoringProvider

def test_json_valid_check():
    assert run_deterministic_check({"type": "json_valid"}, '{"key": "value"}') is True
    assert run_deterministic_check({"type": "json_valid"}, '```json\n{"key": "value"}\n```') is True
    assert run_deterministic_check({"type": "json_valid"}, '{invalid: json}') is False

def test_max_words_check():
    assert run_deterministic_check({"type": "max_words", "value": 5}, "one two three four five") is True
    assert run_deterministic_check({"type": "max_words", "value": 4}, "one two three four five") is False

def test_regex_checks():
    assert run_deterministic_check({"type": "regex_match", "pattern": "hello"}, "Hello world") is True
    assert run_deterministic_check({"type": "regex_absent", "pattern": "hello"}, "Hi world") is True
    assert run_deterministic_check({"type": "regex_absent", "pattern": "hello"}, "Hello world") is False

def test_equals_field_check():
    json_str = '{"user": {"name": "alice"}, "id": 123}'
    assert run_deterministic_check({"type": "equals_field", "path": "user.name", "value": "alice"}, json_str) is True
    assert run_deterministic_check({"type": "equals_field", "path": "id", "value": 123}, json_str) is True
    assert run_deterministic_check({"type": "equals_field", "path": "user.name", "value": "bob"}, json_str) is False
    assert run_deterministic_check({"type": "equals_field", "path": "missing", "value": "val"}, json_str) is False

def test_l2_execution_harness():
    spec = {
        "test_cases": [
            {
                "id": "t1",
                "input": "test input",
                "checks": [{"type": "regex_match", "pattern": "MOCK_RESPONSE"}]
            },
            {
                "id": "t2",
                "input": "test input 2",
                "checks": [{"type": "json_valid"}] # mock doesn't return JSON unless format is specified, so this will fail
            }
        ]
    }
    
    provider = MockScoringProvider()
    harness = ScoringHarness(provider)
    result = harness.evaluate_submission_l2("system prompt", spec)
    
    scores = result["dimension_scores"]
    # 1 pass (t1), 1 fail (t2) -> 50% pass rate -> 10.0 score
    assert scores["clarity"] == 10.0
    assert result["test_results"][0]["result"]["passed"] is True
    assert result["test_results"][1]["result"]["passed"] is False
