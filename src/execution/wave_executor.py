"""
WaveExecutor - Parallel execution of atoms within dependency waves

Executes atoms in parallel within each wave, respecting dependency constraints
and managing concurrency with error isolation.

Author: DevMatrix Team
Date: 2025-10-24
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from sqlalchemy.orm import Session

from ..models import AtomicUnit, DependencyGraph
from ..observability import StructuredLogger


logger = StructuredLogger("wave_executor", output_json=True)


class AtomStatus(Enum):
    """Atom execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AtomExecutionResult:
    """Result of single atom execution"""
    atom_id: uuid.UUID
    status: AtomStatus
    generated_code: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WaveExecutionResult:
    """Result of wave execution"""
    wave_number: int
    total_atoms: int
    successful: int
    failed: int
    skipped: int
    execution_time_seconds: float
    atom_results: List[AtomExecutionResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class WaveExecutor:
    """
    Executes atoms in parallel within dependency waves.

    Features:
    - Parallel execution within wave (100+ concurrent atoms)
    - Dependency-aware coordination between waves
    - Error isolation (one failure doesn't stop others)
    - Progress tracking
    - Configurable concurrency limits
    """

    def __init__(
        self,
        db: Session,
        code_generator: Optional[Callable] = None,
        max_concurrent: int = 100,
        timeout_seconds: int = 300
    ):
        """
        Initialize WaveExecutor

        Args:
            db: Database session
            code_generator: Optional code generation function (atom, attempt) -> code
            max_concurrent: Max concurrent atom executions (default: 100)
            timeout_seconds: Timeout per atom execution (default: 300s)
        """
        self.db = db
        self.code_generator = code_generator
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds

        # Execution state
        self._execution_state: Dict[uuid.UUID, AtomExecutionResult] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def execute_wave(
        self,
        wave_number: int,
        wave_atoms: List[AtomicUnit],
        masterplan_id: uuid.UUID
    ) -> WaveExecutionResult:
        """
        Execute all atoms in a wave in parallel

        Args:
            wave_number: Wave number (0-indexed)
            wave_atoms: List of atoms in this wave
            masterplan_id: MasterPlan ID for context

        Returns:
            WaveExecutionResult with execution summary
        """
        logger.info(
            f"Starting wave {wave_number} execution",
            extra={
                "wave_number": wave_number,
                "atom_count": len(wave_atoms),
                "masterplan_id": str(masterplan_id)
            }
        )

        start_time = datetime.utcnow()

        # Create semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        # Execute all atoms in parallel
        tasks = [
            self._execute_atom_with_semaphore(atom, masterplan_id)
            for atom in wave_atoms
        ]

        atom_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = 0
        failed = 0
        skipped = 0
        errors = []

        for result in atom_results:
            if isinstance(result, Exception):
                failed += 1
                errors.append(f"Unexpected exception: {str(result)}")
                continue

            if result.status == AtomStatus.SUCCESS:
                successful += 1
            elif result.status == AtomStatus.FAILED:
                failed += 1
                if result.error_message:
                    errors.append(result.error_message)
            elif result.status == AtomStatus.SKIPPED:
                skipped += 1

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        wave_result = WaveExecutionResult(
            wave_number=wave_number,
            total_atoms=len(wave_atoms),
            successful=successful,
            failed=failed,
            skipped=skipped,
            execution_time_seconds=execution_time,
            atom_results=[r for r in atom_results if isinstance(r, AtomExecutionResult)],
            errors=errors
        )

        logger.info(
            f"Wave {wave_number} completed",
            extra={
                "wave_number": wave_number,
                "total": len(wave_atoms),
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "execution_time": execution_time
            }
        )

        return wave_result

    async def _execute_atom_with_semaphore(
        self,
        atom: AtomicUnit,
        masterplan_id: uuid.UUID
    ) -> AtomExecutionResult:
        """Execute atom with semaphore-based concurrency control"""
        async with self._semaphore:
            return await self.execute_atom(atom, masterplan_id)

    async def execute_atom(
        self,
        atom: AtomicUnit,
        masterplan_id: uuid.UUID,
        retry_count: int = 0
    ) -> AtomExecutionResult:
        """
        Execute single atom

        Args:
            atom: Atom to execute
            masterplan_id: MasterPlan ID for context
            retry_count: Current retry attempt number

        Returns:
            AtomExecutionResult with execution details
        """
        logger.debug(
            f"Executing atom {atom.atom_id}",
            extra={
                "atom_id": str(atom.atom_id),
                "atom_number": atom.atom_number,
                "description": atom.description,
                "retry_count": retry_count
            }
        )

        start_time = datetime.utcnow()

        # Check dependencies
        if not self._check_dependencies(atom):
            logger.warning(
                f"Atom {atom.atom_id} dependencies not satisfied, skipping",
                extra={"atom_id": str(atom.atom_id)}
            )
            return AtomExecutionResult(
                atom_id=atom.atom_id,
                status=AtomStatus.SKIPPED,
                error_message="Dependencies not satisfied",
                retry_count=retry_count
            )

        try:
            # Generate code for atom
            if self.code_generator:
                generated_code = await asyncio.wait_for(
                    self._generate_code_async(atom, retry_count),
                    timeout=self.timeout_seconds
                )
            else:
                # Mock implementation for testing
                generated_code = atom.code_to_generate

            # Update atom in database
            atom.generated_code = generated_code
            atom.status = "completed"
            atom.completed_at = datetime.utcnow()
            self.db.commit()

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            result = AtomExecutionResult(
                atom_id=atom.atom_id,
                status=AtomStatus.SUCCESS,
                generated_code=generated_code,
                execution_time_seconds=execution_time,
                retry_count=retry_count
            )

            self._execution_state[atom.atom_id] = result

            logger.info(
                f"Atom {atom.atom_id} executed successfully",
                extra={
                    "atom_id": str(atom.atom_id),
                    "execution_time": execution_time,
                    "retry_count": retry_count
                }
            )

            return result

        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Atom execution timeout ({self.timeout_seconds}s)"

            logger.error(
                error_msg,
                extra={"atom_id": str(atom.atom_id)}
            )

            result = AtomExecutionResult(
                atom_id=atom.atom_id,
                status=AtomStatus.FAILED,
                error_message=error_msg,
                execution_time_seconds=execution_time,
                retry_count=retry_count
            )

            self._execution_state[atom.atom_id] = result
            return result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Atom execution failed: {str(e)}"

            logger.error(
                error_msg,
                extra={
                    "atom_id": str(atom.atom_id),
                    "error": str(e)
                },
                exc_info=True
            )

            # Update atom status
            atom.status = "failed"
            atom.error_message = error_msg
            self.db.commit()

            result = AtomExecutionResult(
                atom_id=atom.atom_id,
                status=AtomStatus.FAILED,
                error_message=error_msg,
                execution_time_seconds=execution_time,
                retry_count=retry_count
            )

            self._execution_state[atom.atom_id] = result
            return result

    async def _generate_code_async(
        self,
        atom: AtomicUnit,
        retry_count: int
    ) -> str:
        """
        Async wrapper for code generation

        Args:
            atom: Atom to generate code for
            retry_count: Current retry attempt

        Returns:
            Generated code string
        """
        # Run code generation in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.code_generator,
            atom,
            retry_count
        )

    def _check_dependencies(self, atom: AtomicUnit) -> bool:
        """
        Check if atom dependencies are satisfied

        Args:
            atom: Atom to check

        Returns:
            True if all dependencies satisfied, False otherwise
        """
        if not atom.dependencies:
            return True

        # Check if all dependency atoms have been executed successfully
        for dep_id in atom.dependencies:
            dep_result = self._execution_state.get(dep_id)

            if not dep_result:
                # Dependency not yet executed
                return False

            if dep_result.status != AtomStatus.SUCCESS:
                # Dependency failed
                return False

        return True

    def manage_concurrency(self, max_concurrent: int):
        """
        Update concurrency limit

        Args:
            max_concurrent: New maximum concurrent executions
        """
        logger.info(
            f"Updating concurrency limit: {self.max_concurrent} → {max_concurrent}"
        )
        self.max_concurrent = max_concurrent

        # Semaphore will be recreated on next wave execution
        self._semaphore = None

    def track_progress(self) -> Dict[str, Any]:
        """
        Get current execution progress

        Returns:
            Progress statistics dictionary
        """
        total = len(self._execution_state)

        if total == 0:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "progress_percentage": 0.0
            }

        completed = sum(
            1 for r in self._execution_state.values()
            if r.status == AtomStatus.SUCCESS
        )

        failed = sum(
            1 for r in self._execution_state.values()
            if r.status == AtomStatus.FAILED
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "progress_percentage": (completed / total) * 100 if total > 0 else 0.0
        }

    def handle_errors(self) -> List[AtomExecutionResult]:
        """
        Get all failed atom executions

        Returns:
            List of failed AtomExecutionResult objects
        """
        return [
            result for result in self._execution_state.values()
            if result.status == AtomStatus.FAILED
        ]

    def coordinate_dependencies(
        self,
        masterplan_id: uuid.UUID
    ) -> List[List[AtomicUnit]]:
        """
        Organize atoms into waves based on dependency graph

        Args:
            masterplan_id: MasterPlan ID

        Returns:
            List of waves, where each wave is a list of atoms
        """
        # Load dependency graph
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if not dep_graph or not dep_graph.waves:
            logger.warning(
                f"No dependency graph found for masterplan {masterplan_id}"
            )
            return []

        # Load all atoms for this masterplan
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        # Create atom lookup by ID
        atom_lookup = {atom.atom_id: atom for atom in atoms}

        # Organize atoms into waves
        waves = []
        for wave_data in dep_graph.waves:
            wave_atoms = []
            for atom_id_str in wave_data.get('atoms', []):
                atom_id = uuid.UUID(atom_id_str)
                if atom_id in atom_lookup:
                    wave_atoms.append(atom_lookup[atom_id])

            if wave_atoms:
                waves.append(wave_atoms)

        logger.info(
            f"Organized {len(atoms)} atoms into {len(waves)} waves",
            extra={
                "masterplan_id": str(masterplan_id),
                "total_atoms": len(atoms),
                "wave_count": len(waves)
            }
        )

        return waves

    def reset_state(self):
        """Reset execution state (for new masterplan execution)"""
        self._execution_state.clear()
        self._semaphore = None
        logger.info("Execution state reset")
