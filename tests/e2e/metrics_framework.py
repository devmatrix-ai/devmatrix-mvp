"""
E2E Test Metrics Collection Framework
Comprehensive metrics tracking for spec-to-app pipeline testing
"""

import time
import psutil
import json
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class PhaseMetrics:
    """Metrics for individual pipeline phase"""
    phase_name: str
    status: PhaseStatus = PhaseStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: Optional[int] = None
    checkpoints_total: int = 0
    checkpoints_completed: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retries: int = 0

    # Phase-specific metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    # Resource metrics
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None

    def start(self):
        self.start_time = time.time()
        self.status = PhaseStatus.IN_PROGRESS

    def complete(self):
        self.end_time = time.time()
        if self.start_time:
            self.duration_ms = int((self.end_time - self.start_time) * 1000)
        self.status = PhaseStatus.COMPLETED

    def fail(self, error: Dict[str, Any]):
        self.status = PhaseStatus.FAILED
        self.errors.append(error)

    def add_checkpoint(self):
        self.checkpoints_completed += 1

    def progress(self) -> float:
        if self.checkpoints_total == 0:
            return 0.0
        return self.checkpoints_completed / self.checkpoints_total


@dataclass
class PipelineMetrics:
    """
    Complete metrics for entire pipeline execution

    Tracks metrics for all pipeline phases including Phase 6.5 (Code Repair).

    Repair Metrics (Phase 6.5):
        repair_applied: Whether any repair was executed
        repair_iterations: Number of repair cycles (max 3)
        repair_improvement: Compliance delta (after - before)
        tests_fixed: Number of compliance issues resolved
        regressions_detected: Number of rollbacks due to regressions
        pattern_reuse_count: Times RAG patterns were reused
        repair_time_ms: Total repair phase duration
        repair_skipped: Whether repair was skipped (compliance >= 80%)
        repair_skip_reason: Reason for skipping repair
    """
    pipeline_id: str
    spec_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration_ms: Optional[int] = None

    # Phase metrics
    phases: Dict[str, PhaseMetrics] = field(default_factory=dict)

    # Overall metrics
    overall_status: str = "pending"
    overall_progress: float = 0.0

    # Pattern Bank metrics
    pattern_reuse_rate: float = 0.0
    patterns_matched: int = 0
    new_patterns_learned: int = 0

    # Learning metrics (Phase 10)
    patterns_stored: int = 0
    patterns_promoted: int = 0
    patterns_reused: int = 0
    learning_time_ms: float = 0.0
    candidates_created: int = 0

    # Quality metrics
    test_coverage: float = 0.0
    code_quality_score: float = 0.0
    acceptance_criteria_met: int = 0
    acceptance_criteria_total: int = 0

    # Performance metrics
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0

    # Database metrics
    neo4j_queries: int = 0
    neo4j_avg_query_ms: float = 0.0
    qdrant_queries: int = 0
    qdrant_avg_query_ms: float = 0.0

    # Error and recovery metrics
    total_errors: int = 0
    recovered_errors: int = 0
    critical_errors: int = 0
    recovery_success_rate: float = 0.0

    # E2E Precision metrics
    overall_accuracy: float = 0.0
    pipeline_precision: float = 0.0
    pattern_precision: float = 0.0
    pattern_recall: float = 0.0
    pattern_f1: float = 0.0
    classification_accuracy: float = 0.0
    execution_success_rate: float = 0.0
    test_pass_rate: float = 0.0
    contract_violations: int = 0

    # Phase 6.5: Code Repair metrics (Task Group 2.2)
    repair_applied: bool = False
    repair_iterations: int = 0
    repair_improvement: float = 0.0
    tests_fixed: int = 0
    regressions_detected: int = 0
    pattern_reuse_count: int = 0
    repair_time_ms: float = 0.0
    repair_skipped: bool = False
    repair_skip_reason: str = ""

    def initialize_phases(self):
        """Initialize all pipeline phases with checkpoints"""
        phase_configs = {
            "spec_ingestion": 4,  # checkpoints
            "requirements_analysis": 5,
            "multi_pass_planning": 5,
            "atomization": 5,
            "dag_construction": 5,
            "wave_execution": 5,
            "validation": 5,
            "deployment": 5,
            "health_verification": 5,
            "learning": 5  # Phase 10: Learning
        }

        for phase_name, checkpoint_count in phase_configs.items():
            self.phases[phase_name] = PhaseMetrics(
                phase_name=phase_name,
                checkpoints_total=checkpoint_count
            )

    def update_progress(self):
        """Calculate overall progress based on phase weights"""
        phase_weights = {
            "spec_ingestion": 0.02,
            "requirements_analysis": 0.08,
            "multi_pass_planning": 0.15,
            "atomization": 0.12,
            "dag_construction": 0.05,
            "wave_execution": 0.40,  # Reduced to make room for new phases
            "validation": 0.08,
            "deployment": 0.05,
            "health_verification": 0.025,
            "learning": 0.025
        }

        total_progress = 0.0
        for phase_name, weight in phase_weights.items():
            if phase_name in self.phases:
                phase_progress = self.phases[phase_name].progress()
                total_progress += phase_progress * weight

        self.overall_progress = total_progress

    def complete_pipeline(self):
        """Mark pipeline as complete and calculate final metrics"""
        self.end_time = time.time()
        self.total_duration_ms = int((self.end_time - self.start_time) * 1000)

        # Calculate success rate
        if self.total_errors > 0:
            self.recovery_success_rate = self.recovered_errors / self.total_errors

        # Determine overall status
        critical_phases_ok = all(
            self.phases[p].status == PhaseStatus.COMPLETED
            for p in ["wave_execution", "deployment", "health_verification"]
        )

        if critical_phases_ok and self.critical_errors == 0:
            self.overall_status = "success"
        elif critical_phases_ok:
            self.overall_status = "partial_success"
        else:
            self.overall_status = "failed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert phase objects
        result["phases"] = {
            name: asdict(phase) for name, phase in self.phases.items()
        }
        # Add timestamp
        result["timestamp"] = datetime.now().isoformat()
        return result

    def summary(self) -> str:
        """Generate human-readable summary"""
        duration_min = (self.total_duration_ms / 1000 / 60) if self.total_duration_ms else 0

        return f"""
=== Pipeline Execution Summary ===
Pipeline ID: {self.pipeline_id}
Spec: {self.spec_name}
Status: {self.overall_status.upper()}
Progress: {self.overall_progress:.1%}
Duration: {duration_min:.1f} minutes

Phase Status:
{self._phase_summary()}

Pattern Metrics:
- Patterns Matched: {self.patterns_matched}
- Pattern Reuse Rate: {self.pattern_reuse_rate:.1%}
- New Patterns Learned: {self.new_patterns_learned}

Quality Metrics:
- Test Coverage: {self.test_coverage:.1%}
- Code Quality: {self.code_quality_score:.2f}/1.0
- Acceptance Criteria: {self.acceptance_criteria_met}/{self.acceptance_criteria_total}

Performance:
- Peak Memory: {self.peak_memory_mb:.1f} MB
- Peak CPU: {self.peak_cpu_percent:.1f}%
- Neo4j Avg Query: {self.neo4j_avg_query_ms:.1f}ms
- Qdrant Avg Query: {self.qdrant_avg_query_ms:.1f}ms

Reliability:
- Total Errors: {self.total_errors}
- Recovered: {self.recovered_errors}
- Critical: {self.critical_errors}
- Recovery Rate: {self.recovery_success_rate:.1%}
"""

    def _phase_summary(self) -> str:
        lines = []
        for phase_name, phase in self.phases.items():
            status_icon = {
                PhaseStatus.COMPLETED: "✅",
                PhaseStatus.FAILED: "❌",
                PhaseStatus.IN_PROGRESS: "🔄",
                PhaseStatus.PENDING: "⏳",
                PhaseStatus.RETRYING: "🔁"
            }.get(phase.status, "❓")

            duration = f"{phase.duration_ms}ms" if phase.duration_ms else "---"
            checkpoint_info = f"{phase.checkpoints_completed}/{phase.checkpoints_total}"

            lines.append(
                f"  {status_icon} {phase_name:20} | {checkpoint_info:5} | {duration:8}"
            )

        return "\n".join(lines)


class MetricsCollector:
    """Real-time metrics collection during pipeline execution"""

    def __init__(self, pipeline_id: str, spec_name: str):
        self.metrics = PipelineMetrics(pipeline_id, spec_name)
        self.metrics.initialize_phases()
        self.resource_samples = []
        self._monitoring = False

    async def start_monitoring(self):
        """Start background resource monitoring"""
        self._monitoring = True
        asyncio.create_task(self._monitor_resources())

    async def _monitor_resources(self):
        """Monitor CPU and memory usage"""
        while self._monitoring:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()

            self.resource_samples.append({
                "timestamp": time.time(),
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent
            })

            # Update peaks
            if memory_mb > self.metrics.peak_memory_mb:
                self.metrics.peak_memory_mb = memory_mb
            if cpu_percent > self.metrics.peak_cpu_percent:
                self.metrics.peak_cpu_percent = cpu_percent

            await asyncio.sleep(1)  # Sample every second

    def stop_monitoring(self):
        """Stop resource monitoring and calculate averages"""
        self._monitoring = False

        if self.resource_samples:
            avg_memory = sum(s["memory_mb"] for s in self.resource_samples) / len(self.resource_samples)
            avg_cpu = sum(s["cpu_percent"] for s in self.resource_samples) / len(self.resource_samples)

            self.metrics.avg_memory_mb = avg_memory
            self.metrics.avg_cpu_percent = avg_cpu

    def start_phase(self, phase_name: str):
        """Mark phase as started"""
        if phase_name in self.metrics.phases:
            self.metrics.phases[phase_name].start()
            # Removed redundant "Phase Started" message - phase info printed by phase methods

    def complete_phase(self, phase_name: str):
        """Mark phase as completed"""
        if phase_name in self.metrics.phases:
            phase = self.metrics.phases[phase_name]
            phase.complete()
            print(f"✅ Phase Completed: {phase_name} ({phase.duration_ms}ms)")
            self.metrics.update_progress()

    def add_checkpoint(self, phase_name: str, checkpoint_name: str, metrics: Dict[str, Any] = None):
        """Add checkpoint completion"""
        if phase_name in self.metrics.phases:
            phase = self.metrics.phases[phase_name]
            phase.add_checkpoint()

            if metrics:
                phase.custom_metrics.update(metrics)

            self.metrics.update_progress()
            print(f"  ✓ Checkpoint: {checkpoint_name} ({phase.checkpoints_completed}/{phase.checkpoints_total})")

    def record_error(self, phase_name: str, error: Dict[str, Any], critical: bool = False):
        """Record an error during execution"""
        self.metrics.total_errors += 1
        if critical:
            self.metrics.critical_errors += 1

        if phase_name in self.metrics.phases:
            self.metrics.phases[phase_name].fail(error)

    def record_recovery(self, phase_name: str):
        """Record successful error recovery"""
        self.metrics.recovered_errors += 1
        if phase_name in self.metrics.phases:
            self.metrics.phases[phase_name].status = PhaseStatus.COMPLETED

    def update_pattern_metrics(self, patterns_matched: int, reuse_rate: float, new_patterns: int = 0):
        """Update Pattern Bank metrics"""
        self.metrics.patterns_matched = patterns_matched
        self.metrics.pattern_reuse_rate = reuse_rate
        self.metrics.new_patterns_learned = new_patterns

    def update_quality_metrics(self, coverage: float, quality_score: float,
                              criteria_met: int, criteria_total: int):
        """Update code quality metrics"""
        self.metrics.test_coverage = coverage
        self.metrics.code_quality_score = quality_score
        self.metrics.acceptance_criteria_met = criteria_met
        self.metrics.acceptance_criteria_total = criteria_total

    def update_database_metrics(self, db_type: str, query_count: int, avg_time_ms: float):
        """Update database query metrics"""
        if db_type == "neo4j":
            self.metrics.neo4j_queries = query_count
            self.metrics.neo4j_avg_query_ms = avg_time_ms
        elif db_type == "qdrant":
            self.metrics.qdrant_queries = query_count
            self.metrics.qdrant_avg_query_ms = avg_time_ms

    def finalize(self):
        """Finalize metrics collection"""
        self.stop_monitoring()
        self.metrics.complete_pipeline()
        return self.metrics

    def save_metrics(self, filepath: str):
        """Save metrics to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.metrics.to_dict(), f, indent=2, default=str)
        print(f"📊 Metrics saved to: {filepath}")

    def print_summary(self):
        """Print metrics summary"""
        print(self.metrics.summary())


# Example validation gates
class ValidationGates:
    """Validation checks at different pipeline phases"""

    @staticmethod
    def validate_spec_ingestion(metrics: PhaseMetrics) -> bool:
        """Validate spec ingestion phase"""
        required = ["spec_format", "required_sections", "parseable"]
        return all(metrics.custom_metrics.get(k, False) for k in required)

    @staticmethod
    def validate_dag_construction(metrics: PhaseMetrics) -> bool:
        """Validate DAG construction"""
        dag_metrics = metrics.custom_metrics
        return all([
            dag_metrics.get("is_acyclic", False),
            dag_metrics.get("all_nodes_reachable", False),
            dag_metrics.get("no_orphaned_nodes", False),
            dag_metrics.get("naming_valid", False)
        ])

    @staticmethod
    def validate_deployment(metrics: PhaseMetrics) -> bool:
        """Validate deployment phase"""
        return all([
            metrics.custom_metrics.get("health_checks_pass", False),
            metrics.custom_metrics.get("smoke_tests_pass", False),
            metrics.custom_metrics.get("no_critical_errors", True)
        ])