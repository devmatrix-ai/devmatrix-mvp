# MGE v2: Architecture Overview

**Document**: 03 of 15
**Purpose**: High-level system architecture and component interaction

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MGE v2 SYSTEM                            │
│                                                                  │
│  Input: User Requirements                                       │
│  Output: Complete Codebase (98% precision, 1.5h, $180-330)     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: FOUNDATION (Existing from MVP)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 0: Discovery Engine                                      │
│  ├─ Conversational intake                                       │
│  ├─ DDD modeling                                                │
│  └─ Tech stack selection                                        │
│                                                                  │
│  Phase 1: RAG Retrieval                                         │
│  ├─ ChromaDB semantic search                                    │
│  ├─ Past patterns                                               │
│  └─ Best practices                                              │
│                                                                  │
│  Phase 2: Masterplan Generation                                 │
│  ├─ Hierarchical: Phases → Milestones → Tasks                  │
│  ├─ Dependencies (high-level)                                   │
│  └─ Agent assignment                                            │
│                                                                  │
│  Output: ~50 Tasks, project context                             │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: ATOMIZATION (NEW)                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 3: AST Atomization                                       │
│  ├─ MultiLanguageParser (tree-sitter)                          │
│  ├─ RecursiveDecomposer (Tasks → Atoms)                        │
│  ├─ ContextInjector (95% completeness)                         │
│  └─ AtomicityValidator (10 criteria)                           │
│                                                                  │
│  Output: ~800 AtomicUnits with full context                     │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: DEPENDENCY MANAGEMENT (NEW)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 4: Dependency Graph                                      │
│  ├─ DependencyAnalyzer (build graph)                           │
│  ├─ Topological sort (generation order)                        │
│  ├─ Parallel group detection                                    │
│  └─ Boundary detection (validation checkpoints)                │
│                                                                  │
│  Output: Dependency graph, execution order, parallel groups     │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: VALIDATION (NEW)                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 5: Hierarchical Validation                               │
│  ├─ Level 1: Atomic (per atom)                                 │
│  ├─ Level 2: Module (10-20 atoms)                              │
│  ├─ Level 3: Component (50-100 atoms)                          │
│  └─ Level 4: System (full project)                             │
│                                                                  │
│  Output: Multi-level validation results, boundaries             │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: EXECUTION (NEW)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 6: Execution + Retry                                     │
│  ├─ DependencyAwareGenerator                                    │
│  ├─ AtomExecutorWithRetry (3 attempts)                         │
│  ├─ ParallelExecutor (100+ concurrent)                         │
│  └─ ProgressiveIntegrationTester                               │
│                                                                  │
│  Output: Generated code, 98% precision                          │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: HUMAN COLLABORATION (NEW, Optional)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 7: Human Review                                          │
│  ├─ ConfidenceScorer                                            │
│  ├─ ReviewQueue (15-20% lowest confidence)                     │
│  ├─ ReviewInterface (Web UI)                                    │
│  └─ AISuggestions (smart fixes)                                │
│                                                                  │
│  Output: Reviewed code, 99%+ precision                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Diagram

```
┌──────────────┐
│     User     │
└──────┬───────┘
       │ Requirements
       ▼
┌──────────────────┐
│  Discovery       │──┐
│  Engine          │  │
└──────┬───────────┘  │
       │              │
       │ Context      │
       ▼              │
┌──────────────────┐  │
│  RAG Retrieval   │◄─┤ ChromaDB
└──────┬───────────┘  │
       │              │
       │ Patterns     │
       ▼              │
┌──────────────────┐  │
│  Masterplan      │  │
│  Generator       │  │
└──────┬───────────┘  │
       │              │
       │ 50 Tasks     │
       ▼              │
┌──────────────────┐  │
│  AST Atomizer    │◄─┤ tree-sitter
└──────┬───────────┘  │
       │              │
       │ 800 Atoms    │
       ▼              │
┌──────────────────┐  │
│  Dependency      │◄─┤ Neo4j
│  Analyzer        │  │ (or PostgreSQL)
└──────┬───────────┘  │
       │              │
       │ Graph        │
       ▼              │
┌──────────────────┐  │
│  Hierarchical    │  │
│  Validator       │  │
└──────┬───────────┘  │
       │              │
       │ Checkpoints  │
       ▼              │
┌──────────────────┐  │
│  Parallel        │◄─┤ Claude API
│  Executor        │  │
└──────┬───────────┘  │
       │              │
       │ Generated    │
       │ Code         │
       ▼              │
┌──────────────────┐  │
│  Confidence      │  │
│  Scorer          │  │
└──────┬───────────┘  │
       │              │
       │ Low confidence
       ▼              │
┌──────────────────┐  │
│  Human Review    │◄─┤ Web UI
│  Interface       │  │
└──────┬───────────┘  │
       │              │
       │ Approved     │
       ▼              │
┌──────────────────┐  │
│  Final Codebase  │  │
└──────────────────┘  │
                      │
                  ┌───┴────┐
                  │ Storage│
                  │ Layer  │
                  └────────┘
```

---

## Data Flow

### 1. Discovery Phase (0-2)

```
User Input
  ↓
Discovery Questions
  ↓
DDD Model
  ↓
RAG Search (ChromaDB)
  ↓
Relevant Patterns
  ↓
Masterplan Generation
  ↓
Hierarchical Structure:
  - 5-10 Phases
  - 20-30 Milestones
  - 50-100 Tasks

Output:
  project_context: {
    mission: str,
    tech_stack: dict,
    ddd_model: dict,
    patterns: list,
    tasks: list[Task]
  }
```

### 2. Atomization Phase (3)

```
For each Task:
  ↓
Parse to AST (tree-sitter)
  ↓
Recursive Decomposition:
  - Split at function boundaries
  - Split at class methods
  - Split at statement groups
  Until:
    - LOC <= 10
    - Complexity <= 3.0
  ↓
Generate AtomicUnit specs:
  - name, description
  - estimated LOC
  - dependencies
  ↓
Inject Context:
  - schemas
  - types
  - preconditions
  - postconditions
  - test cases
  (95% completeness)

Output:
  atoms: list[AtomicUnit] (~800)
```

### 3. Dependency Phase (4)

```
All atoms
  ↓
Dependency Detection:
  - Import dependencies
  - Data flow dependencies
  - Function call dependencies
  - Type dependencies
  ↓
Build Graph (Neo4j or PostgreSQL):
  nodes: atoms
  edges: dependencies
  ↓
Topological Sort:
  - Order: dependencies before dependents
  - Detect cycles (error if found)
  ↓
Parallel Grouping:
  - Level 0: No dependencies
  - Level 1: Depends only on L0
  - Level 2: Depends only on L0-L1
  ...
  ↓
Boundary Detection:
  - Module boundaries
  - Component boundaries
  - Fan-out points

Output:
  graph: DependencyGraph
  order: list[atom_id]
  groups: list[list[atom_id]]
  boundaries: list[Boundary]
```

### 4. Validation Phase (5)

```
Setup Checkpoints:
  ↓
Level 1: After each atom
  - Syntax check
  - Type check
  - Unit test
  - Atomicity validation
  ↓
Level 2: Every 10-20 atoms (module boundary)
  - Integration test
  - API consistency
  - Cohesion check
  ↓
Level 3: Every 50-100 atoms (component boundary)
  - Component E2E
  - Architecture compliance
  - Performance benchmark
  ↓
Level 4: Full project (system)
  - System E2E
  - Acceptance criteria
  - Production readiness

Output:
  validation_results: dict[level, ValidationResult]
  checkpoints: list[Checkpoint]
```

### 5. Execution Phase (6)

```
For each parallel group:
  ↓
For each atom in group (concurrent):
  ↓
Attempt 1:
  - Get validated dependencies
  - Build focused context
  - Generate code (Claude API)
  - Validate (Level 1)
  - Execute in sandbox
  ↓
If failed:
  Attempt 2:
    - Analyze error
    - Build feedback prompt
    - Regenerate (temp 0.5)
    - Retry validation
  ↓
  If failed:
    Attempt 3:
      - Detailed error analysis
      - Regenerate (temp 0.3)
      - Final retry
    ↓
    If failed:
      - Flag for human review
      - Continue with other atoms
  ↓
Progressive Integration Testing:
  - Every 10 atoms: run integration tests
  - If failure: bisect to find culprit
  - Fix and continue

Output:
  generated_atoms: dict[atom_id, GeneratedAtom]
  failed_atoms: list[atom_id]
```

### 6. Review Phase (7, Optional)

```
All generated atoms
  ↓
Calculate Confidence Scores:
  - Validation results (40%)
  - Attempts needed (30%)
  - Complexity (20%)
  - Integration tests (10%)
  ↓
Sort by confidence (lowest first)
  ↓
Select bottom 15-20% for review
  ↓
For each low-confidence atom:
  ↓
Present to Human:
  - Code
  - Context
  - AI suggestions
  - Actions: Approve | Edit | Regenerate
  ↓
Human Action:
  - Approve: Accept as-is
  - Edit: Manual fix
  - Regenerate: Retry with human feedback
  ↓
Update atom with human input

Output:
  reviewed_atoms: list[AtomicUnit]
  final_precision: 99%+
```

---

## Technology Stack

### Core Technologies

```yaml
Backend:
  language: Python 3.11
  framework: FastAPI 0.104
  async: asyncio + aiohttp

Database:
  primary: PostgreSQL 15
  vector: ChromaDB 0.4
  graph: Neo4j 5.0 (optional, can use PostgreSQL)
  cache: Redis 7.0

LLM:
  provider: Anthropic
  model: Claude Sonnet 4.5
  features:
    - Extended context (200K tokens)
    - Function calling
    - Structured outputs

Parsing:
  library: tree-sitter 0.20
  languages:
    - tree-sitter-python
    - tree-sitter-typescript
    - tree-sitter-javascript

Graphs:
  library: networkx 3.0
  algorithms:
    - Topological sort
    - Cycle detection
    - Level-based grouping

Testing:
  framework: pytest
  coverage: pytest-cov
  async: pytest-asyncio

Frontend:
  framework: React 18 + TypeScript
  ui: TailwindCSS + shadcn/ui
  editor: CodeMirror 6
  diff: react-diff-viewer

Infrastructure:
  containerization: Docker + docker-compose
  orchestration: Kubernetes (production)
  monitoring: Prometheus + Grafana
  logging: ELK stack
```

### File Structure

```
mge-v2/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── projects.py
│   │   │   │   ├── atoms.py
│   │   │   │   └── review.py
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── llm.py
│   │   ├── models/
│   │   │   ├── project.py
│   │   │   ├── task.py
│   │   │   ├── atom.py
│   │   │   └── validation.py
│   │   ├── services/
│   │   │   ├── discovery/
│   │   │   ├── atomization/
│   │   │   │   ├── parser.py
│   │   │   │   ├── decomposer.py
│   │   │   │   ├── context_injector.py
│   │   │   │   └── validator.py
│   │   │   ├── dependencies/
│   │   │   │   ├── analyzer.py
│   │   │   │   ├── graph.py
│   │   │   │   └── generator.py
│   │   │   ├── validation/
│   │   │   │   ├── hierarchical.py
│   │   │   │   ├── atomic.py
│   │   │   │   ├── module.py
│   │   │   │   ├── component.py
│   │   │   │   └── system.py
│   │   │   ├── execution/
│   │   │   │   ├── executor.py
│   │   │   │   ├── retry.py
│   │   │   │   ├── parallel.py
│   │   │   │   └── sandbox.py
│   │   │   └── review/
│   │   │       ├── scorer.py
│   │   │       ├── queue.py
│   │   │       └── interface.py
│   │   └── utils/
│   │       ├── metrics.py
│   │       ├── logging.py
│   │       └── errors.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── hooks/
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   ├── setup.sh
│   ├── migrate.sh
│   └── deploy.sh
├── docker-compose.yml
└── README.md
```

---

## Scalability Considerations

### Horizontal Scaling

```yaml
Components that scale horizontally:
  - API servers (FastAPI instances)
  - LLM request workers (parallel generation)
  - Validation workers (parallel testing)
  - Review interface (stateless web servers)

Scaling strategy:
  - Load balancer (nginx)
  - Multiple FastAPI instances
  - Task queue (Celery + Redis)
  - Shared state (PostgreSQL + Redis)
```

### Performance Targets

```yaml
Throughput:
  - 10 projects/hour (single instance)
  - 100 projects/hour (10 instances)

Latency:
  - Atomization: <5 minutes
  - Dependency graph: <1 minute
  - Execution: 1-1.5 hours
  - Review: 20-30 minutes (optional)

Resource usage:
  - CPU: 4-8 cores per instance
  - RAM: 16-32 GB per instance
  - Storage: 100 GB per 1000 projects
```

---

## Security Architecture

### Authentication & Authorization

```yaml
Authentication:
  - JWT tokens
  - OAuth 2.0 (Google, GitHub)
  - API keys for programmatic access

Authorization:
  - Role-based access control (RBAC)
  - Project-level permissions
  - Review-level permissions

Secrets management:
  - Environment variables
  - AWS Secrets Manager / HashiCorp Vault
  - Encrypted at rest
```

### Code Execution Sandbox

```yaml
Isolation:
  - Docker containers (per execution)
  - Limited resources (CPU, RAM, disk)
  - No network access (except allowed APIs)
  - Temporary filesystem

Security:
  - Non-root user
  - Seccomp profiles
  - AppArmor / SELinux
  - Timeout enforcement (30 sec per atom)
```

---

## Monitoring & Observability

### Metrics

```yaml
Business metrics:
  - Projects completed
  - Average precision
  - Average execution time
  - Average cost
  - Human review rate

Technical metrics:
  - API latency
  - LLM request rate
  - Validation pass rate
  - Retry rate
  - Error rate

Resource metrics:
  - CPU usage
  - Memory usage
  - Disk I/O
  - Network I/O
```

### Logging

```yaml
Log levels:
  - DEBUG: Detailed execution traces
  - INFO: Normal operations
  - WARNING: Validation failures, retries
  - ERROR: Exceptions, system errors
  - CRITICAL: System failures

Log aggregation:
  - ELK stack (Elasticsearch, Logstash, Kibana)
  - Structured logging (JSON)
  - Request tracing (trace IDs)
```

---

**Next Document**: [04_PHASE_0_2_FOUNDATION.md](04_PHASE_0_2_FOUNDATION.md) - Foundation phases
