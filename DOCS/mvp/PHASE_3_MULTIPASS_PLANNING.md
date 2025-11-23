# Phase 3: Multi-Pass Planning

**Purpose**: Break requirements into 100+ task plan, identify dependencies, organize into waves

**Status**: ✅ Optional (Graceful degradation if unavailable)

---

## Overview

Phase 3 takes classified requirements and decomposes them into a detailed task plan with 100-150 atomic tasks. It builds dependency waves showing which tasks can execute in parallel.

## Input

- **Source**: Classified requirements from Phase 2
- **Contains**:
  - Classified requirements with domains, priorities, risks
  - Dependency graph
  - Ground truth DAG (optional)

## Processing

```python
async def _phase_3_multi_pass_planning(self):
    # 1. Get ground truth
    dag_ground_truth = spec_requirements.dag_ground_truth

    # 2. Infer dependencies
    inferred_edges = planner.infer_dependencies_enhanced(
        requirements=classified_requirements,
        dag_ground_truth=dag_ground_truth
    )

    # 3. Build waves from dependencies (Kahn's algorithm)
    waves_data = planner.build_waves_from_edges(
        classified_requirements,
        inferred_edges
    )
```

## Output

### Master Plan

```python
class MasterPlan:
    tasks: List[Task]              # 100-150 atomic tasks
    waves: List[List[Task]]        # Dependency-based execution waves (3-8 waves)
    total_estimated_effort: int    # Estimated lines of code
    phases: Dict[str, List[Task]]  # Grouped by phase (Data, API, Validation, etc.)
```

### Execution Wave Structure

```
Wave 1: Core Data Models
  ├─ Task 1.1: Create User model
  ├─ Task 1.2: Create Task model
  └─ Task 1.3: Create database schema

Wave 2: API Routes (depends on Wave 1)
  ├─ Task 2.1: Create /api/users endpoint
  ├─ Task 2.2: Create /api/tasks endpoint
  └─ Task 2.3: Create /api/auth endpoint

Wave 3: Validation (depends on Wave 1-2)
  ├─ Task 3.1: User email validation
  ├─ Task 3.2: Task title validation
  └─ Task 3.3: Permission validation

Wave 4: Testing (depends on all previous)
  ├─ Task 4.1: Unit tests for models
  ├─ Task 4.2: Integration tests for API
  └─ Task 4.3: End-to-end tests
```

## Service Dependencies

### Required
- **MultiPassPlanner** (`src/cognitive/planning/multi_pass_planner.py`)
  - Requirement decomposition
  - Dependency inference
  - Wave generation (topological sort)
  - Effort estimation

### Optional
- None (part of cognitive services group)

## Planning Phases

| Phase | Tasks | Description |
|-------|-------|-------------|
| **Data Layer** | 15-25 | Models, schema, migrations |
| **API Routes** | 20-35 | Endpoints, request handlers |
| **Validation** | 10-20 | Business logic, constraints |
| **Authentication** | 5-10 | Auth flows, JWT, permissions |
| **Testing** | 20-40 | Unit, integration, E2E tests |
| **Documentation** | 5-10 | API docs, guides, examples |
| **Infrastructure** | 5-15 | Database, caching, deployment |

## Complexity Factors

```python
Task Complexity = Base_Complexity × Domain_Multiplier × Risk_Multiplier

Base: 0.1-1.0 depending on requirement type
Domain multiplier:
  - Simple (CRUD): 1.0
  - Complex (Auth, Payment): 1.5-2.0
Risk multiplier:
  - Low risk: 1.0
  - Medium risk: 1.2
  - High risk: 1.5
```

## Metrics Collected

- Total task count
- Task distribution by phase
- Task distribution by domain
- Wave count
- Parallelization potential
- Estimated total effort (LOC)

## Data Flow

```
Classified Requirements + Dependency Graph
    ↓
    └─ MultiPassPlanner.infer_dependencies_enhanced()
        ├─ Enhanced dependency inference using ground truth
        ├─ Cycle detection and resolution
        └─ Complexity estimation
            ↓
        DAG with Nodes and Edges
            ↓
        MultiPassPlanner.build_waves_from_edges()
            ├─ Topological sort (Kahn's algorithm)
            ├─ Group by execution wave
            └─ Parallelize independent tasks
                ↓
            MasterPlan with Waves
                ↓
                Feeds to Phase 4 (Atomization)
```

## Wave Organization Logic

1. **Wave 1**: No dependencies (data models, base infrastructure)
2. **Wave 2**: Depends only on Wave 1 (API routes, basic handlers)
3. **Wave 3**: Depends on Wave 1-2 (validation, business logic)
4. **Wave 4+**: Progressive composition (tests, integration)

### Parallelization Example
```
Sequential would be: T1 → T2 → T3 → T4 → T5 (5 steps)

Wave-based parallel:
  Wave 1: T1, T2 (parallel) = 1 step
  Wave 2: T3 (depends on T1, T2) = 1 step
  Wave 3: T4, T5 (parallel, depend on T3) = 1 step
  Total: 3 steps (40% reduction)
```

## Validation

- ✅ All requirements have corresponding tasks
- ✅ No task is orphaned (unconnected from dependency graph)
- ✅ Wave ordering respects dependency order
- ✅ Total estimated effort reasonable
- ✅ Domain distribution balanced

## Performance Characteristics

- **Time**: ~3-8 seconds
- **Memory**: ~100-300 MB
- **Computation**: Topological sort, dependency inference

## Integration Points

- **Phase 2**: Receives classified requirements + dependency graph
- **Phase 4**: Sends task plan to atomization
- **Phase 6**: Code generation uses wave order for parallel generation
- **Metrics**: Wave count, task distribution, effort estimation

## Success Criteria

✅ Master plan created with 100+ tasks
✅ Tasks organized into 3-8 dependency waves
✅ All requirements have corresponding tasks
✅ Dependency graph is valid DAG (no cycles)
✅ Effort estimation completed
✅ Parallelization potential identified

## Typical Planning Output

```
Master Plan Summary:
  Total Tasks: 127

Task Distribution by Phase:
  - Data Layer: 18 tasks
  - API Routes: 27 tasks
  - Validation: 14 tasks
  - Authentication: 9 tasks
  - Testing: 35 tasks
  - Documentation: 8 tasks
  - Infrastructure: 16 tasks

Execution Waves: 6
  Wave 1: 22 tasks (parallel)
  Wave 2: 28 tasks (parallel)
  Wave 3: 25 tasks (parallel)
  Wave 4: 32 tasks (parallel)
  Wave 5: 15 tasks (parallel)
  Wave 6: 5 tasks (sequential)

Estimated Total Effort:
  - Lines of code: ~3,500
  - Estimated time: 15-20 hours (with parallelization)
  - Parallelization potential: 60% (40% must be sequential)

Dependency Graph:
  Nodes: 127
  Edges: 89
  Longest dependency chain: 8 tasks
  Parallelizable tasks: 76 (60%)
```

## Known Limitations

- ⚠️ Task decomposition is heuristic-based
- ⚠️ Effort estimation is approximate (±30%)
- ⚠️ Dependency inference may miss implicit dependencies
- ⚠️ Assumes uniform task execution time (not accurate)

## Fallback Behavior (if unavailable)

If MultiPassPlanner is unavailable:
1. Create simple flat task list (no waves)
2. No dependency ordering
3. All tasks appear independent
4. Code generation becomes sequential
5. Still produces valid output, slower execution

## Next Phase

Output feeds to **Phase 4: Atomization** which:
- Breaks each task into atomic units (~10 LOC each)
- Validates atomization quality
- Prepares for code generation

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:1129-1318
**Status**: Verified ✅
