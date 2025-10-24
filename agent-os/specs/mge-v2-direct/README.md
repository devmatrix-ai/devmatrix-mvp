# MGE V2 Direct Migration Specification

## Overview
Migración directa de DevMatrix MVP a MGE V2 **SIN** mantener compatibilidad backward con MVP.

**Estrategia**: Replace MVP → Deploy V2 → Rollback via Git si falla

## Key Differences vs DUAL-MODE Migration

| Aspecto | DUAL-MODE | Direct V2 |
|---------|-----------|-----------|
| **Compatibilidad MVP** | ✅ Mantenida | ❌ Reemplazada |
| **Código** | Strategy Pattern, Feature Flags | Directo, más simple |
| **Database** | Dual schema (MVP + V2) | Solo V2 schema |
| **Deployment** | Gradual rollout (5→100%) | Deploy completo |
| **Downtime** | Zero downtime | 2-4 horas |
| **Rollback** | <5 minutos (feature flag) | 30-60 min (git + DB restore) |
| **Timeline** | 16 semanas | **12-14 semanas** |
| **Budget** | $27K-55K | **$20K-40K** |
| **Complejidad código** | +30% | Baseline |
| **Testing surface** | 2x (MVP + V2) | 1x (solo V2) |

## Migration Strategy

### Phase 1: Staging Validation (Week 12)
1. Deploy V2 completo en staging
2. Migrate existing test data (tasks → atoms)
3. Run full E2E test suite
4. Performance benchmarks
5. Security audit
6. **Criterio éxito**: All tests passing, performance targets met

### Phase 2: Production Migration (Week 13)
**Downtime Window**: 2-4 horas (preferible madrugada)

1. **Pre-migration** (30 min)
   - Announce maintenance window
   - Set system to maintenance mode
   - Full database backup
   - Git tag current production (`pre-v2-migration`)
   - Stop all services

2. **Database Migration** (60-90 min)
   - Run Alembic migrations (add V2 tables)
   - Data migration script (tasks → atoms)
   - Verify data integrity
   - Drop old MVP-specific tables (optional, can keep for audit)

3. **Code Deployment** (30 min)
   - Deploy V2 codebase
   - Update environment variables
   - Restart services
   - Health check endpoints

4. **Validation** (30-60 min)
   - Smoke tests
   - Critical path E2E tests
   - Monitor error rates
   - Performance validation

5. **Go Live** (if all green)
   - Remove maintenance mode
   - Announce system live
   - Monitor closely for 2 hours

### Phase 3: Rollback (if needed)
**Estimated time**: 30-60 minutes

1. Set maintenance mode
2. Stop services
3. Git checkout `pre-v2-migration` tag
4. Restore database backup
5. Restart services (MVP mode)
6. Validate rollback success
7. Post-mortem analysis

## Documents

### Planning
- **`idea.md`**: Raw concept and approach
- **`README.md`**: This file - overview and strategy
- **`tasks.md`**: Detailed implementation tasks (~150 tasks)
- **`migration-runbook.md`**: Step-by-step production migration guide

### Reference
- **`/DOCS/MGE_V2/`**: Complete MGE V2 specification
- **`/agent-os/workflows/mge-v2-direct.md`**: Complete workflow (to be created)

## Architecture Changes

### Removed Components (from MVP)
- ❌ `TaskExecutor` service → Replaced by `AtomExecutor`
- ❌ `MasterPlanTask.subtasks` → Replaced by `AtomicUnit`
- ❌ MVP-specific validation → Replaced by 4-level validation
- ❌ Sequential task execution → Replaced by wave-based parallel

### New Components (V2)
- ✅ `MultiLanguageParser` (tree-sitter)
- ✅ `RecursiveDecomposer` (task → atoms)
- ✅ `DependencyAnalyzer` (graph construction)
- ✅ `WaveExecutor` (parallel execution)
- ✅ `HierarchicalValidator` (4 levels)
- ✅ `RetryOrchestrator` (feedback-driven retry)
- ✅ `ConfidenceScorer` + `ReviewQueueManager` (human review)

### Database Schema

**New Tables** (7 total):
```sql
atomic_units           -- 10 LOC execution units
atom_dependencies      -- Dependency edges
dependency_graphs      -- Graph metadata
validation_results     -- 4-level validation
execution_waves        -- Parallel execution groups
atom_retry_history     -- Retry tracking
human_review_queue     -- Manual review queue
```

**Modified Tables**:
```sql
masterplans            -- Add V2 metadata fields
  + atomization_config
  + graph_id (FK to dependency_graphs)
  + v2_mode (always true)
```

**Deprecated Tables** (can drop post-migration):
```sql
masterplan_subtasks    -- Replaced by atomic_units
```

## Success Criteria

### Technical
- ✅ Precision ≥98%
- ✅ Execution time <1.5 hours
- ✅ Cost <$200 per project
- ✅ Parallelization 100+ atoms
- ✅ Context completeness ≥95%
- ✅ All E2E tests passing

### Migration
- ✅ Zero data loss
- ✅ Downtime <4 hours
- ✅ Rollback tested and ready
- ✅ All existing projects migrated successfully
- ✅ Performance targets met in production

### Business
- ✅ User satisfaction ≥4.5/5 (post-migration)
- ✅ Support tickets <15/week (first month)
- ✅ No critical bugs in production
- ✅ Time to value <2 hours

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Data migration failure** | 🟡 MEDIUM | 🔴 HIGH | Full backup, dry-run in staging, rollback ready |
| **Extended downtime** | 🟡 MEDIUM | 🟡 MEDIUM | Thorough staging testing, detailed runbook, extra buffer time |
| **Performance degradation** | 🟢 LOW | 🔴 HIGH | Load testing in staging, performance benchmarks |
| **User resistance** | 🟡 MEDIUM | 🟡 MEDIUM | Clear communication, training, support resources |
| **Rollback needed** | 🟡 MEDIUM | 🔴 HIGH | Tested rollback procedure, 30-60 min recovery |

## Timeline Summary

**12-14 weeks** across 6 phases:

1. **Foundation** (Week 1-2): Infrastructure, DB schema
2. **Atomization** (Week 3-4): tree-sitter, decomposer
3. **Dependencies** (Week 5-6): Graph construction
4. **Validation** (Week 7-8): 4-level validator
5. **Execution** (Week 9-10): Wave executor, retry
6. **Review + Deploy** (Week 11-14): Human review, testing, migration

## Budget Breakdown

| Category | Estimate |
|----------|----------|
| **Development** | $15K-30K |
| **Infrastructure** | +$80/month |
| **Testing/QA** | $3K-7K |
| **Migration** | $2K-3K |
| **Total** | **$20K-40K** |

**Savings vs DUAL-MODE**: $7K-15K

## Rollback Strategy

### When to Rollback
- Critical bugs in production
- Performance <50% of targets
- Data integrity issues
- User-facing errors >5%

### Rollback Process
1. **Announce** maintenance (5 min)
2. **Stop services** (5 min)
3. **Git checkout** `pre-v2-migration` (5 min)
4. **DB restore** from backup (15-30 min)
5. **Restart services** MVP mode (5 min)
6. **Validate** rollback (10 min)
7. **Total**: 30-60 minutes

### Post-Rollback
- Root cause analysis
- Fix issues in staging
- Re-attempt migration when ready

## Next Steps

1. **[ ] Review and approve** this spec
2. **[ ] Assign resources** (2-3 engineers × 12-14 weeks)
3. **[ ] Create detailed tasks** (tasks.md)
4. **[ ] Create migration runbook** (migration-runbook.md)
5. **[ ] Kickoff Phase 1** (Foundation)

---

**Status**: 🔄 Planning Complete | Implementation Pending
**Created**: 2025-10-23
**Timeline**: 12-14 weeks
**Budget**: $20K-40K
**Strategy**: Direct migration, replace MVP
