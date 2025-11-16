"""
Precision Auto-Corrector

Automated correction loop to improve code precision from initial generation to 92%+ target.

Architecture:
    Generated Code + Test Failures → FailureAnalyzer → Atom Regeneration →
    Re-execution → Precision Check → Loop until ≥92% or max iterations

Features:
    - Iterative correction with max iterations (default: 5)
    - Intelligent atom regeneration strategies
    - Temperature and prompt adjustment based on failure patterns
    - Correction history tracking with metrics
    - Early stopping when target precision reached
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json

# Import precision components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.precision.correction.failure_analyzer import FailureAnalyzer, FailureAnalysis
from tests.precision.validators.code_validator import GeneratedCodeValidator, ValidationResult


@dataclass
class CorrectionIteration:
    """Single correction iteration result."""

    iteration: int
    precision_before: float
    precision_after: float
    failures_analyzed: int
    atoms_regenerated: int
    regeneration_strategy: str
    improvement: float
    timestamp: datetime


@dataclass
class CorrectionResult:
    """Complete auto-correction session result."""

    initial_precision: float
    final_precision: float
    target_precision: float
    iterations_executed: int
    max_iterations: int
    target_reached: bool
    total_improvement: float

    # Iteration history
    iterations: List[CorrectionIteration]

    # Metrics
    total_atoms_regenerated: int
    total_time_seconds: float
    avg_improvement_per_iteration: float

    # Final state
    final_validation: ValidationResult
    timestamp: datetime


class PrecisionAutoCorrector:
    """
    Automated precision correction system.

    Iteratively improves code quality through failure analysis and atom regeneration
    until target precision (default: 92%) is reached or max iterations exhausted.
    """

    def __init__(
        self,
        target_precision: float = 0.92,
        max_iterations: int = 5,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize auto-corrector.

        Args:
            target_precision: Target precision to reach (default: 0.92 = 92%)
            max_iterations: Maximum correction iterations (default: 5)
            anthropic_api_key: API key for code regeneration (optional)
        """
        self.target_precision = target_precision
        self.max_iterations = max_iterations
        self.api_key = anthropic_api_key

        # Initialize components
        self.failure_analyzer = FailureAnalyzer()
        self.code_validator = GeneratedCodeValidator()

        # Correction history
        self.iterations: List[CorrectionIteration] = []

    def correct(
        self,
        code_dir: Path,
        test_file: Path,
        module_name: str,
        regenerate_atom_func: Optional[Callable] = None,
    ) -> CorrectionResult:
        """
        Execute auto-correction loop until target precision or max iterations.

        Args:
            code_dir: Directory with generated code to correct
            test_file: Contract test file to validate against
            module_name: Module name for validation
            regenerate_atom_func: Function to regenerate atoms (optional, uses mock if None)

        Returns:
            CorrectionResult with complete correction session metrics
        """
        print("\n" + "=" * 70)
        print(f"🔧 AUTO-CORRECTION SESSION: {module_name}")
        print(f"🎯 Target: {self.target_precision:.1%} precision")
        print(f"🔄 Max Iterations: {self.max_iterations}")
        print("=" * 70)

        start_time = datetime.now()

        # Initial validation
        print("\n📊 Initial Validation...")
        initial_validation = self.code_validator.validate(
            code_dir=code_dir,
            test_file=test_file,
            module_name=module_name,
        )

        initial_precision = initial_validation.precision
        current_precision = initial_precision

        print(f"Initial Precision: {initial_precision:.1%}")

        # Check if already at target
        if initial_precision >= self.target_precision:
            print(f"\n✅ Already at target precision ({initial_precision:.1%} ≥ {self.target_precision:.1%})")
            return self._create_result(
                initial_precision=initial_precision,
                final_precision=initial_precision,
                iterations_executed=0,
                target_reached=True,
                final_validation=initial_validation,
                start_time=start_time,
            )

        # Correction loop
        iteration = 0
        total_atoms_regenerated = 0
        current_validation = initial_validation  # Initialize for early breaks

        while iteration < self.max_iterations and current_precision < self.target_precision:
            iteration += 1

            print("\n" + "-" * 70)
            print(f"🔄 Iteration {iteration}/{self.max_iterations}")
            print("-" * 70)

            # Step 1: Analyze failures
            print("  1️⃣ Analyzing failures...")
            test_results = initial_validation.test_results if iteration == 1 else current_validation.test_results

            failures = self.failure_analyzer.analyze_failures(test_results, code_dir)

            print(f"     Found {len(failures)} failures to address")

            if len(failures) == 0:
                print("     No failures to correct!")
                break

            # Step 2: Select regeneration strategy
            strategy = self._select_strategy(iteration, failures)
            print(f"  2️⃣ Strategy: {strategy}")

            # Step 3: Regenerate problematic atoms
            print("  3️⃣ Regenerating atoms...")
            atoms_regenerated = self._regenerate_atoms(
                failures=failures,
                code_dir=code_dir,
                strategy=strategy,
                regenerate_func=regenerate_atom_func,
            )

            total_atoms_regenerated += atoms_regenerated
            print(f"     Regenerated {atoms_regenerated} atoms")

            # Step 4: Re-validate
            print("  4️⃣ Re-validating code...")
            current_validation = self.code_validator.validate(
                code_dir=code_dir,
                test_file=test_file,
                module_name=module_name,
            )

            precision_before = current_precision
            current_precision = current_validation.precision
            improvement = current_precision - precision_before

            print(f"     Precision: {precision_before:.1%} → {current_precision:.1%} ({improvement:+.1%})")

            # Record iteration
            self.iterations.append(
                CorrectionIteration(
                    iteration=iteration,
                    precision_before=precision_before,
                    precision_after=current_precision,
                    failures_analyzed=len(failures),
                    atoms_regenerated=atoms_regenerated,
                    regeneration_strategy=strategy,
                    improvement=improvement,
                    timestamp=datetime.now(),
                )
            )

            # Check if target reached
            if current_precision >= self.target_precision:
                print(f"\n🎉 Target precision reached! ({current_precision:.1%} ≥ {self.target_precision:.1%})")
                break

        # Final result
        target_reached = current_precision >= self.target_precision

        result = self._create_result(
            initial_precision=initial_precision,
            final_precision=current_precision,
            iterations_executed=iteration,
            target_reached=target_reached,
            final_validation=current_validation,
            start_time=start_time,
            total_atoms_regenerated=total_atoms_regenerated,
        )

        self._report_final_result(result)

        return result

    def _select_strategy(self, iteration: int, failures: List[FailureAnalysis]) -> str:
        """
        Select regeneration strategy based on iteration and failure patterns.

        Args:
            iteration: Current iteration number (1-based)
            failures: List of failure analyses

        Returns:
            Strategy name
        """
        # First iteration: Standard regeneration
        if iteration == 1:
            return "standard"

        # Check failure severity distribution
        critical_count = sum(1 for f in failures if f.severity == "critical")
        total_count = len(failures)

        # High critical percentage: Enhanced context
        if critical_count / total_count > 0.5:
            return "enhanced_context"

        # Later iterations: More aggressive strategies
        if iteration >= 3:
            return "temperature_adjusted"

        return "improved_prompts"

    def _regenerate_atoms(
        self,
        failures: List[FailureAnalysis],
        code_dir: Path,
        strategy: str,
        regenerate_func: Optional[Callable],
    ) -> int:
        """
        Regenerate problematic atoms using selected strategy.

        Args:
            failures: Failure analyses identifying problematic atoms
            code_dir: Code directory to update
            strategy: Regeneration strategy to use
            regenerate_func: Optional custom regeneration function

        Returns:
            Number of atoms regenerated
        """
        # Get unique atoms to regenerate (sorted by priority)
        atoms_to_regenerate = set()
        for failure in failures:
            atoms_to_regenerate.update(failure.suspected_atoms)

        # Use custom regeneration function if provided
        if regenerate_func:
            return regenerate_func(atoms_to_regenerate, strategy)

        # Mock regeneration (for testing)
        return self._mock_regenerate(atoms_to_regenerate, code_dir, strategy)

    def _mock_regenerate(
        self, atoms: set, code_dir: Path, strategy: str
    ) -> int:
        """
        Mock atom regeneration for testing.

        In production, this would call MGE V2 to regenerate specific atoms.

        Args:
            atoms: Set of atom IDs to regenerate
            code_dir: Code directory
            strategy: Regeneration strategy

        Returns:
            Number of atoms regenerated
        """
        # TODO: Integrate with MGE V2 atom regeneration
        # This is a placeholder that simulates regeneration

        print(f"     [MOCK] Regenerating {len(atoms)} atoms with strategy: {strategy}")

        # In real implementation:
        # 1. Extract atom metadata from MGE V2
        # 2. Generate improved prompts based on failure context
        # 3. Adjust temperature/parameters based on strategy
        # 4. Regenerate code for each atom
        # 5. Update code_dir with new implementations

        return len(atoms)

    def _create_result(
        self,
        initial_precision: float,
        final_precision: float,
        iterations_executed: int,
        target_reached: bool,
        final_validation: ValidationResult,
        start_time: datetime,
        total_atoms_regenerated: int = 0,
    ) -> CorrectionResult:
        """Create CorrectionResult from session data."""

        total_time = (datetime.now() - start_time).total_seconds()
        total_improvement = final_precision - initial_precision

        avg_improvement = (
            total_improvement / iterations_executed if iterations_executed > 0 else 0.0
        )

        return CorrectionResult(
            initial_precision=initial_precision,
            final_precision=final_precision,
            target_precision=self.target_precision,
            iterations_executed=iterations_executed,
            max_iterations=self.max_iterations,
            target_reached=target_reached,
            total_improvement=total_improvement,
            iterations=self.iterations,
            total_atoms_regenerated=total_atoms_regenerated,
            total_time_seconds=total_time,
            avg_improvement_per_iteration=avg_improvement,
            final_validation=final_validation,
            timestamp=start_time,
        )

    def _report_final_result(self, result: CorrectionResult) -> None:
        """Print final correction session report."""

        print("\n" + "=" * 70)
        print("📊 AUTO-CORRECTION FINAL REPORT")
        print("=" * 70)

        print(f"\n🎯 Precision Journey:")
        print(f"  Initial:  {result.initial_precision:.1%}")
        print(f"  Final:    {result.final_precision:.1%}")
        print(f"  Target:   {result.target_precision:.1%}")
        print(f"  Improvement: {result.total_improvement:+.1%}")

        print(f"\n🔄 Iteration Summary:")
        print(f"  Executed: {result.iterations_executed}/{result.max_iterations}")
        print(f"  Avg Improvement: {result.avg_improvement_per_iteration:+.1%} per iteration")

        print(f"\n🧬 Atoms Regenerated:")
        print(f"  Total: {result.total_atoms_regenerated}")

        print(f"\n⏱️  Time:")
        print(f"  Total: {result.total_time_seconds:.2f}s")

        print(f"\n🚪 Final Quality Gates:")
        must_icon = "✅" if result.final_validation.must_gate_passed else "❌"
        should_icon = "✅" if result.final_validation.should_gate_passed else "❌"
        print(f"  {must_icon} Must Requirements: {result.final_validation.must_tests_passed}/{result.final_validation.must_tests_total}")
        print(f"  {should_icon} Should Requirements: {result.final_validation.should_tests_passed}/{result.final_validation.should_tests_total}")

        # Final verdict
        print("\n" + "=" * 70)
        if result.target_reached:
            print(f"✅ SUCCESS - Target precision reached ({result.final_precision:.1%} ≥ {result.target_precision:.1%})")
        else:
            print(f"⚠️  INCOMPLETE - Target not reached after {result.iterations_executed} iterations")
            print(f"   Need {result.target_precision - result.final_precision:.1%} more precision")
        print("=" * 70 + "\n")

    def save_correction_history(self, output_file: Path) -> None:
        """
        Save correction session history to JSON file.

        Args:
            output_file: Path to output JSON file
        """
        history_data = {
            "iterations": [
                {
                    "iteration": it.iteration,
                    "precision_before": it.precision_before,
                    "precision_after": it.precision_after,
                    "failures_analyzed": it.failures_analyzed,
                    "atoms_regenerated": it.atoms_regenerated,
                    "strategy": it.regeneration_strategy,
                    "improvement": it.improvement,
                    "timestamp": it.timestamp.isoformat(),
                }
                for it in self.iterations
            ]
        }

        output_file.write_text(json.dumps(history_data, indent=2))
        print(f"💾 Correction history saved: {output_file}")


# Example usage
if __name__ == "__main__":
    from pathlib import Path

    # Initialize auto-corrector
    corrector = PrecisionAutoCorrector(
        target_precision=0.92,
        max_iterations=5,
    )

    # Mock paths (in production, these would be real generated code)
    code_dir = Path("/tmp/generated_code/example")
    test_file = Path("/tmp/contract_tests/test_example.py")

    # Execute correction
    result = corrector.correct(
        code_dir=code_dir,
        test_file=test_file,
        module_name="example",
    )

    print(f"\n✅ Correction complete!")
    print(f"Final Precision: {result.final_precision:.1%}")
    print(f"Target Reached: {result.target_reached}")
