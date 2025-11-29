# Análisis de Sprints 3-5 (Core IRs)

> **BehaviorModelIR, ValidationModelIR, InfrastructureModelIR, TestsModelIR**
> **Fecha**: 2025-11-29

---

## Sprint 3 — BehaviorModelIR + ValidationModelIR

**Estado**: PENDIENTE
**Prerrequisito**: Sprint 2.5 (TARGETS_ENTITY)

### Diseño Conceptual ✅

| Componente | Diseño | Estado |
|------------|--------|--------|
| Flow → Step → Action chain | ✅ Correcto | - |
| Invariant como nodo | ✅ Bien pensado | - |
| Esquema consistente con IR | ✅ | - |

### Gap Crítico: Grafo Desconectado

**Problema**:
```yaml
BehaviorModelIR debe referenciar DomainModelIR y APIModelIR

ACTUAL (mal):
  (:Flow)-[:HAS_STEP]->(:Step {action: "create product"})
  # ↑ Step no conecta con Entity(Product) ni Endpoint(POST /products)

REQUERIDO (bien):
  (:Flow)-[:HAS_STEP]->(:Step)
    -[:TARGETS_ENTITY]->(:Entity {name: "Product"})
    -[:CALLS_ENDPOINT]->(:Endpoint {path: "/products"})
```

### Edges Requeridos

```cypher
-- 1. Step → Entity
(Step)-[:TARGETS_ENTITY {
    operation: string,  -- "create", "update", "delete", "read"
    role: string        -- "primary", "secondary"
}]->(Entity)

-- 2. Step → Endpoint
(Step)-[:CALLS_ENDPOINT {
    sequence: integer,
    conditional: boolean
}]->(Endpoint)

-- 3. Invariant → Entity
(Invariant)-[:APPLIES_TO {
    scope: string  -- "pre-condition", "post-condition", "global"
}]->(Entity)

-- 4. Invariant → Attribute
(Invariant)-[:CHECKS_ATTRIBUTE {
    expression: string,  -- "price > 0"
    operator: string     -- ">", "==", "IN", "REGEX"
}]->(Attribute)
```

### Ejemplo Completo

```cypher
-- Flow: "Create Order with Items"

(:Flow {name: "Create Order"})-[:HAS_STEP]->
  (:Step {action: "validate_cart"})
    -[:TARGETS_ENTITY]->(:Entity {name: "Cart"})
    -[:CALLS_ENDPOINT]->(:Endpoint {path: "/carts/{id}"})

(:Flow)-[:HAS_STEP]->
  (:Step {action: "create_order"})
    -[:TARGETS_ENTITY]->(:Entity {name: "Order"})
    -[:CALLS_ENDPOINT]->(:Endpoint {path: "/orders"})

(:Flow)-[:HAS_INVARIANT]->
  (:Invariant {rule: "cart.total > 0"})
    -[:APPLIES_TO]->(:Entity {name: "Cart"})
    -[:CHECKS_ATTRIBUTE]->(:Attribute {name: "total"})
```

### Impacto si no se implementan edges

- ❌ No hay lineage real Flow → Domain → API
- ❌ No se puede detectar impacto de cambios
- ❌ QA pierde trazabilidad
- ❌ BehaviorModel es metadata decorativa, no grafo inteligente

**Prioridad**: 🔴 CRÍTICO

---

## Sprint 4 — InfrastructureModelIR

**Estado**: PENDIENTE

### Diseño Base ✅

| Componente | Estado |
|------------|--------|
| DatabaseConfig | ✅ |
| ContainerService | ✅ |
| Observability | ✅ |

### Gaps Identificados

#### 4.1 ValidationRule → Attribute Link

**Problema**:
```yaml
ACTUAL (mal):
  (:ValidationRule {
    expression: "price > 0",
    target_entity: "Product"  -- STRING, no relationship
  })

REQUERIDO (bien):
  (:ValidationRule {
    expression: "price > 0"
  })-[:VALIDATES_FIELD]->(:Attribute {
    name: "price",
    entity: "Product"
  })
```

**Edge requerido**:
```cypher
(ValidationRule)-[:VALIDATES_FIELD {
    operator: string,      -- ">", "==", "IN", "REGEX"
    expected_value: string -- "0" para price > 0
}]->(Attribute)
```

**Impacto**:
- Sin edge → no hay lineage
- Cambio en Attribute.price no alerta sobre ValidationRule

#### 4.2 Merge Strategy Faltante

**Problema**:
```yaml
Escenario:
  - App regenerada con cambios en DatabaseConfig
  - ¿Qué hacer con InfrastructureModelIR existente?

Opciones:
  A) Reemplazar subgrafo entero (destructivo)
  B) Actualizar sobre IDs determinísticos (incremental)
  C) Versionado de infraestructura (histórico)
```

**Solución recomendada**:
```python
class InfrastructureModelGraphRepository(GraphIRRepository):

    async def save_infra_model(
        self,
        app_id: str,
        infra_ir: InfrastructureModelIR,
        strategy: str = "incremental"
    ):
        if strategy == "incremental":
            # MERGE sobre IDs determinísticos
            # UPDATE properties si existen
            # CREATE si no existen
            ...

        elif strategy == "replace":
            # DELETE subgrafo completo
            # CREATE nuevo subgrafo
            ...
```

**Prioridad**: 🟡 ALTO
**Esfuerzo**: 3-4 hours

---

## Sprint 5 — TestsModelIR

**Estado**: PENDIENTE
**Problema**: Sprint sobrecargado (ver [RISKS.md#r5](./RISKS.md#r5-sprint-5-sobrecargado))

### Diseño Base ✅

| Componente | Estado |
|------------|--------|
| Seeds | ✅ |
| TestSuite | ✅ |
| TestScenarioIR | ✅ |
| Dependencies | ✅ |
| Assertions | ✅ |

### Recomendación: Dividir en 2 Sprints

#### Sprint 5 — MVP (1 semana)

```yaml
Scope:
  Nodos:
    - TestsModelIR
    - EndpointTestSuite
    - TestScenarioIR (básico)

  Edges:
    - VALIDATES_ENDPOINT

  Objetivo:
    - Validación básica endpoint-level
    - Sin seeds, sin flows
```

**Modelo MVP**:
```cypher
(:TestsModelIR)-[:HAS_TEST_SUITE]->
  (:EndpointTestSuite)-[:HAS_SCENARIO]->
    (:TestScenarioIR)-[:VALIDATES_ENDPOINT]->(:Endpoint)
```

#### Sprint 5.5 — Complete (1 semana)

```yaml
Scope adicional:
  Nodos:
    - SeedEntityIR
    - FlowTestSuite
    - Assertions
    - TestExecutionIR

  Edges:
    - DEPENDS_ON_SEED
    - VALIDATES_FLOW
    - VALIDATES_RULE
    - HAS_EXECUTION
```

### Gap Crítico: TestExecutionIR

**Problema**: Plan solo contempla escenarios, no ejecuciones

```yaml
TestScenarioIR:
  - Define QUÉ testear (estático)

TestExecutionIR:
  - Registra CUÁNDO se ejecutó (dinámico)
  - Registra RESULTADO (pass/fail/error)
  - Métricas de performance
```

**Modelo requerido**:
```cypher
CREATE (exec:TestExecutionIR {
    execution_id: string,
    scenario_id: string,

    -- Resultado
    status: string,              -- "pass" | "fail" | "error" | "skipped"
    duration_ms: integer,

    -- Output
    stdout: string,
    stderr: string,
    error_message: string,

    -- Context
    environment: string,         -- "dev" | "staging" | "prod"
    code_branch: string,
    code_commit: string,

    -- Temporal
    started_at: datetime,
    completed_at: datetime
})

-- Relationships
(TestScenarioIR)-[:HAS_EXECUTION]->(TestExecutionIR)
(TestExecutionIR)-[:FOUND_BUG]->(CodeGenerationError)  -- Si falla
(TestExecutionIR)-[:VALIDATED_ENDPOINT]->(Endpoint)    -- Si pass
```

**Query de uso**:
```cypher
-- Success rate últimas 24h
MATCH (s:TestScenarioIR)-[:HAS_EXECUTION]->(e:TestExecutionIR)
WHERE e.completed_at > datetime() - duration('P1D')
WITH s, count(e) as total,
     sum(CASE WHEN e.status = 'pass' THEN 1 ELSE 0 END) as passed
RETURN
    s.scenario_name,
    total,
    passed,
    (100.0 * passed / total) as success_rate
ORDER BY success_rate ASC;
```

**Prioridad**: 🔴 CRÍTICO para QA
**Bloqueante para**: Sprint 6 (lineage), Sprint 8 (analytics)

---

## Resumen de Edges por Sprint

| Sprint | Edge | Impacto |
|--------|------|---------|
| 3 | Step→Entity, Step→Endpoint | Behavior conectado |
| 3 | Invariant→Entity, Invariant→Attribute | Rules conectadas |
| 4 | ValidationRule→Attribute | Validation conectado |
| 5 | TestScenario→Endpoint | Tests conectados |
| 5.5 | TestExecution→* | Métricas reales |

---

*Ver también*: [SPRINT_6-8.md](./SPRINT_6-8.md) para Sprints avanzados
