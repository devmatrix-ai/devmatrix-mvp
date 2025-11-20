#!/usr/bin/env python3
"""
Run E2E test for ecommerce_api_simple.md spec
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.e2e.real_e2e_with_dashboard import RealE2ETest


async def main():
    """Execute E2E test for ecommerce spec"""

    # Read ecommerce spec
    spec_path = Path(__file__).parent / "test_specs" / "ecommerce_api_simple.md"

    if not spec_path.exists():
        print(f"❌ Spec not found: {spec_path}")
        sys.exit(1)

    with open(spec_path, 'r') as f:
        spec_content = f.read()

    print("\n" + "="*80)
    print("🛒 E2E TEST - ECOMMERCE API (ecommerce_api_simple.md)")
    print("="*80)
    print(f"\n📄 Spec: {spec_path}")
    print(f"📏 Size: {len(spec_content)} chars")
    print(f"📊 Estimated complexity: 0.45 (Simple-Medium)")
    print("\n" + "="*80 + "\n")

    # Run test
    test = RealE2ETest(spec_content)
    metrics = await test.run()

    print("\n" + "="*80)
    print("✅ E2E TEST COMPLETADO")
    print("="*80)

    metrics_dict = metrics.to_dict()
    print(f"\n📊 Estado: {metrics_dict['overall_status'].upper()}")
    print(f"⏱️  Duración: {metrics.total_duration_ms / 1000:.1f}s")
    print(f"🎯 Patterns creados automáticamente almacenados en Pattern Bank")
    print(f"\n📁 Métricas guardadas en: tests/e2e/metrics/")

    # Verify pattern bank state after
    print("\n" + "="*80)
    print("📊 VERIFICANDO PATTERN BANK")
    print("="*80)

    from neo4j import GraphDatabase
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'devmatrix123'))

    with driver.session() as session:
        # Total patterns
        result = session.run("MATCH (p:Pattern) RETURN count(p) as total")
        total = result.single()['total']

        # FastAPI patterns
        result = session.run("""
            MATCH (p:Pattern)
            WHERE p.framework = 'fastapi'
            RETURN count(p) as count
        """)
        fastapi = result.single()['count']

        # Ecommerce patterns (newly created)
        result = session.run("""
            MATCH (p:Pattern)
            WHERE p.description =~ '(?i).*(product|customer|cart|order|checkout|ecommerce).*'
              AND p.framework = 'fastapi'
              AND p.created_at > datetime() - duration('PT2H')
            RETURN count(p) as count
        """)
        new_ecommerce = result.single()['count']

    driver.close()

    print(f"\n📦 Total patterns: {total:,}")
    print(f"🐍 FastAPI patterns: {fastapi:,}")
    print(f"🛒 Nuevos patterns ecommerce (últimas 2h): {new_ecommerce}")

    return metrics


if __name__ == "__main__":
    asyncio.run(main())
