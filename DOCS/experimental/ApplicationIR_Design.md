# ApplicationIR - Diseño Arquitectónico Completo

## 1. Overview
Este documento describe el patrón completo para el **ApplicationIR**, su arquitectura, submodelos internos y el flujo transformacional de DevMatrix:

```
Markdown → ApplicationIR → Graphs → Tasks → Code → Validation → Code Repair
```

El objetivo es formalizar el **IR unificado** que representa la aplicación en todas las fases del pipeline.

---

## 2. Patrón recomendado: Aggregate Root + Transformers (Phase Updaters)

### ✔ ApplicationIR es el **Aggregate Root**  
Representa la verdad central y única sobre:

- Domain Model  
- API Model  
- Behavior Model  
- Quality Model  
- Infrastructure Model  
- Planning Model  

Todas las fases del pipeline leen/escriben **copias nuevas** de este IR usando transformadores (Phase Updaters).

---

## 3. Modelo Completo del IR

```python
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class DomainModelIR(BaseModel):
    entities: Dict[str, "EntityIR"] = {}

class APIModelIR(BaseModel):
    endpoints: List["EndpointIR"] = []

class BehaviorModelIR(BaseModel):
    requirements: List["RequirementIR"] = []

class QualityModelIR(BaseModel):
    validations: List["ValidationIR"] = []

class InfrastructureModelIR(BaseModel):
    database: Optional["DatabaseIR"] = None
    observability: Optional["ObservabilityIR"] = None
    security: Optional["SecurityIR"] = None
    testing: Optional["TestingInfraIR"] = None

class PlanningModelIR(BaseModel):
    requirements_graph: Optional["GraphIR"] = None
    component_graph: Optional["GraphIR"] = None
    task_graph: Optional["TaskGraphIR"] = None
    pattern_links: List["PatternLinkIR"] = []

class SpecMetadata(BaseModel):
    spec_path: str
    spec_hash: str
    created_at: datetime
    description: Optional[str] = None

class ApplicationIR(BaseModel):
    app_id: str
    name: str
    version: str = "1.0.0"
    schema_version: str = "1.0.0"
    spec_metadata: SpecMetadata

    domain_model: DomainModelIR
    api_model: APIModelIR
    behavior_model: BehaviorModelIR
    quality_model: QualityModelIR
    infrastructure_model: InfrastructureModelIR
    planning_model: PlanningModelIR

    phase_status: Dict[str, str] = {}

    class Config:
        frozen = True
```

---

## 4. Phase Updaters (Transformers Funcionales)

Cada fase hace:

```
ApplicationIR → ApplicationIR (nuevo)
```

Ejemplo:

```python
class Phase2RequirementsAnalysisUpdater:
    def __init__(self, classifier):
        self._classifier = classifier

    def run(self, ir: ApplicationIR) -> ApplicationIR:
        enriched_behavior, dag = self._classifier.enrich(
            ir.behavior_model, ir.domain_model, ir.api_model
        )

        return ir.copy(update={
            "behavior_model": enriched_behavior,
            "planning_model": ir.planning_model.copy(
                update={"requirements_graph": dag}
            ),
            "phase_status": {**ir.phase_status, "phase_2": "complete"},
        })
```

---

## 5. Flujo Completo del Pipeline usando ApplicationIR

```
Phase 1 — SpecParser → ApplicationIR (esqueleto)

Phase 2 — RequirementsClassifier → IR enriquecido

Phase 3 — PatternBank Matching → IR con patrones

Phase 4 — MultiPassPlanner + DAGBuilder → IR con TaskGraph

Phase 5 — CodeGenerationService → Código generado

Phase 6 — Deployment

Phase 6.5 — CodeRepair → Código converge al IR

Phase 7 — Semantic Validation contra IR

Phase 8 — Health & Infra Validation

Phase 9 — Learning (patterns, heuristics, repairs)
```

---

## 6. Beneficios Estrategicos

- **Máxima valuación**: compradores como Anthropic, Microsoft y OpenAI exigen un IR formal.
- **Determinismo**: el pipeline deja trazabilidad perfecta.
- **Extensibilidad multiplataforma**: FastAPI hoy, mañana NestJS o Django, mismo IR.
- **Reproducibilidad**: puedes reconstruir cualquier app desde el IR.
- **Validación formal**: compliance es “implementación vs IR”, no heurística.

---

## 7. Conclusión

Tu Ground Truth actual YA ES la base del IR.  
Solo hacía falta empaquetarlo formalmente y definir cómo lo transforma cada fase.

Este documento es ahora tu especificación oficial de ApplicationIR.
