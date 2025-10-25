"""
Prometheus Metrics for MGE V2 Execution

Tracks retry, wave, execution, and atom-level performance metrics.
"""

from prometheus_client import Counter, Gauge, Histogram

# ========================================
# Retry Metrics
# ========================================

RETRY_ATTEMPTS_TOTAL = Counter(
    "v2_retry_attempts_total",
    "Total retry attempts",
    ["atom_id", "attempt_number"]
)

RETRY_SUCCESS_RATE = Gauge(
    "v2_retry_success_rate",
    "Retry success rate (0.0-1.0)"
)

RETRY_TEMPERATURE_CHANGES = Counter(
    "v2_retry_temperature_changes",
    "Temperature backoff events",
    ["from_temp", "to_temp"]
)

# ========================================
# Wave Metrics
# ========================================

WAVE_COMPLETION_PERCENT = Gauge(
    "v2_wave_completion_percent",
    "Wave progress (0-100)",
    ["wave_id", "masterplan_id"]
)

WAVE_ATOM_THROUGHPUT = Gauge(
    "v2_wave_atom_throughput",
    "Atoms processed per second in wave"
)

WAVE_TIME_SECONDS = Histogram(
    "v2_wave_time_seconds",
    "Wave execution time in seconds",
    ["wave_id", "masterplan_id"]
)

# ========================================
# Execution Metrics
# ========================================

EXECUTION_PRECISION_PERCENT = Gauge(
    "v2_execution_precision_percent",
    "Execution precision (0-100)",
    ["masterplan_id"]
)

EXECUTION_TIME_SECONDS = Histogram(
    "v2_execution_time_seconds",
    "Total execution time in seconds",
    ["masterplan_id"]
)

EXECUTION_COST_USD_TOTAL = Counter(
    "v2_execution_cost_usd_total",
    "Total execution cost in USD",
    ["masterplan_id"]
)

# ========================================
# Atom Metrics
# ========================================

ATOMS_SUCCEEDED_TOTAL = Counter(
    "v2_atoms_succeeded_total",
    "Total successful atoms",
    ["masterplan_id"]
)

ATOMS_FAILED_TOTAL = Counter(
    "v2_atoms_failed_total",
    "Total failed atoms",
    ["masterplan_id"]
)

ATOM_EXECUTION_TIME_SECONDS = Histogram(
    "v2_atom_execution_time_seconds",
    "Per-atom execution time in seconds"
)

ATOM_VALIDATION_PASS_RATE = Gauge(
    "v2_atom_validation_pass_rate",
    "Atom validation pass rate (0.0-1.0)"
)


# ========================================
# Helper Functions
# ========================================

def calculate_success_rate() -> float:
    """
    Calculate overall retry success rate.

    Returns:
        Success rate as float (0.0-1.0)
    """
    try:
        # Get total attempts and successful attempts
        # This is a simplified calculation - in production,
        # you'd track successes separately
        total_attempts = sum(
            metric.samples[0].value
            for metric in RETRY_ATTEMPTS_TOTAL.collect()
            for sample in metric.samples
        )

        if total_attempts == 0:
            return 0.0

        # Estimate success rate (simplified)
        # In real implementation, track successes explicitly
        return 0.95  # Placeholder - implement actual tracking

    except Exception:
        return 0.0


def update_success_rate():
    """Update the retry success rate gauge."""
    rate = calculate_success_rate()
    RETRY_SUCCESS_RATE.set(rate)
