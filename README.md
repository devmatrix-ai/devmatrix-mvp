# Devmatrix

**AI-Powered Autonomous Software Development System**

Devmatrix is an agentic AI system that generates production-ready code with human-in-the-loop oversight. Built with LangGraph and powered by Claude Sonnet 4.5, it combines intelligent code generation with adaptive autonomy control.

---

## 🎯 Project Status

**Version**: 0.1.0 (MVP Ready!)
**Phase**: Phase 1 - Single Agent POC ✅ COMPLETE
**Progress**: Phase 0 ✅ | Phase 1 ✅ Complete (Days 1-18)
**Tests**: 244 passing | Coverage: 92%
**Target**: MVP completed ahead of schedule! 🎉

---

## ✨ Features

### Core Capabilities
- ✅ **Intelligent Code Generation**: AI-powered Python code generation with Claude Sonnet 4.5
- ✅ **Human-in-Loop Approval**: Interactive approval gates with feedback for regeneration
- ✅ **Self-Review System**: Automated code quality assessment (0-10 scoring)
- ✅ **Git Integration**: Automatic commits with LLM-generated conventional commit messages
- ✅ **Feedback Loop**: Request modifications and regenerate code iteratively
- ✅ **Workspace Management**: Isolated workspace environments for safe code generation

### Technical Features
- ✅ **LangGraph Workflows**: State machine orchestration with conditional routing
- ✅ **State Persistence**: Redis (realtime) + PostgreSQL (historical)
- ✅ **Cost Tracking**: Token usage and cost monitoring per task
- ✅ **CLI Interface**: Rich terminal with syntax highlighting and progress indicators
- ✅ **Comprehensive Testing**: 244 tests, 92% coverage, E2E validation
- ✅ **Production Ready**: Error handling, validation, and logging throughout

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│         CodeGenerationAgent (LangGraph)          │
│                                                  │
│  ┌────────┐  ┌──────┐  ┌──────────┐  ┌───────┐ │
│  │Analyze │→ │ Plan │→ │ Generate │→ │Review │ │
│  └────────┘  └──────┘  └──────────┘  └───┬───┘ │
│                                           │     │
│  ┌──────────────────────────────────────┐│     │
│  │         Human Approval Gate           ││     │
│  │  • Approve  • Reject  • Modify       │←─────┘
│  └──────────┬───────────────────────────┘      │
│             │                                   │
│  ┌──────────▼─────┐    ┌──────────────┐       │
│  │  Write File    │ →  │  Git Commit  │       │
│  └────────────────┘    └──────────────┘       │
│                                                 │
│  LLM: Claude Sonnet 4.5 (10-step workflow)     │
└────────────┬────────────────────────────────────┘
             │
    ┌────────┴─────────┐
    │                  │
┌───▼────────┐  ┌─────▼──────────┐
│   Tools    │  │     State      │
│            │  │                │
│ • Files    │  │ • Redis Cache  │
│ • Git      │  │ • PostgreSQL   │
│ • Workspace│  │ • Cost Tracking│
└────────────┘  └────────────────┘
```

### Workflow Steps
1. **Analyze**: Extract requirements and determine filename
2. **Plan**: Create detailed implementation plan
3. **Generate**: Produce Python code with type hints and docstrings
4. **Review**: Self-assess code quality (0-10 score)
5. **Approval**: Human decision (approve/reject/modify)
6. **Write**: Save approved code to workspace
7. **Commit**: Auto-commit to Git with conventional message
8. **Log**: Record decision and metadata to PostgreSQL

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

6. **Try the Code Generation Agent**
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

### Basic Code Generation

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
│   ├── agents/              # Agent implementations
│   ├── tools/               # MCP-compatible tools
│   ├── llm/                 # LLM integration & routing
│   ├── state/               # State management
│   └── cli/                 # CLI interface
├── tests/                   # Unit & integration tests
├── docker/                  # Docker configuration
├── scripts/                 # Utility scripts
├── workspace/               # Agent workspace (gitignored)
├── DOCS/                    # Documentation
│   ├── devmatrix-architecture-2025.md
│   ├── WORKPLAN.md
│   └── PROJECT_MEMORY.md
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

### ✅ Phase 0: Foundation (Weeks 1-2) - COMPLETED
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

### ✅ Phase 1: Single Agent POC (Weeks 3-4) - COMPLETED
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

### 📅 Phase 2: Multi-Agent System (Future)
- [ ] Orchestrator agent
- [ ] Specialized agents (Frontend, Backend, Testing)
- [ ] Inter-agent communication
- [ ] Parallel execution

---

## 📚 Documentation

- [Architecture Specification](DOCS/devmatrix-architecture-2025.md) - Complete technical architecture
- [Work Plan](DOCS/WORKPLAN.md) - Detailed 4-week development plan
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

**Last Updated**: 2025-10-11 (Phase 1 COMPLETE - MVP Ready! 🎉)
