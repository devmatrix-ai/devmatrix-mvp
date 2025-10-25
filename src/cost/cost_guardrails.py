"""
CostGuardrails - Enforce cost limits and alerts

Prevents budget overruns with soft/hard limits and Grafana alerting integration.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass

from .cost_tracker import CostTracker, CostBreakdown

logger = logging.getLogger(__name__)


class CostLimitExceeded(Exception):
    """Raised when hard cost limit is exceeded"""
    def __init__(self, message: str, current_cost: float, limit: float):
        super().__init__(message)
        self.current_cost = current_cost
        self.limit = limit


@dataclass
class CostLimits:
    """Cost limit configuration"""
    soft_limit_usd: float  # Warning threshold (e.g., 80% of budget)
    hard_limit_usd: float  # Hard stop threshold (e.g., 100% of budget)
    per_atom_limit_usd: Optional[float] = None  # Optional per-atom limit


class CostGuardrails:
    """
    Enforce cost limits with soft/hard caps

    Features:
    - Soft limits (warnings, alerts)
    - Hard limits (block execution)
    - Per-masterplan limits
    - Per-atom limits (optional)
    - Grafana alert integration
    """

    DEFAULT_SOFT_LIMIT_USD = 50.0  # $50 warning
    DEFAULT_HARD_LIMIT_USD = 100.0  # $100 hard stop

    def __init__(
        self,
        cost_tracker: CostTracker,
        default_soft_limit: float = DEFAULT_SOFT_LIMIT_USD,
        default_hard_limit: float = DEFAULT_HARD_LIMIT_USD
    ):
        """
        Initialize CostGuardrails

        Args:
            cost_tracker: CostTracker instance for cost data
            default_soft_limit: Default soft limit in USD
            default_hard_limit: Default hard limit in USD
        """
        self.cost_tracker = cost_tracker
        self.default_soft_limit = default_soft_limit
        self.default_hard_limit = default_hard_limit

        # Per-masterplan custom limits
        self._masterplan_limits: Dict[UUID, CostLimits] = {}

        # Track soft limit violations (for alerting)
        self._soft_limit_violations: Dict[UUID, bool] = {}

    def set_masterplan_limits(
        self,
        masterplan_id: UUID,
        soft_limit_usd: float,
        hard_limit_usd: float,
        per_atom_limit_usd: Optional[float] = None
    ):
        """
        Set custom cost limits for a masterplan

        Args:
            masterplan_id: Masterplan UUID
            soft_limit_usd: Soft limit (warning) in USD
            hard_limit_usd: Hard limit (stop) in USD
            per_atom_limit_usd: Optional per-atom limit in USD
        """
        if soft_limit_usd >= hard_limit_usd:
            raise ValueError("Soft limit must be less than hard limit")

        self._masterplan_limits[masterplan_id] = CostLimits(
            soft_limit_usd=soft_limit_usd,
            hard_limit_usd=hard_limit_usd,
            per_atom_limit_usd=per_atom_limit_usd
        )

        logger.info(
            f"Set cost limits for masterplan {masterplan_id}: "
            f"soft=${soft_limit_usd}, hard=${hard_limit_usd}"
        )

    def check_limits(
        self,
        masterplan_id: UUID,
        atom_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Check if current costs exceed limits

        Args:
            masterplan_id: Masterplan UUID
            atom_id: Optional atom UUID for per-atom check

        Returns:
            Dict with limit check results: {
                'within_limits': bool,
                'soft_limit_exceeded': bool,
                'hard_limit_exceeded': bool,
                'current_cost': float,
                'soft_limit': float,
                'hard_limit': float,
                'usage_percentage': float
            }

        Raises:
            CostLimitExceeded: If hard limit is exceeded
        """
        # Get current cost
        cost_breakdown = self.cost_tracker.get_masterplan_cost(masterplan_id)
        current_cost = cost_breakdown.total_cost_usd

        # Get limits
        limits = self._masterplan_limits.get(masterplan_id)
        if limits:
            soft_limit = limits.soft_limit_usd
            hard_limit = limits.hard_limit_usd
        else:
            soft_limit = self.default_soft_limit
            hard_limit = self.default_hard_limit

        # Check hard limit
        if current_cost >= hard_limit:
            logger.error(
                f"HARD LIMIT EXCEEDED for masterplan {masterplan_id}: "
                f"${current_cost:.2f} >= ${hard_limit:.2f}"
            )

            # Trigger Grafana alert (if configured)
            self._trigger_alert(
                masterplan_id=masterplan_id,
                alert_type='hard_limit_exceeded',
                current_cost=current_cost,
                limit=hard_limit
            )

            raise CostLimitExceeded(
                f"Hard cost limit exceeded: ${current_cost:.2f} >= ${hard_limit:.2f}",
                current_cost=current_cost,
                limit=hard_limit
            )

        # Check soft limit
        soft_limit_exceeded = current_cost >= soft_limit

        if soft_limit_exceeded and not self._soft_limit_violations.get(masterplan_id, False):
            logger.warning(
                f"SOFT LIMIT EXCEEDED for masterplan {masterplan_id}: "
                f"${current_cost:.2f} >= ${soft_limit:.2f}"
            )

            # Trigger Grafana alert
            self._trigger_alert(
                masterplan_id=masterplan_id,
                alert_type='soft_limit_exceeded',
                current_cost=current_cost,
                limit=soft_limit
            )

            # Mark as violated (avoid repeated alerts)
            self._soft_limit_violations[masterplan_id] = True

        # Check per-atom limit if specified
        if atom_id and limits and limits.per_atom_limit_usd:
            atom_cost = self.cost_tracker.get_atom_cost(atom_id).total_cost_usd

            if atom_cost >= limits.per_atom_limit_usd:
                logger.warning(
                    f"Per-atom limit exceeded for atom {atom_id}: "
                    f"${atom_cost:.2f} >= ${limits.per_atom_limit_usd:.2f}"
                )

        usage_percentage = (current_cost / hard_limit) * 100 if hard_limit > 0 else 0

        return {
            'within_limits': current_cost < hard_limit,
            'soft_limit_exceeded': soft_limit_exceeded,
            'hard_limit_exceeded': current_cost >= hard_limit,
            'current_cost': current_cost,
            'soft_limit': soft_limit,
            'hard_limit': hard_limit,
            'usage_percentage': usage_percentage
        }

    def check_before_execution(
        self,
        masterplan_id: UUID,
        estimated_tokens: int = 10000,
        model: str = 'claude-3-5-sonnet-20241022'
    ):
        """
        Check limits before executing an operation

        Args:
            masterplan_id: Masterplan UUID
            estimated_tokens: Estimated token usage (default: 10K)
            model: Model to use for cost estimation

        Raises:
            CostLimitExceeded: If executing would exceed hard limit
        """
        # Get current cost
        current_cost = self.cost_tracker.get_masterplan_cost(masterplan_id).total_cost_usd

        # Estimate cost of operation
        estimated_cost = self.cost_tracker._calculate_cost(
            estimated_tokens // 2,  # Assume 50% input
            estimated_tokens // 2,  # Assume 50% output
            model
        )

        projected_cost = current_cost + estimated_cost

        # Get hard limit
        limits = self._masterplan_limits.get(masterplan_id)
        hard_limit = limits.hard_limit_usd if limits else self.default_hard_limit

        if projected_cost >= hard_limit:
            raise CostLimitExceeded(
                f"Projected cost ${projected_cost:.2f} would exceed hard limit ${hard_limit:.2f}",
                current_cost=projected_cost,
                limit=hard_limit
            )

    def _trigger_alert(
        self,
        masterplan_id: UUID,
        alert_type: str,
        current_cost: float,
        limit: float
    ):
        """
        Trigger Grafana alert

        Args:
            masterplan_id: Masterplan UUID
            alert_type: Alert type ('soft_limit_exceeded' or 'hard_limit_exceeded')
            current_cost: Current cost in USD
            limit: Limit that was exceeded
        """
        # TODO: Implement Grafana alerting integration
        # For now, just log the alert
        logger.warning(
            f"ALERT [{alert_type}]: Masterplan {masterplan_id} - "
            f"${current_cost:.2f} >= ${limit:.2f}",
            extra={
                "masterplan_id": str(masterplan_id),
                "alert_type": alert_type,
                "current_cost": current_cost,
                "limit": limit,
                "severity": "critical" if alert_type == 'hard_limit_exceeded' else "warning"
            }
        )

    def get_limit_status(self, masterplan_id: UUID) -> Dict[str, Any]:
        """
        Get current limit status for a masterplan

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            Dict with status: {
                'current_cost': float,
                'soft_limit': float,
                'hard_limit': float,
                'usage_percentage': float,
                'remaining_budget': float,
                'calls_made': int
            }
        """
        cost_breakdown = self.cost_tracker.get_masterplan_cost(masterplan_id)

        limits = self._masterplan_limits.get(masterplan_id)
        soft_limit = limits.soft_limit_usd if limits else self.default_soft_limit
        hard_limit = limits.hard_limit_usd if limits else self.default_hard_limit

        usage_percentage = (cost_breakdown.total_cost_usd / hard_limit) * 100 if hard_limit > 0 else 0
        remaining_budget = hard_limit - cost_breakdown.total_cost_usd

        return {
            'current_cost': cost_breakdown.total_cost_usd,
            'soft_limit': soft_limit,
            'hard_limit': hard_limit,
            'usage_percentage': usage_percentage,
            'remaining_budget': max(0, remaining_budget),
            'calls_made': cost_breakdown.call_count
        }

    def reset_violations(self, masterplan_id: Optional[UUID] = None):
        """
        Reset soft limit violation tracking

        Args:
            masterplan_id: Optional masterplan to reset (resets all if None)
        """
        if masterplan_id:
            self._soft_limit_violations.pop(masterplan_id, None)
        else:
            self._soft_limit_violations.clear()
