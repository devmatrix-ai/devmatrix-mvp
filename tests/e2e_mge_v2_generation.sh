#!/bin/bash

# E2E Test for MGE V2 MasterPlan Generation
# Tests complete flow: auth → generation → monitoring → validation

set -e

echo "=========================================="
echo "E2E MGE V2 Generation Test"
echo "=========================================="
echo ""

# Configuration
API_URL="http://localhost:8000"
UI_URL="http://localhost:3000"
TEST_EMAIL="test@devmatrix.com"
TEST_PASSWORD="Test123!"
TEST_PROMPT="Create a simple REST API for managing blog posts with CRUD operations"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Step 1: Authentication
log_test "Step 1: Authentication"
echo "Authenticating user: $TEST_EMAIL"

AUTH_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    log_error "Authentication failed"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

log_success "Authentication successful"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 2: Create conversation
log_test "Step 2: Create conversation"

# Get user_id from token
USER_ID=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT user_id FROM users WHERE email = '$TEST_EMAIL';" | xargs)

# Create conversation directly in database
CONVERSATION_ID=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "INSERT INTO conversations (id, user_id, title, created_at, updated_at)
   VALUES (gen_random_uuid(), '$USER_ID', 'E2E Test - MGE V2', NOW(), NOW())
   RETURNING id;" | xargs)

if [ -z "$CONVERSATION_ID" ]; then
    log_error "Failed to create conversation"
    exit 1
fi

log_success "Conversation created: $CONVERSATION_ID"
echo ""

# Step 3: Send message and trigger generation
log_test "Step 3: Send message and trigger MasterPlan generation"
echo "Prompt: $TEST_PROMPT"

MSG_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/conversations/$CONVERSATION_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"$TEST_PROMPT\"}")

MESSAGE_ID=$(echo "$MSG_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ -z "$MESSAGE_ID" ]; then
    log_error "Failed to send message"
    echo "Response: $MSG_RESPONSE"
    exit 1
fi

log_success "Message sent: $MESSAGE_ID"
echo ""

# Step 4: Wait for generation to start
log_test "Step 4: Wait for MasterPlan generation to start"
sleep 5

# Check database for MasterPlan
log_info "Checking database for MasterPlan..."

MASTERPLAN_CHECK=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT id, status FROM masterplans WHERE conversation_id = '$CONVERSATION_ID' ORDER BY created_at DESC LIMIT 1;")

MASTERPLAN_ID=$(echo "$MASTERPLAN_CHECK" | awk '{print $1}' | xargs)
MASTERPLAN_STATUS=$(echo "$MASTERPLAN_CHECK" | awk '{print $3}' | xargs)

if [ -z "$MASTERPLAN_ID" ]; then
    log_error "MasterPlan not found in database"
    exit 1
fi

log_success "MasterPlan found: $MASTERPLAN_ID"
log_info "Initial status: $MASTERPLAN_STATUS"
echo ""

# Step 5: Monitor generation progress
log_test "Step 5: Monitor generation progress"

MAX_WAIT=180  # 3 minutes
ELAPSED=0
CHECK_INTERVAL=5

echo "Monitoring generation (max ${MAX_WAIT}s)..."

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check MasterPlan status
    MP_DATA=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
      "SELECT status, current_phase, progress FROM masterplans WHERE id = '$MASTERPLAN_ID';")

    STATUS=$(echo "$MP_DATA" | awk '{print $1}' | xargs)
    PHASE=$(echo "$MP_DATA" | awk '{print $3}' | xargs)
    PROGRESS=$(echo "$MP_DATA" | awk '{print $5}' | xargs)

    # Count phases
    PHASE_COUNT=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
      "SELECT COUNT(*) FROM masterplan_phases WHERE masterplan_id = '$MASTERPLAN_ID';")

    PHASE_COUNT=$(echo "$PHASE_COUNT" | xargs)

    echo -ne "\r${YELLOW}Status:${NC} $STATUS | ${BLUE}Phase:${NC} $PHASE | ${GREEN}Progress:${NC} ${PROGRESS}% | ${BLUE}Phases:${NC} $PHASE_COUNT | ${YELLOW}Time:${NC} ${ELAPSED}s    "

    # Check if completed or failed
    if [ "$STATUS" = "completed" ]; then
        echo ""
        log_success "Generation completed!"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        log_error "Generation failed"

        # Get error from database
        ERROR=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
          "SELECT metadata->>'error' FROM masterplans WHERE id = '$MASTERPLAN_ID';")
        echo "Error: $ERROR"
        exit 1
    fi

    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
done

echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    log_error "Generation timeout after ${MAX_WAIT}s"
    log_info "Final status: $STATUS"
    exit 1
fi

echo ""

# Step 6: Validate generated artifacts
log_test "Step 6: Validate generated artifacts"

# Check phases
PHASES=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT id, name, status FROM masterplan_phases WHERE masterplan_id = '$MASTERPLAN_ID' ORDER BY phase_order;")

echo "Generated Phases:"
echo "$PHASES" | while IFS='|' read -r id name status; do
    id=$(echo "$id" | xargs)
    name=$(echo "$name" | xargs)
    status=$(echo "$status" | xargs)

    if [ "$status" = "completed" ]; then
        echo -e "  ${GREEN}✓${NC} $name ($id)"
    else
        echo -e "  ${RED}✗${NC} $name ($id) - $status"
    fi
done

PHASE_COUNT=$(echo "$PHASES" | grep -v '^$' | wc -l)

if [ "$PHASE_COUNT" -gt 0 ]; then
    log_success "Found $PHASE_COUNT phases"
else
    log_error "No phases found"
fi

# Check tasks
TASK_COUNT=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT COUNT(*) FROM masterplan_tasks WHERE phase_id IN (SELECT id FROM masterplan_phases WHERE masterplan_id = '$MASTERPLAN_ID');")

TASK_COUNT=$(echo "$TASK_COUNT" | xargs)

if [ "$TASK_COUNT" -gt 0 ]; then
    log_success "Found $TASK_COUNT tasks"
else
    log_error "No tasks found"
fi

# Check subtasks
SUBTASK_COUNT=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT COUNT(*) FROM masterplan_subtasks WHERE task_id IN (SELECT id FROM masterplan_tasks WHERE phase_id IN (SELECT id FROM masterplan_phases WHERE masterplan_id = '$MASTERPLAN_ID'));")

SUBTASK_COUNT=$(echo "$SUBTASK_COUNT" | xargs)

if [ "$SUBTASK_COUNT" -gt 0 ]; then
    log_success "Found $SUBTASK_COUNT subtasks"
else
    log_error "No subtasks found"
fi

echo ""

# Step 7: Check metadata quality
log_test "Step 7: Validate metadata quality"

METADATA=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT metadata FROM masterplans WHERE id = '$MASTERPLAN_ID';")

echo "Checking metadata fields..."

if echo "$METADATA" | grep -q "total_tokens"; then
    log_success "Contains token usage data"
else
    log_error "Missing token usage data"
fi

if echo "$METADATA" | grep -q "requirements"; then
    log_success "Contains requirements analysis"
else
    log_error "Missing requirements analysis"
fi

if echo "$METADATA" | grep -q "timeline"; then
    log_success "Contains timeline estimation"
else
    log_error "Missing timeline estimation"
fi

echo ""

# Step 8: Test API endpoints
log_test "Step 8: Test API endpoints"

# Get MasterPlan via API
MP_API_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/masterplans/$MASTERPLAN_ID" \
  -H "Authorization: Bearer $TOKEN")

if echo "$MP_API_RESPONSE" | grep -q "$MASTERPLAN_ID"; then
    log_success "GET /masterplans/{id} working"
else
    log_error "GET /masterplans/{id} failed"
fi

# Get phases via API
PHASES_API_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/masterplans/$MASTERPLAN_ID/phases" \
  -H "Authorization: Bearer $TOKEN")

if echo "$PHASES_API_RESPONSE" | grep -q "phase_order"; then
    log_success "GET /masterplans/{id}/phases working"
else
    log_error "GET /masterplans/{id}/phases failed"
fi

echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Tests Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Tests Failed:${NC} $TESTS_FAILED"
echo ""
echo -e "MasterPlan ID: ${BLUE}$MASTERPLAN_ID${NC}"
echo -e "Conversation ID: ${BLUE}$CONVERSATION_ID${NC}"
echo -e "Phases: ${BLUE}$PHASE_COUNT${NC}"
echo -e "Tasks: ${BLUE}$TASK_COUNT${NC}"
echo -e "Subtasks: ${BLUE}$SUBTASK_COUNT${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
