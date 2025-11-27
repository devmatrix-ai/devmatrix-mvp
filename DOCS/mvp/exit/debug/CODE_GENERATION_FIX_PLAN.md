# Code Generation Fix Plan

**Date**: Nov 26, 2025
**Status**: ✅ IMPLEMENTADO
**Priority**: ALTA

---

## Problem Summary

El E2E pipeline genera solo 3 archivos en lugar de la estructura completa de la aplicación.

### Síntomas Observados

```text
Log: /tmp/e2e_schema_fixes_test_Ariel_006_06.log

1. "📦 Parsed legacy mode output: 3 files"
2. "⚠️ No main.py found in generated code, skipping repair phase"
3. "✗ File check: src/main.py"
4. main.py en root contiene: "name 'fields' is not defined" (mensaje de error, no código)
```

### Root Cause Identificada

**El problema no era solo `fields` vs `attributes`** - era el comportamiento tóxico del error handler:

```python
# ANTES (línea 684) - TÓXICO:
if allow_syntax_errors:
    return str(syntax_error)  # ← Devolvía el error como "código"
```

Esto causaba que cualquier excepción en `_compose_patterns()` se devolviera como string,
que luego era parseado como si fuera código real, resultando en archivos corruptos.

---

## Fix Implementado: Estructura de 3 Capas

### Capa 1: Error Handling Correcto ✅

**Archivo**: `src/services/code_generation_service.py`
**Líneas**: 687-725

```python
# DESPUÉS - CORRECTO:
except Exception as gen_error:
    # Log completo con traceback
    import traceback
    logger.error(
        f"Code generation from ApplicationIR failed: {gen_error}",
        extra={"traceback": traceback.format_exc()}
    )

    if allow_syntax_errors:
        # NUNCA devolver error como código
        # En cambio, generar estructura mínima válida
        return self._generate_fallback_structure(app_ir, str(gen_error))
    else:
        raise ValueError(f"Code generation failed: {gen_error}") from gen_error
```

**Nuevo método `_generate_fallback_structure()`**:
- Genera estructura mínima pero VÁLIDA sintácticamente
- Incluye: `src/main.py`, `src/models/entities.py`, `src/models/schemas.py`
- Los archivos tienen comentarios claros indicando `FALLBACK MODE`
- Permite que el pipeline continúe para diagnóstico

### Capa 2: Validación Pre-Generación ✅

**Archivo**: `src/services/code_generation_service.py`
**Método**: `_validate_ir_for_generation()`
**Ubicación**: Inicio de `generate_from_application_ir()`

```python
def _validate_ir_for_generation(self, app_ir) -> List[str]:
    """Validate ApplicationIR has minimum required data."""
    errors = []

    if app_ir is None:
        errors.append("ApplicationIR is None")
        return errors

    # Check DomainModelIR
    if not app_ir.domain_model:
        errors.append("DomainModelIR is missing")
    elif not app_ir.domain_model.entities:
        errors.append("DomainModelIR has no entities")
    else:
        for entity in app_ir.domain_model.entities:
            if not hasattr(entity, 'attributes') or not entity.attributes:
                errors.append(f"Entity '{entity.name}' has no attributes")

    # Check APIModelIR
    if not app_ir.api_model:
        errors.append("APIModelIR is missing")
    elif not app_ir.api_model.endpoints:
        errors.append("APIModelIR has no endpoints")

    return errors
```

**Beneficio**: Separa errores de "IR incompleto" de "bug en generadores"

### Capa 3: Validación Post-Generación ✅

**Archivo**: `src/services/code_generation_service.py`
**Método**: `_validate_generated_structure()`
**Ubicación**: Después de `_compose_patterns()`, antes de retornar

```python
def _validate_generated_structure(self, files_dict: Dict[str, str]) -> List[str]:
    """Validate generated files have minimum required structure."""
    errors = []

    required_files = [
        "src/main.py",
        "src/models/entities.py",
        "src/models/schemas.py",
    ]

    for required_file in required_files:
        if required_file not in files_dict:
            errors.append(f"Missing required file: {required_file}")
        elif len(files_dict[required_file].strip()) < 50:
            errors.append(f"File too small or empty: {required_file}")

    # Validate main.py has FastAPI
    if "src/main.py" in files_dict:
        if "FastAPI" not in files_dict["src/main.py"]:
            errors.append("src/main.py does not contain FastAPI app")
        if "FALLBACK MODE" in files_dict["src/main.py"]:
            errors.append("src/main.py is in FALLBACK MODE")

    return errors
```

**Beneficio**: Evita que "3 archivos raros" se consideren éxito

---

## Flujo de Validación Actualizado

```text
generate_from_application_ir()
│
├─→ PRE-VALIDATION: _validate_ir_for_generation()
│   ├─ IR existe?
│   ├─ Entities tienen attributes?
│   └─ Endpoints existen?
│
│   ❌ Falla → _generate_fallback_structure() + log claro
│
├─→ GENERATION: _compose_patterns()
│
│   ❌ Exception → log + traceback + _generate_fallback_structure()
│
├─→ POST-VALIDATION: _validate_generated_structure()
│   ├─ src/main.py existe y tiene FastAPI?
│   ├─ src/models/entities.py existe?
│   └─ src/models/schemas.py existe?
│
│   ❌ Falla → RuntimeError con detalles
│
└─→ ✅ ÉXITO: Retorna código generado
```

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/services/code_generation_service.py` | +3 métodos nuevos, fix error handler |
| `src/validation/compliance_validator.py` | Fix para usar IR getters |

### Métodos Nuevos en code_generation_service.py

1. `_validate_ir_for_generation(app_ir)` → Pre-validación
2. `_validate_generated_structure(files_dict)` → Post-validación
3. `_generate_fallback_structure(app_ir, error)` → Fallback estructural

---

## Success Criteria

- [x] Error handler NO devuelve error como código
- [x] Fallback genera estructura mínima válida
- [x] Pre-validación detecta IR incompleto
- [x] Post-validación detecta estructura incompleta
- [x] Logs tienen traceback completo
- [ ] E2E genera estructura completa (PENDIENTE TEST)
- [ ] ComplianceValidator reporta >80% (PENDIENTE TEST)

---

## Related Fixes

- ComplianceValidator: ✅ COMPLETADO (usaba `.entities` en lugar de `.get_entities()`)
- CodeRepairAgent IR migration: ✅ COMPLETADO
- Phase 3 DAG IR migration: ✅ COMPLETADO

---

## Próximos Pasos

1. **Correr E2E test** para verificar que los fixes funcionan
2. **Si persiste el error `fields`**: El traceback ahora mostrará exactamente dónde ocurre
3. **Agregar unit tests** para los nuevos métodos de validación

---

## Debugging

Si el error persiste, el log ahora mostrará:

```text
ERROR - Code generation from ApplicationIR failed: name 'fields' is not defined
  error_type: NameError
  error_message: name 'fields' is not defined
  traceback: [TRACEBACK COMPLETO CON LÍNEA EXACTA]
```

Esto permitirá identificar EXACTAMENTE dónde en `_compose_patterns()` se usa `fields` incorrectamente.
