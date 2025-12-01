# Plan B: Usar Neo4j de Verdad

**Fecha**: 2025-12-01
**Estado**: PROPUESTA
**Prioridad**: Medium (post-MVP)

---

## 1. Diagnóstico Actual

### 1.1 Estado del Grafo

| Métrica | Valor |
|---------|-------|
| Total nodos | 48,916 |
| Total relaciones | 578,757 |
| Nodos aislados | 137 |
| Rels/nodo | 11.8 |

### 1.2 Composición

| Componente | Nodos | % | Conectado a PatternBank? |
|------------|-------|---|--------------------------|
| PatternBank (Pattern + taxonomy) | ~30,112 | 62% | ✅ Sí (giant component) |
| IR snapshots (~300 apps) | ~18,000 | 37% | ❌ No (subgrafos aislados) |
| Learning patterns | ~500 | 1% | ❌ No |

### 1.3 Uso Durante E2E Pipeline

| Operación | Queries | Impacto en generación |
|-----------|---------|----------------------|
| **READS** | 0 | ❌ No se consulta NADA |
| **WRITES** | ~8 | Solo persistencia histórica |

**Conclusión**: Neo4j es write-only. 48k nodos, 0 queries durante generación.

---

## 2. Propuesta de Valor

### ¿Por qué usar Neo4j de verdad?

| Caso de Uso | Sin Neo4j | Con Neo4j |
|-------------|-----------|-----------|
| **Cross-app learning** | Cada app aprende aislada | "Pattern X falla en apps con >5 entities" |
| **Pattern mining** | Manual/ad-hoc | Queries automáticas de correlación |
| **Debugging** | Logs + grep | "¿Qué patterns generaron este endpoint?" |
| **Similarity search** | Solo Qdrant (embeddings) | Graph traversal + embeddings |
| **Historical analysis** | No existe | "¿Cómo evolucionó el success rate de Pattern X?" |

### ROI Esperado

| Métrica | Actual | Target |
|---------|--------|--------|
| Cross-session error reduction | 20% | 40%+ |
| Pattern reuse rate | ~30% | 60%+ |
| Debugging time | Hours | Minutes |

---

## 3. Arquitectura Propuesta

### 3.1 Flujo Actual (Write-Only)

```
Spec → ApplicationIR → [WRITE] Neo4j (snapshot)
                     ↓
         PatternBank.search(Qdrant) → Generate → [WRITE] Neo4j (results)
```

### 3.2 Flujo Propuesto (Read+Write)

```
Spec → ApplicationIR → [READ] Neo4j: Similar IRs + their patterns
                     ↓
         [READ] Neo4j: Patterns que funcionaron para IRs similares
                     ↓
         PatternBank.search(Qdrant) + Graph-boosted ranking
                     ↓
         Generate → [WRITE] Neo4j (results + correlations)
```

---

## 4. Casos de Uso Concretos

### 4.1 Pre-Generation: Pattern Boosting

**Query**: Antes de generar, buscar patterns exitosos para IRs similares.

```cypher
// Encontrar apps similares por estructura
MATCH (current:ApplicationIR {app_id: $current_app_id})
MATCH (similar:ApplicationIR)
WHERE similar.entity_count = current.entity_count
  AND similar.endpoint_count >= current.endpoint_count - 2
  AND similar.endpoint_count <= current.endpoint_count + 2
  AND similar.app_id <> current.app_id

// Encontrar patterns que funcionaron en esas apps
MATCH (similar)-[:GENERATED_WITH]->(pattern:Pattern)
WHERE pattern.success_rate > 0.8

RETURN pattern.id, pattern.category, pattern.success_rate
ORDER BY pattern.success_rate DESC
LIMIT 10
```

**Integración**: `code_generation_service.py:_retrieve_production_patterns()`

### 4.2 Post-Generation: Correlation Tracking

**Query**: Después de smoke tests, correlacionar patterns con resultados.

```cypher
// Registrar correlación Pattern → Resultado
MATCH (app:ApplicationIR {app_id: $app_id})
MATCH (pattern:Pattern {id: $pattern_id})
MERGE (app)-[r:GENERATED_WITH]->(pattern)
SET r.success = $success,
    r.smoke_pass_rate = $smoke_pass_rate,
    r.timestamp = datetime()
```

**Integración**: `smoke_test_pattern_adapter.py`

### 4.3 Learning: Anti-Pattern Detection

**Query**: Detectar patterns que fallan consistentemente.

```cypher
// Patterns con bajo success rate across apps
MATCH (pattern:Pattern)<-[r:GENERATED_WITH]-(app:ApplicationIR)
WITH pattern, 
     count(r) as uses,
     avg(r.smoke_pass_rate) as avg_success
WHERE uses >= 5 AND avg_success < 0.7
RETURN pattern.id, pattern.category, uses, avg_success
ORDER BY avg_success ASC
```

**Integración**: `pattern_mining_service.py`

### 4.4 Debugging: Trace Generation

**Query**: ¿Qué patterns generaron este endpoint que falló?

```cypher
MATCH (endpoint:Endpoint {path: $path, method: $method})
MATCH (endpoint)<-[:HAS_ENDPOINT]-(api:APIModelIR)
MATCH (api)<-[:HAS_API_MODEL]-(app:ApplicationIR)
MATCH (app)-[r:GENERATED_WITH]->(pattern:Pattern)
WHERE r.success = false
RETURN pattern.id, pattern.category, r.error_type
```

---

## 5. Relaciones Nuevas a Crear

### 5.1 Esquema Propuesto

```cypher
// Pattern ↔ ApplicationIR (generación)
(:ApplicationIR)-[:GENERATED_WITH {
  success: boolean,
  smoke_pass_rate: float,
  timestamp: datetime,
  error_type: string?
}]->(:Pattern)

// Pattern ↔ IR elements (granular)
(:Pattern)-[:APPLIED_TO_ENDPOINT]->(:Endpoint)
(:Pattern)-[:APPLIED_TO_ENTITY]->(:Entity)

// Learning relationships
(:Pattern)-[:SUPERSEDES]->(:Pattern)  // Pattern evolution
(:GenerationAntiPattern)-[:DETECTED_IN]->(:ApplicationIR)
(:PositiveRepairPattern)-[:FIXED_IN]->(:ApplicationIR)
```

---

## 6. Plan de Implementación

### Phase 1: Foundation (1-2 días)

| Task | File | Descripción |
|------|------|-------------|
| 1.1 | `scripts/migrations/neo4j/013_generation_tracking.py` | Crear schema GENERATED_WITH |
| 1.2 | `src/cognitive/services/generation_graph_tracker.py` | Nuevo servicio para tracking |
| 1.3 | `src/services/code_generation_service.py` | Integrar tracker en generación |

### Phase 2: Pre-Generation Queries (2-3 días)

| Task | File | Descripción |
|------|------|-------------|
| 2.1 | `src/cognitive/services/similar_ir_finder.py` | Buscar IRs similares |
| 2.2 | `src/cognitive/services/pattern_booster.py` | Boost patterns por historial |
| 2.3 | `src/services/code_generation_service.py` | Integrar en `_retrieve_production_patterns()` |

### Phase 3: Post-Generation Correlation (1-2 días)

| Task | File | Descripción |
|------|------|-------------|
| 3.1 | `src/validation/smoke_test_pattern_adapter.py` | Registrar correlaciones |
| 3.2 | `src/cognitive/services/ir_code_correlator.py` | Extender para graph writes |

### Phase 4: Learning Queries (2-3 días)

| Task | File | Descripción |
|------|------|-------------|
| 4.1 | `src/cognitive/services/pattern_mining_service.py` | Queries cross-app |
| 4.2 | `src/learning/negative_pattern_store.py` | Leer anti-patterns de Neo4j |
| 4.3 | `src/services/pattern_aware_generator.py` | Aplicar learnings en generación |

---

## 7. Queries de Validación

### 7.1 Verificar Conectividad PatternBank ↔ IR

```cypher
// Después de Phase 1, debe haber edges Pattern → ApplicationIR
MATCH (p:Pattern)-[r:GENERATED_WITH]-(a:ApplicationIR)
RETURN count(r) as connections
// Target: > 0
```

### 7.2 Verificar Giant Component Unificado

```cypher
// El giant component debe incluir IR nodes
MATCH (n)
WITH n, count { MATCH (n)--() } AS degree
ORDER BY degree DESC
LIMIT 1
WITH n AS start

MATCH (start)-[*0..]-(m)
WITH DISTINCT m
RETURN labels(m) AS labels, count(*) AS cnt
ORDER BY cnt DESC
// Target: ApplicationIR, Entity, Endpoint deben aparecer
```

### 7.3 Medir Beneficio de Pattern Boosting

```cypher
// Comparar success rate: patterns boosteados vs no boosteados
MATCH (app:ApplicationIR)-[r:GENERATED_WITH]->(p:Pattern)
WHERE r.boosted = true
WITH avg(r.smoke_pass_rate) as boosted_rate

MATCH (app:ApplicationIR)-[r:GENERATED_WITH]->(p:Pattern)
WHERE r.boosted = false OR r.boosted IS NULL
WITH boosted_rate, avg(r.smoke_pass_rate) as unboosted_rate

RETURN boosted_rate, unboosted_rate, boosted_rate - unboosted_rate as improvement
// Target: improvement > 0.1 (10% mejor)
```

---

## 8. Métricas de Éxito

| Métrica | Baseline | Target | Cómo medir |
|---------|----------|--------|------------|
| Neo4j queries/generation | 0 | 3-5 | Logs |
| Cross-app pattern reuse | 0% | 30%+ | Query 7.3 |
| Giant component coverage | 62% | 95%+ | Query 7.2 |
| Error reduction (boosted) | N/A | 20%+ | Query 7.3 |

---

## 9. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Queries lentas | Media | Alto | Índices, LIMIT, caching |
| Over-engineering | Alta | Medio | Empezar con Phase 1 solo |
| Datos inconsistentes | Media | Alto | Transacciones atómicas |
| Neo4j downtime | Baja | Alto | Fallback a Qdrant-only |

---

## 10. Decisión: ¿Implementar?

### Argumentos a Favor

1. **Ya tenemos la infra**: Neo4j corriendo, 48k nodos
2. **Datos valiosos sin usar**: 300 apps históricas
3. **Cross-app learning imposible sin esto**: Cada app aprende aislada
4. **Debugging sería trivial**: Graph traversal vs grep logs

### Argumentos en Contra

1. **Smoke ya está en 100%**: ¿Para qué optimizar?
2. **Complejidad adicional**: Más queries = más puntos de fallo
3. **Costo de desarrollo**: 6-10 días de trabajo
4. **Qdrant ya funciona**: Pattern search por embeddings es suficiente

### Recomendación

**DEFER hasta post-MVP**. Razones:

1. Smoke tests ya funcionan al 100%
2. El ROI es especulativo (no sabemos si cross-app learning ayudará)
3. Mejor invertir en otros gaps (test coverage, edge cases)

**Trigger para reconsiderar**:
- Si smoke rate cae consistentemente en nuevos specs
- Si debugging se vuelve pain point frecuente
- Si el sistema necesita escalar a >1000 apps

---

## 11. Alternativa Mínima: Quick Wins

Si queremos extraer valor de Neo4j sin el plan completo:

| Quick Win | Esfuerzo | Valor |
|-----------|----------|-------|
| **Dashboard de métricas** | 2h | Ver estadísticas históricas |
| **Query ad-hoc para debugging** | 1h | Investigar fallos manualmente |
| **Garbage collection** | 1h | Limpiar nodos huérfanos |

```cypher
-- Quick Win: Dashboard query
MATCH (app:ApplicationIR)
RETURN
  count(app) as total_apps,
  avg(app.entity_count) as avg_entities,
  avg(app.endpoint_count) as avg_endpoints
```

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2025-12-01 | Plan inicial creado |

