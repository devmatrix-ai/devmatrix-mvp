"""
Unit Tests for RetryOrchestrator

Tests retry logic, temperature backoff, error feedback, and metrics.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4

from src.mge.v2.execution.retry_orchestrator import RetryOrchestrator, RetryResult
from src.mge.v2.validation.atomic_validator import AtomicValidationResult
from src.mge.v2.validation.models import ValidationSeverity, ValidationIssue


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = AsyncMock()
    client.generate_with_caching = AsyncMock(return_value={
        "content": "def foo():\n    pass",
        "cached": False,
        "cost_usd": 0.01
    })
    return client


@pytest.fixture
def mock_validator():
    """Mock validator."""
    validator = AsyncMock()
    validator.validate = AsyncMock()
    return validator


@pytest.fixture
def mock_atom_spec():
    """Mock atomic unit specification."""
    atom = Mock()
    atom.id = uuid4()
    atom.name = "test_function"
    atom.description = "Test function description"
    atom.estimated_loc = 10
    atom.language = "Python"
    atom.code = None
    atom.context = {}
    atom.complexity = "low"
    return atom


@pytest.mark.asyncio
class TestRetryOrchestratorBasics:
    """Test basic RetryOrchestrator functionality."""

    async def test_initialization(self, mock_llm_client, mock_validator):
        """Test RetryOrchestrator initialization."""
        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        assert orchestrator.llm_client == mock_llm_client
        assert orchestrator.validator == mock_validator
        assert orchestrator.MAX_ATTEMPTS == 4
        assert orchestrator.TEMPERATURE_SCHEDULE == [0.7, 0.5, 0.3, 0.3]

    async def test_successful_first_attempt(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test successful code generation on first attempt."""
        # Setup: validation passes on first attempt
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True,
            issues=[],
            metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is True
        assert result.attempts_used == 1
        assert result.code == "def foo():\n    pass"
        assert result.validation_result.passed is True
        assert mock_llm_client.generate_with_caching.call_count == 1

    async def test_successful_second_attempt(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test successful code generation on second attempt after first fails."""
        # Setup: validation fails first, passes second
        mock_validator.validate.side_effect = [
            AtomicValidationResult(
                passed=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="syntax",
                        message="Syntax error",
                        location={"line": 1, "column": 0}
                    )
                ],
                metrics={}
            ),
            AtomicValidationResult(
                passed=True,
                issues=[],
                metrics={}
            ),
        ]

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is True
        assert result.attempts_used == 2
        assert mock_llm_client.generate_with_caching.call_count == 2
        assert mock_validator.validate.call_count == 2


@pytest.mark.asyncio
class TestRetryLogic:
    """Test retry loop and temperature backoff."""

    async def test_temperature_backoff(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test temperature decreases on each retry."""
        # Setup: all attempts fail
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="test",
                    message="Error",
                    location={"line": 1, "column": 0}
                )
            ],
            metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify temperature schedule was followed
        assert mock_llm_client.generate_with_caching.call_count == 4

        calls = mock_llm_client.generate_with_caching.call_args_list
        assert calls[0][1]["temperature"] == 0.7  # Attempt 1
        assert calls[1][1]["temperature"] == 0.5  # Attempt 2
        assert calls[2][1]["temperature"] == 0.3  # Attempt 3
        assert calls[3][1]["temperature"] == 0.3  # Attempt 4

    async def test_max_attempts_exhausted(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test all attempts fail."""
        # Setup: all attempts fail
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="test",
                    message="Critical error",
                    location={"line": 1, "column": 0}
                )
            ],
            metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is False
        assert result.attempts_used == 4
        assert result.error_message is not None
        assert "Failed after 4 attempts" in result.error_message
        assert mock_llm_client.generate_with_caching.call_count == 4

    async def test_early_exit_on_success(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test early exit when validation passes before max attempts."""
        # Setup: third attempt succeeds
        mock_validator.validate.side_effect = [
            AtomicValidationResult(passed=False, issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="test",
                    message="Error 1",
                    location={"line": 1, "column": 0}
                )
            ], metrics={}),
            AtomicValidationResult(passed=False, issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="test",
                    message="Error 2",
                    location={"line": 1, "column": 0}
                )
            ], metrics={}),
            AtomicValidationResult(passed=True, issues=[], metrics={}),
        ]

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify: only 3 attempts, not 4
        assert result.success is True
        assert result.attempts_used == 3
        assert mock_llm_client.generate_with_caching.call_count == 3


@pytest.mark.asyncio
class TestErrorFeedback:
    """Test error feedback to LLM on retries."""

    async def test_error_feedback_on_retry(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test previous errors are passed to LLM on retry."""
        # Setup: first attempt fails, second succeeds
        mock_validator.validate.side_effect = [
            AtomicValidationResult(
                passed=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="syntax",
                        message="Missing colon",
                        location={"line": 1, "column": 10}
                    ),
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="indent",
                        message="Indentation error",
                        location={"line": 2, "column": 0}
                    ),
                ],
                metrics={}
            ),
            AtomicValidationResult(passed=True, issues=[], metrics={}),
        ]

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is True
        assert result.attempts_used == 2

        # Check second call includes retry information
        second_call = mock_llm_client.generate_with_caching.call_args_list[1]
        variable_prompt = second_call[1]["variable_prompt"]

        assert "RETRY ATTEMPT 2" in variable_prompt
        assert "Missing colon" in variable_prompt
        assert "Indentation error" in variable_prompt

    async def test_only_critical_and_error_severity(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test only CRITICAL and ERROR severity issues are passed to retry."""
        # Setup: first attempt fails with mixed severities
        mock_validator.validate.side_effect = [
            AtomicValidationResult(
                passed=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="test",
                        message="Critical issue",
                        location={"line": 1, "column": 0}
                    ),
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="test",
                        message="Error issue",
                        location={"line": 2, "column": 0}
                    ),
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="test",
                        message="Warning issue",
                        location={"line": 3, "column": 0}
                    ),
                ],
                metrics={}
            ),
            AtomicValidationResult(passed=True, issues=[], metrics={}),
        ]

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        second_call = mock_llm_client.generate_with_caching.call_args_list[1]
        variable_prompt = second_call[1]["variable_prompt"]

        # Should include CRITICAL and ERROR, not WARNING
        assert "Critical issue" in variable_prompt
        assert "Error issue" in variable_prompt
        assert "Warning issue" not in variable_prompt


@pytest.mark.asyncio
class TestCodeExtraction:
    """Test code extraction from LLM responses."""

    async def test_extract_code_with_markdown_blocks(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test code extraction from markdown code blocks."""
        # Setup
        mock_llm_client.generate_with_caching.return_value = {
            "content": "```python\ndef foo():\n    return 42\n```",
            "cached": False,
            "cost_usd": 0.01
        }
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify: language identifier stripped
        assert result.code == "def foo():\n    return 42"

    async def test_extract_code_without_markdown(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test code extraction when no markdown blocks present."""
        # Setup
        mock_llm_client.generate_with_caching.return_value = {
            "content": "def bar():\n    return True",
            "cached": False,
            "cost_usd": 0.01
        }
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify: code returned as-is
        assert result.code == "def bar():\n    return True"


@pytest.mark.asyncio
class TestDependenciesHandling:
    """Test dependency formatting and usage."""

    async def test_format_dependencies_empty(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test formatting when no dependencies."""
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is True

        # Check cacheable context includes "No dependencies"
        call_args = mock_llm_client.generate_with_caching.call_args_list[0]
        cacheable_context = call_args[1]["cacheable_context"]
        assert "dependencies" in cacheable_context
        assert "No dependencies" in cacheable_context["dependencies"]

    async def test_format_dependencies_with_code(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test formatting dependencies with code."""
        # Setup dependencies
        dep1 = Mock()
        dep1.name = "dependency_1"
        dep1.code = "def dep1():\n    pass"

        dep2 = Mock()
        dep2.name = "dependency_2"
        dep2.code = "def dep2():\n    pass"

        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[dep1, dep2]
        )

        # Verify
        assert result.success is True

        # Check dependencies formatted correctly
        call_args = mock_llm_client.generate_with_caching.call_args_list[0]
        cacheable_context = call_args[1]["cacheable_context"]
        deps_text = cacheable_context["dependencies"]

        assert "dependency_1" in deps_text
        assert "dependency_2" in deps_text
        assert "def dep1():" in deps_text
        assert "def dep2():" in deps_text

    async def test_format_dependencies_max_limit(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test max 10 dependencies are included."""
        # Setup 15 dependencies
        dependencies = []
        for i in range(15):
            dep = Mock()
            dep.name = f"dep_{i}"
            dep.code = f"def dep_{i}(): pass"
            dependencies.append(dep)

        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=dependencies
        )

        # Verify
        call_args = mock_llm_client.generate_with_caching.call_args_list[0]
        cacheable_context = call_args[1]["cacheable_context"]
        deps_text = cacheable_context["dependencies"]

        # Should show "and 5 more dependencies"
        assert "and 5 more dependencies" in deps_text


@pytest.mark.asyncio
class TestExceptionHandling:
    """Test exception handling during retry."""

    async def test_exception_during_generation(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test exception during code generation is handled."""
        # Setup: exception on first attempt, success on second
        mock_llm_client.generate_with_caching.side_effect = [
            Exception("LLM API error"),
            {
                "content": "def foo():\n    pass",
                "cached": False,
                "cost_usd": 0.01
            }
        ]
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify: should recover on second attempt
        assert result.success is True
        assert result.attempts_used == 2

    async def test_exception_all_attempts(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test all attempts fail due to exceptions."""
        # Setup: exception on all attempts
        mock_llm_client.generate_with_caching.side_effect = Exception("Persistent error")

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is False
        assert result.attempts_used == 4
        assert "Persistent error" in result.error_message


@pytest.mark.asyncio
class TestMetricsEmission:
    """Test Prometheus metrics emission."""

    @patch("src.mge.v2.execution.retry_orchestrator.RETRY_ATTEMPTS_TOTAL")
    @patch("src.mge.v2.execution.retry_orchestrator.RETRY_TEMPERATURE_CHANGES")
    @patch("src.mge.v2.execution.retry_orchestrator.update_success_rate")
    async def test_metrics_emitted_on_success(
        self, mock_update_rate, mock_temp_metric, mock_attempts_metric,
        mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test metrics are emitted on successful execution."""
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify
        assert result.success is True
        assert mock_attempts_metric.labels.called
        assert mock_update_rate.called

    @patch("src.mge.v2.execution.retry_orchestrator.RETRY_TEMPERATURE_CHANGES")
    async def test_temperature_change_metrics(
        self, mock_temp_metric,
        mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test temperature change metrics on retries."""
        # Setup: fails twice, then succeeds
        mock_validator.validate.side_effect = [
            AtomicValidationResult(passed=False, issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="test",
                    message="Error",
                    location={"line": 1, "column": 0}
                )
            ], metrics={}),
            AtomicValidationResult(passed=False, issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="test",
                    message="Error",
                    location={"line": 1, "column": 0}
                )
            ], metrics={}),
            AtomicValidationResult(passed=True, issues=[], metrics={}),
        ]

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[]
        )

        # Verify: 2 temperature changes (attempt 1→2, 2→3)
        assert result.success is True
        assert mock_temp_metric.labels.call_count == 2


@pytest.mark.asyncio
class TestMasterplanIntegration:
    """Test masterplan ID integration for cache invalidation."""

    async def test_masterplan_id_passed_to_llm(
        self, mock_llm_client, mock_validator, mock_atom_spec
    ):
        """Test masterplan ID is passed to LLM client."""
        mock_validator.validate.return_value = AtomicValidationResult(
            passed=True, issues=[], metrics={}
        )

        orchestrator = RetryOrchestrator(mock_llm_client, mock_validator)
        masterplan_id = uuid4()

        # Execute
        result = await orchestrator.execute_with_retry(
            atom_spec=mock_atom_spec,
            dependencies=[],
            masterplan_id=masterplan_id
        )

        # Verify
        assert result.success is True

        # Check masterplan_id passed
        call_args = mock_llm_client.generate_with_caching.call_args_list[0]
        assert call_args[1]["masterplan_id"] == str(masterplan_id)
