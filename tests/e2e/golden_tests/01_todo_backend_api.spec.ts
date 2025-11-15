/**
 * Golden E2E Tests: TODO Backend API (Level 1)
 *
 * Covers 15 scenarios for FastAPI + PostgreSQL + Redis backend
 */

import { test, expect } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:8000';

// Helper to make API requests
async function apiRequest(method: string, endpoint: string, data?: any) {
  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (data) {
    options.body = JSON.stringify(data);
  }

  const response = await fetch(`${API_URL}${endpoint}`, options);
  const body = await response.json().catch(() => null);
  return { status: response.status, body };
}

test.describe('TODO Backend API - Golden Tests', () => {

  /**
   * Test 1: All API endpoints working correctly
   */
  test('should have all required API endpoints responding', async () => {
    // Health check
    const health = await apiRequest('GET', '/health');
    expect(health.status).toBe(200);
    expect(health.body).toHaveProperty('status', 'healthy');
    expect(health.body).toHaveProperty('database', 'connected');
    expect(health.body).toHaveProperty('redis', 'connected');

    // Stats endpoint
    const stats = await apiRequest('GET', '/stats');
    expect(stats.status).toBe(200);
    expect(stats.body).toHaveProperty('cache_hits');
    expect(stats.body).toHaveProperty('cache_misses');
    expect(stats.body).toHaveProperty('hit_rate');
  });

  /**
   * Test 2: Create TODO with valid data
   */
  test('should create a new TODO successfully', async () => {
    const newTodo = {
      title: 'Test TODO Item',
      description: 'This is a test TODO description',
      due_date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
      priority: 'high'
    };

    const response = await apiRequest('POST', '/todos', newTodo);

    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('id');
    expect(response.body.title).toBe(newTodo.title);
    expect(response.body.description).toBe(newTodo.description);
    expect(response.body.status).toBe('pending');
    expect(response.body.priority).toBe('high');
    expect(response.body).toHaveProperty('created_at');
    expect(response.body).toHaveProperty('updated_at');
  });

  /**
   * Test 3: Get TODO by ID (with cache)
   */
  test('should retrieve TODO by ID and use cache', async () => {
    // First create a TODO
    const newTodo = {
      title: 'Cached TODO',
      description: 'Testing cache retrieval'
    };
    const createResponse = await apiRequest('POST', '/todos', newTodo);
    const todoId = createResponse.body.id;

    // Get stats before
    const statsBefore = await apiRequest('GET', '/stats');
    const hitsBefore = statsBefore.body.cache_hits;

    // First GET (should miss cache)
    const firstGet = await apiRequest('GET', `/todos/${todoId}`);
    expect(firstGet.status).toBe(200);
    expect(firstGet.body.id).toBe(todoId);

    // Second GET (should hit cache)
    const secondGet = await apiRequest('GET', `/todos/${todoId}`);
    expect(secondGet.status).toBe(200);
    expect(secondGet.body.id).toBe(todoId);

    // Verify cache was used
    const statsAfter = await apiRequest('GET', '/stats');
    expect(statsAfter.body.cache_hits).toBeGreaterThan(hitsBefore);
  });

  /**
   * Test 4: List TODOs with pagination
   */
  test('should list TODOs with pagination', async () => {
    // Create multiple TODOs
    for (let i = 0; i < 5; i++) {
      await apiRequest('POST', '/todos', {
        title: `TODO ${i}`,
        description: `Description ${i}`
      });
    }

    // Test pagination
    const page1 = await apiRequest('GET', '/todos?page=1&limit=3');
    expect(page1.status).toBe(200);
    expect(page1.body.items).toHaveLength(3);
    expect(page1.body.page).toBe(1);
    expect(page1.body.limit).toBe(3);
    expect(page1.body.total).toBeGreaterThanOrEqual(5);

    const page2 = await apiRequest('GET', '/todos?page=2&limit=3');
    expect(page2.status).toBe(200);
    expect(page2.body.page).toBe(2);
  });

  /**
   * Test 5: Filter TODOs by status
   */
  test('should filter TODOs by status', async () => {
    // Create TODOs with different statuses
    const todo1 = await apiRequest('POST', '/todos', { title: 'Pending TODO' });
    const todo2 = await apiRequest('POST', '/todos', { title: 'In Progress TODO' });
    await apiRequest('PUT', `/todos/${todo2.body.id}`, { status: 'in_progress' });

    // Filter by pending
    const pending = await apiRequest('GET', '/todos?status=pending');
    expect(pending.status).toBe(200);
    expect(pending.body.items.every((t: any) => t.status === 'pending')).toBe(true);

    // Filter by in_progress
    const inProgress = await apiRequest('GET', '/todos?status=in_progress');
    expect(inProgress.status).toBe(200);
    expect(inProgress.body.items.every((t: any) => t.status === 'in_progress')).toBe(true);
  });

  /**
   * Test 6: Filter TODOs by priority
   */
  test('should filter TODOs by priority', async () => {
    await apiRequest('POST', '/todos', { title: 'Low priority', priority: 'low' });
    await apiRequest('POST', '/todos', { title: 'High priority', priority: 'high' });

    const high = await apiRequest('GET', '/todos?priority=high');
    expect(high.status).toBe(200);
    expect(high.body.items.every((t: any) => t.priority === 'high')).toBe(true);
  });

  /**
   * Test 7: Search TODOs by title/description
   */
  test('should search TODOs by text', async () => {
    await apiRequest('POST', '/todos', {
      title: 'Meeting with client',
      description: 'Discuss project requirements'
    });
    await apiRequest('POST', '/todos', {
      title: 'Code review',
      description: 'Review pull requests'
    });

    const search = await apiRequest('GET', '/todos?search=meeting');
    expect(search.status).toBe(200);
    expect(search.body.items.length).toBeGreaterThanOrEqual(1);
    expect(search.body.items.some((t: any) =>
      t.title.toLowerCase().includes('meeting') ||
      t.description?.toLowerCase().includes('meeting')
    )).toBe(true);
  });

  /**
   * Test 8: Update TODO successfully
   */
  test('should update TODO fields', async () => {
    const todo = await apiRequest('POST', '/todos', {
      title: 'Original title',
      description: 'Original description'
    });

    const updated = await apiRequest('PUT', `/todos/${todo.body.id}`, {
      title: 'Updated title',
      priority: 'urgent'
    });

    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe('Updated title');
    expect(updated.body.priority).toBe('urgent');
    expect(updated.body.description).toBe('Original description'); // Unchanged
  });

  /**
   * Test 9: Validate status transitions (valid)
   */
  test('should allow valid status transitions', async () => {
    const todo = await apiRequest('POST', '/todos', { title: 'Status test' });
    const todoId = todo.body.id;

    // pending → in_progress (valid)
    const step1 = await apiRequest('PUT', `/todos/${todoId}`, { status: 'in_progress' });
    expect(step1.status).toBe(200);
    expect(step1.body.status).toBe('in_progress');

    // in_progress → completed (valid)
    const step2 = await apiRequest('PUT', `/todos/${todoId}`, { status: 'completed' });
    expect(step2.status).toBe(200);
    expect(step2.body.status).toBe('completed');

    // Any → archived (valid)
    const step3 = await apiRequest('PUT', `/todos/${todoId}`, { status: 'archived' });
    expect(step3.status).toBe(200);
    expect(step3.body.status).toBe('archived');
  });

  /**
   * Test 10: Validate status transitions (invalid)
   */
  test('should reject invalid status transitions', async () => {
    const todo = await apiRequest('POST', '/todos', { title: 'Invalid transition test' });

    // Set to completed
    await apiRequest('PUT', `/todos/${todo.body.id}`, { status: 'in_progress' });
    await apiRequest('PUT', `/todos/${todo.body.id}`, { status: 'completed' });

    // completed → pending (invalid)
    const invalid = await apiRequest('PUT', `/todos/${todo.body.id}`, { status: 'pending' });
    expect(invalid.status).toBe(400);
    expect(invalid.body).toHaveProperty('detail');
  });

  /**
   * Test 11: Soft delete TODO
   */
  test('should soft delete TODO and invalidate cache', async () => {
    const todo = await apiRequest('POST', '/todos', { title: 'To be deleted' });
    const todoId = todo.body.id;

    // Ensure it's cached
    await apiRequest('GET', `/todos/${todoId}`);

    // Delete
    const deleteResponse = await apiRequest('DELETE', `/todos/${todoId}`);
    expect(deleteResponse.status).toBe(204);

    // Should return 404 after deletion
    const notFound = await apiRequest('GET', `/todos/${todoId}`);
    expect(notFound.status).toBe(404);
  });

  /**
   * Test 12: Validation - title required
   */
  test('should reject TODO creation without title', async () => {
    const response = await apiRequest('POST', '/todos', {
      description: 'No title provided'
    });

    expect(response.status).toBe(422);
    expect(response.body).toHaveProperty('detail');
  });

  /**
   * Test 13: Validation - title max length
   */
  test('should reject title exceeding 200 chars', async () => {
    const longTitle = 'A'.repeat(201);
    const response = await apiRequest('POST', '/todos', { title: longTitle });

    expect(response.status).toBe(422);
  });

  /**
   * Test 14: Cache hit rate > 70%
   */
  test('should achieve cache hit rate > 70%', async () => {
    // Create TODO
    const todo = await apiRequest('POST', '/todos', { title: 'Cache test' });
    const todoId = todo.body.id;

    // Get stats before
    const statsBefore = await apiRequest('GET', '/stats');
    const hitsBefore = statsBefore.body.cache_hits || 0;
    const missesBefore = statsBefore.body.cache_misses || 0;

    // Make 10 requests to same TODO (first miss, rest hits)
    for (let i = 0; i < 10; i++) {
      await apiRequest('GET', `/todos/${todoId}`);
    }

    // Get stats after
    const statsAfter = await apiRequest('GET', '/stats');
    const hitsAfter = statsAfter.body.cache_hits;
    const missesAfter = statsAfter.body.cache_misses;

    const newHits = hitsAfter - hitsBefore;
    const newMisses = missesAfter - missesBefore;
    const hitRate = newHits / (newHits + newMisses);

    // Should have at least 70% hit rate
    expect(hitRate).toBeGreaterThanOrEqual(0.7);
  });

  /**
   * Test 15: Database migrations applied successfully
   */
  test('should have database schema with all required columns', async () => {
    // Create a TODO and verify all fields are present
    const todo = await apiRequest('POST', '/todos', {
      title: 'Schema test',
      description: 'Testing schema',
      due_date: new Date().toISOString(),
      priority: 'medium'
    });

    expect(todo.status).toBe(201);

    // Verify all required fields exist
    const requiredFields = [
      'id', 'title', 'description', 'status', 'priority',
      'due_date', 'created_at', 'updated_at'
    ];

    for (const field of requiredFields) {
      expect(todo.body).toHaveProperty(field);
    }

    // Verify default values
    expect(todo.body.status).toBe('pending');
    expect(todo.body.priority).toBe('medium');
    expect(todo.body.deleted_at).toBeUndefined(); // Soft delete column exists but null
  });
});

test.describe('TODO Backend API - Performance Tests', () => {

  /**
   * Performance Test: List TODOs < 100ms
   */
  test('should list TODOs in < 100ms (without cache)', async () => {
    const start = Date.now();
    const response = await apiRequest('GET', '/todos?limit=50');
    const duration = Date.now() - start;

    expect(response.status).toBe(200);
    expect(duration).toBeLessThan(100);
  });

  /**
   * Performance Test: Get TODO by ID < 50ms (with cache)
   */
  test('should get TODO by ID in < 50ms (with cache)', async () => {
    // Create and cache a TODO
    const todo = await apiRequest('POST', '/todos', { title: 'Perf test' });
    await apiRequest('GET', `/todos/${todo.body.id}`); // Cache it

    // Measure cached retrieval
    const start = Date.now();
    const response = await apiRequest('GET', `/todos/${todo.body.id}`);
    const duration = Date.now() - start;

    expect(response.status).toBe(200);
    expect(duration).toBeLessThan(50);
  });

  /**
   * Performance Test: Create TODO < 200ms
   */
  test('should create TODO in < 200ms', async () => {
    const start = Date.now();
    const response = await apiRequest('POST', '/todos', {
      title: 'Performance test TODO'
    });
    const duration = Date.now() - start;

    expect(response.status).toBe(201);
    expect(duration).toBeLessThan(200);
  });
});
