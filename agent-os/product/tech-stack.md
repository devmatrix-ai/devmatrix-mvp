# Tech Stack

Complete technical stack documentation for DevMatrix v0.5.0.

---

## Core Languages & Runtimes

### Backend
- **Python 3.12+** - Primary backend language for API, agents, and business logic
- **Poetry** - Python dependency management and packaging

### Frontend
- **TypeScript 5.x** - Type-safe JavaScript for React application
- **Node.js 20+** - JavaScript runtime for frontend build tooling
- **npm** - Frontend package management

---

## Backend Framework & API

### Web Framework
- **FastAPI 0.104+** - Modern async Python web framework for REST API
- **Uvicorn** - ASGI server for running FastAPI applications
- **Pydantic 2.x** - Data validation and settings management using Python type hints

### API Features
- **CORS Middleware** - Cross-origin resource sharing for frontend-backend communication
- **Request Validation** - Automatic request/response validation via Pydantic models
- **OpenAPI/Swagger** - Auto-generated API documentation

---

## Frontend Framework & UI

### Core Framework
- **React 18** - Component-based UI library with concurrent features
- **Vite 5.x** - Next-generation frontend build tool and dev server
- **React Router** - Client-side routing for single-page application

### Styling & UI
- **Tailwind CSS 3.x** - Utility-first CSS framework for responsive design
- **PostCSS** - CSS processing and transformation
- **Dark Mode Support** - System-wide dark theme with Tailwind dark mode classes

### UI Components
- **Markdown Rendering** - React Markdown for formatted message display
- **Syntax Highlighting** - Prism.js or Highlight.js for code blocks
- **Copy to Clipboard** - Browser clipboard API integration for code copying

---

## LLM & AI Framework

### AI Orchestration
- **LangGraph 0.2+** - State machine framework for building agentic workflows
- **LangChain 0.3+** - LLM application framework for chains and agents
- **LangChain Community** - Community-contributed integrations and tools

### LLM Provider
- **Anthropic Claude** - Primary LLM provider
  - **Claude Sonnet 4.5** - Primary model for code generation, conversation, and orchestration
  - **Claude Opus 4.1** - Advanced reasoning model for complex architectural decisions
- **Anthropic SDK** - Official Python SDK for Claude API integration

### AI Features
- **Prompt Caching** - Anthropic prompt caching for cost reduction on repeated context
- **Streaming Responses** - Real-time streaming of LLM outputs via WebSocket
- **Cost Tracking** - Token usage tracking and budget management (200 EUR/month)
- **Model Selection** - Dynamic model selection based on task complexity

---

## State Management & Databases

### Relational Database
- **PostgreSQL 16+** - Primary persistent database for conversations, users, and application data
- **SQLAlchemy 2.x** - Python SQL toolkit and ORM
- **Alembic** - Database migration tool for SQLAlchemy
- **psycopg2** - PostgreSQL adapter for Python

### In-Memory Store
- **Redis 7+** - In-memory data store for real-time workflow state and caching
- **redis-py** - Python Redis client

### Vector Database
- **ChromaDB** - Vector database for code embeddings and RAG (Retrieval-Augmented Generation)
- **Embeddings** - Code and documentation embeddings for semantic search

### Database Features
- **Connection Pooling** - SQLAlchemy connection pooling for performance
- **Async Database Access** - AsyncIO-compatible database operations
- **Migrations** - Alembic-based schema versioning and migration management

---

## Real-Time Communication

### WebSocket
- **python-socketio** - Python Socket.IO server implementation
- **python-engineio** - Engine.IO server (WebSocket transport layer)
- **socket.io-client** - JavaScript/TypeScript Socket.IO client for React

### Communication Features
- **Bidirectional Messaging** - Real-time client-server communication
- **Event-Based Protocol** - Structured event types for different message kinds
- **Automatic Reconnection** - Client-side reconnection logic on connection loss
- **Room Support** - Socket.IO rooms for user session isolation

---

## CLI & Terminal UI

### CLI Framework
- **Typer** - Modern Python CLI framework built on Click
- **Click** - Command-line interface creation kit (Typer dependency)

### Terminal UI
- **Rich** - Beautiful terminal formatting and progress bars
- **Rich Console** - Styled terminal output with colors and formatting
- **Rich Progress** - Progress bars and spinners for long-running operations

---

## Development Tools

### Code Quality
- **Black** - Uncompromising Python code formatter
- **Ruff** - Fast Python linter and code checker
- **MyPy** - Static type checker for Python
- **Pylint** - Python code analysis tool
- **isort** - Python import sorting

### Testing
- **pytest** - Python testing framework (244 tests, 92% coverage)
- **pytest-cov** - Coverage plugin for pytest
- **pytest-asyncio** - Pytest plugin for async test support
- **pytest-mock** - Mocking plugin for pytest

### Pre-commit Hooks
- **pre-commit** - Git hook framework for running checks before commits
- **Hooks Configuration** - Black, Ruff, MyPy, and test execution on commit

---

## Version Control & Git

### Git Integration
- **GitPython** - Python library for Git repository interaction
- **Git Automation** - Automatic commits after successful code generation
- **Conventional Commits** - LLM-generated commit messages following conventional commit format

### Git Features
- **Auto-staging** - Automatic staging of modified and new files
- **Commit Message Generation** - LLM-powered commit message creation
- **Branch Management** - Create and switch branches programmatically

---

## Containerization & Infrastructure

### Development Environment
- **Docker** - Container platform for local development
- **Docker Compose** - Multi-container orchestration for local services
- **Dockerfile** - Container definitions for backend and frontend

### Services
- **PostgreSQL Container** - Dockerized PostgreSQL 16 with persistent volumes
- **Redis Container** - Dockerized Redis 7 for state management
- **ChromaDB Container** - Dockerized vector database

---

## Build & Bundling

### Frontend Build
- **Vite** - Frontend build tool with HMR (Hot Module Replacement)
- **esbuild** - Fast JavaScript/TypeScript bundler (Vite dependency)
- **TypeScript Compiler** - Type checking and transpilation
- **Rollup** - Module bundler for production builds (Vite uses Rollup)

### Optimization
- **Code Splitting** - Automatic code splitting for optimal bundle sizes
- **Tree Shaking** - Dead code elimination in production builds
- **Asset Optimization** - Image and static asset optimization

---

## Configuration & Environment

### Configuration Management
- **python-dotenv** - Load environment variables from .env files
- **Pydantic Settings** - Type-safe configuration management
- **Environment Variables** - 12-factor app configuration pattern

### Configuration Files
- **.env** - Local environment configuration
- **.env.example** - Template for environment variables
- **pyproject.toml** - Python project configuration (Poetry, Black, Ruff, MyPy)
- **tsconfig.json** - TypeScript compiler configuration
- **vite.config.ts** - Vite build configuration
- **tailwind.config.js** - Tailwind CSS configuration

---

## Monitoring & Observability (Planned)

### Logging
- **Python logging** - Standard library logging with structured logs
- **Log Levels** - DEBUG, INFO, WARNING, ERROR, CRITICAL
- **JSON Logging** - Structured JSON logs for production (planned)

### Error Tracking (Planned - Phase 5)
- **Sentry** - Error tracking and performance monitoring
- **Exception Handling** - Global exception handlers with detailed error context

### Metrics (Planned - Phase 5)
- **Prometheus** - Metrics collection and storage
- **Grafana** - Metrics visualization and dashboards

---

## Security

### Authentication (Planned - Phase 6)
- **JWT** - JSON Web Tokens for stateless authentication
- **bcrypt** - Password hashing
- **OAuth 2.0** - Third-party authentication (GitHub, Google)

### API Security
- **HTTPS** - TLS/SSL encryption for all API traffic
- **CORS** - Cross-origin resource sharing configuration
- **Rate Limiting** - Request rate limiting (planned - Phase 6)

---

## CI/CD & Deployment (Planned - Phase 5)

### Continuous Integration
- **GitHub Actions** - Automated testing, linting, and type checking on pull requests

### Deployment Platforms
- **Backend Hosting** - Railway, Render, or AWS for backend deployment
- **Frontend Hosting** - Vercel or Netlify for React application
- **Managed Services** - PostgreSQL and Redis as managed cloud services

### Domain & SSL
- **Custom Domain** - Production domain with DNS configuration
- **SSL Certificates** - Automatic HTTPS via Let's Encrypt or platform-managed SSL

---

## Development Workflow

### Local Development
1. **Docker Compose Up** - Start PostgreSQL, Redis, ChromaDB containers
2. **Backend Dev Server** - `uvicorn src.api.app:app --reload` with hot reload
3. **Frontend Dev Server** - `npm run dev` with Vite HMR
4. **Database Migrations** - `alembic upgrade head` for schema updates

### Testing Workflow
1. **Run Tests** - `pytest` for backend unit and integration tests
2. **Coverage Report** - `pytest --cov=src` for coverage analysis
3. **Type Checking** - `mypy src` for static type validation
4. **Linting** - `ruff check src` for code quality

### Production Build
1. **Frontend Build** - `npm run build` creates optimized production bundle
2. **Type Check** - `tsc --noEmit` validates TypeScript types
3. **Backend Package** - Poetry build for Python distribution
4. **Container Build** - `docker build` for containerized deployment

---

## Version Information

- **Current Version**: v0.5.0
- **Python Version**: 3.12+
- **Node Version**: 20+
- **PostgreSQL Version**: 16+
- **Redis Version**: 7+
- **React Version**: 18
- **TypeScript Version**: 5.x
- **FastAPI Version**: 0.104+

---

## External Services & APIs

### Required Services
- **Anthropic API** - Claude LLM access (API key required)
- **PostgreSQL Database** - Relational database (local or managed)
- **Redis Instance** - In-memory store (local or managed)

### Optional Services (Planned)
- **Sentry** - Error tracking and monitoring
- **GitHub API** - GitHub integration for PR reviews and issue management
- **Slack API** - Team notifications and webhooks

---

## Cost Tracking & Budget

### LLM Budget
- **Monthly Budget**: 200 EUR/month for Claude API usage
- **Cost Tracking**: Token usage monitoring per request
- **Budget Alerts**: Warnings when approaching monthly limit

### Usage Metrics
- **Token Counting**: Input and output token tracking
- **Model Cost Tracking**: Per-model cost calculation (Sonnet vs Opus)
- **User Attribution**: Cost tracking per user (planned - Phase 6)
