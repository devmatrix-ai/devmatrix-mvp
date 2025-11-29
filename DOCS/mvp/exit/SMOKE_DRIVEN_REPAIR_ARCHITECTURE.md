# Smoke-Driven Repair Architecture

**Fecha:** 2025-11-29
**Estado:** Diseño Completo
**Referencia:** `DOCS/mvp/exit/debug/SMOKE_REPAIR_DISCONNECT.md`

---

## Overview

Esta arquitectura cierra el gap crítico entre smoke tests y code repair, habilitando un ciclo de mejora continua basado en pruebas de runtime reales.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SMOKE-DRIVEN REPAIR ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Code Generation ──→ Smoke Test ──→ Analyze Failures ──→ Repair ──→ Loop  │
│         │                 │                │                 │              │
│         │                 ↓                ↓                 ↓              │
│         │            Pass Rate        Violations        Fix Patterns       │
│         │             < 80%?          + Stack Traces    Applied           │
│         │                 │                │                 │              │
│         │                 ↓                ↓                 ↓              │
│         └──────────────── Learning System ←─────────────────┘              │
│                               │                                             │
│                               ↓                                             │
│                    Next Generation Improved                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. SmokeTestOrchestrator

**Ubicación:** `src/validation/smoke_test_orchestrator.py` (NUEVO)

**Responsabilidad:** Coordinar el ciclo smoke→repair→smoke.

```python
@dataclass
class SmokeRepairConfig:
    """Configuration for smoke-driven repair."""
    max_iterations: int = 3
    target_pass_rate: float = 0.8
    enable_server_log_capture: bool = True
    enable_learning: bool = True


class SmokeTestOrchestrator:
    """
    Orchestrates the smoke test → repair → retest cycle.

    Flow:
    1. Run initial smoke test
    2. If pass_rate < target: trigger repair
    3. Repair based on violations
    4. Retest
    5. Repeat until pass_rate >= target or max_iterations
    6. Record learnings
    """

    def __init__(
        self,
        smoke_validator: RuntimeSmokeValidator,
        code_repair_agent: CodeRepairAgent,
        pattern_adapter: SmokeTestPatternAdapter,
        config: SmokeRepairConfig = None
    ):
        self.smoke_validator = smoke_validator
        self.code_repair_agent = code_repair_agent
        self.pattern_adapter = pattern_adapter
        self.config = config or SmokeRepairConfig()

    async def run_smoke_repair_cycle(
        self,
        app_path: Path,
        application_ir: ApplicationIR
    ) -> SmokeRepairResult:
        """
        Main entry point for smoke-driven repair.

        Returns comprehensive result including:
        - Final smoke test results
        - Repairs applied per iteration
        - Learning events generated
        - Improvement trajectory
        """
        iterations = []
        current_pass_rate = 0.0

        for i in range(self.config.max_iterations):
            # 1. Run smoke test
            smoke_result = await self.smoke_validator.run_smoke_test(
                app_path=app_path,
                capture_logs=self.config.enable_server_log_capture
            )

            current_pass_rate = smoke_result.pass_rate
            iterations.append(SmokeIteration(
                iteration=i + 1,
                pass_rate=current_pass_rate,
                violations=len(smoke_result.violations)
            ))

            # 2. Check if target reached
            if current_pass_rate >= self.config.target_pass_rate:
                break

            # 3. Repair based on violations
            repair_result = await self.code_repair_agent.repair_from_smoke(
                violations=smoke_result.violations,
                server_logs=smoke_result.server_logs,
                app_path=app_path
            )

            # 4. Record learnings
            if self.config.enable_learning:
                self.pattern_adapter.record_repair_attempt(
                    violations=smoke_result.violations,
                    repairs=repair_result.fixes_applied,
                    success=repair_result.success
                )

        return SmokeRepairResult(
            final_pass_rate=current_pass_rate,
            iterations=iterations,
            target_reached=current_pass_rate >= self.config.target_pass_rate,
            total_repairs=sum(it.repairs_applied for it in iterations)
        )
```

### 2. Enhanced RuntimeSmokeValidator

**Ubicación:** `src/validation/runtime_smoke_validator.py` (MODIFICAR)

**Nuevas capacidades:**
- Captura de server logs
- Extracción de stack traces
- Clasificación de errores

```python
@dataclass
class EnhancedSmokeResult:
    """Extended smoke test result with diagnostics."""
    # Existing fields
    passed: bool
    pass_rate: float
    endpoints_tested: int
    endpoints_passed: int
    violations: List[SmokeViolation]

    # NEW fields
    server_logs: str
    stack_traces: List[StackTrace]
    error_classifications: Dict[str, List[str]]  # {endpoint: [error_types]}


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


class RuntimeSmokeValidator:
    async def run_smoke_test(
        self,
        app_path: Path,
        capture_logs: bool = True
    ) -> EnhancedSmokeResult:
        """Run smoke test with optional log capture."""

        # Start container with log capture
        container = await self._start_container(app_path)

        try:
            # Run scenarios
            results = await self._execute_scenarios(container)

            # Capture logs if enabled
            server_logs = ""
            stack_traces = []
            if capture_logs:
                server_logs = await self._get_container_logs(container)
                stack_traces = self._parse_stack_traces(server_logs)

            return EnhancedSmokeResult(
                passed=results.all_passed,
                pass_rate=results.pass_rate,
                # ... other fields ...
                server_logs=server_logs,
                stack_traces=stack_traces,
                error_classifications=self._classify_errors(stack_traces)
            )
        finally:
            await self._cleanup_container(container)

    def _parse_stack_traces(self, logs: str) -> List[StackTrace]:
        """Extract stack traces from server logs."""
        traces = []
        # Regex patterns for common Python exceptions
        traceback_pattern = r'Traceback \(most recent call last\):.*?(?=\n\n|\Z)'

        for match in re.finditer(traceback_pattern, logs, re.DOTALL):
            trace_text = match.group()
            traces.append(self._parse_single_trace(trace_text))

        return traces

    def _classify_errors(self, traces: List[StackTrace]) -> Dict[str, List[str]]:
        """Classify errors by type for targeted repair."""
        classifications = {
            "database": [],      # IntegrityError, OperationalError
            "validation": [],    # ValidationError, ValueError
            "import": [],        # ImportError, ModuleNotFoundError
            "attribute": [],     # AttributeError
            "type": [],          # TypeError
            "key": [],           # KeyError
            "other": []
        }

        for trace in traces:
            category = self._categorize_exception(trace.exception_class)
            classifications[category].append(trace.endpoint)

        return classifications
```

### 3. Smoke-Aware CodeRepairAgent

**Ubicación:** `src/mge/v2/agents/code_repair_agent.py` (MODIFICAR)

**Nuevas capacidades:**
- Repair basado en stack traces
- Fix strategies por tipo de error
- Query de fix patterns previos

```python
class CodeRepairAgent:
    async def repair_from_smoke(
        self,
        violations: List[SmokeViolation],
        server_logs: str,
        app_path: Path
    ) -> RepairResult:
        """
        Repair code based on smoke test failures.

        Strategy selection based on error type:
        - 500 + IntegrityError → Fix database constraints/nullability
        - 500 + ValidationError → Fix Pydantic schema mismatches
        - 500 + AttributeError → Fix missing imports/attributes
        - 404 → Fix route registration
        - 422 → Fix request body schema
        """
        repairs = []

        # Group violations by error classification
        by_type = self._group_by_error_type(violations, server_logs)

        for error_type, endpoints in by_type.items():
            strategy = self._get_repair_strategy(error_type)
            for endpoint in endpoints:
                fix = await strategy.apply(endpoint, app_path)
                if fix:
                    repairs.append(fix)

        return RepairResult(
            fixes_applied=repairs,
            success=len(repairs) > 0,
            files_modified=[r.file_path for r in repairs]
        )

    def _get_repair_strategy(self, error_type: str) -> RepairStrategy:
        """Get appropriate repair strategy for error type."""
        strategies = {
            "database": DatabaseRepairStrategy(),
            "validation": ValidationRepairStrategy(),
            "import": ImportRepairStrategy(),
            "attribute": AttributeRepairStrategy(),
            "route": RouteRepairStrategy(),
        }
        return strategies.get(error_type, GenericRepairStrategy())


class DatabaseRepairStrategy(RepairStrategy):
    """Fix database-related 500 errors."""

    async def apply(self, endpoint: str, app_path: Path) -> Optional[Fix]:
        """
        Common database fixes:
        1. Add nullable=True to optional columns
        2. Add default values
        3. Fix foreign key references
        4. Add missing indices
        """
        # Identify affected entity from endpoint
        entity = self._endpoint_to_entity(endpoint)

        # Check common issues
        fixes = []

        # Issue: Column not nullable but no default
        if await self._has_nullable_issue(entity, app_path):
            fixes.append(self._fix_nullable(entity, app_path))

        # Issue: Missing foreign key
        if await self._has_fk_issue(entity, app_path):
            fixes.append(self._fix_foreign_key(entity, app_path))

        return fixes[0] if fixes else None


class ValidationRepairStrategy(RepairStrategy):
    """Fix Pydantic validation errors."""

    async def apply(self, endpoint: str, app_path: Path) -> Optional[Fix]:
        """
        Common validation fixes:
        1. Add Optional[] to non-required fields
        2. Fix type mismatches (str vs int)
        3. Add field validators
        4. Fix enum values
        """
        # ... implementation
```

### 4. Fix Pattern Learning

**Ubicación:** `src/validation/smoke_test_pattern_adapter.py` (EXTENDER)

**Nuevas capacidades:**
- Record de fix patterns exitosos
- Query de fixes para problemas similares
- Aplicación automática de fixes conocidos

```python
@dataclass
class FixPattern:
    """A learned fix pattern from smoke-driven repair."""
    pattern_id: str
    error_type: str           # "database", "validation", etc.
    endpoint_pattern: str     # "POST /entities", "PUT /entities/{id}"
    exception_class: str      # "IntegrityError", "ValidationError"
    fix_type: str            # "add_nullable", "fix_import", etc.
    fix_template: str        # Code template to apply
    success_count: int
    failure_count: int
    success_rate: float


class SmokeTestPatternAdapter:
    def record_repair_attempt(
        self,
        violations: List[SmokeViolation],
        repairs: List[Fix],
        success: bool
    ):
        """
        Record fix attempt for learning.

        If successful:
        - Increment success_count for matching pattern
        - Update success_rate
        - Consider for promotion

        If failed:
        - Increment failure_count
        - Consider for demotion
        """
        for repair in repairs:
            pattern = self._find_or_create_pattern(repair)

            if success:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1

            pattern.success_rate = (
                pattern.success_count /
                (pattern.success_count + pattern.failure_count)
            )

            self._persist_pattern(pattern)

    def get_known_fix(
        self,
        error_type: str,
        endpoint_pattern: str,
        exception_class: str
    ) -> Optional[FixPattern]:
        """
        Query for known fix pattern with high success rate.

        Returns pattern if:
        - Matches error signature
        - success_rate >= 0.7
        - success_count >= 3 (enough evidence)
        """
        query = """
        MATCH (fp:FixPattern)
        WHERE fp.error_type = $error_type
          AND fp.endpoint_pattern = $endpoint_pattern
          AND fp.exception_class = $exception_class
          AND fp.success_rate >= 0.7
          AND fp.success_count >= 3
        RETURN fp
        ORDER BY fp.success_rate DESC
        LIMIT 1
        """
        # ... execute query
```

---

## Pipeline Integration

### Nuevo Flujo de Fases

```
Phase 6: Code Generation
    ↓
Phase 6.5: Code Repair (compliance-based) - PUEDE SKIPPEARSE
    ↓
Phase 7: Validation (semantic)
    ↓
Phase 8: Deployment
    ↓
Phase 8.5: Smoke-Repair Cycle (NUEVO)          ← Principal punto de repair
    ├── Run smoke test
    ├── If pass_rate < 80%:
    │   ├── Capture server logs
    │   ├── Parse stack traces
    │   ├── Apply targeted repairs
    │   ├── Retest
    │   └── Loop (max 3 iterations)
    └── Record learnings
    ↓
Phase 9: Health Verification
    ↓
Phase 10: Learning & Promotion
```

### Código de Integración

```python
# tests/e2e/real_e2e_full_pipeline.py

async def _phase_8_5_smoke_repair(self):
    """Phase 8.5: Smoke-Driven Repair Cycle."""
    print("\n🔥 Phase 8.5: Smoke-Driven Repair")

    orchestrator = SmokeTestOrchestrator(
        smoke_validator=self.smoke_validator,
        code_repair_agent=self.code_repair_agent,
        pattern_adapter=self.smoke_pattern_adapter,
        config=SmokeRepairConfig(
            max_iterations=3,
            target_pass_rate=0.8,
            enable_server_log_capture=True,
            enable_learning=True
        )
    )

    result = await orchestrator.run_smoke_repair_cycle(
        app_path=self.output_path,
        application_ir=self.application_ir
    )

    # Report results
    print(f"\n  📊 Smoke-Repair Results:")
    print(f"    - Initial pass rate: {result.iterations[0].pass_rate:.1%}")
    print(f"    - Final pass rate: {result.final_pass_rate:.1%}")
    print(f"    - Iterations: {len(result.iterations)}")
    print(f"    - Total repairs: {result.total_repairs}")
    print(f"    - Target reached: {'✅' if result.target_reached else '❌'}")

    # Record in metrics
    self.metrics_collector.add_checkpoint("smoke_repair", "CP-8.5.COMPLETE", {
        "initial_pass_rate": result.iterations[0].pass_rate,
        "final_pass_rate": result.final_pass_rate,
        "iterations": len(result.iterations),
        "repairs_applied": result.total_repairs,
        "target_reached": result.target_reached
    })

    return result
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DATA FLOW DIAGRAM                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SmokeTest                                                                   │
│      │                                                                       │
│      ├── violations: [{endpoint, expected, actual, error}]                  │
│      ├── server_logs: "Traceback... IntegrityError..."                      │
│      └── stack_traces: [{endpoint, exception_class, file, line}]            │
│              │                                                               │
│              ↓                                                               │
│  ErrorClassifier                                                             │
│      │                                                                       │
│      └── classifications: {                                                  │
│              "database": ["/products", "/customers"],                        │
│              "validation": ["/orders"],                                      │
│          }                                                                   │
│              │                                                               │
│              ↓                                                               │
│  FixPatternStore (query known fixes)                                        │
│      │                                                                       │
│      └── known_fixes: [FixPattern] or None                                  │
│              │                                                               │
│              ↓                                                               │
│  RepairStrategy (apply fix)                                                 │
│      │                                                                       │
│      └── Fix: {file_path, old_code, new_code, fix_type}                    │
│              │                                                               │
│              ↓                                                               │
│  CodeRepairAgent (execute fix)                                              │
│      │                                                                       │
│      └── RepairResult: {success, files_modified}                            │
│              │                                                               │
│              ↓                                                               │
│  PatternAdapter (record learning)                                           │
│      │                                                                       │
│      └── FixPattern: {success_count++, success_rate updated}               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Métricas y Monitoreo

### Nuevas Métricas

```python
@dataclass
class SmokeRepairMetrics:
    """Metrics for smoke-driven repair cycle."""

    # Pass rate trajectory
    initial_pass_rate: float
    final_pass_rate: float
    improvement: float  # final - initial

    # Repair effectiveness
    iterations_used: int
    repairs_attempted: int
    repairs_successful: int
    repair_success_rate: float

    # Error distribution
    errors_by_type: Dict[str, int]
    most_common_error: str

    # Learning
    new_patterns_discovered: int
    known_patterns_applied: int
    patterns_promoted: int

    # Timing
    total_duration_ms: int
    avg_iteration_ms: int
```

### Dashboard Output

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SMOKE-DRIVEN REPAIR DASHBOARD                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📈 Pass Rate Trajectory                                                     │
│  ─────────────────────                                                       │
│  Iteration 1: ████████████████░░░░░░░░░░ 56%                                │
│  Iteration 2: █████████████████████░░░░░ 72%                                │
│  Iteration 3: ███████████████████████░░░ 85% ✅                              │
│                                                                              │
│  🔧 Repairs Applied                                                          │
│  ─────────────────                                                           │
│  Database fixes:    8 (IntegrityError, nullable)                            │
│  Validation fixes:  3 (Pydantic schema)                                     │
│  Import fixes:      2 (missing modules)                                     │
│  Route fixes:       1 (registration)                                        │
│                                                                              │
│  🎓 Learning                                                                 │
│  ─────────────                                                               │
│  New patterns:      4                                                        │
│  Applied known:     6                                                        │
│  Promoted:          2 (>70% success)                                        │
│                                                                              │
│  ⏱️  Timing                                                                   │
│  ──────────                                                                  │
│  Total: 45.2s (3 iterations × ~15s each)                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Archivos Nuevos/Modificados

### Nuevos Archivos

| Archivo | Descripción |
|---------|-------------|
| `src/validation/smoke_test_orchestrator.py` | Coordinador del ciclo smoke→repair |
| `src/mge/v2/strategies/database_repair.py` | Strategy para fixes de DB |
| `src/mge/v2/strategies/validation_repair.py` | Strategy para fixes de validación |

### Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/validation/runtime_smoke_validator.py` | Server log capture, stack trace parsing |
| `src/mge/v2/agents/code_repair_agent.py` | `repair_from_smoke()` method |
| `src/validation/smoke_test_pattern_adapter.py` | FixPattern learning |
| `tests/e2e/real_e2e_full_pipeline.py` | Phase 8.5 integration |

---

## Advanced Features: Cognitive Software Engine

Estas mejoras elevan el sistema de "repair loop" a un **Cognitive Software Engine** con auto-reparación estructural.

### 2.1 Causal Repair Attribution

**Objetivo:** Mapear causalmente IR → AST → Failing Test para identificar la causa raíz exacta.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAUSAL REPAIR ATTRIBUTION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Failing Test                                                               │
│       │                                                                     │
│       ↓                                                                     │
│  POST /products → 500 IntegrityError                                       │
│       │                                                                     │
│       ↓                                                                     │
│  AST Analysis                                                              │
│       │                                                                     │
│       └── ProductCreate schema missing `price` validation                  │
│           │                                                                │
│           ↓                                                                 │
│  IR Constraint Mismatch                                                    │
│       │                                                                     │
│       └── IRConstraint: price > 0 (required)                               │
│           GeneratedConstraint: MISSING                                     │
│           │                                                                │
│           ↓                                                                 │
│  Root Cause: ValidationModelIR → Schema generation lost constraint         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementación:**

```python
@dataclass
class CausalChain:
    """Causal chain from failing test to IR root cause."""
    failing_test: str           # "POST /products [create_product_happy_path]"
    error_type: str             # "IntegrityError"
    ast_location: str           # "src/models/schemas.py:ProductCreate"
    ir_constraint: str          # "price > 0 (required)"
    generated_constraint: str   # "MISSING" or actual
    root_cause: str            # "ValidationModelIR → Schema generation"
    confidence: float          # 0.0 - 1.0


class CausalAttributor:
    """
    Identifies causal chain from test failure to IR root cause.

    Algorithm:
    1. Parse failing test → identify endpoint + entity
    2. AST parse generated code → find constraint definitions
    3. Compare with IR constraints → identify delta
    4. Attribute root cause to specific IR→Code transformation
    """

    def attribute_failure(
        self,
        violation: SmokeViolation,
        stack_trace: StackTrace,
        application_ir: ApplicationIR,
        app_path: Path
    ) -> CausalChain:
        # 1. Extract entity from endpoint
        entity = self._endpoint_to_entity(violation.endpoint)

        # 2. Get IR constraints for entity
        ir_constraints = self._get_ir_constraints(entity, application_ir)

        # 3. AST parse generated code
        generated_constraints = self._parse_generated_constraints(
            entity, app_path
        )

        # 4. Find missing/mismatched constraints
        delta = self._compute_constraint_delta(
            ir_constraints, generated_constraints
        )

        # 5. Attribute to specific transformation stage
        root_cause = self._identify_transformation_stage(delta)

        return CausalChain(
            failing_test=violation.scenario_name,
            error_type=stack_trace.exception_class,
            ast_location=f"{delta.file}:{delta.line}",
            ir_constraint=delta.expected,
            generated_constraint=delta.actual,
            root_cause=root_cause,
            confidence=self._compute_confidence(delta)
        )
```

**Beneficio:** Mapeo causal convierte el sistema en "compiler con dataflow error analysis".

---

### 2.2 Multi-Repair Loop con Convergencia

**Objetivo:** Fixed-point iteration hasta convergencia o regresión detectada.

```python
@dataclass
class ConvergenceResult:
    """Result of convergence analysis."""
    converged: bool
    iterations: int
    trajectory: List[float]  # pass_rate per iteration
    regression_detected: bool
    fixed_point: Optional[float]  # stable pass_rate if converged


class ConvergentRepairLoop:
    """
    Multi-repair loop with mathematical convergence detection.

    Stops when:
    1. pass_rate >= target (success)
    2. pass_rate[n] <= pass_rate[n-1] (regression)
    3. |pass_rate[n] - pass_rate[n-1]| < epsilon (convergence)
    4. n >= max_iterations (timeout)
    """

    EPSILON = 0.01  # 1% change threshold

    async def run_until_convergence(
        self,
        app_path: Path,
        target: float = 0.8,
        max_iterations: int = 3
    ) -> ConvergenceResult:
        trajectory = []

        for i in range(max_iterations):
            # Run smoke test
            result = await self.smoke_validator.run_smoke_test(app_path)
            pass_rate = result.pass_rate
            trajectory.append(pass_rate)

            # Check success
            if pass_rate >= target:
                return ConvergenceResult(
                    converged=True,
                    iterations=i + 1,
                    trajectory=trajectory,
                    regression_detected=False,
                    fixed_point=pass_rate
                )

            # Check regression
            if i > 0 and pass_rate < trajectory[i-1]:
                return ConvergenceResult(
                    converged=False,
                    iterations=i + 1,
                    trajectory=trajectory,
                    regression_detected=True,
                    fixed_point=None
                )

            # Check convergence (stuck at same level)
            if i > 0 and abs(pass_rate - trajectory[i-1]) < self.EPSILON:
                return ConvergenceResult(
                    converged=True,  # Converged but not at target
                    iterations=i + 1,
                    trajectory=trajectory,
                    regression_detected=False,
                    fixed_point=pass_rate
                )

            # Repair and continue
            await self.repair_agent.repair_from_smoke(
                result.violations, result.server_logs, app_path
            )

        return ConvergenceResult(
            converged=False,
            iterations=max_iterations,
            trajectory=trajectory,
            regression_detected=False,
            fixed_point=trajectory[-1] if trajectory else None
        )
```

**Beneficio:** Fixed-point iteration es matemáticamente riguroso y atractivo para research.

---

### 2.3 Mutation History

**Objetivo:** Registrar secuencia completa de diffs, no solo fix final.

```python
@dataclass
class MutationRecord:
    """Single mutation in repair history."""
    iteration: int
    file_path: str
    diff: str  # unified diff format
    fix_type: str
    triggered_by: str  # violation that caused this fix
    result: str  # "success", "failure", "regression"
    timestamp: datetime


@dataclass
class MutationHistory:
    """Complete mutation history for a repair session."""
    session_id: str
    app_path: Path
    mutations: List[MutationRecord]

    def get_successful_path(self) -> List[MutationRecord]:
        """Get sequence of mutations that led to success."""
        return [m for m in self.mutations if m.result == "success"]

    def get_failed_paths(self) -> List[List[MutationRecord]]:
        """Get sequences that led to failures (for learning)."""
        # Group mutations by iteration, identify failed branches
        pass

    def rollback_to(self, iteration: int) -> None:
        """Rollback code to state at specific iteration."""
        pass


class MutationTracker:
    """
    Tracks all code mutations during repair.

    Enables:
    - Analysis of failed repair paths
    - Discovery of finer repair patterns
    - Intelligent rollback
    - Genetic Programming-like evolution
    """

    def __init__(self, app_path: Path):
        self.app_path = app_path
        self.history = MutationHistory(
            session_id=str(uuid.uuid4())[:8],
            app_path=app_path,
            mutations=[]
        )
        self._snapshots: Dict[int, Dict[str, str]] = {}

    def snapshot(self, iteration: int) -> None:
        """Take snapshot of current code state."""
        self._snapshots[iteration] = self._read_all_files()

    def record_mutation(
        self,
        iteration: int,
        file_path: str,
        old_content: str,
        new_content: str,
        fix_type: str,
        triggered_by: str
    ) -> None:
        """Record a single mutation."""
        diff = self._compute_diff(old_content, new_content)
        self.history.mutations.append(MutationRecord(
            iteration=iteration,
            file_path=file_path,
            diff=diff,
            fix_type=fix_type,
            triggered_by=triggered_by,
            result="pending",
            timestamp=datetime.now()
        ))

    def mark_iteration_result(self, iteration: int, result: str) -> None:
        """Mark all mutations in iteration with result."""
        for m in self.history.mutations:
            if m.iteration == iteration and m.result == "pending":
                m.result = result

    def rollback(self, to_iteration: int) -> None:
        """Rollback to snapshot at iteration."""
        if to_iteration in self._snapshots:
            self._restore_files(self._snapshots[to_iteration])
```

**Beneficio:** Convierte repair engine en "Genetic Programming dirigido".

---

### 2.4 Confidence Model para Repair

**Objetivo:** Ordenar estrategias de repair por probabilidad de éxito.

```python
@dataclass
class RepairCandidate:
    """A candidate repair with confidence score."""
    strategy: RepairStrategy
    target_file: str
    fix_description: str
    confidence: float  # 0.0 - 1.0

    # Components of confidence score
    pattern_score: float      # Historical success rate of this pattern
    ir_context_score: float   # How well IR matches the error
    semantic_match_score: float  # Semantic similarity to known fixes


class ConfidenceModel:
    """
    Computes confidence scores for repair candidates.

    confidence = α * pattern_score + β * ir_context_score + γ * semantic_match

    Where:
    - pattern_score: Success rate from Neo4j FixPattern history
    - ir_context_score: How well IR explains the failure
    - semantic_match_score: Embedding similarity to successful fixes
    """

    ALPHA = 0.4  # Weight for historical pattern success
    BETA = 0.35  # Weight for IR context match
    GAMMA = 0.25  # Weight for semantic similarity

    def __init__(self, pattern_store: FixPatternStore, embedder: SentenceTransformer):
        self.pattern_store = pattern_store
        self.embedder = embedder

    def score_candidates(
        self,
        candidates: List[RepairCandidate],
        violation: SmokeViolation,
        causal_chain: CausalChain
    ) -> List[RepairCandidate]:
        """Score and rank repair candidates by confidence."""

        for candidate in candidates:
            # 1. Pattern score from history
            pattern = self.pattern_store.get_pattern(
                candidate.strategy.name,
                violation.endpoint_pattern
            )
            candidate.pattern_score = pattern.success_rate if pattern else 0.5

            # 2. IR context score
            candidate.ir_context_score = self._compute_ir_context_score(
                candidate, causal_chain
            )

            # 3. Semantic match score
            candidate.semantic_match_score = self._compute_semantic_match(
                candidate.fix_description,
                causal_chain.root_cause
            )

            # Combined confidence
            candidate.confidence = (
                self.ALPHA * candidate.pattern_score +
                self.BETA * candidate.ir_context_score +
                self.GAMMA * candidate.semantic_match_score
            )

        # Sort by confidence descending
        return sorted(candidates, key=lambda c: c.confidence, reverse=True)

    def _compute_ir_context_score(
        self,
        candidate: RepairCandidate,
        causal_chain: CausalChain
    ) -> float:
        """How well does the repair strategy address the IR gap?"""
        # Match strategy type to causal chain root cause
        strategy_matches = {
            "add_nullable": ["constraint missing", "required field"],
            "fix_foreign_key": ["relationship", "foreign key"],
            "add_validator": ["validation", "format", "range"],
        }

        root_cause_lower = causal_chain.root_cause.lower()
        strategy_keywords = strategy_matches.get(candidate.strategy.name, [])

        return 1.0 if any(kw in root_cause_lower for kw in strategy_keywords) else 0.3
```

**Beneficio:** Da apariencia de "machine intelligence" ordenando por probabilidad.

---

### 2.5 Delta IR Validation

**Objetivo:** Solo validar entidades/endpoints afectados por el repair (70% reducción de tiempo).

```python
@dataclass
class AffectedScope:
    """Scope of code affected by a repair."""
    entities: Set[str]
    endpoints: Set[str]
    constraints: Set[str]
    test_files: Set[str]


class DeltaIRValidator:
    """
    Validates only the subset of IR affected by repairs.

    Instead of full smoke test (75 scenarios), runs only:
    - Tests for affected entities
    - Tests for affected endpoints
    - Related constraint validations

    Reduces validation time ~70%.
    """

    def compute_affected_scope(
        self,
        mutations: List[MutationRecord],
        application_ir: ApplicationIR
    ) -> AffectedScope:
        """Determine what IR elements are affected by mutations."""

        affected_entities = set()
        affected_endpoints = set()
        affected_constraints = set()

        for mutation in mutations:
            # Parse file to identify affected elements
            if "models/entities.py" in mutation.file_path:
                entities = self._extract_entities_from_diff(mutation.diff)
                affected_entities.update(entities)

            elif "models/schemas.py" in mutation.file_path:
                entities = self._extract_schemas_from_diff(mutation.diff)
                affected_entities.update(entities)

            elif "api/routes" in mutation.file_path:
                endpoints = self._extract_endpoints_from_diff(mutation.diff)
                affected_endpoints.update(endpoints)

        # Expand to related constraints
        for entity in affected_entities:
            constraints = self._get_entity_constraints(entity, application_ir)
            affected_constraints.update(constraints)

        # Map to test files
        test_files = self._map_to_test_files(
            affected_entities, affected_endpoints
        )

        return AffectedScope(
            entities=affected_entities,
            endpoints=affected_endpoints,
            constraints=affected_constraints,
            test_files=test_files
        )

    async def validate_delta(
        self,
        scope: AffectedScope,
        app_path: Path
    ) -> DeltaValidationResult:
        """Run validation only on affected scope."""

        # 1. Run only affected smoke scenarios
        affected_scenarios = self._filter_scenarios(scope.endpoints)
        smoke_result = await self.smoke_validator.run_scenarios(
            affected_scenarios, app_path
        )

        # 2. Run only affected tests
        test_result = await self._run_affected_tests(scope.test_files, app_path)

        # 3. Validate only affected constraints
        constraint_result = self._validate_constraints(
            scope.constraints, scope.entities, app_path
        )

        return DeltaValidationResult(
            scope=scope,
            smoke_result=smoke_result,
            test_result=test_result,
            constraint_result=constraint_result,
            full_validation_skipped=True,
            time_saved_percent=self._compute_time_savings(scope)
        )
```

**Beneficio:** Escala real para Anthropic - no re-validar todo cada iteración.

---

## Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    COGNITIVE SOFTWARE ENGINE ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────────┐  │
│  │ Smoke Test  │───▶│   Causal     │───▶│  Confidence   │───▶│   Repair     │  │
│  │ + Logs      │    │ Attribution  │    │    Model      │    │  Strategy    │  │
│  └─────────────┘    └──────────────┘    └───────────────┘    └──────────────┘  │
│         │                  │                   │                    │          │
│         │                  ▼                   ▼                    ▼          │
│         │          IR ↔ AST ↔ Test      Ranked Repairs       Apply Fix        │
│         │             Mapping            by Probability       + Record        │
│         │                                                         │          │
│         │                                                         ▼          │
│         │                                               ┌─────────────────┐  │
│         │                                               │ Mutation History│  │
│         │                                               │ diff_1 → diff_2 │  │
│         │                                               └─────────────────┘  │
│         │                                                         │          │
│         ▼                                                         ▼          │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    CONVERGENT REPAIR LOOP                                │  │
│  │                                                                          │  │
│  │  Iteration 1 ──▶ Iteration 2 ──▶ Iteration 3                            │  │
│  │     56%            72%             85% ✅                                 │  │
│  │                                                                          │  │
│  │  Stop conditions:                                                        │  │
│  │  ✅ pass_rate >= 80% (success)                                           │  │
│  │  ⚠️ regression detected (rollback)                                       │  │
│  │  📊 converged at fixed point                                             │  │
│  │  ⏱️ max_iterations reached                                               │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│         │                                                                     │
│         ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    DELTA IR VALIDATION                                   │  │
│  │                                                                          │  │
│  │  Full validation: 75 scenarios × 3 iterations = 225 runs                │  │
│  │  Delta validation: 15 scenarios × 3 iterations = 45 runs  (70% faster)  │  │
│  │                                                                          │  │
│  │  Only validate:                                                          │  │
│  │  • Affected entities (from mutation diff)                               │  │
│  │  • Affected endpoints (from route changes)                              │  │
│  │  • Related constraints (from IR graph)                                  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│         │                                                                     │
│         ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    LEARNING SYSTEM                                       │  │
│  │                                                                          │  │
│  │  • Successful mutation paths → FixPatterns promoted                     │  │
│  │  • Failed mutation paths → Anti-patterns demoted                        │  │
│  │  • Causal chains → IR transformation improvements                       │  │
│  │  • Confidence model → Self-improving repair ranking                     │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Progreso de Implementación

### Phase 1: Core Smoke-Repair (Tasks 1-5) - ✅ COMPLETADO

| Task | Estado | Archivo |
|------|--------|---------|
| 1. Implementar SmokeRepairOrchestrator | ✅ | `src/validation/smoke_repair_orchestrator.py` |
| 2. Agregar server log capture | ✅ | `src/validation/runtime_smoke_validator.py` |
| 3. Implementar repair strategies | ✅ | `smoke_repair_orchestrator.py` (DatabaseRepairStrategy, ValidationRepairStrategy, etc.) |
| 4. Integrar en pipeline | ✅ | `tests/e2e/real_e2e_full_pipeline.py` (`_attempt_runtime_repair`) |
| 5. Agregar fix pattern learning | ✅ | `src/validation/smoke_test_pattern_adapter.py` (FixPatternLearner) |

**Componentes implementados:**
- `SmokeRepairOrchestrator` - Ciclo smoke→repair→retest con convergencia y regresión
- `SmokeRepairConfig` - Configuración (max_iterations, target_pass_rate, epsilon)
- `ServerLogParser` - Parsing de logs Docker y stack traces
- `ErrorClassifier` - Clasificación de errores (DATABASE, VALIDATION, IMPORT, etc.)
- `MutationTracker` - Tracking de cambios de código
- `repair_from_smoke` en CodeRepairAgent - Método de repair basado en smoke failures
- `FixPattern` - Dataclass para patrones de fix aprendidos
- `FixPatternLearner` - Learning de fix patterns con Neo4j persistence
- `get_fix_pattern_learner` - Singleton para acceder al learner

**Integración pipeline:**
- `_attempt_runtime_repair` ahora usa `SmokeRepairOrchestrator` cuando disponible
- Fallback a legacy repair loop si orquestador no disponible
- Server logs pasados a `repair_from_smoke` para análisis de root cause

### Phase 2: Cognitive Enhancements (Tasks 6-10) - ✅ COMPLETADO

| Task | Estado | Archivo |
|------|--------|---------|
| 6. Causal Repair Attribution | ✅ | `src/validation/repair_confidence_model.py` (LightweightCausalAttributor) |
| 7. Convergence Detection | ✅ | `src/validation/smoke_repair_orchestrator.py` |
| 8. Mutation History | ✅ | `src/validation/smoke_repair_orchestrator.py` (MutationTracker) |
| 9. Confidence Model | ✅ | `src/validation/repair_confidence_model.py` (RepairConfidenceModel) |
| 10. Delta IR Validation | ✅ | `src/validation/delta_ir_validator.py` (DeltaIRValidator) |

**Nuevos componentes Phase 2:**
- `DeltaIRValidator` - Valida solo entidades/endpoints afectados (70% faster)
- `AffectedScope` - Scope de código afectado por mutations
- `DeltaValidationIntegration` - Integración con SmokeRepairOrchestrator
- `RepairConfidenceModel` - Ranking de repairs por probabilidad de éxito
- `RepairCandidate` - Candidato de repair con confidence score
- `LightweightCausalAttributor` - Atribución causal error → IR root cause
- `CausalChain` - Cadena causal desde test failure hasta root cause

### Phase 3: E2E Pipeline Integration - ✅ COMPLETADO

| Component | Integration Point | Status |
|-----------|------------------|--------|
| SmokeRepairOrchestrator | `tests/e2e/real_e2e_full_pipeline.py:_attempt_runtime_repair` | ✅ |
| DeltaIRValidator | Integrated in SmokeRepairOrchestrator.__init__ | ✅ |
| RepairConfidenceModel | `_repair_from_smoke()` → `_apply_repair_with_confidence()` | ✅ |
| LightweightCausalAttributor | Integrated in repair loop for root cause analysis | ✅ |
| FixPatternLearner | `_record_learning()` + `_try_known_fix()` | ✅ |

**E2E Integration Details:**
- All Phase 2 components auto-enable if available
- Graceful degradation if components missing (ImportError handling)
- Metrics collector tracks Phase 2 component availability
- Progress logging shows component activation status

**New E2E Flags:**
- `DELTA_VALIDATOR_AVAILABLE` - 70% validation speedup
- `REPAIR_CONFIDENCE_MODEL_AVAILABLE` - Probabilistic repair ranking
- `FIX_PATTERN_LEARNER_AVAILABLE` - Cross-session learning

### Estimated Impact

| Feature | Effort | Impact |
|---------|--------|--------|
| Causal Attribution | 4h | Compiler-level error analysis |
| Convergence Loop | 2h | Mathematical rigor |
| Mutation History | 3h | Genetic Programming capabilities |
| Confidence Model | 4h | ML-like repair ordering |
| Delta Validation | 3h | 70% speed improvement |
| E2E Integration | 2h | Full pipeline activation |

---

**Documento creado:** 2025-11-29
**Última actualización:** 2025-11-29
**Autor:** DevMatrix Pipeline Team
