# Análisis de Sprints 6-8 (Avanzados)

> **Lineage, Real-Time Tracking, Analytics**
> **Fecha**: 2025-11-29

---

## Sprint 6 — Lineage & Intelligence

**Estado**: PENDIENTE
**Prerrequisitos**: Sprints 2.5-5 completados

### Diseño Conceptual ✅

| Componente | Estado |
|------------|--------|
| Spec → IR → File lineage | ✅ Perfecto |
| Pattern usage tracking | ✅ Bien pensado |
| Error embeddings | ✅ |
| Pre-generation context builder | ✅ |

### Gap Crítico: FullIRGraphLoader

**Problema**: Plan no incluye cargador completo de IR desde Neo4j

```yaml
Esto es INDISPENSABLE para:
  - QA: Cargar IR completo para validar contra generado
  - Reparación: Cargar IR, modificar, regenerar
  - Regeneración parcial: Cargar subset del IR
  - Iteración: Cargar IR, aplicar feedback, guardar
  - Evaluación científica: Comparar IRs entre versiones
```

### Componente Requerido

```python
# File: src/cognitive/services/full_ir_graph_loader.py

class FullIRGraphLoader:
    """Carga ApplicationIR completo desde Neo4j"""

    async def load_application_ir(self, app_id: str) -> ApplicationIR:
        """
        Carga TODOS los sub-IRs:
        - DomainModelIR (entities, attributes, relationships)
        - APIModelIR (endpoints, parameters, schemas)
        - BehaviorModelIR (flows, steps, invariants)
        - ValidationModelIR (rules, test cases, enforcement)
        - InfrastructureModelIR (database, containers, observability)
        - TestsModelIR (suites, scenarios, seeds, assertions)

        Returns: ApplicationIR completamente hidratado
        """

    async def load_domain_model_ir(self, domain_id: str) -> DomainModelIR:
        """Carga solo DomainModelIR con todas sus entidades"""

    async def load_api_model_ir(self, api_id: str) -> APIModelIR:
        """Carga solo APIModelIR con todos sus endpoints"""

    async def load_partial_ir(
        self,
        app_id: str,
        components: list[str]  # ["domain", "api", "behavior"]
    ) -> PartialApplicationIR:
        """Carga solo componentes específicos"""
```

### Uso en QA

```python
# QA Workflow
loader = FullIRGraphLoader()
ir_from_graph = await loader.load_application_ir(app_id)
ir_from_spec = spec_parser.parse(spec_file)

# Compare
diff = ir_comparator.compare(ir_from_graph, ir_from_spec)
if diff.has_differences():
    report_precision_issues(diff)
```

**Prioridad**: 🔴 CRÍTICO para QA científico
**Esfuerzo**: 2-3 days

---

## Sprint 7 — Real-Time Tracking

**Estado**: PENDIENTE

### Diseño Base ✅

| Componente | Estado |
|------------|--------|
| Code fragment embeddings | ✅ |
| Event logs | ✅ |
| Error lineage | ✅ |

### Gaps: Formalización de Eventos

**Problema**: Plan no especifica qué eventos rastrear

### Tipos de Eventos Requeridos

```yaml
1. Pattern Selection:
   PATTERN_SELECTED:
     pattern_id: string
     confidence: float
     context: string
     alternatives: list[string]

2. Planner Decision:
   PLANNER_DECISION:
     phase: string
     decision: string
     reasoning: string
     alternatives_considered: list[string]

3. Validation Failure:
   VALIDATION_FAIL:
     validator: string
     rule: string
     expected: string
     actual: string
     severity: string

4. Repair Attempt:
   REPAIR_ATTEMPT:
     error_id: string
     strategy: string
     iteration: integer
     success: boolean

5. Retry:
   RETRY:
     operation: string
     attempt_number: integer
     reason: string
     backoff_ms: integer

6. Cost Accumulated:
   COST_ACCUMULATED:
     model: string
     tokens_in: integer
     tokens_out: integer
     cost_usd: float

7. Code Fragment Generated:
   CODE_FRAGMENT_GENERATED:
     file_path: string
     function_name: string
     lines: integer
     pattern_used: string
```

### Relación con Archivos Generados

**Problema**: Plan no especifica cómo vincular eventos con archivos

```cypher
-- Modelo requerido
(Event)-[:ASSOCIATED_WITH]->(GeneratedFile)
(Event)-[:TRIGGERED_BY]->(PreviousEvent)
(Event)-[:DURING_PHASE]->(Phase)

-- Queries habilitadas
"¿Qué eventos ocurrieron durante generación de auth/service.py?"
"¿Qué archivos fueron afectados por VALIDATION_FAIL event X?"
"¿Cuántos retries hubo para este archivo?"
```

**Prioridad**: 🟡 MEDIUM
**Esfuerzo**: 4-6 hours (design) + implementation

---

## Sprint 8 — Analytics & Optimization

**Estado**: PENDIENTE

### Evaluación: ✅ Correcto y ambicioso

El plan para Sprint 8 está bien pensado:

| Componente | Estado | Comentario |
|------------|--------|------------|
| Pattern performance analytics | ✅ | Excelente |
| Success rate tracking | ✅ | Necesario para ML |
| Cost optimization | ✅ | Business critical |
| Transfer learning | ✅ | Ambicioso, correcto |

### Sin gaps significativos

Sprint 8 es el sprint final de analytics y no tiene gaps arquitectónicos críticos. Los componentes propuestos son:

1. **Pattern Performance Dashboard**
   - Success rate por pattern
   - Tiempo de generación promedio
   - Costo por pattern

2. **Optimization Engine**
   - Pattern selection ML model
   - Cost-aware routing
   - Quality prediction

3. **Transfer Learning**
   - Cross-app pattern learning
   - Domain adaptation
   - Few-shot improvements

**Recomendación**: Ejecutar como está planificado después de Sprints 6-7.

---

## Dependencias entre Sprints Avanzados

```
Sprint 5 (TestsModelIR)
    │
    ▼
Sprint 6 (Lineage)
    │ Requiere:
    │ - FullIRGraphLoader
    │ - Todos los edges de Sprints 3-5
    │
    ▼
Sprint 7 (Real-Time Tracking)
    │ Requiere:
    │ - Event schema
    │ - File→Event linking
    │
    ▼
Sprint 8 (Analytics)
    │ Requiere:
    │ - Todos los datos de Sprint 6-7
    │ - Suficiente volumen para ML
```

---

## Resumen de Componentes Faltantes

| Sprint | Componente | Prioridad | Esfuerzo |
|--------|------------|-----------|----------|
| 6 | FullIRGraphLoader | 🔴 CRÍTICO | 2-3 days |
| 7 | Event types schema | 🟡 MEDIUM | 4-6h |
| 7 | Event→File linking | 🟡 MEDIUM | 2-3h |
| 8 | - | ✅ Sin gaps | - |

---

*Ver también*: [ACTION_PLAN.md](./ACTION_PLAN.md) para timeline completo
