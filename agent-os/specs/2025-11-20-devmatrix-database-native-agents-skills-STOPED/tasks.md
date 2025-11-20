# DevMatrix Database-Native Transformation - Tasks

**Updated**: 2025-11-20 - Revised based on blueprint with implementation options

## ⚠️ IMPORTANT: Branch Strategy

**BEFORE STARTING ANY IMPLEMENTATION:**
1. Create a new branch from main:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/devmatrix-database-native
   ```

2. All development happens in this feature branch
3. Regular commits with clear messages
4. When complete and tested, create PR to merge back to main
5. DO NOT work directly on main branch

## Implementation Strategy

Following the blueprint's recommended approach:

1. **Foundation Layer** (Week 1): DatabaseContext + DatabaseTaskManager
2. **Orchestration Engine** (Week 2): GraphOrchestrator + Wave Execution
3. **Hybrid Code Generator** (Week 3): Integration with existing CodeGenerationService
4. **Skills Framework** (Week 4): Port 17 agent-os skills
5. **Full MVP** (Week 5): Complete integration and testing

## PHASE 1: Foundation Layer (Week 1 - 20h)

### Task Group 1.1: Database Architecture Design (4h)
- [ ] **Task 1.1.1**: Design PostgreSQL schema for specs and tasks (1.5h)
  - [ ] Create ERD diagram for all tables
  - [ ] Define indexes and constraints
  - [ ] Plan migration strategy
- [ ] **Task 1.1.2**: Design Neo4j graph model for dependencies (1.5h)
  - [ ] Define node types and properties
  - [ ] Map relationship types
  - [ ] Plan traversal queries
- [ ] **Task 1.1.3**: Design Qdrant collections for embeddings (1h)
  - [ ] Define vector dimensions
  - [ ] Plan payload structures
  - [ ] Design similarity thresholds

### Task Group 1.2: Integration Analysis (3h)
- [ ] **Task 1.2.1**: Map DevMatrix pipeline to database operations (1.5h)
  - [ ] Identify touchpoints for each phase
  - [ ] Define transaction boundaries
  - [ ] Plan rollback strategies
- [ ] **Task 1.2.2**: Analyze existing agent-os workflow patterns (1.5h)
  - [ ] Document task hierarchy patterns
  - [ ] Map skills to database operations
  - [ ] Identify orchestration requirements

### Task Group 1.3: Performance Planning (3h)
- [ ] **Task 1.3.1**: Define performance benchmarks (1h)
  - [ ] Set query time targets
  - [ ] Define throughput requirements
  - [ ] Plan load testing scenarios
- [ ] **Task 1.3.2**: Design caching strategy (1h)
  - [ ] Identify cacheable operations
  - [ ] Plan cache invalidation
  - [ ] Consider Redis integration
- [ ] **Task 1.3.3**: Plan connection pooling (1h)
  - [ ] Configure pool sizes
  - [ ] Plan failover strategies
  - [ ] Design circuit breakers

### Task Group 1.2: DatabaseContext Implementation (8h) **[NEW - Critical Component]**

- [ ] **Task 1.2.1**: Implement minimal context query engine (3h)
  - [ ] Create PostgreSQL query methods for task details
  - [ ] Implement Neo4j dependency queries
  - [ ] Add Qdrant pattern search (top-K with threshold)
  - [ ] Build context formatting logic (2-3KB target)

- [ ] **Task 1.2.2**: Add Redis caching layer (2h)
  - [ ] Configure Redis connection pool
  - [ ] Implement cache-aside pattern for contexts
  - [ ] Set TTL policies (5 min for contexts)
  - [ ] Add cache invalidation on task updates

- [ ] **Task 1.2.3**: Implement context builders (2h)
  - [ ] get_minimal_context() method
  - [ ] get_task_with_dependencies() method
  - [ ] get_similar_patterns() method
  - [ ] Pattern formatting helpers

- [ ] **Task 1.2.4**: Performance optimization and testing (1h)
  - [ ] Benchmark query times (<100ms target)
  - [ ] Test token reduction (30-50% vs markdown)
  - [ ] Verify cache hit rates
  - [ ] Test with various task types

### Task Group 1.3: DatabaseTaskManager Implementation (8h)

- [ ] **Task 1.3.1**: PostgreSQL setup and schema (2h)
  - [ ] Create database instance
  - [ ] Implement all tables (specs, tasks, reports, audit_log)
  - [ ] Add indexes and constraints
  - [ ] Create Alembic migration scripts

- [ ] **Task 1.3.2**: CRUD operations (3h)
  - [ ] create_spec(), get_spec(), update_spec()
  - [ ] create_task_hierarchy() with parent-child relationships
  - [ ] update_task_status(), get_pending_tasks()
  - [ ] Transaction support with rollback

- [ ] **Task 1.3.3**: Audit logging and reporting (2h)
  - [ ] Implement audit_log table operations
  - [ ] Track all state changes
  - [ ] Create reports storage methods
  - [ ] Query methods for execution metrics

- [ ] **Task 1.3.4**: Connection pooling and error handling (1h)
  - [ ] Configure SQLAlchemy pool (size=10)
  - [ ] Implement retry logic with exponential backoff
  - [ ] Add connection health checks
  - [ ] Error recovery strategies

## PHASE 2: Orchestration Engine (Week 2 - 25h)

### Task Group 2.1: Neo4j Graph Setup (6h)

- [ ] **Task 2.1.1**: Neo4j database configuration (2h)
  - [ ] Setup Neo4j instance
  - [ ] Create node constraints and indexes
  - [ ] Configure connection pooling (size=5)
  - [ ] Test Cypher query performance

- [ ] **Task 2.1.2**: Graph data model implementation (2h)
  - [ ] Define Task, Skill, Agent, Wave nodes
  - [ ] Implement DEPENDS_ON, REQUIRES_SKILL, ASSIGNED_TO relationships
  - [ ] Create PARENT_OF for task hierarchy
  - [ ] Add IN_WAVE for wave assignments

- [ ] **Task 2.1.3**: Import/export utilities (2h)
  - [ ] PostgreSQL to Neo4j task import
  - [ ] Bulk import optimization
  - [ ] Graph visualization helpers
  - [ ] Cycle detection algorithms

### Task Group 2.2: GraphOrchestrator Implementation (12h) **[Critical - Wave Generation]**

- [ ] **Task 2.2.1**: Task import to graph (3h)
  - [ ] import_tasks_to_graph() implementation
  - [ ] Create Task nodes from PostgreSQL
  - [ ] Build dependency relationships
  - [ ] Map skill requirements

- [ ] **Task 2.2.2**: Wave generation algorithm (4h)
  - [ ] Implement Cypher wave analysis query
  - [ ] Find tasks with no dependencies (Wave 0)
  - [ ] Iteratively identify subsequent waves
  - [ ] Group tasks by wave number

- [ ] **Task 2.2.3**: Agent assignment logic (3h)
  - [ ] _assign_agents_to_tasks() based on skills
  - [ ] Map backend-api → BackendAPIAgent
  - [ ] Map frontend-components → FrontendAgent
  - [ ] Map backend-models → DatabaseAgent
  - [ ] Default to GeneralistAgent

- [ ] **Task 2.2.4**: Wave execution with parallel agents (2h)
  - [ ] execute_wave() with ThreadPoolExecutor
  - [ ] Configure max_workers=5
  - [ ] Result collection with timeouts (5 min per task)
  - [ ] Immediate PostgreSQL status updates

### Task Group 2.3: WaveExecutor and Monitoring (7h)

- [ ] **Task 2.3.1**: Parallel execution infrastructure (3h)
  - [ ] ThreadPoolExecutor configuration
  - [ ] Task submission and future tracking
  - [ ] Timeout handling (300s per task)
  - [ ] Exception handling and retry logic

- [ ] **Task 2.3.2**: Real-time progress tracking (2h)
  - [ ] Wave status updates in Neo4j
  - [ ] Task status updates in PostgreSQL
  - [ ] Progress calculation methods
  - [ ] Dashboard data generation

- [ ] **Task 2.3.3**: Performance optimization (2h)
  - [ ] Cypher query optimization with EXPLAIN
  - [ ] Index usage verification
  - [ ] Benchmark wave analysis (<500ms target)
  - [ ] Optimize for 1000+ task graphs

## PHASE 3: Hybrid Code Generator (Week 3 - 25h)

### Task Group 3.1: Qdrant Pattern Store Setup (6h)

- [ ] **Task 3.1.1**: Qdrant configuration (2h)
  - [ ] Setup Qdrant instance
  - [ ] Create collections (task_embeddings, code_patterns, success_patterns)
  - [ ] Configure vector dimensions (768)
  - [ ] Set distance metrics (Cosine)

- [ ] **Task 3.1.2**: SemanticPatternStore implementation (3h)
  - [ ] Embedding generation for tasks
  - [ ] store_success_pattern() method
  - [ ] find_similar() with threshold filtering (>0.8)
  - [ ] Pattern ranking and quality metrics

- [ ] **Task 3.1.3**: Pattern utilities and optimization (1h)
  - [ ] Batch embedding generation
  - [ ] Cache pattern searches
  - [ ] Benchmark similarity search (<200ms target)
  - [ ] Pattern metadata management

### Task Group 3.2: HybridCodeGenerator Implementation (12h) **[Critical - Core Generation]**

- [ ] **Task 3.2.1**: Integration with CodeGenerationService (4h)
  - [ ] _task_to_requirements() converter
  - [ ] Route structured tasks (API/MODEL/CRUD) to CodeGenerationService
  - [ ] Pass enhanced prompts with patterns and skills
  - [ ] Handle async generation with proper error handling

- [ ] **Task 3.2.2**: Direct agent execution path (3h)
  - [ ] LLM client configuration for generic tasks
  - [ ] Prompt building for non-structured tasks
  - [ ] Temperature and token settings (0.2, 4000 tokens)
  - [ ] Response parsing and validation

- [ ] **Task 3.2.3**: Enhanced prompt building (3h)
  - [ ] _build_enhanced_prompt() implementation
  - [ ] Include minimal context from DatabaseContext
  - [ ] Add similar patterns from Qdrant
  - [ ] Embed skill standards and requirements
  - [ ] Format with proper structure and examples

- [ ] **Task 3.2.4**: Pattern storage and learning (2h)
  - [ ] Store successful generations in Qdrant
  - [ ] Track pattern usage and success metrics
  - [ ] Update pattern rankings based on outcomes
  - [ ] Clean up low-performing patterns

### Task Group 3.3: Code Validation and Skills Integration (7h)

- [ ] **Task 3.3.1**: Basic code validation (2h)
  - [ ] _validate_code() implementation
  - [ ] Syntax checking (AST parsing)
  - [ ] Completeness verification
  - [ ] Structure validation (classes/functions present)

- [ ] **Task 3.3.2**: Skills framework integration (3h)
  - [ ] Apply skills before generation (in prompt)
  - [ ] Validate with skills after generation
  - [ ] apply_skill_standards() for corrections
  - [ ] Track which skills were applied

- [ ] **Task 3.3.3**: Integration testing (2h)
  - [ ] Test with various task types
  - [ ] Verify CodeGenerationService route works
  - [ ] Verify direct agent route works
  - [ ] Measure generation quality metrics

## PHASE 4: Skills Framework (Week 4 - 20h)

### Task Group 4.1: Skills Porting from Agent-OS (10h)

- [ ] **Task 4.1.1**: Port frontend skills (3h)
  - [ ] frontend-responsive (mobile-first, breakpoints)
  - [ ] frontend-components (reusability, composition)
  - [ ] frontend-accessibility (WCAG, ARIA, keyboard nav)
  - [ ] frontend-css (Tailwind, BEM, consistency)

- [ ] **Task 4.1.2**: Port backend skills (3h)
  - [ ] backend-models (ORM, relationships, validation)
  - [ ] backend-api (RESTful, status codes, versioning)
  - [ ] backend-queries (parameterized, optimization, N+1)
  - [ ] backend-migrations (versioning, rollback, zero-downtime)

- [ ] **Task 4.1.3**: Port global/quality skills (3h)
  - [ ] global-coding-style (naming, DRY, formatting)
  - [ ] global-validation (input validation, sanitization)
  - [ ] global-error-handling (try-catch, specific exceptions)
  - [ ] global-commenting (self-documenting, minimal)
  - [ ] global-conventions (git, docs, env config)
  - [ ] global-tech-stack (framework consistency)

- [ ] **Task 4.1.4**: Port testing skill (1h)
  - [ ] testing-test-writing (core flows, strategic testing)

### Task Group 4.2: SkillsFramework Implementation (7h)

- [ ] **Task 4.2.1**: Skill registry and mapping (3h)
  - [ ] Create skills registry with metadata
  - [ ] map_task_to_skills() based on task type
  - [ ] Skill dependency resolution
  - [ ] Priority ordering for skill application

- [ ] **Task 4.2.2**: Skill validation engine (2h)
  - [ ] validate_with_skill() implementation
  - [ ] Run skill-specific checks on code
  - [ ] Generate ValidationResult with details
  - [ ] Categorize issues by severity

- [ ] **Task 4.2.3**: Skill application and correction (2h)
  - [ ] apply_skill_standards() implementation
  - [ ] Auto-fix common violations
  - [ ] Track corrections applied
  - [ ] Report skill compliance scores

### Task Group 4.3: Skills Metrics and Testing (3h)

- [ ] **Task 4.3.1**: Metrics tracking (1h)
  - [ ] Skill usage frequency
  - [ ] Validation pass rates per skill
  - [ ] Correction effectiveness
  - [ ] Skill impact on quality scores

- [ ] **Task 4.3.2**: Skills testing (2h)
  - [ ] Test each skill with sample code
  - [ ] Verify validation logic works
  - [ ] Test auto-correction capabilities
  - [ ] Benchmark skill processing time

## PHASE 5: Full MVP Integration (Week 5 - 30h)

### Task Group 5.1: DevMatrix Pipeline Integration (12h) **[Critical - End-to-End]**

- [ ] **Task 5.1.1**: Phases 1-3 integration (4h)
  - [ ] Integrate SpecParser with DatabaseTaskManager
  - [ ] Store specs in PostgreSQL on ingestion
  - [ ] Connect RequirementsClassifier to database
  - [ ] TaskHierarchyBuilder creates database tasks
  - [ ] Test: simple_task_api.md → PostgreSQL tasks

- [ ] **Task 5.1.2**: Phases 4-5 integration (4h)
  - [ ] Atomization marks tasks in database
  - [ ] GraphOrchestrator imports to Neo4j
  - [ ] Wave generation from dependency analysis
  - [ ] Test: Verify waves generated correctly

- [ ] **Task 5.1.3**: Phase 6 integration (4h)
  - [ ] HybridCodeGenerator executes waves
  - [ ] DatabaseContext provides minimal context per task
  - [ ] Results stored in PostgreSQL
  - [ ] Patterns stored in Qdrant on success
  - [ ] Test: Generate code for all waves

### Task Group 5.2: Remaining Pipeline Phases (8h)

- [ ] **Task 5.2.1**: Phase 6.5 - Code Repair integration (2h)
  - [ ] ComplianceValidator reads from database
  - [ ] CodeRepairOrchestrator updates tasks
  - [ ] Repair results stored in PostgreSQL
  - [ ] Test: Repair flow with low compliance

- [ ] **Task 5.2.2**: Phases 7-8 integration (3h)
  - [ ] SemanticValidator reads task outputs
  - [ ] Validation results in reports table
  - [ ] DiskDeployer exports from database
  - [ ] Test: Validate and deploy to disk

- [ ] **Task 5.2.3**: Phases 9-10 integration (3h)
  - [ ] HealthChecker validates deployment
  - [ ] Health status stored in PostgreSQL
  - [ ] PatternFeedbackIntegration updates Qdrant
  - [ ] Neo4j performance data updated
  - [ ] Test: Complete learning cycle

### Task Group 5.3: API and Monitoring (6h)

- [ ] **Task 5.3.1**: REST API endpoints (3h)
  - [ ] POST /api/specs (create spec)
  - [ ] GET /api/specs/{id}/tasks (task hierarchy)
  - [ ] POST /api/tasks/{id}/execute (execute task)
  - [ ] GET /api/waves/current (current wave status)
  - [ ] GET /api/progress/{spec_id} (progress report)

- [ ] **Task 5.3.2**: ProgressMonitor implementation (2h)
  - [ ] Real-time status tracking
  - [ ] get_spec_progress() from PostgreSQL
  - [ ] get_wave_status() from Neo4j
  - [ ] Dashboard data generation

- [ ] **Task 5.3.3**: WebSocket support (1h)
  - [ ] Real-time progress updates
  - [ ] Wave completion events
  - [ ] Task status changes streaming

### Task Group 5.4: Testing and Validation (4h)

- [ ] **Task 5.4.1**: End-to-end testing (2h)
  - [ ] Test with simple_task_api.md
  - [ ] Test with ecommerce_api_simple.md
  - [ ] Verify all 10 phases execute correctly
  - [ ] Validate wave-based parallel execution

- [ ] **Task 5.4.2**: Performance benchmarking (1h)
  - [ ] Context generation: <100ms
  - [ ] Wave analysis: <500ms
  - [ ] Pattern search: <200ms
  - [ ] Database queries: <100ms p95
  - [ ] Overall speedup: 3-5x vs sequential

- [ ] **Task 5.4.3**: Quality validation (1h)
  - [ ] Compliance rate: >90%
  - [ ] Pattern reuse: >80%
  - [ ] Skill validation pass: >95%
  - [ ] Token reduction: 30-50% verified
  - [ ] Generated code quality scores

## Summary

**Updated Estimates Based on Blueprint Architecture**

- **Total Estimated Effort**: 120 hours (5 weeks)
- **Phases**: 5 (Foundation → Orchestration → Hybrid Gen → Skills → Full MVP)
- **Task Groups**: 16
- **Tasks**: 48
- **Subtasks**: ~150

### Phase Breakdown

| Phase | Focus | Effort | Key Deliverables |
|-------|-------|--------|------------------|
| **1. Foundation** | DatabaseContext + TaskManager | 20h | Minimal context queries, PostgreSQL CRUD |
| **2. Orchestration** | GraphOrchestrator + Waves | 25h | Neo4j wave generation, parallel execution |
| **3. Hybrid Generator** | Code generation integration | 25h | CodeGenerationService + agents, Qdrant patterns |
| **4. Skills Framework** | Port 17 agent-os skills | 20h | SkillsFramework, validation, corrections |
| **5. Full MVP** | End-to-end pipeline integration | 30h | Complete 10-phase integration, testing |

## Dependencies

### Critical Path

```
Foundation Layer (Week 1)
  → DatabaseContext MUST complete before Orchestration
  → DatabaseTaskManager MUST complete before all subsequent work

Orchestration Engine (Week 2)
  → GraphOrchestrator MUST complete before Hybrid Generator
  → Wave generation needed for parallel execution

Hybrid Generator (Week 3)
  → Depends on DatabaseContext for minimal context
  → Depends on Qdrant for pattern storage
  → CodeGenerationService integration required

Skills Framework (Week 4)
  → Can run in parallel with some Phase 3 work
  → Must complete before Phase 5 testing

Full MVP (Week 5)
  → Depends on ALL previous phases
  → Sequential integration of 10 pipeline phases
```

### Parallel Execution Opportunities

- **Week 1**: Database setup tasks (PostgreSQL, Neo4j, Qdrant configs) can run in parallel
- **Week 2**: Neo4j setup + GraphOrchestrator can partially overlap
- **Week 3**: Qdrant setup + HybridCodeGenerator can partially overlap
- **Week 4**: Skills porting (frontend/backend/global) can run in parallel
- **Week 5**: API development can run parallel with pipeline integration

## Risk Factors

### Technical Risks

1. **Context Optimization** (Medium)
   - Risk: Minimal context might miss critical information
   - Mitigation: Iterative testing with various task types, fallback to expanded context
   - Impact: Quality of generated code

2. **Neo4j Wave Performance** (Medium)
   - Risk: Cypher queries slow for large graphs (>1000 tasks)
   - Mitigation: Index optimization, query profiling with EXPLAIN
   - Impact: Wave generation time target (<500ms)

3. **Pattern Quality** (Low-Medium)
   - Risk: Qdrant patterns might not generalize well
   - Mitigation: Threshold tuning (>0.8), pattern validation, quality metrics
   - Impact: Pattern reuse rate target (>80%)

4. **CodeGenerationService Integration** (Medium)
   - Risk: Existing service might not support enhanced prompts
   - Mitigation: Wrapper layer, gradual migration, fallback to direct agents
   - Impact: Code quality for structured tasks

5. **Skills Framework Complexity** (Low)
   - Risk: 17 skills might be too many to maintain
   - Mitigation: Start with core 8 skills, add incrementally
   - Impact: Skill validation coverage

### Integration Risks

6. **Pipeline Modifications** (High)
   - Risk: Changes to 10-phase pipeline could break existing functionality
   - Mitigation: Feature flags, gradual rollout, comprehensive testing
   - Impact: DevMatrix stability

7. **Database Consistency** (Medium)
   - Risk: Data sync issues between PostgreSQL/Neo4j/Qdrant
   - Mitigation: Transactions, eventual consistency patterns, reconciliation
   - Impact: Data integrity

8. **Performance Degradation** (Low-Medium)
   - Risk: Database queries slower than markdown file reads
   - Mitigation: Redis caching, query optimization, connection pooling
   - Impact: Overall execution time

## Success Criteria

### Performance Metrics

- Context generation: <100ms (with Redis cache)
- Wave analysis: <500ms (for 1000+ task graphs)
- Pattern search: <200ms (Qdrant similarity)
- Database queries: <100ms p95 (PostgreSQL)
- Overall speedup: 3-5x vs sequential execution

### Quality Metrics

- Compliance rate: >90% (vs current DevMatrix baseline)
- Pattern reuse: >80% for similar tasks
- Skill validation pass: >95%
- Token reduction: 30-50% vs full markdown context
- Generated code quality: Match or exceed current CodeGenerationService

### Functional Metrics

- All 10 pipeline phases execute successfully
- Wave-based parallel execution works
- Skills applied correctly before/after generation
- Pattern learning improves over time
- Real-time progress tracking functional

## Next Steps Post-MVP

1. **Optimization Phase** (Week 6)
   - Query optimization and profiling
   - Redis caching refinement
   - Pattern quality improvements
   - Performance tuning to hit all targets

2. **Production Readiness** (Week 7-8)
   - Docker containerization
   - CI/CD pipeline setup
   - Monitoring and alerting (Prometheus/Grafana)
   - Documentation and runbooks
   - Security audit and hardening

3. **Scale Testing** (Week 9)
   - Test with 100+ specs
   - Benchmark with 5000+ task graphs
   - Concurrent user load testing
   - Database scaling validation

4. **Advanced Features** (Future)
   - Custom skill creation UI
   - Pattern marketplace
   - Multi-tenancy support
   - Advanced analytics dashboard
   - A/B testing framework for patterns
