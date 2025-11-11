# RAG System - Quick Reference Guide

## System Overview
- **Purpose**: Retrieve relevant code examples to improve LLM generation accuracy
- **Vector DB**: ChromaDB (local HTTP server on localhost:8001)
- **Embedding Model**: Jina Code (768 dimensions)
- **Current Performance**: 55.6% success rate (15/27 benchmark queries)

## Key Files

### Core Components
| File | What It Does | Key Classes |
|------|-------------|------------|
| `embeddings.py` | Generate vector embeddings | `EmbeddingModel` |
| `vector_store.py` | Store/search embeddings | `VectorStore`, `SearchRequest` |
| `retriever.py` | High-level retrieval | `Retriever`, `RetrievalConfig`, `RetrievalStrategy` |
| `hybrid_retriever.py` | Multi-signal ranking | `HybridRetriever` |
| `context_builder.py` | Format results for LLM | `ContextBuilder`, `ContextTemplate` |
| `reranker.py` | Re-rank results | `Reranker` |
| `multi_collection_manager.py` | Manage multiple collections | `MultiCollectionManager` |

### Configuration
- `src/config/constants.py` - All environment variables
- Key settings: `EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_SIMILARITY_THRESHOLD`

### Data & Benchmarks
- `DOCS/rag/verification.json` - 258KB test results
- `scripts/benchmark_*.py` - Performance testing
- `scripts/seed_*.py` - Data ingestion

---

## How RAG Works

### 1. Indexing
```python
from src.rag import create_embedding_model, create_vector_store

# Create embedding model
embeddings = create_embedding_model()  # Loads Jina Code

# Create vector store
vector_store = create_vector_store(embeddings)

# Add examples
vector_store.add_batch(
    codes=["def hello(): ...", "function setup() {...}"],
    metadatas=[{"framework": "python"}, {"framework": "javascript"}]
)
```

### 2. Retrieval
```python
from src.rag import create_retriever, RetrievalStrategy

# Create retriever
retriever = create_retriever(
    vector_store,
    strategy=RetrievalStrategy.SIMILARITY,
    top_k=5
)

# Retrieve relevant examples
results = retriever.retrieve("how to define a function")
# Returns: [RetrievalResult, RetrievalResult, ...]
```

### 3. Context Building
```python
from src.rag import create_context_builder, ContextTemplate

# Create context builder
builder = create_context_builder()

# Format for LLM prompt
context = builder.build_context(
    query="how to define a function",
    results=results,
    template=ContextTemplate.DETAILED
)
# Returns: Formatted string ready for LLM
```

---

## Current Issues

### 🔴 BLOCKER: ChromaDB Cache Corruption
**Problem**: All queries return identical documents with identical distances
```
Query 1: "Express server" → distance: 0.172270, docs: [A, B, C]
Query 2: "React hooks" → distance: 0.172270, docs: [A, B, C]  ← SAME!
```

**Impact**: Hybrid retrieval benchmarks are invalid
**Solution**: Reset ChromaDB and re-ingest data

### 🟡 Data Quality Issues
- 64% of examples have "framework: unknown" (metadata dilution)
- Queries expect teaching examples, but have production code
- Generic queries like "Middleware patterns" have 0.018 similarity

### 🟡 Incomplete Features
- HybridRetriever implemented but not integrated
- Feedback learning loop exists but untested
- Limited unit test coverage

---

## Performance Metrics

### Current Results (Phase 4)
| Category | Success Rate | Count |
|----------|--------------|-------|
| TypeScript | 100% | 4/4 |
| Express | 80% | 4/5 |
| React | 50% | 3/6 |
| Node.js | 50% | 1/2 |
| General | 30% | 3/10 |
| **Overall** | **55.6%** | **15/27** |

### Target: 85% (23/27 queries)
Gap: 29.4 percentage points

### Worst Performers
1. "Middleware patterns" - 0.018 similarity
2. "Form submission handling" - 0.025 similarity
3. "Code splitting & performance" - 0.214 similarity

---

## Configuration Tuning

### Environment Variables
```bash
# Embedding
EMBEDDING_MODEL="jinaai/jina-embeddings-v2-base-code"  # or all-mpnet-base-v2
EMBEDDING_DEVICE="cuda"  # or "cpu"

# ChromaDB
CHROMADB_HOST="localhost"
CHROMADB_PORT=8001
CHROMADB_DISTANCE_METRIC="cosine"  # cosine, l2, ip

# Retrieval
RAG_TOP_K=5                          # Results to return
RAG_SIMILARITY_THRESHOLD=0.7         # Minimum quality
RAG_BATCH_SIZE=32                    # Embedding batch size
RAG_CACHE_ENABLED=true               # Use caching

# Per-Collection Thresholds
RAG_SIMILARITY_THRESHOLD_CURATED=0.7      # Curated examples
RAG_SIMILARITY_THRESHOLD_PROJECT=0.6      # Project code
RAG_SIMILARITY_THRESHOLD_STANDARDS=0.5    # Standards
```

### Code-Level Tuning
| Parameter | File | Default | Adjustable |
|-----------|------|---------|-----------|
| MMR Lambda | `retriever.py` | 0.35 | Yes |
| Curated Bonus | `reranker.py` | 0.05 | Yes |
| Medium Length Bonus | `reranker.py` | 0.02 | Yes |
| Hybrid Weights | `hybrid_retriever.py` | 0.5/0.3/0.2 | Yes |

---

## Data Structure

### RetrievalResult
```python
@dataclass
class RetrievalResult:
    id: str                           # Document ID
    code: str                         # Code snippet
    metadata: Dict[str, Any]          # { framework, language, tags, ... }
    similarity: float                 # 0.0-1.0 cosine similarity
    rank: int                         # Position in results (1-based)
    relevance_score: float            # After re-ranking
    mmr_score: Optional[float]        # For MMR strategy
```

### Metadata Keys (Whitelisted)
```python
allowed_keys = {
    "language",          # python, javascript, typescript
    "file_path",         # source file path
    "approved",          # boolean
    "tags",              # list of tags
    "indexed_at",        # timestamp
    "code_length",       # character count
    "author",            # author name
    "task_type",         # type of task
    "source",            # data source
    "framework",         # React, Express, etc.
    "collection",        # collection name
    "source_collection", # original collection
}
```

---

## Common Tasks

### Run Benchmarks
```bash
# Benchmark Phase 4 performance
python scripts/benchmark_phase4_hybrid.py

# Compare embedding models
python scripts/benchmark_embedding_models.py

# Verify data quality
python scripts/verify_rag_quality.py
```

### Add Data
```bash
# Ingest Phase 4 examples
python scripts/ingest_phase4_examples.py

# Extract from GitHub
python scripts/seed_github_repos.py

# Seed from documentation
python scripts/seed_official_docs.py
```

### Analyze
```bash
# Analyze coverage
python scripts/analyze_phase4_coverage.py

# Check RAG quality
python scripts/maintain_rag_quality.py
```

---

## Debugging

### Check Vector Store
```python
from src.rag import create_embedding_model, create_vector_store

embeddings = create_embedding_model()
vector_store = create_vector_store(embeddings)

# Get stats
stats = vector_store.get_stats()
print(f"Total examples: {stats['total_examples']}")

# Health check
is_healthy, message = vector_store.health_check()
print(message)
```

### Test Retrieval
```python
from src.rag import create_retriever

retriever = create_retriever(vector_store)

# Test query
results = retriever.retrieve("test query")
for r in results:
    print(f"Rank {r.rank}: {r.code[:50]}... (sim={r.similarity:.3f})")
```

### Check Cache
```python
# Embedding cache stats
cache_stats = embeddings.get_cache_stats()
print(f"Cache hits: {cache_stats.hit_count}")

# Clear cache if needed
embeddings.clear_cache()
```

---

## Next Steps

### Immediate
1. Reset ChromaDB (fix corruption blocker)
2. Re-ingest Phase 4 data
3. Verify embedding quality

### Short-Term (1-2 weeks)
1. Integrate HybridRetriever into main flow
2. Add metadata to 94 "unknown" examples
3. Analyze failing queries

### Medium-Term (3-4 weeks)
1. Experiment with semantic chunking
2. Try CodeBERT or GraphCodeBERT models
3. Implement query expansion with LLM

### Long-Term (2+ months)
1. Fine-tune embedding model on project code
2. Multi-stage retrieval pipeline
3. Feedback loop for continuous improvement

---

## Useful Links

- **ChromaDB Docs**: https://docs.trychroma.com/
- **Jina Embeddings**: https://jina.ai/embeddings/
- **Sentence Transformers**: https://www.sbert.net/
- **BM25**: https://en.wikipedia.org/wiki/Okapi_BM25
- **MMR**: https://en.wikipedia.org/wiki/Maximal_marginal_relevance

## Support

- **Analysis**: See `RAG_IMPLEMENTATION_ANALYSIS.md`
- **Phase 4 Report**: See `PHASE4_FINAL_REPORT.md`
- **Blocker Details**: See `PHASE4_HYBRID_DISCOVERY.md`
- **Model Experiment**: See `PHASE4_MODEL_EXPERIMENT.md`
