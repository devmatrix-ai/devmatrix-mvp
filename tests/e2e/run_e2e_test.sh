#!/bin/bash
# =============================================================================
# E2E Pipeline Test Runner
# Complete spec-to-deployment testing with granular metrics
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
TEST_NAME="${1:-simple_crud_api}"
SPEC_FILE="${2:-agent-os/specs/simple_crud_api.md}"
DASHBOARD_MODE="${3:-mock}"  # mock or live

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           E2E PIPELINE TEST EXECUTION FRAMEWORK                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Step 1: Pre-flight Checks
# =============================================================================
echo -e "${BLUE}[1/9] Running Pre-flight Checks...${NC}"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
if (( $(echo "$python_version < 3.11" | bc -l) )); then
    echo -e "${RED}✗ Python 3.11+ required (found $python_version)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version: $python_version${NC}"

# Check databases
check_database() {
    local name=$1
    local command=$2

    if eval "$command" 2>/dev/null; then
        echo -e "${GREEN}✓ $name is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $name is not running${NC}"
        return 1
    fi
}

# Neo4j check
check_database "Neo4j" "curl -s http://localhost:7474 > /dev/null"

# Qdrant check
check_database "Qdrant" "curl -s http://localhost:6333/health > /dev/null"

# PostgreSQL check
check_database "PostgreSQL" "pg_isready -h localhost -p 5432 > /dev/null"

echo ""

# =============================================================================
# Step 2: Environment Setup
# =============================================================================
echo -e "${BLUE}[2/9] Setting up test environment...${NC}"

# Export environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export E2E_TEST_MODE="true"
export COGNITIVE_REQUIRED="true"
export MGE_V2_FALLBACK="false"
export ORCHESTRATION_PIPELINE="cognitive"
export LOG_LEVEL="INFO"

# Create test directories
mkdir -p tests/e2e/results
mkdir -p tests/e2e/logs
mkdir -p tests/e2e/metrics

echo -e "${GREEN}✓ Environment configured${NC}"
echo ""

# =============================================================================
# Step 3: Install Dependencies
# =============================================================================
echo -e "${BLUE}[3/9] Checking dependencies...${NC}"

# Check required Python packages
packages_missing=false
for package in rich websockets psutil pytest pytest-asyncio; do
    if ! python3 -c "import $package" 2>/dev/null; then
        echo -e "${YELLOW}Installing $package...${NC}"
        pip install $package --quiet
    fi
done

echo -e "${GREEN}✓ Dependencies verified${NC}"
echo ""

# =============================================================================
# Step 4: Validate Pattern Bank
# =============================================================================
echo -e "${BLUE}[4/9] Validating Pattern Bank...${NC}"

python3 -c "
import sys
sys.path.append('.')
from src.cognitive.patterns.pattern_bank import PatternBank

pb = PatternBank()
neo4j_count = pb.get_pattern_count()
print(f'Neo4j patterns: {neo4j_count}')

if neo4j_count < 1000:
    print('⚠ Warning: Low pattern count in Neo4j')
else:
    print('✓ Pattern Bank validated')
" || echo -e "${YELLOW}⚠ Pattern Bank validation skipped${NC}"

echo ""

# =============================================================================
# Step 5: Start Dashboard (in background)
# =============================================================================
echo -e "${BLUE}[5/9] Starting Progress Dashboard...${NC}"

if [ "$DASHBOARD_MODE" = "mock" ]; then
    # Run mock dashboard in background
    python3 tests/e2e/progress_dashboard.py --mock --duration 300 > tests/e2e/logs/dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    echo -e "${GREEN}✓ Mock dashboard started (PID: $DASHBOARD_PID)${NC}"
else
    # Live dashboard would connect to WebSocket
    echo -e "${YELLOW}⚠ Live dashboard mode requires WebSocket server${NC}"
fi

echo ""

# =============================================================================
# Step 6: Execute E2E Test
# =============================================================================
echo -e "${BLUE}[6/9] Executing E2E Pipeline Test...${NC}"
echo -e "${CYAN}Test: $TEST_NAME${NC}"
echo -e "${CYAN}Spec: $SPEC_FILE${NC}"
echo ""

# Run the main test orchestrator
TEST_START=$(date +%s)

python3 tests/e2e/pipeline_e2e_orchestrator.py 2>&1 | tee tests/e2e/logs/test_execution.log

TEST_END=$(date +%s)
TEST_DURATION=$((TEST_END - TEST_START))

echo ""
echo -e "${GREEN}✓ Test execution completed in ${TEST_DURATION} seconds${NC}"
echo ""

# =============================================================================
# Step 7: Collect Metrics
# =============================================================================
echo -e "${BLUE}[7/9] Collecting Test Metrics...${NC}"

# Find the latest metrics file
METRICS_FILE=$(ls -t e2e_metrics_*.json 2>/dev/null | head -1)

if [ -f "$METRICS_FILE" ]; then
    # Parse key metrics
    python3 -c "
import json
with open('$METRICS_FILE') as f:
    metrics = json.load(f)

print('📊 Key Metrics:')
print(f'  • Overall Status: {metrics.get(\"overall_status\", \"unknown\").upper()}')
print(f'  • Total Duration: {metrics.get(\"total_duration_ms\", 0) / 1000 / 60:.1f} minutes')
print(f'  • Pattern Reuse Rate: {metrics.get(\"pattern_reuse_rate\", 0):.1%}')
print(f'  • Test Coverage: {metrics.get(\"test_coverage\", 0):.1%}')
print(f'  • Errors Recovered: {metrics.get(\"recovered_errors\", 0)}/{metrics.get(\"total_errors\", 0)}')
print(f'  • Peak Memory: {metrics.get(\"peak_memory_mb\", 0):.1f} MB')
print(f'  • Peak CPU: {metrics.get(\"peak_cpu_percent\", 0):.1f}%')
"

    # Move metrics to results directory
    mv "$METRICS_FILE" tests/e2e/metrics/
    echo -e "${GREEN}✓ Metrics saved to tests/e2e/metrics/${NC}"
else
    echo -e "${YELLOW}⚠ No metrics file found${NC}"
fi

echo ""

# =============================================================================
# Step 8: Generate Test Report
# =============================================================================
echo -e "${BLUE}[8/9] Generating Test Report...${NC}"

REPORT_FILE="tests/e2e/results/report_$(date +%Y%m%d_%H%M%S).md"

cat > "$REPORT_FILE" << EOF
# E2E Pipeline Test Report

**Date**: $(date)
**Test**: $TEST_NAME
**Spec**: $SPEC_FILE
**Duration**: ${TEST_DURATION} seconds

## Test Results

### Phase Completion Status
\`\`\`
$(grep "Phase Completed" tests/e2e/logs/test_execution.log || echo "No phase data available")
\`\`\`

### Error Summary
\`\`\`
$(grep "ERROR\|CRITICAL" tests/e2e/logs/test_execution.log | head -10 || echo "No errors detected")
\`\`\`

### Performance Metrics
- Execution Time: ${TEST_DURATION}s
- Expected Time: 360s (6 minutes for simple CRUD)
- Performance Score: $(echo "scale=2; 100 * (360 / $TEST_DURATION)" | bc)%

## Recommendations

$(if [ $TEST_DURATION -gt 420 ]; then
    echo "⚠️ Performance degradation detected. Consider:"
    echo "- Optimizing wave execution parallelization"
    echo "- Reviewing Pattern Bank query performance"
    echo "- Checking database connection pooling"
else
    echo "✅ Performance within acceptable range"
fi)

## Next Steps
1. Review detailed metrics in tests/e2e/metrics/
2. Check execution logs in tests/e2e/logs/
3. Analyze any failed checkpoints for improvements

---
*Generated by E2E Test Framework*
EOF

echo -e "${GREEN}✓ Report saved to $REPORT_FILE${NC}"
echo ""

# =============================================================================
# Step 9: Cleanup
# =============================================================================
echo -e "${BLUE}[9/9] Cleaning up...${NC}"

# Kill dashboard if running
if [ ! -z "$DASHBOARD_PID" ]; then
    kill $DASHBOARD_PID 2>/dev/null || true
    echo -e "${GREEN}✓ Dashboard stopped${NC}"
fi

# Archive logs
tar -czf "tests/e2e/logs/archive_$(date +%Y%m%d_%H%M%S).tar.gz" \
    tests/e2e/logs/*.log 2>/dev/null || true

# Clean temporary files
rm -f *.log 2>/dev/null || true

echo -e "${GREEN}✓ Cleanup completed${NC}"
echo ""

# =============================================================================
# Final Summary
# =============================================================================
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    TEST EXECUTION SUMMARY                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ -f "tests/e2e/metrics/$(basename $METRICS_FILE)" ]; then
    python3 -c "
import json
with open('tests/e2e/metrics/$(basename $METRICS_FILE)') as f:
    metrics = json.load(f)
    status = metrics.get('overall_status', 'unknown')

    if status == 'success':
        print('🎉 TEST PASSED - All phases completed successfully')
        exit(0)
    elif status == 'partial_success':
        print('⚠️  TEST PARTIALLY PASSED - Some non-critical failures')
        exit(1)
    else:
        print('❌ TEST FAILED - Critical errors detected')
        exit(2)
"
    EXIT_CODE=$?
else
    echo -e "${RED}❌ TEST INCOMPLETE - No metrics available${NC}"
    EXIT_CODE=3
fi

echo ""
echo -e "${CYAN}Full report: $REPORT_FILE${NC}"
echo -e "${CYAN}Metrics: tests/e2e/metrics/${NC}"
echo -e "${CYAN}Logs: tests/e2e/logs/${NC}"
echo ""

exit $EXIT_CODE