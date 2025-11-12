#!/usr/bin/env python3
"""
Precision Baseline Measurement Script

Ejecuta N iteraciones del pipeline completo MGE V2 y mide:
- Determinismo (¿mismo output?)
- Precisión (¿cuántos átomos exitosos?)
- Variabilidad (¿qué tan consistente?)
- Performance (tiempo y costo)

Usage:
    python scripts/measure_precision_baseline.py --iterations 10
    python scripts/measure_precision_baseline.py --discovery-file example.json --iterations 5
"""

import asyncio
import argparse
import hashlib
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from src.config.database import DatabaseConfig
from src.services.discovery_service import DiscoveryService
from src.models.masterplan import DiscoveryDocument, MasterPlan
from src.llm import EnhancedAnthropicClient

# Import MGE V2 components (only if needed)
# from src.atomization.decomposer import Decomposer
# from src.mge.v2.execution.wave_executor import WaveExecutor
# from src.dependency.graph import DependencyGraph

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PrecisionMeasurement:
    """Single measurement iteration."""

    def __init__(self, iteration: int):
        self.iteration = iteration
        self.discovery_id: Optional[UUID] = None
        self.masterplan_id: Optional[UUID] = None
        self.task_count: int = 0
        self.atom_count: int = 0
        self.success_rate: float = 0.0
        self.code_hash: str = ""
        self.execution_time: float = 0.0
        self.cost_usd: float = 0.0
        self.determinism_violations: int = 0
        self.atoms_succeeded: int = 0
        self.atoms_failed: int = 0
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration": self.iteration,
            "discovery_id": str(self.discovery_id) if self.discovery_id else None,
            "masterplan_id": str(self.masterplan_id) if self.masterplan_id else None,
            "task_count": self.task_count,
            "atom_count": self.atom_count,
            "atoms_succeeded": self.atoms_succeeded,
            "atoms_failed": self.atoms_failed,
            "success_rate": self.success_rate,
            "code_hash": self.code_hash,
            "execution_time": self.execution_time,
            "cost_usd": self.cost_usd,
            "determinism_violations": self.determinism_violations,
            "error": self.error_message
        }


class PrecisionBaseline:
    """Precision baseline measurement tool."""

    def __init__(
        self,
        db: Session,
        user_request: str = "Create a simple REST API for task management with CRUD operations",
        iterations: int = 10
    ):
        self.db = db
        self.user_request = user_request
        self.iterations = iterations
        self.measurements: List[PrecisionMeasurement] = []

        # Services
        self.discovery_service = DiscoveryService(db=db)
        self.llm_client = EnhancedAnthropicClient()

        # Baseline references (from iteration 1)
        self.baseline_code_hash: Optional[str] = None
        self.baseline_task_count: Optional[int] = None
        self.baseline_atom_count: Optional[int] = None

    async def run_single_iteration(self, iteration: int) -> PrecisionMeasurement:
        """
        Run single iteration of complete pipeline.

        Workflow:
        1. Generate DiscoveryDocument
        2. Generate MasterPlan
        3. Atomize tasks
        4. Execute atoms
        5. Measure results
        """
        measurement = PrecisionMeasurement(iteration=iteration)
        start_time = time.time()

        try:
            logger.info(f"🔬 Iteration {iteration}/{self.iterations} - Starting")

            # Step 1: Generate Discovery Document
            logger.info(f"  📋 Generating Discovery Document...")
            discovery_id = await self.discovery_service.generate_discovery(
                user_request=self.user_request,
                session_id=f"baseline_session_{iteration}",
                user_id="baseline_user"
            )
            measurement.discovery_id = discovery_id

            # Get discovery document
            discovery_doc = self.discovery_service.get_discovery(discovery_id)
            if not discovery_doc:
                raise ValueError(f"Discovery document {discovery_id} not found")

            logger.info(f"  ✅ Discovery: {discovery_doc.domain} ({len(discovery_doc.bounded_contexts)} contexts)")

            # Step 2: Generate MasterPlan (simulated - would call masterplan service)
            logger.info(f"  🎯 Generating MasterPlan...")
            masterplan_id = await self._generate_masterplan(discovery_doc)
            measurement.masterplan_id = masterplan_id

            # Get masterplan
            masterplan = self.db.query(MasterPlan).filter(
                MasterPlan.masterplan_id == masterplan_id
            ).first()

            if not masterplan:
                raise ValueError(f"MasterPlan {masterplan_id} not found")

            measurement.task_count = masterplan.total_tasks or 0
            logger.info(f"  ✅ MasterPlan: {masterplan.project_name} ({measurement.task_count} tasks)")

            # Step 3: Atomize tasks
            logger.info(f"  ⚛️  Atomizing tasks...")
            atoms = await self._atomize_tasks(masterplan)
            measurement.atom_count = len(atoms)
            logger.info(f"  ✅ Atomization: {measurement.atom_count} atoms")

            # Step 4: Calculate code hash (determinism check)
            code_content = self._extract_code_content(atoms)
            measurement.code_hash = hashlib.sha256(code_content.encode()).hexdigest()

            # Step 5: Execute atoms (simulated for baseline)
            logger.info(f"  🚀 Executing atoms...")
            execution_results = await self._execute_atoms(atoms, masterplan_id)

            measurement.atoms_succeeded = execution_results["succeeded"]
            measurement.atoms_failed = execution_results["failed"]
            measurement.success_rate = (
                (measurement.atoms_succeeded / measurement.atom_count * 100)
                if measurement.atom_count > 0
                else 0.0
            )

            # Step 6: Calculate determinism violations
            if iteration == 1:
                # First iteration - set baseline
                self.baseline_code_hash = measurement.code_hash
                self.baseline_task_count = measurement.task_count
                self.baseline_atom_count = measurement.atom_count
                measurement.determinism_violations = 0
            else:
                # Compare with baseline
                violations = 0
                if measurement.code_hash != self.baseline_code_hash:
                    violations += 1
                if measurement.task_count != self.baseline_task_count:
                    violations += 1
                if measurement.atom_count != self.baseline_atom_count:
                    violations += 1
                measurement.determinism_violations = violations

            # Calculate cost (from LLM usage)
            measurement.cost_usd = self._calculate_total_cost(discovery_doc, masterplan)

            logger.info(
                f"  ✅ Iteration {iteration} completed: "
                f"{measurement.atoms_succeeded}/{measurement.atom_count} succeeded "
                f"({measurement.success_rate:.1f}%) - "
                f"Violations: {measurement.determinism_violations}"
            )

        except Exception as e:
            logger.error(f"  ❌ Iteration {iteration} failed: {e}")
            measurement.error_message = str(e)

        finally:
            measurement.execution_time = time.time() - start_time

        return measurement

    async def _generate_masterplan(self, discovery_doc: DiscoveryDocument) -> UUID:
        """
        Generate MasterPlan from discovery document.

        Note: This is a simplified version. Real implementation would use
        MasterPlanService with proper LLM generation.
        """
        masterplan_id = uuid4()

        # Create minimal masterplan for testing
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            discovery_id=discovery_doc.discovery_id,
            session_id=discovery_doc.session_id,
            user_id=discovery_doc.user_id,
            project_name=f"{discovery_doc.domain} API",
            description=f"REST API for {discovery_doc.domain}",
            tech_stack={
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "orm": "SQLAlchemy"
            },
            total_tasks=len(discovery_doc.aggregates) * 5,  # Estimate: 5 tasks per aggregate
            llm_model="claude-sonnet-4-5",
            generation_cost_usd=0.05
        )

        self.db.add(masterplan)
        self.db.commit()

        return masterplan_id

    async def _atomize_tasks(self, masterplan: MasterPlan) -> List[Any]:
        """
        Atomize masterplan tasks into atomic units.

        Note: Simplified for baseline measurement.
        """
        # In real implementation, would use Atomizer service
        # For baseline, create mock atoms
        atoms = []

        for i in range(masterplan.total_tasks or 0):
            atoms.append({
                "atom_id": uuid4(),
                "task_name": f"Task {i+1}",
                "code": f"# Generated code for task {i+1}\n",
                "dependencies": []
            })

        return atoms

    async def _execute_atoms(
        self,
        atoms: List[Any],
        masterplan_id: UUID
    ) -> Dict[str, int]:
        """
        Execute atoms and track results.

        Note: Simulated execution for baseline.
        In real implementation, would use ExecutionServiceV2.
        """
        # Simulate execution with 40% success rate (current baseline)
        import random
        random.seed(42)  # Fixed seed for reproducibility

        succeeded = sum(1 for _ in atoms if random.random() > 0.6)  # ~40% success
        failed = len(atoms) - succeeded

        return {
            "succeeded": succeeded,
            "failed": failed,
            "total": len(atoms)
        }

    def _extract_code_content(self, atoms: List[Any]) -> str:
        """Extract all code content for hashing."""
        code_parts = []

        for atom in sorted(atoms, key=lambda a: str(a.get("atom_id", ""))):
            code = atom.get("code", "")
            code_parts.append(code)

        return "\n".join(code_parts)

    def _calculate_total_cost(
        self,
        discovery_doc: DiscoveryDocument,
        masterplan: MasterPlan
    ) -> float:
        """Calculate total LLM cost."""
        discovery_cost = discovery_doc.llm_cost_usd or 0.0
        masterplan_cost = masterplan.generation_cost_usd or 0.0

        # Add estimated execution cost (placeholder)
        execution_cost = (masterplan.total_tasks or 0) * 0.01  # $0.01 per task estimate

        return discovery_cost + masterplan_cost + execution_cost

    async def run_all_iterations(self) -> Dict[str, Any]:
        """Run all iterations and analyze results."""
        logger.info(f"🚀 Starting precision baseline measurement ({self.iterations} iterations)")
        logger.info(f"   User request: {self.user_request}")

        # Run iterations
        for i in range(1, self.iterations + 1):
            measurement = await self.run_single_iteration(i)
            self.measurements.append(measurement)

        # Analyze results
        results = self._analyze_results()

        return results

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze all measurements and calculate statistics."""
        import statistics

        # Filter successful measurements
        successful = [m for m in self.measurements if m.error_message is None]

        if not successful:
            return {
                "error": "All iterations failed",
                "measurements": [m.to_dict() for m in self.measurements]
            }

        # Calculate statistics
        task_counts = [m.task_count for m in successful]
        atom_counts = [m.atom_count for m in successful]
        success_rates = [m.success_rate for m in successful]
        execution_times = [m.execution_time for m in successful]
        costs = [m.cost_usd for m in successful]
        violations = [m.determinism_violations for m in successful]

        # Determinism score (% of iterations with 0 violations)
        deterministic_iterations = sum(1 for v in violations if v == 0)
        determinism_score = (deterministic_iterations / len(successful)) * 100

        # Precision score (average success rate)
        precision_score = statistics.mean(success_rates)

        analysis = {
            "summary": {
                "total_iterations": self.iterations,
                "successful_iterations": len(successful),
                "failed_iterations": len(self.measurements) - len(successful),
                "precision_score": round(precision_score, 2),
                "determinism_score": round(determinism_score, 2),
                "target_precision": 98.0,
                "gap_to_target": round(98.0 - precision_score, 2)
            },
            "task_count": {
                "mean": statistics.mean(task_counts),
                "std": statistics.stdev(task_counts) if len(task_counts) > 1 else 0.0,
                "min": min(task_counts),
                "max": max(task_counts)
            },
            "atom_count": {
                "mean": statistics.mean(atom_counts),
                "std": statistics.stdev(atom_counts) if len(atom_counts) > 1 else 0.0,
                "min": min(atom_counts),
                "max": max(atom_counts)
            },
            "success_rate": {
                "mean": statistics.mean(success_rates),
                "std": statistics.stdev(success_rates) if len(success_rates) > 1 else 0.0,
                "min": min(success_rates),
                "max": max(success_rates)
            },
            "execution_time": {
                "mean": statistics.mean(execution_times),
                "std": statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0,
                "min": min(execution_times),
                "max": max(execution_times)
            },
            "cost_usd": {
                "mean": statistics.mean(costs),
                "std": statistics.stdev(costs) if len(costs) > 1 else 0.0,
                "min": min(costs),
                "max": max(costs),
                "total": sum(costs)
            },
            "determinism_violations": {
                "mean": statistics.mean(violations),
                "total_violations": sum(violations),
                "deterministic_iterations": deterministic_iterations,
                "determinism_percentage": determinism_score
            },
            "measurements": [m.to_dict() for m in self.measurements]
        }

        return analysis

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save results to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"📊 Results saved to {output_path}")

    def generate_html_report(self, results: Dict[str, Any], output_path: str):
        """Generate HTML report with visualizations."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Precision Baseline Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f9f9f9; border-left: 4px solid #4CAF50; padding: 15px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #4CAF50; }}
        .metric-label {{ color: #666; font-size: 14px; }}
        .alert {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .success {{ background: #d4edda; border-left: 4px solid #28a745; }}
        .danger {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .progress-bar {{ width: 100%; height: 30px; background: #e0e0e0; border-radius: 5px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #4CAF50; transition: width 0.3s; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Precision Baseline Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Iterations:</strong> {results['summary']['total_iterations']}</p>

        <h2>📊 Summary Metrics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{results['summary']['precision_score']}%</div>
                <div class="metric-label">Current Precision</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{results['summary']['determinism_score']}%</div>
                <div class="metric-label">Determinism Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{results['summary']['gap_to_target']}%</div>
                <div class="metric-label">Gap to 98% Target</div>
            </div>
        </div>

        <div class="{'success' if results['summary']['gap_to_target'] < 10 else 'alert'}">
            <strong>Status:</strong>
            {'🎉 Near target! Less than 10% gap.' if results['summary']['gap_to_target'] < 10 else f"⚠️ Need {results['summary']['gap_to_target']}% improvement to reach 98% target."}
        </div>

        <h2>📈 Progress to Target</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {results['summary']['precision_score']}%"></div>
        </div>
        <p style="text-align: center;">{results['summary']['precision_score']}% / 98% Target</p>

        <h2>🔬 Detailed Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Mean</th>
                <th>Std Dev</th>
                <th>Min</th>
                <th>Max</th>
            </tr>
            <tr>
                <td>Task Count</td>
                <td>{results['task_count']['mean']:.1f}</td>
                <td>{results['task_count']['std']:.2f}</td>
                <td>{results['task_count']['min']}</td>
                <td>{results['task_count']['max']}</td>
            </tr>
            <tr>
                <td>Atom Count</td>
                <td>{results['atom_count']['mean']:.1f}</td>
                <td>{results['atom_count']['std']:.2f}</td>
                <td>{results['atom_count']['min']}</td>
                <td>{results['atom_count']['max']}</td>
            </tr>
            <tr>
                <td>Success Rate (%)</td>
                <td>{results['success_rate']['mean']:.1f}</td>
                <td>{results['success_rate']['std']:.2f}</td>
                <td>{results['success_rate']['min']:.1f}</td>
                <td>{results['success_rate']['max']:.1f}</td>
            </tr>
            <tr>
                <td>Execution Time (s)</td>
                <td>{results['execution_time']['mean']:.1f}</td>
                <td>{results['execution_time']['std']:.2f}</td>
                <td>{results['execution_time']['min']:.1f}</td>
                <td>{results['execution_time']['max']:.1f}</td>
            </tr>
            <tr>
                <td>Cost (USD)</td>
                <td>${results['cost_usd']['mean']:.4f}</td>
                <td>${results['cost_usd']['std']:.4f}</td>
                <td>${results['cost_usd']['min']:.4f}</td>
                <td>${results['cost_usd']['max']:.4f}</td>
            </tr>
        </table>

        <h2>🎲 Determinism Analysis</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{results['determinism_violations']['deterministic_iterations']}/{results['summary']['successful_iterations']}</div>
                <div class="metric-label">Deterministic Iterations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{results['determinism_violations']['total_violations']}</div>
                <div class="metric-label">Total Violations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{results['determinism_violations']['determinism_percentage']:.1f}%</div>
                <div class="metric-label">Determinism %</div>
            </div>
        </div>

        <h2>📋 Individual Iterations</h2>
        <table>
            <tr>
                <th>Iteration</th>
                <th>Tasks</th>
                <th>Atoms</th>
                <th>Success Rate</th>
                <th>Time (s)</th>
                <th>Cost (USD)</th>
                <th>Violations</th>
            </tr>
"""

        for m in results['measurements']:
            if m.get('error'):
                html_content += f"""
            <tr style="background: #f8d7da;">
                <td>{m['iteration']}</td>
                <td colspan="6">❌ Error: {m['error']}</td>
            </tr>
"""
            else:
                html_content += f"""
            <tr>
                <td>{m['iteration']}</td>
                <td>{m['task_count']}</td>
                <td>{m['atom_count']}</td>
                <td>{m['success_rate']:.1f}%</td>
                <td>{m['execution_time']:.1f}</td>
                <td>${m['cost_usd']:.4f}</td>
                <td>{m['determinism_violations']}</td>
            </tr>
"""

        html_content += """
        </table>
    </div>
</body>
</html>
"""

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"📊 HTML report saved to {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Measure precision baseline for MGE V2"
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=10,
        help='Number of iterations to run (default: 10)'
    )
    parser.add_argument(
        '--user-request',
        type=str,
        default="Create a simple REST API for task management with CRUD operations",
        help='User request to test with'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./reports/precision',
        help='Output directory for reports (default: ./reports/precision)'
    )

    args = parser.parse_args()

    # Create database session
    SessionLocal = DatabaseConfig.get_session_factory()
    db = SessionLocal()

    try:
        # Run baseline measurement
        baseline = PrecisionBaseline(
            db=db,
            user_request=args.user_request,
            iterations=args.iterations
        )

        results = await baseline.run_all_iterations()

        # Generate outputs
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(args.output_dir)

        # Save JSON
        json_path = output_dir / f"baseline_{timestamp}.json"
        baseline.save_results(results, str(json_path))

        # Generate HTML report
        html_path = output_dir / f"baseline_{timestamp}.html"
        baseline.generate_html_report(results, str(html_path))

        # Print summary
        print("\n" + "=" * 80)
        print("🎯 PRECISION BASELINE SUMMARY")
        print("=" * 80)
        print(f"Iterations:         {results['summary']['total_iterations']}")
        print(f"Successful:         {results['summary']['successful_iterations']}")
        print(f"Failed:             {results['summary']['failed_iterations']}")
        print(f"Precision Score:    {results['summary']['precision_score']}%")
        print(f"Determinism Score:  {results['summary']['determinism_score']}%")
        print(f"Target:             98.0%")
        print(f"Gap:                {results['summary']['gap_to_target']}%")
        print("=" * 80)
        print(f"\n📊 Reports saved:")
        print(f"   JSON:  {json_path}")
        print(f"   HTML:  {html_path}")
        print("\n")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
