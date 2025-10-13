# DevMatrix Operational Runbooks

Standard operating procedures for common operational tasks.

## Table of Contents

1. [Deployment Procedures](#deployment-procedures)
2. [Rollback Procedures](#rollback-procedures)
3. [Scaling Operations](#scaling-operations)
4. [Backup and Restore](#backup-and-restore)
5. [Disaster Recovery](#disaster-recovery)
6. [Incident Response](#incident-response)
7. [Maintenance Windows](#maintenance-windows)

---

## Deployment Procedures

### Standard Production Deployment

**Pre-deployment Checklist:**
- [ ] Code reviewed and approved
- [ ] All tests passing in CI
- [ ] Staging environment validated
- [ ] Backup completed
- [ ] Change request approved
- [ ] Team notified
- [ ] Rollback plan ready

**Deployment Steps:**

```bash
# 1. Verify current state
kubectl get pods -n devmatrix-prod
helm list -n devmatrix-prod

# 2. Create backup
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  pg_dump -U devmatrix devmatrix > backup-$(date +%Y%m%d-%H%M%S).sql

# 3. Deploy new version
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --values helm/devmatrix/values/prod.yaml \
  --set api.image.tag=v1.2.3 \
  --wait \
  --timeout 15m

# 4. Monitor rollout
kubectl rollout status deployment/devmatrix -n devmatrix-prod
watch kubectl get pods -n devmatrix-prod

# 5. Verify health
ENDPOINT="https://api.devmatrix.example.com"
curl -f ${ENDPOINT}/api/v1/health/live
curl -f ${ENDPOINT}/api/v1/health/ready

# 6. Run smoke tests
# See smoke-tests.sh

# 7. Monitor metrics
kubectl port-forward -n devmatrix-prod svc/devmatrix 9090:8000
curl http://localhost:9090/metrics
```

**Post-deployment:**
- [ ] Health checks passing
- [ ] Metrics normal
- [ ] Smoke tests passed
- [ ] Logs clean
- [ ] Team notified of success

---

## Rollback Procedures

### Immediate Rollback (Critical Issues)

**When to rollback immediately:**
- 5xx error rate > 10%
- Service completely down
- Data corruption detected
- Critical security issue

**Rollback Steps:**

```bash
# 1. Stop incoming traffic (if necessary)
kubectl scale deployment/devmatrix --replicas=0 -n devmatrix-prod

# 2. Rollback Helm release
helm rollback devmatrix -n devmatrix-prod

# 3. Or rollback Kubernetes deployment
kubectl rollout undo deployment/devmatrix -n devmatrix-prod

# 4. Monitor rollback
kubectl rollout status deployment/devmatrix -n devmatrix-prod

# 5. Restore traffic
kubectl scale deployment/devmatrix --replicas=5 -n devmatrix-prod

# 6. Verify health
curl -f https://api.devmatrix.example.com/api/v1/health/live
```

### Controlled Rollback

**For non-critical issues:**

```bash
# 1. Identify target revision
helm history devmatrix -n devmatrix-prod

# 2. Rollback to specific revision
helm rollback devmatrix <revision> -n devmatrix-prod

# 3. Verify rollback
kubectl get pods -n devmatrix-prod
kubectl logs -f deployment/devmatrix -n devmatrix-prod

# 4. Run validation tests
# See validation-tests.sh
```

**Post-rollback:**
- [ ] Service restored
- [ ] Root cause identified
- [ ] Incident documented
- [ ] Team notified
- [ ] Post-mortem scheduled

---

## Scaling Operations

### Manual Scaling

**Vertical Scaling (Resources):**

```bash
# Update resource limits
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --reuse-values \
  --set api.resources.limits.memory=2Gi \
  --set api.resources.limits.cpu=2000m
```

**Horizontal Scaling (Replicas):**

```bash
# Scale up for traffic spike
kubectl scale deployment/devmatrix --replicas=15 -n devmatrix-prod

# Monitor scaling
watch kubectl get pods -n devmatrix-prod

# Verify load distribution
kubectl top pods -n devmatrix-prod
```

### Auto-scaling Configuration

**Enable HPA:**

```bash
helm upgrade devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --reuse-values \
  --set api.autoscaling.enabled=true \
  --set api.autoscaling.minReplicas=5 \
  --set api.autoscaling.maxReplicas=20 \
  --set api.autoscaling.targetCPUUtilizationPercentage=70
```

**Monitor HPA:**

```bash
# Check HPA status
kubectl get hpa -n devmatrix-prod

# Describe HPA for details
kubectl describe hpa devmatrix -n devmatrix-prod

# Watch HPA in action
watch kubectl get hpa devmatrix -n devmatrix-prod
```

---

## Backup and Restore

### PostgreSQL Backup

**Manual Backup:**

```bash
# Full database backup
DATE=$(date +%Y%m%d-%H%M%S)
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  pg_dump -U devmatrix -Fc devmatrix > backup-${DATE}.dump

# Verify backup
ls -lh backup-${DATE}.dump
```

**Automated Backup (CronJob):**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: devmatrix-prod
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -U devmatrix -h devmatrix-postgres -Fc devmatrix | \
              aws s3 cp - s3://devmatrix-backups/postgres-$(date +%Y%m%d-%H%M%S).dump
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: devmatrix-secrets
                  key: postgres-password
          restartPolicy: OnFailure
```

### PostgreSQL Restore

**Restore from Backup:**

```bash
# 1. Stop application
kubectl scale deployment/devmatrix --replicas=0 -n devmatrix-prod

# 2. Copy backup to pod
kubectl cp backup-20240115-020000.dump \
  devmatrix-postgres-pod:/tmp/restore.dump \
  -n devmatrix-prod

# 3. Restore database
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  pg_restore -U devmatrix -d devmatrix -c /tmp/restore.dump

# 4. Restart application
kubectl scale deployment/devmatrix --replicas=5 -n devmatrix-prod

# 5. Verify restore
kubectl logs -f deployment/devmatrix -n devmatrix-prod
```

### Redis Backup

**Manual Backup:**

```bash
# Trigger SAVE
kubectl exec -it deployment/devmatrix-redis -n devmatrix-prod -- \
  redis-cli SAVE

# Copy RDB file
kubectl cp devmatrix-redis-pod:/data/dump.rdb \
  ./redis-backup-$(date +%Y%m%d-%H%M%S).rdb \
  -n devmatrix-prod
```

---

## Disaster Recovery

### Complete Cluster Failure

**Recovery Steps:**

```bash
# 1. Provision new cluster
# (Cloud provider specific)

# 2. Install prerequisites
kubectl create namespace devmatrix-prod
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# 3. Restore secrets
kubectl create secret generic devmatrix-secrets \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  --namespace devmatrix-prod

# 4. Deploy with Helm
helm install devmatrix ./helm/devmatrix \
  --namespace devmatrix-prod \
  --values helm/devmatrix/values/prod.yaml \
  --set secrets.create=false

# 5. Restore database
# See PostgreSQL Restore section

# 6. Verify system
kubectl get all -n devmatrix-prod
curl -f https://api.devmatrix.example.com/api/v1/health/live
```

### Database Corruption

**Recovery Steps:**

```bash
# 1. Assess damage
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  psql -U devmatrix -d devmatrix -c "\dt"

# 2. Stop application
kubectl scale deployment/devmatrix --replicas=0 -n devmatrix-prod

# 3. Attempt repair
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  vacuumdb -U devmatrix -d devmatrix -f -z

# 4. If repair fails, restore from backup
# See PostgreSQL Restore section

# 5. Restart application
kubectl scale deployment/devmatrix --replicas=5 -n devmatrix-prod
```

---

## Incident Response

### Severity Levels

**P0 - Critical:**
- Complete service outage
- Data loss or corruption
- Security breach

**P1 - High:**
- Partial service degradation
- High error rates (>5%)
- Performance severely impacted

**P2 - Medium:**
- Minor feature issues
- Isolated errors
- Performance slightly degraded

**P3 - Low:**
- Cosmetic issues
- Feature requests
- Minor bugs

### P0 Incident Response

**Immediate Actions (First 5 minutes):**

```bash
# 1. Assess impact
kubectl get pods -n devmatrix-prod
kubectl top nodes
kubectl top pods -n devmatrix-prod

# 2. Check recent changes
helm history devmatrix -n devmatrix-prod
kubectl rollout history deployment/devmatrix -n devmatrix-prod

# 3. Check logs for errors
kubectl logs -f deployment/devmatrix -n devmatrix-prod --tail=100 | grep ERROR

# 4. Declare incident
# Post to #incidents channel
# Start incident bridge call

# 5. Initial mitigation
# If caused by recent deploy: rollback immediately
helm rollback devmatrix -n devmatrix-prod
```

**Investigation (Next 15 minutes):**

```bash
# 1. Check external dependencies
# PostgreSQL
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  psql -U devmatrix -c "SELECT 1"

# Redis
kubectl exec -it deployment/devmatrix-redis -n devmatrix-prod -- \
  redis-cli ping

# 2. Check resource usage
kubectl top pods -n devmatrix-prod
kubectl describe nodes

# 3. Check network
kubectl get ingress -n devmatrix-prod
kubectl describe ingress devmatrix -n devmatrix-prod

# 4. Check API health
curl -v https://api.devmatrix.example.com/api/v1/health/live
```

**Communication:**

```
Incident Update Template:

**Status:** INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED
**Impact:** [Brief description of user impact]
**Started:** [Timestamp]
**Last Update:** [Timestamp]

**Current Status:**
[What we know so far]

**Actions Taken:**
- [Action 1]
- [Action 2]

**Next Steps:**
- [Next action]

**ETA:** [Estimated resolution time or "unknown"]
```

### Post-Incident

**Post-Mortem Template:**

```markdown
# Incident Post-Mortem

**Date:** 2024-01-15
**Severity:** P0
**Duration:** 45 minutes
**Impact:** 100% of users unable to access API

## Timeline
- 14:00 - Deployment started (v1.2.3)
- 14:05 - High error rate alerts triggered
- 14:07 - Incident declared
- 14:10 - Rollback initiated
- 14:15 - Service restored
- 14:45 - Monitoring shows normal behavior

## Root Cause
[Detailed explanation of what went wrong]

## Resolution
[How the issue was resolved]

## Action Items
- [ ] Fix identified issue (Owner: @person, Due: date)
- [ ] Add monitoring for X (Owner: @person, Due: date)
- [ ] Update runbook (Owner: @person, Due: date)
- [ ] Review deployment process (Owner: @person, Due: date)

## Lessons Learned
- What went well
- What could be improved
```

---

## Maintenance Windows

### Scheduled Maintenance

**Pre-maintenance:**

```bash
# 1. Announce maintenance window
# Post to #devmatrix-updates 24 hours ahead

# 2. Create backup
# See Backup section

# 3. Prepare rollback plan
helm history devmatrix -n devmatrix-prod

# 4. Put service in maintenance mode (optional)
kubectl set env deployment/devmatrix \
  MAINTENANCE_MODE=true \
  -n devmatrix-prod
```

**During maintenance:**

```bash
# 1. Scale down (if needed)
kubectl scale deployment/devmatrix --replicas=0 -n devmatrix-prod

# 2. Perform maintenance tasks
# Database migrations
kubectl exec -it deployment/devmatrix-postgres -n devmatrix-prod -- \
  psql -U devmatrix -d devmatrix -f /path/to/migration.sql

# 3. Scale back up
kubectl scale deployment/devmatrix --replicas=5 -n devmatrix-prod

# 4. Verify health
kubectl get pods -n devmatrix-prod
curl -f https://api.devmatrix.example.com/api/v1/health/live
```

**Post-maintenance:**

```bash
# 1. Run validation tests
# See validation-tests.sh

# 2. Monitor for 30 minutes
watch kubectl get pods -n devmatrix-prod
watch kubectl top pods -n devmatrix-prod

# 3. Announce completion
# Post to #devmatrix-updates

# 4. Document any issues
# Update runbook if needed
```

---

## Contact Information

**On-call Engineers:**
- Primary: [Name] <email> +1-xxx-xxx-xxxx
- Secondary: [Name] <email> +1-xxx-xxx-xxxx

**Escalation Path:**
1. On-call Engineer
2. Team Lead
3. Engineering Manager
4. CTO

**Communication Channels:**
- Incidents: #incidents
- Updates: #devmatrix-updates
- Engineering: #devmatrix-eng

**External Services:**
- PagerDuty: https://yourcompany.pagerduty.com
- Status Page: https://status.devmatrix.example.com
