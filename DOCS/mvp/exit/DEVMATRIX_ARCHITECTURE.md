# DevMatrix Architecture: Spec to Application Pipeline

**Date**: 2025-12-01  
**Version**: 1.0  
**Author**: DevMatrix Team

---

## 1. Executive Summary

DevMatrix es un sistema de generación de código agentico que transforma especificaciones en lenguaje natural (Markdown) en aplicaciones FastAPI completamente funcionales con:

- Base de datos PostgreSQL
- Migraciones Alembic
- Tests automatizados
- Docker deployment
- Observabilidad (Prometheus/Grafana)

### Pipeline Overview

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│  Spec.md    │────▶│ IR Extraction│────▶│ Code Generation│────▶│ Final App    │
│  (Natural   │     │ (LLM + Cache)│     │ (PatternBank)  │     │ (Docker)     │
│  Language)  │     └──────────────┘     └────────────────┘     └──────────────┘
└─────────────┘            │                     │                     │
                           ▼                     ▼                     ▼
                    ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
                    │ApplicationIR │     │ 90+ Files      │     │ Smoke Tests  │
                    │(6 Sub-Models)│     │ Generated      │     │ Validation   │
                    └──────────────┘     └────────────────┘     └──────────────┘
```

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph Input["📄 Input Layer"]
        SPEC[/"spec.md\n(Natural Language)"/]
    end

    subgraph Extraction["🔍 IR Extraction Layer"]
        STA[SpecToApplicationIR]
        LLM[(Claude LLM)]
        CACHE[(4-Tier Cache)]
        
        STA -->|"prompt"| LLM
        LLM -->|"JSON"| STA
        STA <-->|"check/store"| CACHE
    end

    subgraph IR["📐 Intermediate Representation"]
        AIR[ApplicationIR]
        DOM[DomainModelIR]
        API[APIModelIR]
        BEH[BehaviorModelIR]
        VAL[ValidationModelIR]
        INF[InfrastructureModelIR]
        TST[TestsModelIR]
        
        AIR --> DOM
        AIR --> API
        AIR --> BEH
        AIR --> VAL
        AIR --> INF
        AIR --> TST
    end

    subgraph CodeGen["⚙️ Code Generation Layer"]
        CGS[CodeGenerationService]
        PB[(PatternBank\nQdrant)]
        BG[BehaviorGenerator]
        TIG[TestsIRGenerator]
        
        CGS <-->|"retrieve patterns"| PB
        CGS --> BG
        CGS --> TIG
    end

    subgraph Output["📦 Output Layer"]
        FILES[/"90+ Generated Files"/]
        DOCKER[Docker Compose]
        DB[(PostgreSQL)]
        APP[FastAPI App]
    end

    subgraph Validation["✅ Validation Layer"]
        SMOKE[SmokeRunnerV2]
        REPAIR[SmokeRepairOrchestrator]
        
        SMOKE <-->|"iterate"| REPAIR
    end

    SPEC --> STA
    STA --> AIR
    AIR --> CGS
    CGS --> FILES
    FILES --> DOCKER
    DOCKER --> DB
    DOCKER --> APP
    APP --> SMOKE
    SMOKE -->|"failures"| REPAIR
    REPAIR -->|"fix code"| FILES
```

---

## 3. Component Details

### 3.1 Input Layer

| Component | File | Description |
|-----------|------|-------------|
| **Spec Parser** | `tests/e2e/synthetic_specs/*.md` | Markdown specs with entities, endpoints, business logic |

**Example Spec Structure:**
```markdown
# E-Commerce API

## Entities
- Product: name, price, stock, active
- Customer: email, name
- Cart: customer_id, items[]
- Order: customer_id, items[], status, total

## Endpoints  
- POST /products - Create product
- GET /products/{id} - Get product
- POST /carts/{id}/checkout - Create order from cart

## Business Logic
- Price must be > 0
- Stock cannot go negative
- Cart must have items to checkout
```

---

### 3.2 IR Extraction Layer

| Component | File | Purpose |
|-----------|------|---------|
| **SpecToApplicationIR** | `src/specs/spec_to_application_ir.py` | LLM-based IR extraction |
| **LLM Client** | `src/cognitive/llm/anthropic_client.py` | Claude API wrapper |
| **IR Cache** | `src/cognitive/ir/ir_cache.py` | 4-tier caching |

**Cache Strategy (4-Tier):**

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: Redis           │ TTL: 7 days │ Fastest lookup     │
├─────────────────────────────────────────────────────────────┤
│  Tier 2: Filesystem      │ .devmatrix/ir_cache/ │ Cold start│
├─────────────────────────────────────────────────────────────┤
│  Tier 3: Neo4j           │ Graph persistence │ Optional     │
├─────────────────────────────────────────────────────────────┤
│  Tier 4: LLM Generation  │ Only when cache miss │ $0.01-0.05│
└─────────────────────────────────────────────────────────────┘
```

---

### 3.3 Intermediate Representation (IR)

```mermaid
classDiagram
    class ApplicationIR {
        +UUID app_id
        +str name
        +str description
        +DomainModelIR domain_model
        +APIModelIR api_model
        +BehaviorModelIR behavior_model
        +ValidationModelIR validation_model
        +InfrastructureModelIR infrastructure_model
        +TestsModelIR tests_model
    }
    
    class DomainModelIR {
        +List~Entity~ entities
    }
    
    class Entity {
        +str name
        +List~Attribute~ attributes
        +List~Relationship~ relationships
    }
    
    class APIModelIR {
        +List~Endpoint~ endpoints
    }
    
    class Endpoint {
        +str path
        +str method
        +str summary
        +List~APIParameter~ parameters
        +APISchema request_body
        +Dict responses
    }
    
    class BehaviorModelIR {
        +List~Flow~ flows
        +List~Invariant~ invariants
    }
    
    class TestsModelIR {
        +List~SeedEntityIR~ seed_entities
        +List~EndpointTestSuite~ endpoint_tests
    }
    
    ApplicationIR --> DomainModelIR
    ApplicationIR --> APIModelIR
    ApplicationIR --> BehaviorModelIR
    ApplicationIR --> TestsModelIR
    DomainModelIR --> Entity
    APIModelIR --> Endpoint
    BehaviorModelIR --> Flow
```

---

### 3.4 Code Generation Layer

| Component | File | Purpose |
|-----------|------|---------|
| **CodeGenerationService** | `src/services/code_generation_service.py` | Main orchestrator |
| **PatternBank** | `src/cognitive/patterns/pattern_bank.py` | Qdrant vector store |
| **BehaviorGenerator** | `src/cognitive/behavior/behavior_generator.py` | Workflows/state machines |
| **TestsIRGenerator** | `src/services/tests_ir_generator.py` | Test scenario generation |

**Pattern Composition Flow:**

```mermaid
sequenceDiagram
    participant CGS as CodeGenerationService
    participant PB as PatternBank (Qdrant)
    participant IR as ApplicationIR
    participant Files as Generated Files

    CGS->>IR: Read entities, endpoints
    CGS->>PB: Query patterns by category
    PB-->>CGS: Return matched patterns

    loop For each pattern category
        CGS->>CGS: Adapt pattern with IR data
        CGS->>Files: Write file (entities.py, routes/*.py, etc.)
    end

    CGS->>CGS: Generate missing files (README, requirements.txt)
    CGS->>CGS: Add __init__.py files
    CGS-->>Files: 90+ files generated
```

**Generated File Structure:**

```
generated_app/
├── src/
│   ├── main.py                    # FastAPI app entry
│   ├── core/
│   │   ├── config.py              # Settings (Pydantic)
│   │   ├── database.py            # Async SQLAlchemy
│   │   └── dependencies.py        # DI container
│   ├── models/
│   │   ├── entities.py            # SQLAlchemy models
│   │   └── schemas.py             # Pydantic schemas
│   ├── api/
│   │   └── routes/
│   │       ├── product.py         # CRUD routes
│   │       ├── customer.py
│   │       ├── cart.py
│   │       └── order.py
│   ├── services/
│   │   ├── product_service.py     # Business logic
│   │   ├── cart_service.py
│   │   └── order_service.py
│   └── workflows/                  # From BehaviorModelIR
│       └── checkout_workflow.py
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── scripts/
│   └── seed_db.py                 # Test data seeding
├── tests/
│   └── test_*.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

### 3.5 Infrastructure Layer

```mermaid
graph TB
    subgraph Docker["🐳 Docker Compose"]
        APP[FastAPI App\n:8000]
        DB[(PostgreSQL\n:5432)]
        REDIS[(Redis\n:6379)]
        PROM[Prometheus\n:9090]
        GRAF[Grafana\n:3000]
    end

    subgraph External["☁️ External Services"]
        QDRANT[(Qdrant\n:6333)]
        NEO4J[(Neo4j\n:7687)]
        LLM[Claude API]
    end

    APP -->|"async"| DB
    APP -->|"cache"| REDIS
    APP -->|"metrics"| PROM
    PROM --> GRAF

    APP -.->|"patterns"| QDRANT
    APP -.->|"graph"| NEO4J
    APP -.->|"generation"| LLM
```

**Docker Compose Services:**

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `app` | Python 3.11 | 8000 | FastAPI application |
| `postgres` | postgres:15 | 5432 | Primary database |
| `redis` | redis:7 | 6379 | Caching, sessions |
| `prometheus` | prom/prometheus | 9090 | Metrics collection |
| `grafana` | grafana/grafana | 3000 | Dashboards |

**Environment Variables:**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/app
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=admin
POSTGRES_DB=devmatrix_db

# Redis
REDIS_URL=redis://redis:6379/0

# App
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=<generated>
```

---

### 3.6 Validation Layer

```mermaid
flowchart LR
    subgraph SmokeTest["🧪 Smoke Testing"]
        RUNNER[SmokeRunnerV2]
        TESTS[(TestsModelIR)]

        RUNNER -->|"execute"| TESTS
    end

    subgraph Repair["🔧 Repair Loop"]
        ORCH[SmokeRepairOrchestrator]
        DOCKER[Docker Rebuild]

        ORCH --> DOCKER
        DOCKER --> RUNNER
    end

    subgraph Results["📊 Results"]
        PASS[Pass Rate %]
        REPORT[JSON Report]
    end

    TESTS --> RUNNER
    RUNNER -->|"failures"| ORCH
    RUNNER -->|"results"| PASS
    RUNNER -->|"save"| REPORT
    ORCH -->|"fix code"| DOCKER
```

**Smoke Test Execution:**

1. **Seed Database**: Run `scripts/seed_db.py` with predictable UUIDs
2. **Start App**: `docker compose up -d`
3. **Execute Tests**: Run all scenarios from `TestsModelIR`
4. **Collect Results**: Pass/fail per endpoint
5. **Repair Loop**: If failures > threshold, attempt code fixes

**Test Scenario Types:**

| Type | Description | Expected Status |
|------|-------------|-----------------|
| `happy_path` | Valid request with seeded data | 200/201 |
| `edge_case` | Boundary conditions | 200/400 |
| `error_case` | Invalid input | 400/422 |
| `not_found` | Non-existent resource | 404 |

---

## 4. Data Flow: End-to-End

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Spec as spec.md
    participant STA as SpecToApplicationIR
    participant Cache as 4-Tier Cache
    participant LLM as Claude LLM
    participant IR as ApplicationIR
    participant CGS as CodeGenerationService
    participant PB as PatternBank
    participant Files as Generated Files
    participant Docker as Docker Compose
    participant Smoke as SmokeRunnerV2
    participant App as Final App

    User->>Spec: Write specification
    Spec->>STA: Parse markdown

    STA->>Cache: Check cache
    alt Cache Hit
        Cache-->>STA: Return cached IR
    else Cache Miss
        STA->>LLM: Extract IR (prompt)
        LLM-->>STA: JSON response
        STA->>Cache: Store IR
    end

    STA->>IR: Build ApplicationIR
    IR->>CGS: Pass to code generator

    CGS->>PB: Query patterns
    PB-->>CGS: Return patterns

    loop For each file category
        CGS->>CGS: Compose pattern + IR
        CGS->>Files: Write file
    end

    Files->>Docker: Build image
    Docker->>Docker: Start services
    Docker->>Smoke: Run tests

    alt Tests Pass
        Smoke-->>User: ✅ App ready
    else Tests Fail
        Smoke->>CGS: Repair request
        CGS->>Files: Apply fixes
        Files->>Docker: Rebuild
    end

    Docker->>App: Deploy
    App-->>User: 🚀 Production ready
```

---

## 5. Key Algorithms

### 5.1 Dual UUID Seeding (Bug #187)

Para evitar que DELETE tests destruyan data usada por otros tests:

```python
# Primary UUIDs: ..01, ..02, ..03 (GET, PUT, PATCH)
# Secondary UUIDs: ..11, ..12, ..13 (DELETE only)

uuid_base = "00000000-0000-4000-8000-00000000000"
uuid_base_delete = "00000000-0000-4000-8000-0000000000"

for idx, entity in enumerate(entities, start=1):
    primary_uuid = f"{uuid_base}{idx}"      # ..01, ..02
    delete_uuid = f"{uuid_base_delete}{idx + 10}"  # ..11, ..12
```

### 5.2 Pattern Matching

```python
# PatternBank query by semantic similarity
patterns = await pattern_bank.search(
    query=f"FastAPI {entity_name} CRUD routes",
    category="routes",
    limit=5,
    min_score=0.7
)

# Adapt pattern with IR data
adapted = pattern.code.replace("{{entity_name}}", entity.name)
adapted = adapted.replace("{{attributes}}", format_attrs(entity.attributes))
```

### 5.3 Test Generation

```python
# From APIModelIR → EndpointTestSuite
for endpoint in api_model.endpoints:
    suite = EndpointTestSuite(
        endpoint_path=endpoint.path,
        http_method=endpoint.method,
        happy_path=generate_happy_path(endpoint),
        edge_cases=generate_edge_cases(endpoint),
        error_cases=generate_error_cases(endpoint)
    )
```

---

## 6. Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Spec → IR extraction | < 10s | ~5s (cached: <100ms) |
| Code generation | < 60s | ~30s |
| Docker build | < 120s | ~60s |
| Smoke tests (74 scenarios) | < 60s | ~45s |
| **Total pipeline** | < 5 min | ~3 min |

---

## 7. Error Handling

| Layer | Error Type | Recovery |
|-------|------------|----------|
| IR Extraction | LLM timeout | Retry 3x with backoff |
| IR Extraction | Invalid JSON | Validate + fill defaults |
| Code Generation | Pattern not found | LLM fallback generation |
| Code Generation | Syntax error | AST repair pass |
| Smoke Tests | 404/422 mismatch | Repair orchestrator |
| Docker | Build failure | Retry with --no-cache |

---

## 8. Observability

### 8.1 Logging

```python
# Structured logging with structlog
logger.info("Code generation complete", extra={
    "files_count": 96,
    "duration_ms": 1234,
    "stratum": {"TEMPLATE": 31, "AST": 59, "LLM": 6}
})
```

### 8.2 Metrics

```python
# Prometheus metrics exposed at /metrics
REQUEST_COUNT = Counter("http_requests_total", "Total requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency")
```

### 8.3 Health Checks

| Endpoint | Purpose |
|----------|---------|
| `GET /health/health` | Liveness probe |
| `GET /health/ready` | Readiness probe |
| `GET /metrics/metrics` | Prometheus metrics |

---

## 9. Security

| Control | Implementation |
|---------|----------------|
| Input validation | Pydantic schemas with constraints |
| SQL injection | SQLAlchemy ORM (parameterized) |
| Authentication | JWT tokens (optional) |
| CORS | Configurable origins |
| Secrets | Environment variables |
| Container | Non-root user, read-only FS |

---

## 10. Appendix: File Reference

| Category | Files | Lines (approx) |
|----------|-------|----------------|
| IR Models | 8 | ~1,200 |
| Code Generation | 5 | ~6,500 |
| Pattern Bank | 3 | ~800 |
| Smoke Testing | 4 | ~2,000 |
| E2E Pipeline | 1 | ~6,800 |
| **Total** | **21** | **~17,300** |

### Key Source Files

| File | Purpose |
|------|---------|
| `src/specs/spec_to_application_ir.py` | IR extraction (LLM) |
| `src/cognitive/ir/application_ir.py` | Root IR model |
| `src/services/code_generation_service.py` | Code generation |
| `src/cognitive/patterns/pattern_bank.py` | Pattern storage |
| `src/validation/smoke_runner_v2.py` | Test execution |
| `src/validation/smoke_repair_orchestrator.py` | Repair loop |
| `tests/e2e/real_e2e_full_pipeline.py` | E2E orchestrator |

---

## 11. Domain-Agnostic Architecture (Planned)

> **Reference**: See `IR_AGNOSTIC_IMPLEMENTATION_PLAN.md` for full implementation details.

DevMatrix is designed to be **100% domain-agnostic**. The IR contains all semantic information needed to generate, test, and repair code without knowing the business domain.

### 11.1 IR as Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ApplicationIR                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  DomainModelIR     │ Entities, attributes, relationships               │
│  APIModelIR        │ Endpoints, parameters, request/response schemas   │
│  BehaviorModelIR   │ Flows, preconditions, postconditions, invariants  │
│  ValidationModelIR │ Constraints, rules, enforcement types              │
│  TestsModelIR      │ Seed data, test scenarios, expected outcomes       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Code Generation   │ Schemas from IR, not hardcoded entity names       │
│  Seed Generation   │ Payloads from constraints, relationships from IR  │
│  Failure Repair    │ Classify by IR semantics, fix by IR contracts     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Auto-Seed Generator (IR-Aware)

The seed generator derives all data from IR without domain knowledge:

| IR Source | Derived Information |
|-----------|---------------------|
| `DomainModelIR.entities` | What to create |
| `ValidationModelIR.rules` | FK relationships, dependency order |
| `ValidationModelIR.rules` | Valid values (min/max, enums) |
| `APIModelIR.endpoints` | Which POST endpoint to use |
| `BehaviorModelIR.flows` | Required state for flow tests |

### 11.3 Runtime Flow Repair (Agnostic)

Failures are classified and repaired using IR semantics:

| Failure Type | IR Detection | Repair Action |
|--------------|--------------|---------------|
| `MISSING_PRECONDITION` | Entity in path doesn't exist | Seed missing entity |
| `WRONG_STATUS_CODE` | IR says valid, code returns error | Fix status code |
| `MISSING_SIDE_EFFECT` | Postcondition not satisfied | Inject service call |

### 11.4 Complete Agnostic Pipeline

```
SPEC (any domain)
       ↓
IR Multi-Layer (types, relationships, constraints, flows)
       ↓
Planner + DAG
       ↓
PatternBank (universal semantic patterns)
       ↓
AST Synthesis (deterministic)
       ↓
CodeGen
       ↓
Static Validation + Repair
       ↓
Deployment
       ↓
Auto-Seed (universal, IR-derived)
       ↓
Runtime Smoke + IR Smoke
       ↓
Runtime Flow Repair (universal, IR-driven)
       ↓
Learning (global anti-patterns)
       ↓
✅ Perfect Code — without knowing the domain
```

---

## 12. Recent Bug Fixes

### Bug #199: Missing request_schema in Inferred Endpoints
- **File**: `src/services/inferred_endpoint_enricher.py`
- **Fix**: Build `request_schema` from child entity attributes for nested resource PUT endpoints

### Bug #200: Code Generator Ignoring IR Schemas
- **Files**: `src/services/code_generation_service.py`, `src/services/production_code_generators.py`
- **Fix**: Use `endpoint.request_schema.name` from IR instead of hardcoding `{Entity}Update`

---

**Document End**


