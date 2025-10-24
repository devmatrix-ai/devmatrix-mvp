"""
Result Aggregator - Execution Result Aggregation

Aggregates and combines execution results across atoms, modules, and components.

Features:
- Hierarchical result aggregation
- Module-level result combining
- Component-level result combining
- System-level result combining
- Output merging and deduplication

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .code_executor import ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class AggregatedResult:
    """Aggregated execution result"""
    level: str  # 'atom', 'module', 'component', 'system'
    entity_id: uuid.UUID  # Atom, Module, Component, or MasterPlan ID
    total_atoms: int
    successful_atoms: int
    failed_atoms: int
    success_rate: float
    total_execution_time: float
    avg_execution_time: float
    combined_stdout: str = ""
    combined_stderr: str = ""
    errors: List[Dict[str, Any]] = field(default_factory=list)
    atom_results: List[ExecutionResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResultAggregator:
    """
    Result aggregator - Combines execution results

    Aggregation levels:
    1. Atom: Individual result (passthrough)
    2. Module: Combine all atoms in module
    3. Component: Combine all modules in component
    4. System: Combine all components

    Aggregation strategies:
    - Sequential: Results in execution order
    - Parallel: Results from parallel execution
    - Hierarchical: Nested aggregation by structure
    """

    def __init__(self):
        """Initialize result aggregator"""
        logger.info("ResultAggregator initialized")

    def aggregate_atom_results(
        self,
        results: List[ExecutionResult]
    ) -> AggregatedResult:
        """
        Aggregate multiple atom results

        Args:
            results: List of execution results

        Returns:
            AggregatedResult with combined data
        """
        if not results:
            return AggregatedResult(
                level='atom',
                entity_id=uuid.uuid4(),
                total_atoms=0,
                successful_atoms=0,
                failed_atoms=0,
                success_rate=0.0,
                total_execution_time=0.0,
                avg_execution_time=0.0
            )

        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_time = sum(r.execution_time for r in results)

        # Combine outputs
        combined_stdout = self._combine_outputs([r.stdout for r in results if r.stdout])
        combined_stderr = self._combine_outputs([r.stderr for r in results if r.stderr])

        # Collect errors
        errors = []
        for result in results:
            if not result.success and result.error_message:
                errors.append({
                    'atom_id': str(result.atom_id),
                    'error_message': result.error_message,
                    'exception_type': result.exception_type,
                    'stderr': result.stderr
                })

        # Determine overall entity_id (use first result's atom_id)
        entity_id = results[0].atom_id

        # Get time range
        started_at = min((r.started_at for r in results if r.started_at), default=None)
        completed_at = max((r.completed_at for r in results if r.completed_at), default=None)

        return AggregatedResult(
            level='atom',
            entity_id=entity_id,
            total_atoms=len(results),
            successful_atoms=successful,
            failed_atoms=failed,
            success_rate=successful / len(results) if results else 0.0,
            total_execution_time=total_time,
            avg_execution_time=total_time / len(results) if results else 0.0,
            combined_stdout=combined_stdout,
            combined_stderr=combined_stderr,
            errors=errors,
            atom_results=results,
            started_at=started_at,
            completed_at=completed_at
        )

    def aggregate_module_results(
        self,
        module_id: uuid.UUID,
        atom_results: List[ExecutionResult]
    ) -> AggregatedResult:
        """
        Aggregate results for a module

        Args:
            module_id: Module UUID
            atom_results: List of atom execution results

        Returns:
            AggregatedResult at module level
        """
        logger.debug(f"Aggregating module results: {module_id}")

        # First aggregate atoms
        atom_aggregated = self.aggregate_atom_results(atom_results)

        # Convert to module level
        module_result = AggregatedResult(
            level='module',
            entity_id=module_id,
            total_atoms=atom_aggregated.total_atoms,
            successful_atoms=atom_aggregated.successful_atoms,
            failed_atoms=atom_aggregated.failed_atoms,
            success_rate=atom_aggregated.success_rate,
            total_execution_time=atom_aggregated.total_execution_time,
            avg_execution_time=atom_aggregated.avg_execution_time,
            combined_stdout=atom_aggregated.combined_stdout,
            combined_stderr=atom_aggregated.combined_stderr,
            errors=atom_aggregated.errors,
            atom_results=atom_aggregated.atom_results,
            started_at=atom_aggregated.started_at,
            completed_at=atom_aggregated.completed_at
        )

        logger.debug(f"Module aggregation complete: {module_result.success_rate:.1%} success rate")
        return module_result

    def aggregate_component_results(
        self,
        component_id: uuid.UUID,
        module_results: List[AggregatedResult]
    ) -> AggregatedResult:
        """
        Aggregate results for a component

        Args:
            component_id: Component UUID
            module_results: List of module aggregated results

        Returns:
            AggregatedResult at component level
        """
        logger.debug(f"Aggregating component results: {component_id}")

        if not module_results:
            return AggregatedResult(
                level='component',
                entity_id=component_id,
                total_atoms=0,
                successful_atoms=0,
                failed_atoms=0,
                success_rate=0.0,
                total_execution_time=0.0,
                avg_execution_time=0.0
            )

        # Aggregate across modules
        total_atoms = sum(m.total_atoms for m in module_results)
        successful = sum(m.successful_atoms for m in module_results)
        failed = sum(m.failed_atoms for m in module_results)
        total_time = sum(m.total_execution_time for m in module_results)

        # Combine outputs from all modules
        combined_stdout = self._combine_outputs([m.combined_stdout for m in module_results if m.combined_stdout])
        combined_stderr = self._combine_outputs([m.combined_stderr for m in module_results if m.combined_stderr])

        # Collect all errors
        all_errors = []
        for module in module_results:
            all_errors.extend(module.errors)

        # Collect all atom results
        all_atom_results = []
        for module in module_results:
            all_atom_results.extend(module.atom_results)

        # Get time range
        started_at = min((m.started_at for m in module_results if m.started_at), default=None)
        completed_at = max((m.completed_at for m in module_results if m.completed_at), default=None)

        return AggregatedResult(
            level='component',
            entity_id=component_id,
            total_atoms=total_atoms,
            successful_atoms=successful,
            failed_atoms=failed,
            success_rate=successful / total_atoms if total_atoms > 0 else 0.0,
            total_execution_time=total_time,
            avg_execution_time=total_time / total_atoms if total_atoms > 0 else 0.0,
            combined_stdout=combined_stdout,
            combined_stderr=combined_stderr,
            errors=all_errors,
            atom_results=all_atom_results,
            started_at=started_at,
            completed_at=completed_at
        )

    def aggregate_system_results(
        self,
        masterplan_id: uuid.UUID,
        component_results: List[AggregatedResult]
    ) -> AggregatedResult:
        """
        Aggregate results for entire system

        Args:
            masterplan_id: MasterPlan UUID
            component_results: List of component aggregated results

        Returns:
            AggregatedResult at system level
        """
        logger.info(f"Aggregating system results: {masterplan_id}")

        if not component_results:
            return AggregatedResult(
                level='system',
                entity_id=masterplan_id,
                total_atoms=0,
                successful_atoms=0,
                failed_atoms=0,
                success_rate=0.0,
                total_execution_time=0.0,
                avg_execution_time=0.0
            )

        # Aggregate across components
        total_atoms = sum(c.total_atoms for c in component_results)
        successful = sum(c.successful_atoms for c in component_results)
        failed = sum(c.failed_atoms for c in component_results)
        total_time = sum(c.total_execution_time for c in component_results)

        # Combine outputs from all components
        combined_stdout = self._combine_outputs([c.combined_stdout for c in component_results if c.combined_stdout])
        combined_stderr = self._combine_outputs([c.combined_stderr for c in component_results if c.combined_stderr])

        # Collect all errors
        all_errors = []
        for component in component_results:
            all_errors.extend(component.errors)

        # Collect all atom results
        all_atom_results = []
        for component in component_results:
            all_atom_results.extend(component.atom_results)

        # Get time range
        started_at = min((c.started_at for c in component_results if c.started_at), default=None)
        completed_at = max((c.completed_at for c in component_results if c.completed_at), default=None)

        result = AggregatedResult(
            level='system',
            entity_id=masterplan_id,
            total_atoms=total_atoms,
            successful_atoms=successful,
            failed_atoms=failed,
            success_rate=successful / total_atoms if total_atoms > 0 else 0.0,
            total_execution_time=total_time,
            avg_execution_time=total_time / total_atoms if total_atoms > 0 else 0.0,
            combined_stdout=combined_stdout,
            combined_stderr=combined_stderr,
            errors=all_errors,
            atom_results=all_atom_results,
            started_at=started_at,
            completed_at=completed_at
        )

        logger.info(f"System aggregation complete: {result.successful_atoms}/{result.total_atoms} succeeded ({result.success_rate:.1%})")
        return result

    def _combine_outputs(self, outputs: List[str]) -> str:
        """
        Combine multiple outputs with deduplication

        Args:
            outputs: List of output strings

        Returns:
            Combined output string
        """
        if not outputs:
            return ""

        # Simple combination with separators
        combined = []
        seen = set()

        for output in outputs:
            output = output.strip()
            if output and output not in seen:
                combined.append(output)
                seen.add(output)

        return "\n\n".join(combined)

    def format_result(
        self,
        result: AggregatedResult,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Format aggregated result as dictionary

        Args:
            result: Aggregated result
            include_details: Include detailed atom results

        Returns:
            Dictionary representation
        """
        formatted = {
            'level': result.level,
            'entity_id': str(result.entity_id),
            'summary': {
                'total_atoms': result.total_atoms,
                'successful_atoms': result.successful_atoms,
                'failed_atoms': result.failed_atoms,
                'success_rate': result.success_rate,
            },
            'performance': {
                'total_execution_time': result.total_execution_time,
                'avg_execution_time': result.avg_execution_time,
                'started_at': result.started_at.isoformat() if result.started_at else None,
                'completed_at': result.completed_at.isoformat() if result.completed_at else None
            },
            'output': {
                'stdout': result.combined_stdout if result.combined_stdout else None,
                'stderr': result.combined_stderr if result.combined_stderr else None
            },
            'errors': result.errors
        }

        if include_details and result.atom_results:
            formatted['atom_details'] = [
                {
                    'atom_id': str(r.atom_id),
                    'success': r.success,
                    'execution_time': r.execution_time,
                    'error': r.error_message if r.error_message else None
                }
                for r in result.atom_results
            ]

        return formatted
