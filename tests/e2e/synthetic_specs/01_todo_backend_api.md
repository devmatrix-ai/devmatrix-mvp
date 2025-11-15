# TODO Backend API - Level 1 Synthetic Spec

## Overview
RESTful API backend for TODO list management using FastAPI, PostgreSQL, and Redis.

## Tech Stack
- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Deployment**: Docker Compose
- **Testing**: pytest, pytest-asyncio

## Features

### F1: TODO CRUD Operations
- Create TODO with title, description, due_date, priority
- Read single TODO by ID
- List all TODOs (paginated, max 50 per page)
- Update TODO (any field)
- Delete TODO (soft delete with deleted_at timestamp)
- Filter TODOs by: status, priority, due_date range
- Search TODOs by title/description (full-text search)

### F2: TODO Status Management
- Statuses: pending, in_progress, completed, archived
- Status transitions:
  - pending → in_progress → completed
  - Any status → archived
- Validate invalid transitions (e.g., completed → pending not allowed)

### F3: Priority Levels
- Priority: low, medium, high, urgent
- Default priority: medium
- Sort by priority (urgent first)

### F4: Caching Layer
- Cache frequently accessed TODOs (GET /todos/{id}) in Redis
- TTL: 5 minutes
- Cache invalidation on UPDATE/DELETE
- Cache statistics endpoint

### F5: API Documentation
- Auto-generated OpenAPI docs at /docs
- Redoc at /redoc
- Health check endpoint at /health

## Database Schema

### Table: todos
```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    CHECK (status IN ('pending', 'in_progress', 'completed', 'archived')),
    CHECK (priority IN ('low', 'medium', 'high', 'urgent'))
);

CREATE INDEX idx_todos_status ON todos(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_priority ON todos(priority) WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_due_date ON todos(due_date) WHERE deleted_at IS NULL;
```

## API Endpoints

### POST /todos
Create new TODO
- Request: `{title, description?, due_date?, priority?}`
- Response: `{id, title, description, status, priority, due_date, created_at, updated_at}`
- Status: 201 Created

### GET /todos/{id}
Get TODO by ID
- Response: TODO object (from cache if available)
- Status: 200 OK | 404 Not Found

### GET /todos
List TODOs (paginated)
- Query params: `?page=1&limit=50&status=pending&priority=high&search=meeting`
- Response: `{items: [...], total: 42, page: 1, limit: 50}`
- Status: 200 OK

### PUT /todos/{id}
Update TODO
- Request: `{title?, description?, status?, priority?, due_date?}`
- Validate status transitions
- Response: Updated TODO object
- Status: 200 OK | 404 Not Found | 400 Bad Request

### DELETE /todos/{id}
Soft delete TODO
- Sets deleted_at timestamp
- Invalidates cache
- Status: 204 No Content | 404 Not Found

### GET /health
Health check
- Response: `{status: "healthy", database: "connected", redis: "connected", timestamp: "..."}`
- Status: 200 OK

### GET /stats
Cache statistics
- Response: `{cache_hits: 123, cache_misses: 45, hit_rate: 0.73}`
- Status: 200 OK

## Validation Rules
1. Title: Required, max 200 chars
2. Description: Optional, max 5000 chars
3. Status: Must be valid enum value
4. Priority: Must be valid enum value
5. Due date: Must be future date (optional)
6. Status transitions: Validate allowed transitions

## Error Handling
- 400: Validation errors, invalid status transitions
- 404: TODO not found
- 422: Invalid request body
- 500: Internal server error

## Performance Requirements
- List TODOs: < 100ms (without cache)
- Get TODO by ID: < 50ms (with cache), < 100ms (without cache)
- Create/Update/Delete: < 200ms
- Cache hit rate target: > 70%

## Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/todos
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: todos
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Test Coverage Requirements
- Unit tests: ≥ 95% coverage
- Integration tests: All API endpoints
- E2E tests: 15 scenarios (provided separately)

## Success Criteria
1. All API endpoints working correctly
2. Database migrations applied successfully
3. Redis caching functional with >70% hit rate
4. Docker Compose up and running
5. All tests passing (≥95% coverage)
6. OpenAPI docs accessible
7. Health check returns healthy status
