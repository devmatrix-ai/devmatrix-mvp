"""
Prompt Enhancer - Injects anti-patterns into code generation prompts.

Enhances LLM prompts with "AVOID THESE KNOWN ISSUES" warnings based on
previously seen errors, enabling the model to prevent recurring mistakes.

Reference: DOCS/mvp/exit/learning/GENERATION_FEEDBACK_LOOP.md
"""
import logging
from typing import Any, List, Optional

from src.learning.negative_pattern_store import (
    GenerationAntiPattern,
    NegativePatternStore,
    get_negative_pattern_store,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Enhancer
# =============================================================================


class GenerationPromptEnhancer:
    """
    Enhances code generation prompts with learned anti-patterns.

    Before (standard prompt):
        "Generate FastAPI endpoint for POST /products"

    After (enhanced prompt):
        "Generate FastAPI endpoint for POST /products

        AVOID THESE KNOWN ISSUES:
        1. IntegrityError on category_id: Always use Optional[int] for FK fields
        2. ValidationError on price: Ensure Decimal validation in schema
        3. ImportError: Import all models from src.models.entities"

    This teaches the LLM to avoid mistakes it has made before.
    """

    # Configuration
    MAX_ANTIPATTERNS_PER_PROMPT = 5   # Don't overwhelm the LLM
    MIN_OCCURRENCE_COUNT = 2          # Only include patterns seen 2+ times
    MAX_WARNING_LENGTH = 150          # Max characters per warning

    # Warning section header
    WARNING_HEADER = "\n\nAVOID THESE KNOWN ISSUES:"
    WARNING_FOOTER = "\n(Based on previous generation errors)"

    def __init__(
        self,
        pattern_store: Optional[NegativePatternStore] = None,
        max_patterns: int = None,
        min_occurrences: int = None,
    ):
        """
        Initialize enhancer.

        Args:
            pattern_store: NegativePatternStore instance (or uses singleton)
            max_patterns: Maximum patterns per prompt (default: 5)
            min_occurrences: Minimum occurrence count (default: 2)
        """
        self.pattern_store = pattern_store or get_negative_pattern_store()
        self.max_patterns = max_patterns or self.MAX_ANTIPATTERNS_PER_PROMPT
        self.min_occurrences = min_occurrences or self.MIN_OCCURRENCE_COUNT
        self.logger = logging.getLogger(f"{__name__}.GenerationPromptEnhancer")

        # Track which patterns were injected (for prevention tracking)
        self._injected_patterns: List[str] = []

    # =========================================================================
    # Public Enhancement Methods
    # =========================================================================

    def enhance_entity_prompt(
        self,
        base_prompt: str,
        entity_name: str,
        entity_ir: Any = None,
    ) -> str:
        """
        Enhance prompt for entity/model generation.

        Args:
            base_prompt: Original prompt for entity generation
            entity_name: Entity name (e.g., "Product")
            entity_ir: EntityIR object (optional, for field context)

        Returns:
            Enhanced prompt with anti-pattern warnings
        """
        patterns = self.pattern_store.get_patterns_for_entity(
            entity_name=entity_name,
            min_occurrences=self.min_occurrences,
        )

        # Also get generic database patterns
        db_patterns = self.pattern_store.get_patterns_by_error_type(
            error_type="database",
            min_occurrences=self.min_occurrences,
        )

        # Combine and deduplicate
        all_patterns = self._merge_patterns(patterns, db_patterns)

        enhanced = self._inject_patterns(base_prompt, all_patterns, context="entity")

        if len(all_patterns) > 0:
            self.logger.info(
                f"Enhanced entity prompt for {entity_name} with "
                f"{min(len(all_patterns), self.max_patterns)} warnings"
            )

        return enhanced

    def enhance_endpoint_prompt(
        self,
        base_prompt: str,
        endpoint_pattern: str,
        method: str = None,
    ) -> str:
        """
        Enhance prompt for endpoint/route generation.

        Args:
            base_prompt: Original prompt for endpoint generation
            endpoint_pattern: Endpoint path (e.g., "/products/{id}")
            method: HTTP method (e.g., "POST")

        Returns:
            Enhanced prompt with anti-pattern warnings
        """
        full_pattern = f"{method} {endpoint_pattern}" if method else endpoint_pattern

        patterns = self.pattern_store.get_patterns_for_endpoint(
            endpoint_pattern=full_pattern,
            method=method,
            min_occurrences=self.min_occurrences,
        )

        # Also get validation patterns (common for endpoints)
        validation_patterns = self.pattern_store.get_patterns_by_error_type(
            error_type="validation",
            min_occurrences=self.min_occurrences,
        )

        all_patterns = self._merge_patterns(patterns, validation_patterns)

        enhanced = self._inject_patterns(base_prompt, all_patterns, context="endpoint")

        if len(all_patterns) > 0:
            self.logger.info(
                f"Enhanced endpoint prompt for {full_pattern} with "
                f"{min(len(all_patterns), self.max_patterns)} warnings"
            )

        return enhanced

    def enhance_schema_prompt(
        self,
        base_prompt: str,
        schema_name: str,
        entity_ir: Any = None,
    ) -> str:
        """
        Enhance prompt for schema generation.

        Args:
            base_prompt: Original prompt for schema generation
            schema_name: Schema name (e.g., "ProductCreate")
            entity_ir: EntityIR object (optional)

        Returns:
            Enhanced prompt with anti-pattern warnings
        """
        patterns = self.pattern_store.get_patterns_for_schema(
            schema_name=schema_name,
            min_occurrences=self.min_occurrences,
        )

        enhanced = self._inject_patterns(base_prompt, patterns, context="schema")

        if len(patterns) > 0:
            self.logger.info(
                f"Enhanced schema prompt for {schema_name} with "
                f"{min(len(patterns), self.max_patterns)} warnings"
            )

        return enhanced

    def enhance_service_prompt(
        self,
        base_prompt: str,
        entity_name: str,
    ) -> str:
        """
        Enhance prompt for service/business logic generation.

        Args:
            base_prompt: Original prompt for service generation
            entity_name: Related entity name

        Returns:
            Enhanced prompt with anti-pattern warnings
        """
        # Services tend to have attribute and type errors
        attr_patterns = self.pattern_store.get_patterns_by_error_type(
            error_type="attribute",
            min_occurrences=self.min_occurrences,
        )

        type_patterns = self.pattern_store.get_patterns_by_error_type(
            error_type="type",
            min_occurrences=self.min_occurrences,
        )

        entity_patterns = self.pattern_store.get_patterns_for_entity(
            entity_name=entity_name,
            min_occurrences=self.min_occurrences,
        )

        all_patterns = self._merge_patterns(attr_patterns, type_patterns, entity_patterns)

        enhanced = self._inject_patterns(base_prompt, all_patterns, context="service")

        if len(all_patterns) > 0:
            self.logger.info(
                f"Enhanced service prompt for {entity_name} with "
                f"{min(len(all_patterns), self.max_patterns)} warnings"
            )

        return enhanced

    def enhance_generic_prompt(
        self,
        base_prompt: str,
        error_types: List[str] = None,
    ) -> str:
        """
        Enhance prompt with generic warnings (all error types).

        Args:
            base_prompt: Original prompt
            error_types: Specific error types to include (or all)

        Returns:
            Enhanced prompt
        """
        error_types = error_types or ["database", "validation", "import", "attribute"]

        all_patterns = []
        for error_type in error_types:
            patterns = self.pattern_store.get_patterns_by_error_type(
                error_type=error_type,
                min_occurrences=self.min_occurrences,
            )
            all_patterns.extend(patterns)

        # Deduplicate by pattern_id
        unique_patterns = {p.pattern_id: p for p in all_patterns}
        all_patterns = list(unique_patterns.values())

        return self._inject_patterns(base_prompt, all_patterns, context="generic")

    # =========================================================================
    # Prevention Tracking
    # =========================================================================

    def get_injected_patterns(self) -> List[str]:
        """Get list of pattern IDs that were injected in recent prompts."""
        return self._injected_patterns.copy()

    def clear_injected_patterns(self):
        """Clear the list of injected patterns."""
        self._injected_patterns = []

    def mark_patterns_as_prevented(self):
        """
        Mark all recently injected patterns as prevented.

        Call this after successful code generation that passed smoke tests.
        """
        for pattern_id in self._injected_patterns:
            self.pattern_store.increment_prevention(pattern_id)

        self.logger.info(
            f"Marked {len(self._injected_patterns)} patterns as prevented"
        )
        self._injected_patterns = []

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _inject_patterns(
        self,
        base_prompt: str,
        patterns: List[GenerationAntiPattern],
        context: str = "generic",
    ) -> str:
        """Format and inject patterns into prompt."""
        if not patterns:
            return base_prompt

        # Sort by severity (most common/impactful first)
        patterns = sorted(
            patterns,
            key=lambda p: (p.occurrence_count, -p.times_prevented),
            reverse=True
        )[:self.max_patterns]

        # Track injected patterns
        for p in patterns:
            if p.pattern_id not in self._injected_patterns:
                self._injected_patterns.append(p.pattern_id)

        # Format warnings
        warnings = [self.WARNING_HEADER]

        for i, p in enumerate(patterns, 1):
            warning = self._format_warning(p, i)
            warnings.append(warning)

        warnings.append(self.WARNING_FOOTER)

        return f"{base_prompt}{chr(10).join(warnings)}"

    def _format_warning(
        self,
        pattern: GenerationAntiPattern,
        index: int
    ) -> str:
        """Format a single pattern as a warning line."""
        # Build warning message
        location = ""
        if pattern.field_pattern and pattern.field_pattern != "*":
            location = f" on {pattern.field_pattern}"
        elif pattern.entity_pattern and pattern.entity_pattern != "*":
            location = f" in {pattern.entity_pattern}"

        fix = pattern.correct_code_snippet
        if len(fix) > self.MAX_WARNING_LENGTH:
            fix = fix[:self.MAX_WARNING_LENGTH - 3] + "..."

        warning = f"{index}. {pattern.exception_class}{location}: {fix}"

        return warning

    def _merge_patterns(
        self,
        *pattern_lists: List[GenerationAntiPattern]
    ) -> List[GenerationAntiPattern]:
        """Merge multiple pattern lists, deduplicating by pattern_id."""
        seen = set()
        merged = []

        for pattern_list in pattern_lists:
            for p in pattern_list:
                if p.pattern_id not in seen:
                    seen.add(p.pattern_id)
                    merged.append(p)

        return merged


# =============================================================================
# Singleton Instance
# =============================================================================

_prompt_enhancer: Optional[GenerationPromptEnhancer] = None


def get_prompt_enhancer() -> GenerationPromptEnhancer:
    """Get singleton instance of GenerationPromptEnhancer."""
    global _prompt_enhancer
    if _prompt_enhancer is None:
        _prompt_enhancer = GenerationPromptEnhancer()
    return _prompt_enhancer


# =============================================================================
# Convenience Functions
# =============================================================================


def enhance_prompt(
    base_prompt: str,
    entity_name: str = None,
    endpoint_pattern: str = None,
    schema_name: str = None,
    method: str = None,
) -> str:
    """
    Convenience function to enhance any prompt type.

    Auto-detects context and applies appropriate enhancements.

    Usage:
        prompt = enhance_prompt(
            "Generate FastAPI endpoint for POST /products",
            endpoint_pattern="/products",
            method="POST"
        )
    """
    enhancer = get_prompt_enhancer()

    if schema_name:
        return enhancer.enhance_schema_prompt(base_prompt, schema_name)
    elif endpoint_pattern:
        return enhancer.enhance_endpoint_prompt(base_prompt, endpoint_pattern, method)
    elif entity_name:
        return enhancer.enhance_entity_prompt(base_prompt, entity_name)
    else:
        return enhancer.enhance_generic_prompt(base_prompt)
