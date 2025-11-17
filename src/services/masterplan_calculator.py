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

from typing import Dict, List, Any, Optional
from uuid import UUID

from src.models.masterplan import DiscoveryDocument
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("masterplan_calculator")


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
        pass

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
        logger.info(
            f"Analyzing discovery for task calculation",
            discovery_id=str(discovery.discovery_id),
            domain=discovery.domain
        )

        # Extract metrics
        metrics = self._extract_metrics(discovery)

        logger.info(
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

        logger.info(
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

        ULTRA-ATOMIC PHILOSOPHY: Each task = 1 file operation
        More tasks = More detailed and deterministic plan

        Formula (per file):
        - Setup: 8+ files (pyproject.toml, Dockerfile, docker-compose, .env, README, etc.)
        - Modeling: 2 files per aggregate (model.py + schema.py)
        - Persistence: 3 files per aggregate (repository.py + migration.py + db_model.py)
        - Implementation: 2-3 files per service/aggregate (service.py + router.py + deps.py)
        - Integration: 5+ files (main.py, config.py, middleware/*, dependencies.py)
        - Testing: 4+ files per aggregate (test_model, test_repo, test_api, test_service)
        - Deployment: 8+ files (CI/CD, Docker prod, k8s, nginx, scripts)
        - Optimization: 6+ files (logging, metrics, tracing, dashboards, monitoring)
        """
        breakdown = TaskBreakdown()

        # Setup: Core infrastructure files + per BC configs
        # Files: pyproject.toml, Dockerfile, docker-compose.yml, .env.example, README,
        #        alembic.ini, src/__init__, tests/__init__ + BC-specific configs
        breakdown.setup_tasks = max(8, 6 + metrics.bounded_contexts * 3)

        # Modeling: 2 files per Aggregate (Pydantic model + Schema)
        # Files: src/models/{aggregate}.py + src/schemas/{aggregate}_schema.py
        breakdown.modeling_tasks = metrics.aggregates * 2

        # Persistence: 3 files per Aggregate (Repository + Migration + ORM model)
        # Files: repositories/{agg}_repository.py + migrations/00X_create_{agg}.py
        #        + database/models/{agg}_db.py
        breakdown.persistence_tasks = metrics.aggregates * 3

        # Implementation: Service files + Router files + Dependencies
        # Files: services/{svc}_service.py + api/routers/{agg}.py + api/dependencies/{svc}_deps.py
        breakdown.implementation_tasks = metrics.services * 2 + metrics.aggregates

        # Integration: Core app files + middleware + per-service integration
        # Files: api/main.py, core/config.py, core/dependencies.py, middleware/*.py
        breakdown.integration_tasks = max(5, 4 + metrics.services + (metrics.services // 3))

        # Testing: ULTRA-ATOMIC - 4 test files per aggregate + general + E2E + contracts
        # Files per aggregate: tests/models/test_{agg}.py, tests/repositories/test_{agg}_repository.py,
        #                      tests/api/test_{agg}_router.py, tests/services/test_{agg}_service.py
        # General: test_config.py, test_main.py, e2e/test_*_flow.py, contracts/test_*_schema.py,
        #          performance/test_load.py, security/test_auth.py
        breakdown.testing_tasks = max(
            12,  # ABSOLUTE MINIMUM - always at least 12 test files
            metrics.aggregates * 4 +  # 4 test files per aggregate
            max(3, metrics.aggregates // 3) +  # E2E flow tests (1 per 3 aggregates)
            4  # General: config, main, performance, security
        )

        # Deployment: Multi-environment, multi-stage deployment files
        # Files: .github/workflows/ci.yml, .github/workflows/deploy.yml, Dockerfile.prod,
        #        docker-compose.prod.yml, kubernetes/*, terraform/*, scripts/deploy.sh, nginx.conf
        breakdown.deployment_tasks = max(8, 7 + metrics.bounded_contexts * 2)

        # Optimization: Observability stack + monitoring per BC
        # Files: observability/logging.py, observability/metrics.py, observability/tracing.py,
        #        grafana/dashboards/*.json, prometheus/prometheus.yml, scripts/performance_test.sh
        breakdown.optimization_tasks = max(6, 5 + (metrics.aggregates // 4))

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
        ULTRA-ATOMIC: Each task = 1 file operation
        """
        return (
            f"Calculated {breakdown.total_tasks} ULTRA-ATOMIC tasks (1 task = 1 file) from: "
            f"{breakdown.setup_tasks} setup files (config, docker, infra); "
            f"{breakdown.modeling_tasks} model files ({metrics.aggregates} agg × 2 files); "
            f"{breakdown.persistence_tasks} persistence files ({metrics.aggregates} agg × 3 files); "
            f"{breakdown.implementation_tasks} implementation files ({metrics.services} svc × 2 + {metrics.aggregates} routers); "
            f"{breakdown.integration_tasks} integration files (main, middleware, config); "
            f"{breakdown.testing_tasks} test files ({metrics.aggregates} agg × 4 + E2E + contracts + general); "
            f"{breakdown.deployment_tasks} deployment files (CI/CD, k8s, nginx, scripts); "
            f"{breakdown.optimization_tasks} optimization files (observability, monitoring). "
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
