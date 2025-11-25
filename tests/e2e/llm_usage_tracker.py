"""
LLM Usage Tracker for Pipeline E2E Testing
Tracks token consumption and cost across pipeline execution
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class LLMCall:
    """Single LLM API call record"""
    timestamp: float
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float = 0.0


class LLMUsageTracker:
    """
    Track LLM token usage and costs across pipeline execution.

    Supports Claude 3 family models with configurable pricing.
    """

    # Pricing per 1M tokens
    PRICING = {
        "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    }

    def __init__(self, model: str = "claude-3-5-sonnet"):
        self.model = model
        self.calls: List[LLMCall] = []
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost_usd = 0.0

    def record_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Record an LLM API call.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            latency_ms: Response time in milliseconds
        """
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost
        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        # Create call record
        call = LLMCall(
            timestamp=time.time(),
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )

        # Store and aggregate
        self.calls.append(call)
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        self.total_cost_usd += cost

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate USD cost for given tokens."""
        rates = self.PRICING.get(self.model, self.PRICING["claude-3-5-sonnet"])

        cost = (prompt_tokens / 1_000_000) * rates["input"] + (
            completion_tokens / 1_000_000
        ) * rates["output"]

        return cost

    def get_avg_latency(self) -> float:
        """Get average latency across all calls."""
        if not self.calls:
            return 0.0
        return sum(c.latency_ms for c in self.calls) / len(self.calls)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all LLM usage."""
        return {
            "model": self.model,
            "total_calls": len(self.calls),
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost_usd": self.total_cost_usd,
            "avg_latency_ms": self.get_avg_latency(),
            "tokens_per_call": self.total_tokens / len(self.calls)
            if self.calls
            else 0,
        }

    def record_from_response(self, response: Any, latency_ms: float = 0.0) -> None:
        """
        Record usage from OpenAI-like API response.

        Args:
            response: API response object with usage attribute
            latency_ms: Request latency in milliseconds
        """
        if hasattr(response, "usage"):
            self.record_call(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                latency_ms=latency_ms,
            )
        elif isinstance(response, dict) and "usage" in response:
            usage = response["usage"]
            self.record_call(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency_ms,
            )
