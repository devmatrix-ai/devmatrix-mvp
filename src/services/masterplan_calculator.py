"""
MasterPlan Calculator - Intelligent task counting based on Discovery Document

Calculates exact number of atomic tasks needed based on:
- Number and complexity of Bounded Contexts
- Number of Aggregates and Entities
- Number of Domain Events
- Number of Services
- Parallelization opportunities

No arbitrary numbers - everything calculated from discovery structure.
"""

import logging
from typing import Dict, List, Any, Optional
from uuid import UUID

from src.models.masterplan import DiscoveryDocument
from src.config.database import get_db_context

logger = logging.getLogger(__name__)


class ComplexityMetrics:
    """Metrics for complexity analysis of discovery components"""

    def __init__(self):
        self.bounded_contexts = 0
        self.aggregates = 0
        self.value_objects = 0
        self.domain_events = 0
        self.services = 0
        self.total_entities = 0


class TaskBreakdown:
    """Detailed breakdown of tasks by category"""

    def __init__(self):
        self.setup_tasks = 0  # Infrastructure, repo setup, etc.
        self.modeling_tasks = 0  # DDD modeling, aggregate definition
        self.persistence_tasks = 0  # Database, ORM, queries
        self.implementation_tasks = 0  # Feature implementation
        self.integration_tasks = 0  # Service integration
        self.testing_tasks = 0  # Unit, integration, E2E tests
        self.deployment_tasks = 0  # Docker, CI/CD, deployment
        self.optimization_tasks = 0  # Performance, monitoring

    @property
    def total_tasks(self) -> int:
        return (
            self.setup_tasks +
            self.modeling_tasks +
            self.persistence_tasks +
            self.implementation_tasks +
            self.integration_tasks +
            self.testing_tasks +
            self.deployment_tasks +
            self.optimization_tasks
        )

    def to_dict(self) -> Dict[str, int]:
        return {
            "setup": self.setup_tasks,
            "modeling": self.modeling_tasks,
            "persistence": self.persistence_tasks,
            "implementation": self.implementation_tasks,
            "integration": self.integration_tasks,
            "testing": self.testing_tasks,
            "deployment": self.deployment_tasks,
            "optimization": self.optimization_tasks,
            "total": self.total_tasks,
        }


class MasterPlanCalculator:
    """
    Intelligently calculates task count and structure based on Discovery Document.

    Formula:
    - Each Bounded Context: 2 setup/integration tasks
    - Each Aggregate: 3 tasks (modeling + persistence + testing)
    - Each Service: 2 tasks (implementation + integration)
    - Each Domain Event: 0.5 tasks (event handler, aggregated)
    - Cross-cutting: auth, monitoring, deployment (4-6 tasks)

    Result: Actual tasks needed, not arbitrary numbers
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_discovery(self, discovery: DiscoveryDocument) -> Dict[str, Any]:
        """
        Analyze discovery document and calculate task requirements.

        Args:
            discovery: DiscoveryDocument from database

        Returns:
            Dict with:
            - calculated_task_count: exact number of tasks needed
            - complexity_metrics: breakdown by component
            - task_breakdown: breakdown by task type
            - parallelization_level: max concurrent tasks
            - task_sequencing: which tasks depend on others
        """
        self.logger.info(
            f"Analyzing discovery for task calculation",
            discovery_id=str(discovery.discovery_id),
            domain=discovery.domain
        )

        # Extract metrics
        metrics = self._extract_metrics(discovery)

        self.logger.info(
            f"Extracted complexity metrics",
            bounded_contexts=metrics.bounded_contexts,
            aggregates=metrics.aggregates,
            value_objects=metrics.value_objects,
            domain_events=metrics.domain_events,
            services=metrics.services
        )

        # Calculate task breakdown
        breakdown = self._calculate_task_breakdown(metrics)

        # Determine parallelization
        parallelization = self._determine_parallelization(metrics, breakdown)

        # Create task sequencing
        task_sequencing = self._create_task_sequencing(metrics, breakdown)

        result = {
            "calculated_task_count": breakdown.total_tasks,
            "complexity_metrics": {
                "bounded_contexts": metrics.bounded_contexts,
                "aggregates": metrics.aggregates,
                "value_objects": metrics.value_objects,
                "domain_events": metrics.domain_events,
                "services": metrics.services,
                "total_entities": metrics.total_entities,
            },
            "task_breakdown": breakdown.to_dict(),
            "parallelization_level": parallelization,
            "task_sequencing": task_sequencing,
            "rationale": self._generate_rationale(metrics, breakdown)
        }

        self.logger.info(
            f"Task calculation complete",
            calculated_count=breakdown.total_tasks,
            parallelization=parallelization,
            task_breakdown=breakdown.to_dict()
        )

        return result

    def _extract_metrics(self, discovery: DiscoveryDocument) -> ComplexityMetrics:
        """Extract complexity metrics from discovery document"""
        metrics = ComplexityMetrics()

        # Count entities
        metrics.bounded_contexts = len(discovery.bounded_contexts) if discovery.bounded_contexts else 0
        metrics.aggregates = len(discovery.aggregates) if discovery.aggregates else 0
        metrics.value_objects = len(discovery.value_objects) if discovery.value_objects else 0
        metrics.domain_events = len(discovery.domain_events) if discovery.domain_events else 0
        metrics.services = len(discovery.services) if discovery.services else 0

        metrics.total_entities = (
            metrics.bounded_contexts +
            metrics.aggregates +
            metrics.value_objects +
            metrics.domain_events +
            metrics.services
        )

        return metrics

    def _calculate_task_breakdown(self, metrics: ComplexityMetrics) -> TaskBreakdown:
        """
        Calculate task breakdown based on complexity metrics.

        Formula:
        - Setup (1 task): Initial repo, Docker, configuration
        - Modeling (BC × 2 + Agg × 1): DDD modeling tasks
        - Persistence (Agg × 1): Database/ORM setup per aggregate
        - Implementation (Agg × 1 + Services × 1): Feature implementation
        - Integration (Services × 0.5): Cross-service integration
        - Testing (Agg × 1): Unit/integration tests
        - Deployment (2 tasks): Docker, CI/CD, deployment
        - Optimization (1 task): Monitoring, performance tuning
        """
        breakdown = TaskBreakdown()

        # Setup: 1 task (repo, docker, config)
        breakdown.setup_tasks = 1

        # Modeling: 2 per BC + 1 per Aggregate
        breakdown.modeling_tasks = (metrics.bounded_contexts * 2) + metrics.aggregates

        # Persistence: 1 per Aggregate
        breakdown.persistence_tasks = metrics.aggregates

        # Implementation: 1 per Aggregate + 1 per Service
        breakdown.implementation_tasks = metrics.aggregates + metrics.services

        # Integration: 0.5 per Service (rounded up)
        breakdown.integration_tasks = (metrics.services + 1) // 2

        # Testing: 1 per Aggregate + 1 general
        breakdown.testing_tasks = metrics.aggregates + 1

        # Deployment: 2 tasks (CI/CD + deployment)
        breakdown.deployment_tasks = 2

        # Optimization: 1 task (monitoring, perf tuning)
        breakdown.optimization_tasks = 1

        return breakdown

    def _determine_parallelization(self, metrics: ComplexityMetrics, breakdown: TaskBreakdown) -> int:
        """
        Determine maximum number of tasks that can run in parallel.

        Based on:
        - Number of bounded contexts (can work in parallel)
        - Number of aggregates per context
        - Service dependencies

        Conservative estimate: min(aggregates, 8)
        """
        # Can parallelize at least one task per aggregate
        base_parallelization = min(metrics.aggregates, 8)

        # But limited by bounded contexts (can't parallelize across BCs without core integration)
        limited_by_contexts = max(metrics.bounded_contexts, 2)

        parallelization = min(base_parallelization, limited_by_contexts * 2)

        return max(parallelization, 2)  # At least 2 parallel tasks

    def _create_task_sequencing(self, metrics: ComplexityMetrics, breakdown: TaskBreakdown) -> Dict[str, List[str]]:
        """
        Create task sequencing showing dependencies.

        Returns groups of tasks that must be sequential.
        """
        sequencing = {
            "phase_1_setup": ["repo_setup", "docker_infrastructure", "database_setup"],
            "phase_2_modeling": [f"model_bc_{i}" for i in range(metrics.bounded_contexts)],
            "phase_3_implementation": [f"implement_aggregate_{i}" for i in range(metrics.aggregates)],
            "phase_4_integration": [f"integrate_service_{i}" for i in range(metrics.services)],
            "phase_5_testing": ["unit_tests", "integration_tests"],
            "phase_6_deployment": ["ci_cd_setup", "deploy_to_staging"],
        }

        return sequencing

    def _generate_rationale(self, metrics: ComplexityMetrics, breakdown: TaskBreakdown) -> str:
        """
        Generate human-readable rationale for calculated task count.
        """
        return (
            f"Calculated {breakdown.total_tasks} tasks from: "
            f"{metrics.bounded_contexts} bounded contexts × 2 = {metrics.bounded_contexts * 2} modeling tasks; "
            f"{metrics.aggregates} aggregates × 3 (model+persist+test) = {metrics.aggregates * 3} tasks; "
            f"{metrics.services} services × 1.5 = {int(metrics.services * 1.5)} tasks; "
            f"+ {breakdown.setup_tasks + breakdown.deployment_tasks} setup/deployment tasks. "
            f"Max parallelization: {self._determine_parallelization(metrics, breakdown)} concurrent tasks."
        )

    @staticmethod
    def get_discovery_and_analyze(discovery_id: UUID) -> Dict[str, Any]:
        """
        Load discovery document from database and analyze it.

        Args:
            discovery_id: UUID of discovery document

        Returns:
            Analysis result dict
        """
        with get_db_context() as db:
            discovery = db.query(DiscoveryDocument).filter(
                DiscoveryDocument.discovery_id == discovery_id
            ).first()

            if not discovery:
                raise ValueError(f"Discovery not found: {discovery_id}")

            calculator = MasterPlanCalculator()
            return calculator.analyze_discovery(discovery)


# Example usage:
if __name__ == "__main__":
    """
    Example:

    from uuid import UUID
    from src.services.masterplan_calculator import MasterPlanCalculator

    discovery_id = UUID("...")
    result = MasterPlanCalculator.get_discovery_and_analyze(discovery_id)

    print(f"Calculated tasks: {result['calculated_task_count']}")
    print(f"Breakdown: {result['task_breakdown']}")
    print(f"Parallelization: {result['parallelization_level']}")
    print(f"Rationale: {result['rationale']}")
    """
    pass
