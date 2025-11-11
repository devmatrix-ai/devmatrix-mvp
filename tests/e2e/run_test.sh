#!/bin/bash
#
# Run MGE V2 E2E Tests
#
# Usage:
#   ./run_test.sh              # Run all E2E tests
#   ./run_test.sh --fast       # Run only benchmark
#   ./run_test.sh --full       # Run complete pipeline test
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}MGE V2 E2E Test Runner${NC}"
echo -e "${GREEN}================================${NC}\n"

# Check prerequisites
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}\n"

# 1. Check PostgreSQL
if ! docker exec devmatrix-postgres pg_isready -U devmatrix > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL not running${NC}"
    echo "   Starting PostgreSQL..."
    docker-compose up -d devmatrix-postgres
    sleep 5
fi
echo -e "${GREEN}✅ PostgreSQL running${NC}"

# 2. Check test database
if ! docker exec devmatrix-postgres psql -U devmatrix -lqt | cut -d \| -f 1 | grep -qw devmatrix_test; then
    echo -e "${YELLOW}⚠️  Test database not found, creating...${NC}"
    docker exec devmatrix-postgres createdb -U devmatrix devmatrix_test
fi
echo -e "${GREEN}✅ Test database exists${NC}"

# 3. Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}❌ ANTHROPIC_API_KEY not set${NC}"
    echo "   Please set it in .env or export it:"
    echo "   export ANTHROPIC_API_KEY='sk-ant-...'"
    exit 1
fi
echo -e "${GREEN}✅ API key configured${NC}\n"

# Parse arguments
TEST_TYPE="all"
if [ "$1" == "--fast" ]; then
    TEST_TYPE="benchmark"
elif [ "$1" == "--full" ]; then
    TEST_TYPE="full"
fi

# Run tests
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🚀 Running Tests${NC}"
echo -e "${GREEN}================================${NC}\n"

cd "$(dirname "$0")/../.."

case $TEST_TYPE in
    "benchmark")
        echo -e "${YELLOW}Running performance benchmark only...${NC}\n"
        pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_mge_v2_performance_benchmark \
            -v -s --tb=short \
            -m benchmark
        ;;

    "full")
        echo -e "${YELLOW}Running complete pipeline test...${NC}\n"
        pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_complete_mge_v2_pipeline_fastapi \
            -v -s --tb=short \
            -m e2e
        ;;

    "all")
        echo -e "${YELLOW}Running all E2E tests...${NC}\n"
        pytest tests/e2e/ \
            -v -s --tb=short \
            -m e2e
        ;;
esac

TEST_EXIT_CODE=$?

# Summary
echo -e "\n${GREEN}================================${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Tests PASSED!${NC}"
else
    echo -e "${RED}❌ Tests FAILED${NC}"
fi
echo -e "${GREEN}================================${NC}\n"

# Cleanup prompt
echo -e "${YELLOW}Cleanup test data?${NC}"
echo "  1. Keep test data (default)"
echo "  2. Clean workspace only"
echo "  3. Clean everything (workspace + DB)"
echo -n "Choice [1]: "
read -t 10 CLEANUP_CHOICE || CLEANUP_CHOICE="1"

case $CLEANUP_CHOICE in
    "2")
        echo -e "\n${YELLOW}Cleaning workspace...${NC}"
        rm -rf /tmp/mge_v2_workspace/*
        echo -e "${GREEN}✅ Workspace cleaned${NC}"
        ;;

    "3")
        echo -e "\n${YELLOW}Cleaning everything...${NC}"
        rm -rf /tmp/mge_v2_workspace/*
        docker exec devmatrix-postgres psql -U devmatrix -c "DROP DATABASE IF EXISTS devmatrix_test"
        docker exec devmatrix-postgres createdb -U devmatrix devmatrix_test
        echo -e "${GREEN}✅ Everything cleaned${NC}"
        ;;

    *)
        echo -e "\n${GREEN}Test data preserved${NC}"
        echo "Workspace: /tmp/mge_v2_workspace/"
        echo "Database: devmatrix_test"
        ;;
esac

exit $TEST_EXIT_CODE
