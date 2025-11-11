# Integration with DevMatrix MVP

**Document**: 10 of 15
**Purpose**: How to integrate MGE v2 with existing DevMatrix MVP

---

## Integration Strategy

**Goal**: Add MGE v2 as enhancement, keep MVP working

**Approach**: Feature flag system - users choose MVP or v2

---

## Architecture Integration

```
DevMatrix MVP (Existing)
├─ Phase 0: Discovery ✅ (keep as-is)
├─ Phase 1: RAG ✅ (keep as-is)
├─ Phase 2: Masterplan ✅ (keep as-is)
└─ Phase 3-old: Task Decomposition

MGE v2 (New)
├─ Phase 3-new: AST Atomization 🆕
├─ Phase 4: Dependency Graph 🆕
├─ Phase 5: Hierarchical Validation 🆕
├─ Phase 6: Execution + Retry 🆕
└─ Phase 7: Human Review (Optional) 🆕
```

---

## Database Migration

```sql
-- Add execution_mode to projects table
ALTER TABLE projects ADD COLUMN execution_mode VARCHAR(20) DEFAULT 'mvp';
ALTER TABLE projects ADD COLUMN mge_v2_enabled BOOLEAN DEFAULT FALSE;

-- New tables (from 01_CONTEXT_MVP_TO_V2.md)
CREATE TABLE atomic_units (...);  -- 800+ atoms per project
CREATE TABLE atom_dependencies (...);  -- Dependency edges
CREATE TABLE validation_checkpoints (...);  -- 4-level validation
CREATE TABLE review_queue (...);  -- Human review
CREATE TABLE execution_plans (...);  -- Parallel execution plans

-- Indexes
CREATE INDEX idx_atomic_units_task ON atomic_units(task_id);
CREATE INDEX idx_atomic_units_status ON atomic_units(status);
CREATE INDEX idx_atom_deps_from ON atom_dependencies(from_atom_id);
CREATE INDEX idx_atom_deps_to ON atom_dependencies(to_atom_id);
```

---

## API Changes

### New Endpoints

```python
# FastAPI routes

@app.post("/api/projects/{project_id}/enable-v2")
async def enable_mge_v2(project_id: str):
    """Enable MGE v2 for project."""
    project = await Project.get(project_id)
    project.mge_v2_enabled = True
    project.execution_mode = 'v2'
    await project.save()
    return {"status": "enabled"}

@app.post("/api/tasks/{task_id}/atomize")
async def atomize_task(task_id: str):
    """Atomize task using Phase 3."""
    pipeline = ASTAtomizationPipeline()
    task = await Task.get(task_id)
    atoms = pipeline.atomize_task(
        task_id=task_id,
        task_code=task.description,
        language=task.language,
        file_path=task.file_path
    )
    return {"atoms": atoms}

@app.post("/api/projects/{project_id}/execute-v2")
async def execute_v2(project_id: str):
    """Execute project using MGE v2."""
    # Run Phases 3-7
    atoms = await atomize_all_tasks(project_id)
    graph, plan = await build_dependency_graph(atoms)
    validation_results = await hierarchical_validation(atoms)
    execution_results = await execute_with_retry(plan, atoms)
    
    if project.human_review_enabled:
        review_queue = await create_review_queue(atoms, execution_results)
        return {"status": "awaiting_review", "review_queue": review_queue}
    
    return {"status": "complete", "results": execution_results}
```

---

## Backward Compatibility

```python
class ExecutionRouter:
    """Route execution based on project settings."""
    
    async def execute_project(self, project_id: str):
        """Execute project (MVP or v2)."""
        project = await Project.get(project_id)
        
        if project.execution_mode == 'v2' and project.mge_v2_enabled:
            return await self.execute_v2(project)
        else:
            return await self.execute_mvp(project)
    
    async def execute_mvp(self, project: Project):
        """Original MVP execution (unchanged)."""
        # Phases 0-2 + original Phase 3
        masterplan = await generate_masterplan(project)
        subtasks = await decompose_tasks(masterplan)
        results = await execute_sequential(subtasks)
        return results
    
    async def execute_v2(self, project: Project):
        """MGE v2 execution (new)."""
        # Phases 0-2 (reuse) + Phases 3-7 (new)
        masterplan = await generate_masterplan(project)
        atoms = await atomize_tasks(masterplan.tasks)
        graph, plan = await build_dependency_graph(atoms)
        validation = await hierarchical_validation(atoms, project.path)
        execution = await execute_with_retry(plan, atoms)
        
        if project.human_review_enabled:
            review = await human_review_workflow(atoms, execution)
            return review
        
        return execution
```

---

## Configuration

```yaml
# config/mge_v2.yml

mge_v2:
  enabled: false  # Feature flag
  
  phases:
    atomization:
      enabled: true
      languages: ['python', 'typescript', 'javascript']
      target_loc: 10
      max_complexity: 5
    
    dependency_graph:
      enabled: true
      use_neo4j: false  # Use NetworkX by default
      max_parallel: 100
    
    validation:
      levels: 4
      atomic_threshold: 0.80
      module_threshold: 0.85
      component_threshold: 0.90
      system_threshold: 0.95
    
    execution:
      retry_attempts: 4
      parallel_workers: 100
      llm_model: "claude-sonnet-4.5-20250929"
    
    human_review:
      enabled: false  # Optional
      confidence_threshold: 0.75
      auto_approve_high_confidence: true
```

---

## Migration Path

### Week 1: Database Setup
```bash
# Run migrations
python manage.py migrate add_mge_v2_tables

# Verify
python manage.py dbshell
\dt  # List tables
```

### Week 2: Install Dependencies
```bash
pip install tree-sitter tree-sitter-python tree-sitter-typescript
pip install networkx matplotlib  # Optional: for visualization
pip install neo4j  # Optional: if using Neo4j
```

### Week 3: Deploy New Code
```bash
# Deploy Phases 3-7
git pull origin mge-v2
docker-compose up --build

# Verify
curl http://localhost:8000/api/health/mge-v2
```

### Week 4: Enable for Test Projects
```python
# Enable v2 for specific projects
test_projects = ['proj_1', 'proj_2', 'proj_3']

for proj_id in test_projects:
    await Project.update(proj_id, mge_v2_enabled=True, execution_mode='v2')
```

---

## Monitoring

```python
# Metrics to track

class MGEv2Metrics:
    """Track MGE v2 performance."""
    
    precision_v2: float  # Should be ≥98%
    time_v2: float  # Should be <2 hours
    cost_v2: float  # Should be <$200
    
    precision_improvement: float  # v2 - MVP
    time_reduction: float  # MVP - v2
    
    atomization_success_rate: float
    dependency_graph_build_time: float
    validation_pass_rate: Dict[int, float]  # By level
    execution_retry_rate: float
    human_review_usage: float  # % of projects
```

---

## Rollback Plan

```python
# If MGE v2 has issues, rollback

@app.post("/api/projects/{project_id}/rollback-to-mvp")
async def rollback_to_mvp(project_id: str):
    """Rollback project to MVP execution."""
    project = await Project.get(project_id)
    project.execution_mode = 'mvp'
    project.mge_v2_enabled = False
    await project.save()
    
    # Optional: Clean up v2 data
    await AtomicUnit.delete_many(task_id__in=project.task_ids)
    
    return {"status": "rolled_back_to_mvp"}
```

---

**Next Document**: [11_IMPLEMENTATION_ROADMAP.md](11_IMPLEMENTATION_ROADMAP.md)
