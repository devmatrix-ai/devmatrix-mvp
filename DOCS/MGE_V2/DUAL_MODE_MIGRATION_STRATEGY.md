# MGE V2 DUAL-MODE Migration Strategy

**Version**: 1.0
**Date**: 2025-10-23
**Author**: Dany (System Architect)
**Purpose**: Complete migration analysis from DevMatrix MVP to MGE V2 with DUAL-MODE compatibility

---

## Executive Summary

### Migration Approach: DUAL-MODE Architecture

This strategy enables **simultaneous operation** of both MVP (Task-based, 25 LOC granularity) and V2 (Atom-based, 10 LOC granularity) execution modes within the same codebase, allowing:

- **Zero-downtime migration**: Users can continue using MVP while V2 is developed
- **Gradual rollout**: Feature-flag controlled transition from MVP → V2
- **A/B testing**: Compare precision/performance between modes
- **Rollback capability**: Instant revert to MVP if V2 issues arise
- **Incremental validation**: Test V2 components independently

### Key Metrics Comparison

| Metric | MVP | V2 Autonomous | V2 + Human | Migration Target |
|--------|-----|---------------|------------|------------------|
| **Precision** | 87.1% | 98% | 99%+ | 95%+ (V2 solo) |
| **Time** | 13 hours | 1-1.5 hours | 1.5-2 hours | <2 hours |
| **Cost** | $160 | $180 | $280-330 | <$200 (optimize) |
| **Granularity** | 25 LOC/subtask | 10 LOC/atom | 10 LOC/atom | 10 LOC/atom |
| **Parallelization** | 2-3 concurrent | 100+ concurrent | 100+ concurrent | 50+ concurrent |

---

## 1. GAP ANALYSIS: MVP → V2

### 1.1 Database Schema Gaps

#### EXISTING (MVP)
```sql
✅ discovery_documents     -- DDD analysis results
✅ masterplans              -- 50 task plans
✅ masterplan_phases        -- Setup/Core/Polish
✅ masterplan_milestones    -- Milestone groupings
✅ masterplan_tasks         -- 80 LOC tasks with basic dependencies
✅ masterplan_subtasks      -- 25 LOC subtasks
✅ masterplan_versions      -- Version tracking
✅ masterplan_history       -- Execution audit trail
```

#### MISSING (V2 Requirements)
```sql
❌ atomic_units                    -- NEW: 10 LOC atoms (Phase 3)
❌ atom_dependencies                -- NEW: Fine-grained dep graph (Phase 4)
❌ dependency_graph_metadata        -- NEW: Neo4j/networkx state
❌ validation_results               -- NEW: 4-level validation (Phase 5)
❌ execution_waves                  -- NEW: Parallel wave tracking (Phase 6)
❌ retry_history                    -- NEW: Atom retry logs (Phase 6)
❌ confidence_scores                -- NEW: Human review flags (Phase 7)
❌ human_review_queue               -- NEW: Low-confidence atoms (Phase 7)
```

### 1.2 Service Layer Gaps

#### EXISTING (MVP)
```python
✅ DiscoveryAgent           -- DDD discovery (Sonnet 4.5)
✅ MasterPlanGenerator      -- 50 task generation
✅ TaskExecutor             -- Task execution with RAG
✅ CodeValidator            -- Basic syntax/test validation
✅ AuthService              -- JWT authentication
✅ ChatService              -- Conversation management
✅ AdminService             -- Admin operations
✅ EmailService             -- Email notifications
✅ PasswordResetService     -- Password recovery
✅ TenancyService           -- Multi-tenancy
✅ UsageTrackingService     -- Usage monitoring
✅ WorkspaceService         -- Workspace management
```

#### MISSING (V2 Requirements)
```python
❌ ASTAtomizationService       -- NEW: tree-sitter parsing (Phase 3)
❌ RecursiveDecomposer          -- NEW: AST → atoms (Phase 3)
❌ ContextInjector              -- NEW: 95% context enrichment (Phase 3)
❌ AtomicityValidator           -- NEW: 10-criteria validation (Phase 3)
❌ DependencyAnalyzer           -- NEW: Graph builder (Phase 4)
❌ DependencyAwareGenerator     -- NEW: Topological execution (Phase 4)
❌ HierarchicalValidator        -- NEW: 4-level validation (Phase 5)
❌ RetryOrchestrator            -- NEW: 3-attempt retry loop (Phase 6)
❌ WaveExecutor                 -- NEW: Parallel wave management (Phase 6)
❌ ConfidenceScorer             -- NEW: ML confidence scoring (Phase 7)
❌ HumanReviewService           -- NEW: Review UI/API (Phase 7)
```

### 1.3 Technology Stack Gaps

#### EXISTING (MVP)
```yaml
Backend:
  ✅ Python 3.11
  ✅ FastAPI
  ✅ SQLAlchemy
  ✅ Alembic (migrations)
  ✅ PostgreSQL 15
  ✅ Redis (caching)
  ✅ ChromaDB (RAG)

Frontend:
  ✅ React 18
  ✅ TypeScript
  ✅ TailwindCSS
  ✅ React Query

LLM:
  ✅ Anthropic Claude (Sonnet 4.5, Haiku 3.5)
  ✅ Prompt caching

DevOps:
  ✅ Docker
  ✅ Docker Compose
  ✅ GitHub Actions
```

#### MISSING (V2 Requirements)
```yaml
Backend:
  ❌ tree-sitter (AST parsing) -- CRITICAL for Phase 3
  ❌ tree-sitter-python
  ❌ tree-sitter-typescript
  ❌ tree-sitter-javascript
  ❌ networkx (dependency graphs) -- OR Neo4j
  ❌ pytest-xdist (parallel testing)

Optional (Nice-to-have):
  ❌ Neo4j (graph database) -- Better than networkx for large projects
  ❌ Celery (distributed task queue) -- For massive parallelization
  ❌ scikit-learn (confidence scoring) -- For Phase 7 ML
```

### 1.4 API Endpoint Gaps

#### EXISTING (MVP)
```
✅ POST   /api/v1/discovery/start          -- Start DDD discovery
✅ POST   /api/v1/masterplan/generate      -- Generate 50-task plan
✅ POST   /api/v1/masterplan/execute       -- Execute plan
✅ GET    /api/v1/masterplan/{id}          -- Get plan status
✅ GET    /api/v1/task/{id}                -- Get task details
✅ POST   /api/v1/task/{id}/retry          -- Retry failed task
✅ WS     /ws/masterplan/{id}              -- Real-time progress
```

#### MISSING (V2 Requirements)
```
❌ POST   /api/v2/atomize/task/{id}        -- Atomize single task
❌ POST   /api/v2/atomize/plan/{id}        -- Atomize entire plan
❌ GET    /api/v2/atoms/{plan_id}          -- List all atoms
❌ GET    /api/v2/atom/{id}                -- Get atom details
❌ POST   /api/v2/dependency-graph/build   -- Build dep graph
❌ GET    /api/v2/dependency-graph/{id}    -- Get graph visualization
❌ GET    /api/v2/execution-waves/{id}     -- Get parallel waves
❌ POST   /api/v2/execute/wave             -- Execute single wave
❌ POST   /api/v2/validate/hierarchical    -- Run 4-level validation
❌ GET    /api/v2/review-queue/{plan_id}   -- Get atoms needing review
❌ POST   /api/v2/review/{atom_id}         -- Submit human review
❌ POST   /api/v2/mode                     -- Switch MVP ↔ V2 mode
```

---

## 2. DUAL-MODE ARCHITECTURE DESIGN

### 2.1 Mode Selection Strategy

#### Feature Flag Configuration
```python
# File: src/config/execution_mode.py

from enum import Enum
from typing import Optional
import os

class ExecutionMode(str, Enum):
    """Execution mode for MasterPlan generation/execution"""
    MVP = "mvp"           # Task-based (25 LOC subtasks)
    V2_ATOMS = "v2_atoms" # Atom-based (10 LOC atoms)
    HYBRID = "hybrid"     # Use V2 for some phases, MVP for others

class ModeConfig:
    """Configuration for execution mode selection"""

    # Default mode (can be overridden by env var or user preference)
    DEFAULT_MODE = ExecutionMode(os.getenv("DEVMATRIX_MODE", "mvp"))

    # Per-user mode override (stored in database)
    USER_MODE_OVERRIDE: dict[str, ExecutionMode] = {}

    # Per-plan mode override (stored in masterplans table)
    PLAN_MODE_OVERRIDE: dict[str, ExecutionMode] = {}

    # Feature flags for gradual rollout
    ENABLE_V2_ATOMIZATION = os.getenv("ENABLE_V2_ATOMIZATION", "false") == "true"
    ENABLE_V2_DEP_GRAPH = os.getenv("ENABLE_V2_DEP_GRAPH", "false") == "true"
    ENABLE_V2_VALIDATION = os.getenv("ENABLE_V2_VALIDATION", "false") == "true"
    ENABLE_V2_EXECUTION = os.getenv("ENABLE_V2_EXECUTION", "false") == "true"
    ENABLE_V2_REVIEW = os.getenv("ENABLE_V2_REVIEW", "false") == "true"

    # Rollout percentage (0-100)
    V2_ROLLOUT_PERCENT = int(os.getenv("V2_ROLLOUT_PERCENT", "0"))

    @classmethod
    def get_mode(
        cls,
        user_id: Optional[str] = None,
        plan_id: Optional[str] = None
    ) -> ExecutionMode:
        """
        Determine execution mode with priority:
        1. Plan-level override
        2. User-level override
        3. Rollout percentage
        4. Default mode
        """
        # Check plan override
        if plan_id and plan_id in cls.PLAN_MODE_OVERRIDE:
            return cls.PLAN_MODE_OVERRIDE[plan_id]

        # Check user override
        if user_id and user_id in cls.USER_MODE_OVERRIDE:
            return cls.USER_MODE_OVERRIDE[user_id]

        # Check rollout percentage
        if cls.V2_ROLLOUT_PERCENT > 0:
            import random
            if random.randint(1, 100) <= cls.V2_ROLLOUT_PERCENT:
                return ExecutionMode.V2_ATOMS

        # Default
        return cls.DEFAULT_MODE

    @classmethod
    def is_v2_enabled(cls) -> bool:
        """Check if V2 mode is available"""
        return (
            cls.ENABLE_V2_ATOMIZATION and
            cls.ENABLE_V2_DEP_GRAPH and
            cls.ENABLE_V2_VALIDATION and
            cls.ENABLE_V2_EXECUTION
        )
```

### 2.2 Database Schema: Additive Approach

**Strategy**: Add V2 tables WITHOUT modifying existing MVP tables

#### New Tables for V2
```sql
-- Phase 3: Atomic Units
CREATE TABLE atomic_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to existing task (BACKWARD COMPATIBLE)
    task_id UUID REFERENCES masterplan_tasks(task_id) NOT NULL,

    -- Atom identification
    atom_number INTEGER NOT NULL,
    name VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,

    -- Code specifications
    language VARCHAR(50) NOT NULL,
    estimated_loc INTEGER DEFAULT 10,
    actual_loc INTEGER,
    complexity FLOAT DEFAULT 1.0,
    node_type VARCHAR(100),  -- AST node type

    -- Context (95% completeness)
    context_json JSONB NOT NULL,
    completeness_score FLOAT DEFAULT 0.0,

    -- Code
    code TEXT,

    -- Execution state
    status VARCHAR(50) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,

    -- Validation
    validation_passed BOOLEAN,
    validation_results JSONB,
    atomicity_score FLOAT,

    -- Confidence (Phase 7)
    confidence_score FLOAT,
    needs_human_review BOOLEAN DEFAULT FALSE,
    human_reviewed BOOLEAN DEFAULT FALSE,
    human_feedback TEXT,

    -- LLM metadata
    llm_model VARCHAR(100),
    llm_cost_usd FLOAT,
    llm_tokens_input INTEGER,
    llm_tokens_output INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT unique_task_atom UNIQUE (task_id, atom_number)
);

CREATE INDEX idx_atom_task ON atomic_units(task_id);
CREATE INDEX idx_atom_status ON atomic_units(status);
CREATE INDEX idx_atom_review ON atomic_units(needs_human_review, human_reviewed);

-- Phase 4: Atom Dependencies
CREATE TABLE atom_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    from_atom_id UUID REFERENCES atomic_units(id) NOT NULL,
    to_atom_id UUID REFERENCES atomic_units(id) NOT NULL,

    dependency_type VARCHAR(50) NOT NULL,  -- 'import', 'data', 'control', 'type'
    weight FLOAT DEFAULT 1.0,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_atom_dep UNIQUE (from_atom_id, to_atom_id)
);

CREATE INDEX idx_dep_from ON atom_dependencies(from_atom_id);
CREATE INDEX idx_dep_to ON atom_dependencies(to_atom_id);

-- Phase 4: Dependency Graph Metadata
CREATE TABLE dependency_graphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    masterplan_id UUID REFERENCES masterplans(masterplan_id) NOT NULL,

    -- Graph statistics
    total_atoms INTEGER NOT NULL,
    total_edges INTEGER NOT NULL,
    max_depth INTEGER,
    parallelizable_atoms INTEGER,

    -- Topological order (JSON array of atom IDs)
    execution_order JSONB NOT NULL,

    -- Parallel waves (JSON array of arrays)
    parallel_waves JSONB NOT NULL,

    -- Boundaries (module/component boundaries)
    boundaries JSONB,

    -- Graph serialization (for visualization)
    graph_json JSONB,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_graph_plan UNIQUE (masterplan_id)
);

CREATE INDEX idx_graph_plan ON dependency_graphs(masterplan_id);

-- Phase 5: Validation Results
CREATE TABLE validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    masterplan_id UUID REFERENCES masterplans(masterplan_id) NOT NULL,
    atom_id UUID REFERENCES atomic_units(id),

    -- Validation level
    validation_level VARCHAR(50) NOT NULL,  -- 'atomic', 'module', 'component', 'system'

    -- Results
    passed BOOLEAN NOT NULL,
    score FLOAT,
    violations JSONB,
    warnings JSONB,

    -- Context
    validated_at TIMESTAMP DEFAULT NOW(),
    duration_seconds FLOAT,

    -- Metadata
    validator_version VARCHAR(50)
);

CREATE INDEX idx_validation_plan ON validation_results(masterplan_id);
CREATE INDEX idx_validation_atom ON validation_results(atom_id);
CREATE INDEX idx_validation_level ON validation_results(validation_level);

-- Phase 6: Execution Waves
CREATE TABLE execution_waves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    masterplan_id UUID REFERENCES masterplans(masterplan_id) NOT NULL,

    wave_number INTEGER NOT NULL,
    atom_ids JSONB NOT NULL,  -- Array of atom IDs in this wave

    -- Wave state
    status VARCHAR(50) DEFAULT 'pending',
    total_atoms INTEGER NOT NULL,
    completed_atoms INTEGER DEFAULT 0,
    failed_atoms INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,

    CONSTRAINT unique_wave UNIQUE (masterplan_id, wave_number)
);

CREATE INDEX idx_wave_plan ON execution_waves(masterplan_id);

-- Phase 6: Retry History
CREATE TABLE atom_retry_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    atom_id UUID REFERENCES atomic_units(id) NOT NULL,

    attempt_number INTEGER NOT NULL,

    -- Failure info
    error_message TEXT,
    error_type VARCHAR(100),
    validation_errors JSONB,

    -- Retry strategy
    feedback_prompt TEXT,
    temperature FLOAT,

    -- Timing
    attempted_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_retry UNIQUE (atom_id, attempt_number)
);

CREATE INDEX idx_retry_atom ON atom_retry_history(atom_id);

-- Phase 7: Human Review Queue
CREATE TABLE human_review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    atom_id UUID REFERENCES atomic_units(id) NOT NULL,
    masterplan_id UUID REFERENCES masterplans(masterplan_id) NOT NULL,

    -- Confidence scoring
    confidence_score FLOAT NOT NULL,
    reasons JSONB,  -- Why flagged for review

    -- Review state
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'in_review', 'approved', 'rejected', 'regenerated'
    assigned_to VARCHAR(100),

    -- Review results
    human_decision VARCHAR(50),  -- 'approve', 'edit', 'regenerate'
    human_edits TEXT,
    human_comments TEXT,

    -- Timing
    queued_at TIMESTAMP DEFAULT NOW(),
    assigned_at TIMESTAMP,
    reviewed_at TIMESTAMP,

    CONSTRAINT unique_review_atom UNIQUE (atom_id)
);

CREATE INDEX idx_review_plan ON human_review_queue(masterplan_id);
CREATE INDEX idx_review_status ON human_review_queue(status);
CREATE INDEX idx_review_confidence ON human_review_queue(confidence_score);
```

#### Extend Existing Tables (Backward Compatible)
```sql
-- Add execution_mode to masterplans
ALTER TABLE masterplans
ADD COLUMN execution_mode VARCHAR(50) DEFAULT 'mvp';

-- Add mode-specific metrics
ALTER TABLE masterplans
ADD COLUMN v2_total_atoms INTEGER DEFAULT 0,
ADD COLUMN v2_avg_atom_loc FLOAT DEFAULT 0.0,
ADD COLUMN v2_atomization_time_seconds FLOAT,
ADD COLUMN v2_graph_build_time_seconds FLOAT;

-- Add mode to execution history
ALTER TABLE masterplan_history
ADD COLUMN execution_mode VARCHAR(50);

-- Create indexes
CREATE INDEX idx_masterplan_mode ON masterplans(execution_mode);
```

### 2.3 Service Layer: Abstraction Pattern

**Strategy**: Use Strategy Pattern for mode-specific execution

#### Unified Execution Interface
```python
# File: src/services/execution_interface.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from uuid import UUID

class ExecutionStrategy(ABC):
    """Abstract base class for execution strategies"""

    @abstractmethod
    async def atomize_plan(
        self,
        masterplan_id: UUID
    ) -> Dict[str, Any]:
        """Break down plan into execution units"""
        pass

    @abstractmethod
    async def build_execution_order(
        self,
        masterplan_id: UUID
    ) -> List[str]:
        """Determine execution order"""
        pass

    @abstractmethod
    async def execute_unit(
        self,
        unit_id: UUID
    ) -> Dict[str, Any]:
        """Execute a single unit"""
        pass

    @abstractmethod
    async def validate_unit(
        self,
        unit_id: UUID
    ) -> Dict[str, Any]:
        """Validate a unit"""
        pass

# File: src/services/mvp_strategy.py

class MVPExecutionStrategy(ExecutionStrategy):
    """MVP execution strategy (task-based, 25 LOC subtasks)"""

    async def atomize_plan(self, masterplan_id: UUID) -> Dict[str, Any]:
        """MVP doesn't need atomization - tasks are already defined"""
        # Load tasks from database
        # Return task structure
        pass

    async def build_execution_order(self, masterplan_id: UUID) -> List[str]:
        """Build task execution order (simple dependency resolution)"""
        # Use existing task dependency logic
        pass

    async def execute_unit(self, unit_id: UUID) -> Dict[str, Any]:
        """Execute task using TaskExecutor"""
        # Use existing TaskExecutor
        pass

    async def validate_unit(self, unit_id: UUID) -> Dict[str, Any]:
        """Validate task using CodeValidator"""
        # Use existing CodeValidator
        pass

# File: src/services/v2_strategy.py

class V2ExecutionStrategy(ExecutionStrategy):
    """V2 execution strategy (atom-based, 10 LOC atoms)"""

    async def atomize_plan(self, masterplan_id: UUID) -> Dict[str, Any]:
        """NEW: Atomize tasks using AST parsing"""
        # Use ASTAtomizationService
        pass

    async def build_execution_order(self, masterplan_id: UUID) -> List[str]:
        """NEW: Build dependency graph and topological order"""
        # Use DependencyAnalyzer
        pass

    async def execute_unit(self, unit_id: UUID) -> Dict[str, Any]:
        """NEW: Execute atom with retry loop"""
        # Use RetryOrchestrator
        pass

    async def validate_unit(self, unit_id: UUID) -> Dict[str, Any]:
        """NEW: 4-level hierarchical validation"""
        # Use HierarchicalValidator
        pass

# File: src/services/execution_orchestrator.py

class ExecutionOrchestrator:
    """Unified orchestrator that delegates to mode-specific strategies"""

    def __init__(self):
        self.strategies = {
            ExecutionMode.MVP: MVPExecutionStrategy(),
            ExecutionMode.V2_ATOMS: V2ExecutionStrategy()
        }

    def get_strategy(self, mode: ExecutionMode) -> ExecutionStrategy:
        """Get strategy for execution mode"""
        return self.strategies[mode]

    async def execute_masterplan(
        self,
        masterplan_id: UUID,
        mode: Optional[ExecutionMode] = None
    ) -> Dict[str, Any]:
        """
        Execute masterplan using specified mode.

        If mode not specified, determine from ModeConfig.
        """
        # Determine mode
        if mode is None:
            mode = ModeConfig.get_mode(plan_id=str(masterplan_id))

        # Get strategy
        strategy = self.get_strategy(mode)

        # Execute workflow
        # 1. Atomize plan
        atomization_result = await strategy.atomize_plan(masterplan_id)

        # 2. Build execution order
        execution_order = await strategy.build_execution_order(masterplan_id)

        # 3. Execute units
        for unit_id in execution_order:
            await strategy.execute_unit(unit_id)
            await strategy.validate_unit(unit_id)

        return {"status": "completed", "mode": mode.value}
```

### 2.4 API Layer: Versioned Endpoints

**Strategy**: Keep v1 (MVP) and add v2 (V2) endpoints

```python
# File: src/api/routers/v1/masterplan.py

from fastapi import APIRouter, Depends
from src.services.mvp_strategy import MVPExecutionStrategy

router_v1 = APIRouter(prefix="/api/v1", tags=["v1-masterplan"])

@router_v1.post("/masterplan/execute")
async def execute_masterplan_v1(masterplan_id: UUID):
    """Execute masterplan using MVP strategy (backward compatible)"""
    strategy = MVPExecutionStrategy()
    result = await strategy.atomize_plan(masterplan_id)
    # ... execute ...
    return result

# File: src/api/routers/v2/masterplan.py

from fastapi import APIRouter, Depends
from src.services.v2_strategy import V2ExecutionStrategy

router_v2 = APIRouter(prefix="/api/v2", tags=["v2-masterplan"])

@router_v2.post("/masterplan/atomize")
async def atomize_masterplan(masterplan_id: UUID):
    """NEW: Atomize masterplan using AST parsing"""
    # V2-specific atomization
    pass

@router_v2.post("/masterplan/execute")
async def execute_masterplan_v2(masterplan_id: UUID):
    """Execute masterplan using V2 strategy"""
    strategy = V2ExecutionStrategy()
    result = await strategy.atomize_plan(masterplan_id)
    # ... execute ...
    return result

# File: src/api/routers/unified.py

from fastapi import APIRouter
from src.services.execution_orchestrator import ExecutionOrchestrator

router_unified = APIRouter(prefix="/api", tags=["unified"])

@router_unified.post("/masterplan/execute")
async def execute_masterplan(
    masterplan_id: UUID,
    mode: Optional[str] = None
):
    """
    Unified endpoint that delegates to appropriate strategy.

    Mode detection:
    1. Explicit mode parameter
    2. User preference
    3. Plan configuration
    4. Default mode
    """
    orchestrator = ExecutionOrchestrator()

    execution_mode = None
    if mode:
        execution_mode = ExecutionMode(mode)

    result = await orchestrator.execute_masterplan(
        masterplan_id=masterplan_id,
        mode=execution_mode
    )

    return result
```

---

## 3. PHASED IMPLEMENTATION ROADMAP

### Phase-by-Phase Rollout Strategy

#### Phase 1: Foundation & Infrastructure (Week 1-2)

**Goal**: Set up V2 infrastructure without breaking MVP

**Tasks**:
1. Install tree-sitter dependencies
2. Create V2 database tables (atomic_units, etc.)
3. Run Alembic migrations (additive only)
4. Implement ModeConfig and feature flags
5. Create ExecutionStrategy interface
6. Implement MVPExecutionStrategy (wrap existing code)
7. Create API v2 routers (stub implementations)
8. Add unit tests for new infrastructure

**Success Criteria**:
- All tests pass (MVP + new infrastructure)
- MVP functionality unchanged
- V2 tables exist but empty
- Mode selection works (always returns MVP for now)

**Rollback**: Drop V2 tables, remove new code (MVP unaffected)

#### Phase 2: AST Atomization (Week 3-4)

**Goal**: Implement Phase 3 (AST parsing and atomization)

**Tasks**:
1. Implement MultiLanguageParser (tree-sitter)
2. Implement ASTClassifier
3. Implement RecursiveDecomposer
4. Implement ContextInjector (95% context)
5. Implement AtomicityValidator (10 criteria)
6. Implement ASTAtomizationPipeline
7. Create ASTAtomizationService
8. Add POST /api/v2/atomize/task endpoint
9. Add POST /api/v2/atomize/plan endpoint
10. Add comprehensive tests

**Success Criteria**:
- Can atomize single task to atoms
- Can atomize entire plan (50 tasks → 400-800 atoms)
- Context completeness ≥93%
- Validation pass rate ≥88%
- Processing time <5 sec/task

**Testing**:
- Test with sample Python code
- Test with sample TypeScript code
- Validate atom structure and context
- Verify database persistence

**Rollback**: Disable ENABLE_V2_ATOMIZATION flag

#### Phase 3: Dependency Graph (Week 5-6)

**Goal**: Implement Phase 4 (dependency analysis and graph)

**Tasks**:
1. Implement DependencyAnalyzer
2. Implement graph building (networkx)
3. Implement topological sort
4. Implement parallel wave detection
5. Implement boundary identification
6. Create DependencyGraphService
7. Add POST /api/v2/dependency-graph/build endpoint
8. Add GET /api/v2/dependency-graph/{id} endpoint
9. Add GET /api/v2/execution-waves/{id} endpoint
10. Add visualization support
11. Add tests

**Success Criteria**:
- Can build dependency graph for atomized plan
- Topological sort produces valid order
- Parallel waves identified correctly
- Cycle detection works
- Graph visualization available

**Testing**:
- Test with linear dependencies
- Test with parallel opportunities
- Test cycle detection
- Verify wave grouping

**Rollback**: Disable ENABLE_V2_DEP_GRAPH flag

#### Phase 4: Hierarchical Validation (Week 7-8)

**Goal**: Implement Phase 5 (4-level validation)

**Tasks**:
1. Implement AtomicValidator (Level 1)
2. Implement ModuleValidator (Level 2)
3. Implement ComponentValidator (Level 3)
4. Implement SystemValidator (Level 4)
5. Implement HierarchicalValidator orchestrator
6. Create ValidationService
7. Add POST /api/v2/validate/hierarchical endpoint
8. Add validation result storage
9. Add tests

**Success Criteria**:
- All 4 validation levels operational
- Atomic validation: 90% catch rate
- Module validation: 95% catch rate
- Component validation: 98% catch rate
- System validation: 99% catch rate

**Testing**:
- Test each validation level independently
- Test with known errors at each level
- Verify error reporting and bisection

**Rollback**: Disable ENABLE_V2_VALIDATION flag

#### Phase 5: Execution + Retry (Week 9-10)

**Goal**: Implement Phase 6 (atom execution with retry)

**Tasks**:
1. Implement DependencyAwareGenerator
2. Implement RetryOrchestrator (3 attempts)
3. Implement WaveExecutor (parallel execution)
4. Implement feedback loop for retries
5. Create V2ExecutionStrategy
6. Add POST /api/v2/execute/wave endpoint
7. Add retry history tracking
8. Add execution monitoring
9. Add tests

**Success Criteria**:
- Can execute atoms in dependency order
- Retry loop works (3 attempts)
- Parallel execution (50+ concurrent)
- Wave execution completes successfully
- Metrics tracked accurately

**Testing**:
- Test dependency-aware execution
- Test retry mechanism
- Test parallel wave execution
- Verify no cascading errors

**Rollback**: Disable ENABLE_V2_EXECUTION flag

#### Phase 6: Human Review (Week 11-12)

**Goal**: Implement Phase 7 (confidence scoring + review)

**Tasks**:
1. Implement ConfidenceScorer (ML-based)
2. Implement HumanReviewService
3. Create review queue management
4. Build review UI components
5. Add GET /api/v2/review-queue/{plan_id} endpoint
6. Add POST /api/v2/review/{atom_id} endpoint
7. Add review workflow logic
8. Add tests

**Success Criteria**:
- Confidence scoring identifies low-confidence atoms
- 15-20% flagged for review
- Review UI functional
- Human feedback integration works
- 99%+ precision achieved with review

**Testing**:
- Test confidence scoring accuracy
- Test review queue management
- Test feedback integration

**Rollback**: Disable ENABLE_V2_REVIEW flag

#### Phase 7: Integration & Testing (Week 13-14)

**Goal**: End-to-end V2 testing and optimization

**Tasks**:
1. End-to-end V2 workflow testing
2. Performance optimization
3. Cost optimization
4. Bug fixes and refinements
5. Documentation updates
6. User acceptance testing (UAT)
7. A/B testing setup

**Success Criteria**:
- Complete V2 workflow operational
- Precision ≥98% (autonomous)
- Time <2 hours
- Cost <$200
- All tests passing
- UAT approved

#### Phase 8: Gradual Rollout (Week 15-16)

**Goal**: Gradual production rollout

**Rollout Schedule**:
```
Week 15:
  - Day 1-2: 5% rollout (internal testing)
  - Day 3-4: 10% rollout (beta users)
  - Day 5-7: 25% rollout (early adopters)

Week 16:
  - Day 1-2: 50% rollout (general availability)
  - Day 3-4: 75% rollout
  - Day 5-7: 100% rollout (V2 default)
```

**Monitoring**:
- Track precision MVP vs V2
- Track execution time MVP vs V2
- Track cost MVP vs V2
- Track error rates
- User feedback collection

**Success Criteria**:
- V2 precision ≥ MVP precision
- V2 time < MVP time
- Error rate acceptable
- No major incidents

---

## 4. SACRIFICES & TRADE-OFFS

### 4.1 Performance Overhead

**Dual-Mode Complexity**:
- **Code Complexity**: +30% more code to maintain
- **Testing Surface**: 2x test matrix (MVP + V2)
- **Database Size**: +40% storage (V2 tables)
- **API Surface**: 2x endpoints (v1 + v2)

**Mitigation**:
- Strategy pattern keeps code organized
- Shared test utilities reduce duplication
- Separate tables prevent data bloat
- Unified endpoint reduces API confusion

### 4.2 Technical Debt

**Temporary Debt**:
- MVP code remains unchanged (no refactoring)
- Duplicate logic in some areas
- Two execution paths to maintain
- Migration state complexity

**Long-term Debt**:
- Will eventually deprecate MVP
- 6-12 month migration window
- MVP removal planned for V2.5

**Mitigation**:
- Clear deprecation timeline
- Automated migration tools
- Gradual feature parity

### 4.3 Development Time

**Additional Time**:
- Infrastructure setup: +2 weeks
- Dual-mode testing: +30% test time
- Documentation: +1 week
- Migration tooling: +1 week

**Total Overhead**: ~4 weeks additional development

**Mitigation**:
- Phased rollout reduces risk
- Parallel development possible
- Automated testing reduces manual QA

### 4.4 Cost Implications

**Infrastructure Costs**:
- Additional database storage: +$20/month
- Additional compute (parallel execution): +$50/month
- Monitoring and logging: +$10/month

**Development Costs**:
- 4 weeks additional development: $20K-40K

**Mitigation**:
- V2 cost savings offset infrastructure costs
- Faster execution reduces compute time
- Higher precision reduces rework costs

---

## 5. ROLLBACK STRATEGY

### 5.1 Instant Rollback (Emergency)

**Scenario**: Critical V2 bug discovered in production

**Action**:
```bash
# 1. Disable V2 via feature flags
export ENABLE_V2_ATOMIZATION=false
export ENABLE_V2_DEP_GRAPH=false
export ENABLE_V2_VALIDATION=false
export ENABLE_V2_EXECUTION=false
export V2_ROLLOUT_PERCENT=0

# 2. Restart services
docker-compose restart api

# 3. Verify rollback
curl http://localhost:8000/api/health
```

**Time to Rollback**: <5 minutes
**Impact**: All users revert to MVP immediately
**Data Loss**: None (V2 data preserved for debugging)

### 5.2 Gradual Rollback (Controlled)

**Scenario**: V2 precision below target, gradual rollback needed

**Action**:
```python
# Reduce rollout percentage gradually
V2_ROLLOUT_PERCENT = 75  # Day 1
V2_ROLLOUT_PERCENT = 50  # Day 2
V2_ROLLOUT_PERCENT = 25  # Day 3
V2_ROLLOUT_PERCENT = 10  # Day 4
V2_ROLLOUT_PERCENT = 0   # Day 5 (full rollback)
```

**Time to Rollback**: 5 days
**Impact**: Gradual user migration back to MVP
**Data Loss**: None

### 5.3 Complete Removal (Post-Mortem)

**Scenario**: V2 deemed not viable, permanent removal

**Action**:
```sql
-- Drop V2 tables
DROP TABLE human_review_queue CASCADE;
DROP TABLE atom_retry_history CASCADE;
DROP TABLE execution_waves CASCADE;
DROP TABLE validation_results CASCADE;
DROP TABLE dependency_graphs CASCADE;
DROP TABLE atom_dependencies CASCADE;
DROP TABLE atomic_units CASCADE;

-- Remove V2 columns from existing tables
ALTER TABLE masterplans DROP COLUMN execution_mode;
ALTER TABLE masterplans DROP COLUMN v2_total_atoms;
ALTER TABLE masterplans DROP COLUMN v2_avg_atom_loc;
ALTER TABLE masterplans DROP COLUMN v2_atomization_time_seconds;
ALTER TABLE masterplans DROP COLUMN v2_graph_build_time_seconds;
```

**Time to Rollback**: 1 hour
**Impact**: V2 completely removed
**Data Loss**: All V2 data deleted (backup recommended)

### 5.4 Rollback Decision Matrix

| Issue Severity | Rollback Strategy | Timeline |
|----------------|-------------------|----------|
| **Critical** (data loss, security) | Instant rollback | <5 min |
| **High** (precision <85%, crashes) | Gradual rollback | 3-5 days |
| **Medium** (precision 85-90%, slow) | Fix in place | 1-2 weeks |
| **Low** (minor bugs, UX issues) | Fix in next release | Next sprint |

---

## 6. SUCCESS METRICS & MONITORING

### 6.1 Technical Metrics

| Metric | MVP Baseline | V2 Target | Monitoring |
|--------|--------------|-----------|------------|
| **Precision** | 87.1% | ≥95% | Per-plan success rate |
| **Execution Time** | 13 hours | <2 hours | End-to-end timing |
| **Cost per Plan** | $160 | <$200 | LLM token usage |
| **Parallelization** | 2-3 tasks | 50+ atoms | Concurrent execution |
| **Context Completeness** | 70% | ≥95% | Context scoring |
| **Validation Pass Rate** | N/A | ≥90% | Atomicity validation |
| **Retry Success Rate** | N/A | ≥95% | 3-attempt success |

### 6.2 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **User Adoption** | 80% within 3 months | Active V2 users / total users |
| **User Satisfaction** | ≥4.5/5 | Post-execution survey |
| **Time to Value** | <2 hours | Discovery → complete code |
| **Error Recovery** | <5 min | Time to fix failed tasks |
| **Support Tickets** | <10/week | V2-related issues |

### 6.3 Monitoring Dashboard

**Real-time Metrics**:
```
DevMatrix V2 Dashboard
├── Execution Mode Distribution
│   ├── MVP: 40%
│   ├── V2: 60%
│   └── Rollout %: 60%
│
├── Precision Comparison
│   ├── MVP Avg: 87.1%
│   ├── V2 Avg: 96.3%
│   └── Delta: +9.2%
│
├── Performance Comparison
│   ├── MVP Avg Time: 13.2 hours
│   ├── V2 Avg Time: 1.7 hours
│   └── Improvement: 87% faster
│
├── Cost Comparison
│   ├── MVP Avg: $162
│   ├── V2 Avg: $185
│   └── Delta: +$23 (+14%)
│
└── System Health
    ├── API Response Time: 230ms
    ├── Database Load: 45%
    ├── Error Rate: 0.3%
    └── Active Plans: 127
```

---

## 7. RISK ANALYSIS & MITIGATION

### 7.1 Technical Risks

#### Risk 1: AST Parsing Failures
**Impact**: High (Phase 3 blocks everything)
**Probability**: Medium (complex code structures)
**Mitigation**:
- Extensive testing with diverse code samples
- Fallback to MVP for unparseable code
- Error handling with detailed logging
- Support for multiple languages

#### Risk 2: Dependency Graph Cycles
**Impact**: High (blocks execution)
**Probability**: Low (proper planning prevents)
**Mitigation**:
- Cycle detection in analyzer
- Automatic cycle breaking heuristics
- Manual review for complex cases
- Graph visualization for debugging

#### Risk 3: Validation False Positives
**Impact**: Medium (slower execution)
**Probability**: Medium (strict validation)
**Mitigation**:
- Tunable validation thresholds
- Manual override capability
- Continuous validation improvement
- Feedback loop for false positives

#### Risk 4: Parallel Execution Race Conditions
**Impact**: High (data corruption)
**Probability**: Medium (complex dependencies)
**Mitigation**:
- Atomic database operations
- Proper locking mechanisms
- Wave-based execution (controlled parallelism)
- Extensive concurrency testing

### 7.2 Business Risks

#### Risk 1: User Resistance to Change
**Impact**: Medium (slow adoption)
**Probability**: Medium (users prefer MVP)
**Mitigation**:
- Gradual rollout with opt-in
- Clear communication of benefits
- Side-by-side comparison
- User education and training

#### Risk 2: Migration Delays
**Impact**: Medium (extended dual-mode period)
**Probability**: High (complex system)
**Mitigation**:
- Buffer time in schedule
- Phased approach allows flexibility
- Regular progress reviews
- Contingency planning

#### Risk 3: Cost Overruns
**Impact**: Low (manageable increase)
**Probability**: Medium (V2 more expensive)
**Mitigation**:
- Cost monitoring and alerts
- Optimization opportunities
- V2 efficiency gains offset cost
- Transparent cost reporting

---

## 8. DECISION LOG

### Major Architectural Decisions

#### Decision 1: DUAL-MODE vs Big Bang Migration
**Date**: 2025-10-23
**Decision**: DUAL-MODE architecture
**Rationale**:
- Enables zero-downtime migration
- Reduces risk through gradual rollout
- Allows A/B testing and comparison
- Instant rollback capability
**Trade-offs**: Increased complexity, longer migration period

#### Decision 2: networkx vs Neo4j for Dependency Graph
**Date**: 2025-10-23
**Decision**: Start with networkx, migrate to Neo4j if needed
**Rationale**:
- networkx sufficient for <1000 atoms
- Neo4j adds infrastructure complexity
- Can migrate later without API changes
**Trade-offs**: May hit performance limits on large projects

#### Decision 3: Additive vs Replacement Schema
**Date**: 2025-10-23
**Decision**: Additive schema (new tables, extend existing)
**Rationale**:
- Preserves MVP functionality
- Enables rollback without data loss
- Simpler migration path
**Trade-offs**: More database tables, some duplication

#### Decision 4: Strategy Pattern vs Conditional Logic
**Date**: 2025-10-23
**Decision**: Strategy Pattern for mode selection
**Rationale**:
- Clean separation of concerns
- Easier testing and maintenance
- Supports future modes (hybrid, etc.)
**Trade-offs**: More classes and interfaces

---

## 9. IMPLEMENTATION CHECKLIST

### Pre-Migration Checklist
- [ ] Complete current MVP testing
- [ ] Document all MVP endpoints and behaviors
- [ ] Backup production database
- [ ] Set up staging environment
- [ ] Create rollback procedures
- [ ] Define success metrics
- [ ] Get stakeholder approval

### Phase 1: Foundation (Week 1-2)
- [ ] Install tree-sitter dependencies
- [ ] Create V2 database migrations
- [ ] Implement ModeConfig
- [ ] Implement ExecutionStrategy interface
- [ ] Implement MVPExecutionStrategy wrapper
- [ ] Create API v2 routers (stubs)
- [ ] Write unit tests
- [ ] Deploy to staging
- [ ] Verify MVP unchanged

### Phase 2: AST Atomization (Week 3-4)
- [ ] Implement MultiLanguageParser
- [ ] Implement ASTClassifier
- [ ] Implement RecursiveDecomposer
- [ ] Implement ContextInjector
- [ ] Implement AtomicityValidator
- [ ] Implement ASTAtomizationPipeline
- [ ] Create ASTAtomizationService
- [ ] Add atomization endpoints
- [ ] Write integration tests
- [ ] Deploy to staging
- [ ] Test with sample projects

### Phase 3: Dependency Graph (Week 5-6)
- [ ] Implement DependencyAnalyzer
- [ ] Implement graph building
- [ ] Implement topological sort
- [ ] Implement parallel wave detection
- [ ] Create DependencyGraphService
- [ ] Add graph endpoints
- [ ] Add visualization support
- [ ] Write tests
- [ ] Deploy to staging

### Phase 4: Hierarchical Validation (Week 7-8)
- [ ] Implement 4 validation levels
- [ ] Implement HierarchicalValidator
- [ ] Create ValidationService
- [ ] Add validation endpoints
- [ ] Write tests
- [ ] Deploy to staging

### Phase 5: Execution + Retry (Week 9-10)
- [ ] Implement DependencyAwareGenerator
- [ ] Implement RetryOrchestrator
- [ ] Implement WaveExecutor
- [ ] Create V2ExecutionStrategy
- [ ] Add execution endpoints
- [ ] Write tests
- [ ] Deploy to staging

### Phase 6: Human Review (Week 11-12)
- [ ] Implement ConfidenceScorer
- [ ] Implement HumanReviewService
- [ ] Build review UI
- [ ] Add review endpoints
- [ ] Write tests
- [ ] Deploy to staging

### Phase 7: Integration & Testing (Week 13-14)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Cost optimization
- [ ] Bug fixes
- [ ] Documentation updates
- [ ] UAT
- [ ] A/B test setup

### Phase 8: Gradual Rollout (Week 15-16)
- [ ] 5% rollout (internal)
- [ ] 10% rollout (beta users)
- [ ] 25% rollout (early adopters)
- [ ] 50% rollout (general availability)
- [ ] 75% rollout
- [ ] 100% rollout (V2 default)
- [ ] Monitor metrics
- [ ] Collect feedback
- [ ] Deprecate MVP (planned V2.5)

---

## 10. APPENDIX

### A. Key Files to Create/Modify

**New Files (V2)**:
```
src/config/execution_mode.py
src/services/execution_interface.py
src/services/mvp_strategy.py
src/services/v2_strategy.py
src/services/execution_orchestrator.py
src/services/ast_atomization_service.py
src/services/dependency_analyzer.py
src/services/hierarchical_validator.py
src/services/retry_orchestrator.py
src/services/wave_executor.py
src/services/confidence_scorer.py
src/services/human_review_service.py
src/api/routers/v2/atomization.py
src/api/routers/v2/dependency.py
src/api/routers/v2/validation.py
src/api/routers/v2/execution.py
src/api/routers/v2/review.py
src/mge_v2/atomization/parser.py
src/mge_v2/atomization/decomposer.py
src/mge_v2/atomization/context_injector.py
src/mge_v2/atomization/validator.py
src/mge_v2/dependencies/analyzer.py
src/mge_v2/dependencies/generator.py
src/mge_v2/validation/hierarchical.py
src/mge_v2/execution/retry.py
src/mge_v2/execution/wave.py
src/mge_v2/review/confidence.py
src/mge_v2/review/queue.py
```

**Modified Files (Integration)**:
```
src/api/main.py                          -- Add v2 routers
src/config/database.py                   -- Add V2 models
src/models/masterplan.py                 -- Add execution_mode
alembic/versions/XXX_add_v2_tables.py    -- V2 migrations
requirements.txt                         -- Add tree-sitter, networkx
docker-compose.yml                       -- Update env vars
.env.example                             -- Add V2 feature flags
```

### B. Environment Variables

```bash
# Execution Mode
DEVMATRIX_MODE=mvp                       # Default: mvp | v2_atoms | hybrid

# V2 Feature Flags
ENABLE_V2_ATOMIZATION=false
ENABLE_V2_DEP_GRAPH=false
ENABLE_V2_VALIDATION=false
ENABLE_V2_EXECUTION=false
ENABLE_V2_REVIEW=false

# Rollout Configuration
V2_ROLLOUT_PERCENT=0                     # 0-100

# V2 Performance Tuning
V2_MAX_PARALLEL_ATOMS=50                 # Max concurrent atoms
V2_RETRY_MAX_ATTEMPTS=3                  # Max retry attempts
V2_CONTEXT_COMPLETENESS_TARGET=0.95      # 95% target
V2_VALIDATION_STRICTNESS=medium          # low | medium | high

# Dependency Graph
V2_GRAPH_BACKEND=networkx                # networkx | neo4j
NEO4J_URI=bolt://localhost:7687          # If using Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### C. Database Migration Script

```python
# alembic/versions/XXX_add_v2_tables.py

"""Add V2 tables for MGE V2 DUAL-MODE support

Revision ID: XXX
Revises: YYY
Create Date: 2025-10-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'XXX'
down_revision = 'YYY'
branch_labels = None
depends_on = None

def upgrade():
    # Create atomic_units table
    op.create_table(
        'atomic_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('atom_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('language', sa.String(50), nullable=False),
        sa.Column('estimated_loc', sa.Integer(), default=10),
        sa.Column('actual_loc', sa.Integer()),
        sa.Column('complexity', sa.Float(), default=1.0),
        sa.Column('node_type', sa.String(100)),
        sa.Column('context_json', postgresql.JSONB(), nullable=False),
        sa.Column('completeness_score', sa.Float(), default=0.0),
        sa.Column('code', sa.Text()),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('attempts', sa.Integer(), default=0),
        sa.Column('validation_passed', sa.Boolean()),
        sa.Column('validation_results', postgresql.JSONB()),
        sa.Column('atomicity_score', sa.Float()),
        sa.Column('confidence_score', sa.Float()),
        sa.Column('needs_human_review', sa.Boolean(), default=False),
        sa.Column('human_reviewed', sa.Boolean(), default=False),
        sa.Column('human_feedback', sa.Text()),
        sa.Column('llm_model', sa.String(100)),
        sa.Column('llm_cost_usd', sa.Float()),
        sa.Column('llm_tokens_input', sa.Integer()),
        sa.Column('llm_tokens_output', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['task_id'], ['masterplan_tasks.task_id']),
        sa.UniqueConstraint('task_id', 'atom_number', name='unique_task_atom')
    )

    # Create indexes
    op.create_index('idx_atom_task', 'atomic_units', ['task_id'])
    op.create_index('idx_atom_status', 'atomic_units', ['status'])
    op.create_index('idx_atom_review', 'atomic_units', ['needs_human_review', 'human_reviewed'])

    # ... (create other V2 tables: atom_dependencies, dependency_graphs, etc.)

    # Extend existing masterplans table
    op.add_column('masterplans', sa.Column('execution_mode', sa.String(50), server_default='mvp'))
    op.add_column('masterplans', sa.Column('v2_total_atoms', sa.Integer(), default=0))
    op.add_column('masterplans', sa.Column('v2_avg_atom_loc', sa.Float(), default=0.0))
    op.add_column('masterplans', sa.Column('v2_atomization_time_seconds', sa.Float()))
    op.add_column('masterplans', sa.Column('v2_graph_build_time_seconds', sa.Float()))

    op.create_index('idx_masterplan_mode', 'masterplans', ['execution_mode'])

def downgrade():
    # Drop V2 tables in reverse order
    op.drop_table('human_review_queue')
    op.drop_table('atom_retry_history')
    op.drop_table('execution_waves')
    op.drop_table('validation_results')
    op.drop_table('dependency_graphs')
    op.drop_table('atom_dependencies')
    op.drop_table('atomic_units')

    # Remove V2 columns from masterplans
    op.drop_index('idx_masterplan_mode', table_name='masterplans')
    op.drop_column('masterplans', 'execution_mode')
    op.drop_column('masterplans', 'v2_total_atoms')
    op.drop_column('masterplans', 'v2_avg_atom_loc')
    op.drop_column('masterplans', 'v2_atomization_time_seconds')
    op.drop_column('masterplans', 'v2_graph_build_time_seconds')
```

---

## 11. CONCLUSION

### Migration Summary

La estrategia DUAL-MODE propuesta permite una migración segura y gradual de DevMatrix MVP a MGE V2, manteniendo ambos modos operativos simultáneamente durante el período de transición.

**Ventajas Clave**:
1. **Riesgo Minimizado**: Rollback instantáneo si V2 falla
2. **Validación Continua**: A/B testing entre MVP y V2
3. **Cero Downtime**: Usuarios no experimentan interrupciones
4. **Migración Gradual**: 16 semanas de implementación faseada
5. **Backward Compatible**: MVP continúa funcionando sin cambios

**Próximos Pasos**:
1. Aprobar estrategia de migración
2. Asignar recursos (equipo, tiempo, presupuesto)
3. Iniciar Phase 1: Foundation & Infrastructure
4. Establecer monitoring y alertas
5. Comunicar plan a stakeholders

**Target Timeline**: 16 semanas (4 meses) desde inicio hasta 100% rollout

**Expected Outcome**:
- Precision: 87% → 98% (+12.6%)
- Time: 13h → 1.5h (-87%)
- Cost: $160 → $185 (+15%, justified by quality)
- User Satisfaction: 4.5/5+

---

**Document Status**: DRAFT v1.0
**Review Required**: Technical Lead, Product Manager, Engineering Manager
**Next Update**: After stakeholder review and feedback
