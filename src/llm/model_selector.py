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
    """Available Claude models (Nov 2025)"""
    # Current models - Nov 2025
    OPUS_4_5 = "claude-opus-4-5-20251101"      # Deep thinking, architecture, discovery
    SONNET_4_5 = "claude-sonnet-4-5-20250929"  # Intermediate tasks, analysis
    HAIKU_4_5 = "claude-haiku-4-5-20251001"    # Code gen, repair, tests, docs

    # Legacy aliases (for compatibility)
    OPUS_4_1 = "claude-opus-4-5-20251101"      # Redirect to Opus 4.5
    SONNET_3_5 = "claude-sonnet-4-5-20250929"  # Redirect to Sonnet 4.5
    HAIKU_3_5 = "claude-haiku-4-5-20251001"    # Redirect to Haiku 4.5


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
    CODE_REPAIR = "code_repair"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    SUMMARY = "summary"
    VALIDATION = "validation"


# Model pricing (per 1M tokens) - Nov 2025
MODEL_PRICING = {
    ClaudeModel.OPUS_4_5: {
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
}

# Model capabilities - Nov 2025
MODEL_CAPABILITIES = {
    ClaudeModel.OPUS_4_5: {
        "context_window": 200_000,
        "output_tokens": 32_000,
        "reasoning": True,
        "best_for": "Discovery, MasterPlan, Architecture, Deep thinking"
    },
    ClaudeModel.SONNET_4_5: {
        "context_window": 200_000,
        "output_tokens": 64_000,
        "reasoning": True,
        "best_for": "Intermediate tasks, analysis, general purpose"
    },
    ClaudeModel.HAIKU_4_5: {
        "context_window": 200_000,
        "output_tokens": 64_000,
        "reasoning": True,
        "best_for": "Code generation, repair, tests, documentation"
    }
}


class ModelSelector:
    """
    Selects optimal Claude model for each task.

    Model Strategy (Nov 2025):
    - Opus 4.5: Discovery, MasterPlan, Architecture (deep thinking)
    - Sonnet 4.5: Intermediate analysis, general purpose, high complexity
    - Haiku 4.5: Code gen, repair, tests, docs (fast execution)

    Usage:
        selector = ModelSelector()
        model = selector.select_model(
            task_type="task_execution",
            complexity="medium"
        )
    """

    def __init__(
        self,
        use_opus: bool = True,   # Enabled - use for deep thinking tasks
        cost_optimization: bool = True  # Use Haiku for code tasks
    ):
        """
        Initialize model selector.

        Args:
            use_opus: Enable Opus 4.5 for discovery/masterplan (default: True)
            cost_optimization: Use Haiku for code tasks (default: True)
        """
        self.use_opus = use_opus
        self.cost_optimization = cost_optimization

        # Bug #119: Changed to debug to reduce noise in smoke test output
        logger.debug(
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
        """Internal logic for model selection (Nov 2025 strategy)"""

        # Rule 1: Deep thinking tasks → Opus 4.5
        # Discovery and MasterPlan require deep analysis
        if task_type in [TaskType.DISCOVERY, TaskType.MASTERPLAN_GENERATION]:
            if self.use_opus:
                return ClaudeModel.OPUS_4_5.value
            return ClaudeModel.SONNET_4_5.value  # Fallback if Opus disabled

        # Rule 2: Code tasks → Haiku 4.5 (fast execution)
        # Code gen, repair, tests, docs are repetitive and benefit from speed
        if task_type in [
            TaskType.TASK_EXECUTION,
            TaskType.CODE_REPAIR,
            TaskType.TEST_GENERATION,
            TaskType.DOCUMENTATION,
            TaskType.SUMMARY,
        ]:
            return ClaudeModel.HAIKU_4_5.value

        # Rule 3: Analysis tasks → Sonnet 4.5 (balanced)
        # Code review, validation need quality but not deep thinking
        if task_type in [TaskType.CODE_REVIEW, TaskType.VALIDATION]:
            return ClaudeModel.SONNET_4_5.value

        # Rule 4: Complexity override
        # Critical complexity elevates to Opus
        if complexity == TaskComplexity.CRITICAL:
            if self.use_opus:
                return ClaudeModel.OPUS_4_5.value
            return ClaudeModel.SONNET_4_5.value

        # Rule 5: High complexity → Sonnet
        if complexity == TaskComplexity.HIGH:
            return ClaudeModel.SONNET_4_5.value

        # Default fallback → Haiku (cost efficient)
        return ClaudeModel.HAIKU_4_5.value

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
                for model in [ClaudeModel.HAIKU_4_5, ClaudeModel.SONNET_4_5, ClaudeModel.OPUS_4_5]
            ]
        }
