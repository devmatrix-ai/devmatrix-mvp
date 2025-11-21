"""
Error Pattern Store - Cognitive Feedback Loop for Code Generation

Stores and retrieves code generation errors and successful patterns using:
- Neo4j: Structured error/success nodes with relationships
- Qdrant: Semantic embeddings for similarity search
- GraphCodeBERT: Code-aware embeddings (768-dim)

Purpose: Enable ML-driven learning from code generation failures
"""

import asyncio
import uuid
import warnings
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from neo4j import GraphDatabase

from src.cognitive.config.settings import CognitiveSettings
from src.observability import get_logger

# P3 FIX: Use GraphCodeBERT singleton to avoid multiple loads
from src.models.graphcodebert_singleton import get_graphcodebert


logger = get_logger("services.error_pattern_store")


@dataclass
class ErrorPattern:
    """Code generation error pattern."""
    error_id: str
    task_id: str
    task_description: str
    error_type: str  # "syntax_error", "validation_error", "runtime_error"
    error_message: str
    failed_code: str
    attempt: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuccessPattern:
    """Successful code generation pattern."""
    success_id: str
    task_id: str
    task_description: str
    generated_code: str
    quality_score: float  # 0.0-1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimilarError:
    """Similar error found in pattern store."""
    error_id: str
    task_description: str
    error_message: str
    failed_code: str
    similarity_score: float
    how_it_was_fixed: Optional[str] = None


class ErrorPatternStore:
    """
    Store and retrieve error patterns for code generation learning.

    Architecture:
    - Neo4j: Structured storage with relationships
    - Qdrant: Semantic similarity search
    - GraphCodeBERT: Code-aware 768-dim embeddings
    """

    COLLECTION_NAME = "code_generation_feedback"
    EMBEDDING_DIM = 768  # GraphCodeBERT dimension

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
    ):
        """
        Initialize error pattern store.

        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.logger = logger
        self.settings = CognitiveSettings()

        # P3 FIX: Use GraphCodeBERT singleton (avoids multiple loads)
        # BEFORE: Each ErrorPatternStore instance loaded model (~10-30s + 300MB RAM)
        # AFTER: Singleton loads once, all instances share (~50% startup time reduction)
        try:
            self.logger.info("Loading GraphCodeBERT singleton...")
            self.embedding_model = get_graphcodebert()
            self.logger.info("✅ GraphCodeBERT singleton loaded (768-dim embeddings)")
        except Exception as e:
            self.logger.error(f"Failed to load GraphCodeBERT singleton: {e}")
            raise

        # Initialize Qdrant client
        try:
            self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
            self._ensure_collection_exists()
            self.logger.info(f"Connected to Qdrant at {qdrant_host}:{qdrant_port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Qdrant: {e}")
            raise

        # Initialize Neo4j driver
        try:
            self.neo4j_driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            self.logger.info(f"Connected to Neo4j at {neo4j_uri}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def _ensure_collection_exists(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        try:
            collections = self.qdrant.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.COLLECTION_NAME not in collection_names:
                self.qdrant.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.EMBEDDING_DIM,
                        distance=Distance.COSINE
                    )
                )
                self.logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")
            else:
                self.logger.info(f"Qdrant collection exists: {self.COLLECTION_NAME}")
        except Exception as e:
            self.logger.warning(f"Could not ensure collection exists: {e}")

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to ensure all keys and values are serializable.

        Handles problematic types like slice objects that can't be used as dict keys
        or stored in vector databases.

        Args:
            metadata: Original metadata dictionary

        Returns:
            Sanitized metadata with all serializable values
        """
        if not metadata:
            return {}

        sanitized = {}
        for key, value in metadata.items():
            # Ensure key is string (not slice or other non-hashable)
            if isinstance(key, slice):
                sanitized_key = f"slice_{key.start}_{key.stop}_{key.step}"
            elif not isinstance(key, str):
                sanitized_key = str(key)
            else:
                sanitized_key = key

            # Sanitize value
            if isinstance(value, slice):
                sanitized[sanitized_key] = f"slice({value.start}, {value.stop}, {value.step})"
            elif isinstance(value, (str, int, float, bool, type(None))):
                sanitized[sanitized_key] = value
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[sanitized_key] = self._sanitize_metadata(value)
            elif isinstance(value, (list, tuple)):
                # Sanitize list/tuple elements
                sanitized[sanitized_key] = [self._sanitize_value(item) for item in value]
            else:
                # Convert any other type to string
                sanitized[sanitized_key] = str(value)

        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        """Helper to sanitize individual values in lists/tuples."""
        if isinstance(value, slice):
            return f"slice({value.start}, {value.stop}, {value.step})"
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            return self._sanitize_metadata(value)
        elif isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        else:
            return str(value)

    def close(self) -> None:
        """Close connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            self.logger.info("Closed Neo4j connection")

    async def store_error(self, error: ErrorPattern) -> bool:
        """
        Store code generation error in Neo4j + Qdrant.

        Args:
            error: Error pattern to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize metadata to prevent unhashable type errors
            sanitized_metadata = self._sanitize_metadata(error.metadata)

            # Create embedding from error context
            error_context = f"""
Task: {error.task_description}
Error Type: {error.error_type}
Error Message: {error.error_message}
Failed Code:
{error.failed_code}
""".strip()

            embedding = self.embedding_model.encode(error_context).tolist()

            # Store in Qdrant with metadata
            payload = {
                "error_id": error.error_id,
                "task_id": error.task_id,
                "task_description": error.task_description,
                "error_type": error.error_type,
                "error_message": error.error_message,
                "failed_code": error.failed_code[:500],  # Truncate for storage
                "attempt": error.attempt,
                "timestamp": error.timestamp.isoformat(),
                "type": "error"
            }
            # Add sanitized metadata if present
            if sanitized_metadata:
                payload["metadata"] = sanitized_metadata

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )

            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )

            # Store in Neo4j
            with self.neo4j_driver.session() as session:
                session.run("""
                    CREATE (e:CodeGenerationError {
                        error_id: $error_id,
                        task_id: $task_id,
                        task_description: $task_description,
                        error_type: $error_type,
                        error_message: $error_message,
                        failed_code: $failed_code,
                        attempt: $attempt,
                        timestamp: datetime($timestamp)
                    })
                """, {
                    "error_id": error.error_id,
                    "task_id": error.task_id,
                    "task_description": error.task_description,
                    "error_type": error.error_type,
                    "error_message": error.error_message,
                    "failed_code": error.failed_code,
                    "attempt": error.attempt,
                    "timestamp": error.timestamp.isoformat()
                })

            self.logger.info(f"Stored error pattern: {error.error_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store error pattern: {e}")
            return False

    async def store_success(self, success: SuccessPattern) -> bool:
        """
        Store successful code generation in Neo4j + Qdrant.

        Args:
            success: Success pattern to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize metadata to prevent unhashable type errors
            sanitized_metadata = self._sanitize_metadata(success.metadata)

            # Create embedding from success context
            success_context = f"""
Task: {success.task_description}
Generated Code:
{success.generated_code}
""".strip()

            embedding = self.embedding_model.encode(success_context).tolist()

            # Store in Qdrant
            payload = {
                "success_id": success.success_id,
                "task_id": success.task_id,
                "task_description": success.task_description,
                "generated_code": success.generated_code[:1000],  # Truncate
                "quality_score": success.quality_score,
                "timestamp": success.timestamp.isoformat(),
                "type": "success"
            }
            # Add sanitized metadata if present
            if sanitized_metadata:
                payload["metadata"] = sanitized_metadata

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )

            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )

            # Store in Neo4j
            with self.neo4j_driver.session() as session:
                session.run("""
                    CREATE (s:SuccessfulCode {
                        success_id: $success_id,
                        task_id: $task_id,
                        task_description: $task_description,
                        generated_code: $generated_code,
                        quality_score: $quality_score,
                        timestamp: datetime($timestamp)
                    })
                """, {
                    "success_id": success.success_id,
                    "task_id": success.task_id,
                    "task_description": success.task_description,
                    "generated_code": success.generated_code,
                    "quality_score": success.quality_score,
                    "timestamp": success.timestamp.isoformat()
                })

            self.logger.info(f"Stored success pattern: {success.success_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store success pattern: {e}")
            return False

    async def search_similar_errors(
        self,
        task_description: str,
        error_message: str,
        top_k: int = 3
    ) -> List[SimilarError]:
        """
        Search for similar errors using semantic similarity.

        Args:
            task_description: Current task description
            error_message: Current error message
            top_k: Number of similar errors to return

        Returns:
            List of similar errors found
        """
        try:
            # Create query embedding
            query_context = f"""
Task: {task_description}
Error: {error_message}
""".strip()

            query_embedding = self.embedding_model.encode(query_context).tolist()

            # Search in Qdrant (filter for errors only)
            results = self.qdrant.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match=MatchValue(value="error")
                        )
                    ]
                ),
                limit=top_k
            )

            similar_errors = []
            for result in results:
                payload = result.payload
                similar_errors.append(SimilarError(
                    error_id=payload["error_id"],
                    task_description=payload["task_description"],
                    error_message=payload["error_message"],
                    failed_code=payload.get("failed_code", ""),
                    similarity_score=result.score
                ))

            self.logger.info(f"Found {len(similar_errors)} similar errors")
            return similar_errors

        except Exception as e:
            self.logger.error(f"Failed to search similar errors: {e}")
            return []

    async def search_successful_patterns(
        self,
        task_description: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for successful code generation patterns.

        Args:
            task_description: Current task description
            top_k: Number of successful patterns to return

        Returns:
            List of successful patterns
        """
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode(task_description).tolist()

            # Search in Qdrant (filter for successes only)
            results = self.qdrant.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match=MatchValue(value="success")
                        )
                    ]
                ),
                limit=top_k
            )

            patterns = []
            for result in results:
                payload = result.payload
                patterns.append({
                    "success_id": payload["success_id"],
                    "task_description": payload["task_description"],
                    "generated_code": payload.get("generated_code", ""),
                    "quality_score": payload.get("quality_score", 0.0),
                    "similarity_score": result.score
                })

            self.logger.info(f"Found {len(patterns)} successful patterns")
            return patterns

        except Exception as e:
            self.logger.error(f"Failed to search successful patterns: {e}")
            return []

    async def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored error patterns.

        Returns:
            Dictionary with error statistics
        """
        try:
            with self.neo4j_driver.session() as session:
                # Total errors
                result = session.run("MATCH (e:CodeGenerationError) RETURN count(e) AS total")
                total_errors = result.single()["total"]

                # Errors by type
                result = session.run("""
                    MATCH (e:CodeGenerationError)
                    RETURN e.error_type AS type, count(e) AS count
                    ORDER BY count DESC
                """)
                errors_by_type = {record["type"]: record["count"] for record in result}

                # Recent errors (last 24h)
                result = session.run("""
                    MATCH (e:CodeGenerationError)
                    WHERE e.timestamp > datetime() - duration('P1D')
                    RETURN count(e) AS recent_count
                """)
                recent_errors = result.single()["recent_count"]

                return {
                    "total_errors": total_errors,
                    "errors_by_type": errors_by_type,
                    "recent_errors_24h": recent_errors
                }

        except Exception as e:
            self.logger.error(f"Failed to get error statistics: {e}")
            return {}


# Singleton instance
_error_pattern_store: Optional[ErrorPatternStore] = None


def get_error_pattern_store() -> ErrorPatternStore:
    """Get singleton instance of ErrorPatternStore."""
    global _error_pattern_store
    if _error_pattern_store is None:
        settings = CognitiveSettings()
        _error_pattern_store = ErrorPatternStore(
            qdrant_host=getattr(settings, 'qdrant_host', 'localhost'),
            qdrant_port=getattr(settings, 'qdrant_port', 6333),
            neo4j_uri=getattr(settings, 'neo4j_uri', 'bolt://localhost:7687'),
            neo4j_user=getattr(settings, 'neo4j_user', 'neo4j'),
            neo4j_password=getattr(settings, 'neo4j_password', 'password')
        )
    return _error_pattern_store
