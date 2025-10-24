"""
ExecutionServiceV2 - MGE V2 Execution Orchestration

Orchestrates wave-based parallel execution with retry logic for masterplan atoms.
Coordinates WaveExecutor and RetryOrchestrator for complete execution pipeline.

Author: DevMatrix Team
Date: 2025-10-24
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from sqlalchemy.orm import Session

from ..models import MasterPlan, AtomicUnit, DependencyGraph
from ..execution.wave_executor import WaveExecutor, WaveExecutionResult, AtomStatus
from ..execution.retry_orchestrator import RetryOrchestrator
from ..observability import StructuredLogger


logger = StructuredLogger("execution_service_v2", output_json=True)


class ExecutionServiceV2:
    """
    Orchestrates MGE V2 execution pipeline.

    Coordinates:
    - Wave-based parallel execution (WaveExecutor)
    - Smart retry logic (RetryOrchestrator)
    - Progress tracking
    - Status persistence
    - Retry history management
    """

    def __init__(
        self,
        db: Session,
        code_generator: Optional[Callable] = None,
        max_concurrent: int = 100,
        max_retries: int = 3,
        enable_backoff: bool = True
    ):
        """
        Initialize ExecutionServiceV2

        Args:
            db: Database session
            code_generator: Optional code generation function
            max_concurrent: Max concurrent atom executions (default: 100)
            max_retries: Max retry attempts per atom (default: 3)
            enable_backoff: Enable exponential backoff (default: True)
        """
        self.db = db
        self.code_generator = code_generator

        # Initialize executors
        self.wave_executor = WaveExecutor(
            db=db,
            code_generator=code_generator,
            max_concurrent=max_concurrent
        )

        self.retry_orchestrator = RetryOrchestrator(
            db=db,
            max_attempts=max_retries,
            enable_backoff=enable_backoff
        )

        logger.info(
            "ExecutionServiceV2 initialized",
            extra={
                "max_concurrent": max_concurrent,
                "max_retries": max_retries,
                "enable_backoff": enable_backoff
            }
        )

    async def start_execution(
        self,
        masterplan_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Start masterplan execution

        Args:
            masterplan_id: MasterPlan ID to execute

        Returns:
            Execution summary with statistics
        """
        logger.info(
            f"Starting execution for masterplan {masterplan_id}",
            extra={"masterplan_id": str(masterplan_id)}
        )

        # Load masterplan
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            raise ValueError(f"MasterPlan {masterplan_id} not found")

        # Update masterplan status
        masterplan.status = "executing"
        self.db.commit()

        # Organize atoms into waves
        waves = self.wave_executor.coordinate_dependencies(masterplan_id)

        if not waves:
            logger.warning(
                f"No waves found for masterplan {masterplan_id}",
                extra={"masterplan_id": str(masterplan_id)}
            )
            masterplan.status = "completed"
            self.db.commit()
            return {
                "masterplan_id": str(masterplan_id),
                "status": "completed",
                "total_waves": 0,
                "total_atoms": 0,
                "message": "No atoms to execute"
            }

        # Execute waves sequentially
        wave_results = await self.execute_waves(waves, masterplan_id)

        # Manage retries for failed atoms
        all_failed_atoms = []
        for wave_result in wave_results:
            failed_results = [
                r for r in wave_result.atom_results
                if r.status == AtomStatus.FAILED
            ]
            all_failed_atoms.extend(failed_results)

        retry_results = await self.manage_retries(all_failed_atoms, masterplan_id)

        # Calculate final statistics
        total_atoms = sum(wr.total_atoms for wr in wave_results)
        successful_atoms = sum(wr.successful for wr in wave_results)
        failed_atoms = len(all_failed_atoms) - len(
            [r for r in retry_results if r['success']]
        )

        # Update masterplan status
        if failed_atoms == 0:
            masterplan.status = "completed"
        elif failed_atoms < total_atoms:
            masterplan.status = "partially_completed"
        else:
            masterplan.status = "failed"

        masterplan.completed_at = datetime.utcnow()
        self.db.commit()

        # Get retry statistics
        retry_stats = self.retry_orchestrator.get_retry_statistics()

        execution_summary = {
            "masterplan_id": str(masterplan_id),
            "status": masterplan.status,
            "total_waves": len(waves),
            "total_atoms": total_atoms,
            "successful_atoms": successful_atoms,
            "failed_atoms": failed_atoms,
            "success_rate": (successful_atoms / total_atoms * 100) if total_atoms > 0 else 0.0,
            "retry_stats": retry_stats,
            "wave_results": [
                {
                    "wave_number": wr.wave_number,
                    "total": wr.total_atoms,
                    "successful": wr.successful,
                    "failed": wr.failed,
                    "execution_time": wr.execution_time_seconds
                }
                for wr in wave_results
            ]
        }

        logger.info(
            f"Execution completed for masterplan {masterplan_id}",
            extra={
                "masterplan_id": str(masterplan_id),
                "status": masterplan.status,
                "total_atoms": total_atoms,
                "successful_atoms": successful_atoms,
                "failed_atoms": failed_atoms
            }
        )

        return execution_summary

    async def execute_waves(
        self,
        waves: List[List[AtomicUnit]],
        masterplan_id: uuid.UUID
    ) -> List[WaveExecutionResult]:
        """
        Execute waves sequentially

        Args:
            waves: List of waves (each wave is a list of atoms)
            masterplan_id: MasterPlan ID for context

        Returns:
            List of WaveExecutionResult for each wave
        """
        logger.info(
            f"Executing {len(waves)} waves for masterplan {masterplan_id}",
            extra={
                "masterplan_id": str(masterplan_id),
                "wave_count": len(waves)
            }
        )

        wave_results = []

        for wave_number, wave_atoms in enumerate(waves):
            logger.info(
                f"Executing wave {wave_number} with {len(wave_atoms)} atoms",
                extra={
                    "wave_number": wave_number,
                    "atom_count": len(wave_atoms)
                }
            )

            result = await self.wave_executor.execute_wave(
                wave_number=wave_number,
                wave_atoms=wave_atoms,
                masterplan_id=masterplan_id
            )

            wave_results.append(result)

            logger.info(
                f"Wave {wave_number} completed: {result.successful}/{result.total_atoms} successful",
                extra={
                    "wave_number": wave_number,
                    "successful": result.successful,
                    "failed": result.failed,
                    "total": result.total_atoms
                }
            )

        return wave_results

    async def manage_retries(
        self,
        failed_atom_results: List[Any],
        masterplan_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Manage retry attempts for failed atoms

        Args:
            failed_atom_results: List of failed AtomExecutionResult
            masterplan_id: MasterPlan ID for context

        Returns:
            List of retry results
        """
        if not failed_atom_results:
            return []

        logger.info(
            f"Managing retries for {len(failed_atom_results)} failed atoms",
            extra={
                "masterplan_id": str(masterplan_id),
                "failed_count": len(failed_atom_results)
            }
        )

        retry_results = []

        for failed_result in failed_atom_results:
            # Load atom
            atom = self.db.query(AtomicUnit).filter(
                AtomicUnit.atom_id == failed_result.atom_id
            ).first()

            if not atom:
                logger.warning(
                    f"Atom {failed_result.atom_id} not found for retry",
                    extra={"atom_id": str(failed_result.atom_id)}
                )
                continue

            # Attempt retries
            success = False
            final_code = None
            final_feedback = None

            for attempt in range(1, self.retry_orchestrator.max_attempts + 1):
                logger.info(
                    f"Retry attempt {attempt} for atom {atom.atom_id}",
                    extra={
                        "atom_id": str(atom.atom_id),
                        "attempt": attempt
                    }
                )

                success, code, feedback = await self.retry_orchestrator.retry_atom(
                    atom=atom,
                    error=failed_result.error_message or "Unknown error",
                    attempt=attempt,
                    code_generator=self.code_generator
                )

                if success:
                    final_code = code
                    final_feedback = feedback
                    logger.info(
                        f"Atom {atom.atom_id} retry succeeded on attempt {attempt}",
                        extra={
                            "atom_id": str(atom.atom_id),
                            "attempt": attempt
                        }
                    )
                    break

                final_feedback = feedback

            # Record retry result
            retry_result = {
                "atom_id": str(atom.atom_id),
                "success": success,
                "total_attempts": attempt,
                "final_code": final_code,
                "final_feedback": final_feedback
            }

            retry_results.append(retry_result)

            # Persist retry history
            self.persist_retry_history(atom)

        logger.info(
            f"Retry management completed: {sum(1 for r in retry_results if r['success'])}/{len(retry_results)} succeeded",
            extra={
                "masterplan_id": str(masterplan_id),
                "total_retries": len(retry_results),
                "successful_retries": sum(1 for r in retry_results if r['success'])
            }
        )

        return retry_results

    def track_progress(self, masterplan_id: uuid.UUID) -> Dict[str, Any]:
        """
        Track execution progress for masterplan

        Args:
            masterplan_id: MasterPlan ID

        Returns:
            Progress statistics
        """
        # Get masterplan
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            raise ValueError(f"MasterPlan {masterplan_id} not found")

        # Get all atoms
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        total_atoms = len(atoms)
        completed_atoms = sum(1 for a in atoms if a.status == "completed")
        failed_atoms = sum(1 for a in atoms if a.status == "failed")
        pending_atoms = sum(1 for a in atoms if a.status == "pending")

        # Get wave executor progress
        wave_progress = self.wave_executor.track_progress()

        # Get retry statistics
        retry_stats = self.retry_orchestrator.get_retry_statistics()

        progress = {
            "masterplan_id": str(masterplan_id),
            "masterplan_status": masterplan.status,
            "total_atoms": total_atoms,
            "completed_atoms": completed_atoms,
            "failed_atoms": failed_atoms,
            "pending_atoms": pending_atoms,
            "progress_percentage": (completed_atoms / total_atoms * 100) if total_atoms > 0 else 0.0,
            "wave_executor_progress": wave_progress,
            "retry_stats": retry_stats
        }

        return progress

    def get_execution_status(self, masterplan_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get detailed execution status

        Args:
            masterplan_id: MasterPlan ID

        Returns:
            Execution status with details
        """
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            raise ValueError(f"MasterPlan {masterplan_id} not found")

        # Get atoms grouped by status
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        atoms_by_status = {
            "completed": [str(a.atom_id) for a in atoms if a.status == "completed"],
            "failed": [str(a.atom_id) for a in atoms if a.status == "failed"],
            "pending": [str(a.atom_id) for a in atoms if a.status == "pending"]
        }

        # Get failed atom errors
        failed_atoms_detail = []
        for atom in atoms:
            if atom.status == "failed" and atom.error_message:
                failed_atoms_detail.append({
                    "atom_id": str(atom.atom_id),
                    "atom_number": atom.atom_number,
                    "description": atom.description,
                    "error": atom.error_message,
                    "file_path": atom.file_path
                })

        status = {
            "masterplan_id": str(masterplan_id),
            "status": masterplan.status,
            "created_at": masterplan.created_at.isoformat() if masterplan.created_at else None,
            "completed_at": masterplan.completed_at.isoformat() if masterplan.completed_at else None,
            "total_atoms": len(atoms),
            "atoms_by_status": atoms_by_status,
            "failed_atoms_detail": failed_atoms_detail,
            "retry_stats": self.retry_orchestrator.get_retry_statistics()
        }

        return status

    def persist_retry_history(self, atom: AtomicUnit):
        """
        Persist retry history to database

        Args:
            atom: Atom with retry history
        """
        history = self.retry_orchestrator.track_retry_history(atom.atom_id)

        if not history:
            return

        # Store retry information in atom metadata (if available)
        # In a real implementation, this could write to a separate retry_history table
        retry_summary = {
            "total_attempts": history.total_attempts,
            "final_success": history.final_success,
            "attempts": [
                {
                    "attempt_number": att.attempt_number,
                    "temperature": att.temperature,
                    "error_category": att.error_category.value,
                    "success": att.success,
                    "timestamp": att.timestamp.isoformat()
                }
                for att in history.attempts
            ]
        }

        logger.debug(
            f"Retry history for atom {atom.atom_id}",
            extra={
                "atom_id": str(atom.atom_id),
                "retry_summary": retry_summary
            }
        )

        # In production, persist to database table
        # For now, just log

    def reset_execution_state(self):
        """Reset execution state for new masterplan"""
        self.wave_executor.reset_state()
        self.retry_orchestrator.reset_history()
        logger.info("Execution state reset")
