"""Neo4j Client for DevMatrix V2.1 Hybrid Architecture"""

from typing import Dict, List, Optional, Any
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j client for template and component management"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "devmatrix123",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[AsyncDriver] = None

    async def connect(self) -> bool:
        """Initialize Neo4j connection"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            # Verify connection
            try:
                async with self.driver.session() as session:
                    await session.run("RETURN 1")
                logger.info("✅ Neo4j connected successfully")
                return True
            except Exception as verify_error:
                logger.error(f"❌ Connection verification failed: {verify_error}")
                return False
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            return False

    async def close(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")

    async def init_schema(self) -> Dict[str, bool]:
        """Initialize complete schema with constraints and indexes"""
        results = {}

        if not self.driver:
            logger.error("Driver not initialized")
            return results

        async with self.driver.session() as session:
            # Templates constraints and indexes
            try:
                await session.run(
                    "CREATE CONSTRAINT template_id IF NOT EXISTS "
                    "FOR (t:Template) REQUIRE t.id IS UNIQUE"
                )
                results["template_id_constraint"] = True
            except Exception as e:
                logger.warning(f"Template constraint creation: {e}")
                results["template_id_constraint"] = False

            # Components constraints and indexes
            try:
                await session.run(
                    "CREATE CONSTRAINT component_id IF NOT EXISTS "
                    "FOR (c:Component) REQUIRE c.id IS UNIQUE"
                )
                results["component_id_constraint"] = True
            except Exception as e:
                logger.warning(f"Component constraint creation: {e}")
                results["component_id_constraint"] = False

            # Trezo components index
            try:
                await session.run(
                    "CREATE INDEX trezo_components IF NOT EXISTS "
                    "FOR (c:Component) ON (c.source)"
                )
                results["trezo_index"] = True
            except Exception as e:
                logger.warning(f"Trezo index creation: {e}")
                results["trezo_index"] = False

            # Precision index for fast queries
            try:
                await session.run(
                    "CREATE INDEX component_precision IF NOT EXISTS "
                    "FOR (c:Component) ON (c.precision)"
                )
                results["precision_index"] = True
            except Exception as e:
                logger.warning(f"Precision index creation: {e}")
                results["precision_index"] = False

        return results

    async def create_template(self, template_data: Dict[str, Any]) -> Optional[str]:
        """Create a template node"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        CREATE (t:Template {
            id: $id,
            name: $name,
            category: $category,
            framework: $framework,
            precision: $precision,
            code: $code,
            description: $description,
            created_at: datetime()
        })
        RETURN t.id as template_id
        """

        async with self.driver.session() as session:
            result = await session.run(query, **template_data)
            record = await result.single()
            return record["template_id"] if record else None

    async def create_component(self, component_data: Dict[str, Any]) -> Optional[str]:
        """Create a component node (UI or other)"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        CREATE (c:Component {
            id: $id,
            name: $name,
            category: $category,
            source: $source,
            precision: $precision,
            code: $code,
            features: $features,
            created_at: datetime()
        })
        RETURN c.id as component_id
        """

        async with self.driver.session() as session:
            result = await session.run(query, **component_data)
            record = await result.single()
            return record["component_id"] if record else None

    async def find_component_by_features(
        self, category: str, features: List[str], source: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find component by category and features"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        MATCH (c:Component)
        WHERE c.category = $category
        AND c.precision > 0.8
        """

        params: Dict[str, Any] = {"category": category, "features": features}

        if source:
            query += " AND c.source = $source"
            params["source"] = source

        query += """
        RETURN c.id as id, c.name as name, c.precision as precision,
               c.code as code, c.features as features
        ORDER BY c.precision DESC
        LIMIT 1
        """

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            record = await result.single()
            return dict(record) if record else None

    async def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        stats = {}

        async with self.driver.session() as session:
            # Count templates
            result = await session.run(
                "MATCH (t:Template) RETURN count(t) as count"
            )
            record = await result.single()
            stats["templates"] = record["count"] if record else 0

            # Count components
            result = await session.run(
                "MATCH (c:Component) RETURN count(c) as count"
            )
            record = await result.single()
            stats["components"] = record["count"] if record else 0

            # Count Trezo components
            result = await session.run(
                "MATCH (c:Component {source: 'trezo'}) RETURN count(c) as count"
            )
            record = await result.single()
            stats["trezo_components"] = record["count"] if record else 0

        return stats

    async def verify_connection(self) -> bool:
        """Verify Neo4j is accessible"""
        if not self.driver:
            return False

        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return bool(record)
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False
