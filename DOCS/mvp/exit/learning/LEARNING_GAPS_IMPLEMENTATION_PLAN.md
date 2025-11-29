# Learning Gaps Implementation Plan

**Fecha:** 2025-11-29
**Estado:** Draft
**Prioridad:** Alta - Bloqueante para Pattern Promotion

---

## Executive Summary

El sistema de learning actual tiene gaps críticos que impiden la promoción de patterns.
Este plan detalla las implementaciones necesarias para cerrar el ciclo de feedback.

### Estado Actual vs Deseado

| Métrica | Actual | Target |
|---------|--------|--------|
| Pattern Promotion Rate | 0% | >30% |
| Smoke Test Pass Rate | 47.7% | >80% |
| Learning Feedback Loops | 2/7 | 7/7 |
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

**Problema:**
- Classification Accuracy: 41.2% - NUNCA mejora
- No hay feedback loop cuando la clasificación es incorrecta
- El ground truth existe pero no se usa para entrenar

**Evidencia:**
```
📊 Classification Metrics
    ├─ Accuracy: 41.2%
    ├─ Precision: 85.0%
```

**Impacto:** MEDIO - Afecta calidad de planning

**Solución Propuesta:**

```python
# src/services/requirements_classifier_trainer.py (NUEVO)

class RequirementsClassifierTrainer:
    """Online learning for requirements classifier."""

    def __init__(self, classifier: RequirementsClassifier, ground_truth_path: str):
        self.classifier = classifier
        self.ground_truth = self._load_ground_truth(ground_truth_path)
        self.training_samples = []

    def record_classification_result(
        self,
        requirement: str,
        predicted_class: str,
        actual_class: str  # From final validation
    ):
        """Record classification for future training."""
        if predicted_class != actual_class:
            self.training_samples.append({
                "requirement": requirement,
                "predicted": predicted_class,
                "actual": actual_class,
                "timestamp": datetime.utcnow()
            })

    def retrain_if_needed(self, min_samples: int = 50):
        """Retrain classifier if enough new samples."""
        if len(self.training_samples) >= min_samples:
            # Fine-tune classifier with new samples
            self.classifier.fine_tune(self.training_samples)
            self.training_samples = []
```

**Integración:**
- Post-validation: Comparar clasificación inicial vs resultado final
- Acumular samples incorrectos
- Reentrenar cada N runs o cuando accuracy < threshold

**Archivos a Modificar:**
- `src/services/requirements_classifier_trainer.py` (NUEVO)
- `src/services/requirements_classifier.py` (agregar fine_tune method)
- `tests/e2e/real_e2e_full_pipeline.py` (integrar en Phase 7)

**Esfuerzo:** 6-8 horas
**Dependencias:** Ground truth dataset

---

### Gap 3: Neo4j Pattern Mining

**Problema:**
- Neo4j almacena ApplicationIR pero NO se usa para análisis de patterns
- No hay queries que correlacionen IR elements con failures
- El grafo es write-only, no read-for-learning

**Impacto:** MEDIO - Oportunidad de insights perdida

**Solución Propuesta:**

```cypher
-- queries/learning/failure_patterns.cypher

-- Query 1: Endpoints que fallan consistentemente
MATCH (app:ApplicationIR)-[:HAS_API]->(api:APIModelIR)-[:HAS_ENDPOINT]->(ep:Endpoint)
MATCH (ep)-[:GENERATED_CODE]->(code:GeneratedFile)
MATCH (code)-[:FAILED_TEST]->(test:SmokeTest)
RETURN ep.path, ep.method, count(test) as failure_count
ORDER BY failure_count DESC
LIMIT 10;

-- Query 2: Entities con alta tasa de error en services
MATCH (dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)
MATCH (e)-[:GENERATES]->(svc:ServiceFile)
MATCH (svc)-[:HAS_ERROR]->(err:RuntimeError)
RETURN e.name, count(err) as error_count, collect(DISTINCT err.type) as error_types
ORDER BY error_count DESC;

-- Query 3: Patterns exitosos por dominio
MATCH (p:Pattern)-[:USED_IN]->(gen:Generation)
WHERE gen.smoke_pass_rate > 0.8
RETURN p.category, p.name, count(gen) as success_count, avg(gen.smoke_pass_rate) as avg_pass
ORDER BY success_count DESC;

-- Query 4: Correlation IR complexity → failures
MATCH (app:ApplicationIR)
WITH app,
     size((app)-[:HAS_ENTITY]->()) as entity_count,
     size((app)-[:HAS_ENDPOINT]->()) as endpoint_count,
     size((app)-[:HAS_FLOW]->()) as flow_count
MATCH (app)-[:GENERATED]->(gen:Generation)
RETURN entity_count, endpoint_count, flow_count,
       avg(gen.smoke_pass_rate) as avg_pass_rate,
       count(gen) as sample_count
ORDER BY avg_pass_rate ASC;
```

**Implementación:**

```python
# src/cognitive/services/pattern_mining_service.py (NUEVO)

class PatternMiningService:
    """Mines patterns from Neo4j graph for learning insights."""

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    def get_failure_patterns(self) -> List[FailurePattern]:
        """Get endpoints/entities with high failure rates."""
        with self.driver.session() as session:
            result = session.run(FAILURE_PATTERNS_QUERY)
            return [FailurePattern(**r) for r in result]

    def get_success_patterns(self) -> List[SuccessPattern]:
        """Get patterns with high success rates."""
        with self.driver.session() as session:
            result = session.run(SUCCESS_PATTERNS_QUERY)
            return [SuccessPattern(**r) for r in result]

    def get_complexity_correlation(self) -> ComplexityCorrelation:
        """Analyze correlation between IR complexity and failures."""
        with self.driver.session() as session:
            result = session.run(COMPLEXITY_CORRELATION_QUERY)
            return self._analyze_correlation(result)

    def generate_learning_report(self) -> LearningReport:
        """Generate comprehensive learning insights report."""
        return LearningReport(
            failure_patterns=self.get_failure_patterns(),
            success_patterns=self.get_success_patterns(),
            complexity_correlation=self.get_complexity_correlation(),
            recommendations=self._generate_recommendations()
        )
```

**Archivos a Crear/Modificar:**
- `src/cognitive/services/pattern_mining_service.py` (NUEVO)
- `queries/learning/*.cypher` (NUEVO - query files)
- `tests/e2e/real_e2e_full_pipeline.py` (integrar en Phase 10)

**Esfuerzo:** 8-10 horas
**Dependencias:** Gap 1 (necesita datos de smoke tests en grafo)

---

### Gap 4: Code Repair Fix Pattern Learning

**Problema:**
- Code Repair guarda ERROR patterns
- NO guarda FIX patterns que funcionaron
- Cuando el mismo error aparece, no sabe qué fix aplicar

**Evidencia:**
```python
# Actual - Solo guarda errores:
await error_pattern_store.store_error(error_pattern)

# Falta - Guardar fixes exitosos:
# await error_pattern_store.store_fix(fix_pattern)  # NO EXISTE
```

**Impacto:** BAJO-MEDIO - Repair loops innecesarios

**Solución Propuesta:**

```python
# Agregar a src/services/error_pattern_store.py

class FixPattern:
    """Represents a successful fix for an error pattern."""
    error_signature: str  # Hash del error original
    fix_code: str         # Código del fix
    fix_strategy: str     # "add_import", "fix_type", "add_validation", etc.
    success_count: int    # Veces que funcionó
    context: dict         # Entity, endpoint, etc.

async def store_fix(self, error_pattern: ErrorPattern, fix_code: str, strategy: str):
    """Store a successful fix for an error pattern."""
    fix = FixPattern(
        error_signature=self._compute_error_signature(error_pattern),
        fix_code=fix_code,
        fix_strategy=strategy,
        success_count=1,
        context=error_pattern.context
    )

    # Upsert - increment success_count if exists
    await self._upsert_fix(fix)

async def get_fix_for_error(self, error: ErrorPattern) -> Optional[FixPattern]:
    """Get the most successful fix for a similar error."""
    signature = self._compute_error_signature(error)
    fixes = await self._query_fixes(signature)

    if fixes:
        # Return fix with highest success count
        return max(fixes, key=lambda f: f.success_count)
    return None
```

**Integración en Code Repair:**
```python
# En _phase_8_code_repair

# ANTES de intentar reparar, buscar fix conocido:
known_fix = await self.error_pattern_store.get_fix_for_error(current_error)
if known_fix:
    print(f"    💡 Found known fix: {known_fix.fix_strategy}")
    apply_fix(known_fix)
else:
    # Proceed with LLM-based repair
    ...

# DESPUÉS de repair exitoso:
if repair_successful:
    await self.error_pattern_store.store_fix(
        error_pattern=original_error,
        fix_code=applied_fix,
        strategy=detected_strategy
    )
```

**Archivos a Modificar:**
- `src/services/error_pattern_store.py` (agregar FixPattern, store_fix, get_fix_for_error)
- `tests/e2e/real_e2e_full_pipeline.py` (integrar en Phase 6.5)

**Esfuerzo:** 4-6 horas
**Dependencias:** Ninguna

---

### Gap 5: IR-to-Code Failure Correlation

**Problema:**
- No sabemos qué elementos del IR producen código que falla
- Entities complejas? Endpoints con muchos params? Flows con loops?
- Sin esta data, no podemos mejorar la generación

**Impacto:** BAJO - Insight para mejora futura

**Solución Propuesta:**

```python
# src/cognitive/services/ir_code_correlator.py (NUEVO)

class IRCodeCorrelator:
    """Correlates IR elements with generated code quality."""

    def analyze_generation(
        self,
        app_ir: ApplicationIR,
        smoke_results: SmokeTestResult,
        generation_manifest: dict
    ) -> IRCorrelationReport:
        """Analyze which IR elements correlate with failures."""

        correlations = []

        # Analyze entity complexity vs service failures
        for entity in app_ir.get_entities():
            entity_complexity = self._compute_entity_complexity(entity)
            service_pass_rate = self._get_service_pass_rate(entity.name, smoke_results)

            correlations.append(EntityCorrelation(
                entity_name=entity.name,
                complexity_score=entity_complexity,
                pass_rate=service_pass_rate,
                attributes_count=len(entity.attributes),
                relationships_count=len(entity.relationships)
            ))

        # Analyze endpoint complexity vs route failures
        for endpoint in app_ir.get_endpoints():
            endpoint_complexity = self._compute_endpoint_complexity(endpoint)
            endpoint_pass_rate = self._get_endpoint_pass_rate(endpoint.path, smoke_results)

            correlations.append(EndpointCorrelation(
                path=endpoint.path,
                method=endpoint.method,
                complexity_score=endpoint_complexity,
                pass_rate=endpoint_pass_rate,
                params_count=len(endpoint.parameters),
                has_body=endpoint.request_body is not None
            ))

        return IRCorrelationReport(
            correlations=correlations,
            high_risk_patterns=self._identify_high_risk_patterns(correlations),
            recommendations=self._generate_recommendations(correlations)
        )

    def _compute_entity_complexity(self, entity: Entity) -> float:
        """Compute complexity score for an entity."""
        base_score = len(entity.attributes) * 0.1
        relationship_score = len(entity.relationships) * 0.3

        # Penalize complex types
        for attr in entity.attributes:
            if attr.data_type in [DataType.JSON, DataType.ENUM]:
                base_score += 0.2

        return min(1.0, base_score + relationship_score)
```

**Archivos a Crear:**
- `src/cognitive/services/ir_code_correlator.py` (NUEVO)

**Esfuerzo:** 6-8 horas
**Dependencias:** Gap 1

---

### Gap 6: Spec Ingestion Learning

**Problema:**
- No aprendemos qué specs son fáciles/difíciles de procesar
- Phase 1 tarda 4 minutos - no sabemos por qué algunas specs son más lentas
- No hay feedback sobre calidad del spec parsing

**Impacto:** BAJO - Optimización futura

**Solución Propuesta:**

```python
# src/services/spec_complexity_analyzer.py (NUEVO)

class SpecComplexityAnalyzer:
    """Analyzes spec complexity and tracks processing metrics."""

    def analyze_spec(self, spec_path: str) -> SpecComplexity:
        """Analyze spec complexity before processing."""
        spec_content = self._load_spec(spec_path)

        return SpecComplexity(
            path=spec_path,
            size_bytes=len(spec_content),
            entity_mentions=self._count_entity_mentions(spec_content),
            endpoint_mentions=self._count_endpoint_mentions(spec_content),
            complexity_indicators=self._detect_complexity_indicators(spec_content),
            estimated_processing_time=self._estimate_time(spec_content)
        )

    def record_processing_result(
        self,
        spec_complexity: SpecComplexity,
        actual_time_ms: int,
        success: bool,
        ir_quality_score: float
    ):
        """Record actual processing results for learning."""
        # Store for future predictions
        self._store_sample(
            complexity=spec_complexity,
            actual_time=actual_time_ms,
            success=success,
            quality=ir_quality_score
        )

        # Update time estimator model
        self._update_time_model(spec_complexity, actual_time_ms)
```

**Esfuerzo:** 4-6 horas
**Dependencias:** Ninguna

---

### Gap 7: Validation Constraint Learning

**Problema:**
- IR Constraint compliance: 53-74%
- Los mismos constraints fallan repetidamente
- No aprendemos qué transformaciones IR→Code pierden constraints

**Evidencia:**
```
📋 Constraint compliance (relaxed): 53.3%
📋 Constraint compliance (strict): 73.8%
```

**Impacto:** BAJO - Ya tenemos semantic compliance 100%

**Solución Propuesta:**

Logging detallado de constraints que fallan + categorización para identificar patrones.

**Esfuerzo:** 2-4 horas
**Dependencias:** Ninguna

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
**Commit:** `2f18290d`

| Componente | Estado | Archivo |
|------------|--------|---------|
| ErrorKnowledge dataclass | ✅ Done | `src/cognitive/services/error_knowledge_repository.py` |
| ErrorKnowledgeRepository | ✅ Done | `src/cognitive/services/error_knowledge_repository.py` |
| Neo4j Migration 011 | ✅ Done | `scripts/migrations/neo4j/011_error_knowledge_schema.cypher` |
| RuntimeSmokeValidator integration | ✅ Done | `src/validation/runtime_smoke_validator.py` |

**Métodos implementados:**

- `learn_from_failure()` - Guarda errores de smoke tests
- `learn_from_fix()` - Guarda código corregido
- `get_relevant_errors()` - Query errores por entity/endpoint
- `build_avoidance_context()` - Genera contexto para generación

**Pendiente:**

- [ ] Ejecutar migration 011 en Neo4j
- [ ] Integrar `get_relevant_errors()` en code generation prompts
- [ ] Conectar con Pattern Feedback para scores

---

**Documento creado:** 2025-11-29
**Última actualización:** 2025-11-29
**Autor:** DevMatrix AI Pipeline Team
