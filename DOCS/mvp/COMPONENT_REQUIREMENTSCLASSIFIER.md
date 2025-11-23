# Component: RequirementsClassifier

**Module**: `src/classification/requirements_classifier.py`
**Phase**: 2 (Requirements Analysis)
**Status**: ✅ Core Required Component

---

## Purpose

RequirementsClassifier takes flat requirement lists and organizes them semantically by:
- Domain categorization (auth, CRUD, UI, infrastructure, etc.)
- Type classification (functional vs non-functional)
- Priority assignment (critical, high, medium, low)
- Dependency relationship building

It transforms unordered requirements into a structured, analyzable graph for planning.

## Role in Pipeline

```
Input: SpecRequirements from Phase 1
    ↓
[RequirementsClassifier]
├─ classify_batch() → ClassifiedRequirement[]
├─ build_dependency_graph() → DependencyGraph
└─ validate_dag() → bool
    ↓
Output: ClassifiedRequirement[] + DependencyGraph
    ↓
Consumed by: Phase 3 (MultiPassPlanner)
```

## Key Methods

### Method 1: `classify_batch(requirements: List[Requirement]) → List[ClassifiedRequirement]`

**Purpose**: Classify requirements by domain, type, and priority

**Input**:
```python
requirements: List[Requirement]  # From SpecParser output
```

**Output**:
```python
List[ClassifiedRequirement] = [
    ClassifiedRequirement {
        id: "F1",
        description: "User registration",
        type: "functional",
        domain: "auth",
        priority: "high",
        complexity: 2,
        risk_level: "low",
        dependencies: ["NF1"]
    },
    ...
]
```

**Usage in Pipeline** (Phase 2, line 807-809):
```python
self.classified_requirements = self.requirements_classifier.classify_batch(
    self.spec_requirements.requirements
)
```

### Method 2: `build_dependency_graph(requirements: List[ClassifiedRequirement]) → DependencyGraph`

**Purpose**: Build directed acyclic graph showing requirement dependencies

**Output**:
```python
DependencyGraph {
    nodes: List[Requirement],      # All requirements
    edges: List[Dependency],       # Requirement → Requirement relationships
    layers: List[List[Requirement]]  # Execution layers (no internal deps)
}
```

**Usage in Pipeline** (Phase 2, line 812-814):
```python
self.dependency_graph = self.requirements_classifier.build_dependency_graph(
    self.classified_requirements
)
```

### Method 3: `validate_dag(graph: DependencyGraph) → bool`

**Purpose**: Validate that dependency graph is a valid DAG (no cycles)

**Returns**: `True` if valid DAG, `False` if contains cycles

**Usage in Pipeline** (Phase 2, line 817):
```python
is_valid_dag = self.requirements_classifier.validate_dag(self.dependency_graph)
```

## Classification Schema

### Domain Categories

| Domain | Examples | Priority Weight |
|--------|----------|-----------------|
| **auth** | Login, password reset, 2FA | High (foundational) |
| **crud** | Create, read, update, delete entities | High (core functionality) |
| **ui** | Forms, dashboards, components | Medium (user experience) |
| **api** | REST endpoints, middleware | High (interface) |
| **validation** | Input validation, constraints | Medium (quality) |
| **infrastructure** | Database, caching, logging | Medium (reliability) |
| **workflow** | State machines, business logic | High (correctness) |
| **integration** | External services, webhooks | Medium (extensibility) |

### Type Classification

```python
type = "functional" | "non_functional"

# Functional: Requirements for what system must DO
# Examples: "User can login", "Create task with title"

# Non-functional: Requirements for HOW system should behave
# Examples: "Response time < 200ms", "99.9% uptime"
```

### Priority Levels

```python
priority = "critical" | "high" | "medium" | "low"

# Critical: System cannot function without
# Example: Database connectivity

# High: Core feature functionality
# Example: User authentication

# Medium: Important but can work without
# Example: Email notifications

# Low: Nice-to-have enhancements
# Example: User theme preferences
```

### Complexity Scoring

```python
complexity: int  # 1-5 scale

# 1: Trivial (simple field, no logic)
# 2: Simple (basic CRUD operation)
# 3: Moderate (complex logic, multiple steps)
# 4: Complex (involves multiple systems, workflow)
# 5: Very Complex (distributed, highly coupled)
```

## Sample Classification Output

```python
ClassifiedRequirement {
    id: "F1",
    description: "User can register with email and password",
    type: "functional",
    domain: "auth",
    priority: "critical",
    complexity: 2,
    risk_level: "low",
    related_entities: ["User"],
    related_endpoints: ["POST /api/users"],
    dependencies: ["NF1"]  # Depends on password hashing requirement
}

ClassifiedRequirement {
    id: "F2",
    description: "User can login",
    type: "functional",
    domain: "auth",
    priority: "critical",
    complexity: 2,
    risk_level: "low",
    related_entities: ["User"],
    related_endpoints: ["POST /api/auth/login"],
    dependencies: ["F1"]  # Depends on user registration
}

ClassifiedRequirement {
    id: "F3",
    description: "User can create task",
    type: "functional",
    domain: "crud",
    priority: "high",
    complexity: 2,
    risk_level: "low",
    related_entities: ["Task", "User"],
    related_endpoints: ["POST /api/tasks"],
    dependencies: ["F1"]  # User must exist
}

ClassifiedRequirement {
    id: "F4",
    description: "Task status follows workflow",
    type: "functional",
    domain: "workflow",
    priority: "high",
    complexity: 3,
    risk_level: "medium",
    related_entities: ["Task"],
    related_endpoints: ["PATCH /api/tasks/{id}"],
    dependencies: ["F3"]  # Task must exist first
}

ClassifiedRequirement {
    id: "NF1",
    description: "Passwords must be hashed",
    type: "non_functional",
    domain: "auth",
    priority: "critical",
    complexity: 1,
    risk_level: "high",
    related_components: ["User model", "Password hashing library"],
    dependencies: []
}
```

## Dependency Graph Structure

### Example Graph

```
F1: User registration
    ↓
F2: User login
    ↓
F3: Create task
    ↓
F4: Task status workflow
    ├─→ F5: Update task
    └─→ F6: Delete task

Dependencies:
- F1 has no dependencies
- F2 depends on F1
- F3 depends on F1
- F4 depends on F3
- F5 depends on F3
- F6 depends on F3
```

### Valid DAG Check

```python
# Valid DAG - no circular dependencies
F1 → F2 → F3 → F4 ✅

# Invalid - has cycle
F1 → F2
↑    ↓
└─── F3 ❌
```

## Metrics Collected

In Phase 2 (line 833-847):
```python
metrics_collector.add_checkpoint("requirements_analysis", "CP-2.X", {
    "total_requirements": len(self.classified_requirements),
    "functional": len(functional_reqs),
    "non_functional": len(non_functional_reqs),
    "dependency_graph_nodes": len(self.dependency_graph),
    "valid_dag": is_valid_dag,
    "domain_distribution": domain_counts
})
```

Example metrics:
```
Total requirements: 25
Functional: 18
Non-functional: 7
Dependency graph nodes: 25
Valid DAG: true
Domain distribution:
  - auth: 3
  - crud: 8
  - ui: 2
  - validation: 4
  - workflow: 5
  - infrastructure: 3
```

## Integration Points

### Input from
- Phase 1: SpecParser (SpecRequirements object)

### Output to
- Phase 3: MultiPassPlanner (ClassifiedRequirement[] + DependencyGraph)
- Throughout: Metrics collector

### Produces
- ClassifiedRequirement[] array
- DependencyGraph object
- Domain distribution metrics
- Validation status

## Domain Distribution Analysis

**Example from Phase 2**:
```
Domain: auth        Count: 3
Domain: crud        Count: 8
Domain: validation  Count: 4
Domain: workflow    Count: 5
Domain: ui          Count: 2
Domain: infra       Count: 3
```

## Error Handling

### Circular Dependencies
```python
if not validate_dag(dependency_graph):
    raise ValueError("Circular dependency detected in requirements")
```

### Missing Dependency
```python
if req.depends_on("F999") and "F999" not in all_requirements:
    warnings.warn(f"Requirement {req.id} depends on missing F999")
```

### Invalid Classification
```python
if domain not in VALID_DOMAINS:
    warnings.warn(f"Unknown domain '{domain}', defaulting to 'api'")
```

## Usage Example

```python
from src.classification.requirements_classifier import RequirementsClassifier

# Initialize classifier
classifier = RequirementsClassifier()

# Classify batch of requirements
classified = classifier.classify_batch(spec_requirements.requirements)

# Build dependency graph
graph = classifier.build_dependency_graph(classified)

# Validate DAG
is_valid = classifier.validate_dag(graph)

# Analyze results
functional = [r for r in classified if r.type == "functional"]
by_domain = {}
for req in classified:
    if req.domain not in by_domain:
        by_domain[req.domain] = []
    by_domain[req.domain].append(req)

print(f"Functional requirements: {len(functional)}")
for domain, reqs in by_domain.items():
    print(f"  {domain}: {len(reqs)} requirements")
```

## Performance Characteristics

- **Time**: ~500ms - 2s (depending on requirement count)
- **Memory**: ~20-50 MB (graph in memory)
- **Computation**: O(n²) for dependency graph building
- **Complexity**: Quadratic with requirement count

## Success Criteria

✅ All requirements classified by domain
✅ All requirements typed (functional/non-functional)
✅ Priority assigned to each requirement
✅ Dependencies identified correctly
✅ Dependency graph built
✅ No circular dependencies
✅ Valid DAG confirmed
✅ Metrics collected

## Typical Output

```
Phase 2: Requirements Analysis (Enhanced with RequirementsClassifier)
  ✓ Semantic classification completed
    - Total requirements classified: 25
    - Functional requirements: 18
    - Non-functional requirements: 7
    - Dependency graph nodes: 25
    - Valid DAG: true

  ✓ Domain distribution:
    - auth: 3
    - crud: 8
    - validation: 4
    - workflow: 5
    - ui: 2
    - infrastructure: 3
```

## Known Limitations

- ⚠️ Classification heuristics may not match domain exactly
- ⚠️ Dependency inference may miss implicit relationships
- ⚠️ Complex workflows may be oversimplified
- ⚠️ Priority assignment is heuristic-based

## Next Component

Output (ClassifiedRequirement[] + DependencyGraph) feeds to **Phase 3: MultiPassPlanner** which:
- Creates comprehensive task plan
- Organizes requirements into execution waves
- Identifies parallelizable tasks
- Sequences dependent tasks correctly

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:807-847
**Status**: Verified ✅
