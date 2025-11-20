# Test Suite Documentation

## Overview

Comprehensive test suite for production-ready FastAPI applications with 80%+ coverage targets.

## Structure

```
tests/
├── pytest.ini              # Pytest configuration
├── .coveragerc            # Coverage configuration
├── conftest.py.j2         # Test fixtures and setup
├── factories.py.j2        # Test data factories
├── unit/
│   ├── test_models.py.j2       # Pydantic schema tests (90%+ coverage)
│   ├── test_repositories.py.j2  # Database CRUD tests (85%+ coverage)
│   └── test_services.py.j2     # Business logic tests (80%+ coverage)
└── integration/
    └── test_api.py.j2          # API endpoint tests (75%+ coverage)
```

## Test Categories

### Unit Tests

#### test_models.py.j2 (Coverage target: 90%+)
- Pydantic schema validation
- Required field tests
- Field constraint tests (min_length, max_length, gt, ge)
- Strict mode tests (type coercion rejection)
- ORM model conversion tests

**Key test patterns:**
- `test_create_with_valid_data` - Valid schema creation
- `test_create_missing_required_*` - Required field validation
- `test_create_*_min_length` - String min length constraints
- `test_create_*_max_length` - String max length constraints
- `test_create_strict_mode_type_coercion_rejected` - Strict type validation
- `test_update_all_fields_optional` - Update schema flexibility
- `test_response_with_orm_model` - Entity to schema conversion

#### test_repositories.py.j2 (Coverage target: 85%+)
- CRUD operation tests
- Database session management
- Not found scenarios
- Pagination tests

**Key test patterns:**
- `test_create_*` - Entity creation
- `test_get_existing_*` - Successful retrieval
- `test_get_nonexistent_*` - 404 scenarios
- `test_list_*_pagination` - Pagination logic
- `test_update_existing_*` - Full updates
- `test_update_partial_fields` - Partial updates
- `test_delete_existing_*` - Successful deletion

#### test_services.py.j2 (Coverage target: 80%+)
- Business logic validation
- HTML sanitization (XSS prevention)
- Entity-schema conversion
- Mocked repository tests

**Key test patterns:**
- `test_create_*_sanitizes_html` - XSS prevention
- `test_get_existing_*` - Service layer retrieval
- `test_list_*_with_pagination` - Pagination calculations
- `test_update_*_sanitizes_html` - Update sanitization
- `test_entity_to_schema_conversion` - Model conversion

### Integration Tests

#### test_api.py.j2 (Coverage target: 75%+)
- Full HTTP request/response cycle
- All CRUD endpoints
- Success scenarios (201, 200, 204)
- Error scenarios (404, 422)
- End-to-end workflows

**Key test patterns:**
- `test_create_*_success` - POST 201 Created
- `test_create_*_validation_error` - POST 422 Validation
- `test_get_existing_*` - GET 200 OK
- `test_get_nonexistent_*` - GET 404 Not Found
- `test_list_*_pagination` - GET with query params
- `test_update_existing_*` - PUT 200 OK
- `test_update_nonexistent_*` - PUT 404 Not Found
- `test_delete_existing_*` - DELETE 204 No Content
- `test_end_to_end_workflow` - Complete CRUD cycle

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run specific test categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_models.py

# Specific test class
pytest tests/unit/test_models.py::TestTaskCreate

# Specific test method
pytest tests/unit/test_models.py::TestTaskCreate::test_create_with_valid_data
```

### Run with markers
```bash
# Unit tests
pytest -m unit

# Integration tests
pytest -m integration

# Slow tests
pytest -m slow
```

### Run with verbose output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run failed tests only
```bash
pytest --lf  # Last failed
pytest --ff  # Failed first
```

## Test Fixtures

### db_session (conftest.py.j2)
- Creates fresh in-memory SQLite database for each test
- Automatic rollback after test completion
- Ensures test isolation

**Usage:**
```python
@pytest.mark.asyncio
async def test_example(db_session: AsyncSession):
    repo = TaskRepository(db_session)
    # Use repo...
```

### client (conftest.py.j2)
- AsyncClient with database dependency override
- Full HTTP request/response testing
- Automatic cleanup

**Usage:**
```python
@pytest.mark.asyncio
async def test_api_example(client: AsyncClient):
    response = await client.post("/api/tasks", json={...})
    assert response.status_code == 201
```

## Test Data Factories

### Factory Pattern
Factories provide realistic test data with easy customization:

```python
# Create with defaults
task_data = TaskFactory.create()

# Override specific fields
task_data = TaskFactory.create(title="Custom Title", completed=True)

# Create batch
tasks = TaskFactory.create_batch(5)

# Create batch with overrides
tasks = TaskFactory.create_batch(3, completed=False)
```

## Coverage Reports

### Terminal Report
```bash
pytest --cov=src --cov-report=term-missing
```

Shows coverage with missing line numbers.

### HTML Report
```bash
pytest --cov=src --cov-report=html
```

Generates `htmlcov/index.html` with interactive coverage visualization.

### Coverage Thresholds
- Overall: 80%+
- Models/Schemas: 90%+
- Repositories: 85%+
- Services: 80%+
- API Routes: 75%+

## Best Practices

### Test Naming
- Descriptive test names: `test_create_task_with_valid_data`
- Include expected outcome: `test_create_task_missing_title_returns_422`
- Use consistent patterns across similar tests

### Test Organization
- One test class per entity/component
- Group related tests within classes
- Order tests logically (happy path → edge cases → error cases)

### Test Independence
- Each test should be fully independent
- Use fixtures for setup, not manual state creation
- Avoid test order dependencies

### Async Tests
Always mark async tests with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_async_operation(db_session: AsyncSession):
    result = await async_function()
    assert result is not None
```

### Assertions
- Use specific assertions
- One logical assertion per test (multiple assert statements OK if testing same concept)
- Use descriptive assertion messages for complex checks

## Continuous Integration

Tests are designed for CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pytest --cov=src --cov-fail-under=80
```

Coverage failure threshold is configured in `pytest.ini`:
```ini
addopts = --cov-fail-under=80
```

## Troubleshooting

### Import Errors
Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Database Errors
Tests use in-memory SQLite. If seeing persistent data:
- Check fixture scope (should be `function`)
- Verify rollback in conftest.py
- Check for missing `await` on async operations

### Async Warnings
Configure pytest to auto-detect async mode in `pytest.ini`:
```ini
asyncio_mode = auto
```

### Coverage Gaps
Use HTML report to identify untested code:
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Test Statistics

- **Total Test Files**: 4 templates
- **Total Test Methods**: 54+ tests per entity
- **Total Lines of Code**: 1,600+ lines
- **Coverage Target**: 80%+ overall
- **Test Categories**: Unit (3 files) + Integration (1 file)

## Dependencies

Required packages (in requirements.txt):
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0
```
