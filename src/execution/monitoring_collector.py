"""
Monitoring Collector - Real-Time Execution Monitoring

Collects and aggregates execution metrics for performance analysis.

Metrics tracked:
- Execution time per atom
- Memory usage
- Success/failure rates
- Error patterns
- Retry statistics
- Wave-level performance

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from .code_executor import ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Execution metrics for an atom or wave"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0  # Seconds
    max_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    total_execution_time: float = 0.0
    avg_memory_used: int = 0  # Bytes
    max_memory_used: int = 0
    error_count_by_type: Dict[str, int] = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class WaveMetrics:
    """Metrics for an execution wave"""
    wave_number: int
    total_atoms: int
    completed_atoms: int = 0
    successful_atoms: int = 0
    failed_atoms: int = 0
    avg_execution_time: float = 0.0
    total_execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parallelism_achieved: float = 0.0  # Actual vs theoretical


class MonitoringCollector:
    """
    Monitoring collector - Real-time execution tracking

    Collects and aggregates:
    1. Atom-level metrics
    2. Wave-level metrics
    3. System-level metrics
    4. Error patterns
    5. Performance trends

    Used for:
    - Real-time monitoring dashboards
    - Performance optimization
    - Error pattern detection
    - Retry decision making
    - Resource planning
    """

    def __init__(self):
        """Initialize monitoring collector"""
        self.atom_metrics: Dict[uuid.UUID, ExecutionMetrics] = {}
        self.wave_metrics: Dict[int, WaveMetrics] = {}
        self.system_metrics = ExecutionMetrics()
        self.execution_timeline: List[Dict[str, Any]] = []

        logger.info("MonitoringCollector initialized")

    def record_execution(
        self,
        result: ExecutionResult,
        wave_number: Optional[int] = None,
        retry_attempt: int = 0
    ) -> None:
        """
        Record execution result

        Args:
            result: Execution result to record
            wave_number: Optional wave number
            retry_attempt: Retry attempt number (0 = first attempt)
        """
        logger.debug(f"Recording execution: atom={result.atom_id}, success={result.success}")

        # Update atom metrics
        if result.atom_id not in self.atom_metrics:
            self.atom_metrics[result.atom_id] = ExecutionMetrics()

        atom_metrics = self.atom_metrics[result.atom_id]
        self._update_metrics(atom_metrics, result, retry_attempt)

        # Update wave metrics
        if wave_number is not None:
            if wave_number not in self.wave_metrics:
                self.wave_metrics[wave_number] = WaveMetrics(
                    wave_number=wave_number,
                    total_atoms=0  # Will be set when wave starts
                )

            wave_metrics = self.wave_metrics[wave_number]
            self._update_wave_metrics(wave_metrics, result)

        # Update system metrics
        self._update_metrics(self.system_metrics, result, retry_attempt)

        # Add to timeline
        self.execution_timeline.append({
            'timestamp': result.completed_at or datetime.utcnow(),
            'atom_id': str(result.atom_id),
            'wave_number': wave_number,
            'success': result.success,
            'execution_time': result.execution_time,
            'retry_attempt': retry_attempt
        })

    def _update_metrics(
        self,
        metrics: ExecutionMetrics,
        result: ExecutionResult,
        retry_attempt: int
    ) -> None:
        """Update metrics with execution result"""
        metrics.total_executions += 1

        if result.success:
            metrics.successful_executions += 1
        else:
            metrics.failed_executions += 1

            # Track error types
            if result.exception_type:
                error_type = result.exception_type
                metrics.error_count_by_type[error_type] = \
                    metrics.error_count_by_type.get(error_type, 0) + 1

        # Update execution time stats
        if result.execution_time > 0:
            metrics.total_execution_time += result.execution_time
            metrics.avg_execution_time = \
                metrics.total_execution_time / metrics.total_executions
            metrics.max_execution_time = max(
                metrics.max_execution_time, result.execution_time
            )
            metrics.min_execution_time = min(
                metrics.min_execution_time, result.execution_time
            )

        # Update memory stats
        if result.memory_used > 0:
            metrics.avg_memory_used = (
                (metrics.avg_memory_used * (metrics.total_executions - 1) + result.memory_used)
                / metrics.total_executions
            )
            metrics.max_memory_used = max(metrics.max_memory_used, result.memory_used)

        # Track retries
        if retry_attempt > 0:
            metrics.retry_count += 1

    def _update_wave_metrics(
        self,
        wave_metrics: WaveMetrics,
        result: ExecutionResult
    ) -> None:
        """Update wave-level metrics"""
        wave_metrics.completed_atoms += 1

        if result.success:
            wave_metrics.successful_atoms += 1
        else:
            wave_metrics.failed_atoms += 1

        # Update wave timing
        if wave_metrics.started_at is None:
            wave_metrics.started_at = result.started_at

        if result.completed_at:
            wave_metrics.completed_at = result.completed_at

        # Update wave execution time
        if result.execution_time > 0:
            wave_metrics.total_execution_time += result.execution_time
            wave_metrics.avg_execution_time = \
                wave_metrics.total_execution_time / wave_metrics.completed_atoms

    def start_wave(self, wave_number: int, total_atoms: int) -> None:
        """
        Mark wave start

        Args:
            wave_number: Wave number
            total_atoms: Total atoms in wave
        """
        if wave_number not in self.wave_metrics:
            self.wave_metrics[wave_number] = WaveMetrics(
                wave_number=wave_number,
                total_atoms=total_atoms,
                started_at=datetime.utcnow()
            )
        else:
            self.wave_metrics[wave_number].total_atoms = total_atoms
            self.wave_metrics[wave_number].started_at = datetime.utcnow()

        logger.info(f"Wave {wave_number} started with {total_atoms} atoms")

    def complete_wave(self, wave_number: int) -> None:
        """
        Mark wave completion

        Args:
            wave_number: Wave number
        """
        if wave_number in self.wave_metrics:
            wave = self.wave_metrics[wave_number]
            wave.completed_at = datetime.utcnow()

            # Calculate parallelism achieved
            if wave.started_at and wave.completed_at and wave.total_execution_time > 0:
                wall_clock_time = (wave.completed_at - wave.started_at).total_seconds()
                theoretical_parallel_time = wave.total_execution_time / wave.total_atoms if wave.total_atoms > 0 else 0
                if theoretical_parallel_time > 0:
                    wave.parallelism_achieved = theoretical_parallel_time / wall_clock_time

            logger.info(f"Wave {wave_number} completed: {wave.successful_atoms}/{wave.total_atoms} succeeded")

    def get_atom_metrics(self, atom_id: uuid.UUID) -> Optional[ExecutionMetrics]:
        """Get metrics for specific atom"""
        return self.atom_metrics.get(atom_id)

    def get_wave_metrics(self, wave_number: int) -> Optional[WaveMetrics]:
        """Get metrics for specific wave"""
        return self.wave_metrics.get(wave_number)

    def get_system_metrics(self) -> ExecutionMetrics:
        """Get system-wide metrics"""
        return self.system_metrics

    def get_summary(self) -> Dict[str, Any]:
        """
        Get execution summary

        Returns:
            Dictionary with summary statistics
        """
        system = self.system_metrics

        success_rate = (
            system.successful_executions / system.total_executions
            if system.total_executions > 0 else 0.0
        )

        return {
            'total_atoms_executed': len(self.atom_metrics),
            'total_executions': system.total_executions,
            'successful_executions': system.successful_executions,
            'failed_executions': system.failed_executions,
            'success_rate': success_rate,
            'avg_execution_time': system.avg_execution_time,
            'max_execution_time': system.max_execution_time,
            'total_execution_time': system.total_execution_time,
            'retry_count': system.retry_count,
            'error_types': system.error_count_by_type,
            'waves_executed': len(self.wave_metrics)
        }

    def get_error_analysis(self) -> Dict[str, Any]:
        """
        Analyze error patterns

        Returns:
            Dictionary with error analysis
        """
        all_errors = defaultdict(int)
        error_atoms = []

        for atom_id, metrics in self.atom_metrics.items():
            if metrics.failed_executions > 0:
                error_atoms.append(str(atom_id))
                for error_type, count in metrics.error_count_by_type.items():
                    all_errors[error_type] += count

        # Find most common errors
        sorted_errors = sorted(
            all_errors.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            'total_errors': sum(all_errors.values()),
            'unique_error_types': len(all_errors),
            'most_common_errors': sorted_errors[:5],
            'atoms_with_errors': error_atoms[:10],  # First 10
            'error_rate': (
                self.system_metrics.failed_executions / self.system_metrics.total_executions
                if self.system_metrics.total_executions > 0 else 0.0
            )
        }

    def get_performance_analysis(self) -> Dict[str, Any]:
        """
        Analyze performance characteristics

        Returns:
            Dictionary with performance analysis
        """
        # Find slowest atoms
        slow_atoms = sorted(
            [(atom_id, metrics) for atom_id, metrics in self.atom_metrics.items()],
            key=lambda x: x[1].avg_execution_time,
            reverse=True
        )[:5]

        # Analyze wave performance
        wave_performance = []
        for wave_num, wave in sorted(self.wave_metrics.items()):
            wave_performance.append({
                'wave_number': wave_num,
                'total_atoms': wave.total_atoms,
                'avg_execution_time': wave.avg_execution_time,
                'parallelism_achieved': wave.parallelism_achieved,
                'success_rate': wave.successful_atoms / wave.total_atoms if wave.total_atoms > 0 else 0
            })

        return {
            'avg_execution_time': self.system_metrics.avg_execution_time,
            'max_execution_time': self.system_metrics.max_execution_time,
            'min_execution_time': self.system_metrics.min_execution_time if self.system_metrics.min_execution_time != float('inf') else 0,
            'slowest_atoms': [
                {
                    'atom_id': str(atom_id),
                    'avg_time': metrics.avg_execution_time,
                    'max_time': metrics.max_execution_time
                }
                for atom_id, metrics in slow_atoms
            ],
            'wave_performance': wave_performance
        }

    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics for persistence

        Returns:
            Dictionary with all metrics
        """
        return {
            'system_metrics': {
                'total_executions': self.system_metrics.total_executions,
                'successful_executions': self.system_metrics.successful_executions,
                'failed_executions': self.system_metrics.failed_executions,
                'avg_execution_time': self.system_metrics.avg_execution_time,
                'max_execution_time': self.system_metrics.max_execution_time,
                'total_execution_time': self.system_metrics.total_execution_time,
                'retry_count': self.system_metrics.retry_count,
                'error_count_by_type': self.system_metrics.error_count_by_type
            },
            'atom_metrics': {
                str(atom_id): {
                    'total_executions': metrics.total_executions,
                    'successful_executions': metrics.successful_executions,
                    'failed_executions': metrics.failed_executions,
                    'avg_execution_time': metrics.avg_execution_time
                }
                for atom_id, metrics in self.atom_metrics.items()
            },
            'wave_metrics': {
                wave_num: {
                    'wave_number': wave.wave_number,
                    'total_atoms': wave.total_atoms,
                    'completed_atoms': wave.completed_atoms,
                    'successful_atoms': wave.successful_atoms,
                    'parallelism_achieved': wave.parallelism_achieved
                }
                for wave_num, wave in self.wave_metrics.items()
            }
        }
