# MasterPlan Testing Task Templates

**Date**: 2025-11-16
**Author**: DevMatrix Cognitive Architecture Team
**Purpose**: Comprehensive testing task templates for all project types and tech stacks

---

## Overview

Este documento proporciona templates completos de tareas de testing para diferentes tipos de proyectos, frameworks, y patrones arquitectónicos. Cada template incluye la estructura JSON completa con subtasks detalladas.

---

## Template Structure

Cada testing task debe seguir esta estructura:

```json
{
  "task_number": <number>,
  "name": "Generate <test_type> for <component>",
  "description": "Create <file_path> with <framework> tests for <component> covering <test_cases>",
  "complexity": "low|medium|high",
  "depends_on_tasks": [<implementation_task_numbers>],
  "target_files": ["<test_file_path>"],
  "estimated_tokens": <token_estimate>,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "<subtask_name>",
      "description": "<subtask_details>"
    }
  ]
}
```

---

## 1. Backend Testing Templates

### 1.1 Python/FastAPI - Unit Test (Model)

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
      "name": "Import test dependencies and fixtures",
      "description": "import pytest; from src.models.user import User; from src.database import get_test_db; from tests.fixtures import user_factory, db_session"
    },
    {
      "subtask_number": 2,
      "name": "Test model creation with valid data",
      "description": "def test_create_user_valid(db_session): user = User(email='test@example.com', password='SecurePass123', role='user'); db_session.add(user); db_session.commit(); assert user.id is not None; assert user.email == 'test@example.com'"
    },
    {
      "subtask_number": 3,
      "name": "Test email validation (invalid format)",
      "description": "def test_email_validation_invalid(): with pytest.raises(ValidationError): User(email='invalid-email', password='pass')"
    },
    {
      "subtask_number": 4,
      "name": "Test password hashing on creation",
      "description": "def test_password_hashing(db_session): user = User(email='test@test.com', password='plaintext'); db_session.add(user); db_session.commit(); assert user.password != 'plaintext'; assert len(user.password) > 50; assert user.password.startswith('$2b$')"
    },
    {
      "subtask_number": 5,
      "name": "Test role assignment and permissions",
      "description": "def test_role_assignment(db_session): user = User(email='admin@test.com', password='pass', role='admin'); assert user.has_permission('manage_users') == True; assert user.has_permission('manage_system') == True"
    },
    {
      "subtask_number": 6,
      "name": "Test timestamp auto-generation",
      "description": "def test_timestamps(db_session): user = User(email='test@test.com', password='pass'); db_session.add(user); db_session.commit(); assert user.created_at is not None; assert user.updated_at is not None; assert user.created_at <= user.updated_at"
    }
  ]
}
```

### 1.2 Python/FastAPI - Integration Test (API Endpoint)

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
      "description": "import pytest; from fastapi.testclient import TestClient; from src.main import app; from tests.fixtures import test_db, auth_headers, mock_user"
    },
    {
      "subtask_number": 2,
      "name": "Test successful user signup",
      "description": "def test_signup_success(client): response = client.post('/api/auth/signup', json={'email': 'new@test.com', 'password': 'SecurePass123', 'name': 'Test User'}); assert response.status_code == 201; data = response.json(); assert 'access_token' in data; assert data['user']['email'] == 'new@test.com'"
    },
    {
      "subtask_number": 3,
      "name": "Test signup with duplicate email",
      "description": "def test_signup_duplicate_email(client, existing_user): response = client.post('/api/auth/signup', json={'email': existing_user.email, 'password': 'pass'}); assert response.status_code == 409; assert 'already exists' in response.json()['detail'].lower()"
    },
    {
      "subtask_number": 4,
      "name": "Test successful login with valid credentials",
      "description": "def test_login_success(client, existing_user): response = client.post('/api/auth/login', json={'email': existing_user.email, 'password': 'correct_password'}); assert response.status_code == 200; data = response.json(); assert 'access_token' in data; assert 'refresh_token' in data"
    },
    {
      "subtask_number": 5,
      "name": "Test login with invalid credentials",
      "description": "def test_login_invalid_credentials(client): response = client.post('/api/auth/login', json={'email': 'wrong@test.com', 'password': 'wrong'}); assert response.status_code == 401; assert 'invalid credentials' in response.json()['detail'].lower()"
    },
    {
      "subtask_number": 6,
      "name": "Test protected endpoint access with valid token",
      "description": "def test_protected_endpoint_with_token(client, auth_headers): response = client.get('/api/users/me', headers=auth_headers); assert response.status_code == 200; data = response.json(); assert 'email' in data; assert 'id' in data"
    },
    {
      "subtask_number": 7,
      "name": "Test protected endpoint access without token",
      "description": "def test_protected_endpoint_without_token(client): response = client.get('/api/users/me'); assert response.status_code == 401; assert 'not authenticated' in response.json()['detail'].lower()"
    }
  ]
}
```

### 1.3 Python/Django - Unit Test (Model)

```json
{
  "task_number": 96,
  "name": "Generate unit tests for Product model",
  "description": "Create tests/models/test_product.py with Django TestCase for Product model covering creation, price validation, stock management, and category relationships",
  "complexity": "low",
  "depends_on_tasks": [20],
  "target_files": ["tests/models/test_product.py"],
  "estimated_tokens": 700,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import Django test dependencies",
      "description": "from django.test import TestCase; from decimal import Decimal; from products.models import Product, Category; from django.core.exceptions import ValidationError"
    },
    {
      "subtask_number": 2,
      "name": "Test product creation with valid data",
      "description": "def test_create_product_valid(self): category = Category.objects.create(name='Electronics'); product = Product.objects.create(name='Laptop', price=Decimal('999.99'), stock=10, category=category); self.assertEqual(product.name, 'Laptop'); self.assertEqual(product.stock, 10)"
    },
    {
      "subtask_number": 3,
      "name": "Test price validation (negative price)",
      "description": "def test_price_validation_negative(self): category = Category.objects.create(name='Electronics'); with self.assertRaises(ValidationError): product = Product(name='Test', price=Decimal('-10.00'), category=category); product.full_clean()"
    },
    {
      "subtask_number": 4,
      "name": "Test stock decrement method",
      "description": "def test_stock_decrement(self): product = Product.objects.create(name='Test', price=Decimal('10.00'), stock=5); product.decrement_stock(2); self.assertEqual(product.stock, 3); with self.assertRaises(ValueError): product.decrement_stock(10)"
    },
    {
      "subtask_number": 5,
      "name": "Test category relationship cascade",
      "description": "def test_category_cascade_delete(self): category = Category.objects.create(name='Electronics'); product = Product.objects.create(name='Laptop', price=Decimal('999.99'), category=category); category_id = category.id; category.delete(); self.assertFalse(Product.objects.filter(id=product.id).exists())"
    }
  ]
}
```

### 1.4 Node.js/Express - Integration Test (API)

```json
{
  "task_number": 106,
  "name": "Generate integration tests for product endpoints",
  "description": "Create tests/api/test_products.test.js with Jest and Supertest for product CRUD endpoints covering create, read, update, delete operations",
  "complexity": "medium",
  "depends_on_tasks": [50, 51],
  "target_files": ["tests/api/test_products.test.js"],
  "estimated_tokens": 800,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import test dependencies",
      "description": "const request = require('supertest'); const app = require('../../src/app'); const { setupTestDB, teardownTestDB } = require('../fixtures/db'); const { createAuthToken } = require('../fixtures/auth');"
    },
    {
      "subtask_number": 2,
      "name": "Setup and teardown database",
      "description": "beforeAll(async () => { await setupTestDB(); }); afterAll(async () => { await teardownTestDB(); });"
    },
    {
      "subtask_number": 3,
      "name": "Test GET all products",
      "description": "test('GET /api/products - success', async () => { const res = await request(app).get('/api/products').expect(200); expect(Array.isArray(res.body)).toBe(true); });"
    },
    {
      "subtask_number": 4,
      "name": "Test POST create product (authenticated)",
      "description": "test('POST /api/products - success', async () => { const token = createAuthToken({ role: 'admin' }); const res = await request(app).post('/api/products').set('Authorization', `Bearer ${token}`).send({ name: 'New Product', price: 99.99, stock: 10 }).expect(201); expect(res.body.name).toBe('New Product'); });"
    },
    {
      "subtask_number": 5,
      "name": "Test PUT update product",
      "description": "test('PUT /api/products/:id - success', async () => { const token = createAuthToken({ role: 'admin' }); const res = await request(app).put('/api/products/1').set('Authorization', `Bearer ${token}`).send({ price: 89.99 }).expect(200); expect(res.body.price).toBe(89.99); });"
    },
    {
      "subtask_number": 6,
      "name": "Test DELETE product (authorization)",
      "description": "test('DELETE /api/products/:id - forbidden without admin role', async () => { const token = createAuthToken({ role: 'user' }); await request(app).delete('/api/products/1').set('Authorization', `Bearer ${token}`).expect(403); });"
    }
  ]
}
```

---

## 2. Frontend Testing Templates

### 2.1 React - Component Unit Test

```json
{
  "task_number": 97,
  "name": "Generate unit tests for LoginForm component",
  "description": "Create tests/components/test_LoginForm.test.tsx with React Testing Library for LoginForm covering rendering, user input, validation, and submission",
  "complexity": "medium",
  "depends_on_tasks": [60],
  "target_files": ["tests/components/test_LoginForm.test.tsx"],
  "estimated_tokens": 700,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import React testing dependencies",
      "description": "import { render, screen, fireEvent, waitFor } from '@testing-library/react'; import userEvent from '@testing-library/user-event'; import { LoginForm } from '@/components/LoginForm'; import { vi } from 'vitest';"
    },
    {
      "subtask_number": 2,
      "name": "Test component renders correctly",
      "description": "test('renders login form with email and password fields', () => { render(<LoginForm onSubmit={vi.fn()} />); expect(screen.getByLabelText(/email/i)).toBeInTheDocument(); expect(screen.getByLabelText(/password/i)).toBeInTheDocument(); expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument(); });"
    },
    {
      "subtask_number": 3,
      "name": "Test user can type in input fields",
      "description": "test('allows user to type email and password', async () => { const user = userEvent.setup(); render(<LoginForm onSubmit={vi.fn()} />); const emailInput = screen.getByLabelText(/email/i); const passwordInput = screen.getByLabelText(/password/i); await user.type(emailInput, 'test@example.com'); await user.type(passwordInput, 'password123'); expect(emailInput).toHaveValue('test@example.com'); expect(passwordInput).toHaveValue('password123'); });"
    },
    {
      "subtask_number": 4,
      "name": "Test form validation for invalid email",
      "description": "test('shows error for invalid email format', async () => { const user = userEvent.setup(); render(<LoginForm onSubmit={vi.fn()} />); await user.type(screen.getByLabelText(/email/i), 'invalid-email'); await user.click(screen.getByRole('button', { name: /log in/i })); expect(await screen.findByText(/invalid email/i)).toBeInTheDocument(); });"
    },
    {
      "subtask_number": 5,
      "name": "Test form submission with valid data",
      "description": "test('calls onSubmit with form data when valid', async () => { const handleSubmit = vi.fn(); const user = userEvent.setup(); render(<LoginForm onSubmit={handleSubmit} />); await user.type(screen.getByLabelText(/email/i), 'test@example.com'); await user.type(screen.getByLabelText(/password/i), 'password123'); await user.click(screen.getByRole('button', { name: /log in/i })); await waitFor(() => { expect(handleSubmit).toHaveBeenCalledWith({ email: 'test@example.com', password: 'password123' }); }); });"
    },
    {
      "subtask_number": 6,
      "name": "Test loading state during submission",
      "description": "test('shows loading state during submission', async () => { const user = userEvent.setup(); const slowSubmit = vi.fn(() => new Promise(resolve => setTimeout(resolve, 1000))); render(<LoginForm onSubmit={slowSubmit} />); await user.type(screen.getByLabelText(/email/i), 'test@example.com'); await user.type(screen.getByLabelText(/password/i), 'password123'); await user.click(screen.getByRole('button', { name: /log in/i })); expect(screen.getByRole('button')).toBeDisabled(); expect(screen.getByText(/loading/i)).toBeInTheDocument(); });"
    }
  ]
}
```

### 2.2 Vue - Component Unit Test

```json
{
  "task_number": 98,
  "name": "Generate unit tests for ProductCard component",
  "description": "Create tests/components/test_ProductCard.spec.js with Vue Test Utils for ProductCard covering props, events, and conditional rendering",
  "complexity": "low",
  "depends_on_tasks": [65],
  "target_files": ["tests/components/test_ProductCard.spec.js"],
  "estimated_tokens": 650,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import Vue testing dependencies",
      "description": "import { mount } from '@vue/test-utils'; import ProductCard from '@/components/ProductCard.vue'; import { describe, it, expect, vi } from 'vitest';"
    },
    {
      "subtask_number": 2,
      "name": "Test component renders with props",
      "description": "it('renders product information correctly', () => { const wrapper = mount(ProductCard, { props: { product: { id: 1, name: 'Test Product', price: 99.99, image: '/test.jpg' } } }); expect(wrapper.text()).toContain('Test Product'); expect(wrapper.text()).toContain('$99.99'); expect(wrapper.find('img').attributes('src')).toBe('/test.jpg'); });"
    },
    {
      "subtask_number": 3,
      "name": "Test add to cart button click",
      "description": "it('emits add-to-cart event when button clicked', async () => { const wrapper = mount(ProductCard, { props: { product: { id: 1, name: 'Test', price: 99.99 } } }); await wrapper.find('button').trigger('click'); expect(wrapper.emitted('add-to-cart')).toBeTruthy(); expect(wrapper.emitted('add-to-cart')[0]).toEqual([{ id: 1, name: 'Test', price: 99.99 }]); });"
    },
    {
      "subtask_number": 4,
      "name": "Test out of stock conditional rendering",
      "description": "it('shows out of stock message when stock is 0', () => { const wrapper = mount(ProductCard, { props: { product: { id: 1, name: 'Test', price: 99.99, stock: 0 } } }); expect(wrapper.text()).toContain('Out of Stock'); expect(wrapper.find('button').attributes('disabled')).toBeDefined(); });"
    },
    {
      "subtask_number": 5,
      "name": "Test discount badge conditional rendering",
      "description": "it('shows discount badge when discount exists', () => { const wrapper = mount(ProductCard, { props: { product: { id: 1, name: 'Test', price: 99.99, discount: 20 } } }); expect(wrapper.text()).toContain('20% OFF'); expect(wrapper.find('.discount-badge').exists()).toBe(true); });"
    }
  ]
}
```

---

## 3. E2E Testing Templates

### 3.1 Playwright - User Flow E2E Test

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
      "description": "import pytest; from playwright.sync_api import Page, expect; from tests.e2e.fixtures import authenticated_page, test_product, mock_payment_gateway"
    },
    {
      "subtask_number": 2,
      "name": "Test product selection and add to cart",
      "description": "def test_add_to_cart(authenticated_page: Page, test_product): page = authenticated_page; page.goto('/products'); page.click(f'[data-testid=\"product-{test_product.id}\"]'); page.click('[data-testid=\"add-to-cart\"]'); expect(page.locator('[data-testid=\"cart-count\"]')).to_have_text('1'); expect(page.locator('[data-testid=\"cart-notification\"]')).to_contain_text('Added to cart')"
    },
    {
      "subtask_number": 3,
      "name": "Test cart review and quantity update",
      "description": "def test_update_cart_quantity(authenticated_page: Page): page = authenticated_page; page.goto('/cart'); expect(page.locator('[data-testid=\"cart-item\"]')).to_be_visible(); page.fill('[data-testid=\"quantity-input\"]', '3'); page.click('[data-testid=\"update-quantity\"]'); expect(page.locator('[data-testid=\"total-price\"]')).to_contain_text('$90.00'); expect(page.locator('[data-testid=\"item-subtotal\"]')).to_contain_text('$90.00')"
    },
    {
      "subtask_number": 4,
      "name": "Test shipping information entry",
      "description": "def test_enter_shipping_info(authenticated_page: Page): page = authenticated_page; page.goto('/checkout'); page.fill('[name=\"address\"]', '123 Test St'); page.fill('[name=\"city\"]', 'Test City'); page.fill('[name=\"zipcode\"]', '12345'); page.select_option('[name=\"country\"]', 'US'); page.click('[data-testid=\"continue-to-payment\"]'); expect(page).to_have_url('/checkout/payment')"
    },
    {
      "subtask_number": 5,
      "name": "Test payment processing (mock)",
      "description": "def test_payment_processing_mock(authenticated_page: Page, mock_payment_gateway): page = authenticated_page; page.goto('/checkout/payment'); page.fill('[name=\"card_number\"]', '4111111111111111'); page.fill('[name=\"expiry\"]', '12/25'); page.fill('[name=\"cvv\"]', '123'); page.click('[data-testid=\"place-order\"]'); expect(page).to_have_url('/order-confirmation', timeout=10000)"
    },
    {
      "subtask_number": 6,
      "name": "Test order confirmation display",
      "description": "def test_order_confirmation(authenticated_page: Page): page = authenticated_page; expect(page.locator('[data-testid=\"order-number\"]')).to_be_visible(); order_number = page.locator('[data-testid=\"order-number\"]').inner_text(); assert len(order_number) > 0; expect(page.locator('[data-testid=\"confirmation-message\"]')).to_contain_text('Thank you for your order'); expect(page.locator('[data-testid=\"order-summary\"]')).to_be_visible()"
    }
  ]
}
```

### 3.2 Cypress - E2E Feature Test

```json
{
  "task_number": 113,
  "name": "Generate E2E tests for user registration flow",
  "description": "Create tests/e2e/test_registration.cy.js with Cypress tests for user registration including form validation, email verification, and account creation",
  "complexity": "high",
  "depends_on_tasks": [45, 46],
  "target_files": ["tests/e2e/test_registration.cy.js"],
  "estimated_tokens": 750,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Setup Cypress test structure",
      "description": "describe('User Registration Flow', () => { beforeEach(() => { cy.visit('/signup'); cy.intercept('POST', '/api/auth/signup').as('signupRequest'); }); });"
    },
    {
      "subtask_number": 2,
      "name": "Test form validation errors",
      "description": "it('shows validation errors for invalid inputs', () => { cy.get('[data-cy=\"signup-button\"]').click(); cy.get('[data-cy=\"email-error\"]').should('contain', 'Email is required'); cy.get('[data-cy=\"password-error\"]').should('contain', 'Password is required'); cy.get('[data-cy=\"email\"]').type('invalid-email'); cy.get('[data-cy=\"signup-button\"]').click(); cy.get('[data-cy=\"email-error\"]').should('contain', 'Invalid email format'); });"
    },
    {
      "subtask_number": 3,
      "name": "Test password strength indicator",
      "description": "it('shows password strength indicator', () => { cy.get('[data-cy=\"password\"]').type('weak'); cy.get('[data-cy=\"password-strength\"]').should('have.class', 'weak'); cy.get('[data-cy=\"password\"]').clear().type('Strong@Pass123'); cy.get('[data-cy=\"password-strength\"]').should('have.class', 'strong'); });"
    },
    {
      "subtask_number": 4,
      "name": "Test successful registration",
      "description": "it('successfully registers a new user', () => { cy.get('[data-cy=\"name\"]').type('Test User'); cy.get('[data-cy=\"email\"]').type('newuser@test.com'); cy.get('[data-cy=\"password\"]').type('SecurePass123!'); cy.get('[data-cy=\"confirm-password\"]').type('SecurePass123!'); cy.get('[data-cy=\"signup-button\"]').click(); cy.wait('@signupRequest'); cy.url().should('include', '/verify-email'); cy.get('[data-cy=\"verification-message\"]').should('contain', 'Check your email'); });"
    },
    {
      "subtask_number": 5,
      "name": "Test duplicate email error",
      "description": "it('shows error for duplicate email', () => { cy.intercept('POST', '/api/auth/signup', { statusCode: 409, body: { detail: 'Email already exists' } }).as('signupDuplicate'); cy.get('[data-cy=\"email\"]').type('existing@test.com'); cy.get('[data-cy=\"password\"]').type('SecurePass123!'); cy.get('[data-cy=\"signup-button\"]').click(); cy.wait('@signupDuplicate'); cy.get('[data-cy=\"error-message\"]').should('contain', 'Email already exists'); });"
    }
  ]
}
```

---

## 4. Contract Testing Templates

### 4.1 Pydantic Schema Contract Test

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
      "description": "import pytest; from pydantic import ValidationError; from datetime import datetime; from src.api.schemas.order import CreateOrderRequest, OrderResponse, OrderStatus, OrderItem"
    },
    {
      "subtask_number": 2,
      "name": "Test valid CreateOrderRequest schema",
      "description": "def test_create_order_request_valid(): request = CreateOrderRequest(items=[OrderItem(product_id=1, quantity=2, price=29.99)], shipping_address='123 Main St', payment_method='credit_card'); assert request.items[0].quantity == 2; assert request.items[0].product_id == 1; assert len(request.items) == 1"
    },
    {
      "subtask_number": 3,
      "name": "Test CreateOrderRequest with missing required fields",
      "description": "def test_create_order_request_missing_fields(): with pytest.raises(ValidationError) as exc_info: CreateOrderRequest(items=[], shipping_address='123 St'); errors = exc_info.value.errors(); assert any(e['loc'] == ('items',) for e in errors); assert any('at least one item' in str(e['msg']).lower() for e in errors)"
    },
    {
      "subtask_number": 4,
      "name": "Test OrderResponse schema structure",
      "description": "def test_order_response_schema(): response = OrderResponse(order_id='ORD-12345', status=OrderStatus.PENDING, total=99.99, items=[OrderItem(product_id=1, quantity=2, price=49.99)], created_at=datetime.now()); assert response.order_id == 'ORD-12345'; assert response.status == OrderStatus.PENDING; assert response.total == 99.99; assert len(response.items) == 1"
    },
    {
      "subtask_number": 5,
      "name": "Test OrderStatus enum validation",
      "description": "def test_order_status_enum(): assert OrderStatus.PENDING in OrderStatus; assert OrderStatus.PROCESSING in OrderStatus; assert OrderStatus.SHIPPED in OrderStatus; assert OrderStatus.DELIVERED in OrderStatus; with pytest.raises(ValueError): OrderResponse(order_id='123', status='INVALID_STATUS', total=10.0, items=[], created_at=datetime.now())"
    },
    {
      "subtask_number": 6,
      "name": "Test OrderItem nested schema validation",
      "description": "def test_order_item_validation(): with pytest.raises(ValidationError): OrderItem(product_id=-1, quantity=0, price=-10.00); valid_item = OrderItem(product_id=1, quantity=2, price=29.99); assert valid_item.product_id > 0; assert valid_item.quantity > 0; assert valid_item.price > 0"
    }
  ]
}
```

### 4.2 GraphQL Schema Contract Test

```json
{
  "task_number": 117,
  "name": "Generate contract tests for GraphQL User schema",
  "description": "Create tests/contracts/test_user_graphql.py with GraphQL schema validation tests for User type queries and mutations",
  "complexity": "medium",
  "depends_on_tasks": [62],
  "target_files": ["tests/contracts/test_user_graphql.py"],
  "estimated_tokens": 700,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import GraphQL test dependencies",
      "description": "import pytest; from graphene.test import Client; from src.graphql.schema import schema; from tests.fixtures import mock_user_data"
    },
    {
      "subtask_number": 2,
      "name": "Test User query schema contract",
      "description": "def test_user_query_schema(): client = Client(schema); query = '''{ user(id: \"1\") { id email name createdAt } }'''; result = client.execute(query); assert 'errors' not in result; assert 'data' in result; assert 'user' in result['data']; assert 'id' in result['data']['user']; assert 'email' in result['data']['user']"
    },
    {
      "subtask_number": 3,
      "name": "Test createUser mutation schema contract",
      "description": "def test_create_user_mutation_schema(): client = Client(schema); mutation = '''mutation { createUser(input: { email: \"test@example.com\", password: \"pass123\", name: \"Test User\" }) { user { id email name } errors } }'''; result = client.execute(mutation); assert 'errors' not in result; assert 'createUser' in result['data']; assert 'user' in result['data']['createUser']; assert 'errors' in result['data']['createUser']"
    },
    {
      "subtask_number": 4,
      "name": "Test invalid field query returns error",
      "description": "def test_invalid_field_query(): client = Client(schema); query = '''{ user(id: \"1\") { invalidField } }'''; result = client.execute(query); assert 'errors' in result; assert any('invalidField' in str(e) for e in result['errors'])"
    },
    {
      "subtask_number": 5,
      "name": "Test required argument validation",
      "description": "def test_required_argument_validation(): client = Client(schema); mutation = '''mutation { createUser(input: { email: \"test@example.com\" }) { user { id } } }'''; result = client.execute(mutation); assert 'errors' in result; assert any('password' in str(e).lower() for e in result['errors'])"
    }
  ]
}
```

---

## 5. Performance Testing Templates

### 5.1 Locust Load Test

```json
{
  "task_number": 118,
  "name": "Generate load tests for API endpoints",
  "description": "Create tests/performance/test_api_load.py with Locust performance tests for API endpoints covering concurrent users, response times, and throughput",
  "complexity": "medium",
  "depends_on_tasks": [45, 50],
  "target_files": ["tests/performance/test_api_load.py"],
  "estimated_tokens": 650,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import Locust dependencies",
      "description": "from locust import HttpUser, task, between; import json; from random import randint"
    },
    {
      "subtask_number": 2,
      "name": "Define API user behavior class",
      "description": "class APIUser(HttpUser): wait_time = between(1, 3); def on_start(self): response = self.client.post('/api/auth/login', json={'email': 'test@example.com', 'password': 'pass123'}); self.token = response.json()['access_token']"
    },
    {
      "subtask_number": 3,
      "name": "Test GET products list load",
      "description": "@task(3); def get_products(self): headers = {'Authorization': f'Bearer {self.token}'}; self.client.get('/api/products', headers=headers, name='/api/products')"
    },
    {
      "subtask_number": 4,
      "name": "Test GET single product load",
      "description": "@task(2); def get_product_detail(self): product_id = randint(1, 100); headers = {'Authorization': f'Bearer {self.token}'}; self.client.get(f'/api/products/{product_id}', headers=headers, name='/api/products/:id')"
    },
    {
      "subtask_number": 5,
      "name": "Test POST create order load",
      "description": "@task(1); def create_order(self): headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}; payload = {'items': [{'product_id': randint(1, 50), 'quantity': randint(1, 5)}], 'shipping_address': '123 Test St'}; self.client.post('/api/orders', json=payload, headers=headers, name='/api/orders')"
    }
  ]
}
```

---

## 6. Database Testing Templates

### 6.1 SQLAlchemy Database Integration Test

```json
{
  "task_number": 119,
  "name": "Generate database integration tests for User repository",
  "description": "Create tests/database/test_user_repository.py with pytest tests for User repository covering CRUD operations, transactions, and query optimization",
  "complexity": "medium",
  "depends_on_tasks": [15, 18],
  "target_files": ["tests/database/test_user_repository.py"],
  "estimated_tokens": 750,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import database test dependencies",
      "description": "import pytest; from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker; from src.database.models import User, Base; from src.repositories.user_repository import UserRepository; from tests.fixtures import test_db_engine"
    },
    {
      "subtask_number": 2,
      "name": "Test user creation transaction",
      "description": "def test_create_user_transaction(test_db_session): repo = UserRepository(test_db_session); user = repo.create(email='test@example.com', password='hash123', name='Test User'); test_db_session.commit(); assert user.id is not None; retrieved = repo.get_by_id(user.id); assert retrieved.email == 'test@example.com'"
    },
    {
      "subtask_number": 3,
      "name": "Test user query by email (indexed)",
      "description": "def test_get_user_by_email_performance(test_db_session): repo = UserRepository(test_db_session); user = repo.create(email='indexed@test.com', password='hash'); test_db_session.commit(); import time; start = time.time(); result = repo.get_by_email('indexed@test.com'); duration = time.time() - start; assert result.email == 'indexed@test.com'; assert duration < 0.1"
    },
    {
      "subtask_number": 4,
      "name": "Test bulk user insert with transaction",
      "description": "def test_bulk_user_insert(test_db_session): repo = UserRepository(test_db_session); users = [User(email=f'user{i}@test.com', password=f'hash{i}') for i in range(100)]; test_db_session.bulk_save_objects(users); test_db_session.commit(); count = test_db_session.query(User).count(); assert count >= 100"
    },
    {
      "subtask_number": 5,
      "name": "Test rollback on constraint violation",
      "description": "def test_rollback_on_duplicate_email(test_db_session): repo = UserRepository(test_db_session); repo.create(email='duplicate@test.com', password='hash1'); test_db_session.commit(); with pytest.raises(Exception): repo.create(email='duplicate@test.com', password='hash2'); test_db_session.commit(); test_db_session.rollback(); users = repo.get_by_email('duplicate@test.com'); assert len([users]) == 1"
    }
  ]
}
```

---

## 7. Security Testing Templates

### 7.1 Authentication Security Test

```json
{
  "task_number": 120,
  "name": "Generate security tests for authentication system",
  "description": "Create tests/security/test_auth_security.py with pytest tests covering JWT security, password hashing, rate limiting, and CSRF protection",
  "complexity": "high",
  "depends_on_tasks": [45, 46, 47],
  "target_files": ["tests/security/test_auth_security.py"],
  "estimated_tokens": 800,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import security test dependencies",
      "description": "import pytest; from fastapi.testclient import TestClient; from jose import jwt; from datetime import datetime, timedelta; from src.auth.security import verify_password, create_access_token, decode_token"
    },
    {
      "subtask_number": 2,
      "name": "Test password hashing security (bcrypt)",
      "description": "def test_password_hashing_security(): plain_password = 'SecurePassword123!'; hashed = hash_password(plain_password); assert hashed != plain_password; assert len(hashed) > 50; assert hashed.startswith('$2b$'); assert verify_password(plain_password, hashed) == True; assert verify_password('WrongPassword', hashed) == False"
    },
    {
      "subtask_number": 3,
      "name": "Test JWT token tampering detection",
      "description": "def test_jwt_tampering_detection(): token = create_access_token({'sub': 'user@test.com'}); parts = token.split('.'); tampered = parts[0] + '.TAMPERED.' + parts[2]; with pytest.raises(jwt.JWTError): decode_token(tampered)"
    },
    {
      "subtask_number": 4,
      "name": "Test JWT expiration enforcement",
      "description": "def test_jwt_expiration(): expired_token = create_access_token({'sub': 'user@test.com'}, expires_delta=timedelta(seconds=-10)); with pytest.raises(jwt.ExpiredSignatureError): decode_token(expired_token)"
    },
    {
      "subtask_number": 5,
      "name": "Test rate limiting on login endpoint",
      "description": "def test_login_rate_limiting(client): for i in range(5): response = client.post('/api/auth/login', json={'email': 'test@test.com', 'password': 'wrong'}); response = client.post('/api/auth/login', json={'email': 'test@test.com', 'password': 'wrong'}); assert response.status_code == 429; assert 'rate limit' in response.json()['detail'].lower()"
    },
    {
      "subtask_number": 6,
      "name": "Test CSRF token validation",
      "description": "def test_csrf_protection(client, auth_headers): response = client.post('/api/sensitive-action', headers=auth_headers); assert response.status_code == 403; assert 'csrf' in response.json()['detail'].lower(); csrf_token = client.get('/api/csrf-token').json()['token']; headers = {**auth_headers, 'X-CSRF-Token': csrf_token}; response = client.post('/api/sensitive-action', headers=headers); assert response.status_code != 403"
    }
  ]
}
```

---

## 8. Accessibility Testing Templates

### 8.1 Axe-core Accessibility Test

```json
{
  "task_number": 121,
  "name": "Generate accessibility tests for main pages",
  "description": "Create tests/accessibility/test_wcag_compliance.py with Playwright and axe-core for automated WCAG 2.1 AA compliance testing",
  "complexity": "medium",
  "depends_on_tasks": [60, 65],
  "target_files": ["tests/accessibility/test_wcag_compliance.py"],
  "estimated_tokens": 700,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import accessibility test dependencies",
      "description": "import pytest; from playwright.sync_api import Page; from axe_playwright_python import Axe; from tests.e2e.fixtures import authenticated_page"
    },
    {
      "subtask_number": 2,
      "name": "Test homepage accessibility compliance",
      "description": "def test_homepage_wcag_compliance(page: Page): page.goto('/'); axe = Axe(); results = axe.run(page); assert len(results.violations) == 0, f'WCAG violations found: {results.violations}'"
    },
    {
      "subtask_number": 3,
      "name": "Test form accessibility (labels, ARIA)",
      "description": "def test_login_form_accessibility(page: Page): page.goto('/login'); axe = Axe(); results = axe.run(page); violations = results.violations; label_violations = [v for v in violations if 'label' in v['id'].lower()]; assert len(label_violations) == 0, 'Form inputs missing labels'; aria_violations = [v for v in violations if 'aria' in v['id'].lower()]; assert len(aria_violations) == 0, 'ARIA attributes invalid'"
    },
    {
      "subtask_number": 4,
      "name": "Test keyboard navigation accessibility",
      "description": "def test_keyboard_navigation(page: Page): page.goto('/'); page.keyboard.press('Tab'); focused = page.evaluate('document.activeElement.tagName'); assert focused in ['A', 'BUTTON', 'INPUT'], 'First tab should focus interactive element'; skip_link = page.locator('a[href=\"#main-content\"]'); assert skip_link.is_visible(), 'Skip to main content link missing'"
    },
    {
      "subtask_number": 5,
      "name": "Test color contrast ratios",
      "description": "def test_color_contrast(page: Page): page.goto('/'); axe = Axe(); results = axe.run(page, options={'runOnly': ['color-contrast']}); contrast_violations = results.violations; assert len(contrast_violations) == 0, f'Color contrast violations: {[v[\"description\"] for v in contrast_violations]}'"
    },
    {
      "subtask_number": 6,
      "name": "Test screen reader compatibility",
      "description": "def test_screen_reader_compatibility(page: Page): page.goto('/dashboard'); landmarks = page.locator('[role=\"main\"], [role=\"navigation\"], [role=\"complementary\"]'); assert landmarks.count() > 0, 'No ARIA landmarks found'; headings = page.locator('h1, h2, h3'); assert headings.count() > 0, 'No heading structure found'; first_heading = page.locator('h1').first; assert first_heading.is_visible(), 'Main h1 heading missing'"
    }
  ]
}
```

---

## 9. Tech Stack Specific Templates

### 9.1 Next.js API Route Test

```json
{
  "task_number": 122,
  "name": "Generate tests for Next.js API routes",
  "description": "Create tests/api/test_nextjs_routes.test.js with Jest tests for Next.js API routes covering request handling, middleware, and error responses",
  "complexity": "medium",
  "depends_on_tasks": [52],
  "target_files": ["tests/api/test_nextjs_routes.test.js"],
  "estimated_tokens": 700,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import Next.js test dependencies",
      "description": "import { createMocks } from 'node-mocks-http'; import handler from '@/pages/api/users/[id]'; import { getSession } from 'next-auth/react';"
    },
    {
      "subtask_number": 2,
      "name": "Test GET request with valid ID",
      "description": "test('GET /api/users/:id returns user data', async () => { const { req, res } = createMocks({ method: 'GET', query: { id: '123' } }); await handler(req, res); expect(res._getStatusCode()).toBe(200); const data = JSON.parse(res._getData()); expect(data.id).toBe('123'); expect(data.email).toBeDefined(); });"
    },
    {
      "subtask_number": 3,
      "name": "Test authentication middleware",
      "description": "test('requires authentication for protected route', async () => { getSession.mockResolvedValue(null); const { req, res } = createMocks({ method: 'GET', query: { id: '123' } }); await handler(req, res); expect(res._getStatusCode()).toBe(401); });"
    },
    {
      "subtask_number": 4,
      "name": "Test method not allowed",
      "description": "test('returns 405 for unsupported methods', async () => { const { req, res } = createMocks({ method: 'PATCH', query: { id: '123' } }); await handler(req, res); expect(res._getStatusCode()).toBe(405); expect(res._getData()).toContain('Method Not Allowed'); });"
    },
    {
      "subtask_number": 5,
      "name": "Test error handling for invalid ID",
      "description": "test('returns 400 for invalid ID format', async () => { const { req, res } = createMocks({ method: 'GET', query: { id: 'invalid' } }); await handler(req, res); expect(res._getStatusCode()).toBe(400); expect(JSON.parse(res._getData()).error).toContain('Invalid ID'); });"
    }
  ]
}
```

### 9.2 Django REST Framework Serializer Test

```json
{
  "task_number": 123,
  "name": "Generate tests for DRF serializers",
  "description": "Create tests/serializers/test_product_serializer.py with Django TestCase for ProductSerializer covering validation, nested serialization, and custom fields",
  "complexity": "low",
  "depends_on_tasks": [21],
  "target_files": ["tests/serializers/test_product_serializer.py"],
  "estimated_tokens": 650,
  "subtasks": [
    {
      "subtask_number": 1,
      "name": "Import DRF test dependencies",
      "description": "from django.test import TestCase; from rest_framework.exceptions import ValidationError; from products.serializers import ProductSerializer, CategorySerializer; from products.models import Product, Category"
    },
    {
      "subtask_number": 2,
      "name": "Test serializer with valid data",
      "description": "def test_product_serializer_valid_data(self): category = Category.objects.create(name='Electronics'); data = {'name': 'Laptop', 'price': '999.99', 'category': category.id, 'stock': 10}; serializer = ProductSerializer(data=data); self.assertTrue(serializer.is_valid()); product = serializer.save(); self.assertEqual(product.name, 'Laptop'); self.assertEqual(product.category.id, category.id)"
    },
    {
      "subtask_number": 3,
      "name": "Test serializer validation errors",
      "description": "def test_product_serializer_invalid_price(self): data = {'name': 'Test', 'price': '-10.00', 'stock': 5}; serializer = ProductSerializer(data=data); self.assertFalse(serializer.is_valid()); self.assertIn('price', serializer.errors); self.assertIn('must be positive', str(serializer.errors['price']).lower())"
    },
    {
      "subtask_number": 4,
      "name": "Test nested serializer read",
      "description": "def test_nested_category_serializer_read(self): category = Category.objects.create(name='Electronics'); product = Product.objects.create(name='Laptop', price='999.99', category=category); serializer = ProductSerializer(product); data = serializer.data; self.assertEqual(data['category']['name'], 'Electronics'); self.assertIn('id', data['category'])"
    },
    {
      "subtask_number": 5,
      "name": "Test custom field serialization",
      "description": "def test_custom_field_total_value(self): product = Product.objects.create(name='Laptop', price='999.99', stock=5); serializer = ProductSerializer(product); data = serializer.data; self.assertIn('total_value', data); self.assertEqual(float(data['total_value']), 999.99 * 5)"
    }
  ]
}
```

---

## 10. Summary Table

| Test Type | Template Count | Primary Frameworks | Complexity Range |
|-----------|---------------|-------------------|------------------|
| Backend Unit | 3 | Python/FastAPI, Django, Node.js | Low - Medium |
| Backend Integration | 2 | FastAPI, Express | Medium |
| Frontend Unit | 2 | React, Vue | Low - Medium |
| E2E Tests | 2 | Playwright, Cypress | High |
| Contract Tests | 2 | Pydantic, GraphQL | Low - Medium |
| Performance Tests | 1 | Locust | Medium |
| Database Tests | 1 | SQLAlchemy | Medium |
| Security Tests | 1 | pytest, JWT | High |
| Accessibility Tests | 1 | Playwright, axe-core | Medium |
| Framework-Specific | 2 | Next.js, Django REST | Low - Medium |

**Total Templates**: 17 comprehensive testing task templates

---

## Usage Guidelines

### Selecting the Right Template

1. **Identify Test Type**: Unit, Integration, E2E, Contract, Performance, Security, or Accessibility
2. **Match Tech Stack**: Choose template matching project's framework (FastAPI, Django, React, etc.)
3. **Adjust Complexity**: Modify subtask count based on component complexity
4. **Update Dependencies**: Ensure `depends_on_tasks` references correct implementation tasks
5. **Verify File Paths**: Confirm `target_files` match project test directory structure

### Customizing Templates

```python
# Template customization checklist:
- [ ] Update task_number to match MasterPlan sequence
- [ ] Modify name and description for specific component
- [ ] Set complexity based on component size and logic
- [ ] Add correct depends_on_tasks references
- [ ] Verify target_files path matches project structure
- [ ] Adjust estimated_tokens for component size
- [ ] Add/remove subtasks based on test coverage needs
- [ ] Ensure subtask descriptions match project patterns
```

### Quality Standards

All testing task templates MUST:
- Specify exact test file path in `target_files`
- Include 4-7 specific subtasks describing test cases
- Depend on implementation tasks (avoid orphan tests)
- Use project-appropriate testing framework
- Follow project naming conventions
- Cover critical test scenarios (happy path, edge cases, errors)

---

**Next Implementation Steps**:
1. Integrate templates into MASTERPLAN_SYSTEM_PROMPT
2. Add template selection logic based on project tech stack
3. Validate generated testing tasks against templates
4. Monitor testing task quality in first 10 MasterPlans
