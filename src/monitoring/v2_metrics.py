"""
MGE V2 Prometheus Metrics

Metrics for monitoring MGE V2 execution performance, quality, and cost.

Metrics:
- v2_execution_time_seconds: Total execution time per masterplan
- v2_atoms_generated_total: Total atoms generated
- v2_atoms_failed_total: Total atoms that failed
- v2_waves_executed_total: Total execution waves
- v2_parallel_atoms: Max atoms running in parallel
- v2_precision_percent: Execution precision percentage
- v2_cost_per_project_usd: Total cost per project

Author: DevMatrix Team
Date: 2025-10-23
"""

from prometheus_client import Counter, Gauge, Histogram, Summary
from typing import Optional


# Execution Time
v2_execution_time_seconds = Histogram(
    'v2_execution_time_seconds',
    'MGE V2 total execution time per masterplan (seconds)',
    buckets=[60, 300, 900, 1800, 3600, 5400, 7200],  # 1m, 5m, 15m, 30m, 1h, 1.5h, 2h
    labelnames=['masterplan_id', 'project_name', 'status']
)

# Atoms Generated
v2_atoms_generated_total = Counter(
    'v2_atoms_generated_total',
    'Total number of atomic units generated',
    labelnames=['masterplan_id', 'language']
)

# Atoms Failed
v2_atoms_failed_total = Counter(
    'v2_atoms_failed_total',
    'Total number of atomic units that failed',
    labelnames=['masterplan_id', 'failure_reason']
)

# Atoms Completed
v2_atoms_completed_total = Counter(
    'v2_atoms_completed_total',
    'Total number of atomic units completed successfully',
    labelnames=['masterplan_id']
)

# Execution Waves
v2_waves_executed_total = Gauge(
    'v2_waves_executed_total',
    'Total number of execution waves',
    labelnames=['masterplan_id', 'graph_id']
)

# Parallel Atoms (Max Parallelism)
v2_parallel_atoms = Gauge(
    'v2_parallel_atoms',
    'Maximum number of atoms running in parallel',
    labelnames=['masterplan_id', 'wave_number']
)

# Current Wave
v2_current_wave = Gauge(
    'v2_current_wave',
    'Current execution wave number',
    labelnames=['masterplan_id']
)

# Precision Percentage
v2_precision_percent = Gauge(
    'v2_precision_percent',
    'Execution precision percentage (0-100)',
    labelnames=['masterplan_id']
)

# Context Completeness
v2_context_completeness = Histogram(
    'v2_context_completeness',
    'Context completeness score per atom (0.0-1.0)',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0],
    labelnames=['masterplan_id']
)

# Atomicity Score
v2_atomicity_score = Histogram(
    'v2_atomicity_score',
    'Atomicity quality score per atom (0.0-1.0)',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
    labelnames=['masterplan_id']
)

# Confidence Score
v2_confidence_score = Histogram(
    'v2_confidence_score',
    'Confidence score per atom (0.0-1.0)',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
    labelnames=['masterplan_id']
)

# Validation Results
v2_validation_passed = Counter(
    'v2_validation_passed',
    'Validation tests passed',
    labelnames=['masterplan_id', 'validation_level', 'test_type']
)

v2_validation_failed = Counter(
    'v2_validation_failed',
    'Validation tests failed',
    labelnames=['masterplan_id', 'validation_level', 'test_type']
)

# Retry Attempts
v2_retry_attempts = Counter(
    'v2_retry_attempts',
    'Number of retry attempts',
    labelnames=['masterplan_id', 'attempt_number']
)

v2_retry_success = Counter(
    'v2_retry_success',
    'Successful retries',
    labelnames=['masterplan_id', 'attempt_number']
)

# Human Review
v2_review_queue_size = Gauge(
    'v2_review_queue_size',
    'Number of atoms in human review queue',
    labelnames=['status', 'priority']
)

v2_atoms_reviewed = Counter(
    'v2_atoms_reviewed',
    'Total atoms reviewed by humans',
    labelnames=['resolution']
)

# Cost Tracking
v2_cost_per_project_usd = Gauge(
    'v2_cost_per_project_usd',
    'Total LLM cost per project (USD)',
    labelnames=['masterplan_id', 'project_name']
)

v2_cost_per_atom_usd = Histogram(
    'v2_cost_per_atom_usd',
    'LLM cost per atom (USD)',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    labelnames=['masterplan_id']
)

v2_tokens_used = Counter(
    'v2_tokens_used',
    'Total tokens used',
    labelnames=['masterplan_id', 'operation']
)

# LOC per Atom
v2_loc_per_atom = Histogram(
    'v2_loc_per_atom',
    'Lines of code per atom',
    buckets=[5, 8, 10, 12, 15, 20, 25],
    labelnames=['masterplan_id', 'language']
)

# Complexity per Atom
v2_complexity_per_atom = Histogram(
    'v2_complexity_per_atom',
    'Cyclomatic complexity per atom',
    buckets=[1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
    labelnames=['masterplan_id', 'language']
)

# Graph Statistics
v2_graph_edges = Gauge(
    'v2_graph_edges',
    'Total edges in dependency graph',
    labelnames=['masterplan_id', 'graph_id']
)

v2_graph_has_cycles = Gauge(
    'v2_graph_has_cycles',
    'Whether dependency graph has cycles (1=yes, 0=no)',
    labelnames=['masterplan_id', 'graph_id']
)

# Wave Duration
v2_wave_duration_seconds = Histogram(
    'v2_wave_duration_seconds',
    'Wave execution duration (seconds)',
    buckets=[10, 30, 60, 120, 300, 600, 900],
    labelnames=['masterplan_id', 'wave_number']
)


# Helper functions for recording metrics
def record_execution_time(masterplan_id: str, project_name: str, duration_seconds: float, status: str):
    """Record total execution time for a masterplan"""
    v2_execution_time_seconds.labels(
        masterplan_id=masterplan_id,
        project_name=project_name,
        status=status
    ).observe(duration_seconds)


def record_atom_generated(masterplan_id: str, language: str):
    """Record an atom generation"""
    v2_atoms_generated_total.labels(
        masterplan_id=masterplan_id,
        language=language
    ).inc()


def record_atom_failed(masterplan_id: str, failure_reason: str):
    """Record an atom failure"""
    v2_atoms_failed_total.labels(
        masterplan_id=masterplan_id,
        failure_reason=failure_reason
    ).inc()


def record_atom_completed(masterplan_id: str):
    """Record an atom completion"""
    v2_atoms_completed_total.labels(masterplan_id=masterplan_id).inc()


def record_precision(masterplan_id: str, precision: float):
    """Record execution precision (0-100)"""
    v2_precision_percent.labels(masterplan_id=masterplan_id).set(precision)


def record_cost(masterplan_id: str, project_name: str, cost_usd: float):
    """Record project cost"""
    v2_cost_per_project_usd.labels(
        masterplan_id=masterplan_id,
        project_name=project_name
    ).set(cost_usd)


def record_validation(masterplan_id: str, level: str, test_type: str, passed: bool):
    """Record validation result"""
    if passed:
        v2_validation_passed.labels(
            masterplan_id=masterplan_id,
            validation_level=level,
            test_type=test_type
        ).inc()
    else:
        v2_validation_failed.labels(
            masterplan_id=masterplan_id,
            validation_level=level,
            test_type=test_type
        ).inc()


def record_retry(masterplan_id: str, attempt_number: int, success: bool):
    """Record retry attempt"""
    v2_retry_attempts.labels(
        masterplan_id=masterplan_id,
        attempt_number=str(attempt_number)
    ).inc()

    if success:
        v2_retry_success.labels(
            masterplan_id=masterplan_id,
            attempt_number=str(attempt_number)
        ).inc()


def update_review_queue(status: str, priority: int, count: int):
    """Update review queue size"""
    v2_review_queue_size.labels(
        status=status,
        priority=str(priority)
    ).set(count)


def record_atom_reviewed(resolution: str):
    """Record human review completion"""
    v2_atoms_reviewed.labels(resolution=resolution).inc()
