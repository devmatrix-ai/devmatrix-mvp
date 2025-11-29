# Database Architecture: Neo4j, Qdrant & pgvector

> Documentacion de la arquitectura polyglot de bases de datos del proyecto DevMatrix/Agentic-AI.
> Fecha: 2025-11-29
> **Actualizado**: 2025-11-29 (datos actualizados post-Sprint 0-2)

## Resumen Ejecutivo

El proyecto usa una **arquitectura polyglot** optimizada para diferentes concerns:

| Database | Rol Principal | Datos Verificados (Post-Sprint 0-2) |
|----------|---------------|-------------------|
| **Neo4j** | Grafos + Relaciones | 31,811 patterns, 280 IRs expandidos, 43,065 nodos totales |
| **Qdrant** | Busqueda Semantica | 30,126 patterns + 1,056 feedback (768-dim) |
| **pgvector** | Vectores ACID | Schema con IVFFlat listo, 1 registro |

---

## 1. Neo4j - Graph Database

### 1.1 Configuracion

```bash
# Credenciales
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devmatrix123
NEO4J_DATABASE=neo4j

# Puertos
HTTP:  7474  # Browser UI
BOLT:  7687  # Driver protocol

# Container
docker: neo4j:5.26-community
plugins: APOC
```

### 1.2 Estadísticas de Nodos (Actualizado Post-Sprint 0-2)

```
┌─────────────────────────┬─────────┬──────────────────────────┐
│ Label                   │ Count   │ Sprint                   │
├─────────────────────────┼─────────┼──────────────────────────┤
│ Pattern                 │ 31,811  │ Pre-existing             │
│ Attribute               │  5,204  │ Sprint 1 (Domain Model)  │
│ Endpoint                │  4,022  │ Sprint 2 (API Model)     │
│ Entity                  │  1,084  │ Sprint 1 (Domain Model)  │
│ SuccessfulCode          │    850  │ Pre-existing             │
│ APIParameter            │    668  │ Sprint 2 (API Model)     │
│ CodeGenerationError     │    523  │ Pre-existing             │
│ DomainModelIR           │    280  │ Sprint 0-1               │
│ BehaviorModel           │    280  │ Pre-existing             │
│ APIModelIR              │    280  │ Sprint 0-2               │
│ ValidationModel         │    280  │ Pre-existing             │
│ InfrastructureModel     │    280  │ Pre-existing             │
│ ApplicationIR           │    278  │ Sprint 0                 │
│ Dependency              │    168  │ Pre-existing             │
│ AtomicTask              │    100  │ Pre-existing             │
│ EnforcementStrategy     │     80  │ Pre-existing             │
│ ValidationRule          │     80  │ Pre-existing             │
│ Tag                     │     42  │ Pre-existing             │
│ Category                │     26  │ Pre-existing             │
├─────────────────────────┼─────────┼──────────────────────────┤
│ TOTAL NODOS             │ 46,636  │                          │
└─────────────────────────┴─────────┴──────────────────────────┘

**Expansión Sprint 0-2:**
- Sprint 0: ApplicationIR schema cleanup (278 apps)
- Sprint 1: DomainModelIR → Entity (1,084) + Attribute (5,204) = 6,288 nodos
- Sprint 2: APIModelIR → Endpoint (4,022) + APIParameter (668) = 4,690 nodos
- **Total agregado:** ~11,000 nodos nuevos
```

### 1.3 Relaciones (Actualizado Post-Sprint 0-2)

```
┌─────────────────────────┬─────────┬──────────────────────────┐
│ Relationship Type       │ Count   │ Sprint                   │
├─────────────────────────┼─────────┼──────────────────────────┤
│ CO_OCCURS               │ 100,000 │ Pre-existing             │
│ HAS_TAG                 │  69,138 │ Pre-existing             │
│ IN_CATEGORY             │  30,168 │ Pre-existing             │
│ FROM_REPO               │  30,060 │ Pre-existing             │
│ USES_FRAMEWORK          │  30,060 │ Pre-existing             │
│ HAS_ATTRIBUTE           │   5,204 │ Sprint 1 (Entity→Attr)   │
│ HAS_PARAMETER           │   4,690 │ Sprint 2 (Endpoint→Param)│
│ HAS_ENTITY              │   1,084 │ Sprint 1 (Domain→Entity) │
│ HAS_ENDPOINT            │     280 │ Sprint 2 (API→Endpoint)  │
│ HAS_BEHAVIOR            │     278 │ Pre-existing             │
│ HAS_INFRASTRUCTURE      │     278 │ Pre-existing             │
│ HAS_API_MODEL           │     278 │ Pre-existing             │
│ HAS_DOMAIN_MODEL        │     278 │ Pre-existing             │
│ HAS_VALIDATION          │     278 │ Pre-existing             │
│ RELATES_TO              │     132 │ Sprint 1 (Entity rels)   │
│ DEPENDS_ON              │     115 │ Pre-existing             │
│ HAS_ENFORCEMENT         │      80 │ Pre-existing             │
├─────────────────────────┼─────────┼──────────────────────────┤
│ TOTAL EDGES             │ 270,925 │                          │
└─────────────────────────┴─────────┴──────────────────────────┘

**Expansión Sprint 0-2:**
- Sprint 1: +6,420 edges (HAS_ENTITY, HAS_ATTRIBUTE, RELATES_TO)
- Sprint 2: +4,970 edges (HAS_ENDPOINT, HAS_PARAMETER)
- **Total agregado:** ~11,400 edges nuevos
```

### 1.4 Pattern Node Schema

```yaml
Pattern:
  # Identificación
  pattern_id: string           # UUID único
  name: string                 # Nombre del patrón
  hash: string                 # Content hash

  # Código
  code: string                 # Código fuente completo
  loc: integer                 # Lines of code
  complexity: float            # Complejidad computada

  # Clasificación
  pattern_type: string         # function, class, module
  language: string             # python, javascript
  framework: string            # fastapi, react
  category: string             # utilities, auth

  # Embeddings (dual)
  code_embedding_dim: 768
  semantic_embedding_dim: 768
  dual_embedding_version: string
  embedding_generation_time_ms: integer

  # ML Classification
  classification_method: string
  classification_confidence: float
  classification_reasoning: string
  cluster_id: string
  performance_tier: string     # high, medium, low
  security_level: string
```

### 1.5 Application IR Graph (Expandido en Sprint 0-2)

```yaml
ApplicationIR (278 nodos) - Sprint 0
├── app_id: uuid
├── name: string
├── version: string
├── ir_version: string
├── phase_status: string
└── Relaciones:
    ├── [:HAS_DOMAIN_MODEL] → DomainModelIR (280) - Sprint 1 Expandido
    │   └── [:HAS_ENTITY] → Entity (1,084)
    │       ├── [:HAS_ATTRIBUTE] → Attribute (5,204)
    │       └── [:RELATES_TO] → Entity (132 edges)
    │
    ├── [:HAS_API_MODEL] → APIModelIR (280) - Sprint 2 Expandido
    │   └── [:HAS_ENDPOINT] → Endpoint (4,022)
    │       └── [:HAS_PARAMETER] → APIParameter (668)
    │
    ├── [:HAS_BEHAVIOR] → BehaviorModel (280) - JSON (Sprint 3+ pendiente)
    ├── [:HAS_VALIDATION] → ValidationModel (280) - JSON (Sprint 4+ pendiente)
    └── [:HAS_INFRASTRUCTURE] → InfrastructureModel (280) - JSON (Sprint 6+ pendiente)

**Progreso de Expansión:**
- ✅ Sprint 0: ApplicationIR root nodes
- ✅ Sprint 1: DomainModelIR → Entity → Attribute (grafo completo)
- ✅ Sprint 2: APIModelIR → Endpoint → Parameter (grafo completo)
- ⏳ Sprint 3: BehaviorModelIR → Flow → Step (pendiente)
- ⏳ Sprint 4: ValidationModelIR → Rule (pendiente)
- ⏳ Sprint 5: TestsModelIR → TestScenario → SeedData (pendiente)
- ⏳ Sprint 6: InfrastructureModelIR → Service → Container (pendiente)
```

### 1.6 Error/Success Tracking

```yaml
SuccessfulCode (850 nodos):
  success_id: string
  task_id: string
  task_description: string
  generated_code: string
  quality_score: float         # 0.0 - 1.0
  timestamp: datetime

CodeGenerationError (523 nodos):
  error_id: string
  task_id: string
  task_description: string
  failed_code: string
  error_type: string           # SyntaxError, ImportError
  error_message: string
  attempt: integer
  timestamp: datetime
```

### 1.7 AtomicTask (DAG)

```yaml
AtomicTask (100 nodos):
  task_id: string
  dag_id: string               # Parent DAG
  name: string
  purpose: string
  intent: string
  task_type: string
  domain: string
  category: string
  framework: string
  level: integer               # DAG depth
  complexity: float
  max_loc: integer
  pattern_id: string           # Linked pattern

# Relación: [:DEPENDS_ON] → AtomicTask (115 edges)
```

### 1.8 Archivos Clave

| Archivo | Proposito |
|---------|-----------|
| `src/cognitive/infrastructure/neo4j_client.py` | Cliente principal |
| `src/cognitive/infrastructure/neo4j_schema.py` | Schema management |
| `src/cognitive/services/neo4j_ir_repository.py` | IR persistence |
| `src/cognitive/planning/dag_builder.py` | DAG construction |
| `src/services/error_pattern_store.py` | Error tracking |
| `src/rag/unified_retriever.py` | RAG (peso 0.3) |

---

## 2. Qdrant - Vector Database

### 2.1 Configuracion

```bash
# Conexion
QDRANT_HOST=localhost
QDRANT_PORT=6333      # HTTP API
QDRANT_GRPC_PORT=6334 # gRPC

# Container
docker: qdrant/qdrant:latest
```

### 2.2 Collections (Verificado)

| Collection | Registros | Vector Dim | Distancia |
|------------|-----------|------------|-----------|
| `devmatrix_patterns` | **30,126** | 768 | Cosine |
| `semantic_patterns` | **48** | 768 | Cosine |
| `code_generation_feedback` | **1,056** | 768 | Cosine |

### 2.3 devmatrix_patterns Schema

```json
{
  "id": "uuid",
  "vector": [768 floats],
  "payload": {
    "pattern_id": "next.js_function_bytelength_...",
    "name": "byteLength",
    "code": "function byteLength(str) { ... }",
    "pattern_type": "function",
    "language": "javascript",
    "framework": "nextjs",
    "domain": "utilities",
    "category": "utilities"
  }
}
```

### 2.4 semantic_patterns Schema (High-Value)

```json
{
  "id": "uuid",
  "vector": [768 floats],
  "payload": {
    "pattern_id": "repo_pattern_001",
    "purpose": "Repository pattern for SQLAlchemy",
    "intent": "async crud operations with transactions",
    "domain": "data_access",
    "code": "class BaseRepository: ...",
    "success_rate": 0.96,
    "usage_count": 802,
    "production_ready": true
  }
}
```

### 2.5 code_generation_feedback Schema

```json
// Success entries
{
  "success_id": "uuid",
  "task_id": "task-456",
  "task_description": "Create auth endpoint",
  "generated_code": "@router.post('/auth')...",
  "quality_score": 1.0,
  "type": "success"
}

// Error entries
{
  "error_id": "uuid",
  "task_id": "task-789",
  "task_description": "Create validation",
  "failed_code": "def validate...",
  "error_type": "ImportError",
  "error_message": "No module named...",
  "attempt": 1,
  "type": "error"
}
```

### 2.6 Archivos Clave

| Archivo | Proposito |
|---------|-----------|
| `src/cognitive/infrastructure/qdrant_client.py` | Cliente principal |
| `src/cognitive/patterns/pattern_bank.py` | Storage (95% threshold) |
| `src/services/error_pattern_store.py` | Error similarity |
| `src/cognitive/patterns/pattern_feedback_integration.py` | Feedback loop |
| `src/rag/unified_retriever.py` | RAG (peso 0.7) |

---

## 3. pgvector - PostgreSQL Extension

### 3.1 Configuracion

```bash
# Conexion
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix

# Container
docker: pgvector/pgvector:pg16

# Extension
pgvector version: 0.8.1
```

### 3.2 Tabla: pattern_embeddings (Verificado)

```sql
CREATE TABLE pattern_embeddings (
    pattern_id                VARCHAR(255) PRIMARY KEY,
    neo4j_node_id             VARCHAR(255) UNIQUE,
    code_embedding            VECTOR(768),
    semantic_embedding        VECTOR(768),
    dual_embedding_version    VARCHAR(50) DEFAULT 'v1_dual',
    pattern_name              TEXT,
    pattern_type              VARCHAR(50),
    language                  VARCHAR(50),
    framework                 VARCHAR(100),
    category                  VARCHAR(100),
    classification_confidence DOUBLE PRECISION,
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- IVFFlat indexes para búsqueda vectorial
CREATE INDEX idx_pattern_code_embedding
    ON pattern_embeddings USING ivfflat (code_embedding vector_cosine_ops)
    WITH (lists='100');

CREATE INDEX idx_pattern_semantic_embedding
    ON pattern_embeddings USING ivfflat (semantic_embedding vector_cosine_ops)
    WITH (lists='100');
```

**Estado:** Schema completo con indexes, **1 registro** (infraestructura lista).

### 3.3 Otras Tablas PostgreSQL

| Tabla | Registros | Proposito |
|-------|-----------|-----------|
| pattern_embeddings | 1 | Vector storage (ACID) |
| masterplans | 22 | Planning data |
| masterplan_phases | - | Phase breakdowns |
| masterplan_tasks | - | Task definitions |
| projects | 0 | Project registry |
| tasks | 0 | Task registry |
| agent_decisions | 0 | Decision logging |
| cost_tracking | 0 | Cost analytics |

---

## 4. Arquitectura de Integracion

### 4.1 Flujo de Datos

```
                    ┌─────────────────┐
                    │  User Request   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │     Qdrant      │           │     Neo4j       │
    │   (peso 0.7)    │           │   (peso 0.3)    │
    │  30,126 vectors │           │  31,811 nodes   │
    └────────┬────────┘           └────────┬────────┘
             │                             │
             └──────────────┬──────────────┘
                            ▼
                   ┌─────────────────┐
                   │  Weighted Merge │
                   │  + Deduplication│
                   └────────┬────────┘
                            ▼
                   ┌─────────────────┐
                   │     Results     │
                   └─────────────────┘
```

### 4.2 RAG Retrieval Weights

```python
# src/rag/unified_retriever.py
RETRIEVAL_WEIGHTS = {
    "qdrant": 0.7,    # Primary - semantic similarity
    "neo4j": 0.3,     # Secondary - graph relationships
    "chromadb": 0.0   # Disabled
}
```

### 4.3 Matriz de Decision

| Requerimiento | Neo4j | Qdrant | pgvector |
|---------------|:-----:|:------:|:--------:|
| Busqueda semantica | - | **++** | + |
| Relaciones de grafos | **++** | - | - |
| ACID transactions | **+** | - | **++** |
| Deteccion de ciclos | **++** | - | - |
| Filtrado metadata | + | **++** | + |
| Performance vectores | - | **++** | + |
| Knowledge base (30K+) | **++** | **++** | + |

**Leyenda**: `++` excelente, `+` bueno, `-` no aplica

---

## 5. Estadisticas de Datos (Verificado 2025-11-29)

### 5.1 Neo4j

| Tipo | Count | Descripcion |
|------|-------|-------------|
| Pattern | 31,811 | Patrones de código |
| Application | 278 | IRs completos |
| SuccessfulCode | 850 | Generaciones exitosas |
| CodeGenerationError | 523 | Errores registrados |
| AtomicTask | 100 | Tareas DAG |
| CO_OCCURS | 100,000 | Pattern co-occurrence |
| HAS_TAG | 69,138 | Pattern tags |

### 5.2 Qdrant

| Collection | Count | Descripcion |
|------------|-------|-------------|
| devmatrix_patterns | 30,126 | Pattern embeddings |
| semantic_patterns | 48 | High-value patterns |
| code_generation_feedback | 1,056 | Learning data |

### 5.3 pgvector

| Tabla | Count | Descripcion |
|-------|-------|-------------|
| pattern_embeddings | 1 | Dual vectors (ready) |
| masterplans | 22 | Planning data |

---

## 6. Troubleshooting

### 6.1 Neo4j

```bash
# Verificar conexion (HTTP API recomendado)
curl -s -u neo4j:devmatrix123 http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"RETURN 1"}]}'

# Estadisticas
curl -s -u neo4j:devmatrix123 http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN labels(n)[0], count(n)"}]}'

# Browser UI
http://localhost:7474
```

### 6.2 Qdrant

```bash
# Health check
curl http://localhost:6333/health

# Collections
curl http://localhost:6333/collections

# Collection stats
curl http://localhost:6333/collections/devmatrix_patterns
```

### 6.3 PostgreSQL

```bash
# Conectar
PGPASSWORD=devmatrix psql -h localhost -U devmatrix -d devmatrix

# Verificar pgvector
SELECT extversion FROM pg_extension WHERE extname = 'vector';

# Ver tablas
\dt
```

---

## 7. Variables de Entorno

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devmatrix123
NEO4J_DATABASE=neo4j

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix
```

---

*Documento generado: 2025-11-29*
*Última verificación: 2025-11-29 (query directa a DBs)*
*Proyecto: DevMatrix/Agentic-AI*
