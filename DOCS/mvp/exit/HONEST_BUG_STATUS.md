# Estado Honesto de Bugs - DevMatrix Pipeline

**Fecha**: 26 de Noviembre 2025
**Autor**: Análisis post-E2E
**Propósito**: Documentación sin auto-engaño del estado real del sistema

---

## Resumen Ejecutivo

**Quality Gate**: PASSED (DEV environment)
**Semantic Compliance**: 100%
**IR Compliance (Relaxed)**: 86.2%
**Code Repair**: Plateau en 94.4%
**Tests Ejecutados**: 0 (pytest exit code 4)

### Realidad vs Documentación

| Aspecto | Documentado | Realidad |
|---------|-------------|----------|
| Bug #36 (list vs dict) | "FIXED" | ❌ SIGUE FALLANDO |
| Order.creation_date | No documentado | ❌ NUNCA SE GENERA |
| Order.items | No documentado | ❌ TIPO INCORRECTO |
| README.md | "FIXED" | ❌ NO SE GENERA |
| pytest asyncio | No documentado | ❌ CONFIG ROTA |

---

## 🔴 BUGS MARCADOS "FIXED" QUE SIGUEN FALLANDO

### Bug #36: constraints list vs dict - FIX INCOMPLETO

**Estado Documentado**: FIXED (Nov 26, 2025)
**Estado Real**: ❌ PARCIALMENTE ARREGLADO

**Evidencia del E2E**:
```
ERROR - Pattern-based extraction failed: 'list' object has no attribute 'get'
```

**Root Cause Real**:
El fix se aplicó SOLO a `_extract_from_field_descriptions()` (línea 139-149), pero el MISMO BUG existe en `_extract_pattern_rules()` (línea 814):

```python
# business_logic_extractor.py línea 814 - SIN FIX
if (field.get(condition) or
    field.get("constraints", {}).get(condition)):  # ← FALLA si constraints es list
```

**Archivos que necesitan el fix**:
1. `src/services/business_logic_extractor.py` línea 814 ← **NO ARREGLADO**
2. `src/specs/spec_to_application_ir.py` líneas 633-684 ← **NO ARREGLADO**

**Fix Correcto**:
Aplicar la misma normalización list→dict en TODAS las ubicaciones donde se usa `.get()` en constraints.

---

### Bug #32: README.md Not Generated - FIX INEFECTIVO

**Estado Documentado**: FIXED
**Estado Real**: ❌ README.md NO SE GENERA

**Evidencia del E2E**:
```
📄 README.md: ❌ No generado
```

**Root Cause Real**:
El fix verifica contenido pero el problema es que `_generate_with_llm_fallback()` nunca se llama correctamente o falla silenciosamente.

---

## 🔴 BUGS NO DOCUMENTADOS (CRÍTICOS)

### Order.creation_date - Campo Inexistente en Schema

**Problema**:
El spec dice: "Fecha de creación (automática, solo lectura)"
El IR espera: `creation_date`
El código genera: `created_at` en `OrderResponse`

**Evidencia**:
```python
# schemas.py línea 256 - generado
class OrderResponse(OrderBase):
    created_at: datetime  # ← NOMBRE INCORRECTO
```

**Impact**: Code Repair no puede arreglar porque el campo `creation_date` NO EXISTE:
```
Could not find field creation_date in Order schemas to update
```

**Root Cause**:
Desconexión entre naming conventions del IR (creation_date) y código generado (created_at).

---

### Order.items - Tipo Completamente Incorrecto

**Problema**:
El spec dice: "Ítems en la orden (copia del carrito)"
Debería ser: `items: List[OrderItemResponse]`
El código genera: `items: Optional[int]`

**Evidencia**:
```python
# schemas.py líneas 227, 236, 245, 254
items: Optional[int] = None  # ← ESTO ES ABSURDO
```

**Impact**: Imposible tener una Order con sus items. La relación está completamente rota.

**Root Cause**:
El sistema no entiende que `items` es una relación one-to-many, lo interpreta como un campo entero.

---

### pytest asyncio - Configuración Rota

**Problema**:
pytest no ejecuta ningún test (exit code 4).

**Evidencia**:
```
PytestUnraisableExceptionWarning: asyncio_default_fixture_loop_scope is unset
test session starts: 6 items collected
!!! COLLECTION ERROR !!!
```

**Root Cause**:
Falta configuración de pytest-asyncio en el proyecto generado o conflicto de versiones.

---

### Golden App YAML Parsing - LLM Respuestas Malformadas

**Problema**:
El LLM devuelve YAML/JSON malformado durante comparación con Golden App.

**Evidencia**:
```
Golden App YAML Parsing Error: invalid start character: ord('V'): V47_customer_
No JSON found in LLM response (occurred 3 times)
```

**Root Cause**:
El LLM no está siguiendo el formato esperado. Prompt engineering deficiente o modelo inconsistente.

---

## 🟡 PROBLEMAS ESTRUCTURALES

### 1. Inconsistencia de Tipos en constraints

El modelo define `constraints: Dict[str, Any]` pero múltiples lugares lo tratan como list:

| Archivo | Línea | Asume |
|---------|-------|-------|
| domain_model.py | 28 | Dict |
| ir_builder.py | 174 | List (itera) |
| business_logic_extractor.py | 139 | List (fix) |
| business_logic_extractor.py | 814 | Dict (no fix) |
| spec_to_application_ir.py | 633+ | Dict (no fix) |

### 2. Naming Convention Mismatch

| Spec/IR | Código Generado |
|---------|-----------------|
| creation_date | created_at |
| items (relación) | items (int) |
| registration_date | registration_date ✓ |

### 3. Relaciones No Implementadas

El generador no maneja relaciones one-to-many correctamente:
- Order → OrderItem: Genera `items: Optional[int]`
- Cart → CartItem: Similar problema

---

## 📋 PLAN DE SOLUCIÓN REALISTA

### Fase 1: Fixes Inmediatos (2-3 días)

1. **Completar Bug #36** - constraints list→dict en TODAS las ubicaciones
   - `business_logic_extractor.py:814`
   - `spec_to_application_ir.py:633-684`
   - Agregar helper function `normalize_constraints(raw)` usado en todos lados

2. **pytest-asyncio config**
   - Agregar `pytest.ini` o `pyproject.toml` con:
     ```ini
     [tool.pytest.ini_options]
     asyncio_mode = "auto"
     asyncio_default_fixture_loop_scope = "function"
     ```

### Fase 2: Schema Generation (1 semana)

1. **Naming Convention Alignment**
   - Mapeo explícito: `creation_date` ↔ `created_at`
   - O forzar IR a usar mismo naming que SQLAlchemy conventions

2. **Relationship Fields**
   - Detectar campos que son relaciones en el IR
   - Generar `List[RelatedSchema]` en lugar de primitivos

### Fase 3: README y Essential Files (3 días)

1. Debug `_generate_with_llm_fallback()` para entender por qué falla
2. Agregar logging explícito de cada paso
3. Fallback a template estático si LLM falla

### Fase 4: Golden App Parsing (1 semana)

1. Mejorar prompts para formato estricto
2. Agregar retry con reformatting
3. Validación de respuesta antes de parsing

---

## Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Bugs "FIXED" que fallan | 2+ | 0 |
| Tests ejecutados | 0 | >0 |
| README generado | No | Sí |
| Order.items tipo correcto | No | Sí |
| Pattern extraction errores | 1 | 0 |

---

## Conclusión Honesta

El sistema tiene bugs documentados como "FIXED" que siguen fallando. Esto indica:

1. **Testing insuficiente post-fix**: No hay tests que validen los fixes
2. **Fixes parciales**: Se arregla un síntoma, no la causa raíz
3. **Documentación optimista**: Se marca "FIXED" antes de confirmar

**Recomendación**: Antes de marcar cualquier bug como FIXED, debe existir un test automatizado que lo valide.

---

*Documento generado para transparencia y mejora continua del pipeline DevMatrix*
