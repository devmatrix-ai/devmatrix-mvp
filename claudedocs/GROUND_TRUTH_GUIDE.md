# Ground Truth Definition Guide

**Version**: 1.0
**Date**: 2025-11-20
**Audience**: Developers, QA Engineers, Technical Writers
**Purpose**: Learn how to define classification and DAG ground truth for test specifications

---

## Overview

Ground truth definitions enable the DevMatrix pipeline to measure its own accuracy. This guide shows you how to define ground truth for:

1. **Classification Ground Truth**: Expected domain and risk classifications
2. **DAG Ground Truth**: Expected dependency graph structure

---

## When to Define Ground Truth

**Required for:**
- ✅ New test specifications
- ✅ Regression testing
- ✅ Precision benchmarking
- ✅ Quality validation

**Optional for:**
- ⚠️ Exploratory prototypes
- ⚠️ One-off experiments
- ⚠️ Proof-of-concept specs

**Best Practice**: Define ground truth for ALL test specs in `tests/e2e/test_specs/`.

---

## Classification Ground Truth

### Purpose

Classification ground truth tells the pipeline:
- What **domain** each requirement belongs to (crud, workflow, payment, custom)
- What **risk level** each requirement has (low, medium, high)

This enables the pipeline to measure classification accuracy.

### Where to Add It

Add classification ground truth to your test specification file:

```
tests/e2e/test_specs/<your_spec>.md
```

### YAML Format

```yaml
## Classification Ground Truth

<requirement_id>:
  domain: <crud|workflow|payment|custom>
  risk: <low|medium|high>
  rationale: |
    <Optional multi-line explanation of why this classification
    was chosen. Helpful for edge cases and team consensus.>
```

### Step-by-Step Instructions

#### Step 1: Identify All Requirements

List all functional requirements from your spec:

```markdown
# Example Spec: Simple Task API

## Functional Requirements

- F1: Create Task - POST /tasks
- F2: List Tasks - GET /tasks
- F3: Get Task - GET /tasks/{id}
- F4: Update Task - PUT /tasks/{id}
- F5: Delete Task - DELETE /tasks/{id}
- F6: Assign Task - POST /tasks/{id}/assign
- F7: Complete Task - POST /tasks/{id}/complete
```

#### Step 2: Classify Each Requirement

Use the classification decision tree (see [CLASSIFICATION.md](./CLASSIFICATION.md)):

```
F1: Create Task
  → Single entity? YES → domain: crud
  → External dependencies? NO → risk: low

F2: List Tasks
  → Single entity? YES → domain: crud
  → External dependencies? NO → risk: low

F3: Get Task
  → Single entity? YES → domain: crud
  → External dependencies? NO → risk: low

F4: Update Task
  → Single entity? YES → domain: crud
  → External dependencies? NO → risk: low

F5: Delete Task
  → Single entity? YES → domain: crud
  → External dependencies? NO → risk: low

F6: Assign Task
  → Multi-step workflow? YES → domain: workflow
  → State changes? YES → risk: medium

F7: Complete Task
  → Multi-step workflow? YES → domain: workflow
  → State changes? YES → risk: medium
```

#### Step 3: Write Ground Truth YAML

Add to your spec file:

```yaml
## Classification Ground Truth

F1_create_task:
  domain: crud
  risk: low
  rationale: Simple CRUD operation creating Task entity with basic validation

F2_list_tasks:
  domain: crud
  risk: low
  rationale: Simple read operation with optional filtering, no state changes

F3_get_task:
  domain: crud
  risk: low
  rationale: Simple read operation for single Task entity

F4_update_task:
  domain: crud
  risk: low
  rationale: Basic CRUD update operation with standard validation

F5_delete_task:
  domain: crud
  risk: low
  rationale: Simple delete operation, no complex dependencies

F6_assign_task:
  domain: workflow
  risk: medium
  rationale: |
    Workflow step that assigns task to user.
    Updates task state and establishes relationship.
    Requires validation of user permissions.

F7_complete_task:
  domain: workflow
  risk: medium
  rationale: |
    Workflow step that transitions task state to completed.
    May trigger notifications, update dependencies, and validate completion criteria.
```

#### Step 4: Review with Team

**Checklist:**
- ✅ All requirements have classifications
- ✅ Classifications use decision tree consistently
- ✅ Edge cases have rationale documented
- ✅ Team agrees on classifications

---

## DAG Ground Truth

### Purpose

DAG ground truth tells the pipeline:
- What **nodes** (tasks) should exist in the dependency graph
- What **edges** (dependencies) should connect the nodes

This enables the pipeline to measure DAG construction accuracy.

### Where to Add It

Add DAG ground truth to the same test specification file:

```
tests/e2e/test_specs/<your_spec>.md
```

### YAML Format

```yaml
## Expected Dependency Graph (Ground Truth)

nodes: <count>
  - <node_1_name>
  - <node_2_name>
  # ... list all expected nodes

edges: <count>  # Count of unique dependency edges
  - <from_node> → <to_node>
    rationale: <why this dependency exists>
  - <from_node> → <to_node>
    rationale: <why this dependency exists>
  # ... list all expected edges
```

### Step-by-Step Instructions

#### Step 1: Identify Nodes

Nodes typically correspond to main implementation functions/endpoints:

```markdown
# Example Spec: Simple Task API

Expected Nodes (7):
1. create_task      (F1: POST /tasks)
2. list_tasks       (F2: GET /tasks)
3. get_task         (F3: GET /tasks/{id})
4. update_task      (F4: PUT /tasks/{id})
5. delete_task      (F5: DELETE /tasks/{id})
6. assign_task      (F6: POST /tasks/{id}/assign)
7. complete_task    (F7: POST /tasks/{id}/complete)
```

#### Step 2: Identify CRUD Dependencies

**Rule**: Create operations must come before Read/Update/Delete operations.

```
create_task → list_tasks    (must create before listing)
create_task → get_task      (must create before getting)
create_task → update_task   (must create before updating)
create_task → delete_task   (must create before deleting)
```

#### Step 3: Identify Workflow Dependencies

**Rule**: Workflow steps must execute in sequence.

```
create_task → assign_task   (must create before assigning)
assign_task → complete_task (must assign before completing)
```

#### Step 4: Identify Relationship Dependencies

**Rule**: Related entities must exist before relationships can be established.

```
# No additional relationships in this simple example
# For more complex specs, consider:
# - User must exist before assigning task to user
# - Project must exist before creating task in project
```

#### Step 5: Write Ground Truth YAML

```yaml
## Expected Dependency Graph (Ground Truth)

nodes: 7
  - create_task
  - list_tasks
  - get_task
  - update_task
  - delete_task
  - assign_task
  - complete_task

edges: 7  # Unique dependency edges
  - create_task → list_tasks
    rationale: Must create tasks before listing them

  - create_task → get_task
    rationale: Must create task before getting it

  - create_task → update_task
    rationale: Must create task before updating it

  - create_task → delete_task
    rationale: Must create task before deleting it

  - create_task → assign_task
    rationale: Must create task before assigning it

  - assign_task → complete_task
    rationale: Task should be assigned before completion (workflow logic)

  - create_task → complete_task
    rationale: Must create task before completing it
```

#### Step 6: Validate No Cycles

**Critical**: DAG must not contain cycles!

**Bad Example (cycle)**:
```
create_task → assign_task → create_task  ❌ CYCLE!
```

**Good Example (acyclic)**:
```
create_task → assign_task → complete_task  ✅ NO CYCLES
```

#### Step 7: Review with Team

**Checklist:**
- ✅ All expected nodes listed
- ✅ CRUD dependencies included
- ✅ Workflow dependencies correct
- ✅ No cycles in dependency graph
- ✅ Edge rationale documented
- ✅ Team agrees on dependencies

---

## Complete Example: E-commerce API

Here's a complete example for the `ecommerce_api_simple` spec:

```yaml
## Classification Ground Truth

F1_create_product:
  domain: crud
  risk: low
  rationale: Simple CRUD operation creating Product entity

F2_list_products:
  domain: crud
  risk: low
  rationale: Simple read operation with optional filtering

F8_create_cart:
  domain: workflow
  risk: medium
  rationale: Initiates shopping cart workflow, creates Cart for Customer

F9_add_to_cart:
  domain: workflow
  risk: medium
  rationale: Part of cart workflow, validates product availability, manages quantities

F13_checkout_cart:
  domain: payment
  risk: high
  rationale: Initiates payment workflow, transitions cart to order

F14_simulate_payment:
  domain: payment
  risk: high
  rationale: Processes payment simulation, updates order status

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

edges: 12
  # CRUD dependencies
  - create_product → list_products
    rationale: Must create products before listing

  - create_product → add_to_cart
    rationale: Products must exist before adding to cart

  # Workflow dependencies
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

  # Additional workflow
  - create_cart → checkout_cart
    rationale: Cart must exist and be valid for checkout

  - simulate_payment → cancel_order
    rationale: Payment must be processed before allowing cancellation
```

---

## Common Patterns and Templates

### CRUD-Only Application

```yaml
## Classification Ground Truth

F1_create_entity:
  domain: crud
  risk: low

F2_list_entities:
  domain: crud
  risk: low

F3_get_entity:
  domain: crud
  risk: low

F4_update_entity:
  domain: crud
  risk: low

F5_delete_entity:
  domain: crud
  risk: low

## Expected Dependency Graph (Ground Truth)

nodes: 5
  - create_entity
  - list_entities
  - get_entity
  - update_entity
  - delete_entity

edges: 4
  - create_entity → list_entities
    rationale: Create before list

  - create_entity → get_entity
    rationale: Create before get

  - create_entity → update_entity
    rationale: Create before update

  - create_entity → delete_entity
    rationale: Create before delete
```

### Workflow Application

```yaml
## Classification Ground Truth

F1_create_workflow:
  domain: workflow
  risk: medium

F2_step_1:
  domain: workflow
  risk: medium

F3_step_2:
  domain: workflow
  risk: medium

F4_complete_workflow:
  domain: workflow
  risk: high

## Expected Dependency Graph (Ground Truth)

nodes: 4
  - create_workflow
  - step_1
  - step_2
  - complete_workflow

edges: 3
  - create_workflow → step_1
    rationale: Workflow must be created before first step

  - step_1 → step_2
    rationale: Sequential workflow steps

  - step_2 → complete_workflow
    rationale: Must complete steps before finishing workflow
```

### Payment Application

```yaml
## Classification Ground Truth

F1_create_order:
  domain: workflow
  risk: medium

F2_process_payment:
  domain: payment
  risk: high

F3_confirm_payment:
  domain: payment
  risk: high

F4_refund_payment:
  domain: payment
  risk: high

## Expected Dependency Graph (Ground Truth)

nodes: 4
  - create_order
  - process_payment
  - confirm_payment
  - refund_payment

edges: 3
  - create_order → process_payment
    rationale: Order must exist before payment

  - process_payment → confirm_payment
    rationale: Payment must be processed before confirmation

  - confirm_payment → refund_payment
    rationale: Payment must be confirmed before refund
```

---

## Validation and Testing

### Validating Your Ground Truth

Before committing, validate your ground truth:

```bash
# Run unit tests for ground truth parsing
python -m pytest tests/unit/test_classification_validator.py -v
python -m pytest tests/unit/test_dag_ground_truth.py -v

# Run E2E pipeline with your spec
python -m pytest tests/e2e/test_real_e2e_full_pipeline.py -k "your_spec" -v

# Check metrics output
# Expected:
# - Classification Accuracy: 80%+ (if classifications match)
# - DAG Accuracy: 80%+ (if dependencies match)
```

### Common Validation Errors

**Error: YAML parsing failed**
```
Solution: Check YAML indentation (use 2 spaces, not tabs)
```

**Error: Classification accuracy is 0%**
```
Solution: Requirement IDs in ground truth must match spec exactly
Example: Use "F1_create_task" not "F1" or "create_task"
```

**Error: DAG accuracy is low**
```
Solution: Review dependency edges, ensure all CRUD dependencies included
```

**Error: Cycle detected in DAG**
```
Solution: Remove circular dependencies, validate workflow logic
```

---

## Best Practices

### DO

✅ **Start Simple**: Begin with CRUD dependencies, add workflow later
✅ **Be Consistent**: Use same classification criteria across all specs
✅ **Document Rationale**: Include rationale for non-obvious classifications
✅ **Review as Team**: Get consensus on edge cases
✅ **Validate Early**: Test ground truth before committing
✅ **Version Control**: Commit ground truth with spec changes

### DON'T

❌ **Skip Rationale**: Rationale helps future reviewers understand decisions
❌ **Guess Classifications**: Use decision tree, not intuition
❌ **Create Cycles**: DAG must be acyclic
❌ **Ignore Validation Errors**: Fix errors before committing
❌ **Diverge from Spec**: Keep ground truth synchronized with spec
❌ **Use Inconsistent IDs**: Requirement IDs must match exactly

---

## Troubleshooting

### Q: What if I'm unsure about a classification?

**A**: Follow this process:
1. Use the classification decision tree in [CLASSIFICATION.md](./CLASSIFICATION.md)
2. Document your reasoning in `rationale`
3. Review with team members
4. Start conservative (e.g., risk: medium instead of low)
5. Refine based on metrics and team feedback

### Q: How do I know if my DAG ground truth is correct?

**A**: Check for:
- All CRUD dependencies included (create before read/update/delete)
- Workflow steps in correct sequence
- No circular dependencies (use topological sort)
- Edges make logical sense for execution order
- DAG accuracy metric is 80%+

### Q: What if the pipeline's actual DAG differs from my ground truth?

**A**: Investigate both:
- Is your ground truth wrong? (Review dependencies)
- Is the pipeline's inference wrong? (File bug report)
- Usually: Refine ground truth based on insights

### Q: Should I include optional dependencies?

**A**: Include dependencies that are:
- Required for correctness (e.g., create before read)
- Part of critical workflows (e.g., checkout before payment)

Exclude dependencies that are:
- Optional optimizations
- Nice-to-have but not required
- Implementation details

---

## FAQ

### How long does it take to define ground truth?

**Simple spec (5-10 requirements)**: 15-30 minutes
**Medium spec (10-20 requirements)**: 30-60 minutes
**Complex spec (20+ requirements)**: 1-2 hours

### Do I need to update ground truth when spec changes?

**Yes!** Ground truth must stay synchronized with spec:
- Add ground truth for new requirements
- Update classifications if logic changes
- Add/remove edges if dependencies change
- Version control ground truth with spec

### Can I reuse ground truth from similar specs?

**Yes**, but carefully:
- Copy similar patterns
- Adjust for spec-specific requirements
- Validate all IDs match new spec
- Review classifications for context

### What if I make a mistake in ground truth?

**No problem!** Ground truth is iterative:
- Pipeline will show low accuracy metrics
- Review and refine ground truth
- Commit corrections
- Re-run tests to validate

---

## Related Documentation

- **Classification Guide**: [CLASSIFICATION.md](./CLASSIFICATION.md) - Classification decision tree and examples
- **DAG Construction**: [DAG_CONSTRUCTION.md](./DAG_CONSTRUCTION.md) - Dependency inference strategies
- **Metrics Guide**: [METRICS_GUIDE.md](./METRICS_GUIDE.md) - How ground truth affects precision
- **Troubleshooting**: [PRECISION_TROUBLESHOOTING.md](./PRECISION_TROUBLESHOOTING.md) - Debugging ground truth issues

---

## Checklist: Ground Truth Completion

Use this checklist before committing:

### Classification Ground Truth
- [ ] All functional requirements have classifications
- [ ] Domain values are valid (crud, workflow, payment, custom)
- [ ] Risk values are valid (low, medium, high)
- [ ] Edge cases have rationale documented
- [ ] Team has reviewed and approved classifications

### DAG Ground Truth
- [ ] All expected nodes listed
- [ ] Node count matches nodes list
- [ ] All CRUD dependencies included
- [ ] Workflow dependencies in correct sequence
- [ ] Edge count matches edges list
- [ ] No circular dependencies
- [ ] Edge rationale documented
- [ ] Team has reviewed and approved dependencies

### Validation
- [ ] Unit tests pass (test_classification_validator, test_dag_ground_truth)
- [ ] E2E pipeline runs successfully with spec
- [ ] Classification accuracy ≥ 80%
- [ ] DAG accuracy ≥ 80%
- [ ] No validation warnings or errors

### Documentation
- [ ] Ground truth committed to version control
- [ ] Changes documented in commit message
- [ ] Team notified of ground truth update

---

**End of Guide**

For questions or help, refer to [PRECISION_TROUBLESHOOTING.md](./PRECISION_TROUBLESHOOTING.md) or ask your team lead.
