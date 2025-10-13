"""
Metrics Collection System

Provides Prometheus-compatible metrics collection for monitoring
system performance and behavior.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from threading import Lock


class MetricType(Enum):
    """Metric type enumeration."""

    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"  # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values


@dataclass
class Metric:
    """Single metric data point."""

    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    help_text: str = ""


class MetricsCollector:
    """
    Prometheus-compatible metrics collector.

    Collects and exposes metrics in Prometheus exposition format
    for scraping by monitoring systems.

    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.increment_counter("requests_total", labels={"method": "GET"})
        >>> metrics.set_gauge("active_connections", 42)
        >>> metrics.observe_histogram("request_duration_seconds", 0.123)
        >>> print(metrics.export_prometheus())
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._metric_help: Dict[str, str] = {}
        self._lock = Lock()

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """
        Increment counter metric.

        Args:
            name: Metric name
            value: Increment value (default: 1.0)
            labels: Metric labels
            help_text: Help text
        """
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
            if help_text:
                self._metric_help[name] = help_text

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """
        Set gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Metric labels
            help_text: Help text
        """
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            if help_text:
                self._metric_help[name] = help_text

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """
        Add observation to histogram.

        Args:
            name: Metric name
            value: Observed value
            labels: Metric labels
            help_text: Help text
        """
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            if help_text:
                self._metric_help[name] = help_text

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key)

    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        Get histogram statistics.

        Returns:
            Dictionary with count, sum, min, max, avg
        """
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0}

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus exposition format.

        Returns:
            Prometheus-formatted metrics
        """
        lines = []

        with self._lock:
            # Export counters
            for key, value in sorted(self._counters.items()):
                name, labels = self._parse_key(key)
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} counter")
                label_str = self._format_labels(labels) if labels else ""
                lines.append(f"{name}{label_str} {value}")

            # Export gauges
            for key, value in sorted(self._gauges.items()):
                name, labels = self._parse_key(key)
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} gauge")
                label_str = self._format_labels(labels) if labels else ""
                lines.append(f"{name}{label_str} {value}")

            # Export histograms
            for key, values in sorted(self._histograms.items()):
                name, labels = self._parse_key(key)
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} histogram")

                stats = self.get_histogram_stats(name, labels)
                label_str = self._format_labels(labels) if labels else ""

                lines.append(f"{name}_count{label_str} {stats['count']}")
                lines.append(f"{name}_sum{label_str} {stats['sum']}")

        return "\n".join(lines) + "\n"

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._metric_help.clear()

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Make metric key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str) -> tuple:
        """Parse metric key into name and labels."""
        if "{" not in key:
            return key, {}

        name, label_part = key.split("{", 1)
        label_part = label_part.rstrip("}")

        labels = {}
        for pair in label_part.split(","):
            k, v = pair.split("=", 1)
            labels[k] = v

        return name, labels

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        label_strs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_strs) + "}"
