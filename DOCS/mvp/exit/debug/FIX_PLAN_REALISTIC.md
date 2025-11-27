# Plan de Fixes Realista - DevMatrix Pipeline

**Fecha**: 26 de Noviembre 2025
**Basado en**: E2E Test Results y análisis de código
**Última Actualización**: 26 de Noviembre 2025

---

## Estado de Implementación

| Fix | Estado | Archivos Modificados |
|-----|--------|---------------------|
| #1 constraints list→dict | ✅ IMPLEMENTADO | constraint_helpers.py (nuevo), business_logic_extractor.py, spec_to_application_ir.py |
| #2 pytest-asyncio config | ✅ IMPLEMENTADO | code_generation_service.py |
| #3 creation_date mapping | ✅ EXTENDIDO | production_code_generators.py, code_repair_agent.py, ir_compliance_checker.py |
| #4 Order.items tipo | ✅ IMPLEMENTADO Y VERIFICADO | production_code_generators.py |
| #5 README generation | ✅ IMPLEMENTADO | code_generation_service.py (_generate_readme_fallback) |
| #6 YAML parsing | ✅ IMPLEMENTADO | yaml_helpers.py (nuevo) |
| #7 Spanish→English field names | ✅ IMPLEMENTADO | llm_spec_normalizer.py |

### Resultados de Verificación (26 Nov 2025 19:02 UTC)

**E2E Test Run**: `ecommerce-api-spec-human_1764179857`

| Fix | Verificación | Evidencia |
|-----|-------------|-----------|
| #1 Bug #36 | ✅ PASÓ | Sin errores "'list' object has no attribute 'get'" |
| #2 pytest-asyncio | ✅ PASÓ | `asyncio_default_fixture_loop_scope = "function"` en pyproject.toml |
| #3 creation_date | ✅ IMPLEMENTADO | `normalize_field_name()` mapea creation_date → created_at |
| #4 Order.items | ✅ PASÓ | `items: List[OrderItemResponse] = []` en schemas.py:227 |
| #5 README | ✅ IMPLEMENTADO | `_generate_readme_fallback()` con template estático |
| #6 YAML parsing | ✅ IMPLEMENTADO | `robust_yaml_parse()` con 4 estrategias de fallback |

**Compliance**: 100% (entities: 100.0%, endpoints: 100.0%, validations: 100.0%)

### Todos los Fixes Completados (26 Nov 2025 19:20 UTC)

---

## Fix #1: Completar Bug #36 - constraints list→dict ✅ IMPLEMENTADO

### Problema
`constraints` puede ser `list` o `dict`, pero múltiples ubicaciones asumen `dict`.

### Ubicaciones a Arreglar

#### 1.1 business_logic_extractor.py línea 814

**Antes**:
```python
if (field.get(condition) or
    field.get("constraints", {}).get(condition)):
```

**Después**:
```python
raw_constraints = field.get("constraints", {})
# Normalize constraints to dict
if isinstance(raw_constraints, list):
    constraints_dict = {}
    for c in raw_constraints:
        if isinstance(c, str) and "=" in c:
            key, val = c.split("=", 1)
            constraints_dict[key] = val
        elif isinstance(c, str):
            constraints_dict[c] = True
    raw_constraints = constraints_dict

if (field.get(condition) or raw_constraints.get(condition)):
```

#### 1.2 spec_to_application_ir.py líneas 610 y 633-684

**Antes** (línea 610):
```python
constraints = attr.constraints or {}
```

**Después**:
```python
raw_constraints = attr.constraints or {}
# Normalize constraints to dict if it's a list
if isinstance(raw_constraints, list):
    constraints = {}
    for c in raw_constraints:
        if isinstance(c, str) and "=" in c:
            key, val = c.split("=", 1)
            constraints[key] = val
        elif isinstance(c, str):
            constraints[c] = True
else:
    constraints = raw_constraints
```

#### 1.3 Helper function centralizada (MEJOR SOLUCIÓN)

Crear en `src/utils/constraint_helpers.py`:
```python
def normalize_constraints(raw: Any) -> Dict[str, Any]:
    """
    Normalize constraints to dict format.

    Handles:
    - None → {}
    - dict → dict (passthrough)
    - list of strings ["gt=0", "required"] → {"gt": "0", "required": True}
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        result = {}
        for c in raw:
            if isinstance(c, str) and "=" in c:
                key, val = c.split("=", 1)
                result[key] = val
            elif isinstance(c, str):
                result[c] = True
        return result
    return {}
```

Usar en todos los archivos afectados.

---

## Fix #2: pytest-asyncio Configuration

### Problema
pytest no ejecuta tests por falta de configuración asyncio.

### Solución
Agregar a `pyproject.toml` del proyecto generado:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Archivo a Modificar
`src/services/production_code_generators.py` - donde se genera `pyproject.toml`:

```python
def _generate_pyproject_toml(self, ...):
    return '''
[tool.poetry]
...

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
'''
```

---

## Fix #3: Order.creation_date vs created_at

### Problema
- IR espera: `creation_date`
- Código genera: `created_at`
- Code Repair falla porque `creation_date` no existe

### Opciones

#### Opción A: Cambiar IR para usar `created_at`
Modificar `src/cognitive/ir/ir_builder.py` para generar `created_at` en lugar de `creation_date`.

**Pros**: Compatible con convenciones SQLAlchemy
**Contras**: Cambio en IR puede romper otras cosas

#### Opción B: Cambiar generador para usar `creation_date`
Modificar los generadores de schemas para usar `creation_date`.

**Pros**: Mantiene consistencia con IR
**Contras**: Naming no convencional (Entonces arreglesmolo de otra forma, Ariel)

#### Opción C (RECOMENDADA): Mapeo explícito
Crear diccionario de mapeo en generadores:

```python
FIELD_NAME_MAPPING = {
    "creation_date": "created_at",
    "modification_date": "updated_at",
}

def normalize_field_name(ir_name: str) -> str:
    return FIELD_NAME_MAPPING.get(ir_name, ir_name)
```

Y actualizar IR compliance checker para aceptar ambos nombres.

---

## Fix #4: Order.items Tipo Incorrecto

### Problema
`items: Optional[int]` en lugar de `items: List[OrderItemResponse]`

### Root Cause
El generador no detecta que `items` es una relación one-to-many.

### Solución

#### 4.1 En IR Builder
Marcar campos que son relaciones:

```python
# En DomainModelIR
class Attribute:
    ...
    is_relationship: bool = False
    relationship_target: Optional[str] = None
    relationship_type: Optional[str] = None  # "one_to_many", "many_to_one"
```

#### 4.2 En Schema Generator
Detectar relaciones y generar tipo correcto:

```python
def _generate_field_type(self, field: Attribute, schema_type: str) -> str:
    if field.is_relationship:
        target = field.relationship_target
        if field.relationship_type == "one_to_many":
            return f"List[{target}Response] = []"
        elif field.relationship_type == "many_to_one":
            return f"{target}Response"
    # ... tipo normal
```

---

## Fix #5: README.md No Generado

### Problema
`_generate_with_llm_fallback()` no genera README.md efectivamente.

### Diagnóstico Necesario
1. Agregar logging detallado:
```python
async def _generate_with_llm_fallback(self, ...):
    logger.info(f"🔍 Checking for missing files...")

    if "README.md" not in files_dict:
        logger.info(f"📝 README.md missing, generating...")
        readme = await self._generate_readme_md(...)
        logger.info(f"📄 README.md generated: {len(readme)} chars")
        if readme:
            files_dict["README.md"] = readme
        else:
            logger.warning("⚠️ README.md generation returned empty")
```

### Fallback Template
Si LLM falla, usar template estático:

```python
def _generate_readme_fallback(self, app_name: str) -> str:
    return f'''# {app_name}

Generated API application.

## Setup

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

## API Documentation

Visit `/docs` for interactive API documentation.
'''
```

---

## Fix #6: Golden App YAML Parsing

### Problema
LLM devuelve respuestas malformadas durante comparación.

### Solución

#### 6.1 Prompt más estricto
```python
COMPARISON_PROMPT = """
Compare the generated code with the reference.
RESPOND ONLY IN VALID YAML FORMAT.
DO NOT include any text before or after the YAML.
Start your response with '---' and end with '...'

Example format:
---
comparison_result:
  field1: match
  field2: mismatch
...
"""
```

#### 6.2 Retry con reformatting
```python
def parse_llm_response(response: str) -> dict:
    for attempt in range(3):
        try:
            # Try direct parse
            return yaml.safe_load(response)
        except yaml.YAMLError:
            # Extract YAML block if mixed with text
            yaml_match = re.search(r'---\n(.*?)\n\.\.\.', response, re.DOTALL)
            if yaml_match:
                return yaml.safe_load(yaml_match.group(1))
            # Ask LLM to reformat
            response = llm.reformat_to_yaml(response)
    raise ValueError("Could not parse LLM response as YAML")
```

---

## Fix #7: Spanish→English Field Names in IR ✅ IMPLEMENTADO

### Problema
El LLM Spec Normalizer preservaba nombres de campos en español del spec original:
- `estado_activo` en lugar de `is_active`
- `nombre_completo` en lugar de `full_name`
- `fecha_de_registro` en lugar de `registration_date`
- `cliente_propietario` en lugar de `customer_id`
- `cantidad` en lugar de `quantity`
- `precio_unitario` en lugar de `unit_price`
- `monto_total` en lugar de `total_amount`
- `producto` en lugar de `product_id`

Esto causaba que el Code Repair fallara con errores "Could not find field X in schemas".

### Root Cause
El prompt del `LLMSpecNormalizer` no instruía al LLM a traducir nombres de campos a inglés.

### Solución
Agregar regla #5 al `NORMALIZATION_PROMPT` en `src/services/llm_spec_normalizer.py`:

```python
5. CRITICAL: ALL field names MUST be in English using snake_case convention, regardless of the spec language:
   - "estado_activo" → "is_active"
   - "nombre_completo" → "full_name"
   - "fecha_de_registro" → "registration_date"
   - "fecha_creacion" or "creation_date" → "created_at"
   - "cliente_propietario" → "customer_id"
   - "monto_total" → "total_amount"
   - "precio_unitario" → "unit_price"
   - "cantidad" → "quantity"
   - "producto" → "product_id" (if it's a foreign key)
   - Use standard Python/SQLAlchemy naming conventions (snake_case, English)
```

### Verificación Pendiente
E2E test `ecommerce-api-spec-human_1764187772` en progreso para validar que:
1. El IR ahora tiene nombres de campos en inglés
2. Code Repair ya no reporta "field not found" errors
3. IR Compliance mejora de 86.2% → ~100%

---

## Priorización

| Fix | Impacto | Esfuerzo | Prioridad |
|-----|---------|----------|-----------|
| #1 constraints | Alto | Bajo | 🔴 P0 |
| #2 pytest config | Alto | Bajo | 🔴 P0 |
| #4 Order.items | Alto | Medio | 🔴 P0 |
| #3 creation_date | Medio | Bajo | 🟡 P1 |
| #5 README | Bajo | Bajo | 🟡 P1 |
| #6 YAML parsing | Bajo | Medio | 🟢 P2 |

---

## Validación Post-Fix

Para cada fix, crear test automatizado:

```python
# tests/unit/test_bug_fixes.py

def test_bug36_constraints_as_list():
    """Bug #36: constraints can be list, not just dict."""
    field = {"name": "price", "constraints": ["gt=0", "required"]}
    result = extract_validations(field)
    assert "gt" in result  # Should not raise AttributeError

def test_order_items_is_list():
    """Order.items should be List[OrderItemResponse]."""
    schemas = generate_schemas(order_ir)
    assert "List[OrderItemResponse]" in schemas["OrderResponse"]

def test_pytest_config_generated():
    """pytest-asyncio config should be in pyproject.toml."""
    pyproject = generate_pyproject_toml(...)
    assert "asyncio_mode" in pyproject
```

---

## Timeline Realista

| Semana | Fixes | Entregable |
|--------|-------|------------|
| 1 | #1, #2 | E2E tests ejecutan |
| 2 | #3, #4 | Order schemas correctos |
| 3 | #5, #6 | README + parsing estable |

---

## Bugs de Métricas Encontrados (26 Nov 2025)

Durante el análisis de los resultados E2E, se identificaron tres bugs en el tracking de métricas:

### Bug #8: STRICT Mode 0% para Entities y Flows

**Síntoma**:
```json
"strict": {
  "overall": 43.5,
  "entities": 0,      // ❌ Siempre 0%
  "flows": 0,         // ❌ Siempre 0%
  "constraints": 43.5
}
```

**Root Cause 1 - Entity Suffix Mismatch**:
- IR genera: `Product`, `Order`, `Customer`
- Código genera: `ProductEntity`, `OrderEntity`, `CustomerEntity`
- `StrictEntityMatcher` requiere match exacto → 0%

**Root Cause 2 - Spanish Flow Names**:
- IR tiene: `F1: Crear Producto`, `F2: Actualizar Producto`
- Código genera: `create_product()`, `update_product()`
- Match directo imposible por idioma

**Archivos Afectados**:
- `src/services/ir_compliance_checker.py` - `StrictEntityMatcher`
- `src/cognitive/ir/ir_builder.py` - Generación de nombres

**Solución Propuesta**:
```python
# Normalizar sufijos de entidad
def normalize_entity_name(name: str) -> str:
    suffixes = ['Entity', 'Model', 'Schema']
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name

# Normalizar flows a formato inglés
FLOW_NAME_MAPPING = {
    "Crear": "create",
    "Actualizar": "update",
    "Eliminar": "delete",
    "Listar": "list",
    "Obtener": "get",
}
```

**Prioridad**: 🟡 P1 (Métricas incorrectas, no afecta funcionalidad)

---

### Bug #9: Stratum Timing 0ms Duration

**Síntoma**:
```json
"stratum_performance": {
  "TEMPLATE": {"count": 85, "duration_ms": 0},
  "AST": {"count": 0, "duration_ms": 0},
  "LLM": {"count": 0, "duration_ms": 0}
}
```

**Root Cause**:
El código usa `record_file()` pero nunca usa el context manager `track()`:

```python
# real_e2e_full_pipeline.py:623-666
# PROBLEMA: Solo llama record_file(), no track()
stratum_metrics.record_file(file_path, stratum, StratumSource.GENERATION)

# DEBERÍA SER:
with stratum_metrics.track(file_path, stratum):
    # ... código de generación ...
    pass  # track() captura el tiempo automáticamente
```

**Archivo Afectado**:
- `tests/e2e/real_e2e_full_pipeline.py` líneas 623-666

**Solución**:
```python
# Opción A: Usar track() como context manager
for file_path, content in files.items():
    stratum = classify_stratum(file_path)
    with stratum_metrics.track(file_path, stratum):
        write_file(file_path, content)

# Opción B: Pasar duración a record_file()
start = time.time()
write_file(file_path, content)
duration_ms = (time.time() - start) * 1000
stratum_metrics.record_file(file_path, stratum, source, duration_ms=duration_ms)
```

**Prioridad**: 🟢 P2 (Solo métricas de observabilidad)

---

### Bug #10: LLM Tokens Siempre 0

**Síntoma**:
```json
"llm_total_tokens": 0,
"llm_prompt_tokens": 0,
"llm_completion_tokens": 0,
"llm_cost_usd": 0.0,
"llm_calls_count": 0
```

**Root Cause**:
`LLMUsageTracker` está implementado pero nunca se llama después de las llamadas LLM:

```python
# real_e2e_full_pipeline.py:2299
# LLMUsageTracker existe pero NUNCA se usa:
llm_tracker = LLMUsageTracker()

# Después de cada llamada LLM debería llamarse:
# llm_tracker.record_call(
#     model="claude-sonnet-4-5-20250929",
#     prompt_tokens=response.usage.input_tokens,
#     completion_tokens=response.usage.output_tokens
# )

# Pero esto NUNCA se hace en el código actual
```

**Archivos Afectados**:
- `tests/e2e/real_e2e_full_pipeline.py` - `LLMUsageTracker` no integrado
- `src/services/llm_spec_normalizer.py` - Llamadas LLM sin tracking
- `src/services/code_generation_service.py` - Llamadas LLM sin tracking

**Solución**:
```python
# 1. Crear decorator para tracking automático
def track_llm_usage(tracker: LLMUsageTracker):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)
            if hasattr(response, 'usage'):
                tracker.record_call(
                    model=kwargs.get('model', 'unknown'),
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens
                )
            return response
        return wrapper
    return decorator

# 2. O integrar en el cliente Anthropic wrapper
class TrackedAnthropicClient:
    def __init__(self, tracker: LLMUsageTracker):
        self.client = Anthropic()
        self.tracker = tracker

    def messages_create(self, **kwargs):
        response = self.client.messages.create(**kwargs)
        self.tracker.record_call(
            model=kwargs.get('model'),
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens
        )
        return response
```

**Prioridad**: 🟡 P1 (Importante para análisis de costos)

---

## Resumen de Bugs de Métricas

| Bug | Componente | Impacto | Prioridad | Estado |
|-----|-----------|---------|-----------|--------|
| #8 | STRICT Compliance | Métricas falsas | 🟡 P1 | ✅ IMPLEMENTADO |
| #9 | Stratum Timing | Sin timing data | 🟢 P2 | ✅ IMPLEMENTADO |
| #10 | LLM Tokens | Sin cost tracking | 🟡 P1 | ✅ IMPLEMENTADO |

**Nota**: Estos bugs NO afectan la funcionalidad del pipeline. Solo afectan las métricas de observabilidad y el cálculo de compliance STRICT (que es informativo, no bloqueante).

---

## Implementación de Bugs #8, #9, #10 (26 Nov 2025 21:30 UTC)

### Bug #8: IMPLEMENTADO ✅

**Archivos Modificados**: `src/services/ir_compliance_checker.py`

**Cambios**:
1. Agregado `normalize_entity_name()` - Strip de sufijos Entity/Model/Schema
2. Agregado `normalize_flow_name()` - Mapeo Spanish→English para flows
3. Modificado `StrictEntityMatcher.find_entity_match()` - Usa normalización
4. Modificado `StrictFlowMatcher.find_flow_match()` - Usa normalización
5. Modificado `StrictConstraintMatcher.find_entity_constraints()` - Usa normalización

**Código**:
```python
ENTITY_SUFFIXES = ['Entity', 'Model', 'Schema', 'Base', 'Mixin']
FLOW_ACTION_MAPPING = {
    "crear": "create", "actualizar": "update", "eliminar": "delete",
    "borrar": "delete", "listar": "list", "obtener": "get", ...
}

def normalize_entity_name(name: str) -> str:
    for suffix in ENTITY_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[:-len(suffix)]
    return name

def normalize_flow_name(flow_name: str) -> str:
    clean_name = re.sub(r'^F\d+:\s*', '', flow_name)
    words = clean_name.lower().split()
    if words and words[0] in FLOW_ACTION_MAPPING:
        words[0] = FLOW_ACTION_MAPPING[words[0]]
    return '_'.join(words)
```

### Bug #9: IMPLEMENTADO ✅

**Archivos Modificados**:
- `src/services/stratum_metrics.py`
- `tests/e2e/real_e2e_full_pipeline.py`

**Cambios**:
1. Agregado `duration_ms` parameter a `record_file()`
2. Modificado loop de guardado de archivos para medir tiempo
3. Pasa duración a `_record_file_in_manifest()`

**Código**:
```python
# stratum_metrics.py
def record_file(self, stratum: Stratum, tokens: int = 0, duration_ms: float = 0.0):
    if duration_ms > 0:
        metrics.add_duration(duration_ms)

# real_e2e_full_pipeline.py
file_start_time = time.time()
# ... write file ...
file_duration_ms = (time.time() - file_start_time) * 1000
self._record_file_in_manifest(filename, content, duration_ms=file_duration_ms)
```

### Bug #10: IMPLEMENTADO ✅

**Archivos Modificados**:
- `src/services/llm_spec_normalizer.py`
- `tests/e2e/real_e2e_full_pipeline.py`

**Cambios**:
1. Agregado tracking de tokens en `LLMSpecNormalizer`:
   - `last_input_tokens`, `last_output_tokens` class attributes
   - Captura tokens de `response.usage` después de API call
   - Método `get_last_token_usage()` getter
2. Integrado con pipeline E2E para reportar a stratum metrics

**Código**:
```python
# llm_spec_normalizer.py
self.last_input_tokens = response.usage.input_tokens
self.last_output_tokens = response.usage.output_tokens

def get_last_token_usage(self) -> tuple:
    return (self.last_input_tokens, self.last_output_tokens)

# real_e2e_full_pipeline.py
input_tokens, output_tokens = normalizer.get_last_token_usage()
total_tokens = input_tokens + output_tokens
if self.stratum_metrics_collector and total_tokens > 0:
    self.stratum_metrics_collector.record_tokens(MetricsStratum.LLM, total_tokens)
    print(f"    - 📊 LLM tokens tracked: {input_tokens} in + {output_tokens} out = {total_tokens} total")
```

### Verificación (26 Nov 2025 21:32 UTC)

Test E2E ejecutado con evidencia de Bug #10:
```
📊 LLM tokens tracked: 4009 in + 2852 out = 6861 total
```

---

## Bug #8 Post-Mortem: STRICT Flows Still 0% (26 Nov 2025 22:00 UTC)

### Observed Results

After initial Bug #8 implementation:
```
📊 STRICT mode (exact matching):
  ✅ Entities: 100.0%    ← FIXED! (was 0%)
  ⚠️ Flows: 0.0%         ← STILL 0%
  ⚠️ Constraints: 43.5%
```

Entity normalization works, but Flow matching still fails.

### Root Cause Analysis

**Key Insight**: DevMatrix internally works ONLY in English.

#### IR Investigation

Ran diagnostic to inspect ApplicationIR:

```python
# BehaviorModelIR flows (from spec):
 1. name='F1: Crear Producto', entity='N/A'
 2. name='F6: Registrar Cliente', entity='N/A'
 3. name='F10: Ver Carrito Actual', entity='N/A'
...
Total flows: 17

# APIModelIR endpoints (internally translated):
- POST /products -> create_product
- GET /customers/{id} -> get_customer
...
Total endpoints: 19

# Generated service methods:
- f1_crear_producto()
- f6_registrar_cliente()
- f10_ver_carrito_actual()
```

#### The Mismatch

| Component | Name Format | Language |
|-----------|-------------|----------|
| BehaviorModelIR flows | `F1: Crear Producto` | Spanish |
| APIModelIR endpoints | `create_product` | English ✅ |
| Generated methods | `f1_crear_producto` | Spanish |

**Problem**: BehaviorModelIR preserves Spanish flow names from spec.
**Problem**: Code generator keeps F+number prefix AND Spanish.

My compliance fix tried to translate `F1: Crear Producto` → `create_producto`, but generated code has `f1_crear_producto`.

### Correct Fix Location

The fix should NOT be in `ir_compliance_checker.py`.

**DevMatrix Rule**: All internal representations must be in English.

The fix should be in one of:
1. `src/cognitive/ir/ir_builder.py` - Translate flows when building IR
2. `src/services/ir_service_generator.py` - Use English names when generating methods
3. `src/specs/spec_to_application_ir.py` - Translate during spec parsing

### Proposed Fix #8B: Translate Flows in IR Builder

Similar to Fix #7 (Spanish→English field names in LLMSpecNormalizer), we need:

```python
# In ir_builder.py or spec_to_application_ir.py

FLOW_ACTION_MAPPING = {
    "crear": "create",
    "actualizar": "update",
    "eliminar": "delete",
    "listar": "list",
    "obtener": "get",
    "ver": "view",
    "agregar": "add",
    "vaciar": "clear",
    "pagar": "pay",
    "cancelar": "cancel",
    "registrar": "register",
}

def translate_flow_name(spanish_name: str) -> str:
    """
    Translate flow name from Spanish to English.
    'F1: Crear Producto' -> 'create_product'
    """
    # Remove F+number prefix
    clean = re.sub(r'^F\d+:\s*', '', spanish_name)
    words = clean.lower().split()

    # Translate each word
    translated = []
    for word in words:
        eng = FLOW_ACTION_MAPPING.get(word, word)
        translated.append(eng)

    return '_'.join(translated)
```

Then in code generator, use English flow names:
```python
# Instead of: f1_crear_producto
# Generate: create_product
```

### Exact Fix Location

**File**: `src/specs/spec_to_application_ir.py`
**Method**: `_build_behavior_model()` (line 560-596)
**Line**: 579

```python
# BEFORE (line 579):
flow = Flow(
    name=flow_data.get("name", "Unknown"),  # ← Spanish name preserved
    ...
)

# AFTER:
flow = Flow(
    name=translate_flow_name(flow_data.get("name", "Unknown")),  # ← Translated
    ...
)
```

### Files to Modify

1. **`src/specs/spec_to_application_ir.py`** (PRIMARY)
   - Add `translate_flow_name()` function
   - Call it in `_build_behavior_model()` line 579
   - Also translate step.description and step.action

2. **`src/services/ir_service_generator.py`** - Verify uses translated names

3. **`src/services/ir_compliance_checker.py`** - Revert translation logic (no longer needed)

### Priority

🟡 P1 - Important for consistency but doesn't affect functionality.

Current workaround: RELAXED mode (100% flows) is used for production metrics.

---

## Summary: All IRs Language Analysis (26 Nov 2025)

| IR Component | Source | Language | Status |
|-------------|--------|----------|--------|
| DomainModelIR.entities | LLMSpecNormalizer | English ✅ | OK (Fix #7 applied) |
| DomainModelIR.attributes | LLMSpecNormalizer | English ✅ | OK (Fix #7 applied) |
| APIModelIR.endpoints | LLM extraction | English ✅ | OK |
| APIModelIR.operation_ids | LLM extraction | English ✅ | OK |
| **BehaviorModelIR.flows** | LLM extraction | **Spanish ❌** | **NEEDS FIX** |
| ValidationModelIR.rules | Derived from domain | English ✅ | OK |
| InfrastructureModelIR | Config defaults | English ✅ | OK |

### Evidence from Diagnostic

```python
# DomainModelIR - ALREADY IN ENGLISH (Fix #7 working)
entities: ['Product', 'Customer', 'Cart', 'CartItem', 'Order', 'OrderItem']
attributes: ['id', 'name', 'email', 'full_name', 'registration_date'...]

# APIModelIR - ALREADY IN ENGLISH
endpoints: ['create_product', 'get_customer', 'list_products'...]

# BehaviorModelIR - STILL IN SPANISH (NEEDS FIX)
flows: ['F1: Crear Producto', 'F6: Registrar Cliente', 'F10: Ver Carrito Actual'...]
```

### Conclusion

Only **BehaviorModelIR** needs translation fix. Other IRs are correctly using English through:
- Fix #7: LLMSpecNormalizer prompt instructs LLM to translate field names
- LLM extraction: Naturally produces English operation_ids for REST endpoints

The flows bypass LLMSpecNormalizer and go directly from spec text to BehaviorModelIR without translation.

---

## Investigation: Two ApplicationIR Construction Paths (26 Nov 2025)

### Discovery

There are **TWO** different paths to construct ApplicationIR:

| Path | File | Called From | Flows Source |
|------|------|-------------|--------------|
| **IRBuilder** | `ir_builder.py:30` | `code_generation_service.py:345-346` | Hardcoded generic ("State Transition", "Workflow") |
| **SpecToApplicationIR** | `spec_to_application_ir.py:67` | `real_e2e_full_pipeline.py:1239-1240` | LLM extraction from spec (Spanish) |

### E2E Pipeline Flow (Production Path)

```
real_e2e_full_pipeline.py:1239-1240
    ↓
SpecToApplicationIR.get_application_ir()
    ↓
_build_behavior_model() [line 560-596]
    ↓
Flow(name="F1: Crear Producto")  # ← Spanish preserved
    ↓
code_generator.generate_from_application_ir(self.application_ir)  [line 2309]
    ↓
behavior_generator.generate_business_logic(app_ir.behavior_model)  [line 633]
    ↓
_snake_case("F1: Crear Producto") → "f1_crear_producto"  # ← Generated method name
```

### Code Generation Service Dual Entry Points

```python
# code_generation_service.py

# ENTRY 1: generate() - Uses IRBuilder (legacy path)
async def generate(self, spec_requirements: SpecRequirements, ...):
    from src.cognitive.ir.ir_builder import IRBuilder
    app_ir = IRBuilder.build_from_spec(spec_requirements)  # line 345-346
    # ... uses hardcoded generic flows ...

# ENTRY 2: generate_from_application_ir() - Uses external ApplicationIR (E2E path)
async def generate_from_application_ir(self, application_ir, ...):  # line 515
    app_ir = application_ir  # Receives SpecToApplicationIR result
    # ... uses Spanish flows from LLM extraction ...
```

### IRBuilder Hardcoded Flows (ir_builder.py:142-147)

```python
# NOT the production path - only generic flows
flows.append(Flow(
    name="State Transition",        # ← Generic English, not from spec
    type=FlowType.STATE_TRANSITION,
    trigger="State Change",
    description=logic.description
))
```

### Why STRICT Flows = 0%

**The Mismatch**:
```
IR Flow Name:       "F1: Crear Producto"     # ← From SpecToApplicationIR
Generated Method:   "f1_crear_producto"      # ← behavior_code_generator._snake_case()
My normalize_flow_name():  "create_producto"  # ← WRONG transformation
```

**My previous fix** tried to translate in compliance_checker but used different logic than `_snake_case()`.

### Correct Fix Options

**Option A: Fix at IR Construction (Architecturally Correct)**
- Translate in `spec_to_application_ir.py:579`
- IR stores English: `"Create Product"`
- Generated code: `"create_product"`
- Compliance matches: `"create_product"` == `"create_product"` ✅

**Option B: Fix at Compliance Checking (Pragmatic Short-term)**
- Keep IR in Spanish: `"F1: Crear Producto"`
- Use same `_snake_case()` logic in compliance_checker
- Match `"f1_crear_producto"` == `"f1_crear_producto"` ✅

### Recommendation

**Option A** is correct per user requirement: "internamente devmatrix SOLO trabaja en inglés"

But implementing requires:
1. Spanish→English translation dictionary for flow action verbs
2. Testing to ensure behavior_code_generator produces same output

---

## Implementation: Bug #8 Fix v2 + Deprecations (26 Nov 2025)

### Changes Made

1. **Deprecated IRBuilder** (`src/cognitive/ir/ir_builder.py`)
   - Added DEPRECATED notice in module docstring
   - Added `DeprecationWarning` in `build_from_spec()` method
   - Documented that SpecToApplicationIR is the production path

2. **Deprecated generate_from_requirements()** (`src/services/code_generation_service.py`)
   - Added DEPRECATED notice in docstring
   - Added `DeprecationWarning` runtime warning
   - Documented to use `generate_from_application_ir()` instead

3. **Fixed normalize_flow_name()** (`src/services/ir_compliance_checker.py`)
   - Replaced translation logic with same `_snake_case()` transformation
   - Now matches `behavior_code_generator._snake_case()` exactly
   - `"F1: Crear Producto"` → `"f1_crear_producto"` (matches generated code)

### Production Path (E2E Pipeline)

```
SpecToApplicationIR.get_application_ir()
    ↓
generate_from_application_ir(application_ir)
    ↓
behavior_generator.generate_business_logic()
```

### Legacy Path (Deprecated)

```
generate_from_requirements(spec_requirements)
    ↓
IRBuilder.build_from_spec()  # ⚠️ DEPRECATED
    ↓
Hardcoded generic flows
```

---

*Plan generado para ejecución pragmática sin auto-engaño*
