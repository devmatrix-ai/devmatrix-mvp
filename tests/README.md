# Testing Guide - Agentic AI RAG System

Guía completa para ejecutar tests del sistema RAG (Retrieval-Augmented Generation).

## Tabla de Contenidos

- [Estructura de Tests](#estructura-de-tests)
- [Requisitos](#requisitos)
- [Tests Unitarios](#tests-unitarios)
- [Tests de Integración E2E](#tests-de-integración-e2e)
- [Tests de Performance](#tests-de-performance)
- [Coverage](#coverage)
- [CI/CD](#cicd)

## Estructura de Tests

```
tests/
├── unit/                    # Tests unitarios con mocks
│   ├── agents/             # Tests de agentes
│   └── rag/                # Tests de componentes RAG
├── integration/            # Tests de integración E2E
│   └── rag/               # Tests E2E del sistema RAG
├── performance/            # Tests de performance y benchmarks
│   └── test_rag_performance.py
└── README.md              # Esta guía
```

## Requisitos

### Requisitos Básicos
```bash
# Python 3.10+
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
```

### Requisitos para Tests E2E
Los tests E2E requieren ChromaDB corriendo:

```bash
# Opción 1: Docker Compose (recomendado)
docker-compose up chromadb -d

# Opción 2: Docker directo
docker run -d -p 8000:8000 chromadb/chroma:latest

# Verificar que ChromaDB está corriendo
curl http://localhost:8000/api/v1/heartbeat
```

**Nota**: Los tests E2E se saltan automáticamente si ChromaDB no está disponible (usando `pytest.skip`).

## Tests Unitarios

Tests con mocks, no requieren servicios externos.

### Ejecutar Todos los Tests Unitarios
```bash
# Todos los tests unitarios
pytest tests/unit/ -v

# Tests de agentes
pytest tests/unit/agents/ -v

# Tests específicos de RAG con integración de ImplementationAgent
pytest tests/unit/agents/test_implementation_agent_rag.py -v
```

### Tests Disponibles

#### Tests de ImplementationAgent con RAG
```bash
pytest tests/unit/agents/test_implementation_agent_rag.py -v

# Cobertura:
# ✓ Inicialización RAG (enabled/disabled)
# ✓ Generación de código con contexto RAG
# ✓ Generación sin resultados RAG
# ✓ Grabación de code approval
# ✓ Inferencia de lenguajes
# ✓ Manejo de errores
```

**Características**:
- 26 tests unitarios
- Cobertura completa de flujos RAG
- Mocks para todos los componentes
- Tests de error handling

## Tests de Integración E2E

Tests end-to-end con ChromaDB real.

### Ejecutar Tests E2E

```bash
# 1. Asegurar que ChromaDB está corriendo
docker-compose up chromadb -d

# 2. Ejecutar tests E2E
pytest tests/integration/rag/test_rag_e2e.py -v

# 3. Con output detallado
pytest tests/integration/rag/test_rag_e2e.py -v -s

# 4. Test específico
pytest tests/integration/rag/test_rag_e2e.py::TestCompleteRAGPipeline::test_indexing_and_retrieval -v
```

### Tests Disponibles (14 tests)

#### TestCompleteRAGPipeline
Tests del pipeline completo:

1. **test_indexing_and_retrieval**: Indexado básico y recuperación
   - Indexa código de autenticación
   - Recupera ejemplos similares
   - Verifica similarity scores

2. **test_retrieval_context_building**: Retrieval + Context Building
   - Recupera ejemplos relevantes
   - Construye contexto formateado
   - Verifica inclusión de código esperado

3. **test_feedback_loop_and_reindexing**: Feedback Loop
   - Registra approval de código
   - Auto-indexa código aprobado
   - Verifica que sea recuperable

4. **test_mmr_diversity**: MMR (Maximal Marginal Relevance)
   - Indexa múltiples funciones similares
   - Verifica diversidad en resultados
   - Valida que MMR evita redundancia

5. **test_metadata_filtering**: Filtrado por Metadata
   - Indexa códigos con diferentes proyectos
   - Filtra por project_id
   - Verifica aislamiento de resultados

6. **test_no_results_scenario**: Manejo de Sin Resultados
   - Query con filtros que no matchean
   - Verifica lista vacía (no error)

7. **test_approved_code_boost**: Boost de Código Aprobado
   - Indexa código aprobado y no aprobado
   - Usa estrategia HYBRID
   - Verifica que aprobados tienen prioridad

#### TestEdgeCases
Tests de casos extremos:

8. **test_empty_code_indexing**: Código vacío
   - Debe lanzar ValueError

9. **test_very_long_code**: Código muy largo (1000+ líneas)
   - Debe indexarse correctamente

10. **test_special_characters_in_code**: Unicode y caracteres especiales
    - Emojis, chino, etc.
    - Debe manejarse sin errores

11. **test_retrieval_with_invalid_top_k**: Validación de parámetros
    - top_k=0 o negativo debe fallar

12. **test_health_check**: Health Check
    - Vector store debe reportar healthy

#### TestPerformanceBasics
Tests básicos de performance:

13. **test_batch_indexing**: Indexado en lote
    - Indexa 50 códigos
    - Debe completar en < 10 segundos

14. **test_retrieval_speed**: Velocidad de retrieval
    - 10 retrievals consecutivos
    - Debe completar en < 5 segundos

### Output Esperado

#### Ejemplo de Ejecución Exitosa
```bash
$ pytest tests/integration/rag/test_rag_e2e.py -v

tests/integration/rag/test_rag_e2e.py::TestCompleteRAGPipeline::test_indexing_and_retrieval PASSED
tests/integration/rag/test_rag_e2e.py::TestCompleteRAGPipeline::test_retrieval_context_building PASSED
...
================================ 14 passed in 12.34s ================================
```

#### Ejemplo Sin ChromaDB
```bash
$ pytest tests/integration/rag/test_rag_e2e.py -v

tests/integration/rag/test_rag_e2e.py::... SKIPPED (ChromaDB not available: ...)
...
================================ 14 skipped in 0.12s ================================
```

## Tests de Performance

Benchmarks y mediciones de performance con mocks (no requieren ChromaDB).

### Ejecutar Tests de Performance

```bash
# Todos los tests de performance
pytest tests/performance/test_rag_performance.py -v -s

# Test específico
pytest tests/performance/test_rag_performance.py::TestEmbeddingPerformance -v -s

# Sin logs detallados
pytest tests/performance/test_rag_performance.py -v
```

### Tests Disponibles (16 tests)

#### TestEmbeddingPerformance
Medición de velocidad de embeddings:

1. **test_single_embedding_speed**: Embedding individual
   - Objetivo: < 500ms
   - Resultado típico: ~220ms

2. **test_batch_embedding_speed**: Batch de 100 códigos
   - Objetivo: < 5 segundos
   - Resultado típico: ~5000 codes/sec

3. **test_embedding_consistency**: Consistencia
   - Mismo código debe producir mismo embedding

4. **test_large_batch_performance**: Batch grande (500 códigos)
   - Objetivo: < 20 segundos
   - Resultado típico: ~8000 codes/sec

#### TestRetrievalPerformance
Performance de retrieval (con mocks):

5. **test_retrieval_speed_basic**: Retrieval básico
   - Objetivo: < 1 segundo
   - Mide tiempo de retrieval con top_k=5

6. **test_batch_retrieval_performance**: 20 retrievals
   - Objetivo: < 5 segundos
   - Mide throughput de queries

7. **test_mmr_algorithm_performance**: MMR
   - Objetivo: < 2 segundos
   - MMR tiene overhead adicional

8. **test_cache_performance_impact**: Cache hit/miss
   - Mide speedup del cache
   - Compara primera vs segunda query

#### TestContextBuildingPerformance
Performance de context building:

9. **test_simple_template_speed**: Template SIMPLE
   - Objetivo: < 100ms
   - Resultado típico: ~0.1ms

10. **test_detailed_template_speed**: Template DETAILED
    - Objetivo: < 200ms
    - Resultado típico: ~0.1ms

11. **test_structured_template_speed**: Template STRUCTURED
    - Objetivo: < 200ms
    - Resultado típico: ~0.1ms

12. **test_large_context_performance**: 50 resultados grandes
    - Objetivo: < 1 segundo
    - ~50KB de contexto

13. **test_truncation_performance**: Truncación
    - Compara con/sin truncación
    - Mide overhead de truncado

#### TestScalingBehavior
Comportamiento con diferentes tamaños:

14. **test_retrieval_scaling**: Escalado
    - Mide con 100, 500, 1000, 5000 ejemplos
    - Verifica escalado sub-lineal

#### TestMemoryUsage
Eficiencia de memoria:

15. **test_embedding_memory**: Memory footprint de embedding
    - Objetivo: < 10KB por embedding
    - 384 dimensiones ~3KB

16. **test_context_memory_efficiency**: Memory de contexto
    - Objetivo: < 100KB para 10 resultados

### Output de Performance

```bash
$ pytest tests/performance/test_rag_performance.py -v -s

tests/performance/test_rag_performance.py::TestEmbeddingPerformance::test_single_embedding_speed
Single embedding generated in 214.8ms
PASSED

tests/performance/test_rag_performance.py::TestEmbeddingPerformance::test_batch_embedding_speed
Generated 100 embeddings in 0.02s (5225.2 codes/sec)
PASSED

...

================================ 16 passed in 13.84s ================================
```

## Coverage

Generar reporte de coverage:

```bash
# Generar coverage HTML
pytest tests/ --cov=src/rag --cov-report=html

# Ver reporte
firefox htmlcov/index.html

# Coverage solo RAG
pytest tests/unit/agents/test_implementation_agent_rag.py tests/integration/rag/ tests/performance/ --cov=src/rag --cov-report=term-missing
```

### Coverage Actual (RAG Components)

- **src/rag/retriever.py**: 78%
- **src/rag/context_builder.py**: 73%
- **src/rag/embeddings.py**: 58%
- **src/rag/feedback_service.py**: 36%
- **src/rag/vector_store.py**: 14% (requiere ChromaDB real para full coverage)

## CI/CD

### GitHub Actions

Los tests se ejecutan automáticamente en CI/CD:

```yaml
# .github/workflows/test.yml
test:
  services:
    chromadb:
      image: chromadb/chroma:latest
      ports:
        - 8000:8000

  steps:
    - name: Run Unit Tests
      run: pytest tests/unit/ -v

    - name: Run E2E Tests
      run: pytest tests/integration/ -v
      env:
        CHROMADB_HOST: chromadb
        CHROMADB_PORT: 8000

    - name: Run Performance Tests
      run: pytest tests/performance/ -v
```

### Pre-commit Hooks

Ejecutar tests antes de commit:

```bash
# Instalar pre-commit
pip install pre-commit
pre-commit install

# Los tests unitarios corren automáticamente en cada commit
```

## Troubleshooting

### ChromaDB no está disponible

**Error**: `14 skipped (ChromaDB not available)`

**Solución**:
```bash
# Verificar docker
docker ps | grep chroma

# Reiniciar ChromaDB
docker-compose restart chromadb

# Verificar puerto
curl http://localhost:8000/api/v1/heartbeat
```

### Tests lentos

**Problema**: Tests de embedding muy lentos

**Solución**:
- Los embeddings usan el modelo `all-MiniLM-L6-v2`
- Primera ejecución descarga el modelo (~80MB)
- Ejecuciones subsecuentes usan cache
- Para tests más rápidos: usar mocks (ver tests de performance)

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solución**:
```bash
# Ejecutar desde el root del proyecto
cd /home/kwar/code/agentic-ai

# O configurar PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/home/kwar/code/agentic-ai"
```

## Contribuir

Al agregar nuevos tests:

1. **Tests Unitarios**: Agregar en `tests/unit/`
   - Usar mocks para dependencias externas
   - Verificar error handling

2. **Tests E2E**: Agregar en `tests/integration/`
   - Usar fixtures con ChromaDB real
   - Implementar skip condicional si falta ChromaDB

3. **Tests de Performance**: Agregar en `tests/performance/`
   - Establecer umbrales realistas
   - Incluir print de métricas para análisis

4. **Documentación**: Actualizar este README con nuevos tests

## Recursos

- **Pytest Docs**: https://docs.pytest.org/
- **ChromaDB Docs**: https://docs.trychroma.com/
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Última actualización**: FASE 7 - Testing Comprehensivo (2025)
