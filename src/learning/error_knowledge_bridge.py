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
    NegativePatternStore.store()
           │
           ▼
    Next Generation: IRCentricCognitivePass queries patterns ✓

Reference: COGNITIVE_CODE_GENERATION_PROPOSAL.md
Created: 2025-11-30

Design Decision (2025-11-30):
- Prefer heuristic/structural parsing over regex for robustness
- URL normalization keeps minimal regex (numeric IDs, UUIDs) - simple patterns
- Exception extraction uses token-based parsing, no regex
- Error pattern abstraction uses structural parsing, no regex
- LLM fallback available for complex cases (opt-in via constructor)
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse

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
            existing = self._pattern_store.get(pattern_id)
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
            stored = self._pattern_store.store(anti_pattern)

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
        """
        Extract exception class from error message using token-based parsing.

        Design: NO REGEX - uses structural string parsing for robustness.

        Algorithm:
        1. Split by common delimiters (: and newline)
        2. Find tokens ending with 'Error' or 'Exception'
        3. Validate token is a valid Python identifier
        4. Return first match or "Unknown"

        Examples:
            "IntegrityError: duplicate key" → "IntegrityError"
            "sqlalchemy.exc.IntegrityError: ..." → "IntegrityError"
            "ValidationError\nDetails: ..." → "ValidationError"
        """
        if not error_message:
            return "Unknown"

        # Suffixes that indicate exception classes
        exception_suffixes = ("Error", "Exception", "Warning")

        # Split by common delimiters
        for delimiter in (":", "\n", " - ", " | "):
            parts = error_message.split(delimiter)
            for part in parts:
                # Clean and get last word (handles "sqlalchemy.exc.IntegrityError")
                tokens = part.strip().split(".")
                for token in reversed(tokens):
                    token = token.strip()
                    # Check if it's an exception class
                    if any(token.endswith(suffix) for suffix in exception_suffixes):
                        # Validate it looks like a class name (PascalCase, no spaces)
                        if token and token[0].isupper() and " " not in token:
                            return token

        # Fallback: scan all words
        words = error_message.replace(".", " ").replace(":", " ").split()
        for word in words:
            if any(word.endswith(suffix) for suffix in exception_suffixes):
                if word and word[0].isupper():
                    return word

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
        """
        Normalize endpoint to pattern form using structural parsing.

        Design: NO REGEX - uses segment-by-segment analysis.

        Algorithm:
        1. Split endpoint by '/'
        2. For each segment, check if it's an ID (numeric or UUID)
        3. Replace IDs with '{id}' placeholder
        4. Rejoin segments

        Examples:
            "/products/123"                    → "/products/{id}"
            "POST /orders/abc-def-123/items"   → "POST /orders/{id}/items"
            "/users/550e8400-e29b-41d4-a716"   → "/users/{id}"
        """
        if not endpoint:
            return "*"

        # Split method from path if present (e.g., "POST /products")
        parts = endpoint.split()
        if len(parts) >= 2:
            method = parts[0]
            path = parts[-1]
        else:
            method = None
            path = endpoint

        # Split path into segments
        segments = path.split("/")
        normalized_segments = []

        for segment in segments:
            if not segment:
                normalized_segments.append(segment)
                continue

            # Check if segment is a numeric ID
            if segment.isdigit():
                normalized_segments.append("{id}")
            # Check if segment is a UUID
            elif self._is_uuid(segment):
                normalized_segments.append("{id}")
            # Check if it's already a path parameter
            elif segment.startswith("{") and segment.endswith("}"):
                normalized_segments.append(segment)
            else:
                normalized_segments.append(segment)

        normalized_path = "/".join(normalized_segments)

        # Reconstruct with method if present
        if method:
            return f"{method} {normalized_path}"
        return normalized_path

    def _is_uuid(self, segment: str) -> bool:
        """
        Check if segment is a UUID without regex.

        UUID format: 8-4-4-4-12 hex characters
        Example: 550e8400-e29b-41d4-a716-446655440000
        """
        # Remove any leading/trailing whitespace
        clean = segment.strip()

        # UUIDs have exactly 36 characters (32 hex + 4 dashes)
        if len(clean) != 36:
            # Also check for partial UUIDs (at least 8-4-4 pattern)
            parts = clean.split("-")
            if len(parts) < 3:
                return False
            # Check if it looks like start of UUID
            if len(parts[0]) != 8:
                return False

        # Split by dashes
        parts = clean.split("-")

        # Full UUID has 5 parts
        if len(parts) == 5:
            expected_lengths = [8, 4, 4, 4, 12]
            for i, part in enumerate(parts):
                if len(part) != expected_lengths[i]:
                    return False
                # Check all characters are hex
                if not all(c in "0123456789abcdefABCDEF" for c in part):
                    return False
            return True

        # Partial UUID (at least looks like hex-with-dashes)
        if len(parts) >= 3:
            # Check all parts are hex
            for part in parts:
                if not all(c in "0123456789abcdefABCDEF" for c in part):
                    return False
            return True

        return False

    def _create_error_pattern(self, error_message: str) -> str:
        """
        Create a pattern from error message using structural parsing.

        Design: NO REGEX - uses character-level state machine for quotes,
        and token analysis for dates/numbers.

        Algorithm:
        1. Replace quoted strings with placeholders (state machine)
        2. Replace date-like tokens with 'DATE'
        3. Replace long numeric sequences with 'NUM'
        4. Truncate to reasonable length

        Examples:
            "IntegrityError: 'value123'" → "IntegrityError: '...'"
            "Date: 2025-11-30" → "Date: DATE"
            "ID: 12345678" → "ID: NUM"
        """
        if not error_message:
            return ""

        # Truncate first
        msg = error_message[:200]

        # Step 1: Replace quoted strings using state machine (no regex)
        result = []
        in_single_quote = False
        in_double_quote = False
        i = 0

        while i < len(msg):
            char = msg[i]

            if char == "'" and not in_double_quote:
                if in_single_quote:
                    result.append("...")
                    in_single_quote = False
                else:
                    result.append(char)
                    in_single_quote = True
            elif char == '"' and not in_single_quote:
                if in_double_quote:
                    result.append("...")
                    in_double_quote = False
                else:
                    result.append(char)
                    in_double_quote = True
            elif not in_single_quote and not in_double_quote:
                result.append(char)
            # Skip characters inside quotes (they'll be replaced with ...)

            i += 1

        pattern = "".join(result)

        # Step 2: Replace date-like tokens (structural check, no regex)
        tokens = pattern.split()
        processed_tokens = []

        for token in tokens:
            # Check if it looks like a date: YYYY-MM-DD or similar
            if self._looks_like_date(token):
                processed_tokens.append("DATE")
            # Check if it's a long number (likely an ID)
            elif self._looks_like_id(token):
                processed_tokens.append("NUM")
            else:
                processed_tokens.append(token)

        return " ".join(processed_tokens)

    def _looks_like_date(self, token: str) -> bool:
        """
        Check if token looks like a date without regex.

        Checks for patterns like: 2025-11-30, 2025/11/30, 30-11-2025
        """
        # Remove common punctuation from end
        clean = token.rstrip(".,;:)")

        # Check for date separators
        if "-" in clean or "/" in clean:
            # Split by either separator
            sep = "-" if "-" in clean else "/"
            parts = clean.split(sep)

            # Date should have 3 parts
            if len(parts) == 3:
                # All parts should be numeric
                if all(p.isdigit() for p in parts):
                    # Check reasonable lengths (year: 4, month/day: 1-2)
                    lengths = [len(p) for p in parts]
                    # YYYY-MM-DD or DD-MM-YYYY patterns
                    if 4 in lengths and all(1 <= l <= 4 for l in lengths):
                        return True

        return False

    def _looks_like_id(self, token: str) -> bool:
        """
        Check if token looks like a numeric ID without regex.

        Returns True for long numbers that are likely IDs (6+ digits).
        """
        # Remove common punctuation
        clean = token.rstrip(".,;:)")

        # Check if it's all digits and reasonably long
        if clean.isdigit() and len(clean) >= 6:
            return True

        # Check for UUID-like patterns (hex with dashes)
        if "-" in clean:
            parts = clean.split("-")
            if len(parts) >= 4:
                # Check if all parts are hex
                if all(all(c in "0123456789abcdefABCDEF" for c in p) for p in parts if p):
                    return True

        return False

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
