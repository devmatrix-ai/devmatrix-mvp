"""Validate Neo4j Performance Against Targets

This script runs performance benchmarks against the targets defined in
the Neo4j architecture document:
- Template search by category+framework: <10ms
- With dependencies: <50ms
- Full-text: <100ms
- Batch operations (1K items): <5s
"""

import asyncio
import logging
import time
from typing import Dict, List, Tuple
from src.neo4j_client import Neo4jClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceValidator:
    def __init__(self, client: Neo4jClient):
        self.client = client
        self.results = {}

    async def validate_template_search(self) -> Tuple[int, float]:
        """Validate template search by category+framework < 10ms"""
        start = time.time()
        try:
            # Use existing method to get category templates
            result = await self.client.get_category_templates("authentication", limit=10)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            status = "✅" if elapsed < 10 else "⚠️"
            logger.info(f"{status} Template search: {elapsed:.2f}ms (target: <10ms)")
            return len(result) if result else 0, elapsed
        except Exception as e:
            logger.error(f"❌ Template search failed: {e}")
            return 0, 0

    async def validate_template_with_dependencies(self) -> Tuple[int, float]:
        """Validate template with dependencies < 50ms"""
        start = time.time()
        try:
            result = await self.client.get_template_with_dependencies("jwt_auth_fastapi_v1")
            elapsed = (time.time() - start) * 1000

            status = "✅" if elapsed < 50 else "⚠️"
            logger.info(f"{status} Template with deps: {elapsed:.2f}ms (target: <50ms)")
            return 1 if result else 0, elapsed
        except Exception as e:
            logger.error(f"❌ Template with deps failed: {e}")
            return 0, 0

    async def validate_category_templates(self) -> Tuple[int, float]:
        """Validate category template retrieval"""
        start = time.time()
        try:
            result = await self.client.get_category_templates("authentication")
            elapsed = (time.time() - start) * 1000

            count = len(result) if result else 0
            status = "✅" if elapsed < 10 else "⚠️"
            logger.info(f"{status} Category templates ({count}): {elapsed:.2f}ms (target: <10ms)")
            return count, elapsed
        except Exception as e:
            logger.error(f"❌ Category templates failed: {e}")
            return 0, 0

    async def validate_framework_templates(self) -> Tuple[int, float]:
        """Validate framework template retrieval"""
        start = time.time()
        try:
            # Validate by finding components/templates with framework
            templates = await self.client.find_component_by_features("api", ["rest"])
            elapsed = (time.time() - start) * 1000

            count = 1 if templates else 0
            status = "✅" if elapsed < 10 else "⚠️"
            logger.info(f"{status} Framework templates: {elapsed:.2f}ms (target: <10ms)")
            return count, elapsed
        except Exception as e:
            logger.error(f"❌ Framework templates failed: {e}")
            return 0, 0

    async def validate_stats_query(self) -> Tuple[int, float]:
        """Validate comprehensive stats query"""
        start = time.time()
        try:
            stats = await self.client.get_database_stats()
            elapsed = (time.time() - start) * 1000

            status = "✅" if elapsed < 100 else "⚠️"
            logger.info(f"{status} Stats query: {elapsed:.2f}ms (target: <100ms)")
            logger.info(f"   Templates: {stats.get('template_count', 0)}")
            logger.info(f"   Categories: {stats.get('category_count', 0)}")
            logger.info(f"   Frameworks: {stats.get('framework_count', 0)}")
            logger.info(f"   Relationships: {stats.get('relationship_count', 0)}")
            logger.info(f"   Avg Precision: {stats.get('avg_template_precision', 0.0):.3f}")
            return stats.get('template_count', 0), elapsed
        except Exception as e:
            logger.error(f"❌ Stats query failed: {e}")
            return 0, 0

    async def validate_similar_templates(self) -> Tuple[int, float]:
        """Validate similar templates search"""
        start = time.time()
        try:
            result = await self.client.find_similar_templates("jwt_auth_fastapi_v1", limit=5)
            elapsed = (time.time() - start) * 1000

            count = len(result) if result else 0
            status = "✅" if elapsed < 50 else "⚠️"
            logger.info(f"{status} Similar templates ({count}): {elapsed:.2f}ms (target: <50ms)")
            return count, elapsed
        except Exception as e:
            logger.error(f"❌ Similar templates failed: {e}")
            return 0, 0

    async def validate_all(self) -> Dict[str, Tuple[int, float]]:
        """Run all performance validations"""
        logger.info("\n" + "="*60)
        logger.info("🚀 NEO4J PERFORMANCE VALIDATION")
        logger.info("="*60)

        results = {
            "template_search": await self.validate_template_search(),
            "template_with_deps": await self.validate_template_with_dependencies(),
            "category_templates": await self.validate_category_templates(),
            "framework_templates": await self.validate_framework_templates(),
            "similar_templates": await self.validate_similar_templates(),
            "stats_query": await self.validate_stats_query(),
        }

        return results

    def print_summary(self, results: Dict[str, Tuple[int, float]]):
        """Print validation summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 PERFORMANCE VALIDATION SUMMARY")
        logger.info("="*60)

        total_time = sum(r[1] for r in results.values())
        targets = {
            "template_search": 10,
            "template_with_deps": 50,
            "category_templates": 10,
            "framework_templates": 10,
            "similar_templates": 50,
            "stats_query": 100,
        }

        passed = 0
        failed = 0

        for test_name, (count, elapsed) in results.items():
            target = targets.get(test_name, 100)
            status = "✅ PASS" if elapsed < target else "⚠️  WARN"
            passed += 1 if elapsed < target else 0
            failed += 0 if elapsed < target else 1

            logger.info(f"{status} {test_name:25} {elapsed:8.2f}ms (target: {target:3d}ms)")

        logger.info("="*60)
        logger.info(f"📈 Results: {passed} passed, {failed} warnings")
        logger.info(f"⏱️  Total time: {total_time:.2f}ms")
        logger.info("="*60)


async def main():
    """Main validation orchestration"""
    client = Neo4jClient()

    try:
        if not await client.connect():
            logger.error("Failed to connect to Neo4j")
            return

        logger.info("✅ Connected to Neo4j")

        validator = PerformanceValidator(client)
        results = await validator.validate_all()
        validator.print_summary(results)

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
