# Plan Completo del Grafo Neo4j (PatternBank + IR)

Guía lista para copiar y pegar en Claude Code. Resume el estado del grafo, los objetivos y las tareas concretas a implementar sin perder detalle.

---

## 1. Contexto general
- Grafo Neo4j con dos pilares:
  - **PatternBank**: patrones de generación, anti-patrones, reparación, etc.
  - **IR de cada app/spec**: ApplicationIR, DomainModelIR, APIModelIR, BehaviorModelIR, ValidationModelIR, InfrastructureModelIR y nodos derivados (Entity, Attribute, Endpoint, Flow, Step, Invariant, ValidationRule, AtomicTask, APISchema*, etc.).
- Objetivo: que el grafo actúe como cognitive compiler unificado; los patrones deben aplicarse sobre el IR real de cada aplicación (hoy no ocurre).
- Trabajo pendiente: cerrar la brecha integrando PatternBank con el IR.

---

## 2. Estado actual del grafo (baseline medido)

### 2.1 Métricas globales
Query usada:
```cypher
CALL {
  MATCH (n)
  RETURN count(n) AS total_nodes
}
CALL {
  MATCH ()-[r]->()
  RETURN count(r) AS total_rels
}
CALL {
  MATCH (n)
  WHERE NOT EXISTS { MATCH (n)--() }
  RETURN count(n) AS isolated_nodes
}
CALL {
  MATCH (n)
  WITH n, count { MATCH (n)--() } AS degree
  RETURN avg(degree) AS avg_degree,
         percentileCont(degree, 0.95) AS p95_degree
}
RETURN
  total_nodes,
  total_rels,
  round(1.0 * total_rels / total_nodes, 2) AS rels_per_node,
  isolated_nodes,
  round(avg_degree, 2) AS avg_degree,
  p95_degree;
```
Resultados (baseline):
- `total_nodes ≈ 48.916`
- `total_rels ≈ 578.757`
- `rels_per_node ≈ 11,8`
- `isolated_nodes = 137`
- `avg_degree ≈ 23,7`
- `p95_degree ≈ 105`
Interpretación: grafo denso y sano, pocos nodos aislados, hubs claros.

### 2.2 Giant component de PatternBank
Queries:
```cypher
MATCH (n)
WITH n, count { MATCH (n)--() } AS degree
ORDER BY degree DESC
LIMIT 1
WITH n AS start

MATCH (start)-[*0..]-(m)
RETURN count(DISTINCT m) AS reachable_nodes;
```
Resultado: `reachable_nodes = 30.112`

Distribución de labels en ese componente:
```cypher
CALL {
  MATCH (n)
  WITH n, count { MATCH (n)--() } AS degree
  ORDER BY degree DESC
  LIMIT 1
  RETURN n AS start
}

MATCH (start)-[*0..]-(m)
WITH DISTINCT m
RETURN labels(m) AS labels, count(*) AS cnt
ORDER BY cnt DESC;
```
Resultado principal:
- Pattern ≈ 30.060
- Tag ≈ 19
- Category ≈ 19
- Repository ≈ 9
- Framework ≈ 5
Conclusión: el componente gigante es casi solo Pattern + taxonomía (Tag/Category/Framework/Repository).

### 2.3 Qué está fuera del giant component (IR)
Query:
```cypher
CALL {
  MATCH (n)
  WITH n, count { MATCH (n)--() } AS degree
  ORDER BY degree DESC
  LIMIT 1
  RETURN n AS start
}

MATCH (start)-[*0..]-(m)
WITH collect(DISTINCT m) AS comp_nodes

MATCH (n)
WHERE NOT n IN comp_nodes
RETURN labels(n) AS labels, count(*) AS cnt
ORDER BY cnt DESC;
```
Resultados clave:
- Attribute 5.291
- Endpoint 4.147
- Invariant 2.538
- Step 1.691
- Entity 1.096
- APIParameter 791
- Flow 474
- ValidationRule 388
- ApplicationIR 306
- BehaviorModelIR 306
- ValidationModelIR 306
- InfrastructureModelIR 306
- DomainModelIR 295
- APIModelIR 281
- APISchemaField 167
- AtomicTask 100
- Otros: Template, IRCorrelationReport, FixPattern, PositiveRepairPattern, etc.
Conclusión: el IR completo por app está fuera del componente gigante de PatternBank (~18k nodos en subgrafos).

### 2.4 Relaciones Pattern → otros labels
Query:
```cypher
MATCH (p:Pattern)--(n)
WHERE NOT n:Pattern
RETURN labels(n) AS other_labels, count(*) AS edges
ORDER BY edges DESC;
```
Resultado:
- Tag → 69.138 edges
- Category → 30.168 edges
- Framework → 30.060 edges
- Repository → 30.060 edges
Conclusión: PatternBank solo se conecta a taxonomía/metadatos; no toca Attribute, Endpoint, Entity, Flow, Invariant, AtomicTask, etc.

### 2.5 Subgrafos IR por aplicación
Query:
```cypher
CALL {
  MATCH (n)
  WHERE n:ApplicationIR
     OR n:DomainModelIR
     OR n:APIModelIR
     OR n:BehaviorModelIR
     OR n:ValidationModelIR
     OR n:InfrastructureModelIR
  WITH n, count { MATCH (n)--() } AS degree
  ORDER BY degree DESC
  LIMIT 1
  RETURN n AS start
}

MATCH (start)-[*0..]-(m)
RETURN count(DISTINCT m) AS reachable_ir_nodes;
```
Resultado: `reachable_ir_nodes = 221`
Interpretación: cada app/spec tiene subgrafo IR de ~221 nodos; ~300 subgrafos similares no conectados entre sí ni a PatternBank.

---

## 3. Objetivo

### 3.1 Conceptual
- Patrones deben aplicarse al IR real: Endpoint, Attribute, Entity, Flow/Step, Invariant/ValidationRule, AtomicTask.
- Se busca un único componente gigante que combine PatternBank + IR + relaciones de aplicación/enforcement.

### 3.2 Técnico
- Definir esquema de integración Pattern ↔ IR (relaciones y cardinalidades).
- Ubicar fuentes de correlación (IRCorrelationReport, PatternScore, etc.).
- Extender el loader Neo4j para crear relaciones Pattern ↔ IR de forma determinista.
- Conservar relaciones actuales (Pattern ↔ Tag/Category/Framework/Repository), evitar explosión de edges y mantener tiempos razonables.

---

## 4. Diseño propuesto Pattern ↔ IR

### 4.1 Relaciones núcleo (mínimo viable)
- `(:Pattern)-[:APPLIES_TO_ENDPOINT]->(:Endpoint)`
- `(:Pattern)-[:APPLIES_TO_ATTRIBUTE]->(:Attribute)`
- `(:Pattern)-[:APPLIES_TO_ENTITY]->(:Entity)`
- `(:Pattern)-[:ENFORCES_INVARIANT]->(:Invariant)` (o hacia ValidationRule)
- `(:Pattern)-[:SHAPES_FLOW]->(:Flow)`
- `(:AtomicTask)-[:USES_PATTERN]->(:Pattern)`

Relaciones opcionales/deseables:
- `(:GenerationAntiPattern)-[:COUNTERED_BY]->(:FixPattern)`
- `(:PositiveRepairPattern)-[:REPAIRS]->(:GenerationAntiPattern)`
- `(:IRCorrelationReport)-[:LINKS_PATTERN]->(:Pattern)`
- `(:IRCorrelationReport)-[:LINKS_IR_NODE]->(:ApplicationIR|DomainModelIR|APIModelIR|BehaviorModelIR|ValidationModelIR|InfrastructureModelIR)`

### 4.2 Cardinalidades razonables
- Limitar targets por patrón (por app): ~5–10 Endpoint y ~5–10 Attribute por patrón.
- Un Endpoint puede tener varios Pattern, pero limitar a top N por score/prioridad/frecuencia.
- Si se usan correlaciones: solo crear edges con score >= threshold configurable.

---

## 5. Fuentes de información

### 5.1 En Neo4j
- Nodos: Pattern, FixPattern, PositiveRepairPattern, GenerationAntiPattern, ApplicationIR, DomainModelIR, APIModelIR, BehaviorModelIR, ValidationModelIR, InfrastructureModelIR, Endpoint, Entity, Attribute, Flow, Step, Invariant, ValidationRule, AtomicTask, IRCorrelationReport, PatternScore (si existe).
- Propiedades: IDs lógicos para vincular IR ↔ patrones (pattern_id, ir_node_id, correlation_score, etc.).

### 5.2 En código / storage externo
- Clases/servicios que calculan correlaciones IR–Pattern, scores de patrones y reportes.
- Módulo que construye/guarda IRCorrelationReport / PatternScore y alimenta Neo4j (reusar, no recalcular).

---

## 6. Plan de implementación (Claude Code)

### Paso 1 – Auditar estructuras existentes
- Buscar en el código: IRCorrelationReport, PatternScore, “pattern correlation”, “matcher”, “semantic matcher”.
- Documentar datos (IDs, scores, tipos) y cómo se relacionan con Endpoint/Entity/Attribute/Flow/AtomicTask.
- Verificar qué ya se guarda en Neo4j (existen nodos IRCorrelationReport).

### Paso 2 – Definir mapping lógico Pattern ↔ IR
- Endpoint: entrada típica OpenAPI path + method; mapear patrones (auth, pagination, error handling).
- Attribute/Entity: campos (price, unit_price, email, created_at); mapear por invariantes/constraints/normalización semántica.
- Invariant/ValidationRule: reglas de negocio (stock >= 0, price > 0); mapear a patrones de validación/seguridad/consistencia.
- Flow/Step: secuencias (cart → checkout → payment → order); mapear a patrones de orquestación/idempotencia/retries/sagas.
- AtomicTask: unidad de planner; patrones a nivel de bloque/operación.
- Claude debe traducir correlaciones existentes (reportes/scores) en relaciones concretas.

### Paso 3 – Crear relaciones en el loader Neo4j
- Añadir fase `PatternIRLinker` (nombre sugerido) al pipeline de carga.
- Para cada IRCorrelationReport (o equivalente):
  - Resolver Pattern por ID.
  - Resolver target IR (Endpoint/Attribute/Entity/etc.).
  - Elegir relación según tipo y score >= MIN_SCORE.
  - MERGE para no duplicar; limitar cantidad por patrón/target según parámetros.
Pseudocódigo:
```python
for corr in correlation_reports:
    pattern = get_pattern_by_id(corr.pattern_id)
    target_node = get_ir_node_by_id(corr.target_ir_id)

    if corr.type == "endpoint":
        rel_type = "APPLIES_TO_ENDPOINT"
    elif corr.type == "attribute":
        rel_type = "APPLIES_TO_ATTRIBUTE"
    # ...

    if corr.score >= MIN_SCORE:
        neo4j_session.run(
            f"""
            MATCH (p:Pattern {{id: $pattern_id}})
            MATCH (t:{corr.target_label} {{id: $target_id}})
            MERGE (p)-[r:{rel_type}]->(t)
            SET r.score = $score
            """,
            pattern_id=corr.pattern_id,
            target_id=corr.target_ir_id,
            score=corr.score,
        )
```

### Paso 4 – Validaciones post-carga
- **Relaciones Pattern → otros labels** (deben aparecer labels IR):
  ```cypher
  MATCH (p:Pattern)--(n)
  WHERE NOT n:Pattern
  RETURN labels(n) AS other_labels, count(*) AS edges
  ORDER BY edges DESC;
  ```
- **Tamaño del nuevo giant component**:
  ```cypher
  MATCH (n)
  WITH n, count { MATCH (n)--() } AS degree
  ORDER BY degree DESC
  LIMIT 1
  WITH n AS start

  MATCH (start)-[*0..]-(m)
  RETURN count(DISTINCT m) AS reachable_nodes;
  ```
  Objetivo: `reachable_nodes` ≈ `total_nodes - isolated_nodes`.
- **Labels dentro del giant component**:
  ```cypher
  CALL {
    MATCH (n)
    WITH n, count { MATCH (n)--() } AS degree
    ORDER BY degree DESC
    LIMIT 1
    RETURN n AS start
  }

  MATCH (start)-[*0..]-(m)
  WITH DISTINCT m
  RETURN labels(m) AS labels, count(*) AS cnt
  ORDER BY cnt DESC;
  ```

---

## 7. Criterios de éxito
- PatternBank e IR en un único giant component (salvo pocos aislados).
- Query Pattern --( )--> other_labels muestra labels IR con número de edges coherente.
- Navegación por app: desde un Pattern se llega al Endpoint/Attribute/Entity/Flow/AtomicTask afectado.
- Coste de carga y consulta sigue razonable (sin explosión de relaciones).
