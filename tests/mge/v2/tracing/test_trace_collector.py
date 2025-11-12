"""
Tests for TraceCollector

Complete test coverage for E2E tracing system.
"""
import pytest
from uuid import UUID, uuid4
from src.mge.v2.tracing.collector import TraceCollector
from src.mge.v2.tracing.models import (
    AtomTrace,
    TraceCorrelation,
    ValidationTrace
)
from src.mge.v2.validation.atomic_validator import AtomicValidationResult


@pytest.fixture
def collector():
    """Create fresh TraceCollector instance."""
    return TraceCollector()


@pytest.fixture
def masterplan_id():
    """Create masterplan ID."""
    return uuid4()


@pytest.fixture
def atom_id():
    """Create atom ID."""
    return uuid4()


class TestTraceCollectorBasics:
    """Test basic TraceCollector functionality."""

    def test_initialization(self, collector):
        """Test that collector initializes empty."""
        assert len(collector.traces) == 0
        assert len(collector.atom_traces) == 0
        assert len(collector.masterplan_traces) == 0

    def test_start_trace(self, collector, atom_id, masterplan_id):
        """Test starting a new trace."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom",
            context_data={"key": "value"},
            dependencies=["dep1", "dep2"]
        )

        assert isinstance(trace, AtomTrace)
        assert trace.atom_id == atom_id
        assert trace.masterplan_id == masterplan_id
        assert trace.wave_id == 1
        assert trace.atom_name == "test_atom"
        assert trace.context_data == {"key": "value"}
        assert trace.dependencies == ["dep1", "dep2"]
        assert len(trace.events) == 1  # ATOM_STARTED event

    def test_get_trace_by_atom(self, collector, atom_id, masterplan_id):
        """Test retrieving trace by atom ID."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert retrieved is not None
        assert retrieved.trace_id == trace.trace_id

    def test_get_trace_by_atom_not_found(self, collector):
        """Test getting trace for unknown atom."""
        result = collector.get_trace_by_atom(uuid4())
        assert result is None

    def test_get_trace(self, collector, atom_id, masterplan_id):
        """Test retrieving trace by trace ID."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        retrieved = collector.get_trace(trace.trace_id)
        assert retrieved is not None
        assert retrieved.atom_id == atom_id

    def test_get_masterplan_traces(self, collector, masterplan_id):
        """Test getting all traces for a masterplan."""
        # Create 3 atoms
        atom1 = uuid4()
        atom2 = uuid4()
        atom3 = uuid4()

        collector.start_trace(atom1, masterplan_id, 1, "atom1")
        collector.start_trace(atom2, masterplan_id, 1, "atom2")
        collector.start_trace(atom3, masterplan_id, 2, "atom3")

        traces = collector.get_masterplan_traces(masterplan_id)
        assert len(traces) == 3


class TestRetryTracking:
    """Test retry attempt tracking."""

    def test_record_retry_attempt(self, collector, atom_id, masterplan_id):
        """Test recording retry attempt."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        collector.record_retry_attempt(
            atom_id=atom_id,
            attempt=1,
            temperature=0.7,
            success=False,
            duration_ms=1000.0,
            error_feedback=["error1", "error2"]
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert len(retrieved.retries) == 1
        assert retrieved.retries[0].attempt_number == 1
        assert retrieved.retries[0].temperature == 0.7
        assert retrieved.retries[0].success is False
        assert retrieved.retries[0].duration_ms == 1000.0
        assert retrieved.retries[0].error_feedback == ["error1", "error2"]
        assert retrieved.total_attempts == 1

    def test_record_multiple_retries(self, collector, atom_id, masterplan_id):
        """Test recording multiple retry attempts."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        # Record 3 retries
        for i in range(1, 4):
            collector.record_retry_attempt(
                atom_id=atom_id,
                attempt=i,
                temperature=0.7 - (i * 0.1),
                success=(i == 3),  # Success on 3rd attempt
                duration_ms=1000.0 * i
            )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert len(retrieved.retries) == 3
        assert retrieved.total_attempts == 3
        assert retrieved.retries[2].success is True


class TestValidationTracking:
    """Test validation tracking."""

    def test_record_validation(self, collector, atom_id, masterplan_id):
        """Test recording validation results."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        validation_result = AtomicValidationResult(
            passed=True,
            issues=[],
            metrics={
                "l1_syntax": {"passed": True},
                "l2_imports": {"passed": True},
                "l3_types": {"passed": False},
                "l4_complexity": {"passed": True}
            }
        )

        collector.record_validation(
            atom_id=atom_id,
            validation_result=validation_result,
            duration_ms=500.0
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert retrieved.validation.total_duration_ms == 500.0
        assert retrieved.validation.passed is True
        assert retrieved.validation.issues_count == 0
        assert retrieved.time.validation_duration_ms == 500.0

    def test_validation_events_recorded(self, collector, atom_id, masterplan_id):
        """Test that validation L1-L4 events are recorded."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        validation_result = AtomicValidationResult(
            passed=True,
            issues=[],
            metrics={
                "l1_syntax": {"passed": True},
                "l2_imports": {"passed": True},
                "l3_types": {"passed": True},
                "l4_complexity": {"passed": True}
            }
        )

        collector.record_validation(atom_id, validation_result, 500.0)

        retrieved = collector.get_trace_by_atom(atom_id)
        # Should have ATOM_STARTED + L1 + L2 + L3 + L4 events
        assert len(retrieved.events) >= 5


class TestAcceptanceTestsTracking:
    """Test acceptance tests tracking."""

    def test_record_acceptance_tests(self, collector, atom_id, masterplan_id):
        """Test recording acceptance test results."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        collector.record_acceptance_tests(
            atom_id=atom_id,
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            must_pass_rate=1.0,
            should_pass_rate=0.9,
            duration_ms=2000.0
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert retrieved.acceptance_tests is not None
        assert retrieved.acceptance_tests.total_tests == 10
        assert retrieved.acceptance_tests.passed_tests == 9
        assert retrieved.acceptance_tests.failed_tests == 1
        assert retrieved.acceptance_tests.must_pass_rate == 1.0
        assert retrieved.acceptance_tests.should_pass_rate == 0.9
        assert retrieved.time.acceptance_duration_ms == 2000.0


class TestCostTracking:
    """Test cost tracking."""

    def test_record_cost(self, collector, atom_id, masterplan_id):
        """Test recording LLM cost metrics."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        collector.record_cost(
            atom_id=atom_id,
            llm_api_cost_usd=0.05,
            prompt_tokens=1000,
            completion_tokens=500,
            cache_hit=True
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert retrieved.cost.llm_api_cost_usd == 0.05
        assert retrieved.cost.prompt_tokens == 1000
        assert retrieved.cost.completion_tokens == 500
        assert retrieved.cost.total_tokens == 1500
        assert retrieved.cost.cache_hit is True


class TestTraceCompletion:
    """Test trace completion."""

    def test_complete_trace_success(self, collector, atom_id, masterplan_id):
        """Test completing trace with success."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        code = "def foo(): pass"
        collector.complete_trace(
            atom_id=atom_id,
            success=True,
            code=code
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert retrieved.final_status == "success"
        assert retrieved.code_generated == code
        assert retrieved.completed_at is not None
        assert retrieved.time.total_duration_ms > 0

    def test_complete_trace_failure(self, collector, atom_id, masterplan_id):
        """Test completing trace with failure."""
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="test_atom"
        )

        collector.complete_trace(
            atom_id=atom_id,
            success=False,
            error="Validation failed"
        )

        retrieved = collector.get_trace_by_atom(atom_id)
        assert retrieved.final_status == "failed"
        assert retrieved.completed_at is not None


class TestCorrelationAnalysis:
    """Test correlation calculations."""

    def test_calculate_correlations_empty(self, collector, masterplan_id):
        """Test correlation calculation with no traces."""
        correlations = collector.calculate_correlations(masterplan_id)

        assert correlations.total_atoms == 0
        assert correlations.avg_retries_success == 0.0
        assert correlations.avg_retries_failed == 0.0

    def test_calculate_correlations_with_traces(self, collector, masterplan_id):
        """Test correlation calculation with multiple traces."""
        # Create 2 successful atoms
        for i in range(2):
            atom_id = uuid4()
            collector.start_trace(atom_id, masterplan_id, 1, f"atom_{i}")
            collector.record_retry_attempt(atom_id, 1, 0.7, True, 1000.0)
            collector.record_validation(
                atom_id,
                AtomicValidationResult(passed=True, issues=[], metrics={}),
                500.0
            )
            collector.complete_trace(atom_id, True, "code")

        # Create 1 failed atom with more retries
        failed_atom = uuid4()
        collector.start_trace(failed_atom, masterplan_id, 1, "failed_atom")
        for attempt in range(1, 4):
            collector.record_retry_attempt(failed_atom, attempt, 0.7, False, 1000.0)
        collector.record_validation(
            failed_atom,
            AtomicValidationResult(passed=False, issues=["error"], metrics={}),
            500.0
        )
        collector.complete_trace(failed_atom, False, error="Failed")

        correlations = collector.calculate_correlations(masterplan_id)

        assert correlations.total_atoms == 3
        assert correlations.avg_retries_success == 1.0  # 2 atoms with 1 attempt each
        assert correlations.avg_retries_failed == 3.0  # 1 atom with 3 attempts
        assert correlations.avg_l1_issues_success == 0.0  # No issues
        assert correlations.avg_l1_issues_failed == 1.0  # 1 issue


class TestTraceClearance:
    """Test trace clearance functionality."""

    def test_clear_traces_for_masterplan(self, collector, masterplan_id):
        """Test clearing traces for specific masterplan."""
        # Create traces for masterplan
        atom1 = uuid4()
        atom2 = uuid4()
        collector.start_trace(atom1, masterplan_id, 1, "atom1")
        collector.start_trace(atom2, masterplan_id, 1, "atom2")

        # Create trace for different masterplan
        other_masterplan = uuid4()
        atom3 = uuid4()
        collector.start_trace(atom3, other_masterplan, 1, "atom3")

        # Clear first masterplan
        collector.clear_traces(masterplan_id)

        # First masterplan traces should be gone
        assert len(collector.get_masterplan_traces(masterplan_id)) == 0

        # Other masterplan trace should still exist
        assert len(collector.get_masterplan_traces(other_masterplan)) == 1

    def test_clear_all_traces(self, collector, masterplan_id):
        """Test clearing all traces."""
        atom1 = uuid4()
        atom2 = uuid4()
        collector.start_trace(atom1, masterplan_id, 1, "atom1")
        collector.start_trace(atom2, masterplan_id, 1, "atom2")

        collector.clear_traces()

        assert len(collector.traces) == 0
        assert len(collector.atom_traces) == 0
        assert len(collector.masterplan_traces) == 0


class TestGlobalCollector:
    """Test global collector instance."""

    def test_get_trace_collector(self):
        """Test that get_trace_collector returns singleton."""
        from src.mge.v2.tracing.collector import get_trace_collector

        collector1 = get_trace_collector()
        collector2 = get_trace_collector()

        assert collector1 is collector2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_record_validation_without_trace(self, collector):
        """Test recording validation when no trace exists for atom."""
        from uuid import uuid4

        fake_atom_id = uuid4()
        validation_result = AtomicValidationResult(
            passed=True,
            issues=[],
            metrics={}
        )

        # Should not raise exception, just log warning
        collector.record_validation(
            atom_id=fake_atom_id,
            validation_result=validation_result,
            duration_ms=500.0
        )

        # Verify trace was not created
        assert collector.get_trace_by_atom(fake_atom_id) is None

    def test_record_retry_without_trace(self, collector):
        """Test recording retry when no trace exists for atom."""
        from uuid import uuid4

        fake_atom_id = uuid4()

        # Should not raise exception, just log warning
        collector.record_retry_attempt(
            atom_id=fake_atom_id,
            attempt=1,
            temperature=0.7,
            success=False,
            duration_ms=1000.0
        )

        # Verify trace was not created
        assert collector.get_trace_by_atom(fake_atom_id) is None

    def test_record_acceptance_tests_without_trace(self, collector):
        """Test recording acceptance tests when no trace exists for atom."""
        from uuid import uuid4

        fake_atom_id = uuid4()

        # Should not raise exception, just log warning
        collector.record_acceptance_tests(
            atom_id=fake_atom_id,
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            must_pass_rate=1.0,
            should_pass_rate=0.9,
            duration_ms=2000.0
        )

        # Verify trace was not created
        assert collector.get_trace_by_atom(fake_atom_id) is None

    def test_record_cost_without_trace(self, collector):
        """Test recording cost when no trace exists for atom."""
        from uuid import uuid4

        fake_atom_id = uuid4()

        # Should not raise exception, just log warning
        collector.record_cost(
            atom_id=fake_atom_id,
            llm_api_cost_usd=0.05,
            prompt_tokens=1000,
            completion_tokens=500
        )

        # Verify trace was not created
        assert collector.get_trace_by_atom(fake_atom_id) is None

    def test_complete_trace_without_trace(self, collector):
        """Test completing trace when no trace exists for atom."""
        from uuid import uuid4

        fake_atom_id = uuid4()

        # Should not raise exception, just log warning
        collector.complete_trace(
            atom_id=fake_atom_id,
            success=True,
            code="def foo(): pass"
        )

        # Verify trace was not created
        assert collector.get_trace_by_atom(fake_atom_id) is None
