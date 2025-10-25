# MGE V2 - Comprehensive Testing for Implemented Gaps (5-9)

**Version**: 1.0
**Status**: Specification
**Priority**: CRITICAL - Code exists, tests missing
**Owner**: Test Coverage Initiative
**Due**: Week 1

## Executive Summary

**Discovery**: Ultra-deep codebase analysis revealed **5 gaps fully implemented** (~1,600 LOC) but **0% test coverage**. This spec addresses that critical gap.

### Gaps Requiring Tests

| Gap | Component | LOC | Current Tests | Target Tests | Status |
|-----|-----------|-----|---------------|--------------|--------|
| Gap 5 | Dependencies (graph_builder.py) | 350 | 0 | 25+ | 🔴 ZERO |
| Gap 6 | Atomization (atomization.py) | 380 | 0 | 30+ | 🔴 ZERO |
| Gap 7 | Cycle-breaking (topological_sorter.py) | 365 | Broken | 25+ | 🟡 BROKEN |
| Gap 8 | Concurrency (backpressure_queue.py) | 196 | 0 | 20+ | 🔴 ZERO |
| Gap 9 | Cost Guardrails (cost_guardrails.py) | 319 | 0 | 25+ | 🔴 ZERO |
| **Total** | **5 Components** | **1,610** | **0** | **125+** | **URGENT** |

## Success Criteria

### Test Coverage Targets
- ✅ **125+ tests passing** across all 5 components
- ✅ **≥95% code coverage** for each component
- ✅ **100% critical path coverage** (happy path + error paths)
- ✅ **Integration tests** for inter-component dependencies
- ✅ **Performance benchmarks** where applicable

### Quality Gates
- **No test failures** - All tests must pass
- **No flaky tests** - 100% reproducible results
- **Fast execution** - Full suite <30 seconds
- **Clear test names** - Self-documenting test descriptions
- **Comprehensive mocking** - Isolated unit tests

## Technical Requirements

---

## Gap 5: Dependency Graph Builder Tests

**File**: `src/dependency/graph_builder.py` (350 LOC)
**Test File**: `tests/unit/test_graph_builder.py` (NEW)
**Target Tests**: 25+

### Test Categories

#### 1. Symbol Extraction Tests (8 tests)
```python
# Python symbol extraction
test_extract_python_functions()
test_extract_python_variables()
test_extract_python_classes()
test_extract_python_imports()

# TypeScript/JavaScript symbol extraction
test_extract_ts_functions()
test_extract_ts_variables()
test_extract_ts_types_interfaces()
test_extract_js_imports()
```

#### 2. Dependency Detection Tests (10 tests)
```python
# Function call dependencies
test_detect_function_call_dependency()
test_ignore_self_dependencies()
test_detect_cross_file_function_calls()

# Variable dependencies
test_detect_variable_usage()
test_detect_shared_variables()

# Type dependencies
test_detect_type_usage()
test_detect_interface_implementation()

# Import dependencies
test_detect_module_imports()
test_detect_barrel_file_imports()
test_detect_dynamic_imports()
```

#### 3. Graph Construction Tests (7 tests)
```python
test_build_graph_single_atom()
test_build_graph_multiple_atoms()
test_graph_node_attributes()
test_graph_edge_attributes()
test_graph_dependency_weights()
test_isolated_nodes_detection()
test_cycle_detection()
```

### Integration Test
```python
test_graph_builder_accuracy_vs_ground_truth()
# Load test suite with known dependencies
# Verify ≥90% edge accuracy
```

---

## Gap 6: Atomization API Tests

**File**: `src/api/routers/atomization.py` (380 LOC)
**Test File**: `tests/api/routers/test_atomization.py` (NEW)
**Target Tests**: 30+

### Test Categories

#### 1. Decompose Endpoint Tests (12 tests)
```python
# POST /api/v2/atomization/decompose
test_decompose_valid_task()
test_decompose_returns_atoms()
test_decompose_calculates_stats()
test_decompose_atomicity_scores()
test_decompose_context_completeness()
test_decompose_invalid_task_id()
test_decompose_task_not_found()
test_decompose_empty_task()
test_decompose_large_task_100_atoms()
test_decompose_multi_language_task()
test_decompose_complex_task()
test_decompose_pipeline_complete()
```

#### 2. Get Atom Tests (6 tests)
```python
# GET /api/v2/atoms/{atom_id}
test_get_atom_valid_id()
test_get_atom_returns_all_fields()
test_get_atom_atomicity_score()
test_get_atom_invalid_id()
test_get_atom_not_found()
test_get_atom_status_values()
```

#### 3. Get Atoms by Task Tests (4 tests)
```python
# GET /api/v2/atoms/by-task/{task_id}
test_get_atoms_by_task()
test_get_atoms_by_task_count()
test_get_atoms_by_task_empty()
test_get_atoms_by_task_invalid_id()
```

#### 4. Update Atom Tests (4 tests)
```python
# PUT /api/v2/atoms/{atom_id}
test_update_atom_name()
test_update_atom_code()
test_update_atom_status()
test_update_atom_not_found()
```

#### 5. Delete Atom Tests (2 tests)
```python
# DELETE /api/v2/atoms/{atom_id}
test_delete_atom()
test_delete_atom_not_found()
```

#### 6. Stats Endpoint Tests (2 tests)
```python
# GET /api/v2/atoms/by-task/{task_id}/stats
test_get_decomposition_stats()
test_stats_accuracy()
```

---

## Gap 7: Topological Sorter Tests

**File**: `src/dependency/topological_sorter.py` (365 LOC)
**Test File**: `tests/unit/test_topological_sorter.py` (EXISTS - BROKEN)
**Target Tests**: 25+

### Fix Collection Error First
```python
# Current error: ImportError or ModuleNotFoundError
# Action: Fix imports and module structure
```

### Test Categories

#### 1. Wave Generation Tests (8 tests)
```python
test_generate_waves_single_wave()
test_generate_waves_multiple_waves()
test_generate_waves_sequential_dependencies()
test_wave_level_assignment()
test_wave_parallelism_calculation()
test_max_parallelism_tracking()
test_avg_parallelism_calculation()
test_estimated_duration_calculation()
```

#### 2. Cycle Handling Tests (10 tests)
```python
test_detect_simple_cycle()
test_detect_complex_cycles()
test_break_cycles_with_fas()
test_feedback_arc_set_minimal()
test_cycle_breaking_preserves_dag()
test_cycle_info_logging()
test_removed_edges_tracking()
test_multiple_cycles_handling()
test_cycle_count_accuracy()
test_dag_validation_after_breaking()
```

#### 3. Execution Plan Tests (7 tests)
```python
test_create_execution_plan_simple()
test_create_execution_plan_complex()
test_execution_plan_wave_count()
test_execution_plan_atom_distribution()
test_execution_plan_dependencies_satisfied()
test_execution_plan_has_cycles_flag()
test_execution_plan_statistics()
```

---

## Gap 8: Concurrency Controller Tests

**File**: `src/concurrency/backpressure_queue.py` (196 LOC)
**Test File**: `tests/unit/test_backpressure_queue.py` (NEW)
**Target Tests**: 20+

### Test Categories

#### 1. Enqueue Tests (6 tests)
```python
test_enqueue_success()
test_enqueue_with_priority()
test_enqueue_queue_full_rejection()
test_enqueue_updates_statistics()
test_enqueue_rejected_count()
test_enqueue_concurrent_requests()
```

#### 2. Dequeue Tests (6 tests)
```python
test_dequeue_priority_order()
test_dequeue_fifo_within_priority()
test_dequeue_timeout()
test_dequeue_request_expired()
test_dequeue_empty_queue()
test_dequeue_updates_statistics()
```

#### 3. Backpressure Tests (4 tests)
```python
test_is_at_capacity_threshold_80()
test_is_at_capacity_below_threshold()
test_backpressure_signal_when_full()
test_queue_recovery_after_backpressure()
```

#### 4. Statistics Tests (4 tests)
```python
test_statistics_enqueued_count()
test_statistics_dequeued_count()
test_statistics_timeout_count()
test_statistics_rejected_count()
```

---

## Gap 9: Cost Guardrails Tests

**File**: `src/cost/cost_guardrails.py` (319 LOC)
**Test File**: `tests/unit/test_cost_guardrails.py` (NEW)
**Target Tests**: 25+

### Test Categories

#### 1. Limit Configuration Tests (5 tests)
```python
test_set_masterplan_limits()
test_default_limits()
test_custom_limits()
test_per_atom_limits()
test_soft_less_than_hard_validation()
```

#### 2. Soft Limit Tests (6 tests)
```python
test_soft_limit_warning()
test_soft_limit_alert_triggered()
test_soft_limit_not_repeated()
test_soft_limit_usage_percentage()
test_soft_limit_reset()
test_multiple_masterplans_soft_limits()
```

#### 3. Hard Limit Tests (6 tests)
```python
test_hard_limit_exception_raised()
test_hard_limit_blocks_execution()
test_hard_limit_exact_threshold()
test_hard_limit_alert_triggered()
test_hard_limit_per_atom()
test_hard_limit_usage_100_percent()
```

#### 4. Pre-Execution Check Tests (4 tests)
```python
test_check_before_execution_passes()
test_check_before_execution_blocks()
test_check_before_execution_estimated_cost()
test_check_before_execution_projection()
```

#### 5. Status & Metrics Tests (4 tests)
```python
test_get_limit_status()
test_remaining_budget_calculation()
test_usage_percentage_accuracy()
test_calls_made_tracking()
```

---

## Integration Tests

### Cross-Component Integration (5 tests)

```python
# Test dependencies → atomization → execution flow
test_dependency_graph_to_atomization()

# Test atomization → topological sort → execution
test_atomization_to_execution_plan()

# Test concurrency + cost guardrails integration
test_concurrency_with_cost_limits()

# Test full pipeline with all components
test_e2e_pipeline_integration()

# Test error propagation across components
test_error_handling_integration()
```

---

## Performance Benchmarks

### Benchmark Tests (5 tests)

```python
# Dependency graph performance
test_dependency_graph_1000_atoms_performance()  # Target: <5s

# Atomization performance
test_atomization_large_task_performance()  # Target: <10s

# Topological sort performance
test_topological_sort_1000_atoms_performance()  # Target: <2s

# Queue throughput
test_backpressure_queue_throughput()  # Target: >1000 req/s

# Cost calculation performance
test_cost_guardrails_check_performance()  # Target: <100ms
```

---

## Testing Infrastructure

### Fixtures & Mocks

```python
# Common fixtures
@pytest.fixture
def sample_atoms():
    """Generate sample atomic units for testing"""

@pytest.fixture
def dependency_graph():
    """Generate sample dependency graph"""

@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy session"""

@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker for guardrails tests"""
```

### Test Utilities

```python
# Helper functions
def create_atom(atom_id, language="python", loc=10):
    """Create test atom"""

def create_dependency_edge(source, target, dep_type="import"):
    """Create test dependency"""

def assert_graph_valid(graph):
    """Validate graph structure"""
```

---

## Implementation Plan

### Phase 1: Fix Broken Tests (Day 1)
- **Task 1.1**: Fix topological_sorter test collection error
- **Task 1.2**: Update imports and module structure
- **Task 1.3**: Verify existing test infrastructure works

### Phase 2: Gap 5 - Dependency Tests (Day 1-2)
- **Task 2.1**: Create test_graph_builder.py
- **Task 2.2**: Implement symbol extraction tests (8 tests)
- **Task 2.3**: Implement dependency detection tests (10 tests)
- **Task 2.4**: Implement graph construction tests (7 tests)
- **Task 2.5**: Add integration test for accuracy

### Phase 3: Gap 6 - Atomization Tests (Day 2-3)
- **Task 3.1**: Create test_atomization.py
- **Task 3.2**: Implement decompose endpoint tests (12 tests)
- **Task 3.3**: Implement get atom tests (6 tests)
- **Task 3.4**: Implement get atoms by task tests (4 tests)
- **Task 3.5**: Implement update/delete tests (6 tests)
- **Task 3.6**: Implement stats tests (2 tests)

### Phase 4: Gap 7 - Topological Tests (Day 3)
- **Task 4.1**: Fix test collection error
- **Task 4.2**: Implement wave generation tests (8 tests)
- **Task 4.3**: Implement cycle handling tests (10 tests)
- **Task 4.4**: Implement execution plan tests (7 tests)

### Phase 5: Gap 8 - Concurrency Tests (Day 4)
- **Task 5.1**: Create test_backpressure_queue.py
- **Task 5.2**: Implement enqueue tests (6 tests)
- **Task 5.3**: Implement dequeue tests (6 tests)
- **Task 5.4**: Implement backpressure tests (4 tests)
- **Task 5.5**: Implement statistics tests (4 tests)

### Phase 6: Gap 9 - Cost Guardrails Tests (Day 4-5)
- **Task 6.1**: Create test_cost_guardrails.py
- **Task 6.2**: Implement limit configuration tests (5 tests)
- **Task 6.3**: Implement soft limit tests (6 tests)
- **Task 6.4**: Implement hard limit tests (6 tests)
- **Task 6.5**: Implement pre-execution tests (4 tests)
- **Task 6.6**: Implement status/metrics tests (4 tests)

### Phase 7: Integration & Performance (Day 5)
- **Task 7.1**: Create integration test suite (5 tests)
- **Task 7.2**: Create performance benchmarks (5 tests)
- **Task 7.3**: Run full test suite
- **Task 7.4**: Verify 100% pass rate
- **Task 7.5**: Measure and document coverage

---

## Success Metrics

### Quantitative
- **125+ tests** implemented and passing
- **≥95% code coverage** per component
- **0 test failures**
- **<30 seconds** full test suite execution
- **100% reproducible** results

### Qualitative
- **Clear test names** - Self-documenting
- **Comprehensive edge cases** - Covers error paths
- **Well-structured** - Organized by feature
- **Fast feedback** - Quick iteration cycle

---

## Dependencies

### External
- `pytest` (testing framework)
- `pytest-asyncio` (async test support)
- `unittest.mock` (mocking framework)
- `pytest-cov` (coverage reporting)

### Internal
- src/dependency/graph_builder.py (Gap 5)
- src/api/routers/atomization.py (Gap 6)
- src/dependency/topological_sorter.py (Gap 7)
- src/concurrency/backpressure_queue.py (Gap 8)
- src/cost/cost_guardrails.py (Gap 9)

---

## Risk Mitigation

### Risks
1. **Test collection errors** - Fix existing broken tests first
2. **Complex mocking** - Use well-structured fixtures
3. **Async testing complexity** - Leverage pytest-asyncio
4. **Performance test flakiness** - Use stable benchmarks

### Mitigation
- Start with Phase 1 to fix infrastructure
- Create reusable test utilities
- Use proper async patterns
- Run performance tests in isolation

---

## Documentation

### Test Documentation
- **Test naming convention**: `test_<component>_<scenario>_<expected>`
- **Docstrings required**: All test functions must have docstrings
- **Coverage reports**: Generate after each phase
- **Test summary**: Document in TESTING_SUMMARY.md

---

## Timeline

- **Day 1**: Phase 1 + Phase 2 (Fix + Gap 5)
- **Day 2-3**: Phase 3 + Phase 4 (Gap 6 + Gap 7)
- **Day 4**: Phase 5 + Phase 6 start (Gap 8 + Gap 9)
- **Day 5**: Phase 6 complete + Phase 7 (Gap 9 + Integration)

**Total**: 5 days, 125+ tests, ≥95% coverage
