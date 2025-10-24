# MGE V2 Production Migration Runbook

**Purpose**: Step-by-step guide for production migration day
**Estimated Duration**: 2-4 hours
**Team Required**: 2-3 engineers on-call
**Rollback Time**: 30-60 minutes

---

## Pre-Migration Checklist (T-48h)

### Staging Validation
- [ ] All E2E tests passing in staging ✅
- [ ] Performance benchmarks met (precision ≥98%, time <1.5h) ✅
- [ ] Load tests passed (10+ concurrent) ✅
- [ ] Security audit complete (0 critical issues) ✅
- [ ] Data migration dry-run successful ✅

### Rollback Preparation
- [ ] Rollback procedure tested in staging ✅
- [ ] Database backup scripts verified ✅
- [ ] Git tag `pre-v2-migration` created ✅
- [ ] Rollback checklist printed ✅

### Communication
- [ ] Users notified (T-48h email) ✅
- [ ] Status page updated ✅
- [ ] Social media announcement ✅
- [ ] Support team briefed ✅

### Team Readiness
- [ ] Primary engineer assigned ✅
- [ ] Backup engineer on-call ✅
- [ ] Database admin on-call ✅
- [ ] Conference bridge ready ✅

---

## Migration Timeline

### T-2 Hours: Final Preparation

**Tasks**:
- [ ] Final staging validation
- [ ] Announce "Maintenance starting in 2 hours"
- [ ] Email users with maintenance window
- [ ] Update status page: "Upcoming Maintenance"
- [ ] Verify backups working
- [ ] Test conference bridge

**Communication Template**:
```
Subject: DevMatrix Maintenance Window - MGE V2 Upgrade

We will be performing a major system upgrade to MGE V2 today.

Maintenance Window: [START_TIME] - [END_TIME] (estimated 2-4 hours)
Impact: Full system unavailable
Reason: Migration to MGE V2 for improved performance and accuracy

What to expect after upgrade:
- 98% precision (up from 87%)
- 1.5 hour execution (down from 13 hours)
- 100+ parallel atoms (up from 2-3 tasks)

We appreciate your patience!
```

---

### T+0:00 - Enable Maintenance Mode (5 minutes)

**Goal**: Stop accepting new requests

**Steps**:
1. **Set maintenance mode flag**
   ```bash
   docker exec devmatrix-backend \
     python -c "from src.config import set_maintenance_mode; set_maintenance_mode(True)"
   ```

2. **Update load balancer** (if applicable)
   ```bash
   # Return 503 for all requests
   # Keep health check endpoint alive
   ```

3. **Display maintenance page**
   - Update homepage to show maintenance message
   - Return HTTP 503 Service Unavailable

4. **Verify maintenance mode**
   ```bash
   curl -I http://localhost:8000/api/v1/health
   # Should return 503
   ```

**Validation**:
- [ ] All endpoints return 503
- [ ] Maintenance page visible
- [ ] Health check still responding

---

### T+0:05 - Stop All Services (5 minutes)

**Goal**: Safely stop all running services

**Steps**:
1. **Stop Celery workers** (background tasks)
   ```bash
   docker-compose stop celery
   docker-compose ps celery  # Verify stopped
   ```

2. **Stop FastAPI backend**
   ```bash
   docker-compose stop backend
   docker-compose ps backend  # Verify stopped
   ```

3. **Verify no active connections**
   ```bash
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "SELECT count(*) FROM pg_stat_activity WHERE datname='devmatrix';"
   # Should show minimal connections (just this query)
   ```

4. **Verify no pending jobs**
   ```bash
   docker exec devmatrix-redis redis-cli LLEN celery
   # Should be 0 or very low
   ```

**Validation**:
- [ ] All services stopped
- [ ] No active database connections
- [ ] No pending jobs

---

### T+0:10 - Database Backup (10 minutes)

**Goal**: Full backup for rollback safety

**Steps**:
1. **Create backup directory**
   ```bash
   mkdir -p ~/devmatrix-backups/$(date +%Y%m%d)
   cd ~/devmatrix-backups/$(date +%Y%m%d)
   ```

2. **Dump PostgreSQL database**
   ```bash
   BACKUP_FILE="devmatrix_pre_v2_$(date +%Y%m%d_%H%M%S).sql"

   docker exec devmatrix-postgres \
     pg_dump -U devmatrix devmatrix \
     > $BACKUP_FILE

   # Compress backup
   gzip $BACKUP_FILE
   ```

3. **Verify backup**
   ```bash
   gunzip -c ${BACKUP_FILE}.gz | head -100
   # Should show SQL dump header

   du -h ${BACKUP_FILE}.gz
   # Should be reasonable size (check against expected)
   ```

4. **Copy backup to safe location**
   ```bash
   # S3 / Cloud storage
   aws s3 cp ${BACKUP_FILE}.gz s3://devmatrix-backups/

   # Or external server
   scp ${BACKUP_FILE}.gz backup-server:/backups/
   ```

**Validation**:
- [ ] Backup file created
- [ ] Backup file verified (not corrupt)
- [ ] Backup copied to safe location
- [ ] Backup file size reasonable

**Rollback Point**: If backup fails, ABORT migration

---

### T+0:20 - Run Database Migrations (10 minutes)

**Goal**: Add V2 schema to database

**Steps**:
1. **Verify migration files**
   ```bash
   ls -la alembic/versions/202510*
   # Should see mge_v2_schema.py
   ```

2. **Check current migration version**
   ```bash
   docker-compose run --rm backend \
     alembic current
   # Note current version
   ```

3. **Run migrations**
   ```bash
   docker-compose run --rm backend \
     alembic upgrade head
   ```

4. **Verify new tables**
   ```bash
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "\dt" | grep -E "(atomic_units|atom_dependencies|dependency_graphs)"

   # Should show 7 new tables:
   # - atomic_units
   # - atom_dependencies
   # - dependency_graphs
   # - validation_results
   # - execution_waves
   # - atom_retry_history
   # - human_review_queue
   ```

5. **Check table schemas**
   ```bash
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "\d atomic_units"
   # Verify columns match spec
   ```

**Validation**:
- [ ] Migrations ran successfully
- [ ] All 7 new tables created
- [ ] Table schemas correct
- [ ] Indexes created

**Rollback Point**: If migrations fail, restore backup and abort

---

### T+0:30 - Data Migration (60-90 minutes)

**Goal**: Convert existing tasks → atoms

**Steps**:
1. **Dry run** (test mode)
   ```bash
   docker-compose run --rm backend \
     python scripts/migrate_tasks_to_atoms.py --dry-run

   # Review output:
   # - Number of tasks found
   # - Expected atoms to create
   # - Any warnings/errors
   ```

2. **Production migration**
   ```bash
   docker-compose run --rm backend \
     python scripts/migrate_tasks_to_atoms.py --production

   # Monitor output:
   # - Progress (tasks processed)
   # - Success rate
   # - Any errors
   ```

3. **Verify data integrity**
   ```bash
   # Check atom count
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "SELECT COUNT(*) FROM atomic_units;"

   # Check all tasks migrated
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "SELECT COUNT(*) FROM masterplan_tasks WHERE NOT EXISTS (
           SELECT 1 FROM atomic_units WHERE task_id = masterplan_tasks.task_id
         );"
   # Should be 0

   # Check context completeness
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "SELECT AVG((context_json->>'completeness_score')::float) FROM atomic_units;"
   # Should be ≥0.95
   ```

4. **Spot check data**
   ```bash
   # Check a few atoms manually
   docker exec devmatrix-postgres \
     psql -U devmatrix -d devmatrix \
     -c "SELECT atom_id, name, estimated_loc, complexity
         FROM atomic_units
         LIMIT 10;"
   ```

**Validation**:
- [ ] All tasks converted to atoms
- [ ] Atom count reasonable (tasks × 8 average)
- [ ] Context completeness ≥95%
- [ ] No data corruption
- [ ] Spot checks look good

**Rollback Point**: If data migration fails, restore backup and abort

---

### T+1:30 - Deploy V2 Code (30 minutes)

**Goal**: Deploy V2 codebase to production

**Steps**:
1. **Pull V2 code**
   ```bash
   git fetch --all
   git checkout v2.0.0  # Or appropriate tag
   git log -1  # Verify correct commit
   ```

2. **Build Docker images**
   ```bash
   docker-compose build backend
   docker-compose build celery
   ```

3. **Update environment variables**
   ```bash
   # Verify .env has V2-specific vars
   cat .env | grep V2

   # Example vars:
   # ENABLE_V2=true
   # V2_ATOMIZATION_ENABLED=true
   # V2_DEPENDENCY_GRAPH_ENABLED=true
   ```

4. **Start services**
   ```bash
   docker-compose up -d backend
   docker-compose up -d celery
   ```

5. **Check container status**
   ```bash
   docker-compose ps
   # All should be "Up"
   ```

6. **Check logs**
   ```bash
   docker-compose logs backend --tail 100
   docker-compose logs celery --tail 100
   # Look for startup errors
   ```

**Validation**:
- [ ] Containers running
- [ ] No errors in logs
- [ ] Services started successfully

---

### T+2:00 - Health Checks (15 minutes)

**Goal**: Verify all systems operational

**Steps**:
1. **Database connectivity**
   ```bash
   curl http://localhost:8000/api/v1/health/db
   # Should return 200 OK
   ```

2. **Redis connectivity**
   ```bash
   curl http://localhost:8000/api/v1/health/redis
   # Should return 200 OK
   ```

3. **ChromaDB connectivity**
   ```bash
   curl http://localhost:8000/api/v1/health/chromadb
   # Should return 200 OK
   ```

4. **API endpoints**
   ```bash
   # V1 endpoints (backward compat)
   curl http://localhost:8000/api/v1/health

   # V2 endpoints
   curl http://localhost:8000/api/v2/health
   curl http://localhost:8000/api/v2/atoms/health
   curl http://localhost:8000/api/v2/graphs/health
   curl http://localhost:8000/api/v2/validation/health
   curl http://localhost:8000/api/v2/execution/health
   curl http://localhost:8000/api/v2/review/health
   ```

**Validation**:
- [ ] All health checks passing
- [ ] Database connected
- [ ] Redis connected
- [ ] ChromaDB connected
- [ ] All V2 endpoints responding

---

### T+2:15 - Smoke Tests (15 minutes)

**Goal**: Verify critical paths working

**Steps**:
1. **Create test masterplan**
   ```bash
   curl -X POST http://localhost:8000/api/v2/masterplans \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TEST_TOKEN" \
     -d '{
       "user_request": "Build a simple TODO app with FastAPI and React",
       "user_id": "test-user-migration",
       "session_id": "test-session-migration"
     }'

   # Save masterplan_id from response
   MASTERPLAN_ID="..."
   ```

2. **Run atomization**
   ```bash
   curl -X POST http://localhost:8000/api/v2/atomization/decompose \
     -H "Authorization: Bearer $TEST_TOKEN" \
     -d "{\"masterplan_id\": \"$MASTERPLAN_ID\"}"

   # Should return atoms count (e.g., 800)
   ```

3. **Build dependency graph**
   ```bash
   curl -X POST http://localhost:8000/api/v2/graphs/build \
     -H "Authorization: Bearer $TEST_TOKEN" \
     -d "{\"masterplan_id\": \"$MASTERPLAN_ID\"}"

   # Should return graph_id and waves count
   ```

4. **Execute small batch**
   ```bash
   # Execute just first wave (10-20 atoms)
   curl -X POST http://localhost:8000/api/v2/execution/start \
     -H "Authorization: Bearer $TEST_TOKEN" \
     -d "{
       \"masterplan_id\": \"$MASTERPLAN_ID\",
       \"max_waves\": 1
     }"

   # Monitor execution
   watch -n 5 "curl -s http://localhost:8000/api/v2/execution/status/$MASTERPLAN_ID \
     -H 'Authorization: Bearer $TEST_TOKEN' | jq '.'"
   ```

5. **Verify results**
   ```bash
   # Check execution results
   curl http://localhost:8000/api/v2/execution/results/$MASTERPLAN_ID \
     -H "Authorization: Bearer $TEST_TOKEN" | jq '.'

   # Should show:
   # - Atoms executed successfully
   # - Precision metrics
   # - Execution time
   ```

**Validation**:
- [ ] Masterplan created
- [ ] Atomization successful (800 atoms)
- [ ] Dependency graph built (8-10 waves)
- [ ] Execution working (10-20 atoms completed)
- [ ] Results look correct

**Rollback Point**: If smoke tests fail, initiate rollback

---

### T+2:30 - Go/No-Go Decision (10 minutes)

**Criteria for GO**:
- ✅ All health checks passing
- ✅ Smoke tests passing
- ✅ No critical errors in logs
- ✅ Database integrity verified
- ✅ Performance acceptable

**Criteria for NO-GO**:
- ❌ Health checks failing
- ❌ Smoke tests failing
- ❌ Critical errors in logs
- ❌ Data corruption detected
- ❌ Performance unacceptable

**If GO**:
- Proceed to "Remove Maintenance Mode"

**If NO-GO**:
- Proceed to "Rollback Procedure"

---

### T+2:30 - Remove Maintenance Mode (5 minutes)

**Goal**: Open system to users

**Steps**:
1. **Disable maintenance mode**
   ```bash
   docker exec devmatrix-backend \
     python -c "from src.config import set_maintenance_mode; set_maintenance_mode(False)"
   ```

2. **Update status page**
   - Status: "Operational"
   - Message: "MGE V2 upgrade complete!"

3. **Announce completion**
   ```
   Subject: DevMatrix Back Online - MGE V2 Live!

   Great news! Our MGE V2 upgrade is complete and the system is back online.

   What's new:
   - 98% precision (up from 87%)
   - 1.5 hour execution (down from 13 hours)
   - 100+ parallel atoms (up from 2-3 tasks)

   Please let us know if you experience any issues.
   Thank you for your patience!
   ```

4. **Verify users can access**
   ```bash
   curl http://localhost:8000/api/v1/health
   # Should return 200, not 503
   ```

**Validation**:
- [ ] Maintenance mode disabled
- [ ] Users can access system
- [ ] Status page updated
- [ ] Announcement sent

---

### T+2:30 → T+4:30 - Close Monitoring (2 hours)

**Goal**: Monitor for issues and respond quickly

**Monitoring Checklist** (every 15 minutes):
- [ ] **Error rates**: <1%
  ```bash
  # Check error logs
  docker-compose logs backend --tail 100 | grep -i error
  ```

- [ ] **Performance**: Execution time <1.5h
  ```bash
  # Check recent executions
  curl http://localhost:8000/api/v2/metrics/executions/recent \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```

- [ ] **Precision**: ≥98%
  ```bash
  # Check precision metrics
  curl http://localhost:8000/api/v2/metrics/precision/recent \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```

- [ ] **User activity**: Normal patterns
  ```bash
  # Check active users
  curl http://localhost:8000/api/v2/metrics/users/active \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```

- [ ] **Support tickets**: Manageable volume
  - Check support inbox
  - Monitor Slack/Discord

**Alert Triggers**:
- Error rate >5% → Investigate immediately
- Execution time >3h → Performance issue
- Precision <90% → Quality issue
- No user activity → Access issue
- Support ticket flood → Communication needed

**Actions on Issues**:
- **Minor issues**: Fix in place, monitor
- **Major issues**: Consider rollback
- **Critical issues**: Initiate rollback immediately

---

## Rollback Procedure (30-60 minutes)

**When to Rollback**:
- Critical bugs preventing usage
- Data corruption detected
- Performance <50% of targets
- User-facing errors >5%
- Team consensus to rollback

### Step 1: Announce Rollback (5 min)
```bash
# Set maintenance mode
docker exec devmatrix-backend \
  python -c "from src.config import set_maintenance_mode; set_maintenance_mode(True)"

# Announce
echo "ROLLBACK INITIATED - System in maintenance mode"
```

### Step 2: Stop V2 Services (5 min)
```bash
docker-compose stop backend celery
docker-compose ps  # Verify stopped
```

### Step 3: Restore Database (15-30 min)
```bash
# Drop V2 database
docker exec devmatrix-postgres \
  dropdb -U devmatrix devmatrix --if-exists

# Create fresh database
docker exec devmatrix-postgres \
  createdb -U devmatrix devmatrix

# Restore from backup
BACKUP_FILE="devmatrix_pre_v2_YYYYMMDD_HHMM"
gunzip -c ${BACKUP_FILE}.gz | \
  docker exec -i devmatrix-postgres \
  psql -U devmatrix devmatrix

# Verify restore
docker exec devmatrix-postgres \
  psql -U devmatrix -d devmatrix \
  -c "SELECT COUNT(*) FROM masterplan_tasks;"
```

### Step 4: Deploy MVP Code (10 min)
```bash
# Checkout pre-migration code
git checkout pre-v2-migration
git log -1  # Verify

# Rebuild images
docker-compose build backend celery

# Start services
docker-compose up -d backend celery
```

### Step 5: Validate Rollback (10 min)
```bash
# Health checks
curl http://localhost:8000/api/v1/health

# Smoke test (MVP flow)
# Create masterplan
# Execute task
# Verify results
```

### Step 6: Go Live (5 min)
```bash
# Disable maintenance mode
docker exec devmatrix-backend \
  python -c "from src.config import set_maintenance_mode; set_maintenance_mode(False)"

# Announce rollback complete
echo "ROLLBACK COMPLETE - MVP restored"
```

### Step 7: Post-Rollback
- [ ] Root cause analysis
- [ ] Document lessons learned
- [ ] Fix issues in staging
- [ ] Re-test thoroughly
- [ ] Schedule new migration date

---

## Post-Migration Tasks (Week 14)

### Immediate (First 48 hours)
- [ ] Monitor error rates hourly
- [ ] Respond to support tickets promptly
- [ ] Fix critical bugs immediately
- [ ] Collect user feedback

### Short-term (First week)
- [ ] Performance optimization based on metrics
- [ ] Documentation updates
- [ ] Training materials for support team
- [ ] Success criteria validation

### Long-term (First month)
- [ ] User satisfaction survey
- [ ] ROI tracking
- [ ] Optimization opportunities
- [ ] Plan for future enhancements

---

## Emergency Contacts

**Primary Engineer**: [Name] - [Phone] - [Email]
**Backup Engineer**: [Name] - [Phone] - [Email]
**Database Admin**: [Name] - [Phone] - [Email]
**Product Manager**: [Name] - [Phone] - [Email]

**Conference Bridge**: [URL/Phone]
**Status Page**: [URL]
**Support Email**: support@devmatrix.com

---

## Success Criteria

After migration, verify:
- ✅ Zero data loss
- ✅ Downtime <4 hours
- ✅ Precision ≥98%
- ✅ Execution time <1.5h
- ✅ Cost <$200 per project
- ✅ Parallelization 100+ atoms
- ✅ User satisfaction ≥4.5/5
- ✅ No critical bugs

---

**Runbook Status**: ✅ Ready for Use
**Last Updated**: 2025-10-23
**Version**: 1.0
