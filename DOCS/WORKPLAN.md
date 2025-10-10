# Devmatrix - Plan de Trabajo MVP

**Versión**: 1.0
**Fecha inicio**: 2025-10-10
**Fecha target**: 2025-11-07 (4 semanas)
**Owner**: Ariel + Dany

---

## 🎯 Objetivo del MVP

Construir un **Single Agent POC** que genere código Python simple con human-in-loop, validando la arquitectura base de Devmatrix.

**Success Criteria:**
- ✅ Agent genera funciones Python correctas
- ✅ Código es válido y ejecutable
- ✅ Human puede aprobar/rechazar en CLI
- ✅ State persiste en Redis
- ✅ Git integration básico funciona
- ✅ Docker Compose funcional

---

## 📅 Timeline General

```
Week 1-2: Phase 0 - Foundation
Week 3-4: Phase 1 - Single Agent POC
```

---

## 🏗️ PHASE 0: FOUNDATION (Weeks 1-2)

**Objetivo**: Setup completo de infraestructura y environment

### Week 1: Infrastructure Setup

#### Day 1-2: Project Structure & Git Setup
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 4-6 hours

**Tasks:**
- [ ] Inicializar repositorio Git
- [ ] Crear estructura de directorios
  ```
  devmatrix/
  ├── src/
  │   ├── agents/          # Agent implementations
  │   ├── tools/           # MCP tools
  │   ├── llm/             # LLM integration & routing
  │   ├── state/           # State management
  │   └── cli/             # CLI interface
  ├── tests/
  ├── docs/
  ├── docker/
  ├── scripts/
  ├── .env.example
  ├── requirements.txt
  ├── pyproject.toml
  └── README.md
  ```
- [ ] Setup .gitignore (Python, Docker, env files)
- [ ] Create README.md inicial
- [ ] Setup branch protection (main branch)

**Deliverables:**
- ✅ Repositorio Git funcional
- ✅ Estructura de directorios clara
- ✅ README con instrucciones básicas

---

#### Day 3-4: Docker Compose & Dependencies
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 6-8 hours

**Tasks:**
- [ ] Docker Compose configuration
  - FastAPI service
  - PostgreSQL (con pgvector extension)
  - Redis
  - (Optional) Celery worker
- [ ] requirements.txt con dependencies:
  ```
  fastapi==0.115.0
  uvicorn[standard]==0.30.0
  langchain==0.3.0
  langgraph==0.2.0
  langchain-anthropic==0.2.0
  langchain-openai==0.2.0
  langchain-google-genai==2.0.0
  redis==5.1.0
  psycopg2-binary==2.9.9
  sqlalchemy==2.0.35
  pydantic==2.9.0
  pydantic-settings==2.5.0
  python-dotenv==1.0.1
  rich==13.8.0
  typer==0.12.0
  pytest==8.3.0
  pytest-asyncio==0.24.0
  ```
- [ ] .env.example con variables:
  ```
  # LLM API Keys
  ANTHROPIC_API_KEY=your_key_here
  OPENAI_API_KEY=your_key_here
  GOOGLE_API_KEY=your_key_here

  # Database
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
  POSTGRES_DB=devmatrix
  POSTGRES_USER=devmatrix
  POSTGRES_PASSWORD=devmatrix

  # Redis
  REDIS_HOST=localhost
  REDIS_PORT=6379

  # App Config
  ENVIRONMENT=development
  LOG_LEVEL=INFO
  ```
- [ ] Verificar `docker compose up` funciona
- [ ] Health checks para todos los servicios

**Deliverables:**
- ✅ Docker Compose funcional
- ✅ Todos los servicios levantan correctamente
- ✅ Dependencies instaladas

**Blockers potenciales:**
- ⚠️ Versiones de dependencias incompatibles
- ⚠️ pgvector extension no disponible en Postgres image

---

#### Day 5: LangGraph Hello World
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 4-6 hours

**Tasks:**
- [ ] Implementar LangGraph básico
- [ ] Single node graph que responde "Hello World"
- [ ] State management mínimo
- [ ] Test de conexión LLM (Claude Sonnet 4.5)
- [ ] CLI básico para ejecutar el agent

**Code Structure:**
```python
# src/agents/base.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated

class AgentState(TypedDict):
    messages: list[str]
    current_task: str
    status: str

def hello_world_node(state: AgentState):
    """Simple hello world node"""
    return {"messages": ["Hello World from Devmatrix!"]}

# Create graph
workflow = StateGraph(AgentState)
workflow.add_node("hello", hello_world_node)
workflow.set_entry_point("hello")
workflow.add_edge("hello", END)

app = workflow.compile()
```

**Deliverables:**
- ✅ LangGraph funcional
- ✅ Test ejecuta y retorna respuesta
- ✅ State se mantiene durante ejecución

---

### Week 2: Core Components

#### Day 6-7: State Management (Redis + PostgreSQL)
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 6-8 hours

**Tasks:**
- [ ] Implementar StateManager class
- [ ] Redis para state temporal (workflow activo)
- [ ] PostgreSQL para state persistente (project history)
- [ ] Schema inicial:
  ```sql
  CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
  );

  CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    agent_name VARCHAR(100),
    task_type VARCHAR(100),
    input TEXT,
    output TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP,
    completed_at TIMESTAMP
  );

  CREATE TABLE agent_decisions (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    decision_type VARCHAR(100),
    reasoning TEXT,
    approved BOOLEAN,
    created_at TIMESTAMP
  );
  ```
- [ ] SQLAlchemy models
- [ ] Redis TTL para workflow state (30 min)
- [ ] Tests de persistencia

**Deliverables:**
- ✅ StateManager funcional
- ✅ Redis + PostgreSQL integrados
- ✅ Tests pasan

---

#### Day 8-9: Basic Tools (File Operations)
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 6-8 hours

**Tasks:**
- [ ] Implementar MCP-compatible tools:
  - `read_file(path: str) -> str`
  - `write_file(path: str, content: str) -> bool`
  - `list_directory(path: str) -> list[str]`
  - `create_directory(path: str) -> bool`
- [ ] Sandboxing: whitelist de directorios permitidos
- [ ] Error handling robusto
- [ ] Logging de todas las operaciones
- [ ] Tests unitarios

**Security Considerations:**
```python
ALLOWED_PATHS = [
    "/workspace",
    "/tmp/devmatrix"
]

def is_path_allowed(path: str) -> bool:
    """Verify path is within allowed directories"""
    resolved = Path(path).resolve()
    return any(
        resolved.is_relative_to(allowed)
        for allowed in ALLOWED_PATHS
    )
```

**Deliverables:**
- ✅ Tools funcionan correctamente
- ✅ Sandboxing efectivo
- ✅ Tests de seguridad pasan

---

#### Day 10: CLI Interface (Rich)
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 4-6 hours

**Tasks:**
- [ ] Implementar CLI con Typer + Rich
- [ ] Comandos básicos:
  - `devmatrix init` - Inicializar proyecto
  - `devmatrix run` - Ejecutar agent
  - `devmatrix status` - Ver estado actual
- [ ] Progress bars para operaciones largas
- [ ] Syntax highlighting para código
- [ ] Interactive prompts para approval gates

**Example CLI:**
```python
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer()
console = Console()

@app.command()
def run(task: str):
    """Run agent with specified task"""
    console.print(f"[bold blue]Starting Devmatrix...[/bold blue]")

    with Progress() as progress:
        task_progress = progress.add_task(
            "[green]Processing...",
            total=100
        )
        # Execute agent
        # Update progress

    console.print("[bold green]✓ Task completed![/bold green]")
```

**Deliverables:**
- ✅ CLI funcional y user-friendly
- ✅ Progress indicators claros
- ✅ Interactive approval gates

---

## 🤖 PHASE 1: SINGLE AGENT POC (Weeks 3-4)

**Objetivo**: Agent funcional que genera código Python con human-in-loop

### Week 3: Agent Implementation

#### Day 11-12: Planning Agent Core
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 8-10 hours

**Tasks:**
- [ ] Implementar Planning Agent con LangGraph
- [ ] System prompt optimizado:
  ```
  You are a Python code generation expert. Your task is to:
  1. Understand user requirements clearly
  2. Generate clean, well-documented Python code
  3. Include error handling and type hints
  4. Write code that follows PEP 8 standards

  You have access to the following tools:
  - read_file: Read existing files
  - write_file: Write new code files
  - list_directory: Explore directory structure
  ```
- [ ] Multi-step reasoning flow:
  1. Analyze requirement
  2. Plan implementation
  3. Generate code
  4. Self-review
  5. Present for approval
- [ ] LLM integration (Claude Sonnet 4.5)
- [ ] Tool calling integration
- [ ] Error handling y retries

**Graph Structure:**
```python
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("analyze", analyze_requirement)
workflow.add_node("plan", create_plan)
workflow.add_node("generate", generate_code)
workflow.add_node("review", self_review)
workflow.add_node("approval", human_approval)

# Edges
workflow.set_entry_point("analyze")
workflow.add_edge("analyze", "plan")
workflow.add_edge("plan", "generate")
workflow.add_edge("generate", "review")
workflow.add_edge("review", "approval")

# Conditional edge based on approval
workflow.add_conditional_edges(
    "approval",
    should_regenerate,
    {
        "regenerate": "generate",
        "accept": END,
        "reject": END
    }
)
```

**Deliverables:**
- ✅ Planning Agent funcional
- ✅ Multi-step reasoning works
- ✅ Tool calls exitosos

---

#### Day 13-14: Human-in-Loop Approval
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 6-8 hours

**Tasks:**
- [ ] Implementar approval gate mechanism
- [ ] CLI prompt para mostrar código generado
- [ ] Opciones: Approve / Reject / Modify
- [ ] Si Reject: permitir feedback para regenerar
- [ ] Si Approve: escribir código a filesystem
- [ ] Logging de decisiones en PostgreSQL

**Approval Flow:**
```python
def human_approval(state: AgentState) -> AgentState:
    """Present generated code for human approval"""
    console.print("\n[bold]Generated Code:[/bold]")
    syntax = Syntax(state["generated_code"], "python")
    console.print(syntax)

    action = Prompt.ask(
        "Action",
        choices=["approve", "reject", "modify"],
        default="approve"
    )

    if action == "approve":
        # Write to file
        write_file(state["target_path"], state["generated_code"])
        state["status"] = "approved"
    elif action == "reject":
        state["status"] = "rejected"
    else:
        feedback = Prompt.ask("What would you like to modify?")
        state["feedback"] = feedback
        state["status"] = "needs_modification"

    return state
```

**Deliverables:**
- ✅ Approval gate funcional
- ✅ Feedback loop works
- ✅ Decisions logged

---

#### Day 15-16: Git Integration
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 4-6 hours

**Tasks:**
- [ ] Implementar Git tools:
  - `git_init(path: str)` - Initialize repo
  - `git_add(files: list[str])` - Stage files
  - `git_commit(message: str)` - Create commit
  - `git_status()` - Check status
- [ ] Auto-commit después de approval
- [ ] Commit messages automáticos descriptivos
- [ ] Git history tracking en PostgreSQL

**Example Git Integration:**
```python
from git import Repo

def git_commit_changes(files: list[str], message: str):
    """Commit changes with descriptive message"""
    repo = Repo("/workspace")

    # Stage files
    repo.index.add(files)

    # Commit
    commit = repo.index.commit(message)

    # Log to DB
    log_git_commit(
        commit_hash=commit.hexsha,
        message=message,
        files=files
    )

    return commit.hexsha
```

**Deliverables:**
- ✅ Git integration funcional
- ✅ Auto-commits work
- ✅ History tracked

---

### Week 4: Testing & Polish

#### Day 17-18: End-to-End Tests
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 6-8 hours

**Tasks:**
- [ ] E2E test scenarios:
  1. Generate simple function (fibonacci)
  2. Generate class with methods
  3. Generate module with multiple functions
  4. Handle rejection and regeneration
  5. Git commit verification
- [ ] Integration tests (Redis + PostgreSQL)
- [ ] Tool tests (file operations)
- [ ] CLI tests (interactive flows)
- [ ] Performance tests (response times)

**Test Coverage Target**: >80%

**Example E2E Test:**
```python
@pytest.mark.asyncio
async def test_generate_fibonacci():
    """Test generating fibonacci function"""
    # Initialize agent
    agent = PlanningAgent()

    # Run task
    result = await agent.run(
        task="Create a Python function to calculate fibonacci numbers"
    )

    # Verify code generated
    assert result["status"] == "completed"
    assert "def fibonacci" in result["generated_code"]
    assert result["file_written"] is True

    # Verify git commit
    assert result["git_commit_hash"] is not None
```

**Deliverables:**
- ✅ E2E tests pass
- ✅ Coverage >80%
- ✅ Performance acceptable (<10s per task)

---

#### Day 19-20: Documentation & Polish
**Status**: 🔴 Not Started
**Owner**: Dany
**Effort**: 4-6 hours

**Tasks:**
- [ ] README.md completo con:
  - Installation instructions
  - Quick start guide
  - Example usage
  - Architecture overview
  - Troubleshooting
- [ ] API documentation (FastAPI auto-docs)
- [ ] Code comments y docstrings
- [ ] Architecture diagram (mermaid)
- [ ] Demo video (opcional)
- [ ] CHANGELOG.md

**Deliverables:**
- ✅ Documentation completa
- ✅ Easy onboarding para nuevos devs
- ✅ Clear architecture understanding

---

## 📊 Success Metrics

### MVP Success Criteria
- [ ] Agent genera código Python correcto (>90% accuracy)
- [ ] Human approval flow funciona sin bugs
- [ ] State persiste correctamente (Redis + PostgreSQL)
- [ ] Git integration funcional
- [ ] Tests pasan (>80% coverage)
- [ ] Docker Compose levanta en <2 min
- [ ] CLI es intuitivo y user-friendly
- [ ] Documentation clara y completa

### Performance Targets
- Task completion time: <10 seconds (simple function)
- LLM response time: <5 seconds
- Docker startup: <2 minutes
- Test suite: <30 seconds

### Quality Targets
- Code quality: Pylint score >8.0
- Type coverage: >90% (mypy)
- Test coverage: >80%
- Zero critical security issues

---

## 🚧 Risks & Mitigation

### Technical Risks

**Risk 1: LLM API rate limits**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Implement caching para requests similares
  - Exponential backoff en retries
  - Fallback a modelos alternativos

**Risk 2: State management complexity**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Start simple, add complexity gradual
  - Extensive tests de state transitions
  - Clear state schema documentation

**Risk 3: LangGraph learning curve**
- **Probability**: High
- **Impact**: Medium
- **Mitigation**:
  - Start con examples simples
  - Incremental complexity
  - LangSmith para debugging

**Risk 4: Budget overrun (€200/mes)**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Real-time cost tracking
  - Alertas at 75% budget
  - Smart model routing (Gemini Flash para simple tasks)

### Schedule Risks

**Risk 1: Underestimated complexity**
- **Probability**: High
- **Impact**: High
- **Mitigation**:
  - Buffer time en cada phase (20%)
  - Clear scope definition
  - Cut non-essential features si needed

**Risk 2: Dependency issues**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Lock versions en requirements.txt
  - Test dependency compatibility early
  - Maintain alternative dependencies list

---

## 📦 Deliverables Checklist

### Phase 0 Deliverables
- [ ] Git repository inicializado
- [ ] Docker Compose funcional
- [ ] Requirements.txt completo
- [ ] .env.example configurado
- [ ] LangGraph hello world funciona
- [ ] StateManager implementado
- [ ] File operation tools funcionan
- [ ] CLI básico implementado

### Phase 1 Deliverables
- [ ] Planning Agent funcional
- [ ] Human approval flow working
- [ ] Git integration completa
- [ ] E2E tests passing (>80% coverage)
- [ ] Documentation completa
- [ ] README con quick start
- [ ] Demo funcional

---

## 🔄 Weekly Reviews

### Week 1 Review (2025-10-17)
**Status**: 🔴 Not Started
**Completed**: -
**Blockers**: -
**Next Week Focus**: -

### Week 2 Review (2025-10-24)
**Status**: 🔴 Not Started
**Completed**: -
**Blockers**: -
**Next Week Focus**: -

### Week 3 Review (2025-10-31)
**Status**: 🔴 Not Started
**Completed**: -
**Blockers**: -
**Next Week Focus**: -

### Week 4 Review (2025-11-07)
**Status**: 🔴 Not Started
**Completed**: -
**Blockers**: -
**Next Steps**: Phase 2 planning

---

## 📚 Resources

### Documentation
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangSmith](https://docs.smith.langchain.com/)
- [Claude API Docs](https://docs.anthropic.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

### Examples & Templates
- LangGraph examples: https://github.com/langchain-ai/langgraph/tree/main/examples
- Agent patterns: https://python.langchain.com/docs/modules/agents/

### Tools
- Rich CLI: https://rich.readthedocs.io/
- Typer: https://typer.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/

---

## 🎯 Next Phase Preview

### Phase 2: Multi-Agent System (Weeks 5-8)
**Scope**:
- Orchestrator agent
- Implementation Agent
- Testing Agent
- Inter-agent communication
- Parallel execution

**Success Criteria**:
- 3 agents colaborando
- Task decomposition automática
- Testing agent valida código
- Proyectos más complejos (múltiples archivos)

---

**Última actualización**: 2025-10-10
**Próxima revisión**: 2025-10-17 (Weekly Review)
