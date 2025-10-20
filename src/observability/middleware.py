"""
FastAPI Middleware for Metrics Collection

Automatically instruments all HTTP requests with metrics:
- Request count by endpoint/method/status
- Request latency histogram
- Error rates and status code distribution
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .metrics_collector import MetricsCollector
from .structured_logger import StructuredLogger


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic HTTP metrics collection.

    Collects:
    - http_requests_total: Counter of requests by endpoint/method/status
    - http_request_duration_seconds: Histogram of request latencies
    - http_requests_in_progress: Gauge of concurrent requests
    """

    def __init__(self, app: ASGIApp, metrics_collector: MetricsCollector):
        """
        Initialize metrics middleware.

        Args:
            app: ASGI application
            metrics_collector: Metrics collector instance
        """
        super().__init__(app)
        self.metrics = metrics_collector
        self.logger = StructuredLogger("metrics.middleware")

        # Initialize in-progress gauge
        self.metrics.set_gauge(
            "http_requests_in_progress",
            0.0,
            help_text="Number of HTTP requests currently being processed"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Start timing
        start_time = time.time()

        # Track request method and path
        method = request.method
        path = self._normalize_path(request.url.path)

        # Increment in-progress requests
        self.metrics.set_gauge(
            "http_requests_in_progress",
            self.metrics.get_gauge("http_requests_in_progress") or 0 + 1
        )

        # Process request
        status_code = 500  # Default to error if exception occurs
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as exc:
            self.logger.error(
                f"Request failed: {method} {path}",
                extra={"error": str(exc)}
            )
            raise

        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Decrement in-progress requests
            current = self.metrics.get_gauge("http_requests_in_progress") or 1
            self.metrics.set_gauge("http_requests_in_progress", current - 1)

            # Record metrics
            labels = {
                "method": method,
                "endpoint": path,
                "status": str(status_code)
            }

            # Increment request counter
            self.metrics.increment_counter(
                "http_requests_total",
                labels=labels,
                help_text="Total HTTP requests"
            )

            # Record request duration
            self.metrics.observe_histogram(
                "http_request_duration_seconds",
                duration,
                labels=labels,
                help_text="HTTP request duration in seconds"
            )

            # Track error rates
            if status_code >= 400:
                error_type = "client_error" if status_code < 500 else "server_error"
                self.metrics.increment_counter(
                    "http_errors_total",
                    labels={
                        "method": method,
                        "endpoint": path,
                        "status": str(status_code),
                        "error_type": error_type
                    },
                    help_text="Total HTTP errors"
                )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize URL path for metrics labels.

        Converts dynamic path parameters to template format to avoid
        high cardinality in metrics labels.

        Args:
            path: Raw URL path

        Returns:
            Normalized path template
        """
        # Remove trailing slash
        path = path.rstrip('/')

        # Skip normalization for static assets and root
        if not path or path.startswith('/static') or path.startswith('/assets'):
            return path or '/'

        # Common API path patterns
        parts = path.split('/')
        normalized = []

        for i, part in enumerate(parts):
            if not part:
                continue

            # Replace UUIDs and IDs with template
            if self._looks_like_id(part):
                normalized.append('{id}')
            else:
                normalized.append(part)

        return '/' + '/'.join(normalized)

    def _looks_like_id(self, part: str) -> bool:
        """
        Check if path part looks like an ID.

        Args:
            part: Path component

        Returns:
            True if looks like ID
        """
        # Check for UUID pattern
        if len(part) == 36 and part.count('-') == 4:
            return True

        # Check for numeric ID
        if part.isdigit():
            return True

        # Check for hex ID (MongoDB style)
        if len(part) == 24 and all(c in '0123456789abcdef' for c in part.lower()):
            return True

        return False
