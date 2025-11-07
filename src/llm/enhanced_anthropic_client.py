"""
Enhanced Anthropic Client for MVP

Extends base AnthropicClient with:
1. Multi-model support (Haiku/Sonnet/Opus)
2. Anthropic's Prompt Caching (32% cost savings)
3. Model-specific cost tracking
4. Task-based model selection

This is the primary client for MasterPlan MVP implementation.
"""

import asyncio
import logging
import time
import json
from uuid import UUID
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, APIError

from src.llm.model_selector import ModelSelector, TaskType, TaskComplexity
from src.llm.prompt_cache_manager import PromptCacheManager, CacheableContext
from src.llm.anthropic_client import AnthropicClient  # Base client
from src.observability.metrics_collector import MetricsCollector

# Import MGE V2 caching
from src.mge.v2.caching import LLMPromptCache, RequestBatcher

logger = logging.getLogger(__name__)


def json_serializable(obj):
    """Helper to serialize non-JSON types like UUID."""
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _perform_streaming_sync(anthropic_client, model: str, max_tokens: int, temperature: float, system, messages) -> Dict[str, Any]:
    """
    Synchronous streaming helper function.

    This function performs the actual streaming operation synchronously.
    It's designed to be called via asyncio.to_thread() to avoid blocking
    the async event loop during long-running streaming operations.

    Args:
        anthropic_client: Anthropic client instance
        model: Model to use
        max_tokens: Maximum output tokens
        temperature: Sampling temperature
        system: System prompt with cache markers
        messages: Message list

    Returns:
        Dict with streaming results and cache stats
    """
    full_text = ""
    cache_stats = {
        "input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "output_tokens": 0
    }
    chunk_buffer = []
    checkpoint_intervals = 500
    last_checkpoint_pos = 0
    chunk_count = 0

    with anthropic_client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            chunk_buffer.append(text)
            chunk_count += 1

            # PHASE 2: Log chunk progress
            if chunk_count % 50 == 0:
                logger.debug(
                    f"Streaming progress: {len(full_text)} chars, "
                    f"{chunk_count} chunks, "
                    f"Last chunk: {len(text)} chars"
                )

            # PHASE 2: Detect content structure (JSON boundaries)
            if len(full_text) - last_checkpoint_pos >= checkpoint_intervals:
                checkpoint_data = {
                    "position": len(full_text),
                    "chunks_received": chunk_count,
                    "timestamp": time.time(),
                    "content_sample": full_text[max(0, len(full_text)-100):]
                }
                logger.debug(f"Checkpoint reached: {checkpoint_data}")
                last_checkpoint_pos = len(full_text)

        # Get final message with usage stats
        final_message = stream.get_final_message()
        cache_stats["input_tokens"] = final_message.usage.input_tokens
        cache_stats["cache_read_input_tokens"] = getattr(final_message.usage, "cache_read_input_tokens", 0)
        cache_stats["cache_creation_input_tokens"] = getattr(final_message.usage, "cache_creation_input_tokens", 0)
        cache_stats["output_tokens"] = final_message.usage.output_tokens

        # Create response-like object for compatibility
        class StreamResponse:
            def __init__(self, text, model, usage, stop_reason):
                self.content = [type('obj', (object,), {'text': text})]
                self.model = model
                self.usage = usage
                self.stop_reason = stop_reason

        response = StreamResponse(
            text=full_text,
            model=final_message.model,
            usage=final_message.usage,
            stop_reason=final_message.stop_reason
        )

    return {
        "response": response,
        "cache_stats": cache_stats,
        "full_text": full_text,
        "chunk_count": chunk_count,
        "chunk_buffer": chunk_buffer
    }


class EnhancedAnthropicClient:
    """
    Enhanced Anthropic client for MVP with multi-model and prompt caching.

    Usage:
        client = EnhancedAnthropicClient()

        # Simple generation (auto-selects model)
        response = await client.generate_with_caching(
            task_type="task_execution",
            complexity="medium",
            cacheable_context={
                "system_prompt": "You are...",
                "discovery_doc": {...},
                "rag_examples": [...]
            },
            variable_prompt="Create a User API endpoint"
        )

        # Advanced: Manual model selection
        response = await client.generate(
            model="claude-haiku-4-5-20251015",
            messages=[...],
            system=[...]
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_opus: bool = False,  # MVP: disabled
        cost_optimization: bool = True,  # MVP: enabled (use Haiku)
        metrics_collector: Optional[MetricsCollector] = None,
        enable_v2_caching: bool = True,  # NEW: Enable MGE V2 caching
        enable_v2_batching: bool = False,  # NEW: Enable MGE V2 request batching (disabled by default)
        redis_url: str = "redis://redis:6379"  # Redis URL for V2 caching (Docker service name)
    ):
        """
        Initialize enhanced client.

        Args:
            api_key: Anthropic API key
            use_opus: Enable Opus 4.1 (default: False for MVP)
            cost_optimization: Use Haiku for simple tasks (default: True)
            metrics_collector: Metrics collector instance
            enable_v2_caching: Enable MGE V2 LLM response caching (default: True)
            enable_v2_batching: Enable MGE V2 request batching (default: False)
            redis_url: Redis connection URL for V2 caching
        """
        # Initialize base client (for retry/circuit breaker)
        self.base_client = AnthropicClient(
            api_key=api_key,
            metrics_collector=metrics_collector
        )

        # Initialize direct Anthropic client (for prompt caching support)
        self.anthropic = Anthropic(api_key=api_key or self.base_client.api_key)

        # Initialize model selector
        self.model_selector = ModelSelector(
            use_opus=use_opus,
            cost_optimization=cost_optimization
        )

        # Initialize prompt cache manager
        self.cache_manager = PromptCacheManager()

        # Metrics
        self.metrics = metrics_collector if metrics_collector else MetricsCollector()

        # NEW: Initialize MGE V2 caching components
        self.enable_v2_caching = enable_v2_caching
        self.enable_v2_batching = enable_v2_batching

        if self.enable_v2_caching:
            self.llm_cache = LLMPromptCache(redis_url=redis_url)
            logger.info("MGE V2 LLM response caching enabled")
        else:
            self.llm_cache = None

        if self.enable_v2_batching:
            self.request_batcher = RequestBatcher(
                llm_client=self,  # Pass self as client
                max_batch_size=5,
                batch_window_ms=500
            )
            logger.info("MGE V2 request batching enabled")
        else:
            self.request_batcher = None

        logger.info(
            f"EnhancedAnthropicClient initialized: "
            f"use_opus={use_opus}, cost_optimization={cost_optimization}, "
            f"v2_caching={enable_v2_caching}, v2_batching={enable_v2_batching}"
        )

    async def generate_with_caching(
        self,
        task_type: str,
        complexity: str,
        cacheable_context: Dict[str, Any],
        variable_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate completion with prompt caching and auto model selection.

        This is the PRIMARY method for MVP.

        With MGE V2 caching enabled:
        1. Checks LLMPromptCache for cached responses (24h TTL)
        2. On cache hit: Returns cached response immediately
        3. On cache miss: Calls Anthropic API → caches result → returns

        Args:
            task_type: Type of task (discovery, task_execution, etc.)
            complexity: Task complexity (low, medium, high)
            cacheable_context: Dict with system_prompt, discovery_doc, rag_examples, etc.
            variable_prompt: Variable prompt for this specific task
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            force_model: Force specific model (overrides selection)

        Returns:
            Dict with content, usage, cost, etc.
        """
        start_time = time.time()

        # Select model
        model = self.model_selector.select_model(
            task_type=task_type,
            complexity=complexity,
            force_model=force_model
        )

        # NEW: Check MGE V2 LLM cache BEFORE building prompt
        # Build full prompt for cache key generation
        full_prompt = self._build_full_prompt(cacheable_context, variable_prompt)

        if self.enable_v2_caching and self.llm_cache:
            cached_response = await self.llm_cache.get(
                prompt=full_prompt,
                model=model,
                temperature=temperature
            )

            if cached_response:
                # Cache hit! Return cached response
                logger.info(
                    f"V2 cache HIT: Returning cached response "
                    f"(saved API call, age={(time.time() - cached_response.cached_at) / 3600:.1f}h)"
                )

                # Calculate cost savings (would have cost full price without cache)
                model_pricing = self.model_selector.get_model_pricing(model)
                estimated_input_tokens = cached_response.prompt_tokens
                estimated_output_tokens = cached_response.completion_tokens
                full_cost = (
                    (estimated_input_tokens / 1_000_000) * model_pricing["input"] +
                    (estimated_output_tokens / 1_000_000) * model_pricing["output"]
                )

                # Emit cost savings metric
                from src.mge.v2.caching.metrics import CACHE_COST_SAVINGS_USD
                CACHE_COST_SAVINGS_USD.labels(cache_layer="llm").inc(full_cost)

                # Return cached response in same format as API response
                return {
                    "content": cached_response.text,
                    "model": cached_response.model,
                    "usage": {
                        "input_tokens": cached_response.prompt_tokens,
                        "output_tokens": cached_response.completion_tokens,
                        "cache_read_input_tokens": 0  # Not applicable for V2 cache
                    },
                    "cost_usd": 0,  # Cached response = no cost
                    "cost_analysis": {
                        "cost_with_cache": 0,
                        "cost_without_cache": full_cost,
                        "savings": full_cost,
                        "savings_percent": 100
                    },
                    "stop_reason": "end_turn",  # Assume normal completion
                    "duration_seconds": time.time() - start_time,
                    "cached": True  # Flag to indicate cache hit
                }

        # Cache miss - continue with normal API call
        logger.info(
            "V2 cache MISS: Calling Anthropic API"
        )

        logger.info(
            f"Generating with caching: "
            f"task_type={task_type}, complexity={complexity}, model={model}"
        )

        # Build cacheable sections
        cacheable_sections = self.cache_manager.build_cacheable_context(
            system_prompt=cacheable_context.get("system_prompt"),
            discovery_doc=cacheable_context.get("discovery_doc"),
            rag_examples=cacheable_context.get("rag_examples"),
            db_schema=cacheable_context.get("db_schema"),
            project_structure=cacheable_context.get("project_structure")
        )

        # Format prompt with caching
        system, messages = self.cache_manager.format_prompt_with_caching(
            cacheable_context=cacheable_sections,
            variable_prompt=variable_prompt
        )

        # Log cache info
        total_cacheable = sum(s.estimated_tokens for s in cacheable_sections)
        logger.debug(f"Cacheable context: {total_cacheable} tokens across {len(cacheable_sections)} sections")

        try:
            # For large token requests or long-running operations, use streaming to avoid 10-minute timeout
            # Streaming is required for operations that may take >10 minutes
            # Force streaming for masterplan generation (can take >10 min even with fewer tokens)
            use_streaming = (
                max_tokens >= 8000 or  # Reduced threshold (safer)
                force_model and "streaming" in task_type.lower() or
                task_type == "masterplan_generation"  # Always stream for masterplan
            )

            if use_streaming:
                logger.info(f"Using streaming mode for {task_type} (max_tokens={max_tokens})")
                # FIX: Run streaming in thread pool to avoid blocking async event loop
                # The synchronous Anthropic streaming API blocks, so we run it in a separate
                # thread via asyncio.to_thread() to keep the event loop free for WebSocket,
                # other requests, and timeouts while streaming completes.
                try:
                    streaming_result = await asyncio.to_thread(
                        _perform_streaming_sync,
                        self.anthropic,
                        model,
                        max_tokens,
                        temperature,
                        system,
                        messages
                    )

                    response = streaming_result["response"]
                    cache_stats = streaming_result["cache_stats"]
                    full_text = streaming_result["full_text"]
                    chunk_count = streaming_result["chunk_count"]
                    chunk_buffer = streaming_result["chunk_buffer"]

                except Exception as stream_exception:
                    # Error Handling
                    logger.error(
                        f"Stream error during {task_type}: {type(stream_exception).__name__}: {str(stream_exception)}",
                        exc_info=True
                    )

                    # Check if we have partial content saved somewhere
                    partial_completion = False
                    full_text = ""
                    chunk_count = 0
                    chunk_buffer = []

                    logger.warning(
                        f"Streaming failed: {str(stream_exception)}. "
                        f"Attempting non-streaming fallback for {task_type}"
                    )

                    # Propagate to outer exception handler for non-streaming fallback
                    raise
            else:
                # Regular non-streaming mode for smaller requests
                logger.info(f"Using non-streaming mode for {task_type} (max_tokens={max_tokens})")
                response = self.anthropic.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,  # ← With cache markers
                    messages=messages
                )

                # Extract cache stats
                cache_stats = self.cache_manager.extract_cache_stats_from_response(response)

        except Exception as outer_exception:
            # PHASE 3: Non-streaming Fallback
            logger.warning(
                f"Streaming mode failed for {task_type}, attempting non-streaming fallback: "
                f"{type(outer_exception).__name__}"
            )

            try:
                logger.info(f"PHASE 3: Attempting non-streaming fallback for {task_type}")
                response = self.anthropic.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,  # ← With cache markers
                    messages=messages
                )

                # Extract cache stats
                cache_stats = self.cache_manager.extract_cache_stats_from_response(response)

                logger.info(
                    f"Non-streaming fallback succeeded for {task_type}: "
                    f"{len(response.content[0].text)} chars"
                )

            except Exception as fallback_exception:
                # Both streaming and non-streaming failed
                logger.error(
                    f"Both streaming and non-streaming failed for {task_type}: "
                    f"Streaming: {type(outer_exception).__name__}, "
                    f"Non-streaming: {type(fallback_exception).__name__}",
                    exc_info=True
                )
                raise

        # Process response and return (executed for BOTH successful try path and successful fallback)
        try:
            # Calculate cost
            model_pricing = self.model_selector.get_model_pricing(model)
            cost_analysis = self.cache_manager.calculate_savings(
                uncached_input=cache_stats["input_tokens"] - cache_stats["cache_read_input_tokens"],
                cached_input=cache_stats["cache_read_input_tokens"],
                output_tokens=cache_stats["output_tokens"],
                model_pricing=model_pricing
            )

            # NEW: Save response to V2 cache (async, no waiting)
            response_text = response.content[0].text
            if self.enable_v2_caching and self.llm_cache:
                # Save to cache (don't await - fire and forget for performance)
                import asyncio
                asyncio.create_task(
                    self.llm_cache.set(
                        prompt=full_prompt,
                        model=model,
                        temperature=temperature,
                        response_text=response_text,
                        prompt_tokens=cache_stats["input_tokens"],
                        completion_tokens=cache_stats["output_tokens"]
                    )
                )
                logger.debug("V2 cache: Saved response to cache")

            # Build result
            result = {
                "content": response_text,
                "model": response.model,
                "usage": cache_stats,
                "cost_usd": cost_analysis["cost_with_cache"],
                "cost_analysis": cost_analysis,
                "stop_reason": response.stop_reason,
                "duration_seconds": time.time() - start_time,
                "cached": False  # Flag to indicate new API call
            }

            # Metrics
            self._record_metrics(
                model=model,
                task_type=task_type,
                complexity=complexity,
                cache_stats=cache_stats,
                cost_usd=cost_analysis["cost_with_cache"],
                duration=result["duration_seconds"],
                status="success"
            )

            logger.info(
                f"Generation complete: "
                f"input={cache_stats['input_tokens']}, "
                f"cached={cache_stats['cache_read_input_tokens']}, "
                f"output={cache_stats['output_tokens']}, "
                f"cost=${cost_analysis['cost_with_cache']:.4f}, "
                f"saved=${cost_analysis['savings']:.4f} ({cost_analysis['savings_percent']:.1f}%)"
            )

            return result

        except Exception as e:
            # Metrics: Error
            self._record_metrics(
                model=model,
                task_type=task_type,
                complexity=complexity,
                cache_stats={},
                cost_usd=0,
                duration=time.time() - start_time,
                status="error"
            )

            logger.error(f"Generation failed: {str(e)}")
            raise RuntimeError(f"Enhanced Anthropic API error: {str(e)}") from e

    async def generate_simple(
        self,
        prompt: str,
        task_type: str = "task_execution",
        complexity: str = "medium",
        max_tokens: int = 8000,
        temperature: float = 0.7
    ) -> str:
        """
        Simple generation without prompt caching.

        Useful for quick/one-off requests.

        Args:
            prompt: User prompt
            task_type: Task type for model selection
            complexity: Task complexity
            max_tokens: Maximum output tokens
            temperature: Sampling temperature

        Returns:
            Generated text content
        """
        # Select model
        model = self.model_selector.select_model(
            task_type=task_type,
            complexity=complexity
        )

        # Use base client (has retry/circuit breaker)
        response = self.base_client.generate(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        return response["content"]

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 8000
    ):
        """
        Direct generation method for RequestBatcher compatibility.

        Args:
            prompt: User prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            Object with .text attribute containing response
        """
        # Call Anthropic API directly
        response = self.anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )

        # Return object with .text attribute (RequestBatcher expects this)
        class SimpleResponse:
            def __init__(self, text):
                self.text = text

        return SimpleResponse(text=response.content[0].text)

    def get_model_for_task(
        self,
        task_type: str,
        complexity: str
    ) -> str:
        """
        Get model that would be selected for task.

        Useful for planning/cost estimation.

        Args:
            task_type: Task type
            complexity: Task complexity

        Returns:
            Model name
        """
        return self.model_selector.select_model(
            task_type=task_type,
            complexity=complexity
        )

    def estimate_cost(
        self,
        task_type: str,
        complexity: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0
    ) -> Dict[str, float]:
        """
        Estimate cost for task.

        Args:
            task_type: Task type
            complexity: Complexity
            input_tokens: Input tokens
            output_tokens: Output tokens
            cached_tokens: Cached tokens (if using prompt caching)

        Returns:
            Dict with cost breakdown
        """
        model = self.model_selector.select_model(task_type, complexity)
        model_pricing = self.model_selector.get_model_pricing(model)

        cost_analysis = self.cache_manager.calculate_savings(
            uncached_input=input_tokens - cached_tokens,
            cached_input=cached_tokens,
            output_tokens=output_tokens,
            model_pricing=model_pricing
        )

        return {
            "model": model,
            **cost_analysis
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get prompt cache performance stats.

        Returns:
            Dict with cache_writes, cache_reads, hit_rate, etc.
        """
        return self.cache_manager.get_cache_stats()

    def get_model_stats(self) -> Dict[str, Any]:
        """
        Get model selector configuration.

        Returns:
            Dict with use_opus, cost_optimization, available_models
        """
        return self.model_selector.get_stats()

    def _record_metrics(
        self,
        model: str,
        task_type: str,
        complexity: str,
        cache_stats: Dict,
        cost_usd: float,
        duration: float,
        status: str
    ):
        """Record metrics for request"""
        # Request counter
        self.metrics.increment_counter(
            "enhanced_llm_requests_total",
            labels={
                "model": model,
                "task_type": task_type,
                "complexity": complexity,
                "status": status
            },
            help_text="Total enhanced LLM requests"
        )

        # Duration
        self.metrics.observe_histogram(
            "enhanced_llm_duration_seconds",
            duration,
            labels={
                "model": model,
                "task_type": task_type
            },
            help_text="Enhanced LLM request duration"
        )

        # Cost
        if cost_usd > 0:
            self.metrics.observe_histogram(
                "enhanced_llm_cost_usd",
                cost_usd,
                labels={
                    "model": model,
                    "task_type": task_type
                },
                help_text="Enhanced LLM cost in USD"
            )

        # Token usage
        if cache_stats:
            self.metrics.increment_counter(
                "enhanced_llm_tokens_total",
                value=cache_stats.get("input_tokens", 0),
                labels={"model": model, "type": "input"},
                help_text="Total input tokens"
            )

            self.metrics.increment_counter(
                "enhanced_llm_tokens_total",
                value=cache_stats.get("output_tokens", 0),
                labels={"model": model, "type": "output"},
                help_text="Total output tokens"
            )

            # Cache metrics
            if cache_stats.get("cache_read_input_tokens", 0) > 0:
                self.metrics.increment_counter(
                    "enhanced_llm_cache_hits_total",
                    labels={"model": model},
                    help_text="Prompt cache hits"
                )

                self.metrics.increment_counter(
                    "enhanced_llm_cached_tokens_total",
                    value=cache_stats["cache_read_input_tokens"],
                    labels={"model": model},
                    help_text="Total cached tokens read"
                )

    def _build_full_prompt(
        self,
        cacheable_context: Dict[str, Any],
        variable_prompt: str
    ) -> str:
        """
        Build full prompt string for V2 cache key generation.

        Combines system prompt and variable prompt into single string for hashing.

        Args:
            cacheable_context: Dict with system_prompt, discovery_doc, etc.
            variable_prompt: Variable prompt

        Returns:
            Full prompt string
        """
        import json

        parts = []

        # System prompt
        if "system_prompt" in cacheable_context:
            parts.append(f"SYSTEM:\n{cacheable_context['system_prompt']}")

        # Discovery doc
        if "discovery_doc" in cacheable_context:
            parts.append(f"DISCOVERY:\n{json.dumps(cacheable_context['discovery_doc'], sort_keys=True, default=json_serializable)}")

        # RAG examples
        if "rag_examples" in cacheable_context:
            parts.append(f"RAG:\n{json.dumps(cacheable_context['rag_examples'], sort_keys=True, default=json_serializable)}")

        # DB schema
        if "db_schema" in cacheable_context:
            parts.append(f"SCHEMA:\n{json.dumps(cacheable_context['db_schema'], sort_keys=True, default=json_serializable)}")

        # Project structure
        if "project_structure" in cacheable_context:
            parts.append(f"PROJECT:\n{json.dumps(cacheable_context['project_structure'], sort_keys=True, default=json_serializable)}")

        # Variable prompt
        parts.append(f"PROMPT:\n{variable_prompt}")

        return "\n\n".join(parts)
