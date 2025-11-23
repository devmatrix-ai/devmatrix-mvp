# Phase 3: Graph-Based Entity Relationship Inference

## Executive Summary

**Objective**: Achieve 100% validation coverage (62/62 validations) by inferring missing validations through entity relationship graphs.

**Approach**: Build semantic graph of entities, relationships, and constraints. Use graph analysis to infer:
- Cross-entity relationship constraints
- Workflow state transitions
- Implicit business rules from relationships
- Missing uniqueness and foreign key constraints

**Expected Results**:
- **Coverage**: 62/62 validations (100%)
- **Improvement**: +2-5 additional validations vs Phase 2
- **Cost**: ~$0.002/spec (minimal)
- **Complexity**: Medium (graph construction + inference)

**Timeline**: 1-2 weeks

---

## Current State Analysis

### Phase 1: Pattern-Based Extraction
```
Input: Specification (YAML/JSON)
Process:
  - Load 8 pattern categories (type, semantic, constraint, endpoint, domain, relationship, workflow, implicit)
  - Match fields against patterns
  - Apply confidence scoring
  - Deduplicate by (entity, attribute, type)
Output: 45 validations detected
Coverage: 73% (45/62)
Cost: ~$0.01/spec
```

**Detects**: Type validations, semantic patterns, basic constraints, endpoint validations

**Misses**:
- Relationship-dependent validations
- Workflow-specific constraints
- Business rule implications
- Transitive relationship constraints

### Phase 2: LLM-Primary Extraction
```
Input: Specification + Phase 1 results
Process:
  - 3 specialized LLM prompts (field, endpoint, cross-entity)
  - JSON parsing with fallback mechanisms
  - Retry logic with exponential backoff
  - Confidence scoring per validation
Output: Expected 60-62 validations
Coverage: Expected 97-100% (60-62/62)
Cost: ~$0.11/spec
```

**Detects**: Everything Phase 1 does + LLM-inferred constraints

**Misses**:
- Graph-dependent relationship constraints
- Transitive implications
- Implicit workflow constraints not mentioned in spec text

### Phase 3: Graph-Based Inference (NEW)
```
Input: Specification + Phase 1+2 results + Entity relationships
Process:
  - Build EntityRelationshipGraph from spec
  - Analyze relationship properties (cardinality, direction, constraints)
  - Infer missing constraints through graph traversal
  - Detect implicit business rules
Output: 62 validations (all)
Coverage: 100% (62/62)
Cost: ~$0.002/spec
```

**Detects**: Everything + relationship-derived constraints and implicit rules

**Achieves**: Complete validation coverage

---

## Architecture Design

### 1. Entity Relationship Graph Model

```python
# Node: EntityNode represents a business entity
class EntityNode:
    name: str  # e.g., "Order", "Product", "Customer"
    attributes: Dict[str, Field]
    validation_rules: List[ValidationRule]
    constraints: List[Constraint]

    # Computed properties
    is_aggregate_root: bool  # Is this entity a domain aggregate root?
    domain_context: str  # Bounded context (e-commerce, inventory, user-mgmt)
    lifecycle_states: Optional[List[str]]  # Status values if entity has lifecycle

# Edge: RelationshipEdge represents a relationship between entities
class RelationshipEdge:
    source: str  # Source entity name
    target: str  # Target entity name
    type: str  # "one-to-many", "many-to-many", "one-to-one", "composition"
    cardinality: Tuple[str, str]  # ("1", "N"), ("1", "1"), etc.
    direction: str  # "forward", "backward", "bidirectional"

    # Relationship semantics
    foreign_key_field: Optional[str]  # Field containing the relationship
    required: bool  # Is this relationship mandatory?
    cascade_delete: bool  # Delete target when source deleted?
    depends_on: Optional[str]  # Alternative: this relationship depends on another

    # Derived constraints
    implied_constraints: List[ImpliedConstraint]
    business_rules: List[BusinessRule]

# Constraint: Inferred constraint from relationship analysis
class ImpliedConstraint:
    entity: str
    attribute: str
    type: ValidationType  # PRESENCE, RELATIONSHIP, UNIQUENESS, etc.
    source: str  # "relationship_cascade", "workflow_state", "cardinality", etc.
    condition: str  # Why is this constraint implied?
    confidence: float  # 0.0-1.0 confidence in inference
```

### 2. Graph Construction Algorithm

```python
class EntityRelationshipGraphBuilder:
    """Build semantic graph from specification."""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.graph = nx.DiGraph()  # Directed graph
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: List[RelationshipEdge] = []

    def build(self) -> EntityRelationshipGraph:
        """Build complete graph from spec."""
        # Step 1: Create nodes for each entity
        self._create_entity_nodes()

        # Step 2: Create edges for relationships
        self._create_relationship_edges()

        # Step 3: Analyze cardinality and constraints
        self._analyze_cardinality()

        # Step 4: Detect aggregate roots and boundaries
        self._detect_aggregate_roots()

        # Step 5: Analyze workflow states
        self._analyze_workflows()

        # Step 6: Compute transitive relationships
        self._compute_transitive_relationships()

        return EntityRelationshipGraph(
            nodes=self.nodes,
            edges=self.edges,
            graph=self.graph
        )

    def _create_entity_nodes(self):
        """Create EntityNode for each entity in spec."""
        for entity_name, entity_spec in self.spec.get("entities", {}).items():
            node = EntityNode(
                name=entity_name,
                attributes=entity_spec.get("attributes", {}),
                validation_rules=[],
                constraints=entity_spec.get("constraints", [])
            )
            self.nodes[entity_name] = node
            self.graph.add_node(entity_name, entity=node)

    def _create_relationship_edges(self):
        """Create RelationshipEdge for each relationship."""
        # Extract from "relationships" section
        for rel in self.spec.get("relationships", []):
            edge = RelationshipEdge(
                source=rel["from"],
                target=rel["to"],
                type=rel.get("type", "one-to-many"),
                cardinality=rel.get("cardinality", ("1", "N")),
                direction=rel.get("direction", "forward"),
                foreign_key_field=rel.get("foreign_key"),
                required=rel.get("required", False),
                cascade_delete=rel.get("cascade_delete", False)
            )
            self.edges.append(edge)
            self.graph.add_edge(rel["from"], rel["to"], relationship=edge)

    def _analyze_cardinality(self):
        """Analyze cardinality constraints."""
        for edge in self.edges:
            # One-to-many: target must have foreign key to source
            if edge.type == "one-to-many":
                target_node = self.nodes[edge.target]
                # Infer: foreign_key field should be present and required
                edge.implied_constraints.append(
                    ImpliedConstraint(
                        entity=edge.target,
                        attribute=edge.foreign_key_field,
                        type=ValidationType.PRESENCE,
                        source="one-to-many_cardinality",
                        condition=f"Foreign key to {edge.source} required by cardinality",
                        confidence=0.95
                    )
                )

            # Many-to-many: requires junction entity
            elif edge.type == "many-to-many":
                edge.implied_constraints.append(
                    ImpliedConstraint(
                        entity=edge.target,
                        attribute=edge.foreign_key_field,
                        type=ValidationType.RELATIONSHIP,
                        source="many-to-many_cardinality",
                        condition="Many-to-many relationship via junction entity",
                        confidence=0.9
                    )
                )

    def _detect_aggregate_roots(self):
        """Detect aggregate roots (high out-degree nodes)."""
        # Aggregate roots have many outgoing relationships
        for node_name in self.graph.nodes():
            out_degree = self.graph.out_degree(node_name)
            in_degree = self.graph.in_degree(node_name)

            # Heuristic: out-degree > in-degree = likely aggregate root
            node = self.nodes[node_name]
            node.is_aggregate_root = out_degree > in_degree

    def _analyze_workflows(self):
        """Extract workflow states and transitions."""
        for entity_name, entity in self.nodes.items():
            # Look for status/state fields
            for attr_name, attr_spec in entity.attributes.items():
                if any(kw in attr_name.lower() for kw in ["status", "state", "stage"]):
                    # Extract allowed states
                    states = attr_spec.get("allowed_values", [])
                    entity.lifecycle_states = states

                    # Infer: status field should be present and constrained
                    entity.validation_rules.append(
                        ValidationRule(
                            entity=entity_name,
                            attribute=attr_name,
                            type=ValidationType.STATUS_TRANSITION,
                            condition=f"Status must be one of: {', '.join(states)}",
                            error_message=f"Invalid status for {entity_name}"
                        )
                    )

    def _compute_transitive_relationships(self):
        """Find paths between entities (transitive relationships)."""
        # For all pairs of nodes, compute shortest path
        # This reveals implicit dependencies
        for source in self.graph.nodes():
            for target in self.graph.nodes():
                if source != target:
                    try:
                        path = nx.shortest_path(self.graph, source, target)
                        if len(path) > 2:  # Transitive (more than direct edge)
                            # Path: A -> B -> C means C implicitly depends on A
                            # Add constraint: if relationship to B, then A must exist
                            self._infer_transitive_constraint(path)
                    except nx.NetworkXNoPath:
                        pass
```

### 3. Constraint Inference Engine

```python
class ConstraintInferenceEngine:
    """Infer missing validation constraints from graph."""

    def __init__(self, graph: EntityRelationshipGraph):
        self.graph = graph
        self.inferred_constraints: List[ValidationRule] = []

    def infer_all_constraints(self) -> List[ValidationRule]:
        """Infer all missing constraints."""
        # Type 1: Cardinality constraints
        self.inferred_constraints.extend(self._infer_cardinality_constraints())

        # Type 2: Uniqueness constraints
        self.inferred_constraints.extend(self._infer_uniqueness_constraints())

        # Type 3: Workflow state transitions
        self.inferred_constraints.extend(self._infer_workflow_constraints())

        # Type 4: Cross-entity business rules
        self.inferred_constraints.extend(self._infer_business_rules())

        # Type 5: Implicit presence constraints
        self.inferred_constraints.extend(self._infer_presence_constraints())

        # Type 6: Relationship direction constraints
        self.inferred_constraints.extend(self._infer_relationship_constraints())

        return self.inferred_constraints

    def _infer_cardinality_constraints(self) -> List[ValidationRule]:
        """Infer constraints from relationship cardinality."""
        rules = []
        for edge in self.graph.edges:
            # For one-to-many relationships
            if edge.cardinality[1] == "N":  # Many side
                rules.append(
                    ValidationRule(
                        entity=edge.target,
                        attribute=edge.foreign_key_field,
                        type=ValidationType.PRESENCE,
                        condition=f"Must reference {edge.source}",
                        error_message=f"Foreign key to {edge.source} is required",
                        confidence=0.95
                    )
                )
        return rules

    def _infer_uniqueness_constraints(self) -> List[ValidationRule]:
        """Infer uniqueness from natural identifiers."""
        rules = []
        for entity_name, node in self.graph.nodes.items():
            # Infer: Primary keys should be unique
            for attr_name, attr_spec in node.attributes.items():
                if attr_spec.get("is_primary_key"):
                    rules.append(
                        ValidationRule(
                            entity=entity_name,
                            attribute=attr_name,
                            type=ValidationType.UNIQUENESS,
                            condition="Primary key must be unique",
                            error_message=f"{attr_name} must be unique",
                            confidence=0.99
                        )
                    )
        return rules

    def _infer_workflow_constraints(self) -> List[ValidationRule]:
        """Infer constraints from workflow state transitions."""
        rules = []
        for entity_name, node in self.graph.nodes.items():
            if node.lifecycle_states:
                # Infer valid state transitions
                rules.append(
                    ValidationRule(
                        entity=entity_name,
                        attribute=node._get_status_field(),
                        type=ValidationType.STATUS_TRANSITION,
                        condition=f"Valid transitions: {self._compute_valid_transitions(node)}",
                        error_message="Invalid state transition",
                        confidence=0.85
                    )
                )
        return rules

    def _infer_business_rules(self) -> List[ValidationRule]:
        """Infer business rules from relationship semantics."""
        rules = []

        # Rule 1: Cascade delete implies order dependency
        for edge in self.graph.edges:
            if edge.cascade_delete:
                rules.append(
                    ValidationRule(
                        entity=edge.target,
                        attribute="deletion_rule",
                        type=ValidationType.WORKFLOW_CONSTRAINT,
                        condition=f"Cannot delete {edge.target} if {edge.source} still exists",
                        error_message=f"Delete {edge.source} first",
                        confidence=0.9
                    )
                )

        # Rule 2: Aggregate root owns entities
        for entity_name, node in self.graph.nodes.items():
            if node.is_aggregate_root:
                # Infer: entities in aggregate must reference root
                for outgoing in self.graph.graph.out_edges(entity_name):
                    target_entity = outgoing[1]
                    rules.append(
                        ValidationRule(
                            entity=target_entity,
                            attribute=f"{entity_name.lower()}_id",
                            type=ValidationType.PRESENCE,
                            condition=f"{target_entity} is part of {entity_name} aggregate",
                            error_message=f"Must belong to {entity_name}",
                            confidence=0.88
                        )
                    )

        return rules

    def _infer_presence_constraints(self) -> List[ValidationRule]:
        """Infer presence constraints from relationships."""
        rules = []
        for edge in self.graph.edges:
            if edge.required:
                rules.append(
                    ValidationRule(
                        entity=edge.source,
                        attribute=edge.foreign_key_field,
                        type=ValidationType.PRESENCE,
                        condition="Required relationship",
                        error_message=f"Must have {edge.target}",
                        confidence=0.92
                    )
                )
        return rules

    def _infer_relationship_constraints(self) -> List[ValidationRule]:
        """Infer constraints from relationship properties."""
        rules = []
        for edge in self.graph.edges:
            rules.append(
                ValidationRule(
                    entity=edge.target,
                    attribute=edge.foreign_key_field,
                    type=ValidationType.RELATIONSHIP,
                    condition=f"Must reference {edge.source}",
                    error_message=f"Invalid {edge.source} reference",
                    confidence=0.93
                )
            )
        return rules
```

### 4. Integration with Validation Pipeline

```python
# Modify BusinessLogicExtractor to include Phase 3

class BusinessLogicExtractor:

    def extract_validations(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Extract validations from spec using all 3 phases."""

        # Phase 1: Pattern-based extraction
        phase1_rules = self._extract_pattern_rules(spec)

        # Phase 2: LLM-based extraction
        phase2_rules = self._extract_llm_rules(spec)

        # NEW: Phase 3: Graph-based inference
        phase3_rules = self._extract_graph_rules(spec)

        # Merge all validations
        all_rules = phase1_rules + phase2_rules + phase3_rules

        # Deduplicate by (entity, attribute, type) + relationship context
        deduplicated = self._deduplicate_with_context(all_rules)

        return deduplicated

    def _extract_graph_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """NEW: Extract validations from entity relationship graph."""
        # Step 1: Build entity relationship graph
        graph_builder = EntityRelationshipGraphBuilder(spec)
        graph = graph_builder.build()

        # Step 2: Infer constraints from graph
        inference_engine = ConstraintInferenceEngine(graph)
        graph_rules = inference_engine.infer_all_constraints()

        # Step 3: Filter and score
        # Only keep rules with confidence > 0.70
        filtered_rules = [r for r in graph_rules if r.confidence > 0.70]

        return filtered_rules

    def _deduplicate_with_context(self, all_rules: List[ValidationRule]) -> List[ValidationRule]:
        """Deduplicate considering relationship context."""
        # Key: (entity, attribute, type, source_relationship)
        seen = {}

        for rule in sorted(all_rules, key=lambda r: r.confidence, reverse=True):
            key = (rule.entity, rule.attribute, rule.type)

            if key not in seen:
                seen[key] = rule
            else:
                # Keep rule with highest confidence
                existing = seen[key]
                if rule.confidence > existing.confidence:
                    seen[key] = rule

        return list(seen.values())
```

---

## Implementation Plan

### Week 1: Design & Setup (Days 1-3)
```
[ ] Create EntityNode and RelationshipEdge dataclasses
[ ] Implement EntityRelationshipGraphBuilder
[ ] Create test specs with known relationships
[ ] Add graph visualization utility (for debugging)
```

### Week 1: Inference Engine (Days 4-5)
```
[ ] Implement ConstraintInferenceEngine
[ ] Implement cardinality constraint inference
[ ] Implement uniqueness constraint inference
[ ] Implement workflow state constraint inference
[ ] Implement business rule inference
```

### Week 2: Integration (Days 6-8)
```
[ ] Integrate Phase 3 into BusinessLogicExtractor pipeline
[ ] Implement deduplication with relationship context
[ ] Add confidence scoring calibration
[ ] Test Phase 1 + 2 + 3 combined
```

### Week 2: Testing & Validation (Days 9-10)
```
[ ] Create E2E tests for Phase 3
[ ] Measure coverage improvement: 60-62 → 62/62
[ ] Validate false positive rate (<5%)
[ ] Optimize inference performance
```

---

## Testing Strategy

### Test Case 1: E-commerce Spec (Known)
```yaml
Entities: 4 (User, Product, Order, OrderItem)
Relationships: 5 (User→Order, Product→OrderItem, Order→OrderItem, etc.)
Expected Phase 3 Detections: +2 validations
- Cascade delete constraint: OrderItem deleted when Order deleted
- Aggregate root constraint: OrderItem must belong to Order
Result: Expected 62/62 (100%)
```

### Test Case 2: Inventory System
```yaml
Entities: 6 (Warehouse, StockLevel, Product, Category, Supplier, Purchase)
Relationships: 8 (complex)
Expected Phase 3 Detections: +3 validations
- Multi-level relationships
- Transitive dependencies
- Business rule implications
```

### Test Case 3: Workflow System
```yaml
Entities: 3 (Task, User, Project)
Relationships: 4 (with state transitions)
Expected Phase 3 Detections: +2 validations
- Workflow state transitions
- Status-dependent constraints
- Role-based visibility rules
```

---

## Success Criteria

✅ **Coverage**: 62/62 validations detected (100%)
✅ **Accuracy**: <5% false positive rate
✅ **Performance**: <1s inference time per spec
✅ **Confidence**: Average confidence > 0.85
✅ **Integration**: Seamless with Phase 1 + 2

---

## Resource Requirements

- **Development Time**: 7-10 days
- **Test Data**: 3-5 complex specs (provided)
- **Dependencies**:
  - NetworkX (graph library) - already available
  - Existing Phase 1 + 2 infrastructure

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Over-inference (false positives) | Set confidence threshold > 0.70 |
| Graph complexity | Use incremental graph building |
| Deduplication conflicts | Prefer highest confidence source |
| Relationship ambiguity | Require explicit relationship definitions |

---

## Next Steps

1. ✅ Create Phase 3 design document (this file)
2. ⏭️ Implement EntityRelationshipGraphBuilder
3. ⏭️ Implement ConstraintInferenceEngine
4. ⏭️ Integrate into BusinessLogicExtractor
5. ⏭️ Run comprehensive E2E tests
6. ⏭️ Validate 100% coverage achievement
7. ⏭️ Create Phase 3 release documentation

---

## Expected Outcome

**Before Phase 3**:
- Phase 1: 45/62 validations (73%)
- Phase 2: 60-62/62 validations (97-100%)
- Combined: Missing cross-entity and graph-derived constraints

**After Phase 3**:
- All three phases working together
- Graph-based inference catches relationship-dependent validations
- **100% coverage: 62/62 validations (100%)**
- Production-ready validation extraction system

This completes the vision of comprehensive, systematic validation discovery without manual specification.
