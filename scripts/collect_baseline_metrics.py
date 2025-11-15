"""
Baseline Metrics Collection for Cognitive Architecture MVP

Collects baseline metrics for tracking cognitive architecture performance:
- Precision % (E2E and Atomic)
- Pattern reuse rate
- Time per atom (CPIE inference time)
- Cost per atom (LLM API costs)

Usage:
    python scripts/collect_baseline_metrics.py --output metrics/baseline.json
"""

import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cognitive.config.settings import settings as cognitive_settings
settings = cognitive_settings


class BaselineMetricsCollector:
    """Collects and stores baseline metrics for cognitive architecture."""

    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            output_path: Path to save metrics JSON (default: metrics/baseline.json)
        """
        self.output_path = Path(output_path or "metrics/baseline.json")
        self.metrics: Dict[str, Any] = {}

    def collect_infrastructure_metrics(self) -> Dict[str, Any]:
        """
        Collect infrastructure availability metrics.

        Returns:
            Dictionary with infrastructure status
        """
        infra_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "neo4j": {
                "configured": bool(settings.neo4j_uri),
                "uri": settings.neo4j_uri,
                "expected_patterns": 30071
            },
            "qdrant": {
                "configured": bool(settings.qdrant_host),
                "host": f"{settings.qdrant_host}:{settings.qdrant_port}",
                "collection_patterns": settings.qdrant_collection_patterns,
                "collection_semantic": settings.qdrant_collection_semantic,
                "expected_patterns": 21624
            },
            "embeddings": {
                "model": settings.embedding_model,
                "dimension": settings.embedding_dimension
            }
        }

        # Test Neo4j connectivity
        try:
            from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient
            with Neo4jPatternClient() as client:
                client.connect()
                pattern_count = client.get_pattern_count()
                infra_metrics["neo4j"]["status"] = "connected"
                infra_metrics["neo4j"]["actual_patterns"] = pattern_count
        except Exception as e:
            infra_metrics["neo4j"]["status"] = f"error: {str(e)}"
            infra_metrics["neo4j"]["actual_patterns"] = 0

        # Test Qdrant connectivity
        try:
            from src.cognitive.infrastructure.qdrant_client import QdrantPatternClient
            with QdrantPatternClient() as client:
                client.connect()
                info = client.get_collection_info()
                infra_metrics["qdrant"]["status"] = "connected"
                infra_metrics["qdrant"]["actual_patterns"] = info["points_count"]
        except Exception as e:
            infra_metrics["qdrant"]["status"] = f"error: {str(e)}"
            infra_metrics["qdrant"]["actual_patterns"] = 0

        return infra_metrics

    def collect_target_metrics(self) -> Dict[str, Any]:
        """
        Collect target metrics from settings.

        Returns:
            Dictionary with precision and performance targets
        """
        return {
            "precision_targets": {
                "e2e_precision_mvp": settings.e2e_precision_target,
                "atomic_precision_mvp": settings.atomic_precision_target,
                "unit_test_coverage": settings.unit_test_coverage_target
            },
            "pattern_bank": {
                "similarity_threshold": settings.pattern_similarity_threshold,
                "reuse_target_mvp": settings.pattern_reuse_target,
                "precision_threshold": settings.cpie_precision_threshold
            },
            "performance_targets": {
                "cpie_max_inference_time_mvp": f"{settings.cpie_max_inference_time}s",
                "co_reasoning_enabled": settings.co_reasoning_enabled,
                "lrm_enabled": settings.lrm_enabled
            }
        }

    def collect_baseline_performance(self) -> Dict[str, Any]:
        """
        Collect baseline performance metrics (pre-implementation).

        Returns:
            Dictionary with baseline performance data
        """
        return {
            "current_precision": {
                "e2e_precision": 0.00,  # Not implemented yet
                "atomic_precision": 0.00,  # Not implemented yet
                "note": "Pre-implementation baseline - will be updated after Phase 1"
            },
            "current_performance": {
                "pattern_reuse_rate": 0.00,  # No patterns reused yet
                "avg_time_per_atom": 0.00,  # No atoms generated yet
                "avg_cost_per_atom": 0.00,  # No LLM calls yet
                "note": "Pre-implementation baseline"
            },
            "phase_0_completion": {
                "infrastructure_ready": True,
                "migrations_applied": True,
                "clients_implemented": True,
                "date": datetime.utcnow().isoformat()
            }
        }

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all baseline metrics.

        Returns:
            Complete metrics dictionary
        """
        print("📊 Collecting baseline metrics...")

        self.metrics = {
            "collection_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "phase": "Phase 0 Complete - Pre Phase 1",
                "version": "0.1.0",
                "collector": "BaselineMetricsCollector"
            },
            "infrastructure": self.collect_infrastructure_metrics(),
            "targets": self.collect_target_metrics(),
            "baseline": self.collect_baseline_performance()
        }

        return self.metrics

    def save_metrics(self) -> None:
        """Save metrics to JSON file."""
        # Create metrics directory if it doesn't exist
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save metrics
        with open(self.output_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

        print(f"✅ Metrics saved to {self.output_path}")

    def print_summary(self) -> None:
        """Print metrics summary to console."""
        print("\n" + "=" * 60)
        print("BASELINE METRICS SUMMARY")
        print("=" * 60)

        # Infrastructure
        print("\n📡 Infrastructure Status:")
        neo4j = self.metrics["infrastructure"]["neo4j"]
        print(f"  Neo4j: {neo4j['status']} ({neo4j.get('actual_patterns', 0)} patterns)")
        qdrant = self.metrics["infrastructure"]["qdrant"]
        print(f"  Qdrant: {qdrant['status']} ({qdrant.get('actual_patterns', 0)} patterns)")

        # Targets
        print("\n🎯 MVP Targets:")
        targets = self.metrics["targets"]["precision_targets"]
        print(f"  E2E Precision: {targets['e2e_precision_mvp']*100:.0f}%")
        print(f"  Atomic Precision: {targets['atomic_precision_mvp']*100:.0f}%")
        print(f"  Test Coverage: {targets['unit_test_coverage']*100:.0f}%")

        pattern_targets = self.metrics["targets"]["pattern_bank"]
        print(f"  Pattern Reuse: {pattern_targets['reuse_target_mvp']*100:.0f}%")
        print(f"  Similarity Threshold: {pattern_targets['similarity_threshold']*100:.0f}%")

        perf_targets = self.metrics["targets"]["performance_targets"]
        print(f"  CPIE Max Time: {perf_targets['cpie_max_inference_time_mvp']}")

        # Baseline
        print("\n📈 Current Baseline (Pre-Implementation):")
        baseline = self.metrics["baseline"]["current_precision"]
        print(f"  E2E Precision: {baseline['e2e_precision']*100:.1f}%")
        print(f"  Atomic Precision: {baseline['atomic_precision']*100:.1f}%")

        print("\n" + "=" * 60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Collect baseline metrics for Cognitive Architecture MVP"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="metrics/baseline.json",
        help="Output path for metrics JSON (default: metrics/baseline.json)"
    )
    parser.add_argument(
        "--silent",
        "-s",
        action="store_true",
        help="Suppress summary output"
    )

    args = parser.parse_args()

    # Collect metrics
    collector = BaselineMetricsCollector(output_path=args.output)
    collector.collect_all_metrics()
    collector.save_metrics()

    # Print summary
    if not args.silent:
        collector.print_summary()


if __name__ == "__main__":
    main()
