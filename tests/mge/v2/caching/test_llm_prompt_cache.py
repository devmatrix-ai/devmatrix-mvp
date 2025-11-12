"""
Unit tests for LLMPromptCache

Tests:
- Cache key generation determinism
- Cache hit scenario
- Cache miss scenario
- Cache set with TTL
- Cache invalidation
- Redis error handling
- Metrics increments
"""

import pytest
import json
import hashlib
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import redis.asyncio as redis

from src.mge.v2.caching.llm_prompt_cache import LLMPromptCache, CachedLLMResponse


@pytest.fixture
async def cache():
    """Create LLMPromptCache instance for testing"""
    cache = LLMPromptCache(redis_url="redis://localhost:6379")
    yield cache
    # Cleanup
    if cache.redis_client:
        await cache.close()


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    mock = AsyncMock()
    return mock


class TestCacheKeyGeneration:
    """Test cache key generation logic"""

    def test_cache_key_deterministic(self):
        """Cache key should be deterministic for same inputs"""
        cache = LLMPromptCache()

        key1 = cache._generate_cache_key("test prompt", "gpt-4", 0.7)
        key2 = cache._generate_cache_key("test prompt", "gpt-4", 0.7)

        assert key1 == key2

    def test_cache_key_unique_prompt(self):
        """Different prompts should generate different keys"""
        cache = LLMPromptCache()

        key1 = cache._generate_cache_key("prompt 1", "gpt-4", 0.7)
        key2 = cache._generate_cache_key("prompt 2", "gpt-4", 0.7)

        assert key1 != key2

    def test_cache_key_unique_model(self):
        """Different models should generate different keys"""
        cache = LLMPromptCache()

        key1 = cache._generate_cache_key("test prompt", "gpt-4", 0.7)
        key2 = cache._generate_cache_key("test prompt", "claude-3-5-sonnet", 0.7)

        assert key1 != key2

    def test_cache_key_unique_temperature(self):
        """Different temperatures should generate different keys"""
        cache = LLMPromptCache()

        key1 = cache._generate_cache_key("test prompt", "gpt-4", 0.7)
        key2 = cache._generate_cache_key("test prompt", "gpt-4", 0.8)

        assert key1 != key2

    def test_cache_key_format(self):
        """Cache key should have correct prefix"""
        cache = LLMPromptCache()

        key = cache._generate_cache_key("test prompt", "gpt-4", 0.7)

        assert key.startswith("llm_cache:")

    def test_cache_key_sha256(self):
        """Cache key should use SHA256 hash"""
        cache = LLMPromptCache()

        key = cache._generate_cache_key("test prompt", "gpt-4", 0.7)

        # Extract hash part (remove prefix)
        hash_part = key.replace("llm_cache:", "")

        # SHA256 hash is 64 characters in hex
        assert len(hash_part) == 64
        assert all(c in "0123456789abcdef" for c in hash_part)


@pytest.mark.asyncio
class TestCacheHit:
    """Test cache hit scenarios"""

    async def test_cache_hit_returns_response(self):
        """Cache hit should return cached response"""
        cache = LLMPromptCache()

        # Mock Redis get to return cached data
        cached_data = {
            "text": "cached response",
            "model": "gpt-4",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.get = AsyncMock(return_value=json.dumps(cached_data))

            result = await cache.get("test prompt", "gpt-4", 0.7)

            assert result is not None
            assert result.text == "cached response"
            assert result.model == "gpt-4"
            assert result.prompt_tokens == 10
            assert result.completion_tokens == 20

    async def test_cache_hit_emits_metric(self):
        """Cache hit should emit hit metric"""
        cache = LLMPromptCache()

        cached_data = {
            "text": "cached response",
            "model": "gpt-4",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "cached_at": 1234567890.0,
        }

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.get = AsyncMock(return_value=json.dumps(cached_data))

            await cache.get("test prompt", "gpt-4", 0.7)

            mock_emit.assert_called_once_with("hit")


@pytest.mark.asyncio
class TestCacheMiss:
    """Test cache miss scenarios"""

    async def test_cache_miss_returns_none(self):
        """Cache miss should return None"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.get = AsyncMock(return_value=None)

            result = await cache.get("test prompt", "gpt-4", 0.7)

            assert result is None

    async def test_cache_miss_emits_metric(self):
        """Cache miss should emit miss metric"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.get = AsyncMock(return_value=None)

            await cache.get("test prompt", "gpt-4", 0.7)

            mock_emit.assert_called_once_with("miss")


@pytest.mark.asyncio
class TestCacheSet:
    """Test cache set operations"""

    async def test_cache_set_stores_data(self):
        """Cache set should store data in Redis"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.setex = AsyncMock()

            await cache.set(
                "test prompt",
                "gpt-4",
                0.7,
                "response text",
                10,
                20,
            )

            mock_client.setex.assert_called_once()

    async def test_cache_set_uses_default_ttl(self):
        """Cache set should use default TTL if not specified"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.setex = AsyncMock()

            # Use a neutral prompt that doesn't trigger prompt type detection
            await cache.set(
                "Sample prompt for caching",
                "gpt-4",
                0.7,
                "response text",
                10,
                20,
            )

            # Check TTL is default (86400) - no type detection triggered
            call_args = mock_client.setex.call_args
            assert call_args[0][1] == 86400  # Default TTL

    async def test_cache_set_custom_ttl(self):
        """Cache set should use custom TTL if specified"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.setex = AsyncMock()

            await cache.set(
                "test prompt", "gpt-4", 0.7, "response text", 10, 20, ttl=3600
            )

            # Check TTL is custom (3600)
            call_args = mock_client.setex.call_args
            assert call_args[0][1] == 3600

    async def test_cache_set_emits_metric(self):
        """Cache set should emit write metric"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.setex = AsyncMock()

            await cache.set(
                "test prompt",
                "gpt-4",
                0.7,
                "response text",
                10,
                20,
            )

            mock_emit.assert_called_once_with("write")


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Test cache invalidation logic"""

    async def test_invalidate_masterplan_scans_pattern(self):
        """Invalidate should scan for pattern"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.scan = AsyncMock(return_value=(0, []))

            await cache.invalidate_masterplan("test-masterplan-id")

            mock_client.scan.assert_called_once()
            call_args = mock_client.scan.call_args
            assert "llm_cache:*test-masterplan-id*" in str(call_args)

    async def test_invalidate_masterplan_deletes_keys(self):
        """Invalidate should delete matching keys"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            # Mock scan to return some keys, then empty
            mock_client.scan = AsyncMock(
                side_effect=[(0, [b"key1", b"key2", b"key3"])]
            )
            mock_client.delete = AsyncMock()

            await cache.invalidate_masterplan("test-masterplan-id")

            mock_client.delete.assert_called_once_with(b"key1", b"key2", b"key3")

    async def test_invalidate_emits_metric(self):
        """Invalidate should emit invalidation metric"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.scan = AsyncMock(return_value=(0, []))

            await cache.invalidate_masterplan("test-masterplan-id")

            mock_emit.assert_called_once_with("invalidation")


@pytest.mark.asyncio
class TestRedisErrorHandling:
    """Test Redis error handling"""

    async def test_get_handles_redis_error(self):
        """Get should handle Redis errors gracefully"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.get = AsyncMock(side_effect=redis.RedisError("Connection error"))

            result = await cache.get("test prompt", "gpt-4", 0.7)

            assert result is None

    async def test_get_emits_error_metric(self):
        """Get should emit error metric on Redis error"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.get = AsyncMock(side_effect=redis.RedisError("Connection error"))

            await cache.get("test prompt", "gpt-4", 0.7)

            mock_emit.assert_any_call("error", operation="get")

    async def test_set_handles_redis_error(self):
        """Set should handle Redis errors gracefully"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ):
            mock_client.setex = AsyncMock(
                side_effect=redis.RedisError("Connection error")
            )

            # Should not raise exception
            await cache.set(
                "test prompt",
                "gpt-4",
                0.7,
                "response text",
                10,
                20,
            )

    async def test_set_emits_error_metric(self):
        """Set should emit error metric on Redis error"""
        cache = LLMPromptCache()

        with patch.object(
            cache, "_ensure_connection", new_callable=AsyncMock
        ), patch.object(
            cache, "redis_client", new_callable=Mock
        ) as mock_client, patch.object(
            cache, "_emit_metric"
        ) as mock_emit:
            mock_client.setex = AsyncMock(
                side_effect=redis.RedisError("Connection error")
            )

            await cache.set(
                "test prompt",
                "gpt-4",
                0.7,
                "response text",
                10,
                20,
            )

            mock_emit.assert_any_call("error", operation="set")
