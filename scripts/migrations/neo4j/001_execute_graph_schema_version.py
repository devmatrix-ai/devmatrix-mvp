#!/usr/bin/env python3
"""
001_execute_graph_schema_version.py

Ejecuta la migration 001: GraphSchemaVersion singleton creation
Sprint: Tareas Inmediatas (Pre-Sprint 3)
Fecha: 2025-11-29
"""

import sys
from pathlib import Path
from datetime import datetime

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient


def verify_pre_conditions():
    """Verificar que no exista ya un GraphSchemaVersion."""
    print("🔍 Verificando pre-condiciones...")

    with Neo4jPatternClient() as neo4j:
        query = """
        MATCH (v:GraphSchemaVersion)
        RETURN count(v) as existing_count,
               collect(v.current_version) as versions
        """

        result = neo4j._execute_query(query)
        count = result[0]["existing_count"] if result else 0
        versions = result[0]["versions"] if result else []

        if count > 0:
            print(f"⚠️  WARNING: {count} GraphSchemaVersion nodes already exist")
            print(f"   Existing versions: {versions}")
            print(f"   Migration will UPDATE existing singleton")
        else:
            print("✅ No existing GraphSchemaVersion found, will create new")

    return True


def execute_migration():
    """Ejecutar migration script."""
    print("\n🚀 Ejecutando migration 001_graph_schema_version.cypher...")

    neo4j = Neo4jPatternClient()
    neo4j.connect()

    # Leer script Cypher
    script_path = Path(__file__).parent / "001_graph_schema_version.cypher"

    if not script_path.exists():
        print(f"❌ ERROR: Script not found at {script_path}")
        neo4j.close()
        return False

    with open(script_path, "r") as f:
        cypher_script = f.read()

    # Separar por statements (punto y coma)
    statements = [s.strip() for s in cypher_script.split(";") if s.strip()]

    # Filtrar comentarios de cada statement
    clean_statements = []
    for stmt in statements:
        lines = [line.strip() for line in stmt.split("\n") if line.strip() and not line.strip().startswith("//")]
        if lines:
            clean_statements.append(" ".join(lines))

    # Ejecutar cada statement
    print(f"   Ejecutando {len(clean_statements)} statements...")
    last_result = None

    for i, statement in enumerate(clean_statements, 1):
        if not statement:
            continue

        print(f"   [{i}/{len(clean_statements)}] Executing...")
        try:
            result = neo4j._execute_query(statement)
            last_result = result
        except Exception as e:
            print(f"   ❌ Error in statement {i}: {e}")
            print(f"   Statement: {statement[:200]}...")
            neo4j.close()
            return False

    # Mostrar resultado del último statement (RETURN)
    print(f"   ✅ GraphSchemaVersion singleton created/updated")
    if last_result:
        for row in last_result:
            print(f"      Version: {row.get('current_version')}")
            print(f"      Last migration: {row.get('last_migration')}")
            print(f"      Sprints: {row.get('sprints_completed')}")

    neo4j.close()
    print("✅ Migration ejecutada exitosamente")
    return True


def verify_post_conditions():
    """Verificar que la migration se ejecutó correctamente."""
    print("\n🔍 Verificando post-condiciones...")

    with Neo4jPatternClient() as neo4j:
        # 1. Verificar singleton count
        query_count = """
        MATCH (v:GraphSchemaVersion {singleton: true})
        RETURN count(v) as singleton_count
        """
        result = neo4j._execute_query(query_count)
        count = result[0]["singleton_count"] if result else 0

        if count != 1:
            print(f"❌ FAILED: Expected 1 singleton, found {count}")
            return False

        print(f"✅ Singleton count: {count} (expected: 1)")

        # 2. Verificar contenido
        query_content = """
        MATCH (v:GraphSchemaVersion {singleton: true})
        RETURN
            v.current_version as version,
            v.last_migration as last_migration,
            v.sprints_completed as sprints,
            v.created_at as created_at,
            v.updated_at as updated_at
        """
        result = neo4j._execute_query(query_content)

        if not result:
            print("❌ FAILED: Could not retrieve singleton content")
            return False

        data = result[0]

        print(f"✅ Current version: {data['version']} (expected: 2)")
        print(f"✅ Last migration: {data['last_migration']}")
        print(f"✅ Sprints completed: {data['sprints']}")
        print(f"✅ Created at: {data['created_at']}")
        print(f"✅ Updated at: {data['updated_at']}")

        # Validaciones
        if data['version'] != 2:
            print(f"❌ FAILED: Version is {data['version']}, expected 2")
            return False

        if len(data['sprints']) != 3:
            print(f"❌ FAILED: Expected 3 sprints, found {len(data['sprints'])}")
            return False

    print("\n🎉 All post-conditions verified successfully!")
    return True


def main():
    """Main execution flow."""
    print("=" * 80)
    print("MIGRATION 001: GraphSchemaVersion Singleton Creation")
    print("Sprint: Tareas Inmediatas (Pre-Sprint 3)")
    print(f"Execution time: {datetime.now().isoformat()}")
    print("=" * 80)

    try:
        # Step 1: Pre-conditions
        if not verify_pre_conditions():
            print("\n❌ Pre-conditions failed, aborting")
            return 1

        # Step 2: Execute migration
        if not execute_migration():
            print("\n❌ Migration execution failed, aborting")
            return 1

        # Step 3: Post-conditions
        if not verify_post_conditions():
            print("\n❌ Post-conditions verification failed")
            print("   Consider running rollback: 001_rollback_graph_schema_version.cypher")
            return 1

        print("\n" + "=" * 80)
        print("✅ MIGRATION 001 COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. ✅ IA.1 DONE: GraphSchemaVersion singleton created")
        print("  2. ⏳ IA.2 TODO: Execute 002_register_past_migrations.py")
        print("  3. ⏳ IA.3 TODO: Create GraphIRRepository base class")
        print("  4. ⏳ IA.4 TODO: Implement roundtrip tests")
        print("=" * 80)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
