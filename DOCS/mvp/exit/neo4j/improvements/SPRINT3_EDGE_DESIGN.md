# Sprint 3: BehaviorModelIR Edge Design

> **Document**: Tarea 3.1 + 3.2
> **Date**: 2025-11-29
> **Status**: APPROVED

---

## Current State

```
BehaviorModelIR nodes: 280 (empty shells)
Flow nodes: 0
Step nodes: 0
Invariant nodes: 0
HAS_BEHAVIOR_MODEL relationships: 0
```

## Target State

```
ApplicationIR
    └── HAS_BEHAVIOR_MODEL → BehaviorModelIR
            ├── HAS_FLOW → Flow
            │       └── HAS_STEP → Step
            │               ├── TARGETS_ENTITY → Entity
            │               └── CALLS_ENDPOINT → Endpoint
            └── HAS_INVARIANT → Invariant
                    ├── APPLIES_TO → Entity
                    └── CHECKS_ATTRIBUTE → Attribute
```

---

## Node Schemas

### Flow Node

```cypher
(:Flow {
    flow_id: string,           -- "{app_id}|flow|{name}"
    name: string,              -- Flow name
    type: string,              -- "workflow" | "state_transition" | "policy" | "event_handler"
    trigger: string,           -- e.g., "On Checkout", "Before Save"
    description: string,       -- Optional description
    behavior_model_id: string, -- Parent reference
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

### Step Node

```cypher
(:Step {
    step_id: string,           -- "{flow_id}|step|{order}"
    order: integer,            -- Sequence number
    description: string,       -- What this step does
    action: string,            -- Action type/name
    target_entity: string,     -- Optional target entity name
    condition: string,         -- Optional condition expression
    flow_id: string,           -- Parent reference
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

### Invariant Node

```cypher
(:Invariant {
    invariant_id: string,      -- "{app_id}|invariant|{entity}|{hash}"
    entity: string,            -- Target entity name
    description: string,       -- Human-readable description
    expression: string,        -- e.g., "balance >= 0"
    enforcement_level: string, -- "strict" | "eventual"
    behavior_model_id: string, -- Parent reference
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

---

## Relationship Schemas

### HAS_BEHAVIOR_MODEL

```cypher
(ApplicationIR)-[:HAS_BEHAVIOR_MODEL {
    created_at: datetime
}]->(BehaviorModelIR)
```

**Cardinality**: 1:1 (cada ApplicationIR tiene exactamente 1 BehaviorModelIR)

### HAS_FLOW

```cypher
(BehaviorModelIR)-[:HAS_FLOW {
    created_at: datetime
}]->(Flow)
```

**Cardinality**: 1:N (BehaviorModelIR puede tener múltiples Flows)

### HAS_STEP

```cypher
(Flow)-[:HAS_STEP {
    sequence: integer,
    created_at: datetime
}]->(Step)
```

**Cardinality**: 1:N (Flow puede tener múltiples Steps ordenados)

### TARGETS_ENTITY (Step → Entity)

```cypher
(Step)-[:TARGETS_ENTITY {
    operation: string,         -- "create" | "update" | "delete" | "read"
    role: string,              -- "primary" | "secondary"
    confidence: float,         -- Inference confidence
    inference_method: string,  -- "explicit" | "path_analysis" | "action_semantic"
    created_at: datetime
}]->(Entity)
```

**Cardinality**: N:1 (múltiples Steps pueden apuntar a la misma Entity)

### CALLS_ENDPOINT (Step → Endpoint)

```cypher
(Step)-[:CALLS_ENDPOINT {
    sequence: integer,         -- Order within the step
    conditional: boolean,      -- Is this call conditional?
    confidence: float,         -- Inference confidence
    inference_method: string,  -- "explicit" | "action_matching"
    created_at: datetime
}]->(Endpoint)
```

**Cardinality**: N:M (Steps pueden llamar múltiples Endpoints, Endpoints llamados por múltiples Steps)

### HAS_INVARIANT

```cypher
(BehaviorModelIR)-[:HAS_INVARIANT {
    created_at: datetime
}]->(Invariant)
```

**Cardinality**: 1:N (BehaviorModelIR puede tener múltiples Invariants)

### APPLIES_TO (Invariant → Entity)

```cypher
(Invariant)-[:APPLIES_TO {
    scope: string,             -- "pre-condition" | "post-condition" | "global"
    created_at: datetime
}]->(Entity)
```

**Cardinality**: N:1 (múltiples Invariants pueden aplicar a la misma Entity)

### CHECKS_ATTRIBUTE (Invariant → Attribute)

```cypher
(Invariant)-[:CHECKS_ATTRIBUTE {
    expression: string,        -- The check expression
    operator: string,          -- ">=", "==", "<", "!=", "IN", etc.
    created_at: datetime
}]->(Attribute)
```

**Cardinality**: N:M (Invariants pueden verificar múltiples Attributes)

---

## Inference Strategies

### Step → Entity Inference

```python
def infer_step_targets_entity(step: Step, entities: List[Entity]) -> Optional[Entity]:
    """
    Strategies (in order of confidence):
    1. Explicit: step.target_entity matches entity.name (confidence: 1.0)
    2. Action Semantic: "create Product" → Product entity (confidence: 0.9)
    3. Description Analysis: NLP on step.description (confidence: 0.7)
    """

    # Strategy 1: Explicit match
    if step.target_entity:
        entity = find_entity_by_name(step.target_entity, entities)
        if entity:
            return {"entity": entity, "confidence": 1.0, "method": "explicit"}

    # Strategy 2: Action semantic parsing
    # Pattern: "{verb} {Entity}" → e.g., "create Order", "update Product"
    action_entity = parse_action_entity(step.action, entities)
    if action_entity:
        return {"entity": action_entity, "confidence": 0.9, "method": "action_semantic"}

    # Strategy 3: Description NLP
    description_entity = extract_entity_from_description(step.description, entities)
    if description_entity:
        return {"entity": description_entity, "confidence": 0.7, "method": "description_analysis"}

    return None
```

### Step → Endpoint Inference

```python
def infer_step_calls_endpoint(step: Step, endpoints: List[Endpoint]) -> List[Endpoint]:
    """
    Strategies:
    1. Action → HTTP Method mapping
       - "create" → POST
       - "update" → PUT/PATCH
       - "delete" → DELETE
       - "read/get/fetch" → GET

    2. Entity → Endpoint path matching
       - step.target_entity = "Product" → /products/*
    """

    results = []

    # Get target entity from step
    target = step.target_entity or extract_entity_from_action(step.action)

    # Map action to HTTP method
    method_map = {
        "create": ["POST"],
        "update": ["PUT", "PATCH"],
        "delete": ["DELETE"],
        "read": ["GET"],
        "get": ["GET"],
        "fetch": ["GET"],
        "list": ["GET"],
    }

    action_verb = step.action.split()[0].lower()
    expected_methods = method_map.get(action_verb, [])

    # Find matching endpoints
    for endpoint in endpoints:
        if matches_entity_path(endpoint.path, target):
            if not expected_methods or endpoint.method.value in expected_methods:
                results.append({
                    "endpoint": endpoint,
                    "confidence": 0.85,
                    "method": "action_matching"
                })

    return results
```

### Invariant → Entity Inference

```python
def infer_invariant_applies_to(invariant: Invariant, entities: List[Entity]) -> Entity:
    """
    Simple: invariant.entity directly references entity name
    """
    return find_entity_by_name(invariant.entity, entities)
```

### Invariant → Attribute Inference

```python
def infer_invariant_checks_attribute(invariant: Invariant, entity: Entity) -> List[Attribute]:
    """
    Parse expression to find attribute references:
    - "balance >= 0" → balance attribute
    - "status IN ['active', 'pending']" → status attribute
    - "price > 0 AND quantity > 0" → price, quantity attributes
    """

    # Extract attribute names from expression
    attribute_names = parse_expression_attributes(invariant.expression)

    results = []
    for attr_name in attribute_names:
        attr = find_attribute_by_name(attr_name, entity.attributes)
        if attr:
            operator = extract_operator_for_attribute(invariant.expression, attr_name)
            results.append({
                "attribute": attr,
                "operator": operator,
                "expression": extract_subexpression(invariant.expression, attr_name)
            })

    return results
```

---

## Migration Plan

### Migration 009: Expand BehaviorModelIR Structure

1. Create HAS_BEHAVIOR_MODEL relationships (ApplicationIR → BehaviorModelIR)
2. Load Flow data from JSON legacy and create Flow nodes
3. Create HAS_FLOW relationships
4. Load Step data and create Step nodes
5. Create HAS_STEP relationships with sequence
6. Add temporal metadata to all new nodes

### Migration 010: Create Cross-IR Relationships

1. Infer and create TARGETS_ENTITY (Step → Entity)
2. Infer and create CALLS_ENDPOINT (Step → Endpoint)
3. Load Invariant data and create Invariant nodes
4. Create HAS_INVARIANT relationships
5. Create APPLIES_TO (Invariant → Entity)
6. Infer and create CHECKS_ATTRIBUTE (Invariant → Attribute)

---

## Validation Queries

```cypher
-- Query 1: BehaviorModelIR without flows
MATCH (b:BehaviorModelIR)
WHERE NOT (b)-[:HAS_FLOW]->(:Flow)
RETURN count(b) as empty_behavior_models;

-- Query 2: Flows without steps
MATCH (f:Flow)
WHERE NOT (f)-[:HAS_STEP]->(:Step)
RETURN count(f) as empty_flows;

-- Query 3: Steps without TARGETS_ENTITY
MATCH (s:Step)
WHERE s.target_entity IS NOT NULL
  AND NOT (s)-[:TARGETS_ENTITY]->(:Entity)
RETURN count(s) as unlinked_steps;

-- Query 4: Invariants without APPLIES_TO
MATCH (i:Invariant)
WHERE NOT (i)-[:APPLIES_TO]->(:Entity)
RETURN count(i) as orphan_invariants;

-- Query 5: Coverage metrics
MATCH (s:Step)
OPTIONAL MATCH (s)-[:TARGETS_ENTITY]->(e:Entity)
WITH count(s) as total_steps, count(e) as linked_steps
RETURN total_steps, linked_steps,
       round(100.0 * linked_steps / total_steps, 2) as coverage_percent;
```

---

## Exit Criteria

- [ ] HAS_BEHAVIOR_MODEL relationships created for all ApplicationIR
- [ ] Flow nodes created with all properties
- [ ] Step nodes created with sequence order
- [ ] TARGETS_ENTITY coverage >= 70% for Steps with target_entity
- [ ] CALLS_ENDPOINT relationships created where inferable
- [ ] Invariant nodes created with all properties
- [ ] APPLIES_TO relationships 100% coverage
- [ ] CHECKS_ATTRIBUTE relationships where expression exists
- [ ] All new nodes have temporal metadata
- [ ] Schema version updated to 5

---

*Sprint 3 Edge Design - Approved for Implementation*
