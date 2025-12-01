"""
Pattern-Aware Generator - Bug #164 Fix

Applies learned anti-patterns to AST/TEMPLATE code generation WITHOUT using LLM.
This enables the 94% of code (non-LLM stratum) to benefit from learning.

Architecture:
    NegativePatternStore (learned patterns)
           │
           ▼
    PatternAwareGenerator.get_adjustments()
           │
           ▼
    AST Generator (production_code_generators.py)
           │
           ▼
    Generated Code (pattern-aware)

Design Principles:
1. NO LLM - purely deterministic adjustments
2. Pattern matching by entity/field names
3. Adjustments are optional overrides, not mandatory
4. Graceful degradation if pattern store unavailable

Created: 2025-11-30 (Bug #164)
Reference: DOCS/mvp/exit/learning/LEARNING_ARCHITECTURE_GAPS_2025-11-30.md
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FieldAdjustment:
    """Adjustment to apply to a field during code generation."""
    field_name: str
    adjustment_type: str  # nullable, default, type_change, validation
    value: Any
    reason: str  # Why this adjustment exists (from pattern)
    pattern_id: str  # Source pattern for traceability


@dataclass
class EntityAdjustments:
    """All adjustments for a single entity."""
    entity_name: str
    field_adjustments: Dict[str, FieldAdjustment] = field(default_factory=dict)
    relationship_adjustments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validation_adjustments: List[Dict[str, Any]] = field(default_factory=list)


class PatternAwareGenerator:
    """
    Wrapper that injects pattern awareness into AST/TEMPLATE generation.

    Bug #164 Fix: Enables 94% of code (non-LLM) to benefit from learned patterns.

    Usage:
        pattern_store = get_negative_pattern_store()
        pag = PatternAwareGenerator(pattern_store)

        # Get adjustments for an entity
        adjustments = pag.get_entity_adjustments("Product")

        # Apply to AST generation
        if adjustments.field_adjustments.get("category_id"):
            # Make category_id nullable based on learned pattern
            field_def = adjustments.field_adjustments["category_id"]
            ...
    """

    # Common error patterns and their deterministic fixes
    PATTERN_TO_ADJUSTMENT = {
        # IntegrityError on FK → make nullable
        "IntegrityError": {
            "adjustment_type": "nullable",
            "value": True,
            "reason": "FK constraint error - making nullable to allow orphan records"
        },
        # ValidationError on required field → add default
        "ValidationError": {
            "adjustment_type": "default",
            "value": None,  # Will use field-specific default
            "reason": "Validation error - adding default value"
        },
        # TypeError on field → type coercion
        "TypeError": {
            "adjustment_type": "type_coerce",
            "value": True,
            "reason": "Type error - enabling coercion"
        },
        # AttributeError on relationship → lazy load
        "AttributeError": {
            "adjustment_type": "lazy_load",
            "value": "select",
            "reason": "Attribute error - changing to lazy loading"
        },
        # Schema validation error (Field required) → make optional
        "FieldRequired": {
            "adjustment_type": "optional",
            "value": True,
            "reason": "Field required error - making optional in schema"
        },
    }

    def __init__(self, pattern_store=None):
        """
        Initialize PatternAwareGenerator.

        Args:
            pattern_store: NegativePatternStore instance (optional, will try to get singleton)
        """
        self._pattern_store = pattern_store
        self._cache: Dict[str, EntityAdjustments] = {}
        self._patterns_applied = 0
        self._entities_adjusted = 0

        # Try to get pattern store if not provided
        if self._pattern_store is None:
            try:
                from src.learning.negative_pattern_store import get_negative_pattern_store
                self._pattern_store = get_negative_pattern_store()
                logger.debug("PatternAwareGenerator: Connected to NegativePatternStore")
            except Exception as e:
                logger.warning(f"PatternAwareGenerator: No pattern store available: {e}")
                self._pattern_store = None

    def get_entity_adjustments(self, entity_name: str) -> EntityAdjustments:
        """
        Get all adjustments for an entity based on learned patterns.

        Args:
            entity_name: Name of the entity (e.g., "Product", "Cart")

        Returns:
            EntityAdjustments with field/relationship/validation modifications
        """
        # Check cache first
        if entity_name in self._cache:
            return self._cache[entity_name]

        adjustments = EntityAdjustments(entity_name=entity_name)

        if not self._pattern_store:
            return adjustments

        try:
            # Query patterns for this entity
            patterns = self._pattern_store.get_patterns_for_entity(entity_name)

            if not patterns:
                # Also try with common suffixes
                patterns = self._pattern_store.get_patterns_for_entity(f"{entity_name}Entity")

            for pattern in patterns:
                self._apply_pattern_to_adjustments(pattern, adjustments)
                self._patterns_applied += 1

            if adjustments.field_adjustments:
                self._entities_adjusted += 1
                logger.info(
                    f"🎓 PatternAwareGenerator: {len(adjustments.field_adjustments)} adjustments "
                    f"for {entity_name} from {len(patterns)} patterns"
                )

            # Cache result
            self._cache[entity_name] = adjustments

        except Exception as e:
            logger.warning(f"PatternAwareGenerator: Error querying patterns for {entity_name}: {e}")

        return adjustments

    def _apply_pattern_to_adjustments(
        self,
        pattern,  # GenerationAntiPattern
        adjustments: EntityAdjustments
    ) -> None:
        """
        Convert a pattern into concrete adjustments.

        Uses the pattern's exception class to determine adjustment type.
        """
        exception_class = getattr(pattern, 'exception_class', 'Unknown')
        field_pattern = getattr(pattern, 'field_pattern', None)
        endpoint_pattern = getattr(pattern, 'endpoint_pattern', '*')
        pattern_id = getattr(pattern, 'pattern_id', 'unknown')

        # Determine adjustment based on exception type
        adjustment_config = self.PATTERN_TO_ADJUSTMENT.get(exception_class, {})

        if not adjustment_config:
            # Try to match partial exception names
            for exc_type, config in self.PATTERN_TO_ADJUSTMENT.items():
                if exc_type in exception_class:
                    adjustment_config = config
                    break

        if not adjustment_config:
            logger.debug(f"No adjustment mapping for exception: {exception_class}")
            return

        # Extract field name from pattern
        field_name = self._extract_field_from_pattern(pattern)

        if field_name:
            # Create field adjustment
            adjustments.field_adjustments[field_name] = FieldAdjustment(
                field_name=field_name,
                adjustment_type=adjustment_config["adjustment_type"],
                value=adjustment_config["value"],
                reason=adjustment_config["reason"],
                pattern_id=pattern_id
            )

        # Check for relationship patterns (FK errors)
        if "IntegrityError" in exception_class and "_id" in (field_pattern or ""):
            # This is likely a FK relationship issue
            related_entity = self._extract_related_entity(field_pattern)
            if related_entity:
                adjustments.relationship_adjustments[field_pattern] = {
                    "nullable": True,
                    "ondelete": "SET NULL",
                    "reason": f"FK constraint error on {field_pattern}",
                    "pattern_id": pattern_id
                }

    def _extract_field_from_pattern(self, pattern) -> Optional[str]:
        """Extract field name from pattern error message or field_pattern."""
        # Try field_pattern first
        field_pattern = getattr(pattern, 'field_pattern', None)
        if field_pattern and field_pattern != "*":
            return field_pattern

        # Try to extract from error message
        error_msg = getattr(pattern, 'error_message_pattern', '')

        # Look for common field patterns in error messages
        # "null value in column 'category_id'" → category_id
        # "field 'price' is required" → price
        if "column" in error_msg.lower():
            # Extract between quotes after "column"
            parts = error_msg.split("'")
            for i, part in enumerate(parts):
                if "column" in part.lower() and i + 1 < len(parts):
                    return parts[i + 1]

        if "field" in error_msg.lower():
            parts = error_msg.split("'")
            for i, part in enumerate(parts):
                if "field" in part.lower() and i + 1 < len(parts):
                    return parts[i + 1]

        return None

    def _extract_related_entity(self, field_name: str) -> Optional[str]:
        """Extract related entity name from FK field."""
        if not field_name:
            return None

        # product_id → Product
        # category_id → Category
        # customer_id → Customer
        if field_name.endswith("_id"):
            entity = field_name[:-3]  # Remove _id
            return entity.capitalize()

        return None

    def get_field_overrides(self, entity_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get field overrides in a format ready for AST generators.

        Returns:
            Dict mapping field names to override configurations

        Example:
            {
                "category_id": {"nullable": True},
                "price": {"default": 0.0},
            }
        """
        adjustments = self.get_entity_adjustments(entity_name)
        overrides = {}

        for field_name, adj in adjustments.field_adjustments.items():
            if adj.adjustment_type == "nullable":
                overrides[field_name] = {"nullable": adj.value}
            elif adj.adjustment_type == "default":
                overrides[field_name] = {"default": adj.value}
            elif adj.adjustment_type == "lazy_load":
                overrides[field_name] = {"lazy": adj.value}
            elif adj.adjustment_type == "optional":
                overrides[field_name] = {"optional": adj.value}

        # Add relationship overrides
        for field_name, rel_adj in adjustments.relationship_adjustments.items():
            if field_name not in overrides:
                overrides[field_name] = {}
            overrides[field_name].update(rel_adj)

        return overrides

    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "patterns_applied": self._patterns_applied,
            "entities_adjusted": self._entities_adjusted,
            "cached_entities": len(self._cache),
            "pattern_store_available": self._pattern_store is not None,
        }

    def clear_cache(self) -> None:
        """Clear the adjustments cache."""
        self._cache.clear()


# Singleton instance
_pattern_aware_generator: Optional[PatternAwareGenerator] = None


def get_pattern_aware_generator() -> PatternAwareGenerator:
    """Get or create singleton PatternAwareGenerator."""
    global _pattern_aware_generator
    if _pattern_aware_generator is None:
        _pattern_aware_generator = PatternAwareGenerator()
    return _pattern_aware_generator


def get_field_overrides_for_entity(entity_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to get field overrides for an entity.

    Usage in AST generators:
        overrides = get_field_overrides_for_entity("Product")
        if "category_id" in overrides:
            field_kwargs.update(overrides["category_id"])
    """
    pag = get_pattern_aware_generator()
    return pag.get_field_overrides(entity_name)
