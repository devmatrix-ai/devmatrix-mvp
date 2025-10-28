# Masterplan End-to-End Workflow Implementation

## Overview
Fix critical bugs in the masterplan generation system and implement the complete end-to-end workflow from chat generation to execution monitoring.

## Key Problems to Solve
1. File Overwriting Bug (P0): All tasks default to files=["main.py"], causing overwriting
2. Database Persistence Failure (P0): Orchestrator saves to non-existent 'projects' table
3. Missing Approval Workflow (P1): No approve/reject functionality
4. Missing Execution API (P1): No endpoint to start execution
5. Missing Real-Time Monitoring (P1): No way to watch tasks execute

## Desired End-to-End Flow
- Phase 1: Chat generates masterplan → saves to DB with status='draft'
- Phase 2: User reviews in /masterplans and approves/rejects
- Phase 3: User starts execution → backend runs all tasks
- Phase 4: User monitors live execution in review queue with WebSocket updates
- Phase 5: Completion notification with link to generated workspace

## Implementation Groups
- GROUP 1: Critical Fixes (file naming, DB persistence, workspace mapping)
- GROUP 2: Approval Workflow (approve/reject endpoints + UI)
- GROUP 3: Execution Engine (execute endpoint, task executor service)
- GROUP 4: Real-Time Monitoring (WebSocket updates, monitoring UI)

## Tech Stack
- Backend: FastAPI, SQLAlchemy + PostgreSQL, Socket.IO WebSockets
- Frontend: React 18.2 + TypeScript, existing design system
- Database schema already exists in src/models/masterplan.py

## Success Criteria
User can: create masterplan in chat → view/approve in UI → start execution → monitor real-time → receive completion notification
