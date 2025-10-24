# Validation API - MGE V2

## Overview

The Validation API provides 4-level hierarchical validation for the MGE V2 (Master Code Generation Engine V2) system. It validates generated code quality at multiple levels of abstraction.

## Base URL

```
/api/v2/validation
```

## Validation Hierarchy

The validation system follows a hierarchical structure:

```
Level 1: Atomic     → Individual code atoms (10-15 LOC)
Level 2: Task       → Groups of atoms within a MasterPlanTask
Level 3: Milestone  → Groups of tasks within a MasterPlanMilestone
Level 4: MasterPlan → Complete project validation
```

## Endpoints

### 1. Validate Atom (Level 1)

Validates an individual atomic unit of code.

**Endpoint**: `POST /api/v2/validation/atom/{atom_id}`

**Parameters**:
- `atom_id` (path): UUID of the atom to validate

**Response**:
```json
{
  "atom_id": "uuid",
  "is_valid": true,
  "validation_score": 0.95,
  "checks": {
    "syntax": true,
    "semantics": true,
    "atomicity": true,
    "type_safety": true,
    "runtime_safety": true
  },
  "issues": [],
  "errors": [],
  "warnings": []
}
```

**Validation Checks**:
- **Syntax**: Code parses correctly (Python/TypeScript/JavaScript)
- **Semantics**: Variables are defined before use, proper scoping
- **Atomicity**: Meets atomicity criteria (LOC ≤15, complexity <3.0, context ≥95%)
- **Type Safety**: Type hints present (Python), type annotations (TypeScript)
- **Runtime Safety**: No dangerous patterns (eval, exec, etc.)

---

### 2. Validate Task (Level 2)

Validates coherence between atoms within a task.

**Endpoint**: `POST /api/v2/validation/task/{task_id}`

**Parameters**:
- `task_id` (path): UUID of the MasterPlanTask to validate

**Response**:
```json
{
  "task_id": "uuid",
  "is_valid": true,
  "validation_score": 0.92,
  "checks": {
    "consistency": true,
    "integration": true,
    "imports": true,
    "naming": true,
    "contracts": true
  },
  "issues": [],
  "errors": [],
  "warnings": []
}
```

**Validation Checks**:
- **Consistency**: All atoms use same language and style
- **Integration**: Symbols are properly defined and used across atoms
- **Imports**: No duplicate imports, proper import organization
- **Naming**: Consistent naming conventions (snake_case for Python, camelCase for JS)
- **Contracts**: Public API is consistent and well-defined

---

### 3. Validate Milestone (Level 3)

Validates integration between tasks within a milestone.

**Endpoint**: `POST /api/v2/validation/milestone/{milestone_id}`

**Parameters**:
- `milestone_id` (path): UUID of the MasterPlanMilestone to validate

**Response**:
```json
{
  "milestone_id": "uuid",
  "is_valid": true,
  "validation_score": 0.88,
  "checks": {
    "interfaces": true,
    "contracts": true,
    "api_consistency": true,
    "integration": true,
    "dependencies": true
  },
  "issues": [],
  "errors": [],
  "warnings": []
}
```

**Validation Checks**:
- **Interfaces**: Inter-task interfaces are well-defined
- **Contracts**: Milestone-level contracts are satisfied
- **API Consistency**: API naming is consistent across tasks
- **Integration**: Tasks integrate properly within milestone
- **Dependencies**: No circular dependencies between tasks

---

### 4. Validate MasterPlan (Level 4)

Validates the entire masterplan system.

**Endpoint**: `POST /api/v2/validation/masterplan/{masterplan_id}`

**Parameters**:
- `masterplan_id` (path): UUID of the MasterPlan to validate

**Response**:
```json
{
  "masterplan_id": "uuid",
  "is_valid": true,
  "validation_score": 0.90,
  "checks": {
    "architecture": true,
    "dependencies": true,
    "contracts": true,
    "performance": true,
    "security": true
  },
  "statistics": {
    "total_atoms": 150,
    "total_tasks": 25,
    "total_milestones": 5
  },
  "issues": [],
  "errors": [],
  "warnings": []
}
```

**Validation Checks**:
- **Architecture**: System follows architectural patterns (proper layering, module organization)
- **Dependencies**: Dependency graph is valid (no cycles, proper structure)
- **Contracts**: System-wide contracts are satisfied
- **Performance**: Performance characteristics are acceptable (complexity distribution, LOC)
- **Security**: Security posture is acceptable (no dangerous patterns, SQL injection checks)

---

### 5. Hierarchical Validation

Validates all levels hierarchically for a masterplan.

**Endpoint**: `POST /api/v2/validation/hierarchical/{masterplan_id}`

**Request Body** (optional):
```json
{
  "levels": ["atomic", "task", "milestone", "masterplan"]
}
```

**Parameters**:
- `masterplan_id` (path): UUID of the MasterPlan to validate
- `levels` (body, optional): Array of levels to validate. Default: all levels

**Response**:
```json
{
  "masterplan_id": "uuid",
  "levels_validated": ["atomic", "task", "milestone", "masterplan"],
  "overall_valid": true,
  "overall_score": 0.91,
  "results": {
    "atomic": {
      "total_atoms": 150,
      "valid_atoms": 148,
      "avg_score": 0.93,
      "atoms": [...]
    },
    "task": {
      "total_tasks": 25,
      "valid_tasks": 24,
      "avg_score": 0.90,
      "tasks": [...]
    },
    "milestone": {
      "total_milestones": 5,
      "valid_milestones": 5,
      "avg_score": 0.89,
      "milestones": [...]
    },
    "masterplan": {
      "is_valid": true,
      "validation_score": 0.92,
      ...
    }
  }
}
```

---

### 6. Batch Validate Atoms

Validates multiple atoms in a single request.

**Endpoint**: `POST /api/v2/validation/batch/atoms`

**Request Body**:
```json
{
  "atom_ids": ["uuid1", "uuid2", "uuid3", ...]
}
```

**Response**:
```json
{
  "total_atoms": 10,
  "valid_atoms": 9,
  "avg_score": 0.91,
  "atoms": [
    {
      "atom_id": "uuid1",
      "is_valid": true,
      "validation_score": 0.95,
      ...
    },
    ...
  ]
}
```

---

## Validation Scoring

Each validation level produces a score from 0.0 to 1.0:

### Level 1 (Atomic)
- **Syntax**: 20%
- **Semantics**: 20%
- **Atomicity**: 20%
- **Type Safety**: 20%
- **Runtime Safety**: 20%

### Level 2 (Task)
- **Consistency**: 20%
- **Integration**: 20%
- **Imports**: 20%
- **Naming**: 20%
- **Contracts**: 20%

### Level 3 (Milestone)
- **Interfaces**: 20%
- **Contracts**: 20%
- **API Consistency**: 20%
- **Integration**: 20%
- **Dependencies**: 20%

### Level 4 (MasterPlan)
- **Architecture**: 25%
- **Dependencies**: 25%
- **Contracts**: 20%
- **Performance**: 15%
- **Security**: 15%

---

## Issue Severity Levels

Issues are classified by severity:

- **error**: Critical issues that prevent code execution or violate hard constraints
- **warning**: Non-critical issues that should be reviewed but don't block execution
- **info**: Informational messages about potential improvements

---

## Example Usage

### Validate a single atom

```bash
curl -X POST "http://localhost:8000/api/v2/validation/atom/123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json"
```

### Validate entire masterplan hierarchically

```bash
curl -X POST "http://localhost:8000/api/v2/validation/hierarchical/123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -d '{
    "levels": ["atomic", "task", "milestone", "masterplan"]
  }'
```

### Batch validate atoms

```bash
curl -X POST "http://localhost:8000/api/v2/validation/batch/atoms" \
  -H "Content-Type: application/json" \
  -d '{
    "atom_ids": [
      "123e4567-e89b-12d3-a456-426614174001",
      "123e4567-e89b-12d3-a456-426614174002",
      "123e4567-e89b-12d3-a456-426614174003"
    ]
  }'
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid atom_id: badly formed hexadecimal UUID string"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Validation failed: <error message>"
}
```

---

## Integration with MGE V2 Pipeline

The Validation API integrates with the MGE V2 pipeline at Phase 4:

```
Phase 1: Database Setup
Phase 2: Atomization (task → atoms)
Phase 3: Dependency Graph Construction
Phase 4: Hierarchical Validation ← YOU ARE HERE
Phase 5: Wave-based Execution
```

Validation results are used to:
1. **Quality Gate**: Prevent execution of invalid code
2. **Confidence Scoring**: Calculate atom confidence for review queue
3. **Retry Logic**: Trigger regeneration for low-scoring atoms
4. **Metrics**: Track code quality metrics across projects

---

## Performance Considerations

- **Atomic Validation**: ~50ms per atom (AST parsing + analysis)
- **Task Validation**: ~200ms per task (depends on atom count)
- **Milestone Validation**: ~500ms per milestone (depends on task count)
- **MasterPlan Validation**: ~2s per masterplan (full system analysis)
- **Hierarchical Validation**: ~3-5s for typical project (150 atoms)

For large projects (>500 atoms), consider:
- Using batch validation for atoms
- Validating selectively (specific levels only)
- Running validation asynchronously

---

## Related Documentation

- [MGE V2 Architecture](../mge-v2-architecture.md)
- [Atomization Guide](../atomization.md)
- [Dependency Graph](../dependency-graph.md)
- [Execution Pipeline](../execution.md)

---

**Last Updated**: 2025-10-23
**API Version**: v2
**Status**: ✅ Production Ready
