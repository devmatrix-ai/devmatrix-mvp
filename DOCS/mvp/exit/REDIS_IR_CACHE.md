# Redis IR Cache Migration

## Overview

Migración del cache de ApplicationIR desde filesystem a Redis como cache primario, implementando una estrategia multi-tier para máxima performance y resiliencia.

## Arquitectura Multi-Tier

```
┌─────────────────────────────────────────────────────────────────┐
│                    IR Cache Strategy                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Request ──► TIER 1: Redis (Primary)                          │
│                  │ TTL: 7 days                                  │
│                  │ Key: ir_cache:{spec_name}_{hash8}            │
│                  │                                              │
│                  ▼ Miss?                                        │
│              TIER 2: Filesystem (Fallback)                      │
│                  │ Path: .cache/ir/{spec_name}_{hash8}.json     │
│                  │ Auto warm-up → Redis                         │
│                  │                                              │
│                  ▼ Miss?                                        │
│              TIER 3: LLM Generation                             │
│                  │ Save → Redis + Filesystem                    │
│                  ▼                                              │
│              Return ApplicationIR                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. Constantes de Configuración

**Archivo**: `src/config/constants.py`

```python
# IR Cache TTL: 7 days - spec IR only changes when spec content changes (hash-based invalidation)
IR_CACHE_TTL = int(os.getenv("IR_CACHE_TTL", "604800"))  # 604800 = 7 * 24 * 60 * 60
```

**Rationale del TTL de 7 días**:
- El IR solo cambia cuando el contenido del spec cambia
- La invalidación es por hash del contenido, no por tiempo
- 7 días es suficiente para mantener el cache caliente entre sesiones
- Redis auto-expira, eliminando entradas huérfanas automáticamente

### 2. Métodos de RedisManager

**Archivo**: `src/state/redis_manager.py`

#### `cache_ir(cache_key, ir_data, ttl)`
```python
def cache_ir(self, cache_key: str, ir_data: dict[str, Any], ttl: int = IR_CACHE_TTL) -> bool:
    """Cache ApplicationIR data for a spec.

    Uses SCAN-safe key pattern: ir_cache:{cache_key}

    Args:
        cache_key: Unique key (typically spec_name + content_hash)
        ir_data: Serialized ApplicationIR dictionary
        ttl: Time to live in seconds (default 7 days)

    Returns:
        True if cached successfully
    """
```

#### `get_cached_ir(cache_key)`
```python
def get_cached_ir(self, cache_key: str) -> Optional[dict[str, Any]]:
    """Retrieve cached ApplicationIR data.

    Args:
        cache_key: The cache key used when storing

    Returns:
        Deserialized IR dict or None if not found
    """
```

#### `clear_ir_cache(spec_name)` - SCAN-based Flush
```python
def clear_ir_cache(self, spec_name: Optional[str] = None) -> int:
    """Clear IR cache entries using SCAN (non-blocking).

    FLUSH STRATEGY:
    - Uses SCAN instead of KEYS to avoid blocking Redis in production
    - Iterates in batches of 100 keys
    - Safe for large datasets

    Args:
        spec_name: Optional - clear only for specific spec, or all if None

    Returns:
        Number of keys deleted
    """
```

#### `get_ir_cache_stats()`
```python
def get_ir_cache_stats(self) -> dict[str, Any]:
    """Get statistics about IR cache usage.

    Returns:
        Dict with keys: total_keys, total_size_bytes, specs (list of cached specs)
    """
```

### 3. SpecToApplicationIR Integration

**Archivo**: `src/specs/spec_to_application_ir.py`

```python
async def get_application_ir(self, spec_markdown: str, spec_path: str = "spec.md",
                             force_refresh: bool = False) -> ApplicationIR:
    """Get ApplicationIR with multi-tier caching.

    CACHE STRATEGY:
    1. Redis (primary) - fast, TTL auto-expire (7 days)
    2. Filesystem (fallback) - cold start recovery, debugging
    3. LLM generation - only when no cache exists
    """
```

## Flush Strategy: SCAN vs KEYS

### Por qué SCAN?

```python
# ❌ MALO: Bloquea Redis
keys = redis.keys("ir_cache:*")  # O(N) blocking operation
redis.delete(*keys)

# ✅ BUENO: No bloquea Redis
cursor = 0
while True:
    cursor, keys = redis.scan(cursor, match="ir_cache:*", count=100)
    if keys:
        redis.delete(*keys)
    if cursor == 0:
        break
```

**Ventajas de SCAN**:
1. **No-blocking**: Itera en batches, no bloquea el servidor
2. **Production-safe**: Seguro para datasets grandes
3. **Incremental**: Procesa 100 keys por iteración
4. **Memory efficient**: No carga todas las keys en memoria

### Patrones de Keys

```
ir_cache:ecommerce-api-spec-human_a1b2c3d4    # Spec específico
ir_cache:petstore-spec_e5f6g7h8                # Otro spec
```

**Flush selectivo**:
```python
# Limpiar solo un spec
redis_manager.clear_ir_cache("ecommerce-api-spec-human")
# Pattern: ir_cache:ecommerce-api-spec-human_*

# Limpiar todo el cache IR
redis_manager.clear_ir_cache()
# Pattern: ir_cache:*
```

## Uso

### Uso Normal (Automático)

```python
from src.specs.spec_to_application_ir import SpecToApplicationIR

converter = SpecToApplicationIR()

# Automáticamente usa Redis → Filesystem → LLM
ir = await converter.get_application_ir(spec_content, "my-api-spec.md")
```

### Forzar Refresh

```python
# Ignorar cache, regenerar con LLM
ir = await converter.get_application_ir(spec_content, "my-api-spec.md", force_refresh=True)
```

### Limpiar Cache

```python
# Limpiar todo
converter.clear_cache()

# Solo filesystem
converter.clear_cache(redis=False)

# Solo Redis de un spec
converter.redis.clear_ir_cache("ecommerce-api-spec-human")
```

### Ver Estado del Cache

```python
info = converter.get_cache_info()
print(info)
# {
#     "redis": {"total_keys": 5, "total_size_bytes": 102400, "specs": [...]},
#     "filesystem": {"directory": ".cache/ir", "file_count": 5, "total_size_bytes": 98000}
# }
```

## Warm-up Automático

Cuando se encuentra un cache hit en filesystem pero no en Redis, el sistema automáticamente "calienta" Redis:

```python
# En get_application_ir:
if not redis_hit and filesystem_hit:
    # Warm up Redis from filesystem
    self._cache_to_redis(cache_key, ir_dict)
```

Esto asegura que después de un cold start (reinicio de Redis), el cache se repobla gradualmente desde el filesystem.

## Monitoreo

### Redis Stats

```bash
# Desde redis-cli
SCAN 0 MATCH ir_cache:* COUNT 100

# Memory usage
MEMORY USAGE ir_cache:ecommerce-api-spec-human_a1b2c3d4
```

### Logs

```
INFO: IR cache HIT (Redis) for ecommerce-api-spec-human
INFO: IR cache HIT (filesystem) for petstore-spec, warming Redis
INFO: IR cache MISS for new-api-spec, generating with LLM
INFO: Cleared IR cache from Redis {'pattern': 'ir_cache:*', 'deleted': 15}
```

## Configuración por Entorno

```bash
# Development - TTL corto para debugging
export IR_CACHE_TTL=3600  # 1 hour

# Production - TTL largo
export IR_CACHE_TTL=604800  # 7 days (default)

# Testing - sin cache
export IR_CACHE_TTL=0  # Disabled
```

## Performance

| Operación | Latencia Típica |
|-----------|-----------------|
| Redis HIT | < 5ms |
| Filesystem HIT | 10-50ms |
| LLM Generation | 30-120 seconds |
| SCAN flush (100 keys) | < 100ms |

## Migración desde Sistema Anterior

El sistema anterior usaba solo filesystem. La migración es transparente:

1. **Primera ejecución**: Redis vacío, filesystem con datos existentes
2. **Warm-up automático**: Al leer del filesystem, se copia a Redis
3. **Ejecuciones siguientes**: Redis responde directamente

No se requiere migración manual de datos.

---

*Implementado: 2025-11-26*
*Autor: DevMatrix Pipeline Team*
