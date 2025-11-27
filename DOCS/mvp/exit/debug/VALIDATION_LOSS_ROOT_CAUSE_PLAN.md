# Plan: Resolver Pérdida de Validación (-35.6%)

**Document Version**: 1.0
**Date**: November 25, 2025
**Status**: 🔴 PENDING
**Priority**: 🔴 CRITICAL - Pipeline compliance drops from 92.9% → 64.4%

---

## 📋 Executive Summary

### Problem Statement
**Current State**: Pipeline detecta ~148 constraints pero compliance cae de 92.9% a 64.4%
**Root Cause**: El problema NO es detección, es **NORMALIZACIÓN SEMÁNTICA**
**Impact**: -35.6% validation loss forzando repair loops innecesarios

### Root Causes Identified

| # | Causa | Impacto | Descripción |
|---|-------|---------|-------------|
| 1 | AST Parser Literals | ~40% | Extrae literales (`"email"`) vs claves semánticas (`email_field`) |
| 2 | Extractores Desconectados | ~30% | OpenAPI + AST tienen solo 23.6% overlap |
| 3 | Semantic Matching Incompleto | ~20% | No reconoce equivalencias (`price` ≡ `unit_price`) |
| 4 | Ground Truth Mismatch | ~10% | Formato spec vs formato código difieren |

---

## 🎯 Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEMANTIC NORMALIZATION LAYER                  │
├─────────────────────────────────────────────────────────────────┤
│  OpenAPI Extractor  ──┐                                         │
│                       ├──► Semantic Normalizer ──► Unified IR   │
│  AST Parser ─────────┘         │                                │
│                                │                                │
│                    ┌───────────┴───────────┐                    │
│                    │  Equivalence Engine   │                    │
│                    │  - Synonym mapping    │                    │
│                    │  - Pattern matching   │                    │
│                    │  - Context inference  │                    │
│                    └───────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementation Plan

### Fase 1: Semantic Normalizer Layer (Priority: CRITICAL)
**Impacto esperado**: +25-30% compliance recovery
**Tiempo estimado**: 2-3 horas
**File**: `src/services/semantic_normalizer.py` (NEW)

#### Task 1.1: Crear SemanticNormalizer Base
```python
class SemanticNormalizer:
    """
    Normaliza constraints de diferentes fuentes a formato semántico unificado.
    """

    def normalize_field_name(self, raw_name: str, context: dict) -> str:
        """
        Normaliza nombres de campos a forma canónica.

        Examples:
            "email" → "email"
            "user_email" → "email"
            "emailAddress" → "email"
            "e-mail" → "email"
        """
        pass

    def normalize_constraint_type(self, raw_type: str) -> str:
        """
        Normaliza tipos de constraint.

        Examples:
            "EmailStr" → "FORMAT_EMAIL"
            "email validator" → "FORMAT_EMAIL"
            "must be valid email" → "FORMAT_EMAIL"
        """
        pass

    def normalize_validation_rule(self, rule: dict) -> NormalizedRule:
        """
        Convierte cualquier formato de regla a NormalizedRule.
        """
        pass
```

#### Task 1.2: Implementar Equivalence Mappings
```python
FIELD_EQUIVALENCES = {
    "email": ["email", "user_email", "emailAddress", "e-mail", "mail"],
    "price": ["price", "unit_price", "unitPrice", "amount", "cost"],
    "quantity": ["quantity", "qty", "count", "amount"],
    "name": ["name", "full_name", "fullName", "username", "title"],
    "date": ["date", "created_at", "createdAt", "timestamp", "datetime"],
    "status": ["status", "state", "order_status", "orderStatus"],
    "stock": ["stock", "inventory", "quantity_available", "available"],
}

CONSTRAINT_EQUIVALENCES = {
    "FORMAT_EMAIL": ["EmailStr", "email", "email_validator", "valid email"],
    "RANGE_MIN": ["ge", "gte", "min", "minimum", ">=", "greater than"],
    "RANGE_MAX": ["le", "lte", "max", "maximum", "<=", "less than"],
    "REQUIRED": ["required", "not null", "mandatory", "must have"],
    "UNIQUE": ["unique", "distinct", "no duplicates"],
}
```

#### Task 1.3: Integrar con Pipeline
- Modificar `_phase_4_validation_extraction()` para usar SemanticNormalizer
- Normalizar antes de comparar con ground truth
- Agregar métricas de normalización

---

### Fase 2: Merger de Extractores (Priority: HIGH)
**Impacto esperado**: +15-20% compliance recovery
**Tiempo estimado**: 1-2 horas
**File**: `src/services/unified_constraint_extractor.py` (NEW)

#### Task 2.1: Crear UnifiedConstraintExtractor
```python
class UnifiedConstraintExtractor:
    """
    Combina OpenAPI y AST extractors con deduplicación inteligente.
    """

    def __init__(self):
        self.openapi_extractor = OpenAPIExtractor()
        self.ast_extractor = ASTConstraintExtractor()
        self.normalizer = SemanticNormalizer()

    async def extract_all(self, code_files: dict) -> list[NormalizedRule]:
        """
        Extrae de ambas fuentes, normaliza y deduplica.
        """
        openapi_rules = await self.openapi_extractor.extract(code_files)
        ast_rules = await self.ast_extractor.extract(code_files)

        # Normalizar ambos conjuntos
        normalized_openapi = [self.normalizer.normalize(r) for r in openapi_rules]
        normalized_ast = [self.normalizer.normalize(r) for r in ast_rules]

        # Merge con deduplicación semántica
        return self._semantic_merge(normalized_openapi, normalized_ast)

    def _semantic_merge(self, set_a: list, set_b: list) -> list:
        """
        Merge inteligente que reconoce duplicados semánticos.
        """
        pass
```

#### Task 2.2: Mejorar Overlap Detection
- Implementar `_is_semantic_duplicate(rule_a, rule_b)`
- Usar fuzzy matching para nombres similares
- Considerar contexto (entity, field type) para desambiguar

---

### Fase 3: Expand Semantic Matching (Priority: MEDIUM)
**Impacto esperado**: +10-15% compliance recovery
**Tiempo estimado**: 1 hora
**File**: `src/services/semantic_matcher.py` (MODIFY)

#### Task 3.1: Mejorar Fuzzy Matching
```python
def semantic_match(spec_rule: str, code_rule: str) -> float:
    """
    Retorna score de similitud semántica (0.0 - 1.0).

    Uses:
    - Levenshtein distance para typos
    - Synonym lookup para equivalencias
    - Pattern matching para variaciones
    """
    # Direct match
    if spec_rule == code_rule:
        return 1.0

    # Normalized match
    norm_spec = normalize(spec_rule)
    norm_code = normalize(code_rule)
    if norm_spec == norm_code:
        return 0.95

    # Synonym match
    if are_synonyms(norm_spec, norm_code):
        return 0.9

    # Fuzzy match
    ratio = fuzz.ratio(norm_spec, norm_code)
    if ratio > 80:
        return ratio / 100 * 0.85

    return 0.0
```

#### Task 3.2: Agregar Context-Aware Matching
- Considerar entity context al matchear
- Usar field types como hint adicional
- Implementar confidence scoring

---

### Fase 4: Ground Truth Normalization (Priority: LOW)
**Impacto esperado**: +5-10% compliance recovery
**Tiempo estimado**: 30 min
**File**: `tests/e2e/test_specs/` (MODIFY)

#### Task 4.1: Normalizar Spec Format
- Crear `normalize_spec_constraints()` para uniformizar formato
- Mapear spec terminology a código terminology
- Documentar convenciones de naming

#### Task 4.2: Update Ground Truth Files
- Actualizar `ecommerce-api-spec-human.md` con formato normalizado
- Agregar sección de constraint mappings explícitos
- Validar consistencia con código esperado

---

## 📊 Success Metrics

| Métrica | Current | Target | Improvement |
|---------|---------|--------|-------------|
| Compliance Pre-Repair | 64.4% | 90%+ | +25.6% |
| Validation Loss | -35.6% | <5% | +30.6% |
| Constraint Match Rate | 23.6% | 80%+ | +56.4% |
| Repair Iterations Needed | 2-3 | 0-1 | -66% |

---

## 🔄 Execution Order

```
Fase 1 (CRITICAL) ──► Fase 2 (HIGH) ──► Fase 3 (MEDIUM) ──► Fase 4 (LOW)
     │                    │                  │                  │
     │                    │                  │                  │
     ▼                    ▼                  ▼                  ▼
  +25-30%             +15-20%            +10-15%             +5-10%

Total Expected: +55-75% compliance recovery
Target: 64.4% + 55% = ~90%+ compliance
```

---

## 📋 Checklist

### Fase 1: SemanticMatcher Híbrido ✅ COMPLETADA
- [x] Task 1.1: Crear SemanticMatcher class (`src/services/semantic_matcher.py`)
  - Híbrido: Embeddings (sentence-transformers) + LLM (Claude Haiku)
  - ~380 líneas de código, con fallback graceful
  - Thresholds: HIGH=0.8 (embedding match), LOW=0.5 (go to LLM)
- [x] Task 1.2: Integrar con ComplianceValidator (`src/validation/compliance_validator.py`)
  - Método `_semantic_match_validations()` agregado
  - Auto-activación via env var USE_SEMANTIC_MATCHING
  - Fallback a semantic_equivalences manual si no disponible
- [x] Task 1.3: Integrar en `_calculate_validation_compliance()`
  - SemanticMatcher se usa PRIMERO si disponible
  - ~300 líneas de código manual quedan como fallback
- [x] Task 1.4: Integrar con ApplicationIR (ValidationModelIR)
  - ComplianceValidator acepta `application_ir` opcional
  - Método `match_from_validation_model()` usa IR para matching preciso
  - Prioridad: IR-based > Standard batch matching > Manual equivalences
- [ ] Tests: Crear unit tests (pendiente)

### Fase 2: Merger de Extractores (PENDIENTE)
- [ ] Task 2.1: Crear UnifiedConstraintExtractor
- [ ] Task 2.2: Mejorar overlap detection
- [ ] Tests: Verificar merge correcto

### Fase 3: Semantic Matching Avanzado (PENDIENTE)
- [ ] Task 3.1: Integrar con ApplicationIR para contexto
- [ ] Task 3.2: Agregar context-aware matching
- [ ] Tests: Verificar match rates

### Fase 4: Ground Truth (PENDIENTE)
- [ ] Task 4.1: Normalizar spec format
- [ ] Task 4.2: Update ground truth files
- [ ] Tests: Verificar consistencia

---

## 🎯 Expected Outcome

**After Fase 1 Implementation (ACTUAL)**:
- Compliance Pre-Repair: **64.4% → TBD** (pendiente medición)
- Método: **Manual dict (~100 líneas) → ML híbrido**
- Fallback: **Graceful** si sentence-transformers no disponible

**Archivos Modificados**:
- `src/services/semantic_matcher.py` (NUEVO - 380 líneas)
- `src/validation/compliance_validator.py` (MODIFICADO - integración)

**Key Insight**: El problema nunca fue detección (~148 constraints detectados).
El problema es que **no estamos hablando el mismo idioma** entre spec y código.
La solución es un **traductor semántico** que unifique vocabularios.

---

**Timeline**: Fase 1 completada (~2h)
**Blocked By**: None
**Next Action**: Crear unit tests y medir impacto en compliance

