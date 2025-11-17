# DevMatrix DevOps Guide

**Fecha**: 2025-11-16
**Status**: 🟢 Production Ready
**Versión**: 1.0

---

## 📋 Tabla de Contenidos

1. [Arquitectura de Infraestructura](#arquitectura-de-infraestructura)
2. [Docker & Containerización](#docker--containerización)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Monitoring & Observability](#monitoring--observability)
6. [Backup & Disaster Recovery](#backup--disaster-recovery)
7. [Scaling Strategies](#scaling-strategies)
8. [Security & Secrets Management](#security--secrets-management)
9. [Operational Runbooks](#operational-runbooks)
10. [Cloud Providers Setup](#cloud-providers-setup)

---

## 🏗️ Arquitectura de Infraestructura

### Stack Completo

```
┌─────────────────────────────────────────────────────────────┐
│                     LOAD BALANCER                           │
│                  (NGINX / AWS ALB)                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│  FastAPI    │         │  FastAPI    │
│  Instance 1 │         │  Instance 2 │
│  (8000)     │         │  (8000)     │
└──────┬──────┘         └──────┬──────┘
       │                       │
       └───────────┬───────────┘
                   │
       ┌───────────┴───────────┬───────────────┬──────────────┐
       │                       │               │              │
       ▼                       ▼               ▼              ▼
┌─────────────┐         ┌─────────────┐  ┌──────────┐  ┌──────────┐
│ PostgreSQL  │         │   Qdrant    │  │  Neo4j   │  │  Redis   │
│   (5432)    │         │   (6333)    │  │  (7687)  │  │  (6379)  │
└─────────────┘         └─────────────┘  └──────────┘  └──────────┘
       │                       │               │              │
       └───────────┬───────────┴───────────────┴──────────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Backup System │
          │  (S3 / Minio)  │
          └────────────────┘
```

### Componentes Principales

| Componente | Tecnología | Puerto | Replicas | Recursos |
|------------|------------|--------|----------|----------|
| API Server | FastAPI | 8000 | 3+ | 2 CPU, 4GB RAM |
| Database | PostgreSQL 15 | 5432 | 1 (+ standby) | 4 CPU, 8GB RAM |
| Vector DB | Qdrant | 6333 | 1 | 2 CPU, 4GB RAM |
| Graph DB | Neo4j | 7687 | 1 | 2 CPU, 4GB RAM |
| Cache | Redis | 6379 | 1 (+ sentinel) | 1 CPU, 2GB RAM |
| Load Balancer | NGINX | 80/443 | 2 | 1 CPU, 2GB RAM |
| Monitoring | Prometheus | 9090 | 1 | 2 CPU, 4GB RAM |
| Logs | Elasticsearch | 9200 | 3 | 4 CPU, 8GB RAM |

---

## 🐳 Docker & Containerización

### Dockerfile - FastAPI Backend

```dockerfile
# /Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd -m -u 1000 devmatrix && \
    chown -R devmatrix:devmatrix /app

USER devmatrix

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### docker-compose.yml - Development

```yaml
# /docker-compose.yml
version: '3.8'

services:
  # FastAPI Backend
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:devmatrix2024@postgres:5432/devmatrix
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=devmatrix2024
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - qdrant
      - neo4j
      - redis
    volumes:
      - ./src:/app/src
      - ./workspaces:/app/workspaces
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=devmatrix2024
      - POSTGRES_DB=devmatrix
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  # Neo4j Graph Database
  neo4j:
    image: neo4j:5.0
    environment:
      - NEO4J_AUTH=neo4j/devmatrix2024
      - NEO4J_PLUGINS=["apoc"]
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # NGINX Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  qdrant_data:
  neo4j_data:
  neo4j_logs:
  redis_data:
```

### docker-compose.production.yml

```yaml
# /docker-compose.production.yml
version: '3.8'

services:
  api:
    image: devmatrix/api:${VERSION}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - ENV=production
      - LOG_LEVEL=INFO
    secrets:
      - anthropic_api_key
      - db_password
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  postgres:
    image: postgres:15
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
    volumes:
      - /mnt/data/postgres:/var/lib/postgresql/data
    command: postgres -c max_connections=200 -c shared_buffers=2GB

secrets:
  anthropic_api_key:
    external: true
  db_password:
    external: true
```

---

## ☸️ Kubernetes Deployment

### Namespace

```yaml
# /k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: devmatrix
  labels:
    name: devmatrix
    environment: production
```

### ConfigMap

```yaml
# /k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: devmatrix-config
  namespace: devmatrix
data:
  DATABASE_HOST: postgres-service
  QDRANT_URL: http://qdrant-service:6333
  NEO4J_URI: bolt://neo4j-service:7687
  REDIS_URL: redis://redis-service:6379
  LOG_LEVEL: INFO
  ENV: production
```

### Secrets

```yaml
# /k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: devmatrix-secrets
  namespace: devmatrix
type: Opaque
stringData:
  ANTHROPIC_API_KEY: sk-ant-xxxxx  # Replace with actual key
  DATABASE_PASSWORD: xxxxx         # Replace with actual password
  NEO4J_PASSWORD: xxxxx            # Replace with actual password
```

### API Deployment

```yaml
# /k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devmatrix-api
  namespace: devmatrix
  labels:
    app: devmatrix-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devmatrix-api
  template:
    metadata:
      labels:
        app: devmatrix-api
    spec:
      containers:
      - name: api
        image: devmatrix/api:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: devmatrix-config
        - secretRef:
            name: devmatrix-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: devmatrix-api-service
  namespace: devmatrix
spec:
  selector:
    app: devmatrix-api
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

### PostgreSQL StatefulSet

```yaml
# /k8s/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: devmatrix
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          value: devmatrix
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: devmatrix-secrets
              key: DATABASE_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: devmatrix
spec:
  selector:
    app: postgres
  ports:
  - protocol: TCP
    port: 5432
    targetPort: 5432
  clusterIP: None
```

### Ingress

```yaml
# /k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: devmatrix-ingress
  namespace: devmatrix
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.devmatrix.com
    secretName: devmatrix-tls
  rules:
  - host: api.devmatrix.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: devmatrix-api-service
            port:
              number: 8000
```

### HorizontalPodAutoscaler

```yaml
# /k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: devmatrix-api-hpa
  namespace: devmatrix
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: devmatrix-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions - Main Workflow

```yaml
# /.github/workflows/main.yml
name: DevMatrix CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio

    - name: Run linters
      run: |
        pip install black mypy pylint
        black --check src/
        mypy src/
        pylint src/ --fail-under=8.0

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
      run: |
        pytest tests/ -v --cov=src --cov-report=xml --cov-report=term

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
        flags: unittests

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    permissions:
      contents: read
      packages: write

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=sha,prefix={{branch}}-
          type=semver,pattern={{version}}

    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging

    steps:
    - uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --name devmatrix-staging --region us-east-1

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/devmatrix-api \
          api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:develop-${{ github.sha }} \
          -n devmatrix-staging
        kubectl rollout status deployment/devmatrix-api -n devmatrix-staging

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
    - uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --name devmatrix-prod --region us-east-1

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/devmatrix-api \
          api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main-${{ github.sha }} \
          -n devmatrix
        kubectl rollout status deployment/devmatrix-api -n devmatrix

    - name: Verify deployment
      run: |
        kubectl get pods -n devmatrix
        kubectl get svc -n devmatrix
```

---

## 📊 Monitoring & Observability

### Prometheus Configuration

```yaml
# /monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'devmatrix-api'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - devmatrix
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      regex: devmatrix-api
      action: keep
    - source_labels: [__meta_kubernetes_pod_ip]
      target_label: __address__
      replacement: ${1}:8000

  - job_name: 'postgres'
    static_configs:
    - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
    - targets: ['redis-exporter:9121']

  - job_name: 'node-exporter'
    kubernetes_sd_configs:
    - role: node
```

### Prometheus Alerts

```yaml
# /monitoring/alerts.yml
groups:
- name: devmatrix
  interval: 30s
  rules:
  - alert: HighErrorRate
    expr: |
      rate(http_requests_total{status=~"5.."}[5m]) /
      rate(http_requests_total[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }}"

  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        rate(http_request_duration_seconds_bucket[5m])
      ) > 1
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High API latency"
      description: "P95 latency is {{ $value }}s"

  - alert: DatabaseDown
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "PostgreSQL is down"

  - alert: HighCPUUsage
    expr: |
      rate(container_cpu_usage_seconds_total{
        namespace="devmatrix",
        pod=~"devmatrix-api.*"
      }[5m]) > 0.8
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage on {{ $labels.pod }}"

  - alert: HighMemoryUsage
    expr: |
      container_memory_usage_bytes{
        namespace="devmatrix",
        pod=~"devmatrix-api.*"
      } / container_spec_memory_limit_bytes > 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High memory usage on {{ $labels.pod }}"
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "DevMatrix Operations",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Connections",
        "targets": [
          {
            "expr": "sum(pg_stat_activity_count)"
          }
        ]
      }
    ]
  }
}
```

### ELK Stack - Logstash Pipeline

```ruby
# /monitoring/logstash/pipeline.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [kubernetes][labels][app] == "devmatrix-api" {
    json {
      source => "message"
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    mutate {
      add_field => {
        "[@metadata][index]" => "devmatrix-api"
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][index]}-%{+YYYY.MM.dd}"
  }
}
```

---

## 💾 Backup & Disaster Recovery

### Backup Scripts

```bash
#!/bin/bash
# /scripts/backup.sh

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="s3://devmatrix-backups"

# PostgreSQL Backup
echo "Backing up PostgreSQL..."
pg_dump -h postgres -U postgres devmatrix | gzip > "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"

# Qdrant Backup
echo "Backing up Qdrant..."
curl -X POST "http://qdrant:6333/collections/snapshot" > "${BACKUP_DIR}/qdrant_${TIMESTAMP}.snapshot"

# Neo4j Backup
echo "Backing up Neo4j..."
docker exec neo4j neo4j-admin database dump neo4j --to-path=/backups > "${BACKUP_DIR}/neo4j_${TIMESTAMP}.dump"

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz" "${S3_BUCKET}/postgres/"
aws s3 cp "${BACKUP_DIR}/qdrant_${TIMESTAMP}.snapshot" "${S3_BUCKET}/qdrant/"
aws s3 cp "${BACKUP_DIR}/neo4j_${TIMESTAMP}.dump" "${S3_BUCKET}/neo4j/"

# Cleanup old backups (keep last 7 days)
find "${BACKUP_DIR}" -type f -mtime +7 -delete

echo "Backup completed successfully"
```

### Restore Script

```bash
#!/bin/bash
# /scripts/restore.sh

set -e

BACKUP_FILE=$1
COMPONENT=$2

if [ -z "$BACKUP_FILE" ] || [ -z "$COMPONENT" ]; then
  echo "Usage: $0 <backup_file> <postgres|qdrant|neo4j>"
  exit 1
fi

case $COMPONENT in
  postgres)
    echo "Restoring PostgreSQL from ${BACKUP_FILE}..."
    gunzip -c "$BACKUP_FILE" | psql -h postgres -U postgres devmatrix
    ;;

  qdrant)
    echo "Restoring Qdrant from ${BACKUP_FILE}..."
    curl -X PUT "http://qdrant:6333/collections/restore" \
      -H "Content-Type: application/json" \
      -d @"$BACKUP_FILE"
    ;;

  neo4j)
    echo "Restoring Neo4j from ${BACKUP_FILE}..."
    docker exec neo4j neo4j-admin database load neo4j --from-path=/backups
    ;;

  *)
    echo "Unknown component: $COMPONENT"
    exit 1
    ;;
esac

echo "Restore completed successfully"
```

### Automated Backup CronJob

```yaml
# /k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: devmatrix-backup
  namespace: devmatrix
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: devmatrix/backup-tools:latest
            env:
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: access-key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: secret-key
            command:
            - /scripts/backup.sh
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

---

## 📈 Scaling Strategies

### Vertical Scaling

```yaml
# Increase resources per pod
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

### Horizontal Scaling

```bash
# Manual scaling
kubectl scale deployment devmatrix-api --replicas=10 -n devmatrix

# Auto-scaling (HPA already configured)
# Scales between 3-10 pods based on CPU/memory
```

### Database Scaling

```sql
-- PostgreSQL Read Replicas
-- Configure in postgresql.conf:
hot_standby = on
max_wal_senders = 5
wal_level = replica

-- Connection Pooling (PgBouncer)
[databases]
devmatrix = host=postgres-primary port=5432 dbname=devmatrix

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

---

## 🔒 Security & Secrets Management

### Secrets Management with HashiCorp Vault

```hcl
# /vault/secrets.hcl
path "secret/data/devmatrix/*" {
  capabilities = ["read", "list"]
}

path "database/creds/devmatrix-app" {
  capabilities = ["read"]
}
```

### Network Policies

```yaml
# /k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: devmatrix-api-policy
  namespace: devmatrix
spec:
  podSelector:
    matchLabels:
      app: devmatrix-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
```

---

## 📖 Operational Runbooks

### Runbook 1: High CPU Alert

**Symptoms**: CPU usage > 80% for 10+ minutes

**Steps**:
1. Check current load:
   ```bash
   kubectl top pods -n devmatrix
   ```
2. Review recent deployments:
   ```bash
   kubectl rollout history deployment/devmatrix-api -n devmatrix
   ```
3. Scale up if needed:
   ```bash
   kubectl scale deployment devmatrix-api --replicas=6 -n devmatrix
   ```
4. Check logs for CPU-intensive operations:
   ```bash
   kubectl logs -n devmatrix -l app=devmatrix-api --tail=100 | grep -i "slow\|timeout"
   ```

### Runbook 2: Database Connection Pool Exhaustion

**Symptoms**: "Too many connections" errors

**Steps**:
1. Check current connections:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```
2. Kill idle connections:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle'
   AND state_change < current_timestamp - INTERVAL '5 minutes';
   ```
3. Increase pool size (temporary):
   ```bash
   kubectl set env deployment/devmatrix-api DB_POOL_SIZE=50 -n devmatrix
   ```

### Runbook 3: Deployment Rollback

**When**: New deployment causes errors

**Steps**:
1. Immediate rollback:
   ```bash
   kubectl rollout undo deployment/devmatrix-api -n devmatrix
   ```
2. Verify rollback:
   ```bash
   kubectl rollout status deployment/devmatrix-api -n devmatrix
   ```
3. Check application health:
   ```bash
   curl https://api.devmatrix.com/health
   ```

---

## ☁️ Cloud Providers Setup

### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster \
  --name devmatrix-prod \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --name devmatrix-prod --region us-east-1
```

### GCP GKE

```bash
# Create GKE cluster
gcloud container clusters create devmatrix-prod \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials devmatrix-prod --zone us-central1-a
```

### Azure AKS

```bash
# Create resource group
az group create --name devmatrix-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group devmatrix-rg \
  --name devmatrix-prod \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group devmatrix-rg --name devmatrix-prod
```

---

## 📞 Support & Escalation

### On-Call Rotation

| Week | Primary | Secondary | Backup |
|------|---------|-----------|--------|
| 1 | DevOps Team | Backend Team | Platform Team |
| 2 | Backend Team | Platform Team | DevOps Team |
| 3 | Platform Team | DevOps Team | Backend Team |

### Severity Levels

| Severity | Response Time | Example |
|----------|---------------|---------|
| P0 - Critical | 15 minutes | Complete system outage |
| P1 - High | 1 hour | Major feature unavailable |
| P2 - Medium | 4 hours | Performance degradation |
| P3 - Low | Next business day | Minor bugs |

---

## 📚 Additional Resources

- **Kubernetes Docs**: https://kubernetes.io/docs/
- **Prometheus Docs**: https://prometheus.io/docs/
- **ELK Stack**: https://www.elastic.co/guide/
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/

---

**Last Updated**: 2025-11-16
**Maintained By**: DevOps Team
**Review Cycle**: Monthly
