# 07_Learning_Layer_and_Promotion.md
**DevMatrix – Learning Layer & Pattern Promotion Architecture**

---

## 1. Overview

Este documento describe la **Learning Layer** de DevMatrix: el conjunto de pipelines y servicios que permiten que el sistema **aprenda de sus propias ejecuciones** y mejore con el tiempo.

La Learning Layer actúa **en paralelo** al pipeline cognitivo principal (Spec → ApplicationIR → Graphs → Tasks → Code → Validation → Repair) y se alimenta de:

- Resultados de generación (éxitos y fallos)
- Métricas de validación y reparación
- Código generado y reparado
- Feedback de RAG (fragmentos de código aprobados)
- Patrones candidatos para promoción

El objetivo es transformar DevMatrix en un motor **self-improving**, donde:

> Cada nueva generación de aplicaciones aporta datos que mejoran  
> las decisiones futuras de selección de patrones, reparación y retrieval.

---

## 2. Componentes principales de la Learning Layer

La Learning Layer se compone de tres sub-pipelines principales:

1. **Pattern Promotion Pipeline (Milestone 4)**
2. **Error Pattern Feedback Loop**
3. **RAG Feedback Learning Loop**

Estos pipelines no son MGE en sí mismos, sino capas de **feedback y optimización** que rodean al motor de generación.

---

## 3. Pattern Promotion Pipeline

**Ubicación conceptual:**
- Módulo: `cognitive/patterns/pattern_feedback_integration.py`
- Integración: `CodeGenerationService` (flags: `enable_feedback_loop`, `enable_pattern_promotion`, `enable_dag_sync`)

### 3.1. Propósito

El Pattern Promotion Pipeline existe para:

- Identificar **patrones de código exitosos** (templates, snippets, combinaciones de patterns)
- Evaluar su calidad con métricas objetivas
- Promover esos patrones a **“production-ready patterns”** dentro de `PatternBank`
- Desactivar o penalizar patrones problemáticos

En otras palabras:

> Transformar ejecuciones exitosas en **nuevos patrones oficiales** reutilizables.

### 3.2. Modelo de datos

Estados típicos de promoción (`PromotionStatus`):

- `PENDING` – candidato recién registrado
- `ANALYZING` – en proceso de evaluación
- `DUAL_VALIDATION` – verificando tests + métricas
- `APPROVED` – candidato aceptado
- `REJECTED` – candidato descartado
- `PROMOTED` – patrón incorporado a PatternBank

Cada candidato contiene:

- Referencias al patrón base
- Contexto de uso (spec/app, tipo de requirement)
- Métricas de:
  - Test pass rate
  - Semantic compliance inicial/final
  - Cantidad de reparaciones necesarias
  - Tiempos de ejecución por fase
  - Tasa de errores secundarios

### 3.3. Flujo

1. **Registro de candidato**
   - Trigger: Phase 6/7 completada con alta compliance (ej. ≥ 99.5%).
   - Se registra un `PatternCandidate` con:
     - Código generado (fragmento relevante)
     - Métricas de validación
     - Metadatos (IR, requirement, categoría, etc.)

2. **Evaluación de calidad**
   - Se evalúan:
     - Tests (unit, integration)
     - Compliance semántica
     - Compatibilidad con la arquitectura target
     - Historial de reparaciones

3. **Validación dual**
   - Opcional (modo “strict”):
     - Validación automatizada + validación manual (en entornos internos).
   - Una vez pasa dual validation, el patrón se marca como `APPROVED`.

4. **Promoción**
   - El patrón pasa a `PROMOTED`.
   - Se serializa en `PatternBank` con:
     - Nueva versión
     - Metadata de contexto (para matching futuro)
   - `CodeGenerationService` pasa a **preferir** patrones promovidos en contextos similares.

5. **DAG Sync (opcional)**
   - Actualiza la información de dependencias, tareas y relaciones para reflejar el nuevo patrón dentro del `TaskGraph`.

---

## 4. Error Pattern Feedback Loop

**Ubicación conceptual:**
- Módulos:  
  - `services/error_pattern_store.py`  
  - `services/error_pattern_analyzer.py`

### 4.1. Propósito

El Error Pattern Feedback Loop tiene tres objetivos:

1. **Registrar errores de generación y validación** de forma rica y estructurada.
2. **Detectar patrones recurrentes de fallo** (mis mismos errores apareciendo en múltiples apps/specs).
3. **Guiar ajustes de heurísticas, thresholds y selección de patrones** para prevenir esos errores en el futuro.

### 4.2. Recolección de errores

En cada punto crítico del pipeline (especialmente en:

- Phase 6 (Code Generation)
- Phase 6.5 (Code Repair)
- Phase 7 (Validation)

se registran:

- Tipo de error (sintaxis, validación, schema mismatch, endpoint missing, etc.)
- Tarea asociada (TaskID, wave, requirement vinculado)
- Patrón utilizado (PatternID, categoría)
- Código antes/después de reparación (cuando aplique)
- IR y contexto (ApplicationIR recortado / referenciado)

Esto se almacena en:

- Neo4j (grafos de errores y su contexto)
- Qdrant / Vector DB (embeddings de código y errores, vía GraphCodeBERT)

### 4.3. Análisis (ErrorPatternAnalyzer)

El analizador:

- Agrupa errores similares (clustering por embedding + metadata)
- Detecta:
  - tareas problemáticas recurrentes
  - patrones con alta tasa de fallo
  - combinaciones IR + patrón que suelen requerir repair
- Calcula:
  - tasa de recurrencia
  - impacto por categoría
  - evolución en el tiempo (¿van bajando estos errores?)

### 4.4. Uso de resultados

Los resultados de este análisis se utilizan para:

- Penalizar ciertos patrones (reduciendo su prioridad de selección)
- Ajustar heurísticas:
  - thresholds de complejidad
  - número máximo de retry
  - activación preventiva de ciertos repairs
- Generar tickets o reportes para mejorar patrones base o templates
- Alimentar el Pattern Promotion Pipeline (promover alternativas más estables)

---

## 5. RAG Feedback Learning Loop

**Ubicación conceptual:**
- Módulo: `rag/feedback_service.py` + integración con VectorStore

### 5.1. Propósito

Este loop se encarga de aprender de **fragmentos de código generados que se consideran “buenos ejemplos”** (pasaron validación, reparaciones mínimas, alta estabilidad).

La idea es:

> Cualquier fragmento de código “validado” debe poder servir de ejemplo  
> para futuras generaciones en contextos similares.

### 5.2. Flujo

1. **Registro de feedback positivo**
   - Cuando una app llega a 100% compliance / tests green:
     - Se seleccionan fragmentos relevantes:
       - Patterns adaptados
       - Snippets de rutas
       - Servicios clave
       - Tests representativos
     - Se crean `FeedbackEntry` con:
       - Código
       - Contexto (spec, IR, requirement)
       - Metadata (tipo de componente, framework)

2. **Indexación**
   - Se compute embeddings de código (GraphCodeBERT u otro modelo).
   - Se guarda en VectorStore con:
     - ID, embedding, metadata.

3. **Uso en generación**
   - En fases de codegen que requieren ejemplos:
     - Se consulta el VectorStore según:
       - tipo de requirement
       - categoría del patrón
       - contexto IR
     - Se traen snippets previos como referencia antes de llamar al LLM.
   - Esto reduce:
     - dependencia del LLM para inventar estructuras
     - riesgo de errores
     - longitud de prompts

---

## 6. Integración con el Pipeline Cognitivo Principal

### 6.1. Hooks de entrada a la Learning Layer

Los hooks más relevantes:

- **Al final de Phase 6/6.5/7**:
  - registrar candidatos de patrón (Pattern Promotion)
  - registrar errores (Error Pattern Store)
  - registrar snippets exitosos (RAG Feedback)

- **En arranque de Phase 6 (CodeGenerationService)**:
  - utilizar:
    - patrones promovidos
    - insights de ErrorPatternAnalyzer
    - ejemplos de RAG Feedback

### 6.2. Ciclo de aprendizaje

1. Run del pipeline principal:
   - Especificación → App → Validación → Métricas
2. Learning Layer registra:
   - éxitos,
   - errores,
   - candidatos
3. Jobs periódicos (cron/CLI `devmatrix learn`):
   - analizan y cierran el ciclo:
     - promoción de patrones
     - actualización de pesos/heurísticas
     - actualización de índices de RAG
4. Próximo run:
   - se beneficia de las decisiones mejoradas.

---

## 7. Métricas de Éxito de la Learning Layer

Para evaluar si la Learning Layer aporta valor real, algunas métricas clave:

1. **Reducción de errores recurrentes**
   - Nº de apariciones de una clase de error antes/después.
2. **Disminución de dependencia del CodeRepair**
   - Nº medio de reparaciones por app generada.
3. **Mejora de compliance inicial**
   - Compliance inicial (antes de repair) a lo largo del tiempo.
4. **Reducción de latencia y coste**
   - Tiempo medio por generación.
   - Nº de llamadas al LLM por app.
5. **Tasa de adopción de patrones promovidos**
   - Porcentaje de generaciones que usan patrones “promoted”.
6. **Estabilidad entre ejecuciones**
   - Determinismo: variación entre múltiples runs de la misma spec.

---

## 8. Roadmap para pasar de “infra lista” a “learning real”

### 8.1. Pattern Promotion

- Activar promociones reales:
  - Implementar validación dual (automática + opcional manual).
  - Definir umbrales claros de promoción.
- Ajustar `CodeGenerationService` para priorizar patrones promovidos.
- Añadir métricas de tracking de patrones promovidos.

### 8.2. Error Pattern Loop

- Conectar todos los puntos de error críticos al `ErrorPatternStore`.
- Ejecutar el `ErrorPatternAnalyzer` en un job recurrente.
- Traducir output del análisis en:
  - ajustes de prioridad
  - ajustes de thresholds
  - activación de repairs preventivos.

### 8.3. RAG Feedback

- Establecer criterios de selección de snippets “dignos de feedback”.
- Conectar `FeedbackService` a Phase 7/8.
- Integrar un paso de consulta a VectorStore en CodeGenerationService.

---

## 9. Valor Estratégico de la Learning Layer

Con la Learning Layer completamente activa, DevMatrix no solo genera aplicaciones:

- Aprende qué funciona y qué no.
- Mejora la selección de patrones con datos reales.
- Reduce errores y tiempo de corrección.
- Se vuelve más determinista y estable con el tiempo.
- Construye un “conocimiento interno” de cómo se programa bien en ciertos dominios.

Esto es exactamente lo que compañías como **Anthropic, Microsoft, OpenAI, AWS, Google** necesitan para:

- completar su historia de “Enterprise Agents”
- reducir coste de código generado
- mejorar estabilidad y reproducibilidad
- diferenciarse de sistemas basados únicamente en prompts.

---

## 10. Conclusión

La Learning Layer convierte a DevMatrix en un motor:

- **Self-improving**: cada ejecución deja al sistema un poco mejor.
- **Data-driven**: decisiones basadas en métricas reales, no solo en heurísticas fijas.
- **Extensible**: cada nuevo dominio/cliente aporta datos para el futuro.
- **Estratégicamente diferenciador**: difícil de replicar, valioso para adquisición.

Este documento formaliza:

- Qué componentes existen
- Cómo se integran
- Qué falta para “encenderlos” completamente
- Qué métricas definen el éxito

DevMatrix pasa de ser “solo un generador de aplicaciones” a una **fábrica de software cognitiva que aprende**.
