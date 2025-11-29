"""
Pattern Mining Service for Neo4j Graph Analysis.

Gap 3 Implementation: Mines patterns from Neo4j graph to extract
learning insights from ApplicationIR, generations, and test results.

Reference: DOCS/mvp/exit/learning/LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 3
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes for Mining Results
# =============================================================================

@dataclass
class FailurePattern:
    """Pattern representing a consistently failing endpoint or entity."""
    element_type: str  # "endpoint", "entity", "service"
    element_name: str
    failure_count: int
    error_types: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuccessPattern:
    """Pattern representing consistently successful code generation."""
    pattern_category: str
    pattern_name: str
    success_count: int
    avg_pass_rate: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplexityCorrelation:
    """Correlation between IR complexity and generation success."""
    entity_count: int
    endpoint_count: int
    flow_count: int
    avg_pass_rate: float
    sample_count: int


@dataclass
class EntityErrorProfile:
    """Error profile for a specific entity type."""
    entity_name: str
    error_count: int
    error_types: List[str]
    common_fixes: List[str] = field(default_factory=list)


@dataclass
class LearningReport:
    """Comprehensive learning insights report."""
    generated_at: datetime
    failure_patterns: List[FailurePattern]
    success_patterns: List[SuccessPattern]
    complexity_correlations: List[ComplexityCorrelation]
    entity_error_profiles: List[EntityErrorProfile]
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# Cypher Queries for Pattern Mining
# =============================================================================

FAILURE_PATTERNS_QUERY = """
// Query 1: Endpoints with consistent failures
// Note: Uses coalesce for occurrence_count as it may not exist on all ErrorKnowledge nodes
MATCH (ek:ErrorKnowledge)
WITH ek, coalesce(ek.occurrence_count, 1) as occ_count
WHERE occ_count >= 2
RETURN
    'endpoint' as element_type,
    ek.endpoint_pattern as element_name,
    occ_count as failure_count,
    [ek.error_type] as error_types,
    {entity: ek.entity_type, category: ek.pattern_category} as context
ORDER BY failure_count DESC
LIMIT 20
"""

SUCCESS_PATTERNS_QUERY = """
// Query 2: Patterns with high confidence (successful)
MATCH (fp:FixPattern)
WHERE fp.confidence >= 0.7 AND fp.success_count >= 2
RETURN
    fp.fix_strategy as pattern_category,
    fp.error_type as pattern_name,
    fp.success_count as success_count,
    fp.confidence as avg_pass_rate,
    {signature: fp.error_signature} as context
ORDER BY success_count DESC
LIMIT 20
"""

ENTITY_ERROR_PROFILE_QUERY = """
// Query 3: Entity error profiles
// Note: Uses coalesce for occurrence_count as it may not exist on all ErrorKnowledge nodes
MATCH (ek:ErrorKnowledge)
WHERE ek.entity_type IS NOT NULL
WITH ek.entity_type as entity_name,
     collect(ek.error_type) as error_types,
     sum(coalesce(ek.occurrence_count, 1)) as total_errors
RETURN entity_name, total_errors as error_count, error_types
ORDER BY error_count DESC
LIMIT 10
"""

FIX_STRATEGY_EFFECTIVENESS_QUERY = """
// Query 4: Fix strategy effectiveness
MATCH (fp:FixPattern)
WITH fp.fix_strategy as strategy,
     count(fp) as usage_count,
     avg(fp.confidence) as avg_confidence,
     sum(fp.success_count) as total_successes,
     sum(fp.failure_count) as total_failures
RETURN strategy, usage_count, avg_confidence, total_successes, total_failures
ORDER BY avg_confidence DESC
"""

ERROR_TYPE_DISTRIBUTION_QUERY = """
// Query 5: Error type distribution
MATCH (ek:ErrorKnowledge)
RETURN ek.error_type as error_type,
       count(ek) as count,
       avg(ek.confidence) as avg_confidence
ORDER BY count DESC
LIMIT 10
"""

PATTERN_CATEGORY_SUCCESS_QUERY = """
// Query 6: Pattern category success rates
MATCH (ek:ErrorKnowledge)
WITH ek.pattern_category as category,
     count(ek) as error_count,
     avg(ek.confidence) as avg_confidence
RETURN category, error_count, avg_confidence
ORDER BY error_count DESC
"""


# =============================================================================
# Pattern Mining Service
# =============================================================================

class PatternMiningService:
    """
    Mines patterns from Neo4j graph for learning insights.

    Gap 3 Implementation: Analyzes stored ErrorKnowledge and FixPattern
    nodes to extract actionable insights for improving code generation.
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize with Neo4j connection."""
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        self.logger = logging.getLogger(f"{__name__}.PatternMiningService")

    def close(self):
        """Close Neo4j connection."""
        self.driver.close()

    def get_failure_patterns(self) -> List[FailurePattern]:
        """
        Get endpoints/entities with high failure rates.

        Returns:
            List of FailurePattern objects ordered by failure count
        """
        try:
            with self.driver.session() as session:
                result = session.run(FAILURE_PATTERNS_QUERY)
                patterns = []
                for record in result:
                    patterns.append(FailurePattern(
                        element_type=record["element_type"],
                        element_name=record["element_name"] or "unknown",
                        failure_count=record["failure_count"],
                        error_types=record["error_types"] or [],
                        context=dict(record["context"]) if record["context"] else {}
                    ))
                self.logger.info(f"Found {len(patterns)} failure patterns")
                return patterns
        except Exception as e:
            self.logger.error(f"Error getting failure patterns: {e}")
            return []

    def get_success_patterns(self) -> List[SuccessPattern]:
        """
        Get patterns with high success rates.

        Returns:
            List of SuccessPattern objects ordered by success count
        """
        try:
            with self.driver.session() as session:
                result = session.run(SUCCESS_PATTERNS_QUERY)
                patterns = []
                for record in result:
                    patterns.append(SuccessPattern(
                        pattern_category=record["pattern_category"] or "unknown",
                        pattern_name=record["pattern_name"] or "unknown",
                        success_count=record["success_count"],
                        avg_pass_rate=record["avg_pass_rate"] or 0.0,
                        context=dict(record["context"]) if record["context"] else {}
                    ))
                self.logger.info(f"Found {len(patterns)} success patterns")
                return patterns
        except Exception as e:
            self.logger.error(f"Error getting success patterns: {e}")
            return []

    def get_entity_error_profiles(self) -> List[EntityErrorProfile]:
        """
        Get error profiles grouped by entity type.

        Returns:
            List of EntityErrorProfile objects
        """
        try:
            with self.driver.session() as session:
                result = session.run(ENTITY_ERROR_PROFILE_QUERY)
                profiles = []
                for record in result:
                    profiles.append(EntityErrorProfile(
                        entity_name=record["entity_name"],
                        error_count=record["error_count"],
                        error_types=list(set(record["error_types"] or []))
                    ))
                self.logger.info(f"Found {len(profiles)} entity error profiles")
                return profiles
        except Exception as e:
            self.logger.error(f"Error getting entity error profiles: {e}")
            return []

    def get_fix_strategy_effectiveness(self) -> Dict[str, Any]:
        """
        Analyze effectiveness of different fix strategies.

        Returns:
            Dict with strategy effectiveness metrics
        """
        try:
            with self.driver.session() as session:
                result = session.run(FIX_STRATEGY_EFFECTIVENESS_QUERY)
                strategies = {}
                for record in result:
                    strategies[record["strategy"]] = {
                        "usage_count": record["usage_count"],
                        "avg_confidence": round(record["avg_confidence"] or 0, 3),
                        "total_successes": record["total_successes"],
                        "total_failures": record["total_failures"]
                    }
                return strategies
        except Exception as e:
            self.logger.error(f"Error getting fix strategy effectiveness: {e}")
            return {}

    def get_error_distribution(self) -> Dict[str, int]:
        """
        Get distribution of error types.

        Returns:
            Dict mapping error_type to count
        """
        try:
            with self.driver.session() as session:
                result = session.run(ERROR_TYPE_DISTRIBUTION_QUERY)
                distribution = {}
                for record in result:
                    distribution[record["error_type"]] = record["count"]
                return distribution
        except Exception as e:
            self.logger.error(f"Error getting error distribution: {e}")
            return {}

    def generate_learning_report(self) -> LearningReport:
        """
        Generate comprehensive learning insights report.

        Analyzes all available patterns and generates actionable insights.

        Returns:
            LearningReport with patterns, correlations, and recommendations
        """
        self.logger.info("Generating learning report...")

        failure_patterns = self.get_failure_patterns()
        success_patterns = self.get_success_patterns()
        entity_profiles = self.get_entity_error_profiles()
        fix_effectiveness = self.get_fix_strategy_effectiveness()
        error_distribution = self.get_error_distribution()

        # Generate insights
        insights = self._generate_insights(
            failure_patterns, success_patterns,
            entity_profiles, fix_effectiveness
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            failure_patterns, success_patterns,
            entity_profiles, fix_effectiveness
        )

        report = LearningReport(
            generated_at=datetime.now(),
            failure_patterns=failure_patterns,
            success_patterns=success_patterns,
            complexity_correlations=[],  # TODO: Add when ApplicationIR relationships exist
            entity_error_profiles=entity_profiles,
            insights=insights,
            recommendations=recommendations
        )

        self.logger.info(
            f"Learning report generated: {len(failure_patterns)} failures, "
            f"{len(success_patterns)} successes, {len(insights)} insights"
        )

        return report

    def _generate_insights(
        self,
        failures: List[FailurePattern],
        successes: List[SuccessPattern],
        entity_profiles: List[EntityErrorProfile],
        fix_effectiveness: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from mining results."""
        insights = []

        # Insight 1: Most problematic endpoints
        if failures:
            top_failure = failures[0]
            insights.append(
                f"Most problematic pattern: '{top_failure.element_name}' "
                f"with {top_failure.failure_count} failures "
                f"(errors: {', '.join(top_failure.error_types[:3])})"
            )

        # Insight 2: Most effective fix strategies
        if fix_effectiveness:
            best_strategy = max(
                fix_effectiveness.items(),
                key=lambda x: x[1].get("avg_confidence", 0)
            )
            insights.append(
                f"Most effective fix strategy: '{best_strategy[0]}' "
                f"with {best_strategy[1]['avg_confidence']:.0%} confidence"
            )

        # Insight 3: Entity error concentration
        if entity_profiles:
            total_errors = sum(p.error_count for p in entity_profiles)
            top_entity = entity_profiles[0]
            if total_errors > 0:
                concentration = (top_entity.error_count / total_errors) * 100
                insights.append(
                    f"Entity '{top_entity.entity_name}' accounts for "
                    f"{concentration:.1f}% of all errors"
                )

        # Insight 4: Success pattern availability
        if successes:
            high_confidence = [s for s in successes if s.avg_pass_rate >= 0.8]
            insights.append(
                f"{len(high_confidence)} fix patterns have ≥80% success rate"
            )

        return insights

    def _generate_recommendations(
        self,
        failures: List[FailurePattern],
        successes: List[SuccessPattern],
        entity_profiles: List[EntityErrorProfile],
        fix_effectiveness: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on mining results."""
        recommendations = []

        # Recommendation 1: Focus on high-failure areas
        if failures and failures[0].failure_count >= 3:
            top_failure = failures[0]
            recommendations.append(
                f"Priority: Investigate recurring failures in "
                f"'{top_failure.element_name}' ({top_failure.failure_count} occurrences)"
            )

        # Recommendation 2: Leverage successful strategies
        if fix_effectiveness:
            good_strategies = [
                k for k, v in fix_effectiveness.items()
                if v.get("avg_confidence", 0) >= 0.7
            ]
            if good_strategies:
                recommendations.append(
                    f"Prioritize fix strategies: {', '.join(good_strategies[:3])}"
                )

        # Recommendation 3: Entity-specific templates
        if entity_profiles:
            problematic = [p for p in entity_profiles if p.error_count >= 5]
            if problematic:
                recommendations.append(
                    f"Consider custom templates for entities: "
                    f"{', '.join(p.entity_name for p in problematic[:3])}"
                )

        # Recommendation 4: Expand successful patterns
        if successes:
            recommendations.append(
                f"Expand usage of {len(successes)} proven fix patterns"
            )

        return recommendations

    def get_mining_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for pattern mining.

        Returns:
            Dict with mining statistics
        """
        try:
            with self.driver.session() as session:
                # Count nodes
                error_knowledge_count = session.run(
                    "MATCH (ek:ErrorKnowledge) RETURN count(ek) as count"
                ).single()["count"]

                fix_pattern_count = session.run(
                    "MATCH (fp:FixPattern) RETURN count(fp) as count"
                ).single()["count"]

                # Get date range
                date_range = session.run("""
                    MATCH (ek:ErrorKnowledge)
                    RETURN min(ek.created_at) as earliest, max(ek.last_seen) as latest
                """).single()

                return {
                    "error_knowledge_count": error_knowledge_count,
                    "fix_pattern_count": fix_pattern_count,
                    "earliest_error": str(date_range["earliest"]) if date_range["earliest"] else None,
                    "latest_error": str(date_range["latest"]) if date_range["latest"] else None,
                    "data_available": error_knowledge_count > 0 or fix_pattern_count > 0
                }
        except Exception as e:
            self.logger.error(f"Error getting mining statistics: {e}")
            return {"error": str(e), "data_available": False}


# =============================================================================
# Singleton Instance
# =============================================================================

_pattern_mining_service: Optional[PatternMiningService] = None


def get_pattern_mining_service() -> PatternMiningService:
    """Get singleton instance of PatternMiningService."""
    global _pattern_mining_service
    if _pattern_mining_service is None:
        import os
        _pattern_mining_service = PatternMiningService(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _pattern_mining_service
