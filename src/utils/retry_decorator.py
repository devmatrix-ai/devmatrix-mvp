"""
Retry Decorator with Exponential Backoff

Provides configurable retry logic for async functions with:
- Configurable max retries
- Exponential backoff strategy
- Customizable backoff factor and max delay
- Exception filtering
- Logging and metrics

@since Nov 4, 2025
@version 1.0
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, Set, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Set[Type[Exception]]] = None,
    ):
        """
        Initialize retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 60.0)
            backoff_factor: Multiply delay by this after each retry (default: 2.0)
            jitter: Add random jitter to delays (default: True)
            retryable_exceptions: Set of exception types to retry on.
                                If None, retries on all exceptions
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or {Exception}
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number with exponential backoff"""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            jitter_amount = random.uniform(0, delay * 0.1)
            delay += jitter_amount
        
        return delay


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Set[Type[Exception]]] = None,
):
    """
    Decorator for retrying async functions with exponential backoff
    
    Usage:
    ```python
    @retry(max_retries=3, initial_delay=1.0)
    async def generate_masterplan(user_id: str):
        # LLM call that might fail temporarily
        return await llm.generate(...)
    ```
    
    Args:
        max_retries: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Max delay cap in seconds
        backoff_factor: Exponential backoff multiplier
        jitter: Add random jitter to delays
        retryable_exceptions: Exception types to retry on
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    logger.debug(f"[{func.__name__}] Attempt {attempt + 1}/{config.max_retries + 1}")
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"[{func.__name__}] Succeeded after {attempt} retries"
                        )
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception type is retryable
                    is_retryable = any(
                        isinstance(e, exc_type)
                        for exc_type in config.retryable_exceptions
                    )
                    
                    if not is_retryable:
                        logger.warning(
                            f"[{func.__name__}] Non-retryable exception: {type(e).__name__}: {str(e)}"
                        )
                        raise
                    
                    # Check if we should retry
                    if attempt >= config.max_retries:
                        logger.error(
                            f"[{func.__name__}] Max retries ({config.max_retries}) exceeded. Last error: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay for next retry
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt + 1} failed ({type(e).__name__}): {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            
            raise RuntimeError(f"[{func.__name__}] Unexpected retry exhaustion")
        
        return wrapper
    
    return decorator


def create_retryable_config(
    service_type: str,
) -> RetryConfig:
    """
    Create pre-configured RetryConfig for specific service types
    
    Args:
        service_type: Type of service ('llm', 'database', 'api', 'general')
    
    Returns:
        RetryConfig optimized for the service type
    """
    configs = {
        'llm': RetryConfig(
            max_retries=3,
            initial_delay=2.0,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter=True,
            retryable_exceptions={
                TimeoutError,
                ConnectionError,
                IOError,
            },
        ),
        'database': RetryConfig(
            max_retries=2,
            initial_delay=0.5,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=True,
            retryable_exceptions={
                ConnectionError,
                IOError,
                TimeoutError,
            },
        ),
        'api': RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter=True,
            retryable_exceptions={
                ConnectionError,
                TimeoutError,
                IOError,
            },
        ),
        'general': RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=True,
        ),
    }
    
    return configs.get(service_type, configs['general'])
