"""
Anthropic Claude Client

Wrapper for Anthropic API with retry logic, error handling, and caching.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from dotenv import load_dotenv

from src.error_handling import RetryStrategy, RetryConfig, CircuitBreaker, CircuitBreakerConfig

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
        model: str = "claude-3-5-sonnet-20241022",
        enable_cache: bool = True,
        cache_manager = None,
        enable_retry: bool = True,
        enable_circuit_breaker: bool = True,
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model to use (default: claude-3-5-sonnet-20241022)
            enable_cache: Enable response caching (default: True)
            cache_manager: CacheManager instance (creates new if None)
            enable_retry: Enable retry with exponential backoff (default: True)
            enable_circuit_breaker: Enable circuit breaker protection (default: True)
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
                    max_attempts=3,
                    initial_delay=1.0,
                    max_delay=30.0,
                    exponential_base=2.0,
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
                    failure_threshold=5,
                    success_threshold=2,
                    timeout=60.0,
                    expected_exception=APIError,
                )
            )
        else:
            self.circuit_breaker = None

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
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
        # Try cache first if enabled
        if self.enable_cache and use_cache and self.cache_manager:
            # Construct prompt for caching
            prompt = "\n".join([m.get("content", "") for m in messages])
            cached_response = self.cache_manager.get_cached_llm_response(
                prompt=prompt,
                system=system
            )
            if cached_response:
                # Add cache hit indicator
                cached_response["cached"] = True
                return cached_response

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

            # Cache response if enabled
            if self.enable_cache and use_cache and self.cache_manager:
                prompt = "\n".join([m.get("content", "") for m in messages])
                self.cache_manager.cache_llm_response(
                    prompt=prompt,
                    system=system,
                    response=result,
                    ttl=3600  # Cache for 1 hour
                )

            return result

        except Exception as e:
            logger.error(f"Anthropic API error after all retries: {str(e)}")
            raise RuntimeError(f"Anthropic API error: {str(e)}") from e

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
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
        # Input: $3 per 1M tokens
        # Output: $15 per 1M tokens
        input_cost_eur = (input_tokens / 1_000_000) * 3 * 0.92  # USD to EUR ~0.92
        output_cost_eur = (output_tokens / 1_000_000) * 15 * 0.92

        return input_cost_eur + output_cost_eur
