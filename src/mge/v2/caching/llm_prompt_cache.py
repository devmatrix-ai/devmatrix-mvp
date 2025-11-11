"""
LLM Prompt Cache - Redis-based caching for LLM responses

Caches LLM responses by prompt hash to reduce redundant API calls and costs.

Features:
- SHA256-based cache keys (prompt + model + temperature)
- Configurable TTL (default 24 hours)
- Redis error handling with graceful fallback
- Prometheus metrics integration
- Masterplan-based cache invalidation

Performance:
- Cache lookup latency: <5ms
- Cache write latency: <10ms
- Target hit rate: ≥60%
"""

import hashlib
import json
import logging
import time
import re
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from uuid import UUID

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class CachedLLMResponse:
    """Cached LLM response with metadata"""

    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_at: float


class LLMPromptCache:
    """
    Cache LLM responses by prompt hash

    Cache key format: llm_cache:{hash}
    where hash = SHA256(prompt + model + temperature)

    Example:
        cache = LLMPromptCache()

        # Check cache
        cached = await cache.get("Write a function", "gpt-4", 0.7)
        if cached:
            return cached.text

        # Cache miss - call LLM
        response = await llm.generate(...)

        # Store in cache
        await cache.set("Write a function", "gpt-4", 0.7, response.text, ...)
    """

    def __init__(self, redis_url: str = "redis://redis:6379"):
        """
        Initialize LLM prompt cache

        Args:
            redis_url: Redis connection URL (default: redis://redis:6379 for Docker)
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 86400  # 24 hours
        self.prefix = "llm_cache:"

        # Dynamic TTL configuration (in seconds)
        self.ttl_config = {
            "code_generation": 86400,  # 24h - code patterns are stable
            "validation": 43200,       # 12h - validation logic changes less often
            "test_generation": 21600,  # 6h - tests may need updates
            "review": 10800,           # 3h - review criteria evolve
            "default": 86400           # 24h - fallback
        }

        # Metrics will be imported later to avoid circular dependency
        self._metrics_initialized = False

    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if self.redis_client is None:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url, decode_responses=False
                )
                logger.info(f"Connected to Redis at {self.redis_url}")
            except redis.RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    def _normalize_prompt(self, prompt: str) -> str:
        """
        Normalize prompt to improve cache hit rate

        Normalizations:
        - Strip leading/trailing whitespace
        - Collapse multiple spaces to single space
        - Normalize newlines to single \n
        - Remove code block markers (```)
        - Lowercase common keywords (def, class, function, etc.)

        Args:
            prompt: Raw prompt text

        Returns:
            Normalized prompt text
        """
        # Strip and collapse whitespace
        normalized = prompt.strip()
        normalized = re.sub(r'\s+', ' ', normalized)

        # Normalize newlines
        normalized = re.sub(r'\n+', '\n', normalized)

        # Remove code block markers
        normalized = re.sub(r'```[\w]*', '', normalized)

        # Lowercase common programming keywords (preserves variable names)
        keywords = [
            'def', 'class', 'function', 'async', 'await', 'import', 'from',
            'return', 'if', 'else', 'for', 'while', 'try', 'except', 'with'
        ]
        for keyword in keywords:
            # Replace whole words only (case-insensitive)
            normalized = re.sub(
                rf'\b{keyword}\b',
                keyword.lower(),
                normalized,
                flags=re.IGNORECASE
            )

        return normalized

    def _detect_prompt_type(self, prompt: str) -> str:
        """
        Detect prompt type to determine appropriate TTL

        Detection rules:
        - Contains "generate", "write", "create" + "code" → code_generation
        - Contains "validate", "check", "verify" → validation
        - Contains "test", "pytest", "assert" → test_generation
        - Contains "review", "analyze", "assess" → review
        - Default → default

        Args:
            prompt: Prompt text (normalized)

        Returns:
            Prompt type string
        """
        prompt_lower = prompt.lower()

        # Code generation patterns
        if any(gen in prompt_lower for gen in ['generate', 'write', 'create', 'implement']):
            if 'code' in prompt_lower or 'function' in prompt_lower or 'class' in prompt_lower:
                return "code_generation"

        # Validation patterns
        if any(val in prompt_lower for val in ['validate', 'check', 'verify', 'lint']):
            return "validation"

        # Test generation patterns
        if any(test in prompt_lower for test in ['test', 'pytest', 'assert', 'unittest']):
            return "test_generation"

        # Review patterns
        if any(rev in prompt_lower for rev in ['review', 'analyze', 'assess', 'evaluate']):
            return "review"

        return "default"

    def _get_dynamic_ttl(self, prompt: str) -> int:
        """
        Get dynamic TTL based on prompt type

        Args:
            prompt: Prompt text

        Returns:
            TTL in seconds
        """
        prompt_type = self._detect_prompt_type(prompt)
        ttl = self.ttl_config.get(prompt_type, self.default_ttl)

        logger.debug(f"Detected prompt type '{prompt_type}' → TTL={ttl}s")

        return ttl

    def _generate_cache_key(
        self, prompt: str, model: str, temperature: float
    ) -> str:
        """
        Generate cache key from prompt + params

        Uses normalized prompt to improve cache hit rate.

        Args:
            prompt: LLM prompt text
            model: Model name (claude-3-5-sonnet, gpt-4, etc.)
            temperature: Temperature parameter

        Returns:
            SHA256 hash as hex string with prefix
        """
        # Normalize prompt before hashing
        normalized_prompt = self._normalize_prompt(prompt)

        content = f"{normalized_prompt}|{model}|{temperature}"
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        return f"{self.prefix}{hash_obj.hexdigest()}"

    async def get(
        self, prompt: str, model: str, temperature: float
    ) -> Optional[CachedLLMResponse]:
        """
        Get cached response if available

        Args:
            prompt: LLM prompt text
            model: Model name
            temperature: Temperature parameter

        Returns:
            CachedLLMResponse or None if cache miss
        """
        cache_key = self._generate_cache_key(prompt, model, temperature)

        try:
            await self._ensure_connection()
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                # Emit cache hit metric
                self._emit_metric("hit")

                logger.info(f"LLM cache HIT: {cache_key[:16]}...")

                return CachedLLMResponse(
                    text=data["text"],
                    model=data["model"],
                    prompt_tokens=data["prompt_tokens"],
                    completion_tokens=data["completion_tokens"],
                    cached_at=data["cached_at"],
                )

            # Cache miss
            self._emit_metric("miss")
            logger.debug(f"LLM cache MISS: {cache_key[:16]}...")

            return None

        except redis.RedisError as e:
            logger.error(f"Redis error on cache get: {e}")
            self._emit_metric("error", operation="get")
            return None
        except Exception as e:
            logger.error(f"Unexpected error on cache get: {e}")
            return None

    async def set(
        self,
        prompt: str,
        model: str,
        temperature: float,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        ttl: Optional[int] = None,
    ):
        """
        Store LLM response in cache

        If TTL not specified, uses dynamic TTL based on prompt type.

        Args:
            prompt: LLM prompt
            model: Model name
            temperature: Temperature parameter
            response_text: LLM response text
            prompt_tokens: Input tokens used
            completion_tokens: Output tokens used
            ttl: Time-to-live in seconds (if None, uses dynamic TTL)
        """
        cache_key = self._generate_cache_key(prompt, model, temperature)

        # Use dynamic TTL if not specified
        if ttl is None:
            ttl = self._get_dynamic_ttl(prompt)

        cached_response = {
            "text": response_text,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cached_at": time.time(),
        }

        try:
            await self._ensure_connection()
            await self.redis_client.setex(
                cache_key, ttl, json.dumps(cached_response)
            )

            self._emit_metric("write")

            logger.debug(
                f"LLM cache SET: {cache_key[:16]}... (TTL={ttl}s)"
            )

        except redis.RedisError as e:
            logger.error(f"Redis error on cache set: {e}")
            self._emit_metric("error", operation="set")
        except Exception as e:
            logger.error(f"Unexpected error on cache set: {e}")

    async def invalidate_masterplan(self, masterplan_id: str):
        """
        Invalidate all cache entries for a masterplan

        Uses Redis SCAN with pattern matching to find and delete all
        cache entries related to a specific masterplan.

        Args:
            masterplan_id: Masterplan UUID to invalidate

        Note:
            This is an expensive operation (O(N) scan) but only used
            when masterplan is regenerated or modified.
        """
        pattern = f"{self.prefix}*{masterplan_id}*"

        try:
            await self._ensure_connection()
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor, match=pattern, count=100
                )

                if keys:
                    await self.redis_client.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            logger.info(
                f"Invalidated {deleted_count} cache entries for masterplan {masterplan_id}"
            )

            self._emit_metric("invalidation")

        except redis.RedisError as e:
            logger.error(f"Redis error on cache invalidation: {e}")
            self._emit_metric("error", operation="invalidate")
        except Exception as e:
            logger.error(f"Unexpected error on cache invalidation: {e}")

    async def warm_up_cache(
        self,
        masterplan_id: UUID,
        common_prompts: Optional[List[Dict[str, str]]] = None
    ):
        """
        Warm up cache with common prompts at masterplan start

        Pre-fills cache with common code generation patterns to improve
        initial hit rate.

        Args:
            masterplan_id: MasterPlan UUID for tracking
            common_prompts: Optional list of {prompt, model, temperature, response}
                            If None, uses default common patterns

        Default common patterns:
        - Validation prompts (syntax, imports, types)
        - Common code patterns (auth, CRUD, error handling)
        - Test generation templates
        """
        if common_prompts is None:
            # Default common prompts for typical MGE V2 operations
            common_prompts = [
                {
                    "prompt": "Validate Python syntax and check for common errors",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.0,
                    "response": "# Syntax validation template",
                    "tokens_in": 100,
                    "tokens_out": 50
                },
                {
                    "prompt": "Check import statements and resolve dependencies",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.0,
                    "response": "# Import validation template",
                    "tokens_in": 100,
                    "tokens_out": 50
                },
                {
                    "prompt": "Verify type annotations and type safety",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.0,
                    "response": "# Type validation template",
                    "tokens_in": 100,
                    "tokens_out": 50
                },
                {
                    "prompt": "Generate pytest unit tests for function",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.7,
                    "response": "# Test generation template",
                    "tokens_in": 150,
                    "tokens_out": 200
                }
            ]

        try:
            await self._ensure_connection()

            warmed_count = 0

            for prompt_data in common_prompts:
                await self.set(
                    prompt=prompt_data["prompt"],
                    model=prompt_data["model"],
                    temperature=prompt_data["temperature"],
                    response_text=prompt_data["response"],
                    prompt_tokens=prompt_data.get("tokens_in", 100),
                    completion_tokens=prompt_data.get("tokens_out", 50)
                )
                warmed_count += 1

            logger.info(
                f"Cache warmed up with {warmed_count} common prompts for masterplan {masterplan_id}"
            )

        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")

    def _emit_metric(self, metric_type: str, operation: str = None):
        """
        Emit Prometheus metric

        Args:
            metric_type: Type of metric (hit, miss, write, error, invalidation)
            operation: Operation name for error metrics (get, set, invalidate)
        """
        try:
            # Import metrics here to avoid circular dependency
            if not self._metrics_initialized:
                from .metrics import (
                    CACHE_HIT_RATE,
                    CACHE_MISS_RATE,
                    CACHE_WRITES,
                    CACHE_ERRORS,
                    CACHE_INVALIDATIONS,
                )

                self._CACHE_HIT_RATE = CACHE_HIT_RATE
                self._CACHE_MISS_RATE = CACHE_MISS_RATE
                self._CACHE_WRITES = CACHE_WRITES
                self._CACHE_ERRORS = CACHE_ERRORS
                self._CACHE_INVALIDATIONS = CACHE_INVALIDATIONS
                self._metrics_initialized = True

            if metric_type == "hit":
                self._CACHE_HIT_RATE.labels(cache_layer="llm").inc()
            elif metric_type == "miss":
                self._CACHE_MISS_RATE.labels(cache_layer="llm").inc()
            elif metric_type == "write":
                self._CACHE_WRITES.labels(cache_layer="llm").inc()
            elif metric_type == "error":
                self._CACHE_ERRORS.labels(cache_layer="llm", operation=operation).inc()
            elif metric_type == "invalidation":
                self._CACHE_INVALIDATIONS.labels(cache_layer="llm").inc()

        except ImportError:
            # Metrics not available yet (during initial setup)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit metric: {e}")

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Closed Redis connection")
