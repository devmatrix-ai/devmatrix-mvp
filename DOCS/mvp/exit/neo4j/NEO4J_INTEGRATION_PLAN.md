# Neo4j Integration Plan

**Objetivo**: Integrar componentes Neo4j en el pipeline E2E y código fuente principal
**Fecha**: 2025-11-29
**Prerequisito**: Sprint 6 completado (10/10 Safety Rails)

---

## Estado Actual

### Componentes Neo4j Listos

| Componente | Ubicación | Estado |
|------------|-----------|--------|
| `FullIRGraphLoader` | `src/cognitive/services/full_ir_graph_loader.py` | ✅ Ready |
| `GraphIRRepository` | `src/cognitive/services/graph_ir_repository.py` | ✅ Ready |
| `DomainModelGraphRepository` | `src/cognitive/services/domain_model_graph_repository.py` | ✅ Ready |
| `APIModelGraphRepository` | `src/cognitive/services/api_model_graph_repository.py` | ✅ Ready |
| `GraphHealthMonitor` | `src/cognitive/infrastructure/graph_health_monitor.py` | ✅ Ready |
| `AtomicMigration` | `src/cognitive/infrastructure/atomic_migration.py` | ✅ Ready |
| `TemporalMetadata` | `src/cognitive/infrastructure/temporal_metadata.py` | ✅ Ready |

### Pipeline E2E Actual

```
tests/e2e/real_e2e_full_pipeline.py

Phase 1:  Spec Ingestion (SpecParser)
Phase 1.5: Validation Scaling
Phase 2:  Requirements Analysis (RequirementsClassifier)
Phase 3:  Multi-Pass Planning
Phase 4:  Atomization
Phase 5:  DAG Construction
Phase 6:  Wave Execution (Code Generation)
Phase 7:  Deployment (Save Generated Files)
Phase 8:  Code Repair
Phase 8.5: Runtime Smoke Test
Phase 9:  Validation
Phase 10: Health Verification
```

### Gap Identificado

- ❌ ApplicationIR se cachea como JSON, no en Neo4j
- ❌ No hay persistencia de IR en grafo entre ejecuciones
- ❌ No hay lineage tracking entre specs y código generado
- ❌ FullIRGraphLoader no está integrado en pipeline

---

## Plan de Integración

### Sprint 7: Pipeline Integration (3-4 días)

#### 7.1 Neo4j IR Persistence Layer

**Archivo**: `src/cognitive/services/ir_persistence_service.py`

```python
class IRPersistenceService:
    """
    Unified service for IR persistence to Neo4j.
    Replaces JSON caching with graph persistence.
    """

    def __init__(self):
        self.full_loader = FullIRGraphLoader()
        self.domain_repo = DomainModelGraphRepository()
        self.api_repo = APIModelGraphRepository()

    async def save_application_ir(self, app_ir: ApplicationIR) -> str:
        """Save complete ApplicationIR to Neo4j graph."""
        app_id = app_ir.app_id or str(uuid.uuid4())

        # Save each submodel
        await self.domain_repo.save_domain_model(app_ir.domain_model, app_id)
        await self.api_repo.save_api_model(app_ir.api_model, app_id)
        # ... behavior, validation, infrastructure, tests

        return app_id

    async def load_application_ir(self, app_id: str) -> Optional[ApplicationIR]:
        """Load complete ApplicationIR from Neo4j graph."""
        result = self.full_loader.load_full_ir(app_id)
        return result.application_ir if result.success else None

    async def exists(self, app_id: str) -> bool:
        """Check if ApplicationIR exists in graph."""
        return self.full_loader.exists(app_id)
```

**Tareas**:
| ID | Tarea | Esfuerzo |
|----|-------|----------|
| 7.1.1 | Crear `ir_persistence_service.py` | 4h |
| 7.1.2 | Implementar save para todos los submodels | 4h |
| 7.1.3 | Integrar con SpecToApplicationIR | 2h |
| 7.1.4 | Tests de roundtrip completo | 2h |

#### 7.2 Pipeline E2E Integration

**Modificar**: `tests/e2e/real_e2e_full_pipeline.py`

```python
# Nuevos imports
from src.cognitive.services.ir_persistence_service import IRPersistenceService
from src.cognitive.services.full_ir_graph_loader import FullIRGraphLoader

class RealE2EPipeline:
    def __init__(self):
        # ... existing init ...
        self.ir_persistence = IRPersistenceService()
        self.use_neo4j_cache = os.environ.get('USE_NEO4J_CACHE', 'true').lower() == 'true'

    async def phase_1_spec_ingestion(self):
        """Phase 1: Spec Ingestion with Neo4j caching."""

        # Check Neo4j cache first
        if self.use_neo4j_cache:
            cached_ir = await self.ir_persistence.load_application_ir(self.spec_hash)
            if cached_ir:
                self.application_ir = cached_ir
                print(f"    📦 Loaded ApplicationIR from Neo4j (app_id: {self.spec_hash})")
                return

        # Generate new IR
        ir_converter = SpecToApplicationIR()
        self.application_ir = await ir_converter.get_application_ir(...)

        # Save to Neo4j
        if self.use_neo4j_cache:
            await self.ir_persistence.save_application_ir(self.application_ir)
            print(f"    💾 Saved ApplicationIR to Neo4j")
```

**Tareas**:
| ID | Tarea | Esfuerzo |
|----|-------|----------|
| 7.2.1 | Agregar imports y inicialización | 1h |
| 7.2.2 | Modificar Phase 1 para usar Neo4j cache | 2h |
| 7.2.3 | Agregar flag `USE_NEO4J_CACHE` | 0.5h |
| 7.2.4 | Tests E2E con Neo4j enabled/disabled | 2h |

#### 7.3 Lineage Tracking

**Nuevo**: `src/cognitive/services/lineage_tracker.py`

```python
class LineageTracker:
    """
    Track lineage between specs, IRs, and generated code.
    Uses Neo4j relationships for full traceability.
    """

    async def record_generation(
        self,
        app_id: str,
        spec_path: str,
        output_path: str,
        metrics: dict
    ):
        """Record a code generation run with lineage."""
        # Create GenerationRun node
        # Link to ApplicationIR
        # Store metrics

    async def get_generation_history(self, app_id: str) -> List[GenerationRun]:
        """Get all generation runs for an ApplicationIR."""

    async def compare_generations(
        self,
        run_id_1: str,
        run_id_2: str
    ) -> ComparisonReport:
        """Compare two generation runs."""
```

**Tareas**:
| ID | Tarea | Esfuerzo |
|----|-------|----------|
| 7.3.1 | Diseñar schema de lineage | 1h |
| 7.3.2 | Implementar `lineage_tracker.py` | 3h |
| 7.3.3 | Integrar en pipeline Phase 7 (Deployment) | 1h |
| 7.3.4 | Dashboard queries para lineage | 1h |

---

### Sprint 8: Quality & Observability (2-3 días)

#### 8.1 Graph Health en Pipeline

**Integrar**: `GraphHealthMonitor` en validación

```python
async def phase_10_health_verification(self):
    """Phase 10: Health Verification with Graph Health."""

    # Existing health checks...

    # NEW: Graph health check
    if self.use_neo4j_cache:
        health_monitor = GraphHealthMonitor()
        graph_health = await health_monitor.check_health()

        if not graph_health.is_healthy:
            print(f"    ⚠️ Graph health issues: {graph_health.issues}")
        else:
            print(f"    ✅ Graph health: OK")
```

**Tareas**:
| ID | Tarea | Esfuerzo |
|----|-------|----------|
| 8.1.1 | Integrar GraphHealthMonitor en Phase 10 | 1h |
| 8.1.2 | Agregar métricas de grafo a reporte final | 1h |

#### 8.2 IR Compliance from Graph

**Mejorar**: `IRComplianceMetrics` para usar grafo

```python
class IRComplianceMetrics:
    @classmethod
    async def from_graph(cls, app_id: str) -> 'IRComplianceMetrics':
        """Calculate compliance metrics from Neo4j graph."""
        loader = FullIRGraphLoader()
        result = loader.load_full_ir(app_id)

        # Calculate metrics from loaded IR
        return cls(
            entities=len(result.application_ir.domain_model.entities),
            endpoints=len(result.application_ir.api_model.endpoints),
            # ...
        )
```

**Tareas**:
| ID | Tarea | Esfuerzo |
|----|-------|----------|
| 8.2.1 | Agregar `from_graph()` a IRComplianceMetrics | 2h |
| 8.2.2 | Comparar métricas JSON vs Graph | 1h |

#### 8.3 NeoDash Integration

**Usar**: `neodash_views.cypher` para dashboards

**Tareas**:
| ID | Tarea | Esfuerzo |
|----|-------|----------|
| 8.3.1 | Documentar cómo configurar NeoDash | 1h |
| 8.3.2 | Agregar queries específicas para pipeline | 2h |

---

### Sprint 9: Advanced Features (2-3 días)

#### 9.1 Pattern Learning from Graph

**Nuevo**: Usar grafo para aprender patrones de generación

```python
class PatternLearner:
    """Learn code generation patterns from successful runs in Neo4j."""

    async def extract_successful_patterns(self) -> List[Pattern]:
        """
        Query Neo4j for successful generation runs.
        Extract common patterns for reuse.
        """
        query = """
        MATCH (run:GenerationRun {success: true})
        MATCH (run)-[:GENERATED_FROM]->(ir:ApplicationIR)
        MATCH (ir)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
        RETURN ir.app_id, run.metrics, collect(dm.entities) as entities
        ORDER BY run.quality_score DESC
        LIMIT 10
        """
```

#### 9.2 Regression Detection

**Usar**: TestExecutionIR schema para detectar regresiones

```python
class RegressionDetector:
    """Detect regressions using historical test data in Neo4j."""

    async def detect_regression(
        self,
        app_id: str,
        current_results: TestResults
    ) -> RegressionReport:
        """Compare current results with historical data."""
```

---

## Timeline

```
Week 1 (2025-12-02 → 2025-12-06)
├── Día 1-2: Sprint 7.1 (IR Persistence Layer)
├── Día 3: Sprint 7.2 (Pipeline Integration)
└── Día 4-5: Sprint 7.3 (Lineage Tracking)

Week 2 (2025-12-09 → 2025-12-13)
├── Día 1-2: Sprint 8 (Quality & Observability)
└── Día 3-5: Sprint 9 (Advanced Features) [opcional]
```

---

## Criterios de Exit

### Sprint 7 ✓

- [x] IRPersistenceService funcional (Sprint 7.1 ✅)
- [x] Pipeline E2E usa Neo4j cache (Sprint 7.2 ✅)
- [ ] Lineage tracking implementado (Sprint 7.3 pendiente)
- [ ] Tests E2E pasan con `USE_NEO4J_CACHE=true`

### Sprint 8 ✓
- [ ] GraphHealthMonitor integrado en Phase 10
- [ ] IRComplianceMetrics desde grafo
- [ ] NeoDash documentado

### Sprint 9 ✓ (opcional)
- [ ] Pattern learning funcional
- [ ] Regression detection implementado

---

## Archivos a Crear/Modificar

### Nuevos
- `src/cognitive/services/ir_persistence_service.py`
- `src/cognitive/services/lineage_tracker.py`
- `tests/integration/test_ir_persistence_service.py`
- `tests/integration/test_lineage_tracker.py`

### Modificar
- `tests/e2e/real_e2e_full_pipeline.py` - Agregar Neo4j integration
- `src/specs/spec_to_application_ir.py` - Usar persistence service
- `tests/e2e/precision_metrics.py` - Agregar graph metrics

---

## Variables de Entorno

```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Feature Flags
USE_NEO4J_CACHE=true          # Enable Neo4j caching (default: true)
FORCE_IR_REFRESH=false        # Force regenerate IR (default: false)
ENABLE_LINEAGE_TRACKING=true  # Enable lineage (default: true)
```

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Neo4j no disponible | Pipeline falla | Fallback a JSON cache |
| Performance degradada | E2E más lento | Cache in-memory (ya implementado) |
| Schema mismatch | IRs corruptos | Validación pre/post save |
| Concurrency issues | Data inconsistente | Transacciones atómicas |

---

## Referencia: Documentación Archivada

- [IMPLEMENTATION_PLAN_v1_COMPLETED.md](archive/IMPLEMENTATION_PLAN_v1_COMPLETED.md) - Plan original (Sprint 0-6)
- [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md) - Estado final Sprint 6

---

*Plan de Integración v1.0*
*Sprint 7-9: Neo4j → Pipeline E2E*
