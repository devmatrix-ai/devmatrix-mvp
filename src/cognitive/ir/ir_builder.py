"""
IR Builder.

Responsible for constructing the initial ApplicationIR from SpecRequirements.
This acts as the bridge between the "Analysis Phase" (SpecRequirements) and the "Generation Phase" (ApplicationIR).
"""
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute, Relationship, DataType, RelationshipType
from src.cognitive.ir.api_model import APIModelIR, Endpoint, HttpMethod, ParameterLocation, APIParameter
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, DatabaseType, ObservabilityConfig
from src.cognitive.ir.behavior_model import BehaviorModelIR, Invariant, Flow, FlowType
from src.cognitive.ir.validation_model import ValidationModelIR, ValidationRule, ValidationType, EnforcementType

# Import actual SpecRequirements from parser
from src.parsing.spec_parser import SpecRequirements

# Import business logic extractor
from src.services.business_logic_extractor import BusinessLogicExtractor

class IRBuilder:
    """Builder for ApplicationIR."""

    @staticmethod
    def build_from_spec(spec: SpecRequirements) -> ApplicationIR:
        """
        Convert SpecRequirements to ApplicationIR.
        """
        # 1. Build Domain Model
        domain_model = IRBuilder._build_domain_model(spec)

        # 2. Build API Model
        api_model = IRBuilder._build_api_model(spec)

        # 3. Build Infrastructure Model
        infrastructure_model = IRBuilder._build_infrastructure_model(spec)

        # 4. Build Behavior Model
        behavior_model = IRBuilder._build_behavior_model(spec)

        # 5. Build Validation Model
        validation_model = IRBuilder._build_validation_model(spec)

        # 6. Construct Root IR
        return ApplicationIR(
            name=spec.metadata.get("spec_name", "Generated App"),
            description=spec.metadata.get("description", ""),
            domain_model=domain_model,
            api_model=api_model,
            infrastructure_model=infrastructure_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            phase_status={"init": "completed"}
        )

    @staticmethod
    def _build_domain_model(spec: SpecRequirements) -> DomainModelIR:
        entities = []
        for entity_spec in spec.entities:
            attributes = []
            # entity_spec.fields is a list of Field objects
            for field in entity_spec.fields:
                attributes.append(Attribute(
                    name=field.name,
                    data_type=IRBuilder._map_data_type(field.type),
                    is_primary_key=field.primary_key,
                    is_nullable=not field.required,
                    is_unique=field.unique,
                    default_value=field.default,
                    description=field.description,
                    constraints={"raw": field.constraints} if field.constraints else {}
                ))
            
            entities.append(Entity(
                name=entity_spec.name,
                attributes=attributes,
                description=entity_spec.description
            ))
            
        return DomainModelIR(entities=entities)

    @staticmethod
    def _build_api_model(spec: SpecRequirements) -> APIModelIR:
        endpoints = []
        for ep_spec in spec.endpoints:
            # ep_spec is Endpoint object from parser
            endpoints.append(Endpoint(
                path=ep_spec.path,
                method=HttpMethod(ep_spec.method.upper()),
                operation_id=f"{ep_spec.method.lower()}_{ep_spec.path.replace('/', '_').strip('_')}",
                description=ep_spec.description,
                tags=[ep_spec.entity] if hasattr(ep_spec, 'entity') and ep_spec.entity else []
            ))
            
        return APIModelIR(endpoints=endpoints)

    @staticmethod
    def _build_infrastructure_model(spec: SpecRequirements) -> InfrastructureModelIR:
        # Default to Postgres + Neo4j + Qdrant as per standard stack
        db_config = DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            port=5432,
            name="app_db",
            user="postgres",
            password_env_var="DB_PASSWORD"
        )
        
        return InfrastructureModelIR(
            database=db_config,
            observability=ObservabilityConfig()
        )

    @staticmethod
    def _build_behavior_model(spec: SpecRequirements) -> BehaviorModelIR:
        invariants = []
        flows = []
        
        # Extract from business_logic
        for logic in spec.business_logic:
            if logic.type == "validation":
                # Heuristic: Treat validations as invariants for now
                invariants.append(Invariant(
                    entity="Unknown", # Need better entity extraction from logic
                    description=logic.description,
                    enforcement_level="strict"
                ))
            elif logic.type == "state_machine":
                flows.append(Flow(
                    name="State Transition",
                    type=FlowType.STATE_TRANSITION,
                    trigger="State Change",
                    description=logic.description
                ))
                
        return BehaviorModelIR(invariants=invariants, flows=flows)

    @staticmethod
    def _build_validation_model(spec: SpecRequirements) -> ValidationModelIR:
        rules = []

        # Extract from entity fields (basic rules)
        for entity in spec.entities:
            for field in entity.fields:
                if field.required:
                    rules.append(ValidationRule(
                        entity=entity.name,
                        attribute=field.name,
                        type=ValidationType.PRESENCE,
                        error_message=f"{field.name} is required"
                    ))
                if field.unique:
                    rules.append(ValidationRule(
                        entity=entity.name,
                        attribute=field.name,
                        type=ValidationType.UNIQUENESS,
                        error_message=f"{field.name} must be unique"
                    ))
                # Extract constraints
                if field.constraints:
                    for constraint in field.constraints:
                        rules.append(ValidationRule(
                            entity=entity.name,
                            attribute=field.name,
                            type=ValidationType.CUSTOM,
                            condition=constraint
                        ))

        # Use BusinessLogicExtractor for complex business logic rules
        try:
            # Convert spec to dict format that BusinessLogicExtractor expects
            # CRITICAL: Include description for enforcement type detection!
            spec_dict = {
                "name": spec.metadata.get("spec_name", ""),
                "entities": [
                    {
                        "name": entity.name,
                        "fields": [
                            {
                                "name": field.name,
                                "type": field.type,
                                "description": field.description or "",  # ✅ CRITICAL for enforcement detection
                                "constraints": field.constraints or {},
                                "unique": field.unique
                            }
                            for field in entity.fields
                        ]
                    }
                    for entity in spec.entities
                ]
            }

            extractor = BusinessLogicExtractor()
            business_logic_model = extractor.extract_validation_rules(spec_dict)
            rules.extend(business_logic_model.rules)
            logger.info(f"BusinessLogicExtractor added {len(business_logic_model.rules)} rules")
        except Exception as e:
            # If extraction fails, log error and continue with basic rules
            logger.error(f"BusinessLogicExtractor failed: {e}", exc_info=True)
            pass

        # Optimize enforcement placement for each rule
        optimized_rules = [IRBuilder._optimize_enforcement_placement(rule) for rule in rules]

        return ValidationModelIR(rules=optimized_rules)

    @staticmethod
    def _optimize_enforcement_placement(rule: ValidationRule) -> ValidationRule:
        """
        Optimize where enforcement rules are applied based on their type.

        Routing logic:
        - VALIDATOR: schema + entity (unique → also service for uniqueness check)
        - IMMUTABLE: schema + entity
        - COMPUTED_FIELD: entity only
        - STATE_MACHINE: service + endpoint
        - BUSINESS_LOGIC: service only
        - DESCRIPTION: no enforcement
        """
        if rule.enforcement is None or rule.enforcement_type == EnforcementType.DESCRIPTION:
            # No enforcement placement needed
            return rule

        enforcement_type = rule.enforcement_type

        # Determine optimal applied_at locations
        if enforcement_type == EnforcementType.VALIDATOR:
            # Validators always go in schema + entity
            if rule.enforcement.applied_at is None:
                rule.enforcement.applied_at = []

            # Ensure schema and entity are included
            if "schema" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("schema")
            if "entity" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("entity")

            # For uniqueness constraints, also apply at service level
            if rule.type == ValidationType.UNIQUENESS:
                if "service" not in rule.enforcement.applied_at:
                    rule.enforcement.applied_at.append("service")

        elif enforcement_type == EnforcementType.IMMUTABLE:
            # Immutable fields: schema + entity (read-only, no updates)
            if rule.enforcement.applied_at is None:
                rule.enforcement.applied_at = []

            if "schema" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("schema")
            if "entity" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("entity")

        elif enforcement_type == EnforcementType.COMPUTED_FIELD:
            # Computed fields: entity only (calculated at model level)
            if rule.enforcement.applied_at is None:
                rule.enforcement.applied_at = []

            if "entity" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("entity")

        elif enforcement_type == EnforcementType.STATE_MACHINE:
            # State machines: service + endpoint (workflow enforcement)
            if rule.enforcement.applied_at is None:
                rule.enforcement.applied_at = []

            if "service" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("service")
            if "endpoint" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("endpoint")

        elif enforcement_type == EnforcementType.BUSINESS_LOGIC:
            # Business logic: service only (orchestration, complex rules)
            if rule.enforcement.applied_at is None:
                rule.enforcement.applied_at = []

            if "service" not in rule.enforcement.applied_at:
                rule.enforcement.applied_at.append("service")

        return rule

    @staticmethod
    def _map_data_type(type_str: str) -> DataType:
        type_str = type_str.lower()
        if "int" in type_str:
            return DataType.INTEGER
        elif "float" in type_str or "decimal" in type_str:
            return DataType.FLOAT
        elif "bool" in type_str:
            return DataType.BOOLEAN
        elif "date" in type_str or "time" in type_str:
            return DataType.DATETIME
        elif "uuid" in type_str:
            return DataType.UUID
        else:
            return DataType.STRING
