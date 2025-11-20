"""
Co-Reasoning System for Cognitive Architecture

Intelligent routing between Claude (strategy) and DeepSeek (implementation) based on
task complexity estimation. Supports single-LLM and dual-LLM reasoning strategies.

Key Components:
1. Complexity Estimation: 4-component formula (I/O, security, domain, constraints)
2. Routing Decision: Single-LLM (<0.6) vs Dual-LLM (0.6-0.85)
3. Cost Calculation: $0.001 (single) vs $0.003 (dual)
4. Model Selection: Claude for strategy, DeepSeek for code (extensible for LRM)

Spec Reference: Section 3.4 - Co-Reasoning System
Target Coverage: >90%
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.cognitive.patterns.pattern_bank import PatternBank

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security level mapping to complexity scores."""
    LOW = 0.1
    MEDIUM = 0.5
    HIGH = 0.8
    CRITICAL = 1.0


class RoutingStrategy(Enum):
    """Routing strategy types."""
    SINGLE_LLM = "single_llm"  # Claude only
    DUAL_LLM = "dual_llm"      # Claude + DeepSeek


def estimate_complexity(
    signature: SemanticTaskSignature,
    pattern_bank: PatternBank,
) -> float:
    """
    Estimate task complexity using 4-component weighted formula.

    Formula: complexity = (0.30 * io_complexity) + (0.40 * security_impact) +
                         (0.20 * domain_novelty) + (0.10 * constraint_count)

    Components:
    - I/O Complexity (30%): Based on unique input/output type count
    - Security Impact (40%): Mapped from security_level (LOW=0.1, CRITICAL=1.0)
    - Domain Novelty (20%): 0.1 if pattern found, 0.8 if not found
    - Constraint Count (10%): Number of constraints / max possible (10)

    Args:
        signature: Semantic task signature
        pattern_bank: Pattern bank for domain novelty check

    Returns:
        Complexity score in range [0.0, 1.0]

    Example:
        >>> signature = SemanticTaskSignature(purpose="Add numbers", ...)
        >>> complexity = estimate_complexity(signature, pattern_bank)
        >>> # Returns: 0.25 (simple task)
    """
    # 1. I/O Complexity (30% weight)
    # Count unique input/output types, normalize by max expected (10 types)
    input_types = len(signature.inputs) if signature.inputs else 0
    output_types = len(signature.outputs) if signature.outputs else 0
    total_io_types = input_types + output_types
    io_complexity = min(total_io_types / 10.0, 1.0)  # Cap at 1.0

    # 2. Security Impact (40% weight)
    # Map security level to score (lowercase as per Pydantic validation)
    security_map = {
        "low": SecurityLevel.LOW.value,
        "medium": SecurityLevel.MEDIUM.value,
        "high": SecurityLevel.HIGH.value,
        "critical": SecurityLevel.CRITICAL.value,
    }
    security_impact = security_map.get(signature.security_level, SecurityLevel.LOW.value)

    # 3. Domain Novelty (20% weight)
    # Search pattern bank for similar patterns using adaptive thresholds + keyword fallback (TG4+TG5)
    try:
        patterns = pattern_bank.search_with_fallback(signature, top_k=1, min_results=1)
        domain_novelty = 0.1 if patterns else 0.8  # Found=0.1, Not found=0.8
    except Exception as e:
        logger.warning(f"Pattern search failed: {e}, assuming high novelty")
        domain_novelty = 0.8

    # 4. Constraint Count (10% weight)
    # Normalize by max possible constraints (10)
    constraint_count = len(signature.constraints) if signature.constraints else 0
    constraint_complexity = min(constraint_count / 10.0, 1.0)

    # Calculate weighted complexity
    complexity = (
        (0.30 * io_complexity) +
        (0.40 * security_impact) +
        (0.20 * domain_novelty) +
        (0.10 * constraint_complexity)
    )

    # Ensure range [0.0, 1.0]
    complexity = max(0.0, min(1.0, complexity))

    logger.debug(
        f"Complexity: {complexity:.3f} "
        f"(io={io_complexity:.2f}, sec={security_impact:.2f}, "
        f"novelty={domain_novelty:.2f}, constraints={constraint_complexity:.2f})"
    )

    return complexity


def calculate_cost(complexity: float, routing_decision: str) -> float:
    """
    Calculate cost per atom based on routing strategy.

    Cost Model:
    - Single-LLM (Claude only): $0.001 per atom
    - Dual-LLM (Claude + DeepSeek): $0.003 per atom

    Args:
        complexity: Task complexity score [0.0-1.0]
        routing_decision: "single_llm" or "dual_llm"

    Returns:
        Cost in USD per atom

    Example:
        >>> cost = calculate_cost(0.3, "single_llm")
        >>> # Returns: 0.001
    """
    if routing_decision == RoutingStrategy.SINGLE_LLM.value:
        return 0.001
    elif routing_decision == RoutingStrategy.DUAL_LLM.value:
        return 0.003
    else:
        logger.warning(f"Unknown routing: {routing_decision}, defaulting to single_llm cost")
        return 0.001


class ModelSelector:
    """
    Model selector for Co-Reasoning System.

    Supports:
    - Claude (claude-opus-4) for strategic reasoning
    - DeepSeek for code implementation
    - Extensible for LRM (Phase 2)

    Example:
        >>> selector = ModelSelector()
        >>> model = selector.select_model("strategy", 0.5)
        >>> # Returns: "claude-opus-4"
    """

    def __init__(self):
        """Initialize model selector with default model registry."""
        self._model_registry: Dict[str, str] = {
            "claude_strategy": "claude-opus-4",
            "claude_code": "claude-sonnet-4",
            "deepseek_code": "deepseek",
        }
        logger.info("ModelSelector initialized with Claude and DeepSeek support")

    def select_model(
        self,
        task_type: str,
        complexity: float,
        routing: Optional[str] = None,
    ) -> str:
        """
        Select appropriate model based on task type and complexity.

        Args:
            task_type: "strategy" or "code"
            complexity: Task complexity [0.0-1.0]
            routing: Optional routing strategy override

        Returns:
            Model name/identifier

        Example:
            >>> selector.select_model("strategy", 0.7)
            >>> # Returns: "claude-opus-4"
        """
        if task_type == "strategy":
            # Strategy tasks always route to Claude
            return self._model_registry["claude_strategy"]

        elif task_type == "code":
            # Code tasks route based on routing strategy
            if routing == RoutingStrategy.DUAL_LLM.value:
                return self._model_registry["deepseek_code"]
            else:
                # Single-LLM uses Claude for code too
                return self._model_registry["claude_code"]

        else:
            logger.warning(f"Unknown task_type: {task_type}, defaulting to Claude")
            return self._model_registry["claude_strategy"]

    def add_model_support(self, model_type: str, model_name: str) -> None:
        """
        Add support for new model (extensibility for LRM Phase 2).

        Args:
            model_type: Type identifier (e.g., "lrm_strategy", "lrm_code")
            model_name: Model name/identifier

        Example:
            >>> selector.add_model_support("lrm_code", "lrm-v1")
        """
        self._model_registry[model_type] = model_name
        logger.info(f"Added model support: {model_type} -> {model_name}")

    def register_model(self, model_type: str, model_name: str) -> None:
        """Alias for add_model_support (backward compatibility)."""
        self.add_model_support(model_type, model_name)


class CoReasoningSystem:
    """
    Co-Reasoning System orchestrating Claude and DeepSeek.

    Routing Logic:
    - Complexity < 0.6: Single-LLM (Claude only)
    - 0.6 ≤ Complexity < 0.85: Dual-LLM (Claude strategy + DeepSeek code)

    Expected Precision:
    - Single-LLM: 88%
    - Dual-LLM: 94%

    Example:
        >>> system = CoReasoningSystem(pattern_bank=bank, claude_client=claude)
        >>> code = system.generate(signature)
        >>> # Returns: Generated code using optimal routing
    """

    def __init__(
        self,
        pattern_bank: PatternBank,
        claude_client: Optional[Any] = None,
        deepseek_client: Optional[Any] = None,
    ):
        """
        Initialize Co-Reasoning System.

        Args:
            pattern_bank: Pattern bank for complexity estimation
            claude_client: Optional Claude LLM client
            deepseek_client: Optional DeepSeek LLM client
        """
        self.pattern_bank = pattern_bank
        self.claude_client = claude_client
        self.deepseek_client = deepseek_client
        self.model_selector = ModelSelector()

        logger.info("CoReasoningSystem initialized")

    def estimate_complexity(self, signature: SemanticTaskSignature) -> float:
        """Estimate task complexity (wrapper for module-level function)."""
        return estimate_complexity(signature, self.pattern_bank)

    def decide_routing(self, signature: SemanticTaskSignature) -> str:
        """
        Decide routing strategy based on complexity.

        Thresholds:
        - < 0.6: single_llm
        - 0.6-0.85: dual_llm

        Args:
            signature: Semantic task signature

        Returns:
            "single_llm" or "dual_llm"
        """
        complexity = self.estimate_complexity(signature)

        if complexity < 0.6:
            routing = RoutingStrategy.SINGLE_LLM.value
            logger.debug(f"Routing: single_llm (complexity={complexity:.3f})")
        else:
            routing = RoutingStrategy.DUAL_LLM.value
            logger.debug(f"Routing: dual_llm (complexity={complexity:.3f})")

        return routing

    def calculate_cost(self, signature: SemanticTaskSignature) -> float:
        """Calculate cost for generating code for signature."""
        complexity = self.estimate_complexity(signature)
        routing = self.decide_routing(signature)
        return calculate_cost(complexity, routing)

    def generate_strategy_prompt(self, signature: SemanticTaskSignature) -> str:
        """
        Generate Claude strategy prompt from signature.

        Args:
            signature: Semantic task signature

        Returns:
            Formatted prompt string for Claude
        """
        prompt = f"""Task Purpose: {signature.purpose}
Intent: {signature.intent}
Inputs: {signature.inputs}
Outputs: {signature.outputs}
Domain: {signature.domain}
Security Level: {signature.security_level}
Constraints: {signature.constraints}

Generate a strategic approach to implement this task.
Consider edge cases, performance, and security.
Focus on the high-level reasoning and approach."""

        return prompt

    def generate_code_prompt(
        self,
        signature: SemanticTaskSignature,
        strategy: str,
    ) -> str:
        """
        Generate DeepSeek code prompt with strategy.

        Args:
            signature: Semantic task signature
            strategy: Strategic approach from Claude

        Returns:
            Formatted prompt string for DeepSeek
        """
        prompt = f"""Task: {signature.purpose}
Strategy: {strategy}
Inputs: {signature.inputs}
Outputs: {signature.outputs}
Constraints: {signature.constraints}

Implement the code following the strategy.
Requirements:
- Maximum 10 lines of code
- Full type hints for all parameters and return values
- No TODO or placeholder comments
- Valid Python syntax
- Single responsibility principle"""

        return prompt

    def generate(self, signature: SemanticTaskSignature) -> Optional[str]:
        """
        Generate code using optimal routing strategy.

        Args:
            signature: Semantic task signature

        Returns:
            Generated code string or None if generation fails
        """
        routing = self.decide_routing(signature)

        if routing == RoutingStrategy.SINGLE_LLM.value:
            # Single-LLM: Claude for both strategy and code
            return self._generate_single_llm(signature)
        else:
            # Dual-LLM: Claude for strategy, DeepSeek for code
            return self._generate_dual_llm(signature)

    def _generate_single_llm(self, signature: SemanticTaskSignature) -> Optional[str]:
        """Generate code using Claude only."""
        if not self.claude_client:
            logger.error("Claude client not configured")
            return None

        prompt = self.generate_code_prompt(signature, "Direct implementation")

        try:
            code = self.claude_client.generate(prompt)
            logger.info("Single-LLM generation succeeded")
            return code
        except Exception as e:
            logger.error(f"Single-LLM generation failed: {e}")
            return None

    def _generate_dual_llm(self, signature: SemanticTaskSignature) -> Optional[str]:
        """Generate code using Claude (strategy) + DeepSeek (code)."""
        if not self.claude_client or not self.deepseek_client:
            logger.error("Claude or DeepSeek client not configured")
            return None

        try:
            # Step 1: Claude generates strategy
            strategy_prompt = self.generate_strategy_prompt(signature)
            strategy = self.claude_client.generate_strategy(strategy_prompt)
            logger.debug(f"Strategy generated: {strategy[:100]}...")

            # Step 2: DeepSeek generates code based on strategy
            code_prompt = self.generate_code_prompt(signature, strategy)
            code = self.deepseek_client.generate_code(code_prompt)
            logger.info("Dual-LLM generation succeeded")

            return code

        except Exception as e:
            logger.error(f"Dual-LLM generation failed: {e}")
            return None
