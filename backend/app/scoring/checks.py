import json
import re
from typing import Any, Dict

def check_json_valid(output: str) -> bool:
    try:
        # Strip potential markdown fences
        clean = output.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        json.loads(clean.strip())
        return True
    except ValueError:
        return False

def check_max_words(output: str, max_words: int) -> bool:
    words = len(output.split())
    return words <= max_words

def check_regex_match(output: str, pattern: str) -> bool:
    return bool(re.search(pattern, output, re.IGNORECASE))

def check_regex_absent(output: str, pattern: str) -> bool:
    return not bool(re.search(pattern, output, re.IGNORECASE))

def check_equals_field(output: str, path: str, expected: Any) -> bool:
    try:
        clean = output.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        data = json.loads(clean.strip())
        
        # Simple dot notation path resolver
        keys = path.split(".")
        val = data
        for k in keys:
            val = val[k]
        
        return val == expected
    except Exception:
        return False

def run_deterministic_check(check: Dict[str, Any], output: str) -> bool:
    check_type = check.get("type")
    
    if check_type == "json_valid":
        return check_json_valid(output)
    elif check_type == "max_words":
        return check_max_words(output, check.get("value", 1000))
    elif check_type == "regex_match":
        return check_regex_match(output, check.get("pattern", ""))
    elif check_type == "regex_absent":
        return check_regex_absent(output, check.get("pattern", ""))
    elif check_type == "equals_field":
        return check_equals_field(output, check.get("path", ""), check.get("value"))
    
    # Fallback for unimplemented or LLM checks
    return True
