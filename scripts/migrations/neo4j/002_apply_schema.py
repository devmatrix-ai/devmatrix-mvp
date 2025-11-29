#!/usr/bin/env python3
"""
Sprint 1 Task 1.1: Apply Domain Model Schema
Ejecuta el script Cypher para crear constraints e indexes.
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
    - CREATE, CALL, and other Cypher commands
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
    """Aplica el schema de Domain Model."""
    print("🚀 Aplicando Schema de DomainModelIR...")
    print(f"📊 Conectando a Neo4j: {NEO4J_URI}")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # Leer el script Cypher
        script_path = "scripts/migrations/neo4j/002_domain_model_schema.cypher"
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
            for c in constraints:
                if 'entity' in c.get('name', '').lower() or 'attribute' in c.get('name', '').lower():
                    print(f"   ✓ {c.get('name')}: {c.get('type')}")

        print("\n📊 Verificando Indexes:")
        with driver.session() as session:
            result = session.run("SHOW INDEXES")
            indexes = [dict(r) for r in result]
            for idx in indexes:
                if 'entity' in idx.get('name', '').lower() or 'attribute' in idx.get('name', '').lower():
                    print(f"   ✓ {idx.get('name')}: {idx.get('labelsOrTypes')} - {idx.get('properties')}")

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
