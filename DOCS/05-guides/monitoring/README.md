# DevMatrix Monitoring & Observability Guide

Guía completa del sistema de observabilidad DevOps/App con Prometheus y Grafana.

## 📊 Resumen del Sistema

**Stack de Observabilidad:**
- **Prometheus**: Recolección y almacenamiento de métricas
- **Grafana**: Visualización y dashboards
- **Postgres Exporter**: Métricas de PostgreSQL
- **Redis Exporter**: Métricas de Redis
- **Instrumentación Custom**: API, WebSocket, LLM, RAG

## 🚀 Inicio Rápido

### Activar Monitoring

```bash
# Iniciar stack completo de monitoring
docker compose --profile monitoring up -d

# Verificar que todos los servicios estén healthy
docker compose ps

# Ver logs en tiempo real
docker compose logs -f prometheus grafana
```

### URLs de Acceso

- **Grafana**: http://localhost:3001
  - Usuario: `admin`
  - Password: `admin` (cambialo en .env con `GRAFANA_ADMIN_PASSWORD`)

- **Prometheus**: http://localhost:9090
  - Interfaz web para queries y alertas

- **API Metrics Endpoint**: http://localhost:8000/api/v1/metrics
  - Formato Prometheus exposition

## 📈 Dashboards de Grafana

### Dashboard 1: System + API Overview

**Ubicación**: `1-system-api-overview.json`

**Métricas Clave:**
- **HTTP API**:
  - Request rate por endpoint/método/status
  - Response time (p95/p50)
  - Error rate (4xx/5xx)
  - Requests in progress

- **WebSocket**:
  - Conexiones activas
  - Message rate (sent/received)
  - Errores por tipo
  - Message processing time

- **Workspace**:
  - Operaciones de archivo (write_file, read_file)
  - Success/failure rate

**Panels**: 13 paneles organizados en 4 filas

### Dashboard 2: LLM & RAG Performance

**Ubicación**: `2-llm-rag-performance.json`

**Métricas Clave:**
- **LLM (Anthropic)**:
  - Request rate por modelo
  - Request latency (cached vs no-cached)
  - Cache hit rate
  - Token usage (input/output)
  - Cost EUR/hour
  - Errores por tipo

- **RAG System**:
  - Retrieval latency por estrategia
  - Cache hit rate
  - Embedding generation rate
  - Indexing performance
  - Vector store size
  - Similarity scores distribution
  - Context building time

**Panels**: 14 paneles organizados en 4 filas

### Dashboard 3: Databases (PostgreSQL & Redis)

**Ubicación**: `3-databases.json`

**Métricas Clave:**
- **PostgreSQL**:
  - Active connections
  - Transaction rate (commits/rollbacks)
  - Database size
  - Tuple operations (inserts/updates/deletes/fetches)
  - Cache hit ratio
  - Query duration

- **Redis**:
  - Connected clients
  - Memory usage
  - Commands/sec
  - Keyspace hit rate
  - Total keys
  - Evicted keys
  - Operations by command

**Panels**: 13 paneles organizados en 4 filas

## 🔔 Alertas Configuradas

**Ubicación**: `docker/prometheus/alerts.yml`

### API Alerts

| Alert | Threshold | Severity | Description |
|-------|-----------|----------|-------------|
| HighAPIErrorRate | >1% for 5min | Critical | Server errors exceden 1% |
| HighAPILatency | >2s for 5min | Warning | p95 latency > 2 segundos |
| APIServiceDown | Down for 1min | Critical | API no responde |

### WebSocket Alerts

| Alert | Threshold | Severity | Description |
|-------|-----------|----------|-------------|
| HighWebSocketErrors | >5 errors/s for 5min | Warning | Tasa de errores alta |
| NoActiveWebSocketConnections | 0 for 10min | Info | Sin conexiones activas |

### LLM Alerts

| Alert | Threshold | Severity | Description |
|-------|-----------|----------|-------------|
| HighLLMErrorRate | >5% for 5min | Critical | Errores LLM exceden 5% |
| LowLLMCacheHitRate | <30% for 10min | Info | Cache poco efectivo |
| HighLLMCost | >€10/hour | Warning | Costos altos de API |

### Database Alerts

| Alert | Threshold | Severity | Description |
|-------|-----------|----------|-------------|
| HighPostgreSQLConnections | >50 for 5min | Warning | Demasiadas conexiones |
| LowPostgreSQLCacheHitRatio | <90% for 10min | Warning | Cache ratio bajo |
| PostgreSQLDown | Down for 1min | Critical | PostgreSQL no responde |
| HighRedisMemoryUsage | >80% for 5min | Warning | Memoria Redis alta |
| RedisDown | Down for 1min | Critical | Redis no responde |
| HighRedisEvictionRate | >100 keys/s for 5min | Warning | Eviction rate alto |

### RAG Alerts

| Alert | Threshold | Severity | Description |
|-------|-----------|----------|-------------|
| HighRAGRetrievalLatency | >1s for 5min | Warning | Retrieval lento |
| LowRAGCacheHitRate | <50% for 10min | Info | Cache RAG poco efectivo |

## 📊 Métricas Instrumentadas

### HTTP Metrics (Middleware FastAPI)

**Archivo**: `src/observability/middleware.py`

```
http_requests_total{method,endpoint,status}          # Counter
http_request_duration_seconds{method,endpoint}       # Histogram
http_errors_total{method,endpoint,status,error_type} # Counter
http_requests_in_progress                            # Gauge
```

### WebSocket Metrics

**Archivo**: `src/api/routers/websocket.py`

```
websocket_connections_total{type}                    # Counter (connect/disconnect)
websocket_connections_active                         # Gauge
websocket_messages_total{event,direction}            # Counter (sent/received)
websocket_message_duration_seconds{event}            # Histogram
websocket_errors_total{event,error_type}             # Counter
websocket_workspace_operations_total{operation,result} # Counter
```

### LLM Metrics (AnthropicClient)

**Archivo**: `src/llm/anthropic_client.py`

```
llm_requests_total{model,status}                     # Counter (success/error)
llm_request_duration_seconds{model,cached}           # Histogram
llm_tokens_total{model,type}                         # Counter (input/output)
llm_cache_hits_total{model}                          # Counter
llm_cache_misses_total{model}                        # Counter
llm_cost_eur{model}                                  # Histogram
llm_errors_total{model,error_type}                   # Counter
```

### RAG Metrics (Existentes)

**Archivo**: `src/rag/metrics.py`

```
# Embeddings
rag_embedding_duration_seconds{dimension}            # Histogram
rag_embeddings_generated_total{dimension}            # Counter
rag_embedding_generation_rate{dimension}             # Gauge

# Retrieval
rag_retrieval_duration_seconds{strategy}             # Histogram
rag_retrievals_total{strategy}                       # Counter
rag_retrieval_results_count{strategy}                # Histogram
rag_retrieval_cache_hits_total{strategy}             # Counter
rag_retrieval_cache_misses_total{strategy}           # Counter
rag_retrieval_errors_total{strategy,error_type}      # Counter

# Context Building
rag_context_build_duration_seconds{template}         # Histogram
rag_context_builds_total{template}                   # Counter
rag_context_length_chars{template}                   # Histogram
rag_context_truncations_total{template}              # Counter

# Indexing
rag_indexing_duration_seconds{batch}                 # Histogram
rag_examples_indexed_total{batch}                    # Counter
rag_indexing_rate{batch}                             # Gauge

# Vector Store
rag_vector_store_examples_total                      # Gauge
rag_vector_store_size_mb                             # Gauge

# Quality
rag_similarity_scores{strategy}                      # Histogram
rag_mmr_scores                                       # Histogram
rag_component_health{component}                      # Gauge (1=healthy, 0=unhealthy)
```

## 🛠️ Configuración de Prometheus

**Archivo**: `docker/prometheus/prometheus.yml`

### Scrape Targets

```yaml
scrape_configs:
  - job_name: 'prometheus'          # Self-monitoring
    targets: ['localhost:9090']

  - job_name: 'devmatrix-api'       # FastAPI app
    metrics_path: '/api/v1/metrics'
    targets: ['api:8000']

  - job_name: 'postgres'            # PostgreSQL exporter
    targets: ['postgres-exporter:9187']

  - job_name: 'redis'               # Redis exporter
    targets: ['redis-exporter:9121']

  - job_name: 'chromadb'            # ChromaDB (si expone métricas)
    targets: ['chromadb:8000']
```

### Configuración de Scraping

- **Scrape interval**: 15 segundos (global)
- **Evaluation interval**: 15 segundos (alertas)
- **API scrape interval**: 10 segundos (más frecuente)

## 📦 Exporters

### PostgreSQL Exporter

**Imagen**: `prometheuscommunity/postgres-exporter:latest`
**Puerto**: 9187
**Métricas**: ~100+ métricas de PostgreSQL
**Documentación**: https://github.com/prometheus-community/postgres_exporter

**Métricas Principales**:
- `pg_stat_database_*`: Stats de bases de datos
- `pg_stat_activity_*`: Conexiones activas
- `pg_database_size_bytes`: Tamaño de DB
- `pg_stat_statements_*`: Query performance

### Redis Exporter

**Imagen**: `oliver006/redis_exporter:latest`
**Puerto**: 9121
**Métricas**: ~50+ métricas de Redis
**Documentación**: https://github.com/oliver006/redis_exporter

**Métricas Principales**:
- `redis_connected_clients`: Clientes conectados
- `redis_memory_used_bytes`: Uso de memoria
- `redis_commands_processed_total`: Comandos procesados
- `redis_keyspace_hits/misses_total`: Cache hit/miss

## 🔍 Queries Útiles de Prometheus

### API Performance

```promql
# Request rate por endpoint
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate percentage
sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) * 100

# Top 10 endpoints más lentos
topk(10, histogram_quantile(0.95, sum by (endpoint) (rate(http_request_duration_seconds_bucket[5m]))))
```

### LLM Costs

```promql
# Costo total por hora
sum(rate(llm_cost_eur_sum[1h])) * 3600

# Tokens por segundo
rate(llm_tokens_total[5m])

# Cache hit rate
sum(rate(llm_cache_hits_total[5m])) / (sum(rate(llm_cache_hits_total[5m])) + sum(rate(llm_cache_misses_total[5m]))) * 100
```

### Database Health

```promql
# PostgreSQL conexiones activas
pg_stat_database_numbackends{datname="devmatrix"}

# Redis memory usage percentage
redis_memory_used_bytes / redis_memory_max_bytes * 100

# PostgreSQL cache hit ratio
pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read) * 100
```

## 🧪 Testing & Validación

### Verificar Métricas

```bash
# Verificar que el endpoint de métricas funciona
curl http://localhost:8000/api/v1/metrics

# Verificar que Prometheus scrape funciona
curl http://localhost:9090/api/v1/targets

# Verificar alertas configuradas
curl http://localhost:9090/api/v1/rules
```

### Generar Tráfico de Prueba

```bash
# Generar requests HTTP
for i in {1..100}; do curl http://localhost:8000/api/v1/health/live; done

# Verificar métricas en Grafana
# Abrir http://localhost:3001 y explorar dashboards
```

## 📝 Troubleshooting

### Prometheus No Scrape Métricas

1. Verificar que el servicio esté up:
   ```bash
   docker compose ps prometheus
   ```

2. Ver logs:
   ```bash
   docker compose logs prometheus
   ```

3. Verificar targets en Prometheus UI:
   ```
   http://localhost:9090/targets
   ```

### Grafana No Muestra Datos

1. Verificar data source de Prometheus:
   - Ir a Configuration > Data Sources
   - Verificar URL: `http://prometheus:9090`
   - Test connection

2. Verificar queries en paneles:
   - Editar panel
   - Ver errores en query inspector

### Exporters No Funcionan

```bash
# PostgreSQL exporter
docker compose logs postgres-exporter

# Redis exporter
docker compose logs redis-exporter

# Verificar conectividad
docker compose exec postgres-exporter wget -O- http://localhost:9187/metrics
docker compose exec redis-exporter wget -O- http://localhost:9121/metrics
```

## 🔧 Configuración Avanzada

### Retention de Métricas

Editar `docker-compose.yml`:

```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # Retener 30 días
    - '--storage.tsdb.retention.size=10GB' # Máximo 10GB
```

### Configurar Alertmanager

1. Agregar servicio en `docker-compose.yml`:

```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  volumes:
    - ./docker/prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

2. Configurar notificaciones en `alertmanager.yml`

## 📖 Referencias

- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/
- **PostgreSQL Exporter**: https://github.com/prometheus-community/postgres_exporter
- **Redis Exporter**: https://github.com/oliver006/redis_exporter
- **PromQL**: https://prometheus.io/docs/prometheus/latest/querying/basics/

## 🎯 Next Steps

1. **Configurar Alertmanager** para notificaciones (Slack, Email, PagerDuty)
2. **Agregar más dashboards** personalizados por equipo
3. **Configurar retention policies** según necesidades de storage
4. **Implementar distributed tracing** con Jaeger/Tempo
5. **Agregar logs centralizados** con Loki/ELK
