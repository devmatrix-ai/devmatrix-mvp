# Components Reference

**Complete guide to all pipeline components and their roles**

**Status**: ✅ Complete Reference
**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py + component source files

---

## 📋 Core Components Overview

### Phase 1: Spec Ingestion
- **[SpecParser](COMPONENT_SPECPARSER.md)** - Parse Markdown specifications into structured requirements

### Phase 2: Requirements Analysis
- **[RequirementsClassifier](COMPONENT_REQUIREMENTSCLASSIFIER.md)** - Classify requirements by domain and priority

### Phase 3: Multi-Pass Planning
- **[MultiPassPlanner](COMPONENT_MULTIPASSPLANNER.md)** - Create comprehensive task plan with execution waves

### Phase 5: DAG Construction
- **[DAGBuilder](COMPONENT_DAGBUILDER.md)** - Build execution DAG with dependency validation

### Phase 6: Code Generation
- **[CodeGenerationService](COMPONENT_CODEGENERATIONSERVICE.md)** - Generate production-ready Python code

### Phase 6.5: Code Repair (Optional)
- **[CodeRepairAgent](COMPONENT_CODEREPAIRAGENT.md)** - Fix syntax errors and test failures
- **[TestResultAdapter](COMPONENT_TESTRESULTADAPTER.md)** - Parse and adapt test results for repair

### Phase 7: Validation
- **[ComplianceValidator](COMPONENT_COMPLIANCEVALIDATOR.md)** - Validate generated code against spec

### Phase 10: Learning (Optional)
- **[PatternFeedbackIntegration](COMPONENT_PATTERNFEEDBACKINTEGRATION.md)** - Record execution feedback and manage pattern promotion
- **[ErrorPatternStore](COMPONENT_ERRORPATTERNSTORE.md)** - Store and retrieve error patterns with solutions

### Throughout: Pattern Management
- **[PatternBank](COMPONENT_PATTERNBANK.md)** - Centralized pattern repository and matching

---

## 🔴 Core Required Components

| Component | Module | Phase | Purpose | Status |
|-----------|--------|-------|---------|--------|
| **SpecParser** | `src/parsing/spec_parser.py` | 1 | Parse Markdown specs | ✅ Required |
| **RequirementsClassifier** | `src/classification/requirements_classifier.py` | 2 | Classify requirements | ✅ Required |
| **MultiPassPlanner** | `src/cognitive/planning/multi_pass_planner.py` | 3 | Create task plan | ✅ Required |
| **DAGBuilder** | `src/cognitive/planning/dag_builder.py` | 5 | Build execution DAG | ✅ Required |
| **CodeGenerationService** | `src/services/code_generation_service.py` | 6 | Generate code | ✅ Required |
| **ComplianceValidator** | `src/validation/compliance_validator.py` | 7 | Validate code | ✅ Required |

## 🟡 Optional Components (Graceful Degradation)

| Component | Module | Phase | Purpose | Fallback |
|-----------|--------|-------|---------|----------|
| **CodeRepairAgent** | `src/mge/v2/agents/code_repair_agent.py` | 6.5 | Repair code | Continue with broken code |
| **TestResultAdapter** | `tests/e2e/adapters/test_result_adapter.py` | 6.5 | Parse tests | Skip repair |
| **PatternFeedbackIntegration** | `src/cognitive/patterns/pattern_feedback_integration.py` | 10 | Record patterns | Skip learning |
| **ErrorPatternStore** | `src/services/error_pattern_store.py` | 10 | Store errors | No error learning |

## 🟢 Supporting Components

| Component | Module | Purpose | Availability |
|-----------|--------|---------|---------------|
| **PatternBank** | `src/cognitive/patterns/pattern_bank.py` | Pattern repository | Optional (graceful) |

---

## Component Interaction Map

```
Phase 1 Input
    ↓
    [SpecParser] → SpecRequirements
    ↓
Phase 2 Input
    ↓
    [RequirementsClassifier] → ClassifiedRequirement[] + DependencyGraph
    ↓
Phase 3 Input
    ↓
    [MultiPassPlanner] → MasterPlan + Waves
    ↓
Phase 4 Input
    ↓
    Manual atomization
    ↓
Phase 5 Input
    ↓
    [DAGBuilder] → ExecutionDAG
    ↓
Phase 6 Input
    ↓
    [CodeGenerationService] → GeneratedCode (40-60 files)
    ├─ Uses: [PatternBank] for patterns
    ├─ Uses: [ApplicationIRNormalizer] for templates
    ├─ Optional: [CodeRepairAgent] in Phase 6.5
    └─ Optional: [TestResultAdapter] for test parsing
    ↓
Phase 7 Input
    ↓
    [ComplianceValidator] → ComplianceValidationResult
    ↓
Phase 10 Input (Optional)
    ↓
    [PatternFeedbackIntegration] → Pattern updates
    ├─ Uses: [ErrorPatternStore] for error recording
    └─ Promotes patterns in [PatternBank]
```

---

## Data Flow Through Components

### Specification to Code Generation

```
.md file (spec)
    ↓
[SpecParser.parse()]
    ↓
SpecRequirements {
    requirements: [Requirement],
    entities: [Entity],
    endpoints: [Endpoint],
    business_logic: [BusinessLogicRule]
}
    ↓
[RequirementsClassifier.classify_batch()]
    ↓
ClassifiedRequirement[] {
    type: "functional" | "non_functional",
    domain: "auth" | "crud" | "ui" | ...,
    priority: int,
    dependencies: [id]
}
    ↓
[RequirementsClassifier.build_dependency_graph()]
    ↓
DependencyGraph {
    nodes: [Requirement],
    edges: [Dependency]
}
    ↓
[MultiPassPlanner.create_plan()]
    ↓
MasterPlan {
    tasks: [Task],
    waves: [Wave]  # Execution groups
}
    ↓
[DAGBuilder.build_dag()]
    ↓
ExecutionDAG {
    nodes: [AtomicUnit],
    edges: [Dependency],
    waves: [Wave]  # Parallel execution groups
}
    ↓
[CodeGenerationService.generate_from_requirements()]
    ├─ Consults: [PatternBank] for code patterns
    ├─ Uses: [ApplicationIRNormalizer] for template rendering
    └─ May consult: [ErrorPatternStore] for known fixes
    ↓
GeneratedCode {
    files: {
        "src/main.py": "...",
        "src/models/user.py": "...",
        ...  (40-60 files)
    }
}
    ↓
[TestResultAdapter.parse_results()] (Phase 6.5, if needed)
    ↓
[CodeRepairAgent.repair()] (Phase 6.5, if errors)
    ↓
[ComplianceValidator.validate()]
    ↓
ComplianceValidationResult {
    passed: bool,
    compliance_score: 0.0-1.0,
    issues: [ValidationIssue],
    coverage: {type: float}
}
    ↓
[PatternFeedbackIntegration.register_successful_generation()] (Phase 10, if learning enabled)
    ↓
Pattern database updated
Error patterns learned
Better patterns for next execution
```

---

## Component Dependency Graph

```
SpecParser
    (no dependencies)

RequirementsClassifier
    depends_on: SpecParser output

MultiPassPlanner
    depends_on: RequirementsClassifier output

DAGBuilder
    depends_on: MultiPassPlanner output
    optionally_uses: Neo4j (for DAG storage)

CodeGenerationService (CRITICAL)
    depends_on: DAGBuilder output
    uses: ApplicationIRNormalizer (transitive)
    optionally_uses: PatternBank
    optionally_uses: ErrorPatternStore
    optionally_calls: CodeRepairAgent (Phase 6.5)

ComplianceValidator
    depends_on: CodeGenerationService output
    depends_on: SpecRequirements (Phase 1 output)

PatternFeedbackIntegration
    depends_on: ComplianceValidator output
    uses: ErrorPatternStore
    updates: PatternBank

ErrorPatternStore
    optionally_uses: Neo4j
    optionally_uses: Qdrant
    fallback: Local storage
```

---

## Service Initialization Status

From tests/e2e/real_e2e_full_pipeline.py:

```python
# Core services (lines 601-618) - REQUIRED
✅ RequirementsClassifier()
✅ ComplianceValidator()
✅ CodeGenerationService(db=None)
✅ MultiPassPlanner()
✅ DAGBuilder()

# Optional services (lines 620-642) - GRACEFUL DEGRADATION
🟡 PatternFeedbackIntegration()  # Skip if unavailable
🟡 ErrorPatternStore()  # Skip if unavailable
🟡 CodeRepairAgent()  # Skip repair phase if unavailable
🟡 TestResultAdapter()  # Skip test parsing if unavailable

# Pattern Bank (lines 88-105) - Optional
🟡 PatternBank()  # Fallback to hardcoded if unavailable
```

---

## Component Usage in Pipeline

| Phase | Component(s) Used | Optional | Impact if Missing |
|-------|------------------|----------|-------------------|
| 1 | SpecParser | No | Cannot parse specs - fatal |
| 2 | RequirementsClassifier | No | Cannot classify - fatal |
| 3 | MultiPassPlanner | No | Cannot plan - fatal |
| 4 | (manual) | N/A | Atomization is manual |
| 5 | DAGBuilder | No | Cannot build DAG - fatal |
| 6 | CodeGenerationService, PatternBank | No / Yes | Cannot generate - fatal |
| 6.5 | CodeRepairAgent, TestResultAdapter | Yes | Skip repair, deploy broken code |
| 7 | ComplianceValidator | No | Cannot validate - fatal |
| 8 | (file system) | N/A | Write files to disk |
| 9 | (file system) | N/A | Check files exist |
| 10 | PatternFeedbackIntegration, ErrorPatternStore | Yes | Skip learning, use defaults next time |

---

## Key Architecture Patterns

### Pattern 1: Graceful Degradation
Optional components (marked with try/except in initialization) fail silently:
```python
try:
    self.code_repair_agent = CodeRepairAgent()
except ImportError:
    self.code_repair_agent = None  # Continue without repair
```

### Pattern 2: Transitive Dependencies
Some components have transitive dependencies through imports:
```python
CodeGenerationService
    → imports ApplicationIRNormalizer
    → imports Neo4j connector
    → imports Qdrant connector
```

Pipeline succeeds even if Neo4j/Qdrant unavailable (optional features).

### Pattern 3: Data Pipeline
Each phase output becomes next phase input:
```
Phase N Output → Phase N+1 Input
(SpecRequirements) → (ClassifiedRequirement[]) → (MasterPlan) → ... → (ComplianceValidationResult)
```

### Pattern 4: Metric Collection
All components feed metrics to central collector:
```python
metrics_collector.add_checkpoint(phase_name, checkpoint_id, metrics)
```

---

## Quick Reference: Component Selection

**Need to parse specs?** → [SpecParser](COMPONENT_SPECPARSER.md)

**Need to categorize requirements?** → [RequirementsClassifier](COMPONENT_REQUIREMENTSCLASSIFIER.md)

**Need to plan execution?** → [MultiPassPlanner](COMPONENT_MULTIPASSPLANNER.md)

**Need to build task DAG?** → [DAGBuilder](COMPONENT_DAGBUILDER.md)

**Need to generate code?** → [CodeGenerationService](COMPONENT_CODEGENERATIONSERVICE.md)

**Need to fix broken code?** → [CodeRepairAgent](COMPONENT_CODEREPAIRAGENT.md)

**Need to validate code?** → [ComplianceValidator](COMPONENT_COMPLIANCEVALIDATOR.md)

**Need to learn from execution?** → [PatternFeedbackIntegration](COMPONENT_PATTERNFEEDBACKINTEGRATION.md)

**Need error pattern management?** → [ErrorPatternStore](COMPONENT_ERRORPATTERNSTORE.md)

**Need code patterns?** → [PatternBank](COMPONENT_PATTERNBANK.md)

---

## Integration Checklist

- ✅ All 6 core components documented
- ✅ All 4 optional components documented
- ✅ Component interaction map provided
- ✅ Data flow diagrams included
- ✅ Dependency graph documented
- ✅ Service initialization status clear
- ✅ Graceful degradation patterns explained
- ✅ Pipeline integration points identified

---

**For detailed information on each component, see individual component documentation files.**
