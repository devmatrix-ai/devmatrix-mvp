# DAG Construction - Technical Documentation

**Version**: 1.0
**Date**: 2025-11-20
**Status**: ✅ Ground Truth Implemented (Task Group 6) | 🚧 Enhanced Inference Pending (TG7-8)
**Related**: DevMatrix Pipeline Precision Improvement

---

## Overview

The DAG (Directed Acyclic Graph) Construction system builds execution dependencies between atomized tasks to ensure correct execution order. This document describes the ground truth format, dependency inference strategies, and execution order validation.

## DAG Structure

A DAG consists of:
- **Nodes**: Atomic tasks (functions/endpoints) to be implemented
- **Edges**: Dependencies between tasks (task A must complete before task B)
- **Waves**: Execution layers where all tasks can run in parallel

```
Wave 1: [create_product, create_customer]  ← Independent tasks
   ↓
Wave 2: [create_cart]  ← Depends on create_customer
   ↓
Wave 3: [add_to_cart]  ← Depends on create_cart AND create_product
   ↓
Wave 4: [checkout_cart]  ← Depends on add_to_cart
   ↓
Wave 5: [simulate_payment]  ← Depends on checkout_cart
```

---

## Ground Truth Format

DAG ground truth defines the **expected** nodes and edges for validation purposes.

### Location

Ground truth should be added to test specification files:
```
tests/e2e/test_specs/<spec_name>.md
```

### YAML Schema

```yaml
## Expected Dependency Graph (Ground Truth)

nodes: <count>
  - <node_1_name>
  - <node_2_name>
  # ... all expected nodes

edges: <count>  # Unique dependency edges
  - <from_node> → <to_node>
  - <from_node> → <to_node>
  # ... all expected edges with rationale
```

### Complete Example

From `ecommerce_api_simple.md`:

```yaml
## Expected Dependency Graph (Ground Truth)

nodes: 10
  - create_product      # F1: POST /products
  - list_products       # F2: GET /products
  - create_customer     # F5: POST /customers
  - create_cart         # F8: POST /carts
  - add_to_cart         # F9: POST /carts/{id}/items
  - checkout_cart       # F13: POST /carts/{id}/checkout
  - simulate_payment    # F14: POST /payments/simulate
  - cancel_order        # F15: POST /orders/{id}/cancel
  - list_orders         # F16: GET /customers/{id}/orders
  - get_order           # F17: GET /orders/{id}

edges: 12  # Explicit dependencies
  # CRUD dependencies (create before read)
  - create_product → list_products
    rationale: Must create products before listing them

  - create_product → add_to_cart
    rationale: Products must exist before adding to cart

  # Workflow dependencies (sequential steps)
  - create_customer → create_cart
    rationale: Customer must exist to create their cart

  - create_cart → add_to_cart
    rationale: Cart must exist before adding items

  - add_to_cart → checkout_cart
    rationale: Cart must have items before checkout

  - checkout_cart → simulate_payment
    rationale: Order must be created before payment

  - checkout_cart → cancel_order
    rationale: Order must exist before cancellation

  - checkout_cart → list_orders
    rationale: At least one order must exist to list

  - checkout_cart → get_order
    rationale: Order must exist to retrieve it

  # Relationship dependencies
  - create_customer → list_orders
    rationale: Customer must exist to list their orders

  # Validation dependencies
  - create_cart → checkout_cart
    rationale: Cart must exist and be valid for checkout

  - add_to_cart → list_products
    rationale: Products in cart should be listable (optional)
```

---

## Ground Truth Parsing

### Loading Ground Truth

Ground truth is loaded from spec metadata using `load_dag_ground_truth()` in `precision_metrics.py`:

```python
def load_dag_ground_truth(spec_path: str) -> Dict[str, Any]:
    """
    Parse DAG ground truth from spec file

    Args:
        spec_path: Path to test specification markdown file

    Returns:
        Dictionary with:
        {
            'nodes': List[str],         # Expected node names
            'edges': List[Tuple[str, str]],  # Expected (from, to) edges
            'nodes_count': int,         # Expected node count
            'edges_count': int          # Expected edge count
        }

    Example:
        {
            'nodes': ['create_product', 'list_products', ...],
            'edges': [('create_product', 'list_products'), ...],
            'nodes_count': 10,
            'edges_count': 12
        }
    """
    # Implementation reads YAML section from markdown file
    # See: tests/e2e/precision_metrics.py
```

### Validation

DAG validation tests are in:
```
tests/unit/test_dag_ground_truth.py
```

**Test Coverage:**
- Ground truth parser loads nodes correctly
- Ground truth parser loads edges correctly
- DAG accuracy calculation is correct
- Missing edges are detected
- Invalid edges (cycles) are rejected

---

## Dependency Inference Strategies

The DAG construction process uses **multiple strategies** to infer dependencies:

### Strategy 1: Explicit Dependencies

Dependencies explicitly stated in spec metadata:

```yaml
# In spec file:
## Requirements

F9_add_to_cart:
  depends_on: [F8_create_cart, F1_create_product]
```

**Implementation:**
```python
def _explicit_dependencies(requirements: List[Requirement]) -> List[Edge]:
    """Extract dependencies from requirement metadata"""
    edges = []
    for req in requirements:
        if hasattr(req, 'depends_on'):
            for dep_id in req.depends_on:
                edges.append(Edge(
                    from_node=dep_id,
                    to_node=req.id,
                    type='explicit',
                    reason=f"Explicit dependency in spec"
                ))
    return edges
```

### Strategy 2: CRUD Dependencies

**Rule**: Create operations must precede Read/Update/Delete operations for the same entity.

```
create_product → list_products
create_product → update_product
create_product → delete_product
```

**Implementation** (🚧 Pending - Task Group 7):

```python
def _crud_dependencies(requirements: List[Requirement]) -> List[Edge]:
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
```

**Entity Grouping:**
```python
def _group_by_entity(requirements: List[Requirement]) -> Dict[str, List[Requirement]]:
    """Group requirements by entity (Product, Customer, Cart, etc.)"""
    entities = {}

    for req in requirements:
        entity = self._extract_entity(req)
        if entity not in entities:
            entities[entity] = []
        entities[entity].append(req)

    return entities

def _extract_entity(req: Requirement) -> str:
    """Extract entity name from requirement"""
    text = req.description.lower()
    known_entities = ['product', 'customer', 'cart', 'order', 'payment']

    for entity in known_entities:
        if entity in text:
            return entity

    return 'unknown'
```

### Strategy 3: Workflow Dependencies

**Rule**: Workflow steps must execute in sequence based on state transitions.

```
create_cart → add_to_cart → checkout_cart → simulate_payment
```

**Examples:**
- **Shopping Cart**: create_cart → add_to_cart → update_cart → checkout
- **Order Processing**: checkout → payment → fulfillment → delivery
- **User Onboarding**: register → verify_email → complete_profile

**Implementation** (🚧 Pending - Task Group 7):

```python
def _workflow_dependencies(requirements: List[Requirement]) -> List[Edge]:
    """
    Infer workflow dependencies based on state transitions

    Common patterns:
    - Cart workflow: create → add_items → checkout → payment
    - Order workflow: checkout → payment → fulfillment
    - User workflow: register → verify → activate
    """
    edges = []

    # Define workflow patterns
    workflows = {
        'cart': ['create_cart', 'add_to_cart', 'update_cart', 'checkout_cart'],
        'order': ['checkout_cart', 'simulate_payment', 'fulfill_order', 'cancel_order'],
        'user': ['register_user', 'verify_email', 'complete_profile']
    }

    for workflow_name, steps in workflows.items():
        # Find matching requirements
        workflow_reqs = [
            req for req in requirements
            if any(step in req.id.lower() for step in steps)
        ]

        # Create sequential dependencies
        for i in range(len(workflow_reqs) - 1):
            edges.append(Edge(
                from_node=workflow_reqs[i].id,
                to_node=workflow_reqs[i + 1].id,
                type='workflow_dependency',
                reason=f"{workflow_name} workflow: step {i} → step {i+1}"
            ))

    return edges
```

### Strategy 4: Pattern-Based Dependencies

Dependencies inferred from matched patterns:

```python
def _pattern_dependencies(requirements: List[Requirement]) -> List[Edge]:
    """
    Infer dependencies based on pattern relationships

    Example: If Pattern A is typically used with Pattern B,
    and Pattern A creates entity X, Pattern B may depend on X.
    """
    edges = []

    # Pattern-based rules
    # Example: REST API patterns
    if has_pattern(requirements, 'crud_create'):
        create_req = find_req_with_pattern(requirements, 'crud_create')
        list_req = find_req_with_pattern(requirements, 'crud_list')

        if create_req and list_req:
            edges.append(Edge(
                from_node=create_req.id,
                to_node=list_req.id,
                type='pattern_dependency',
                reason="CRUD pattern: create before list"
            ))

    return edges
```

---

## Enhanced Dependency Inference (🚧 Pending - TG7)

### Multi-Strategy Orchestration

The `infer_dependencies_enhanced()` method combines all strategies:

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
    3. Workflow dependencies (sequential state transitions)
    4. Pattern-based dependencies

    Returns:
        Deduplicated list of validated edges
    """
    edges = []

    # Strategy 1: Explicit from spec
    edges.extend(self._explicit_dependencies(requirements))

    # Strategy 2: CRUD rules
    edges.extend(self._crud_dependencies(requirements))

    # Strategy 3: Workflow patterns
    edges.extend(self._workflow_dependencies(requirements))

    # Strategy 4: Pattern-based
    edges.extend(self._pattern_dependencies(requirements))

    # Deduplicate and validate
    return self._validate_edges(edges)
```

### Edge Validation

```python
def _validate_edges(edges: List[Edge]) -> List[Edge]:
    """
    Validate and deduplicate edges

    Checks:
    - Remove duplicate edges (same from/to nodes)
    - Detect cycles (A → B → A)
    - Validate node existence
    - Remove self-references (A → A)
    """
    # Deduplicate
    unique_edges = {}
    for edge in edges:
        key = (edge.from_node, edge.to_node)
        if key not in unique_edges:
            unique_edges[key] = edge

    # Check for cycles
    edges_list = list(unique_edges.values())
    if has_cycles(edges_list):
        logger.warning("Cycles detected in DAG, removing cycle-causing edges")
        edges_list = remove_cycles(edges_list)

    # Remove self-references
    edges_list = [e for e in edges_list if e.from_node != e.to_node]

    return edges_list
```

---

## Execution Order Validation (🚧 Pending - TG8)

### Validation Method

```python
def validate_execution_order(self, dag: DAG) -> float:
    """
    Validate if DAG allows correct execution order

    Checks:
    - CRUD: Create before Read/Update/Delete (per entity)
    - Workflow: Cart before Checkout, Checkout before Payment
    - No cycles in dependency graph

    Returns:
        Score 0.0-1.0 (1.0 = all checks pass)
    """
    violations = []

    # Check 1: CRUD ordering
    for entity in ['product', 'customer', 'cart', 'order']:
        create_wave = self._find_wave(dag, f"create_{entity}")
        read_wave = self._find_wave(dag, f"list_{entity}")

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
    total_checks = 5  # Adjust based on number of checks performed
    score = 1.0 - (len(violations) / total_checks) if total_checks > 0 else 1.0

    if violations:
        logger.warning(f"Execution order violations: {violations}")

    return score
```

### Helper Methods

```python
def _find_wave(dag: DAG, node_name: str) -> Optional[int]:
    """Find which wave a node is in"""
    for wave_idx, wave in enumerate(dag.waves):
        if any(node.name == node_name for node in wave.nodes):
            return wave_idx
    return None

def _has_node(dag: DAG, node_name: str) -> bool:
    """Check if DAG contains a node"""
    return any(
        any(node.name == node_name for node in wave.nodes)
        for wave in dag.waves
    )
```

---

## DAG Accuracy Calculation

### Current Implementation (TG6)

```python
# File: tests/e2e/real_e2e_full_pipeline.py

# Load ground truth
ground_truth = load_dag_ground_truth(spec_path)

# Calculate accuracy
dag_accuracy = (
    (correct_nodes + correct_edges) /
    (ground_truth['nodes_count'] + ground_truth['edges_count'])
)

# Where:
# - correct_nodes: Count of nodes matching ground truth
# - correct_edges: Count of edges matching ground truth
# - nodes_count: Expected node count from ground truth
# - edges_count: Expected edge count from ground truth
```

### Target Accuracy

- **Baseline**: 57.6%
- **Target**: 80%+
- **Stretch**: 85%+

**Impact on Overall Precision**: DAG accuracy contributes **10%** to overall pipeline precision.

---

## Common DAG Patterns

### CRUD Application

```
Nodes: [create_X, list_X, get_X, update_X, delete_X]
Edges:
  create_X → list_X  (must create before listing)
  create_X → get_X   (must create before getting)
  create_X → update_X (must create before updating)
  create_X → delete_X (must create before deleting)
```

### E-commerce Application

```
Wave 1: create_product, create_customer
Wave 2: create_cart (depends on create_customer)
Wave 3: add_to_cart (depends on create_cart, create_product)
Wave 4: checkout_cart (depends on add_to_cart)
Wave 5: simulate_payment (depends on checkout_cart)
Wave 6: cancel_order (depends on checkout_cart)
```

### Multi-Tenant SaaS

```
Wave 1: create_organization
Wave 2: create_user (depends on create_organization)
Wave 3: create_project (depends on create_organization)
Wave 4: assign_user_to_project (depends on create_user, create_project)
Wave 5: create_task (depends on create_project)
Wave 6: assign_task (depends on create_task, create_user)
```

---

## Testing and Validation

### Unit Tests

DAG ground truth validation is tested in:
```
tests/unit/test_dag_ground_truth.py
```

**Test Coverage:**
- Ground truth parser loads nodes correctly
- Ground truth parser loads edges correctly
- DAG accuracy calculation is correct
- Missing edges are detected
- Cycle detection works

**Example Tests:**
```python
def test_dag_ground_truth_parser_nodes():
    """Test that ground truth parser loads nodes correctly"""
    ground_truth = load_dag_ground_truth("tests/e2e/test_specs/ecommerce_api_simple.md")
    assert ground_truth['nodes_count'] == 10
    assert 'create_product' in ground_truth['nodes']
    assert 'checkout_cart' in ground_truth['nodes']

def test_dag_ground_truth_parser_edges():
    """Test that ground truth parser loads edges correctly"""
    ground_truth = load_dag_ground_truth("tests/e2e/test_specs/ecommerce_api_simple.md")
    assert ground_truth['edges_count'] == 12
    assert ('create_product', 'list_products') in ground_truth['edges']
```

### Integration Testing

Full pipeline testing validates DAG accuracy across complete specifications:

```bash
# Run E2E pipeline with DAG validation
python -m pytest tests/e2e/test_real_e2e_full_pipeline.py -v

# Expected output:
# DAG Accuracy: 83.3% (18/22 correct nodes+edges)
# Overall Precision: 87.1% (+2.2% from enhanced inference)
```

---

## Troubleshooting

### Low DAG Accuracy (<80%)

**Symptoms:**
- DAG accuracy in metrics report is below 80%
- Many missing or incorrect edges

**Diagnosis:**
1. Review ground truth edge definitions
2. Check dependency inference logic
3. Validate that expected nodes are created

**Solutions:**
- Refine ground truth edge rationale
- Enable additional inference strategies
- Fix node naming inconsistencies

### Incorrect Execution Order

**Symptoms:**
- Tasks execute before their dependencies
- Runtime errors due to missing entities
- Tests fail due to execution order violations

**Diagnosis:**
- Review DAG wave assignments
- Check for missing edges
- Validate execution order score

**Solutions:**
```python
# Add missing explicit dependencies
F9_add_to_cart:
  depends_on: [F8_create_cart, F1_create_product]

# Or improve CRUD inference
# Ensure all entities have create operations defined
```

### Cycles Detected

**Symptoms:**
- DAG construction fails with cycle detection error
- Circular dependencies between tasks

**Diagnosis:**
- Review edge definitions for circular references
- Check workflow logic for circular dependencies

**Solutions:**
- Break cycles by reordering workflow steps
- Remove incorrect bidirectional edges
- Use validation to detect and fix cycles

---

## Best Practices

### 1. Ground Truth Definition

**DO:**
- ✅ Include rationale for all edges
- ✅ Document workflow sequences explicitly
- ✅ Use consistent node naming
- ✅ Review with team for consensus

**DON'T:**
- ❌ Define circular dependencies
- ❌ Omit critical dependencies
- ❌ Use inconsistent naming conventions

### 2. Dependency Inference

**DO:**
- ✅ Start with explicit dependencies
- ✅ Use CRUD rules for entity operations
- ✅ Document workflow patterns
- ✅ Validate execution order

**DON'T:**
- ❌ Rely solely on one inference strategy
- ❌ Ignore execution order violations
- ❌ Skip validation checks

### 3. Validation

**DO:**
- ✅ Run execution order validation
- ✅ Check for cycles before execution
- ✅ Monitor DAG accuracy metrics
- ✅ Review failed dependencies

**DON'T:**
- ❌ Ignore validation warnings
- ❌ Accept low accuracy without investigation
- ❌ Skip ground truth validation

---

## Related Documentation

- **Metrics Guide**: [METRICS_GUIDE.md](./METRICS_GUIDE.md) - Overall precision calculation
- **Ground Truth Guide**: [GROUND_TRUTH_GUIDE.md](./GROUND_TRUTH_GUIDE.md) - How to define ground truth
- **Troubleshooting**: [PRECISION_TROUBLESHOOTING.md](./PRECISION_TROUBLESHOOTING.md) - Debugging DAG issues

---

## Implementation Status

### ✅ Completed (Task Group 6)
- Ground truth YAML format defined
- Ground truth parser implemented (`load_dag_ground_truth()`)
- DAG accuracy calculation using ground truth
- Unit tests for ground truth validation
- Example ground truth for ecommerce spec

### 🚧 Pending (Task Groups 7-8)
- Enhanced dependency inference (`infer_dependencies_enhanced()`)
- CRUD dependency rules (`_crud_dependencies()`)
- Workflow dependency patterns (`_workflow_dependencies()`)
- Entity grouping and extraction
- Execution order validation (`validate_execution_order()`)
- Wave finding helpers

---

**End of Document**
