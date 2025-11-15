"""
Pattern Bank with Qdrant Integration

Auto-evolutionary knowledge base for code generation patterns.
Stores successful patterns as embeddings in Qdrant vector database.

Spec Reference: Section 3.2 - Pattern Bank
Target Coverage: >90% (TDD approach)
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from sentence_transformers import SentenceTransformer

from src.cognitive.config.settings import settings
from src.cognitive.signatures.semantic_signature import (
    SemanticTaskSignature,
    compute_semantic_hash,
)

logger = logging.getLogger(__name__)


@dataclass
class StoredPattern:
    """
    Stored pattern retrieved from pattern bank.

    Represents a successfully validated code pattern with metadata
    for tracking usage and effectiveness.
    """

    pattern_id: str
    signature: SemanticTaskSignature
    code: str
    success_rate: float
    similarity_score: float
    usage_count: int
    created_at: datetime
    domain: str


class PatternBank:
    """
    Pattern Bank with Qdrant vector database integration.

    Auto-evolutionary knowledge base that stores and retrieves successful
    code generation patterns using semantic embeddings.

    **Core Features**:
    - Pattern storage with ≥95% success rate threshold
    - Semantic similarity search (Sentence Transformers embeddings)
    - Hybrid search (vector + metadata filtering)
    - Usage tracking and metrics
    - Auto-evolution through feedback loops

    **Example Usage**:
    ```python
    # Initialize pattern bank
    bank = PatternBank()
    bank.connect()
    bank.create_collection()

    # Store successful pattern
    pattern_id = bank.store_pattern(
        signature=my_signature,
        code="def validate_email(...)...",
        success_rate=0.97
    )

    # Search for similar patterns
    matches = bank.search_patterns(
        query_signature,
        top_k=5,
        similarity_threshold=0.85
    )

    # Hybrid search with domain filter
    filtered = bank.hybrid_search(
        query_signature,
        domain="authentication",
        top_k=3
    )
    ```

    **Spec Compliance**:
    - Qdrant collection: semantic_patterns (768-dim Sentence Transformers)
    - Distance metric: Cosine similarity
    - Success threshold: ≥95% for storage
    - Similarity threshold: ≥85% for retrieval
    - Metadata: purpose, code, domain, success_rate, usage_count, created_at
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize Pattern Bank.

        Args:
            collection_name: Qdrant collection name (default: from settings)
            embedding_model: Sentence Transformers model (default: from settings)
        """
        self.collection_name = collection_name or settings.qdrant_collection_semantic
        self.embedding_dimension = settings.embedding_dimension
        self.embedding_model_name = embedding_model or settings.embedding_model

        # Qdrant client (initialized on connect())
        self.client: Optional[QdrantClient] = None
        self.is_connected = False

        # Sentence Transformers encoder for embeddings
        self.encoder = SentenceTransformer(self.embedding_model_name)

        logger.info(
            f"Initialized PatternBank with collection '{self.collection_name}', "
            f"model '{self.embedding_model_name}'"
        )

    def connect(self) -> None:
        """
        Connect to Qdrant vector database.

        Raises:
            ConnectionError: If connection to Qdrant fails
        """
        try:
            self.client = QdrantClient(
                host=settings.qdrant_host, port=settings.qdrant_port
            )

            # Verify connection
            self.client.get_collections()
            self.is_connected = True

            logger.info(
                f"Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Failed to connect to Qdrant: {e}")

    def create_collection(self) -> None:
        """
        Create Qdrant collection for semantic patterns.

        Creates collection with:
        - 768 dimensions (Sentence Transformers)
        - Cosine distance metric
        - Metadata indexes for domain, success_rate filtering
        """
        if not self.is_connected:
            self.connect()

        try:
            # Check if collection already exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return

            # Create new collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension, distance=Distance.COSINE
                ),
            )

            logger.info(
                f"Created collection '{self.collection_name}' "
                f"({self.embedding_dimension}-dim, Cosine)"
            )

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def delete_collection(self) -> None:
        """Delete Qdrant collection (use with caution)."""
        if not self.is_connected:
            self.connect()

        self.client.delete_collection(collection_name=self.collection_name)
        logger.warning(f"Deleted collection '{self.collection_name}'")

    def store_pattern(
        self, signature: SemanticTaskSignature, code: str, success_rate: float
    ) -> str:
        """
        Store successful pattern in pattern bank.

        Only stores patterns with success_rate ≥ 95% (MVP threshold).

        Args:
            signature: Semantic task signature
            code: Generated code (validated and successful)
            success_rate: Validation success rate (must be ≥ 0.95)

        Returns:
            pattern_id: Unique identifier for stored pattern

        Raises:
            ValueError: If success_rate < 95%

        Example:
        ```python
        pattern_id = bank.store_pattern(
            signature=email_validation_sig,
            code="def validate_email(email: str) -> bool: ...",
            success_rate=0.97
        )
        ```
        """
        # Validate success rate threshold
        if success_rate < settings.cpie_precision_threshold:
            raise ValueError(
                f"success_rate must be ≥ {settings.cpie_precision_threshold} "
                f"(got {success_rate})"
            )

        # Generate pattern ID
        pattern_id = f"pat_{uuid.uuid4().hex[:12]}"

        # Compute semantic hash
        semantic_hash = compute_semantic_hash(signature)

        # Create embedding from signature purpose + code
        embedding_text = f"{signature.purpose}\n\n{code}"
        embedding = self.encoder.encode(embedding_text).tolist()

        # Create metadata
        metadata = {
            "pattern_id": pattern_id,
            "purpose": signature.purpose,
            "intent": signature.intent,
            "domain": signature.domain,
            "code": code,
            "success_rate": success_rate,
            "usage_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "semantic_hash": semantic_hash,
        }

        # Store in Qdrant
        self._store_in_qdrant(embedding, metadata, pattern_id)

        logger.info(
            f"Stored pattern {pattern_id}: {signature.purpose[:50]} "
            f"(success={success_rate:.2%})"
        )

        return pattern_id

    def _store_in_qdrant(
        self, embedding: List[float], metadata: Dict[str, Any], pattern_id: str
    ) -> None:
        """Internal method to store vector in Qdrant."""
        if not self.is_connected:
            self.connect()

        point = PointStruct(id=pattern_id, vector=embedding, payload=metadata)

        self.client.upsert(collection_name=self.collection_name, points=[point])

    def search_patterns(
        self,
        signature: SemanticTaskSignature,
        top_k: int = 5,
        similarity_threshold: float = 0.85,
    ) -> List[StoredPattern]:
        """
        Search for similar patterns using semantic similarity.

        Args:
            signature: Query signature
            top_k: Maximum number of results (default: 5)
            similarity_threshold: Minimum similarity score (default: 0.85)

        Returns:
            List of StoredPattern sorted by similarity (descending)

        Example:
        ```python
        matches = bank.search_patterns(
            my_signature,
            top_k=5,
            similarity_threshold=0.85
        )

        for pattern in matches:
            print(f"Match: {pattern.purpose} (similarity={pattern.similarity_score})")
        ```
        """
        if not self.is_connected:
            self.connect()

        # Create query embedding
        query_text = f"{signature.purpose}"
        query_embedding = self.encoder.encode(query_text).tolist()

        # Search Qdrant
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=similarity_threshold,
        )

        # Convert to StoredPattern objects
        patterns = []
        for hit in search_result:
            pattern = self._hit_to_stored_pattern(hit, similarity_score=hit.score)
            patterns.append(pattern)

            # Increment usage count
            self._increment_usage_count(hit.id)

        logger.info(
            f"Found {len(patterns)} patterns for '{signature.purpose[:50]}' "
            f"(threshold={similarity_threshold})"
        )

        return patterns

    def hybrid_search(
        self,
        signature: SemanticTaskSignature,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> List[StoredPattern]:
        """
        Hybrid search combining vector similarity and metadata filtering.

        Scoring: 70% vector similarity + 30% metadata relevance

        Args:
            signature: Query signature
            domain: Optional domain filter
            top_k: Maximum results

        Returns:
            List of StoredPattern with combined scores

        Example:
        ```python
        auth_patterns = bank.hybrid_search(
            my_signature,
            domain="authentication",
            top_k=3
        )
        ```
        """
        if not self.is_connected:
            self.connect()

        # Create query embedding
        query_text = f"{signature.purpose}"
        query_embedding = self.encoder.encode(query_text).tolist()

        # Build filter for domain if specified
        search_filter = None
        if domain:
            search_filter = Filter(
                must=[FieldCondition(key="domain", match=MatchValue(value=domain))]
            )

        # Search with optional filter
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
        )

        # Convert to StoredPattern with hybrid scoring
        patterns = []
        for hit in search_result:
            vector_score = hit.score
            metadata_score = self._metadata_score(hit.payload, signature, domain)

            # Hybrid score: 70% vector + 30% metadata
            final_score = 0.7 * vector_score + 0.3 * metadata_score

            pattern = self._hit_to_stored_pattern(hit, similarity_score=final_score)
            pattern.similarity_score = final_score  # Override with hybrid score
            patterns.append(pattern)

            # Increment usage count
            self._increment_usage_count(hit.id)

        # Sort by hybrid score
        patterns.sort(key=lambda p: p.similarity_score, reverse=True)

        logger.info(
            f"Hybrid search found {len(patterns)} patterns "
            f"(domain={domain}, top_k={top_k})"
        )

        return patterns

    def _vector_search(
        self, signature: SemanticTaskSignature, top_k: int
    ) -> List[Dict]:
        """Internal vector search (for testing)."""
        query_embedding = self.encoder.encode(f"{signature.purpose}").tolist()
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
        )
        return [{"pattern_id": r.id, "score": r.score} for r in results]

    def _metadata_score(
        self, payload: Dict, signature: SemanticTaskSignature, domain: Optional[str]
    ) -> float:
        """
        Calculate metadata relevance score.

        Factors:
        - Domain match (if specified)
        - Intent match
        - Success rate

        Returns:
            Score in range [0.0, 1.0]
        """
        score = 0.0

        # Domain match (40%)
        if domain and payload.get("domain") == domain:
            score += 0.4

        # Intent match (30%)
        if payload.get("intent") == signature.intent:
            score += 0.3

        # Success rate contribution (30%)
        score += 0.3 * payload.get("success_rate", 0.0)

        return min(score, 1.0)

    def _increment_usage_count(self, pattern_id: str) -> None:
        """Increment usage count for pattern."""
        try:
            # Get current pattern
            result = self.client.retrieve(
                collection_name=self.collection_name, ids=[pattern_id]
            )

            if result:
                current_count = result[0].payload.get("usage_count", 0)
                new_count = current_count + 1

                # Update payload
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload={"usage_count": new_count},
                    points=[pattern_id],
                )

                logger.debug(f"Incremented usage_count for {pattern_id}: {new_count}")

        except Exception as e:
            logger.warning(f"Failed to increment usage_count for {pattern_id}: {e}")

    def _hit_to_stored_pattern(self, hit: Any, similarity_score: float) -> StoredPattern:
        """Convert Qdrant search hit to StoredPattern object."""
        payload = hit.payload

        # Reconstruct signature from payload
        signature = SemanticTaskSignature(
            purpose=payload["purpose"],
            intent=payload["intent"],
            inputs={},  # Not stored in pattern bank
            outputs={},  # Not stored in pattern bank
            domain=payload["domain"],
        )

        return StoredPattern(
            pattern_id=payload["pattern_id"],
            signature=signature,
            code=payload["code"],
            success_rate=payload["success_rate"],
            similarity_score=similarity_score,
            usage_count=payload.get("usage_count", 0),
            created_at=datetime.fromisoformat(payload["created_at"]),
            domain=payload["domain"],
        )

    def get_pattern_by_id(self, pattern_id: str) -> Optional[StoredPattern]:
        """
        Retrieve specific pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            StoredPattern or None if not found
        """
        if not self.is_connected:
            self.connect()

        try:
            result = self.client.retrieve(
                collection_name=self.collection_name, ids=[pattern_id]
            )

            if result:
                hit = result[0]
                return self._hit_to_stored_pattern(hit, similarity_score=1.0)

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve pattern {pattern_id}: {e}")
            return None

    def update_pattern_success(self, pattern_id: str, new_success_rate: float) -> None:
        """
        Update success rate for existing pattern.

        Args:
            pattern_id: Pattern identifier
            new_success_rate: Updated success rate
        """
        if not self.is_connected:
            self.connect()

        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"success_rate": new_success_rate},
            points=[pattern_id],
        )

        logger.info(f"Updated {pattern_id} success_rate to {new_success_rate:.2%}")

    def get_pattern_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated pattern bank metrics.

        Returns:
            Dictionary with metrics:
            - total_patterns: Total patterns stored
            - avg_success_rate: Average success rate
            - avg_usage_count: Average usage count
            - domain_distribution: Patterns per domain
            - most_used_patterns: Top 10 by usage_count

        Example:
        ```python
        metrics = bank.get_pattern_metrics()
        print(f"Total patterns: {metrics['total_patterns']}")
        print(f"Avg success rate: {metrics['avg_success_rate']:.2%}")
        ```
        """
        if not self.is_connected:
            self.connect()

        # Get collection info
        collection_info = self.client.get_collection(self.collection_name)
        total_patterns = collection_info.points_count

        # Scroll through all points to calculate metrics
        # Note: For production, implement pagination for large datasets
        scroll_result = self.client.scroll(
            collection_name=self.collection_name, limit=total_patterns or 100
        )

        points = scroll_result[0]

        # Calculate aggregated metrics
        total_success = 0.0
        total_usage = 0
        domain_counts: Dict[str, int] = {}
        pattern_usage: List[tuple] = []

        for point in points:
            payload = point.payload

            total_success += payload.get("success_rate", 0.0)
            usage = payload.get("usage_count", 0)
            total_usage += usage

            # Domain distribution
            domain = payload.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Track for most_used_patterns
            pattern_usage.append(
                (payload.get("pattern_id"), payload.get("purpose", ""), usage)
            )

        # Calculate averages
        avg_success = total_success / total_patterns if total_patterns > 0 else 0.0
        avg_usage = total_usage / total_patterns if total_patterns > 0 else 0.0

        # Sort and get top 10 most used
        pattern_usage.sort(key=lambda x: x[2], reverse=True)
        most_used = [
            {"pattern_id": pid, "purpose": purpose, "usage_count": count}
            for pid, purpose, count in pattern_usage[:10]
        ]

        metrics = {
            "total_patterns": total_patterns,
            "avg_success_rate": round(avg_success, 3),
            "avg_usage_count": round(avg_usage, 2),
            "domain_distribution": domain_counts,
            "most_used_patterns": most_used,
        }

        logger.info(
            f"Pattern bank metrics: {total_patterns} patterns, "
            f"avg_success={avg_success:.2%}"
        )

        return metrics
