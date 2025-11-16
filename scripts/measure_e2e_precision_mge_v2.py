#!/usr/bin/env python3
"""
E2E Precision Measurement Script - MGE V2 Real Integration

Standalone script for measuring code generation precision using REAL MGE V2 pipeline.

NO MOCKS - Uses real LLMs, database, code generation, and infrastructure.

Usage:
    # Single measurement with discovery document
    python scripts/measure_e2e_precision_mge_v2.py --discovery discovery_docs/ecommerce.md

    # With auto-correction
    python scripts/measure_e2e_precision_mge_v2.py --discovery discovery_docs/ecommerce.md --auto-correct --target 0.95

    # Custom output directory
    python scripts/measure_e2e_precision_mge_v2.py --discovery discovery_docs/ecommerce.md --output /tmp/precision_results/

Metrics Reported:
    - MasterPlan ID and execution metrics
    - Code generation cost (USD)
    - Initial and final precision
    - Number of correction iterations
    - Total execution time
    - Workspace path with generated code
    - Tests passed/failed by category (must/should)

Requirements:
    - PostgreSQL database running (DevMatrix DB)
    - ANTHROPIC_API_KEY environment variable set
    - MGE V2 services configured
"""

import argparse
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.precision.e2e.precision_pipeline_mge_v2 import (
    E2EPrecisionPipelineMGE_V2,
    MGE_V2_PipelineResult,
)


class E2EPrecisionMeasurementMGE_V2:
    """E2E precision measurement orchestrator with MGE V2 integration."""

    def __init__(
        self,
        anthropic_api_key: str = None,
        auto_correct: bool = False,
        target_precision: float = 0.92,
        max_iterations: int = 5,
    ):
        """
        Initialize measurement tool with MGE V2.

        Args:
            anthropic_api_key: Claude API key
            auto_correct: Enable auto-correction
            target_precision: Target precision (default: 0.92)
            max_iterations: Max correction iterations (default: 5)
        """
        self.pipeline = E2EPrecisionPipelineMGE_V2(
            anthropic_api_key=anthropic_api_key,
            auto_correct=auto_correct,
            target_precision=target_precision,
            max_correction_iterations=max_iterations,
        )

    async def measure_single(
        self, discovery_file: Path, output_dir: Path, user_id: str = "precision_test"
    ) -> Dict[str, Any]:
        """
        Measure precision for single project using real MGE V2.

        Args:
            discovery_file: Discovery document file
            output_dir: Output directory for results
            user_id: User identifier (default: "precision_test")

        Returns:
            Dictionary with measurement results
        """
        print("\n" + "=" * 80)
        print(f"📊 MEASURING PRECISION WITH MGE V2: {discovery_file.name}")
        print("=" * 80)

        # Read discovery document
        discovery_doc = discovery_file.read_text()

        # Execute pipeline with real MGE V2
        result = await self.pipeline.execute_from_discovery(
            discovery_doc=discovery_doc,
            user_id=user_id,
            output_dir=output_dir,
        )

        # Create measurement summary
        summary = {
            "discovery_file": str(discovery_file),
            "discovery_id": result.discovery_id,
            "masterplan_id": result.masterplan_id,
            "timestamp": result.timestamp.isoformat(),
            "project": {
                "project_name": result.project_name,
                "module_name": result.module_name,
            },
            "mge_v2_execution": {
                "total_tasks": result.total_tasks,
                "total_atoms": result.total_atoms,
                "workspace_path": result.workspace_path,
                "code_generation_cost_usd": result.code_generation_cost_usd,
                "code_generation_time_seconds": result.code_generation_time,
            },
            "precision": {
                "initial": result.initial_precision,
                "final": result.final_precision,
                "target": result.target_precision,
                "target_reached": result.precision_gate_passed,
            },
            "tests": {
                "total": result.total_tests,
                "passed": result.passed_tests,
                "failed": result.failed_tests,
                "must_passed": result.must_gate_passed,
                "should_passed": result.should_gate_passed,
            },
            "auto_correction": {
                "applied": result.auto_correction_applied,
                "iterations": result.correction_iterations,
                "improvement": result.total_improvement,
            },
            "performance": {
                "total_time_seconds": result.total_time,
            },
            "artifacts": {
                "workspace_path": result.workspace_path,
                "test_file": result.test_file,
            },
        }

        return summary

    def save_results(self, results: Dict[str, Any], output_file: Path) -> None:
        """
        Save measurement results to JSON file.

        Args:
            results: Measurement results dictionary
            output_file: Output JSON file
        """
        output_file.write_text(json.dumps(results, indent=2))
        print(f"\n💾 Results saved: {output_file}")

    def print_summary(self, results: Dict[str, Any]) -> None:
        """
        Print measurement summary.

        Args:
            results: Measurement results
        """
        print("\n" + "=" * 80)
        print("📊 MEASUREMENT SUMMARY (MGE V2)")
        print("=" * 80)

        project = results.get("project", {})
        mge_v2 = results.get("mge_v2_execution", {})
        precision = results.get("precision", {})
        tests = results.get("tests", {})
        auto_corr = results.get("auto_correction", {})
        perf = results.get("performance", {})

        print(f"\n📦 Project: {project.get('project_name', 'Unknown')}")
        print(f"📝 Module: {project.get('module_name', 'Unknown')}")
        print(f"🆔 MasterPlan ID: {results.get('masterplan_id', 'Unknown')}")

        print(f"\n🏗️  MGE V2 Execution:")
        print(f"  ✓ Tasks: {mge_v2.get('total_tasks', 0)}")
        print(f"  ✓ Atoms: {mge_v2.get('total_atoms', 0)}")
        print(f"  💰 Cost: ${mge_v2.get('code_generation_cost_usd', 0):.4f}")
        print(f"  ⏱️  Time: {mge_v2.get('code_generation_time_seconds', 0):.2f}s")
        print(f"  📁 Workspace: {mge_v2.get('workspace_path', 'N/A')}")

        print(f"\n🎯 Precision:")
        print(f"  Initial:  {precision.get('initial', 0):.1%}")
        print(f"  Final:    {precision.get('final', 0):.1%}")
        print(f"  Target:   {precision.get('target', 0):.1%}")
        target_icon = "✅" if precision.get("target_reached", False) else "❌"
        print(f"  {target_icon} Target Reached: {precision.get('target_reached', False)}")

        print(f"\n🧪 Tests:")
        print(f"  Total:  {tests.get('total', 0)}")
        print(f"  Passed: {tests.get('passed', 0)}")
        print(f"  Failed: {tests.get('failed', 0)}")
        must_icon = "✅" if tests.get("must_passed", False) else "❌"
        should_icon = "✅" if tests.get("should_passed", False) else "❌"
        print(f"  {must_icon} Must Gate")
        print(f"  {should_icon} Should Gate")

        if auto_corr.get("applied", False):
            print(f"\n🔧 Auto-Correction:")
            print(f"  Iterations: {auto_corr.get('iterations', 0)}")
            print(f"  Improvement: {auto_corr.get('improvement', 0):+.1%}")

        print(f"\n⏱️  Performance:")
        print(f"  Total Time: {perf.get('total_time_seconds', 0):.2f}s")

        print("\n" + "=" * 80)


async def main_async():
    """Main entry point for E2E precision measurement with MGE V2."""
    parser = argparse.ArgumentParser(
        description="E2E Precision Measurement Tool with MGE V2 (Real LLMs & Infrastructure)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input
    parser.add_argument(
        "--discovery",
        type=Path,
        required=True,
        help="Discovery document file to measure",
    )

    # Configuration
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/precision_measurements_mge_v2"),
        help="Output directory for results (default: /tmp/precision_measurements_mge_v2)",
    )
    parser.add_argument(
        "--auto-correct",
        action="store_true",
        help="Enable auto-correction loop",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=0.92,
        help="Target precision (default: 0.92 = 92%%)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum auto-correction iterations (default: 5)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API key (default: from ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="precision_test",
        help="User ID for tracking (default: precision_test)",
    )

    args = parser.parse_args()

    # Validate discovery file exists
    if not args.discovery.exists():
        print(f"❌ Discovery file not found: {args.discovery}")
        sys.exit(1)

    # Initialize measurement tool
    measurement = E2EPrecisionMeasurementMGE_V2(
        anthropic_api_key=args.api_key,
        auto_correct=args.auto_correct,
        target_precision=args.target,
        max_iterations=args.max_iterations,
    )

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Execute measurement with real MGE V2
    results = await measurement.measure_single(
        discovery_file=args.discovery,
        output_dir=args.output,
        user_id=args.user_id,
    )

    # Save and print results
    module_name = results.get("project", {}).get("module_name", "unknown")
    results_file = args.output / f"{module_name}_mge_v2_precision_results.json"
    measurement.save_results(results, results_file)
    measurement.print_summary(results)

    print(f"\n✅ Measurement complete!")
    print(f"📁 Results: {args.output}")
    print(f"📂 Workspace: {results['artifacts']['workspace_path']}")


def main():
    """Sync wrapper for async main."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
