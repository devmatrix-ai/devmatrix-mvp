# Devmatrix

**AI-Powered Autonomous Software Development System**

Devmatrix is an agentic AI system that generates production-ready code with human-in-the-loop oversight. Built with LangGraph and powered by Claude Sonnet 4.5, it combines intelligent code generation with adaptive autonomy control.

---

## 🎯 Project Status

**Version**: 0.4.0 (Production Ready!)
**Phase**: Phase 4 - Task Execution ✅ COMPLETE
**Progress**: Phase 0 ✅ | Phase 1 ✅ | Phase 2 ✅ | Phase 3 ✅ | Phase 4 ✅ (Days 1-70)
**Tests**: 244 passing | Coverage: 92% | E2E: ✅ Passing
**Current Focus**: Production deployment and polish
**Target**: ✅ ACHIEVED - Full autonomous development system working end-to-end! 🎉

---

## ✨ Features

### Core Capabilities
- ✅ **Conversational Web UI**: React-based chat interface for natural project discussions
- ✅ **Intelligent Orchestration**: Multi-agent system with specialized agents (Frontend, Backend, Testing, Documentation)
- ✅ **Task Execution System**: Dependency-aware task execution with topological sorting
- ✅ **Real-time Progress Streaming**: Live updates via WebSocket during orchestration
- ✅ **Context-Aware Intent Detection**: Smart routing between conversation and implementation modes
- ✅ **Markdown Rendering**: Syntax-highlighted code blocks with copy buttons
- ✅ **Dark Mode Support**: Light/Dark/System theme with persistent preferences
- ✅ **Keyboard Shortcuts**: Ctrl+K (focus), Ctrl+L (clear), Ctrl+N (new project)
- ✅ **Export Functionality**: Download conversations as Markdown files
- ✅ **Human-in-Loop Approval**: Interactive approval gates with feedback for regeneration
- ✅ **Self-Review System**: Automated code quality assessment (0-10 scoring)
- ✅ **Git Integration**: Automatic commits with LLM-generated conventional commit messages
- ✅ **Workspace Management**: Isolated workspace environments for safe code generation

### Technical Features
- ✅ **Multi-Agent System**: OrchestratorAgent coordinating specialized domain agents
- ✅ **LangGraph Workflows**: State machine orchestration with conditional routing
- ✅ **State Persistence**: Redis (realtime) + PostgreSQL (historical)
- ✅ **React 18 + TypeScript**: Modern web UI with Vite build system and Tailwind CSS
- ✅ **WebSocket Streaming**: Real-time bidirectional communication for agent interactions
- ✅ **Markdown Rendering**: Syntax highlighting and rich formatting for code responses
- ✅ **Cost Tracking**: Token usage and cost monitoring per task
- ✅ **CLI + Web Interface**: Rich terminal and conversational web interface
- ✅ **Comprehensive Testing**: 244 tests, 92% coverage, E2E validation
- ✅ **Production Ready**: Error handling, validation, and logging throughout

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         Web UI (React + TypeScript)                 │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ ChatWindow   │  │  MessageList   │  │  ChatInput           │  │
│  │ • Auto-focus │  │  • Markdown    │  │  • Command hints     │  │
│  │ • Nuevo btn  │  │  • Syntax hl.  │  │  • Smart autocomplete│  │
│  └──────┬───────┘  └────────┬───────┘  └──────────┬───────────┘  │
│         │                   │                      │               │
│         └───────────────────┴──────────────────────┘               │
│                             │                                       │
│                    ┌────────▼─────────┐                           │
│                    │ WebSocket Client │ (Socket.IO)               │
│                    │ • useChat hook   │                           │
│                    │ • Event routing  │                           │
│                    └────────┬─────────┘                           │
└─────────────────────────────┼─────────────────────────────────────┘
                              │ WebSocket (Socket.IO)
┌─────────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Server + python-socketio                │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                      ChatService                            │  │
│  │  • Intent Detection (conversational vs orchestration)       │  │
│  │  • Conversation Management                                  │  │
│  │  • Message History                                          │  │
│  └────────────────────┬────────────────────────────────────────┘  │
└───────────────────────┼───────────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
┌───────▼────────┐            ┌──────────▼───────────┐
│ Conversational │            │  OrchestratorAgent   │
│ Agent (LLM)    │            │                      │
│ • Spanish      │            │  Multi-Agent System  │
│ • Natural chat │            │  ┌─────────────────┐ │
│ • Q&A          │            │  │ Implementation  │ │
└────────────────┘            │  │ Testing         │ │
                              │  │ Documentation   │ │
                              │  │ Frontend        │ │
                              │  │ Backend         │ │
                              │  └─────────────────┘ │
                              │                      │
                              │  LangGraph Workflow  │
                              │  • Analyze Project   │
                              │  • Decompose Tasks   │
                              │  • Build Dependencies│
                              │  • Assign Agents     │
                              │  • Display Plan      │
                              └──────────┬───────────┘
                                         │
                                ┌────────┴─────────┐
                                │                  │
                        ┌───────▼────────┐  ┌─────▼──────────┐
                        │   Tools        │  │     State      │
                        │                │  │                │
                        │ • Files        │  │ • Redis Cache  │
                        │ • Git          │  │ • PostgreSQL   │
                        │ • Workspace    │  │ • Cost Tracking│
                        └────────────────┘  └────────────────┘
```

### Workflow Steps

#### Web UI Flow
1. **User Input**: Natural language project description via chat
2. **Intent Detection**: Classify as conversational (Q&A) or orchestration (implementation)
3. **Conversation Mode**: Answer questions, clarify requirements, guide user
4. **Orchestration Mode**: Decompose project into tasks and assign to specialized agents
5. **Real-time Updates**: Stream status and progress via WebSocket
6. **Markdown Rendering**: Display formatted responses with syntax-highlighted code

#### Orchestration Workflow
1. **Analyze Project**: Extract requirements, identify technology stack, assess complexity
2. **Decompose Tasks**: Break down into atomic, manageable tasks with clear ownership
3. **Build Dependency Graph**: Identify task dependencies for parallel execution
4. **Assign Agents**: Route tasks to specialized agents (Frontend, Backend, Testing, etc.)
5. **Display Plan**: Show comprehensive task breakdown to user
6. **Execute Tasks**: ✅ Coordinate agent execution with topological sorting and dependency awareness
7. **Stream Progress**: Real-time updates (phase_start, task_start, task_complete, etc.) via WebSocket
8. **Review & Commit**: Quality checks and Git integration
9. **Log & Track**: Record decisions, costs, and metrics to PostgreSQL

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-ai
   ```

2. **Setup environment**
   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env and add your Anthropic API key
   nano .env  # or use your preferred editor
   ```

3. **Install CLI utilities**
   ```bash
   # Install dvmtx command
   ./scripts/install-cli.sh
   ```

4. **Start services**
   ```bash
   # Start Docker services (PostgreSQL + Redis)
   dvmtx up

   # Check service health
   dvmtx status
   ```

5. **Install Python dependencies**
   ```bash
   # Install core dependencies
   pip install langchain langgraph langchain-anthropic rich typer python-dotenv
   ```

6. **Start the Web UI**
   ```bash
   # Start the API server (includes WebSocket)
   cd src/api
   python app.py

   # In another terminal, start the UI dev server
   cd src/ui
   npm run dev

   # Or use the production build
   cd src/ui
   npm run build  # Builds to ../api/static/
   # Then access at http://localhost:8000
   ```

7. **Try the CLI (Alternative Interface)**
   ```bash
   # Generate a simple function
   devmatrix generate "Create a function to calculate fibonacci numbers"

   # Generate with custom workspace
   devmatrix generate "Create a Calculator class" --workspace my-calc-project

   # Disable Git auto-commit
   devmatrix generate "Create a greeting function" --no-git
   ```

---

## 📖 Usage Examples

### Web UI Conversational Flow

Open the web UI at `http://localhost:8000` and start a conversation:

**Example 1: Simple Greeting**
```
User: Buenos dias
DevMatrix: ¡Hola! Soy DevMatrix, tu asistente para desarrollo de software.
          Puedo ayudarte a diseñar arquitecturas, planear proyectos, y
          orquestar la implementación con múltiples agentes especializados.
          ¿En qué puedo ayudarte hoy?
```

**Example 2: Design Discussion**
```
User: Podríamos diseñar una app de task manager?
DevMatrix: ¡Dale! Task manager suena bien. ¿Qué features principales necesitás?
          (autenticación, asignación de tareas, notificaciones, kanban, etc.)

User: Kanban, sprints, roles Dev/PO/Lead, colaboración
DevMatrix: Perfecto, ya tengo claro el scope. Cuando quieras arrancar con la
          implementación, decime "crear task manager con FastAPI, kanban,
          sprints y roles" y lo orquesto.
```

**Example 3: Direct Implementation Request**
```
User: Quiero hacer una API REST para gestión de usuarios con FastAPI,
      autenticación JWT y CRUD completo

DevMatrix: [Starts orchestration immediately]
          ## Orchestration Complete
          **Workspace**: `workspace_abc123`
          **Project Type**: backend_api
          **Complexity**: 7.2
          **Tasks**: 12

          ### Task Breakdown:
          - **task_1**: Project structure and dependencies
          - **task_2**: Database models and migrations (depends on: task_1)
          - **task_3**: JWT authentication middleware (depends on: task_1)
          ...
```

### CLI Code Generation

```bash
# Generate a simple function
devmatrix generate "Create a function to validate email addresses"
```

**What happens**:
1. Agent analyzes your request
2. Creates an implementation plan
3. Generates Python code with type hints and docstrings
4. Self-reviews the code (quality score)
5. Shows you the code with syntax highlighting
6. Asks for approval: `[approve/reject/modify]`
7. If approved: writes file + commits to Git

### Interactive Approval Flow

```
╭───────────────────────╮
│ Generated Code        │
│ Filename: validator.py│
│ Quality Score: 8.5/10 │
╰───────────────────────╯

  1 def validate_email(email: str) -> bool:
  2     """Validate email address format."""
  3     import re
  4     pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  5     return bool(re.match(pattern, email))

AI Review:
Score: 8.5/10
Feedback: Clean implementation with proper regex validation.

Action [approve/reject/modify]: approve

✓ Code approved!
✓ File written: /workspace/my-project/validator.py
✓ Git commit: a1b2c3d - feat: add email validation function
```

### Request Modifications

```
Action [approve/reject/modify]: modify
What would you like to modify?: Add error handling and support for internationalized emails

↻ Regenerating with feedback...

[Shows updated code with requested changes]
```

### Advanced Usage

```bash
# Generate with additional context
devmatrix generate "Create a REST API client" \
  --workspace api-project \
  --context '{"base_url": "https://api.example.com", "auth": "Bearer token"}'

# Planning mode (analysis + plan, no code generation)
devmatrix plan "Design a caching system with Redis"

# Workspace management
devmatrix workspace create my-new-project
devmatrix workspace list
devmatrix files list my-new-project

# Git operations
devmatrix git status my-new-project
```

---

## 📁 Project Structure

```
agentic-ai/
├── src/                      # Source code
│   ├── agents/              # Multi-agent system
│   │   ├── orchestrator_agent.py    # Main orchestrator
│   │   ├── implementation_agent.py  # Code implementation
│   │   ├── testing_agent.py         # Test generation
│   │   ├── documentation_agent.py   # Documentation
│   │   ├── frontend_agent.py        # React/Vue/Angular
│   │   └── backend_agent.py         # FastAPI/Django/Flask
│   ├── services/            # Business logic
│   │   ├── chat_service.py          # Conversational routing
│   │   └── agent_registry.py        # Agent management
│   ├── api/                 # FastAPI server
│   │   ├── app.py                   # Main server + WebSocket
│   │   ├── routes/                  # HTTP endpoints
│   │   └── static/                  # Built UI assets
│   ├── ui/                  # React Web UI
│   │   ├── src/
│   │   │   ├── components/chat/     # Chat components
│   │   │   ├── hooks/               # Custom hooks (useChat, useWebSocket)
│   │   │   └── services/            # WebSocket service
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── tools/               # MCP-compatible tools
│   ├── llm/                 # LLM integration & routing
│   ├── state/               # State management (Redis + PostgreSQL)
│   └── cli/                 # CLI interface
├── tests/                   # Unit & integration tests
├── docker/                  # Docker configuration
├── scripts/                 # Utility scripts
├── workspace/               # Agent workspace (gitignored)
├── DOCS/                    # Documentation
│   ├── ARCHITECTURE.md      # System architecture
│   ├── WORKPLAN.md          # Development roadmap
│   ├── WEB_UI.md            # Web UI documentation
│   └── PROJECT_MEMORY.md    # Decision log
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

---

## 🔐 Security

**IMPORTANT**: Never commit API keys or secrets!

- All secrets go in `.env` (gitignored)
- `.env.example` is a template only
- Agent workspace is sandboxed to `/workspace` by default
- All file operations are logged for audit

---

## 🔧 LangGraph Workflows

### Hello World Example

The `examples/hello_world.py` demonstrates the basic LangGraph workflow pattern:

```python
# State definition with TypedDict
class AgentState(TypedDict):
    user_request: str
    messages: Annotated[Sequence[dict], add]
    generated_code: str
    # ... more fields

# Agent node function
def hello_agent_node(state: AgentState) -> dict[str, Any]:
    # Process state and return updates
    return {"messages": [message], "current_task": "complete"}

# Create workflow
workflow = StateGraph(AgentState)
workflow.add_node("hello_agent", hello_agent_node)
workflow.set_entry_point("hello_agent")
workflow.add_edge("hello_agent", END)
app = workflow.compile()

# Execute
final_state = app.invoke(initial_state)
```

**Key concepts**:
- **State**: TypedDict passed between nodes
- **Nodes**: Functions that transform state
- **Edges**: Define workflow flow
- **Reducers**: Accumulate values (e.g., `add` for messages list)

---

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agents.py
```

### Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Format code
black src/ tests/
```

---

## 📊 Cost Management

**Budget**: €200/month

**Monitoring**:
- Alert at 75% budget usage
- Throttle at 90% budget usage
- Hard stop at 100%

**Optimization**:
- Claude Sonnet 4.5 for code generation (quality)
- Gemini 2.5 Flash for simple tasks (cost)
- Smart routing based on complexity

---

## 🗺️ Roadmap

### ✅ Phase 0: Foundation (Days 1-18) - COMPLETED
- [x] Git repository setup
- [x] Project structure
- [x] Security & secrets management
- [x] Docker Compose configuration (PostgreSQL + Redis + pgAdmin)
- [x] LangGraph hello world
- [x] CLI utilities (dvmtx command)
- [x] State management (Redis + PostgreSQL integration)
- [x] Basic file operation tools (WorkspaceManager, FileOperations, GitOperations)
- [x] CLI interface with Rich (13 commands)
- **Tests**: 166 passing, 93% coverage
- **Timeline**: Completed ahead of schedule!

### ✅ Phase 1: Single Agent POC (Days 19-40) - COMPLETED
- [x] **Days 1-4**: Planning & Code Generation Agent (LangGraph workflow)
- [x] **Days 5-8**: Analysis, Planning, Code Generation nodes
- [x] **Days 9-12**: Self-review and quality scoring
- [x] **Days 13-14**: Human approval flow with feedback loop
- [x] **Days 15-16**: Git integration with auto-commit
- [x] **Days 17-18**: Comprehensive E2E test suite
- [x] **Days 19-20**: Documentation and polish
- **Tests**: 244 passing, 92% coverage
- **Features**: Complete code generation workflow with Git integration
- **Status**: ✅ MVP COMPLETE - ahead of schedule!

### ✅ Phase 2: Multi-Agent System (Days 41-58) - COMPLETED
- [x] OrchestratorAgent with LangGraph workflow
- [x] Specialized agents (Implementation, Testing, Documentation, Frontend, Backend)
- [x] Agent registry for dynamic agent management
- [x] Task decomposition and dependency graph building
- [x] Agent assignment based on task requirements
- **Status**: ✅ Multi-agent orchestration system functional!

### ✅ Phase 3: Conversational Web UI (Days 59-63) - COMPLETED
- [x] **React 18 + TypeScript** web UI with Vite build system
- [x] **Real-time WebSocket** communication with Socket.IO
- [x] **Chat interface** with markdown rendering and syntax highlighting
- [x] **Intent detection** - smart routing between conversation and orchestration
- [x] **ChatService** - conversational agent and orchestration routing
- [x] **FastAPI integration** - WebSocket server with python-socketio
- [x] **Auto-focus & UX** - input focus, "Nuevo Proyecto" button
- [x] **Bug fixes** - Critical event listener lifecycle fix
- [x] **Documentation** - Complete WEB_UI.md documentation
- **Status**: ✅ Conversational UI fully functional!

### ✅ Phase 4: Task Execution (Days 64-70) - COMPLETED
- [x] **Execute Tasks Node** - Added execution to orchestrator workflow
- [x] **Dependency-Aware Execution** - Topological sort respects task dependencies
- [x] **Progress Streaming** - Real-time status updates via WebSocket
- [x] **Error Handling** - Graceful failure recovery per task
- [x] **Model Configuration** - Claude Opus 4.1 (reasoning) + Sonnet 4.5 (execution)
- [x] **Markdown Rendering** - Syntax highlighting with copy buttons
- [x] **Dark Mode Support** - Light/Dark/System theme persistence
- [x] **Keyboard Shortcuts** - Ctrl+K, Ctrl+L, Ctrl+N shortcuts
- [x] **Export Functionality** - Download conversations as Markdown
- [x] **E2E Testing** - Full orchestration flow validated
- **Status**: ✅ System fully functional end-to-end!

### 🚀 Phase 5: Production Deployment (Days 71+) - NEXT
- [ ] Docker compose production configuration
- [ ] Environment-based configuration (dev/staging/prod)
- [ ] Load testing and performance optimization
- [ ] Monitoring and observability (metrics, logs, traces)
- [ ] CI/CD pipeline setup
- [ ] User documentation and guides
- [ ] Deployment to production infrastructure

---

## 📚 Documentation

- [Architecture](DOCS/ARCHITECTURE.md) - Complete technical architecture
- [Work Plan](DOCS/WORKPLAN.md) - Detailed development roadmap with completed phases
- [Web UI](DOCS/WEB_UI.md) - Complete Web UI and chat system documentation
- [Features Completed](DOCS/FEATURES_COMPLETED.md) - Comprehensive list of implemented features
- [Frontend Roadmap](DOCS/FRONTEND_ROADMAP.md) - UI enhancement roadmap and implementation guide
- [Project Memory](DOCS/PROJECT_MEMORY.md) - Decision log and progress tracking

---

## 🤝 Contributing

This is currently a private development project. Contribution guidelines will be added in future phases.

---

## 📄 License

TBD - License to be determined

---

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration framework
- [Anthropic Claude](https://www.anthropic.com/) - LLM for code generation
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Rich](https://rich.readthedocs.io/) - Terminal UI library

---

## 📞 Contact

**Project Owner**: Ariel
**Lead Developer**: Dany (SuperClaude)
**Started**: 2025-10-10

---

**Last Updated**: 2025-10-16 (Phase 4 COMPLETE - Full Task Execution System! 🎉)
