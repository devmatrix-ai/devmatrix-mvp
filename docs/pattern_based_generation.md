# Pattern-Based Code Generation

## 🎯 Objetivo

Migrar de **templates hardcodeados** a **patterns semánticos** en el pattern bank para:

1. ✅ **Flexibilidad**: Patterns se adaptan al contexto con LLM
2. ✅ **Evolución**: Patterns mejoran con el uso y feedback
3. ✅ **Búsqueda semántica**: Encuentra patterns similares automáticamente
4. ✅ **No hardcoding**: Elimina dependencia de templates en código

## 📋 Arquitectura

### Antes (Templates Hardcodeados)

```python
# code_generation_service.py
def _generate_dockerfile(self, spec_requirements) -> str:
    """Returns hardcoded Dockerfile string."""
    return '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
...'''
```

**Problemas**:
- ❌ Templates hardcodeados en el código
- ❌ No evolucionan con el uso
- ❌ Difícil de adaptar a contextos diferentes
- ❌ No aprovecha embeddings semánticos

### Después (Pattern Bank)

```python
# Paso 1: Poblar pattern bank (una sola vez)
python scripts/populate_template_patterns.py

# Paso 2: Generar usando patterns
from src.services.pattern_based_generation import PatternBasedGenerator

generator = PatternBasedGenerator(pattern_bank, llm_client)

dockerfile = await generator.generate_dockerfile(
    context=GenerationContext(
        project_name="ecommerce_api",
        python_version="3.11"
    )
)
```

**Beneficios**:
- ✅ Patterns searchables semánticamente
- ✅ LLM adapta patterns al contexto
- ✅ Patterns mejoran con feedback
- ✅ Fallback a generación desde cero si no hay pattern

## 🚀 Uso

### 1. Poblar Pattern Bank (Una Sola Vez)

```bash
# Migrar todos los templates hardcodeados al pattern bank
PYTHONPATH=/home/kwar/code/agentic-ai python scripts/populate_template_patterns.py
```

Esto crea patterns para:

**Infrastructure**:
- `Dockerfile`
- `docker-compose.yml`
- `prometheus.yml`
- Grafana configs
- `alembic.ini`
- `.env.example`
- `.gitignore`
- `pyproject.toml`

**Build**:
- `Makefile`
- `requirements.txt` (verified versions)

**Code**:
- `src/main.py` (FastAPI entrypoint)
- `alembic/env.py` (async migrations)
- `alembic/script.py.mako`
- `src/api/routes/metrics.py`

### 2. Generar Código con Patterns

#### Opción A: Usar métodos convenientes

```python
from src.services.pattern_based_generation import (
    PatternBasedGenerator,
    GenerationContext
)
from src.cognitive.patterns.pattern_bank import PatternBank
from src.llm.claude_client import ClaudeClient

# Setup
pattern_bank = PatternBank()
pattern_bank.connect()

llm_client = ClaudeClient(api_key="your-key")

generator = PatternBasedGenerator(
    pattern_bank=pattern_bank,
    llm_client=llm_client,
    use_llm_adaptation=True  # LLM adapta patterns (más flexible)
)

# Contexto del proyecto
context = GenerationContext(
    project_name="ecommerce_api",
    api_version="v1",
    python_version="3.11",
    database_url="postgresql+asyncpg://user:pass@localhost/db"
)

# Generar archivos específicos
dockerfile = await generator.generate_dockerfile(context)
docker_compose = await generator.generate_docker_compose(context)
requirements = await generator.generate_requirements_txt(context)
main_py = await generator.generate_main_py(context)
makefile = await generator.generate_makefile(context)
```

#### Opción B: Usar método genérico

```python
# Búsqueda semántica flexible
code = await generator.generate_from_pattern(
    purpose="Generate production-ready Dockerfile for FastAPI application",
    context=context,
    domain="infrastructure",
    fallback_to_llm=True  # Si no hay pattern, generar desde cero
)
```

#### Opción C: Sin adaptación LLM (más rápido)

```python
# Solo sustitución de placeholders (sin LLM)
generator = PatternBasedGenerator(
    pattern_bank=pattern_bank,
    llm_client=llm_client,
    use_llm_adaptation=False  # Solo reemplaza {{placeholders}}
)

dockerfile = await generator.generate_dockerfile(context)
# Reemplaza {{project_name}} → "ecommerce_api"
# Reemplaza {{python_version}} → "3.11"
```

### 3. Integración con Code Generation Service

```python
# code_generation_service.py

class CodeGenerationService:
    def __init__(self, pattern_bank, llm_client, ...):
        self.pattern_generator = PatternBasedGenerator(
            pattern_bank=pattern_bank,
            llm_client=llm_client
        )

    async def generate_files(self, spec_requirements):
        """Generate files using pattern bank instead of hardcoded templates."""

        context = GenerationContext(
            project_name=spec_requirements["project_name"],
            api_version=spec_requirements.get("api_version", "v1"),
            python_version="3.11"
        )

        files = {}

        # Infrastructure
        files["Dockerfile"] = await self.pattern_generator.generate_dockerfile(context)
        files["docker/docker-compose.yml"] = await self.pattern_generator.generate_docker_compose(context)
        files["requirements.txt"] = await self.pattern_generator.generate_requirements_txt(context)
        files["Makefile"] = await self.pattern_generator.generate_makefile(context)
        files["alembic.ini"] = await self.pattern_generator.generate_alembic_ini(context)

        # Code
        files["src/main.py"] = await self.pattern_generator.generate_main_py(context)
        files["src/api/routes/metrics.py"] = await self.pattern_generator.generate_metrics_route(context)

        # Config
        files["docker/prometheus.yml"] = await self.pattern_generator.generate_prometheus_config(context)

        return files
```

## 🔄 Cómo Funciona

### Proceso de Generación

```
1. Búsqueda Semántica
   ├─ Crear signature: SemanticTaskSignature(purpose="Generate Dockerfile...")
   ├─ Buscar patterns similares: pattern_bank.search_with_fallback()
   └─ Ranking: similarity + success_rate + usage_count

2. Adaptación al Contexto
   ├─ Si use_llm_adaptation=True:
   │  └─ LLM adapta pattern con contexto específico
   └─ Si use_llm_adaptation=False:
      └─ Sustitución simple de {{placeholders}}

3. Fallback (si no hay pattern)
   ├─ Si fallback_to_llm=True:
   │  └─ LLM genera desde cero con instrucciones
   └─ Si fallback_to_llm=False:
      └─ Lanza error
```

### Ejemplo de Búsqueda

```python
# Usuario pide: "Generate Dockerfile for FastAPI"

# 1. Signature creado
signature = SemanticTaskSignature(
    purpose="Generate production-ready Dockerfile for FastAPI application",
    intent="create",
    inputs={"framework": "FastAPI", "python_version": "3.11"},
    outputs={"file": "Dockerfile"},
    domain="infrastructure"
)

# 2. Búsqueda semántica en pattern bank
patterns = pattern_bank.search_with_fallback(signature, top_k=3)

# 3. Resultado
# [
#   StoredPattern(
#       purpose="Generate production-ready Dockerfile for FastAPI application",
#       similarity_score=0.98,
#       code="FROM python:{{python_version}}-slim\n...",
#       success_rate=0.98
#   )
# ]

# 4. Adaptación con LLM
# LLM recibe:
# - Pattern code: "FROM python:{{python_version}}-slim\n..."
# - Context: {"python_version": "3.11", "project_name": "ecommerce_api"}
# - Instructions: "Replace placeholders and adapt"

# 5. Output
# FROM python:3.11-slim
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install -r requirements.txt
# ...
```

## 📊 Comparación

| Aspecto | Templates Hardcodeados | Pattern Bank |
|---------|------------------------|--------------|
| **Flexibilidad** | ❌ Rígido | ✅ Adaptable al contexto |
| **Evolución** | ❌ Estático | ✅ Mejora con uso/feedback |
| **Búsqueda** | ❌ Manual | ✅ Semántica automática |
| **Mantenimiento** | ❌ Editar código fuente | ✅ Actualizar patterns |
| **Escalabilidad** | ❌ Difícil agregar templates | ✅ Fácil agregar patterns |
| **Personalización** | ❌ Limitada | ✅ LLM adapta a necesidades |

## 🎨 Casos de Uso

### 1. Proyecto Estándar

```python
context = GenerationContext(project_name="standard_api")
dockerfile = await generator.generate_dockerfile(context)
# → Usa pattern base sin modificaciones
```

### 2. Proyecto Custom

```python
context = GenerationContext(
    project_name="ml_api",
    python_version="3.11",
    additional_context={
        "requires_cuda": True,
        "ml_framework": "pytorch"
    }
)

dockerfile = await generator.generate_dockerfile(context)
# → LLM adapta pattern para incluir CUDA y PyTorch
```

### 3. Sin Pattern Disponible

```python
code = await generator.generate_from_pattern(
    purpose="Generate Kubernetes Helm chart for FastAPI",
    context=context,
    fallback_to_llm=True
)
# → No hay pattern para Helm → LLM genera desde cero
```

## 🔧 Configuración Avanzada

### Umbral de Similaridad

```python
# Búsqueda con umbral bajo (más resultados)
patterns = pattern_bank.search_patterns(
    signature,
    similarity_threshold=0.50  # Default: 0.48
)

# Búsqueda solo production-ready
patterns = pattern_bank.hybrid_search(
    signature,
    production_ready=True,  # Solo patterns con test coverage > 80%
    domain="infrastructure"
)
```

### Modo Rápido (Sin LLM)

```python
# Para desarrollo rápido: solo sustitución de placeholders
generator = PatternBasedGenerator(
    pattern_bank=pattern_bank,
    llm_client=llm_client,
    use_llm_adaptation=False  # ⚡ Más rápido
)
```

## 📈 Métricas del Pattern Bank

```python
# Ver estadísticas
metrics = pattern_bank.get_pattern_metrics()

print(f"Total patterns: {metrics['total_patterns']}")
print(f"Avg success rate: {metrics['avg_success_rate']:.2%}")
print(f"Most used: {metrics['most_used_patterns']}")

# Output:
# Total patterns: 15
# Avg success rate: 97.33%
# Most used: [
#   {"pattern_id": "abc-123", "purpose": "Generate Dockerfile", "usage_count": 42},
#   ...
# ]
```

## 🚀 Migración Gradual

### Fase 1: Poblar Patterns (Completado)
```bash
python scripts/populate_template_patterns.py
```

### Fase 2: Usar Patterns en Generación (En Curso)
```python
# Modificar code_generation_service.py para usar pattern_generator
# En lugar de métodos _generate_*() hardcodeados
```

### Fase 3: Deprecar Templates Hardcodeados
```python
# Marcar métodos _generate_*() como deprecated
# Migrar completamente a pattern bank
```

### Fase 4: Feedback Loop
```python
# Actualizar patterns basado en:
# - Success rate de generaciones
# - Feedback de usuarios
# - Métricas de ejecución
```

## 🎯 Próximos Pasos

1. ✅ Script para poblar patterns: `populate_template_patterns.py`
2. ✅ Clase `PatternBasedGenerator` con búsqueda semántica
3. 🔄 Integrar en `CodeGenerationService`
4. 🔄 Testing E2E con patterns
5. 🔄 Feedback loop para mejorar patterns
6. 🔄 Deprecar templates hardcodeados

## 💡 Notas Importantes

- **Placeholders**: Usar `{{variable}}` en patterns (doble llave)
- **Similaridad**: Threshold 0.48 funciona bien (ajustar según necesidad)
- **Fallback**: Siempre habilitar `fallback_to_llm=True` en producción
- **Production Patterns**: Marcar con `production_ready=True` y metadata completa
- **Versionado**: Patterns evolucionan, no usar control de versiones explícito

## 🔗 Referencias

- [Pattern Bank](../src/cognitive/patterns/pattern_bank.py)
- [Pattern Based Generation](../src/services/pattern_based_generation.py)
- [Populate Script](../scripts/populate_template_patterns.py)
- [Code Generation Service](../src/services/code_generation_service.py)
