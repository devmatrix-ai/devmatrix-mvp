"""
Negative Pattern Store - Anti-pattern persistence for code generation prevention.

Stores GenerationAntiPattern nodes in Neo4j to feed into code generation prompts.
The goal is to prevent recurring generation errors by injecting "AVOID" warnings.

Reference: DOCS/mvp/exit/learning/GENERATION_FEEDBACK_LOOP.md
"""
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GenerationAntiPattern:
    """
    Anti-pattern that code generation should AVOID.

    Captured from smoke test failures to prevent the same errors in future runs.
    """
    pattern_id: str

    # Error signature
    error_type: str           # "database", "validation", "import", "attribute"
    exception_class: str      # "IntegrityError", "ValidationError", "KeyError"
    error_message_pattern: str  # Regex or key message fragment

    # IR context
    entity_pattern: str       # "Product", "Order", "*" for generic
    endpoint_pattern: str     # "POST /{entities}", "PUT /{entities}/{id}"
    field_pattern: str        # "foreign_key:*", "nullable:*", "type:uuid"

    # Code patterns
    bad_code_snippet: str     # What NOT to generate (example)
    correct_code_snippet: str # What TO generate instead

    # Learning metrics
    occurrence_count: int = 1       # How many times this error occurred
    times_prevented: int = 0        # How many times we avoided it
    last_seen: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def prevention_rate(self) -> float:
        """Calculate how often this pattern is prevented vs occurred."""
        total = self.occurrence_count + self.times_prevented
        return self.times_prevented / total if total > 0 else 0.0

    @property
    def severity_score(self) -> float:
        """Higher score = more important to prevent (based on frequency)."""
        # Patterns that occur often and aren't prevented are high priority
        if self.occurrence_count == 0:
            return 0.0
        recency_factor = 1.0  # Could decay over time
        frequency_factor = min(self.occurrence_count / 10, 1.0)  # Cap at 10
        prevention_factor = 1.0 - self.prevention_rate
        return recency_factor * frequency_factor * prevention_factor

    def to_prompt_warning(self) -> str:
        """Format as a warning for code generation prompts."""
        warning = f"{self.exception_class}"
        if self.field_pattern and self.field_pattern != "*":
            warning += f" on {self.field_pattern}"
        warning += f": {self.correct_code_snippet}"
        return warning

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "error_type": self.error_type,
            "exception_class": self.exception_class,
            "error_message_pattern": self.error_message_pattern,
            "entity_pattern": self.entity_pattern,
            "endpoint_pattern": self.endpoint_pattern,
            "field_pattern": self.field_pattern,
            "bad_code_snippet": self.bad_code_snippet,
            "correct_code_snippet": self.correct_code_snippet,
            "occurrence_count": self.occurrence_count,
            "times_prevented": self.times_prevented,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "prevention_rate": self.prevention_rate,
            "severity_score": self.severity_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationAntiPattern":
        """Create from dictionary."""
        last_seen = data.get("last_seen")
        created_at = data.get("created_at")

        if isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen)
        elif last_seen is None:
            last_seen = datetime.now()

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            pattern_id=data["pattern_id"],
            error_type=data.get("error_type", "unknown"),
            exception_class=data.get("exception_class", "Unknown"),
            error_message_pattern=data.get("error_message_pattern", ""),
            entity_pattern=data.get("entity_pattern", "*"),
            endpoint_pattern=data.get("endpoint_pattern", "*"),
            field_pattern=data.get("field_pattern", "*"),
            bad_code_snippet=data.get("bad_code_snippet", ""),
            correct_code_snippet=data.get("correct_code_snippet", ""),
            occurrence_count=data.get("occurrence_count", 1),
            times_prevented=data.get("times_prevented", 0),
            last_seen=last_seen,
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# Pattern ID Generation
# =============================================================================


def generate_pattern_id(
    error_type: str,
    exception_class: str,
    entity_pattern: str,
    endpoint_pattern: str,
    field_pattern: str = "*"
) -> str:
    """
    Generate deterministic pattern ID for deduplication.

    Same error signature should always produce the same ID.
    """
    key = f"{error_type}:{exception_class}:{entity_pattern}:{endpoint_pattern}:{field_pattern}"
    hash_val = hashlib.md5(key.encode()).hexdigest()[:12]
    return f"gap_{hash_val}"  # gap = Generation Anti-Pattern


# =============================================================================
# Negative Pattern Store
# =============================================================================


class NegativePatternStore:
    """
    Stores and retrieves GenerationAntiPatterns from Neo4j.

    Used by:
    - FeedbackCollector: To store new anti-patterns from smoke failures
    - PromptEnhancer: To retrieve relevant patterns for prompt injection

    Neo4j Schema:
        (:GenerationAntiPattern {
            pattern_id, error_type, exception_class, error_message_pattern,
            entity_pattern, endpoint_pattern, field_pattern,
            bad_code_snippet, correct_code_snippet,
            occurrence_count, times_prevented, last_seen, created_at
        })
    """

    # Thresholds for pattern retrieval
    MIN_OCCURRENCE_FOR_PROMPT = 2   # Only inject patterns seen 2+ times
    MAX_PATTERNS_PER_QUERY = 10     # Limit patterns per query

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize store with Neo4j connection."""
        self.logger = logging.getLogger(f"{__name__}.NegativePatternStore")

        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            self._neo4j_available = True
            self._ensure_schema()
        except Exception as e:
            self.logger.warning(f"Neo4j not available for NegativePatternStore: {e}")
            self._neo4j_available = False
            self.driver = None

        # In-memory cache for fast lookups
        self._cache: Dict[str, GenerationAntiPattern] = {}
        self._cache_loaded = False

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def _ensure_schema(self):
        """Ensure Neo4j schema exists."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                # Create constraint for unique pattern_id
                session.run("""
                    CREATE CONSTRAINT gap_pattern_id IF NOT EXISTS
                    FOR (ap:GenerationAntiPattern) REQUIRE ap.pattern_id IS UNIQUE
                """)

                # Create indexes for fast lookup
                session.run("""
                    CREATE INDEX gap_error_type IF NOT EXISTS
                    FOR (ap:GenerationAntiPattern) ON (ap.error_type)
                """)

                session.run("""
                    CREATE INDEX gap_entity IF NOT EXISTS
                    FOR (ap:GenerationAntiPattern) ON (ap.entity_pattern)
                """)

                session.run("""
                    CREATE INDEX gap_endpoint IF NOT EXISTS
                    FOR (ap:GenerationAntiPattern) ON (ap.endpoint_pattern)
                """)

                session.run("""
                    CREATE INDEX gap_exception IF NOT EXISTS
                    FOR (ap:GenerationAntiPattern) ON (ap.exception_class)
                """)

                self.logger.debug("Neo4j schema for GenerationAntiPattern ensured")

        except Exception as e:
            self.logger.warning(f"Failed to ensure schema: {e}")

    # =========================================================================
    # Core CRUD Operations
    # =========================================================================

    def store(self, pattern: GenerationAntiPattern) -> bool:
        """
        Store a new anti-pattern.

        If pattern_id already exists, increments occurrence_count instead.

        Returns:
            True if stored/updated successfully
        """
        # Update cache
        self._cache[pattern.pattern_id] = pattern

        if not self._neo4j_available or not self.driver:
            return True  # Cache-only mode

        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (ap:GenerationAntiPattern {pattern_id: $pattern_id})
                    ON CREATE SET
                        ap.error_type = $error_type,
                        ap.exception_class = $exception_class,
                        ap.error_message_pattern = $error_message_pattern,
                        ap.entity_pattern = $entity_pattern,
                        ap.endpoint_pattern = $endpoint_pattern,
                        ap.field_pattern = $field_pattern,
                        ap.bad_code_snippet = $bad_code_snippet,
                        ap.correct_code_snippet = $correct_code_snippet,
                        ap.occurrence_count = 1,
                        ap.times_prevented = 0,
                        ap.created_at = datetime(),
                        ap.last_seen = datetime()
                    ON MATCH SET
                        ap.occurrence_count = ap.occurrence_count + 1,
                        ap.last_seen = datetime(),
                        ap.bad_code_snippet = CASE
                            WHEN $bad_code_snippet <> '' THEN $bad_code_snippet
                            ELSE ap.bad_code_snippet
                        END,
                        ap.correct_code_snippet = CASE
                            WHEN $correct_code_snippet <> '' THEN $correct_code_snippet
                            ELSE ap.correct_code_snippet
                        END
                """, {
                    "pattern_id": pattern.pattern_id,
                    "error_type": pattern.error_type,
                    "exception_class": pattern.exception_class,
                    "error_message_pattern": pattern.error_message_pattern[:500],
                    "entity_pattern": pattern.entity_pattern,
                    "endpoint_pattern": pattern.endpoint_pattern,
                    "field_pattern": pattern.field_pattern,
                    "bad_code_snippet": pattern.bad_code_snippet[:1000],
                    "correct_code_snippet": pattern.correct_code_snippet[:1000],
                })

                self.logger.debug(f"Stored anti-pattern: {pattern.pattern_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to store anti-pattern: {e}")
            return False

    def exists(self, pattern_id: str) -> bool:
        """Check if pattern exists."""
        if pattern_id in self._cache:
            return True

        if not self._neo4j_available or not self.driver:
            return False

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern {pattern_id: $pattern_id})
                    RETURN count(ap) > 0 AS exists
                """, pattern_id=pattern_id)

                record = result.single()
                return record["exists"] if record else False

        except Exception as e:
            self.logger.warning(f"Failed to check pattern existence: {e}")
            return False

    def get(self, pattern_id: str) -> Optional[GenerationAntiPattern]:
        """Get pattern by ID."""
        if pattern_id in self._cache:
            return self._cache[pattern_id]

        if not self._neo4j_available or not self.driver:
            return None

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern {pattern_id: $pattern_id})
                    RETURN ap
                """, pattern_id=pattern_id)

                record = result.single()
                if record:
                    pattern = self._node_to_pattern(record["ap"])
                    self._cache[pattern_id] = pattern
                    return pattern

        except Exception as e:
            self.logger.warning(f"Failed to get pattern: {e}")

        return None

    def increment_occurrence(self, pattern_id: str) -> bool:
        """Increment occurrence count for existing pattern."""
        if pattern_id in self._cache:
            self._cache[pattern_id].occurrence_count += 1
            self._cache[pattern_id].last_seen = datetime.now()

        if not self._neo4j_available or not self.driver:
            return True

        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (ap:GenerationAntiPattern {pattern_id: $pattern_id})
                    SET ap.occurrence_count = ap.occurrence_count + 1,
                        ap.last_seen = datetime()
                """, pattern_id=pattern_id)
                return True

        except Exception as e:
            self.logger.warning(f"Failed to increment occurrence: {e}")
            return False

    def increment_prevention(self, pattern_id: str) -> bool:
        """
        Increment prevention count when pattern was successfully avoided.

        Called when code generation succeeds after receiving this warning.
        """
        if pattern_id in self._cache:
            self._cache[pattern_id].times_prevented += 1

        if not self._neo4j_available or not self.driver:
            return True

        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (ap:GenerationAntiPattern {pattern_id: $pattern_id})
                    SET ap.times_prevented = ap.times_prevented + 1
                """, pattern_id=pattern_id)
                return True

        except Exception as e:
            self.logger.warning(f"Failed to increment prevention: {e}")
            return False

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_patterns_for_entity(
        self,
        entity_name: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """
        Get anti-patterns relevant to an entity.

        Args:
            entity_name: Entity name (e.g., "Product")
            min_occurrences: Minimum occurrence count (default: MIN_OCCURRENCE_FOR_PROMPT)

        Returns:
            List of relevant anti-patterns sorted by severity
        """
        min_occ = min_occurrences or self.MIN_OCCURRENCE_FOR_PROMPT

        # Check cache first
        cached = [
            p for p in self._cache.values()
            if (p.entity_pattern == entity_name or p.entity_pattern == "*")
            and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE (ap.entity_pattern = $entity_name OR ap.entity_pattern = '*')
                      AND ap.occurrence_count >= $min_occ
                    RETURN ap
                    ORDER BY ap.occurrence_count DESC
                    LIMIT $limit
                """, {
                    "entity_name": entity_name,
                    "min_occ": min_occ,
                    "limit": self.MAX_PATTERNS_PER_QUERY
                })

                patterns = []
                for record in result:
                    pattern = self._node_to_pattern(record["ap"])
                    self._cache[pattern.pattern_id] = pattern
                    patterns.append(pattern)

                return sorted(patterns, key=lambda p: p.severity_score, reverse=True)

        except Exception as e:
            self.logger.warning(f"Failed to query patterns for entity: {e}")
            return cached

    def get_patterns_for_endpoint(
        self,
        endpoint_pattern: str,
        method: str = None,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """
        Get anti-patterns relevant to an endpoint.

        Args:
            endpoint_pattern: Endpoint pattern (e.g., "POST /products")
            method: HTTP method (optional, for filtering)
            min_occurrences: Minimum occurrence count

        Returns:
            List of relevant anti-patterns
        """
        min_occ = min_occurrences or self.MIN_OCCURRENCE_FOR_PROMPT

        # Normalize endpoint pattern
        normalized = self._normalize_endpoint(endpoint_pattern)

        # Check cache first
        cached = [
            p for p in self._cache.values()
            if self._endpoint_matches(p.endpoint_pattern, normalized)
            and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE ap.occurrence_count >= $min_occ
                    RETURN ap
                    ORDER BY ap.occurrence_count DESC
                    LIMIT $limit
                """, {
                    "min_occ": min_occ,
                    "limit": self.MAX_PATTERNS_PER_QUERY * 2  # Fetch more for filtering
                })

                patterns = []
                for record in result:
                    pattern = self._node_to_pattern(record["ap"])
                    if self._endpoint_matches(pattern.endpoint_pattern, normalized):
                        self._cache[pattern.pattern_id] = pattern
                        patterns.append(pattern)

                return sorted(
                    patterns[:self.MAX_PATTERNS_PER_QUERY],
                    key=lambda p: p.severity_score,
                    reverse=True
                )

        except Exception as e:
            self.logger.warning(f"Failed to query patterns for endpoint: {e}")
            return cached

    def get_patterns_for_schema(
        self,
        schema_name: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """
        Get anti-patterns relevant to a schema.

        Schema patterns relate to validation errors (ValidationError, KeyError).

        Args:
            schema_name: Schema name (e.g., "ProductCreate")
            min_occurrences: Minimum occurrence count
        """
        min_occ = min_occurrences or self.MIN_OCCURRENCE_FOR_PROMPT

        # Extract entity from schema name (ProductCreate -> Product)
        entity_name = re.sub(r'(Create|Update|Read|Base|Schema)$', '', schema_name)

        # Get patterns for validation errors
        cached = [
            p for p in self._cache.values()
            if p.error_type == "validation"
            and (p.entity_pattern == entity_name or p.entity_pattern == "*")
            and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE ap.error_type = 'validation'
                      AND (ap.entity_pattern = $entity_name OR ap.entity_pattern = '*')
                      AND ap.occurrence_count >= $min_occ
                    RETURN ap
                    ORDER BY ap.occurrence_count DESC
                    LIMIT $limit
                """, {
                    "entity_name": entity_name,
                    "min_occ": min_occ,
                    "limit": self.MAX_PATTERNS_PER_QUERY
                })

                patterns = []
                for record in result:
                    pattern = self._node_to_pattern(record["ap"])
                    self._cache[pattern.pattern_id] = pattern
                    patterns.append(pattern)

                return sorted(patterns, key=lambda p: p.severity_score, reverse=True)

        except Exception as e:
            self.logger.warning(f"Failed to query patterns for schema: {e}")
            return cached

    def get_patterns_by_error_type(
        self,
        error_type: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """Get all patterns of a specific error type."""
        min_occ = min_occurrences or self.MIN_OCCURRENCE_FOR_PROMPT

        cached = [
            p for p in self._cache.values()
            if p.error_type == error_type and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE ap.error_type = $error_type
                      AND ap.occurrence_count >= $min_occ
                    RETURN ap
                    ORDER BY ap.occurrence_count DESC
                    LIMIT $limit
                """, {
                    "error_type": error_type,
                    "min_occ": min_occ,
                    "limit": self.MAX_PATTERNS_PER_QUERY
                })

                patterns = []
                for record in result:
                    pattern = self._node_to_pattern(record["ap"])
                    self._cache[pattern.pattern_id] = pattern
                    patterns.append(pattern)

                return sorted(patterns, key=lambda p: p.severity_score, reverse=True)

        except Exception as e:
            self.logger.warning(f"Failed to query patterns by error type: {e}")
            return cached

    def get_all_patterns(
        self,
        min_occurrences: int = 1,
        limit: int = 100
    ) -> List[GenerationAntiPattern]:
        """Get all patterns above minimum occurrence threshold."""
        if not self._neo4j_available or not self.driver:
            return sorted(
                [p for p in self._cache.values() if p.occurrence_count >= min_occurrences],
                key=lambda p: p.severity_score,
                reverse=True
            )[:limit]

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE ap.occurrence_count >= $min_occ
                    RETURN ap
                    ORDER BY ap.occurrence_count DESC
                    LIMIT $limit
                """, {
                    "min_occ": min_occurrences,
                    "limit": limit
                })

                patterns = []
                for record in result:
                    pattern = self._node_to_pattern(record["ap"])
                    self._cache[pattern.pattern_id] = pattern
                    patterns.append(pattern)

                return patterns

        except Exception as e:
            self.logger.warning(f"Failed to get all patterns: {e}")
            return list(self._cache.values())[:limit]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics."""
        if not self._neo4j_available or not self.driver:
            patterns = list(self._cache.values())
            total = len(patterns)
            return {
                "total_patterns": total,
                "total_occurrences": sum(p.occurrence_count for p in patterns),
                "total_preventions": sum(p.times_prevented for p in patterns),
                "avg_prevention_rate": (
                    sum(p.prevention_rate for p in patterns) / total if total else 0
                ),
                "patterns_by_error_type": {},
                "source": "cache"
            }

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    RETURN
                        count(ap) AS total,
                        sum(ap.occurrence_count) AS total_occurrences,
                        sum(ap.times_prevented) AS total_preventions,
                        collect({
                            error_type: ap.error_type,
                            count: 1
                        }) AS by_type
                """)

                record = result.single()
                if record:
                    # Aggregate by error type
                    by_type = {}
                    for item in record["by_type"]:
                        et = item["error_type"]
                        by_type[et] = by_type.get(et, 0) + 1

                    total = record["total"]
                    total_occ = record["total_occurrences"] or 0
                    total_prev = record["total_preventions"] or 0

                    return {
                        "total_patterns": total,
                        "total_occurrences": total_occ,
                        "total_preventions": total_prev,
                        "avg_prevention_rate": (
                            total_prev / (total_occ + total_prev)
                            if (total_occ + total_prev) > 0 else 0
                        ),
                        "patterns_by_error_type": by_type,
                        "source": "neo4j"
                    }

        except Exception as e:
            self.logger.warning(f"Failed to get statistics: {e}")

        return {
            "total_patterns": len(self._cache),
            "source": "cache_fallback"
        }

    def load_cache(self, limit: int = 100) -> int:
        """Load patterns into cache from Neo4j."""
        if self._cache_loaded:
            return len(self._cache)

        patterns = self.get_all_patterns(min_occurrences=1, limit=limit)
        self._cache_loaded = True

        self.logger.info(f"Loaded {len(patterns)} anti-patterns into cache")
        return len(patterns)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _node_to_pattern(self, node) -> GenerationAntiPattern:
        """Convert Neo4j node to GenerationAntiPattern."""
        # Handle Neo4j datetime
        last_seen = node.get("last_seen")
        created_at = node.get("created_at")

        if hasattr(last_seen, "to_native"):
            last_seen = last_seen.to_native()
        elif last_seen is None:
            last_seen = datetime.now()

        if hasattr(created_at, "to_native"):
            created_at = created_at.to_native()
        elif created_at is None:
            created_at = datetime.now()

        return GenerationAntiPattern(
            pattern_id=node["pattern_id"],
            error_type=node.get("error_type", "unknown"),
            exception_class=node.get("exception_class", "Unknown"),
            error_message_pattern=node.get("error_message_pattern", ""),
            entity_pattern=node.get("entity_pattern", "*"),
            endpoint_pattern=node.get("endpoint_pattern", "*"),
            field_pattern=node.get("field_pattern", "*"),
            bad_code_snippet=node.get("bad_code_snippet", ""),
            correct_code_snippet=node.get("correct_code_snippet", ""),
            occurrence_count=node.get("occurrence_count", 1),
            times_prevented=node.get("times_prevented", 0),
            last_seen=last_seen,
            created_at=created_at,
        )

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint to pattern form."""
        # /products/123 → /products/{id}
        # /users/abc-def/orders → /users/{id}/orders
        pattern = re.sub(r'/\d+', '/{id}', endpoint)
        pattern = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            pattern,
            flags=re.IGNORECASE
        )
        return pattern

    def _endpoint_matches(self, pattern: str, endpoint: str) -> bool:
        """Check if endpoint matches pattern."""
        if pattern == "*":
            return True
        if pattern == endpoint:
            return True

        # Generalize both and compare
        norm_pattern = self._normalize_endpoint(pattern)
        norm_endpoint = self._normalize_endpoint(endpoint)

        return norm_pattern == norm_endpoint


# =============================================================================
# Singleton Instance
# =============================================================================

_negative_pattern_store: Optional[NegativePatternStore] = None


def get_negative_pattern_store() -> NegativePatternStore:
    """Get singleton instance of NegativePatternStore."""
    global _negative_pattern_store
    if _negative_pattern_store is None:
        _negative_pattern_store = NegativePatternStore(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _negative_pattern_store


# =============================================================================
# Convenience Functions
# =============================================================================


def create_anti_pattern(
    error_type: str,
    exception_class: str,
    entity_pattern: str,
    endpoint_pattern: str,
    field_pattern: str = "*",
    error_message_pattern: str = "",
    bad_code_snippet: str = "",
    correct_code_snippet: str = ""
) -> GenerationAntiPattern:
    """
    Create a new GenerationAntiPattern with auto-generated ID.

    Convenience function for creating patterns from smoke test failures.
    """
    pattern_id = generate_pattern_id(
        error_type=error_type,
        exception_class=exception_class,
        entity_pattern=entity_pattern,
        endpoint_pattern=endpoint_pattern,
        field_pattern=field_pattern
    )

    return GenerationAntiPattern(
        pattern_id=pattern_id,
        error_type=error_type,
        exception_class=exception_class,
        error_message_pattern=error_message_pattern,
        entity_pattern=entity_pattern,
        endpoint_pattern=endpoint_pattern,
        field_pattern=field_pattern,
        bad_code_snippet=bad_code_snippet,
        correct_code_snippet=correct_code_snippet,
    )
