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

    async def create_relationship(
        self,
        source_label: str,
        source_id: str,
        target_label: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between two nodes"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        properties = properties or {}
        props_str = ", ".join(
            [f"{k}: ${k}" for k in properties.keys()]
        ) if properties else ""
        props_clause = f" {{{props_str}}}" if props_str else ""

        query = f"""
        MATCH (source:{source_label} {{id: $source_id}})
        MATCH (target:{target_label} {{id: $target_id}})
        CREATE (source)-[r:{relationship_type}{props_clause}]->(target)
        RETURN COUNT(r) as count
        """

        params = {
            "source_id": source_id,
            "target_id": target_id,
            **properties,
        }

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            record = await result.single()
            return record["count"] > 0 if record else False

    async def get_template_with_dependencies(
        self, template_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get template with all its dependencies and relationships"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        MATCH (t:Template {id: $template_id})
        OPTIONAL MATCH (t)-[:BELONGS_TO]->(cat:Category)
        OPTIONAL MATCH (t)-[:USES]->(f:Framework)
        OPTIONAL MATCH (t)-[:REQUIRES]->(d:Dependency)
        OPTIONAL MATCH (t)-[:IMPLEMENTS]->(p:Pattern)
        OPTIONAL MATCH (t)-[:CREATED_BY]->(u:User)
        RETURN {
            template: t,
            category: cat,
            framework: f,
            dependencies: collect(DISTINCT d),
            patterns: collect(DISTINCT p),
            creator: u
        } as full_template
        """

        async with self.driver.session() as session:
            result = await session.run(query, template_id=template_id)
            record = await result.single()
            return dict(record["full_template"]) if record else None

    async def find_similar_templates(
        self,
        template_id: str,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Find similar templates based on relationships"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        MATCH (t:Template {id: $template_id})
        MATCH (t)-[sim:SIMILAR_TO]->(similar)
        WHERE similar.status = 'active'
        AND sim.similarity_score >= $min_similarity
        RETURN similar as template, sim.similarity_score as score
        ORDER BY score DESC
        LIMIT $limit
        """

        async with self.driver.session() as session:
            result = await session.run(
                query,
                template_id=template_id,
                limit=limit,
                min_similarity=min_similarity,
            )
            records = [record async for record in result]
            return [
                {
                    **dict(record["template"]),
                    "similarity_score": record["score"],
                }
                for record in records
            ]

    async def batch_create_templates(
        self, templates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Create multiple templates in a single transaction (bulk insert)"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        UNWIND $templates as template_data
        CREATE (t:Template {
            id: template_data.id,
            name: template_data.name,
            category: template_data.category,
            subcategory: template_data.subcategory,
            framework: template_data.framework,
            language: template_data.language,
            precision: template_data.precision,
            code: template_data.code,
            description: template_data.description,
            complexity: template_data.complexity,
            version: template_data.version,
            status: template_data.status,
            source: template_data.source,
            created_at: datetime()
        })
        RETURN COUNT(t) as created
        """

        async with self.driver.session() as session:
            result = await session.run(query, templates=templates)
            record = await result.single()
            return {
                "created": record["created"] if record else 0,
                "total": len(templates),
            }

    async def get_category_templates(
        self, category_id: str, status: str = "active", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all templates belonging to a category"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        MATCH (c:Category {id: $category_id})
        MATCH (c)<-[bt:BELONGS_TO]-(t:Template)
        WHERE t.status = $status
        RETURN t
        ORDER BY t.precision DESC
        LIMIT $limit
        """

        async with self.driver.session() as session:
            result = await session.run(
                query, category_id=category_id, status=status, limit=limit
            )
            records = [record async for record in result]
            return [dict(record["t"]) for record in records]

    async def create_category(self, category_data: Dict[str, Any]) -> Optional[str]:
        """Create a category node"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        CREATE (c:Category {
            id: $id,
            name: $name,
            icon: $icon,
            description: $description,
            order: $order,
            created_at: datetime()
        })
        RETURN c.id as category_id
        """

        async with self.driver.session() as session:
            result = await session.run(query, **category_data)
            record = await result.single()
            return record["category_id"] if record else None

    async def create_framework(self, framework_data: Dict[str, Any]) -> Optional[str]:
        """Create a framework node"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        CREATE (f:Framework {
            id: $id,
            name: $name,
            type: $type,
            language: $language,
            version_range: $version_range,
            ecosystem: $ecosystem,
            created_at: datetime()
        })
        RETURN f.id as framework_id
        """

        async with self.driver.session() as session:
            result = await session.run(query, **framework_data)
            record = await result.single()
            return record["framework_id"] if record else None

    async def create_pattern(self, pattern_data: Dict[str, Any]) -> Optional[str]:
        """Create a pattern node"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        CREATE (p:Pattern {
            id: $id,
            name: $name,
            description: $description,
            category: $category,
            complexity_level: $complexity_level,
            use_cases: $use_cases,
            created_at: datetime()
        })
        RETURN p.id as pattern_id
        """

        async with self.driver.session() as session:
            result = await session.run(query, **pattern_data)
            record = await result.single()
            return record["pattern_id"] if record else None

    async def create_dependency(self, dependency_data: Dict[str, Any]) -> Optional[str]:
        """Create a dependency node"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        query = """
        CREATE (d:Dependency {
            id: $id,
            name: $name,
            language: $language,
            version_range: $version_range,
            type: $type,
            security_status: $security_status,
            created_at: datetime()
        })
        RETURN d.id as dependency_id
        """

        async with self.driver.session() as session:
            result = await session.run(query, **dependency_data)
            record = await result.single()
            return record["dependency_id"] if record else None

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")

        stats = {}

        async with self.driver.session() as session:
            # Node counts
            for label in ["Template", "TrezoComponent", "CustomComponent", "Pattern",
                         "Framework", "Dependency", "Category", "MasterPlan", "Atom", "User", "Project"]:
                result = await session.run(
                    f"MATCH (n:{label}) RETURN count(n) as count"
                )
                record = await result.single()
                stats[f"{label.lower()}_count"] = record["count"] if record else 0

            # Relationship counts
            result = await session.run(
                "MATCH ()-[r]->() RETURN count(r) as count"
            )
            record = await result.single()
            stats["relationship_count"] = record["count"] if record else 0

            # Average precision
            result = await session.run(
                "MATCH (t:Template) RETURN avg(t.precision) as avg_precision"
            )
            record = await result.single()
            stats["avg_template_precision"] = (
                float(record["avg_precision"]) if record and record["avg_precision"] else 0.0
            )

        return stats
