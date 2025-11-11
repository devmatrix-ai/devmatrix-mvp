"""
RAG Query Cache - Redis-based caching for RAG queries with similarity matching

Caches RAG query results with embedding similarity-based partial hits.

Features:
- SHA256-based cache keys (query + embedding_model + top_k)
- Exact match cache hits
- Similarity-based partial hits (cosine similarity ≥0.95)
- Configurable TTL (default 1 hour, shorter than LLM cache)
- Prometheus metrics integration
- Redis error handling with graceful fallback

Performance:
- Exact match lookup: <5ms
- Similarity search: O(N) but only on cache miss
- Cache write latency: <10ms
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from collections import OrderedDict
from uuid import UUID

import numpy as np
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class CachedRAGResult:
    """Cached RAG query result with embeddings"""

    query: str
    query_embedding: List[float]
    documents: List[Dict]
    cached_at: float


class RAGQueryCache:
    """
    Cache RAG queries with similarity-based partial hits

    For exact matches: hash(query + embedding_model + top_k)
    For partial matches: cosine similarity ≥0.95 on query embeddings

    Example:
        cache = RAGQueryCache()

        # Check cache (exact + similarity)
        cached = await cache.get("find auth code", embedding, "sentence-transformers", 5)
        if cached:
            return cached.documents

        # Cache miss - query vector DB
        results = await vector_db.query(...)

        # Store in cache
        await cache.set("find auth code", embedding, "sentence-transformers", 5, results)
    """

    def __init__(
        self,
        redis_url: str = "redis://redis:6379",
        l1_cache_size: int = 100
    ):
        """
        Initialize RAG query cache with multi-level caching

        L1: In-memory LRU cache (fast, limited size)
        L2: Redis cache (persistent, larger capacity)

        Args:
            redis_url: Redis connection URL (default: redis://redis:6379 for Docker)
            l1_cache_size: L1 cache size (default: 100 entries)
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hour (shorter than LLM cache due to code changes)
        self.prefix = "rag_cache:"
        self.similarity_threshold = 0.95

        # L1 cache: In-memory LRU cache for hot queries
        self.l1_cache: OrderedDict[str, CachedRAGResult] = OrderedDict()
        self.l1_cache_size = l1_cache_size

        # Sorted set for fast similarity lookup
        self.similarity_index_key = f"{self.prefix}similarity_index"

        # Metrics will be imported later to avoid circular dependency
        self._metrics_initialized = False

    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if self.redis_client is None:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url, decode_responses=False
                )
                logger.info(f"RAG cache connected to Redis at {self.redis_url}")
            except redis.RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    def _add_to_l1_cache(self, cache_key: str, result: CachedRAGResult):
        """
        Add result to L1 cache with LRU eviction

        Args:
            cache_key: Cache key
            result: Cached RAG result
        """
        # Remove oldest entry if cache is full
        if len(self.l1_cache) >= self.l1_cache_size:
            # Remove oldest (first) entry
            self.l1_cache.popitem(last=False)

        # Add to cache (at end = most recent)
        self.l1_cache[cache_key] = result

        logger.debug(f"Added to L1 cache: {cache_key[:16]}... (size={len(self.l1_cache)})")

    def _get_from_l1_cache(self, cache_key: str) -> Optional[CachedRAGResult]:
        """
        Get result from L1 cache and move to end (MRU)

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None if not in L1
        """
        if cache_key in self.l1_cache:
            # Move to end (most recently used)
            self.l1_cache.move_to_end(cache_key)

            logger.debug(f"L1 cache HIT: {cache_key[:16]}...")

            self._emit_metric("hit", cache_layer="rag_l1")

            return self.l1_cache[cache_key]

        return None

    def _compute_embedding_hash(self, embedding: List[float]) -> float:
        """
        Compute hash of embedding for sorted set score

        Uses first 4 components of embedding to create a float score.
        This enables fast range queries in sorted set.

        Args:
            embedding: Embedding vector

        Returns:
            Float score for sorted set
        """
        # Use first 4 components to create score
        # Normalize to [0, 1] range
        components = embedding[:4]
        score = sum(abs(c) for c in components) / len(components)

        return score

    async def _add_to_similarity_index(
        self,
        cache_key: str,
        embedding: List[float]
    ):
        """
        Add embedding to similarity index (Redis sorted set)

        Args:
            cache_key: Cache key
            embedding: Query embedding
        """
        try:
            await self._ensure_connection()

            score = self._compute_embedding_hash(embedding)

            # Add to sorted set with score
            await self.redis_client.zadd(
                self.similarity_index_key,
                {cache_key: score}
            )

            logger.debug(f"Added to similarity index: {cache_key[:16]}... (score={score:.4f})")

        except redis.RedisError as e:
            logger.error(f"Failed to add to similarity index: {e}")

    async def _find_similar_in_index(
        self,
        embedding: List[float],
        top_k: int
    ) -> Optional[Tuple[str, CachedRAGResult]]:
        """
        Fast similarity search using sorted set index

        Strategy:
        1. Compute embedding hash score
        2. Query sorted set for nearby scores (±0.1 range)
        3. Check actual cosine similarity for candidates
        4. Return first match above threshold

        Args:
            embedding: Query embedding
            top_k: Number of documents (must match)

        Returns:
            (cache_key, result) tuple or None
        """
        try:
            await self._ensure_connection()

            score = self._compute_embedding_hash(embedding)

            # Query sorted set for nearby scores (±0.1 range)
            min_score = max(0.0, score - 0.1)
            max_score = min(1.0, score + 0.1)

            # Get candidates from sorted set
            candidates = await self.redis_client.zrangebyscore(
                self.similarity_index_key,
                min_score,
                max_score
            )

            if not candidates:
                return None

            query_embedding_np = np.array(embedding)

            # Check actual similarity for each candidate
            for candidate_key in candidates:
                cached_data = await self.redis_client.get(candidate_key)

                if not cached_data:
                    continue

                data = json.loads(cached_data)

                # Must have same top_k
                if data["top_k"] != top_k:
                    continue

                cached_embedding_np = np.array(data["query_embedding"])

                # Compute cosine similarity
                similarity = np.dot(query_embedding_np, cached_embedding_np) / (
                    np.linalg.norm(query_embedding_np)
                    * np.linalg.norm(cached_embedding_np)
                )

                if similarity >= self.similarity_threshold:
                    logger.info(
                        f"Found similar in index (similarity={similarity:.3f})"
                    )

                    return (
                        candidate_key.decode() if isinstance(candidate_key, bytes) else candidate_key,
                        CachedRAGResult(
                            query=data["query"],
                            query_embedding=data["query_embedding"],
                            documents=data["documents"],
                            cached_at=data["cached_at"],
                        )
                    )

            return None

        except Exception as e:
            logger.error(f"Error in similarity index search: {e}")
            return None

    def _generate_cache_key(
        self, query: str, embedding_model: str, top_k: int
    ) -> str:
        """
        Generate cache key from query params

        Args:
            query: RAG query text
            embedding_model: Embedding model name
            top_k: Number of documents to retrieve

        Returns:
            SHA256 hash as hex string with prefix
        """
        content = f"{query}|{embedding_model}|{top_k}"
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        return f"{self.prefix}{hash_obj.hexdigest()}"

    async def get(
        self,
        query: str,
        query_embedding: List[float],
        embedding_model: str,
        top_k: int,
    ) -> Optional[CachedRAGResult]:
        """
        Get cached RAG result with multi-level cache

        Lookup order:
        1. L1 cache (in-memory, fast)
        2. L2 cache exact match (Redis)
        3. L2 cache similarity match (Redis sorted set index)

        Args:
            query: RAG query text
            query_embedding: Query embedding vector
            embedding_model: Embedding model name
            top_k: Number of documents requested

        Returns:
            CachedRAGResult or None if cache miss
        """
        cache_key = self._generate_cache_key(query, embedding_model, top_k)

        try:
            # 1. Try L1 cache first (fastest)
            l1_result = self._get_from_l1_cache(cache_key)

            if l1_result:
                logger.info(f"RAG cache HIT (L1): {cache_key[:16]}...")
                return l1_result

            await self._ensure_connection()

            # 2. Try L2 exact match
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                result = CachedRAGResult(
                    query=data["query"],
                    query_embedding=data["query_embedding"],
                    documents=data["documents"],
                    cached_at=data["cached_at"],
                )

                # Add to L1 cache for future hits
                self._add_to_l1_cache(cache_key, result)

                # Emit L2 exact match hit metric
                self._emit_metric("hit", cache_layer="rag_l2_exact")

                logger.info(f"RAG cache HIT (L2 exact): {cache_key[:16]}...")

                return result

            # 3. Try L2 similarity match using sorted set index
            similar_match = await self._find_similar_in_index(
                query_embedding, top_k
            )

            if similar_match:
                similar_key, similar_result = similar_match

                # Add to L1 cache for future hits
                self._add_to_l1_cache(cache_key, similar_result)

                # Emit L2 similarity match hit metric
                self._emit_metric("hit", cache_layer="rag_l2_similarity")

                logger.info(f"RAG cache HIT (L2 similarity): {cache_key[:16]}...")

                return similar_result

            # Cache miss
            self._emit_metric("miss", cache_layer="rag")
            logger.debug(f"RAG cache MISS: {cache_key[:16]}...")

            return None

        except redis.RedisError as e:
            logger.error(f"Redis error on RAG cache get: {e}")
            self._emit_metric("error", cache_layer="rag", operation="get")
            return None
        except Exception as e:
            logger.error(f"Unexpected error on RAG cache get: {e}")
            return None

    async def set(
        self,
        query: str,
        query_embedding: List[float],
        embedding_model: str,
        top_k: int,
        documents: List[Dict],
        ttl: Optional[int] = None,
    ):
        """
        Store RAG query result in cache (L1 + L2 + similarity index)

        Writes to:
        1. L1 cache (in-memory LRU)
        2. L2 cache (Redis)
        3. Similarity index (Redis sorted set)

        Args:
            query: RAG query text
            query_embedding: Query embedding vector
            embedding_model: Embedding model name
            top_k: Number of documents
            documents: Retrieved documents
            ttl: Time-to-live in seconds (default: 1h)
        """
        cache_key = self._generate_cache_key(query, embedding_model, top_k)

        cached_result_dict = {
            "query": query,
            "query_embedding": query_embedding,
            "embedding_model": embedding_model,
            "top_k": top_k,
            "documents": documents,
            "cached_at": time.time(),
        }

        cached_result_obj = CachedRAGResult(
            query=query,
            query_embedding=query_embedding,
            documents=documents,
            cached_at=cached_result_dict["cached_at"]
        )

        try:
            # 1. Write to L1 cache
            self._add_to_l1_cache(cache_key, cached_result_obj)

            await self._ensure_connection()

            # 2. Write to L2 cache (Redis)
            await self.redis_client.setex(
                cache_key, ttl or self.default_ttl, json.dumps(cached_result_dict)
            )

            # 3. Add to similarity index
            await self._add_to_similarity_index(cache_key, query_embedding)

            self._emit_metric("write", cache_layer="rag")

            logger.debug(
                f"RAG cache SET (L1+L2+index): {cache_key[:16]}... (TTL={ttl or self.default_ttl}s)"
            )

        except redis.RedisError as e:
            logger.error(f"Redis error on RAG cache set: {e}")
            self._emit_metric("error", cache_layer="rag", operation="set")
        except Exception as e:
            logger.error(f"Unexpected error on RAG cache set: {e}")

    async def invalidate_by_scope(
        self,
        scope: str,
        scope_id: UUID
    ):
        """
        Invalidate cache entries by scope (atom, phase, masterplan)

        Granular invalidation for different levels:
        - atom: When single atom is regenerated
        - phase: When phase is retried
        - masterplan: When entire masterplan is regenerated

        Args:
            scope: Scope level ('atom', 'phase', 'masterplan')
            scope_id: UUID of the scope
        """
        pattern_map = {
            "atom": f"{self.prefix}*atom_{scope_id}*",
            "phase": f"{self.prefix}*phase_{scope_id}*",
            "masterplan": f"{self.prefix}*masterplan_{scope_id}*"
        }

        pattern = pattern_map.get(scope, f"{self.prefix}*{scope_id}*")

        try:
            await self._ensure_connection()
            cursor = 0
            deleted_count = 0

            # Scan and delete from Redis
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor, match=pattern, count=100
                )

                if keys:
                    # Delete from L2 cache
                    await self.redis_client.delete(*keys)

                    # Remove from similarity index
                    await self.redis_client.zrem(
                        self.similarity_index_key,
                        *keys
                    )

                    deleted_count += len(keys)

                if cursor == 0:
                    break

            # Clear L1 cache entries matching scope
            # (Simple approach: clear all L1 cache when invalidating)
            if deleted_count > 0:
                self.l1_cache.clear()

            logger.info(
                f"Invalidated {deleted_count} cache entries for {scope} {scope_id}"
            )

        except redis.RedisError as e:
            logger.error(f"Redis error on cache invalidation: {e}")
        except Exception as e:
            logger.error(f"Unexpected error on cache invalidation: {e}")

    def _emit_metric(
        self, metric_type: str, cache_layer: str = "rag", operation: str = None
    ):
        """
        Emit Prometheus metric

        Args:
            metric_type: Type of metric (hit, miss, write, error)
            cache_layer: Cache layer (rag, rag_similarity)
            operation: Operation name for error metrics (get, set)
        """
        try:
            # Import metrics here to avoid circular dependency
            if not self._metrics_initialized:
                from .metrics import (
                    CACHE_HIT_RATE,
                    CACHE_MISS_RATE,
                    CACHE_WRITES,
                    CACHE_ERRORS,
                )

                self._CACHE_HIT_RATE = CACHE_HIT_RATE
                self._CACHE_MISS_RATE = CACHE_MISS_RATE
                self._CACHE_WRITES = CACHE_WRITES
                self._CACHE_ERRORS = CACHE_ERRORS
                self._metrics_initialized = True

            if metric_type == "hit":
                self._CACHE_HIT_RATE.labels(cache_layer=cache_layer).inc()
            elif metric_type == "miss":
                self._CACHE_MISS_RATE.labels(cache_layer=cache_layer).inc()
            elif metric_type == "write":
                self._CACHE_WRITES.labels(cache_layer=cache_layer).inc()
            elif metric_type == "error":
                self._CACHE_ERRORS.labels(
                    cache_layer=cache_layer, operation=operation
                ).inc()

        except ImportError:
            # Metrics not available yet (during initial setup)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit metric: {e}")

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Closed RAG cache Redis connection")
