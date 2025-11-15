# TODO Fullstack App - Level 2 Synthetic Spec

## Overview
Full-stack TODO application with Next.js 14 frontend, FastAPI backend, PostgreSQL database, and Redis caching. Complete CRUD operations, user authentication, and real-time updates.

## Tech Stack
- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python 3.10+), SQLAlchemy 2.0, Alembic
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Auth**: JWT (httponly cookies)
- **Deployment**: Docker Compose
- **Testing**: Vitest + Testing Library (frontend), pytest (backend), Playwright (E2E)

## Features

### F1: User Authentication
- User registration with email and password
- Login with JWT token (httponly cookie)
- Logout (clear cookie)
- Protected routes (redirect to login if unauthenticated)
- Password requirements: min 8 chars, 1 uppercase, 1 number
- Email validation
- Auth state management (Context API or Zustand)

### F2: TODO CRUD Operations
- Create TODO with title, description, due date, priority
- Read single TODO by ID
- List all user's TODOs (paginated, 20 per page)
- Update TODO (title, description, status, priority, due_date)
- Delete TODO (soft delete with confirmation modal)
- Filter by status, priority, due date range
- Search by title/description (debounced input)
- Sort by created_at, due_date, priority

### F3: TODO Status Management
- Statuses: pending, in_progress, completed, archived
- Status badge with color coding
- Drag-and-drop status change (Kanban board view)
- Status transitions validation:
  - pending → in_progress → completed
  - Any status → archived
  - Invalid transitions show error toast
- Status change history (audit log)

### F4: Priority Management
- Priority levels: low, medium, high, urgent
- Color-coded priority badges
- Default priority: medium
- Sort by priority (urgent first)
- Priority filter in sidebar

### F5: Real-time Updates (Optional Bonus)
- WebSocket connection for real-time TODO updates
- Live updates when other sessions modify TODOs
- Optimistic UI updates with rollback on error
- Connection status indicator

### F6: Responsive UI
- Mobile-first design
- Desktop: Sidebar + main content (list/kanban views)
- Mobile: Bottom navigation + hamburger menu
- Tablet: Adaptive layout
- Touch-friendly interactions (44px minimum tap targets)

### F7: Dark Mode
- Light/dark theme toggle
- Persisted in localStorage
- Smooth transition between themes
- System preference detection on first load

## Architecture

### Frontend Structure
```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── todos/page.tsx
│   │   └── todos/[id]/page.tsx
│   ├── layout.tsx
│   ├── page.tsx (redirect to /todos or /login)
│   └── globals.css
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   └── RegisterForm.tsx
│   ├── todos/
│   │   ├── TodoList.tsx
│   │   ├── TodoItem.tsx
│   │   ├── TodoForm.tsx
│   │   ├── TodoFilters.tsx
│   │   ├── KanbanBoard.tsx
│   │   └── TodoStats.tsx
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── MobileNav.tsx
│   └── ui/ (shadcn/ui components)
├── lib/
│   ├── api.ts (axios client with auth)
│   ├── auth.ts (auth helpers)
│   └── utils.ts
├── hooks/
│   ├── useTodos.ts
│   ├── useAuth.ts
│   └── useTheme.ts
├── stores/
│   └── authStore.ts (Zustand)
└── types/
    └── index.ts
```

### Backend Structure
```
src/
├── api/
│   ├── routers/
│   │   ├── auth.py
│   │   └── todos.py
│   ├── dependencies/
│   │   └── auth.py (JWT validation)
│   └── main.py
├── models/
│   ├── user.py
│   └── todo.py
├── schemas/
│   ├── user.py (Pydantic)
│   └── todo.py (Pydantic)
├── services/
│   ├── auth_service.py
│   ├── todo_service.py
│   └── cache_service.py
├── database/
│   ├── database.py (SQLAlchemy engine)
│   └── session.py (dependency)
├── alembic/
│   └── versions/
└── config.py (settings)
```

## Database Schema

### users table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

### todos table
```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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

CREATE INDEX idx_todos_user_id ON todos(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_status ON todos(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_priority ON todos(priority) WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_due_date ON todos(due_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_created_at ON todos(created_at) WHERE deleted_at IS NULL;
```

### todo_history table (audit log)
```sql
CREATE TABLE todo_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- 'created', 'updated', 'status_changed', 'deleted'
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_todo_history_todo_id ON todo_history(todo_id);
CREATE INDEX idx_todo_history_user_id ON todo_history(user_id);
```

## API Endpoints

### Authentication
**POST /api/v1/auth/register**
- Request: `{email, username, password}`
- Response: `{user: {id, email, username}, message}`
- Status: 201 Created

**POST /api/v1/auth/login**
- Request: `{email, password}`
- Response: Sets httponly cookie, returns `{user: {id, email, username}}`
- Status: 200 OK

**POST /api/v1/auth/logout**
- Response: Clears cookie, returns `{message: "Logged out"}`
- Status: 200 OK

**GET /api/v1/auth/me**
- Headers: Cookie with JWT
- Response: `{id, email, username}`
- Status: 200 OK | 401 Unauthorized

### TODOs (Protected Routes)
**POST /api/v1/todos**
- Headers: Cookie with JWT
- Request: `{title, description?, due_date?, priority?}`
- Response: TODO object
- Status: 201 Created

**GET /api/v1/todos**
- Headers: Cookie with JWT
- Query: `?page=1&limit=20&status=pending&priority=high&search=meeting&sort_by=due_date&order=asc`
- Response: `{items: [...], total: 42, page: 1, limit: 20, total_pages: 3}`
- Status: 200 OK

**GET /api/v1/todos/{id}**
- Headers: Cookie with JWT
- Response: TODO object (from cache if available)
- Status: 200 OK | 404 Not Found

**PUT /api/v1/todos/{id}**
- Headers: Cookie with JWT
- Request: `{title?, description?, status?, priority?, due_date?}`
- Response: Updated TODO object
- Status: 200 OK | 404 Not Found | 400 Bad Request

**DELETE /api/v1/todos/{id}**
- Headers: Cookie with JWT
- Status: 204 No Content | 404 Not Found

**GET /api/v1/todos/stats**
- Headers: Cookie with JWT
- Response: `{total, by_status: {pending: 5, in_progress: 3, ...}, by_priority: {...}}`
- Status: 200 OK

**GET /api/v1/todos/{id}/history**
- Headers: Cookie with JWT
- Response: `[{action, old_value, new_value, created_at}, ...]`
- Status: 200 OK

### Health & Info
**GET /api/v1/health**
- Response: `{status: "healthy", database: "connected", redis: "connected"}`
- Status: 200 OK

## Frontend Pages

### /login
- Email and password inputs
- Login button (disabled during loading)
- Link to /register
- Validation errors inline
- Remember me checkbox (extends JWT expiry)

### /register
- Email, username, password, confirm password inputs
- Password strength indicator
- Register button (disabled during loading)
- Link to /login
- Validation errors inline

### /todos
- Main dashboard with TODO list
- Sidebar with filters (status, priority, date range)
- Search bar (debounced)
- View toggle: List vs Kanban
- Create TODO button (opens modal or inline form)
- TODO stats cards (total, pending, in_progress, completed)
- Pagination controls

### /todos/[id]
- Single TODO detail view
- Edit mode toggle
- History/audit log
- Delete button with confirmation
- Back to list button

## Validation Rules

### Frontend
- Email: Valid email format
- Password: Min 8 chars, 1 uppercase, 1 number
- Username: 3-30 chars, alphanumeric + underscore
- TODO Title: 1-200 chars, required
- TODO Description: Max 5000 chars, optional
- Due date: Future date only (optional)

### Backend
- Same validation rules enforced
- Status transitions validated
- User can only access own TODOs
- JWT token expiry: 24 hours (access), 7 days (refresh if "remember me")

## Error Handling

### Frontend
- Toast notifications for errors and success
- Form validation errors inline
- Network errors: Retry button
- Optimistic UI with rollback on failure
- Loading states for all async operations

### Backend
- 400: Validation errors, invalid status transitions
- 401: Unauthenticated (redirect to login)
- 403: Forbidden (accessing other user's TODO)
- 404: TODO not found
- 422: Invalid request body
- 500: Internal server error (log to console)

## Caching Strategy

### Redis Caching
- Cache user's TODO list: Key `todos:user:{user_id}`, TTL 5 minutes
- Cache single TODO: Key `todo:{id}`, TTL 5 minutes
- Cache invalidation on UPDATE/DELETE/CREATE
- Cache stats: Key `stats:user:{user_id}`, TTL 1 minute

## Performance Requirements

### Frontend
- Initial page load: < 2s
- Route transitions: < 300ms
- Search debounce: 300ms
- Optimistic UI updates: Immediate
- Lighthouse Performance: ≥ 85

### Backend
- List TODOs: < 100ms (without cache), < 50ms (with cache)
- Get TODO by ID: < 50ms (with cache), < 100ms (without)
- Create/Update/Delete: < 200ms
- Auth endpoints: < 150ms
- Cache hit rate: > 70%

## Docker Compose

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/todos
      REDIS_URL: redis://redis:6379
      SECRET_KEY: your-secret-key-change-in-production
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 1440
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
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
```

## Test Coverage Requirements

### Frontend Tests
- Unit tests: ≥ 90% coverage
- Components: Render, interactions, state changes
- Hooks: useTodos, useAuth, useTheme
- API client: Mock axios responses

### Backend Tests
- Unit tests: ≥ 95% coverage
- Services: Business logic, caching
- Routers: All endpoints
- Dependencies: Auth validation
- Database: SQLAlchemy models

### E2E Tests (25 scenarios)
1. User registration flow
2. User login flow
3. User logout flow
4. Create TODO (authenticated)
5. Create TODO (unauthenticated - redirect to login)
6. View TODO list (authenticated)
7. View single TODO
8. Update TODO title
9. Update TODO status (valid transition)
10. Update TODO status (invalid transition - show error)
11. Delete TODO (with confirmation)
12. Search TODOs
13. Filter by status
14. Filter by priority
15. Filter by due date range
16. Sort by created_at
17. Sort by due_date
18. Sort by priority
19. Pagination (next/previous page)
20. Kanban board drag-and-drop
21. Dark mode toggle
22. Mobile responsive layout
23. TODO stats display
24. View TODO history
25. Cache hit rate > 70% (performance test)

## Success Criteria

1. ✅ User can register, login, logout
2. ✅ Protected routes redirect unauthenticated users
3. ✅ All CRUD operations working
4. ✅ Status transitions validated
5. ✅ Search, filter, sort functional
6. ✅ Pagination working (20 items per page)
7. ✅ Redis caching functional (>70% hit rate)
8. ✅ Docker Compose up and running (4 services)
9. ✅ All E2E tests passing (25 scenarios)
10. ✅ Frontend tests ≥90%, backend tests ≥95% coverage
11. ✅ Responsive design (mobile, tablet, desktop)
12. ✅ Dark mode functional
13. ✅ Performance requirements met
14. ✅ Error handling comprehensive
15. ✅ Database migrations applied successfully
