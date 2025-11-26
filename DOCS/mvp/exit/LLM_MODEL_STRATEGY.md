# LLM Model Strategy - DevMatrix

**Fecha**: Nov 26, 2025
**Status**: IMPLEMENTADO
**Prioridad**: ALTA

---

## Estrategia de Modelos

DevMatrix usa una estrategia de selección de modelos basada en complejidad de tareas:

| Tier | Modelo | Model ID | Uso |
|------|--------|----------|-----|
| **Opus** | Claude Opus 4.5 | `claude-opus-4-5-20251101` | Deep thinking, architecture, discovery |
| **Sonnet** | Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | Analysis, orchestration, validation |
| **Haiku** | Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Code gen, repair, tests, docs |

---

## Asignación por Componente

### Opus 4.5 (Deep Thinking)
Tareas que requieren razonamiento profundo y arquitectura:

| Componente | Archivo | Task Type |
|------------|---------|-----------|
| Discovery Agent | `src/services/discovery_agent.py` | `discovery` |
| MasterPlan Generator | `src/services/masterplan_generator.py` | `masterplan_generation` |

### Sonnet 4.5 (Analysis/Orchestration)
Tareas intermedias de análisis y coordinación:

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| Orchestrator Agent | `src/agents/orchestrator_agent.py` | Coordinación multi-agente |
| LLM Spec Normalizer | `src/services/llm_spec_normalizer.py` | Normalización semántica |
| Business Logic Extractor | `src/services/business_logic_extractor.py` | Extracción de lógica |
| Ensemble Validator | `src/cognitive/validation/ensemble_validator.py` | Validación con LLM |
| Code Review | Via ModelSelector | `code_review` |
| Validation | Via ModelSelector | `validation` |

### Haiku 4.5 (Code Tasks)
Tareas de generación/reparación de código:

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| Testing Agent | `src/agents/testing_agent.py` | Test generation |
| Documentation Agent | `src/agents/documentation_agent.py` | Docs generation |
| Implementation Agent | `src/agents/implementation_agent.py` | Code generation |
| Code Repair Agent | `src/mge/v2/agents/code_repair_agent.py` | Code fixes |
| Validation Extractor | `src/services/llm_validation_extractor.py` | Constraint extraction |
| Validation Code Gen | `src/services/validation_code_generator.py` | Validation code |
| Semantic Matcher | `src/services/semantic_matcher.py` | Constraint matching |

---

## ModelSelector Configuration

El `ModelSelector` (`src/llm/model_selector.py`) maneja el ruteo automático:

```python
class ClaudeModel(str, Enum):
    OPUS_4_5 = "claude-opus-4-5-20251101"      # Deep thinking
    SONNET_4_5 = "claude-sonnet-4-5-20250929"  # Analysis
    HAIKU_4_5 = "claude-haiku-4-5-20251001"    # Code tasks
```

### Selection Logic

```python
def _select_model_logic(self, task_type, complexity):
    # Rule 1: Deep thinking → Opus
    if task_type in [DISCOVERY, MASTERPLAN_GENERATION]:
        return OPUS_4_5

    # Rule 2: Code tasks → Haiku
    if task_type in [TASK_EXECUTION, CODE_REPAIR, TEST_GENERATION,
                      DOCUMENTATION, SUMMARY]:
        return HAIKU_4_5

    # Rule 3: Analysis → Sonnet
    if task_type in [CODE_REVIEW, VALIDATION]:
        return SONNET_4_5

    # Rule 4: Critical complexity → Opus
    if complexity == CRITICAL:
        return OPUS_4_5

    # Rule 5: High complexity → Sonnet
    if complexity == HIGH:
        return SONNET_4_5

    # Default → Haiku
    return HAIKU_4_5
```

---

## Pricing (Nov 2025)

| Modelo | Input/1M | Output/1M | Cached/1M |
|--------|----------|-----------|-----------|
| Opus 4.5 | $15.00 | $75.00 | $1.50 |
| Sonnet 4.5 | $3.00 | $15.00 | $0.30 |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 |

---

## Archivos Modificados

1. `src/llm/model_selector.py` - Core selection logic
2. `src/services/discovery_agent.py` - Opus
3. `src/services/llm_spec_normalizer.py` - Sonnet
4. `src/services/business_logic_extractor.py` - Sonnet
5. `src/services/semantic_matcher.py` - Haiku (actualizado de modelo 2024)
6. `src/agents/orchestrator_agent.py` - Sonnet
7. `src/cognitive/validation/ensemble_validator.py` - Sonnet
8. `src/services/code_generation_service.py` - Comentarios limpiados

---

## Bug Fix Importante

**Problema**: `SONNET_4_5` estaba apuntando incorrectamente a Haiku:
```python
# BUG - ANTES
SONNET_4_5 = "claude-haiku-4-5-20251001"  # ❌ WRONG!

# FIX - DESPUES
SONNET_4_5 = "claude-sonnet-4-5-20250929"  # ✅ CORRECT
```

Esto causaba que ~95% del codebase usara Haiku cuando debía usar Sonnet.

---

## Notas

- PRODUCTION_MODE checks removidos completamente
- Todos los archivos usan ahora la estrategia correcta
- ModelSelector es la fuente de verdad para selección de modelos
- Los modelos legacy (3.5, 4.1) redireccionan a versiones 4.5
