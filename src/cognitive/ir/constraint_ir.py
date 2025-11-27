"""
Phase 3: Typed Constraint IR for IR-native matching.

ALIGNED WITH PHASE 4: Uses ValidationType and EnforcementType directly.
No duplicate enums - Phase 2 SemanticNormalizer already normalized to these types.
"""

from dataclasses import dataclass
from typing import Optional, Any, List

from src.cognitive.ir.validation_model import (
    ValidationType,
    EnforcementType,
    EnforcementStrategy,
    ValidationRule,
)
from src.services.production_code_generators import normalize_field_name


@dataclass
class ConstraintIR:
    """
    Typed constraint representation for IR-native matching.

    PHASE 4 ALIGNED: Uses ValidationType and EnforcementType directly.
    No duplicate enums - Phase 2 SemanticNormalizer already normalized to these types.

    This is the intermediate representation for comparing spec constraints
    against code constraints at the IR level (Phase 3).
    """

    entity: str
    field: str
    validation_type: ValidationType  # Phase 4 enum
    constraint_type: str  # Specific type from normalization (for dedup key)
    value: Optional[Any] = None
    enforcement_type: EnforcementType = EnforcementType.DESCRIPTION
    enforcement: Optional[EnforcementStrategy] = None
    confidence: float = 1.0
    source: str = "ir"

    @property
    def canonical_key(self) -> str:
        """Unique identifier for deduplication."""
        return f"{self.entity}.{self.field}.{self.constraint_type}"

    @property
    def validation_type_key(self) -> str:
        """ValidationType-level key for fuzzy matching."""
        return f"{self.entity}.{self.field}.{self.validation_type.value}"

    @property
    def field_key(self) -> str:
        """Field-level key for broad matching."""
        return f"{self.entity}.{self.field}"

    def matches_exactly(self, other: 'ConstraintIR') -> bool:
        """Exact IR match - same entity, field, type, value."""
        return (
            self.entity == other.entity and
            self.field == other.field and
            self.constraint_type == other.constraint_type and
            self._values_match(self.value, other.value)
        )

    def matches_validation_type(self, other: 'ConstraintIR') -> bool:
        """ValidationType-level match - same entity, field, validation_type."""
        return (
            self.entity == other.entity and
            self.field == other.field and
            self.validation_type == other.validation_type
        )

    def matches_field(self, other: 'ConstraintIR') -> bool:
        """Field-level match - same entity and field."""
        return (
            self.entity == other.entity and
            self.field == other.field
        )

    def _values_match(self, v1: Any, v2: Any) -> bool:
        """Check if two values are semantically equivalent."""
        if v1 is None or v2 is None:
            return True  # None matches anything

        # Numeric comparison with tolerance
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return abs(v1 - v2) < 0.001

        # List comparison (order-independent)
        if isinstance(v1, list) and isinstance(v2, list):
            return set(map(str, v1)) == set(map(str, v2))

        # String comparison (case-insensitive)
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.lower() == v2.lower()

        return v1 == v2

    @classmethod
    def from_validation_rule(cls, rule: ValidationRule) -> 'ConstraintIR':
        """
        Convert Phase 4 ValidationRule to ConstraintIR.

        PHASE 4 ALIGNED: ValidationRule already has ValidationType and EnforcementType.
        Direct mapping - no inference needed.
        """
        return cls(
            entity=rule.entity,
            field=rule.attribute,
            validation_type=rule.type,
            constraint_type=rule.type.value,
            value=rule.condition,
            enforcement_type=rule.enforcement_type,
            enforcement=rule.enforcement,
            confidence=1.0,
            source="validation_model"
        )

    @classmethod
    def from_validation_string(cls, s: str) -> 'ConstraintIR':
        """
        Parse validation string to ConstraintIR.

        Formats supported:
        - "Entity.field: constraint_type"
        - "Entity.field: constraint_type=value"
        - "Entity.field: constraint_type: value1, value2"

        Examples:
        - "Product.id: unique" -> ConstraintIR(entity="Product", field="id", constraint_type="unique")
        - "Customer.email: pattern=^[^@]+@..." -> ConstraintIR(entity="Customer", field="email", ...)
        """
        # Mapping from constraint strings to ValidationType
        # ValidationType values: FORMAT, RANGE, PRESENCE, UNIQUENESS, RELATIONSHIP,
        # STOCK_CONSTRAINT, STATUS_TRANSITION, WORKFLOW_CONSTRAINT, CUSTOM
        CONSTRAINT_TO_VALIDATION_TYPE = {
            # Uniqueness constraints
            "unique": ValidationType.UNIQUENESS,
            "primary_key": ValidationType.UNIQUENESS,
            # Presence constraints
            "required": ValidationType.PRESENCE,
            "non-empty": ValidationType.PRESENCE,
            "min_length": ValidationType.PRESENCE,
            "max_length": ValidationType.RANGE,
            # Range constraints
            "gt": ValidationType.RANGE,
            "ge": ValidationType.RANGE,
            "lt": ValidationType.RANGE,
            "le": ValidationType.RANGE,
            "greater_than_zero": ValidationType.RANGE,
            "positive": ValidationType.RANGE,
            "non_negative": ValidationType.RANGE,
            # Format constraints
            "pattern": ValidationType.FORMAT,
            "valid_email_format": ValidationType.FORMAT,
            "email": ValidationType.FORMAT,
            # Status/enum constraints
            "enum_values": ValidationType.STATUS_TRANSITION,
            "enum": ValidationType.STATUS_TRANSITION,
            # Relationship constraints
            "foreign_key": ValidationType.RELATIONSHIP,
            "foreign_key_customer": ValidationType.RELATIONSHIP,
            "foreign_key_product": ValidationType.RELATIONSHIP,
            # Workflow constraints (auto-generated, read-only)
            # Keys use underscores because lookup does .replace("-", "_")
            "auto_generated": ValidationType.WORKFLOW_CONSTRAINT,
            "auto_calculated": ValidationType.WORKFLOW_CONSTRAINT,
            "default": ValidationType.WORKFLOW_CONSTRAINT,
            "default_true": ValidationType.WORKFLOW_CONSTRAINT,
            "default_factory": ValidationType.WORKFLOW_CONSTRAINT,
            "read_only": ValidationType.WORKFLOW_CONSTRAINT,
            "snapshot": ValidationType.WORKFLOW_CONSTRAINT,
        }

        # Parse: "Entity.field: constraint_type" or "Entity.field: constraint_type=value"
        try:
            # Split on first ": "
            if ": " not in s:
                # Fallback: treat whole thing as constraint
                return cls(
                    entity="Unknown",
                    field="unknown",
                    validation_type=ValidationType.CUSTOM,
                    constraint_type=s,
                    value=None,
                    source="string_parse"
                )

            entity_field, rest = s.split(": ", 1)

            # Parse entity.field
            if "." in entity_field:
                entity, field = entity_field.rsplit(".", 1)
                # Bug #14 Fix: Normalize field names (e.g., creation_date -> created_at)
                field = normalize_field_name(field)
            else:
                entity = entity_field
                field = "unknown"

            # Parse constraint_type and value
            value = None
            constraint_type = rest

            # Check for "=" value format
            if "=" in rest and not rest.startswith("enum"):
                constraint_type, value = rest.split("=", 1)

            # Check for ": value1, value2" format (enums)
            elif rest.count(": ") >= 1:
                parts = rest.split(": ", 1)
                constraint_type = parts[0]
                if len(parts) > 1:
                    value = [v.strip() for v in parts[1].split(",")]

            # Map to ValidationType
            validation_type = CONSTRAINT_TO_VALIDATION_TYPE.get(
                constraint_type.lower().replace("-", "_"),
                ValidationType.CUSTOM
            )

            return cls(
                entity=entity,
                field=field,
                validation_type=validation_type,
                constraint_type=constraint_type,
                value=value,
                source="string_parse"
            )
        except Exception:
            # Fallback for unparseable strings
            return cls(
                entity="Unknown",
                field="unknown",
                validation_type=ValidationType.CUSTOM,
                constraint_type=s,
                value=None,
                source="string_parse_fallback"
            )

    @classmethod
    def from_dict(cls, data: dict) -> 'ConstraintIR':
        """Create ConstraintIR from dictionary."""
        return cls(
            entity=data.get("entity", ""),
            field=data.get("field", ""),
            validation_type=ValidationType(data.get("validation_type", "custom")),
            constraint_type=data.get("constraint_type", ""),
            value=data.get("value"),
            enforcement_type=EnforcementType(data.get("enforcement_type", "description")),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "dict"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "entity": self.entity,
            "field": self.field,
            "validation_type": self.validation_type.value,
            "constraint_type": self.constraint_type,
            "value": self.value,
            "enforcement_type": self.enforcement_type.value,
            "confidence": self.confidence,
            "source": self.source,
        }

    def to_string(self) -> str:
        """Convert to string for embedding fallback (ONLY when needed)."""
        value_str = f"={self.value}" if self.value is not None else ""
        return f"{self.entity}.{self.field}: {self.constraint_type}{value_str}"

    def __repr__(self) -> str:
        return f"ConstraintIR({self.canonical_key}, type={self.validation_type.value}, val={self.value})"

    def __hash__(self) -> int:
        return hash(self.canonical_key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConstraintIR):
            return False
        return self.canonical_key == other.canonical_key


def validation_model_to_constraint_irs(validation_model) -> List[ConstraintIR]:
    """
    Convert ValidationModelIR to list of ConstraintIRs.

    Args:
        validation_model: ValidationModelIR instance

    Returns:
        List of ConstraintIR objects
    """
    constraints = []
    for rule in validation_model.rules:
        constraints.append(ConstraintIR.from_validation_rule(rule))
    return constraints
