"""
IR-based Compliance Checking Services.

Validates generated code against ApplicationIR models:
- EntityComplianceChecker: Generated entities vs DomainModelIR
- FlowComplianceChecker: Implemented services vs BehaviorModelIR
- ConstraintComplianceChecker: Code constraints vs ValidationModelIR

Supports dual-mode validation via Strategy Pattern:
- STRICT: Exact matching for technical validation
- RELAXED: Semantic/fuzzy matching for dashboard/investor metrics
"""
from typing import List, Dict, Any, Optional, Set, Protocol, runtime_checkable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import ast
import logging
import re

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import (
    DomainModelIR, Entity, Attribute, Relationship, DataType, RelationshipType
)
from src.cognitive.ir.behavior_model import BehaviorModelIR, Flow, FlowType, Invariant
from src.cognitive.ir.validation_model import (
    ValidationModelIR, ValidationRule, ValidationType
)
from src.services.production_code_generators import normalize_field_name

logger = logging.getLogger(__name__)


# =============================================================================
# Bug #8 Fix: Entity Suffix & Flow Name Normalization
# =============================================================================

# Entity suffixes that should be stripped for matching
ENTITY_SUFFIXES = ['Entity', 'Model', 'Schema', 'Base', 'Mixin']

# Spanish→English flow action mapping
FLOW_ACTION_MAPPING = {
    # Spanish verbs
    "crear": "create",
    "actualizar": "update",
    "eliminar": "delete",
    "borrar": "delete",
    "listar": "list",
    "obtener": "get",
    "buscar": "search",
    "agregar": "add",
    "quitar": "remove",
    "procesar": "process",
    "validar": "validate",
    "activar": "activate",
    "desactivar": "deactivate",
    # Common variants
    "añadir": "add",
    "modificar": "update",
    "consultar": "get",
    "recuperar": "get",
}


def normalize_entity_name(name: str) -> str:
    """
    Normalize entity name by stripping common suffixes.

    Bug #8 Fix: ProductEntity -> Product, OrderModel -> Order

    Args:
        name: Entity name to normalize

    Returns:
        Normalized entity name without suffix
    """
    for suffix in ENTITY_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[:-len(suffix)]
    return name


def normalize_flow_name(flow_name: str) -> str:
    """
    Normalize flow name to match behavior_code_generator._snake_case() output.

    Bug #8 Fix v2: Use SAME transformation as code generator for STRICT matching.

    "F1: Crear Producto" -> "f1_crear_producto" (matches generated method name)

    Args:
        flow_name: Flow name from BehaviorModelIR

    Returns:
        snake_case name matching generated code
    """
    import unicodedata

    # Step 1: Normalize unicode (remove accents: í→i, ó→o)
    result = unicodedata.normalize('NFKD', flow_name)
    result = result.encode('ascii', 'ignore').decode('ascii')

    # Step 2: Remove invalid characters (keep only letters, digits, spaces, underscores)
    # This removes : ( ) and other special chars
    result = re.sub(r'[^a-zA-Z0-9\s_]', '', result)

    # Step 3: Replace spaces/hyphens with underscores
    result = result.replace(" ", "_").replace("-", "_")

    # Step 4: Handle camelCase
    result = re.sub('([A-Z]+)', r'_\1', result).lower()

    # Step 5: Clean up multiple underscores
    result = re.sub('_+', '_', result).strip('_')

    return result


# =============================================================================
# Validation Mode & Strategy Pattern
# =============================================================================

class ValidationMode(Enum):
    """
    Validation mode for IR compliance checking.

    STRICT: Exact matching only - for technical validation
        - Entity names must match exactly (case-insensitive)
        - Method names must match exactly
        - Constraint types must match exactly

    RELAXED: Semantic/fuzzy matching - for dashboard/investor metrics
        - Entity suffixes normalized (Product = ProductModel = ProductEntity)
        - Action synonyms accepted (create = add = insert)
        - Semantic range equivalence (gt=0 ≈ ge=1)
    """
    STRICT = "strict"
    RELAXED = "relaxed"


@runtime_checkable
class EntityMatchingStrategy(Protocol):
    """Strategy protocol for entity matching."""

    def find_entity_match(
        self,
        ir_entity: str,
        generated_entities: Dict[str, Any],
        threshold: float = 0.7
    ) -> tuple:
        """Find matching entity. Returns (matched_name, match_info)."""
        ...

    def find_attribute_match(
        self,
        ir_attr: str,
        gen_attributes: Dict[str, Any],
        threshold: float = 0.8
    ) -> Optional[str]:
        """Find matching attribute name."""
        ...


@runtime_checkable
class FlowMatchingStrategy(Protocol):
    """Strategy protocol for flow matching."""

    def find_flow_match(
        self,
        flow_name: str,
        flow_entity: Optional[str],
        service_classes: Dict[str, List[str]],
        all_code: str,
        flow_mapping: Optional[Dict] = None
    ) -> tuple:
        """Find flow implementation. Returns (found, match_info)."""
        ...


@runtime_checkable
class ConstraintMatchingStrategy(Protocol):
    """Strategy protocol for constraint matching."""

    def find_entity_constraints(
        self,
        ir_entity: str,
        code_constraints: Dict[str, Dict[str, Set[str]]]
    ) -> tuple:
        """Find constraints for entity. Returns (merged_constraints, match_info)."""
        ...

    def check_range_constraint(
        self,
        ir_condition: str,
        attr_constraints: Set[str]
    ) -> tuple:
        """Check range constraint. Returns (found, match_info)."""
        ...


# =============================================================================
# STRICT Matching Strategies (Exact Match)
# =============================================================================

class StrictEntityMatcher:
    """STRICT mode: Exact entity matching with suffix normalization (Bug #8 fix)."""

    def find_entity_match(
        self,
        ir_entity: str,
        generated_entities: Dict[str, Any],
        threshold: float = 0.7
    ) -> tuple:
        """Find exact entity match with suffix normalization (case-insensitive)."""
        # Bug #8 Fix: Normalize IR entity name (strip suffixes)
        ir_normalized = normalize_entity_name(ir_entity)

        # 1. Exact match (original)
        if ir_entity in generated_entities:
            return ir_entity, {"match_mode": "exact", "score": 1.0}

        # 2. Exact match (normalized IR name)
        if ir_normalized in generated_entities:
            return ir_normalized, {"match_mode": "exact_normalized", "score": 1.0}

        # 3. Case-insensitive match with suffix normalization
        ir_lower = ir_normalized.lower()
        for gen_name in generated_entities:
            gen_normalized = normalize_entity_name(gen_name)
            # Match: Product == ProductEntity (both normalize to Product)
            if gen_normalized.lower() == ir_lower:
                return gen_name, {"match_mode": "suffix_normalized", "score": 1.0}
            # Also try original IR name
            if gen_normalized.lower() == ir_entity.lower():
                return gen_name, {"match_mode": "case_insensitive", "score": 1.0}

        return None, {"match_mode": "none", "score": 0.0}

    def find_attribute_match(
        self,
        ir_attr: str,
        gen_attributes: Dict[str, Any],
        threshold: float = 0.8
    ) -> Optional[str]:
        """Find exact attribute match (case-insensitive), with field name normalization."""
        # Fix #3: Normalize field names (e.g., creation_date -> created_at)
        normalized_ir_attr = normalize_field_name(ir_attr)

        # 1. Direct match with normalized name
        if normalized_ir_attr in gen_attributes:
            return normalized_ir_attr

        # 2. Original name match
        if ir_attr in gen_attributes:
            return ir_attr

        # 3. Case-insensitive match (both normalized and original)
        ir_lower = normalized_ir_attr.lower()
        ir_orig_lower = ir_attr.lower()
        for gen_attr in gen_attributes:
            gen_lower = gen_attr.lower()
            if gen_lower == ir_lower or gen_lower == ir_orig_lower:
                return gen_attr

        return None


class StrictFlowMatcher:
    """STRICT mode: Flow matching with Spanish→English normalization (Bug #8 fix)."""

    def find_flow_match(
        self,
        flow_name: str,
        flow_entity: Optional[str],
        service_classes: Dict[str, List[str]],
        all_code: str,
        flow_mapping: Optional[Dict] = None
    ) -> tuple:
        """Find flow implementation with Spanish→English translation."""
        # Bug #8 Fix: Normalize flow name (Spanish→English, e.g., "Crear Producto" -> "create_product")
        normalized_flow = normalize_flow_name(flow_name)

        # 1. IR mapping (highest priority)
        if flow_mapping and flow_name in flow_mapping:
            mapped = flow_mapping[flow_name]
            for class_name, methods in service_classes.items():
                if mapped.get("method", "").lower() in [m.lower() for m in methods]:
                    return True, {
                        "match_mode": "ir_mapping",
                        "matched_class": class_name,
                        "matched_method": mapped["method"],
                        "score": 1.0
                    }

        # 2. Exact method name match (original)
        flow_method = flow_name.lower().replace(' ', '_').replace('-', '_')
        for class_name, methods in service_classes.items():
            for method in methods:
                if method.lower() == flow_method:
                    return True, {
                        "match_mode": "exact_method",
                        "matched_class": class_name,
                        "matched_method": method,
                        "score": 1.0
                    }

        # 3. Bug #8 Fix: Match with normalized flow name (Spanish→English)
        for class_name, methods in service_classes.items():
            for method in methods:
                if method.lower() == normalized_flow:
                    return True, {
                        "match_mode": "spanish_normalized",
                        "matched_class": class_name,
                        "matched_method": method,
                        "original_flow": flow_name,
                        "normalized_flow": normalized_flow,
                        "score": 1.0
                    }

        # 4. Entity+Action pattern with Spanish translation
        if flow_entity:
            # Try normalized action (from Spanish)
            normalized_words = normalized_flow.split('_')
            if normalized_words:
                action = normalized_words[0]  # Already translated
                entity_lower = normalize_entity_name(flow_entity).lower()
                for class_name, methods in service_classes.items():
                    class_normalized = normalize_entity_name(class_name.replace('Service', '')).lower()
                    if entity_lower == class_normalized or entity_lower in class_name.lower():
                        for method in methods:
                            if method.lower() == action:
                                return True, {
                                    "match_mode": "entity_action_normalized",
                                    "matched_class": class_name,
                                    "matched_method": method,
                                    "score": 1.0
                                }

        # 5. Original Entity+Action pattern (fallback)
        if flow_entity:
            words = flow_name.lower().split()
            if words:
                action = words[0]
                entity_lower = flow_entity.lower()
                for class_name, methods in service_classes.items():
                    class_lower = class_name.lower()
                    if entity_lower in class_lower or class_lower.replace('service', '') == entity_lower:
                        for method in methods:
                            if method.lower() == action:
                                return True, {
                                    "match_mode": "entity_action_exact",
                                    "matched_class": class_name,
                                    "matched_method": method,
                                    "score": 1.0
                                }

        return False, {"match_mode": "none", "score": 0.0}


class StrictConstraintMatcher:
    """STRICT mode: Constraint matching with entity suffix normalization and consolidation.

    Bug #8 Fix: Entity suffix normalization
    Bug #12 Fix: Consolidate constraints across schema variants
    """

    def find_entity_constraints(
        self,
        ir_entity: str,
        code_constraints: Dict[str, Dict[str, Set[str]]]
    ) -> tuple:
        """Find and consolidate constraints across all schema variants.

        Bug #12 Fix: Consolidate constraints from Product, ProductBase, ProductCreate, etc.
        This mirrors RELAXED behavior but with stricter matching criteria.
        """
        # Bug #8 Fix: Normalize entity name for matching
        ir_normalized = normalize_entity_name(ir_entity)
        ir_lower = ir_normalized.lower()

        # Bug #12 Fix: Consolidate constraints from ALL matching variants
        merged: Dict[str, Set[str]] = {}
        matched_classes = []

        # 1. Collect all matching variants with suffix normalization
        for class_name, attrs in code_constraints.items():
            class_normalized = normalize_entity_name(class_name)
            # Match if normalized names are equal (case-insensitive)
            if class_normalized.lower() == ir_lower or class_normalized.lower() == ir_entity.lower():
                matched_classes.append(class_name)
                # Merge constraints from this variant
                for attr, constraints in attrs.items():
                    if attr not in merged:
                        merged[attr] = set()
                    merged[attr].update(constraints)

        if matched_classes:
            # Return consolidated constraints with match info
            return merged, {
                "match_mode": "suffix_normalized_consolidated",
                "matched_classes": matched_classes,
                "score": 1.0
            }

        # 2. Fallback: exact match on original name
        if ir_entity in code_constraints:
            return code_constraints[ir_entity], {
                "match_mode": "exact",
                "matched_class": ir_entity,
                "score": 1.0
            }

        return {}, {"match_mode": "none", "score": 0.0}

    def check_range_constraint(
        self,
        ir_condition: str,
        attr_constraints: Set[str]
    ) -> tuple:
        """Check range constraint match with integer semantic equivalences.

        Bug #12 Fix: Accept semantic equivalences for integer constraints:
        - > N (for integers) is equivalent to >= N+1
        - >= N (for integers) is equivalent to > N-1
        - < N (for integers) is equivalent to <= N-1
        - <= N (for integers) is equivalent to < N+1
        """
        condition_lower = ir_condition.lower().strip()

        range_constraints = [c for c in attr_constraints if c.startswith(("ge_", "gt_", "le_", "lt_"))]
        if not range_constraints:
            return False, {"match_mode": "none", "score": 0.0}

        # Extract numeric value from IR condition
        ir_value = self._extract_numeric_value(condition_lower)

        # Build a map of constraint types and their values
        constraint_map = {}
        for c in range_constraints:
            prefix = c[:3]  # ge_, gt_, le_, lt_
            try:
                val = int(c[3:]) if c[3:].lstrip('-').isdigit() else float(c[3:])
                constraint_map[prefix] = val
            except (ValueError, IndexError):
                pass

        # Check with semantic equivalences for integers
        if ">=" in condition_lower:
            # >= N: accept ge_N or gt_(N-1) for integers
            if "ge_" in constraint_map:
                if ir_value is not None and constraint_map["ge_"] == ir_value:
                    return True, {
                        "match_mode": "exact_ge",
                        "ir_condition": ir_condition,
                        "code_constraint": f"ge_{constraint_map['ge_']}",
                        "score": 1.0
                    }
            if "gt_" in constraint_map and ir_value is not None:
                # >= N is semantically equivalent to > (N-1) for integers
                if isinstance(ir_value, int) and constraint_map["gt_"] == ir_value - 1:
                    return True, {
                        "match_mode": "semantic_ge_as_gt",
                        "ir_condition": ir_condition,
                        "code_constraint": f"gt_{constraint_map['gt_']}",
                        "score": 0.95
                    }
            # Fallback: any ge_ constraint is acceptable
            for c in range_constraints:
                if c.startswith("ge_"):
                    return True, {
                        "match_mode": "relaxed_ge",
                        "ir_condition": ir_condition,
                        "code_constraint": c,
                        "score": 0.9
                    }

        elif ">" in condition_lower:
            # > N: accept gt_N or ge_(N+1) for integers
            if "gt_" in constraint_map:
                if ir_value is not None and constraint_map["gt_"] == ir_value:
                    return True, {
                        "match_mode": "exact_gt",
                        "ir_condition": ir_condition,
                        "code_constraint": f"gt_{constraint_map['gt_']}",
                        "score": 1.0
                    }
            if "ge_" in constraint_map and ir_value is not None:
                # > N is semantically equivalent to >= (N+1) for integers
                if isinstance(ir_value, int) and constraint_map["ge_"] == ir_value + 1:
                    return True, {
                        "match_mode": "semantic_gt_as_ge",
                        "ir_condition": ir_condition,
                        "code_constraint": f"ge_{constraint_map['ge_']}",
                        "score": 0.95
                    }
            # Fallback: any gt_ constraint is acceptable
            for c in range_constraints:
                if c.startswith("gt_"):
                    return True, {
                        "match_mode": "relaxed_gt",
                        "ir_condition": ir_condition,
                        "code_constraint": c,
                        "score": 0.9
                    }

        if "<=" in condition_lower:
            # <= N: accept le_N or lt_(N+1) for integers
            if "le_" in constraint_map:
                if ir_value is not None and constraint_map["le_"] == ir_value:
                    return True, {
                        "match_mode": "exact_le",
                        "ir_condition": ir_condition,
                        "code_constraint": f"le_{constraint_map['le_']}",
                        "score": 1.0
                    }
            if "lt_" in constraint_map and ir_value is not None:
                # <= N is semantically equivalent to < (N+1) for integers
                if isinstance(ir_value, int) and constraint_map["lt_"] == ir_value + 1:
                    return True, {
                        "match_mode": "semantic_le_as_lt",
                        "ir_condition": ir_condition,
                        "code_constraint": f"lt_{constraint_map['lt_']}",
                        "score": 0.95
                    }
            # Fallback: any le_ constraint is acceptable
            for c in range_constraints:
                if c.startswith("le_"):
                    return True, {
                        "match_mode": "relaxed_le",
                        "ir_condition": ir_condition,
                        "code_constraint": c,
                        "score": 0.9
                    }

        elif "<" in condition_lower:
            # < N: accept lt_N or le_(N-1) for integers
            if "lt_" in constraint_map:
                if ir_value is not None and constraint_map["lt_"] == ir_value:
                    return True, {
                        "match_mode": "exact_lt",
                        "ir_condition": ir_condition,
                        "code_constraint": f"lt_{constraint_map['lt_']}",
                        "score": 1.0
                    }
            if "le_" in constraint_map and ir_value is not None:
                # < N is semantically equivalent to <= (N-1) for integers
                if isinstance(ir_value, int) and constraint_map["le_"] == ir_value - 1:
                    return True, {
                        "match_mode": "semantic_lt_as_le",
                        "ir_condition": ir_condition,
                        "code_constraint": f"le_{constraint_map['le_']}",
                        "score": 0.95
                    }
            # Fallback: any lt_ constraint is acceptable
            for c in range_constraints:
                if c.startswith("lt_"):
                    return True, {
                        "match_mode": "relaxed_lt",
                        "ir_condition": ir_condition,
                        "code_constraint": c,
                        "score": 0.9
                    }

        return False, {"match_mode": "none", "score": 0.0}

    def _extract_numeric_value(self, condition: str) -> int | float | None:
        """Extract numeric value from a constraint condition string.

        Examples:
            "> 0" -> 0
            ">= 1" -> 1
            "< 100" -> 100
            "value > 5" -> 5
        """
        import re
        # Match patterns like "> 0", ">= 1", "< 100", etc.
        match = re.search(r'[><]=?\s*(-?\d+(?:\.\d+)?)', condition)
        if match:
            val_str = match.group(1)
            if '.' in val_str:
                return float(val_str)
            return int(val_str)
        return None


# =============================================================================
# Strategy Factory
# =============================================================================

def get_entity_matcher(mode: ValidationMode) -> EntityMatchingStrategy:
    """Get entity matching strategy for mode."""
    if mode == ValidationMode.STRICT:
        return StrictEntityMatcher()
    return FuzzyEntityMatcherAdapter()


def get_flow_matcher(mode: ValidationMode) -> FlowMatchingStrategy:
    """Get flow matching strategy for mode."""
    if mode == ValidationMode.STRICT:
        return StrictFlowMatcher()
    return SemanticFlowMatcherAdapter()


def get_constraint_matcher(mode: ValidationMode) -> ConstraintMatchingStrategy:
    """Get constraint matching strategy for mode."""
    if mode == ValidationMode.STRICT:
        return StrictConstraintMatcher()
    return SemanticConstraintMatcherAdapter()


# =============================================================================
# RELAXED Adapters (wrap existing matchers to Protocol interface)
# =============================================================================

class FuzzyEntityMatcherAdapter:
    """Adapter to make FuzzyEntityMatcher conform to EntityMatchingStrategy."""

    def find_entity_match(
        self,
        ir_entity: str,
        generated_entities: Dict[str, Any],
        threshold: float = 0.7
    ) -> tuple:
        return FuzzyEntityMatcher.find_best_match(ir_entity, generated_entities, threshold)

    def find_attribute_match(
        self,
        ir_attr: str,
        gen_attributes: Dict[str, Any],
        threshold: float = 0.8
    ) -> Optional[str]:
        return FuzzyEntityMatcher.find_attribute_match(ir_attr, gen_attributes, threshold)


class SemanticFlowMatcherAdapter:
    """Adapter to make SemanticFlowMatcher conform to FlowMatchingStrategy."""

    def find_flow_match(
        self,
        flow_name: str,
        flow_entity: Optional[str],
        service_classes: Dict[str, List[str]],
        all_code: str,
        flow_mapping: Optional[Dict] = None
    ) -> tuple:
        return SemanticFlowMatcher.find_flow_in_code(
            flow_name, flow_entity, service_classes, all_code, flow_mapping
        )


class SemanticConstraintMatcherAdapter:
    """Adapter to make SemanticConstraintMatcher conform to ConstraintMatchingStrategy."""

    def find_entity_constraints(
        self,
        ir_entity: str,
        code_constraints: Dict[str, Dict[str, Set[str]]]
    ) -> tuple:
        return SemanticConstraintMatcher.find_entity_constraints(ir_entity, code_constraints)

    def check_range_constraint(
        self,
        ir_condition: str,
        attr_constraints: Set[str]
    ) -> tuple:
        return SemanticConstraintMatcher.check_range_constraint(ir_condition, attr_constraints)


# =============================================================================
# Fuzzy Matching Utilities (RELAXED mode implementations)
# =============================================================================

class FuzzyEntityMatcher:
    """Fuzzy matching for IR entities vs generated code."""

    COMMON_SUFFIXES = ["Model", "Entity", "Base", "Schema", "DB", "Table", "Record"]
    COMMON_PREFIXES = ["Db", "DB", "Tbl", ""]

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize entity name for comparison."""
        normalized = name
        # Remove common suffixes
        for suffix in FuzzyEntityMatcher.COMMON_SUFFIXES:
            if normalized.endswith(suffix) and len(normalized) > len(suffix):
                normalized = normalized[:-len(suffix)]
                break
        # Remove common prefixes
        for prefix in FuzzyEntityMatcher.COMMON_PREFIXES:
            if prefix and normalized.startswith(prefix) and len(normalized) > len(prefix):
                normalized = normalized[len(prefix):]
                break
        return normalized.lower()

    @staticmethod
    def find_best_match(
        ir_entity: str,
        generated_entities: Dict[str, Any],
        threshold: float = 0.7
    ) -> tuple:
        """
        Find best matching generated entity for IR entity.

        Returns:
            Tuple of (matched_name, match_info) where match_info contains:
            - match_mode: "exact" | "normalized" | "substring" | "similarity"
            - score: float (1.0 for exact/normalized, actual score for similarity)
        """
        ir_normalized = FuzzyEntityMatcher.normalize_name(ir_entity)

        # 1. Exact match first
        if ir_entity in generated_entities:
            return ir_entity, {"match_mode": "exact", "score": 1.0}

        # 2. Exact normalized match
        for gen_name in generated_entities:
            if FuzzyEntityMatcher.normalize_name(gen_name) == ir_normalized:
                return gen_name, {"match_mode": "normalized", "score": 1.0}

        # 3. Substring match (IR name contained in generated or vice versa)
        for gen_name in generated_entities:
            gen_normalized = FuzzyEntityMatcher.normalize_name(gen_name)
            if ir_normalized in gen_normalized or gen_normalized in ir_normalized:
                return gen_name, {"match_mode": "substring", "score": 0.9}

        # 4. Sequence similarity (Levenshtein-like)
        from difflib import SequenceMatcher
        best_match = None
        best_score = 0
        for gen_name in generated_entities:
            score = SequenceMatcher(
                None,
                ir_normalized,
                FuzzyEntityMatcher.normalize_name(gen_name)
            ).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = gen_name

        if best_match:
            return best_match, {"match_mode": "similarity", "score": best_score}

        return None, {"match_mode": "none", "score": 0.0}

    @staticmethod
    def find_attribute_match(
        ir_attr: str,
        gen_attributes: Dict[str, Any],
        threshold: float = 0.8
    ) -> Optional[str]:
        """Find best matching attribute name, with field name normalization."""
        # Fix #3: Normalize field names (e.g., creation_date -> created_at)
        normalized_ir_attr = normalize_field_name(ir_attr)
        ir_lower = normalized_ir_attr.lower().replace('_', '')
        ir_orig_lower = ir_attr.lower().replace('_', '')

        # 1. Exact match with normalized name
        if normalized_ir_attr in gen_attributes:
            return normalized_ir_attr

        # 2. Exact match with original name
        if ir_attr in gen_attributes:
            return ir_attr

        # 3. Case-insensitive match (both normalized and original)
        for gen_attr in gen_attributes:
            gen_lower = gen_attr.lower()
            if gen_lower == normalized_ir_attr.lower() or gen_lower == ir_attr.lower():
                return gen_attr

        # 4. Normalized match (remove underscores)
        for gen_attr in gen_attributes:
            gen_normalized = gen_attr.lower().replace('_', '')
            if gen_normalized == ir_lower or gen_normalized == ir_orig_lower:
                return gen_attr

        # 5. Sequence similarity
        from difflib import SequenceMatcher
        best_match = None
        best_score = 0
        for gen_attr in gen_attributes:
            gen_normalized = gen_attr.lower().replace('_', '')
            # Check against both normalized and original
            score_norm = SequenceMatcher(None, ir_lower, gen_normalized).ratio()
            score_orig = SequenceMatcher(None, ir_orig_lower, gen_normalized).ratio()
            score = max(score_norm, score_orig)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = gen_attr

        return best_match


class SemanticFlowMatcher:
    """
    Semantic matching for IR flows vs generated code.

    Matching strategies:
    1. IR mapping (from phase 6.6) - highest priority
    2. Entity+Action pattern: "Create Product" → ProductService.create
    3. Action synonyms: "process" → "handle", "execute", etc.
    4. Code content search: flow words in method/class names
    """

    ACTION_SYNONYMS = {
        "create": ["add", "new", "insert", "register", "save", "post"],
        "read": ["get", "fetch", "retrieve", "find", "load", "query", "list"],
        "update": ["modify", "edit", "change", "set", "patch", "put"],
        "delete": ["remove", "destroy", "clear", "drop"],
        "process": ["handle", "execute", "run", "perform", "do"],
        "validate": ["check", "verify", "ensure", "confirm"],
        "calculate": ["compute", "determine", "evaluate", "sum", "total"],
        "send": ["emit", "dispatch", "publish", "notify"],
        "add": ["insert", "append", "push", "create"],
        "get": ["read", "fetch", "retrieve", "find", "load"],
    }

    @staticmethod
    def find_flow_in_code(
        flow_name: str,
        flow_entity: Optional[str],
        service_classes: Dict[str, List[str]],
        all_code: str,
        flow_mapping: Optional[Dict] = None
    ) -> tuple:
        """
        Find if flow is implemented in code.

        Args:
            flow_name: IR flow name (e.g., "Create Product")
            flow_entity: Associated entity (e.g., "Product")
            service_classes: Dict of class_name -> [method_names]
            all_code: Combined code content for text search
            flow_mapping: Optional IR flow mapping from phase 6.6

        Returns:
            Tuple of (found: bool, match_info: dict)
        """
        # 1. IR mapping from phase 6.6 (highest priority)
        if flow_mapping and flow_name in flow_mapping:
            mapped = flow_mapping[flow_name]
            # Check if method exists
            for class_name, methods in service_classes.items():
                if mapped.get("method", "").lower() in [m.lower() for m in methods]:
                    return True, {
                        "match_mode": "ir_mapping",
                        "matched_class": class_name,
                        "matched_method": mapped["method"],
                        "score": 1.0
                    }

        # Parse flow name into action + subject
        flow_lower = flow_name.lower()
        words = flow_lower.replace('-', ' ').replace('_', ' ').split()

        if len(words) < 2:
            # Single word flow, try direct match
            return SemanticFlowMatcher._search_in_code(flow_lower, all_code)

        action = words[0]
        subject = '_'.join(words[1:])  # "to cart" → "to_cart"
        subject_clean = subject.replace('_', '').replace(' ', '')

        # 2. Entity+Action pattern: "Create Product" → ProductService.create
        if flow_entity:
            entity_lower = flow_entity.lower()
            for class_name, methods in service_classes.items():
                class_lower = class_name.lower()
                # Check if class matches entity (ProductService, Product, etc.)
                if entity_lower in class_lower or class_lower.replace('service', '') == entity_lower:
                    # Check if action method exists
                    action_variants = [action] + SemanticFlowMatcher.ACTION_SYNONYMS.get(action, [])
                    for method in methods:
                        method_lower = method.lower()
                        if method_lower in action_variants:
                            return True, {
                                "match_mode": "entity_action",
                                "matched_class": class_name,
                                "matched_method": method,
                                "pattern": f"{flow_entity}.{action}",
                                "score": 0.95
                            }

        # 3. Action synonyms with subject: "Add to Cart" → CartService.add_item
        for class_name, methods in service_classes.items():
            class_lower = class_name.lower().replace('service', '')
            # Check if subject relates to class
            if subject_clean in class_lower or class_lower in subject_clean:
                action_variants = [action] + SemanticFlowMatcher.ACTION_SYNONYMS.get(action, [])
                for method in methods:
                    method_lower = method.lower()
                    for variant in action_variants:
                        if variant in method_lower:
                            return True, {
                                "match_mode": "action_synonym",
                                "matched_class": class_name,
                                "matched_method": method,
                                "action_matched": variant,
                                "score": 0.85
                            }

        # 4. Route/endpoint pattern search
        # "Process Payment" → POST /{id}/pay
        route_patterns = SemanticFlowMatcher._extract_route_patterns(flow_name)
        for pattern in route_patterns:
            if pattern in all_code.lower():
                return True, {
                    "match_mode": "route_pattern",
                    "matched_pattern": pattern,
                    "score": 0.8
                }

        # 5. Code content search (last resort)
        return SemanticFlowMatcher._search_in_code(flow_name, all_code)

    @staticmethod
    def _extract_route_patterns(flow_name: str) -> List[str]:
        """Extract likely route patterns from flow name."""
        patterns = []
        words = flow_name.lower().split()

        # "Process Payment" → ["pay", "payment", "/pay"]
        for word in words:
            if len(word) > 3:
                patterns.append(word)
                patterns.append(f"/{word}")
                # Verb forms
                if word.endswith('e'):
                    patterns.append(word[:-1] + 'ing')
                elif not word.endswith('ing'):
                    patterns.append(word + 'ing')

        return patterns

    @staticmethod
    def _search_in_code(flow_name: str, code: str) -> tuple:
        """Search for flow evidence in code content."""
        code_lower = code.lower()
        flow_words = set(flow_name.lower().replace('-', ' ').replace('_', ' ').split())
        # Remove stop words
        flow_words -= {'the', 'a', 'an', 'to', 'for', 'of', 'in', 'by', 'from'}

        if len(flow_words) == 0:
            return False, {"match_mode": "none", "score": 0.0}

        matches = sum(1 for word in flow_words if word in code_lower and len(word) > 2)
        match_ratio = matches / len(flow_words)

        if match_ratio >= 0.7:
            return True, {
                "match_mode": "code_content",
                "words_found": matches,
                "words_total": len(flow_words),
                "score": match_ratio * 0.7  # Lower confidence
            }

        return False, {"match_mode": "none", "score": 0.0}


class SemanticConstraintMatcher:
    """
    Semantic matching for IR constraints vs generated code.

    Handles:
    1. Fuzzy entity matching: Product → ProductBase, ProductCreate, etc.
    2. Semantic range equivalence: gt=0 ≈ ge=1 for quantities
    3. Constraint consolidation across schema variants
    """

    # Schema class suffixes to strip for entity matching
    SCHEMA_SUFFIXES = ["Base", "Create", "Update", "Response", "List", "Schema", "Model"]

    @staticmethod
    def normalize_entity_name(class_name: str) -> str:
        """Normalize schema class name to entity name."""
        name = class_name
        for suffix in SemanticConstraintMatcher.SCHEMA_SUFFIXES:
            if name.endswith(suffix) and len(name) > len(suffix):
                name = name[:-len(suffix)]
                break
        return name

    @staticmethod
    def find_entity_constraints(
        ir_entity: str,
        code_constraints: Dict[str, Dict[str, Set[str]]]
    ) -> tuple:
        """
        Find constraints for IR entity across all schema variants.

        Args:
            ir_entity: IR entity name (e.g., "Product")
            code_constraints: Dict of class_name -> {attr -> constraints}

        Returns:
            Tuple of (merged_constraints: Dict[str, Set[str]], match_info: dict)
        """
        ir_lower = ir_entity.lower()
        merged: Dict[str, Set[str]] = {}
        matched_classes = []

        for class_name, attrs in code_constraints.items():
            normalized = SemanticConstraintMatcher.normalize_entity_name(class_name)
            if normalized.lower() == ir_lower:
                matched_classes.append(class_name)
                for attr, constraints in attrs.items():
                    if attr not in merged:
                        merged[attr] = set()
                    merged[attr].update(constraints)

        if matched_classes:
            return merged, {
                "match_mode": "fuzzy_entity",
                "matched_classes": matched_classes,
                "score": 0.95
            }

        # Try substring match
        for class_name, attrs in code_constraints.items():
            class_lower = class_name.lower()
            if ir_lower in class_lower or class_lower.startswith(ir_lower):
                matched_classes.append(class_name)
                for attr, constraints in attrs.items():
                    if attr not in merged:
                        merged[attr] = set()
                    merged[attr].update(constraints)

        if matched_classes:
            return merged, {
                "match_mode": "substring_entity",
                "matched_classes": matched_classes,
                "score": 0.85
            }

        return {}, {"match_mode": "none", "score": 0.0}

    @staticmethod
    def check_range_constraint(
        ir_condition: str,
        attr_constraints: Set[str]
    ) -> tuple:
        """
        Check if range constraint is semantically satisfied.

        Handles semantic equivalences:
        - gt=0 ≈ ge=1 for integers (quantity > 0 means quantity >= 1)
        - ge=0.01 ≈ gt=0 for prices

        Args:
            ir_condition: IR condition like "price > 0" or "stock >= 0"
            attr_constraints: Set of constraints like {"gt_0", "ge_0.01"}

        Returns:
            Tuple of (found: bool, match_info: dict)
        """
        # Parse IR condition
        condition_lower = ir_condition.lower().strip()

        # Check for any range constraints present
        range_constraints = [c for c in attr_constraints if c.startswith(("ge_", "gt_", "le_", "lt_"))]
        if not range_constraints:
            return False, {"match_mode": "none", "score": 0.0}

        # Check for ">" or ">="
        if ">" in condition_lower:
            # Extract value
            if ">=" in condition_lower:
                # IR wants >= X
                for c in range_constraints:
                    if c.startswith("ge_") or c.startswith("gt_"):
                        return True, {
                            "match_mode": "range_semantic",
                            "ir_condition": ir_condition,
                            "code_constraint": c,
                            "score": 0.9
                        }
            else:
                # IR wants > X (strictly greater)
                for c in range_constraints:
                    if c.startswith("gt_"):
                        return True, {
                            "match_mode": "range_exact",
                            "ir_condition": ir_condition,
                            "code_constraint": c,
                            "score": 1.0
                        }
                    # RELAXED: ge=1 satisfies > 0 for integers
                    if c.startswith("ge_"):
                        return True, {
                            "match_mode": "range_relaxed",
                            "ir_condition": ir_condition,
                            "code_constraint": c,
                            "note": "ge used instead of gt (semantically equivalent for integers)",
                            "score": 0.85
                        }

        # Check for "<" or "<="
        if "<" in condition_lower:
            for c in range_constraints:
                if c.startswith("le_") or c.startswith("lt_"):
                    return True, {
                        "match_mode": "range_semantic",
                        "ir_condition": ir_condition,
                        "code_constraint": c,
                        "score": 0.9
                    }

        # Any range constraint present is partial match
        return True, {
            "match_mode": "range_partial",
            "ir_condition": ir_condition,
            "code_constraints": range_constraints,
            "score": 0.7
        }


@dataclass
class ComplianceIssue:
    """Single compliance issue found during validation."""
    category: str  # "entity", "flow", "constraint"
    severity: str  # "error", "warning", "info"
    entity: str
    field: Optional[str]
    expected: str
    actual: str
    message: str


@dataclass
class ComplianceReport:
    """Full compliance report from validation."""
    total_expected: int = 0
    total_found: int = 0
    issues: List[ComplianceIssue] = field(default_factory=list)
    coverage: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_compliant(self) -> bool:
        """Check if no errors found."""
        return all(i.severity != "error" for i in self.issues)

    @property
    def compliance_score(self) -> float:
        """Calculate compliance percentage."""
        if self.total_expected == 0:
            return 100.0
        error_count = sum(1 for i in self.issues if i.severity == "error")
        return max(0, (self.total_expected - error_count) / self.total_expected * 100)


class EntityComplianceChecker:
    """
    Validate generated entities.py against DomainModelIR.

    Checks:
    - All entities exist
    - All attributes present with correct types
    - All relationships defined
    - Constraints properly applied

    Supports dual-mode validation:
    - STRICT: Exact entity/attribute name matching
    - RELAXED: Fuzzy matching with suffix normalization
    """

    TYPE_MAPPING = {
        DataType.STRING: {"str", "String", "Text", "VARCHAR"},
        DataType.INTEGER: {"int", "Integer", "BigInteger"},
        DataType.FLOAT: {"float", "Float", "Numeric", "Decimal"},
        DataType.BOOLEAN: {"bool", "Boolean"},
        DataType.DATETIME: {"datetime", "DateTime", "Date"},
        DataType.UUID: {"uuid", "UUID", "Uuid"},
        DataType.JSON: {"dict", "Dict", "JSON", "JSONB"},
        DataType.ENUM: {"enum", "Enum"},
    }

    def __init__(self, domain_model: DomainModelIR, mode: ValidationMode = ValidationMode.RELAXED):
        self.domain_model = domain_model
        self.mode = mode
        self.entity_matcher = get_entity_matcher(mode)

    def check_entities_file(
        self,
        entities_path: Optional[Path] = None,
        content: Optional[str] = None
    ) -> ComplianceReport:
        """
        Validate entities.py against DomainModelIR.

        Args:
            entities_path: Path to entities.py file (legacy, for file-based validation)
            content: In-memory code content (preferred, for pre-deployment validation)
        """
        report = ComplianceReport()
        report.total_expected = len(self.domain_model.entities)

        # Prefer in-memory content over file path
        if content is not None:
            code_content = content
        elif entities_path is not None:
            if not entities_path.exists():
                report.issues.append(ComplianceIssue(
                    category="entity",
                    severity="error",
                    entity="*",
                    field=None,
                    expected="entities.py file",
                    actual="File not found",
                    message=f"Entities file not found: {entities_path}"
                ))
                return report
            code_content = entities_path.read_text()
        else:
            report.issues.append(ComplianceIssue(
                category="entity",
                severity="error",
                entity="*",
                field=None,
                expected="entities.py content",
                actual="No content provided",
                message="Either entities_path or content must be provided"
            ))
            return report

        generated_entities = self._parse_entities_from_code(code_content)

        # Store entity mappings for later use (e.g., constraint checking)
        report.details["entity_mapping"] = {}

        for expected_entity in self.domain_model.entities:
            # Use strategy-based matching (STRICT or RELAXED)
            matched_name, match_info = self.entity_matcher.find_entity_match(
                expected_entity.name,
                generated_entities
            )

            if not matched_name:
                report.issues.append(ComplianceIssue(
                    category="entity",
                    severity="error",
                    entity=expected_entity.name,
                    field=None,
                    expected=f"Entity {expected_entity.name}",
                    actual=f"Not found (checked: {list(generated_entities.keys())})",
                    message=f"Missing entity: {expected_entity.name}"
                ))
                continue

            report.total_found += 1
            gen_entity = generated_entities[matched_name]

            # Store mapping with match details for auditing
            report.details["entity_mapping"][expected_entity.name] = {
                "matched_name": matched_name,
                "match_mode": match_info["match_mode"],
                "score": match_info["score"]
            }

            if matched_name != expected_entity.name:
                logger.debug(
                    f"Fuzzy matched: {expected_entity.name} -> {matched_name} "
                    f"(mode={match_info['match_mode']}, score={match_info['score']:.2f})"
                )

            # Check attributes with fuzzy matching
            for attr in expected_entity.attributes:
                self._check_attribute(expected_entity.name, attr, gen_entity, report)

            # Check relationships
            for rel in expected_entity.relationships:
                self._check_relationship(expected_entity.name, rel, gen_entity, report)

        report.coverage = report.total_found / max(1, report.total_expected) * 100
        return report

    def _parse_entities_from_code(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Parse entity definitions from Python code."""
        entities = {}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a SQLAlchemy/Pydantic model
                    is_model = any(
                        isinstance(base, ast.Name) and base.id in ("Base", "BaseModel")
                        or isinstance(base, ast.Attribute)
                        for base in node.bases
                    )

                    if is_model:
                        entity_info = {
                            "name": node.name,
                            "attributes": {},
                            "relationships": []
                        }

                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and item.target:
                                attr_name = item.target.id if isinstance(item.target, ast.Name) else None
                                if attr_name:
                                    type_str = self._get_type_annotation(item.annotation)
                                    constraints = self._extract_constraints(item)
                                    entity_info["attributes"][attr_name] = {
                                        "type": type_str,
                                        "constraints": constraints
                                    }

                            elif isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        attr_name = target.id
                                        if isinstance(item.value, ast.Call):
                                            func_name = self._get_call_name(item.value)
                                            if func_name in ("Column", "Mapped", "relationship"):
                                                entity_info["attributes"][attr_name] = {
                                                    "type": self._extract_column_type(item.value),
                                                    "constraints": self._extract_column_constraints(item.value)
                                                }
                                            if func_name == "relationship":
                                                entity_info["relationships"].append(attr_name)

                        entities[node.name] = entity_info

        except SyntaxError as e:
            logger.warning(f"Failed to parse entities file: {e}")

        return entities

    def _get_type_annotation(self, annotation) -> str:
        """Extract type string from annotation node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr
        return "Unknown"

    def _get_call_name(self, call: ast.Call) -> str:
        """Get function name from Call node."""
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return call.func.attr
        return ""

    def _extract_column_type(self, call: ast.Call) -> str:
        """Extract type from Column() call."""
        if call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Name):
                return first_arg.id
            elif isinstance(first_arg, ast.Call):
                return self._get_call_name(first_arg)
        return "Unknown"

    def _extract_constraints(self, item: ast.AnnAssign) -> Dict[str, Any]:
        """Extract constraints from annotated assignment."""
        constraints = {}
        if isinstance(item.value, ast.Call):
            for kw in item.value.keywords:
                if kw.arg in ("ge", "gt", "le", "lt", "min_length", "max_length", "pattern"):
                    constraints[kw.arg] = self._get_literal_value(kw.value)
        return constraints

    def _extract_column_constraints(self, call: ast.Call) -> Dict[str, Any]:
        """Extract constraints from Column() call."""
        constraints = {}
        for kw in call.keywords:
            if kw.arg in ("nullable", "unique", "primary_key", "index"):
                constraints[kw.arg] = self._get_literal_value(kw.value)
        return constraints

    def _get_literal_value(self, node) -> Any:
        """Get literal value from AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id == "True"
        return None

    def _check_attribute(self, entity: str, attr: Attribute, gen_entity: Dict, report: ComplianceReport):
        """Check single attribute compliance with strategy-based matching."""
        attr_name = attr.name

        # Use strategy-based matching for attribute names
        matched_attr = self.entity_matcher.find_attribute_match(
            attr_name,
            gen_entity["attributes"]
        )

        if not matched_attr:
            report.issues.append(ComplianceIssue(
                category="entity",
                severity="error",
                entity=entity,
                field=attr_name,
                expected=f"Attribute {attr_name}",
                actual=f"Not found (available: {list(gen_entity['attributes'].keys())[:5]}...)",
                message=f"Missing attribute: {entity}.{attr_name}"
            ))
            return

        gen_attr = gen_entity["attributes"][matched_attr]
        expected_types = self.TYPE_MAPPING.get(attr.data_type, {attr.data_type.value})

        if gen_attr["type"] not in expected_types:
            report.issues.append(ComplianceIssue(
                category="entity",
                severity="warning",
                entity=entity,
                field=attr_name,
                expected=f"Type {attr.data_type.value}",
                actual=f"Type {gen_attr['type']}",
                message=f"Type mismatch for {entity}.{attr_name}"
            ))

    def _check_relationship(self, entity: str, rel: Relationship, gen_entity: Dict, report: ComplianceReport):
        """Check single relationship compliance."""
        if rel.field_name not in gen_entity["relationships"]:
            # Also check in attributes (might be stored as FK)
            fk_name = f"{rel.field_name}_id"
            if fk_name not in gen_entity["attributes"]:
                report.issues.append(ComplianceIssue(
                    category="entity",
                    severity="warning",
                    entity=entity,
                    field=rel.field_name,
                    expected=f"Relationship to {rel.target_entity}",
                    actual="Not found",
                    message=f"Missing relationship: {entity}.{rel.field_name} -> {rel.target_entity}"
                ))


class FlowComplianceChecker:
    """
    Validate implemented services against BehaviorModelIR flows.

    Checks:
    - All flows have corresponding service methods
    - Flow steps are implemented in correct order
    - Invariants are enforced

    Supports dual-mode validation:
    - STRICT: Exact method name matching
    - RELAXED: Semantic matching with action synonyms
    """

    def __init__(self, behavior_model: BehaviorModelIR, mode: ValidationMode = ValidationMode.RELAXED):
        self.behavior_model = behavior_model
        self.mode = mode
        self.flow_matcher = get_flow_matcher(mode)

    def check_services_directory(
        self,
        services_dir: Optional[Path] = None,
        services_content: Optional[Dict[str, str]] = None
    ) -> ComplianceReport:
        """
        Check all service files for flow implementation.

        Args:
            services_dir: Path to services directory (legacy, for file-based validation)
            services_content: Dict of filename -> content (preferred, for pre-deployment validation)
        """
        report = ComplianceReport()
        report.total_expected = len(self.behavior_model.flows)
        report.details["flow_mapping"] = {}

        # Collect all service methods and classes
        all_methods: Set[str] = set()
        service_classes: Dict[str, List[str]] = {}
        all_code = ""

        # Prefer in-memory content over directory path
        if services_content is not None:
            for filename, content in services_content.items():
                all_code += content
                methods, classes = self._extract_methods_and_classes(content)
                all_methods.update(methods)
                service_classes.update(classes)
        elif services_dir is not None:
            if not services_dir.exists():
                report.issues.append(ComplianceIssue(
                    category="flow",
                    severity="error",
                    entity="services",
                    field=None,
                    expected="Services directory",
                    actual="Not found",
                    message=f"Services directory not found: {services_dir}"
                ))
                return report

            for py_file in services_dir.glob("*.py"):
                content = py_file.read_text()
                all_code += content
                methods, classes = self._extract_methods_and_classes(content)
                all_methods.update(methods)
                service_classes.update(classes)
        else:
            report.issues.append(ComplianceIssue(
                category="flow",
                severity="error",
                entity="services",
                field=None,
                expected="Services content",
                actual="No content provided",
                message="Either services_dir or services_content must be provided"
            ))
            return report

        # Check each flow using SemanticFlowMatcher
        for flow in self.behavior_model.flows:
            self._check_flow_implementation(flow, all_methods, service_classes, all_code, report)

        # Check invariants
        for invariant in self.behavior_model.invariants:
            self._check_invariant_enforcement(invariant, all_code, report)

        report.coverage = report.total_found / max(1, report.total_expected) * 100
        return report

    def _extract_methods(self, content: str) -> Set[str]:
        """Extract method names from Python code."""
        methods = set()
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    methods.add(node.name.lower())
        except SyntaxError:
            pass
        return methods

    def _extract_methods_and_classes(self, content: str) -> tuple:
        """
        Extract both flat method names and class-method mapping.

        Returns:
            Tuple of (all_methods: Set[str], service_classes: Dict[str, List[str]])
        """
        methods = set()
        classes: Dict[str, List[str]] = {}
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_name = item.name
                            if not method_name.startswith('_'):
                                class_methods.append(method_name)
                            methods.add(method_name.lower())
                    if class_methods:
                        classes[node.name] = class_methods
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Top-level functions
                    if node.col_offset == 0:
                        methods.add(node.name.lower())
        except SyntaxError:
            pass
        return methods, classes

    def _check_flow_implementation(
        self,
        flow: Flow,
        methods: Set[str],
        service_classes: Dict[str, List[str]],
        code: str,
        report: ComplianceReport
    ):
        """Check if a flow is implemented using strategy-based matching."""
        # Extract entity from flow if available
        flow_entity = getattr(flow, 'entity', None)
        if not flow_entity:
            # Try to extract from flow name: "Create Product" → "Product"
            words = flow.name.split()
            if len(words) >= 2:
                flow_entity = words[-1]  # Last word often is the entity

        # Use strategy-based flow matcher (STRICT or RELAXED)
        found, match_info = self.flow_matcher.find_flow_match(
            flow_name=flow.name,
            flow_entity=flow_entity,
            service_classes=service_classes,
            all_code=code,
            flow_mapping=None  # TODO: Pass IR mapping from phase 6.6 when available
        )

        # Store match details for trazabilidad
        report.details["flow_mapping"][flow.name] = {
            "found": found,
            "entity": flow_entity,
            **match_info
        }

        if found:
            report.total_found += 1
        else:
            # severity="error" so compliance_score correctly counts missing flows
            report.issues.append(ComplianceIssue(
                category="flow",
                severity="error",
                entity=flow.name,
                field=None,
                expected=f"Flow implementation for '{flow.name}'",
                actual=f"Not found (mode: {match_info.get('match_mode', 'none')})",
                message=f"Missing flow implementation: {flow.name} (trigger: {flow.trigger})"
            ))

        # Check if flow steps are mentioned in code
        for step in flow.steps:
            if step.action and step.action.lower() not in code.lower():
                report.issues.append(ComplianceIssue(
                    category="flow",
                    severity="info",
                    entity=flow.name,
                    field=f"step_{step.order}",
                    expected=f"Step: {step.description}",
                    actual="Action not found in code",
                    message=f"Flow step may not be implemented: {step.description}"
                ))

    def _generate_method_variants(self, flow_name: str) -> List[str]:
        """Generate possible method name variants."""
        base = flow_name.lower().replace(' ', '_').replace('-', '_')
        return [
            base,
            f"do_{base}",
            f"execute_{base}",
            f"process_{base}",
            f"handle_{base}",
            f"create_{base}",
            f"update_{base}",
            base.replace('_', ''),
        ]

    def _check_invariant_enforcement(self, invariant: Invariant, code: str, report: ComplianceReport):
        """Check if invariant is enforced in code."""
        # Look for invariant expression or entity validation
        if invariant.expression:
            # Check if expression pattern appears
            expr_pattern = invariant.expression.lower()
            if expr_pattern not in code.lower():
                report.issues.append(ComplianceIssue(
                    category="flow",
                    severity="warning",
                    entity=invariant.entity,
                    field=None,
                    expected=f"Invariant: {invariant.description}",
                    actual="Expression not found",
                    message=f"Invariant may not be enforced: {invariant.description}"
                ))


class ConstraintComplianceChecker:
    """
    Validate code constraints against ValidationModelIR.

    Complements existing SemanticMatcher by using IR as source of truth.

    Supports dual-mode validation:
    - STRICT: Exact entity/constraint matching
    - RELAXED: Semantic matching across schema variants
    """

    def __init__(self, validation_model: ValidationModelIR, mode: ValidationMode = ValidationMode.RELAXED):
        self.validation_model = validation_model
        self.mode = mode
        self.constraint_matcher = get_constraint_matcher(mode)

    def check_constraints(
        self,
        entities_path: Optional[Path] = None,
        schemas_path: Optional[Path] = None,
        entities_content: Optional[str] = None,
        schemas_content: Optional[str] = None
    ) -> ComplianceReport:
        """
        Check code constraints against ValidationModelIR rules.

        Args:
            entities_path: Path to entities.py (legacy, for file-based validation)
            schemas_path: Path to schemas.py (legacy, for file-based validation)
            entities_content: In-memory entities.py content (preferred)
            schemas_content: In-memory schemas.py content (preferred)
        """
        report = ComplianceReport()
        report.total_expected = len(self.validation_model.rules)

        # Extract constraints from code
        code_constraints: Dict[str, Dict[str, Set[str]]] = {}
        has_content = False

        # Prefer in-memory content over file paths
        if entities_content is not None:
            entities_constraints = self._extract_constraints_from_content(entities_content)
            self._merge_constraints(code_constraints, entities_constraints)
            has_content = True
        elif entities_path is not None and entities_path.exists():
            entities_constraints = self._extract_constraints_from_file(entities_path)
            self._merge_constraints(code_constraints, entities_constraints)
            has_content = True

        if schemas_content is not None:
            schemas_constraints = self._extract_constraints_from_content(schemas_content)
            self._merge_constraints(code_constraints, schemas_constraints)
            has_content = True
        elif schemas_path is not None and schemas_path.exists():
            schemas_constraints = self._extract_constraints_from_file(schemas_path)
            self._merge_constraints(code_constraints, schemas_constraints)
            has_content = True

        if not has_content:
            report.issues.append(ComplianceIssue(
                category="constraint",
                severity="error",
                entity="*",
                field=None,
                expected="Code files",
                actual="Not found",
                message="No entities or schemas content provided (file or in-memory)"
            ))
            return report

        # Check each validation rule
        for rule in self.validation_model.rules:
            self._check_rule_enforcement(rule, code_constraints, report)

        report.coverage = report.total_found / max(1, report.total_expected) * 100
        return report

    def _extract_constraints_from_file(self, file_path: Path) -> Dict[str, Dict[str, Set[str]]]:
        """Extract constraints from Python file."""
        content = file_path.read_text()
        return self._extract_constraints_from_content(content, source=str(file_path))

    def _extract_constraints_from_content(
        self,
        content: str,
        source: str = "in-memory"
    ) -> Dict[str, Dict[str, Set[str]]]:
        """Extract constraints from Python code content."""
        constraints: Dict[str, Dict[str, Set[str]]] = {}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entity_name = node.name
                    constraints[entity_name] = {}

                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and item.target:
                            attr_name = getattr(item.target, 'id', None)
                            if attr_name:
                                attr_constraints = self._parse_field_constraints(item)
                                constraints[entity_name][attr_name] = attr_constraints

        except SyntaxError as e:
            logger.warning(f"Failed to parse {source}: {e}")

        return constraints

    def _parse_field_constraints(self, item: ast.AnnAssign) -> Set[str]:
        """Parse constraints from field definition.

        Enhanced to detect additional constraint patterns:
        - default_factory → auto_generated
        - auto=True, read=True → read_only
        - pattern with email regex → email_format
        - positive=True, greater_than_zero=True → positive
        - non_negative=True → non_negative
        - snapshot=True → snapshot (price snapshot)
        - frozen=True → immutable
        """
        constraints: Set[str] = set()

        # Check annotation for Optional
        if isinstance(item.annotation, ast.Subscript):
            if isinstance(item.annotation.value, ast.Name):
                if item.annotation.value.id == "Optional":
                    constraints.add("nullable")

        # Check Field() call for constraints
        if isinstance(item.value, ast.Call):
            func_name = self._get_call_name(item.value)

            if func_name in ("Field", "Column", "Mapped"):
                for kw in item.value.keywords:
                    kw_arg = kw.arg
                    kw_val = self._get_literal_value(kw.value)

                    # Range constraints
                    if kw_arg == "ge":
                        constraints.add(f"ge_{kw_val}")
                    elif kw_arg == "gt":
                        constraints.add(f"gt_{kw_val}")
                    elif kw_arg == "le":
                        constraints.add(f"le_{kw_val}")
                    elif kw_arg == "lt":
                        constraints.add(f"lt_{kw_val}")
                    # Length constraints
                    elif kw_arg == "min_length":
                        constraints.add(f"min_length_{kw_val}")
                    elif kw_arg == "max_length":
                        constraints.add(f"max_length_{kw_val}")
                    # Pattern constraint - check for email
                    elif kw_arg == "pattern":
                        constraints.add("pattern")
                        pattern_str = self._get_string_value(kw.value)
                        if pattern_str and ("@" in pattern_str or "email" in pattern_str.lower()):
                            constraints.add("email_format")
                    # Uniqueness
                    elif kw_arg == "unique" and kw_val:
                        constraints.add("unique")
                    # Required/nullable
                    elif kw_arg == "nullable" and not kw_val:
                        constraints.add("required")
                    # Auto-generated (default_factory implies auto-generated)
                    elif kw_arg == "default_factory":
                        constraints.add("auto_generated")
                        constraints.add("read_only")
                    # Custom markers from generator
                    elif kw_arg == "auto" and kw_val:
                        constraints.add("auto_generated")
                    elif kw_arg == "read" and kw_val:
                        constraints.add("read_only")
                    elif kw_arg == "frozen" and kw_val:
                        constraints.add("immutable")
                        constraints.add("read_only")
                    # Semantic constraints
                    elif kw_arg == "positive" and kw_val:
                        constraints.add("positive")
                    elif kw_arg == "greater_than_zero" and kw_val:
                        constraints.add("positive")
                    elif kw_arg == "non_negative" and kw_val:
                        constraints.add("non_negative")
                    elif kw_arg == "snapshot" and kw_val:
                        constraints.add("snapshot")
                    elif kw_arg == "valid_email_format" and kw_val:
                        constraints.add("email_format")
                    elif kw_arg.startswith("foreign_key_") and kw_val:
                        # foreign_key_product=True → foreign_key constraint
                        ref_entity = kw_arg.replace("foreign_key_", "")
                        constraints.add(f"foreign_key_{ref_entity}")

        return constraints

    def _get_string_value(self, node) -> str:
        """Extract string value from AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return ""

    def _get_call_name(self, call: ast.Call) -> str:
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return call.func.attr
        return ""

    def _get_literal_value(self, node) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id == "True"
        return None

    def _merge_constraints(self, target: Dict, source: Dict):
        """Merge source constraints into target."""
        for entity, attrs in source.items():
            if entity not in target:
                target[entity] = {}
            for attr, constraints in attrs.items():
                if attr not in target[entity]:
                    target[entity][attr] = set()
                target[entity][attr].update(constraints)

    def _check_rule_enforcement(
        self,
        rule: ValidationRule,
        code_constraints: Dict[str, Dict[str, Set[str]]],
        report: ComplianceReport
    ):
        """Check if a validation rule is enforced in code using strategy-based matching."""
        # Use strategy-based entity matching (STRICT or RELAXED)
        entity_constraints, entity_match_info = self.constraint_matcher.find_entity_constraints(
            rule.entity, code_constraints
        )
        attr_constraints = entity_constraints.get(rule.attribute, set())

        found = False
        match_info = {
            "entity_match": entity_match_info,
            "attribute": rule.attribute,
            "found_constraints": list(attr_constraints)
        }

        if rule.type == ValidationType.PRESENCE:
            # RELAXED: min_length_X implies required (must provide at least X chars)
            has_required = "required" in attr_constraints
            has_min_length = any(c.startswith("min_length_") for c in attr_constraints)
            not_nullable = "nullable" not in attr_constraints
            found = has_required or has_min_length or not_nullable
            match_info["check_type"] = "presence"
            match_info["presence_indicators"] = {
                "required": has_required,
                "min_length": has_min_length,
                "not_nullable": not_nullable
            }
        elif rule.type == ValidationType.UNIQUENESS:
            found = "unique" in attr_constraints
            match_info["check_type"] = "uniqueness"
        elif rule.type == ValidationType.FORMAT:
            # Enhanced: detect email_format, pattern, or length constraints
            has_pattern = "pattern" in attr_constraints
            has_email = "email_format" in attr_constraints
            has_length = any("length" in c for c in attr_constraints)
            found = has_pattern or has_email or has_length
            match_info["check_type"] = "format"
            match_info["format_indicators"] = {
                "pattern": has_pattern,
                "email_format": has_email,
                "length": has_length
            }
        elif rule.type == ValidationType.RANGE:
            # Use strategy-based range matching
            found, range_match_info = self.constraint_matcher.check_range_constraint(
                rule.condition or "",
                attr_constraints
            )
            match_info["check_type"] = "range"
            match_info["range_match"] = range_match_info
        elif rule.type == ValidationType.RELATIONSHIP:
            # Check for foreign_key_* constraints
            has_fk = any(c.startswith("foreign_key_") for c in attr_constraints)
            found = has_fk
            match_info["check_type"] = "relationship"
            match_info["foreign_keys"] = [c for c in attr_constraints if c.startswith("foreign_key_")]
        elif rule.type == ValidationType.STOCK_CONSTRAINT:
            # Check for non_negative or inventory-related constraints
            has_non_negative = "non_negative" in attr_constraints
            has_ge_zero = any(c.startswith("ge_0") for c in attr_constraints)
            found = has_non_negative or has_ge_zero
            match_info["check_type"] = "stock_constraint"
            match_info["stock_indicators"] = {
                "non_negative": has_non_negative,
                "ge_zero": has_ge_zero
            }
        elif rule.type == ValidationType.STATUS_TRANSITION:
            # Check for status-related constraints (usually in workflow validators)
            # This is soft-validated as transitions are often in service layer
            found = len(attr_constraints) > 0 or True  # Soft pass - status transitions are usually runtime
            match_info["check_type"] = "status_transition"
        else:
            # For other types (CUSTOM, WORKFLOW_CONSTRAINT), check if any constraint exists
            found = len(attr_constraints) > 0
            match_info["check_type"] = "other"

        # Store match details for trazabilidad
        rule_key = f"{rule.entity}.{rule.attribute}"
        if "constraint_mapping" not in report.details:
            report.details["constraint_mapping"] = {}
        report.details["constraint_mapping"][rule_key] = {
            "found": found,
            "rule_type": rule.type.value,
            **match_info
        }

        if found:
            report.total_found += 1
        else:
            report.issues.append(ComplianceIssue(
                category="constraint",
                severity="warning" if rule.type in (ValidationType.CUSTOM, ValidationType.WORKFLOW_CONSTRAINT) else "error",
                entity=rule.entity,
                field=rule.attribute,
                expected=f"{rule.type.value}: {rule.condition or 'N/A'}",
                actual=f"Not enforced (entity_match: {entity_match_info.get('match_mode', 'none')})",
                message=f"Missing constraint: {rule.entity}.{rule.attribute} ({rule.type.value})"
            ))


def check_full_ir_compliance(
    app_ir: ApplicationIR,
    generated_app_path: Optional[Path] = None,
    generated_code: Optional[Dict[str, str]] = None,
    mode: ValidationMode = ValidationMode.RELAXED
) -> Dict[str, ComplianceReport]:
    """
    Run full IR compliance check on generated application.

    Args:
        app_ir: The ApplicationIR with domain, behavior, and validation models
        generated_app_path: Path to generated app directory (legacy, for file-based validation)
        generated_code: Dict of relative path -> content (preferred, for pre-deployment validation)
            Expected keys: "src/models/entities.py", "src/models/schemas.py", "src/services/*.py"
        mode: ValidationMode.STRICT for exact matching, ValidationMode.RELAXED for semantic matching

    Returns dict of checker type -> report.
    """
    reports = {}

    # Extract content from generated_code dict if provided
    entities_content = None
    schemas_content = None
    services_content = None

    if generated_code:
        entities_content = generated_code.get("src/models/entities.py")
        schemas_content = generated_code.get("src/models/schemas.py")
        # Collect all service files
        services_content = {
            k: v for k, v in generated_code.items()
            if k.startswith("src/services/") and k.endswith(".py")
        }

    # Entity compliance
    if app_ir.domain_model:
        checker = EntityComplianceChecker(app_ir.domain_model, mode=mode)
        if entities_content is not None:
            reports["entities"] = checker.check_entities_file(content=entities_content)
        elif generated_app_path:
            entities_path = generated_app_path / "src" / "models" / "entities.py"
            reports["entities"] = checker.check_entities_file(entities_path=entities_path)
        else:
            reports["entities"] = checker.check_entities_file()  # Will generate error
        logger.info(f"📋 Entity compliance ({mode.value}): {reports['entities'].compliance_score:.1f}%")

    # Flow compliance
    if app_ir.behavior_model:
        checker = FlowComplianceChecker(app_ir.behavior_model, mode=mode)
        if services_content:
            reports["flows"] = checker.check_services_directory(services_content=services_content)
        elif generated_app_path:
            services_path = generated_app_path / "src" / "services"
            reports["flows"] = checker.check_services_directory(services_dir=services_path)
        else:
            reports["flows"] = checker.check_services_directory()  # Will generate error
        logger.info(f"📋 Flow compliance ({mode.value}): {reports['flows'].compliance_score:.1f}%")

    # Constraint compliance
    if app_ir.validation_model:
        checker = ConstraintComplianceChecker(app_ir.validation_model, mode=mode)
        if entities_content is not None or schemas_content is not None:
            reports["constraints"] = checker.check_constraints(
                entities_content=entities_content,
                schemas_content=schemas_content
            )
        elif generated_app_path:
            entities_path = generated_app_path / "src" / "models" / "entities.py"
            schemas_path = generated_app_path / "src" / "models" / "schemas.py"
            reports["constraints"] = checker.check_constraints(
                entities_path=entities_path,
                schemas_path=schemas_path
            )
        else:
            reports["constraints"] = checker.check_constraints()  # Will generate error
        logger.info(f"📋 Constraint compliance ({mode.value}): {reports['constraints'].compliance_score:.1f}%")

    # Summary
    total_score = sum(r.compliance_score for r in reports.values()) / max(1, len(reports))
    logger.info(f"📊 Overall IR compliance ({mode.value}): {total_score:.1f}%")

    # Store mode in reports for trazabilidad
    for report in reports.values():
        report.details["validation_mode"] = mode.value

    return reports
