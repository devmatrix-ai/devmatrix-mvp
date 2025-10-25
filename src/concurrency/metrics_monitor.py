"""
MetricsMonitor - System metrics monitoring

Monitors Prometheus metrics for CPU, memory, API latency, and error rates.
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage_percent: float
    memory_usage_percent: float
    api_latency_p95_ms: float
    api_error_rate: float
    active_requests: int
    timestamp: datetime


class MetricsMonitor:
    """
    Monitor system metrics from Prometheus

    Features:
    - CPU/memory usage tracking
    - API latency monitoring (p95)
    - Error rate tracking
    - Active request counting
    - Trend analysis
    """

    def __init__(
        self,
        prometheus_url: Optional[str] = None,
        scrape_interval_seconds: int = 10
    ):
        """
        Initialize MetricsMonitor

        Args:
            prometheus_url: Prometheus server URL (optional)
            scrape_interval_seconds: Metrics scraping interval
        """
        self.prometheus_url = prometheus_url or "http://localhost:9090"
        self.scrape_interval = scrape_interval_seconds

        # Metrics history for trend analysis
        self._metrics_history: list[SystemMetrics] = []
        self._max_history_size = 100  # Keep last 100 samples

    async def get_current_metrics(self) -> SystemMetrics:
        """
        Get current system metrics

        Returns:
            SystemMetrics with current values
        """
        # TODO: Implement Prometheus query integration
        # For now, return mock metrics

        metrics = SystemMetrics(
            cpu_usage_percent=45.0,
            memory_usage_percent=60.0,
            api_latency_p95_ms=250.0,
            api_error_rate=0.02,  # 2%
            active_requests=15,
            timestamp=datetime.utcnow()
        )

        # Add to history
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history.pop(0)

        logger.debug(
            f"Current metrics: CPU={metrics.cpu_usage_percent}%, "
            f"Memory={metrics.memory_usage_percent}%, "
            f"Latency p95={metrics.api_latency_p95_ms}ms, "
            f"Error rate={metrics.api_error_rate:.2%}"
        )

        return metrics

    def get_metrics_trend(self, window_minutes: int = 5) -> Dict[str, float]:
        """
        Get metrics trend over time window

        Args:
            window_minutes: Time window in minutes

        Returns:
            Dict with trend data: {
                'cpu_trend': float,  # -1 to 1 (decreasing to increasing)
                'memory_trend': float,
                'latency_trend': float,
                'error_rate_trend': float
            }
        """
        if len(self._metrics_history) < 2:
            return {
                'cpu_trend': 0.0,
                'memory_trend': 0.0,
                'latency_trend': 0.0,
                'error_rate_trend': 0.0
            }

        # Filter metrics within window
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_metrics = [
            m for m in self._metrics_history
            if m.timestamp >= cutoff_time
        ]

        if len(recent_metrics) < 2:
            recent_metrics = self._metrics_history[-10:]  # Use last 10 samples

        # Calculate trends (simple linear trend)
        def calculate_trend(values: list[float]) -> float:
            if len(values) < 2:
                return 0.0

            # Simple slope calculation
            n = len(values)
            x = list(range(n))
            y = values

            x_mean = sum(x) / n
            y_mean = sum(y) / n

            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                return 0.0

            slope = numerator / denominator

            # Normalize to -1 to 1
            return max(-1.0, min(1.0, slope / 10))

        cpu_values = [m.cpu_usage_percent for m in recent_metrics]
        memory_values = [m.memory_usage_percent for m in recent_metrics]
        latency_values = [m.api_latency_p95_ms for m in recent_metrics]
        error_values = [m.api_error_rate * 100 for m in recent_metrics]

        return {
            'cpu_trend': calculate_trend(cpu_values),
            'memory_trend': calculate_trend(memory_values),
            'latency_trend': calculate_trend(latency_values),
            'error_rate_trend': calculate_trend(error_values)
        }

    def is_system_healthy(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        latency_threshold_ms: float = 1000.0,
        error_rate_threshold: float = 0.05  # 5%
    ) -> Dict[str, bool]:
        """
        Check if system is healthy

        Args:
            cpu_threshold: CPU usage threshold (%)
            memory_threshold: Memory usage threshold (%)
            latency_threshold_ms: Latency p95 threshold (ms)
            error_rate_threshold: Error rate threshold (0-1)

        Returns:
            Dict with health checks: {
                'healthy': bool,
                'cpu_healthy': bool,
                'memory_healthy': bool,
                'latency_healthy': bool,
                'errors_healthy': bool
            }
        """
        if not self._metrics_history:
            return {
                'healthy': True,
                'cpu_healthy': True,
                'memory_healthy': True,
                'latency_healthy': True,
                'errors_healthy': True
            }

        current = self._metrics_history[-1]

        cpu_healthy = current.cpu_usage_percent < cpu_threshold
        memory_healthy = current.memory_usage_percent < memory_threshold
        latency_healthy = current.api_latency_p95_ms < latency_threshold_ms
        errors_healthy = current.api_error_rate < error_rate_threshold

        return {
            'healthy': all([cpu_healthy, memory_healthy, latency_healthy, errors_healthy]),
            'cpu_healthy': cpu_healthy,
            'memory_healthy': memory_healthy,
            'latency_healthy': latency_healthy,
            'errors_healthy': errors_healthy
        }

    def get_load_factor(self) -> float:
        """
        Get current system load factor (0.0 to 1.0)

        Returns:
            Load factor: 0.0 = idle, 1.0 = at capacity
        """
        if not self._metrics_history:
            return 0.0

        current = self._metrics_history[-1]

        # Weighted average of metrics
        cpu_factor = current.cpu_usage_percent / 100
        memory_factor = current.memory_usage_percent / 100
        latency_factor = min(1.0, current.api_latency_p95_ms / 1000)  # Cap at 1000ms
        error_factor = min(1.0, current.api_error_rate / 0.1)  # Cap at 10%

        # Weighted combination
        load_factor = (
            0.3 * cpu_factor +
            0.3 * memory_factor +
            0.3 * latency_factor +
            0.1 * error_factor
        )

        return min(1.0, max(0.0, load_factor))
