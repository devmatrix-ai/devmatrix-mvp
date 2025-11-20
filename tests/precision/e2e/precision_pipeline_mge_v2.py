"""
E2E Precision Pipeline with Real MGE V2 Integration

Complete precision measurement using the real MGE V2 pipeline:
Discovery → MasterPlan → Code Generation → Atomization → File Writing → Contract Testing → Precision Measurement

This replaces the mock implementation with full MGE V2 integration.

Author: DevMatrix Team
Date: 2025-11-14
"""

import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import tempfile
import json

# Import precision components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.precision.generators.contract_test_generator import ContractTestGenerator
from tests.precision.validators.code_validator import GeneratedCodeValidator
from tests.precision.correction.auto_corrector import PrecisionAutoCorrector
from tests.precision.correction.failure_analyzer import FailureAnalyzer

# Import MGE V2 components
from src.services.mge_v2_orchestration_service import MGE_V2_OrchestrationService
from src.services.code_generation_service import CodeGenerationService
from src.config.database import DatabaseConfig
from src.models import MasterPlan, DiscoveryDocument


@dataclass
class MGE_V2_PipelineResult:
    """Complete E2E pipeline result with MGE V2 integration."""

    # Discovery and MasterPlan
    discovery_id: str
    masterplan_id: str
    module_name: str
    project_name: str

    # MGE V2 execution
    total_tasks: int
    total_atoms: int
    workspace_path: str
    code_generation_cost_usd: float
    code_generation_time: float

    # Contract testing
    tests_generated: int
    contracts_extracted: int
    test_file: str

    # Precision validation
    initial_precision: float
    final_precision: float
    target_precision: float
    precision_gate_passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    must_gate_passed: bool
    should_gate_passed: bool
    gate_passed: bool

    # Auto-correction
    auto_correction_applied: bool
    correction_iterations: int
    total_improvement: float

    # Overall metrics
    total_time: float
    timestamp: datetime

    # Repair loop (STEP 5 - NEW)
    repair_applied: bool = False
    repair_iterations: int = 0
    repair_improvement: float = 0.0
    repair_metrics: Optional[Dict[str, Any]] = None


class E2EPrecisionPipelineMGE_V2:
    """
    Complete E2E precision pipeline with real MGE V2 integration.

    Flow:
    1. Discovery Document (from user request or provided)
    2. MGE V2 Orchestration (MasterPlan → Code Gen → Atomization → Files)
    3. Contract Test Generation (from discovery document)
    4. Code Validation (contract tests against generated code)
    5. Auto-Correction (if enabled and precision < target)
    6. Metrics Reporting
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        auto_correct: bool = True,
        target_precision: float = 0.92,
        max_correction_iterations: int = 5,
    ):
        """
        Initialize E2E pipeline with MGE V2.

        Args:
            anthropic_api_key: Claude API key
            auto_correct: Enable auto-correction (default: True)
            target_precision: Target precision (default: 0.92 = 92%)
            max_correction_iterations: Max correction iterations (default: 5)
        """
        self.api_key = anthropic_api_key
        self.auto_correct = auto_correct
        self.target_precision = target_precision
        self.max_correction_iterations = max_correction_iterations

        # Initialize precision components
        self.contract_generator = ContractTestGenerator(api_key=anthropic_api_key)
        self.code_validator = GeneratedCodeValidator()
        self.failure_analyzer = FailureAnalyzer()
        self.auto_corrector = PrecisionAutoCorrector(
            target_precision=target_precision,
            max_iterations=max_correction_iterations,
            anthropic_api_key=anthropic_api_key,
        )

        print(f"✅ E2E Precision Pipeline with MGE V2 initialized")
        print(f"  Target Precision: {target_precision:.1%}")
        print(f"  Auto-Correction: {'Enabled' if auto_correct else 'Disabled'}")

    async def execute_from_discovery(
        self,
        discovery_doc: str,
        user_id: str = "precision_test",
        session_id: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> MGE_V2_PipelineResult:
        """
        Execute complete E2E pipeline from discovery document using real MGE V2.

        Args:
            discovery_doc: Discovery document markdown
            user_id: User identifier
            session_id: Session identifier (auto-generated if not provided)
            output_dir: Output directory for metrics (default: temp dir)

        Returns:
            MGE_V2_PipelineResult with complete metrics
        """
        print("\n" + "=" * 80)
        print("🚀 E2E PRECISION PIPELINE - REAL MGE V2 INTEGRATION")
        print("=" * 80)

        start_time = datetime.now()
        session_id = session_id or str(uuid.uuid4())

        # Create output directory - PERSISTENT in workspace_tests (not /tmp)
        if output_dir is None:
            # Use persistent workspace_tests directory instead of tempfile
            workspace_base = Path(__file__).parent.parent.parent.parent / "workspace_tests"
            workspace_base.mkdir(parents=True, exist_ok=True)

            # Create unique subdirectory for this test run
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = str(uuid.uuid4())[:8]
            output_dir = workspace_base / f"e2e_precision_mge_v2_{timestamp}_{run_id}"
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📁 Output Directory: {output_dir}")
        print(f"👤 User ID: {user_id}")
        print(f"🔖 Session ID: {session_id}")

        # Create database session
        session_factory = DatabaseConfig.get_session_factory()
        db = session_factory()

        try:
            # STEP 1: Create Discovery Document in database
            print("\n" + "-" * 80)
            print("STEP 1: Create Discovery Document")
            print("-" * 80)

            # Parse discovery document to extract domain info (simple extraction)
            domain_name = self._extract_domain_from_discovery(discovery_doc)

            discovery = DiscoveryDocument(
                discovery_id=uuid.uuid4(),
                session_id=session_id,
                user_id=user_id,
                user_request=discovery_doc[:500],  # Store first 500 chars as user request
                domain=domain_name,
                bounded_contexts=[{"name": domain_name, "description": "Main context"}],
                aggregates=[],
                value_objects=[],
                domain_events=[],
                services=[],
            )
            db.add(discovery)
            db.commit()
            db.refresh(discovery)

            print(f"✅ Discovery Document created: {discovery.discovery_id}")
            print(f"  Domain: {domain_name}")

            # STEP 2: Execute MGE V2 Pipeline (MasterPlan → Code → Atomization → Files)
            print("\n" + "-" * 80)
            print("STEP 2: Execute MGE V2 Pipeline")
            print("-" * 80)

            mge_v2_service = MGE_V2_OrchestrationService(
                db=db,
                api_key=self.api_key,
                enable_caching=True,
                enable_rag=True,
            )

            # Track MGE V2 execution
            masterplan_id = None
            total_tasks = 0
            total_atoms = 0
            workspace_path = None
            code_gen_cost = 0.0
            mge_v2_start = datetime.now()

            async for event in mge_v2_service.orchestrate_from_discovery(
                discovery_id=discovery.discovery_id,
                session_id=session_id,
                user_id=user_id,
            ):
                # Track events
                if event["type"] == "status":
                    print(f"  [{event['phase']}] {event['message']}")

                    if event["phase"] == "masterplan_generation" and "masterplan_id" in event:
                        masterplan_id = event["masterplan_id"]

                    if event["phase"] == "file_writing" and "workspace_path" in event:
                        workspace_path = event["workspace_path"]

                elif event["type"] == "complete":
                    masterplan_id = event["masterplan_id"]
                    total_tasks = event["total_tasks"]
                    total_atoms = event["total_atoms"]

                elif event["type"] == "error":
                    raise RuntimeError(f"MGE V2 failed: {event['message']}")

            mge_v2_time = (datetime.now() - mge_v2_start).total_seconds()

            if not workspace_path:
                raise RuntimeError("MGE V2 did not produce workspace_path")

            print(f"\n✅ MGE V2 Pipeline completed in {mge_v2_time:.2f}s")
            print(f"  MasterPlan ID: {masterplan_id}")
            print(f"  Tasks: {total_tasks}")
            print(f"  Atoms: {total_atoms}")
            print(f"  Workspace: {workspace_path}")

            # Load MasterPlan to get cost info
            masterplan = db.query(MasterPlan).filter(
                MasterPlan.masterplan_id == uuid.UUID(masterplan_id)
            ).first()

            code_gen_cost = masterplan.generation_cost_usd if masterplan else 0.0
            project_name = masterplan.project_name if masterplan else domain_name

            # STEP 3: Generate Contract Tests from Discovery Document
            print("\n" + "-" * 80)
            print("STEP 3: Generate Contract Tests")
            print("-" * 80)

            test_dir = output_dir / "tests"
            module_name = domain_name.lower().replace(" ", "_").replace("-", "_")

            contract_stats = self.contract_generator.generate_from_discovery(
                discovery_doc=discovery_doc,
                output_dir=test_dir,
                module_name=module_name,
                code_dir=Path(workspace_path),  # Fix 3.2b: Pass code_dir for import analysis
            )

            test_file = test_dir / f"test_{module_name}_contracts.py"
            print(f"✅ Generated {contract_stats['tests_generated']} contract tests")
            print(f"  Test File: {test_file}")

            # STEP 4: Validate Generated Code with Contract Tests
            print("\n" + "-" * 80)
            print("STEP 4: Validate Generated Code")
            print("-" * 80)

            code_dir = Path(workspace_path)

            validation_result = self.code_validator.validate(
                code_dir=code_dir,
                test_file=test_file,
                module_name=module_name,
            )

            initial_precision = validation_result.precision
            print(f"  Initial Precision: {initial_precision:.1%}")
            print(f"  Tests Passed: {validation_result.passed_tests}/{validation_result.total_tests}")

            # STEP 5: Iterative Repair Loop (NEW - Code Repair with Learning)
            repair_applied = False
            repair_iterations = 0
            repair_improvement = 0.0
            repair_metrics_dict = None
            final_validation = validation_result

            if validation_result.precision < self.target_precision:
                print("\n" + "-" * 80)
                print("STEP 5: Iterative Repair Loop")
                print("-" * 80)
                print(f"  Precision {validation_result.precision:.1%} < Target {self.target_precision:.1%}")

                try:
                    # Import CodeRepairAgent
                    from src.mge.v2.agents.code_repair_agent import CodeRepairAgent
                    from src.services.error_pattern_store import get_error_pattern_store
                    from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

                    # Initialize repair agent
                    error_store = get_error_pattern_store()
                    repair_llm = EnhancedAnthropicClient()

                    repair_agent = CodeRepairAgent(
                        error_pattern_store=error_store,
                        code_validator=self.code_validator,
                        llm_client=repair_llm,
                        max_iterations=3,
                        precision_target=self.target_precision,
                    )

                    print(f"  🔧 Initialized CodeRepairAgent (max_iterations=3)")

                    # Execute repair loop
                    repair_result = await repair_agent.repair_failures(
                        validation_result=validation_result,
                        code_dir=code_dir,
                        test_file=test_file,
                        module_name=module_name,
                        masterplan_id=str(masterplan_id),
                    )

                    # Log repair metrics
                    print(f"\n✅ Repair Loop Complete")
                    print(f"  Iterations: {repair_result.iterations_executed}/{repair_result.max_iterations}")
                    print(f"  Tests Fixed: {repair_result.tests_fixed}")
                    print(f"  Improvement: {validation_result.precision:.1%} → {repair_result.final_precision:.1%} (+{repair_result.final_precision - validation_result.precision:.1%})")
                    print(f"  Gate Passed: {repair_result.gate_passed}")

                    # Update tracking variables
                    repair_applied = True
                    repair_iterations = repair_result.iterations_executed
                    repair_improvement = repair_result.final_precision - validation_result.precision
                    repair_metrics_dict = repair_result.to_dict()

                    # Re-validate to get final result after repairs
                    final_validation = self.code_validator.validate(
                        code_dir=code_dir,
                        test_file=test_file,
                        module_name=module_name,
                    )

                    print(f"  📊 Final Validation: {final_validation.precision:.1%} ({final_validation.passed_tests}/{final_validation.total_tests} tests passed)")

                except ImportError as e:
                    print(f"  ⚠️  CodeRepairAgent not available (skipping repair): {e}")
                    # Continue without repair
                except Exception as e:
                    print(f"  ⚠️  Repair loop failed (continuing): {e}")
                    # Continue without repair

            # STEP 6: Auto-Correction (if enabled and needed)
            auto_correction_applied = False
            correction_iterations = 0
            total_improvement = 0.0
            final_precision = final_validation.precision  # Use precision after repair (or initial if no repair)

            # Only apply auto-correction if repair didn't reach target
            if self.auto_correct and final_validation.precision < self.target_precision:
                print("\n" + "-" * 80)
                print("STEP 6: Auto-Correction Loop (Legacy)")
                print("-" * 80)
                print(f"  Precision {final_validation.precision:.1%} < Target {self.target_precision:.1%}")

                # Create regeneration function that uses MGE V2's CodeGenerationService
                from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
                from src.models import AtomicUnit, MasterPlanTask
                from src.services.atom_service import AtomService

                # Initialize services for regeneration
                llm_client = EnhancedAnthropicClient()
                code_gen_service = CodeGenerationService(db=db, llm_client=llm_client)
                atom_service = AtomService(db=db)

                def regenerate_atom_func(atoms_to_regenerate: set, strategy: str) -> int:
                    """
                    Regenerate specific atoms using CodeGenerationService.

                    Args:
                        atoms_to_regenerate: Set of atom IDs (format: "atom-reqXXX-impl-XXX")
                        strategy: Regeneration strategy (standard, improved_prompts, etc.)

                    Returns:
                        Number of atoms successfully regenerated
                    """
                    print(f"    🔧 Regenerating {len(atoms_to_regenerate)} atoms with strategy: {strategy}")

                    # Map atoms to their parent tasks
                    task_ids = set()

                    for atom_id_str in atoms_to_regenerate:
                        # Query AtomicUnit from database to find parent task
                        # Note: atom_id format is "atom-reqXXX-impl-XXX" (string), but DB uses UUID
                        # For now, we'll do a simple extraction and lookup

                        # TODO: This is a simplified implementation
                        # In production, we need proper atom_id to task_id mapping
                        print(f"      - Queued: {atom_id_str}")

                    # For initial implementation, regenerate ALL tasks in masterplan
                    # as we don't have atom metadata linking yet
                    print(f"    ⚠️  Note: Regenerating all tasks (atom-level regeneration requires metadata)")

                    # Load all tasks for this masterplan
                    tasks = db.query(MasterPlanTask).filter(
                        MasterPlanTask.masterplan_id == uuid.UUID(masterplan_id)
                    ).all()

                    regenerated_count = 0

                    # Regenerate each task (async calls need to be wrapped)
                    import asyncio

                    async def regenerate_tasks():
                        nonlocal regenerated_count

                        for task in tasks[:3]:  # Limit to first 3 tasks for testing
                            try:
                                # Clear previous code
                                task.llm_response = None
                                db.commit()

                                # Regenerate code
                                result = await code_gen_service.generate_code_for_task(task.task_id)

                                if result.get("success"):
                                    # Re-atomize task
                                    atomization_result = atom_service.decompose_task(task.task_id)
                                    regenerated_count += len(atomization_result.get("atoms", []))

                                    print(f"      ✓ Task {task.task_number}: {len(atomization_result.get('atoms', []))} atoms")
                                else:
                                    print(f"      ✗ Task {task.task_number}: failed")

                            except Exception as e:
                                print(f"      ✗ Task {task.task_number}: {e}")

                    # Run async regeneration
                    asyncio.run(regenerate_tasks())

                    # Re-write files to workspace
                    from src.services.file_writer_service import FileWriterService
                    file_writer = FileWriterService(db=db)

                    async def rewrite_files():
                        write_result = await file_writer.write_atoms_to_files(
                            masterplan_id=uuid.UUID(masterplan_id)
                        )

                        if write_result["success"]:
                            print(f"      ✓ Re-wrote {write_result['files_written']} files")
                        else:
                            print(f"      ✗ File writing failed")

                    asyncio.run(rewrite_files())

                    return regenerated_count

                correction_result = self.auto_corrector.correct(
                    code_dir=code_dir,
                    test_file=test_file,
                    module_name=module_name,
                    regenerate_atom_func=regenerate_atom_func,
                )

                auto_correction_applied = True
                correction_iterations = correction_result.iterations_executed
                total_improvement = correction_result.total_improvement
                final_precision = correction_result.final_precision

                print(f"\n✅ Auto-Correction Complete")
                print(f"  Iterations: {correction_iterations}")
                print(f"  Improvement: {initial_precision:.1%} → {final_precision:.1%}")

            else:
                # No auto-correction applied, use precision from repair (or initial)
                final_precision = final_validation.precision

            # Update final_validation if auto-correction was applied
            if auto_correction_applied:
                final_validation = self.code_validator.validate(
                    code_dir=code_dir,
                    test_file=test_file,
                    module_name=module_name,
                )
                final_precision = final_validation.precision

            # Calculate total time
            total_time = (datetime.now() - start_time).total_seconds()

            # Create result
            result = MGE_V2_PipelineResult(
                discovery_id=str(discovery.discovery_id),
                masterplan_id=str(masterplan_id),
                module_name=module_name,
                project_name=project_name,
                total_tasks=total_tasks,
                total_atoms=total_atoms,
                workspace_path=workspace_path,
                code_generation_cost_usd=code_gen_cost,
                code_generation_time=mge_v2_time,
                tests_generated=contract_stats["tests_generated"],
                contracts_extracted=contract_stats["contracts_extracted"],
                test_file=str(test_file),
                initial_precision=initial_precision,
                final_precision=final_precision,
                target_precision=self.target_precision,
                precision_gate_passed=(final_precision >= self.target_precision),
                total_tests=final_validation.total_tests,
                passed_tests=final_validation.passed_tests,
                failed_tests=final_validation.failed_tests,
                must_gate_passed=final_validation.must_gate_passed,
                should_gate_passed=final_validation.should_gate_passed,
                gate_passed=final_validation.gate_passed,
                auto_correction_applied=auto_correction_applied,
                correction_iterations=correction_iterations,
                total_improvement=total_improvement,
                repair_applied=repair_applied,
                repair_iterations=repair_iterations,
                repair_improvement=repair_improvement,
                repair_metrics=repair_metrics_dict,
                total_time=total_time,
                timestamp=start_time,
            )

            # Save results
            self._save_results(result, output_dir)

            # Report final results
            self._report_final_results(result)

            return result

        finally:
            db.close()

    def _extract_domain_from_discovery(self, discovery_doc: str) -> str:
        """Extract domain name from discovery document."""
        # Simple extraction - look for first line with "Domain:" or use default
        lines = discovery_doc.split("\n")
        for line in lines:
            if "domain:" in line.lower():
                return line.split(":")[-1].strip()

        # Default
        return "test_domain"

    def _save_results(self, result: MGE_V2_PipelineResult, output_dir: Path) -> None:
        """Save pipeline results to JSON file."""
        results_file = output_dir / "mge_v2_precision_results.json"

        results_dict = {
            "discovery_id": result.discovery_id,
            "masterplan_id": result.masterplan_id,
            "module_name": result.module_name,
            "project_name": result.project_name,
            "timestamp": result.timestamp.isoformat(),
            "mge_v2_execution": {
                "total_tasks": result.total_tasks,
                "total_atoms": result.total_atoms,
                "workspace_path": result.workspace_path,
                "code_generation_cost_usd": result.code_generation_cost_usd,
                "code_generation_time_seconds": result.code_generation_time,
            },
            "contract_generation": {
                "tests_generated": result.tests_generated,
                "contracts_extracted": result.contracts_extracted,
                "test_file": result.test_file,
            },
            "validation": {
                "initial_precision": result.initial_precision,
                "final_precision": result.final_precision,
                "target_precision": result.target_precision,
                "precision_gate_passed": result.precision_gate_passed,
                "total_tests": result.total_tests,
                "passed_tests": result.passed_tests,
                "failed_tests": result.failed_tests,
            },
            "auto_correction": {
                "applied": result.auto_correction_applied,
                "iterations": result.correction_iterations,
                "improvement": result.total_improvement,
            },
            "repair": {
                "applied": result.repair_applied,
                "iterations": result.repair_iterations,
                "improvement": result.repair_improvement,
                "metrics": result.repair_metrics if result.repair_metrics else {},
            },
            "quality_gates": {
                "must_gate_passed": result.must_gate_passed,
                "should_gate_passed": result.should_gate_passed,
                "gate_passed": result.gate_passed,
            },
            "metrics": {
                "total_time_seconds": result.total_time,
            },
        }

        results_file.write_text(json.dumps(results_dict, indent=2))
        print(f"\n💾 Results saved: {results_file}")

    def _report_final_results(self, result: MGE_V2_PipelineResult) -> None:
        """Print final pipeline results summary."""
        print("\n" + "=" * 80)
        print("📊 FINAL E2E PRECISION RESULTS (MGE V2)")
        print("=" * 80)

        print(f"\n📦 Project: {result.project_name}")
        print(f"📝 Module: {result.module_name}")
        print(f"⏱️  Total Time: {result.total_time:.2f}s")

        print(f"\n🏗️  MGE V2 Execution:")
        print(f"  ✓ MasterPlan ID: {result.masterplan_id}")
        print(f"  ✓ Tasks: {result.total_tasks}")
        print(f"  ✓ Atoms: {result.total_atoms}")
        print(f"  💰 Cost: ${result.code_generation_cost_usd:.4f}")
        print(f"  ⏱️  Time: {result.code_generation_time:.2f}s")
        print(f"  📁 Workspace: {result.workspace_path}")

        print(f"\n📝 Contract Generation:")
        print(f"  ✓ Tests Generated: {result.tests_generated}")
        print(f"  ✓ Contracts Extracted: {result.contracts_extracted}")

        print(f"\n🎯 Precision Validation:")
        precision_icon = "✅" if result.final_precision >= result.target_precision else "⚠️ "
        print(f"  {precision_icon} Final Precision: {result.final_precision:.1%}")
        print(f"  🎯 Target: {result.target_precision:.1%}")
        print(f"  ✓ Tests Passed: {result.passed_tests}/{result.total_tests}")

        if result.repair_applied:
            print(f"\n🔧 Repair Loop (STEP 5):")
            print(f"  ✓ Iterations: {result.repair_iterations}")
            print(f"  📈 Improvement: {result.initial_precision:.1%} → {result.initial_precision + result.repair_improvement:.1%} (+{result.repair_improvement:.1%})")
            if result.repair_metrics:
                learning_metrics = result.repair_metrics.get("learning", {})
                print(f"  🧠 Patterns Reused: {learning_metrics.get('patterns_reused', 0)}")
                print(f"  📚 Similar Patterns Found: {learning_metrics.get('similar_patterns_found', 0)}")
                print(f"  ✅ Tests Fixed: {result.repair_metrics.get('repairs', {}).get('tests_fixed', 0)}")

        if result.auto_correction_applied:
            print(f"\n🔧 Auto-Correction (STEP 6):")
            print(f"  ✓ Iterations: {result.correction_iterations}")
            print(f"  📈 Improvement: {result.initial_precision:.1%} → {result.final_precision:.1%} (+{result.total_improvement:.1%})")

        print(f"\n🚪 Quality Gates:")
        must_icon = "✅" if result.must_gate_passed else "❌"
        should_icon = "✅" if result.should_gate_passed else "❌"
        gate_icon = "✅" if result.gate_passed else "❌"
        print(f"  {must_icon} Must Requirements: {result.must_gate_passed}")
        print(f"  {should_icon} Should Requirements: {result.should_gate_passed}")
        print(f"  {gate_icon} Overall Gate: {'PASSED' if result.gate_passed else 'FAILED'}")

        print("\n" + "=" * 80)
        if result.precision_gate_passed:
            print(f"✅ PRECISION TARGET REACHED: {result.final_precision:.1%} ≥ {result.target_precision:.1%}")
        else:
            print(f"⚠️  PRECISION BELOW TARGET: {result.final_precision:.1%} < {result.target_precision:.1%}")
        print("=" * 80 + "\n")


# Example usage
if __name__ == "__main__":
    from tests.precision.fixtures.sample_prompts import SAMPLE_PROMPT_4

    async def main():
        # Initialize pipeline with MGE V2
        pipeline = E2EPrecisionPipelineMGE_V2(
            auto_correct=True,
            target_precision=0.92,
            max_correction_iterations=5,
        )

        # Execute E2E test with real MGE V2
        result = await pipeline.execute_from_discovery(
            discovery_doc=SAMPLE_PROMPT_4,
            user_id="test_user",
        )

        print(f"\n✅ Pipeline completed!")
        print(f"Final Precision: {result.final_precision:.1%}")
        print(f"Gate Passed: {result.gate_passed}")

    # Run async
    asyncio.run(main())
