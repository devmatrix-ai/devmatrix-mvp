"""
Anthropic Claude Client

Wrapper for Anthropic API with retry logic, error handling, and caching.
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from dotenv import load_dotenv

from src.error_handling import RetryStrategy, RetryConfig, CircuitBreaker, CircuitBreakerConfig
from src.observability.metrics_collector import MetricsCollector
from src.config.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_MODEL,
    DEFAULT_MAX_RETRIES,
    RETRY_INITIAL_DELAY,
    RETRY_MAX_DELAY,
    RETRY_EXPONENTIAL_BASE,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    CIRCUIT_BREAKER_TIMEOUT,
    LLM_CACHE_TTL,
    COST_PER_1M_INPUT_TOKENS_USD,
    COST_PER_1M_OUTPUT_TOKENS_USD,
    USD_TO_EUR_RATE,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AnthropicClient:
    """
    Anthropic Claude API client.

    Usage:
        client = AnthropicClient()
        response = client.generate(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are a helpful assistant"
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        enable_cache: bool = True,
        cache_manager = None,
        enable_retry: bool = True,
        enable_circuit_breaker: bool = True,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model to use (default: claude-haiku-4-5-20251001)
            enable_cache: Enable response caching (default: True)
            cache_manager: CacheManager instance (creates new if None)
            enable_retry: Enable retry with exponential backoff (default: True)
            enable_circuit_breaker: Enable circuit breaker protection (default: True)
            metrics_collector: MetricsCollector instance (creates new if None)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. "
                "Set it in .env file or pass as argument."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.enable_cache = enable_cache

        # Use provided metrics collector or create new one
        self.metrics = metrics_collector if metrics_collector is not None else MetricsCollector()

        # Initialize cache manager if caching is enabled
        if self.enable_cache:
            if cache_manager is None:
                try:
                    from src.performance.cache_manager import CacheManager
                    self.cache_manager = CacheManager()
                except Exception as e:
                    logger.warning(f"Failed to initialize cache manager: {e}")
                    self.enable_cache = False
                    self.cache_manager = None
            else:
                self.cache_manager = cache_manager
        else:
            self.cache_manager = None

        # Initialize retry strategy
        self.enable_retry = enable_retry
        if self.enable_retry:
            self.retry_strategy = RetryStrategy(
                RetryConfig(
                    max_attempts=DEFAULT_MAX_RETRIES,
                    initial_delay=RETRY_INITIAL_DELAY,
                    max_delay=RETRY_MAX_DELAY,
                    exponential_base=RETRY_EXPONENTIAL_BASE,
                    jitter=True,
                    retryable_exceptions=(
                        APIConnectionError,
                        RateLimitError,
                        TimeoutError,
                    ),
                )
            )
        else:
            self.retry_strategy = None

        # Initialize circuit breaker
        self.enable_circuit_breaker = enable_circuit_breaker
        if self.enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                CircuitBreakerConfig(
                    failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    success_threshold=CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
                    timeout=CIRCUIT_BREAKER_TIMEOUT,
                    expected_exception=APIError,
                )
            )
        else:
            self.circuit_breaker = None

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion from Claude with caching support.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            use_cache: Use cached response if available (default: True)
            **kwargs: Additional API parameters

        Returns:
            Dictionary with response data including content and usage
        """
        start_time = time.time()
        cache_hit = False

        # Try cache first if enabled
        if self.enable_cache and use_cache and self.cache_manager:
            # Construct prompt for caching
            prompt = "\n".join([m.get("content", "") for m in messages])
            cached_response = self.cache_manager.get_cached_llm_response(
                prompt=prompt,
                system=system
            )
            if cached_response:
                # Metrics: Cache hit
                self.metrics.increment_counter(
                    "llm_cache_hits_total",
                    labels={"model": self.model},
                    help_text="Total LLM cache hits"
                )
                # Add cache hit indicator
                cached_response["cached"] = True
                cache_hit = True

                # Still record request metrics for cached responses
                duration = time.time() - start_time
                self.metrics.observe_histogram(
                    "llm_request_duration_seconds",
                    duration,
                    labels={"model": self.model, "cached": "true"},
                    help_text="LLM request duration"
                )

                return cached_response

        # Metrics: Cache miss
        if self.enable_cache and use_cache:
            self.metrics.increment_counter(
                "llm_cache_misses_total",
                labels={"model": self.model},
                help_text="Total LLM cache misses"
            )

        # Define API call function for retry/circuit breaker
        def _make_api_call():
            return self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
                **kwargs
            )

        try:
            # Apply circuit breaker if enabled
            if self.enable_circuit_breaker and self.circuit_breaker:
                if self.enable_retry and self.retry_strategy:
                    # Both retry and circuit breaker
                    response = self.circuit_breaker.call(
                        self.retry_strategy.execute,
                        _make_api_call
                    )
                else:
                    # Circuit breaker only
                    response = self.circuit_breaker.call(_make_api_call)
            elif self.enable_retry and self.retry_strategy:
                # Retry only
                response = self.retry_strategy.execute(_make_api_call)
            else:
                # No protection
                response = _make_api_call()

            result = {
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
                "cached": False
            }

            # Metrics: Request completed
            duration = time.time() - start_time
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            self.metrics.increment_counter(
                "llm_requests_total",
                labels={"model": self.model, "status": "success"},
                help_text="Total LLM requests"
            )

            self.metrics.observe_histogram(
                "llm_request_duration_seconds",
                duration,
                labels={"model": self.model, "cached": "false"},
                help_text="LLM request duration"
            )

            self.metrics.increment_counter(
                "llm_tokens_total",
                value=input_tokens,
                labels={"model": self.model, "type": "input"},
                help_text="Total LLM tokens"
            )

            self.metrics.increment_counter(
                "llm_tokens_total",
                value=output_tokens,
                labels={"model": self.model, "type": "output"},
                help_text="Total LLM tokens"
            )

            # Calculate and record cost
            cost_eur = self.calculate_cost(input_tokens, output_tokens)
            self.metrics.observe_histogram(
                "llm_cost_eur",
                cost_eur,
                labels={"model": self.model},
                help_text="LLM API cost in EUR"
            )

            # Cache response if enabled
            if self.enable_cache and use_cache and self.cache_manager:
                prompt = "\n".join([m.get("content", "") for m in messages])
                self.cache_manager.cache_llm_response(
                    prompt=prompt,
                    system=system,
                    response=result,
                    ttl=LLM_CACHE_TTL
                )

            return result

        except Exception as e:
            # Metrics: Request failed
            self.metrics.increment_counter(
                "llm_requests_total",
                labels={"model": self.model, "status": "error"},
                help_text="Total LLM requests"
            )

            error_type = type(e).__name__
            self.metrics.increment_counter(
                "llm_errors_total",
                labels={"model": self.model, "error_type": error_type},
                help_text="Total LLM errors"
            )

            logger.error(f"Anthropic API error after all retries: {str(e)}")
            raise RuntimeError(f"Anthropic API error: {str(e)}") from e

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> Dict[str, Any]:
        """
        Generate completion with tool use.

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            system: System prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Dictionary with response including tool calls if any
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
                tools=tools,
            )

            # Parse response for tool calls
            tool_calls = []
            text_content = ""

            for content_block in response.content:
                if content_block.type == "text":
                    text_content += content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    })

            return {
                "content": text_content,
                "tool_calls": tool_calls,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
            }

        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}") from e

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in EUR for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in EUR
        """
        # Claude 3.5 Sonnet pricing (as of 2024)
        input_cost_eur = (input_tokens / 1_000_000) * COST_PER_1M_INPUT_TOKENS_USD * USD_TO_EUR_RATE
        output_cost_eur = (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT_TOKENS_USD * USD_TO_EUR_RATE

        return input_cost_eur + output_cost_eur
