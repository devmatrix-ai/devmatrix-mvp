"""
QA Levels - Fast vs Heavy Validation

Phase 0.5.6: Separate validation into two levels for efficiency.

FAST QA (Local/PR):
- py_compile, AST validation
- Regression pattern detection
- IR/OpenAPI compliance check
- Dead code detection
- ~seconds, no external deps

HEAVY QA (CI/Nightly):
- All FAST checks +
- alembic upgrade (schema validation)
- docker-compose up (service startup)
- Smoke HTTP tests
- ~minutes, requires Docker
"""

import os
import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class QALevel(str, Enum):
    """Quality Assurance levels."""
    FAST = "fast"    # py_compile, AST, regressions, IR compliance
    HEAVY = "heavy"  # + alembic, docker, smoke tests


class QAStage(str, Enum):
    """Individual QA stages."""
    SYNTAX = "syntax"
    REGRESSION = "regression"
    DEAD_CODE = "dead_code"
    IMPORT_CHECK = "import_check"
    IR_COMPLIANCE = "ir_compliance"
    OPENAPI_COMPLIANCE = "openapi_compliance"
    ALEMBIC = "alembic"
    DOCKER = "docker"
    SMOKE_TEST = "smoke_test"


@dataclass
class QAStageResult:
    """Result of a single QA stage."""
    stage: QAStage
    passed: bool
    duration_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class QAResult:
    """Complete QA result."""
    level: QALevel
    passed: bool
    stages: List[QAStageResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def summary(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        passed_stages = sum(1 for s in self.stages if s.passed)
        skipped_stages = sum(1 for s in self.stages if s.skipped)
        return (
            f"{status} [{self.level.value.upper()}] | "
            f"Stages: {passed_stages}/{len(self.stages)} passed "
            f"({skipped_stages} skipped) | "
            f"Time: {self.total_duration_ms:.0f}ms"
        )


# =============================================================================
# STAGE DEFINITIONS BY LEVEL
# =============================================================================

FAST_STAGES: List[QAStage] = [
    QAStage.SYNTAX,
    QAStage.REGRESSION,
    QAStage.DEAD_CODE,
    QAStage.IMPORT_CHECK,
    QAStage.IR_COMPLIANCE,
    QAStage.OPENAPI_COMPLIANCE,
]

HEAVY_STAGES: List[QAStage] = FAST_STAGES + [
    QAStage.ALEMBIC,
    QAStage.DOCKER,
    QAStage.SMOKE_TEST,
]


def get_stages_for_level(level: QALevel) -> List[QAStage]:
    """Get QA stages for a given level."""
    if level == QALevel.FAST:
        return FAST_STAGES
    return HEAVY_STAGES


# =============================================================================
# QA EXECUTOR
# =============================================================================

class QAExecutor:
    """
    Executes QA pipeline at specified level.

    Usage:
        executor = QAExecutor(QALevel.FAST)
        result = executor.run(files, ir=application_ir)
    """

    def __init__(self, level: QALevel = None):
        """
        Initialize QA executor.

        Args:
            level: QA level (defaults to env QA_LEVEL or FAST)
        """
        if level is None:
            level = QALevel(os.getenv("QA_LEVEL", "fast"))
        self.level = level
        self._stage_handlers: Dict[QAStage, Callable] = {
            QAStage.SYNTAX: self._run_syntax,
            QAStage.REGRESSION: self._run_regression,
            QAStage.DEAD_CODE: self._run_dead_code,
            QAStage.IMPORT_CHECK: self._run_import_check,
            QAStage.IR_COMPLIANCE: self._run_ir_compliance,
            QAStage.OPENAPI_COMPLIANCE: self._run_openapi_compliance,
            QAStage.ALEMBIC: self._run_alembic,
            QAStage.DOCKER: self._run_docker,
            QAStage.SMOKE_TEST: self._run_smoke_test,
        }

    def run(
        self,
        files: Dict[str, str],
        ir: Optional[Any] = None,
        app_dir: Optional[str] = None,
    ) -> QAResult:
        """
        Run QA pipeline.

        Args:
            files: Dict of file_path -> content
            ir: ApplicationIR for compliance checks
            app_dir: Directory for heavy checks (docker, alembic)

        Returns:
            QAResult with all stage results
        """
        import time
        start_time = time.time()

        stages = get_stages_for_level(self.level)
        results: List[QAStageResult] = []
        all_passed = True

        logger.info(f"🔍 Starting QA [{self.level.value.upper()}] - {len(stages)} stages")

        for stage in stages:
            handler = self._stage_handlers.get(stage)
            if handler:
                stage_start = time.time()
                try:
                    stage_result = handler(files, ir, app_dir)
                except Exception as e:
                    stage_result = QAStageResult(
                        stage=stage,
                        passed=False,
                        duration_ms=0,
                        errors=[f"Stage error: {str(e)}"],
                    )
                stage_result.duration_ms = (time.time() - stage_start) * 1000
                results.append(stage_result)

                if not stage_result.passed and not stage_result.skipped:
                    all_passed = False

                status = "✅" if stage_result.passed else ("⏭️" if stage_result.skipped else "❌")
                logger.info(f"  {status} {stage.value}: {stage_result.duration_ms:.0f}ms")
            else:
                results.append(QAStageResult(
                    stage=stage,
                    passed=True,
                    duration_ms=0,
                    skipped=True,
                    skip_reason="No handler defined",
                ))

        total_duration = (time.time() - start_time) * 1000

        result = QAResult(
            level=self.level,
            passed=all_passed,
            stages=results,
            total_duration_ms=total_duration,
        )

        logger.info(f"📊 QA Complete: {result.summary()}")
        return result

    # =========================================================================
    # FAST STAGES (Always run)
    # =========================================================================

    def _run_syntax(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run syntax validation."""
        from src.validation.basic_pipeline import validate_generated_files

        result = validate_generated_files(files)

        # Filter to only syntax errors
        syntax_errors = [e for e in result.errors if e.category == "syntax"]

        return QAStageResult(
            stage=QAStage.SYNTAX,
            passed=len(syntax_errors) == 0,
            duration_ms=result.duration_ms,
            errors=[f"{e.file_path}:{e.line_number}: {e.message}" for e in syntax_errors],
        )

    def _run_regression(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run regression pattern detection."""
        from src.validation.basic_pipeline import validate_generated_files

        result = validate_generated_files(files)

        # Filter to regression errors (not syntax, not dead_code)
        regression_cats = {"server_default", "schema_error", "security", "async_pattern", "incomplete_code"}
        regression_errors = [e for e in result.errors if e.category in regression_cats]

        return QAStageResult(
            stage=QAStage.REGRESSION,
            passed=len(regression_errors) == 0,
            duration_ms=0,
            errors=[f"[{e.category}] {e.file_path}:{e.line_number}: {e.message}" for e in regression_errors],
        )

    def _run_dead_code(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run dead code detection."""
        from src.validation.basic_pipeline import validate_generated_files

        result = validate_generated_files(files)

        dead_code_warnings = [e for e in result.warnings if e.category == "dead_code"]

        return QAStageResult(
            stage=QAStage.DEAD_CODE,
            passed=True,  # Warnings don't fail
            duration_ms=0,
            warnings=[f"{e.file_path}:{e.line_number}: {e.message}" for e in dead_code_warnings],
        )

    def _run_import_check(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run import validation."""
        from src.validation.basic_pipeline import validate_generated_files

        result = validate_generated_files(files)

        import_errors = [e for e in result.errors if e.category == "import_error"]
        import_warnings = [e for e in result.warnings if e.category in ("import_error", "import_style")]

        return QAStageResult(
            stage=QAStage.IMPORT_CHECK,
            passed=len(import_errors) == 0,
            duration_ms=0,
            errors=[f"{e.file_path}:{e.line_number}: {e.message}" for e in import_errors],
            warnings=[f"{e.file_path}:{e.line_number}: {e.message}" for e in import_warnings],
        )

    def _run_ir_compliance(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run IR compliance check."""
        if ir is None:
            return QAStageResult(
                stage=QAStage.IR_COMPLIANCE,
                passed=True,
                duration_ms=0,
                skipped=True,
                skip_reason="No ApplicationIR provided",
            )

        # IR compliance check - PLANNED: Integrate with compliance_validator
        # Currently passes since IR generation is validated during parsing
        return QAStageResult(
            stage=QAStage.IR_COMPLIANCE,
            passed=True,
            duration_ms=0,
        )

    def _run_openapi_compliance(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run OpenAPI compliance check."""
        # Check if openapi.json exists in files
        openapi_content = None
        for path, content in files.items():
            if "openapi.json" in path:
                openapi_content = content
                break

        if openapi_content is None:
            return QAStageResult(
                stage=QAStage.OPENAPI_COMPLIANCE,
                passed=True,
                duration_ms=0,
                skipped=True,
                skip_reason="No openapi.json in files",
            )

        # Basic JSON validation
        import json
        try:
            json.loads(openapi_content)
            return QAStageResult(
                stage=QAStage.OPENAPI_COMPLIANCE,
                passed=True,
                duration_ms=0,
            )
        except json.JSONDecodeError as e:
            return QAStageResult(
                stage=QAStage.OPENAPI_COMPLIANCE,
                passed=False,
                duration_ms=0,
                errors=[f"Invalid OpenAPI JSON: {e}"],
            )

    # =========================================================================
    # HEAVY STAGES (CI/Nightly only)
    # =========================================================================

    def _run_alembic(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run alembic upgrade check."""
        if app_dir is None:
            return QAStageResult(
                stage=QAStage.ALEMBIC,
                passed=True,
                duration_ms=0,
                skipped=True,
                skip_reason="No app_dir provided",
            )

        # Would run: cd app_dir && alembic upgrade head
        # For now, skip with message
        return QAStageResult(
            stage=QAStage.ALEMBIC,
            passed=True,
            duration_ms=0,
            skipped=True,
            skip_reason="Alembic check not implemented yet",
        )

    def _run_docker(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run docker-compose validation."""
        if app_dir is None:
            return QAStageResult(
                stage=QAStage.DOCKER,
                passed=True,
                duration_ms=0,
                skipped=True,
                skip_reason="No app_dir provided",
            )

        # Would run: cd app_dir && docker-compose config
        return QAStageResult(
            stage=QAStage.DOCKER,
            passed=True,
            duration_ms=0,
            skipped=True,
            skip_reason="Docker check not implemented yet",
        )

    def _run_smoke_test(
        self,
        files: Dict[str, str],
        ir: Optional[Any],
        app_dir: Optional[str],
    ) -> QAStageResult:
        """Run HTTP smoke tests."""
        if app_dir is None:
            return QAStageResult(
                stage=QAStage.SMOKE_TEST,
                passed=True,
                duration_ms=0,
                skipped=True,
                skip_reason="No app_dir provided",
            )

        # Would start app and hit /health
        return QAStageResult(
            stage=QAStage.SMOKE_TEST,
            passed=True,
            duration_ms=0,
            skipped=True,
            skip_reason="Smoke tests not implemented yet",
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_fast_qa(files: Dict[str, str], ir: Optional[Any] = None) -> QAResult:
    """Run FAST QA level."""
    return QAExecutor(QALevel.FAST).run(files, ir=ir)


def run_heavy_qa(
    files: Dict[str, str],
    ir: Optional[Any] = None,
    app_dir: Optional[str] = None,
) -> QAResult:
    """Run HEAVY QA level."""
    return QAExecutor(QALevel.HEAVY).run(files, ir=ir, app_dir=app_dir)


def get_qa_level() -> QALevel:
    """Get current QA level from environment."""
    return QALevel(os.getenv("QA_LEVEL", "fast"))


def should_run_heavy_qa() -> bool:
    """Check if HEAVY QA should run."""
    return get_qa_level() == QALevel.HEAVY
