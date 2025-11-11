# Architecture Comparison: MVP vs V2

**Visual Side-by-Side Analysis** | **Date**: 2025-10-23

---

## System Architecture Overview

### MVP Architecture (Current)
```
┌───────────────────────────────────────────────────────────┐
│                    MVP ARCHITECTURE                        │
└───────────────────────────────────────────────────────────┘

INPUT: User Requirements
  │
  ├─> PHASE 0: Discovery (DDD Analysis)
  │   └─> DiscoveryDocument
  │       ├─ Domain Model
  │       ├─ Bounded Contexts
  │       ├─ Aggregates & Entities
  │       └─ Value Objects
  │
  ├─> PHASE 1: RAG Retrieval
  │   └─> ChromaDB Search
  │       ├─ Similar Patterns
  │       ├─ Best Practices
  │       └─ Code Examples
  │
  ├─> PHASE 2: MasterPlan Generation
  │   └─> Hierarchical Plan (Sonnet 4.5)
  │       ├─ 3 Phases (Setup, Core, Polish)
  │       ├─ 15-20 Milestones
  │       ├─ 50 Tasks (80 LOC each)
  │       └─ 150 Subtasks (25 LOC each)
  │           ├─ Basic dependency tracking
  │           └─ Agent assignment
  │
  └─> PHASE 3: Execution
      └─> TaskExecutor (Sequential++)
          ├─ 2-3 concurrent tasks
          ├─ LLM generation (Haiku/Sonnet)
          ├─ Basic validation (syntax, tests)
          ├─ 1 retry attempt
          └─ 13 hours average

RESULTS:
  ├─ Precision: 87.1%
  ├─ Time: 13 hours
  ├─ Cost: $160
  ├─ Granularity: 25 LOC/subtask
  └─ Parallelization: 2-3 concurrent
```

### V2 Architecture (Target)
```
┌───────────────────────────────────────────────────────────┐
│                     V2 ARCHITECTURE                        │
└───────────────────────────────────────────────────────────┘

INPUT: User Requirements
  │
  ├─> PHASE 0-2: Foundation (SAME AS MVP)
  │   └─> Discovery + RAG + MasterPlan
  │       └─ 50 Tasks generated
  │
  ├─> PHASE 3: AST Atomization 🆕
  │   └─> tree-sitter Parsing
  │       ├─ Parse tasks to AST
  │       ├─ Recursive decomposition
  │       ├─ Generate ~800 Atoms (10 LOC each)
  │       ├─ Context injection (95% completeness)
  │       └─ Atomicity validation
  │           ├─ Size: 5-15 LOC
  │           ├─ Complexity: <3.0
  │           ├─ Single responsibility
  │           └─ 10-criteria validation
  │
  ├─> PHASE 4: Dependency Graph 🆕
  │   └─> networkx/Neo4j
  │       ├─ Build dependency graph
  │       ├─ Topological sort
  │       ├─ Detect parallel groups (8-10 waves)
  │       └─ Identify boundaries (module/component)
  │
  ├─> PHASE 5: Hierarchical Validation 🆕
  │   └─> 4-Level Validation
  │       ├─ Level 1: Atomic (per atom)
  │       ├─ Level 2: Module (10-20 atoms)
  │       ├─ Level 3: Component (50-100 atoms)
  │       └─ Level 4: System (full project)
  │
  ├─> PHASE 6: Execution + Retry 🆕
  │   └─> Wave Executor
  │       ├─ 100+ concurrent atoms
  │       ├─ Dependency-aware generation
  │       ├─ 3-attempt retry loop
  │       ├─ Error feedback integration
  │       └─ Progressive validation
  │
  └─> PHASE 7: Human Review 🆕 (Optional)
      └─> Confidence Scoring
          ├─ Flag 15-20% low-confidence atoms
          ├─ Human review UI
          ├─ Approve/Edit/Regenerate
          └─ 99%+ precision with review

RESULTS:
  ├─ Precision: 98% (99%+ with review)
  ├─ Time: 1-1.5 hours (1.5-2h with review)
  ├─ Cost: $180 ($280-330 with review)
  ├─ Granularity: 10 LOC/atom
  └─ Parallelization: 100+ concurrent
```

---

## Component-by-Component Comparison

### Data Models

#### MVP Models
```python
✅ DiscoveryDocument         # DDD analysis
✅ MasterPlan                 # 50 tasks
✅ MasterPlanPhase            # Setup/Core/Polish
✅ MasterPlanMilestone        # Milestone grouping
✅ MasterPlanTask             # 80 LOC tasks
✅ MasterPlanSubtask          # 25 LOC subtasks
✅ MasterPlanVersion          # Version tracking
✅ MasterPlanHistory          # Audit trail
```

#### V2 Additional Models
```python
🆕 AtomicUnit                 # 10 LOC atoms (Phase 3)
🆕 AtomDependency             # Fine-grained deps (Phase 4)
🆕 DependencyGraph            # Graph metadata (Phase 4)
🆕 ValidationResult           # 4-level validation (Phase 5)
🆕 ExecutionWave              # Parallel waves (Phase 6)
🆕 AtomRetryHistory           # Retry logs (Phase 6)
🆕 HumanReviewQueue           # Review queue (Phase 7)
```

**Total**: MVP (8 models) → V2 (15 models) = **+87% models**

---

### Service Layer

#### MVP Services
```python
✅ DiscoveryAgent             # DDD analysis
✅ MasterPlanGenerator        # 50-task generation
✅ TaskExecutor               # Task execution
✅ CodeValidator              # Basic validation
✅ AuthService                # JWT auth
✅ ChatService                # Conversations
✅ AdminService               # Admin ops
✅ EmailService               # Notifications
✅ PasswordResetService       # Password recovery
✅ TenancyService             # Multi-tenancy
✅ UsageTrackingService       # Usage metrics
✅ WorkspaceService           # Workspace mgmt
```

#### V2 Additional Services
```python
🆕 ASTAtomizationService      # tree-sitter (Phase 3)
🆕 RecursiveDecomposer        # AST → atoms (Phase 3)
🆕 ContextInjector            # 95% context (Phase 3)
🆕 AtomicityValidator         # 10 criteria (Phase 3)
🆕 DependencyAnalyzer         # Graph builder (Phase 4)
🆕 DependencyAwareGenerator   # Topological exec (Phase 4)
🆕 HierarchicalValidator      # 4-level val (Phase 5)
🆕 RetryOrchestrator          # 3-attempt retry (Phase 6)
🆕 WaveExecutor               # Parallel waves (Phase 6)
🆕 ConfidenceScorer           # ML scoring (Phase 7)
🆕 HumanReviewService         # Review UI/API (Phase 7)
```

**Total**: MVP (12 services) → V2 (23 services) = **+92% services**

---

### Technology Stack

#### MVP Stack
```yaml
Backend:
  ✅ Python 3.11
  ✅ FastAPI
  ✅ SQLAlchemy + Alembic
  ✅ PostgreSQL 15
  ✅ Redis (caching)
  ✅ ChromaDB (RAG)

Frontend:
  ✅ React 18 + TypeScript
  ✅ TailwindCSS
  ✅ React Query

LLM:
  ✅ Anthropic Claude (Sonnet 4.5, Haiku 3.5)
  ✅ Prompt caching

Infrastructure:
  ✅ Docker + Docker Compose
  ✅ GitHub Actions
```

#### V2 Additional Stack
```yaml
Backend:
  🆕 tree-sitter (AST parsing) ← CRITICAL
  🆕 tree-sitter-python
  🆕 tree-sitter-typescript
  🆕 tree-sitter-javascript
  🆕 networkx (dep graphs)
  🆕 pytest-xdist (parallel tests)

Optional:
  🆕 Neo4j (graph database)
  🆕 Celery (distributed tasks)
  🆕 scikit-learn (ML confidence)
```

**New Dependencies**: 6-9 packages

---

### API Endpoints

#### MVP Endpoints
```
✅ POST   /api/v1/discovery/start
✅ POST   /api/v1/masterplan/generate
✅ POST   /api/v1/masterplan/execute
✅ GET    /api/v1/masterplan/{id}
✅ GET    /api/v1/task/{id}
✅ POST   /api/v1/task/{id}/retry
✅ WS     /ws/masterplan/{id}
```

#### V2 Additional Endpoints
```
🆕 POST   /api/v2/atomize/task/{id}
🆕 POST   /api/v2/atomize/plan/{id}
🆕 GET    /api/v2/atoms/{plan_id}
🆕 GET    /api/v2/atom/{id}
🆕 POST   /api/v2/dependency-graph/build
🆕 GET    /api/v2/dependency-graph/{id}
🆕 GET    /api/v2/execution-waves/{id}
🆕 POST   /api/v2/execute/wave
🆕 POST   /api/v2/validate/hierarchical
🆕 GET    /api/v2/review-queue/{plan_id}
🆕 POST   /api/v2/review/{atom_id}
🆕 POST   /api/v2/mode
```

**Total**: MVP (7 endpoints) → V2 (19 endpoints) = **+171% endpoints**

---

## Execution Flow Comparison

### MVP Execution Flow
```
┌─────────────────────────────────────────────────────────┐
│ 1. User Request                                          │
│    └─> "Build e-commerce platform"                      │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Discovery (15 min)                                    │
│    └─> DDD Analysis                                      │
│        ├─ Domain: E-commerce                            │
│        ├─ Contexts: Catalog, Sales, Identity           │
│        └─ Entities: User, Product, Order               │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 3. MasterPlan Generation (5 min)                        │
│    └─> 50 Tasks Generated                               │
│        ├─ Phase 1: Setup (15 tasks)                    │
│        ├─ Phase 2: Core (25 tasks)                     │
│        └─ Phase 3: Polish (10 tasks)                   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Task Execution (12-13 hours)                         │
│    └─> Sequential++ Execution                           │
│        ├─ Task 1 (30 min) ✅                           │
│        ├─ Task 2 (25 min) ✅                           │
│        ├─ Task 3 (40 min) ❌ (retry) → ✅             │
│        ├─ ... (2-3 concurrent)                         │
│        └─ Task 50 (20 min) ✅                          │
│                                                          │
│    Breakdown per task:                                  │
│    ├─ Load dependencies (1 min)                        │
│    ├─ RAG retrieval (1 min)                            │
│    ├─ LLM generation (10-20 min)                       │
│    ├─ Validation (2-3 min)                             │
│    └─ Save to workspace (1 min)                        │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Results                                               │
│    ├─ Success Rate: 87.1%                               │
│    ├─ Total Time: 13 hours                              │
│    ├─ Total Cost: $160                                  │
│    └─ Manual Fixes: ~20 tasks                          │
└─────────────────────────────────────────────────────────┘
```

### V2 Execution Flow
```
┌─────────────────────────────────────────────────────────┐
│ 1-3. Same as MVP (20 min)                               │
│     └─> Discovery + RAG + MasterPlan                    │
│         └─> 50 Tasks Generated                          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 4. AST Atomization (5 min) 🆕                           │
│    └─> tree-sitter Parsing                              │
│        ├─ Parse 50 tasks to AST                        │
│        ├─ Recursive decomposition                      │
│        ├─ Generate 800 atoms (10 LOC each)             │
│        └─> Context injection (95%)                     │
│            ├─ Dependencies extracted                   │
│            ├─ Type hints analyzed                      │
│            └─ Documentation enriched                   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Dependency Graph (2 min) 🆕                          │
│    └─> Build Graph + Topological Sort                   │
│        ├─ Identify dependencies                        │
│        ├─ Detect cycles (if any)                       │
│        ├─ Calculate parallel waves                     │
│        └─> 8 waves identified                          │
│            ├─ Wave 1: 120 atoms (no deps)             │
│            ├─ Wave 2: 110 atoms                        │
│            └─ ... Wave 8: 40 atoms                    │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Wave Execution (1 hour) 🆕                           │
│    └─> Parallel Execution + Retry                       │
│        │                                                 │
│        ├─ Wave 1 (10 min)                              │
│        │   ├─ 100 atoms concurrent                     │
│        │   ├─ Retry failed atoms (3x)                  │
│        │   ├─ Validate (Level 1)                       │
│        │   └─> 98% success                             │
│        │                                                 │
│        ├─ Wave 2 (8 min)                               │
│        │   └─> 97% success                             │
│        │                                                 │
│        ├─ ... Waves 3-7 (35 min total)                │
│        │                                                 │
│        └─ Wave 8 (5 min)                               │
│            └─> 99% success                             │
│                                                          │
│    Per-atom execution:                                  │
│    ├─ Get validated deps (<1 sec)                     │
│    ├─ LLM generation (5-10 sec)                        │
│    ├─ Validate (Level 1) (2 sec)                      │
│    ├─ Retry if failed (3x max)                        │
│    └─ Save (< 1 sec)                                   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Hierarchical Validation (10 min) 🆕                  │
│    └─> 4-Level Validation                               │
│        ├─ Level 1: Atomic (per atom) ✅               │
│        ├─ Level 2: Module (10-20 atoms) ✅            │
│        ├─ Level 3: Component (50-100 atoms) ✅        │
│        └─ Level 4: System (full project) ✅           │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 8. Human Review (Optional, 20 min) 🆕                   │
│    └─> Confidence Scoring                               │
│        ├─ Identify 120 low-confidence atoms (15%)     │
│        ├─ Human review UI                              │
│        ├─ Approve: 100 atoms                           │
│        ├─ Edit: 15 atoms                               │
│        └─ Regenerate: 5 atoms                          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 9. Results                                               │
│    ├─ Success Rate: 98% (99%+ with review)             │
│    ├─ Total Time: 1.5 hours (2h with review)           │
│    ├─ Total Cost: $180 ($330 with review)              │
│    └─ Manual Fixes: ~15 atoms (2% of 800)             │
└─────────────────────────────────────────────────────────┘
```

---

## Performance Metrics Side-by-Side

### Quantitative Comparison

| Metric | MVP | V2 Autonomous | V2 + Human | Improvement |
|--------|-----|---------------|------------|-------------|
| **Precision** | 87.1% | 98% | 99%+ | +12.6% / +13.6% |
| **Total Time** | 13 hours | 1.5 hours | 2 hours | -87% / -85% |
| **Cost per Plan** | $160 | $180 | $280-330 | +13% / +75-106% |
| **Granularity** | 25 LOC/subtask | 10 LOC/atom | 10 LOC/atom | 2.5x finer |
| **Total Units** | 150 subtasks | 800 atoms | 800 atoms | 5.3x more |
| **Parallelization** | 2-3 concurrent | 100+ concurrent | 100+ concurrent | 50x more |
| **Retry Attempts** | 1 | 3 | 3 | 3x more |
| **Validation Levels** | 1 (basic) | 4 (hierarchical) | 4 (hierarchical) | 4x more |
| **Context Completeness** | 70% | 95% | 95% | +36% |
| **Manual Fixes** | ~20 tasks (13%) | ~15 atoms (2%) | ~5 atoms (<1%) | -85% / -96% |

### Qualitative Comparison

| Aspect | MVP | V2 |
|--------|-----|-----|
| **Code Quality** | Good | Excellent (finer granularity) |
| **Error Detection** | Basic (syntax, tests) | Comprehensive (4-level) |
| **Dependency Handling** | Coarse (task-level) | Fine-grained (atom-level) |
| **Cascading Errors** | Possible | Prevented (dep-aware) |
| **Developer Experience** | Manual retry tedious | Automatic retry smooth |
| **Scalability** | Limited (3 concurrent) | High (100+ concurrent) |
| **Cost Efficiency** | Good | Acceptable (better quality) |
| **Time Efficiency** | Slow (13h) | Fast (1.5h) |
| **Precision** | Acceptable (87%) | High (98%) |

---

## Database Schema Growth

### Tables Count

```
MVP Tables:     8
V2 Tables:     15 (8 MVP + 7 new)
Growth:       +87%
```

### Storage Estimation

```
MVP Database Size:     100 MB (typical project)
V2 Database Size:      140 MB (typical project)
Growth:               +40%

Breakdown:
  MVP data:            100 MB
  V2 atoms:             25 MB (800 atoms × 30 KB avg)
  V2 dependencies:       5 MB (2000 edges × 2.5 KB avg)
  V2 validation:         5 MB
  V2 other:              5 MB
  Total:               140 MB
```

---

## Code Complexity Growth

### Lines of Code

```
MVP Codebase:        ~15,000 LOC
V2 Addition:         ~8,000 LOC (new V2 components)
V2 Total:           ~23,000 LOC
Growth:             +53%

Breakdown:
  MVP (unchanged):        15,000 LOC
  V2 Phase 3 (AST):        2,500 LOC
  V2 Phase 4 (Dep):        1,500 LOC
  V2 Phase 5 (Val):        1,000 LOC
  V2 Phase 6 (Exec):       1,500 LOC
  V2 Phase 7 (Review):     1,000 LOC
  V2 Infrastructure:         500 LOC
  Total:                  23,000 LOC
```

### Test Coverage

```
MVP Tests:           ~5,000 LOC (33% coverage)
V2 Tests:           ~8,000 LOC (35% coverage)
Total Tests:       ~13,000 LOC

Test Growth:        +160%
```

---

## Cost Analysis Deep Dive

### MVP Cost Breakdown (per plan)

```
Discovery:           $0.09 (Sonnet 4.5)
MasterPlan:          $0.32 (Sonnet 4.5)
Task Execution:     $159.59
  ├─ Haiku (60%):     $48.00 (30 tasks × $1.60)
  ├─ Sonnet (40%):   $111.59 (20 tasks × $5.58)
  └─ Retry (13%):      $0.00 (included)

Total:              $160.00
```

### V2 Cost Breakdown (per plan)

```
Discovery:           $0.09 (Sonnet 4.5) [SAME]
MasterPlan:          $0.32 (Sonnet 4.5) [SAME]
Atomization:         $1.50 (Sonnet 4.5 for context)
Dep Graph:           $0.20 (computation only)
Atom Execution:    $177.89
  ├─ Haiku (70%):    $67.20 (560 atoms × $0.12)
  ├─ Sonnet (30%):  $110.69 (240 atoms × $0.46)
  └─ Retry (5%):      $0.00 (included)

Total (Autonomous): $180.00

With Human Review:
  + Review UI:         $0.00 (no LLM cost)
  + Regenerate (5%):  $8.00 (40 atoms × $0.20)
  + Human time:      $100-150 (20 min @ $300-450/hr)

Total (+ Human):    $288-338
```

---

## Conclusion: Why DUAL-MODE?

### Benefits Visualization

```
┌──────────────────────────────────────────────────────────┐
│              DUAL-MODE BENEFITS                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ✅ Zero Downtime                                        │
│     └─> Users never experience interruption             │
│                                                           │
│  ✅ Instant Rollback                                     │
│     └─> <5 minutes to revert to MVP if issues          │
│                                                           │
│  ✅ A/B Testing                                          │
│     └─> Compare MVP vs V2 in production                 │
│                                                           │
│  ✅ Risk Mitigation                                      │
│     └─> MVP continues working during V2 development     │
│                                                           │
│  ✅ Gradual Rollout                                      │
│     └─> 5% → 10% → 25% → 50% → 100%                    │
│                                                           │
│  ✅ User Choice                                          │
│     └─> Users can opt-in to V2 early                   │
│                                                           │
│  ✅ Data Preservation                                    │
│     └─> MVP data unchanged, V2 additive                 │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Trade-Offs Accepted

```
┌──────────────────────────────────────────────────────────┐
│            DUAL-MODE TRADE-OFFS                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ⚠️  Code Complexity: +30%                              │
│      └─> Strategy Pattern keeps it organized            │
│                                                           │
│  ⚠️  Testing Surface: 2x                                │
│      └─> Shared utilities reduce duplication            │
│                                                           │
│  ⚠️  Database Size: +40%                                │
│      └─> Storage cheap, quality valuable                │
│                                                           │
│  ⚠️  Development Time: +4 weeks                         │
│      └─> Risk reduction worth the investment            │
│                                                           │
│  ⚠️  Maintenance: 2 modes                               │
│      └─> Temporary (6-12 months until MVP deprecated)   │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

**End of Comparison**

**Next Steps**: Review `/DOCS/MGE_V2/MIGRATION_EXECUTIVE_SUMMARY.md` for implementation plan.
