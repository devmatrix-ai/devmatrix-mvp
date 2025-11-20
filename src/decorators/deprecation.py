"""
Deprecation decorator - Stub implementation

Temporary stub to allow application startup.
"""
import warnings
from functools import wraps
from typing import Callable, Any


def deprecated(message: str = "") -> Callable:
    """
    Decorator to mark functions as deprecated.

    Args:
        message: Optional deprecation message

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warning_msg = f"{func.__name__} is deprecated"
            if message:
                warning_msg += f": {message}"
            warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def deprecated_class(message: str = "", alternative: str = "") -> Callable:
    """
    Decorator to mark classes as deprecated.

    Args:
        message: Optional deprecation message
        alternative: Optional alternative class to use

    Returns:
        Decorated class
    """
    def decorator(cls: type) -> type:
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, *args: Any, **kwargs: Any) -> None:
            warning_msg = f"{cls.__name__} is deprecated"
            if message:
                warning_msg += f": {message}"
            if alternative:
                warning_msg += f". Use {alternative} instead"
            warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls
    return decorator
