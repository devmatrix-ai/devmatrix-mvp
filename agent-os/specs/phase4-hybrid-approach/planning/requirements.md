# Phase 4 Hybrid Approach - Requirements

## Project Goal
Implement Option D (Hybrid Approach) to achieve 85%+ query success rate in the RAG system's Phase 4 JavaScript/TypeScript ingestion phase.

## Current State
- **Pragmatic ingestion**: 34 hand-curated examples successfully ingested into ChromaDB
- **Quality metrics**: Excellent (100% metadata completeness, 71.2% code quality)
- **Query success rate**: 25.9% (7/27 queries successful) - BELOW TARGET
- **Infrastructure**: All scripts tested and operational

## Problem Statement
The current 34 examples provide high quality but insufficient semantic coverage for queries:
1. **Dataset size too small** - Only 34 vs 400+ needed for semantic matching
2. **Query validation too strict** - Blocks legitimate code queries containing SQL keywords
3. **Semantic model limitations** - General-purpose embeddings not optimized for code
4. **Framework imbalance** - Express 41%, React 29%, TypeScript 24%, Node.js 6%, Cloud/DB 0%

## Target Success Rate
- **Minimum**: 85% query success rate (23/27 queries)
- **Target outcome**: Production-ready Phase 4 RAG system

## Implementation Strategy: Option D (Hybrid)

### Phase 1: Fix Query Validation (0.5-1 hour)
- Remove overly restrictive SQL injection checks from `SearchRequest.validate_query()`
- Allow legitimate code keywords: "union", "update", "select", "insert", etc.
- Implement smarter validation approach
- Re-run benchmarks to measure improvement

### Phase 2: GitHub Extraction (4-6 hours, can run in background)
- Complete `extract_github_typescript.py` using provided GITHUB_TOKEN
- Target: Extract 400-600 real examples from popular JavaScript/TypeScript repositories
- Parallel execution: Can run while Phase 1 validation work completes

### Phase 3: Ingest Extracted Examples (0.5-1 hour)
- Use optimized `ingest_phase4_examples.py` pipeline
- Combine seed examples (34) with extracted examples (400-500)
- Target: 434-534 total examples in ChromaDB
- Expected embedding model: all-mpnet-base-v2 (768 dimensions)

### Phase 4: Re-run Benchmarks (1 hour)
- Execute `benchmark_phase4_queries.py` with full dataset
- Verify 85%+ query success rate achieved
- Identify any remaining weak areas

### Phase 5: Address Gaps (1-2 hours, if needed)
- If success rate <85%: Add targeted curated examples (50-100)
- Focus on underperforming query categories
- Re-benchmark until target achieved

### Phase 6: Documentation & Commit (1 hour)
- Document final Phase 4 metrics and improvements
- Commit all work to main branch
- Prepare foundation for Phase 5 (Cloud/DevOps patterns)

## Alternative Flow (if GitHub extraction too slow)
If GitHub extraction exceeds 6 hours due to API rate limiting:
1. Start GitHub extraction in background (continue running)
2. Execute Phase 5 in parallel: Add 50-100 curated examples targeting failure cases
3. Ingest combined dataset when GitHub extraction completes
4. Final benchmark with full coverage (434-634 examples)

## Success Criteria
✅ 85%+ query success rate on 27-query benchmark suite
✅ 400+ real examples ingested from GitHub
✅ All 34 seed examples preserved and integrated
✅ Zero ingestion failures
✅ Comprehensive documentation of improvements
✅ All work committed to main branch

## Timeline
- **Total estimated time**: 8-12 hours
- **Critical path**: GitHub extraction (4-6 hours)
- **Parallelizable work**: Validation fix + curation can run while extraction proceeds

## Dependencies
- **GitHub token**: `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` (provided)
- **Scripts**: All Phase 4 scripts already implemented and tested
- **Infrastructure**: ChromaDB, embedding model, vector store fully operational
- **Benchmark suite**: 27 test queries validated

## Deliverables
1. ✅ Fixed query validation in `src/rag/vector_store.py`
2. ✅ Extracted 400-600 examples from GitHub
3. ✅ Ingested full dataset into ChromaDB (434-534 examples)
4. ✅ Benchmark results showing 85%+ success rate
5. ✅ Documentation of Phase 4 completion
6. ✅ Commit to main branch with detailed commit message

## Notes
- This hybrid approach addresses both immediate validation issues AND root cause (dataset size)
- Real GitHub examples provide better semantic coverage than pure curation
- Alternative flow provides contingency for slow API extraction
- Phase 4 completion enables Phase 5 (Cloud/DevOps) to begin
