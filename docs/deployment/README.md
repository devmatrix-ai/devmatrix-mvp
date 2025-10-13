# DevMatrix Deployment Guide

Comprehensive guide for deploying DevMatrix to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoring & Observability](#monitoring--observability)
7. [Troubleshooting](#troubleshooting)
8. [Runbooks](#runbooks)

## Prerequisites

### Required Tools

- **Docker** 24.0+
- **Kubernetes** 1.21+
- **Helm** 3.0+
- **kubectl** configured with cluster access
- **Python** 3.11+
- **Git**

### Required Secrets

```bash
# API Keys
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Database
POSTGRES_PASSWORD=secure-random-password
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix

# Redis (optional)
REDIS_PASSWORD=secure-random-password
```

### Infrastructure Requirements

#### Development
- 2 CPUs, 4GB RAM minimum
- 10GB disk space

#### Staging
- 4 CPUs, 8GB RAM recommended
- 50GB disk space
- PostgreSQL with 10GB storage
- Redis with 5GB storage

#### Production
- 8+ CPUs, 16GB+ RAM
- 100GB+ disk space
- PostgreSQL with 50GB+ SSD storage
- Redis with 20GB+ SSD storage
- Load balancer with SSL termination
- Backup solution
- Monitoring stack

## Local Development

### Using Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/yourusername/devmatrix.git
cd devmatrix

# 2. Create .env file
cp .env.example .env
# Edit .env with your API keys

# 3. Start services
docker compose up -d

# 4. Check logs
docker compose logs -f api

# 5. Access API
curl http://localhost:8000/api/v1/health/live
```

### Native Python Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Start PostgreSQL and Redis
docker compose up -d postgres redis

# 4. Run migrations
alembic upgrade head

# 5. Start API
uvicorn src.api.main:app --reload --port 8000
```

## Docker Deployment

### Build Images

```bash
# Development image
docker build --target development -t devmatrix/api:dev .

# Production image
docker build --target production -t devmatrix/api:latest .
```

### Run Production Image

```bash
# Using docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d

# Or manually
docker run -d \
  --name devmatrix-api \
  -p 8000:8000 \
  -e POSTGRES_HOST=postgres \
  -e REDIS_HOST=redis \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --network devmatrix-network \
  devmatrix/api:latest
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/api/v1/health/live

# Readiness probe
curl http://localhost:8000/api/v1/health/ready

# Metrics
curl http://localhost:8000/metrics
```

## Kubernetes Deployment

### Quick Start with Helm

```bash
# 1. Add secrets
kubectl create namespace devmatrix
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=your-password \
  --from-literal=anthropic-api-key=your-key \
  --from-literal=openai-api-key=your-key \
  --namespace devmatrix

# 2. Install with Helm
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/prod.yaml \
  --set secrets.create=false

# 3. Verify deployment
kubectl get pods -n devmatrix
kubectl get svc -n devmatrix
kubectl get ingress -n devmatrix
```

### Environment-Specific Deployments

#### Development
```bash
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-dev \
  --create-namespace \
  --values helm/devmatrix/values/dev.yaml
```

#### Staging
```bash
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-staging \
  --create-namespace \
  --values helm/devmatrix/values/staging.yaml \
  --set secrets.data.anthropicApiKey=$ANTHROPIC_API_KEY_STAGING
```

#### Production
```bash
# Production requires pre-created secrets
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --namespace devmatrix-prod

helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --create-namespace \
  --values helm/devmatrix/values/prod.yaml \
  --set secrets.create=false
```

### Upgrading Deployments

```bash
# Upgrade with new values
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/prod.yaml \
  --set api.image.tag=v1.2.3

# Check rollout status
kubectl rollout status deployment/devmatrix -n devmatrix

# Rollback if needed
helm rollback devmatrix -n devmatrix
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment devmatrix --replicas=10 -n devmatrix

# Enable HPA (Horizontal Pod Autoscaler)
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --set api.autoscaling.enabled=true \
  --set api.autoscaling.minReplicas=5 \
  --set api.autoscaling.maxReplicas=20
```

## CI/CD Pipeline

### GitHub Actions Workflows

The project includes three main workflows:

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Code quality checks (Black, isort, flake8, mypy, pylint)
   - Security scanning (Safety, Bandit)
   - Unit tests with coverage
   - Integration tests
   - Docker image builds

2. **CD Pipeline** (`.github/workflows/cd.yml`)
   - Build and push Docker images to GHCR
   - Deploy to development (on `develop` branch)
   - Deploy to staging (on `main` branch)
   - Deploy to production (on version tags)
   - Smoke tests after deployment
   - Automatic rollback on failure

3. **Release Workflow** (`.github/workflows/release.yml`)
   - Create GitHub release
   - Package Helm chart
   - Generate changelog
   - Update documentation
   - Notifications

### Required GitHub Secrets

```bash
# Kubernetes Configurations (base64 encoded kubeconfig)
KUBE_CONFIG_DEV
KUBE_CONFIG_STAGING
KUBE_CONFIG_PROD

# API Keys per environment
ANTHROPIC_API_KEY_STAGING
ANTHROPIC_API_KEY_PROD
OPENAI_API_KEY_STAGING
OPENAI_API_KEY_PROD

# Optional: Notifications
SLACK_WEBHOOK
```

### Manual Deployment Trigger

```bash
# Trigger deployment via GitHub CLI
gh workflow run cd.yml -f environment=production

# Or via GitHub UI:
# Actions → CD Pipeline → Run workflow → Select environment
```

### Rollback Procedure

```bash
# Via GitHub Actions
gh workflow run cd.yml -f environment=production --rollback

# Via kubectl
kubectl rollout undo deployment/devmatrix -n devmatrix-prod

# Via Helm
helm rollback devmatrix -n devmatrix-prod
```

## Monitoring & Observability

### Prometheus Metrics

The API exposes Prometheus metrics at `/metrics`:

```yaml
# Scrape configuration
- job_name: 'devmatrix'
  static_configs:
    - targets: ['devmatrix:8000']
  metrics_path: '/metrics'
  scrape_interval: 30s
```

**Key Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `agent_executions_total` - Agent execution count
- `cache_hits_total` / `cache_misses_total` - Cache performance
- `db_connections_active` - Database connection pool

### Health Endpoints

```bash
# Liveness - Is the service running?
GET /api/v1/health/live
Response: 200 OK

# Readiness - Can the service accept traffic?
GET /api/v1/health/ready
Response: 200 OK (checks DB and Redis connectivity)
```

### Logging

**Structured JSON logging** in production:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "devmatrix.api",
  "message": "Request completed",
  "request_id": "abc-123",
  "method": "POST",
  "path": "/api/v1/agents/execute",
  "status": 200,
  "duration_ms": 1250
}
```

**Log aggregation:**
```bash
# View logs in Kubernetes
kubectl logs -f deployment/devmatrix -n devmatrix --tail=100

# Follow logs from all pods
kubectl logs -f -l app=devmatrix -n devmatrix --all-containers=true

# Export logs to file
kubectl logs deployment/devmatrix -n devmatrix --since=1h > devmatrix.log
```

### Alerts

Production alerting rules (Prometheus):

```yaml
groups:
  - name: devmatrix
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting guide.

### Common Issues

#### Pods Crashing
```bash
# Check pod status
kubectl get pods -n devmatrix

# View pod logs
kubectl logs <pod-name> -n devmatrix

# Describe pod for events
kubectl describe pod <pod-name> -n devmatrix
```

#### Database Connection Issues
```bash
# Test PostgreSQL connectivity
kubectl exec -it deployment/devmatrix -n devmatrix -- \
  psql -h devmatrix-postgres -U devmatrix -d devmatrix -c "SELECT 1"

# Check PostgreSQL logs
kubectl logs deployment/devmatrix-postgres -n devmatrix
```

#### Redis Connection Issues
```bash
# Test Redis connectivity
kubectl exec -it deployment/devmatrix -n devmatrix -- \
  redis-cli -h devmatrix-redis ping

# Check Redis logs
kubectl logs deployment/devmatrix-redis -n devmatrix
```

## Runbooks

See [RUNBOOKS.md](./RUNBOOKS.md) for operational procedures:

- Deployment procedures
- Rollback procedures
- Scaling procedures
- Backup and restore
- Disaster recovery
- Incident response

## Security Best Practices

1. **Never commit secrets** - Use sealed-secrets or external-secrets
2. **Use RBAC** - Minimal permissions for service accounts
3. **Enable network policies** - Restrict pod-to-pod communication
4. **Scan images** - Use vulnerability scanning in CI/CD
5. **Rotate secrets** - Regular secret rotation policy
6. **Use TLS** - Always encrypt traffic with valid certificates
7. **Audit logs** - Enable Kubernetes audit logging
8. **Resource limits** - Always set CPU and memory limits

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/devmatrix/issues
- Documentation: https://github.com/yourusername/devmatrix/docs
- Slack: #devmatrix-support
