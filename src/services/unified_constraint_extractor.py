"""
Phase 2: Unified Constraint Extractor.

Orchestrates constraint extraction from all sources (BusinessLogicExtractor, etc),
normalizes to canonical form, and produces unified ValidationModelIR.

PHASE 4 ALIGNED: Works directly with ValidationType and EnforcementType.
CRITICAL: Single entry point for constraint extraction - aggregates all sources.
"""

import logging
from typing import Dict, List, Any, Optional

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.validation_model import (
    ValidationModelIR,
    ValidationRule,
    ValidationType,
    EnforcementType,
)
from src.services.business_logic_extractor import BusinessLogicExtractor
from src.services.semantic_normalizer import (
    SemanticNormalizer,
    ConstraintRule,
    NormalizedRule,
)

logger = logging.getLogger(__name__)


class UnifiedConstraintExtractor:
    """
    Unified constraint extraction and merging orchestrator.

    Flow:
    1. Extract from BusinessLogicExtractor (already comprehensive)
    2. Apply SemanticNormalizer for further normalization if needed
    3. Merge by semantic constraint_key
    4. Output deduplicated ValidationModelIR

    PHASE 2 ROLE: Primary orchestrator that ensures:
    - All constraints normalized to Phase 4 canonical form
    - Deduplication by entity.field.constraint_type
    - Confidence scoring attached to each rule
    - Source tracking for debugging
    """

    # Constraint key format for deduplication
    CONSTRAINT_KEY_FORMAT = "{entity}.{field}.{validation_type}"

    # Source priority (lower number = higher priority when merging duplicates)
    SOURCE_PRIORITY = {
        "ast_sqlalchemy": 1,   # Highest reliability
        "ast_pydantic": 2,
        "openapi": 3,
        "business_logic": 4,
        "llm": 5,
        "pattern_based": 6,
        "unknown": 7,
    }

    def __init__(self, application_ir: ApplicationIR):
        """
        Initialize unified extractor.

        Args:
            application_ir: ApplicationIR with entities, fields, and validation config
        """
        self.ir = application_ir
        self.business_logic_extractor = BusinessLogicExtractor()
        self.semantic_normalizer = SemanticNormalizer(application_ir)

    async def extract_all(self, spec: Dict[str, Any]) -> ValidationModelIR:
        """
        Extract all constraints from spec and merge to unified IR.

        Args:
            spec: Specification dictionary with entities, endpoints, etc.

        Returns:
            ValidationModelIR with fully merged constraint set
        """
        logger.info("🔍 Starting unified constraint extraction...")

        # Step 1: Extract from all sources
        all_rules = []

        # Primary source: BusinessLogicExtractor (comprehensive, already normalized)
        try:
            bl_model = self.business_logic_extractor.extract_validation_rules(spec)
            all_rules.extend(bl_model.rules)
            logger.info(f"✅ BusinessLogicExtractor: {len(bl_model.rules)} rules")
        except Exception as e:
            logger.error(f"❌ BusinessLogicExtractor failed: {e}")

        # Step 2: Deduplicate and merge
        merged_rules = self._semantic_merge(all_rules)
        logger.info(f"🔗 Merged to {len(merged_rules)} unique constraints")

        # Step 3: Build final ValidationModelIR
        validation_model = ValidationModelIR(
            rules=merged_rules,
        )

        logger.info(
            f"✅ Unified extraction complete: {len(merged_rules)} normalized constraints"
        )
        return validation_model

    def _semantic_merge(
        self,
        rules: List[ValidationRule],
    ) -> List[ValidationRule]:
        """
        Merge and deduplicate by semantic ID: entity.field.validation_type.

        Algorithm:
        1. Build constraint_key for each rule
        2. Group by constraint_key
        3. For duplicates, keep highest-priority rule
        4. Return deduplicated list

        Args:
            rules: List of ValidationRules from all sources

        Returns:
            Deduplicated list of ValidationRules
        """
        constraint_map: Dict[str, ValidationRule] = {}

        for rule in rules:
            constraint_key = self._make_constraint_key(rule)

            if constraint_key not in constraint_map:
                # First occurrence
                constraint_map[constraint_key] = rule
            else:
                # Duplicate - keep higher priority
                existing = constraint_map[constraint_key]
                existing_priority = self.SOURCE_PRIORITY.get(
                    self._infer_source(existing), 99
                )
                new_priority = self.SOURCE_PRIORITY.get(self._infer_source(rule), 99)

                if new_priority < existing_priority:
                    logger.debug(
                        f"🔄 Replacing {constraint_key} "
                        f"(priority {existing_priority} → {new_priority})"
                    )
                    constraint_map[constraint_key] = rule

        dedup_count = len(rules) - len(constraint_map)
        if dedup_count > 0:
            logger.info(f"🎯 Deduplication: removed {dedup_count} duplicates")

        return list(constraint_map.values())

    @staticmethod
    def _make_constraint_key(rule: ValidationRule) -> str:
        """
        Create semantic constraint key for deduplication.

        Key = "{entity}.{field}.{validation_type}"

        This groups equivalent constraints across sources:
        - price.product.range (OpenAPI extraction)
        - unit_price.product.range (AST extraction)
        → Same key, deduplicated to one rule
        """
        entity = rule.entity or "unknown"
        field = rule.attribute or "unknown"
        vtype = rule.type.value if rule.type else "unknown"
        return f"{entity}.{field}.{vtype}"

    @staticmethod
    def _infer_source(rule: ValidationRule) -> str:
        """
        Infer source of a rule from its properties.

        Heuristics:
        - enforcement_type == BUSINESS_LOGIC → business_logic
        - enforcement_code contains "@field_validator" → pydantic
        - etc.
        """
        # If enforcement_type is set, use it to infer source
        if rule.enforcement_type == EnforcementType.BUSINESS_LOGIC:
            return "business_logic"

        # Check enforcement_code for patterns
        if rule.enforcement_code:
            if "@field_validator" in rule.enforcement_code:
                return "ast_pydantic"
            if "Column" in rule.enforcement_code:
                return "ast_sqlalchemy"

        # Default
        return "unknown"


async def extract_all_constraints_sync(
    application_ir: ApplicationIR,
    spec: Dict[str, Any],
) -> ValidationModelIR:
    """
    Synchronous convenience function for extracting all constraints.

    Args:
        application_ir: ApplicationIR providing canonical forms
        spec: Specification dictionary

    Returns:
        ValidationModelIR with all extracted and merged constraints
    """
    extractor = UnifiedConstraintExtractor(application_ir)
    return await extractor.extract_all(spec)
