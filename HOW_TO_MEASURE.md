# HOW TO MEASURE - Precision Baseline Guide

**Goal**: Measure and track MGE V2 precision from current baseline (38%) to target (98%)

## Quick Start

```bash
# 1. Run baseline measurement (10 iterations)
python scripts/measure_precision_baseline.py --iterations 10

# 2. Run determinism tests
pytest tests/test_determinism.py -v

# 3. Check dashboard
curl http://localhost:8000/api/dashboard/precision

# 4. View reports
open reports/precision/baseline_*.html
```

## Using Docker (Recommended)

### Start Test Infrastructure

```bash
# Start PostgreSQL and Redis for testing
docker-compose -f docker-compose.test.yml up -d postgres-test redis-test

# Wait for healthy status
docker-compose -f docker-compose.test.yml ps
```

### Run Baseline Measurement

```bash
# Quick baseline (3 iterations, ~2 minutes)
docker-compose -f docker-compose.test.yml --profile quick up baseline-quick

# Full baseline (10 iterations, ~5-10 minutes)
docker-compose -f docker-compose.test.yml --profile baseline up baseline

# Custom iterations
BASELINE_ITERATIONS=20 docker-compose -f docker-compose.test.yml --profile baseline up baseline
```

### Run Determinism Tests

```bash
# Run determinism test suite
docker-compose -f docker-compose.test.yml --profile determinism up determinism-tests

# Interactive test shell
docker-compose -f docker-compose.test.yml run --rm tests bash
pytest tests/test_determinism.py -v -s
```

### Run All Tests

```bash
# Complete test suite with coverage
docker-compose -f docker-compose.test.yml --profile test up tests
```

### Cleanup

```bash
# Stop and remove containers
docker-compose -f docker-compose.test.yml down

# Remove volumes (clean state)
docker-compose -f docker-compose.test.yml down -v
```

## Native Python Execution

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Start PostgreSQL and Redis (local or Docker)
# See docker-compose.yml for configuration
```

### Run Baseline Script

```bash
# Default: 10 iterations
python scripts/measure_precision_baseline.py

# Custom iterations
python scripts/measure_precision_baseline.py --iterations 20

# Custom user request
python scripts/measure_precision_baseline.py \
  --user-request "Create a REST API for e-commerce platform" \
  --iterations 5

# Custom output directory
python scripts/measure_precision_baseline.py \
  --output-dir ./custom-reports \
  --iterations 10
```

**Output:**
- JSON: `reports/precision/baseline_TIMESTAMP.json`
- HTML: `reports/precision/baseline_TIMESTAMP.html`

### Run Determinism Tests

```bash
# All determinism tests
pytest tests/test_determinism.py -v

# Specific test
pytest tests/test_determinism.py::TestDeterminism::test_same_discovery_same_masterplan_hash -v

# With coverage
pytest tests/test_determinism.py --cov=src --cov-report=html
```

## Understanding the Reports

### JSON Report Structure

```json
{
  "summary": {
    "total_iterations": 10,
    "successful_iterations": 10,
    "failed_iterations": 0,
    "precision_score": 38.5,
    "determinism_score": 50.0,
    "target_precision": 98.0,
    "gap_to_target": 59.5
  },
  "task_count": {
    "mean": 25.0,
    "std": 0.0,
    "min": 25,
    "max": 25
  },
  "atom_count": {
    "mean": 25.0,
    "std": 0.0,
    "min": 25,
    "max": 25
  },
  "success_rate": {
    "mean": 38.5,
    "std": 2.1,
    "min": 36.0,
    "max": 40.0
  },
  "determinism_violations": {
    "mean": 0.5,
    "total_violations": 5,
    "deterministic_iterations": 5,
    "determinism_percentage": 50.0
  }
}
```

### HTML Report

Open `reports/precision/baseline_*.html` in browser to see:
- Summary metrics (precision, determinism, gap to target)
- Progress bar visualization
- Detailed metrics table
- Individual iteration results
- Determinism analysis

### Key Metrics

1. **Precision Score**: % of atoms that succeed (target: 98%)
2. **Determinism Score**: % of iterations with identical output (target: 100%)
3. **Gap to Target**: How much improvement needed
4. **Task/Atom Count Variance**: Should be 0 (deterministic)
5. **Success Rate Variance**: Measure of consistency

## Dashboard API

### Start API Server

```bash
# Development mode
uvicorn src.api.main:app --reload

# Or with Docker
docker-compose up -d api
```

### Check Precision Dashboard

```bash
# Get current metrics
curl http://localhost:8000/api/dashboard/precision | jq

# Response:
{
  "metrics": {
    "current_precision": 38.5,
    "target_precision": 98.0,
    "determinism_score": 50.0,
    "phase": 1,
    "gap_to_target": 59.5,
    "total_executions": 10,
    "last_updated": "2025-11-12T10:00:00Z"
  },
  "last_executions": [...],
  "alerts": [...]
}
```

### Get Execution History

```bash
# Last 20 executions
curl http://localhost:8000/api/dashboard/history?limit=20 | jq

# With pagination
curl http://localhost:8000/api/dashboard/history?limit=10&offset=10 | jq
```

### Get Precision Trends

```bash
# Hourly trends (last 24 hours)
curl http://localhost:8000/api/dashboard/trends?period=hour | jq

# Daily trends (last 7 days)
curl http://localhost:8000/api/dashboard/trends?period=day | jq

# Weekly trends (last 12 weeks)
curl http://localhost:8000/api/dashboard/trends?period=week | jq
```

### Get Alerts

```bash
# Active alerts
curl http://localhost:8000/api/dashboard/alerts | jq

# Example alerts:
[
  {
    "severity": "warning",
    "message": "Precision below target: 38.5%",
    "timestamp": "2025-11-12T10:00:00Z",
    "details": {"current": 38.5, "threshold": 70.0}
  },
  {
    "severity": "info",
    "message": "Large gap to target: 59.5% improvement needed",
    "timestamp": "2025-11-12T10:00:00Z",
    "details": {"gap": 59.5, "target": 98.0}
  }
]
```

## CI/CD Integration

### GitHub Actions

The workflow runs automatically:
- **Every commit**: Determinism tests
- **Every hour**: Baseline measurement
- **On PR**: Regression check

**Manual trigger:**

```bash
# Via GitHub UI: Actions → Precision Tracking → Run workflow

# Or via gh CLI:
gh workflow run precision-tracking.yml --ref main
gh workflow run precision-tracking.yml --ref main -f iterations=20
```

**View results:**

```bash
# List workflow runs
gh run list --workflow=precision-tracking.yml

# View specific run
gh run view <run-id>

# Download artifacts
gh run download <run-id>
```

**Check status:**

```bash
# Latest run status
gh run view --workflow=precision-tracking.yml
```

### Regression Detection

The CI automatically:
1. Compares current vs previous precision
2. Fails if drop > 5%
3. Comments on PR if regression detected
4. Creates alerts

**Example PR comment:**

```
❌ CRITICAL PRECISION REGRESSION DETECTED

- Previous: 40.5%
- Current: 34.2%
- Change: -6.3%

Please review the changes that caused this regression.
```

## Interpreting Results

### Good Results (Deterministic)

```json
{
  "summary": {
    "precision_score": 95.0,
    "determinism_score": 100.0,
    "gap_to_target": 3.0
  },
  "task_count": {"std": 0.0},
  "atom_count": {"std": 0.0},
  "success_rate": {"std": 0.0},
  "determinism_violations": {
    "total_violations": 0,
    "determinism_percentage": 100.0
  }
}
```

✅ **Interpretation:**
- All iterations produce identical results
- High success rate
- Near target

### Bad Results (Non-deterministic)

```json
{
  "summary": {
    "precision_score": 38.0,
    "determinism_score": 30.0,
    "gap_to_target": 60.0
  },
  "task_count": {"std": 2.5},
  "atom_count": {"std": 3.1},
  "success_rate": {"std": 8.2},
  "determinism_violations": {
    "total_violations": 21,
    "determinism_percentage": 30.0
  }
}
```

❌ **Problems:**
- Task/atom counts vary (non-deterministic)
- Low determinism percentage
- High variance in success rate
- Large gap to target

## Debugging Non-Determinism

### Check Temperature Settings

```python
# In LLM calls - verify temperature=0
llm_client.generate(
    temperature=0.0,  # Must be 0 for determinism
    seed=42           # Fixed seed
)
```

### Check Random Operations

```python
# All random operations must use fixed seed
import random
random.seed(42)
```

### Check Timestamps

```python
# Avoid datetime.now() in deterministic paths
# Use fixed timestamps or exclude from hashing
```

### Check Sorting

```python
# Always sort before hashing
atoms_sorted = sorted(atoms, key=lambda a: a.get("atom_id"))
```

## Monitoring Phase Progress

### Phase Definitions

| Phase | Precision Range | Status |
|-------|----------------|--------|
| 1 - Baseline | 0-50% | Current baseline |
| 2 - Validation Gates | 50-70% | Add validation |
| 3 - Recovery | 70-85% | Add retry logic |
| 4 - Stability | 85-95% | Optimize reliability |
| 5 - Excellence | 95-98%+ | Target achieved |

### Track Progress

```bash
# Check current phase
curl http://localhost:8000/api/dashboard/precision | jq '.metrics.phase'

# View progress
curl http://localhost:8000/api/dashboard/precision | jq '.metrics | {
  current: .current_precision,
  phase: .phase,
  gap: .gap_to_target
}'
```

## Troubleshooting

### Baseline Script Fails

**Error:** `DiscoveryDocument not found`

**Solution:**
```bash
# Check database connection
psql -h localhost -U devmatrix_test -d devmatrix_test -c "SELECT 1"

# Run migrations
alembic upgrade head
```

**Error:** `No module named 'src'`

**Solution:**
```bash
# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root
cd /path/to/agentic-ai
python scripts/measure_precision_baseline.py
```

### Tests Fail

**Error:** `asyncio runtime error`

**Solution:**
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Add to pytest.ini
[pytest]
asyncio_mode = auto
```

**Error:** `Database connection refused`

**Solution:**
```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.test.yml ps postgres-test

# Check connection
PGPASSWORD=devmatrix_test psql -h localhost -p 5433 -U devmatrix_test -c "SELECT 1"
```

### Dashboard Returns Empty

**Error:** `No executions found`

**Solution:**
```bash
# Run baseline first to create data
python scripts/measure_precision_baseline.py --iterations 3

# Verify data
psql -h localhost -U devmatrix_test -d devmatrix_test -c "SELECT COUNT(*) FROM masterplans"
```

## Best Practices

### Before Each Phase

1. **Run baseline measurement** to establish current precision
2. **Save reports** for comparison
3. **Document baseline** in phase documentation
4. **Set phase target** (e.g., "Phase 2: reach 65%")

### During Development

1. **Run determinism tests** after code changes
2. **Check for regressions** before committing
3. **Monitor dashboard** for trends
4. **Fix violations immediately** (don't accumulate)

### After Each Phase

1. **Run full baseline** (20+ iterations)
2. **Generate comparison report** vs previous phase
3. **Verify improvement** meets phase target
4. **Update documentation** with results

## Next Steps

1. ✅ **Setup Complete**: Infrastructure ready
2. 🎯 **Run Baseline**: Establish current 38% baseline
3. 📊 **Monitor Dashboard**: Track progress
4. 🔬 **Phase 1**: Implement validation gates
5. 📈 **Iterate**: Measure → Improve → Measure

## Support

**Questions?** Check:
- [ROADMAP_PRECISION_98.md](./DOCS/ROADMAP_PRECISION_98.md) - Implementation plan
- [MASTERPLAN_DESIGN.md](./DOCS/MASTERPLAN_DESIGN.md) - System architecture
- GitHub Issues - Report problems

**Need help?**
```bash
# Check script help
python scripts/measure_precision_baseline.py --help

# Check test options
pytest tests/test_determinism.py --help

# View Docker logs
docker-compose -f docker-compose.test.yml logs baseline
```
