# Testing & E2E Pipeline

**Version**: 2.1
**Date**: November 2025
**Status**: Production
**Source**: `tests/e2e/real_e2e_full_pipeline.py` (~4000 lines)

---

## Overview

DevMatrix's E2E pipeline orchestrates complete application generation from natural language specs to validated, production-ready code. The pipeline is a single async Python file with 11 phases, performance profiling, and comprehensive metrics collection.

---

## Quick Start

```bash
# Full E2E test with stratified architecture
PYTHONPATH=/home/kwar/code/agentic-ai \
EXECUTION_MODE=hybrid \
QA_LEVEL=fast \
QUALITY_GATE_ENV=dev \
timeout 9000 python tests/e2e/real_e2e_full_pipeline.py tests/e2e/test_specs/ecommerce-api-spec-human.md
```

**Usage**: `python tests/e2e/real_e2e_full_pipeline.py <spec_file_path>`

---

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `EXECUTION_MODE` | safe, hybrid, research | hybrid | Controls LLM stratum usage |
| `QA_LEVEL` | fast, heavy | fast | Validation depth |
| `QUALITY_GATE_ENV` | dev, staging, production | dev | Policy strictness |
| `USE_REAL_CODE_GENERATION` | true, false | true | Enable real code generation |
| `MIN_ACCEPTABLE_COMPLIANCE` | 0.0-1.0 | 0.65 | Minimum compliance to continue |
| `COMPLIANCE_THRESHOLD` | 0.0-1.0 | 0.80 | Target compliance score |
| `REPAIR_IMPROVEMENT_THRESHOLD` | 0.0-1.0 | 0.85 | Post-repair compliance target |
| `VALIDATION_EXTRACTION_TIMEOUT` | seconds | 60 | Timeout for validation extraction |

---

## RealE2ETest Class

**File**: `tests/e2e/real_e2e_full_pipeline.py:445`

```python
class RealE2ETest:
    """Real E2E test with actual code generation"""

    # Performance thresholds
    COMPLIANCE_THRESHOLD_PASS = 0.80
    TEST_PASS_RATE_THRESHOLD = 0.90
    SPEC_TO_APP_PRECISION_EXCELLENT = 0.95
    SPEC_TO_APP_PRECISION_GOOD = 0.80

    def __init__(self, spec_file: str):
        self.spec_file = spec_file
        self.output_dir = f"tests/e2e/generated_apps/{spec_name}_{timestamp}"

        # Performance profiling
        tracemalloc.start()
        self.process = psutil.Process()

        # Metrics and validation
        self.metrics_collector = MetricsCollector(...)
        self.precision = PrecisionMetrics()
        self.contract_validator = ContractValidator()
        self.llm_tracker = LLMUsageTracker(model="claude-3-5-sonnet")

        # Pipeline data
        self.spec_requirements: SpecRequirements = None
        self.application_ir: ApplicationIR = None
        self.generated_code = {}
        self.compliance_report = None
        self.ir_compliance_metrics = None

        # Stratified Architecture Components
        self.execution_manager = None      # ExecutionModeManager
        self.manifest_builder = None       # ManifestBuilder
        self.stratum_metrics_collector = None  # MetricsCollector
        self.quality_gate = None           # QualityGate
        self.golden_app_runner = None      # GoldenAppRunner
        self.skeleton_generator = None     # SkeletonGenerator
        self.pattern_promoter = None       # PatternPromoter
```

---

## Pipeline Phases (11 Total)

### Phase 1: Spec Ingestion (`_phase_1_spec_ingestion`)

**Purpose**: Parse natural language spec and extract ApplicationIR

```python
async def _phase_1_spec_ingestion(self):
    # 1. Read spec file
    self.spec_content = Path(spec_file).read_text()

    # 2. Parse with SpecParser
    parser = SpecParser()
    self.spec_requirements = parser.parse(spec_path)

    # 3. Extract ApplicationIR (IR-centric architecture)
    ir_converter = SpecToApplicationIR()
    self.application_ir = await ir_converter.get_application_ir(
        self.spec_content,
        spec_path.name,
        force_refresh=False
    )

    # Output: ir_entities, ir_endpoints, ir_flows, ir_validations
```

**Checkpoints**: CP-1.1 (Spec loaded), CP-1.2 (Requirements extracted), CP-1.3 (Context loaded), CP-1.4 (Complexity assessed)

---

### Phase 1.5: Validation Scaling (`_phase_1_5_validation_scaling`)

**Purpose**: Multi-phase validation extraction (Pattern + LLM + Graph)

```python
async def _phase_1_5_validation_scaling(self):
    # Option 1: LLM Normalization (Selected)
    normalizer = LLMSpecNormalizer()
    normalized_spec = normalizer.normalize(self.spec_content)

    # Extract validations using BusinessLogicExtractor
    extractor = BusinessLogicExtractor()
    validations = extractor.extract_validations(spec_dict)

    # Validation types extracted:
    # - PRESENCE, FORMAT, RANGE, UNIQUENESS
    # - RELATIONSHIP, STATUS_TRANSITION, WORKFLOW_CONSTRAINT
    # - STOCK_CONSTRAINT and cross-entity validations
```

**Validation Phases**:
1. Pattern-based extraction (50+ YAML patterns)
2. LLM-based extraction (3 specialized prompts)
3. Graph-based inference (entity relationships) [PLANNED]

---

### Phase 2: Requirements Analysis (`_phase_2_requirements_analysis`)

**Purpose**: Semantic classification using RequirementsClassifier

```
BEFORE: Keyword matching with 42% accuracy, 6% functional recall
AFTER: Semantic classification with ≥90% accuracy, ≥90% functional recall
```

---

### Phase 3: Multi-Pass Planning (`_phase_3_multi_pass_planning`)

**Purpose**: Generate DAG from ApplicationIR with 6-pass planning

```python
async def _phase_3_multi_pass_planning(self):
    # Get DAG nodes from ApplicationIR (Phase 3 IR Migration)
    nodes = self.application_ir.get_dag_nodes()
    # Returns: entities from DomainModelIR, endpoints from APIModelIR,
    #          flows from BehaviorModelIR

    # Build ordered dependency waves for Phase 6
    self.ordered_waves = self._build_dependency_waves(nodes)
```

---

### Phase 4: Atomization (`_phase_4_atomization`)

**Purpose**: Break into atomic generation units

---

### Phase 5: DAG Construction (`_phase_5_dag_construction`)

**Purpose**: Build execution DAG with Neo4j

---

### Phase 6: Code Generation (`_phase_6_code_generation`)

**Purpose**: IR-driven production code generation

```python
async def _phase_6_code_generation(self):
    # ApplicationIR is REQUIRED (no fallback to legacy spec_requirements)
    if not self.application_ir:
        raise RuntimeError("ApplicationIR extraction failed...")

    # Verify all required sub-IRs
    required_irs = {
        'domain_model': self.application_ir.domain_model,
        'api_model': self.application_ir.api_model,
        'validation_model': self.application_ir.validation_model,
        'infrastructure_model': self.application_ir.infrastructure_model,
    }

    # Generate with animated progress bar
    generated_code_str = await self.code_generator.generate_from_application_ir(
        self.application_ir,
        allow_syntax_errors=True  # Let repair loop fix issues
    )

    # Parse into file structure
    self.generated_code = self._parse_generated_code_to_files(generated_code_str)
```

**Checkpoints**: CP-6.1 to CP-6.5 (Models, Routes, Tests, Complete)

---

### Phase 6.5: IR-based Test Generation

**Purpose**: Generate tests from ValidationModelIR

```python
# Phase 6.5: Generate IR-based tests
if IR_SERVICES_AVAILABLE and self.application_ir:
    generated_test_files = generate_all_tests_from_ir(
        self.application_ir,
        tests_output_dir
    )
    # Generates: test_validation_rules.py, test_integration_flows.py,
    #            test_api_contracts.py
```

---

### Phase 6.6: IR-based Service Generation

**Purpose**: Generate service methods from BehaviorModelIR

```python
# Phase 6.6: Generate services from BehaviorModelIR
generated_service_files = generate_services_from_ir(
    self.application_ir,
    self.output_path
)

# Check flow coverage
coverage = get_flow_coverage_report(self.application_ir, services_dir)
# Returns: coverage_percentage, implemented_flows, total_flows, missing_flows
```

---

### Phase 7: Deployment (`_phase_7_deployment`)

**Purpose**: Save generated files to output directory

```python
async def _phase_7_deployment(self):
    # Phase 2.5: Run basic validation BEFORE saving files
    # Phase 3: Track QA stratum metrics

    # Save all generated files
    for filepath, content in self.generated_code.items():
        full_path = self.output_path / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

        # Record in manifest with stratum classification
        self._record_file_in_manifest(filepath, content, llm_tokens)
```

---

### Phase 8: Code Repair (`_phase_8_code_repair`)

**Purpose**: Iterative LLM-based code repair

```python
async def _phase_8_code_repair(self):
    # CP-6.5.1: ComplianceValidator pre-check
    compliance_report = self.compliance_validator.validate_from_app(
        spec_requirements=self.spec_requirements,
        output_path=self.output_path
    )

    # Early exit if compliance < MIN_ACCEPTABLE_COMPLIANCE (65%)
    if compliance_score < MIN_ACCEPTABLE_COMPLIANCE:
        raise SystemExit(1)

    # Skip if compliance is perfect (100%)
    if compliance_score >= 1.00:
        return  # Skip repair

    # CP-6.5.4: Execute repair loop (max 3 iterations)
    repair_result = await self._execute_repair_loop(
        initial_compliance_report=compliance_report,
        test_results=test_results,
        main_code=main_code,
        max_iterations=3,
        precision_target=1.00  # Must achieve 100%
    )
```

**Repair Loop Steps**:
1. Analyze failures
2. Search RAG for similar patterns
3. Generate repair proposal
4. Create backup before applying
5. Apply repair to generated code
6. Re-validate compliance
7. Check for regression
8. Store repair attempt in ErrorPatternStore

---

### Phase 9: Validation (`_phase_9_validation`)

**Purpose**: Comprehensive semantic validation

```python
async def _phase_9_validation(self):
    # Structural validation (files exist, syntax valid)
    # Dependency order validation (ordered_waves)

    # Semantic validation with ComplianceValidator
    self.compliance_report = self.compliance_validator.validate_from_app(
        spec_requirements=self.application_ir,  # IR-centric
        output_path=self.output_path
    )

    # UUID serialization validation & auto-repair
    uuid_validator = UUIDSerializationValidator(self.output_path)
    is_valid, issues = uuid_validator.validate()
    if not is_valid:
        uuid_validator.auto_repair()

    # IR-based Compliance Check (STRICT + RELAXED modes)
    ir_compliance_reports_strict = check_full_ir_compliance(
        self.application_ir, self.output_path,
        mode=ValidationMode.STRICT
    )
    ir_compliance_reports_relaxed = check_full_ir_compliance(
        self.application_ir, self.output_path,
        mode=ValidationMode.RELAXED
    )

    # Run real tests and calculate coverage
    tests_executed, tests_passed, tests_failed = await self._run_generated_tests()
    coverage = await self._calculate_test_coverage()
```

**Checkpoints**: CP-7.1 to CP-7.6 (File structure, Syntax, Semantic, Business logic, Tests, Quality)

---

### Phase 10: Health Verification (`_phase_10_health_verification`)

**Purpose**: Verify generated application health endpoints

---

### Phase 11: Learning (`_phase_11_learning`)

**Purpose**: Pattern promotion and learning feedback

---

## Stratified Architecture Integration

### Initialization (`_init_stratified_architecture`)

```python
def _init_stratified_architecture(self):
    # Phase 1: Execution Mode
    self.execution_manager = get_execution_mode_manager(mode)

    # Phase 2: Manifest Tracking
    self.manifest_builder = get_manifest_builder(app_id)

    # Phase 3: Stratum Metrics
    self.stratum_metrics_collector = get_metrics_collector(app_id, mode)

    # Phase 4: Quality Gate
    self.quality_gate = get_quality_gate(env_str)

    # Phase 5: Golden Apps
    self.golden_app_runner = GoldenAppRunner(strict_mode=False)

    # Phase 6: Skeleton + Holes
    self.skeleton_generator = SkeletonGenerator(strict_mode=True)
    self.skeleton_llm_integration = SkeletonLLMIntegration(...)

    # Phase 7: Pattern Promotion
    self.pattern_promoter = get_pattern_promoter()
```

### File Stratum Classification (`_classify_file_stratum`)

```python
# TEMPLATE stratum - infrastructure files
template_patterns = [
    "docker-compose", "Dockerfile", "requirements.txt",
    "pyproject.toml", "alembic.ini", "prometheus.yml",
    "core/config.py", "core/database.py", "routes/health.py",
    "models/base.py", "main.py", "README.md", ".env"
]

# AST stratum - structured code
ast_patterns = [
    "models/entities.py", "models/schemas.py",
    "repositories/", "alembic/versions/", "routes/"
]

# LLM stratum - business logic
llm_patterns = [
    "services/", "_flow.py", "_business.py", "_custom.py"
]
```

---

## Key Service Imports

```python
# Core parsing
from src.parsing.spec_parser import SpecParser, SpecRequirements

# Requirements classification
from src.classification.requirements_classifier import RequirementsClassifier

# Compliance validation
from src.validation.compliance_validator import ComplianceValidator

# ApplicationIR extraction
from src.specs.spec_to_application_ir import SpecToApplicationIR

# IR-based services
from src.services.ir_test_generator import generate_all_tests_from_ir
from src.services.ir_compliance_checker import check_full_ir_compliance
from src.services.ir_service_generator import generate_services_from_ir

# Validation scaling
from src.services.business_logic_extractor import BusinessLogicExtractor
from src.services.llm_spec_normalizer import LLMSpecNormalizer

# Cognitive services
from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.planning.multi_pass_planner import MultiPassPlanner
from src.cognitive.planning.dag_builder import DAGBuilder
from src.services.code_generation_service import CodeGenerationService
from src.mge.v2.agents.code_repair_agent import CodeRepairAgent

# Stratified architecture
from src.services.execution_modes import ExecutionModeManager
from src.services.generation_manifest import ManifestBuilder
from src.services.stratum_metrics import MetricsCollector
from src.services.quality_gate import QualityGate
from src.services.skeleton_generator import SkeletonGenerator
from src.services.pattern_promoter import PatternPromoter
```

---

## Performance Profiling

```python
# Memory and CPU tracking
tracemalloc.start()
self.process = psutil.Process()

def _sample_performance(self):
    """Sample current memory and CPU usage"""
    current, peak = tracemalloc.get_traced_memory()
    current_memory_mb = current / 1024 / 1024
    current_cpu = self.process.cpu_percent(interval=0.1)

    self.memory_samples.append(current_memory_mb)
    self.cpu_samples.append(current_cpu)
```

---

## Output Structure

```
generated_app/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── dependencies.py
│   ├── models/
│   │   ├── base.py
│   │   ├── entities.py
│   │   └── schemas.py
│   ├── repositories/
│   │   └── {entity}_repository.py
│   ├── services/
│   │   └── {entity}_service.py
│   └── routes/
│       ├── health.py
│       └── {entity}_router.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── generated/
│       ├── test_validation_rules.py
│       ├── test_integration_flows.py
│       └── test_api_contracts.py
├── alembic/
│   ├── env.py
│   └── versions/
├── generation_manifest.json
├── stratum_metrics.json
├── quality_gate.json
└── golden_app_comparison.json
```

---

## Compliance Targets

| Metric | Threshold | Description |
|--------|-----------|-------------|
| MIN_ACCEPTABLE_COMPLIANCE | 65% | Stops test if below |
| COMPLIANCE_THRESHOLD | 80% | Target for validation |
| REPAIR_IMPROVEMENT_THRESHOLD | 85% | Post-repair target |
| Entity compliance | ≥95% | From IR |
| Flow compliance | ≥80% | From IR |
| Constraint compliance | ≥90% | From IR |

---

## Related Documentation

- [05-CODE_GENERATION.md](05-CODE_GENERATION.md) - Generation pipeline
- [06-VALIDATION.md](06-VALIDATION.md) - Validation system
- [08-RISKS_GAPS.md](08-RISKS_GAPS.md) - Known gaps

---

*DevMatrix - Testing & E2E Pipeline*
