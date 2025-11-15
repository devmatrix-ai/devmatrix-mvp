"""
Neo4j Pattern Graph Client

Wrapper for Neo4j graph database integration.
Connects to EXISTING infrastructure with 30,071 pattern nodes.

Schema:
- Pattern nodes (30,071): Code patterns from 9 repositories
- Dependency relationships (84): Pattern dependencies
- Tag nodes (21): Classification tags
- Category nodes (13): Domain categories
- Framework nodes (6): Technology frameworks
- Repository nodes (9): Source repositories
"""

from typing import List, Dict, Any, Optional
import logging
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

from src.cognitive.config import settings

logger = logging.getLogger(__name__)


class Neo4jPatternClient:
    """
    Neo4j client for pattern graph operations.

    Provides methods to:
    - Query existing 30K+ pattern nodes
    - Navigate dependency relationships
    - Build DAG structures for task orchestration
    - Retrieve patterns by category, framework, language
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j Bolt URI (default from settings)
            user: Neo4j username (default from settings)
            password: Neo4j password (default from settings)
            database: Neo4j database name (default from settings)
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database or settings.neo4j_database
        self._driver: Optional[Driver] = None

    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def get_patterns_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve patterns by category from existing 30K+ patterns.

        Args:
            category: Category name (e.g., "auth", "api", "database")
            limit: Maximum number of patterns to return

        Returns:
            List of pattern nodes with properties
        """
        query = """
        MATCH (p:Pattern)-[:IN_CATEGORY]->(c:Category {name: $category})
        RETURN p.pattern_id AS pattern_id,
               p.name AS name,
               p.pattern_type AS pattern_type,
               p.language AS language,
               p.framework AS framework,
               p.code AS code,
               p.complexity AS complexity,
               p.loc AS loc
        ORDER BY p.complexity ASC, p.loc ASC
        LIMIT $limit
        """
        return self._execute_query(query, {"category": category, "limit": limit})

    def get_patterns_by_framework(self, framework: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve patterns by framework.

        Args:
            framework: Framework name (e.g., "fastapi", "nextjs", "react")
            limit: Maximum number of patterns to return

        Returns:
            List of pattern nodes
        """
        query = """
        MATCH (p:Pattern)-[:USES_FRAMEWORK]->(f:Framework {name: $framework})
        RETURN p.pattern_id AS pattern_id,
               p.name AS name,
               p.pattern_type AS pattern_type,
               p.code AS code,
               p.complexity AS complexity
        ORDER BY p.complexity ASC
        LIMIT $limit
        """
        return self._execute_query(query, {"framework": framework, "limit": limit})

    def get_dependencies(self, pattern_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependencies for a pattern.

        Args:
            pattern_id: Pattern identifier

        Returns:
            List of dependent pattern nodes
        """
        query = """
        MATCH (p:Pattern {pattern_id: $pattern_id})-[:DEPENDS_ON]->(dep:Pattern)
        RETURN dep.pattern_id AS pattern_id,
               dep.name AS name,
               dep.pattern_type AS pattern_type
        """
        return self._execute_query(query, {"pattern_id": pattern_id})

    def get_dependency_chain(self, pattern_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Get full dependency chain for a pattern.

        Args:
            pattern_id: Pattern identifier
            max_depth: Maximum traversal depth

        Returns:
            List of all dependencies in chain
        """
        query = """
        MATCH path=(p:Pattern {pattern_id: $pattern_id})-[:DEPENDS_ON*1..{max_depth}]->(dep:Pattern)
        RETURN DISTINCT dep.pattern_id AS pattern_id,
               dep.name AS name,
               length(path) AS depth
        ORDER BY depth ASC
        """.format(max_depth=max_depth)
        return self._execute_query(query, {"pattern_id": pattern_id})

    def create_dag(self, task_nodes: List[Dict[str, Any]]) -> str:
        """
        Create DAG structure for atomic tasks in Neo4j.

        Args:
            task_nodes: List of task dictionaries with keys:
                - task_id: Unique task identifier
                - name: Task name
                - dependencies: List of task_id dependencies

        Returns:
            DAG identifier
        """
        # Create AtomicTask nodes
        for task in task_nodes:
            create_node_query = """
            MERGE (t:AtomicTask {task_id: $task_id})
            SET t.name = $name,
                t.created_at = timestamp()
            """
            self._execute_query(create_node_query, {
                "task_id": task["task_id"],
                "name": task["name"]
            })

        # Create DEPENDS_ON relationships
        for task in task_nodes:
            for dep_id in task.get("dependencies", []):
                create_rel_query = """
                MATCH (t:AtomicTask {task_id: $task_id})
                MATCH (dep:AtomicTask {task_id: $dep_id})
                MERGE (t)-[:DEPENDS_ON]->(dep)
                """
                self._execute_query(create_rel_query, {
                    "task_id": task["task_id"],
                    "dep_id": dep_id
                })

        logger.info(f"Created DAG with {len(task_nodes)} nodes")
        return f"dag_{task_nodes[0]['task_id']}" if task_nodes else "dag_empty"

    def detect_cycles(self, task_id: str) -> bool:
        """
        Detect circular dependencies in DAG.

        Args:
            task_id: Starting task identifier

        Returns:
            True if cycle detected, False otherwise
        """
        query = """
        MATCH path=(t:AtomicTask {task_id: $task_id})-[:DEPENDS_ON*]->(t)
        RETURN count(path) AS cycle_count
        """
        result = self._execute_query(query, {"task_id": task_id})
        cycle_count = result[0]["cycle_count"] if result else 0
        return cycle_count > 0

    def get_pattern_count(self) -> int:
        """
        Get total pattern count in database.

        Returns:
            Number of Pattern nodes
        """
        query = "MATCH (p:Pattern) RETURN count(p) AS count"
        result = self._execute_query(query)
        return result[0]["count"] if result else 0

    def healthcheck(self) -> bool:
        """
        Verify Neo4j connection and data availability.

        Returns:
            True if healthy, False otherwise
        """
        try:
            count = self.get_pattern_count()
            logger.info(f"Neo4j healthcheck: {count} patterns available")
            return count > 0
        except Exception as e:
            logger.error(f"Neo4j healthcheck failed: {e}")
            return False
