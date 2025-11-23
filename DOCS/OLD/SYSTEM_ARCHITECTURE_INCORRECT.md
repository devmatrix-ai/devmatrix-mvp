# System Architecture

**Document Date:** 2025-11-23
**Status:** Complete Architecture Documentation
**Version:** 1.0
**Scope:** Complete agentic-ai system design, components, and integration

---

## Executive Summary

The agentic-ai system is an autonomous software development platform that transforms natural language specifications into fully functional applications. It combines retrieval-augmented generation, multi-phase planning, and intelligent code generation to create production-ready code.

### Key Characteristics

| Aspect | Details |
|--------|---------|
| **Architecture Pattern** | Event-driven, microservices-inspired |
| **Data Sources** | 4 databases (PostgreSQL, Redis, Neo4j, Qdrant) |
| **Processing Model** | Multi-phase pipeline (11 sequential phases) |
| **Scalability** | Horizontal (stateless services, distributed execution) |
| **Deployment** | Docker Compose (5 containers) |
| **Test Coverage** | 1,798 tests, 92% coverage |
| **Primary Language** | Python 3.10+ (backend), TypeScript (frontend) |

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Layers](#core-layers)
3. [Data Architecture](#data-architecture)
4. [Processing Pipeline](#processing-pipeline)
5. [Integration Patterns](#integration-patterns)
6. [Deployment Architecture](#deployment-architecture)
7. [Component Communication](#component-communication)
8. [Error Handling & Recovery](#error-handling--recovery)
9. [Security Architecture](#security-architecture)
10. [Performance Characteristics](#performance-characteristics)

---

## System Overview

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  React 18 UI (TypeScript) - Chat, History, Settings        │  │
│  │  Real-time WebSocket, Streaming responses                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼───────────────────────────────────────────┐
│                       API GATEWAY LAYER                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application with JWT Auth, CORS, Rate Limiting    │  │
│  │  Router endpoints: chat, masterplans, executions, rag       │  │
│  │  Middleware: Auth, Logging, Metrics, Error Handling        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────────┘
                       │ Internal APIs
┌──────────────────────▼───────────────────────────────────────────┐
│                   CORE APPLICATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    ORCHESTRATION                             │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │  OrchestratorMVP (11-Phase Pipeline Controller)        │ │ │
│  │  │  - Multi-Pass Planning                                 │ │ │
│  │  │  - DAG Building & Execution Coordination               │ │ │
│  │  │  - Progress Tracking & Metrics                         │ │ │
│  │  │  - Pattern Learning & Feedback Loop                    │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  COGNITIVE ENGINE                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │ │
│  │  │    IR    │  │ Planning │  │ Patterns │  │   CPIE   │    │ │
│  │  │Builder   │  │ (Multi-  │  │ (Pattern │  │(Inference)   │ │
│  │  │(Spec →  │  │  Pass)   │  │  Bank +  │  │            │ │
│  │  │ Models) │  │          │  │ Learning)│  │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │  Validation (Ensemble + E2E) + Signatures            │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               CODE GENERATION LAYER                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │  │Behavior  │ │ Behavior │ │OpenAPI   │ │ Modular  │        │ │
│  │  │Code Gen  │ │Validation│ │Generator │ │Generator │        │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │ │
│  │  Production Code Generators (Fallback)                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               SERVICE LAYER                                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │  │MasterPlan│ │ Atomic   │ │Code Exec │ │ File     │        │ │
│  │  │Generator │ │Spec Gen  │ │Service   │ │Writer    │        │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │ │
│  │  Business Logic Extraction + Error Pattern Store            │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
┌───────▼──────┐ ┌────▼──────┐ ┌────▼──────┐ ┌────▼──────┐
│  RAG SYSTEM  │ │ DATA LAYER │ │   AUDIT   │ │ REAL-TIME │
│              │ │            │ │  & LOGS   │ │  STATE    │
│  ┌────────┐  │ │┌────────┐  │ │┌────────┐ │ │┌────────┐ │
│  │ Qdrant │  │ ││ Postgres│  │ ││ Postgres│ │ ││ Redis  │ │
│  │ (Vec)  │  │ ││ (App   │  │ ││ (Audit) │ │ ││ (Cache)│ │
│  └────────┘  │ ││ State) │  │ │└────────┘ │ │ └────────┘ │
│  ┌────────┐  │ │└────────┘  │ │           │ │            │
│  │ Neo4j  │  │ │┌────────┐  │ │           │ │            │
│  │ (Graph)│  │ ││ Redis  │  │ │           │ │            │
│  └────────┘  │ ││(Cache) │  │ │           │ │            │
│  ┌────────┐  │ │└────────┘  │ │           │ │            │
│  │ChromaDB│  │ │            │ │           │ │            │
│  │(Semantic)  │ │            │ │           │ │            │
│  └────────┘  │ │            │ │           │ │            │
└───────┬──────┘ └────┬───────┘ └────┬──────┘ └────┬───────┘
        │              │              │              │
        └──────────────┼──────────────┴──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   INFRASTRUCTURE LAYER      │
        │  ┌──────────────────────┐   │
        │  │  Docker Compose      │   │
        │  │  Network Policies    │   │
        │  │  Health Checks       │   │
        │  │  Volume Management   │   │
        │  └──────────────────────┘   │
        └─────────────────────────────┘
```

---

## Core Layers

### Layer 1: User Interface Layer

**Technology**: React 18 + TypeScript + Vite + Tailwind CSS

**Responsibilities**:
- Chat interface with streaming support
- Conversation history management
- Real-time WebSocket communication
- Settings and preferences
- Export/import functionality
- Dark mode support

**Key Components**:
```
src/ui/
├── components/
│   ├── Chat.tsx              # Main chat interface
│   ├── Message.tsx           # Message rendering
│   ├── MessageInput.tsx       # User input component
│   ├── History.tsx           # Conversation history
│   └── ... (other components)
├── pages/
│   ├── ChatPage.tsx
│   ├── HistoryPage.tsx
│   ├── SettingsPage.tsx
│   └── ...
├── hooks/
│   ├── useChat.ts            # Chat API hook
│   ├── useConversation.ts    # Conversation state
│   └── ...
├── services/
│   ├── api.ts                # API client
│   ├── websocket.ts          # WebSocket client
│   └── ...
├── stores/
│   └── chatStore.ts          # State management
└── App.tsx                   # Root component
```

**Communication**: HTTP REST + WebSocket (SSE streaming)

### Layer 2: API Gateway Layer

**Technology**: FastAPI + Python 3.10+

**Responsibilities**:
- Request routing and handling
- Authentication & Authorization (JWT)
- Request/response validation
- Rate limiting
- CORS handling
- Error standardization
- Middleware chain

**Entry Point**: [src/api/app.py]

```python
app = FastAPI(
    title="Agentic AI",
    description="Autonomous Software Development Platform",
    version="1.0.0",
    lifespan=lifespan  # Startup/shutdown hooks
)

# Applied Middleware
app.add_middleware(CORSMiddleware, ...)      # CORS
app.add_middleware(JWTAuthMiddleware, ...)   # Authentication
app.add_middleware(RequestLoggingMiddleware, ...) # Logging
app.add_middleware(MetricsMiddleware, ...)   # Metrics

# Router Registration
app.include_router(auth_router)              # /api/auth
app.include_router(chat_router)              # /api/chat
app.include_router(masterplans_router)       # /api/masterplans
app.include_router(executions_router)        # /api/executions
app.include_router(rag_router)               # /api/rag
app.include_router(health_router)            # /health
```

**Key Routers**:

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| auth_router | /login, /register, /token, /refresh | User authentication |
| chat_router | /chat, /chat/stream, /chat/history | Chat interactions |
| masterplans_router | /masterplans, /masterplans/{id} | Plan management |
| executions_router | /executions, /executions/{id} | Execution tracking |
| rag_router | /rag/retrieve, /rag/patterns | RAG operations |
| validation_router | /validate, /validate/result | Code validation |
| health_router | /health, /ready, /live | Health checks |

### Layer 3: Core Application Layer

**Responsibilities**:
- Business logic orchestration
- Spec-to-code transformation
- Execution planning and coordination
- Pattern management
- Code generation

**Structure**:

```
src/
├── cognitive/
│   ├── orchestration/
│   │   └── orchestrator_mvp.py   # Main orchestrator (11-phase pipeline)
│   ├── ir/
│   │   ├── application_ir.py     # Root data model
│   │   ├── domain_model.py       # Entity definitions
│   │   ├── api_model.py          # REST endpoint definitions
│   │   ├── infrastructure_model.py # Database/infra config
│   │   ├── behavior_model.py     # Business rules
│   │   └── ir_builder.py         # IR construction
│   ├── planning/
│   │   ├── multi_pass_planner.py # Task decomposition
│   │   └── dag_builder.py        # Dependency graph building
│   ├── patterns/
│   │   ├── pattern_bank.py       # Pattern management
│   │   ├── pattern_classifier.py # Pattern classification
│   │   └── pattern_feedback_integration.py # Learning loop
│   ├── inference/
│   │   └── cpie.py               # Core Pattern Inference Engine
│   ├── validation/
│   │   ├── ensemble_validator.py # Multi-validator
│   │   └── e2e_production_validator.py # Full validation
│   └── signatures/
│       └── semantic_signature.py # Semantic task representation
├── rag/
│   └── (see RAG_SYSTEM.md)       # Retrieval-augmented generation
├── services/
│   ├── code_generation_service.py    # Main code generator
│   ├── masterplan_generator.py       # Plan creation
│   ├── masterplan_execution_service.py # Plan execution
│   ├── atomic_spec_generator.py      # Atomic task specs
│   ├── behavior_code_generator.py    # Behavior code generation
│   ├── validation_code_generator.py  # Test code generation
│   └── (20+ other services)
└── models/
    └── (SQLAlchemy ORM models)
```

---

## Data Architecture

### Database Topology

```
┌────────────────────────────────────────────────────────┐
│             Data Architecture Overview                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│  PostgreSQL (Primary Data Store)                      │
│  ├── conversations & messages (Chat history)          │
│  ├── masterplans & masterplan_tasks (Execution)      │
│  ├── atomic_specs & atomic_units (Tasks)             │
│  ├── validation_results & acceptance_tests (QA)      │
│  ├── users, roles, security_events (Auth & Audit)    │
│  ├── human_reviews & dependency_graphs (Control)     │
│  └── alert_history & user_usage (Monitoring)         │
│                                                        │
│  Redis (Real-time Cache & State)                     │
│  ├── session_data (User sessions)                     │
│  ├── execution_state (Current execution status)      │
│  ├── rag_cache (RAG query results, 1hr TTL)         │
│  ├── locks (Distributed locks)                       │
│  └── metrics (Real-time metrics)                      │
│                                                        │
│  Neo4j (Knowledge Graph)                             │
│  ├── Pattern nodes (30,314 nodes)                    │
│  ├── Entity nodes                                    │
│  ├── Relationship edges (159,793 edges)              │
│  ├── Dependency relationships                        │
│  └── Pattern evolution tracking                      │
│                                                        │
│  Qdrant (Vector Database)                            │
│  ├── Pattern embeddings (21,624 patterns, 768-dim)  │
│  ├── Code snippet embeddings                         │
│  ├── Query cache (similar queries)                   │
│  └── Multiple specialized collections               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### PostgreSQL Schema (Key Tables)

```sql
-- User Management
users (id, email, username, password_hash, created_at, updated_at)
roles (id, name, permissions)
user_roles (user_id, role_id)

-- Chat Persistence
conversations (id, user_id, title, created_at, updated_at)
messages (id, conversation_id, role, content, timestamp)

-- Execution Planning
masterplans (id, application_id, status, created_at)
masterplan_tasks (id, masterplan_id, task_name, status, rag_context)

-- Task Management
atomic_specs (id, task_id, code_type, specification)
atomic_units (id, atomic_spec_id, atom_type, parsed_content)
execution_waves (id, masterplan_id, level, status)

-- Validation & Quality
validation_results (id, execution_id, validator_type, passed, details)
acceptance_tests (id, scenario, input_data, expected_outcome)

-- Audit & Monitoring
audit_logs (id, action, actor_id, resource, timestamp)
security_events (id, event_type, severity, description)
alert_history (id, alert_type, status, resolution)
user_usage (id, user_id, tokens_used, cost, timestamp)

-- Dependencies
dependency_graphs (id, masterplan_id, dag_json)
human_reviews (id, execution_id, reviewer_id, status, feedback)
```

### Data Flow Through Databases

```
User Spec Input
     ↓
  [Parsed & stored in PostgreSQL conversations]
     ↓
  [RAG retrieves patterns from Qdrant + Neo4j]
     ↓
  [Planning creates tasks, stored in PostgreSQL masterplans]
     ↓
  [Execution state cached in Redis]
     ↓
  [Results stored in PostgreSQL + cached in Redis]
     ↓
  [Patterns learned back to Qdrant + Neo4j]
```

---

## Processing Pipeline

### 11-Phase Execution Model

The system operates through 11 sequential phases, with parallel execution within compatible levels:

```
Phase 1: SPEC INGESTION
├─ Parse user specification
├─ Extract requirements
└─ Create SpecRequirements object
     ↓
Phase 2: REQUIREMENTS ANALYSIS
├─ Classify requirements
├─ Identify constraints
├─ Extract entities/attributes
└─ Create RequirementsAnalysis object
     ↓
Phase 3: MULTI-PASS PLANNING
├─ Decompose spec into atomic tasks
├─ Create semantic signatures
├─ Apply pattern matching
└─ Return List[AtomicTask]
     ↓
Phase 4: ATOMIZATION
├─ Parse planned tasks
├─ Extract atomic units
├─ Create atomic specifications
└─ Return List[AtomicSpec]
     ↓
Phase 5: DAG CONSTRUCTION
├─ Analyze task dependencies
├─ Build dependency graph
├─ Identify parallelizable levels
└─ Return ExecutionDAG
     ↓
Phase 6: CODE GENERATION
├─ For each task:
│  ├─ Retrieve RAG patterns
│  ├─ Generate code
│  ├─ Apply patterns
│  └─ Validate syntax
└─ Return List[CodeFile]
     ↓
Phase 7: DEPLOYMENT
├─ Setup infrastructure
├─ Deploy database
├─ Configure environment
└─ Initialize application
     ↓
Phase 8: CODE REPAIR
├─ Identify issues
├─ Analyze error patterns
├─ Apply fixes
├─ Re-validate
└─ Return RepairResult
     ↓
Phase 9: VALIDATION
├─ Run syntax checks
├─ Run type checks
├─ Run semantic validation
├─ Run business rule validation
└─ Return ValidationResult
     ↓
Phase 10: HEALTH VERIFICATION
├─ Check system health
├─ Verify endpoints
├─ Run basic tests
├─ Confirm deployment success
└─ Return HealthStatus
     ↓
Phase 11: LEARNING
├─ Collect execution metrics
├─ Analyze success patterns
├─ Store in pattern bank
├─ Update Neo4j graph
└─ Update Qdrant embeddings
```

**Execution Strategy**: Level-by-level with intra-level parallelization

```python
# Execution pattern from orchestrator_mvp.py

for level in dag.levels:  # Sequential levels
    tasks_at_level = dag.get_tasks_at_level(level)

    # Execute in parallel within level
    results = await asyncio.gather(
        *[execute_task(task) for task in tasks_at_level],
        return_exceptions=True
    )

    # Error handling
    for result in results:
        if isinstance(result, Exception):
            handle_error(result)

    # Store results before next level
    await store_results(results)
```

---

## Integration Patterns

### Pattern 1: RAG-Enhanced Code Generation

```python
# Workflow: Task → RAG Retrieval → Code Generation → Validation

async def generate_with_rag(task: AtomicTask) -> GeneratedCode:
    # 1. Retrieve patterns
    rag_context = await rag_retriever.retrieve(
        query=task.name,
        domain=task.domain,
        max_results=5
    )

    # 2. Build prompt with pattern context
    prompt = build_prompt(task, rag_context.patterns)

    # 3. Generate code
    code = await llm.generate(prompt)

    # 4. Validate against patterns
    validation_result = validate_against_patterns(code, rag_context)

    if not validation_result.passed:
        # 5. Repair and retry
        code = await repair_code(code, validation_result.issues)

    # 6. Store successful pattern for learning
    if validation_result.passed:
        await pattern_bank.promote_pattern(code, task)

    return GeneratedCode(code=code, patterns_used=rag_context)
```

### Pattern 2: Orchestrated Task Execution

```python
# Workflow: Plan → DAG → Parallel Execution → Aggregation

async def execute_plan(plan: MasterPlan):
    # 1. Create DAG
    dag = dag_builder.build(plan)

    # 2. Execute level-by-level
    execution_results = []
    for level in dag.levels:
        level_results = await execute_level_in_parallel(level)
        execution_results.extend(level_results)

        # Check for critical failures
        if any(r.failed for r in level_results):
            await handle_failures(level_results)

    # 3. Aggregate results
    final_result = aggregate_results(execution_results)

    # 4. Store and report
    await store_execution_result(final_result)
    return final_result
```

### Pattern 3: Feedback Loop for Pattern Learning

```python
# Workflow: Execute → Measure → Learn → Update Knowledge Base

async def execute_with_learning(task: AtomicTask):
    # 1. Execute task
    start_time = time.time()
    result = await cpie.execute(task)
    execution_time = time.time() - start_time

    # 2. Measure success
    quality_score = measure_quality(result)
    success = quality_score > QUALITY_THRESHOLD

    # 3. Learn from execution
    if success:
        learning = {
            "patterns_used": task.rag_context.pattern_ids,
            "execution_time": execution_time,
            "quality_score": quality_score,
            "success": True
        }

        # 4. Update pattern bank
        await pattern_bank.update_patterns(learning)

        # 5. Store in Neo4j
        await neo4j_repository.record_successful_execution(learning)
```

---

## Deployment Architecture

### Docker Compose Setup

```yaml
version: '3.8'

services:
  # API Server
  api:
    image: agentic-ai:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db/agentic_ai
      - REDIS_URL=redis://redis:6379
      - NEO4J_URL=bolt://neo4j:7687
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - db
      - redis
      - neo4j
      - qdrant
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: agentic_ai
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Neo4j Graph Database
  neo4j:
    image: neo4j:5.3-community
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_apoc_import_file_enabled: 'true'
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p password 'return 1' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Frontend (optional)
  ui:
    image: agentic-ai-ui:latest
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
  neo4j_data:
  qdrant_data:

networks:
  default:
    name: agentic-ai-network
```

### Health Check Strategy

```python
# src/api/health.py

@router.get("/health")
async def health_check():
    """Basic health check (quick)"""
    return {"status": "healthy", "timestamp": datetime.now()}

@router.get("/ready")
async def readiness_check():
    """Readiness check (all dependencies)"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "neo4j": await check_neo4j(),
        "qdrant": await check_qdrant(),
        "api": True
    }

    ready = all(checks.values())
    return {
        "ready": ready,
        "checks": checks,
        "timestamp": datetime.now()
    }

@router.get("/live")
async def liveness_check():
    """Liveness check (server is running)"""
    return {"alive": True, "timestamp": datetime.now()}
```

---

## Component Communication

### Synchronous Communication

```
Client Request
    ↓
FastAPI Endpoint Handler
    ↓
Business Logic Service
    ↓
Database Query
    ↓
Response
    ↓
Client
```

**Example**: Chat message handling

```python
@router.post("/api/chat")
async def create_message(request: ChatRequest):
    # 1. Validate JWT
    user = validate_token(request.auth_token)

    # 2. Store message
    conversation = db.query(Conversation).get(request.conversation_id)
    message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )
    db.add(message)
    db.commit()

    # 3. Process (can be async)
    response = await process_message(message)

    # 4. Return
    return {"response": response}
```

### Asynchronous Communication

```
Task Queue
    ↓
Async Worker
    ↓
Long-Running Process
    ↓
Update State
    ↓
Webhook / Long Poll / WebSocket
    ↓
Client
```

**Example**: Code generation

```python
@router.post("/api/masterplans/{plan_id}/execute")
async def execute_plan(plan_id: str):
    # 1. Queue execution
    job = JobQueue.create(
        job_type="execute_plan",
        plan_id=plan_id
    )

    # 2. Async task
    asyncio.create_task(execute_plan_async(plan_id, job.id))

    # 3. Return job ID immediately
    return {"job_id": job.id, "status": "queued"}

# Long-running task
async def execute_plan_async(plan_id: str, job_id: str):
    try:
        # 4. Execute in background
        result = await orchestrator.execute(plan_id)

        # 5. Update state
        job.update(status="completed", result=result)

    except Exception as e:
        job.update(status="failed", error=str(e))

# Client polling
@router.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    job = JobQueue.get(job_id)
    return {
        "status": job.status,
        "result": job.result if job.status == "completed" else None
    }
```

### Real-Time Communication (WebSocket)

```
Client connects to WebSocket
    ↓
Server establishes connection
    ↓
Client sends message
    ↓
Server processes stream
    ↓
Server sends updates (push)
    ↓
Client receives updates in real-time
    ↓
Client disconnects
```

**Example**: Streaming code generation

```python
@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    try:
        while True:
            # 1. Receive message
            data = await websocket.receive_json()
            message = data.get("message")

            # 2. Start generation
            async with chat_service.generate_stream(message) as stream:
                # 3. Stream response chunks
                async for chunk in stream:
                    await websocket.send_json({
                        "type": "chunk",
                        "content": chunk
                    })

            # 4. Signal completion
            await websocket.send_json({
                "type": "complete",
                "timestamp": datetime.now()
            })

    except WebSocketDisconnect:
        print(f"Client {conversation_id} disconnected")
```

---

## Error Handling & Recovery

### Error Handling Strategy

```python
# Multi-layer error handling

# 1. INPUT VALIDATION LAYER
@router.post("/api/chat")
async def create_message(request: ChatRequest):
    if not request.message or len(request.message) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Message length must be 1-10000 characters"
        )

# 2. BUSINESS LOGIC LAYER
async def generate_code(spec: SpecRequirements):
    try:
        # Try primary method
        result = await llm.generate(spec)
    except RateLimitError as e:
        # Handle rate limit with backoff
        await exponential_backoff(e.retry_after)
        result = await llm.generate(spec)
    except LLMError as e:
        # Fall back to pattern-based generation
        logger.warning(f"LLM error: {e}, using fallback")
        result = await fallback_generator.generate(spec)

# 3. DATABASE LAYER
async def store_execution_result(result: ExecutionResult):
    try:
        db.add(result)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Handle duplicate/constraint violation
        logger.error(f"Integrity error: {e}")
        raise HTTPException(status_code=409, detail="Conflict")
    except DatabaseError as e:
        db.rollback()
        # General database error
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# 4. API RESPONSE LAYER
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.now(),
            "request_id": request.headers.get("x-request-id")
        }
    )
```

### Retry Strategy

```python
# Exponential backoff with jitter
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise

            # Calculate backoff: base_delay * (2^attempt) + jitter
            base_delay = 1
            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0, delay * 0.1)
            total_delay = delay + jitter

            logger.warning(f"Attempt {attempt+1} failed, retrying in {total_delay}s")
            await asyncio.sleep(total_delay)
```

---

## Security Architecture

### Authentication Flow

```
User Login Request
    ↓
┌─────────────────────┐
│ Validate Credentials│
│ (email + password)  │
└──────────┬──────────┘
           ↓
    ┌──────────────┐
    │ Hash matches?│
    └──┬───────┬───┘
       │       │
    Yes│       │No
       │       └─→ Return 401
       ↓
    ┌──────────────────────┐
    │ Create JWT Token     │
    │ (Claims: user_id,    │
    │  role, exp, iat)     │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ Return Token         │
    │ (httpOnly cookie)    │
    └──────────────────────┘
```

### Authorization Checks

```python
# Role-based access control (RBAC)

@router.delete("/api/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Check permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete users"
        )

    # Proceed with deletion
    db.delete(db.query(User).get(user_id))
    db.commit()
    return {"deleted": True}
```

### Data Protection

```python
# Encryption at rest (PostgreSQL)
# SSL/TLS in transit (HTTPS)
# JWT token security (httpOnly, secure, samesite)
# Secrets management (environment variables)
# SQL injection prevention (parameterized queries)
# CORS whitelist (approved origins)
```

---

## Performance Characteristics

### Throughput

| Operation | Throughput | Latency |
|-----------|-----------|---------|
| Chat message | 100+ req/s | 200-500ms |
| RAG retrieval | 50+ req/s | 100-150ms |
| Code generation | 5-10 req/s | 10-30s (LLM bound) |
| Execution | 1-2 concurrent | 5-60min (complexity dependent) |

### Scalability

```
Horizontal Scaling:
├─ API servers: Stateless, load balanced (horizontal)
├─ Workers: Async task queue (horizontal)
├─ RAG system: Read-replicas (horizontal)
└─ Data stores: Managed services (vertical)

Caching Strategy:
├─ Browser cache: Assets (static files)
├─ Redis cache: Sessions, RAG results, execution state
├─ Query cache: Database result caching
└─ CDN: Static content distribution
```

### Resource Usage

```
Memory Per Process:
├─ API server: 300-500MB
├─ Worker: 200-400MB
├─ Total system: 2-4GB

Database Storage:
├─ PostgreSQL: 1-10GB (varies by execution history)
├─ Neo4j: 2-5GB (knowledge graph)
├─ Qdrant: 3-8GB (vector embeddings)
└─ Redis: 100-500MB (cache)

GPU Usage:
├─ LLM inference: Optional (external API)
└─ Embeddings: CPU (GraphCodeBERT)
```

---

## Monitoring & Observability

### Metrics Collection

```python
# Prometheus metrics

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# Execution metrics
execution_duration = Histogram(
    'execution_duration_seconds',
    'Execution duration by phase',
    ['phase']
)

# RAG metrics
rag_retrieval_time = Histogram(
    'rag_retrieval_time_ms',
    'RAG retrieval time'
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'RAG cache hit percentage'
)
```

### Logging

```python
# Structured logging with JSON format

import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Example log entry
logger.info(json.dumps({
    "timestamp": datetime.now().isoformat(),
    "level": "INFO",
    "message": "Task execution completed",
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "duration_seconds": 45.2,
    "status": "success",
    "metrics": {
        "tokens_used": 1500,
        "cost_usd": 0.03
    }
}))
```

---

## Future Architecture Enhancements

1. **Microservices Split**: Separate code generation, validation, and execution services
2. **Event Bus**: Message broker (RabbitMQ/Kafka) for decoupled communication
3. **Plugin System**: Allow custom generators and validators
4. **Multi-Tenancy**: Complete tenant isolation
5. **AI Backbone**: Hybrid model (local + remote LLMs)
6. **Real-time Collaboration**: Multi-user code generation sessions
7. **Advanced Caching**: Distributed cache with invalidation strategy
8. **Performance Optimization**: Request batching, query optimization, lazy loading

---

**Last Updated**: 2025-11-23
**Maintained By**: Agentic AI Team
**Version**: 1.0
