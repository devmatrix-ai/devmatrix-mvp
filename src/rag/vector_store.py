"""
ChromaDB vector store for RAG system.

This module provides a wrapper around ChromaDB for storing and retrieving
code embeddings. It handles collection management, indexing, and similarity search.

Updated for Phase 1 Critical Security Vulnerabilities - Group 5: API Security Layer
Added input validation and sanitization for SQL injection prevention.
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
import re
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.api.types import QueryResult
from pydantic import BaseModel, Field, field_validator

from src.rag.embeddings import EmbeddingModel
from src.config import (
    CHROMADB_HOST,
    CHROMADB_PORT,
    CHROMADB_COLLECTION_NAME,
    CHROMADB_DISTANCE_METRIC,
)
from src.observability import get_logger


# ========================================
# Input Validation Schemas
# Group 5.6: SQL Injection Prevention
# ========================================

class SearchRequest(BaseModel):
    """
    Validated search request schema.

    Prevents SQL injection by validating and sanitizing inputs.
    """
    query: str = Field(..., min_length=1, max_length=500, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results (1-100)")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata filters")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """
        Validate and sanitize query string.

        Checks for SQL injection patterns and sanitizes input.

        Args:
            v: Query string

        Returns:
            Sanitized query string

        Raises:
            ValueError: If query contains SQL special characters
        """
        # Check for SQL special characters
        sql_special_chars = ["'", '"', "--", ";", "/*", "*/", "UNION", "DROP", "DELETE", "INSERT", "UPDATE"]

        for char in sql_special_chars:
            if char in v.upper():
                raise ValueError(f"Query contains prohibited character or keyword: {char}")

        # Remove any remaining dangerous characters
        sanitized = re.sub(r'[;\'"\\]', '', v)

        return sanitized

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Validate filter dictionary.

        Only allows whitelisted filter keys.

        Args:
            v: Filter dictionary

        Returns:
            Validated filters

        Raises:
            ValueError: If filter contains non-whitelisted keys
        """
        if v is None:
            return None

        # Whitelist of allowed filter keys
        allowed_keys = {
            "language", "file_path", "approved", "tags",
            "indexed_at", "code_length", "author", "task_type",
            # Provenance and routing keys for better retrieval control
            "source", "framework", "collection", "source_collection"
        }

        for key in v.keys():
            if key not in allowed_keys:
                raise ValueError(f"Filter key '{key}' is not allowed")

        return v


class VectorStore:
    """
    ChromaDB wrapper for storing and retrieving code embeddings.

    Provides methods for indexing code examples and performing similarity search
    to retrieve relevant examples for RAG-enhanced code generation.

    Attributes:
        embedding_model: Model for generating embeddings
        client: ChromaDB client instance
        collection: ChromaDB collection for storing embeddings
        logger: Structured logger instance
    """

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        host: str = CHROMADB_HOST,
        port: int = CHROMADB_PORT,
        collection_name: str = CHROMADB_COLLECTION_NAME,
        distance_metric: str = CHROMADB_DISTANCE_METRIC,
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            embedding_model: Embedding model instance
            host: ChromaDB host (default: from config)
            port: ChromaDB port (default: from config)
            collection_name: Name of the collection (default: from config)
            distance_metric: Distance metric (cosine, l2, ip) (default: from config)

        Raises:
            Exception: If connection to ChromaDB fails
        """
        self.logger = get_logger("rag.vector_store")
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.distance_metric = distance_metric

        try:
            self.logger.info(
                "Connecting to ChromaDB",
                host=host,
                port=port,
                collection=collection_name
            )

            # Initialize ChromaDB client
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                )
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": distance_metric}
            )

            self.logger.info(
                "ChromaDB connection established",
                collection=collection_name,
                count=self.collection.count()
            )

        except Exception as e:
            self.logger.error(
                "Failed to connect to ChromaDB",
                error=str(e),
                error_type=type(e).__name__,
                host=host,
                port=port
            )
            raise

    def add_example(
        self,
        code: str,
        metadata: Optional[Dict[str, Any]] = None,
        example_id: Optional[str] = None,
    ) -> str:
        """
        Add a single code example to the vector store.

        Args:
            code: Code snippet to index
            metadata: Optional metadata (file_path, language, tags, etc.)
            example_id: Optional custom ID (auto-generated if not provided)

        Returns:
            ID of the added example

        Raises:
            ValueError: If code is empty
            Exception: If indexing fails
        """
        if not code or not code.strip():
            raise ValueError("Cannot add empty code example")

        try:
            # Generate ID if not provided
            if example_id is None:
                example_id = str(uuid.uuid4())

            self.logger.debug(
                "Adding code example to vector store",
                example_id=example_id,
                code_length=len(code),
                has_metadata=metadata is not None
            )

            # Generate embedding
            embedding = self.embedding_model.embed_text(code)

            # Prepare metadata
            example_metadata = metadata or {}
            example_metadata["indexed_at"] = datetime.utcnow().isoformat()
            example_metadata["code_length"] = len(code)

            # Add to collection
            self.collection.add(
                ids=[example_id],
                embeddings=[embedding],
                documents=[code],
                metadatas=[example_metadata]
            )

            self.logger.info(
                "Code example added successfully",
                example_id=example_id,
                collection=self.collection_name,
                total_count=self.collection.count()
            )

            return example_id

        except Exception as e:
            self.logger.error(
                "Failed to add code example",
                error=str(e),
                error_type=type(e).__name__,
                code_length=len(code) if code else 0
            )
            raise

    def add_batch(
        self,
        codes: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        example_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add multiple code examples efficiently.

        Args:
            codes: List of code snippets to index
            metadatas: Optional list of metadata dicts (one per code)
            example_ids: Optional list of custom IDs (auto-generated if not provided)

        Returns:
            List of IDs for the added examples

        Raises:
            ValueError: If codes list is empty or lengths don't match
            Exception: If batch indexing fails
        """
        if not codes:
            raise ValueError("Cannot add empty batch of code examples")

        # Validate inputs
        if metadatas and len(metadatas) != len(codes):
            raise ValueError(
                f"Metadatas length ({len(metadatas)}) must match codes length ({len(codes)})"
            )

        if example_ids and len(example_ids) != len(codes):
            raise ValueError(
                f"IDs length ({len(example_ids)}) must match codes length ({len(codes)})"
            )

        try:
            self.logger.info(
                "Adding batch of code examples",
                batch_size=len(codes),
                has_metadatas=metadatas is not None,
                has_ids=example_ids is not None
            )

            # Generate IDs if not provided
            if example_ids is None:
                example_ids = [str(uuid.uuid4()) for _ in codes]

            # Generate embeddings
            embeddings = self.embedding_model.embed_batch(codes, show_progress=False)

            # Prepare metadatas
            if metadatas is None:
                metadatas = [{} for _ in codes]

            # Add timestamp and code length to each metadata
            indexed_at = datetime.utcnow().isoformat()
            for i, metadata in enumerate(metadatas):
                metadata["indexed_at"] = indexed_at
                metadata["code_length"] = len(codes[i])

            # Add batch to collection
            self.collection.add(
                ids=example_ids,
                embeddings=embeddings,
                documents=codes,
                metadatas=metadatas
            )

            self.logger.info(
                "Batch added successfully",
                batch_size=len(codes),
                collection=self.collection_name,
                total_count=self.collection.count()
            )

            return example_ids

        except Exception as e:
            self.logger.error(
                "Failed to add batch",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(codes)
            )
            raise

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code examples.

        SECURITY: Input validation added to prevent SQL injection.

        Args:
            query: Query text (code snippet or natural language)
            top_k: Number of results to return (default: 5)
            where: Optional metadata filter (e.g., {"language": "python"})
            where_document: Optional document content filter

        Returns:
            List of results with code, metadata, and similarity scores

        Raises:
            ValueError: If query is empty or top_k is invalid
            Exception: If search fails
        """
        # Validate inputs using Pydantic schema
        try:
            search_request = SearchRequest(
                query=query,
                top_k=top_k,
                filters=where
            )
        except ValueError as e:
            self.logger.warning(f"Search validation failed: {str(e)}")
            raise ValueError(f"Invalid search parameters: {str(e)}")

        # Use validated values
        query = search_request.query
        top_k = search_request.top_k
        where = search_request.filters

        try:
            self.logger.debug(
                "Searching vector store",
                query_length=len(query),
                top_k=top_k,
                has_where=where is not None,
                has_where_document=where_document is not None
            )

            # Generate query embedding
            query_embedding = self.embedding_model.embed_text(query)

            # Translate simple equality filters into Chroma's where syntax
            where_chroma = None
            if where:
                clauses = []
                for k, v in where.items():
                    clauses.append({k: {"$eq": v}})
                where_chroma = {"$and": clauses} if len(clauses) > 1 else clauses[0]

            # Perform search using parameterized ChromaDB query
            # ChromaDB uses safe parameterization internally
            results: QueryResult = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_chroma,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = self._format_query_results(results)

            self.logger.info(
                "Search completed",
                query_length=len(query),
                results_count=len(formatted_results),
                top_k=top_k
            )

            return formatted_results

        except Exception as e:
            self.logger.error(
                "Search failed",
                error=str(e),
                error_type=type(e).__name__,
                query_length=len(query) if query else 0
            )
            raise

    def search_with_metadata(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search with metadata filtering and similarity threshold.

        Args:
            query: Query text
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"language": "python", "approved": True})
            min_similarity: Minimum similarity score (0.0-1.0)

        Returns:
            List of results filtered by similarity threshold

        Raises:
            ValueError: If parameters are invalid
            Exception: If search fails
        """
        # Perform search (validation happens in search method)
        results = self.search(query=query, top_k=top_k, where=filters)

        # Apply similarity threshold if specified
        if min_similarity is not None:
            if min_similarity < 0.0 or min_similarity > 1.0:
                raise ValueError(f"min_similarity must be 0.0-1.0, got {min_similarity}")

            results = [r for r in results if r["similarity"] >= min_similarity]

            self.logger.debug(
                "Applied similarity threshold",
                min_similarity=min_similarity,
                results_before=len(results) if not min_similarity else top_k,
                results_after=len(results)
            )

        return results

    def delete_example(self, example_id: str) -> bool:
        """
        Delete a code example from the vector store.

        Args:
            example_id: ID of the example to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            Exception: If deletion fails
        """
        try:
            self.logger.debug("Deleting example", example_id=example_id)

            # Check if exists
            result = self.collection.get(ids=[example_id])
            if not result["ids"]:
                self.logger.warning(
                    "Example not found for deletion",
                    example_id=example_id
                )
                return False

            # Delete
            self.collection.delete(ids=[example_id])

            self.logger.info(
                "Example deleted successfully",
                example_id=example_id,
                total_count=self.collection.count()
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to delete example",
                error=str(e),
                error_type=type(e).__name__,
                example_id=example_id
            )
            raise

    def delete_batch(self, example_ids: List[str]) -> int:
        """
        Delete multiple examples.

        Args:
            example_ids: List of IDs to delete

        Returns:
            Number of examples deleted

        Raises:
            Exception: If deletion fails
        """
        if not example_ids:
            return 0

        try:
            self.logger.info("Deleting batch", batch_size=len(example_ids))

            # Check which exist
            existing = self.collection.get(ids=example_ids)
            existing_ids = existing["ids"]

            if not existing_ids:
                self.logger.warning("No examples found for deletion")
                return 0

            # Delete
            self.collection.delete(ids=existing_ids)

            self.logger.info(
                "Batch deleted successfully",
                requested=len(example_ids),
                deleted=len(existing_ids),
                total_count=self.collection.count()
            )

            return len(existing_ids)

        except Exception as e:
            self.logger.error(
                "Failed to delete batch",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(example_ids)
            )
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()

            return {
                "collection_name": self.collection_name,
                "total_examples": count,
                "distance_metric": self.distance_metric,
                "embedding_dimension": self.embedding_model.get_dimension(),
                "embedding_model": self.embedding_model.model_name,
            }

        except Exception as e:
            self.logger.error(
                "Failed to get stats",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": str(e),
                "collection_name": self.collection_name,
            }

    def health_check(self) -> Tuple[bool, str]:
        """
        Check if vector store is healthy.

        Returns:
            Tuple of (is_healthy, status_message)
        """
        try:
            # Try to query the collection
            self.collection.count()
            return True, "Vector store is healthy"

        except Exception as e:
            self.logger.error(
                "Health check failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return False, f"Vector store is unhealthy: {str(e)}"

    def clear_collection(self) -> int:
        """
        Clear all examples from the collection.

        WARNING: This operation cannot be undone!

        Returns:
            Number of examples deleted
        """
        try:
            count_before = self.collection.count()

            self.logger.warning(
                "Clearing collection",
                collection=self.collection_name,
                count=count_before
            )

            # Delete collection and recreate
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric}
            )

            self.logger.warning(
                "Collection cleared",
                deleted_count=count_before
            )

            return count_before

        except Exception as e:
            self.logger.error(
                "Failed to clear collection",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _format_query_results(self, results: QueryResult) -> List[Dict[str, Any]]:
        """
        Format ChromaDB query results into a cleaner structure.

        Args:
            results: Raw ChromaDB query results

        Returns:
            List of formatted result dictionaries
        """
        formatted = []

        # ChromaDB returns results as nested lists
        ids = results["ids"][0] if results["ids"] else []
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        for i in range(len(ids)):
            # Convert distance to similarity (cosine distance -> cosine similarity)
            # For cosine distance: similarity = 1 - distance
            distance = distances[i] if i < len(distances) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance))

            formatted.append({
                "id": ids[i],
                "code": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distance,
                "similarity": similarity,
            })

        return formatted


def create_vector_store(
    embedding_model: EmbeddingModel,
    host: str = CHROMADB_HOST,
    port: int = CHROMADB_PORT,
) -> VectorStore:
    """
    Factory function to create a vector store instance.

    Args:
        embedding_model: Embedding model instance
        host: ChromaDB host
        port: ChromaDB port

    Returns:
        Initialized VectorStore instance
    """
    return VectorStore(
        embedding_model=embedding_model,
        host=host,
        port=port,
    )
