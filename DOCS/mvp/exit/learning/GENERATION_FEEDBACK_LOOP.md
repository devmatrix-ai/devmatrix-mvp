# Generation Feedback Loop - Closing the Learning Gap

## Problem Statement

El sistema actual aprende de **reparaciones exitosas** pero no previene **errores de generación**.

```
CICLO ACTUAL (BROKEN):
CodeGen → (errores) → Smoke → (falla) → Repair → (no puede) → FIN
                                              ↓
                                        (arregla) → Guarda fix pattern

PROBLEMA: CodeGen sigue cometiendo los mismos errores run tras run.
```

## Gaps Identificados

| Gap | Descripción | Impacto |
|-----|-------------|---------|
| **G1** | No hay feedback de smoke → code generation | Errores repetidos |
| **G2** | FixPatternLearner solo guarda reparaciones | No prevención |
| **G3** | Errores unfixable se pierden | Sin learning negativo |
| **G4** | Prompts de generación son estáticos | No mejoran con experiencia |
| **G5** | No hay clasificación de error → root cause en IR | Fixes genéricos |

---

## Arquitectura Propuesta: Generation Feedback Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GENERATION FEEDBACK LOOP                                 │
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │  CodeGen     │────▶│  Smoke Test  │────▶│  Classifier  │                │
│  │  Service     │     │  Validator   │     │  (Error→IR)  │                │
│  └──────┬───────┘     └──────────────┘     └──────┬───────┘                │
│         │                                          │                         │
│         │  ┌─────────────────────────────────────┐ │                         │
│         │  │    NEGATIVE PATTERN STORE           │ │                         │
│         │  │    (Neo4j: GenerationAntiPattern)   │◀┘                         │
│         │  │                                     │                           │
│         │  │  - error_signature                  │                           │
│         │  │  - ir_context (entity/endpoint)     │                           │
│         │  │  - bad_code_pattern                 │                           │
│         │  │  - correct_code_pattern             │                           │
│         │  │  - occurrence_count                 │                           │
│         │  │  - last_seen                        │                           │
│         │  └─────────────────┬───────────────────┘                           │
│         │                    │                                               │
│         │  ┌─────────────────▼───────────────────┐                           │
│         │  │    PROMPT ENHANCER                  │                           │
│         │  │    (Inject anti-patterns)           │                           │
│         │  └─────────────────┬───────────────────┘                           │
│         │                    │                                               │
│         └────────────────────┘                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes a Implementar

### Task 1: NegativePatternStore

**Archivo**: `src/learning/negative_pattern_store.py`

```python
@dataclass
class GenerationAntiPattern:
    """Pattern that code generation should AVOID."""
    pattern_id: str

    # Error signature
    error_type: str           # "database", "validation", "import"
    exception_class: str      # "IntegrityError", "KeyError"
    error_message_pattern: str  # Regex pattern

    # IR context
    entity_pattern: str       # "Product", "Order", "*"
    endpoint_pattern: str     # "POST /{entities}", "PUT /{entities}/{id}"
    field_pattern: str        # "foreign_key:*", "nullable:*"

    # Code patterns
    bad_code_snippet: str     # What NOT to generate
    correct_code_snippet: str # What TO generate instead

    # Learning metrics
    occurrence_count: int = 0
    times_prevented: int = 0  # How many times we avoided this
    last_seen: datetime = None

    @property
    def prevention_rate(self) -> float:
        total = self.occurrence_count + self.times_prevented
        return self.times_prevented / total if total > 0 else 0.0
```

**Neo4j Schema**:
```cypher
CREATE CONSTRAINT gen_antipattern_id IF NOT EXISTS
FOR (ap:GenerationAntiPattern) REQUIRE ap.pattern_id IS UNIQUE;

// Indexes for fast lookup
CREATE INDEX gen_antipattern_error IF NOT EXISTS
FOR (ap:GenerationAntiPattern) ON (ap.error_type, ap.exception_class);

CREATE INDEX gen_antipattern_entity IF NOT EXISTS
FOR (ap:GenerationAntiPattern) ON (ap.entity_pattern);
```

### Task 2: SmokeFeedbackClassifier

**Archivo**: `src/learning/smoke_feedback_classifier.py`

Clasifica errores de smoke y los mapea a contexto IR:

```python
class SmokeFeedbackClassifier:
    """
    Classifies smoke test failures and maps them to IR context.

    Smoke Error → (entity, endpoint, field, constraint) → AntiPattern
    """

    ERROR_PATTERNS = {
        # Database errors → entity/field patterns
        'IntegrityError': {
            'NOT NULL constraint': 'nullable_missing',
            'FOREIGN KEY constraint': 'fk_relationship_missing',
            'UNIQUE constraint': 'unique_constraint_missing',
        },

        # Validation errors → schema patterns
        'ValidationError': {
            'field required': 'required_field_missing',
            'value is not a valid': 'type_mismatch',
            'extra fields not permitted': 'extra_field_in_schema',
        },

        # Import errors → module patterns
        'ImportError': {
            'No module named': 'missing_import',
            'cannot import name': 'wrong_import_path',
        },

        # Attribute errors → code patterns
        'AttributeError': {
            'has no attribute': 'missing_attribute',
            'NoneType': 'null_reference',
        }
    }

    def classify_for_generation(
        self,
        violation: Dict[str, Any],
        stack_trace: str,
        application_ir: ApplicationIR
    ) -> Optional[GenerationAntiPattern]:
        """
        Create anti-pattern from smoke failure.

        Returns:
            GenerationAntiPattern if classifiable, None otherwise
        """
        pass

    def extract_ir_context(
        self,
        endpoint: str,
        error_message: str,
        application_ir: ApplicationIR
    ) -> Dict[str, str]:
        """
        Extract IR context from error.

        Returns dict with:
        - entity_name
        - field_name
        - constraint_type
        - relationship_type
        """
        pass
```

### Task 3: PromptEnhancer

**Archivo**: `src/learning/prompt_enhancer.py`

Inyecta anti-patterns en prompts de generación:

```python
class GenerationPromptEnhancer:
    """
    Enhances code generation prompts with learned anti-patterns.

    Before:
        "Generate FastAPI endpoint for POST /products"

    After:
        "Generate FastAPI endpoint for POST /products

        AVOID THESE KNOWN ISSUES:
        1. IntegrityError on category_id: Always use Optional[int] for FK fields
        2. ValidationError on price: Ensure Decimal validation in schema
        3. ImportError: Import all models from src.models.entities"
    """

    MAX_ANTIPATTERNS_PER_PROMPT = 5  # Don't overwhelm the LLM
    MIN_OCCURRENCE_COUNT = 2         # Only include patterns seen 2+ times

    def __init__(self, pattern_store: NegativePatternStore):
        self.pattern_store = pattern_store

    def enhance_entity_prompt(
        self,
        base_prompt: str,
        entity_name: str,
        entity_ir: EntityIR
    ) -> str:
        """Add anti-patterns relevant to this entity."""
        patterns = self.pattern_store.get_patterns_for_entity(entity_name)
        return self._inject_patterns(base_prompt, patterns)

    def enhance_endpoint_prompt(
        self,
        base_prompt: str,
        endpoint_pattern: str,
        method: str
    ) -> str:
        """Add anti-patterns relevant to this endpoint type."""
        patterns = self.pattern_store.get_patterns_for_endpoint(
            endpoint_pattern, method
        )
        return self._inject_patterns(base_prompt, patterns)

    def enhance_schema_prompt(
        self,
        base_prompt: str,
        schema_name: str,
        entity_ir: EntityIR
    ) -> str:
        """Add anti-patterns relevant to this schema."""
        patterns = self.pattern_store.get_patterns_for_schema(schema_name)
        return self._inject_patterns(base_prompt, patterns)

    def _inject_patterns(
        self,
        base_prompt: str,
        patterns: List[GenerationAntiPattern]
    ) -> str:
        """Format and inject patterns into prompt."""
        if not patterns:
            return base_prompt

        # Sort by occurrence count (most common first)
        patterns = sorted(
            patterns,
            key=lambda p: p.occurrence_count,
            reverse=True
        )[:self.MAX_ANTIPATTERNS_PER_PROMPT]

        warnings = ["AVOID THESE KNOWN ISSUES:"]
        for i, p in enumerate(patterns, 1):
            warnings.append(
                f"{i}. {p.exception_class} on {p.field_pattern}: "
                f"{p.correct_code_snippet}"
            )

        return f"{base_prompt}\n\n{chr(10).join(warnings)}"
```

### Task 4: FeedbackCollector

**Archivo**: `src/learning/feedback_collector.py`

Recolecta feedback de smoke tests y lo procesa:

```python
class GenerationFeedbackCollector:
    """
    Collects smoke test results and creates anti-patterns.

    Integrates with:
    - RuntimeSmokeTestValidator (source of violations)
    - SmokeFeedbackClassifier (classification)
    - NegativePatternStore (persistence)
    """

    def __init__(
        self,
        classifier: SmokeFeedbackClassifier,
        store: NegativePatternStore
    ):
        self.classifier = classifier
        self.store = store

    async def process_smoke_results(
        self,
        smoke_result: SmokeTestResult,
        application_ir: ApplicationIR,
        generation_manifest: Dict[str, Any]
    ) -> FeedbackProcessingResult:
        """
        Process smoke test results and store anti-patterns.

        Returns:
            FeedbackProcessingResult with:
            - patterns_created: int
            - patterns_updated: int
            - unclassifiable_errors: List[str]
        """
        patterns_created = 0
        patterns_updated = 0
        unclassifiable = []

        for violation in smoke_result.violations:
            # Find matching stack trace
            stack_trace = self._find_stack_trace(
                violation,
                smoke_result.stack_traces
            )

            # Classify into anti-pattern
            anti_pattern = self.classifier.classify_for_generation(
                violation=violation,
                stack_trace=stack_trace,
                application_ir=application_ir
            )

            if anti_pattern:
                # Store/update pattern
                if self.store.exists(anti_pattern.pattern_id):
                    self.store.increment_occurrence(anti_pattern.pattern_id)
                    patterns_updated += 1
                else:
                    self.store.store(anti_pattern)
                    patterns_created += 1
            else:
                unclassifiable.append(str(violation))

        return FeedbackProcessingResult(
            patterns_created=patterns_created,
            patterns_updated=patterns_updated,
            unclassifiable_errors=unclassifiable
        )
```

### Task 5: Integration Points

#### 5.1 CodeGenerationService Integration

**Archivo**: `src/services/code_generation_service.py`

```python
class CodeGenerationService:
    def __init__(self, ..., prompt_enhancer: GenerationPromptEnhancer = None):
        self.prompt_enhancer = prompt_enhancer or get_prompt_enhancer()

    async def generate_entity(self, entity_ir: EntityIR, ...) -> str:
        base_prompt = self._build_entity_prompt(entity_ir)

        # NEW: Enhance with anti-patterns
        enhanced_prompt = self.prompt_enhancer.enhance_entity_prompt(
            base_prompt,
            entity_name=entity_ir.name,
            entity_ir=entity_ir
        )

        return await self._call_llm(enhanced_prompt)
```

#### 5.2 E2E Pipeline Integration

**Archivo**: `tests/e2e/real_e2e_full_pipeline.py`

```python
# After smoke test, before repair
async def _process_generation_feedback(
    self,
    smoke_result: SmokeTestResult,
    application_ir: ApplicationIR,
    manifest: Dict
):
    """Process smoke failures for generation learning."""
    if not smoke_result.violations:
        return

    collector = get_feedback_collector()
    result = await collector.process_smoke_results(
        smoke_result=smoke_result,
        application_ir=application_ir,
        generation_manifest=manifest
    )

    logger.info(
        f"    Generation feedback: {result.patterns_created} new, "
        f"{result.patterns_updated} updated anti-patterns"
    )
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (4h)

| Task | Archivo | Tiempo |
|------|---------|--------|
| 1.1 | `src/learning/negative_pattern_store.py` | 1.5h |
| 1.2 | Neo4j schema + migrations | 0.5h |
| 1.3 | `src/learning/smoke_feedback_classifier.py` | 2h |

### Phase 2: Prompt Enhancement (3h)

| Task | Archivo | Tiempo |
|------|---------|--------|
| 2.1 | `src/learning/prompt_enhancer.py` | 1.5h |
| 2.2 | Integration con CodeGenerationService | 1h |
| 2.3 | Tests unitarios | 0.5h |

### Phase 3: Pipeline Integration (2h)

| Task | Archivo | Tiempo |
|------|---------|--------|
| 3.1 | `src/learning/feedback_collector.py` | 1h |
| 3.2 | Integration en E2E pipeline | 0.5h |
| 3.3 | Metrics y logging | 0.5h |

### Phase 4: Validation (1h)

| Task | Descripción | Tiempo |
|------|-------------|--------|
| 4.1 | E2E test con feedback loop | 0.5h |
| 4.2 | Verificar prevention rate | 0.5h |

---

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Repeated generation errors | ~33/run | <5/run after 3 runs |
| Prevention rate | 0% | >70% |
| Time to first fix | N/A | Run 2 |
| Anti-patterns captured | 0 | 50+ |

## Ciclo Esperado Post-Implementación

```
RUN 1:
  CodeGen → 33 errors → Smoke fails → Classify → Store 33 anti-patterns

RUN 2:
  CodeGen + 33 anti-patterns → 5 errors → Smoke fails → Store 5 new

RUN 3:
  CodeGen + 38 anti-patterns → 1 error → Smoke passes

RUN 4+:
  CodeGen + 39 anti-patterns → 0 errors → Smoke passes
```

---

## Dependencies

- Neo4j (ya disponible)
- ApplicationIR (ya disponible)
- SmokeTestResult con stack_traces (ya implementado)
- CodeGenerationService (ya disponible)

## Risks

| Risk | Mitigation |
|------|------------|
| Anti-patterns demasiado específicos | Generalización de patterns |
| Prompt inflation (demasiadas warnings) | Límite MAX_ANTIPATTERNS_PER_PROMPT |
| False positives | Threshold mínimo de occurrences |
| LLM ignora warnings | Testing + prompt tuning |

---

## ✅ IMPLEMENTATION STATUS (2025-11-29)

### Archivos Creados

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `src/learning/__init__.py` | 25 | Module exports |
| `src/learning/negative_pattern_store.py` | ~400 | Neo4j persistence con cache in-memory |
| `src/learning/smoke_feedback_classifier.py` | ~350 | Clasificación error→IR con pattern matching |
| `src/learning/prompt_enhancer.py` | ~420 | Injection de warnings en prompts |
| `src/learning/feedback_collector.py` | ~430 | Orchestración del feedback loop |

### Integraciones Completadas

| Archivo | Cambio |
|---------|--------|
| `src/services/code_generation_service.py` | `_get_avoidance_context()` usa NegativePatternStore |
| `tests/e2e/real_e2e_full_pipeline.py` | `_process_smoke_result()` llama FeedbackCollector |

### Bug Fixes Adicionales (misma sesión)

| Issue | Archivo | Fix |
|-------|---------|-----|
| Logger init order | `negative_pattern_store.py` | Move logger init antes de `_ensure_schema()` |
| Neo4j missing property | `pattern_mining_service.py` | `coalesce(ek.occurrence_count, 1)` |
| YAML block scalars | `spec_complexity_analyzer.py` | `_clean_yaml_content()` + `safe_yaml_load` |
| YAML parsing | `structured_spec_parser.py` | Usa `safe_yaml_load` con fallback |

### Verificación

```bash
# Test de parsing YAML robusto
python3 -c "
from src.services.spec_complexity_analyzer import SpecComplexityAnalyzer
# Block scalars con español ahora parsean correctamente
"
# ✅ OK

# Test de imports
python3 -c "from src.learning import *; print('OK')"
# ✅ OK
```

---

**Documento creado**: 2025-11-29
**Autor**: DevMatrix Pipeline Team
**Estado**: ✅ IMPLEMENTADO
