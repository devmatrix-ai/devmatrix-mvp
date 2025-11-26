"""
CostTracker - Real-time LLM cost tracking

Tracks token usage and costs for Claude API calls with per-masterplan and
per-wave granularity.
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage for a single LLM call"""
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostBreakdown:
    """Cost breakdown for a scope (masterplan, wave, atom)"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0
    model_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)


class CostTracker:
    """
    Track LLM costs in real-time

    Features:
    - Per-masterplan cost tracking
    - Per-wave cost tracking
    - Per-atom cost tracking
    - Model-specific pricing
    - Real-time cost calculation
    """

    # Claude 3.5 Sonnet pricing (per 1M tokens)
    MODEL_PRICING = {
        'claude-haiku-4-5-20251001': {
            'input': 3.00,   # $3 per 1M input tokens
            'output': 15.00  # $15 per 1M output tokens
        },
        'claude-haiku-4-5-20251001': {
            'input': 0.80,   # $0.80 per 1M input tokens
            'output': 4.00   # $4 per 1M output tokens
        },
        'claude-3-opus-20240229': {
            'input': 15.00,  # $15 per 1M input tokens
            'output': 75.00  # $75 per 1M output tokens
        }
    }

    def __init__(self, db_session: AsyncSession):
        """
        Initialize CostTracker

        Args:
            db_session: Database session for cost persistence
        """
        self.db = db_session

        # In-memory cost tracking (flushed to DB periodically)
        self._masterplan_costs: Dict[UUID, CostBreakdown] = {}
        self._wave_costs: Dict[UUID, CostBreakdown] = {}
        self._atom_costs: Dict[UUID, CostBreakdown] = {}

    def track_usage(
        self,
        masterplan_id: UUID,
        input_tokens: int,
        output_tokens: int,
        model: str,
        wave_id: Optional[UUID] = None,
        atom_id: Optional[UUID] = None
    ):
        """
        Track token usage for a single LLM call

        Args:
            masterplan_id: Masterplan UUID
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            model: Model name (e.g., 'claude-haiku-4-5-20251001')
            wave_id: Optional wave UUID
            atom_id: Optional atom UUID
        """
        cost_usd = self._calculate_cost(input_tokens, output_tokens, model)

        # Track at masterplan level
        if masterplan_id not in self._masterplan_costs:
            self._masterplan_costs[masterplan_id] = CostBreakdown()

        breakdown = self._masterplan_costs[masterplan_id]
        breakdown.total_input_tokens += input_tokens
        breakdown.total_output_tokens += output_tokens
        breakdown.total_cost_usd += cost_usd
        breakdown.call_count += 1

        # Track model breakdown
        if model not in breakdown.model_breakdown:
            breakdown.model_breakdown[model] = {'input': 0, 'output': 0, 'cost': 0.0}

        breakdown.model_breakdown[model]['input'] += input_tokens
        breakdown.model_breakdown[model]['output'] += output_tokens
        breakdown.model_breakdown[model]['cost'] += cost_usd

        # Track at wave level
        if wave_id:
            if wave_id not in self._wave_costs:
                self._wave_costs[wave_id] = CostBreakdown()

            wave_breakdown = self._wave_costs[wave_id]
            wave_breakdown.total_input_tokens += input_tokens
            wave_breakdown.total_output_tokens += output_tokens
            wave_breakdown.total_cost_usd += cost_usd
            wave_breakdown.call_count += 1

        # Track at atom level
        if atom_id:
            if atom_id not in self._atom_costs:
                self._atom_costs[atom_id] = CostBreakdown()

            atom_breakdown = self._atom_costs[atom_id]
            atom_breakdown.total_input_tokens += input_tokens
            atom_breakdown.total_output_tokens += output_tokens
            atom_breakdown.total_cost_usd += cost_usd
            atom_breakdown.call_count += 1

        logger.debug(
            f"Tracked usage: {input_tokens} input, {output_tokens} output, ${cost_usd:.4f}",
            extra={
                "masterplan_id": str(masterplan_id),
                "wave_id": str(wave_id) if wave_id else None,
                "atom_id": str(atom_id) if atom_id else None,
                "model": model,
                "cost_usd": cost_usd
            }
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculate cost in USD for token usage

        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            model: Model name

        Returns:
            Cost in USD
        """
        if model not in self.MODEL_PRICING:
            logger.warning(f"Unknown model {model}, using default pricing")
            model = 'claude-haiku-4-5-20251001'

        pricing = self.MODEL_PRICING[model]

        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        return input_cost + output_cost

    def get_masterplan_cost(self, masterplan_id: UUID) -> CostBreakdown:
        """
        Get cost breakdown for a masterplan

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            CostBreakdown with totals
        """
        return self._masterplan_costs.get(masterplan_id, CostBreakdown())

    def get_wave_cost(self, wave_id: UUID) -> CostBreakdown:
        """
        Get cost breakdown for a wave

        Args:
            wave_id: Wave UUID

        Returns:
            CostBreakdown with totals
        """
        return self._wave_costs.get(wave_id, CostBreakdown())

    def get_atom_cost(self, atom_id: UUID) -> CostBreakdown:
        """
        Get cost breakdown for an atom

        Args:
            atom_id: Atom UUID

        Returns:
            CostBreakdown with totals
        """
        return self._atom_costs.get(atom_id, CostBreakdown())

    def get_total_costs(self) -> Dict[str, float]:
        """
        Get total costs across all masterplans

        Returns:
            Dict with total costs: {'total_usd': float, 'masterplan_count': int}
        """
        total_usd = sum(
            breakdown.total_cost_usd
            for breakdown in self._masterplan_costs.values()
        )

        return {
            'total_usd': total_usd,
            'masterplan_count': len(self._masterplan_costs)
        }

    async def flush_to_db(self):
        """
        Flush in-memory costs to database

        This should be called periodically to persist cost data.
        """
        # TODO: Implement database persistence
        # For now, costs are kept in memory only
        logger.info(
            f"Flushing costs to DB: {len(self._masterplan_costs)} masterplans tracked"
        )

    def reset_tracking(self, masterplan_id: Optional[UUID] = None):
        """
        Reset cost tracking

        Args:
            masterplan_id: Optional masterplan to reset (resets all if None)
        """
        if masterplan_id:
            self._masterplan_costs.pop(masterplan_id, None)
            # Clear associated waves and atoms
            # (requires tracking which waves/atoms belong to masterplan)
            logger.info(f"Reset cost tracking for masterplan {masterplan_id}")
        else:
            self._masterplan_costs.clear()
            self._wave_costs.clear()
            self._atom_costs.clear()
            logger.info("Reset all cost tracking")
