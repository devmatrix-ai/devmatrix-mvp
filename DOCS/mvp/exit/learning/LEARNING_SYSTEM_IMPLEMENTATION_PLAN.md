# Learning System Implementation Plan

**Fecha:** 2025-12-03
**Basado en:** `analisis.md` - Evaluación Principal Engineer
**Estado:** EN PROGRESO

---

## Progress Tracker

| Phase | Descripción | Estado | Fecha |
|-------|-------------|--------|-------|
| 1 | SERVICE Routing + Agent con learning básico | ✅ COMPLETE | 2025-12-03 |
| 2 | PreconditionLearner + Auto-Seed minimal | ⏳ PENDING | - |
| 3 | Fix Reuse solo para SERVICE | ⏳ PENDING | - |
| 4 | PromptEnhancer | ⏳ PENDING | - |
| 5 | Tracker | ⏳ PENDING | - |

### Phase 1 Completed Files:
- ✅ `src/validation/error_types.py` (NEW) - Enums normalizados
- ✅ `src/validation/smoke_repair_orchestrator.py` - _route_violation_to_repair_agent()
- ✅ `src/validation/service_repair_agent.py` - Idempotencia + signatures
- ✅ `src/learning/service_repair_feedback.py` (NEW) - Feedback loop

---

## Executive Summary

El análisis identifica un gap crítico: **el learning detecta y clasifica correctamente, pero no influye en el comportamiento real del sistema**. Los anti-patterns crecen, los scores se actualizan, pero:

1. Los fixes elegidos (`add_validator`) no resuelven errores de precondición (404) ni business logic (422)
2. No hay SERVICE-level repair que modifique servicios/repositorios
3. El learning no retroalimenta a Auto-Seed, Flows, ni Tests
4. Los fix-patterns aprendidos no influyen en la generación inicial

---

## Gap Analysis (del análisis)

| Componente | Estado Actual | Problema |
|------------|---------------|----------|
| Anti-pattern detection | ✅ Funciona | - |
| Score updates | ✅ Funciona | Scores = 0.00 (fixes no mejoran) |
| Fix selection | ⚠️ Parcial | Elige schema-fixes para errores de servicio |
| SERVICE repair | ❌ No existe | Errores 404/422 no reparables |
| Learning → Generation | ❌ Desconectado | Anti-patterns no modifican código inicial |
| Learning → Auto-Seed | ❌ Desconectado | Precondiciones no satisfechas |
| Learning → Tests | ❌ Desconectado | Tests no se adaptan |

---

## Critical Adjustments (Feedback Incorporado)

| Fase | Ajuste | Razón |
|------|--------|-------|
| 1 | `status_code == 404` explícito, no `"404" in str()` | Evita falsos positivos |
| 1 | Normalizar `error_type` a enum definido | Routing predecible |
| 1 | Guard injection idempotente (pattern match previo) | Evita duplicados |
| 2 | Persistencia en Neo4j (no solo dict en memoria) | Reuso entre runs |
| 2 | Merge defensivo: IR manda, learned rellena | No romper seeds |
| 2 | Aplicar precondiciones solo en contexto del endpoint/flow | No sobre-ajustar |
| 3 | Enhanced prompt declarativo, no logs crudos | LLM entiende mejor |
| 3 | Solo para SERVICE/repos/flows, no schema | Foco donde importa |
| 4 | `_compute_signature()` coherente con `store_fix()` | Que matchee |

---

## Implementation Order (Ajustado)

| # | Phase | Esfuerzo | Dependencias | Impacto | Estado |
|---|-------|----------|--------------|---------|--------|
| 1 | SERVICE Routing + Agent con learning básico | 4-6h | ServiceRepairAgent (✅) | ALTO | ✅ DONE |
| 2 | PreconditionLearner + Auto-Seed minimal | 3-4h | Phase 1 ✅ | ALTO | ⏳ |
| 3 | Fix Reuse solo para SERVICE (mini-Phase 4) | 2h | Phase 1 ✅ | MEDIO | ⏳ |
| 4 | PromptEnhancer (cuando hay 2-3 patterns útiles) | 2-3h | Phases 1-3 | MEDIO | ⏳ |
| 5 | Tracker (después de 3 runs comparables) | 2h | All | BAJO | ⏳ |

**Total estimado:** 13-17 horas
**Completado:** ~4-6h (Phase 1)

---

## Implementation Plan

### Phase 1: SERVICE Repair Integration (4-6h)

**Objetivo:** Conectar el `ServiceRepairAgent` (ya implementado) con el Learning System.

#### 1.1 Error Type Enum (Normalización)

**Archivo:** `src/validation/error_types.py` (NUEVO)

```python
from enum import Enum

class ViolationErrorType(str, Enum):
    """Normalized error types for routing."""
    MISSING_PRECONDITION = "MISSING_PRECONDITION"  # 404
    BUSINESS_LOGIC = "BUSINESS_LOGIC"              # 422 status/stock
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"        # 422 schema
    INTERNAL_ERROR = "INTERNAL_ERROR"              # 500
    UNKNOWN = "UNKNOWN"

class ConstraintType(str, Enum):
    """Normalized constraint types for SERVICE repair."""
    STATUS_TRANSITION = "status_transition"
    STOCK_CONSTRAINT = "stock_constraint"
    WORKFLOW_CONSTRAINT = "workflow_constraint"
    PRECONDITION_REQUIRED = "precondition_required"
    CUSTOM = "custom"
```

#### 1.2 Routing de Constraints a SERVICE Repair

**Archivo:** `src/validation/smoke_repair_orchestrator.py`

```python
from src.validation.error_types import ViolationErrorType, ConstraintType

def _route_violation(self, violation: dict) -> str:
    """Route violation to appropriate repair agent."""
    # CRÍTICO: Comparación explícita de status_code
    status_code = violation.get("status_code")
    constraint_type = violation.get("constraint_type", "")

    # Normalizar error_type
    error_type = self._normalize_error_type(violation)

    # 404 → SERVICE repair (precondition)
    if status_code == 404:
        return "SERVICE"

    # Business logic constraints → SERVICE repair
    if constraint_type in [
        ConstraintType.STATUS_TRANSITION,
        ConstraintType.STOCK_CONSTRAINT,
        ConstraintType.WORKFLOW_CONSTRAINT,
    ]:
        return "SERVICE"

    # Precondition errors → SERVICE repair
    if error_type == ViolationErrorType.MISSING_PRECONDITION:
        return "SERVICE"

    # Schema/validation issues → SCHEMA repair
    return "SCHEMA"

def _normalize_error_type(self, violation: dict) -> ViolationErrorType:
    """Normalize error type to enum."""
    raw = violation.get("error_type", "")
    status = violation.get("status_code")

    if status == 404:
        return ViolationErrorType.MISSING_PRECONDITION
    if "precondition" in raw.lower():
        return ViolationErrorType.MISSING_PRECONDITION
    if status == 422:
        if any(kw in raw.lower() for kw in ["status", "stock", "workflow"]):
            return ViolationErrorType.BUSINESS_LOGIC
        return ViolationErrorType.SCHEMA_VALIDATION
    if status == 500:
        return ViolationErrorType.INTERNAL_ERROR
    return ViolationErrorType.UNKNOWN
```

#### 1.3 Guard Injection Idempotente

**Archivo:** `src/validation/service_repair_agent.py`

```python
import re

def _inject_guard(self, service_code: str, guard_code: str, method_name: str) -> str:
    """Inject guard at method start - IDEMPOTENTE."""

    # CRÍTICO: Verificar si guard ya existe (pattern match)
    guard_signature = self._extract_guard_signature(guard_code)
    if guard_signature and guard_signature in service_code:
        # Guard ya presente, no duplicar
        return service_code

    # Buscar método y agregar guard después de def
    pattern = rf'(def {method_name}\([^)]*\):[^\n]*\n)'

    def add_guard(match):
        return match.group(1) + f"        {guard_code}\n"

    return re.sub(pattern, add_guard, service_code)

def _extract_guard_signature(self, guard_code: str) -> str:
    """Extract unique signature from guard for dedup."""
    # "if cart.status != 'OPEN': raise..." → "cart.status != 'OPEN'"
    match = re.search(r'if\s+([^:]+):', guard_code)
    return match.group(1).strip() if match else ""
```

#### 1.4 Feedback Loop para SERVICE Repairs

**Archivo:** `src/learning/service_repair_feedback.py` (NUEVO)

```python
class ServiceRepairFeedback:
    """Tracks SERVICE repair outcomes and updates learning."""

    def record_repair_outcome(
        self,
        constraint_type: ConstraintType,
        guard_spec: GuardSpec,
        smoke_passed: bool
    ):
        if smoke_passed:
            # Incrementar confidence del pattern
            self.store.increment_success(guard_spec.pattern_id)
        else:
            # Decrementar y marcar para revisión
            self.store.increment_failure(guard_spec.pattern_id)
```

---

### Phase 2: Learning → Auto-Seed Connection (3-4h)

**Objetivo:** Los errores de precondición (404) deben retroalimentar al Auto-Seed Generator.

#### 2.1 Precondition Learner con Neo4j Persistence

**Archivo:** `src/learning/precondition_learner.py` (NUEVO)

```python
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class PreconditionPattern:
    """Learned precondition requirement - persisted in Neo4j."""
    pattern_id: str
    entity_type: str           # "Cart", "Order"
    endpoint_pattern: str      # "/carts/{id}/checkout"
    flow_name: Optional[str]   # "checkout_cart"
    required_status: Optional[str] = None   # "OPEN"
    required_relations: List[str] = None    # ["CartItem"]
    required_fields: Dict[str, str] = None  # {"stock": "positive"}
    occurrence_count: int = 1
    confidence: float = 0.5

class PreconditionLearner:
    """Learns precondition requirements from 404 errors - Neo4j backed."""

    def __init__(self, neo4j_driver=None):
        self.driver = neo4j_driver

    def learn_from_404(self, violation: dict, ir: 'ApplicationIR'):
        """Extract and persist precondition pattern."""
        # Solo procesar 404 explícitos
        if violation.get("status_code") != 404:
            return None

        endpoint = violation.get("endpoint", "")
        entity = self._extract_entity(endpoint)

        # Buscar flow en IR
        flow = self._find_flow_for_endpoint(endpoint, ir)

        pattern = PreconditionPattern(
            pattern_id=f"precond_{entity}_{hash(endpoint) % 10000:04d}",
            entity_type=entity,
            endpoint_pattern=self._generalize_endpoint(endpoint),
            flow_name=flow.name if flow else None,
        )

        if flow and hasattr(flow, 'preconditions'):
            pattern.required_status = self._extract_status(flow.preconditions)
            pattern.required_relations = self._extract_relations(flow.preconditions)
            pattern.required_fields = self._extract_fields(flow.preconditions)

        # PERSISTIR en Neo4j (no solo memoria)
        self._upsert_to_neo4j(pattern)
        return pattern

    def _upsert_to_neo4j(self, pattern: PreconditionPattern):
        """Upsert pattern to Neo4j."""
        if not self.driver:
            return

        with self.driver.session() as session:
            session.run("""
                MERGE (p:PreconditionPattern {pattern_id: $pattern_id})
                ON CREATE SET
                    p.entity_type = $entity_type,
                    p.endpoint_pattern = $endpoint_pattern,
                    p.flow_name = $flow_name,
                    p.required_status = $required_status,
                    p.required_relations = $required_relations,
                    p.required_fields = $required_fields,
                    p.occurrence_count = 1,
                    p.confidence = 0.5,
                    p.created_at = datetime()
                ON MATCH SET
                    p.occurrence_count = p.occurrence_count + 1,
                    p.confidence = CASE
                        WHEN p.occurrence_count >= 5 THEN 0.95
                        WHEN p.occurrence_count >= 3 THEN 0.8
                        ELSE p.confidence + 0.1
                    END,
                    p.last_seen = datetime()
            """, **pattern.__dict__)

    def get_for_entity(self, entity_name: str, min_confidence: float = 0.5) -> List[PreconditionPattern]:
        """Get learned preconditions for entity from Neo4j."""
        if not self.driver:
            return []

        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:PreconditionPattern)
                WHERE toLower(p.entity_type) = toLower($entity_name)
                  AND p.confidence >= $min_confidence
                RETURN p
                ORDER BY p.confidence DESC
            """, entity_name=entity_name, min_confidence=min_confidence)

            return [self._to_pattern(r["p"]) for r in result]
```

#### 2.2 Auto-Seed Enhancement (Merge Defensivo)

**Archivo:** `src/services/code_generation_service.py`

```python
def _generate_seed_db_script(self, entities, ir, ...):
    # 1. Extraer precondiciones del IR (FUENTE PRIMARIA)
    ir_preconditions = self._extract_flow_preconditions(ir)

    # 2. Consultar precondiciones aprendidas
    learned_preconditions = {}
    for entity in entities:
        patterns = self.precondition_learner.get_for_entity(entity.name)
        for p in patterns:
            # MERGE DEFENSIVO: Solo agregar si NO existe en IR
            key = f"{entity.name.lower()}.status"
            if p.required_status and key not in ir_preconditions:
                learned_preconditions[key] = p.required_status

            for field, value in (p.required_fields or {}).items():
                key = f"{entity.name.lower()}.{field}"
                if key not in ir_preconditions:
                    learned_preconditions[key] = value

    # 3. Combinar: IR manda, learned rellena gaps
    all_preconditions = {**learned_preconditions, **ir_preconditions}

    # 4. Aplicar solo en contexto del endpoint/flow relevante
    # (no sobre-ajustar con precondiciones de otros flows)
    ...
```

---

### Phase 3: Fix Reuse para SERVICE (mini-Phase 4)

**Objetivo:** Reutilizar guards exitosos sin regenerar con LLM.

#### 3.1 Signature Coherente

**Archivo:** `src/validation/service_repair_agent.py`

```python
def _compute_signature(self, constraint_type: str, entity: str, method: str) -> str:
    """Compute signature coherente con store_fix()."""
    # Normalizar para matching consistente
    return f"{constraint_type}:{entity.lower()}:{method.lower()}"

async def repair_constraint(self, constraint_type, entity_name, method_name, ...):
    # Usar MISMA lógica de signature
    signature = self._compute_signature(constraint_type, entity_name, method_name)

    # Buscar fix conocido
    known_fix = self.fix_store.get_fix_for_error(
        error_signature=signature,
        min_confidence=0.7
    )

    if known_fix:
        # Aplicar directamente (sin LLM)
        result = self._apply_known_guard(known_fix.fix_code, service_code)
        self.metrics["fixes_from_learning"] += 1
        return result

    # Generar nuevo guard
    guard_code = self._generate_and_inject_guard(...)

    # Guardar con MISMA signature
    self.fix_store.store_fix(
        error_signature=signature,
        fix_code=guard_code,
        ...
    )
```

---

### Phase 4: Learning → Generation Prompt (2-3h)

**Objetivo:** Anti-patterns influyen en generación inicial (solo SERVICE/repos/flows).

#### 4.1 Prompt Declarativo (no logs crudos)

**Archivo:** `src/learning/prompt_enhancer.py`

```python
def enhance_service_prompt(self, base_prompt: str, entity_name: str) -> str:
    """Enhance SERVICE prompt - declarativo, no logs."""

    # SOLO buscar patterns de SERVICE, no schema
    patterns = self.pattern_store.get_patterns_for_entity(
        entity_name=entity_name,
        min_occurrences=self.min_occurrences,
        category="service"  # FILTRAR por categoría
    )

    if not patterns:
        return base_prompt

    # Formato DECLARATIVO (no logs crudos)
    warnings = ["\n# BUSINESS LOGIC CONSTRAINTS (learned):"]
    for p in patterns[:3]:  # Max 3 para no saturar
        # Formato claro para LLM
        warnings.append(f"# - {p.entity_pattern}.{p.method_name}: {p.guard_template}")

    return base_prompt + "\n".join(warnings)
```

#### 4.2 Categoría SERVICE en Anti-patterns

**Archivo:** `src/learning/negative_pattern_store.py`

```python
class GenerationAntiPattern:
    # Existente...
    category: str  # "schema", "validation", "service", "repository", "flow"

    # NUEVO: Para SERVICE-level patterns
    guard_template: Optional[str] = None   # "if entity.status != 'OPEN': raise 422"
    method_name: Optional[str] = None      # "add_item", "checkout"
    injection_point: str = "method_start"  # "method_start", "before_db_call"

def get_patterns_for_entity(
    self,
    entity_name: str,
    min_occurrences: int = 2,
    category: str = None  # NUEVO: Filtrar por categoría
) -> List[GenerationAntiPattern]:
    """Get patterns filtered by category."""
    patterns = self._get_all_for_entity(entity_name)

    if category:
        patterns = [p for p in patterns if p.category == category]

    return [p for p in patterns if p.occurrence_count >= min_occurrences]
```

#### 4.3 Solo Enhance SERVICE/Repos/Flows

**Archivo:** `src/services/code_generation_service.py`

```python
async def generate_service_code(self, entity, endpoints, ...):
    base_prompt = self._build_service_prompt(entity, endpoints)

    # SOLO enhance para SERVICE (no schema, no models)
    enhanced_prompt = self.prompt_enhancer.enhance_service_prompt(
        base_prompt,
        entity_name=entity.name
    )

    code = await self.llm_client.generate(enhanced_prompt)

async def generate_schema_code(self, entity, ...):
    # NO enhance - schema no necesita business logic warnings
    prompt = self._build_schema_prompt(entity)
    code = await self.llm_client.generate(prompt)
```

---

### Phase 4: Fix Pattern Reuse (2-3h)

**Objetivo:** Los fix-patterns exitosos deben reutilizarse automáticamente.

#### 4.1 Fix Pattern Matching en Repair

**Archivo:** `src/mge/v2/agents/code_repair_agent.py`

```python
def _repair_smoke_violation(self, violation: dict, ...):
    # PRIMERO: Buscar fix pattern conocido
    known_fix = self.fix_store.get_fix_for_error(
        error_signature=self._compute_signature(violation),
        min_confidence=0.7
    )
    
    if known_fix:
        # Aplicar fix conocido directamente (sin LLM)
        self._apply_known_fix(known_fix)
        self.metrics["fixes_from_learning"] += 1
        return
    
    # FALLBACK: Generar fix con LLM
    ...
```

#### 4.2 Métricas de Reuso

**Archivo:** `src/validation/compliance_validator.py`

```python
@dataclass
class ComplianceReport:
    # Existente...
    
    # NUEVO: Learning metrics
    fixes_from_learning: int = 0
    fixes_from_llm: int = 0
    learning_reuse_rate: float = 0.0
```

---

### Phase 5: Closed-Loop Verification (2h)

**Objetivo:** Verificar que el learning realmente mejora las siguientes generaciones.

#### 5.1 Learning Effectiveness Tracker

**Archivo:** `src/learning/effectiveness_tracker.py` (NUEVO)

```python
class LearningEffectivenessTracker:
    """Tracks if learning actually improves outcomes."""
    
    def compare_runs(self, run_before: str, run_after: str) -> dict:
        """Compare two runs to measure learning impact."""
        return {
            "error_reduction": self._compute_error_reduction(run_before, run_after),
            "repair_iterations_saved": self._compute_iterations_saved(...),
            "patterns_reused": self._count_patterns_reused(...),
            "preconditions_satisfied": self._count_preconditions_satisfied(...),
        }
```

---

## Implementation Order

| # | Phase | Esfuerzo | Dependencias | Impacto |
|---|-------|----------|--------------|---------|
| 1 | SERVICE Repair Integration | 4-6h | ServiceRepairAgent (✅ done) | ALTO |
| 2 | Learning → Auto-Seed | 3-4h | Phase 1 | ALTO |
| 3 | Learning → Generation | 2-3h | - | MEDIO |
| 4 | Fix Pattern Reuse | 2-3h | Phase 1 | MEDIO |
| 5 | Closed-Loop Verification | 2h | All | BAJO |

**Total estimado:** 13-18 horas

---

## Success Criteria

| Métrica | Actual | Target |
|---------|--------|--------|
| Fixes from learning | 0/7 (0%) | >50% |
| Pattern scores > 0 | 0% | >30% |
| 404 errors (precondition) | Alto | -80% |
| 422 errors (business logic) | Alto | -60% |
| Repair iterations | ~3 | <2 |

---

## Files to Modify/Create

### New Files

- `src/validation/error_types.py` - Enums normalizados (ViolationErrorType, ConstraintType)
- `src/learning/service_repair_feedback.py` - Feedback loop para SERVICE repairs
- `src/learning/precondition_learner.py` - Aprende precondiciones de 404s (Neo4j backed)
- `src/learning/effectiveness_tracker.py` - Mide mejora real entre runs

### Modified Files

- `src/validation/smoke_repair_orchestrator.py` - Route to SERVICE repair con enums
- `src/validation/service_repair_agent.py` - Guard idempotente + signature coherente
- `src/services/code_generation_service.py` - Merge defensivo precondiciones + PromptEnhancer
- `src/learning/prompt_enhancer.py` - Formato declarativo, filtro por categoría
- `src/learning/negative_pattern_store.py` - Categoría SERVICE, guard_template
- `src/validation/compliance_validator.py` - Learning metrics

---

## Diagrama de Flujo Objetivo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LEARNING-DRIVEN GENERATION LOOP                           │
└─────────────────────────────────────────────────────────────────────────────┘

    Smoke Test Failure
           │
           ▼
    ┌──────────────────┐
    │ Classify Error   │
    │ - 404 → Precond  │
    │ - 422 → BizLogic │
    │ - 500 → Schema   │
    └────────┬─────────┘
             │
    ┌────────┴────────┬────────────────┐
    │                 │                │
    ▼                 ▼                ▼
┌─────────┐    ┌───────────┐    ┌───────────┐
│Precond  │    │ SERVICE   │    │ SCHEMA    │
│Learner  │    │ Repair    │    │ Repair    │
└────┬────┘    └─────┬─────┘    └─────┬─────┘
     │               │                │
     ▼               ▼                ▼
┌─────────┐    ┌───────────┐    ┌───────────┐
│Auto-Seed│    │ Guard     │    │ Validator │
│Enhanced │    │ Injection │    │ Fix       │
└────┬────┘    └─────┬─────┘    └─────┬─────┘
     │               │                │
     └───────────────┴────────────────┘
                     │
                     ▼
           ┌─────────────────┐
           │ Store Pattern   │
           │ (if successful) │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Next Generation │
           │ Uses Patterns   │
           └─────────────────┘
```

---

## Detailed Implementation Steps

### Step 1.1: Modify SmokeRepairOrchestrator

```python
# src/validation/smoke_repair_orchestrator.py

from src.validation.service_repair_agent import ServiceRepairAgent, get_service_repair_agent

class SmokeRepairOrchestrator:
    def __init__(self, ...):
        # Existente...
        self.service_repair_agent = get_service_repair_agent()

    def _route_violation(self, violation: dict) -> str:
        """Route violation to appropriate repair agent."""
        constraint_type = violation.get("constraint_type", "")
        error_type = violation.get("error_type", "")

        # Business logic constraints → SERVICE repair
        if constraint_type in [
            "status_transition",
            "stock_constraint",
            "workflow_constraint",
            "precondition_required"
        ]:
            return "SERVICE"

        # Precondition errors (404) → SERVICE repair (needs entity setup)
        if error_type == "MISSING_PRECONDITION" or "404" in str(violation.get("status_code", "")):
            return "SERVICE"

        # Schema/validation issues → SCHEMA repair
        return "SCHEMA"

    async def repair_violation(self, violation: dict, ...):
        route = self._route_violation(violation)

        if route == "SERVICE":
            return await self.service_repair_agent.repair_constraint(
                constraint_type=violation.get("constraint_type"),
                entity_name=violation.get("entity"),
                method_name=violation.get("method"),
                service_code=self._get_service_code(violation),
                ir=self.application_ir
            )
        else:
            return await self.code_repair_agent.repair(violation, ...)
```

### Step 1.2: Add Learning to ServiceRepairAgent

```python
# src/validation/service_repair_agent.py

from src.services.error_pattern_store import get_error_pattern_store

class ServiceRepairAgent:
    def __init__(self, ...):
        self.fix_store = get_error_pattern_store()

    async def repair_constraint(self, ...):
        # PRIMERO: Buscar fix conocido
        known_fix = self.fix_store.get_fix_for_error(
            error_signature=f"{constraint_type}:{entity_name}:{method_name}",
            min_confidence=0.7
        )

        if known_fix:
            # Aplicar fix conocido
            result = self._apply_known_guard(known_fix.fix_code, service_code)
            self._record_reuse(known_fix.fix_id)
            return result

        # Generar nuevo guard
        guard_spec = self._generate_guard(constraint_type, entity_name, method_name, ir)
        guard_code = self._render_guard(guard_spec)

        # Inyectar en servicio
        repaired_code = self._inject_guard(service_code, guard_code, method_name)

        return repaired_code

    def learn_from_outcome(self, constraint_type: str, guard_code: str, success: bool):
        """Store successful guard for future reuse."""
        if success:
            self.fix_store.store_fix(
                error_type=constraint_type,
                error_signature=f"{constraint_type}:*:*",  # Generalizado
                fix_code=guard_code,
                fix_strategy="guard_injection"
            )
```

### Step 2.1: PreconditionLearner Implementation

```python
# src/learning/precondition_learner.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import re

@dataclass
class PreconditionPattern:
    """Learned precondition requirement from 404 errors."""
    pattern_id: str
    entity_type: str
    endpoint_pattern: str
    required_status: Optional[str] = None
    required_relations: List[str] = field(default_factory=list)
    required_fields: Dict[str, str] = field(default_factory=dict)
    occurrence_count: int = 1
    confidence: float = 0.5

class PreconditionLearner:
    """Learns precondition requirements from 404/422 errors."""

    def __init__(self, neo4j_driver=None):
        self.driver = neo4j_driver
        self._patterns: Dict[str, PreconditionPattern] = {}

    def learn_from_error(self, violation: dict, ir: 'ApplicationIR'):
        """Extract and store precondition pattern from error."""
        endpoint = violation.get("endpoint", "")
        error_type = violation.get("error_type", "")

        if error_type not in ["MISSING_PRECONDITION", "404"]:
            return None

        entity = self._extract_entity_from_endpoint(endpoint)
        if not entity:
            return None

        # Buscar flow en IR para extraer precondiciones
        flow = self._find_flow_for_endpoint(endpoint, ir)

        pattern = PreconditionPattern(
            pattern_id=f"precond_{entity}_{hash(endpoint) % 10000:04d}",
            entity_type=entity,
            endpoint_pattern=self._generalize_endpoint(endpoint),
        )

        if flow and hasattr(flow, 'preconditions'):
            pattern.required_status = self._extract_status(flow.preconditions)
            pattern.required_relations = self._extract_relations(flow.preconditions)
            pattern.required_fields = self._extract_fields(flow.preconditions)

        # Upsert pattern
        existing = self._patterns.get(pattern.pattern_id)
        if existing:
            existing.occurrence_count += 1
            existing.confidence = min(0.95, existing.confidence + 0.1)
        else:
            self._patterns[pattern.pattern_id] = pattern

        return pattern

    def get_for_entity(self, entity_name: str) -> List[PreconditionPattern]:
        """Get learned preconditions for an entity."""
        return [
            p for p in self._patterns.values()
            if p.entity_type.lower() == entity_name.lower()
            and p.confidence >= 0.5
        ]

    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # /products/{id} → Product
        # /carts/{id}/items → Cart
        match = re.match(r'^/([a-z]+)', endpoint)
        if match:
            entity = match.group(1)
            if entity.endswith('s'):
                entity = entity[:-1]
            return entity.capitalize()
        return None

    def _generalize_endpoint(self, endpoint: str) -> str:
        """Generalize endpoint to pattern."""
        # /products/123 → /products/{id}
        pattern = re.sub(r'/[0-9a-f-]{36}', '/{id}', endpoint)
        pattern = re.sub(r'/\d+', '/{id}', pattern)
        return pattern

    def _find_flow_for_endpoint(self, endpoint: str, ir: 'ApplicationIR'):
        """Find BehaviorModel flow for endpoint."""
        if not ir or not hasattr(ir, 'behavior_model'):
            return None

        behavior = ir.behavior_model
        if not hasattr(behavior, 'flows'):
            return None

        for flow in behavior.flows:
            if hasattr(flow, 'endpoint') and flow.endpoint in endpoint:
                return flow

        return None

    def _extract_status(self, preconditions: list) -> Optional[str]:
        """Extract required status from preconditions."""
        for precond in preconditions:
            if 'status' in str(precond).lower():
                # "{cart}.status == 'OPEN'" → "OPEN"
                match = re.search(r"status\s*==\s*['\"](\w+)['\"]", str(precond))
                if match:
                    return match.group(1)
        return None

    def _extract_relations(self, preconditions: list) -> List[str]:
        """Extract required relations from preconditions."""
        relations = []
        for precond in preconditions:
            # "{cart}.items.count >= 1" → "items"
            match = re.search(r'\{(\w+)\}\.(\w+)\.count', str(precond))
            if match:
                relations.append(match.group(2))
        return relations

    def _extract_fields(self, preconditions: list) -> Dict[str, str]:
        """Extract required field values from preconditions."""
        fields = {}
        for precond in preconditions:
            # "{product}.stock >= {quantity}" → {"stock": "positive"}
            if 'stock' in str(precond).lower():
                fields['stock'] = 'positive_required'
        return fields


# Singleton
_precondition_learner: Optional[PreconditionLearner] = None

def get_precondition_learner() -> PreconditionLearner:
    global _precondition_learner
    if _precondition_learner is None:
        _precondition_learner = PreconditionLearner()
    return _precondition_learner
```

### Step 2.2: Integrate with Auto-Seed

```python
# src/services/code_generation_service.py

from src.learning.precondition_learner import get_precondition_learner

class CodeGenerationService:
    def __init__(self, ...):
        # Existente...
        self.precondition_learner = get_precondition_learner()

    def _generate_seed_db_script(self, entities, ir, ...):
        # Existente: extraer precondiciones del IR
        ir_preconditions = self._extract_flow_preconditions(ir)

        # NUEVO: Agregar precondiciones aprendidas
        for entity in entities:
            learned = self.precondition_learner.get_for_entity(entity.name)
            for pattern in learned:
                if pattern.required_status:
                    ir_preconditions[f"{entity.name.lower()}.status"] = pattern.required_status
                if pattern.required_fields:
                    for field, value in pattern.required_fields.items():
                        ir_preconditions[f"{entity.name.lower()}.{field}"] = value

        # Generar seeds con precondiciones combinadas
        ...
```

---

## Verification Checklist

### Phase 1 Verification ✅ COMPLETE (2025-12-03)

- [x] SERVICE repair agent receives business logic violations
- [x] Guards are injected into service methods (idempotent)
- [x] Successful guards are stored for reuse (`_compute_signature()`)
- [x] Metrics tracking implemented (`get_repair_metrics()`)
- [x] Normalized error types (`ViolationErrorType`, `ConstraintType` enums)
- [x] Routing uses explicit `status_code == 404` (no string matching)
- [x] Feedback loop for SERVICE repairs (`service_repair_feedback.py`)

### Phase 2 Verification
- [ ] 404 errors create PreconditionPattern
- [ ] Auto-Seed uses learned preconditions
- [ ] Subsequent runs have fewer 404 errors

### Phase 3 Verification
- [ ] PromptEnhancer is called during generation
- [ ] Anti-patterns appear in LLM prompts
- [ ] Generated code avoids known issues

### Phase 4 Verification
- [ ] Fix patterns are matched before LLM call
- [ ] `learning_reuse_rate > 0.5` after 3+ runs

### Phase 5 Verification
- [ ] `compare_runs()` shows improvement
- [ ] Error reduction > 50% after learning

---

**Documento creado:** 2025-12-03
**Autor:** DevMatrix AI Pipeline Team

