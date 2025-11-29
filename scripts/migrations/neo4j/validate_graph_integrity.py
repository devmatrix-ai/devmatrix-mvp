#!/usr/bin/env python3
"""
validate_graph_integrity.py
Task IA.6: Validation queries for graph cardinalities

Validates:
1. Entity nodes MUST have ≥1 Attribute
2. DomainModelIR nodes MUST have ≥1 Entity
3. APIModelIR nodes MUST have ≥1 Endpoint
4. ApplicationIR nodes MUST have DomainModelIR and APIModelIR
5. No orphan nodes (nodes without relationships)
6. Temporal metadata presence

Usage:
    PYTHONPATH=. python scripts/migrations/neo4j/validate_graph_integrity.py
    PYTHONPATH=. python scripts/migrations/neo4j/validate_graph_integrity.py --fix-orphans
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import Optional

from neo4j import GraphDatabase

from src.cognitive.config.settings import settings


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    count: int = 0
    details: str = ""
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class ValidationReport:
    """Full validation report."""

    results: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results if r.severity == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if not r.passed and r.severity == "WARNING")

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if not r.passed and r.severity == "ERROR")

    def add(self, result: ValidationResult):
        self.results.append(result)


def get_driver():
    """Create Neo4j driver from settings."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


# =============================================================================
# VALIDATION QUERIES
# =============================================================================


def validate_entities_have_attributes(tx) -> ValidationResult:
    """Check that all Entity nodes have at least one Attribute."""
    query = """
    MATCH (e:Entity)
    WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
    RETURN count(e) as invalid_count, collect(e.name)[..5] as examples
    """
    result = tx.run(query)
    record = result.single()
    count = record["invalid_count"] if record else 0
    examples = record["examples"] if record else []

    return ValidationResult(
        name="Entities must have ≥1 Attribute",
        passed=count == 0,
        count=count,
        details=f"Examples: {examples}" if examples else "",
        severity="ERROR",
    )


def validate_domain_models_have_entities(tx) -> ValidationResult:
    """Check that all DomainModelIR nodes have at least one Entity."""
    query = """
    MATCH (d:DomainModelIR)
    WHERE NOT (d)-[:HAS_ENTITY]->(:Entity)
    RETURN count(d) as invalid_count, collect(d.app_id)[..5] as examples
    """
    result = tx.run(query)
    record = result.single()
    count = record["invalid_count"] if record else 0
    examples = record["examples"] if record else []

    return ValidationResult(
        name="DomainModelIR must have ≥1 Entity",
        passed=count == 0,
        count=count,
        details=f"Examples: {examples}" if examples else "",
        severity="ERROR",
    )


def validate_api_models_have_endpoints(tx) -> ValidationResult:
    """Check that all APIModelIR nodes have at least one Endpoint."""
    query = """
    MATCH (a:APIModelIR)
    WHERE NOT (a)-[:HAS_ENDPOINT]->(:Endpoint)
    RETURN count(a) as invalid_count, collect(a.app_id)[..5] as examples
    """
    result = tx.run(query)
    record = result.single()
    count = record["invalid_count"] if record else 0
    examples = record["examples"] if record else []

    return ValidationResult(
        name="APIModelIR must have ≥1 Endpoint",
        passed=count == 0,
        count=count,
        details=f"Examples: {examples}" if examples else "",
        severity="ERROR",
    )


def validate_applications_have_models(tx) -> ValidationResult:
    """Check that ApplicationIR nodes have both DomainModelIR and APIModelIR."""
    query = """
    MATCH (app:ApplicationIR)
    OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
    OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(am:APIModelIR)
    WITH app,
         dm IS NOT NULL as has_domain,
         am IS NOT NULL as has_api
    WHERE NOT has_domain OR NOT has_api
    RETURN count(app) as invalid_count,
           sum(CASE WHEN NOT has_domain THEN 1 ELSE 0 END) as missing_domain,
           sum(CASE WHEN NOT has_api THEN 1 ELSE 0 END) as missing_api
    """
    result = tx.run(query)
    record = result.single()
    count = record["invalid_count"] if record else 0
    missing_domain = record["missing_domain"] if record else 0
    missing_api = record["missing_api"] if record else 0

    return ValidationResult(
        name="ApplicationIR must have DomainModelIR and APIModelIR",
        passed=count == 0,
        count=count,
        details=f"Missing domain: {missing_domain}, Missing API: {missing_api}",
        severity="WARNING",
    )


def validate_no_orphan_nodes(tx) -> ValidationResult:
    """Check for nodes without any relationships."""
    query = """
    MATCH (n)
    WHERE NOT (n)--()
      AND NOT n:GraphSchemaVersion
      AND NOT n:MigrationRun
      AND NOT n:MigrationCheckpoint
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    """
    result = tx.run(query)
    orphans = {record["label"]: record["count"] for record in result}
    total = sum(orphans.values())

    return ValidationResult(
        name="No orphan nodes (except infrastructure)",
        passed=total == 0,
        count=total,
        details=str(orphans) if orphans else "",
        severity="WARNING",
    )


def validate_temporal_metadata(tx) -> ValidationResult:
    """Check that key nodes have temporal metadata."""
    query = """
    MATCH (n)
    WHERE (n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter)
      AND n.created_at IS NULL
    RETURN labels(n)[0] as label, count(n) as count
    """
    result = tx.run(query)
    missing = {record["label"]: record["count"] for record in result}
    total = sum(missing.values())

    return ValidationResult(
        name="Nodes have temporal metadata",
        passed=total == 0,
        count=total,
        details=str(missing) if missing else "",
        severity="WARNING",
    )


def validate_schema_version_coherence(tx) -> ValidationResult:
    """Check that GraphSchemaVersion matches last MigrationRun."""
    query = """
    MATCH (v:GraphSchemaVersion {singleton: true})
    OPTIONAL MATCH (m:MigrationRun {migration_id: v.last_migration})
    RETURN
        v.current_version as schema_version,
        v.last_migration as last_migration,
        m IS NOT NULL as migration_exists,
        m.schema_version_after as migration_version
    """
    result = tx.run(query)
    record = result.single()

    if not record:
        return ValidationResult(
            name="GraphSchemaVersion singleton exists",
            passed=False,
            details="No GraphSchemaVersion singleton found",
            severity="ERROR",
        )

    migration_exists = record["migration_exists"]
    version_match = record["schema_version"] == record["migration_version"]
    passed = migration_exists and version_match

    return ValidationResult(
        name="Schema version coherence",
        passed=passed,
        details=f"Schema v{record['schema_version']}, last_migration: {record['last_migration']}",
        severity="ERROR" if not passed else "INFO",
    )


def get_graph_statistics(tx) -> dict:
    """Get overall graph statistics."""
    query = """
    MATCH (n)
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    """
    result = tx.run(query)
    return {record["label"]: record["count"] for record in result}


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Validate Neo4j graph integrity for IR schema"
    )
    parser.add_argument(
        "--fix-orphans",
        action="store_true",
        help="Delete orphan nodes (not implemented yet)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show graph statistics",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Graph Integrity Validation (IA.6)")
    print("=" * 70)
    print()

    driver = get_driver()
    database = settings.neo4j_database

    try:
        with driver.session(database=database) as session:
            # Statistics
            print("📊 Graph Statistics")
            print("-" * 50)
            stats = session.execute_read(get_graph_statistics)
            total_nodes = sum(stats.values())
            for label, count in sorted(stats.items(), key=lambda x: -x[1]):
                print(f"   {label}: {count:,}")
            print(f"   TOTAL: {total_nodes:,} nodes")
            print()

            if args.stats_only:
                return 0

            # Validations
            print("🔍 Validation Checks")
            print("-" * 50)

            report = ValidationReport()
            validations = [
                validate_entities_have_attributes,
                validate_domain_models_have_entities,
                validate_api_models_have_endpoints,
                validate_applications_have_models,
                validate_no_orphan_nodes,
                validate_temporal_metadata,
                validate_schema_version_coherence,
            ]

            for validation in validations:
                result = session.execute_read(validation)
                report.add(result)

                status = "✅" if result.passed else ("⚠️" if result.severity == "WARNING" else "❌")
                print(f"   {status} {result.name}")
                if not result.passed:
                    print(f"      Count: {result.count}")
                    if result.details:
                        print(f"      Details: {result.details}")

            print()
            print("=" * 70)
            print("Summary")
            print("=" * 70)

            if report.passed:
                print("✅ All critical validations PASSED")
            else:
                print(f"❌ {report.errors} critical validation(s) FAILED")

            if report.warnings > 0:
                print(f"⚠️  {report.warnings} warning(s)")

            print()
            return 0 if report.passed else 1

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
