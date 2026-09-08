import time
import json
from typing import Optional, Dict, Any
from app.core.token_counter import count_tokens

class AIProviderError(Exception):
    def __init__(self, message: str, is_transient: bool = False, is_content_safety: bool = False):
        super().__init__(message)
        self.is_transient = is_transient
        self.is_content_safety = is_content_safety

class MockLLMProvider:
    """Mock provider for automated unit and contract tests."""
    def __init__(self):
        self.should_fail_transient = False
        self.should_fail_safety = False
        self.should_timeout = False
        self.attempts = 0

    def generate(self, system_prompt: Optional[str], user_prompt: str, model: str, max_tokens: int = 500) -> str:
        self.attempts += 1

        if self.should_timeout:
            raise TimeoutError("Model execution timed out after 25s limit")

        if self.should_fail_safety:
            raise AIProviderError("Content blocked by safety filters", is_transient=False, is_content_safety=True)

        if self.should_fail_transient:
            if self.attempts == 1:
                # First attempt fails transiently
                raise AIProviderError("503 Service Unavailable: Temporary network glitch", is_transient=True)
            # Second attempt (retry) succeeds

        lower = user_prompt.lower()
        if "json" in lower:
            return json.dumps({"result": "NEGATIVE", "confidence": 0.95})
        elif "one word" in lower or "only the single classification" in lower:
            return "NEGATIVE" if any(w in lower for w in ["broke", "terrible", "worst", "bad", "wiped"]) else "POSITIVE"
        elif "summarize" in lower:
            return "The update caused system errors across modules."
        return "Processed response: " + user_prompt[:80]

class AIProviderAdapter:
    """Pluggable provider-agnostic execution adapter (SRS Section 15)."""
    
    mock_provider = MockLLMProvider()
    use_mock = True

    @classmethod
    def execute(
        cls,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        start_time = time.time()
        timeout_limit = 25.0 # SRS Section 15.3: 25s hard timeout
        
        output_text = None
        status = "success"
        error_msg = None
        retries = 0

        while retries <= 1:
            try:
                # Check elapsed timeout
                if time.time() - start_time > timeout_limit:
                    raise TimeoutError("Per-call execution deadline exceeded (25s)")

                if cls.use_mock:
                    output_text = cls.mock_provider.generate(system_prompt, user_prompt, model, max_tokens)
                else:
                    # Real provider placeholder / HTTP call
                    output_text = f"Live output for prompt: {user_prompt[:50]}"
                
                status = "success"
                break

            except TimeoutError as e:
                status = "timeout"
                error_msg = str(e)
                break

            except AIProviderError as e:
                # Content safety rejections are NEVER retried
                if e.is_content_safety:
                    status = "error"
                    error_msg = str(e)
                    break

                # Transient errors are retried at most ONCE
                if e.is_transient and retries == 0:
                    retries += 1
                    time.sleep(0.05)
                    continue
                else:
                    status = "error"
                    error_msg = str(e)
                    break

            except Exception as e:
                status = "error"
                error_msg = str(e)
                break

        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens = count_tokens(user_prompt) + (count_tokens(system_prompt) if system_prompt else 0)
        output_tokens = count_tokens(output_text) if output_text else 0

        return {
            "output_text": output_text,
            "token_count_prompt": prompt_tokens,
            "token_count_output": output_tokens,
            "latency_ms": latency_ms,
            "status": status,
            "error": error_msg
        }
