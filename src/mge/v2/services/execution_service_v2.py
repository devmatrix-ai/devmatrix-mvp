"""
Execution Service V2 for MGE

State management and orchestration for execution pipeline.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel

from src.mge.v2.execution.wave_executor import WaveExecutor, ExecutionResult
from src.mge.v2.execution.metrics import (
    EXECUTION_PRECISION_PERCENT,
    EXECUTION_TIME_SECONDS,
    EXECUTION_COST_USD_TOTAL,
)

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionState(BaseModel):
    """State of an execution."""
    execution_id: UUID
    masterplan_id: UUID
    status: ExecutionStatus
    current_wave: int
    total_waves: int
    atoms_completed: int
    atoms_total: int
    atoms_succeeded: int
    atoms_failed: int
    total_cost_usd: float
    total_time_seconds: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat() if v else None
        }


class ExecutionServiceV2:
    """
    Service for managing execution state and orchestration.

    Features:
    - Execution state tracking (pending, running, completed, failed)
    - Progress reporting (wave progress, atom completion %)
    - Cost tracking (LLM API costs per atom, per wave, total)
    - Time tracking (execution time per atom, per wave, total)
    - Pause/Resume support
    - Background execution with asyncio tasks
    """

    def __init__(self, wave_executor: WaveExecutor):
        """
        Initialize ExecutionServiceV2.

        Args:
            wave_executor: WaveExecutor for executing waves
        """
        self.wave_executor = wave_executor
        self.executions: Dict[UUID, ExecutionState] = {}
        self.execution_results: Dict[UUID, Dict[UUID, ExecutionResult]] = {}
        self.pause_flags: Dict[UUID, bool] = {}

    async def start_execution(
        self,
        masterplan_id: UUID,
        execution_plan: List,  # List[ExecutionWave]
        atoms: Dict[str, any]  # Dict[atom_id, AtomicUnit]
    ) -> UUID:
        """
        Start execution for a masterplan.

        Args:
            masterplan_id: Masterplan ID
            execution_plan: List of waves to execute
            atoms: All atoms keyed by ID

        Returns:
            Execution ID
        """
        execution_id = uuid4()

        # Calculate total atoms
        total_atoms = sum(
            len(getattr(wave, "atom_ids", [])) for wave in execution_plan
        )

        # Initialize state
        state = ExecutionState(
            execution_id=execution_id,
            masterplan_id=masterplan_id,
            status=ExecutionStatus.RUNNING,
            current_wave=0,
            total_waves=len(execution_plan),
            atoms_total=total_atoms,
            atoms_completed=0,
            atoms_succeeded=0,
            atoms_failed=0,
            total_cost_usd=0.0,
            total_time_seconds=0.0,
            started_at=datetime.utcnow()
        )

        self.executions[execution_id] = state
        self.execution_results[execution_id] = {}
        self.pause_flags[execution_id] = False

        logger.info(
            f"🚀 Starting execution {execution_id} for masterplan {masterplan_id} "
            f"({total_atoms} atoms, {len(execution_plan)} waves)"
        )

        # Execute in background
        asyncio.create_task(
            self._execute_background(execution_id, execution_plan, atoms, masterplan_id)
        )

        return execution_id

    async def _execute_background(
        self,
        execution_id: UUID,
        execution_plan: List,
        atoms: Dict[str, any],
        masterplan_id: UUID
    ):
        """
        Execute plan in background.

        Args:
            execution_id: Execution ID
            execution_plan: List of waves
            atoms: All atoms
            masterplan_id: Masterplan ID
        """
        start_time = time.time()

        try:
            # Execute plan
            results = await self._execute_with_pause_support(
                execution_id, execution_plan, atoms, masterplan_id
            )

            # Store results
            self.execution_results[execution_id] = results

            # Calculate final statistics
            succeeded = sum(1 for r in results.values() if r.success)
            failed = len(results) - succeeded
            precision = (succeeded / len(results) * 100) if results else 0
            total_time = time.time() - start_time

            # Update state
            state = self.executions[execution_id]
            state.atoms_completed = len(results)
            state.atoms_succeeded = succeeded
            state.atoms_failed = failed
            state.total_time_seconds = total_time
            state.completed_at = datetime.utcnow()
            state.status = ExecutionStatus.COMPLETED if succeeded == len(results) else ExecutionStatus.FAILED

            # Emit final metrics
            EXECUTION_PRECISION_PERCENT.labels(
                masterplan_id=str(masterplan_id)
            ).set(precision)

            EXECUTION_TIME_SECONDS.labels(
                masterplan_id=str(masterplan_id)
            ).observe(total_time)

            logger.info(
                f"✅ Execution {execution_id} completed: {succeeded}/{len(results)} succeeded "
                f"({precision:.1f}% precision) in {total_time:.1f}s"
            )

        except Exception as e:
            logger.error(f"❌ Execution {execution_id} failed with exception: {e}")

            # Update state to failed
            state = self.executions[execution_id]
            state.status = ExecutionStatus.FAILED
            state.completed_at = datetime.utcnow()
            state.total_time_seconds = time.time() - start_time

    async def _execute_with_pause_support(
        self,
        execution_id: UUID,
        execution_plan: List,
        atoms: Dict[str, any],
        masterplan_id: UUID
    ) -> Dict[UUID, ExecutionResult]:
        """
        Execute plan with pause support.

        Args:
            execution_id: Execution ID
            execution_plan: List of waves
            atoms: All atoms
            masterplan_id: Masterplan ID

        Returns:
            Dict of execution results
        """
        all_results = {}

        for wave in execution_plan:
            # Check pause flag
            if self.pause_flags.get(execution_id, False):
                logger.info(f"⏸️ Execution {execution_id} paused at wave {wave.level}")
                state = self.executions[execution_id]
                state.status = ExecutionStatus.PAUSED
                break

            # Update current wave
            state = self.executions[execution_id]
            state.current_wave = wave.level

            # Execute wave
            wave_result = await self.wave_executor.execute_wave(
                wave_id=wave.level,
                wave_atoms=[atoms[aid] for aid in wave.atom_ids if aid in atoms],
                all_atoms=atoms,
                masterplan_id=masterplan_id
            )

            # Update results
            all_results.update(wave_result.atom_results)

            # Update state
            state.atoms_completed += wave_result.total_atoms
            state.atoms_succeeded += wave_result.succeeded
            state.atoms_failed += wave_result.failed

            # Track cost (if available from execution results)
            for result in wave_result.atom_results.values():
                # Placeholder - cost tracking would come from LLM client
                # In real implementation, extract from result.validation_result.metrics
                pass

        return all_results

    async def pause_execution(self, execution_id: UUID) -> bool:
        """
        Pause execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if paused, False if not found or not running
        """
        if execution_id not in self.executions:
            return False

        state = self.executions[execution_id]

        if state.status != ExecutionStatus.RUNNING:
            return False

        self.pause_flags[execution_id] = True
        logger.info(f"⏸️ Pausing execution {execution_id}")

        return True

    async def resume_execution(self, execution_id: UUID) -> bool:
        """
        Resume paused execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if resumed, False if not found or not paused
        """
        if execution_id not in self.executions:
            return False

        state = self.executions[execution_id]

        if state.status != ExecutionStatus.PAUSED:
            return False

        self.pause_flags[execution_id] = False
        state.status = ExecutionStatus.RUNNING

        logger.info(f"▶️ Resuming execution {execution_id}")

        # Note: Resume functionality would require storing remaining waves
        # For MVP, this is a placeholder

        return True

    def get_execution_state(self, execution_id: UUID) -> Optional[ExecutionState]:
        """
        Get execution state.

        Args:
            execution_id: Execution ID

        Returns:
            ExecutionState or None if not found
        """
        return self.executions.get(execution_id)

    def get_execution_results(
        self, execution_id: UUID
    ) -> Optional[Dict[UUID, ExecutionResult]]:
        """
        Get execution results.

        Args:
            execution_id: Execution ID

        Returns:
            Dict of execution results or None if not found
        """
        return self.execution_results.get(execution_id)

    def get_wave_status(
        self, execution_id: UUID, wave_id: int
    ) -> Optional[Dict[str, any]]:
        """
        Get wave status.

        Args:
            execution_id: Execution ID
            wave_id: Wave ID

        Returns:
            Wave status dict or None if not found
        """
        if execution_id not in self.execution_results:
            return None

        # Filter results for this wave
        # Note: In real implementation, would track wave-level metadata
        # For MVP, return aggregated stats

        state = self.executions.get(execution_id)
        if not state:
            return None

        return {
            "wave_id": wave_id,
            "execution_id": str(execution_id),
            "status": "completed" if state.current_wave > wave_id else "pending",
            "current": state.current_wave == wave_id
        }

    def get_atom_status(
        self, execution_id: UUID, atom_id: UUID
    ) -> Optional[ExecutionResult]:
        """
        Get atom status.

        Args:
            execution_id: Execution ID
            atom_id: Atom ID

        Returns:
            ExecutionResult or None if not found
        """
        results = self.execution_results.get(execution_id)
        if not results:
            return None

        return results.get(atom_id)

    def get_execution_metrics(self, execution_id: UUID) -> Optional[Dict[str, any]]:
        """
        Get execution metrics.

        Args:
            execution_id: Execution ID

        Returns:
            Metrics dict or None if not found
        """
        state = self.executions.get(execution_id)
        if not state:
            return None

        precision = (
            (state.atoms_succeeded / state.atoms_total * 100)
            if state.atoms_total > 0
            else 0
        )

        return {
            "execution_id": str(execution_id),
            "masterplan_id": str(state.masterplan_id),
            "precision_percent": precision,
            "atoms_total": state.atoms_total,
            "atoms_succeeded": state.atoms_succeeded,
            "atoms_failed": state.atoms_failed,
            "atoms_completed": state.atoms_completed,
            "completion_percent": (
                (state.atoms_completed / state.atoms_total * 100)
                if state.atoms_total > 0
                else 0
            ),
            "current_wave": state.current_wave,
            "total_waves": state.total_waves,
            "total_cost_usd": state.total_cost_usd,
            "total_time_seconds": state.total_time_seconds,
            "status": state.status.value,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        }

    def list_executions(
        self, masterplan_id: Optional[UUID] = None
    ) -> List[ExecutionState]:
        """
        List all executions, optionally filtered by masterplan.

        Args:
            masterplan_id: Optional masterplan ID filter

        Returns:
            List of ExecutionState
        """
        executions = list(self.executions.values())

        if masterplan_id:
            executions = [e for e in executions if e.masterplan_id == masterplan_id]

        return executions
