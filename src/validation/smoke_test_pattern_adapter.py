"""
Smoke Test Pattern Adapter - Maps Smoke Results to Pattern Feedback.

Bridges the gap between smoke test results and the pattern promotion system.
Creates LearningEvents that update pattern scores based on test outcomes.

Reference: LEARNING_GAPS_IMPLEMENTATION_PLAN.md - SmokeTest→Pattern Integration
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

class LearningEventType(str, Enum):
    """Type of learning event."""
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class LearningEvent:
    """
    Learning event for pattern score updates.

    Generated from smoke test results to provide feedback to the pattern system.
    """
    event_id: str
    event_type: LearningEventType
    weight: float  # +1.0 for positive, -1.0 for negative
    source: str  # "smoke_test", "validation", "repair"

    # Context
    endpoint: str
    method: str
    pattern_ids: List[str]  # Pattern IDs affected by this event
    category: str  # "routes", "services", "models", "schemas"

    # Error details (for negative events)
    error_signature: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    app_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternScoreUpdate:
    """Update to apply to a pattern's score."""
    pattern_id: str
    category: str
    delta_success: int  # +1 or 0
    delta_failure: int  # +1 or 0
    new_score: float
    event_source: str


@dataclass
class ScoreUpdateSummary:
    """Summary of pattern score updates."""
    total_patterns_updated: int
    positive_events: int
    negative_events: int
    avg_score: float
    promoted_count: int
    demoted_count: int
    patterns_by_category: Dict[str, int]


# =============================================================================
# Smoke Test Pattern Adapter
# =============================================================================

class SmokeTestPatternAdapter:
    """
    Adapts smoke test results to pattern learning events.

    Responsibilities:
    1. Map smoke test scenarios to pattern categories
    2. Create LearningEvents from pass/fail results
    3. Update pattern scores in Phase 10
    4. Generate explicit logs of score updates
    """

    # Category mappings from endpoint patterns
    CATEGORY_PATTERNS = {
        "routes": [r"/routes/", r"_routes\.py", r"router"],
        "services": [r"/services/", r"_service\.py", r"Service"],
        "models": [r"/models/", r"entities\.py", r"Entity"],
        "schemas": [r"/schemas/", r"schema\.py", r"Schema"],
        "repositories": [r"/repositories/", r"_repository\.py", r"Repository"],
    }

    # Default weights
    POSITIVE_WEIGHT = 1.0
    NEGATIVE_WEIGHT = -1.0
    PROMOTION_THRESHOLD = 0.7
    DEMOTION_THRESHOLD = 0.3

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize adapter."""
        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            self._neo4j_available = True
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")
            self._neo4j_available = False
            self.driver = None

        self.logger = logging.getLogger(f"{__name__}.SmokeTestPatternAdapter")

        # In-memory tracking
        self._events: List[LearningEvent] = []
        self._score_updates: List[PatternScoreUpdate] = []
        self._pattern_scores: Dict[str, Dict[str, Any]] = {}

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def process_smoke_results(
        self,
        smoke_result: Dict[str, Any],
        generation_manifest: Dict[str, Any],
        app_id: Optional[str] = None
    ) -> List[LearningEvent]:
        """
        Process smoke test results and generate learning events.

        Args:
            smoke_result: Dict with 'violations' and 'passed_scenarios'
            generation_manifest: Dict from GenerationManifest.to_dict()
            app_id: Application identifier

        Returns:
            List of LearningEvents generated
        """
        import uuid
        events = []

        # Get file-to-atom mappings from manifest
        file_atoms = self._extract_file_atoms(generation_manifest)

        # Process passed scenarios (positive feedback)
        passed = smoke_result.get("passed_scenarios", [])
        for scenario in passed:
            endpoint = scenario.get("endpoint", scenario.get("path", ""))
            method = scenario.get("method", "GET")

            # Find pattern IDs for this endpoint
            pattern_ids = self._find_patterns_for_endpoint(endpoint, method, file_atoms)
            category = self._categorize_endpoint(endpoint)

            if pattern_ids:
                event = LearningEvent(
                    event_id=f"le_{uuid.uuid4().hex[:8]}",
                    event_type=LearningEventType.POSITIVE,
                    weight=self.POSITIVE_WEIGHT,
                    source="smoke_test",
                    endpoint=endpoint,
                    method=method,
                    pattern_ids=pattern_ids,
                    category=category,
                    app_id=app_id
                )
                events.append(event)
                self._events.append(event)

        # Process violations (negative feedback)
        violations = smoke_result.get("violations", [])
        for violation in violations:
            endpoint = violation.get("endpoint", violation.get("path", ""))
            method = violation.get("method", "GET")

            pattern_ids = self._find_patterns_for_endpoint(endpoint, method, file_atoms)
            category = self._categorize_endpoint(endpoint)

            if pattern_ids:
                event = LearningEvent(
                    event_id=f"le_{uuid.uuid4().hex[:8]}",
                    event_type=LearningEventType.NEGATIVE,
                    weight=self.NEGATIVE_WEIGHT,
                    source="smoke_test",
                    endpoint=endpoint,
                    method=method,
                    pattern_ids=pattern_ids,
                    category=category,
                    error_signature=violation.get("error_signature"),
                    error_type=violation.get("error_type", violation.get("type")),
                    error_message=str(violation.get("error", violation.get("message", "")))[:500],
                    status_code=violation.get("status_code"),
                    app_id=app_id
                )
                events.append(event)
                self._events.append(event)

        self.logger.info(
            f"Generated {len(events)} learning events: "
            f"{sum(1 for e in events if e.event_type == LearningEventType.POSITIVE)} positive, "
            f"{sum(1 for e in events if e.event_type == LearningEventType.NEGATIVE)} negative"
        )

        return events

    def _extract_file_atoms(self, manifest: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract file-to-atoms mapping from manifest."""
        file_atoms = {}
        files = manifest.get("files", {})

        for file_path, file_data in files.items():
            atoms = file_data.get("atoms", [])
            if atoms:
                file_atoms[file_path] = atoms

        return file_atoms

    def _find_patterns_for_endpoint(
        self,
        endpoint: str,
        method: str,
        file_atoms: Dict[str, List[str]]
    ) -> List[str]:
        """
        Find pattern IDs related to an endpoint.

        Strategy:
        1. Extract entity from endpoint path (e.g., /products → Product)
        2. Find atoms matching that entity
        3. Return pattern IDs from matching atoms
        """
        pattern_ids = []

        # Extract entity name from endpoint
        entity_name = self._extract_entity_from_endpoint(endpoint)

        if entity_name:
            entity_lower = entity_name.lower()

            for file_path, atoms in file_atoms.items():
                for atom in atoms:
                    # Check if atom relates to this entity
                    # Atoms look like: "entity:Product", "service:ProductService", "route:products"
                    atom_lower = atom.lower()
                    if entity_lower in atom_lower:
                        # Create pattern ID from atom
                        pattern_id = f"pat_{atom.replace(':', '_')}"
                        if pattern_id not in pattern_ids:
                            pattern_ids.append(pattern_id)

        # Also add category-based pattern
        category = self._categorize_endpoint(endpoint)
        category_pattern = f"pat_{category}_{entity_name or 'general'}"
        if category_pattern not in pattern_ids:
            pattern_ids.append(category_pattern)

        return pattern_ids[:5]  # Limit to 5 patterns

    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # /products → Product
        # /products/{id} → Product
        # /users/{user_id}/orders → User, Order

        parts = endpoint.strip("/").split("/")
        if parts:
            # First meaningful part is usually the entity
            entity_part = parts[0]
            # Remove parameter placeholders
            if not entity_part.startswith("{"):
                # Singularize and capitalize
                entity = entity_part.rstrip("s").title()
                return entity

        return None

    def _categorize_endpoint(self, endpoint: str) -> str:
        """Categorize endpoint by type."""
        endpoint_lower = endpoint.lower()

        if "/health" in endpoint_lower:
            return "health"

        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, endpoint_lower):
                    return category

        # Default based on HTTP semantics
        return "routes"

    def update_pattern_scores(self) -> ScoreUpdateSummary:
        """
        Update pattern scores based on accumulated learning events.

        Returns:
            ScoreUpdateSummary with update statistics
        """
        if not self._events:
            return ScoreUpdateSummary(
                total_patterns_updated=0,
                positive_events=0,
                negative_events=0,
                avg_score=0.0,
                promoted_count=0,
                demoted_count=0,
                patterns_by_category={}
            )

        # Group events by pattern
        pattern_events: Dict[str, List[LearningEvent]] = {}
        for event in self._events:
            for pattern_id in event.pattern_ids:
                if pattern_id not in pattern_events:
                    pattern_events[pattern_id] = []
                pattern_events[pattern_id].append(event)

        # Update scores
        updates = []
        promoted = 0
        demoted = 0
        category_counts: Dict[str, int] = {}

        for pattern_id, events in pattern_events.items():
            positive_count = sum(1 for e in events if e.event_type == LearningEventType.POSITIVE)
            negative_count = sum(1 for e in events if e.event_type == LearningEventType.NEGATIVE)
            total = positive_count + negative_count

            # Calculate new score
            if total > 0:
                new_score = positive_count / total
            else:
                new_score = 0.5  # Neutral

            # Get current score
            current = self._pattern_scores.get(pattern_id, {})
            old_score = current.get("score", 0.5)
            old_success = current.get("success_count", 0)
            old_failure = current.get("failure_count", 0)

            # Apply exponential moving average
            alpha = 0.3  # Learning rate
            final_score = alpha * new_score + (1 - alpha) * old_score

            # Track promotion/demotion
            if final_score >= self.PROMOTION_THRESHOLD and old_score < self.PROMOTION_THRESHOLD:
                promoted += 1
            elif final_score < self.DEMOTION_THRESHOLD and old_score >= self.DEMOTION_THRESHOLD:
                demoted += 1

            # Update stored score
            self._pattern_scores[pattern_id] = {
                "score": final_score,
                "success_count": old_success + positive_count,
                "failure_count": old_failure + negative_count,
                "last_seen": datetime.now()
            }

            # Track category
            category = events[0].category if events else "unknown"
            category_counts[category] = category_counts.get(category, 0) + 1

            update = PatternScoreUpdate(
                pattern_id=pattern_id,
                category=category,
                delta_success=positive_count,
                delta_failure=negative_count,
                new_score=final_score,
                event_source="smoke_test"
            )
            updates.append(update)
            self._score_updates.append(update)

        # Persist to Neo4j
        self._persist_score_updates(updates)

        # Calculate summary
        total_updated = len(updates)
        avg_score = sum(u.new_score for u in updates) / total_updated if total_updated else 0

        positive_events = sum(1 for e in self._events if e.event_type == LearningEventType.POSITIVE)
        negative_events = sum(1 for e in self._events if e.event_type == LearningEventType.NEGATIVE)

        summary = ScoreUpdateSummary(
            total_patterns_updated=total_updated,
            positive_events=positive_events,
            negative_events=negative_events,
            avg_score=avg_score,
            promoted_count=promoted,
            demoted_count=demoted,
            patterns_by_category=category_counts
        )

        # Log explicit update message
        self._log_score_updates(summary)

        # Clear processed events
        self._events = []

        return summary

    def _persist_score_updates(self, updates: List[PatternScoreUpdate]):
        """Persist score updates to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                for update in updates:
                    session.run("""
                        MERGE (p:PatternScore {pattern_id: $pattern_id})
                        ON CREATE SET
                            p.category = $category,
                            p.success_count = $success,
                            p.failure_count = $failure,
                            p.score = $score,
                            p.created_at = datetime(),
                            p.last_seen = datetime()
                        ON MATCH SET
                            p.success_count = p.success_count + $success,
                            p.failure_count = p.failure_count + $failure,
                            p.score = $score,
                            p.last_seen = datetime()
                    """, {
                        "pattern_id": update.pattern_id,
                        "category": update.category,
                        "success": update.delta_success,
                        "failure": update.delta_failure,
                        "score": update.new_score
                    })

                self.logger.debug(f"Persisted {len(updates)} pattern score updates")

        except Exception as e:
            self.logger.warning(f"Failed to persist score updates: {e}")

    def _log_score_updates(self, summary: ScoreUpdateSummary):
        """Log explicit score update message."""
        if summary.total_patterns_updated == 0:
            self.logger.info("📊 No pattern scores to update")
            return

        # Format category breakdown
        category_str = ", ".join(
            f"{cat}: {count}"
            for cat, count in sorted(summary.patterns_by_category.items())
        )

        msg = (
            f"📊 Updated pattern scores: {summary.total_patterns_updated} patterns "
            f"(avg score {summary.avg_score:.2f}, "
            f"promoted: {summary.promoted_count}, demoted: {summary.demoted_count})"
        )

        if category_str:
            msg += f"\n   Categories: {category_str}"

        msg += f"\n   Events: +{summary.positive_events} positive, -{summary.negative_events} negative"

        self.logger.info(msg)
        print(msg)  # Also print to console for visibility

    def get_pattern_scores(self) -> Dict[str, Dict[str, Any]]:
        """Get current pattern scores."""
        return self._pattern_scores.copy()

    def get_promotable_patterns(self) -> List[str]:
        """Get patterns above promotion threshold."""
        return [
            pid for pid, data in self._pattern_scores.items()
            if data.get("score", 0) >= self.PROMOTION_THRESHOLD
        ]

    def get_events_summary(self) -> Dict[str, Any]:
        """Get summary of pending events."""
        return {
            "total_events": len(self._events),
            "positive_events": sum(1 for e in self._events if e.event_type == LearningEventType.POSITIVE),
            "negative_events": sum(1 for e in self._events if e.event_type == LearningEventType.NEGATIVE),
            "unique_patterns": len(set(
                pid for e in self._events for pid in e.pattern_ids
            ))
        }

    def load_historical_scores(self, limit: int = 100) -> int:
        """Load historical pattern scores from Neo4j."""
        if not self._neo4j_available or not self.driver:
            return 0

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:PatternScore)
                    RETURN p
                    ORDER BY p.last_seen DESC
                    LIMIT $limit
                """, limit=limit)

                count = 0
                for record in result:
                    p = record["p"]
                    self._pattern_scores[p["pattern_id"]] = {
                        "score": p.get("score", 0.5),
                        "success_count": p.get("success_count", 0),
                        "failure_count": p.get("failure_count", 0),
                        "category": p.get("category", "unknown")
                    }
                    count += 1

                self.logger.info(f"Loaded {count} historical pattern scores")
                return count

        except Exception as e:
            self.logger.error(f"Failed to load historical scores: {e}")
            return 0


# =============================================================================
# Fix Pattern Learning
# =============================================================================

@dataclass
class FixPattern:
    """
    A learned fix pattern from smoke-driven repair.

    Captures successful repair strategies that can be reused for similar failures.
    """
    pattern_id: str
    error_type: str           # "database", "validation", "import", etc.
    endpoint_pattern: str     # "POST /entities", "PUT /entities/{id}"
    exception_class: str      # "IntegrityError", "ValidationError"
    fix_type: str             # "add_nullable", "fix_import", "add_validator"
    fix_template: str         # Description or code template

    # Success tracking
    success_count: int = 0
    failure_count: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def total_attempts(self) -> int:
        """Total number of repair attempts."""
        return self.success_count + self.failure_count


@dataclass
class RepairAttemptRecord:
    """Record of a repair attempt for learning."""
    violation_endpoint: str
    error_type: str
    exception_class: str
    fix_type: str
    fix_description: str
    success: bool
    iteration: int
    timestamp: datetime = field(default_factory=datetime.now)


class FixPatternLearner:
    """
    Learns and queries fix patterns from repair history.

    Capabilities:
    - Record fix attempts and outcomes
    - Query known fixes for similar errors
    - Promote high-success patterns
    - Demote low-success patterns
    """

    MIN_SUCCESS_RATE = 0.7    # Minimum success rate to recommend
    MIN_SUCCESS_COUNT = 3     # Minimum successful uses to recommend

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize learner."""
        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            self._neo4j_available = True
        except Exception as e:
            logger.warning(f"Neo4j not available for FixPatternLearner: {e}")
            self._neo4j_available = False
            self.driver = None

        self.logger = logging.getLogger(f"{__name__}.FixPatternLearner")

        # In-memory cache
        self._patterns: Dict[str, FixPattern] = {}
        self._attempt_records: List[RepairAttemptRecord] = []

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def record_repair_attempt(
        self,
        violations: List[Dict[str, Any]],
        repairs: List[Any],
        success: bool,
        iteration: int = 1
    ) -> int:
        """
        Record repair attempts for learning.

        Args:
            violations: List of violations that triggered repair
            repairs: List of repair descriptions applied
            success: Whether the repair improved pass rate
            iteration: Current iteration in repair loop

        Returns:
            Number of patterns updated
        """
        import uuid
        patterns_updated = 0

        for violation in violations:
            endpoint = violation.get("endpoint", violation.get("path", "unknown"))
            error_type = violation.get("error_type", "unknown")
            exception_class = violation.get("exception_class",
                                           violation.get("error", ""))

            # Extract exception class from error message if needed
            if not exception_class or exception_class == "unknown":
                error_msg = str(violation.get("error_message", ""))
                exception_class = self._extract_exception_class(error_msg)

            for repair in repairs:
                repair_desc = repair.get("description") if isinstance(repair, dict) else str(repair)
                fix_type = repair.get("fix_type") if isinstance(repair, dict) else None
                fix_type = fix_type or self._classify_fix_type(repair_desc)

                # Record attempt
                record = RepairAttemptRecord(
                    violation_endpoint=endpoint,
                    error_type=error_type,
                    exception_class=exception_class,
                    fix_type=fix_type,
                    fix_description=repair_desc,
                    success=success,
                    iteration=iteration
                )
                self._attempt_records.append(record)

                # Create/update pattern
                pattern_id = self._generate_pattern_id(
                    error_type, endpoint, exception_class, fix_type
                )

                if pattern_id in self._patterns:
                    pattern = self._patterns[pattern_id]
                else:
                    pattern = FixPattern(
                        pattern_id=pattern_id,
                        error_type=error_type,
                        endpoint_pattern=self._generalize_endpoint(endpoint),
                        exception_class=exception_class,
                        fix_type=fix_type,
                        fix_template=repair
                    )
                    self._patterns[pattern_id] = pattern

                # Update counts
                if success:
                    pattern.success_count += 1
                else:
                    pattern.failure_count += 1
                pattern.last_used = datetime.now()

                patterns_updated += 1

        # Persist to Neo4j
        self._persist_patterns()

        self.logger.info(
            f"Recorded {len(violations)} violations × {len(repairs)} repairs "
            f"= {patterns_updated} pattern updates (success={success})"
        )

        return patterns_updated

    def get_known_fix(
        self,
        error_type: str,
        endpoint: str,
        exception_class: str
    ) -> Optional[FixPattern]:
        """
        Query for known fix pattern with high success rate.

        Returns pattern if:
        - Matches error signature
        - success_rate >= 0.7
        - success_count >= 3 (enough evidence)

        Args:
            error_type: Type of error (database, validation, etc.)
            endpoint: Failing endpoint
            exception_class: Exception class name

        Returns:
            Best matching FixPattern or None
        """
        endpoint_pattern = self._generalize_endpoint(endpoint)

        # Try exact match first
        candidates = [
            p for p in self._patterns.values()
            if p.error_type == error_type
            and p.exception_class == exception_class
            and p.endpoint_pattern == endpoint_pattern
            and p.success_rate >= self.MIN_SUCCESS_RATE
            and p.success_count >= self.MIN_SUCCESS_COUNT
        ]

        if candidates:
            # Return highest success rate
            return max(candidates, key=lambda p: p.success_rate)

        # Try partial match (same error_type and exception)
        candidates = [
            p for p in self._patterns.values()
            if p.error_type == error_type
            and p.exception_class == exception_class
            and p.success_rate >= self.MIN_SUCCESS_RATE
            and p.success_count >= self.MIN_SUCCESS_COUNT
        ]

        if candidates:
            return max(candidates, key=lambda p: p.success_rate)

        # Query Neo4j for historical patterns
        return self._query_neo4j_pattern(error_type, endpoint_pattern, exception_class)

    def get_successful_fixes(
        self,
        min_success_rate: float = 0.7,
        limit: int = 10
    ) -> List[FixPattern]:
        """Get top successful fix patterns."""
        patterns = [
            p for p in self._patterns.values()
            if p.success_rate >= min_success_rate
            and p.success_count >= self.MIN_SUCCESS_COUNT
        ]
        return sorted(patterns, key=lambda p: p.success_rate, reverse=True)[:limit]

    def _generate_pattern_id(
        self,
        error_type: str,
        endpoint: str,
        exception_class: str,
        fix_type: str
    ) -> str:
        """Generate unique pattern ID."""
        import hashlib
        key = f"{error_type}:{endpoint}:{exception_class}:{fix_type}"
        return f"fix_{hashlib.md5(key.encode()).hexdigest()[:12]}"

    def _generalize_endpoint(self, endpoint: str) -> str:
        """Generalize endpoint to pattern."""
        # /products/123 → /products/{id}
        # /users/456/orders/789 → /users/{id}/orders/{id}
        import re
        pattern = re.sub(r'/\d+', '/{id}', endpoint)
        pattern = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                        '/{id}', pattern, flags=re.IGNORECASE)
        return pattern

    def _extract_exception_class(self, error_message: str) -> str:
        """Extract exception class from error message."""
        import re
        # Common patterns: "IntegrityError: ...", "ValidationError: ..."
        match = re.search(r'(\w+Error|\w+Exception):', error_message)
        if match:
            return match.group(1)
        return "Unknown"

    def _classify_fix_type(self, repair_description: str) -> str:
        """Classify fix type from repair description."""
        desc_lower = repair_description.lower() if repair_description else ""

        if "nullable" in desc_lower or "optional" in desc_lower:
            return "add_nullable"
        elif "import" in desc_lower or "missing module" in desc_lower:
            return "fix_import"
        elif "validator" in desc_lower or "validation" in desc_lower:
            return "add_validator"
        elif "foreign key" in desc_lower or "relationship" in desc_lower:
            return "fix_foreign_key"
        elif "route" in desc_lower or "endpoint" in desc_lower:
            return "fix_route"
        elif "type" in desc_lower or "cast" in desc_lower:
            return "fix_type"
        elif "default" in desc_lower:
            return "add_default"
        else:
            return "generic_fix"

    def _persist_patterns(self):
        """Persist patterns to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                for pattern in self._patterns.values():
                    session.run("""
                        MERGE (fp:FixPattern {pattern_id: $pattern_id})
                        ON CREATE SET
                            fp.error_type = $error_type,
                            fp.endpoint_pattern = $endpoint_pattern,
                            fp.exception_class = $exception_class,
                            fp.fix_type = $fix_type,
                            fp.fix_template = $fix_template,
                            fp.success_count = $success_count,
                            fp.failure_count = $failure_count,
                            fp.created_at = datetime()
                        ON MATCH SET
                            fp.success_count = $success_count,
                            fp.failure_count = $failure_count,
                            fp.fix_template = $fix_template,
                            fp.last_used = datetime()
                    """, {
                        "pattern_id": pattern.pattern_id,
                        "error_type": pattern.error_type,
                        "endpoint_pattern": pattern.endpoint_pattern,
                        "exception_class": pattern.exception_class,
                        "fix_type": pattern.fix_type,
                        "fix_template": pattern.fix_template[:500],
                        "success_count": pattern.success_count,
                        "failure_count": pattern.failure_count
                    })

                self.logger.debug(f"Persisted {len(self._patterns)} fix patterns")

        except Exception as e:
            self.logger.warning(f"Failed to persist fix patterns: {e}")

    def _query_neo4j_pattern(
        self,
        error_type: str,
        endpoint_pattern: str,
        exception_class: str
    ) -> Optional[FixPattern]:
        """Query Neo4j for matching fix pattern."""
        if not self._neo4j_available or not self.driver:
            return None

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (fp:FixPattern)
                    WHERE fp.error_type = $error_type
                      AND fp.exception_class = $exception_class
                      AND (fp.success_count * 1.0) /
                          (fp.success_count + fp.failure_count) >= 0.7
                      AND fp.success_count >= 3
                    RETURN fp
                    ORDER BY (fp.success_count * 1.0) /
                             (fp.success_count + fp.failure_count) DESC
                    LIMIT 1
                """, {
                    "error_type": error_type,
                    "exception_class": exception_class
                })

                record = result.single()
                if record:
                    fp = record["fp"]
                    pattern = FixPattern(
                        pattern_id=fp["pattern_id"],
                        error_type=fp["error_type"],
                        endpoint_pattern=fp["endpoint_pattern"],
                        exception_class=fp["exception_class"],
                        fix_type=fp["fix_type"],
                        fix_template=fp.get("fix_template", ""),
                        success_count=fp["success_count"],
                        failure_count=fp["failure_count"]
                    )
                    # Cache it
                    self._patterns[pattern.pattern_id] = pattern
                    return pattern

        except Exception as e:
            self.logger.warning(f"Failed to query fix patterns: {e}")

        return None

    def load_historical_patterns(self, limit: int = 100) -> int:
        """Load historical fix patterns from Neo4j."""
        if not self._neo4j_available or not self.driver:
            return 0

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (fp:FixPattern)
                    RETURN fp
                    ORDER BY fp.success_count DESC
                    LIMIT $limit
                """, limit=limit)

                count = 0
                for record in result:
                    fp = record["fp"]
                    pattern = FixPattern(
                        pattern_id=fp["pattern_id"],
                        error_type=fp["error_type"],
                        endpoint_pattern=fp["endpoint_pattern"],
                        exception_class=fp["exception_class"],
                        fix_type=fp["fix_type"],
                        fix_template=fp.get("fix_template", ""),
                        success_count=fp["success_count"],
                        failure_count=fp["failure_count"]
                    )
                    self._patterns[pattern.pattern_id] = pattern
                    count += 1

                self.logger.info(f"Loaded {count} historical fix patterns")
                return count

        except Exception as e:
            self.logger.error(f"Failed to load fix patterns: {e}")
            return 0


# =============================================================================
# Singleton Instance
# =============================================================================

_smoke_pattern_adapter: Optional[SmokeTestPatternAdapter] = None
_fix_pattern_learner: Optional[FixPatternLearner] = None


def get_smoke_pattern_adapter() -> SmokeTestPatternAdapter:
    """Get singleton instance of SmokeTestPatternAdapter."""
    global _smoke_pattern_adapter
    if _smoke_pattern_adapter is None:
        import os
        _smoke_pattern_adapter = SmokeTestPatternAdapter(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _smoke_pattern_adapter


def get_fix_pattern_learner() -> FixPatternLearner:
    """Get singleton instance of FixPatternLearner."""
    global _fix_pattern_learner
    if _fix_pattern_learner is None:
        import os
        _fix_pattern_learner = FixPatternLearner(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _fix_pattern_learner


# =============================================================================
# Convenience Functions
# =============================================================================

def process_smoke_results_to_patterns(
    smoke_result: Dict[str, Any],
    generation_manifest: Dict[str, Any],
    app_id: Optional[str] = None
) -> ScoreUpdateSummary:
    """
    Convenience function to process smoke results and update patterns.

    Usage in Phase 10:
        from src.validation.smoke_test_pattern_adapter import process_smoke_results_to_patterns

        summary = process_smoke_results_to_patterns(
            smoke_result=smoke_validator.result,
            generation_manifest=manifest.to_dict(),
            app_id=app_id
        )
        # Output: "Updated pattern scores: 27 patterns (avg score 0.63, promoted: 3)"

    Args:
        smoke_result: Dict with violations and passed_scenarios
        generation_manifest: Generation manifest dict
        app_id: Application ID

    Returns:
        ScoreUpdateSummary with statistics
    """
    adapter = get_smoke_pattern_adapter()
    adapter.process_smoke_results(smoke_result, generation_manifest, app_id)
    return adapter.update_pattern_scores()
