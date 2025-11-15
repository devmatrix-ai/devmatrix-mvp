"""
Qdrant Vector Database Client

Wrapper for Qdrant vector database integration.
Connects to EXISTING infrastructure with 21,624 pattern embeddings.

Collections:
- devmatrix_patterns (21,624 patterns): Existing patterns from 9 repositories
- semantic_patterns (0 patterns): New collection for semantic task signatures

Vector Configuration:
- Dimension: 768 (Sentence Transformers)
- Distance: Cosine similarity
- Model: sentence-transformers/all-MiniLM-L6-v2
"""

from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from src.cognitive.config import settings

logger = logging.getLogger(__name__)


class QdrantPatternClient:
    """
    Qdrant client for semantic pattern search and storage.

    Provides methods to:
    - Search existing 21K+ patterns by semantic similarity
    - Store new semantic task signatures
    - Retrieve similar patterns for inference
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_patterns: Optional[str] = None,
        collection_semantic: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant host (default from settings)
            port: Qdrant port (default from settings)
            collection_patterns: Existing patterns collection name
            collection_semantic: Semantic signatures collection name
            embedding_model: Sentence Transformers model name
        """
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.collection_patterns = collection_patterns or settings.qdrant_collection_patterns
        self.collection_semantic = collection_semantic or settings.qdrant_collection_semantic
        self.embedding_model_name = embedding_model or settings.embedding_model

        self._client: Optional[QdrantClient] = None
        self._encoder: Optional[SentenceTransformer] = None

    def connect(self) -> None:
        """Establish connection to Qdrant and load embedding model."""
        try:
            self._client = QdrantClient(host=self.host, port=self.port)

            # Verify connectivity by listing collections
            collections = self._client.get_collections()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            logger.info(f"Available collections: {[c.name for c in collections.collections]}")

            # Load embedding model
            self._encoder = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def close(self) -> None:
        """Close Qdrant connection."""
        if self._client:
            self._client.close()
            logger.info("Qdrant connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _encode(self, text: str) -> List[float]:
        """
        Encode text to embedding vector.

        Args:
            text: Input text

        Returns:
            768-dimensional embedding vector
        """
        if not self._encoder:
            raise RuntimeError("Embedding model not loaded. Call connect() first.")

        embedding = self._encoder.encode(text)
        return embedding.tolist()

    def search_patterns(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search existing patterns by semantic similarity.

        Args:
            query: Search query text (purpose or code description)
            limit: Maximum number of results
            similarity_threshold: Minimum cosine similarity (default from settings)
            filters: Optional metadata filters (e.g., {"language": "python"})

        Returns:
            List of pattern matches with scores
        """
        if not self._client:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        threshold = similarity_threshold or settings.pattern_similarity_threshold
        query_vector = self._encode(query)

        # Build filters if provided
        query_filter = None
        if filters:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filters.items()
            ]
            query_filter = Filter(must=conditions)

        # Search in existing patterns collection
        results = self._client.search(
            collection_name=self.collection_patterns,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=threshold
        )

        # Format results
        matches = []
        for result in results:
            match = {
                "pattern_id": result.payload.get("pattern_id"),
                "name": result.payload.get("name"),
                "pattern_type": result.payload.get("pattern_type"),
                "language": result.payload.get("language"),
                "framework": result.payload.get("framework"),
                "code": result.payload.get("code"),
                "similarity_score": result.score
            }
            matches.append(match)

        logger.info(f"Found {len(matches)} patterns with similarity >= {threshold}")
        return matches

    def store_semantic_signature(
        self,
        signature_id: str,
        purpose: str,
        code: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store new semantic task signature in semantic_patterns collection.

        Args:
            signature_id: Unique signature identifier
            purpose: Task purpose/description
            code: Generated code
            metadata: Additional metadata (domain, complexity, etc.)

        Returns:
            Stored point ID
        """
        if not self._client:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        # Encode purpose + code for semantic similarity
        text_to_encode = f"{purpose}\n\n{code}"
        embedding = self._encode(text_to_encode)

        # Create point with metadata
        point = PointStruct(
            id=signature_id,
            vector=embedding,
            payload={
                "signature_id": signature_id,
                "purpose": purpose,
                "code": code,
                **metadata
            }
        )

        # Store in semantic_patterns collection
        self._client.upsert(
            collection_name=self.collection_semantic,
            points=[point]
        )

        logger.info(f"Stored semantic signature: {signature_id}")
        return signature_id

    def get_similar(
        self,
        purpose: str,
        limit: int = 5,
        collection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get similar patterns or signatures by purpose.

        Args:
            purpose: Task purpose description
            limit: Maximum number of results
            collection: Collection to search (default: patterns)

        Returns:
            List of similar items
        """
        collection_name = collection or self.collection_patterns
        return self.search_patterns(query=purpose, limit=limit)

    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get collection statistics.

        Args:
            collection_name: Collection to inspect (default: patterns)

        Returns:
            Collection metadata and statistics
        """
        if not self._client:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        coll_name = collection_name or self.collection_patterns
        info = self._client.get_collection(collection_name=coll_name)

        return {
            "name": coll_name,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": info.status
        }

    def healthcheck(self) -> bool:
        """
        Verify Qdrant connection and data availability.

        Returns:
            True if healthy, False otherwise
        """
        try:
            info = self.get_collection_info()
            logger.info(f"Qdrant healthcheck: {info['points_count']} patterns available")
            return info['points_count'] > 0
        except Exception as e:
            logger.error(f"Qdrant healthcheck failed: {e}")
            return False

    def ensure_semantic_collection_exists(self) -> None:
        """
        Ensure semantic_patterns collection exists with correct configuration.
        Creates collection if it doesn't exist.
        """
        if not self._client:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        try:
            # Check if collection exists
            self._client.get_collection(collection_name=self.collection_semantic)
            logger.info(f"Collection {self.collection_semantic} already exists")
        except Exception:
            # Create collection
            self._client.create_collection(
                collection_name=self.collection_semantic,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection {self.collection_semantic}")
