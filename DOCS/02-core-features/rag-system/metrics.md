# RAG System Metrics

Documentación de métricas disponibles para monitoreo del sistema RAG.

## Overview

El sistema RAG expone métricas en formato Prometheus para monitorear:
- Performance de embeddings
- Latencia de retrieval
- Cache hit rates
- Feedback loop
- Operaciones de vector store

## Uso Básico

```python
from src.rag.metrics import get_rag_metrics_tracker

# Obtener tracker global
metrics = get_rag_metrics_tracker()

# Registrar métricas
metrics.record_embedding_generation(duration=0.5, count=100)
metrics.record_retrieval(duration=0.1, results_count=5, strategy="mmr")

# Exportar para Prometheus
prometheus_metrics = metrics.export_prometheus()

# Obtener resumen
summary = metrics.get_summary()
print(f"Cache hit rate: {summary['cache_hit_rate']:.2%}")
```

## Métricas Disponibles

### Embedding Metrics

#### `rag_embedding_duration_seconds` (histogram)
- **Descripción**: Tiempo para generar embeddings
- **Labels**: `dimension` (384)
- **Uso**: Detectar degradación de performance en embedding generation

#### `rag_embeddings_generated_total` (counter)
- **Descripción**: Total de embeddings generados
- **Labels**: `dimension`
- **Uso**: Monitorear volumen de embeddings

#### `rag_embedding_generation_rate` (gauge)
- **Descripción**: Embeddings por segundo
- **Labels**: `dimension`
- **Uso**: Monitorear throughput de embedding generation

**Ejemplo**:
```python
metrics.record_embedding_generation(
    duration=0.02,  # 20ms
    count=100,
    dimension=384
)
```

### Retrieval Metrics

#### `rag_retrieval_duration_seconds` (histogram)
- **Descripción**: Tiempo de retrieval
- **Labels**: `strategy` (similarity, mmr, hybrid)
- **Uso**: Identificar queries lentos

#### `rag_retrievals_total` (counter)
- **Descripción**: Total de retrievals ejecutados
- **Labels**: `strategy`
- **Uso**: Monitorear uso del sistema

#### `rag_retrieval_results_count` (histogram)
- **Descripción**: Número de resultados retornados
- **Labels**: `strategy`
- **Uso**: Analizar calidad de resultados

#### `rag_retrieval_cache_hits_total` (counter)
- **Descripción**: Cache hits
- **Labels**: `strategy`
- **Uso**: Calcular cache hit rate

#### `rag_retrieval_cache_misses_total` (counter)
- **Descripción**: Cache misses
- **Labels**: `strategy`
- **Uso**: Calcular cache hit rate

#### `rag_retrieval_errors_total` (counter)
- **Descripción**: Errores de retrieval
- **Labels**: `strategy`, `error_type`
- **Uso**: Monitorear salud del sistema

**Ejemplo**:
```python
metrics.record_retrieval(
    duration=0.1,
    results_count=5,
    strategy="mmr",
    top_k=5,
    cache_hit=False
)
```

### Context Building Metrics

#### `rag_context_build_duration_seconds` (histogram)
- **Descripción**: Tiempo de construcción de contexto
- **Labels**: `template` (simple, detailed, structured)
- **Uso**: Optimizar performance de templates

#### `rag_context_builds_total` (counter)
- **Descripción**: Total de contextos construidos
- **Labels**: `template`
- **Uso**: Monitorear uso de templates

#### `rag_context_length_chars` (histogram)
- **Descripción**: Longitud del contexto en caracteres
- **Labels**: `template`
- **Uso**: Analizar tamaños de contexto

#### `rag_context_truncations_total` (counter)
- **Descripción**: Contextos truncados
- **Labels**: `template`
- **Uso**: Detectar configuraciones sub-óptimas

**Ejemplo**:
```python
metrics.record_context_building(
    duration=0.001,
    results_count=5,
    context_length=2500,
    template="detailed",
    truncated=False
)
```

### Vector Store Metrics

#### `rag_indexing_duration_seconds` (histogram)
- **Descripción**: Tiempo de indexado
- **Labels**: `batch` (true, false)
- **Uso**: Optimizar operaciones de indexado

#### `rag_examples_indexed_total` (counter)
- **Descripción**: Total de ejemplos indexados
- **Labels**: `batch`
- **Uso**: Monitorear crecimiento del vector store

#### `rag_indexing_rate` (gauge)
- **Descripción**: Ejemplos indexados por segundo
- **Labels**: `batch`
- **Uso**: Monitorear throughput de indexado

#### `rag_vector_store_examples_total` (gauge)
- **Descripción**: Total de ejemplos en el vector store
- **Sin labels**
- **Uso**: Monitorear tamaño del store

#### `rag_vector_store_size_mb` (gauge)
- **Descripción**: Tamaño del vector store en MB
- **Sin labels**
- **Uso**: Monitorear uso de almacenamiento

**Ejemplo**:
```python
metrics.record_indexing(duration=0.5, count=50, batch=True)
metrics.update_vector_store_stats(total_examples=1000, collection_size_mb=125.5)
```

### Feedback Loop Metrics

#### `rag_feedback_events_total` (counter)
- **Descripción**: Total de eventos de feedback
- **Labels**: `type` (approval, rejection, etc.)
- **Uso**: Monitorear feedback loop

#### `rag_auto_indexed_total` (counter)
- **Descripción**: Ejemplos auto-indexados desde feedback
- **Sin labels**
- **Uso**: Monitorear learning automático

**Ejemplo**:
```python
metrics.record_feedback(feedback_type="approval", auto_indexed=True)
```

### Quality Metrics

#### `rag_similarity_scores` (histogram)
- **Descripción**: Distribución de similarity scores
- **Labels**: `strategy`
- **Uso**: Analizar calidad de retrieval

#### `rag_mmr_scores` (histogram)
- **Descripción**: Distribución de MMR scores
- **Sin labels**
- **Uso**: Analizar diversidad de resultados

**Ejemplo**:
```python
metrics.record_similarity_score(score=0.85, strategy="mmr")
metrics.record_mmr_score(score=0.72)
```

### Health Metrics

#### `rag_component_health` (gauge)
- **Descripción**: Estado de salud de componentes (1=healthy, 0=unhealthy)
- **Labels**: `component` (embeddings, vector_store, retriever, etc.)
- **Uso**: Alertas de disponibilidad

**Ejemplo**:
```python
metrics.set_health_status(component="vector_store", healthy=True)
```

## Queries Prometheus Útiles

### Cache Hit Rate
```promql
sum(rate(rag_retrieval_cache_hits_total[5m])) /
sum(rate(rag_retrieval_cache_hits_total[5m]) + rate(rag_retrieval_cache_misses_total[5m]))
```

### Latencia p95 de Retrieval
```promql
histogram_quantile(0.95,
  sum(rate(rag_retrieval_duration_seconds_bucket[5m])) by (le, strategy)
)
```

### Throughput de Embeddings
```promql
sum(rate(rag_embeddings_generated_total[5m])) by (dimension)
```

### Tasa de Errores
```promql
sum(rate(rag_retrieval_errors_total[5m])) by (strategy, error_type)
```

### Uso de Estrategias
```promql
sum(rate(rag_retrievals_total[5m])) by (strategy)
```

## Dashboard Grafana

### Panel 1: Performance Overview
- Cache hit rate (gauge)
- Retrieval p50/p95/p99 latency (graph)
- Embedding generation rate (graph)
- Context build duration (graph)

### Panel 2: Volume Metrics
- Retrievals per second by strategy (stacked graph)
- Embeddings generated per second (graph)
- Examples indexed per second (graph)
- Vector store total examples (gauge)

### Panel 3: Quality Metrics
- Similarity score distribution (heatmap)
- Results count distribution (histogram)
- Context length distribution (histogram)
- Truncation rate (gauge)

### Panel 4: Health
- Component health status (status panel)
- Error rate by type (graph)
- Feedback events rate (graph)
- Auto-indexed rate (gauge)

## Alertas Recomendadas

### High Latency
```yaml
alert: RAGHighRetrievalLatency
expr: histogram_quantile(0.95, rag_retrieval_duration_seconds_bucket) > 1.0
for: 5m
annotations:
  summary: "RAG retrieval p95 latency > 1s"
```

### Low Cache Hit Rate
```yaml
alert: RAGLowCacheHitRate
expr: rate(rag_retrieval_cache_hits_total[5m]) /
      (rate(rag_retrieval_cache_hits_total[5m]) + rate(rag_retrieval_cache_misses_total[5m])) < 0.3
for: 10m
annotations:
  summary: "RAG cache hit rate < 30%"
```

### Component Unhealthy
```yaml
alert: RAGComponentUnhealthy
expr: rag_component_health == 0
for: 2m
annotations:
  summary: "RAG component {{ $labels.component }} is unhealthy"
```

### High Error Rate
```yaml
alert: RAGHighErrorRate
expr: rate(rag_retrieval_errors_total[5m]) > 0.05
for: 5m
annotations:
  summary: "RAG error rate > 5%"
```

## Integración

### Endpoint Prometheus

Exponer métricas en `/metrics`:

```python
from flask import Flask, Response
from src.rag.metrics import get_rag_metrics_tracker

app = Flask(__name__)
metrics = get_rag_metrics_tracker()

@app.route('/metrics')
def prometheus_metrics():
    return Response(
        metrics.export_prometheus(),
        mimetype='text/plain; version=0.0.4'
    )
```

### Scrape Config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rag-system'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:5000']
```

## Performance Baselines

Valores típicos para referencia:

- **Embedding generation**: ~5000 codes/sec (batch)
- **Single embedding**: <500ms
- **Retrieval (similarity)**: <100ms
- **Retrieval (MMR)**: <500ms
- **Context building**: <10ms
- **Cache hit rate**: >70% en producción

## Troubleshooting

### Métricas no aparecen
1. Verificar que `get_rag_metrics_tracker()` se llama
2. Confirmar que componentes registran métricas
3. Verificar endpoint `/metrics` accesible

### Cache hit rate bajo
1. Revisar TTL de cache
2. Analizar diversidad de queries
3. Considerar aumentar cache size

### High latency
1. Revisar tamaño de vector store
2. Optimizar configuración de ChromaDB
3. Considerar sharding para stores grandes

---

**Última actualización**: FASE 8 - Monitoring y Métricas (2025)
