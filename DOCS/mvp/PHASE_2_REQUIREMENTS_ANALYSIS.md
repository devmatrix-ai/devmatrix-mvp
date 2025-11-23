# Phase 2: Requirements Analysis

**Purpose**: Classify requirements into domains, priorities, and risk levels

**Status**: ✅ Core (Required)

---

## Overview

Phase 2 takes the parsed `SpecRequirements` from Phase 1 and classifies each requirement using semantic analysis. It builds a dependency graph showing how requirements depend on each other.

## Input

- **Source**: SpecRequirements object from Phase 1
- **Contains**:
  - List of all requirements
  - Entities, endpoints, validations
  - Ground truth classification data (optional)

## Processing

```python
async def _phase_2_requirements_analysis(self):
    # 1. Semantic classification
    classified_requirements = classifier.classify_batch(
        spec_requirements.requirements
    )

    # 2. Build dependency graph
    dependency_graph = classifier.build_dependency_graph(
        classified_requirements
    )

    # 3. Validate DAG (no circular dependencies)
    is_valid_dag = classifier.validate_dag(dependency_graph)
```

## Output

### Classified Requirement

```python
class ClassifiedRequirement:
    id: str                    # F1, F2, etc.
    description: str           # Requirement text
    type: str                  # "functional" | "non_functional"
    domain: str                # "crud", "auth", "payment", etc.
    priority: str              # "MUST", "SHOULD", "COULD"
    risk_level: str            # "low", "medium", "high"
    dependencies: List[str]    # IDs of requirements this depends on
    complexity: float          # 0.0-1.0 complexity estimate
```

### Data Structures

```python
DependencyGraph: Dict[req_id] -> List[dependent_req_ids]
    # Edges show what this requirement depends on

ClassificationAccuracy: float
    # Percentage of requirements correctly classified
    # (validated against ground truth if available)
```

## Service Dependencies

### Required
- **RequirementsClassifier** (`src/classification/requirements_classifier.py`)
  - Semantic classification using ML/NLP
  - Domain identification
  - Priority assessment
  - Risk level estimation
  - Dependency inference
  - DAG validation

### Optional
- None

## Classification Domains

| Domain | Examples | Usage |
|--------|----------|-------|
| **crud** | Create/Read/Update/Delete | Basic entity operations |
| **auth** | Login, JWT, permissions | Authentication/authorization |
| **validation** | Constraints, checks | Input validation |
| **workflow** | Status transitions | Business logic |
| **integration** | External APIs | Third-party services |
| **infrastructure** | Database, caching | System setup |

## Classification Priorities

| Priority | Definition | Action |
|----------|-----------|--------|
| **MUST** | Required for MVP | Must be implemented |
| **SHOULD** | Important feature | Implement if time |
| **COULD** | Nice to have | Optional enhancement |

## Risk Levels

| Level | Threshold | Characteristics |
|-------|-----------|-----------------|
| **LOW** | < 0.3 | Simple, well-understood |
| **MEDIUM** | 0.3-0.7 | Moderate complexity |
| **HIGH** | > 0.7 | Complex, novel, risky |

## Dependency Graph

Example:
```
User Creation (F1) ──┐
                     ├──> Email Validation (F3) ──> Notification (F4)
Password Hash (F2) ──┤
                     └──> Stored in DB (F5)

Topological sort → Execution order:
1. F1, F2 (no dependencies)
2. F3, F5 (depend on F1, F2)
3. F4 (depends on F3)
```

## Validation Results

```python
Classification Metrics:
  - Total requirements: N
  - Correctly classified: M (vs ground truth)
  - Classification accuracy: M/N %

Graph Validation:
  - Nodes: N requirements
  - Edges: E dependencies
  - Valid DAG: Yes/No
  - Cycles detected: 0
```

## Metrics Collected

- Classification accuracy (vs ground truth)
- Domain distribution histogram
- Dependency graph density
- Risk distribution
- Priority distribution

## Error Handling

### No Ground Truth Available
- Classification proceeds without validation
- Accuracy metrics show 100% (assumed correct)
- Warning logged

### Circular Dependency Detected
```python
ValueError: Circular dependency detected in requirements
```
**Resolution**: Fix requirement dependencies, ensure DAG structure

### Invalid Requirement Format
```python
ValueError: Requirement missing required fields
```
**Resolution**: Ensure Phase 1 parsed correctly

## Data Flow

```
ClassifiedRequirements (Phase 1)
    ↓
    └─ RequirementsClassifier.classify_batch()
        ├─ Assign domain
        ├─ Assign priority
        ├─ Estimate risk
        └─ Identify dependencies
            ↓
        Classified Requirements
            +
        Dependency Graph
            ↓
            Feeds to Phase 3 (Multi-Pass Planning)
```

## Performance Characteristics

- **Time**: ~5-15 seconds (depends on requirement count)
- **Memory**: ~50-200 MB
- **Computation**: Semantic embedding generation (GPU recommended)

## Integration Points

- **Phase 1**: Receives parsed requirements
- **Phase 3**: Sends classified requirements and dependency graph
- **Metrics**: Classification accuracy, domain distribution
- **Validation**: Ground truth comparison (if available)

## Success Criteria

✅ All requirements classified into domains
✅ Dependency graph created (DAG structure)
✅ Circular dependencies checked and resolved
✅ Priority and risk levels assigned
✅ Classification accuracy calculated
✅ Metrics collected and logged

## Known Limitations

- ❌ Accuracy depends on spec clarity (garbage in = garbage out)
- ⚠️ Domain classification may miss novel domains
- ⚠️ Dependency inference is heuristic-based
- ⚠️ Risk estimation is approximation (not exhaustive)

## Typical Classification Output

```
Requirements Analysis Report:
  Total: 12 requirements
  Functional: 10 (83%)
  Non-functional: 2 (17%)

Domain Distribution:
  - CRUD: 4 requirements
  - Auth: 3 requirements
  - Validation: 3 requirements
  - Workflow: 2 requirements

Priority Distribution:
  - MUST: 7 requirements (58%)
  - SHOULD: 3 requirements (25%)
  - COULD: 2 requirements (17%)

Risk Distribution:
  - Low: 6 requirements (50%)
  - Medium: 5 requirements (42%)
  - High: 1 requirement (8%)

Dependency Graph:
  - Nodes: 12
  - Edges: 8
  - Valid DAG: Yes
  - Complexity: Moderate

Classification Accuracy: 94.5% (vs ground truth)
```

## Next Phase

Output feeds to **Phase 3: Multi-Pass Planning** which:
- Creates task breakdown structure (100+ tasks)
- Orders tasks using dependency graph
- Organizes into execution waves

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:777-1128
**Status**: Verified ✅
