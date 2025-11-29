# Learning System Overview

## Estado Actual vs Objetivo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LEARNING SYSTEM MAP                                   │
│                                                                              │
│  ESTADO ACTUAL:                          OBJETIVO:                          │
│  ═══════════════                         ════════                           │
│                                                                              │
│  Smoke → Repair → ✅ FixPatternLearner   Smoke → CodeGen → ✅ Prevention    │
│              │                                        ↑                      │
│              └── Solo aprende repairs    ┌───────────┘                      │
│                                          │                                   │
│                                   NegativePatternStore                      │
│                                   PromptEnhancer                            │
│                                   FeedbackCollector                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes de Learning

### Existentes (Funcionando)

| Componente | Archivo | Función | Gap |
|------------|---------|---------|-----|
| **FixPatternLearner** | `smoke_test_pattern_adapter.py` | Guarda fix patterns exitosos | Solo repairs |
| **SmokeTestPatternAdapter** | `smoke_test_pattern_adapter.py` | Score patterns por smoke results | No afecta code gen |
| **RepairConfidenceModel** | `repair_confidence_model.py` | Ranking de repair candidates | Solo repairs |
| **ConstraintLearningService** | `constraint_learning_service.py` | Aprende constraints de IR | No feedback loop |

### A Implementar (Plan)

| Componente | Archivo | Función | Prioridad |
|------------|---------|---------|-----------|
| **NegativePatternStore** | `learning/negative_pattern_store.py` | Guarda anti-patterns para code gen | P0 |
| **SmokeFeedbackClassifier** | `learning/smoke_feedback_classifier.py` | Clasifica smoke errors → IR context | P0 |
| **PromptEnhancer** | `learning/prompt_enhancer.py` | Inyecta anti-patterns en prompts | P0 |
| **FeedbackCollector** | `learning/feedback_collector.py` | Orquesta el feedback loop | P1 |

---

## Flujos de Datos

### Flujo Actual (Repair Learning)

```
SmokeTestResult
    │
    ▼
RuntimeSmokeRepair ─────────────────────────────────────┐
    │                                                   │
    ▼                                                   ▼
CodeRepairAgent.repair_from_smoke()     FixPatternLearner.record_repair_attempt()
    │                                                   │
    ▼                                                   ▼
RepairFix (applied)                     Neo4j: FixPattern node
    │
    ▼
Next run: FixPatternLearner.get_known_fix() → Skip LLM if match
```

### Flujo Objetivo (Generation Learning)

```
SmokeTestResult
    │
    ├───────────────────────────────────────────────────┐
    │                                                   │
    ▼                                                   ▼
RuntimeSmokeRepair                      FeedbackCollector.process_smoke_results()
    │                                                   │
    │                                                   ▼
    │                                   SmokeFeedbackClassifier.classify_for_generation()
    │                                                   │
    │                                                   ▼
    │                                   NegativePatternStore.store()
    │                                                   │
    │                                                   ▼
    │                                   Neo4j: GenerationAntiPattern node
    │
    │
NEXT RUN:
    │
    ▼
CodeGenerationService.generate_*()
    │
    ▼
PromptEnhancer.enhance_*_prompt()
    │
    ▼
NegativePatternStore.get_patterns_for_*()
    │
    ▼
Enhanced prompt with "AVOID THESE KNOWN ISSUES: ..."
    │
    ▼
LLM generates CORRECT code (avoids known mistakes)
```

---

## Neo4j Schema

### Nodos Existentes

```cypher
// Fix patterns (repair learning)
(:FixPattern {
    pattern_id: String,
    error_type: String,
    endpoint_pattern: String,
    exception_class: String,
    fix_type: String,
    fix_template: String,
    success_count: Integer,
    failure_count: Integer
})

// Constraint learning
(:ConstraintPattern {
    constraint_type: String,
    entity_pattern: String,
    field_pattern: String,
    frequency: Integer
})

// Smoke test patterns
(:SmokeTestPattern {
    pattern_id: String,
    endpoint_pattern: String,
    method: String,
    score: Float
})
```

### Nodos a Agregar

```cypher
// Generation anti-patterns (NEW)
(:GenerationAntiPattern {
    pattern_id: String,
    error_type: String,
    exception_class: String,
    error_message_pattern: String,
    entity_pattern: String,
    endpoint_pattern: String,
    field_pattern: String,
    bad_code_snippet: String,
    correct_code_snippet: String,
    occurrence_count: Integer,
    times_prevented: Integer,
    last_seen: DateTime
})

// Links
(:GenerationAntiPattern)-[:AFFECTS_ENTITY]->(:EntityIR)
(:GenerationAntiPattern)-[:AFFECTS_ENDPOINT]->(:EndpointIR)
(:GenerationAntiPattern)-[:DERIVED_FROM]->(:SmokeTestResult)
```

---

## Metrics Dashboard

### Current Metrics

| Metric | Valor | Fuente |
|--------|-------|--------|
| Fix patterns stored | ? | `FixPattern` count |
| Fix pattern success rate | ? | avg(success_count/(success+failure)) |
| Repair skips (known fix) | ? | logs |

### Target Metrics (Post-Implementation)

| Metric | Target | Fuente |
|--------|--------|--------|
| Anti-patterns stored | 50+ | `GenerationAntiPattern` count |
| Prevention rate | >70% | times_prevented/(occurrence+prevented) |
| Generation errors/run | <5 | smoke violations |
| Time to convergence | 3 runs | runs until 0 errors |

---

## Implementation Roadmap

```
Week 1: Core Infrastructure
├── Day 1-2: NegativePatternStore + Neo4j schema
├── Day 3-4: SmokeFeedbackClassifier
└── Day 5: Unit tests

Week 2: Integration
├── Day 1-2: PromptEnhancer + CodeGenerationService integration
├── Day 3-4: FeedbackCollector + E2E integration
└── Day 5: E2E validation
```

---

## Related Documents

- [GENERATION_FEEDBACK_LOOP.md](./GENERATION_FEEDBACK_LOOP.md) - Detailed implementation plan
- [SMOKE_DRIVEN_REPAIR_ARCHITECTURE.md](../SMOKE_DRIVEN_REPAIR_ARCHITECTURE.md) - Current repair system
- [SMOKE_TEST_PATTERN_ADAPTER.md](../neo4j/DATA_STRUCTURES_INVENTORY.md) - Pattern storage

---

**Estado**: ✅ IMPLEMENTADO (2025-11-29)
**Prioridad**: Alta - Bloquea mejora en smoke pass rate
**Esfuerzo real**: ~4h

## Archivos Implementados

| Archivo | Descripción |
|---------|-------------|
| `src/learning/__init__.py` | Module exports |
| `src/learning/negative_pattern_store.py` | Neo4j persistence for GenerationAntiPattern |
| `src/learning/smoke_feedback_classifier.py` | Error→IR context mapping |
| `src/learning/prompt_enhancer.py` | Injects anti-patterns into prompts |
| `src/learning/feedback_collector.py` | Orchestrates the feedback loop |

## Integraciones

- **CodeGenerationService** (`src/services/code_generation_service.py`): `_get_avoidance_context()` ahora usa NegativePatternStore
- **E2E Pipeline** (`tests/e2e/real_e2e_full_pipeline.py`): `_process_smoke_result()` llama a FeedbackCollector
