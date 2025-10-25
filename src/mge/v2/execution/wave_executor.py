"""
Wave Executor for MGE V2

Parallel execution of atoms within waves with dependency resolution.
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from uuid import UUID

from .retry_orchestrator import RetryOrchestrator, RetryResult
from .metrics import (
    WAVE_COMPLETION_PERCENT,
    WAVE_ATOM_THROUGHPUT,
    WAVE_TIME_SECONDS,
    ATOMS_SUCCEEDED_TOTAL,
    ATOMS_FAILED_TOTAL,
    ATOM_EXECUTION_TIME_SECONDS,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of atom execution."""
    atom_id: UUID
    success: bool
    code: Optional[str] = None
    validation_result: Optional[any] = None
    attempts: int = 0
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0


@dataclass
class WaveResult:
    """Result of wave execution."""
    wave_id: int
    total_atoms: int
    succeeded: int
    failed: int
    execution_time_seconds: float
    atom_results: Dict[UUID, ExecutionResult]


class WaveExecutor:
    """
    Executes atoms in parallel within waves with dependency resolution.

    Features:
    - Wave-based execution (sequential waves, parallel atoms within wave)
    - Concurrency control (max 100 atoms per wave by default)
    - Dependency resolution (atoms only execute after dependencies complete)
    - Progress tracking (wave completion, atom status)
    - Error isolation (one atom failure doesn't crash entire wave)
    - Prometheus metrics emission
    """

    def __init__(
        self,
        retry_orchestrator: RetryOrchestrator,
        max_concurrency: int = 100
    ):
        """
        Initialize WaveExecutor.

        Args:
            retry_orchestrator: Orchestrator for retry logic
            max_concurrency: Maximum concurrent atoms per wave (default: 100)
        """
        self.retry_orchestrator = retry_orchestrator
        self.max_concurrency = max_concurrency

    async def execute_wave(
        self,
        wave_id: int,
        wave_atoms: List,  # List[AtomicUnit]
        all_atoms: Dict[str, any],  # Dict[atom_id, AtomicUnit]
        masterplan_id: Optional[UUID] = None
    ) -> WaveResult:
        """
        Execute all atoms in a wave (parallel execution).

        Args:
            wave_id: Wave identifier
            wave_atoms: List of atoms to execute in this wave
            all_atoms: All atoms (for dependency lookup)
            masterplan_id: Optional masterplan ID for metrics

        Returns:
            WaveResult with execution statistics
        """
        logger.info(
            f"🌊 Executing Wave {wave_id} with {len(wave_atoms)} atoms "
            f"(max concurrency: {self.max_concurrency})"
        )

        start_time = time.time()
        results: Dict[UUID, ExecutionResult] = {}

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute_atom(atom):
            """Execute single atom with concurrency control."""
            async with semaphore:
                atom_start_time = time.time()

                try:
                    # Get dependencies (already completed in previous waves)
                    deps = [
                        all_atoms[dep_id]
                        for dep_id in getattr(atom, "depends_on", [])
                        if dep_id in all_atoms
                    ]

                    # Execute with retry
                    retry_result: RetryResult = await self.retry_orchestrator.execute_with_retry(
                        atom_spec=atom,
                        dependencies=deps,
                        masterplan_id=masterplan_id
                    )

                    atom_execution_time = time.time() - atom_start_time

                    # Emit atom execution time metric
                    ATOM_EXECUTION_TIME_SECONDS.observe(atom_execution_time)

                    # Create execution result
                    result = ExecutionResult(
                        atom_id=atom.id,
                        success=retry_result.success,
                        code=retry_result.code,
                        validation_result=retry_result.validation_result,
                        attempts=retry_result.attempts_used,
                        error_message=retry_result.error_message,
                        execution_time_seconds=atom_execution_time
                    )

                    # Emit success/failure metrics
                    if retry_result.success:
                        ATOMS_SUCCEEDED_TOTAL.labels(
                            masterplan_id=str(masterplan_id) if masterplan_id else "unknown"
                        ).inc()
                        logger.debug(f"  ✅ {atom.name} succeeded (attempt {retry_result.attempts_used})")
                    else:
                        ATOMS_FAILED_TOTAL.labels(
                            masterplan_id=str(masterplan_id) if masterplan_id else "unknown"
                        ).inc()
                        logger.warning(f"  ❌ {atom.name} failed after {retry_result.attempts_used} attempts")

                    return result

                except Exception as e:
                    atom_execution_time = time.time() - atom_start_time
                    logger.error(f"  ⚠️ Exception executing {atom.name}: {e}")

                    ATOMS_FAILED_TOTAL.labels(
                        masterplan_id=str(masterplan_id) if masterplan_id else "unknown"
                    ).inc()

                    return ExecutionResult(
                        atom_id=atom.id,
                        success=False,
                        error_message=f"Exception: {str(e)}",
                        execution_time_seconds=atom_execution_time
                    )

        # Execute all atoms in parallel
        tasks = [execute_atom(atom) for atom in wave_atoms]
        atom_results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for atom, result in zip(wave_atoms, atom_results_list):
            if isinstance(result, Exception):
                logger.error(f"  ⚠️ Exception in gather for {atom.name}: {result}")
                results[atom.id] = ExecutionResult(
                    atom_id=atom.id,
                    success=False,
                    error_message=f"Gather exception: {str(result)}"
                )
            else:
                results[atom.id] = result

        # Calculate wave statistics
        execution_time = time.time() - start_time
        succeeded = sum(1 for r in results.values() if r.success)
        failed = len(results) - succeeded

        # Emit wave metrics
        WAVE_TIME_SECONDS.labels(
            wave_id=str(wave_id),
            masterplan_id=str(masterplan_id) if masterplan_id else "unknown"
        ).observe(execution_time)

        # Calculate throughput (atoms/second)
        throughput = len(wave_atoms) / execution_time if execution_time > 0 else 0
        WAVE_ATOM_THROUGHPUT.set(throughput)

        logger.info(
            f"  ✅ Wave {wave_id} complete: {succeeded}/{len(wave_atoms)} succeeded "
            f"in {execution_time:.1f}s ({throughput:.1f} atoms/s)"
        )

        return WaveResult(
            wave_id=wave_id,
            total_atoms=len(wave_atoms),
            succeeded=succeeded,
            failed=failed,
            execution_time_seconds=execution_time,
            atom_results=results
        )

    async def execute_plan(
        self,
        execution_plan: List,  # List[ExecutionWave]
        atoms: Dict[str, any],  # Dict[atom_id, AtomicUnit]
        masterplan_id: Optional[UUID] = None
    ) -> Dict[UUID, ExecutionResult]:
        """
        Execute complete execution plan (sequential waves, parallel atoms within wave).

        Args:
            execution_plan: List of waves to execute
            atoms: All atoms keyed by ID
            masterplan_id: Optional masterplan ID for metrics

        Returns:
            Dict mapping atom_id to ExecutionResult
        """
        logger.info("=" * 70)
        logger.info("⚙️  PHASE 6: EXECUTION + RETRY")
        logger.info("=" * 70)

        all_results: Dict[UUID, ExecutionResult] = {}
        total_atoms = sum(len(getattr(wave, "atom_ids", [])) for wave in execution_plan)
        completed = 0

        for wave in execution_plan:
            wave_id = getattr(wave, "level", 0)
            atom_ids = getattr(wave, "atom_ids", [])

            logger.info(f"\n📋 Executing Wave {wave_id} ({len(atom_ids)} atoms)...")

            # Get wave atoms
            wave_atoms = [atoms[aid] for aid in atom_ids if aid in atoms]

            if not wave_atoms:
                logger.warning(f"  ⚠️ No atoms found for wave {wave_id}, skipping")
                continue

            # Execute wave
            wave_result = await self.execute_wave(
                wave_id=wave_id,
                wave_atoms=wave_atoms,
                all_atoms=atoms,
                masterplan_id=masterplan_id
            )

            # Update all_results
            all_results.update(wave_result.atom_results)

            # Update progress
            completed += len(atom_ids)
            completion_percent = (completed / total_atoms * 100) if total_atoms > 0 else 0

            # Emit wave completion metric
            WAVE_COMPLETION_PERCENT.labels(
                wave_id=str(wave_id),
                masterplan_id=str(masterplan_id) if masterplan_id else "unknown"
            ).set(completion_percent)

            logger.info(
                f"  Progress: {completed}/{total_atoms} atoms "
                f"({completion_percent:.1f}% complete)"
            )

        # Final summary
        total_success = sum(1 for r in all_results.values() if r.success)
        precision = (total_success / total_atoms * 100) if total_atoms > 0 else 0

        logger.info(f"\n🎯 Final Results:")
        logger.info(f"  Success: {total_success}/{total_atoms} ({precision:.1f}%)")
        logger.info(f"  Failed: {total_atoms - total_success}")
        logger.info("=" * 70)

        return all_results
