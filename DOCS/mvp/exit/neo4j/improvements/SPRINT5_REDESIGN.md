# Sprint 5 Redesign: TestsModelIR Expansion

> **Document**: Fase 5 - Sprint 5 Redesign
> **Date**: 2025-11-29
> **Status**: APPROVED

---

## Executive Summary

Sprint 5 original es demasiado grande para un solo sprint. Este documento divide Sprint 5 en dos partes:

| Sprint | Enfoque | Duración | Complejidad |
|--------|---------|----------|-------------|
| **5 MVP** | TestsModelIR básico | 1 semana | Media |
| **5.5 Complete** | TestExecutionIR + Flows | 1 semana | Alta |

---

## Sprint 5 MVP (Semana 1)

### Scope

**Incluido:**
- TestsModelIR node y HAS_TESTS_MODEL relationship
- SeedEntityIR node y HAS_SEED_ENTITY relationship
- EndpointTestSuite node y HAS_ENDPOINT_SUITE relationship
- TestScenarioIR node (happy path + error cases)
- VALIDATES_ENDPOINT relationship (TestScenarioIR → Endpoint)

**Excluido (movido a 5.5):**
- SeedFieldValue nodes (granularidad excesiva para MVP)
- DEPENDS_ON_SEED relationships
- FlowTestSuite nodes
- TestExecutionIR nodes

### Target Schema (MVP)

```
(:ApplicationIR)
    └── HAS_TESTS_MODEL → (:TestsModelIR)
            ├── HAS_SEED_ENTITY → (:SeedEntityIR)
            └── HAS_ENDPOINT_SUITE → (:EndpointTestSuite)
                    └── HAS_SCENARIO → (:TestScenarioIR)
                            └── VALIDATES_ENDPOINT → (:Endpoint)
```

### Node Schemas

#### TestsModelIR

```cypher
(:TestsModelIR {
    tests_model_id: string,      -- "{app_id}|tests"
    app_id: string,
    generated_at: datetime,
    generator_version: string,
    source_ir_hash: string,      -- Hash of source IRs for change detection
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

#### SeedEntityIR

```cypher
(:SeedEntityIR {
    seed_entity_id: string,      -- "{app_id}|seed|{entity_name}"
    entity_name: string,
    table_name: string,
    count: integer,              -- Number of seed records
    priority: integer,           -- Order for dependency resolution
    tests_model_id: string,
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

#### EndpointTestSuite

```cypher
(:EndpointTestSuite {
    suite_id: string,            -- "{app_id}|suite|{method}|{path_hash}"
    endpoint_path: string,
    http_method: string,
    tests_model_id: string,
    scenario_count: integer,
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

#### TestScenarioIR

```cypher
(:TestScenarioIR {
    scenario_id: string,         -- "{suite_id}|scenario|{name}"
    name: string,
    description: string,
    test_type: string,           -- "happy_path" | "error_case" | "edge_case"
    expected_status_code: integer,
    priority: string,            -- "critical" | "high" | "medium" | "low"
    suite_id: string,
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

### Relationship Schemas

#### HAS_TESTS_MODEL

```cypher
(ApplicationIR)-[:HAS_TESTS_MODEL {
    created_at: datetime
}]->(TestsModelIR)
```

#### HAS_SEED_ENTITY

```cypher
(TestsModelIR)-[:HAS_SEED_ENTITY {
    order: integer,              -- Seed order for dependencies
    created_at: datetime
}]->(SeedEntityIR)
```

#### HAS_ENDPOINT_SUITE

```cypher
(TestsModelIR)-[:HAS_ENDPOINT_SUITE {
    created_at: datetime
}]->(EndpointTestSuite)
```

#### HAS_SCENARIO

```cypher
(EndpointTestSuite)-[:HAS_SCENARIO {
    test_type: string,           -- "happy_path" | "error_case"
    created_at: datetime
}]->(TestScenarioIR)
```

#### VALIDATES_ENDPOINT

```cypher
(TestScenarioIR)-[:VALIDATES_ENDPOINT {
    coverage_type: string,       -- "functional" | "security" | "performance"
    confidence: float,
    created_at: datetime
}]->(Endpoint)
```

### Exit Criteria (Sprint 5 MVP)

- [ ] TestsModelIR nodes created for all apps with tests
- [ ] SeedEntityIR nodes created
- [ ] EndpointTestSuite nodes created
- [ ] TestScenarioIR nodes created
- [ ] VALIDATES_ENDPOINT coverage >= 60%
- [ ] Schema version updated to 7

---

## Sprint 5.5 Complete (Semana 2)

### Scope

**Incluido:**
- SeedFieldValue nodes (field-level seed config)
- DEPENDS_ON_SEED relationships (seed ordering)
- FlowTestSuite nodes (multi-step test flows)
- TestExecutionIR nodes (runtime tracking)
- HAS_EXECUTION relationship

### Additional Nodes

#### SeedFieldValue

```cypher
(:SeedFieldValue {
    field_id: string,
    field_name: string,
    generator: string,           -- "uuid4" | "faker.name" | "sequence"
    generator_params: string,    -- JSON config
    seed_entity_id: string,
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

#### FlowTestSuite

```cypher
(:FlowTestSuite {
    flow_suite_id: string,
    name: string,
    description: string,
    step_count: integer,
    tests_model_id: string,
    created_at: datetime,
    updated_at: datetime,
    schema_version: integer
})
```

#### TestExecutionIR (Critical!)

```cypher
(:TestExecutionIR {
    execution_id: string,        -- UUID
    scenario_id: string,         -- Reference to TestScenarioIR
    executed_at: datetime,
    status: string,              -- "passed" | "failed" | "skipped" | "error"
    duration_ms: integer,
    error_message: string,
    stack_trace: string,
    test_framework: string,      -- "pytest" | "jest" | etc.
    runner: string,              -- "qa_agent" | "ci_pipeline" | "manual"
    environment: string,         -- "local" | "staging" | "prod"
    app_id: string,
    build_id: string,            -- CI build reference
    created_at: datetime,
    schema_version: integer
})
```

### Additional Relationships

#### HAS_SEED_FIELD

```cypher
(SeedEntityIR)-[:HAS_SEED_FIELD {
    created_at: datetime
}]->(SeedFieldValue)
```

#### DEPENDS_ON_SEED

```cypher
(SeedEntityIR)-[:DEPENDS_ON_SEED {
    dependency_type: string,     -- "foreign_key" | "reference"
    created_at: datetime
}]->(SeedEntityIR)
```

#### HAS_FLOW_SUITE

```cypher
(TestsModelIR)-[:HAS_FLOW_SUITE {
    created_at: datetime
}]->(FlowTestSuite)
```

#### VALIDATES_FLOW

```cypher
(FlowTestSuite)-[:VALIDATES_FLOW {
    created_at: datetime
}]->(Flow)
```

#### HAS_EXECUTION

```cypher
(TestScenarioIR)-[:HAS_EXECUTION {
    created_at: datetime
}]->(TestExecutionIR)
```

### Exit Criteria (Sprint 5.5)

- [ ] SeedFieldValue nodes created
- [ ] DEPENDS_ON_SEED relationships created
- [ ] FlowTestSuite nodes created
- [ ] VALIDATES_FLOW coverage >= 50%
- [ ] TestExecutionIR tracking operational
- [ ] Schema version updated to 8

---

## TestExecutionIR Design (Critical Component)

### Purpose

TestExecutionIR es **crítico** para:
1. **Regression Analysis**: Detectar tests que antes pasaban y ahora fallan
2. **QA Dashboards**: Métricas reales de calidad
3. **ML Training**: Patrones de fallos para predicción

### Usage Patterns

#### 1. Record Test Execution

```python
async def record_execution(
    scenario_id: str,
    status: str,
    duration_ms: int,
    error: Optional[str] = None
):
    query = """
    MATCH (s:TestScenarioIR {scenario_id: $scenario_id})
    CREATE (e:TestExecutionIR {
        execution_id: randomUUID(),
        scenario_id: $scenario_id,
        executed_at: datetime(),
        status: $status,
        duration_ms: $duration_ms,
        error_message: $error,
        runner: 'qa_agent',
        environment: $env
    })
    CREATE (s)-[:HAS_EXECUTION {created_at: datetime()}]->(e)
    RETURN e.execution_id
    """
```

#### 2. Detect Regressions

```cypher
// Find scenarios that were passing but now fail
MATCH (s:TestScenarioIR)-[:HAS_EXECUTION]->(recent:TestExecutionIR)
WHERE recent.status = 'failed'
  AND recent.executed_at > datetime() - duration('P1D')
WITH s, recent
MATCH (s)-[:HAS_EXECUTION]->(prev:TestExecutionIR)
WHERE prev.status = 'passed'
  AND prev.executed_at < recent.executed_at
RETURN s.name as scenario,
       recent.error_message as current_error,
       prev.executed_at as last_passed
ORDER BY recent.executed_at DESC
```

#### 3. Test Health Dashboard

```cypher
// Test health by endpoint
MATCH (e:Endpoint)<-[:VALIDATES_ENDPOINT]-(s:TestScenarioIR)
OPTIONAL MATCH (s)-[:HAS_EXECUTION]->(exec:TestExecutionIR)
WHERE exec.executed_at > datetime() - duration('P7D')
WITH e, s,
     count(exec) as total_runs,
     sum(CASE WHEN exec.status = 'passed' THEN 1 ELSE 0 END) as passed
RETURN e.path as endpoint,
       e.method as method,
       count(s) as scenarios,
       sum(total_runs) as executions,
       round(100.0 * sum(passed) / sum(total_runs), 2) as pass_rate
ORDER BY pass_rate ASC
```

#### 4. Flaky Test Detection

```cypher
// Find tests with inconsistent results
MATCH (s:TestScenarioIR)-[:HAS_EXECUTION]->(e:TestExecutionIR)
WHERE e.executed_at > datetime() - duration('P30D')
WITH s, collect(e.status) as statuses
WHERE 'passed' IN statuses AND 'failed' IN statuses
RETURN s.name as scenario,
       size([x IN statuses WHERE x = 'passed']) as pass_count,
       size([x IN statuses WHERE x = 'failed']) as fail_count,
       size(statuses) as total_runs
ORDER BY fail_count DESC
```

---

## Migration Strategy

### Sprint 5 MVP Migration (011)

```python
# scripts/migrations/neo4j/011_expand_tests_model_mvp.py

class TestsModelMVPExpansion:
    """
    Creates:
    - TestsModelIR nodes
    - SeedEntityIR nodes
    - EndpointTestSuite nodes
    - TestScenarioIR nodes
    - VALIDATES_ENDPOINT relationships
    """
```

### Sprint 5.5 Migration (012)

```python
# scripts/migrations/neo4j/012_expand_tests_model_complete.py

class TestsModelCompleteExpansion:
    """
    Creates:
    - SeedFieldValue nodes
    - FlowTestSuite nodes
    - TestExecutionIR infrastructure
    - DEPENDS_ON_SEED, VALIDATES_FLOW relationships
    """
```

---

## Updated Timeline

```
Week 1 (Sprint 5 MVP)
├── Day 1-2: TestsModelIR, SeedEntityIR nodes
├── Day 3-4: EndpointTestSuite, TestScenarioIR nodes
└── Day 5: VALIDATES_ENDPOINT inference

Week 2 (Sprint 5.5 Complete)
├── Day 1: SeedFieldValue, DEPENDS_ON_SEED
├── Day 2-3: FlowTestSuite, VALIDATES_FLOW
├── Day 4-5: TestExecutionIR implementation
```

---

## Validation Queries

```cypher
-- Sprint 5 MVP Coverage
MATCH (t:TestsModelIR)
RETURN count(t) as tests_models;

MATCH (s:TestScenarioIR)
RETURN count(s) as scenarios;

-- VALIDATES_ENDPOINT coverage
MATCH (e:Endpoint)
OPTIONAL MATCH (s:TestScenarioIR)-[:VALIDATES_ENDPOINT]->(e)
WITH count(e) as total, count(s) as covered
RETURN total, covered, round(100.0 * covered / total, 2) as coverage;

-- Sprint 5.5 Coverage
MATCH (e:TestExecutionIR)
RETURN count(e) as executions;

MATCH (f:FlowTestSuite)
RETURN count(f) as flow_suites;
```

---

*Sprint 5 Redesign - Approved for Implementation*
