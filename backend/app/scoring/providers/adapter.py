from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class Completion(BaseModel):
    content: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float

class AIProviderAdapter(ABC):
    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> Completion:
        pass

class MockScoringProvider(AIProviderAdapter):
    """
    Used for Phase 2 testing. Mimics successful completions and counts tokens roughly.
    """
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> Completion:
        # Simplistic token estimation
        tokens_in = sum(len(m.get("content", "").split()) for m in messages)
        response_text = "MOCK_RESPONSE"
        
        if response_format == "json_object":
            response_text = '{"scores": {"clarity": 20, "specificity": 20, "context": 20, "output_format": 20, "constraints": 20}, "evidence": {"clarity": "Mock quote"}}'
            
        tokens_out = len(response_text.split())
        
        return Completion(
            content=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=150,
            cost_usd=0.001
        )
