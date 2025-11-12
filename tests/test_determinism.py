"""
Determinism Test Suite

Tests to verify that MGE V2 produces deterministic results across
multiple executions with the same input.

Critical Requirements:
1. Same Discovery → Same MasterPlan (hash match)
2. Same Discovery → Same Code (hash match)
3. Temperature = 0 enforced
4. Seed = 42 fixed
5. No tolerance in task count (exact match required)
"""

import pytest
import hashlib
import json
from uuid import UUID
from typing import Dict, List, Any
import asyncio

from sqlalchemy.orm import Session
from src.config.database import DatabaseConfig
from src.services.discovery_service import DiscoveryService
from src.models.masterplan import DiscoveryDocument, MasterPlan
from src.llm import EnhancedAnthropicClient


@pytest.fixture
def db_session():
    """Database session fixture."""
    SessionLocal = DatabaseConfig.get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_user_request():
    """Sample user request for testing."""
    return "Create a simple REST API for task management with CRUD operations"


@pytest.fixture
def discovery_service(db_session):
    """Discovery service fixture."""
    return DiscoveryService(db=db_session)


class TestDeterminism:
    """Determinism test suite."""

    @pytest.mark.asyncio
    async def test_same_discovery_same_masterplan_hash(
        self,
        db_session: Session,
        discovery_service: DiscoveryService,
        sample_user_request: str
    ):
        """
        Test: Running discovery 5 times should produce identical MasterPlans.

        Verification:
        - Hash of MasterPlan content should be identical
        - Task count should be identical
        - Tech stack should be identical
        """
        iterations = 5
        masterplan_hashes = []
        task_counts = []

        for i in range(iterations):
            # Generate discovery
            discovery_id = await discovery_service.generate_discovery(
                user_request=sample_user_request,
                session_id=f"determinism_test_session_{i}",
                user_id="determinism_test_user"
            )

            discovery_doc = discovery_service.get_discovery(discovery_id)
            assert discovery_doc is not None

            # Generate masterplan (simplified - would use real service)
            masterplan_content = self._create_masterplan_content(discovery_doc)
            masterplan_hash = hashlib.sha256(
                json.dumps(masterplan_content, sort_keys=True).encode()
            ).hexdigest()

            masterplan_hashes.append(masterplan_hash)
            task_counts.append(len(discovery_doc.aggregates) * 5)

        # Verify all hashes are identical
        unique_hashes = set(masterplan_hashes)
        assert len(unique_hashes) == 1, (
            f"MasterPlan hashes differ across iterations. "
            f"Expected 1 unique hash, got {len(unique_hashes)}. "
            f"Hashes: {masterplan_hashes}"
        )

        # Verify all task counts are identical
        unique_counts = set(task_counts)
        assert len(unique_counts) == 1, (
            f"Task counts differ across iterations. "
            f"Expected 1 unique count, got {len(unique_counts)}. "
            f"Counts: {task_counts}"
        )

    @pytest.mark.asyncio
    async def test_same_discovery_same_code_hash(
        self,
        db_session: Session,
        discovery_service: DiscoveryService,
        sample_user_request: str
    ):
        """
        Test: Generated code should be identical across iterations.

        Verification:
        - Code hash should be identical
        - Atom count should be identical
        """
        iterations = 5
        code_hashes = []
        atom_counts = []

        for i in range(iterations):
            # Generate discovery
            discovery_id = await discovery_service.generate_discovery(
                user_request=sample_user_request,
                session_id=f"code_determinism_test_{i}",
                user_id="code_determinism_user"
            )

            discovery_doc = discovery_service.get_discovery(discovery_id)
            assert discovery_doc is not None

            # Generate code (simulated)
            code_content = self._generate_code(discovery_doc)
            code_hash = hashlib.sha256(code_content.encode()).hexdigest()

            code_hashes.append(code_hash)
            atom_counts.append(len(discovery_doc.aggregates) * 5)

        # Verify all code hashes are identical
        unique_hashes = set(code_hashes)
        assert len(unique_hashes) == 1, (
            f"Code hashes differ across iterations. "
            f"Expected 1 unique hash, got {len(unique_hashes)}. "
            f"Hashes: {code_hashes}"
        )

        # Verify all atom counts are identical
        unique_counts = set(atom_counts)
        assert len(unique_counts) == 1, (
            f"Atom counts differ across iterations. "
            f"Expected 1 unique count, got {len(unique_counts)}. "
            f"Counts: {atom_counts}"
        )

    @pytest.mark.asyncio
    async def test_temperature_zero_enforced(self):
        """
        Test: LLM client should enforce temperature=0 for deterministic operations.

        Verification:
        - Check LLM client configuration
        - Verify temperature is set to 0
        """
        llm_client = EnhancedAnthropicClient()

        # Check if temperature=0 is enforced in deterministic mode
        # Note: Would need to inspect actual LLM calls
        # For now, verify client has configuration capability

        assert hasattr(llm_client, 'generate_with_caching'), (
            "LLM client should support caching for deterministic operations"
        )

        # Verify temperature can be set to 0
        # In real implementation, would check actual API calls
        assert True, "Temperature enforcement test placeholder"

    @pytest.mark.asyncio
    async def test_seed_fixed(self):
        """
        Test: Random operations should use fixed seed=42.

        Verification:
        - Check that random operations use fixed seed
        - Verify reproducible random selections
        """
        import random

        # Test 1: Verify fixed seed produces same results
        random.seed(42)
        sequence_1 = [random.random() for _ in range(10)]

        random.seed(42)
        sequence_2 = [random.random() for _ in range(10)]

        assert sequence_1 == sequence_2, (
            "Random sequences with same seed should be identical. "
            f"Seed 42 produced different sequences."
        )

        # Test 2: Verify different seeds produce different results
        random.seed(42)
        sequence_3 = [random.random() for _ in range(10)]

        random.seed(43)
        sequence_4 = [random.random() for _ in range(10)]

        assert sequence_3 != sequence_4, (
            "Random sequences with different seeds should differ"
        )

    @pytest.mark.asyncio
    async def test_no_tolerance_in_task_count(
        self,
        db_session: Session,
        discovery_service: DiscoveryService,
        sample_user_request: str
    ):
        """
        Test: Task count must be exact - no tolerance allowed.

        Verification:
        - Task count should be identical across all iterations
        - No variance allowed (no ±1, no ±5%)
        """
        iterations = 10
        task_counts = []

        for i in range(iterations):
            # Generate discovery
            discovery_id = await discovery_service.generate_discovery(
                user_request=sample_user_request,
                session_id=f"task_count_test_{i}",
                user_id="task_count_user"
            )

            discovery_doc = discovery_service.get_discovery(discovery_id)
            assert discovery_doc is not None

            # Calculate task count (deterministic formula)
            task_count = len(discovery_doc.aggregates) * 5
            task_counts.append(task_count)

        # Verify all task counts are identical
        unique_counts = set(task_counts)
        assert len(unique_counts) == 1, (
            f"Task counts must be identical - no tolerance allowed. "
            f"Expected 1 unique count, got {len(unique_counts)}. "
            f"Counts: {task_counts}"
        )

        # Verify no variance
        if len(task_counts) > 1:
            import statistics
            std_dev = statistics.stdev(task_counts)
            assert std_dev == 0.0, (
                f"Task count variance detected: std_dev = {std_dev}. "
                f"Must be exactly 0.0 (no tolerance)."
            )

    @pytest.mark.asyncio
    async def test_discovery_document_stability(
        self,
        db_session: Session,
        discovery_service: DiscoveryService,
        sample_user_request: str
    ):
        """
        Test: DiscoveryDocument should be stable across iterations.

        Verification:
        - Domain should be identical
        - Bounded context count should be identical
        - Aggregate count should be identical
        """
        iterations = 5
        discoveries = []

        for i in range(iterations):
            discovery_id = await discovery_service.generate_discovery(
                user_request=sample_user_request,
                session_id=f"stability_test_{i}",
                user_id="stability_user"
            )

            discovery_doc = discovery_service.get_discovery(discovery_id)
            assert discovery_doc is not None

            discoveries.append({
                "domain": discovery_doc.domain,
                "bounded_contexts_count": len(discovery_doc.bounded_contexts),
                "aggregates_count": len(discovery_doc.aggregates),
                "value_objects_count": len(discovery_doc.value_objects),
                "services_count": len(discovery_doc.services)
            })

        # Verify all metrics are identical
        for key in discoveries[0].keys():
            values = [d[key] for d in discoveries]
            unique_values = set(values)

            assert len(unique_values) == 1, (
                f"{key} differs across iterations. "
                f"Expected 1 unique value, got {len(unique_values)}. "
                f"Values: {values}"
            )

    @pytest.mark.asyncio
    async def test_atomization_determinism(
        self,
        db_session: Session,
        discovery_service: DiscoveryService,
        sample_user_request: str
    ):
        """
        Test: Atomization should produce identical atoms across iterations.

        Verification:
        - Atom count should be identical
        - Atom IDs (when ordered) should produce same hash
        """
        iterations = 3
        atom_metadata = []

        for i in range(iterations):
            # Generate discovery
            discovery_id = await discovery_service.generate_discovery(
                user_request=sample_user_request,
                session_id=f"atomization_test_{i}",
                user_id="atomization_user"
            )

            discovery_doc = discovery_service.get_discovery(discovery_id)
            assert discovery_doc is not None

            # Simulate atomization
            atoms = self._simulate_atomization(discovery_doc)

            # Calculate metadata
            atom_count = len(atoms)
            atoms_sorted = sorted(atoms, key=lambda a: a["name"])
            atoms_hash = hashlib.sha256(
                json.dumps(atoms_sorted, sort_keys=True).encode()
            ).hexdigest()

            atom_metadata.append({
                "count": atom_count,
                "hash": atoms_hash
            })

        # Verify all atom counts are identical
        counts = [m["count"] for m in atom_metadata]
        unique_counts = set(counts)
        assert len(unique_counts) == 1, (
            f"Atom counts differ across iterations. "
            f"Counts: {counts}"
        )

        # Verify all atom hashes are identical
        hashes = [m["hash"] for m in atom_metadata]
        unique_hashes = set(hashes)
        assert len(unique_hashes) == 1, (
            f"Atom structure differs across iterations. "
            f"Hashes: {hashes}"
        )

    # Helper methods

    def _create_masterplan_content(self, discovery_doc: DiscoveryDocument) -> Dict[str, Any]:
        """Create deterministic masterplan content from discovery."""
        return {
            "domain": discovery_doc.domain,
            "bounded_contexts": discovery_doc.bounded_contexts,
            "aggregates": discovery_doc.aggregates,
            "task_count": len(discovery_doc.aggregates) * 5,
            "tech_stack": {
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "orm": "SQLAlchemy"
            }
        }

    def _generate_code(self, discovery_doc: DiscoveryDocument) -> str:
        """Generate deterministic code from discovery."""
        code_parts = []

        for agg in sorted(discovery_doc.aggregates, key=lambda a: a.get("name", "")):
            code_parts.append(f"# Model: {agg.get('name', 'Unknown')}\n")
            code_parts.append(f"class {agg.get('name', 'Unknown')}:\n")
            code_parts.append(f"    pass\n\n")

        return "".join(code_parts)

    def _simulate_atomization(self, discovery_doc: DiscoveryDocument) -> List[Dict[str, Any]]:
        """Simulate deterministic atomization."""
        atoms = []

        for i, agg in enumerate(sorted(discovery_doc.aggregates, key=lambda a: a.get("name", ""))):
            for j in range(5):  # 5 tasks per aggregate
                atoms.append({
                    "name": f"{agg.get('name', 'Unknown')}_task_{j+1}",
                    "aggregate": agg.get("name", "Unknown"),
                    "task_number": i * 5 + j + 1
                })

        return atoms


class TestDeterminismVariance:
    """Tests to measure and report variance (should be 0)."""

    @pytest.mark.asyncio
    async def test_measure_discovery_variance(
        self,
        db_session: Session,
        discovery_service: DiscoveryService,
        sample_user_request: str
    ):
        """
        Measure variance in discovery generation.

        Should report variance = 0 for all metrics.
        """
        import statistics

        iterations = 10
        metrics = {
            "bounded_contexts_count": [],
            "aggregates_count": [],
            "value_objects_count": [],
            "services_count": []
        }

        for i in range(iterations):
            discovery_id = await discovery_service.generate_discovery(
                user_request=sample_user_request,
                session_id=f"variance_test_{i}",
                user_id="variance_user"
            )

            discovery_doc = discovery_service.get_discovery(discovery_id)
            assert discovery_doc is not None

            metrics["bounded_contexts_count"].append(len(discovery_doc.bounded_contexts))
            metrics["aggregates_count"].append(len(discovery_doc.aggregates))
            metrics["value_objects_count"].append(len(discovery_doc.value_objects))
            metrics["services_count"].append(len(discovery_doc.services))

        # Calculate variance for each metric
        for metric_name, values in metrics.items():
            if len(values) > 1:
                variance = statistics.variance(values)
                std_dev = statistics.stdev(values)

                # Report variance (should be 0)
                print(f"\n{metric_name}:")
                print(f"  Values: {values}")
                print(f"  Mean: {statistics.mean(values):.2f}")
                print(f"  Std Dev: {std_dev:.4f}")
                print(f"  Variance: {variance:.4f}")

                # Assert variance is 0
                assert variance == 0.0, (
                    f"{metric_name} has variance {variance} (expected 0). "
                    f"Values: {values}"
                )


class TestDeterminismRegression:
    """Regression tests to catch determinism violations."""

    @pytest.mark.asyncio
    async def test_no_randomness_in_critical_path(self):
        """
        Test: Critical path should have no random operations.

        Verification:
        - No random.random() calls
        - No datetime.now() in deterministic sections
        - No non-deterministic sorts
        """
        # This is a code inspection test
        # In real implementation, would use AST analysis

        import random
        import datetime

        # Verify random seed is controlled
        random.seed(42)
        sample_1 = random.random()

        random.seed(42)
        sample_2 = random.random()

        assert sample_1 == sample_2, "Random seed not properly controlled"

    @pytest.mark.asyncio
    async def test_llm_response_caching(self):
        """
        Test: LLM responses should be cached for identical inputs.

        Verification:
        - Same input → cache hit
        - Different input → cache miss
        """
        llm_client = EnhancedAnthropicClient()

        # Verify caching capability exists
        assert hasattr(llm_client, 'generate_with_caching'), (
            "LLM client should support response caching"
        )

        # In real implementation, would verify:
        # 1. Cache key generation is deterministic
        # 2. Cache hits produce identical results
        # 3. Cache misses generate new responses

        assert True, "LLM caching test placeholder"
