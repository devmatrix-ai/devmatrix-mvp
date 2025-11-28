# Deprecated Tests

Tests in this directory are deprecated and excluded from pytest runs.

## Reason for Deprecation

These tests were written for legacy APIs that have been replaced in MGE v2:

### Unit Tests (`unit/`)

- **test_api_security.py** - Hardcoded Mac path (`/Users/arieleduardoghysels/...`)
- **test_recursive_decomposer.py** - Uses old `RecursiveDecomposer.__init__()` signature (21 TypeErrors)
- **test_wave_executor.py** - Uses old `AtomicUnit` with `dependencies` parameter (15 TypeErrors)
- **test_context_injector.py** - Uses old `ContextInjector.__init__()` signature (14 TypeErrors)
- **test_retry_orchestrator.py** - Uses old `AtomicUnit` with `dependencies` parameter (9 TypeErrors)

### Unit/API Tests (`unit/api/`)

- **test_api_smoke.py** - Expects JSON response where root returns plain text

### Integration Tests (`integration/`)

- **test_phase1_integration.py** - Collection error due to import issues
- **test_pattern_based_generation.py** - Collection error due to import issues

## Migration Path

If you need functionality from these tests:

1. Check if equivalent tests exist in `tests/mge/v2/` (newer architecture)
2. Update test code to use current API signatures
3. Move updated tests back to main test directories

## Do Not Delete

These tests are preserved for:
- Historical reference
- Future migration if needed
- Understanding legacy architecture

Last updated: 2025-11-28
