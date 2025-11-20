# DevMatrix E2E Pipeline - Análisis Completo

**Fecha**: 2025-11-20
**Test de Referencia**: [real_e2e_full_pipeline.py](../tests/e2e/real_e2e_full_pipeline.py)

## 🎯 Resumen Ejecutivo

DevMatrix implementa un **pipeline cognitivo de 10 fases** que transforma especificaciones en markdown en aplicaciones FastAPI funcionales con validación semántica, repair automático y learning continuo.

**Pipeline Flow**: Spec → Parse → Classify → Plan → Atomize → DAG → Generate → **Repair** → Validate → Deploy → Learn

**Puntos Clave**:
- ✅ **Validación semántica** (no solo structural)
- ✅ **Repair loop automático** con LLM guidance
- ✅ **Learning feedback** con pattern promotion
- ✅ **Cognitive RAG** para error patterns y success patterns
- ✅ **Contract validation** entre todas las fases

---

## 📋 Las 10 Fases del Pipeline

### Phase 1: Spec Ingestion 🔵
**Archivo**: [`src/parsing/spec_parser.py`](../src/parsing/spec_parser.py)
**Duración típica**: ~2s

**Qué hace**:
- Parsea especificaciones en markdown (.md files)
- Extrae requirements funcionales (**F1. Description**)
- Extrae requirements no-funcionales (**NF1. Description**)
- Identifica **Entities** con fields, types, constraints, relationships
- Identifica **Endpoints** con methods, paths, params, responses
- Extrae **Business Logic** (validations, calculations, state machines)

**Input**: Spec file path (e.g., `tests/e2e/test_specs/simple_task_api.md`)

**Output**: `SpecRequirements` objeto con:
```python
SpecRequirements(
    requirements=[Requirement(id, type, priority, description)],
    entities=[Entity(name, fields, relationships, validations)],
    endpoints=[Endpoint(method, path, entity, operation, params)],
    business_logic=[BusinessLogic(type, description, conditions, actions)],
    metadata={'spec_name': 'Simple Task API', ...}
)
```

**Checkpoints**:
- CP-1.1: Spec loaded from file
- CP-1.2: Requirements extracted (functional/non-functional counts)
- CP-1.3: Context loaded
- CP-1.4: Complexity assessed

**Mejora clave** (Task Group 1.2):
- ❌ **Antes**: Extracción básica de 55 líneas (solo list items)
- ✅ **Ahora**: Extracción estructurada de entities, endpoints, business logic

---

### Phase 2: Requirements Analysis 🔍
**Archivo**: [`src/classification/requirements_classifier.py`](../src/classification/requirements_classifier.py)
**Duración típica**: ~3s

**Qué hace**:
- **Clasificación semántica** de requirements por domain
- Construye **dependency graph** entre requirements
- Calcula **complexity score** y **risk level**
- Búsqueda de **patterns** en PatternBank (RAG)

**Dominios detectados**:
- `crud`: Create, Read, Update, Delete operations
- `authentication`: Login, JWT, OAuth
- `payment`: Checkout, transactions, billing
- `workflow`: State machines, approvals, notifications
- `search`: Filters, pagination, sorting
- `custom`: Todo lo demás

**Output**:
```python
classified_requirements = [
    Requirement(
        id="F1",
        type="functional",
        priority="MUST",
        description="Create task endpoint",
        domain="crud",  # ← Clasificado
        complexity=0.6,  # ← Calculado
        risk_level="medium",  # ← Evaluado
        dependencies=["F2", "F3"]  # ← Graph
    ),
    ...
]
dependency_graph = {"F1": ["F2"], "F2": ["F3"], ...}
```

**Checkpoints**:
- CP-2.1: Functional requirements classified
- CP-2.2: Non-functional requirements classified
- CP-2.3: Dependencies identified (DAG validation)
- CP-2.4: Constraints extracted (complexity, risk)
- CP-2.5: Patterns matched (from PatternBank)

**Mejora clave** (Task Group 2.2):
- ❌ **Antes**: Keyword matching con 42% accuracy, 6% functional recall
- ✅ **Ahora**: Semantic classification con ≥90% accuracy, ≥90% functional recall

**PatternBank Integration**:
```python
# Busca patterns similares en RAG
results = self.pattern_bank.search_patterns(
    signature=signature,
    top_k=10,
    similarity_threshold=0.45
)
```

---

### Phase 3: Multi-Pass Planning 📐
**Archivo**: [`src/cognitive/planning/multi_pass_planner.py`](../src/cognitive/planning/multi_pass_planner.py)
**Duración típica**: ~2s

**Qué hace**:
- Crea **DAG inicial** desde requirements
- Refina **dependencies** entre nodes
- Optimiza **recursos** (memory, CPU)
- Repara **cycles** (deadlock detection)
- Valida que el DAG sea **acíclico**

**Output**:
```python
dag = {
    "nodes": [
        {"id": "node_0", "name": "Create task endpoint", "type": "requirement"},
        {"id": "node_1", "name": "List tasks endpoint", "type": "requirement"},
        ...
    ],
    "edges": [
        {"from": "node_0", "to": "node_1"},
        ...
    ],
    "waves": 3  # Número de waves paralelas
}
```

**Checkpoints**:
- CP-3.1: Initial DAG created (node count)
- CP-3.2: Dependencies refined (edge count)
- CP-3.3: Resources optimized
- CP-3.4: Cycles repaired
- CP-3.5: DAG validated (is_acyclic=True)

---

### Phase 4: Atomization ⚛️
**Duración típica**: ~2s

**Qué hace**:
- Divide DAG nodes en **atomic units** ejecutables
- Cada atom es una unidad de código independiente
- Calcula **complexity** y **LOC estimate** por atom

**Output**:
```python
atomic_units = [
    {
        "id": "node_0",
        "name": "Create task endpoint",
        "type": "code_unit",
        "complexity": 0.5,
        "loc_estimate": 30
    },
    ...
]
```

**Checkpoints**:
- CP-4.1 a CP-4.5: Steps 1-5 de atomización

**Métricas**:
- Atoms generated
- Atoms valid (~90%)
- Atoms invalid (~10%)

---

### Phase 5: DAG Construction 🔗
**Archivo**: [`src/cognitive/planning/dag_builder.py`](../src/cognitive/planning/dag_builder.py)
**Duración típica**: ~2s

**Qué hace**:
- Construye **DAG final** con nodes + edges
- Organiza en **waves** (grupos paralelos)
- Prepara para wave execution

**Output**:
```python
{
    "nodes": [...],  # Atomic units
    "edges": [...],  # Dependencies
    "waves": [
        [atom1, atom2, atom3],  # Wave 1 (parallel)
        [atom4, atom5],         # Wave 2 (parallel)
        [atom6]                 # Wave 3
    ],
    "wave_count": 3
}
```

**Checkpoints**:
- CP-5.1 a CP-5.5: Steps 1-5 de construcción

---

### Phase 6: Code Generation 🌊
**Archivo**: [`src/services/code_generation_service.py`](../src/services/code_generation_service.py)
**Duración típica**: ~15-30s (LLM call)

**Qué hace**:
- **Genera código real** desde SpecRequirements usando LLM
- Método clave: `generate_from_requirements(spec_requirements)`
- Construye **prompt comprehensivo** con entities, endpoints, business logic
- Valida **sintaxis** del código generado
- Integra con **cognitive feedback loop**

**Prompt Construction** (Task Group 3.1.3):
```python
def _build_requirements_prompt(spec_requirements):
    """
    Genera prompt detallado con:
    - ENTITIES: fields, types, constraints, relationships
    - ENDPOINTS: methods, paths, params, responses, business logic
    - BUSINESS LOGIC: validations, calculations, state machines
    - GENERATION INSTRUCTIONS: Pydantic models, FastAPI routes, error handling
    """
```

**System Prompt** (Task Group 3.1.3):
```
You are an expert FastAPI backend engineer.

CRITICAL RULES:
1. Specification Compliance: ONLY generate entities/endpoints from spec
   - If spec says Product/Cart/Order → generate Product/Cart/Order (NOT Task)
2. Pydantic Models: Complete models with validators
3. FastAPI Routes: ALL endpoints with proper CRUD logic
4. Business Logic: Implement ALL validations and rules
5. Error Handling: HTTPException(404, 400, 422)
6. Code Quality: NO TODO, NO placeholders, Complete implementations
```

**LLM Call** (con caching):
```python
response = await self.llm_client.generate_with_caching(
    task_type="task_execution",
    complexity="high",
    cacheable_context={"system_prompt": system_prompt},
    variable_prompt=prompt,
    temperature=0.0,  # Deterministic
    max_tokens=4000,
    timeout=120.0  # 2 minutos
)
```

**Output**:
```python
generated_code = {
    "main.py": "...",  # Complete FastAPI app
    "requirements.txt": "fastapi==0.109.0\nuvicorn==0.27.0\n...",
    "README.md": "# Simple Task API\n..."
}
```

**Checkpoints**:
- CP-6.1: Code generation started
- CP-6.2: Models generated (files count)
- CP-6.3: Routes generated
- CP-6.4: Tests generated
- CP-6.5: Code generation complete

**Mejora clave** (Task Group 3.2):
- ❌ **Antes**: Hardcoded Task API template para TODOS los specs
- ✅ **Ahora**: Genera código real basado en SpecRequirements

**Feature Flag**:
```python
USE_REAL_CODE_GENERATION=true  # Default ON
```

**Cognitive Integrations**:
1. **Pattern Promotion Pipeline** (Milestone 4)
   ```python
   candidate_id = self.pattern_feedback.register_successful_generation(
       code=code,
       signature=signature,
       execution_result=execution_result,
       task_id=task_id
   )
   ```

2. **DAG Synchronization** (Milestone 3)
   ```python
   self.dag_synchronizer.sync_execution_metrics(
       task_id=task_id,
       execution_metrics=metrics
   )
   ```

3. **Error Pattern Store** (Legacy)
   ```python
   await self.pattern_store.store_success(success_pattern)
   await self.pattern_store.store_error(error_pattern)
   ```

**Retry Logic con RAG**:
```python
# En retry attempts, consulta cognitive feedback loop
if attempt > 1 and self.enable_feedback_loop:
    # Busca errores similares en history
    similar_errors = await self.pattern_store.search_similar_errors(
        task_description=task.description,
        error_message=str(last_error),
        top_k=3
    )

    # Busca patterns exitosos
    successful_patterns = await self.pattern_store.search_successful_patterns(
        task_description=task.description,
        top_k=5
    )

    # Genera prompt mejorado con feedback
    prompt = self._build_prompt_with_feedback(
        task, similar_errors, successful_patterns, str(last_error)
    )
```

---

### Phase 6.5: Code Repair 🔧 (NEW - Task Group 4)
**Archivos**:
- [`src/validation/compliance_validator.py`](../src/validation/compliance_validator.py)
- [`tests/e2e/adapters/test_result_adapter.py`](../tests/e2e/adapters/test_result_adapter.py)
- [`src/mge/v2/agents/code_repair_agent.py`](../src/mge/v2/agents/code_repair_agent.py) (stub)

**Duración típica**: ~0-90s (0s si compliance ≥ 0.80, hasta 3 iterations si < 0.80)

**Qué hace**:
- **Pre-check** de compliance con ComplianceValidator
- **Skip logic**: Si compliance ≥ 80%, skip repair (fast path)
- **Repair loop** iterativo (max 3 iterations):
  1. Analyze failures
  2. Search RAG for similar patterns
  3. **Generate repair proposal** usando LLM con contexto completo
  4. Create backup
  5. Apply repair
  6. Re-validate compliance
  7. Check for regression (rollback si compliance baja)
  8. Store repair attempt en ErrorPatternStore

**Architecture**:
```
CP-6.5.1: ComplianceValidator pre-check
    ↓
[Skip if compliance ≥ 0.80]
    ↓
CP-6.5.2: Initialize dependencies (TestResultAdapter, ErrorPatternStore)
    ↓
CP-6.5.3: Convert ComplianceReport → TestResult (Adapter)
    ↓
CP-6.5.4: Execute repair loop (REAL - LLM-guided)
    ↓
CP-6.5.5: Collect metrics (iterations, improvement, tests_fixed)
```

**Repair Loop** (CP-6.5.4):
```python
async def _execute_repair_loop(
    initial_compliance_report,
    test_results: List,
    main_code: str,
    max_iterations: int = 3,
    precision_target: float = 0.88
) -> Dict[str, Any]:
    """
    Loop iterativo con:
    - Early exit si compliance ≥ precision_target (0.88)
    - Early exit si no improvement por 2 consecutive iterations
    - Regression detection → rollback a backup
    - Pattern storage (success/error)
    """

    for iteration in range(max_iterations):
        # Step 3: Generate repair proposal (REAL LLM)
        repair_proposal = await self._generate_repair_proposal(
            compliance_report=initial_compliance_report,
            spec_requirements=self.spec_requirements,
            test_results=test_results,
            current_code=current_code,
            iteration=iteration
        )

        # Step 5: Apply repair
        repaired_code = self._apply_repair_to_code(current_code, repair_proposal)

        # Step 6: Re-validate
        new_compliance = self.compliance_validator.validate(
            spec_requirements=self.spec_requirements,
            generated_code=repaired_code
        )

        # Step 7: Check regression
        if new_compliance.overall_compliance < current_compliance:
            # ROLLBACK!
            regressions_detected += 1
            continue

        # No regression → update state
        current_code = repaired_code
        best_code = repaired_code
        tests_fixed = calculate_tests_fixed(...)

    return {
        "repair_applied": True,
        "iterations": iterations_executed,
        "improvement": final_compliance - initial_compliance,
        "tests_fixed": tests_fixed,
        "regressions_detected": regressions_detected,
        "final_code": best_code
    }
```

**Repair Proposal Generation** (ROOT CAUSE fix):
```python
async def _generate_repair_proposal(
    compliance_report,
    spec_requirements: SpecRequirements,  # FULL spec context
    test_results: List,
    current_code: str,
    iteration: int
) -> str:
    """
    CRITICAL FIX: Usa REAL LLM con FULL spec context

    Antes: Placeholder que retornaba código sin cambios
    Ahora: Genera código reparado REAL usando LLM
    """

    # Build detailed failure context
    missing_entities = [...]
    wrong_entities = [...]
    missing_endpoints = [...]

    repair_context = f"""
CODE REPAIR ITERATION {iteration + 1}

COMPLIANCE ANALYSIS:
- Overall Compliance: {compliance_report.overall_compliance:.1%}
- Missing entities: {', '.join(missing_entities)}
- WRONG entities (not in spec): {', '.join(wrong_entities)}
- Missing endpoints: {', '.join(missing_endpoints)}

CRITICAL REPAIR INSTRUCTIONS:
1. Generate ONLY the entities specified in the spec
2. Do NOT create Base/Update/Create variants unless EXPLICITLY specified
3. Include ALL required endpoints
4. Follow EXACT entity and endpoint names from spec
5. Fix syntax errors if any exist
6. Preserve working code from previous iteration

CURRENT CODE TO REPAIR:
{current_code}

GENERATE COMPLETE REPAIRED CODE BELOW:
"""

    # CRITICAL: Use LLM to generate repaired code
    repaired_code = await self.code_generator.generate_from_requirements(
        spec_requirements,
        allow_syntax_errors=False,
        repair_context=repair_context  # ← Guía para el LLM
    )

    return repaired_code
```

**Checkpoints**:
- CP-6.5.1: Pre-check complete (compliance_score)
- CP-6.5.SKIP: Skipping repair (high compliance) [si ≥ 0.80]
- CP-6.5.2: Dependencies initialized
- CP-6.5.3: Test results adapted (failure count)
- CP-6.5.4: Repair loop executed (iterations, improvement)
- CP-6.5.5: Metrics collected

**Métricas**:
```python
self.metrics_collector.metrics.repair_applied = True/False
self.metrics_collector.metrics.repair_iterations = 0-3
self.metrics_collector.metrics.repair_improvement = -1.0 to 1.0
self.metrics_collector.metrics.tests_fixed = 0-N
self.metrics_collector.metrics.regressions_detected = 0-N
self.metrics_collector.metrics.pattern_reuse_count = 0-N
self.metrics_collector.metrics.repair_time_ms = ...
```

**Mejora clave** (Task Group 4):
- ❌ **Antes**: Phase 6.5 con 0% effectiveness (placeholder repair)
- ✅ **Ahora**: REAL LLM-guided repair con full spec context y regression detection

---

### Phase 7: Validation ✅
**Archivo**: [`src/validation/compliance_validator.py`](../src/validation/compliance_validator.py)
**Duración típica**: ~2s

**Qué hace**:
- **Structural validation** (files exist, syntax valid)
- **Semantic validation** (entities, endpoints, business logic match spec)
- Calcula **compliance score** por categoría
- **FAIL** si overall compliance < threshold (default 0.80)

**ComplianceValidator**:
```python
def validate(
    spec_requirements: SpecRequirements,
    generated_code: str
) -> ComplianceReport:
    """
    1. Extract what was implemented (CodeAnalyzer)
       - entities_found = extract_models(code)
       - endpoints_found = extract_endpoints(code)
       - validations_found = extract_validations(code)

    2. Extract what was expected (from spec)
       - entities_expected = [e.name for e in spec.entities]
       - endpoints_expected = [f"{ep.method} {ep.path}" for ep in spec.endpoints]

    3. Calculate compliance per category
       - entity_compliance = found / expected
       - endpoint_compliance = found / expected
       - validation_compliance = found / expected

    4. Overall compliance (weighted average)
       - 40% entities + 40% endpoints + 20% validations

    5. Identify missing requirements
    """
```

**CodeAnalyzer** (extracción de código):
```python
class CodeAnalyzer:
    def extract_models(self, code: str) -> List[str]:
        """Extract Pydantic class names: class Product(BaseModel):"""

    def extract_endpoints(self, code: str) -> List[str]:
        """Extract FastAPI routes: @app.post("/products")"""

    def extract_validations(self, code: str) -> List[str]:
        """Extract validators: Field(gt=0), @field_validator"""
```

**ComplianceReport**:
```python
@dataclass
class ComplianceReport:
    overall_compliance: float  # 0.0-1.0

    entities_implemented: List[str]  # ["Product", "Cart"]
    entities_expected: List[str]     # ["Product", "Cart", "Order"]

    endpoints_implemented: List[str]  # ["POST /products"]
    endpoints_expected: List[str]     # ["POST /products", "GET /products"]

    validations_implemented: List[str]
    validations_expected: List[str]

    missing_requirements: List[str]  # ["Order entity", "GET /products"]

    compliance_details: Dict[str, float]  # {"entities": 0.67, "endpoints": 0.50}
```

**validate_or_raise()** (Task Group 4.2.3):
```python
def validate_or_raise(
    spec_requirements: SpecRequirements,
    generated_code: str,
    threshold: float = 0.80
) -> ComplianceReport:
    """
    Valida y RAISE exception si compliance < threshold

    Raises:
        ComplianceValidationError: Si overall_compliance < threshold
    """
    report = self.validate(spec_requirements, generated_code)

    if report.overall_compliance < threshold:
        raise ComplianceValidationError(
            f"Compliance {report.overall_compliance:.1%} "
            f"below threshold {threshold:.1%}\n"
            f"Missing: {report.missing_requirements}"
        )

    return report
```

**Checkpoints**:
- CP-7.1: File structure validated (files count)
- CP-7.2: Syntax validation
- CP-7.3: **Semantic validation complete** (compliance_score)
- CP-7.4: Business logic validation
- CP-7.5: Test generation check
- CP-7.6: Quality metrics

**Mejora clave** (Task Group 4.2):
- ❌ **Antes**: Solo structural checks (files exist, syntax valid)
- ✅ **Ahora**: Structural + **Semantic validation** (entities, endpoints match spec)
- ❌ **Antes**: Tests pasan con wrong code (Task entity en spec de Products)
- ✅ **Ahora**: FAIL si wrong code (ComplianceValidationError)

**Configurable Threshold**:
```bash
COMPLIANCE_THRESHOLD=0.80  # Default 80%
```

---

### Phase 8: Deployment 📦
**Duración típica**: ~1s

**Qué hace**:
- Guarda **todos los archivos generados** a disco
- Crea **directory structure**
- Output: `tests/e2e/generated_apps/{spec_name}_{timestamp}/`

**Files saved**:
```
generated_apps/simple_task_api_1763634331/
├── main.py               # Complete FastAPI app
├── requirements.txt      # Dependencies
└── README.md            # How to run
```

**Checkpoints**:
- CP-8.1: Files saved to disk (output_dir)
- CP-8.2: Directory structure created
- CP-8.3: README generated
- CP-8.4: Dependencies documented
- CP-8.5: Deployment complete

---

### Phase 9: Health Verification 🏥
**Duración típica**: ~1s

**Qué hace**:
- Verifica que **expected files** existan en output_dir
- File existence checks

**Expected files**:
- `main.py`
- `requirements.txt`
- `README.md`

**Checkpoints**:
- CP-9.1 a CP-9.5: Steps 1-5 de health checks

---

### Phase 10: Learning 🧠
**Archivo**: [`src/cognitive/patterns/pattern_feedback_integration.py`](../src/cognitive/patterns/pattern_feedback_integration.py)
**Duración típica**: ~2s

**Qué hace**:
- Registra **código exitoso** como pattern candidate
- Check de **patterns ready for promotion**
- Promoción automática a PatternBank si threshold alcanzado
- Métricas de learning

**PatternFeedbackIntegration**:
```python
class PatternFeedbackIntegration:
    """
    Pipeline de promoción de patterns (Milestone 4)

    Candidato → Dual Validation → Promotion → PatternBank
    """

    def register_successful_generation(
        self,
        code: str,
        signature: SemanticTaskSignature,
        execution_result: ExecutionResult,
        task_id: UUID,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Registra código exitoso como candidate

        Returns:
            candidate_id: UUID del candidate
        """

    def check_and_promote_ready_patterns(self) -> Dict[str, int]:
        """
        Chequea candidates listos para promoción

        Criteria:
        - success_count ≥ MIN_SUCCESS_COUNT (default 3)
        - No validation errors

        Returns:
            {
                "total_candidates": 10,
                "promotions_succeeded": 2,
                "promotions_failed": 0
            }
        """
```

**Checkpoints**:
- CP-10.1: Execution status assessed (successful: True/False)
- CP-10.2: Pattern registered (candidate_id)
- CP-10.3: Checking promotion candidates
- CP-10.4: Promotion check complete (candidates, promotions)
- CP-10.5: Learning phase complete

**Métricas**:
```python
self.metrics_collector.metrics.patterns_stored = 1
self.metrics_collector.metrics.patterns_promoted = 2
self.metrics_collector.metrics.candidates_created = 1
```

---

## 🔗 Integraciones Principales

### 1. StatefulWorkflow (LangGraph)
**Archivo**: [`src/workflows/stateful_workflow.py`](../src/workflows/stateful_workflow.py)

**Qué hace**:
- Workflow con **LangGraph**
- **Redis**: temporary workflow state
- **PostgreSQL**: persistent task tracking
- **Cost tracking** integration

**Componentes**:
```python
class StatefulWorkflow:
    def __init__(self, redis_manager, postgres_manager):
        self.redis = redis_manager or RedisManager()
        self.postgres = postgres_manager or PostgresManager()

    def create_agent_node(self, agent_name: str):
        """
        Agent node con:
        - Save state to Redis
        - Track execution in PostgreSQL
        - Cost tracking per task
        """

    def run_workflow(self, user_request: str):
        """
        Ejecuta workflow:
        1. Create project in PostgreSQL
        2. Generate workflow_id
        3. Save initial state to Redis
        4. Execute workflow
        5. Return final state + project_id + task_id
        """
```

**State Management**:
```python
# Redis: workflow state (temporary, TTL)
self.redis.save_workflow_state(workflow_id, state_dict)
state = self.redis.get_workflow_state(workflow_id)

# PostgreSQL: task tracking (persistent)
task_id = self.postgres.create_task(
    project_id=project_id,
    agent_name=agent_name,
    task_type="summary",
    input_data={"user_request": user_request}
)
self.postgres.update_task_status(task_id, status="in_progress")
self.postgres.update_task_status(task_id, status="completed", output_data={...})

# Cost tracking
cost_id = self.postgres.track_cost(
    task_id=task_id,
    model_name="claude-sonnet-4-5",
    input_tokens=1000,
    output_tokens=500,
    cost_usd=0.05
)
```

---

### 2. Cognitive Services (RAG + Learning)

#### PatternBank
**Archivo**: [`src/cognitive/patterns/pattern_bank.py`](../src/cognitive/patterns/pattern_bank.py)

**Qué hace**:
- Store de **success patterns** y **error patterns**
- **Semantic search** con embeddings
- **Pattern reuse** en code generation

**API**:
```python
# Search patterns by semantic similarity
results = pattern_bank.search_patterns(
    signature=SemanticTaskSignature(
        purpose="Create CRUD API for tasks",
        intent="create",
        domain="crud"
    ),
    top_k=10,
    similarity_threshold=0.45
)

# Store new pattern
pattern_bank.store_pattern(
    pattern=StoredPattern(
        code="...",
        signature=signature,
        metadata={...}
    )
)
```

#### ErrorPatternStore
**Archivo**: [`src/services/error_pattern_store.py`](../src/services/error_pattern_store.py)

**Qué hace**:
- Store de **error patterns** (failures)
- Store de **success patterns** (working code)
- **RAG search** en retry loops

**API**:
```python
# Store error
await error_pattern_store.store_error(
    ErrorPattern(
        error_id=uuid4(),
        task_id=task_id,
        task_description="Create product endpoint",
        error_type="syntax_error",
        error_message="SyntaxError: invalid syntax",
        failed_code="class Product\n  def __init__(...):",  # Incomplete
        attempt=1,
        timestamp=datetime.now()
    )
)

# Store success
await error_pattern_store.store_success(
    SuccessPattern(
        success_id=uuid4(),
        task_id=task_id,
        task_description="Create product endpoint",
        generated_code="class Product(BaseModel):\n  ...",
        quality_score=0.95,
        timestamp=datetime.now()
    )
)

# Search similar errors
similar_errors = await error_pattern_store.search_similar_errors(
    task_description="Create product endpoint",
    error_message="SyntaxError: invalid syntax",
    top_k=3
)

# Search successful patterns
successful_patterns = await error_pattern_store.search_successful_patterns(
    task_description="Create product endpoint",
    top_k=5
)
```

#### PatternFeedbackIntegration (Milestone 4)
**Archivo**: [`src/cognitive/patterns/pattern_feedback_integration.py`](../src/cognitive/patterns/pattern_feedback_integration.py)

**Qué hace**:
- **Pattern promotion pipeline**: Candidate → Dual Validation → Promotion
- **Auto-promotion** cuando success_count ≥ threshold
- Integration con PatternBank

**Pipeline**:
```
Successful Code Generation
    ↓
[Register as Candidate]
    candidate_id = register_successful_generation(code, signature)
    ↓
[Accumulate Success Count]
    success_count++
    ↓
[Check Promotion Criteria]
    if success_count ≥ MIN_SUCCESS_COUNT (3):
        ↓
    [Dual Validation]
        syntactic_validation (compile check)
        semantic_validation (spec compliance)
        ↓
    [Promote to PatternBank]
        pattern_bank.store_pattern(promoted_pattern)
```

---

### 3. Metrics & Observability

#### MetricsCollector
**Archivo**: [`tests/e2e/metrics_framework.py`](../tests/e2e/metrics_framework.py)

**Qué hace**:
- Colecta métricas de **todas las fases**
- Tracking de **checkpoints** por fase
- **Duration** por fase
- **Error tracking** con criticality levels

**API**:
```python
metrics = MetricsCollector(
    pipeline_id="real_e2e_1763634331",
    spec_name="simple_task_api"
)

# Phase tracking
metrics.start_phase("spec_ingestion")
metrics.add_checkpoint("spec_ingestion", "CP-1.1: Spec loaded", {})
metrics.complete_phase("spec_ingestion")

# Error tracking
metrics.record_error("code_generation", {"error": str(e)}, critical=True)

# Finalize
final_metrics = metrics.finalize()
# Output: {
#   "overall_status": "success",
#   "total_duration_ms": 45231,
#   "phases": {
#     "spec_ingestion": {"duration_ms": 2345, "checkpoints": [...]},
#     ...
#   }
# }
```

#### PrecisionMetrics
**Archivo**: [`tests/e2e/precision_metrics.py`](../tests/e2e/precision_metrics.py)

**Qué hace**:
- Cálculo de **accuracy, precision, recall, F1**
- Métricas por categoría:
  - Pattern matching
  - Classification
  - DAG construction
  - Atomization
  - Execution
  - Validation

**Métricas**:
```python
precision = PrecisionMetrics()

# Pattern matching
precision.patterns_expected = 10
precision.patterns_found = 8
precision.patterns_correct = 7
precision.patterns_incorrect = 1
precision.patterns_missed = 3

# Calculos
pattern_precision = precision.calculate_pattern_precision()  # 7 / 8 = 0.875
pattern_recall = precision.calculate_pattern_recall()        # 7 / 10 = 0.70
pattern_f1 = precision.calculate_pattern_f1()                # 2 * (0.875 * 0.70) / (0.875 + 0.70)

# Classification
precision.requirements_total = 17
precision.requirements_classified = 17
precision.requirements_correct = 16
classification_accuracy = precision.calculate_classification_accuracy()  # 16 / 17 = 0.94

# Overall
overall_precision = precision.calculate_overall_precision()
overall_accuracy = precision.calculate_accuracy()
```

#### ContractValidator
**Archivo**: [`tests/e2e/precision_metrics.py`](../tests/e2e/precision_metrics.py)

**Qué hace**:
- Valida **contract de cada phase**
- Verifica que **output esperado** esté presente
- Tracking de **violations**

**Contracts**:
```python
phase_contracts = {
    "spec_ingestion": {
        "required_keys": ["spec_content", "requirements", "complexity"],
        "type_checks": {
            "complexity": float,
            "requirements": list
        }
    },
    "requirements_analysis": {
        "required_keys": ["functional_reqs", "non_functional_reqs", "patterns_matched"],
        "validation_rules": {
            "functional_reqs_count": lambda x: len(x) > 0,
            "classification_accuracy": lambda x: 0 <= x <= 1.0
        }
    },
    "validation": {
        "required_keys": ["tests_run", "tests_passed", "compliance_score"],
        "validation_rules": {
            "compliance_score": lambda x: 0 <= x <= 1.0,
            "tests_passed": lambda x: x >= 0
        }
    }
}
```

---

## 🎨 Patrones de Diseño

### 1. Strategy Pattern

**PromptStrategyFactory**:
```python
# Diferentes strategies por tipo de archivo
class PromptStrategyFactory:
    @staticmethod
    def get_strategy(file_type: FileType):
        if file_type == FileType.PYTHON:
            return PythonPromptStrategy()
        elif file_type == FileType.MARKDOWN:
            return MarkdownPromptStrategy()
        elif file_type == FileType.YAML:
            return YamlPromptStrategy()
        # ...

# Usage
file_type_detection = detector.detect(task_name, task_description)
strategy = PromptStrategyFactory.get_strategy(file_type_detection.file_type)
prompt = strategy.generate_prompt(context)
```

**ValidationStrategyFactory**:
```python
# Validación por tipo de archivo
class ValidationStrategyFactory:
    @staticmethod
    def get_strategy(file_type: FileType):
        if file_type == FileType.PYTHON:
            return PythonValidationStrategy()  # compile() check
        elif file_type == FileType.YAML:
            return YamlValidationStrategy()    # yaml.safe_load() check
        # ...

# Usage
validator = ValidationStrategyFactory.get_strategy(file_type)
is_valid, error_message = validator.validate(code)
```

### 2. Pipeline Pattern

**10 fases secuenciales** con:
- Checkpoints por fase
- Contract validation entre fases
- Error propagation
- Metrics collection

```python
try:
    # Phase 1
    await self._phase_1_spec_ingestion()

    # Phase 2
    await self._phase_2_requirements_analysis()

    # ...

    # Phase 10
    await self._phase_10_learning()

except Exception as e:
    self.metrics_collector.record_error("pipeline", {"error": str(e)}, critical=True)
finally:
    await self._finalize_and_report()
```

### 3. Retry Pattern

**Exponential backoff** con cognitive feedback:
```python
for attempt in range(1, max_retries + 1):
    try:
        # En retry attempts, consulta RAG
        if attempt > 1 and self.enable_feedback_loop:
            similar_errors = await self.pattern_store.search_similar_errors(...)
            successful_patterns = await self.pattern_store.search_successful_patterns(...)
            prompt = self._build_prompt_with_feedback(task, similar_errors, successful_patterns)
        else:
            prompt = self._build_prompt(task)

        # Generate code
        response = await self.llm_client.generate_with_caching(...)
        code = self._extract_code(response)

        # Success!
        return {"success": True, "code": code}

    except Exception as e:
        last_error = e

        # Store error pattern
        await self.pattern_store.store_error(error_pattern)

        # Exponential backoff
        await asyncio.sleep(2 ** attempt)
```

### 4. Observer Pattern

**MetricsCollector** observa todas las fases:
```python
# Phase start
metrics.start_phase("code_generation")

# Checkpoints durante phase
metrics.add_checkpoint("code_generation", "CP-6.1: Code generation started", {})
metrics.add_checkpoint("code_generation", "CP-6.2: Models generated", {"files": 3})

# Phase complete
metrics.complete_phase("code_generation")

# Error tracking
metrics.record_error("code_generation", {"error": str(e)}, critical=False)
```

### 5. Repository Pattern

**PostgresManager**:
```python
class PostgresManager:
    def create_project(self, name: str, description: str) -> UUID:
        """Create project record"""

    def create_task(self, project_id: UUID, agent_name: str, ...) -> UUID:
        """Create task record"""

    def update_task_status(self, task_id: UUID, status: str, ...) -> None:
        """Update task status"""

    def track_cost(self, task_id: UUID, model_name: str, ...) -> UUID:
        """Track LLM cost"""

    def get_task(self, task_id: UUID) -> Dict:
        """Get task by ID"""
```

**RedisManager**:
```python
class RedisManager:
    def save_workflow_state(self, workflow_id: str, state: Dict) -> None:
        """Save workflow state with TTL"""

    def get_workflow_state(self, workflow_id: str) -> Dict | None:
        """Get workflow state"""
```

---

## 📊 Métricas de Calidad

### 1. Precision Metrics

**Pattern Matching**:
- **Precision**: `patterns_correct / patterns_found`
- **Recall**: `patterns_correct / patterns_expected`
- **F1-Score**: `2 * (precision * recall) / (precision + recall)`

**Classification**:
- **Accuracy**: `requirements_correct / requirements_total`
- **Functional Recall**: `functional_correct / functional_expected`

**DAG Construction**:
- **Node Accuracy**: `dag_nodes_created / dag_nodes_expected`
- **Edge Accuracy**: `dag_edges_created / dag_edges_expected`

**Atomization**:
- **Quality**: `atoms_valid / atoms_generated`

**Execution**:
- **Success Rate**: `atoms_succeeded / atoms_executed`
- **Recovery Rate**: `atoms_recovered / atoms_failed_first_try`

**Validation**:
- **Test Pass Rate**: `tests_passed / tests_executed`

**Overall**:
- **Accuracy**: `successful_operations / total_operations`
- **Precision**: Average of all precision metrics

### 2. Compliance Metrics

**Semantic Compliance**:
- **Overall**: `(entity_compliance * 0.40) + (endpoint_compliance * 0.40) + (validation_compliance * 0.20)`
- **Entity Compliance**: `entities_found / entities_expected`
- **Endpoint Compliance**: `endpoints_found / endpoints_expected`
- **Validation Compliance**: `validations_found / validations_expected`

**Threshold**:
- Default: **0.80** (80%)
- Configurable: `COMPLIANCE_THRESHOLD` env var

### 3. Performance Metrics

**Duration**:
- Total pipeline duration (ms)
- Duration per phase (ms)
- LLM call duration (s)

**Token Usage**:
- Input tokens
- Output tokens
- Cached tokens
- Cost (USD)

**Repair Metrics** (Phase 6.5):
- `repair_applied`: bool
- `repair_iterations`: 0-3
- `repair_improvement`: -1.0 to 1.0
- `tests_fixed`: 0-N
- `regressions_detected`: 0-N
- `pattern_reuse_count`: 0-N
- `repair_time_ms`: ...

**Learning Metrics** (Phase 10):
- `patterns_stored`: count
- `patterns_promoted`: count
- `candidates_created`: count

---

## 🔧 Puntos de Extensión

### 1. Agregar nuevos File Types

**PromptStrategyFactory**:
```python
# src/services/prompt_strategies.py

class TypeScriptPromptStrategy(PromptStrategy):
    def generate_prompt(self, context: PromptContext) -> str:
        """Generate TypeScript-specific prompt"""
        return f"""Generate TypeScript code for:
Task: {context.task_name}
Description: {context.task_description}

Requirements:
- Use strict typing
- Add JSDoc comments
- Follow Airbnb style guide
...
"""

# Register in factory
class PromptStrategyFactory:
    @staticmethod
    def get_strategy(file_type: FileType):
        if file_type == FileType.TYPESCRIPT:
            return TypeScriptPromptStrategy()
        # ...
```

### 2. Agregar nuevos Validators

**ValidationStrategyFactory**:
```python
# src/services/validation_strategies.py

class TypeScriptValidationStrategy(ValidationStrategy):
    def validate(self, code: str) -> tuple[bool, str]:
        """Validate TypeScript syntax"""
        try:
            # Run tsc --noEmit on code
            result = subprocess.run(
                ["tsc", "--noEmit"],
                input=code,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False, result.stderr
            return True, ""
        except Exception as e:
            return False, str(e)

# Register in factory
class ValidationStrategyFactory:
    @staticmethod
    def get_strategy(file_type: FileType):
        if file_type == FileType.TYPESCRIPT:
            return TypeScriptValidationStrategy()
        # ...
```

### 3. Agregar nuevos Domains

**DomainPatterns**:
```python
# src/classification/requirements_classifier.py

class DomainPatterns:
    # Existing domains...

    # NEW domain
    ANALYTICS = [
        "metric",
        "dashboard",
        "report",
        "analytics",
        "tracking",
        "kpi",
        "visualization"
    ]

    @classmethod
    def get_all_keywords(cls) -> Dict[str, List[str]]:
        return {
            "crud": [...],
            "authentication": [...],
            "analytics": cls.ANALYTICS,  # ← New
        }
```

### 4. Extender Repair Strategies

**CodeRepairAgent**:
```python
# src/mge/v2/agents/code_repair_agent.py

class CodeRepairAgent:
    async def repair_with_strategy(
        self,
        code: str,
        compliance_report: ComplianceReport,
        strategy: str = "llm_guided"
    ) -> str:
        """
        Repair with different strategies:
        - llm_guided: Use LLM with full spec context (current)
        - template_based: Use templates for common patterns
        - rule_based: Apply rule-based fixes
        - hybrid: Combine multiple strategies
        """
        if strategy == "llm_guided":
            return await self._llm_guided_repair(code, compliance_report)
        elif strategy == "template_based":
            return await self._template_based_repair(code, compliance_report)
        # ...
```

### 5. Agregar nuevas Metrics

**MetricsCollector**:
```python
# tests/e2e/metrics_framework.py

class PipelineMetrics:
    # Existing metrics...

    # NEW metrics
    llm_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0
    code_quality_score: float = 0.0
    security_issues_found: int = 0

# Usage
metrics.metrics.llm_latency_ms = (end_time - start_time) * 1000
metrics.metrics.cache_hit_rate = cached_tokens / (input_tokens + cached_tokens)
```

---

## 🎯 Key Takeaways

### ✅ Lo que hace bien

1. **Pipeline comprehensivo**: 10 fases que cubren spec → code → validation → learning
2. **Semantic validation**: No solo structural, valida que código matchee spec
3. **Repair automático**: Loop de reparación con LLM guidance
4. **RAG integration**: Error patterns y success patterns para retry logic
5. **Learning continuo**: Pattern promotion pipeline con auto-promotion
6. **Observability**: Métricas detalladas en todas las fases
7. **Contract validation**: Verifica output de cada fase
8. **Cognitive feedback**: Integration con PatternBank, ErrorPatternStore
9. **State management**: Redis (temp) + PostgreSQL (persistent)
10. **Cost tracking**: Track de tokens y USD por task

### 🔴 Áreas de mejora

1. **Phase 3-5**: MultiPassPlanner, Atomization, DAGBuilder están simplificados en test
   - DAG real probablemente más complejo
   - Atomization podría beneficiarse de AST parsing

2. **CodeRepairAgent**: Stub implementation (solo se usa repair loop directo en test)
   - Podría encapsular logic de repair loop
   - Permitiría diferentes repair strategies

3. **Phase 10 Learning**: Integration con PatternBank funciona, pero promotion criteria podrían ser más sofisticados
   - success_count ≥ 3 es heurístico simple
   - Podría usar quality_score, execution_time, etc.

4. **Metrics**: PrecisionMetrics tracking manual (calcular expected vs found)
   - Podría auto-calcularse desde ComplianceReport

5. **Test coverage**: E2E test cubre happy path, pero faltan tests de:
   - Error scenarios (LLM timeout, syntax errors que no se pueden repair, etc.)
   - Regression detection en repair loop
   - Pattern promotion edge cases

### 🚀 Próximos pasos sugeridos

1. **Implementar CodeRepairAgent completo** como clase standalone
2. **Agregar más repair strategies** (template-based, rule-based)
3. **Mejorar MultiPassPlanner** con planning real (no simplificado)
4. **Agregar E2E tests** para error scenarios
5. **Dashboard de métricas** para visualizar pipeline performance
6. **Incremental learning**: Store de patterns exitosos en producción
7. **A/B testing**: Compare diferentes prompt strategies
8. **Monitoring**: Alertas cuando compliance < threshold consistentemente

---

## 📚 Referencias

### Archivos Clave

**Pipeline Core**:
- [`tests/e2e/real_e2e_full_pipeline.py`](../tests/e2e/real_e2e_full_pipeline.py) - Test E2E completo

**Phase Implementations**:
- [`src/parsing/spec_parser.py`](../src/parsing/spec_parser.py) - Phase 1
- [`src/classification/requirements_classifier.py`](../src/classification/requirements_classifier.py) - Phase 2
- [`src/cognitive/planning/multi_pass_planner.py`](../src/cognitive/planning/multi_pass_planner.py) - Phase 3
- [`src/cognitive/planning/dag_builder.py`](../src/cognitive/planning/dag_builder.py) - Phase 5
- [`src/services/code_generation_service.py`](../src/services/code_generation_service.py) - Phase 6
- [`src/validation/compliance_validator.py`](../src/validation/compliance_validator.py) - Phase 6.5 & 7

**Infrastructure**:
- [`src/workflows/stateful_workflow.py`](../src/workflows/stateful_workflow.py) - LangGraph workflow
- [`src/cognitive/patterns/pattern_bank.py`](../src/cognitive/patterns/pattern_bank.py) - Pattern storage
- [`src/services/error_pattern_store.py`](../src/services/error_pattern_store.py) - Error/Success patterns

**Metrics & Testing**:
- [`tests/e2e/metrics_framework.py`](../tests/e2e/metrics_framework.py) - Metrics collection
- [`tests/e2e/precision_metrics.py`](../tests/e2e/precision_metrics.py) - Precision calculation

### Task Groups Completados

- ✅ **Task Group 1.2**: SpecParser con extracción estructurada
- ✅ **Task Group 2.2**: RequirementsClassifier con semantic classification
- ✅ **Task Group 3.1**: CodeGenerationService con generate_from_requirements()
- ✅ **Task Group 3.2**: Remove hardcoded templates, real code generation
- ✅ **Task Group 4.1**: ComplianceValidator con semantic validation
- ✅ **Task Group 4.2**: Phase 6.5 Code Repair con LLM-guided repair loop

---

**Última actualización**: 2025-11-20
