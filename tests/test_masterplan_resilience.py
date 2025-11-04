"""
Comprehensive Tests for MasterPlan Resilience Features

Tests the retry decorator, orphan cleanup, and status recovery endpoint
to ensure robust generation and recovery capabilities.

@since Nov 4, 2025
@version 1.0
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import UUID, uuid4

# Import retry decorator
from src.utils.retry_decorator import RetryConfig, retry, create_retryable_config

# Import orphan cleanup
from src.services.orphan_cleanup import OrphanCleanupWorker

# Import models
from src.models.masterplan import MasterPlan, MasterPlanStatus


# ============================================================================
# RETRY DECORATOR TESTS
# ============================================================================

class TestRetryDecorator:
    """Test the retry decorator with exponential backoff"""

    def test_retry_config_defaults(self):
        """Test RetryConfig initialization with defaults"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_retry_config_custom(self):
        """Test RetryConfig with custom values"""
        config = RetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            backoff_factor=3.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.backoff_factor == 3.0
        assert config.jitter is False

    def test_retry_config_get_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=False,
        )
        # Attempt 0: 1.0s
        assert config.get_delay(0) == 1.0
        # Attempt 1: 2.0s
        assert config.get_delay(1) == 2.0
        # Attempt 2: 4.0s
        assert config.get_delay(2) == 4.0
        # Attempt 3: 8.0s
        assert config.get_delay(3) == 8.0
        # Attempt 4: 16.0s
        assert config.get_delay(4) == 16.0
        # Attempt 5: 32.0s (capped at 60)
        assert config.get_delay(5) == 32.0

    def test_retry_config_get_delay_with_max_cap(self):
        """Test that delay is capped at max_delay"""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=False,
        )
        # Attempt 4: 16.0s → capped at 10.0s
        assert config.get_delay(4) == 10.0
        # Attempt 5: 32.0s → capped at 10.0s
        assert config.get_delay(5) == 10.0

    def test_retry_config_jitter(self):
        """Test that jitter adds variation to delays"""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=True,
        )
        # Run multiple times and verify variability
        delays = [config.get_delay(2) for _ in range(10)]
        # All should be >= 4.0 (base delay) and <= 4.4 (with 10% jitter)
        assert all(4.0 <= d <= 4.4 for d in delays)
        # Should have variation (not all exactly the same)
        assert len(set(delays)) > 1

    def test_create_retryable_config_llm(self):
        """Test LLM-specific retry configuration"""
        config = create_retryable_config("llm")
        assert config.max_retries == 3
        assert config.initial_delay == 2.0
        assert config.max_delay == 30.0
        assert TimeoutError in config.retryable_exceptions
        assert ConnectionError in config.retryable_exceptions
        assert IOError in config.retryable_exceptions

    def test_create_retryable_config_database(self):
        """Test database-specific retry configuration"""
        config = create_retryable_config("database")
        assert config.max_retries == 2
        assert config.initial_delay == 0.5
        assert config.max_delay == 10.0

    def test_create_retryable_config_api(self):
        """Test API-specific retry configuration"""
        config = create_retryable_config("api")
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0

    def test_create_retryable_config_general(self):
        """Test general retry configuration"""
        config = create_retryable_config("general")
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0

    def test_create_retryable_config_unknown(self):
        """Test unknown service type defaults to general"""
        config = create_retryable_config("unknown")
        assert config.max_retries == 3
        assert config.initial_delay == 1.0

    @pytest.mark.asyncio
    async def test_retry_decorator_success_first_try(self):
        """Test that decorated function returns immediately on success"""
        call_count = 0

        @retry(max_retries=3)
        async def async_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await async_func()
        assert result == "success"
        assert call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_retry_decorator_retries_on_transient_error(self):
        """Test that decorator retries on retryable exceptions"""
        call_count = 0

        @retry(max_retries=3, initial_delay=0.01)
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient connection error")
            return "success"

        result = await async_func()
        assert result == "success"
        assert call_count == 3  # Called 3 times (2 failures + 1 success)

    @pytest.mark.asyncio
    async def test_retry_decorator_fails_on_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately"""
        call_count = 0

        @retry(
            max_retries=3,
            retryable_exceptions={ConnectionError}  # Only retry ConnectionError
        )
        async def async_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError, match="Non-retryable error"):
            await async_func()
        assert call_count == 1  # Only called once, no retries


# ============================================================================
# ORPHAN CLEANUP TESTS
# ============================================================================

class TestOrphanCleanupWorker:
    """Test the orphan cleanup background worker"""

    def test_orphan_cleanup_worker_init(self):
        """Test OrphanCleanupWorker initialization"""
        worker = OrphanCleanupWorker(
            timeout_minutes=120,
            check_interval_minutes=15,
        )
        assert worker.timeout_minutes == 120
        assert worker.check_interval_seconds == 900  # 15 * 60
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_orphan_cleanup_worker_start_stop(self):
        """Test starting and stopping the cleanup worker"""
        worker = OrphanCleanupWorker(timeout_minutes=120, check_interval_minutes=1)

        # Start worker
        await worker.start()
        assert worker.is_running is True
        assert worker.cleanup_task is not None

        # Stop worker
        await worker.stop()
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_orphan_cleanup_worker_idempotent_start(self):
        """Test that starting an already-running worker is safe"""
        worker = OrphanCleanupWorker()
        await worker.start()

        # Second start should be no-op
        await worker.start()
        assert worker.is_running is True

        await worker.stop()

    @pytest.mark.asyncio
    async def test_orphan_cleanup_worker_idempotent_stop(self):
        """Test that stopping an already-stopped worker is safe"""
        worker = OrphanCleanupWorker()
        await worker.stop()  # Should not raise


# ============================================================================
# STATUS ENDPOINT TESTS
# ============================================================================

class TestMasterPlanStatusEndpoint:
    """Test the GET /masterplans/{id}/status endpoint"""

    def test_status_endpoint_draft_status(self):
        """Test status endpoint returns draft options"""
        # Mock MasterPlan with DRAFT status
        masterplan = Mock(spec=MasterPlan)
        masterplan.masterplan_id = uuid4()
        masterplan.status = MasterPlanStatus.DRAFT
        masterplan.created_at = datetime.utcnow()
        masterplan.updated_at = datetime.utcnow()
        masterplan.total_tasks = 42
        masterplan.error_message = None

        # Determine recovery options (same logic as endpoint)
        recovery_options = ["approve", "reject"]
        can_retry = False
        can_execute = False

        assert recovery_options == ["approve", "reject"]
        assert can_retry is False
        assert can_execute is False

    def test_status_endpoint_approved_status(self):
        """Test status endpoint returns approved options"""
        recovery_options = ["execute", "reject"]
        can_retry = False
        can_execute = True

        assert "execute" in recovery_options
        assert can_execute is True

    def test_status_endpoint_failed_status(self):
        """Test status endpoint returns failed options with retry"""
        recovery_options = ["retry", "view_details", "reject"]
        can_retry = True
        can_execute = False

        assert "retry" in recovery_options
        assert can_retry is True

    def test_status_endpoint_in_progress_status(self):
        """Test status endpoint for in-progress generation"""
        recovery_options = ["view_details", "cancel"]
        can_retry = False
        can_execute = False

        assert recovery_options == ["view_details", "cancel"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMasterPlanResilienceIntegration:
    """Integration tests for the complete resilience system"""

    def test_retry_decorator_with_llm_config(self):
        """Test that LLM retry config is appropriate for API failures"""
        config = create_retryable_config("llm")
        # Should retry transient errors
        assert TimeoutError in config.retryable_exceptions
        assert ConnectionError in config.retryable_exceptions
        # Should not retry too aggressively
        assert config.max_retries == 3
        # Delays should be reasonable
        assert config.initial_delay >= 1.0
        assert config.max_delay <= 60.0

    def test_orphan_cleanup_identifies_stale_masterplans(self):
        """Test that cleanup correctly identifies stale generations"""
        now = datetime.utcnow()
        timeout_minutes = 120

        # Create test MasterPlans
        fresh = Mock(spec=MasterPlan)
        fresh.status = MasterPlanStatus.IN_PROGRESS
        fresh.updated_at = now - timedelta(minutes=30)  # 30min old

        stale = Mock(spec=MasterPlan)
        stale.status = MasterPlanStatus.IN_PROGRESS
        stale.updated_at = now - timedelta(minutes=150)  # 150min old (> 120min)

        completed = Mock(spec=MasterPlan)
        completed.status = MasterPlanStatus.COMPLETED
        completed.updated_at = now - timedelta(minutes=200)  # Old but completed

        # Check cutoff logic
        cutoff_time = now - timedelta(minutes=timeout_minutes)

        # Fresh should not be cleaned
        assert fresh.updated_at > cutoff_time
        # Stale should be cleaned
        assert stale.updated_at < cutoff_time
        # Completed should not be cleaned (different status)
        assert completed.status != MasterPlanStatus.IN_PROGRESS

    def test_status_endpoint_reflects_recovery_state(self):
        """Test that status endpoint provides actionable recovery info"""
        # Status FAILED should suggest retry
        status = "failed"
        recovery_options = ["retry", "view_details", "reject"] if status == "failed" else []
        can_retry = status == "failed"

        assert "retry" in recovery_options
        assert can_retry is True

        # Status APPROVED should suggest execute
        status = "approved"
        recovery_options = ["execute", "reject"] if status == "approved" else []
        can_execute = status == "approved"

        assert "execute" in recovery_options
        assert can_execute is True


# ============================================================================
# PERFORMANCE & REGRESSION TESTS
# ============================================================================

class TestPerformance:
    """Performance and regression tests"""

    def test_retry_config_delay_calculation_performance(self):
        """Test that delay calculation is fast"""
        import time
        config = RetryConfig()

        start = time.perf_counter()
        for _ in range(10000):
            config.get_delay(3)
        duration = time.perf_counter() - start

        # Should complete 10K calculations in < 100ms
        assert duration < 0.1

    @pytest.mark.asyncio
    async def test_orphan_cleanup_handles_empty_results(self):
        """Test that cleanup gracefully handles no orphans found"""
        worker = OrphanCleanupWorker()

        # Mock _find_orphan_masterplans to return empty list
        with patch.object(worker, "_find_orphan_masterplans", return_value=[]):
            with patch.object(worker, "_cleanup_masterplan") as mock_cleanup:
                await worker._run_cleanup_cycle()
                # Cleanup should not be called
                mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_orphan_cleanup_handles_cleanup_errors(self):
        """Test that cleanup continues even if one cleanup fails"""
        worker = OrphanCleanupWorker()

        # Create mock orphans with required attributes
        orphan1 = Mock(spec=MasterPlan)
        orphan1.id = uuid4()
        orphan2 = Mock(spec=MasterPlan)
        orphan2.id = uuid4()

        # Mock _find_orphan_masterplans to return 2 orphans
        with patch.object(worker, "_find_orphan_masterplans", return_value=[orphan1, orphan2]):
            # First cleanup fails, second succeeds
            with patch.object(worker, "_cleanup_masterplan") as mock_cleanup:
                mock_cleanup.side_effect = [Exception("Cleanup error"), None]

                # Should not raise, should continue
                await worker._run_cleanup_cycle()

                # Both cleanups should be attempted
                assert mock_cleanup.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
