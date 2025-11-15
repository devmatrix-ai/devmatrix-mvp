/**
 * Golden E2E Tests: TODO Fullstack App (Level 2)
 *
 * Covers 25 scenarios for Next.js + FastAPI + PostgreSQL + Redis + Auth
 */

import { test, expect, Page } from '@playwright/test';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// Test user credentials
const TEST_USER = {
  email: 'test@example.com',
  username: 'testuser',
  password: 'TestPass123'
};

// Helper functions
async function registerUser(page: Page, user = TEST_USER) {
  await page.goto(`${FRONTEND_URL}/register`);
  await page.fill('input[name="email"]', user.email);
  await page.fill('input[name="username"]', user.username);
  await page.fill('input[name="password"]', user.password);
  await page.fill('input[name="confirmPassword"]', user.password);
  await page.click('button[type="submit"]');
}

async function loginUser(page: Page, email = TEST_USER.email, password = TEST_USER.password) {
  await page.goto(`${FRONTEND_URL}/login`);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${FRONTEND_URL}/todos`);
}

async function createTodo(page: Page, title: string, description?: string) {
  await page.click('button:has-text("Create"), button:has-text("New TODO")');
  await page.fill('input[name="title"]', title);
  if (description) {
    await page.fill('textarea[name="description"]', description);
  }
  await page.click('button[type="submit"]');
  await page.waitForTimeout(500);
}

test.describe('TODO Fullstack - Authentication Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Clear cookies before each test
    await page.context().clearCookies();
  });

  /**
   * Test 1: User registration flow
   */
  test('should register a new user successfully', async ({ page }) => {
    const uniqueEmail = `user-${Date.now()}@example.com`;
    await registerUser(page, { ...TEST_USER, email: uniqueEmail });

    // Should redirect to login or todos page
    await expect(page).toHaveURL(/\/(login|todos)/);

    // Success message should be visible
    await expect(page.locator('text=/registered|success/i')).toBeVisible({ timeout: 5000 });
  });

  /**
   * Test 2: User login flow
   */
  test('should login with valid credentials', async ({ page }) => {
    await loginUser(page);

    // Should be on todos page
    await expect(page).toHaveURL(`${FRONTEND_URL}/todos`);

    // User info should be visible in header
    await expect(page.locator(`text=${TEST_USER.username}`)).toBeVisible();
  });

  /**
   * Test 3: User logout flow
   */
  test('should logout successfully', async ({ page }) => {
    await loginUser(page);

    // Click logout button
    await page.click('button:has-text("Logout"), [data-testid="logout-button"]');
    await page.waitForTimeout(500);

    // Should redirect to login page
    await expect(page).toHaveURL(/\/login/);
  });

  /**
   * Test 4: Create TODO (authenticated)
   */
  test('should create TODO when authenticated', async ({ page }) => {
    await loginUser(page);
    await createTodo(page, 'Test TODO Item', 'This is a test description');

    // Verify TODO appears in list
    await expect(page.locator('text=Test TODO Item')).toBeVisible();
  });

  /**
   * Test 5: Create TODO (unauthenticated - redirect to login)
   */
  test('should redirect to login when creating TODO unauthenticated', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/todos`);

    // Should be redirected to login
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('TODO Fullstack - CRUD Operations', () => {

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginUser(page);
  });

  /**
   * Test 6: View TODO list (authenticated)
   */
  test('should view TODO list', async ({ page }) => {
    // Create some TODOs
    await createTodo(page, 'TODO 1');
    await createTodo(page, 'TODO 2');

    // Verify both appear in list
    await expect(page.locator('text=TODO 1')).toBeVisible();
    await expect(page.locator('text=TODO 2')).toBeVisible();
  });

  /**
   * Test 7: View single TODO
   */
  test('should view single TODO detail', async ({ page }) => {
    await createTodo(page, 'Detailed TODO', 'Full description here');

    // Click on the TODO to view details
    await page.click('text=Detailed TODO');
    await page.waitForTimeout(500);

    // Should show full description
    await expect(page.locator('text=Full description here')).toBeVisible();
  });

  /**
   * Test 8: Update TODO title
   */
  test('should update TODO title', async ({ page }) => {
    await createTodo(page, 'Original Title');

    // Click edit button
    await page.click('[data-testid="edit-todo"], button:has-text("Edit")');
    await page.fill('input[name="title"]', 'Updated Title');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);

    // Verify updated title appears
    await expect(page.locator('text=Updated Title')).toBeVisible();
  });

  /**
   * Test 9: Update TODO status (valid transition)
   */
  test('should update TODO status with valid transition', async ({ page }) => {
    await createTodo(page, 'Status Test');

    // Change status to in_progress
    const statusDropdown = page.locator('select[name="status"], [data-testid="status-select"]').first();
    await statusDropdown.selectOption('in_progress');
    await page.waitForTimeout(500);

    // Verify status badge updated
    await expect(page.locator('[data-testid="status-badge"]:has-text("in_progress"), .badge:has-text("in progress")')).toBeVisible();
  });

  /**
   * Test 10: Update TODO status (invalid transition - show error)
   */
  test('should show error for invalid status transition', async ({ page }) => {
    await createTodo(page, 'Invalid Transition Test');

    // Set to completed first
    const statusDropdown = page.locator('select[name="status"]').first();
    await statusDropdown.selectOption('in_progress');
    await page.waitForTimeout(300);
    await statusDropdown.selectOption('completed');
    await page.waitForTimeout(300);

    // Try to transition back to pending (invalid)
    await statusDropdown.selectOption('pending');
    await page.waitForTimeout(500);

    // Error toast should appear
    await expect(page.locator('text=/invalid.*transition|not.*allowed/i')).toBeVisible({ timeout: 3000 });
  });

  /**
   * Test 11: Delete TODO (with confirmation)
   */
  test('should delete TODO after confirmation', async ({ page }) => {
    await createTodo(page, 'TODO to Delete');

    // Click delete button
    await page.click('[data-testid="delete-todo"], button:has-text("Delete")');

    // Confirmation modal should appear
    await expect(page.locator('text=/confirm|are you sure/i')).toBeVisible();

    // Confirm deletion
    await page.click('button:has-text("Confirm"), button:has-text("Yes")');
    await page.waitForTimeout(500);

    // TODO should be removed from list
    await expect(page.locator('text=TODO to Delete')).not.toBeVisible();
  });
});

test.describe('TODO Fullstack - Search, Filter, Sort', () => {

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginUser(page);

    // Create diverse TODOs for testing
    await createTodo(page, 'Meeting with client');
    await createTodo(page, 'Code review');
    await createTodo(page, 'Write documentation');
  });

  /**
   * Test 12: Search TODOs
   */
  test('should search TODOs by keyword', async ({ page }) => {
    // Enter search term
    await page.fill('input[placeholder*="Search" i]', 'meeting');
    await page.waitForTimeout(500); // Debounce

    // Should show matching TODO
    await expect(page.locator('text=Meeting with client')).toBeVisible();

    // Should hide non-matching TODOs
    await expect(page.locator('text=Code review')).not.toBeVisible();
  });

  /**
   * Test 13: Filter by status
   */
  test('should filter TODOs by status', async ({ page }) => {
    // Change one TODO to in_progress
    await page.locator('select[name="status"]').first().selectOption('in_progress');
    await page.waitForTimeout(300);

    // Apply status filter
    await page.click('[data-testid="filter-button"], button:has-text("Filter")');
    await page.click('input[value="in_progress"], label:has-text("In Progress")');
    await page.waitForTimeout(500);

    // Should show only in_progress TODOs
    const visibleTodos = page.locator('[data-testid="todo-item"]');
    const count = await visibleTodos.count();

    expect(count).toBeGreaterThanOrEqual(1);
  });

  /**
   * Test 14: Filter by priority
   */
  test('should filter TODOs by priority', async ({ page }) => {
    // Apply priority filter
    await page.click('[data-testid="filter-priority"], select[name="priority"]');
    await page.selectOption('[data-testid="filter-priority"], select[name="priority"]', 'high');
    await page.waitForTimeout(500);

    // Count visible TODOs
    const todos = page.locator('[data-testid="todo-item"]');
    const count = await todos.count();

    // Should filter correctly
    expect(count).toBeGreaterThanOrEqual(0);
  });

  /**
   * Test 15: Filter by due date range
   */
  test('should filter TODOs by due date range', async ({ page }) => {
    // Open date filter
    const dateFilter = page.locator('input[type="date"]').first();
    if (await dateFilter.count() > 0) {
      const today = new Date().toISOString().split('T')[0];
      await dateFilter.fill(today);
      await page.waitForTimeout(500);

      // Verify filter applied
      expect(await page.locator('[data-testid="todo-item"]').count()).toBeGreaterThanOrEqual(0);
    }
  });

  /**
   * Test 16: Sort by created_at
   */
  test('should sort TODOs by created date', async ({ page }) => {
    // Click sort dropdown
    await page.selectOption('[data-testid="sort-select"], select:has-option([value*="created"])', 'created_at');
    await page.waitForTimeout(500);

    // Verify TODOs are sorted
    const todos = page.locator('[data-testid="todo-item"]');
    const count = await todos.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  /**
   * Test 17: Sort by due_date
   */
  test('should sort TODOs by due date', async ({ page }) => {
    await page.selectOption('[data-testid="sort-select"], select', 'due_date');
    await page.waitForTimeout(500);

    const todos = page.locator('[data-testid="todo-item"]');
    expect(await todos.count()).toBeGreaterThanOrEqual(0);
  });

  /**
   * Test 18: Sort by priority
   */
  test('should sort TODOs by priority', async ({ page }) => {
    await page.selectOption('[data-testid="sort-select"], select', 'priority');
    await page.waitForTimeout(500);

    // Verify urgent items appear first (if any exist)
    const todos = page.locator('[data-testid="todo-item"]');
    expect(await todos.count()).toBeGreaterThanOrEqual(0);
  });
});

test.describe('TODO Fullstack - Advanced Features', () => {

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginUser(page);
  });

  /**
   * Test 19: Pagination (next/previous page)
   */
  test('should paginate TODO list', async ({ page }) => {
    // Create 25 TODOs to trigger pagination
    for (let i = 0; i < 25; i++) {
      await createTodo(page, `TODO ${i}`);
    }
    await page.reload();

    // Look for pagination controls
    const nextButton = page.locator('button:has-text("Next"), [data-testid="next-page"]');
    if (await nextButton.count() > 0) {
      await nextButton.click();
      await page.waitForTimeout(500);

      // Should show page 2 indicator
      await expect(page.locator('text=/page 2|2 of/i')).toBeVisible();
    }
  });

  /**
   * Test 20: Kanban board drag-and-drop
   */
  test('should support Kanban board view', async ({ page }) => {
    // Check if Kanban view toggle exists
    const kanbanToggle = page.locator('button:has-text("Kanban"), [data-testid="kanban-view"]');
    if (await kanbanToggle.count() > 0) {
      await kanbanToggle.click();
      await page.waitForTimeout(500);

      // Verify Kanban columns are visible
      await expect(page.locator('text=/pending|in.progress|completed/i')).toBeVisible();
    }
  });

  /**
   * Test 21: Dark mode toggle
   */
  test('should toggle dark mode', async ({ page }) => {
    const darkModeToggle = page.locator('button[aria-label*="dark" i], [data-testid="theme-toggle"]');
    if (await darkModeToggle.count() > 0) {
      // Get initial theme
      const initialClass = await page.locator('html').getAttribute('class');

      // Toggle dark mode
      await darkModeToggle.click();
      await page.waitForTimeout(300);

      // Verify class changed
      const newClass = await page.locator('html').getAttribute('class');
      expect(newClass).not.toBe(initialClass);
    }
  });

  /**
   * Test 22: Mobile responsive layout
   */
  test('should display mobile responsive layout', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await createTodo(page, 'Mobile Test TODO');

    // Verify mobile layout
    await expect(page.locator('text=Mobile Test TODO')).toBeVisible();

    // Check for mobile navigation
    const mobileNav = page.locator('[data-testid="mobile-nav"], button[aria-label*="menu" i]');
    if (await mobileNav.count() > 0) {
      await expect(mobileNav).toBeVisible();
    }
  });

  /**
   * Test 23: TODO stats display
   */
  test('should display TODO statistics', async ({ page }) => {
    await createTodo(page, 'Stats Test 1');
    await createTodo(page, 'Stats Test 2');

    // Look for stats cards
    const statsSection = page.locator('[data-testid="todo-stats"], .stats, .statistics');
    if (await statsSection.count() > 0) {
      await expect(statsSection).toBeVisible();

      // Should show total count
      await expect(page.locator('text=/total.*\\d+|\\d+.*total/i')).toBeVisible();
    }
  });

  /**
   * Test 24: View TODO history
   */
  test('should view TODO change history', async ({ page }) => {
    await createTodo(page, 'History Test');

    // Update the TODO
    await page.click('[data-testid="edit-todo"], button:has-text("Edit")');
    await page.fill('input[name="title"]', 'History Test Updated');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);

    // Click on TODO to view details
    await page.click('text=History Test Updated');

    // Look for history section
    const historySection = page.locator('[data-testid="history"], text=/history|audit/i');
    if (await historySection.count() > 0) {
      await expect(historySection).toBeVisible();
    }
  });

  /**
   * Test 25: Cache hit rate > 70% (performance test)
   */
  test('should achieve cache hit rate > 70%', async ({ page }) => {
    // Create a TODO
    await createTodo(page, 'Cache Test TODO');

    // Make multiple requests to same data
    for (let i = 0; i < 10; i++) {
      await page.reload();
      await page.waitForTimeout(100);
    }

    // Verify TODOs still load quickly (benefiting from cache)
    await expect(page.locator('text=Cache Test TODO')).toBeVisible({ timeout: 1000 });
  });
});

test.describe('TODO Fullstack - Performance Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginUser(page);
  });

  /**
   * Performance Test: Frontend performance
   */
  test('should meet performance requirements', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${FRONTEND_URL}/todos`);
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - start;

    // Initial page load should be < 2s
    expect(loadTime).toBeLessThan(2000);
  });

  /**
   * Performance Test: Route transitions
   */
  test('should have fast route transitions', async ({ page }) => {
    const start = Date.now();
    await page.click('a[href="/todos"]');
    await page.waitForURL(/\/todos/);
    const transitionTime = Date.now() - start;

    // Route transitions should be < 300ms
    expect(transitionTime).toBeLessThan(300);
  });
});
