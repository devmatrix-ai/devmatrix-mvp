# Simple Task Management API

## Overview
A RESTful API for managing tasks with basic CRUD operations.

## Requirements

### Functional Requirements
1. **Create Task**: Users can create a new task with title and description
2. **Read Tasks**: Users can retrieve all tasks or a single task by ID
3. **Update Task**: Users can update task details and mark as completed
4. **Delete Task**: Users can delete a task by ID

### Data Model
**Task**:
- id: unique identifier (UUID)
- title: string (required, max 200 chars)
- description: string (optional, max 1000 chars)
- completed: boolean (default: false)
- created_at: timestamp
- updated_at: timestamp

### API Endpoints
- `POST /tasks` - Create new task
- `GET /tasks` - List all tasks
- `GET /tasks/{id}` - Get task by ID
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task

### Non-Functional Requirements
- RESTful design principles
- JSON request/response format
- Input validation
- Error handling with appropriate HTTP status codes
- In-memory storage (no database required for MVP)

### Success Criteria
- All CRUD operations work correctly
- Proper HTTP status codes (200, 201, 404, 400, etc.)
- Input validation prevents invalid data
- API follows REST conventions
