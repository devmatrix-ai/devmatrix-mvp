# RAG System Documentation

Welcome to the RAG (Retrieval-Augmented Generation) system documentation for the Agentic AI project.

---

## 📋 Quick Navigation

### Current Status
- **Phase 1:** ✅ GPU OPTIMIZATION - COMPLETE
- **Phase 2:** 📋 Multi-Collection Implementation - READY TO START
- **Phase 3+:** 📅 In Planning

### Executive Summary
Start here for a high-level overview: [**PHASE1_GPU_OPTIMIZATION_COMPLETE.md**](PHASE1_GPU_OPTIMIZATION_COMPLETE.md)

---

## 📚 Documentation by Phase

### Phase 1: GPU Optimization ✅

**Status:** 100% Complete (Nov 3, 2025)

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [PHASE1_GPU_OPTIMIZATION_COMPLETE.md](PHASE1_GPU_OPTIMIZATION_COMPLETE.md) | Executive summary of Phase 1 completion | 10 min |
| [embedding_model_research.md](embedding_model_research.md) | Detailed model comparison & selection rationale | 15 min |
| [embedding_benchmark.md](embedding_benchmark.md) | Benchmark results & performance metrics | 8 min |

**Key Achievements:**
- Selected & deployed `jinaai/jina-embeddings-v2-base-code` (768-dim, GPU-optimized)
- Implemented adaptive threshold system (0.65/0.55/0.60)
- Created MultiCollectionManager architecture
- Re-indexed all 56 examples with new model
- Achieved 31ms average retrieval time (target: <100ms) ✅

---

### Phase 2: Multi-Collection Implementation 🔄

**Status:** Ready to Start (4-5 days estimated)

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [PHASE2_ROADMAP.md](PHASE2_ROADMAP.md) | Detailed Phase 2 implementation plan | 15 min |

**Planned Tasks:**
1. Integrate MultiCollectionManager into Retriever
2. Create 3 physical collections in ChromaDB
3. Integration testing & validation
4. Architecture documentation

**Success Criteria:**
- Multi-collection system fully operational
- All benchmark queries return appropriate results
- Architecture documented & team-ready

---

### Phase 3: Data Population 📊

**Status:** In Planning (targeting 500+ examples)

**Planned Sources:**
- GitHub: 200-300 high-quality examples from FastAPI, SQLModel, Pydantic, Pytest, HTTPX
- Official Docs: 50+ expanded examples
- Auto-indexing: Task execution feedback loop

**Expected Impact:** Success rate jump to 50%+

---

## 🏗️ Architecture

### Current System (Post Phase 1)

```
Application (Agents)
    ↓
Retriever Interface (SingleVectorStore mode)
    ↓
VectorStore (ChromaDB - default collection)
    ├─ 30 Enhanced Patterns (768-dim)
    ├─ 10 Project Standards (768-dim)
    ├─ 16 Official Docs (768-dim)
    └─ Total: 56 examples

Embedding Model: jinaai/jina-embeddings-v2-base-code (GPU)
Device: CUDA (RTX 4070 Ti SUPER)
```

### Target System (Post Phase 2)

```
Application (Agents)
    ↓
Retriever Interface (MultiCollection mode)
    ↓
MultiCollectionManager
    ├─ devmatrix_curated (46 examples)
    │  └─ Threshold: 0.65
    ├─ devmatrix_project_code (0 examples, ready)
    │  └─ Threshold: 0.55
    └─ devmatrix_standards (10 examples)
       └─ Threshold: 0.60

Embedding Model: jinaai/jina-embeddings-v2-base-code (GPU, 768-dim)
Device: CUDA (RTX 4070 Ti SUPER)
Fallback Strategy: Curated → Project → Standards
```

---

## 🔧 Configuration Reference

### Key Variables (src/config/constants.py)

```python
# Embedding Model Configuration
EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-base-code"
EMBEDDING_DEVICE = "cuda"  # or "cpu"

# Similarity Thresholds
RAG_SIMILARITY_THRESHOLD = 0.7  # General threshold
RAG_SIMILARITY_THRESHOLD_CURATED = 0.65  # High-quality examples
RAG_SIMILARITY_THRESHOLD_PROJECT = 0.55  # More lenient
RAG_SIMILARITY_THRESHOLD_STANDARDS = 0.60  # Moderate

# Retrieval Configuration
RAG_TOP_K = 5  # Examples to retrieve
RAG_BATCH_SIZE = 32
RAG_MAX_CONTEXT_LENGTH = 8000
```

---

## 📊 Performance Metrics

### Phase 1 Results

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Embedding Dims | 384 | 768 | ✅ |
| Device | CPU | GPU | ✅ |
| Avg Retrieval | 50-100ms | 31ms | ✅ |
| Success Rate | 3.3% | 3.3%* | 85% (Phase 3) |
| Examples | 56 | 56 (new) | 1000+ (Phase 5) |

*No change yet due to low example count and high threshold. Will improve with Phase 2-3.

---

## 🚀 Quick Start

### For Developers

1. **Understanding the System:**
   - Read: PHASE1_GPU_OPTIMIZATION_COMPLETE.md
   - Then: PHASE2_ROADMAP.md

2. **Working with RAG:**
   - Import: `from src.rag import create_retriever, create_embedding_model`
   - Initialize: `retriever = create_retriever(vector_store)`
   - Query: `results = retriever.retrieve(query="your query")`

3. **Adding Examples:**
   - See: adding_examples.md (TBD in Phase 5)

### For Operations

1. **Monitoring:**
   - Check: RAG health metrics via API `/api/v1/rag/metrics`
   - Verify: Collection stats via `MultiCollectionManager.get_collection_stats()`

2. **Maintenance:**
   - Monthly: Run `scripts/maintain_rag_quality.py`
   - Quarterly: Re-benchmark with `scripts/benchmark_embedding_models.py`

---

## 📝 Files Reference

### Core RAG Components

| File | Lines | Purpose |
|------|-------|---------|
| src/rag/embeddings.py | ~350 | Embedding model wrapper |
| src/rag/vector_store.py | ~400 | ChromaDB wrapper |
| src/rag/retriever.py | ~300 | Retrieval strategies |
| src/rag/multi_collection_manager.py | ~286 | Multi-collection orchestration (NEW) |

### Configuration

| File | Purpose |
|------|---------|
| src/config/constants.py | RAG configuration (UPDATED) |
| src/config/__init__.py | Config exports (UPDATED) |

### Scripts

| Script | Purpose |
|--------|---------|
| scripts/seed_enhanced_patterns.py | Curated examples |
| scripts/seed_project_standards.py | Project standards |
| scripts/seed_official_docs.py | Official documentation |
| scripts/migrate_existing_code.py | Project code migration |
| scripts/orchestrate_rag_population.py | Orchestration master |
| scripts/benchmark_embedding_models.py | Performance validation (NEW) |
| scripts/verify_rag_quality.py | Quality verification |

---

## 🎯 Success Metrics

### Phase 1: ✅ Complete
- GPU model deployed & verified
- All configurations working
- Examples re-indexed
- Benchmarking complete

### Phase 2: 📋 Ready
- Multi-collection integration
- 3 physical collections
- Comprehensive testing
- Team documentation

### Phase 3: 📅 Planned
- Data population (500+ examples)
- Success rate: >50%
- Threshold tuning

### Phase 4-5: 🔮 Future
- 1000+ examples
- LLM re-ranking
- Dashboard & monitoring
- Success rate: >85%

---

## 🔗 External Resources

### Embedding Models
- Jina AI: https://huggingface.co/jinaai/
- Sentence Transformers: https://www.sbert.net/

### Vector Databases
- ChromaDB: https://docs.trychroma.com/
- Vector Search: https://en.wikipedia.org/wiki/Vector_database

### RAG Systems
- LangChain: https://python.langchain.com/
- LLamaIndex: https://gpt-index.readthedocs.io/

---

## ❓ FAQ

**Q: Why did we switch to GPU?**
A: GPU acceleration provides 10-20x faster inference, enabling real-time queries at scale.

**Q: Why 3 collections?**
A: Separating collections allows different thresholds per source quality, improving recall for fallback scenarios.

**Q: What's the difference between 0.65 and 0.55 thresholds?**
A: Curated examples are high-quality (stricter), project code needs lower threshold for more matches.

**Q: When will success rate improve?**
A: After Phase 3 data population (500+ examples) - currently limited by low example count.

**Q: Can I use a different embedding model?**
A: Yes! Update `EMBEDDING_MODEL` in constants.py and re-index. See embedding_model_research.md for options.

---

## 📞 Support

### Issues or Questions?
- Check: PHASE1_GPU_OPTIMIZATION_COMPLETE.md for completed tasks
- Read: PHASE2_ROADMAP.md for next steps
- Review: Relevant phase documentation above

### Reporting Issues
- Document: Exact query and results
- Include: System info (VRAM, GPU, ChromaDB version)
- Attach: Relevant logs from DOCS/rag/

---

## 📜 Version History

| Version | Phase | Date | Status |
|---------|-------|------|--------|
| 0.1 | Phase 1 | Nov 3, 2025 | ✅ Complete |
| 0.2 | Phase 2 | TBD | 📋 Planned |
| 0.5 | Phase 3 | TBD | 📅 Planned |
| 1.0 | Phase 5 | TBD | 🔮 Future |

---

## ⭐ Credits

**RAG Excellence Plan:** Comprehensive multi-phase modernization
**GPU Optimization:** Phase 1 Complete
**Team:** Agentic AI Development Team

**Last Updated:** November 3, 2025
**Next Review:** After Phase 2 Completion

---

[← Back to Project Root](../../README.md)

## 📥 Data Ingestion (How to add data to the RAG)

- **Prereqs**: ChromaDB running (`docker-compose up chromadb -d`), `.env` with `CHROMADB_HOST`/`CHROMADB_PORT`.

- **Option A — Ready-made scripts (recommended)**
  - Curated patterns:
    ```bash
    python scripts/seed_enhanced_patterns.py --category all --batch-size 50
    ```
  - Official docs:
    ```bash
    python scripts/seed_official_docs.py --framework fastapi  # or sqlalchemy/pytest/all
    ```
  - Project code (index your repo):
    ```bash
    python scripts/migrate_existing_code.py --path src --batch-size 50
    ```
  - Orchestrated (runs a sensible sequence):
    ```bash
    python scripts/orchestrate_rag_population.py
    ```

- **Option B — API ingestion**
  - Endpoint: `POST /api/v1/rag/index`
  - Minimal payload:
    ```json
    {
      "code": "def hello():\n    return 'world'\n",
      "metadata": {
        "language": "python",
        "framework": "fastapi",
        "tags": "jwt,security",
        "approved": true
      },
      "collection": "devmatrix_curated"
    }
    ```
  - Notes: use `collection` = `devmatrix_curated` (alta calidad), `devmatrix_project_code`, o `devmatrix_standards`.

- **Option C — Programmatic (Python)**
  ```python
  from src.rag import create_embedding_model
  from src.rag.vector_store import VectorStore

  embeddings = create_embedding_model()
  store = VectorStore(embeddings, collection_name="devmatrix_curated")
  store.add_example(
      code="from fastapi import FastAPI\napp = FastAPI()",
      metadata={
          "language": "python",
          "framework": "fastapi",
          "tags": "jwt,oauth2,bearer",
          "approved": True,
      },
  )
  ```

- **Metadata best practices**
  - Use `language`, `framework`, `tags`, `approved`, `task_type`, `pattern`.
  - Para priorizar en búsquedas: añade `tags` bien específicos (ej.: `jwt, oauth2, bearer`).
  - Filtros permitidos: `language`, `file_path`, `approved`, `tags`, `indexed_at`, `code_length`, `author`, `task_type`, `source`, `framework`, `collection`, `source_collection`.

- **Verificación rápida**
  ```bash
  # Consulta con filtros (usa multi-colección por defecto)
  curl -s http://localhost:8000/api/v1/rag/query \
    -H "Content-Type: application/json" \
    -d '{
      "query": "Implementar JWT con OAuth2PasswordBearer en FastAPI",
      "top_k": 3,
      "strategy": "mmr",
      "filters": {"framework": "fastapi", "tags": "jwt"}
    }' | jq .
  ```

- **Diagnóstico**
  - Si no hay resultados: baja `min_similarity` o quita filtros; confirma que el ejemplo esté en la colección esperada.
  - Revisa stats: `GET /api/v1/rag/metrics` y `MultiCollectionManager.get_collection_stats()`.
