"""
Phase 2: Semantic Normalizer.

Converts extracted constraints from any source (OpenAPI, AST-Pydantic, AST-SQLAlchemy,
business logic) into canonical ApplicationIR form, enabling IR-native matching (Phase 3).

PHASE 4 ALIGNED: Uses ValidationType and EnforcementType directly.
CRITICAL: Single entry point for constraint normalization - all raw constraints → NormalizedRule.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict, Tuple
from enum import Enum

from src.cognitive.ir.validation_model import (
    ValidationType,
    EnforcementType,
    EnforcementStrategy,
)
from src.cognitive.ir.application_ir import ApplicationIR

logger = logging.getLogger(__name__)


@dataclass
class ConstraintRule:
    """Raw extracted constraint from any source."""
    entity: str              # "Product", "product", "PRODUCT"
    field: str               # "price", "unit_price", "unitPrice"
    constraint_type: str     # "range", "gt", "greater_than", "min"
    value: Optional[Any] = None     # 0, "0", [0, 1000]
    enforcement_type: str = "validator"    # "validator", "database", "computed"
    source: str = "unknown"  # "openapi" | "ast_pydantic" | "ast_sqlalchemy" | "business_logic"
    confidence: float = 0.95  # Source confidence (before normalization)


@dataclass
class NormalizedRule:
    """Canonical ApplicationIR form - aligned with Phase 4 ValidationRule."""
    entity: str              # Canonical entity name (from IR)
    field: str               # Canonical field name (from IR)
    validation_type: ValidationType  # Phase 4 enum (FORMAT, RANGE, PRESENCE, etc.)
    constraint_type: str     # Specific type from normalization
    value: Optional[Any] = None     # Normalized value
    enforcement_type: EnforcementType = EnforcementType.VALIDATOR
    enforcement: Optional[EnforcementStrategy] = None
    confidence: float = 1.0  # Confidence after normalization
    original_rule: Optional[ConstraintRule] = None
    normalization_path: str = "unknown"  # Trace how normalization was achieved


class SemanticNormalizer:
    """
    Normalizes constraints from multiple sources to canonical IR form.

    PHASE 4 ALIGNED: Simplified because Phase 2 already normalized types.
    Single responsibility: Convert raw constraints → NormalizedRule with Phase 4 types.
    """

    # Source reliability (higher number = lower priority when merging)
    SOURCE_PRIORITY = {
        "ast_sqlalchemy": 1,   # Highest reliability (database schema)
        "ast_pydantic": 2,     # Model validation
        "openapi": 3,          # API schema
        "business_logic": 4,   # Inferred patterns
        "unknown": 5,          # Lowest priority
    }

    # Confidence penalties for different match types
    CONFIDENCE_PENALTIES = {
        "exact_match": 0.0,           # Perfect: entity=Product, field=price
        "case_variation": 0.02,       # product → Product
        "case_conversion": 0.05,      # unit_price → unitPrice
        "plural_singular": 0.08,      # items → item
        "synonym_mapping": 0.12,      # price → unitPrice (from aliases)
        "pattern_inference": 0.20,    # Inferred from pattern
        "fallback": 0.40,             # Couldn't resolve
    }

    def __init__(self, application_ir: ApplicationIR):
        """
        Initialize with ApplicationIR providing canonical forms.

        Args:
            application_ir: ApplicationIR with entities, fields, and validation rules
        """
        self.ir = application_ir
        self._build_lookup_tables()

    def _build_lookup_tables(self):
        """Build fast lookup tables for entity/field resolution."""
        # Entity lookup: lowercase → canonical name
        self.entity_lookup = {}
        if hasattr(self.ir, 'domain_model') and self.ir.domain_model:
            for entity in self.ir.domain_model.entities:
                entity_name = entity.name
                # Add exact match (lowercase)
                self.entity_lookup[entity_name.lower()] = entity_name

                # Add plural forms (bidirectional)
                # Example: Product → product, products
                # Example: Orders → orders, order
                plural = self._pluralize(entity_name)
                singular = self._singularize(entity_name)

                if plural.lower() != entity_name.lower():
                    self.entity_lookup[plural.lower()] = entity_name
                if singular.lower() != entity_name.lower():
                    self.entity_lookup[singular.lower()] = entity_name

        # Field lookup: (entity, lowercase field) → canonical field name
        self.field_lookup = {}
        if hasattr(self.ir, 'domain_model') and self.ir.domain_model:
            for entity in self.ir.domain_model.entities:
                entity_fields = {}
                for attr in entity.attributes:
                    entity_fields[attr.name.lower()] = attr.name
                    # snake_case ↔ camelCase variants
                    if '_' in attr.name:  # snake_case
                        camel = self._snake_to_camel(attr.name)
                        entity_fields[camel.lower()] = attr.name
                    elif any(c.isupper() for c in attr.name[1:]):  # camelCase
                        snake = self._camel_to_snake(attr.name)
                        entity_fields[snake.lower()] = attr.name

                self.field_lookup[entity.name] = entity_fields

    def normalize_rule(self, rule: ConstraintRule) -> NormalizedRule:
        """
        Convert extracted rule to canonical ApplicationIR form.

        Algorithm:
        1. Resolve entity name → canonical entity
        2. Resolve field name → canonical field (within entity)
        3. Normalize constraint type → canonical type (ValidationType)
        4. Map enforcement type → canonical enforcement
        5. Return NormalizedRule with confidence score

        Args:
            rule: ConstraintRule from extraction

        Returns:
            NormalizedRule with Phase 4 types and confidence

        Raises:
            ValueError: If entity or field cannot be resolved (no fallback)
        """
        match_path = []

        # Step 1: Entity normalization
        canonical_entity, entity_match = self._resolve_entity(rule.entity)
        if not canonical_entity:
            raise ValueError(f"Cannot resolve entity: {rule.entity}")
        match_path.append(f"entity:{entity_match}")

        # Step 2: Field normalization
        canonical_field, field_match = self._resolve_field(canonical_entity, rule.field)
        if not canonical_field:
            raise ValueError(
                f"Cannot resolve field '{rule.field}' in entity '{canonical_entity}'"
            )
        match_path.append(f"field:{field_match}")

        # Step 3: Constraint type normalization
        canonical_type, type_match = self._resolve_constraint_type(
            rule.constraint_type, canonical_entity, canonical_field
        )
        if not canonical_type:
            raise ValueError(f"Cannot resolve constraint type: {rule.constraint_type}")
        match_path.append(f"type:{type_match}")

        # Step 4: Enforcement mapping
        canonical_enforcement = self._map_enforcement_type(rule.enforcement_type)

        # Step 5: Value normalization (type-specific)
        normalized_value = self._normalize_value(
            canonical_type, rule.value, canonical_field
        )

        # Step 6: Compute confidence
        confidence = self._compute_confidence(
            rule,
            entity_match=entity_match,
            field_match=field_match,
            type_match=type_match,
            value_changed=(normalized_value != rule.value),
        )

        return NormalizedRule(
            entity=canonical_entity,
            field=canonical_field,
            validation_type=canonical_type,
            constraint_type=rule.constraint_type,
            value=normalized_value,
            enforcement_type=canonical_enforcement,
            confidence=confidence,
            original_rule=rule,
            normalization_path=" → ".join(match_path),
        )

    def _resolve_entity(self, entity_name: str) -> Tuple[Optional[str], str]:
        """
        Resolve entity name to canonical form.

        Returns:
            (canonical_name, match_type) or (None, "no_match")

        Examples:
          "Product" → ("Product", "exact_match")
          "product" → ("Product", "case_variation")
          "items" → ("Item", "plural_singular")
        """
        if not entity_name:
            return None, "empty"

        # Exact match (case-insensitive)
        canonical = self.entity_lookup.get(entity_name.lower())
        if canonical:
            if canonical == entity_name:
                return canonical, "exact_match"
            else:
                return canonical, "case_variation"

        # Fallback: try to find via IR entities directly
        if hasattr(self.ir, 'domain_model') and self.ir.domain_model:
            for entity in self.ir.domain_model.entities:
                if entity.name.lower() == entity_name.lower():
                    return entity.name, "case_variation"

        return None, "no_match"

    def _resolve_field(self, entity: str, field_name: str) -> Tuple[Optional[str], str]:
        """
        Resolve field name within entity to canonical form.

        Returns:
            (canonical_field, match_type) or (None, "no_match")

        Examples:
          (Product, unit_price) → (price, case_conversion) [if alias exists]
          (Product, unitPrice) → (unitPrice, exact_match)
          (Product, PRICE) → (price, case_variation)
        """
        if not field_name:
            return None, "empty"

        # Get field lookup for this entity
        field_map = self.field_lookup.get(entity, {})

        # Exact match (case-insensitive)
        canonical = field_map.get(field_name.lower())
        if canonical:
            if canonical == field_name:
                return canonical, "exact_match"
            else:
                return canonical, "case_variation"

        # Try direct IR lookup as fallback
        if hasattr(self.ir, 'domain_model') and self.ir.domain_model:
            for ent in self.ir.domain_model.entities:
                if ent.name == entity:
                    for attr in ent.attributes:
                        if attr.name.lower() == field_name.lower():
                            if attr.name == field_name:
                                return attr.name, "exact_match"
                            else:
                                return attr.name, "case_variation"

        return None, "no_match"

    def _resolve_constraint_type(
        self,
        constraint_type: str,
        entity: str,
        field: str,
    ) -> Tuple[Optional[ValidationType], str]:
        """
        Resolve constraint type to canonical ValidationType enum.

        Examples:
          "EmailStr" → (ValidationType.FORMAT, "pattern_inference")
          "gt=0" → (ValidationType.RANGE, "pattern_inference")
          "unique" → (ValidationType.UNIQUENESS, "direct_match")
          "PRIMARY KEY" → (ValidationType.UNIQUENESS, "pattern_inference")
          "required" → (ValidationType.PRESENCE, "pattern_inference")
        """
        if not constraint_type:
            return ValidationType.CUSTOM, "empty"

        constraint_lower = constraint_type.lower()

        # Direct ValidationType match
        for vtype in ValidationType:
            if vtype.value.lower() == constraint_lower or vtype.name.lower() == constraint_lower:
                return vtype, "direct_match"

        # Pattern-based matching
        match_type = "pattern_inference"

        # Email patterns
        if any(p in constraint_lower for p in ["email", "emailstr", "valid email"]):
            return ValidationType.FORMAT, match_type

        # Range patterns (min, max, gt, lt, etc)
        if any(p in constraint_lower for p in ["gt", "greater", "min", ">=", "range"]):
            return ValidationType.RANGE, match_type
        if any(p in constraint_lower for p in ["lt", "less", "max", "<="]):
            return ValidationType.RANGE, match_type

        # Uniqueness patterns
        if "unique" in constraint_lower or "distinct" in constraint_lower:
            return ValidationType.UNIQUENESS, match_type

        # Primary key patterns
        if "primary" in constraint_lower or "pk" in constraint_lower:
            return ValidationType.UNIQUENESS, match_type

        # Immutability patterns
        if any(p in constraint_lower for p in ["exclude", "readonly", "immutable"]):
            # This is enforcement-type info, not validation-type
            # Return CUSTOM but enforcement will be IMMUTABLE
            return ValidationType.CUSTOM, match_type

        # Required/presence patterns
        if any(p in constraint_lower for p in ["required", "not null", "mandatory", "notnull"]):
            return ValidationType.PRESENCE, match_type

        # Computed/read-only patterns
        if "computed" in constraint_lower or "generated" in constraint_lower:
            # This is enforcement-type info
            return ValidationType.CUSTOM, match_type

        # Status/workflow patterns
        if any(p in constraint_lower for p in ["status", "state", "transition", "workflow"]):
            return ValidationType.STATUS_TRANSITION, match_type

        # Relationship patterns
        if any(p in constraint_lower for p in ["foreign", "reference", "fk", "references"]):
            return ValidationType.RELATIONSHIP, match_type

        # Stock/inventory patterns
        if any(p in constraint_lower for p in ["stock", "inventory", "available"]):
            return ValidationType.STOCK_CONSTRAINT, match_type

        # Format patterns (regex, pattern, url, uuid, phone, etc)
        if any(p in constraint_lower for p in ["regex", "pattern", "url", "uuid", "phone", "format"]):
            return ValidationType.FORMAT, match_type

        # Default
        return ValidationType.CUSTOM, "fallback"

    def _map_enforcement_type(self, enforcement_type: str) -> EnforcementType:
        """Map source enforcement type to Phase 4 EnforcementType enum."""
        if not enforcement_type:
            return EnforcementType.VALIDATOR

        enforcement_lower = enforcement_type.lower().replace(" ", "_").replace("-", "_")

        # Direct match
        for etype in EnforcementType:
            if etype.value.lower() == enforcement_lower or etype.name.lower() == enforcement_lower:
                return etype

        # Pattern-based mapping
        mapping = {
            "database": EnforcementType.VALIDATOR,  # DB constraints → validator
            "computed_field": EnforcementType.COMPUTED_FIELD,
            "computed": EnforcementType.COMPUTED_FIELD,
            "immutable": EnforcementType.IMMUTABLE,
            "state_machine": EnforcementType.STATE_MACHINE,
            "workflow": EnforcementType.STATE_MACHINE,
            "business_logic": EnforcementType.BUSINESS_LOGIC,
            "description": EnforcementType.DESCRIPTION,
        }

        return mapping.get(enforcement_lower, EnforcementType.VALIDATOR)

    def _normalize_value(
        self,
        validation_type: ValidationType,
        value: Any,
        field_name: str,
    ) -> Any:
        """
        Normalize constraint value based on type.

        Examples:
          validation_type=RANGE, value="0" → 0
          validation_type=FORMAT, value=None → None
          validation_type=RANGE, value=[0, 100] → [0, 100]
        """
        if value is None:
            return None

        if validation_type == ValidationType.RANGE:
            try:
                if isinstance(value, (int, float)):
                    return value
                if isinstance(value, str):
                    return float(value)
                if isinstance(value, list):
                    return [float(v) if isinstance(v, str) else v for v in value]
            except (ValueError, TypeError):
                return value

        if validation_type == ValidationType.FORMAT:
            # Keep string values as-is
            if isinstance(value, str):
                return value

        if validation_type in [ValidationType.UNIQUENESS, ValidationType.PRESENCE]:
            # These typically don't have values
            return None

        # For other types, keep as-is
        return value

    def _compute_confidence(
        self,
        rule: ConstraintRule,
        entity_match: str,
        field_match: str,
        type_match: str,
        value_changed: bool,
    ) -> float:
        """
        Compute confidence of normalization (0.0-1.0).

        High confidence: Exact matches in IR, reliable sources
        Medium confidence: Fuzzy matches, case variations
        Low confidence: Pattern inference, fallback matches
        """
        base_confidence = 1.0

        # Penalties for match types
        entity_penalty = self.CONFIDENCE_PENALTIES.get(entity_match, 0.15)
        field_penalty = self.CONFIDENCE_PENALTIES.get(field_match, 0.15)
        type_penalty = self.CONFIDENCE_PENALTIES.get(type_match, 0.15)

        # Source reliability penalty (higher number = lower reliability)
        source_penalty_factor = (
            self.SOURCE_PRIORITY.get(rule.source, 5) - 1
        ) * 0.05  # 0% for best, 20% for worst

        # Value transformation penalty
        value_penalty = 0.05 if value_changed else 0.0

        # Total penalty
        total_penalty = (
            entity_penalty + field_penalty + type_penalty + source_penalty_factor + value_penalty
        )

        confidence = max(0.0, base_confidence - total_penalty)
        return round(confidence, 2)

    def normalize_rules(
        self,
        rules: List[ConstraintRule],
    ) -> Tuple[List[NormalizedRule], List[Tuple[ConstraintRule, str]]]:
        """
        Normalize multiple rules, preserving errors as warnings.

        Args:
            rules: List of raw ConstraintRules

        Returns:
            (normalized_rules, errors) where errors are (rule, error_message) tuples
        """
        normalized = []
        errors = []

        for rule in rules:
            try:
                normalized_rule = self.normalize_rule(rule)
                normalized.append(normalized_rule)
            except Exception as e:
                errors.append((rule, str(e)))
                logger.warning(f"Failed to normalize rule {rule.entity}.{rule.field}: {e}")

        logger.info(f"✅ Normalized {len(normalized)} constraints, {len(errors)} errors")
        return normalized, errors

    # Helper methods for pluralization
    @staticmethod
    def _pluralize(word: str) -> str:
        """
        Convert singular to plural form (simple heuristic).

        Examples:
            Product → Products
            Order → Orders
            User → Users
            Category → Categories
        """
        if word.endswith('y'):
            return word[:-1] + 'ies'
        elif word.endswith(('s', 'ss', 'x', 'z', 'ch', 'sh')):
            return word + 'es'
        else:
            return word + 's'

    @staticmethod
    def _singularize(word: str) -> str:
        """
        Convert plural to singular form (simple heuristic).

        Examples:
            Products → Product
            Orders → Order
            Users → User
            Categories → Category
        """
        if word.endswith('ies'):
            return word[:-3] + 'y'
        elif word.endswith('es'):
            # Check if base ends with s, ss, x, z, ch, sh
            base = word[:-2]
            if base.endswith(('s', 'x', 'z')) or base.endswith(('ch', 'sh')):
                return base
            return word
        elif word.endswith('s'):
            return word[:-1]
        else:
            return word

    # Helper methods for case conversion
    @staticmethod
    def _snake_to_camel(name: str) -> str:
        """Convert snake_case to camelCase."""
        parts = name.split('_')
        return parts[0] + ''.join(p.capitalize() for p in parts[1:])

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        result = []
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                result.append('_')
                result.append(c.lower())
            else:
                result.append(c)
        return ''.join(result)


def normalize_rules_sync(
    application_ir: ApplicationIR,
    rules: List[ConstraintRule],
) -> Tuple[List[NormalizedRule], List[Tuple[ConstraintRule, str]]]:
    """
    Synchronous convenience function for normalizing constraints.

    Args:
        application_ir: ApplicationIR providing canonical forms
        rules: List of raw ConstraintRules

    Returns:
        (normalized_rules, errors)
    """
    normalizer = SemanticNormalizer(application_ir)
    return normalizer.normalize_rules(rules)
