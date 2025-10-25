"""
Unit tests for RAGQueryCache

Tests:
- Cache key generation
- Exact match cache hit
- Similarity-based cache hit (≥0.95)
- Cache miss (no similar queries)
- Cache set with 1h TTL
- Cosine similarity calculation
- Redis error handling
- Metrics increments (exact + similarity)
"""

import pytest
import json
import numpy as np
from unittest.mock import AsyncMock, Mock, patch
import redis.asyncio as redis

from src.mge.v2.caching.rag_query_cache import RAGQueryCache, CachedRAGResult


@pytest.fixture
async def cache():
    """Create RAGQueryCache instance for testing"""
    cache = RAGQueryCache(redis_url="redis://localhost:6379")
    yield cache
    if cache.redis_client:
        await cache.close()


class TestCacheKeyGeneration:
    """Test cache key generation logic"""

    def test_cache_key_deterministic(self):
        """Cache key should be deterministic for same inputs"""
        cache = RAGQueryCache()

        key1 = cache._generate_cache_key("test query", "sentence-transformers", 5)
        key2 = cache._generate_cache_key("test query", "sentence-transformers", 5)

        assert key1 == key2

    def test_cache_key_unique_query(self):
        """Different queries should generate different keys"""
        cache = RAGQueryCache()

        key1 = cache._generate_cache_key("query 1", "sentence-transformers", 5)
        key2 = cache._generate_cache_key("query 2", "sentence-transformers", 5)

        assert key1 != key2

    def test_cache_key_unique_model(self):
        """Different models should generate different keys"""
        cache = RAGQueryCache()

        key1 = cache._generate_cache_key("test query", "model-a", 5)
        key2 = cache._generate_cache_key("test query", "model-b", 5)

        assert key1 != key2

    def test_cache_key_unique_top_k(self):
        """Different top_k should generate different keys"""
        cache = RAGQueryCache()

        key1 = cache._generate_cache_key("test query", "sentence-transformers", 5)
        key2 = cache._generate_cache_key("test query", "sentence-transformers", 10)

        assert key1 != key2

    def test_cache_key_format(self):
        """Cache key should have correct prefix"""
        cache = RAGQueryCache()

        key = cache._generate_cache_key("test query", "sentence-transformers", 5)

        assert key.startswith("rag_cache:")


@pytest.mark.asyncio
class TestExactMatchCacheHit:
    """Test exact match cache hit scenarios"""

    async def test_exact_match_returns_response(self):
        """Exact match cache hit should return cached response"""
        cache = RAGQueryCache()

        cached_data = {
            "query": "test query",
            "query_embedding": [0.1, 0.2, 0.3],
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [{"id": 1, "text": "doc 1"}],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.get = AsyncMock(return_value=json.dumps(cached_data))

            result = await cache.get(
                "test query", [0.1, 0.2, 0.3], "sentence-transformers", 5
            )

            assert result is not None
            assert result.query == "test query"
            assert result.documents == [{"id": 1, "text": "doc 1"}]

    async def test_exact_match_emits_rag_metric(self):
        """Exact match should emit rag hit metric"""
        cache = RAGQueryCache()

        cached_data = {
            "query": "test query",
            "query_embedding": [0.1, 0.2, 0.3],
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.get = AsyncMock(return_value=json.dumps(cached_data))

            await cache.get("test query", [0.1, 0.2, 0.3], "sentence-transformers", 5)

            mock_emit.assert_any_call("hit", cache_layer="rag")


@pytest.mark.asyncio
class TestSimilarityBasedCacheHit:
    """Test similarity-based cache hit scenarios"""

    async def test_similarity_match_returns_response(self):
        """Similarity match (≥0.95) should return cached response"""
        cache = RAGQueryCache()

        # Create similar embeddings (cosine similarity ≥ 0.95)
        query_embedding = np.array([1.0, 0.0, 0.0])
        cached_embedding = np.array([0.96, 0.28, 0.0])  # ~0.96 cosine similarity

        cached_data = {
            "query": "similar query",
            "query_embedding": cached_embedding.tolist(),
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [{"id": 1, "text": "doc 1"}],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            # Exact match miss, similarity match hit
            mock_client.get = AsyncMock(return_value=None)
            mock_client.scan = AsyncMock(return_value=(0, [b"rag_cache:key1"]))

            # Mock second get for similarity search
            async def get_side_effect(key):
                if key == b"rag_cache:key1":
                    return json.dumps(cached_data)
                return None

            mock_client.get = AsyncMock(side_effect=get_side_effect)

            result = await cache.get(
                "test query", query_embedding.tolist(), "sentence-transformers", 5
            )

            assert result is not None
            assert result.query == "similar query"

    async def test_similarity_match_emits_similarity_metric(self):
        """Similarity match should emit rag_similarity hit metric"""
        cache = RAGQueryCache()

        query_embedding = np.array([1.0, 0.0, 0.0])
        cached_embedding = np.array([0.96, 0.28, 0.0])

        cached_data = {
            "query": "similar query",
            "query_embedding": cached_embedding.tolist(),
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.scan = AsyncMock(return_value=(0, [b"rag_cache:key1"]))

            async def get_side_effect(key):
                if key == b"rag_cache:key1":
                    return json.dumps(cached_data)
                return None

            mock_client.get = AsyncMock(side_effect=get_side_effect)

            await cache.get(
                "test query", query_embedding.tolist(), "sentence-transformers", 5
            )

            mock_emit.assert_any_call("hit", cache_layer="rag_similarity")

    async def test_low_similarity_returns_none(self):
        """Similarity below threshold (<0.95) should return None"""
        cache = RAGQueryCache()

        # Create dissimilar embeddings (cosine similarity < 0.95)
        query_embedding = np.array([1.0, 0.0, 0.0])
        cached_embedding = np.array([0.5, 0.5, 0.5])  # ~0.58 cosine similarity

        cached_data = {
            "query": "dissimilar query",
            "query_embedding": cached_embedding.tolist(),
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.scan = AsyncMock(return_value=(0, [b"rag_cache:key1"]))

            async def get_side_effect(key):
                if key == b"rag_cache:key1":
                    return json.dumps(cached_data)
                return None

            mock_client.get = AsyncMock(side_effect=get_side_effect)

            result = await cache.get(
                "test query", query_embedding.tolist(), "sentence-transformers", 5
            )

            assert result is None


@pytest.mark.asyncio
class TestCosineSimilarity:
    """Test cosine similarity calculation"""

    async def test_identical_vectors_similarity_1(self):
        """Identical vectors should have similarity = 1.0"""
        cache = RAGQueryCache()

        embedding = np.array([1.0, 0.0, 0.0])

        cached_data = {
            "query": "test",
            "query_embedding": embedding.tolist(),
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.scan = AsyncMock(return_value=(0, [b"rag_cache:key1"]))

            async def get_side_effect(key):
                if key == b"rag_cache:key1":
                    return json.dumps(cached_data)
                return None

            mock_client.get = AsyncMock(side_effect=get_side_effect)

            result = await cache.get("test", embedding.tolist(), "sentence-transformers", 5)

            # Should match (similarity = 1.0 ≥ 0.95)
            assert result is not None

    async def test_orthogonal_vectors_similarity_0(self):
        """Orthogonal vectors should have similarity ≈ 0.0"""
        cache = RAGQueryCache()

        query_embedding = np.array([1.0, 0.0, 0.0])
        cached_embedding = np.array([0.0, 1.0, 0.0])

        cached_data = {
            "query": "test",
            "query_embedding": cached_embedding.tolist(),
            "embedding_model": "sentence-transformers",
            "top_k": 5,
            "documents": [],
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.scan = AsyncMock(return_value=(0, [b"rag_cache:key1"]))

            async def get_side_effect(key):
                if key == b"rag_cache:key1":
                    return json.dumps(cached_data)
                return None

            mock_client.get = AsyncMock(side_effect=get_side_effect)

            result = await cache.get(
                "test", query_embedding.tolist(), "sentence-transformers", 5
            )

            # Should not match (similarity ≈ 0.0 < 0.95)
            assert result is None


@pytest.mark.asyncio
class TestCacheMiss:
    """Test cache miss scenarios"""

    async def test_cache_miss_returns_none(self):
        """Cache miss should return None"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.get = AsyncMock(return_value=None)
            mock_client.scan = AsyncMock(return_value=(0, []))

            result = await cache.get("test query", [0.1, 0.2], "sentence-transformers", 5)

            assert result is None

    async def test_cache_miss_emits_metric(self):
        """Cache miss should emit miss metric"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.get = AsyncMock(return_value=None)
            mock_client.scan = AsyncMock(return_value=(0, []))

            await cache.get("test query", [0.1, 0.2], "sentence-transformers", 5)

            mock_emit.assert_any_call("miss", cache_layer="rag")


@pytest.mark.asyncio
class TestCacheSet:
    """Test cache set operations"""

    async def test_cache_set_stores_data(self):
        """Cache set should store data in Redis"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.setex = AsyncMock()

            await cache.set(
                "test query",
                [0.1, 0.2, 0.3],
                "sentence-transformers",
                5,
                [{"id": 1}],
            )

            mock_client.setex.assert_called_once()

    async def test_cache_set_uses_default_ttl(self):
        """Cache set should use default TTL (1h) if not specified"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.setex = AsyncMock()

            await cache.set(
                "test query",
                [0.1, 0.2, 0.3],
                "sentence-transformers",
                5,
                [{"id": 1}],
            )

            # Check TTL is 1 hour (3600)
            call_args = mock_client.setex.call_args
            assert call_args[0][1] == 3600

    async def test_cache_set_emits_metric(self):
        """Cache set should emit write metric"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.setex = AsyncMock()

            await cache.set(
                "test query",
                [0.1, 0.2, 0.3],
                "sentence-transformers",
                5,
                [{"id": 1}],
            )

            mock_emit.assert_called_once_with("write", cache_layer="rag")


@pytest.mark.asyncio
class TestRedisErrorHandling:
    """Test Redis error handling"""

    async def test_get_handles_redis_error(self):
        """Get should handle Redis errors gracefully"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.get = AsyncMock(side_effect=redis.RedisError("Connection error"))

            result = await cache.get("test", [0.1], "sentence-transformers", 5)

            assert result is None

    async def test_get_emits_error_metric(self):
        """Get should emit error metric on Redis error"""
        cache = RAGQueryCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(cache, "redis_client", new_callable=Mock) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.get = AsyncMock(side_effect=redis.RedisError("Connection error"))

            await cache.get("test", [0.1], "sentence-transformers", 5)

            mock_emit.assert_called_with("error", cache_layer="rag", operation="get")
