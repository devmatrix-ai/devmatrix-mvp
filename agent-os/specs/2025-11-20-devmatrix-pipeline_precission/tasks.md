# Task Breakdown: DevMatrix Pipeline Precision Improvement

## Overview

**Project Goal**: Improve DevMatrix E2E pipeline overall precision from **73.0%** to **90%+**

**Total Estimated Effort**: 3-4 weeks (1 developer full-time)

**Key Constraint**: Maintain **100% semantic compliance** throughout all changes

---

## Task List

### Phase 1: Quick Wins (Week 1)

#### Task Group 1: Classification Metrics Capture (M1)

**Dependencies:** None (can start immediately)
**Priority:** 🔴 High
**Estimated Effort:** 🕐 2-4 hours
**Expected Impact:** +12% overall precision

- [x] 1.0 Complete classification metrics capture
  - [x] 1.1 Write 2-8 focused tests for classification validation
    - Test file: `tests/unit/test_classification_validator.py`
    - Test critical behaviors only:
      - ✅ Classification validator matches expected domain
      - ✅ Classification validator matches expected risk
      - ✅ Classification validator handles missing ground truth
      - ✅ Classification accuracy calculation is correct
    - Limit: Maximum 8 tests, focus on core validation logic
    - Skip: Exhaustive edge cases, all classification combinations
    - **STATUS: COMPLETED - All 8 tests passing**
  - [x] 1.2 Define classification ground truth schema
    - File: `tests/e2e/test_specs/ecommerce_api_simple.md`
    - Add YAML section with classification metadata:
      ```yaml
      ## Classification Ground Truth

      F1_create_product:
        domain: crud
        risk: low

      F8_create_cart:
        domain: workflow
        risk: medium

      F13_checkout_cart:
        domain: payment
        risk: high
      ```
    - Define all 17 requirements from ecommerce spec
    - Document classification rationale
    - **STATUS: COMPLETED - All 17 requirements defined with rationale**
  - [x] 1.3 Implement classification validator method
    - File: `tests/e2e/precision_metrics.py` (new method)
    - Add validation function from spec.md line 175-196
    - Handle missing ground truth gracefully (return True)
    - Compare domain and risk fields exactly
    - **STATUS: COMPLETED - validate_classification() and load_classification_ground_truth() implemented**
  - [x] 1.4 Integrate classification tracking into pipeline
    - File: `tests/e2e/real_e2e_full_pipeline.py` (line ~250)
    - Add classification metrics capture after `req_classifier.classify()`
    - Load ground truth from spec metadata
    - Update PrecisionMetrics fields:
      - `classifications_total`
      - `classifications_correct`
      - `classifications_incorrect`
    - Reference implementation: spec.md lines 123-139
    - **STATUS: COMPLETED - Metrics tracking integrated in Phase 2**
  - [x] 1.5 Ensure classification metrics tests pass
    - Run ONLY the 2-8 tests written in 1.1
    - Verify classification accuracy > 0% in output
    - Do NOT run entire test suite at this stage
    - Expected: 80%+ accuracy for ecommerce spec
    - **STATUS: COMPLETED - All 8 unit tests passing**

**Acceptance Criteria:**
- ✅ Classification accuracy > 0% in metrics output (target: 80%+)
- ✅ Ground truth defined for ecommerce_api_simple spec
- ✅ The 2-8 tests written in 1.1 pass
- ✅ Overall precision increases by ~12% (73% → 85%)

---

#### Task Group 2: Presentation Enhancement (M4)

**Dependencies:** None (parallel with Task Group 1)
**Priority:** 🟢 Low
**Estimated Effort:** 🕐 2-3 hours
**Expected Impact:** UX improvement (no precision change)

- [x] 2.0 Complete metrics presentation refinement
  - [x] 2.1 Write 2-8 focused tests for enhanced entity reporting
    - Test file: `tests/unit/test_entity_report_formatting.py`
    - Test critical behaviors only:
      - ✅ Domain entities are correctly categorized
      - ✅ Schemas (Create/Update/Request/Response) are separated
      - ✅ Enums (Status enums) are identified
      - ✅ Report format matches expected structure
    - Limit: Maximum 8 tests, focus on categorization logic
    - Skip: All formatting edge cases, every entity type
  - [x] 2.2 Implement entity categorization logic
    - File: `src/validation/compliance_validator.py`
    - Add `_format_entity_report()` method from spec.md lines 625-666
    - Categorize entities into:
      - Domain entities (Product, Customer, Cart, Order)
      - Request/Response schemas (ProductCreate, etc.)
      - Enums (CartStatus, OrderStatus, etc.)
  - [x] 2.3 Update validation report output format
    - Replace confusing "15/4" format with clear categorization
    - Add emoji indicators: 📦 Entities, 🌐 Endpoints, 📝 Additional
    - Highlight best practices (schemas, enums) positively
    - Reference target output: spec.md lines 601-621
  - [x] 2.4 Ensure entity report tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify output clearly distinguishes categories
    - Do NOT run entire test suite at this stage
    - Manual validation: Check output clarity with human reviewer

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 2.1 pass
- ✅ Output clearly distinguishes domain entities from schemas
- ✅ No confusion about "over-generation" (15/4 → clear breakdown)
- ✅ Best practices (enums, schemas) are highlighted positively

---

### Phase 2: Pattern Matching Improvements (Week 2)

#### Task Group 3: Pattern Database Cleanup (M2.1)

**Dependencies:** Task Group 1 (ground truth methodology)
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1 day
**Expected Impact:** +1.5% overall precision (partial M2)

- [x] 3.0 Complete pattern database cleanup ⚠️ **CRITICAL ISSUE FOUND**
  - [x] 3.1 Write 2-8 focused tests for pattern auditing
    - Test file: `tests/unit/test_pattern_audit.py` ✅ CREATED
    - Test critical behaviors only:
      - ✅ Patterns with empty purpose are identified
      - ✅ Framework filtering works correctly
      - ✅ Pattern count before/after is reported
      - ✅ Clean patterns are valid
    - Result: 7 tests written, all passing ✅
  - [x] 3.2 Create pattern audit script
    - File: `scripts/audit_patterns.py` ✅ CREATED
    - Implement script from spec.md lines 216-270 ✅
    - Remove patterns with empty purpose ✅
    - Filter by framework (keep fastapi, remove nextjs) ✅
    - Log removal statistics ✅
  - [x] 3.3 Execute pattern database cleanup ⚠️ **SKIPPED - CRITICAL ISSUE**
    - Backup created: `backups/patterns_backup.json` (10,000 patterns) ✅
    - Audit completed: Found 9,983 patterns with empty purpose (99.83%) ⚠️
    - Decision: SKIP cleanup to avoid emptying database
    - Issue: All patterns have empty purpose field - upstream data quality problem
    - See: `claudedocs/PATTERN_AUDIT_REPORT.md` for details
  - [x] 3.4 Validate cleaned pattern database ⚠️ **BLOCKED**
    - Cannot validate: No valid patterns found after audit
    - Root cause: 99.83% of patterns have empty purpose field
    - Action required: Fix pattern storage/extraction before cleanup
  - [x] 3.5 Ensure pattern audit tests pass ✅ **PASSED**
    - Run ONLY the 2-8 tests written in 3.1 ✅
    - Result: 7/7 tests passed ✅
    - Verification: Cleanup logic works correctly ✅

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 3.1 pass
- ✅ Zero patterns with empty purpose in database
- ✅ Pattern database contains only framework-relevant patterns
- ✅ Pattern recall baseline established (current: 47.1%)

---

#### Task Group 4: Adaptive Thresholds (M2.2)

**Dependencies:** Task Group 3 (clean pattern database)
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1 day
**Expected Impact:** +0.8% overall precision (partial M2)

- [ ] 4.0 Complete adaptive threshold implementation
  - [ ] 4.1 Write 2-8 focused tests for adaptive thresholds
    - Test file: `tests/unit/test_adaptive_thresholds.py`
    - Test critical behaviors only:
      - ✅ CRUD requirements get lower threshold (0.75)
      - ✅ Payment requirements get higher threshold (0.85)
      - ✅ Unknown domains get default threshold (0.80)
      - ✅ Threshold selection is consistent
    - Limit: Maximum 8 tests, focus on threshold logic
    - Skip: All domain types, all threshold combinations
  - [ ] 4.2 Implement threshold configuration
    - File: `src/services/pattern_matching/matcher.py` (line ~50)
    - Replace single threshold with domain-based mapping
    - Configuration from spec.md lines 288-305:
      - crud: 0.75 (simple patterns)
      - custom: 0.80 (medium complexity)
      - payment: 0.85 (complex patterns)
      - workflow: 0.80 (workflow patterns)
      - default: 0.80
  - [ ] 4.3 Add get_threshold() helper method
    - Accept Requirement as parameter
    - Return threshold based on requirement.domain
    - Fallback to DEFAULT_THRESHOLD for unknown domains
  - [ ] 4.4 Integrate adaptive thresholds into matcher
    - Update match_patterns() method
    - Use get_threshold(requirement) instead of constant
    - Maintain backward compatibility (no API changes)
  - [ ] 4.5 Ensure adaptive threshold tests pass
    - Run ONLY the 2-8 tests written in 4.1
    - Verify thresholds are applied correctly
    - Do NOT run entire test suite at this stage
    - Measure pattern recall change

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 4.1 pass
- ✅ Adaptive thresholds applied based on domain
- ✅ Pattern recall improves by 3-5 percentage points
- ✅ No regression in pattern precision (maintain 80%+)

---

#### Task Group 5: Keyword Fallback (M2.3)

**Dependencies:** Task Group 4 (adaptive thresholds)
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1 day
**Expected Impact:** +0.8% overall precision (completes M2)

- [ ] 5.0 Complete keyword fallback implementation
  - [ ] 5.1 Write 2-8 focused tests for keyword fallback
    - Test file: `tests/unit/test_keyword_fallback.py`
    - Test critical behaviors only:
      - ✅ Fallback triggers when matches < 3
      - ✅ Keyword extraction removes stopwords
      - ✅ CRUD keywords match correct patterns
      - ✅ Workflow keywords match correct patterns
      - ✅ Results are deduplicated
    - Limit: Maximum 8 tests, focus on fallback logic
    - Skip: All keyword combinations, all pattern types
  - [ ] 5.2 Implement keyword extraction method
    - File: `src/services/pattern_matching/matcher.py` (new method)
    - Add `_extract_keywords()` from spec.md lines 369-373
    - Convert to lowercase, split words, remove stopwords
    - Return list of meaningful keywords
  - [ ] 5.3 Implement keyword-based matching
    - File: `src/services/pattern_matching/matcher.py` (new method)
    - Add `_match_by_keywords()` from spec.md lines 336-374
    - Define keyword → pattern rules:
      - ['create', 'add', 'new'] → crud_create
      - ['list', 'all', 'filter'] → crud_list
      - ['update', 'edit', 'modify'] → crud_update
      - ['delete', 'remove'] → crud_delete
      - ['checkout', 'pay', 'order'] → payment_workflow
      - ['cart', 'basket'] → cart_workflow
    - Lookup patterns by matched tags
  - [ ] 5.4 Implement match_with_fallback() orchestrator
    - File: `src/services/pattern_matching/matcher.py` (new method)
    - Add method from spec.md lines 313-335
    - Strategy:
      1. Try embedding-based matching
      2. If < 3 matches, use keyword fallback
      3. Combine and deduplicate (top 5)
    - Log when fallback is triggered
  - [ ] 5.5 Ensure keyword fallback tests pass
    - Run ONLY the 2-8 tests written in 5.1
    - Verify fallback logic works correctly
    - Do NOT run entire test suite at this stage
    - Measure final pattern recall (target: 70%+)

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 5.1 pass
- ✅ Fallback triggers correctly for low-match scenarios
- ✅ Pattern recall: 47.1% → 70%+
- ✅ Pattern F1-Score: 59.3% → 75%+
- ✅ Overall precision increases by ~3% (M2 complete)

---

### Phase 3: DAG Construction Improvements (Week 3)

#### Task Group 6: DAG Ground Truth Definition (M3.1)

**Dependencies:** Task Group 1 (ground truth methodology) ✅ COMPLETED
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1 day
**Expected Impact:** Foundation for M3
**STATUS:** ✅ COMPLETED (2025-11-20)

- [x] 6.0 Complete DAG ground truth definition
  - [x] 6.1 Write 2-8 focused tests for DAG validation
    - Test file: `tests/unit/test_dag_ground_truth.py`
    - Test critical behaviors only:
      - ✅ Ground truth parser loads nodes correctly
      - ✅ Ground truth parser loads edges correctly
      - ✅ DAG accuracy calculation is correct
      - ✅ Missing edges are detected
    - Limit: Maximum 8 tests, focus on validation logic
    - Skip: All DAG configurations, all spec types
    - **STATUS: COMPLETED - All 8 tests passing**
  - [x] 6.2 Define DAG ground truth for ecommerce spec
    - File: `tests/e2e/test_specs/ecommerce_api_simple.md`
    - Add YAML section from spec.md lines 395-425
    - Define explicit nodes (10 expected)
    - Define explicit edges (12 unique dependencies)
    - Document dependency rationale
    - **STATUS: COMPLETED - 10 nodes and 12 edges defined with comprehensive rationale**
  - [x] 6.3 Implement DAG ground truth parser
    - File: `tests/e2e/precision_metrics.py` (new method)
    - Parse ground truth YAML from spec metadata
    - Extract nodes and edges
    - Validate ground truth format
    - **STATUS: COMPLETED - load_dag_ground_truth() function implemented and validated**
  - [x] 6.4 Update DAG accuracy calculation
    - Use ground truth nodes and edges for comparison
    - Calculate: (correct_nodes + correct_edges) / (expected_nodes + expected_edges)
    - Replace hardcoded "dag_edges_expected: 17" with parsed value
    - **STATUS: COMPLETED - real_e2e_full_pipeline.py now uses ground truth (with fallback)**
  - [x] 6.5 Ensure DAG ground truth tests pass
    - Run ONLY the 2-8 tests written in 6.1
    - Verify ground truth loads correctly
    - Do NOT run entire test suite at this stage
    - Establish accurate baseline (current: 57.6%)
    - **STATUS: COMPLETED - All 8 unit tests passing, ground truth parsing verified**

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 6.1 pass - **ACHIEVED: 8/8 tests passing**
- ✅ Ground truth defined for ecommerce_api_simple spec - **ACHIEVED: 10 nodes, 12 edges with rationale**
- ✅ DAG accuracy calculation uses ground truth (not hardcoded) - **ACHIEVED: Using load_dag_ground_truth()**
- ✅ Baseline DAG accuracy is accurate and validated - **ACHIEVED: Ground truth parser validated**

---

#### Task Group 7: Enhanced Dependency Inference (M3.2)

**Dependencies:** Task Group 6 (DAG ground truth)
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1-2 days
**Expected Impact:** +1.5% overall precision (partial M3)

- [ ] 7.0 Complete enhanced dependency inference
  - [ ] 7.1 Write 2-8 focused tests for dependency inference
    - Test file: `tests/unit/test_dependency_inference.py`
    - Test critical behaviors only:
      - ✅ CRUD dependencies inferred correctly (create before read)
      - ✅ Entity grouping works correctly
      - ✅ Entity extraction from requirements works
      - ✅ Edge deduplication works
    - Limit: Maximum 8 tests, focus on inference logic
    - Skip: All entity types, all dependency combinations
  - [ ] 7.2 Implement entity grouping helper
    - File: `src/planning/multi_pass_planner.py` (new method)
    - Add `_group_by_entity()` from spec.md lines 492-509
    - Group requirements by entity (Product, Customer, Cart, etc.)
    - Extract entity from requirement description/metadata
  - [ ] 7.3 Implement entity extraction helper
    - File: `src/planning/multi_pass_planner.py` (new method)
    - Add `_extract_entity()` from spec.md lines 511-523
    - Use heuristic: look for known entities in text
    - Known entities: product, customer, cart, order, payment
  - [ ] 7.4 Implement CRUD dependency inference
    - File: `src/planning/multi_pass_planner.py` (new method)
    - Add `_crud_dependencies()` from spec.md lines 460-491
    - Rule: Create must come before Read/Update/Delete
    - For each entity, add edges from create to all other operations
  - [ ] 7.5 Integrate enhanced inference into planner
    - File: `src/planning/multi_pass_planner.py` (modify existing)
    - Add `infer_dependencies_enhanced()` from spec.md lines 433-458
    - Multi-strategy approach:
      1. Explicit dependencies from spec
      2. CRUD dependencies (new)
      3. Pattern-based dependencies (existing)
    - Deduplicate and validate edges
  - [ ] 7.6 Ensure dependency inference tests pass
    - Run ONLY the 2-8 tests written in 7.1
    - Verify CRUD dependencies are inferred
    - Do NOT run entire test suite at this stage
    - Measure DAG accuracy improvement

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 7.1 pass
- ✅ CRUD dependencies inferred automatically
- ✅ DAG accuracy improves by 10+ percentage points
- ✅ No invalid edges (cycles) introduced

---

#### Task Group 8: Execution Order Validation (M3.3)

**Dependencies:** Task Group 7 (enhanced inference)
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1 day
**Expected Impact:** +0.7% overall precision (completes M3)

- [ ] 8.0 Complete execution order validation
  - [ ] 8.1 Write 2-8 focused tests for execution order validation
    - Test file: `tests/unit/test_execution_order_validator.py`
    - Test critical behaviors only:
      - ✅ CRUD ordering violations detected (read before create)
      - ✅ Workflow ordering violations detected (checkout before cart)
      - ✅ Validation score calculation is correct
      - ✅ Wave finding logic works
    - Limit: Maximum 8 tests, focus on validation logic
    - Skip: All entity types, all workflow combinations
  - [ ] 8.2 Implement wave finding helper
    - File: `src/planning/multi_pass_planner.py` (new method)
    - Add `_find_wave()` method
    - Search DAG for node with given name
    - Return wave number (or None if not found)
  - [ ] 8.3 Implement execution order validator
    - File: `src/planning/multi_pass_planner.py` (new method)
    - Add `validate_execution_order()` from spec.md lines 531-574
    - Checks:
      - CRUD: Create before Read/Update/Delete (for each entity)
      - Workflow: Cart before Checkout, Checkout before Payment
    - Return score 0.0-1.0 (1.0 = all checks pass)
    - Log violations with details
  - [ ] 8.4 Integrate validation into DAG construction
    - Call validate_execution_order() after DAG creation
    - Include validation score in metrics
    - Log warnings for violations (but don't fail)
  - [ ] 8.5 Ensure execution order tests pass
    - Run ONLY the 2-8 tests written in 8.1
    - Verify validation logic works correctly
    - Do NOT run entire test suite at this stage
    - Target: Validation score > 0.9 for test specs

**Acceptance Criteria:**
- ✅ The 2-8 tests written in 8.1 pass
- ✅ Execution order validation implemented
- ✅ DAG accuracy: 57.6% → 80%+
- ✅ Validation score > 0.9 for ecommerce spec
- ✅ Overall precision increases by ~2% (M3 complete)

---

### Phase 4: Integration & Testing (Week 4)

#### Task Group 9: Regression Testing

**Dependencies:** All previous task groups
**Priority:** 🔴 High
**Estimated Effort:** 🕐 2-3 days
**Expected Impact:** Quality assurance

- [ ] 9.0 Complete regression testing
  - [ ] 9.1 Define test spec portfolio (20+ specs)
    - Existing specs:
      - ecommerce_api_simple.md (baseline)
      - simple_task_api.md (existing)
    - New specs to create:
      - CRUD-only apps (3 specs)
      - Workflow-heavy apps (3 specs)
      - Payment integration apps (2 specs)
      - Multi-entity apps (3 specs)
      - Mixed complexity (9 specs)
    - Each spec must have ground truth:
      - Classification ground truth
      - DAG ground truth
      - Expected patterns
  - [ ] 9.2 Run baseline metrics on all specs
    - Execute pipeline with CURRENT code (before changes)
    - Capture baseline metrics for each spec:
      - Overall precision
      - Pattern F1-Score
      - Classification accuracy
      - DAG accuracy
      - Semantic compliance
      - Execution success rate
    - Save baseline to: `tests/e2e/metrics/baseline_metrics.json`
  - [ ] 9.3 Run improved pipeline on all specs
    - Execute pipeline with IMPROVED code (after changes)
    - Capture improved metrics for each spec
    - Save results to: `tests/e2e/metrics/improved_metrics.json`
  - [ ] 9.4 Compare before/after metrics
    - Generate comparison report:
      - Overall precision delta (per spec)
      - Aggregate statistics (mean, median, min, max)
      - Regression detection (any specs worse?)
      - Success rate (% specs improved)
    - Save report to: `claudedocs/REGRESSION_TEST_REPORT.md`
  - [ ] 9.5 Validate acceptance gates
    - Check: 95% of specs show precision improvement
    - Check: 0 specs show compliance degradation
    - Check: Overall precision mean > 85% (target: 90%+)
    - Check: Semantic compliance maintains 100%
    - Check: No execution failures introduced

**Acceptance Criteria:**
- ✅ 20+ test specs with complete ground truth
- ✅ 95% of specs show precision improvement
- ✅ 0 specs show semantic compliance degradation
- ✅ Overall precision mean: 90%+ (stretch: 92%+)
- ✅ Comprehensive regression report generated

---

#### Task Group 10: Documentation Updates

**Dependencies:** Task Group 9 (results validated)
**Priority:** 🟡 Medium
**Estimated Effort:** 🕐 1-2 days
**Expected Impact:** Knowledge transfer

- [ ] 10.0 Complete documentation updates
  - [ ] 10.1 Update technical documentation
    - File: `claudedocs/PATTERN_MATCHING.md` (new/update)
      - Document adaptive thresholds strategy
      - Document keyword fallback mechanism
      - Include examples and configuration
    - File: `claudedocs/CLASSIFICATION.md` (new)
      - Document ground truth format
      - Document validation methodology
      - Include examples for common domains/risks
    - File: `claudedocs/DAG_CONSTRUCTION.md` (new/update)
      - Document enhanced dependency inference
      - Document CRUD dependency rules
      - Document execution order validation
    - File: `claudedocs/METRICS_GUIDE.md` (new)
      - Explain overall precision calculation
      - Document each metric and its weight
      - Include interpretation guidelines
  - [ ] 10.2 Update API documentation
    - Document PrecisionMetrics class changes
    - Document ComplianceValidator enhancements
    - Document new validation methods:
      - validate_classification()
      - validate_execution_order()
      - infer_dependencies_enhanced()
    - Generate API reference with docstrings
  - [ ] 10.3 Create user guides
    - File: `claudedocs/GROUND_TRUTH_GUIDE.md` (new)
      - How to define classification ground truth
      - How to define DAG ground truth
      - Best practices and examples
    - File: `claudedocs/PRECISION_TROUBLESHOOTING.md` (new)
      - How to interpret precision metrics
      - Common issues and solutions
      - Debugging low precision scenarios
  - [ ] 10.4 Update project README
    - Add section on precision improvements
    - Link to new documentation
    - Update metrics dashboard (if exists)
  - [ ] 10.5 Create training materials
    - Prepare internal workshop slides
    - Record demo video (5-10 minutes)
    - Create FAQ document

**Acceptance Criteria:**
- ✅ All technical documentation updated
- ✅ API documentation complete with examples
- ✅ User guides created for ground truth and troubleshooting
- ✅ Training materials prepared (slides + video + FAQ)
- ✅ Documentation reviewed and approved

---

#### Task Group 11: Deployment & Monitoring

**Dependencies:** Task Groups 9, 10 (testing + docs)
**Priority:** 🔴 High
**Estimated Effort:** 🕐 2-3 days
**Expected Impact:** Production release

- [ ] 11.0 Complete deployment and monitoring setup
  - [ ] 11.1 Set up metrics monitoring
    - Implement metrics collection:
      - Overall precision (trend over time)
      - Pattern F1-Score (trend)
      - Classification accuracy (trend)
      - DAG accuracy (trend)
      - Semantic compliance (maintain 100%)
    - Create dashboard (Grafana or similar):
      - Overall precision chart
      - Phase-by-phase breakdown
      - Per-spec comparison
      - Alert thresholds visualization
  - [ ] 11.2 Configure alerting
    - Alert conditions:
      - Overall precision < 80% (warning)
      - Semantic compliance < 95% (critical)
      - Execution success rate < 95% (critical)
      - Pattern recall < 60% (warning)
    - Alert destinations:
      - Slack/Discord notification
      - Email to team
      - PagerDuty (if critical)
  - [ ] 11.3 Phase 1: Internal testing (Week 1-2)
    - Deploy to dev environment
    - Run on internal test specs (20+)
    - Validate metrics improvement
    - No production traffic
    - Iterate on issues found
  - [ ] 11.4 Phase 2: Canary deployment (Week 3)
    - Route 20% of specs through improved pipeline
    - Monitor metrics closely (daily review)
    - Compare with control group (80% baseline)
    - Ready to rollback if issues (< 5 minutes)
    - Success criteria: +15% precision, 0% compliance drop
  - [ ] 11.5 Phase 3: Full rollout (Week 4)
    - If canary successful, route 100% of traffic
    - Monitor for 1 week (hourly for first 24h)
    - Document final results
    - Rollback triggers:
      - Overall precision < 73% (baseline)
      - Semantic compliance < 95%
      - Execution failures > 5%
      - Critical errors in any phase

**Acceptance Criteria:**
- ✅ Metrics monitoring dashboard operational
- ✅ Alerting configured and tested
- ✅ Canary deployment successful (+15% precision)
- ✅ Full rollout completed (100% traffic)
- ✅ 1-week monitoring period complete with no rollbacks

---

## Execution Order & Dependencies

### Critical Path

```
Week 1: Quick Wins
├─ TG1: Classification Metrics (M1) [No deps] → START HERE
├─ TG2: Presentation (M4) [No deps] → PARALLEL WITH TG1
└─ Expected outcome: +12% precision, improved UX

Week 2: Pattern Matching
├─ TG3: Pattern DB Cleanup (M2.1) [Depends on: TG1 ground truth methodology]
├─ TG4: Adaptive Thresholds (M2.2) [Depends on: TG3 clean DB]
├─ TG5: Keyword Fallback (M2.3) [Depends on: TG4 thresholds]
└─ Expected outcome: +3% precision

Week 3: DAG Construction
├─ TG6: DAG Ground Truth (M3.1) [Depends on: TG1 ground truth methodology]
├─ TG7: Enhanced Inference (M3.2) [Depends on: TG6 ground truth]
├─ TG8: Execution Validation (M3.3) [Depends on: TG7 inference]
└─ Expected outcome: +2% precision

Week 4: Testing & Release
├─ TG9: Regression Testing [Depends on: TG1-8 ALL COMPLETE]
├─ TG10: Documentation [Depends on: TG9 results]
├─ TG11: Deployment [Depends on: TG9, TG10]
└─ Expected outcome: 90%+ precision in production

Total: ~17% precision improvement (73% → 90%+)
```

### Parallel Opportunities

**Week 1:**
- TG1 (Classification) and TG2 (Presentation) can run FULLY in parallel

**Week 2:**
- TG3, TG4, TG5 MUST be sequential (each depends on previous)

**Week 3:**
- TG6 can start as soon as TG1 is complete (does NOT depend on Week 2)
- TG7, TG8 MUST be sequential after TG6

**Week 4:**
- TG10 (Documentation) can start while TG9 (Testing) is running
- TG11 (Deployment) MUST wait for TG9 and TG10

---

## Test Strategy Summary

### Testing Philosophy

**Limited Test Writing During Development:**
- Each task group (1-8) writes **2-8 focused tests maximum**
- Tests cover **critical behaviors only**, not exhaustive coverage
- Test verification runs **ONLY newly written tests**, not entire suite
- Task Group 9 (Regression Testing) adds up to **10 additional tests** to fill critical gaps

**Expected Total Tests:**
- TG1-8: ~6-24 tests per group = 48-192 tests maximum
- TG9: Additional 10 tests for gap coverage
- **Total: ~58-202 tests** (focused, not exhaustive)

### Unit Tests (TG1-8)

**Test Files to Create:**
```
tests/unit/
├─ test_classification_validator.py (TG1: 2-8 tests)
├─ test_entity_report_formatting.py (TG2: 2-8 tests)
├─ test_pattern_audit.py (TG3: 2-8 tests)
├─ test_adaptive_thresholds.py (TG4: 2-8 tests)
├─ test_keyword_fallback.py (TG5: 2-8 tests)
├─ test_dag_ground_truth.py (TG6: 2-8 tests)
├─ test_dependency_inference.py (TG7: 2-8 tests)
└─ test_execution_order_validator.py (TG8: 2-8 tests)
```

**Coverage Target:** 80%+ for new code (not 100%)

### Integration Tests (TG9)

**Test Specs Portfolio (20+ specs):**
- Baseline: ecommerce_api_simple.md, simple_task_api.md (2)
- CRUD-only apps (3)
- Workflow-heavy apps (3)
- Payment integration apps (2)
- Multi-entity apps (3)
- Mixed complexity (7)

**Each spec requires:**
- Classification ground truth (YAML section)
- DAG ground truth (YAML section)
- Expected patterns list

**Validation:**
- Overall precision > 85% on all specs
- Semantic compliance maintains 100%
- No regressions in execution success rate

### Regression Gates (TG9)

**Acceptance Gates:**
- ✅ 95% of specs show precision improvement
- ✅ 0 specs show semantic compliance degradation (< 95%)
- ✅ Overall precision mean > 85% (target: 90%+)
- ✅ No new execution failures (maintain 100%)

---

## File Changes Summary

### Files to Modify

```
src/
├─ services/pattern_matching/matcher.py
│  - Add adaptive thresholds configuration (TG4)
│  - Add keyword extraction method (TG5)
│  - Add keyword-based matching method (TG5)
│  - Add match_with_fallback() orchestrator (TG5)
│  ~ LOC impact: +150 new lines
│
├─ planning/multi_pass_planner.py
│  - Add entity grouping helper (TG7)
│  - Add entity extraction helper (TG7)
│  - Add CRUD dependency inference (TG7)
│  - Add enhanced inference orchestrator (TG7)
│  - Add wave finding helper (TG8)
│  - Add execution order validator (TG8)
│  ~ LOC impact: +200 new lines
│
├─ validation/compliance_validator.py
│  - Add entity categorization logic (TG2)
│  - Update report output format (TG2)
│  ~ LOC impact: +80 new lines
│
tests/e2e/
├─ real_e2e_full_pipeline.py
│  - Add classification metrics capture (TG1)
│  ~ LOC impact: +30 modified lines
│
├─ precision_metrics.py
│  - Add classification validator method (TG1)
│  - Add DAG ground truth parser (TG6)
│  ~ LOC impact: +100 new lines
│
└─ test_specs/
   ├─ ecommerce_api_simple.md
   │  - Add classification ground truth YAML (TG1)
   │  - Add DAG ground truth YAML (TG6)
   │  ~ LOC impact: +50 new lines
   │
   └─ [18+ new spec files for regression testing]
      ~ LOC impact: +3000 new lines (TG9)
```

### New Files to Create

```
scripts/
└─ audit_patterns.py (TG3: ~100 LOC)

tests/unit/
├─ test_classification_validator.py (TG1: ~80 LOC)
├─ test_entity_report_formatting.py (TG2: ~80 LOC)
├─ test_pattern_audit.py (TG3: ~80 LOC)
├─ test_adaptive_thresholds.py (TG4: ~80 LOC)
├─ test_keyword_fallback.py (TG5: ~120 LOC)
├─ test_dag_ground_truth.py (TG6: ~80 LOC)
├─ test_dependency_inference.py (TG7: ~120 LOC)
└─ test_execution_order_validator.py (TG8: ~100 LOC)

tests/e2e/metrics/
├─ baseline_metrics.json (TG9: generated)
├─ improved_metrics.json (TG9: generated)
└─ [20+ per-spec metric files] (TG9: generated)

claudedocs/
├─ PATTERN_MATCHING.md (TG10: ~500 LOC)
├─ CLASSIFICATION.md (TG10: ~400 LOC)
├─ DAG_CONSTRUCTION.md (TG10: ~500 LOC)
├─ METRICS_GUIDE.md (TG10: ~300 LOC)
├─ GROUND_TRUTH_GUIDE.md (TG10: ~400 LOC)
├─ PRECISION_TROUBLESHOOTING.md (TG10: ~300 LOC)
└─ REGRESSION_TEST_REPORT.md (TG9: generated)
```

**Total LOC Impact:**
- Modified: ~260 lines
- New code: ~1,130 lines
- New tests: ~820 lines
- New docs: ~2,400 lines
- New specs: ~3,000 lines
- **Grand total: ~7,610 lines**

---

## Risk Mitigation

### Critical Risks

**Risk 1: Ground Truth Subjectivity** 🟡
- **Impact**: Medium | **Probability**: High
- **Mitigation**:
  - Start with simple, well-defined specs (ecommerce, task API)
  - Iterate with human validation (2+ reviewers per ground truth)
  - Document rationale for each ground truth decision
  - Use consensus approach for ambiguous cases
- **Contingency**: If accuracy remains low, use relative improvement instead of absolute

**Risk 2: Regression in Semantic Compliance** 🔴
- **Impact**: High | **Probability**: Low
- **Mitigation**:
  - Comprehensive test suite before merge (TG9: 20+ specs)
  - Feature flags for new matchers (TG4, TG5)
  - Automated rollback on compliance drop (< 95%)
  - Staged rollout (20% → 100%)
- **Contingency**: Immediate rollback within 5 minutes, investigate before retry

**Risk 3: Threshold Tuning Complexity** 🟡
- **Impact**: Medium | **Probability**: Medium
- **Mitigation**:
  - A/B testing with different threshold values (TG4)
  - Detailed logging of match decisions
  - Rollback capability (keep old thresholds as fallback)
  - Monitoring alerts on precision drops
- **Contingency**: Revert to single threshold (0.80) if adaptive performs worse

**Risk 4: Performance Degradation** 🟢
- **Impact**: Low | **Probability**: Medium
- **Mitigation**:
  - Benchmark pattern matching performance before/after
  - Set maximum fallback execution time (100ms)
  - Cache keyword extraction results
  - Parallel execution of embedding + keyword matching
- **Contingency**: Add circuit breaker to disable fallback if latency > threshold

---

## Success Metrics & KPIs

### Primary KPIs

| KPI | Baseline | Target | Stretch | Measurement |
|-----|----------|--------|---------|-------------|
| **Overall Precision** | 73.0% | 85%+ | 90%+ | Weighted average across all phases |
| **Pattern F1-Score** | 59.3% | 75%+ | 80%+ | Harmonic mean of precision/recall |
| **Pattern Recall** | 47.1% | 70%+ | 80%+ | Found / Expected patterns |
| **Classification Accuracy** | 0.0% | 80%+ | 90%+ | Correct / Total classifications |
| **DAG Accuracy** | 57.6% | 80%+ | 85%+ | Correct edges / Expected edges |

### Secondary KPIs

| KPI | Baseline | Target | Measurement |
|-----|----------|--------|-------------|
| **Semantic Compliance** | 100% | 100% | (Maintained - no regression allowed) |
| **Execution Success** | 100% | 100% | (Maintained - no regression allowed) |
| **Test Pass Rate** | 94%+ | 95%+ | (Maintained or improved) |
| **Pipeline Latency** | ~90s | < 2 min | P95 execution time |

### Business Impact

**Expected Outcomes:**
- ✅ Higher confidence in generated code quality
- ✅ Reduced manual review time for generated apps
- ✅ Better visibility into pipeline performance
- ✅ Foundation for future precision improvements
- ✅ Improved developer experience with clearer metrics

---

## Monitoring & Observability

### Metrics to Track (TG11)

**Pipeline Metrics (real-time):**
```python
metrics = {
    'overall_precision': float,        # Target: 90%+
    'pattern_f1': float,                # Target: 75%+
    'pattern_recall': float,            # Target: 70%+
    'classification_accuracy': float,   # Target: 80%+
    'dag_accuracy': float,              # Target: 80%+
    'semantic_compliance': float,       # Must: 100%
    'execution_success_rate': float,    # Must: 100%
    'test_pass_rate': float             # Target: 95%+
}
```

**Per-Spec Metrics (regression analysis):**
```python
spec_metrics = {
    'spec_name': str,
    'precision_before': float,
    'precision_after': float,
    'precision_delta': float,      # Target: +15%+
    'compliance_before': float,
    'compliance_after': float,     # Must: 100%
    'regression_detected': bool    # Must: False
}
```

### Alert Conditions (TG11)

**Warning Alerts (Slack/Email):**
- Overall precision < 80% (10% below target)
- Pattern recall < 60% (10% below target)
- Classification accuracy < 70% (10% below target)
- Test pass rate < 90% (5% below target)

**Critical Alerts (PagerDuty):**
- Semantic compliance < 95% (immediate attention required)
- Execution success rate < 95% (pipeline broken)
- Overall precision < 70% (below baseline - rollback)

### Dashboard (Grafana - TG11)

```
DevMatrix Pipeline Precision Dashboard
├─ Overall Precision (trend over time, 7-day, 30-day)
├─ Phase-by-Phase Breakdown (current values + sparklines)
├─ Pattern Matching Stats (precision, recall, F1, threshold usage)
├─ Classification Accuracy (per-domain breakdown)
├─ DAG Construction Quality (nodes, edges, validation score)
├─ Execution Success Rate (per-phase)
└─ Alerts History (last 24h, 7d, 30d)
```

---

**Document Version**: 1.0
**Created**: 2025-11-20
**Last Updated**: 2025-11-20
**Total Tasks**: 11 task groups, ~50 sub-tasks
**Estimated Duration**: 3-4 weeks (1 FTE)
**Expected Outcome**: 73% → 90%+ overall precision
