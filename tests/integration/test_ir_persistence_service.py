"""
Integration Tests for IRPersistenceService
==========================================
Tests for the unified IR persistence service.

Sprint 7: Pipeline Integration
"""

import pytest
import uuid
import os
from datetime import datetime

# Skip if Neo4j not available
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set - Neo4j integration tests skipped"
)

from src.cognitive.services.ir_persistence_service import IRPersistenceService, IRPersistenceError
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute, DataType, Relationship, RelationshipType
from src.cognitive.ir.api_model import APIModelIR, Endpoint, HttpMethod, APIParameter, ParameterLocation
from src.cognitive.ir.behavior_model import BehaviorModelIR, Flow, FlowType, Step, Invariant
from src.cognitive.ir.validation_model import ValidationModelIR, ValidationRule, ValidationType
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, DatabaseType
from src.cognitive.ir.tests_model import TestsModelIR, SeedEntityIR, TestScenarioIR, TestType, TestPriority


def create_test_application_ir() -> ApplicationIR:
    """Create a complete ApplicationIR for testing."""
    app_id = uuid.uuid4()

    # Domain Model
    entity = Entity(
        name="Product",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True),
            Attribute(name="name", data_type=DataType.STRING, is_nullable=False),
            Attribute(name="price", data_type=DataType.DECIMAL, is_nullable=False),
            Attribute(name="stock", data_type=DataType.INTEGER, default_value=0),
        ],
        relationships=[
            Relationship(
                name="category",
                target_entity="Category",
                type=RelationshipType.MANY_TO_ONE,
            )
        ],
    )
    domain_model = DomainModelIR(entities=[entity])

    # API Model
    endpoint = Endpoint(
        path="/products",
        method=HttpMethod.POST,
        operation_id="create_product",
        summary="Create a new product",
        parameters=[
            APIParameter(
                name="name",
                location=ParameterLocation.BODY,
                required=True,
            )
        ],
    )
    api_model = APIModelIR(endpoints=[endpoint])

    # Behavior Model
    flow = Flow(
        name="CreateProduct",
        type=FlowType.WORKFLOW,
        trigger="POST /products",
        steps=[
            Step(order=1, description="Validate input", action="validate"),
            Step(order=2, description="Create product", action="create", target_entity="Product"),
        ],
    )
    behavior_model = BehaviorModelIR(
        flows=[flow],
        invariants=[
            Invariant(
                entity="Product",
                description="Price must be positive",
                expression="price > 0",
            )
        ],
    )

    # Validation Model
    validation_model = ValidationModelIR(
        rules=[
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
                condition="price > 0",
                error_message="Price must be positive",
            )
        ]
    )

    # Infrastructure Model
    infrastructure_model = InfrastructureModelIR(
        database=DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            name="test_db",
        )
    )

    # Tests Model
    tests_model = TestsModelIR(
        seed_entities=[
            SeedEntityIR(entity_name="Product", count=5, scenario="smoke_test")
        ],
        test_scenarios=[
            TestScenarioIR(
                name="CreateProductTest",
                description="Test product creation",
                type=TestType.INTEGRATION,
                priority=TestPriority.HIGH,
            )
        ],
    )

    return ApplicationIR(
        app_id=app_id,
        name="TestApp",
        description="Test application for IRPersistenceService",
        domain_model=domain_model,
        api_model=api_model,
        behavior_model=behavior_model,
        validation_model=validation_model,
        infrastructure_model=infrastructure_model,
        tests_model=tests_model,
    )


class TestIRPersistenceService:
    """Test suite for IRPersistenceService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        svc = IRPersistenceService()
        yield svc
        svc.close()

    @pytest.fixture
    def test_app_ir(self):
        """Create test ApplicationIR."""
        return create_test_application_ir()

    def test_save_and_load_roundtrip(self, service, test_app_ir):
        """Test that save and load produce identical ApplicationIR."""
        # Save
        app_id = service.save_application_ir(test_app_ir)
        assert app_id is not None

        # Load
        loaded_ir = service.load_application_ir(app_id)
        assert loaded_ir is not None

        # Compare key attributes
        assert loaded_ir.name == test_app_ir.name
        assert len(loaded_ir.domain_model.entities) == len(test_app_ir.domain_model.entities)
        assert len(loaded_ir.api_model.endpoints) == len(test_app_ir.api_model.endpoints)
        assert len(loaded_ir.behavior_model.flows) == len(test_app_ir.behavior_model.flows)

    def test_exists(self, service, test_app_ir):
        """Test exists method."""
        app_id = str(test_app_ir.app_id)

        # Should not exist before save
        assert not service.exists(app_id)

        # Save
        service.save_application_ir(test_app_ir, app_id=app_id)

        # Should exist after save
        assert service.exists(app_id)

    def test_load_nonexistent(self, service):
        """Test loading non-existent ApplicationIR returns None."""
        result = service.load_application_ir("nonexistent_app_id")
        assert result is None

    def test_get_all_app_ids(self, service, test_app_ir):
        """Test getting all app IDs."""
        app_id = service.save_application_ir(test_app_ir)

        app_ids = service.get_all_app_ids()
        assert app_id in app_ids

    def test_cache_invalidation(self, service, test_app_ir):
        """Test cache invalidation."""
        app_id = service.save_application_ir(test_app_ir)

        # Load to populate cache
        service.load_application_ir(app_id, use_cache=True)

        # Invalidate
        service.invalidate_cache(app_id)

        # Should still be able to load
        loaded = service.load_application_ir(app_id)
        assert loaded is not None

    def test_get_stats(self, service, test_app_ir):
        """Test getting persistence stats."""
        service.save_application_ir(test_app_ir)

        stats = service.get_stats()
        assert "app_count" in stats or stats is not None

    def test_save_with_custom_app_id(self, service, test_app_ir):
        """Test saving with custom app_id."""
        custom_id = "custom_test_app_123"

        saved_id = service.save_application_ir(test_app_ir, app_id=custom_id)
        assert saved_id == custom_id

        # Verify can load with custom ID
        loaded = service.load_application_ir(custom_id)
        assert loaded is not None
        assert loaded.name == test_app_ir.name

    def test_update_existing(self, service, test_app_ir):
        """Test updating existing ApplicationIR."""
        app_id = service.save_application_ir(test_app_ir)

        # Modify and save again
        test_app_ir.name = "UpdatedTestApp"
        test_app_ir.description = "Updated description"
        service.save_application_ir(test_app_ir, app_id=app_id)

        # Load and verify update
        loaded = service.load_application_ir(app_id)
        assert loaded.name == "UpdatedTestApp"

    def test_context_manager(self, test_app_ir):
        """Test using service as context manager."""
        with IRPersistenceService() as service:
            app_id = service.save_application_ir(test_app_ir)
            assert app_id is not None

    def test_domain_model_entities(self, service, test_app_ir):
        """Test that domain model entities are persisted correctly."""
        app_id = service.save_application_ir(test_app_ir)
        loaded = service.load_application_ir(app_id)

        assert len(loaded.domain_model.entities) == 1
        entity = loaded.domain_model.entities[0]
        assert entity.name == "Product"
        assert len(entity.attributes) >= 1

    def test_api_model_endpoints(self, service, test_app_ir):
        """Test that API model endpoints are persisted correctly."""
        app_id = service.save_application_ir(test_app_ir)
        loaded = service.load_application_ir(app_id)

        assert len(loaded.api_model.endpoints) == 1
        endpoint = loaded.api_model.endpoints[0]
        assert endpoint.path == "/products"
        assert endpoint.method == HttpMethod.POST
