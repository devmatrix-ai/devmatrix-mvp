# Learning Gaps Implementation Plan

**Fecha:** 2025-11-29
**Estado:** ✅ COMPLETO (7/7 Gaps Implementados)
**Prioridad:** Alta - Bloqueante para Pattern Promotion

---

## Executive Summary

El sistema de learning actual tiene gaps críticos que impiden la promoción de patterns.
Este plan detalla las implementaciones necesarias para cerrar el ciclo de feedback.

### Progreso de Implementación

| Gap | Descripción | Estado |
|-----|-------------|--------|
| 1 | Active Learning (ErrorKnowledge) | ✅ COMPLETO |
| 2 | Requirements Classifier Learning | ✅ COMPLETO |
| 3 | Neo4j Pattern Mining | ✅ COMPLETO |
| 4 | Code Repair Fix Pattern Learning | ✅ COMPLETO |
| 5 | IR-to-Code Failure Correlation | ✅ COMPLETO |
| 6 | Spec Ingestion Learning | ✅ COMPLETO |
| 7 | Validation Constraint Learning | ✅ COMPLETO |

### Estado Actual vs Deseado

| Métrica | Actual | Target |
|---------|--------|--------|
| Pattern Promotion Rate | 0% | >30% |
| Smoke Test Pass Rate | 47.7% | >80% |
| Learning Feedback Loops | 7/7 | 7/7 |
| Cross-Phase Correlation | 0% | 100% |

---

## Gap Analysis

### Gap 1: Smoke Test → Pattern Feedback (CRÍTICO)

**Problema:**
- Smoke tests fallan (47.7%) pero NO retroalimentan al sistema de patterns
- El score de promoción queda en 0.00 porque no hay feedback negativo/positivo
- Patterns se quedan en "pending" indefinidamente

**Evidencia:**
```
⏳ Pattern b4956871... pending (score: 0.00 < 0.7)
Promotion check complete: 0/1 promoted
```

**Impacto:** BLOQUEANTE - Sin esto, el sistema nunca aprende

**Solución Propuesta:**

```python
# src/validation/smoke_test_feedback.py (NUEVO)

class SmokeTestFeedback:
    """Connects smoke test results to pattern feedback system."""

    def __init__(self, feedback_integration: PatternFeedbackIntegration):
        self.feedback = feedback_integration

    async def process_smoke_results(
        self,
        smoke_result: SmokeTestResult,
        generation_manifest: dict
    ):
        """Process smoke test results and update pattern scores."""

        # Map each failed endpoint to the pattern that generated it
        for violation in smoke_result.violations:
            endpoint = violation['endpoint']
            pattern_id = self._find_pattern_for_endpoint(endpoint, generation_manifest)

            if pattern_id:
                await self.feedback.record_negative_feedback(
                    pattern_id=pattern_id,
                    failure_type="smoke_test_500",
                    endpoint=endpoint,
                    error_details=violation
                )

        # Record positive feedback for passing endpoints
        for passed in smoke_result.passed_scenarios:
            pattern_id = self._find_pattern_for_endpoint(passed['endpoint'], generation_manifest)

            if pattern_id:
                await self.feedback.record_positive_feedback(
                    pattern_id=pattern_id,
                    success_type="smoke_test_pass",
                    endpoint=passed['endpoint']
                )
```

**Integración en Pipeline:**
```python
# real_e2e_full_pipeline.py - Phase 8.5 (Runtime Smoke Test)

# DESPUÉS de ejecutar smoke tests:
if self.feedback_integration:
    smoke_feedback = SmokeTestFeedback(self.feedback_integration)
    await smoke_feedback.process_smoke_results(
        smoke_result=smoke_result,
        generation_manifest=self.generation_manifest
    )
    print(f"    📊 Feedback recorded: {len(smoke_result.violations)} negative, {len(smoke_result.passed_scenarios)} positive")
```

**Archivos a Modificar:**
- `src/validation/smoke_test_feedback.py` (NUEVO)
- `src/cognitive/patterns/pattern_feedback_integration.py` (agregar record_negative_feedback, record_positive_feedback)
- `tests/e2e/real_e2e_full_pipeline.py` (integrar en Phase 8.5)

**Esfuerzo:** 4-6 horas
**Dependencias:** Ninguna

---

### Gap 2: Requirements Classifier Learning

**Estado: COMPLETO** ✅

**Implementación (2025-11-29):**

1. **RequirementsClassifierTrainer** (`src/classification/requirements_classifier_trainer.py`):
   - `record_result()` - Registra predicción vs resultado real
   - `should_retrain()` - Verifica si se necesita reentrenamiento
   - `fine_tune_classifier()` - Fine-tuning con samples acumulados
   - `get_performance_report()` - Métricas de rendimiento
   - `load_misclassified_from_neo4j()` - Carga samples para batch retraining

2. **Data Classes**:
   - `ClassificationSample` - Record de clasificación individual
   - `ClassifierMetrics` - Métricas de rendimiento (accuracy, confusion matrix)

3. **Fine-tuning Features**:
   - Actualiza domain templates con embeddings de samples correctos
   - Extrae keywords de samples misclasificados
   - Weighted embedding updates (80% old, 20% new)
   - Threshold configurable (min 30 samples o accuracy < 60%)

4. **Persistencia**:
   - Samples almacenados en Neo4j (ClassificationSample nodes)
   - Métricas guardadas en ClassifierMetrics node
   - In-memory fallback cuando Neo4j no está disponible

**Uso:**
```python
from src.classification.requirements_classifier_trainer import get_classifier_trainer

trainer = get_classifier_trainer()
trainer.set_classifier(classifier)

# Después de cada clasificación
trainer.record_result(
    requirement_text="Create a new product",
    predicted_domain="crud",
    actual_domain="crud"
)

# Check si necesita retraining
if trainer.should_retrain():
    results = trainer.fine_tune_classifier()

# Ver métricas
report = trainer.get_performance_report()
print(f"Accuracy: {report['accuracy']}")
```

**Archivos Creados:**
- `src/classification/requirements_classifier_trainer.py` ✅

**Integración Pendiente:**
- Conectar con pipeline E2E para auto-registro de resultados
- Ground truth auto-generation basado en validación final

---

### Gap 3: Neo4j Pattern Mining

**Estado: COMPLETO** ✅

**Implementación (2025-11-29):**

1. **PatternMiningService** (`src/cognitive/services/pattern_mining_service.py`):
   - `get_failure_patterns()` - Endpoints/entities con alta tasa de fallas
   - `get_success_patterns()` - Fix patterns con alta confianza
   - `get_entity_error_profiles()` - Perfil de errores por entidad
   - `get_fix_strategy_effectiveness()` - Efectividad de estrategias de fix
   - `get_error_distribution()` - Distribución de tipos de error
   - `generate_learning_report()` - Reporte completo con insights y recomendaciones
   - `get_mining_statistics()` - Estadísticas de datos disponibles

2. **Data Classes**:
   - `FailurePattern` - Pattern de falla recurrente
   - `SuccessPattern` - Pattern de éxito reutilizable
   - `EntityErrorProfile` - Perfil de errores por entidad
   - `ComplexityCorrelation` - Correlación complejidad-éxito
   - `LearningReport` - Reporte completo con insights

3. **Cypher Queries** (6 queries optimizados):
   - `FAILURE_PATTERNS_QUERY` - ErrorKnowledge con ≥2 ocurrencias
   - `SUCCESS_PATTERNS_QUERY` - FixPattern con ≥70% confianza
   - `ENTITY_ERROR_PROFILE_QUERY` - Agrupación por entity_type
   - `FIX_STRATEGY_EFFECTIVENESS_QUERY` - Efectividad por estrategia
   - `ERROR_TYPE_DISTRIBUTION_QUERY` - Distribución de error_type
   - `PATTERN_CATEGORY_SUCCESS_QUERY` - Éxito por pattern_category

4. **Insights automáticos**:
   - Identifica endpoints más problemáticos
   - Recomienda estrategias de fix más efectivas
   - Detecta concentración de errores por entidad
   - Sugiere templates personalizados para entidades problemáticas

**Uso:**
```python
from src.cognitive.services.pattern_mining_service import get_pattern_mining_service

service = get_pattern_mining_service()
report = service.generate_learning_report()
print(f"Insights: {report.insights}")
print(f"Recommendations: {report.recommendations}")
```

**Archivos Creados:**

- `src/cognitive/services/pattern_mining_service.py` ✅

---

### Gap 4: Code Repair Fix Pattern Learning

**Estado: COMPLETO** ✅

**Implementación (2025-11-29):**

1. **FixPattern Dataclass** (`src/services/error_pattern_store.py`):
   - `fix_id`, `error_signature`, `error_type`, `error_message`
   - `fix_strategy`: "add_import", "fix_type_uuid", "llm_repair", etc.
   - `fix_code`: Full fixed file content
   - `success_count`, `failure_count`, `confidence`
   - Computed signature normalizes error messages (removes line numbers, UUIDs, paths)

2. **store_fix() Method**:
   - Stores in Neo4j (FixPattern nodes) + Qdrant (semantic embeddings)
   - Upserts: increments `success_count` if signature exists
   - GraphCodeBERT embeddings for semantic similarity search

3. **get_fix_for_error() Method**:
   - Exact signature match first (fast, Neo4j)
   - Falls back to semantic similarity (Qdrant) if no exact match
   - Returns fix with confidence >= 0.6 and similarity >= 0.75

4. **CodeRepairAgent Integration** (`src/mge/v2/agents/code_repair_agent.py`):
   - `_repair_single_runtime_violation()` now checks for known fixes FIRST
   - If known fix found → applies it directly (no LLM call)
   - If LLM fix works → stores it for future reuse
   - `mark_fix_failed()` decrements confidence when fix doesn't work

5. **Neo4j Migration 012** (`scripts/migrations/neo4j/012_fix_pattern_schema.cypher`):
   - 1 constraint: `fix_pattern_signature` (unique)
   - 6 indexes: confidence, error_type, fix_strategy, lookup (composite), last_used, success_count

**Beneficios:**
- Evita LLM calls repetidos para errores similares
- Acumula conocimiento de fixes exitosos
- Confidence score permite filtrar fixes no confiables
- Semantic search encuentra fixes para errores similares pero no idénticos

**Archivos Modificados:**
- `src/services/error_pattern_store.py` ✅
- `src/mge/v2/agents/code_repair_agent.py` ✅
- `scripts/migrations/neo4j/012_*` (3 archivos) ✅

---

### Gap 5: IR-to-Code Failure Correlation

**Estado: COMPLETO** ✅

**Implementación (2025-11-29):**

1. **IRCodeCorrelator** (`src/cognitive/services/ir_code_correlator.py`):
   - `analyze_generation()` - Analiza correlación entre IR y calidad de código
   - `_compute_entity_complexity()` - Score de complejidad de entidades
   - `_compute_endpoint_complexity()` - Score de complejidad de endpoints
   - `_identify_high_risk_patterns()` - Detecta patrones problemáticos
   - `get_historical_correlations()` - Obtiene historial de análisis

2. **Data Classes**:
   - `EntityCorrelation` - Correlación entidad-calidad
   - `EndpointCorrelation` - Correlación endpoint-calidad
   - `HighRiskPattern` - Patrón identificado como riesgoso
   - `IRCorrelationReport` - Reporte completo

3. **High-Risk Pattern Detection**:
   - Entidades con alta complejidad + bajo pass rate
   - Entidades con campos enum
   - Entidades con campos JSON
   - Endpoints complejos (>3 params + body)
   - Entidades con muchas relaciones

**Uso:**
```python
from src.cognitive.services.ir_code_correlator import get_ir_code_correlator

correlator = get_ir_code_correlator()
report = correlator.analyze_generation(entities, endpoints, smoke_results)
print(f"High-risk patterns: {len(report.high_risk_patterns)}")
```

**Archivos Creados:**
- `src/cognitive/services/ir_code_correlator.py` ✅

---

### Gap 6: Spec Ingestion Learning

**Estado: COMPLETO** ✅

**Implementación (2025-11-29):**

1. **SpecComplexityAnalyzer** (`src/services/spec_complexity_analyzer.py`):
   - `analyze_spec()` - Analiza complejidad antes de procesar
   - `record_processing_result()` - Registra resultados para aprender
   - `_estimate_processing_time()` - Estima tiempo de procesamiento
   - `get_learning_insights()` - Genera insights de aprendizaje
   - `get_statistics()` - Estadísticas de procesamiento

2. **Data Classes**:
   - `SpecComplexity` - Análisis de complejidad
   - `ProcessingResult` - Resultado de procesamiento
   - `SpecLearningInsight` - Insight de aprendizaje

3. **Complexity Detection**:
   - Conteo de endpoints, entidades, schemas
   - Detección de referencias circulares
   - Detección de polimorfismo (oneOf, anyOf, allOf)
   - Detección de referencias externas
   - Estimación de tiempo basada en coeficientes aprendidos

**Uso:**

```python
from src.services.spec_complexity_analyzer import get_spec_complexity_analyzer

analyzer = get_spec_complexity_analyzer()
complexity = analyzer.analyze_spec("/path/to/spec.yaml")
print(f"Estimated time: {complexity.estimated_processing_ms}ms")
```

**Archivos Creados:**
- `src/services/spec_complexity_analyzer.py` ✅

---

### Gap 7: Validation Constraint Learning

**Estado: COMPLETO** ✅

**Implementación (2025-11-29):**

1. **ConstraintLearningService** (`src/validation/constraint_learning_service.py`):
   - `record_violation()` - Registra violación individual
   - `record_batch_violations()` - Registra múltiples violaciones
   - `identify_patterns()` - Identifica patrones recurrentes
   - `generate_report()` - Genera reporte de aprendizaje
   - `get_statistics()` - Estadísticas de violaciones

2. **Data Classes**:
   - `ConstraintViolation` - Violación individual
   - `ConstraintPattern` - Patrón recurrente identificado
   - `ConstraintLearningReport` - Reporte completo

3. **Pattern Detection**:
   - Mismo tipo de constraint fallando repetidamente
   - Misma entidad con múltiples violaciones
   - Mismo campo fallando en múltiples entidades
   - Sugerencias de fix basadas en tipo de constraint

**Uso:**

```python
from src.validation.constraint_learning_service import get_constraint_learning_service

service = get_constraint_learning_service()
service.record_violation('required', 'field_name', 'Entity', 'field', 'not null', 'null')
report = service.generate_report()
print(f"Patterns found: {len(report.patterns)}")
```

**Archivos Creados:**
- `src/validation/constraint_learning_service.py` ✅

---

## Implementation Roadmap

### Sprint L1: Critical Feedback Loop (2-3 días)

| Task | Prioridad | Esfuerzo | Dependencia |
|------|-----------|----------|-------------|
| Gap 1: Smoke Test Feedback | P0 | 4-6h | - |
| Integración en Pipeline | P0 | 2h | Gap 1 |
| Tests unitarios | P0 | 2h | Gap 1 |
| Verificación E2E | P0 | 1h | All |

**Criterio de Exit:**
- [ ] Pattern scores > 0 después de E2E run
- [ ] Feedback positivo/negativo visible en logs
- [ ] Al menos 1 pattern promovido con score > 0.3

### Sprint L2: Enhanced Learning (3-4 días)

| Task | Prioridad | Esfuerzo | Dependencia |
|------|-----------|----------|-------------|
| Gap 4: Fix Pattern Learning | P1 | 4-6h | - |
| Gap 3: Neo4j Pattern Mining | P1 | 8-10h | Gap 1 |
| Cypher queries library | P1 | 2h | Gap 3 |
| Learning dashboard (CLI) | P2 | 4h | Gap 3 |

**Criterio de Exit:**
- [ ] Fix patterns se almacenan y reutilizan
- [ ] Neo4j queries retornan insights útiles
- [ ] Repair iterations reducidos en 30%

### Sprint L3: Advanced Correlation (4-5 días)

| Task | Prioridad | Esfuerzo | Dependencia |
|------|-----------|----------|-------------|
| Gap 2: Requirements Classifier Training | P2 | 6-8h | - |
| Gap 5: IR-to-Code Correlation | P2 | 6-8h | Gap 1 |
| Gap 6: Spec Complexity Analyzer | P3 | 4-6h | - |
| Gap 7: Constraint Learning | P3 | 2-4h | - |

**Criterio de Exit:**
- [ ] Classification accuracy > 60%
- [ ] IR complexity → failure correlation documented
- [ ] Spec processing time predictions within 20%

---

## Métricas de Éxito

### KPIs Post-Implementación

| Métrica | Baseline | Target Sprint L1 | Target Sprint L3 |
|---------|----------|------------------|------------------|
| Pattern Promotion Rate | 0% | 20% | 50% |
| Smoke Test Pass Rate | 47.7% | 60% | 80% |
| Repair Iterations Avg | Unknown | -20% | -40% |
| Classification Accuracy | 41.2% | 41.2% | 60% |
| Learning Feedback Loops | 2/7 | 3/7 | 7/7 |

### Telemetry to Add

```python
# Nuevas métricas para el reporte E2E:

📚 LEARNING METRICS (Sprint L1+)
------------------------------------------------------------------------------------------
  Positive Feedback Events:    X
  Negative Feedback Events:    Y
  Pattern Scores Updated:      Z
  Patterns Above Threshold:    N (>0.7)
  Fix Patterns Stored:         M
  Fix Patterns Reused:         K
  Learning Queries Executed:   Q
```

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Feedback loop creates noise | Media | Alto | Threshold mínimo para eventos, debounce |
| Neo4j queries lentos | Baja | Medio | Indexes, query caching |
| Over-fitting en patterns | Media | Alto | Regularization, diverse test sets |
| Complexity en pipeline | Alta | Medio | Feature flags, gradual rollout |

---

## Appendix A: Data Flow Diagrams

### Current Flow (Broken)
```
Generation → Smoke Tests → Results → (void)
                              ↓
                         No feedback
                              ↓
                    Pattern score = 0.00
```

### Target Flow (Sprint L1)
```
Generation → Smoke Tests → Results → SmokeTestFeedback
                              ↓              ↓
                         Record in DB   Update Pattern Scores
                              ↓              ↓
                    Neo4j Lineage     Promotion Check
                              ↓              ↓
                    Pattern Mining    Pattern Promoted!
```

---

## Appendix B: Code Templates

### Template: Feedback Event

```python
@dataclass
class FeedbackEvent:
    event_id: str
    event_type: Literal["positive", "negative"]
    source: Literal["smoke_test", "validation", "repair", "manual"]
    pattern_id: str
    timestamp: datetime
    metadata: dict

    # For negative events
    error_type: Optional[str] = None
    error_details: Optional[dict] = None

    # For positive events
    pass_rate: Optional[float] = None
    endpoint: Optional[str] = None
```

### Template: Learning Query Result

```python
@dataclass
class LearningInsight:
    insight_type: str
    confidence: float
    data: dict
    recommendation: str
    affected_patterns: List[str]
    priority: Literal["critical", "high", "medium", "low"]
```

---

## Implementation Progress

### ✅ Active Learning (Section 7 of LEARNING_SYSTEM_REDESIGN.md)

**Fecha:** 2025-11-29
**Commit:** `2f18290d`, `pending`

| Componente | Estado | Archivo |
|------------|--------|---------|
| ErrorKnowledge dataclass | ✅ Done | `src/cognitive/services/error_knowledge_repository.py` |
| ErrorKnowledgeRepository | ✅ Done | `src/cognitive/services/error_knowledge_repository.py` |
| Neo4j Migration 011 | ✅ Done | `scripts/migrations/neo4j/011_error_knowledge_schema.cypher` |
| RuntimeSmokeValidator integration | ✅ Done | `src/validation/runtime_smoke_validator.py` |
| CodeGenerationService avoidance | ✅ Done | `src/services/code_generation_service.py` |
| PatternFeedback error registration | ✅ Done | `src/cognitive/patterns/pattern_feedback_integration.py` |
| SmokeValidator → PatternFeedback | ✅ Done | `src/validation/runtime_smoke_validator.py` |

**Métodos implementados:**

- `learn_from_failure()` - Guarda errores de smoke tests
- `learn_from_fix()` - Guarda código corregido
- `get_relevant_errors()` - Query errores por entity/endpoint
- `build_avoidance_context()` - Genera contexto para generación
- `_get_avoidance_context()` - Query errores antes de generar código (CodeGenerationService)
- `register_generation_failure()` - Registra errores y penaliza scores (PatternFeedback)
- `_learn_from_error()` - Integración completa con ErrorKnowledge + PatternFeedback

**Ciclo de Aprendizaje Completo:**

```text
Smoke Test Failure → RuntimeSmokeValidator._learn_from_error()
                     ├─→ ErrorKnowledgeRepository.learn_from_failure() [Neo4j]
                     └─→ PatternFeedback.register_generation_failure() [Score penalty]

Code Generation → CodeGenerationService.generate_from_application_ir()
                  └─→ _get_avoidance_context() → ErrorKnowledgeRepository.get_relevant_errors()
                      └─→ build_avoidance_context() → Inject into repair_context
```

**Pendiente:**

- [x] ~~Ejecutar migration 011 en Neo4j~~ ✅ (1 constraint, 7 indexes)
- [x] ~~Integrar `get_relevant_errors()` en code generation prompts~~ ✅
- [x] ~~Conectar con Pattern Feedback para scores~~ ✅

**Estado: COMPLETO** ✅

---

## Resumen de Progreso

| Gap | Descripción | Impacto | Estado |
|-----|-------------|---------|--------|
| 1 | Active Learning (ErrorKnowledge) | CRÍTICO | ✅ COMPLETO |
| 2 | Requirements Classifier Learning | MEDIO | ✅ COMPLETO |
| 3 | Neo4j Pattern Mining | MEDIO | ✅ COMPLETO |
| 4 | Code Repair Fix Pattern Learning | ALTO | ✅ COMPLETO |
| 5 | IR-to-Code Failure Correlation | BAJO | ✅ COMPLETO |
| 6 | Spec Ingestion Learning | BAJO | ✅ COMPLETO |
| 7 | Validation Constraint Learning | BAJO | ✅ COMPLETO |

**Progreso Total:** 7/7 Gaps Completos (100%) ✅

**Archivos Creados:**

- `src/cognitive/services/error_knowledge_repository.py` (Gap 1)
- `src/classification/requirements_classifier_trainer.py` (Gap 2)
- `src/cognitive/services/pattern_mining_service.py` (Gap 3)
- `src/services/error_pattern_store.py` - FixPattern methods (Gap 4)
- `src/cognitive/services/ir_code_correlator.py` (Gap 5)
- `src/services/spec_complexity_analyzer.py` (Gap 6)
- `src/validation/constraint_learning_service.py` (Gap 7)
- `src/validation/smoke_test_pattern_adapter.py` (SmokeTest→Pattern) ✅

---

## SmokeTest→Pattern Integration ✅ COMPLETO

**Implementación (2025-11-29):**

1. **SmokeTestPatternAdapter** (`src/validation/smoke_test_pattern_adapter.py`):
   - `process_smoke_results()` - Genera LearningEvents desde smoke results
   - `update_pattern_scores()` - Actualiza scores con EMA
   - `_find_patterns_for_endpoint()` - Mapea endpoints a pattern_ids
   - `_log_score_updates()` - Log explícito de actualizaciones

2. **Data Classes**:
   - `LearningEvent` - Evento de feedback (POSITIVE/NEGATIVE)
   - `LearningEventType` - Enum para tipo de evento
   - `PatternScoreUpdate` - Actualización de score individual
   - `ScoreUpdateSummary` - Resumen de actualizaciones

3. **Features**:
   - Exponential Moving Average (α=0.3) para score updates
   - Promotion threshold: 0.7, Demotion threshold: 0.3
   - Persistencia en Neo4j (PatternScore nodes)
   - In-memory fallback cuando Neo4j no disponible
   - Convenience function: `process_smoke_results_to_patterns()`

**Integración al Pipeline E2E** (`tests/e2e/real_e2e_full_pipeline.py`):

| Servicio | Fase | Función |
|----------|------|---------|
| SpecComplexityAnalyzer | Phase 1 | Analiza complejidad de specs |
| ConstraintLearningService | Phase 7 | Aprende de constraint violations |
| SmokeTestPatternAdapter | Phase 8.5 | Actualiza pattern scores |
| IRCodeCorrelator | Phase 8.5 | Correlaciona IR con resultados |
| PatternMiningService | Final Report | Genera learning insights |

**Output del Pipeline:**

```text
📋 Phase 1: Spec Ingestion
    - 🎓 Spec complexity: 0.45 (est. 2500ms)

✅ Phase 7: Validation
    - 🎓 Constraint learning: 3 violation patterns identified

🔥 Phase 8.5: Runtime Smoke Test
  📊 Updated pattern scores: 12 patterns (avg score 0.52, promoted: 0)
  🎓 Pattern learning: 12 patterns updated
  🎓 IR-Code correlation: No high-risk patterns detected

🎓 Learning Insights:
    💡 Most problematic pattern: 'POST /orders' with 5 failures
```

**Uso:**

```python
from src.validation.smoke_test_pattern_adapter import process_smoke_results_to_patterns

summary = process_smoke_results_to_patterns(
    smoke_result={"violations": [...], "passed_scenarios": [...]},
    generation_manifest=manifest.to_dict(),
    app_id="my_app"
)
# Output: "📊 Updated pattern scores: 27 patterns (avg score 0.63, promoted: 3)"
```

---

**Documento creado:** 2025-11-29
**Última actualización:** 2025-11-29
**Autor:** DevMatrix AI Pipeline Team
