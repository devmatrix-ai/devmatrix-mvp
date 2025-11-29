"""
Validation Constraint Learning Service.

Gap 7 Implementation: Learns from constraint validation failures
to identify patterns in IR→Code transformations that lose constraints.

Reference: DOCS/mvp/exit/learning/LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 7
"""
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ConstraintViolation:
    """A single constraint violation record."""
    violation_id: str
    constraint_type: str  # "required", "type", "format", "enum", "range", "pattern"
    constraint_name: str
    entity_name: str
    field_name: str
    expected_value: str
    actual_value: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConstraintPattern:
    """Pattern of recurring constraint violations."""
    pattern_id: str
    constraint_type: str
    occurrence_count: int
    affected_entities: List[str]
    affected_fields: List[str]
    common_cause: str
    suggested_fix: str
    confidence: float = 0.5


@dataclass
class ConstraintLearningReport:
    """Report on constraint learning insights."""
    generated_at: datetime
    total_violations: int
    violations_by_type: Dict[str, int]
    violations_by_entity: Dict[str, int]
    patterns: List[ConstraintPattern]
    insights: List[str]
    recommendations: List[str]


# =============================================================================
# Constraint Learning Service
# =============================================================================

class ConstraintLearningService:
    """
    Learns from constraint validation failures.

    Gap 7 Implementation:
    - Logs detailed constraint violations
    - Categorizes violations by type and entity
    - Identifies recurring patterns
    - Suggests fixes based on historical data
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize service."""
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

        self.logger = logging.getLogger(f"{__name__}.ConstraintLearningService")

        # In-memory violation tracking
        self._violations: List[ConstraintViolation] = []
        self._violation_counts: Dict[str, int] = defaultdict(int)
        self._entity_violations: Dict[str, List[ConstraintViolation]] = defaultdict(list)

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def record_violation(
        self,
        constraint_type: str,
        constraint_name: str,
        entity_name: str,
        field_name: str,
        expected_value: Any,
        actual_value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintViolation:
        """
        Record a constraint violation for learning.

        Args:
            constraint_type: Type of constraint (required, type, format, etc.)
            constraint_name: Name of the constraint
            entity_name: Entity where violation occurred
            field_name: Field that violated constraint
            expected_value: What was expected
            actual_value: What was actually generated
            context: Additional context

        Returns:
            ConstraintViolation record
        """
        import uuid

        violation = ConstraintViolation(
            violation_id=f"cv_{uuid.uuid4().hex[:8]}",
            constraint_type=constraint_type.lower(),
            constraint_name=constraint_name,
            entity_name=entity_name,
            field_name=field_name,
            expected_value=str(expected_value)[:200],
            actual_value=str(actual_value)[:200],
            context=context or {},
            timestamp=datetime.now()
        )

        # Track in memory
        self._violations.append(violation)
        self._violation_counts[constraint_type] += 1
        self._entity_violations[entity_name].append(violation)

        # Persist to Neo4j
        self._persist_violation(violation)

        self.logger.debug(
            f"Recorded constraint violation: {constraint_type} on "
            f"{entity_name}.{field_name}"
        )

        return violation

    def record_batch_violations(
        self,
        violations: List[Dict[str, Any]]
    ) -> int:
        """
        Record multiple violations at once.

        Args:
            violations: List of violation dicts with keys:
                - constraint_type, constraint_name, entity_name,
                - field_name, expected_value, actual_value

        Returns:
            Number of violations recorded
        """
        count = 0
        for v in violations:
            try:
                self.record_violation(
                    constraint_type=v.get("constraint_type", "unknown"),
                    constraint_name=v.get("constraint_name", ""),
                    entity_name=v.get("entity_name", "unknown"),
                    field_name=v.get("field_name", ""),
                    expected_value=v.get("expected_value", ""),
                    actual_value=v.get("actual_value", ""),
                    context=v.get("context")
                )
                count += 1
            except Exception as e:
                self.logger.warning(f"Failed to record violation: {e}")

        self.logger.info(f"Recorded {count} constraint violations")
        return count

    def _persist_violation(self, violation: ConstraintViolation):
        """Persist violation to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (v:ConstraintViolation {
                        violation_id: $id,
                        constraint_type: $type,
                        constraint_name: $name,
                        entity_name: $entity,
                        field_name: $field,
                        expected_value: $expected,
                        actual_value: $actual,
                        created_at: datetime()
                    })
                """, {
                    "id": violation.violation_id,
                    "type": violation.constraint_type,
                    "name": violation.constraint_name,
                    "entity": violation.entity_name,
                    "field": violation.field_name,
                    "expected": violation.expected_value,
                    "actual": violation.actual_value
                })
        except Exception as e:
            self.logger.warning(f"Failed to persist violation: {e}")

    def identify_patterns(self) -> List[ConstraintPattern]:
        """
        Identify recurring violation patterns.

        Returns:
            List of identified patterns
        """
        patterns = []
        import uuid

        # Pattern 1: Same constraint type failing repeatedly
        for ctype, count in self._violation_counts.items():
            if count >= 3:
                violations = [v for v in self._violations if v.constraint_type == ctype]
                entities = list(set(v.entity_name for v in violations))
                fields = list(set(v.field_name for v in violations))

                cause, fix = self._suggest_fix_for_type(ctype, violations)

                patterns.append(ConstraintPattern(
                    pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                    constraint_type=ctype,
                    occurrence_count=count,
                    affected_entities=entities[:5],
                    affected_fields=fields[:5],
                    common_cause=cause,
                    suggested_fix=fix,
                    confidence=min(0.9, 0.5 + count * 0.1)
                ))

        # Pattern 2: Same entity failing multiple constraints
        for entity, violations in self._entity_violations.items():
            if len(violations) >= 3:
                types = list(set(v.constraint_type for v in violations))
                fields = list(set(v.field_name for v in violations))

                patterns.append(ConstraintPattern(
                    pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                    constraint_type="entity_multiple",
                    occurrence_count=len(violations),
                    affected_entities=[entity],
                    affected_fields=fields[:5],
                    common_cause=f"Entity '{entity}' has multiple constraint issues: {', '.join(types)}",
                    suggested_fix=f"Review entity template for '{entity}', check field definitions",
                    confidence=0.7
                ))

        # Pattern 3: Same field name across entities
        field_violations: Dict[str, List[ConstraintViolation]] = defaultdict(list)
        for v in self._violations:
            field_violations[v.field_name].append(v)

        for field, violations in field_violations.items():
            if len(violations) >= 3 and len(set(v.entity_name for v in violations)) > 1:
                entities = list(set(v.entity_name for v in violations))
                types = list(set(v.constraint_type for v in violations))

                patterns.append(ConstraintPattern(
                    pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                    constraint_type="field_pattern",
                    occurrence_count=len(violations),
                    affected_entities=entities[:5],
                    affected_fields=[field],
                    common_cause=f"Field '{field}' fails across multiple entities",
                    suggested_fix=f"Check common field template for '{field}' type handling",
                    confidence=0.75
                ))

        return sorted(patterns, key=lambda p: p.occurrence_count, reverse=True)

    def _suggest_fix_for_type(
        self,
        constraint_type: str,
        violations: List[ConstraintViolation]
    ) -> tuple:
        """Suggest fix based on constraint type."""
        fixes = {
            "required": (
                "Required field missing in generated code",
                "Add field to entity model, ensure not nullable"
            ),
            "type": (
                "Type mismatch between IR and generated code",
                "Review type mapping in code generator"
            ),
            "format": (
                "Format constraint not enforced",
                "Add format validation in schema/model"
            ),
            "enum": (
                "Enum values not properly generated",
                "Ensure enum definition is created before entity"
            ),
            "range": (
                "Numeric range not validated",
                "Add min/max validators to field"
            ),
            "pattern": (
                "String pattern not enforced",
                "Add regex validation to field"
            ),
            "relationship": (
                "Relationship constraint violated",
                "Review foreign key and join definitions"
            ),
        }

        return fixes.get(constraint_type, (
            f"Unknown constraint type: {constraint_type}",
            "Review constraint definition and code generation"
        ))

    def generate_report(self) -> ConstraintLearningReport:
        """
        Generate comprehensive learning report.

        Returns:
            ConstraintLearningReport with analysis
        """
        patterns = self.identify_patterns()

        # Generate insights
        insights = []

        if self._violations:
            # Most common type
            if self._violation_counts:
                most_common = max(self._violation_counts.items(), key=lambda x: x[1])
                insights.append(
                    f"Most common violation: '{most_common[0]}' ({most_common[1]} occurrences)"
                )

            # Most problematic entity
            if self._entity_violations:
                worst_entity = max(
                    self._entity_violations.items(),
                    key=lambda x: len(x[1])
                )
                insights.append(
                    f"Most problematic entity: '{worst_entity[0]}' ({len(worst_entity[1])} violations)"
                )

            # Pattern count
            if patterns:
                insights.append(f"Identified {len(patterns)} recurring patterns")

        # Generate recommendations
        recommendations = []
        for pattern in patterns[:3]:  # Top 3 patterns
            recommendations.append(f"[{pattern.constraint_type}] {pattern.suggested_fix}")

        if not recommendations:
            recommendations.append("No critical patterns - constraint compliance is acceptable")

        return ConstraintLearningReport(
            generated_at=datetime.now(),
            total_violations=len(self._violations),
            violations_by_type=dict(self._violation_counts),
            violations_by_entity={k: len(v) for k, v in self._entity_violations.items()},
            patterns=patterns,
            insights=insights,
            recommendations=recommendations
        )

    def get_entity_violations(self, entity_name: str) -> List[ConstraintViolation]:
        """Get all violations for a specific entity."""
        return self._entity_violations.get(entity_name, [])

    def get_violations_by_type(self, constraint_type: str) -> List[ConstraintViolation]:
        """Get all violations of a specific type."""
        return [v for v in self._violations if v.constraint_type == constraint_type]

    def get_statistics(self) -> Dict[str, Any]:
        """Get violation statistics."""
        if not self._violations:
            return {"total_violations": 0}

        return {
            "total_violations": len(self._violations),
            "unique_types": len(self._violation_counts),
            "unique_entities": len(self._entity_violations),
            "violations_by_type": dict(self._violation_counts),
            "top_entities": sorted(
                [(k, len(v)) for k, v in self._entity_violations.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def load_historical_violations(self, limit: int = 100) -> int:
        """
        Load historical violations from Neo4j.

        Args:
            limit: Maximum violations to load

        Returns:
            Number of violations loaded
        """
        if not self._neo4j_available or not self.driver:
            return 0

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (v:ConstraintViolation)
                    RETURN v
                    ORDER BY v.created_at DESC
                    LIMIT $limit
                """, limit=limit)

                count = 0
                for record in result:
                    v = record["v"]
                    violation = ConstraintViolation(
                        violation_id=v["violation_id"],
                        constraint_type=v["constraint_type"],
                        constraint_name=v.get("constraint_name", ""),
                        entity_name=v["entity_name"],
                        field_name=v["field_name"],
                        expected_value=v.get("expected_value", ""),
                        actual_value=v.get("actual_value", "")
                    )
                    self._violations.append(violation)
                    self._violation_counts[violation.constraint_type] += 1
                    self._entity_violations[violation.entity_name].append(violation)
                    count += 1

                self.logger.info(f"Loaded {count} historical violations")
                return count

        except Exception as e:
            self.logger.error(f"Failed to load historical violations: {e}")
            return 0

    def clear_violations(self):
        """Clear in-memory violations (for testing)."""
        self._violations = []
        self._violation_counts = defaultdict(int)
        self._entity_violations = defaultdict(list)


# =============================================================================
# Singleton Instance
# =============================================================================

_constraint_service: Optional[ConstraintLearningService] = None


def get_constraint_learning_service() -> ConstraintLearningService:
    """Get singleton instance of ConstraintLearningService."""
    global _constraint_service
    if _constraint_service is None:
        import os
        _constraint_service = ConstraintLearningService(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _constraint_service
