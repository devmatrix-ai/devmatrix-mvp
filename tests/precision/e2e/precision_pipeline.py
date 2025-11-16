"""
E2E Precision Pipeline

Orchestrates the complete pipeline: Discovery → Contract Tests → MGE V2 → Validation → Precision

Architecture:
    Discovery Doc → ContractTestGenerator → MGE V2 Code Generation →
    GeneratedCodeValidator → Precision Measurement → (Optional) Auto-Correction

This is the CORRECT measurement point - tests generated code quality, not test quality.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import tempfile
import shutil

# Import our precision components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.precision.generators.contract_test_generator import ContractTestGenerator
from tests.precision.validators.code_validator import GeneratedCodeValidator


@dataclass
class PipelineResult:
    """Complete E2E pipeline execution result."""

    # Discovery inputs
    discovery_doc: str
    module_name: str

    # Contract generation
    tests_generated: int
    contracts_extracted: int
    test_file: str

    # Code generation (MGE V2)
    code_generated: bool
    code_generation_time: float
    code_directory: str

    # Validation
    precision: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    gate_passed: bool
    must_gate_passed: bool
    should_gate_passed: bool

    # Overall metrics
    total_time: float
    timestamp: datetime

    # Auto-correction (if applied)
    auto_correction_applied: bool = False
    correction_iterations: int = 0
    initial_precision: float = 0.0
    final_precision: float = 0.0


class E2EPrecisionPipeline:
    """
    End-to-end precision measurement pipeline.

    Measures precision of GENERATED code (not test generation quality).
    This is the CORRECT approach identified by user.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        auto_correct: bool = False,
        target_precision: float = 0.92,
        max_iterations: int = 5,
    ):
        """
        Initialize E2E pipeline.

        Args:
            anthropic_api_key: API key for Claude (test generation)
            auto_correct: Enable auto-correction loop
            target_precision: Target precision (default: 92%)
            max_iterations: Max correction iterations (default: 5)
        """
        self.contract_generator = ContractTestGenerator(api_key=anthropic_api_key)
        self.code_validator = GeneratedCodeValidator()
        self.auto_correct = auto_correct
        self.target_precision = target_precision
        self.max_iterations = max_iterations

    def execute(
        self,
        discovery_doc: str,
        module_name: str,
        output_dir: Optional[Path] = None,
        mge_v2_enabled: bool = False,
    ) -> PipelineResult:
        """
        Execute complete E2E precision measurement pipeline.

        Args:
            discovery_doc: Markdown discovery document with requirements
            module_name: Name of module (e.g., "task_management")
            output_dir: Where to write outputs (default: temp dir)
            mge_v2_enabled: Use real MGE V2 for code generation (default: False, uses mock)

        Returns:
            PipelineResult with complete metrics
        """
        print("\n" + "=" * 70)
        print(f"🚀 E2E PRECISION PIPELINE: {module_name}")
        print("=" * 70)

        start_time = datetime.now()

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix=f"e2e_precision_{module_name}_"))
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📁 Output Directory: {output_dir}")

        try:
            # Step 1: Generate contract tests from discovery doc
            print("\n" + "-" * 70)
            print("STEP 1: Contract Test Generation")
            print("-" * 70)

            test_dir = output_dir / "tests"
            contract_stats = self.contract_generator.generate_from_discovery(
                discovery_doc=discovery_doc,
                output_dir=test_dir,
                module_name=module_name,
            )

            test_file = test_dir / f"test_{module_name}_contracts.py"
            print(f"✅ Generated {contract_stats['tests_generated']} contract tests")

            # Step 2: Generate code using MGE V2
            print("\n" + "-" * 70)
            print("STEP 2: Code Generation (MGE V2)")
            print("-" * 70)

            code_dir = output_dir / "code"
            code_gen_start = datetime.now()

            if mge_v2_enabled:
                # TODO: Integrate real MGE V2 pipeline
                code_generated = self._generate_code_mge_v2(
                    discovery_doc, code_dir, module_name
                )
            else:
                # Mock code generation for testing
                print("⚠️  Using MOCK code generation (MGE V2 not enabled)")
                code_generated = self._generate_code_mock(code_dir, module_name)

            code_gen_time = (datetime.now() - code_gen_start).total_seconds()
            print(f"✅ Code generated in {code_gen_time:.2f}s")

            # Step 3: Validate generated code with contract tests
            print("\n" + "-" * 70)
            print("STEP 3: Code Validation")
            print("-" * 70)

            validation_result = self.code_validator.validate(
                code_dir=code_dir,
                test_file=test_file,
                module_name=module_name,
            )

            initial_precision = validation_result.precision

            # Step 4: Auto-correction (if enabled and needed)
            auto_correction_applied = False
            correction_iterations = 0
            final_precision = initial_precision

            if self.auto_correct and validation_result.precision < self.target_precision:
                print("\n" + "-" * 70)
                print("STEP 4: Auto-Correction Loop")
                print("-" * 70)
                print(
                    f"Initial precision: {initial_precision:.1%} < target {self.target_precision:.1%}"
                )
                print("Starting auto-correction...")

                # TODO: Implement auto-correction with FailureAnalyzer + AutoCorrector
                print("⚠️  Auto-correction not yet implemented")
                auto_correction_applied = False
                correction_iterations = 0
                final_precision = initial_precision

            else:
                final_precision = validation_result.precision

            # Calculate total time
            total_time = (datetime.now() - start_time).total_seconds()

            # Create pipeline result
            result = PipelineResult(
                discovery_doc=discovery_doc[:200] + "...",  # Truncate for storage
                module_name=module_name,
                tests_generated=contract_stats["tests_generated"],
                contracts_extracted=contract_stats["contracts_extracted"],
                test_file=str(test_file),
                code_generated=code_generated,
                code_generation_time=code_gen_time,
                code_directory=str(code_dir),
                precision=validation_result.precision,
                total_tests=validation_result.total_tests,
                passed_tests=validation_result.passed_tests,
                failed_tests=validation_result.failed_tests,
                gate_passed=validation_result.gate_passed,
                must_gate_passed=validation_result.must_gate_passed,
                should_gate_passed=validation_result.should_gate_passed,
                total_time=total_time,
                timestamp=start_time,
                auto_correction_applied=auto_correction_applied,
                correction_iterations=correction_iterations,
                initial_precision=initial_precision,
                final_precision=final_precision,
            )

            # Save results
            self._save_results(result, output_dir)

            # Report final results
            self._report_final_results(result)

            return result

        except Exception as e:
            print(f"\n❌ Pipeline failed with error: {e}")
            raise

    def _generate_code_mock(self, code_dir: Path, module_name: str) -> bool:
        """
        Mock code generation for testing (replaces MGE V2).

        In real implementation, this will call MGE V2 pipeline.

        Args:
            code_dir: Where to write generated code
            module_name: Module name

        Returns:
            True if successful
        """
        code_dir.mkdir(parents=True, exist_ok=True)

        # Generate simple mock Python module
        mock_code = f'''"""
Generated code for {module_name}

This is MOCK code for testing the precision pipeline.
In production, this will be generated by MGE V2.
"""

class MockAPI:
    """Mock API implementation."""

    def __init__(self):
        self.items = {{}}
        self.next_id = 1

    def create(self, **kwargs):
        """Create new item."""
        item = {{"id": self.next_id, **kwargs}}
        self.items[self.next_id] = item
        self.next_id += 1
        return item

    def get(self, item_id: int):
        """Get item by ID."""
        return self.items.get(item_id)

    def list_all(self):
        """List all items."""
        return list(self.items.values())

    def delete(self, item_id: int):
        """Delete item."""
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False
'''

        # Write mock code file
        (code_dir / f"{module_name}.py").write_text(mock_code)
        (code_dir / "__init__.py").write_text(f"from .{module_name} import MockAPI\n")

        print(f"  📝 Mock code generated: {code_dir}/{module_name}.py")
        return True

    def _generate_code_mge_v2(
        self, discovery_doc: str, code_dir: Path, module_name: str
    ) -> bool:
        """
        Generate code using real MGE V2 pipeline.

        TODO: Implement integration with MGE V2.

        Args:
            discovery_doc: Discovery document
            code_dir: Output directory
            module_name: Module name

        Returns:
            True if successful
        """
        # TODO: Integrate with MGE V2 orchestration service
        # from src.services.mge_v2_orchestration_service import MGEV2OrchestrationService
        #
        # orchestrator = MGEV2OrchestrationService(db=...)
        # result = await orchestrator.execute_full_pipeline(
        #     discovery_doc=discovery_doc,
        #     output_dir=code_dir,
        # )
        #
        # return result.success

        raise NotImplementedError("MGE V2 integration not yet implemented")

    def _save_results(self, result: PipelineResult, output_dir: Path) -> None:
        """
        Save pipeline results to JSON file.

        Args:
            result: Pipeline result
            output_dir: Output directory
        """
        results_file = output_dir / "pipeline_results.json"

        results_dict = {
            "module_name": result.module_name,
            "timestamp": result.timestamp.isoformat(),
            "contract_generation": {
                "tests_generated": result.tests_generated,
                "contracts_extracted": result.contracts_extracted,
                "test_file": result.test_file,
            },
            "code_generation": {
                "success": result.code_generated,
                "time_seconds": result.code_generation_time,
                "directory": result.code_directory,
            },
            "validation": {
                "precision": result.precision,
                "total_tests": result.total_tests,
                "passed_tests": result.passed_tests,
                "failed_tests": result.failed_tests,
                "gate_passed": result.gate_passed,
                "must_gate_passed": result.must_gate_passed,
                "should_gate_passed": result.should_gate_passed,
            },
            "auto_correction": {
                "applied": result.auto_correction_applied,
                "iterations": result.correction_iterations,
                "initial_precision": result.initial_precision,
                "final_precision": result.final_precision,
            },
            "metrics": {
                "total_time_seconds": result.total_time,
            },
        }

        results_file.write_text(json.dumps(results_dict, indent=2))
        print(f"\n💾 Results saved: {results_file}")

    def _report_final_results(self, result: PipelineResult) -> None:
        """
        Print final pipeline results summary.

        Args:
            result: Pipeline result
        """
        print("\n" + "=" * 70)
        print("📊 FINAL RESULTS")
        print("=" * 70)

        print(f"\n📦 Module: {result.module_name}")
        print(f"⏱️  Total Time: {result.total_time:.2f}s")

        print(f"\n📝 Contract Generation:")
        print(f"  ✓ Tests Generated: {result.tests_generated}")
        print(f"  ✓ Contracts Extracted: {result.contracts_extracted}")

        print(f"\n💻 Code Generation:")
        status = "✓" if result.code_generated else "✗"
        print(f"  {status} Success: {result.code_generated}")
        print(f"  ⏱️  Time: {result.code_generation_time:.2f}s")

        print(f"\n🧪 Validation:")
        precision_icon = "✅" if result.precision >= 0.92 else "⚠️ "
        print(f"  {precision_icon} Precision: {result.precision:.1%}")
        print(f"  ✓ Tests Passed: {result.passed_tests}/{result.total_tests}")

        gate_icon = "✅" if result.gate_passed else "❌"
        print(f"\n🚪 Quality Gates: {gate_icon}")
        must_icon = "✅" if result.must_gate_passed else "❌"
        should_icon = "✅" if result.should_gate_passed else "❌"
        print(f"  {must_icon} Must Requirements: {result.must_gate_passed}")
        print(f"  {should_icon} Should Requirements: {result.should_gate_passed}")

        if result.auto_correction_applied:
            print(f"\n🔧 Auto-Correction:")
            print(f"  ✓ Iterations: {result.correction_iterations}")
            print(f"  📈 Improvement: {result.initial_precision:.1%} → {result.final_precision:.1%}")

        print("\n" + "=" * 70)

        # Final verdict
        if result.gate_passed:
            print("✅ PIPELINE SUCCESS - Quality gates passed!")
        else:
            print("❌ PIPELINE FAILED - Quality gates not met")
            if result.precision < 0.92:
                print(f"   Need {0.92 - result.precision:.1%} more precision to reach 92% target")

        print("=" * 70 + "\n")


# Example usage
if __name__ == "__main__":
    from tests.precision.fixtures.sample_prompts import SAMPLE_PROMPT_4

    # Initialize pipeline
    pipeline = E2EPrecisionPipeline(
        auto_correct=False,  # Enable auto-correction
        target_precision=0.92,
        max_iterations=5,
    )

    # Execute E2E test
    result = pipeline.execute(
        discovery_doc=SAMPLE_PROMPT_4,
        module_name="task_management",
        mge_v2_enabled=False,  # Use mock code generation
    )

    print(f"\n✅ Pipeline completed!")
    print(f"Final Precision: {result.precision:.1%}")
    print(f"Gate Passed: {result.gate_passed}")
