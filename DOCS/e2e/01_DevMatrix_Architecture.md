# Arquitectura Completa de DevMatrix

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura de Sistema](#arquitectura-de-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Datos](#flujo-de-datos)
5. [Tecnologías](#tecnologías)

---

## Visión General

**DevMatrix** es un sistema de generación automática de código production-ready que transforma especificaciones en markdown a aplicaciones completas usando un pipeline cognitivo de 7 fases.

### Características Clave

- 🧠 **Cognitivo**: Usa GraphCodeBERT para clasificación semántica
- 📚 **Aprendizaje**: Pattern Bank que mejora con el tiempo
- 🔄 **Autorreparación**: Code Repair automático con feedback loops
- ✅ **Validación**: 100% compliance con la spec original
- 🚀 **Production-Ready**: Apps listas para producción desde el primer momento

### Arquitectura de Alto Nivel

```mermaid
graph TB
    subgraph "📄 Input Layer"
        MD[Markdown Spec<br/>Functional + Non-Functional Requirements]
    end

    subgraph "🧠 Processing Layer - Pipeline Cognitivo"
        direction TB

        subgraph "Phase 1-2: Understanding"
            SP[SpecParser<br/>Extrae entities, endpoints, business logic]
            RC[RequirementsClassifier<br/>GraphCodeBERT + Keyword Matching]
        end

        subgraph "Phase 3: Pattern Recognition"
            PB[PatternBank<br/>Semantic Patterns DB]
            PC[PatternClassifier<br/>Match requirements → patterns]
        end

        subgraph "Phase 4: Planning"
            MP[MultiPassPlanner<br/>Genera plan de implementación]
            DB[DAGBuilder<br/>Dependency Graph]
        end

        subgraph "Phase 5: Generation"
            CG[CodeGenerationService<br/>LLM + Templates]
            MAG[ModularArchitectureGenerator<br/>Estructura modular]
        end

        subgraph "Phase 6: Quality"
            CR[CodeRepairAgent<br/>Auto-fix errors]
            EP[ErrorPatternStore<br/>Aprende de errores]
        end

        subgraph "Phase 7: Validation"
            CV[ComplianceValidator<br/>Verifica 100% cumplimiento]
        end
    end

    subgraph "📦 Output Layer"
        APP[Production App<br/>FastAPI + PostgreSQL + Docker]
    end

    subgraph "💾 Storage Layer"
        QD[(Qdrant<br/>Vector DB<br/>Patterns)]
        N4[(Neo4j<br/>Graph DB<br/>Dependencies)]
    end

    MD --> SP
    SP --> RC
    RC --> PC
    PC --> PB
    PB --> MP
    MP --> DB
    DB --> CG
    CG --> MAG
    MAG --> CR
    CR --> EP
    EP --> CV
    CV --> APP

    PB <--> QD
    DB <--> N4
    EP <--> QD

    style MD fill:#4A90E2,stroke:#2E5C8A,color:#FFFFFF,stroke-width:3px
    style APP fill:#50C878,stroke:#2E7D4E,color:#FFFFFF,stroke-width:3px
    style SP fill:#FF6B6B,stroke:#CC5555,color:#FFFFFF,stroke-width:2px
    style RC fill:#FF6B6B,stroke:#CC5555,color:#FFFFFF,stroke-width:2px
    style PB fill:#FFD93D,stroke:#CCA830,color:#000000,stroke-width:2px
    style PC fill:#FFD93D,stroke:#CCA830,color:#000000,stroke-width:2px
    style MP fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style DB fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style CG fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:2px
    style MAG fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:2px
    style CR fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style EP fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style CV fill:#16A085,stroke:#117A65,color:#FFFFFF,stroke-width:2px
    style QD fill:#95A5A6,stroke:#7F8C8D,color:#FFFFFF,stroke-width:2px
    style N4 fill:#95A5A6,stroke:#7F8C8D,color:#FFFFFF,stroke-width:2px
```

---

## Arquitectura de Sistema

### Capas del Sistema

```mermaid
graph TB
    subgraph "🔴 Presentation Layer"
        CLI[CLI Interface<br/>real_e2e_full_pipeline.py]
        API[FastAPI Endpoints<br/>Future: Web UI]
    end

    subgraph "🟠 Service Layer"
        direction LR

        subgraph "Parsing Services"
            SPS[SpecParser]
            RCS[RequirementsClassifier]
        end

        subgraph "Pattern Services"
            PBS[PatternBank]
            PCS[PatternClassifier]
            PFI[PatternFeedbackIntegration]
        end

        subgraph "Planning Services"
            MPS[MultiPassPlanner]
            DBS[DAGBuilder]
            DSS[DAGSynchronizer]
        end

        subgraph "Generation Services"
            CGS[CodeGenerationService]
            MAGS[ModularArchitectureGenerator]
            PGS[ProductionCodeGenerators]
        end

        subgraph "Quality Services"
            CRA[CodeRepairAgent]
            EPS[ErrorPatternStore]
            CVS[ComplianceValidator]
        end
    end

    subgraph "🟡 Domain Layer"
        direction LR

        subgraph "Models"
            REQ[Requirement]
            ENT[Entity]
            ENDP[Endpoint]
            PAT[Pattern]
        end

        subgraph "Signatures"
            STS[SemanticTaskSignature]
            SS[SemanticSignature]
        end
    end

    subgraph "🟢 Infrastructure Layer"
        direction LR

        subgraph "AI/ML"
            GCBERT[GraphCodeBERT<br/>Singleton]
            LLM[EnhancedAnthropicClient<br/>Claude Sonnet]
        end

        subgraph "Storage"
            QDR[(Qdrant<br/>Vector Store)]
            NEO[(Neo4j<br/>Graph Store)]
            PG[(PostgreSQL<br/>Metadata)]
        end

        subgraph "Observability"
            LOG[StructuredLogger<br/>structlog]
            MET[MetricsCollector<br/>Prometheus]
        end
    end

    CLI --> SPS
    API --> SPS

    SPS --> RCS
    RCS --> PCS
    PCS --> PBS
    PBS --> MPS
    MPS --> DBS
    DBS --> CGS
    CGS --> MAGS
    MAGS --> CRA
    CRA --> CVS

    PBS --> PFI
    CRA --> EPS

    RCS --> GCBERT
    CGS --> LLM

    PBS --> QDR
    DBS --> NEO
    EPS --> QDR

    CGS --> LOG
    CGS --> MET

    style CLI fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style QDR fill:#8E44AD,stroke:#6C3483,color:#FFFFFF,stroke-width:2px
    style NEO fill:#8E44AD,stroke:#6C3483,color:#FFFFFF,stroke-width:2px
    style GCBERT fill:#F39C12,stroke:#D68910,color:#FFFFFF,stroke-width:2px
    style LLM fill:#F39C12,stroke:#D68910,color:#FFFFFF,stroke-width:2px
```

---

## Componentes Principales

### 1. SpecParser
**Archivo:** `src/parsing/spec_parser.py`

**Responsabilidades:**
- Parsear markdown specs con estructura flexible
- Extraer entities con fields, types, constraints
- Identificar endpoints (method, path, params)
- Detectar business logic y validaciones

**Output Example:**
```python
Entity(
    name="Product",
    fields=[
        Field(name="id", type="UUID", primary_key=True),
        Field(name="price", type="Decimal", constraints=["gt=0"])
    ]
)
```

### 2. RequirementsClassifier
**Archivo:** `src/classification/requirements_classifier.py`

**Enfoque Híbrido:**
1. Keyword matching (baseline rápido)
2. GraphCodeBERT embeddings (semantic)
3. Domain templates (CRUD, Auth, Payment, etc.)

**Performance:** 90%+ accuracy, ~5s processing

### 3. PatternBank
**Archivo:** `src/cognitive/patterns/pattern_bank.py`

**Categories:**
- Production (database, config, logging)
- Testing (pytest, fixtures, integration)
- Security (sanitization, rate limiting)
- Observability (metrics, health checks)

**Storage:** Qdrant vector DB

### 4. CodeGenerationService
**Archivo:** `src/services/code_generation_service.py`

**Estrategia:**
- Templates Jinja2 para estructura
- Claude LLM para lógica compleja
- Production generators (hardcoded) para calidad

**Features:**
- Retry logic exponential backoff
- Token usage tracking
- Code validation

---

## Flujo de Datos

```mermaid
sequenceDiagram
    participant USER as Usuario
    participant SP as SpecParser
    participant RC as RequirementsClassifier
    participant PB as PatternBank
    participant CG as CodeGenerationService
    participant CR as CodeRepairAgent
    participant CV as ComplianceValidator

    USER->>SP: spec.md
    SP->>SP: Extract entities/endpoints
    SP-->>RC: SpecRequirements

    RC->>RC: Classify (GraphCodeBERT)
    RC-->>PB: Classified Requirements

    PB->>PB: Match patterns (Qdrant)
    PB-->>CG: Matched Patterns

    CG->>CG: Generate code (LLM)
    CG-->>CR: Generated Files

    CR->>CR: Run tests & repair
    CR-->>CV: Repaired Code

    CV->>CV: Validate compliance
    CV-->>USER: ✅ Production App

    style SP fill:#FF6B6B,stroke:#CC5555,color:#FFFFFF
    style RC fill:#FFD93D,stroke:#CCA830,color:#000000
    style PB fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF
    style CG fill:#3498DB,stroke:#2874A6,color:#FFFFFF
    style CR fill:#E74C3C,stroke:#C0392B,color:#FFFFFF
    style CV fill:#16A085,stroke:#117A65,color:#FFFFFF
```

---

## Tecnologías

| Layer | Tecnología | Uso |
|-------|------------|-----|
| **AI/ML** | GraphCodeBERT | Embeddings semánticos |
| **AI/ML** | Claude Sonnet 4.5 | Generación de código |
| **Storage** | Qdrant | Vector DB patterns |
| **Storage** | Neo4j | Dependency graphs |
| **Framework** | FastAPI | Apps generadas |
| **ORM** | SQLAlchemy async | Database access |
| **Testing** | pytest | Unit + integration |
| **Observability** | structlog + Prometheus | Logging + metrics |

---

**Continuar leyendo:** [02_Pipeline_Flow.md](02_Pipeline_Flow.md)
