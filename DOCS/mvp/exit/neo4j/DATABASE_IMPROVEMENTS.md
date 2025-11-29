# Database Improvements: Maximizing Neo4j, Qdrant & pgvector in DevMatrix Pipeline

> Analisis de gaps y oportunidades de mejora para el pipeline E2E.
> Basado en: `tests/e2e/real_e2e_full_pipeline.py`
> Fecha: 2025-11-29

---

## 1. Estado Actual del Pipeline

### 1.1 Fases del Pipeline

```
Phase 1    → Spec Ingestion + ApplicationIR Extraction
Phase 1.5  → Validation Scaling (BusinessLogicExtractor)
Phase 2    → Requirements Analysis + Classification
Phase 3    → Multi-Pass Planning (DAG inference)
Phase 4    → Atomization
Phase 5    → DAG Construction (SIMULADA)
Phase 6    → Code Generation
Phase 7    → Deployment
Phase 8    → Code Repair Loop
Phase 8.5  → Runtime Smoke Tests
Phase 9    → Validation
Phase 10   → Health Verification
Phase 11   → Learning (Pattern Storage)
```

### 1.2 Uso Actual de Databases

| Database | Componente | Fase | Estado |
|----------|------------|------|--------|
| **Qdrant** | PatternBank.search_with_fallback | Phase 2 | ✅ USADO |
| **Qdrant** | ErrorPatternStore (errors) | Phase 8 | ✅ USADO |
| **Qdrant** | PatternFeedbackIntegration | Phase 11 | ✅ USADO |
| **Neo4j** | ErrorPatternStore (graph) | Phase 8 | ⚠️ PARCIAL |
| **Neo4j** | DAGBuilder | Phase 5 | ❌ NO USADO |
| **Neo4j** | neo4j_ir_repository | - | ❌ NO USADO |
| **Neo4j** | unified_retriever (RAG) | - | ❌ NO USADO |
| **pgvector** | - | - | ❌ NO USADO |

---

## 2. GAPS CRITICOS

### 2.1 🔴 Neo4j DAGBuilder NO SE USA

**Ubicacion:** `src/cognitive/planning/dag_builder.py`

**Problema:**
```python
# Phase 5 actual (real_e2e_full_pipeline.py:2419)
async def _phase_5_dag_construction(self):
    """Phase 5: DAG Construction"""
    # Solo simula checkpoints, NO usa DAGBuilder real
    for i in range(5):
        await asyncio.sleep(0.3)  # Simulacion!
```

**Capacidades desperdiciadas:**
- Deteccion de ciclos con Cypher
- Paralelizacion automatica de tareas independientes
- Persistencia de task dependencies
- Historial de ejecuciones previas

**Impacto:** No hay optimizacion real del orden de generacion de codigo.

---

### 2.2 🔴 ApplicationIR NO SE PERSISTE en Neo4j

**Ubicacion:** `src/cognitive/services/neo4j_ir_repository.py`

**Problema:**
```python
# El pipeline extrae ApplicationIR pero NO lo guarda
self.application_ir = await ir_extractor.extract(...)
# MISSING: neo4j_ir_repository.save(self.application_ir)
```

**Capacidades desperdiciadas:**
- Cache de IR entre ejecuciones
- Comparacion de IRs para detectar cambios
- Historial de specs procesados
- Relaciones entre domain models y endpoints

**Impacto:** Cada ejecucion re-extrae el IR desde cero (~30% del tiempo de pipeline).

---

### 2.3 🔴 unified_retriever (RAG Combinado) NO SE USA

**Ubicacion:** `src/rag/unified_retriever.py`

**Problema:**
```python
# Pipeline usa SOLO PatternBank (Qdrant)
results = self.pattern_bank.search_with_fallback(signature, top_k=10)

# DISPONIBLE pero no usado:
# unified_retriever combina:
# - Qdrant (0.7 weight) → semantic patterns
# - Neo4j (0.3 weight) → graph relationships
```

**Capacidades desperdiciadas:**
- Patrones relacionados via graph traversal
- Ranking combinado (semantic + structural)
- 30,071 nodos de patrones en Neo4j ignorados
- Dependencias entre patrones

**Impacto:** Solo usa 21,624 patrones de Qdrant, ignora relaciones de Neo4j.

---

### 2.4 🟡 Error Learning Loop INCOMPLETO

**Ubicacion:** `src/services/error_pattern_store.py`

**Estado actual:**
```python
# Phase 8 guarda errores
await self.error_pattern_store.store_error(error_pattern)

# Phase 8 guarda exitos
await self.error_pattern_store.store_success(success_pattern)

# PERO: No se consultan errores similares ANTES de generar codigo
# find_similar_errors() existe pero no se llama
```

**Capacidades desperdiciadas:**
- Evitar errores conocidos ANTES de generacion
- Aplicar fixes historicos automaticamente
- Trending de tipos de errores
- Correlacion error → fix exitoso

**Impacto:** El pipeline repite los mismos errores sin aprender.

---

### 2.5 🟡 pgvector COMPLETAMENTE IGNORADO

**Estado:**
- Extension instalada en PostgreSQL
- Tablas de logs creadas (JSONB, no Vector)
- NO se usa para embeddings ni similarity

**Oportunidades perdidas:**
- Audit trail con embeddings para anomaly detection
- Vectores transaccionales (ACID)
- Query embeddings + execution context en una operacion

---

## 3. MEJORAS PROPUESTAS

### 3.1 🚀 Integrar DAGBuilder Real en Phase 5

**Cambio:**
```python
# ANTES
async def _phase_5_dag_construction(self):
    for i in range(5):
        await asyncio.sleep(0.3)  # Simulacion

# DESPUES
async def _phase_5_dag_construction(self):
    from src.cognitive.planning.dag_builder import DAGBuilder

    dag_builder = DAGBuilder(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password
    )

    # Crear nodos de tareas atomicas
    for unit in self.atomic_units:
        dag_builder.create_task_node(
            task_id=unit["id"],
            name=unit["name"],
            domain=unit.get("domain", "general")
        )

    # Crear dependencias (de Phase 3)
    for edge in self.inferred_edges:
        dag_builder.create_dependency(edge["from"], edge["to"])

    # Detectar ciclos
    cycles = dag_builder.detect_cycles()
    if cycles:
        raise ValueError(f"Ciclos detectados: {cycles}")

    # Obtener orden de ejecucion optimizado
    self.execution_order = dag_builder.get_execution_waves()
```

**Beneficio:** Paralelizacion real, deteccion de ciclos, historial.

---

### 3.2 🚀 Persistir ApplicationIR en Neo4j

**Cambio:**
```python
# En Phase 1, despues de extraer IR
from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository

ir_repo = Neo4jIRRepository()

# Verificar si ya existe (cache)
cached_ir = await ir_repo.load_by_spec_hash(spec_hash)
if cached_ir and not FORCE_IR_REFRESH:
    self.application_ir = cached_ir
    print("  ✅ ApplicationIR loaded from Neo4j cache")
else:
    self.application_ir = await ir_extractor.extract(...)
    await ir_repo.save(self.application_ir, spec_hash)
    print("  ✅ ApplicationIR extracted and cached in Neo4j")
```

**Beneficio:**
- Skip extraction si spec no cambio (~30% tiempo)
- Historial de IRs para comparacion
- Relaciones entre specs y sus modelos

---

### 3.3 🚀 Usar unified_retriever para RAG Combinado

**Cambio:**
```python
# ANTES
results = self.pattern_bank.search_with_fallback(signature, top_k=10)

# DESPUES
from src.rag.unified_retriever import UnifiedRetriever

retriever = UnifiedRetriever()
results = await retriever.retrieve(
    query=signature.purpose,
    top_k=10,
    weights={"qdrant": 0.7, "neo4j": 0.3}
)
# Ahora incluye:
# - Patrones semanticamente similares (Qdrant)
# - Patrones relacionados por dependencias (Neo4j graph)
```

**Beneficio:**
- Acceso a 30,071 patrones de Neo4j
- Relaciones de dependencia informan el ranking
- Diversidad de resultados (no solo similitud)

---

### 3.4 🚀 Error Learning ANTES de Generar

**Cambio:**
```python
# En Phase 6, ANTES de generar codigo para cada archivo
async def _generate_file_with_learning(self, file_spec):
    # 1. Buscar errores similares ANTES de generar
    similar_errors = await self.error_pattern_store.find_similar_errors(
        task_description=file_spec["description"],
        limit=3
    )

    # 2. Si hay errores conocidos, incluir en el prompt
    error_context = ""
    if similar_errors:
        error_context = "\n".join([
            f"AVOID: {e.error_message} (similar task failed with: {e.failed_code[:100]})"
            for e in similar_errors
        ])

    # 3. Buscar fixes exitosos para errores similares
    successful_fixes = await self.error_pattern_store.find_successful_patterns(
        task_description=file_spec["description"],
        limit=2
    )

    # 4. Generar con contexto enriquecido
    code = await self.code_generator.generate(
        spec=file_spec,
        avoid_patterns=error_context,
        reference_patterns=[p.generated_code for p in successful_fixes]
    )
```

**Beneficio:**
- Evita errores conocidos proactivamente
- Usa fixes historicos como referencia
- Reduce iterations del repair loop

---

### 3.5 🚀 pgvector para Operational Analytics

**Propuesta:**
```python
# Agregar columna vector a logs
ALTER TABLE code_generation_logs
ADD COLUMN embedding vector(768);

# En cada generacion, guardar embedding del prompt
async def log_generation(self, prompt, result, metrics):
    embedding = self.embedding_model.encode(prompt)

    await db.execute("""
        INSERT INTO code_generation_logs
        (timestamp, prompt, result, metrics, embedding)
        VALUES ($1, $2, $3, $4, $5)
    """, datetime.now(), prompt, result, metrics, embedding)

# Detectar anomalias (prompts muy diferentes a historicos)
async def detect_anomaly(self, new_prompt):
    embedding = self.embedding_model.encode(new_prompt)

    similar = await db.execute("""
        SELECT AVG(1 - (embedding <=> $1)) as avg_similarity
        FROM code_generation_logs
        WHERE timestamp > NOW() - INTERVAL '7 days'
    """, embedding)

    if similar.avg_similarity < 0.5:
        logger.warning(f"Anomaly detected: prompt very different from recent history")
```

**Beneficio:**
- Anomaly detection en prompts
- ACID con embeddings
- Time-series analysis de patrones

---

## 4. MATRIZ DE PRIORIDADES

| Mejora | Impacto | Esfuerzo | Prioridad |
|--------|---------|----------|-----------|
| DAGBuilder real en Phase 5 | Alto | Medio | 🔴 P1 |
| ApplicationIR cache en Neo4j | Alto | Bajo | 🔴 P1 |
| unified_retriever para RAG | Alto | Bajo | 🔴 P1 |
| Error learning pre-generation | Medio | Medio | 🟡 P2 |
| pgvector operational analytics | Bajo | Alto | 🟢 P3 |

---

## 5. METRICAS ESPERADAS

### 5.1 Con DAGBuilder Real
- **Paralelizacion:** +40% throughput en generacion
- **Deteccion ciclos:** 100% (vs 0% actual)
- **Historial:** Reuso de DAGs exitosos

### 5.2 Con IR Cache en Neo4j
- **Tiempo Phase 1:** -30% (skip extraction)
- **Storage:** ~5KB por spec (vs re-compute)
- **Comparacion:** Diff automatico entre versiones

### 5.3 Con unified_retriever
- **Patrones accesibles:** 30,071 + 21,624 (vs solo 21,624)
- **Relevancia:** +15% (relaciones de dependencia)
- **Diversidad:** Patrones estructuralmente relacionados

### 5.4 Con Error Learning Pre-Gen
- **Repair iterations:** -50% estimado
- **First-pass success:** +20% estimado
- **Knowledge reuse:** Errores no se repiten

---

## 6. IMPLEMENTACION SUGERIDA

### 6.1 Sprint 1: Quick Wins (P1)

```
[ ] Integrar unified_retriever en Phase 2
    - Archivo: tests/e2e/real_e2e_full_pipeline.py:2134
    - Cambio: Reemplazar pattern_bank.search_with_fallback por unified_retriever

[ ] Agregar IR cache en Phase 1
    - Archivo: tests/e2e/real_e2e_full_pipeline.py (Phase 1)
    - Nuevo: Llamar neo4j_ir_repository.save() despues de extraction

[ ] Activar DAGBuilder en Phase 5
    - Archivo: tests/e2e/real_e2e_full_pipeline.py:2419
    - Cambio: Reemplazar simulacion por DAGBuilder real
```

### 6.2 Sprint 2: Error Learning (P2)

```
[ ] Pre-generation error check
    - Archivo: CodeGenerationService o Phase 6
    - Nuevo: find_similar_errors() antes de generate()

[ ] Fix reference injection
    - Nuevo: find_successful_patterns() para enriquecer prompts
```

### 6.3 Sprint 3: Analytics (P3)

```
[ ] pgvector schema migration
    - Archivo: scripts/setup_test_database.py
    - Nuevo: ALTER TABLE para columnas vector

[ ] Anomaly detection service
    - Nuevo: src/services/anomaly_detector.py
```

---

## 7. ARQUITECTURA OBJETIVO

```
                         ┌─────────────────────────────────────┐
                         │         DevMatrix Pipeline          │
                         └─────────────────┬───────────────────┘
                                           │
        ┌──────────────────────────────────┼──────────────────────────────────┐
        │                                  │                                  │
        ▼                                  ▼                                  ▼
┌───────────────┐                 ┌───────────────┐                 ┌───────────────┐
│    Neo4j      │                 │    Qdrant     │                 │   pgvector    │
│               │                 │               │                 │               │
│ • DAG Tasks   │◄───────────────►│ • Patterns    │                 │ • Audit Logs  │
│ • IR Cache    │  unified_       │ • Errors      │                 │ • Embeddings  │
│ • Pattern     │  retriever      │ • Feedback    │                 │ • Anomalies   │
│   Relations   │                 │               │                 │               │
└───────┬───────┘                 └───────┬───────┘                 └───────┬───────┘
        │                                 │                                 │
        │      ┌──────────────────────────┴────────────────────────┐       │
        │      │                                                   │       │
        ▼      ▼                                                   ▼       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              Unified Data Layer                                   │
│                                                                                  │
│  • RAG retrieval (semantic + graph)                                              │
│  • Error learning (pre-generation + post-mortem)                                 │
│  • IR caching (skip re-extraction)                                               │
│  • DAG optimization (parallel execution)                                         │
│  • Operational analytics (anomaly detection)                                     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

*Documento generado: 2025-11-29*
*Proyecto: DevMatrix/Agentic-AI*
