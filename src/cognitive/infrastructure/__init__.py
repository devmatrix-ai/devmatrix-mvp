"""
Cognitive Architecture Infrastructure Clients

Wrappers for external infrastructure services:
- Neo4j: Graph database for pattern dependencies and DAG construction
- Qdrant: Vector database for semantic pattern search

Both services use EXISTING data:
- Neo4j: 30,071 pattern nodes with relationships already stored
- Qdrant: 21,624 patterns with embeddings already indexed
"""

from .neo4j_client import Neo4jPatternClient
from .qdrant_client import QdrantPatternClient

__all__ = ["Neo4jPatternClient", "QdrantPatternClient"]
