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
from src.rag.multi_collection_manager import MultiCollectionManager
from src.config import RAG_TOP_K, RAG_SIMILARITY_THRESHOLD, RAG_CACHE_ENABLED
from src.config import (
    RAG_SIMILARITY_THRESHOLD_CURATED,
    RAG_SIMILARITY_THRESHOLD_PROJECT,
    RAG_SIMILARITY_THRESHOLD_STANDARDS,
)
from src.observability import get_logger
from src.rag.reranker import Reranker
from src.rag.query_expander import QueryExpander
from src.rag.cross_encoder_reranker import CrossEncoderReranker

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
                   FIX #3: Adjusted from 0.5 to 0.35 for better diversity
                   Higher diversity prevents same examples from being returned
                   across different queries
        filters: Metadata filters
        rerank: Whether to apply re-ranking
        cache_enabled: Whether to use caching
    """
    top_k: int = RAG_TOP_K
    min_similarity: float = RAG_SIMILARITY_THRESHOLD
    strategy: RetrievalStrategy = RetrievalStrategy.SIMILARITY
    mmr_lambda: float = 0.35  # FIX #3: Increased diversity bias (65% diversity, 35% similarity)
    filters: Optional[Dict[str, Any]] = None
    rerank: bool = True
    cache_enabled: bool = RAG_CACHE_ENABLED


@dataclass
class RetrievalContext:
    """
    Request-scoped context for retrieval to avoid redundant computations.

    This context is created once per retrieve() call and passed to all
    sub-methods to avoid re-computing query embeddings multiple times.

    Attributes:
        query: Original query text
        query_embedding: Pre-computed query embedding (cached per request)
        embedding_model_name: Name of embedding model used
    """
    query: str
    query_embedding: Optional[List[float]] = None
    embedding_model_name: Optional[str] = None

    def ensure_embedding(self, embedding_fn: Callable[[str], List[float]]) -> List[float]:
        """
        Lazily compute and cache query embedding.

        Args:
            embedding_fn: Function to compute embedding if not cached

        Returns:
            Query embedding vector
        """
        if self.query_embedding is None:
            self.query_embedding = embedding_fn(self.query)
        return self.query_embedding


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
        vector_store: Optional[VectorStore] = None,
        config: Optional[RetrievalConfig] = None,
        enable_v2_caching: bool = True,
        redis_url: str = "redis://localhost:6379",
        multi_collection_manager: Optional[Any] = None,
        enable_query_expansion: bool = True,
        enable_cross_encoder_reranking: bool = True,
    ):
        """
        Initialize retriever.

        Args:
            vector_store: VectorStore instance
            config: Optional retrieval configuration
            enable_v2_caching: Enable MGE V2 RAG query caching (default: True)
            redis_url: Redis connection URL for V2 caching (default: redis://localhost:6379 for Docker)
            enable_query_expansion: Enable query expansion for better coverage (default: True)
            enable_cross_encoder_reranking: Enable cross-encoder semantic re-ranking (default: True)
        """
        self.logger = get_logger("rag.retriever")
        self.vector_store = vector_store
        self.multi_collection_manager = multi_collection_manager
        self.use_multi_collection = multi_collection_manager is not None
        self.config = config or RetrievalConfig()
        self.cache: Dict[str, List[RetrievalResult]] = {}  # Legacy in-memory cache
        self._reranker = Reranker()
        self._query_expander = QueryExpander() if enable_query_expansion else None
        self.enable_query_expansion = enable_query_expansion
        self._cross_encoder = CrossEncoderReranker() if enable_cross_encoder_reranking else None
        self.enable_cross_encoder_reranking = enable_cross_encoder_reranking

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
            v2_caching=enable_v2_caching,
            query_expansion=enable_query_expansion,
            cross_encoder_reranking=enable_cross_encoder_reranking
        )

    async def _check_v2_cache_async(
        self,
        context: RetrievalContext,
        top_k: int,
    ) -> Optional[List[RetrievalResult]]:
        """
        Check V2 RAG cache for query results.

        This is a shared helper used by all retrieval strategies to avoid
        redundant caching logic across _retrieve_similarity_async, _retrieve_mmr, etc.

        Args:
            context: RetrievalContext with query and optionally pre-computed embedding
            top_k: Number of results

        Returns:
            Cached results if hit, None if miss

        NEW: V2 cache is now checked by all strategies, not just similarity
        """
        if not self.enable_v2_caching or not self.rag_cache:
            return None

        try:
            # Ensure embedding is available
            query_embedding = context.ensure_embedding(
                self.vector_store.embedding_model.embed_text
            )

            if context.embedding_model_name is None:
                context.embedding_model_name = getattr(
                    self.vector_store.embedding_model, 'model_name', 'sentence-transformers'
                )

            # Check cache
            cached_result = await self.rag_cache.get(
                query=context.query,
                query_embedding=query_embedding,
                embedding_model=context.embedding_model_name,
                top_k=top_k
            )

            if cached_result:
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

            return None

        except Exception as e:
            self.logger.warning(
                "V2 cache check failed, continuing without cache",
                error=str(e)
            )
            return None

    async def _save_v2_cache_async(
        self,
        context: RetrievalContext,
        results: List[RetrievalResult],
        top_k: int,
    ) -> None:
        """
        Save results to V2 RAG cache with proper error handling.

        FIX #3: Now uses await instead of fire-and-forget create_task()
        to ensure cache is persisted before method returns.

        Args:
            context: RetrievalContext with query and embedding
            results: Retrieved results to cache
            top_k: Number of results

        NEW: Properly awaited with timeout instead of fire-and-forget
        """
        if not self.enable_v2_caching or not self.rag_cache:
            return

        try:
            # Ensure embedding is available
            query_embedding = context.ensure_embedding(
                self.vector_store.embedding_model.embed_text
            )

            if context.embedding_model_name is None:
                context.embedding_model_name = getattr(
                    self.vector_store.embedding_model, 'model_name', 'sentence-transformers'
                )

            # Convert results to dict format for caching
            documents = [
                {
                    "id": r.id,
                    "code": r.code,
                    "metadata": r.metadata,
                    "similarity": r.similarity
                }
                for r in results
            ]

            # Save with timeout to prevent blocking
            import asyncio
            await asyncio.wait_for(
                self.rag_cache.set(
                    query=context.query,
                    query_embedding=query_embedding,
                    embedding_model=context.embedding_model_name,
                    top_k=top_k,
                    documents=documents
                ),
                timeout=2.0
            )

            self.logger.debug("V2 RAG cache: Saved query results")

        except asyncio.TimeoutError:
            self.logger.warning(
                "V2 cache save timed out, continuing without caching"
            )
        except Exception as e:
            self.logger.warning(
                "V2 cache save failed, continuing",
                error=str(e)
            )

    def retrieve_with_expansion(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        strategy: Optional[RetrievalStrategy] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve with query expansion for better coverage.

        Expands query into variants and retrieves results for each,
        then deduplicates and combines results intelligently.

        Args:
            query: Query text (code or natural language)
            top_k: Number of results (overrides config)
            min_similarity: Minimum similarity (overrides config)
            filters: Metadata filters (overrides config)
            strategy: Retrieval strategy (overrides config)

        Returns:
            List of RetrievalResult objects, ranked by relevance
        """
        if not self.enable_query_expansion or not self._query_expander:
            # Fallback to regular retrieval if expansion disabled
            return self.retrieve(query, top_k, min_similarity, filters, strategy)

        effective_top_k = top_k or self.config.top_k

        try:
            # Expand query into variants
            query_variants = self._query_expander.expand_query(
                query,
                max_variants=5  # Use up to 5 variants
            )

            self.logger.info(
                "Query expansion",
                original_query=query,
                variant_count=len(query_variants)
            )

            # Retrieve results for each variant
            results_by_query: Dict[str, List[RetrievalResult]] = {}
            all_results: List[RetrievalResult] = []

            for variant in query_variants:
                try:
                    variant_results = self.retrieve(
                        query=variant,
                        top_k=effective_top_k * 2,  # Get more to handle deduplication
                        min_similarity=min_similarity,
                        filters=filters,
                        strategy=strategy
                    )
                    results_by_query[variant] = variant_results
                    all_results.extend(variant_results)

                    self.logger.debug(
                        f"Variant retrieval: '{variant}' → {len(variant_results)} results"
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to retrieve for variant '{variant}'",
                        error=str(e)
                    )
                    continue

            if not all_results:
                self.logger.info("No results found for any query variant")
                return []

            # Deduplicate by ID and combine
            seen_ids: Dict[str, RetrievalResult] = {}
            for result in all_results:
                if result.id not in seen_ids:
                    seen_ids[result.id] = result
                else:
                    # Keep result with higher similarity
                    if result.similarity > seen_ids[result.id].similarity:
                        seen_ids[result.id] = result

            # Convert to list and sort by similarity
            combined_results = list(seen_ids.values())
            combined_results.sort(key=lambda x: x.similarity, reverse=True)

            # Return top_k results
            final_results = combined_results[:effective_top_k]

            # Assign final ranks
            for i, result in enumerate(final_results, 1):
                result.rank = i

            self.logger.info(
                "Expanded retrieval completed",
                original_query=query,
                variant_count=len(query_variants),
                combined_results=len(seen_ids),
                final_results=len(final_results),
                top_k=effective_top_k
            )

            return final_results

        except Exception as e:
            self.logger.error(
                "Expanded retrieval failed",
                error=str(e),
                error_type=type(e).__name__,
                query_length=len(query)
            )
            # Fallback to regular retrieval
            return self.retrieve(query, top_k, min_similarity, filters, strategy)

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

            # FIX #2: Create request-scoped context for embedding deduplication
            context = RetrievalContext(query=query)

            # Prefer multi-collection retrieval when available
            if self.use_multi_collection:
                results = self._retrieve_multi_collection(
                    query=query,
                    top_k=effective_top_k,
                    min_similarity=effective_min_sim,
                    filters=effective_filters,
                    strategy=effective_strategy,
                )
            else:
                # Execute retrieval based on strategy
                if effective_strategy == RetrievalStrategy.SIMILARITY:
                    results = self._retrieve_similarity(
                        context, effective_top_k, effective_min_sim, effective_filters
                    )
                elif effective_strategy == RetrievalStrategy.MMR:
                    results = self._retrieve_mmr(
                        context, effective_top_k, effective_min_sim, effective_filters
                    )
                elif effective_strategy == RetrievalStrategy.HYBRID:
                    results = self._retrieve_hybrid(
                        context, effective_top_k, effective_min_sim, effective_filters
                    )
                else:
                    raise ValueError(f"Unknown strategy: {effective_strategy}")

            # Apply re-ranking if enabled
            if self.config.rerank and results:
                results = self._reranker.rerank(query, results)

            # Apply cross-encoder re-ranking if enabled (more semantic understanding)
            if self.enable_cross_encoder_reranking and self._cross_encoder and results:
                try:
                    results = self._cross_encoder.rerank(query, results)
                except Exception as e:
                    self.logger.warning(
                        "Cross-encoder re-ranking failed, continuing with heuristic ranking",
                        error=str(e)
                    )

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
        context: RetrievalContext,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        Pure similarity-based retrieval with V2 caching support (async version).

        FIX #1 & #2: Now uses RetrievalContext for embedding deduplication
        and shared V2 cache helpers for all strategies.

        Args:
            context: RetrievalContext with query and optional pre-computed embedding
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        # FIX #1: Check V2 cache using shared helper
        cached_results = await self._check_v2_cache_async(context, top_k)
        if cached_results is not None:
            self.logger.debug("V2 RAG cache MISS: Querying vector store")
            return cached_results

        # Cache miss - continue with normal retrieval
        self.logger.debug("V2 RAG cache MISS: Querying vector store")

        # Search vector store
        raw_results = self.vector_store.search_with_metadata(
            query=context.query,
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

        # FIX #3: Save to V2 cache using await with timeout
        await self._save_v2_cache_async(context, results, top_k)

        return results

    def _retrieve_multi_collection(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        strategy: Optional[RetrievalStrategy] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve from multi-collection manager with fallback strategy.
        """
        effective_top_k = top_k or self.config.top_k
        
        try:
            self.logger.debug(
                "Multi-collection retrieval",
                query_length=len(query),
                top_k=effective_top_k
            )
            
            # Use MultiCollectionManager for retrieval
            raw_results = self.multi_collection_manager.search_with_fallback(
                query=query,
                top_k=effective_top_k,
                include_low_quality=False
            )
            
            # Convert SearchResult to RetrievalResult
            results = []
            for i, sr in enumerate(raw_results, 1):
                result = RetrievalResult(
                    id=sr.id or f"multi_collection_{i}",
                    code=sr.content,
                    metadata={
                        **sr.metadata,
                        "collection": sr.collection,
                        "source_collection": sr.collection
                    },
                    similarity=sr.similarity,
                    rank=i,
                    relevance_score=sr.similarity
                )
                results.append(result)
            
            self.logger.info(
                "Multi-collection retrieval completed",
                query_length=len(query),
                results_count=len(results)
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Multi-collection retrieval failed",
                error=str(e),
                query_length=len(query)
            )
            raise
    
    def _retrieve_single_collection(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        strategy: Optional[RetrievalStrategy] = None,
    ) -> List[RetrievalResult]:
        """Original single-collection retrieval logic (backward compatible)."""
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
                results = self._reranker.rerank(query, results)

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

    def _retrieve_similarity(
        self,
        context: RetrievalContext,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        Pure similarity-based retrieval (sync wrapper for backward compatibility).

        FIX #2: Now accepts RetrievalContext for embedding deduplication.

        Args:
            context: RetrievalContext with query and optional pre-computed embedding
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
            self._retrieve_similarity_async(context, top_k, min_similarity, filters)
        )

    def _retrieve_mmr(
        self,
        context: RetrievalContext,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        MMR-based retrieval for diversity.

        MMR (Maximal Marginal Relevance) balances similarity to query
        with diversity among results to avoid redundant examples.

        FIX #1: Now uses shared V2 cache helpers for consistency
        FIX #2: Uses RetrievalContext for embedding deduplication

        Args:
            context: RetrievalContext with query and optional pre-computed embedding
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects with diverse examples
        """
        # FIX #1: Check V2 cache first (now implemented for MMR!)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        cached_results = loop.run_until_complete(
            self._check_v2_cache_async(context, top_k)
        )
        if cached_results is not None:
            return cached_results

        # Cache miss - continue with MMR retrieval
        # Get more candidates than needed for MMR selection
        candidate_k = min(top_k * 3, 50)

        # Search vector store
        candidates = self.vector_store.search_with_metadata(
            query=context.query,
            top_k=candidate_k,
            filters=filters,
            min_similarity=min_similarity
        )

        if not candidates:
            return []

        # FIX #2: Use context to ensure embedding is computed only once
        query_embedding = context.ensure_embedding(
            self.vector_store.embedding_model.embed_text
        )

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

        # FIX #1: Save to V2 cache using async helper
        loop.run_until_complete(
            self._save_v2_cache_async(context, results, top_k)
        )

        return results

    def _retrieve_hybrid(
        self,
        context: RetrievalContext,
        top_k: int,
        min_similarity: float,
        filters: Optional[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining multiple signals.

        Combines similarity search with metadata-based boosting
        and other relevance signals.

        FIX #1: Now uses shared V2 cache helpers for consistency
        FIX #2: Uses RetrievalContext for embedding deduplication

        Args:
            context: RetrievalContext with query and optional pre-computed embedding
            top_k: Number of results
            min_similarity: Minimum similarity
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        # FIX #1: Check V2 cache first (now implemented for Hybrid!)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        cached_results = loop.run_until_complete(
            self._check_v2_cache_async(context, top_k)
        )
        if cached_results is not None:
            return cached_results

        # Cache miss - continue with hybrid retrieval
        # Start with similarity search
        results = self._retrieve_similarity(context, top_k * 2, min_similarity, filters)

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
        final_results = results[:top_k]

        # FIX #1: Save to V2 cache using async helper
        loop.run_until_complete(
            self._save_v2_cache_async(context, final_results, top_k)
        )

        return final_results

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
    strategy: RetrievalStrategy = RetrievalStrategy.MMR,
    top_k: int = RAG_TOP_K,
    min_similarity: float = RAG_SIMILARITY_THRESHOLD,
    use_multi_collection: bool = True,
    enable_v2_caching: bool = True,
    enable_query_expansion: bool = True,
    enable_cross_encoder_reranking: bool = True,
) -> Retriever:
    """
    Factory function to create a retriever instance.

    Args:
        vector_store: VectorStore instance
        strategy: Retrieval strategy
        top_k: Number of results
        min_similarity: Minimum similarity threshold
        use_multi_collection: Enable multi-collection manager
        enable_v2_caching: Enable V2 RAG query caching (default: True)
        enable_query_expansion: Enable query expansion (default: True)
        enable_cross_encoder_reranking: Enable cross-encoder semantic re-ranking (default: True)

    Returns:
        Initialized Retriever instance
    """
    config = RetrievalConfig(
        top_k=top_k,
        min_similarity=min_similarity,
        strategy=strategy,
    )

    mcm = MultiCollectionManager(vector_store.embedding_model) if use_multi_collection else None
    return Retriever(
        vector_store=vector_store,
        config=config,
        multi_collection_manager=mcm,
        enable_v2_caching=enable_v2_caching,
        enable_query_expansion=enable_query_expansion,
        enable_cross_encoder_reranking=enable_cross_encoder_reranking,
    )
