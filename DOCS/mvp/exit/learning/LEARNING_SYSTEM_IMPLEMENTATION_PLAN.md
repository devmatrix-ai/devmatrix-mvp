# Learning System Implementation Plan

**Fecha:** 2025-12-03  
**Basado en:** `analisis.md` - Evaluación Principal Engineer  
**Estado:** PLAN DETALLADO

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

## Implementation Plan

### Phase 1: SERVICE Repair Integration (4-6h)

**Objetivo:** Conectar el `ServiceRepairAgent` (ya implementado) con el Learning System.

#### 1.1 Routing de Constraints a SERVICE Repair

**Archivo:** `src/validation/smoke_repair_orchestrator.py`

```python
# Modificar _route_violation() para usar ServiceRepairAgent
def _route_violation(self, violation: dict) -> str:
    constraint_type = violation.get("constraint_type", "")
    
    # Business logic → SERVICE repair
    if constraint_type in ["status_transition", "stock_constraint", "workflow_constraint"]:
        return "SERVICE"
    
    # Schema issues → SCHEMA repair (actual)
    return "SCHEMA"
```

**Archivo:** `src/validation/service_repair_agent.py`

```python
# Agregar método para aprender de reparaciones exitosas
def learn_from_repair(self, constraint_type: str, guard_code: str, success: bool):
    """Store successful guard patterns for reuse."""
    if success:
        self.store.store_fix_pattern(
            error_type=constraint_type,
            fix_code=guard_code,
            confidence=0.8
        )
```

#### 1.2 Feedback Loop para SERVICE Repairs

**Archivo:** `src/learning/service_repair_feedback.py` (NUEVO)

```python
class ServiceRepairFeedback:
    """Tracks SERVICE repair outcomes and updates learning."""
    
    def record_repair_outcome(
        self,
        constraint_type: str,
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

#### 2.1 Precondition Error Classifier

**Archivo:** `src/learning/precondition_learner.py` (NUEVO)

```python
@dataclass
class PreconditionPattern:
    """Learned precondition requirement."""
    entity_type: str           # "Cart", "Order"
    required_status: str       # "OPEN", "PENDING"
    required_relations: list   # ["CartItem", "Product"]
    occurrence_count: int
    confidence: float

class PreconditionLearner:
    """Learns precondition requirements from 404 errors."""
    
    def learn_from_404(self, violation: dict, ir: ApplicationIR):
        """Extract precondition pattern from 404 error."""
        endpoint = violation.get("endpoint", "")
        entity = self._extract_entity(endpoint)
        
        # Analizar IR para encontrar precondiciones
        flow = self._find_flow_for_endpoint(endpoint, ir)
        if flow and flow.preconditions:
            pattern = self._extract_pattern(entity, flow.preconditions)
            self.store.store_precondition(pattern)
```

#### 2.2 Auto-Seed Enhancement

**Archivo:** `src/services/code_generation_service.py`

```python
# En _generate_seed_db_script():
def _generate_seed_db_script(self, ...):
    # NUEVO: Consultar precondiciones aprendidas
    learned_preconditions = self.precondition_learner.get_for_entity(entity_name)
    
    # Combinar con precondiciones del IR
    all_preconditions = self._merge_preconditions(
        ir_preconditions,
        learned_preconditions
    )
    
    # Generar seeds que satisfagan todas las precondiciones
    ...
```

---

### Phase 3: Learning → Generation Prompt (2-3h)

**Objetivo:** Los anti-patterns deben modificar la generación inicial, no solo el repair.

#### 3.1 Integrar PromptEnhancer en CodeGenerationService

**Archivo:** `src/services/code_generation_service.py`

```python
from src.learning.prompt_enhancer import get_prompt_enhancer

class CodeGenerationService:
    def __init__(self, ...):
        self.prompt_enhancer = get_prompt_enhancer()
    
    async def generate_service_code(self, entity, endpoints, ...):
        # ANTES: prompt = self._build_service_prompt(entity, endpoints)
        
        # DESPUÉS: Enhance con anti-patterns aprendidos
        base_prompt = self._build_service_prompt(entity, endpoints)
        enhanced_prompt = self.prompt_enhancer.enhance_service_prompt(
            base_prompt,
            entity_name=entity.name
        )
        
        # Generar con awareness de errores previos
        code = await self.llm_client.generate(enhanced_prompt)
```

#### 3.2 Agregar Anti-patterns de SERVICE Level

**Archivo:** `src/learning/negative_pattern_store.py`

```python
# Agregar categoría SERVICE a GenerationAntiPattern
class GenerationAntiPattern:
    # Existente...
    category: str  # "schema", "validation", "service", "repository"
    
    # NUEVO: Para SERVICE-level patterns
    guard_template: Optional[str] = None  # Template de guard a inyectar
    injection_point: Optional[str] = None  # "method_start", "before_db_call"
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
- `src/learning/service_repair_feedback.py`
- `src/learning/precondition_learner.py`
- `src/learning/effectiveness_tracker.py`

### Modified Files
- `src/validation/smoke_repair_orchestrator.py` - Route to SERVICE repair
- `src/validation/service_repair_agent.py` - Add learning integration
- `src/services/code_generation_service.py` - Integrate PromptEnhancer + Preconditions
- `src/mge/v2/agents/code_repair_agent.py` - Fix pattern reuse
- `src/learning/negative_pattern_store.py` - SERVICE category
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

### Phase 1 Verification
- [ ] SERVICE repair agent receives business logic violations
- [ ] Guards are injected into service methods
- [ ] Successful guards are stored for reuse
- [ ] Metrics show `fixes_from_learning > 0`

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

