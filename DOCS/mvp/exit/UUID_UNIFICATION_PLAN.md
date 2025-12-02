# UUID Unification Plan

## Problema Identificado

**Fecha**: 2025-12-02  
**Síntoma**: seed_db.py genera UUIDs empezando en `000000000020` en lugar de `000000000001`

### Causa Raíz

Existen **DOS generadores de seed_db.py** que no comparten lógica de UUIDs:

| Componente | Ubicación | UUIDs Generados |
|------------|-----------|-----------------|
| `_generate_seed_db_script()` | `code_generation_service.py:5540` | ✅ Correctos (0001, 0002...) |
| `SeedDataAgent.generate_seed_script()` | `seed_data_agent.py:112` | ❌ Desde LLM (puede variar) |

**Flujo actual**:
1. `code_generation_service.py` genera `seed_db.py` con UUIDs correctos
2. `SmokeTestOrchestrator` (línea 92-93) **sobrescribe** con output del LLM
3. LLM genera UUIDs inconsistentes → FK violations

---

## Tabla de Progreso

| Fase | Tarea | Estado | Fecha |
|------|-------|--------|-------|
| 1 | Crear UUIDRegistry centralizado | ⬜ Pendiente | - |
| 2 | Refactorizar code_generation_service.py | ⬜ Pendiente | - |
| 3 | Refactorizar smoke test orchestrator | ⬜ Pendiente | - |
| 4 | Actualizar prompts del LLM planner | ⬜ Pendiente | - |
| 5 | Validar con E2E test | ⬜ Pendiente | - |

**Leyenda**: ⬜ Pendiente | 🔄 En Progreso | ✅ Completado | ❌ Bloqueado

---

## Fase 1: Crear UUIDRegistry Centralizado

**Objetivo**: Módulo único que genere UUIDs deterministas por entidad.

**Ubicación**: `src/core/uuid_registry.py`

**API Propuesta**:
```python
class SeedUUIDRegistry:
    """Genera UUIDs predictibles para seed data y smoke tests."""
    
    def __init__(self, entities: List[str]):
        """Inicializa con lista de entidades del IR."""
        
    def get_uuid(self, entity: str, variant: str = "primary") -> str:
        """Obtiene UUID para entidad.
        
        Args:
            entity: Nombre de entidad (ej: "product", "customer")
            variant: "primary" (tests normales) o "delete" (tests DELETE)
        """
        
    def get_fk_uuid(self, target_entity: str) -> str:
        """Obtiene UUID para referencia FK."""
        
    def to_dict(self) -> Dict[str, Tuple[str, str]]:
        """Exporta mapeo entity -> (primary, delete) para inyectar en prompts."""
```

---

## Fase 2: Refactorizar code_generation_service.py

**Cambios**:
1. Importar `SeedUUIDRegistry`
2. Reemplazar lógica inline de `uuid_base`, `entity_uuids` con registry
3. Mantener compatibilidad con output actual

---

## Fase 3: Refactorizar Smoke Test Orchestrator

**Opción A (Recomendada)**: NO sobrescribir seed_db.py
- `SmokeTestOrchestrator` usa el seed_db.py ya generado por code_generation_service

**Opción B**: Inyectar UUIDs del registry en SeedDataAgent
- Pasar UUIDRegistry al agente para que use los mismos UUIDs

---

## Fase 4: Actualizar Prompts del LLM Planner

**Cambio en `planner_agent.py`**:
```python
PLANNER_USER_PROMPT = """...
## Pre-assigned UUIDs (USE THESE EXACTLY)
{uuid_mapping_json}

IMPORTANT: Use the UUIDs above. Do NOT generate your own UUIDs.
"""
```

---

## Fase 5: Validación E2E

**Comando**:
```bash
rm -rf tests/e2e/generated_apps/ecommerce-* && python tests/e2e/real_e2e_full_pipeline.py
```

**Criterios de éxito**:
- [ ] Product ID = `000000000001`
- [ ] Customer ID = `000000000002`
- [ ] FKs referencian UUIDs correctos
- [ ] No hay "Seed data verification failed"

---

## Archivos Afectados

| Archivo | Acción |
|---------|--------|
| `src/core/uuid_registry.py` | CREAR |
| `src/services/code_generation_service.py` | MODIFICAR |
| `src/validation/smoke_test_orchestrator.py` | MODIFICAR |
| `src/validation/agents/planner_agent.py` | MODIFICAR |
| `src/validation/agents/seed_data_agent.py` | MODIFICAR (opcional) |

