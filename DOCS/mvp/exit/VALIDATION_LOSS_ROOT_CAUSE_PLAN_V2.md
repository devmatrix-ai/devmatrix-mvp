# Plan v2.0: Resolver Pérdida de Validación (-35.6%) + ApplicationIR

**Document Version**: 2.0
**Date**: November 25, 2025
**Status**: 🟡 IN PROGRESS (Fase 1 completada)
**Priority**: 🔴 CRITICAL
**Scope**: Validation + IR Consistency + Semantic Integrity

---

## 📌 ¿Por qué ApplicationIR es Crítico?

El plan anterior arreglaba:
- Normalización semántica
- Overlaps entre extractores
- Matching fuzzy
- Ground truth

Pero **NO atacaba el punto central**: El **ApplicationIR debe ser la fuente de verdad semántica**.

### Sin ApplicationIR:
- No existe semántica canónica
- No hay campo estandarizado para constraints
- No hay equivalencias unificadas entre extractores
- No hay round-trip preciso: `spec → IR → code → IR`
- No hay reproducibilidad multi-dominio

### El Problema Actual:
```
Spec → OpenAPI    → AST    → Code
       ↕             ↕
    (diferencias semánticas)
```

No compara contra **ApplicationIR**, que es la única representación semántica limpia.

---

## 🏗️ Nueva Arquitectura con ApplicationIR

```
                 SPEC
                  │
                  ▼
             ApplicationIR  ◄──────────────┐
                  │                        │
        ┌─────────┼─────────┐              │
        ▼         ▼         ▼              │
   OpenAPI     AST-Pyd.   AST-SQLA         │
  Extractor     Extract.    Extract.       │
        └─────────┼─────────┘              │
                  ▼                        │
        Semantic Normalizer (A + C)        │
                  ▼                        │
         Unified Constraint IR  ───────────┘
                  │
                  ▼
         ComplianceValidator
                  │
                  ▼
              CodeRepair
```

---

## 🛠️ Implementation Plan

### Fase 1: SemanticMatcher Híbrido ✅ COMPLETADA

**Impacto**: +25-30% compliance recovery

**Implementado**:
- [x] `src/services/semantic_matcher.py` (380 líneas)
  - Híbrido: Embeddings (sentence-transformers) + LLM (Claude Haiku)
  - Thresholds: HIGH=0.8, LOW=0.5
  - Método `match_from_validation_model()` para IR-based matching
- [x] Integración con `ComplianceValidator`
  - Parámetro `application_ir` opcional
  - Auto-selección de método más preciso disponible
- [x] Unit tests: 16/16 passing

**Arquitectura del Matcher**:
```
Spec Constraints ──► Embed (MiniLM) ──┐
                                      ├──► Cosine Similarity
Code Constraints ──► Embed (MiniLM) ──┘
                                           │
                               sim > 0.8?  ┼  sim < 0.5?
                                   │       │       │
                                   ▼       │       ▼
                                MATCH      │   NO MATCH
                                           │
                                           ▼
                                    LLM Validation
                                    (Claude Haiku)
```

### Fase 2: Unified Constraint Extractor → IR Loader (PENDIENTE)

**Impacto**: +15-20% compliance

**Tareas**:
- [ ] OpenAPI extraction → mapped to IR
- [ ] AST Pydantic → mapped to IR
- [ ] AST SQLAlchemy → mapped to IR
- [ ] Business logic patterns → mapped to IR

**Key**: Merge por ID semántico:
```python
ConstraintKey = f"{entity}.{field}.{constraint_type}"
```

Esto hace que:
- "price" y "unit_price" → mismo IR field
- "createdAt", "creation_date" → "creation_date"
- UNIQUE/PRIMARY KEY → se alineen

### Fase 3: Semantic Matcher con IR Awareness (PENDIENTE)

**Impacto**: +10-15%

**Ya implementado parcialmente**:
- [x] `match_from_validation_model()` compara ValidationModelIR
- [ ] Integrar con todos los extractores

**Matching basado en IR**:
```
Spec dice: unit_price: snapshot at creation
AST SQLAlchemy: exclude=True, onupdate=None
Pydantic: Field(..., exclude=True)

Semantic matcher:
  snapshot → IMMUTABLE
  exclude=True → IMMUTABLE
  → Match perfecto
```

### Fase 4: Ground Truth sobre ApplicationIR (PENDIENTE)

**Impacto**: +5-10%

**Flujo**:
1. Parsear spec
2. Transformar a ApplicationIR
3. Evaluar ground truth contra IR (no contra texto)

---

## 📊 KPIs Target

| Métrica | Estado Actual | Target |
|---------|---------------|--------|
| Pre-Repair Compliance | 64.4% | 92-96% |
| Validations Compliance | 71.2% | 95%+ |
| Validation Loss | -35.6% | <5% |
| Constraint Match Rate | 23.6% | 85-98% |
| Repair Iterations | 3 | 0-1 |
| IR Reproducibility | 100% | 100% |

---

## 📁 Archivos Modificados/Creados

| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `src/services/semantic_matcher.py` | ✅ CREADO | SemanticMatcher híbrido |
| `src/validation/compliance_validator.py` | ✅ MODIFICADO | Integración IR |
| `tests/unit/test_semantic_matcher.py` | ✅ CREADO | 16 unit tests |

---

## 🎯 Próximos Pasos

1. **Medir impacto actual**: Ejecutar E2E con SemanticMatcher habilitado
2. **Fase 2**: Crear UnifiedConstraintExtractor que mapee a IR
3. **Fase 3**: Completar IR awareness en todos los extractores
4. **Fase 4**: Normalizar ground truth sobre IR

---

## 🏆 Resultado Esperado

Al completar todas las fases con ApplicationIR:
- ✔ Pipeline heurístico → **determinístico**
- ✔ >80% falsos negativos eliminados
- ✔ Dominio ecommerce **95%+ correcto**
- ✔ Motor escala a **multi-dominio**
- ✔ **VC-ready** y enterprise-grade
