# Devmatrix

**AI-Powered Autonomous Software Development System**

Devmatrix is an agentic AI system that generates production-ready code with human-in-the-loop oversight. Built with LangGraph and powered by Claude Sonnet 4.5, it combines intelligent code generation with adaptive autonomy control.

---

## 🎯 Project Status

**Version**: 0.1.0 (MVP in development)
**Phase**: Phase 0 - Foundation
**Target**: Single Agent POC (4 weeks)

---

## ✨ Features (Planned)

- ✅ **Intelligent Code Generation**: Python functions, modules, and projects
- ✅ **Human-in-Loop**: Approval gates with feedback for regeneration
- ✅ **Git Integration**: Automatic commits with descriptive messages
- ✅ **Cost-Optimized**: Smart LLM routing (Claude + Gemini)
- ✅ **State Persistence**: Redis (realtime) + PostgreSQL (history)
- ✅ **CLI Interface**: Rich terminal with progress bars and syntax highlighting

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│      Planning Agent (MVP)       │
│   - Analyze requirements        │
│   - Generate Python code        │
│   - Self-review & validation    │
│   - Human approval gates        │
│   LLM: Claude Sonnet 4.5        │
└────────────┬────────────────────┘
             │
    ┌────────┴─────────┐
    │                  │
┌───▼────┐      ┌─────▼──────┐
│ Tools  │      │   State    │
│        │      │            │
│ Files  │      │ Redis      │
│ Git    │      │ PostgreSQL │
└────────┘      └────────────┘
```

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

6. **Try the Hello World example**
   ```bash
   # Run basic LangGraph workflow
   python examples/hello_world.py

   # Or with custom request
   python examples/hello_world.py "Create a function to calculate factorial"
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

### ✅ Phase 0: Foundation (Weeks 1-2)
- [x] Git repository setup
- [x] Project structure
- [x] Security & secrets management
- [x] Docker Compose configuration
- [x] LangGraph hello world
- [x] CLI utilities (dvmtx command)
- [ ] State management (Redis + PostgreSQL integration)
- [ ] Basic file operation tools
- [ ] CLI interface with Rich

### 🔄 Phase 1: Single Agent POC (Weeks 3-4)
- [ ] Planning Agent implementation
- [ ] Human approval flow
- [ ] Git integration
- [ ] End-to-end tests
- [ ] Documentation

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

**Last Updated**: 2025-10-10
