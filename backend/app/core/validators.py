import re
import json
from typing import Tuple, Optional
from app.core.token_counter import count_tokens

def validate_max_tokens(prompt: str, max_tokens: int = 50) -> Tuple[bool, str]:
    tokens = count_tokens(prompt)
    if tokens <= max_tokens:
        return True, f"Compliant: {tokens} tokens is within limit of {max_tokens}"
    return False, f"Violated: {tokens} tokens exceeds limit of {max_tokens}"

def validate_zero_shot(prompt: str) -> Tuple[bool, str]:
    # Check for presence of examples (e.g. "Example:", "Input: ... Output:", "e.g.")
    example_patterns = [
        r'\bexample\s*\d*:',
        r'\binput:\s*.*?\boutput:',
        r'\bq:\s*.*?\ba:',
        r'\be\.g\.',
        r'\bsample\s*input'
    ]
    for pattern in example_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            return False, "Violated: Prompt contains one or more few-shot examples"
    return True, "Compliant: No examples found in prompt (zero-shot)"

def validate_one_shot(prompt: str) -> Tuple[bool, str]:
    # Must contain exactly one example
    example_matches = len(re.findall(r'\b(example\s*\d*|sample\s*input|e\.g\.|input\s*:)\b', prompt, re.IGNORECASE))
    if example_matches == 1 or "example:" in prompt.lower():
        # Check if there is a second example
        if prompt.lower().count("example") > 1 or prompt.lower().count("input:") > 1:
            return False, "Violated: Prompt contains more than one example"
        return True, "Compliant: Prompt contains exactly one example (one-shot)"
    return False, "Violated: Prompt must contain exactly one example"

def validate_no_system_prompt(system_prompt: Optional[str]) -> Tuple[bool, str]:
    if not system_prompt or not system_prompt.strip():
        return True, "Compliant: System prompt is empty (disabled)"
    return False, "Violated: System prompt was provided when forbidden"

def validate_generalize_unseen_inputs(prompt: str, test_inputs: list) -> Tuple[bool, str]:
    # Verifies prompt does not hardcode specific test answers or cheat on hidden inputs
    lower_prompt = prompt.lower()
    for item in test_inputs:
        # Check if full specific hidden sentence was pasted directly into prompt
        if len(item) > 20 and item.lower() in lower_prompt:
            return False, "Violated: Prompt hardcodes specific test input"
    return True, "Compliant: Prompt is generalizable"

def validate_valid_json_always(output_text: str) -> Tuple[bool, str]:
    if not output_text or not output_text.strip():
        return False, "Violated: Output is empty"
    try:
        json.loads(output_text.strip())
        return True, "Compliant: Output is strictly valid JSON"
    except Exception as e:
        return False, f"Violated: Output failed JSON parsing ({str(e)})"
