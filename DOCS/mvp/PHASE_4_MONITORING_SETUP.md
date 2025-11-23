# Phase 4: Monitoring & Observability Setup

**Status**: 🔄 **IN PROGRESS**
**Updated**: 2025-11-23
**Goal**: Configure Prometheus + Grafana for production monitoring

---

## 1. Prometheus Metrics Collection

### 1.1 Core Metrics Framework

Prometheus collects time-series metrics from your application. Generated apps include automatic instrumentation for:

**HTTP Request Metrics:**
- `http_requests_total` - Total requests by endpoint
- `http_request_duration_seconds` - Response time distribution (histogram)
- `http_request_size_bytes` - Request payload size
- `http_response_size_bytes` - Response payload size
- `http_errors_total` - Error count by status code

**Database Metrics:**
- `db_query_count_total` - Total queries by type
- `db_query_duration_seconds` - Query execution time
- `db_connection_pool_size` - Active connections
- `db_connection_wait_seconds` - Time waiting for connection

**Business Logic Metrics:**
- `validation_failures_total` - Validation errors by type
- `workflow_transitions_total` - State machine transitions
- `business_rule_violations_total` - Business logic constraint violations

**System Metrics:**
- `python_process_resident_memory_bytes` - Memory usage
- `python_process_cpu_seconds_total` - CPU usage
- `python_gc_collections_total` - Garbage collection events

### 1.2 Instrumentation in Generated Apps

Generated services automatically include Prometheus instrumentation:

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics objects (defined in service)
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['endpoint'])
db_query_count = Counter('db_queries_total', 'Total database queries', ['operation'])
validation_failures = Counter('validation_failures_total', 'Validation failures', ['entity', 'field'])

# Automatic instrumentation in route handlers
@router.post('/customers')
async def create_customer(data: CustomerCreate, db: AsyncSession):
    start = time.time()
    request_count.labels(method='POST', endpoint='create_customer').inc()

    try:
        # Business logic...
        pass
    except ValidationError as e:
        validation_failures.labels(entity='Customer', field=str(e)).inc()
        raise
    finally:
        duration = time.time() - start
        request_duration.labels(endpoint='create_customer').observe(duration)
```

### 1.3 Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:5432']
```

### 1.4 Key Metrics Queries

**Request Rate (requests per second):**
```
rate(http_requests_total[5m])
```

**Error Rate (percentage):**
```
rate(http_errors_total[5m]) / rate(http_requests_total[5m])
```

**P95 Response Time:**
```
histogram_quantile(0.95, http_request_duration_seconds_bucket)
```

**Database Query Performance:**
```
rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m])
```

---

## 2. Grafana Dashboards & Alerts

### 2.1 Dashboard: System Overview

**Components:**
- Service health status (up/down)
- Request rate (current, 5m average)
- Error rate trend
- Response time trend
- Database connection pool usage
- Memory/CPU utilization

**Key Alerts:**
- ⚠️ Error rate > 1% for 5 minutes
- 🚨 Error rate > 5% for 2 minutes
- ⚠️ Response time p95 > 500ms
- 🚨 Response time p99 > 1000ms

### 2.2 Dashboard: API Performance

**Endpoint-Level Metrics:**
- Request volume by endpoint
- Response time distribution by endpoint
- Error count by endpoint
- Slowest endpoints (by p95 latency)
- Most requested endpoints

**Drill-down Capability:**
- Click endpoint → See request patterns
- Click error → See error types and frequencies
- Click duration → See latency distribution

### 2.3 Dashboard: Database Performance

**Metrics:**
- Query count by operation (SELECT, INSERT, UPDATE, DELETE)
- Average query duration by operation
- Slow queries (> 1 second)
- Connection pool status
- Transaction metrics

**Alerts:**
- ⚠️ Slow query detected (> 1s)
- 🚨 Connection pool exhaustion (>90% used)
- ⚠️ High transaction count

### 2.4 Dashboard: Business Logic

**Metrics:**
- Validation failures by entity/field
- Business rule violations by type
- Workflow transitions by state
- Code generation success rate
- Pattern matching performance

**Visualization:**
- Heatmap: Validation failures by hour
- Pie chart: Failure distribution
- Trend: Success rate over time

### 2.5 Alert Rules Configuration

```yaml
# alert_rules.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: CriticalErrorRate
        expr: rate(http_errors_total[2m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical error rate"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.5
        for: 5m
        labels:
          severity: warning
```

---

## 3. Implementation Checklist

### Phase 4 (This Session)
- [x] Define Prometheus metrics to collect
- [x] Document Grafana dashboard requirements
- [ ] Auto-instrument generated services with prometheus_client
- [ ] Generate prometheus.yml from ApplicationIR
- [ ] Generate Grafana dashboard JSON files
- [ ] Create docker-compose setup with Prometheus + Grafana

### Phase 4.1 (Post-MVP)
- [ ] Implement actual Grafana dashboards in instances
- [ ] Configure alert notification channels (PagerDuty, Slack, email)
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Implement distributed tracing (Jaeger)
- [ ] Performance baseline collection

---

## 4. Generated App Integration

When DevMatrix generates an application, it automatically includes:

**prometheus_client dependency:**
```toml
# pyproject.toml
prometheus-client = "^0.20.0"
```

**Metrics middleware in main.py:**
```python
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = DispatcherMiddleware(app, {'/metrics': make_wsgi_app()})
```

**Service-level instrumentation:**
- Each service class includes metrics
- Each route handler wrapped with metrics
- Database queries tracked
- Validation errors recorded

**Docker compose for monitoring:**
```yaml
services:
  api:
    ports:
      - "8000:8000"
    environment:
      - PROMETHEUS_PORT=8001

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 5. Success Metrics

**Observability Goals:**
- ✅ All HTTP endpoints tracked
- ✅ Database queries monitored
- ✅ Business logic metrics recorded
- ✅ Real-time dashboards available
- ✅ Alert rules functioning

**SLA Indicators:**
- 📊 p50 response time < 50ms
- 📊 p95 response time < 100ms
- 📊 p99 response time < 200ms
- 📊 Error rate < 0.1%
- 📊 99.9% uptime capability

---

## Next Steps

1. **Integrate metrics into code generators** - Auto-instrument generated services
2. **Generate prometheus.yml** - From ApplicationIR configuration
3. **Generate Grafana dashboards** - JSON specs from metrics definitions
4. **Test in E2E pipeline** - Verify metrics collection works

---

**Owner**: DevMatrix Phase 4 Team
**Updated**: 2025-11-23
**Status**: 🔄 **IN PROGRESS** - Monitoring framework documented, implementation pending
