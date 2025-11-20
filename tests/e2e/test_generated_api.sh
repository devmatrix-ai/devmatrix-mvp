#!/bin/bash
# Test script for generated API

API_URL="http://localhost:8002"

echo "=== 🧪 TESTING CRUD ENDPOINTS ==="
echo ""

# 1. Create Task 1
echo "1️⃣  POST /tasks - Create task 1"
TASK1=$(curl -s -X POST "$API_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Task 1", "description": "First test task"}')
echo "$TASK1" | jq .
TASK1_ID=$(echo "$TASK1" | jq -r '.id')
echo "✅ Created task ID: $TASK1_ID"
echo ""

# 2. Create Task 2
echo "2️⃣  POST /tasks - Create task 2"
TASK2=$(curl -s -X POST "$API_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Task 2", "description": "Second test task"}')
echo "$TASK2" | jq .
TASK2_ID=$(echo "$TASK2" | jq -r '.id')
echo "✅ Created task ID: $TASK2_ID"
echo ""

# 3. List all tasks
echo "3️⃣  GET /tasks - List all tasks"
curl -s "$API_URL/tasks" | jq .
echo ""

# 4. Get specific task
echo "4️⃣  GET /tasks/{id} - Get task 1"
curl -s "$API_URL/tasks/$TASK1_ID" | jq .
echo ""

# 5. Update task
echo "5️⃣  PUT /tasks/{id} - Update task 1"
curl -s -X PUT "$API_URL/tasks/$TASK1_ID" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Task 1", "description": "This task is now complete", "completed": true}' | jq .
echo ""

# 6. Verify update
echo "6️⃣  GET /tasks - Verify update"
curl -s "$API_URL/tasks" | jq .
echo ""

# 7. Delete task
echo "7️⃣  DELETE /tasks/{id} - Delete task 2"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API_URL/tasks/$TASK2_ID")
echo "HTTP Status: $STATUS"
echo ""

# 8. Verify deletion
echo "8️⃣  GET /tasks - Verify deletion (should only show task 1)"
curl -s "$API_URL/tasks" | jq .
echo ""

# 9. Try to get deleted task
echo "9️⃣  GET /tasks/{id} - Try to get deleted task (should 404)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/tasks/$TASK2_ID")
echo "HTTP Status: $STATUS"
if [ "$STATUS" == "404" ]; then
    echo "✅ Correctly returned 404 for deleted task"
else
    echo "❌ Expected 404, got $STATUS"
fi
echo ""

echo "=== ✅ ALL TESTS COMPLETED ==="
