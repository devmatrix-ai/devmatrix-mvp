# DevMatrix - Deployment & Startup Guide

Complete guide for deploying and running DevMatrix in any environment.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Configuration](#configuration)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended for Local)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/devmatrix.git
cd devmatrix

# 2. Create environment file
cp .env.example .env
# Edit .env with your API keys

# 3. Start all services
docker compose up -d

# 4. Verify it's running
curl http://localhost:8000/api/v1/health/live

# 5. View logs
docker compose logs -f api
```

### Option 2: Kubernetes with Helm (Production)

```bash
# 1. Create namespace and secrets
kubectl create namespace devmatrix
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=your-secure-password \
  --from-literal=anthropic-api-key=sk-ant-... \
  --from-literal=openai-api-key=sk-... \
  --namespace devmatrix

# 2. Deploy with Helm
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/prod.yaml \
  --set secrets.create=false

# 3. Check deployment
kubectl get pods -n devmatrix
kubectl get svc -n devmatrix
```

### Option 3: Native Python (Development)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Start PostgreSQL and Redis
docker compose up -d postgres redis

# 4. Run migrations
alembic upgrade head

# 5. Start API server
uvicorn src.api.main:app --reload --port 8000
```

---

## 📦 Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Application runtime |
| Docker | 24.0+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| PostgreSQL | 15+ | Database (via Docker or native) |
| Redis | 7+ | Caching and state management |
| kubectl | 1.21+ | Kubernetes CLI (for K8s deployments) |
| Helm | 3.0+ | Kubernetes package manager |

### Required API Keys

```bash
# AI Providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-...  # For Claude models
OPENAI_API_KEY=sk-...         # For GPT models
GOOGLE_API_KEY=...            # For Gemini models

# Database (auto-configured in Docker)
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=your-secure-password

# Redis (optional password)
REDIS_PASSWORD=your-redis-password
```

### System Requirements

**Minimum (Development):**
- 2 CPU cores
- 4 GB RAM
- 10 GB disk space

**Recommended (Production):**
- 8+ CPU cores
- 16+ GB RAM
- 100+ GB SSD storage
- Load balancer
- Backup solution

---

## 💻 Local Development

### Setup Development Environment

```bash
# 1. Clone and navigate
git clone https://github.com/yourusername/devmatrix.git
cd devmatrix

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Create .env file
cat > .env <<EOF
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-key-here

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
EOF

# 5. Start infrastructure services
docker compose up -d postgres redis

# 6. Wait for services to be ready
sleep 5

# 7. Run database migrations
alembic upgrade head

# 8. Create initial data (optional)
python scripts/init_db.py

# 9. Start API server with hot reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Development Workflow

```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Security scan
bandit -r src/
safety check

# View API documentation
# Open http://localhost:8000/docs (Swagger UI)
# Open http://localhost:8000/redoc (ReDoc)
```

### Using DevMatrix CLI

```bash
# Activate virtual environment
source venv/bin/activate

# Check CLI
devmatrix --help

# Create agent
devmatrix agents create --name "MyAgent" --type coordinator

# List agents
devmatrix agents list

# Execute agent
devmatrix agents execute --agent-id 1 --task "Analyze repository"

# Manage plugins
devmatrix plugins list
devmatrix plugins load ./examples/plugins/
```

---

## 🐳 Docker Deployment

### Development with Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f
docker compose logs -f api

# Execute commands in container
docker compose exec api bash
docker compose exec postgres psql -U devmatrix

# Stop services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

### Production with Docker Compose

```bash
# 1. Create production environment file
cat > .env.production <<EOF
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=$(openssl rand -base64 32)

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$(openssl rand -base64 32)

ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=4
EOF

# 2. Start with production compose file
docker compose -f docker-compose.prod.yml up -d

# 3. Check status
docker compose -f docker-compose.prod.yml ps

# 4. View logs
docker compose -f docker-compose.prod.yml logs -f api

# 5. Monitor resources
docker stats
```

### Build Custom Docker Images

```bash
# Build development image
docker build --target development -t devmatrix/api:dev .

# Build production image
docker build --target production -t devmatrix/api:latest .

# Build with specific version
docker build --target production \
  --build-arg VERSION=1.0.0 \
  -t devmatrix/api:1.0.0 .

# Test image
docker run --rm devmatrix/api:latest python -c "import src; print('OK')"

# Run production image
docker run -d \
  --name devmatrix-api \
  -p 8000:8000 \
  -e POSTGRES_HOST=postgres \
  -e REDIS_HOST=redis \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  devmatrix/api:latest
```

---

## ☸️ Kubernetes Deployment

### Prerequisites for Kubernetes

```bash
# 1. Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# 2. Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 3. Install cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# 4. Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx
```

### Deploy to Development

```bash
# 1. Create namespace
kubectl create namespace devmatrix-dev

# 2. Deploy with Helm
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-dev \
  --values helm/devmatrix/values/dev.yaml

# 3. Check status
kubectl get all -n devmatrix-dev

# 4. Port forward to access locally
kubectl port-forward -n devmatrix-dev svc/devmatrix 8000:8000

# 5. Test
curl http://localhost:8000/api/v1/health/live
```

### Deploy to Staging

```bash
# 1. Create namespace
kubectl create namespace devmatrix-staging

# 2. Create secrets
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY_STAGING \
  --from-literal=openai-api-key=$OPENAI_API_KEY_STAGING \
  --namespace devmatrix-staging

# 3. Deploy with Helm
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-staging \
  --values helm/devmatrix/values/staging.yaml \
  --set secrets.create=false

# 4. Check deployment
kubectl get pods -n devmatrix-staging
kubectl rollout status deployment/devmatrix -n devmatrix-staging

# 5. Get ingress URL
kubectl get ingress -n devmatrix-staging
```

### Deploy to Production

```bash
# 1. Create namespace
kubectl create namespace devmatrix-prod

# 2. Create secrets securely (use sealed-secrets or external-secrets in real production)
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=$POSTGRES_PASSWORD_PROD \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY_PROD \
  --from-literal=openai-api-key=$OPENAI_API_KEY_PROD \
  --from-literal=google-api-key=$GOOGLE_API_KEY_PROD \
  --namespace devmatrix-prod

# 3. Deploy with Helm
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --values helm/devmatrix/values/prod.yaml \
  --set secrets.create=false \
  --set api.image.tag=v1.0.0

# 4. Verify deployment
kubectl get all -n devmatrix-prod
kubectl rollout status deployment/devmatrix -n devmatrix-prod

# 5. Check health
INGRESS_IP=$(kubectl get ingress devmatrix -n devmatrix-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$INGRESS_IP/api/v1/health/live

# 6. Monitor logs
kubectl logs -f deployment/devmatrix -n devmatrix-prod
```

### Upgrade Deployment

```bash
# Upgrade with new version
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --values helm/devmatrix/values/prod.yaml \
  --set api.image.tag=v1.1.0

# Check rollout
kubectl rollout status deployment/devmatrix -n devmatrix-prod

# Rollback if needed
helm rollback devmatrix -n devmatrix-prod
```

### Scale Deployment

```bash
# Manual scaling
kubectl scale deployment devmatrix --replicas=10 -n devmatrix-prod

# Enable auto-scaling
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --reuse-values \
  --set api.autoscaling.enabled=true \
  --set api.autoscaling.minReplicas=5 \
  --set api.autoscaling.maxReplicas=20

# Check HPA status
kubectl get hpa -n devmatrix-prod
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Application
ENVIRONMENT=development|staging|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json|text
PORT=8000
WORKERS=4  # Number of worker processes

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=secure-password
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=10

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_TTL=7200
REDIS_MAX_CONNECTIONS=50

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Performance
CACHE_ENABLED=true
CACHE_TTL=3600
MAX_WORKERS=4
REQUEST_TIMEOUT=300

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=8000
```

### Configuration Files

**config/app.yaml** (Kubernetes ConfigMap):
```yaml
environment: production
log_level: INFO
log_format: json

api:
  host: 0.0.0.0
  port: 8000
  workers: 4
  timeout: 300

redis:
  host: devmatrix-redis
  port: 6379
  db: 0
  ttl: 7200

postgres:
  host: devmatrix-postgres
  port: 5432
  pool_size: 20
  max_overflow: 10
```

---

## 📊 Monitoring

### Health Checks

```bash
# Liveness probe - Is service running?
curl http://localhost:8000/api/v1/health/live

# Readiness probe - Can service accept traffic?
curl http://localhost:8000/api/v1/health/ready

# Detailed health
curl http://localhost:8000/api/v1/health/detailed
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics to monitor:
# - http_requests_total
# - http_request_duration_seconds
# - agent_executions_total
# - cache_hits_total / cache_misses_total
# - db_connections_active
```

### Logs

```bash
# Docker Compose
docker compose logs -f api
docker compose logs -f --tail=100 api

# Kubernetes
kubectl logs -f deployment/devmatrix -n devmatrix
kubectl logs -f -l app=devmatrix -n devmatrix --all-containers=true
kubectl logs --since=1h deployment/devmatrix -n devmatrix > logs.txt
```

### Access API Documentation

```bash
# Swagger UI
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc

# OpenAPI JSON
curl http://localhost:8000/openapi.json
```

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs api
kubectl logs deployment/devmatrix -n devmatrix

# Check environment variables
docker compose exec api env | grep -E 'POSTGRES|REDIS|ANTHROPIC'
kubectl exec deployment/devmatrix -n devmatrix -- env

# Test database connection
docker compose exec postgres psql -U devmatrix -c "SELECT 1"
kubectl exec deployment/devmatrix-postgres -n devmatrix -- psql -U devmatrix -c "SELECT 1"

# Test Redis connection
docker compose exec redis redis-cli ping
kubectl exec deployment/devmatrix-redis -n devmatrix -- redis-cli ping
```

### High Error Rate

```bash
# Check error logs
docker compose logs api | grep ERROR
kubectl logs deployment/devmatrix -n devmatrix | grep ERROR

# Check resource usage
docker stats
kubectl top pods -n devmatrix
kubectl top nodes

# Check database connections
docker compose exec postgres psql -U devmatrix -c "SELECT count(*) FROM pg_stat_activity"
```

### Database Migration Issues

```bash
# Check current migration version
docker compose exec api alembic current

# Run migrations manually
docker compose exec api alembic upgrade head

# Rollback migration
docker compose exec api alembic downgrade -1

# Generate new migration
docker compose exec api alembic revision --autogenerate -m "description"
```

### Plugin Issues

```bash
# List loaded plugins
devmatrix plugins list

# Check plugin info
devmatrix plugins info plugin-name

# Reload plugins
devmatrix plugins load ./examples/plugins/

# Check plugin logs
docker compose logs api | grep "plugin"
```

### Network Issues

```bash
# Test API connectivity
curl -v http://localhost:8000/api/v1/health/live

# Check Docker network
docker network ls
docker network inspect devmatrix-network

# Check Kubernetes services
kubectl get svc -n devmatrix
kubectl describe svc devmatrix -n devmatrix

# Check ingress
kubectl get ingress -n devmatrix
kubectl describe ingress devmatrix -n devmatrix
```

---

## 🚨 Common Issues and Solutions

### Issue: "Connection refused" to PostgreSQL

**Solution:**
```bash
# Wait for PostgreSQL to be ready
docker compose up -d postgres
sleep 10

# Or check health
docker compose ps postgres
kubectl get pods -n devmatrix -l component=postgres
```

### Issue: "Redis connection timeout"

**Solution:**
```bash
# Restart Redis
docker compose restart redis

# Or check if Redis is responding
redis-cli -h localhost ping
```

### Issue: "API key invalid"

**Solution:**
```bash
# Verify API keys are set
echo $ANTHROPIC_API_KEY

# Update .env file
nano .env

# Restart services
docker compose restart api
```

### Issue: Kubernetes pods in CrashLoopBackOff

**Solution:**
```bash
# Check pod logs
kubectl logs <pod-name> -n devmatrix

# Check pod events
kubectl describe pod <pod-name> -n devmatrix

# Check secrets exist
kubectl get secrets -n devmatrix

# Delete and recreate pod
kubectl delete pod <pod-name> -n devmatrix
```

---

## 📚 Additional Resources

- **Full Deployment Guide**: [docs/deployment/README.md](docs/deployment/README.md)
- **Operational Runbooks**: [docs/deployment/RUNBOOKS.md](docs/deployment/RUNBOOKS.md)
- **Helm Chart Documentation**: [helm/devmatrix/README.md](helm/devmatrix/README.md)
- **Plugin Development**: [src/plugins/README.md](src/plugins/README.md)
- **API Documentation**: http://localhost:8000/docs
- **GitHub Repository**: https://github.com/yourusername/devmatrix

---

## 🆘 Getting Help

### Community Support
- GitHub Issues: https://github.com/yourusername/devmatrix/issues
- Discussions: https://github.com/yourusername/devmatrix/discussions
- Documentation: https://docs.devmatrix.example.com

### Reporting Bugs
1. Check existing issues
2. Create new issue with:
   - Environment details (OS, Python version, Docker version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs
   - Screenshots if applicable

### Contributing
1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by the DevMatrix Team**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
