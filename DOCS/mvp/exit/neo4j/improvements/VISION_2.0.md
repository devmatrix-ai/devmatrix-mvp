# Strategic Database Architecture: DevMatrix Pipeline 2.0

> Propuesta de mejoras sustanciales para maximizar Neo4j, Qdrant y pgvector.
> Fecha: 2025-11-29

---

## 1. PROBLEMA FUNDAMENTAL

### 1.1 El Pipeline Actual es STATELESS

```
Spec → [Phase 1-11] → Generated App
         ↓
    (todo se pierde)
```

**Problemas:**
- Cada ejecución empieza de cero
- No hay memoria entre runs
- Los errores se repiten
- Las métricas no se acumulan
- No hay trazabilidad código → patrón → spec

### 1.2 Las Bases de Datos son SILOS

```
Neo4j ──────────── (30K patterns, no se usan)
    │
Qdrant ─────────── (21K patterns, búsqueda básica)
    │
pgvector ───────── (0% utilización)
```

**No hay:**
- Flujo de datos entre bases
- Estrategia unificada
- Aprovechamiento de fortalezas complementarias

---

## 2. VISION: PIPELINE CON MEMORIA

### 2.1 Arquitectura Propuesta

```
                    ┌─────────────────────────────────────────────┐
                    │           KNOWLEDGE GRAPH (Neo4j)           │
                    │                                             │
                    │  Spec ──→ ApplicationIR ──→ Generated Code  │
                    │   │            │                  │         │
                    │   └──→ Patterns Used ←──────────┘         │
                    │              │                              │
                    │         Error History                       │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │    Qdrant     │  │    Neo4j      │  │   pgvector    │
           │               │  │               │  │               │
           │ • Semantic    │  │ • Graph       │  │ • Time-series │
           │   Search      │  │   Traversal   │  │   Analytics   │
           │ • Similarity  │  │ • Lineage     │  │ • Anomalies   │
           │ • Real-time   │  │ • History     │  │ • Trends      │
           └───────────────┘  └───────────────┘  └───────────────┘
```

### 2.2 Principio Central: TRAZABILIDAD COMPLETA

```
Spec (hash)
  └──→ ApplicationIR (versioned)
        └──→ Pattern Used (id, similarity)
              └──→ Generated Code (file, content)
                    └──→ Test Result (pass/fail)
                          └──→ Error/Success (feedback)
```

**Cada decisión del pipeline queda registrada.**

---

## 3. ESTRATEGIA POR BASE DE DATOS

### 3.1 Neo4j: KNOWLEDGE GRAPH + LINEAGE

**Rol:** Grafo de conocimiento y trazabilidad completa.

#### Nuevo Schema Propuesto

```cypher
// === SPEC LINEAGE ===
(:Spec {hash, name, version, created_at})
  -[:PRODUCES]-> (:ApplicationIR {id, version})
    -[:HAS_ENTITY]-> (:Entity {name, attributes})
    -[:HAS_ENDPOINT]-> (:Endpoint {method, path})
    -[:HAS_FLOW]-> (:Flow {name, type})
    -[:HAS_VALIDATION]-> (:Validation {type, rule})

// === CODE GENERATION LINEAGE ===
(:ApplicationIR)
  -[:GENERATES]-> (:GeneratedFile {path, hash, created_at})
    -[:USED_PATTERN {similarity, ranking}]-> (:Pattern)
    -[:HAD_ERROR]-> (:Error {type, message, fixed_by})
    -[:PASSED_TEST]-> (:TestResult {name, duration})

// === PATTERN EVOLUTION ===
(:Pattern)
  -[:EVOLVED_FROM]-> (:Pattern)  // Pattern versioning
  -[:SIMILAR_TO {score}]-> (:Pattern)  // Cluster patterns
  -[:USED_IN]-> (:GeneratedFile)  // Usage tracking

// === EXECUTION HISTORY ===
(:PipelineRun {id, timestamp, duration, success})
  -[:PROCESSED]-> (:Spec)
  -[:GENERATED]-> (:GeneratedFile)
  -[:METRICS]-> (:RunMetrics {compliance, tokens, errors})
```

#### Queries Habilitados

```cypher
// ¿Qué patterns funcionaron para specs similares?
MATCH (s:Spec {hash: $hash})-[:PRODUCES]->(ir)-[:GENERATES]->(f)
      -[:USED_PATTERN]->(p:Pattern)
WHERE f.test_passed = true
RETURN p, count(*) as success_count
ORDER BY success_count DESC

// ¿Qué errores tuvo este tipo de endpoint antes?
MATCH (ep:Endpoint {method: 'POST', path: '/products'})
      <-[:HAS_ENDPOINT]-(ir)<-[:PRODUCES]-(s)
      -[:GENERATES]->(f)-[:HAD_ERROR]->(e:Error)
RETURN e.type, e.message, count(*) as frequency

// Lineage completo de un archivo generado
MATCH path = (s:Spec)-[:PRODUCES]->(ir)-[:GENERATES]->(f {path: $file})
              -[:USED_PATTERN]->(p)
RETURN path

// Patterns que nunca fallaron
MATCH (p:Pattern)
WHERE NOT (p)<-[:USED_PATTERN]-(:GeneratedFile)-[:HAD_ERROR]->()
RETURN p ORDER BY p.usage_count DESC
```

---

### 3.2 Qdrant: SEMANTIC SEARCH + REAL-TIME MATCHING

**Rol:** Búsqueda semántica rápida y matching en tiempo real.

#### Collections Propuestas

```yaml
devmatrix_patterns:  # Existente - 21K patterns
  vector: 768-dim GraphCodeBERT
  payload: pattern_id, name, code, language, framework
  uso: Búsqueda semántica de patterns

spec_signatures:  # NUEVO
  vector: 768-dim (spec content embedding)
  payload: spec_hash, name, ir_summary, entities, endpoints
  uso: Encontrar specs similares para transfer learning

error_embeddings:  # NUEVO (split de code_generation_feedback)
  vector: 768-dim (error context embedding)
  payload: error_id, type, message, context, fix_applied
  uso: Encontrar errores similares ANTES de generar

code_fragments:  # NUEVO
  vector: 768-dim (generated code embedding)
  payload: file_path, function_name, spec_hash, pattern_used
  uso: Detectar código duplicado, encontrar ejemplos similares
```

#### Flujos Propuestos

```python
# 1. ANTES de generar código para un endpoint
async def pre_generation_search(endpoint_spec):
    # Buscar errores similares
    similar_errors = await qdrant.search(
        collection="error_embeddings",
        query=embed(endpoint_spec),
        filter={"type": ["syntax", "validation"]},
        limit=5
    )

    # Buscar código exitoso similar
    similar_code = await qdrant.search(
        collection="code_fragments",
        query=embed(endpoint_spec),
        filter={"test_passed": True},
        limit=3
    )

    return {
        "avoid": [e.payload["fix_applied"] for e in similar_errors],
        "reference": [c.payload["code"] for c in similar_code]
    }

# 2. Transfer learning entre specs
async def find_similar_specs(new_spec_content):
    similar = await qdrant.search(
        collection="spec_signatures",
        query=embed(new_spec_content),
        limit=3
    )
    # Reusar IRs y patterns de specs similares
    return [s.payload["spec_hash"] for s in similar if s.score > 0.85]
```

---

### 3.3 pgvector: TIME-SERIES ANALYTICS + OPERATIONAL DATA

**Rol:** Analytics temporales, detección de anomalías, métricas operacionales.

#### Schema Propuesto

```sql
-- Pipeline executions con embeddings
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY,
    spec_hash VARCHAR(64),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    success BOOLEAN,

    -- Metrics
    compliance_score FLOAT,
    tokens_used INTEGER,
    duration_ms INTEGER,
    files_generated INTEGER,
    errors_count INTEGER,

    -- Embedding del spec para clustering
    spec_embedding vector(768),

    -- JSON flexible
    metrics JSONB,
    phases JSONB
);

-- Code generation events (time-series)
CREATE TABLE generation_events (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES pipeline_runs(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    phase VARCHAR(50),
    event_type VARCHAR(50),  -- 'start', 'complete', 'error', 'retry'

    -- Context embedding para anomaly detection
    context_embedding vector(768),

    details JSONB
);

-- Error patterns over time
CREATE TABLE error_trends (
    id SERIAL PRIMARY KEY,
    error_type VARCHAR(100),
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    occurrence_count INTEGER,

    -- Error signature embedding
    signature_embedding vector(768),

    -- Temporal analysis
    avg_time_to_fix_ms INTEGER,
    auto_fixed_count INTEGER
);

-- Indexes para analytics
CREATE INDEX idx_runs_spec ON pipeline_runs(spec_hash);
CREATE INDEX idx_runs_time ON pipeline_runs(started_at);
CREATE INDEX idx_events_run ON generation_events(run_id);
CREATE INDEX idx_errors_type ON error_trends(error_type);

-- Vector index para similarity
CREATE INDEX idx_runs_embedding ON pipeline_runs
    USING ivfflat (spec_embedding vector_cosine_ops);
```

#### Queries Analíticos

```sql
-- Tendencia de compliance por spec type
SELECT
    DATE_TRUNC('day', started_at) as day,
    AVG(compliance_score) as avg_compliance,
    COUNT(*) as runs
FROM pipeline_runs
WHERE started_at > NOW() - INTERVAL '30 days'
GROUP BY day
ORDER BY day;

-- Specs que consistentemente fallan (anomaly detection)
SELECT
    spec_hash,
    COUNT(*) as total_runs,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
    AVG(compliance_score) as avg_compliance
FROM pipeline_runs
GROUP BY spec_hash
HAVING AVG(compliance_score) < 0.7
ORDER BY total_runs DESC;

-- Encontrar runs similares a uno que falló
SELECT
    pr2.id,
    pr2.success,
    pr2.compliance_score,
    1 - (pr1.spec_embedding <=> pr2.spec_embedding) as similarity
FROM pipeline_runs pr1, pipeline_runs pr2
WHERE pr1.id = $failed_run_id
  AND pr2.id != pr1.id
  AND pr2.success = true
ORDER BY similarity DESC
LIMIT 5;

-- Error types trending up (early warning)
SELECT
    error_type,
    occurrence_count,
    last_seen,
    EXTRACT(EPOCH FROM (NOW() - last_seen)) / 3600 as hours_since
FROM error_trends
WHERE last_seen > NOW() - INTERVAL '24 hours'
ORDER BY occurrence_count DESC;
```

---

## 4. FLUJO DE DATOS INTEGRADO

### 4.1 Pre-Generation Intelligence

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRE-GENERATION PHASE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Spec Input                                                  │
│     │                                                           │
│     ▼                                                           │
│  2. [Qdrant] Find similar specs                                │
│     │         → Transfer patterns from successful specs         │
│     │                                                           │
│     ▼                                                           │
│  3. [Neo4j] Check spec history                                 │
│     │        → Previous runs, errors, successful patterns       │
│     │                                                           │
│     ▼                                                           │
│  4. [pgvector] Anomaly check                                   │
│     │           → Is this spec similar to failing patterns?     │
│     │                                                           │
│     ▼                                                           │
│  5. Enriched Context for Generation                            │
│     - Patterns to use (high success rate)                       │
│     - Patterns to avoid (caused errors)                         │
│     - Reference code (similar successful generations)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Generation-Time Tracking

```
┌─────────────────────────────────────────────────────────────────┐
│                    GENERATION PHASE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each file generated:                                       │
│                                                                 │
│  1. [Qdrant] Search best patterns                              │
│     │                                                           │
│     ▼                                                           │
│  2. [Neo4j] Record: File -[:USED_PATTERN]-> Pattern            │
│     │                                                           │
│     ▼                                                           │
│  3. Generate code with LLM                                      │
│     │                                                           │
│     ▼                                                           │
│  4. [pgvector] Log generation event                            │
│     │                                                           │
│     ▼                                                           │
│  5. If error:                                                   │
│     - [Neo4j] Create Error node, link to File                  │
│     - [Qdrant] Store error embedding                           │
│     - [pgvector] Update error_trends                           │
│                                                                 │
│  6. If success:                                                 │
│     - [Neo4j] Mark File as successful                          │
│     - [Qdrant] Store code fragment embedding                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Post-Generation Learning

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEARNING PHASE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. [Neo4j] Update Pattern statistics                          │
│     - Increment usage_count                                     │
│     - Update success_rate based on test results                 │
│     - Create EVOLVED_FROM if pattern was modified               │
│                                                                 │
│  2. [Qdrant] Promote successful patterns                       │
│     - If pattern success_rate >= 95%, add to devmatrix_patterns │
│     - Update similarity clusters                                │
│                                                                 │
│  3. [pgvector] Store run analytics                             │
│     - Full metrics for trend analysis                           │
│     - Embedding for similar-run queries                         │
│                                                                 │
│  4. [Neo4j] Complete lineage graph                             │
│     - Spec -> IR -> Files -> Tests -> Results                   │
│     - Full audit trail for debugging                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. IMPLEMENTACION POR FASES

### Phase 1: Foundation (Sprint 1)

```
[ ] Neo4j: Crear schema de lineage
    - Spec, ApplicationIR, GeneratedFile nodes
    - PRODUCES, GENERATES relationships

[ ] Qdrant: Crear collection spec_signatures
    - Embed specs al ingresar
    - Buscar specs similares

[ ] pgvector: Crear tabla pipeline_runs
    - Logging básico de cada ejecución
```

**Entregable:** Trazabilidad básica Spec → IR → Files

---

### Phase 2: Pre-Generation Intelligence (Sprint 2)

```
[ ] Qdrant: Crear collection error_embeddings
    - Split de code_generation_feedback
    - Indexar errores históricos

[ ] Neo4j: Pattern usage tracking
    - USED_PATTERN relationships
    - Success/failure counts

[ ] Pipeline: Integrar pre-generation search
    - Buscar errores similares antes de generar
    - Incluir context en prompts
```

**Entregable:** El pipeline aprende de errores pasados

---

### Phase 3: Real-Time Tracking (Sprint 3)

```
[ ] pgvector: Crear tabla generation_events
    - Time-series de eventos
    - Context embeddings

[ ] Neo4j: Error lineage
    - Error nodes con fixes aplicados
    - Link Error -> Pattern que lo causó

[ ] Qdrant: code_fragments collection
    - Indexar código generado exitoso
    - Detectar duplicados
```

**Entregable:** Visibilidad completa del proceso de generación

---

### Phase 4: Analytics & Optimization (Sprint 4)

```
[ ] pgvector: Dashboards de tendencias
    - Compliance over time
    - Error patterns trending

[ ] Neo4j: Pattern optimization
    - Identify best patterns per domain
    - Prune low-performing patterns

[ ] Qdrant: Transfer learning
    - Reusar patterns entre specs similares
    - Auto-clustering de patterns
```

**Entregable:** Sistema auto-optimizante

---

## 6. METRICAS DE EXITO

### 6.1 Efficiency Metrics

| Métrica | Actual | Target |
|---------|--------|--------|
| IR extraction time (cached) | 30s | <1s |
| Pattern search latency | 200ms | <50ms |
| Error repeat rate | ~40% | <10% |
| First-pass success | ~60% | >85% |

### 6.2 Quality Metrics

| Métrica | Actual | Target |
|---------|--------|--------|
| Pattern reuse rate | 0% | >60% |
| Lineage completeness | 0% | 100% |
| Cross-spec learning | None | Active |
| Anomaly detection | None | Real-time |

### 6.3 Operational Metrics

| Métrica | Actual | Target |
|---------|--------|--------|
| Runs tracked | 0 | 100% |
| Error categorization | Manual | Automatic |
| Trend visibility | None | 30-day window |
| Debug time | Hours | Minutes |

---

## 7. RIESGOS Y MITIGACIONES

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Overhead de tracking | +latency | Async writes, batch inserts |
| Schema migrations | Downtime | Versioned schemas, blue-green |
| Storage growth | Costs | Retention policies, archiving |
| Query complexity | Bugs | Comprehensive testing, monitoring |

---

## 8. RESUMEN EJECUTIVO

### Cambio de Paradigma

```
ANTES: Pipeline stateless, cada run independiente
DESPUES: Pipeline con memoria, aprendizaje continuo
```

### Uso Estratégico por DB

| Database | Fortaleza | Uso en DevMatrix |
|----------|-----------|------------------|
| **Neo4j** | Relaciones | Lineage, trazabilidad, pattern graph |
| **Qdrant** | Velocidad | Search pre-gen, similarity real-time |
| **pgvector** | ACID + SQL | Analytics, trends, operational data |

### Quick Wins Inmediatos

1. **IR Cache en Neo4j** → -30% tiempo Phase 1
2. **Error search pre-gen** → -50% repair iterations
3. **Pattern usage tracking** → Visibility + optimization data

### Beneficio Principal

```
El pipeline APRENDE de cada ejecución.
Los errores no se repiten.
Los patterns exitosos se propagan.
Todo es trazable y auditable.
```

---

*Documento generado: 2025-11-29*
*Proyecto: DevMatrix/Agentic-AI*
