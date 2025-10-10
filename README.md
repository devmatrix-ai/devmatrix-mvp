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

3. **Start services**
   ```bash
   # Start Docker services (PostgreSQL + Redis)
   docker compose up -d

   # Install Python dependencies
   pip install -r requirements.txt
   ```

4. **Run the agent**
   ```bash
   # CLI command (coming soon in Phase 1)
   python -m devmatrix.cli run "Create a fibonacci function"
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
- [ ] Docker Compose configuration
- [ ] LangGraph hello world
- [ ] State management (Redis + PostgreSQL)
- [ ] Basic file operation tools
- [ ] CLI interface

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
