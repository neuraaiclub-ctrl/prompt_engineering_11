import time
import httpx
from typing import List, Dict, Any, Optional
from .adapter import AIProviderAdapter, Completion

class GroqProviderAdapter(AIProviderAdapter):
    def __init__(self, api_key: str, base_url: str = "https://api.groq.com/openai/v1/chat/completions"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> Completion:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
            
        start_time = time.time()
        resp = self.client.post(self.base_url, headers=headers, json=payload)
        resp.raise_for_status()
        latency_ms = int((time.time() - start_time) * 1000)
        
        data = resp.json()
        choice = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        
        # Groq pricing approx (Llama3 70b): $0.59 / 1M input, $0.79 / 1M output
        cost_usd = (tokens_in * 0.59 / 1_000_000) + (tokens_out * 0.79 / 1_000_000)
        
        return Completion(
            content=choice,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd=cost_usd
        )
