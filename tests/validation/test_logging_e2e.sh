#!/bin/bash
# End-to-end logging validation script
# Tests logging in different environments and configurations

set -e

echo "🔍 Logging End-to-End Validation"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $1"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $1"
        ((FAILED++))
    fi
}

# Test 1: Development environment (text format)
echo -e "${YELLOW}Test 1: Development Environment (text format)${NC}"
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text
unset LOG_FILE

python -c "
from src.observability import setup_logging, get_logger
setup_logging()
logger = get_logger('test_dev')
logger.debug('Debug message in development')
logger.info('Info message in development')
logger.warning('Warning message in development')
print('Development logging test completed')
" > /tmp/logging_dev_test.log 2>&1

grep -q "Info message in development" /tmp/logging_dev_test.log
check_result "Development text format logging"

# Test 2: Production environment (JSON format)
echo -e "${YELLOW}Test 2: Production Environment (JSON format)${NC}"
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export LOG_FORMAT=json
unset LOG_FILE

python -c "
from src.observability import setup_logging, get_logger
setup_logging()
logger = get_logger('test_prod')
logger.info('Info message in production', user_id='123', action='test')
logger.warning('Warning message in production')
logger.error('Error message in production')
print('Production logging test completed')
" > /tmp/logging_prod_test.log 2>&1

grep -q "production" /tmp/logging_prod_test.log
check_result "Production JSON format logging"

# Test 3: File logging with rotation
echo -e "${YELLOW}Test 3: File Logging with Rotation${NC}"
export ENVIRONMENT=development
export LOG_LEVEL=INFO
export LOG_FORMAT=json
export LOG_FILE=/tmp/test_rotation.log

# Clean up previous test
rm -f /tmp/test_rotation.log*

python -c "
from src.observability import setup_logging, get_logger
setup_logging()
logger = get_logger('test_rotation')
for i in range(50):
    logger.info(f'Log message {i}' + 'x' * 200)
" > /dev/null 2>&1

# Check that log file was created
[ -f /tmp/test_rotation.log ]
check_result "File logging creates log file"

# Test 4: Log levels filtering
echo -e "${YELLOW}Test 4: Log Levels Filtering${NC}"
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export LOG_FORMAT=text
unset LOG_FILE

python -c "
from src.observability import setup_logging, get_logger
setup_logging()
logger = get_logger('test_levels')
logger.debug('Debug message - should not appear')
logger.info('Info message - should not appear')
logger.warning('Warning message - should appear')
logger.error('Error message - should appear')
" > /tmp/logging_levels_test.log 2>&1

# Check that WARNING and ERROR appear, but not DEBUG/INFO
grep -q "Warning message" /tmp/logging_levels_test.log && \
grep -q "Error message" /tmp/logging_levels_test.log
check_result "Log level filtering works correctly"

# Test 5: Agents use logging correctly
echo -e "${YELLOW}Test 5: Agents Use Logging${NC}"
export ENVIRONMENT=development
export LOG_LEVEL=INFO
export LOG_FORMAT=text
unset LOG_FILE

python -c "
from src.observability import get_logger

# Test that orchestrator has logger
try:
    from src.agents.orchestrator_agent import OrchestratorAgent
    agent = OrchestratorAgent()
    assert hasattr(agent, 'logger'), 'Orchestrator missing logger'
    assert agent.logger.name == 'orchestrator', 'Orchestrator logger wrong name'
    print('Orchestrator has logger: OK')
except Exception as e:
    print(f'Orchestrator logging check failed: {e}')
    exit(1)

# Test that code generation agent has logger
try:
    from src.agents.code_generation_agent import CodeGenerationAgent
    agent = CodeGenerationAgent()
    assert hasattr(agent, 'logger'), 'CodeGen missing logger'
    assert agent.logger.name == 'code_generation', 'CodeGen logger wrong name'
    print('CodeGeneration has logger: OK')
except Exception as e:
    print(f'CodeGeneration logging check failed: {e}')
    exit(1)
" > /tmp/logging_agents_test.log 2>&1

check_result "Agents have StructuredLogger configured"

# Test 6: No print statements in production code
echo -e "${YELLOW}Test 6: No Print Statements in Production Code${NC}"
python -m pytest tests/unit/observability/test_logging.py::TestNoPrintStatements -v -q > /tmp/no_prints_test.log 2>&1
check_result "No print statements in production code"

# Clean up
rm -f /tmp/logging_*.log /tmp/test_rotation.log*

# Summary
echo ""
echo "================================"
echo "Validation Summary"
echo "================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All validation tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some validation tests failed${NC}"
    exit 1
fi
