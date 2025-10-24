# MGE V2 Direct Migration Workflow
## DevMatrix MVP → MGE V2 (Direct Replacement)

**Version**: 1.0
**Created**: 2025-10-23
**Strategy**: Direct Migration (Replace MVP)
**Duration**: 12-14 semanas
**Budget**: $20K-40K + $80/mes infraestructura
**Downtime**: 2-4 horas (production migration)

---

## 🎯 Executive Summary

### Migration Approach
**Direct Replacement**: Reemplazamos MVP completamente con V2, sin mantener compatibilidad.

**Key Decisions**:
- ✅ Paramos sistema durante migración (2-4h downtime)
- ✅ Rollback via Git + DB restore (30-60 min)
- ✅ No Strategy Pattern, no Feature Flags
- ✅ Arquitectura más simple y limpia
- ✅ -30% código vs DUAL-MODE
- ✅ -4 semanas desarrollo

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
- ✅ ROI: 4 meses

---

## 📊 Simplified Architecture

### What We Remove (MVP)
```python
# DEPRECATED - To be removed
src/services/task_executor.py          # → Replaced by AtomExecutor
src/models/masterplan.py:MasterPlanSubtask  # → Replaced by AtomicUnit

# MODIFIED - Keep but update
src/services/masterplan_generator.py   # → Update to generate atoms, not tasks
src/models/masterplan.py:MasterPlan    # → Add V2 metadata fields
```

### What We Add (V2)
```python
# NEW SERVICES (11 components)
src/atomization/parser.py              # MultiLanguageParser (tree-sitter)
src/atomization/decomposer.py          # RecursiveDecomposer
src/atomization/context_injector.py    # ContextInjector
src/atomization/validator.py           # AtomicityValidator

src/dependencies/analyzer.py           # DependencyAnalyzer
src/dependencies/graph.py              # Graph operations
src/dependencies/wave_generator.py     # WaveGenerator

src/validation/hierarchical_validator.py  # 4-level coordinator
src/validation/atomic_validator.py     # Level 1
src/validation/module_validator.py     # Level 2
src/validation/component_validator.py  # Level 3
src/validation/system_validator.py     # Level 4

src/execution/wave_executor.py         # Parallel wave execution
src/execution/retry_orchestrator.py    # 3-attempt retry with feedback
src/execution/feedback_generator.py    # Error analysis → prompt

src/review/confidence_scorer.py        # Quality scoring
src/review/queue_manager.py            # Review queue
src/review/ai_assistant.py             # Fix suggestions

# NEW MODELS (7 tables)
src/models/atomic_unit.py              # AtomicUnit model
src/models/dependency_graph.py         # DependencyGraph model
src/models/validation_result.py        # ValidationResult model
src/models/execution_wave.py           # ExecutionWave model
src/models/atom_retry.py               # AtomRetryHistory model
src/models/human_review.py             # HumanReviewQueue model
```

---

## 📅 6-Phase Implementation Plan

### Phase 1: Foundation & Database (Week 1-2)

**Objetivo**: Setup infrastructure y schema V2

**Tasks**:
- [ ] Add dependencies to `requirements.txt`
  ```bash
  tree-sitter==0.20.1
  tree-sitter-python
  tree-sitter-typescript
  tree-sitter-javascript
  networkx==3.1
  ```
- [ ] Create database migration `202510xx_mge_v2_schema.py`
  - [ ] Add 7 new tables (atomic_units, atom_dependencies, etc.)
  - [ ] Modify masterplans table (add v2 metadata)
  - [ ] Add indexes for performance
- [ ] Test migration up/down in local
- [ ] Deploy to staging DB
- [ ] Create data migration script `migrate_tasks_to_atoms.py`
  - [ ] Convert existing tasks → atoms (for testing)
  - [ ] Preserve task metadata
  - [ ] Verify data integrity
- [ ] Setup monitoring
  - [ ] Prometheus metrics for V2
  - [ ] Grafana dashboard
  - [ ] Alerts configuration

**Deliverables**:
- ✅ Database schema V2 ready
- ✅ Migration scripts tested
- ✅ Monitoring configured

**Testing**:
- Migration up/down successful
- Data migration preserves integrity
- Performance acceptable

**Criterio de éxito**:
- All migrations run successfully
- No data loss in test migrations
- Rollback works correctly

---

### Phase 2: AST Atomization (Week 3-4)

**Objetivo**: Implementar Phase 3 de MGE V2 (task → atoms decomposition)

**Tasks**:
- [ ] Implement `MultiLanguageParser`
  - `src/atomization/parser.py`
  - Python, TypeScript, JavaScript parsers
  - AST extraction
  - Complexity calculation
  - LOC counting

- [ ] Implement `RecursiveDecomposer`
  - `src/atomization/decomposer.py`
  - Recursive splitting algorithm
  - Atomicity validation (10 LOC, complexity <3.0)
  - Boundary detection
  - Decomposition scoring

- [ ] Implement `ContextInjector`
  - `src/atomization/context_injector.py`
  - Import extraction from AST
  - Type schema inference
  - Preconditions/postconditions
  - Test case generation
  - 95% context completeness target

- [ ] Implement `AtomicityValidator`
  - `src/atomization/validator.py`
  - 10 atomicity criteria checks
  - Scoring algorithm

- [ ] Create `AtomService`
  - `src/services/atom_service.py`
  - CRUD for atomic_units
  - Decomposition orchestration

- [ ] API endpoints
  - `POST /api/v2/atomization/decompose`
  - `GET /api/v2/atoms/{atom_id}`
  - `GET /api/v2/atoms/by-task/{task_id}`

**Deliverables**:
- ✅ Task → Atoms decomposition working
- ✅ Context injection 95% complete
- ✅ Atomicity validation passing

**Testing**:
- Unit tests per language parser
- Decomposition tests (80 LOC → 8 atoms)
- Context completeness tests (≥95%)
- Atomicity score tests

**Criterio de éxito**:
- 1 task (80 LOC) → 8 atoms (10 LOC each)
- Context completeness ≥95%
- Atomicity score >0.9 for 90% atoms

---

### Phase 3: Dependency Graph (Week 5-6)

**Objetivo**: Implementar Phase 4 de MGE V2 (dependency-aware execution order)

**Tasks**:
- [ ] Implement `DependencyAnalyzer`
  - `src/dependencies/analyzer.py`
  - Import dependency detection
  - Data flow analysis
  - Function call tracking
  - Type dependency detection

- [ ] Implement Graph operations
  - `src/dependencies/graph.py`
  - NetworkX DiGraph construction
  - Topological sort
  - Cycle detection
  - Level-based grouping

- [ ] Implement `WaveGenerator`
  - `src/dependencies/wave_generator.py`
  - Parallel group detection
  - Wave boundary identification
  - Parallelization maximization

- [ ] Create `DependencyService`
  - `src/services/dependency_service.py`
  - Graph building orchestration
  - CRUD for dependency_graphs, execution_waves

- [ ] API endpoints
  - `GET /api/v2/graphs/{graph_id}`
  - `GET /api/v2/graphs/{graph_id}/waves`
  - `GET /api/v2/graphs/{graph_id}/visualize`

**Deliverables**:
- ✅ Dependency graph construction
- ✅ Topological ordering
- ✅ Wave generation (100+ atoms/wave)

**Testing**:
- Dependency detection accuracy (>90%)
- Topological sort correctness
- Cycle detection tests
- Wave grouping tests (>50x parallelization)

**Criterio de éxito**:
- 800 atoms → 8-10 waves
- 100+ atoms per wave average
- Cycle detection prevents deadlocks
- Topological order correct

---

### Phase 4: Hierarchical Validation (Week 7-8)

**Objetivo**: Implementar Phase 5 de MGE V2 (4-level validation)

**Tasks**:
- [ ] Implement `AtomicValidator` (Level 1)
  - `src/validation/atomic_validator.py`
  - Syntax validation (AST parsing)
  - Type checking (mypy integration)
  - Unit test generation + execution
  - Atomicity criteria validation

- [ ] Implement `ModuleValidator` (Level 2)
  - `src/validation/module_validator.py`
  - Integration tests (10-20 atoms)
  - API consistency checks
  - Cohesion analysis

- [ ] Implement `ComponentValidator` (Level 3)
  - `src/validation/component_validator.py`
  - Component E2E tests
  - Architecture compliance
  - Performance benchmarks

- [ ] Implement `SystemValidator` (Level 4)
  - `src/validation/system_validator.py`
  - Full system E2E
  - Acceptance criteria
  - Production readiness

- [ ] Implement `HierarchicalValidator`
  - `src/validation/hierarchical_validator.py`
  - Coordinate 4 levels
  - Boundary-aware validation
  - Early error detection

- [ ] Create `ValidationService`
  - `src/services/validation_service.py`
  - Orchestration
  - CRUD for validation_results

- [ ] API endpoints
  - `POST /api/v2/validation/run`
  - `GET /api/v2/validation/results/{atom_id}`

**Deliverables**:
- ✅ 4-level validation system
- ✅ Early error detection
- ✅ Progressive validation

**Testing**:
- Each validator level unit tests
- Integration between levels
- False positive rate <5%
- Validation time <2 min/atom

**Criterio de éxito**:
- Level 1: 99% syntax correctness
- Level 2: 95% integration pass
- Level 3: 90% component E2E pass
- Level 4: 85% system E2E pass
- Early detection >90%

---

### Phase 5: Execution + Retry (Week 9-10)

**Objetivo**: Implementar Phase 6 de MGE V2 (wave-based parallel execution)

**Tasks**:
- [ ] Implement `WaveExecutor`
  - `src/execution/wave_executor.py`
  - Parallel execution (100+ concurrent)
  - Dependency-aware coordination
  - Progress tracking
  - Error handling per atom

- [ ] Implement `RetryOrchestrator`
  - `src/execution/retry_orchestrator.py`
  - 3-attempt retry loop
  - Error analysis
  - Temperature adjustment (0.7 → 0.5 → 0.3)
  - Backoff strategy

- [ ] Implement `FeedbackGenerator`
  - `src/execution/feedback_generator.py`
  - Error message parsing
  - Context-aware prompts
  - Previous attempt analysis

- [ ] Create `ExecutionServiceV2`
  - `src/services/execution_service_v2.py`
  - Wave orchestration
  - Retry management
  - CRUD for atom_retry_history

- [ ] **Replace** `MasterPlanGenerator`
  - Update to generate atoms directly (not tasks)
  - Integration with atomization pipeline
  - Preserve masterplan metadata

- [ ] API endpoints
  - `POST /api/v2/execution/start`
  - `GET /api/v2/execution/status/{masterplan_id}`
  - `POST /api/v2/retry/{atom_id}`

**Deliverables**:
- ✅ Wave-based parallel execution
- ✅ Retry with feedback
- ✅ 100+ atoms concurrent

**Testing**:
- Parallel execution stress tests
- Retry success rate tests (99% after 3 attempts)
- Feedback quality tests
- Integration with validation

**Criterio de éxito**:
- 90% atoms success attempt 1
- 99% success after 3 attempts
- 100+ atoms executing parallel
- Retry reduces errors 50%+

---

### Phase 6: Human Review + Final Integration (Week 11-14)

**Objetivo**: Complete human review system + comprehensive testing + migration

#### Week 11: Human Review System

**Tasks**:
- [ ] Implement `ConfidenceScorer`
  - `src/review/confidence_scorer.py`
  - Validation results weight (40%)
  - Attempts needed weight (30%)
  - Complexity weight (20%)
  - Integration tests weight (10%)

- [ ] Implement `ReviewQueueManager`
  - `src/review/queue_manager.py`
  - Sort by confidence
  - Select bottom 15-20%
  - Priority assignment
  - CRUD for human_review_queue

- [ ] Implement `AIAssistant`
  - `src/review/ai_assistant.py`
  - Issue detection
  - Fix suggestions
  - Alternative implementations

- [ ] Create Review UI
  - `src/ui/src/pages/ReviewQueue.tsx`
  - Code viewer with diff
  - AI suggestions panel
  - Approve/Edit/Regenerate actions

- [ ] API endpoints
  - `GET /api/v2/review/queue`
  - `POST /api/v2/review/approve`
  - `POST /api/v2/review/edit`

**Deliverables**:
- ✅ Confidence scoring
- ✅ Review queue
- ✅ AI-assisted review UI

#### Week 12: Staging Deployment & Testing

**Tasks**:
- [ ] Deploy complete V2 to staging
- [ ] End-to-end testing
  - `tests/e2e/test_v2_full_flow.py`
  - Discovery → Masterplan → Atomization → Execution
  - Test with 10+ real projects

- [ ] Performance testing
  - Execution time <1.5h
  - Precision ≥98%
  - Cost <$200
  - Parallelization 100+ atoms

- [ ] Load testing
  - 10+ concurrent masterplans
  - Database performance
  - API response times

- [ ] Security audit
  - Code injection tests
  - Sandbox escape tests
  - Authentication tests

- [ ] Data migration dry-run
  - Migrate production snapshot to staging
  - Verify all tasks → atoms conversion
  - Test data integrity

**Deliverables**:
- ✅ All E2E tests passing
- ✅ Performance targets met
- ✅ Security audit passed
- ✅ Data migration validated

#### Week 13: Production Migration

**Downtime Window**: 2-4 hours (preferably madrugada/weekend)

**Pre-Migration Checklist**:
- [ ] All staging tests green
- [ ] Rollback procedure tested
- [ ] Database backup verified
- [ ] Git tag created: `pre-v2-migration`
- [ ] Team on-call ready
- [ ] Communication sent to users

**Migration Steps** (see migration-runbook.md for details):

1. **Announce Maintenance** (T-2 hours)
   - Email users
   - Set status page
   - Social media announcement

2. **Enable Maintenance Mode** (T+0:00)
   - Return 503 for all endpoints
   - Display maintenance page

3. **Stop Services** (T+0:05)
   ```bash
   docker-compose stop backend
   docker-compose stop celery
   ```

4. **Database Backup** (T+0:10)
   ```bash
   pg_dump devmatrix > backup_pre_v2_$(date +%Y%m%d_%H%M).sql
   ```

5. **Run Migrations** (T+0:20)
   ```bash
   alembic upgrade head  # Add V2 tables
   ```

6. **Data Migration** (T+0:30)
   ```bash
   python scripts/migrate_tasks_to_atoms.py --production
   ```
   - Convert all existing tasks → atoms
   - Verify 100% conversion success
   - Check data integrity

7. **Deploy V2 Code** (T+1:30)
   ```bash
   git checkout v2.0.0
   docker-compose build
   docker-compose up -d
   ```

8. **Health Checks** (T+2:00)
   - Database connectivity
   - Redis connectivity
   - ChromaDB connectivity
   - API endpoints responding

9. **Smoke Tests** (T+2:15)
   - Create test masterplan
   - Run atomization
   - Execute 10 atoms
   - Verify results

10. **Go Live Decision** (T+2:30)
    - If all green → Remove maintenance mode
    - If issues → Initiate rollback

11. **Monitor Closely** (T+2:30 → T+4:30)
    - Error rates
    - Performance metrics
    - User feedback
    - Support tickets

**Deliverables**:
- ✅ V2 live in production
- ✅ Zero data loss
- ✅ Performance targets met
- ✅ Users can execute masterplans

#### Week 14: Post-Migration Validation

**Tasks**:
- [ ] 48-hour monitoring
  - Error rates <1%
  - Performance stable
  - User satisfaction tracking

- [ ] Fix any critical issues immediately

- [ ] Documentation updates
  - User guide for V2
  - API documentation
  - Troubleshooting guide

- [ ] Performance optimization
  - Based on production metrics
  - Bottleneck identification
  - Query optimization

- [ ] Success criteria validation
  - Precision ≥98%?
  - Time <1.5h?
  - Cost <$200?
  - Users satisfied?

**Deliverables**:
- ✅ V2 stable in production
- ✅ All success criteria met
- ✅ Documentation complete
- ✅ Users happy 🎉

---

## 🔄 Rollback Procedure

### When to Rollback
- **Critical bugs**: System unusable
- **Data integrity**: Data corruption detected
- **Performance**: <50% of targets
- **User impact**: >5% error rate

### Rollback Steps (30-60 minutes)

1. **Announce Rollback** (5 min)
   - Set maintenance mode
   - Notify team

2. **Stop V2 Services** (5 min)
   ```bash
   docker-compose stop
   ```

3. **Restore Database** (15-30 min)
   ```bash
   psql devmatrix < backup_pre_v2_YYYYMMDD_HHMM.sql
   ```

4. **Deploy MVP Code** (10 min)
   ```bash
   git checkout pre-v2-migration
   docker-compose build
   docker-compose up -d
   ```

5. **Validate Rollback** (10 min)
   - Health checks
   - Smoke tests
   - Data integrity

6. **Go Live** (5 min)
   - Remove maintenance mode
   - Announce rollback complete

### Post-Rollback
- [ ] Root cause analysis
- [ ] Fix issues in staging
- [ ] Re-test thoroughly
- [ ] Schedule new migration date

---

## 💰 Budget Breakdown

| Category | Estimate | Notes |
|----------|----------|-------|
| **Development** | $15K-30K | 2-3 engineers × 12-14 weeks |
| **Infrastructure** | +$80/month | Increased compute, storage |
| **Testing/QA** | $3K-7K | E2E, performance, security |
| **Migration** | $2K-3K | Downtime, data migration, validation |
| **Contingency** | $3K-5K | Bug fixes, unexpected issues |
| **Total** | **$20K-40K** | One-time + $80/month recurring |

**Savings vs DUAL-MODE**: $7K-15K

---

## ✅ Success Criteria

### Technical Metrics
- ✅ Precision ≥98%
- ✅ Execution time <1.5 hours
- ✅ Cost <$200 per project
- ✅ Parallelization 100+ atoms
- ✅ Context completeness ≥95%

### Migration Metrics
- ✅ Zero data loss
- ✅ Downtime <4 hours
- ✅ Rollback tested (<60 min)
- ✅ All projects migrated successfully

### Business Metrics
- ✅ User satisfaction ≥4.5/5
- ✅ Support tickets <15/week (first month)
- ✅ No critical bugs
- ✅ Time to value <2 hours

---

## ⚠️ Risk Management

| Risk | Mitigation |
|------|------------|
| **Extended downtime** | Thorough staging testing, detailed runbook, buffer time |
| **Data migration failure** | Full backup, dry-run in staging, rollback ready |
| **Performance issues** | Load testing in staging, monitoring, optimization |
| **User resistance** | Communication, training, support resources |
| **Rollback needed** | Tested procedure, 30-60 min recovery time |

---

## 📚 Documentation Deliverables

- [ ] **API Documentation** (Swagger/OpenAPI)
- [ ] **Architecture Diagrams** (Mermaid/PlantUML)
- [ ] **Migration Runbook** (Step-by-step guide)
- [ ] **User Guide** (How to use V2 features)
- [ ] **Developer Onboarding** (How to contribute)
- [ ] **Troubleshooting Guide** (Common issues)

---

## 🎯 Summary

**12-14 weeks** para migración completa:
- ✅ Más simple que DUAL-MODE (-30% código)
- ✅ Más rápido (-4 semanas)
- ✅ Más barato (-$7K-15K)
- ✅ Arquitectura más limpia
- ❌ Downtime 2-4h (aceptable)
- ❌ Rollback más lento (30-60 min vs <5 min)

**ROI**: 4 meses | **Mejoras**: 98% precision, 1.5h execution, 100+ parallel

---

**Document Status**: ✅ Complete
**Next Step**: Create detailed tasks.md
**Ready for**: Resource allocation and kickoff
