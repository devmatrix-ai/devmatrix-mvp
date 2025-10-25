"""
Unit Tests - CostGuardrails

Tests cost limit enforcement with soft/hard caps and alerting.

Author: DevMatrix Team
Date: 2025-10-25
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from src.cost.cost_guardrails import CostGuardrails, CostLimitExceeded, CostLimits
from src.cost.cost_tracker import CostBreakdown


@pytest.fixture
def mock_cost_tracker():
    """Create mock CostTracker"""
    tracker = MagicMock()
    return tracker


@pytest.fixture
def guardrails(mock_cost_tracker):
    """Create CostGuardrails instance"""
    return CostGuardrails(
        cost_tracker=mock_cost_tracker,
        default_soft_limit=50.0,
        default_hard_limit=100.0
    )


@pytest.fixture
def masterplan_id():
    """Sample masterplan UUID"""
    return uuid4()


@pytest.fixture
def atom_id():
    """Sample atom UUID"""
    return uuid4()


# ============================================================================
# Set Limits Tests
# ============================================================================

def test_set_masterplan_limits_success(guardrails, masterplan_id):
    """Test setting custom limits for masterplan"""
    guardrails.set_masterplan_limits(
        masterplan_id=masterplan_id,
        soft_limit_usd=40.0,
        hard_limit_usd=80.0,
        per_atom_limit_usd=5.0
    )

    limits = guardrails._masterplan_limits[masterplan_id]
    assert limits.soft_limit_usd == 40.0
    assert limits.hard_limit_usd == 80.0
    assert limits.per_atom_limit_usd == 5.0


def test_set_limits_soft_exceeds_hard_error(guardrails, masterplan_id):
    """Test error when soft limit >= hard limit"""
    with pytest.raises(ValueError, match="Soft limit must be less than hard limit"):
        guardrails.set_masterplan_limits(
            masterplan_id=masterplan_id,
            soft_limit_usd=100.0,
            hard_limit_usd=80.0
        )


def test_set_limits_equal_error(guardrails, masterplan_id):
    """Test error when soft limit equals hard limit"""
    with pytest.raises(ValueError):
        guardrails.set_masterplan_limits(
            masterplan_id=masterplan_id,
            soft_limit_usd=50.0,
            hard_limit_usd=50.0
        )


# ============================================================================
# Check Limits Tests - Within Limits
# ============================================================================

def test_check_limits_within_all_limits(guardrails, masterplan_id, mock_cost_tracker):
    """Test check when cost is within all limits"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=25.0,
        total_input_tokens=50000,
        total_output_tokens=25000,
        call_count=5
    )

    result = guardrails.check_limits(masterplan_id)

    assert result['within_limits'] is True
    assert result['soft_limit_exceeded'] is False
    assert result['hard_limit_exceeded'] is False
    assert result['current_cost'] == 25.0
    assert result['soft_limit'] == 50.0
    assert result['hard_limit'] == 100.0
    assert result['usage_percentage'] == 25.0


def test_check_limits_uses_custom_limits(guardrails, masterplan_id, mock_cost_tracker):
    """Test check uses custom limits when set"""
    guardrails.set_masterplan_limits(
        masterplan_id=masterplan_id,
        soft_limit_usd=30.0,
        hard_limit_usd=60.0
    )

    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=25.0,
        total_input_tokens=50000,
        total_output_tokens=25000,
        call_count=5
    )

    result = guardrails.check_limits(masterplan_id)

    assert result['soft_limit'] == 30.0
    assert result['hard_limit'] == 60.0


# ============================================================================
# Check Limits Tests - Soft Limit Exceeded
# ============================================================================

def test_check_limits_soft_limit_exceeded(guardrails, masterplan_id, mock_cost_tracker):
    """Test soft limit exceeded triggers warning"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=60.0,
        total_input_tokens=120000,
        total_output_tokens=60000,
        call_count=10
    )

    with patch.object(guardrails, '_trigger_alert') as mock_alert:
        result = guardrails.check_limits(masterplan_id)

        assert result['soft_limit_exceeded'] is True
        assert result['hard_limit_exceeded'] is False
        assert result['within_limits'] is True

        # Alert should be triggered
        mock_alert.assert_called_once()
        assert mock_alert.call_args[1]['alert_type'] == 'soft_limit_exceeded'


def test_soft_limit_alert_only_once(guardrails, masterplan_id, mock_cost_tracker):
    """Test soft limit alert triggered only once"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=60.0,
        total_input_tokens=120000,
        total_output_tokens=60000,
        call_count=10
    )

    with patch.object(guardrails, '_trigger_alert') as mock_alert:
        # First check - should trigger alert
        guardrails.check_limits(masterplan_id)
        assert mock_alert.call_count == 1

        # Second check - should NOT trigger alert again
        guardrails.check_limits(masterplan_id)
        assert mock_alert.call_count == 1  # Still 1


# ============================================================================
# Check Limits Tests - Hard Limit Exceeded
# ============================================================================

def test_check_limits_hard_limit_exceeded(guardrails, masterplan_id, mock_cost_tracker):
    """Test hard limit exceeded raises exception"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=110.0,
        total_input_tokens=220000,
        total_output_tokens=110000,
        call_count=20
    )

    with pytest.raises(CostLimitExceeded) as exc_info:
        guardrails.check_limits(masterplan_id)

    assert exc_info.value.current_cost == 110.0
    assert exc_info.value.limit == 100.0


def test_hard_limit_triggers_alert(guardrails, masterplan_id, mock_cost_tracker):
    """Test hard limit exceeded triggers critical alert"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=110.0,
        total_input_tokens=220000,
        total_output_tokens=110000,
        call_count=20
    )

    with patch.object(guardrails, '_trigger_alert') as mock_alert:
        with pytest.raises(CostLimitExceeded):
            guardrails.check_limits(masterplan_id)

        mock_alert.assert_called_once()
        assert mock_alert.call_args[1]['alert_type'] == 'hard_limit_exceeded'


# ============================================================================
# Per-Atom Limit Tests
# ============================================================================

def test_per_atom_limit_not_exceeded(guardrails, masterplan_id, atom_id, mock_cost_tracker):
    """Test per-atom limit check when within limit"""
    guardrails.set_masterplan_limits(
        masterplan_id=masterplan_id,
        soft_limit_usd=50.0,
        hard_limit_usd=100.0,
        per_atom_limit_usd=5.0
    )

    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=25.0,
        total_input_tokens=50000,
        total_output_tokens=25000,
        call_count=5
    )

    mock_cost_tracker.get_atom_cost.return_value = CostBreakdown(
        total_cost_usd=3.0,
        total_input_tokens=6000,
        total_output_tokens=3000,
        call_count=1
    )

    result = guardrails.check_limits(masterplan_id, atom_id=atom_id)
    assert result['within_limits'] is True


def test_per_atom_limit_exceeded_logs_warning(guardrails, masterplan_id, atom_id, mock_cost_tracker):
    """Test per-atom limit exceeded logs warning (does not raise)"""
    guardrails.set_masterplan_limits(
        masterplan_id=masterplan_id,
        soft_limit_usd=50.0,
        hard_limit_usd=100.0,
        per_atom_limit_usd=5.0
    )

    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=25.0,
        total_input_tokens=50000,
        total_output_tokens=25000,
        call_count=5
    )

    mock_cost_tracker.get_atom_cost.return_value = CostBreakdown(
        total_cost_usd=7.0,  # Exceeds per-atom limit
        total_input_tokens=14000,
        total_output_tokens=7000,
        call_count=1
    )

    # Should not raise, just log warning
    result = guardrails.check_limits(masterplan_id, atom_id=atom_id)
    assert result['within_limits'] is True


# ============================================================================
# Check Before Execution Tests
# ============================================================================

def test_check_before_execution_sufficient_budget(guardrails, masterplan_id, mock_cost_tracker):
    """Test check before execution when budget is sufficient"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=30.0,
        total_input_tokens=60000,
        total_output_tokens=30000,
        call_count=5
    )

    # Mock cost calculation
    mock_cost_tracker._calculate_cost.return_value = 5.0  # Estimated cost

    # Should not raise (30 + 5 = 35 < 100)
    guardrails.check_before_execution(
        masterplan_id=masterplan_id,
        estimated_tokens=10000
    )


def test_check_before_execution_would_exceed_limit(guardrails, masterplan_id, mock_cost_tracker):
    """Test check before execution when operation would exceed limit"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=90.0,
        total_input_tokens=180000,
        total_output_tokens=90000,
        call_count=15
    )

    # Mock cost calculation
    mock_cost_tracker._calculate_cost.return_value = 15.0  # Would exceed (90 + 15 = 105 > 100)

    with pytest.raises(CostLimitExceeded) as exc_info:
        guardrails.check_before_execution(
            masterplan_id=masterplan_id,
            estimated_tokens=30000
        )

    assert exc_info.value.current_cost == 105.0


def test_check_before_execution_with_custom_limits(guardrails, masterplan_id, mock_cost_tracker):
    """Test check before execution respects custom limits"""
    guardrails.set_masterplan_limits(
        masterplan_id=masterplan_id,
        soft_limit_usd=40.0,
        hard_limit_usd=60.0
    )

    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=50.0,
        total_input_tokens=100000,
        total_output_tokens=50000,
        call_count=10
    )

    mock_cost_tracker._calculate_cost.return_value = 15.0  # Would exceed custom limit

    with pytest.raises(CostLimitExceeded):
        guardrails.check_before_execution(
            masterplan_id=masterplan_id,
            estimated_tokens=30000
        )


# ============================================================================
# Get Limit Status Tests
# ============================================================================

def test_get_limit_status_default_limits(guardrails, masterplan_id, mock_cost_tracker):
    """Test get limit status with default limits"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=35.0,
        total_input_tokens=70000,
        total_output_tokens=35000,
        call_count=7
    )

    status = guardrails.get_limit_status(masterplan_id)

    assert status['current_cost'] == 35.0
    assert status['soft_limit'] == 50.0
    assert status['hard_limit'] == 100.0
    assert status['usage_percentage'] == 35.0
    assert status['remaining_budget'] == 65.0
    assert status['calls_made'] == 7


def test_get_limit_status_custom_limits(guardrails, masterplan_id, mock_cost_tracker):
    """Test get limit status with custom limits"""
    guardrails.set_masterplan_limits(
        masterplan_id=masterplan_id,
        soft_limit_usd=30.0,
        hard_limit_usd=50.0
    )

    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=20.0,
        total_input_tokens=40000,
        total_output_tokens=20000,
        call_count=4
    )

    status = guardrails.get_limit_status(masterplan_id)

    assert status['soft_limit'] == 30.0
    assert status['hard_limit'] == 50.0
    assert status['usage_percentage'] == 40.0
    assert status['remaining_budget'] == 30.0


def test_get_limit_status_over_budget(guardrails, masterplan_id, mock_cost_tracker):
    """Test get limit status when over budget"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=110.0,
        total_input_tokens=220000,
        total_output_tokens=110000,
        call_count=20
    )

    status = guardrails.get_limit_status(masterplan_id)

    assert abs(status['usage_percentage'] - 110.0) < 0.001  # Floating point tolerance
    assert status['remaining_budget'] == 0.0  # max(0, -10) = 0


# ============================================================================
# Reset Violations Tests
# ============================================================================

def test_reset_violations_specific_masterplan(guardrails, masterplan_id, mock_cost_tracker):
    """Test resetting violations for specific masterplan"""
    # Trigger soft limit violation
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=60.0,
        total_input_tokens=120000,
        total_output_tokens=60000,
        call_count=10
    )

    guardrails.check_limits(masterplan_id)
    assert masterplan_id in guardrails._soft_limit_violations

    # Reset
    guardrails.reset_violations(masterplan_id)
    assert masterplan_id not in guardrails._soft_limit_violations


def test_reset_violations_all_masterplans(guardrails, mock_cost_tracker):
    """Test resetting all violations"""
    mp1 = uuid4()
    mp2 = uuid4()

    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=60.0,
        total_input_tokens=120000,
        total_output_tokens=60000,
        call_count=10
    )

    # Trigger violations for both
    guardrails.check_limits(mp1)
    guardrails.check_limits(mp2)

    assert len(guardrails._soft_limit_violations) == 2

    # Reset all
    guardrails.reset_violations()
    assert len(guardrails._soft_limit_violations) == 0


# ============================================================================
# Edge Cases
# ============================================================================

def test_zero_cost_calculation(guardrails, masterplan_id, mock_cost_tracker):
    """Test with zero cost"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=0.0,
        total_input_tokens=0,
        total_output_tokens=0,
        call_count=0
    )

    result = guardrails.check_limits(masterplan_id)

    assert result['current_cost'] == 0.0
    assert result['usage_percentage'] == 0.0
    assert result['within_limits'] is True


def test_exactly_at_soft_limit(guardrails, masterplan_id, mock_cost_tracker):
    """Test when cost is exactly at soft limit"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=50.0,  # Exactly at soft limit
        total_input_tokens=100000,
        total_output_tokens=50000,
        call_count=10
    )

    result = guardrails.check_limits(masterplan_id)

    assert result['soft_limit_exceeded'] is True
    assert result['hard_limit_exceeded'] is False


def test_exactly_at_hard_limit(guardrails, masterplan_id, mock_cost_tracker):
    """Test when cost is exactly at hard limit"""
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=100.0,  # Exactly at hard limit
        total_input_tokens=200000,
        total_output_tokens=100000,
        call_count=20
    )

    with pytest.raises(CostLimitExceeded):
        guardrails.check_limits(masterplan_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
