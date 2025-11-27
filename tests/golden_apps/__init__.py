"""
Golden Apps Framework - Phase 5

Reference implementations for automated validation.
Each golden app includes:
- spec.yaml: OpenAPI specification
- expected_ir.json: ApplicationIR snapshot
- expected_openapi.json: Generated OpenAPI snapshot
- expected_metrics.json: Expected compliance metrics
- known_regressions.json: Regressions to detect/avoid
"""

from tests.golden_apps.runner import (
    GoldenApp,
    GoldenAppResult,
    GoldenAppRunner,
    run_golden_app,
    run_all_golden_apps,
    list_golden_apps,
)

__all__ = [
    "GoldenApp",
    "GoldenAppResult",
    "GoldenAppRunner",
    "run_golden_app",
    "run_all_golden_apps",
    "list_golden_apps",
]
