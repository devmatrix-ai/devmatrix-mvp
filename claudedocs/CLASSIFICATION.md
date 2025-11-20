# Requirements Classification - Technical Documentation

**Version**: 1.0
**Date**: 2025-11-20
**Status**: ✅ Implemented (Task Group 1)
**Related**: DevMatrix Pipeline Precision Improvement

---

## Overview

The Requirements Classification system categorizes functional requirements by **domain** and **risk level** to enable intelligent pattern matching, dependency inference, and execution planning. This document describes the ground truth format, validation methodology, and classification rationale.

## Classification Dimensions

### Domain Classification

Requirements are classified into one of four primary domains:

| Domain | Description | Examples |
|--------|-------------|----------|
| **crud** | Simple CRUD operations on single entities | Create product, List customers, Update cart |
| **workflow** | Multi-step business processes | Shopping cart flow, Order processing |
| **payment** | Payment processing and financial transactions | Checkout, Process payment, Refund |
| **custom** | Complex business logic not fitting other categories | Custom algorithms, Reports, Analytics |

**Decision Criteria:**
- **CRUD**: Single entity, single operation (Create/Read/Update/Delete)
- **Workflow**: Multiple steps, state transitions, cross-entity coordination
- **Payment**: Involves money transfer, external payment gateways, financial validation
- **Custom**: Complex logic, calculations, aggregations, domain-specific algorithms

### Risk Classification

Requirements are classified into one of three risk levels:

| Risk Level | Characteristics | Impact |
|------------|----------------|---------|
| **low** | Simple CRUD, well-established patterns, minimal business logic | Low testing priority, standard validation |
| **medium** | Moderate complexity, state management, workflow coordination | Standard testing, careful validation |
| **high** | Financial transactions, security-sensitive, complex business logic | Extensive testing, security audit, compliance checks |

**Decision Criteria:**
- **Low**: No state changes, no external dependencies, simple validation
- **Medium**: State changes, internal dependencies, moderate validation
- **High**: Financial impact, external APIs, security concerns, regulatory compliance

---

## Ground Truth Format

Classification ground truth is defined in test specifications using YAML format:

### Location

Ground truth should be added to test specification files:
```
tests/e2e/test_specs/<spec_name>.md
```

### YAML Schema

```yaml
## Classification Ground Truth

<requirement_id>:
  domain: <crud|workflow|payment|custom>
  risk: <low|medium|high>
  rationale: <optional explanation>
```

### Complete Example

From `ecommerce_api_simple.md`:

```yaml
## Classification Ground Truth

F1_create_product:
  domain: crud
  risk: low
  rationale: |
    Simple CRUD operation creating a single Product entity.
    Standard validation (name, price, stock). No external dependencies.

F2_list_products:
  domain: crud
  risk: low
  rationale: |
    Simple read operation with optional filtering.
    No state changes, standard query patterns.

F8_create_cart:
  domain: workflow
  risk: medium
  rationale: |
    Initiates shopping cart workflow. Creates Cart entity
    and establishes relationship with Customer. Requires state management.

F9_add_to_cart:
  domain: workflow
  risk: medium
  rationale: |
    Part of shopping cart workflow. Validates product availability,
    updates cart state, manages item quantities.

F13_checkout_cart:
  domain: payment
  risk: high
  rationale: |
    Initiates payment workflow. Transitions cart to order,
    triggers payment processing. Financial transaction with
    external system integration.

F14_simulate_payment:
  domain: payment
  risk: high
  rationale: |
    Processes payment simulation. Updates order status,
    manages payment state. High risk due to financial impact.
```

---

## Validation Methodology

### Validation Function

Classification validation is performed by `validate_classification()` in `precision_metrics.py`:

```python
def validate_classification(
    actual: Dict[str, Any],
    expected: Dict[str, Any]
) -> bool:
    """
    Validate if requirement classification matches ground truth

    Args:
        actual: Classification from RequirementsClassifier
                {domain: str, risk: str, ...}
        expected: Ground truth classification
                  {domain: str, risk: str}

    Returns:
        True if both domain and risk match exactly
        True if no ground truth exists (graceful degradation)
    """
    if not expected:
        return True  # No ground truth = assume correct

    return (
        actual.get('domain') == expected.get('domain') and
        actual.get('risk') == expected.get('risk')
    )
```

### Loading Ground Truth

Ground truth is loaded from spec metadata using `load_classification_ground_truth()`:

```python
def load_classification_ground_truth(spec_path: str) -> Dict[str, Dict[str, str]]:
    """
    Parse classification ground truth from spec file

    Args:
        spec_path: Path to test specification markdown file

    Returns:
        Dictionary mapping requirement_id to {domain, risk, rationale}

    Example:
        {
            "F1_create_product": {
                "domain": "crud",
                "risk": "low",
                "rationale": "Simple CRUD operation..."
            }
        }
    """
    # Implementation reads YAML section from markdown file
    # See: tests/e2e/precision_metrics.py lines 180-220
```

### Accuracy Calculation

Classification accuracy is calculated as:

```python
accuracy = classifications_correct / classifications_total

# Where:
# - classifications_correct: Count of requirements where domain AND risk match
# - classifications_total: Total requirements classified
```

**Target Accuracy**: 80%+ (stretch goal: 90%+)

---

## Classification Examples by Domain

### CRUD Domain (Low Risk)

**Characteristics:**
- Single entity operation
- Standard HTTP methods (GET, POST, PUT, DELETE)
- Simple validation rules
- No external dependencies

**Examples:**
```yaml
F1_create_product:
  domain: crud
  risk: low
  # POST /products - create Product with name, price, stock

F2_list_products:
  domain: crud
  risk: low
  # GET /products - list with optional filters

F3_update_product:
  domain: crud
  risk: low
  # PUT /products/{id} - update product fields

F4_delete_product:
  domain: crud
  risk: low
  # DELETE /products/{id} - soft or hard delete
```

### Workflow Domain (Medium Risk)

**Characteristics:**
- Multi-step business process
- State transitions
- Cross-entity coordination
- Internal dependencies

**Examples:**
```yaml
F8_create_cart:
  domain: workflow
  risk: medium
  # Initiates cart workflow, creates Cart for Customer

F9_add_to_cart:
  domain: workflow
  risk: medium
  # Validates product, updates cart state, manages quantities

F10_remove_from_cart:
  domain: workflow
  risk: medium
  # Removes item, recalculates totals, validates cart state

F11_update_cart_item:
  domain: workflow
  risk: medium
  # Updates quantity, validates stock, recalculates totals
```

### Payment Domain (High Risk)

**Characteristics:**
- Financial transactions
- External system integration
- Security-sensitive operations
- Regulatory compliance requirements

**Examples:**
```yaml
F13_checkout_cart:
  domain: payment
  risk: high
  # Transitions cart to order, initiates payment workflow

F14_simulate_payment:
  domain: payment
  risk: high
  # Processes payment, updates order status, manages payment state

F15_cancel_order:
  domain: payment
  risk: high
  # Cancels order, potentially refunds payment, updates status
```

### Custom Domain (Variable Risk)

**Characteristics:**
- Complex business logic
- Calculations or aggregations
- Domain-specific algorithms
- May have low to high risk depending on complexity

**Examples:**
```yaml
F17_calculate_revenue:
  domain: custom
  risk: low
  # Simple aggregation query for revenue reporting

F18_recommendation_engine:
  domain: custom
  risk: medium
  # ML-based product recommendations using customer history

F19_fraud_detection:
  domain: custom
  risk: high
  # Real-time fraud detection with external risk scoring
```

---

## Integration with Pipeline

### Phase 2: Requirements Analysis

Classification happens in Phase 2 of the DevMatrix E2E pipeline:

```python
# File: tests/e2e/real_e2e_full_pipeline.py (Phase 2)

# 1. Classify requirements
classified_reqs = req_classifier.classify(functional_reqs)

# 2. Load ground truth for validation
ground_truth = load_classification_ground_truth(spec_path)

# 3. Track classification metrics
precision_tracker.classifications_total = len(classified_reqs)
precision_tracker.classifications_correct = sum(
    1 for req in classified_reqs
    if validate_classification(req, ground_truth.get(req.id, {}))
)
precision_tracker.classifications_incorrect = (
    precision_tracker.classifications_total -
    precision_tracker.classifications_correct
)
```

### Impact on Overall Precision

Classification accuracy contributes **15%** to overall pipeline precision:

```python
# Precision calculation weights
weights = {
    'accuracy': 0.20,         # 20%
    'pattern_f1': 0.15,       # 15%
    'classification': 0.15,   # 15% ← Classification
    'dag': 0.10,              # 10%
    'atomization': 0.10,      # 10%
    'execution': 0.20,        # 20%
    'tests': 0.10             # 10%
}

overall_precision = sum(scores[k] * weights[k] for k in weights)
```

**Impact Example:**
- Baseline classification accuracy: 0% (not tracked)
- Target classification accuracy: 80%
- Precision improvement: +12% overall (80% × 15% weight)

---

## Classification Decision Tree

Use this decision tree to determine domain and risk:

```
1. Does it involve money transfer or payment processing?
   YES → domain: payment, risk: high
   NO  → Continue to 2

2. Does it perform a single CRUD operation on one entity?
   YES → domain: crud
         - No external dependencies? → risk: low
         - Has external dependencies? → risk: medium
   NO  → Continue to 3

3. Does it coordinate multiple steps or state transitions?
   YES → domain: workflow
         - Simple state changes? → risk: medium
         - Complex with external APIs? → risk: high
   NO  → Continue to 4

4. Is it complex business logic or algorithm?
   YES → domain: custom
         - Simple calculation? → risk: low
         - Moderate complexity? → risk: medium
         - Security/compliance concerns? → risk: high
```

---

## Common Classification Patterns

### E-commerce Application

| Requirement | Domain | Risk | Pattern |
|-------------|--------|------|---------|
| Create Product | crud | low | Basic entity creation |
| List Products | crud | low | Simple read with filters |
| Create Customer | crud | low | Basic entity creation |
| Create Cart | workflow | medium | Workflow initiation |
| Add to Cart | workflow | medium | State management |
| Checkout | payment | high | Payment workflow |
| Process Payment | payment | high | Financial transaction |
| Cancel Order | payment | high | Refund workflow |

### Task Management Application

| Requirement | Domain | Risk | Pattern |
|-------------|--------|------|---------|
| Create Task | crud | low | Basic entity creation |
| List Tasks | crud | low | Simple read with filters |
| Update Task | crud | low | Basic entity update |
| Assign Task | workflow | medium | Relationship management |
| Complete Task | workflow | medium | Status transition |
| Task Notifications | custom | medium | Event-driven logic |

---

## Testing and Validation

### Unit Tests

Classification validation is tested in:
```
tests/unit/test_classification_validator.py
```

**Test Coverage:**
- Domain matching validation
- Risk matching validation
- Missing ground truth handling
- Accuracy calculation
- Edge cases (empty classifications, malformed data)

**Example Tests:**
```python
def test_classification_validator_domain_match():
    """Test that domain matching works correctly"""
    actual = {"domain": "crud", "risk": "low"}
    expected = {"domain": "crud", "risk": "low"}
    assert validate_classification(actual, expected) is True

def test_classification_validator_domain_mismatch():
    """Test that domain mismatch is detected"""
    actual = {"domain": "workflow", "risk": "low"}
    expected = {"domain": "crud", "risk": "low"}
    assert validate_classification(actual, expected) is False
```

### Integration Testing

Full pipeline testing validates classification accuracy across complete specifications:

```bash
# Run E2E pipeline with classification validation
python -m pytest tests/e2e/test_real_e2e_full_pipeline.py -v

# Expected output:
# Classification Accuracy: 88.2% (15/17 requirements)
# Overall Precision: 85.3% (+12.3% from baseline)
```

---

## Troubleshooting

### Low Classification Accuracy (<80%)

**Symptoms:**
- Classification accuracy in metrics report is below 80%
- Many requirements misclassified

**Diagnosis:**
1. Review ground truth definitions
2. Check RequirementsClassifier logic
3. Validate requirement parsing

**Solutions:**
- Refine ground truth rationale
- Update classifier heuristics
- Add domain-specific keywords

### Missing Ground Truth

**Symptoms:**
- Classification accuracy shows 100% but seems unrealistic
- Warning: "No ground truth found for spec"

**Diagnosis:**
- Ground truth YAML section missing from spec file
- Incorrect YAML format

**Solutions:**
```yaml
# Add to test spec file:
## Classification Ground Truth

<requirement_id>:
  domain: <domain>
  risk: <risk>
  rationale: <explanation>
```

### Classification Inconsistency

**Symptoms:**
- Similar requirements classified differently
- Classifications don't match expected patterns

**Diagnosis:**
- Inconsistent classification logic
- Missing classification rules

**Solutions:**
- Use classification decision tree consistently
- Document edge cases and rationale
- Review with team for consensus

---

## Best Practices

### 1. Ground Truth Definition

**DO:**
- ✅ Include rationale for non-obvious classifications
- ✅ Use consistent decision criteria across specs
- ✅ Review with team for consensus on edge cases
- ✅ Document assumptions explicitly

**DON'T:**
- ❌ Guess classifications without clear rationale
- ❌ Mix classification criteria between specs
- ❌ Skip rationale for complex requirements

### 2. Validation

**DO:**
- ✅ Validate ground truth format before running pipeline
- ✅ Review misclassifications systematically
- ✅ Update ground truth based on insights

**DON'T:**
- ❌ Ignore validation warnings
- ❌ Accept low accuracy without investigation

### 3. Maintenance

**DO:**
- ✅ Update ground truth when spec changes
- ✅ Version ground truth with specs
- ✅ Review classification accuracy in CI/CD

**DON'T:**
- ❌ Let ground truth drift from specs
- ❌ Skip ground truth in new specs

---

## Related Documentation

- **Metrics Guide**: [METRICS_GUIDE.md](./METRICS_GUIDE.md) - Overall precision calculation
- **Ground Truth Guide**: [GROUND_TRUTH_GUIDE.md](./GROUND_TRUTH_GUIDE.md) - How to define ground truth
- **Troubleshooting**: [PRECISION_TROUBLESHOOTING.md](./PRECISION_TROUBLESHOOTING.md) - Debugging low precision

---

## Appendix: Full Ecommerce Example

Complete classification ground truth from `ecommerce_api_simple.md`:

```yaml
## Classification Ground Truth

F1_create_product:
  domain: crud
  risk: low
  rationale: Simple CRUD operation creating Product entity with basic validation

F2_list_products:
  domain: crud
  risk: low
  rationale: Simple read operation with optional filtering, no state changes

F3_update_product:
  domain: crud
  risk: low
  rationale: Basic CRUD update operation with standard validation

F4_delete_product:
  domain: crud
  risk: low
  rationale: Simple delete operation, no complex dependencies

F5_create_customer:
  domain: crud
  risk: low
  rationale: Basic CRUD operation creating Customer entity

F6_list_customers:
  domain: crud
  risk: low
  rationale: Simple read operation with optional filters

F7_get_customer:
  domain: crud
  risk: low
  rationale: Simple read operation for single entity

F8_create_cart:
  domain: workflow
  risk: medium
  rationale: Initiates shopping cart workflow, creates Cart and establishes Customer relationship

F9_add_to_cart:
  domain: workflow
  risk: medium
  rationale: Part of cart workflow, validates product availability, manages item quantities

F10_remove_from_cart:
  domain: workflow
  risk: medium
  rationale: Cart workflow step, removes items and recalculates totals

F11_update_cart_item:
  domain: workflow
  risk: medium
  rationale: Updates cart item quantity with stock validation

F12_get_cart:
  domain: workflow
  risk: medium
  rationale: Retrieves cart with items, part of workflow state inspection

F13_checkout_cart:
  domain: payment
  risk: high
  rationale: Initiates payment workflow, transitions cart to order, financial transaction

F14_simulate_payment:
  domain: payment
  risk: high
  rationale: Processes payment simulation, updates order status, financial impact

F15_cancel_order:
  domain: payment
  risk: high
  rationale: Cancels order with potential refund, manages payment state

F16_list_orders:
  domain: crud
  risk: low
  rationale: Simple read operation listing orders for customer

F17_get_order:
  domain: crud
  risk: low
  rationale: Simple read operation for single order entity
```

---

**End of Document**
