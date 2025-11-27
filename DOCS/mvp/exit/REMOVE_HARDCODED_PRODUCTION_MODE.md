# Plan: Eliminar Generación Hardcodeada en PRODUCTION_MODE

**Fecha**: Nov 26, 2025
**Status**: ✅ COMPLETADO (Fases 1-3 completadas, comentarios limpiados)
**Prioridad**: ALTA

> **Relacionado**: Ver [LLM_MODEL_STRATEGY.md](LLM_MODEL_STRATEGY.md) para la estrategia de modelos implementada.

---

## Problema

`PRODUCTION_MODE=true` activa generadores hardcodeados que bypasean el sistema IR-centric, violando la arquitectura.

**Principio violado**: ApplicationIR es la única fuente de verdad para generación de código.

---

## Ubicaciones a Migrar

### 1. main.py (línea ~2075)

**Actual**:
```python
if os.getenv("PRODUCTION_MODE") == "true":
    main_py_code = self._generate_main_py(app_ir)  # Hardcoded
```

**Migración**:
```python
# Sin PRODUCTION_MODE check - siempre usar IR
main_py_code = self._generate_main_py_from_ir(app_ir)
```

**Datos del IR necesarios**:
- `app_ir.api_model.endpoints` → rutas
- `app_ir.domain_model.entities` → modelos para imports
- `app_ir.metadata` → nombre del proyecto, descripción

---

### 2. Essential Files Generator (línea ~2128)

**Actual**:
```python
is_production = os.getenv("PRODUCTION_MODE") == "true"
method = "Hardcoded generator" if is_production else "LLM fallback"
```

**Migración**:
- Eliminar check de PRODUCTION_MODE
- Siempre usar IR → LLM fallback si no hay patterns

---

### 3. requirements.txt (línea ~2153)

**Actual**:
```python
if os.getenv("PRODUCTION_MODE") == "true":
    return self._generate_requirements_hardcoded()
```

**Migración**:
```python
def _generate_requirements_from_ir(self, app_ir: ApplicationIR) -> str:
    deps = set()

    # Core FastAPI
    deps.add("fastapi>=0.109.0")
    deps.add("uvicorn[standard]>=0.27.0")

    # Database (si hay entities)
    if app_ir.domain_model and app_ir.domain_model.get_entities():
        deps.add("sqlalchemy>=2.0.0")
        deps.add("asyncpg>=0.29.0")
        deps.add("alembic>=1.13.0")

    # Auth (si hay endpoints con auth)
    if self._has_auth_endpoints(app_ir):
        deps.add("python-jose[cryptography]>=3.3.0")
        deps.add("passlib[bcrypt]>=1.7.4")

    # Validación
    deps.add("pydantic>=2.0.0")
    deps.add("pydantic-settings>=2.0.0")

    return "\n".join(sorted(deps))
```

**Datos del IR necesarios**:
- `app_ir.domain_model.entities` → detectar si necesita DB
- `app_ir.api_model.endpoints` → detectar auth requirements
- `app_ir.metadata.tech_stack` → dependencias específicas

---

### 4. Routes/Metrics/Health (línea ~2533)

**Actual**:
```python
if os.getenv("PRODUCTION_MODE") == "true":
    # Hardcoded metrics y health routes
```

**Migración**:
```python
def _generate_health_routes_from_ir(self, app_ir: ApplicationIR) -> str:
    """Genera health/metrics desde IR metadata."""
    project_name = app_ir.metadata.get("project_name", "api")

    return f'''
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    return {{"status": "healthy", "service": "{project_name}"}}

@router.get("/ready")
async def readiness():
    return {{"ready": True}}
'''
```

---

### 5. Docker Files (línea ~2823)

**Actual**:
```python
if os.getenv("PRODUCTION_MODE") == "true":
    # Hardcoded Dockerfile y docker-compose
```

**Migración**:
```python
def _generate_dockerfile_from_ir(self, app_ir: ApplicationIR) -> str:
    """Genera Dockerfile desde IR."""
    python_version = app_ir.metadata.get("python_version", "3.11")
    project_name = app_ir.metadata.get("project_name", "app")

    return f'''FROM python:{python_version}-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
```

---

### 6. Alembic Files (línea ~2883)

**Actual**:
```python
if os.getenv("PRODUCTION_MODE") == "true":
    # Hardcoded alembic.ini y env.py
```

**Migración**:
```python
def _generate_alembic_from_ir(self, app_ir: ApplicationIR) -> Dict[str, str]:
    """Genera archivos Alembic desde IR."""
    db_url = app_ir.metadata.get("database_url", "postgresql://...")

    files = {}
    files["alembic.ini"] = self._alembic_ini_template(db_url)
    files["alembic/env.py"] = self._alembic_env_template(app_ir)

    return files
```

---

## Estrategia de Migración

### Fase 1: Preparación IR
1. Asegurar que `ApplicationIR` tenga todos los campos necesarios:
   - `metadata.project_name`
   - `metadata.python_version`
   - `metadata.database_url`
   - `metadata.tech_stack`

### Fase 2: Crear Generadores IR-Based
1. `_generate_main_py_from_ir(app_ir)`
2. `_generate_requirements_from_ir(app_ir)`
3. `_generate_health_routes_from_ir(app_ir)`
4. `_generate_dockerfile_from_ir(app_ir)`
5. `_generate_alembic_from_ir(app_ir)`

### Fase 3: Eliminar PRODUCTION_MODE Checks
1. Remover todos los `if os.getenv("PRODUCTION_MODE")`
2. Usar generadores IR-based como única fuente

### Fase 4: Testing
1. Correr E2E sin PRODUCTION_MODE
2. Verificar que IR genera código correcto
3. Validar con ComplianceValidator

---

## Beneficios

| Antes | Después |
|-------|---------|
| Código hardcodeado duplicado | IR como única fuente |
| Difícil de mantener | Cambios en IR se propagan |
| Comportamiento diferente dev/prod | Comportamiento consistente |
| No testeable unitariamente | Cada generador testeable |

---

## Criterios de Éxito

- [x] Cero referencias a `PRODUCTION_MODE` en generadores ✅
- [x] Todos los archivos generados desde IR (PatternBank → fallback) ✅
- [ ] E2E pasa sin `PRODUCTION_MODE=true` (PENDIENTE TEST)
- [ ] ComplianceValidator >80% (PENDIENTE TEST)
- [ ] Unit tests para cada generador IR-based (OPCIONAL)

---

## Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `src/services/code_generation_service.py` | Remover 6 PRODUCTION_MODE checks |
| `src/cognitive/ir/application_ir.py` | Agregar metadata fields si faltan |
| `tests/unit/test_ir_generators.py` | Nuevos tests para generadores |

---

## Notas

- El IR ya tiene toda la información necesaria
- Los generadores hardcodeados son duplicación innecesaria
- La arquitectura IR-centric debe ser respetada en TODOS los modos

---

## Trabajo Completado (Nov 26, 2025)

### Cambios Realizados

1. **PRODUCTION_MODE checks eliminados** de `code_generation_service.py`
2. **Comentarios limpiados** - Referencias a PRODUCTION_MODE removidas
3. **Backup eliminado** - `code_generation_service.py.backup` removido
4. **Modelos LLM actualizados** - Ver [LLM_MODEL_STRATEGY.md](LLM_MODEL_STRATEGY.md)

### Verificación

```bash
# Buscar PRODUCTION_MODE en código (solo docs deben aparecer)
grep -r "PRODUCTION_MODE" src/ --include="*.py" | grep -v ".backup"
# Resultado esperado: 0 matches
```
