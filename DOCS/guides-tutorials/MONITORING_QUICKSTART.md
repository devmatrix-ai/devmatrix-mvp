# Monitoring QuickStart

## 🚀 Comandos Rápidos

### Levantar Monitoring
```bash
docker compose --profile monitoring up -d
```

### Ver Estado
```bash
docker compose ps
```

### Ver Logs
```bash
docker compose logs -f prometheus grafana
docker compose logs -f postgres-exporter redis-exporter
```

### Restart Prometheus (si cambias config)
```bash
docker compose restart prometheus
```

## 🌐 URLs de Acceso

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **API Metrics** | http://localhost:8000/api/v1/metrics | - |
| **Postgres Exporter** | http://localhost:9187/metrics | - |
| **Redis Exporter** | http://localhost:9121/metrics | - |

## 📊 Dashboards de Grafana

1. **System + API Overview** - HTTP, WebSocket, Workspace
2. **LLM & RAG Performance** - Anthropic, tokens, RAG metrics
3. **Databases** - PostgreSQL, Redis

## 🔍 Verificación Rápida

```bash
# Verificar targets de Prometheus
curl -s http://localhost:9090/api/v1/targets | python3 -c "import sys, json; data = json.load(sys.stdin); [print(f\"{t['labels']['job']:20} → {t['health']}\") for t in data['data']['activeTargets']]"

# Ver métricas de API
curl http://localhost:8000/api/v1/metrics | head -30

# Ver métricas de PostgreSQL
curl http://localhost:9187/metrics | grep pg_stat_database_numbackends

# Ver métricas de Redis
curl http://localhost:9121/metrics | grep redis_connected_clients
```

## 🎯 Generar Tráfico para Testing

```bash
# Generar requests HTTP
for i in {1..100}; do curl http://localhost:8000/api/v1/health/live; done

# Usar la UI para generar WebSocket traffic
open http://localhost:3000
```

## 📈 Queries Útiles de Prometheus

### API Performance
```promql
# Request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate %
sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) * 100
```

### LLM Metrics
```promql
# LLM request rate
rate(llm_requests_total[5m])

# Cost per hour
sum(rate(llm_cost_eur_sum[1h])) * 3600

# Cache hit rate
sum(rate(llm_cache_hits_total[5m])) / (sum(rate(llm_cache_hits_total[5m])) + sum(rate(llm_cache_misses_total[5m]))) * 100
```

### Database Health
```promql
# PostgreSQL connections
pg_stat_database_numbackends{datname="devmatrix"}

# Redis memory usage %
redis_memory_used_bytes / redis_memory_max_bytes * 100

# PostgreSQL cache hit ratio
pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read) * 100
```

## 🔧 Troubleshooting

### Prometheus no scrape targets
```bash
# Ver logs de Prometheus
docker compose logs prometheus

# Verificar config
docker compose exec prometheus cat /etc/prometheus/prometheus.yml

# Restart
docker compose restart prometheus
```

### Grafana no muestra datos
```bash
# Verificar data source
# → Ir a Configuration > Data Sources en Grafana
# → URL debe ser: http://prometheus:9090

# Test connection en Grafana UI
```

### Exporters no funcionan
```bash
# Ver logs
docker compose logs postgres-exporter
docker compose logs redis-exporter

# Verificar conectividad
docker compose exec postgres-exporter wget -O- http://localhost:9187/metrics
docker compose exec redis-exporter wget -O- http://localhost:9121/metrics
```

## 📖 Documentación Completa

Ver `DOCS/MONITORING_GUIDE.md` para:
- Lista completa de métricas instrumentadas
- Configuración detallada de alertas
- Queries avanzadas de Prometheus
- Configuración de Alertmanager
- Referencias y links útiles
