# Pipeline Refactoring Plan: Complete Migration to /src/pipeline

**Status**: DRAFT v2 (FULL MIGRATION)
**Created**: 2025-11-28
**Updated**: 2025-11-28
**Target**: Move ALL pipeline logic from `tests/e2e/real_e2e_full_pipeline.py` to `/src/pipeline/*`
**Goal**: Transform monolithic 5,275-line test into production pipeline with thin E2E wrapper

---

## Executive Summary

### Current State
- **File**: `tests/e2e/real_e2e_full_pipeline.py`
- **Size**: 5,275 lines (64K tokens)
- **Structure**: 1 monolithic class (RealE2ETest) with 53 methods
- **Phases**: 11 pipeline phases + 1 sub-phase (8.5)
- **Complexity**: HIGH - tightly coupled, difficult to test in isolation
- **Location**: tests/ directory (WRONG - this is production logic, not test code)

### Target State
- **Architecture**: Full pipeline in `/src/pipeline/` as production code
- **Structure**: Modular classes with clear separation of concerns
- **Location**: `/src/pipeline/core/pipeline.py` (orchestrator) + specialized modules
- **Test File**: `/tests/e2e/test_real_e2e_pipeline.py` (~50 lines thin wrapper)
- **Testability**: Unit testable components + E2E integration test
- **Maintainability**: Single Responsibility Principle per module
- **Reusability**: ALL components usable across codebase

### Non-Negotiables (Pragmatic Constraints)
1. **NO BIG BANG REFACTOR**: Incremental, deliverable phases
2. **ALWAYS GREEN**: Pipeline must work after each phase
3. **TEST COVERAGE FIRST**: Migrate with tests, not migrate then test
4. **PRODUCTION READY**: Code quality standards from day 1
5. **NO REGRESSIONS**: Existing E2E metrics must not degrade
6. **COMPLETE MIGRATION**: Nothing stays in tests/ except thin E2E runner

---

## Architecture Analysis

### Current Monolith Breakdown (ALL TO BE MIGRATED)

```
RealE2ETest (5,275 lines) → ALL TO /src/pipeline/
├── Initialization (96 lines) → MIGRATE TO /src/pipeline/core/
│   ├── __init__() - Setup output dirs, metrics, services
│   └── _init_stratified_architecture() - Init manifest, stratum, quality gate
│
├── Phase Methods (2,800+ lines) → MIGRATE TO /src/pipeline/phases/
│   ├── _phase_1_spec_ingestion()          [L1282] → phase_1_spec_ingestion.py
│   ├── _phase_1_5_validation_scaling()    [L1404] → phase_1_5_validation_scaling.py
│   ├── _phase_2_requirements_analysis()   [L1659] → phase_2_requirements.py
│   ├── _phase_3_multi_pass_planning()     [L2014] → phase_3_planning.py
│   ├── _phase_4_atomization()             [L2203] → phase_4_atomization.py
│   ├── _phase_5_dag_construction()        [L2260] → phase_5_dag.py
│   ├── _phase_6_code_generation()         [L2290] → phase_6_generation.py (LARGEST)
│   ├── _phase_7_deployment()              [L4391] → phase_7_deployment.py
│   ├── _phase_8_code_repair()             [L2899] → phase_8_repair.py
│   ├── _phase_8_5_runtime_smoke_test()    [L3135] → phase_8_5_smoke_test.py
│   ├── _phase_9_validation()              [L4030] → phase_9_validation.py
│   ├── _phase_10_health_verification()    [L4554] → phase_10_health.py
│   └── _phase_11_learning()               [L4597] → phase_11_learning.py
│
├── IR Extractors (96 lines) → MIGRATE TO /src/pipeline/ir/
│   ├── _get_dag_ground_truth_from_ir()    [L866]
│   ├── _get_entities_from_ir()            [L895]
│   ├── _get_endpoints_from_ir()           [L907]
│   ├── _get_requirements_count_from_ir()  [L919]
│   ├── _get_metadata_from_ir()            [L941]
│   └── _get_dag_nodes_from_ir()           [L953]
│
├── Utilities (250+ lines) → MIGRATE TO /src/pipeline/utils/
│   ├── ErrorPatternStoreFilter            [L295] - Logging filter
│   ├── animated_progress_bar()            [L325] - Rich progress UI
│   ├── silent_logs()                      [L372] - Context manager for log suppression
│   ├── _sample_performance()              [L777] - Memory/CPU sampling
│   ├── _finalize_performance_metrics()    [L813] - Performance calculations
│   └── _apply_error_pattern_filter()      [L853] - Apply logging filter
│
├── Parsers (150+ lines) → MIGRATE TO /src/pipeline/parsers/
│   ├── _parse_generated_code_to_files()   [L2544] - Markdown → files dict
│   └── _extract_atoms_from_file()         [L744] - Extract classes/functions
│
├── Stratum Classification (100+ lines) → MIGRATE TO /src/pipeline/stratum/
│   ├── _classify_file_stratum()           [L702] - Path → stratum mapping
│   └── _record_file_in_manifest()         [L656] - Manifest + metrics recording
│
├── Display Helpers (300+ lines) → MIGRATE TO /src/pipeline/display/
│   ├── _display_phase_6_patterns_summary() [L2641]
│   ├── _display_phase_6_summary()          [L2699]
│   ├── _display_phase_7_summary()          [L2775]
│   ├── _display_phase_8_summary()          [L2831]
│   └── _print_report()                     [L5056] - Final report
│
├── Phase Helpers (800+ lines) → MIGRATE TO /src/pipeline/phases/<phase>_helpers.py
│   ├── _match_patterns_real()             [L1957] → phase_2_helpers.py
│   ├── _match_patterns_simple()           [L1999] → phase_2_helpers.py
│   ├── _find_matching_golden_app()        [L2866] → phase_6_helpers.py
│   ├── _execute_repair_loop()             [L3558] → phase_8_helpers.py
│   ├── _generate_repair_proposal()        [L3879] → phase_8_helpers.py
│   ├── _apply_repair_to_code()            [L4006] → phase_8_helpers.py
│   ├── _attempt_runtime_repair()          [L3290] → phase_8_5_helpers.py
│   ├── _run_llm_smoke_test()              [L3369] → phase_8_5_helpers.py
│   ├── _process_smoke_result()            [L3493] → phase_8_5_helpers.py
│   ├── _run_generated_tests()             [L4704] → phase_9_helpers.py
│   ├── _calculate_test_coverage()         [L4798] → phase_9_helpers.py
│   └── _validate_atomic_units()           [L4863] → phase_9_helpers.py
│
└── Orchestration (200+ lines) → MIGRATE TO /src/pipeline/core/pipeline.py
    ├── run()                               [L1011] - Main entry point
    ├── _initialize_services()              [L1127] - Service initialization
    ├── _finalize_and_report()              [L4887] - Final metrics
    └── _flush_llm_cache()                  [L5009] - Redis cleanup
```

### Migration Strategy (100% of code)

| Group | Lines | Priority | Complexity | Phase |
|-------|-------|----------|------------|-------|
| **IR Extractors** | ~100 | PHASE 1 | LOW | Foundation |
| **Utilities** | ~250 | PHASE 1 | LOW | Foundation |
| **Parsers** | ~150 | PHASE 2 | MEDIUM | Core Support |
| **Stratum Classification** | ~100 | PHASE 2 | LOW | Core Support |
| **Display Helpers** | ~300 | PHASE 3 | LOW | UI Layer |
| **Phase Helpers** | ~800 | PHASE 4 | MEDIUM-HIGH | Business Logic |
| **Phase Methods** | ~2,800 | PHASE 5 | HIGH | Core Pipeline |
| **Orchestration** | ~200 | PHASE 6 | MEDIUM | Final Integration |

**Total to migrate**: 5,275 lines (100%)
**Remaining in tests/e2e/**: ~50 lines (thin E2E wrapper only)

---

## Target Architecture (Complete Migration)

### Directory Structure

```
/src/pipeline/
├── __init__.py                          # Public API exports
│
├── core/
│   ├── __init__.py
│   ├── pipeline.py                      # E2EPipeline (main orchestrator)
│   ├── config.py                        # Pipeline configuration
│   └── context.py                       # PipelineContext (shared state)
│
├── phases/
│   ├── __init__.py
│   ├── phase_1_spec_ingestion.py        # Phase 1: Parse spec → IR
│   ├── phase_1_5_validation_scaling.py  # Phase 1.5: Extract validations
│   ├── phase_2_requirements.py          # Phase 2: Classify requirements
│   ├── phase_2_helpers.py               # Pattern matching helpers
│   ├── phase_3_planning.py              # Phase 3: Multi-pass planning
│   ├── phase_4_atomization.py           # Phase 4: Task atomization
│   ├── phase_5_dag.py                   # Phase 5: DAG construction
│   ├── phase_6_generation.py            # Phase 6: Code generation
│   ├── phase_6_helpers.py               # Golden app matching, etc.
│   ├── phase_7_deployment.py            # Phase 7: Save files to disk
│   ├── phase_8_repair.py                # Phase 8: Code repair loop
│   ├── phase_8_helpers.py               # Repair proposal, apply fixes
│   ├── phase_8_5_smoke_test.py          # Phase 8.5: Runtime smoke test
│   ├── phase_8_5_helpers.py             # Smoke test orchestration
│   ├── phase_9_validation.py            # Phase 9: IR compliance validation
│   ├── phase_9_helpers.py               # Test execution, coverage
│   ├── phase_10_health.py               # Phase 10: Health verification
│   └── phase_11_learning.py             # Phase 11: Pattern learning
│
├── ir/
│   ├── __init__.py
│   ├── extractor.py                     # IRExtractor class
│   └── validator.py                     # IR validation utilities (future)
│
├── stratum/
│   ├── __init__.py
│   ├── classifier.py                    # StratumClassifier
│   ├── patterns.py                      # Stratum pattern definitions
│   └── recorder.py                      # Manifest recording logic
│
├── parsers/
│   ├── __init__.py
│   ├── markdown_code.py                 # MarkdownCodeParser
│   └── python_atoms.py                  # PythonAtomExtractor
│
├── utils/
│   ├── __init__.py
│   ├── logging_filters.py               # ErrorPatternStoreFilter
│   ├── logging_context.py               # silent_logs()
│   ├── progress_display.py              # animated_progress_bar()
│   └── performance_monitor.py           # PerformanceMonitor
│
└── display/
    ├── __init__.py
    ├── phase_summary.py                 # Phase summary displays
    └── final_report.py                  # Final report generation

/tests/e2e/
├── test_real_e2e_pipeline.py            # Thin E2E wrapper (~50 lines)
├── test_pipeline_ir_extractor.py        # Unit tests for IR extractor
├── test_pipeline_utils.py               # Unit tests for utilities
├── test_pipeline_parsers.py             # Unit tests for parsers
├── test_pipeline_stratum.py             # Unit tests for stratum
├── test_pipeline_phases.py              # Unit tests for phase logic
└── fixtures/
    └── test_specs/                      # Test spec files
```

### Key Classes

#### E2EPipeline (Main Orchestrator)
```python
# /src/pipeline/core/pipeline.py
from typing import Optional
from pathlib import Path
from src.pipeline.core.context import PipelineContext

class E2EPipeline:
    """
    Main orchestrator for E2E code generation pipeline.

    Executes 11 phases sequentially:
    1. Spec Ingestion → ApplicationIR
    2. Requirements Analysis → Classified requirements
    3. Multi-pass Planning → Execution plan
    4. Atomization → Atomic tasks
    5. DAG Construction → Dependency graph
    6. Code Generation → Generated files
    7. Deployment → Files on disk
    8. Code Repair → Fixed errors
    8.5. Runtime Smoke Test → Deployed app validation
    9. Validation → IR compliance check
    10. Health Verification → Service health
    11. Learning → Pattern feedback
    """

    def __init__(self, spec_file: str, output_dir: Optional[str] = None):
        """Initialize pipeline with spec file and output directory."""
        self.spec_file = Path(spec_file)
        self.ctx = PipelineContext(spec_file, output_dir)

    async def run(self) -> Dict[str, Any]:
        """Execute full pipeline and return metrics."""
        await self._initialize_services()

        # Execute phases sequentially
        await self._execute_phase_1()
        await self._execute_phase_1_5()
        await self._execute_phase_2()
        # ... all phases

        return await self._finalize_and_report()
```

#### PipelineContext (Shared State)
```python
# /src/pipeline/core/context.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path

@dataclass
class PipelineContext:
    """
    Shared context/state across all pipeline phases.

    Replaces instance variables in monolithic RealE2ETest.
    Passed between phase functions to maintain state.
    """
    # Input/Output
    spec_file: Path
    output_dir: Path
    timestamp: int = field(default_factory=lambda: int(time.time()))

    # Phase 1: Spec Ingestion
    spec_content: str = ""
    spec_requirements: Optional[SpecRequirements] = None
    application_ir: Optional[ApplicationIR] = None

    # Phase 2: Requirements Analysis
    classified_requirements: List[Dict] = field(default_factory=list)
    dependency_graph: Dict = field(default_factory=dict)

    # Phase 3-5: Planning & DAG
    patterns_matched: List[Dict] = field(default_factory=list)
    atomic_units: List[Dict] = field(default_factory=list)
    dag: Optional[Dict] = None

    # Phase 6: Code Generation
    generated_code: Dict[str, str] = field(default_factory=dict)

    # Phase 9: Validation
    compliance_report: Optional[Any] = None
    ir_compliance_metrics: Optional[Any] = None

    # Services
    pattern_bank: Optional[Any] = None
    code_generator: Optional[Any] = None
    # ... all service references

    # Metrics
    metrics_collector: Optional[Any] = None
    perf_monitor: Optional[Any] = None
```

#### IRExtractor
```python
# /src/pipeline/ir/extractor.py
from src.cognitive.ir.application_ir import ApplicationIR
from typing import Dict, List, Tuple, Optional

class IRExtractor:
    """Extract structured data from ApplicationIR.

    Centralizes IR access patterns used throughout pipeline.
    Provides fallback to legacy SpecRequirements when IR unavailable.
    """

    def __init__(self, application_ir: Optional[ApplicationIR] = None):
        self.ir = application_ir

    def get_dag_ground_truth(self) -> Tuple[Dict, Dict]:
        """Extract DAG ground truth and classification ground truth."""
        ...

    def get_entities(self) -> List[Dict]:
        """Extract domain entities from IR."""
        ...

    def get_endpoints(self) -> List[Dict]:
        """Extract API endpoints from IR."""
        ...

    def get_requirements_count(self) -> Dict[str, int]:
        """Get requirements count breakdown."""
        ...

    def get_metadata(self) -> Dict:
        """Extract IR metadata."""
        ...

    def get_dag_nodes(self) -> List[Dict]:
        """Extract DAG nodes from all IR models."""
        ...
```

#### PerformanceMonitor
```python
# /src/pipeline/utils/performance_monitor.py
import psutil
import tracemalloc
from typing import Dict, List

class PerformanceMonitor:
    """Monitor memory and CPU usage during pipeline execution.

    Thread-safe performance profiling with peak/average metrics.
    """

    def __init__(self):
        tracemalloc.start()
        self.process = psutil.Process()
        self.memory_samples: List[float] = []
        self.cpu_samples: List[float] = []
        self.peak_memory_mb = 0.0
        self.peak_cpu_percent = 0.0

    def sample(self) -> None:
        """Take a performance sample (memory + CPU)."""
        ...

    def finalize(self) -> Dict[str, float]:
        """Calculate final metrics from samples.

        Returns:
            {
                'avg_memory_mb': float,
                'peak_memory_mb': float,
                'avg_cpu_percent': float,
                'peak_cpu_percent': float
            }
        """
        ...
```

#### StratumClassifier
```python
# /src/pipeline/stratum/classifier.py
from typing import List
from src.pipeline.stratum.patterns import STRATUM_PATTERNS

class StratumClassifier:
    """Classify files into execution strata (TEMPLATE, AST, LLM).

    Uses pattern matching on file paths to determine generation strategy.
    """

    def classify(self, filename: str) -> str:
        """Classify file into stratum.

        Returns: "template" | "ast" | "llm"
        """
        ...

    def extract_atoms(self, filename: str, content: str) -> List[str]:
        """Extract atom identifiers from file content.

        Returns: List of atoms (e.g., ['entity:User', 'schema:UserCreate'])
        """
        ...
```

#### MarkdownCodeParser
```python
# /src/pipeline/parsers/markdown_code.py
from typing import Dict
import re

class MarkdownCodeParser:
    """Parse LLM-generated code from markdown format.

    Extracts code blocks with filenames from markdown.
    Format: ```python filename.py\n<code>\n```
    """

    def parse_to_files(self, generated_code: str) -> Dict[str, str]:
        """Parse markdown to files dictionary.

        Returns: {filename: content}
        """
        ...
```

---

### Thin E2E Wrapper (Final State)
```python
# /tests/e2e/test_real_e2e_pipeline.py (~50 lines)
"""
E2E integration test for full pipeline.

This is a THIN WRAPPER that just invokes the production pipeline.
All logic lives in /src/pipeline/.
"""
import asyncio
from pathlib import Path
from src.pipeline import E2EPipeline

async def main():
    """Run E2E test with real spec."""
    spec_file = "data/specs/ecommerce-api-spec-human.md"

    # Create and run pipeline
    pipeline = E2EPipeline(spec_file)
    metrics = await pipeline.run()

    # Validate metrics
    assert metrics["ir_compliance_strict"] > 0.80, "IR compliance too low"
    assert metrics["test_pass_rate"] > 0.90, "Test pass rate too low"

    print(f"✅ E2E Pipeline completed successfully")
    print(f"   IR Compliance: {metrics['ir_compliance_strict']:.1%}")
    print(f"   Test Pass Rate: {metrics['test_pass_rate']:.1%}")

    return metrics

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Git Branch Strategy

### Branch Naming Convention
```
feature/pipeline-refactor-full/<phase>
```

### Phase Branches (FULL MIGRATION)

| Phase | Branch Name | Base | Scope |
|-------|-------------|------|-------|
| Phase 1 | `feature/pipeline-refactor-full/phase1-foundation` | `feature/validation-scaling-phase1` | IR + Utils |
| Phase 2 | `feature/pipeline-refactor-full/phase2-support` | Phase 1 | Parsers + Stratum |
| Phase 3 | `feature/pipeline-refactor-full/phase3-display` | Phase 2 | Display helpers |
| Phase 4 | `feature/pipeline-refactor-full/phase4-helpers` | Phase 3 | Phase helpers |
| Phase 5 | `feature/pipeline-refactor-full/phase5-phases` | Phase 4 | Phase methods |
| Phase 6 | `feature/pipeline-refactor-full/phase6-integration` | Phase 5 | Orchestrator + E2E wrapper |

### Branch Protection Rules
1. **All phases**: Must pass E2E tests before merge
2. **Integration branch**: Requires code review + full test suite
3. **Merge commits**: Squash per phase for clean history

### Checkpoint Strategy
```bash
# After each extraction group
git add -A
git commit -m "refactor(pipeline): Extract <group> to /src/pipeline/<module>

- Extracted: <list of classes/functions>
- Tests: <new test file>
- Coverage: <percentage>
- E2E Status: PASSING"

git push origin <branch-name>
```

---

## Phase Execution Plan

### Phase 1: IR Extractors (HIGH PRIORITY)
**Branch**: `feature/pipeline-refactor/phase1-ir-extractors`
**Effort**: 2-3 hours
**Risk**: LOW (pure extraction, no side effects)

#### Deliverables
1. **Create**: `/src/pipeline/ir/extractor.py`
   - `IRExtractor` class with 6 methods
   - Fallback logic to legacy SpecRequirements
   - Type hints and docstrings

2. **Create**: `/tests/e2e/test_ir_extractor.py`
   - Unit tests for each method
   - Test with ApplicationIR fixture
   - Test fallback to SpecRequirements

3. **Refactor**: `tests/e2e/real_e2e_full_pipeline.py`
   - Remove 6 `_get_*_from_ir()` methods
   - Add: `self.ir_extractor = IRExtractor(self.application_ir)`
   - Replace calls: `self._get_entities_from_ir()` → `self.ir_extractor.get_entities()`

#### Acceptance Criteria
- [ ] All 6 IR extractor methods in `IRExtractor` class
- [ ] Unit tests with >90% coverage
- [ ] E2E test passes with identical metrics
- [ ] No regressions in precision/recall scores

#### Rollback Plan
```bash
git revert <commit-hash>
git push origin <branch-name>
```

---

### Phase 2: Utilities (HIGH PRIORITY)
**Branch**: `feature/pipeline-refactor/phase2-utilities`
**Effort**: 3-4 hours
**Risk**: LOW-MEDIUM (context manager needs careful testing)

#### Deliverables
1. **Create**: `/src/pipeline/utils/logging_filters.py`
   ```python
   class ErrorPatternStoreFilter(logging.Filter):
       """Filter error_pattern_store logs to reduce noise."""
       def filter(self, record): ...

   def apply_error_pattern_filter() -> None:
       """Apply filter to all loggers globally."""
       ...
   ```

2. **Create**: `/src/pipeline/utils/logging_context.py`
   ```python
   @contextmanager
   def silent_logs():
       """Context manager to suppress verbose logs."""
       ...
   ```

3. **Create**: `/src/pipeline/utils/progress_display.py`
   ```python
   def animated_progress_bar(message: str, duration: int = 120):
       """Display animated progress bar with rich."""
       ...
   ```

4. **Create**: `/src/pipeline/utils/performance_monitor.py`
   ```python
   class PerformanceMonitor:
       def __init__(self): ...
       def sample(self) -> None: ...
       def finalize(self) -> Dict[str, float]: ...
   ```

5. **Create**: `/tests/e2e/test_pipeline_utils.py`
   - Test `ErrorPatternStoreFilter` filtering logic
   - Test `silent_logs()` context manager
   - Test `PerformanceMonitor` sampling and finalization
   - Test `animated_progress_bar()` (basic smoke test)

6. **Refactor**: `tests/e2e/real_e2e_full_pipeline.py`
   - Import from `/src/pipeline/utils/*`
   - Remove duplicate implementations
   - Replace `self._sample_performance()` → `self.perf_monitor.sample()`
   - Replace `self._finalize_performance_metrics()` → `self.perf_monitor.finalize()`

#### Acceptance Criteria
- [ ] All utilities extracted and importable from `/src/pipeline/utils/`
- [ ] Unit tests with >85% coverage
- [ ] E2E test passes with identical performance metrics
- [ ] `silent_logs()` correctly suppresses logs without side effects

#### Rollback Plan
Same as Phase 1

---

### Phase 3: Parsers (MEDIUM PRIORITY)
**Branch**: `feature/pipeline-refactor/phase3-parsers`
**Effort**: 3-4 hours
**Risk**: MEDIUM (parsing logic has edge cases)

#### Deliverables
1. **Create**: `/src/pipeline/parsers/markdown_code.py`
   ```python
   class MarkdownCodeParser:
       def parse_to_files(self, generated_code: str) -> Dict[str, str]:
           """Parse markdown code blocks to files dict."""
           ...
   ```

2. **Create**: `/src/pipeline/parsers/python_atoms.py`
   ```python
   class PythonAtomExtractor:
       def extract(self, content: str) -> List[str]:
           """Extract atoms (classes, functions) from Python code."""
           ...
   ```

3. **Create**: `/tests/e2e/test_pipeline_parsers.py`
   - Test markdown parsing with various formats
   - Test atom extraction from real Python files
   - Edge cases: empty files, malformed markdown, no atoms

4. **Refactor**: `tests/e2e/real_e2e_full_pipeline.py`
   - Import parsers from `/src/pipeline/parsers/`
   - Remove `_parse_generated_code_to_files()` and `_extract_atoms_from_file()`
   - Use `MarkdownCodeParser().parse_to_files()` in Phase 6
   - Use `PythonAtomExtractor().extract()` in stratum methods

#### Acceptance Criteria
- [ ] Parsers handle all existing test cases
- [ ] Unit tests with >90% coverage
- [ ] E2E test generates identical file structures
- [ ] No regressions in code generation metrics

#### Rollback Plan
Same as Phase 1

---

### Phase 4: Stratum Classification (MEDIUM PRIORITY)
**Branch**: `feature/pipeline-refactor/phase4-stratum`
**Effort**: 2-3 hours
**Risk**: LOW (pattern matching is deterministic)

#### Deliverables
1. **Create**: `/src/pipeline/stratum/patterns.py`
   ```python
   # Centralized pattern definitions
   STRATUM_PATTERNS = {
       "template": [
           "requirements.txt", "Dockerfile", "docker-compose",
           ...
       ],
       "ast": [
           "models/entities.py", "models/schemas.py",
           ...
       ],
       "llm": [
           "services/", "_flow.py", "_business.py",
           ...
       ]
   }
   ```

2. **Create**: `/src/pipeline/stratum/classifier.py`
   ```python
   class StratumClassifier:
       def classify(self, filename: str) -> str: ...
       def extract_atoms(self, filename: str, content: str) -> List[str]: ...
   ```

3. **Create**: `/tests/e2e/test_stratum_classifier.py`
   - Test classification for all pattern types
   - Test atom extraction
   - Edge cases: unknown patterns, empty content

4. **Refactor**: `tests/e2e/real_e2e_full_pipeline.py`
   - Import `StratumClassifier` from `/src/pipeline/stratum/`
   - Remove `_classify_file_stratum()` and pattern constants
   - Use `self.stratum_classifier.classify()` in manifest recording

#### Acceptance Criteria
- [ ] All files classified correctly in E2E test
- [ ] Patterns externalized and maintainable
- [ ] Unit tests with >90% coverage
- [ ] No regressions in stratum metrics

#### Rollback Plan
Same as Phase 1

---

### Phase 5: Integration & Cleanup (FINAL)
**Branch**: `feature/pipeline-refactor/integration`
**Effort**: 2-3 hours
**Risk**: MEDIUM (final validation)

#### Deliverables
1. **Create**: `/src/pipeline/__init__.py`
   ```python
   # Public API
   from .ir.extractor import IRExtractor
   from .stratum.classifier import StratumClassifier
   from .parsers.markdown_code import MarkdownCodeParser
   from .parsers.python_atoms import PythonAtomExtractor
   from .utils.performance_monitor import PerformanceMonitor
   from .utils.logging_filters import ErrorPatternStoreFilter, apply_error_pattern_filter
   from .utils.logging_context import silent_logs
   from .utils.progress_display import animated_progress_bar

   __all__ = [
       "IRExtractor",
       "StratumClassifier",
       "MarkdownCodeParser",
       "PythonAtomExtractor",
       "PerformanceMonitor",
       "ErrorPatternStoreFilter",
       "apply_error_pattern_filter",
       "silent_logs",
       "animated_progress_bar",
   ]
   ```

2. **Update**: `tests/e2e/real_e2e_full_pipeline.py`
   - Clean imports: use `/src/pipeline` public API
   - Remove all extracted method stubs
   - Verify line count reduction (~900 lines removed)

3. **Create**: Documentation
   - `/src/pipeline/README.md` - Architecture overview
   - Docstrings for all public classes/methods

4. **Validation**
   - Run full E2E test suite (5+ specs)
   - Compare metrics with baseline (before refactor)
   - Performance regression check (<5% degradation allowed)

#### Acceptance Criteria
- [ ] E2E test reduced to ~4,300 lines (from 5,275)
- [ ] All tests passing (E2E + unit)
- [ ] Metrics identical or improved
- [ ] Documentation complete
- [ ] Code review approved

---

## Testing Strategy

### Unit Tests (per phase)
```python
# tests/e2e/test_ir_extractor.py
def test_ir_extractor_get_entities():
    ir = create_test_application_ir()
    extractor = IRExtractor(ir)
    entities = extractor.get_entities()
    assert len(entities) > 0
    assert entities[0]["name"] == "User"

# tests/e2e/test_performance_monitor.py
def test_performance_monitor_sampling():
    monitor = PerformanceMonitor()
    monitor.sample()
    monitor.sample()
    metrics = monitor.finalize()
    assert metrics["peak_memory_mb"] > 0
    assert metrics["avg_cpu_percent"] >= 0

# tests/e2e/test_markdown_parser.py
def test_parse_markdown_to_files():
    parser = MarkdownCodeParser()
    markdown = '''
    ```python main.py
    def main():
        pass
    ```
    '''
    files = parser.parse_to_files(markdown)
    assert "main.py" in files
    assert "def main():" in files["main.py"]
```

### E2E Regression Tests
```bash
# Baseline (before refactor)
PRODUCTION_MODE=true PYTHONPATH=. timeout 600 python tests/e2e/real_e2e_full_pipeline.py \
    --spec data/specs/ecommerce-api-spec-human.md > baseline_metrics.json

# After each phase
PRODUCTION_MODE=true PYTHONPATH=. timeout 600 python tests/e2e/real_e2e_full_pipeline.py \
    --spec data/specs/ecommerce-api-spec-human.md > phase_N_metrics.json

# Compare
python tests/e2e/compare_metrics.py baseline_metrics.json phase_N_metrics.json
```

### Metrics to Track
| Metric | Threshold | Critical? |
|--------|-----------|-----------|
| IR compliance (strict) | >80% | YES |
| Test pass rate | >90% | YES |
| Total execution time | <+10% | NO |
| Peak memory usage | <+15% | NO |
| Lines of code reduced | ~900 lines | NO |

---

## Risk Mitigation

### Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking E2E tests | MEDIUM | HIGH | Unit tests + E2E regression suite |
| Performance degradation | LOW | MEDIUM | Benchmark before/after each phase |
| Import circular dependencies | LOW | HIGH | Careful module design, no cross-imports |
| Incomplete extraction | MEDIUM | MEDIUM | Code review checklist per phase |
| Git merge conflicts | LOW | LOW | Small, frequent commits |

### Validation Checkpoints
1. **After each extraction**: Run full E2E test with 3 different specs
2. **Before merge**: Compare metrics with baseline (must be within thresholds)
3. **Code review**: Verify no duplicate logic, clean imports
4. **Integration test**: Run against all golden apps

---

## Success Metrics

### Quantitative Goals
- [x] Reduce `real_e2e_full_pipeline.py` by ~900 lines (17%)
- [x] Achieve >85% unit test coverage for extracted modules
- [x] Maintain E2E test pass rate >90%
- [x] No performance regression >10%

### Qualitative Goals
- [x] Extracted modules follow Single Responsibility Principle
- [x] Code is reusable outside E2E context
- [x] Improved maintainability (clear module boundaries)
- [x] Production-ready code quality (docstrings, type hints, error handling)

### Post-Refactor Benefits
1. **Testability**: Utilities and extractors testable in isolation
2. **Reusability**: IR extractors usable in other pipelines
3. **Maintainability**: Clear separation of concerns
4. **Extensibility**: Easy to add new stratum patterns or parsers
5. **Documentation**: Self-documenting module structure

---

## Timeline Estimate (Pragmatic)

| Phase | Effort | Dependencies | Cumulative |
|-------|--------|--------------|------------|
| Phase 1: IR Extractors | 2-3 hours | None | 3 hours |
| Phase 2: Utilities | 3-4 hours | Phase 1 | 7 hours |
| Phase 3: Parsers | 3-4 hours | Phase 2 | 11 hours |
| Phase 4: Stratum | 2-3 hours | Phase 3 | 14 hours |
| Phase 5: Integration | 2-3 hours | Phase 4 | 17 hours |

**Total**: ~17 hours (3 working days at 60% productivity)

### Realistic Schedule
- **Day 1**: Phases 1-2 (IR + Utilities)
- **Day 2**: Phases 3-4 (Parsers + Stratum)
- **Day 3**: Phase 5 (Integration + Documentation)

---

## Appendix A: Code Extraction Checklist

### Per Extraction Group
- [ ] Create new module file in `/src/pipeline/<category>/`
- [ ] Extract class/function with full implementation
- [ ] Add type hints (all parameters and return types)
- [ ] Add docstrings (class + all public methods)
- [ ] Create unit test file in `/tests/e2e/`
- [ ] Write tests for happy path + edge cases
- [ ] Refactor E2E test to use new module
- [ ] Run E2E test and verify metrics
- [ ] Commit with descriptive message
- [ ] Push to feature branch

### Before Merge
- [ ] All unit tests passing (>85% coverage)
- [ ] E2E test passing with identical metrics
- [ ] No pylint/mypy errors
- [ ] Code review completed
- [ ] Documentation updated

---

## Appendix B: Import Structure After Refactor

```python
# tests/e2e/real_e2e_full_pipeline.py (after all phases)

# Standard library
import asyncio, os, sys, json, time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Project modules
from src.pipeline import (
    IRExtractor,
    StratumClassifier,
    MarkdownCodeParser,
    PythonAtomExtractor,
    PerformanceMonitor,
    ErrorPatternStoreFilter,
    apply_error_pattern_filter,
    silent_logs,
    animated_progress_bar,
)

# Existing imports (unchanged)
from src.parsing.spec_parser import SpecParser
from src.classification.requirements_classifier import RequirementsClassifier
from src.services.code_generation_service import CodeGenerationService
# ... etc
```

---

## Appendix C: Non-Goals (Explicitly Out of Scope)

### What We Are NOT Doing
1. **Phase method extraction**: Phases stay in E2E test (too coupled)
2. **Display helper extraction**: Low value, low priority (defer to future)
3. **Config externalization**: Pipeline config stays in-code for now
4. **Complete rewrite**: This is incremental refactor, not greenfield
5. **Performance optimization**: Focus is on structure, not speed
6. **Adding new features**: Only extract existing functionality
7. **Changing phase logic**: No behavioral changes to pipeline

### Why These Are Non-Goals
- **Phase coupling**: Phases have deep state dependencies, extraction would be high-risk
- **Diminishing returns**: Display helpers have low reusability, not worth effort now
- **Scope creep**: Must ship refactor without adding scope
- **Risk management**: Avoid big bang changes that could break production pipeline

---

## Sign-Off

### Approval Required Before Execution
- [ ] Technical lead review
- [ ] Architecture alignment confirmed
- [ ] Test strategy approved
- [ ] Timeline realistic and approved

### Execution Authorization
**Status**: READY FOR PHASE 1
**Start Date**: TBD
**Owner**: TBD

---

**END OF PLAN**
