# Testing Strategy

**Document**: 12 of 15
**Purpose**: Comprehensive testing plan for MGE v2

---

## Testing Pyramid

```
        E2E Tests (10%)
       /                \
    Integration Tests (30%)
   /                          \
Unit Tests (60%)
```

---

## Unit Tests (60% of test suite)

### Phase 3: AST Atomization
```python
# test_ast_parser.py

def test_python_parser():
    """Test Python AST parsing."""
    parser = MultiLanguageParser()
    code = "def add(a, b):\n    return a + b"
    tree = parser.parse_code(code, 'python')
    assert tree.root_node.type == 'module'

def test_recursive_decomposition():
    """Test recursive decomposition."""
    decomposer = RecursiveDecomposer(ASTClassifier())
    # Test with sample code...
    atoms = decomposer.decompose_task(...)
    assert len(atoms) >= 1
    assert all(a.estimated_loc <= 15 for a in atoms)

def test_context_injection():
    """Test context completeness."""
    injector = ContextInjector(parser)
    atoms = injector.enrich_atoms(...)
    assert all(a.context.get('completeness_score', 0) >= 0.90 for a in atoms)

# Target: 100+ unit tests, 95%+ coverage
```

### Phase 4: Dependency Graph
```python
# test_dependency_graph.py

def test_dependency_detection():
    """Test dependency analysis."""
    analyzer = DependencyAnalyzer(atoms)
    deps = analyzer.analyze_all_dependencies()
    assert len(deps) > 0

def test_topological_sort():
    """Test topological ordering."""
    graph = DependencyGraph()
    graph.build_from_atoms(atoms, dependencies)
    order = graph.topological_sort()
    # Verify dependencies come before dependents
    assert verify_dependency_order(order, dependencies)

def test_cycle_detection():
    """Test cycle detection."""
    graph = build_graph_with_cycle()
    assert not nx.is_directed_acyclic_graph(graph.graph)
    cycles = graph.detect_cycles()
    assert len(cycles) > 0

# Target: 50+ unit tests, 90%+ coverage
```

### Phase 5: Validation
```python
# test_validation.py

def test_atomic_validation():
    """Test Level 1 validation."""
    validator = AtomicValidator()
    result = validator.validate(good_atom)
    assert result.passed
    assert result.score >= 0.80

def test_validation_detects_errors():
    """Test error detection."""
    bad_atom = create_atom_with_syntax_error()
    result = validator.validate(bad_atom)
    assert not result.passed
    assert any(i.severity == ValidationSeverity.CRITICAL for i in result.issues)

# Target: 80+ unit tests, 95%+ coverage
```

---

## Integration Tests (30% of test suite)

### End-to-End Phase Testing
```python
# test_phase_integration.py

def test_phase3_to_phase4_integration():
    """Test Phase 3 → Phase 4 pipeline."""
    # Phase 3: Atomize
    atoms = atomization_pipeline.atomize_task(task)
    
    # Phase 4: Build graph
    graph, plan = dependency_pipeline.process_atoms(atoms)
    
    # Verify integration
    assert len(atoms) == len(graph.graph.nodes)
    assert plan is not None
    assert len(plan) > 0

def test_validation_execution_integration():
    """Test Phase 5 → Phase 6 pipeline."""
    # Phase 5: Validate
    validation_results = validation_pipeline.validate_all(atoms, project_path)
    
    # Phase 6: Execute (mock LLM)
    execution_results = execution_pipeline.execute_plan(plan, atoms)
    
    # Verify all atoms processed
    assert len(execution_results) == len(atoms)

# Target: 40+ integration tests
```

---

## End-to-End Tests (10% of test suite)

### Real Project Tests
```python
# test_e2e.py

def test_complete_project_generation():
    """Test complete MGE v2 pipeline on real project."""
    
    # Input: Simple e-commerce project spec
    project_spec = {
        'name': 'Simple Shop',
        'entities': ['User', 'Product', 'Order'],
        'tech_stack': 'Python + FastAPI'
    }
    
    # Run complete pipeline
    result = mge_v2_complete_pipeline(project_spec)
    
    # Assertions
    assert result['precision'] >= 0.95
    assert result['total_atoms'] >= 50
    assert result['execution_time'] < 7200  # < 2 hours
    assert result['cost'] < 250  # < $250
    
    # Verify generated code
    assert os.path.exists(result['output_path'])
    assert build_succeeds(result['output_path'])
    assert tests_pass(result['output_path'])

# Target: 10+ E2E tests on real projects
```

---

## Test Data

### Sample Projects for Testing

```yaml
test_projects:
  simple_api:
    description: "Simple REST API with 3 models"
    expected_atoms: 50-80
    expected_time: 30-45 min
    target_precision: 98%
  
  ecommerce:
    description: "E-commerce with auth, catalog, orders"
    expected_atoms: 150-200
    expected_time: 60-90 min
    target_precision: 97%
  
  blog_platform:
    description: "Blog with users, posts, comments"
    expected_atoms: 100-150
    expected_time: 45-75 min
    target_precision: 98%
  
  complex_saas:
    description: "Multi-tenant SaaS with billing"
    expected_atoms: 400-600
    expected_time: 2-3 hours
    target_precision: 95%
```

---

## Performance Benchmarks

### Benchmark Suite
```python
# test_performance.py

@pytest.mark.benchmark
def test_atomization_performance(benchmark):
    """Benchmark atomization speed."""
    result = benchmark(
        lambda: atomization_pipeline.atomize_task(sample_task)
    )
    assert result.execution_time < 5.0  # < 5 seconds

@pytest.mark.benchmark
def test_dependency_graph_performance(benchmark):
    """Benchmark graph building."""
    result = benchmark(
        lambda: dependency_pipeline.process_atoms(atoms_800)
    )
    assert result.execution_time < 10.0  # < 10 seconds

@pytest.mark.benchmark
def test_validation_performance(benchmark):
    """Benchmark validation speed."""
    result = benchmark(
        lambda: validation_pipeline.validate_all(atoms_800, path)
    )
    assert result.execution_time < 120.0  # < 2 minutes
```

---

## Coverage Targets

| Component | Unit Tests | Integration Tests | E2E Tests | Target Coverage |
|-----------|------------|-------------------|-----------|-----------------|
| AST Parser | 30 | 5 | 1 | 95% |
| Decomposer | 25 | 5 | 1 | 95% |
| Context Injector | 20 | 5 | 1 | 90% |
| Dependency Analyzer | 20 | 5 | 1 | 90% |
| Graph Builder | 20 | 5 | 1 | 95% |
| Validators (all) | 40 | 10 | 2 | 95% |
| Executors | 30 | 10 | 3 | 90% |
| Review System | 15 | 5 | 1 | 85% |
| **Total** | **200+** | **50+** | **10+** | **90%+** |

---

## Continuous Integration

```yaml
# .github/workflows/test.yml

name: MGE v2 Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services (PostgreSQL, Neo4j)
        run: docker-compose up -d
      - name: Run integration tests
        run: pytest tests/integration/ -v
  
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E tests
        run: pytest tests/e2e/ -v --slow
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## Quality Gates

```python
# Pre-merge requirements

quality_gates = {
    'test_coverage': 90,        # Minimum 90% coverage
    'test_pass_rate': 100,      # All tests must pass
    'performance_regression': 0.10,  # Max 10% slowdown
    'precision_target': 0.95,   # Min 95% precision on test projects
    'cost_per_project': 250     # Max $250 per test project
}

def check_quality_gates(test_results):
    """Verify all quality gates pass."""
    for gate, threshold in quality_gates.items():
        actual = test_results[gate]
        if actual < threshold:
            raise Exception(f"{gate} failed: {actual} < {threshold}")
    
    return True
```

---

**Next Document**: [13_PERFORMANCE_COST.md](13_PERFORMANCE_COST.md)
