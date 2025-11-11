# Runbook: Operaciones Locales Production-Ready

Guía completa de operaciones para el sistema DevMatrix corriendo localmente con servicios reales.

## Inicio Rápido

### Start All Services

```bash
# 1. Start core services
docker compose up -d postgres redis chromadb

# 2. Wait for services to be healthy (30 seconds)
sleep 30

# 3. Verify all services are healthy
docker compose ps

# 4. Start monitoring (optional)
docker compose --profile monitoring up -d prometheus grafana

# 5. Start API (if needed)
docker compose up -d api

# 6. Verify everything is running
docker compose ps
```

### Stop All Services

```bash
# Stop all services
docker compose down

# Stop including volumes (⚠️ deletes data)
docker compose down -v
```

### Restart Single Service

```bash
# Restart specific service
docker compose restart postgres
docker compose restart redis
docker compose restart chromadb

# View logs
docker compose logs -f postgres
```

---

## Validación de Sistema

### Quick Health Checks

```bash
# PostgreSQL
docker exec -it devmatrix-postgres pg_isready -U devmatrix
# Expected: "devmatrix-postgres:5432 - accepting connections"

# Redis
docker exec -it devmatrix-redis redis-cli ping
# Expected: "PONG"

# ChromaDB
curl http://localhost:8001/api/v2/heartbeat
# Expected: {"nanosecond heartbeat": <timestamp>}

# API (if running)
curl http://localhost:8000/api/v1/health/live
# Expected: {"status": "healthy"}
```

### Run Comprehensive Validation

```bash
# Run validation script
python scripts/validate_local_production.py

# Expected output:
# ✅ Docker Services: PASSED
# ✅ PostgreSQL: PASSED
# ✅ Redis: PASSED
# ✅ ChromaDB: PASSED
# ✅ Git Workspace: PASSED
# ✅ Monitoring Stack: PASSED
# ✅ Anthropic API: PASSED
# ✅ Smoke Tests: PASSED
# ✨ System is PRODUCTION READY (Local) ✨
```

---

## Testing

### Run Test Suites

```bash
# 1. Unit tests (fast, no external dependencies)
pytest -m unit

# 2. Service validation tests (requires docker services)
pytest -v -m "real_services and smoke and not real_api"

# 3. RAG integration tests (requires ChromaDB)
pytest -v tests/integration/test_rag_real_services.py

# 4. E2E with real API (slow, costs money ~$0.05-0.20 per test)
pytest -v -m "e2e and real_api" tests/integration/test_e2e_code_generation_real.py

# 5. Complete workflow tests (requires API key)
pytest -v -m "e2e and real_api" tests/integration/test_complete_workflow_real.py
```

### Run Specific Test

```bash
# Run single test with verbose output
pytest -v -s tests/integration/test_rag_real_services.py::TestRAGRealChromaDB::test_indexing_and_retrieval_real

# Run with detailed traceback
pytest -v --tb=long tests/integration/test_services_validation.py
```

### View Test Coverage

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html -m "real_services and not real_api"

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Monitoring

### Access Dashboards

- **Grafana**: http://localhost:3001
  - Username: `admin`
  - Password: `admin` (or check GRAFANA_ADMIN_PASSWORD in .env)
  - Dashboard: DevMatrix Overview

- **Prometheus**: http://localhost:9090
  - Targets: http://localhost:9090/targets
  - Graph: http://localhost:9090/graph

### View Metrics

```bash
# API metrics (when instrumented)
curl http://localhost:8000/api/v1/metrics/prometheus

# Query Prometheus directly
curl 'http://localhost:9090/api/v1/query?query=up'

# Query specific metric
curl 'http://localhost:9090/api/v1/query?query=http_requests_total'
```

### Monitor Service Health

```bash
# Watch all container status
watch -n 2 'docker compose ps'

# Monitor resource usage
docker stats

# View all logs in real-time
docker compose logs -f
```

---

## Database Operations

### PostgreSQL

```bash
# Connect to database
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test

# Run SQL query
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "SELECT COUNT(*) FROM code_generation_logs"

# View tables
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "\dt"

# Backup database
docker exec devmatrix-postgres pg_dump -U devmatrix devmatrix_test > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20251017.sql | docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix_test
```

### Redis

```bash
# Connect to Redis CLI
docker exec -it devmatrix-redis redis-cli

# View all keys
docker exec -it devmatrix-redis redis-cli KEYS '*'

# Get specific key
docker exec -it devmatrix-redis redis-cli GET workflow:test_session

# Flush all data (⚠️ dangerous)
docker exec -it devmatrix-redis redis-cli FLUSHALL

# Get info
docker exec -it devmatrix-redis redis-cli INFO
```

### ChromaDB

```bash
# View collections
curl http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections

# Get collection count
python -c "
from src.rag import create_embedding_model, create_vector_store
embedding_model = create_embedding_model()
vector_store = create_vector_store(embedding_model, collection_name='devmatrix_code_examples')
print(f'Total examples: {vector_store.collection.count()}')
"

# Backup ChromaDB data
docker cp devmatrix-chromadb:/chroma/chroma ./chromadb_backup_$(date +%Y%m%d)/
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs [service-name] --tail 50

# Example: PostgreSQL logs
docker compose logs postgres | tail -50

# Check if port is already in use
netstat -tulpn | grep 5432  # PostgreSQL
netstat -tulpn | grep 6379  # Redis
netstat -tulpn | grep 8001  # ChromaDB

# Restart with fresh volumes
docker compose down -v
docker compose up -d
```

### Tests Failing

```bash
# 1. Check environment configuration
cat .env.test | grep ANTHROPIC_API_KEY

# 2. Validate services are running
python scripts/validate_local_production.py

# 3. Check test database exists
docker exec -it devmatrix-postgres psql -U devmatrix -l | grep devmatrix_test

# 4. Re-setup test database
python scripts/setup_test_database.py

# 5. Run with verbose output
pytest -v -s --tb=long
```

### API Rate Limits / Circuit Breaker

```bash
# Check if Anthropic API is rate limited
# Look for 429 errors in logs

# Wait and retry (rate limits reset after time)
sleep 60

# Reduce test parallelization
pytest -n 1  # Sequential execution

# Disable circuit breaker for tests
# In conftest.py: enable_circuit_breaker=False
```

### ChromaDB Connection Issues

```bash
# Check ChromaDB is running
curl http://localhost:8001/api/v2/heartbeat

# Restart ChromaDB
docker compose restart chromadb

# View ChromaDB logs
docker compose logs chromadb --tail 100

# Check port configuration
echo $CHROMADB_PORT  # Should be 8001
```

### Git Operations Failing

```bash
# Check git configuration in workspace
cd workspace_test
git config user.name
git config user.email

# Re-initialize git workspace
cd ..
rm -rf workspace_test
mkdir workspace_test
cd workspace_test
git init
git config user.name "DevMatrix Test"
git config user.email "test@devmatrix.local"
touch .gitkeep
git add .gitkeep
git commit -m "chore: init test workspace"
```

---

## Maintenance

### Clean Up Test Data

```bash
# Truncate test tables
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "TRUNCATE TABLE code_generation_logs CASCADE"

docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "TRUNCATE TABLE agent_execution_logs CASCADE"

# Flush Redis test keys
docker exec -it devmatrix-redis redis-cli --scan --pattern 'workflow:*' | \
  xargs docker exec -i devmatrix-redis redis-cli DEL

# Clear ChromaDB test collections
python -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8001)
collections = client.list_collections()
for col in collections:
    if 'test' in col.name:
        client.delete_collection(col.name)
        print(f'Deleted: {col.name}')
"
```

### Update Dependencies

```bash
# Pull latest Docker images
docker compose pull

# Rebuild API container
docker compose build --no-cache api

# Restart with new images
docker compose down
docker compose up -d

# Update Python dependencies
pip install -r requirements.txt --upgrade
```

### Backup Complete System

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup PostgreSQL
docker exec devmatrix-postgres pg_dump -U devmatrix devmatrix_test > \
  backups/$(date +%Y%m%d)/postgres.sql

# Backup ChromaDB
docker cp devmatrix-chromadb:/chroma/chroma \
  backups/$(date +%Y%m%d)/chromadb/

# Backup configuration
cp .env.test backups/$(date +%Y%m%d)/env.test.bak
cp docker-compose.yml backups/$(date +%Y%m%d)/docker-compose.yml.bak

echo "Backup complete: backups/$(date +%Y%m%d)/"
```

---

## Cost Management

### Estimate API Costs

```bash
# View token usage from logs
grep -r "tokens_used" logs/ | tail -20

# Calculate approximate cost
# Claude 3.5 Sonnet pricing (as of 2024):
# Input: $3 per million tokens
# Output: $15 per million tokens

python -c "
input_tokens = 5000  # example
output_tokens = 1000  # example
cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)
print(f'Estimated cost: \${cost:.4f}')
"
```

### Limit API Usage

```bash
# Run only specific tests
pytest -k "test_simple_function" -m real_api

# Run single test
pytest tests/integration/test_e2e_code_generation_real.py::TestE2ERealServices::test_e2e_fibonacci_real_api

# Enable caching to reduce redundant calls
# In .env.test:
# RAG_CACHE_ENABLED=true

# Use smaller test dataset
# Reduce iterations in performance tests
```

---

## Performance Optimization

### Speed Up Tests

```bash
# Run tests in parallel (for unit tests)
pytest -n auto -m unit

# Skip slow tests
pytest -m "not slow"

# Use test markers strategically
pytest -m "smoke"  # Only quick validation tests
```

### Monitor Performance

```bash
# Test execution time breakdown
pytest --durations=10

# Profile specific test
pytest --profile tests/integration/test_rag_real_services.py

# Monitor resource usage during tests
docker stats
```

---

## Common Workflows

### Daily Development

```bash
# Morning setup
docker compose up -d postgres redis chromadb
python scripts/validate_local_production.py

# Run tests before committing
pytest -m "real_services and not real_api"

# Evening cleanup
docker compose down
```

### Before Deployment

```bash
# Full validation
python scripts/validate_local_production.py

# Run complete test suite
pytest -v -m "real_services"

# Run E2E tests (if budget allows)
pytest -v -m "e2e and real_api" --maxfail=1

# Check test coverage
pytest --cov=src --cov-report=term-missing
```

### Debugging Issues

```bash
# 1. Check all services
docker compose ps

# 2. View logs
docker compose logs --tail 100

# 3. Run validation
python scripts/validate_local_production.py

# 4. Run specific failing test with debugging
pytest -v -s --pdb tests/integration/test_rag_real_services.py::TestRAGRealChromaDB::test_indexing_and_retrieval_real
```

---

## Quick Reference

### Service Ports

- PostgreSQL: 5432
- Redis: 6379
- ChromaDB: 8001
- API: 8000
- Prometheus: 9090
- Grafana: 3001

### Important Files

- `.env.test` - Test environment configuration
- `docker-compose.yml` - Service definitions
- `tests/conftest.py` - Test fixtures
- `scripts/validate_local_production.py` - Validation script
- `scripts/setup_test_database.py` - Database setup

### Key Commands

```bash
# Start everything
docker compose up -d && docker compose --profile monitoring up -d

# Validate
python scripts/validate_local_production.py

# Test
pytest -v -m "real_services and not real_api"

# Monitor
docker compose logs -f

# Stop
docker compose down
```

---

## Support & Resources

### Documentation
- Main Plan: `DOCS/LOCAL_PRODUCTION_READY_PLAN.md`
- This Runbook: `DOCS/LOCAL_OPERATIONS_RUNBOOK.md`
- Test Documentation: `tests/README.md` (if exists)

### Logs Location
- Test logs: `tests/test.log`
- Application logs: `logs/` directory
- Docker logs: `docker compose logs [service]`

### Getting Help

1. Check this runbook first
2. Run validation script: `python scripts/validate_local_production.py`
3. Check service logs: `docker compose logs [service]`
4. Review test output: `pytest -v --tb=long`

---

**Last Updated**: 2025-10-17
**System Version**: Production Ready Local v1.0
