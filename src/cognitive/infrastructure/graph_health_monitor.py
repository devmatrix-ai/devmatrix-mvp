"""
Graph Health Monitor
====================
Sprint: Infrastructure Improvements (Fase 4)
Date: 2025-11-29

Provides:
- Real-time graph health metrics
- Anomaly detection for node/relationship counts
- Performance monitoring for common queries
- Alerting thresholds and notifications
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from neo4j import GraphDatabase


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    NODE_COUNT = "node_count"
    RELATIONSHIP_COUNT = "relationship_count"
    QUERY_LATENCY = "query_latency"
    ORPHAN_NODES = "orphan_nodes"
    SCHEMA_VERSION = "schema_version"
    CONSTRAINT_VIOLATIONS = "constraint_violations"


@dataclass
class HealthMetric:
    """Represents a single health metric."""
    name: str
    metric_type: MetricType
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HealthReport:
    """Complete health report for the graph."""
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    timestamp: datetime
    schema_version: int
    node_count: int
    relationship_count: int
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "schema_version": self.schema_version,
            "node_count": self.node_count,
            "relationship_count": self.relationship_count,
            "metrics": [
                {
                    "name": m.name,
                    "type": m.metric_type.value,
                    "value": m.value,
                    "unit": m.unit,
                    "status": m.status.value,
                    "message": m.message
                }
                for m in self.metrics
            ],
            "recommendations": self.recommendations
        }


class GraphHealthMonitor:
    """
    Monitors Neo4j graph health and provides metrics.

    Usage:
        monitor = GraphHealthMonitor(driver, database)
        report = monitor.check_health()
        print(report.overall_status)
    """

    # Default thresholds
    DEFAULT_THRESHOLDS = {
        "orphan_nodes_warning": 100,
        "orphan_nodes_critical": 1000,
        "query_latency_warning_ms": 100,
        "query_latency_critical_ms": 500,
        "node_drift_warning_percent": 5,
        "node_drift_critical_percent": 20,
    }

    def __init__(
        self,
        driver,
        database: str,
        thresholds: Optional[Dict[str, float]] = None,
        on_alert: Optional[Callable[[HealthMetric], None]] = None
    ):
        self.driver = driver
        self.database = database
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.on_alert = on_alert
        self._baseline: Optional[Dict[str, int]] = None

    def check_health(self, include_performance: bool = True) -> HealthReport:
        """
        Run a complete health check on the graph.

        Args:
            include_performance: If True, run query latency tests

        Returns:
            HealthReport with all metrics and recommendations
        """
        metrics = []

        with self.driver.session(database=self.database) as session:
            # 1. Schema version check
            metrics.append(self._check_schema_version(session))

            # 2. Node counts by label
            node_metrics = self._check_node_counts(session)
            metrics.extend(node_metrics)

            # 3. Relationship counts
            rel_metrics = self._check_relationship_counts(session)
            metrics.extend(rel_metrics)

            # 4. Orphan nodes
            metrics.append(self._check_orphan_nodes(session))

            # 5. Constraint violations
            metrics.append(self._check_constraints(session))

            # 6. Query performance (optional)
            if include_performance:
                metrics.append(self._check_query_latency(session))

            # Calculate totals
            total_nodes = sum(
                int(m.value) for m in metrics
                if m.metric_type == MetricType.NODE_COUNT
            )
            total_rels = sum(
                int(m.value) for m in metrics
                if m.metric_type == MetricType.RELATIONSHIP_COUNT
            )

            # Get schema version
            schema_version = next(
                (int(m.value) for m in metrics
                 if m.metric_type == MetricType.SCHEMA_VERSION),
                0
            )

        # Determine overall status
        overall_status = self._calculate_overall_status(metrics)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)

        # Trigger alerts for critical/warning metrics
        for metric in metrics:
            if metric.status in (HealthStatus.WARNING, HealthStatus.CRITICAL):
                if self.on_alert:
                    self.on_alert(metric)

        return HealthReport(
            overall_status=overall_status,
            metrics=metrics,
            timestamp=datetime.now(),
            schema_version=schema_version,
            node_count=total_nodes,
            relationship_count=total_rels,
            recommendations=recommendations
        )

    def _check_schema_version(self, session) -> HealthMetric:
        """Check graph schema version."""
        query = """
        MATCH (v:GraphSchemaVersion {singleton: true})
        RETURN v.current_version as version, v.last_migration as last_migration
        """
        result = session.run(query)
        record = result.single()

        if not record:
            return HealthMetric(
                name="Schema Version",
                metric_type=MetricType.SCHEMA_VERSION,
                value=0,
                unit="version",
                status=HealthStatus.CRITICAL,
                message="GraphSchemaVersion singleton not found"
            )

        return HealthMetric(
            name="Schema Version",
            metric_type=MetricType.SCHEMA_VERSION,
            value=record["version"],
            unit="version",
            status=HealthStatus.HEALTHY,
            message=f"Last migration: {record['last_migration']}"
        )

    def _check_node_counts(self, session) -> List[HealthMetric]:
        """Check node counts by label."""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        result = session.run(query)
        metrics = []

        for record in result:
            label = record["label"]
            count = record["count"]

            # Check against baseline if exists
            status = HealthStatus.HEALTHY
            message = ""

            if self._baseline and label in self._baseline:
                baseline = self._baseline[label]
                drift = abs(count - baseline) / baseline * 100 if baseline > 0 else 0

                if drift > self.thresholds["node_drift_critical_percent"]:
                    status = HealthStatus.CRITICAL
                    message = f"Node count drift: {drift:.1f}% from baseline"
                elif drift > self.thresholds["node_drift_warning_percent"]:
                    status = HealthStatus.WARNING
                    message = f"Node count drift: {drift:.1f}% from baseline"

            metrics.append(HealthMetric(
                name=f"Node Count: {label}",
                metric_type=MetricType.NODE_COUNT,
                value=count,
                unit="nodes",
                status=status,
                message=message
            ))

        return metrics

    def _check_relationship_counts(self, session) -> List[HealthMetric]:
        """Check relationship counts by type."""
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        LIMIT 20
        """
        result = session.run(query)
        metrics = []

        for record in result:
            rel_type = record["type"]
            count = record["count"]

            metrics.append(HealthMetric(
                name=f"Relationship Count: {rel_type}",
                metric_type=MetricType.RELATIONSHIP_COUNT,
                value=count,
                unit="relationships",
                status=HealthStatus.HEALTHY,
                message=""
            ))

        return metrics

    def _check_orphan_nodes(self, session) -> HealthMetric:
        """Check for orphan nodes (nodes without relationships)."""
        query = """
        MATCH (n)
        WHERE NOT (n)--()
          AND NOT n:GraphSchemaVersion
          AND NOT n:MigrationRun
          AND NOT n:MigrationCheckpoint
        RETURN count(n) as orphan_count
        """
        result = session.run(query)
        orphan_count = result.single()["orphan_count"]

        status = HealthStatus.HEALTHY
        message = ""

        if orphan_count > self.thresholds["orphan_nodes_critical"]:
            status = HealthStatus.CRITICAL
            message = "High number of orphan nodes detected"
        elif orphan_count > self.thresholds["orphan_nodes_warning"]:
            status = HealthStatus.WARNING
            message = "Orphan nodes detected - consider cleanup"

        return HealthMetric(
            name="Orphan Nodes",
            metric_type=MetricType.ORPHAN_NODES,
            value=orphan_count,
            unit="nodes",
            status=status,
            threshold_warning=self.thresholds["orphan_nodes_warning"],
            threshold_critical=self.thresholds["orphan_nodes_critical"],
            message=message
        )

    def _check_constraints(self, session) -> HealthMetric:
        """Check for constraint violations in IR nodes."""
        # Check for common violations
        violations = 0
        messages = []

        # Check DomainModelIR without entities
        query = """
        MATCH (dm:DomainModelIR)
        WHERE NOT (dm)-[:HAS_ENTITY]->(:Entity)
        RETURN count(dm) as count
        """
        result = session.run(query)
        dm_violations = result.single()["count"]
        if dm_violations > 0:
            violations += dm_violations
            messages.append(f"{dm_violations} DomainModelIR without entities")

        # Check APIModelIR without endpoints
        query = """
        MATCH (api:APIModelIR)
        WHERE NOT (api)-[:HAS_ENDPOINT]->(:Endpoint)
        RETURN count(api) as count
        """
        result = session.run(query)
        api_violations = result.single()["count"]
        if api_violations > 0:
            violations += api_violations
            messages.append(f"{api_violations} APIModelIR without endpoints")

        status = HealthStatus.HEALTHY if violations == 0 else HealthStatus.WARNING

        return HealthMetric(
            name="Constraint Violations",
            metric_type=MetricType.CONSTRAINT_VIOLATIONS,
            value=violations,
            unit="violations",
            status=status,
            message="; ".join(messages) if messages else "No violations"
        )

    def _check_query_latency(self, session) -> HealthMetric:
        """Test query latency with a representative query."""
        import time

        # Run a typical query and measure time
        query = """
        MATCH (a:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(d:DomainModelIR)
              -[:HAS_ENTITY]->(e:Entity)-[:HAS_ATTRIBUTE]->(attr:Attribute)
        RETURN count(*) as count
        """

        start = time.perf_counter()
        session.run(query).consume()
        latency_ms = (time.perf_counter() - start) * 1000

        status = HealthStatus.HEALTHY
        message = ""

        if latency_ms > self.thresholds["query_latency_critical_ms"]:
            status = HealthStatus.CRITICAL
            message = "Query latency is critically high"
        elif latency_ms > self.thresholds["query_latency_warning_ms"]:
            status = HealthStatus.WARNING
            message = "Query latency is elevated"

        return HealthMetric(
            name="Query Latency",
            metric_type=MetricType.QUERY_LATENCY,
            value=round(latency_ms, 2),
            unit="ms",
            status=status,
            threshold_warning=self.thresholds["query_latency_warning_ms"],
            threshold_critical=self.thresholds["query_latency_critical_ms"],
            message=message
        )

    def _calculate_overall_status(self, metrics: List[HealthMetric]) -> HealthStatus:
        """Calculate overall health status from individual metrics."""
        statuses = [m.status for m in metrics]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def _generate_recommendations(self, metrics: List[HealthMetric]) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []

        for metric in metrics:
            if metric.status == HealthStatus.CRITICAL:
                if metric.metric_type == MetricType.ORPHAN_NODES:
                    recommendations.append(
                        f"Run orphan node cleanup: {int(metric.value)} nodes need attention"
                    )
                elif metric.metric_type == MetricType.QUERY_LATENCY:
                    recommendations.append(
                        "Consider adding indexes or optimizing queries"
                    )
                elif metric.metric_type == MetricType.SCHEMA_VERSION:
                    recommendations.append(
                        "Run schema version initialization migration"
                    )

            elif metric.status == HealthStatus.WARNING:
                if metric.metric_type == MetricType.CONSTRAINT_VIOLATIONS:
                    recommendations.append(
                        f"Review data quality: {metric.message}"
                    )
                elif "drift" in metric.message.lower():
                    recommendations.append(
                        f"Investigate node count changes for {metric.name}"
                    )

        return recommendations

    def set_baseline(self):
        """Set current node counts as baseline for drift detection."""
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            """
            result = session.run(query)
            self._baseline = {
                record["label"]: record["count"]
                for record in result
            }

    def get_baseline(self) -> Optional[Dict[str, int]]:
        """Get current baseline."""
        return self._baseline


def create_health_check_endpoint():
    """
    Factory function to create a health check callable.

    Usage in FastAPI:
        @app.get("/health/graph")
        async def graph_health():
            return create_health_check_endpoint()()
    """
    from src.cognitive.config.settings import settings

    def check():
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        try:
            monitor = GraphHealthMonitor(driver, settings.neo4j_database)
            report = monitor.check_health()
            return report.to_dict()
        finally:
            driver.close()

    return check
