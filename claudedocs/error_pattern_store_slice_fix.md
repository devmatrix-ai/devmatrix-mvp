# Error Pattern Store - Fix para objetos slice en metadata

**Fecha**: 2025-11-19
**Tipo**: Bug Fix
**Severidad**: Medium (Non-blocking)
**Componente**: Cognitive Feedback Loop

## Problema

El sistema de aprendizaje cognitivo (Cognitive Feedback Loop) estaba fallando al intentar almacenar patrones de éxito/error cuando los metadata contenían objetos `slice` de Python u otros tipos no-serializables.

### Error observado
```
[ERROR] [services.error_pattern_store] Failed to store success pattern: unhashable type: 'slice'
```

### Impacto
- **Funcional**: El Cognitive Feedback Loop no podía aprender de algunos patrones de código exitosos
- **Alcance**: No bloqueante - no afecta la generación de código, solo el aprendizaje de patrones
- **Frecuencia**: Ocurría cuando objetos Task contenían propiedades con slices en sus metadata

## Causa raíz

Los objetos `SuccessPattern` y `ErrorPattern` aceptan un campo `metadata: Dict[str, Any]` que puede contener cualquier tipo de dato. Sin embargo:

1. Qdrant (vector database) requiere payloads serializables
2. Neo4j requiere propiedades serializables
3. Python no permite objetos `slice` como claves de diccionario (unhashable type)

Cuando el código de generación pasaba objetos Task con propiedades complejas (incluyendo slices) en los metadata, el sistema intentaba almacenarlos directamente y fallaba.

## Solución implementada

Se agregó sanitización defensiva de metadata en `error_pattern_store.py`:

### 1. Función de sanitización principal
```python
def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize metadata to ensure all keys and values are serializable.

    Handles problematic types like slice objects that can't be used as dict keys
    or stored in vector databases.
    """
```

**Comportamiento**:
- Slices → Convierte a string: `slice(1, 10, 2)` → `"slice(1, 10, 2)"`
- Objetos complejos → Convierte a string con `str(obj)`
- Tipos básicos (str, int, float, bool, None) → Mantiene sin cambios
- Diccionarios anidados → Sanitiza recursivamente
- Listas/tuplas → Sanitiza cada elemento

### 2. Función helper para valores anidados
```python
def _sanitize_value(self, value: Any) -> Any:
    """Helper to sanitize individual values in lists/tuples."""
```

Maneja sanitización de valores dentro de listas y tuplas, aplicando las mismas reglas recursivamente.

### 3. Integración en métodos de almacenamiento

**En `store_error()`**:
```python
# Sanitize metadata to prevent unhashable type errors
sanitized_metadata = self._sanitize_metadata(error.metadata)

# Add sanitized metadata if present
if sanitized_metadata:
    payload["metadata"] = sanitized_metadata
```

**En `store_success()`**:
```python
# Sanitize metadata to prevent unhashable type errors
sanitized_metadata = self._sanitize_metadata(success.metadata)

# Add sanitized metadata if present
if sanitized_metadata:
    payload["metadata"] = sanitized_metadata
```

## Verificación

### Tests ejecutados
✅ Slice como valor en metadata
✅ Objetos complejos en metadata
✅ Slices anidados en estructuras complejas
✅ ErrorPattern con slices

### Resultado
Todos los tests pasaron exitosamente. El sistema ahora puede almacenar cualquier tipo de metadata sin fallar.

## Archivos modificados

- [`src/services/error_pattern_store.py`](../src/services/error_pattern_store.py)
  - Líneas 149-203: Funciones de sanitización
  - Líneas 222-223: Uso en `store_error()`
  - Líneas 305-306: Uso en `store_success()`

## Impacto del cambio

### Positivo
- ✅ El Cognitive Feedback Loop ahora puede aprender de todos los patrones de código
- ✅ No más errores "unhashable type: 'slice'" en los logs
- ✅ Robustez mejorada - maneja cualquier tipo de objeto en metadata
- ✅ Backward compatible - no rompe código existente

### Consideraciones
- Objetos slice se convierten a string, perdiendo su naturaleza de objeto (aceptable para propósitos de logging/storage)
- Pequeño overhead de procesamiento por la sanitización (negligible)

## Monitoreo

Verificar que los logs ya no muestren:
```
[ERROR] [services.error_pattern_store] Failed to store success pattern: unhashable type: 'slice'
```

Confirmar que el Cognitive Feedback Loop almacena patrones exitosamente:
```
[INFO] [services.error_pattern_store] Stored success pattern: {pattern_id}
```

## Referencias

- Issue: Error pattern store failing with unhashable type: 'slice'
- Sprint: Sprint 1 - Validation & Bug Fixes
- Related: Cognitive Feedback Loop (MGE v2)
