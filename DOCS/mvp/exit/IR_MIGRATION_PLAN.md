# IR Migration Plan - Phase 3 & Phase 7

**Date**: Nov 26, 2025
**Status**: Phase 7 ✅ IMPLEMENTED | Phase 3 ✅ IMPLEMENTED
**Priority**: Phase 7 🔴 ALTA | Phase 3 🟡 MEDIA

---

## Overview

Migrar las fases pendientes del E2E pipeline a usar ApplicationIR como única fuente de verdad.

```text
Estado Actual (Nov 26, 2025):
┌─────────────────────────────────────────────────────────────┐
│  Phase 1 → ApplicationIR ✅                                 │
│  Phase 3 → DAG ground truth ✅, nodos ✅ MIGRADO a IR      │
│  Phase 6 → generate_from_application_ir() ✅                │
│  Phase 7 → CodeRepairAgent usa ApplicationIR ✅ MIGRADO    │
│  Phase 9 → ComplianceValidator contra IR ✅                 │
└─────────────────────────────────────────────────────────────┘

Estado Objetivo:
┌─────────────────────────────────────────────────────────────┐
│  Phase 1 → ApplicationIR ✅                                 │
│  Phase 3 → DAG 100% desde IR ✅                             │
│  Phase 6 → generate_from_application_ir() ✅                │
│  Phase 7 → CodeRepairAgent usa ApplicationIR ✅             │
│  Phase 9 → ComplianceValidator contra IR ✅                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Plan 1: Phase 7 - CodeRepairAgent Migration

### Prioridad: 🔴 ALTA

### Problema

CodeRepairAgent actualmente usa `spec_requirements` (legacy) para obtener definiciones de entities/endpoints que faltan:

```python
# src/mge/v2/agents/code_repair_agent.py:115-118
entity_req = next(
    (e for e in spec_requirements.entities if e.name.lower() == entity_name.lower()),
    None
)
```

### Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `src/mge/v2/agents/code_repair_agent.py` | Aceptar ApplicationIR, usar DomainModelIR |
| `tests/e2e/real_e2e_full_pipeline.py` | Pasar ApplicationIR a CodeRepairAgent |

### Implementación

#### Task 1.1: Actualizar Constructor de CodeRepairAgent

```python
# ANTES:
class CodeRepairAgent:
    def __init__(self, output_path: Path, llm_client: Optional[EnhancedAnthropicClient] = None):
        self.output_path = Path(output_path).resolve()
        ...

# DESPUÉS:
class CodeRepairAgent:
    def __init__(
        self,
        output_path: Path,
        application_ir: Optional[ApplicationIR] = None,  # NEW
        llm_client: Optional[EnhancedAnthropicClient] = None
    ):
        self.output_path = Path(output_path).resolve()
        self.application_ir = application_ir  # NEW
        ...
```

#### Task 1.2: Actualizar Método repair()

```python
# ANTES:
async def repair(
    self,
    compliance_report,
    spec_requirements,  # ← legacy
    max_attempts: int = 3
) -> RepairResult:

# DESPUÉS:
async def repair(
    self,
    compliance_report,
    spec_requirements=None,  # ← deprecated, keep for backward compat
    max_attempts: int = 3
) -> RepairResult:
    # Use ApplicationIR if available, fallback to spec_requirements
    if self.application_ir:
        return await self._repair_from_ir(compliance_report, max_attempts)
    elif spec_requirements:
        return await self._repair_from_legacy(compliance_report, spec_requirements, max_attempts)
    else:
        raise ValueError("Either application_ir or spec_requirements required")
```

#### Task 1.3: Crear Método _repair_from_ir()

```python
async def _repair_from_ir(
    self,
    compliance_report,
    max_attempts: int = 3
) -> RepairResult:
    """Repair using ApplicationIR as source of truth."""
    repairs_applied = []
    repaired_files = []

    # Get missing entities from IR
    for entity_name in compliance_report.entities_expected:
        if entity_name.lower() not in [e.lower() for e in compliance_report.entities_implemented]:
            # Find entity in IR
            entity_def = next(
                (e for e in self.application_ir.domain_model.entities
                 if e.name.lower() == entity_name.lower()),
                None
            )
            if entity_def:
                success = self._repair_entity_from_ir(entity_def)
                if success:
                    repairs_applied.append(f"Added entity: {entity_name}")
                    repaired_files.append(str(self.entities_file))

    # Get missing endpoints from IR
    for endpoint_str in compliance_report.endpoints_expected:
        if endpoint_str.lower() not in [e.lower() for e in compliance_report.endpoints_implemented]:
            parts = endpoint_str.split()
            if len(parts) >= 2:
                method, path = parts[0].upper(), parts[1]
                endpoint_def = next(
                    (ep for ep in self.application_ir.api_model.endpoints
                     if ep.method.upper() == method and ep.path == path),
                    None
                )
                if endpoint_def:
                    route_file = self._repair_endpoint_from_ir(endpoint_def)
                    if route_file:
                        repairs_applied.append(f"Added endpoint: {method} {path}")
                        repaired_files.append(route_file)

    return RepairResult(
        success=len(repairs_applied) > 0,
        repaired_files=repaired_files,
        repairs_applied=repairs_applied
    )
```

#### Task 1.4: Actualizar E2E Pipeline

```python
# tests/e2e/real_e2e_full_pipeline.py
# En _phase_8_code_repair():

# ANTES:
self.code_repair_agent = CodeRepairAgent(
    output_path=self.output_path,
    llm_client=self.llm_client
)
result = await self.code_repair_agent.repair(
    compliance_report=self.compliance_report,
    spec_requirements=self.spec_requirements
)

# DESPUÉS:
self.code_repair_agent = CodeRepairAgent(
    output_path=self.output_path,
    application_ir=self.application_ir,  # NEW
    llm_client=self.llm_client
)
result = await self.code_repair_agent.repair(
    compliance_report=self.compliance_report,
    # spec_requirements removed - uses application_ir from constructor
)
```

### Tests

```python
# tests/unit/test_code_repair_agent_ir.py
async def test_repair_from_ir():
    """Test CodeRepairAgent uses ApplicationIR correctly."""
    # Create mock ApplicationIR with entity
    app_ir = ApplicationIR(
        domain_model=DomainModelIR(
            entities=[Entity(name="Product", attributes=[...])]
        )
    )

    agent = CodeRepairAgent(output_path=tmp_path, application_ir=app_ir)

    # Mock compliance report with missing entity
    report = ComplianceReport(
        entities_expected=["Product"],
        entities_implemented=[]
    )

    result = await agent.repair(report)
    assert result.success
    assert "Added entity: Product" in result.repairs_applied
```

### Criterio de Éxito

- [x] CodeRepairAgent acepta ApplicationIR
- [x] Repair usa DomainModelIR.entities para definiciones
- [x] Repair usa APIModelIR.endpoints para definiciones
- [x] Backward compatibility con spec_requirements (fallback)
- [x] Tests unitarios pasan
- [x] E2E pipeline funciona con IR

---

## Plan 2: Phase 3 - DAG Nodes Migration

### Prioridad: 🟡 MEDIA

### Problema

Phase 3 construye el DAG con:

- Ground truth desde IR ✅
- Nodos desde `classified_requirements` ⚠️ legacy

```python
# tests/e2e/real_e2e_full_pipeline.py:1556-1581
dag_nodes = self.classified_requirements  # ← legacy!
self.dag = {
    "nodes": [{"id": req.id, "name": req.description} for req in dag_nodes],
    ...
}
```

### Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `tests/e2e/real_e2e_full_pipeline.py` | Construir nodos desde ApplicationIR |
| `src/cognitive/ir/application_ir.py` | Agregar método `get_dag_nodes()` |

### Implementación

#### Task 2.1: Agregar get_dag_nodes() a ApplicationIR

```python
# src/cognitive/ir/application_ir.py

def get_dag_nodes(self) -> List[Dict[str, Any]]:
    """
    Get DAG nodes from all IR models.

    Returns list of nodes with id, name, and type.
    """
    nodes = []

    # Entities from DomainModelIR
    for entity in self.get_entities():
        nodes.append({
            "id": f"entity_{entity.name}",
            "name": entity.name,
            "type": "entity",
            "source": "DomainModelIR"
        })

    # Endpoints from APIModelIR
    for endpoint in self.get_endpoints():
        endpoint_id = f"{endpoint.method}_{endpoint.path}".replace("/", "_")
        nodes.append({
            "id": endpoint_id,
            "name": f"{endpoint.method} {endpoint.path}",
            "type": "endpoint",
            "source": "APIModelIR"
        })

    # Flows from BehaviorModelIR
    for flow in self.get_flows():
        nodes.append({
            "id": f"flow_{flow.name}".replace(" ", "_"),
            "name": flow.name,
            "type": "flow",
            "source": "BehaviorModelIR"
        })

    return nodes
```

#### Task 2.2: Actualizar Phase 3 para usar IR nodes

```python
# tests/e2e/real_e2e_full_pipeline.py
# En _phase_3_multi_pass_planning():

# ANTES:
dag_nodes = self.classified_requirements
self.dag = {
    "nodes": [{"id": req.id, "name": req.description} for req in dag_nodes],
    "edges": [...],
    ...
}

# DESPUÉS:
# Use IR-centric nodes if available, fallback to legacy
if self.application_ir:
    dag_nodes_ir = self.application_ir.get_dag_nodes()
    self.dag = {
        "nodes": dag_nodes_ir,
        "edges": [...],
        ...
    }
    print(f"    ✅ DAG nodes from IR: {len(dag_nodes_ir)} nodes")
else:
    # Fallback to legacy classified_requirements
    dag_nodes = self.classified_requirements
    self.dag = {
        "nodes": [{"id": req.id, "name": req.description} for req in dag_nodes],
        "edges": [...],
        ...
    }
    print(f"    ⚠️ DAG nodes from legacy: {len(dag_nodes)} nodes")
```

#### Task 2.3: Actualizar infer_dependencies para nuevos nodos

```python
# src/cognitive/multi_pass_planner.py
# Asegurar que infer_dependencies_enhanced funciona con nuevo formato de nodos

def infer_dependencies_enhanced(
    self,
    requirements=None,  # ← legacy
    dag_nodes_ir=None,  # ← NEW
    dag_ground_truth=None,
    classification_ground_truth=None
) -> List[Edge]:
    """
    Infer dependencies from nodes.

    Supports both legacy requirements and IR-based nodes.
    """
    if dag_nodes_ir:
        return self._infer_from_ir_nodes(dag_nodes_ir, dag_ground_truth)
    elif requirements:
        return self._infer_from_requirements(requirements, dag_ground_truth, classification_ground_truth)
    else:
        return []
```

### Tests

```python
# tests/unit/test_application_ir_dag.py
def test_get_dag_nodes():
    """Test ApplicationIR generates correct DAG nodes."""
    app_ir = ApplicationIR(
        domain_model=DomainModelIR(
            entities=[Entity(name="Product"), Entity(name="Order")]
        ),
        api_model=APIModelIR(
            endpoints=[Endpoint(method="GET", path="/products")]
        ),
        behavior_model=BehaviorModelIR(
            flows=[Flow(name="Create Order", type=FlowType.WORKFLOW)]
        )
    )

    nodes = app_ir.get_dag_nodes()

    assert len(nodes) == 4  # 2 entities + 1 endpoint + 1 flow
    assert any(n["type"] == "entity" and n["name"] == "Product" for n in nodes)
    assert any(n["type"] == "endpoint" for n in nodes)
    assert any(n["type"] == "flow" for n in nodes)
```

### Criterio de Éxito

- [x] E2E Pipeline tiene método `_get_dag_nodes_from_ir()`
- [x] Phase 3 usa IR nodes cuando disponible
- [x] Fallback a classified_requirements funciona
- [x] DAG incluye entities, endpoints, y flows
- [x] Tests unitarios pasan
- [x] E2E pipeline funciona con nuevos nodos

---

## Orden de Ejecución

```text
1. Phase 7 Migration (🔴 ALTA)
   ├─ Task 1.1: Actualizar constructor
   ├─ Task 1.2: Actualizar método repair()
   ├─ Task 1.3: Crear _repair_from_ir()
   ├─ Task 1.4: Actualizar E2E pipeline
   └─ Tests

2. Phase 3 Migration (🟡 MEDIA)
   ├─ Task 2.1: Agregar get_dag_nodes()
   ├─ Task 2.2: Actualizar Phase 3
   ├─ Task 2.3: Actualizar infer_dependencies
   └─ Tests
```

---

## Estimación

| Plan | Complejidad | Archivos | Riesgo |
|------|-------------|----------|--------|
| **Phase 7** | Media | 2 | Bajo (backward compat) |
| **Phase 3** | Media | 3 | Bajo (fallback logic) |

---

## Rollback Strategy

Ambas migraciones mantienen **backward compatibility**:

- Phase 7: Si `application_ir` es None → usa `spec_requirements`
- Phase 3: Si `application_ir` es None → usa `classified_requirements`

Para rollback completo:

```python
# Desactivar IR en Phase 7:
self.code_repair_agent = CodeRepairAgent(
    output_path=self.output_path,
    application_ir=None,  # ← Force legacy
    llm_client=self.llm_client
)

# Desactivar IR en Phase 3:
self.application_ir = None  # Before _phase_3_multi_pass_planning()
```

---

## Validation Checklist

### Post Phase 7 Migration ✅

- [x] E2E test completa sin errores
- [x] CodeRepair encuentra entities desde IR
- [x] CodeRepair encuentra endpoints desde IR
- [x] Fallback a spec_requirements funciona

### Post Phase 3 Migration ✅

- [x] E2E test completa sin errores
- [x] DAG tiene nodos de entities
- [x] DAG tiene nodos de endpoints
- [x] DAG tiene nodos de flows
- [x] Fallback a classified_requirements funciona

---

## Related Documentation

- [E2E_IR_CENTRIC_INTEGRATION.md](E2E_IR_CENTRIC_INTEGRATION.md) - IR architecture overview
- [pipeline/phases.md](pipeline/phases.md) - Phase reference
- [PIPELINE_E2E_PHASES.md](PIPELINE_E2E_PHASES.md) - Pipeline documentation
