#!/usr/bin/env python3
"""
008_validate_graph_shape_contract.py
Task IA.7: Graph Shape Contract Validation

Comprehensive validation of Neo4j graph against GRAPH_SHAPE_CONTRACT.yml.

Features:
- Node label existence and property validation
- Relationship type and cardinality validation
- Cross-node integrity checks
- Temporal metadata validation
- ID format validation
- Schema version coherence

Usage:
    PYTHONPATH=. python scripts/migrations/neo4j/008_validate_graph_shape_contract.py
    PYTHONPATH=. python scripts/migrations/neo4j/008_validate_graph_shape_contract.py --strict
    PYTHONPATH=. python scripts/migrations/neo4j/008_validate_graph_shape_contract.py --fix-issues
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from neo4j import GraphDatabase

from src.cognitive.config.settings import settings


# =============================================================================
# DATA CLASSES
# =============================================================================


class Severity(Enum):
    """Validation issue severity."""

    CRITICAL = "CRITICAL"  # Breaks integrity
    ERROR = "ERROR"  # Violates contract
    WARNING = "WARNING"  # Best practice violation
    INFO = "INFO"  # Informational


@dataclass
class ValidationIssue:
    """A single validation issue."""

    rule: str
    severity: Severity
    count: int = 0
    details: str = ""
    examples: list = field(default_factory=list)
    fixable: bool = False


@dataclass
class ContractValidationReport:
    """Complete validation report."""

    timestamp: str
    schema_version: int
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL and i.count > 0)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR and i.count > 0)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING and i.count > 0)

    @property
    def passed(self) -> bool:
        return self.critical_count == 0 and self.error_count == 0

    def add(self, issue: ValidationIssue):
        self.issues.append(issue)


# =============================================================================
# CONTRACT RULES
# =============================================================================


class GraphShapeContractValidator:
    """Validates Neo4j graph against Graph Shape Contract."""

    def __init__(self, driver, database: str):
        self.driver = driver
        self.database = database

    def validate_all(self, strict: bool = False) -> ContractValidationReport:
        """Run all contract validations."""
        report = ContractValidationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            schema_version=self._get_schema_version(),
        )

        with self.driver.session(database=self.database) as session:
            # Get stats first
            report.stats = session.execute_read(self._get_graph_stats)

            # Infrastructure validations
            report.add(session.execute_read(self._validate_schema_singleton))
            report.add(session.execute_read(self._validate_schema_version_coherence))
            report.add(session.execute_read(self._validate_migration_run_integrity))

            # ApplicationIR hierarchy
            report.add(session.execute_read(self._validate_application_ir_completeness))
            report.add(session.execute_read(self._validate_domain_model_has_entities))
            report.add(session.execute_read(self._validate_entities_have_attributes))
            report.add(session.execute_read(self._validate_api_model_has_endpoints))

            # ID format validations
            report.add(session.execute_read(self._validate_entity_id_format))
            report.add(session.execute_read(self._validate_attribute_id_format))
            report.add(session.execute_read(self._validate_endpoint_id_format))

            # Relationship validations
            report.add(session.execute_read(self._validate_targets_entity_coverage))
            report.add(session.execute_read(self._validate_no_duplicate_relationships))

            # Temporal metadata
            report.add(session.execute_read(self._validate_temporal_metadata))

            # Orphan nodes
            report.add(session.execute_read(self._validate_no_orphan_nodes))

            # Strict mode validations
            if strict:
                report.add(session.execute_read(self._validate_attribute_types))
                report.add(session.execute_read(self._validate_endpoint_methods))

        return report

    def _get_schema_version(self) -> int:
        """Get current schema version."""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (v:GraphSchemaVersion {singleton: true}) RETURN v.current_version as version"
            )
            record = result.single()
            return record["version"] if record else 0

    # =========================================================================
    # STAT QUERIES
    # =========================================================================

    def _get_graph_stats(self, tx) -> dict:
        """Get overall graph statistics."""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        result = tx.run(query)
        stats = {"nodes": {}, "total_nodes": 0}
        for record in result:
            stats["nodes"][record["label"]] = record["count"]
            stats["total_nodes"] += record["count"]

        # Relationship stats
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(r) as count
        ORDER BY count DESC
        """
        rel_result = tx.run(rel_query)
        stats["relationships"] = {}
        stats["total_relationships"] = 0
        for record in rel_result:
            stats["relationships"][record["rel_type"]] = record["count"]
            stats["total_relationships"] += record["count"]

        return stats

    # =========================================================================
    # INFRASTRUCTURE VALIDATIONS
    # =========================================================================

    def _validate_schema_singleton(self, tx) -> ValidationIssue:
        """Contract: GraphSchemaVersion must be singleton."""
        query = """
        MATCH (v:GraphSchemaVersion)
        RETURN count(v) as count
        """
        result = tx.run(query)
        record = result.single()
        count = record["count"] if record else 0

        if count == 0:
            return ValidationIssue(
                rule="GraphSchemaVersion singleton exists",
                severity=Severity.CRITICAL,
                count=1,
                details="No GraphSchemaVersion node found",
            )
        elif count > 1:
            return ValidationIssue(
                rule="GraphSchemaVersion singleton exists",
                severity=Severity.CRITICAL,
                count=count - 1,
                details=f"Found {count} GraphSchemaVersion nodes, expected 1",
            )

        return ValidationIssue(
            rule="GraphSchemaVersion singleton exists",
            severity=Severity.INFO,
            count=0,
            details="Singleton verified",
        )

    def _validate_schema_version_coherence(self, tx) -> ValidationIssue:
        """Contract: Schema version matches last migration."""
        query = """
        MATCH (v:GraphSchemaVersion {singleton: true})
        OPTIONAL MATCH (m:MigrationRun {migration_id: v.last_migration})
        RETURN
            v.current_version as schema_version,
            v.last_migration as last_migration,
            m.schema_version_after as migration_version,
            m IS NOT NULL as migration_exists
        """
        result = tx.run(query)
        record = result.single()

        if not record:
            return ValidationIssue(
                rule="Schema version coherence",
                severity=Severity.CRITICAL,
                count=1,
                details="No GraphSchemaVersion found",
            )

        if not record["migration_exists"]:
            return ValidationIssue(
                rule="Schema version coherence",
                severity=Severity.ERROR,
                count=1,
                details=f"MigrationRun '{record['last_migration']}' not found",
            )

        if record["schema_version"] != record["migration_version"]:
            return ValidationIssue(
                rule="Schema version coherence",
                severity=Severity.ERROR,
                count=1,
                details=f"Schema v{record['schema_version']} != Migration v{record['migration_version']}",
            )

        return ValidationIssue(
            rule="Schema version coherence",
            severity=Severity.INFO,
            count=0,
            details=f"Schema v{record['schema_version']} coherent",
        )

    def _validate_migration_run_integrity(self, tx) -> ValidationIssue:
        """Contract: All MigrationRun nodes have RESULTED_IN_VERSION."""
        query = """
        MATCH (m:MigrationRun)
        WHERE NOT (m)-[:RESULTED_IN_VERSION]->(:GraphSchemaVersion)
        RETURN m.migration_id as migration_id
        """
        result = tx.run(query)
        orphan_migrations = [r["migration_id"] for r in result]

        return ValidationIssue(
            rule="MigrationRun → RESULTED_IN_VERSION → GraphSchemaVersion",
            severity=Severity.ERROR if orphan_migrations else Severity.INFO,
            count=len(orphan_migrations),
            details="Orphan migrations without version link",
            examples=orphan_migrations[:5],
        )

    # =========================================================================
    # APPLICATION IR HIERARCHY VALIDATIONS
    # =========================================================================

    def _validate_application_ir_completeness(self, tx) -> ValidationIssue:
        """Contract: ApplicationIR must have DomainModel AND APIModel."""
        query = """
        MATCH (app:ApplicationIR)
        OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
        OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(am:APIModelIR)
        WITH app,
             dm IS NOT NULL as has_domain,
             am IS NOT NULL as has_api
        WHERE NOT has_domain OR NOT has_api
        RETURN app.app_id as app_id, has_domain, has_api
        LIMIT 10
        """
        result = tx.run(query)
        incomplete = [
            {
                "app_id": r["app_id"],
                "missing": ("DomainModel" if not r["has_domain"] else "")
                + ("APIModel" if not r["has_api"] else ""),
            }
            for r in result
        ]

        return ValidationIssue(
            rule="ApplicationIR has DomainModelIR AND APIModelIR",
            severity=Severity.WARNING if incomplete else Severity.INFO,
            count=len(incomplete),
            details="ApplicationIR missing required sub-models",
            examples=[f"{i['app_id']}: missing {i['missing']}" for i in incomplete],
        )

    def _validate_domain_model_has_entities(self, tx) -> ValidationIssue:
        """Contract: DomainModelIR must have ≥1 Entity."""
        query = """
        MATCH (dm:DomainModelIR)
        WHERE NOT (dm)-[:HAS_ENTITY]->(:Entity)
        RETURN dm.app_id as app_id
        LIMIT 10
        """
        result = tx.run(query)
        empty_domains = [r["app_id"] for r in result]

        return ValidationIssue(
            rule="DomainModelIR has ≥1 Entity",
            severity=Severity.ERROR if empty_domains else Severity.INFO,
            count=len(empty_domains),
            details="DomainModelIR without entities",
            examples=empty_domains[:5],
        )

    def _validate_entities_have_attributes(self, tx) -> ValidationIssue:
        """Contract: Entity must have ≥1 Attribute."""
        query = """
        MATCH (e:Entity)
        WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
        RETURN e.name as entity_name, e.entity_id as entity_id
        LIMIT 10
        """
        result = tx.run(query)
        empty_entities = [r["entity_name"] for r in result]

        return ValidationIssue(
            rule="Entity has ≥1 Attribute",
            severity=Severity.ERROR if empty_entities else Severity.INFO,
            count=len(empty_entities),
            details="Entities without attributes",
            examples=empty_entities[:5],
        )

    def _validate_api_model_has_endpoints(self, tx) -> ValidationIssue:
        """Contract: APIModelIR must have ≥1 Endpoint."""
        query = """
        MATCH (api:APIModelIR)
        WHERE NOT (api)-[:HAS_ENDPOINT]->(:Endpoint)
        RETURN api.app_id as app_id
        LIMIT 10
        """
        result = tx.run(query)
        empty_apis = [r["app_id"] for r in result]

        return ValidationIssue(
            rule="APIModelIR has ≥1 Endpoint",
            severity=Severity.ERROR if empty_apis else Severity.INFO,
            count=len(empty_apis),
            details="APIModelIR without endpoints",
            examples=empty_apis[:5],
        )

    # =========================================================================
    # ID FORMAT VALIDATIONS
    # =========================================================================

    def _validate_entity_id_format(self, tx) -> ValidationIssue:
        """Contract: entity_id format: {app_id}|entity|{name}."""
        # Check entities with wrong format
        query = """
        MATCH (e:Entity)
        WHERE NOT e.entity_id CONTAINS '|entity|'
        RETURN e.entity_id as id, e.name as name
        LIMIT 10
        """
        result = tx.run(query)
        invalid = [r["id"] for r in result]

        return ValidationIssue(
            rule="Entity ID format: {app_id}|entity|{name}",
            severity=Severity.WARNING if invalid else Severity.INFO,
            count=len(invalid),
            details="Invalid entity_id format",
            examples=invalid[:5],
            fixable=True,
        )

    def _validate_attribute_id_format(self, tx) -> ValidationIssue:
        """Contract: attribute_id format: {entity_id}|attr|{name}."""
        query = """
        MATCH (a:Attribute)
        WHERE NOT a.attribute_id CONTAINS '|attr|'
        RETURN a.attribute_id as id, a.name as name
        LIMIT 10
        """
        result = tx.run(query)
        invalid = [r["id"] for r in result]

        return ValidationIssue(
            rule="Attribute ID format: {entity_id}|attr|{name}",
            severity=Severity.WARNING if invalid else Severity.INFO,
            count=len(invalid),
            details="Invalid attribute_id format",
            examples=invalid[:5],
            fixable=True,
        )

    def _validate_endpoint_id_format(self, tx) -> ValidationIssue:
        """Contract: endpoint_id format: {app_id}|endpoint|{method}|{path}."""
        query = """
        MATCH (e:Endpoint)
        WHERE NOT e.endpoint_id CONTAINS '|endpoint|'
        RETURN e.endpoint_id as id, e.path as path
        LIMIT 10
        """
        result = tx.run(query)
        invalid = [r["id"] for r in result]

        return ValidationIssue(
            rule="Endpoint ID format: {app_id}|endpoint|{method}|{path}",
            severity=Severity.WARNING if invalid else Severity.INFO,
            count=len(invalid),
            details="Invalid endpoint_id format",
            examples=invalid[:5],
            fixable=True,
        )

    # =========================================================================
    # RELATIONSHIP VALIDATIONS
    # =========================================================================

    def _validate_targets_entity_coverage(self, tx) -> ValidationIssue:
        """Contract: TARGETS_ENTITY coverage ≥80%."""
        query = """
        MATCH (e:Endpoint)
        WHERE e.api_model_id IS NOT NULL
        WITH count(e) as total
        MATCH (e:Endpoint)-[:TARGETS_ENTITY]->(:Entity)
        WITH total, count(DISTINCT e) as linked
        RETURN total, linked,
               CASE WHEN total > 0 THEN (100.0 * linked / total) ELSE 0 END as coverage
        """
        result = tx.run(query)
        record = result.single()

        if not record:
            return ValidationIssue(
                rule="TARGETS_ENTITY coverage ≥80%",
                severity=Severity.WARNING,
                count=1,
                details="No endpoints found",
            )

        coverage = record["coverage"]
        total = record["total"]
        linked = record["linked"]

        severity = Severity.INFO if coverage >= 80 else Severity.WARNING

        return ValidationIssue(
            rule="TARGETS_ENTITY coverage ≥80%",
            severity=severity,
            count=0 if coverage >= 80 else total - linked,
            details=f"Coverage: {coverage:.1f}% ({linked}/{total} endpoints)",
        )

    def _validate_no_duplicate_relationships(self, tx) -> ValidationIssue:
        """Contract: No duplicate relationships of same type between same nodes."""
        query = """
        MATCH (a)-[r]->(b)
        WITH a, b, type(r) as rel_type, count(r) as rel_count
        WHERE rel_count > 1
        RETURN labels(a)[0] as from_label, labels(b)[0] as to_label,
               rel_type, rel_count
        LIMIT 10
        """
        result = tx.run(query)
        duplicates = [
            f"{r['from_label']}-[{r['rel_type']}x{r['rel_count']}]->{r['to_label']}"
            for r in result
        ]

        return ValidationIssue(
            rule="No duplicate relationships",
            severity=Severity.WARNING if duplicates else Severity.INFO,
            count=len(duplicates),
            details="Duplicate relationships found",
            examples=duplicates[:5],
            fixable=True,
        )

    # =========================================================================
    # TEMPORAL METADATA VALIDATIONS
    # =========================================================================

    def _validate_temporal_metadata(self, tx) -> ValidationIssue:
        """Contract: Key nodes have created_at and updated_at."""
        query = """
        MATCH (n)
        WHERE (n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter)
          AND (n.created_at IS NULL OR n.updated_at IS NULL)
        RETURN labels(n)[0] as label, count(n) as count
        """
        result = tx.run(query)
        missing = {r["label"]: r["count"] for r in result}
        total = sum(missing.values())

        return ValidationIssue(
            rule="Temporal metadata (created_at, updated_at)",
            severity=Severity.WARNING if total > 0 else Severity.INFO,
            count=total,
            details=str(missing) if missing else "All nodes have temporal metadata",
            fixable=True,
        )

    # =========================================================================
    # ORPHAN NODE VALIDATION
    # =========================================================================

    def _validate_no_orphan_nodes(self, tx) -> ValidationIssue:
        """Contract: No orphan nodes (except infrastructure)."""
        query = """
        MATCH (n)
        WHERE NOT (n)--()
          AND NOT n:GraphSchemaVersion
          AND NOT n:MigrationRun
          AND NOT n:MigrationCheckpoint
          AND NOT n:Pattern
          AND NOT n:SuccessfulCode
          AND NOT n:CodeGenerationError
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        LIMIT 10
        """
        result = tx.run(query)
        orphans = {r["label"]: r["count"] for r in result}
        total = sum(orphans.values())

        return ValidationIssue(
            rule="No orphan IR nodes",
            severity=Severity.WARNING if total > 0 else Severity.INFO,
            count=total,
            details=str(orphans) if orphans else "No orphan IR nodes",
            fixable=True,
        )

    # =========================================================================
    # STRICT MODE VALIDATIONS
    # =========================================================================

    def _validate_attribute_types(self, tx) -> ValidationIssue:
        """Strict: Attribute.type must be valid SQL type."""
        valid_types = {
            "UUID",
            "STRING",
            "TEXT",
            "INTEGER",
            "INT",
            "BIGINT",
            "FLOAT",
            "DOUBLE",
            "DECIMAL",
            "BOOLEAN",
            "BOOL",
            "DATE",
            "DATETIME",
            "TIMESTAMP",
            "TIME",
            "JSON",
            "JSONB",
            "ARRAY",
            "ENUM",
        }

        query = """
        MATCH (a:Attribute)
        WHERE a.type IS NOT NULL
        RETURN DISTINCT upper(a.type) as attr_type, count(*) as count
        """
        result = tx.run(query)
        invalid_types = []
        for r in result:
            if r["attr_type"] not in valid_types:
                invalid_types.append(f"{r['attr_type']} ({r['count']})")

        return ValidationIssue(
            rule="Attribute.type is valid SQL type",
            severity=Severity.WARNING if invalid_types else Severity.INFO,
            count=len(invalid_types),
            details="Invalid attribute types found",
            examples=invalid_types[:5],
        )

    def _validate_endpoint_methods(self, tx) -> ValidationIssue:
        """Strict: Endpoint.method must be valid HTTP method."""
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

        query = """
        MATCH (e:Endpoint)
        WHERE e.method IS NOT NULL AND NOT upper(e.method) IN $valid
        RETURN e.method as method, count(*) as count
        LIMIT 10
        """
        result = tx.run(query, valid=list(valid_methods))
        invalid = [f"{r['method']} ({r['count']})" for r in result]

        return ValidationIssue(
            rule="Endpoint.method is valid HTTP method",
            severity=Severity.WARNING if invalid else Severity.INFO,
            count=len(invalid),
            details="Invalid HTTP methods found",
            examples=invalid[:5],
        )


# =============================================================================
# REPORT FORMATTING
# =============================================================================


def format_report(report: ContractValidationReport) -> str:
    """Format validation report for console output."""
    lines = []
    lines.append("=" * 70)
    lines.append("Graph Shape Contract Validation (IA.7)")
    lines.append("=" * 70)
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append(f"Schema Version: {report.schema_version}")
    lines.append("")

    # Stats
    lines.append("📊 Graph Statistics")
    lines.append("-" * 50)
    lines.append(f"   Total Nodes: {report.stats.get('total_nodes', 0):,}")
    lines.append(f"   Total Relationships: {report.stats.get('total_relationships', 0):,}")
    lines.append("")

    # Top node types
    nodes = report.stats.get("nodes", {})
    top_nodes = sorted(nodes.items(), key=lambda x: -x[1])[:10]
    for label, count in top_nodes:
        lines.append(f"   {label}: {count:,}")
    lines.append("")

    # Validation Results
    lines.append("🔍 Contract Validation")
    lines.append("-" * 50)

    for issue in report.issues:
        if issue.count > 0:
            icon = {
                Severity.CRITICAL: "🚨",
                Severity.ERROR: "❌",
                Severity.WARNING: "⚠️",
                Severity.INFO: "ℹ️",
            }.get(issue.severity, "•")
        else:
            icon = "✅"

        lines.append(f"   {icon} {issue.rule}")
        if issue.count > 0:
            lines.append(f"      Count: {issue.count}")
            if issue.details:
                lines.append(f"      Details: {issue.details}")
            if issue.examples:
                lines.append(f"      Examples: {issue.examples[:3]}")
            if issue.fixable:
                lines.append("      [Fixable]")

    lines.append("")

    # Summary
    lines.append("=" * 70)
    lines.append("Summary")
    lines.append("=" * 70)

    if report.passed:
        lines.append("✅ All critical/error validations PASSED")
    else:
        if report.critical_count > 0:
            lines.append(f"🚨 {report.critical_count} CRITICAL issue(s)")
        if report.error_count > 0:
            lines.append(f"❌ {report.error_count} ERROR(s)")

    if report.warning_count > 0:
        lines.append(f"⚠️  {report.warning_count} WARNING(s)")

    lines.append("")

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================


def get_driver():
    """Create Neo4j driver from settings."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Validate Neo4j graph against Graph Shape Contract"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Run additional strict validations",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--fix-issues",
        action="store_true",
        help="Attempt to fix fixable issues (not implemented)",
    )
    args = parser.parse_args()

    driver = get_driver()
    database = settings.neo4j_database

    try:
        validator = GraphShapeContractValidator(driver, database)
        report = validator.validate_all(strict=args.strict)

        if args.json:
            import json

            output = {
                "timestamp": report.timestamp,
                "schema_version": report.schema_version,
                "passed": report.passed,
                "critical_count": report.critical_count,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
                "stats": report.stats,
                "issues": [
                    {
                        "rule": i.rule,
                        "severity": i.severity.value,
                        "count": i.count,
                        "details": i.details,
                        "examples": i.examples,
                        "fixable": i.fixable,
                    }
                    for i in report.issues
                ],
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_report(report))

        return 0 if report.passed else 1

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
