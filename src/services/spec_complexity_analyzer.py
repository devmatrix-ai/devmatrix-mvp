"""
Spec Complexity Analyzer - Learning from Spec Processing.

Gap 6 Implementation: Analyzes spec complexity to predict processing time
and learn what makes specs difficult to process.

Reference: DOCS/mvp/exit/learning/LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 6
"""
import logging
import re
import json
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase

from src.utils.yaml_helpers import safe_yaml_load

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SpecComplexity:
    """Complexity analysis of a spec file."""
    spec_id: str
    path: str
    size_bytes: int
    line_count: int
    entity_count: int
    endpoint_count: int
    schema_count: int
    has_circular_refs: bool = False
    has_polymorphism: bool = False  # oneOf, anyOf, allOf
    has_external_refs: bool = False
    complexity_score: float = 0.0
    complexity_indicators: List[str] = field(default_factory=list)
    estimated_processing_ms: int = 0


@dataclass
class ProcessingResult:
    """Result of processing a spec."""
    spec_id: str
    actual_time_ms: int
    success: bool
    ir_quality_score: float
    error_message: Optional[str] = None
    phases_completed: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SpecLearningInsight:
    """Learning insight about spec processing."""
    insight_type: str
    description: str
    affected_specs: int
    avg_time_impact_ms: int
    recommendation: str


# =============================================================================
# Spec Complexity Analyzer
# =============================================================================

class SpecComplexityAnalyzer:
    """
    Analyzes spec complexity and tracks processing metrics.

    Gap 6 Implementation:
    - Analyzes specs before processing to estimate complexity
    - Records actual processing times for learning
    - Identifies patterns that make specs difficult
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123"
    ):
        """Initialize analyzer."""
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

        self.logger = logging.getLogger(f"{__name__}.SpecComplexityAnalyzer")

        # In-memory learning data
        self._processing_samples: List[Dict[str, Any]] = []

        # Baseline time estimates (ms per unit)
        self._time_coefficients = {
            "base": 5000,  # 5s base
            "per_endpoint": 200,
            "per_entity": 300,
            "per_schema": 100,
            "circular_ref_penalty": 2000,
            "polymorphism_penalty": 1500,
            "external_ref_penalty": 1000,
        }

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def analyze_spec(self, spec_path: str) -> SpecComplexity:
        """
        Analyze spec complexity before processing.

        Args:
            spec_path: Path to OpenAPI spec file

        Returns:
            SpecComplexity with analysis results
        """
        import uuid
        spec_id = f"spec_{uuid.uuid4().hex[:8]}"

        try:
            content = self._load_spec(spec_path)
            spec_data = self._parse_spec(content, spec_path)

            # Bug #171 Fix: For markdown specs, use text-based analysis
            if spec_path.endswith('.md') or not spec_data:
                return self._analyze_markdown_spec(spec_id, spec_path, content)

            # Count elements
            endpoints = self._count_endpoints(spec_data)
            entities = self._count_entities(spec_data)
            schemas = self._count_schemas(spec_data)

            # Detect complexity indicators
            indicators = []
            has_circular = self._detect_circular_refs(spec_data)
            has_poly = self._detect_polymorphism(spec_data)
            has_external = self._detect_external_refs(spec_data)

            if has_circular:
                indicators.append("circular_references")
            if has_poly:
                indicators.append("polymorphic_schemas")
            if has_external:
                indicators.append("external_references")
            if endpoints > 20:
                indicators.append("many_endpoints")
            if entities > 10:
                indicators.append("many_entities")
            if schemas > 30:
                indicators.append("many_schemas")

            # Compute complexity score
            complexity = self._compute_complexity_score(
                endpoints, entities, schemas,
                has_circular, has_poly, has_external
            )

            # Estimate processing time
            estimated_time = self._estimate_processing_time(
                endpoints, entities, schemas,
                has_circular, has_poly, has_external
            )

            return SpecComplexity(
                spec_id=spec_id,
                path=spec_path,
                size_bytes=len(content),
                line_count=content.count('\n') + 1,
                entity_count=entities,
                endpoint_count=endpoints,
                schema_count=schemas,
                has_circular_refs=has_circular,
                has_polymorphism=has_poly,
                has_external_refs=has_external,
                complexity_score=complexity,
                complexity_indicators=indicators,
                estimated_processing_ms=estimated_time
            )

        except Exception as e:
            self.logger.error(f"Failed to analyze spec: {e}")
            return SpecComplexity(
                spec_id=spec_id,
                path=spec_path,
                size_bytes=0,
                line_count=0,
                entity_count=0,
                endpoint_count=0,
                schema_count=0,
                complexity_score=1.0,  # Assume complex if can't analyze
                complexity_indicators=["parse_error"],
                estimated_processing_ms=60000
            )

    def _analyze_markdown_spec(self, spec_id: str, spec_path: str, content: str) -> SpecComplexity:
        """
        Bug #171 Fix: Analyze markdown spec using text patterns.

        For markdown specs, we can't use JSON/YAML parsing, so we use regex patterns
        to estimate entities, endpoints, and complexity from the text.
        """
        import re

        # Count endpoints from patterns like "GET /products", "POST /orders"
        endpoint_patterns = re.findall(
            r'\b(GET|POST|PUT|PATCH|DELETE)\s+/[a-zA-Z0-9_/{}]+',
            content, re.IGNORECASE
        )
        endpoints = len(endpoint_patterns)

        # Count entities from header patterns like "## Product", "### Order Entity"
        entity_patterns = re.findall(
            r'^#+\s+(\w+)\s*(?:Entity|Model|Resource|Schema)?',
            content, re.MULTILINE | re.IGNORECASE
        )
        # Filter common non-entity headers
        entity_blacklist = {'api', 'overview', 'introduction', 'endpoints', 'authentication',
                           'flows', 'business', 'requirements', 'summary', 'description'}
        entities = len([e for e in entity_patterns if e.lower() not in entity_blacklist])

        # Count flows from patterns like "checkout flow", "payment process"
        flow_patterns = re.findall(
            r'\b(flow|process|workflow|scenario|use.?case)\b',
            content, re.IGNORECASE
        )
        flows = len(flow_patterns) // 2  # Approximate, flows mentioned multiple times

        # Compute complexity based on text-extracted counts
        complexity = self._compute_complexity_score(
            endpoints=endpoints,
            entities=entities,
            schemas=entities,  # Use entities as proxy for schemas
            has_circular=False,
            has_poly=False,
            has_external=False
        )

        # Add markdown-specific complexity factors
        if 'authentication' in content.lower() or 'oauth' in content.lower():
            complexity = min(1.0, complexity + 0.1)
        if 'pagination' in content.lower():
            complexity = min(1.0, complexity + 0.05)

        # Build indicators
        indicators = ["markdown_spec"]
        if endpoints > 20:
            indicators.append("many_endpoints")
        if entities > 10:
            indicators.append("many_entities")
        if flows > 5:
            indicators.append("complex_flows")

        # Estimate processing time
        estimated_time = self._estimate_processing_time(
            endpoints, entities, entities, False, False, False
        )

        self.logger.info(
            f"Markdown spec analysis: {endpoints} endpoints, {entities} entities, "
            f"complexity={complexity:.2f}"
        )

        return SpecComplexity(
            spec_id=spec_id,
            path=spec_path,
            size_bytes=len(content),
            line_count=content.count('\n') + 1,
            entity_count=entities,
            endpoint_count=endpoints,
            schema_count=entities,
            has_circular_refs=False,
            has_polymorphism=False,
            has_external_refs=False,
            complexity_score=complexity,
            complexity_indicators=indicators,
            estimated_processing_ms=estimated_time
        )

    def _load_spec(self, spec_path: str) -> str:
        """Load spec file content."""
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"Spec not found: {spec_path}")
        return path.read_text()

    def _parse_spec(self, content: str, path: str) -> Dict[str, Any]:
        """
        Parse spec content to dict with robust error handling.

        Supports:
        - JSON files (.json)
        - YAML files (.yaml, .yml)
        - Markdown files (.md) - returns empty dict, complexity from text analysis
        """
        if path.endswith('.json'):
            return json.loads(content)
        elif path.endswith('.md'):
            # Markdown files are NOT YAML - don't try to parse them
            # Complexity analysis will use text-based metrics instead
            logger.debug(f"Markdown spec {path} - using text analysis only")
            return {}
        elif path.endswith(('.yaml', '.yml')):
            # Only parse YAML for actual YAML files
            result = safe_yaml_load(content, default=None)
            if result is None:
                logger.warning(f"YAML parse failed for {path}, attempting cleanup")
                cleaned = self._clean_yaml_content(content)
                result = safe_yaml_load(cleaned, default={})
            return result if isinstance(result, dict) else {}
        else:
            # Unknown extension - try YAML as fallback but don't error
            result = safe_yaml_load(content, default={})
            return result if isinstance(result, dict) else {}

    def _clean_yaml_content(self, content: str) -> str:
        """
        Clean YAML content by removing or fixing problematic lines.

        Common issues:
        - Block scalars (>) with special characters
        - Unquoted strings with colons
        - Spanish/unicode descriptions
        """
        lines = content.split('\n')
        cleaned_lines = []
        skip_block = False

        for line in lines:
            # Skip block scalar content (lines starting with >)
            if skip_block:
                if line.strip() and not line.startswith(' '):
                    skip_block = False
                else:
                    continue

            # Detect block scalar start
            if ': >' in line or ':>' in line:
                # Replace block scalar with empty string
                cleaned_lines.append(line.split(':')[0] + ': ""')
                skip_block = True
                continue

            # Fix description lines with problematic content
            if 'description:' in line.lower():
                match = re.match(r'^(\s*description:\s*)(.+)$', line, re.IGNORECASE)
                if match:
                    indent = match.group(1)
                    value = match.group(2).strip()
                    # Quote the value if not already quoted
                    if value and not (value.startswith('"') or value.startswith("'")):
                        value = value.replace('"', '\\"')
                        line = f'{indent}"{value}"'

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _count_endpoints(self, spec: Dict[str, Any]) -> int:
        """Count endpoints in spec."""
        paths = spec.get("paths", {})
        count = 0
        for path_item in paths.values():
            if isinstance(path_item, dict):
                for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
                    if method in path_item:
                        count += 1
        return count

    def _count_entities(self, spec: Dict[str, Any]) -> int:
        """Estimate entity count from schemas."""
        schemas = spec.get("components", {}).get("schemas", {})
        # Count schemas that look like entities (have properties, not enums)
        entity_count = 0
        for name, schema in schemas.items():
            if isinstance(schema, dict):
                if "properties" in schema and "enum" not in schema:
                    # Check if it looks like an entity (has id, created_at, etc.)
                    props = schema.get("properties", {})
                    if any(p in props for p in ["id", "created_at", "name"]):
                        entity_count += 1
        return entity_count

    def _count_schemas(self, spec: Dict[str, Any]) -> int:
        """Count total schemas."""
        return len(spec.get("components", {}).get("schemas", {}))

    def _detect_circular_refs(self, spec: Dict[str, Any]) -> bool:
        """Detect circular references in schemas."""
        schemas = spec.get("components", {}).get("schemas", {})

        def find_refs(obj, path=None):
            """Find all $ref in an object."""
            if path is None:
                path = []
            refs = []
            if isinstance(obj, dict):
                if "$ref" in obj:
                    refs.append(obj["$ref"])
                for k, v in obj.items():
                    refs.extend(find_refs(v, path + [k]))
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    refs.extend(find_refs(v, path + [str(i)]))
            return refs

        # Build reference graph
        for name, schema in schemas.items():
            refs = find_refs(schema)
            for ref in refs:
                if f"#/components/schemas/{name}" in ref:
                    return True  # Self-reference
                # Could implement full cycle detection, but self-ref is most common

        return False

    def _detect_polymorphism(self, spec: Dict[str, Any]) -> bool:
        """Detect polymorphic schemas (oneOf, anyOf, allOf)."""
        content = json.dumps(spec) if isinstance(spec, dict) else str(spec)
        return any(kw in content for kw in ['"oneOf"', '"anyOf"', '"allOf"'])

    def _detect_external_refs(self, spec: Dict[str, Any]) -> bool:
        """Detect external references."""
        content = json.dumps(spec) if isinstance(spec, dict) else str(spec)
        # Look for refs that aren't local
        external_patterns = [
            r'\$ref.*http',
            r'\$ref.*\.yaml',
            r'\$ref.*\.json',
        ]
        return any(re.search(p, content) for p in external_patterns)

    def _compute_complexity_score(
        self,
        endpoints: int,
        entities: int,
        schemas: int,
        has_circular: bool,
        has_poly: bool,
        has_external: bool
    ) -> float:
        """Compute complexity score (0-1)."""
        score = 0.0

        # Size-based complexity
        score += min(0.3, endpoints * 0.01)
        score += min(0.2, entities * 0.02)
        score += min(0.1, schemas * 0.003)

        # Feature-based complexity
        if has_circular:
            score += 0.15
        if has_poly:
            score += 0.15
        if has_external:
            score += 0.1

        return min(1.0, score)

    def _estimate_processing_time(
        self,
        endpoints: int,
        entities: int,
        schemas: int,
        has_circular: bool,
        has_poly: bool,
        has_external: bool
    ) -> int:
        """Estimate processing time in milliseconds."""
        c = self._time_coefficients

        time_ms = c["base"]
        time_ms += endpoints * c["per_endpoint"]
        time_ms += entities * c["per_entity"]
        time_ms += schemas * c["per_schema"]

        if has_circular:
            time_ms += c["circular_ref_penalty"]
        if has_poly:
            time_ms += c["polymorphism_penalty"]
        if has_external:
            time_ms += c["external_ref_penalty"]

        return int(time_ms)

    def record_processing_result(
        self,
        spec_complexity: SpecComplexity,
        actual_time_ms: int,
        success: bool,
        ir_quality_score: float,
        error_message: Optional[str] = None
    ):
        """
        Record actual processing results for learning.

        Args:
            spec_complexity: Original complexity analysis
            actual_time_ms: Actual processing time
            success: Whether processing succeeded
            ir_quality_score: Quality score of generated IR (0-1)
            error_message: Error message if failed
        """
        result = ProcessingResult(
            spec_id=spec_complexity.spec_id,
            actual_time_ms=actual_time_ms,
            success=success,
            ir_quality_score=ir_quality_score,
            error_message=error_message
        )

        # Store for learning
        sample = {
            "spec_id": spec_complexity.spec_id,
            "complexity": spec_complexity,
            "result": result,
            "estimation_error": actual_time_ms - spec_complexity.estimated_processing_ms
        }
        self._processing_samples.append(sample)

        # Update time model
        self._update_time_model(spec_complexity, actual_time_ms)

        # Persist to Neo4j
        self._persist_result(spec_complexity, result)

        self.logger.info(
            f"Recorded processing: {spec_complexity.spec_id} - "
            f"estimated {spec_complexity.estimated_processing_ms}ms, "
            f"actual {actual_time_ms}ms "
            f"({'✓' if success else '✗'})"
        )

    def _update_time_model(self, complexity: SpecComplexity, actual_time: int):
        """Update time estimation model based on actual results."""
        # Simple exponential moving average for coefficients
        alpha = 0.1  # Learning rate

        estimated = complexity.estimated_processing_ms
        error_ratio = actual_time / max(estimated, 1)

        # Adjust base if consistently under/over
        if len(self._processing_samples) >= 5:
            recent_errors = [
                s["estimation_error"]
                for s in self._processing_samples[-5:]
            ]
            avg_error = sum(recent_errors) / len(recent_errors)

            if abs(avg_error) > 5000:  # >5s average error
                adjustment = avg_error * 0.1
                self._time_coefficients["base"] = int(
                    self._time_coefficients["base"] + adjustment
                )
                self.logger.info(
                    f"Adjusted base time estimate by {adjustment:.0f}ms"
                )

    def _persist_result(self, complexity: SpecComplexity, result: ProcessingResult):
        """Persist processing result to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (s:SpecProcessing {
                        spec_id: $spec_id,
                        path: $path,
                        endpoints: $endpoints,
                        entities: $entities,
                        complexity_score: $complexity,
                        estimated_time_ms: $estimated,
                        actual_time_ms: $actual,
                        success: $success,
                        ir_quality: $quality,
                        error_message: $error,
                        processed_at: datetime()
                    })
                """, {
                    "spec_id": complexity.spec_id,
                    "path": complexity.path,
                    "endpoints": complexity.endpoint_count,
                    "entities": complexity.entity_count,
                    "complexity": complexity.complexity_score,
                    "estimated": complexity.estimated_processing_ms,
                    "actual": result.actual_time_ms,
                    "success": result.success,
                    "quality": result.ir_quality_score,
                    "error": result.error_message
                })
        except Exception as e:
            self.logger.warning(f"Failed to persist result: {e}")

    def get_learning_insights(self) -> List[SpecLearningInsight]:
        """
        Get learning insights from accumulated data.

        Returns:
            List of insights about spec processing patterns
        """
        insights = []

        if not self._processing_samples:
            return insights

        # Insight 1: Estimation accuracy
        errors = [abs(s["estimation_error"]) for s in self._processing_samples]
        avg_error = sum(errors) / len(errors)
        insights.append(SpecLearningInsight(
            insight_type="estimation_accuracy",
            description=f"Average estimation error: {avg_error/1000:.1f}s",
            affected_specs=len(self._processing_samples),
            avg_time_impact_ms=int(avg_error),
            recommendation="Time estimates are being refined with each run"
        ))

        # Insight 2: Failure patterns
        failed = [s for s in self._processing_samples if not s["result"].success]
        if failed:
            insights.append(SpecLearningInsight(
                insight_type="failure_rate",
                description=f"{len(failed)}/{len(self._processing_samples)} specs failed processing",
                affected_specs=len(failed),
                avg_time_impact_ms=0,
                recommendation="Review failed specs for common patterns"
            ))

        # Insight 3: Complexity impact
        complex_specs = [
            s for s in self._processing_samples
            if s["complexity"].complexity_score > 0.5
        ]
        if complex_specs:
            avg_time = sum(s["result"].actual_time_ms for s in complex_specs) / len(complex_specs)
            insights.append(SpecLearningInsight(
                insight_type="complexity_impact",
                description=f"High-complexity specs average {avg_time/1000:.1f}s processing",
                affected_specs=len(complex_specs),
                avg_time_impact_ms=int(avg_time),
                recommendation="Consider breaking down complex specs"
            ))

        return insights

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        if not self._processing_samples:
            return {"total_processed": 0}

        successful = [s for s in self._processing_samples if s["result"].success]

        return {
            "total_processed": len(self._processing_samples),
            "success_count": len(successful),
            "success_rate": len(successful) / len(self._processing_samples),
            "avg_processing_time_ms": sum(
                s["result"].actual_time_ms for s in self._processing_samples
            ) / len(self._processing_samples),
            "avg_estimation_error_ms": sum(
                abs(s["estimation_error"]) for s in self._processing_samples
            ) / len(self._processing_samples),
            "time_coefficients": self._time_coefficients
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_spec_analyzer: Optional[SpecComplexityAnalyzer] = None


def get_spec_complexity_analyzer() -> SpecComplexityAnalyzer:
    """Get singleton instance of SpecComplexityAnalyzer."""
    global _spec_analyzer
    if _spec_analyzer is None:
        import os
        _spec_analyzer = SpecComplexityAnalyzer(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _spec_analyzer
