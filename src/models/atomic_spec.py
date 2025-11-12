"""
AtomicSpec Model - Atomic Specification (Pre-Generation)

Pydantic model for atomic specifications generated BEFORE code.
Represents a ~10 LOC atomic unit with complete context for generation.

This is Fase 2 (Proactive Atomization):
- Specs generated BEFORE code
- Validated BEFORE generation
- Deterministic (temp=0, seed=42)
- 10 LOC target

Author: DevMatrix Team
Date: 2025-11-12
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class AtomicSpec(BaseModel):
    """
    Atomic Specification - 10 LOC target

    Specification generated BEFORE code generation.
    Represents one atomic unit (~10 LOC) with complete execution context.

    Atomicity Criteria:
    1. Single responsibility (one verb)
    2. Size: 5-15 LOC (target: 10)
    3. Complexity: ≤3.0
    4. Testable: Clear I/O with test cases
    5. Type-safe: Explicit types
    6. Independent: No shared state
    7. Deterministic: Same input = same output
    8. Context-complete: All imports/dependencies specified
    """

    # Identification
    spec_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique spec identifier"
    )
    task_id: UUID = Field(
        ...,
        description="Foreign key to MasterPlanTask"
    )
    sequence_number: int = Field(
        ...,
        ge=1,
        description="Sequence number within task (1..N)"
    )

    # Description
    description: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="Precise description of WHAT this atom does (max 200 chars)"
    )

    # Types and Context
    input_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Input parameter types: {'param_name': 'Type'}"
    )
    output_type: str = Field(
        ...,
        min_length=1,
        description="Return type of the function/block"
    )

    # Atomicity Metrics
    target_loc: int = Field(
        default=10,
        ge=5,
        le=15,
        description="Target lines of code (goal: 10, min 5, max 15)"
    )
    complexity_limit: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Maximum cyclomatic complexity allowed"
    )

    # Dependencies and Context
    imports_required: List[str] = Field(
        default_factory=list,
        description="Required imports: ['from x import y', 'import z']"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Spec IDs this depends on (other AtomicSpec instances)"
    )

    # Execution Conditions
    preconditions: List[str] = Field(
        default_factory=list,
        description="Required state/conditions before execution"
    )
    postconditions: List[str] = Field(
        default_factory=list,
        description="Expected state/conditions after execution"
    )

    # Testing
    test_cases: List[Dict] = Field(
        default_factory=list,
        description="Input/output test examples: [{'input': {...}, 'output': ...}]"
    )

    # Functional Constraints
    must_be_pure: bool = Field(
        default=False,
        description="Must be a pure function (no side effects)"
    )
    must_be_idempotent: bool = Field(
        default=False,
        description="Multiple calls with same input produce same output"
    )

    # Implementation Metadata
    language: str = Field(
        default="python",
        description="Target programming language"
    )
    target_file: Optional[str] = Field(
        default=None,
        description="Target file path for implementation"
    )

    # Validation Fields
    _validated: bool = False
    _validation_errors: List[str] = []

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is concise and actionable"""
        words = v.split()
        if len(words) < 3:
            raise ValueError("Description too short (minimum 3 words required)")

        # Check for single responsibility (max 1 verb in first 5 words)
        action_verbs = ['create', 'update', 'delete', 'validate', 'send', 'fetch',
                        'process', 'parse', 'transform', 'calculate', 'generate']
        verb_count = sum(1 for word in words[:5] if word.lower() in action_verbs)

        if verb_count > 1:
            raise ValueError(
                "Description suggests multiple responsibilities (multiple action verbs). "
                "Each spec should have ONE clear purpose."
            )

        return v

    @field_validator('test_cases')
    @classmethod
    def validate_test_cases(cls, v: List[Dict]) -> List[Dict]:
        """Ensure at least one test case with valid structure"""
        if len(v) < 1:
            raise ValueError("At least one test case required for testability")

        # Validate test case structure
        for i, test_case in enumerate(v):
            if 'input' not in test_case:
                raise ValueError(f"Test case {i} missing 'input' field")
            if 'output' not in test_case:
                raise ValueError(f"Test case {i} missing 'output' field")

        return v

    @field_validator('imports_required')
    @classmethod
    def validate_imports(cls, v: List[str]) -> List[str]:
        """Ensure imports are valid Python import statements"""
        for imp in v:
            imp_lower = imp.strip().lower()
            if not (imp_lower.startswith('import ') or imp_lower.startswith('from ')):
                raise ValueError(
                    f"Invalid import statement: '{imp}'. "
                    f"Must start with 'import' or 'from'"
                )
        return v

    @field_validator('dependencies')
    @classmethod
    def validate_dependencies(cls, v: List[str]) -> List[str]:
        """Ensure dependencies are valid spec IDs (UUIDs)"""
        for dep_id in v:
            try:
                UUID(dep_id)
            except ValueError:
                raise ValueError(f"Invalid dependency spec_id: '{dep_id}' (must be UUID)")
        return v

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "spec_id": self.spec_id,
            "task_id": str(self.task_id),
            "sequence_number": self.sequence_number,
            "description": self.description,
            "input_types": self.input_types,
            "output_type": self.output_type,
            "target_loc": self.target_loc,
            "complexity_limit": self.complexity_limit,
            "imports_required": self.imports_required,
            "dependencies": self.dependencies,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "test_cases": self.test_cases,
            "must_be_pure": self.must_be_pure,
            "must_be_idempotent": self.must_be_idempotent,
            "language": self.language,
            "target_file": self.target_file
        }

    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "spec_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_id": "660e8400-e29b-41d4-a716-446655440001",
                "sequence_number": 1,
                "description": "Validate user email format using regex pattern",
                "input_types": {
                    "email": "str"
                },
                "output_type": "bool",
                "target_loc": 10,
                "complexity_limit": 2.0,
                "imports_required": [
                    "import re"
                ],
                "dependencies": [],
                "preconditions": [
                    "email is not None",
                    "email is str"
                ],
                "postconditions": [
                    "returns True if valid email format",
                    "returns False if invalid email format"
                ],
                "test_cases": [
                    {
                        "input": {"email": "test@example.com"},
                        "output": True
                    },
                    {
                        "input": {"email": "invalid-email"},
                        "output": False
                    },
                    {
                        "input": {"email": ""},
                        "output": False
                    }
                ],
                "must_be_pure": True,
                "must_be_idempotent": True,
                "language": "python",
                "target_file": "src/utils/validators.py"
            }
        }


class AtomicSpecValidationResult(BaseModel):
    """
    Result of AtomicSpec validation

    Contains validation status, errors, and warnings.
    """

    is_valid: bool = Field(
        ...,
        description="Whether the spec passed validation"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Critical validation errors (prevent code generation)"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical warnings (suggestions for improvement)"
    )
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Validation score (0.0-1.0)"
    )

    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"Validation Result: {status} (score: {self.score:.2f})\n"
            f"Errors: {len(self.errors)}\n"
            f"Warnings: {len(self.warnings)}"
        )
