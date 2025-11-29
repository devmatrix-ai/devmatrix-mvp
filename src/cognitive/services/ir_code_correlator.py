"""
IR-to-Code Failure Correlation Service.

Gap 5 Implementation: Correlates IR complexity with code generation quality
to identify patterns that consistently produce failing code.

Reference: DOCS/mvp/exit/learning/LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 5
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EntityCorrelation:
    """Correlation between entity complexity and generation quality."""
    entity_name: str
    complexity_score: float
    pass_rate: float
    attributes_count: int
    relationships_count: int
    has_enums: bool = False
    has_json_fields: bool = False
    failure_types: List[str] = field(default_factory=list)


@dataclass
class EndpointCorrelation:
    """Correlation between endpoint complexity and generation quality."""
    path: str
    method: str
    complexity_score: float
    pass_rate: float
    params_count: int
    has_body: bool
    has_path_params: bool = False
    has_query_params: bool = False
    failure_types: List[str] = field(default_factory=list)


@dataclass
class HighRiskPattern:
    """Pattern identified as high-risk for code generation."""
    pattern_type: str  # "entity", "endpoint", "relationship"
    pattern_name: str
    risk_score: float
    occurrences: int
    avg_pass_rate: float
    description: str
    mitigation: str


@dataclass
class IRCorrelationReport:
    """Comprehensive IR-to-Code correlation report."""
    generated_at: datetime
    entity_correlations: List[EntityCorrelation]
    endpoint_correlations: List[EndpointCorrelation]
    high_risk_patterns: List[HighRiskPattern]
    insights: List[str]
    recommendations: List[str]
    summary: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# IR Code Correlator Service
# =============================================================================

class IRCodeCorrelator:
    """
    Correlates IR elements with generated code quality.

    Gap 5 Implementation: Analyzes relationships between IR complexity
    (entities, endpoints, flows) and code generation success rates.
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize with Neo4j connection."""
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

        self.logger = logging.getLogger(f"{__name__}.IRCodeCorrelator")

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def analyze_generation(
        self,
        entities: List[Dict[str, Any]],
        endpoints: List[Dict[str, Any]],
        smoke_results: Dict[str, Any]
    ) -> IRCorrelationReport:
        """
        Analyze which IR elements correlate with failures.

        Args:
            entities: List of entity dicts from ApplicationIR
            endpoints: List of endpoint dicts from ApplicationIR
            smoke_results: Dict with violations and passed_scenarios

        Returns:
            IRCorrelationReport with correlations and insights
        """
        entity_correlations = []
        endpoint_correlations = []

        # Analyze entities
        for entity in entities:
            correlation = self._analyze_entity(entity, smoke_results)
            entity_correlations.append(correlation)

        # Analyze endpoints
        for endpoint in endpoints:
            correlation = self._analyze_endpoint(endpoint, smoke_results)
            endpoint_correlations.append(correlation)

        # Identify high-risk patterns
        high_risk = self._identify_high_risk_patterns(
            entity_correlations, endpoint_correlations
        )

        # Generate insights
        insights = self._generate_insights(
            entity_correlations, endpoint_correlations, high_risk
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(high_risk)

        # Build summary
        summary = self._build_summary(
            entity_correlations, endpoint_correlations, high_risk
        )

        report = IRCorrelationReport(
            generated_at=datetime.now(),
            entity_correlations=entity_correlations,
            endpoint_correlations=endpoint_correlations,
            high_risk_patterns=high_risk,
            insights=insights,
            recommendations=recommendations,
            summary=summary
        )

        # Persist to Neo4j
        self._persist_report(report)

        return report

    def _analyze_entity(
        self,
        entity: Dict[str, Any],
        smoke_results: Dict[str, Any]
    ) -> EntityCorrelation:
        """Analyze a single entity's complexity vs generation quality."""
        name = entity.get("name", "unknown")
        attributes = entity.get("attributes", [])
        relationships = entity.get("relationships", [])

        # Compute complexity
        complexity = self._compute_entity_complexity(entity)

        # Get pass rate from smoke results
        pass_rate = self._get_entity_pass_rate(name, smoke_results)

        # Get failure types
        failure_types = self._get_entity_failure_types(name, smoke_results)

        # Check for complex types
        has_enums = any(
            attr.get("data_type") == "enum" or attr.get("is_enum", False)
            for attr in attributes
        )
        has_json = any(
            attr.get("data_type") in ["json", "jsonb", "dict"]
            for attr in attributes
        )

        return EntityCorrelation(
            entity_name=name,
            complexity_score=complexity,
            pass_rate=pass_rate,
            attributes_count=len(attributes),
            relationships_count=len(relationships),
            has_enums=has_enums,
            has_json_fields=has_json,
            failure_types=failure_types
        )

    def _analyze_endpoint(
        self,
        endpoint: Dict[str, Any],
        smoke_results: Dict[str, Any]
    ) -> EndpointCorrelation:
        """Analyze a single endpoint's complexity vs generation quality."""
        path = endpoint.get("path", "/unknown")
        method = endpoint.get("method", "GET").upper()
        parameters = endpoint.get("parameters", [])
        request_body = endpoint.get("request_body")

        # Compute complexity
        complexity = self._compute_endpoint_complexity(endpoint)

        # Get pass rate
        pass_rate = self._get_endpoint_pass_rate(path, method, smoke_results)

        # Get failure types
        failure_types = self._get_endpoint_failure_types(path, method, smoke_results)

        # Check parameter types
        has_path = any(p.get("in") == "path" for p in parameters)
        has_query = any(p.get("in") == "query" for p in parameters)

        return EndpointCorrelation(
            path=path,
            method=method,
            complexity_score=complexity,
            pass_rate=pass_rate,
            params_count=len(parameters),
            has_body=request_body is not None,
            has_path_params=has_path,
            has_query_params=has_query,
            failure_types=failure_types
        )

    def _compute_entity_complexity(self, entity: Dict[str, Any]) -> float:
        """Compute complexity score for an entity (0-1)."""
        attributes = entity.get("attributes", [])
        relationships = entity.get("relationships", [])

        # Base score from attributes
        base_score = len(attributes) * 0.05

        # Relationship score
        relationship_score = len(relationships) * 0.15

        # Penalize complex types
        for attr in attributes:
            dtype = attr.get("data_type", "").lower()
            if dtype in ["json", "jsonb", "dict", "array", "list"]:
                base_score += 0.15
            elif dtype in ["enum"]:
                base_score += 0.1
            elif dtype in ["uuid"]:
                base_score += 0.05

        # Penalize nullable fields (more error-prone)
        nullable_count = sum(1 for a in attributes if a.get("nullable", False))
        base_score += nullable_count * 0.02

        return min(1.0, base_score + relationship_score)

    def _compute_endpoint_complexity(self, endpoint: Dict[str, Any]) -> float:
        """Compute complexity score for an endpoint (0-1)."""
        parameters = endpoint.get("parameters", [])
        request_body = endpoint.get("request_body")
        responses = endpoint.get("responses", {})

        # Base from parameters
        base_score = len(parameters) * 0.1

        # Request body adds complexity
        if request_body:
            base_score += 0.2
            # Nested body is more complex
            if isinstance(request_body, dict):
                properties = request_body.get("properties", {})
                base_score += len(properties) * 0.03

        # Multiple response codes add complexity
        base_score += len(responses) * 0.05

        # Path parameters are more complex than query
        path_params = sum(1 for p in parameters if p.get("in") == "path")
        base_score += path_params * 0.05

        return min(1.0, base_score)

    def _get_entity_pass_rate(
        self,
        entity_name: str,
        smoke_results: Dict[str, Any]
    ) -> float:
        """Get pass rate for entity-related tests."""
        violations = smoke_results.get("violations", [])
        passed = smoke_results.get("passed_scenarios", [])

        entity_lower = entity_name.lower()

        # Count entity-related failures
        entity_failures = sum(
            1 for v in violations
            if entity_lower in str(v).lower()
        )

        # Count entity-related passes
        entity_passes = sum(
            1 for p in passed
            if entity_lower in str(p).lower()
        )

        total = entity_failures + entity_passes
        if total == 0:
            return 1.0  # No data = assume OK

        return entity_passes / total

    def _get_endpoint_pass_rate(
        self,
        path: str,
        method: str,
        smoke_results: Dict[str, Any]
    ) -> float:
        """Get pass rate for a specific endpoint."""
        violations = smoke_results.get("violations", [])
        passed = smoke_results.get("passed_scenarios", [])

        # Normalize path for matching
        path_pattern = path.replace("{", "").replace("}", "").lower()

        # Count failures
        failures = sum(
            1 for v in violations
            if path_pattern in str(v.get("endpoint", "")).lower()
            and method.upper() in str(v.get("method", "")).upper()
        )

        # Count passes
        passes = sum(
            1 for p in passed
            if path_pattern in str(p.get("endpoint", "")).lower()
            and method.upper() in str(p.get("method", "")).upper()
        )

        total = failures + passes
        if total == 0:
            return 1.0

        return passes / total

    def _get_entity_failure_types(
        self,
        entity_name: str,
        smoke_results: Dict[str, Any]
    ) -> List[str]:
        """Get failure types for an entity."""
        violations = smoke_results.get("violations", [])
        entity_lower = entity_name.lower()

        failure_types = []
        for v in violations:
            if entity_lower in str(v).lower():
                error_type = v.get("error_type", v.get("type", "unknown"))
                if error_type not in failure_types:
                    failure_types.append(error_type)

        return failure_types[:5]  # Limit to 5

    def _get_endpoint_failure_types(
        self,
        path: str,
        method: str,
        smoke_results: Dict[str, Any]
    ) -> List[str]:
        """Get failure types for an endpoint."""
        violations = smoke_results.get("violations", [])
        path_pattern = path.replace("{", "").replace("}", "").lower()

        failure_types = []
        for v in violations:
            if (path_pattern in str(v.get("endpoint", "")).lower() and
                    method.upper() in str(v.get("method", "")).upper()):
                error_type = v.get("error_type", v.get("type", "unknown"))
                if error_type not in failure_types:
                    failure_types.append(error_type)

        return failure_types[:5]

    def _identify_high_risk_patterns(
        self,
        entity_correlations: List[EntityCorrelation],
        endpoint_correlations: List[EndpointCorrelation]
    ) -> List[HighRiskPattern]:
        """Identify patterns that are high-risk for code generation."""
        patterns = []

        # Pattern 1: High complexity + low pass rate entities
        risky_entities = [
            e for e in entity_correlations
            if e.complexity_score > 0.5 and e.pass_rate < 0.7
        ]
        if risky_entities:
            avg_pass = sum(e.pass_rate for e in risky_entities) / len(risky_entities)
            patterns.append(HighRiskPattern(
                pattern_type="entity",
                pattern_name="high_complexity_entity",
                risk_score=0.8,
                occurrences=len(risky_entities),
                avg_pass_rate=avg_pass,
                description=f"Entities with >50% complexity and <70% pass rate",
                mitigation="Consider simplifying entity structure or adding specialized templates"
            ))

        # Pattern 2: Entities with enums
        enum_entities = [e for e in entity_correlations if e.has_enums]
        if enum_entities:
            avg_pass = sum(e.pass_rate for e in enum_entities) / len(enum_entities)
            if avg_pass < 0.8:
                patterns.append(HighRiskPattern(
                    pattern_type="entity",
                    pattern_name="enum_fields",
                    risk_score=0.6,
                    occurrences=len(enum_entities),
                    avg_pass_rate=avg_pass,
                    description="Entities with enum fields tend to have generation issues",
                    mitigation="Ensure enum definitions are properly generated before entity"
                ))

        # Pattern 3: Entities with JSON fields
        json_entities = [e for e in entity_correlations if e.has_json_fields]
        if json_entities:
            avg_pass = sum(e.pass_rate for e in json_entities) / len(json_entities)
            if avg_pass < 0.8:
                patterns.append(HighRiskPattern(
                    pattern_type="entity",
                    pattern_name="json_fields",
                    risk_score=0.5,
                    occurrences=len(json_entities),
                    avg_pass_rate=avg_pass,
                    description="Entities with JSON/dict fields may have serialization issues",
                    mitigation="Add JSON serialization helpers to entity templates"
                ))

        # Pattern 4: Complex endpoints (many params + body)
        complex_endpoints = [
            e for e in endpoint_correlations
            if e.params_count > 3 and e.has_body and e.pass_rate < 0.7
        ]
        if complex_endpoints:
            avg_pass = sum(e.pass_rate for e in complex_endpoints) / len(complex_endpoints)
            patterns.append(HighRiskPattern(
                pattern_type="endpoint",
                pattern_name="complex_endpoint",
                risk_score=0.7,
                occurrences=len(complex_endpoints),
                avg_pass_rate=avg_pass,
                description="Endpoints with >3 params and request body are error-prone",
                mitigation="Break into smaller endpoints or use request schema validation"
            ))

        # Pattern 5: Many relationships
        many_rels = [e for e in entity_correlations if e.relationships_count > 2]
        if many_rels:
            avg_pass = sum(e.pass_rate for e in many_rels) / len(many_rels)
            if avg_pass < 0.8:
                patterns.append(HighRiskPattern(
                    pattern_type="relationship",
                    pattern_name="many_relationships",
                    risk_score=0.6,
                    occurrences=len(many_rels),
                    avg_pass_rate=avg_pass,
                    description="Entities with >2 relationships often have join issues",
                    mitigation="Review relationship definitions and lazy loading strategy"
                ))

        return sorted(patterns, key=lambda p: p.risk_score, reverse=True)

    def _generate_insights(
        self,
        entity_correlations: List[EntityCorrelation],
        endpoint_correlations: List[EndpointCorrelation],
        high_risk: List[HighRiskPattern]
    ) -> List[str]:
        """Generate insights from correlation analysis."""
        insights = []

        # Insight 1: Overall entity health
        if entity_correlations:
            avg_entity_pass = sum(e.pass_rate for e in entity_correlations) / len(entity_correlations)
            insights.append(
                f"Average entity pass rate: {avg_entity_pass:.1%} "
                f"({len(entity_correlations)} entities analyzed)"
            )

        # Insight 2: Overall endpoint health
        if endpoint_correlations:
            avg_endpoint_pass = sum(e.pass_rate for e in endpoint_correlations) / len(endpoint_correlations)
            insights.append(
                f"Average endpoint pass rate: {avg_endpoint_pass:.1%} "
                f"({len(endpoint_correlations)} endpoints analyzed)"
            )

        # Insight 3: Complexity correlation
        if entity_correlations:
            high_complexity = [e for e in entity_correlations if e.complexity_score > 0.5]
            low_complexity = [e for e in entity_correlations if e.complexity_score <= 0.5]

            if high_complexity and low_complexity:
                high_pass = sum(e.pass_rate for e in high_complexity) / len(high_complexity)
                low_pass = sum(e.pass_rate for e in low_complexity) / len(low_complexity)

                if high_pass < low_pass:
                    diff = (low_pass - high_pass) * 100
                    insights.append(
                        f"High-complexity entities have {diff:.1f}% lower pass rate than simple ones"
                    )

        # Insight 4: Risk patterns
        if high_risk:
            insights.append(
                f"Identified {len(high_risk)} high-risk patterns to address"
            )

        return insights

    def _generate_recommendations(
        self,
        high_risk: List[HighRiskPattern]
    ) -> List[str]:
        """Generate recommendations based on high-risk patterns."""
        recommendations = []

        for pattern in high_risk[:3]:  # Top 3 risks
            recommendations.append(
                f"[{pattern.pattern_type.upper()}] {pattern.pattern_name}: "
                f"{pattern.mitigation}"
            )

        if not recommendations:
            recommendations.append("No critical patterns identified - generation quality is acceptable")

        return recommendations

    def _build_summary(
        self,
        entity_correlations: List[EntityCorrelation],
        endpoint_correlations: List[EndpointCorrelation],
        high_risk: List[HighRiskPattern]
    ) -> Dict[str, Any]:
        """Build summary statistics."""
        return {
            "total_entities": len(entity_correlations),
            "total_endpoints": len(endpoint_correlations),
            "high_risk_patterns": len(high_risk),
            "avg_entity_complexity": (
                sum(e.complexity_score for e in entity_correlations) / len(entity_correlations)
                if entity_correlations else 0
            ),
            "avg_endpoint_complexity": (
                sum(e.complexity_score for e in endpoint_correlations) / len(endpoint_correlations)
                if endpoint_correlations else 0
            ),
            "entities_with_failures": sum(1 for e in entity_correlations if e.pass_rate < 1.0),
            "endpoints_with_failures": sum(1 for e in endpoint_correlations if e.pass_rate < 1.0),
        }

    def _persist_report(self, report: IRCorrelationReport):
        """Persist correlation report to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                # Store summary node
                session.run("""
                    CREATE (r:IRCorrelationReport {
                        generated_at: datetime(),
                        total_entities: $entities,
                        total_endpoints: $endpoints,
                        high_risk_count: $high_risk,
                        insights: $insights
                    })
                """, {
                    "entities": report.summary.get("total_entities", 0),
                    "endpoints": report.summary.get("total_endpoints", 0),
                    "high_risk": len(report.high_risk_patterns),
                    "insights": report.insights[:5]
                })

                self.logger.info("Persisted IR correlation report to Neo4j")
        except Exception as e:
            self.logger.warning(f"Failed to persist report: {e}")

    def get_historical_correlations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get historical correlation reports from Neo4j."""
        if not self._neo4j_available or not self.driver:
            return []

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (r:IRCorrelationReport)
                    RETURN r
                    ORDER BY r.generated_at DESC
                    LIMIT $limit
                """, limit=limit)

                return [dict(record["r"]) for record in result]
        except Exception as e:
            self.logger.error(f"Failed to get historical correlations: {e}")
            return []


# =============================================================================
# Singleton Instance
# =============================================================================

_ir_code_correlator: Optional[IRCodeCorrelator] = None


def get_ir_code_correlator() -> IRCodeCorrelator:
    """Get singleton instance of IRCodeCorrelator."""
    global _ir_code_correlator
    if _ir_code_correlator is None:
        import os
        _ir_code_correlator = IRCodeCorrelator(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _ir_code_correlator
