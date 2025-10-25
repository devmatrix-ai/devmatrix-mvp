"""
LimitAdjuster - Adaptive concurrency limit adjustment

Adjusts concurrency limits based on system metrics using AIMD algorithm.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

from .metrics_monitor import MetricsMonitor

logger = logging.getLogger(__name__)


class LimitAdjuster:
    """
    Adaptive concurrency limit adjustment using AIMD

    AIMD (Additive Increase Multiplicative Decrease):
    - Increase limit gradually when system is healthy
    - Decrease limit sharply when system is under stress

    Features:
    - CPU/memory/latency-based adjustments
    - Configurable min/max limits
    - Smooth transitions (avoid thrashing)
    - Backoff on repeated failures
    """

    def __init__(
        self,
        metrics_monitor: MetricsMonitor,
        initial_limit: int = 100,
        min_limit: int = 10,
        max_limit: int = 500,
        increase_step: int = 5,
        decrease_factor: float = 0.75
    ):
        """
        Initialize LimitAdjuster

        Args:
            metrics_monitor: MetricsMonitor for system metrics
            initial_limit: Starting concurrency limit
            min_limit: Minimum concurrency limit
            max_limit: Maximum concurrency limit
            increase_step: Amount to increase on healthy system
            decrease_factor: Multiplier to decrease on stress (0.75 = 25% decrease)
        """
        self.metrics_monitor = metrics_monitor
        self.current_limit = initial_limit
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.increase_step = increase_step
        self.decrease_factor = decrease_factor

        # State tracking
        self._last_adjustment = datetime.utcnow()
        self._adjustment_cooldown_seconds = 10  # Wait between adjustments
        self._consecutive_healthy_checks = 0
        self._consecutive_unhealthy_checks = 0

    async def adjust_limit(self) -> int:
        """
        Adjust concurrency limit based on current metrics

        Returns:
            New concurrency limit
        """
        # Check cooldown
        if (datetime.utcnow() - self._last_adjustment).total_seconds() < self._adjustment_cooldown_seconds:
            return self.current_limit

        # Get current metrics
        metrics = await self.metrics_monitor.get_current_metrics()
        health = self.metrics_monitor.is_system_healthy()

        previous_limit = self.current_limit

        if health['healthy']:
            # System is healthy - increase limit (AIMD additive increase)
            self._consecutive_healthy_checks += 1
            self._consecutive_unhealthy_checks = 0

            # Only increase after multiple healthy checks (avoid oscillation)
            if self._consecutive_healthy_checks >= 3:
                self.current_limit = min(
                    self.max_limit,
                    self.current_limit + self.increase_step
                )

                if self.current_limit > previous_limit:
                    logger.info(
                        f"Increasing concurrency limit: {previous_limit} → {self.current_limit} "
                        f"(healthy system)"
                    )
                    self._last_adjustment = datetime.utcnow()

        else:
            # System is under stress - decrease limit (AIMD multiplicative decrease)
            self._consecutive_unhealthy_checks += 1
            self._consecutive_healthy_checks = 0

            self.current_limit = max(
                self.min_limit,
                int(self.current_limit * self.decrease_factor)
            )

            logger.warning(
                f"Decreasing concurrency limit: {previous_limit} → {self.current_limit} "
                f"(unhealthy: CPU={metrics.cpu_usage_percent}%, "
                f"Memory={metrics.memory_usage_percent}%, "
                f"Latency={metrics.api_latency_p95_ms}ms, "
                f"Errors={metrics.api_error_rate:.2%})"
            )

            self._last_adjustment = datetime.utcnow()

        return self.current_limit

    def get_current_limit(self) -> int:
        """
        Get current concurrency limit

        Returns:
            Current limit value
        """
        return self.current_limit

    def set_limit_manually(self, new_limit: int):
        """
        Manually override concurrency limit

        Args:
            new_limit: New limit value
        """
        if new_limit < self.min_limit or new_limit > self.max_limit:
            raise ValueError(
                f"Limit {new_limit} outside valid range [{self.min_limit}, {self.max_limit}]"
            )

        previous_limit = self.current_limit
        self.current_limit = new_limit

        logger.info(f"Manually set concurrency limit: {previous_limit} → {new_limit}")

    def get_adjustment_stats(self) -> dict:
        """
        Get adjustment statistics

        Returns:
            Dict with stats: {
                'current_limit': int,
                'min_limit': int,
                'max_limit': int,
                'consecutive_healthy': int,
                'consecutive_unhealthy': int,
                'last_adjustment': datetime
            }
        """
        return {
            'current_limit': self.current_limit,
            'min_limit': self.min_limit,
            'max_limit': self.max_limit,
            'consecutive_healthy': self._consecutive_healthy_checks,
            'consecutive_unhealthy': self._consecutive_unhealthy_checks,
            'last_adjustment': self._last_adjustment
        }
