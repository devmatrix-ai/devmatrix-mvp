# Precision Metrics Troubleshooting Guide

**Version**: 1.0
**Date**: 2025-11-20
**Audience**: Developers, QA Engineers
**Purpose**: Diagnose and fix low precision metrics in DevMatrix E2E pipeline

---

## Quick Reference

| Symptom | Likely Cause | Quick Fix | Full Solution |
|---------|--------------|-----------|---------------|
| Overall precision < 70% | Multiple issues | See diagnostic flowchart | Address all failing metrics |
| Classification accuracy 0% | No ground truth | Add classification YAML | See Classification Issues |
| Pattern F1 < 60% | Weak pattern database | Clean patterns, adjust thresholds | See Pattern Matching Issues |
| DAG accuracy < 60% | Missing dependencies | Add ground truth edges | See DAG Construction Issues |
| Execution success < 95% | Code generation errors | Check logs, fix templates | See Execution Issues |
| Tests pass rate < 90% | Semantic compliance issues | Review generated code | See Test Failure Issues |

---

## Diagnostic Flowchart

```
Start: Low overall precision (<80%)
│
├─ Check Classification Accuracy
│  ├─ = 0%? → Missing ground truth → Add classification YAML
│  └─ < 80%? → Misclassifications → Review classification logic
│
├─ Check Pattern F1
│  ├─ Precision high, recall low? → Missing patterns → Add patterns or fallback
│  └─ Precision low, recall high? → Too many patterns → Clean pattern database
│
├─ Check DAG Accuracy
│  ├─ < 60%? → Missing edges → Add dependency ground truth
│  └─ 60-80%? → Some edges wrong → Review inference logic
│
├─ Check Execution Success
│  ├─ < 95%? → Code errors → Check execution logs
│  └─ = 100%? → Not the issue → Continue
│
└─ Check Tests Pass Rate
   ├─ < 90%? → Semantic issues → Review generated code
   └─ = 100%? → Not the issue → Continue
```

---

## Classification Issues

### Symptom: Classification Accuracy is 0%

**Diagnosis:**
```bash
# Check if ground truth exists
grep -A 20 "## Classification Ground Truth" tests/e2e/test_specs/your_spec.md

# Expected output: YAML section with classifications
# If empty → ground truth is missing
```

**Root Cause:** No classification ground truth defined in spec file.

**Solution:**

1. **Add classification ground truth to spec**:
```yaml
## Classification Ground Truth

F1_create_product:
  domain: crud
  risk: low
  rationale: Simple CRUD operation

F2_list_products:
  domain: crud
  risk: low
  rationale: Simple read operation
```

2. **Validate format**:
```bash
python -m pytest tests/unit/test_classification_validator.py -v
```

3. **Re-run E2E pipeline**:
```bash
python -m pytest tests/e2e/test_real_e2e_full_pipeline.py -k "your_spec" -v
```

**Expected Result:** Classification accuracy > 80%

---

### Symptom: Classification Accuracy is Low (< 80%)

**Diagnosis:**
```python
# Check which requirements are misclassified
from tests.e2e.precision_metrics import load_classification_ground_truth, validate_classification

ground_truth = load_classification_ground_truth("tests/e2e/test_specs/your_spec.md")

# Compare actual vs expected
for req_id, expected in ground_truth.items():
    actual = get_actual_classification(req_id)  # From pipeline output
    if not validate_classification(actual, expected):
        print(f"❌ Misclassified: {req_id}")
        print(f"   Expected: {expected}")
        print(f"   Actual: {actual}")
```

**Root Causes:**
1. Ground truth classifications are incorrect
2. RequirementsClassifier logic is wrong
3. Requirement IDs don't match

**Solutions:**

**1. Fix Ground Truth:**
```yaml
# Review using classification decision tree
# Update misclassified requirements

F8_create_cart:
  domain: workflow  # Was: crud (WRONG)
  risk: medium      # Was: low (WRONG)
  rationale: |
    Initiates shopping cart workflow, not simple CRUD.
    Creates Cart and establishes Customer relationship.
```

**2. Check Requirement IDs:**
```python
# IDs must match EXACTLY
# Ground truth: "F1_create_product"
# Pipeline: "F1_create_product"
# NOT: "F1", "create_product", "F1_CREATE_PRODUCT"
```

**3. Debug Classifier Logic:**
```python
# File: src/services/requirements_classifier.py
# Add logging to see classification decisions

logger.debug(f"Classifying {req.id}:")
logger.debug(f"  → domain: {domain} (reason: {reason})")
logger.debug(f"  → risk: {risk} (reason: {risk_reason})")
```

**Expected Result:** Classification accuracy > 80%

---

## Pattern Matching Issues

### Symptom: Pattern F1-Score is Low (< 60%)

**Diagnosis:**
```python
# Check precision vs recall breakdown
precision = patterns_correct / (patterns_correct + patterns_incorrect)
recall = patterns_correct / (patterns_correct + patterns_missed)

print(f"Pattern Precision: {precision:.1%}")
print(f"Pattern Recall: {recall:.1%}")

# High precision, low recall → Missing patterns (recall problem)
# Low precision, high recall → Too many wrong patterns (precision problem)
```

**Root Cause 1: Low Recall (patterns_missed is high)**

**Problem:** Pattern matcher is too strict, missing valid patterns.

**Solutions:**

1. **Lower similarity thresholds** (⚠️ Use Task Group 4):
```python
# File: src/services/pattern_matching/matcher.py

# Before:
SIMILARITY_THRESHOLD = 0.85  # Too strict

# After (adaptive thresholds):
SIMILARITY_THRESHOLDS = {
    'crud': 0.75,      # Lower for simple patterns
    'workflow': 0.80,
    'payment': 0.85,   # Higher for complex patterns
}
```

2. **Add keyword fallback** (⚠️ Use Task Group 5):
```python
# When embedding matching finds < 3 patterns, use keyword fallback
def match_with_fallback(self, req: Requirement) -> List[Pattern]:
    matches = self._match_by_embedding(req)
    if len(matches) < 3:
        keyword_matches = self._match_by_keywords(req)
        matches.extend(keyword_matches)
    return matches[:5]
```

3. **Enrich pattern database**:
```bash
# Add missing patterns for your domain
python scripts/add_pattern.py \
    --name "crud_create" \
    --purpose "Create new entity" \
    --framework "fastapi" \
    --code "..." \
    --tags "crud,create,post"
```

**Expected Result:** Pattern recall > 70%

---

**Root Cause 2: Low Precision (patterns_incorrect is high)**

**Problem:** Pattern matcher is too lenient, matching irrelevant patterns.

**Solutions:**

1. **Raise similarity thresholds**:
```python
# File: src/services/pattern_matching/matcher.py

SIMILARITY_THRESHOLDS = {
    'crud': 0.80,      # Raise if too many false positives
    'workflow': 0.85,
    'payment': 0.90,   # Much stricter for complex patterns
}
```

2. **Clean pattern database**:
```bash
# Remove patterns with empty purpose
python scripts/audit_patterns.py

# Expected output:
# Removed (empty purpose): 9983
# Removed (wrong framework): 15
# Remaining: 2
```

3. **Filter by framework**:
```python
# Only match patterns for current framework
patterns = pattern_bank.load_all(framework="fastapi")  # Not "nextjs", "react", etc.
```

**Expected Result:** Pattern precision > 80%

---

### Symptom: Pattern Database Mostly Empty

**Diagnosis:**
```bash
# Check pattern count
python -c "from src.storage.pattern_bank import PatternBank; pb = PatternBank(); print(f'Patterns: {len(pb.load_all())}')"

# Expected: 50-200 patterns
# If < 10 → database is depleted
```

**Root Cause:** Pattern audit script removed too many patterns (99.83% had empty purpose).

**Solution:**

**⚠️ CRITICAL: DO NOT run cleanup until upstream issue is fixed!**

See `claudedocs/PATTERN_AUDIT_REPORT.md` for details.

**Temporary workaround:**
```bash
# Restore from backup
cp backups/patterns_backup.json qdrant_storage/collections/patterns/data.json

# Use keyword fallback (Task Group 5) instead of cleaning patterns
```

**Long-term fix:**
- Fix pattern storage to preserve `purpose` field
- Re-generate pattern database with valid metadata
- Run audit script only after fix is verified

---

## DAG Construction Issues

### Symptom: DAG Accuracy is Low (< 60%)

**Diagnosis:**
```python
# Check which edges are missing
from tests.e2e.precision_metrics import load_dag_ground_truth

ground_truth = load_dag_ground_truth("tests/e2e/test_specs/your_spec.md")

expected_edges = set(ground_truth['edges'])
actual_edges = set(get_actual_dag_edges())  # From pipeline output

missing_edges = expected_edges - actual_edges
extra_edges = actual_edges - expected_edges

print(f"Missing edges ({len(missing_edges)}):")
for from_node, to_node in missing_edges:
    print(f"  - {from_node} → {to_node}")

print(f"Extra edges ({len(extra_edges)}):")
for from_node, to_node in extra_edges:
    print(f"  - {from_node} → {to_node}")
```

**Root Cause 1: Missing Ground Truth**

**Solution:**

Add DAG ground truth to spec:
```yaml
## Expected Dependency Graph (Ground Truth)

nodes: 10
  - create_product
  - list_products
  # ... all nodes

edges: 12
  - create_product → list_products
    rationale: Must create before listing

  - create_product → add_to_cart
    rationale: Products must exist before adding to cart

  # ... all edges with rationale
```

**Root Cause 2: Dependency Inference is Weak**

**Problem:** Pipeline is not inferring CRUD dependencies.

**Solution (⚠️ Requires Task Group 7):**

Implement enhanced dependency inference:
```python
# File: src/planning/multi_pass_planner.py

def infer_dependencies_enhanced(self, requirements):
    edges = []

    # Strategy 1: Explicit dependencies
    edges.extend(self._explicit_dependencies(requirements))

    # Strategy 2: CRUD dependencies (NEW)
    edges.extend(self._crud_dependencies(requirements))

    # Strategy 3: Workflow dependencies (NEW)
    edges.extend(self._workflow_dependencies(requirements))

    return self._validate_edges(edges)
```

**Temporary workaround:**

Add explicit dependencies in spec:
```yaml
## Requirements

F9_add_to_cart:
  depends_on: [F8_create_cart, F1_create_product]

F13_checkout_cart:
  depends_on: [F9_add_to_cart]
```

**Expected Result:** DAG accuracy > 80%

---

### Symptom: Cycle Detected in DAG

**Diagnosis:**
```bash
# Check DAG construction logs
grep -i "cycle" logs/e2e_pipeline.log

# Expected output:
# ERROR: Cycle detected: A → B → C → A
```

**Root Cause:** Circular dependencies in ground truth or inference logic.

**Solution:**

1. **Review ground truth edges**:
```yaml
# BAD: Circular dependency
- create_cart → add_to_cart
- add_to_cart → create_cart  # ❌ CYCLE

# GOOD: Acyclic
- create_cart → add_to_cart
- add_to_cart → checkout_cart  # ✅ NO CYCLE
```

2. **Validate with topological sort**:
```python
import networkx as nx

# Build graph from edges
G = nx.DiGraph()
for from_node, to_node in edges:
    G.add_edge(from_node, to_node)

# Check for cycles
if not nx.is_directed_acyclic_graph(G):
    cycles = list(nx.simple_cycles(G))
    print(f"Cycles detected: {cycles}")
```

3. **Fix workflow logic**:
```yaml
# Workflow should be sequential, not circular
- create_cart → add_to_cart → checkout_cart → payment  # ✅ Sequential
```

**Expected Result:** DAG construction succeeds with no cycles

---

## Execution Issues

### Symptom: Execution Success < 95%

**Diagnosis:**
```bash
# Check execution logs for failures
grep -i "error\|exception\|failed" logs/execution.log

# Look for patterns:
# - Import errors → Missing dependencies
# - Runtime errors → Code generation bugs
# - Timeout errors → Infinite loops or slow code
```

**Root Cause 1: Import Errors**

**Problem:**
```python
ImportError: No module named 'fastapi'
```

**Solution:**
```bash
# Install missing dependencies
pip install -r requirements.txt

# Or install specific package
pip install fastapi
```

**Root Cause 2: Runtime Errors**

**Problem:**
```python
AttributeError: 'NoneType' object has no attribute 'id'
```

**Solution:**

1. Review generated code in `tests/e2e/generated_apps/<app_name>/`
2. Check for null pointer errors, type mismatches
3. Add defensive programming:
```python
# BAD:
product = get_product(id)
return product.name  # ❌ Fails if product is None

# GOOD:
product = get_product(id)
if not product:
    raise HTTPException(status_code=404, detail="Product not found")
return product.name  # ✅ Safe
```

**Root Cause 3: Code Generation Templates**

**Problem:** Code generation templates have bugs.

**Solution:**
```bash
# Review templates
ls src/codegen/templates/

# Check for stub implementations
grep -r "raise NotImplementedError" tests/e2e/generated_apps/

# Fix templates or implement missing methods
```

**Expected Result:** Execution success = 100%

---

## Test Failure Issues

### Symptom: Tests Pass Rate < 90%

**Diagnosis:**
```bash
# Run tests with verbose output
python -m pytest tests/e2e/generated_apps/<app_name>/tests/ -v

# Check failure reasons:
# - Assertion errors → Semantic compliance issues
# - Import errors → Missing test dependencies
# - Timeout errors → Tests too slow
```

**Root Cause 1: Semantic Compliance Issues**

**Problem:**
```python
# Test expects:
assert response.json() == {"name": "Product 1", "price": 100}

# But generated code returns:
{"name": "Product 1", "price": "100"}  # ❌ price is string, not int
```

**Solution:**

1. Review `ComplianceValidator` report:
```bash
grep -A 30 "Compliance Report" logs/validation.log

# Check:
# - Entities: Are all expected entities implemented?
# - Endpoints: Are all expected endpoints present?
# - Validations: Is business logic correct?
```

2. Fix semantic issues in generated code
3. Re-run validation

**Root Cause 2: Missing Validations**

**Problem:** Generated code doesn't validate inputs.

**Solution:**

Add validation to generated code:
```python
# BAD: No validation
@app.post("/products")
def create_product(product: ProductCreate):
    return save_product(product)  # ❌ No validation

# GOOD: With validation
@app.post("/products")
def create_product(product: ProductCreate):
    if product.price < 0:
        raise HTTPException(status_code=400, detail="Price must be positive")
    if not product.name:
        raise HTTPException(status_code=400, detail="Name is required")
    return save_product(product)  # ✅ Validated
```

**Expected Result:** Tests pass rate > 95%

---

## Common Error Messages

### "Ground truth not found for spec"

**Meaning:** Spec file doesn't have classification or DAG ground truth.

**Fix:**
```yaml
# Add to spec file:
## Classification Ground Truth
<your classifications>

## Expected Dependency Graph (Ground Truth)
<your DAG structure>
```

### "Requirement ID mismatch"

**Meaning:** Ground truth uses different IDs than spec.

**Fix:**
```yaml
# Spec has: F1: Create Product
# Ground truth should use: F1_create_product
# NOT: F1, create_product, F1_CREATE_PRODUCT
```

### "Classification validation failed"

**Meaning:** Actual classification doesn't match expected.

**Fix:**
```python
# Check actual vs expected:
print(f"Expected domain: {expected['domain']}")
print(f"Actual domain: {actual['domain']}")

# Update ground truth or fix classifier
```

### "DAG cycle detected"

**Meaning:** Dependency graph has circular reference.

**Fix:**
```yaml
# Find the cycle:
# A → B → C → A

# Break it by removing one edge:
# A → B → C (no edge back to A)
```

### "Pattern matching timeout"

**Meaning:** Pattern matching is taking too long.

**Fix:**
```python
# Reduce pattern database size
python scripts/audit_patterns.py

# Or increase timeout
PATTERN_MATCHING_TIMEOUT = 60  # seconds
```

---

## Performance Tuning

### Slow Pattern Matching

**Symptoms:**
- Pattern matching takes > 10 seconds
- High CPU usage during embedding calculation

**Solutions:**

1. **Reduce pattern database size**:
```bash
# Remove irrelevant patterns
python scripts/audit_patterns.py --framework fastapi
```

2. **Cache embeddings**:
```python
# File: src/services/pattern_matching/matcher.py

@lru_cache(maxsize=1000)
def get_embedding(text: str):
    return self.embedding_model.encode(text)
```

3. **Parallelize pattern matching**:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    matches = list(executor.map(match_pattern, requirements))
```

---

### Slow DAG Construction

**Symptoms:**
- DAG construction takes > 30 seconds
- Many unnecessary edges calculated

**Solutions:**

1. **Limit dependency strategies**:
```python
# Only use necessary strategies
edges = []
edges.extend(self._explicit_dependencies(reqs))  # Always
edges.extend(self._crud_dependencies(reqs))      # If needed
# Skip workflow inference if not needed
```

2. **Cache entity grouping**:
```python
@lru_cache(maxsize=100)
def _group_by_entity(requirements_tuple):
    # Expensive operation, cache results
    pass
```

---

## Preventive Measures

### 1. Ground Truth Validation in CI/CD

```yaml
# .github/workflows/ci.yml

- name: Validate Ground Truth
  run: |
    python -m pytest tests/unit/test_classification_validator.py -v
    python -m pytest tests/unit/test_dag_ground_truth.py -v
```

### 2. Metrics Monitoring

```bash
# Add alerts for low precision
if [ $(calculate_precision) -lt 80 ]; then
    send_alert "Precision dropped below 80%"
fi
```

### 3. Regression Testing

```bash
# Run E2E on all specs before merge
python -m pytest tests/e2e/test_real_e2e_full_pipeline.py -v

# Compare metrics with baseline
python scripts/compare_metrics.py \
    --baseline metrics/baseline.json \
    --current metrics/current.json
```

---

## Getting Help

### Debugging Checklist

Before asking for help, complete this checklist:

- [ ] Read error message carefully
- [ ] Check this troubleshooting guide
- [ ] Review relevant documentation (CLASSIFICATION.md, DAG_CONSTRUCTION.md, METRICS_GUIDE.md)
- [ ] Run unit tests for affected components
- [ ] Check logs for detailed error information
- [ ] Verify ground truth format and IDs
- [ ] Try solutions from this guide

### Reporting Issues

When reporting precision issues, include:

1. **Spec name**: Which test specification is affected?
2. **Metrics output**: Full metrics report from pipeline
3. **Error messages**: Complete error logs (not screenshots)
4. **Ground truth**: Show your classification and DAG ground truth
5. **Steps to reproduce**: Exact commands to reproduce issue
6. **Expected vs actual**: What you expected vs what happened

**Example:**
```
Spec: ecommerce_api_simple.md
Issue: Classification accuracy is 52%

Metrics:
  Overall Precision: 65.3%
  Classification Accuracy: 52.4% (9/17 correct)

Ground truth:
  [paste classification YAML]

Steps to reproduce:
  1. python -m pytest tests/e2e/test_real_e2e_full_pipeline.py -k "ecommerce" -v
  2. Check metrics output

Expected: 80%+ classification accuracy
Actual: 52.4% classification accuracy

Error logs:
  [paste relevant logs]
```

---

## Related Documentation

- **Classification Guide**: [CLASSIFICATION.md](./CLASSIFICATION.md) - Classification methodology
- **DAG Construction**: [DAG_CONSTRUCTION.md](./DAG_CONSTRUCTION.md) - Dependency inference
- **Metrics Guide**: [METRICS_GUIDE.md](./METRICS_GUIDE.md) - Precision calculation
- **Ground Truth Guide**: [GROUND_TRUTH_GUIDE.md](./GROUND_TRUTH_GUIDE.md) - How to define ground truth

---

**End of Guide**

If your issue is not covered here, check [Github Issues](https://github.com/your-repo/issues) or contact the DevMatrix team.
