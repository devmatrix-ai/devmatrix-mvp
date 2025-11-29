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


@dataclass
class FixPattern:
    """
    Successful fix pattern for code generation errors.

    Gap 4 Implementation: Stores successful repairs to avoid re-computing
    fixes for similar errors. The fix can be looked up by error_signature
    before invoking LLM-based repair.

    Reference: LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 4
    """
    fix_id: str
    error_signature: str  # Hash of error context for lookup
    error_type: str  # "syntax_error", "runtime_error", "validation_error"
    error_message: str  # Original error message
    fix_strategy: str  # "add_import", "fix_type", "add_validation", "ast_patch", etc.
    fix_code: str  # The actual fix (code diff or full replacement)
    context: Dict[str, Any] = field(default_factory=dict)  # Entity, endpoint, file, etc.
    success_count: int = 1  # Times this fix worked
    failure_count: int = 0  # Times it was tried but failed
    confidence: float = 0.5  # Success rate derived score
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


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

    # =========================================================================
    # GAP 4: Fix Pattern Learning Methods
    # =========================================================================

    def _compute_error_signature(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compute a stable signature for an error to enable fix lookup.

        The signature is based on:
        - Error type (e.g., "NameError", "ValidationError")
        - Normalized error message (without line numbers, file paths)
        - Optional context (entity type, endpoint pattern)

        Args:
            error_type: Python exception type or error category
            error_message: Full error message
            context: Optional context dict with entity_type, endpoint_pattern, etc.

        Returns:
            SHA256 hash of normalized error components
        """
        import hashlib
        import re

        # Normalize error message:
        # - Remove line numbers
        # - Remove file paths
        # - Remove UUIDs
        # - Lowercase
        normalized_msg = error_message.lower()
        normalized_msg = re.sub(r'line \d+', 'line N', normalized_msg)
        normalized_msg = re.sub(r'/[^\s]+\.py', 'FILE.py', normalized_msg)
        normalized_msg = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', normalized_msg)

        # Build signature components
        components = [
            error_type.lower(),
            normalized_msg[:200],  # First 200 chars of normalized message
        ]

        # Add context if provided
        if context:
            if 'entity_type' in context:
                components.append(f"entity:{context['entity_type'].lower()}")
            if 'endpoint_pattern' in context:
                # Normalize endpoint pattern: /products/{id} -> /{entity}/{param}
                ep = re.sub(r'/\w+/', '/{entity}/', context['endpoint_pattern'])
                ep = re.sub(r'\{[^}]+\}', '{param}', ep)
                components.append(f"endpoint:{ep}")

        signature_input = '|'.join(components)
        return hashlib.sha256(signature_input.encode()).hexdigest()[:32]

    async def store_fix(self, fix: FixPattern) -> bool:
        """
        Store a successful fix pattern for future reuse.

        Gap 4 Implementation: Stores the fix in both Neo4j (for queries by signature)
        and Qdrant (for semantic similarity search).

        If a fix with the same signature already exists, increments success_count
        and updates last_used timestamp.

        Args:
            fix: FixPattern to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize metadata
            sanitized_metadata = self._sanitize_metadata(fix.metadata)
            sanitized_context = self._sanitize_metadata(fix.context)

            # Check if fix already exists (by signature)
            with self.neo4j_driver.session() as session:
                existing = session.run("""
                    MATCH (f:FixPattern {error_signature: $signature})
                    RETURN f.fix_id as fix_id, f.success_count as success_count
                """, signature=fix.error_signature).single()

                if existing:
                    # Update existing fix
                    session.run("""
                        MATCH (f:FixPattern {error_signature: $signature})
                        SET f.success_count = f.success_count + 1,
                            f.last_used = datetime(),
                            f.confidence = toFloat(f.success_count + 1) / toFloat(f.success_count + f.failure_count + 1)
                        RETURN f
                    """, signature=fix.error_signature)
                    self.logger.info(f"Updated existing fix pattern: {existing['fix_id']} (success_count: {existing['success_count'] + 1})")
                    return True

                # Create new fix pattern in Neo4j
                session.run("""
                    CREATE (f:FixPattern {
                        fix_id: $fix_id,
                        error_signature: $signature,
                        error_type: $error_type,
                        error_message: $error_message,
                        fix_strategy: $fix_strategy,
                        fix_code: $fix_code,
                        context: $context,
                        success_count: $success_count,
                        failure_count: $failure_count,
                        confidence: $confidence,
                        created_at: datetime(),
                        last_used: datetime()
                    })
                """, {
                    "fix_id": fix.fix_id,
                    "signature": fix.error_signature,
                    "error_type": fix.error_type,
                    "error_message": fix.error_message[:500],  # Truncate
                    "fix_strategy": fix.fix_strategy,
                    "fix_code": fix.fix_code[:2000],  # Truncate
                    "context": str(sanitized_context),
                    "success_count": fix.success_count,
                    "failure_count": fix.failure_count,
                    "confidence": fix.confidence
                })

            # Create embedding for semantic search
            fix_context = f"""
Error Type: {fix.error_type}
Error Message: {fix.error_message}
Fix Strategy: {fix.fix_strategy}
Fix Code:
{fix.fix_code[:500]}
""".strip()

            embedding = self.embedding_model.encode(fix_context).tolist()

            # Store in Qdrant
            payload = {
                "fix_id": fix.fix_id,
                "error_signature": fix.error_signature,
                "error_type": fix.error_type,
                "error_message": fix.error_message[:500],
                "fix_strategy": fix.fix_strategy,
                "fix_code": fix.fix_code[:1000],
                "success_count": fix.success_count,
                "confidence": fix.confidence,
                "type": "fix"
            }
            if sanitized_context:
                payload["context"] = sanitized_context

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )

            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )

            self.logger.info(f"Stored new fix pattern: {fix.fix_id} (strategy: {fix.fix_strategy})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store fix pattern: {e}")
            return False

    async def get_fix_for_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.6
    ) -> Optional[FixPattern]:
        """
        Look up a known fix for an error by signature.

        Gap 4 Implementation: First tries exact signature match (fast),
        then falls back to semantic similarity search if no exact match.

        Args:
            error_type: Error type (e.g., "NameError", "ValidationError")
            error_message: Full error message
            context: Optional context (entity_type, endpoint_pattern)
            min_confidence: Minimum confidence threshold (default 0.6)

        Returns:
            FixPattern if found with sufficient confidence, None otherwise
        """
        try:
            # Compute signature for exact lookup
            signature = self._compute_error_signature(error_type, error_message, context)

            # Try exact match first (fast)
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (f:FixPattern {error_signature: $signature})
                    WHERE f.confidence >= $min_confidence
                    RETURN f
                """, signature=signature, min_confidence=min_confidence)

                record = result.single()
                if record:
                    f = record["f"]
                    self.logger.info(f"Found exact fix match: {f['fix_id']} (confidence: {f['confidence']:.2f})")
                    return FixPattern(
                        fix_id=f["fix_id"],
                        error_signature=f["error_signature"],
                        error_type=f["error_type"],
                        error_message=f["error_message"],
                        fix_strategy=f["fix_strategy"],
                        fix_code=f["fix_code"],
                        success_count=f["success_count"],
                        failure_count=f["failure_count"],
                        confidence=f["confidence"]
                    )

            # Fall back to semantic similarity search
            query_context = f"""
Error Type: {error_type}
Error Message: {error_message}
""".strip()

            query_embedding = self.embedding_model.encode(query_context).tolist()

            results = self.qdrant.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match=MatchValue(value="fix")
                        )
                    ]
                ),
                limit=3
            )

            # Find best match above threshold
            for result in results:
                payload = result.payload
                if payload.get("confidence", 0) >= min_confidence and result.score >= 0.75:
                    self.logger.info(
                        f"Found semantic fix match: {payload['fix_id']} "
                        f"(similarity: {result.score:.2f}, confidence: {payload['confidence']:.2f})"
                    )
                    return FixPattern(
                        fix_id=payload["fix_id"],
                        error_signature=payload["error_signature"],
                        error_type=payload["error_type"],
                        error_message=payload["error_message"],
                        fix_strategy=payload["fix_strategy"],
                        fix_code=payload["fix_code"],
                        success_count=payload.get("success_count", 1),
                        failure_count=payload.get("failure_count", 0),
                        confidence=payload.get("confidence", 0.5)
                    )

            self.logger.debug(f"No fix found for error signature: {signature[:16]}...")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get fix for error: {e}")
            return None

    async def mark_fix_failed(self, error_signature: str) -> bool:
        """
        Mark a fix as failed (increment failure_count, recalculate confidence).

        Called when a fix was applied but didn't resolve the issue.

        Args:
            error_signature: Signature of the fix that failed

        Returns:
            True if updated, False otherwise
        """
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (f:FixPattern {error_signature: $signature})
                    SET f.failure_count = f.failure_count + 1,
                        f.confidence = toFloat(f.success_count) / toFloat(f.success_count + f.failure_count + 1)
                    RETURN f.confidence as new_confidence
                """, signature=error_signature)

                record = result.single()
                if record:
                    self.logger.info(f"Marked fix as failed, new confidence: {record['new_confidence']:.2f}")
                    return True
                return False

        except Exception as e:
            self.logger.error(f"Failed to mark fix as failed: {e}")
            return False

    async def get_fix_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored fix patterns.

        Returns:
            Dictionary with fix statistics
        """
        try:
            with self.neo4j_driver.session() as session:
                # Total fixes
                result = session.run("MATCH (f:FixPattern) RETURN count(f) AS total")
                total_fixes = result.single()["total"]

                # Fixes by strategy
                result = session.run("""
                    MATCH (f:FixPattern)
                    RETURN f.fix_strategy AS strategy, count(f) AS count
                    ORDER BY count DESC
                """)
                fixes_by_strategy = {record["strategy"]: record["count"] for record in result}

                # High confidence fixes
                result = session.run("""
                    MATCH (f:FixPattern)
                    WHERE f.confidence >= 0.8
                    RETURN count(f) AS high_confidence_count
                """)
                high_confidence = result.single()["high_confidence_count"]

                # Average success rate
                result = session.run("""
                    MATCH (f:FixPattern)
                    RETURN avg(f.confidence) AS avg_confidence
                """)
                avg_confidence = result.single()["avg_confidence"] or 0

                return {
                    "total_fixes": total_fixes,
                    "fixes_by_strategy": fixes_by_strategy,
                    "high_confidence_fixes": high_confidence,
                    "average_confidence": round(avg_confidence, 3)
                }

        except Exception as e:
            self.logger.error(f"Failed to get fix statistics: {e}")
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
