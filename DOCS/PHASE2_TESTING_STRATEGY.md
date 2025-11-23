# Phase 2 Testing & Validation Strategy

## Executive Summary

**Objective**: Comprehensive testing plan for Phase 2 validation extraction improvements targeting 97-100% coverage (60-62/62 validations).

**Current State**: Phase 1 achieved 45/62 validations (73%) via pattern-based extraction
**Target State**: Phase 2 targets 60-62/62 validations (97-100%) via aggressive LLM extraction
**Gap**: +15-17 additional validations needed through improved LLM extraction

## Testing Infrastructure Analysis

### Existing Test Structure
```
tests/
├── conftest.py                    # Pytest configuration with real service fixtures
├── cognitive/
│   ├── patterns/                  # Pattern learning tests
│   │   ├── test_pattern_classifier.py
│   │   └── test_pattern_feedback_integration.py
│   ├── unit/                      # Cognitive unit tests
│   └── integration/               # Cognitive integration tests
├── test_mge_v2_e2e.py            # E2E testing framework
└── [other test directories...]
```

### Testing Capabilities Available
- **Real Service Testing**: Anthropic API, PostgreSQL, Redis, ChromaDB via conftest.py fixtures
- **Mocking Framework**: pytest with comprehensive fixture system
- **E2E Framework**: WebSocket, API, DB validation pipeline
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.real_api`

## Phase 2 Component Architecture

### Target Component: Enhanced LLM Extraction
**Location**: `src/services/business_logic_extractor.py`
**Method**: `_extract_with_llm()` (lines 219-267)
**Current Issues**:
- Only 1000 max_tokens (insufficient for comprehensive extraction)
- Basic prompt without examples or structured guidance
- No retry mechanism for JSON parsing failures
- No confidence scoring
- No extraction verification/validation

### Enhancement Plan
**New Component**: `LLMValidationExtractor` (separate class)
**Features**:
- Structured extraction with rich examples
- Retry logic with exponential backoff
- Confidence scoring per validation
- Multi-pass extraction strategy
- Validation rule verification
- Deduplication with confidence weighting

## Test Plan Structure

### 1. Unit Tests for LLMValidationExtractor

**Test File**: `tests/cognitive/unit/test_llm_validation_extractor.py`
**Coverage Target**: >90%
**Estimated Tests**: 15-20 tests

#### Test Cases

##### 1.1 Initialization Tests (3 tests)
```python
def test_initialization_with_defaults():
    """Test extractor initializes with default parameters."""

def test_initialization_with_custom_config():
    """Test extractor accepts custom model, max_tokens, temperature."""

def test_initialization_validates_api_key():
    """Test extractor fails gracefully without valid API key."""
```

##### 1.2 JSON Parsing Tests (4 tests)
```python
def test_parse_valid_json_response():
    """Test parsing well-formed JSON array response."""

def test_parse_json_with_markdown_wrapper():
    """Test parsing JSON wrapped in ```json code blocks."""

def test_parse_malformed_json_returns_empty():
    """Test resilient handling of unparseable JSON."""

def test_parse_json_with_extra_text():
    """Test extracting JSON from response with extra commentary."""
```

##### 1.3 Retry Logic Tests (3 tests)
```python
def test_retry_on_json_parse_failure():
    """Test retry mechanism activates on JSON parse errors."""

def test_retry_with_exponential_backoff():
    """Test backoff timing increases exponentially."""

def test_max_retries_respected():
    """Test extraction stops after max retry attempts."""
```

##### 1.4 Confidence Scoring Tests (3 tests)
```python
def test_confidence_scoring_basic():
    """Test confidence score calculation for simple validations."""

def test_confidence_scoring_with_specificity():
    """Test higher confidence for specific condition details."""

def test_confidence_threshold_filtering():
    """Test low-confidence rules filtered out."""
```

##### 1.5 Validation Rule Creation Tests (3 tests)
```python
def test_create_validation_rule_complete():
    """Test creating ValidationRule from complete JSON data."""

def test_create_validation_rule_partial():
    """Test creating ValidationRule with optional fields missing."""

def test_create_validation_rule_invalid_type():
    """Test handling of invalid ValidationType enum values."""
```

### 2. Integration Tests for Phase 2

**Test File**: `tests/cognitive/integration/test_phase2_extraction_integration.py`
**Coverage Target**: End-to-end extraction pipeline
**Estimated Tests**: 10-15 tests

#### Test Cases

##### 2.1 BusinessLogicExtractor Integration (3 tests)
```python
def test_integration_with_pattern_extraction():
    """Test LLM extraction integrates with Stage 6.5 pattern rules."""

def test_deduplication_between_pattern_and_llm():
    """Test rules from both sources deduplicated correctly."""

def test_llm_extraction_fallback_on_pattern_failure():
    """Test LLM extraction proceeds if pattern extraction fails."""
```

##### 2.2 Stage Interaction Tests (4 tests)
```python
def test_stage_6_pattern_extraction():
    """Test Stage 6.5 pattern-based extraction works."""

def test_stage_7_llm_extraction():
    """Test Stage 7 LLM extraction works independently."""

def test_stage_8_deduplication():
    """Test Stage 8 deduplication merges pattern + LLM rules."""

def test_full_pipeline_stages_1_through_8():
    """Test complete extraction pipeline from entities to LLM."""
```

##### 2.3 Confidence Aggregation Tests (3 tests)
```python
def test_confidence_aggregation_pattern_vs_llm():
    """Test confidence when same rule extracted by both methods."""

def test_confidence_ordering_in_output():
    """Test high-confidence rules appear first in results."""

def test_low_confidence_rule_exclusion():
    """Test rules below threshold excluded from final output."""
```

##### 2.4 Real LLM Integration Tests (2 tests)
```python
@pytest.mark.real_api
def test_real_llm_extraction_ecommerce_spec(real_anthropic_client):
    """Test real LLM extraction on e-commerce spec (requires API key)."""

@pytest.mark.real_api
def test_real_llm_extraction_handles_api_errors(real_anthropic_client):
    """Test graceful handling of real API rate limits/errors."""
```

### 3. Coverage Measurement Framework

**Test File**: `tests/cognitive/validation/test_validation_coverage.py`
**Purpose**: Measure extraction coverage before/after Phase 2
**Estimated Tests**: 3-5 measurement tests

#### Test Cases

##### 3.1 Phase 1 Baseline Measurement (1 test)
```python
def test_phase1_baseline_coverage():
    """
    Measure Phase 1 coverage (pattern-based only).
    Expected: 45/62 validations (73%).
    """
    extractor = BusinessLogicExtractor()
    # Disable LLM extraction
    extractor._extract_with_llm = lambda spec: []

    validation_ir = extractor.extract_validation_rules(ecommerce_spec)

    assert len(validation_ir.rules) == 45
    assert calculate_coverage(validation_ir) == 0.73
```

##### 3.2 Phase 2 Coverage Measurement (1 test)
```python
def test_phase2_full_coverage():
    """
    Measure Phase 2 coverage (pattern + LLM).
    Expected: 60-62/62 validations (97-100%).
    """
    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(ecommerce_spec)

    assert len(validation_ir.rules) >= 60
    assert calculate_coverage(validation_ir) >= 0.97
```

##### 3.3 Coverage Breakdown by Type (1 test)
```python
def test_coverage_breakdown_by_validation_type():
    """
    Measure coverage breakdown:
    - UNIQUENESS (email, username, etc.)
    - RELATIONSHIP (foreign keys)
    - STOCK_CONSTRAINT (inventory)
    - STATUS_TRANSITION (workflows)
    - etc.
    """
    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(ecommerce_spec)

    breakdown = group_by_validation_type(validation_ir.rules)

    assert breakdown['UNIQUENESS'] >= 5
    assert breakdown['RELATIONSHIP'] >= 8
    assert breakdown['STOCK_CONSTRAINT'] >= 3
```

##### 3.4 Coverage Breakdown by Entity (1 test)
```python
def test_coverage_breakdown_by_entity():
    """
    Measure coverage by entity:
    - Customer validations
    - Product validations
    - Order validations
    - etc.
    """
    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(ecommerce_spec)

    breakdown = group_by_entity(validation_ir.rules)

    assert 'Customer' in breakdown
    assert 'Product' in breakdown
    assert 'Order' in breakdown
```

##### 3.5 Coverage Source Attribution (1 test)
```python
def test_coverage_source_attribution():
    """
    Measure extraction source breakdown:
    - Direct (entity field constraints)
    - Pattern (YAML patterns)
    - LLM (intelligent extraction)
    """
    extractor = BusinessLogicExtractor()
    # Add source tracking to extraction
    validation_ir = extractor.extract_validation_rules(ecommerce_spec)

    sources = attribute_extraction_sources(validation_ir.rules)

    assert sources['direct'] >= 20  # Stage 1-5
    assert sources['pattern'] >= 15  # Stage 6.5
    assert sources['llm'] >= 15      # Stage 7
```

### 4. E2E and Regression Testing

**Test File**: `tests/cognitive/e2e/test_phase2_e2e.py`
**Purpose**: End-to-end validation pipeline testing
**Estimated Tests**: 5-10 tests

#### Test Cases

##### 4.1 Full Pipeline E2E Tests (2 tests)
```python
def test_e2e_ecommerce_spec_extraction():
    """
    Full extraction pipeline on e-commerce spec:
    1. Load spec
    2. Extract validations (all stages)
    3. Validate output structure
    4. Verify coverage target met
    """

def test_e2e_extraction_with_real_llm():
    """
    Full extraction with real LLM API:
    1. Load spec
    2. Call real Anthropic API
    3. Parse and validate results
    4. Check coverage improvement
    """
```

##### 4.2 Regression Tests (5 tests)
```python
def test_regression_phase1_validations_preserved():
    """
    Ensure all 45 Phase 1 validations still extracted.
    No regressions from pattern-based extraction.
    """

def test_regression_deduplication_no_losses():
    """
    Ensure deduplication doesn't incorrectly remove valid rules.
    """

def test_regression_confidence_ordering():
    """
    Ensure high-confidence rules appear before low-confidence.
    """

def test_regression_error_messages_user_friendly():
    """
    Ensure error messages remain clear and actionable.
    """

def test_regression_validation_types_correct():
    """
    Ensure ValidationType enums correctly assigned.
    """
```

##### 4.3 Performance Regression Tests (2 tests)
```python
def test_performance_extraction_time():
    """
    Measure extraction time per spec.
    Target: <5 seconds total extraction time.
    """

def test_performance_api_token_usage():
    """
    Measure API token consumption.
    Target: <3000 tokens per extraction.
    """
```

### 5. Quality Metrics Tests

**Test File**: `tests/cognitive/quality/test_phase2_quality.py`
**Purpose**: Code quality and documentation validation
**Estimated Tests**: 5-8 tests

#### Test Cases

##### 5.1 Code Coverage Tests (2 tests)
```python
def test_code_coverage_llm_extractor():
    """
    Verify code coverage >90% for LLMValidationExtractor.
    """

def test_type_coverage_100_percent():
    """
    Verify 100% type hint coverage for new code.
    """
```

##### 5.2 Documentation Tests (2 tests)
```python
def test_docstring_coverage_100_percent():
    """
    Verify 100% docstring coverage for public methods.
    """

def test_readme_examples_work():
    """
    Verify README examples execute without errors.
    """
```

##### 5.3 False Positive Tests (2 tests)
```python
def test_false_positive_rate():
    """
    Measure false positives (<5% of extracted rules).
    False positive = rule doesn't match spec requirement.
    """

def test_confidence_score_accuracy():
    """
    Validate confidence scores correlate with rule correctness.
    High confidence (>0.9) = >95% correct.
    """
```

### 6. Performance Testing

**Test File**: `tests/cognitive/performance/test_phase2_performance.py`
**Purpose**: Performance benchmarking
**Estimated Tests**: 3-5 tests

#### Test Cases

```python
def test_extraction_time_per_call():
    """Measure LLM extraction latency per call."""

def test_api_token_usage():
    """Measure token consumption per extraction."""

def test_memory_usage():
    """Measure memory footprint during extraction."""

def test_concurrent_extraction_performance():
    """Test performance with multiple concurrent extractions."""
```

## Test Execution Plan

### Phase 1: Unit Tests (Day 1-2)
```bash
# Run unit tests (can run immediately, no dependencies)
pytest tests/cognitive/unit/test_llm_validation_extractor.py -v

# Expected: 15-20 tests, >90% code coverage
```

### Phase 2: Integration Tests (Day 2-3)
```bash
# Run integration tests (after LLM extractor implementation)
pytest tests/cognitive/integration/test_phase2_extraction_integration.py -v

# Expected: 10-15 tests, validates stage interaction
```

### Phase 3: Coverage Measurement (Day 3)
```bash
# Measure baseline and Phase 2 coverage
pytest tests/cognitive/validation/test_validation_coverage.py -v

# Expected: Phase 1 = 45/62 (73%), Phase 2 = 60-62/62 (97-100%)
```

### Phase 4: E2E Tests (Day 4)
```bash
# Run E2E tests with real data
pytest tests/cognitive/e2e/test_phase2_e2e.py -v

# Expected: Full pipeline validation, production-like scenario
```

### Phase 5: Regression Tests (Day 4-5)
```bash
# Run regression suite to catch any regressions
pytest tests/cognitive/e2e/test_phase2_e2e.py::test_regression* -v

# Expected: All Phase 1 validations preserved, no quality degradation
```

### Phase 6: Performance & Quality (Day 5)
```bash
# Run performance benchmarks
pytest tests/cognitive/performance/test_phase2_performance.py -v

# Run quality checks
pytest tests/cognitive/quality/test_phase2_quality.py -v

# Expected: <5s extraction, >90% coverage, 100% type hints
```

## Test Data Strategy

### Primary Test Spec
**Source**: E-commerce API specification (simple version)
**Location**: `tests/fixtures/ecommerce_api_spec.yaml`
**Entities**: Customer, Product, Order, OrderItem
**Expected Validations**: 62 total validations

### Validation Breakdown (Target)
```yaml
UNIQUENESS: 8 validations
  - Customer.email (unique)
  - Customer.username (unique)
  - Product.sku (unique)
  - Product.slug (unique)
  - Order.order_number (unique)
  - etc.

RELATIONSHIP: 12 validations
  - Order.customer_id (FK to Customer)
  - OrderItem.order_id (FK to Order)
  - OrderItem.product_id (FK to Product)
  - etc.

STOCK_CONSTRAINT: 5 validations
  - Product.stock_quantity (>= 0)
  - OrderItem.quantity <= Product.stock_quantity
  - etc.

STATUS_TRANSITION: 8 validations
  - Order.status transitions (pending → processing → shipped → delivered)
  - Customer.is_active (boolean)
  - etc.

PRESENCE: 15 validations
  - Customer.email (required)
  - Customer.password (required)
  - Order.customer_id (required)
  - etc.

FORMAT: 10 validations
  - Customer.email (email format)
  - Product.price (decimal format)
  - Customer.phone (phone format)
  - etc.

RANGE: 4 validations
  - Product.price (>= 0)
  - OrderItem.quantity (>= 1)
  - etc.
```

## Quality Gates

### Pre-Commit Gates
- [ ] All unit tests pass (15-20 tests)
- [ ] Code coverage >90% for new code
- [ ] Type hints 100% coverage
- [ ] Docstrings 100% coverage
- [ ] No linting errors (ruff, mypy)

### Pre-Merge Gates
- [ ] All integration tests pass (10-15 tests)
- [ ] All E2E tests pass (5-10 tests)
- [ ] All regression tests pass (5-10 tests)
- [ ] Coverage target met: 60-62/62 validations (97-100%)
- [ ] Performance target met: <5s extraction time
- [ ] False positive rate <5%

### Production Readiness Gates
- [ ] Performance tests pass (<5s extraction, <3000 tokens)
- [ ] Quality tests pass (>90% coverage, 100% types/docs)
- [ ] Real API tests pass (with actual Anthropic API)
- [ ] Documentation tests pass (examples work)
- [ ] Security review complete
- [ ] Code review approved by 2+ reviewers

## Success Metrics

### Coverage Metrics
- **Phase 1 Baseline**: 45/62 validations (73%) ✅ (measured)
- **Phase 2 Target**: 60-62/62 validations (97-100%) 🎯 (target)
- **Improvement Delta**: +15-17 validations (+24-27% improvement)

### Quality Metrics
- **Code Coverage**: >90% for LLMValidationExtractor
- **Type Coverage**: 100% type hints
- **Docstring Coverage**: 100%
- **Test Pass Rate**: 100%
- **False Positive Rate**: <5%

### Performance Metrics
- **Extraction Time**: <5 seconds per spec
- **API Token Usage**: <3000 tokens per extraction
- **Memory Usage**: <500MB peak
- **Concurrent Performance**: 3+ extractions in parallel

## Risk Mitigation

### High-Risk Areas
1. **LLM API Reliability**: Anthropic API may have rate limits, outages
   - **Mitigation**: Retry logic with exponential backoff, fallback to pattern-based extraction

2. **JSON Parsing Failures**: LLM may return malformed JSON
   - **Mitigation**: Robust JSON parsing with markdown wrapper removal, retry on parse errors

3. **Confidence Scoring Accuracy**: Low-confidence rules may be incorrectly filtered
   - **Mitigation**: Confidence threshold tuning, manual validation of filtered rules

4. **Deduplication Issues**: May incorrectly merge or remove valid rules
   - **Mitigation**: Comprehensive deduplication tests, confidence-based merge logic

### Low-Risk Areas
1. **Pattern Extraction**: Already tested and working in Phase 1
2. **Entity/Field Parsing**: Stable code, low regression risk
3. **Validation Rule Creation**: Simple data structure, well-tested

## Deliverables Checklist

### Test Implementation
- [ ] `tests/cognitive/unit/test_llm_validation_extractor.py` (300-400 lines)
- [ ] `tests/cognitive/integration/test_phase2_extraction_integration.py` (200-300 lines)
- [ ] `tests/cognitive/validation/test_validation_coverage.py` (150-200 lines)
- [ ] `tests/cognitive/e2e/test_phase2_e2e.py` (200-250 lines)
- [ ] `tests/cognitive/quality/test_phase2_quality.py` (100-150 lines)
- [ ] `tests/cognitive/performance/test_phase2_performance.py` (100-150 lines)

### Test Fixtures
- [ ] `tests/fixtures/ecommerce_api_spec.yaml` (reference spec)
- [ ] `tests/fixtures/mock_llm_responses.json` (mock LLM JSON responses)
- [ ] `tests/fixtures/expected_validations.yaml` (ground truth validations)

### Documentation
- [ ] `DOCS/PHASE2_TESTING_STRATEGY.md` (this document)
- [ ] `DOCS/TESTING_GUIDE.md` (how to run tests)
- [ ] `DOCS/COVERAGE_REPORT.md` (before/after coverage metrics)
- [ ] `README.md` updates (testing section)

### Reports
- [ ] Coverage measurement report (before/after metrics)
- [ ] Performance benchmark report
- [ ] Quality gate checklist (signed off)
- [ ] Regression test report

## Timeline Estimate

### Week 1: Foundation
- **Day 1-2**: Unit tests implementation (15-20 tests)
- **Day 2-3**: Integration tests implementation (10-15 tests)
- **Day 3**: Coverage measurement framework (3-5 tests)

### Week 2: Validation
- **Day 4**: E2E tests (5-10 tests)
- **Day 4-5**: Regression tests (5-10 tests)
- **Day 5**: Performance & quality tests (8-12 tests)

### Week 3: Polish
- **Day 6**: Real API testing and debugging
- **Day 7**: Documentation and reports
- **Day 8**: Code review and refinements
- **Day 9-10**: Buffer for unexpected issues

**Total Estimated Effort**: 2-3 weeks (depending on complexity and issues encountered)

## Next Steps

1. ✅ **Review and approve this testing strategy**
2. ⏳ **Create test fixtures** (ecommerce spec, mock responses, expected validations)
3. ⏳ **Implement unit tests** (start with LLMValidationExtractor tests)
4. ⏳ **Implement LLMValidationExtractor** (parallel to unit test development)
5. ⏳ **Run integration tests** (validate stage interaction)
6. ⏳ **Measure coverage** (compare Phase 1 vs Phase 2)
7. ⏳ **Run E2E and regression tests** (validate no regressions)
8. ⏳ **Performance and quality validation** (meet all targets)
9. ⏳ **Documentation and reporting** (finalize deliverables)
10. ⏳ **Code review and merge** (get team approval)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-23
**Author**: Quality Engineer (Claude Code)
**Status**: Draft for Review
