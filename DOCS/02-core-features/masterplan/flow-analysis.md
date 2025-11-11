# MasterPlan Flow Analysis - Complete E2E Mapping
**Fecha:** 2025-11-04
**Análisis:** Flujo completo desde Chat hasta Review
**Estado:** Investigación exhaustiva completada

---

## 🎯 Executive Summary

### Hallazgos Críticos
1. **Flujo COMPLETO implementado**: Chat → Discovery → MasterPlan → Persistence → Review
2. **WebSocket real-time**: Progress updates funcionando con Socket.IO
3. **Review system PRODUCTION-READY**: 95% complete con UI y API completa
4. **Gap principal**: Execution V2 no conecta con MasterPlan generation
5. **Problema crítico**: No hay bridge entre MasterPlan approval y execution V2

### Estado General
- ✅ **Generation Flow**: 100% funcional
- ✅ **WebSocket Updates**: 100% implementado
- ✅ **Review System**: 95% completo
- ⚠️ **Execution Integration**: 40% - falta conexión con MGE V2
- ❌ **E2E Automation**: Missing orchestration layer

---

## 📊 Flujo Arquitectónico Completo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + TS)                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. ChatWindow.tsx                                                        │
│     ├─ Socket.IO connection con JWT auth                                 │
│     ├─ join_chat(token) → session_id                                     │
│     ├─ send_message("crear app con FastAPI...") → backend                │
│     └─ Listeners:                                                         │
│         ├─ discovery_* events                                            │
│         ├─ masterplan_* events                                           │
│         └─ message events                                                │
│                                                                            │
│  2. MasterPlanProgressModal.tsx                                           │
│     ├─ Progress tracking real-time                                       │
│     ├─ Phase indicators (Discovery → MasterPlan)                         │
│     ├─ Token count tracking                                              │
│     └─ Final summary display                                             │
│                                                                            │
│  3. ReviewQueue.tsx (páginas de review)                                  │
│     ├─ GET /api/v2/review/queue                                          │
│     ├─ Approve/Reject/Edit/Regenerate                                    │
│     └─ AI suggestions display                                            │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          WEBSOCKET LAYER (Socket.IO)                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  src/api/routers/websocket.py                                             │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Socket.IO Server (AsyncServer)                                      │ │
│  │  ├─ ping_timeout: 120s                                              │ │
│  │  ├─ ping_interval: 60s                                              │ │
│  │  └─ compression enabled                                             │ │
│  │                                                                      │ │
│  │ Event Handlers:                                                     │ │
│  │  ├─ connect/disconnect                                              │ │
│  │  ├─ join_chat(token) → JWT validation → create conversation        │ │
│  │  ├─ send_message → ChatService.send_message()                      │ │
│  │  ├─ join_masterplan(masterplan_id) → room subscription             │ │
│  │  └─ leave_masterplan                                                │ │
│  │                                                                      │ │
│  │ WebSocketManager (global instance):                                 │ │
│  │  ├─ emit_discovery_* events                                         │ │
│  │  ├─ emit_masterplan_* events                                        │ │
│  │  └─ emit_task_execution_* events                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         CHAT SERVICE LAYER                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  src/services/chat_service.py (977 LOC)                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ ChatService                                                         │ │
│  │  ├─ create_conversation(user_id, session_id)                       │ │
│  │  │   └─ PostgreSQL persistence (conversations table)               │ │
│  │  │                                                                  │ │
│  │  ├─ send_message(conversation_id, content) → AsyncIterator         │ │
│  │  │   ├─ ChatCommand.is_command(content)?                           │ │
│  │  │   │   ├─ YES: _handle_command()                                 │ │
│  │  │   │   │     ├─ /help → show commands                            │ │
│  │  │   │   │     ├─ /masterplan <desc> →                             │ │
│  │  │   │   │     │     _execute_masterplan_generation()              │ │
│  │  │   │   │     └─ /orchestrate <desc> →                            │ │
│  │  │   │   │           _execute_orchestration()                      │ │
│  │  │   │   │                                                          │ │
│  │  │   │   └─ NO: _handle_regular_message()                          │ │
│  │  │   │         ├─ is_direct_implementation?                        │ │
│  │  │   │         │   ├─ YES → _execute_orchestration()               │ │
│  │  │   │         │   └─ NO → _handle_conversational()                │ │
│  │  │   │         │           (LLM chat con Sonnet)                   │ │
│  │  │   │                                                              │ │
│  │  │   └─ Save messages to DB (messages table)                       │ │
│  │  │                                                                  │ │
│  │  └─ _execute_masterplan_generation() → AsyncIterator               │ │
│  │      ├─ Step 1: Discovery                                          │ │
│  │      │   ├─ DiscoveryAgent.conduct_discovery()                     │ │
│  │      │   │   └─ Emits: discovery_* WebSocket events                │ │
│  │      │   └─ Returns: discovery_id                                  │ │
│  │      │                                                              │ │
│  │      └─ Step 2: MasterPlan Generation                              │ │
│  │          ├─ MasterPlanGenerator.generate_masterplan()              │ │
│  │          │   └─ Emits: masterplan_* WebSocket events               │ │
│  │          └─ Returns: masterplan_id                                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    MASTERPLAN GENERATION SERVICE                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  src/services/masterplan_generator.py (1,019 LOC)                        │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ MasterPlanGenerator                                                 │ │
│  │                                                                      │ │
│  │ __init__(llm_client, metrics, use_rag=True, websocket_manager)     │ │
│  │  ├─ Initializes RAG retriever (ChromaDB + embeddings)              │ │
│  │  └─ Sets up WebSocket manager for real-time updates                │ │
│  │                                                                      │ │
│  │ async generate_masterplan(discovery_id, session_id, user_id):      │ │
│  │  │                                                                  │ │
│  │  ├─ 1. Load Discovery from DB                                      │ │
│  │  │   └─ Query: DiscoveryDocument.discovery_id == discovery_id      │ │
│  │  │                                                                  │ │
│  │  ├─ 2. Emit WebSocket: masterplan_generation_start                 │ │
│  │  │   └─ ws_manager.emit_masterplan_generation_start()              │ │
│  │  │       ├─ session_id (Socket.IO room)                            │ │
│  │  │       ├─ discovery_id                                           │ │
│  │  │       ├─ estimated_tokens: 17,000                               │ │
│  │  │       └─ estimated_duration: 90s                                │ │
│  │  │                                                                  │ │
│  │  ├─ 3. Retrieve RAG Examples                                       │ │
│  │  │   ├─ Query: domain + bounded_contexts                           │ │
│  │  │   ├─ Top 5 similar masterplans                                  │ │
│  │  │   └─ min_similarity: 0.7                                        │ │
│  │  │                                                                  │ │
│  │  ├─ 4. Generate with LLM (Sonnet 4.5)                              │ │
│  │  │   ├─ System: MASTERPLAN_SYSTEM_PROMPT (215 lines)               │ │
│  │  │   │   ├─ Structure: 3 Phases (Setup/Core/Polish)                │ │
│  │  │   │   ├─ 120 ULTRA-ATOMIC tasks                                 │ │
│  │  │   │   ├─ Task structure: subtasks (3-7 micro-steps)             │ │
│  │  │   │   └─ Complexity: low/medium/high/critical                   │ │
│  │  │   │                                                              │ │
│  │  │   ├─ Variable prompt: Discovery context + RAG examples          │ │
│  │  │   │                                                              │ │
│  │  │   ├─ LLM call: generate_with_caching()                          │ │
│  │  │   │   ├─ max_tokens: 64,000                                     │ │
│  │  │   │   ├─ temperature: 0.7                                       │ │
│  │  │   │   ├─ streaming: automatic                                   │ │
│  │  │   │   └─ Emits: masterplan_tokens_progress events               │ │
│  │  │   │       (every 5 seconds during generation)                   │ │
│  │  │   │                                                              │ │
│  │  │   └─ Output: ~17K tokens JSON                                   │ │
│  │  │       ├─ project_name                                           │ │
│  │  │       ├─ tech_stack                                             │ │
│  │  │       ├─ phases[] (3 phases)                                    │ │
│  │  │       │   └─ milestones[]                                       │ │
│  │  │       │       └─ tasks[] (120 total)                            │ │
│  │  │       │           └─ subtasks[] (3-7 per task)                  │ │
│  │  │       ├─ total_tasks: 120                                       │ │
│  │  │       ├─ estimated_cost_usd                                     │ │
│  │  │       └─ estimated_duration_minutes                             │ │
│  │  │                                                                  │ │
│  │  ├─ 5. Parse & Validate                                            │ │
│  │  │   ├─ Extract JSON from markdown                                 │ │
│  │  │   ├─ Validate structure (3 phases, 100-150 tasks)               │ │
│  │  │   ├─ Emit: masterplan_parsing_complete                          │ │
│  │  │   └─ Emit: masterplan_validation_start                          │ │
│  │  │                                                                  │ │
│  │  ├─ 6. Save to Database                                            │ │
│  │  │   ├─ Emit: masterplan_saving_start                              │ │
│  │  │   │                                                              │ │
│  │  │   ├─ Create MasterPlan record                                   │ │
│  │  │   │   ├─ status: DRAFT                                          │ │
│  │  │   │   ├─ discovery_id, session_id, user_id                     │ │
│  │  │   │   ├─ project_name, description                              │ │
│  │  │   │   ├─ tech_stack (JSON)                                      │ │
│  │  │   │   ├─ total_tasks, total_phases, total_milestones            │ │
│  │  │   │   ├─ estimated_cost_usd (calculated)                        │ │
│  │  │   │   ├─ estimated_duration_minutes                             │ │
│  │  │   │   └─ llm_model, generation_cost_usd                         │ │
│  │  │   │                                                              │ │
│  │  │   ├─ Create Phases (3)                                          │ │
│  │  │   │   ├─ phase_type: SETUP/CORE/POLISH                         │ │
│  │  │   │   ├─ phase_number: 1/2/3                                    │ │
│  │  │   │   └─ name, description                                      │ │
│  │  │   │                                                              │ │
│  │  │   ├─ Create Milestones (per phase)                              │ │
│  │  │   │   ├─ milestone_number                                       │ │
│  │  │   │   ├─ depends_on_milestones (JSON)                           │ │
│  │  │   │   └─ total_tasks count                                      │ │
│  │  │   │                                                              │ │
│  │  │   ├─ Create Tasks (120 total)                                   │ │
│  │  │   │   ├─ task_number (global 1-120)                             │ │
│  │  │   │   ├─ name, description                                      │ │
│  │  │   │   ├─ complexity: LOW/MEDIUM/HIGH/CRITICAL                   │ │
│  │  │   │   ├─ depends_on_tasks (JSON, task UUIDs)                    │ │
│  │  │   │   ├─ target_files (JSON array)                              │ │
│  │  │   │   └─ status: PENDING                                        │ │
│  │  │   │                                                              │ │
│  │  │   └─ Create Subtasks (per task)                                 │ │
│  │  │       ├─ subtask_number (1-7)                                   │ │
│  │  │       ├─ name, description                                      │ │
│  │  │       ├─ status: PENDING                                        │ │
│  │  │       └─ completed: false                                       │ │
│  │  │                                                                  │ │
│  │  └─ 7. Emit WebSocket: masterplan_generation_complete              │ │
│  │      ├─ masterplan_id                                              │ │
│  │      ├─ project_name                                               │ │
│  │      ├─ total_phases, total_milestones, total_tasks                │ │
│  │      ├─ generation_cost_usd                                        │ │
│  │      ├─ duration_seconds                                           │ │
│  │      └─ estimated_total_cost_usd, estimated_duration_minutes       │ │
│  │                                                                      │ │
│  │  Returns: masterplan_id (UUID)                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATABASE PERSISTENCE                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  PostgreSQL Tables (src/models/masterplan.py - 470 LOC)                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                                                                      │ │
│  │ 1. discovery_documents                                              │ │
│  │    ├─ discovery_id (UUID, PK)                                       │ │
│  │    ├─ session_id, user_id                                           │ │
│  │    ├─ domain, bounded_contexts, aggregates (JSON)                   │ │
│  │    ├─ value_objects, domain_events, services (JSON)                 │ │
│  │    ├─ llm_model, llm_cost_usd                                       │ │
│  │    └─ created_at, updated_at                                        │ │
│  │                                                                      │ │
│  │ 2. masterplans                                                       │ │
│  │    ├─ masterplan_id (UUID, PK)                                      │ │
│  │    ├─ discovery_id (FK → discovery_documents)                       │ │
│  │    ├─ session_id, user_id                                           │ │
│  │    ├─ project_name, description                                     │ │
│  │    ├─ status (DRAFT/APPROVED/IN_PROGRESS/COMPLETED/FAILED)          │ │
│  │    ├─ tech_stack (JSON)                                             │ │
│  │    ├─ total_phases, total_milestones, total_tasks                   │ │
│  │    ├─ completed_tasks, failed_tasks, progress_percent               │ │
│  │    ├─ estimated_cost_usd, actual_cost_usd                           │ │
│  │    ├─ workspace_path (added for execution)                          │ │
│  │    ├─ llm_model, generation_cost_usd                                │ │
│  │    └─ created_at, started_at, completed_at                          │ │
│  │                                                                      │ │
│  │ 3. masterplan_phases                                                 │ │
│  │    ├─ phase_id (UUID, PK)                                           │ │
│  │    ├─ masterplan_id (FK)                                            │ │
│  │    ├─ phase_type (SETUP/CORE/POLISH)                                │ │
│  │    ├─ phase_number (1/2/3)                                          │ │
│  │    ├─ total_milestones, total_tasks, completed_tasks                │ │
│  │    └─ started_at, completed_at                                      │ │
│  │                                                                      │ │
│  │ 4. masterplan_milestones                                             │ │
│  │    ├─ milestone_id (UUID, PK)                                       │ │
│  │    ├─ phase_id (FK)                                                 │ │
│  │    ├─ milestone_number                                              │ │
│  │    ├─ depends_on_milestones (JSON)                                  │ │
│  │    ├─ total_tasks, completed_tasks, progress_percent                │ │
│  │    └─ started_at, completed_at                                      │ │
│  │                                                                      │ │
│  │ 5. masterplan_tasks                                                  │ │
│  │    ├─ task_id (UUID, PK)                                            │ │
│  │    ├─ masterplan_id, phase_id, milestone_id (FKs)                   │ │
│  │    ├─ task_number (global 1-120)                                    │ │
│  │    ├─ name, description                                             │ │
│  │    ├─ complexity (LOW/MEDIUM/HIGH/CRITICAL)                         │ │
│  │    ├─ task_type                                                     │ │
│  │    ├─ depends_on_tasks (JSON - task UUIDs)                          │ │
│  │    ├─ status (PENDING/READY/IN_PROGRESS/COMPLETED/FAILED)           │ │
│  │    ├─ target_files, modified_files (JSON)                           │ │
│  │    ├─ llm_model, llm_prompt, llm_response                           │ │
│  │    ├─ llm_cost_usd, llm_tokens_*                                    │ │
│  │    ├─ validation_passed, validation_errors                          │ │
│  │    ├─ retry_count, max_retries, last_error                          │ │
│  │    └─ started_at, completed_at, failed_at                           │ │
│  │                                                                      │ │
│  │ 6. masterplan_subtasks                                               │ │
│  │    ├─ subtask_id (UUID, PK)                                         │ │
│  │    ├─ task_id (FK)                                                  │ │
│  │    ├─ subtask_number (1-7)                                          │ │
│  │    ├─ name, description                                             │ │
│  │    ├─ status (PENDING/COMPLETED)                                    │ │
│  │    ├─ completed (boolean)                                           │ │
│  │    └─ completed_at                                                  │ │
│  │                                                                      │ │
│  │ 7. masterplan_versions                                               │ │
│  │    ├─ version_id, masterplan_id                                     │ │
│  │    ├─ version_number                                                │ │
│  │    ├─ snapshot (JSON - complete state)                              │ │
│  │    └─ created_by, created_at                                        │ │
│  │                                                                      │ │
│  │ 8. masterplan_history                                                │ │
│  │    ├─ history_id, masterplan_id, task_id                            │ │
│  │    ├─ event_type, event_data (JSON)                                 │ │
│  │    ├─ actor (system/user/llm)                                       │ │
│  │    └─ created_at                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         MASTERPLAN API ENDPOINTS                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  src/api/routers/masterplans.py (648 LOC)                                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                                                                      │ │
│  │ REST API Endpoints:                                                 │ │
│  │                                                                      │ │
│  │ 1. POST /api/v1/masterplans                                         │ │
│  │    ├─ Request: {discovery_id, session_id}                           │ │
│  │    ├─ Creates: MasterPlan from DiscoveryDocument                    │ │
│  │    ├─ Uses: MasterPlanGenerator.generate_masterplan()              │ │
│  │    ├─ WebSocket: Emits progress via ws_manager                      │ │
│  │    └─ Response: {masterplan_id, status, message}                    │ │
│  │                                                                      │ │
│  │ 2. GET /api/v1/masterplans                                          │ │
│  │    ├─ Query: limit, offset, status filter                           │ │
│  │    ├─ Returns: List of masterplan summaries                         │ │
│  │    └─ Response: {masterplans[], total, limit, offset}               │ │
│  │                                                                      │ │
│  │ 3. GET /api/v1/masterplans/{masterplan_id}                          │ │
│  │    ├─ Returns: Complete masterplan with all relationships           │ │
│  │    │   ├─ Phases                                                    │ │
│  │    │   ├─ Milestones                                                │ │
│  │    │   ├─ Tasks (with subtasks)                                     │ │
│  │    │   └─ Progress metrics                                          │ │
│  │    └─ Response: Full nested JSON structure                          │ │
│  │                                                                      │ │
│  │ 4. POST /api/v1/masterplans/{masterplan_id}/approve                 │ │
│  │    ├─ Validates: status == DRAFT                                    │ │
│  │    ├─ Updates: status → APPROVED                                    │ │
│  │    └─ Response: Updated masterplan details                          │ │
│  │                                                                      │ │
│  │ 5. POST /api/v1/masterplans/{masterplan_id}/reject                  │ │
│  │    ├─ Request: {rejection_reason}                                   │ │
│  │    ├─ Updates: status → REJECTED                                    │ │
│  │    └─ Response: Rejection confirmation                              │ │
│  │                                                                      │ │
│  │ 6. POST /api/v1/masterplans/{masterplan_id}/execute                 │ │
│  │    ├─ Validates: status == APPROVED                                 │ │
│  │    ├─ Creates: Workspace via WorkspaceService                       │ │
│  │    ├─ Updates: status → IN_PROGRESS, workspace_path                 │ │
│  │    ├─ Executes: MasterplanExecutionService.execute()                │ │
│  │    │   (background task - async)                                    │ │
│  │    └─ Response: {workspace_id, workspace_path, total_tasks}         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    MASTERPLAN EXECUTION SERVICE (MVP)                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  src/services/masterplan_execution_service.py (696 LOC)                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ MasterplanExecutionService                                          │ │
│  │                                                                      │ │
│  │ 1. create_workspace(masterplan_id) → workspace_path                 │ │
│  │    ├─ Uses: WorkspaceService.create_workspace()                     │ │
│  │    ├─ Format: "masterplan_{project_name}"                           │ │
│  │    ├─ Stores: workspace_path in masterplans.workspace_path          │ │
│  │    └─ Returns: Absolute path                                        │ │
│  │                                                                      │ │
│  │ 2. execute(masterplan_id) → Dict[result]                            │ │
│  │    ├─ Load: Masterplan with all phases/milestones/tasks             │ │
│  │    ├─ Emit: masterplan_execution_start WebSocket event              │ │
│  │    ├─ Build: Dependency graph from tasks                            │ │
│  │    ├─ Sort: Topological sort → execution_order                      │ │
│  │    ├─ Execute: Tasks in dependency order                            │ │
│  │    │   └─ For each task:                                            │ │
│  │    │       ├─ _progress_callback(status="in_progress")              │ │
│  │    │       ├─ _execute_single_task(task) → STUB!                    │ │
│  │    │       │   ├─ TODO: Integrate OrchestratorAgent                 │ │
│  │    │       │   ├─ For now: Mark as completed                        │ │
│  │    │       │   └─ Extract target_files from task                    │ │
│  │    │       ├─ Retry logic (max 1 retry)                             │ │
│  │    │       ├─ Emit: task_execution_complete event                   │ │
│  │    │       └─ Update: Task status in DB                             │ │
│  │    ├─ Update: masterplan status → COMPLETED                         │ │
│  │    └─ Returns: {success, completed_tasks, failed_tasks}             │ │
│  │                                                                      │ │
│  │ ⚠️ CRITICAL GAP: _execute_single_task is STUB                       │ │
│  │    - No integration with MGE V2 execution                            │ │
│  │    - No integration with OrchestratorAgent                           │ │
│  │    - Just marks tasks as completed                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    REVIEW SYSTEM (95% COMPLETE)                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. Backend Components:                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ src/review/                                                         │ │
│  │  ├─ confidence_scorer.py                                            │ │
│  │  │   ├─ Formula: 40% validation + 30% retries +                     │ │
│  │  │   │           20% complexity + 10% integration                   │ │
│  │  │   └─ Thresholds: HIGH(≥0.85), MEDIUM(0.70-0.84),                │ │
│  │  │                   LOW(0.50-0.69), CRITICAL(<0.50)                │ │
│  │  │                                                                  │ │
│  │  ├─ queue_manager.py                                                │ │
│  │  │   ├─ select_for_review(percentage=0.15-0.20)                     │ │
│  │  │   └─ Bottom 15-20% by confidence score                           │ │
│  │  │                                                                  │ │
│  │  └─ ai_assistant.py                                                 │ │
│  │      └─ analyze_atom_for_review() → AI suggestions                  │ │
│  │                                                                      │ │
│  │ src/services/review_service.py                                      │ │
│  │  ├─ create_review(atom_id, auto_add_suggestions)                    │ │
│  │  ├─ get_review_queue(status, assigned_to, limit)                    │ │
│  │  ├─ approve_atom(review_id, reviewer_id, feedback)                  │ │
│  │  ├─ reject_atom(review_id, reviewer_id, feedback)                   │ │
│  │  ├─ edit_atom(review_id, reviewer_id, new_code, feedback)           │ │
│  │  └─ regenerate_atom(review_id, reviewer_id, feedback)               │ │
│  │                                                                      │ │
│  │ src/api/routers/review.py (438 LOC)                                 │ │
│  │  ├─ GET  /api/v2/review/queue                                       │ │
│  │  ├─ GET  /api/v2/review/{review_id}                                 │ │
│  │  ├─ POST /api/v2/review/approve                                     │ │
│  │  ├─ POST /api/v2/review/reject                                      │ │
│  │  ├─ POST /api/v2/review/edit                                        │ │
│  │  ├─ POST /api/v2/review/regenerate                                  │ │
│  │  ├─ POST /api/v2/review/assign                                      │ │
│  │  ├─ GET  /api/v2/review/statistics/{masterplan_id}                  │ │
│  │  ├─ POST /api/v2/review/create/{atom_id}                            │ │
│  │  └─ POST /api/v2/review/bulk-create/{masterplan_id}                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  2. Frontend Components (React):                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ src/ui/src/pages/review/ReviewQueue.tsx                             │ │
│  │  ├─ Displays review queue with filtering                            │ │
│  │  ├─ AI suggestions panel                                            │ │
│  │  ├─ Approve/Reject/Edit/Regenerate actions                          │ │
│  │  └─ Real-time updates via REST API                                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Critical Gaps Analysis

### 1. ❌ MISSING: MGE V2 Integration with MasterPlan Execution

**Problem:**
```python
# src/services/masterplan_execution_service.py:656
def _execute_single_task(self, task, masterplan_id) -> bool:
    """
    Execute a single task.

    This is a stub implementation for Group 3. Full implementation with
    OrchestratorAgent integration will be completed in a future iteration.
    """
    # TODO: Integrate with OrchestratorAgent for actual execution
    # For now, mark task as completed (stub)
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    self.db.commit()
    return True
```

**Impact:**
- MasterPlan execution doesn't actually execute tasks
- No connection to MGE V2 (AtomicUnits, WaveExecutor, RetryOrchestrator)
- Tasks are just marked as "completed" without code generation

**Fix Required:**
```python
# Integration needed:
def _execute_single_task(self, task, masterplan_id) -> bool:
    # 1. Convert MasterPlanTask → AtomicUnit(s)
    # 2. Use WaveExecutor to execute atoms in parallel
    # 3. Use RetryOrchestrator for retry logic
    # 4. Validate with AcceptanceGate
    # 5. Update task status based on results
```

---

### 2. ⚠️ PARTIAL: Acceptance Tests Integration

**Status:** Tests are generated but not executed automatically

**Evidence:**
- `src/testing/acceptance_gate.py` - Gate checking implemented ✅
- `src/testing/test_generator.py` - Auto-generation from masterplan ✅
- `src/api/routers/testing.py` - Complete API ✅
- **MISSING:** Automatic execution after wave completion ❌

**Fix Required:**
- Add hook in `WaveExecutor` to run acceptance tests after wave
- Implement `Gate S` validation before allowing next wave
- Report test failures back to review queue

---

### 3. ⚠️ PARTIAL: Human Review Workflow Integration

**Status:** Review system complete but not triggered automatically

**Evidence:**
- Confidence scoring: ✅
- Review queue management: ✅
- API endpoints: ✅
- UI components: ✅
- **MISSING:** Automatic review creation for low-confidence atoms ❌

**Fix Required:**
```python
# After task execution:
if atom.confidence_score < 0.70:
    review_service.create_review(
        atom_id=atom.atom_id,
        auto_add_suggestions=True
    )
```

---

### 4. ❌ MISSING: Progress Tracking for MGE V2 Execution

**Problem:**
- WebSocket events defined for masterplan generation ✅
- WebSocket events defined for task execution (MVP stub) ✅
- **MISSING:** WebSocket events for MGE V2 wave execution ❌

**Events Needed:**
```python
# For WaveExecutor:
- wave_execution_start(wave_id, total_atoms)
- atom_execution_progress(atom_id, status, current, total)
- atom_execution_complete(atom_id, result)
- wave_execution_complete(wave_id, success_count, fail_count)

# For RetryOrchestrator:
- atom_retry_start(atom_id, attempt_number, max_retries)
- atom_retry_failed(atom_id, final_error)

# For AcceptanceGate:
- acceptance_test_start(test_id, requirement)
- acceptance_test_result(test_id, passed, error)
- gate_validation_result(passed, must_rate, should_rate)
```

---

### 5. ⚠️ PARTIAL: Cost Tracking and Guardrails

**Status:** Cost calculation exists but not enforced during execution

**Evidence:**
- `src/cost/cost_guardrails.py` - Implemented ✅
- Soft/hard limits defined ✅
- **MISSING:** Integration with execution flow ❌

**Fix Required:**
```python
# Before executing wave:
cost_guardrails.check_before_execution(
    masterplan_id=masterplan_id,
    estimated_cost=wave.estimated_cost
)
```

---

## 📊 Component Status Matrix

| Component | Implementation | Tests | Integration | Status |
|-----------|---------------|-------|-------------|--------|
| **Chat Service** | 100% | 70% | ✅ | Production |
| **WebSocket** | 100% | 60% | ✅ | Production |
| **MasterPlan Generation** | 100% | 80% | ✅ | Production |
| **Database Models** | 100% | 90% | ✅ | Production |
| **REST API** | 100% | 75% | ✅ | Production |
| **Frontend Components** | 100% | 50% | ✅ | Production |
| **Review System** | 95% | 40% | ⚠️ | Needs Integration |
| **Acceptance Tests** | 100% | 60% | ⚠️ | Needs Auto-execution |
| **Execution Service (MVP)** | 80% | 70% | ❌ | STUB - needs MGE V2 |
| **MGE V2 Execution** | 100% | 84% | ❌ | Not connected |
| **WaveExecutor** | 100% | 100% | ❌ | Isolated |
| **RetryOrchestrator** | 100% | 100% | ❌ | Isolated |
| **Cost Guardrails** | 90% | 0% | ❌ | Not enforced |

---

## 🎯 Priority Recommendations

### Immediate Actions (Week 1)

1. **Connect MGE V2 to MasterPlan Execution**
   ```python
   # File: src/services/masterplan_execution_v2.py
   class MasterplanExecutionV2Service:
       def execute(self, masterplan_id):
           # 1. Convert tasks → atoms
           # 2. Build dependency graph
           # 3. Create waves with WaveExecutor
           # 4. Execute with RetryOrchestrator
           # 5. Validate with AcceptanceGate
           # 6. Trigger review for low-confidence
   ```

2. **Add WebSocket Events for MGE V2**
   ```python
   # Add to src/websocket/websocket_manager.py
   async def emit_wave_execution_start(session_id, wave_id, total_atoms)
   async def emit_atom_execution_progress(session_id, atom_id, status)
   async def emit_acceptance_test_result(session_id, test_id, passed)
   ```

3. **Auto-trigger Review for Low Confidence**
   ```python
   # After atom execution:
   if confidence_score < 0.70:
       review_service.create_review(atom_id, auto_add_suggestions=True)
   ```

### Medium Term (Week 2-3)

4. **Acceptance Test Auto-execution**
   - Add hook in WaveExecutor after wave completion
   - Execute acceptance tests automatically
   - Block next wave if Gate S fails

5. **Cost Guardrails Enforcement**
   - Add pre-execution cost check
   - Emit alerts when approaching soft limit
   - Block execution at hard limit

### Long Term (Week 4+)

6. **E2E Testing**
   - Complete flow test: Chat → Generation → Execution → Review
   - Verify all WebSocket events
   - Load testing with multiple concurrent masterplans

7. **Performance Optimization**
   - Database query optimization
   - WebSocket event batching
   - Caching strategies

---

## 📁 Key Files Reference

### Backend Core
- `src/services/chat_service.py` (977 LOC) - Chat orchestration
- `src/services/masterplan_generator.py` (1,019 LOC) - Plan generation
- `src/services/masterplan_execution_service.py` (696 LOC) - **STUB - needs MGE V2**
- `src/models/masterplan.py` (470 LOC) - Database models

### MGE V2 Components (Not Integrated)
- `src/mge/v2/execution/wave_executor.py` (270 LOC) - Parallel execution ✅
- `src/mge/v2/execution/retry_orchestrator.py` (350 LOC) - Retry logic ✅
- `src/testing/acceptance_gate.py` (328 LOC) - Gate validation ✅

### Review System
- `src/review/confidence_scorer.py` - Confidence calculation ✅
- `src/review/queue_manager.py` - Queue management ✅
- `src/services/review_service.py` - Review orchestration ✅
- `src/api/routers/review.py` (438 LOC) - REST API ✅

### API Layer
- `src/api/routers/masterplans.py` (648 LOC) - MasterPlan endpoints
- `src/api/routers/testing.py` (383 LOC) - Test endpoints
- `src/api/routers/websocket.py` (655 LOC) - WebSocket handlers

### Frontend
- `src/ui/src/components/chat/ChatWindow.tsx` - Main chat UI
- `src/ui/src/components/chat/MasterPlanProgressModal.tsx` - Progress display
- `src/ui/src/pages/review/ReviewQueue.tsx` - Review UI

---

## 📝 Conclusion

### ✅ What Works Well
1. **Complete generation flow** from chat to database persistence
2. **Real-time progress updates** via WebSocket
3. **Production-ready review system** (95% complete)
4. **Comprehensive database schema** with all relationships
5. **Clean API separation** between generation and execution

### ❌ Critical Gaps
1. **No connection between MasterPlan and MGE V2 execution**
2. **Acceptance tests not auto-executed**
3. **Review system not auto-triggered**
4. **Cost guardrails not enforced**
5. **Missing WebSocket events for MGE V2 execution**

### 🎯 Next Steps
1. **Week 1:** Integrate MGE V2 with MasterPlan execution
2. **Week 2:** Add auto-execution for acceptance tests
3. **Week 3:** Connect review system to execution flow
4. **Week 4:** E2E testing and optimization

**Bottom Line:** El sistema tiene todos los componentes necesarios, pero están **desconectados**. La prioridad es crear el **orchestration layer** que los una.
