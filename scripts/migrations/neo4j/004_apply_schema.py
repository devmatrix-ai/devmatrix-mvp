#!/usr/bin/env python3
"""
Sprint 2 Task 2.1: Apply API Model Schema
Ejecuta el script Cypher para crear constraints e indexes de APIModelIR.

Este script:
1. Lee el archivo 004_api_model_schema.cypher
2. Parsea los statements Cypher individuales
3. Ejecuta cada statement contra Neo4j
4. Verifica que constraints e indexes se crearon correctamente

Constraints creados:
- endpoint_unique: (api_model_id, path, method)
- api_parameter_unique: (endpoint_id, name)
- api_schema_unique: (api_model_id, name)
- api_schema_field_unique: (schema_id, name)

Indexes creados:
- endpoint_path, endpoint_method, endpoint_operation_id, endpoint_inferred
- api_parameter_location, api_parameter_required
- api_schema_name
- api_schema_field_required

Uso:
    python scripts/migrations/neo4j/004_apply_schema.py

Variables de entorno:
    NEO4J_URI: URI de Neo4j (default: bolt://localhost:7687)
    NEO4J_USER: Usuario de Neo4j (default: neo4j)
    NEO4J_PASSWORD: Password de Neo4j (default: devmatrix123)
"""
import os
import sys
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devmatrix123")

def parse_cypher_file(filepath: str) -> list:
    """
    Parse Cypher file into individual statements.

    Handles:
    - Single-line comments (//)
    - Multi-line statements
    - CREATE, DROP, CALL, and other Cypher commands

    Args:
        filepath: Ruta al archivo .cypher

    Returns:
        Lista de strings, cada uno un statement Cypher completo
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()

    statements = []
    current_statement = []
    in_statement = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('//'):
            continue

        # Check if this is the start of a new statement
        if stripped.upper().startswith(('CREATE', 'DROP', 'MATCH', 'MERGE', 'CALL', 'WITH', 'RETURN')):
            # Save previous statement if exists
            if current_statement:
                stmt = '\n'.join(current_statement)
                statements.append(stmt)
                current_statement = []

            in_statement = True

        # Accumulate lines for current statement
        if in_statement:
            current_statement.append(line.rstrip())

            # Check if statement ends with semicolon
            if stripped.endswith(';'):
                stmt = '\n'.join(current_statement)
                statements.append(stmt)
                current_statement = []
                in_statement = False

    # Add final statement if exists
    if current_statement:
        stmt = '\n'.join(current_statement)
        statements.append(stmt)

    return statements

def apply_schema():
    """
    Aplica el schema de API Model.

    Proceso:
    1. Conecta a Neo4j
    2. Lee y parsea 004_api_model_schema.cypher
    3. Ejecuta cada statement
    4. Maneja errores comunes (constraints ya existentes, sintaxis vieja)
    5. Verifica creación exitosa con SHOW CONSTRAINTS y SHOW INDEXES
    """
    print("🚀 Aplicando Schema de APIModelIR...")
    print(f"📊 Conectando a Neo4j: {NEO4J_URI}")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # Leer el script Cypher
        script_path = "scripts/migrations/neo4j/004_api_model_schema.cypher"
        statements = parse_cypher_file(script_path)

        print(f"📝 Ejecutando {len(statements)} statements...\n")

        with driver.session() as session:
            for i, statement in enumerate(statements, 1):
                # Ignorar comentarios multi-línea
                if statement.startswith('/*') or not statement:
                    continue

                try:
                    result = session.run(statement)
                    summary = result.consume()
                    print(f"✅ Statement {i}/{len(statements)}: {statement[:60]}...")

                except Exception as e:
                    # Algunos statements pueden fallar si ya existen (IGNORE)
                    if "already exists" in str(e) or "equivalent" in str(e):
                        print(f"⏩ Statement {i}/{len(statements)}: Ya existe (skip)")
                    # Los statements de CALL db.constraints/indexes con WHERE tienen sintaxis vieja
                    elif statement.strip().upper().startswith('CALL DB.'):
                        print(f"⏩ Statement {i}/{len(statements)}: Verificación (skip syntax)")
                    # RETURN standalone sin CALL previo (parte de verificación)
                    elif statement.strip().upper().startswith('RETURN') and 'not defined' in str(e):
                        print(f"⏩ Statement {i}/{len(statements)}: RETURN standalone (skip)")
                    else:
                        print(f"❌ Error en statement {i}: {e}")
                        raise

        print("\n" + "="*60)
        print("✅ SCHEMA APLICADO EXITOSAMENTE")
        print("="*60)

        # Verificar constraints e indexes creados
        print("\n📊 Verificando Constraints:")
        with driver.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            constraints = [dict(r) for r in result]
            api_constraints = 0
            for c in constraints:
                name = c.get('name', '').lower()
                if 'endpoint' in name or 'api_parameter' in name or 'api_schema' in name:
                    print(f"   ✓ {c.get('name')}: {c.get('type')}")
                    api_constraints += 1
            print(f"\n   Total API Model constraints: {api_constraints}")

        print("\n📊 Verificando Indexes:")
        with driver.session() as session:
            result = session.run("SHOW INDEXES")
            indexes = [dict(r) for r in result]
            api_indexes = 0
            for idx in indexes:
                name = idx.get('name', '').lower()
                if 'endpoint' in name or 'api_parameter' in name or 'api_schema' in name:
                    print(f"   ✓ {idx.get('name')}: {idx.get('labelsOrTypes')} - {idx.get('properties')}")
                    api_indexes += 1
            print(f"\n   Total API Model indexes: {api_indexes}")

        # Resumen final
        print("\n" + "="*60)
        print("📋 RESUMEN")
        print("="*60)
        print(f"✅ Constraints creados: {api_constraints}")
        print(f"✅ Indexes creados: {api_indexes}")
        print("\n🎯 Siguiente paso: Crear API Model Repository (Task 2.2)")

    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        driver.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    apply_schema()
