# Phase 5: DAG Construction

**Purpose**: Construct final execution DAG from atomic units and validate it

**Status**: ✅ Core (Required)

---

## Overview

Phase 5 takes atomic units from Phase 4 and constructs the final Directed Acyclic Graph (DAG) that defines the execution order and dependencies for code generation. This ensures no circular dependencies and enables proper parallelization.

## Input

- **Source**: Atomic units from Phase 4
- **Contains**: Atomic units with dependencies and wave assignments

## Processing

```python
async def _phase_5_dag_construction(self):
    # 1. Create DAG nodes from atomic units
    nodes = [{"id": atom.id, "name": atom.name} for atom in atomic_units]

    # 2. Create DAG edges from dependencies
    edges = [{"from": dep, "to": atom.id} for atom, dep in dependencies]

    # 3. Validate no cycles
    dag = {
        "nodes": nodes,
        "edges": edges,
        "waves": wave_organization
    }

    # 4. Validate contract
    validate_dag_contract(dag)
```

## Output

### Execution DAG

```python
class ExecutionDAG:
    nodes: List[Node]           # Atomic units as nodes
    edges: List[Edge]           # Dependency relationships
    waves: List[List[Node]]     # Execution waves (3-8)
    valid: bool                 # DAG validation result
    has_cycles: bool            # Cycle detection result
    max_depth: int              # Longest dependency chain
```

### Node Structure

```python
class Node:
    id: str                     # Atom ID
    name: str                   # Atom name
    complexity: float           # Complexity 0.0-1.0
    loc_estimate: int           # ~10-30 LOC
    wave: int                   # Execution wave (1-8)
    dependencies: List[str]     # IDs of dependent nodes
```

## DAG Validation

```python
# Validate no circular dependencies
cycles = detect_cycles(edges)
if cycles:
    raise ValueError("Circular dependencies detected")

# Validate all edges point to existing nodes
for edge in edges:
    assert edge.from_id in node_ids
    assert edge.to_id in node_ids

# Validate wave ordering
for i, wave in enumerate(waves):
    for node in wave:
        for dep in node.dependencies:
            assert find_wave(dep) < i
```

## Service Dependencies

### Required
- **DAGBuilder** (`src/cognitive/planning/dag_builder.py`)
  - DAG construction
  - Cycle detection
  - Wave generation
  - Topological validation

### Optional
- None

## Execution Wave Structure

```
Wave 1: Base infrastructure (no dependencies)
  ├─ Node 1.1: Create database connection
  ├─ Node 1.2: Define base models
  └─ Node 1.3: Create ORM schema

Wave 2: Depends only on Wave 1
  ├─ Node 2.1: Create API router
  ├─ Node 2.2: Implement CRUD handlers
  └─ Node 2.3: Add authentication middleware

Wave 3: Depends on Waves 1-2
  ├─ Node 3.1: Add validation logic
  ├─ Node 3.2: Implement business rules
  └─ Node 3.3: Add error handling

Wave 4+: Progressive composition
```

## Cycle Detection Algorithm

```python
def detect_cycles(edges):
    # Use DFS (Depth-First Search) to find cycles
    visited = set()
    rec_stack = set()
    cycles = []

    for node in nodes:
        if not visited[node]:
            cycles.extend(dfs(node, visited, rec_stack))

    return cycles
```

## Performance Characteristics

- **Time**: ~0.5-2 seconds
- **Memory**: ~50-150 MB
- **Computation**: Topological sort, cycle detection

## Metrics Collected

- DAG validity status
- Node count
- Edge count
- Wave count
- Maximum dependency depth
- Cycle count (should be 0)
- Parallelization ratio

## Data Flow

```
Atomic Units with Dependencies
    ↓
    └─ DAGBuilder.build()
        ├─ Create nodes from atoms
        ├─ Create edges from dependencies
        ├─ Detect cycles
        └─ Organize into waves
            ↓
        Final ExecutionDAG
            ├─ Valid: Yes/No
            ├─ Cycles: 0
            └─ Waves: 3-8
                ↓
                Feeds to Phase 6 (Code Generation)
```

## Validation Contract

```python
DAG Contract:
    nodes: List[Node]               ✓
    edges: List[Edge]               ✓
    waves: List[List[Node]]         ✓
    wave_count: 3-8                 ✓
    is_valid: True                  ✓
    has_cycles: False               ✓
```

## Integration Points

- **Phase 4**: Receives atomic units
- **Phase 6**: Sends DAG for parallelized code generation
- **Phase 7**: Uses wave structure for validation
- **Metrics**: DAG statistics, parallelization metrics

## Success Criteria

✅ DAG constructed with all atoms as nodes
✅ Dependencies properly represented as edges
✅ No circular dependencies detected
✅ Organized into 3-8 execution waves
✅ Wave ordering respects dependencies
✅ Contract validation passed

## Typical DAG Output

```
DAG Summary:
  Nodes: 382
  Edges: 287
  Valid DAG: Yes
  Cycles Detected: 0

Wave Structure:
  Wave 1: 68 nodes (0 dependencies, can start immediately)
  Wave 2: 78 nodes (depend on Wave 1)
  Wave 3: 71 nodes (depend on Waves 1-2)
  Wave 4: 85 nodes (depend on Waves 1-3)
  Wave 5: 54 nodes (depend on Waves 1-4)
  Wave 6: 26 nodes (depend on all previous)

Execution Characteristics:
  Maximum dependency chain: 6 nodes
  Critical path: 6 sequential steps
  Parallelizable nodes: 315 (82%)
  Sequential-only nodes: 67 (18%)

Estimated Execution Time:
  - Sequential: ~382 * 5 seconds = 31 minutes
  - Parallelized (5 concurrent): ~150 seconds = 2.5 minutes
  - Speedup: 12.4x
```

## Known Limitations

- ⚠️ Assumes all nodes can be generated independently
- ⚠️ Shared state/dependencies not represented
- ⚠️ External API calls not modeled
- ⚠️ Resource constraints not considered

## Fallback Behavior

If cycle detected:
1. Attempt cycle breaking (reorder nodes)
2. If fails, flatten graph (sequential execution)
3. Log warnings and continue
4. Code generation proceeds without parallelization

## Common Cycle Scenarios

```
Example Cycle (INVALID):
  User (F1) ──> Profile (F2) ──> User (F1)   ❌ Circular!

Solution:
  User (F1) ──> Profile (F2)
  Profile references User, but doesn't create circular edge in DAG
```

## Next Phase

Output feeds to **Phase 6: Code Generation** which:
- Uses DAG waves for parallelized code generation
- Generates code for each atom
- Combines atoms into complete project files

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:1375-1404
**Status**: Verified ✅
