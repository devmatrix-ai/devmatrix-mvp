# 🧠 Sistema de Learning - Arquitectura Completa

**Autor:** Análisis Ultrathink del Pipeline E2E
**Fecha:** 2025-11-28
**Versión:** 1.1 - Actualizado con Learning Gaps Sprint 8
**Última actualización:** 2025-11-29

---

## 🆕 Nuevos Componentes (Sprint 8 - Learning Gaps)

```
src/cognitive/services/
├─ error_knowledge_repository.py   ← Gap 1: Active Learning
├─ pattern_mining_service.py       ← Gap 3: Pattern Mining from Neo4j
└─ ir_code_correlator.py          ← Gap 5: IR-to-Code Correlation

src/classification/
└─ requirements_classifier_trainer.py  ← Gap 2: Classifier Learning

src/services/
├─ error_pattern_store.py          ← Gap 4: FixPattern methods
└─ spec_complexity_analyzer.py     ← Gap 6: Spec Complexity Learning

src/validation/
├─ constraint_learning_service.py  ← Gap 7: Constraint Violations
└─ smoke_test_pattern_adapter.py   ← SmokeTest→Pattern feedback

scripts/migrations/neo4j/
├─ 011_error_knowledge_schema.cypher
└─ 012_fix_pattern_schema.cypher
```

**Ver:** [LEARNING_GAPS_IMPLEMENTATION_PLAN.md](./LEARNING_GAPS_IMPLEMENTATION_PLAN.md) para detalles.

---

## 📊 Arquitectura General del Sistema de Learning

```
┌─────────────────────────────────────────────────────────────────┐
│                    CICLO DE LEARNING COMPLETO                   │
└─────────────────────────────────────────────────────────────────┘

1. CAPTURA DE PATRONES
   ├─ CodeGenerationService genera código
   ├─ Se ejecutan tests y validaciones
   └─ Se registra el resultado (éxito/error)

2. ALMACENAMIENTO DUAL
   ├─ Neo4j: Estructura y relaciones
   └─ Qdrant: Embeddings semánticos (768-dim GraphCodeBERT)

3. ANÁLISIS Y SCORING
   ├─ PatternAnalyzer: reusabilidad, seguridad, calidad
   ├─ QualityEvaluator: métricas de ejecución y validación
   └─ DualValidator: validación con LLMs (Claude + GPT-4)

4. PROMOCIÓN DE PATRONES
   ├─ LLM stratum → AST stratum → TEMPLATE stratum
   ├─ Criterios formales por dominio
   └─ Sistema adaptativo de thresholds

5. REUTILIZACIÓN
   ├─ Búsqueda semántica en PatternBank
   ├─ Ranking basado en ejecuciones (DAG)
   └─ Fallback keywords cuando no hay matches
```

---

## 🗺️ Mapa de Componentes del Sistema

### Archivos Principales

```
src/cognitive/patterns/
├─ pattern_feedback_integration.py  ← Orquestador principal
├─ pattern_bank.py                  ← Almacenamiento de patterns promovidos
├─ pattern_classifier.py            ← Clasificación semántica
├─ pattern_analyzer.py              ← Análisis de calidad de código
└─ dual_validator.py                ← Validación con 2 LLMs

src/services/
├─ error_pattern_store.py           ← Almacenamiento errores/éxitos
├─ pattern_promoter.py              ← Sistema de stratum promotion
└─ code_generation_service.py       ← Generación + pattern reuse

tests/e2e/
└─ real_e2e_full_pipeline.py        ← Pipeline completo con learning
```

### Puntos de Learning en el Pipeline E2E

```python
real_e2e_full_pipeline.py:
├─ Line 1254: _initialize_services()
│  ├─ 1269: self.pattern_bank = PatternBank()
│  ├─ 1344: self.error_pattern_store = ErrorPatternStore()  # ← Guarda errores/éxitos
│  └─ 1367: self.feedback_integration = PatternFeedbackIntegration()  # ← Sistema promoción
│
├─ Line 2102: Pattern Search ANTES de generar código 🔍
│  └─ self.pattern_bank.search_with_fallback()  # ← REUTILIZA patterns
│
├─ Line 3026: _phase_8_code_repair() - Learning durante reparación
│  ├─ 3766: Busca similar_patterns en ErrorPatternStore
│  ├─ 3898: await error_pattern_store.store_error()  # ← Guarda ERRORES
│  └─ 3972: await error_pattern_store.store_success()  # ← Guarda ÉXITOS
│
└─ Line 4739: _phase_11_learning() - Learning post-generación
   ├─ 4771: feedback_integration.register_successful_generation()  # ← Registra candidato
   └─ 4796: feedback_integration.check_and_promote_ready_patterns()  # ← PROMOCIÓN
```

---

## 🔄 Flujo Detallado: De la Generación al Aprendizaje

### **Fase 1: Generación de Código con Contexto**

**Archivo:** `src/services/code_generation_service.py`

Cuando se genera código nuevo:

```python
# 1. CodeGenerationService intenta generar código
generated_code = await self.llm_client.generate(prompt)

# 2. Se valida el código generado
validation_result = ValidationStrategyFactory.validate(
    code=generated_code,
    file_type=file_type
)

# 3. Si hay errores previos, busca patrones similares
if attempt > 1 and self.pattern_store:
    similar_errors = await self.pattern_store.search_similar_errors(
        task_description=task.description,
        error_message=last_error_msg,
        top_k=3
    )
    # Los errores similares se agregan al prompt como contexto
```

**Detalle clave:** Usás **GraphCodeBERT** (768 dimensiones) para generar embeddings semánticos del código. Esto permite encontrar patrones similares no solo por texto, sino por estructura de código.

---

### **Fase 2: Registro en Dual Storage (Neo4j + Qdrant)**

**Archivo:** `src/services/error_pattern_store.py`

Cada resultado (error o éxito) se almacena en **DOS bases de datos simultáneamente**:

#### **Neo4j - Estructura y Queries Complejas**

```cypher
-- Almacena errores con relaciones
CREATE (e:CodeGenerationError {
    error_id: $error_id,
    task_id: $task_id,
    task_description: $task_description,
    error_type: $error_type,
    error_message: $error_message,
    failed_code: $failed_code,
    attempt: $attempt,
    timestamp: datetime($timestamp)
})

-- Almacena éxitos
CREATE (s:SuccessfulCode {
    success_id: $success_id,
    task_id: $task_id,
    task_description: $task_description,
    generated_code: $generated_code,
    quality_score: $quality_score,
    timestamp: datetime($timestamp)
})
```

#### **Qdrant - Búsqueda Semántica Vectorial**

```python
# Genera embedding del contexto del error/éxito
error_context = f"""
Task: {error.task_description}
Error Type: {error.error_type}
Error Message: {error.error_message}
Failed Code:
{error.failed_code}
""".strip()

# Usa GraphCodeBERT para embeddings (768-dim)
embedding = self.embedding_model.encode(error_context).tolist()

# Almacena en Qdrant con metadata
point = PointStruct(
    id=str(uuid.uuid4()),
    vector=embedding,  # 768-dimensional vector
    payload={
        "error_id": error.error_id,
        "task_id": error.task_id,
        "task_description": error.task_description,
        "error_type": error.error_type,
        "error_message": error.error_message,
        "failed_code": error.failed_code[:500],
        "attempt": error.attempt,
        "timestamp": error.timestamp.isoformat(),
        "type": "error"
    }
)

self.qdrant.upsert(
    collection_name="code_generation_feedback",
    points=[point]
)
```

**¿Por qué dual storage?**
- **Neo4j:** Queries complejas (ej: "errores recurrentes en últimas 24h por tipo")
- **Qdrant:** Búsqueda semántica ultrarrápida (encuentra código similar aunque use variables diferentes)

#### **Estructura de Collections en Qdrant**

```
Collection: code_generation_feedback
├─ Vectores: 768-dimensional (GraphCodeBERT)
├─ Distance: Cosine similarity
└─ Payload: {
    error_id/success_id,
    task_id,
    task_description,
    error_message/generated_code,
    metadata,
    type: "error" | "success"
}

Collection: semantic_patterns (PatternBank)
├─ Vectores: 384-dimensional (Sentence-BERT)
├─ Distance: Cosine similarity
└─ Payload: {
    pattern_id,
    purpose,
    code,
    success_rate,
    usage_count,
    domain,
    production_ready,
    security_level,
    performance_tier
}
```

---

### **Fase 3: Análisis y Scoring de Patrones**

**Archivo:** `src/cognitive/patterns/pattern_feedback_integration.py`

Cuando un patrón se registra exitosamente, pasa por múltiples evaluadores:

#### **3.1. QualityEvaluator - Métricas Objetivas**

```python
class QualityEvaluator:
    def calculate_quality_metrics(self, candidate_id: str) -> QualityMetrics:
        # Success rate (35%)
        success_rate = test_passed / test_total

        # Test coverage (35%)
        test_coverage = coverage_lines_covered / coverage_lines_total

        # Validation score (20%)
        validation_score = rules_passed / rules_total

        # Performance score (10%)
        performance_score = max(0.0, min(1.0, 2.0 - time_ratio))

        # Overall quality (weighted average)
        overall_quality = (
            0.35 * success_rate +
            0.35 * test_coverage +
            0.20 * validation_score +
            0.10 * performance_score
        )

        return QualityMetrics(
            success_rate=success_rate,
            test_coverage=test_coverage,
            validation_score=validation_score,
            performance_score=performance_score,
            overall_quality=overall_quality
        )
```

**Pesos de las métricas:**
- **35%** - Success Rate (tests passing)
- **35%** - Test Coverage (code coverage)
- **20%** - Validation Score (validaciones cumplidas)
- **10%** - Performance Score (tiempo de ejecución)

#### **3.2. PatternAnalyzer - Análisis de Código**

```python
class PatternAnalyzer:
    def score_reusability(self, code: str) -> float:
        """Analiza reusabilidad del código"""
        score = 1.0

        # Penaliza hardcoded values
        hardcoded_strings = re.findall(r'"[^"]{3,}"', code)
        magic_value_penalty = min(0.3, len(hardcoded_strings) * 0.05)
        score -= magic_value_penalty

        # Bonifica parametrización
        has_params = bool(re.search(r'def \w+\([^)]+\)', code))
        if has_params:
            score += 0.1

        # Bonifica type hints
        has_type_hints = bool(re.search(r':\s*\w+', code))
        if has_type_hints:
            score += 0.1

        # Bonifica docstrings
        has_docstring = bool(re.search(r'"""[\s\S]*?"""', code))
        if has_docstring:
            score += 0.1

        return max(0.0, min(1.0, score))

    def analyze_security(self, code: str) -> float:
        """Analiza vulnerabilidades de seguridad"""
        score = 1.0

        # Detecta secrets hardcodeados
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]
        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                score -= 0.3

        # Detecta SQL injection risks
        if 'execute(' in code and '%s' in code:
            score -= 0.2

        # Detecta eval/exec (peligroso)
        if 'eval(' in code or 'exec(' in code:
            score -= 0.4

        return max(0.0, min(1.0, score))

    def analyze_code_quality(self, code: str) -> float:
        """Analiza calidad del código"""
        score = 1.0

        # Detecta deep nesting (code smell)
        lines = code.split('\n')
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)

        if max_indent > 16:  # >4 niveles
            score -= 0.2

        # Bonifica error handling
        if 'try:' in code and 'except' in code:
            score += 0.1

        # Bonifica logging
        if 'logger.' in code or 'logging.' in code:
            score += 0.1

        return max(0.0, min(1.0, score))
```

**Criterios de análisis:**

**Reusabilidad:**
- ❌ Penaliza: Hardcoded values, magic numbers
- ✅ Bonifica: Parametrización, type hints, docstrings

**Seguridad:**
- ❌ Penaliza: Secrets hardcodeados, SQL injection, eval/exec
- ✅ Bonifica: Validación de inputs, sanitización

**Calidad de Código:**
- ❌ Penaliza: Deep nesting (>4 niveles)
- ✅ Bonifica: Error handling, logging

#### **3.3. DualValidator - Validación con LLMs**

**Archivo:** `src/cognitive/patterns/dual_validator.py`

Este es el componente más innovador - usa **dos LLMs diferentes** para validar patrones:

```python
class RealDualValidator:
    MIN_SUCCESS_RATE = 0.95      # 95% éxito requerido
    MIN_TEST_COVERAGE = 0.80      # 80% coverage requerido
    MIN_SECURITY_LEVEL = SecurityLevel.MEDIUM
    MIN_COMPLIANCE_LEVEL = ComplianceLevel.PARTIAL
    MIN_PERFORMANCE_SCORE = 0.70
    MIN_QUALITY_SCORE = 0.75

    def validate_pattern(self, pattern: Any, context: Dict[str, Any]) -> ValidationResult:
        """Valida patrón con métricas reales"""

        # 1. Valida success rate
        if success_rate < self.MIN_SUCCESS_RATE:
            issues.append(f"Success rate {success_rate:.2%} below minimum")

        # 2. Valida test coverage
        if test_coverage < self.MIN_TEST_COVERAGE:
            issues.append(f"Test coverage {test_coverage:.2%} below minimum")

        # 3. Analiza seguridad
        security_level = self._analyze_security(code)

        # 4. Analiza performance
        if performance_score < self.MIN_PERFORMANCE_SCORE:
            issues.append(f"Performance score too low")

        # 5. Calcula quality score
        quality_score = self._calculate_quality_score(
            success_rate, test_coverage, security_level,
            performance_score, compliance_level
        )

        # 6. Decide si promover
        should_promote = self._should_promote_internal(
            success_rate, test_coverage, security_level,
            compliance_level, performance_score, quality_score
        )

        return ValidationResult(
            is_valid=len(issues) == 0,
            should_promote=should_promote,
            quality_score=quality_score,
            issues=issues,
            recommendations=recommendations
        )
```

**Thresholds Mínimos:**
- ✅ Success Rate: **≥95%**
- ✅ Test Coverage: **≥80%**
- ✅ Security Level: **≥MEDIUM**
- ✅ Performance Score: **≥0.70**
- ✅ Quality Score: **≥0.75**

---

### **Fase 4: Sistema de Promoción Multi-Nivel (Stratum)**

**Archivo:** `src/services/pattern_promoter.py`

Tu sistema tiene **3 niveles de confianza** para los patrones:

```
┌──────────────────────────────────────────────────────┐
│              STRATUM HIERARCHY                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  🥇 TEMPLATE (Highest Trust)                        │
│     ├─ 99% success rate requerido                   │
│     ├─ 50+ runs exitosos                            │
│     ├─ 0 regresiones                                │
│     ├─ 14 días de estabilidad                       │
│     ├─ 5+ proyectos distintos                       │
│     └─ 🔒 Requiere revisión humana                  │
│                                                      │
│  🥈 AST (Medium Trust)                              │
│     ├─ 95% success rate requerido                   │
│     ├─ 10+ runs exitosos                            │
│     ├─ 0 regresiones                                │
│     ├─ 3 días de estabilidad                        │
│     ├─ 3+ proyectos distintos                       │
│     └─ ✅ Promoción automática                      │
│                                                      │
│  🥉 LLM (Lowest Trust - Starting Point)             │
│     ├─ Código recién generado                       │
│     ├─ Sin historial probado                        │
│     └─ Requiere validación                          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### **Criterios Formales de Promoción (Phase 7)**

```python
PROMOTION_CRITERIA_FORMAL = {
    "llm_to_ast": FormalPromotionCriteria(
        min_distinct_projects=3,
        min_semantic_compliance=1.00,       # 100% compliance!
        max_regressions_golden_apps=0,
        min_successful_runs=10,
        max_generation_time_variance=0.50,  # 50% variance OK
        requires_no_project_context=False,
    ),
    "ast_to_template": FormalPromotionCriteria(
        min_distinct_projects=5,
        min_semantic_compliance=1.00,       # Perfect compliance
        max_regressions_golden_apps=0,
        min_successful_runs=50,
        max_generation_time_variance=0.10,  # Solo 10% variance
        requires_no_project_context=True,   # Debe ser context-free
    ),
}
```

**Comparación de Criterios:**

| Criterio | LLM → AST | AST → TEMPLATE |
|----------|-----------|----------------|
| Success Rate | ≥95% | ≥99% |
| Successful Runs | ≥10 | ≥50 |
| Distinct Projects | ≥3 | ≥5 |
| Regressions | 0 | 0 |
| Semantic Compliance | 100% | 100% |
| Time Variance | <50% | <10% |
| Context-Free | No | **Sí** |
| Human Review | No | **Sí** |

#### **Proceso de Evaluación**

```python
async def _attempt_auto_promotion(
    self,
    candidate: PatternCandidate,
    quality_metrics: QualityMetrics
) -> bool:
    # 1. Analiza el patrón
    reusability = self.pattern_analyzer.score_reusability(candidate.code)
    security = self.pattern_analyzer.analyze_security(candidate.code)
    code_quality = self.pattern_analyzer.analyze_code_quality(candidate.code)

    # 2. Calcula promotion score
    promotion_score = (
        0.4 * quality_metrics.overall_quality +
        0.3 * reusability +
        0.2 * security +
        0.1 * code_quality
    )

    # 3. Verifica threshold adaptativo por dominio
    threshold = self.quality_evaluator.get_threshold(candidate.domain)
    adjusted_threshold = self.threshold_manager.get_adjusted_threshold(
        candidate.domain,
        threshold.promotion_score
    )

    if promotion_score < adjusted_threshold:
        return False  # No promover

    # 4. Dual-validator (Claude + GPT-4)
    validation_result = self.dual_validator.validate_pattern(
        pattern=candidate,
        context={
            'quality_metrics': quality_metrics,
            'code': candidate.code,
            'signature': candidate.signature
        }
    )

    if not validation_result.should_promote:
        return False

    # 5. PROMOCIÓN EXITOSA
    logger.info(f"🚀 Pattern {candidate.candidate_id} PROMOTED!")
    candidate.status = PromotionStatus.PROMOTED

    # Track en sistema adaptativo
    self.threshold_manager.track_promotion(candidate.domain, success=True)

    return True
```

**Fórmula de Promotion Score:**
```
promotion_score =
    0.4 × overall_quality +     (Quality metrics weighted)
    0.3 × reusability +         (Code reusability)
    0.2 × security +            (Security analysis)
    0.1 × code_quality          (Code quality)
```

#### **Sistema de Demotion (Agresivo)**

**Filosofía:** Conservative promotion, **AGGRESSIVE demotion**

```python
DEMOTION_THRESHOLDS = {
    "failure_rate": 0.10,     # >10% failures → demote
    "regression_count": 1,    # ANY regression → demote
    "recent_failures": 3,     # 3 failures in last 10 runs → demote
}

def evaluate_demotion(
    self,
    pattern_id: str,
    metrics: PatternMetrics,
    recent_results: List[bool]
) -> Optional[Stratum]:
    """Conservative promotion, AGGRESSIVE demotion"""

    # Check 1: Overall failure rate
    failure_rate = metrics.failed_runs / metrics.total_runs
    if failure_rate > 0.10:
        return self._get_previous_stratum(current)

    # Check 2: ANY regression triggers demotion
    if metrics.regression_count >= 1:
        return self._get_previous_stratum(current)

    # Check 3: Recent failures (last 10 runs)
    recent_failures = sum(1 for r in recent_results[-10:] if not r)
    if recent_failures >= 3:
        return self._get_previous_stratum(current)

    return None  # No demotion needed
```

**Triggers de Demotion:**
- ❌ Failure rate **>10%**
- ❌ **ANY** regression detectada
- ❌ **3+ failures** en últimos 10 runs

---

### **Fase 5: Almacenamiento en PatternBank y Reutilización**

**Archivo:** `src/cognitive/patterns/pattern_bank.py`

Una vez que un patrón es **PROMOTED**, se almacena en el **PatternBank** con embeddings duales:

#### **Dual Embeddings (GraphCodeBERT + Sentence-BERT)**

```python
def store_pattern(
    self,
    signature: SemanticTaskSignature,
    code: str,
    success_rate: float
) -> str:
    # 1. Valida threshold (≥95% success rate)
    if success_rate < 0.95:
        raise ValueError("success_rate must be ≥ 0.95")

    # 2. Genera dual embeddings
    if self.enable_dual_embeddings:
        pattern_dict = {
            'code': code,
            'description': signature.purpose,
            'pattern_id': pattern_id
        }
        dual_emb = self.dual_generator.generate_batch([pattern_dict])[0]

        code_embedding = dual_emb.code_embedding      # GraphCodeBERT 768-dim
        semantic_embedding = dual_emb.semantic_embedding  # Sentence-BERT 384-dim

    # 3. Almacena en AMBAS colecciones de Qdrant
    # - devmatrix_patterns (code embeddings)
    # - semantic_patterns (semantic embeddings)

    # 4. Metadata enriquecida
    metadata = {
        "pattern_id": pattern_id,
        "purpose": signature.purpose,
        "domain": signature.domain,
        "category": classification_result.category,
        "code": code,
        "success_rate": success_rate,
        "usage_count": 0,
        "created_at": datetime.utcnow().isoformat(),

        # Production readiness (Task Group 8)
        "production_ready": False,
        "production_readiness_score": production_score,
        "test_coverage": 0.0,
        "security_level": security_level,
        "performance_tier": performance_tier,
    }

    return pattern_id
```

**Dual Embeddings Explicados:**

| Embedding | Modelo | Dimensiones | Propósito |
|-----------|--------|-------------|-----------|
| Code | GraphCodeBERT | 768 | Captura estructura sintáctica del código |
| Semantic | Sentence-BERT | 384 | Captura significado semántico del propósito |

#### **Búsqueda Inteligente con Fallback**

```python
def search_with_fallback(
    self,
    signature: SemanticTaskSignature,
    top_k: int = 5,
    min_results: int = 3,
) -> List[StoredPattern]:
    """TG4: Adaptive thresholds + TG5: Keyword fallback"""

    # 1. Threshold adaptativo por dominio
    domain_thresholds = {
        "crud": 0.60,
        "custom": 0.65,
        "payment": 0.70,
        "workflow": 0.65,
    }
    adaptive_threshold = domain_thresholds.get(
        signature.domain.lower(), 0.60
    )

    # 2. Búsqueda semántica
    semantic_results = self.search_patterns(
        signature,
        top_k=top_k,
        similarity_threshold=adaptive_threshold,
    )

    # 3. Si hay suficientes resultados, devolver
    if len(semantic_results) >= min_results:
        return semantic_results

    # 4. TG5: Keyword Fallback
    logger.info("🔄 TG5: Triggering keyword fallback")

    # Extrae keywords
    keywords = self._extract_keywords(signature.purpose)

    # Mapea a pattern types
    keyword_patterns = set()
    for keyword in keywords:
        pattern_type = self._keyword_to_pattern_type(keyword)
        if pattern_type:
            keyword_patterns.add(pattern_type)

    # Búsqueda más amplia con threshold bajo
    broad_results = self.search_patterns(
        signature,
        top_k=top_k * 2,
        similarity_threshold=0.4,  # Very low
    )

    # Filtra por keyword match
    keyword_results = [
        pattern for pattern in broad_results
        if self._matches_keywords(pattern, keyword_patterns)
    ]

    # 5. Combina y deduplica
    combined = self._deduplicate(semantic_results + keyword_results)

    # 6. Ordena por similarity y limita a top_k
    combined.sort(key=lambda p: p.similarity_score, reverse=True)
    return combined[:top_k]
```

**Thresholds Adaptativos por Dominio:**

| Dominio | Threshold | Razón |
|---------|-----------|-------|
| CRUD | 0.60 | Operaciones estándar, más variaciones válidas |
| Custom | 0.65 | Lógica específica, mayor precisión requerida |
| Payment | 0.70 | Crítico, requiere exactitud máxima |
| Workflow | 0.65 | Lógica de negocio, precisión moderada |

**Keyword Fallback (TG5):**

Cuando la búsqueda semántica no encuentra suficientes resultados (< `min_results`):

1. **Extrae keywords** del `signature.purpose`
2. **Mapea keywords → pattern types** (ej: "create" → "crud", "auth" → "auth")
3. **Búsqueda amplia** con threshold muy bajo (0.4)
4. **Filtra** por keyword matches
5. **Combina** con resultados semánticos
6. **Ordena** por similarity score

---

## 🔄 Ciclo Completo de Promoción

```
┌────────────────────────────────────────────────────┐
│   PATTERN PROMOTION PIPELINE (Milestone 4)        │
└────────────────────────────────────────────────────┘

1️⃣  CODE GENERATION
    ├─ LLM genera código
    ├─ Se ejecutan tests
    └─ Se valida sintaxis/semántica

2️⃣  REGISTRATION
    ├─ PatternFeedbackIntegration.register_successful_generation()
    ├─ QualityEvaluator.store_candidate()
    └─ Metadata: test_results, validation_results

3️⃣  EXECUTION TRACKING
    ├─ QualityEvaluator.track_execution_results()
    │   └─ Tests passed/total, coverage, execution time
    └─ QualityEvaluator.track_validation_results()
        └─ Rules passed/total, type hints coverage

4️⃣  QUALITY CALCULATION
    ├─ QualityEvaluator.calculate_quality_metrics()
    │   ├─ success_rate (35%)
    │   ├─ test_coverage (35%)
    │   ├─ validation_score (20%)
    │   └─ performance_score (10%)
    └─ Overall quality = weighted average

5️⃣  PATTERN ANALYSIS
    ├─ PatternAnalyzer.score_reusability()
    │   └─ Checks: hardcoded values, params, type hints, docs
    ├─ PatternAnalyzer.analyze_security()
    │   └─ Checks: secrets, SQL injection, eval/exec
    └─ PatternAnalyzer.analyze_code_quality()
        └─ Checks: nesting, error handling, logging

6️⃣  PROMOTION SCORING
    ├─ Calculate composite score:
    │   promotion_score = 0.4*quality + 0.3*reusability +
    │                     0.2*security + 0.1*code_quality
    ├─ Get domain threshold (adaptive)
    └─ Compare: promotion_score >= adjusted_threshold

7️⃣  DUAL VALIDATION
    ├─ RealDualValidator.validate_pattern()
    │   ├─ Success rate ≥ 95%?
    │   ├─ Test coverage ≥ 80%?
    │   ├─ Security level ≥ MEDIUM?
    │   ├─ Performance score ≥ 0.70?
    │   └─ Quality score ≥ 0.75?
    └─ should_promote = all criteria met

8️⃣  PROMOTION/REJECTION
    ├─ If approved:
    │   ├─ candidate.status = PromotionStatus.PROMOTED
    │   ├─ Store in PatternBank with embeddings
    │   ├─ Track usage count
    │   └─ Update ranking_score in Neo4j DAG
    └─ If rejected:
        ├─ candidate.status = PromotionStatus.REJECTED
        ├─ Log blocking issues
        └─ Track for learning (adjust thresholds)

9️⃣  REUSE
    ├─ Future generations search PatternBank
    ├─ Semantic similarity + keyword fallback
    ├─ DAG-based ranking boost
    └─ Increment usage_count on retrieval
```

---

## 💻 Uso en el Pipeline E2E

### **Phase 1: Inicialización de Servicios**

**Archivo:** `tests/e2e/real_e2e_full_pipeline.py:1254`

```python
async def _initialize_services(self):
    """Initialize real cognitive services with minimal output"""

    # 1. PatternBank - almacena patterns promovidos
    self.pattern_bank = PatternBank()
    self.pattern_bank.connect()

    # 2. ErrorPatternStore - guarda errores/éxitos
    self.error_pattern_store = ErrorPatternStore()

    # 3. PatternFeedbackIntegration - orquestador
    self.feedback_integration = PatternFeedbackIntegration(
        enable_auto_promotion=False,  # Manual control for testing
        mock_dual_validator=True       # Use mock for testing
    )
```

### **Phase 2: Búsqueda de Patterns Durante Generación**

**Archivo:** `tests/e2e/real_e2e_full_pipeline.py:2097`

```python
# Para cada requirement, buscar patterns existentes
for req in self.requirements:
    signature = SemanticTaskSignature(
        purpose=req.description,
        inputs={"request": "dict"},
        outputs={"code": "str"},
        domain="api_development"
    )

    # TG4 (adaptive thresholds) + TG5 (keyword fallback)
    results = self.pattern_bank.search_with_fallback(
        signature=signature,
        top_k=10,
        min_results=3  # Trigger keyword fallback if < 3 results
    )

    if results:
        logger.info(f"🔍 Found {len(results)} matching patterns")
        self.patterns_matched.extend(results)
```

### **Phase 8: Learning Durante Code Repair**

**Archivo:** `tests/e2e/real_e2e_full_pipeline.py:3026`

```python
async def _phase_8_code_repair(self):
    """Code Repair con learning activo"""

    # Repair loop
    for iteration in range(max_iterations):
        # Step 2: Buscar patterns similares
        if self.error_pattern_store:
            similar_patterns = await self.error_pattern_store.search_similar_errors(
                task_description=f"Phase 6.5 Code Repair - {self.spec_name}",
                error_message=compliance_failures,
                top_k=3
            )
            pattern_reuse_count += len(similar_patterns)

        # Step 3-6: Aplicar repairs y validar
        repair_result = await self.code_repair_agent.repair(...)
        new_compliance_report = self.compliance_validator.validate_from_app(...)

        # Step 7: Detectar regresión
        if new_compliance < current_compliance:
            # Store failed repair pattern
            await self.error_pattern_store.store_error(
                ErrorPattern(
                    error_id=str(uuid4()),
                    task_description=f"Phase 6.5 Code Repair - {self.spec_name}",
                    error_type="regression",
                    error_message=f"Regression: {current:.1%} → {new:.1%}",
                    failed_code=str(repair_result)[:500],
                    attempt=iteration,
                    metadata={
                        "compliance_before": current_compliance,
                        "compliance_after": new_compliance,
                        "regression": True
                    }
                )
            )
        else:
            # Step 8: Store successful repair pattern
            await self.error_pattern_store.store_success(
                SuccessPattern(
                    success_id=str(uuid4()),
                    task_description=f"Phase 6.5 Code Repair - {self.spec_name}",
                    generated_code=str(repair_result)[:1000],
                    quality_score=new_compliance,
                    metadata={
                        "compliance_after": new_compliance,
                        "tests_fixed": tests_fixed,
                        "spec_name": self.spec_name
                    }
                )
            )
```

### **Phase 11: Learning Post-Generación**

**Archivo:** `tests/e2e/real_e2e_full_pipeline.py:4739`

```python
async def _phase_11_learning(self):
    """Phase 10: Learning - Store successful patterns for future reuse"""

    if not self.feedback_integration:
        logger.warning("PatternFeedbackIntegration not available")
        return

    # Register successful code generation
    if self.execution_successful:
        # Combine all generated Python code
        combined_code = "\n\n".join([
            f"# File: {filename}\n{content}"
            for filename, content in self.generated_code.items()
            if filename.endswith('.py')
        ])

        # Create execution result
        execution_result = self._create_execution_result()

        # Register with feedback system
        candidate_id = await self.feedback_integration.register_successful_generation(
            code=combined_code,
            signature=self.task_signature,
            execution_result=execution_result,
            task_id=uuid4(),
            metadata={
                "spec_name": self.spec_name,
                "patterns_matched": len(self.patterns_matched),
                "duration_ms": self.metrics_collector.metrics.total_duration_ms,
                "files_generated": len(self.generated_code),
                "requirements_count": len(self.requirements)
            }
        )

        logger.info(f"✅ Pattern candidate registered: {candidate_id}")

    # Check for patterns ready for promotion
    promotion_stats = self.feedback_integration.check_and_promote_ready_patterns()

    logger.info(f"📊 Promotion Results:")
    logger.info(f"  - Total candidates: {promotion_stats.get('total_candidates', 0)}")
    logger.info(f"  - Promoted: {promotion_stats.get('promotions_succeeded', 0)}")
    logger.info(f"  - Failed: {promotion_stats.get('promotions_failed', 0)}")

    # Update metrics
    self.metrics_collector.metrics.patterns_stored = 1 if self.execution_successful else 0
    self.metrics_collector.metrics.patterns_promoted = promotion_stats.get("promotions_succeeded", 0)
    self.metrics_collector.metrics.candidates_created = 1 if self.execution_successful else 0
```

---

## 📈 Métricas del Sistema de Learning

**Archivo:** `src/services/error_pattern_analyzer.py`

El sistema mide su propia efectividad:

```python
async def calculate_learning_effectiveness(
    self,
    time_window_hours: int = 24
) -> LearningMetrics:
    # 1. Total errors en ventana de tiempo
    total_errors = neo4j_query("MATCH (e:CodeGenerationError) WHERE ...")

    # 2. Errors donde se usó feedback (attempt > 1)
    errors_with_feedback = neo4j_query("... WHERE e.attempt > 1")

    # 3. Success rates con/sin feedback
    with_feedback_stats = neo4j_query("... WHERE used_feedback = true")
    without_feedback_stats = neo4j_query("... WHERE used_feedback = false")

    success_rate_with = with_fb_successes / with_fb_total
    success_rate_without = without_fb_successes / without_fb_total

    # 4. Improvement percentage
    improvement = (
        (success_rate_with - success_rate_without) /
        success_rate_without * 100
    )

    return LearningMetrics(
        total_errors=total_errors,
        errors_with_feedback=errors_with_feedback,
        success_rate_without_feedback=success_rate_without,
        success_rate_with_feedback=success_rate_with,
        improvement_percentage=improvement,
        avg_retries_with_feedback=avg_retries_with,
        avg_retries_without_feedback=avg_retries_without,
    )
```

**Métricas Clave:**

| Métrica | Descripción | Objetivo |
|---------|-------------|----------|
| `total_errors` | Total de errores en ventana de tiempo | Monitor general |
| `errors_with_feedback` | Errores que usaron feedback | Uso del sistema |
| `success_rate_without_feedback` | Success rate sin learning | Baseline |
| `success_rate_with_feedback` | Success rate con learning | Efectividad |
| `improvement_percentage` | % mejora con learning | **KPI Principal** |
| `avg_retries_with_feedback` | Promedio de reintentos con feedback | Eficiencia |
| `avg_retries_without_feedback` | Promedio de reintentos sin feedback | Comparación |

---

## 🎯 Puntos Clave del Sistema de Learning

### **1. Captura de Patrones Exitosos**

✅ **Threshold estricto:** Solo patrones con ≥95% success rate
✅ **Validación múltiple:** Tests + validations + métricas de calidad
✅ **Embeddings code-aware:** GraphCodeBERT entiende sintaxis y semántica
✅ **Metadata rica:** Domain, security level, performance tier, usage count

### **2. Almacenamiento Dual (Neo4j + Qdrant)**

```
Neo4j (Relacional):
├─ Queries complejas
├─ Análisis de tendencias
├─ Detección de errores recurrentes
└─ DAG de dependencias

Qdrant (Vectorial):
├─ Búsqueda semántica ultrarrápida
├─ Cosine similarity
├─ GraphCodeBERT embeddings (768D)
└─ Sentence-BERT embeddings (384D)
```

### **3. Sistema de Promoción Multi-Nivel**

```python
# Filosofía: Conservative promotion, aggressive demotion

Promotion Requirements (LLM → AST):
✅ 95% success rate
✅ 10+ successful runs
✅ 0 regressions
✅ 3 days stability
✅ 3+ distinct projects
✅ 100% semantic compliance
✅ <50% generation time variance

Promotion Requirements (AST → TEMPLATE):
✅ 99% success rate
✅ 50+ successful runs
✅ 0 regressions
✅ 14 days stability
✅ 5+ distinct projects
✅ 100% semantic compliance
✅ <10% generation time variance
✅ Context-independent (no project-specific code)
✅ 🔒 Human review required

Demotion Triggers (INSTANT):
❌ >10% failure rate
❌ ANY regression detected
❌ 3+ failures in last 10 runs
```

### **4. Reutilización Inteligente**

#### **Búsqueda Semántica:**
```python
query_text = "Create a new user"
query_embedding = encode(query_text)  # 768-dim vector

# Busca en Qdrant con cosine similarity
results = qdrant.search(
    collection_name="semantic_patterns",
    query_vector=query_embedding,
    score_threshold=0.60,  # Adaptive per domain
    limit=5
)
```

#### **Ranking con DAG (Milestone 3):**
```python
def _get_dag_ranking_score(pattern_id: str) -> float:
    # Formula:
    # Base: Pattern's Neo4j ranking_score (0.0-1.0)
    # Boost: Recent successes (+0.10 if within 7 days)
    # Penalty: Failed executions (-0.05 per failure)
    # Efficiency: Fast + low memory (+0.03 if <5s and <256MB)

    base_score = neo4j_query(pattern_id).ranking_score

    if has_recent_successes(pattern_id):
        base_score += 0.10

    failures = count_recent_failures(pattern_id)
    base_score -= 0.05 * failures

    if is_resource_efficient(pattern_id):
        base_score += 0.03

    return clamp(base_score, 0.0, 1.0)
```

---

## 🎓 Conclusiones Clave

Tu sistema de learning es **production-grade machine learning** integrado directamente en el pipeline de código. Las características más destacadas son:

### **1. Dual Storage Strategy**
- **Neo4j** para relaciones y queries complejas
- **Qdrant** para búsqueda semántica ultrarrápida

### **2. Multi-Level Trust System (Stratum)**
- **Promoción conservadora** (earn trust slowly)
- **Demotion agresiva** (lose trust quickly)
- **Thresholds adaptativos** por dominio

### **3. Comprehensive Quality Scoring**
- Quality metrics (tests + coverage + validation)
- Pattern analysis (reusability + security + code quality)
- Dual LLM validation (Claude + GPT-4)
- Composite promotion score (weighted formula)

### **4. Intelligent Retrieval**
- Semantic search con GraphCodeBERT embeddings
- Adaptive thresholds por dominio
- Keyword fallback cuando no hay matches semánticos
- DAG-based ranking (execution success boosts ranking)

### **5. Self-Measuring System**
- Learning effectiveness metrics
- Recurring error detection
- Problematic task identification
- Improvement recommendations

**El flujo completo:**
```
Code Generation → Validation → Registration → Analysis → Scoring →
Dual Validation → Promotion/Demotion → PatternBank Storage →
Reuse in Future Generations → Feedback Loop Closes
```

Es un sistema que literalmente **aprende de sus errores y éxitos**, mejorando continuamente la calidad del código generado. 🚀

---

## 📚 Referencias

### Archivos Principales del Sistema

```
Core Learning Components:
├─ src/cognitive/patterns/pattern_feedback_integration.py
├─ src/cognitive/patterns/pattern_bank.py
├─ src/cognitive/patterns/pattern_analyzer.py
├─ src/cognitive/patterns/dual_validator.py
├─ src/services/error_pattern_store.py
├─ src/services/pattern_promoter.py
└─ tests/e2e/real_e2e_full_pipeline.py

Supporting Services:
├─ src/services/code_generation_service.py
├─ src/services/error_pattern_analyzer.py
└─ src/cognitive/planning/multi_pass_planner.py
```

### Tecnologías Clave

- **GraphCodeBERT:** 768-dimensional code embeddings
- **Sentence-BERT:** 384-dimensional semantic embeddings
- **Qdrant:** Vector database para búsqueda semántica
- **Neo4j:** Graph database para relaciones y DAG
- **Claude + GPT-4:** Dual LLM validation

---

**Última actualización:** 2025-11-28
**Estado:** Producción - Sistema activo en E2E pipeline
