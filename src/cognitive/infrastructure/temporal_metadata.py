"""
Temporal Metadata Enforcement
=============================
Sprint: Infrastructure Improvements (Fase 4)
Date: 2025-11-29

Provides:
- Automatic temporal metadata on all IR nodes
- Enforcement middleware for repositories
- Audit trail capabilities
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps

from neo4j import GraphDatabase


# Labels that require temporal metadata
TEMPORAL_LABELS = [
    "ApplicationIR",
    "DomainModelIR",
    "APIModelIR",
    "BehaviorModelIR",
    "ValidationModelIR",
    "InfrastructureModelIR",
    "Entity",
    "Attribute",
    "Endpoint",
    "APIParameter",
    "APISchema",
    "APISchemaField",
    "Flow",
    "Step",
    "Invariant",
]


class TemporalMetadataEnforcer:
    """
    Enforces temporal metadata (created_at, updated_at, schema_version)
    on all IR nodes in the graph.
    """

    def __init__(self, driver, database: str, schema_version: int = 6):
        self.driver = driver
        self.database = database
        self.schema_version = schema_version

    def enforce_all(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Add temporal metadata to all nodes missing it.

        Returns:
            Dict with counts of nodes updated per label
        """
        results = {}

        with self.driver.session(database=self.database) as session:
            for label in TEMPORAL_LABELS:
                count = self._enforce_label(session, label, dry_run)
                results[label] = count

        return results

    def _enforce_label(self, session, label: str, dry_run: bool) -> int:
        """Enforce temporal metadata for a specific label."""
        if dry_run:
            # Count nodes needing update
            query = f"""
            MATCH (n:{label})
            WHERE n.created_at IS NULL OR n.updated_at IS NULL
            RETURN count(n) as count
            """
            result = session.run(query)
            return result.single()["count"]

        # Update nodes
        query = f"""
        MATCH (n:{label})
        WHERE n.created_at IS NULL OR n.updated_at IS NULL
        SET n.created_at = coalesce(n.created_at, datetime()),
            n.updated_at = coalesce(n.updated_at, datetime()),
            n.schema_version = coalesce(n.schema_version, $schema_version)
        RETURN count(n) as updated
        """
        result = session.run(query, {"schema_version": self.schema_version})
        return result.single()["updated"]

    def validate_coverage(self) -> Dict[str, Dict[str, int]]:
        """
        Check temporal metadata coverage for all IR labels.

        Returns:
            Dict with {label: {total, with_temporal, coverage_percent}}
        """
        results = {}

        with self.driver.session(database=self.database) as session:
            for label in TEMPORAL_LABELS:
                query = f"""
                MATCH (n:{label})
                RETURN count(n) as total,
                       sum(CASE WHEN n.created_at IS NOT NULL AND n.updated_at IS NOT NULL THEN 1 ELSE 0 END) as with_temporal
                """
                result = session.run(query)
                record = result.single()

                total = record["total"]
                with_temporal = record["with_temporal"]
                coverage = (with_temporal / total * 100) if total > 0 else 100.0

                results[label] = {
                    "total": total,
                    "with_temporal": with_temporal,
                    "coverage_percent": round(coverage, 1)
                }

        return results

    def get_missing_nodes(self, label: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample of nodes missing temporal metadata."""
        with self.driver.session(database=self.database) as session:
            query = f"""
            MATCH (n:{label})
            WHERE n.created_at IS NULL OR n.updated_at IS NULL
            RETURN elementId(n) as id, keys(n) as properties
            LIMIT $limit
            """
            result = session.run(query, {"limit": limit})
            return [dict(record) for record in result]


def temporal_metadata_middleware(func):
    """
    Decorator for repository methods to automatically add temporal metadata.

    Usage:
        class MyRepository:
            @temporal_metadata_middleware
            def create_node(self, props):
                # props will automatically include created_at, updated_at
                ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Find properties dict in args or kwargs
        if 'properties' in kwargs:
            kwargs['properties'] = _add_temporal_fields(kwargs['properties'])
        elif len(args) > 1 and isinstance(args[1], dict):
            args = (args[0], _add_temporal_fields(args[1])) + args[2:]

        return func(*args, **kwargs)

    return wrapper


def _add_temporal_fields(props: Dict[str, Any]) -> Dict[str, Any]:
    """Add temporal fields to properties dict."""
    now = datetime.now().isoformat()
    return {
        **props,
        'created_at': props.get('created_at', now),
        'updated_at': now,
        'schema_version': props.get('schema_version', 6)
    }


class TemporalAuditTrail:
    """
    Tracks changes to IR nodes with timestamps and versions.

    Stores audit entries in AuditLog nodes linked to modified nodes.
    """

    def __init__(self, driver, database: str):
        self.driver = driver
        self.database = database

    def log_change(
        self,
        node_id: str,
        node_label: str,
        change_type: str,
        changed_by: str = "system",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a change to an IR node.

        Args:
            node_id: The unique ID of the node
            node_label: Label of the node (e.g., "Entity")
            change_type: Type of change (create, update, delete)
            changed_by: User or system that made the change
            details: Additional change details
        """
        with self.driver.session(database=self.database) as session:
            query = f"""
            MATCH (n:{node_label})
            WHERE n.{self._get_id_property(node_label)} = $node_id
            CREATE (log:AuditLog {{
                log_id: randomUUID(),
                node_id: $node_id,
                node_label: $node_label,
                change_type: $change_type,
                changed_by: $changed_by,
                changed_at: datetime(),
                details: $details
            }})
            CREATE (log)-[:AUDITS]->(n)
            RETURN log.log_id as log_id
            """
            import json
            session.run(query, {
                "node_id": node_id,
                "node_label": node_label,
                "change_type": change_type,
                "changed_by": changed_by,
                "details": json.dumps(details or {})
            })

    def get_history(
        self,
        node_id: str,
        node_label: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit history for a node."""
        with self.driver.session(database=self.database) as session:
            query = f"""
            MATCH (n:{node_label})<-[:AUDITS]-(log:AuditLog)
            WHERE n.{self._get_id_property(node_label)} = $node_id
            RETURN log
            ORDER BY log.changed_at DESC
            LIMIT $limit
            """
            result = session.run(query, {"node_id": node_id, "limit": limit})
            return [dict(record["log"]) for record in result]

    def _get_id_property(self, label: str) -> str:
        """Get the ID property name for a label."""
        id_map = {
            "Entity": "entity_id",
            "Attribute": "attribute_id",
            "Endpoint": "endpoint_id",
            "APIParameter": "parameter_id",
            "Flow": "flow_id",
            "Step": "step_id",
            "Invariant": "invariant_id",
            "ApplicationIR": "app_id",
            "DomainModelIR": "app_id",
            "APIModelIR": "app_id",
        }
        return id_map.get(label, "id")


# Migration script for adding temporal metadata
def run_temporal_enforcement(dry_run: bool = False):
    """
    CLI entry point for temporal metadata enforcement.

    Usage:
        python -m src.cognitive.infrastructure.temporal_metadata
    """
    from src.cognitive.config.settings import settings

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        enforcer = TemporalMetadataEnforcer(driver, settings.neo4j_database)

        print("=" * 60)
        print("TEMPORAL METADATA ENFORCEMENT")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print()

        # Show current coverage
        print("Current Coverage:")
        coverage = enforcer.validate_coverage()
        for label, stats in coverage.items():
            if stats["total"] > 0:
                icon = "✅" if stats["coverage_percent"] == 100 else "⚠️"
                print(f"  {icon} {label}: {stats['coverage_percent']}% ({stats['with_temporal']}/{stats['total']})")

        print()

        # Run enforcement
        print("Enforcing temporal metadata...")
        results = enforcer.enforce_all(dry_run=dry_run)

        total_updated = sum(results.values())
        print(f"\n{'Would update' if dry_run else 'Updated'}: {total_updated} nodes")

        if not dry_run:
            # Verify
            print("\nPost-enforcement Coverage:")
            coverage = enforcer.validate_coverage()
            for label, stats in coverage.items():
                if stats["total"] > 0:
                    icon = "✅" if stats["coverage_percent"] == 100 else "⚠️"
                    print(f"  {icon} {label}: {stats['coverage_percent']}% ({stats['with_temporal']}/{stats['total']})")

    finally:
        driver.close()


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    run_temporal_enforcement(dry_run=dry_run)
