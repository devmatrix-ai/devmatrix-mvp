# Pipeline Refactoring Plan: Complete Migration to /src/pipeline

**Status**: DRAFT v2 (FULL MIGRATION - 100% code moved to src/)
**Created**: 2025-11-28
**Branch Base**: `feature/validation-scaling-phase1`
**Goal**: Move ALL 5,275 lines from `tests/e2e/real_e2e_full_pipeline.py` to `/src/pipeline/*`

---

## Phase Execution Plan (6 Phases - Complete Migration)

### Phase 1: Foundation (IR + Utils)
**Branch**: `feature/pipeline-refactor-full/phase1-foundation`
**Effort**: 4-5 hours
**Risk**: LOW
**Lines Migrated**: ~350 lines

#### Deliverables
1. **Create `/src/pipeline/ir/extractor.py`**
   - `IRExtractor` class (6 methods)
   - Migrate all `_get_*_from_ir()` methods

2. **Create `/src/pipeline/utils/`**
   - `logging_filters.py`: `ErrorPatternStoreFilter` + `apply_error_pattern_filter()`
   - `logging_context.py`: `silent_logs()` context manager
   - `progress_display.py`: `animated_progress_bar()`
   - `performance_monitor.py`: `PerformanceMonitor` class

3. **Create `/tests/e2e/test_pipeline_foundation.py`**
   - Unit tests for `IRExtractor`
   - Unit tests for all utilities

4. **Update `/tests/e2e/real_e2e_full_pipeline.py`**
   - Import from `/src/pipeline/ir/` and `/src/pipeline/utils/`
   - Remove migrated code
   - Verify E2E test still passes

#### Acceptance Criteria
- [ ] All foundation modules in `/src/pipeline/`
- [ ] Unit tests >85% coverage
- [ ] E2E test passes with identical metrics
- [ ] No performance regression

---

### Phase 2: Core Support (Parsers + Stratum)
**Branch**: `feature/pipeline-refactor-full/phase2-support`
**Effort**: 3-4 hours
**Risk**: LOW-MEDIUM
**Lines Migrated**: ~250 lines

#### Deliverables
1. **Create `/src/pipeline/parsers/`**
   - `markdown_code.py`: `MarkdownCodeParser`
   - `python_atoms.py`: `PythonAtomExtractor`

2. **Create `/src/pipeline/stratum/`**
   - `patterns.py`: Centralized stratum pattern definitions
   - `classifier.py`: `StratumClassifier` class
   - `recorder.py`: Manifest recording logic (from `_record_file_in_manifest`)

3. **Create `/tests/e2e/test_pipeline_support.py`**
   - Tests for parsers (happy path + edge cases)
   - Tests for stratum classification

4. **Update E2E test**
   - Use parsers and stratum from `/src/pipeline/`
   - Remove migrated code

#### Acceptance Criteria
- [ ] Parsers handle all markdown formats correctly
- [ ] Stratum classifier matches all existing patterns
- [ ] Unit tests >90% coverage
- [ ] E2E test passes

---

### Phase 3: Display Layer
**Branch**: `feature/pipeline-refactor-full/phase3-display`
**Effort**: 3-4 hours
**Risk**: LOW
**Lines Migrated**: ~300 lines

#### Deliverables
1. **Create `/src/pipeline/display/`**
   - `phase_summary.py`: All `_display_phase_*_summary()` methods
   - `final_report.py`: `_print_report()` final report generation

2. **Create `/src/pipeline/display/formatters.py`**
   - Common formatting utilities (ASCII tables, progress bars, etc.)

3. **Create `/tests/e2e/test_pipeline_display.py`**
   - Tests for summary displays
   - Tests for final report generation

4. **Update E2E test**
   - Use display utilities from `/src/pipeline/`
   - Remove migrated display code

#### Acceptance Criteria
- [ ] All display methods in `/src/pipeline/display/`
- [ ] Output format matches original exactly
- [ ] Unit tests >80% coverage
- [ ] E2E test output visually identical

---

### Phase 4: Phase Helpers
**Branch**: `feature/pipeline-refactor-full/phase4-helpers`
**Effort**: 5-6 hours
**Risk**: MEDIUM-HIGH
**Lines Migrated**: ~800 lines

#### Deliverables
1. **Create phase helper modules**:
   - `/src/pipeline/phases/phase_2_helpers.py`:
     - `match_patterns_real()`
     - `match_patterns_simple()`

   - `/src/pipeline/phases/phase_6_helpers.py`:
     - `find_matching_golden_app()`

   - `/src/pipeline/phases/phase_8_helpers.py`:
     - `execute_repair_loop()`
     - `generate_repair_proposal()`
     - `apply_repair_to_code()`

   - `/src/pipeline/phases/phase_8_5_helpers.py`:
     - `attempt_runtime_repair()`
     - `run_llm_smoke_test()`
     - `process_smoke_result()`

   - `/src/pipeline/phases/phase_9_helpers.py`:
     - `run_generated_tests()`
     - `calculate_test_coverage()`
     - `validate_atomic_units()`

2. **Create `/tests/e2e/test_pipeline_helpers.py`**
   - Unit tests for each helper function
   - Mock heavy dependencies (LLM, Docker, etc.)

3. **Update E2E test**
   - Import helpers from `/src/pipeline/phases/`
   - Remove migrated helper code

#### Acceptance Criteria
- [ ] All helper functions migrated
- [ ] Helpers properly isolated and testable
- [ ] Unit tests with mocked dependencies >70% coverage
- [ ] E2E test passes with real integrations

---

### Phase 5: Phase Methods (CORE MIGRATION)
**Branch**: `feature/pipeline-refactor-full/phase5-phases`
**Effort**: 8-10 hours (CRITICAL PHASE)
**Risk**: HIGH
**Lines Migrated**: ~2,800 lines

#### Strategy
Each phase method becomes a **standalone async function** that takes `PipelineContext` and modifies it in-place.

#### Deliverables
1. **Create `/src/pipeline/core/context.py`**
   ```python
   @dataclass
   class PipelineContext:
       """Shared state across all pipeline phases."""
       spec_file: Path
       output_dir: Path
       timestamp: int

       # Phase 1
       spec_content: str = ""
       application_ir: Optional[ApplicationIR] = None

       # Phase 2
       classified_requirements: List[Dict] = field(default_factory=list)

       # ... all phase data

       # Services
       pattern_bank: Optional[PatternBank] = None
       code_generator: Optional[CodeGenerationService] = None

       # Metrics
       metrics_collector: Optional[MetricsCollector] = None
       perf_monitor: Optional[PerformanceMonitor] = None
   ```

2. **Create individual phase files**:
   - `/src/pipeline/phases/phase_1_spec_ingestion.py`:
     ```python
     async def execute_phase_1(ctx: PipelineContext) -> None:
         """Phase 1: Parse spec → ApplicationIR."""
         # Current _phase_1_spec_ingestion() logic
         ...
     ```

   - `/src/pipeline/phases/phase_2_requirements.py`:
     ```python
     async def execute_phase_2(ctx: PipelineContext) -> None:
         """Phase 2: Classify requirements."""
         ...
     ```

   - ... same for all 13 phases (including 1.5 and 8.5)

3. **Create `/tests/e2e/test_pipeline_phases.py`**
   - Unit tests for each phase (isolated)
   - Mock dependencies where possible
   - Integration tests for critical phases

4. **Update E2E test**
   - Import phase functions from `/src/pipeline/phases/`
   - Replace phase method calls with phase function calls
   - Pass `PipelineContext` through all phases

#### Acceptance Criteria
- [ ] All 13 phase methods migrated to standalone functions
- [ ] `PipelineContext` properly threaded through pipeline
- [ ] Unit tests for phase logic >60% coverage
- [ ] E2E test passes with identical phase outputs

---

### Phase 6: Final Integration & Orchestrator
**Branch**: `feature/pipeline-refactor-full/phase6-integration`
**Effort**: 4-5 hours
**Risk**: MEDIUM
**Lines Migrated**: ~200 lines + CREATE WRAPPER

#### Deliverables
1. **Create `/src/pipeline/core/pipeline.py`**
   ```python
   class E2EPipeline:
       """Main orchestrator for E2E pipeline."""

       def __init__(self, spec_file: str, output_dir: Optional[str] = None):
           self.spec_file = Path(spec_file)
           self.ctx = PipelineContext(spec_file, output_dir)

       async def run(self) -> Dict[str, Any]:
           """Execute full pipeline."""
           await self._initialize_services()

           # Execute phases
           await execute_phase_1(self.ctx)
           await execute_phase_1_5(self.ctx)
           await execute_phase_2(self.ctx)
           # ... all phases

           return await self._finalize_and_report()

       async def _initialize_services(self) -> None:
           """Initialize PatternBank, CodeGen, etc."""
           # Migrate from _initialize_services()
           ...

       async def _finalize_and_report(self) -> Dict[str, Any]:
           """Finalize metrics and return report."""
           # Migrate from _finalize_and_report()
           ...
   ```

2. **Create `/src/pipeline/__init__.py`**
   ```python
   # Public API
   from .core.pipeline import E2EPipeline
   from .core.context import PipelineContext

   # Utilities (optional exports)
   from .ir.extractor import IRExtractor
   from .utils.performance_monitor import PerformanceMonitor

   __all__ = [
       "E2EPipeline",
       "PipelineContext",
       "IRExtractor",
       "PerformanceMonitor",
   ]
   ```

3. **REPLACE `/tests/e2e/real_e2e_full_pipeline.py`**
   ```python
   # Thin wrapper (~50 lines)
   import asyncio
   from src.pipeline import E2EPipeline

   async def main():
       spec_file = "data/specs/ecommerce-api-spec-human.md"
       pipeline = E2EPipeline(spec_file)
       metrics = await pipeline.run()

       assert metrics["ir_compliance_strict"] > 0.80
       assert metrics["test_pass_rate"] > 0.90

       print("✅ E2E Pipeline completed")
       return metrics

   if __name__ == "__main__":
       asyncio.run(main())
   ```

4. **DELETE old monolithic code**
   - Keep ONLY the thin wrapper in `real_e2e_full_pipeline.py`
   - DELETE all migrated class/methods

5. **Create `/src/pipeline/README.md`**
   - Architecture overview
   - Usage examples
   - Phase documentation

#### Acceptance Criteria
- [ ] `E2EPipeline` orchestrator fully functional
- [ ] E2E wrapper <100 lines total
- [ ] ALL logic moved to `/src/pipeline/`
- [ ] Full E2E test passes multiple specs
- [ ] Metrics match baseline (±5%)
- [ ] Code review approved

---

## Timeline (Complete Migration)

| Phase | Duration | Cumulative | Status |
|-------|----------|------------|--------|
| **Phase 1: Foundation** | 4-5 hours | 5 hours | Not Started |
| **Phase 2: Core Support** | 3-4 hours | 9 hours | Not Started |
| **Phase 3: Display Layer** | 3-4 hours | 13 hours | Not Started |
| **Phase 4: Phase Helpers** | 5-6 hours | 19 hours | Not Started |
| **Phase 5: Phase Methods** | 8-10 hours | 29 hours | Not Started |
| **Phase 6: Integration** | 4-5 hours | 34 hours | Not Started |

**Total Effort**: ~34 hours (5-6 working days at 60% productivity)

### Realistic Schedule
- **Week 1 (Days 1-2)**: Phases 1-2 (Foundation + Support)
- **Week 1 (Day 3)**: Phase 3 (Display)
- **Week 2 (Days 4-5)**: Phase 4 (Helpers)
- **Week 2-3 (Days 6-8)**: Phase 5 (Core Phases) - CRITICAL
- **Week 3 (Day 9)**: Phase 6 (Integration + Cleanup)

---

## Success Metrics (Complete Migration)

### Quantitative Goals
- [ ] Reduce `real_e2e_full_pipeline.py` from 5,275 to <100 lines
- [ ] Migrate 100% of logic to `/src/pipeline/`
- [ ] Achieve >70% unit test coverage for migrated code
- [ ] E2E test passes with ±5% metrics variance
- [ ] No performance regression >15%

### Qualitative Goals
- [ ] Clean separation of concerns (phases, utils, IR, display)
- [ ] Production-ready code in `/src/pipeline/`
- [ ] Reusable components across codebase
- [ ] Clear module boundaries and dependencies
- [ ] Comprehensive documentation

### Post-Migration Benefits
1. **Testability**: All components unit testable
2. **Reusability**: Pipeline usable from any entry point (CLI, API, notebook)
3. **Maintainability**: Clear module structure
4. **Extensibility**: Easy to add new phases or modify existing
5. **Professional**: Production code in src/, tests in tests/

---

## Rollback Strategy

### Per-Phase Rollback
```bash
# If phase N fails
git revert <phase-N-commit>
git push origin <phase-N-branch>

# Fix issues
# Re-run phase N
```

### Complete Rollback (Nuclear Option)
```bash
# Revert ALL migrations, back to monolith
git checkout feature/validation-scaling-phase1
git branch -D feature/pipeline-refactor-full/*
```

---

## Risk Mitigation (Complete Migration)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Phase 5 breaks E2E** | MEDIUM | HIGH | Migrate phases incrementally, test after each |
| **Context threading errors** | MEDIUM | HIGH | Unit test `PipelineContext` modifications |
| **Import circular dependencies** | LOW | HIGH | Careful module design, no cross-phase imports |
| **Performance degradation** | LOW | MEDIUM | Benchmark before/after, optimize if needed |
| **Incomplete migration** | LOW | HIGH | Checklist per phase, code review |
| **Lost functionality** | LOW | CRITICAL | Diff original vs final, test all features |

---

## Validation Checklist (Final)

### Code Quality
- [ ] All code in `/src/pipeline/` follows PEP 8
- [ ] Type hints on all public functions
- [ ] Docstrings on all public classes/functions
- [ ] No TODO/FIXME comments in production code

### Testing
- [ ] Unit tests for all utilities/helpers
- [ ] Integration tests for critical phases
- [ ] E2E test passes with 5+ different specs
- [ ] Metrics validated against baseline

### Documentation
- [ ] `/src/pipeline/README.md` complete
- [ ] Architecture diagrams (optional)
- [ ] Usage examples in docstrings
- [ ] Migration notes in commit messages

### Cleanup
- [ ] No dead code in `/src/pipeline/`
- [ ] No commented-out code blocks
- [ ] No debug print statements
- [ ] All TODOs resolved or documented

---

## Appendix: Final Import Structure

```python
# /tests/e2e/test_real_e2e_pipeline.py (FINAL STATE - ~50 lines)

import asyncio
from src.pipeline import E2EPipeline

async def main():
    """E2E test: Full pipeline execution."""
    pipeline = E2EPipeline("data/specs/ecommerce-api-spec-human.md")
    metrics = await pipeline.run()

    # Validate
    assert metrics["ir_compliance_strict"] > 0.80
    assert metrics["test_pass_rate"] > 0.90

    print(f"✅ Pipeline completed")
    print(f"   IR Compliance: {metrics['ir_compliance_strict']:.1%}")
    print(f"   Tests Passed: {metrics['test_pass_rate']:.1%}")

    return metrics

if __name__ == "__main__":
    asyncio.run(main())
```

```python
# /src/pipeline/__init__.py (PUBLIC API)

from .core.pipeline import E2EPipeline
from .core.context import PipelineContext

# Optional: Export utilities for external use
from .ir.extractor import IRExtractor
from .utils.performance_monitor import PerformanceMonitor
from .stratum.classifier import StratumClassifier

__all__ = [
    # Core
    "E2EPipeline",
    "PipelineContext",

    # Utilities (optional)
    "IRExtractor",
    "PerformanceMonitor",
    "StratumClassifier",
]
```

---

**END OF COMPLETE MIGRATION PLAN**

## NOTA DE ARIEL:

4. Qué haría yo en la práctica (recorte inteligente)

Si tuviera que priorizar ahora, manteniendo tu plan como “visión completa”, haría:

Paso 1 — Mini orquestador sin migrar todo (1–2 días)

Crear src/pipeline/core/context.py y src/pipeline/core/pipeline.py, pero:

al principio, el E2EPipeline.run() puede simplemente:

llamar al script actual (o wrappers),

o encapsular el flujo sin dividir aún todas las fases en módulos separados.

Objetivo:
Tener algo como:

pipeline = E2EPipeline(spec_file)
metrics = await pipeline.run()


funcionando, aunque internamente siga usando el “monolito”.

Esto ya te da:

API limpia,

entrada única para futuros refactors,

algo decente para enseñar/compartir.

Paso 2 — Extraer sólo foundation + display (lo de menor riesgo)

Implementar Fase 1–3 de tu plan:

ir/extractor.py

utils/*

display/*

Dejar phases helpers + phases core para más adelante.

Ventajas:

Reducís tamaño del monolito,

No tocas la lógica delicada de CodeRepair, golden apps, etc.,

Ganás testabilidad en partes de bajo riesgo.

**Status**: REPLANING
**Approval Required**: Technical Lead Sign-Off
**Estimated Completion**: 2 weeks (with buffer)
