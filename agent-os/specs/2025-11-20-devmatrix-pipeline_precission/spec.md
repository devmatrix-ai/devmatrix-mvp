# Specification: DevMatrix Pipeline Precision Improvement

**Version**: 1.0
**Date**: 2025-11-20
**Status**: 📋 Planning
**Priority**: 🔴 High
**Owner**: DevMatrix Team

---

## 1. Overview

### 1.1 Purpose

Improve DevMatrix E2E pipeline overall precision from **73.0%** to **90%+** by addressing deficiencies in three intermediate pipeline phases while maintaining **100% semantic compliance** of generated code.

### 1.2 Scope

**In Scope:**
- Fix Pattern Matching recall (47.1% → 70%+)
- Implement Classification metrics tracking (0% → 80%+)
- Improve DAG Construction accuracy (57.6% → 80%+)
- Enhance metrics presentation UX

**Out of Scope:**
- Changes to code generation logic (already at 100% semantic compliance)
- Modification of execution or validation phases (already at 100% success)
- New pipeline phases or architectural changes

### 1.3 Success Criteria

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| **Overall Precision** | 73.0% | 85%+ | 90%+ |
| Pattern F1-Score | 59.3% | 75%+ | 80%+ |
| Pattern Recall | 47.1% | 70%+ | 80%+ |
| Classification Accuracy | 0.0% | 80%+ | 90%+ |
| DAG Accuracy | 57.6% | 80%+ | 85%+ |
| Semantic Compliance | 100% | 100% | 100% |

---

## 2. Current State Analysis

### 2.1 Pipeline Architecture

```
DevMatrix E2E Pipeline (10 Phases)
├─ Phase 1: Spec Ingestion         [✅ 100%] - GOOD
├─ Phase 2: Requirements Analysis   [⚠️ 59.3%] - NEEDS IMPROVEMENT
│  ├─ Pattern Matching              [⚠️ 47.1% recall]
│  └─ Classification                [❌ 0% accuracy]
├─ Phase 3: Multi-Pass Planning     [⚠️ 57.6%] - NEEDS IMPROVEMENT
├─ Phase 4: Atomization             [✅ 90%] - GOOD
├─ Phase 5: DAG Construction        [⚠️ 57.6%] - NEEDS IMPROVEMENT
├─ Phase 6: Wave Execution          [✅ 100%] - GOOD
├─ Phase 7: Validation              [✅ 100%] - GOOD
├─ Phase 8: Deployment              [✅ 100%] - GOOD
├─ Phase 9: Health Verification     [✅ 100%] - GOOD
└─ Phase 10: Learning               [✅ 100%] - GOOD

Overall Precision: 73.0% (weighted average)
```

### 2.2 Precision Calculation Formula

```python
# Source: tests/e2e/precision_metrics.py:143
overall_precision = sum(scores[k] * weights[k] for k in weights)

Weights:
  accuracy: 20%        → 100% ✅
  pattern_f1: 15%      → 59.3% ❌
  classification: 15%  → 0% ❌
  dag: 10%             → 57.6% ❌
  atomization: 10%     → 90% ✅
  execution: 20%       → 100% ✅
  tests: 10%           → 94% ✅

Calculation:
  (1.00 * 0.20) + (0.593 * 0.15) + (0.00 * 0.15) +
  (0.576 * 0.10) + (0.90 * 0.10) + (1.00 * 0.20) + (0.94 * 0.10)
  = 0.731 = 73.1%
```

### 2.3 Problem Areas Identified

#### Problem 1: Pattern Matching Low Recall
- **Precision**: 80.0% (patterns found are correct)
- **Recall**: 47.1% (only finds 47% of expected patterns)
- **F1-Score**: 59.3%
- **Root Cause**: Generic embeddings, incomplete pattern database, no fallback heuristics

#### Problem 2: Classification Metrics Not Captured
- **Accuracy**: 0.0% (metrics not tracked)
- **Root Cause**: Disconnect between RequirementsClassifier and PrecisionMetrics tracker

#### Problem 3: DAG Construction Inaccuracy
- **Accuracy**: 57.6% (missing edges)
- **Root Cause**: Weak dependency inference, undefined ground truth

---

## 3. Technical Requirements

### 3.1 Milestone 1: Fix Classification Metrics (Quick Win)

**Priority**: 🔴 High
**Effort**: 🟢 Low (2-4 hours)
**Impact**: +12% overall precision

#### 3.1.1 Capture Classification Metrics

**File**: `tests/e2e/real_e2e_full_pipeline.py` (line ~250)

**Current Code**:
```python
# Phase 2: Requirements Analysis
classified_reqs = req_classifier.classify(functional_reqs)
# ❌ No metrics tracking
```

**Required Change**:
```python
# Phase 2: Requirements Analysis
classified_reqs = req_classifier.classify(functional_reqs)

# NEW: Track classification metrics
ground_truth = self._load_classification_ground_truth(spec_path)
precision_tracker.classifications_total = len(classified_reqs)
precision_tracker.classifications_correct = sum(
    1 for req in classified_reqs
    if self._validate_classification(req, ground_truth)
)
precision_tracker.classifications_incorrect = (
    precision_tracker.classifications_total -
    precision_tracker.classifications_correct
)
```

#### 3.1.2 Define Classification Ground Truth

**File**: `tests/e2e/test_specs/ecommerce_api_simple.md`

**Required Addition**:
```yaml
## Classification Ground Truth

# Format: requirement_id: {domain: <domain>, risk: <risk>}
F1_create_product:
  domain: crud
  risk: low

F2_list_products:
  domain: crud
  risk: low

F8_create_cart:
  domain: workflow
  risk: medium

F13_checkout_cart:
  domain: payment
  risk: high

# ... (all 17 requirements)
```

#### 3.1.3 Implement Classification Validator

**File**: `tests/e2e/precision_metrics.py` (new method)

**Required Addition**:
```python
def validate_classification(
    actual: Dict[str, Any],
    expected: Dict[str, Any]
) -> bool:
    """
    Validate if requirement classification matches ground truth

    Args:
        actual: {domain: str, risk: str, ...}
        expected: {domain: str, risk: str}

    Returns:
        True if domain and risk match
    """
    if not expected:
        return True  # No ground truth = assume correct

    return (
        actual.get('domain') == expected.get('domain') and
        actual.get('risk') == expected.get('risk')
    )
```

**Acceptance Criteria**:
- ✅ Classification accuracy > 0% in metrics output
- ✅ Ground truth defined for all 20+ test specs
- ✅ Overall precision increases by ~12%

---

### 3.2 Milestone 2: Improve Pattern Matching Recall

**Priority**: 🟡 Medium
**Effort**: 🟡 Medium (1-2 days)
**Impact**: +3.1% overall precision

#### 3.2.1 Clean Pattern Database

**File**: New script `scripts/audit_patterns.py`

**Required Script**:
```python
#!/usr/bin/env python3
"""
Audit and clean pattern database
- Remove patterns with empty purpose
- Filter patterns by framework
- Validate embedding quality
"""

import logging
from src.storage.pattern_bank import PatternBank

logger = logging.getLogger(__name__)

def audit_patterns(framework_filter: str = "fastapi"):
    """
    Audit pattern database

    Args:
        framework_filter: Only keep patterns for this framework
    """
    pattern_bank = PatternBank()
    patterns = pattern_bank.load_all()

    logger.info(f"Total patterns: {len(patterns)}")

    cleaned = []
    removed_empty = 0
    removed_framework = 0

    for p in patterns:
        # Remove empty purpose
        if not p.purpose or p.purpose.strip() == "":
            logger.warning(f"Removing pattern {p.id}: empty purpose")
            removed_empty += 1
            continue

        # Filter by framework
        if framework_filter and p.framework != framework_filter:
            logger.debug(f"Skipping pattern {p.id}: framework {p.framework}")
            removed_framework += 1
            continue

        cleaned.append(p)

    pattern_bank.save_all(cleaned)

    logger.info(f"Cleaned patterns:")
    logger.info(f"  - Removed (empty purpose): {removed_empty}")
    logger.info(f"  - Removed (wrong framework): {removed_framework}")
    logger.info(f"  - Remaining: {len(cleaned)}")

if __name__ == "__main__":
    audit_patterns(framework_filter="fastapi")
```

**Usage**:
```bash
cd /home/kwar/code/agentic-ai
python scripts/audit_patterns.py
```

#### 3.2.2 Implement Adaptive Thresholds

**File**: `src/services/pattern_matching/matcher.py` (line ~50)

**Current Code**:
```python
SIMILARITY_THRESHOLD = 0.85  # Single threshold for all patterns
```

**Required Change**:
```python
# Adaptive thresholds by requirement domain
SIMILARITY_THRESHOLDS = {
    'crud': 0.75,      # Simple patterns (lower threshold)
    'custom': 0.80,    # Medium complexity
    'payment': 0.85,   # Complex patterns (higher threshold)
    'workflow': 0.80   # Workflow patterns
}

DEFAULT_THRESHOLD = 0.80

def get_threshold(requirement: Requirement) -> float:
    """Get similarity threshold based on requirement domain"""
    return SIMILARITY_THRESHOLDS.get(
        requirement.domain,
        DEFAULT_THRESHOLD
    )
```

#### 3.2.3 Add Keyword-Based Fallback

**File**: `src/services/pattern_matching/matcher.py` (new method)

**Required Addition**:
```python
def match_with_fallback(self, req: Requirement) -> List[Pattern]:
    """
    Pattern matching with keyword fallback

    Strategy:
    1. Try embedding-based matching
    2. If < 3 matches, use keyword fallback
    3. Combine and deduplicate results
    """
    # 1. Embedding-based matching
    matches = self._match_by_embedding(req)

    if len(matches) >= 3:
        return matches[:5]  # Top 5

    # 2. Keyword fallback
    logger.info(f"Low matches for {req.id}, using keyword fallback")
    keyword_matches = self._match_by_keywords(req)

    # 3. Combine (deduplicate by pattern ID)
    combined = matches + [m for m in keyword_matches if m not in matches]
    return combined[:5]

def _match_by_keywords(self, req: Requirement) -> List[Pattern]:
    """
    Keyword-based pattern matching

    Rules:
    - ['create', 'add', 'new'] → crud_create
    - ['list', 'all', 'filter'] → crud_list
    - ['update', 'edit', 'modify'] → crud_update
    - ['delete', 'remove'] → crud_delete
    - ['checkout', 'pay', 'order'] → payment_workflow
    """
    keywords = self._extract_keywords(req.description)

    rules = [
        (['create', 'add', 'new'], 'crud_create'),
        (['list', 'all', 'filter'], 'crud_list'),
        (['update', 'edit', 'modify'], 'crud_update'),
        (['delete', 'remove'], 'crud_delete'),
        (['checkout', 'pay', 'order'], 'payment_workflow'),
        (['cart', 'basket'], 'cart_workflow'),
    ]

    pattern_tags = []
    for trigger_words, tag in rules:
        if any(word in keywords for word in trigger_words):
            pattern_tags.append(tag)

    # Lookup patterns by tag
    return [
        p for p in self.pattern_bank.load_all()
        if p.tag in pattern_tags
    ]

def _extract_keywords(self, text: str) -> List[str]:
    """Extract keywords from requirement text (lowercase, no stopwords)"""
    stopwords = {'a', 'an', 'the', 'to', 'from', 'for', 'of', 'in', 'on'}
    words = text.lower().split()
    return [w for w in words if w not in stopwords]
```

**Acceptance Criteria**:
- ✅ Pattern recall: 47% → 70%+
- ✅ Pattern F1-Score: 59% → 75%+
- ✅ Zero patterns with empty purpose
- ✅ Overall precision increases by ~3%

---

### 3.3 Milestone 3: Fix DAG Construction Accuracy

**Priority**: 🟡 Medium
**Effort**: 🟡 Medium (1-2 days)
**Impact**: +2.2% overall precision

#### 3.3.1 Define DAG Ground Truth

**File**: `tests/e2e/test_specs/ecommerce_api_simple.md`

**Required Addition**:
```yaml
## Expected Dependency Graph (Ground Truth)

nodes: 10
  - create_product
  - list_products
  - create_customer
  - create_cart
  - add_to_cart
  - checkout_cart
  - simulate_payment
  - cancel_order
  - list_orders
  - get_order

edges: 12  # Explicit dependencies
  - create_customer → create_cart
  - create_product → add_to_cart
  - create_cart → add_to_cart
  - add_to_cart → checkout_cart
  - checkout_cart → simulate_payment
  - checkout_cart → cancel_order
  - create_customer → list_orders
  - checkout_cart → list_orders
  - checkout_cart → get_order
  - create_product → list_products
  - create_cart → add_to_cart (duplicate, already listed)
  - add_to_cart → checkout_cart (duplicate, already listed)

# Simplified: 9 unique edges
```

#### 3.3.2 Enhance Dependency Inference

**File**: `src/planning/multi_pass_planner.py` (new method)

**Required Addition**:
```python
def infer_dependencies_enhanced(
    self,
    requirements: List[Requirement]
) -> List[Edge]:
    """
    Multi-strategy dependency inference

    Strategies:
    1. Explicit dependencies from spec metadata
    2. CRUD dependencies (create before read/update/delete)
    3. Pattern-based dependencies
    4. Semantic dependencies (future: LLM-based)
    """
    edges = []

    # Strategy 1: Explicit from spec
    edges.extend(self._explicit_dependencies(requirements))

    # Strategy 2: CRUD rules
    edges.extend(self._crud_dependencies(requirements))

    # Strategy 3: Pattern-based
    edges.extend(self._pattern_dependencies(requirements))

    # Deduplicate and validate
    return self._validate_edges(edges)

def _crud_dependencies(
    self,
    requirements: List[Requirement]
) -> List[Edge]:
    """
    Infer CRUD dependencies

    Rule: Create must come before Read/Update/Delete for same entity
    """
    edges = []
    entities = self._group_by_entity(requirements)

    for entity_name, reqs in entities.items():
        create_req = next(
            (r for r in reqs if r.operation == 'create'),
            None
        )

        if not create_req:
            continue

        for req in reqs:
            if req.operation in ['read', 'list', 'update', 'delete']:
                edges.append(Edge(
                    from_node=create_req.id,
                    to_node=req.id,
                    type='crud_dependency',
                    reason=f"{entity_name} must be created before {req.operation}"
                ))

    return edges

def _group_by_entity(
    self,
    requirements: List[Requirement]
) -> Dict[str, List[Requirement]]:
    """Group requirements by entity (Product, Customer, Cart, etc.)"""
    entities = {}

    for req in requirements:
        # Extract entity from requirement
        # Example: "create_product" → "product"
        entity = self._extract_entity(req)

        if entity not in entities:
            entities[entity] = []

        entities[entity].append(req)

    return entities

def _extract_entity(self, req: Requirement) -> str:
    """Extract entity name from requirement"""
    # Simple heuristic: look for known entities
    text = req.description.lower()

    entities = ['product', 'customer', 'cart', 'order', 'payment']

    for entity in entities:
        if entity in text:
            return entity

    return 'unknown'
```

#### 3.3.3 Validate Execution Order

**File**: `src/planning/multi_pass_planner.py` (new method)

**Required Addition**:
```python
def validate_execution_order(self, dag: DAG) -> float:
    """
    Validate if DAG allows correct execution order

    Checks:
    - CRUD: Create before Read/Update/Delete
    - Workflow: Cart before Checkout, Checkout before Payment

    Returns:
        Score 0.0-1.0 (1.0 = all checks pass)
    """
    violations = []

    # Check 1: CRUD ordering
    for entity in ['product', 'customer', 'cart', 'order']:
        create_wave = self._find_wave(dag, f"create_{entity}")
        read_wave = self._find_wave(dag, f"read_{entity}")

        if read_wave is not None and create_wave is not None:
            if read_wave <= create_wave:
                violations.append(
                    f"Read {entity} (wave {read_wave}) before create (wave {create_wave})"
                )

    # Check 2: Workflow ordering
    if self._has_node(dag, "checkout_cart"):
        cart_wave = self._find_wave(dag, "create_cart")
        checkout_wave = self._find_wave(dag, "checkout_cart")

        if checkout_wave is not None and cart_wave is not None:
            if checkout_wave <= cart_wave:
                violations.append(
                    f"Checkout (wave {checkout_wave}) before cart (wave {cart_wave})"
                )

    # Calculate score
    total_checks = len(['product', 'customer', 'cart', 'order']) + 1
    score = 1.0 - (len(violations) / total_checks) if total_checks > 0 else 1.0

    if violations:
        logger.warning(f"Execution order violations: {violations}")

    return score
```

**Acceptance Criteria**:
- ✅ DAG accuracy: 57% → 80%+
- ✅ Ground truth defined for all test specs
- ✅ Execution order validation passes (score > 0.9)
- ✅ Overall precision increases by ~2%

---

### 3.4 Milestone 4: Refine Metrics Presentation

**Priority**: 🟢 Low
**Effort**: 🟢 Low (2-3 hours)
**Impact**: UX improvement (no precision change)

#### 3.4.1 Enhanced Entity Report

**File**: `src/validation/compliance_validator.py` (modify report formatting)

**Current Output**:
```
✅ Semantic validation PASSED: 100.0% compliance
    - Entities: 15/4    # ⚠️ Confusing
    - Endpoints: 19/17  # ⚠️ Confusing
```

**Target Output**:
```
✅ Semantic validation PASSED: 100.0% compliance

📦 Entities (4 required, all present):
   ✅ Product, Customer, Cart, Order

   📝 Additional models (best practices):
   - Request/Response schemas: 8 (ProductCreate, CustomerCreate, ...)
   - Enums: 3 (CartStatus, OrderStatus, PaymentStatus)

🌐 Endpoints (17 required, all present):
   ✅ POST /products, GET /products, ...

   📝 Additional endpoints (best practices):
   - GET / (API root)
   - GET /health (health check)

✅ All required elements implemented
✅ No missing requirements
```

**Required Implementation**:
```python
def _format_entity_report(
    self,
    report: ComplianceReport
) -> str:
    """
    Enhanced entity report with categorization

    Separates:
    - Domain entities (Product, Customer, etc.)
    - Request/Response schemas (ProductCreate, etc.)
    - Enums (Status enums)
    """
    # Categorize entities
    domain_entities = []
    schemas = []
    enums = []

    for entity in report.entities_implemented:
        if entity in report.entities_expected:
            domain_entities.append(entity)
        elif entity.endswith(('Create', 'Update', 'Request', 'Response')):
            schemas.append(entity)
        elif entity.endswith('Status'):
            enums.append(entity)
        else:
            # Unknown category
            domain_entities.append(entity)

    # Format output
    lines = []
    lines.append(f"\n📦 Entities ({len(report.entities_expected)} required, {len(domain_entities)} present):")
    lines.append(f"   ✅ {', '.join(domain_entities)}")

    if schemas or enums:
        lines.append(f"\n   📝 Additional models (best practices):")
        if schemas:
            lines.append(f"   - Request/Response schemas: {len(schemas)}")
        if enums:
            lines.append(f"   - Enums: {len(enums)}")

    return "\n".join(lines)
```

**Acceptance Criteria**:
- ✅ Output clearly distinguishes domain entities from schemas
- ✅ No confusion about "over-generation"
- ✅ Best practices (enums, schemas) are highlighted positively

---

## 4. Implementation Plan

### 4.1 Timeline

```
Week 1: Quick Wins
├─ Day 1-2: Milestone 1 (Classification Metrics)
│           Expected gain: +12% precision
└─ Day 3-5: Milestone 4 (Presentation)
            Expected gain: UX improvement

Week 2: Pattern Matching
├─ Day 1-2: Pattern DB cleanup
├─ Day 3-4: Adaptive thresholds
└─ Day 5: Keyword fallback
            Expected gain: +3% precision

Week 3: DAG Construction
├─ Day 1-2: Ground truth definition
├─ Day 3-4: Enhanced dependency inference
└─ Day 5: Execution order validation
            Expected gain: +2% precision

Week 4: Testing & Validation
├─ Day 1-3: Regression testing (20+ specs)
├─ Day 4: Documentation updates
└─ Day 5: Release preparation
```

### 4.2 Dependencies

```
Milestone 1 → No dependencies (can start immediately)
Milestone 2 → Requires ground truth from Milestone 1 tests
Milestone 3 → Requires ground truth definition
Milestone 4 → No dependencies (can run parallel with 1)
```

### 4.3 Resource Requirements

- **Developer Time**: 3-4 weeks (1 developer full-time)
- **Infrastructure**: Existing (no new services required)
- **Data**: Ground truth definition for 20+ test specs

---

## 5. Testing Strategy

### 5.1 Unit Tests

**New Test Files**:
```
tests/unit/
├─ test_pattern_matcher_fallback.py
├─ test_classification_validator.py
├─ test_dag_dependency_inference.py
└─ test_execution_order_validator.py
```

**Coverage Target**: 90%+ for new code

### 5.2 Integration Tests

**Test Specs**:
- `ecommerce_api_simple.md` (current baseline)
- `simple_task_api.md` (existing)
- 18+ additional specs covering:
  - CRUD-only apps
  - Workflow-heavy apps
  - Payment integration apps
  - Multi-entity apps

**Validation**:
- Overall precision > 85% on all specs
- Semantic compliance maintains 100%
- No regressions in execution success rate

### 5.3 Regression Testing

**Process**:
1. Run E2E pipeline on 20+ specs
2. Compare metrics before/after changes
3. Ensure no degradation in:
   - Semantic compliance
   - Execution success rate
   - Test pass rate
   - Code quality

**Acceptance Gate**:
- 95% of specs show precision improvement
- 0 specs show compliance degradation

---

## 6. Monitoring & Observability

### 6.1 Metrics to Track

**Pipeline Metrics**:
```python
metrics = {
    'overall_precision': float,
    'pattern_f1': float,
    'pattern_recall': float,
    'classification_accuracy': float,
    'dag_accuracy': float,
    'semantic_compliance': float,
    'execution_success_rate': float,
    'test_pass_rate': float
}
```

**Per-Spec Metrics**:
```python
spec_metrics = {
    'spec_name': str,
    'precision_before': float,
    'precision_after': float,
    'precision_delta': float,
    'compliance_before': float,
    'compliance_after': float
}
```

### 6.2 Alerting

**Alert Conditions**:
- Overall precision < 80% (warning)
- Semantic compliance < 95% (critical)
- Execution success rate < 95% (critical)
- Pattern recall < 60% (warning)

### 6.3 Dashboards

**Grafana Dashboard**:
```
DevMatrix Pipeline Precision
├─ Overall Precision (trend over time)
├─ Phase-by-Phase Breakdown
├─ Pattern Matching Stats
├─ Classification Accuracy
├─ DAG Construction Quality
└─ Execution Success Rate
```

---

## 7. Risks & Mitigations

### Risk 1: Ground Truth Subjectivity

**Risk**: Manual definition of "expected patterns" and "expected DAG" is subjective

**Impact**: Medium
**Probability**: High

**Mitigation**:
- Start with simple, well-defined specs
- Iterate with human validation
- Document rationale for each ground truth decision
- Use consensus approach (2+ reviewers)

### Risk 2: Regression in Semantic Compliance

**Risk**: Changes to pattern matching might break code generation

**Impact**: High
**Probability**: Low

**Mitigation**:
- Comprehensive test suite before merge
- Feature flags for new matchers
- Automated rollback on compliance drop
- Staged rollout (20% → 50% → 100%)

### Risk 3: Threshold Tuning Complexity

**Risk**: Adaptive thresholds may have unexpected effects

**Impact**: Medium
**Probability**: Medium

**Mitigation**:
- A/B testing with different threshold values
- Detailed logging of match decisions
- Rollback capability
- Monitoring alerts on precision drops

### Risk 4: Performance Degradation

**Risk**: Keyword fallback adds latency

**Impact**: Low
**Probability**: Medium

**Mitigation**:
- Benchmark pattern matching performance
- Set maximum fallback execution time (100ms)
- Cache keyword extraction results
- Parallel execution of embedding + keyword matching

---

## 8. Rollout Plan

### Phase 1: Internal Testing (Week 1-2)

- Deploy to dev environment
- Run on internal test specs
- Validate metrics improvement
- No production traffic

### Phase 2: Canary Deployment (Week 3)

- Route 20% of specs through improved pipeline
- Monitor metrics closely
- Compare with control group (80% baseline)
- Ready to rollback if issues

### Phase 3: Full Rollout (Week 4)

- If canary shows +15% precision improvement
- Route 100% of traffic
- Monitor for 1 week
- Document final results

### Rollback Triggers

- Overall precision drops below baseline (73%)
- Semantic compliance drops below 95%
- Execution failures > 5%
- Critical errors in any phase

---

## 9. Success Metrics & KPIs

### 9.1 Primary KPIs

| KPI | Target | Measurement |
|-----|--------|-------------|
| Overall Precision | 90%+ | Weighted average across all phases |
| Pattern F1-Score | 80%+ | Harmonic mean of precision/recall |
| Classification Accuracy | 80%+ | Correct / Total classifications |
| DAG Accuracy | 80%+ | Correct edges / Expected edges |

### 9.2 Secondary KPIs

| KPI | Target | Measurement |
|-----|--------|-------------|
| Semantic Compliance | 100% | (Maintained) |
| Execution Success | 100% | (Maintained) |
| Test Pass Rate | 95%+ | (Maintained or improved) |
| Pipeline Latency | < 2 min | P95 execution time |

### 9.3 Business Impact

**Expected Outcomes**:
- Higher confidence in generated code quality
- Reduced manual review time for generated apps
- Better visibility into pipeline performance
- Foundation for future precision improvements

---

## 10. Documentation Updates

### 10.1 Required Documentation

**Technical Docs**:
- `PATTERN_MATCHING.md` - Updated with fallback strategy
- `CLASSIFICATION.md` - New doc on ground truth format
- `DAG_CONSTRUCTION.md` - Enhanced dependency inference
- `METRICS_GUIDE.md` - Precision calculation explained

**API Docs**:
- PrecisionMetrics class reference
- ComplianceValidator enhancements
- New validation methods

**User Guides**:
- How to define classification ground truth
- How to interpret precision metrics
- Troubleshooting precision issues

### 10.2 Training Materials

- Internal workshop on precision improvements
- Demo video of enhanced metrics presentation
- FAQ on new metrics tracking

---

## 11. Appendix

### 11.1 File Changes Summary

```
Files to Modify:
├─ tests/e2e/real_e2e_full_pipeline.py
├─ tests/e2e/precision_metrics.py
├─ src/services/pattern_matching/matcher.py
├─ src/planning/multi_pass_planner.py
├─ src/validation/compliance_validator.py
└─ tests/e2e/test_specs/*.md (ground truth addition)

New Files:
├─ scripts/audit_patterns.py
└─ tests/unit/test_*.py (new test files)

Total LOC Impact: ~800 new lines, ~200 modified lines
```

### 11.2 References

**Codebase Locations**:
- Pattern Matching: [src/services/pattern_matching/](/src/services/pattern_matching/)
- Requirements Classification: [src/services/requirements_classifier.py](/src/services/requirements_classifier.py)
- Multi-Pass Planning: [src/planning/multi_pass_planner.py](/src/planning/multi_pass_planner.py)
- Compliance Validation: [src/validation/compliance_validator.py](/src/validation/compliance_validator.py)
- E2E Tests: [tests/e2e/](/tests/e2e/)

**Related Documents**:
- [DevMatrix E2E Pipeline Analysis](../../claudedocs/DEVMATRIX_E2E_PIPELINE_ANALYSIS.md)
- [Milestone 4 Completion Report](../../claudedocs/MILESTONE_4_COMPLETION_REPORT.md)
- [Original Improvement Plan](planning/requirements.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Approved By**: [Pending]
**Next Review**: After Milestone 1 completion
