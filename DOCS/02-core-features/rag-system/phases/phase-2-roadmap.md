# Fase 2: Multi-Collection Implementation - ROADMAP

**Status:** Ready to start
**Estimated Duration:** 4-5 days
**Priority:** CRITICAL PATH

---

## Overview

Fase 2 builds on the GPU optimization from Fase 1 by implementing the multi-collection architecture that was designed in Phase 1.

**Current State:**
- ✅ MultiCollectionManager code created
- ✅ Adaptive thresholds configured
- ✅ GPU model operational
- ⏳ Need: Physical collection separation in ChromaDB
- ⏳ Need: Retriever integration

---

## Phase 2 Objectives

### 2.1 Retriever Integration

**Task:** Integrate `MultiCollectionManager` into `src/rag/retriever.py`

**Details:**
- Modify `Retriever` class to accept both `VectorStore` and `MultiCollectionManager`
- Add strategy selection: `use_multi_collection=True/False`
- Route queries through MultiCollectionManager when enabled
- Maintain backward compatibility

**Acceptance Criteria:**
- Retriever can work with single collection (current mode)
- Retriever can work with multi-collection (new mode)
- All tests pass
- No performance regression

**Estimated Time:** 2-3 hours

### 2.2 Physical Collection Creation

**Task:** Separate current collection into 3 collections in ChromaDB

**Current Situation:**
```
Single Collection (default)
├─ 30 enhanced patterns (curated)
├─ 10 project standards (standards)
├─ 16 official docs (should be curated)
└─ Empty: project_code (reserved for future)
```

**Target Situation:**
```
devmatrix_curated (46 examples)
├─ 30 enhanced patterns
├─ 16 official docs
└─ [Will accept GitHub examples in Fase 3]

devmatrix_standards (10 examples)
├─ 10 project standards
└─ [Will accept constitution/contributing in Fase 3]

devmatrix_project_code (0 examples - ready)
└─ [Will auto-populate from task execution in Fase 3]
```

**Implementation:**
1. Create script: `scripts/redistribute_collections.py`
2. Read all examples from current collection
3. Categorize by source
4. Create 3 separate collections
5. Re-index appropriately
6. Verify counts match

**Acceptance Criteria:**
- 3 collections exist in ChromaDB
- Total examples: 56 (all accounted for)
- Collection names match constants
- Query any collection returns results

**Estimated Time:** 3-4 hours

### 2.3 Integration Testing

**Task:** Test multi-collection search end-to-end

**Test Scenarios:**
1. Query with results in curated only
2. Query with fallback to project_code
3. Query with fallback to standards
4. Query with no results (handle gracefully)
5. Collection statistics endpoint
6. Single collection searches

**Test Queries:**
```python
test_queries = [
    "FastAPI dependency injection",       # Should find in curated
    "password hashing bcrypt",             # Edge case - may fallback
    "REST API design pattern",             # Generic - might need fallback
    "project structure recommendation",    # Should find in standards
    "xyzabc nonsense query",              # Should handle no results
]
```

**Acceptance Criteria:**
- All test queries return appropriate results
- No crashes or exceptions
- Logging shows which collection was used
- Performance <100ms per query

**Estimated Time:** 2-3 hours

### 2.4 Documentation

**Create in DOCS/rag/:**

1. **architecture.md** (2-3 hours)
   - Multi-collection design
   - Fallback strategy flowchart
   - Use cases per collection
   - Decision tree for queries

2. **collection_management.md** (1 hour)
   - How to move examples between collections
   - Adding new collections
   - Maintenance procedures

3. **configuration.md** (1 hour)
   - Threshold tuning guide
   - Performance optimization
   - Collection size recommendations

**Acceptance Criteria:**
- Clear explanation of why 3 collections
- Diagrams/flowcharts included
- Ready for team consumption

**Estimated Time:** 4 hours

---

## Fase 2 Timeline

```
Day 1:
  Morning: Retriever integration (2-3h)
  Afternoon: Physical collection creation (3-4h)
  Total: ~6-7 hours

Day 2:
  Morning: Integration testing (2-3h)
  Afternoon: Documentation (4h)
  Total: ~6-7 hours

Day 3: Buffer/Polish
  Final testing, edge cases, documentation review
```

**Total Duration:** 2.5-3 days

---

## Definition of Done

### Technical
- [ ] MultiCollectionManager integrated into Retriever
- [ ] 3 physical collections in ChromaDB with correct examples
- [ ] All tests passing (integration + unit)
- [ ] No performance regression
- [ ] Logging shows collection selection per query

### Documentation
- [ ] architecture.md explains design
- [ ] collection_management.md explains operations
- [ ] configuration.md explains tuning
- [ ] All docs in DOCS/rag/ folder

### Verification
- [ ] Run 30 test queries across all collections
- [ ] All retrieve results meet threshold
- [ ] Collection stats endpoint works
- [ ] Fallback strategy works as expected

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Retriever integration time | <4 hours |
| Collection creation time | <4 hours |
| Test execution time | <3 hours |
| Documentation time | <4 hours |
| Query success rate | >80% (before data population) |
| Query latency | <100ms |
| No regressions | ✓ |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Data loss during collection split | Low | High | Backup before split |
| Performance degradation | Medium | Medium | Benchmark before/after |
| Retriever API change breaks agents | Low | High | Backward compatibility |
| Threshold tuning issues | Medium | Low | Test with multiple thresholds |

---

## Dependencies

### Prerequisite (✅ Complete)
- GPU model operational
- Adaptive thresholds configured
- MultiCollectionManager code written

### Blocks Fase 3
- Needs: Working multi-collection system before adding GitHub data

---

## Next: Fase 3 - Data Population

Once Fase 2 completes:
1. Start `scripts/seed_github_repos.py` (200-300 examples)
2. Expand `scripts/seed_official_docs.py` (50+ examples)
3. Target: 500+ examples in RAG
4. Expected: Success rate jumps to >50%

---

## Quick Start for Fase 2

```bash
# 1. Review MultiCollectionManager
cat src/rag/multi_collection_manager.py

# 2. Plan Retriever changes
# - Open src/rag/retriever.py
# - Review current __init__ and retrieve methods
# - Design integration points

# 3. Create collection redistribution script
# - Read current collection
# - Categorize examples
# - Create 3 new collections
# - Verify migration

# 4. Write integration tests
# - Test each collection
# - Test fallback behavior
# - Test statistics

# 5. Document architecture
# - Create diagrams
# - Write flowcharts
# - Explain decisions
```

---

## Communication Checklist

Before starting Fase 2:
- [ ] Review GPU optimization results with team
- [ ] Confirm multi-collection approach approved
- [ ] Get threshold tuning parameters
- [ ] Identify collection categorization rules
- [ ] Schedule integration testing time

---

## Success Declaration

Fase 2 is complete when:
1. ✅ Retriever seamlessly switches between single/multi-collection mode
2. ✅ 3 physical collections in ChromaDB with correct data distribution
3. ✅ All 30 benchmark queries return >0.7 similarity from at least one collection
4. ✅ Multi-collection fallback strategy works as documented
5. ✅ Team can understand architecture from documentation
6. ✅ Zero regressions compared to Phase 1

---

**Phase 2 Ready to Start** ✅

See: `DOCS/rag/PHASE1_GPU_OPTIMIZATION_COMPLETE.md` for context.
