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
from typing import Optional, List, Dict

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

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize RAG query cache

        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379)
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hour (shorter than LLM cache due to code changes)
        self.prefix = "rag_cache:"
        self.similarity_threshold = 0.95

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
        Get cached RAG result

        First tries exact match, then similarity-based partial match

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
            await self._ensure_connection()

            # Try exact match first
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                # Emit exact match hit metric
                self._emit_metric("hit", cache_layer="rag")

                logger.info(f"RAG cache HIT (exact): {cache_key[:16]}...")

                return CachedRAGResult(
                    query=data["query"],
                    query_embedding=data["query_embedding"],
                    documents=data["documents"],
                    cached_at=data["cached_at"],
                )

            # Try similarity-based partial match
            similar_result = await self._find_similar_cached_query(
                query_embedding, top_k
            )

            if similar_result:
                # Emit similarity match hit metric
                self._emit_metric("hit", cache_layer="rag_similarity")

                logger.info(f"RAG cache HIT (similarity): {cache_key[:16]}...")

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
        Store RAG query result in cache

        Args:
            query: RAG query text
            query_embedding: Query embedding vector
            embedding_model: Embedding model name
            top_k: Number of documents
            documents: Retrieved documents
            ttl: Time-to-live in seconds (default: 1h)
        """
        cache_key = self._generate_cache_key(query, embedding_model, top_k)

        cached_result = {
            "query": query,
            "query_embedding": query_embedding,
            "embedding_model": embedding_model,
            "top_k": top_k,
            "documents": documents,
            "cached_at": time.time(),
        }

        try:
            await self._ensure_connection()
            await self.redis_client.setex(
                cache_key, ttl or self.default_ttl, json.dumps(cached_result)
            )

            self._emit_metric("write", cache_layer="rag")

            logger.debug(
                f"RAG cache SET: {cache_key[:16]}... (TTL={ttl or self.default_ttl}s)"
            )

        except redis.RedisError as e:
            logger.error(f"Redis error on RAG cache set: {e}")
            self._emit_metric("error", cache_layer="rag", operation="set")
        except Exception as e:
            logger.error(f"Unexpected error on RAG cache set: {e}")

    async def _find_similar_cached_query(
        self, query_embedding: List[float], top_k: int
    ) -> Optional[CachedRAGResult]:
        """
        Find cached query with similar embedding (cosine similarity ≥0.95)

        This is expensive (O(N) scan) but only runs on cache miss.

        Args:
            query_embedding: Query embedding to match against
            top_k: Number of documents (must match)

        Returns:
            CachedRAGResult if similar query found, None otherwise
        """
        try:
            await self._ensure_connection()
            pattern = f"{self.prefix}*"
            cursor = 0

            query_embedding_np = np.array(query_embedding)

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor, match=pattern, count=50
                )

                for key in keys:
                    cached_data = await self.redis_client.get(key)
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
                            f"Found similar cached query (similarity={similarity:.3f})"
                        )

                        return CachedRAGResult(
                            query=data["query"],
                            query_embedding=data["query_embedding"],
                            documents=data["documents"],
                            cached_at=data["cached_at"],
                        )

                if cursor == 0:
                    break

            return None

        except Exception as e:
            logger.error(f"Error finding similar cached query: {e}")
            return None

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
