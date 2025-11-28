# TestsIR: Plan de Arquitectura Unificada de Testing

## Progreso de Implementación

| Fase | Descripción | Estado | Archivos | Notas |
|------|-------------|--------|----------|-------|
| **Fase 1** | Diseño TestsModelIR | ✅ Completado | `src/cognitive/ir/tests_model.py` | Integrado en ApplicationIR |
| **Fase 2** | Generador Determinístico | ✅ Completado | `src/services/tests_ir_generator.py` | 100% coverage garantizado |
| **Fase 3** | Consumidores IR-Céntricos | ✅ Completado | `src/services/ir_test_code_generator.py`, `src/validation/smoke_runner_v2.py` | Tests + Runner listos |
| **Fase 4** | Migración Pipeline | ✅ Completado | `tests/e2e/real_e2e_full_pipeline.py` | `_run_ir_smoke_test()` activo |

**Última actualización**: 2025-11-28
**Bugs relacionados**: #129, #130, Code Repair 0%, 7/35 cobertura
**Estado**: ✅ **IMPLEMENTACIÓN COMPLETA** - Listo para testing E2E

---

## Resumen Ejecutivo

Centralizar toda la lógica de testing en un nuevo sub-modelo `TestsModelIR` dentro de `ApplicationIR`, eliminando problemas de sincronización entre lo que el código genera y lo que los tests verifican.

---

## 1. Problema Actual

### 1.1 Síntomas Observados

| Bug | Síntoma | Root Cause |
|-----|---------|------------|
| #129/#130 | `/health/health` 404 en smoke test | IR tiene path incorrecto que difiere del código generado |
| Code Repair 0% | 199 repairs, 0% improvement | Repair y checker miden cosas diferentes |
| 7/35 scenarios | Baja cobertura smoke test | LLM genera solo 20% de endpoints |
| 72 tests fail | 32.9% failure rate | Tests generados no matchean código |

### 1.2 Arquitectura Actual (Fragmentada)

```
┌─────────────────────────────────────────────────────────────────┐
│                      ApplicationIR                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │DomainModelIR│  │APIModelIR   │  │ValidationModelIR        │  │
│  │ entities    │  │ endpoints   │  │ rules                   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                  │                    │
         │                  │                    │
         ▼                  ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ir_test_generator│  │planner_agent.py  │  │compliance_checker│
│ (validation)    │  │ (LLM smoke test) │  │ (semantic match) │
│ DESYNC!         │  │ DESYNC!          │  │ DESYNC!          │
└─────────────────┘  └──────────────────┘  └──────────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              Tests Generados (Sin Fuente Única)                  │
│  test_validation.py  smoke_test_plan.json  compliance_report    │
└─────────────────────────────────────────────────────────────────┘
```

**Problemas:**
1. Cada componente lee del IR de forma independiente
2. El LLM en planner_agent puede "inventar" scenarios
3. No hay validación cruzada entre tests y código generado
4. Los paths en IR pueden diferir de los paths en código generado

---

## 2. Solución Propuesta: TestsModelIR

### 2.1 Nueva Arquitectura (Unificada)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ApplicationIR                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │DomainModelIR│  │APIModelIR   │  │ValidationModel│  │ TestsModelIR │  │
│  │ entities    │  │ endpoints   │  │ rules         │  │ ★ NUEVO ★    │  │
│  └─────────────┘  └─────────────┘  └───────────────┘  └──────────────┘  │
│         │               │                 │                  │          │
│         └───────────────┼─────────────────┼──────────────────┘          │
│                         │                 │                             │
│                         ▼                 ▼                             │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      TestsModelIR                               │    │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐    │    │
│  │  │SeedDataIR    │  │ScenariosIR    │  │MetricsConfigIR   │    │    │
│  │  │ entities[]   │  │ by_endpoint[] │  │ thresholds       │    │    │
│  │  │ fixtures[]   │  │ by_flow[]     │  │ coverage_targets │    │    │
│  │  └──────────────┘  └───────────────┘  └──────────────────┘    │    │
│  │  ┌──────────────────────────────────────────────────────────┐ │    │
│  │  │ValidationConfigIR                                        │ │    │
│  │  │ pre_conditions[]  post_conditions[]  invariants[]        │ │    │
│  │  └──────────────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ SINGLE SOURCE OF TRUTH
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        TestsIR Consumers                                 │
│  ┌───────────────────┐  ┌────────────────┐  ┌─────────────────────┐    │
│  │TestCodeGenerator  │  │SmokeTestRunner │  │ComplianceValidator  │    │
│  │ → test_*.py       │  │ → HTTP tests   │  │ → metrics           │    │
│  └───────────────────┘  └────────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Estructura de TestsModelIR

```python
# src/cognitive/ir/tests_model.py

class SeedEntity(BaseModel):
    """Seed data entity for testing."""
    entity_name: str                    # "Product", "Cart"
    uuid: str                           # "00000000-0000-4000-8000-000000000001"
    state: Optional[str] = None         # "active", "inactive", "paid"
    fields: Dict[str, Any]              # Field values
    depends_on: List[str] = []          # FK dependencies (UUIDs)

class TestScenarioIR(BaseModel):
    """Single test scenario derived from IR."""
    id: str                             # Unique scenario ID
    endpoint_ref: str                   # Reference to APIModelIR endpoint
    scenario_type: ScenarioType         # happy_path, not_found, validation_error, etc.
    name: str                           # Human-readable name
    description: str

    # Request
    path_params: Dict[str, str] = {}
    query_params: Optional[Dict[str, str]] = None
    payload: Optional[Dict[str, Any]] = None

    # Expectations
    expected_status: Union[int, List[int]]
    expected_response_contains: Optional[List[str]] = None

    # Traceability
    derived_from: str                   # "endpoint:GET /products", "flow:checkout", "validation:email_format"
    seed_data_refs: List[str] = []      # UUIDs needed for this scenario

class ScenarioType(str, Enum):
    HAPPY_PATH = "happy_path"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    BUSINESS_RULE = "business_rule"
    STATE_TRANSITION = "state_transition"
    FLOW_STEP = "flow_step"
    INVARIANT = "invariant"

class EndpointTestSuite(BaseModel):
    """All scenarios for a single endpoint."""
    endpoint_key: str                   # "GET /products/{id}"
    endpoint_path: str                  # Actual path from APIModelIR
    scenarios: List[TestScenarioIR]
    coverage: EndpointCoverage

class EndpointCoverage(BaseModel):
    has_happy_path: bool = False
    has_not_found: bool = False
    has_validation_tests: int = 0
    has_auth_tests: bool = False
    coverage_score: float = 0.0         # 0.0 - 1.0

class FlowTestSuite(BaseModel):
    """All scenarios for a business flow."""
    flow_ref: str                       # Reference to BehaviorModelIR flow
    flow_name: str
    steps: List[TestScenarioIR]         # Ordered steps
    invariants_tested: List[str]        # Invariants verified by this flow

class MetricsConfigIR(BaseModel):
    """Testing metrics and thresholds."""
    coverage_target: float = 0.80       # 80% minimum coverage
    happy_path_required: bool = True    # All endpoints need happy_path
    max_response_time_ms: int = 5000    # 5s max

    # Quality gates
    dev_pass_rate: float = 0.67         # 67% for dev
    staging_pass_rate: float = 0.90     # 90% for staging
    prod_pass_rate: float = 0.95        # 95% for prod

class ValidationConfigIR(BaseModel):
    """Pre/post conditions and invariants for tests."""
    pre_conditions: List[TestCondition] = []
    post_conditions: List[TestCondition] = []
    invariants: List[TestInvariant] = []

class TestCondition(BaseModel):
    """Pre/post condition for a test."""
    name: str
    check: str                          # "entity_exists", "field_equals", etc.
    params: Dict[str, Any]

class TestInvariant(BaseModel):
    """Business invariant to verify."""
    name: str
    description: str
    rule: str                           # "balance >= 0", "status in ['active', 'inactive']"
    entities: List[str]                 # Entities affected

class TestsModelIR(BaseModel):
    """
    Complete testing model derived from ApplicationIR.

    SINGLE SOURCE OF TRUTH for all testing operations.
    """
    # Seed data
    seed_data: List[SeedEntity] = []
    fixtures: Dict[str, Dict[str, Any]] = {}  # Reusable test fixtures

    # Test suites
    endpoint_suites: List[EndpointTestSuite] = []
    flow_suites: List[FlowTestSuite] = []

    # Configuration
    metrics: MetricsConfigIR = MetricsConfigIR()
    validation: ValidationConfigIR = ValidationConfigIR()

    # Derived metrics
    total_scenarios: int = 0
    coverage_score: float = 0.0

    # Traceability
    generated_from_ir_version: str = ""
    generation_timestamp: datetime = None
```

---

## 3. Proceso de Generación

### 3.1 Pipeline de Generación de TestsModelIR

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TestsModelIR Generation Pipeline                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STEP 1: Extract from IR (Deterministic)                                │
│  ────────────────────────────────────────                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │APIModelIR   │ ──► │Generate     │ ──► │Endpoint     │               │
│  │.endpoints   │     │happy_path   │     │TestSuites   │               │
│  │             │     │not_found    │     │(skeleton)   │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│                                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │Validation   │ ──► │Generate     │ ──► │Validation   │               │
│  │ModelIR.rules│     │error tests  │     │scenarios    │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│                                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │BehaviorModel│ ──► │Generate     │ ──► │Flow         │               │
│  │IR.flows     │     │flow tests   │     │TestSuites   │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│                                                                          │
│  STEP 2: Generate Seed Data (Deterministic)                             │
│  ──────────────────────────────────────────                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │DomainModel  │ ──► │Analyze FKs  │ ──► │SeedEntities │               │
│  │IR.entities  │     │& states     │     │(ordered)    │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│                                                                          │
│  STEP 3: Enrich with LLM (Optional, Controlled)                         │
│  ──────────────────────────────────────────────                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │TestsModelIR │ ──► │LLM reviews  │ ──► │TestsModelIR │               │
│  │(skeleton)   │     │& suggests   │     │(enriched)   │               │
│  │             │     │edge cases   │     │             │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│                                                                          │
│  STEP 4: Validate (Mandatory)                                           │
│  ────────────────────────────                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ✓ All endpoints have at least happy_path                        │   │
│  │ ✓ All {id} endpoints have not_found                             │   │
│  │ ✓ All seed UUIDs exist for referenced path_params               │   │
│  │ ✓ FK dependencies are ordered correctly                         │   │
│  │ ✓ Paths match exactly with APIModelIR                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Generador Determinístico (Sin LLM)

```python
# src/cognitive/ir/tests_model_generator.py

class TestsModelGenerator:
    """
    Generates TestsModelIR deterministically from ApplicationIR.
    NO LLM calls - pure transformation logic.
    """

    def generate(self, app_ir: ApplicationIR) -> TestsModelIR:
        """Generate complete TestsModelIR from ApplicationIR."""
        tests_ir = TestsModelIR(
            generated_from_ir_version=app_ir.version,
            generation_timestamp=datetime.utcnow()
        )

        # Step 1: Generate seed data from entities
        tests_ir.seed_data = self._generate_seed_data(app_ir.domain_model)

        # Step 2: Generate endpoint test suites
        tests_ir.endpoint_suites = self._generate_endpoint_suites(
            app_ir.api_model,
            app_ir.validation_model,
            tests_ir.seed_data
        )

        # Step 3: Generate flow test suites
        tests_ir.flow_suites = self._generate_flow_suites(
            app_ir.behavior_model,
            tests_ir.seed_data
        )

        # Step 4: Calculate coverage
        tests_ir.total_scenarios = self._count_scenarios(tests_ir)
        tests_ir.coverage_score = self._calculate_coverage(tests_ir)

        # Step 5: Validate
        self._validate(tests_ir, app_ir)

        return tests_ir

    def _generate_seed_data(self, domain_model: DomainModelIR) -> List[SeedEntity]:
        """
        Generate seed data for all entities with FK ordering.

        Uses topological sort to ensure parents before children.
        """
        # ... implementación

    def _generate_endpoint_suites(
        self,
        api_model: APIModelIR,
        validation_model: ValidationModelIR,
        seed_data: List[SeedEntity]
    ) -> List[EndpointTestSuite]:
        """
        Generate test suite for each endpoint.

        For each endpoint:
        1. happy_path (always)
        2. not_found (if has {id} param)
        3. validation_error (for each validation rule on request fields)
        """
        # ... implementación

    def _generate_flow_suites(
        self,
        behavior_model: BehaviorModelIR,
        seed_data: List[SeedEntity]
    ) -> List[FlowTestSuite]:
        """
        Generate test suite for each business flow.

        Converts flow steps into ordered test scenarios.
        """
        # ... implementación

    def _validate(self, tests_ir: TestsModelIR, app_ir: ApplicationIR):
        """
        Validate TestsModelIR against ApplicationIR.

        Raises ValidationError if:
        - Any endpoint missing happy_path
        - Any seed UUID orphaned
        - Path mismatch between test and API
        """
        # ... implementación
```

---

## 4. Consumidores de TestsModelIR

### 4.1 Test Code Generator

```python
# src/services/test_code_generator.py

class TestCodeGenerator:
    """Generate pytest files from TestsModelIR."""

    def generate_all(self, tests_ir: TestsModelIR) -> Dict[str, str]:
        """
        Generate all test files.

        Returns:
            Dict[filename, content]
        """
        files = {}

        # test_validation_generated.py
        files["test_validation_generated.py"] = self._generate_validation_tests(tests_ir)

        # test_integration_generated.py
        files["test_integration_generated.py"] = self._generate_integration_tests(tests_ir)

        # test_contract_generated.py
        files["test_contract_generated.py"] = self._generate_contract_tests(tests_ir)

        # test_flows_generated.py
        files["test_flows_generated.py"] = self._generate_flow_tests(tests_ir)

        # conftest.py (fixtures from seed_data)
        files["conftest.py"] = self._generate_conftest(tests_ir)

        return files
```

### 4.2 Smoke Test Runner

```python
# src/validation/smoke_test_runner.py

class SmokeTestRunner:
    """Execute smoke tests from TestsModelIR."""

    def __init__(self, tests_ir: TestsModelIR, base_url: str):
        self.tests_ir = tests_ir
        self.base_url = base_url

    async def run_all(self) -> SmokeTestReport:
        """
        Run all smoke test scenarios.

        Uses TestsModelIR as single source of truth - no LLM.
        """
        # 1. Seed database with tests_ir.seed_data
        await self._seed_database()

        # 2. Execute each scenario
        results = []
        for suite in self.tests_ir.endpoint_suites:
            for scenario in suite.scenarios:
                result = await self._execute_scenario(scenario)
                results.append(result)

        # 3. Generate report
        return self._generate_report(results)

    async def _execute_scenario(self, scenario: TestScenarioIR) -> ScenarioResult:
        """Execute single scenario using exact path from IR."""
        # Path comes from TestsModelIR which comes from APIModelIR
        # NO path manipulation - use as-is
        url = f"{self.base_url}{scenario.endpoint_path}"
        # ... execute HTTP request
```

### 4.3 Compliance Validator

```python
# src/validation/compliance_validator_v2.py

class ComplianceValidatorV2:
    """Validate generated code against TestsModelIR."""

    def validate(
        self,
        app_dir: Path,
        tests_ir: TestsModelIR
    ) -> ComplianceReport:
        """
        Validate app against TestsModelIR expectations.

        Checks:
        1. All endpoints from tests_ir.endpoint_suites exist in app
        2. All seed entities can be created
        3. All scenarios pass with expected status
        """
        # ... implementación
```

---

## 5. Integración con ApplicationIR

### 5.1 Modificación de ApplicationIR

```python
# src/cognitive/ir/application_ir.py

class ApplicationIR(BaseModel):
    # ... existing fields ...

    # NEW: Add TestsModelIR
    tests_model: Optional[TestsModelIR] = None

    def get_tests_ir(self) -> TestsModelIR:
        """Get or generate TestsModelIR."""
        if self.tests_model is None:
            from src.cognitive.ir.tests_model_generator import TestsModelGenerator
            generator = TestsModelGenerator()
            self.tests_model = generator.generate(self)
        return self.tests_model
```

### 5.2 Sincronización Automática

```python
# Cuando se modifica APIModelIR, regenerar TestsModelIR
class ApplicationIRBuilder:

    def add_endpoint(self, endpoint: Endpoint) -> 'ApplicationIRBuilder':
        self.api_model.endpoints.append(endpoint)
        # Invalidate tests_model to force regeneration
        self._tests_model_dirty = True
        return self

    def build(self) -> ApplicationIR:
        ir = ApplicationIR(...)
        if self._tests_model_dirty or ir.tests_model is None:
            ir.tests_model = TestsModelGenerator().generate(ir)
        return ir
```

---

## 6. Resolución de Bugs Actuales

### 6.1 Bug #129/#130: `/health/health` Path

**Causa**: APIModelIR tiene `/health/health` pero código genera `/health`

**Fix con TestsModelIR**:
1. El generador de TestsModelIR lee paths de APIModelIR
2. Validación en `_validate()` compara paths de TestsModelIR con paths en código generado
3. Si hay mismatch → error antes de ejecutar tests

```python
def _validate_paths_match(self, tests_ir: TestsModelIR, generated_app_dir: Path):
    """Validate that test paths match generated code paths."""
    # Parse generated OpenAPI spec
    openapi_paths = self._extract_paths_from_generated_app(generated_app_dir)

    for suite in tests_ir.endpoint_suites:
        if suite.endpoint_path not in openapi_paths:
            raise ValidationError(
                f"Path mismatch: TestsModelIR has '{suite.endpoint_path}' "
                f"but generated app does not have this path. "
                f"Available paths: {openapi_paths}"
            )
```

### 6.2 Code Repair 0% Improvement

**Causa**: Repair y checker miden cosas diferentes

**Fix con TestsModelIR**:
1. CodeRepairAgent recibe TestsModelIR como fuente de verdad
2. Repara hacia lo que TestsModelIR espera
3. ComplianceValidator valida contra mismo TestsModelIR

```python
class CodeRepairAgentV2:
    def repair(self, app_dir: Path, tests_ir: TestsModelIR):
        """Repair code to match TestsModelIR expectations."""
        # Both repair and validation use same source of truth
        for suite in tests_ir.endpoint_suites:
            self._ensure_endpoint_exists(app_dir, suite.endpoint_path)
            for scenario in suite.scenarios:
                if scenario.scenario_type == ScenarioType.VALIDATION_ERROR:
                    self._ensure_validation_exists(app_dir, scenario)
```

### 6.3 Solo 7/35 Scenarios

**Causa**: LLM genera pocos scenarios

**Fix con TestsModelIR**:
1. Generación determinística garantiza cobertura
2. LLM solo enriquece con edge cases opcionales
3. Validación rechaza TestsModelIR con cobertura < 80%

```python
def _validate_coverage(self, tests_ir: TestsModelIR, api_model: APIModelIR):
    """Validate minimum coverage."""
    expected_endpoints = len(api_model.endpoints)
    covered_endpoints = len([s for s in tests_ir.endpoint_suites if s.coverage.has_happy_path])

    coverage = covered_endpoints / expected_endpoints
    if coverage < tests_ir.metrics.coverage_target:
        raise ValidationError(
            f"Coverage {coverage:.1%} below target {tests_ir.metrics.coverage_target:.1%}"
        )
```

---

## 7. Plan de Implementación

### Phase 1: Core TestsModelIR (2-3 días)

| Task | Archivo | Descripción |
|------|---------|-------------|
| 1.1 | `src/cognitive/ir/tests_model.py` | Definir modelos Pydantic |
| 1.2 | `src/cognitive/ir/tests_model_generator.py` | Generador determinístico |
| 1.3 | `src/cognitive/ir/application_ir.py` | Integrar tests_model |
| 1.4 | Tests unitarios | Verificar generación correcta |

### Phase 2: Consumidores (2-3 días)

| Task | Archivo | Descripción |
|------|---------|-------------|
| 2.1 | `src/services/test_code_generator_v2.py` | Generar pytest desde TestsModelIR |
| 2.2 | `src/validation/smoke_test_runner.py` | Runner que usa TestsModelIR |
| 2.3 | `src/validation/compliance_validator_v2.py` | Validador contra TestsModelIR |
| 2.4 | Migrar pipeline | Usar nuevos componentes |

### Phase 3: Deprecar LLM Planner (1-2 días)

| Task | Archivo | Descripción |
|------|---------|-------------|
| 3.1 | `src/validation/agents/planner_agent.py` | Deprecar, usar TestsModelGenerator |
| 3.2 | `src/validation/smoke_test_orchestrator.py` | Usar SmokeTestRunner |
| 3.3 | Pipeline E2E | Remover llamadas LLM para tests |

### Phase 4: Validaciones y Métricas (1-2 días)

| Task | Archivo | Descripción |
|------|---------|-------------|
| 4.1 | Validación de paths | Pre-check paths match código |
| 4.2 | Validación de coverage | Rechazar < 80% |
| 4.3 | Métricas dashboard | Mostrar coverage en reporte |

---

## 8. Métricas de Éxito

| Métrica | Actual | Target |
|---------|--------|--------|
| Smoke test pass rate | 85.7% (6/7) | 100% |
| Endpoint coverage | 20% (7/35) | 100% |
| Path sync errors | 1 (/health/health) | 0 |
| Code repair improvement | 0% | >0% cuando hay issues |
| LLM calls para tests | 1 | 0 (determinístico) |

---

## 9. Diagrama de Flujo Final

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        E2E Pipeline con TestsModelIR                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   Spec.md  ──►  SpecParser  ──►  ApplicationIR  ──►  TestsModelIR        │
│                                       │                   │               │
│                                       │                   │               │
│                                       ▼                   ▼               │
│                              CodeGeneration     TestCodeGenerator         │
│                                       │                   │               │
│                                       ▼                   ▼               │
│                              Generated App       test_*.py files         │
│                                       │                   │               │
│                                       │                   │               │
│                                       └───────┬───────────┘               │
│                                               │                           │
│                                               ▼                           │
│                              ┌────────────────────────────────┐          │
│                              │     Pre-Validation             │          │
│                              │  ✓ Paths match                 │          │
│                              │  ✓ Coverage >= 80%             │          │
│                              │  ✓ Seed data complete          │          │
│                              └────────────────────────────────┘          │
│                                               │                           │
│                                               ▼                           │
│                              ┌────────────────────────────────┐          │
│                              │     SmokeTestRunner            │          │
│                              │  Uses TestsModelIR directly    │          │
│                              │  NO LLM calls                  │          │
│                              └────────────────────────────────┘          │
│                                               │                           │
│                                               ▼                           │
│                              ┌────────────────────────────────┐          │
│                              │     ComplianceValidatorV2      │          │
│                              │  Validates against TestsModelIR│          │
│                              │  Same source of truth          │          │
│                              └────────────────────────────────┘          │
│                                               │                           │
│                                               ▼                           │
│                              ┌────────────────────────────────┐          │
│                              │     Quality Gate               │          │
│                              │  Based on TestsModelIR.metrics │          │
│                              └────────────────────────────────┘          │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Archivos a Crear/Modificar

### Nuevos Archivos

| Archivo | Propósito |
|---------|-----------|
| `src/cognitive/ir/tests_model.py` | Modelos Pydantic para TestsModelIR |
| `src/cognitive/ir/tests_model_generator.py` | Generador determinístico |
| `src/services/test_code_generator_v2.py` | Genera pytest desde TestsModelIR |
| `src/validation/smoke_test_runner.py` | Runner que usa TestsModelIR |
| `src/validation/compliance_validator_v2.py` | Validador contra TestsModelIR |

### Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `src/cognitive/ir/application_ir.py` | Agregar `tests_model: TestsModelIR` |
| `tests/e2e/real_e2e_full_pipeline.py` | Usar nuevos componentes |
| `src/validation/smoke_test_orchestrator.py` | Deprecar LLM, usar TestsModelGenerator |

### Archivos a Deprecar

| Archivo | Razón |
|---------|-------|
| `src/validation/agents/planner_agent.py` | Reemplazado por TestsModelGenerator |
| `src/services/ir_test_generator.py` | Consolidado en test_code_generator_v2.py |

---

## 11. Notas Finales

### Principios Clave

1. **Single Source of Truth**: TestsModelIR es LA fuente para todo lo relacionado a tests
2. **Determinístico**: Sin LLM para generación core, solo enriquecimiento opcional
3. **Validación Temprana**: Detectar desync antes de ejecutar tests
4. **Trazabilidad**: Cada scenario tiene `derived_from` para debugging

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Breaking change grande | Implementar en paralelo, feature flag |
| Tests existentes | Mantener compatibilidad temporal |
| Performance | TestsModelIR se genera una vez, se cachea |

### Dependencias

- ApplicationIR debe estar estable
- APIModelIR.endpoints debe tener paths correctos
- ValidationModelIR.rules debe estar completo
