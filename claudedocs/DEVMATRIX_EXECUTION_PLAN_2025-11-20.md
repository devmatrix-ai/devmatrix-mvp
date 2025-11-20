# DevMatrix Execution Plan - simple_task_api.md

**Fecha**: 2025-11-20
**Spec**: `/home/kwar/code/agentic-ai/tests/e2e/test_specs/simple_task_api.md`
**Objetivo**: Ejecutar DevMatrix directamente para generar código de Task API

---

## 📋 Spec Overview

**Nombre**: Simple Task Management API
**Tipo**: RESTful CRUD API
**Complejidad**: Baja (ideal para primera ejecución)

**Requisitos**:
```
✅ CRUD operations (Create, Read, Update, Delete)
✅ Data Model: Task (id, title, description, completed, timestamps)
✅ 5 Endpoints: POST/GET/GET/:id/PUT/:id/DELETE/:id
✅ In-memory storage (no DB)
✅ Input validation
✅ Error handling
```

**Expectativa**: Framework FastAPI detectado → Código Python generado → Validación exitosa

---

## 🎯 Flujo de Ejecución

### Opción 1: Usar Test E2E Existente (RECOMENDADO)

**Archivo**: `tests/e2e/real_e2e_full_pipeline.py`
**Script**: `tests/e2e/run_e2e_test.sh`

**Ventajas**:
- ✅ Ya tiene todo el pipeline implementado
- ✅ Incluye todos los 5 stubs integrados
- ✅ Genera métricas y reportes automáticos
- ✅ Output directory organizado
- ✅ Error handling completo

**Comando**:
```bash
cd /home/kwar/code/agentic-ai

# Ejecutar test E2E con simple_task_api.md
PYTHONPATH=/home/kwar/code/agentic-ai python -m pytest tests/e2e/real_e2e_full_pipeline.py \
    --spec-file tests/e2e/test_specs/simple_task_api.md \
    -v -s
```

**Output Esperado**:
```
tests/e2e/generated_apps/simple_task_api_{timestamp}/
├── main.py              # FastAPI application
├── models.py            # Task model
├── routes.py            # CRUD endpoints
├── tests/              # Generated tests
└── requirements.txt     # Dependencies
```

### Opción 2: Script Directo Simplificado (Nuevo)

**Archivo**: `scripts/run_devmatrix_single_spec.py` (nuevo)

**Ventajas**:
- ✅ Más simple y directo
- ✅ Solo ejecuta el spec sin test framework
- ✅ Output más limpio

**Desventajas**:
- ❌ Requiere crear el script (15-30 min)
- ❌ Menos métricas y validación

---

## 🔧 Plan de Ejecución Detallado (Opción 1)

### Pre-requisitos

**1. Verificar Servicios Activos**:
```bash
# Neo4j
docker ps | grep neo4j

# Qdrant
curl -s http://localhost:6333/health | jq

# Output esperado:
# {"status":"ok","version":"..."}
```

**2. Verificar Variables de Entorno**:
```bash
# Verificar ANTHROPIC_API_KEY
printenv | grep ANTHROPIC_API_KEY

# Si no existe, configurar:
export ANTHROPIC_API_KEY="tu-api-key"
```

**3. Verificar Python Dependencies**:
```bash
pip list | grep -E "(anthropic|qdrant|neo4j|fastapi)"

# Instalar faltantes:
# pip install anthropic qdrant-client neo4j fastapi
```

### Paso 1: Preparar Entorno

```bash
cd /home/kwar/code/agentic-ai

# Limpiar outputs previos (opcional)
rm -rf tests/e2e/generated_apps/simple_task_api_*

# Verificar spec existe
cat tests/e2e/test_specs/simple_task_api.md | head -20
```

### Paso 2: Ejecutar DevMatrix

**Comando Completo**:
```bash
# Activar modo verbose para ver todo el flujo
PYTHONPATH=/home/kwar/code/agentic-ai \
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
python tests/e2e/real_e2e_full_pipeline.py \
    tests/e2e/test_specs/simple_task_api.md

# O usar pytest para mejor output:
pytest tests/e2e/real_e2e_full_pipeline.py \
    -k "test_simple_task" \
    -v -s --tb=short
```

### Paso 3: Monitorear Ejecución

**Logs a Observar**:
```bash
# En otra terminal, monitorear logs
tail -f logs/devmatrix_*.log

# O seguir el output en tiempo real
```

**Fases Esperadas** (con stubs):
```
1. ✅ Spec Ingestion
   → SpecParser extrae requirements, entities, endpoints
   → Output: SpecRequirements object

2. ✅ Pattern Classification (STUB #1)
   → PatternClassifier clasifica como "api_handlers"
   → Output: category="api_handlers", confidence=0.85

3. ✅ File Type Detection (STUB #2)
   → FileTypeDetector detecta FastAPI framework
   → Output: file_type=PYTHON, framework="FastAPI", confidence=0.95

4. ✅ Multi-Pass Planning
   → MultiPassPlanner crea DAG de tareas
   → Output: [models → routes → tests]

5. ✅ Prompt Strategy (STUB #3)
   → PythonPromptStrategy genera prompt FastAPI
   → Output: Prompt con type hints, async, Pydantic

6. ✅ Code Generation
   → LLM (Claude/DeepSeek) genera código
   → Output: main.py, models.py, routes.py

7. ✅ Validation (STUB #4)
   → PythonValidationStrategy valida sintaxis, types, LOC
   → Output: is_valid=True o error details

8. ✅ Pattern Feedback (STUB #5)
   → PatternFeedbackIntegration evalúa calidad
   → Output: promotion_score, almacenado en Qdrant+Neo4j
```

### Paso 4: Verificar Resultados

**A. Código Generado**:
```bash
# Listar archivos generados
ls -lh tests/e2e/generated_apps/simple_task_api_*/

# Ver código principal
cat tests/e2e/generated_apps/simple_task_api_*/main.py

# Verificar estructura
tree tests/e2e/generated_apps/simple_task_api_*/
```

**B. Pattern Storage (Qdrant)**:
```bash
# Verificar nuevo pattern en Qdrant
curl -s "http://localhost:6333/collections/semantic_patterns" | \
    jq '.result.points_count'

# Debería ser 30,127 (30,126 + 1 nuevo)
```

**C. Pattern Storage (Neo4j)**:
```bash
# Verificar nuevo pattern en Neo4j
docker exec devmatrix-neo4j cypher-shell -u neo4j -p password \
    "MATCH (p:Pattern) WHERE p.category = 'api_handlers'
     RETURN count(p) as api_patterns" 2>/dev/null | grep -E "^[0-9]+"
```

**D. Métricas**:
```bash
# Ver métricas generadas
ls -lh tests/e2e/metrics/

# Revisar JSON de métricas
cat tests/e2e/metrics/real_e2e_simple_task_api_*.json | jq
```

---

## 📊 Criterios de Éxito

### Nivel 1: Ejecución Básica
```
✅ Pipeline completa sin errores fatales
✅ Código generado en output directory
✅ Al menos 1 archivo .py creado
```

### Nivel 2: Calidad de Código
```
✅ Sintaxis Python válida (ast.parse pasa)
✅ Type hints presentes (>90%)
✅ Endpoints RESTful implementados
✅ CRUD operations funcionales
```

### Nivel 3: Integración Completa
```
✅ Pattern clasificado y almacenado en Qdrant
✅ Pattern almacenado en Neo4j con metadata
✅ Stubs ejecutados sin errores
✅ Métricas generadas y guardadas
```

### Nivel 4: Pattern Promotion
```
✅ Quality score calculado (>0.8 ideal)
✅ Pattern promovido a PatternBank
✅ Disponible para reuso futuro
```

---

## 🚨 Troubleshooting

### Error 1: "No module named 'anthropic'"
**Solución**:
```bash
pip install anthropic
```

### Error 2: "Qdrant connection refused"
**Solución**:
```bash
# Verificar Qdrant corriendo
docker ps | grep qdrant

# Si no está, iniciar:
docker-compose up -d qdrant
```

### Error 3: "Neo4j authentication failed"
**Solución**:
```bash
# Verificar credenciales
docker exec devmatrix-neo4j cypher-shell -u neo4j -p password "RETURN 1"
```

### Error 4: "ANTHROPIC_API_KEY not found"
**Solución**:
```bash
# Configurar en .env
echo "ANTHROPIC_API_KEY=tu-key" >> .env

# O exportar directamente
export ANTHROPIC_API_KEY="tu-key"
```

### Error 5: "ValidationStrategy retorna False"
**Diagnóstico**:
```
- Revisar error message en output
- Código probablemente tiene TODOs o syntax errors
- LLM generó código incompleto
```

**Solución**:
```
- Verificar prompt strategy generó instrucciones claras
- Re-ejecutar con --retry flag
- Revisar logs de LLM generation
```

### Error 6: "PatternFeedbackIntegration falló"
**Diagnóstico**:
```
- Qdrant o Neo4j no accesibles
- ClassificationResult incompatible
- Dual validator timeouts
```

**Solución**:
```bash
# Verificar conexiones
curl http://localhost:6333/health
docker exec devmatrix-neo4j cypher-shell -u neo4j -p password "RETURN 1"

# Revisar logs
grep "PatternFeedbackIntegration" logs/devmatrix_*.log
```

---

## 📝 Logs y Observabilidad

### Archivos de Log
```
logs/devmatrix_pipeline_{timestamp}.log      - Pipeline general
logs/code_generation_{timestamp}.log         - LLM generation
logs/pattern_classification_{timestamp}.log  - Classification
logs/validation_{timestamp}.log              - Validation errors
```

### Monitoreo en Tiempo Real
```bash
# Ver todos los logs relevantes
tail -f logs/*.log | grep -E "(ERROR|WARNING|SUCCESS|PATTERN)"

# Solo errores
tail -f logs/*.log | grep ERROR

# Solo stubs
tail -f logs/*.log | grep -E "(PatternClassifier|FileTypeDetector|PromptStrategy|ValidationStrategy|PatternFeedback)"
```

### Métricas Post-Ejecución
```bash
# Ver resumen de métricas
cat tests/e2e/metrics/real_e2e_simple_task_api_*.json | \
    jq '{
        success: .pipeline_success,
        duration: .total_duration_seconds,
        pattern_promoted: .pattern_promoted,
        quality_score: .quality_score
    }'
```

---

## 🎯 Comando Final Recomendado

```bash
cd /home/kwar/code/agentic-ai

# Verificar pre-requisitos
docker ps | grep -E "(neo4j|qdrant)"
printenv | grep ANTHROPIC_API_KEY

# Ejecutar DevMatrix con simple_task_api.md
PYTHONPATH=/home/kwar/code/agentic-ai \
python tests/e2e/real_e2e_full_pipeline.py \
    tests/e2e/test_specs/simple_task_api.md \
    2>&1 | tee devmatrix_execution_$(date +%Y%m%d_%H%M%S).log

# Resultado en:
# - Código: tests/e2e/generated_apps/simple_task_api_*/
# - Métricas: tests/e2e/metrics/real_e2e_simple_task_api_*.json
# - Log: devmatrix_execution_{timestamp}.log
```

**Duración estimada**: 2-5 minutos (dependiendo de LLM response time)

---

## 📄 Próximos Pasos Post-Ejecución

### Si Ejecución Exitosa ✅
```
1. Revisar código generado manualmente
2. Ejecutar tests generados (si existen)
3. Validar que todos los endpoints funcionan
4. Verificar pattern en Qdrant/Neo4j
5. Analizar métricas de calidad
6. Documentar lessons learned
```

### Si Ejecución Falló ❌
```
1. Revisar logs de error
2. Identificar en qué fase falló
3. Diagnosticar causa raíz
4. Aplicar troubleshooting apropiado
5. Re-ejecutar con fixes
6. Documentar issue y solución
```

### Validación de Stubs
```bash
# Verificar que todos los stubs fueron usados
grep -E "PatternClassifier|FileTypeDetector|PromptStrategy|ValidationStrategy|PatternFeedback" \
    devmatrix_execution_*.log | wc -l

# Debería mostrar múltiples líneas (uno por cada stub)
```

---

**Última actualización**: 2025-11-20
**Listo para ejecutar**: ✅ SÍ
**Siguiente acción**: Ejecutar comando final
