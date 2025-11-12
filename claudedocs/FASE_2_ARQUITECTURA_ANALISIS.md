# Fase 2: Atomización Proactiva - Análisis Arquitectónico Completo

**Fecha**: 2025-11-12
**Objetivo**: Invertir flujo de atomización - Specs primero, código después
**Duración Estimada**: 2-3 horas
**Deliverable**: Plan detallado + código base + tests

---

## 1. ANÁLISIS DE ARQUITECTURA ACTUAL

### 1.1 Flujo Actual de Atomización (Reactivo)

**Modelo Actual**:
```
Task → Código → Parser → Decomposer → AtomicUnit (validación posterior)
                                                ↓
                                         Validator (retroactivo)
```

**Componentes Clave Encontrados**:

#### `/src/models/atomic_unit.py`
- **AtomicUnit**: Modelo DB completo (ORM)
- Contiene: código generado, validación, dependencias, retry history
- **Validación POSTERIOR**: `atomicity_score`, `is_atomic`, `violations`
- Target: ~10 LOC, complexity <3.0
- **Problema**: Validación ocurre DESPUÉS de generar código

#### `/src/atomization/decomposer.py`
- **RecursiveDecomposer**: Divide código existente en átomos
- Estrategias: by_function, by_class, by_block
- **Límite**: Opera sobre código YA escrito
- **Target**: 10 LOC por átomo

#### `/src/atomization/validator.py`
- **AtomicityValidator**: 10 criterios de atomicidad
  1. LOC ≤ 15
  2. Complexity < 3.0
  3. Single responsibility
  4. Clear boundaries
  5. Independence
  6. Context completeness ≥ 95%
  7. Testable
  8. Deterministic
  9. No side effects (preferred)
  10. Clear I/O
- **Score**: 0.0-1.0, threshold ≥ 0.8
- **Problema**: Rechaza código inválido DESPUÉS de generarlo

#### `/src/mge/v2/validation/atomic_validator.py`
- Wrapper para MGE V2
- Integra validador legacy con pipeline V2
- **Fallback**: Basic validation (syntax check)

### 1.2 Flujo de MasterPlan a Tareas

**Pipeline Actual**:
```
DiscoveryDocument → MasterPlan → Tasks → Subtasks
                                            ↓
                                   (NO hay atomización aquí)
```

**Estructura Encontrada**:

#### `/src/services/masterplan_generator.py`
- Genera MasterPlan completo (120 tasks)
- **Subtasks**: 3-7 micro-steps por tarea
- **PERO**: Son descripciones textuales, NO especificaciones atómicas
- **Output**: JSON con tasks → subtasks (texto plano)

#### `/src/models/masterplan.py`
- **MasterPlanTask**: Tarea de alto nivel
  - `name`, `description`, `target_files`
  - `complexity`: low/medium/high/critical
  - `depends_on_tasks`: dependencias
  - `subtasks`: array de descripciones
- **MasterPlanSubtask**: Micro-paso textual
  - `name`, `description` (texto plano)
  - NO tiene especificación ejecutable

**GAP CRÍTICO**:
- Las tareas tienen `subtasks`, pero son **texto plano**
- NO hay especificaciones atómicas de 10 LOC
- NO hay validación previa de atomicidad
- La atomización ocurre DESPUÉS al ejecutar

### 1.3 Integración con Fase 1

**Cambios de Fase 1** (ya implementados):
- `temperature=0` para determinismo
- `seed=42` para reproducibilidad
- Prompt optimizado para generación consistente

**¿Dónde encaja Fase 2?**
```
MasterPlanTask → [NUEVA CAPA] → AtomicSpec (10 LOC) → Code Generation
                                      ↑
                                 Validación PREVIA
```

---

## 2. DISEÑO DE FASE 2: ATOMIZACIÓN PROACTIVA

### 2.1 Nuevo Flujo (Proactivo)

```
MasterPlanTask → SpecGenerator → [AtomicSpec 1..N] → Validator → Code Generation
                       ↓                                   ↓
               Prompt con contexto                  Pre-validación
               Discovery Document                    (antes de código)
```

**Ventajas**:
1. **Validación temprana**: Rechazar specs inválidas ANTES de generar código
2. **Determinismo**: Specs son reproducibles (seed=42)
3. **Planificación**: Conocer CUÁNTOS átomos antes de ejecutar
4. **Trazabilidad**: Task → Specs → Code (cadena completa)

### 2.2 Modelo AtomicSpec (Especificación, NO código)

**Ubicación**: `/src/models/atomic_spec.py`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from uuid import UUID, uuid4

class AtomicSpec(BaseModel):
    """
    Especificación Atómica - 10 LOC target

    Especificación PREVIA a generación de código.
    Representa un átomo de 10 LOC con contexto completo.
    """

    # Identificación
    spec_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: UUID  # FK a MasterPlanTask
    sequence_number: int  # 1..N dentro de la tarea

    # Descripción
    description: str = Field(
        ...,
        max_length=200,
        description="Descripción precisa de QUÉ hace este átomo (max 200 chars)"
    )

    # Tipos y Contexto
    input_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Input types: {'param_name': 'Type'}"
    )
    output_type: str = Field(
        ...,
        description="Return type de la función/bloque"
    )

    # Métricas de Atomicidad
    target_loc: int = Field(
        default=10,
        ge=5,
        le=15,
        description="Target LOC (goal: 10, min 5, max 15)"
    )
    complexity_limit: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Max cyclomatic complexity"
    )

    # Dependencias y Contexto
    imports_required: List[str] = Field(
        default_factory=list,
        description="Required imports: ['from x import y', 'import z']"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Spec IDs this depends on (otros AtomicSpec)"
    )

    # Condiciones
    preconditions: List[str] = Field(
        default_factory=list,
        description="Required state before execution"
    )
    postconditions: List[str] = Field(
        default_factory=list,
        description="Expected state after execution"
    )

    # Testing
    test_cases: List[Dict] = Field(
        default_factory=list,
        description="Input/output examples: [{'input': {...}, 'output': ...}]"
    )

    # Restricciones
    must_be_pure: bool = Field(
        default=False,
        description="Must be a pure function (no side effects)"
    )
    must_be_idempotent: bool = Field(
        default=False,
        description="Multiple calls with same input = same output"
    )

    # Metadata
    language: str = Field(default="python")
    target_file: Optional[str] = None

    @field_validator('description')
    def validate_description(cls, v):
        """Ensure description is concise and actionable"""
        if len(v.split()) < 3:
            raise ValueError("Description too short (min 3 words)")
        return v

    @field_validator('test_cases')
    def validate_test_cases(cls, v):
        """Ensure at least one test case"""
        if len(v) == 0:
            raise ValueError("At least one test case required")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "spec_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_id": "660e8400-e29b-41d4-a716-446655440001",
                "sequence_number": 1,
                "description": "Validate user email format using regex",
                "input_types": {"email": "str"},
                "output_type": "bool",
                "target_loc": 10,
                "complexity_limit": 2.0,
                "imports_required": ["import re"],
                "dependencies": [],
                "preconditions": ["email is not None"],
                "postconditions": ["returns True if valid, False otherwise"],
                "test_cases": [
                    {"input": {"email": "test@example.com"}, "output": True},
                    {"input": {"email": "invalid"}, "output": False}
                ],
                "must_be_pure": True,
                "must_be_idempotent": True
            }
        }
```

**Diferencias vs AtomicUnit**:
| Característica | AtomicSpec (Fase 2) | AtomicUnit (Actual) |
|----------------|---------------------|---------------------|
| **Momento** | ANTES de código | DESPUÉS de código |
| **Contenido** | Especificación | Código + resultado |
| **Validación** | Pre-generación | Post-generación |
| **Modificable** | Sí (rechazar/re-generar) | No (ya ejecutado) |
| **Tamaño** | Liviano (spec) | Pesado (código + metadata) |
| **Storage** | Opcional (cache) | Persistente (DB) |

### 2.3 Validador de AtomicSpec

**Ubicación**: `/src/services/atomic_spec_validator.py`

```python
from typing import List, Tuple
from .atomic_spec import AtomicSpec

class AtomicSpecValidationResult:
    """Resultado de validación de spec"""
    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str]):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.score = 1.0 if is_valid else 0.0

class AtomicSpecValidator:
    """
    Validador de AtomicSpec - Pre-generación

    Valida especificaciones ANTES de generar código.
    """

    def __init__(
        self,
        max_loc: int = 15,
        max_complexity: float = 3.0,
        min_test_cases: int = 1
    ):
        self.max_loc = max_loc
        self.max_complexity = max_complexity
        self.min_test_cases = min_test_cases

    def validate(self, spec: AtomicSpec) -> AtomicSpecValidationResult:
        """
        Validate atomic spec against atomicity criteria

        Returns:
            Validation result with errors/warnings
        """
        errors = []
        warnings = []

        # 1. Single Responsibility Check
        if not self._has_single_responsibility(spec):
            errors.append(
                f"Description '{spec.description}' suggests multiple responsibilities"
            )

        # 2. LOC Target Check
        if spec.target_loc > self.max_loc:
            errors.append(
                f"Target LOC {spec.target_loc} exceeds maximum {self.max_loc}"
            )
        elif spec.target_loc < 5:
            warnings.append(
                f"Target LOC {spec.target_loc} is very small (<5)"
            )

        # 3. Complexity Check
        if spec.complexity_limit > self.max_complexity:
            errors.append(
                f"Complexity limit {spec.complexity_limit} exceeds maximum {self.max_complexity}"
            )

        # 4. Test Cases Check
        if len(spec.test_cases) < self.min_test_cases:
            errors.append(
                f"At least {self.min_test_cases} test case(s) required, got {len(spec.test_cases)}"
            )

        # 5. Type Safety Check
        if not spec.output_type:
            warnings.append("No output type specified")

        if not spec.input_types:
            warnings.append("No input types specified")

        # 6. Context Completeness Check
        if not spec.imports_required and spec.target_loc > 5:
            warnings.append("No imports specified for non-trivial spec")

        # 7. Purity Check (if required)
        if spec.must_be_pure:
            if self._has_side_effects_indicators(spec):
                errors.append("Spec marked as pure but has side effect indicators")

        # 8. Testability Check
        if not self._is_testable(spec):
            errors.append("Spec is not testable (missing clear I/O)")

        is_valid = len(errors) == 0
        return AtomicSpecValidationResult(is_valid, errors, warnings)

    def _has_single_responsibility(self, spec: AtomicSpec) -> bool:
        """Check if description suggests single responsibility"""
        description = spec.description.lower()

        # Multiple verbs indicate multiple responsibilities
        verbs = ['create', 'update', 'delete', 'validate', 'send', 'fetch', 'process']
        verb_count = sum(1 for verb in verbs if verb in description)

        # Multiple "and" suggests multiple operations
        and_count = description.count(' and ')

        return verb_count <= 1 and and_count <= 1

    def _has_side_effects_indicators(self, spec: AtomicSpec) -> bool:
        """Check for side effect indicators in spec"""
        description = spec.description.lower()
        side_effect_keywords = [
            'save', 'persist', 'write', 'update', 'delete',
            'send', 'publish', 'log', 'print'
        ]
        return any(keyword in description for keyword in side_effect_keywords)

    def _is_testable(self, spec: AtomicSpec) -> bool:
        """Check if spec is testable"""
        # Must have clear inputs and outputs
        has_inputs = len(spec.input_types) > 0 or spec.description
        has_outputs = bool(spec.output_type)
        has_test_cases = len(spec.test_cases) >= self.min_test_cases

        return has_inputs and has_outputs and has_test_cases

    def validate_batch(self, specs: List[AtomicSpec]) -> Tuple[List[AtomicSpec], List[Tuple[AtomicSpec, AtomicSpecValidationResult]]]:
        """
        Validate multiple specs and separate valid from invalid

        Returns:
            (valid_specs, invalid_specs_with_errors)
        """
        valid = []
        invalid = []

        for spec in specs:
            result = self.validate(spec)
            if result.is_valid:
                valid.append(spec)
            else:
                invalid.append((spec, result))

        return valid, invalid
```

### 2.4 Generador de AtomicSpec

**Ubicación**: `/src/services/atomic_spec_generator.py`

```python
from typing import List, Dict, Any, Optional
from uuid import UUID
from src.models.masterplan import MasterPlanTask, DiscoveryDocument
from src.llm import EnhancedAnthropicClient, TaskType, TaskComplexity
from .atomic_spec import AtomicSpec
from .atomic_spec_validator import AtomicSpecValidator
import json

class AtomicSpecGenerator:
    """
    Generador de AtomicSpec desde MasterPlanTask

    Genera N especificaciones atómicas (10 LOC cada una) a partir de una tarea.
    Valida cada spec ANTES de retornar.
    """

    def __init__(
        self,
        llm_client: Optional[EnhancedAnthropicClient] = None,
        validator: Optional[AtomicSpecValidator] = None
    ):
        self.llm = llm_client or EnhancedAnthropicClient()
        self.validator = validator or AtomicSpecValidator()

    async def generate_specs_from_task(
        self,
        task: MasterPlanTask,
        discovery: DiscoveryDocument,
        max_retries: int = 3
    ) -> List[AtomicSpec]:
        """
        Generate atomic specs from a task

        Args:
            task: MasterPlanTask to atomize
            discovery: Discovery context for generation
            max_retries: Max re-generation attempts for invalid specs

        Returns:
            List of validated AtomicSpec instances

        Raises:
            ValueError: If unable to generate valid specs after retries
        """

        for attempt in range(max_retries):
            # Generate specs with LLM
            specs = await self._generate_specs_llm(task, discovery)

            # Validate all specs
            valid_specs, invalid_specs = self.validator.validate_batch(specs)

            if len(invalid_specs) == 0:
                # All specs valid
                return valid_specs

            # Some specs invalid - report and retry
            print(f"Attempt {attempt + 1}: {len(invalid_specs)} invalid specs, retrying...")
            for spec, result in invalid_specs:
                print(f"  - {spec.description}: {', '.join(result.errors)}")

        # Failed after all retries
        raise ValueError(
            f"Failed to generate valid atomic specs after {max_retries} attempts. "
            f"Last attempt had {len(invalid_specs)} invalid specs."
        )

    async def _generate_specs_llm(
        self,
        task: MasterPlanTask,
        discovery: DiscoveryDocument
    ) -> List[AtomicSpec]:
        """Generate specs using LLM"""

        # Build context from discovery
        context = self._build_discovery_context(discovery)

        # Build prompt
        prompt = self._build_generation_prompt(task, context)

        # Generate with Fase 1 params (temp=0, seed=42)
        response = await self.llm.generate_with_caching(
            task_type="atomic_spec_generation",
            complexity=self._map_task_complexity(task.complexity),
            cacheable_context={
                "system_prompt": ATOMIC_SPEC_SYSTEM_PROMPT,
                "discovery_context": context
            },
            variable_prompt=prompt,
            max_tokens=4000,
            temperature=0.0,  # Fase 1: determinismo
            # seed=42  # Fase 1: reproducibilidad (si el LLM lo soporta)
        )

        # Parse response to AtomicSpec list
        specs = self._parse_specs_response(response["content"], task.task_id)

        return specs

    def _build_discovery_context(self, discovery: DiscoveryDocument) -> Dict[str, Any]:
        """Build discovery context for prompt"""
        return {
            "domain": discovery.domain,
            "bounded_contexts": discovery.bounded_contexts,
            "aggregates": discovery.aggregates,
            "value_objects": discovery.value_objects,
            "services": discovery.services
        }

    def _build_generation_prompt(self, task: MasterPlanTask, context: Dict) -> str:
        """Build prompt for spec generation"""
        return f"""Generate atomic specifications for this task:

**Task**: {task.name}
**Description**: {task.description}
**Complexity**: {task.complexity.value}
**Target Files**: {', '.join(task.target_files)}

**Discovery Context**:
- Domain: {context['domain']}
- Bounded Contexts: {len(context['bounded_contexts'])} contexts
- Aggregates: {len(context['aggregates'])} aggregates

**Requirements**:
1. Generate 3-7 atomic specifications (each ~10 LOC)
2. Each spec MUST be independently executable
3. Each spec MUST have clear input/output types
4. Each spec MUST have at least 1 test case
5. Complexity limit: ≤3.0 per spec
6. Target LOC: 10 (min 5, max 15)

Return a JSON array of AtomicSpec objects following the schema.
"""

    def _map_task_complexity(self, task_complexity) -> TaskComplexity:
        """Map task complexity to LLM complexity"""
        mapping = {
            "low": TaskComplexity.LOW,
            "medium": TaskComplexity.MEDIUM,
            "high": TaskComplexity.HIGH,
            "critical": TaskComplexity.CRITICAL
        }
        return mapping.get(str(task_complexity).lower(), TaskComplexity.MEDIUM)

    def _parse_specs_response(self, content: str, task_id: UUID) -> List[AtomicSpec]:
        """Parse LLM response to AtomicSpec list"""
        # Extract JSON from markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Parse JSON
        try:
            specs_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}")

        # Convert to AtomicSpec instances
        specs = []
        for i, spec_data in enumerate(specs_data):
            spec_data["task_id"] = task_id
            spec_data["sequence_number"] = i + 1
            specs.append(AtomicSpec(**spec_data))

        return specs


# System Prompt for Atomic Spec Generation
ATOMIC_SPEC_SYSTEM_PROMPT = """You are an expert software architect specializing in atomic code decomposition.

Your task is to generate ATOMIC SPECIFICATIONS (not code!) for implementing tasks.

## Atomic Specification Philosophy:

Each spec MUST represent EXACTLY 10 lines of code (LOC):
- Target: 10 LOC
- Minimum: 5 LOC
- Maximum: 15 LOC

## Atomicity Criteria:

1. **Single Responsibility**: One clear purpose (one verb)
2. **Independence**: No shared state with siblings
3. **Testability**: Clear input/output with test cases
4. **Complexity**: Cyclomatic complexity ≤ 3.0
5. **Type Safety**: Explicit input/output types
6. **Context Completeness**: All imports and dependencies specified
7. **Determinism**: Same input = same output
8. **Purity** (preferred): No side effects when possible

## Output Format:

Return a JSON array of AtomicSpec objects:

```json
[
  {
    "description": "Validate user email format using regex pattern",
    "input_types": {"email": "str"},
    "output_type": "bool",
    "target_loc": 10,
    "complexity_limit": 2.0,
    "imports_required": ["import re"],
    "dependencies": [],
    "preconditions": ["email is not None", "email is str"],
    "postconditions": ["returns True if valid email", "returns False otherwise"],
    "test_cases": [
      {"input": {"email": "test@example.com"}, "output": true},
      {"input": {"email": "invalid-email"}, "output": false}
    ],
    "must_be_pure": true,
    "must_be_idempotent": true,
    "language": "python"
  }
]
```

## Guidelines:

- Break tasks into 3-7 atomic specs
- Each spec = ~10 LOC of actual implementation
- Specs must be independently executable
- Provide at least 1 test case per spec
- Use explicit types (Python type hints, TypeScript types, etc.)
- Specify all required imports
- Define clear preconditions/postconditions
- Prefer pure functions when possible

CRITICAL: Return ONLY valid JSON, no markdown, no explanations outside the JSON.
"""
```

---

## 3. INTEGRACIÓN CON FASE 1

### 3.1 ¿Dónde va el generador?

**Punto de integración**:
```
MasterPlanTask (generado por MasterPlanGenerator)
           ↓
   [NUEVO] AtomicSpecGenerator
           ↓
    List[AtomicSpec] (validados)
           ↓
    Code Generation (Fase 3+)
```

**Modificaciones necesarias**:
1. **NO modificar** `MasterPlanGenerator` (mantener Fase 1 intacta)
2. **Nuevo servicio**: `AtomicSpecGenerator` (standalone)
3. **Ejecución**: Llamar DESPUÉS de crear MasterPlanTask, ANTES de generar código

### 3.2 Prompt Template con Fase 1

El prompt del generador YA incluye:
- `temperature=0.0` (determinismo de Fase 1)
- `seed=42` (reproducibilidad - si el LLM lo soporta)
- Contexto del Discovery Document
- Validación de 10 LOC target

**Sistema de validación en bucle**:
```python
for attempt in range(max_retries=3):
    specs = await llm.generate(prompt)
    valid, invalid = validator.validate_batch(specs)

    if all valid:
        return specs
    else:
        print(f"Retry {attempt}: {len(invalid)} specs inválidos")

raise ValueError("No se pudo generar specs válidos")
```

---

## 4. ANÁLISIS DE IMPACTO

### 4.1 Cambios en Código Existente

| Componente | Cambio | Tipo | Justificación |
|------------|--------|------|---------------|
| `MasterPlanGenerator` | **NINGUNO** | N/A | Mantener Fase 1 intacta |
| `AtomicUnit` | **NINGUNO** | N/A | Modelo legacy sigue funcionando |
| `AtomicityValidator` | **NINGUNO** | N/A | Validación post-código se mantiene |
| Database | **NUEVO** | Aditivo | Tabla opcional para `AtomicSpec` (cache) |

**Conclusión**: **CERO breaking changes**

### 4.2 ¿Feature Flags necesarios?

**NO** - Fase 2 es completamente aditiva:
- Nuevo servicio (`AtomicSpecGenerator`)
- Nuevo modelo (`AtomicSpec`)
- Validador nuevo (`AtomicSpecValidator`)
- NO toca código existente

**Estrategia de adopción**:
1. Implementar Fase 2 en paralelo
2. Ejecutar ambos flujos (legacy + nuevo) para comparar
3. Migrar gradualmente cuando Fase 2 esté validada

### 4.3 ¿Migration necesaria?

**NO** - Fase 2 no requiere migration:
- `AtomicSpec` es un modelo Pydantic (no ORM)
- Se puede persistir en DB opcional para caching
- NO afecta tablas existentes (`atomic_units`, `masterplans`)

**Schema opcional para cache**:
```sql
CREATE TABLE IF NOT EXISTS atomic_specs_cache (
    spec_id UUID PRIMARY KEY,
    task_id UUID REFERENCES masterplan_tasks(task_id),
    spec_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_atomic_specs_task ON atomic_specs_cache(task_id);
```

---

## 5. PRÓXIMOS PASOS

### 5.1 Implementación Inmediata (2-3 horas)

1. **Crear modelo** `/src/models/atomic_spec.py` (30 min)
2. **Crear validador** `/src/services/atomic_spec_validator.py` (45 min)
3. **Crear generador** `/src/services/atomic_spec_generator.py` (60 min)
4. **Tests unitarios** `/tests/unit/test_atomic_spec_validator.py` (45 min)

### 5.2 Prueba de Concepto

**Caso de prueba**:
```python
# Tomar 1 MasterPlanTask del sistema actual
task = get_sample_task()  # e.g., "Create User SQLAlchemy model"

# Generar specs
generator = AtomicSpecGenerator()
specs = await generator.generate_specs_from_task(task, discovery)

# Resultado esperado:
# [
#   AtomicSpec(description="Import SQLAlchemy dependencies", target_loc=3),
#   AtomicSpec(description="Define User class with __tablename__", target_loc=5),
#   AtomicSpec(description="Add id field as UUID primary key", target_loc=7),
#   AtomicSpec(description="Add email and password_hash fields", target_loc=10),
#   AtomicSpec(description="Add timestamp fields (created_at, updated_at)", target_loc=8)
# ]
```

### 5.3 Integración Futura

**Fase 3** (siguiente sprint):
- Generador de código desde `AtomicSpec`
- Executor que consume specs y genera código
- Comparación: Fase 2 (specs first) vs Legacy (code first)

---

## 6. MÉTRICAS DE ÉXITO

### 6.1 Métricas Técnicas

1. **Validación previa**: ≥95% de specs generadas son válidas en primer intento
2. **Atomicidad**: 100% de specs tienen target_loc=10±5
3. **Testabilidad**: 100% de specs tienen ≥1 test case
4. **Determinismo**: Generar mismos specs con mismo seed (reproducibilidad)
5. **Performance**: Generar specs <5 segundos por tarea

### 6.2 Métricas de Negocio

1. **Reducción de re-trabajo**: Menos código inválido generado
2. **Planificación**: Conocer N átomos ANTES de ejecutar
3. **Trazabilidad**: Task → Specs → Code (full audit trail)
4. **Calidad**: Código generado cumple atomicidad por diseño

---

## CONCLUSIÓN

**Fase 2 es VIABLE y NO INVASIVA**:
- ✅ NO requiere cambios en código existente
- ✅ NO requiere migrations
- ✅ NO requiere feature flags
- ✅ Integra perfectamente con Fase 1 (temp=0, seed=42)
- ✅ Proporciona validación PREVIA (antes de código)
- ✅ Permite planificación exacta (N átomos conocidos)

**Riesgo**: BAJO - Implementación aditiva, reversible
**Valor**: ALTO - Validación temprana + determinismo + planificación

**RECOMENDACIÓN**: Proceder con implementación inmediata (2-3 horas)
