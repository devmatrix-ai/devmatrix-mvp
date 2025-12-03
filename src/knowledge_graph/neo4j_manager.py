"""
Neo4jManager - Centralized Neo4j connection for Learning System.

Bug #205: This module was missing, causing "No module named 'src.knowledge_graph'"
and Neo4j Queries: 0 in pipeline runs.

Provides:
- Connection pooling and reuse
- Graceful degradation when Neo4j unavailable
- Query execution with error handling

Created: 2025-12-03
Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_IMPLEMENTATION_PLAN.md
"""

import os
import logging
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Neo4j driver - optional dependency
try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None


class Neo4jManager:
    """
    Centralized Neo4j connection manager for the Learning System.
    
    Usage:
        manager = Neo4jManager()
        result = manager.execute_query("MATCH (n) RETURN n LIMIT 10")
        manager.close()
    
    Or with singleton:
        manager = get_neo4j_manager()
        result = manager.execute_query(...)
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j URI (default: from NEO4J_URI env or bolt://localhost:7687)
            user: Neo4j user (default: from NEO4J_USER env or neo4j)
            password: Neo4j password (default: from NEO4J_PASSWORD env or devmatrix123)
        """
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        
        self._driver = None
        self._connected = False
        self._query_count = 0
        
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Neo4j."""
        if not NEO4J_AVAILABLE:
            logger.warning("📚 Neo4jManager: neo4j driver not installed")
            return
        
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            with self._driver.session() as session:
                session.run("RETURN 1")
            self._connected = True
            logger.info(f"📚 Neo4jManager: Connected to {self.uri}")
        except ServiceUnavailable as e:
            logger.warning(f"📚 Neo4jManager: Service unavailable at {self.uri}: {e}")
            self._driver = None
        except AuthError as e:
            logger.warning(f"📚 Neo4jManager: Auth failed for {self.user}@{self.uri}: {e}")
            self._driver = None
        except Exception as e:
            logger.warning(f"📚 Neo4jManager: Connection failed: {e}")
            self._driver = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self._connected and self._driver is not None
    
    @property
    def query_count(self) -> int:
        """Number of queries executed."""
        return self._query_count
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        database: str = "neo4j"
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            params: Query parameters
            database: Database name (default: neo4j)
            
        Returns:
            List of result records as dicts
        """
        if not self.is_connected:
            logger.debug("Neo4jManager: Not connected, query skipped")
            return []
        
        try:
            with self._driver.session(database=database) as session:
                result = session.run(query, params or {})
                records = [dict(record) for record in result]
                self._query_count += 1
                return records
        except Exception as e:
            logger.warning(f"Neo4jManager: Query failed: {e}")
            return []
    
    def execute_write(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        database: str = "neo4j"
    ) -> bool:
        """
        Execute a write query (MERGE, CREATE, etc).
        
        Args:
            query: Cypher write query
            params: Query parameters
            database: Database name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            with self._driver.session(database=database) as session:
                session.run(query, params or {})
                self._query_count += 1
                return True
        except Exception as e:
            logger.warning(f"Neo4jManager: Write failed: {e}")
            return False
    
    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("📚 Neo4jManager: Connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance
_neo4j_manager: Optional[Neo4jManager] = None


def get_neo4j_manager() -> Neo4jManager:
    """Get singleton Neo4jManager instance."""
    global _neo4j_manager
    if _neo4j_manager is None:
        _neo4j_manager = Neo4jManager()
    return _neo4j_manager

