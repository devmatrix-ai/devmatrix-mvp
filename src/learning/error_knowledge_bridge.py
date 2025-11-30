"""
Error Knowledge Bridge - Bug #161

Bridges the gap between ErrorKnowledge (from smoke tests) and GenerationAntiPattern
(used by IRCentricCognitivePass for code generation).

The Problem:
- Smoke test failures are stored in ErrorKnowledge nodes (ErrorKnowledgeRepository)
- Code generation queries GenerationAntiPattern nodes (NegativePatternStore)
- These two systems were NOT connected, so learned errors were never used

The Solution:
This bridge converts ErrorKnowledge → GenerationAntiPattern and stores them
in the NegativePatternStore so they can be queried during code generation.

Architecture:
    Smoke Test Failure
           │
           ▼
    ErrorKnowledgeRepository.learn_from_failure()
           │
           ▼
    ErrorKnowledge (Neo4j node)
           │
           ▼
    ErrorKnowledgeBridge.bridge_to_anti_pattern()  ← NEW
           │
           ▼
    GenerationAntiPattern
           │
           ▼
    NegativePatternStore.store_pattern()
           │
           ▼
    Next Generation: IRCentricCognitivePass queries patterns ✓

Reference: COGNITIVE_CODE_GENERATION_PROPOSAL.md
Created: 2025-11-30
"""
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.learning.negative_pattern_store import (
    GenerationAntiPattern,
    NegativePatternStore,
    get_negative_pattern_store,
    create_anti_pattern,
    generate_pattern_id,
)

logger = logging.getLogger(__name__)


@dataclass
class BridgeResult:
    """Result of bridging an error to an anti-pattern."""
    success: bool
    pattern_id: Optional[str] = None
    message: str = ""
    is_new: bool = False


class ErrorKnowledgeBridge:
    """
    Bridges ErrorKnowledge to GenerationAntiPattern.

    Converts smoke test error data into anti-patterns that can be
    queried by IRCentricCognitivePass during code generation.
    """

    # Map HTTP status codes to error types
    STATUS_TO_ERROR_TYPE = {
        500: "server_error",
        422: "validation_error",
        404: "not_found",
        400: "bad_request",
        401: "auth_error",
        403: "forbidden",
    }

    # Map exception classes to severity scores
    EXCEPTION_SEVERITY = {
        "IntegrityError": 0.9,
        "AttributeError": 0.8,
        "TypeError": 0.7,
        "ValidationError": 0.6,
        "KeyError": 0.6,
        "ValueError": 0.5,
        "ImportError": 0.9,
    }

    def __init__(self, pattern_store: Optional[NegativePatternStore] = None):
        """
        Initialize bridge.

        Args:
            pattern_store: NegativePatternStore instance (uses singleton if None)
        """
        self._pattern_store = pattern_store or get_negative_pattern_store()
        self._bridged_count = 0
        self._errors: List[str] = []

    def bridge_from_smoke_error(
        self,
        endpoint_path: str,
        error_type: str,
        error_message: str,
        exception_class: Optional[str] = None,
        entity_name: Optional[str] = None,
        failed_code: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> BridgeResult:
        """
        Bridge a smoke test error to a GenerationAntiPattern.

        This is the main entry point called from RuntimeSmokeValidator.

        Args:
            endpoint_path: API endpoint that failed (e.g., "POST /products")
            error_type: Type of error (e.g., "500", "IntegrityError")
            error_message: Full error message
            exception_class: Exception class name if available
            entity_name: Entity name if extracted
            failed_code: Code snippet that caused the error
            status_code: HTTP status code if available

        Returns:
            BridgeResult with success status and pattern_id
        """
        try:
            # Extract exception class from error message if not provided
            if not exception_class:
                exception_class = self._extract_exception_class(error_message)

            # Extract entity from endpoint if not provided
            if not entity_name:
                entity_name = self._extract_entity_from_endpoint(endpoint_path)

            # Determine error type from status code if available
            if status_code and error_type in ("unknown", ""):
                error_type = self.STATUS_TO_ERROR_TYPE.get(status_code, "server_error")

            # Normalize endpoint to pattern
            endpoint_pattern = self._normalize_endpoint(endpoint_path)

            # Generate pattern ID
            pattern_id = generate_pattern_id(
                error_type=error_type,
                exception_class=exception_class or "Unknown",
                entity_pattern=entity_name or "*",
                endpoint_pattern=endpoint_pattern,
            )

            # Check if pattern already exists
            existing = self._pattern_store.get_pattern(pattern_id)
            if existing:
                # Increment occurrence count
                self._pattern_store.increment_occurrence(pattern_id)
                logger.debug(f"Incremented existing pattern: {pattern_id}")
                return BridgeResult(
                    success=True,
                    pattern_id=pattern_id,
                    message="Incremented existing pattern",
                    is_new=False,
                )

            # Create new anti-pattern
            anti_pattern = create_anti_pattern(
                error_type=error_type,
                exception_class=exception_class or "Unknown",
                entity_pattern=entity_name or "*",
                endpoint_pattern=endpoint_pattern,
                error_message_pattern=self._create_error_pattern(error_message),
                bad_code_snippet=failed_code[:500] if failed_code else "",
            )

            # Store in NegativePatternStore
            stored = self._pattern_store.store_pattern(anti_pattern)

            if stored:
                self._bridged_count += 1
                logger.info(
                    f"🌉 Bridged smoke error to anti-pattern: {pattern_id} "
                    f"(endpoint={endpoint_pattern}, entity={entity_name})"
                )
                return BridgeResult(
                    success=True,
                    pattern_id=pattern_id,
                    message="Created new anti-pattern",
                    is_new=True,
                )
            else:
                return BridgeResult(
                    success=False,
                    message="Failed to store pattern",
                )

        except Exception as e:
            error_msg = f"Bridge failed: {e}"
            self._errors.append(error_msg)
            logger.warning(error_msg)
            return BridgeResult(success=False, message=error_msg)

    def bridge_batch(
        self,
        violations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Bridge multiple smoke test violations to anti-patterns.

        Args:
            violations: List of violation dictionaries from smoke test

        Returns:
            Summary with counts and pattern IDs
        """
        results = {
            "total": len(violations),
            "bridged": 0,
            "new_patterns": 0,
            "existing_patterns": 0,
            "failed": 0,
            "pattern_ids": [],
        }

        for violation in violations:
            result = self.bridge_from_smoke_error(
                endpoint_path=violation.get("endpoint", violation.get("path", "")),
                error_type=violation.get("error_type", "unknown"),
                error_message=str(violation.get("error", violation.get("message", ""))),
                exception_class=violation.get("exception_class"),
                entity_name=violation.get("entity"),
                failed_code=violation.get("stack_trace"),
                status_code=violation.get("status_code"),
            )

            if result.success:
                results["bridged"] += 1
                if result.is_new:
                    results["new_patterns"] += 1
                else:
                    results["existing_patterns"] += 1
                if result.pattern_id:
                    results["pattern_ids"].append(result.pattern_id)
            else:
                results["failed"] += 1

        logger.info(
            f"🌉 Bridge batch complete: {results['bridged']}/{results['total']} "
            f"({results['new_patterns']} new, {results['existing_patterns']} existing)"
        )

        return results

    def _extract_exception_class(self, error_message: str) -> str:
        """Extract exception class from error message."""
        if not error_message:
            return "Unknown"

        # Common patterns: "IntegrityError: ...", "ValidationError: ..."
        match = re.search(r'(\w+Error|\w+Exception):', error_message)
        if match:
            return match.group(1)

        # Try to find any Error/Exception word
        match = re.search(r'(\w+Error|\w+Exception)', error_message)
        if match:
            return match.group(1)

        return "Unknown"

    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        if not endpoint:
            return None

        # "POST /products" → "Product"
        # "/carts/{id}/items" → "Cart"
        parts = endpoint.split()
        path = parts[-1] if parts else endpoint

        for segment in path.strip("/").split("/"):
            if segment and not segment.startswith("{") and segment not in ("api", "v1", "v2"):
                # Singularize and capitalize
                entity = segment.rstrip("s").capitalize()
                return entity

        return None

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint to pattern form."""
        if not endpoint:
            return "*"

        # /products/123 → /products/{id}
        pattern = re.sub(r'/\d+', '/{id}', endpoint)
        # UUIDs
        pattern = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            pattern,
            flags=re.IGNORECASE
        )
        return pattern

    def _create_error_pattern(self, error_message: str) -> str:
        """Create a pattern from error message for matching."""
        if not error_message:
            return ""

        # Truncate and clean
        pattern = error_message[:200]
        # Remove specific values that change
        pattern = re.sub(r"'[^']*'", "'...'", pattern)
        pattern = re.sub(r'"[^"]*"', '"..."', pattern)
        pattern = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', pattern)

        return pattern

    def get_statistics(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "bridged_count": self._bridged_count,
            "error_count": len(self._errors),
            "pattern_store_size": len(self._pattern_store._cache),
        }

    def reset(self) -> None:
        """Reset bridge statistics."""
        self._bridged_count = 0
        self._errors.clear()


# =============================================================================
# Singleton Instance
# =============================================================================

_error_knowledge_bridge: Optional[ErrorKnowledgeBridge] = None


def get_error_knowledge_bridge() -> ErrorKnowledgeBridge:
    """Get singleton instance of ErrorKnowledgeBridge."""
    global _error_knowledge_bridge
    if _error_knowledge_bridge is None:
        _error_knowledge_bridge = ErrorKnowledgeBridge()
    return _error_knowledge_bridge


# =============================================================================
# Convenience Function
# =============================================================================

def bridge_smoke_error_to_pattern(
    endpoint_path: str,
    error_type: str,
    error_message: str,
    **kwargs
) -> BridgeResult:
    """
    Convenience function to bridge a smoke error to an anti-pattern.

    Usage in RuntimeSmokeValidator._learn_from_error():
        from src.learning.error_knowledge_bridge import bridge_smoke_error_to_pattern

        bridge_smoke_error_to_pattern(
            endpoint_path="POST /products",
            error_type="500",
            error_message="IntegrityError: duplicate key",
            entity_name="Product",
        )
    """
    bridge = get_error_knowledge_bridge()
    return bridge.bridge_from_smoke_error(
        endpoint_path=endpoint_path,
        error_type=error_type,
        error_message=error_message,
        **kwargs
    )
