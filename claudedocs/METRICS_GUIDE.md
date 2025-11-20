# DevMatrix Pipeline Metrics Guide

**Version**: 1.0
**Date**: 2025-11-20
**Status**: ✅ Implemented
**Related**: DevMatrix Pipeline Precision Improvement

---

## Overview

This guide explains how the DevMatrix E2E pipeline calculates overall precision and individual phase metrics. Understanding these metrics is essential for:

- Evaluating pipeline quality
- Identifying improvement opportunities
- Monitoring production performance
- Debugging precision issues

---

## Overall Precision Calculation

### Formula

Overall precision is calculated as a **weighted average** across all pipeline phases:

```python
overall_precision = sum(scores[metric] * weights[metric] for metric in weights)
```

### Weights Distribution

| Metric | Weight | Rationale |
|--------|--------|-----------|
| **accuracy** | 20% | Overall pipeline success rate - critical baseline |
| **pattern_f1** | 15% | Pattern matching quality - impacts code quality |
| **classification** | 15% | Requirement categorization - guides planning |
| **dag** | 10% | Dependency accuracy - ensures correct execution order |
| **atomization** | 10% | Task granularity - affects execution efficiency |
| **execution** | 20% | Code execution success - end-to-end validation |
| **tests** | 10% | Test coverage and pass rate - quality assurance |
| **Total** | 100% | |

### Example Calculation

From `ecommerce_api_simple` spec:

```python
# Individual metric scores
scores = {
    'accuracy': 1.00,         # 100% operations successful
    'pattern_f1': 0.593,      # 59.3% pattern F1-score
    'classification': 0.00,   # 0% (not tracked - baseline)
    'dag': 0.576,             # 57.6% DAG accuracy
    'atomization': 0.90,      # 90% atoms well-sized
    'execution': 1.00,        # 100% execution success
    'tests': 0.94             # 94% tests passed
}

# Weights
weights = {
    'accuracy': 0.20,
    'pattern_f1': 0.15,
    'classification': 0.15,
    'dag': 0.10,
    'atomization': 0.10,
    'execution': 0.20,
    'tests': 0.10
}

# Calculation
overall_precision = (
    (1.00 * 0.20) +    # accuracy: 0.20
    (0.593 * 0.15) +   # pattern_f1: 0.089
    (0.00 * 0.15) +    # classification: 0.00
    (0.576 * 0.10) +   # dag: 0.058
    (0.90 * 0.10) +    # atomization: 0.09
    (1.00 * 0.20) +    # execution: 0.20
    (0.94 * 0.10)      # tests: 0.094
)

overall_precision = 0.731 = 73.1%
```

---

## Individual Metrics Explained

### 1. Accuracy (20% weight)

**Definition**: Percentage of pipeline operations that complete successfully.

**Calculation**:
```python
accuracy = successful_operations / total_operations
```

**Example**:
```python
total_operations = 100      # Total pipeline steps
successful_operations = 100 # All succeeded
accuracy = 100 / 100 = 1.00 (100%)
```

**Interpretation**:
- **100%**: Perfect - all operations successful
- **95-99%**: Good - few failures, investigate errors
- **<95%**: Poor - systematic issues, requires attention

**Target**: Maintain 100%

---

### 2. Pattern F1-Score (15% weight)

**Definition**: Harmonic mean of pattern matching precision and recall.

**Calculation**:
```python
precision = patterns_correct / (patterns_correct + patterns_incorrect)
recall = patterns_correct / (patterns_correct + patterns_missed)
f1_score = 2 * (precision * recall) / (precision + recall)
```

**Example**:
```python
patterns_expected = 20      # Ground truth patterns
patterns_correct = 16       # True positives
patterns_incorrect = 4      # False positives (wrong patterns)
patterns_missed = 4         # False negatives (missed patterns)

precision = 16 / (16 + 4) = 0.80 (80%)
recall = 16 / (16 + 4) = 0.80 (80%)
f1_score = 2 * (0.80 * 0.80) / (0.80 + 0.80) = 0.80 (80%)
```

**Interpretation**:
- **>80%**: Excellent - patterns matched accurately
- **60-80%**: Good - room for improvement
- **<60%**: Poor - pattern matching needs work

**Target**: 75%+ (stretch: 80%+)

**Improvement Strategies**:
- Clean pattern database (remove empty patterns)
- Use adaptive thresholds by domain
- Implement keyword fallback for low matches

---

### 3. Classification Accuracy (15% weight)

**Definition**: Percentage of requirements correctly classified by domain and risk.

**Calculation**:
```python
classification_accuracy = classifications_correct / classifications_total
```

**Example**:
```python
classifications_total = 17       # Total requirements
classifications_correct = 15     # Domain AND risk match ground truth
classifications_incorrect = 2    # Misclassified

classification_accuracy = 15 / 17 = 0.882 (88.2%)
```

**Interpretation**:
- **>90%**: Excellent - classification very accurate
- **80-90%**: Good - meets target
- **<80%**: Poor - needs ground truth refinement

**Target**: 80%+ (stretch: 90%+)

**Improvement Strategies**:
- Define comprehensive ground truth
- Refine classification decision tree
- Add domain-specific keywords

---

### 4. DAG Accuracy (10% weight)

**Definition**: Percentage of dependency graph nodes and edges matching expected structure.

**Calculation**:
```python
dag_accuracy = (correct_nodes + correct_edges) / (expected_nodes + expected_edges)
```

**Example**:
```python
# Ground truth
expected_nodes = 10          # Expected task nodes
expected_edges = 12          # Expected dependency edges

# Actual DAG
dag_nodes = 10               # Nodes created
dag_edges = 10               # Edges created

# Validation
correct_nodes = 10           # All nodes match
correct_edges = 7            # 7/12 edges match

dag_accuracy = (10 + 7) / (10 + 12) = 17 / 22 = 0.773 (77.3%)
```

**Interpretation**:
- **>85%**: Excellent - DAG structure very accurate
- **80-85%**: Good - meets target
- **<80%**: Poor - dependency inference needs improvement

**Target**: 80%+ (stretch: 85%+)

**Improvement Strategies**:
- Implement CRUD dependency inference
- Add workflow pattern detection
- Validate execution order

---

### 5. Atomization Quality (10% weight)

**Definition**: Percentage of generated atoms (tasks) that are properly sized.

**Calculation**:
```python
atomization_quality = atoms_valid / atoms_generated

# Where atoms_valid = atoms that are:
# - Not too large (>50 LOC)
# - Not too small (<5 LOC)
# - Single responsibility
# - Executable independently
```

**Example**:
```python
atoms_generated = 50         # Total atoms created
atoms_valid = 45             # Well-sized atoms
atoms_too_large = 3          # >50 LOC
atoms_too_small = 2          # <5 LOC

atomization_quality = 45 / 50 = 0.90 (90%)
```

**Interpretation**:
- **>90%**: Excellent - atoms well-sized
- **80-90%**: Good - acceptable granularity
- **<80%**: Poor - atomization needs refinement

**Target**: 90%+

**Improvement Strategies**:
- Adjust LOC thresholds (currently 5-50 LOC)
- Split large atoms into smaller units
- Merge trivial atoms

---

### 6. Execution Success (20% weight)

**Definition**: Percentage of atoms that execute successfully (possibly after recovery).

**Calculation**:
```python
execution_success = atoms_succeeded / atoms_executed

# Where atoms_succeeded includes:
# - Atoms that succeeded first try
# - Atoms that succeeded after recovery
```

**Example**:
```python
atoms_executed = 50          # Total atoms attempted
atoms_succeeded = 50         # All eventually succeeded
atoms_failed_first_try = 5   # Failed initially but recovered
atoms_permanently_failed = 0 # Could not be recovered

execution_success = 50 / 50 = 1.00 (100%)
```

**Interpretation**:
- **100%**: Perfect - all atoms execute successfully
- **95-99%**: Good - minor issues, mostly recoverable
- **<95%**: Poor - systematic execution problems

**Target**: Maintain 100%

**Critical Metric**: Execution success should NEVER drop below 95%. If it does, investigate immediately.

---

### 7. Test Pass Rate (10% weight)

**Definition**: Percentage of tests that pass after code generation.

**Calculation**:
```python
test_pass_rate = tests_passed / tests_executed
```

**Example**:
```python
tests_executed = 50          # Total tests run
tests_passed = 47            # Tests that passed
tests_failed = 3             # Tests that failed
tests_skipped = 0            # Tests skipped

test_pass_rate = 47 / 50 = 0.94 (94%)
```

**Interpretation**:
- **>95%**: Excellent - high code quality
- **90-95%**: Good - acceptable quality
- **<90%**: Poor - code quality issues

**Target**: 95%+

---

## Metrics Reporting

### Console Output Format

```
========================================
DevMatrix E2E Pipeline Metrics
========================================

Overall Precision: 73.1%

Phase-by-Phase Breakdown:
  ✅ Accuracy:           100.0% (20% weight → 20.0%)
  ⚠️  Pattern F1:         59.3% (15% weight →  8.9%)
  ❌ Classification:      0.0% (15% weight →  0.0%)
  ⚠️  DAG Accuracy:       57.6% (10% weight →  5.8%)
  ✅ Atomization:         90.0% (10% weight →  9.0%)
  ✅ Execution:          100.0% (20% weight → 20.0%)
  ✅ Tests:               94.0% (10% weight →  9.4%)

Improvement Opportunities:
  🔴 HIGH PRIORITY: Classification (0% → 80% target = +12% overall)
  🟡 MEDIUM: Pattern F1 (59% → 75% target = +2.4% overall)
  🟡 MEDIUM: DAG Accuracy (58% → 80% target = +2.2% overall)

Estimated Overall Precision After Improvements: 90.6%
```

### JSON Output Format

```json
{
  "overall_precision": 0.731,
  "metrics": {
    "accuracy": {"score": 1.00, "weight": 0.20, "contribution": 0.200},
    "pattern_f1": {"score": 0.593, "weight": 0.15, "contribution": 0.089},
    "classification": {"score": 0.00, "weight": 0.15, "contribution": 0.000},
    "dag": {"score": 0.576, "weight": 0.10, "contribution": 0.058},
    "atomization": {"score": 0.90, "weight": 0.10, "contribution": 0.090},
    "execution": {"score": 1.00, "weight": 0.20, "contribution": 0.200},
    "tests": {"score": 0.94, "weight": 0.10, "contribution": 0.094}
  },
  "improvement_potential": {
    "classification": {"current": 0.00, "target": 0.80, "impact": 0.12},
    "pattern_f1": {"current": 0.593, "target": 0.75, "impact": 0.024},
    "dag": {"current": 0.576, "target": 0.80, "impact": 0.022}
  },
  "projected_precision": 0.906
}
```

---

## Improvement Impact Analysis

### Calculating Impact

To calculate the impact of improving a metric:

```python
impact = (target_score - current_score) * weight

# Example: Classification improvement
current_classification = 0.00
target_classification = 0.80
classification_weight = 0.15

impact = (0.80 - 0.00) * 0.15 = 0.12 = +12% overall precision
```

### Prioritization Matrix

| Metric | Current | Target | Potential Impact | Priority |
|--------|---------|--------|------------------|----------|
| Classification | 0% | 80% | +12.0% | 🔴 HIGH |
| Pattern F1 | 59.3% | 75% | +2.4% | 🟡 MEDIUM |
| DAG Accuracy | 57.6% | 80% | +2.2% | 🟡 MEDIUM |
| Tests | 94% | 95% | +0.1% | 🟢 LOW |

**Total Potential Improvement**: +16.7% (73.1% → 89.8%)

### Improvement Roadmap

**Phase 1: Quick Wins (Week 1)**
- Fix Classification metrics (0% → 80%): **+12% overall**
- Estimated precision after: **85.1%**

**Phase 2: Pattern Matching (Week 2)**
- Improve Pattern F1 (59% → 75%): **+2.4% overall**
- Estimated precision after: **87.5%**

**Phase 3: DAG Construction (Week 3)**
- Improve DAG Accuracy (58% → 80%): **+2.2% overall**
- Estimated precision after: **89.7%**

**Final Target**: **90%+ overall precision**

---

## Metrics Collection

### Code Location

Metrics are collected in:
```
tests/e2e/real_e2e_full_pipeline.py
```

### Metrics Tracker

```python
from tests.e2e.precision_metrics import PrecisionMetrics

precision_tracker = PrecisionMetrics()

# Phase 1: Spec Ingestion
precision_tracker.total_operations += 1
precision_tracker.successful_operations += 1

# Phase 2: Pattern Matching
precision_tracker.patterns_expected = len(expected_patterns)
precision_tracker.patterns_found = len(matched_patterns)
precision_tracker.patterns_correct = count_correct_matches()

# Phase 2: Classification
precision_tracker.classifications_total = len(classified_reqs)
precision_tracker.classifications_correct = count_correct_classifications()

# Phase 5: DAG Construction
precision_tracker.dag_nodes_expected = ground_truth['nodes_count']
precision_tracker.dag_nodes_created = len(dag.nodes)
precision_tracker.dag_edges_expected = ground_truth['edges_count']
precision_tracker.dag_edges_created = len(dag.edges)

# Phase 6: Atomization
precision_tracker.atoms_generated = len(atoms)
precision_tracker.atoms_valid = count_valid_atoms()

# Phase 7: Execution
precision_tracker.atoms_executed = len(executed_atoms)
precision_tracker.atoms_succeeded = count_successful_atoms()

# Phase 9: Testing
precision_tracker.tests_executed = len(test_results)
precision_tracker.tests_passed = count_passed_tests()

# Final Report
print(precision_tracker.generate_report())
```

---

## Interpreting Results

### Healthy Pipeline

```
Overall Precision: 92.3%

✅ All metrics above targets
✅ No critical failures
✅ Consistent performance across specs
```

**Action**: Monitor for regressions

---

### Pipeline Needs Improvement

```
Overall Precision: 73.1%

⚠️ Classification: 0% (target: 80%)
⚠️ Pattern F1: 59.3% (target: 75%)
⚠️ DAG Accuracy: 57.6% (target: 80%)
```

**Action**: Follow improvement roadmap

---

### Pipeline Has Critical Issues

```
Overall Precision: 45.2%

❌ Execution: 67% (target: 100%)
❌ Tests: 42% (target: 95%)
❌ Accuracy: 55% (target: 100%)
```

**Action**: Stop development, debug immediately

---

## Monitoring and Alerting

### Alert Thresholds

**Warning Alerts** (🟡):
- Overall precision < 80%
- Pattern F1 < 60%
- Classification < 70%
- DAG accuracy < 70%

**Critical Alerts** (🔴):
- Overall precision < 70%
- Execution success < 95%
- Accuracy < 95%
- Tests pass rate < 90%

### Dashboards

**Grafana Dashboard Panels**:
1. Overall Precision (trend over time)
2. Phase-by-Phase Breakdown (current values)
3. Pattern Matching Stats (precision, recall, F1)
4. Classification Accuracy (per-domain)
5. DAG Construction Quality (nodes, edges)
6. Execution Success Rate (per-phase)
7. Test Pass Rate (over time)

---

## Common Questions

### Q: Why are weights not equal?

**A**: Weights reflect the relative importance of each phase:
- **Execution (20%)** and **Accuracy (20%)** are highest because they indicate end-to-end success
- **Pattern F1 (15%)** and **Classification (15%)** guide code quality
- **Tests (10%)**, **DAG (10%)**, **Atomization (10%)** are supporting metrics

### Q: Can I change the weights?

**A**: Yes, but:
- Weights must sum to 1.0 (100%)
- Changes affect historical comparisons
- Document rationale for changes
- Use consistent weights across specs

### Q: What if I don't have ground truth?

**A**:
- Metrics without ground truth default to their current values
- Classification and DAG fall back to assumed correctness
- Define ground truth incrementally as specs mature

### Q: How often should metrics be reviewed?

**A**:
- **Per PR**: Check for regressions
- **Weekly**: Review trends and identify issues
- **Monthly**: Analyze improvement opportunities
- **Quarterly**: Adjust targets and priorities

---

## Related Documentation

- **Classification Guide**: [CLASSIFICATION.md](./CLASSIFICATION.md) - Classification ground truth
- **DAG Construction**: [DAG_CONSTRUCTION.md](./DAG_CONSTRUCTION.md) - DAG ground truth
- **Ground Truth Guide**: [GROUND_TRUTH_GUIDE.md](./GROUND_TRUTH_GUIDE.md) - How to define ground truth
- **Troubleshooting**: [PRECISION_TROUBLESHOOTING.md](./PRECISION_TROUBLESHOOTING.md) - Debugging metrics

---

**End of Document**
