#!/usr/bin/env python3
"""
Sprint 2 Task 2.3: API Model Expansion Migration

Migrates APIModelIR nodes from JSON string storage to proper graph structure:
- Creates Endpoint nodes with HAS_ENDPOINT relationships
- Creates APIParameter nodes with HAS_PARAMETER relationships
- Creates APISchema nodes with HAS_SCHEMA relationships
- Creates APISchemaField nodes with HAS_FIELD relationships
- Creates REQUEST_SCHEMA and RESPONSE_SCHEMA relationships

This script:
1. Queries all APIModelIR nodes with endpoints JSON property
2. Parses JSON and creates graph nodes for endpoints, schemas, and parameters
3. Establishes proper relationships between nodes
4. Keeps original JSON for rollback capability
5. Provides verification and dry-run modes

The script is idempotent - it uses MERGE to avoid duplicates and can be run multiple times safely.
"""
import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.cognitive.ir.api_model import (
    APIModelIR,
    Endpoint,
    APIParameter,
    APISchema,
    APISchemaField,
    HttpMethod,
    ParameterLocation,
    InferenceSource
)
from src.cognitive.services.api_model_graph_repository import (
    APIModelGraphRepository,
    APIModelPersistenceError
)

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devmatrix123")

# Progress reporting interval
PROGRESS_INTERVAL = 50

# Dry run mode
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


async def get_api_models_with_json(driver) -> List[Dict[str, Any]]:
    """
    Retrieve all APIModelIR nodes that have endpoints as JSON property.

    Returns:
        List of records with app_id and endpoints JSON string
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (api:APIModelIR)
            WHERE api.endpoints IS NOT NULL
              AND api.endpoints <> ''
              AND api.app_id IS NOT NULL
            RETURN api.app_id as app_id,
                   api.endpoints as endpoints_json,
                   api.schemas as schemas_json,
                   api.base_path as base_path,
                   api.version as version
            ORDER BY api.app_id
        """)
        records = [
            {
                "app_id": record["app_id"],
                "endpoints_json": record["endpoints_json"],
                "schemas_json": record["schemas_json"],
                "base_path": record["base_path"],
                "version": record["version"]
            }
            async for record in result
        ]
        return records


async def migrate_api_model(
    app_id: str,
    endpoints_json: str,
    schemas_json: Optional[str],
    base_path: str,
    version: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Migrate a single APIModelIR from JSON to graph nodes.

    Args:
        app_id: Application ID
        endpoints_json: JSON string containing endpoints
        schemas_json: JSON string containing schemas (optional)
        base_path: API base path
        version: API version
        dry_run: If True, only parse and validate without writing

    Returns:
        Statistics dict with counts of created nodes/relationships
    """
    stats = {
        "endpoints": 0,
        "parameters": 0,
        "schemas": 0,
        "fields": 0
    }

    try:
        # Parse endpoints JSON
        endpoints_data = json.loads(endpoints_json)

        # Parse schemas JSON (may be null/empty)
        schemas_data = []
        if schemas_json:
            schemas_data = json.loads(schemas_json)

        # Build complete APIModelIR
        api_model = APIModelIR(
            endpoints=endpoints_data,
            schemas=schemas_data,
            base_path=base_path if base_path else "",
            version=version if version else "v1"
        )

        if dry_run:
            # Just count what would be created
            stats["endpoints"] = len(api_model.endpoints)
            stats["schemas"] = len(api_model.schemas)
            for endpoint in api_model.endpoints:
                stats["parameters"] += len(endpoint.parameters)
            for schema in api_model.schemas:
                stats["fields"] += len(schema.fields)
            return stats

        # Use repository to create graph structure
        repo = APIModelGraphRepository()
        try:
            repo.save_api_model(app_id, api_model)

            # Count created objects
            stats["endpoints"] = len(api_model.endpoints)
            stats["schemas"] = len(api_model.schemas)
            for endpoint in api_model.endpoints:
                stats["parameters"] += len(endpoint.parameters)
            for schema in api_model.schemas:
                stats["fields"] += len(schema.fields)

        finally:
            repo.close()

        return stats

    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON for {app_id}: {e}")
        return stats
    except Exception as e:
        print(f"❌ Error migrating {app_id}: {e}")
        import traceback
        traceback.print_exc()
        return stats


async def verify_migration(driver) -> Dict[str, int]:
    """
    Verify the migration by counting created nodes and relationships.

    Returns:
        Dict with verification counts
    """
    async with driver.session() as session:
        # Count Endpoint nodes
        result = await session.run("MATCH (e:Endpoint) RETURN count(e) as count")
        record = await result.single()
        endpoint_count = record["count"] if record else 0

        # Count APIParameter nodes
        result = await session.run("MATCH (p:APIParameter) RETURN count(p) as count")
        record = await result.single()
        parameter_count = record["count"] if record else 0

        # Count APISchema nodes
        result = await session.run("MATCH (s:APISchema) RETURN count(s) as count")
        record = await result.single()
        schema_count = record["count"] if record else 0

        # Count APISchemaField nodes
        result = await session.run("MATCH (f:APISchemaField) RETURN count(f) as count")
        record = await result.single()
        field_count = record["count"] if record else 0

        # Count HAS_ENDPOINT relationships
        result = await session.run("MATCH ()-[r:HAS_ENDPOINT]->() RETURN count(r) as count")
        record = await result.single()
        has_endpoint_count = record["count"] if record else 0

        # Count HAS_PARAMETER relationships
        result = await session.run("MATCH ()-[r:HAS_PARAMETER]->() RETURN count(r) as count")
        record = await result.single()
        has_parameter_count = record["count"] if record else 0

        # Count HAS_SCHEMA relationships
        result = await session.run("MATCH ()-[r:HAS_SCHEMA]->() RETURN count(r) as count")
        record = await result.single()
        has_schema_count = record["count"] if record else 0

        # Count REQUEST_SCHEMA relationships
        result = await session.run("MATCH ()-[r:REQUEST_SCHEMA]->() RETURN count(r) as count")
        record = await result.single()
        request_schema_count = record["count"] if record else 0

        # Count RESPONSE_SCHEMA relationships
        result = await session.run("MATCH ()-[r:RESPONSE_SCHEMA]->() RETURN count(r) as count")
        record = await result.single()
        response_schema_count = record["count"] if record else 0

        return {
            "endpoints": endpoint_count,
            "parameters": parameter_count,
            "schemas": schema_count,
            "fields": field_count,
            "has_endpoint": has_endpoint_count,
            "has_parameter": has_parameter_count,
            "has_schema": has_schema_count,
            "request_schema": request_schema_count,
            "response_schema": response_schema_count
        }


async def mark_migration_complete(driver, app_id: str) -> None:
    """
    Mark an APIModelIR as migrated by setting a flag.

    Args:
        driver: Neo4j driver
        app_id: Application ID
    """
    async with driver.session() as session:
        await session.run("""
            MATCH (api:APIModelIR {app_id: $app_id})
            SET api.migrated_to_graph = true,
                api.migration_timestamp = datetime()
        """, app_id=app_id)


async def run_migration():
    """
    Main migration logic.

    Process:
    1. Connect to Neo4j
    2. Get all APIModelIR nodes with JSON endpoints
    3. For each, parse JSON and create graph structure
    4. Report progress every PROGRESS_INTERVAL records
    5. Verify migration with counts
    """
    mode_str = "DRY RUN" if DRY_RUN else "MIGRATION"
    print(f"🚀 Starting API Model {mode_str}...")
    print(f"📊 Configuration:")
    print(f"   Neo4j: {NEO4J_URI}")
    print(f"   Mode: {'DRY RUN' if DRY_RUN else 'LIVE MIGRATION'}")
    print(f"   Progress interval: {PROGRESS_INTERVAL}")
    print()

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        # Get all APIModels with JSON data
        print("🔍 Fetching APIModelIR nodes with JSON data...")
        api_models = await get_api_models_with_json(driver)
        print(f"📝 Found {len(api_models)} APIModelIR nodes to migrate")

        if not api_models:
            print("✅ No APIModelIR nodes to migrate!")
            return

        print()

        # Migration statistics
        total_endpoints = 0
        total_parameters = 0
        total_schemas = 0
        total_fields = 0
        migrated = 0
        errors = 0

        # Process each APIModel
        for i, record in enumerate(api_models, 1):
            app_id = record["app_id"]

            try:
                # Migrate this APIModel
                stats = await migrate_api_model(
                    app_id,
                    record["endpoints_json"],
                    record["schemas_json"],
                    record["base_path"],
                    record["version"],
                    dry_run=DRY_RUN
                )

                total_endpoints += stats["endpoints"]
                total_parameters += stats["parameters"]
                total_schemas += stats["schemas"]
                total_fields += stats["fields"]

                # Mark as migrated (only in LIVE mode)
                if not DRY_RUN:
                    await mark_migration_complete(driver, app_id)

                migrated += 1

                # Progress report
                if i % PROGRESS_INTERVAL == 0 or i == len(api_models):
                    print(f"✅ [{i}/{len(api_models)}] {app_id}")
                    print(f"   Endpoints: {stats['endpoints']}, Parameters: {stats['parameters']}, "
                          f"Schemas: {stats['schemas']}, Fields: {stats['fields']}")

            except Exception as e:
                errors += 1
                print(f"❌ Error processing {app_id}: {e}")
                continue

        # Final report
        print("\n" + "="*60)
        print(f"📊 {mode_str} COMPLETE")
        print("="*60)
        print(f"Total APIModels processed: {len(api_models)}")
        print(f"✅ Successfully migrated: {migrated} ({migrated/len(api_models)*100:.1f}%)")
        print(f"❌ Errors: {errors}")
        print()
        print(f"📈 Objects {'would be created' if DRY_RUN else 'created'}:")
        print(f"   Endpoint nodes: {total_endpoints}")
        print(f"   APIParameter nodes: {total_parameters}")
        print(f"   APISchema nodes: {total_schemas}")
        print(f"   APISchemaField nodes: {total_fields}")
        print(f"   Total: {total_endpoints + total_parameters + total_schemas + total_fields}")
        print("="*60)

        # Verification (only in LIVE mode)
        if not DRY_RUN:
            print("\n🔍 Verifying migration...")
            verification = await verify_migration(driver)

            print("\n📊 Verification Results:")
            print(f"   Endpoint nodes: {verification['endpoints']}")
            print(f"   APIParameter nodes: {verification['parameters']}")
            print(f"   APISchema nodes: {verification['schemas']}")
            print(f"   APISchemaField nodes: {verification['fields']}")
            print()
            print(f"   HAS_ENDPOINT edges: {verification['has_endpoint']}")
            print(f"   HAS_PARAMETER edges: {verification['has_parameter']}")
            print(f"   HAS_SCHEMA edges: {verification['has_schema']}")
            print(f"   REQUEST_SCHEMA edges: {verification['request_schema']}")
            print(f"   RESPONSE_SCHEMA edges: {verification['response_schema']}")

            # Verification checks
            print("\n✅ Verification Checks:")
            checks_passed = 0
            checks_total = 5

            if verification['endpoints'] == total_endpoints:
                print(f"   ✓ Endpoint count matches: {verification['endpoints']}")
                checks_passed += 1
            else:
                print(f"   ✗ Endpoint count mismatch: expected {total_endpoints}, got {verification['endpoints']}")

            if verification['parameters'] == total_parameters:
                print(f"   ✓ Parameter count matches: {verification['parameters']}")
                checks_passed += 1
            else:
                print(f"   ✗ Parameter count mismatch: expected {total_parameters}, got {verification['parameters']}")

            if verification['schemas'] == total_schemas:
                print(f"   ✓ Schema count matches: {verification['schemas']}")
                checks_passed += 1
            else:
                print(f"   ✗ Schema count mismatch: expected {total_schemas}, got {verification['schemas']}")

            if verification['fields'] == total_fields:
                print(f"   ✓ Field count matches: {verification['fields']}")
                checks_passed += 1
            else:
                print(f"   ✗ Field count mismatch: expected {total_fields}, got {verification['fields']}")

            if verification['has_endpoint'] == migrated:
                print(f"   ✓ HAS_ENDPOINT relationship count matches: {verification['has_endpoint']}")
                checks_passed += 1
            else:
                print(f"   ✗ HAS_ENDPOINT mismatch: expected {migrated}, got {verification['has_endpoint']}")

            print(f"\n🎯 Verification: {checks_passed}/{checks_total} checks passed")

            if checks_passed == checks_total:
                print("\n🎉 MIGRATION SUCCESSFUL - All verification checks passed!")
            else:
                print("\n⚠️  WARNING - Some verification checks failed, please review")

        else:
            print("\n💡 Next steps:")
            print("   1. Review the dry-run results above")
            print("   2. If everything looks good, run without DRY_RUN=true:")
            print(f"      python {__file__}")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await driver.close()
        print("\n🔌 Connection closed")


if __name__ == "__main__":
    asyncio.run(run_migration())
