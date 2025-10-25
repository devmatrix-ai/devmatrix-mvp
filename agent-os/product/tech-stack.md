# Tech Stack: DevMatrix MVP Security & Performance Remediation

Complete technical stack documentation for the DevMatrix MVP remediation project, including existing technologies and new additions for security, performance, reliability, and observability.

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
- **CORS Middleware** - Strict origin whitelisting (replacing wildcard configuration)
- **Request Validation** - Automatic request/response validation via Pydantic models
- **OpenAPI/Swagger** - Auto-generated API documentation
- **Rate Limiting Middleware** - New: Redis-backed rate limiting per-IP and per-user

---

## Frontend Framework & UI

### Core Framework
- **React 18** - Component-based UI library with concurrent features
- **Vite 5.x** - Next-generation frontend build tool and dev server
- **React Router** - Client-side routing for single-page application

### Styling & UI
- **Material-UI v7** - Comprehensive React component library (migrated from Tailwind CSS)
- **Emotion** - CSS-in-JS styling solution (Material-UI dependency)
- **PostCSS** - CSS processing and transformation
- **Dark Mode Support** - Material-UI theme with light/dark mode toggle

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
- **Error Handling** - New: Comprehensive retry logic, circuit breaker pattern, fallback responses

---

## State Management & Databases

### Relational Database
- **PostgreSQL 16+** - Primary persistent database for conversations, users, and application data
- **SQLAlchemy 2.x** - Python SQL toolkit and ORM
- **Alembic** - Database migration tool for SQLAlchemy
- **psycopg2** - PostgreSQL adapter for Python

### In-Memory Store
- **Redis 7+** - In-memory data store for real-time workflow state, caching, and rate limiting
- **redis-py** - Python Redis client
- **New Redis Use Cases**:
  - Token blacklist for logout functionality
  - Distributed rate limiting counters
  - Query result caching
  - Session data caching

### Vector Database
- **ChromaDB** - Vector database for code embeddings and RAG (Retrieval-Augmented Generation)
- **Embeddings** - Code and documentation embeddings for semantic search

### Database Features
- **Connection Pooling** - New: Configured SQLAlchemy pool (size: 20, max_overflow: 10)
- **Async Database Access** - AsyncIO-compatible database operations
- **Migrations** - Alembic-based schema versioning and migration management
- **Query Optimization** - New: Eager loading, strategic indexes, query caching
- **Transaction Management** - New: Timeout guards, deadlock detection, retry logic

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
- **Memory Leak Prevention** - New: Proper connection cleanup, idle timeout, stale connection removal

---

## Security & Authentication

### Authentication (New in Remediation)
- **JWT (JSON Web Tokens)** - Token-based authentication with environment-managed secrets
- **PyJWT** - Python library for encoding/decoding JWT tokens
- **Token Blacklist** - Redis-backed token invalidation on logout
- **Token Rotation** - Refresh token rotation for enhanced security

### Input Validation & Sanitization
- **Pydantic** - Schema validation on all request inputs
- **Bleach** - HTML sanitization to prevent XSS attacks
- **SQLAlchemy Parameterized Queries** - SQL injection prevention

### Security Headers
- **Content Security Policy (CSP)** - Prevent XSS and injection attacks
- **X-Content-Type-Options** - Prevent MIME-sniffing
- **X-Frame-Options** - Clickjacking protection
- **X-XSS-Protection** - Browser XSS filter enablement

### Rate Limiting
- **slowapi** - Rate limiting library for FastAPI
- **Redis** - Distributed rate limit counter storage
- **Configuration**:
  - Per-IP limits: 100 requests/minute
  - Per-user limits: 1000 requests/hour
  - Configurable limits per endpoint

### Audit Logging
- **PostgreSQL audit_logs table** - Comprehensive security event logging
- **Logged Events**: Authentication, authorization, data access, data modifications
- **Audit Fields**: User ID, action, resource, timestamp, IP address, user agent

---

## Monitoring & Observability (New in Remediation)

### Metrics
- **Prometheus** - Time-series metrics collection and storage
- **prometheus_client** - Python Prometheus client library
- **Metrics Tracked**:
  - Request duration (histogram)
  - Request count (counter)
  - Error rate (counter)
  - LLM API latency and cost
  - Database query performance
  - WebSocket connections (gauge)
  - Cache hit rate

### Error Tracking
- **Sentry** - Real-time error tracking and monitoring
- **sentry-sdk** - Python Sentry SDK with FastAPI integration
- **Features**:
  - Error grouping and deduplication
  - Release tracking
  - User context in error reports
  - Breadcrumbs for debugging
  - Performance monitoring

### Logging
- **Python logging** - Standard library logging
- **structlog** - Structured JSON logging for production
- **Features**:
  - Correlation IDs for request tracing
  - Structured log fields (timestamp, level, user_id, endpoint, latency)
  - Log levels per environment (DEBUG in dev, INFO in prod)
  - Log aggregation integration (CloudWatch Logs, Datadog)

### Distributed Tracing
- **OpenTelemetry** - Vendor-neutral observability framework
- **opentelemetry-api** - OpenTelemetry Python API
- **opentelemetry-instrumentation-fastapi** - FastAPI auto-instrumentation
- **Jaeger or Zipkin** - Distributed tracing backend
- **Traced Operations**:
  - HTTP requests
  - Database queries
  - Redis operations
  - LLM API calls
  - WebSocket messages

### Dashboards
- **Grafana** - Metrics visualization and dashboards
- **Dashboard Panels**:
  - Request rate and latency (p50, p95, p99)
  - Error rate by endpoint
  - LLM API cost tracking
  - Database connection pool utilization
  - Cache hit rate
  - WebSocket active connections

---

## Performance Optimization (New in Remediation)

### Caching
- **Redis** - Distributed caching layer
- **Cache Strategy**:
  - Conversations: 5-minute TTL
  - Messages: 1-minute TTL
  - Query results: 10-minute TTL
  - LLM responses: Semantic caching
- **Cache Invalidation**: Write-through on updates

### Database Optimization
- **Strategic Indexes**:
  - `conversations.owner_id` (authorization queries)
  - `messages.conversation_id` (message retrieval)
  - `(owner_id, created_at)` composite (sorted queries)
  - `tokens.jti` (blacklist lookup)
- **Query Optimization**:
  - Eager loading (.joinedload(), .selectinload())
  - Batch loading of related entities
  - Query result caching
  - EXPLAIN analysis for slow queries

### Load Testing
- **Locust** - Python-based load testing framework
- **k6** - JavaScript-based load testing tool (alternative)
- **Test Scenarios**:
  - 100 concurrent users on conversation list
  - 50 concurrent writes on message creation
  - 200 concurrent WebSocket connections
  - 1-hour sustained load test

### Profiling
- **cProfile** - Python built-in profiler
- **py-spy** - Sampling profiler for production
- **memory_profiler** - Memory usage profiling
- **asyncio profiling** - Event loop blocking detection

---

## Reliability & Resilience (New in Remediation)

### Circuit Breaker
- **pybreaker** - Circuit breaker pattern implementation
- **Configuration**:
  - 5 failures trigger circuit open
  - 60-second cooldown before retry
  - Fallback responses when open

### Retry Logic
- **tenacity** - Retry library with exponential backoff
- **Retry Configuration**:
  - LLM API calls: 3 attempts, exponential backoff (1s, 2s, 4s)
  - Database connections: 5 attempts, exponential backoff
  - Redis connections: 3 attempts, exponential backoff

### Health Checks
- **Custom /health endpoints**:
  - `/health` - Basic health check
  - `/health/ready` - Readiness probe (checks all dependencies)
  - `/health/live` - Liveness probe (process alive)
- **Dependency Checks**:
  - PostgreSQL connectivity
  - Redis connectivity
  - ChromaDB availability
  - LLM API reachability

### Graceful Degradation
- **Redis Failure**: Bypass rate limiting, continue operation
- **ChromaDB Failure**: Disable RAG, continue with basic chat
- **LLM API Failure**: Return cached response or error message

---

## Testing

### Backend Testing
- **pytest** - Python testing framework
- **pytest-cov** - Coverage plugin for pytest
- **pytest-asyncio** - Pytest plugin for async test support
- **pytest-mock** - Mocking plugin for pytest
- **New Test Categories**:
  - Security tests (rate limiting, authorization, SQL injection)
  - Performance tests (load testing, memory leak detection)
  - Integration tests (end-to-end workflows)
  - Chaos tests (failure injection, resilience)

### Frontend Testing
- **Vitest** - Unit testing framework for Vite projects
- **React Testing Library** - Testing utilities for React components
- **Mock Service Worker (MSW)** - API mocking for tests

### Load Testing
- **Locust** - Distributed load testing framework
- **k6** - Modern load testing tool

### Security Testing
- **bandit** - Python security linter
- **safety** - Dependency vulnerability scanner
- **OWASP ZAP** - Penetration testing tool (manual testing)

### Test Coverage Target
- **Current**: 244 tests, 92% coverage
- **Remediation Goal**: 300+ tests, 95% coverage
- **Coverage Requirements**: All new code must have 90%+ coverage

---

## Development Tools

### Code Quality
- **Black** - Uncompromising Python code formatter
- **Ruff** - Fast Python linter and code checker
- **MyPy** - Static type checker for Python (strict mode enabled)
- **Pylint** - Python code analysis tool
- **isort** - Python import sorting

### Pre-commit Hooks
- **pre-commit** - Git hook framework for running checks before commits
- **Hooks Configuration**:
  - Black formatting
  - Ruff linting
  - MyPy type checking
  - Unit test execution
  - Security scanning (bandit)

### Static Analysis
- **SonarQube** - Continuous code quality inspection (optional)
- **CodeClimate** - Automated code review (optional)

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
- **Redis Container** - Dockerized Redis 7 for state management and caching
- **ChromaDB Container** - Dockerized vector database
- **Prometheus Container** - New: Metrics collection and storage
- **Grafana Container** - New: Metrics visualization

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
- **Pydantic Settings** - New: Type-safe configuration management with validation
- **Environment Variables** - 12-factor app configuration pattern

### Required Environment Variables (New in Remediation)
- **DATABASE_URL** - PostgreSQL connection string (validated on startup)
- **REDIS_URL** - Redis connection string (validated on startup)
- **JWT_SECRET** - JWT signing key (no hardcoded defaults, required)
- **JWT_ALGORITHM** - JWT algorithm (default: HS256)
- **JWT_EXPIRATION_MINUTES** - Token TTL (default: 60)
- **CORS_ORIGINS** - Comma-separated allowed origins (no wildcard)
- **RATE_LIMIT_PER_MINUTE** - Per-IP rate limit (default: 100)
- **RATE_LIMIT_PER_HOUR** - Per-user rate limit (default: 1000)
- **ANTHROPIC_API_KEY** - Claude API key
- **SENTRY_DSN** - Sentry error tracking DSN (optional)
- **ENVIRONMENT** - Environment name (dev, staging, prod)

### Configuration Files
- **.env** - Local environment configuration
- **.env.example** - Template for environment variables
- **pyproject.toml** - Python project configuration (Poetry, Black, Ruff, MyPy)
- **tsconfig.json** - TypeScript compiler configuration
- **vite.config.ts** - Vite build configuration
- **prometheus.yml** - Prometheus scraping configuration

---

## CI/CD & Deployment

### Continuous Integration
- **GitHub Actions** - Automated testing, linting, and type checking on pull requests
- **CI Pipeline**:
  - Lint (Ruff, Black, isort)
  - Type check (MyPy strict mode)
  - Unit tests (pytest with coverage)
  - Security scan (bandit, safety)
  - Integration tests
  - Load tests (on main branch)

### Deployment Platforms (Planned - Phase 5)
- **Backend Hosting** - Railway, Render, or AWS for backend deployment
- **Frontend Hosting** - Vercel or Netlify for React application
- **Managed Services**:
  - PostgreSQL (AWS RDS, Digital Ocean Managed Database)
  - Redis (Redis Cloud, AWS ElastiCache)
  - Prometheus (Grafana Cloud, AWS Managed Prometheus)

### Domain & SSL
- **Custom Domain** - Production domain with DNS configuration
- **SSL Certificates** - Automatic HTTPS via Let's Encrypt or platform-managed SSL

---

## Backup & Disaster Recovery (New in Remediation)

### Database Backups
- **pg_dump** - PostgreSQL backup utility
- **Backup Strategy**:
  - Daily full backups
  - Hourly incremental backups
  - 30-day retention policy
  - Point-in-time recovery capability
- **Backup Storage**: AWS S3, Backblaze B2, or Digital Ocean Spaces
- **Automated Restoration Testing**: Monthly backup restoration verification

### Disaster Recovery
- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 1 hour
- **Runbooks**: Documented disaster recovery procedures
- **Failover**: Multi-region deployment for high availability (future)

---

## Security Compliance & Standards

### Compliance
- **OWASP Top 10** - Address all OWASP web application security risks
- **GDPR** - User data privacy and right to deletion (soft delete)
- **SOC 2** - Security, availability, confidentiality (future)

### Security Best Practices
- **Secrets Management**: No hardcoded credentials, environment-based secrets
- **Least Privilege**: Row-level authorization, RBAC
- **Defense in Depth**: Multiple security layers (rate limiting, input validation, authorization)
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Audit Logging**: Comprehensive security event logging

---

## Version Information

- **Current Version**: v0.5.0 (pre-remediation)
- **Target Version**: v1.0.0 (post-remediation)
- **Python Version**: 3.12+
- **Node Version**: 20+
- **PostgreSQL Version**: 16+
- **Redis Version**: 7+
- **React Version**: 18
- **TypeScript Version**: 5.x
- **FastAPI Version**: 0.104+
- **Material-UI Version**: v7

---

## External Services & APIs

### Required Services
- **Anthropic API** - Claude LLM access (API key required)
- **PostgreSQL Database** - Relational database (local or managed)
- **Redis Instance** - In-memory store (local or managed)

### Observability Services (New in Remediation)
- **Sentry** - Error tracking and performance monitoring
- **Grafana Cloud** - Metrics visualization and alerting (optional)
- **CloudWatch Logs** - Log aggregation (AWS deployments)
- **Datadog** - Comprehensive observability platform (alternative)

### Optional Services
- **GitHub API** - GitHub integration for PR reviews and issue management (future)
- **Slack API** - Team notifications and webhooks (future)

---

## Cost Tracking & Budget

### LLM Budget
- **Monthly Budget**: 200 EUR/month for Claude API usage
- **Cost Tracking**: Token usage monitoring per request
- **Budget Alerts**: Warnings when approaching monthly limit
- **Cost Optimization**: Prompt caching, semantic caching, response streaming

### Infrastructure Costs (Estimated)
- **Database**: $25-50/month (managed PostgreSQL)
- **Redis**: $10-25/month (managed Redis)
- **Backend Hosting**: $20-40/month (Railway/Render)
- **Frontend Hosting**: $0 (Vercel free tier or $20/month)
- **Monitoring**: $0-50/month (Grafana Cloud, Sentry)
- **Total Estimated**: $75-200/month (excluding LLM costs)

---

## Development Workflow

### Local Development
1. **Docker Compose Up** - Start PostgreSQL, Redis, ChromaDB, Prometheus, Grafana containers
2. **Backend Dev Server** - `uvicorn src.api.app:app --reload` with hot reload
3. **Frontend Dev Server** - `npm run dev` with Vite HMR
4. **Database Migrations** - `alembic upgrade head` for schema updates

### Testing Workflow
1. **Run Tests** - `pytest` for backend unit and integration tests
2. **Coverage Report** - `pytest --cov=src --cov-report=html` for coverage analysis
3. **Type Checking** - `mypy src` for static type validation
4. **Linting** - `ruff check src` for code quality
5. **Security Scan** - `bandit -r src` for security vulnerabilities

### Performance Testing
1. **Load Tests** - `locust -f tests/load/locustfile.py` for load testing
2. **Memory Profiling** - `python -m memory_profiler src/main.py` for memory analysis
3. **Query Analysis** - Enable SQLAlchemy echo for query logging

### Production Build
1. **Frontend Build** - `npm run build` creates optimized production bundle
2. **Type Check** - `tsc --noEmit` validates TypeScript types
3. **Backend Package** - Poetry build for Python distribution
4. **Container Build** - `docker build` for containerized deployment

---

## Notes

- **Remediation Focus**: This tech stack documentation emphasizes new additions and modifications for security, performance, reliability, and observability
- **Production Readiness**: All technologies selected for enterprise-grade deployment with proven scalability
- **Observability First**: Comprehensive monitoring, logging, and tracing enable rapid incident response
- **Security by Design**: Multiple layers of security controls (authentication, authorization, rate limiting, input validation)
- **Performance Optimized**: Caching, indexing, connection pooling, and query optimization for sub-100ms latency
- **Developer Experience**: Type safety, comprehensive testing, clear documentation, and automated workflows
