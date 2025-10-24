# MGE V2 Migration Workflow
## DevMatrix MVP → MGE V2 (DUAL-MODE Strategy)

**Version**: 1.0
**Created**: 2025-10-23
**Strategy**: Adaptive DUAL-MODE (backward compatible)
**Duration**: 16 semanas (4 meses)
**Budget**: $27K-55K + $80/mes infraestructura

---

## 🎯 Executive Summary

### Current State (MVP)
- **Precisión**: 87.1%
- **Tiempo ejecución**: 13 horas
- **Granularidad**: 25 LOC/subtask
- **Paralelización**: 2-3 tasks concurrent
- **Stack**: Python, FastAPI, PostgreSQL, ChromaDB, Redis

### Target State (MGE V2)
- **Precisión**: 98% (autónomo) | 99%+ (con human review)
- **Tiempo ejecución**: 1-1.5 horas
- **Granularidad**: 10 LOC/atom
- **Paralelización**: 100+ atoms concurrent
- **Stack**: + tree-sitter, networkx, enhanced validation

### Benefits
- ✅ +12.6% precisión (87% → 98%)
- ✅ -87% tiempo (13h → 1.5h)
- ✅ 2.5x más granular
- ✅ 50x más paralelización
- ✅ ROI: 3-6 meses

---

## 📋 Gap Analysis: MVP vs V2

### Missing Database Models (7 nuevas tablas)

| Tabla | Propósito | Relaciones |
|-------|-----------|------------|
| `atomic_units` | Unidades atómicas de 10 LOC | FK: task_id |
| `atom_dependencies` | Grafo de dependencias | FK: from_atom_id, to_atom_id |
| `dependency_graphs` | Metadata de grafos | FK: masterplan_id |
| `validation_results` | Resultados de 4 niveles | FK: atom_id, level |
| `execution_waves` | Grupos de ejecución paralela | FK: graph_id |
| `atom_retry_history` | Historial de reintentos | FK: atom_id |
| `human_review_queue` | Cola de revisión humana | FK: atom_id |

### Missing Services (11 nuevos componentes)

#### Phase 3: AST Atomization
- `MultiLanguageParser` - Parser AST con tree-sitter
- `RecursiveDecomposer` - Descomposición recursiva
- `ContextInjector` - Inyección de contexto (95% completeness)
- `AtomicityValidator` - Validación de atomicidad

#### Phase 4: Dependency Graph
- `DependencyAnalyzer` - Construcción de grafo
- `TopologicalSorter` - Ordenamiento topológico
- `WaveGenerator` - Detección de grupos paralelos

#### Phase 5: Hierarchical Validation
- `HierarchicalValidator` - Coordinador de 4 niveles
- `AtomicValidator` - Nivel 1 validation
- `ModuleValidator` - Nivel 2 validation
- `ComponentValidator` - Nivel 3 validation
- `SystemValidator` - Nivel 4 validation

#### Phase 6: Execution + Retry
- `WaveExecutor` - Ejecución paralela por waves
- `RetryOrchestrator` - Gestión de 3 reintentos con feedback
- `FeedbackGenerator` - Generación de prompts de error

#### Phase 7: Human Review
- `ConfidenceScorer` - Scoring de confianza
- `ReviewQueueManager` - Gestión de cola de revisión
- `AIAssistant` - Sugerencias de fixes

### Missing Technology Stack

| Tecnología | Propósito | Versión | Criticidad |
|------------|-----------|---------|------------|
| **tree-sitter** | AST parsing multi-lenguaje | 0.20+ | 🔴 CRÍTICO |
| tree-sitter-python | Python AST | latest | 🔴 CRÍTICO |
| tree-sitter-typescript | TypeScript AST | latest | 🟡 IMPORTANTE |
| tree-sitter-javascript | JavaScript AST | latest | 🟡 IMPORTANTE |
| **networkx** | Dependency graph operations | 3.0+ | 🔴 CRÍTICO |
| pytest-xdist | Parallel testing | latest | 🟢 RECOMENDADO |

### Missing API Endpoints (12 nuevos v2)

```
POST   /api/v2/atomization/analyze      - Analizar task para atomización
POST   /api/v2/atomization/decompose    - Descomponer task en atoms
GET    /api/v2/atoms/{atom_id}          - Obtener atom details
GET    /api/v2/graphs/{graph_id}        - Obtener dependency graph
POST   /api/v2/validation/atomic        - Validar atom individual
POST   /api/v2/validation/hierarchical  - Validar módulo/componente
POST   /api/v2/execution/waves          - Ejecutar wave paralelo
GET    /api/v2/execution/status         - Estado ejecución detallado
POST   /api/v2/retry/{atom_id}          - Reintentar atom fallido
GET    /api/v2/review/queue             - Cola de revisión humana
POST   /api/v2/review/approve           - Aprobar atom revisado
GET    /api/v2/metrics                  - Métricas V2 detalladas
```

---

## 🏗️ DUAL-MODE Architecture Design

### Execution Mode Enum

```python
# src/models/execution_mode.py
from enum import Enum

class ExecutionMode(str, Enum):
    """Execution mode selection"""
    MVP = "mvp"              # Task-based (25 LOC subtasks)
    V2_ATOMS = "v2_atoms"    # Atom-based (10 LOC atoms)
    HYBRID = "hybrid"        # Selective per phase
```

### Strategy Pattern Implementation

```python
# src/execution/strategies.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ExecutionStrategy(ABC):
    """Abstract execution strategy"""

    @abstractmethod
    async def execute_masterplan(
        self,
        masterplan_id: UUID,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute masterplan with specific strategy"""
        pass

    @abstractmethod
    def get_execution_units(
        self,
        masterplan: MasterPlan
    ) -> List[ExecutionUnit]:
        """Get execution units (tasks or atoms)"""
        pass

class MVPExecutionStrategy(ExecutionStrategy):
    """MVP task-based execution"""

    def __init__(self, task_executor: TaskExecutor):
        self.task_executor = task_executor

    async def execute_masterplan(
        self,
        masterplan_id: UUID,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Wrap existing TaskExecutor logic
        tasks = self._load_tasks(masterplan_id)
        results = []

        for task in tasks:
            if self._check_dependencies(task):
                result = await self.task_executor.execute_task(task.task_id)
                results.append(result)

        return {"mode": "mvp", "results": results}

    def get_execution_units(
        self,
        masterplan: MasterPlan
    ) -> List[MasterPlanTask]:
        # Return tasks as execution units
        return self._load_all_tasks(masterplan)

class V2ExecutionStrategy(ExecutionStrategy):
    """V2 atom-based execution"""

    def __init__(
        self,
        atomizer: RecursiveDecomposer,
        dependency_analyzer: DependencyAnalyzer,
        wave_executor: WaveExecutor,
        validator: HierarchicalValidator
    ):
        self.atomizer = atomizer
        self.dependency_analyzer = dependency_analyzer
        self.wave_executor = wave_executor
        self.validator = validator

    async def execute_masterplan(
        self,
        masterplan_id: UUID,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Phase 3: Atomization
        atoms = await self.atomizer.decompose_all_tasks(masterplan_id)

        # Phase 4: Dependency Graph
        graph = await self.dependency_analyzer.build_graph(atoms)
        waves = graph.get_parallel_waves()

        # Phase 5-6: Validation + Execution
        results = []
        for wave in waves:
            wave_results = await self.wave_executor.execute_wave(
                wave_atoms=wave,
                validator=self.validator
            )
            results.extend(wave_results)

        return {
            "mode": "v2_atoms",
            "atoms_total": len(atoms),
            "waves_executed": len(waves),
            "results": results
        }

    def get_execution_units(
        self,
        masterplan: MasterPlan
    ) -> List[AtomicUnit]:
        # Return atoms as execution units
        return self._load_all_atoms(masterplan)

class ExecutionOrchestrator:
    """Unified orchestrator for both modes"""

    def __init__(self):
        self.strategies: Dict[ExecutionMode, ExecutionStrategy] = {}

    def register_strategy(
        self,
        mode: ExecutionMode,
        strategy: ExecutionStrategy
    ):
        self.strategies[mode] = strategy

    async def execute(
        self,
        masterplan_id: UUID,
        mode: ExecutionMode,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute using specified mode"""
        if mode not in self.strategies:
            raise ValueError(f"No strategy registered for mode: {mode}")

        strategy = self.strategies[mode]
        return await strategy.execute_masterplan(masterplan_id, context)
```

### Feature Flags Configuration

```python
# src/config/feature_flags.py
from pydantic import BaseSettings

class FeatureFlags(BaseSettings):
    """Feature flags for V2 features"""

    # Global toggle
    ENABLE_V2: bool = False

    # Gradual rollout
    V2_PERCENTAGE: int = 0  # 0-100%
    V2_WHITELIST_USERS: list[str] = []
    V2_BLACKLIST_USERS: list[str] = []

    # Phase-specific toggles
    ENABLE_AST_ATOMIZATION: bool = False
    ENABLE_DEPENDENCY_GRAPH: bool = False
    ENABLE_HIERARCHICAL_VALIDATION: bool = False
    ENABLE_WAVE_EXECUTION: bool = False
    ENABLE_RETRY_FEEDBACK: bool = False
    ENABLE_HUMAN_REVIEW: bool = False

    # Fallback behavior
    FALLBACK_TO_MVP_ON_ERROR: bool = True

    class Config:
        env_prefix = "FF_"

def get_execution_mode(user_id: str, flags: FeatureFlags) -> ExecutionMode:
    """Determine execution mode for user"""

    # Blacklist check
    if user_id in flags.V2_BLACKLIST_USERS:
        return ExecutionMode.MVP

    # Whitelist check
    if user_id in flags.V2_WHITELIST_USERS:
        return ExecutionMode.V2_ATOMS

    # Global toggle
    if not flags.ENABLE_V2:
        return ExecutionMode.MVP

    # Percentage rollout
    import hashlib
    hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    if (hash_value % 100) < flags.V2_PERCENTAGE:
        return ExecutionMode.V2_ATOMS

    return ExecutionMode.MVP
```

### Database Schema Additions (Aditivo, no destructivo)

```sql
-- Phase 3: AST Atomization
CREATE TABLE atomic_units (
    atom_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES masterplan_tasks(task_id),
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id),

    -- Atom identification
    atom_number INTEGER NOT NULL,
    name VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,

    -- Code specs
    language VARCHAR(50) NOT NULL,
    estimated_loc INTEGER NOT NULL,
    actual_loc INTEGER,
    complexity DECIMAL(5,2) NOT NULL,

    -- Context (95% completeness target)
    context_json JSONB NOT NULL,
    imports JSONB,
    types JSONB,
    preconditions JSONB,
    postconditions JSONB,
    test_cases JSONB,

    -- Dependencies
    depends_on_atoms UUID[],

    -- Execution state
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    code TEXT,
    attempts INTEGER DEFAULT 0,

    -- Validation
    validation_results JSONB,
    confidence_score DECIMAL(3,2),
    is_atomic BOOLEAN DEFAULT true,
    atomicity_score DECIMAL(3,2),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_at TIMESTAMPTZ,
    validated_at TIMESTAMPTZ,

    CONSTRAINT fk_task FOREIGN KEY (task_id) REFERENCES masterplan_tasks(task_id) ON DELETE CASCADE,
    CONSTRAINT fk_masterplan FOREIGN KEY (masterplan_id) REFERENCES masterplans(masterplan_id) ON DELETE CASCADE
);

CREATE INDEX idx_atom_task ON atomic_units(task_id);
CREATE INDEX idx_atom_masterplan ON atomic_units(masterplan_id);
CREATE INDEX idx_atom_status ON atomic_units(status);
CREATE INDEX idx_atom_confidence ON atomic_units(confidence_score);

-- Phase 4: Dependency Graph
CREATE TABLE dependency_graphs (
    graph_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id) UNIQUE,

    -- Graph metadata
    total_atoms INTEGER NOT NULL,
    total_edges INTEGER NOT NULL,
    max_depth INTEGER NOT NULL,
    total_waves INTEGER NOT NULL,

    -- Graph data
    nodes_json JSONB NOT NULL,
    edges_json JSONB NOT NULL,
    topological_order UUID[] NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_masterplan FOREIGN KEY (masterplan_id) REFERENCES masterplans(masterplan_id) ON DELETE CASCADE
);

CREATE INDEX idx_graph_masterplan ON dependency_graphs(masterplan_id);

CREATE TABLE atom_dependencies (
    dependency_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_id UUID NOT NULL REFERENCES dependency_graphs(graph_id),
    from_atom_id UUID NOT NULL REFERENCES atomic_units(atom_id),
    to_atom_id UUID NOT NULL REFERENCES atomic_units(atom_id),

    -- Dependency metadata
    dependency_type VARCHAR(50) NOT NULL, -- 'import', 'data', 'control', 'type'
    weight DECIMAL(3,2) DEFAULT 1.0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_graph FOREIGN KEY (graph_id) REFERENCES dependency_graphs(graph_id) ON DELETE CASCADE,
    CONSTRAINT fk_from_atom FOREIGN KEY (from_atom_id) REFERENCES atomic_units(atom_id) ON DELETE CASCADE,
    CONSTRAINT fk_to_atom FOREIGN KEY (to_atom_id) REFERENCES atomic_units(atom_id) ON DELETE CASCADE,
    CONSTRAINT unique_dependency UNIQUE (from_atom_id, to_atom_id)
);

CREATE INDEX idx_dep_from ON atom_dependencies(from_atom_id);
CREATE INDEX idx_dep_to ON atom_dependencies(to_atom_id);
CREATE INDEX idx_dep_graph ON atom_dependencies(graph_id);

CREATE TABLE execution_waves (
    wave_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_id UUID NOT NULL REFERENCES dependency_graphs(graph_id),

    -- Wave info
    wave_number INTEGER NOT NULL,
    atom_ids UUID[] NOT NULL,
    atom_count INTEGER NOT NULL,

    -- Execution state
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Performance
    duration_seconds DECIMAL(10,2),
    parallelization_factor INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_graph FOREIGN KEY (graph_id) REFERENCES dependency_graphs(graph_id) ON DELETE CASCADE
);

CREATE INDEX idx_wave_graph ON execution_waves(graph_id);
CREATE INDEX idx_wave_status ON execution_waves(status);

-- Phase 5: Hierarchical Validation
CREATE TABLE validation_results (
    validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    atom_id UUID REFERENCES atomic_units(atom_id),
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id),

    -- Validation level
    level INTEGER NOT NULL, -- 1=atomic, 2=module, 3=component, 4=system
    level_name VARCHAR(50) NOT NULL,

    -- Results
    passed BOOLEAN NOT NULL,
    errors JSONB,
    warnings JSONB,

    -- Checks performed
    checks_run JSONB NOT NULL,
    checks_passed INTEGER NOT NULL,
    checks_failed INTEGER NOT NULL,

    -- Performance
    duration_seconds DECIMAL(10,2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_atom FOREIGN KEY (atom_id) REFERENCES atomic_units(atom_id) ON DELETE CASCADE,
    CONSTRAINT fk_masterplan FOREIGN KEY (masterplan_id) REFERENCES masterplans(masterplan_id) ON DELETE CASCADE
);

CREATE INDEX idx_validation_atom ON validation_results(atom_id);
CREATE INDEX idx_validation_level ON validation_results(level);
CREATE INDEX idx_validation_passed ON validation_results(passed);

-- Phase 6: Retry History
CREATE TABLE atom_retry_history (
    retry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    atom_id UUID NOT NULL REFERENCES atomic_units(atom_id),

    -- Retry info
    attempt_number INTEGER NOT NULL,
    error_message TEXT,
    feedback_prompt TEXT,

    -- Result
    success BOOLEAN NOT NULL,
    code_generated TEXT,

    -- LLM metadata
    llm_model VARCHAR(100),
    llm_cost_usd DECIMAL(10,6),
    llm_tokens_input INTEGER,
    llm_tokens_output INTEGER,
    temperature DECIMAL(3,2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_atom FOREIGN KEY (atom_id) REFERENCES atomic_units(atom_id) ON DELETE CASCADE
);

CREATE INDEX idx_retry_atom ON atom_retry_history(atom_id);
CREATE INDEX idx_retry_success ON atom_retry_history(success);

-- Phase 7: Human Review
CREATE TABLE human_review_queue (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    atom_id UUID NOT NULL REFERENCES atomic_units(atom_id),
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id),

    -- Queue info
    confidence_score DECIMAL(3,2) NOT NULL,
    priority INTEGER NOT NULL, -- Lower confidence = higher priority

    -- Review state
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, in_review, approved, rejected, regenerated
    assigned_to VARCHAR(100),

    -- AI suggestions
    ai_suggestions JSONB,
    issue_detected TEXT,

    -- Human decision
    decision VARCHAR(50),
    human_feedback TEXT,
    modified_code TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,

    CONSTRAINT fk_atom FOREIGN KEY (atom_id) REFERENCES atomic_units(atom_id) ON DELETE CASCADE,
    CONSTRAINT fk_masterplan FOREIGN KEY (masterplan_id) REFERENCES masterplans(masterplan_id) ON DELETE CASCADE
);

CREATE INDEX idx_review_status ON human_review_queue(status);
CREATE INDEX idx_review_confidence ON human_review_queue(confidence_score);
CREATE INDEX idx_review_assigned ON human_review_queue(assigned_to);
```

---

## 📅 8-Phase Implementation Roadmap

### Phase 1: Foundation & Infrastructure (Semana 1-2)

**Objetivo**: Preparar base técnica y organizacional

**Tareas**:
- [ ] Setup feature flags system
  - `src/config/feature_flags.py`
  - Environment variables configuration
  - Gradual rollout logic
- [ ] Create execution mode enum
  - `src/models/execution_mode.py`
- [ ] Implement Strategy Pattern base
  - `src/execution/strategies.py` (abstract + MVP wrapper)
- [ ] Create ExecutionOrchestrator
  - `src/execution/orchestrator.py`
- [ ] Database migrations for 7 new tables
  - `alembic/versions/202510xx_add_v2_tables.py`
- [ ] Add monitoring & logging for V2
  - Prometheus metrics
  - Structured logging with mode tag
- [ ] Setup staging environment
  - Docker compose with V2 flags
- [ ] Create rollback procedures documentation

**Deliverables**:
- ✅ Feature flags funcionando
- ✅ Database schema V2 deployed
- ✅ Strategy Pattern base ready
- ✅ Monitoring configurado
- ✅ Rollback procedures documentados

**Testing**:
- Unit tests para feature flags
- Migration tests (up/down)
- Strategy pattern tests

**Criterio de éxito**:
- Sistema puede toggle entre MVP/V2 sin errores
- Rollback funciona en <5 minutos
- 100% backward compatibility con MVP

---

### Phase 2: AST Atomization (Semana 3-4)

**Objetivo**: Implementar Phase 3 de MGE V2 (atomización con tree-sitter)

**Tareas**:
- [ ] Install tree-sitter dependencies
  ```bash
  pip install tree-sitter==0.20.1
  pip install tree-sitter-python tree-sitter-typescript tree-sitter-javascript
  ```
- [ ] Implement MultiLanguageParser
  - `src/atomization/parser.py`
  - Support Python, TypeScript, JavaScript
  - AST extraction methods
  - Complexity calculation
- [ ] Implement RecursiveDecomposer
  - `src/atomization/decomposer.py`
  - Recursive splitting logic
  - Atomicity validation (10 LOC, complexity <3.0)
  - Decomposition result models
- [ ] Implement ContextInjector
  - `src/atomization/context_injector.py`
  - 95% context completeness target
  - Schema extraction
  - Preconditions/postconditions inference
  - Test case generation
- [ ] Implement AtomicityValidator
  - `src/atomization/validator.py`
  - 10 atomicity criteria checks
- [ ] Create AtomService
  - `src/services/atom_service.py`
  - CRUD for atomic_units table
  - Decomposition orchestration
- [ ] API endpoints for atomization
  - `POST /api/v2/atomization/analyze`
  - `POST /api/v2/atomization/decompose`
  - `GET /api/v2/atoms/{atom_id}`

**Deliverables**:
- ✅ Tree-sitter parsing funcionando
- ✅ Task → Atoms decomposition working
- ✅ Context injection con 95% completeness
- ✅ AtomicityValidator passing criteria

**Testing**:
- Unit tests para cada parser (Python, TS, JS)
- Decomposition tests con tasks reales del MVP
- Context completeness tests (target 95%)
- Edge cases: large functions, complex classes

**Criterio de éxito**:
- 1 task (80 LOC) → 8 atoms (10 LOC cada uno)
- Context completeness ≥95%
- Atomicity score >0.9 en 90% de atoms

---

### Phase 3: Dependency Graph (Semana 5-6)

**Objetivo**: Implementar Phase 4 de MGE V2 (grafo de dependencias)

**Tareas**:
- [ ] Install networkx
  ```bash
  pip install networkx==3.1
  ```
- [ ] Implement DependencyAnalyzer
  - `src/dependencies/analyzer.py`
  - Import dependency detection
  - Data flow analysis
  - Function call detection
  - Type dependency detection
- [ ] Implement graph operations
  - `src/dependencies/graph.py`
  - Build networkx DiGraph
  - Topological sort
  - Cycle detection
  - Level-based grouping
- [ ] Implement WaveGenerator
  - `src/dependencies/wave_generator.py`
  - Parallel group detection
  - Boundary identification
- [ ] Create DependencyService
  - `src/services/dependency_service.py`
  - Graph building orchestration
  - Wave management
- [ ] API endpoints for dependencies
  - `GET /api/v2/graphs/{graph_id}`
  - `GET /api/v2/graphs/{graph_id}/waves`
  - `GET /api/v2/graphs/{graph_id}/visualize`

**Deliverables**:
- ✅ Dependency graph construction
- ✅ Topological sort funcionando
- ✅ Wave generation (100+ atoms paralelos)
- ✅ Cycle detection working

**Testing**:
- Dependency detection accuracy tests
- Topological sort correctness
- Cycle detection tests
- Wave grouping tests (parallelization >50x)

**Criterio de éxito**:
- 800 atoms → 8-10 waves
- 100+ atoms por wave en promedio
- Cycle detection previene deadlocks
- Topological order es correcto

---

### Phase 4: Hierarchical Validation (Semana 7-8)

**Objetivo**: Implementar Phase 5 de MGE V2 (validación en 4 niveles)

**Tareas**:
- [ ] Implement AtomicValidator (Level 1)
  - `src/validation/atomic_validator.py`
  - Syntax check (AST parsing)
  - Type check (mypy/pyright)
  - Unit test generation & execution
  - Atomicity criteria validation
- [ ] Implement ModuleValidator (Level 2)
  - `src/validation/module_validator.py`
  - Integration tests (10-20 atoms)
  - API consistency checks
  - Cohesion analysis
- [ ] Implement ComponentValidator (Level 3)
  - `src/validation/component_validator.py`
  - Component E2E tests
  - Architecture compliance
  - Performance benchmarks
- [ ] Implement SystemValidator (Level 4)
  - `src/validation/system_validator.py`
  - Full system E2E
  - Acceptance criteria
  - Production readiness checks
- [ ] Implement HierarchicalValidator coordinator
  - `src/validation/hierarchical_validator.py`
  - Orchestrates 4 levels
  - Boundary detection integration
  - Progressive validation
- [ ] Create ValidationService
  - `src/services/validation_service.py`
  - Validation orchestration
  - Result persistence
- [ ] API endpoints for validation
  - `POST /api/v2/validation/atomic`
  - `POST /api/v2/validation/module`
  - `POST /api/v2/validation/component`
  - `POST /api/v2/validation/system`
  - `GET /api/v2/validation/results/{atom_id}`

**Deliverables**:
- ✅ 4-level validation system
- ✅ Boundary-aware validation
- ✅ Early error detection
- ✅ Progressive integration testing

**Testing**:
- Each validator level unit tests
- Integration between levels
- False positive rate <5%
- Validation time <2 min per atom

**Criterio de éxito**:
- Level 1: 99% syntax correctness
- Level 2: 95% integration pass rate
- Level 3: 90% component E2E pass
- Level 4: 85% system E2E pass
- Early error detection >90%

---

### Phase 5: Execution + Retry (Semana 9-10)

**Objetivo**: Implementar Phase 6 de MGE V2 (ejecución con retry feedback)

**Tareas**:
- [ ] Implement WaveExecutor
  - `src/execution/wave_executor.py`
  - Parallel execution (100+ concurrent)
  - Dependency-aware coordination
  - Progress tracking per wave
- [ ] Implement RetryOrchestrator
  - `src/execution/retry_orchestrator.py`
  - 3-attempt retry loop
  - Error analysis
  - Feedback prompt generation
  - Temperature adjustment (0.7 → 0.5 → 0.3)
- [ ] Implement FeedbackGenerator
  - `src/execution/feedback_generator.py`
  - Error message parsing
  - Context-aware prompts
  - Previous attempt analysis
- [ ] Implement ProgressiveIntegrationTester
  - `src/execution/integration_tester.py`
  - Run integration tests every 10 atoms
  - Bisect to find culprits on failure
- [ ] Create ExecutionService (V2)
  - `src/services/execution_service_v2.py`
  - Wave-based execution orchestration
  - Retry management
  - Progress webhooks
- [ ] Integrate V2ExecutionStrategy
  - Complete implementation in `strategies.py`
  - Wire all V2 components
- [ ] API endpoints for execution
  - `POST /api/v2/execution/start`
  - `GET /api/v2/execution/status/{masterplan_id}`
  - `POST /api/v2/execution/waves/{wave_id}/execute`
  - `POST /api/v2/retry/{atom_id}`

**Deliverables**:
- ✅ Wave-based parallel execution
- ✅ Retry with feedback working
- ✅ Progressive integration testing
- ✅ 100+ atoms concurrent

**Testing**:
- Parallel execution stress tests
- Retry logic tests (success rate)
- Feedback quality tests
- Integration tester accuracy

**Criterio de éxito**:
- 90% atoms success on attempt 1
- 99% success after 3 attempts
- 100+ atoms executing in parallel
- Retry reduces errors by 50%+

---

### Phase 6: Human Review System (Semana 11-12)

**Objetivo**: Implementar Phase 7 de MGE V2 (optional human review)

**Tareas**:
- [ ] Implement ConfidenceScorer
  - `src/review/confidence_scorer.py`
  - Validation results weight (40%)
  - Attempts needed weight (30%)
  - Complexity weight (20%)
  - Integration tests weight (10%)
  - Score formula: 0.0-1.0
- [ ] Implement ReviewQueueManager
  - `src/review/queue_manager.py`
  - Sort by confidence (lowest first)
  - Select bottom 15-20%
  - Priority assignment
- [ ] Implement AIAssistant
  - `src/review/ai_assistant.py`
  - Issue detection
  - Fix suggestions
  - Alternative implementations
- [ ] Create ReviewService
  - `src/services/review_service.py`
  - Queue management
  - Review workflow
  - Decision tracking
- [ ] Build Review UI (React)
  - `src/ui/src/pages/ReviewQueue.tsx`
  - Code viewer with diff
  - AI suggestions panel
  - Approve/Edit/Regenerate actions
  - Real-time updates via WebSocket
- [ ] API endpoints for review
  - `GET /api/v2/review/queue`
  - `GET /api/v2/review/{review_id}`
  - `POST /api/v2/review/approve`
  - `POST /api/v2/review/reject`
  - `POST /api/v2/review/regenerate`
  - `POST /api/v2/review/edit`

**Deliverables**:
- ✅ Confidence scoring system
- ✅ Review queue con priorización
- ✅ AI-assisted review interface
- ✅ Human workflow completo

**Testing**:
- Confidence scoring accuracy
- Queue prioritization correctness
- AI suggestions quality
- UI/UX testing

**Criterio de éxito**:
- Confidence score correlates with actual quality
- 15-20% atoms flagged for review
- Review time <30 seconds per atom
- 99%+ precision con human review

---

### Phase 7: Integration & Testing (Semana 13-14)

**Objetivo**: Integración completa y testing E2E

**Tareas**:
- [ ] End-to-end testing
  - `tests/e2e/test_v2_full_flow.py`
  - Discovery → Masterplan → Atomization → Execution → Review
  - Test con proyecto real (50 tasks → 800 atoms)
- [ ] Performance testing
  - Measure execution time (target: <1.5h)
  - Measure precision (target: ≥98%)
  - Measure cost (target: <$200)
  - Parallel throughput (target: 100+ atoms)
- [ ] Load testing
  - Multiple concurrent masterplans
  - Database performance under load
  - API response times
- [ ] Integration testing entre modos
  - MVP → V2 migration path
  - V2 → MVP fallback
  - Hybrid mode testing
- [ ] Security testing
  - Code injection attempts
  - Sandbox escape attempts
  - Authentication/authorization
- [ ] Documentation
  - API documentation (Swagger)
  - Architecture diagrams
  - Developer onboarding guide
  - Troubleshooting guide

**Deliverables**:
- ✅ E2E tests passing
- ✅ Performance benchmarks met
- ✅ Load tests passing
- ✅ Security audit passed
- ✅ Documentation completa

**Testing**:
- 10+ real projects executed
- All 4 success criteria met
- Zero critical bugs
- Performance targets achieved

**Criterio de éxito**:
- Precisión ≥98% (autonomous)
- Tiempo <1.5 horas
- Costo <$200
- 100+ atoms paralelos
- Zero critical security issues

---

### Phase 8: Gradual Rollout (Semana 15-16)

**Objetivo**: Despliegue gradual a producción

**Tareas**:
- [ ] Week 15: 5% rollout
  - Enable V2 for 5% users (whitelist or percentage)
  - Monitor metrics closely
  - Collect user feedback
  - Fix critical issues immediately
- [ ] Week 15 mid: 10% rollout
  - Expand to 10% if 5% stable
  - Performance monitoring
  - Cost tracking
- [ ] Week 16: 25% rollout
  - Expand to 25%
  - A/B testing MVP vs V2
  - Gather comparative metrics
- [ ] Week 16 mid: 50% rollout
  - Expand to 50%
  - Final bug fixes
  - Documentation updates
- [ ] Week 16 end: 100% rollout
  - Full V2 deployment
  - MVP mode still available (feature flag)
  - Celebrate! 🎉

**Deliverables**:
- ✅ Gradual rollout completed
- ✅ V2 stable en production
- ✅ Metrics showing improvements
- ✅ User feedback positive

**Monitoring**:
- Precision tracking (target: ≥98%)
- Execution time (target: <1.5h)
- Error rates (<1%)
- User satisfaction (≥4.5/5)
- Support tickets (<10/week)

**Rollback Triggers**:
- Precision drops below 90%
- Execution time >3 hours
- Error rate >5%
- Critical bugs discovered
- User satisfaction <4.0/5

**Criterio de éxito**:
- 100% rollout achieved
- All success metrics met
- <5 support tickets per week
- User feedback ≥4.5/5
- ROI tracking initiated

---

## 🔄 Rollback Strategy

### Emergency Rollback (<5 minutos)

```bash
# 1. Disable V2 globally
export FF_ENABLE_V2=false

# 2. Restart services
docker-compose restart backend

# 3. Verify MVP mode active
curl http://localhost:8000/api/v1/health | jq '.execution_mode'
# Should return: "mvp"
```

**Cuando usar**: Critical production issue, error rate >10%, system down

### Gradual Rollback (3-5 días)

```python
# Day 1: Reduce to 50%
feature_flags.V2_PERCENTAGE = 50

# Day 2: Reduce to 25%
feature_flags.V2_PERCENTAGE = 25

# Day 3: Reduce to 10%
feature_flags.V2_PERCENTAGE = 10

# Day 4: Reduce to 5%
feature_flags.V2_PERCENTAGE = 5

# Day 5: Full rollback
feature_flags.ENABLE_V2 = False
```

**Cuando usar**: Minor issues, user complaints, performance degradation

### Partial Rollback (Phase-specific)

```python
# Disable specific V2 features while keeping others
feature_flags.ENABLE_AST_ATOMIZATION = False  # Use MVP task splitting
feature_flags.ENABLE_DEPENDENCY_GRAPH = True  # Keep graph benefits
feature_flags.ENABLE_HIERARCHICAL_VALIDATION = True
```

**Cuando usar**: Specific component failing, targeted issues

### Complete Rollback (1 hora)

```sql
-- Drop V2 tables (data loss acceptable if issue is severe)
DROP TABLE IF EXISTS human_review_queue CASCADE;
DROP TABLE IF EXISTS atom_retry_history CASCADE;
DROP TABLE IF EXISTS validation_results CASCADE;
DROP TABLE IF EXISTS execution_waves CASCADE;
DROP TABLE IF EXISTS atom_dependencies CASCADE;
DROP TABLE IF EXISTS dependency_graphs CASCADE;
DROP TABLE IF EXISTS atomic_units CASCADE;
```

**Cuando usar**: Architectural issue discovered, V2 abandoned, revert to MVP permanently

### Data Preservation Strategy

```python
# Before rollback: Export V2 data for analysis
import json

def export_v2_data(masterplan_id: UUID):
    """Export V2 data before rollback"""

    atoms = get_all_atoms(masterplan_id)
    graph = get_dependency_graph(masterplan_id)
    validation_results = get_validation_results(masterplan_id)

    export_data = {
        "masterplan_id": str(masterplan_id),
        "atoms": [atom.dict() for atom in atoms],
        "graph": graph.dict(),
        "validation_results": [v.dict() for v in validation_results],
        "exported_at": datetime.utcnow().isoformat()
    }

    # Save to S3 or local storage
    with open(f"rollback_exports/{masterplan_id}.json", "w") as f:
        json.dump(export_data, f, indent=2)

    logger.info(f"Exported V2 data for {masterplan_id}")
```

---

## 💰 Cost-Benefit Analysis

### Implementation Costs

| Category | Estimate | Notes |
|----------|----------|-------|
| **Development** | $20K-40K | 2-3 engineers × 16 weeks |
| **Infrastructure** | +$80/mes | Neo4j hosting, increased compute |
| **Testing/QA** | $5K-10K | E2E testing, performance testing |
| **Documentation** | $2K-5K | Technical docs, training materials |
| **Contingency** | $5K-10K | Bug fixes, unexpected issues |
| **Total** | **$27K-55K** | One-time + $80/mes recurring |

### Expected Benefits

| Benefit | MVP | V2 | Improvement |
|---------|-----|-----|-------------|
| **Precisión** | 87.1% | 98% | **+12.6%** |
| **Tiempo ejecución** | 13h | 1.5h | **-87%** |
| **Feedback loops** | 1 por día | 10+ por día | **10x más rápido** |
| **Bugs en producción** | Baseline | -50% | **Menos rework** |
| **Developer productivity** | Baseline | +30% | **Más features/sprint** |
| **Customer satisfaction** | Baseline | +20% | **Mejor producto** |

### ROI Calculation

**Savings per project**:
- Developer time saved: 11.5 hours × $50/hour = **$575**
- Reduced bugs: 50% reduction × 2 hours fix time × $50/hour = **$50**
- Faster iterations: 10x feedback loops = **$200 value**
- **Total savings per project**: ~$825

**Break-even**:
- Investment: $40K (mid-range)
- Savings per project: $825
- Projects to break-even: 40K / 825 = **49 projects**

**Assuming 10 projects/month**:
- Break-even: 49 / 10 = **~5 months**
- ROI at 12 months: (10 × 12 × 825 - 40K) / 40K = **148% ROI**

### Intangible Benefits

- **Competitive advantage**: Industry-leading precision
- **Customer trust**: Higher quality, fewer bugs
- **Developer morale**: Better tools, less frustration
- **Market positioning**: "98% precision" marketing message
- **Future-proofing**: Foundation for further improvements

---

## ✅ Success Criteria

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Precisión** | ≥98% | Automated tests pass rate |
| **Tiempo ejecución** | <1.5 horas | End-to-end timer |
| **Costo** | <$200 | Claude API cost tracking |
| **Paralelización** | 100+ atoms | Wave size monitoring |
| **Context completeness** | ≥95% | Context scoring |
| **Validation catch rate** | ≥90% | Early error detection |
| **Retry success rate** | ≥99% | After 3 attempts |
| **False positive rate** | <5% | Validation accuracy |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **User adoption** | 80% en 3 meses | Feature usage tracking |
| **User satisfaction** | ≥4.5/5 | Post-execution surveys |
| **Support tickets** | <10/semana | Ticket volume monitoring |
| **Error recovery time** | <5 minutos | Rollback timing |
| **Time to value** | <2 horas | First successful execution |
| **Customer retention** | 95% | Churn rate |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Code coverage** | ≥85% | pytest-cov |
| **Type coverage** | ≥90% | mypy |
| **Security issues** | 0 critical | Security audit |
| **Performance** | <2s API latency | Response time monitoring |
| **Documentation** | 100% coverage | Docs completeness |

---

## ⚠️ Risk Management

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **AST parsing failures** | 🔴 ALTO | 🔴 ALTO | Extensive testing, fallback to MVP |
| **Dependency graph cycles** | 🔴 ALTO | 🔴 ALTO | Cycle detection, breaking heuristics |
| **Validation false positives** | 🟡 MEDIO | 🟡 MEDIO | Tunable thresholds, manual override |
| **Parallel race conditions** | 🔴 ALTO | 🔴 ALTO | Atomic operations, proper locking |
| **User resistance** | 🟡 MEDIO | 🟡 MEDIO | Gradual rollout, clear communication |
| **Cost overruns** | 🟡 MEDIO | 🟡 MEDIO | Contingency budget, scope management |
| **Timeline delays** | 🟡 MEDIO | 🟡 MEDIO | Buffer weeks, priority management |
| **Technical debt** | 🟢 BAJO | 🟡 MEDIO | Code reviews, refactoring sprints |
| **Security vulnerabilities** | 🟢 BAJO | 🔴 ALTO | Security audit, penetration testing |
| **Performance degradation** | 🟡 MEDIO | 🟡 MEDIO | Load testing, optimization |

### Contingency Plans

#### AST Parsing Failures
- **Detection**: Monitor parsing success rate
- **Threshold**: <90% success rate
- **Action**:
  1. Analyze failure patterns
  2. Add language-specific fixes
  3. Fallback to MVP for problematic tasks
  4. Improve parser with edge case tests

#### Dependency Cycles
- **Detection**: Cycle detection algorithm
- **Threshold**: Any cycle found
- **Action**:
  1. Log cycle details
  2. Apply breaking heuristics (optional dependencies)
  3. Manual review if critical
  4. Update atomization logic to prevent cycles

#### Performance Issues
- **Detection**: Execution time monitoring
- **Threshold**: >3 hours execution
- **Action**:
  1. Profile bottlenecks
  2. Optimize hot paths
  3. Increase parallelization
  4. Scale infrastructure

---

## 📊 Monitoring & Observability

### Metrics to Track

**Execution Metrics**:
```python
# Prometheus metrics
execution_time_seconds = Histogram("v2_execution_time_seconds", "V2 execution time")
atoms_generated_total = Counter("v2_atoms_generated_total", "Total atoms generated")
atoms_failed_total = Counter("v2_atoms_failed_total", "Failed atoms")
waves_executed_total = Counter("v2_waves_executed_total", "Waves executed")
parallel_atoms_gauge = Gauge("v2_parallel_atoms", "Atoms executing in parallel")

# Business metrics
precision_percent = Gauge("v2_precision_percent", "V2 precision percentage")
user_satisfaction = Gauge("v2_user_satisfaction", "User satisfaction score")
cost_per_project_usd = Histogram("v2_cost_per_project_usd", "Cost per project")
```

**Dashboards**:
- Grafana dashboard for V2 metrics
- Comparison MVP vs V2 side-by-side
- Real-time execution monitoring
- Cost tracking per masterplan
- User satisfaction trends

**Alerts**:
```yaml
alerts:
  - name: V2PrecisionLow
    condition: precision_percent < 95
    severity: warning
    action: Alert dev team, investigate

  - name: V2ExecutionSlow
    condition: execution_time_seconds > 7200  # 2 hours
    severity: warning
    action: Profile bottlenecks

  - name: V2HighFailureRate
    condition: atoms_failed_total / atoms_generated_total > 0.05
    severity: critical
    action: Consider rollback

  - name: V2CostOverrun
    condition: cost_per_project_usd > 250
    severity: warning
    action: Review LLM usage
```

---

## 🎯 Summary & Recommendations

### ✅ PROCEED with DUAL-MODE Migration

**Razones**:
1. **Riesgo mitigado**: Rollback instantáneo (<5 min), zero downtime
2. **ROI positivo**: 3-6 meses payback, 148% ROI en 12 meses
3. **Ventaja competitiva**: 98% precisión líder de industria vs 40-50% competencia
4. **Seguridad usuarios**: Sin disrupción, gradual rollout
5. **Solidez técnica**: Strategy Pattern, Feature Flags, probados en industria

### 📋 Immediate Next Steps

1. **[ ] Aprobar Estrategia** (Semana actual)
   - Technical Lead review
   - Product Manager alignment
   - Engineering Manager resource allocation

2. **[ ] Asignar Recursos** (Semana 1)
   - 2-3 engineers dedicados
   - 16 semanas commitment
   - Budget approval ($27K-55K)

3. **[ ] Setup Infrastructure** (Semana 1)
   - Feature flags deployment
   - Monitoring setup (Prometheus, Grafana)
   - Staging environment configuration

4. **[ ] Kickoff Phase 1** (Semana 1-2)
   - Foundation & Infrastructure
   - Database migrations
   - Strategy Pattern implementation

5. **[ ] Weekly Reviews** (Ongoing)
   - Progress tracking vs timeline
   - Risk assessment
   - Scope adjustments if needed

### 🎓 Key Takeaways

- **DUAL-MODE permite migración segura**: MVP sigue funcionando, V2 se valida gradualmente
- **16 semanas es realista**: 4 meses para implementación completa con testing
- **$27K-55K inversión justificada**: ROI en 3-6 meses, beneficios a largo plazo
- **98% precisión alcanzable**: Dependency-aware + retry + validation
- **Rollback <5 minutos**: Feature flags permiten reversión instantánea
- **Sacrificios aceptables**: +30% código, +40% DB, temporal durante migración

---

## 📚 References

- **MGE V2 Complete Spec**: `DOCS/MGE_V2/MGE_V2_COMPLETE_TECHNICAL_SPEC.md`
- **Architecture Overview**: `DOCS/MGE_V2/03_ARCHITECTURE_OVERVIEW.md`
- **MVP Models**: `src/models/masterplan.py`
- **MVP Services**: `src/services/`
- **Strategy Pattern**: Gang of Four Design Patterns
- **Feature Flags**: Martin Fowler - Feature Toggles
- **Gradual Rollout**: Google SRE Book - Chapter 15

---

**Document Status**: ✅ Complete
**Last Updated**: 2025-10-23
**Next Review**: After Phase 1 completion (Semana 2)

---

🚀 **Ready to implement!** Workflow detallado con 8 fases, criteria de éxito, y estrategia de rollback completa.
