"""
Enhanced Anthropic Client for MVP

Extends base AnthropicClient with:
1. Multi-model support (Haiku/Sonnet/Opus)
2. Anthropic's Prompt Caching (32% cost savings)
3. Model-specific cost tracking
4. Task-based model selection

This is the primary client for MasterPlan MVP implementation.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, APIError

from src.llm.model_selector import ModelSelector, TaskType, TaskComplexity
from src.llm.prompt_cache_manager import PromptCacheManager, CacheableContext
from src.llm.anthropic_client import AnthropicClient  # Base client
from src.observability.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


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
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize enhanced client.

        Args:
            api_key: Anthropic API key
            use_opus: Enable Opus 4.1 (default: False for MVP)
            cost_optimization: Use Haiku for simple tasks (default: True)
            metrics_collector: Metrics collector instance
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

        logger.info(
            f"EnhancedAnthropicClient initialized: "
            f"use_opus={use_opus}, cost_optimization={cost_optimization}"
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
                # Use streaming mode to collect response incrementally
                full_text = ""
                cache_stats = {
                    "input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 0
                }

                with self.anthropic.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,  # ← With cache markers
                    messages=messages
                ) as stream:
                    for text in stream.text_stream:
                        full_text += text

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
            else:
                # Regular non-streaming mode for smaller requests
                response = self.anthropic.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,  # ← With cache markers
                    messages=messages
                )

                # Extract cache stats
                cache_stats = self.cache_manager.extract_cache_stats_from_response(response)

            # Calculate cost
            model_pricing = self.model_selector.get_model_pricing(model)
            cost_analysis = self.cache_manager.calculate_savings(
                uncached_input=cache_stats["input_tokens"] - cache_stats["cache_read_input_tokens"],
                cached_input=cache_stats["cache_read_input_tokens"],
                output_tokens=cache_stats["output_tokens"],
                model_pricing=model_pricing
            )

            # Build result
            result = {
                "content": response.content[0].text,
                "model": response.model,
                "usage": cache_stats,
                "cost_usd": cost_analysis["cost_with_cache"],
                "cost_analysis": cost_analysis,
                "stop_reason": response.stop_reason,
                "duration_seconds": time.time() - start_time
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
