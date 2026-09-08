import pytest
from app.core.validators import (
    validate_max_tokens,
    validate_zero_shot,
    validate_one_shot,
    validate_no_system_prompt,
    validate_generalize_unseen_inputs,
    validate_valid_json_always
)

def test_validate_max_tokens():
    short_prompt = "Classify sentiment as POSITIVE or NEGATIVE."
    valid, msg = validate_max_tokens(short_prompt, max_tokens=15)
    assert valid is True
    assert "Compliant" in msg

    long_prompt = "You are a professional sentiment analysis system designed to read incoming customer feedback and output exactly one label." * 4
    invalid, msg = validate_max_tokens(long_prompt, max_tokens=15)
    assert invalid is False
    assert "Violated" in msg

def test_validate_zero_shot():
    clean_prompt = "Translate this English sentence to Spanish."
    valid, msg = validate_zero_shot(clean_prompt)
    assert valid is True
    assert "Compliant" in msg

    few_shot_prompt = "Classify sentiment.\nExample: 'Good service' -> POSITIVE\nNow classify: "
    invalid, msg = validate_zero_shot(few_shot_prompt)
    assert invalid is False
    assert "Violated" in msg

def test_validate_one_shot():
    one_shot = "Extract dates.\nExample: 'Met on Jan 4' -> '2024-01-04'\nText: "
    valid, msg = validate_one_shot(one_shot)
    assert valid is True
    assert "Compliant" in msg

    zero_shot = "Extract dates from this text."
    invalid, msg = validate_one_shot(zero_shot)
    assert invalid is False
    assert "Violated" in msg

    two_shot = "Extract dates.\nExample 1: 'Jan 4' -> '2024-01-04'\nExample 2: 'May 10' -> '2024-05-10'"
    invalid2, msg2 = validate_one_shot(two_shot)
    assert invalid2 is False
    assert "Violated" in msg2

def test_validate_no_system_prompt():
    valid, msg = validate_no_system_prompt(None)
    assert valid is True

    valid_empty, _ = validate_no_system_prompt("   ")
    assert valid_empty is True

    invalid, msg = validate_no_system_prompt("You are a helpful assistant.")
    assert invalid is False
    assert "Violated" in msg

def test_validate_generalize_unseen_inputs():
    hidden_inputs = [
        "Unseen customer record #94829 from Tokyo branch reported zero errors in payment gateway."
    ]
    general_prompt = "Analyze bank transaction statements and classify fraud risk."
    valid, msg = validate_generalize_unseen_inputs(general_prompt, hidden_inputs)
    assert valid is True

    cheating_prompt = "If the text is 'Unseen customer record #94829 from Tokyo branch reported zero errors in payment gateway.' output NORMAL."
    invalid, msg = validate_generalize_unseen_inputs(cheating_prompt, hidden_inputs)
    assert invalid is False
    assert "Violated" in msg

def test_validate_valid_json_always():
    valid_json = '{"status": "ok", "items": [1, 2, 3]}'
    valid, msg = validate_valid_json_always(valid_json)
    assert valid is True
    assert "Compliant" in msg

    invalid_json = 'This is not json: {key: value}'
    invalid, msg = validate_valid_json_always(invalid_json)
    assert invalid is False
    assert "Violated" in msg

    empty_json = ""
    invalid_empty, _ = validate_valid_json_always(empty_json)
    assert invalid_empty is False
