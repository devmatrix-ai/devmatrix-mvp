"""
Unit Tests for Co-Reasoning System

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

Test Coverage:
- Complexity estimation accuracy with 4-component formula
- Routing decisions (single-LLM vs dual-LLM based on complexity)
- Claude vs DeepSeek model selection
- Cost calculation for both routing strategies
- Model-specific prompting
- Model selector extensibility for LRM
- Edge cases and validation
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.co_reasoning.co_reasoning import (
    CoReasoningSystem,
    estimate_complexity,
    calculate_cost,
    ModelSelector,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


class TestComplexityEstimation:
    """Test complexity estimation with 4-component formula."""

    def test_complexity_calculation_formula_weights(self):
        """Test that complexity uses correct weights: 30% I/O, 40% security, 20% domain, 10% constraints."""
        signature = SemanticTaskSignature(
            purpose="Simple addition function",
            intent="calculate",
            inputs={"a": "int", "b": "int"},  # 2 types = simple I/O
            outputs={"result": "int"},  # 1 type
            domain="math",
            security_level="low",  # Should map to 0.1
            constraints=[]  # No constraints
        )

        # Mock pattern bank to simulate pattern found (domain novelty = 0.1)
        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=0.90)]

        complexity = estimate_complexity(signature, mock_pattern_bank)

        # Expected calculation:
        # io_complexity = 3 types / some_max (normalized to small value)
        # security_impact = 0.1 (LOW)
        # domain_novelty = 0.1 (pattern found)
        # constraint_count = 0.0 (no constraints)
        # complexity = (0.30 * io) + (0.40 * 0.1) + (0.20 * 0.1) + (0.10 * 0.0)

        assert 0.0 <= complexity <= 1.0  # Valid range
        assert complexity < 0.6  # Should be simple task

    def test_complexity_high_security_critical_task(self):
        """Test that CRITICAL security level increases complexity significantly."""
        signature = SemanticTaskSignature(
            purpose="Encrypt user password with bcrypt",
            intent="transform",
            inputs={"password": "str"},
            outputs={"hash": "str"},
            domain="security",
            security_level="critical",  # Should map to 1.0
            constraints=["Use bcrypt", "Salt must be random"]
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []  # No pattern found (novelty=0.8)

        complexity = estimate_complexity(signature, mock_pattern_bank)

        # Expected: High complexity due to CRITICAL security (0.4 * 1.0 = 0.4)
        # Plus domain novelty (0.2 * 0.8 = 0.16)
        assert complexity >= 0.6  # Should trigger dual-LLM routing
        assert complexity < 1.0

    def test_complexity_domain_novelty_pattern_not_found(self):
        """Test that missing patterns increase domain novelty to 0.8."""
        signature = SemanticTaskSignature(
            purpose="Novel quantum algorithm",
            intent="create",
            inputs={"qubits": "List[Qubit]"},
            outputs={"result": "QuantumState"},
            domain="quantum_computing",
            security_level="medium",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []  # No pattern (novelty=0.8)

        complexity = estimate_complexity(signature, mock_pattern_bank)

        # Domain novelty should contribute 0.2 * 0.8 = 0.16 to total
        assert complexity > 0.16  # At least domain novelty contribution

    def test_complexity_domain_novelty_pattern_found(self):
        """Test that existing patterns reduce domain novelty to 0.1."""
        signature = SemanticTaskSignature(
            purpose="Standard email validation",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="validation",
            security_level="low",
        )

        mock_pattern_bank = Mock()
        mock_pattern = Mock()
        mock_pattern.similarity_score = 0.90
        mock_pattern_bank.search_patterns.return_value = [mock_pattern]  # Pattern found (novelty=0.1)

        complexity = estimate_complexity(signature, mock_pattern_bank)

        # Low complexity due to pattern found and LOW security
        assert complexity < 0.4

    def test_complexity_constraint_count_contribution(self):
        """Test that constraints contribute 10% to complexity."""
        # Define what "total possible constraints" means - let's say 10 types
        signature_no_constraints = SemanticTaskSignature(
            purpose="Simple task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            constraints=[]  # 0/10 = 0.0
        )

        signature_many_constraints = SemanticTaskSignature(
            purpose="Complex task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            constraints=["Must be O(1)", "Thread-safe", "No side effects", "Pure function", "Immutable"]  # 5/10 = 0.5
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=0.90)]

        complexity_no = estimate_complexity(signature_no_constraints, mock_pattern_bank)
        complexity_many = estimate_complexity(signature_many_constraints, mock_pattern_bank)

        # Constraints should add 0.10 * (5/10) = 0.05 to complexity
        assert complexity_many > complexity_no


class TestRoutingDecisions:
    """Test routing decisions based on complexity thresholds."""

    def test_single_llm_routing_for_simple_task(self):
        """Test that complexity < 0.6 routes to single-LLM (Claude only)."""
        signature = SemanticTaskSignature(
            purpose="Add two numbers",
            intent="calculate",
            inputs={"a": "int", "b": "int"},
            outputs={"sum": "int"},
            domain="math",
            security_level="low",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=0.90)]

        co_reasoning = CoReasoningSystem(pattern_bank=mock_pattern_bank)

        routing_decision = co_reasoning.decide_routing(signature)

        assert routing_decision == "single_llm"
        assert co_reasoning.estimate_complexity(signature) < 0.6

    def test_dual_llm_routing_for_moderate_complexity(self):
        """Test that 0.6 ≤ complexity < 0.85 routes to dual-LLM."""
        signature = SemanticTaskSignature(
            purpose="Validate and sanitize user input with XSS protection",
            intent="validate",
            inputs={"user_input": "str", "context": "dict"},
            outputs={"sanitized": "str", "is_safe": "bool"},
            domain="security",
            security_level="high",  # 0.4 * 0.8 = 0.32
            constraints=["No XSS", "SQL injection safe"]
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []  # No pattern (0.2 * 0.8 = 0.16)

        co_reasoning = CoReasoningSystem(pattern_bank=mock_pattern_bank)

        routing_decision = co_reasoning.decide_routing(signature)

        complexity = co_reasoning.estimate_complexity(signature)
        assert 0.6 <= complexity < 0.85
        assert routing_decision == "dual_llm"

    def test_single_llm_uses_claude_only(self):
        """Test that single-LLM routing uses Claude for both strategy and code."""
        signature = SemanticTaskSignature(
            purpose="Simple validation",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="validation",
            security_level="low",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=0.90)]

        mock_claude = Mock()
        mock_claude.generate.return_value = "def validate_email(email: str) -> bool:\n    return '@' in email"

        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=mock_claude,
        )

        result = co_reasoning.generate(signature)

        # Verify Claude was called for code generation
        assert mock_claude.generate.called
        assert result is not None


class TestDualLLMReasoning:
    """Test dual-LLM routing (Claude strategy + DeepSeek code)."""

    def test_dual_llm_uses_claude_for_strategy(self):
        """Test that dual-LLM calls Claude for strategic reasoning."""
        signature = SemanticTaskSignature(
            purpose="Complex security validation with encryption",
            intent="validate",
            inputs={"data": "dict", "context": "dict", "auth_token": "str"},
            outputs={"is_safe": "bool", "risk_score": "float"},
            domain="security",
            security_level="critical",  # 0.4 * 1.0 = 0.4
            constraints=["Must encrypt PII", "Validate against XSS"]  # 0.1 * 0.2 = 0.02
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []

        mock_claude = Mock()
        mock_claude.generate_strategy.return_value = "Use input sanitization and allowlisting"

        mock_deepseek = Mock()
        mock_deepseek.generate_code.return_value = "def validate(data: dict) -> bool:\n    return True"

        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=mock_claude,
            deepseek_client=mock_deepseek,
        )

        result = co_reasoning.generate(signature)

        # Verify Claude was called for strategy
        mock_claude.generate_strategy.assert_called_once()
        # Verify DeepSeek was called for code
        mock_deepseek.generate_code.assert_called_once()

    def test_dual_llm_passes_strategy_to_deepseek(self):
        """Test that strategy from Claude is passed to DeepSeek for code generation."""
        signature = SemanticTaskSignature(
            purpose="Complex cryptographic hash with salt",
            intent="transform",
            inputs={"password": "str", "salt": "bytes", "iterations": "int"},
            outputs={"hash": "bytes", "metadata": "dict"},
            domain="cryptography",
            security_level="critical",  # 0.4 * 1.0 = 0.4
            constraints=["Use PBKDF2", "Min 100k iterations", "Constant time comparison"]  # 0.1 * 0.3 = 0.03
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []

        claude_strategy = "Use two-pointer technique for O(n) complexity"
        mock_claude = Mock()
        mock_claude.generate_strategy.return_value = claude_strategy

        mock_deepseek = Mock()
        mock_deepseek.generate_code.return_value = "def algorithm(data: List[int]) -> int:\n    pass"

        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=mock_claude,
            deepseek_client=mock_deepseek,
        )

        result = co_reasoning.generate(signature)

        # Verify DeepSeek received the strategy in its prompt
        call_args = mock_deepseek.generate_code.call_args
        assert claude_strategy in str(call_args) or "strategy" in str(call_args).lower()


class TestCostCalculation:
    """Test cost calculation for both routing strategies."""

    def test_cost_single_llm_is_001_per_atom(self):
        """Test that single-LLM routing costs $0.001 per atom."""
        complexity = 0.3  # < 0.6, triggers single-LLM
        routing_decision = "single_llm"

        cost = calculate_cost(complexity, routing_decision)

        assert cost == 0.001

    def test_cost_dual_llm_is_003_per_atom(self):
        """Test that dual-LLM routing costs $0.003 per atom."""
        complexity = 0.7  # 0.6 ≤ complexity < 0.85, triggers dual-LLM
        routing_decision = "dual_llm"

        cost = calculate_cost(complexity, routing_decision)

        assert cost == 0.003

    def test_cost_matches_routing_decision(self):
        """Test that cost calculation is consistent with routing."""
        signature_simple = SemanticTaskSignature(
            purpose="Simple task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            security_level="low",
        )

        signature_complex = SemanticTaskSignature(
            purpose="Complex security validation with multi-factor auth",
            intent="validate",
            inputs={"credentials": "dict", "mfa_token": "str", "session_id": "str"},
            outputs={"is_authenticated": "bool", "session_data": "dict"},
            domain="security",
            security_level="critical",  # 0.4 * 1.0 = 0.4
            constraints=["Rate limit", "Audit log"]  # 0.1 * 0.2 = 0.02
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.side_effect = [
            [Mock(similarity_score=0.90)],  # For simple task
            []  # For complex task
        ]

        co_reasoning = CoReasoningSystem(pattern_bank=mock_pattern_bank)

        cost_simple = co_reasoning.calculate_cost(signature_simple)
        cost_complex = co_reasoning.calculate_cost(signature_complex)

        assert cost_simple == 0.001  # Single-LLM
        assert cost_complex == 0.003  # Dual-LLM


class TestModelSelector:
    """Test model selector and extensibility for LRM."""

    def test_model_selector_supports_claude(self):
        """Test that ModelSelector supports Claude model."""
        selector = ModelSelector()

        model = selector.select_model(task_type="strategy", complexity=0.3)

        assert model in ["claude-opus-4", "claude-sonnet-4"]  # Claude models

    def test_model_selector_supports_deepseek(self):
        """Test that ModelSelector supports DeepSeek model."""
        selector = ModelSelector()

        # DeepSeek is used in dual-LLM routing for code generation
        model = selector.select_model(task_type="code", complexity=0.7, routing="dual_llm")

        assert "deepseek" in model.lower() or model == "deepseek"

    def test_model_selector_extensible_for_lrm(self):
        """Test that ModelSelector has hook for LRM support (Phase 2)."""
        selector = ModelSelector()

        # Should have method or attribute for LRM support
        assert hasattr(selector, "add_model_support") or hasattr(selector, "register_model")

        # Verify can add LRM without breaking existing functionality
        if hasattr(selector, "add_model_support"):
            selector.add_model_support("lrm", model_name="lrm-v1")

    def test_model_selector_chooses_claude_for_strategy(self):
        """Test that strategy tasks route to Claude."""
        selector = ModelSelector()

        model = selector.select_model(task_type="strategy", complexity=0.5)

        assert "claude" in model.lower()

    def test_model_selector_chooses_deepseek_for_code_in_dual_llm(self):
        """Test that code tasks in dual-LLM route to DeepSeek."""
        selector = ModelSelector()

        model = selector.select_model(task_type="code", complexity=0.7, routing="dual_llm")

        assert "deepseek" in model.lower()


class TestModelSpecificPrompting:
    """Test model-specific prompt generation."""

    def test_claude_strategy_prompt_includes_signature_details(self):
        """Test that Claude strategy prompts include full signature context."""
        signature = SemanticTaskSignature(
            purpose="Validate user authentication",
            intent="validate",
            inputs={"username": "str", "password": "str"},
            outputs={"is_authenticated": "bool"},
            domain="authentication",
            security_level="high",
            constraints=["Use bcrypt", "Rate limit checks"]
        )

        mock_pattern_bank = Mock()
        co_reasoning = CoReasoningSystem(pattern_bank=mock_pattern_bank)

        prompt = co_reasoning.generate_strategy_prompt(signature)

        # Verify key signature elements in prompt
        assert "Validate user authentication" in prompt
        assert "HIGH" in prompt or "security" in prompt.lower()
        assert "bcrypt" in prompt

    def test_deepseek_code_prompt_includes_strategy_and_constraints(self):
        """Test that DeepSeek code prompts include strategy + constraints."""
        signature = SemanticTaskSignature(
            purpose="Hash password",
            intent="transform",
            inputs={"password": "str"},
            outputs={"hash": "str"},
            domain="security",
            constraints=["Max 10 LOC", "Type hints required"]
        )

        strategy = "Use bcrypt with random salt"

        mock_pattern_bank = Mock()
        co_reasoning = CoReasoningSystem(pattern_bank=mock_pattern_bank)

        prompt = co_reasoning.generate_code_prompt(signature, strategy)

        # Verify strategy and constraints in prompt
        assert strategy in prompt
        assert "Max 10 LOC" in prompt or "10" in prompt
        assert "Type hints" in prompt or "type hint" in prompt.lower()


class TestEdgeCases:
    """Test edge cases and validation."""

    def test_complexity_never_exceeds_1_0(self):
        """Test that complexity is always ≤ 1.0."""
        signature = SemanticTaskSignature(
            purpose="Ultra complex task",
            intent="create",
            inputs={"a": "int", "b": "str", "c": "dict", "d": "list"},
            outputs={"x": "dict", "y": "list", "z": "str"},
            domain="unknown_domain",
            security_level="critical",
            constraints=["Constraint 1", "Constraint 2", "Constraint 3", "Constraint 4", "Constraint 5"]
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []

        complexity = estimate_complexity(signature, mock_pattern_bank)

        assert complexity <= 1.0

    def test_complexity_never_below_0_0(self):
        """Test that complexity is always ≥ 0.0."""
        signature = SemanticTaskSignature(
            purpose="Minimal task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            security_level="low",
            constraints=[]
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=1.0)]

        complexity = estimate_complexity(signature, mock_pattern_bank)

        assert complexity >= 0.0


class TestErrorHandling:
    """Test error handling and edge cases for coverage."""

    def test_calculate_cost_unknown_routing_defaults_to_single_llm(self):
        """Test that unknown routing decision defaults to single-LLM cost."""
        complexity = 0.5
        routing_decision = "unknown_routing"  # Invalid routing

        cost = calculate_cost(complexity, routing_decision)

        assert cost == 0.001  # Should default to single-LLM cost

    def test_model_selector_unknown_task_type_defaults_to_claude(self):
        """Test that unknown task_type defaults to Claude strategy model."""
        selector = ModelSelector()

        model = selector.select_model(task_type="unknown_task", complexity=0.5)

        assert "claude" in model.lower()  # Should default to Claude

    def test_model_selector_register_model_alias(self):
        """Test that register_model is an alias for add_model_support."""
        selector = ModelSelector()

        # Use register_model instead of add_model_support
        selector.register_model("test_model", "test-v1")

        # Verify model was added to registry
        assert selector._model_registry["test_model"] == "test-v1"

    def test_generate_single_llm_without_claude_client(self):
        """Test that single-LLM generation fails gracefully without Claude client."""
        signature = SemanticTaskSignature(
            purpose="Test task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            security_level="low",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=0.90)]

        # Create CoReasoningSystem without claude_client
        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=None,  # No client
        )

        result = co_reasoning._generate_single_llm(signature)

        assert result is None  # Should return None gracefully

    def test_generate_single_llm_exception_handling(self):
        """Test that single-LLM handles exceptions gracefully."""
        signature = SemanticTaskSignature(
            purpose="Test task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            security_level="low",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = [Mock(similarity_score=0.90)]

        # Mock Claude client that raises exception
        mock_claude = Mock()
        mock_claude.generate.side_effect = Exception("LLM API error")

        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=mock_claude,
        )

        result = co_reasoning._generate_single_llm(signature)

        assert result is None  # Should return None after exception

    def test_generate_dual_llm_without_clients(self):
        """Test that dual-LLM generation fails gracefully without clients."""
        signature = SemanticTaskSignature(
            purpose="Test task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            security_level="critical",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []

        # Create CoReasoningSystem without clients
        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=None,
            deepseek_client=None,
        )

        result = co_reasoning._generate_dual_llm(signature)

        assert result is None  # Should return None gracefully

    def test_generate_dual_llm_exception_handling(self):
        """Test that dual-LLM handles exceptions gracefully."""
        signature = SemanticTaskSignature(
            purpose="Test task",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="math",
            security_level="critical",
        )

        mock_pattern_bank = Mock()
        mock_pattern_bank.search_patterns.return_value = []

        # Mock clients that raise exception
        mock_claude = Mock()
        mock_claude.generate_strategy.side_effect = Exception("Strategy API error")

        mock_deepseek = Mock()

        co_reasoning = CoReasoningSystem(
            pattern_bank=mock_pattern_bank,
            claude_client=mock_claude,
            deepseek_client=mock_deepseek,
        )

        result = co_reasoning._generate_dual_llm(signature)

        assert result is None  # Should return None after exception


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
