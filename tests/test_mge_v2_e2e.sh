#!/bin/bash
#
# E2E Test for MGE V2 MasterPlan Generation
# Tests: Auth → Message → MasterPlan Generation → Progress Monitoring → Validation
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "MGE V2 E2E Test"
echo "=========================================="
echo ""

# Configuration
API_URL="http://localhost:8000"
TEST_EMAIL="test@devmatrix.com"
TEST_PASSWORD="Test123!"
PROMPT="Create a REST API for a todo list application with user authentication"

# Step 1: Auth
echo -e "${BLUE}[1/6]${NC} Authenticating..."
TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Authentication failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Authenticated${NC}"

# Step 2: Get user ID
USER_ID=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -A -c \
  "SELECT user_id FROM users WHERE email = '$TEST_EMAIL';" | head -1 | xargs)

echo -e "${GREEN}✓ User ID: $USER_ID${NC}"

# Step 3: Create conversation
echo ""
echo -e "${BLUE}[2/6]${NC} Creating conversation..."
CONVERSATION_ID=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -A -c \
  "INSERT INTO conversations (conversation_id, user_id, title, created_at, updated_at)
   VALUES (gen_random_uuid(), '$USER_ID', 'E2E Test', NOW(), NOW())
   RETURNING conversation_id;" | head -1 | xargs)

echo -e "${GREEN}✓ Conversation: $CONVERSATION_ID${NC}"

# Step 4: Count initial MasterPlans
INITIAL_MP_COUNT=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
  "SELECT COUNT(*) FROM masterplans WHERE user_id = '$USER_ID';" | xargs)

echo -e "${GREEN}✓ Initial MasterPlan count: $INITIAL_MP_COUNT${NC}"

# Step 5: Send message
echo ""
echo -e "${BLUE}[3/6]${NC} Sending message..."
echo "Prompt: $PROMPT"

MSG_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
  "$API_URL/api/v1/conversations/$CONVERSATION_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"$PROMPT\"}")

HTTP_STATUS=$(echo "$MSG_RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
BODY=$(echo "$MSG_RESPONSE" | grep -v "HTTP_STATUS")

if [ "$HTTP_STATUS" != "200" ]; then
    echo -e "${RED}✗ Message failed (HTTP $HTTP_STATUS)${NC}"
    echo "Response: $BODY"
    exit 1
fi

MESSAGE_ID=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$MESSAGE_ID" ]; then
    echo -e "${GREEN}✓ Message sent: $MESSAGE_ID${NC}"
else
    echo -e "${YELLOW}⚠ Message sent (ID not returned)${NC}"
fi

# Step 6: Monitor for MasterPlan creation
echo ""
echo -e "${BLUE}[4/6]${NC} Monitoring MasterPlan creation..."

MAX_WAIT=180
ELAPSED=0
CHECK_INTERVAL=3
MASTERPLAN_ID=""

while [ $ELAPSED -lt $MAX_WAIT ]; do
    CURRENT_COUNT=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
      "SELECT COUNT(*) FROM masterplans WHERE user_id = '$USER_ID';" | xargs)

    if [ "$CURRENT_COUNT" -gt "$INITIAL_MP_COUNT" ]; then
        echo ""
        MASTERPLAN_ID=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -A -c \
          "SELECT masterplan_id FROM masterplans WHERE user_id = '$USER_ID'
           ORDER BY created_at DESC LIMIT 1;" | head -1 | xargs)

        echo -e "${GREEN}✓ MasterPlan created: $MASTERPLAN_ID${NC}"
        break
    fi

    echo -ne "\r${YELLOW}Waiting for generation...${NC} ${ELAPSED}s / ${MAX_WAIT}s"
    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
done

echo ""

if [ -z "$MASTERPLAN_ID" ]; then
    echo -e "${RED}✗ Timeout: No MasterPlan created after ${MAX_WAIT}s${NC}"
    echo ""
    echo "Checking logs..."
    docker logs devmatrix-api --tail 30 | grep -E "(ERROR|MasterPlan)"
    exit 1
fi

# Step 7: Monitor generation progress
echo ""
echo -e "${BLUE}[5/6]${NC} Monitoring generation progress..."

MAX_PROGRESS_WAIT=180
PROGRESS_ELAPSED=0

while [ $PROGRESS_ELAPSED -lt $MAX_PROGRESS_WAIT ]; do
    MP_STATUS=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -A -F'|' -c \
      "SELECT status, total_phases, total_tasks
       FROM masterplans WHERE masterplan_id = '$MASTERPLAN_ID';" | head -1)

    STATUS=$(echo "$MP_STATUS" | cut -d'|' -f1 | xargs)
    PHASES=$(echo "$MP_STATUS" | cut -d'|' -f2 | xargs)
    TASKS=$(echo "$MP_STATUS" | cut -d'|' -f3 | xargs)

    echo -ne "\r${YELLOW}Status:${NC} $STATUS | ${BLUE}Phases:${NC} ${PHASES:-0} | ${BLUE}Tasks:${NC} ${TASKS:-0} | ${YELLOW}Time:${NC} ${PROGRESS_ELAPSED}s    "

    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo -e "${GREEN}✓ Generation completed!${NC}"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo -e "${RED}✗ Generation failed${NC}"

        ERROR=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -c \
          "SELECT metadata->>'error' FROM masterplans WHERE masterplan_id = '$MASTERPLAN_ID';")

        echo "Error: $ERROR"
        exit 1
    fi

    sleep $CHECK_INTERVAL
    PROGRESS_ELAPSED=$((PROGRESS_ELAPSED + CHECK_INTERVAL))
done

echo ""

if [ $PROGRESS_ELAPSED -ge $MAX_PROGRESS_WAIT ]; then
    echo -e "${RED}✗ Timeout: Generation did not complete after ${MAX_PROGRESS_WAIT}s${NC}"
    echo "Last status: $STATUS"
    exit 1
fi

# Step 8: Validate generated artifacts
echo ""
echo -e "${BLUE}[6/6]${NC} Validating artifacts..."

# Get final stats
FINAL_STATS=$(docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -t -A -F'|' -c \
  "SELECT project_name, status, total_phases, total_tasks, total_subtasks
   FROM masterplans WHERE masterplan_id = '$MASTERPLAN_ID';" | head -1)

PROJECT_NAME=$(echo "$FINAL_STATS" | cut -d'|' -f1 | xargs)
FINAL_STATUS=$(echo "$FINAL_STATS" | cut -d'|' -f2 | xargs)
TOTAL_PHASES=$(echo "$FINAL_STATS" | cut -d'|' -f3 | xargs)
TOTAL_TASKS=$(echo "$FINAL_STATS" | cut -d'|' -f4 | xargs)
TOTAL_SUBTASKS=$(echo "$FINAL_STATS" | cut -d'|' -f5 | xargs)

echo ""
echo "==================================="
echo "Final Results"
echo "==================================="
echo -e "${BLUE}Project:${NC} $PROJECT_NAME"
echo -e "${BLUE}MasterPlan ID:${NC} $MASTERPLAN_ID"
echo -e "${BLUE}Status:${NC} $FINAL_STATUS"
echo -e "${BLUE}Phases:${NC} $TOTAL_PHASES"
echo -e "${BLUE}Tasks:${NC} $TOTAL_TASKS"
echo -e "${BLUE}Subtasks:${NC} $TOTAL_SUBTASKS"
echo ""

# Validate minimums
TESTS_PASSED=0
TESTS_FAILED=0

if [ "$FINAL_STATUS" = "completed" ]; then
    echo -e "${GREEN}✓ Status is completed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ Status is not completed: $FINAL_STATUS${NC}"
    ((TESTS_FAILED++))
fi

if [ "$TOTAL_PHASES" -gt 0 ]; then
    echo -e "${GREEN}✓ Has phases ($TOTAL_PHASES)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ No phases generated${NC}"
    ((TESTS_FAILED++))
fi

if [ "$TOTAL_TASKS" -gt 0 ]; then
    echo -e "${GREEN}✓ Has tasks ($TOTAL_TASKS)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ No tasks generated${NC}"
    ((TESTS_FAILED++))
fi

if [ "$TOTAL_SUBTASKS" -gt 0 ]; then
    echo -e "${GREEN}✓ Has subtasks ($TOTAL_SUBTASKS)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ No subtasks generated${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo "==================================="
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed ($TESTS_PASSED/4)${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed ($TESTS_PASSED passed, $TESTS_FAILED failed)${NC}"
    exit 1
fi
