"""
Trace Manager

Manages storage and retrieval of atom traces for E2E traceability.
Stores traces in database for querying and analysis.
"""

from typing import Dict, List, Optional
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .atom_trace import AtomTrace

logger = logging.getLogger(__name__)


class TraceManager:
    """
    Manages atom traces across the pipeline.

    Features:
    - In-memory trace storage during execution
    - Database persistence after completion
    - Trace retrieval by atom_id, masterplan_id
    - Aggregate statistics by masterplan
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize trace manager.

        Args:
            db_session: Optional database session for persistence
        """
        self.db = db_session
        self._traces: Dict[UUID, AtomTrace] = {}  # atom_id -> AtomTrace

    def create_trace(
        self,
        atom_id: UUID,
        masterplan_id: UUID,
        atom_number: int,
        description: str
    ) -> AtomTrace:
        """
        Create new atom trace.

        Args:
            atom_id: Atom UUID
            masterplan_id: MasterPlan UUID
            atom_number: Atom number
            description: Atom description

        Returns:
            AtomTrace instance
        """
        trace = AtomTrace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            atom_number=atom_number,
            description=description
        )

        self._traces[atom_id] = trace
        logger.debug(f"Trace created for atom {atom_id}")

        return trace

    def get_trace(self, atom_id: UUID) -> Optional[AtomTrace]:
        """
        Get atom trace by ID.

        Args:
            atom_id: Atom UUID

        Returns:
            AtomTrace if found, None otherwise
        """
        return self._traces.get(atom_id)

    def get_masterplan_traces(self, masterplan_id: UUID) -> List[AtomTrace]:
        """
        Get all traces for a masterplan.

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            List of AtomTrace instances
        """
        return [
            trace for trace in self._traces.values()
            if trace.masterplan_id == masterplan_id
        ]

    def get_aggregate_stats(self, masterplan_id: UUID) -> Dict:
        """
        Get aggregate statistics for masterplan.

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            Dictionary with aggregate stats
        """
        traces = self.get_masterplan_traces(masterplan_id)

        if not traces:
            return {
                "total_atoms": 0,
                "completed": 0,
                "failed": 0,
                "total_cost_usd": 0.0,
                "total_time_seconds": 0.0,
                "avg_cost_per_atom": 0.0,
                "avg_time_per_atom": 0.0
            }

        total_cost = sum(t.cost.total_cost_usd for t in traces)
        total_time = sum(t.timing.total_seconds for t in traces)
        completed = sum(1 for t in traces if t.status == "completed")
        failed = sum(1 for t in traces if t.status == "failed")

        return {
            "total_atoms": len(traces),
            "completed": completed,
            "failed": failed,
            "total_cost_usd": total_cost,
            "total_time_seconds": total_time,
            "avg_cost_per_atom": total_cost / len(traces) if traces else 0.0,
            "avg_time_per_atom": total_time / len(traces) if traces else 0.0,
            "total_llm_tokens": sum(
                t.cost.llm_tokens_input + t.cost.llm_tokens_output
                for t in traces
            ),
            "total_retries": sum(t.retry.total_attempts for t in traces),
            "cache_hit_rate": (
                sum(t.cost.cache_hits for t in traces) /
                (sum(t.cost.cache_hits + t.cost.cache_misses for t in traces))
                if any(t.cost.cache_hits + t.cost.cache_misses for t in traces) else 0.0
            )
        }

    def persist_trace(self, atom_id: UUID):
        """
        Persist trace to database.

        Args:
            atom_id: Atom UUID to persist
        """
        trace = self.get_trace(atom_id)

        if not trace:
            logger.warning(f"No trace found for atom {atom_id}")
            return

        if not self.db:
            logger.warning("No database session available for persistence")
            return

        # Store trace data in atom metadata or separate trace table
        # For now, we'll use the atom's metadata JSON field
        try:
            from src.models import AtomicUnit

            atom = self.db.query(AtomicUnit).filter(
                AtomicUnit.atom_id == atom_id
            ).first()

            if atom:
                # Store trace in metadata
                if not atom.metadata:
                    atom.metadata = {}

                atom.metadata["trace"] = trace.to_dict()
                self.db.commit()

                logger.info(f"Trace persisted for atom {atom_id}")
            else:
                logger.warning(f"Atom {atom_id} not found in database")

        except Exception as e:
            logger.error(f"Error persisting trace for atom {atom_id}: {e}")
            self.db.rollback()

    def persist_all(self, masterplan_id: UUID):
        """
        Persist all traces for a masterplan.

        Args:
            masterplan_id: MasterPlan UUID
        """
        traces = self.get_masterplan_traces(masterplan_id)

        for trace in traces:
            self.persist_trace(trace.atom_id)

        logger.info(f"Persisted {len(traces)} traces for masterplan {masterplan_id}")

    def clear_traces(self, masterplan_id: Optional[UUID] = None):
        """
        Clear traces from memory.

        Args:
            masterplan_id: If provided, only clear traces for this masterplan
        """
        if masterplan_id:
            self._traces = {
                atom_id: trace
                for atom_id, trace in self._traces.items()
                if trace.masterplan_id != masterplan_id
            }
            logger.debug(f"Cleared traces for masterplan {masterplan_id}")
        else:
            self._traces.clear()
            logger.debug("Cleared all traces")

    def export_traces(self, masterplan_id: UUID, format: str = "json") -> str:
        """
        Export traces to string format.

        Args:
            masterplan_id: MasterPlan UUID
            format: Export format ('json' or 'csv')

        Returns:
            Exported traces as string
        """
        traces = self.get_masterplan_traces(masterplan_id)

        if format == "json":
            import json
            return json.dumps(
                [trace.to_dict() for trace in traces],
                indent=2
            )
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if not traces:
                return ""

            # CSV headers
            fieldnames = [
                "atom_id",
                "atom_number",
                "status",
                "total_time",
                "cost_usd",
                "validation_passed",
                "acceptance_pass_rate",
                "retry_attempts"
            ]

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for trace in traces:
                writer.writerow({
                    "atom_id": str(trace.atom_id),
                    "atom_number": trace.atom_number,
                    "status": trace.status,
                    "total_time": trace.timing.total_seconds,
                    "cost_usd": trace.cost.total_cost_usd,
                    "validation_passed": all([
                        trace.validation.l1_syntax,
                        trace.validation.l2_imports,
                        trace.validation.l3_types,
                        trace.validation.l4_complexity
                    ]),
                    "acceptance_pass_rate": (
                        trace.acceptance.tests_passed / trace.acceptance.tests_executed
                        if trace.acceptance.tests_executed > 0 else 0.0
                    ),
                    "retry_attempts": trace.retry.total_attempts
                })

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
