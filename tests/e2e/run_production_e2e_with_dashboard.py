#!/usr/bin/env python3
"""
Production E2E Test Runner with Real-Time Metrics Dashboard

Executes complete E2E pipeline with Phase 6.5 (Code Repair) on real specs:
- simple_task_api.md
- ecommerce_api_simple.md

Features:
- Real-time metrics dashboard
- Granular phase-by-phase progress tracking
- Precision and success metrics per phase
- Final summary report
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.real_e2e_full_pipeline import RealE2ETest


@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""
    name: str
    status: str = "pending"  # pending, in_progress, completed, failed
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    precision: float = 0.0
    success: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        return self.duration_ms / 1000.0 if self.duration_ms > 0 else 0.0


@dataclass
class SpecExecutionMetrics:
    """Complete metrics for a spec execution."""
    spec_name: str
    spec_path: str
    overall_status: str = "pending"
    start_time: float = 0.0
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    phases: List[PhaseMetrics] = field(default_factory=list)

    # Phase 6.5 specific metrics
    repair_applied: bool = False
    repair_iterations: int = 0
    repair_improvement: float = 0.0
    initial_compliance: float = 0.0
    final_compliance: float = 0.0

    # Overall success metrics
    overall_precision: float = 0.0
    overall_success: bool = False


class ProductionDashboard:
    """Real-time metrics dashboard for production E2E testing."""

    def __init__(self):
        self.specs_metrics: List[SpecExecutionMetrics] = []
        self.start_time = time.time()

    def clear_screen(self):
        """Clear terminal screen."""
        print("\033[2J\033[H", end="")

    def print_header(self):
        """Print dashboard header."""
        elapsed = time.time() - self.start_time
        print("=" * 100)
        print(f"🚀 PRODUCTION E2E TEST - CodeRepairAgent Integration")
        print(f"⏱️  Elapsed Time: {elapsed:.1f}s | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print()

    def print_spec_metrics(self, metrics: SpecExecutionMetrics):
        """Print metrics for a single spec."""
        status_icon = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(metrics.overall_status, "❓")

        print(f"\n{status_icon} {metrics.spec_name}")
        print(f"   Path: {metrics.spec_path}")
        print(f"   Status: {metrics.overall_status.upper()}")

        if metrics.total_duration_ms > 0:
            print(f"   Duration: {metrics.total_duration_ms/1000:.2f}s")

        if metrics.overall_precision > 0:
            print(f"   Overall Precision: {metrics.overall_precision:.1%}")

        if metrics.repair_applied:
            print(f"   🔧 Repair Applied: {metrics.repair_iterations} iterations")
            print(f"   📈 Compliance: {metrics.initial_compliance:.1%} → {metrics.final_compliance:.1%} (+{metrics.repair_improvement:.1%})")

        # Print phase breakdown
        if metrics.phases:
            print("\n   📊 Phase Breakdown:")
            for phase in metrics.phases:
                phase_icon = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "failed": "❌"
                }.get(phase.status, "❓")

                phase_line = f"      {phase_icon} {phase.name}"

                if phase.status == "completed":
                    phase_line += f" - {phase.duration_s:.2f}s"
                    if phase.precision > 0:
                        phase_line += f" - Precision: {phase.precision:.1%}"
                    if phase.success:
                        phase_line += " ✓"
                elif phase.status == "in_progress":
                    elapsed = time.time() - phase.start_time
                    phase_line += f" - Running ({elapsed:.1f}s)..."
                elif phase.status == "failed":
                    phase_line += " - FAILED"

                print(phase_line)

        print("-" * 100)

    def print_summary(self):
        """Print final summary."""
        print("\n")
        print("=" * 100)
        print("📊 FINAL SUMMARY")
        print("=" * 100)

        total_specs = len(self.specs_metrics)
        completed_specs = sum(1 for m in self.specs_metrics if m.overall_status == "completed")
        failed_specs = sum(1 for m in self.specs_metrics if m.overall_status == "failed")

        print(f"\n✅ Completed: {completed_specs}/{total_specs}")
        print(f"❌ Failed: {failed_specs}/{total_specs}")

        if completed_specs > 0:
            avg_precision = sum(m.overall_precision for m in self.specs_metrics if m.overall_status == "completed") / completed_specs
            print(f"📈 Average Precision: {avg_precision:.1%}")

            total_duration = sum(m.total_duration_ms for m in self.specs_metrics) / 1000.0
            print(f"⏱️  Total Duration: {total_duration:.2f}s")

            # Phase 6.5 Summary
            specs_with_repair = [m for m in self.specs_metrics if m.repair_applied]
            if specs_with_repair:
                print(f"\n🔧 Code Repair Summary:")
                print(f"   Specs with repair: {len(specs_with_repair)}")
                avg_improvement = sum(m.repair_improvement for m in specs_with_repair) / len(specs_with_repair)
                avg_iterations = sum(m.repair_iterations for m in specs_with_repair) / len(specs_with_repair)
                print(f"   Average improvement: {avg_improvement:.1%}")
                print(f"   Average iterations: {avg_iterations:.1f}")

        print("=" * 100)

    def update(self):
        """Update and redraw the dashboard."""
        self.clear_screen()
        self.print_header()

        for metrics in self.specs_metrics:
            self.print_spec_metrics(metrics)

        if all(m.overall_status in ["completed", "failed"] for m in self.specs_metrics):
            self.print_summary()


async def execute_spec_with_metrics(
    spec_path: str,
    spec_name: str,
    dashboard: ProductionDashboard
) -> SpecExecutionMetrics:
    """Execute a spec and collect detailed metrics."""

    metrics = SpecExecutionMetrics(
        spec_name=spec_name,
        spec_path=spec_path
    )
    dashboard.specs_metrics.append(metrics)

    # Initialize phases
    phase_names = [
        "Phase 1: Spec Ingestion",
        "Phase 2: Requirements Analysis",
        "Phase 3: Multi-Pass Planning",
        "Phase 4: Atomization",
        "Phase 5: DAG Construction",
        "Phase 6: Code Generation",
        "Phase 6.5: Code Repair",  # NEW
        "Phase 7: Validation"
    ]

    metrics.phases = [PhaseMetrics(name=name) for name in phase_names]

    try:
        metrics.overall_status = "in_progress"
        metrics.start_time = time.time()
        dashboard.update()

        # Create test instance with spec_path
        test = RealE2ETest(spec_file=spec_path)

        # Execute pipeline
        print(f"\n   🚀 Starting pipeline execution for {spec_name}...")

        # Run the complete pipeline
        await test.run()

        # Extract metrics from test instance
        result = {
            "total_duration_ms": (time.time() - metrics.start_time) * 1000,
            "overall_precision": test.precision.calculate_overall_precision() if hasattr(test, 'precision') else 0,
            "overall_success": True,  # If we got here, it succeeded
            "repair_applied": hasattr(test, 'repair_applied') and test.repair_applied,
            "repair_iterations": getattr(test, 'repair_iterations', 0),
            "repair_improvement": getattr(test, 'repair_improvement', 0),
            "initial_compliance": getattr(test, 'initial_compliance', 0),
            "final_compliance": getattr(test, 'final_compliance', 0),
            "phases": []  # We'll extract phase info from metrics_collector if available
        }

        # Extract metrics from result
        metrics.total_duration_ms = result.get("total_duration_ms", 0)
        metrics.overall_precision = result.get("overall_precision", 0)
        metrics.overall_success = result.get("overall_success", False)

        # Phase 6.5 metrics
        metrics.repair_applied = result.get("repair_applied", False)
        metrics.repair_iterations = result.get("repair_iterations", 0)
        metrics.repair_improvement = result.get("repair_improvement", 0)
        metrics.initial_compliance = result.get("initial_compliance", 0)
        metrics.final_compliance = result.get("final_compliance", 0)

        # Update phase metrics
        phase_results = result.get("phases", [])
        for i, phase_result in enumerate(phase_results):
            if i < len(metrics.phases):
                phase_metrics = metrics.phases[i]
                phase_metrics.status = phase_result.get("status", "completed")
                phase_metrics.duration_ms = phase_result.get("duration_ms", 0)
                phase_metrics.precision = phase_result.get("precision", 0)
                phase_metrics.success = phase_result.get("success", True)
                phase_metrics.details = phase_result.get("details", {})

        metrics.overall_status = "completed" if metrics.overall_success else "failed"

    except Exception as e:
        metrics.overall_status = "failed"
        print(f"\n❌ Error executing {spec_name}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        metrics.end_time = time.time()
        if metrics.start_time > 0:
            metrics.total_duration_ms = (metrics.end_time - metrics.start_time) * 1000.0
        dashboard.update()

    return metrics


async def run_production_e2e():
    """Run production E2E tests with real-time dashboard."""

    print("🚀 Starting Production E2E Tests with Phase 6.5 (Code Repair)")
    print("=" * 100)
    print()

    dashboard = ProductionDashboard()

    # Specs to test
    specs = [
        {
            "name": "Simple Task API",
            "path": "tests/e2e/test_specs/simple_task_api.md"
        },
        {
            "name": "E-Commerce API",
            "path": "tests/e2e/test_specs/ecommerce_api_simple.md"
        }
    ]

    # Execute specs sequentially with dashboard updates
    for spec in specs:
        print(f"\n📋 Executing: {spec['name']}")
        await execute_spec_with_metrics(
            spec_path=spec["path"],
            spec_name=spec["name"],
            dashboard=dashboard
        )

    # Final dashboard update
    dashboard.update()

    print("\n✅ Production E2E tests completed!")
    return dashboard.specs_metrics


if __name__ == "__main__":
    print("=" * 100)
    print("🚀 PRODUCTION E2E TEST RUNNER - CodeRepairAgent Integration")
    print("=" * 100)
    print()
    print("Testing specs:")
    print("  1. Simple Task API (simple_task_api.md)")
    print("  2. E-Commerce API (ecommerce_api_simple.md)")
    print()
    print("With Phase 6.5 Code Repair enabled for automatic compliance improvement")
    print()
    print("=" * 100)
    print()

    # Run tests
    asyncio.run(run_production_e2e())
