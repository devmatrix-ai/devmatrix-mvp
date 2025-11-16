"""Token usage tracking and cost calculation for DevMatrix Console."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class TokenMetrics:
    """Token usage metrics."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    session_start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CostMetrics:
    """Cost tracking metrics."""

    total_cost: float = 0.0
    estimated_cost: float = 0.0
    by_model: Dict[str, float] = field(default_factory=dict)
    by_operation: Dict[str, float] = field(default_factory=dict)


class ModelPricing:
    """Model-specific pricing configuration."""

    # Pricing per 1K tokens (example rates, should be configurable)
    DEFAULT_PRICING = {
        "claude-opus-4": {"prompt": 0.015, "completion": 0.075},
        "claude-sonnet-4": {"prompt": 0.003, "completion": 0.015},
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
    }

    def __init__(self, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None):
        """Initialize pricing.

        Args:
            custom_pricing: Custom pricing override
        """
        self.pricing = custom_pricing or self.DEFAULT_PRICING

    def get_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for token usage.

        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in dollars
        """
        if model not in self.pricing:
            logger.warning(f"Unknown model {model}, using gpt-3.5-turbo pricing")
            model = "gpt-3.5-turbo"

        pricing = self.pricing[model]
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]

        return prompt_cost + completion_cost

    def get_all_models(self) -> list[str]:
        """Get list of available models."""
        return list(self.pricing.keys())


class TokenTracker:
    """Tracks token usage and calculates costs."""

    def __init__(
        self,
        default_model: str = "claude-opus-4",
        budget: Optional[float] = None,
        cost_limit: Optional[float] = None,
        pricing: Optional[ModelPricing] = None,
    ):
        """Initialize token tracker.

        Args:
            default_model: Default model for cost calculation
            budget: Token budget (optional)
            cost_limit: Cost limit in dollars (optional)
            pricing: Custom pricing configuration
        """
        self.default_model = default_model
        self.budget = budget
        self.cost_limit = cost_limit
        self.pricing = pricing or ModelPricing()

        self.metrics = TokenMetrics()
        self.cost_metrics = CostMetrics()
        self.session_tokens_by_model: Dict[str, int] = {}

        logger.info(f"TokenTracker initialized: model={default_model}, budget={budget}")

    def add_tokens(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
        operation: str = "unknown",
    ) -> None:
        """Record token usage.

        Args:
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            model: Model used (defaults to configured model)
            operation: Operation name for categorization
        """
        model = model or self.default_model
        total = prompt_tokens + completion_tokens

        self.metrics.total_tokens += total
        self.metrics.prompt_tokens += prompt_tokens
        self.metrics.completion_tokens += completion_tokens
        self.metrics.last_update = datetime.now().isoformat()

        # Track by model
        if model not in self.session_tokens_by_model:
            self.session_tokens_by_model[model] = 0
        self.session_tokens_by_model[model] += total

        # Calculate cost
        cost = self.pricing.get_cost(model, prompt_tokens, completion_tokens)
        self.cost_metrics.total_cost += cost

        # Track by model
        if model not in self.cost_metrics.by_model:
            self.cost_metrics.by_model[model] = 0.0
        self.cost_metrics.by_model[model] += cost

        # Track by operation
        if operation not in self.cost_metrics.by_operation:
            self.cost_metrics.by_operation[operation] = 0.0
        self.cost_metrics.by_operation[operation] += cost

        logger.debug(
            f"Tokens added: {total} ({prompt_tokens} prompt, {completion_tokens} completion) "
            f"Model: {model}, Cost: ${cost:.4f}"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current tracking status.

        Returns:
            Status dictionary with metrics and alerts
        """
        budget_percent = (
            (self.metrics.total_tokens / self.budget * 100) if self.budget else None
        )
        cost_percent = (
            (self.cost_metrics.total_cost / self.cost_limit * 100) if self.cost_limit else None
        )

        alerts = []

        # Budget alerts
        if budget_percent:
            if budget_percent >= 90:
                alerts.append(
                    {"level": "critical", "message": f"Token budget 90%+ used ({budget_percent:.0f}%)"}
                )
            elif budget_percent >= 75:
                alerts.append(
                    {"level": "warning", "message": f"Token budget 75%+ used ({budget_percent:.0f}%)"}
                )

        # Cost alerts
        if cost_percent:
            if cost_percent >= 90:
                alerts.append(
                    {"level": "critical", "message": f"Cost limit 90%+ reached (${self.cost_metrics.total_cost:.2f})"}
                )
            elif cost_percent >= 75:
                alerts.append(
                    {"level": "warning", "message": f"Cost limit 75%+ reached (${self.cost_metrics.total_cost:.2f})"}
                )

        return {
            "tokens": {
                "total": self.metrics.total_tokens,
                "prompt": self.metrics.prompt_tokens,
                "completion": self.metrics.completion_tokens,
                "budget": self.budget,
                "budget_percent": budget_percent,
            },
            "cost": {
                "total": self.cost_metrics.total_cost,
                "limit": self.cost_limit,
                "limit_percent": cost_percent,
                "by_model": self.cost_metrics.by_model,
                "by_operation": self.cost_metrics.by_operation,
            },
            "alerts": alerts,
            "session_start": self.metrics.session_start_time,
            "last_update": self.metrics.last_update,
        }

    def get_summary(self) -> str:
        """Get human-readable summary.

        Returns:
            Formatted summary string
        """
        summary = f"Tokens: {self.metrics.total_tokens:,}"

        if self.budget:
            pct = (self.metrics.total_tokens / self.budget) * 100
            summary += f" / {self.budget:,} ({pct:.0f}%)"

        summary += f" | Cost: ${self.cost_metrics.total_cost:.2f}"

        if self.cost_limit:
            pct = (self.cost_metrics.total_cost / self.cost_limit) * 100
            summary += f" / ${self.cost_limit:.2f} ({pct:.0f}%)"

        return summary

    def reset(self) -> None:
        """Reset all metrics for new session."""
        self.metrics = TokenMetrics()
        self.cost_metrics = CostMetrics()
        self.session_tokens_by_model = {}
        logger.info("Token tracker reset")

    def export_metrics(self) -> Dict[str, Any]:
        """Export metrics for saving to session.

        Returns:
            Exportable metrics dictionary
        """
        return {
            "tokens": {
                "total": self.metrics.total_tokens,
                "prompt": self.metrics.prompt_tokens,
                "completion": self.metrics.completion_tokens,
            },
            "cost": {
                "total": self.cost_metrics.total_cost,
                "by_model": self.cost_metrics.by_model,
            },
            "session_start": self.metrics.session_start_time,
            "by_model": self.session_tokens_by_model,
        }
