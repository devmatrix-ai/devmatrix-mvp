# Spec Requirements: Masterplan End-to-End Workflow Implementation

## Initial Description

Fix critical bugs in the masterplan generation system and implement the complete end-to-end workflow from chat generation to execution monitoring.

### Key Problems to Solve
1. File Overwriting Bug (P0): All tasks default to files=["main.py"], causing overwriting
2. Database Persistence Failure (P0): Orchestrator saves to non-existent 'projects' table
3. Missing Approval Workflow (P1): No approve/reject functionality
4. Missing Execution API (P1): No endpoint to start execution
5. Missing Real-Time Monitoring (P1): No way to watch tasks execute

### Desired End-to-End Flow
- Phase 1: Chat generates masterplan → saves to DB with status='draft'
- Phase 2: User reviews in /masterplans and approves/rejects
- Phase 3: User starts execution → backend runs all tasks
- Phase 4: User monitors live execution in review queue with WebSocket updates
- Phase 5: Completion notification with link to generated workspace

### Implementation Groups
- GROUP 1: Critical Fixes (file naming, DB persistence, workspace mapping)
- GROUP 2: Approval Workflow (approve/reject endpoints + UI)
- GROUP 3: Execution Engine (execute endpoint, task executor service)
- GROUP 4: Real-Time Monitoring (WebSocket updates, monitoring UI)

## Requirements Discussion

### First Round Questions

**Q1: File Overwriting Bug Fix**
For fixing the file overwriting issue, I see two approaches:
- Option A: Extract `target_files` from the existing MasterPlanTask model (I can see it's defined at line 319 in the schema)
- Option B: Add new file path extraction logic in the orchestrator

Which approach should we take?

**Answer:** Option A - Extract `target_files` from existing MasterPlanTask model (line 319). The field already exists, so use it.

**Q2: Database Persistence Strategy**
Currently the orchestrator tries to save to a non-existent 'projects' table. Should we:
- Option A: Remove the projects table persistence entirely and use the existing masterplans tables
- Option B: Create a new projects table and migration

Which direction aligns better with your data model?

**Answer:** Option A - Remove `projects` table persistence entirely. Use existing `masterplans` tables which are complete and migrated.

**Q3: Approval Workflow UI Location**
Where should the approve/reject buttons appear?
- Option A: In the MasterplanDetailPage when viewing a specific plan
- Option B: In a dedicated review queue (similar to existing review patterns)
- Option C: Both locations

**Answer:** Option C - Both locations:
- MasterplanDetailPage: Show buttons when viewing specific plan
- ReviewQueue: Show pending approvals (reuses existing review pattern)

**Q4: Execution Trigger**
When and how should execution start?
- Trigger from MasterplanDetailPage after approval or separate execution page?
- Execute entire masterplan at once or allow per-phase/per-milestone execution?

**Answer:**
- Trigger from MasterplanDetailPage after approval (reuses existing detail page)
- Execute entire masterplan at once (simpler, follows existing orchestrator pattern)

**Q5: Real-Time Monitoring UI Layout**
How should we display task execution progress?
- Option A: Flat list of all tasks with status indicators
- Option B: Organize by Phase > Milestone > Tasks in collapsible sections
- Should we reuse the existing serialize_phase(), serialize_milestone(), serialize_task() functions?

**Answer:**
- Option B - Organize by Phase > Milestone > Tasks in collapsible sections (matches data model)
- Reuse existing serialize_phase(), serialize_milestone(), serialize_task() functions
- Include retry buttons for failed tasks (reuses existing retry_count field)

**Q6: WebSocket Event Names**
Should we follow similar patterns to existing WebSocket events in your codebase?
Example: `masterplan_execution_start`, `task_execution_progress`, `task_execution_complete`

**Answer:** Yes - Use similar patterns:
- masterplan_execution_start
- task_execution_progress
- task_execution_complete

**Q7: Workspace Creation & Storage**
Should we:
- Create a unique workspace folder for each masterplan execution?
- Store the workspace path in the masterplans table for easy access?

**Answer:** Yes to both:
- Create unique workspace folder (reuses existing WorkspaceManager)
- Add workspace_path column to masterplans table (small migration)

**Q8: Error Recovery Strategy**
When a task fails during execution:
- Option A: Stop entire masterplan execution
- Option B: Skip failed task and continue with non-dependent tasks
- Should we use the existing retry_count and max_retries fields?

**Answer:** Option B - Skip failed task and continue with non-dependent tasks:
- Reuses existing depends_on_tasks logic
- Reuses existing retry_count and max_retries fields
- Masterplan stays "in_progress" until all completable tasks finish, then "completed"

**Q9: Scope Boundaries**
Is there anything explicitly OUT of scope for this implementation? For example:
- Manual task reordering?
- Editing generated plans before approval?
- Per-task execution controls?
- Export/import functionality?

**Answer:** [Implied from answers - focus on core workflow, advanced features are out of scope]

### Existing Code to Reference

**Similar Features Identified:**
- **Models**: `src/models/masterplan.py` - Complete schema with phases, milestones, tasks, and all required fields
- **API Routers**: `src/api/routers/masterplans.py` - Serialization functions (serialize_phase(), serialize_milestone(), serialize_task())
- **WebSocket Patterns**: `src/api/routers/websocket.py` - WebSocket event handling patterns to follow
- **Execution Logic**: `src/agents/orchestrator_agent.py` - Task execution logic and orchestration patterns
- **Workspace Management**: `src/services/workspace_manager.py` - Workspace creation and management
- **UI Pages**:
  - `src/ui/src/pages/MasterplanDetailPage.tsx` - Detail view structure and layout
  - `src/ui/src/pages/review/ReviewQueue.tsx` - Review patterns and approval workflows
- **Design System**: Existing GlassCard, GlassButton components for consistent UI

**Components to Potentially Reuse:**
- MasterPlanTask model fields: target_files (line 319), retry_count, max_retries, depends_on_tasks
- Database tables: masterplans, masterplan_phases, masterplan_milestones, masterplan_tasks (all migrated)
- Serialization functions for converting DB models to JSON
- WebSocket connection and event emission patterns
- WorkspaceManager for folder creation
- Design system components for consistent glass-morphism UI

**Backend Logic to Reference:**
- Orchestrator task execution flow
- Dependency resolution using depends_on_tasks
- Retry logic using retry_count and max_retries
- WebSocket event broadcasting patterns

## Visual Assets

### Files Provided:
No visual files found.

### Visual Insights:
No visual assets provided. Implementation will follow existing UI patterns from:
- MasterplanDetailPage.tsx design patterns
- ReviewQueue.tsx approval workflow patterns
- Existing GlassCard/GlassButton design system

## Requirements Summary

### Functional Requirements

**GROUP 1: Critical Bug Fixes**
- Fix file overwriting bug by extracting target_files from existing MasterPlanTask.target_files field (line 319)
- Remove 'projects' table persistence; use existing masterplans tables exclusively
- Create unique workspace folder per masterplan using existing WorkspaceManager
- Add workspace_path column to masterplans table to store execution workspace location

**GROUP 2: Approval Workflow**
- Add approve/reject endpoints to masterplans router
- Display approve/reject buttons in MasterplanDetailPage when viewing specific plan
- Display pending approvals in ReviewQueue (reusing existing review pattern)
- Update masterplan status: 'draft' → 'approved' or 'rejected'

**GROUP 3: Execution Engine**
- Add execute endpoint to trigger masterplan execution from MasterplanDetailPage
- Execute entire masterplan at once (all phases/milestones/tasks)
- Update status: 'approved' → 'in_progress' → 'completed'
- Reuse orchestrator_agent.py execution patterns
- Handle task dependencies using existing depends_on_tasks logic

**GROUP 4: Real-Time Monitoring**
- Implement WebSocket events: masterplan_execution_start, task_execution_progress, task_execution_complete
- Display execution progress organized by Phase > Milestone > Tasks in collapsible sections
- Reuse serialize_phase(), serialize_milestone(), serialize_task() functions for data formatting
- Show retry buttons for failed tasks
- Send completion notification with link to workspace_path

**Error Recovery Strategy**
- When task fails: skip failed task and continue with non-dependent tasks
- Use existing retry_count and max_retries fields for automatic retries
- Masterplan status stays "in_progress" until all completable tasks finish
- Final status: "completed" (not "failed" even if some tasks failed)

### Reusability Opportunities

**Existing Database Schema:**
- masterplans table (id, name, description, status, created_at, updated_at)
- masterplan_phases table (id, masterplan_id, name, order_index, description)
- masterplan_milestones table (id, phase_id, name, order_index, description)
- masterplan_tasks table (id, milestone_id, name, description, target_files, retry_count, max_retries, depends_on_tasks, status, order_index)

**Existing Fields to Reuse:**
- MasterPlanTask.target_files - Already exists at line 319, solves file overwriting bug
- MasterPlanTask.retry_count - For tracking retries
- MasterPlanTask.max_retries - For retry limits
- MasterPlanTask.depends_on_tasks - For dependency resolution
- MasterPlanTask.status - For tracking execution state

**Existing Functions to Reuse:**
- serialize_phase() - Convert phase to JSON
- serialize_milestone() - Convert milestone to JSON
- serialize_task() - Convert task to JSON
- WorkspaceManager.create_workspace() - Create unique workspace folders

**UI Patterns to Follow:**
- MasterplanDetailPage.tsx - Detail view layout and structure
- ReviewQueue.tsx - Approval workflow patterns
- GlassCard - Consistent card styling
- GlassButton - Consistent button styling

**Backend Patterns to Follow:**
- orchestrator_agent.py - Task execution and orchestration logic
- websocket.py - WebSocket event broadcasting patterns
- Dependency resolution using depends_on_tasks field

### Scope Boundaries

**In Scope:**
- Fix file overwriting bug using existing target_files field
- Remove 'projects' table persistence, use masterplans tables
- Workspace creation and storage (workspace_path column)
- Approve/reject workflow in both MasterplanDetailPage and ReviewQueue
- Execute entire masterplan from MasterplanDetailPage after approval
- Real-time monitoring with WebSocket updates
- Error recovery: skip failed tasks, continue with non-dependent tasks
- Retry failed tasks using existing retry_count/max_retries
- Completion notification with workspace link
- UI organized by Phase > Milestone > Tasks structure

**Out of Scope:**
- Manual task reordering interface
- Editing generated plans before approval
- Per-task or per-phase execution controls (only full masterplan execution)
- Pause/resume execution functionality
- Export/import masterplan functionality
- Advanced retry configuration UI
- Task execution history/logs viewer
- Workspace file browser integration

### Technical Considerations

**Database:**
- Use existing migrated tables: masterplans, masterplan_phases, masterplan_milestones, masterplan_tasks
- Add workspace_path column to masterplans table (requires small migration)
- No new 'projects' table needed

**Backend:**
- FastAPI routers: Add approve, reject, execute endpoints to masterplans.py
- WebSocket events: masterplan_execution_start, task_execution_progress, task_execution_complete
- Reuse orchestrator_agent.py for task execution logic
- Reuse WorkspaceManager for workspace creation
- Extract target_files from MasterPlanTask.target_files (line 319) to fix overwriting bug

**Frontend:**
- React 18.2 + TypeScript
- Update MasterplanDetailPage.tsx: Add approve/reject/execute buttons
- Update ReviewQueue.tsx: Show pending masterplan approvals
- Add real-time monitoring view with Phase > Milestone > Tasks hierarchy
- Reuse GlassCard, GlassButton design system components
- WebSocket client for real-time updates

**Integration Points:**
- orchestrator_agent.py - Must read from masterplans tables, not 'projects' table
- WorkspaceManager - Create unique workspace per execution
- WebSocket connection - Broadcast execution progress
- Existing serialization functions - Format data consistently

**Technology Stack:**
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Real-time: Socket.IO WebSockets
- Frontend: React 18.2, TypeScript
- Existing design system: GlassCard, GlassButton components
