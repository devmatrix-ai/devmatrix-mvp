# MGE V2 - Comprehensive Testing for Gaps 5-9 - Implementation Tasks

**Generated**: 2025-10-25
**Strategy**: Adaptive with deep analysis
**Total Phases**: 7
**Estimated Duration**: 5 days (Week 1 Mon-Fri)
**Total Tasks**: 35
**Target**: 125+ tests, ≥95% coverage

---

## Phase 1: Fix Infrastructure & Gap 7 Broken Tests (Day 1 - Mon AM)

### Task 1.1: Diagnose topological_sorter test collection error
**Complexity**: Low
**Duration**: 30 minutes
**Dependencies**: None

**Actions**:
- Read `tests/unit/test_topological_sorter.py`
- Identify import errors or module structure issues
- Check for missing dependencies or circular imports
- Document root cause

**Acceptance Criteria**:
- Root cause identified and documented
- Fix strategy determined

---

### Task 1.2: Fix topological_sorter test imports
**Complexity**: Low
**Duration**: 30 minutes
**Dependencies**: Task 1.1

**Actions**:
- Fix module imports in test file
- Update `sys.path` if needed
- Ensure `TopologicalSorter` class is importable
- Verify `ExecutionWave`, `ExecutionPlan` models import

**Acceptance Criteria**:
- `pytest tests/unit/test_topological_sorter.py --collect-only` succeeds
- No import errors
- Tests discovered successfully

---

### Task 1.3: Verify test infrastructure working
**Complexity**: Low
**Duration**: 15 minutes
**Dependencies**: Task 1.2

**Actions**:
- Run `pytest tests/unit/test_topological_sorter.py -v`
- Verify pytest configuration
- Check for fixture issues
- Run a simple smoke test

**Acceptance Criteria**:
- Tests can execute (pass or fail is OK for now)
- No collection errors
- Infrastructure functional

---

## Phase 2: Gap 5 - Dependency Graph Builder Tests (Day 1 Mon PM)

### Task 2.1: Create test_graph_builder.py with fixtures
**Complexity**: Medium
**Duration**: 1 hour
**Dependencies**: Phase 1 complete

**Actions**:
- Create `tests/unit/test_graph_builder.py`
- Add pytest imports and fixtures
- Create `sample_atoms` fixture (Python, TypeScript, JavaScript atoms)
- Create `mock_atom` helper function
- Set up test class structure

**Fixtures**:
```python
import pytest
from src.dependency.graph_builder import GraphBuilder, DependencyType
from src.models import AtomicUnit

@pytest.fixture
def sample_python_atom():
    """Create sample Python atom for testing"""
    return AtomicUnit(
        atom_id=uuid4(),
        code_to_generate='''
def calculate(x, y):
    return x + y

class Calculator:
    pass
        ''',
        language='python',
        imports={'math': ['sqrt']}
    )

@pytest.fixture
def sample_ts_atom():
    """Create sample TypeScript atom"""
    return AtomicUnit(
        atom_id=uuid4(),
        code_to_generate='''
function process(data: string): void {}
interface DataProcessor {}
        ''',
        language='typescript'
    )

@pytest.fixture
def graph_builder():
    return GraphBuilder()
```

**Acceptance Criteria**:
- Test file created with proper structure
- Fixtures defined and working
- Can import all required modules

---

### Task 2.2: Implement symbol extraction tests (8 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 2.1

**Actions**:
- Test Python function extraction: `test_extract_python_functions`
- Test Python variable extraction: `test_extract_python_variables`
- Test Python class extraction: `test_extract_python_classes`
- Test Python imports: `test_extract_python_imports`
- Test TypeScript function extraction: `test_extract_ts_functions`
- Test TypeScript variable extraction: `test_extract_ts_variables`
- Test TypeScript types/interfaces: `test_extract_ts_types_interfaces`
- Test JavaScript imports: `test_extract_js_imports`

**Test Example**:
```python
def test_extract_python_functions(graph_builder, sample_python_atom):
    """Test Python function extraction from code"""
    symbols = graph_builder._extract_symbols([sample_python_atom])

    atom_symbols = symbols[sample_python_atom.atom_id]
    assert 'calculate' in atom_symbols['defines_functions']
    assert len(atom_symbols['defines_functions']) >= 1

def test_extract_python_classes(graph_builder, sample_python_atom):
    """Test Python class extraction from code"""
    symbols = graph_builder._extract_symbols([sample_python_atom])

    atom_symbols = symbols[sample_python_atom.atom_id]
    assert 'Calculator' in atom_symbols['defines_types']
```

**Acceptance Criteria**:
- 8 tests implemented and passing
- Covers Python, TypeScript, JavaScript
- Symbol extraction verified for functions, variables, types, imports

---

### Task 2.3: Implement dependency detection tests (10 tests)
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: Task 2.2

**Actions**:
- Test function call dependencies: `test_detect_function_call_dependency`
- Test self-dependency filtering: `test_ignore_self_dependencies`
- Test cross-file calls: `test_detect_cross_file_function_calls`
- Test variable usage: `test_detect_variable_usage`
- Test shared variables: `test_detect_shared_variables`
- Test type usage: `test_detect_type_usage`
- Test interface implementation: `test_detect_interface_implementation`
- Test module imports: `test_detect_module_imports`
- Test barrel files: `test_detect_barrel_file_imports`
- Test dynamic imports: `test_detect_dynamic_imports`

**Test Example**:
```python
def test_detect_function_call_dependency(graph_builder):
    """Test detection of function call dependencies between atoms"""
    # Atom A defines function foo()
    atom_a = AtomicUnit(
        atom_id=uuid4(),
        code_to_generate='def foo(): return 42',
        language='python'
    )

    # Atom B calls foo()
    atom_b = AtomicUnit(
        atom_id=uuid4(),
        code_to_generate='result = foo()',
        language='python'
    )

    atoms = [atom_a, atom_b]
    symbols = graph_builder._extract_symbols(atoms)
    dependencies = graph_builder._detect_dependencies(atoms, symbols)

    # Should find dependency from B → A
    func_deps = [d for d in dependencies
                 if d.dependency_type == DependencyType.FUNCTION_CALL]
    assert len(func_deps) > 0
    assert any(d.source_atom_id == atom_b.atom_id and
               d.target_atom_id == atom_a.atom_id
               for d in func_deps)
```

**Acceptance Criteria**:
- 10 tests implemented and passing
- Dependency detection works across all types
- Self-dependencies filtered correctly
- Multi-language support verified

---

### Task 2.4: Implement graph construction tests (7 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 2.3

**Actions**:
- Test single atom graph: `test_build_graph_single_atom`
- Test multiple atoms: `test_build_graph_multiple_atoms`
- Test node attributes: `test_graph_node_attributes`
- Test edge attributes: `test_graph_edge_attributes`
- Test dependency weights: `test_graph_dependency_weights`
- Test isolated nodes: `test_isolated_nodes_detection`
- Test cycle detection: `test_cycle_detection`

**Test Example**:
```python
def test_build_graph_multiple_atoms(graph_builder):
    """Test graph construction with multiple interconnected atoms"""
    atoms = [create_test_atom(i) for i in range(5)]
    graph = graph_builder.build_graph(atoms)

    assert graph.number_of_nodes() == 5
    assert graph.number_of_edges() >= 0

    # Verify all nodes have required attributes
    for node in graph.nodes():
        assert 'atom_number' in graph.nodes[node]
        assert 'language' in graph.nodes[node]
        assert 'loc' in graph.nodes[node]
```

**Acceptance Criteria**:
- 7 tests implemented and passing
- Graph structure validated
- Node/edge attributes verified
- Cycle detection working

---

### Task 2.5: Add graph builder integration test
**Complexity**: High
**Duration**: 1 hour
**Dependencies**: Task 2.4

**Actions**:
- Create integration test with complex multi-file scenario
- Test accuracy against known ground truth
- Verify ≥90% edge accuracy requirement
- Test performance with 100+ atoms

**Test Example**:
```python
def test_graph_builder_accuracy_vs_ground_truth(graph_builder):
    """Integration test: verify accuracy against known dependency structure"""
    # Load test suite with known dependencies
    test_atoms = load_test_atoms_with_ground_truth()
    ground_truth_edges = load_ground_truth_dependencies()

    graph = graph_builder.build_graph(test_atoms)
    detected_edges = set(graph.edges())

    # Calculate accuracy
    true_positives = len(detected_edges & ground_truth_edges)
    false_positives = len(detected_edges - ground_truth_edges)
    false_negatives = len(ground_truth_edges - detected_edges)

    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)

    assert precision >= 0.90, f"Precision {precision:.2%} < 90%"
    assert recall >= 0.90, f"Recall {recall:.2%} < 90%"
```

**Acceptance Criteria**:
- Integration test passes
- ≥90% edge accuracy verified
- Performance acceptable (<5s for 100 atoms)
- **Total: 25+ tests passing for Gap 5**

---

## Phase 3: Gap 6 - Atomization API Tests (Day 2 Tue)

### Task 3.1: Create test_atomization.py with FastAPI test client
**Complexity**: Medium
**Duration**: 1 hour
**Dependencies**: Phase 2 complete

**Actions**:
- Create `tests/api/routers/test_atomization.py`
- Set up FastAPI TestClient
- Create database fixtures (mock or test DB)
- Create sample task fixtures
- Set up test class structure

**Fixtures**:
```python
import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.config.database import get_db

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def mock_db_session(monkeypatch):
    """Mock database session"""
    mock_session = MagicMock()
    monkeypatch.setattr("src.api.routers.atomization.get_db",
                       lambda: mock_session)
    return mock_session

@pytest.fixture
def sample_task():
    """Sample task for atomization"""
    return Task(
        task_id=uuid4(),
        code="def process(): pass",
        language="python"
    )
```

**Acceptance Criteria**:
- Test file created
- FastAPI TestClient configured
- Fixtures working
- Can make test requests

---

### Task 3.2: Implement decompose endpoint tests (12 tests)
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: Task 3.1

**Actions**:
- Test valid decomposition: `test_decompose_valid_task`
- Test atoms returned: `test_decompose_returns_atoms`
- Test stats calculation: `test_decompose_calculates_stats`
- Test atomicity scores: `test_decompose_atomicity_scores`
- Test context completeness: `test_decompose_context_completeness`
- Test invalid task ID: `test_decompose_invalid_task_id`
- Test task not found: `test_decompose_task_not_found`
- Test empty task: `test_decompose_empty_task`
- Test large task (100 atoms): `test_decompose_large_task_100_atoms`
- Test multi-language: `test_decompose_multi_language_task`
- Test complex task: `test_decompose_complex_task`
- Test complete pipeline: `test_decompose_pipeline_complete`

**Test Example**:
```python
def test_decompose_valid_task(client, mock_db_session, sample_task):
    """Test successful task decomposition"""
    response = client.post(
        "/api/v2/atomization/decompose",
        json={"task_id": str(sample_task.task_id)}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["task_id"] == str(sample_task.task_id)
    assert data["total_atoms"] > 0
    assert "atoms" in data
    assert "stats" in data

def test_decompose_atomicity_scores(client, mock_db_session):
    """Test that atomicity scores are calculated"""
    response = client.post(
        "/api/v2/atomization/decompose",
        json={"task_id": str(uuid4())}
    )

    data = response.json()
    for atom in data["atoms"]:
        assert "atomicity_score" in atom
        assert 0 <= atom["atomicity_score"] <= 1.0
        assert "is_atomic" in atom
```

**Acceptance Criteria**:
- 12 tests implemented and passing
- All success paths covered
- All error paths covered
- Edge cases tested (large, empty, complex)

---

### Task 3.3: Implement CRUD endpoint tests (12 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 3.2

**Actions**:
- GET atom tests (6 tests): valid, all fields, scores, invalid, not found, status
- GET atoms by task (4 tests): valid, count, empty, invalid
- UPDATE atom tests (4 tests): name, code, status, not found
- DELETE atom tests (2 tests): success, not found

**Test Example**:
```python
def test_get_atom_valid_id(client):
    """Test retrieving atom by valid ID"""
    atom_id = create_test_atom()

    response = client.get(f"/api/v2/atoms/{atom_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["atom_id"] == str(atom_id)
    assert all(field in data for field in [
        "atom_number", "name", "description", "language",
        "loc", "complexity", "atomicity_score"
    ])

def test_update_atom_code(client):
    """Test updating atom code"""
    atom_id = create_test_atom()
    new_code = "def updated(): pass"

    response = client.put(
        f"/api/v2/atoms/{atom_id}",
        json={"code_to_generate": new_code}
    )

    assert response.status_code == 200
    data = response.json()
    assert new_code in data.get("code_to_generate", "")
```

**Acceptance Criteria**:
- 12 tests implemented and passing
- All CRUD operations tested
- Error handling verified

---

### Task 3.4: Implement stats endpoint tests (2 tests)
**Complexity**: Low
**Duration**: 30 minutes
**Dependencies**: Task 3.3

**Actions**:
- Test stats retrieval: `test_get_decomposition_stats`
- Test stats accuracy: `test_stats_accuracy`

**Acceptance Criteria**:
- 2 tests implemented and passing
- Stats calculation verified
- **Total: 30+ tests passing for Gap 6**

---

## Phase 4: Gap 7 - Topological Sorter Tests (Day 3 Wed)

### Task 4.1: Enhance broken topological_sorter tests
**Complexity**: Medium
**Duration**: 1 hour
**Dependencies**: Phase 1 complete

**Actions**:
- Review existing test structure
- Add missing test cases
- Fix any remaining issues
- Ensure comprehensive coverage

**Acceptance Criteria**:
- All existing tests passing
- Test structure enhanced
- Ready for new tests

---

### Task 4.2: Implement wave generation tests (8 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 4.1

**Actions**:
- Test single wave: `test_generate_waves_single_wave`
- Test multiple waves: `test_generate_waves_multiple_waves`
- Test sequential deps: `test_generate_waves_sequential_dependencies`
- Test wave levels: `test_wave_level_assignment`
- Test parallelism calc: `test_wave_parallelism_calculation`
- Test max parallelism: `test_max_parallelism_tracking`
- Test avg parallelism: `test_avg_parallelism_calculation`
- Test duration estimate: `test_estimated_duration_calculation`

**Test Example**:
```python
def test_generate_waves_multiple_waves(topological_sorter):
    """Test wave generation with multiple dependency levels"""
    # Create graph: A → B → C (3 waves)
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")

    atoms = [create_atom("A"), create_atom("B"), create_atom("C")]
    plan = topological_sorter.create_execution_plan(graph, atoms)

    assert plan.total_waves == 3
    assert plan.waves[0].wave_number == 0
    assert plan.waves[0].atom_ids == [atoms[0].atom_id]  # A has no deps
    assert plan.waves[1].atom_ids == [atoms[1].atom_id]  # B depends on A
    assert plan.waves[2].atom_ids == [atoms[2].atom_id]  # C depends on B
```

**Acceptance Criteria**:
- 8 tests implemented and passing
- Wave generation logic verified
- Parallelism calculations correct

---

### Task 4.3: Implement cycle handling tests (10 tests)
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: Task 4.2

**Actions**:
- Test simple cycle detection: `test_detect_simple_cycle`
- Test complex cycles: `test_detect_complex_cycles`
- Test FAS breaking: `test_break_cycles_with_fas`
- Test FAS minimality: `test_feedback_arc_set_minimal`
- Test DAG preservation: `test_cycle_breaking_preserves_dag`
- Test cycle info logging: `test_cycle_info_logging`
- Test edge tracking: `test_removed_edges_tracking`
- Test multiple cycles: `test_multiple_cycles_handling`
- Test cycle count: `test_cycle_count_accuracy`
- Test DAG validation: `test_dag_validation_after_breaking`

**Test Example**:
```python
def test_break_cycles_with_fas(topological_sorter):
    """Test cycle breaking using feedback arc set"""
    # Create cycle: A → B → C → A
    graph = nx.DiGraph()
    graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])

    atoms = [create_atom(id) for id in ["A", "B", "C"]]

    # This should break the cycle
    plan = topological_sorter.create_execution_plan(graph, atoms)

    assert plan.has_cycles is True
    assert len(plan.cycle_info) > 0
    # After breaking, should be able to sort
    assert plan.total_waves > 0
    # Verify DAG
    assert nx.is_directed_acyclic_graph(graph)
```

**Acceptance Criteria**:
- 10 tests implemented and passing
- Cycle detection working
- FAS algorithm verified
- DAG preservation confirmed

---

### Task 4.4: Implement execution plan tests (7 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 4.3

**Actions**:
- Test simple plan: `test_create_execution_plan_simple`
- Test complex plan: `test_create_execution_plan_complex`
- Test wave count: `test_execution_plan_wave_count`
- Test atom distribution: `test_execution_plan_atom_distribution`
- Test deps satisfied: `test_execution_plan_dependencies_satisfied`
- Test has cycles flag: `test_execution_plan_has_cycles_flag`
- Test statistics: `test_execution_plan_statistics`

**Acceptance Criteria**:
- 7 tests implemented and passing
- Execution plan creation verified
- Statistics accurate
- **Total: 25+ tests passing for Gap 7**

---

## Phase 5: Gap 8 - Concurrency Controller Tests (Day 4 Thu)

### Task 5.1: Create test_backpressure_queue.py
**Complexity**: Low
**Duration**: 30 minutes
**Dependencies**: Phase 4 complete

**Actions**:
- Create `tests/unit/test_backpressure_queue.py`
- Set up pytest fixtures
- Create sample request fixtures
- Set up test class structure

**Acceptance Criteria**:
- Test file created
- Fixtures defined
- Infrastructure ready

---

### Task 5.2: Implement enqueue tests (6 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 5.1

**Actions**:
- Test successful enqueue: `test_enqueue_success`
- Test priority handling: `test_enqueue_with_priority`
- Test queue full rejection: `test_enqueue_queue_full_rejection`
- Test statistics update: `test_enqueue_updates_statistics`
- Test rejected count: `test_enqueue_rejected_count`
- Test concurrent requests: `test_enqueue_concurrent_requests`

**Test Example**:
```python
@pytest.mark.asyncio
async def test_enqueue_success():
    """Test successful request enqueue"""
    queue = BackpressureQueue(max_queue_size=10)

    success = await queue.enqueue(
        request_id="req-1",
        payload={"data": "test"},
        priority=5
    )

    assert success is True
    stats = queue.get_statistics()
    assert stats['current_size'] == 1
    assert stats['enqueued_total'] == 1

@pytest.mark.asyncio
async def test_enqueue_queue_full_rejection():
    """Test backpressure when queue is full"""
    queue = BackpressureQueue(max_queue_size=2)

    # Fill queue
    await queue.enqueue("req-1", {}, 5)
    await queue.enqueue("req-2", {}, 5)

    # This should fail
    success = await queue.enqueue("req-3", {}, 5)

    assert success is False
    stats = queue.get_statistics()
    assert stats['rejected_count'] == 1
```

**Acceptance Criteria**:
- 6 tests implemented and passing
- Enqueue logic verified
- Backpressure working

---

### Task 5.3: Implement dequeue tests (6 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 5.2

**Actions**:
- Test priority order: `test_dequeue_priority_order`
- Test FIFO within priority: `test_dequeue_fifo_within_priority`
- Test timeout: `test_dequeue_timeout`
- Test expired requests: `test_dequeue_request_expired`
- Test empty queue: `test_dequeue_empty_queue`
- Test statistics: `test_dequeue_updates_statistics`

**Test Example**:
```python
@pytest.mark.asyncio
async def test_dequeue_priority_order():
    """Test that higher priority (lower number) dequeues first"""
    queue = BackpressureQueue()

    # Enqueue with different priorities
    await queue.enqueue("low", {}, priority=9)
    await queue.enqueue("high", {}, priority=1)
    await queue.enqueue("medium", {}, priority=5)

    # Should dequeue in priority order
    req1 = await queue.dequeue()
    assert req1.request_id == "high"

    req2 = await queue.dequeue()
    assert req2.request_id == "medium"

    req3 = await queue.dequeue()
    assert req3.request_id == "low"
```

**Acceptance Criteria**:
- 6 tests implemented and passing
- Priority logic verified
- Timeout handling working

---

### Task 5.4: Implement backpressure & statistics tests (8 tests)
**Complexity**: Low
**Duration**: 1.5 hours
**Dependencies**: Task 5.3

**Actions**:
- Test capacity threshold: `test_is_at_capacity_threshold_80`
- Test below threshold: `test_is_at_capacity_below_threshold`
- Test backpressure signal: `test_backpressure_signal_when_full`
- Test recovery: `test_queue_recovery_after_backpressure`
- Test enqueued count: `test_statistics_enqueued_count`
- Test dequeued count: `test_statistics_dequeued_count`
- Test timeout count: `test_statistics_timeout_count`
- Test rejected count: `test_statistics_rejected_count`

**Acceptance Criteria**:
- 8 tests implemented and passing
- Backpressure logic verified
- Statistics accurate
- **Total: 20+ tests passing for Gap 8**

---

## Phase 6: Gap 9 - Cost Guardrails Tests (Day 4-5 Thu-Fri)

### Task 6.1: Create test_cost_guardrails.py with mocks
**Complexity**: Medium
**Duration**: 1 hour
**Dependencies**: Task 5.4

**Actions**:
- Create `tests/unit/test_cost_guardrails.py`
- Mock CostTracker dependency
- Create sample masterplan fixtures
- Set up test class structure

**Fixtures**:
```python
@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker for testing"""
    tracker = MagicMock()
    tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=25.0,
        call_count=100
    )
    return tracker

@pytest.fixture
def cost_guardrails(mock_cost_tracker):
    return CostGuardrails(
        cost_tracker=mock_cost_tracker,
        default_soft_limit=50.0,
        default_hard_limit=100.0
    )
```

**Acceptance Criteria**:
- Test file created
- Mocks configured
- Fixtures working

---

### Task 6.2: Implement limit configuration tests (5 tests)
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 6.1

**Actions**:
- Test set limits: `test_set_masterplan_limits`
- Test defaults: `test_default_limits`
- Test custom limits: `test_custom_limits`
- Test per-atom limits: `test_per_atom_limits`
- Test validation: `test_soft_less_than_hard_validation`

**Acceptance Criteria**:
- 5 tests implemented and passing
- Configuration logic verified

---

### Task 6.3: Implement soft limit tests (6 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 6.2

**Actions**:
- Test soft warning: `test_soft_limit_warning`
- Test alert triggered: `test_soft_limit_alert_triggered`
- Test no repeat: `test_soft_limit_not_repeated`
- Test usage %: `test_soft_limit_usage_percentage`
- Test reset: `test_soft_limit_reset`
- Test multiple masterplans: `test_multiple_masterplans_soft_limits`

**Test Example**:
```python
def test_soft_limit_warning(cost_guardrails, mock_cost_tracker):
    """Test soft limit triggers warning but allows continuation"""
    # Set current cost to 55 (above soft limit of 50)
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=55.0, call_count=200
    )

    masterplan_id = uuid4()
    result = cost_guardrails.check_limits(masterplan_id)

    assert result['soft_limit_exceeded'] is True
    assert result['hard_limit_exceeded'] is False
    assert result['within_limits'] is True  # Still within hard limit
    assert result['usage_percentage'] == 55.0
```

**Acceptance Criteria**:
- 6 tests implemented and passing
- Soft limit behavior verified

---

### Task 6.4: Implement hard limit tests (6 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 6.3

**Actions**:
- Test exception raised: `test_hard_limit_exception_raised`
- Test execution blocked: `test_hard_limit_blocks_execution`
- Test exact threshold: `test_hard_limit_exact_threshold`
- Test alert triggered: `test_hard_limit_alert_triggered`
- Test per-atom limit: `test_hard_limit_per_atom`
- Test 100% usage: `test_hard_limit_usage_100_percent`

**Test Example**:
```python
def test_hard_limit_exception_raised(cost_guardrails, mock_cost_tracker):
    """Test CostLimitExceeded exception when hard limit hit"""
    # Set current cost to 105 (above hard limit of 100)
    mock_cost_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=105.0, call_count=500
    )

    masterplan_id = uuid4()

    with pytest.raises(CostLimitExceeded) as exc_info:
        cost_guardrails.check_limits(masterplan_id)

    assert exc_info.value.current_cost == 105.0
    assert exc_info.value.limit == 100.0
```

**Acceptance Criteria**:
- 6 tests implemented and passing
- Hard limit blocking verified
- Exception handling working

---

### Task 6.5: Implement pre-execution & status tests (8 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 6.4

**Actions**:
- Test pre-check passes: `test_check_before_execution_passes`
- Test pre-check blocks: `test_check_before_execution_blocks`
- Test estimated cost: `test_check_before_execution_estimated_cost`
- Test projection: `test_check_before_execution_projection`
- Test status retrieval: `test_get_limit_status`
- Test remaining budget: `test_remaining_budget_calculation`
- Test usage accuracy: `test_usage_percentage_accuracy`
- Test calls tracking: `test_calls_made_tracking`

**Acceptance Criteria**:
- 8 tests implemented and passing
- Pre-execution checks working
- Status reporting accurate
- **Total: 25+ tests passing for Gap 9**

---

## Phase 7: Integration, Performance & Final Validation (Day 5 Fri)

### Task 7.1: Create cross-component integration tests (5 tests)
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: All previous phases complete

**Actions**:
- Test dependency → atomization flow
- Test atomization → topological sort → execution
- Test concurrency + cost guardrails integration
- Test E2E pipeline integration
- Test error propagation

**Test Example**:
```python
@pytest.mark.asyncio
async def test_e2e_pipeline_integration():
    """Integration test: Full pipeline from dependency graph to execution"""
    # 1. Build dependency graph
    graph_builder = GraphBuilder()
    atoms = create_complex_atom_set(50)
    graph = graph_builder.build_graph(atoms)

    # 2. Create execution plan
    sorter = TopologicalSorter()
    plan = sorter.create_execution_plan(graph, atoms)

    # 3. Check cost guardrails
    guardrails = CostGuardrails(cost_tracker)
    guardrails.check_before_execution(masterplan_id, estimated_tokens=100000)

    # 4. Execute with concurrency control
    queue = BackpressureQueue()
    # ... execute waves

    assert plan.total_waves > 0
    assert not guardrails.check_limits(masterplan_id)['hard_limit_exceeded']
```

**Acceptance Criteria**:
- 5 integration tests passing
- Component interactions verified
- E2E flow working

---

### Task 7.2: Create performance benchmarks (5 tests)
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 7.1

**Actions**:
- Benchmark dependency graph with 1000 atoms (target: <5s)
- Benchmark atomization large task (target: <10s)
- Benchmark topological sort 1000 atoms (target: <2s)
- Benchmark queue throughput (target: >1000 req/s)
- Benchmark cost check (target: <100ms)

**Test Example**:
```python
import time

def test_dependency_graph_1000_atoms_performance():
    """Benchmark: Dependency graph with 1000 atoms should complete in <5s"""
    graph_builder = GraphBuilder()
    atoms = [create_random_atom() for _ in range(1000)]

    start = time.time()
    graph = graph_builder.build_graph(atoms)
    duration = time.time() - start

    assert duration < 5.0, f"Too slow: {duration:.2f}s > 5.0s"
    assert graph.number_of_nodes() == 1000
```

**Acceptance Criteria**:
- 5 performance tests passing
- All benchmarks within targets
- Performance documented

---

### Task 7.3: Run full test suite & verify coverage
**Complexity**: Low
**Duration**: 30 minutes
**Dependencies**: Task 7.2

**Actions**:
- Run all 125+ tests
- Generate coverage report
- Verify ≥95% coverage per component
- Document any gaps

**Commands**:
```bash
pytest tests/unit/test_graph_builder.py -v
pytest tests/api/routers/test_atomization.py -v
pytest tests/unit/test_topological_sorter.py -v
pytest tests/unit/test_backpressure_queue.py -v
pytest tests/unit/test_cost_guardrails.py -v

# Coverage
pytest tests/unit tests/api/routers --cov=src/dependency \
       --cov=src/api/routers/atomization --cov=src/concurrency \
       --cov=src/cost --cov-report=html
```

**Acceptance Criteria**:
- 125+ tests passing (100% pass rate)
- ≥95% coverage per component
- No critical gaps identified

---

### Task 7.4: Document testing results
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 7.3

**Actions**:
- Create `TESTING_SUMMARY.md` in `DOCS/MGE_V2/`
- Document test counts per component
- Document coverage percentages
- Document performance benchmarks
- Create test execution guide

**Documentation Structure**:
```markdown
# MGE V2 Gaps 5-9 Testing Summary

## Test Coverage by Component
- Gap 5 (Dependencies): 25+ tests, 96% coverage
- Gap 6 (Atomization): 30+ tests, 95% coverage
- Gap 7 (Topological): 25+ tests, 97% coverage
- Gap 8 (Concurrency): 20+ tests, 98% coverage
- Gap 9 (Cost): 25+ tests, 96% coverage

## Performance Benchmarks
- Dependency graph (1000 atoms): 3.2s
- ...

## Execution Guide
...
```

**Acceptance Criteria**:
- Documentation complete
- Test execution guide clear
- All metrics documented

---

### Task 7.5: Update precision readiness checklist
**Complexity**: Low
**Duration**: 30 minutes
**Dependencies**: Task 7.4

**Actions**:
- Update `DOCS/MGE_V2/precision_readiness_checklist.md`
- Mark Gaps 5, 6, 7, 8, 9 with test status
- Update completion percentages
- Document next priorities

**Updates**:
```markdown
## Gap 5: Dependencies - ✅ IMPLEMENTED + TESTED (NEW)
- [x] GraphBuilder with 350 LOC
- [x] 25+ tests passing, 96% coverage

## Gap 6: Atomization - ✅ IMPLEMENTED + TESTED (NEW)
- [x] 6 REST endpoints
- [x] 30+ tests passing, 95% coverage
...
```

**Acceptance Criteria**:
- Checklist updated
- All gaps marked correctly
- Next priorities clear

---

## Success Metrics

### Quantitative Targets
- ✅ **125+ tests** implemented and passing (100% pass rate)
- ✅ **≥95% code coverage** per component
- ✅ **0 test failures**
- ✅ **<30 seconds** full test suite execution
- ✅ **5 integration tests** passing
- ✅ **5 performance benchmarks** within targets

### Quality Gates
- ✅ No flaky tests (100% reproducible)
- ✅ Clear, self-documenting test names
- ✅ Comprehensive error path coverage
- ✅ All edge cases tested
- ✅ Proper mocking and isolation

### Documentation
- ✅ TESTING_SUMMARY.md complete
- ✅ Test execution guide clear
- ✅ Coverage reports generated
- ✅ Performance benchmarks documented

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test collection errors persist | Low | High | Phase 1 fixes infrastructure first |
| Complex mocking challenges | Medium | Medium | Use well-structured fixtures, start simple |
| Async test complexity | Medium | Medium | Leverage pytest-asyncio, clear patterns |
| Performance test flakiness | Low | Medium | Run in isolation, stable benchmarks |
| Coverage gaps | Low | High | Systematic testing of all code paths |

---

## Dependencies

### External
- pytest (>=7.4.4)
- pytest-asyncio (>=0.23.3)
- pytest-cov (>=6.2.1)
- httpx (<0.28) - FastAPI TestClient

### Internal
- src/dependency/graph_builder.py
- src/api/routers/atomization.py
- src/dependency/topological_sorter.py
- src/concurrency/backpressure_queue.py
- src/cost/cost_guardrails.py

---

## Timeline Summary

- **Day 1 (Mon)**: Phase 1 + Phase 2 (Fix infra + Gap 5 deps tests)
- **Day 2 (Tue)**: Phase 3 (Gap 6 atomization tests)
- **Day 3 (Wed)**: Phase 4 (Gap 7 topological tests)
- **Day 4 (Thu)**: Phase 5 + Phase 6 start (Gap 8 + Gap 9)
- **Day 5 (Fri)**: Phase 6 complete + Phase 7 (Gap 9 + Integration + Performance)

**Total Duration**: 5 days
**Total Tasks**: 35 tasks
**Total Tests**: 125+ tests
**Target Coverage**: ≥95% per component
