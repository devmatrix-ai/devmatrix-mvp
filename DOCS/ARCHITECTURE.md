# Devmatrix Architecture

Comprehensive architecture documentation for the Devmatrix AI code generation system.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Workflow Diagrams](#workflow-diagrams)
4. [Data Flow](#data-flow)
5. [State Management](#state-management)
6. [Technology Stack](#technology-stack)

---

## System Overview

Devmatrix is an AI-powered code generation system built on LangGraph, featuring human-in-loop approval gates and Git integration.

### High-Level Architecture

```mermaid
graph TB
    User[👤 User] --> CLI[CLI Interface]
    CLI --> Agent[CodeGenerationAgent]
    Agent --> LLM[Claude Sonnet 4.5]
    Agent --> Tools[Tools Layer]
    Agent --> State[State Management]

    Tools --> WS[WorkspaceManager]
    Tools --> Files[FileOperations]
    Tools --> Git[GitOperations]

    State --> Redis[(Redis Cache)]
    State --> Postgres[(PostgreSQL)]

    style Agent fill:#4CAF50
    style LLM fill:#FF9800
    style State fill:#2196F3
```

---

## Component Architecture

### 1. CodeGenerationAgent (Core)

The central agent orchestrating the code generation workflow using LangGraph.

```mermaid
graph LR
    A[Analyze] --> P[Plan]
    P --> G[Generate]
    G --> R[Review]
    R --> H[Human Approval]
    H -->|Approved| W[Write File]
    H -->|Rejected| E[End]
    H -->|Modify| G
    W --> C[Git Commit]
    C --> L[Log Decision]
    L --> E

    style H fill:#FF5722
    style G fill:#4CAF50
    style C fill:#FFC107
```

**Responsibilities**:
- Request analysis and requirement extraction
- Implementation planning
- Code generation with Claude Sonnet 4.5
- Self-review with quality scoring
- Human approval gate management
- File writing and Git commits
- Decision logging to PostgreSQL

### 2. Tools Layer

#### WorkspaceManager
- Creates isolated workspace environments
- Manages workspace lifecycle (create/cleanup)
- Handles path traversal protection
- Supports context manager protocol

```python
with WorkspaceManager("my-project") as ws:
    ws.write_file("code.py", content)
    # Auto-cleanup on exit if auto_cleanup=True
```

#### FileOperations
- Safe file read/write/delete operations
- Directory management
- File metadata and hashing
- Tree structure visualization

#### GitOperations
- Repository initialization and status
- File staging and commits
- Diff generation
- Commit history tracking

### 3. State Management

```mermaid
graph TB
    Agent[Agent Execution] --> Redis[Redis - Workflow State]
    Agent --> Postgres[PostgreSQL - Persistent Storage]

    Redis --> Cache[LLM Response Cache]
    Redis --> WF[Workflow State - 1h TTL]

    Postgres --> Projects[Projects Table]
    Postgres --> Tasks[Tasks Table]
    Postgres --> Decisions[Decisions Table]
    Postgres --> Costs[Costs Table]

    style Redis fill:#DC382D
    style Postgres fill:#336791
```

#### Redis Manager
- **Purpose**: Fast in-memory caching
- **Use Cases**:
  - Workflow state caching (1 hour TTL)
  - LLM response caching (1 hour TTL)
  - Session data
- **Performance**: Sub-millisecond access

#### PostgreSQL Manager
- **Purpose**: Persistent storage and audit trail
- **Schema**:
  - `projects`: Project metadata
  - `tasks`: Task execution records
  - `decisions`: Human approval decisions
  - `costs`: Token usage and cost tracking

---

## Workflow Diagrams

### Complete Code Generation Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Agent
    participant LLM as Claude API
    participant Files
    participant Git
    participant DB as PostgreSQL

    User->>CLI: devmatrix generate "request"
    CLI->>Agent: invoke(user_request)

    Agent->>LLM: Analyze request
    LLM-->>Agent: Requirements + filename

    Agent->>LLM: Create plan
    LLM-->>Agent: Implementation plan

    Agent->>LLM: Generate code
    LLM-->>Agent: Python code

    Agent->>LLM: Review code
    LLM-->>Agent: Quality score + feedback

    Agent->>User: Show code + quality score
    User->>Agent: approve/reject/modify

    alt Approved
        Agent->>Files: Write file
        Files-->>Agent: File path

        Agent->>LLM: Generate commit message
        LLM-->>Agent: Conventional commit message

        Agent->>Git: Commit with message
        Git-->>Agent: Commit hash

        Agent->>DB: Log decision + metadata
        DB-->>Agent: Decision ID

        Agent-->>CLI: Success result
        CLI-->>User: Display summary
    else Rejected
        Agent->>DB: Log rejection
        Agent-->>CLI: Rejected
    else Modify
        User->>Agent: Provide feedback
        Agent->>LLM: Regenerate with feedback
        Note over Agent,User: Loop back to generation
    end
```

### Human Approval Flow

```mermaid
stateDiagram-v2
    [*] --> ShowCode: Code Generated
    ShowCode --> WaitInput: Display with Quality Score
    WaitInput --> Approved: User approves
    WaitInput --> Rejected: User rejects
    WaitInput --> Modify: User requests changes

    Approved --> WriteFile: Save to workspace
    WriteFile --> GitCommit: Commit to Git
    GitCommit --> [*]

    Rejected --> LogRejection: Record decision
    LogRejection --> [*]

    Modify --> GetFeedback: Prompt for feedback
    GetFeedback --> Regenerate: Pass to LLM
    Regenerate --> ShowCode: Show updated code
```

### Git Integration Flow

```mermaid
flowchart TD
    Start[File Written] --> CheckGit{Git Enabled?}
    CheckGit -->|No| Skip[Skip Git Commit]
    CheckGit -->|Yes| CheckRepo{Repo Exists?}

    CheckRepo -->|No| Init[git init]
    Init --> Stage
    CheckRepo -->|Yes| Stage[git add file]

    Stage --> GenMsg[LLM: Generate commit message]
    GenMsg --> Commit[git commit -m message]
    Commit --> Extract[Extract commit hash]
    Extract --> Log[Log to PostgreSQL]
    Log --> End[Complete]
    Skip --> End

    style Init fill:#FFC107
    style GenMsg fill:#4CAF50
    style Commit fill:#2196F3
```

---

## Data Flow

### State Structure (LangGraph)

```python
class CodeGenState(TypedDict):
    # Input
    user_request: str
    context: dict

    # Planning
    plan: dict
    tasks: list

    # Generation
    generated_code: str
    target_filename: str

    # Review
    review_feedback: str
    code_quality_score: float

    # Approval
    approval_status: Literal["pending", "approved", "rejected", "needs_modification"]
    user_feedback: str

    # File Operations
    workspace_id: str
    file_written: bool
    file_path: str

    # Git Integration
    git_enabled: bool
    git_commit_message: str
    git_commit_hash: str
    git_committed: bool

    # Tracking
    messages: Sequence[dict]
    decision_id: str
```

### Database Schema

```sql
-- Projects
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    agent_name VARCHAR(100),
    task_type VARCHAR(50),
    input_data TEXT,
    output_data TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Decisions
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    decision_point VARCHAR(100),
    options TEXT[],
    selected_option VARCHAR(100),
    rationale TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Costs
CREATE TABLE costs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    model VARCHAR(50),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## State Management

### Redis Caching Strategy

```mermaid
graph LR
    Request[LLM Request] --> Check{Cache Hit?}
    Check -->|Yes| Return[Return Cached]
    Check -->|No| API[Call API]
    API --> Store[Store in Redis]
    Store --> Return

    Return --> TTL{TTL Expired?}
    TTL -->|Yes| Evict[Auto-evict]
    TTL -->|No| Keep[Keep in cache]

    style Check fill:#4CAF50
    style API fill:#FF9800
```

**Cache Keys**:
- `workflow:{workflow_id}` - Workflow state (1h TTL)
- `llm_cache:{prompt_hash}` - LLM responses (1h TTL)

### PostgreSQL Persistence

```mermaid
graph TD
    Agent[Agent Execution] --> Create[Create Project]
    Create --> Task[Create Task]
    Task --> Execute[Execute Workflow]
    Execute --> Decision{Human Decision}

    Decision -->|Any| Log[Log Decision]
    Log --> Cost[Track Costs]
    Cost --> Complete[Mark Complete]

    style Create fill:#4CAF50
    style Log fill:#2196F3
    style Cost fill:#FF9800
```

**Data Retention**:
- Projects: Permanent
- Tasks: Permanent (with completed_at timestamp)
- Decisions: Permanent (audit trail)
- Costs: Permanent (budget tracking)

---

## Technology Stack

### Core Framework
- **LangGraph**: State machine workflow orchestration
- **LangChain**: LLM integration and tooling
- **Anthropic Claude**: Sonnet 4.5 for code generation

### State Management
- **Redis**: In-memory caching (Docker container)
- **PostgreSQL**: Persistent storage (Docker container)
- **psycopg2**: PostgreSQL driver
- **redis-py**: Redis client

### CLI & UI
- **Typer**: CLI framework
- **Rich**: Terminal formatting and syntax highlighting
- **Click**: Command-line utilities

### Testing
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **unittest.mock**: Mocking utilities

### Development
- **Black**: Code formatting
- **Ruff**: Linting
- **Mypy**: Type checking
- **Docker Compose**: Service orchestration

---

## Design Patterns

### 1. State Machine Pattern (LangGraph)
- Nodes represent discrete processing steps
- Edges define flow between nodes
- Conditional routing based on state
- Immutable state updates (functional style)

### 2. Strategy Pattern (LLM Routing)
- Future: Route complex tasks to Claude
- Future: Route simple tasks to Gemini
- Cost-optimized model selection

### 3. Command Pattern (CLI)
- Each command is isolated
- Composable operations
- Clear separation of concerns

### 4. Repository Pattern (Database)
- Abstract data access
- Consistent interface
- Easy to test with mocks

---

## Performance Characteristics

### Benchmarks
- **Code Generation**: 5-10 seconds (typical)
- **Test Suite**: ~3 seconds (244 tests)
- **Workspace Creation**: <100ms
- **Git Commit**: <500ms
- **Database Write**: <50ms
- **Redis Cache**: <5ms

### Scalability
- **Current**: Single-threaded execution
- **Future**: Multi-agent parallel execution
- **Bottleneck**: LLM API calls (rate limited)
- **Optimization**: Response caching in Redis

---

## Security Considerations

### API Key Management
- Stored in `.env` file (gitignored)
- Never logged or exposed
- Environment variable isolation

### Workspace Isolation
- Path traversal protection
- Sandboxed to `/workspace` directory
- No access to parent directories

### Database Security
- Connection strings in environment
- No SQL injection (parameterized queries)
- Docker network isolation

### Git Operations
- No automatic push to remote
- Local commits only
- User controls remote operations

---

## Extension Points

### Adding New Agents
```python
class NewAgent:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(CustomState)
        workflow.add_node("step1", self._step1)
        workflow.add_node("step2", self._step2)
        # Define workflow...
        return workflow.compile()
```

### Adding New Tools
```python
class CustomTool:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def execute(self, params: dict) -> dict:
        # Tool implementation
        return result
```

### Custom LLM Integration
```python
class CustomLLMClient:
    def generate(self, messages: list, **kwargs) -> dict:
        # Implement LLM API call
        return {"content": "...", "usage": {...}}
```

---

## Future Architecture (Phase 2)

```mermaid
graph TB
    User[User] --> Orch[Orchestrator Agent]
    Orch --> FE[Frontend Agent]
    Orch --> BE[Backend Agent]
    Orch --> Test[Testing Agent]
    Orch --> Doc[Documentation Agent]

    FE --> React[React/Vue Generation]
    BE --> API[API Generation]
    Test --> Unit[Unit Tests]
    Test --> E2E[E2E Tests]
    Doc --> MD[Markdown Docs]

    style Orch fill:#4CAF50
    style FE fill:#61DAFB
    style BE fill:#FF9800
```

**Planned Enhancements**:
- Multi-agent orchestration
- Specialized agents per domain
- Inter-agent communication protocol
- Parallel execution
- Advanced cost optimization
- Multi-language support

---

**Last Updated**: 2025-10-11
**Version**: 0.1.0 (MVP)
