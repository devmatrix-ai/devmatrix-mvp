#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# validate-masterplan-sync.sh
#
# Quick validation script for MasterPlan Progress Modal synchronization
# Checks all critical points in the data flow
#
# Usage: ./validate-masterplan-sync.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

# ───────────────────────────────────────────────────────────────────────────
# Helper functions
# ───────────────────────────────────────────────────────────────────────────

print_header() {
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

check_pass() {
  echo -e "${GREEN}✅ $1${NC}"
  ((CHECKS_PASSED++))
}

check_fail() {
  echo -e "${RED}❌ $1${NC}"
  ((CHECKS_FAILED++))
}

check_warn() {
  echo -e "${YELLOW}⚠️  $1${NC}"
  ((CHECKS_WARNED++))
}

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION SUITE
# ═══════════════════════════════════════════════════════════════════════════════

print_header "🔍 MasterPlan Progress Modal Validation Suite"

# ───────────────────────────────────────────────────────────────────────────
# Check 1: File Structure
# ───────────────────────────────────────────────────────────────────────────

print_header "1️⃣  FILE STRUCTURE VALIDATION"

# Check critical files exist
declare -a CRITICAL_FILES=(
  "src/ui/src/components/chat/MasterPlanProgressModal.tsx"
  "src/ui/src/hooks/useMasterPlanProgress.ts"
  "src/ui/src/hooks/useChat.ts"
  "src/ui/src/providers/WebSocketProvider.tsx"
  "src/ui/src/stores/masterplanStore.ts"
  "src/websocket/manager.py"
  "src/api/routers/websocket.py"
)

for file in "${CRITICAL_FILES[@]}"; do
  if [ -f "$file" ]; then
    check_pass "Found: $file"
  else
    check_fail "Missing: $file"
  fi
done

# ───────────────────────────────────────────────────────────────────────────
# Check 2: Code Quality - React Hooks
# ───────────────────────────────────────────────────────────────────────────

print_header "2️⃣  REACT HOOKS VALIDATION"

# Check useChat has 16 listeners
LISTENER_COUNT=$(grep -c "const cleanup[0-9]" src/ui/src/hooks/useChat.ts 2>/dev/null || echo 0)
if [ "$LISTENER_COUNT" -ge 16 ]; then
  check_pass "useChat has $LISTENER_COUNT event listeners (expected 16)"
else
  check_warn "useChat has only $LISTENER_COUNT event listeners (expected 16)"
fi

# Check useMasterPlanProgress has state machine
if grep -q "switch (event.type)" src/ui/src/hooks/useMasterPlanProgress.ts 2>/dev/null; then
  check_pass "useMasterPlanProgress has state machine switch"
else
  check_fail "useMasterPlanProgress missing state machine"
fi

# Check for deduplication logic
if grep -q "lastProcessedEventRef" src/ui/src/hooks/useMasterPlanProgress.ts 2>/dev/null; then
  check_pass "Event deduplication implemented (lastProcessedEventRef)"
else
  check_warn "Event deduplication may not be implemented"
fi

# ───────────────────────────────────────────────────────────────────────────
# Check 3: Event Types
# ───────────────────────────────────────────────────────────────────────────

print_header "3️⃣  EVENT TYPES COVERAGE"

declare -a REQUIRED_EVENTS=(
  "discovery_generation_start"
  "discovery_tokens_progress"
  "discovery_entity_discovered"
  "discovery_parsing_complete"
  "discovery_saving_start"
  "discovery_generation_complete"
  "masterplan_generation_start"
  "masterplan_tokens_progress"
  "masterplan_entity_discovered"
  "masterplan_parsing_complete"
  "masterplan_validation_start"
  "masterplan_saving_start"
  "masterplan_generation_complete"
)

for event in "${REQUIRED_EVENTS[@]}"; do
  if grep -q "$event" src/ui/src/hooks/useChat.ts 2>/dev/null; then
    check_pass "Handler for $event"
  else
    check_fail "Missing handler for $event"
  fi
done

# ───────────────────────────────────────────────────────────────────────────
# Check 4: State Management (Zustand)
# ───────────────────────────────────────────────────────────────────────────

print_header "4️⃣  STATE MANAGEMENT VALIDATION"

# Check Zustand store structure
if grep -q "export const useMasterPlanStore" src/ui/src/stores/masterplanStore.ts 2>/dev/null; then
  check_pass "Zustand store exported correctly"
else
  check_fail "Zustand store not exported"
fi

# Check localStorage persistence
if grep -q "persist" src/ui/src/stores/masterplanStore.ts 2>/dev/null; then
  check_pass "Zustand store has persistence"
else
  check_warn "Zustand store may not persist state"
fi

# Check key store actions exist
declare -a STORE_ACTIONS=(
  "updateProgress"
  "setPhases"
  "updateMetrics"
  "startGeneration"
  "endGeneration"
)

for action in "${STORE_ACTIONS[@]}"; do
  if grep -q "$action" src/ui/src/stores/masterplanStore.ts 2>/dev/null; then
    check_pass "Store action: $action"
  else
    check_fail "Missing store action: $action"
  fi
done

# ───────────────────────────────────────────────────────────────────────────
# Check 5: Backend Integration (Python)
# ───────────────────────────────────────────────────────────────────────────

print_header "5️⃣  BACKEND INTEGRATION VALIDATION"

# Check WebSocket manager has all event emitters
declare -a EMIT_METHODS=(
  "emit_discovery_generation_start"
  "emit_discovery_tokens_progress"
  "emit_discovery_entity_discovered"
  "emit_masterplan_generation_start"
  "emit_masterplan_tokens_progress"
  "emit_masterplan_generation_complete"
)

for method in "${EMIT_METHODS[@]}"; do
  if grep -q "$method" src/websocket/manager.py 2>/dev/null; then
    check_pass "Backend method: $method"
  else
    check_warn "Backend method may be missing: $method"
  fi
done

# Check room joining logic
if grep -q "room=" src/websocket/manager.py 2>/dev/null; then
  check_pass "WebSocket room logic implemented"
else
  check_fail "WebSocket room logic missing"
fi

# ───────────────────────────────────────────────────────────────────────────
# Check 6: Component Structure
# ───────────────────────────────────────────────────────────────────────────

print_header "6️⃣  COMPONENT STRUCTURE VALIDATION"

# Check modal has required sections
declare -a MODAL_ELEMENTS=(
  "role=\"dialog\""
  "MasterPlanProgressModal"
  "ProgressTimeline"
  "ProgressMetrics"
  "ErrorPanel"
  "FinalSummary"
)

for element in "${MODAL_ELEMENTS[@]}"; do
  if grep -q "$element" src/ui/src/components/chat/MasterPlanProgressModal.tsx 2>/dev/null; then
    check_pass "Modal has: $element"
  else
    check_fail "Modal missing: $element"
  fi
done

# Check for Suspense boundaries
if grep -q "React.Suspense" src/ui/src/components/chat/MasterPlanProgressModal.tsx 2>/dev/null; then
  check_pass "Lazy loading with Suspense implemented"
else
  check_warn "Lazy loading may not be implemented"
fi

# ───────────────────────────────────────────────────────────────────────────
# Check 7: Error Handling
# ───────────────────────────────────────────────────────────────────────────

print_header "7️⃣  ERROR HANDLING VALIDATION"

# Check error state handling
if grep -q "isError" src/ui/src/components/chat/MasterPlanProgressModal.tsx 2>/dev/null; then
  check_pass "Error state handling in modal"
else
  check_warn "Error state handling may be incomplete"
fi

# Check retry logic
if grep -q "handleRetry\|clearError" src/ui/src/components/chat/MasterPlanProgressModal.tsx 2>/dev/null; then
  check_pass "Retry and error clearing logic present"
else
  check_warn "Retry logic may be missing"
fi

# ───────────────────────────────────────────────────────────────────────────
# Check 8: Testing
# ───────────────────────────────────────────────────────────────────────────

print_header "8️⃣  TEST COVERAGE VALIDATION"

if [ -f "src/ui/tests/MasterPlanProgressModal.e2e.test.ts" ]; then
  check_pass "E2E test file exists"
  TEST_COUNT=$(grep -c "test('" src/ui/tests/MasterPlanProgressModal.e2e.test.ts 2>/dev/null || echo 0)
  check_pass "Found $TEST_COUNT test cases"
else
  check_fail "E2E test file missing"
fi

if [ -f "src/ui/tests/debug-masterplan-flow.ts" ]; then
  check_pass "Debug utility exists"
else
  check_warn "Debug utility missing"
fi

# ───────────────────────────────────────────────────────────────────────────
# Check 9: Dependencies
# ───────────────────────────────────────────────────────────────────────────

print_header "9️⃣  DEPENDENCY VALIDATION"

if [ -f "src/ui/package.json" ]; then
  if grep -q "react" src/ui/package.json 2>/dev/null; then
    check_pass "React dependency found"
  else
    check_fail "React dependency missing"
  fi

  if grep -q "zustand" src/ui/package.json 2>/dev/null; then
    check_pass "Zustand dependency found"
  else
    check_fail "Zustand dependency missing"
  fi

  if grep -q "socket.io-client" src/ui/package.json 2>/dev/null; then
    check_pass "Socket.IO client dependency found"
  else
    check_warn "Socket.IO client dependency may be missing"
  fi
else
  check_warn "package.json not found"
fi

# ───────────────────────────────────────────────────────────────────────────
# Check 10: Documentation
# ───────────────────────────────────────────────────────────────────────────

print_header "🔟 DOCUMENTATION VALIDATION"

if [ -f "MASTERPLAN_PROGRESS_DEBUGGING_GUIDE.md" ]; then
  check_pass "Debugging guide found"
else
  check_warn "Debugging guide missing"
fi

declare -a DOC_SECTIONS=(
  "Quick Start"
  "Flujo de Datos"
  "Tests"
  "Debugging"
  "Issues"
)

if [ -f "MASTERPLAN_PROGRESS_DEBUGGING_GUIDE.md" ]; then
  for section in "${DOC_SECTIONS[@]}"; do
    if grep -q "$section" MASTERPLAN_PROGRESS_DEBUGGING_GUIDE.md 2>/dev/null; then
      check_pass "Documentation covers: $section"
    fi
  done
fi

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print_header "📊 VALIDATION SUMMARY"

TOTAL=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNED))
PASS_PERCENT=$((CHECKS_PASSED * 100 / TOTAL))

echo ""
echo "Total Checks: $TOTAL"
echo -e "  ${GREEN}Passed: $CHECKS_PASSED${NC}"
echo -e "  ${RED}Failed: $CHECKS_FAILED${NC}"
echo -e "  ${YELLOW}Warned: $CHECKS_WARNED${NC}"
echo ""
echo "Pass Rate: $PASS_PERCENT%"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ All critical checks passed!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Start the app and test the MasterPlan generation"
  echo "  2. Open DevTools console (F12)"
  echo "  3. Import the debugger:"
  echo "     import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'"
  echo "     setupMasterPlanDebugger()"
  echo "  4. Generate a MasterPlan"
  echo "  5. Run: window.__masterplanDebug.analyze()"
  echo ""
  exit 0
else
  echo -e "${RED}❌ Some checks failed. Please review the errors above.${NC}"
  echo ""
  echo "Failed checks must be fixed before testing."
  echo "See MASTERPLAN_PROGRESS_DEBUGGING_GUIDE.md for detailed debugging steps."
  echo ""
  exit 1
fi
