# DevMatrix E2E Pipeline - Diagrama de Arquitectura

**Fecha**: 2025-11-20

## 📊 Diagrama Principal: Pipeline Flow

```mermaid
flowchart TD
    %% Input
    START([Spec File .md]) --> P1

    %% Phase 1: Spec Ingestion
    P1[Phase 1: Spec Ingestion<br/>SpecParser]
    P1 --> P1_OUT{SpecRequirements<br/>entities, endpoints,<br/>business logic}

    %% Phase 2: Requirements Analysis
    P1_OUT --> P2[Phase 2: Requirements Analysis<br/>RequirementsClassifier]
    P2 --> PATTERN_BANK[(PatternBank<br/>RAG Search)]
    PATTERN_BANK -.-> P2
    P2 --> P2_OUT{Classified Requirements<br/>+ Dependency Graph}

    %% Phase 3: Multi-Pass Planning
    P2_OUT --> P3[Phase 3: Multi-Pass Planning<br/>MultiPassPlanner]
    P3 --> P3_OUT{Initial DAG<br/>nodes, edges, waves}

    %% Phase 4: Atomization
    P3_OUT --> P4[Phase 4: Atomization]
    P4 --> P4_OUT{Atomic Units<br/>id, complexity, LOC}

    %% Phase 5: DAG Construction
    P4_OUT --> P5[Phase 5: DAG Construction<br/>DAGBuilder]
    P5 --> P5_OUT{Final DAG<br/>with waves}

    %% Phase 6: Code Generation
    P5_OUT --> P6[Phase 6: Code Generation<br/>CodeGenerationService]
    P6 --> LLM[LLM Call<br/>Claude Sonnet 4.5<br/>+ Prompt Caching]
    LLM --> P6
    P6 --> ERROR_STORE[(ErrorPatternStore<br/>RAG Feedback)]
    ERROR_STORE -.retry guidance.-> P6
    P6 --> P6_OUT{Generated Code<br/>main.py, requirements.txt}

    %% Phase 6.5: Code Repair
    P6_OUT --> P6_5{Phase 6.5: Code Repair<br/>ComplianceValidator Pre-check}
    P6_5 -->|compliance ≥ 0.80| SKIP[SKIP REPAIR<br/>Fast Path ✅]
    P6_5 -->|compliance < 0.80| REPAIR_LOOP

    REPAIR_LOOP[Repair Loop<br/>max 3 iterations]
    REPAIR_LOOP --> ADAPTER[TestResultAdapter<br/>ComplianceReport → TestResult]
    ADAPTER --> REPAIR_LLM[Generate Repair Proposal<br/>LLM + Full Spec Context]
    REPAIR_LLM --> APPLY[Apply Repair]
    APPLY --> REVALIDATE[Re-validate Compliance]
    REVALIDATE -->|regression?| ROLLBACK[Rollback ↺]
    ROLLBACK --> REPAIR_LOOP
    REVALIDATE -->|improved!| REPAIR_OUT

    SKIP --> P6_5_OUT{Repaired Code<br/>or Original if skipped}
    REPAIR_OUT[Final Repaired Code] --> P6_5_OUT

    %% Phase 7: Validation
    P6_5_OUT --> P7[Phase 7: Validation<br/>ComplianceValidator]
    P7 --> CODE_ANALYZER[CodeAnalyzer<br/>Extract: entities,<br/>endpoints, validations]
    CODE_ANALYZER --> P7
    P7 -->|compliance < 0.80| FAIL[❌ FAIL<br/>ComplianceValidationError]
    P7 -->|compliance ≥ 0.80| P7_OUT{✅ Validation Passed<br/>Compliance Score}

    %% Phase 8: Deployment
    P7_OUT --> P8[Phase 8: Deployment<br/>Save files to disk]
    P8 --> P8_OUT{Output Directory<br/>generated_apps/...}

    %% Phase 9: Health Verification
    P8_OUT --> P9[Phase 9: Health Verification<br/>File existence checks]
    P9 --> P9_OUT{✅ App Ready}

    %% Phase 10: Learning
    P9_OUT --> P10[Phase 10: Learning<br/>PatternFeedbackIntegration]
    P10 --> REGISTER[Register Successful<br/>Code as Candidate]
    REGISTER --> PROMOTION_CHECK{Check Promotion<br/>Criteria}
    PROMOTION_CHECK -->|success_count ≥ 3| PROMOTE[Promote to PatternBank]
    PROMOTION_CHECK -->|not ready| WAIT[Wait for more successes]
    PROMOTE --> PATTERN_BANK

    %% Final Output
    P10 --> END([🎉 Generated App Ready<br/>+ Patterns Learned])

    %% Styling
    classDef phaseClass fill:#4A90E2,stroke:#2E5C8A,color:#fff
    classDef outputClass fill:#7ED321,stroke:#5FA319,color:#000
    classDef storageClass fill:#F5A623,stroke:#C77E1A,color:#000
    classDef errorClass fill:#D0021B,stroke:#9B0115,color:#fff

    class P1,P2,P3,P4,P5,P6,P6_5,P7,P8,P9,P10 phaseClass
    class P1_OUT,P2_OUT,P3_OUT,P4_OUT,P5_OUT,P6_OUT,P6_5_OUT,P7_OUT,P8_OUT,P9_OUT outputClass
    class PATTERN_BANK,ERROR_STORE storageClass
    class FAIL errorClass
```

---

## 🔄 Diagrama: Phase 6.5 Code Repair Loop (Detallado)

```mermaid
flowchart TD
    START[Generated Code<br/>from Phase 6] --> PRECHECK[CP-6.5.1: ComplianceValidator<br/>Pre-check]

    PRECHECK --> CHECK_SCORE{Compliance Score?}

    CHECK_SCORE -->|≥ 0.80| SKIP[CP-6.5.SKIP<br/>High compliance<br/>Skip repair ✅]
    CHECK_SCORE -->|< 0.80| INIT[CP-6.5.2: Initialize<br/>TestResultAdapter<br/>ErrorPatternStore]

    INIT --> CONVERT[CP-6.5.3: Convert<br/>ComplianceReport →<br/>TestResult format]

    CONVERT --> LOOP_START[CP-6.5.4: Repair Loop<br/>Iteration 1/3]

    %% Repair Loop Steps
    LOOP_START --> STEP1[Step 1: Analyze Failures<br/>Missing entities/endpoints]
    STEP1 --> STEP2[Step 2: Search RAG<br/>Similar error patterns]
    STEP2 --> STEP3[Step 3: Generate Repair Proposal<br/>LLM + Full Spec Context]

    STEP3 --> CONTEXT{Build Repair Context}
    CONTEXT --> |Missing entities<br/>Wrong entities<br/>Missing endpoints| LLM_REPAIR[LLM Call:<br/>generate_from_requirements<br/>+ repair_context]

    LLM_REPAIR --> STEP4[Step 4: Create Backup<br/>backup_code = current_code]
    STEP4 --> STEP5[Step 5: Apply Repair<br/>repaired_code = proposal]
    STEP5 --> STEP6[Step 6: Re-validate<br/>ComplianceValidator.validate]

    STEP6 --> STEP7{Step 7: Regression Check}

    STEP7 -->|new < current| REGRESSION[⚠️ Regression Detected!<br/>Rollback to backup]
    REGRESSION --> STEP8_FAIL[Step 8: Store Error Pattern<br/>ErrorPatternStore]
    STEP8_FAIL --> NO_IMPROVE{No improvement<br/>for 2 iterations?}

    STEP7 -->|new ≥ current| IMPROVED{Improvement?}
    IMPROVED -->|new > best| BETTER[✅ Better code!<br/>Update best_code]
    IMPROVED -->|new = current| SAME[= No change]

    BETTER --> STEP8_SUCCESS[Step 8: Store Success Pattern<br/>SuccessPattern]
    SAME --> NO_IMPROVE

    STEP8_SUCCESS --> TARGET_CHECK{Compliance ≥<br/>0.88 target?}
    TARGET_CHECK -->|Yes| DONE[✅ Target Achieved<br/>Exit loop]
    TARGET_CHECK -->|No| CONTINUE{Iterations<br/>< max?}

    NO_IMPROVE -->|Yes, stop| DONE
    NO_IMPROVE -->|No, continue| CONTINUE

    CONTINUE -->|Yes| LOOP_START
    CONTINUE -->|No| DONE

    %% Final metrics
    DONE --> METRICS[CP-6.5.5: Collect Metrics<br/>iterations, improvement,<br/>tests_fixed, regressions]
    SKIP --> METRICS

    METRICS --> END[Repaired Code<br/>+ Metrics<br/>→ Phase 7]

    %% Styling
    classDef goodClass fill:#7ED321,stroke:#5FA319,color:#000
    classDef badClass fill:#D0021B,stroke:#9B0115,color:#fff
    classDef processClass fill:#4A90E2,stroke:#2E5C8A,color:#fff

    class SKIP,BETTER,DONE goodClass
    class REGRESSION,STEP8_FAIL badClass
    class LOOP_START,STEP1,STEP2,STEP3,STEP4,STEP5,STEP6,STEP8_SUCCESS,METRICS processClass
```

---

## 🏗️ Diagrama: Arquitectura de Componentes

```mermaid
graph TB
    %% Top Layer: Pipeline Orchestration
    subgraph PIPELINE [Pipeline Orchestration]
        E2E[RealE2ETest<br/>10-Phase Pipeline]
        METRICS[MetricsCollector<br/>Checkpoints + Duration]
        CONTRACT[ContractValidator<br/>Phase Output Validation]
    end

    %% Phase Components
    subgraph PARSING [Phase 1-2: Parsing & Classification]
        SPEC_PARSER[SpecParser<br/>Markdown → SpecRequirements]
        REQ_CLASSIFIER[RequirementsClassifier<br/>Semantic Classification]
        DOMAIN_PATTERNS[DomainPatterns<br/>CRUD, Auth, Payment, etc.]
    end

    subgraph PLANNING [Phase 3-5: Planning & DAG]
        MULTI_PASS[MultiPassPlanner<br/>Multi-pass planning]
        DAG_BUILDER[DAGBuilder<br/>DAG construction]
        ATOMIZER[Atomization<br/>Atomic units]
    end

    subgraph CODE_GEN [Phase 6: Code Generation]
        CODE_GEN_SERVICE[CodeGenerationService<br/>LLM-based generation]
        PROMPT_FACTORY[PromptStrategyFactory<br/>File-type strategies]
        VALIDATION_FACTORY[ValidationStrategyFactory<br/>Syntax validation]
        LLM_CLIENT[EnhancedAnthropicClient<br/>Claude Sonnet 4.5]
    end

    subgraph CODE_REPAIR [Phase 6.5: Code Repair]
        COMPLIANCE_VAL[ComplianceValidator<br/>Semantic validation]
        CODE_ANALYZER[CodeAnalyzer<br/>Entity/Endpoint extraction]
        TEST_ADAPTER[TestResultAdapter<br/>Report conversion]
        REPAIR_LOOP[Repair Loop<br/>LLM-guided repairs]
    end

    subgraph VALIDATION [Phase 7: Final Validation]
        FINAL_VAL[ComplianceValidator<br/>validate_or_raise]
        THRESHOLD[Threshold Check<br/>≥ 0.80 or FAIL]
    end

    subgraph DEPLOYMENT [Phase 8-9: Deploy & Health]
        DEPLOY[Deployment<br/>Save files to disk]
        HEALTH[Health Verification<br/>File existence]
    end

    subgraph LEARNING [Phase 10: Learning]
        PATTERN_FEEDBACK[PatternFeedbackIntegration<br/>Candidate → Promotion]
        PROMOTION[Promotion Check<br/>success_count ≥ 3]
    end

    %% Storage Layer
    subgraph STORAGE [Storage & State]
        REDIS[(Redis<br/>Workflow State<br/>Temporary)]
        POSTGRES[(PostgreSQL<br/>Task History<br/>Persistent)]
        PATTERN_BANK[(PatternBank<br/>Success Patterns<br/>Qdrant)]
        ERROR_STORE[(ErrorPatternStore<br/>Error + Success<br/>Qdrant)]
    end

    %% Cognitive Services
    subgraph COGNITIVE [Cognitive Services]
        PATTERN_CLASSIFIER[PatternClassifier<br/>Pattern matching]
        SEMANTIC_SIG[SemanticTaskSignature<br/>Task signatures]
        DAG_SYNC[DAGSynchronizer<br/>Execution metrics]
    end

    %% Observability
    subgraph OBSERVABILITY [Observability]
        STRUCTURED_LOG[StructuredLogger<br/>JSON logging]
        PRECISION[PrecisionMetrics<br/>Accuracy, Precision, Recall]
    end

    %% Connections: Pipeline → Components
    E2E --> SPEC_PARSER
    E2E --> REQ_CLASSIFIER
    E2E --> MULTI_PASS
    E2E --> CODE_GEN_SERVICE
    E2E --> COMPLIANCE_VAL
    E2E --> FINAL_VAL
    E2E --> DEPLOY
    E2E --> PATTERN_FEEDBACK

    %% Phase Dependencies
    SPEC_PARSER --> REQ_CLASSIFIER
    REQ_CLASSIFIER --> MULTI_PASS
    MULTI_PASS --> ATOMIZER
    ATOMIZER --> DAG_BUILDER
    DAG_BUILDER --> CODE_GEN_SERVICE
    CODE_GEN_SERVICE --> COMPLIANCE_VAL
    COMPLIANCE_VAL --> FINAL_VAL
    FINAL_VAL --> DEPLOY
    DEPLOY --> HEALTH
    HEALTH --> PATTERN_FEEDBACK

    %% Component → Storage
    REQ_CLASSIFIER -.RAG search.-> PATTERN_BANK
    CODE_GEN_SERVICE -.retry guidance.-> ERROR_STORE
    CODE_GEN_SERVICE --> LLM_CLIENT
    CODE_GEN_SERVICE -.store success.-> ERROR_STORE
    CODE_GEN_SERVICE -.register candidate.-> PATTERN_FEEDBACK

    COMPLIANCE_VAL --> CODE_ANALYZER
    COMPLIANCE_VAL --> TEST_ADAPTER
    REPAIR_LOOP --> LLM_CLIENT
    REPAIR_LOOP -.store patterns.-> ERROR_STORE

    PATTERN_FEEDBACK -.promotion.-> PATTERN_BANK

    %% State Management
    E2E --> REDIS
    E2E --> POSTGRES

    %% Observability
    E2E --> METRICS
    E2E --> CONTRACT
    E2E --> STRUCTURED_LOG
    E2E --> PRECISION

    %% Cognitive Integration
    CODE_GEN_SERVICE --> DAG_SYNC
    CODE_GEN_SERVICE --> SEMANTIC_SIG
    REQ_CLASSIFIER --> PATTERN_CLASSIFIER

    %% Styling
    classDef pipelineClass fill:#9013FE,stroke:#6A0DAD,color:#fff
    classDef phaseClass fill:#4A90E2,stroke:#2E5C8A,color:#fff
    classDef storageClass fill:#F5A623,stroke:#C77E1A,color:#000
    classDef cognitiveClass fill:#BD10E0,stroke:#8B0AA8,color:#fff
    classDef obsClass fill:#50E3C2,stroke:#3AAA94,color:#000

    class E2E,METRICS,CONTRACT pipelineClass
    class SPEC_PARSER,REQ_CLASSIFIER,MULTI_PASS,CODE_GEN_SERVICE,COMPLIANCE_VAL,FINAL_VAL,DEPLOY,PATTERN_FEEDBACK phaseClass
    class REDIS,POSTGRES,PATTERN_BANK,ERROR_STORE storageClass
    class PATTERN_CLASSIFIER,SEMANTIC_SIG,DAG_SYNC cognitiveClass
    class STRUCTURED_LOG,PRECISION obsClass
```

---

## 📊 Diagrama: Data Flow (SpecRequirements → Generated Code)

```mermaid
flowchart LR
    %% Input Spec
    SPEC[Spec File<br/>simple_task_api.md]

    %% Phase 1 Output
    SPEC_REQ["SpecRequirements {<br/>
    requirements: [F1, F2, ...],<br/>
    entities: [Task {<br/>
      fields: [id, title, status],<br/>
      validations: [...]<br/>
    }],<br/>
    endpoints: [<br/>
      POST /tasks,<br/>
      GET /tasks<br/>
    ],<br/>
    business_logic: [...]<br/>
    }"]

    %% Phase 2 Output
    CLASSIFIED["Classified Requirements {<br/>
    F1: {domain: 'crud', priority: 'MUST'},<br/>
    F2: {domain: 'crud', priority: 'MUST'}<br/>
    }<br/>
    Dependency Graph {<br/>
    F1 → F2<br/>
    }"]

    %% Phase 3-5 Output
    DAG["DAG {<br/>
    nodes: [<br/>
      {id: 'node_0', name: 'Create Task'},<br/>
      {id: 'node_1', name: 'List Tasks'}<br/>
    ],<br/>
    edges: [<br/>
      {from: 'node_0', to: 'node_1'}<br/>
    ],<br/>
    waves: [[node_0], [node_1]]<br/>
    }"]

    %% Phase 6 Output
    CODE["Generated Code {<br/>
    'main.py': '''<br/>
    from fastapi import FastAPI, HTTPException<br/>
    from pydantic import BaseModel<br/>
    from uuid import UUID, uuid4<br/>
    <br/>
    class Task(BaseModel):<br/>
    &nbsp;&nbsp;id: UUID<br/>
    &nbsp;&nbsp;title: str<br/>
    &nbsp;&nbsp;status: str<br/>
    <br/>
    app = FastAPI()<br/>
    tasks = {}<br/>
    <br/>
    @app.post('/tasks')<br/>
    def create_task(task: Task): ...<br/>
    <br/>
    @app.get('/tasks')<br/>
    def list_tasks(): ...<br/>
    ''',<br/>
    'requirements.txt': '...',<br/>
    'README.md': '...'<br/>
    }"]

    %% Phase 6.5 Output
    COMPLIANCE["ComplianceReport {<br/>
    overall_compliance: 0.85,<br/>
    entities_implemented: ['Task'],<br/>
    entities_expected: ['Task'],<br/>
    endpoints_implemented: [<br/>
      'POST /tasks',<br/>
      'GET /tasks'<br/>
    ],<br/>
    endpoints_expected: [<br/>
      'POST /tasks',<br/>
      'GET /tasks'<br/>
    ],<br/>
    missing_requirements: []<br/>
    }"]

    %% Phase 7 Output
    VALIDATED["✅ Validated<br/>Compliance: 85%<br/>Pass Threshold: 80%"]

    %% Phase 8-9 Output
    DEPLOYED["📁 generated_apps/<br/>simple_task_api_1763634331/<br/>
    ├── main.py<br/>
    ├── requirements.txt<br/>
    └── README.md"]

    %% Phase 10 Output
    LEARNED["🧠 Learned Patterns<br/>
    Candidate ID: abc123<br/>
    Success Count: 1<br/>
    (Will promote at count 3)"]

    %% Flow
    SPEC --> SPEC_REQ
    SPEC_REQ --> CLASSIFIED
    CLASSIFIED --> DAG
    DAG --> CODE
    CODE --> COMPLIANCE
    COMPLIANCE --> VALIDATED
    VALIDATED --> DEPLOYED
    DEPLOYED --> LEARNED

    %% Styling
    classDef inputClass fill:#E8E8E8,stroke:#999,color:#000
    classDef processClass fill:#4A90E2,stroke:#2E5C8A,color:#fff
    classDef validClass fill:#7ED321,stroke:#5FA319,color:#000
    classDef outputClass fill:#F5A623,stroke:#C77E1A,color:#000

    class SPEC inputClass
    class SPEC_REQ,CLASSIFIED,DAG,CODE,COMPLIANCE processClass
    class VALIDATED validClass
    class DEPLOYED,LEARNED outputClass
```

---

## 🔄 Diagrama: Cognitive Feedback Loop (RAG + Learning)

```mermaid
flowchart TD
    %% Code Generation Phase
    TASK[Code Generation Task<br/>Task: 'Create Product endpoint']

    TASK --> ATTEMPT1{Attempt 1}
    ATTEMPT1 --> GENERATE1[Generate Code<br/>Standard prompt]
    GENERATE1 --> VALIDATE1{Validate Syntax}

    VALIDATE1 -->|✅ Valid| SUCCESS[Store Success Pattern<br/>ErrorPatternStore]
    VALIDATE1 -->|❌ Invalid| ERROR1[Store Error Pattern<br/>SyntaxError: incomplete class]

    %% Retry with RAG
    ERROR1 --> ATTEMPT2{Attempt 2<br/>Retry with RAG}
    ATTEMPT2 --> RAG_SEARCH[Search Similar Errors<br/>ErrorPatternStore]
    RAG_SEARCH --> SIMILAR[Found 3 similar errors<br/>All had incomplete class def]

    ATTEMPT2 --> RAG_SUCCESS[Search Success Patterns<br/>ErrorPatternStore]
    RAG_SUCCESS --> PATTERNS[Found 5 success patterns<br/>Complete class definitions]

    SIMILAR --> ENHANCED_PROMPT[Build Enhanced Prompt<br/>with RAG feedback]
    PATTERNS --> ENHANCED_PROMPT

    ENHANCED_PROMPT --> GENERATE2[Generate Code<br/>+ explicit class completion instruction]
    GENERATE2 --> VALIDATE2{Validate Syntax}

    VALIDATE2 -->|✅ Valid| SUCCESS2[✅ Store Success Pattern<br/>+ metadata: used_feedback=True]
    VALIDATE2 -->|❌ Invalid| ERROR2[Store Error Pattern<br/>Attempt 2]

    ERROR2 --> ATTEMPT3{Attempt 3<br/>max_retries reached}
    ATTEMPT3 --> FAIL[❌ Code Generation Failed<br/>After 3 attempts]

    %% Success Path: Pattern Promotion
    SUCCESS --> REGISTER[Register as Candidate<br/>PatternFeedbackIntegration]
    SUCCESS2 --> REGISTER

    REGISTER --> CANDIDATE_STORE[(Candidate Store<br/>success_count++)]

    CANDIDATE_STORE --> CHECK_PROMOTION{Check Promotion<br/>success_count ≥ 3?}

    CHECK_PROMOTION -->|No| WAIT[Wait for more<br/>successful uses]
    CHECK_PROMOTION -->|Yes| DUAL_VAL[Dual Validation<br/>Syntactic + Semantic]

    DUAL_VAL -->|✅ Pass| PROMOTE[Promote to PatternBank<br/>Available for future tasks]
    DUAL_VAL -->|❌ Fail| REJECT[Reject promotion<br/>Quality issues]

    PROMOTE --> PATTERN_BANK[(PatternBank<br/>Qdrant Vector Store)]

    %% Future Task Uses Pattern
    PATTERN_BANK -.reuse in future tasks.-> NEW_TASK[New Similar Task<br/>Search PatternBank]
    NEW_TASK --> PATTERN_MATCH[Pattern Match<br/>similarity > 0.45]
    PATTERN_MATCH --> REUSE[Reuse Promoted Pattern<br/>Fast generation]

    %% Styling
    classDef successClass fill:#7ED321,stroke:#5FA319,color:#000
    classDef errorClass fill:#D0021B,stroke:#9B0115,color:#fff
    classDef ragClass fill:#F5A623,stroke:#C77E1A,color:#000
    classDef storeClass fill:#4A90E2,stroke:#2E5C8A,color:#fff

    class SUCCESS,SUCCESS2,PROMOTE,REUSE successClass
    class ERROR1,ERROR2,FAIL,REJECT errorClass
    class RAG_SEARCH,RAG_SUCCESS,SIMILAR,PATTERNS,ENHANCED_PROMPT ragClass
    class CANDIDATE_STORE,PATTERN_BANK storeClass
```

---

## 🎯 Diagrama: Metrics Collection Flow

```mermaid
flowchart LR
    %% Phase Execution
    PHASE[Phase Execution<br/>e.g., Code Generation]

    %% Metrics Collector
    PHASE --> START[metrics.start_phase<br/>'code_generation']
    START --> CP1[metrics.add_checkpoint<br/>'CP-6.1: Started']
    CP1 --> CP2[metrics.add_checkpoint<br/>'CP-6.2: Models generated']
    CP2 --> COMPLETE[metrics.complete_phase<br/>'code_generation']

    %% Error Tracking
    PHASE -.on error.-> ERROR[metrics.record_error<br/>critical=True/False]

    %% Precision Tracking
    PHASE --> PRECISION[PrecisionMetrics<br/>Track expected vs actual]
    PRECISION --> CALC[Calculate:<br/>- Accuracy<br/>- Precision<br/>- Recall<br/>- F1-Score]

    %% Contract Validation
    COMPLETE --> CONTRACT[ContractValidator<br/>validate_phase_output]
    CONTRACT --> VALIDATE{Output Valid?}
    VALIDATE -->|✅ Yes| PASS[Contract Passed]
    VALIDATE -->|❌ No| VIOLATION[Contract Violation<br/>Log + Continue]

    %% Final Report
    PASS --> FINALIZE[metrics.finalize]
    VIOLATION --> FINALIZE
    ERROR --> FINALIZE
    CALC --> FINALIZE

    FINALIZE --> REPORT["Final Report {<br/>
    overall_status: 'success',<br/>
    total_duration_ms: 45231,<br/>
    overall_accuracy: 0.94,<br/>
    pipeline_precision: 0.88,<br/>
    pattern_precision: 0.85,<br/>
    classification_accuracy: 0.90,<br/>
    compliance_score: 0.85,<br/>
    repair_iterations: 2,<br/>
    tests_fixed: 3,<br/>
    patterns_promoted: 1,<br/>
    contract_violations: 0,<br/>
    phases: {...}<br/>
    }"]

    REPORT --> SAVE[Save to JSON<br/>metrics/real_e2e_*.json]

    %% Styling
    classDef metricsClass fill:#50E3C2,stroke:#3AAA94,color:#000
    classDef validClass fill:#7ED321,stroke:#5FA319,color:#000
    classDef errorClass fill:#D0021B,stroke:#9B0115,color:#fff

    class START,CP1,CP2,COMPLETE,PRECISION,FINALIZE metricsClass
    class PASS,CALC validClass
    class ERROR,VIOLATION errorClass
```

---

## 🔧 Diagrama: Strategy Pattern (Prompt & Validation)

```mermaid
graph TD
    %% Input
    TASK[MasterPlan Task<br/>name, description,<br/>target_files]

    %% File Type Detection
    TASK --> DETECTOR[FileTypeDetector<br/>Analyze task metadata]
    DETECTOR --> DETECTION["FileTypeDetection {<br/>
    file_type: FileType.PYTHON,<br/>
    confidence: 0.95,<br/>
    reasoning: 'target_files ends with .py'<br/>
    }"]

    %% Strategy Selection
    DETECTION --> PROMPT_FACTORY[PromptStrategyFactory<br/>get_strategy]
    DETECTION --> VAL_FACTORY[ValidationStrategyFactory<br/>get_strategy]

    %% Prompt Strategies
    PROMPT_FACTORY --> PROMPT_STRATEGY{file_type?}
    PROMPT_STRATEGY -->|PYTHON| PY_PROMPT[PythonPromptStrategy<br/>FastAPI, Pydantic, type hints]
    PROMPT_STRATEGY -->|MARKDOWN| MD_PROMPT[MarkdownPromptStrategy<br/>Headings, lists, tables]
    PROMPT_STRATEGY -->|YAML| YAML_PROMPT[YamlPromptStrategy<br/>Valid YAML structure]
    PROMPT_STRATEGY -->|JSON| JSON_PROMPT[JsonPromptStrategy<br/>Valid JSON structure]

    PY_PROMPT --> GENERATE[Generate Prompt<br/>File-specific instructions]
    MD_PROMPT --> GENERATE
    YAML_PROMPT --> GENERATE
    JSON_PROMPT --> GENERATE

    GENERATE --> LLM[LLM Call<br/>with optimized prompt]

    %% Validation Strategies
    LLM --> CODE[Generated Code]
    CODE --> VAL_STRATEGY{file_type?}

    VAL_STRATEGY -->|PYTHON| PY_VAL[PythonValidationStrategy<br/>compile check]
    VAL_STRATEGY -->|MARKDOWN| MD_VAL[MarkdownValidationStrategy<br/>Heading structure]
    VAL_STRATEGY -->|YAML| YAML_VAL[YamlValidationStrategy<br/>yaml.safe_load]
    VAL_STRATEGY -->|JSON| JSON_VAL[JsonValidationStrategy<br/>json.loads]

    PY_VAL --> VALIDATE[Validate Code<br/>is_valid, error_message]
    MD_VAL --> VALIDATE
    YAML_VAL --> VALIDATE
    JSON_VAL --> VALIDATE

    VALIDATE -->|✅ Valid| SUCCESS[Code Accepted]
    VALIDATE -->|❌ Invalid| RETRY[Store Error<br/>+ Retry with feedback]

    %% Extensibility
    PROMPT_FACTORY -.add new strategy.-> NEW_PROMPT[New Language Strategy<br/>e.g., TypeScriptPromptStrategy]
    VAL_FACTORY -.add new strategy.-> NEW_VAL[New Validation Strategy<br/>e.g., TypeScriptValidationStrategy]

    %% Styling
    classDef strategyClass fill:#9013FE,stroke:#6A0DAD,color:#fff
    classDef validClass fill:#7ED321,stroke:#5FA319,color:#000
    classDef errorClass fill:#D0021B,stroke:#9B0115,color:#fff

    class PROMPT_FACTORY,VAL_FACTORY,PY_PROMPT,MD_PROMPT,YAML_PROMPT,JSON_PROMPT,PY_VAL,MD_VAL,YAML_VAL,JSON_VAL strategyClass
    class SUCCESS validClass
    class RETRY errorClass
```

---

## 📦 Diagrama: State Management (Redis + PostgreSQL)

```mermaid
flowchart TD
    %% Workflow Start
    USER[User Request<br/>'Create task management API']

    USER --> CREATE_PROJECT[PostgresManager<br/>create_project]
    CREATE_PROJECT --> PROJECT_DB[(PostgreSQL<br/>projects table)]
    PROJECT_DB --> PROJECT_ID[project_id: UUID]

    USER --> CREATE_WORKFLOW[Generate workflow_id<br/>UUID]

    %% Initial State
    PROJECT_ID --> INIT_STATE["Initial State {<br/>
    user_request: '...',<br/>
    workflow_id: 'abc-123',<br/>
    project_id: 'xyz-789',<br/>
    current_task: 'starting',<br/>
    messages: [],<br/>
    generated_code: ''<br/>
    }"]

    %% Save to Redis
    INIT_STATE --> REDIS_SAVE[RedisManager<br/>save_workflow_state]
    REDIS_SAVE --> REDIS[(Redis<br/>workflow:abc-123<br/>TTL: 24h)]

    %% Execute Workflow
    INIT_STATE --> WORKFLOW[LangGraph Workflow<br/>Execute agents]

    %% Agent Node Execution
    WORKFLOW --> AGENT[Agent Node<br/>stateful_agent]

    %% Parallel: Update Redis + PostgreSQL
    AGENT --> UPDATE_REDIS[Update Redis State<br/>add message, update task]
    UPDATE_REDIS --> REDIS

    AGENT --> CREATE_TASK[PostgresManager<br/>create_task]
    CREATE_TASK --> TASKS_DB[(PostgreSQL<br/>tasks table)]
    TASKS_DB --> TASK_ID[task_id: UUID]

    AGENT --> UPDATE_STATUS[PostgresManager<br/>update_task_status<br/>'in_progress']
    UPDATE_STATUS --> TASKS_DB

    %% Code Generation
    AGENT --> GENERATE[Generate Code<br/>LLM call]
    GENERATE --> COST[PostgresManager<br/>track_cost<br/>model, tokens, USD]
    COST --> COSTS_DB[(PostgreSQL<br/>llm_costs table)]

    %% Complete Task
    GENERATE --> COMPLETE[PostgresManager<br/>update_task_status<br/>'completed' + output]
    COMPLETE --> TASKS_DB

    %% Final State
    COMPLETE --> FINAL_STATE["Final State {<br/>
    messages: [...],<br/>
    current_task: 'completed',<br/>
    generated_code: '...',<br/>
    task_id: 'task-456'<br/>
    }"]

    FINAL_STATE --> SAVE_FINAL[RedisManager<br/>save_workflow_state]
    SAVE_FINAL --> REDIS

    %% Retrieval
    REDIS -.get_workflow_state.-> RETRIEVE_REDIS[Retrieve workflow state<br/>by workflow_id]
    TASKS_DB -.get_task.-> RETRIEVE_PG[Retrieve task history<br/>by task_id]

    %% Styling
    classDef storageClass fill:#F5A623,stroke:#C77E1A,color:#000
    classDef processClass fill:#4A90E2,stroke:#2E5C8A,color:#fff
    classDef dataClass fill:#E8E8E8,stroke:#999,color:#000

    class REDIS,PROJECT_DB,TASKS_DB,COSTS_DB storageClass
    class CREATE_PROJECT,CREATE_WORKFLOW,WORKFLOW,AGENT,GENERATE,COST processClass
    class INIT_STATE,FINAL_STATE,PROJECT_ID,TASK_ID dataClass
```

---

**Última actualización**: 2025-11-20
