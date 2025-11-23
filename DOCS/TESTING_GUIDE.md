# Testing Guide - Phase 2 Validation Extraction

## Quick Start

### Run All Phase 2 Tests
```bash
# Run all Phase 2 cognitive tests
pytest tests/cognitive/ -v

# Run with coverage report
pytest tests/cognitive/ -v --cov=src/services/business_logic_extractor --cov-report=html
```

### Run Specific Test Suites

#### Unit Tests Only
```bash
pytest tests/cognitive/unit/test_llm_validation_extractor.py -v
```

#### Integration Tests Only
```bash
pytest tests/cognitive/integration/test_phase2_extraction_integration.py -v
```

#### E2E Tests Only
```bash
pytest tests/cognitive/e2e/test_phase2_e2e.py -v
```

#### Coverage Measurement Tests
```bash
pytest tests/cognitive/validation/test_validation_coverage.py -v
```

## Test Categories

### Unit Tests (Fast, No Dependencies)
**Purpose**: Test individual components in isolation with mocks
**Run Time**: <10 seconds
**Command**:
```bash
pytest tests/cognitive/unit/ -m unit -v
```

**Test Files**:
- `test_llm_validation_extractor.py` - LLM extraction logic tests
- `test_pattern_classifier.py` - Pattern matching tests

### Integration Tests (Require Mocks)
**Purpose**: Test component interaction and stage pipeline
**Run Time**: <30 seconds
**Command**:
```bash
pytest tests/cognitive/integration/ -m integration -v
```

**Test Files**:
- `test_phase2_extraction_integration.py` - Stage interaction tests
- `test_pattern_feedback_integration.py` - Pattern learning integration

### E2E Tests (Real Scenarios)
**Purpose**: End-to-end validation extraction pipeline
**Run Time**: <60 seconds
**Command**:
```bash
pytest tests/cognitive/e2e/ -m e2e -v
```

**Test Files**:
- `test_phase2_e2e.py` - Full extraction pipeline tests

### Real API Tests (Requires API Key, Costs Money)
**Purpose**: Test with real Anthropic API calls
**Run Time**: <120 seconds
**Command**:
```bash
# Set API key first
export ANTHROPIC_API_KEY="sk-ant-..."

# Run real API tests
pytest tests/cognitive/ -m real_api -v
```

**Warning**: These tests make real API calls and will consume tokens/cost money

## Test Markers

Use pytest markers to filter tests:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only E2E tests
pytest -m e2e

# Run only real API tests (requires API key)
pytest -m real_api

# Skip slow tests
pytest -m "not slow"

# Skip real API tests (default for CI)
pytest -m "not real_api"
```

## Coverage Measurement

### Generate Coverage Report
```bash
# HTML coverage report
pytest tests/cognitive/ --cov=src/services/business_logic_extractor \
                        --cov=src/cognitive/ir/ \
                        --cov-report=html

# Open report
open htmlcov/index.html
```

### Coverage Targets
- **Unit Tests**: >90% code coverage
- **Integration Tests**: >85% integration paths
- **E2E Tests**: >80% end-to-end scenarios

### Check Coverage Threshold
```bash
# Fail if coverage below 90%
pytest tests/cognitive/unit/ --cov=src/services/business_logic_extractor --cov-fail-under=90
```

## Debugging Tests

### Run Single Test
```bash
# Run specific test by name
pytest tests/cognitive/unit/test_llm_validation_extractor.py::TestJSONParsing::test_parse_valid_json_response -v
```

### Run with Debug Output
```bash
# Show print statements and debug output
pytest tests/cognitive/unit/test_llm_validation_extractor.py -v -s

# Show full diff on assertion failures
pytest tests/cognitive/unit/test_llm_validation_extractor.py -v --tb=long
```

### Run with PDB Debugger
```bash
# Drop into debugger on failure
pytest tests/cognitive/unit/test_llm_validation_extractor.py --pdb

# Drop into debugger on first failure
pytest tests/cognitive/unit/test_llm_validation_extractor.py -x --pdb
```

## Performance Testing

### Run Performance Benchmarks
```bash
pytest tests/cognitive/performance/test_phase2_performance.py -v
```

### Measure Extraction Time
```bash
# Run with timing information
pytest tests/cognitive/performance/ -v --durations=10
```

## Quality Checks

### Run All Quality Checks
```bash
# Type checking with mypy
mypy src/services/business_logic_extractor.py

# Linting with ruff
ruff check src/services/business_logic_extractor.py

# Format checking with black
black --check src/services/business_logic_extractor.py
```

### Run Quality Test Suite
```bash
pytest tests/cognitive/quality/test_phase2_quality.py -v
```

## Continuous Integration

### Pre-Commit Checks
```bash
# Run before every commit
pytest tests/cognitive/unit/ -v --cov=src/services/business_logic_extractor --cov-fail-under=90
mypy src/services/business_logic_extractor.py
ruff check src/services/business_logic_extractor.py
```

### Pre-Push Checks
```bash
# Run before pushing to remote
pytest tests/cognitive/ -m "not real_api" -v --cov=src/services/business_logic_extractor --cov-fail-under=85
```

### CI Pipeline
```bash
# Run all tests except real API (for CI/CD)
pytest tests/cognitive/ -m "not real_api" -v \
  --cov=src/services/business_logic_extractor \
  --cov=src/cognitive/ir/ \
  --cov-report=xml \
  --cov-fail-under=85 \
  --junitxml=test-results/junit.xml
```

## Test Fixtures

### Using Fixtures in Tests
```python
def test_example(sample_spec, mock_llm_response_valid):
    """Tests can use predefined fixtures."""
    extractor = BusinessLogicExtractor()
    # Use sample_spec and mock_llm_response_valid
```

### Available Fixtures

#### From `conftest.py`
- `real_anthropic_client` - Real Anthropic client (requires API key)
- `db_session` - SQLite in-memory database session
- `real_postgres_manager` - PostgreSQL connection
- `real_redis_manager` - Redis connection
- `real_rag_system` - ChromaDB RAG system

#### From `test_llm_validation_extractor.py`
- `sample_spec` - E-commerce API specification
- `mock_llm_response_valid` - Valid LLM JSON response
- `mock_llm_response_with_markdown` - LLM response with markdown wrapper
- `mock_llm_response_malformed` - Malformed JSON response

## Common Test Patterns

### Mocking Anthropic API
```python
@patch('src.services.business_logic_extractor.anthropic.Anthropic')
def test_llm_extraction(mock_anthropic, sample_spec):
    # Mock client and response
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"rules": []}')]
    mock_client.messages.create.return_value = mock_message
    mock_anthropic.return_value = mock_client

    # Test with mock
    extractor = BusinessLogicExtractor()
    extractor.client = mock_client
    rules = extractor._extract_with_llm(sample_spec)
```

### Testing Coverage Metrics
```python
def test_coverage_measurement():
    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(spec)

    # Measure coverage
    total_expected = 62
    total_extracted = len(validation_ir.rules)
    coverage = total_extracted / total_expected

    assert coverage >= 0.97  # 97% coverage target
```

### Testing Deduplication
```python
def test_deduplication():
    extractor = BusinessLogicExtractor()

    rules = [
        ValidationRule(entity="Customer", attribute="email", type=ValidationType.UNIQUENESS),
        ValidationRule(entity="Customer", attribute="email", type=ValidationType.UNIQUENESS),  # Duplicate
    ]

    deduplicated = extractor._deduplicate_rules(rules)
    assert len(deduplicated) == 1  # Only one unique rule
```

## Troubleshooting

### Tests Fail with API Key Error
**Problem**: Tests requiring real API fail with authentication error
**Solution**:
```bash
# Set API key environment variable
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Or skip real API tests
pytest -m "not real_api"
```

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'src'`
**Solution**:
```bash
# Ensure you're in project root
cd /home/kwar/code/agentic-ai

# Install project in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH=/home/kwar/code/agentic-ai:$PYTHONPATH
```

### Coverage Not Showing New Code
**Problem**: Coverage report doesn't show newly added code
**Solution**:
```bash
# Clear coverage cache
rm -rf .coverage htmlcov/

# Re-run with coverage
pytest tests/cognitive/ --cov=src/services/business_logic_extractor --cov-report=html
```

### Tests Hang or Timeout
**Problem**: Tests hang indefinitely or timeout
**Solution**:
```bash
# Run with timeout
pytest tests/cognitive/ --timeout=60 -v

# Or skip slow tests
pytest tests/cognitive/ -m "not slow" -v
```

## Best Practices

### Writing New Tests
1. **Use descriptive test names**: `test_handles_empty_spec_without_crashing`
2. **One assertion per test**: Focus on testing one behavior
3. **Use fixtures**: Reuse test data via fixtures
4. **Mock external dependencies**: Don't make real API calls in unit tests
5. **Add docstrings**: Explain what the test validates

### Test Organization
```python
class TestFeatureArea:
    """Group related tests in classes."""

    def test_scenario_1(self):
        """Test specific scenario."""
        pass

    def test_scenario_2(self):
        """Test another scenario."""
        pass
```

### Test Data Management
- **Use fixtures**: Define reusable test data in `conftest.py` or test file fixtures
- **Keep specs small**: Use minimal specifications for unit tests
- **Real data for E2E**: Use realistic specifications for E2E tests

### Performance Considerations
- **Mark slow tests**: Use `@pytest.mark.slow` for tests >5 seconds
- **Skip expensive tests**: Skip real API tests by default
- **Use caching**: Cache expensive setup operations

## Test Metrics Dashboard

### Current Test Status
```bash
# Get test count and status
pytest tests/cognitive/ --collect-only -q

# Get coverage summary
pytest tests/cognitive/ --cov=src/services/business_logic_extractor --cov-report=term-missing
```

### Expected Metrics (Phase 2 Targets)
- **Unit Tests**: 15-20 tests, >90% coverage
- **Integration Tests**: 10-15 tests, >85% coverage
- **E2E Tests**: 5-10 tests, >80% coverage
- **Total Tests**: 30-45 tests
- **Total Coverage**: >85% across all code

## Next Steps

1. **Run initial test suite**: `pytest tests/cognitive/unit/ -v`
2. **Check coverage**: `pytest tests/cognitive/unit/ --cov=src/services/business_logic_extractor --cov-report=html`
3. **Fix failing tests**: Address any failures or warnings
4. **Add missing tests**: Identify untested code paths and add tests
5. **Measure baseline**: Run coverage measurement tests to establish Phase 1 baseline
6. **Implement Phase 2**: Add LLM extraction improvements
7. **Validate improvement**: Re-run coverage measurement to verify 97-100% target

---

**Last Updated**: 2025-11-23
**Version**: 1.0
**Maintainer**: Quality Engineer (Claude Code)
