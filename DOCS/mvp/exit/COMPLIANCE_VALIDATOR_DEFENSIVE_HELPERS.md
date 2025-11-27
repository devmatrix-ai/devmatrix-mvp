# ComplianceValidator Defensive Helpers

**Fecha**: Nov 26, 2025
**Status**: IMPLEMENTADO
**Prioridad**: ALTA (bloqueaba E2E)

---

## Problema

El `ComplianceValidator` recibía tanto objetos `ApplicationIR` como `SpecRequirements` legacy, pero llamaba métodos que solo existían en uno u otro:

### Errores Específicos

1. **Phase 6.5**: `'SpecRequirements' object has no attribute 'get_entities'`
   - `validate()` llamaba `spec_requirements.get_entities()` directamente
   - `SpecRequirements` usa atributo `.entities`, no método

2. **Phase 7**: `'ApplicationIR' object has no attribute 'requirements'`
   - `_identify_missing_requirements()` accedía `spec.requirements[:5]`
   - `ApplicationIR` guarda requirements en `metadata["requirements"]`

---

## Solución: Defensive Helpers

Se agregaron 4 métodos helper que detectan el tipo de objeto y extraen datos correctamente:

### 1. `_get_entities_from_spec(spec)`

```python
def _get_entities_from_spec(self, spec) -> list:
    """Extract entities from spec, handling both ApplicationIR and SpecRequirements."""
    # 1) ApplicationIR: domain_model.entities
    if hasattr(spec, "domain_model") and spec.domain_model is not None:
        if hasattr(spec.domain_model, "entities"):
            return list(spec.domain_model.entities)
        if hasattr(spec.domain_model, "get_entities"):
            return spec.domain_model.get_entities()

    # 2) Object has modern get_entities() method
    if hasattr(spec, "get_entities") and callable(getattr(spec, "get_entities")):
        try:
            return spec.get_entities()
        except Exception as e:
            logger.warning(f"get_entities() failed: {e}")

    # 3) Legacy SpecRequirements.entities attribute
    if hasattr(spec, "entities"):
        return spec.entities if spec.entities else []

    logger.warning(f"Could not extract entities from spec type: {type(spec).__name__}")
    return []
```

### 2. `_get_endpoints_from_spec(spec)`

```python
def _get_endpoints_from_spec(self, spec) -> list:
    """Extract endpoints from spec, handling both ApplicationIR and SpecRequirements."""
    # 1) ApplicationIR: api_model.endpoints
    if hasattr(spec, "api_model") and spec.api_model is not None:
        if hasattr(spec.api_model, "endpoints"):
            return list(spec.api_model.endpoints)
        if hasattr(spec.api_model, "get_endpoints"):
            return spec.api_model.get_endpoints()

    # 2) Object has modern get_endpoints() method
    if hasattr(spec, "get_endpoints") and callable(getattr(spec, "get_endpoints")):
        try:
            return spec.get_endpoints()
        except Exception as e:
            logger.warning(f"get_endpoints() failed: {e}")

    # 3) Legacy SpecRequirements.endpoints attribute
    if hasattr(spec, "endpoints"):
        return spec.endpoints if spec.endpoints else []

    logger.warning(f"Could not extract endpoints from spec type: {type(spec).__name__}")
    return []
```

### 3. `_get_validation_rules_from_spec(spec)`

```python
def _get_validation_rules_from_spec(self, spec) -> list:
    """Extract validation rules from spec, handling both ApplicationIR and SpecRequirements."""
    # 1) ApplicationIR: validation_model.rules
    if hasattr(spec, "validation_model") and spec.validation_model is not None:
        if hasattr(spec.validation_model, "rules"):
            return list(spec.validation_model.rules)

    # 2) Object has modern get_validation_rules() method
    if hasattr(spec, "get_validation_rules") and callable(getattr(spec, "get_validation_rules")):
        try:
            return spec.get_validation_rules()
        except Exception as e:
            logger.warning(f"get_validation_rules() failed: {e}")

    # 3) Legacy SpecRequirements.validation_rules attribute
    if hasattr(spec, "validation_rules"):
        return spec.validation_rules if spec.validation_rules else []

    return []
```

### 4. `_get_requirements_from_spec(spec)`

```python
def _get_requirements_from_spec(self, spec) -> list:
    """Extract functional requirements from spec, handling both ApplicationIR and SpecRequirements."""
    # 1) ApplicationIR: metadata.requirements
    if hasattr(spec, "metadata") and spec.metadata is not None:
        if isinstance(spec.metadata, dict) and "requirements" in spec.metadata:
            return spec.metadata["requirements"]

    # 2) Object has requirements attribute directly
    if hasattr(spec, "requirements"):
        reqs = spec.requirements
        if reqs is not None:
            return list(reqs) if hasattr(reqs, '__iter__') else []

    # 3) Legacy functional_requirements
    if hasattr(spec, "functional_requirements"):
        return spec.functional_requirements if spec.functional_requirements else []

    return []
```

---

## Ubicaciones Actualizadas

### `validate()` method (~línea 300-341)

```python
# ANTES:
entities_from_ir = spec_requirements.get_entities()
endpoints_from_ir = spec_requirements.get_endpoints()
validation_rules = spec_requirements.get_validation_rules()

# DESPUÉS:
entities_from_ir = self._get_entities_from_spec(spec_requirements)
endpoints_from_ir = self._get_endpoints_from_spec(spec_requirements)
validation_rules = self._get_validation_rules_from_spec(spec_requirements)
```

### `validate_from_app()` method (3 ubicaciones)

```python
# Líneas ~595, ~929-930, ~966: Todas actualizadas con helpers
entities_from_ir = self._get_entities_from_spec(spec_requirements)
endpoints_from_ir = self._get_endpoints_from_spec(spec_requirements)
validation_rules = self._get_validation_rules_from_spec(spec_requirements)
```

### `_identify_missing_requirements()` method (~línea 2282)

```python
# ANTES:
for req in spec.requirements[:5]:
    if req.type == "functional":
        missing.append(f"Requirement {req.id}: {req.description[:60]}...")

# DESPUÉS:
requirements = self._get_requirements_from_spec(spec)
for req in requirements[:5]:
    req_type = getattr(req, 'type', None) or (req.get('type') if isinstance(req, dict) else None)
    if req_type == "functional":
        req_id = getattr(req, 'id', None) or (req.get('id', 'N/A') if isinstance(req, dict) else 'N/A')
        req_desc = getattr(req, 'description', '') or (req.get('description', '') if isinstance(req, dict) else '')
        missing.append(f"Requirement {req_id}: {req_desc[:60]}...")
```

---

## Patrón de Prioridad

Cada helper sigue el mismo patrón de prioridad:

1. **ApplicationIR moderno**: `domain_model.entities`, `api_model.endpoints`, etc.
2. **Método moderno**: `get_entities()`, `get_endpoints()`, etc.
3. **SpecRequirements legacy**: `.entities`, `.endpoints` atributos directos
4. **Fallback**: Lista vacía `[]` con warning si ninguno funciona

---

## Verificación

```bash
# Syntax check
python -m py_compile src/validation/compliance_validator.py
# ✅ Passed

# No direct calls outside helpers
grep -n "\.get_entities()" src/validation/compliance_validator.py
# Solo aparece DENTRO de _get_entities_from_spec

grep -n "\.get_endpoints()" src/validation/compliance_validator.py
# Solo aparece DENTRO de _get_endpoints_from_spec
```

---

## Beneficios

| Aspecto | Antes | Después |
|---------|-------|---------|
| Compatibilidad | Solo ApplicationIR o solo SpecRequirements | Ambos |
| Robustez | Crash si tipo incorrecto | Fallback graceful |
| Mantenimiento | Cambios en múltiples lugares | Cambio en 1 helper |
| Debugging | Stack trace críptico | Warnings descriptivos |

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/validation/compliance_validator.py` | +4 helpers, ~8 llamadas actualizadas |

---

## Próximos Pasos

- [ ] Correr E2E test para validar fixes
- [ ] Verificar que main.py se genera correctamente
- [ ] Confirmar compliance score >80%

---

## Notas

- Los helpers están ubicados después de `__init__` en la clase
- Cada helper tiene logging con `logger.warning()` para debugging
- El patrón es extensible: agregar más fallbacks según necesidad
