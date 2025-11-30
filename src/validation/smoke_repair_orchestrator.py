"""
Smoke Repair Orchestrator

Coordinates the smoke test → repair → retest cycle for runtime bug fixing.

This addresses the critical disconnect where:
- Code Repair uses semantic compliance (100%) → skips repair
- Smoke Test finds real bugs (56% pass rate) → too late

Architecture:
    Code Generation → Smoke Test → Analyze Failures → Repair → Loop
         │                │               │              │
         │                ↓               ↓              ↓
         │           Pass Rate       Violations      Fix Patterns
         │            < 80%?        + Stack Traces   Applied
         │                │               │              │
         └────────────── Learning System ←──────────────┘

Reference: DOCS/mvp/exit/SMOKE_DRIVEN_REPAIR_ARCHITECTURE.md
Created: 2025-11-29
"""
import asyncio
import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Phase 2 Components (Delta Validation, Confidence Model, Pattern Learning)
try:
    from src.validation.delta_ir_validator import (
        DeltaIRValidator,
        DeltaValidationIntegration,
        AffectedScope,
        MutationDiff,
        compute_repair_scope,
        should_run_full_validation
    )
    DELTA_VALIDATOR_AVAILABLE = True
except ImportError:
    DELTA_VALIDATOR_AVAILABLE = False
    DeltaIRValidator = None
    DeltaValidationIntegration = None
    AffectedScope = None
    MutationDiff = None

try:
    from src.validation.repair_confidence_model import (
        RepairConfidenceModel,
        LightweightCausalAttributor,
        RepairCandidate as ConfidenceCandidate,
        ConfidenceModelResult,
        CausalChain
    )
    CONFIDENCE_MODEL_AVAILABLE = True
except ImportError:
    CONFIDENCE_MODEL_AVAILABLE = False
    RepairConfidenceModel = None
    LightweightCausalAttributor = None
    ConfidenceCandidate = None

try:
    from src.validation.smoke_test_pattern_adapter import (
        FixPatternLearner,
        get_fix_pattern_learner,
        FixPattern
    )
    FIX_PATTERN_LEARNER_AVAILABLE = True
except ImportError:
    FIX_PATTERN_LEARNER_AVAILABLE = False
    FixPatternLearner = None
    get_fix_pattern_learner = None

# Generation Feedback Loop - NegativePatternStore for learned anti-patterns
try:
    from src.learning import (
        get_negative_pattern_store,
        NegativePatternStore,
        GenerationAntiPattern,
    )
    NEGATIVE_PATTERN_STORE_AVAILABLE = True
except ImportError:
    NEGATIVE_PATTERN_STORE_AVAILABLE = False
    get_negative_pattern_store = None
    NegativePatternStore = None
    GenerationAntiPattern = None


class RepairStrategyType(Enum):
    """Types of repair strategies based on error classification."""
    DATABASE = "database"
    VALIDATION = "validation"
    IMPORT = "import"
    ATTRIBUTE = "attribute"
    ROUTE = "route"
    TYPE = "type"
    KEY = "key"
    GENERIC = "generic"


@dataclass
class StackTrace:
    """Parsed stack trace from server logs."""
    endpoint: str
    error_type: str  # "500", "404", "422", "timeout"
    exception_class: str  # "IntegrityError", "ValidationError", etc.
    exception_message: str
    file_path: str
    line_number: int
    full_trace: str


@dataclass
class SmokeViolation:
    """A single smoke test violation with diagnostics."""
    endpoint: str
    method: str
    expected_status: int
    actual_status: int
    error_type: str
    error_message: str
    stack_trace: Optional[StackTrace] = None
    scenario_name: Optional[str] = None


@dataclass
class SmokeRepairConfig:
    """Configuration for smoke-driven repair."""
    max_iterations: int = 3
    target_pass_rate: float = 0.8
    enable_server_log_capture: bool = True
    enable_learning: bool = True
    convergence_epsilon: float = 0.01  # 1% change threshold


@dataclass
class SmokeIteration:
    """Result of a single smoke-repair iteration."""
    iteration: int
    pass_rate: float
    violations_count: int
    repairs_applied: int = 0
    repairs_successful: int = 0
    duration_ms: float = 0.0


@dataclass
class RepairCandidate:
    """A candidate repair with confidence score."""
    strategy_type: RepairStrategyType
    target_file: str
    fix_description: str
    confidence: float  # 0.0 - 1.0
    endpoint: str
    error_type: str


@dataclass
class RepairFix:
    """A fix that was applied."""
    file_path: str
    fix_type: str
    description: str
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    success: bool = True


@dataclass
class SmokeRepairResult:
    """Complete result of smoke-driven repair cycle."""
    final_pass_rate: float
    initial_pass_rate: float
    iterations: List[SmokeIteration]
    target_reached: bool
    total_repairs: int
    convergence_detected: bool = False
    regression_detected: bool = False
    fixes_applied: List[RepairFix] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class MutationRecord:
    """Single mutation in repair history."""
    iteration: int
    file_path: str
    diff: str
    fix_type: str
    triggered_by: str  # violation that caused this fix
    result: str  # "success", "failure", "regression"
    timestamp: datetime = field(default_factory=datetime.now)


class ServerLogParser:
    """Parses server logs to extract stack traces and error information."""

    # Regex patterns for Python exceptions
    TRACEBACK_PATTERN = re.compile(
        r'Traceback \(most recent call last\):.*?(?=\n\n|\Z)',
        re.DOTALL
    )

    FILE_LINE_PATTERN = re.compile(
        r'File "([^"]+)", line (\d+)'
    )

    EXCEPTION_PATTERN = re.compile(
        r'(\w+Error|\w+Exception):\s*(.+?)(?:\n|$)'
    )

    def parse_logs(self, logs: str) -> List[StackTrace]:
        """Extract all stack traces from server logs."""
        traces = []

        for match in self.TRACEBACK_PATTERN.finditer(logs):
            trace_text = match.group()
            trace = self._parse_single_trace(trace_text)
            if trace:
                traces.append(trace)

        return traces

    def _parse_single_trace(self, trace_text: str) -> Optional[StackTrace]:
        """Parse a single traceback into StackTrace."""
        # Extract file and line
        file_matches = list(self.FILE_LINE_PATTERN.finditer(trace_text))
        if file_matches:
            last_match = file_matches[-1]  # Most recent frame
            file_path = last_match.group(1)
            line_number = int(last_match.group(2))
        else:
            file_path = ""
            line_number = 0

        # Extract exception type and message
        exc_match = self.EXCEPTION_PATTERN.search(trace_text)
        if exc_match:
            exception_class = exc_match.group(1)
            exception_message = exc_match.group(2).strip()
        else:
            exception_class = "Unknown"
            exception_message = trace_text[:200]

        return StackTrace(
            endpoint="",  # Will be correlated later
            error_type="500",
            exception_class=exception_class,
            exception_message=exception_message,
            file_path=file_path,
            line_number=line_number,
            full_trace=trace_text
        )

    def classify_error(self, exception_class: str) -> RepairStrategyType:
        """Classify error to determine repair strategy."""
        exception_lower = exception_class.lower()

        if any(x in exception_lower for x in ['integrity', 'operational', 'database', 'sqlalchemy']):
            return RepairStrategyType.DATABASE
        elif any(x in exception_lower for x in ['validation', 'pydantic', 'value']):
            return RepairStrategyType.VALIDATION
        elif any(x in exception_lower for x in ['import', 'module']):
            return RepairStrategyType.IMPORT
        elif 'attribute' in exception_lower:
            return RepairStrategyType.ATTRIBUTE
        elif 'type' in exception_lower:
            return RepairStrategyType.TYPE
        elif 'key' in exception_lower:
            return RepairStrategyType.KEY
        else:
            return RepairStrategyType.GENERIC


class ErrorClassifier:
    """Classifies smoke test errors by type for targeted repair."""

    def __init__(self, log_parser: Optional[ServerLogParser] = None):
        self.log_parser = log_parser or ServerLogParser()

    def classify_violations(
        self,
        violations: List[Dict[str, Any]],
        stack_traces: List[StackTrace]
    ) -> Dict[RepairStrategyType, List[SmokeViolation]]:
        """
        Classify violations by error type for targeted repair.

        Returns dict mapping strategy type to list of violations.
        """
        classified: Dict[RepairStrategyType, List[SmokeViolation]] = {
            strategy: [] for strategy in RepairStrategyType
        }

        # Index stack traces by file for correlation
        traces_by_file = {}
        for trace in stack_traces:
            if trace.file_path:
                traces_by_file[trace.file_path] = trace

        for violation in violations:
            endpoint = violation.get('endpoint', '')
            error_type = violation.get('error_type', 'HTTP_500')
            status_code = violation.get('status_code', 500)
            stack_trace_obj = violation.get('stack_trace_obj')
            if isinstance(stack_trace_obj, dict):
                stack_trace_obj = StackTrace(
                    endpoint=stack_trace_obj.get("endpoint", endpoint),
                    error_type=stack_trace_obj.get("error_type", error_type),
                    exception_class=stack_trace_obj.get("exception_class", stack_trace_obj.get("error_type", "Unknown")),
                    exception_message=stack_trace_obj.get("exception_message", ""),
                    file_path=stack_trace_obj.get("file_path", stack_trace_obj.get("file", "")),
                    line_number=stack_trace_obj.get("line_number", stack_trace_obj.get("line", 0)),
                    full_trace=stack_trace_obj.get("full_trace", stack_trace_obj.get("stack_trace", ""))
                )

            # Determine strategy type
            if status_code == 404:
                strategy_type = RepairStrategyType.ROUTE
            elif status_code == 422:
                strategy_type = RepairStrategyType.VALIDATION
            elif error_type and error_type != 'HTTP_500':
                strategy_type = self.log_parser.classify_error(error_type)
            else:
                # Try to infer from stack trace
                file_path = violation.get('file', '')
                if file_path in traces_by_file:
                    trace = traces_by_file[file_path]
                    strategy_type = self.log_parser.classify_error(trace.exception_class)
                else:
                    strategy_type = RepairStrategyType.GENERIC

            smoke_violation = SmokeViolation(
                endpoint=endpoint,
                method=violation.get('method', 'GET'),
                expected_status=200,
                actual_status=status_code or 500,
                error_type=error_type,
                error_message=violation.get('error_message', ''),
                scenario_name=violation.get('scenario_name'),
                stack_trace=stack_trace_obj
            )

            classified[strategy_type].append(smoke_violation)

        return classified


class SmokeRepairOrchestrator:
    """
    Orchestrates the smoke test → repair → retest cycle.

    Flow:
    1. Run initial smoke test
    2. If pass_rate < target: trigger repair
    3. Repair based on violations
    4. Retest
    5. Repeat until pass_rate >= target or max_iterations
    6. Record learnings

    Cognitive Features:
    - Convergence detection (fixed-point iteration)
    - Regression detection (rollback)
    - Mutation history tracking
    - Delta validation (only affected entities)
    """

    def __init__(
        self,
        smoke_validator,  # RuntimeSmokeTestValidator
        code_repair_agent=None,  # CodeRepairAgent (optional)
        pattern_adapter=None,  # SmokeTestPatternAdapter for learning
        config: Optional[SmokeRepairConfig] = None
    ):
        self.smoke_validator = smoke_validator
        self.code_repair_agent = code_repair_agent
        self.pattern_adapter = pattern_adapter
        self.config = config or SmokeRepairConfig()

        # Internal components
        self.log_parser = ServerLogParser()
        self.error_classifier = ErrorClassifier(self.log_parser)

        # Mutation tracking
        self.mutation_history: List[MutationRecord] = []
        self._snapshots: Dict[int, Dict[str, str]] = {}

        # Phase 2: Delta Validation Integration
        self.delta_validator: Optional[DeltaIRValidator] = None
        if DELTA_VALIDATOR_AVAILABLE and DeltaIRValidator:
            self.delta_validator = DeltaIRValidator()
            logger.info("  ✅ Delta IR Validator enabled (70% validation speedup)")

        # Phase 2: Repair Confidence Model
        self.confidence_model: Optional[RepairConfidenceModel] = None
        self.causal_attributor: Optional[LightweightCausalAttributor] = None
        if CONFIDENCE_MODEL_AVAILABLE and RepairConfidenceModel:
            self.confidence_model = RepairConfidenceModel()
            self.causal_attributor = LightweightCausalAttributor()
            logger.info("  ✅ Repair Confidence Model enabled (probabilistic ranking)")

        # Phase 2: Fix Pattern Learning
        self.fix_pattern_learner: Optional[FixPatternLearner] = None
        if FIX_PATTERN_LEARNER_AVAILABLE and get_fix_pattern_learner:
            self.fix_pattern_learner = get_fix_pattern_learner()
            logger.info("  ✅ Fix Pattern Learner enabled (cross-session learning)")

    async def run_smoke_repair_cycle(
        self,
        app_path: Path,
        application_ir,
        capture_logs: bool = True
    ) -> SmokeRepairResult:
        """
        Main entry point for smoke-driven repair.

        Returns comprehensive result including:
        - Final smoke test results
        - Repairs applied per iteration
        - Learning events generated
        - Improvement trajectory
        """
        start_time = time.time()
        iterations: List[SmokeIteration] = []
        initial_pass_rate = 0.0
        current_pass_rate = 0.0
        total_repairs = 0
        all_fixes: List[RepairFix] = []
        convergence_detected = False
        regression_detected = False

        logger.info(f"🔄 Starting Smoke-Repair Cycle (max {self.config.max_iterations} iterations)")

        for i in range(self.config.max_iterations):
            iter_start = time.time()
            logger.info(f"\n  📍 Iteration {i + 1}/{self.config.max_iterations}")

            # 1. Take snapshot before repair (for potential rollback)
            self._take_snapshot(i, app_path)

            # 2. Run smoke test with log capture
            smoke_result = await self._run_smoke_test(app_path, application_ir, capture_logs)

            current_pass_rate = self._calculate_pass_rate(smoke_result)
            violations = smoke_result.violations

            if i == 0:
                initial_pass_rate = current_pass_rate

            logger.info(f"    📊 Pass rate: {current_pass_rate:.1%} ({smoke_result.endpoints_passed}/{smoke_result.endpoints_tested})")

            iteration = SmokeIteration(
                iteration=i + 1,
                pass_rate=current_pass_rate,
                violations_count=len(violations),
                duration_ms=(time.time() - iter_start) * 1000
            )

            # 3. Check success condition
            if current_pass_rate >= self.config.target_pass_rate:
                logger.info(f"    ✅ Target reached! ({self.config.target_pass_rate:.0%})")
                iterations.append(iteration)
                break

            # 4. Check regression (pass rate decreased)
            if i > 0 and current_pass_rate < iterations[-1].pass_rate:
                logger.warning(f"    ⚠️ Regression detected! {iterations[-1].pass_rate:.1%} → {current_pass_rate:.1%}")
                regression_detected = True
                # Rollback to previous state
                self._rollback_to(i - 1, app_path)
                current_pass_rate = iterations[-1].pass_rate
                iterations.append(iteration)
                break

            # 5. Check convergence (stuck at same level)
            if i > 0 and abs(current_pass_rate - iterations[-1].pass_rate) < self.config.convergence_epsilon:
                logger.info(f"    📈 Converged at {current_pass_rate:.1%} (delta < {self.config.convergence_epsilon:.1%})")
                convergence_detected = True
                iterations.append(iteration)
                break

            # 6. Parse server logs for stack traces
            stack_traces = []
            if capture_logs and hasattr(smoke_result, 'server_logs') and smoke_result.server_logs:
                stack_traces = self.log_parser.parse_logs(smoke_result.server_logs)
                logger.info(f"    🔍 Found {len(stack_traces)} stack traces in logs")

            # 7. Classify errors for targeted repair
            classified = self.error_classifier.classify_violations(violations, stack_traces)

            # Log error distribution
            for strategy_type, vios in classified.items():
                if vios:
                    logger.info(f"    📋 {strategy_type.value}: {len(vios)} violations")

            # 8. Repair based on classifications
            repair_result = await self._repair_from_smoke(
                classified,
                stack_traces,
                app_path,
                application_ir
            )

            iteration.repairs_applied = len(repair_result.get('fixes', []))
            iteration.repairs_successful = repair_result.get('successful', 0)
            total_repairs += iteration.repairs_applied
            all_fixes.extend(repair_result.get('fixes', []))

            logger.info(f"    🔧 Applied {iteration.repairs_applied} repairs ({iteration.repairs_successful} successful)")

            # 9. Record learnings
            if self.config.enable_learning and self.pattern_adapter:
                self._record_learning(
                    violations=violations,
                    repairs=repair_result.get('fixes', []),
                    iteration=i + 1
                )

            iterations.append(iteration)

        total_duration = (time.time() - start_time) * 1000

        result = SmokeRepairResult(
            final_pass_rate=current_pass_rate,
            initial_pass_rate=initial_pass_rate,
            iterations=iterations,
            target_reached=current_pass_rate >= self.config.target_pass_rate,
            total_repairs=total_repairs,
            convergence_detected=convergence_detected,
            regression_detected=regression_detected,
            fixes_applied=all_fixes,
            duration_ms=total_duration
        )

        # Log summary
        self._log_summary(result)

        return result

    async def _run_smoke_test(
        self,
        app_path: Path,
        application_ir,
        capture_logs: bool
    ):
        """Run smoke test with optional log capture."""
        # The RuntimeSmokeTestValidator already handles this
        return await self.smoke_validator.validate(application_ir)

    def _calculate_pass_rate(self, smoke_result) -> float:
        """Calculate pass rate from smoke result."""
        if smoke_result.endpoints_tested == 0:
            return 0.0
        return smoke_result.endpoints_passed / smoke_result.endpoints_tested

    async def _repair_from_smoke(
        self,
        classified: Dict[RepairStrategyType, List[SmokeViolation]],
        stack_traces: List[StackTrace],
        app_path: Path,
        application_ir
    ) -> Dict[str, Any]:
        """
        Repair code based on smoke test failures.

        Strategy selection based on error type:
        - DATABASE: Fix nullable, foreign keys, constraints
        - VALIDATION: Fix Pydantic schemas
        - IMPORT: Fix missing imports
        - ATTRIBUTE: Fix missing attributes
        - ROUTE: Fix route registration

        Phase 2 Enhancements:
        - FixPatternLearner: Check for known fixes first (skip LLM)
        - CausalAttributor: Map error → IR root cause
        - ConfidenceModel: Rank repair candidates by probability
        """
        fixes: List[RepairFix] = []
        successful = 0
        known_fixes_applied = 0

        for strategy_type, violations in classified.items():
            if not violations:
                continue

            for violation in violations:
                try:
                    # Phase 2: Check for known fix patterns first (saves LLM calls)
                    known_fix = self._try_known_fix(violation, stack_traces)
                    if known_fix:
                        fixes.append(known_fix)
                        if known_fix.success:
                            successful += 1
                            known_fixes_applied += 1
                        continue

                    # Phase 2: Get causal chain for better repair targeting
                    causal_chain = None
                    if self.causal_attributor:
                        matching_trace = self._find_matching_trace(violation, stack_traces)
                        trace_text = matching_trace.full_trace if matching_trace else None
                        causal_chain = self.causal_attributor.attribute_failure(
                            violation={'endpoint': violation.endpoint, 'error_type': violation.error_type},
                            stack_trace=trace_text,
                            application_ir=application_ir
                        )

                    # Phase 2: Score and rank repair candidates
                    fix = await self._apply_repair_with_confidence(
                        strategy_type,
                        violation,
                        stack_traces,
                        app_path,
                        application_ir,
                        causal_chain
                    )

                    if fix:
                        fixes.append(fix)
                        if fix.success:
                            successful += 1
                            # Record mutation
                            self.mutation_history.append(MutationRecord(
                                iteration=len(self._snapshots),
                                file_path=fix.file_path,
                                diff=f"-{fix.old_code or ''}\n+{fix.new_code or ''}",
                                fix_type=fix.fix_type,
                                triggered_by=violation.endpoint,
                                result="pending"
                            ))
                except Exception as e:
                    logger.error(f"Repair failed for {violation.endpoint}: {e}")

        if known_fixes_applied > 0:
            logger.info(f"    📚 Applied {known_fixes_applied} known fixes (skipped LLM)")

        return {
            'fixes': fixes,
            'successful': successful,
            'known_fixes': known_fixes_applied
        }

    def _try_known_fix(
        self,
        violation: SmokeViolation,
        stack_traces: List[StackTrace]
    ) -> Optional[RepairFix]:
        """
        Check if we have a known fix pattern for this violation.

        Uses FixPatternLearner to lookup previous successful repairs.
        """
        if not self.fix_pattern_learner:
            return None

        matching_trace = self._find_matching_trace(violation, stack_traces)
        exception_class = matching_trace.exception_class if matching_trace else "Unknown"

        known_pattern = self.fix_pattern_learner.get_known_fix(
            error_type=violation.error_type,
            endpoint=violation.endpoint,
            exception_class=exception_class
        )

        if known_pattern and known_pattern.success_rate > 0.7:
            logger.info(f"    📚 Found known fix for {violation.error_type} ({known_pattern.success_rate:.0%} success)")
            return RepairFix(
                file_path=known_pattern.target_file,
                fix_type=known_pattern.fix_type,
                description=f"Known fix: {known_pattern.description}",
                success=True
            )

        return None

    def _get_learned_antipatterns(
        self,
        violation: SmokeViolation,
        stack_traces: List[StackTrace]
    ) -> List[Dict[str, Any]]:
        """
        Query NegativePatternStore for anti-patterns relevant to this violation.

        Returns list of learned anti-patterns with their fixes.
        Used by Generation Feedback Loop to avoid repeating same mistakes.
        """
        if not NEGATIVE_PATTERN_STORE_AVAILABLE or not get_negative_pattern_store:
            return []

        antipatterns = []
        try:
            pattern_store = get_negative_pattern_store()

            # Extract entity from endpoint (e.g., "POST /products" -> "Product")
            entity_name = self._extract_entity_from_endpoint(violation.endpoint)

            # Query by entity
            if entity_name:
                entity_patterns = pattern_store.get_patterns_for_entity(entity_name)
                antipatterns.extend([{
                    "source": "entity",
                    "pattern_id": p.pattern_id,
                    "exception_class": p.exception_class,
                    "wrong_pattern": p.wrong_code_pattern,
                    "correct_pattern": p.correct_code_snippet,
                    "confidence": p.confidence,
                    "occurrences": p.occurrence_count
                } for p in entity_patterns[:3]])  # Top 3 per entity

            # Query by endpoint pattern
            endpoint_patterns = pattern_store.get_patterns_for_endpoint(violation.endpoint)
            antipatterns.extend([{
                "source": "endpoint",
                "pattern_id": p.pattern_id,
                "exception_class": p.exception_class,
                "wrong_pattern": p.wrong_code_pattern,
                "correct_pattern": p.correct_code_snippet,
                "confidence": p.confidence,
                "occurrences": p.occurrence_count
            } for p in endpoint_patterns[:3]])

            # Query by exception class
            matching_trace = self._find_matching_trace(violation, stack_traces)
            if matching_trace:
                exc_patterns = pattern_store.get_patterns_by_exception(
                    matching_trace.exception_class
                )
                antipatterns.extend([{
                    "source": "exception",
                    "pattern_id": p.pattern_id,
                    "exception_class": p.exception_class,
                    "wrong_pattern": p.wrong_code_pattern,
                    "correct_pattern": p.correct_code_snippet,
                    "confidence": p.confidence,
                    "occurrences": p.occurrence_count
                } for p in exc_patterns[:3]])

            # Deduplicate by pattern_id
            seen_ids = set()
            unique_patterns = []
            for p in antipatterns:
                if p["pattern_id"] not in seen_ids:
                    seen_ids.add(p["pattern_id"])
                    unique_patterns.append(p)

            if unique_patterns:
                logger.info(f"    🧠 Found {len(unique_patterns)} learned anti-patterns for repair guidance")

            return unique_patterns

        except Exception as e:
            logger.warning(f"Failed to query NegativePatternStore: {e}")
            return []

    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # "POST /products" -> "Product"
        # "PATCH /products/{id}/deactivate" -> "Product"
        parts = endpoint.split()
        if len(parts) < 2:
            return None

        path = parts[1]
        for segment in path.split('/'):
            if segment and not segment.startswith('{') and segment not in ['api', 'v1', 'v2']:
                # Convert plural to singular and capitalize
                entity = segment.rstrip('s').capitalize()
                return entity

        return None

    def _repair_with_learned_patterns(
        self,
        strategy_type: RepairStrategyType,
        violation: SmokeViolation,
        stack_traces: List[StackTrace],
        app_path: Path,
        application_ir,
        learned_patterns: List[Dict[str, Any]]
    ) -> Optional[RepairFix]:
        """
        Apply repair using learned anti-patterns as guidance.

        This method uses anti-patterns from NegativePatternStore to guide repairs:
        1. If a learned pattern matches, apply its correct_pattern directly
        2. If multiple patterns match, use highest confidence one
        3. Track pattern usage for learning feedback

        Returns:
            RepairFix if successful, None otherwise
        """
        if not learned_patterns:
            return None

        # Sort by confidence * occurrences (more proven patterns first)
        scored_patterns = sorted(
            learned_patterns,
            key=lambda p: p.get("confidence", 0) * p.get("occurrences", 1),
            reverse=True
        )

        best_pattern = scored_patterns[0]
        correct_code = best_pattern.get("correct_pattern", "")

        if not correct_code:
            return None

        # Determine target file based on pattern type
        target_file = self._determine_target_file(
            strategy_type, violation, app_path, best_pattern
        )

        if not target_file or not target_file.exists():
            return None

        # Apply the learned fix
        try:
            content = target_file.read_text()
            new_content = content

            wrong_pattern = best_pattern.get("wrong_pattern", "")

            # If we have a wrong pattern, try to replace it
            if wrong_pattern and wrong_pattern in content:
                new_content = content.replace(wrong_pattern, correct_code)
                fix_description = f"Applied learned fix: {best_pattern['exception_class']} → {correct_code[:50]}..."
            else:
                # Log but don't modify - pattern doesn't match this specific code
                logger.debug(f"Learned pattern exists but wrong_pattern not found in code")
                return None

            if new_content != content:
                target_file.write_text(new_content)

                # Update pattern store - increment prevention count
                if NEGATIVE_PATTERN_STORE_AVAILABLE and get_negative_pattern_store:
                    try:
                        store = get_negative_pattern_store()
                        store.increment_prevention(best_pattern["pattern_id"])
                    except Exception:
                        pass

                logger.info(f"    🎯 Applied learned anti-pattern fix (confidence: {best_pattern['confidence']:.2f})")

                return RepairFix(
                    file_path=str(target_file),
                    fix_type=f"learned_{strategy_type.value}",
                    description=fix_description,
                    old_code=wrong_pattern[:200] if wrong_pattern else "",
                    new_code=correct_code[:200],
                    success=True
                )

        except Exception as e:
            logger.warning(f"Failed to apply learned pattern: {e}")

        return None

    def _determine_target_file(
        self,
        strategy_type: RepairStrategyType,
        violation: SmokeViolation,
        app_path: Path,
        pattern: Dict[str, Any]
    ) -> Optional[Path]:
        """Determine target file for repair based on strategy and pattern."""
        if strategy_type == RepairStrategyType.DATABASE:
            return app_path / "src" / "models" / "entities.py"
        elif strategy_type == RepairStrategyType.VALIDATION:
            return app_path / "src" / "models" / "schemas.py"
        elif strategy_type == RepairStrategyType.ROUTE:
            entity = self._extract_entity_from_endpoint(violation.endpoint)
            if entity:
                return app_path / "src" / "api" / "routes" / f"{entity.lower()}.py"
        elif strategy_type == RepairStrategyType.IMPORT:
            # Try to infer from exception source
            exc_class = pattern.get("exception_class", "")
            if "service" in exc_class.lower():
                return app_path / "src" / "services"
            elif "repository" in exc_class.lower():
                return app_path / "src" / "repositories"

        # Default: try entities first
        return app_path / "src" / "models" / "entities.py"

    def _find_matching_trace(
        self,
        violation: SmokeViolation,
        stack_traces: List[StackTrace]
    ) -> Optional[StackTrace]:
        """Find stack trace matching the violation."""
        for trace in stack_traces:
            if violation.endpoint in trace.full_trace or violation.error_type in trace.exception_class:
                return trace
        return None

    async def _apply_repair_with_confidence(
        self,
        strategy_type: RepairStrategyType,
        violation: SmokeViolation,
        stack_traces: List[StackTrace],
        app_path: Path,
        application_ir,
        causal_chain=None
    ) -> Optional[RepairFix]:
        """
        Apply repair strategy with confidence-based ranking.

        Uses RepairConfidenceModel to score candidates before applying.
        """
        # Generate repair candidates
        candidates = self._generate_repair_candidates(
            strategy_type, violation, stack_traces, app_path
        )

        if not candidates:
            # Fallback to direct strategy
            return await self._apply_repair_strategy(
                strategy_type, violation, stack_traces, app_path, application_ir
            )

        # Score candidates with confidence model
        if self.confidence_model and len(candidates) > 1:
            violation_dict = {
                'endpoint': violation.endpoint,
                'error_type': violation.error_type,
                'status_code': violation.actual_status
            }

            confidence_result = self.confidence_model.score_candidates(
                candidates=candidates,
                violation=violation_dict,
                causal_chain=causal_chain,
                application_ir=application_ir
            )

            # Use top-ranked candidate
            if confidence_result.top_candidates:
                best = confidence_result.top_candidates[0]
                logger.info(f"    🎯 Selected repair: {best.fix_type} (confidence: {best.confidence:.2f})")

                # Apply the best candidate
                return await self._apply_repair_strategy(
                    strategy_type, violation, stack_traces, app_path, application_ir
                )

        # Direct application if no confidence model or single candidate
        return await self._apply_repair_strategy(
            strategy_type, violation, stack_traces, app_path, application_ir
        )

    def _generate_repair_candidates(
        self,
        strategy_type: RepairStrategyType,
        violation: SmokeViolation,
        stack_traces: List[StackTrace],
        app_path: Path
    ) -> List[Dict[str, Any]]:
        """Generate possible repair candidates for a violation."""
        candidates = []
        matching_trace = self._find_matching_trace(violation, stack_traces)

        # Base candidate from strategy type
        candidates.append({
            'strategy_type': strategy_type.value,
            'fix_type': strategy_type.value,
            'target_file': str(app_path / "src" / "models" / "entities.py"),
            'confidence': 0.5
        })

        # Add specific candidates based on strategy
        if strategy_type == RepairStrategyType.DATABASE and matching_trace:
            candidates.append({
                'strategy_type': 'nullable_fix',
                'fix_type': 'database',
                'target_file': str(app_path / "src" / "models" / "entities.py"),
                'confidence': 0.7
            })

        if strategy_type == RepairStrategyType.VALIDATION:
            candidates.append({
                'strategy_type': 'optional_field',
                'fix_type': 'validation',
                'target_file': str(app_path / "src" / "models" / "schemas.py"),
                'confidence': 0.65
            })

        return candidates

    async def _apply_repair_strategy(
        self,
        strategy_type: RepairStrategyType,
        violation: SmokeViolation,
        stack_traces: List[StackTrace],
        app_path: Path,
        application_ir
    ) -> Optional[RepairFix]:
        """Apply specific repair strategy based on error type."""

        # Find matching stack trace
        matching_trace = None
        for trace in stack_traces:
            if violation.endpoint in trace.full_trace or violation.error_type in trace.exception_class:
                matching_trace = trace
                break

        if strategy_type == RepairStrategyType.DATABASE:
            return await self._fix_database_error(violation, matching_trace, app_path)
        elif strategy_type == RepairStrategyType.VALIDATION:
            return await self._fix_validation_error(violation, matching_trace, app_path)
        elif strategy_type == RepairStrategyType.IMPORT:
            return await self._fix_import_error(violation, matching_trace, app_path)
        elif strategy_type == RepairStrategyType.ATTRIBUTE:
            return await self._fix_attribute_error(violation, matching_trace, app_path)
        elif strategy_type == RepairStrategyType.ROUTE:
            return await self._fix_route_error(violation, matching_trace, app_path)
        else:
            # Generic repair - delegate to code repair agent
            return await self._fix_generic_error(violation, matching_trace, app_path, application_ir)

    async def _fix_database_error(
        self,
        violation: SmokeViolation,
        trace: Optional[StackTrace],
        app_path: Path
    ) -> Optional[RepairFix]:
        """
        Fix database-related 500 errors.

        Common fixes:
        1. Add nullable=True to optional columns
        2. Add default values
        3. Fix foreign key references
        """
        if not trace:
            return None

        entities_file = app_path / "src" / "models" / "entities.py"
        if not entities_file.exists():
            return None

        content = entities_file.read_text()
        new_content = content
        fix_description = ""

        # Fix 1: NOT NULL constraint failed → add nullable=True
        if "NOT NULL" in trace.exception_message or "IntegrityError" in trace.exception_class:
            # Find the field mentioned in error
            field_match = re.search(r'column\s+["\']?(\w+)["\']?', trace.exception_message, re.IGNORECASE)
            if field_match:
                field_name = field_match.group(1)
                # Add nullable=True
                pattern = rf'(Column\([^)]*name=["\']?{field_name}["\']?[^)]*)\)'
                replacement = r'\1, nullable=True)'
                new_content = re.sub(pattern, replacement, new_content)
                fix_description = f"Added nullable=True to {field_name}"

        # Fix 2: Foreign key constraint → ensure cascade
        if "foreign key constraint" in trace.exception_message.lower():
            # Add ondelete CASCADE to foreign keys
            new_content = re.sub(
                r'(ForeignKey\([^)]+)\)',
                r'\1, ondelete="CASCADE")',
                new_content
            )
            fix_description = "Added ondelete CASCADE to foreign keys"

        if new_content != content:
            entities_file.write_text(new_content)
            return RepairFix(
                file_path=str(entities_file),
                fix_type="database",
                description=fix_description,
                old_code=content[:200],
                new_code=new_content[:200],
                success=True
            )

        return None

    async def _fix_validation_error(
        self,
        violation: SmokeViolation,
        trace: Optional[StackTrace],
        app_path: Path
    ) -> Optional[RepairFix]:
        """
        Fix Pydantic validation errors.

        Common fixes:
        1. Add Optional[] to non-required fields
        2. Fix type mismatches
        3. Add field validators
        """
        schemas_file = app_path / "src" / "models" / "schemas.py"
        if not schemas_file.exists():
            return None

        content = schemas_file.read_text()
        new_content = content
        fix_description = ""

        if trace and "ValidationError" in trace.exception_class:
            # Find missing field and make it Optional
            field_match = re.search(r'field required.*?["\'](\w+)["\']', trace.exception_message, re.IGNORECASE)
            if field_match:
                field_name = field_match.group(1)
                # Change field: Type to field: Optional[Type] = None
                pattern = rf'(\s+{field_name}:\s*)(\w+)(\s*(?:=|$))'
                replacement = rf'\1Optional[\2] = None'
                new_content = re.sub(pattern, replacement, new_content)
                fix_description = f"Made {field_name} optional"

                # Add Optional import if needed
                if "Optional" not in new_content and "from typing" in new_content:
                    new_content = new_content.replace(
                        "from typing import",
                        "from typing import Optional, "
                    )

        if new_content != content:
            schemas_file.write_text(new_content)
            return RepairFix(
                file_path=str(schemas_file),
                fix_type="validation",
                description=fix_description,
                old_code=content[:200],
                new_code=new_content[:200],
                success=True
            )

        return None

    async def _fix_import_error(
        self,
        violation: SmokeViolation,
        trace: Optional[StackTrace],
        app_path: Path
    ) -> Optional[RepairFix]:
        """Fix import-related errors."""
        if not trace or not trace.file_path:
            return None

        # Find the file with the import error
        file_path = app_path / trace.file_path.replace(str(app_path), "").lstrip("/")
        if not file_path.exists():
            file_path = app_path / "src" / trace.file_path.split("src/")[-1] if "src/" in trace.file_path else None

        if not file_path or not file_path.exists():
            return None

        content = file_path.read_text()
        new_content = content
        fix_description = ""

        # Extract missing module from error
        module_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", trace.exception_message)
        if module_match:
            missing_module = module_match.group(1)
            # Try to add a fallback import
            fix_description = f"Added try/except for {missing_module}"
            # For now, just log - actual fix would need LLM

        # Extract missing name from error
        name_match = re.search(r"cannot import name ['\"](\w+)['\"]", trace.exception_message)
        if name_match:
            missing_name = name_match.group(1)
            fix_description = f"Missing import: {missing_name}"

        return RepairFix(
            file_path=str(file_path),
            fix_type="import",
            description=fix_description,
            success=False  # Import fixes usually need manual intervention
        )

    async def _fix_attribute_error(
        self,
        violation: SmokeViolation,
        trace: Optional[StackTrace],
        app_path: Path
    ) -> Optional[RepairFix]:
        """Fix AttributeError - missing attributes on objects."""
        if not trace:
            return None

        # Extract attribute name from error
        attr_match = re.search(r"has no attribute ['\"](\w+)['\"]", trace.exception_message)
        if not attr_match:
            return None

        missing_attr = attr_match.group(1)

        return RepairFix(
            file_path=trace.file_path,
            fix_type="attribute",
            description=f"Missing attribute: {missing_attr}",
            success=False  # Attribute fixes need context
        )

    async def _fix_route_error(
        self,
        violation: SmokeViolation,
        trace: Optional[StackTrace],
        app_path: Path
    ) -> Optional[RepairFix]:
        """Fix 404 route not found errors."""
        # Extract entity from endpoint path
        path_parts = violation.endpoint.split()
        if len(path_parts) < 2:
            return None

        method = path_parts[0]
        path = path_parts[1]

        # Determine route file
        entity = None
        for part in path.split('/'):
            if part and not part.startswith('{') and part not in ['api', 'v1', 'v2']:
                entity = part.rstrip('s')  # products -> product
                break

        if not entity:
            return None

        route_file = app_path / "src" / "api" / "routes" / f"{entity}.py"

        return RepairFix(
            file_path=str(route_file),
            fix_type="route",
            description=f"Missing route: {method} {path}",
            success=False  # Route additions need LLM
        )

    async def _fix_generic_error(
        self,
        violation: SmokeViolation,
        trace: Optional[StackTrace],
        app_path: Path,
        application_ir
    ) -> Optional[RepairFix]:
        """Fallback: delegate to code repair agent."""
        # This would use the LLM-based repair in CodeRepairAgent
        return RepairFix(
            file_path=trace.file_path if trace else "",
            fix_type="generic",
            description=f"Generic error on {violation.endpoint}: {violation.error_type}",
            success=False
        )

    def _take_snapshot(self, iteration: int, app_path: Path) -> None:
        """Take snapshot of current code state for potential rollback."""
        snapshot = {}
        for py_file in app_path.rglob("*.py"):
            try:
                rel_path = str(py_file.relative_to(app_path))
                snapshot[rel_path] = py_file.read_text()
            except Exception:
                pass
        self._snapshots[iteration] = snapshot

    def _rollback_to(self, iteration: int, app_path: Path) -> None:
        """Rollback to snapshot at specific iteration."""
        if iteration not in self._snapshots:
            logger.warning(f"No snapshot at iteration {iteration}")
            return

        logger.info(f"    🔄 Rolling back to iteration {iteration}")
        snapshot = self._snapshots[iteration]

        for rel_path, content in snapshot.items():
            file_path = app_path / rel_path
            try:
                file_path.write_text(content)
            except Exception as e:
                logger.error(f"Rollback failed for {rel_path}: {e}")

        # Mark mutations as reverted
        for mutation in self.mutation_history:
            if mutation.iteration > iteration:
                mutation.result = "reverted"

    def _record_learning(
        self,
        violations: List[Dict[str, Any]],
        repairs: List[RepairFix],
        iteration: int
    ) -> None:
        """
        Record learning from this iteration.

        Uses FixPatternLearner (Phase 2) for cross-session pattern storage.
        Falls back to pattern_adapter for backward compatibility.
        """
        # Phase 2: Use FixPatternLearner for persistent learning
        if self.fix_pattern_learner:
            try:
                # Determine if iteration was successful overall
                success = len([r for r in repairs if r.success]) > len(repairs) // 2

                # Convert repairs to structured payload for FixPatternLearner.
                repair_descriptions = []
                for r in repairs:
                    payload = {
                        "fix_type": getattr(r, "fix_type", "generic"),
                        "description": getattr(r, "description", ""),
                        "file_path": getattr(r, "file_path", ""),
                        "success": getattr(r, "success", False),
                    }
                    repair_descriptions.append(payload)

                record_id = self.fix_pattern_learner.record_repair_attempt(
                    violations=violations,
                    repairs=repair_descriptions,
                    success=success,
                    iteration=iteration
                )
                logger.info(f"    📝 Recorded repair attempt #{record_id} to FixPatternLearner")
            except Exception as e:
                logger.warning(f"FixPatternLearner recording failed: {e}")

        # Backward compatibility: also use pattern_adapter if available
        if self.pattern_adapter:
            try:
                for repair in repairs:
                    if repair.success:
                        self.pattern_adapter.record_successful_fix({
                            'fix_type': repair.fix_type,
                            'file_path': repair.file_path,
                            'description': repair.description
                        })
            except Exception as e:
                logger.warning(f"Pattern adapter recording failed: {e}")

    def _log_summary(self, result: SmokeRepairResult) -> None:
        """Log comprehensive summary of repair cycle."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 SMOKE-REPAIR CYCLE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Initial pass rate: {result.initial_pass_rate:.1%}")
        logger.info(f"  Final pass rate:   {result.final_pass_rate:.1%}")
        logger.info(f"  Improvement:       +{(result.final_pass_rate - result.initial_pass_rate):.1%}")
        logger.info(f"  Iterations:        {len(result.iterations)}")
        logger.info(f"  Total repairs:     {result.total_repairs}")
        logger.info(f"  Target reached:    {'✅' if result.target_reached else '❌'}")

        if result.convergence_detected:
            logger.info("  ⚠️ Convergence detected (no further improvement)")
        if result.regression_detected:
            logger.info("  ⚠️ Regression detected (rolled back)")

        logger.info(f"  Duration:          {result.duration_ms:.0f}ms")
        logger.info("=" * 60)

    async def _rebuild_docker_no_cache(
        self,
        app_path: Path,
        container_name: Optional[str] = None
    ) -> bool:
        """
        Rebuild Docker container without cache after code repairs.

        This is critical for the Smoke-Driven Repair Loop because:
        1. Docker layers cache old code - repairs won't take effect
        2. --no-cache ensures fresh build with repaired code
        3. Restart container to pick up changes

        Args:
            app_path: Path to the generated app
            container_name: Optional container name (defaults to app folder name)

        Returns:
            True if rebuild successful, False otherwise
        """
        if not container_name:
            container_name = app_path.name

        logger.info(f"    🐳 Rebuilding Docker (--no-cache) for {container_name}...")

        try:
            # Stop existing container
            stop_result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Remove container
            subprocess.run(
                ["docker", "rm", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Rebuild with --no-cache
            build_result = subprocess.run(
                ["docker", "build", "--no-cache", "-t", container_name, "."],
                cwd=str(app_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout for build
            )

            if build_result.returncode != 0:
                logger.error(f"Docker build failed: {build_result.stderr[:500]}")
                return False

            logger.info(f"    ✅ Docker rebuild complete")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Docker rebuild timed out")
            return False
        except FileNotFoundError:
            logger.warning("Docker not available - skipping rebuild")
            return True  # Continue without Docker
        except Exception as e:
            logger.error(f"Docker rebuild failed: {e}")
            return False

    async def _restart_container(
        self,
        app_path: Path,
        container_name: Optional[str] = None,
        port: int = 8002
    ) -> bool:
        """
        Restart the Docker container after rebuild.

        Args:
            app_path: Path to the generated app
            container_name: Optional container name
            port: Port to expose (default 8002)

        Returns:
            True if container started successfully
        """
        if not container_name:
            container_name = app_path.name

        try:
            # Run new container
            run_result = subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", container_name,
                    "-p", f"{port}:{port}",
                    "-e", "DATABASE_URL=sqlite:///./test.db",
                    container_name
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if run_result.returncode != 0:
                logger.error(f"Docker run failed: {run_result.stderr[:500]}")
                return False

            # Wait for container to be ready
            await asyncio.sleep(3)

            logger.info(f"    ✅ Container {container_name} restarted on port {port}")
            return True

        except Exception as e:
            logger.error(f"Container restart failed: {e}")
            return False

    async def run_full_repair_cycle(
        self,
        app_path: Path,
        application_ir,
        with_docker_rebuild: bool = True,
        max_cycles: int = 3
    ) -> SmokeRepairResult:
        """
        Full repair cycle with Docker rebuild integration.

        This is the enhanced version of run_smoke_repair_cycle that:
        1. Runs smoke tests
        2. Applies repairs using learned patterns first
        3. Rebuilds Docker --no-cache
        4. Re-runs smoke tests
        5. Loops until target or convergence

        Args:
            app_path: Path to generated app
            application_ir: ApplicationIR for context
            with_docker_rebuild: Whether to rebuild Docker (default True)
            max_cycles: Maximum repair cycles (default 3)

        Returns:
            SmokeRepairResult with comprehensive metrics
        """
        start_time = time.time()
        all_iterations: List[SmokeIteration] = []
        initial_pass_rate = 0.0
        current_pass_rate = 0.0
        total_repairs = 0
        all_fixes: List[RepairFix] = []
        convergence_detected = False
        regression_detected = False
        learned_patterns_applied = 0

        logger.info(f"🔄 Starting Full Smoke-Repair Cycle (max {max_cycles} cycles, Docker rebuild: {with_docker_rebuild})")

        for cycle in range(max_cycles):
            cycle_start = time.time()
            logger.info(f"\n  🔁 Cycle {cycle + 1}/{max_cycles}")

            # 1. Take snapshot
            self._take_snapshot(cycle, app_path)

            # 2. Run smoke test
            smoke_result = await self._run_smoke_test(app_path, application_ir, True)
            current_pass_rate = self._calculate_pass_rate(smoke_result)
            violations = smoke_result.violations

            if cycle == 0:
                initial_pass_rate = current_pass_rate

            logger.info(f"    📊 Pass rate: {current_pass_rate:.1%} ({smoke_result.endpoints_passed}/{smoke_result.endpoints_tested})")

            # 3. Check success
            if current_pass_rate >= self.config.target_pass_rate:
                logger.info(f"    ✅ Target reached!")
                all_iterations.append(SmokeIteration(
                    iteration=cycle + 1,
                    pass_rate=current_pass_rate,
                    violations_count=len(violations),
                    duration_ms=(time.time() - cycle_start) * 1000
                ))
                break

            # 4. Check regression
            if cycle > 0 and current_pass_rate < all_iterations[-1].pass_rate - self.config.convergence_epsilon:
                logger.warning(f"    ⚠️ Regression detected! Rolling back...")
                regression_detected = True
                self._rollback_to(cycle - 1, app_path)
                break

            # 5. Check convergence
            if cycle > 0 and abs(current_pass_rate - all_iterations[-1].pass_rate) < self.config.convergence_epsilon:
                logger.info(f"    📈 Converged at {current_pass_rate:.1%}")
                convergence_detected = True
                all_iterations.append(SmokeIteration(
                    iteration=cycle + 1,
                    pass_rate=current_pass_rate,
                    violations_count=len(violations),
                    duration_ms=(time.time() - cycle_start) * 1000
                ))
                break

            # 6. Parse logs
            stack_traces = []
            if hasattr(smoke_result, 'server_logs') and smoke_result.server_logs:
                stack_traces = self.log_parser.parse_logs(smoke_result.server_logs)
                logger.info(f"    🔍 Found {len(stack_traces)} stack traces")

            # 7. Classify errors
            classified = self.error_classifier.classify_violations(violations, stack_traces)

            # 8. Apply repairs with learned patterns priority
            cycle_fixes = []
            cycle_successful = 0

            for strategy_type, vios in classified.items():
                if not vios:
                    continue

                for violation in vios:
                    # Try learned patterns first
                    learned = self._get_learned_antipatterns(violation, stack_traces)
                    if learned:
                        fix = self._repair_with_learned_patterns(
                            strategy_type, violation, stack_traces,
                            app_path, application_ir, learned
                        )
                        if fix and fix.success:
                            cycle_fixes.append(fix)
                            cycle_successful += 1
                            learned_patterns_applied += 1
                            continue

                    # Fallback to regular repair
                    fix = await self._apply_repair_with_confidence(
                        strategy_type, violation, stack_traces,
                        app_path, application_ir, None
                    )
                    if fix:
                        cycle_fixes.append(fix)
                        if fix.success:
                            cycle_successful += 1

            total_repairs += len(cycle_fixes)
            all_fixes.extend(cycle_fixes)

            logger.info(f"    🔧 Applied {len(cycle_fixes)} repairs ({learned_patterns_applied} from learned patterns)")

            # 9. Rebuild Docker if repairs were made
            if with_docker_rebuild and cycle_fixes:
                rebuild_ok = await self._rebuild_docker_no_cache(app_path)
                if rebuild_ok:
                    await self._restart_container(app_path)

            # 10. Record learning
            if self.config.enable_learning:
                self._record_learning(violations, cycle_fixes, cycle + 1)

            all_iterations.append(SmokeIteration(
                iteration=cycle + 1,
                pass_rate=current_pass_rate,
                violations_count=len(violations),
                repairs_applied=len(cycle_fixes),
                repairs_successful=cycle_successful,
                duration_ms=(time.time() - cycle_start) * 1000
            ))

        total_duration = (time.time() - start_time) * 1000

        result = SmokeRepairResult(
            final_pass_rate=current_pass_rate,
            initial_pass_rate=initial_pass_rate,
            iterations=all_iterations,
            target_reached=current_pass_rate >= self.config.target_pass_rate,
            total_repairs=total_repairs,
            convergence_detected=convergence_detected,
            regression_detected=regression_detected,
            fixes_applied=all_fixes,
            duration_ms=total_duration
        )

        self._log_summary(result)
        logger.info(f"  🧠 Learned patterns applied: {learned_patterns_applied}")

        return result


# Convenience function
async def run_smoke_repair_cycle(
    app_path: Path,
    application_ir,
    smoke_validator,
    code_repair_agent,
    pattern_adapter=None,
    config: Optional[SmokeRepairConfig] = None
) -> SmokeRepairResult:
    """
    Convenience function to run smoke-driven repair cycle.

    Usage:
        result = await run_smoke_repair_cycle(
            app_path=Path("generated_app/"),
            application_ir=ir,
            smoke_validator=validator,
            code_repair_agent=repair_agent
        )
        print(f"Final pass rate: {result.final_pass_rate:.1%}")
    """
    orchestrator = SmokeRepairOrchestrator(
        smoke_validator=smoke_validator,
        code_repair_agent=code_repair_agent,
        pattern_adapter=pattern_adapter,
        config=config
    )

    return await orchestrator.run_smoke_repair_cycle(
        app_path=app_path,
        application_ir=application_ir
    )
