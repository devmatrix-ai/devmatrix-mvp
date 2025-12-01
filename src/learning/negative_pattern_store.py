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
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Suppress Neo4j "index/constraint already exists" notifications
# These are INFO level and not errors - they just clutter the logs
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)


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
    def confidence(self) -> float:
        """
        Compatibility helper: Some consumers expect `confidence`.
        We use severity_score as a proxy when explicit confidence is absent.
        """
        return self.severity_score

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


@dataclass
class CognitiveRegressionPattern:
    """
    Records failed cognitive enhancement attempts for learning.

    When IRCentricCognitivePass enhances code but validation fails,
    this pattern is stored to avoid repeating the same mistake.

    Reference: COGNITIVE_CODE_GENERATION_PROPOSAL.md v2.0
    """
    # Flow context
    ir_flow: str                      # Flow name that was enhanced
    flow_id: Optional[str] = None     # Flow ID for semantic matching

    # Enhancement context
    anti_patterns_applied: List[str] = field(default_factory=list)  # Pattern IDs used

    # Failure details
    result: str = "ir_contract_violation"  # "ir_contract_violation", "test_regression", "syntax_error"
    violations: List[str] = field(default_factory=list)  # Specific violations

    # Additional context
    enhanced_function: Optional[str] = None  # Function that was enhanced
    original_function: Optional[str] = None  # Original function code
    file_path: Optional[str] = None          # File where enhancement was attempted

    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)

    # Regression ID for deduplication
    regression_id: Optional[str] = None

    def __post_init__(self):
        """Generate regression_id if not provided."""
        if not self.regression_id:
            key = f"{self.ir_flow}:{self.result}:{':'.join(sorted(self.anti_patterns_applied[:5]))}"
            self.regression_id = f"crp_{hashlib.md5(key.encode()).hexdigest()[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "regression_id": self.regression_id,
            "ir_flow": self.ir_flow,
            "flow_id": self.flow_id,
            "anti_patterns_applied": self.anti_patterns_applied,
            "result": self.result,
            "violations": self.violations,
            "enhanced_function": self.enhanced_function,
            "original_function": self.original_function,
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveRegressionPattern":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            ir_flow=data.get("ir_flow", "unknown"),
            flow_id=data.get("flow_id"),
            anti_patterns_applied=data.get("anti_patterns_applied", []),
            result=data.get("result", "unknown"),
            violations=data.get("violations", []),
            enhanced_function=data.get("enhanced_function"),
            original_function=data.get("original_function"),
            file_path=data.get("file_path"),
            timestamp=timestamp,
            regression_id=data.get("regression_id"),
        )


@dataclass
class PositiveRepairPattern:
    """
    Successful repair that should be reused.
    
    LEARNING_GAPS Phase 2.1: Records repairs that worked to guide future fixes.
    """
    pattern_id: str
    
    # Repair signature
    repair_type: str          # "entity_addition", "endpoint_addition", "validation_fix", "import_fix"
    entity_pattern: str       # "Product", "Order", "*" for generic
    endpoint_pattern: str     # "POST /{entities}", "*"
    field_pattern: str        # "foreign_key:*", "nullable:*", "*"
    
    # Repair details
    fix_description: str      # Human-readable description of the fix
    code_snippet: str         # Code that was added/modified (truncated to 500 chars)
    file_path: str            # File that was modified (e.g., "src/models/entities.py")
    
    # Learning metrics
    success_count: int = 1    # How many times this repair was successfully applied
    last_applied: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def reuse_score(self) -> float:
        """Higher score = more likely to be useful for future repairs."""
        # Patterns that have been reused successfully are high value
        if self.success_count == 0:
            return 0.0
        frequency_factor = min(self.success_count / 5, 1.0)  # Cap at 5 reuses
        recency_factor = 1.0  # Could decay over time
        return frequency_factor * recency_factor
    
    def to_prompt_example(self) -> str:
        """Format as a positive example for prompts."""
        example = f"✅ SUCCESSFUL PATTERN (used {self.success_count}x):\n"
        example += f"   Type: {self.repair_type}\n"
        example += f"   Context: {self.entity_pattern}"
        if self.endpoint_pattern != "*":
            example += f" / {self.endpoint_pattern}"
        example += f"\n   Solution: {self.fix_description}\n\n"
        if self.code_snippet:
            example += f"   Example:\n   ```python\n   {self.code_snippet[:300]}...\n   ```\n"
        return example
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "repair_type": self.repair_type,
            "entity_pattern": self.entity_pattern,
            "endpoint_pattern": self.endpoint_pattern,
            "field_pattern": self.field_pattern,
            "fix_description": self.fix_description,
            "code_snippet": self.code_snippet,
            "file_path": self.file_path,
            "success_count": self.success_count,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reuse_score": self.reuse_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositiveRepairPattern":
        """Create from dictionary."""
        last_applied = data.get("last_applied")
        created_at = data.get("created_at")
        
        if isinstance(last_applied, str):
            last_applied = datetime.fromisoformat(last_applied)
        elif last_applied is None:
            last_applied = datetime.now()
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        return cls(
            pattern_id=data["pattern_id"],
            repair_type=data.get("repair_type", "unknown"),
            entity_pattern=data.get("entity_pattern", "*"),
            endpoint_pattern=data.get("endpoint_pattern", "*"),
            field_pattern=data.get("field_pattern", "*"),
            fix_description=data.get("fix_description", ""),
            code_snippet=data.get("code_snippet", ""),
            file_path=data.get("file_path", ""),
            success_count=data.get("success_count", 1),
            last_applied=last_applied,
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

                # Phase 2.1: Schema for PositiveRepairPattern
                session.run("""
                    CREATE CONSTRAINT prp_pattern_id IF NOT EXISTS
                    FOR (pr:PositiveRepairPattern) REQUIRE pr.pattern_id IS UNIQUE
                """)

                session.run("""
                    CREATE INDEX prp_repair_type IF NOT EXISTS
                    FOR (pr:PositiveRepairPattern) ON (pr.repair_type)
                """)

                self.logger.debug("Neo4j schema for GenerationAntiPattern + PositiveRepairPattern ensured")

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

    def update_correct_snippet(self, pattern_id: str, correct_code: str) -> bool:
        """
        Update the correct_code_snippet for an existing pattern.

        Bug #163 Fix: Called when a repair is successful to backfill
        the correct solution, closing the learning loop.

        Args:
            pattern_id: The pattern to update
            correct_code: The verified correct code snippet

        Returns:
            True if updated successfully
        """
        if not correct_code or not correct_code.strip():
            return False

        # Update cache
        if pattern_id in self._cache:
            self._cache[pattern_id].correct_code_snippet = correct_code
            self.logger.info(f"📚 Updated cache with correct_code for {pattern_id}")

        if not self._neo4j_available or not self.driver:
            return True

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern {pattern_id: $pattern_id})
                    SET ap.correct_code_snippet = $correct_code,
                        ap.times_prevented = ap.times_prevented + 1
                    RETURN ap.pattern_id as pid
                """, pattern_id=pattern_id, correct_code=correct_code[:500])

                record = result.single()
                if record:
                    self.logger.info(
                        f"📚 Learning loop closed: Updated pattern {pattern_id} "
                        f"with correct_code_snippet ({len(correct_code)} chars)"
                    )
                    return True
                else:
                    self.logger.warning(f"Pattern {pattern_id} not found in Neo4j")
                    return False

        except Exception as e:
            self.logger.warning(f"Failed to update correct_snippet: {e}")
            return False

    def find_pattern_by_error(
        self,
        error_type: str,
        exception_class: str,
        entity_name: str = "*",
        endpoint_pattern: str = "*"
    ) -> Optional[GenerationAntiPattern]:
        """
        Find a pattern matching an error signature.

        Bug #163 Fix: Used to look up existing patterns when a repair
        succeeds, so we can update them with the correct solution.

        Args:
            error_type: Type of error (database, validation, import, etc.)
            exception_class: Exception class name
            entity_name: Entity name or "*" for any
            endpoint_pattern: Endpoint pattern or "*" for any

        Returns:
            Matching pattern if found, None otherwise
        """
        pattern_id = generate_pattern_id(
            error_type=error_type,
            exception_class=exception_class,
            entity_pattern=entity_name,
            endpoint_pattern=endpoint_pattern,
        )

        return self.get(pattern_id)

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

        # Bug #4 Fix: Normalize entity name for case-insensitive matching
        entity_name_lower = entity_name.lower().strip()

        # Check cache first (case-insensitive)
        cached = [
            p for p in self._cache.values()
            if (p.entity_pattern.lower() == entity_name_lower or p.entity_pattern == "*")
            and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                # Bug #4 Fix: Use LOWER() for case-insensitive matching in Neo4j
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE (LOWER(ap.entity_pattern) = LOWER($entity_name) OR ap.entity_pattern = '*')
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
        # Bug #4 Fix: Normalize for case-insensitive matching
        entity_name_lower = entity_name.lower().strip()

        # Get patterns for validation errors (case-insensitive)
        cached = [
            p for p in self._cache.values()
            if p.error_type == "validation"
            and (p.entity_pattern.lower() == entity_name_lower or p.entity_pattern == "*")
            and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                # Bug #4 Fix: Use LOWER() for case-insensitive matching
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE ap.error_type = 'validation'
                      AND (LOWER(ap.entity_pattern) = LOWER($entity_name) OR ap.entity_pattern = '*')
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

    def get_patterns_by_exception(
        self,
        exception_class: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """
        Get all patterns matching a specific exception class.

        Bug #159 Fix: This method was missing, causing repair orchestrator to fail
        when looking up patterns by exception type (e.g., "IntegrityError", "KeyError").

        Args:
            exception_class: Exception class name (e.g., "IntegrityError", "ValidationError")
            min_occurrences: Minimum occurrence count (default: MIN_OCCURRENCE_FOR_PROMPT)

        Returns:
            List of patterns sorted by severity score
        """
        min_occ = min_occurrences or self.MIN_OCCURRENCE_FOR_PROMPT

        cached = [
            p for p in self._cache.values()
            if p.exception_class == exception_class and p.occurrence_count >= min_occ
        ]

        if not self._neo4j_available or not self.driver:
            return sorted(cached, key=lambda p: p.severity_score, reverse=True)

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (ap:GenerationAntiPattern)
                    WHERE ap.exception_class = $exception_class
                      AND ap.occurrence_count >= $min_occ
                    RETURN ap
                    ORDER BY ap.occurrence_count DESC
                    LIMIT $limit
                """, {
                    "exception_class": exception_class,
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
            self.logger.warning(f"Failed to query patterns by exception class: {e}")
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
    # IR-Centric Cognitive Code Generation Methods
    # Reference: COGNITIVE_CODE_GENERATION_PROPOSAL.md v2.0
    # =========================================================================

    def get_patterns_for_flow(
        self,
        flow_name: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """
        Get anti-patterns semantically matched to an IRFlow.

        This is the PRIMARY query method for IR-Centric Cognitive Code Generation.
        Matches patterns by flow name similarity, not file paths.

        Args:
            flow_name: Flow name (e.g., "add_item_to_cart", "checkout")
            min_occurrences: Minimum occurrence count (default: 1 for flow matching)

        Returns:
            List of patterns sorted by severity
        """
        min_occ = min_occurrences if min_occurrences is not None else 1

        # Normalize flow name for matching
        normalized_flow = flow_name.lower().replace("-", "_").replace(" ", "_")

        # Extract keywords from flow name for semantic matching
        flow_keywords = set(normalized_flow.split("_"))

        # Check cache with semantic matching
        cached = []
        for p in self._cache.values():
            if p.occurrence_count < min_occ:
                continue

            # Match by endpoint pattern (flows often map to endpoints)
            endpoint_match = False
            if p.endpoint_pattern and p.endpoint_pattern != "*":
                endpoint_normalized = p.endpoint_pattern.lower()
                # Check if flow keywords appear in endpoint
                endpoint_match = any(kw in endpoint_normalized for kw in flow_keywords if len(kw) > 2)

            # Match by entity pattern (flows involve entities)
            entity_match = False
            if p.entity_pattern and p.entity_pattern != "*":
                entity_normalized = p.entity_pattern.lower()
                entity_match = any(kw in entity_normalized for kw in flow_keywords if len(kw) > 2)

            # Match by error message pattern
            message_match = False
            if p.error_message_pattern:
                message_normalized = p.error_message_pattern.lower()
                message_match = any(kw in message_normalized for kw in flow_keywords if len(kw) > 3)

            if endpoint_match or entity_match or message_match:
                cached.append(p)

        # If Neo4j available, query for additional patterns
        if self._neo4j_available and self.driver:
            try:
                with self.driver.session() as session:
                    # Use regex matching for semantic search
                    keywords_pattern = "|".join(kw for kw in flow_keywords if len(kw) > 2)
                    if keywords_pattern:
                        result = session.run("""
                            MATCH (ap:GenerationAntiPattern)
                            WHERE ap.occurrence_count >= $min_occ
                              AND (
                                ap.endpoint_pattern =~ $pattern OR
                                ap.entity_pattern =~ $pattern OR
                                ap.error_message_pattern =~ $pattern
                              )
                            RETURN ap
                            ORDER BY ap.occurrence_count DESC
                            LIMIT $limit
                        """, {
                            "min_occ": min_occ,
                            "pattern": f"(?i).*({keywords_pattern}).*",
                            "limit": self.MAX_PATTERNS_PER_QUERY
                        })

                        for record in result:
                            pattern = self._node_to_pattern(record["ap"])
                            if pattern.pattern_id not in {p.pattern_id for p in cached}:
                                self._cache[pattern.pattern_id] = pattern
                                cached.append(pattern)

            except Exception as e:
                self.logger.debug(f"Neo4j flow query fell back to cache: {e}")

        return sorted(cached, key=lambda p: p.severity_score, reverse=True)[:self.MAX_PATTERNS_PER_QUERY]

    def get_patterns_for_constraint_type(
        self,
        constraint_type: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """
        Get anti-patterns related to a specific constraint type.

        Constraint types map to common error categories:
        - stock_constraint → IntegrityError, insufficient stock
        - workflow_constraint → state transition errors
        - uniqueness_constraint → duplicate key errors
        - foreign_key_constraint → referential integrity errors

        Args:
            constraint_type: Constraint type (e.g., "stock_constraint", "workflow_constraint")
            min_occurrences: Minimum occurrence count

        Returns:
            List of patterns sorted by severity
        """
        min_occ = min_occurrences if min_occurrences is not None else 1

        # Map constraint types to error patterns
        constraint_to_errors = {
            "stock_constraint": ["IntegrityError", "ValueError", "insufficient", "stock"],
            "workflow_constraint": ["InvalidStateError", "state", "transition", "status"],
            "uniqueness_constraint": ["IntegrityError", "UniqueViolation", "duplicate", "unique"],
            "foreign_key_constraint": ["IntegrityError", "ForeignKeyViolation", "foreign", "reference"],
            "validation_constraint": ["ValidationError", "TypeError", "invalid", "required"],
            "null_constraint": ["AttributeError", "NoneType", "null", "None"],
        }

        # Get keywords for this constraint type
        keywords = constraint_to_errors.get(
            constraint_type.lower(),
            constraint_type.lower().replace("_", " ").split()
        )

        # Check cache
        cached = []
        for p in self._cache.values():
            if p.occurrence_count < min_occ:
                continue

            # Match by exception class
            if p.exception_class in keywords:
                cached.append(p)
                continue

            # Match by error message pattern
            if p.error_message_pattern:
                msg_lower = p.error_message_pattern.lower()
                if any(kw.lower() in msg_lower for kw in keywords):
                    cached.append(p)

        return sorted(cached, key=lambda p: p.severity_score, reverse=True)[:self.MAX_PATTERNS_PER_QUERY]

    def store_cognitive_regression(
        self,
        regression: "CognitiveRegressionPattern"
    ) -> bool:
        """
        Store a cognitive regression pattern for learning.

        When IRCentricCognitivePass enhances code but the result fails
        IR validation, this method records the failure to avoid repeating it.

        Args:
            regression: The cognitive regression pattern to store

        Returns:
            True if stored successfully
        """
        # Store in memory cache
        if not hasattr(self, '_regression_cache'):
            self._regression_cache: Dict[str, CognitiveRegressionPattern] = {}

        self._regression_cache[regression.regression_id] = regression

        # Store in Neo4j if available
        if not self._neo4j_available or not self.driver:
            self.logger.debug(f"Stored cognitive regression in cache: {regression.regression_id}")
            return True

        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (cr:CognitiveRegression {regression_id: $regression_id})
                    ON CREATE SET
                        cr.ir_flow = $ir_flow,
                        cr.flow_id = $flow_id,
                        cr.anti_patterns_applied = $anti_patterns,
                        cr.result = $result,
                        cr.violations = $violations,
                        cr.file_path = $file_path,
                        cr.timestamp = datetime(),
                        cr.occurrence_count = 1
                    ON MATCH SET
                        cr.occurrence_count = cr.occurrence_count + 1,
                        cr.timestamp = datetime()
                """, {
                    "regression_id": regression.regression_id,
                    "ir_flow": regression.ir_flow,
                    "flow_id": regression.flow_id or "",
                    "anti_patterns": regression.anti_patterns_applied,
                    "result": regression.result,
                    "violations": regression.violations,
                    "file_path": regression.file_path or "",
                })

                self.logger.info(f"🧠 Stored cognitive regression: {regression.regression_id} for flow '{regression.ir_flow}'")
                return True

        except Exception as e:
            self.logger.warning(f"Failed to store cognitive regression in Neo4j: {e}")
            return True  # Still in cache

    def get_cognitive_regressions(
        self,
        flow_name: Optional[str] = None,
        limit: int = 50
    ) -> List["CognitiveRegressionPattern"]:
        """
        Get cognitive regression patterns, optionally filtered by flow.

        Args:
            flow_name: Optional flow name to filter by
            limit: Maximum patterns to return

        Returns:
            List of cognitive regression patterns
        """
        if not hasattr(self, '_regression_cache'):
            self._regression_cache = {}

        # Check cache first
        if flow_name:
            cached = [
                r for r in self._regression_cache.values()
                if r.ir_flow.lower() == flow_name.lower()
            ]
        else:
            cached = list(self._regression_cache.values())

        # Query Neo4j for additional patterns
        if self._neo4j_available and self.driver:
            try:
                with self.driver.session() as session:
                    if flow_name:
                        result = session.run("""
                            MATCH (cr:CognitiveRegression)
                            WHERE toLower(cr.ir_flow) = toLower($flow_name)
                            RETURN cr
                            ORDER BY cr.timestamp DESC
                            LIMIT $limit
                        """, {"flow_name": flow_name, "limit": limit})
                    else:
                        result = session.run("""
                            MATCH (cr:CognitiveRegression)
                            RETURN cr
                            ORDER BY cr.timestamp DESC
                            LIMIT $limit
                        """, {"limit": limit})

                    for record in result:
                        node = record["cr"]
                        reg = CognitiveRegressionPattern(
                            ir_flow=node.get("ir_flow", "unknown"),
                            flow_id=node.get("flow_id"),
                            anti_patterns_applied=node.get("anti_patterns_applied", []),
                            result=node.get("result", "unknown"),
                            violations=node.get("violations", []),
                            file_path=node.get("file_path"),
                            regression_id=node.get("regression_id"),
                        )
                        if reg.regression_id not in {r.regression_id for r in cached}:
                            cached.append(reg)

            except Exception as e:
                self.logger.debug(f"Neo4j regression query fell back to cache: {e}")

        return cached[:limit]

    def has_cognitive_regression(
        self,
        flow_name: str,
        anti_pattern_ids: List[str]
    ) -> bool:
        """
        Check if this combination of flow + anti-patterns has previously regressed.

        Used by IRCentricCognitivePass to avoid repeating failed enhancements.

        Args:
            flow_name: The flow name
            anti_pattern_ids: List of anti-pattern IDs being considered

        Returns:
            True if this combination has failed before
        """
        # Build regression ID to check
        key = f"{flow_name}:ir_contract_violation:{':'.join(sorted(anti_pattern_ids[:5]))}"
        check_id = f"crp_{hashlib.md5(key.encode()).hexdigest()[:12]}"

        # Check cache
        if hasattr(self, '_regression_cache') and check_id in self._regression_cache:
            return True

        # Check Neo4j
        if self._neo4j_available and self.driver:
            try:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (cr:CognitiveRegression {regression_id: $reg_id})
                        RETURN count(cr) > 0 AS exists
                    """, {"reg_id": check_id})
                    record = result.single()
                    return record["exists"] if record else False
            except Exception:
                pass

        return False

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

    # =========================================================================
    # Positive Repair Patterns (Phase 2.1 - LEARNING_INTEGRATION_GAPS)
    # =========================================================================

    def store_positive_repair(self, pattern: PositiveRepairPattern) -> bool:
        """
        Store a successful repair pattern for learning.

        LEARNING_GAPS Phase 2.1: When CodeRepairAgent fixes a compliance issue,
        this records the fix to guide future repairs.

        Uses domain-agnostic patterns (DevMatrix works with any spec domain).

        Args:
            pattern: The successful repair pattern to store

        Returns:
            True if stored successfully
        """
        # Store in memory cache
        if not hasattr(self, '_positive_cache'):
            self._positive_cache: Dict[str, PositiveRepairPattern] = {}

        # Update existing or add new
        if pattern.pattern_id in self._positive_cache:
            existing = self._positive_cache[pattern.pattern_id]
            existing.success_count += 1
            existing.last_applied = datetime.now()
        else:
            self._positive_cache[pattern.pattern_id] = pattern

        # Store in Neo4j if available
        if not self._neo4j_available or not self.driver:
            self.logger.debug(f"Stored positive repair in cache: {pattern.pattern_id}")
            return True

        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (pr:PositiveRepairPattern {pattern_id: $pattern_id})
                    ON CREATE SET
                        pr.repair_type = $repair_type,
                        pr.entity_pattern = $entity_pattern,
                        pr.endpoint_pattern = $endpoint_pattern,
                        pr.field_pattern = $field_pattern,
                        pr.fix_description = $fix_description,
                        pr.code_snippet = $code_snippet,
                        pr.file_path = $file_path,
                        pr.success_count = 1,
                        pr.created_at = datetime(),
                        pr.last_applied = datetime()
                    ON MATCH SET
                        pr.success_count = pr.success_count + 1,
                        pr.last_applied = datetime()
                """, {
                    "pattern_id": pattern.pattern_id,
                    "repair_type": pattern.repair_type,
                    "entity_pattern": pattern.entity_pattern,
                    "endpoint_pattern": pattern.endpoint_pattern,
                    "field_pattern": pattern.field_pattern,
                    "fix_description": pattern.fix_description,
                    "code_snippet": pattern.code_snippet[:500],  # Truncate
                    "file_path": pattern.file_path,
                })

                self.logger.debug(f"Stored positive repair: {pattern.pattern_id} ({pattern.repair_type})")
                return True

        except Exception as e:
            self.logger.warning(f"Failed to store positive repair in Neo4j: {e}")
            return True  # Still in cache

    def get_positive_repairs(
        self,
        repair_type: Optional[str] = None,
        limit: int = 20
    ) -> List[PositiveRepairPattern]:
        """
        Get positive repair patterns for prompt enhancement.

        LEARNING_GAPS Phase 2.1: Used by PromptEnhancer to inject successful
        repair examples into prompts.

        Args:
            repair_type: Optional filter by repair type
            limit: Maximum patterns to return

        Returns:
            List of successful repair patterns, sorted by reuse_score
        """
        if not hasattr(self, '_positive_cache'):
            self._positive_cache = {}

        # Get from cache
        if repair_type:
            cached = [
                p for p in self._positive_cache.values()
                if p.repair_type == repair_type
            ]
        else:
            cached = list(self._positive_cache.values())

        # Query Neo4j for additional patterns
        if self._neo4j_available and self.driver:
            try:
                with self.driver.session() as session:
                    if repair_type:
                        result = session.run("""
                            MATCH (pr:PositiveRepairPattern)
                            WHERE pr.repair_type = $repair_type
                            RETURN pr
                            ORDER BY pr.success_count DESC
                            LIMIT $limit
                        """, {"repair_type": repair_type, "limit": limit})
                    else:
                        result = session.run("""
                            MATCH (pr:PositiveRepairPattern)
                            RETURN pr
                            ORDER BY pr.success_count DESC
                            LIMIT $limit
                        """, {"limit": limit})

                    for record in result:
                        node = record["pr"]
                        pattern = self._node_to_positive_pattern(node)
                        if pattern.pattern_id not in {p.pattern_id for p in cached}:
                            cached.append(pattern)

            except Exception as e:
                self.logger.debug(f"Neo4j positive repair query fell back to cache: {e}")

        # Sort by reuse score and return
        return sorted(cached, key=lambda p: p.reuse_score, reverse=True)[:limit]

    def _node_to_positive_pattern(self, node) -> PositiveRepairPattern:
        """Convert Neo4j node to PositiveRepairPattern."""
        last_applied = node.get("last_applied")
        created_at = node.get("created_at")

        if hasattr(last_applied, "to_native"):
            last_applied = last_applied.to_native()
        elif last_applied is None:
            last_applied = datetime.now()

        if hasattr(created_at, "to_native"):
            created_at = created_at.to_native()
        elif created_at is None:
            created_at = datetime.now()

        return PositiveRepairPattern(
            pattern_id=node["pattern_id"],
            repair_type=node.get("repair_type", "unknown"),
            entity_pattern=node.get("entity_pattern", "*"),
            endpoint_pattern=node.get("endpoint_pattern", "*"),
            field_pattern=node.get("field_pattern", "*"),
            fix_description=node.get("fix_description", ""),
            code_snippet=node.get("code_snippet", ""),
            file_path=node.get("file_path", ""),
            success_count=node.get("success_count", 1),
            last_applied=last_applied,
            created_at=created_at,
        )


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
        # Bug #147 Fix: Load cached patterns on singleton creation
        _negative_pattern_store.load_cache()
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
