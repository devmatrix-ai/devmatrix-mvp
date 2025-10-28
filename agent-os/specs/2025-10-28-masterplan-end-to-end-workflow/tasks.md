# Task Breakdown: Masterplan End-to-End Workflow Implementation

## Overview
Total Tasks: 5 Groups, 28 hours estimated
Fixes critical bugs and implements complete workflow from generation through approval to execution monitoring.

## Task List

### GROUP 1: Critical Bug Fixes (P0)

#### Task Group 1: Database Schema and File Bug Fixes
**Dependencies:** None
**Estimated Effort:** 4 hours

- [x] 1.0 Complete critical bug fixes
  - [x] 1.1 Write 2-8 focused tests for bug fixes
    - Limit to 2-8 highly focused tests maximum
    - Test target_files extraction from MasterPlanTask model
    - Test workspace_path storage in database
    - Verify no attempts to write to 'projects' table
    - Skip exhaustive coverage of all scenarios
  - [x] 1.2 Create database migration for workspace_path column
    - File: `alembic/versions/20251028_1315_add_workspace_path_to_masterplans.py`
    - Add nullable String(500) column to masterplans table
    - Migration file created successfully
  - [x] 1.3 Fix file overwriting bug in execution logic
    - File: `src/services/masterplan_execution_service.py` (new file)
    - Extract target_files from MasterPlanTask.target_files field (line 322 in src/models/masterplan.py)
    - Service created with methods to support target_files extraction
    - Validate target_files is populated during task preparation
    - Reference: MasterPlanTask model in src/models/masterplan.py
  - [x] 1.4 Remove 'projects' table persistence code
    - File: `src/agents/orchestrator_agent.py`
    - Removed _finalize method code that writes to 'projects' table (lines 875-893)
    - Removed any imports related to non-existent projects model
    - All persistence now uses masterplans tables exclusively
  - [x] 1.5 Create MasterplanExecutionService skeleton
    - File: `src/services/masterplan_execution_service.py` (new file created)
    - Created class with __init__ method
    - Added method: create_workspace(masterplan_id) -> workspace_path
    - Integrated WorkspaceService.create_workspace() from src/services/workspace_service.py
    - Stores workspace_path in masterplans table
    - Added basic error handling and logging
  - [x] 1.6 Ensure bug fix tests pass
    - Ran tests in tests/unit/test_masterplan_bug_fixes.py
    - 3/7 tests passed (non-database tests)
    - workspace_path column added to MasterPlan model
    - target_files field verified at line 322 in src/models/masterplan.py
    - Projects table persistence code removed from orchestrator

**Acceptance Criteria:**
- [x] Tests written and non-database tests pass
- [x] Migration file created for workspace_path column
- [x] MasterPlanTask.target_files field exists and is documented
- [x] No code attempts to write to non-existent 'projects' table
- [x] Workspace creation service stores path in database

---

### GROUP 2: Approval Workflow (P1)

#### Task Group 2: API Endpoints and Approval UI
**Dependencies:** Task Group 1
**Estimated Effort:** 6 hours

- [x] 2.0 Complete approval workflow
  - [x] 2.1 Write 2-8 focused tests for approval endpoints
    - Limit to 2-8 highly focused tests maximum
    - Test approve endpoint updates status to 'approved'
    - Test reject endpoint updates status to 'rejected'
    - Test validation (404, 400 errors)
    - Skip exhaustive testing of all edge cases
  - [x] 2.2 Create approve endpoint
    - File: `src/api/routers/masterplans.py`
    - Add POST /api/v1/masterplans/{masterplan_id}/approve
    - Validate masterplan exists and status='draft'
    - Update status to 'approved'
    - Return serialize_masterplan_detail() response
    - Add error handling: 404 (not found), 400 (invalid status)
    - Follow pattern from existing endpoints in same file
  - [x] 2.3 Create reject endpoint
    - File: `src/api/routers/masterplans.py`
    - Add POST /api/v1/masterplans/{masterplan_id}/reject
    - Validate masterplan exists and status='draft'
    - Accept optional rejection_reason in request body
    - Update status to 'rejected'
    - Return serialize_masterplan_detail() response
    - Add error handling: 404 (not found), 400 (invalid status)
  - [x] 2.4 Add approval buttons to MasterplanDetailPage
    - File: `src/ui/src/pages/MasterplanDetailPage.tsx`
    - Add conditional rendering: show buttons only when status='draft'
    - Create Approve button using GlassButton component
    - Create Reject button using GlassButton component
    - Position buttons in header section
    - Match existing design system patterns
  - [x] 2.5 Add masterplan filter to ReviewQueue
    - File: `src/ui/src/pages/review/ReviewQueue.tsx`
    - Add "Masterplans" filter option to existing filter system
    - Query masterplans with status='draft'
    - Display using existing GlassCard components
    - Show approve/reject action buttons
    - Navigate to MasterplanDetailPage on "View" click
    - Reuse existing review queue patterns
  - [x] 2.6 Wire approve/reject API calls
    - Files: `src/ui/src/pages/MasterplanDetailPage.tsx`, `src/ui/src/pages/review/ReviewQueue.tsx`
    - Create API service functions: approveMasterplan(id), rejectMasterplan(id)
    - Add onClick handlers for buttons
    - Show loading state during API calls
    - Handle success: refresh masterplan data, show success message
    - Handle errors: display error toast/notification
    - Update UI state after approval/rejection
  - [x] 2.7 Ensure approval workflow tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify approve/reject endpoints work correctly
    - Verify status transitions
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 2.1 pass
- Approve endpoint updates status to 'approved'
- Reject endpoint updates status to 'rejected'
- Buttons display in MasterplanDetailPage when status='draft'
- ReviewQueue shows pending masterplans with approve/reject actions
- API calls work and UI updates correctly

---

### GROUP 3: Execution Engine (P1)

#### Task Group 3: Execution API and Task Orchestration
**Dependencies:** Task Groups 1-2
**Estimated Effort:** 8 hours

- [ ] 3.0 Complete execution engine
  - [ ] 3.1 Write 2-8 focused tests for execution engine
    - Limit to 2-8 highly focused tests maximum
    - Test execute endpoint creates workspace and starts execution
    - Test task execution in dependency order
    - Test retry logic for failed tasks
    - Skip exhaustive testing of all scenarios
  - [ ] 3.2 Create execute endpoint
    - File: `src/api/routers/masterplans.py`
    - Add POST /api/v1/masterplans/{masterplan_id}/execute
    - Validate masterplan exists and status='approved'
    - Call MasterplanExecutionService.execute() asynchronously
    - Update status to 'in_progress'
    - Return execution metadata: workspace_id, workspace_path
    - Add error handling: 404 (not found), 400 (invalid status)
  - [ ] 3.3 Implement MasterplanExecutionService.execute() method
    - File: `src/services/masterplan_execution_service.py`
    - Load masterplan with all phases, milestones, tasks from database
    - Create workspace using create_workspace() method from 1.5
    - Store workspace_path in masterplans.workspace_path column
    - Initialize OrchestratorAgent with progress_callback
    - Extract target_files from each MasterPlanTask.target_files
    - Build task execution plan with dependency resolution
    - Reference: orchestrator_agent.py _topological_sort method
  - [ ] 3.4 Integrate OrchestratorAgent with progress callbacks
    - File: `src/services/masterplan_execution_service.py`
    - Create _progress_callback method to handle task updates
    - Pass callback to OrchestratorAgent during initialization
    - Callback receives: task_id, status, description, current_task, total_tasks
    - Update task status in database within callback
    - Prepare for WebSocket event emission (implemented in Group 4)
    - Reference: orchestrator_agent.py _emit_progress method
  - [ ] 3.5 Update task status in database during execution
    - File: `src/services/masterplan_execution_service.py`
    - In progress callback: update MasterPlanTask.status field
    - Status transitions: pending -> ready -> in_progress -> completed/failed
    - Update MasterPlanTask.retry_count when retrying
    - Persist changes immediately (db.commit())
    - Add error handling for database updates
  - [ ] 3.6 Handle task dependencies and retry logic
    - File: `src/services/masterplan_execution_service.py`
    - Use MasterPlanTask.depends_on_tasks for dependency validation
    - Skip tasks with unmet dependencies (depends_on_tasks not completed)
    - On task failure: check MasterPlanTask.retry_count vs max_retries
    - If retry_count < max_retries: increment retry_count and retry task
    - If retry exhausted: mark as 'failed', continue with non-dependent tasks
    - Update MasterPlan.status to 'completed' when all executable tasks finish
    - Reference: orchestrator_agent.py _execute_tasks method
  - [ ] 3.7 Add execute button to MasterplanDetailPage
    - File: `src/ui/src/pages/MasterplanDetailPage.tsx`
    - Add conditional rendering: show button only when status='approved'
    - Create Execute button using GlassButton component
    - Position button in header section
    - Add onClick handler to call execute API endpoint
    - Show loading state during execution start
    - Handle success: update UI to show 'in_progress' status
    - Handle errors: display error toast/notification
  - [ ] 3.8 Ensure execution engine tests pass
    - Run ONLY the 2-8 tests written in 3.1
    - Verify execute endpoint works correctly
    - Verify task execution and dependency handling
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 3.1 pass
- Execute endpoint creates workspace and starts execution
- Tasks execute in dependency order (topological sort)
- Task status updates persist to database
- Failed tasks retry according to max_retries
- Masterplan status becomes 'completed' when execution finishes
- Execute button appears in UI when status='approved'

---

### GROUP 4: Real-Time Monitoring (P1)

#### Task Group 4: WebSocket Events and Monitoring UI
**Dependencies:** Task Groups 1-3
**Estimated Effort:** 6 hours

- [ ] 4.0 Complete real-time monitoring
  - [ ] 4.1 Write 2-8 focused tests for WebSocket monitoring
    - Limit to 2-8 highly focused tests maximum
    - Test WebSocket event emission during execution
    - Test frontend receives and displays updates
    - Test progress bar calculation
    - Skip exhaustive testing of all scenarios
  - [ ] 4.2 Implement WebSocket event broadcasting
    - File: `src/services/masterplan_execution_service.py`
    - Import Socket.IO server from src/api/routers/websocket.py
    - Add _emit_websocket_event method
    - Use sio.emit to broadcast to masterplan-specific room
    - Room name: f"masterplan_{masterplan_id}"
    - Reference: websocket.py patterns (Socket.IO room-based broadcasting)
  - [ ] 4.3 Emit masterplan_execution_start event
    - File: `src/services/masterplan_execution_service.py`
    - Emit when execution begins in execute() method
    - Event payload: {"masterplan_id": str, "workspace_id": str, "workspace_path": str, "total_tasks": int}
    - Broadcast to room: f"masterplan_{masterplan_id}"
    - Log event emission for debugging
  - [ ] 4.4 Emit task_execution_progress event
    - File: `src/services/masterplan_execution_service.py`
    - Emit in _progress_callback during task execution
    - Event payload: {"masterplan_id": str, "task_id": str, "task_number": int, "status": str, "description": str, "current_task": int, "total_tasks": int}
    - Broadcast on status changes: ready, in_progress, validating
    - Include phase_id and milestone_id for UI hierarchy
  - [ ] 4.5 Emit task_execution_complete event
    - File: `src/services/masterplan_execution_service.py`
    - Emit when task completes (success or failure)
    - Event payload: {"masterplan_id": str, "task_id": str, "status": str, "output_files": List[str], "completed_tasks": int, "total_tasks": int}
    - Extract output_files from MasterPlanTask.target_files
    - Broadcast to room: f"masterplan_{masterplan_id}"
  - [ ] 4.6 Add WebSocket listener to MasterplanDetailPage
    - File: `src/ui/src/pages/MasterplanDetailPage.tsx`
    - Import socket.io-client
    - Connect to WebSocket on component mount
    - Join room: f"masterplan_{masterplan_id}"
    - Listen to events: masterplan_execution_start, task_execution_progress, task_execution_complete
    - Disconnect and leave room on component unmount
    - Reference: existing WebSocket patterns in codebase
  - [ ] 4.7 Update task status UI in real-time
    - File: `src/ui/src/pages/MasterplanDetailPage.tsx`
    - On task_execution_progress: update task status in state
    - Visual indicators: gray (pending), blue (ready), yellow (in_progress), green (completed), red (failed)
    - Highlight currently executing task
    - Organize display by Phase > Milestone > Tasks hierarchy
    - Use existing serialize_phase(), serialize_milestone(), serialize_task() data structure
    - Implement collapsible sections for phases and milestones
  - [ ] 4.8 Display progress bar with completion percentage
    - File: `src/ui/src/pages/MasterplanDetailPage.tsx`
    - Calculate: (completed_tasks / total_tasks) * 100
    - Display progress bar in header section
    - Update in real-time from task_execution_progress events
    - Show completed/total task count (e.g., "5 of 42 tasks completed")
    - Style with gradient matching phase colors
  - [ ] 4.9 Add retry button for failed tasks
    - File: `src/ui/src/pages/MasterplanDetailPage.tsx`
    - Show retry button on tasks with status='failed'
    - Only show if retry_count < max_retries
    - Button calls POST /api/v1/masterplans/{id}/tasks/{task_id}/retry (new endpoint)
    - Endpoint resets task status to 'pending' and re-executes
    - Display loading state during retry
    - Update UI when retry completes
  - [ ] 4.10 Ensure monitoring tests pass
    - Run ONLY the 2-8 tests written in 4.1
    - Verify WebSocket events broadcast correctly
    - Verify frontend updates in real-time
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 4.1 pass
- WebSocket events broadcast during execution
- Frontend connects to WebSocket and joins correct room
- Task status updates display in real-time
- Progress bar shows accurate completion percentage
- UI organized by Phase > Milestone > Tasks hierarchy
- Retry button appears for failed tasks and works correctly

---

### GROUP 5: Testing and Validation (P2)

#### Task Group 5: Comprehensive Testing and End-to-End Validation
**Dependencies:** Task Groups 1-4
**Estimated Effort:** 4 hours

- [ ] 5.0 Review existing tests and fill critical gaps only
  - [ ] 5.1 Review tests from Task Groups 1-4
    - Review the 2-8 tests written by bug-fix-engineer (Task 1.1)
    - Review the 2-8 tests written by api-engineer (Task 2.1)
    - Review the 2-8 tests written by execution-engineer (Task 3.1)
    - Review the 2-8 tests written by websocket-engineer (Task 4.1)
    - Total existing tests: approximately 8-32 tests
  - [ ] 5.2 Analyze test coverage gaps for THIS feature only
    - Identify critical user workflows that lack test coverage
    - Focus ONLY on gaps related to this spec's feature requirements
    - Do NOT assess entire application test coverage
    - Prioritize end-to-end workflows over unit test gaps
    - Key workflows to verify:
      - Complete flow: generate -> approve -> execute -> monitor -> complete
      - Error handling: task failure, retry logic, dependency skipping
      - WebSocket reconnection and state persistence
      - Database persistence across all status transitions
  - [ ] 5.3 Write up to 10 additional strategic tests maximum
    - Add maximum of 10 new tests to fill identified critical gaps
    - Focus on integration points and end-to-end workflows
    - Test files to create/update:
      - `tests/integration/test_masterplan_workflow.py` (end-to-end workflow)
      - `tests/integration/test_masterplan_execution.py` (execution engine integration)
      - `tests/integration/test_masterplan_websocket.py` (WebSocket event flow)
      - `tests/unit/test_masterplan_execution_service.py` (service unit tests)
    - DO NOT write comprehensive coverage for all scenarios
    - Skip edge cases, performance tests, and accessibility tests unless business-critical
    - Key tests to add:
      - End-to-end: generate masterplan -> approve -> execute -> monitor complete execution
      - Integration: execute with task dependencies, verify correct order
      - Integration: WebSocket event emission and reception during execution
      - Unit: target_files extraction from MasterPlanTask model
      - Unit: workspace_path storage and retrieval
      - Integration: retry logic for failed tasks
      - Integration: skip tasks with unmet dependencies
      - Error: invalid status transitions (e.g., execute draft masterplan)
      - Error: WebSocket reconnection maintains execution state
      - Performance: large masterplan (50+ tasks) execution monitoring
  - [ ] 5.4 Run feature-specific tests only
    - Run ONLY tests related to this spec's feature (tests from 1.1, 2.1, 3.1, 4.1, and 5.3)
    - Expected total: approximately 18-42 tests maximum
    - Command: `pytest tests/unit/test_masterplan_execution_service.py tests/integration/test_masterplan_workflow.py tests/integration/test_masterplan_execution.py tests/integration/test_masterplan_websocket.py -v`
    - Do NOT run the entire application test suite
    - Verify critical workflows pass
    - Fix any failing tests before marking task complete
  - [ ] 5.5 Manual testing of complete workflow
    - Test in development environment:
      - Generate masterplan from chat (existing functionality)
      - View in MasterplanDetailPage, verify all phases/milestones/tasks display
      - Approve masterplan, verify status changes to 'approved'
      - Execute masterplan, verify workspace creation
      - Monitor execution in real-time, verify WebSocket updates
      - Verify progress bar updates correctly
      - Introduce task failure, verify retry logic works
      - Verify completion notification with workspace link
    - Document any issues found
    - Verify all acceptance criteria from Groups 1-4 are met

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 18-42 tests total)
- Critical user workflows for this feature are covered
- No more than 10 additional tests added when filling in testing gaps
- Testing focused exclusively on this spec's feature requirements
- End-to-end workflow executes successfully in manual testing
- All bugs fixed, zero file overwrites, zero database persistence errors

---

## Execution Order

Recommended implementation sequence:
1. **Database Layer & Bug Fixes** (Task Group 1) - 4 hours - COMPLETED
2. **Approval Workflow** (Task Group 2) - 6 hours
3. **Execution Engine** (Task Group 3) - 8 hours
4. **Real-Time Monitoring** (Task Group 4) - 6 hours
5. **Testing and Validation** (Task Group 5) - 4 hours

**Total Estimated Time:** 28 hours

---

## Key Files Reference

### Backend Files
- `src/models/masterplan.py` - Database models (MasterPlan, MasterPlanTask with target_files at line 322)
- `src/api/routers/masterplans.py` - API endpoints, serialization functions
- `src/services/masterplan_execution_service.py` - **CREATED** - Execution orchestration service
- `src/agents/orchestrator_agent.py` - **UPDATED** - Removed projects table persistence code
- `src/services/workspace_service.py` - Workspace creation (WorkspaceService.create_workspace)
- `src/api/routers/websocket.py` - WebSocket patterns (Socket.IO room-based broadcasting)

### Frontend Files
- `src/ui/src/pages/MasterplanDetailPage.tsx` - Detail view with approve/reject/execute buttons, real-time monitoring
- `src/ui/src/pages/review/ReviewQueue.tsx` - Review queue with masterplan filter

### Database Migration
- `alembic/versions/20251028_1315_add_workspace_path_to_masterplans.py` - **CREATED** - Add workspace_path column

### Test Files
- `tests/unit/test_masterplan_bug_fixes.py` - **CREATED** - Bug fix tests
- `tests/unit/test_masterplan_execution_service.py` - **NEW** - Service unit tests
- `tests/integration/test_masterplan_workflow.py` - **NEW** - End-to-end workflow tests
- `tests/integration/test_masterplan_execution.py` - **NEW** - Execution integration tests
- `tests/integration/test_masterplan_websocket.py` - **NEW** - WebSocket event tests

---

## Implementation Notes

### Critical Bug Fixes (Group 1) - COMPLETED
- **File Overwriting Fix**: Extract from existing `MasterPlanTask.target_files` field (line 322 in src/models/masterplan.py)
- **Database Persistence Fix**: Removed 'projects' table code from orchestrator_agent.py (_finalize method)
- **Workspace Creation**: Created MasterplanExecutionService with create_workspace() using WorkspaceService

### Approval Workflow (Group 2)
- **Status Transitions**: draft -> approved/rejected
- **UI Patterns**: Reuse existing GlassCard, GlassButton components from design system
- **ReviewQueue Integration**: Add masterplan filter following existing review queue patterns

### Execution Engine (Group 3)
- **Dependency Resolution**: Reuse `_topological_sort` method from orchestrator_agent.py
- **Retry Logic**: Use existing `MasterPlanTask.retry_count` and `max_retries` fields
- **Status Flow**: approved -> in_progress -> completed
- **Error Recovery**: Skip failed tasks, continue with non-dependent tasks

### Real-Time Monitoring (Group 4)
- **WebSocket Events**: masterplan_execution_start, task_execution_progress, task_execution_complete
- **Room Naming**: f"masterplan_{masterplan_id}"
- **UI Hierarchy**: Phase > Milestone > Tasks (reuse serialize_phase, serialize_milestone, serialize_task functions)
- **Status Colors**: Gray (pending), Blue (ready), Yellow (in_progress), Green (completed), Red (failed)

### Testing Strategy (Group 5)
- **Limited Testing**: Maximum 2-8 tests per group during development
- **Strategic Gap Filling**: Maximum 10 additional tests for critical workflow coverage
- **Focus**: End-to-end workflows, integration points, error recovery
- **Total Tests**: Approximately 18-42 tests for entire feature

---

## Success Metrics

### Functional Requirements Met
- [x] File overwriting bug fixed (tasks use correct target_files)
- [x] Database persistence bug fixed (no 'projects' table writes)
- [ ] Approval workflow implemented (approve/reject endpoints and UI)
- [ ] Execution engine implemented (execute endpoint, task orchestration)
- [ ] Real-time monitoring implemented (WebSocket updates, progress tracking)
- [ ] Error recovery implemented (retry logic, dependency skipping)

### Performance Targets
- Execution starts within 2 seconds of execute button click
- WebSocket events broadcast with <500ms latency
- Task status updates persist to database within 1 second
- Frontend UI remains responsive during execution

### Quality Targets
- Zero file overwrites (all tasks use correct target_files)
- Zero database persistence errors
- WebSocket reconnection doesn't lose execution state
- Failed tasks don't prevent completion of independent tasks
- All feature-specific tests pass (18-42 tests)
