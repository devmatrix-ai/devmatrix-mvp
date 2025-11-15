"""
E2E Metrics Collector

Collects and tracks E2E validation metrics:
- Build success rates
- Unit test pass rates
- E2E test pass rates (PRIMARY METRIC)
- Production readiness scores
- Historical precision tracking
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

from ..validation.e2e_production_validator import ValidationReport, ValidationLayer, ValidationStatus


@dataclass
class E2EMetrics:
    """E2E validation metrics for a single run"""
    spec_name: str
    timestamp: str
    build_success: bool
    unit_tests_passed: bool
    unit_tests_coverage: float
    e2e_tests_passed: int
    e2e_tests_total: int
    e2e_precision: float  # PRIMARY METRIC: passed / total
    production_ready: bool
    total_duration_seconds: float
    overall_success: bool


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across multiple runs"""
    total_runs: int
    successful_builds: int
    successful_unit_tests: int
    successful_e2e_tests: int
    production_ready_count: int

    # Average metrics
    avg_e2e_precision: float
    avg_unit_test_coverage: float
    avg_duration_seconds: float

    # Per-spec breakdown
    spec_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Historical trend
    precision_trend: List[float] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class E2EMetricsCollector:
    """
    E2E Metrics Collector

    Collects, stores, and analyzes E2E validation metrics.
    Primary metric: E2E precision (% of golden tests passed)
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize E2E Metrics Collector.

        Args:
            storage_path: Path to store metrics JSON files
        """
        self.storage_path = storage_path or Path(__file__).parent.parent.parent.parent / "metrics" / "e2e"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.storage_path / "e2e_metrics.jsonl"
        self.summary_file = self.storage_path / "e2e_summary.json"

    def collect_from_report(self, report: ValidationReport) -> E2EMetrics:
        """
        Collect metrics from a validation report.

        Args:
            report: ValidationReport from E2EProductionValidator

        Returns:
            E2EMetrics extracted from report
        """
        # Extract build success
        build_layer = report.layers.get(ValidationLayer.BUILD)
        build_success = build_layer.status == ValidationStatus.PASSED if build_layer else False

        # Extract unit test metrics
        unit_layer = report.layers.get(ValidationLayer.UNIT_TESTS)
        unit_tests_passed = unit_layer.status == ValidationStatus.PASSED if unit_layer else False
        unit_tests_coverage = 0.0
        if unit_layer and "average_coverage" in unit_layer.details:
            unit_tests_coverage = unit_layer.details["average_coverage"]

        # Extract E2E test metrics (PRIMARY METRIC)
        e2e_layer = report.layers.get(ValidationLayer.E2E_TESTS)
        e2e_tests_passed = 0
        e2e_tests_total = 0
        e2e_precision = 0.0

        if e2e_layer:
            e2e_tests_passed = e2e_layer.details.get("passed", 0)
            e2e_tests_total = e2e_layer.details.get("total", 0)
            if e2e_tests_total > 0:
                e2e_precision = e2e_tests_passed / e2e_tests_total

        # Extract production ready
        prod_layer = report.layers.get(ValidationLayer.PRODUCTION_READY)
        production_ready = prod_layer.status == ValidationStatus.PASSED if prod_layer else False

        # Overall success
        overall_success = report.overall_status == ValidationStatus.PASSED

        metrics = E2EMetrics(
            spec_name=report.spec_name,
            timestamp=report.timestamp,
            build_success=build_success,
            unit_tests_passed=unit_tests_passed,
            unit_tests_coverage=unit_tests_coverage,
            e2e_tests_passed=e2e_tests_passed,
            e2e_tests_total=e2e_tests_total,
            e2e_precision=e2e_precision,
            production_ready=production_ready,
            total_duration_seconds=report.total_duration_seconds,
            overall_success=overall_success,
        )

        # Store metrics
        self._store_metrics(metrics)

        logger.info(
            f"Collected metrics for {report.spec_name}: "
            f"E2E Precision: {e2e_precision:.2%}, "
            f"Overall: {'SUCCESS' if overall_success else 'FAILED'}"
        )

        return metrics

    def _store_metrics(self, metrics: E2EMetrics):
        """Store metrics to JSONL file (append-only)"""
        try:
            with open(self.metrics_file, "a") as f:
                f.write(json.dumps(asdict(metrics)) + "\n")

            logger.debug(f"Stored metrics to {self.metrics_file}")
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")

    def load_all_metrics(self) -> List[E2EMetrics]:
        """Load all historical metrics from JSONL file"""
        metrics_list = []

        if not self.metrics_file.exists():
            return metrics_list

        try:
            with open(self.metrics_file) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        metrics_list.append(E2EMetrics(**data))

            logger.debug(f"Loaded {len(metrics_list)} metrics from {self.metrics_file}")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")

        return metrics_list

    def aggregate_metrics(
        self,
        spec_name: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> AggregatedMetrics:
        """
        Aggregate metrics across multiple runs.

        Args:
            spec_name: Filter by specific spec (None = all specs)
            since: Only include metrics after this datetime

        Returns:
            AggregatedMetrics with summary statistics
        """
        all_metrics = self.load_all_metrics()

        # Filter by spec and time
        if spec_name:
            all_metrics = [m for m in all_metrics if m.spec_name == spec_name]

        if since:
            all_metrics = [
                m for m in all_metrics
                if datetime.fromisoformat(m.timestamp) >= since
            ]

        if not all_metrics:
            return AggregatedMetrics(
                total_runs=0,
                successful_builds=0,
                successful_unit_tests=0,
                successful_e2e_tests=0,
                production_ready_count=0,
                avg_e2e_precision=0.0,
                avg_unit_test_coverage=0.0,
                avg_duration_seconds=0.0,
                timestamp=datetime.utcnow().isoformat(),
            )

        # Calculate aggregates
        total_runs = len(all_metrics)
        successful_builds = sum(1 for m in all_metrics if m.build_success)
        successful_unit_tests = sum(1 for m in all_metrics if m.unit_tests_passed)
        successful_e2e_tests = sum(1 for m in all_metrics if m.e2e_tests_passed == m.e2e_tests_total and m.e2e_tests_total > 0)
        production_ready_count = sum(1 for m in all_metrics if m.production_ready)

        # Average metrics
        avg_e2e_precision = sum(m.e2e_precision for m in all_metrics) / total_runs
        avg_unit_test_coverage = sum(m.unit_tests_coverage for m in all_metrics) / total_runs
        avg_duration_seconds = sum(m.total_duration_seconds for m in all_metrics) / total_runs

        # Per-spec breakdown
        spec_metrics = {}
        spec_names = set(m.spec_name for m in all_metrics)

        for spec in spec_names:
            spec_runs = [m for m in all_metrics if m.spec_name == spec]
            spec_metrics[spec] = {
                "runs": len(spec_runs),
                "avg_precision": sum(m.e2e_precision for m in spec_runs) / len(spec_runs),
                "success_rate": sum(1 for m in spec_runs if m.overall_success) / len(spec_runs),
                "avg_duration": sum(m.total_duration_seconds for m in spec_runs) / len(spec_runs),
            }

        # Precision trend (last 10 runs)
        precision_trend = [m.e2e_precision for m in all_metrics[-10:]]

        aggregated = AggregatedMetrics(
            total_runs=total_runs,
            successful_builds=successful_builds,
            successful_unit_tests=successful_unit_tests,
            successful_e2e_tests=successful_e2e_tests,
            production_ready_count=production_ready_count,
            avg_e2e_precision=avg_e2e_precision,
            avg_unit_test_coverage=avg_unit_test_coverage,
            avg_duration_seconds=avg_duration_seconds,
            spec_metrics=spec_metrics,
            precision_trend=precision_trend,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Save summary
        self._save_summary(aggregated)

        return aggregated

    def _save_summary(self, aggregated: AggregatedMetrics):
        """Save aggregated summary to JSON file"""
        try:
            with open(self.summary_file, "w") as f:
                json.dump(aggregated.to_dict(), f, indent=2)

            logger.debug(f"Saved summary to {self.summary_file}")
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")

    def get_precision_target_status(self, target: float = 0.88) -> Dict[str, Any]:
        """
        Check if E2E precision meets target.

        Args:
            target: Target precision (default 0.88 = 88%)

        Returns:
            Dictionary with status and details
        """
        aggregated = self.aggregate_metrics()

        meets_target = aggregated.avg_e2e_precision >= target

        return {
            "meets_target": meets_target,
            "current_precision": aggregated.avg_e2e_precision,
            "target_precision": target,
            "gap": target - aggregated.avg_e2e_precision if not meets_target else 0.0,
            "total_runs": aggregated.total_runs,
            "precision_trend": aggregated.precision_trend,
        }

    def generate_report(self) -> str:
        """
        Generate human-readable metrics report.

        Returns:
            Formatted string report
        """
        aggregated = self.aggregate_metrics()
        target_status = self.get_precision_target_status()

        report_lines = [
            "=" * 60,
            "E2E VALIDATION METRICS REPORT",
            "=" * 60,
            "",
            f"📊 Total Runs: {aggregated.total_runs}",
            f"⏱️  Avg Duration: {aggregated.avg_duration_seconds:.2f}s",
            "",
            "🎯 PRIMARY METRIC: E2E Precision",
            f"   Current: {aggregated.avg_e2e_precision:.2%}",
            f"   Target:  88%",
            f"   Status:  {'✅ MEETS TARGET' if target_status['meets_target'] else '❌ BELOW TARGET'}",
            "",
            "📈 Layer Success Rates:",
            f"   Build:        {aggregated.successful_builds}/{aggregated.total_runs} ({aggregated.successful_builds/aggregated.total_runs:.1%})",
            f"   Unit Tests:   {aggregated.successful_unit_tests}/{aggregated.total_runs} ({aggregated.successful_unit_tests/aggregated.total_runs:.1%})",
            f"   E2E Tests:    {aggregated.successful_e2e_tests}/{aggregated.total_runs} ({aggregated.successful_e2e_tests/aggregated.total_runs:.1%})",
            f"   Production:   {aggregated.production_ready_count}/{aggregated.total_runs} ({aggregated.production_ready_count/aggregated.total_runs:.1%})",
            "",
            f"📦 Unit Test Coverage: {aggregated.avg_unit_test_coverage:.2%}",
            "",
            "🔍 Per-Spec Breakdown:",
        ]

        for spec, metrics in aggregated.spec_metrics.items():
            report_lines.append(
                f"   {spec:30s} | "
                f"Precision: {metrics['avg_precision']:5.1%} | "
                f"Success: {metrics['success_rate']:5.1%} | "
                f"Runs: {metrics['runs']:3d}"
            )

        report_lines.extend([
            "",
            "📉 Precision Trend (last 10 runs):",
            "   " + " → ".join(f"{p:.1%}" for p in aggregated.precision_trend),
            "",
            "=" * 60,
        ])

        return "\n".join(report_lines)

    def export_metrics(self, output_path: Path, format: str = "json"):
        """
        Export metrics to file.

        Args:
            output_path: Path to export file
            format: Export format ("json" or "csv")
        """
        all_metrics = self.load_all_metrics()

        if format == "json":
            with open(output_path, "w") as f:
                json.dump([asdict(m) for m in all_metrics], f, indent=2)

        elif format == "csv":
            import csv
            with open(output_path, "w", newline="") as f:
                if all_metrics:
                    writer = csv.DictWriter(f, fieldnames=asdict(all_metrics[0]).keys())
                    writer.writeheader()
                    for m in all_metrics:
                        writer.writerow(asdict(m))

        logger.info(f"Exported {len(all_metrics)} metrics to {output_path}")
