# DevMatrix Helm Chart

Helm chart for deploying DevMatrix multi-agent AI development environment on Kubernetes.

## Prerequisites

- Kubernetes 1.21+
- Helm 3.0+
- cert-manager (for TLS certificates)
- NGINX Ingress Controller
- PersistentVolume provisioner support in the underlying infrastructure

## Installing the Chart

### Development Environment

```bash
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --create-namespace \
  --values helm/devmatrix/values/dev.yaml
```

### Staging Environment

```bash
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --create-namespace \
  --values helm/devmatrix/values/staging.yaml \
  --set secrets.data.anthropicApiKey="your-key" \
  --set secrets.data.openaiApiKey="your-key"
```

### Production Environment

```bash
# First create secrets manually or use external-secrets
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=secure-password \
  --from-literal=anthropic-api-key=your-key \
  --from-literal=openai-api-key=your-key \
  --namespace devmatrix

# Install with prod values
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --create-namespace \
  --values helm/devmatrix/values/prod.yaml \
  --set secrets.create=false
```

## Configuration

The following table lists the configurable parameters of the DevMatrix chart and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name | `production` |

### API Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.replicaCount` | Number of API replicas | `3` |
| `api.image.repository` | API image repository | `devmatrix/api` |
| `api.image.tag` | API image tag | `latest` |
| `api.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `api.resources.requests.memory` | Memory request | `512Mi` |
| `api.resources.requests.cpu` | CPU request | `250m` |
| `api.resources.limits.memory` | Memory limit | `1Gi` |
| `api.resources.limits.cpu` | CPU limit | `1000m` |
| `api.autoscaling.enabled` | Enable HPA | `false` |
| `api.autoscaling.minReplicas` | Minimum replicas | `3` |
| `api.autoscaling.maxReplicas` | Maximum replicas | `10` |

### PostgreSQL Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.image.repository` | PostgreSQL image | `postgres` |
| `postgresql.image.tag` | PostgreSQL version | `15-alpine` |
| `postgresql.auth.database` | Database name | `devmatrix` |
| `postgresql.auth.username` | Database user | `devmatrix` |
| `postgresql.primary.persistence.enabled` | Enable persistence | `false` |
| `postgresql.primary.persistence.size` | PVC size | `8Gi` |

### Redis Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.image.repository` | Redis image | `redis` |
| `redis.image.tag` | Redis version | `7-alpine` |
| `redis.master.persistence.enabled` | Enable persistence | `false` |
| `redis.master.persistence.size` | PVC size | `8Gi` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Hostname | `api.devmatrix.example.com` |
| `ingress.tls[0].secretName` | TLS secret name | `devmatrix-tls` |

### Secrets Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.create` | Create secrets | `true` |
| `secrets.data.anthropicApiKey` | Anthropic API key | `""` |
| `secrets.data.openaiApiKey` | OpenAI API key | `""` |
| `secrets.data.googleApiKey` | Google API key | `""` |

## Upgrading

```bash
# Development
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/dev.yaml

# Production
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/prod.yaml
```

## Uninstalling

```bash
helm uninstall devmatrix --namespace devmatrix
```

## Environment-Specific Configurations

### Development (`values/dev.yaml`)
- 1 API replica
- No persistence (emptyDir)
- Reduced resource limits
- Debug logging
- Staging TLS certificates
- No monitoring

### Staging (`values/staging.yaml`)
- 2 API replicas
- Persistence enabled (10Gi/5Gi)
- Medium resource limits
- Info logging
- Production TLS certificates
- Basic monitoring

### Production (`values/prod.yaml`)
- 5 API replicas (HPA: 5-20)
- Persistence enabled (50Gi/20Gi) with fast-ssd
- Full resource limits
- Info logging
- Production TLS certificates
- Full monitoring with alerts
- Pod anti-affinity
- Network policies

## Security Considerations

### Secret Management

**DO NOT** commit actual secrets to version control. Use one of these approaches:

1. **Sealed Secrets** (recommended)
```bash
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=YOUR_PASSWORD \
  --from-literal=anthropic-api-key=YOUR_KEY \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secrets.yaml
```

2. **External Secrets Operator**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: devmatrix-secrets
spec:
  secretStoreRef:
    name: vault
  target:
    name: devmatrix-secrets
  data:
  - secretKey: anthropic-api-key
    remoteRef:
      key: devmatrix/api-keys
      property: anthropic
```

3. **Helm Secrets Plugin**
```bash
helm secrets install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/prod.yaml \
  --values secrets://helm/devmatrix/secrets.yaml
```

### RBAC

The chart creates minimal RBAC permissions:
- Read access to ConfigMaps and Secrets
- Read access to Pods
- No cluster-wide permissions

### Network Policies

Enable network policies in production:
```yaml
networkPolicy:
  enabled: true
```

## Monitoring

### Prometheus Metrics

The API exposes Prometheus metrics at `/metrics`:
- HTTP request metrics
- Agent execution metrics
- Cache hit rates
- Database connection pool stats

### Service Monitor

Enable Prometheus ServiceMonitor:
```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
```

### Alerting Rules

Production alerts are configured in `values/prod.yaml`:
- High error rate (>5% 5xx responses)
- High memory usage (>90%)

## Troubleshooting

### Check pod status
```bash
kubectl get pods -n devmatrix
kubectl describe pod <pod-name> -n devmatrix
kubectl logs <pod-name> -n devmatrix
```

### Check secrets
```bash
kubectl get secrets -n devmatrix
kubectl describe secret devmatrix-secrets -n devmatrix
```

### Check configuration
```bash
kubectl get configmap devmatrix-config -n devmatrix -o yaml
```

### Test connectivity
```bash
# Test API
kubectl port-forward svc/devmatrix 8000:8000 -n devmatrix
curl http://localhost:8000/api/v1/health/live

# Test PostgreSQL
kubectl port-forward svc/devmatrix-postgres 5432:5432 -n devmatrix
psql -h localhost -U devmatrix -d devmatrix

# Test Redis
kubectl port-forward svc/devmatrix-redis 6379:6379 -n devmatrix
redis-cli -h localhost ping
```

### Debug Helm
```bash
# Render templates without installing
helm template devmatrix ./helm/devmatrix \
  --values helm/devmatrix/values/dev.yaml \
  --debug

# Dry run
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix \
  --values helm/devmatrix/values/dev.yaml \
  --dry-run --debug
```

## Best Practices

1. **Use environment-specific values files** - Don't modify `values.yaml` directly
2. **Never commit secrets** - Use sealed-secrets or external-secrets
3. **Enable monitoring in staging/prod** - Catch issues early
4. **Use resource limits** - Prevent resource exhaustion
5. **Enable persistence in prod** - Use fast storage for databases
6. **Enable HPA in prod** - Handle traffic spikes automatically
7. **Use pod anti-affinity** - Spread pods across nodes
8. **Enable network policies** - Restrict traffic flow
9. **Regular backups** - Backup PostgreSQL data regularly
10. **Test upgrades in staging** - Before production deployment

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/devmatrix/issues
- Documentation: https://github.com/yourusername/devmatrix/docs
