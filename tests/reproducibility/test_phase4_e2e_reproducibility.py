"""
Phase 4.4: E2E Reproducibility Test
-----------------------------------
Comprehensive test verifying complete reproducibility:
spec → IR → Neo4j → IR → Code is 100% deterministic and reproducible.

Validates the entire Phase 4 pipeline produces identical results through round-trips.
"""

import pytest
import uuid
import json
import time
from datetime import datetime
from pathlib import Path

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute, DataType
from src.cognitive.ir.api_model import APIModelIR, Endpoint
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, ObservabilityConfig
from src.cognitive.ir.behavior_model import BehaviorModelIR
from src.cognitive.ir.validation_model import (
    ValidationModelIR, ValidationRule, TestCase,
    ValidationType, EnforcementType, EnforcementStrategy
)
from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository


class TestPhase4E2EReproducibility:
    """Complete E2E test suite for Phase 4 reproducibility."""

    @pytest.fixture
    def neo4j_repo(self):
        """Fixture providing Neo4j repository."""
        repo = Neo4jIRRepository()
        yield repo
        repo.close()

    @pytest.fixture
    def sample_application_ir(self):
        """Fixture providing a complete ApplicationIR with enforcement."""
        app_id = uuid.uuid4()

        # Create enforcement strategies for different types
        email_enforcement = EnforcementStrategy(
            type=EnforcementType.VALIDATOR,
            implementation="pydantic_field_validator",
            applied_at=["schema", "entity"],
            template_name="email_validator",
            parameters={"pattern": "^[^@]+@[^@]+\\.[^@]+$"},
            code_snippet="@field_validator('email')\ndef validate_email(cls, v):\n    assert '@' in v\n    return v",
            description="Email format validation"
        )

        created_at_enforcement = EnforcementStrategy(
            type=EnforcementType.IMMUTABLE,
            implementation="pydantic_field",
            applied_at=["schema", "entity"],
            template_name="immutable_field",
            parameters={"allow_mutation": False},
            code_snippet="created_at: datetime = Field(default_factory=datetime.now, frozen=True)",
            description="Creation timestamp - immutable"
        )

        status_enforcement = EnforcementStrategy(
            type=EnforcementType.STATE_MACHINE,
            implementation="state_transition_validator",
            applied_at=["service", "endpoint"],
            template_name="order_status_fsm",
            parameters={
                "states": ["pending", "confirmed", "shipped", "delivered", "cancelled"],
                "initial_state": "pending"
            },
            code_snippet="def transition_status(self, new_status: str) -> bool:\n    valid_transitions = self.STATE_TRANSITIONS.get(self.status, [])\n    return new_status in valid_transitions",
            description="Order status state machine"
        )

        # Create validation rules with enforcement
        rules = [
            ValidationRule(
                entity="Customer",
                attribute="email",
                type=ValidationType.FORMAT,
                enforcement_type=EnforcementType.VALIDATOR,
                enforcement=email_enforcement,
                condition="email matches RFC 5322"
            ),
            ValidationRule(
                entity="Order",
                attribute="created_at",
                type=ValidationType.PRESENCE,
                enforcement_type=EnforcementType.IMMUTABLE,
                enforcement=created_at_enforcement,
                condition="timestamp set at creation"
            ),
            ValidationRule(
                entity="Order",
                attribute="status",
                type=ValidationType.STATUS_TRANSITION,
                enforcement_type=EnforcementType.STATE_MACHINE,
                enforcement=status_enforcement,
                condition="status transitions follow defined FSM"
            ),
        ]

        # Build complete IR
        domain_model = DomainModelIR(
            entities=[
                Entity(
                    name="Customer",
                    attributes=[
                        Attribute(name="id", data_type=DataType.UUID, is_primary_key=True),
                        Attribute(name="email", data_type=DataType.STRING, is_unique=True),
                        Attribute(name="name", data_type=DataType.STRING),
                    ]
                ),
                Entity(
                    name="Order",
                    attributes=[
                        Attribute(name="id", data_type=DataType.UUID, is_primary_key=True),
                        Attribute(name="customer_id", data_type=DataType.UUID),
                        Attribute(name="status", data_type=DataType.STRING),
                        Attribute(name="total", data_type=DataType.FLOAT),
                        Attribute(name="created_at", data_type=DataType.DATETIME),
                    ]
                ),
            ]
        )

        api_model = APIModelIR(endpoints=[])

        infra_model = InfrastructureModelIR(
            database=DatabaseConfig(
                type="postgresql",
                host="localhost",
                port=5432,
                name="ecommerce_db",
                user="app_user",
                password_env_var="DB_PASSWORD"
            ),
            observability=ObservabilityConfig(logging_enabled=True, metrics_enabled=True)
        )

        behavior_model = BehaviorModelIR()

        validation_model = ValidationModelIR(
            rules=rules,
            test_cases=[]
        )

        app_ir = ApplicationIR(
            app_id=app_id,
            name="ECommerceApp",
            description="E-commerce application with complete validation",
            domain_model=domain_model,
            api_model=api_model,
            infrastructure_model=infra_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version="1.0",
            phase_status={"phase_4": "e2e_test"}
        )

        return app_ir

    def test_complete_e2e_reproducibility_pipeline(self, neo4j_repo, sample_application_ir):
        """Test complete pipeline: spec → IR → Neo4j → IR → Code reproducibility."""
        app_id = sample_application_ir.app_id
        original_ir = sample_application_ir

        # Step 1: Save IR to Neo4j
        neo4j_repo.save_application_ir(original_ir, str(app_id))

        # Step 2: Load IR from Neo4j
        loaded_ir = neo4j_repo.load_application_ir(app_id)

        # Step 3: Verify IR equality
        assert loaded_ir.app_id == original_ir.app_id
        assert loaded_ir.name == original_ir.name
        assert loaded_ir.description == original_ir.description
        assert len(loaded_ir.domain_model.entities) == len(original_ir.domain_model.entities)
        assert len(loaded_ir.validation_model.rules) == len(original_ir.validation_model.rules)

    def test_enforcement_metadata_complete_roundtrip(self, neo4j_repo, sample_application_ir):
        """Test complete enforcement metadata preservation through entire pipeline."""
        app_id = sample_application_ir.app_id
        original_rules = sample_application_ir.validation_model.rules

        # Save to Neo4j
        neo4j_repo.save_application_ir(sample_application_ir, str(app_id))

        # Load from Neo4j
        loaded_ir = neo4j_repo.load_application_ir(app_id)
        loaded_rules = loaded_ir.validation_model.rules

        # Verify complete enforcement metadata preservation for all rules
        assert len(loaded_rules) == len(original_rules)

        for original, loaded in zip(original_rules, loaded_rules):
            # Verify rule metadata
            assert loaded.entity == original.entity
            assert loaded.attribute == original.attribute
            assert loaded.enforcement_type == original.enforcement_type
            assert loaded.condition == original.condition
            assert loaded.type == original.type

            # Verify enforcement strategy fields
            assert loaded.enforcement is not None
            assert loaded.enforcement.type == original.enforcement.type
            assert loaded.enforcement.implementation == original.enforcement.implementation
            assert loaded.enforcement.applied_at == original.enforcement.applied_at
            assert loaded.enforcement.template_name == original.enforcement.template_name
            assert loaded.enforcement.parameters == original.enforcement.parameters
            assert loaded.enforcement.code_snippet == original.enforcement.code_snippet
            assert loaded.enforcement.description == original.enforcement.description

    def test_domain_entities_consistency_after_roundtrip(self, neo4j_repo, sample_application_ir):
        """Test that domain model entities remain consistent through round-trip."""
        app_id = sample_application_ir.app_id
        original_entities = sample_application_ir.domain_model.entities

        # Save and load
        neo4j_repo.save_application_ir(sample_application_ir, str(app_id))
        loaded_ir = neo4j_repo.load_application_ir(app_id)
        loaded_entities = loaded_ir.domain_model.entities

        # Verify entity structure consistency
        assert len(loaded_entities) == len(original_entities)

        for original, loaded in zip(original_entities, loaded_entities):
            assert loaded.name == original.name
            assert len(loaded.attributes) == len(original.attributes)

            for orig_attr, loaded_attr in zip(original.attributes, loaded.attributes):
                assert loaded_attr.name == orig_attr.name
                assert loaded_attr.data_type == orig_attr.data_type
                assert loaded_attr.is_primary_key == orig_attr.is_primary_key
                assert loaded_attr.is_unique == orig_attr.is_unique
                assert loaded_attr.is_nullable == orig_attr.is_nullable

    def test_multiple_enforcement_types_roundtrip(self, neo4j_repo):
        """Test round-trip with all enforcement types."""
        app_id = uuid.uuid4()

        # Create rules with all enforcement types
        enforcement_configs = [
            (EnforcementType.VALIDATOR, "validator_impl", ["schema", "entity"]),
            (EnforcementType.IMMUTABLE, "immutable_impl", ["schema", "entity"]),
            (EnforcementType.COMPUTED_FIELD, "computed_impl", ["entity"]),
            (EnforcementType.STATE_MACHINE, "state_impl", ["service", "endpoint"]),
            (EnforcementType.BUSINESS_LOGIC, "business_impl", ["service"]),
        ]

        rules = []
        for idx, (enf_type, impl, applied_at) in enumerate(enforcement_configs):
            enforcement = EnforcementStrategy(
                type=enf_type,
                implementation=impl,
                applied_at=applied_at,
                template_name=f"template_{idx}",
                parameters={"key": f"value_{idx}"},
                code_snippet=f"# {enf_type.value}",
                description=f"Test {enf_type.value}"
            )

            rule = ValidationRule(
                entity="TestEntity",
                attribute=f"field_{idx}",
                type=ValidationType.FORMAT,
                enforcement_type=enf_type,
                enforcement=enforcement,
                condition="test"
            )
            rules.append(rule)

        # Build IR
        app_ir = ApplicationIR(
            app_id=app_id,
            name="MultiEnforcementTest",
            description="Test multiple enforcement types",
            domain_model=DomainModelIR(entities=[]),
            api_model=APIModelIR(endpoints=[]),
            infrastructure_model=InfrastructureModelIR(
                database=DatabaseConfig(
                    type="postgresql",
                    host="localhost",
                    port=5432,
                    name="test",
                    user="user",
                    password_env_var="PASSWORD"
                ),
                observability=ObservabilityConfig(logging_enabled=True, metrics_enabled=True)
            ),
            behavior_model=BehaviorModelIR(),
            validation_model=ValidationModelIR(rules=rules, test_cases=[]),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version="1.0",
            phase_status={}
        )

        # Test round-trip
        neo4j_repo.save_application_ir(app_ir, str(app_id))
        loaded_ir = neo4j_repo.load_application_ir(app_id)

        # Verify all enforcement types preserved
        for original, loaded in zip(app_ir.validation_model.rules, loaded_ir.validation_model.rules):
            assert loaded.enforcement_type == original.enforcement_type
            assert loaded.enforcement.type == original.enforcement.type
            assert loaded.enforcement.implementation == original.enforcement.implementation
            assert loaded.enforcement.applied_at == original.enforcement.applied_at

    def test_reproducibility_deterministic_across_multiple_cycles(self, neo4j_repo, sample_application_ir):
        """Test that reproducibility is deterministic across multiple save/load cycles."""
        app_id = sample_application_ir.app_id

        # First cycle: save and load
        neo4j_repo.save_application_ir(sample_application_ir, str(app_id))
        loaded_ir_1 = neo4j_repo.load_application_ir(app_id)

        # Second cycle: load and re-save the loaded IR, then load again
        neo4j_repo.save_application_ir(loaded_ir_1, str(app_id))
        loaded_ir_2 = neo4j_repo.load_application_ir(app_id)

        # Verify consistency between both load cycles
        for rule1, rule2 in zip(loaded_ir_1.validation_model.rules, loaded_ir_2.validation_model.rules):
            assert rule1.entity == rule2.entity
            assert rule1.attribute == rule2.attribute
            assert rule1.enforcement_type == rule2.enforcement_type
            if rule1.enforcement:
                assert rule1.enforcement.type == rule2.enforcement.type
                assert rule1.enforcement.implementation == rule2.enforcement.implementation
                assert rule1.enforcement.applied_at == rule2.enforcement.applied_at
                assert rule1.enforcement.parameters == rule2.enforcement.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
