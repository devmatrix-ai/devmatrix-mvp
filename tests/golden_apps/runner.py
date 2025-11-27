"""
Golden Apps Runner - Phase 5

Runs full pipeline against golden reference apps and compares results.

Usage:
    runner = GoldenAppRunner()
    result = runner.run("ecommerce")

    # Or run all:
    results = run_all_golden_apps()
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import yaml

logger = logging.getLogger(__name__)

# Base directory for golden apps
GOLDEN_APPS_DIR = Path(__file__).parent


class ComparisonStatus(str, Enum):
    """Status of comparison between expected and actual."""
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING_EXPECTED = "missing_expected"
    MISSING_ACTUAL = "missing_actual"
    IMPROVED = "improved"  # Actual is better than expected
    REGRESSED = "regressed"  # Actual is worse than expected


@dataclass
class DiffItem:
    """Single difference between expected and actual."""
    path: str  # JSON path to the difference
    expected: Any
    actual: Any
    status: ComparisonStatus
    severity: str = "warning"  # info, warning, error

    def __str__(self) -> str:
        return f"{self.path}: expected={self.expected}, actual={self.actual} [{self.status.value}]"


@dataclass
class ComparisonResult:
    """Result of comparing expected vs actual."""
    name: str  # What was compared (e.g., "ir", "openapi", "metrics")
    status: ComparisonStatus
    diffs: List[DiffItem] = field(default_factory=list)
    match_percentage: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status in (ComparisonStatus.MATCH, ComparisonStatus.IMPROVED)

    def summary(self) -> str:
        if self.passed:
            return f"✅ {self.name}: {self.match_percentage:.1f}% match"
        else:
            return f"❌ {self.name}: {self.match_percentage:.1f}% match ({len(self.diffs)} diffs)"


@dataclass
class GoldenApp:
    """A golden reference application."""
    name: str
    directory: Path
    spec_path: Path
    expected_ir_path: Optional[Path] = None
    expected_openapi_path: Optional[Path] = None
    expected_metrics_path: Optional[Path] = None
    known_regressions_path: Optional[Path] = None

    @classmethod
    def load(cls, name: str) -> "GoldenApp":
        """Load a golden app by name."""
        directory = GOLDEN_APPS_DIR / name
        if not directory.exists():
            raise ValueError(f"Golden app '{name}' not found at {directory}")

        # Find spec file - PRIORITIZE markdown (human language) over OpenAPI
        # This ensures golden apps use the same input format as E2E tests
        spec_path = None
        for ext in [".md", ".yaml", ".yml", ".json"]:
            candidate = directory / f"spec{ext}"
            if candidate.exists():
                spec_path = candidate
                break

        if spec_path is None:
            raise ValueError(f"No spec file found in {directory}")

        return cls(
            name=name,
            directory=directory,
            spec_path=spec_path,
            expected_ir_path=directory / "expected_ir.json" if (directory / "expected_ir.json").exists() else None,
            expected_openapi_path=directory / "expected_openapi.json" if (directory / "expected_openapi.json").exists() else None,
            expected_metrics_path=directory / "expected_metrics.json" if (directory / "expected_metrics.json").exists() else None,
            known_regressions_path=directory / "known_regressions.json" if (directory / "known_regressions.json").exists() else None,
        )

    def load_spec(self) -> Dict[str, Any]:
        """Load the OpenAPI spec."""
        with open(self.spec_path) as f:
            if self.spec_path.suffix in (".yaml", ".yml"):
                return yaml.safe_load(f)
            elif self.spec_path.suffix == ".md":
                # For markdown specs, return metadata with path
                return {
                    "_type": "markdown_spec",
                    "_path": str(self.spec_path),
                    "_content": f.read(),
                }
            return json.load(f)

    def load_expected_ir(self) -> Optional[Dict[str, Any]]:
        """Load expected ApplicationIR."""
        if self.expected_ir_path and self.expected_ir_path.exists():
            with open(self.expected_ir_path) as f:
                return json.load(f)
        return None

    def load_expected_openapi(self) -> Optional[Dict[str, Any]]:
        """Load expected generated OpenAPI."""
        if self.expected_openapi_path and self.expected_openapi_path.exists():
            with open(self.expected_openapi_path) as f:
                return json.load(f)
        return None

    def load_expected_metrics(self) -> Optional[Dict[str, Any]]:
        """Load expected metrics."""
        if self.expected_metrics_path and self.expected_metrics_path.exists():
            with open(self.expected_metrics_path) as f:
                return json.load(f)
        return None

    def load_known_regressions(self) -> List[str]:
        """Load known regression patterns."""
        if self.known_regressions_path and self.known_regressions_path.exists():
            with open(self.known_regressions_path) as f:
                data = json.load(f)
                return data.get("patterns", [])
        return []

    def save_expected_ir(self, ir: Dict[str, Any]) -> None:
        """Save ApplicationIR as new expected baseline."""
        path = self.directory / "expected_ir.json"
        with open(path, "w") as f:
            json.dump(ir, f, indent=2, default=str)
        self.expected_ir_path = path
        logger.info(f"Saved expected IR to {path}")

    def save_expected_openapi(self, openapi: Dict[str, Any]) -> None:
        """Save generated OpenAPI as new expected baseline."""
        path = self.directory / "expected_openapi.json"
        with open(path, "w") as f:
            json.dump(openapi, f, indent=2, default=str)
        self.expected_openapi_path = path
        logger.info(f"Saved expected OpenAPI to {path}")

    def save_expected_metrics(self, metrics: Dict[str, Any]) -> None:
        """Save metrics as new expected baseline."""
        path = self.directory / "expected_metrics.json"
        with open(path, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        self.expected_metrics_path = path
        logger.info(f"Saved expected metrics to {path}")


@dataclass
class GoldenAppResult:
    """Result of running a golden app test."""
    app_name: str
    passed: bool
    duration_ms: float
    ir_comparison: Optional[ComparisonResult] = None
    openapi_comparison: Optional[ComparisonResult] = None
    metrics_comparison: Optional[ComparisonResult] = None
    regression_check: Optional[ComparisonResult] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    actual_ir: Optional[Dict[str, Any]] = None
    actual_openapi: Optional[Dict[str, Any]] = None
    actual_metrics: Optional[Dict[str, Any]] = None

    def summary(self) -> str:
        """Get human-readable summary."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"Golden App: {self.app_name}",
            f"Status: {status}",
            f"Duration: {self.duration_ms:.0f}ms",
        ]

        if self.ir_comparison:
            lines.append(f"  IR: {self.ir_comparison.summary()}")
        if self.openapi_comparison:
            lines.append(f"  OpenAPI: {self.openapi_comparison.summary()}")
        if self.metrics_comparison:
            lines.append(f"  Metrics: {self.metrics_comparison.summary()}")
        if self.regression_check:
            lines.append(f"  Regressions: {self.regression_check.summary()}")

        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for err in self.errors[:3]:
                lines.append(f"    - {err}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "app_name": self.app_name,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "ir_comparison": {
                "status": self.ir_comparison.status.value if self.ir_comparison else None,
                "match_percentage": self.ir_comparison.match_percentage if self.ir_comparison else None,
                "diffs_count": len(self.ir_comparison.diffs) if self.ir_comparison else 0,
            } if self.ir_comparison else None,
            "openapi_comparison": {
                "status": self.openapi_comparison.status.value if self.openapi_comparison else None,
                "match_percentage": self.openapi_comparison.match_percentage if self.openapi_comparison else None,
                "diffs_count": len(self.openapi_comparison.diffs) if self.openapi_comparison else 0,
            } if self.openapi_comparison else None,
            "metrics_comparison": {
                "status": self.metrics_comparison.status.value if self.metrics_comparison else None,
                "match_percentage": self.metrics_comparison.match_percentage if self.metrics_comparison else None,
            } if self.metrics_comparison else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class GoldenAppRunner:
    """
    Runs golden app tests against the full pipeline.

    Usage:
        runner = GoldenAppRunner()
        result = runner.run("ecommerce")
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize runner.

        Args:
            strict_mode: If True, any diff fails the test.
                        If False, only regressions fail.
        """
        self.strict_mode = strict_mode

    def run(
        self,
        app_name: str,
        update_baseline: bool = False,
    ) -> GoldenAppResult:
        """
        Run golden app test.

        Args:
            app_name: Name of golden app to test
            update_baseline: If True, save actual as new expected

        Returns:
            GoldenAppResult with comparison results
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Load golden app
            golden_app = GoldenApp.load(app_name)
            logger.info(f"Running golden app: {app_name}")

            # Load spec
            spec = golden_app.load_spec()

            # Run pipeline to get actual results
            actual_ir, actual_openapi, actual_metrics = self._run_pipeline(spec)

            # Compare IR
            ir_comparison = None
            expected_ir = golden_app.load_expected_ir()
            if expected_ir:
                ir_comparison = self._compare_ir(expected_ir, actual_ir)
            elif actual_ir:
                warnings.append("No expected IR baseline - consider running with update_baseline=True")

            # Compare OpenAPI
            openapi_comparison = None
            expected_openapi = golden_app.load_expected_openapi()
            if expected_openapi:
                openapi_comparison = self._compare_openapi(expected_openapi, actual_openapi)
            elif actual_openapi:
                warnings.append("No expected OpenAPI baseline - consider running with update_baseline=True")

            # Compare metrics
            metrics_comparison = None
            expected_metrics = golden_app.load_expected_metrics()
            if expected_metrics:
                metrics_comparison = self._compare_metrics(expected_metrics, actual_metrics)

            # Check for regressions
            known_regressions = golden_app.load_known_regressions()
            regression_check = self._check_regressions(known_regressions, actual_ir, actual_openapi)

            # Update baselines if requested
            if update_baseline:
                if actual_ir:
                    golden_app.save_expected_ir(actual_ir)
                if actual_openapi:
                    golden_app.save_expected_openapi(actual_openapi)
                if actual_metrics:
                    golden_app.save_expected_metrics(actual_metrics)

            # Determine pass/fail
            passed = self._evaluate_result(
                ir_comparison,
                openapi_comparison,
                metrics_comparison,
                regression_check,
            )

            duration_ms = (time.time() - start_time) * 1000

            return GoldenAppResult(
                app_name=app_name,
                passed=passed,
                duration_ms=duration_ms,
                ir_comparison=ir_comparison,
                openapi_comparison=openapi_comparison,
                metrics_comparison=metrics_comparison,
                regression_check=regression_check,
                errors=errors,
                warnings=warnings,
                actual_ir=actual_ir,
                actual_openapi=actual_openapi,
                actual_metrics=actual_metrics,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            errors.append(str(e))
            logger.error(f"Golden app test failed: {e}")

            return GoldenAppResult(
                app_name=app_name,
                passed=False,
                duration_ms=duration_ms,
                errors=errors,
                warnings=warnings,
            )

    def _run_pipeline(
        self,
        spec: Dict[str, Any],
    ) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
        """
        Run the full pipeline with spec.

        Returns:
            (actual_ir, actual_openapi, actual_metrics)
        """
        try:
            app_ir = None

            # Bug #23 fix: Changed OpenAPISpecParser -> SpecParser (correct class name)
            # Bug #34 fix: Use IRBuilder.build_from_spec() instead of non-existent normalize_to_application_ir
            # Handle markdown specs differently
            if spec.get("_type") == "markdown_spec":
                # Use the natural language spec parser
                try:
                    from src.parsing.spec_parser import SpecParser
                    from src.cognitive.ir.ir_builder import IRBuilder
                    parser = SpecParser()
                    # Read from file path for markdown
                    spec_path = spec.get("_path")
                    if spec_path:
                        # Bug #39 fix: SpecParser.parse() expects Path object for file reading
                        # When passed a string, it treats it as markdown content, not as a path
                        spec_model = parser.parse(Path(spec_path))
                        app_ir = IRBuilder.build_from_spec(spec_model)
                except Exception as md_err:
                    logger.warning(f"Markdown spec parsing failed: {md_err}")
                    import traceback
                    traceback.print_exc()
                    return None, None, None
            else:
                # Standard OpenAPI spec (dict from YAML)
                # Golden apps should prioritize markdown specs (.md) over OpenAPI (.yaml)
                # If we reach here, try to use SpecToApplicationIR with the YAML content
                try:
                    import asyncio
                    from src.specs.spec_to_application_ir import SpecToApplicationIR
                    import yaml as yaml_lib

                    # Convert dict back to YAML string for SpecToApplicationIR
                    yaml_content = yaml_lib.dump(spec, default_flow_style=False)
                    spec_name = spec.get("info", {}).get("title", "openapi_spec")

                    converter = SpecToApplicationIR()
                    app_ir = asyncio.run(converter.get_application_ir(yaml_content, spec_name))
                except Exception as openapi_err:
                    logger.warning(f"OpenAPI spec processing failed: {openapi_err}")
                    import traceback
                    traceback.print_exc()
                    return None, None, None

            if app_ir is None:
                return None, None, None

            actual_ir = app_ir.to_dict() if hasattr(app_ir, 'to_dict') else None

            # Generate OpenAPI from IR (if implemented)
            actual_openapi = None
            try:
                if hasattr(app_ir, 'to_openapi'):
                    actual_openapi = app_ir.to_openapi()
            except Exception:
                pass

            # Collect metrics
            actual_metrics = self._collect_metrics(app_ir)

            return actual_ir, actual_openapi, actual_metrics

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return None, None, None

    def _collect_metrics(self, app_ir: Any) -> Dict[str, Any]:
        """Collect metrics from ApplicationIR.

        Bug #38 fix: Use correct ApplicationIR accessors (get_endpoints(), get_entities())
        instead of non-existent attributes (endpoints, entities).
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "ir_stats": {},
            "compliance": {},
        }

        try:
            # Extract IR stats using correct ApplicationIR accessors
            # Bug #38: ApplicationIR has get_endpoints(), get_entities() methods, not direct attributes
            endpoints = []
            entities = []
            relationships = []

            if hasattr(app_ir, 'get_endpoints'):
                endpoints = app_ir.get_endpoints() or []
            elif hasattr(app_ir, 'api_model') and hasattr(app_ir.api_model, 'endpoints'):
                endpoints = app_ir.api_model.endpoints or []

            if hasattr(app_ir, 'get_entities'):
                entities = app_ir.get_entities() or []
            elif hasattr(app_ir, 'domain_model') and hasattr(app_ir.domain_model, 'entities'):
                entities = app_ir.domain_model.entities or []

            if hasattr(app_ir, 'domain_model') and hasattr(app_ir.domain_model, 'relationships'):
                relationships = app_ir.domain_model.relationships or []

            metrics["ir_stats"]["total_endpoints"] = len(endpoints)
            metrics["ir_stats"]["total_entities"] = len(entities)
            metrics["ir_stats"]["total_relationships"] = len(relationships)

            # Calculate IR-level compliance metrics
            # These measure IR completeness/quality, not code compliance
            # Bug #38: Original code called validator.validate(app_ir) with wrong signature
            try:
                # Semantic compliance: Are all core IR components present?
                has_domain = hasattr(app_ir, 'domain_model') and app_ir.domain_model is not None
                has_api = hasattr(app_ir, 'api_model') and app_ir.api_model is not None
                has_behavior = hasattr(app_ir, 'behavior_model') and app_ir.behavior_model is not None

                core_components = [has_domain, has_api]
                semantic_score = sum(core_components) / len(core_components) if core_components else 0.0

                # IR compliance relaxed: Basic structure present (entities, endpoints exist)
                has_entities = len(entities) > 0
                has_endpoints = len(endpoints) > 0
                relaxed_checks = [has_entities, has_endpoints, has_domain, has_api]
                relaxed_score = sum(relaxed_checks) / len(relaxed_checks) if relaxed_checks else 0.0

                # IR compliance strict: Full structure with relationships and behaviors
                has_relationships = len(relationships) > 0
                has_flows = hasattr(app_ir, 'get_flows') and len(app_ir.get_flows() or []) > 0
                strict_checks = relaxed_checks + [has_relationships, has_flows, has_behavior]
                strict_score = sum(strict_checks) / len(strict_checks) if strict_checks else 0.0

                metrics["compliance"] = {
                    "semantic_compliance": round(semantic_score, 2),
                    "ir_compliance_relaxed": round(relaxed_score, 2),
                    "ir_compliance_strict": round(strict_score, 2),
                }
            except Exception as e:
                logger.warning(f"Failed to calculate compliance metrics: {e}")
                metrics["compliance"] = {
                    "semantic_compliance": 0.0,
                    "ir_compliance_relaxed": 0.0,
                    "ir_compliance_strict": 0.0,
                }

        except Exception as e:
            logger.warning(f"Failed to collect some metrics: {e}")

        return metrics

    def _compare_ir(
        self,
        expected: Dict[str, Any],
        actual: Optional[Dict[str, Any]],
    ) -> ComparisonResult:
        """Compare expected vs actual ApplicationIR."""
        if actual is None:
            return ComparisonResult(
                name="IR",
                status=ComparisonStatus.MISSING_ACTUAL,
                match_percentage=0.0,
            )

        diffs = self._deep_compare(expected, actual, "ir")

        # Calculate match percentage
        total_keys = self._count_keys(expected)
        diff_keys = len([d for d in diffs if d.status == ComparisonStatus.MISMATCH])
        match_pct = ((total_keys - diff_keys) / total_keys * 100) if total_keys > 0 else 100.0

        if len(diffs) == 0:
            status = ComparisonStatus.MATCH
        elif match_pct >= 95:
            status = ComparisonStatus.IMPROVED if self._is_improved(expected, actual) else ComparisonStatus.MISMATCH
        else:
            status = ComparisonStatus.REGRESSED if match_pct < 80 else ComparisonStatus.MISMATCH

        return ComparisonResult(
            name="IR",
            status=status,
            diffs=diffs,
            match_percentage=match_pct,
        )

    def _compare_openapi(
        self,
        expected: Dict[str, Any],
        actual: Optional[Dict[str, Any]],
    ) -> ComparisonResult:
        """Compare expected vs actual OpenAPI."""
        if actual is None:
            return ComparisonResult(
                name="OpenAPI",
                status=ComparisonStatus.MISSING_ACTUAL,
                match_percentage=0.0,
            )

        diffs = self._deep_compare(expected, actual, "openapi")

        total_keys = self._count_keys(expected)
        diff_keys = len([d for d in diffs if d.status == ComparisonStatus.MISMATCH])
        match_pct = ((total_keys - diff_keys) / total_keys * 100) if total_keys > 0 else 100.0

        if len(diffs) == 0:
            status = ComparisonStatus.MATCH
        else:
            status = ComparisonStatus.REGRESSED if match_pct < 80 else ComparisonStatus.MISMATCH

        return ComparisonResult(
            name="OpenAPI",
            status=status,
            diffs=diffs,
            match_percentage=match_pct,
        )

    def _compare_metrics(
        self,
        expected: Dict[str, Any],
        actual: Optional[Dict[str, Any]],
    ) -> ComparisonResult:
        """Compare expected vs actual metrics."""
        if actual is None:
            return ComparisonResult(
                name="Metrics",
                status=ComparisonStatus.MISSING_ACTUAL,
                match_percentage=0.0,
            )

        diffs: List[DiffItem] = []

        # Compare compliance metrics
        exp_compliance = expected.get("compliance", {})
        act_compliance = actual.get("compliance", {})

        for metric in ["semantic_compliance", "ir_compliance_relaxed", "ir_compliance_strict"]:
            exp_val = exp_compliance.get(metric, 0)
            act_val = act_compliance.get(metric, 0)

            if act_val < exp_val - 0.05:  # 5% tolerance
                diffs.append(DiffItem(
                    path=f"compliance.{metric}",
                    expected=exp_val,
                    actual=act_val,
                    status=ComparisonStatus.REGRESSED,
                    severity="error",
                ))
            elif act_val > exp_val + 0.05:
                diffs.append(DiffItem(
                    path=f"compliance.{metric}",
                    expected=exp_val,
                    actual=act_val,
                    status=ComparisonStatus.IMPROVED,
                    severity="info",
                ))

        # Determine overall status
        regressions = [d for d in diffs if d.status == ComparisonStatus.REGRESSED]
        improvements = [d for d in diffs if d.status == ComparisonStatus.IMPROVED]

        if len(regressions) > 0:
            status = ComparisonStatus.REGRESSED
        elif len(improvements) > 0:
            status = ComparisonStatus.IMPROVED
        else:
            status = ComparisonStatus.MATCH

        match_pct = 100.0 if len(regressions) == 0 else (100.0 - len(regressions) * 10)

        return ComparisonResult(
            name="Metrics",
            status=status,
            diffs=diffs,
            match_percentage=match_pct,
        )

    def _check_regressions(
        self,
        known_patterns: List[str],
        actual_ir: Optional[Dict],
        actual_openapi: Optional[Dict],
    ) -> ComparisonResult:
        """Check for known regression patterns."""
        diffs: List[DiffItem] = []

        # Serialize to string for pattern matching
        ir_str = json.dumps(actual_ir) if actual_ir else ""
        openapi_str = json.dumps(actual_openapi) if actual_openapi else ""
        combined = ir_str + openapi_str

        for pattern in known_patterns:
            if pattern in combined:
                diffs.append(DiffItem(
                    path=f"regression:{pattern}",
                    expected="not present",
                    actual="found",
                    status=ComparisonStatus.REGRESSED,
                    severity="error",
                ))

        status = ComparisonStatus.REGRESSED if diffs else ComparisonStatus.MATCH
        match_pct = 100.0 if not diffs else 0.0

        return ComparisonResult(
            name="Regressions",
            status=status,
            diffs=diffs,
            match_percentage=match_pct,
        )

    def _deep_compare(
        self,
        expected: Any,
        actual: Any,
        path: str,
    ) -> List[DiffItem]:
        """Recursively compare two structures."""
        diffs: List[DiffItem] = []

        if type(expected) != type(actual):
            diffs.append(DiffItem(
                path=path,
                expected=type(expected).__name__,
                actual=type(actual).__name__,
                status=ComparisonStatus.MISMATCH,
            ))
            return diffs

        if isinstance(expected, dict):
            all_keys = set(expected.keys()) | set(actual.keys())
            for key in all_keys:
                new_path = f"{path}.{key}"
                if key not in expected:
                    diffs.append(DiffItem(
                        path=new_path,
                        expected=None,
                        actual=actual[key],
                        status=ComparisonStatus.IMPROVED,  # New in actual
                        severity="info",
                    ))
                elif key not in actual:
                    diffs.append(DiffItem(
                        path=new_path,
                        expected=expected[key],
                        actual=None,
                        status=ComparisonStatus.MISMATCH,
                        severity="warning",
                    ))
                else:
                    diffs.extend(self._deep_compare(expected[key], actual[key], new_path))

        elif isinstance(expected, list):
            if len(expected) != len(actual):
                diffs.append(DiffItem(
                    path=f"{path}.length",
                    expected=len(expected),
                    actual=len(actual),
                    status=ComparisonStatus.MISMATCH,
                    severity="warning",
                ))
            for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
                diffs.extend(self._deep_compare(exp_item, act_item, f"{path}[{i}]"))

        elif expected != actual:
            diffs.append(DiffItem(
                path=path,
                expected=expected,
                actual=actual,
                status=ComparisonStatus.MISMATCH,
            ))

        return diffs

    def _count_keys(self, obj: Any) -> int:
        """Count total keys in nested structure."""
        if isinstance(obj, dict):
            return len(obj) + sum(self._count_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return sum(self._count_keys(item) for item in obj)
        return 1

    def _is_improved(self, expected: Dict, actual: Dict) -> bool:
        """Check if actual is an improvement over expected."""
        # Simple heuristic: more endpoints/entities = improved
        exp_endpoints = len(expected.get("endpoints", []))
        act_endpoints = len(actual.get("endpoints", []))
        return act_endpoints >= exp_endpoints

    def _evaluate_result(
        self,
        ir_comparison: Optional[ComparisonResult],
        openapi_comparison: Optional[ComparisonResult],
        metrics_comparison: Optional[ComparisonResult],
        regression_check: Optional[ComparisonResult],
    ) -> bool:
        """Determine overall pass/fail."""
        # Regressions always fail
        if regression_check and regression_check.status == ComparisonStatus.REGRESSED:
            return False

        # Metrics regressions fail
        if metrics_comparison and metrics_comparison.status == ComparisonStatus.REGRESSED:
            return False

        if self.strict_mode:
            # In strict mode, any mismatch fails
            if ir_comparison and not ir_comparison.passed:
                return False
            if openapi_comparison and not openapi_comparison.passed:
                return False
        else:
            # In non-strict mode, only major regressions fail
            if ir_comparison and ir_comparison.match_percentage < 80:
                return False
            if openapi_comparison and openapi_comparison.match_percentage < 80:
                return False

        return True


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_runner: Optional[GoldenAppRunner] = None


def get_runner(strict_mode: bool = True) -> GoldenAppRunner:
    """Get singleton runner."""
    global _runner
    if _runner is None:
        _runner = GoldenAppRunner(strict_mode=strict_mode)
    return _runner


def run_golden_app(
    app_name: str,
    strict_mode: bool = True,
    update_baseline: bool = False,
) -> GoldenAppResult:
    """
    Run a single golden app test.

    Args:
        app_name: Name of golden app
        strict_mode: If True, any diff fails
        update_baseline: If True, save actual as new expected

    Returns:
        GoldenAppResult
    """
    runner = GoldenAppRunner(strict_mode=strict_mode)
    return runner.run(app_name, update_baseline=update_baseline)


def run_all_golden_apps(
    strict_mode: bool = True,
    update_baseline: bool = False,
) -> Dict[str, GoldenAppResult]:
    """
    Run all golden app tests.

    Returns:
        Dict mapping app name to result
    """
    results = {}
    runner = GoldenAppRunner(strict_mode=strict_mode)

    for app_name in list_golden_apps():
        results[app_name] = runner.run(app_name, update_baseline=update_baseline)

    return results


def list_golden_apps() -> List[str]:
    """List all available golden apps."""
    apps = []
    for item in GOLDEN_APPS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            # Check if it has a spec file
            has_spec = any(
                (item / f"spec{ext}").exists()
                for ext in [".yaml", ".yml", ".json"]
            )
            if has_spec:
                apps.append(item.name)
    return sorted(apps)


def format_golden_apps_report(results: Dict[str, GoldenAppResult]) -> str:
    """Format results as ASCII table."""
    lines = [
        "",
        "Golden Apps Test Results",
        "=" * 60,
    ]

    passed = 0
    failed = 0

    for app_name, result in results.items():
        status = "✅ PASS" if result.passed else "❌ FAIL"
        if result.passed:
            passed += 1
        else:
            failed += 1

        lines.append(f"  {status} {app_name} ({result.duration_ms:.0f}ms)")

        if result.ir_comparison:
            lines.append(f"       IR: {result.ir_comparison.match_percentage:.1f}%")
        if result.metrics_comparison:
            lines.append(f"       Metrics: {result.metrics_comparison.status.value}")
        if result.errors:
            for err in result.errors[:2]:
                lines.append(f"       Error: {err[:50]}...")

    lines.append("=" * 60)
    lines.append(f"Total: {passed} passed, {failed} failed")
    lines.append("")

    return "\n".join(lines)
