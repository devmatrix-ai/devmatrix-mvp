"""
Execution Service - Code Execution Orchestration

Orchestrates code execution with retry logic and monitoring.

Pipeline:
1. Load atoms from database
2. Execute atoms (waves or sequential)
3. Monitor execution
4. Handle failures with retry logic
5. Aggregate results
6. Persist execution records

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import logging

from src.execution.code_executor import CodeExecutor, ExecutionResult
from src.execution.retry_logic import RetryLogic, RetryDecision
from src.execution.monitoring_collector import MonitoringCollector
from src.execution.result_aggregator import ResultAggregator, AggregatedResult
from src.models import AtomicUnit, ExecutionWave, DependencyGraph
from src.dependency import TopologicalSorter

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Execution service - Orchestrates code execution

    Execution modes:
    - Single atom: Execute one atom
    - Batch: Execute multiple atoms
    - Wave: Execute atoms in dependency waves
    - Module: Execute all atoms in module
    - System: Execute entire masterplan

    Features:
    - Automatic retry on failure
    - Real-time monitoring
    - Result aggregation
    - Wave-based parallel execution
    """

    def __init__(self, db: Session, use_retry: bool = True):
        """
        Initialize execution service

        Args:
            db: Database session
            use_retry: Enable retry logic
        """
        self.db = db
        self.executor = CodeExecutor()
        self.retry_logic = RetryLogic() if use_retry else None
        self.monitoring = MonitoringCollector()
        self.aggregator = ResultAggregator()

        logger.info(f"ExecutionService initialized (retry={use_retry})")

    def execute_atom(
        self,
        atom_id: uuid.UUID,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute single atom"""
        logger.info(f"Executing atom: {atom_id}")

        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == atom_id
        ).first()

        if not atom:
            return {'success': False, 'error': 'Atom not found'}

        result = self._execute_with_retry(atom, input_data)
        self.monitoring.record_execution(result)

        return {
            'atom_id': str(result.atom_id),
            'success': result.success,
            'execution_time': result.execution_time,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'error': result.error_message
        }

    def execute_wave(
        self,
        masterplan_id: uuid.UUID,
        wave_number: int
    ) -> Dict[str, Any]:
        """Execute atoms in a wave"""
        logger.info(f"Executing wave {wave_number} for masterplan: {masterplan_id}")

        # Load wave
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if not dep_graph:
            return {'success': False, 'error': 'Dependency graph not found'}

        wave = self.db.query(ExecutionWave).filter(
            ExecutionWave.graph_id == dep_graph.graph_id,
            ExecutionWave.wave_number == wave_number
        ).first()

        if not wave:
            return {'success': False, 'error': f'Wave {wave_number} not found'}

        # Load atoms in wave
        atom_ids = [uuid.UUID(aid) for aid in wave.atom_ids]
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id.in_(atom_ids)
        ).all()

        # Execute wave
        self.monitoring.start_wave(wave_number, len(atoms))
        results = []

        for atom in atoms:
            result = self._execute_with_retry(atom)
            self.monitoring.record_execution(result, wave_number=wave_number)
            results.append(result)

        self.monitoring.complete_wave(wave_number)

        # Aggregate results
        aggregated = self.aggregator.aggregate_atom_results(results)

        return {
            'wave_number': wave_number,
            'total_atoms': len(results),
            'successful': aggregated.successful_atoms,
            'failed': aggregated.failed_atoms,
            'success_rate': aggregated.success_rate,
            'execution_time': aggregated.total_execution_time
        }

    def execute_masterplan(
        self,
        masterplan_id: uuid.UUID,
        execute_by_waves: bool = True
    ) -> Dict[str, Any]:
        """Execute entire masterplan"""
        logger.info(f"Executing masterplan: {masterplan_id}")

        if execute_by_waves:
            return self._execute_by_waves(masterplan_id)
        else:
            return self._execute_sequential(masterplan_id)

    def _execute_by_waves(self, masterplan_id: uuid.UUID) -> Dict[str, Any]:
        """Execute masterplan using dependency waves"""
        # Load dependency graph
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if not dep_graph:
            return {'success': False, 'error': 'Dependency graph not found. Build graph first.'}

        # Get all waves
        waves = self.db.query(ExecutionWave).filter(
            ExecutionWave.graph_id == dep_graph.graph_id
        ).order_by(ExecutionWave.wave_number).all()

        wave_results = []

        for wave in waves:
            wave_result = self.execute_wave(masterplan_id, wave.wave_number)
            wave_results.append(wave_result)

            # Stop if wave failed
            if wave_result.get('success_rate', 0) < 0.5:
                logger.warning(f"Wave {wave.wave_number} failed, stopping execution")
                break

        # Get overall metrics
        metrics = self.monitoring.get_summary()

        return {
            'masterplan_id': str(masterplan_id),
            'execution_mode': 'waves',
            'total_waves': len(waves),
            'completed_waves': len(wave_results),
            'metrics': metrics
        }

    def _execute_sequential(self, masterplan_id: uuid.UUID) -> Dict[str, Any]:
        """Execute masterplan sequentially"""
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        results = []
        for atom in atoms:
            result = self._execute_with_retry(atom)
            self.monitoring.record_execution(result)
            results.append(result)

        aggregated = self.aggregator.aggregate_atom_results(results)

        return {
            'masterplan_id': str(masterplan_id),
            'execution_mode': 'sequential',
            'total_atoms': len(results),
            'successful': aggregated.successful_atoms,
            'failed': aggregated.failed_atoms,
            'success_rate': aggregated.success_rate
        }

    def _execute_with_retry(
        self,
        atom: AtomicUnit,
        input_data: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3
    ) -> ExecutionResult:
        """Execute atom with retry logic"""
        attempt = 0

        while attempt < max_attempts:
            result = self.executor.execute_atom(atom, input_data)

            if result.success or not self.retry_logic:
                return result

            # Analyze failure and decide retry
            decision = self.retry_logic.analyze_failure(atom, result)

            if not decision.should_retry:
                logger.info(f"Not retrying atom {atom.atom_id}: {decision.reason}")
                return result

            logger.info(f"Retrying atom {atom.atom_id} (attempt {attempt + 1}): {decision.retry_strategy}")
            attempt += 1

        return result

    def get_execution_summary(self, masterplan_id: uuid.UUID) -> Dict[str, Any]:
        """Get execution summary"""
        return self.monitoring.get_summary()
