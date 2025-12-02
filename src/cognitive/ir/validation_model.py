"""
Validation Model Intermediate Representation.

Defines the validation rules, contract tests, and compliance requirements.
This serves as the source of truth for generating tests and validation logic.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ValidationType(str, Enum):
    FORMAT = "format"               # regex, email, etc.
    RANGE = "range"                # min, max
    PRESENCE = "presence"          # required, not null
    UNIQUENESS = "uniqueness"      # unique constraint
    RELATIONSHIP = "relationship"  # foreign key existence
    STOCK_CONSTRAINT = "stock_constraint"  # inventory availability
    STATUS_TRANSITION = "status_transition"  # valid state changes
    WORKFLOW_CONSTRAINT = "workflow_constraint"  # workflow sequence validation
    CUSTOM = "custom"


class EnforcementType(str, Enum):
    """How validation is enforced in generated code."""
    DESCRIPTION = "description"      # Only description string (NOT real enforcement)
    VALIDATOR = "validator"          # Pydantic @field_validator
    COMPUTED_FIELD = "computed_field"  # Pydantic @computed_field
    IMMUTABLE = "immutable"          # Field(exclude=True) + onupdate=None
    STATE_MACHINE = "state_machine"  # Workflow state transitions
    BUSINESS_LOGIC = "business_logic"  # Service-layer enforcement


class EnforcementStrategy(BaseModel):
    """How to enforce a validation rule in generated code."""
    type: EnforcementType
    implementation: str  # Code pattern or template name
    applied_at: List[str] = Field(default_factory=list)  # ["schema", "entity", "service", "endpoint"]
    template_name: Optional[str] = None  # e.g., "pydantic_validator", "immutable_field"
    parameters: Dict[str, Any] = Field(default_factory=dict)  # Configuration for template
    code_snippet: Optional[str] = None  # Raw code if not using template
    description: Optional[str] = None  # Human-readable explanation


class ValidationRule(BaseModel):
    entity: str
    attribute: str
    type: ValidationType
    condition: Optional[str] = None
    error_message: Optional[str] = None
    severity: str = "error" # error, warning

    # Enforcement strategy (CRITICAL for 100% compliance)
    enforcement_type: EnforcementType = EnforcementType.DESCRIPTION  # Default: no real enforcement
    enforcement: Optional[EnforcementStrategy] = None  # Detailed enforcement strategy
    enforcement_code: Optional[str] = None  # Legacy: Actual enforcement code or template
    applied_at: List[str] = Field(default_factory=list)  # ["schema", "entity", "service"]

class TestCase(BaseModel):
    """Abstract representation of a test case."""
    name: str
    scenario: str
    input_data: Dict[str, Any]
    expected_outcome: str
    validation_rules_covered: List[str] = Field(default_factory=list)

class ValidationModelIR(BaseModel):
    rules: List[ValidationRule] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)

    def get_fk_relationships(self) -> List[Dict[str, str]]:
        """
        Extract FK relationships from RELATIONSHIP validation rules.

        Returns list of dicts with:
        - child_entity: Entity that has the FK
        - child_field: Field name of the FK (e.g., customer_id)
        - parent_entity: Entity being referenced

        This enables domain-agnostic seed ordering without hardcoding entity names.
        """
        relationships = []
        for rule in self.rules:
            if rule.type == ValidationType.RELATIONSHIP:
                # Parse condition to extract parent entity
                # Conditions like: "references Customer", "must exist in Product"
                parent = None
                condition = rule.condition or ""
                condition_lower = condition.lower()

                # Try to extract parent entity from condition
                if "references " in condition_lower:
                    # "references Customer" -> Customer
                    parts = condition.split("references ")
                    if len(parts) > 1:
                        parent = parts[1].strip().split()[0].strip(".,")
                elif "exist in " in condition_lower:
                    # "must exist in Product" -> Product
                    parts = condition.split("exist in ")
                    if len(parts) > 1:
                        parent = parts[1].strip().split()[0].strip(".,")
                elif "_id" in rule.attribute:
                    # Infer from field name: customer_id -> Customer
                    field_base = rule.attribute.replace("_id", "")
                    parent = field_base.title()

                if parent:
                    relationships.append({
                        "child_entity": rule.entity,
                        "child_field": rule.attribute,
                        "parent_entity": parent
                    })

        return relationships

    def get_entity_constraints(self, entity_name: str) -> List[ValidationRule]:
        """Get all validation rules for a specific entity."""
        return [r for r in self.rules if r.entity == entity_name]

    def get_field_constraints(self, entity_name: str, field_name: str) -> List[ValidationRule]:
        """Get all validation rules for a specific field."""
        return [r for r in self.rules if r.entity == entity_name and r.attribute == field_name]
