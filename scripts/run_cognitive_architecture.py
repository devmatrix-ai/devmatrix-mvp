#!/usr/bin/env python3
"""
E2E Integration Script for Cognitive Architecture MVP

Demonstrates complete pipeline from specification to validated application:
1. Semantic Task Signatures (Week 1)
2. Pattern Bank with GraphCodeBERT embeddings (Week 1)
3. CPIE - Cognitive Pattern Inference Engine (Week 1)
4. Co-Reasoning System - Claude + DeepSeek routing (Week 2)
5. Multi-Pass Planning - 6-pass decomposition (Week 2)
6. DAG Builder - Neo4j dependency graph (Week 2)
7. Orchestrator MVP - Level-by-level execution (Week 2)
8. Ensemble Validator - 6-rule validation (Week 3)
9. E2E Production Validator - 4-layer validation (Week 3)

Usage:
    python scripts/run_cognitive_architecture.py --spec "Build TODO app" --dry-run
    python scripts/run_cognitive_architecture.py --spec-file tests/e2e/synthetic_specs/01_todo_backend_api.md
    python scripts/run_cognitive_architecture.py --example

Requirements:
    - PostgreSQL running (Qdrant)
    - Neo4j running (DAG Builder)
    - Claude API key configured
    - DeepSeek API key configured (optional)
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all cognitive architecture components
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature, compute_semantic_hash
from src.cognitive.patterns.pattern_bank import PatternBank, StoredPattern
from src.cognitive.inference.cpie import CPIE
from src.cognitive.co_reasoning.co_reasoning import CoReasoningSystem, estimate_complexity
from src.cognitive.planning.multi_pass_planner import (
    MultiPassPlanner,
    pass_1_requirements_analysis,
    pass_2_architecture_design,
    pass_3_contract_definition,
    pass_4_integration_points,
    pass_5_atomic_breakdown,
    pass_6_validation,
    plan_complete,
)
from src.cognitive.planning.dag_builder import DAGBuilder
from src.cognitive.orchestration.orchestrator_mvp import OrchestratorMVP, ExecutionMetrics
from src.cognitive.validation.ensemble_validator import EnsembleValidator, ValidationResult
from src.cognitive.validation.e2e_production_validator import E2EProductionValidator, ValidationStatus
from src.cognitive.metrics.e2e_metrics_collector import E2EMetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CognitiveArchitecturePipeline:
    """
    Complete Cognitive Architecture Pipeline (Weeks 1-3).

    Orchestrates the full workflow from high-level specification to
    validated production-ready application.
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        dry_run: bool = False,
    ):
        """
        Initialize complete cognitive architecture pipeline.

        Args:
            qdrant_host: Qdrant vector database host
            qdrant_port: Qdrant vector database port
            neo4j_uri: Neo4j graph database URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            dry_run: If True, simulates execution without actual LLM calls
        """
        self.dry_run = dry_run

        logger.info("=" * 80)
        logger.info("🚀 Initializing Cognitive Architecture Pipeline (Weeks 1-3)")
        logger.info("=" * 80)

        # Week 1: Pattern Storage and Retrieval
        logger.info("📦 [Week 1] Initializing Pattern Bank with GraphCodeBERT...")
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()
        self.pattern_bank.create_collection()

        # Week 2: Co-Reasoning System
        logger.info("🧠 [Week 2] Initializing Co-Reasoning System (Claude + DeepSeek)...")
        self.co_reasoning = CoReasoningSystem(pattern_bank=self.pattern_bank)

        # Week 1: Inference Engine
        logger.info("⚡ [Week 1] Initializing CPIE (Cognitive Pattern Inference Engine)...")
        self.cpie = CPIE(
            pattern_bank=self.pattern_bank,
            co_reasoning_system=self.co_reasoning
        )

        # Week 2: Planning System
        logger.info("📋 [Week 2] Initializing Multi-Pass Planner (6 passes)...")
        self.planner = MultiPassPlanner()

        # Week 2: DAG Builder
        logger.info("🕸️  [Week 2] Initializing DAG Builder (Neo4j)...")
        self.dag_builder = DAGBuilder(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )
        self.dag_builder.initialize_schema()

        # Week 2: Orchestrator
        logger.info("🎯 [Week 2] Initializing Orchestrator MVP...")
        self.orchestrator = OrchestratorMVP(
            pattern_bank=self.pattern_bank,
            planner=self.planner,
            dag_builder=self.dag_builder,
            cpie=self.cpie,
            co_reasoning_system=self.co_reasoning,
        )

        # Week 3: Validators
        logger.info("✅ [Week 3] Initializing Ensemble Validator (6 rules)...")
        self.validator = EnsembleValidator()

        logger.info("🔬 [Week 3] Initializing E2E Production Validator (4 layers)...")
        self.e2e_validator = E2EProductionValidator

        # Week 3: Metrics
        logger.info("📊 [Week 3] Initializing E2E Metrics Collector...")
        self.metrics_collector = E2EMetricsCollector()

        logger.info("✅ All components initialized successfully!\n")

    def run_example(self) -> Dict[str, Any]:
        """
        Run example workflow demonstrating all components.

        Returns:
            Dictionary with execution results and metrics
        """
        logger.info("=" * 80)
        logger.info("🎬 Running Example: Simple Email Validation Function")
        logger.info("=" * 80)

        # Example specification
        spec = """
        # Email Validation Function

        Create a Python function that validates email addresses according to RFC 5322.

        ## Requirements
        - Function name: validate_email
        - Input: email (str)
        - Output: is_valid (bool), error_message (Optional[str])
        - Max 10 lines of code
        - Must handle edge cases: empty string, invalid format, missing @
        - Must use type hints
        - Security level: medium (input validation)
        """

        return self.execute(spec)

    def execute(self, spec: str, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Execute complete cognitive architecture pipeline.

        Pipeline:
        1. Multi-Pass Planning (6 passes) → Atomic tasks
        2. DAG Builder → Dependency graph
        3. Orchestrator → Level-by-level execution with CPIE
        4. Ensemble Validation → Quality gates for each atom
        5. Pattern Learning → Store successful patterns (≥95%)
        6. (Optional) E2E Validation → 4-layer production validation

        Args:
            spec: High-level specification text
            output_path: Optional path to save generated application

        Returns:
            Dictionary with execution results, metrics, and validation status
        """
        start_time = time.time()
        results = {
            "status": "pending",
            "spec": spec,
            "phases": {},
            "metrics": {},
            "errors": [],
        }

        try:
            # ================================================================
            # PHASE 1: Multi-Pass Planning (Week 2)
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("📋 PHASE 1: Multi-Pass Planning (6 passes)")
            logger.info("=" * 80)

            phase1_start = time.time()

            # Pass 1: Requirements Analysis
            logger.info("\n[Pass 1/6] Requirements Analysis...")
            requirements = pass_1_requirements_analysis(spec)
            logger.info(f"  → Entities: {len(requirements.get('entities', []))}")
            logger.info(f"  → Use Cases: {len(requirements.get('use_cases', []))}")

            # Pass 2: Architecture Design
            logger.info("[Pass 2/6] Architecture Design...")
            architecture = pass_2_architecture_design(requirements)
            logger.info(f"  → Modules: {len(architecture.get('modules', []))}")
            logger.info(f"  → Patterns: {len(architecture.get('patterns', []))}")

            # Pass 3: Contract Definition
            logger.info("[Pass 3/6] Contract Definition...")
            contracts = pass_3_contract_definition(architecture)
            logger.info(f"  → API Contracts: {len(contracts.get('api_contracts', []))}")

            # Pass 4: Integration Points
            logger.info("[Pass 4/6] Integration Points Analysis...")
            integration = pass_4_integration_points(contracts)
            logger.info(f"  → Dependencies: {len(integration.get('dependencies', []))}")

            # Pass 5: Atomic Breakdown
            logger.info("[Pass 5/6] Atomic Task Breakdown...")
            atomic_tasks = pass_5_atomic_breakdown(integration)
            logger.info(f"  → Atomic Tasks: {len(atomic_tasks)}")

            # Pass 6: Validation
            logger.info("[Pass 6/6] Validation...")
            is_valid, validated_result = pass_6_validation(atomic_tasks)
            if not is_valid:
                raise ValueError("❌ Validation failed: dependency cycles detected")

            # Extract atoms list from validated_result dict
            task_list = validated_result.get("atoms", [])
            logger.info(f"  → Validated Tasks: {len(task_list)}")
            logger.info(f"  → Validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")

            phase1_time = time.time() - phase1_start
            logger.info(f"\n✅ Phase 1 complete in {phase1_time:.2f}s")

            results["phases"]["planning"] = {
                "status": "success",
                "tasks": task_list,
                "time": phase1_time,
            }

            # ================================================================
            # PHASE 2: DAG Construction (Week 2)
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("🕸️  PHASE 2: DAG Construction (Neo4j)")
            logger.info("=" * 80)

            phase2_start = time.time()

            # Build DAG in Neo4j
            logger.info(f"Building DAG for {len(task_list)} tasks...")
            dag_id = self.dag_builder.build_dag(task_list)
            logger.info(f"  → DAG ID: {dag_id}")

            # Check for cycles
            has_cycles = self.dag_builder.detect_cycles(dag_id)
            if has_cycles:
                raise ValueError("❌ DAG contains cycles! Planning failed.")
            logger.info("  → ✅ No cycles detected")

            # Get topological sort with levels
            levels = self.dag_builder.topological_sort(dag_id)
            logger.info(f"  → Topological levels: {len(levels)}")
            for level_num, tasks_in_level in sorted(levels.items()):
                logger.info(f"    Level {level_num}: {len(tasks_in_level)} tasks (parallel)")

            phase2_time = time.time() - phase2_start
            logger.info(f"\n✅ Phase 2 complete in {phase2_time:.2f}s")

            results["phases"]["dag_construction"] = {
                "status": "success",
                "dag_id": dag_id,
                "levels": len(levels),
                "has_cycles": has_cycles,
                "time": phase2_time,
            }

            # ================================================================
            # PHASE 3: Orchestrated Execution (Week 2)
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("⚡ PHASE 3: Orchestrated Execution (CPIE + Co-Reasoning)")
            logger.info("=" * 80)

            phase3_start = time.time()

            if self.dry_run:
                logger.info("🔍 DRY RUN MODE: Simulating execution...")
                execution_result = self._simulate_execution(task_list, levels)
            else:
                # Execute using Orchestrator MVP
                logger.info("Executing tasks level-by-level...")
                execution_result = self.orchestrator.execute(spec)

            phase3_time = time.time() - phase3_start

            logger.info(f"\n📊 Execution Summary:")
            logger.info(f"  → Total Tasks: {execution_result.get('task_count', 0)}")
            logger.info(f"  → Successful: {execution_result.get('success_count', 0)}")
            logger.info(f"  → Failed: {execution_result.get('failure_count', 0)}")
            logger.info(f"  → Retries: {execution_result.get('retry_count', 0)}")
            logger.info(f"  → Pattern Reuse: {execution_result.get('pattern_reuse_count', 0)}")
            logger.info(f"  → New Patterns: {execution_result.get('new_patterns_learned', 0)}")
            logger.info(f"\n✅ Phase 3 complete in {phase3_time:.2f}s")

            results["phases"]["execution"] = {
                "status": execution_result.get("status", "unknown"),
                "metrics": execution_result,
                "time": phase3_time,
            }

            # ================================================================
            # PHASE 4: Validation (Week 3)
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("✅ PHASE 4: Ensemble Validation (6 rules)")
            logger.info("=" * 80)

            phase4_start = time.time()

            # Validate each generated atom
            validation_results = []
            if not self.dry_run and "generated_code" in execution_result:
                for task_id, code in execution_result["generated_code"].items():
                    # Get signature for this task
                    signature = self._get_signature_for_task(task_id, task_list)

                    # Validate with ensemble validator
                    validation = self.validator.validate(code, signature)
                    validation_results.append({
                        "task_id": task_id,
                        "is_valid": validation.is_valid,
                        "quality_score": validation.quality_score,
                    })

                    if validation.is_valid:
                        logger.info(f"  ✅ Task {task_id}: Valid (score: {validation.quality_score})")
                    else:
                        logger.info(f"  ❌ Task {task_id}: Invalid - {validation.failure_reason}")

            phase4_time = time.time() - phase4_start

            validation_pass_rate = 0
            if validation_results:
                validation_pass_rate = sum(1 for v in validation_results if v["is_valid"]) / len(validation_results)

            logger.info(f"\n📊 Validation Summary:")
            logger.info(f"  → Total Validated: {len(validation_results)}")
            logger.info(f"  → Pass Rate: {validation_pass_rate:.1%}")
            logger.info(f"\n✅ Phase 4 complete in {phase4_time:.2f}s")

            results["phases"]["validation"] = {
                "status": "success",
                "pass_rate": validation_pass_rate,
                "results": validation_results,
                "time": phase4_time,
            }

            # ================================================================
            # PHASE 5: E2E Production Validation (Week 3) - Optional
            # ================================================================
            if output_path and not self.dry_run:
                logger.info("\n" + "=" * 80)
                logger.info("🔬 PHASE 5: E2E Production Validation (4 layers)")
                logger.info("=" * 80)

                phase5_start = time.time()

                # Run 4-layer validation
                e2e_validator = self.e2e_validator(
                    app_path=output_path,
                    spec_name="generated_app"
                )

                e2e_report = e2e_validator.validate()
                e2e_validator.cleanup()

                # Collect metrics
                e2e_metrics = self.metrics_collector.collect_from_report(e2e_report)

                phase5_time = time.time() - phase5_start

                logger.info(f"\n📊 E2E Validation Summary:")
                logger.info(f"  → Build: {'✅' if e2e_report.layers['build'].status == ValidationStatus.PASSED else '❌'}")
                logger.info(f"  → Unit Tests: {'✅' if e2e_report.layers['unit_tests'].status == ValidationStatus.PASSED else '❌'}")
                logger.info(f"  → E2E Tests: {'✅' if e2e_report.layers['e2e_tests'].status == ValidationStatus.PASSED else '❌'}")
                logger.info(f"  → Production Ready: {'✅' if e2e_report.layers['production_ready'].status == ValidationStatus.PASSED else '❌'}")
                logger.info(f"  → E2E Precision: {e2e_metrics.e2e_precision:.1%}")
                logger.info(f"\n✅ Phase 5 complete in {phase5_time:.2f}s")

                results["phases"]["e2e_validation"] = {
                    "status": e2e_report.overall_status.value,
                    "precision": e2e_metrics.e2e_precision,
                    "time": phase5_time,
                }

            # ================================================================
            # Final Summary
            # ================================================================
            total_time = time.time() - start_time
            results["status"] = "success"
            results["total_time"] = total_time

            logger.info("\n" + "=" * 80)
            logger.info("🎉 PIPELINE COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Total Time: {total_time:.2f}s")
            logger.info(f"Status: {'✅ SUCCESS' if results['status'] == 'success' else '❌ FAILED'}")

            return results

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            results["status"] = "failed"
            results["errors"].append(str(e))
            return results

        finally:
            # Cleanup
            self.cleanup()

    def _simulate_execution(self, tasks: list, levels: list) -> Dict[str, Any]:
        """Simulate execution for dry-run mode."""
        return {
            "status": "success",
            "task_count": len(tasks),
            "success_count": len(tasks),
            "failure_count": 0,
            "retry_count": 0,
            "pattern_reuse_count": int(len(tasks) * 0.3),  # Assume 30% reuse
            "new_patterns_learned": int(len(tasks) * 0.7),  # Assume 70% new
            "generated_code": {},  # No actual code in dry-run
        }

    def _get_signature_for_task(self, task_id: str, tasks: list) -> SemanticTaskSignature:
        """Get semantic signature for a task."""
        for task in tasks:
            if task.get("id") == task_id:
                return SemanticTaskSignature(
                    purpose=task.get("purpose", ""),
                    intent=task.get("intent", "implement"),
                    inputs=task.get("inputs", {}),
                    outputs=task.get("outputs", {}),
                    domain=task.get("domain", "general"),
                )

        # Fallback
        return SemanticTaskSignature(
            purpose="Unknown task",
            intent="implement",
            inputs={},
            outputs={},
            domain="general",
        )

    def cleanup(self):
        """Clean up resources."""
        logger.info("\n🧹 Cleaning up resources...")

        if hasattr(self, 'dag_builder'):
            self.dag_builder.close()

        # PatternBank cleanup (Qdrant connection stays open)
        logger.info("Pattern Bank: Qdrant connection remains active")

        logger.info("✅ Cleanup complete")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run Cognitive Architecture E2E Pipeline (Weeks 1-3)"
    )
    parser.add_argument(
        "--spec",
        type=str,
        help="High-level specification text"
    )
    parser.add_argument(
        "--spec-file",
        type=Path,
        help="Path to specification file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for generated application"
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Run example workflow"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without LLM calls"
    )
    parser.add_argument(
        "--qdrant-host",
        default="localhost",
        help="Qdrant host (default: localhost)"
    )
    parser.add_argument(
        "--qdrant-port",
        type=int,
        default=6333,
        help="Qdrant port (default: 6333)"
    )
    parser.add_argument(
        "--neo4j-uri",
        default="bolt://localhost:7687",
        help="Neo4j URI (default: bolt://localhost:7687)"
    )
    parser.add_argument(
        "--neo4j-user",
        default="neo4j",
        help="Neo4j username (default: neo4j)"
    )
    parser.add_argument(
        "--neo4j-password",
        default="password",
        help="Neo4j password"
    )

    args = parser.parse_args()

    # Get spec
    spec = None
    if args.spec:
        spec = args.spec
    elif args.spec_file:
        if not args.spec_file.exists():
            logger.error(f"Spec file not found: {args.spec_file}")
            sys.exit(1)
        spec = args.spec_file.read_text()
    elif not args.example:
        logger.error("Please provide --spec, --spec-file, or --example")
        parser.print_help()
        sys.exit(1)

    # Initialize pipeline
    pipeline = CognitiveArchitecturePipeline(
        qdrant_host=args.qdrant_host,
        qdrant_port=args.qdrant_port,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        dry_run=args.dry_run,
    )

    # Run pipeline
    if args.example:
        results = pipeline.run_example()
    else:
        results = pipeline.execute(spec, output_path=args.output)

    # Print results
    print("\n" + "=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print(json.dumps(results, indent=2, default=str))

    # Exit code
    sys.exit(0 if results["status"] == "success" else 1)


if __name__ == "__main__":
    main()
