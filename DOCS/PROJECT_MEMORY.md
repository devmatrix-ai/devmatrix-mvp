# Devmatrix - Memoria del Proyecto

**Propósito**: Tracking continuo de decisiones, progreso, learnings y context del proyecto
**Última actualización**: 2025-10-10

---

## 📖 Historia del Proyecto

### Sesión 1: Arquitectura y Decisiones Estratégicas (2025-10-10)

**Participantes**: Ariel, Dany (SuperClaude)

**Objetivos de la sesión**:
- ✅ Definir arquitectura completa del sistema
- ✅ Tomar decisiones estratégicas clave
- ✅ Crear plan de trabajo detallado

**Documentos creados**:
- `devmatrix-architecture-2025.md` (v0.2)
- `WORKPLAN.md` (v1.0)
- `PROJECT_MEMORY.md` (este archivo)

---

## 🎯 Decisiones Estratégicas

### Decision Log

#### [2025-10-10] Scope Inicial: MVP (4 semanas)
**Context**: Decidir entre MVP rápido (4 sem) vs full workflow (12 sem)

**Decisión**: MVP de 4 semanas (Phase 0 + Phase 1)
- Single Agent POC
- Python only
- CLI interface
- Docker Compose local

**Rationale**:
- Validar viabilidad arquitectura rápido
- Aprender LangGraph con scope controlado
- Path incremental hacia full system
- Budget limitado (€200/mes) → scope conservador

**Alternativas consideradas**:
- ❌ Full workflow 12 semanas: muy ambicioso para first iteration
- ❌ MVP 6-8 semanas: buen compromiso pero más riesgo
- ✅ MVP 4 semanas: mejor balance risk/reward

**Impact**: Todas las decisiones subsecuentes derivan de este scope reducido

---

#### [2025-10-10] Interface: CLI Primero
**Context**: Decidir interface inicial (CLI vs Web UI)

**Decisión**: CLI primero usando Rich + Typer
- Interactive terminal con progress bars
- Syntax highlighting para código
- Approval gates interactivos
- Web UI post-MVP

**Rationale**:
- 3x más rápido implementar que Web UI
- Focus en agent logic (lo crítico)
- Mejor para debugging early stage
- Target audience inicial: developers (comfortable con CLI)

**Alternativas consideradas**:
- ❌ Web UI desde inicio: 2-3 semanas extra, distrae del core
- ❌ Simple print statements: no user-friendly enough
- ✅ Rich CLI: best balance UX/speed

**Impact**: Ahorro ~2 semanas de desarrollo → reinvertir en agent quality

---

#### [2025-10-10] Deployment: Self-hosted (Docker Compose)
**Context**: Decidir estrategia de deployment inicial

**Decisión**: Docker Compose self-hosted
- Local development con Docker
- $0 costo infraestructura MVP
- Migración gradual a cloud post-MVP

**Rationale**:
- Elimina complejidad cloud en early stage
- Developer experience optimizada (docker compose up)
- Path claro a cloud migration después
- Budget conservador → priorizar LLM APIs sobre infra

**Alternativas consideradas**:
- ❌ AWS/GCP desde inicio: $200-500/mes innecesario para MVP
- ❌ Local sin Docker: no reproducible cross-platform
- ✅ Docker Compose: simplicidad + reproducibilidad

**Impact**: Budget completo disponible para LLM APIs

---

#### [2025-10-10] Lenguajes: Python → Python+JS
**Context**: Qué lenguajes soportar en MVP

**Decisión**: Python only en MVP, JavaScript/TypeScript en Phase 2
- MVP: Python functions/modules/projects
- Phase 2+: JavaScript/TypeScript para full-stack
- Otros lenguajes: según demanda post-MVP

**Rationale**:
- Python = ecosystem nativo para AI/LLM
- Single language = menos complejidad AST parsing
- 80/20: mayoría use cases cubiertos con Python+JS
- Validar arquitectura antes de expandir lenguajes

**Alternativas consideradas**:
- ❌ Multi-language desde inicio: demasiado scope
- ❌ Solo Python forever: limita appeal full-stack devs
- ✅ Python → Python+JS: pragmático y escalable

**Impact**: Simplifica MVP, clear expansion path

---

#### [2025-10-10] Budget LLM: €200/mes
**Context**: Presupuesto mensual para API calls

**Decisión**: €200/mes (~$220 USD) con smart routing
- Claude Sonnet 4.5: code generation (crítico)
- Gemini 2.5 Flash: tareas simples (cost-effective)
- GPT-4: reasoning complejo (selectivo)

**Capacidad estimada**:
- ~200 proyectos pequeños/mes
- ~20 proyectos medianos/mes

**Monitoring**:
- Alertas at 75% budget
- Throttle at 90%
- Hard stop at 100%

**Rationale**:
- Budget moderado permite experimentación
- Smart routing maximiza value por €
- Permite aprender cost patterns reales
- Escalable según ROI demostrado

**Alternativas consideradas**:
- ❌ €100/mes: muy conservador, limitaría testing
- ❌ €500/mes: over-budget para validación
- ✅ €200/mes: sweet spot para MVP

**Impact**: Define task complexity limits y model selection strategy

---

## 📈 Progreso del Proyecto

### Phase 0: Foundation (Weeks 1-2)
**Status**: 🟡 In Progress (Day 1-4 completed)
**Target dates**: 2025-10-10 to 2025-10-24
**Started**: 2025-10-10

**Milestones**:
- [x] **Day 1-2: Project structure & Git setup** ✅ COMPLETED
  - Git repo initialized (main branch)
  - Directory structure created (src/, tests/, docker/, scripts/, workspace/)
  - Security: .gitignore + .env.example
  - Documentation: README, WORKPLAN, PROJECT_MEMORY
  - Dependencies: requirements.txt (35+ packages)
  - Build config: pyproject.toml
  - GitHub: Connected to devmatrix-ai/devmatrix-mvp
  - Initial commit & push completed

- [x] **Day 3-4: Docker Compose & dependencies** ✅ COMPLETED
  - Docker Compose config (PostgreSQL pgvector + Redis + pgAdmin)
  - Multi-stage Dockerfile (development + production)
  - Service health checks (PostgreSQL + Redis)
  - Database initialization script (5 tables + pgvector extension)
  - Volume management (postgres_data, redis_data, pgadmin_data)
  - Network configuration (devmatrix-network)
  - CLI utility scripts (dvmtx command)
  - All services healthy and verified

- [ ] **Day 5: LangGraph hello world** 🔄 NEXT
- [ ] Day 6-7: State management (Redis + PostgreSQL)
- [ ] Day 8-9: Basic tools (file operations)
- [ ] Day 10: CLI interface (Rich)

**Current blockers**: None

**Completed tasks**:
- ✅ Git repository & GitHub integration
- ✅ Project structure & Python packages
- ✅ Security & secrets management
- ✅ Documentation framework
- ✅ Dependency management
- ✅ Docker Compose infrastructure
- ✅ Database schema & initialization
- ✅ CLI utility scripts (dvmtx)

---

### Phase 1: Single Agent POC (Weeks 3-4)
**Status**: 🔴 Not Started
**Target dates**: 2025-10-24 to 2025-11-07

**Milestones**:
- [ ] Day 11-12: Planning Agent core
- [ ] Day 13-14: Human-in-loop approval
- [ ] Day 15-16: Git integration
- [ ] Day 17-18: E2E tests
- [ ] Day 19-20: Documentation & polish

**Current blockers**: Waiting for Phase 0 completion

**Completed tasks**: -

---

## 💡 Learnings & Insights

### Technical Learnings

#### [2025-10-10] LangGraph como Orchestration Framework
**Insight**: LangGraph elegido como framework principal por:
- State management robusto (crítico para multi-agent)
- Human-in-loop nativo (core requirement)
- Visual debugging con LangSmith
- Flexibilidad para multi-model

**Source**: Architecture research session
**Applied to**: Core framework selection decision

---

#### [2025-10-10] Multi-Model Strategy es Crítico
**Insight**: No hay "one size fits all" LLM:
- Claude Sonnet 4.5: best SWE-bench score (77.2%)
- Gemini Flash: 20x más barato para simple tasks
- GPT-5: superior reasoning para planning

**Source**: LLM benchmarking research
**Applied to**: Model routing architecture

**Implications**:
- Router debe ser smart desde MVP
- Cost tracking critical desde día 1
- Model selection = competitive advantage

---

#### [2025-10-10] State Management: Dual Backend
**Insight**: Necesitamos dos tipos de state:
- Redis: workflow state temporal (fast, volatile)
- PostgreSQL: project history (persistent, queryable)

**Source**: Architecture design session
**Applied to**: State management architecture

**Why it matters**:
- Redis: <10ms latency para agent coordination
- PostgreSQL: audit trail, analytics, learning

---

### Product Learnings

#### [2025-10-10] Spec-Driven Development = Diferenciador
**Insight**: La mayoría de code gen tools generan código directo sin spec clara
**Opportunity**: Socratic questioning upfront → mejor código, menos iterations

**Source**: Competitive analysis
**Applied to**: Discovery workflow design

**Validation needed**: MVP debe probar si users valoran este approach

---

#### [2025-10-10] Adaptive Autonomy = Flexibility
**Insight**: Diferentes users/projects necesitan diferentes niveles de autonomía
- Prototyping: full autonomy
- Production: supervised mode
- Learning: co-pilot mode

**Source**: User needs analysis
**Applied to**: Autonomy modes design (3 modes)

**Next step**: MVP con single mode (co-pilot), expand later

---

### Process Learnings

#### [2025-10-10] Decisions-First Approach
**What worked**:
- Tomar decisiones estratégicas upfront
- Document decisions con rationale
- Clear scope antes de code

**Impact**:
- Plan de trabajo claro
- No scope creep (yet)
- Team alignment

**To maintain**:
- Update PROJECT_MEMORY after cada decisión importante
- Review decisions periódicamente
- Document "decision why" no solo "decision what"

---

## 🚧 Riesgos y Mitigaciones

### Active Risks

#### Risk: LLM API Rate Limits
**Status**: 🟡 Medium probability, High impact
**Last updated**: 2025-10-10

**Mitigation plan**:
1. Implement request caching (similar queries)
2. Exponential backoff en retries
3. Fallback a modelos alternativos
4. Monitor rate limit headers
5. Alert before hitting limits

**Monitoring**: Token usage dashboard (TODO: implement)

---

#### Risk: Budget Overrun (€200/mes)
**Status**: 🟡 Medium probability, High impact
**Last updated**: 2025-10-10

**Mitigation plan**:
1. Real-time cost tracking per request
2. Alert at 75% budget usage
3. Auto-throttle at 90%
4. Hard stop at 100%
5. Smart routing to cheaper models

**Monitoring**: Cost dashboard (TODO: implement)

**Contingency**: Si 75% en Week 2 → reduce testing scope

---

#### Risk: LangGraph Learning Curve
**Status**: 🟢 High probability, Medium impact
**Last updated**: 2025-10-10

**Mitigation plan**:
1. Start con examples muy simples
2. Incremental complexity (hello world → single agent → multi-agent)
3. LangSmith debugging desde día 1
4. Budget 20% extra time para learning

**Monitoring**: Velocity tracking (tasks/day)

**Status update**: Not started yet, risk still relevant

---

## 🔄 Pattern Library

### Patterns to Apply

#### Pattern: Incremental Complexity
**Context**: Building complex multi-agent system
**Pattern**: Start simple → validate → add complexity
**Application**:
- Week 1: Hello world
- Week 2: Single node agent
- Week 3: Multi-node agent
- Week 4+: Multi-agent

**Why it works**: Validates each layer before adding next

---

#### Pattern: State Separation
**Context**: Need both fast coordination and persistent history
**Pattern**: Dual backend (Redis + PostgreSQL)
**Application**:
- Redis: <30min TTL, workflow state
- PostgreSQL: permanent, audit + analytics

**Why it works**: Right tool for each job

---

#### Pattern: Smart Model Routing
**Context**: Different tasks need different models
**Pattern**: Complexity scoring → model selection
**Application**:
```python
if complexity_score < 0.3:
    model = "gemini-flash"  # cheap
elif complexity_score < 0.7:
    model = "claude-sonnet"  # balanced
else:
    model = "gpt-5"  # expensive but best
```

**Why it works**: Optimize cost/performance trade-off

---

## 📊 Metrics & KPIs

### Development Metrics

#### Velocity
**Target**: 5-8 tasks/day (average)
**Current**: - (not started)
**Trend**: -

#### Code Quality
**Target**: Pylint >8.0, mypy >90%, tests >80%
**Current**: - (not started)
**Trend**: -

---

### Product Metrics (Post-MVP)

#### Agent Success Rate
**Definition**: % of tasks completed successfully without human intervention
**Target**: >80%
**Current**: - (not started)

#### Time to Code
**Definition**: Average time from request to approved code
**Target**: <10 seconds (simple function)
**Current**: - (not started)

#### User Satisfaction
**Definition**: User approval rate on first generation
**Target**: >70%
**Current**: - (not started)

---

### Cost Metrics

#### Cost per Task
**Definition**: Average LLM API cost per completed task
**Target**: <€1.00 (simple), <€5.00 (complex)
**Current**: - (not started)

#### Budget Utilization
**Definition**: % of €200/mes budget used
**Target**: 70-90% (optimize for learning, not conservation)
**Current**: 0%
**Trend**: -

---

## 🎓 Knowledge Base

### Key Concepts

#### LangGraph State Management
**What**: Graph-based orchestration con typed state
**Why**: Enables complex workflows with state persistence
**Resources**:
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [State Management Guide](https://python.langchain.com/docs/langgraph/concepts/low_level)

**Key takeaways**:
- State is TypedDict
- Nodes transform state
- Edges define flow
- Conditional edges enable branching

---

#### Model Context Protocol (MCP)
**What**: Standard for LLM tool integration
**Why**: Enables safe, structured tool calling
**Resources**:
- [MCP Spec](https://modelcontextprotocol.io/)
- [Anthropic MCP Guide](https://docs.anthropic.com/claude/docs/tool-use)

**Key takeaways**:
- Tools have schemas (input/output types)
- Sandboxing critical for security
- Logging enables debugging
- Error handling must be robust

---

### Technical Stack Reference

#### Core Dependencies
```yaml
Framework: LangGraph (orchestration)
Web: FastAPI (API layer)
State: Redis (temporal) + PostgreSQL (persistent)
LLMs: Claude Sonnet 4.5, Gemini 2.5 Flash, GPT-4
CLI: Typer + Rich
Testing: pytest + pytest-asyncio
```

#### Version Locks
```
langgraph==0.2.0
langchain==0.3.0
fastapi==0.115.0
```
*Note: Lock versions early para avoid breaking changes*

---

## 🔮 Future Considerations

### Post-MVP Features (Phase 2+)

#### Multi-Agent System
**When**: Phase 2 (Weeks 5-8)
**Why**: Enable parallel work, specialized agents
**Complexity**: High
**Dependencies**: Phase 1 must validate single agent first

---

#### Web UI Dashboard
**When**: Post Phase 2
**Why**: Better UX, demos, non-technical users
**Complexity**: Medium
**Dependencies**: Core agent logic stable

---

#### Multi-Language Support
**When**: Phase 3+
**Why**: Expand market, full-stack coverage
**Complexity**: High (each language needs AST parser)
**Priority languages**: Go, Rust, Java

---

#### Vector Memory (pgvector)
**When**: Phase 4+
**Why**: Semantic code search, pattern learning
**Complexity**: Medium
**Dependencies**: Base functionality proven valuable

---

### Open Questions

#### Product Questions
- [ ] **Target market**: Solo devs, teams, or enterprise?
  - *Impact*: Affects pricing, features, deployment model
  - *Decision by*: After MVP user feedback

- [ ] **Pricing model**: Free tier + paid, or usage-based?
  - *Impact*: Revenue strategy, feature gating
  - *Decision by*: Week 8 (after Phase 2)

- [ ] **Open source strategy**: Full open, open-core, or proprietary?
  - *Impact*: Community, competition, monetization
  - *Decision by*: Before public launch

#### Technical Questions
- [ ] **Multi-tenancy**: Single tenant or multi-tenant desde inicio?
  - *Impact*: Database schema, authentication, deployment
  - *Decision by*: Phase 5 (production readiness)

- [ ] **Observability**: LangSmith vs custom vs both?
  - *Impact*: Debugging capability, cost
  - *Decision by*: Phase 1 (MVP needs debugging)

---

## 📝 Session Notes

### Session 1 (2025-10-10) - Part 1: Architecture & Planning
**Duration**: ~2 hours
**Participants**: Ariel, Dany

**Topics covered**:
1. ✅ Architecture review completa
2. ✅ Strategic decisions (5 major decisions)
3. ✅ Work plan creation (4 weeks detailed)
4. ✅ Project memory setup

**Decisions made**: 5 strategic decisions (documented above)

**Action items**:
- [x] Create WORKPLAN.md → Done
- [x] Create PROJECT_MEMORY.md → Done (this file)
- [x] Start Phase 0 implementation → Started

---

### Session 1 (2025-10-10) - Part 2: Implementation Kickoff
**Duration**: ~1 hour
**Participants**: Ariel, Dany

**Topics covered**:
1. ✅ Planning refinement (8 tactical decisions)
2. ✅ Phase 0 Day 1-2 execution (Git + Structure)
3. ✅ Repository setup completo
4. ✅ Secrets management implementation

**Tactical decisions made**:
1. LLM Keys: Solo Claude inicialmente (Anthropic API)
2. Workspace: `/workspace` con `--output-dir` flag opcional
3. Testing: 2-3 E2E smoke tests reales, resto mocked
4. CLI Interaction: Single-shot para MVP
5. Error Recovery: Free-form feedback
6. Git Commits: Ask before commit (safe default)
7. Cost Tracking: Simple counter para MVP
8. Secrets: `.env` + `.gitignore` (NUNCA commit keys)

**Completed tasks**:
- [x] Git repository initialization (main branch)
- [x] Project directory structure creada
- [x] .gitignore comprehensive (secrets, workspace, cache)
- [x] .env.example template con todas las variables
- [x] README.md con quick start guide
- [x] requirements.txt (35+ dependencies)
- [x] pyproject.toml (build config + dev tools)
- [x] Python package structure (__init__.py files)
- [x] GitHub remote repository conectado: `devmatrix-ai/devmatrix-mvp`
- [x] Initial commit + push to GitHub

**Files created** (15 files):
```
.env.example          → Environment template
.gitignore            → Security (secrets excluded)
README.md             → Project documentation
requirements.txt      → Python dependencies
pyproject.toml        → Build & tools config
src/__init__.py       → Main package
src/agents/__init__.py
src/tools/__init__.py
src/llm/__init__.py
src/state/__init__.py
src/cli/__init__.py
tests/__init__.py
DOCS/devmatrix-architecture-2025.md (v0.2)
DOCS/WORKPLAN.md (v1.0)
DOCS/PROJECT_MEMORY.md (this file)
```

**GitHub Repository**:
- URL: `git@github.com:devmatrix-ai/devmatrix-mvp.git`
- First commit: `da3ecf3` - "Initial project setup: Foundation for Devmatrix MVP"
- Branch: `main`
- Status: ✅ Synced with remote

**Next session agenda**:
- Phase 0 Day 3-4: Docker Compose setup
- PostgreSQL + Redis configuration
- First LangGraph "Hello World"

---

### Session 1 (2025-10-10) - Part 3: Docker Infrastructure
**Duration**: ~1.5 hours
**Participants**: Ariel, Dany

**Topics covered**:
1. ✅ Docker Compose multi-service setup
2. ✅ PostgreSQL with pgvector extension
3. ✅ Redis for state management
4. ✅ Database schema initialization
5. ✅ CLI utility scripts creation
6. ✅ Service health verification
7. ✅ Docker configuration debugging

**Completed tasks**:
- [x] docker-compose.yml con 3 servicios (PostgreSQL, Redis, pgAdmin)
- [x] Multi-stage Dockerfile (development + production stages)
- [x] .dockerignore para build optimization
- [x] Database init script: 01-init-db.sql (5 tables + pgvector)
- [x] CLI utility: scripts/dvmtx (350+ lines bash script)
- [x] CLI installer: scripts/install-cli.sh
- [x] CLI documentation: scripts/README.md (500+ lines)
- [x] CLI installed globally: ~/.local/bin/dvmtx
- [x] Services tested and verified healthy

**Technical issues resolved**:
1. **Redis password configuration error**:
   - Problem: Empty REDIS_PASSWORD causing Redis restart loop
   - Solution: Removed `--requirepass` flag from command
   - Result: Redis started successfully

2. **Docker Compose version warning**:
   - Problem: `version: '3.8'` field obsolete in Compose v2
   - Solution: Removed version field from docker-compose.yml
   - Result: Clean startup without warnings

3. **WSL2 credential helper warning**:
   - Problem: "no configuration file provided: not found" on every docker command
   - Solution: Created `docker_compose()` wrapper function to filter warning
   - Result: Clean CLI output without cosmetic errors

**Database schema created**:
```sql
devmatrix.projects       (id, name, description, status, created_at, updated_at)
devmatrix.tasks          (id, project_id, agent_name, task_type, status, input_data, output_data, created_at, completed_at)
devmatrix.agent_decisions (id, task_id, decision_point, options, selected_option, rationale, created_at)
devmatrix.git_commits    (id, project_id, commit_hash, message, author, files_changed, created_at)
devmatrix.cost_tracking  (id, project_id, task_id, model_name, input_tokens, output_tokens, cost_eur, created_at)
```

**CLI commands available**:
```bash
dvmtx up            # Start services
dvmtx down          # Stop services
dvmtx restart       # Restart services
dvmtx status        # Service health
dvmtx logs [svc]    # View logs
dvmtx clean         # Delete all data
dvmtx db shell      # PostgreSQL shell
dvmtx db tables     # List tables
dvmtx db backup     # Create backup
dvmtx redis cli     # Redis CLI
dvmtx redis flush   # Flush Redis
dvmtx dev pgadmin   # Start pgAdmin
dvmtx dev install   # Install Python deps
dvmtx dev test      # Run tests
dvmtx dev lint      # Run linters
dvmtx dev format    # Format code
```

**Files created** (8 files):
```
docker-compose.yml              → Multi-service orchestration
Dockerfile                      → Multi-stage build config
.dockerignore                   → Build optimization
docker/postgres/init/01-init-db.sql → Database schema
scripts/dvmtx                   → CLI utility (350+ lines)
scripts/install-cli.sh          → CLI installer
scripts/README.md               → CLI documentation (500+ lines)
backups/.gitkeep                → Backup directory
```

**Git commits made**:
- `3c8f4e2` - "feat: Add Docker Compose infrastructure with PostgreSQL and Redis"
- `e0aaab1` - "feat: Add CLI utility scripts (dvmtx command)"
- `218b19c` - "fix: Remove obsolete docker-compose version and suppress credential warning"

**Next session agenda**:
- Phase 0 Day 5: LangGraph "Hello World"
- First agent implementation
- Basic workflow with single node

---

## 🔗 Related Documents

### Project Documentation
- `devmatrix-architecture-2025.md` - Complete architecture specification
- `WORKPLAN.md` - Detailed 4-week work plan
- `PROJECT_MEMORY.md` - This file (decision log, progress tracking)

### External Resources
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [SWE-bench Leaderboard](https://www.swebench.com/)
- [Claude API Reference](https://docs.anthropic.com/claude/reference)

---

## 📅 Timeline

```
2025-10-10: Proyecto iniciado, decisiones tomadas
2025-10-10 to 2025-10-24: Phase 0 (Foundation)
2025-10-24 to 2025-11-07: Phase 1 (Single Agent POC)
2025-11-07: MVP target completion
2025-11-08+: Phase 2 planning based on learnings
```

---

## 🎯 Success Criteria (MVP)

### Must Have (Critical)
- ✅ Agent genera código Python correcto (>90% accuracy)
- ✅ Human approval flow funciona sin bugs
- ✅ State persiste correctamente
- ✅ Git integration funcional
- ✅ Tests pasan (>80% coverage)

### Should Have (Important)
- ✅ Docker Compose levanta en <2 min
- ✅ CLI intuitivo y user-friendly
- ✅ Documentation clara
- ✅ Cost tracking básico

### Nice to Have (Optional)
- ⚪ LangSmith integration completa
- ⚪ Advanced error handling
- ⚪ Performance optimization

---

## 🔄 Update Protocol

**Frequency**: Actualizar después de:
- Cada decisión estratégica importante
- Cada milestone completado
- Cada blocker identificado
- Cada learning significativo
- Cada weekly review

**Who**: Dany (con input de Ariel)

**Format**: Agregar entries en secciones relevantes, mantener chronological order

---

**Última actualización**: 2025-10-10 (Session 1 Part 3 - Docker Infrastructure)
**Próxima actualización planeada**: 2025-10-17 (Weekly Review)
**Versión**: 1.2 (Phase 0 Day 1-4 completed)
