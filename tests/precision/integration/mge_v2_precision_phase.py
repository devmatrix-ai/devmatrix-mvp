"""
MGE V2 Phase 8: Precision Validation

Integrates precision measurement and auto-correction into MGE V2 pipeline.

Architecture:
    Phase 8 executes after Phase 6 (Code Generation) to validate and improve
    precision of generated code to 92%+ target.

    Discovery → Contract Tests → Code Validation → Auto-Correction → Metrics

Features:
    - Automated contract test generation from discovery documents
    - Code validation against contract tests
    - Auto-correction loop to reach 92%+ precision
    - Comprehensive metrics tracking and storage
    - Integration with existing MGE V2 pipeline
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

# Import precision components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.precision.generators.contract_test_generator import ContractTestGenerator
from tests.precision.validators.code_validator import GeneratedCodeValidator
from tests.precision.correction.auto_corrector import PrecisionAutoCorrector


@dataclass
class Phase8Result:
    """Phase 8 execution result."""

    masterplan_id: str
    module_name: str

    # Contract generation
    tests_generated: int
    contracts_extracted: int

    # Validation
    initial_precision: float
    final_precision: float
    target_precision: float
    precision_gate_passed: bool

    # Auto-correction
    auto_correction_applied: bool
    correction_iterations: int
    total_improvement: float

    # Quality gates
    must_gate_passed: bool
    should_gate_passed: bool
    gate_passed: bool

    # Metrics
    total_time_seconds: float
    timestamp: datetime

    # File paths
    code_directory: str
    test_file: str
    metrics_file: str


class MGEV2PrecisionPhase:
    """
    Phase 8: Precision Validation for MGE V2.

    Validates and improves generated code precision through:
    1. Contract test generation from discovery documents
    2. Code validation against contract tests
    3. Automated correction to reach 92%+ precision target
    4. Comprehensive metrics tracking
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        target_precision: float = 0.92,
        max_correction_iterations: int = 5,
        auto_correct: bool = True,
    ):
        """
        Initialize Phase 8.

        Args:
            anthropic_api_key: API key for contract generation
            target_precision: Target precision (default: 0.92 = 92%)
            max_correction_iterations: Max auto-correction iterations (default: 5)
            auto_correct: Enable auto-correction (default: True)
        """
        self.target_precision = target_precision
        self.auto_correct = auto_correct

        # Initialize precision components
        self.contract_generator = ContractTestGenerator(api_key=anthropic_api_key)
        self.code_validator = GeneratedCodeValidator()
        self.auto_corrector = PrecisionAutoCorrector(
            target_precision=target_precision,
            max_iterations=max_correction_iterations,
            anthropic_api_key=anthropic_api_key,
        )

    async def execute_phase_8(
        self,
        masterplan_id: str,
        discovery_doc: str,
        code_directory: Path,
        module_name: str,
        output_dir: Path,
    ) -> Phase8Result:
        """
        Execute Phase 8: Precision Validation.

        Args:
            masterplan_id: ID of masterplan being validated
            discovery_doc: Discovery document with requirements
            code_directory: Directory with generated code from Phase 6
            module_name: Module name for code
            output_dir: Directory for test files and metrics

        Returns:
            Phase8Result with complete precision metrics
        """
        print("\n" + "=" * 70)
        print(f"🎯 MGE V2 PHASE 8: PRECISION VALIDATION")
        print(f"📦 MasterPlan: {masterplan_id}")
        print(f"🎯 Target: {self.target_precision:.1%} precision")
        print("=" * 70)

        start_time = datetime.now()

        # Step 1: Generate contract tests from discovery document
        print("\n" + "-" * 70)
        print("STEP 1: Contract Test Generation")
        print("-" * 70)

        test_dir = output_dir / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)

        contract_stats = self.contract_generator.generate_from_discovery(
            discovery_doc=discovery_doc,
            output_dir=test_dir,
            module_name=module_name,
        )

        test_file = test_dir / f"test_{module_name}_contracts.py"
        print(f"✅ Generated {contract_stats['tests_generated']} contract tests")

        # Step 2: Validate generated code
        print("\n" + "-" * 70)
        print("STEP 2: Code Validation")
        print("-" * 70)

        validation_result = self.code_validator.validate(
            code_dir=code_directory,
            test_file=test_file,
            module_name=module_name,
        )

        initial_precision = validation_result.precision
        print(f"Initial Precision: {initial_precision:.1%}")

        # Step 3: Auto-correction (if enabled and needed)
        auto_correction_applied = False
        correction_iterations = 0
        total_improvement = 0.0
        final_precision = initial_precision

        if self.auto_correct and initial_precision < self.target_precision:
            print("\n" + "-" * 70)
            print("STEP 3: Auto-Correction")
            print("-" * 70)

            correction_result = self.auto_corrector.correct(
                code_dir=code_directory,
                test_file=test_file,
                module_name=module_name,
            )

            auto_correction_applied = True
            correction_iterations = correction_result.iterations_executed
            total_improvement = correction_result.total_improvement
            final_precision = correction_result.final_precision

            print(f"✅ Correction complete: {initial_precision:.1%} → {final_precision:.1%}")

        else:
            final_precision = initial_precision

        # Get final validation (re-validate if auto-correction was applied)
        final_validation = validation_result
        if auto_correction_applied:
            final_validation = self.code_validator.validate(
                code_dir=code_directory,
                test_file=test_file,
                module_name=module_name,
            )

        # Step 4: Save precision metrics
        print("\n" + "-" * 70)
        print("STEP 4: Save Metrics")
        print("-" * 70)

        metrics_file = output_dir / f"precision_metrics_{masterplan_id}.json"
        self._save_precision_metrics(
            masterplan_id=masterplan_id,
            module_name=module_name,
            contract_stats=contract_stats,
            initial_precision=initial_precision,
            final_precision=final_precision,
            auto_correction_applied=auto_correction_applied,
            correction_iterations=correction_iterations,
            total_improvement=total_improvement,
            validation_result=final_validation,
            metrics_file=metrics_file,
        )

        print(f"💾 Metrics saved: {metrics_file}")

        # Calculate total time
        total_time = (datetime.now() - start_time).total_seconds()

        # Create Phase 8 result
        result = Phase8Result(
            masterplan_id=masterplan_id,
            module_name=module_name,
            tests_generated=contract_stats["tests_generated"],
            contracts_extracted=contract_stats["contracts_extracted"],
            initial_precision=initial_precision,
            final_precision=final_precision,
            target_precision=self.target_precision,
            precision_gate_passed=(final_precision >= self.target_precision),
            auto_correction_applied=auto_correction_applied,
            correction_iterations=correction_iterations,
            total_improvement=total_improvement,
            must_gate_passed=final_validation.must_gate_passed,
            should_gate_passed=final_validation.should_gate_passed,
            gate_passed=final_validation.gate_passed,
            total_time_seconds=total_time,
            timestamp=start_time,
            code_directory=str(code_directory),
            test_file=str(test_file),
            metrics_file=str(metrics_file),
        )

        # Report final result
        self._report_phase_8_result(result)

        return result

    def _save_precision_metrics(
        self,
        masterplan_id: str,
        module_name: str,
        contract_stats: Dict[str, Any],
        initial_precision: float,
        final_precision: float,
        auto_correction_applied: bool,
        correction_iterations: int,
        total_improvement: float,
        validation_result: Any,
        metrics_file: Path,
    ) -> None:
        """Save precision metrics to JSON file."""

        metrics = {
            "masterplan_id": masterplan_id,
            "module_name": module_name,
            "phase": 8,
            "phase_name": "precision_validation",
            "timestamp": datetime.now().isoformat(),
            "contract_generation": {
                "tests_generated": contract_stats["tests_generated"],
                "contracts_extracted": contract_stats["contracts_extracted"],
            },
            "validation": {
                "initial_precision": initial_precision,
                "final_precision": final_precision,
                "target_precision": self.target_precision,
                "precision_gate_passed": (final_precision >= self.target_precision),
                "total_tests": validation_result.total_tests,
                "passed_tests": validation_result.passed_tests,
                "failed_tests": validation_result.failed_tests,
            },
            "auto_correction": {
                "applied": auto_correction_applied,
                "iterations": correction_iterations,
                "improvement": total_improvement,
            },
            "quality_gates": {
                "must_gate_passed": validation_result.must_gate_passed,
                "should_gate_passed": validation_result.should_gate_passed,
                "gate_passed": validation_result.gate_passed,
            },
        }

        metrics_file.write_text(json.dumps(metrics, indent=2))

    def _report_phase_8_result(self, result: Phase8Result) -> None:
        """Print Phase 8 final result summary."""

        print("\n" + "=" * 70)
        print("📊 PHASE 8 FINAL RESULT")
        print("=" * 70)

        print(f"\n📦 MasterPlan: {result.masterplan_id}")
        print(f"📝 Module: {result.module_name}")
        print(f"⏱️  Total Time: {result.total_time_seconds:.2f}s")

        print(f"\n🎯 Precision Metrics:")
        print(f"  Initial:  {result.initial_precision:.1%}")
        print(f"  Final:    {result.final_precision:.1%}")
        print(f"  Target:   {result.target_precision:.1%}")

        if result.auto_correction_applied:
            print(f"\n🔧 Auto-Correction:")
            print(f"  Iterations: {result.correction_iterations}")
            print(f"  Improvement: {result.total_improvement:+.1%}")

        print(f"\n🚪 Quality Gates:")
        must_icon = "✅" if result.must_gate_passed else "❌"
        should_icon = "✅" if result.should_gate_passed else "❌"
        gate_icon = "✅" if result.gate_passed else "❌"
        print(f"  {must_icon} Must Requirements")
        print(f"  {should_icon} Should Requirements")
        print(f"  {gate_icon} Overall Gate: {'PASSED' if result.gate_passed else 'FAILED'}")

        print(f"\n💾 Artifacts:")
        print(f"  Code: {result.code_directory}")
        print(f"  Tests: {result.test_file}")
        print(f"  Metrics: {result.metrics_file}")

        print("\n" + "=" * 70)
        if result.precision_gate_passed:
            print(f"✅ PHASE 8 SUCCESS - Precision target reached ({result.final_precision:.1%} ≥ {result.target_precision:.1%})")
        else:
            print(f"⚠️  PHASE 8 INCOMPLETE - Precision below target ({result.final_precision:.1%} < {result.target_precision:.1%})")
        print("=" * 70 + "\n")


# Example usage
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    async def main():
        # Initialize Phase 8
        phase8 = MGEV2PrecisionPhase(
            target_precision=0.92,
            max_correction_iterations=5,
            auto_correct=True,
        )

        # Mock data
        masterplan_id = "mp-test-001"
        discovery_doc = "Sample discovery document with requirements..."
        code_directory = Path("/tmp/generated_code/example")
        module_name = "example"
        output_dir = Path("/tmp/phase8_output")

        # Execute Phase 8
        result = await phase8.execute_phase_8(
            masterplan_id=masterplan_id,
            discovery_doc=discovery_doc,
            code_directory=code_directory,
            module_name=module_name,
            output_dir=output_dir,
        )

        print(f"\n✅ Phase 8 complete!")
        print(f"Final Precision: {result.final_precision:.1%}")
        print(f"Gate Passed: {result.gate_passed}")

    asyncio.run(main())
