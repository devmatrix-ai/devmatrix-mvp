# RAG System Optimization Guide

Guía completa de optimización y tuning del sistema RAG.

## Tabla de Contenidos

- [Configuración Recomendada](#configuración-recomendada)
- [Trade-offs](#trade-offs)
- [Performance Tuning](#performance-tuning)
- [Quality Tuning](#quality-tuning)
- [Memory Optimization](#memory-optimization)
- [Scaling](#scaling)
- [Best Practices](#best-practices)

## Configuración Recomendada

### Environment Variables Óptimas

```bash
# .env
# Embedding Configuration
RAG_ENABLED=true
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2  # Balance entre velocidad y calidad
RAG_EMBEDDING_DIM=384

# ChromaDB Configuration
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION=devmatrix_code_examples

# Retrieval Configuration
RAG_TOP_K=5                      # 3-10 óptimo para mayoría de casos
RAG_SIMILARITY_THRESHOLD=0.7     # 0.7-0.8 balance entre precisión/recall
RAG_CACHE_ENABLED=true           # Siempre true en producción
RAG_MMR_LAMBDA=0.7               # 0.5-0.8 balance similarity/diversity

# Context Configuration
RAG_CONTEXT_TEMPLATE=detailed    # simple|detailed|structured
RAG_MAX_CONTEXT_LENGTH=8000      # 5000-10000 para Claude/GPT-4
RAG_TRUNCATE_CODE=true
RAG_MAX_CODE_LENGTH=500          # 300-800 para snippets

# Feedback Configuration
RAG_FEEDBACK_ENABLED=true
RAG_AUTO_INDEX_ON_APPROVAL=true  # Learning automático
```

## Trade-offs

### Similarity Threshold

| Valor | Precision | Recall | Uso |
|-------|-----------|--------|-----|
| 0.9+ | Muy alta | Baja | Matching exacto requerido |
| 0.7-0.8 | Alta | Media-Alta | **Recomendado para producción** |
| 0.5-0.7 | Media | Alta | Exploración, desarrollo |
| <0.5 | Baja | Muy Alta | Debugging, investigación |

**Configuración Recomendada**: `0.7`

### Top-K

| Valor | Context Quality | Context Length | Latency | Uso |
|-------|----------------|----------------|---------|-----|
| 1-3 | Muy Alta | Corto | Bajo | Matching específico |
| **3-5** | **Alta** | **Medio** | **Medio** | **Recomendado producción** |
| 5-10 | Media-Alta | Largo | Alto | Más opciones, exploración |
| 10+ | Variable | Muy Largo | Muy Alto | Análisis exhaustivo |

**Configuración Recomendada**: `5`

### Retrieval Strategy

| Strategy | Speed | Diversity | Quality | Uso |
|----------|-------|-----------|---------|-----|
| SIMILARITY | Rápido | Baja | Alta | Matching exacto |
| **MMR** | **Medio** | **Alta** | **Alta** | **Recomendado producción** |
| HYBRID | Lento | Media | Muy Alta | Casos especiales |

**Configuración Recomendada**: `MMR` (Maximal Marginal Relevance)

### Context Template

| Template | Length | Detail | Parse Speed | Uso |
|----------|--------|--------|-------------|-----|
| SIMPLE | Corto | Bajo | Muy Rápido | Snippets simples |
| **DETAILED** | **Medio** | **Alto** | **Rápido** | **Recomendado producción** |
| STRUCTURED | Largo | Muy Alto | Medio | Análisis complejo |

**Configuración Recomendada**: `DETAILED`

### MMR Lambda

| Lambda | Similarity Weight | Diversity Weight | Resultado |
|--------|------------------|------------------|-----------|
| 1.0 | 100% | 0% | Idéntico a SIMILARITY |
| **0.7** | **70%** | **30%** | **Balance recomendado** |
| 0.5 | 50% | 50% | Máxima diversidad práctica |
| 0.0 | 0% | 100% | Solo diversidad (no útil) |

**Configuración Recomendada**: `0.7`

## Performance Tuning

### Embedding Generation

#### Problema: Embedding generation lento
```python
# ❌ Mal: Embeddings individuales
for code in codes:
    embedding = model.embed_text(code)

# ✅ Bien: Batch embeddings
embeddings = model.embed_batch(codes, batch_size=32)
```

**Optimizaciones**:
- Usar `embed_batch()` con `batch_size=32-64`
- Pre-calcular embeddings en background
- Cache embeddings de queries frecuentes

**Performance Expected**:
- Single: ~200-500ms
- Batch 100: ~5000 codes/sec
- Batch 500: ~8000 codes/sec

#### Problema: Modelo tarda en cargar
```python
# ✅ Singleton pattern
from src.rag import create_embedding_model

# Cache global - solo carga una vez
embedding_model = create_embedding_model()
```

### Retrieval Optimization

#### Cache Configuration

```python
from src.rag import create_retriever, RetrievalStrategy

retriever = create_retriever(
    vector_store,
    strategy=RetrievalStrategy.MMR,
    cache_enabled=True,  # ✅ Siempre en producción
)

# Limpiar cache periódicamente si hay memory pressure
if memory_usage > 0.8:
    retriever.clear_cache()
```

**Cache Performance**:
- Cache miss: ~50-200ms
- Cache hit: ~0.1-1ms
- Expected hit rate: >70% en producción

#### Query Optimization

```python
# ❌ Mal: Query muy largo o muy corto
query = "a"  # Demasiado corto
query = entire_file  # Demasiado largo

# ✅ Bien: Query descriptivo pero conciso
query = "function that authenticates user with JWT"
query = code_snippet[:500]  # Si usas código como query
```

### Context Building Optimization

```python
from src.rag import ContextTemplate

# Para respuestas rápidas
config = ContextConfig(
    template=ContextTemplate.SIMPLE,  # Más rápido
    max_code_length=300,  # Snippets cortos
    truncate_code=True
)

# Para calidad máxima
config = ContextConfig(
    template=ContextTemplate.DETAILED,  # Balance
    max_code_length=500,
    include_metadata=True
)
```

**Performance Expected**:
- SIMPLE: <1ms
- DETAILED: <5ms
- STRUCTURED: <10ms

## Quality Tuning

### Improving Retrieval Quality

#### 1. Threshold Tuning

```python
# Análisis de similarity scores
results = retriever.retrieve("query")
for r in results:
    print(f"Similarity: {r.similarity:.3f} - {r.code[:50]}")

# Si scores típicos son 0.85+, subir threshold
RAG_SIMILARITY_THRESHOLD=0.8

# Si scores típicos son 0.65+, mantener threshold
RAG_SIMILARITY_THRESHOLD=0.7
```

#### 2. Metadata Enrichment

```python
# ❌ Mal: Metadata mínima
vector_store.add_example(
    code=code,
    metadata={"language": "python"}
)

# ✅ Bien: Metadata rica
vector_store.add_example(
    code=code,
    metadata={
        "language": "python",
        "project_id": "auth-service",
        "task_type": "authentication",
        "approved": True,
        "complexity": "medium",
        "patterns": ["jwt", "oauth", "rest"],
        "file_path": "src/auth.py"
    }
)
```

#### 3. Feedback Loop Optimization

```python
from src.rag import create_feedback_service

feedback = create_feedback_service(
    vector_store,
    enabled=True,
    auto_index_on_approval=True  # ✅ Aprendizaje automático
)

# Registrar approvals
feedback.record_approval(
    code=generated_code,
    metadata=enriched_metadata,
    task_description=task
)
```

### Diversity Tuning

```python
# Para resultados más diversos
retriever = create_retriever(
    vector_store,
    strategy=RetrievalStrategy.MMR,
    mmr_lambda=0.5  # Más diversidad
)

# Para resultados más similares
retriever = create_retriever(
    vector_store,
    strategy=RetrievalStrategy.MMR,
    mmr_lambda=0.8  # Más similarity
)
```

## Memory Optimization

### Vector Store Size Management

```python
# Monitorear tamaño
stats = vector_store.get_stats()
print(f"Examples: {stats['total_examples']}")
print(f"Size: {stats.get('collection_size_mb', 0)} MB")

# Si crece demasiado, considerar:
# 1. Partitioning por proyecto
vector_store_auth = create_vector_store(
    embedding_model,
    collection_name="project_auth"
)

# 2. Cleanup de ejemplos viejos/no usados
# (requiere implementación custom)

# 3. Aumentar similarity threshold
RAG_SIMILARITY_THRESHOLD=0.8  # Menos ejemplos indexados
```

### Embedding Cache

```python
# Cache de embeddings de queries comunes
query_cache = {}

def cached_retrieve(query):
    if query in query_cache:
        return query_cache[query]

    results = retriever.retrieve(query)
    query_cache[query] = results
    return results
```

### Context Length Management

```python
# Monitorear context length
context = context_builder.build_context(query, results)
print(f"Context length: {len(context)} chars")

# Si contexto muy largo:
config = ContextConfig(
    max_context_length=6000,  # Reducir
    truncate_code=True,
    max_code_length=300  # Snippets más cortos
)
```

## Scaling

### Horizontal Scaling

#### ChromaDB Clustering

```yaml
# docker-compose.yml
services:
  chromadb-1:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"

  chromadb-2:
    image: chromadb/chroma:latest
    ports:
      - "8002:8000"

  chromadb-3:
    image: chromadb/chroma:latest
    ports:
      - "8003:8000"
```

```python
# Load balancing simple
import random

CHROMADB_HOSTS = ["localhost:8001", "localhost:8002", "localhost:8003"]

def get_vector_store():
    host = random.choice(CHROMADB_HOSTS)
    return create_vector_store(
        embedding_model,
        host=host.split(":")[0],
        port=int(host.split(":")[1])
    )
```

#### Project-based Sharding

```python
# Diferentes collections por proyecto
def get_project_vector_store(project_id):
    return create_vector_store(
        embedding_model,
        collection_name=f"project_{project_id}"
    )

# Retrieval multi-store
def multi_store_retrieve(query, project_ids):
    all_results = []
    for pid in project_ids:
        store = get_project_vector_store(pid)
        retriever = create_retriever(store)
        results = retriever.retrieve(query)
        all_results.extend(results)

    # Re-rank combinados
    all_results.sort(key=lambda x: x.similarity, reverse=True)
    return all_results[:5]
```

### Vertical Scaling

**CPU Optimization**:
- Embeddings: CPU-bound (considerar multi-threading)
- MMR: CPU-intensive (considerar numpy optimization)

**Memory Optimization**:
- ChromaDB: ~100MB per 1000 examples
- Embeddings cache: ~3KB per embedding
- Query cache: Variable por complexity

**Disk Optimization**:
- ChromaDB persiste en disco
- SSD recomendado para high-throughput
- Backup periódico de colecciones

## Best Practices

### Development

```python
# 1. Usar mocks en tests
from unittest.mock import Mock

mock_vector_store = Mock()
mock_vector_store.search_with_metadata.return_value = mock_results

# 2. Testing con datasets pequeños
test_vector_store = create_vector_store(
    embedding_model,
    collection_name="test_small"
)

# 3. Logging comprehensivo
from src.observability import get_logger

logger = get_logger("my_rag_integration")
logger.info("Retrieval", query=query, results=len(results))
```

### Production

```python
# 1. Health checks
is_healthy, message = vector_store.health_check()
if not is_healthy:
    alert_ops(f"Vector store unhealthy: {message}")

# 2. Metrics collection
from src.rag.metrics import get_rag_metrics_tracker

metrics = get_rag_metrics_tracker()
metrics.record_retrieval(duration, results_count, strategy, top_k, cache_hit)

# 3. Error handling
try:
    results = retriever.retrieve(query)
except Exception as e:
    logger.error("Retrieval failed", error=str(e))
    metrics.record_retrieval_error(strategy, type(e).__name__)
    # Fallback sin RAG
    results = []
```

### Monitoring

```python
# Periodic health check
import schedule

def check_rag_health():
    metrics = get_rag_metrics_tracker()
    summary = metrics.get_summary()

    # Alert si problemas
    if summary.get("cache_hit_rate", 0) < 0.5:
        alert("Low cache hit rate")

    if summary.get("retrieval_avg_duration_ms", 0) > 500:
        alert("High retrieval latency")

schedule.every(5).minutes.do(check_rag_health)
```

## Configuration Profiles

### Profile: Development (Fast Iteration)
```bash
RAG_ENABLED=true
RAG_TOP_K=3
RAG_SIMILARITY_THRESHOLD=0.6
RAG_CACHE_ENABLED=false
RAG_CONTEXT_TEMPLATE=simple
RAG_MAX_CODE_LENGTH=300
```

### Profile: Production (Quality)
```bash
RAG_ENABLED=true
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CACHE_ENABLED=true
RAG_CONTEXT_TEMPLATE=detailed
RAG_MAX_CODE_LENGTH=500
RAG_FEEDBACK_ENABLED=true
RAG_AUTO_INDEX_ON_APPROVAL=true
```

### Profile: High-Throughput
```bash
RAG_ENABLED=true
RAG_TOP_K=3
RAG_SIMILARITY_THRESHOLD=0.75
RAG_CACHE_ENABLED=true
RAG_CONTEXT_TEMPLATE=simple
RAG_MAX_CODE_LENGTH=300
RAG_MMR_LAMBDA=0.8  # Menos computation de diversity
```

### Profile: Maximum Quality
```bash
RAG_ENABLED=true
RAG_TOP_K=10
RAG_SIMILARITY_THRESHOLD=0.65
RAG_CACHE_ENABLED=true
RAG_CONTEXT_TEMPLATE=structured
RAG_MAX_CODE_LENGTH=800
RAG_MMR_LAMBDA=0.5  # Máxima diversidad
RAG_FEEDBACK_ENABLED=true
```

## Performance Benchmarks

### Expected Performance (Production Hardware)

| Operation | Target | Acceptable | Alert |
|-----------|--------|------------|-------|
| Single embedding | <200ms | <500ms | >1s |
| Batch 100 embeddings | <50ms | <100ms | >200ms |
| Retrieval (cached) | <1ms | <5ms | >10ms |
| Retrieval (cache miss) | <50ms | <200ms | >500ms |
| MMR retrieval | <100ms | <300ms | >1s |
| Context building | <5ms | <20ms | >50ms |
| Full pipeline | <100ms | <300ms | >1s |

### Scaling Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Cache hit rate | >70% | En producción estable |
| Vector store examples | <100K | Por collection |
| Concurrent retrievals | >100/sec | Con cache |
| Embedding throughput | >5000/sec | Batch mode |

---

**Última actualización**: FASE 9 - Optimización y Tuning (2025)
