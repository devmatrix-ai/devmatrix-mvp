# MasterPlan Testing Improvement - Complete Solution

**Date**: 2025-11-16
**Author**: DevMatrix Cognitive Architecture Team
**Status**: Ready for Implementation

## Overview

Este documento especifica los cambios necesarios al `MASTERPLAN_SYSTEM_PROMPT` para garantizar que SIEMPRE se generen tareas de testing específicas.

---

## 1. Improved Phase 3: Polish Structure

### ❌ BEFORE (Actual - Vague)

```python
### Phase 3: Polish (20-30 tasks)
- Testing (focus on critical paths)
- Error handling and validation
- Performance optimization (key areas)
- Essential documentation
- Deployment preparation
```

### ✅ AFTER (Improved - Specific)

```python
### Phase 3: Polish & Quality (25-35 tasks)

#### 🧪 Testing (12-18 tasks) - **MANDATORY**

**CRITICAL REQUIREMENT**: Generate SPECIFIC test files, NOT generic "testing strategy" tasks.

**Testing Task Breakdown** (exact task count based on project):

1. **Unit Tests** (6-8 tasks):
   - 1 test task per domain model (User, Product, Order, etc.)
   - File: `tests/models/test_*.py`
   - Example: "Generate unit tests for User model"

2. **Integration Tests** (3-5 tasks):
   - 1 test task per API router group (auth, products, orders, etc.)
   - File: `tests/api/test_*.py`
   - Example: "Generate integration tests for auth endpoints"

3. **E2E Tests** (2-3 tasks):
   - 1 test task per critical user flow (signup, checkout, etc.)
   - File: `tests/e2e/test_*.py`
   - Example: "Generate E2E tests for checkout flow"

4. **Contract Tests** (1-2 tasks):
   - 1 test task per aggregate boundary
   - File: `tests/contracts/test_*.py`
   - Example: "Generate contract tests for Order API schema"

**Testing Task Template Structure**:
```json
{
  "task_number": X,
  "name": "Generate unit tests for [ModelName] model",
  "description": "Create tests/models/test_[model].py with pytest tests for [ModelName] model covering CRUD operations, validation rules, business logic, and edge cases",
  "complexity": "low",
  "depends_on_tasks": [Y],  // Depends on task that creates the model
  "target_files": ["tests/models/test_[model].py"],
  "estimated_tokens": 600,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import test dependencies and fixtures",
      "description": "import pytest; from src.models.[model] import [ModelName]; from tests.fixtures import [fixtures]"
    },
    {
      "subtask_number": 2,
      "name": "Test model creation with valid data",
      "description": "def test_create_[model]_valid(): [model] = [ModelName](...); assert [model].field == expected_value"
    },
    {
      "subtask_number": 3,
      "name": "Test field validation (invalid cases)",
      "description": "def test_[field]_validation(): with pytest.raises(ValidationError): [ModelName](field='invalid')"
    },
    {
      "subtask_number": 4,
      "name": "Test business logic methods",
      "description": "def test_[method](): [model] = [ModelName](...); result = [model].[method](); assert result == expected"
    },
    {
      "subtask_number": 5,
      "name": "Test edge cases and boundary conditions",
      "description": "def test_edge_case_[scenario](): [test edge case logic]"
    }
  ]
}
```

#### ✅ Quality & Deployment (8-12 tasks):
- Error handling middleware and validation layers
- Performance optimization (caching, indexing, query optimization)
- API documentation (OpenAPI/Swagger specs)
- Deployment configuration (Docker, environment variables)

**IMPORTANT**:
- Testing tasks are MANDATORY - MUST generate 12-18 specific test file creation tasks
- Each testing task MUST specify exact file path in `target_files`
- Each testing task MUST have 4-6 specific subtasks describing test cases
- Testing tasks MUST depend on implementation tasks (model/endpoint creation)
```

---

## 2. Updated Comprehensive Features List

### Current (línea 212)

```python
**IMPORTANT**:
- Return ONLY valid JSON, no markdown, no explanations outside the JSON
- Generate EXACTLY {task_count} tasks total (complete production-ready implementation)
- Cover ALL aspects: Auth, RBAC, Users, Organizations, Projects, Boards, Issues,
  Sprints, Comments, Attachments, Notifications, Search, Reporting, Real-time, API/Webhooks
- All task_numbers must be sequential starting from 1
- Dependencies must reference valid task_numbers
- EVERY task MUST include a "subtasks" array with 3-5 items (concise)
- Keep descriptions concise to reduce token count
```

### Improved

```python
**IMPORTANT**:
- Return ONLY valid JSON, no markdown, no explanations outside the JSON
- Generate EXACTLY {task_count} tasks total (complete production-ready implementation)
- Cover ALL aspects: Auth, RBAC, Users, Organizations, Projects, Boards, Issues,
  Sprints, Comments, Attachments, Notifications, Search, Reporting, Real-time, API/Webhooks
- **🧪 TESTING IS MANDATORY**: MUST include 12-18 SPECIFIC test generation tasks in Phase 3
  * Unit tests for ALL domain models (tests/models/test_*.py)
  * Integration tests for ALL API routers (tests/api/test_*.py)
  * E2E tests for critical user flows (tests/e2e/test_*.py)
  * Contract tests for aggregate boundaries (tests/contracts/test_*.py)
- All task_numbers must be sequential starting from 1
- Dependencies must reference valid task_numbers
- Testing tasks MUST depend on implementation tasks (use depends_on_tasks)
- EVERY task MUST include a "subtasks" array with 3-6 items
- Keep descriptions concise to reduce token count
```

---

## 3. Complete Testing Task Examples

### Example 1: Unit Test Task

```json
{
  "task_number": 95,
  "name": "Generate unit tests for User model",
  "description": "Create tests/models/test_user.py with pytest tests for User model covering creation, email validation, password hashing, role assignment, and timestamp handling",
  "complexity": "low",
  "depends_on_tasks": [15],
  "target_files": ["tests/models/test_user.py"],
  "estimated_tokens": 650,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import test dependencies",
      "description": "import pytest; from src.models.user import User; from src.database import get_test_db; from tests.fixtures import user_factory"
    },
    {
      "subtask_number": 2,
      "name": "Test user creation with valid data",
      "description": "def test_create_user_valid(): user = User(email='test@example.com', password='SecurePass123'); assert user.email == 'test@example.com'; assert user.id is not None"
    },
    {
      "subtask_number": 3,
      "name": "Test email validation (invalid format)",
      "description": "def test_email_validation_invalid(): with pytest.raises(ValidationError): User(email='invalid-email', password='pass')"
    },
    {
      "subtask_number": 4,
      "name": "Test password hashing on creation",
      "description": "def test_password_hashing(): user = User(email='test@test.com', password='plaintext'); assert user.password != 'plaintext'; assert len(user.password) > 50"
    },
    {
      "subtask_number": 5,
      "name": "Test role assignment and permissions",
      "description": "def test_role_assignment(): user = User(email='admin@test.com', role='admin'); assert user.has_permission('manage_users') == True"
    },
    {
      "subtask_number": 6,
      "name": "Test timestamp auto-generation",
      "description": "def test_timestamps(): user = User(email='test@test.com', password='pass'); assert user.created_at is not None; assert user.updated_at is not None"
    }
  ]
}
```

### Example 2: Integration Test Task

```json
{
  "task_number": 105,
  "name": "Generate integration tests for auth endpoints",
  "description": "Create tests/api/test_auth.py with pytest tests for authentication endpoints covering signup, login, logout, token refresh, and password reset flows",
  "complexity": "medium",
  "depends_on_tasks": [45, 46, 47],
  "target_files": ["tests/api/test_auth.py"],
  "estimated_tokens": 750,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import API test dependencies",
      "description": "import pytest; from fastapi.testclient import TestClient; from src.main import app; from tests.fixtures import test_db, auth_headers"
    },
    {
      "subtask_number": 2,
      "name": "Test successful user signup",
      "description": "def test_signup_success(client): response = client.post('/api/auth/signup', json={'email': 'new@test.com', 'password': 'SecurePass123'}); assert response.status_code == 201; assert 'access_token' in response.json()"
    },
    {
      "subtask_number": 3,
      "name": "Test signup with duplicate email",
      "description": "def test_signup_duplicate_email(client, existing_user): response = client.post('/api/auth/signup', json={'email': existing_user.email, 'password': 'pass'}); assert response.status_code == 409"
    },
    {
      "subtask_number": 4,
      "name": "Test successful login with valid credentials",
      "description": "def test_login_success(client, existing_user): response = client.post('/api/auth/login', json={'email': existing_user.email, 'password': 'correct_password'}); assert response.status_code == 200; assert 'access_token' in response.json()"
    },
    {
      "subtask_number": 5,
      "name": "Test login with invalid credentials",
      "description": "def test_login_invalid_credentials(client): response = client.post('/api/auth/login', json={'email': 'wrong@test.com', 'password': 'wrong'}); assert response.status_code == 401"
    },
    {
      "subtask_number": 6,
      "name": "Test protected endpoint access with valid token",
      "description": "def test_protected_endpoint_with_token(client, auth_headers): response = client.get('/api/users/me', headers=auth_headers); assert response.status_code == 200"
    }
  ]
}
```

### Example 3: E2E Test Task

```json
{
  "task_number": 112,
  "name": "Generate E2E tests for checkout flow",
  "description": "Create tests/e2e/test_checkout.py with Playwright tests for complete user checkout journey from product selection to payment confirmation",
  "complexity": "high",
  "depends_on_tasks": [60, 65, 70],
  "target_files": ["tests/e2e/test_checkout.py"],
  "estimated_tokens": 800,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import E2E test dependencies",
      "description": "import pytest; from playwright.sync_api import Page, expect; from tests.e2e.fixtures import authenticated_page, test_product"
    },
    {
      "subtask_number": 2,
      "name": "Test product selection and add to cart",
      "description": "def test_add_to_cart(authenticated_page, test_product): page.goto('/products'); page.click(f'[data-testid=\"product-{test_product.id}\"]'); page.click('[data-testid=\"add-to-cart\"]'); expect(page.locator('[data-testid=\"cart-count\"]')).to_have_text('1')"
    },
    {
      "subtask_number": 3,
      "name": "Test cart review and quantity update",
      "description": "def test_update_cart_quantity(authenticated_page): page.goto('/cart'); page.fill('[data-testid=\"quantity-input\"]', '3'); page.click('[data-testid=\"update-quantity\"]'); expect(page.locator('[data-testid=\"total-price\"]')).to_contain_text('$90.00')"
    },
    {
      "subtask_number": 4,
      "name": "Test shipping information entry",
      "description": "def test_enter_shipping_info(authenticated_page): page.goto('/checkout'); page.fill('[name=\"address\"]', '123 Test St'); page.fill('[name=\"city\"]', 'Test City'); page.select_option('[name=\"country\"]', 'US'); page.click('[data-testid=\"continue-to-payment\"]')"
    },
    {
      "subtask_number": 5,
      "name": "Test payment processing (mock)",
      "description": "def test_payment_processing_mock(authenticated_page, mock_payment_gateway): page.fill('[name=\"card_number\"]', '4111111111111111'); page.fill('[name=\"cvv\"]', '123'); page.click('[data-testid=\"place-order\"]'); expect(page).to_have_url('/order-confirmation')"
    },
    {
      "subtask_number": 6,
      "name": "Test order confirmation display",
      "description": "def test_order_confirmation(authenticated_page): expect(page.locator('[data-testid=\"order-number\"]')).to_be_visible(); expect(page.locator('[data-testid=\"confirmation-message\"]')).to_contain_text('Thank you for your order')"
    }
  ]
}
```

### Example 4: Contract Test Task

```json
{
  "task_number": 116,
  "name": "Generate contract tests for Order API schema",
  "description": "Create tests/contracts/test_order_api.py with Pydantic schema validation tests for Order aggregate API contracts (request/response schemas)",
  "complexity": "low",
  "depends_on_tasks": [55],
  "target_files": ["tests/contracts/test_order_api.py"],
  "estimated_tokens": 550,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import contract test dependencies",
      "description": "import pytest; from pydantic import ValidationError; from src.api.schemas.order import CreateOrderRequest, OrderResponse, OrderStatus"
    },
    {
      "subtask_number": 2,
      "name": "Test valid CreateOrderRequest schema",
      "description": "def test_create_order_request_valid(): request = CreateOrderRequest(items=[{'product_id': 1, 'quantity': 2}], shipping_address='123 St'); assert request.items[0].quantity == 2"
    },
    {
      "subtask_number": 3,
      "name": "Test CreateOrderRequest with missing required fields",
      "description": "def test_create_order_request_missing_fields(): with pytest.raises(ValidationError) as exc: CreateOrderRequest(items=[]); assert 'items' in str(exc.value)"
    },
    {
      "subtask_number": 4,
      "name": "Test OrderResponse schema structure",
      "description": "def test_order_response_schema(): response = OrderResponse(order_id='123', status=OrderStatus.PENDING, total=99.99, created_at=datetime.now()); assert response.order_id == '123'"
    },
    {
      "subtask_number": 5,
      "name": "Test OrderStatus enum validation",
      "description": "def test_order_status_enum(): assert OrderStatus.PENDING in OrderStatus; with pytest.raises(ValueError): OrderResponse(order_id='1', status='INVALID', total=10, created_at=datetime.now())"
    }
  ]
}
```

---

## 4. Implementation Checklist

### Changes to masterplan_generator.py

- [ ] Update `MASTERPLAN_SYSTEM_PROMPT` (líneas 48-217)
  - [ ] Replace Phase 3 section with improved version
  - [ ] Add testing task template structure
  - [ ] Update comprehensive features list with testing requirement

- [ ] Add validation in `_validate_masterplan()` (líneas 864-921)
  - [ ] Count testing tasks in Phase 3
  - [ ] Validate minimum 10% of total tasks are testing
  - [ ] Validate test files are in correct directories

- [ ] Add testing examples to prompt
  - [ ] Include 1 unit test example
  - [ ] Include 1 integration test example
  - [ ] Include 1 e2e test example

### Validation Implementation

See [masterplan-validation-rules.md](./masterplan-validation-rules.md) for complete validation logic.

---

## 5. Expected Outcomes

### Before Implementation

| Metric | Current Value |
|--------|---------------|
| Testing tasks per MasterPlan | 0 |
| Test files generated | 0 |
| Precision measurement | 0/0 = 100% (false positive) |
| Cognitive Feedback Loop quality | Unvalidated patterns |

### After Implementation

| Metric | Target Value |
|--------|--------------|
| Testing tasks per MasterPlan | 12-18 |
| Test files generated | 12-18 |
| Precision measurement | Real (e.g., 12/13 = 92%) |
| Cognitive Feedback Loop quality | Validated patterns only |

---

## 6. Migration Strategy

1. **Test in Isolated Environment**:
   - Run E2E test with new prompt
   - Verify 12-18 testing tasks are generated
   - Confirm test files are created correctly

2. **Validate Quality**:
   - Check generated tests compile and run
   - Verify test coverage is meaningful
   - Confirm precision measurement is accurate

3. **Deploy to Production**:
   - Update MASTERPLAN_SYSTEM_PROMPT
   - Enable validation rules
   - Monitor first 5 MasterPlans for quality

4. **Measure Impact**:
   - Track precision scores over 20 MasterPlans
   - Compare before/after Cognitive Feedback Loop quality
   - Adjust minimum testing task count if needed

---

**Implementation Files**:
- Main: `src/services/masterplan_generator.py`
- Validation: See [masterplan-validation-rules.md](./masterplan-validation-rules.md)
- Templates: See [masterplan-testing-templates.md](./masterplan-testing-templates.md)
