"""
Phase 4.3: Neo4j Enforcement Persistence Tests
----------------------------------------------
Tests for saving and loading enforcement strategies from Neo4j.

Ensures complete round-trip fidelity:
spec → IR → Neo4j → IR → Code is deterministic and reproducible.
"""

import pytest
import uuid
import json
from datetime import datetime

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


class TestNeo4jEnforcementPersistence:
    """Test suite for Neo4j enforcement strategy persistence."""

    @pytest.fixture
    def neo4j_repo(self):
        """Fixture providing Neo4j repository."""
        repo = Neo4jIRRepository()
        yield repo
        repo.close()

    @pytest.fixture
    def sample_ir_with_enforcement(self):
        """Fixture providing ApplicationIR with enforcement strategies."""
        app_id = uuid.uuid4()

        # Create a validation rule with enforcement
        enforcement = EnforcementStrategy(
            type=EnforcementType.VALIDATOR,
            implementation="pydantic_field_validator",
            applied_at=["schema", "entity"],
            template_name="email_validator",
            parameters={"pattern": "^[^@]+@[^@]+\\.[^@]+$"},
            code_snippet="@field_validator('email')\ndef validate_email(cls, v):\n    assert '@' in v\n    return v",
            description="Email format validation"
        )

        rule = ValidationRule(
            entity="Customer",
            attribute="email",
            description="Customer email must be unique and valid",
            type=ValidationType.FORMAT,
            enforcement_type=EnforcementType.VALIDATOR,
            enforcement=enforcement,
            condition="email matches RFC 5322",
            impact="PREVENT_INVALID_DATA"
        )

        # Create IR with enforcement
        domain_model = DomainModelIR(
            entities=[Entity(
                name="Customer",
                attributes=[
                    Attribute(name="email", data_type=DataType.STRING, description="Email address")
                ]
            )]
        )

        api_model = APIModelIR(endpoints=[])
        infra_model = InfrastructureModelIR(
            database=DatabaseConfig(
                type="postgresql",
                host="localhost",
                port=5432,
                name="test",
                user="test_user",
                password_env_var="TEST_PASSWORD"
            ),
            observability=ObservabilityConfig(logging_enabled=True, metrics_enabled=True)
        )
        behavior_model = BehaviorModelIR()

        validation_model = ValidationModelIR(
            rules=[rule],
            test_cases=[]
        )

        app_ir = ApplicationIR(
            app_id=app_id,
            name="TestApp",
            description="Test application with enforcement",
            domain_model=domain_model,
            api_model=api_model,
            infrastructure_model=infra_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version="1.0",
            phase_status={}
        )

        return app_ir

    def test_save_enforcement_to_neo4j(self, neo4j_repo, sample_ir_with_enforcement):
        """Test saving enforcement strategies to Neo4j."""
        app_id = str(sample_ir_with_enforcement.app_id)

        # Save the IR
        neo4j_repo.save_application_ir(sample_ir_with_enforcement, app_id)

        # Verify by querying Neo4j directly
        with neo4j_repo.driver.session() as session:
            result = session.run(
                """
                MATCH (enforcement:EnforcementStrategy {app_id: $app_id})
                RETURN enforcement
                """,
                {"app_id": app_id}
            )
            enforcement_nodes = list(result)

        # Should have at least one enforcement node
        assert len(enforcement_nodes) > 0, "No enforcement nodes found in Neo4j"

        # Verify enforcement node content
        enforcement_node = enforcement_nodes[0]["enforcement"]
        assert enforcement_node["type"] == "validator"
        assert enforcement_node["implementation"] == "pydantic_field_validator"
        assert enforcement_node["template_name"] == "email_validator"
        assert json.loads(enforcement_node["applied_at"]) == ["schema", "entity"]

    def test_load_enforcement_from_neo4j(self, neo4j_repo, sample_ir_with_enforcement):
        """Test loading enforcement strategies from Neo4j."""
        app_id = sample_ir_with_enforcement.app_id

        # Save the IR
        neo4j_repo.save_application_ir(sample_ir_with_enforcement, str(app_id))

        # Load it back
        loaded_ir = neo4j_repo.load_application_ir(app_id)

        # Verify enforcement was loaded
        assert len(loaded_ir.validation_model.rules) > 0
        loaded_rule = loaded_ir.validation_model.rules[0]

        assert loaded_rule.enforcement is not None, "Enforcement not loaded"
        assert loaded_rule.enforcement.type == EnforcementType.VALIDATOR
        assert loaded_rule.enforcement.implementation == "pydantic_field_validator"
        assert loaded_rule.enforcement.applied_at == ["schema", "entity"]
        assert loaded_rule.enforcement.template_name == "email_validator"

    def test_round_trip_enforcement(self, neo4j_repo, sample_ir_with_enforcement):
        """Test complete round-trip: save → load → verify identical."""
        app_id = sample_ir_with_enforcement.app_id
        original_rule = sample_ir_with_enforcement.validation_model.rules[0]

        # Save
        neo4j_repo.save_application_ir(sample_ir_with_enforcement, str(app_id))

        # Load
        loaded_ir = neo4j_repo.load_application_ir(app_id)
        loaded_rule = loaded_ir.validation_model.rules[0]

        # Compare enforcement metadata
        assert loaded_rule.enforcement_type == original_rule.enforcement_type
        assert loaded_rule.enforcement.type == original_rule.enforcement.type
        assert loaded_rule.enforcement.implementation == original_rule.enforcement.implementation
        assert loaded_rule.enforcement.applied_at == original_rule.enforcement.applied_at
        assert loaded_rule.enforcement.template_name == original_rule.enforcement.template_name
        assert loaded_rule.enforcement.parameters == original_rule.enforcement.parameters
        assert loaded_rule.enforcement.code_snippet == original_rule.enforcement.code_snippet
        assert loaded_rule.enforcement.description == original_rule.enforcement.description

    def test_enforcement_metadata_preservation_roundtrip(self, neo4j_repo):
        """Test that all enforcement metadata fields are preserved through round-trip."""
        app_id = uuid.uuid4()

        # Create multiple enforcement types
        enforcements_to_test = [
            (EnforcementType.VALIDATOR, "validator_impl", ["schema", "entity"]),
            (EnforcementType.IMMUTABLE, "immutable_impl", ["schema", "entity"]),
            (EnforcementType.COMPUTED_FIELD, "computed_impl", ["entity"]),
            (EnforcementType.STATE_MACHINE, "state_machine_impl", ["service", "endpoint"]),
            (EnforcementType.BUSINESS_LOGIC, "business_logic_impl", ["service"]),
        ]

        rules = []
        for idx, (enf_type, impl, applied_at) in enumerate(enforcements_to_test):
            enforcement = EnforcementStrategy(
                type=enf_type,
                implementation=impl,
                applied_at=applied_at,
                template_name=f"template_{idx}",
                parameters={"param_key": f"param_value_{idx}"},
                code_snippet=f"// Code for {enf_type.value}",
                description=f"Test enforcement {enf_type.value}"
            )

            rule = ValidationRule(
                entity="TestEntity",
                attribute=f"field_{idx}",
                description=f"Field {idx} with {enf_type.value}",
                type=ValidationType.FORMAT,
                enforcement_type=enf_type,
                enforcement=enforcement,
                condition=f"condition_{idx}",
                impact="PREVENT_INVALID_DATA"
            )
            rules.append(rule)

        # Build IR
        app_ir = ApplicationIR(
            app_id=app_id,
            name="MetadataTest",
            description="Test enforcement metadata preservation",
            domain_model=DomainModelIR(entities=[]),
            api_model=APIModelIR(endpoints=[]),
            infrastructure_model=InfrastructureModelIR(
                database=DatabaseConfig(
                    type="postgresql",
                    host="localhost",
                    port=5432,
                    name="test",
                    user="test_user",
                    password_env_var="TEST_PASSWORD"
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

        # Save and load
        neo4j_repo.save_application_ir(app_ir, str(app_id))
        loaded_ir = neo4j_repo.load_application_ir(app_id)

        # Verify all enforcement metadata preserved
        for original, loaded in zip(app_ir.validation_model.rules, loaded_ir.validation_model.rules):
            assert loaded.enforcement_type == original.enforcement_type
            assert loaded.enforcement.type == original.enforcement.type
            assert loaded.enforcement.implementation == original.enforcement.implementation
            assert loaded.enforcement.applied_at == original.enforcement.applied_at
            assert loaded.enforcement.template_name == original.enforcement.template_name
            assert loaded.enforcement.parameters == original.enforcement.parameters
            assert loaded.enforcement.code_snippet == original.enforcement.code_snippet
            assert loaded.enforcement.description == original.enforcement.description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
