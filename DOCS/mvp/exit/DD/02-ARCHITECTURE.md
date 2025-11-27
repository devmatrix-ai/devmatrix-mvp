# DevMatrix System Architecture

**Version**: 3.0
**Date**: November 2025
**Status**: Production-Ready Design
**Source**: Extracted from actual codebase (~378 Python files)

---

## Executive Summary

DevMatrix is a **Cognitive Code Generation Engine** that transforms natural language specifications into production-ready applications. The architecture is built on three foundational principles:

1. **IR-Centric**: ApplicationIR is the single source of truth
2. **Stratified Generation**: 4 strata minimize LLM usage (TEMPLATE → AST → LLM → QA)
3. **Cognitive Learning**: Pattern promotion pipeline (LLM → AST → Template)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEVMATRIX ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────────────┐   │
│  │ Natural Lang │───>│   SPEC PARSING   │───>│      APPLICATION IR         │   │
│  │    Spec      │    │   SpecParser     │    │  (Single Source of Truth)   │   │
│  └──────────────┘    │   + LLM Extract  │    │                             │   │
│                      └──────────────────┘    │  ┌─────────────────────────┐│   │
│                                              │  │ DomainModelIR           ││   │
│                                              │  │ APIModelIR              ││   │
│                                              │  │ BehaviorModelIR         ││   │
│                                              │  │ ValidationModelIR       ││   │
│                                              │  │ InfrastructureModelIR   ││   │
│                                              │  └─────────────────────────┘│   │
│                                              └──────────────┬──────────────┘   │
│                                                             │                   │
│                      ┌──────────────────────────────────────┼──────────────┐   │
│                      │           COGNITIVE LAYER            │              │   │
│                      │                                      v              │   │
│  ┌────────────────┐  │  ┌──────────────┐    ┌──────────────────────────┐  │   │
│  │   PatternBank  │<─┼──│ Multi-Pass   │───>│         CPIE             │  │   │
│  │   (Qdrant)     │  │  │ Planner      │    │ (Cognitive Pattern       │  │   │
│  │   768d + 384d  │──┼─>│ (6 passes)   │    │  Inference Engine)       │  │   │
│  └────────────────┘  │  └──────────────┘    └──────────────────────────┘  │   │
│                      │         │                      │                    │   │
│  ┌────────────────┐  │         v                      v                    │   │
│  │   DAG Store    │  │  ┌──────────────┐    ┌──────────────────────────┐  │   │
│  │   (Neo4j)      │<─┼──│ DAG Builder  │    │  Co-Reasoning System     │  │   │
│  │   IR + Tasks   │  │  │ (Execution   │    │  Claude + DeepSeek       │  │   │
│  └────────────────┘  │  │  Waves)      │    └──────────────────────────┘  │   │
│                      │  └──────────────┘                                   │   │
│                      └─────────────────────────────────────────────────────┘   │
│                                              │                                  │
│                      ┌───────────────────────┼───────────────────────────────┐ │
│                      │    STRATIFIED GENERATION LAYER                        │ │
│                      │                       v                               │ │
│    ┌─────────┐       │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │ │
│    │TEMPLATE │       │  │TEMPLATE │  │   AST   │  │   LLM   │  │   QA    │  │ │
│    │ Stratum │       │  │ Infra   │  │Entities │  │Business │  │Validate │  │ │
│    │  (0%)   │       │  │ Config  │  │Schemas  │  │Workflows│  │Compliance│ │ │
│    └─────────┘       │  │ Health  │  │Routes   │  │Custom   │  │Tests    │  │ │
│                      │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │ │
│                      └───────────────────────────────────────────────────────┘ │
│                                              │                                  │
│                      ┌───────────────────────┼───────────────────────────────┐ │
│                      │    VALIDATION & REPAIR LAYER                          │ │
│                      │                       v                               │ │
│  ┌────────────────┐  │  ┌──────────────┐    ┌──────────────────────────┐    │ │
│  │ ErrorPattern   │<─┼──│ Compliance   │───>│    CodeRepairAgent       │    │ │
│  │ Store          │  │  │ Validator    │    │    (AST Patching)        │    │ │
│  └────────────────┘  │  └──────────────┘    └──────────────────────────┘    │ │
│                      └───────────────────────────────────────────────────────┘ │
│                                              │                                  │
│                                              v                                  │
│                      ┌──────────────────────────────────────────────────────┐  │
│                      │              GENERATED APPLICATION                    │  │
│                      │  src/ models/ services/ routes/ tests/ docker/        │  │
│                      └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        E2E PIPELINE (11 PHASES)                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Phase 1: SPEC INGESTION                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  spec.md ──> SpecParser ──> SpecRequirements                            │    │
│  │                   │                                                      │    │
│  │                   v                                                      │    │
│  │         SpecToApplicationIR (LLM extraction)                            │    │
│  │                   │                                                      │    │
│  │                   v                                                      │    │
│  │            ApplicationIR (cached as JSON)                               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 1.5: VALIDATION SCALING      v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Pattern Extraction ──> LLM Extraction ──> Graph Inference              │    │
│  │  (50+ YAML patterns)    (3 prompts)        (entity relationships)       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 2: REQUIREMENTS ANALYSIS     v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  RequirementsClassifier: Domain, Priority, Complexity, Risk, Deps       │    │
│  │  BEFORE: 42% accuracy, 6% recall                                        │    │
│  │  AFTER:  ≥90% accuracy, ≥90% recall (semantic classification)           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 3: MULTI-PASS PLANNING       v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Pass 1: Requirements Analysis (entities, attributes, relationships)    │    │
│  │  Pass 2: Architecture Design (modules, patterns, cross-cutting)         │    │
│  │  Pass 3: Contract Definition (APIs, schemas, validation rules)          │    │
│  │  Pass 4: Integration Points (dependencies, cycle detection)             │    │
│  │  Pass 5: Atomic Breakdown (50-120 atoms, ≤10 LOC each)                  │    │
│  │  Pass 6: Validation & Optimization (Tarjan's algorithm)                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 4: ATOMIZATION               v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Break into atomic generation units with SemanticTaskSignatures          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 5: DAG CONSTRUCTION          v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  DAGBuilder ──> Neo4j storage ──> Execution waves                       │    │
│  │  Cycle detection, topological sort, parallelization levels              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 6: CODE GENERATION           v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  CodeGenerationService.generate_from_application_ir()                   │    │
│  │       │                                                                  │    │
│  │       ├──> PatternBank search (≥60% similarity)                         │    │
│  │       ├──> CPIE inference (pattern or first-principles)                 │    │
│  │       ├──> ProductionCodeGenerators (fallback)                          │    │
│  │       └──> BehaviorCodeGenerator (workflows, state machines)            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 6.5: IR TEST GENERATION      v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  generate_all_tests_from_ir() ──> test_validation_rules.py              │    │
│  │                              ──> test_integration_flows.py              │    │
│  │                              ──> test_api_contracts.py                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 6.6: IR SERVICE GENERATION   v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  generate_services_from_ir() ──> Service methods from BehaviorModelIR   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 7: DEPLOYMENT                v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Save files to output_path with stratum classification                  │    │
│  │  Record in generation_manifest.json                                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 8: CODE REPAIR               v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ComplianceValidator.validate_from_app()                                │    │
│  │       │                                                                  │    │
│  │       └──> If compliance < 100%:                                        │    │
│  │            CodeRepairAgent.repair() (AST patching, max 3 iterations)    │    │
│  │                 │                                                        │    │
│  │                 ├──> Add missing entities                               │    │
│  │                 ├──> Add missing endpoints                              │    │
│  │                 └──> Add missing validations                            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 9: VALIDATION                v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Structural validation (files exist, syntax valid)                      │    │
│  │  Semantic validation (ComplianceValidator)                              │    │
│  │  IR Compliance (STRICT + RELAXED modes)                                 │    │
│  │  UUID serialization validation                                          │    │
│  │  Run generated tests, calculate coverage                                │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 10: HEALTH VERIFICATION      v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Verify /health endpoints respond correctly                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│  Phase 11: LEARNING                 v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Pattern promotion pipeline (successful patterns → PatternBank)         │    │
│  │  Error patterns → ErrorPatternStore for learning                        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│                                     v                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    RUNNING APPLICATION                                   │    │
│  │    docker-compose up ──> FastAPI ──> PostgreSQL ──> Validated & Ready   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Spec Parsing Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPEC PARSING LAYER                            │
│                                                                  │
│  src/parsing/                                                    │
│  ├── spec_parser.py          # Main parser                       │
│  ├── structured_spec_parser.py # YAML/Markdown support          │
│  ├── entity_locator.py       # Entity extraction                │
│  ├── field_extractor.py      # Field extraction                 │
│  └── hierarchical_models.py  # Data structures                  │
│                                                                  │
│  src/specs/                                                      │
│  └── spec_to_application_ir.py # LLM-based IR extraction        │
│                                                                  │
│  Output: SpecRequirements + ApplicationIR                        │
└─────────────────────────────────────────────────────────────────┘
```

**SpecParser** (`src/parsing/spec_parser.py`):
- Parses markdown specifications
- Extracts functional/non-functional requirements (F1, NF1, etc.)
- Extracts entities with fields and constraints
- Extracts API endpoints

**SpecToApplicationIR** (`src/specs/spec_to_application_ir.py`):
- Uses Claude Sonnet for LLM extraction
- Produces complete ApplicationIR with 5 sub-models
- Caches IR as JSON (hash-based invalidation)

---

### 2. ApplicationIR (Single Source of Truth)

```
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION IR                               │
│               (src/cognitive/ir/)                                │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    ApplicationIR                           │  │
│  │  ├── app_id: UUID                                         │  │
│  │  ├── name: str                                            │  │
│  │  ├── description: str                                     │  │
│  │  │                                                         │  │
│  │  ├── domain_model: DomainModelIR ─────────────────────┐   │  │
│  │  │   ├── entities: List[Entity]                       │   │  │
│  │  │   │   ├── name, attributes, relationships          │   │  │
│  │  │   │   └── is_aggregate_root                        │   │  │
│  │  │   └── get_entity(name) -> Entity                   │   │  │
│  │  │                                                     │   │  │
│  │  ├── api_model: APIModelIR ───────────────────────────┤   │  │
│  │  │   ├── endpoints: List[Endpoint]                    │   │  │
│  │  │   │   ├── path, method, operation_id               │   │  │
│  │  │   │   ├── parameters, request_schema               │   │  │
│  │  │   │   └── inference_source (SPEC/CRUD/PATTERN)     │   │  │
│  │  │   └── get_endpoints_by_tag(tag) -> List            │   │  │
│  │  │                                                     │   │  │
│  │  ├── behavior_model: BehaviorModelIR ─────────────────┤   │  │
│  │  │   ├── flows: List[Flow]                            │   │  │
│  │  │   │   ├── name, type (WORKFLOW/STATE_TRANSITION)   │   │  │
│  │  │   │   ├── trigger, steps                           │   │  │
│  │  │   │   └── preconditions, postconditions            │   │  │
│  │  │   └── invariants: List[Invariant]                  │   │  │
│  │  │                                                     │   │  │
│  │  ├── validation_model: ValidationModelIR ─────────────┤   │  │
│  │  │   ├── rules: List[ValidationRule]                  │   │  │
│  │  │   │   ├── entity, attribute, type                  │   │  │
│  │  │   │   ├── condition, error_message                 │   │  │
│  │  │   │   ├── enforcement_type (CRITICAL!)             │   │  │
│  │  │   │   │   └── DESCRIPTION | VALIDATOR | COMPUTED   │   │  │
│  │  │   │   │       | IMMUTABLE | STATE_MACHINE          │   │  │
│  │  │   │   └── enforcement_code, applied_at             │   │  │
│  │  │   └── test_cases: List[Dict]                       │   │  │
│  │  │                                                     │   │  │
│  │  └── infrastructure_model: InfrastructureModelIR ─────┘   │  │
│  │      ├── database: DatabaseConfig                         │  │
│  │      ├── vector_db, graph_db                              │  │
│  │      ├── containers: List[ContainerService]               │  │
│  │      └── observability: ObservabilityConfig               │  │
│  │                                                            │  │
│  │  Convenience Methods:                                      │  │
│  │  ├── get_entities() -> List[Entity]                       │  │
│  │  ├── get_endpoints() -> List[Endpoint]                    │  │
│  │  ├── get_flows() -> List[Flow]                            │  │
│  │  ├── get_validation_rules() -> List[ValidationRule]       │  │
│  │  └── get_dag_nodes() -> List[Dict]                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Data Types**:

| IR | Enums | Key Fields |
|----|-------|------------|
| DomainModelIR | DataType, RelationshipType | Entity.attributes, Entity.relationships |
| APIModelIR | HttpMethod, ParameterLocation, InferenceSource | Endpoint.parameters, request_schema |
| ValidationModelIR | **ValidationType**, **EnforcementType** | rule.enforcement_type, enforcement_code |
| BehaviorModelIR | FlowType | Flow.steps, Invariant.expression |
| InfrastructureModelIR | DatabaseType | database, containers, observability |

---

### 3. Cognitive Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   COGNITIVE ARCHITECTURE                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MULTI-PASS PLANNER                           │   │
│  │         (src/cognitive/planning/multi_pass_planner.py)    │   │
│  │                                                           │   │
│  │  Pass 1: Requirements Analysis                            │   │
│  │  Pass 2: Architecture Design                              │   │
│  │  Pass 3: Contract Definition                              │   │
│  │  Pass 4: Integration Points (cycle detection)             │   │
│  │  Pass 5: Atomic Breakdown (50-120 atoms, ≤10 LOC)        │   │
│  │  Pass 6: Validation & Optimization (Tarjan's algorithm)   │   │
│  │                                                           │   │
│  │  Output: List[AtomicTask] with SemanticTaskSignatures     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              v                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              DAG BUILDER                                  │   │
│  │         (src/cognitive/planning/dag_builder.py)           │   │
│  │                                                           │   │
│  │  - Neo4j graph storage                                    │   │
│  │  - Cypher-based cycle detection                           │   │
│  │  - Topological sorting                                    │   │
│  │  - Parallelization level assignment                       │   │
│  │  - <1s query performance                                  │   │
│  │                                                           │   │
│  │  Output: Execution waves (tasks grouped by dependency)    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              v                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PATTERN BANK                                 │   │
│  │         (src/cognitive/patterns/pattern_bank.py)          │   │
│  │                                                           │   │
│  │  Storage: Qdrant vector database                          │   │
│  │  ├── semantic_patterns: 384-dim (Sentence-BERT)           │   │
│  │  └── devmatrix_patterns: 768-dim (GraphCodeBERT)          │   │
│  │                                                           │   │
│  │  Features:                                                │   │
│  │  ├── Pattern storage (≥95% success rate threshold)        │   │
│  │  ├── Semantic similarity search                           │   │
│  │  ├── Hybrid search (70% vector + 30% metadata)            │   │
│  │  ├── Adaptive thresholds by domain (CRUD: 0.60, etc.)     │   │
│  │  ├── Keyword fallback (TG5)                               │   │
│  │  └── DAG-based ranking (execution success history)        │   │
│  │                                                           │   │
│  │  Methods:                                                 │   │
│  │  ├── store_pattern(signature, code, success_rate)         │   │
│  │  ├── search_patterns(signature, top_k, threshold)         │   │
│  │  ├── search_with_fallback(signature, top_k, min_results)  │   │
│  │  └── hybrid_search(signature, domain, production_ready)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              v                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              CPIE (Cognitive Pattern Inference Engine)    │   │
│  │         (src/cognitive/inference/cpie.py)                 │   │
│  │                                                           │   │
│  │  Strategy:                                                │   │
│  │  1. Pattern matching from PatternBank (≥85% similarity)   │   │
│  │  2. First-principles generation (no pattern match)        │   │
│  │  3. Constraint validation (max 10 LOC, syntax, types)     │   │
│  │  4. Retry with enriched context (max 3 attempts)          │   │
│  │                                                           │   │
│  │  Co-Reasoning:                                            │   │
│  │  ├── Claude: Generate strategy                            │   │
│  │  └── DeepSeek: Implement code                             │   │
│  │                                                           │   │
│  │  Constraints:                                             │   │
│  │  ├── Max 10 LOC per atom                                  │   │
│  │  ├── Full type hints required                             │   │
│  │  ├── No TODO/FIXME comments                               │   │
│  │  └── Valid Python syntax                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. Stratified Generation

```
┌─────────────────────────────────────────────────────────────────┐
│                  STRATIFIED GENERATION                           │
│         (4 Strata: TEMPLATE → AST → LLM → QA)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STRATUM 1: TEMPLATE (Boilerplate - 0% LLM)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Files: docker-compose.yml, Dockerfile, requirements.txt   │  │
│  │         pyproject.toml, alembic.ini, prometheus.yml        │  │
│  │         core/config.py, core/database.py, routes/health.py │  │
│  │         models/base.py, main.py, README.md, .env           │  │
│  │                                                             │  │
│  │  Rule: If it can be templated and tested once,              │  │
│  │        it lives here forever.                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  STRATUM 2: AST (Deterministic from IR)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Files: models/entities.py, models/schemas.py              │  │
│  │         repositories/*, routes/*, alembic/versions/*       │  │
│  │                                                             │  │
│  │  Generation:                                                │  │
│  │  ├── DomainModelIR.entities → SQLAlchemy models            │  │
│  │  ├── APIModelIR.schemas → Pydantic schemas                 │  │
│  │  ├── APIModelIR.endpoints → FastAPI routes                 │  │
│  │  └── DomainModelIR → Alembic migrations                    │  │
│  │                                                             │  │
│  │  Rule: If information is in IR, use deterministic           │  │
│  │        transforms + AST.                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  STRATUM 3: LLM (Complex Business Logic)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Files: services/*_flow.py, services/*_business.py         │  │
│  │         services/*_custom.py, workflows/*, state_machines/ │  │
│  │                                                             │  │
│  │  Types:                                                     │  │
│  │  ├── Multi-entity workflows (checkout, registration)       │  │
│  │  ├── Complex invariants ("Cannot pay CANCELLED order")     │  │
│  │  ├── State machines (order status transitions)             │  │
│  │  ├── Repair patches (IR-guided fixes)                      │  │
│  │  └── Non-trivial DTO mappings                              │  │
│  │                                                             │  │
│  │  Rule: LLM is a discovery tool. Stable patterns            │  │
│  │        graduate to AST/Template.                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  STRATUM 4: QA (Validation)                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Files: tests/*, quality_gate.json                         │  │
│  │                                                             │  │
│  │  Layers:                                                    │  │
│  │  1. Structural: py_compile, AST parse, no pass-only        │  │
│  │  2. Database: alembic upgrade, tables, constraints         │  │
│  │  3. Contract: OpenAPI vs IR (strict/relaxed)               │  │
│  │  4. Smoke: docker-compose, health, happy path              │  │
│  │                                                             │  │
│  │  Rule: Every stratum validated deterministically            │  │
│  │        before acceptance.                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. Code Generation Services

```
┌─────────────────────────────────────────────────────────────────┐
│                   CODE GENERATION SERVICES                       │
│                   (src/services/)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CodeGenerationService (code_generation_service.py)             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Main orchestrator for code generation                     │  │
│  │                                                             │  │
│  │  Integrations:                                              │  │
│  │  ├── PatternBank: Production pattern retrieval             │  │
│  │  ├── ApplicationIRNormalizer: Template rendering           │  │
│  │  ├── PatternFeedbackIntegration: Pattern promotion         │  │
│  │  ├── DAGSynchronizer: Execution metrics                    │  │
│  │  ├── ModularArchitectureGenerator: File structure          │  │
│  │  └── BehaviorCodeGenerator: Workflows, state machines      │  │
│  │                                                             │  │
│  │  Methods:                                                   │  │
│  │  ├── generate_from_application_ir(app_ir) -> str           │  │
│  │  ├── generate_from_requirements(spec_req) -> str           │  │
│  │  └── generate_modular_app(spec_req) -> Dict[str, str]      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ProductionCodeGenerators (production_code_generators.py)       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Hardcoded generators for 100% correct code                │  │
│  │                                                             │  │
│  │  Functions:                                                 │  │
│  │  ├── generate_entities(entities, validation_gt) -> str     │  │
│  │  ├── generate_schemas(entities, validation_gt) -> str      │  │
│  │  ├── generate_config() -> str                              │  │
│  │  ├── generate_service_method(entity, method_type) -> str   │  │
│  │  ├── generate_initial_migration(entities) -> str           │  │
│  │  └── validate_generated_files(files) -> Dict[str, bool]    │  │
│  │                                                             │  │
│  │  Features:                                                  │  │
│  │  ├── Immutable field support (onupdate=None)               │  │
│  │  ├── Constraint handling (unique, nullable, FK)            │  │
│  │  ├── Create/Update schema exclusions                       │  │
│  │  └── Syntax validation                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  BehaviorCodeGenerator (behavior_code_generator.py)             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Generates from BehaviorModelIR:                           │  │
│  │  ├── Workflow implementations                              │  │
│  │  ├── State machine validators                              │  │
│  │  ├── Business rule validators                              │  │
│  │  └── Event handlers                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6. Validation & Repair

```
┌─────────────────────────────────────────────────────────────────┐
│                   VALIDATION & REPAIR                            │
│                   (src/validation/, src/mge/v2/agents/)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ComplianceValidator (compliance_validator.py)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Semantic validation of generated code vs specification    │  │
│  │                                                             │  │
│  │  Compliance Score:                                          │  │
│  │  ├── Entity compliance (40%): entities_found / expected    │  │
│  │  ├── Endpoint compliance (40%): endpoints_found / expected │  │
│  │  └── Validation compliance (20%): validations_found / exp  │  │
│  │                                                             │  │
│  │  Thresholds:                                                │  │
│  │  ├── MIN_ACCEPTABLE_COMPLIANCE: 65% (stops if below)       │  │
│  │  ├── COMPLIANCE_THRESHOLD: 80% (target)                    │  │
│  │  └── REPAIR_IMPROVEMENT_THRESHOLD: 85% (post-repair)       │  │
│  │                                                             │  │
│  │  Methods:                                                   │  │
│  │  ├── validate(spec_req, generated_code) -> ComplianceReport│  │
│  │  └── validate_from_app(spec_req, output_path) -> Report    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  CodeRepairAgent (code_repair_agent.py)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  AST-based targeted repairs (not full regeneration)        │  │
│  │                                                             │  │
│  │  Capabilities:                                              │  │
│  │  ├── Add missing entities to entities.py                   │  │
│  │  ├── Add missing endpoints to routes/*.py                  │  │
│  │  ├── Add missing validations to schemas.py                 │  │
│  │  ├── Preserve existing code                                │  │
│  │  └── Automatic rollback on failure                         │  │
│  │                                                             │  │
│  │  Modes:                                                     │  │
│  │  ├── IR-centric: Uses ApplicationIR (preferred)            │  │
│  │  └── Legacy: Uses spec_requirements                        │  │
│  │                                                             │  │
│  │  Methods:                                                   │  │
│  │  ├── repair(compliance_report, spec_req) -> RepairResult   │  │
│  │  ├── _repair_from_ir(compliance_report) -> RepairResult    │  │
│  │  ├── repair_missing_entity(entity) -> bool                 │  │
│  │  └── repair_missing_endpoint(endpoint) -> str              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure

### Database Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     NEO4J                                │    │
│  │              (DAGs + IR Persistence)                     │    │
│  │                                                          │    │
│  │  Data Stored:                                            │    │
│  │  ├── ApplicationIR (complete graph representation)       │    │
│  │  ├── AtomicTask nodes and dependencies                   │    │
│  │  ├── Execution traces with metrics                       │    │
│  │  └── Pattern → Task relationships                        │    │
│  │                                                          │    │
│  │  Queries:                                                │    │
│  │  ├── Cycle detection (Tarjan's algorithm)                │    │
│  │  ├── Topological sorting                                 │    │
│  │  └── Execution wave computation                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     QDRANT                               │    │
│  │              (Pattern Bank Vector Store)                 │    │
│  │                                                          │    │
│  │  Collections:                                            │    │
│  │  ├── semantic_patterns: 384-dim (Sentence-BERT)          │    │
│  │  │   └── Purpose: Semantic understanding                 │    │
│  │  └── devmatrix_patterns: 768-dim (GraphCodeBERT)         │    │
│  │      └── Purpose: Code-aware embeddings                  │    │
│  │                                                          │    │
│  │  Metadata:                                               │    │
│  │  ├── pattern_id, purpose, intent, domain                 │    │
│  │  ├── code, success_rate, usage_count                     │    │
│  │  ├── production_ready, production_readiness_score        │    │
│  │  └── test_coverage, security_level, docker_ready         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   POSTGRESQL                             │    │
│  │              (Application Data)                          │    │
│  │                                                          │    │
│  │  Generated Tables:                                       │    │
│  │  ├── {entity}_table for each DomainModelIR entity        │    │
│  │  ├── alembic_version for migrations                      │    │
│  │  └── Application-specific tables                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   REDIS (Optional)                       │    │
│  │              (Caching, Sessions)                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pattern Promotion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│               PATTERN PROMOTION PIPELINE                         │
│          (Auto-evolution: LLM → AST → TEMPLATE)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LLM generates code                                              │
│       │                                                          │
│       v                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 QA VALIDATION                            │    │
│  │  - Syntax valid?                                         │    │
│  │  - Tests pass?                                           │    │
│  │  - Compliance ≥95%?                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ├── FAIL ──> Discard, store error pattern for learning     │
│       │                                                          │
│       v PASS                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         STORE AS CANDIDATE IN PATTERNBANK                │    │
│  │  - Store with success_rate ≥0.95                         │    │
│  │  - Track usage_count                                     │    │
│  │  - Assign production_readiness_score                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       v                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         PATTERN REPEATS IN 3+ PROJECTS?                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ├── NO ──> Continue as LLM pattern                         │
│       │                                                          │
│       v YES                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         EXTRACT DETERMINISTIC RULE                       │    │
│  │  - Identify pattern structure                            │    │
│  │  - Create AST transformation rule                        │    │
│  │  - Add to ast_generators.py                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       v                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         NOW AST-BASED (No LLM needed)                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       v                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         PATTERN STABLE FOR 50+ USES?                     │    │
│  │         100% compliance, 0 regressions?                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ├── NO ──> Continue as AST pattern                         │
│       │                                                          │
│       v YES                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         PROMOTE TO TEMPLATE                              │    │
│  │  - Static, pre-tested, immutable                         │    │
│  │  - Never regenerated                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Promotion Criteria:                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Transition    │ Projects │ Compliance │ Regressions    │    │
│  │  ─────────────┼──────────┼────────────┼───────────────  │    │
│  │  LLM → AST    │    3+    │    100%    │      0         │    │
│  │  AST → TEMPL  │    5+    │    100%    │      0         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Execution Modes

| Mode | TEMPLATE | AST | LLM | PatternBank Write | Use Case |
|------|----------|-----|-----|-------------------|----------|
| **SAFE** | Yes | Yes | No | No | Production deployments |
| **HYBRID** | Yes | Yes | Yes (constrained) | Yes | Normal development |
| **RESEARCH** | Yes | Yes | Yes (free) | No (sandbox) | Experimentation |

**Environment Variables**:
```bash
EXECUTION_MODE=hybrid        # safe, hybrid, research
QA_LEVEL=fast               # fast, heavy
QUALITY_GATE_ENV=dev        # dev, staging, production
USE_REAL_CODE_GENERATION=true
MIN_ACCEPTABLE_COMPLIANCE=0.65
COMPLIANCE_THRESHOLD=0.80
REPAIR_IMPROVEMENT_THRESHOLD=0.85
```

---

## Quality Gate Policies

| Environment | Semantic | IR Relaxed | Warnings | Regressions |
|-------------|----------|------------|----------|-------------|
| **DEV** | ≥90% | ≥70% | Allowed | Allowed |
| **STAGING** | =100% | ≥85% | Blocked | Blocked |
| **PRODUCTION** | =100% | ≥95% | Blocked | Blocked + 10 runs |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| LLM calls per generation | ~50 | <10 |
| Infrastructure bugs | ~5% | 0% |
| Migration bugs | ~10% | 0% |
| Generation time | ~2.7min | <1min |
| Pattern reuse rate | ~30% | >60% |
| Regression rate | ~5% | 0% |
| Entity compliance | 95%+ | 100% |
| Endpoint compliance | 100% | 100% |
| Overall compliance | 90-98% | 99%+ |

---

## Key Files Reference

| Component | File | Purpose |
|-----------|------|---------|
| Spec Parser | `src/parsing/spec_parser.py` | Parse markdown specs |
| IR Extraction | `src/specs/spec_to_application_ir.py` | LLM-based IR extraction |
| ApplicationIR | `src/cognitive/ir/application_ir.py` | Root aggregate |
| DomainModelIR | `src/cognitive/ir/domain_model.py` | Entities, relationships |
| APIModelIR | `src/cognitive/ir/api_model.py` | Endpoints, schemas |
| ValidationModelIR | `src/cognitive/ir/validation_model.py` | Validation rules, enforcement |
| BehaviorModelIR | `src/cognitive/ir/behavior_model.py` | Flows, state machines |
| Multi-Pass Planner | `src/cognitive/planning/multi_pass_planner.py` | 6-pass planning |
| DAG Builder | `src/cognitive/planning/dag_builder.py` | Neo4j DAG construction |
| PatternBank | `src/cognitive/patterns/pattern_bank.py` | Qdrant pattern storage |
| CPIE | `src/cognitive/inference/cpie.py` | Pattern inference engine |
| Code Generation | `src/services/code_generation_service.py` | Main orchestrator |
| Prod Generators | `src/services/production_code_generators.py` | Hardcoded generators |
| Compliance | `src/validation/compliance_validator.py` | Semantic validation |
| Code Repair | `src/mge/v2/agents/code_repair_agent.py` | AST-based repair |
| E2E Pipeline | `tests/e2e/real_e2e_full_pipeline.py` | Full pipeline test |

---

## Related Documentation

- [03-CORE_ENGINE.md](03-CORE_ENGINE.md) - Cognitive engine details
- [04-IR_SYSTEM.md](04-IR_SYSTEM.md) - ApplicationIR architecture
- [05-CODE_GENERATION.md](05-CODE_GENERATION.md) - Generation pipeline
- [06-VALIDATION.md](06-VALIDATION.md) - Validation system
- [07-TESTING.md](07-TESTING.md) - E2E pipeline phases
- [11-COMPLETE_PIPELINE_REFERENCE.md](11-COMPLETE_PIPELINE_REFERENCE.md) - Exhaustive reference

---

*DevMatrix - System Architecture v3.0*
*Comprehensive Technical Documentation - November 2025*
