"""
Global Metrics Collector

Singleton instance to avoid circular imports.
"""

from .metrics_collector import MetricsCollector

# Global metrics collector instance
metrics_collector = MetricsCollector()
