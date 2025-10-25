"""
High-level retrieval interface for RAG system.

This module provides advanced retrieval capabilities including:
- Multi-stage ranking and filtering
- MMR (Maximal Marginal Relevance) for diversity
- Re-ranking by multiple criteria
- Caching for performance optimization
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import time

from src.rag.vector_store import VectorStore
from src.config import RAG_TOP_K, RAG_SIMILARITY_THRESHOLD, RAG_CACHE_ENABLED
from src.observability import get_logger

# Import MGE V2 RAG caching
from src.mge.v2.caching import RAGQueryCache


class RetrievalStrategy(Enum):
    """Retrieval strategy enumeration."""
    SIMILARITY = "similarity"  # Pure similarity search
    MMR = "mmr"  # Maximal Marginal Relevance (diversity)
    HYBRID = "hybrid"  # Combination of similarity and other signals


@dataclass
class RetrievalResult:
    """
    Single retrieval result with metadata.

    Attributes:
        id: Example ID
        code: Code snippet
        metadata: Associated metadata
        similarity: Similarity score (0.0-1.0)
        rank: Position in results (1-based)
        relevance_score: Final relevance score after re-ranking
    """
    id: str
    code: str
    metadata: Dict[str, Any]
    similarity: float
    rank: int = 0
    relevance_score: float = 0.0
    mmr_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "code": self.code,
            "metadata": self.metadata,
            "similarity": self.similarity,
            "rank": self.rank,
            "relevance_score": self.relevance_score,
            "mmr_score": self.mmr_score,
        }


@dataclass
class RetrievalConfig:
    """
    Configuration for retrieval behavior.

    Attributes:
        top_k: Number of results to retrieve
        min_similarity: Minimum similarity threshold
        strategy: Retrieval strategy (similarity, mmr, hybrid)
        mmr_lambda: MMR diversity parameter (0=max diversity, 1=max similarity)
        filters: Metadata filters
        rerank: Whether to apply re-ranking
        cache_enabled: Whether to use caching
    """
    top_k: int = RAG_TOP_K
    min_similarity: float = RAG_SIMILARITY_THRESHOLD
    strategy: RetrievalStrategy = RetrievalStrategy.SIMILARITY
    mmr_lambda: float = 0.5  # Balance similarity vs diversity
    filters: Optional[Dict[str, Any]] = None
    rerank: bool = True
    cache_enabled: bool = RAG_CACHE_ENABLED


class Retriever:
    """
    High-level retrieval interface with advanced ranking.

    Provides retrieval with multiple strategies, filtering, and re-ranking
    to retrieve the most relevant and diverse code examples.

    Attributes:
        vector_store: Underlying vector store
        config: Retrieval configuration
        logger: Structured logger
        cache: Simple in-memory cache for queries
    """

    def __init__(
        self,
        vector_store: VectorStore,
        config: Optional[RetrievalConfig] = None,
        enable_v2_caching: bool = True,  # NEW: Enable MGE V2 RAG caching
        redis_url: str = "redis://localhost:6379"  # NEW: Redis URL for V2 caching
    ):
        """
        Initialize retriever.

        Args:
            vector_store: VectorStore instance
            config: Optional retrieval configuration
            enable_v2_caching: Enable MGE V2 RAG query caching (default: True)
            redis_url: Redis connection URL for V2 caching
        """
        self.logger = get_logger("rag.retriever")
        self.vector_store = vector_store
        self.config = config or RetrievalConfig()
        self.cache: Dict[str, List[RetrievalResult]] = {}  # Legacy in-memory cache

        # NEW: Initialize MGE V2 RAG query cache
        self.enable_v2_caching = enable_v2_caching
        if self.enable_v2_caching:
            self.rag_cache = RAGQueryCache(redis_url=redis_url)
            self.logger.info("MGE V2 RAG query caching enabled")
        else:
            self.rag_cache = None

        self.logger.info(
            "Retriever initialized",
            strategy=self.config.strategy.value,
            top_k=self.config.top_k,
            min_similarity=self.config.min_similarity,
            v2_caching=enable_v2_caching
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        strategy: Optional[RetrievalStrategy] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant code examples.

        Args:
            query: Query text (code or natural language)
            top_k: Number of results (overrides config)
            min_similarity: Minimum similarity (overrides config)
            filters: Metadata filters (overrides config)
            strategy: Retrieval strategy (overrides config)

        Returns:
            List of RetrievalResult objects, ranked by relevance

        Raises:
            ValueError: If parameters are invalid
        """
        # Override config with provided parameters
        effective_top_k = top_k or self.config.top_k
        effective_min_sim = min_similarity or self.config.min_similarity
        effective_filters = filters or self.config.filters
        effective_strategy = strategy or self.config.strategy

        # Check cache
        cache_key = self._get_cache_key(query, effective_top_k, effective_filters)
        if self.config.cache_enabled and cache_key in self.cache:
            self.logger.debug("Cache hit", query_length=len(query))
            return self.cache[cache_key]

        try:
            self.logger.debug(
                "Starting retrieval",
                query_length=len(query),
                top_k=effective_top_k,
                strategy=effective_strategy.value
            )

            # Execute retrieval based on strategy
            if effective_strategy == RetrievalStrategy.SIMILARITY:
                results = self._retrieve_similarity(
                    query, effective_top_k, effective_min_sim, effective_filters
                )
            elif effective_strategy == RetrievalStrategy.MMR:
                results = self._retrieve_mmr(
                    query, effective_top_k, effective_min_sim, effective_filters
                )
            elif effective_strategy == RetrievalStrategy.HYBRID:
                results = self._retrieve_hybrid(
                    query, effective_top_k, effective_min_sim, effective_filters
                )
            else:
                raise ValueError(f"Unknown strategy: {effective_strategy}")

            # Apply re-ranking if enabled
            if self.config.rerank and results:
                results = self._rerank_results(query, results)

            # Assign final ranks
            for i, result in enumerate(results, 1):
                result.rank = i

            # Cache results
            if self.config.cache_enabled:
                self.cache[cache_key] = results

            self.logger.info(
                "Retrieval completed",
                query_length=len(query),
                results_count=len(results),
                strategy=effective_strategy.value
            )

            return results

        except Exception as e:
            self.logger.error(
                "Retrieval failed",
                error=str(e),
                error_type=type(e).__name__,
                query_length=len(query)
            )
            raise

    async def _retrieve_similarity_async(
        self,
        query: str,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        Pure similarity-based retrieval with V2 caching support (async version).

        Args:
            query: Query text
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        # NEW: Check V2 RAG cache if enabled
        query_embedding = None
        if self.enable_v2_caching and self.rag_cache:
            # Get query embedding for cache lookup
            query_embedding = self.vector_store.embedding_model.embed_text(query)
            embedding_model_name = getattr(self.vector_store.embedding_model, 'model_name', 'sentence-transformers')

            # Check cache
            cached_result = await self.rag_cache.get(
                query=query,
                query_embedding=query_embedding,
                embedding_model=embedding_model_name,
                top_k=top_k
            )

            if cached_result:
                # Cache hit! Convert cached documents to RetrievalResult
                self.logger.info(
                    f"V2 RAG cache HIT: Returning cached results "
                    f"(age={(time.time() - cached_result.cached_at) / 60:.1f}min)"
                )

                results = []
                for doc in cached_result.documents:
                    result = RetrievalResult(
                        id=doc["id"],
                        code=doc["code"],
                        metadata=doc["metadata"],
                        similarity=doc["similarity"],
                        relevance_score=doc["similarity"]
                    )
                    results.append(result)

                return results

        # Cache miss - continue with normal retrieval
        self.logger.debug("V2 RAG cache MISS: Querying vector store")

        # Search vector store
        raw_results = self.vector_store.search_with_metadata(
            query=query,
            top_k=top_k,
            filters=filters,
            min_similarity=min_similarity
        )

        # Convert to RetrievalResult objects
        results = []
        for raw in raw_results:
            result = RetrievalResult(
                id=raw["id"],
                code=raw["code"],
                metadata=raw["metadata"],
                similarity=raw["similarity"],
                relevance_score=raw["similarity"],  # Initial score = similarity
            )
            results.append(result)

        # NEW: Save to V2 cache (fire and forget)
        if self.enable_v2_caching and self.rag_cache:
            if query_embedding is None:
                query_embedding = self.vector_store.embedding_model.embed_text(query)
            embedding_model_name = getattr(self.vector_store.embedding_model, 'model_name', 'sentence-transformers')

            # Convert results back to dict format for caching
            documents = [
                {
                    "id": r.id,
                    "code": r.code,
                    "metadata": r.metadata,
                    "similarity": r.similarity
                }
                for r in results
            ]

            # Save to cache (async, don't await)
            import asyncio
            import time
            asyncio.create_task(
                self.rag_cache.set(
                    query=query,
                    query_embedding=query_embedding,
                    embedding_model=embedding_model_name,
                    top_k=top_k,
                    documents=documents
                )
            )
            self.logger.debug("V2 RAG cache: Saved query results")

        return results

    def _retrieve_similarity(
        self,
        query: str,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        Pure similarity-based retrieval (sync wrapper for backward compatibility).

        Args:
            query: Query text
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        import asyncio
        # Run async version in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._retrieve_similarity_async(query, top_k, min_similarity, filters)
        )

    def _retrieve_mmr(
        self,
        query: str,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        MMR-based retrieval for diversity.

        MMR (Maximal Marginal Relevance) balances similarity to query
        with diversity among results to avoid redundant examples.

        Args:
            query: Query text
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects with diverse examples
        """
        # Get more candidates than needed for MMR selection
        candidate_k = min(top_k * 3, 50)

        # Search vector store
        candidates = self.vector_store.search_with_metadata(
            query=query,
            top_k=candidate_k,
            filters=filters,
            min_similarity=min_similarity
        )

        if not candidates:
            return []

        # Get embeddings for MMR calculation
        query_embedding = self.vector_store.embedding_model.embed_text(query)

        # Extract candidate embeddings (we need to re-embed codes)
        candidate_codes = [c["code"] for c in candidates]
        candidate_embeddings = self.vector_store.embedding_model.embed_batch(
            candidate_codes,
            show_progress=False
        )

        # Apply MMR algorithm
        selected_indices = self._mmr_selection(
            query_embedding=query_embedding,
            candidate_embeddings=candidate_embeddings,
            top_k=top_k,
            lambda_param=self.config.mmr_lambda
        )

        # Build results from selected indices
        results = []
        for idx in selected_indices:
            candidate = candidates[idx]
            result = RetrievalResult(
                id=candidate["id"],
                code=candidate["code"],
                metadata=candidate["metadata"],
                similarity=candidate["similarity"],
                relevance_score=candidate["similarity"],  # Will be adjusted by MMR
            )
            results.append(result)

        return results

    def _retrieve_hybrid(
        self,
        query: str,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining multiple signals.

        Combines similarity search with metadata-based boosting
        and other relevance signals.

        Args:
            query: Query text
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        # Start with similarity search
        results = self._retrieve_similarity(query, top_k * 2, min_similarity, filters)

        if not results:
            return []

        # Apply hybrid scoring
        for result in results:
            # Base score from similarity
            score = result.similarity

            # Boost approved examples
            if result.metadata.get("approved"):
                score *= 1.2

            # Boost recently indexed examples
            if "indexed_at" in result.metadata:
                # Could add recency boost here
                pass

            # Boost examples with high usage count
            if "usage_count" in result.metadata:
                usage_count = result.metadata["usage_count"]
                score *= (1.0 + min(usage_count / 100, 0.3))

            result.relevance_score = min(score, 1.0)

        # Re-sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Return top_k
        return results[:top_k]

    def _mmr_selection(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int,
        lambda_param: float,
    ) -> List[int]:
        """
        MMR (Maximal Marginal Relevance) selection algorithm.

        MMR = λ * Sim(q, d) - (1-λ) * max(Sim(d, d_i))
        where d_i are already selected documents.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: Candidate embedding vectors
            top_k: Number of items to select
            lambda_param: Balance parameter (0=diversity, 1=similarity)

        Returns:
            List of selected candidate indices
        """
        query_emb = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)

        # Calculate similarities to query
        query_sims = self._cosine_similarity_batch(query_emb, candidates)

        # Initialize
        selected_indices = []
        remaining_indices = list(range(len(candidates)))

        for _ in range(min(top_k, len(candidates))):
            if not remaining_indices:
                break

            mmr_scores = []
            for idx in remaining_indices:
                # Similarity to query
                query_sim = query_sims[idx]

                # Max similarity to already selected
                if selected_indices:
                    selected_embs = candidates[selected_indices]
                    selected_sims = self._cosine_similarity_batch(
                        candidates[idx], selected_embs
                    )
                    max_selected_sim = np.max(selected_sims)
                else:
                    max_selected_sim = 0.0

                # MMR score
                mmr_score = lambda_param * query_sim - (1 - lambda_param) * max_selected_sim
                mmr_scores.append((idx, mmr_score))

            # Select best MMR score
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        return selected_indices

    def _cosine_similarity_batch(
        self,
        vec: np.ndarray,
        matrix: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between a vector and a matrix of vectors.

        Args:
            vec: Single vector (1D array)
            matrix: Matrix of vectors (2D array)

        Returns:
            Array of cosine similarities
        """
        # Normalize
        vec_norm = vec / (np.linalg.norm(vec) + 1e-10)

        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)

        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix_norm = matrix / (matrix_norms + 1e-10)

        # Compute dot products
        similarities = np.dot(matrix_norm, vec_norm)

        return similarities

    def _rerank_results(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Re-rank results using multiple signals.

        Args:
            query: Original query
            results: Initial retrieval results

        Returns:
            Re-ranked results
        """
        if not results:
            return results

        self.logger.debug("Re-ranking results", count=len(results))

        # Apply re-ranking heuristics
        for result in results:
            score = result.relevance_score

            # Boost if code length is appropriate (not too short, not too long)
            code_length = len(result.code)
            if 50 <= code_length <= 500:
                score *= 1.1
            elif code_length < 20:
                score *= 0.8

            # Boost if metadata indicates quality
            if result.metadata.get("approved"):
                score *= 1.15
            if result.metadata.get("reviewed"):
                score *= 1.05

            result.relevance_score = min(score, 1.0)

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results

    def _get_cache_key(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate cache key for query.

        Args:
            query: Query text
            top_k: Number of results
            filters: Metadata filters

        Returns:
            Cache key string
        """
        filters_str = str(sorted(filters.items())) if filters else "none"
        return f"{query}:{top_k}:{filters_str}"

    def clear_cache(self) -> int:
        """
        Clear the query cache.

        Returns:
            Number of cached queries cleared
        """
        count = len(self.cache)
        self.cache.clear()
        self.logger.info("Cache cleared", entries_cleared=count)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get retriever statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "strategy": self.config.strategy.value,
            "top_k": self.config.top_k,
            "min_similarity": self.config.min_similarity,
            "mmr_lambda": self.config.mmr_lambda,
            "cache_enabled": self.config.cache_enabled,
            "cache_size": len(self.cache),
            "rerank_enabled": self.config.rerank,
        }


def create_retriever(
    vector_store: VectorStore,
    strategy: RetrievalStrategy = RetrievalStrategy.SIMILARITY,
    top_k: int = RAG_TOP_K,
    min_similarity: float = RAG_SIMILARITY_THRESHOLD,
) -> Retriever:
    """
    Factory function to create a retriever instance.

    Args:
        vector_store: VectorStore instance
        strategy: Retrieval strategy
        top_k: Number of results
        min_similarity: Minimum similarity threshold

    Returns:
        Initialized Retriever instance
    """
    config = RetrievalConfig(
        top_k=top_k,
        min_similarity=min_similarity,
        strategy=strategy,
    )

    return Retriever(
        vector_store=vector_store,
        config=config,
    )
