# Specification: Masterplan End-to-End Workflow Implementation

## Executive Summary

This specification addresses critical bugs in the masterplan generation system and implements the complete end-to-end workflow from chat generation through approval to execution monitoring. The implementation fixes file overwriting issues, removes database persistence failures, and adds approve/reject/execute capabilities with real-time WebSocket updates.

## Goal

Transform the masterplan system from a generation-only feature into a complete workflow that allows users to generate, review, approve, execute, and monitor autonomous code generation projects with real-time feedback and error recovery.

## Problem Statement

### Current Critical Bugs

1. **File Overwriting Bug (P0)**: All tasks default to files=["main.py"], causing subsequent tasks to overwrite the same file instead of using their designated target_files
2. **Database Persistence Failure (P0)**: Orchestrator agent attempts to save to non-existent 'projects' table instead of using the existing masterplans tables
3. **Missing Approval Workflow (P1)**: No way for users to approve or reject generated masterplans before execution
4. **Missing Execution API (P1)**: No endpoint exists to trigger masterplan execution
5. **Missing Real-Time Monitoring (P1)**: Users cannot watch tasks execute in real-time or see progress updates

### Impact

- File overwrites lead to lost work and incorrect task execution
- Database errors prevent project metadata from being persisted
- Users cannot control which masterplans execute
- No visibility into execution progress or task status

## User Stories

- As a developer, I want to generate a masterplan from a chat conversation so that I can review it before execution
- As a developer, I want to approve or reject a generated masterplan so that I control what code gets created
- As a developer, I want to execute an approved masterplan so that autonomous agents build my project
- As a developer, I want to monitor task execution in real-time so that I can see progress and identify issues
- As a developer, I want failed tasks to automatically retry so that transient errors don't block my entire project
- As a developer, I want to access my generated workspace so that I can review and use the created code

## Core Requirements

### User-Facing Capabilities

**Phase 1: Generation**
- Chat generates masterplan and saves to database with status='draft'
- Masterplan contains complete Phase > Milestone > Task hierarchy
- Each task has target_files array extracted from schema

**Phase 2: Approval**
- View masterplan in MasterplanDetailPage with complete task breakdown
- See pending approvals in ReviewQueue following existing patterns
- Approve button updates status to 'approved'
- Reject button updates status to 'rejected'

**Phase 3: Execution**
- Execute button triggers entire masterplan execution
- Creates unique workspace folder for project files
- Stores workspace_path in database for easy access
- Updates status: 'approved' -> 'in_progress' -> 'completed'

**Phase 4: Monitoring**
- Real-time WebSocket updates during execution
- Visual hierarchy: Phase > Milestone > Tasks in collapsible sections
- Status indicators for each task (pending, in_progress, completed, failed)
- Retry buttons for failed tasks

**Phase 5: Completion**
- Completion notification with link to workspace_path
- Access generated code files
- Review execution metrics and costs

## Visual Design

No mockups provided. Implementation follows existing UI patterns:

- **MasterplanDetailPage.tsx**: Glass-morphism cards with gradient phase headers, collapsible milestones, nested task accordions
- **ReviewQueue.tsx**: Filter-based queue with status badges, GlassCard components, approval workflow patterns
- **Design System**: GlassCard, GlassButton components for consistent visual style
- **Phase Colors**: Blue (Setup), Purple (Core), Green (Polish)
- **Status Colors**: Gray (pending), Blue (ready), Yellow (in_progress), Green (completed), Red (failed)

### Responsive Design

- Desktop-first layout with max-width containers
- Collapsible sections for mobile viewing
- Progress bars and status indicators scale appropriately

## Reusable Components

### Existing Code to Leverage

**Database Models** (src/models/masterplan.py):
- MasterPlan model with status enum and all required fields
- MasterPlanPhase, MasterPlanMilestone, MasterPlanTask models
- MasterPlanTask.target_files (line 319) - CRITICAL for fixing file overwriting bug
- MasterPlanTask.retry_count, max_retries, depends_on_tasks fields
- All tables already migrated and production-ready

**API Serialization** (src/api/routers/masterplans.py):
- serialize_phase() - Converts phase to JSON with milestones
- serialize_milestone() - Converts milestone to JSON with tasks
- serialize_task() - Converts task to JSON with subtasks and metadata
- serialize_masterplan_detail() - Complete masterplan serialization

**Execution Logic** (src/agents/orchestrator_agent.py):
- Task decomposition and dependency resolution
- Topological sort for execution order (_topological_sort method)
- Progress callback system (_emit_progress method)
- Task execution with retry logic (_execute_tasks method)
- Dependency validation and circular dependency detection

**Workspace Management** (src/services/workspace_service.py):
- WorkspaceService.create_workspace() - Creates unique workspace folders
- Workspace model with metadata and file tree support
- File operations: read_file, write_file, delete_file
- Security validation: _resolve_path ensures paths stay within workspace

**WebSocket Patterns** (src/api/routers/websocket.py):
- Socket.IO server with robust timeout configuration
- Room-based event broadcasting (sio.emit to specific rooms)
- Event patterns: join_room, leave_room, emit to room
- Metrics collection for WebSocket events

**Frontend Components** (src/ui/src/pages/):
- MasterplanDetailPage.tsx - Phase/Milestone/Task hierarchy with expand/collapse
- ReviewQueue.tsx - Filter-based queue with status badges and actions
- GlassCard, GlassButton design system components

### New Components Required

**Backend Endpoints**:
- POST /api/v1/masterplans/{id}/approve - Approve masterplan (changes status to 'approved')
- POST /api/v1/masterplans/{id}/reject - Reject masterplan (changes status to 'rejected')
- POST /api/v1/masterplans/{id}/execute - Start execution (creates workspace, runs tasks)

**WebSocket Events**:
- masterplan_execution_start - Emitted when execution begins
- task_execution_progress - Emitted during task execution with status updates
- task_execution_complete - Emitted when all tasks finish

**Database Migration**:
- Add workspace_path column to masterplans table (nullable String field)

**Frontend Components**:
- Approval buttons in MasterplanDetailPage (conditional rendering based on status)
- Execution button in MasterplanDetailPage (shown after approval)
- Real-time monitoring UI with WebSocket integration
- Task retry buttons for failed tasks

**Service Layer**:
- MasterplanExecutionService - Orchestrates execution, manages workspace, broadcasts updates

Why these components are needed:
- Existing endpoints only support GET operations (list, detail)
- No execution service exists to coordinate orchestrator + workspace + WebSocket
- Database schema lacks workspace_path field
- Frontend lacks approval/execution UI controls

## Technical Approach

### Architecture Pattern

Follow existing FastAPI + SQLAlchemy + Socket.IO + React architecture:
1. API endpoints update database and trigger services
2. Services coordinate business logic and emit WebSocket events
3. WebSocket broadcasts updates to connected clients
4. React frontend listens to WebSocket and updates UI

### Database Changes

**Migration**: Add workspace_path column
```python
# alembic migration
op.add_column('masterplans', sa.Column('workspace_path', sa.String(500), nullable=True))
```

**Usage**: Store absolute path to workspace folder after execution starts

### API Endpoints

**POST /api/v1/masterplans/{masterplan_id}/approve**
- Validates masterplan exists and status='draft'
- Updates status to 'approved'
- Returns updated masterplan summary
- Errors: 404 (not found), 400 (invalid status)

**POST /api/v1/masterplans/{masterplan_id}/reject**
- Validates masterplan exists and status='draft'
- Updates status to 'rejected'
- Optionally accepts rejection reason in request body
- Returns updated masterplan summary

**POST /api/v1/masterplans/{masterplan_id}/execute**
- Validates masterplan exists and status='approved'
- Creates workspace using WorkspaceService.create_workspace()
- Stores workspace_path in database
- Updates status to 'in_progress'
- Triggers async execution via MasterplanExecutionService
- Returns execution metadata (workspace_id, workspace_path)

### Execution Service

**MasterplanExecutionService**:
- Loads masterplan with all phases, milestones, tasks from database
- Creates workspace for generated code
- Initializes OrchestratorAgent with progress_callback
- Progress callback broadcasts WebSocket events (masterplan_execution_start, task_execution_progress, task_execution_complete)
- Extracts target_files from MasterPlanTask.target_files (fixes file overwriting bug)
- Removes 'projects' table persistence from orchestrator (fixes database bug)
- Handles task execution with dependency resolution
- Updates task status in database during execution
- Updates masterplan status to 'completed' when done

### WebSocket Events

**masterplan_execution_start**:
```json
{
  "masterplan_id": "uuid",
  "workspace_id": "workspace-id",
  "workspace_path": "/absolute/path",
  "total_tasks": 42
}
```

**task_execution_progress**:
```json
{
  "masterplan_id": "uuid",
  "task_id": "uuid",
  "task_number": 5,
  "status": "in_progress",
  "description": "Create User model",
  "current_task": 5,
  "total_tasks": 42
}
```

**task_execution_complete**:
```json
{
  "masterplan_id": "uuid",
  "task_id": "uuid",
  "status": "completed",
  "output_files": ["models/user.py"],
  "completed_tasks": 5,
  "total_tasks": 42
}
```

### Frontend Changes

**MasterplanDetailPage.tsx**:
- Add conditional approval buttons (status='draft')
- Add conditional execute button (status='approved')
- Add WebSocket listener for execution events
- Update task status in real-time during execution
- Display retry button for failed tasks (status='failed')

**ReviewQueue.tsx**:
- Add masterplan filter to existing queue
- Display pending masterplans with approve/reject actions
- Navigate to MasterplanDetailPage on view

**Monitoring UI** (new component or extend MasterplanDetailPage):
- Connect to WebSocket on component mount
- Listen to task_execution_progress events
- Update task status indicators in real-time
- Show progress bar with completed_tasks/total_tasks
- Highlight currently executing task

### Error Handling and Retry Logic

**Task Execution**:
- Use existing MasterPlanTask.retry_count and max_retries fields
- On task failure: increment retry_count, retry if < max_retries
- If retry exhausted: mark task as 'failed', continue with non-dependent tasks
- Skip tasks with unmet dependencies (depends_on_tasks logic)

**Masterplan Completion**:
- Status becomes 'completed' when all executable tasks finish
- Some tasks may be 'failed' - this is acceptable
- Failed task count stored in MasterPlan.failed_tasks

**WebSocket Reconnection**:
- Frontend reconnects automatically on disconnect (Socket.IO built-in)
- Backend stores task status in database, so state survives reconnections

### File Overwriting Bug Fix

**Root Cause**: Tasks defaulting to files=["main.py"] instead of using target_files

**Solution**:
1. Extract target_files from MasterPlanTask.target_files field (exists at line 319)
2. Pass target_files to orchestrator agent execution context
3. Orchestrator uses target_files when creating/modifying files
4. Validation: Ensure target_files is populated during masterplan generation

### Database Persistence Bug Fix

**Root Cause**: Orchestrator tries to save to non-existent 'projects' table

**Solution**:
1. Remove projects table persistence code from orchestrator_agent.py (_finalize method, lines 874-900)
2. Use existing masterplans tables for all persistence
3. MasterplanExecutionService updates masterplan status directly in masterplans table

## Implementation Groups and Priorities

### GROUP 1: Critical Bug Fixes (P0)
**Estimated Effort**: 4 hours

**Tasks**:
1. Add workspace_path column migration to masterplans table
2. Fix file overwriting: Extract target_files from MasterPlanTask.target_files in execution service
3. Fix database persistence: Remove 'projects' table code from orchestrator_agent.py
4. Create MasterplanExecutionService skeleton with workspace creation

**Success Criteria**:
- Migration applies without errors
- Tasks use correct target_files during execution
- No attempts to write to 'projects' table
- Workspace created with unique ID

### GROUP 2: Approval Workflow (P1)
**Estimated Effort**: 6 hours

**Tasks**:
1. Create POST /api/v1/masterplans/{id}/approve endpoint
2. Create POST /api/v1/masterplans/{id}/reject endpoint
3. Add approval buttons to MasterplanDetailPage.tsx (status='draft')
4. Add masterplan filter to ReviewQueue.tsx
5. Wire approve/reject API calls from frontend

**Success Criteria**:
- Approve endpoint updates status to 'approved'
- Reject endpoint updates status to 'rejected'
- Buttons only show when status='draft'
- ReviewQueue displays pending masterplans

### GROUP 3: Execution Engine (P1)
**Estimated Effort**: 8 hours

**Tasks**:
1. Create POST /api/v1/masterplans/{id}/execute endpoint
2. Implement MasterplanExecutionService.execute() method
3. Integrate OrchestratorAgent with progress callbacks
4. Update task status in database during execution
5. Handle task dependencies and retry logic
6. Add execute button to MasterplanDetailPage.tsx (status='approved')

**Success Criteria**:
- Execute endpoint creates workspace and starts execution
- Tasks execute in dependency order
- Task status updates persist to database
- Failed tasks retry according to max_retries
- Masterplan status becomes 'completed' when done

### GROUP 4: Real-Time Monitoring (P1)
**Estimated Effort**: 6 hours

**Tasks**:
1. Implement WebSocket event broadcasting in MasterplanExecutionService
2. Emit masterplan_execution_start, task_execution_progress, task_execution_complete
3. Add WebSocket listener to MasterplanDetailPage.tsx
4. Update task status UI in real-time
5. Display progress bar with current/total tasks
6. Add retry button for failed tasks

**Success Criteria**:
- WebSocket events broadcast during execution
- Frontend receives and displays updates in real-time
- Progress bar reflects actual completion percentage
- Retry button calls execute endpoint for specific task

### GROUP 5: Testing and Validation (P2)
**Estimated Effort**: 4 hours

**Tasks**:
1. Unit tests for approve/reject/execute endpoints
2. Integration tests for execution workflow
3. WebSocket event tests
4. Frontend component tests for approval/execution UI
5. End-to-end workflow test (generate -> approve -> execute -> monitor)

**Success Criteria**:
- All API endpoints have test coverage
- WebSocket events validated
- Frontend interactions tested
- Complete workflow executes successfully

## Out of Scope

The following features are explicitly excluded from this implementation:

- **Manual task reordering interface**: Tasks execute in dependency order only
- **Editing generated plans before approval**: Plans are approved/rejected as-is
- **Per-task or per-phase execution controls**: Only full masterplan execution supported
- **Pause/resume execution functionality**: Execution runs to completion
- **Export/import masterplan functionality**: Plans stay in database only
- **Advanced retry configuration UI**: Uses default max_retries from schema
- **Task execution history/logs viewer**: Basic status only, no detailed logs UI
- **Workspace file browser integration**: Workspace accessed via file system only
- **Multi-user collaboration on masterplans**: Single user workflow only
- **Masterplan templates or cloning**: Each masterplan generated fresh
- **Cost tracking UI**: Cost fields exist but no visualization

## Success Criteria

### Functional

- Generate masterplan via chat, save to database with status='draft'
- View masterplan in MasterplanDetailPage with complete hierarchy
- Approve masterplan, status changes to 'approved'
- Execute masterplan, creates workspace and runs all tasks
- Monitor execution in real-time via WebSocket updates
- Access completed workspace via workspace_path
- Failed tasks retry up to max_retries and don't block entire masterplan

### Performance

- Masterplan generation completes within 60 seconds (existing behavior)
- Execution starts within 2 seconds of execute button click
- WebSocket events broadcast with <500ms latency
- Task status updates persist to database within 1 second
- Frontend UI remains responsive during execution

### Quality

- Zero file overwrites (all tasks use correct target_files)
- Zero database persistence errors
- WebSocket reconnection doesn't lose execution state
- Failed tasks don't prevent completion of independent tasks
- All existing masterplan tests continue passing

## Testing Strategy

### Unit Tests

- API endpoint validation (approve/reject/execute)
- MasterplanExecutionService methods
- WebSocket event emission
- Target files extraction logic
- Dependency resolution and retry logic

### Integration Tests

- End-to-end workflow: generate -> approve -> execute -> complete
- WebSocket event broadcasting and frontend reception
- Database persistence during execution
- Workspace creation and file operations
- Error recovery and retry scenarios

### Manual Testing

- Generate multiple masterplans with varying complexity
- Approve and reject masterplans
- Execute masterplans with task dependencies
- Monitor execution in real-time via UI
- Verify failed tasks retry correctly
- Confirm workspace files created successfully

### Performance Tests

- Generate large masterplan (50+ tasks)
- Execute with concurrent task monitoring
- Measure WebSocket event latency
- Verify database performance under load

## Technical Dependencies

- FastAPI 0.104+
- SQLAlchemy 2.0+
- Socket.IO (python-socketio)
- PostgreSQL (existing database)
- React 18.2+
- TypeScript 5+
- Socket.IO Client (socket.io-client)

## Migration Plan

1. **Database**: Run Alembic migration to add workspace_path column
2. **Backend**: Deploy new endpoints and execution service
3. **Frontend**: Deploy updated MasterplanDetailPage and ReviewQueue
4. **WebSocket**: Ensure Socket.IO server supports new events
5. **Validation**: Run end-to-end tests in staging environment
6. **Rollout**: Deploy to production with feature flag (optional)

## Rollback Plan

- Database migration is additive (workspace_path nullable), safe to rollback
- New endpoints are isolated, won't affect existing functionality
- Frontend changes are conditional on status fields, backward compatible
- WebSocket events are new, no existing listeners to break

## Security Considerations

- Execution endpoint requires authentication (existing middleware)
- Workspace paths validated to prevent directory traversal
- WebSocket events scoped to authenticated sessions
- Approval actions logged to audit trail (existing audit system)

## Monitoring and Observability

- Log all approval/rejection/execution actions (StructuredLogger)
- Track WebSocket event metrics (existing metrics_collector)
- Monitor task execution duration and failure rates
- Alert on high failure rates or long execution times
- Dashboard showing active executions and completion rates
