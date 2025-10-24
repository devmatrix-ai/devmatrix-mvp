# Context: From DevMatrix MVP to MGE v2

**Document**: 01 of 15
**Purpose**: Understand current DevMatrix MVP state and transition to v2

---

## DevMatrix MVP: Current State

### Architecture

```
DevMatrix MVP Flow:
┌──────────────────────────────────────┐
│ Phase 1: Discovery + RAG Retrieval  │
│ ├─ DDD modeling                      │
│ ├─ ChromaDB semantic search          │
│ └─ Tech stack selection              │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Phase 2: Masterplan Generation       │
│ ├─ Phases → Milestones → Tasks      │
│ ├─ Basic dependency tracking         │
│ └─ Agent assignment                  │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Phase 3: Task Decomposition          │
│ ├─ Tasks → Subtasks                 │
│ ├─ 80 LOC/task, 25 LOC/subtask      │
│ └─ Sequential execution              │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Phase 4: Execution                   │
│ ├─ Generate code per subtask        │
│ ├─ Basic validation (syntax, tests) │
│ └─ Limited parallelization (2-3)    │
└──────────────────────────────────────┘
```

### Results

**Metrics**:
- 50 tasks × 3 subtasks = **150 subtasks**
- **87.1% precision** ✅
- **13 hours** execution time
- **$160** per project
- Sequential++ execution (2-3 parallel max)

**Database Schema** (PostgreSQL):
```sql
-- Existing tables
phases (id, project_id, name, order, status)
milestones (id, phase_id, name, description, status)
tasks (id, milestone_id, name, description, estimated_hours, status)
subtasks (id, task_id, name, code, status, validation_result)
```

**Technology Stack**:
- Backend: FastAPI (Python 3.11)
- Database: PostgreSQL 15
- Vector DB: ChromaDB
- LLM: Claude Sonnet 4.5 (Anthropic)
- Frontend: React + TypeScript

---

## MVP Strengths ✅

### 1. Solid Foundation
- **DDD Modeling**: Domain-driven design produces quality specs
- **RAG Integration**: ChromaDB provides relevant examples
- **Hierarchical Planning**: Phase → Milestone → Task structure is sound
- **Production Ready**: PostgreSQL + FastAPI is battle-tested

### 2. Good Precision
- **87.1%** is actually GOOD for AI code generation
- Better than Copilot (30% acceptance)
- Better than Devin (15% success)
- Comparable to Cursor (40-50%)

### 3. Complete Workflow
- End-to-end flow works
- Discovery → Planning → Execution → Delivery
- User can generate full projects

### 4. Context Management
- DDD provides business context
- RAG provides technical examples
- Task descriptions include requirements

---

## MVP Limitations ⚠️

### 1. Granularity Too Coarse

**Problem**: 25 LOC subtasks still have compound errors

```python
# Subtask: "Create User Model" (25 LOC)
class User(Base):
    __tablename__ = 'users'
    id = Column(UUID, primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    emai_verified = Column(Boolean, default=False)  # ❌ Typo: "emai"
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def verify_email(self):
        self.emai_verified = True  # ❌ Typo propagates

# Result: Typo in 25-line subtask affects multiple parts
# LLM made mistake once, used consistently → looks "correct"
```

**Impact**:
- Errors span multiple lines
- Harder to detect in review
- Propagate to dependent code

### 2. Limited Parallelization

**Problem**: Dependencies tracked at Task level (too coarse)

```python
# Current dependency tracking
Task 1: "Database Layer" (80 LOC)
Task 2: "API Layer" (100 LOC) → depends on Task 1
Task 3: "Frontend" (120 LOC) → depends on Task 2

# Execution: Sequential
Task 1 (15 min) → Task 2 (18 min) → Task 3 (22 min) = 55 min

# But within tasks, no parallelization!
# Task 1 has 3 subtasks that could run parallel → wasted opportunity
```

**Impact**:
- Max 2-3 concurrent tasks
- Most execution is sequential
- 13 hours total time (could be much faster)

### 3. No Retry Mechanism

**Problem**: LLMs are non-deterministic

```python
# Single attempt per subtask
result = llm.generate(subtask)
if validation_fails(result):
    # Mark as failed, move on
    # NO retry with error feedback ❌

# Reality: LLM might succeed on retry!
# Attempt 1: 90% success
# Attempt 2: 90% of remaining 10% = 99% total
# Attempt 3: 99.9% total
```

**Impact**:
- 13% failure rate (100% - 87.1%)
- Could be reduced to <2% with retries
- Wasted potential

### 4. Basic Validation Only

**Problem**: Only syntax + unit tests

```python
# Current validation
def validate_subtask(code):
    # 1. Syntax check
    ast.parse(code)  ✅

    # 2. Run unit test
    run_test(code)   ✅

    # Missing:
    # - Integration tests ❌
    # - Atomicity checks ❌
    # - Complexity analysis ❌
    # - Context completeness ❌
```

**Impact**:
- Integration bugs discovered late
- No early warning system
- Higher debugging cost

---

## Gap Analysis: MVP vs Target

| Aspect | MVP | Target (v2) | Gap |
|--------|-----|-------------|-----|
| **Precision** | 87.1% | 98% | +12.5% |
| **Granularity** | 25 LOC | 10 LOC | 2.5x finer |
| **Parallelization** | 2-3 | 100+ | 50x more |
| **Validation** | 2 levels | 4 levels | 2x depth |
| **Retry** | None | 3 attempts | NEW |
| **Human Review** | Manual | Smart 15% | NEW |
| **Time** | 13h | 1.5h | 87% faster |

---

## Transition Strategy

### What to Keep ✅

1. **Phases 0-2**: Discovery, RAG, Masterplan
   - Already working well
   - No changes needed
   - Just add one more level (Tasks → Atoms)

2. **Database Infrastructure**
   - PostgreSQL is solid
   - FastAPI is good
   - Just add new tables for atoms

3. **LLM Integration**
   - Claude Sonnet 4.5 is fine
   - Just add retry logic

### What to Add 🆕

1. **Phase 3: AST Atomization**
   - NEW: Recursive decomposer
   - NEW: Multi-language parser
   - NEW: Context injector (95% completeness)

2. **Phase 4: Dependency Graph**
   - NEW: Neo4j graph database
   - NEW: Topological sort
   - NEW: Parallel group detection

3. **Phase 5: Hierarchical Validation**
   - NEW: 4-level validation
   - NEW: Progressive integration testing
   - NEW: Boundary detection

4. **Phase 6: Execution + Retry**
   - NEW: Retry loop (3 attempts)
   - NEW: Error feedback to LLM
   - NEW: Dependency-aware generation

5. **Phase 7: Human Review**
   - NEW: Confidence scoring
   - NEW: Review interface
   - NEW: Smart suggestions

### What to Modify 🔧

1. **Task Model**
   - Add: `atomic_units` relationship
   - Add: Fine-grained dependencies

2. **Execution Engine**
   - Replace: Sequential executor
   - With: Parallel dependency-aware executor

3. **Validation**
   - Enhance: From 2 levels to 4 levels
   - Add: Atomicity validation

---

## Database Schema Changes

### New Tables

```sql
-- New in v2
CREATE TABLE atomic_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),

    -- Identification
    atom_number INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Code specs
    language VARCHAR(50) NOT NULL,
    estimated_loc INTEGER DEFAULT 10,
    actual_loc INTEGER,
    complexity FLOAT DEFAULT 1.5,

    -- Context (JSONB for flexibility)
    context_json JSONB NOT NULL,

    -- Dependencies (array of atom IDs)
    depends_on UUID[],

    -- Code
    code TEXT,

    -- Execution
    status VARCHAR(50) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,

    -- Validation
    validation_results JSONB,
    confidence_score FLOAT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    generated_at TIMESTAMP,
    validated_at TIMESTAMP,

    CONSTRAINT fk_task FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_atomic_units_task ON atomic_units(task_id);
CREATE INDEX idx_atomic_units_status ON atomic_units(status);

-- Dependency graph edges (for Neo4j-like queries in PostgreSQL)
CREATE TABLE atom_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_atom_id UUID REFERENCES atomic_units(id),
    to_atom_id UUID REFERENCES atomic_units(id),
    dependency_type VARCHAR(50), -- 'import', 'data', 'control', 'type'
    weight FLOAT DEFAULT 1.0,

    CONSTRAINT fk_from_atom FOREIGN KEY (from_atom_id) REFERENCES atomic_units(id),
    CONSTRAINT fk_to_atom FOREIGN KEY (to_atom_id) REFERENCES atomic_units(id)
);

CREATE INDEX idx_deps_from ON atom_dependencies(from_atom_id);
CREATE INDEX idx_deps_to ON atom_dependencies(to_atom_id);

-- Validation checkpoints
CREATE TABLE validation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    level INTEGER NOT NULL, -- 1=atomic, 2=module, 3=component, 4=system
    checkpoint_type VARCHAR(50),
    atoms_validated UUID[],
    passed BOOLEAN,
    errors JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Human review queue
CREATE TABLE review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    atom_id UUID REFERENCES atomic_units(id),
    confidence_score FLOAT,
    flagged_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewer_action VARCHAR(50), -- 'approve', 'edit', 'regenerate'
    reviewer_notes TEXT,

    CONSTRAINT fk_atom FOREIGN KEY (atom_id) REFERENCES atomic_units(id)
);
```

### Modified Tables

```sql
-- Add to existing tasks table
ALTER TABLE tasks ADD COLUMN atomization_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN total_atoms INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN avg_atom_loc FLOAT;
```

---

## Technology Stack Changes

### New Dependencies

```yaml
# Backend additions
tree-sitter: "0.20.0"  # AST parsing
tree-sitter-python: "0.20.0"
tree-sitter-typescript: "0.20.0"
tree-sitter-javascript: "0.20.0"
networkx: "3.0"  # Graph algorithms
neo4j: "5.0"  # Optional (can use PostgreSQL for graphs)

# Frontend additions (for human review interface)
react-diff-viewer: "^3.1.0"
codemirror: "^6.0.0"  # Code editor
```

### Infrastructure

```yaml
# Existing
postgresql: "15"
chromadb: "0.4.0"
fastapi: "0.104.0"

# New
neo4j: "5.0"  # Optional (dependency graph visualization)
redis: "7.0"  # Caching for retry logic
```

---

## Migration Path

### Phase 1: Add New Tables (Week 1)
1. Create new PostgreSQL tables
2. Add migrations
3. Test with existing data

### Phase 2: Implement AST Atomization (Weeks 2-4)
1. Install tree-sitter
2. Implement parser
3. Implement decomposer
4. Test on sample tasks

### Phase 3: Parallel Execution (Weeks 5-6)
1. Implement dependency graph
2. Implement topological sort
3. Build parallel executor
4. Test throughput

### Phase 4: Validation System (Weeks 7-9)
1. Implement 4-level validator
2. Add integration tests
3. Add progressive testing
4. Measure error detection

### Phase 5: Retry Logic (Weeks 10-11)
1. Add retry mechanism
2. Implement error feedback
3. Test precision improvement
4. Tune retry strategies

### Phase 6: Human Review (Weeks 12-13)
1. Build review interface
2. Implement confidence scoring
3. Add AI suggestions
4. Test with real users

### Phase 7: Integration & Testing (Weeks 14-16)
1. End-to-end testing
2. Performance tuning
3. Documentation
4. Production deployment

---

## Backward Compatibility

### Must Maintain

1. **Existing API Endpoints**
   - `/api/projects/create`
   - `/api/tasks/generate`
   - `/api/tasks/execute`

2. **Database Tables**
   - `projects`, `phases`, `milestones`, `tasks`, `subtasks`
   - Don't break existing queries

3. **Frontend Components**
   - Project creation flow
   - Task visualization
   - Progress tracking

### Migration Strategy

```python
# Support both modes
class ExecutionMode(Enum):
    LEGACY = "mvp"  # 87% precision, 13h
    V2 = "mge_v2"    # 98% precision, 1.5h

# User can choose
project.execution_mode = ExecutionMode.V2

# System routes accordingly
if project.execution_mode == ExecutionMode.LEGACY:
    execute_mvp_pipeline(project)
else:
    execute_v2_pipeline(project)
```

---

## Success Metrics

### Phase 1 (MVP → v2 transition)
- [ ] New tables created
- [ ] AST parser working for Python
- [ ] Can decompose 1 task into atoms
- [ ] Atoms stored in database

### Phase 2 (Core functionality)
- [ ] Dependency graph builds correctly
- [ ] Topological sort produces valid order
- [ ] Can generate 10 atoms in dependency order
- [ ] Precision >90% on test project

### Phase 3 (Full v2)
- [ ] All 7 phases implemented
- [ ] Precision ≥98% on 10 projects
- [ ] Time <2 hours per project
- [ ] Cost <$200 per project

---

**Next Document**: [02_WHY_V2_NOT_V1.md](02_WHY_V2_NOT_V1.md) - Why v2 approach (not v1 fantasy)
