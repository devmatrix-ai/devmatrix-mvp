"""
Example: Structured Logging with Progress Tracking
Shows how to use StructuredLogger to eliminate duplicates while maintaining detail
"""

from tests.e2e.progress_tracker import (
    get_tracker,
    start_phase,
    complete_phase,
    display_progress,
)
from tests.e2e.structured_logger import (
    create_phase_logger,
    log_phase_header,
    get_context_logger,
)
import time


def example_requirements_analysis():
    """Example Phase 2: Requirements Analysis with structured logging"""

    log_phase_header("Phase 2: Requirements Analysis")

    # Create logger for this phase
    logger = create_phase_logger("Requirements Analysis")

    # Start progress tracking
    start_phase("Requirements Analysis", substeps=5)

    # Section 1: Semantic Classification
    logger.section("Semantic Classification (RequirementsClassifier)")
    logger.step("Running semantic classification...")
    time.sleep(0.3)

    logger.success(
        "Classified 24 requirements",
        {
            "Functional": 17,
            "Non-functional": 7,
            "Status": "Complete",
        },
    )

    logger.metric("Accuracy", 33.3, "%")
    logger.metric("Classified items", 24)

    # Section 2: Domain Analysis
    logger.section("Domain Classification & Analysis")
    logger.step("Analyzing domain distribution...")

    domains = {
        "CRUD operations": 12,
        "Authentication": 4,
        "Payment processing": 4,
        "Workflow": 2,
        "Search": 2,
    }
    logger.data_structure("Domain Distribution", domains)

    # Section 3: Pattern Matching
    logger.section("Pattern Matching & Analysis")
    logger.step("Searching for similar patterns...")

    logger.success("Pattern matching completed", {"Patterns found": 10})

    # Accuracy Metrics
    logger.accuracy_metrics(accuracy=0.333, precision=0.800, recall=0.471, f1=0.593)

    # Section 4: Checkpoint Validation
    logger.section("Validation Checkpoints")
    logger.checkpoint("CP-2.1", "Functional requirements classification")
    logger.checkpoint("CP-2.2", "Non-functional requirements extraction")
    logger.checkpoint("CP-2.3", "Dependency identification")
    logger.checkpoint("CP-2.4", "Constraint extraction")
    logger.checkpoint("CP-2.5", "Pattern matching validation")

    # Complete phase and update metrics
    complete_phase("Requirements Analysis", success=True)
    logger.update_live_metrics(neo4j=34, qdrant=12, tokens=120000)

    # Display progress
    display_progress()
    time.sleep(0.5)


def example_code_repair():
    """Example Phase 6.5: Code Repair with structured logging"""

    log_phase_header("Phase 6.5: Code Repair (Enhanced)")

    logger = create_phase_logger("Code Repair")
    start_phase("Code Repair", substeps=5)

    # Compliance Pre-Check
    logger.section("Compliance Pre-Check")
    logger.step("Validating generated code...")

    logger.success(
        "Pre-check complete",
        {
            "Compliance": "53.7%",
            "Entities": "4/4 ✓",
            "Endpoints": "4/17 ⚠️",
        },
    )

    # Repair Loop
    logger.section("Repair Iteration 1/3", emoji="🔁")
    logger.step("Analyzing 33 failures...")

    repairs_applied = [
        "Added endpoint: POST /products",
        "Added endpoint: GET /products",
        "Added endpoint: GET /products/{id}",
        "Added endpoint: PUT /products/{id}",
        "Added endpoint: DELETE /products/{id}",
        "Added validation: Cart.status required",
        "Added validation: CartItem.product_id uuid_format",
    ]

    logger.info(
        f"Applied {len(repairs_applied)} repairs",
        {"Status": "In progress", "Improvements": "33 → 33"},
    )

    # Results
    logger.section("Re-validation Results")
    logger.success(
        "Validation passed",
        {
            "Initial": "53.7%",
            "After repair": "54.1%",
            "Improvement": "+0.4%",
        },
    )

    logger.checkpoint("CP-6.5.1", "Compliance pre-check")
    logger.checkpoint("CP-6.5.2", "Repair initialization")
    logger.checkpoint("CP-6.5.3", "Repair execution")
    logger.checkpoint("CP-6.5.4", "Re-validation")

    # Complete
    complete_phase("Code Repair", success=True)
    logger.update_live_metrics(neo4j=167, qdrant=52, tokens=850000)
    display_progress()
    time.sleep(0.5)


def example_code_generation():
    """Example Phase 6: Code Generation with structured logging"""

    log_phase_header("Phase 6: Code Generation")

    logger = create_phase_logger("Code Generation")
    start_phase("Code Generation", substeps=5)

    # IR Construction
    logger.section("ApplicationIR Construction", emoji="🏗️")
    logger.step("Building Application Intermediate Representation...")

    logger.success(
        "ApplicationIR constructed successfully",
        {
            "App ID": "07334f91-e612-4911-944a-9c58f9fb7737",
            "Status": "Persisted to Neo4j",
        },
    )

    # Pattern Retrieval
    logger.section("Pattern Retrieval", emoji="📚")
    logger.step("Retrieving production-ready patterns...")

    pattern_categories = {
        "Core Configuration": 1,
        "Database (Async)": 1,
        "Observability": 5,
        "Models (Pydantic)": 1,
        "Models (SQLAlchemy)": 1,
        "Repository Pattern": 1,
        "Business Logic": 1,
        "API Routes": 1,
        "Security": 1,
        "Testing": 7,
        "Docker": 4,
        "Project Config": 3,
    }

    logger.metrics_group("Pattern Categories Retrieved", pattern_categories)

    # Code Composition
    logger.section("Code Composition", emoji="🔧")
    logger.step("Composing production-ready application...")

    files_generated = {
        "Configuration files": 3,
        "Core modules": 4,
        "Models": 2,
        "Repositories": 4,
        "Services": 4,
        "API routes": 4,
        "Tests": 7,
        "Docker infrastructure": 6,
        "Project files": 8,
    }

    logger.data_structure("Files Generated by Category", files_generated)

    logger.success(
        "Code generation completed",
        {
            "Total files": 57,
            "Total code": "150,544 lines",
            "Mode": "Production-ready",
        },
    )

    # Checkpoints
    logger.section("Generation Checkpoints")
    logger.checkpoint("CP-6.1", "Code generation started")
    logger.checkpoint("CP-6.2", "Pattern retrieval completed")
    logger.checkpoint("CP-6.3", "Code composition started")
    logger.checkpoint("CP-6.4", "File generation completed")
    logger.checkpoint("CP-6.5", "Production mode validation")

    # Complete
    complete_phase("Code Generation", success=True)
    logger.update_live_metrics(neo4j=145, qdrant=45, tokens=750000)
    display_progress()
    time.sleep(0.5)


def main():
    """Run example with structured logging"""

    print("\n🚀 E2E Pipeline with Structured Logging (No Duplicates)\n")

    # Example 1: Requirements Analysis
    example_requirements_analysis()

    # Example 2: Code Generation
    example_code_generation()

    # Example 3: Code Repair
    example_code_repair()

    # Final Summary
    print("\n" + "=" * 80)
    print("📊 STRUCTURED LOGGING SUMMARY")
    print("=" * 80)

    context_logger = get_context_logger()

    # Show phase logs
    all_logs = context_logger.get_all_logs()
    all_metrics = context_logger.get_all_metrics()

    for phase_name, logs in all_logs.items():
        print(f"\n✅ {phase_name}")
        print(f"   └─ Logged items: {len(logs)}")
        for i, log in enumerate(logs[:3], 1):
            print(f"      {i}. {log[:60]}...")
        if len(logs) > 3:
            print(f"      ... and {len(logs) - 3} more")

    # Show phase metrics
    print("\n📊 Collected Metrics by Phase")
    for phase_name, metrics in all_metrics.items():
        print(f"\n  {phase_name}:")
        for key, value in list(metrics.items())[:5]:
            print(f"    • {key}: {value}")


if __name__ == "__main__":
    main()
