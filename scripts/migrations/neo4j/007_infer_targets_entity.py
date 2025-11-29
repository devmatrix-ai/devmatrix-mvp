#!/usr/bin/env python3
"""
007_infer_targets_entity.py
Sprint 2.5 - Task 2.5.1

Creates TARGETS_ENTITY relationships between Endpoint and Entity nodes
using path analysis heuristics.

Strategies:
1. Path Analysis: /products → Entity(Product)
2. Nested Resources: /customers/{id}/cart → Entity(Cart)
3. Action Detection: /products/{id}/deactivate → Entity(Product)

Usage:
    PYTHONPATH=. python scripts/migrations/neo4j/007_infer_targets_entity.py --dry-run
    PYTHONPATH=. python scripts/migrations/neo4j/007_infer_targets_entity.py
"""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from neo4j import GraphDatabase

from src.cognitive.config.settings import settings


# =============================================================================
# SINGULARIZATION RULES
# =============================================================================

IRREGULAR_PLURALS = {
    "people": "person",
    "children": "child",
    "men": "man",
    "women": "woman",
    "geese": "goose",
    "mice": "mouse",
    "teeth": "tooth",
    "feet": "foot",
    "data": "datum",
    "indices": "index",
    "matrices": "matrix",
    "vertices": "vertex",
    "analyses": "analysis",
}

def singularize(word: str) -> str:
    """Convert plural word to singular."""
    word = word.lower()

    # Check irregular plurals
    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]

    # Standard rules
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es"):
        if word.endswith("sses") or word.endswith("shes") or word.endswith("ches") or word.endswith("xes"):
            return word[:-2]
        return word[:-1]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word


def to_pascal_case(word: str) -> str:
    """Convert word to PascalCase."""
    # Handle compound words like cart_item or cart-item
    parts = re.split(r"[-_]", word)
    return "".join(part.capitalize() for part in parts)


def extract_resource_from_path(path: str) -> Optional[str]:
    """
    Extract the primary resource name from an API path.

    Examples:
        /products -> Product
        /products/{id} -> Product
        /customers/{customer_id}/cart -> Cart
        /carts/{id}/items -> CartItem (special case)
        /products/{id}/deactivate -> Product
    """
    # Remove leading /api/v1 or similar prefixes
    path = re.sub(r"^/api/v\d+", "", path)

    # Split path into segments
    segments = [s for s in path.split("/") if s and not s.startswith("{")]

    if not segments:
        return None

    # Special handling for nested item resources
    if len(segments) >= 2 and segments[-1] in ("items", "item"):
        parent = singularize(segments[-2])
        return to_pascal_case(f"{parent}_item")

    # Get the last non-action resource
    # Common actions to skip
    actions = {"deactivate", "activate", "checkout", "cancel", "confirm", "complete", "approve", "reject"}

    resource = None
    for segment in reversed(segments):
        if segment.lower() not in actions:
            resource = segment
            break

    if resource:
        singular = singularize(resource)
        return to_pascal_case(singular)

    return None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class InferenceResult:
    """Result of TARGETS_ENTITY inference."""
    endpoint_id: str
    entity_id: str
    path: str
    entity_name: str
    confidence: float
    inference_method: str


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

def get_driver():
    """Create Neo4j driver from settings."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def get_endpoints_without_targets(tx) -> list[dict]:
    """Get all endpoints that don't have TARGETS_ENTITY relationship."""
    query = """
    MATCH (e:Endpoint)
    WHERE NOT (e)-[:TARGETS_ENTITY]->(:Entity)
      AND e.api_model_id IS NOT NULL
    RETURN
        e.endpoint_id as endpoint_id,
        e.path as path,
        e.method as method,
        replace(e.api_model_id, '_api', '') as app_id
    """
    result = tx.run(query)
    return [dict(r) for r in result]


def get_entities_by_app(tx) -> dict[str, dict[str, str]]:
    """Get all entities grouped by app_id."""
    query = """
    MATCH (e:Entity)
    WHERE e.app_id IS NOT NULL
    RETURN e.app_id as app_id, e.entity_id as entity_id, e.name as name
    """
    result = tx.run(query)

    entities = {}
    for r in result:
        app_id = r["app_id"]
        if app_id not in entities:
            entities[app_id] = {}
        entities[app_id][r["name"]] = r["entity_id"]

    return entities


def infer_targets(endpoints: list[dict], entities_by_app: dict) -> list[InferenceResult]:
    """Infer TARGETS_ENTITY relationships from endpoints and entities."""
    results = []

    for ep in endpoints:
        path = ep["path"]
        app_id = ep["app_id"]

        # Skip if no entities for this app
        if app_id not in entities_by_app:
            continue

        app_entities = entities_by_app[app_id]

        # Extract resource from path
        resource = extract_resource_from_path(path)
        if not resource:
            continue

        # Check if entity exists
        if resource in app_entities:
            results.append(InferenceResult(
                endpoint_id=ep["endpoint_id"],
                entity_id=app_entities[resource],
                path=path,
                entity_name=resource,
                confidence=0.9,  # High confidence for exact match
                inference_method="path_analysis"
            ))

    return results


def create_targets_entity_relationships(tx, results: list[InferenceResult]) -> int:
    """Create TARGETS_ENTITY relationships in batch."""
    if not results:
        return 0

    query = """
    UNWIND $pairs as pair
    MATCH (e:Endpoint {endpoint_id: pair.endpoint_id})
    MATCH (ent:Entity {entity_id: pair.entity_id})
    CREATE (e)-[r:TARGETS_ENTITY {
        confidence: pair.confidence,
        inference_method: pair.inference_method,
        validated: false,
        created_at: datetime()
    }]->(ent)
    RETURN count(r) as created
    """

    pairs = [
        {
            "endpoint_id": r.endpoint_id,
            "entity_id": r.entity_id,
            "confidence": r.confidence,
            "inference_method": r.inference_method
        }
        for r in results
    ]

    result = tx.run(query, pairs=pairs)
    record = result.single()
    return record["created"] if record else 0


def register_migration(tx, stats: dict) -> None:
    """Register migration in MigrationRun."""
    query = """
    CREATE (m:MigrationRun {
        migration_id: "007_infer_targets_entity",
        schema_version_before: 3,
        schema_version_after: 4,
        status: "SUCCESS",
        started_at: $started_at,
        completed_at: datetime(),
        duration_seconds: $duration,
        objects_created: $created,
        objects_deleted: 0,
        objects_updated: 0,
        error_message: null,
        executed_by: "migration_script",
        execution_mode: "LIVE",
        description: "Infer TARGETS_ENTITY relationships between Endpoint and Entity using path analysis",
        details: $details
    })
    """
    tx.run(
        query,
        started_at=datetime.now(timezone.utc).isoformat(),
        duration=0,
        created=stats.get("relationships_created", 0),
        details=str(stats),
    )


def update_schema_version(tx) -> int:
    """Update GraphSchemaVersion singleton."""
    query = """
    MATCH (v:GraphSchemaVersion {singleton: true})
    SET v.current_version = 4,
        v.last_migration = "007_infer_targets_entity",
        v.updated_at = datetime()
    RETURN v.current_version as version
    """
    result = tx.run(query)
    record = result.single()
    return record["version"] if record else None


def link_migration_to_version(tx) -> None:
    """Create RESULTED_IN_VERSION relationship."""
    query = """
    MATCH (m:MigrationRun {migration_id: "007_infer_targets_entity"})
    MATCH (v:GraphSchemaVersion {singleton: true})
    MERGE (m)-[:RESULTED_IN_VERSION]->(v)
    """
    tx.run(query)


def get_coverage_stats(tx) -> dict:
    """Get TARGETS_ENTITY coverage statistics."""
    query = """
    MATCH (e:Endpoint)
    WHERE e.api_model_id IS NOT NULL
    WITH count(e) as total_endpoints
    MATCH (e:Endpoint)-[:TARGETS_ENTITY]->(ent:Entity)
    WITH total_endpoints, count(DISTINCT e) as linked_endpoints
    RETURN
        total_endpoints,
        linked_endpoints,
        (100.0 * linked_endpoints / total_endpoints) as coverage_percent
    """
    result = tx.run(query)
    record = result.single()
    if record:
        return {
            "total_endpoints": record["total_endpoints"],
            "linked_endpoints": record["linked_endpoints"],
            "coverage_percent": record["coverage_percent"]
        }
    return {}


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Infer TARGETS_ENTITY relationships between Endpoint and Entity"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Migration 007: Infer TARGETS_ENTITY Relationships")
    print("=" * 70)
    print()

    driver = get_driver()
    database = settings.neo4j_database

    try:
        with driver.session(database=database) as session:
            # Get current state
            print("📊 Current State")
            print("-" * 50)

            endpoints = session.execute_read(get_endpoints_without_targets)
            entities_by_app = session.execute_read(get_entities_by_app)

            print(f"   Endpoints without TARGETS_ENTITY: {len(endpoints)}")
            print(f"   Apps with entities: {len(entities_by_app)}")
            print()

            # Infer relationships
            print("🔍 Inferring Relationships")
            print("-" * 50)

            results = infer_targets(endpoints, entities_by_app)

            # Group by entity for summary
            by_entity = {}
            for r in results:
                if r.entity_name not in by_entity:
                    by_entity[r.entity_name] = 0
                by_entity[r.entity_name] += 1

            for entity, count in sorted(by_entity.items(), key=lambda x: -x[1]):
                print(f"   {entity}: {count} endpoints")

            print()
            print(f"   TOTAL inferred: {len(results)} relationships")
            print()

            if not results:
                print("⚠️  No relationships to create")
                return 0

            if args.dry_run:
                print("🔍 DRY RUN - No changes will be made")
                print()
                print("Sample inferences:")
                for r in results[:10]:
                    print(f"   {r.path:40} -> {r.entity_name} ({r.confidence:.1%})")
                return 0

            # Create relationships
            print("🚀 Creating Relationships")
            print("-" * 50)

            start_time = datetime.now(timezone.utc)
            created = session.execute_write(create_targets_entity_relationships, results)
            end_time = datetime.now(timezone.utc)

            print(f"   ✅ Created {created} TARGETS_ENTITY relationships")
            print(f"   ⏱️  Duration: {(end_time - start_time).total_seconds():.2f}s")
            print()

            # Register migration
            print("📝 Registering Migration")
            stats = {"relationships_created": created}
            session.execute_write(register_migration, stats)
            print("   ✅ MigrationRun created")

            new_version = session.execute_write(update_schema_version)
            print(f"   ✅ GraphSchemaVersion updated to {new_version}")

            session.execute_write(link_migration_to_version)
            print("   ✅ RESULTED_IN_VERSION relationship created")
            print()

            # Coverage report
            print("📈 Coverage Report")
            print("-" * 50)

            coverage = session.execute_read(get_coverage_stats)
            print(f"   Total endpoints: {coverage.get('total_endpoints', 0)}")
            print(f"   Linked endpoints: {coverage.get('linked_endpoints', 0)}")
            print(f"   Coverage: {coverage.get('coverage_percent', 0):.1f}%")
            print()

            print("✅ Migration completed successfully!")
            return 0

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
