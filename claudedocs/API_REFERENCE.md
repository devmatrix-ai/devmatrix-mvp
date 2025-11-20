# DevMatrix Precision Metrics - API Reference

**Version**: 1.0
**Date**: 2025-11-20
**Status**: ✅ Implemented (Task Groups 1, 2, 6)
**Module**: `tests/e2e/precision_metrics.py`, `src/validation/compliance_validator.py`

---

## Overview

This document provides API reference for new methods added during the DevMatrix Pipeline Precision Improvement project (Task Groups 1, 2, 6).

---

## Classification Validation

### `validate_classification()`

Validates if a requirement's classification matches the expected ground truth.

**Location**: `tests/e2e/precision_metrics.py`

**Signature**:
```python
def validate_classification(
    actual: Dict[str, Any],
    expected: Dict[str, Any]
) -> bool
```

**Parameters**:
- `actual` (Dict[str, Any]): Actual classification from RequirementsClassifier
  - Required keys: `domain`, `risk`
  - Example: `{"domain": "crud", "risk": "low"}`
- `expected` (Dict[str, Any]): Expected classification from ground truth
  - Required keys: `domain`, `risk`
  - Example: `{"domain": "crud", "risk": "low"}`

**Returns**:
- `bool`: `True` if both domain and risk match, `False` otherwise
- Returns `True` if `expected` is `None` or empty (graceful degradation)

**Examples**:
```python
# Example 1: Matching classification
actual = {"domain": "crud", "risk": "low"}
expected = {"domain": "crud", "risk": "low"}
result = validate_classification(actual, expected)
# Returns: True

# Example 2: Domain mismatch
actual = {"domain": "workflow", "risk": "medium"}
expected = {"domain": "crud", "risk": "low"}
result = validate_classification(actual, expected)
# Returns: False

# Example 3: Risk mismatch
actual = {"domain": "crud", "risk": "medium"}
expected = {"domain": "crud", "risk": "low"}
result = validate_classification(actual, expected)
# Returns: False

# Example 4: No ground truth (graceful handling)
actual = {"domain": "crud", "risk": "low"}
expected = None
result = validate_classification(actual, expected)
# Returns: True
```

**Usage in Pipeline**:
```python
# File: tests/e2e/real_e2e_full_pipeline.py (Phase 2)

from tests.e2e.precision_metrics import validate_classification, load_classification_ground_truth

# Load ground truth
ground_truth = load_classification_ground_truth(spec_path)

# Validate each requirement
for req in classified_reqs:
    expected = ground_truth.get(req.id, {})
    is_correct = validate_classification(req.classification, expected)
    if is_correct:
        precision_tracker.classifications_correct += 1
    else:
        precision_tracker.classifications_incorrect += 1
```

---

### `load_classification_ground_truth()`

Loads classification ground truth from a specification file.

**Location**: `tests/e2e/precision_metrics.py`

**Signature**:
```python
def load_classification_ground_truth(spec_path: str) -> Dict[str, Dict[str, str]]
```

**Parameters**:
- `spec_path` (str): Path to specification markdown file
  - Example: `"tests/e2e/test_specs/ecommerce_api_simple.md"`

**Returns**:
- `Dict[str, Dict[str, str]]`: Dictionary mapping requirement IDs to classification metadata
  - Example: `{"F1_create_product": {"domain": "crud", "risk": "low", "rationale": "..."}}`
  - Returns empty `{}` if no ground truth section found

**Ground Truth Format** (in spec file):
```yaml
## Classification Ground Truth

F1_create_product:
  domain: crud
  risk: low
  rationale: Simple CRUD operation creating Product entity

F8_create_cart:
  domain: workflow
  risk: medium
  rationale: Initiates shopping cart workflow
```

**Examples**:
```python
# Example 1: Load ground truth
ground_truth = load_classification_ground_truth(
    "tests/e2e/test_specs/ecommerce_api_simple.md"
)

# Returns:
# {
#     "F1_create_product": {
#         "domain": "crud",
#         "risk": "low",
#         "rationale": "Simple CRUD operation..."
#     },
#     "F8_create_cart": {
#         "domain": "workflow",
#         "risk": "medium",
#         "rationale": "Initiates shopping cart workflow..."
#     },
#     ...
# }

# Example 2: Access specific requirement
f1_classification = ground_truth.get("F1_create_product", {})
domain = f1_classification.get("domain")  # "crud"
risk = f1_classification.get("risk")      # "low"

# Example 3: No ground truth (file doesn't exist or no section)
ground_truth = load_classification_ground_truth("non_existent.md")
# Returns: {}
```

**Error Handling**:
- Returns empty `{}` if file doesn't exist
- Returns empty `{}` if no "## Classification Ground Truth" section found
- Skips malformed entries and continues parsing
- Logs warnings for parsing errors

**Usage in Pipeline**:
```python
# Load once at start of Phase 2
ground_truth = load_classification_ground_truth(spec_path)

# Use throughout classification validation
for req in classified_reqs:
    expected = ground_truth.get(req.id, {})
    is_correct = validate_classification(req.classification, expected)
```

---

## DAG Validation

### `load_dag_ground_truth()`

Loads DAG ground truth (nodes and edges) from a specification file.

**Location**: `tests/e2e/precision_metrics.py`

**Signature**:
```python
def load_dag_ground_truth(spec_path: str) -> Dict[str, Any]
```

**Parameters**:
- `spec_path` (str): Path to specification markdown file
  - Example: `"tests/e2e/test_specs/ecommerce_api_simple.md"`

**Returns**:
- `Dict[str, Any]`: Dictionary containing expected DAG structure
  ```python
  {
      'nodes': List[str],              # Expected node names
      'edges': List[Tuple[str, str]],  # Expected (from, to) edges
      'nodes_count': int,              # Expected node count
      'edges_count': int               # Expected edge count
  }
  ```
  - Returns default values if no ground truth section found:
    ```python
    {
        'nodes': [],
        'edges': [],
        'nodes_count': 0,
        'edges_count': 0
    }
    ```

**Ground Truth Format** (in spec file):
```yaml
## Expected Dependency Graph (Ground Truth)

nodes: 10
  - create_product
  - list_products
  - create_cart
  - add_to_cart
  # ... more nodes

edges: 12
  - create_product → list_products
    rationale: Must create before listing

  - create_cart → add_to_cart
    rationale: Cart must exist before adding items

  # ... more edges
```

**Examples**:
```python
# Example 1: Load DAG ground truth
ground_truth = load_dag_ground_truth(
    "tests/e2e/test_specs/ecommerce_api_simple.md"
)

# Returns:
# {
#     'nodes': ['create_product', 'list_products', 'create_cart', ...],
#     'edges': [
#         ('create_product', 'list_products'),
#         ('create_cart', 'add_to_cart'),
#         ...
#     ],
#     'nodes_count': 10,
#     'edges_count': 12
# }

# Example 2: Access specific elements
expected_nodes = ground_truth['nodes']
expected_edges = ground_truth['edges']
nodes_count = ground_truth['nodes_count']

# Example 3: Check if edge exists
expected_edge = ('create_product', 'list_products')
if expected_edge in ground_truth['edges']:
    print("Edge found in ground truth")

# Example 4: No ground truth
ground_truth = load_dag_ground_truth("spec_without_dag_gt.md")
# Returns: {'nodes': [], 'edges': [], 'nodes_count': 0, 'edges_count': 0}
```

**Edge Parsing**:
The function parses edges in multiple formats:
```yaml
# Format 1: Arrow notation
- create_product → list_products

# Format 2: Text "to"
- create_product to list_products

# Format 3: Depends keyword
- list_products depends on create_product

# All are parsed as: ('create_product', 'list_products')
```

**Error Handling**:
- Returns default values if file doesn't exist
- Returns default values if no "## Expected Dependency Graph" section found
- Skips malformed edges and continues parsing
- Logs warnings for parsing errors

**Usage in Pipeline**:
```python
# File: tests/e2e/real_e2e_full_pipeline.py (Phase 5)

from tests.e2e.precision_metrics import load_dag_ground_truth

# Load DAG ground truth
ground_truth = load_dag_ground_truth(spec_path)

# Calculate DAG accuracy
expected_total = ground_truth['nodes_count'] + ground_truth['edges_count']
actual_total = len(actual_dag.nodes) + len(actual_dag.edges)

# Count matches
correct_nodes = len(set(actual_dag.nodes) & set(ground_truth['nodes']))
correct_edges = len(set(actual_dag.edges) & set(ground_truth['edges']))

dag_accuracy = (correct_nodes + correct_edges) / expected_total
```

---

## Compliance Validation

### `_format_entity_report()` (ComplianceValidator)

Formats entity compliance report with clear categorization of domain entities, schemas, and enums.

**Location**: `src/validation/compliance_validator.py`

**Signature**:
```python
def _format_entity_report(self, report: ComplianceReport) -> str
```

**Parameters**:
- `report` (ComplianceReport): Compliance report with entity information
  - Contains: `entities_implemented`, `entities_expected`

**Returns**:
- `str`: Formatted entity report with categorization

**Categorization Rules**:
1. **Domain Entities**: Entities in `entities_expected` list
2. **Request/Response Schemas**: Entities ending with `Create`, `Update`, `Request`, `Response`
3. **Enums**: Entities ending with `Status`

**Output Format**:
```
📦 Entities (4 required, 4 present):
   ✅ Product, Customer, Cart, Order

   📝 Additional models (best practices):
   - Request/Response schemas: 8 (ProductCreate, CustomerCreate, ...)
   - Enums: 3 (CartStatus, OrderStatus, PaymentStatus)
```

**Examples**:
```python
# Example 1: All entities implemented
report = ComplianceReport(
    overall_compliance=1.0,
    entities_implemented=['Product', 'Customer', 'ProductCreate', 'CartStatus'],
    entities_expected=['Product', 'Customer']
)

formatted = validator._format_entity_report(report)
# Output:
# 📦 Entities (2 required, 2 present):
#    ✅ Product, Customer
#
#    📝 Additional models (best practices):
#    - Request/Response schemas: 1
#    - Enums: 1

# Example 2: Missing entities
report = ComplianceReport(
    overall_compliance=0.5,
    entities_implemented=['Product'],
    entities_expected=['Product', 'Customer']
)

formatted = validator._format_entity_report(report)
# Output:
# 📦 Entities (2 required, 1 present):
#    ⚠️ Product
#    ❌ Missing: Customer
```

**Usage in Validation**:
```python
# File: src/validation/compliance_validator.py

class ComplianceValidator:
    def validate(self, spec: SpecRequirements, code_path: str) -> ComplianceReport:
        # ... validation logic ...

        # Format entity report
        entity_report = self._format_entity_report(report)

        # Include in overall compliance output
        print(entity_report)

        return report
```

---

## PrecisionMetrics Class Updates

### New Fields

**Classification Metrics**:
```python
classifications_total: int = 0       # Total requirements classified
classifications_correct: int = 0     # Classifications matching ground truth
classifications_incorrect: int = 0   # Classifications not matching ground truth
```

**DAG Metrics** (updated to use ground truth):
```python
dag_nodes_expected: int = 0   # From ground truth
dag_edges_expected: int = 0   # From ground truth
dag_nodes_created: int = 0    # From actual DAG
dag_edges_created: int = 0    # From actual DAG
```

### Updated Methods

**`calculate_classification_accuracy()`**:
```python
def calculate_classification_accuracy(self) -> float:
    """
    Calculate classification accuracy

    Returns:
        Accuracy as float 0.0-1.0
        Returns 0.0 if no classifications
    """
    if self.classifications_total == 0:
        return 0.0
    return self.classifications_correct / self.classifications_total
```

**`calculate_dag_accuracy()`** (updated):
```python
def calculate_dag_accuracy(self) -> float:
    """
    Calculate DAG accuracy using ground truth

    Returns:
        Accuracy as float 0.0-1.0
        Calculated as: (correct_nodes + correct_edges) / (expected_nodes + expected_edges)
    """
    if self.dag_nodes_expected == 0 and self.dag_edges_expected == 0:
        return 0.0

    nodes_correct = min(self.dag_nodes_created, self.dag_nodes_expected)
    edges_correct = min(self.dag_edges_created, self.dag_edges_expected)

    total_expected = self.dag_nodes_expected + self.dag_edges_expected
    total_correct = nodes_correct + edges_correct

    return total_correct / total_expected if total_expected > 0 else 0.0
```

**`get_summary()`** (updated):
```python
def get_summary(self) -> Dict[str, Any]:
    """
    Get comprehensive metrics summary

    Returns:
        Dictionary with all metrics including new classification and updated DAG metrics
    """
    return {
        "overall_precision": self.calculate_overall_precision(),

        "classification": {
            "accuracy": self.calculate_classification_accuracy(),
            "correct": self.classifications_correct,
            "incorrect": self.classifications_incorrect,
            "total": self.classifications_total
        },

        "dag_construction": {
            "accuracy": self.calculate_dag_accuracy(),
            "nodes_expected": self.dag_nodes_expected,
            "nodes_created": self.dag_nodes_created,
            "edges_expected": self.dag_edges_expected,
            "edges_created": self.dag_edges_created
        },

        # ... other metrics ...
    }
```

---

## Unit Tests

### Classification Validation Tests

**Location**: `tests/unit/test_classification_validator.py`

**Test Coverage**:
- ✅ Domain matching validation
- ✅ Risk matching validation
- ✅ Domain mismatch detection
- ✅ Risk mismatch detection
- ✅ Missing ground truth handling (graceful degradation)
- ✅ Accuracy calculation correctness
- ✅ Empty classification handling
- ✅ Malformed data handling

**Example Tests**:
```python
def test_classification_validator_exact_match():
    """Test exact match of domain and risk"""
    actual = {"domain": "crud", "risk": "low"}
    expected = {"domain": "crud", "risk": "low"}
    assert validate_classification(actual, expected) is True

def test_classification_validator_domain_mismatch():
    """Test domain mismatch detection"""
    actual = {"domain": "workflow", "risk": "low"}
    expected = {"domain": "crud", "risk": "low"}
    assert validate_classification(actual, expected) is False

def test_classification_validator_no_ground_truth():
    """Test graceful handling when no ground truth"""
    actual = {"domain": "crud", "risk": "low"}
    expected = None
    assert validate_classification(actual, expected) is True
```

### DAG Ground Truth Tests

**Location**: `tests/unit/test_dag_ground_truth.py`

**Test Coverage**:
- ✅ Ground truth parser loads nodes correctly
- ✅ Ground truth parser loads edges correctly
- ✅ Node count validation
- ✅ Edge count validation
- ✅ DAG accuracy calculation correctness
- ✅ Missing edges detection
- ✅ Invalid edge format handling
- ✅ Missing ground truth section handling

**Example Tests**:
```python
def test_dag_ground_truth_parser_nodes():
    """Test that ground truth parser loads nodes correctly"""
    ground_truth = load_dag_ground_truth(
        "tests/e2e/test_specs/ecommerce_api_simple.md"
    )
    assert ground_truth['nodes_count'] == 10
    assert 'create_product' in ground_truth['nodes']
    assert 'checkout_cart' in ground_truth['nodes']

def test_dag_ground_truth_parser_edges():
    """Test that ground truth parser loads edges correctly"""
    ground_truth = load_dag_ground_truth(
        "tests/e2e/test_specs/ecommerce_api_simple.md"
    )
    assert ground_truth['edges_count'] == 12
    assert ('create_product', 'list_products') in ground_truth['edges']
    assert ('create_cart', 'add_to_cart') in ground_truth['edges']
```

---

## Migration Guide

### Updating Existing Specs

**Before** (no ground truth):
```markdown
# Simple Task API Spec

## Functional Requirements

- F1: Create Task - POST /tasks
- F2: List Tasks - GET /tasks
```

**After** (with ground truth):
```markdown
# Simple Task API Spec

## Functional Requirements

- F1: Create Task - POST /tasks
- F2: List Tasks - GET /tasks

## Classification Ground Truth

F1_create_task:
  domain: crud
  risk: low
  rationale: Simple CRUD operation

F2_list_tasks:
  domain: crud
  risk: low
  rationale: Simple read operation

## Expected Dependency Graph (Ground Truth)

nodes: 2
  - create_task
  - list_tasks

edges: 1
  - create_task → list_tasks
    rationale: Must create before listing
```

### Updating Pipeline Code

**Before** (no classification tracking):
```python
# Phase 2: Requirements Analysis
classified_reqs = req_classifier.classify(functional_reqs)
# No metrics tracking
```

**After** (with classification tracking):
```python
# Phase 2: Requirements Analysis
classified_reqs = req_classifier.classify(functional_reqs)

# Track classification metrics
ground_truth = load_classification_ground_truth(spec_path)
precision_tracker.classifications_total = len(classified_reqs)
precision_tracker.classifications_correct = sum(
    1 for req in classified_reqs
    if validate_classification(req.classification, ground_truth.get(req.id, {}))
)
```

---

## Performance Considerations

### Classification Validation
- **Time Complexity**: O(n) where n = number of requirements
- **Space Complexity**: O(n) for ground truth dictionary
- **Recommendation**: Load ground truth once per spec, cache if needed

### DAG Ground Truth Loading
- **Time Complexity**: O(m) where m = file size in lines
- **Space Complexity**: O(e + n) where e = edges, n = nodes
- **Recommendation**: Load once at start of DAG construction phase

### Caching Strategy
```python
# Cache ground truth for repeated use
from functools import lru_cache

@lru_cache(maxsize=100)
def load_classification_ground_truth_cached(spec_path: str):
    return load_classification_ground_truth(spec_path)
```

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-20 | Initial API release with TG1, TG2, TG6 implementations |
| - | - | `validate_classification()` |
| - | - | `load_classification_ground_truth()` |
| - | - | `load_dag_ground_truth()` |
| - | - | `_format_entity_report()` |
| - | - | Updated `PrecisionMetrics` fields and methods |

---

## Related Documentation

- **Classification Guide**: [CLASSIFICATION.md](./CLASSIFICATION.md) - Classification methodology
- **DAG Construction**: [DAG_CONSTRUCTION.md](./DAG_CONSTRUCTION.md) - DAG ground truth format
- **Metrics Guide**: [METRICS_GUIDE.md](./METRICS_GUIDE.md) - Precision calculation
- **Ground Truth Guide**: [GROUND_TRUTH_GUIDE.md](./GROUND_TRUTH_GUIDE.md) - How to define ground truth
- **Troubleshooting**: [PRECISION_TROUBLESHOOTING.md](./PRECISION_TROUBLESHOOTING.md) - API usage issues

---

**End of API Reference**
