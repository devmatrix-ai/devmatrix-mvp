# E2E Pipeline Documentation

**Complete End-to-End Pipeline Execution Flow**

The E2E pipeline (`tests/e2e/real_e2e_full_pipeline.py`) implements the complete DevMatrix cognitive compiler, transforming natural language specifications into validated, working applications through 10 orchestrated phases.

## 1. System Overview

The pipeline operates as a **Cognitive Compiler**, executing a deterministic flow from unstructured requirements to production-ready code with continuous validation and learning.

```mermaid
graph TD
    subgraph "Frontend: Analysis & IR Construction"
        P1[Phase 1: Spec Ingestion]
        P2[Phase 2: Requirements Analysis]
        P1 -->|SpecRequirements| P2
    end

    subgraph "Optimizer: Planning & Atomization"
        P3[Phase 3: Multi-Pass Planning]
        P4[Phase 4: Atomization]
        P5[Phase 5: DAG Construction]
        P2 -->|Classified Requirements| P3
        P3 -->|Planning Result| P4
        P4 -->|Atomic Units| P5
    end

    subgraph "Backend: Code Generation & Repair"
        P6[Phase 6: Code Generation]
        P8[Phase 8: Deployment]
        P6_5[Phase 6.5: Code Repair]
        P5 -->|DAG| P6
        P6 -->|Generated Code| P8
        P8 -->|Files on Disk| P6_5
    end

    subgraph "Runtime: Validation & Learning"
        P7[Phase 7: Validation]
        P9[Phase 9: Health Verification]
        P10[Phase 10: Learning]
        P6_5 -->|Repaired Code| P7
        P7 -->|Validated App| P9
        P9 -->|Health Check| P10
    end
```

## 2. Pipeline Phases

### Phase 1: Spec Ingestion
**Purpose**: Parse natural language specifications into structured requirements.

**Component**: `SpecParser` ([src/parsing/spec_parser.py](../src/parsing/spec_parser.py))

**Process**:
1. **CP-1.1**: Load spec file (Markdown/text)
2. **CP-1.2**: Extract structured requirements using regex and NLU
3. **CP-1.3**: Load context and metadata
4. **CP-1.4**: Assess complexity based on entities, endpoints, logic rules

**Input**: Raw specification file (`.md`, `.txt`)

**Output**: `SpecRequirements` object containing:
- `requirements`: List of functional/non-functional requirements
- `entities`: Domain entities with attributes and relationships
- `endpoints`: API endpoints with methods, paths, schemas
- `business_logic`: Business rules and invariants
- `metadata`: Project name, description, stack configuration
- `classification_ground_truth`: Expected classifications for validation

**Metrics**:
- Total requirements extracted
- Functional vs non-functional count
- Entity count
- Endpoint count
- Business logic rules count
- Complexity score (0.0-1.0)

**Contract Validation**:
```python
{
    "spec_content": str,
    "requirements": List[str],
    "spec_requirements": {
        "total_requirements": int,
        "functional_count": int,
        "entities": List[str],
        "endpoints": List[str],
        "metadata": Dict
    },
    "complexity": float
}
```

---

### Phase 2: Requirements Analysis
**Purpose**: Semantically classify requirements and build dependency graph.

**Component**: `RequirementsClassifier` ([src/classification/requirements_classifier.py](../src/classification/requirements_classifier.py))

**Process**:
1. **CP-2.1**: Classify functional requirements by domain (auth, data, business_logic, api, ui)
2. **CP-2.2**: Classify non-functional requirements (performance, security, scalability)
3. **CP-2.3**: Build dependency graph (DAG) with topological ordering
4. **CP-2.4**: Validate DAG for cycles and dependency conflicts
5. **CP-2.5**: Track classification accuracy against ground truth

**Classification Strategy**:
- **Semantic Classification**: Uses transformer embeddings + domain keywords
- **Accuracy Target**: ≥90% classification accuracy, ≥90% functional recall
- **Improvement**: Replaced naive keyword matching (42% accuracy) with semantic approach

**Output**: `List[Requirement]` with metadata:
- `id`: Requirement identifier (e.g., "F1_create_product")
- `type`: "functional" | "non_functional"
- `domain`: "auth" | "data" | "business_logic" | "api" | "ui"
- `risk_level`: "low" | "medium" | "high"
- `dependencies`: List of requirement IDs this depends on
- `priority`: int (1-5)

**Dependency Graph**: `Dict[req_id, List[dependency_ids]]`

**Metrics**:
- Classification accuracy (compared to ground truth)
- Functional requirements count
- Non-functional requirements count
- Domain distribution
- Dependency graph validity (is valid DAG)

---

### Phase 3: Multi-Pass Planning
**Purpose**: Generate hierarchical execution plan with multiple passes.

**Component**: `MultiPassPlanner` ([src/cognitive/planning/multi_pass_planner.py](../src/cognitive/planning/multi_pass_planner.py))

**Process**:
1. **CP-3.1**: First pass - high-level architectural decisions
2. **CP-3.2**: Second pass - detailed implementation strategy
3. **CP-3.3**: Third pass - optimization and refinement

**Output**: Planning result with:
- Architectural decisions (database, framework, auth strategy)
- Implementation phases
- Resource allocation
- Risk mitigation strategies

---

### Phase 4: Atomization
**Purpose**: Break down requirements into atomic implementation units.

**Component**: Pattern matching and task decomposition

**Process**:
1. **CP-4.1**: Match requirements to implementation patterns
2. **CP-4.2**: Decompose into atomic units (smallest executable tasks)
3. **CP-4.3**: Assign priorities and complexity scores

**Output**: `List[AtomicUnit]` with:
- Task description
- Implementation pattern
- Dependencies
- Estimated complexity
- Priority level

---

### Phase 5: DAG Construction
**Purpose**: Build execution DAG respecting dependencies.

**Component**: `DAGBuilder` ([src/cognitive/planning/dag_builder.py](../src/cognitive/planning/dag_builder.py))

**Process**:
1. **CP-5.1**: Create DAG nodes from atomic units
2. **CP-5.2**: Add edges based on dependencies
3. **CP-5.3**: Validate DAG (no cycles)
4. **CP-5.4**: Compute topological ordering (wave execution order)

**Output**: DAG with:
- Nodes (atomic units)
- Edges (dependencies)
- Ordered waves (execution batches)

---

### Phase 6: Code Generation
**Purpose**: Generate real application code from requirements.

**Component**: `CodeGenerationService` ([src/services/code_generation_service.py](../src/services/code_generation_service.py))

**Process**:
1. **CP-6.1**: Code generation started
2. **CP-6.2**: Generate domain models (entities, relationships)
3. **CP-6.3**: Generate API routes (endpoints, schemas)
4. **CP-6.4**: Generate tests (unit, integration)
5. **CP-6.5**: Code generation complete

**Implementation**:
```python
generated_code_str = await code_generator.generate_from_requirements(
    spec_requirements,
    allow_syntax_errors=True  # Repair loop will fix syntax issues
)
```

**Output Format**: Multi-file structure with delimiter:
```
=== FILE: src/main.py ===
<content>

=== FILE: src/models/product.py ===
<content>

=== FILE: src/routes/products.py ===
<content>
```

**Parsed Output**: `Dict[filepath, content]`
- `src/main.py`: FastAPI application entry point
- `src/models/*.py`: Pydantic/SQLAlchemy models
- `src/routes/*.py`: API route handlers
- `src/schemas/*.py`: Request/response schemas
- `tests/*.py`: Unit and integration tests
- `requirements.txt`: Python dependencies

**Metrics**:
- Files generated count
- Execution success rate
- Recovery rate (if retries needed)
- Generation time (ms)

**Feature Flag**: `USE_REAL_CODE_GENERATION=true` (default: enabled)

---

### Phase 8: Deployment
**Purpose**: Write generated code to disk before repair phase.

**Process**:
1. **CP-8.1**: Create output directory structure
2. **CP-8.2**: Write all generated files to disk
3. **CP-8.3**: Set proper file permissions

**Critical Note**: Phase 8 runs **BEFORE** Phase 6.5 (Code Repair) because repair needs to read/modify files from disk.

**Output**: Files written to `tests/e2e/generated_apps/{spec_name}_{timestamp}/`

---

### Phase 6.5: Code Repair (NEW)
**Purpose**: Automatically fix code quality issues through iterative repair loop.

**Components**:
- `ComplianceValidator` ([src/validation/compliance_validator.py](../src/validation/compliance_validator.py))
- `TestResultAdapter` ([tests/e2e/adapters/test_result_adapter.py](../tests/e2e/adapters/test_result_adapter.py))
- `ErrorPatternStore` ([src/services/error_pattern_store.py](../src/services/error_pattern_store.py))

**Process**:
1. **CP-6.5.1**: Run compliance pre-check
   - Validate entities and endpoints against spec
   - Calculate compliance score (0.0-1.0)
   - Skip repair if compliance ≥ 1.00 (perfect)

2. **CP-6.5.2**: Initialize repair dependencies
   - ErrorPatternStore (RAG for similar errors)
   - Repair configuration (max_iterations=3, precision_target=1.00)

3. **CP-6.5.3**: Convert ComplianceReport to TestResult format
   - Adapter pattern: ComplianceReport → List[TestResult]
   - Enables repair loop to process compliance failures

4. **CP-6.5.4**: Execute repair loop (iterative)
   - Step 1: Analyze failures from compliance report
   - Step 2: Search RAG for similar error patterns
   - Step 3: Generate repair proposal (LLM-based)
   - Step 4: Create backup before applying repair
   - Step 5: Apply repair to generated code
   - Step 6: Re-validate compliance
   - Step 7: Check for regression (compliance decreased)
   - Step 8: Store repair attempt in ErrorPatternStore

5. **CP-6.5.5**: Collect metrics
   - Repair iterations executed
   - Tests fixed
   - Regressions detected
   - Final compliance score
   - Improvement percentage

**Repair Loop Logic**:
```python
for iteration in range(max_iterations):
    # Analyze current failures
    failures = analyze_compliance_failures(current_compliance_report)

    # Search RAG for similar patterns
    similar_patterns = error_pattern_store.search(failures)

    # Generate repair proposal
    repair_proposal = generate_repair(failures, similar_patterns)

    # Apply repair and re-validate
    apply_repair(repair_proposal)
    new_compliance_report = validate_compliance()

    # Check improvement
    if new_compliance_report.overall_compliance >= precision_target:
        break  # Success!

    if new_compliance_report.overall_compliance <= current_compliance_report.overall_compliance:
        no_improvement_count += 1
        if no_improvement_count >= 2:
            break  # No progress, stop

    current_compliance_report = new_compliance_report
```

**Early Exit Conditions**:
- Compliance ≥ precision_target (1.00 = 100%)
- No improvement for 2 consecutive iterations
- Max iterations reached (3)

**Metrics**:
- `repair_applied`: bool
- `repair_iterations`: int
- `repair_improvement`: float (percentage)
- `tests_fixed`: int
- `regressions_detected`: int
- `pattern_reuse_count`: int
- `repair_time_ms`: float

**Skip Logic**: If compliance ≥ 1.00 in pre-check, skip entire repair phase.

---

### Phase 7: Validation
**Purpose**: Comprehensive structural and semantic validation.

**Components**:
- `ContractValidator` ([tests/e2e/precision_metrics.py](../tests/e2e/precision_metrics.py))
- `ComplianceValidator` ([src/validation/compliance_validator.py](../src/validation/compliance_validator.py))
- `UUIDSerializationValidator` ([src/validation/uuid_serialization_validator.py](../src/validation/uuid_serialization_validator.py))

**Process**:
1. **CP-7.1**: File structure validation
   - Verify all expected files generated
   - Check directory structure

2. **CP-7.2**: Syntax validation
   - Python syntax check (`python -m py_compile`)
   - Import validation

3. **CP-7.2.5**: Dependency order validation
   - Verify execution waves respect dependencies
   - Validate topological ordering

4. **CP-7.3**: Semantic validation (ComplianceValidator)
   - **Entity Validation**: Check all spec entities implemented
   - **Endpoint Validation**: Check all spec endpoints implemented
   - **Schema Validation**: Validate request/response schemas match spec
   - **Business Logic Validation**: Verify business rules implemented

5. **CP-7.4**: UUID Serialization validation
   - Detect UUID serialization issues (e.g., `UUID()` instead of `UUID4`)
   - Auto-repair if issues found
   - Re-validate after repair

**Compliance Validation Strategy**:
- **Before**: String parsing of generated code (fragile, missed modular architecture)
- **After**: OpenAPI schema extraction via `validate_from_app()`
  - Imports generated FastAPI app
  - Extracts OpenAPI schema
  - Compares against SpecRequirements
  - Detects entities, endpoints, schemas in modular architecture

**Validation Report**:
```python
{
    "overall_compliance": float,  # 0.0-1.0
    "entities_expected": List[str],
    "entities_implemented": List[str],
    "entities_missing": List[str],
    "endpoints_expected": List[Endpoint],
    "endpoints_implemented": List[Endpoint],
    "endpoints_missing": List[Endpoint],
    "missing_requirements": List[str],
    "validation_errors": List[str]
}
```

**Compliance Threshold**: Configurable via `COMPLIANCE_THRESHOLD` env var (default: 0.80 = 80%)

**Failure Behavior**: If compliance < threshold, raise `ComplianceValidationError` (fails E2E test)

---

### Phase 9: Health Verification
**Purpose**: Verify generated application can start and respond.

**Process**:
1. **CP-9.1**: Import application module
2. **CP-9.2**: Check FastAPI app instantiation
3. **CP-9.3**: Verify routes registered
4. **CP-9.4**: Test basic health endpoint (if available)

**Health Checks**:
- Application imports without errors
- FastAPI instance created
- Routes registered correctly
- Database connection (if configured)

---

### Phase 10: Learning
**Purpose**: Store successful patterns for future reuse.

**Component**: `PatternFeedbackIntegration` ([src/cognitive/patterns/pattern_feedback_integration.py](../src/cognitive/patterns/pattern_feedback_integration.py))

**Process**:
1. **CP-10.1**: Extract patterns from successful code
2. **CP-10.2**: Calculate pattern quality scores
3. **CP-10.3**: Store patterns in PatternBank
4. **CP-10.4**: Update RAG embeddings (Qdrant)
5. **CP-10.5**: Store success metadata in Neo4j

**Learning Metrics**:
- Patterns extracted
- Patterns promoted to bank
- Average quality score
- Reuse potential score

---

## 3. Component Architecture

### 3.1 SpecParser
**Location**: [src/parsing/spec_parser.py](../src/parsing/spec_parser.py)

**Responsibility**: Natural Language Understanding (NLU)

**Strategy**:
- Regex extraction for structured elements (F1, F2, E1, EP1 tags)
- Heuristic classification for data types
- Relationship inference from descriptions

**Output**: `SpecRequirements` (Pydantic model)

**Improvements** (Task Group 1.2):
- BEFORE: Extracted 55 lines (wrong - only list items)
- AFTER: Extracts structured SpecRequirements with entities, endpoints, business logic

---

### 3.2 RequirementsClassifier
**Location**: [src/classification/requirements_classifier.py](../src/classification/requirements_classifier.py)

**Responsibility**: Semantic classification and dependency analysis

**Strategy**:
- Transformer embeddings (sentence-transformers)
- Domain-specific keywords
- Dependency graph construction
- DAG validation (cycle detection)

**Improvements** (Task Group 2.2):
- BEFORE: Keyword matching with 42% accuracy, 6% functional recall
- AFTER: Semantic classification with ≥90% accuracy, ≥90% functional recall

---

### 3.3 CodeGenerationService
**Location**: [src/services/code_generation_service.py](../src/services/code_generation_service.py)

**Responsibility**: Code synthesis from requirements

**Architecture**:
```python
class CodeGenerationService:
    async def generate_from_requirements(
        self,
        spec_requirements: SpecRequirements,
        allow_syntax_errors: bool = False
    ) -> str:
        """Generate complete application code"""
```

**Components**:
- `PromptBuilder`: Formal prompt construction
- `BackendGenerator`: Abstract interface for multi-stack support
- `UnifiedRAGRetriever`: Context retrieval from PatternBank

**Improvements** (Task Group 3.2):
- BEFORE: Returns hardcoded Task API template for ALL specs
- AFTER: Generates real code based on SpecRequirements from Phase 1

---

### 3.4 ComplianceValidator
**Location**: [src/validation/compliance_validator.py](../src/validation/compliance_validator.py)

**Responsibility**: Semantic validation of generated code

**Strategy**:
- **Old Approach**: String parsing (fragile, missed modular code)
- **New Approach**: OpenAPI schema extraction
  - Imports generated FastAPI app
  - Extracts OpenAPI schema via `/openapi.json`
  - Compares entities/endpoints against SpecRequirements

**Methods**:
```python
class ComplianceValidator:
    def validate_from_app(
        self,
        spec_requirements: SpecRequirements,
        output_path: Path
    ) -> ComplianceReport:
        """Validate using OpenAPI schema (modular-aware)"""
```

**Improvements** (Task Group 4.2):
- BEFORE: Only structural checks (files exist, syntax valid)
- AFTER: Structural + semantic validation (entities, endpoints match spec)

---

### 3.5 TestResultAdapter
**Location**: [tests/e2e/adapters/test_result_adapter.py](../tests/e2e/adapters/test_result_adapter.py)

**Responsibility**: Adapter pattern for ComplianceReport → TestResult

**Purpose**: Enable repair loop to process compliance failures

**Strategy**:
```python
class TestResultAdapter:
    def convert(self, compliance_report: ComplianceReport) -> List[TestResult]:
        """Convert compliance failures to test failures"""
```

**Output**: List of test failures for repair loop

---

## 4. Data Flow

### 4.1 Requirements Flow
```
Raw Spec → SpecParser → SpecRequirements → RequirementsClassifier →
Classified Requirements → MultiPassPlanner → Planning Result →
Atomization → Atomic Units → DAG → Code Generation → Generated Code
```

### 4.2 Validation Flow
```
Generated Code → Deployment (write to disk) → Code Repair (iterative) →
ComplianceValidator → ComplianceReport → Contract Validation →
Health Verification → Success/Failure
```

### 4.3 Learning Flow
```
Successful Code → Pattern Extraction → Quality Scoring →
PatternBank → Qdrant Embeddings → Neo4j Metadata → Future Reuse
```

---

## 5. Metrics & Monitoring

### 5.1 Performance Metrics
Collected by `MetricsCollector` ([tests/e2e/metrics_framework.py](../tests/e2e/metrics_framework.py))

**Tracked Metrics**:
- **Memory**: `avg_memory_mb`, `peak_memory_mb`
- **CPU**: `avg_cpu_percent`, `peak_cpu_percent`
- **Time**: `phase_duration_ms` for each phase
- **Throughput**: Requirements processed per second

**Sampling Strategy**: Sample at each phase start, finalize at pipeline end

---

### 5.2 Precision Metrics
Tracked by `PrecisionMetrics` ([tests/e2e/precision_metrics.py](../tests/e2e/precision_metrics.py))

**Accuracy Metrics**:
- **Classification Accuracy**: Correct classifications / total classifications
- **Execution Success Rate**: Successful atoms / total atoms
- **Recovery Rate**: Recovered atoms / failed atoms
- **Compliance Score**: Overall compliance (0.0-1.0)

**Quality Gates**:
- Classification accuracy ≥ 90%
- Execution success rate ≥ 95%
- Compliance score ≥ 80% (configurable)

---

### 5.3 Checkpoint Tracking
Each phase reports progress via checkpoints:

**Format**: `CP-{phase}.{step}: {description}`

**Example**:
```
CP-1.1: Spec loaded from file
CP-1.2: Requirements extracted
CP-1.3: Context loaded
CP-1.4: Complexity assessed
```

**Visibility**: Checkpoints displayed in real-time during execution

---

## 6. Configuration

### 6.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_REAL_CODE_GENERATION` | Enable real code generation (vs template) | `true` |
| `COMPLIANCE_THRESHOLD` | Minimum compliance score (0.0-1.0) | `0.80` |
| `ANTHROPIC_API_KEY` | Claude API key | Required |
| `OPENAI_API_KEY` | GPT-4 API key (for dual validation) | Optional |
| `ENABLE_AUTO_PROMOTION` | Auto-promote high-quality patterns | `True` |
| `ENABLE_DUAL_VALIDATION` | Require both Claude and GPT-4 | `True` |
| `RAG_STRATEGY` | `semantic` \| `graph` \| `hybrid` | `hybrid` |

---

### 6.2 Feature Flags

**Code Generation**:
- `USE_REAL_CODE_GENERATION=true`: Generate real code from requirements
- `USE_REAL_CODE_GENERATION=false`: Error (hardcoded template removed)

**Repair Loop**:
- Repair skipped if compliance ≥ 1.00 (perfect)
- Max iterations: 3
- Precision target: 1.00 (100% compliance)

**Validation**:
- `COMPLIANCE_THRESHOLD`: Configurable pass/fail threshold
- Default: 0.80 (80% compliance)

---

## 7. Error Handling

### 7.1 Phase-Level Errors
Each phase wrapped in try-except:
```python
try:
    await self._phase_X_name()
except Exception as e:
    print(f"❌ Phase X error: {e}")
    self.metrics_collector.record_error("phase_name", {"error": str(e)}, critical=True)
```

**Recovery Strategy**: Pipeline continues to `_finalize_and_report()` to save metrics

---

### 7.2 Validation Errors

**ComplianceValidationError**: Raised when compliance < threshold
- Contains detailed ComplianceReport
- Fails E2E test immediately
- Reports missing entities/endpoints

**Handling**:
```python
try:
    compliance_report = validator.validate_from_app(...)
    if compliance_report.overall_compliance < THRESHOLD:
        raise ComplianceValidationError(f"Compliance {score:.1%} < {THRESHOLD:.1%}")
except ComplianceValidationError as e:
    print(f"❌ Semantic validation FAILED: {e}")
    raise  # Fail E2E test
```

---

### 7.3 Repair Loop Failures

**Regression Detection**: If compliance decreases after repair
- Increment `regressions_detected`
- Revert to previous code (backup)
- Stop iteration

**No Improvement**: If no improvement for 2 consecutive iterations
- Stop repair loop
- Report final compliance
- Continue to validation

---

## 8. Testing & Validation

### 8.1 Contract Validation
Each phase validates its output contract using `ContractValidator`

**Example**:
```python
phase_output = {
    "spec_content": str,
    "requirements": List[str],
    "complexity": float
}
is_valid = self.contract_validator.validate_phase_output("spec_ingestion", phase_output)
```

**Enforcement**: Contract validation failures logged but don't fail pipeline

---

### 8.2 Ground Truth Validation
Classification accuracy validated against ground truth:

**Ground Truth Format** (in spec file):
```markdown
<!-- GROUND_TRUTH_START
{
  "F1_create_product": {"domain": "data", "risk": "low"},
  "F2_update_inventory": {"domain": "business_logic", "risk": "medium"}
}
GROUND_TRUTH_END -->
```

**Validation**:
```python
for req in classified_requirements:
    actual = {"domain": req.domain, "risk": req.risk_level}
    expected = ground_truth[req.id]
    is_correct = validate_classification(actual, expected)
```

**Metric**: Classification accuracy = correct / total

---

### 8.3 E2E Test Execution

**Run E2E Test**:
```bash
DATABASE_URL='postgresql+asyncpg://test:test@localhost/test' \
python tests/e2e/real_e2e_full_pipeline.py specs/example_spec.md
```

**Success Criteria**:
- All phases complete without critical errors
- Compliance ≥ threshold (default: 80%)
- All contract validations pass
- Generated app imports successfully

**Output**:
- Generated app in `tests/e2e/generated_apps/{spec_name}_{timestamp}/`
- Metrics report (JSON)
- Validation report
- Precision metrics

---

## 9. Future Enhancements

### 9.1 Multi-Stack Support
The `ApplicationIR` is designed to be stack-agnostic:

**Current**: FastAPI (Python)

**Future**:
- Django (Python)
- Node.js / Express (JavaScript)
- Go / Fiber (Go)
- Rust / Actix (Rust)

**Implementation**: Extend `BackendGenerator` abstract interface

---

### 9.2 Advanced Repair Strategies
**Current**: LLM-based iterative repair with RAG

**Future**:
- Static analysis integration (pylint, mypy, ruff)
- Formal verification for critical code paths
- Reinforcement learning for repair strategy selection
- Multi-model consensus repair (Claude + GPT-4 + local models)

---

### 9.3 Real-Time Monitoring
**Current**: Batch metrics collection post-execution

**Future**:
- Real-time metrics dashboard
- Phase-level performance alerting
- Automatic scaling based on load
- Distributed pipeline execution

---

## 10. Troubleshooting

### 10.1 Common Issues

**Issue**: Code generation returns hardcoded template
- **Cause**: `USE_REAL_CODE_GENERATION=false`
- **Fix**: Set `USE_REAL_CODE_GENERATION=true`

**Issue**: Compliance validation fails (0% compliance)
- **Cause**: App import failed or OpenAPI schema not generated
- **Debug**: Check generated code syntax, verify FastAPI app instantiation
- **Fix**: Review `src/main.py`, ensure proper imports

**Issue**: Repair loop makes no improvement
- **Cause**: Error patterns not helpful, LLM can't generate valid repair
- **Debug**: Review `ErrorPatternStore` entries, check repair proposals
- **Fix**: Add more diverse patterns to RAG, improve repair prompt

**Issue**: Classification accuracy low (<90%)
- **Cause**: Ground truth mismatch or classifier needs tuning
- **Debug**: Compare classified vs expected in ground truth
- **Fix**: Update ground truth, retrain classifier embeddings

---

### 10.2 Debug Mode

**Enable verbose logging**:
```python
# In real_e2e_full_pipeline.py
# Comment out silent_logs() context managers
# with silent_logs():  # REMOVE THIS
await self.code_generator.generate_from_requirements(...)
```

**View real-time logs**:
- Code generation prompts
- LLM responses
- Repair proposals
- Compliance validation details

---

### 10.3 Performance Profiling

**Memory Issues**:
- Check `peak_memory_mb` in metrics report
- Reduce batch sizes in classification
- Clear embeddings cache between runs

**CPU Issues**:
- Check `peak_cpu_percent` in metrics report
- Reduce parallelization (lower `CONCURRENCY`)
- Use smaller transformer models

**Time Issues**:
- Check `phase_duration_ms` for bottlenecks
- Optimize slowest phase (usually Phase 6: Code Generation)
- Enable caching for repeated runs

---

## 11. Architecture Diagrams

### 11.1 Complete System Architecture

```mermaid
graph TB
    subgraph "Phase 1-2: Frontend (Compiler Frontend)"
        Spec[Spec File .md] --> Parser[SpecParser]
        Parser --> SpecReq[SpecRequirements]
        SpecReq --> Classifier[RequirementsClassifier]
        Classifier --> ClassifiedReq[Classified Requirements]
    end

    subgraph "Phase 3-5: Optimizer (Planning & DAG)"
        ClassifiedReq --> Planner[MultiPassPlanner]
        Planner --> Atomizer[Atomization Engine]
        Atomizer --> DAGBuilder[DAG Builder]
        DAGBuilder --> DAG[Execution DAG]
    end

    subgraph "Phase 6: Backend (Code Generation)"
        DAG --> RAG[UnifiedRAG Retriever]
        RAG --> PromptBuilder[Prompt Builder]
        PromptBuilder --> LLM[LLM: Claude/GPT-4]
        LLM --> CodeGen[CodeGenerationService]
        CodeGen --> GeneratedCode[Generated Code]
    end

    subgraph "Phase 8: Deployment"
        GeneratedCode --> Disk[Write to Disk]
    end

    subgraph "Phase 6.5: Repair Loop (Runtime)"
        Disk --> PreCheck[Compliance Pre-Check]
        PreCheck -->|< 1.00| Adapter[TestResultAdapter]
        Adapter --> RepairLoop[Repair Loop]
        RepairLoop --> ErrorStore[ErrorPatternStore RAG]
        ErrorStore --> RepairLoop
        RepairLoop --> ReValidate[Re-Validate]
        ReValidate -->|Improved| RepairLoop
        ReValidate -->|Done| RepairedCode[Repaired Code]
        PreCheck -->|≥ 1.00| Skip[Skip Repair]
        Skip --> RepairedCode
    end

    subgraph "Phase 7: Validation (Runtime)"
        RepairedCode --> StructuralVal[Structural Validation]
        StructuralVal --> SemanticVal[Semantic Validation]
        SemanticVal --> UUIDVal[UUID Serialization]
        UUIDVal --> FinalReport[Validation Report]
    end

    subgraph "Phase 9-10: Health & Learning"
        FinalReport --> Health[Health Verification]
        Health --> Learning[Pattern Learning]
        Learning --> PatternBank[PatternBank]
        PatternBank --> Qdrant[(Qdrant Vector DB)]
        Learning --> Neo4j[(Neo4j Graph DB)]
    end
```

---

### 11.2 Data Models

```mermaid
classDiagram
    class SpecRequirements {
        +UUID app_id
        +String name
        +List~Requirement~ requirements
        +List~Entity~ entities
        +List~Endpoint~ endpoints
        +List~BusinessLogic~ business_logic
        +Dict metadata
        +Dict classification_ground_truth
    }

    class Requirement {
        +String id
        +String description
        +String type
        +String domain
        +String risk_level
        +List~String~ dependencies
        +Int priority
    }

    class Entity {
        +String name
        +List~Attribute~ attributes
        +List~Relationship~ relationships
    }

    class Endpoint {
        +String method
        +String path
        +Dict request_schema
        +Dict response_schema
    }

    class ComplianceReport {
        +Float overall_compliance
        +List~String~ entities_expected
        +List~String~ entities_implemented
        +List~String~ entities_missing
        +List~Endpoint~ endpoints_expected
        +List~Endpoint~ endpoints_implemented
        +List~Endpoint~ endpoints_missing
        +List~String~ missing_requirements
    }

    SpecRequirements *-- Requirement
    SpecRequirements *-- Entity
    SpecRequirements *-- Endpoint
```

---

## 12. References

### 12.1 Key Files
- **E2E Test**: [tests/e2e/real_e2e_full_pipeline.py](../tests/e2e/real_e2e_full_pipeline.py)
- **SpecParser**: [src/parsing/spec_parser.py](../src/parsing/spec_parser.py)
- **RequirementsClassifier**: [src/classification/requirements_classifier.py](../src/classification/requirements_classifier.py)
- **CodeGenerationService**: [src/services/code_generation_service.py](../src/services/code_generation_service.py)
- **ComplianceValidator**: [src/validation/compliance_validator.py](../src/validation/compliance_validator.py)
- **MetricsCollector**: [tests/e2e/metrics_framework.py](../tests/e2e/metrics_framework.py)
- **PrecisionMetrics**: [tests/e2e/precision_metrics.py](../tests/e2e/precision_metrics.py)

### 12.2 Related Documentation
- [APPLICATION_IR.md](APPLICATION_IR.md) - Application Intermediate Representation
- [COGNITIVE_ENGINE_ARCHITECTURE.md](COGNITIVE_ENGINE_ARCHITECTURE.md) - Cognitive Compiler Architecture
- [LEARNING_LAYER_INTEGRATION.md](LEARNING_LAYER_INTEGRATION.md) - Learning and Pattern Reuse
- [GAP_ANALYSIS.md](GAP_ANALYSIS.md) - Implementation Gaps and Roadmap

---

**Last Updated**: 2025-11-23
**Version**: 1.0
**Maintainer**: DevMatrix Team
