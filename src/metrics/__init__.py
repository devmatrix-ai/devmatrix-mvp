"""
Metrics module for MGE V2

Provides precision scoring, prometheus metrics, and performance tracking.
"""
from src.metrics.precision_metrics import PrecisionMetricsCalculator

__all__ = [
    'PrecisionMetricsCalculator',
]
