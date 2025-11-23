"""
Model Selector for MVP

Selects optimal Claude model based on task complexity and type.
Implements hybrid strategy: 60% Haiku, 40% Sonnet for cost optimization.
"""

import logging
from typing import Literal, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ClaudeModel(str, Enum):
    """Available Claude models (Oct 2025)"""
    OPUS_4_1 = "claude-opus-4-20250514"
    SONNET_4_5 = "claude-haiku-4-5-20251001"
    HAIKU_4_5 = "claude-haiku-4-5-20251001"  # Released Oct 15, 2025

    # Legacy (for compatibility)
    SONNET_3_5 = "claude-haiku-4-5-20251001"
    HAIKU_3_5 = "claude-3-5-haiku-20241022"


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Task types for model selection"""
    DISCOVERY = "discovery"
    MASTERPLAN_GENERATION = "masterplan_generation"
    TASK_EXECUTION = "task_execution"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    SUMMARY = "summary"
    VALIDATION = "validation"


# Model pricing (per 1M tokens)
MODEL_PRICING = {
    ClaudeModel.OPUS_4_1: {
        "input": 15.0,
        "output": 75.0,
        "input_cached": 1.50,  # 90% discount
    },
    ClaudeModel.SONNET_4_5: {
        "input": 3.0,
        "output": 15.0,
        "input_cached": 0.30,  # 90% discount
    },
    ClaudeModel.HAIKU_4_5: {
        "input": 1.0,
        "output": 5.0,
        "input_cached": 0.10,  # 90% discount
    },
    ClaudeModel.SONNET_3_5: {
        "input": 3.0,
        "output": 15.0,
        "input_cached": 0.30,
    }
}

# Model capabilities
MODEL_CAPABILITIES = {
    ClaudeModel.OPUS_4_1: {
        "context_window": 200_000,
        "output_tokens": 32_000,  # Up to 64K with reasoning
        "reasoning": True,
        "best_for": "Critical architecture, complex DDD modeling"
    },
    ClaudeModel.SONNET_4_5: {
        "context_window": 200_000,
        "output_tokens": 64_000,
        "reasoning": True,
        "best_for": "Balanced quality/cost, general purpose"
    },
    ClaudeModel.HAIKU_4_5: {
        "context_window": 200_000,
        "output_tokens": 64_000,
        "reasoning": True,
        "best_for": "Fast, high-volume, simple/medium tasks"
    }
}


class ModelSelector:
    """
    Selects optimal Claude model for each task.

    MVP Strategy (Hybrid):
    - Discovery: Always Sonnet 4.5
    - MasterPlan: Always Sonnet 4.5
    - Tasks (low/medium): Haiku 4.5 (60% of tasks)
    - Tasks (high): Sonnet 4.5 (40% of tasks)
    - Opus: NOT used in MVP (v2 only)

    Usage:
        selector = ModelSelector()
        model = selector.select_model(
            task_type="task_execution",
            complexity="medium"
        )
    """

    def __init__(
        self,
        use_opus: bool = False,  # Disabled for MVP
        cost_optimization: bool = True  # Use Haiku when possible
    ):
        """
        Initialize model selector.

        Args:
            use_opus: Enable Opus 4.1 for critical tasks (default: False for MVP)
            cost_optimization: Use Haiku for simple/medium tasks (default: True)
        """
        self.use_opus = use_opus
        self.cost_optimization = cost_optimization

        logger.info(
            f"ModelSelector initialized: "
            f"use_opus={use_opus}, "
            f"cost_optimization={cost_optimization}"
        )

    def select_model(
        self,
        task_type: str,
        complexity: str = "medium",
        force_model: Optional[str] = None
    ) -> str:
        """
        Select optimal model for task.

        Args:
            task_type: Type of task (discovery, masterplan_generation, task_execution, etc.)
            complexity: Task complexity (low, medium, high, critical)
            force_model: Force specific model (overrides selection logic)

        Returns:
            Model name string
        """
        # Force model if specified
        if force_model:
            logger.debug(f"Using forced model: {force_model}")
            return force_model

        # Convert to enums
        try:
            task_type_enum = TaskType(task_type)
            complexity_enum = TaskComplexity(complexity)
        except ValueError as e:
            logger.warning(f"Invalid task_type or complexity: {e}. Using Sonnet as fallback.")
            return ClaudeModel.SONNET_4_5.value

        # Selection logic
        model = self._select_model_logic(task_type_enum, complexity_enum)

        logger.debug(
            f"Selected {model} for task_type={task_type}, complexity={complexity}"
        )

        return model

    def _select_model_logic(
        self,
        task_type: TaskType,
        complexity: TaskComplexity
    ) -> str:
        """Internal logic for model selection"""

        # Rule 1: Discovery always uses Sonnet
        if task_type == TaskType.DISCOVERY:
            return ClaudeModel.SONNET_4_5.value

        # Rule 2: MasterPlan generation always uses Sonnet
        if task_type == TaskType.MASTERPLAN_GENERATION:
            return ClaudeModel.SONNET_4_5.value

        # Rule 3: Critical complexity → Opus (if enabled) or Sonnet
        if complexity == TaskComplexity.CRITICAL:
            if self.use_opus:
                return ClaudeModel.OPUS_4_1.value
            return ClaudeModel.SONNET_4_5.value

        # Rule 4: High complexity → Sonnet
        if complexity == TaskComplexity.HIGH:
            return ClaudeModel.SONNET_4_5.value

        # Rule 5: Low/Medium complexity → Haiku (if cost optimization) or Sonnet
        if complexity in [TaskComplexity.LOW, TaskComplexity.MEDIUM]:
            if self.cost_optimization:
                # Use Haiku for most task types
                if task_type in [
                    TaskType.TASK_EXECUTION,
                    TaskType.TEST_GENERATION,
                    TaskType.DOCUMENTATION,
                    TaskType.SUMMARY,
                    TaskType.VALIDATION
                ]:
                    return ClaudeModel.HAIKU_4_5.value

            # Fallback to Sonnet for code review or if optimization disabled
            return ClaudeModel.SONNET_4_5.value

        # Default fallback
        return ClaudeModel.SONNET_4_5.value

    def get_model_pricing(self, model: str) -> dict:
        """
        Get pricing for model.

        Args:
            model: Model name

        Returns:
            Dict with input/output/cached pricing per 1M tokens
        """
        try:
            model_enum = ClaudeModel(model)
            return MODEL_PRICING[model_enum]
        except (ValueError, KeyError):
            logger.warning(f"Unknown model {model}, using Sonnet pricing")
            return MODEL_PRICING[ClaudeModel.SONNET_4_5]

    def get_model_capabilities(self, model: str) -> dict:
        """
        Get capabilities for model.

        Args:
            model: Model name

        Returns:
            Dict with context_window, output_tokens, reasoning, best_for
        """
        try:
            model_enum = ClaudeModel(model)
            return MODEL_CAPABILITIES[model_enum]
        except (ValueError, KeyError):
            logger.warning(f"Unknown model {model}, using Sonnet capabilities")
            return MODEL_CAPABILITIES[ClaudeModel.SONNET_4_5]

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0
    ) -> float:
        """
        Estimate cost for model usage.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached input tokens (with prompt caching)

        Returns:
            Cost in USD
        """
        pricing = self.get_model_pricing(model)

        # Uncached input
        uncached_input = input_tokens - cached_tokens
        input_cost = (uncached_input / 1_000_000) * pricing["input"]

        # Cached input (90% discount)
        cached_cost = (cached_tokens / 1_000_000) * pricing["input_cached"]

        # Output
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total_cost = input_cost + cached_cost + output_cost

        return total_cost

    def get_stats(self) -> dict:
        """
        Get selector configuration stats.

        Returns:
            Dict with config and model info
        """
        return {
            "use_opus": self.use_opus,
            "cost_optimization": self.cost_optimization,
            "available_models": [
                {
                    "model": model.value,
                    "pricing": MODEL_PRICING[model],
                    "capabilities": MODEL_CAPABILITIES[model]
                }
                for model in [ClaudeModel.HAIKU_4_5, ClaudeModel.SONNET_4_5, ClaudeModel.OPUS_4_1]
            ]
        }
