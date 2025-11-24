"""
Example: How to integrate ProgressTracker into E2E Pipeline
Shows usage patterns for animated progress bars and live metrics
"""

from progress_tracker import (
    get_tracker,
    start_phase,
    update_phase,
    increment_step,
    add_item,
    complete_phase,
    add_error,
    update_metrics,
    display_progress
)
import time


def example_full_pipeline():
    """Example full E2E pipeline with progress tracking"""

    tracker = get_tracker()

    # Phase 1: Spec Ingestion
    print("\n🚀 Starting E2E Pipeline with Progress Tracking...\n")

    start_phase("Spec Ingestion", substeps=4)
    update_phase("Spec Ingestion", step="Loading spec file")
    time.sleep(0.5)
    increment_step("Spec Ingestion")
    add_item("Spec Ingestion", "entities", 24, 24)

    update_phase("Spec Ingestion", step="Extracting endpoints")
    time.sleep(0.3)
    increment_step("Spec Ingestion")
    add_item("Spec Ingestion", "endpoints", 18, 18)

    update_phase("Spec Ingestion", step="Parsing requirements")
    time.sleep(0.3)
    increment_step("Spec Ingestion")
    add_item("Spec Ingestion", "requirements", 67, 67)

    update_phase("Spec Ingestion", step="Assessing complexity")
    time.sleep(0.2)
    increment_step("Spec Ingestion")

    complete_phase("Spec Ingestion", success=True)
    update_metrics(neo4j=12, qdrant=5, tokens=45000)
    display_progress()
    time.sleep(1)

    # Phase 2: Requirements Analysis
    start_phase("Requirements Analysis", substeps=4)
    update_phase("Requirements Analysis", step="Functional classification")
    time.sleep(0.4)
    increment_step("Requirements Analysis")
    add_item("Requirements Analysis", "functional", 65, 67)

    update_phase("Requirements Analysis", step="Domain classification")
    time.sleep(0.5)
    increment_step("Requirements Analysis")
    add_item("Requirements Analysis", "Auth", 8, 8)
    add_item("Requirements Analysis", "Data", 24, 24)
    add_item("Requirements Analysis", "API", 18, 18)

    update_phase("Requirements Analysis", step="Building dependency graph")
    time.sleep(0.4)
    increment_step("Requirements Analysis")

    update_phase("Requirements Analysis", step="Validating DAG")
    time.sleep(0.3)
    increment_step("Requirements Analysis")

    complete_phase("Requirements Analysis", success=True)
    update_metrics(neo4j=34, qdrant=12, tokens=120000)
    display_progress()
    time.sleep(1)

    # Phase 3-5: Planning & DAG (simulated as one)
    start_phase("Multi-Pass Planning", substeps=3)
    update_phase("Multi-Pass Planning", step="First pass: Architecture")
    time.sleep(0.6)
    increment_step("Multi-Pass Planning")

    update_phase("Multi-Pass Planning", step="Second pass: Implementation")
    time.sleep(0.5)
    increment_step("Multi-Pass Planning")

    update_phase("Multi-Pass Planning", step="Third pass: Optimization")
    time.sleep(0.4)
    increment_step("Multi-Pass Planning")

    complete_phase("Multi-Pass Planning", success=True)
    update_metrics(neo4j=56, qdrant=18, tokens=250000)
    display_progress()
    time.sleep(1)

    start_phase("Atomization", substeps=2)
    update_phase("Atomization", step="Decomposing requirements")
    time.sleep(0.5)
    increment_step("Atomization")
    add_item("Atomization", "atomic_units", 234, 234)

    update_phase("Atomization", step="Assigning priorities")
    time.sleep(0.4)
    increment_step("Atomization")

    complete_phase("Atomization", success=True)
    update_metrics(neo4j=78, qdrant=24, tokens=380000)
    display_progress()
    time.sleep(1)

    start_phase("DAG Construction", substeps=3)
    update_phase("DAG Construction", step="Creating nodes")
    time.sleep(0.5)
    increment_step("DAG Construction")
    add_item("DAG Construction", "nodes", 234, 234)

    update_phase("DAG Construction", step="Adding edges")
    time.sleep(0.4)
    increment_step("DAG Construction")
    add_item("DAG Construction", "edges", 312, 312)

    update_phase("DAG Construction", step="Topological sort")
    time.sleep(0.3)
    increment_step("DAG Construction")

    complete_phase("DAG Construction", success=True)
    update_metrics(neo4j=98, qdrant=30, tokens=450000)
    display_progress()
    time.sleep(1)

    # Phase 6: Code Generation
    start_phase("Code Generation", substeps=3)
    update_phase("Code Generation", step="Generating models")
    time.sleep(0.8)
    increment_step("Code Generation")
    add_item("Code Generation", "models", 24, 24)

    update_phase("Code Generation", step="Generating routes")
    time.sleep(0.7)
    increment_step("Code Generation")
    add_item("Code Generation", "routes", 18, 18)

    update_phase("Code Generation", step="Generating tests")
    time.sleep(0.6)
    increment_step("Code Generation")
    add_item("Code Generation", "tests", 89, 89)

    complete_phase("Code Generation", success=True)
    update_metrics(neo4j=145, qdrant=45, tokens=750000)
    display_progress()
    time.sleep(1)

    # Phase 7: Code Repair
    start_phase("Code Repair", substeps=2)
    update_phase("Code Repair", step="Identifying issues")
    time.sleep(0.5)
    increment_step("Code Repair")

    update_phase("Code Repair", step="Applying repairs")
    time.sleep(0.4)
    increment_step("Code Repair")
    add_item("Code Repair", "repairs_applied", 8, 8)
    add_item("Code Repair", "tests_fixed", 8, 8)

    complete_phase("Code Repair", success=True)
    update_metrics(neo4j=167, qdrant=52, tokens=850000)
    display_progress()
    time.sleep(1)

    # Phase 8: Validation
    start_phase("Validation", substeps=3)
    update_phase("Validation", step="Schema validation")
    time.sleep(0.3)
    increment_step("Validation")

    update_phase("Validation", step="Compliance check")
    time.sleep(0.4)
    increment_step("Validation")

    update_phase("Validation", step="Contract validation")
    time.sleep(0.3)
    increment_step("Validation")

    complete_phase("Validation", success=True)
    update_metrics(neo4j=189, qdrant=61, tokens=920000)
    display_progress()
    time.sleep(1)

    # Phase 9: Deployment
    start_phase("Deployment", substeps=2)
    update_phase("Deployment", step="Building Docker")
    time.sleep(0.6)
    increment_step("Deployment")

    update_phase("Deployment", step="Health checks")
    time.sleep(0.4)
    increment_step("Deployment")

    complete_phase("Deployment", success=True)
    update_metrics(neo4j=201, qdrant=68, tokens=980000)
    display_progress()
    time.sleep(1)

    # Phase 10: Learning
    start_phase("Learning", substeps=2)
    update_phase("Learning", step="Analyzing patterns")
    time.sleep(0.5)
    increment_step("Learning")
    add_item("Learning", "patterns_analyzed", 87, 87)
    add_item("Learning", "patterns_promoted", 6, 6)

    update_phase("Learning", step="Storing success patterns")
    time.sleep(0.3)
    increment_step("Learning")

    complete_phase("Learning", success=True)
    update_metrics(neo4j=234, qdrant=78, tokens=1000000)
    display_progress()

    # Final summary
    print("\n" + "=" * 80)
    print(" " * 25 + "🎉 PIPELINE COMPLETED SUCCESSFULLY" + " " * 20)
    print("=" * 80)

    summary = tracker.get_summary()
    for phase_name, metrics in summary.items():
        print(f"\n{phase_name}:")
        print(f"  Status: {metrics['status']}")
        print(f"  Duration: {metrics['duration_ms']:.0f}ms")
        if metrics['items']:
            for item_type, (completed, total) in metrics['items'].items():
                print(f"  {item_type}: {completed}/{total}")


if __name__ == "__main__":
    example_full_pipeline()
