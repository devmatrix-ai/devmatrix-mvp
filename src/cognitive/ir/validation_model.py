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

class ValidationRule(BaseModel):
    entity: str
    attribute: str
    type: ValidationType
    condition: Optional[str] = None
    error_message: Optional[str] = None
    severity: str = "error" # error, warning

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
