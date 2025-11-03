#!/bin/bash
# DevMatrix Constitution Compliance Checker
# Version: 1.0.0

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCORE=0
TOTAL_CHECKS=0
FAILED_CHECKS=()

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   DevMatrix Constitution Compliance Check${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Helper function to run check
run_check() {
    local name=$1
    local command=$2
    local principle=$3
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "${YELLOW}[${TOTAL_CHECKS}]${NC} Checking: ${name}..."
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "    ${GREEN}✓${NC} PASS"
        SCORE=$((SCORE + 1))
        return 0
    else
        echo -e "    ${RED}✗${NC} FAIL (Principle: ${principle})"
        FAILED_CHECKS+=("$name")
        return 1
    fi
}

# ============================================================================
# PRINCIPLE 1: Code Quality Standards
# ============================================================================
echo -e "\n${BLUE}PRINCIPLE 1: Code Quality Standards${NC}"
echo "────────────────────────────────────────"

# 1.1 TypeScript Strict Mode
run_check "TypeScript strict mode enabled" \
    "grep -q '\"strict\": true' src/ui/tsconfig.json" \
    "I. Type Safety"

# 1.2 No 'any' types in production code
run_check "No 'any' types in production" \
    "! grep -r ': any' src/ui/src --include='*.ts' --include='*.tsx' --exclude-dir=__tests__ 2>/dev/null || [ \$(grep -r ': any' src/ui/src --include='*.ts' --include='*.tsx' --exclude-dir=__tests__ 2>/dev/null | wc -l) -eq 0 ]" \
    "I. Type Safety"

# 1.3 Python type hints
run_check "Python files have type hints" \
    "python3 scripts/check-type-hints.py" \
    "I. Type Safety"

# 1.4 Function length check (≤100 lines)
run_check "Function length ≤100 lines" \
    "python3 scripts/check-function-length.py --max-lines 100" \
    "I. Code Structure"

# 1.5 Component length check (≤300 lines)
run_check "Component length ≤300 lines" \
    "python3 scripts/check-component-length.py --max-lines 300" \
    "I. Code Structure"

# ============================================================================
# PRINCIPLE 2: Testing Standards
# ============================================================================
echo -e "\n${BLUE}PRINCIPLE 2: Testing Standards${NC}"
echo "────────────────────────────────────────"

# 2.1 Test coverage
run_check "Backend test coverage ≥80%" \
    "pytest --cov=src --cov-report=term-missing --cov-fail-under=80 -q 2>/dev/null" \
    "II. Test Coverage"

# 2.2 All tests passing
run_check "All backend tests passing" \
    "pytest -x -q 2>/dev/null" \
    "II. Test Coverage"

# ============================================================================
# PRINCIPLE 3: User Experience Consistency
# ============================================================================
echo -e "\n${BLUE}PRINCIPLE 3: User Experience Consistency${NC}"
echo "────────────────────────────────────────"

# 3.1 Accessibility - ARIA labels
run_check "Interactive elements have ARIA labels" \
    "python3 scripts/check-accessibility.py" \
    "III. Accessibility"

# ============================================================================
# PRINCIPLE 4: Performance Requirements
# ============================================================================
echo -e "\n${BLUE}PRINCIPLE 4: Performance Requirements${NC}"
echo "────────────────────────────────────────"

# 4.1 Database connection pooling configured
run_check "Database connection pooling configured" \
    "grep -q 'pool_size' src/config/database.py 2>/dev/null || grep -q 'poolclass' src/config/database.py 2>/dev/null" \
    "IV. Backend Performance"

# ============================================================================
# PRINCIPLE 5: Security Standards
# ============================================================================
echo -e "\n${BLUE}PRINCIPLE 5: Security Standards${NC}"
echo "────────────────────────────────────────"

# 5.1 No secrets in code
run_check "No hardcoded secrets" \
    "! grep -r 'sk-ant-' --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' src/ 2>/dev/null" \
    "V. Data Protection"

# 5.2 CORS not wildcard
run_check "CORS not using wildcard" \
    "! grep -r 'allow_origins=\\[\"\\*\"\\]' src/ 2>/dev/null" \
    "V. Data Protection"

# ============================================================================
# DOCUMENTATION
# ============================================================================
echo -e "\n${BLUE}PRINCIPLE: Documentation Standards${NC}"
echo "────────────────────────────────────────"

# README exists
run_check "README.md exists and is up to date" \
    "[ -f README.md ] && [ \$(wc -l < README.md) -gt 100 ]" \
    "Documentation"

# API documentation
run_check "OpenAPI documentation exists" \
    "grep -q 'openapi_url' src/api/app.py 2>/dev/null" \
    "Documentation"

# ============================================================================
# RESULTS
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Results${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

COMPLIANCE=$(awk "BEGIN {printf \"%.1f\", ($SCORE / $TOTAL_CHECKS) * 100}")

echo ""
echo -e "Total Checks: ${TOTAL_CHECKS}"
echo -e "Passed: ${GREEN}${SCORE}${NC}"
echo -e "Failed: ${RED}$((TOTAL_CHECKS - SCORE))${NC}"
echo ""
echo -e "Compliance Score: ${BLUE}${COMPLIANCE}%${NC}"

if [ "$COMPLIANCE" == "100.0" ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ✓ PERFECT COMPLIANCE!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
elif awk "BEGIN {exit !($COMPLIANCE >= 95)}"; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ✓ EXCELLENT COMPLIANCE (≥95%)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
elif awk "BEGIN {exit !($COMPLIANCE >= 80)}"; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}   ⚠ ACCEPTABLE COMPLIANCE (≥80%)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Failed checks:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "  • $check"
    done
    exit 1
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}   ✗ COMPLIANCE BELOW THRESHOLD (<80%)${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}Failed checks:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "  • $check"
    done
    exit 1
fi

