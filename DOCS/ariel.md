╭─kwar@THOR ~/code/agentic-ai  ‹feature/validation-scaling-phase1*›
╰─➤  PRODUCTION_MODE=true PYTHONPATH=/home/kwar/code/agentic-ai timeout 180 python tests/e2e/real_e2e_full_pipeline.py tests/e2e/test_specs/ecommerce_api_simple.md 2>&1 | tee /tmp/backend_generator_test.log

======================================================================
🚀 REAL E2E TEST: Full Pipeline Execution
======================================================================
📄 Spec: tests/e2e/test_specs/ecommerce_api_simple.md
📁 Output: tests/e2e/generated_apps/ecommerce_api_simple_1763919546
======================================================================


📊 Progress tracking enabled


  🔄 Loading PatternBank... ✓
  🔄 Loading PatternClassifier... ✓
  🔄 Loading MultiPassPlanner... ✓
  🔄 Loading RequirementsClassifier... ✓
  🔄 Loading ComplianceValidator... ✓
  🔄 Loading TestResultAdapter... ✓
  🔄 Loading ErrorPatternStore... ✓
  🔄 Loading CodeGenerationService... ✓

🔧 Service Initialization
  ✓ PatternBank                         ✓ PatternClassifier                   ✓ MultiPassPlanner                    ✓ RequirementsClassifier
  ✓ ComplianceValidator                 ✓ TestResultAdapter                   ✓ ErrorPatternStore                   ✓ CodeGenerationService
  ✓ PatternFeedbackIntegration

📋 Phase 1: Spec Ingestion (Enhanced with SpecParser)
  ✓ Checkpoint: CP-1.1: Spec loaded from file (1/4)
  ✓ Checkpoint: CP-1.2: Requirements extracted (2/4)
    - Functional requirements: 17
    - Entities: 4
    - Endpoints: 17
    - Business logic rules: 8
  ✓ Checkpoint: CP-1.3: Context loaded (3/4)
  ✓ Checkpoint: CP-1.4: Complexity assessed (4/4)
✅ Phase Completed: spec_ingestion (18505ms)
  ✅ Contract validation: PASSED
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ⏳ Requirements Analysis     [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Multi-Pass Planning       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Atomization               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ DAG Construction          [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------

  📊 Overall Progress: [██░░░░░░░░░░░░░░░░░░░░░░░]   9%
     1/11 phases completed
  🕐 Estimated Total:  00h 05m 02s | ETA: 18:44:09

================================================================================


✨ Phase 1.5: Validation Scaling (Pattern + LLM + Graph)
    - Total validations extracted: 45
      • format: 15
      • presence: 19
      • range: 4
      • relationship: 5
      • stock_constraint: 1
      • workflow_constraint: 1
    - Coverage: 45/62 (72.6%)
    - Average confidence: 0.80
  ✅ Contract validation: PASSED
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ⏳ Requirements Analysis     [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Multi-Pass Planning       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Atomization               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ DAG Construction          [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------

  📊 Overall Progress: [██░░░░░░░░░░░░░░░░░░░░░░░]   9%
     1/11 phases completed
  🕐 Estimated Total:  00h 12m 50s | ETA: 18:51:56

================================================================================


================================================================================
🔍 Phase 2: Requirements Analysis
================================================================================
📋 Semantic Classification (RequirementsClassifier)
📝 Classifying requirements semantically...
✓ Classification completed
    ├─ Total requirements: 24
    ├─ Functional: 17
    ├─ Non-functional: 7
    ├─ Dependency graph nodes: 5
    ├─ Valid DAG: True
📦 Domain Distribution
    ├─ crud: 12
    ├─ authentication: 4
    ├─ payment: 4
    ├─ workflow: 2
    ├─ search: 2
📋 Ground Truth Validation
📝 Validating against ground truth...
ℹ️ Loaded ground truth
    ├─ Requirements: 17
📊 Classification Metrics
    ├─ Accuracy: 33.3%
    ├─ Precision: 85.0%
  ✓ Checkpoint: CP-2.1: Functional requirements (1/5)
  ✓ Checkpoint: CP-2.2: Non-functional requirements (2/5)
  ✓ Checkpoint: CP-2.3: Dependencies identified (3/5)
  ✓ Checkpoint: CP-2.4: Constraints extracted (4/5)
📋 Pattern Matching & Analysis
📝 Searching for similar patterns (real)...
    ✓ Found 10 matching patterns
✓ Pattern matching completed
    ├─ Patterns found: 10
  ✓ Checkpoint: CP-2.5: Patterns matched (5/5)
📋 Validation Checkpoints
✓ Checkpoint CP-2.1: Functional requirements classification
✓ Checkpoint CP-2.2: Non-functional requirements extraction
✓ Checkpoint CP-2.3: Dependency identification
✓ Checkpoint CP-2.4: Constraint extraction
✓ Checkpoint CP-2.5: Pattern matching validation
✅ Phase Completed: requirements_analysis (951ms)
📊 Phase Metrics
    ├─ Classification Accuracy: 33.3%
    ├─ Pattern Precision: 80.0%
    ├─ Pattern Recall: 47.1%
    ├─ Pattern F1-Score: 59.3%
    ├─ Contract Validation: PASSED
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  🔷 Requirements Analysis     [░░░░░░░░░░░░░░░░░░]   0%  (Searching for similar patterns (real)...)
  ⏳ Multi-Pass Planning       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Atomization               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ DAG Construction          [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 11s | 💾 Memory: 2879.0 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:     34 | 🔍 Qdrant Queries:     12 | 🚀 Tokens Used:   120000

  📊 Overall Progress: [██░░░░░░░░░░░░░░░░░░░░░░░]   9%
     1/11 phases completed
  🕐 Estimated Total:  00h 13m 01s | ETA: 18:52:08

================================================================================

================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ⏳ Multi-Pass Planning       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Atomization               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ DAG Construction          [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 11s | 💾 Memory: 2879.0 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:     34 | 🔍 Qdrant Queries:     12 | 🚀 Tokens Used:   120000

  📊 Overall Progress: [████░░░░░░░░░░░░░░░░░░░░░]  18%
     2/11 phases completed
  🕐 Estimated Total:  00h 06m 30s | ETA: 18:45:37

================================================================================


📐 Phase 3: Multi-Pass Planning
  ✓ Checkpoint: CP-3.1: Initial DAG created (1/5)
  ✓ Checkpoint: CP-3.2: Dependencies refined (2/5)
  ✓ Checkpoint: CP-3.3: Resources optimized (3/5)
  ✓ Checkpoint: CP-3.4: Cycles repaired (4/5)
  ✓ Checkpoint: CP-3.5: DAG validated (5/5)
  📋 Using DAG ground truth: 17 nodes, 15 edges expected
✅ Phase Completed: multi_pass_planning (103ms)
  📊 DAG Accuracy: 100.0%
  ✅ Contract validation: PASSED
  🔍 Execution Order Validation: 100.0% (violations: 0)
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ⏳ Atomization               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ DAG Construction          [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 11s | 💾 Memory: 2879.0 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:     34 | 🔍 Qdrant Queries:     12 | 🚀 Tokens Used:   120000

  📊 Overall Progress: [██████░░░░░░░░░░░░░░░░░░░]  27%
     3/11 phases completed
  🕐 Estimated Total:  00h 04m 21s | ETA: 18:43:27

================================================================================


⚛️ Phase 4: Atomization
  ✓ Checkpoint: CP-4.1: Step 1 (1/5)
  ✓ Checkpoint: CP-4.2: Step 2 (2/5)
  ✓ Checkpoint: CP-4.3: Step 3 (3/5)
  ✓ Checkpoint: CP-4.4: Step 4 (4/5)
  ✓ Checkpoint: CP-4.5: Atomization complete (5/5)
✅ Phase Completed: atomization (1303ms)
  📊 Atomization Quality: 87.5%
  ✅ Contract validation: PASSED
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ⏳ DAG Construction          [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 12s | 💾 Memory: 2879.0 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:     34 | 🔍 Qdrant Queries:     12 | 🚀 Tokens Used:   120000

  📊 Overall Progress: [█████████░░░░░░░░░░░░░░░░]  36%
     4/11 phases completed
  🕐 Estimated Total:  00h 03m 19s | ETA: 18:42:26

================================================================================


🔗 Phase 5: DAG Construction
  ✓ Checkpoint: CP-5.1: Step 1 (1/5)
  ✓ Checkpoint: CP-5.2: Step 2 (2/5)
  ✓ Checkpoint: CP-5.3: Step 3 (3/5)
  ✓ Checkpoint: CP-5.4: Step 4 (4/5)
  ✓ Checkpoint: CP-5.5: Step 5 (5/5)
✅ Phase Completed: dag_construction (1604ms)
  ✅ Contract validation: PASSED
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ⏳ Code Generation           [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 14s | 💾 Memory: 2879.0 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:     34 | 🔍 Qdrant Queries:     12 | 🚀 Tokens Used:   120000

  📊 Overall Progress: [███████████░░░░░░░░░░░░░░]  45%
     5/11 phases completed
  🕐 Estimated Total:  00h 02m 43s | ETA: 18:41:49

================================================================================


================================================================================
🔍 Phase 6: Code Generation
================================================================================
  ✓ Checkpoint: CP-6.1: Code generation started (1/5)
🏗️ Code Generation Initialization
✓ Checkpoint CP-6.1: Code generation started
📝 Generating code from requirements...
ℹ️ Dependency waves prepared
    ├─ Wave count: 6
    ├─ Validation phase: Phase 7
🔧 Code Composition
  📝 Composing production-ready application... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
  📦 Parsed production mode output: 60 files
📚 Pattern Retrieval from PatternBank
📦 Categories Retrieved
    ├─ Core Config: 1
    ├─ Database (Async): 1
    ├─ Observability: 5
    ├─ Models (Pydantic): 1
    ├─ Models (SQLAlchemy): 1
    ├─ Repository Pattern: 1
    ├─ Business Logic: 1
    ├─ API Routes: 1
    ├─ Security Hardening: 1
    ├─ Test Infrastructure: 7
    ├─ Docker Infrastructure: 4
    ├─ Project Config: 3
✓ Total patterns retrieved: 27
    ├─ Categories: 12
    ├─ Status: Ready for composition

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    📦 Code Generation Components
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    Component                              |     Patterns     |     Files Generated     | Status
  --------------------------------------------------------------------------------------------------------------
    Core                                     |         4        |           4           |   ✅
    Models                                   |         3        |           3           |   ✅
    Services                                 |         5        |           5           |   ✅
    API Routes                               |         8        |           8           |   ✅
    Middleware                               |         1        |           1           |   ✅
    Migrations                               |         4        |           4           |   ✅
    Tests                                    |         8        |           8           |   ✅
    Other                                    |        27        |          27           |   ✅
  --------------------------------------------------------------------------------------------------------------
    ⏱️  17824ms                              |        📦 144.0KB       |          📊 60          |  ✅ 100%
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

✓ Code generation completed
    ├─ Total files: 60
    ├─ Duration: 17.8s
  ✓ Checkpoint: CP-6.2: Models generated (2/5)
  ✓ Checkpoint: CP-6.3: Routes generated (3/5)
✓ Checkpoint CP-6.2: Pattern retrieval completed
✓ Checkpoint CP-6.3: Code composition started
  ✓ Checkpoint: CP-6.4: Tests generated (4/5)
✓ Checkpoint CP-6.4: File generation completed
  ✓ Checkpoint: CP-6.5: Code generation complete (5/5)
✓ Checkpoint CP-6.5: Production mode validation
✅ Phase Completed: wave_execution (17926ms)
📊 Generation Metrics
    ├─ Execution Success Rate: 100.0%
    ├─ Recovery Rate: 0.0%
    ├─ Contract Validation: PASSED
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  🔷 Code Generation           [░░░░░░░░░░░░░░░░░░]   0%  (Generating code from requirements...)
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 32s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [███████████░░░░░░░░░░░░░░]  45%
     5/11 phases completed
  🕐 Estimated Total:  00h 03m 22s | ETA: 18:42:29

================================================================================

================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ⏳ Deployment                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 32s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [█████████████░░░░░░░░░░░░]  54%
     6/11 phases completed
  🕐 Estimated Total:  00h 02m 48s | ETA: 18:41:55

================================================================================


📦 Phase 8: Deployment

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    💾 Deployment Complete
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    Metric                                  |           Result            |     Status
  --------------------------------------------------------------------------------------------------------------
    Files Saved                             |               60        |       ✅
    Total Size                              |          144.0KB        |       ✅
    Deployment Time                         |              6ms        |       ✅
    Output Location                         |  .../_1763919546        |       ✅
  --------------------------------------------------------------------------------------------------------------
    ✅ All 60 files successfully deployed to disk
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

  ✓ Checkpoint: CP-8.1: Files saved to disk (1/5)
  ✓ Checkpoint: CP-8.2: Directory structure created (2/5)
  ✓ Checkpoint: CP-8.3: README generated (3/5)
  ✓ Checkpoint: CP-8.4: Dependencies documented (4/5)
  ✓ Checkpoint: CP-8.5: Deployment complete (5/5)
✅ Phase Completed: deployment (107ms)
  ✅ Generated app saved to: tests/e2e/generated_apps/ecommerce_api_simple_1763919546
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ✅ Deployment                [██████████████████] 100%  (Files saved: 60/60)
  ⏳ Code Repair               [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 32s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [███████████████░░░░░░░░░░]  63%
     7/11 phases completed
  🕐 Estimated Total:  00h 02m 24s | ETA: 18:41:31

================================================================================


🔧 Phase 6.5: Code Repair (Task Group 4)

  🔍 CP-6.5.1: Running compliance pre-check...
Successfully imported FastAPI app
Extracted 4 entities from OpenAPI schemas: ['Cart', 'Customer', 'Order', 'Product']
After checking entities.py: 4 entities found: ['Cart', 'Customer', 'Order', 'Product']
Extracted 21 endpoints from OpenAPI paths
Extracted 50 validations from OpenAPI schemas
After checking schemas.py: 60 validations found
Using validation ground truth: 47 validations from ground truth
OpenAPI-based compliance validation complete: 98.4% (entities: 100.0%, endpoints: 100.0%, validations: 92.2%)
  ✓ Pre-check complete: 98.4% compliance
    - Entities: 4/4
    - Endpoints: 21/17

  🤖 CP-6.5.2: Initializing repair dependencies...
  ✓ Dependencies initialized

  🔄 CP-6.5.3: Converting ComplianceReport to TestResult format...
Converting ComplianceReport with 98.4% compliance
Converted 8 compliance failures to TestResult format
  ✓ Test results adapted: 8 failures converted

  🔁 CP-6.5.4: Executing repair loop...
📋 Repair Iterations
📝 Starting repair loop (max 3 iterations)...
⏳ Iteration 1/3
📝 Analyzing 8 failures...
📝 Applying repairs...
CodeRepair: 0 missing entities, 4 missing endpoints, 4 missing validations
Endpoint function create_product already exists in product.py, skipping
Added endpoint GET /products to product.py
Added endpoint POST /customers to customer.py
Added endpoint POST /carts to cart.py
Parsed GT validation 'Cart.status: required' → Cart.status required
Added required Field(...) to Cart.status
Added required=True to Cart.status in schemas.py
Parsed GT validation 'Order.status: required' → Order.status required
Made Order.status required (removed default=None)
Added required=True to Order.status in schemas.py
Parsed GT validation 'Order.payment_status: required' → Order.payment_status required
Added required Field(...) to Order.payment_status
Added required=True to Order.payment_status in schemas.py
Parsed GT validation 'Product.is_active: required' → Product.is_active required
Added required Field(...) to Product.is_active
Added required=True to Product.is_active in schemas.py
✓ Applied 8 repairs
    ├─ Endpoints added: 4
    ├─ Validations added: 4
📝 Re-validating compliance...
Validating app at /home/kwar/code/agentic-ai/tests/e2e/generated_apps/ecommerce_api_simple_1763919546 using OpenAPI schema
Converting DATABASE_URL to async driver for validation
Successfully imported FastAPI app
Extracted 4 entities from OpenAPI schemas: ['Cart', 'Customer', 'Order', 'Product']
After checking entities.py: 4 entities found: ['Cart', 'Customer', 'Order', 'Product']
Extracted 21 endpoints from OpenAPI paths
Extracted 53 validations from OpenAPI schemas
After checking schemas.py: 63 validations found
Using validation ground truth: 47 validations from ground truth
OpenAPI-based compliance validation complete: 99.6% (entities: 100.0%, endpoints: 100.0%, validations: 98.0%)
ℹ️ Compliance: 98.4% → 99.6%
    ├─ Status: ✅
    ├─ Delta: +1.2%
✓ Improvement detected!
    ├─ Improvement: +1.2%
Batches: 100%|██████████| 1/1 [00:00<00:00, 14.45it/s]
⏳ Iteration 2/3
📝 Analyzing 8 failures...
📝 Applying repairs...
CodeRepair: 0 missing entities, 4 missing endpoints, 1 missing validations
Endpoint function create_product already exists in product.py, skipping
Endpoint function get_all_products already exists in product.py, skipping
Endpoint function create_customer already exists in customer.py, skipping
Endpoint function create_cart already exists in cart.py, skipping
Parsed GT validation 'Order.status: required' → Order.status required
Made Order.status required (removed default=None)
Added required=True to Order.status in schemas.py
✓ Applied 5 repairs
    ├─ Endpoints added: 4
    ├─ Validations added: 1
📝 Re-validating compliance...
Validating app at /home/kwar/code/agentic-ai/tests/e2e/generated_apps/ecommerce_api_simple_1763919546 using OpenAPI schema
Converting DATABASE_URL to async driver for validation
Successfully imported FastAPI app
Extracted 4 entities from OpenAPI schemas: ['Cart', 'Customer', 'Order', 'Product']
After checking entities.py: 4 entities found: ['Cart', 'Customer', 'Order', 'Product']
Extracted 21 endpoints from OpenAPI paths
Extracted 53 validations from OpenAPI schemas
After checking schemas.py: 63 validations found
Using validation ground truth: 47 validations from ground truth
OpenAPI-based compliance validation complete: 99.6% (entities: 100.0%, endpoints: 100.0%, validations: 98.0%)
ℹ️ Compliance: 99.6% → 99.6%
    ├─ Status: ⚠️
    ├─ Delta: +0.0%
ℹ️ No improvement
    ├─ Status: =
    ├─ Message: Plateau reached
⏳ Iteration 3/3
📝 Analyzing 8 failures...
📝 Applying repairs...
CodeRepair: 0 missing entities, 4 missing endpoints, 1 missing validations
Endpoint function create_product already exists in product.py, skipping
Endpoint function get_all_products already exists in product.py, skipping
Endpoint function create_customer already exists in customer.py, skipping
Endpoint function create_cart already exists in cart.py, skipping
Parsed GT validation 'Order.status: required' → Order.status required
Made Order.status required (removed default=None)
Added required=True to Order.status in schemas.py
✓ Applied 5 repairs
    ├─ Endpoints added: 4
    ├─ Validations added: 1
📝 Re-validating compliance...
Validating app at /home/kwar/code/agentic-ai/tests/e2e/generated_apps/ecommerce_api_simple_1763919546 using OpenAPI schema
Converting DATABASE_URL to async driver for validation
Successfully imported FastAPI app
Extracted 4 entities from OpenAPI schemas: ['Cart', 'Customer', 'Order', 'Product']
After checking entities.py: 4 entities found: ['Cart', 'Customer', 'Order', 'Product']
Extracted 21 endpoints from OpenAPI paths
Extracted 53 validations from OpenAPI schemas
After checking schemas.py: 63 validations found
Using validation ground truth: 47 validations from ground truth
OpenAPI-based compliance validation complete: 99.6% (entities: 100.0%, endpoints: 100.0%, validations: 98.0%)
ℹ️ Compliance: 99.6% → 99.6%
    ├─ Status: ⚠️
    ├─ Delta: +0.0%
ℹ️ No improvement
    ├─ Status: =
    ├─ Message: Plateau reached
ℹ️ Stopping iteration
    ├─ Reason: No improvement for 2 consecutive iterations

  📊 CP-6.5.5: Metrics collected
  ✅ Phase 6.5 complete
    - Initial compliance: 98.4%
    - Final compliance: 99.6%
    - Improvement: +1.2%
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ✅ Deployment                [██████████████████] 100%  (Files saved: 60/60)
  ✅ Code Repair               [██████████████████] 100%  (Tests fixed: 4/3)
  ⏳ Validation                [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 34s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [██████████████████░░░░░░░]  72%
     8/11 phases completed
  🕐 Estimated Total:  00h 02m 10s | ETA: 18:41:16

================================================================================


✅ Phase 7: Validation (Enhanced with Semantic Validation)
  ✓ Checkpoint: CP-7.1: File structure validated (1/5)
  ✓ Checkpoint: CP-7.2: Syntax validation (2/5)

  📊 Validating dependency execution order...
    Wave 1: 9 requirements (dependency level 1/3)
    Wave 2: 7 requirements (dependency level 2/3)
    Wave 3: 1 requirements (dependency level 3/3)
    Wave 4: 3 requirements (dependency level 4/3)
    Wave 5: 1 requirements (dependency level 5/3)
    Wave 6: 3 requirements (dependency level 6/3)
  ✅ Execution order validated: 6 dependency waves respected
  ✓ Checkpoint: CP-7.2.5: Dependency order validated (3/5)

  🔍 Running semantic validation (ComplianceValidator)...
Validating app at /home/kwar/code/agentic-ai/tests/e2e/generated_apps/ecommerce_api_simple_1763919546 using OpenAPI schema
Converting DATABASE_URL to async driver for validation
Successfully imported FastAPI app
Extracted 4 entities from OpenAPI schemas: ['Cart', 'Customer', 'Order', 'Product']
After checking entities.py: 4 entities found: ['Cart', 'Customer', 'Order', 'Product']
Extracted 21 endpoints from OpenAPI paths
Extracted 53 validations from OpenAPI schemas
After checking schemas.py: 63 validations found
Using validation ground truth: 47 validations from ground truth
OpenAPI-based compliance validation complete: 99.6% (entities: 100.0%, endpoints: 100.0%, validations: 98.0%)
  ✅ Semantic validation PASSED: 99.6% compliance

🌐 Endpoints (17 required, 13 present):
   ✅ GET /products/{id}, PUT /products/{id}, DELETE /products/{id}, GET /customers/{id}, GET /customers/{id}/orders
   ... and 8 more

   📝 Additional endpoints (best practices):
   - GET /health/health
   - GET /health/ready
   - GET /metrics
   - GET /products/
   - POST /products/
   - POST /customers/
   - POST /carts/
   - GET /

📦 Entities (4 required, 4 present):
   ✅ Cart, Customer, Order, Product
  ✓ Checkpoint: CP-7.3: Semantic validation complete (4/5)

  🔍 Running UUID serialization validation...
Declarative base created
  ⚠️ UUID serialization issues detected: 1 issues
    - Exception handlers don't use jsonable_encoder
  🔧 Attempting auto-repair...
✅ Added jsonable_encoder to exception handlers using AST
✅ UUID serialization auto-repairs completed: Added jsonable_encoder to exception handlers
  ✅ UUID serialization auto-repair completed successfully
  ✅ UUID serialization validation PASSED after repair
  ✓ Checkpoint: CP-7.3.5: UUID serialization validated (5/5)
  ✓ Checkpoint: CP-7.4: Business logic validation (6/5)
  ✓ Checkpoint: CP-7.5: Test generation check (7/5)
  ✓ Checkpoint: CP-7.6: Quality metrics (8/5)
✅ Phase Completed: validation (955ms)

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ✅ Validation Results Summary
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    Metric                                  |           Result            |     Status
  --------------------------------------------------------------------------------------------------------------
    Semantic Compliance                     |            99.6%        |       ✅
    Entities                                |              4/4        |       ✅
    Endpoints                               |            21/17        |       ✅
    Files Generated                         |               60        |       ✅
    Test Pass Rate                          |            94.0%        |       ✅
    Contract Validation                     |           PASSED        |       ✅
  --------------------------------------------------------------------------------------------------------------
    Overall Validation Status: ✅ PASSED
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ✅ Deployment                [██████████████████] 100%  (Files saved: 60/60)
  ✅ Code Repair               [██████████████████] 100%  (Tests fixed: 4/3)
  ✅ Validation                [██████████████████] 100%  (Tests: 47/50, Entities: 4/4, Endpoints: 21/17)
  ⏳ Health Verification       [░░░░░░░░░░░░░░░░░░]   0%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 35s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [████████████████████░░░░░]  81%
     9/11 phases completed
  🕐 Estimated Total:  00h 01m 56s | ETA: 18:41:03

================================================================================


🏥 Phase 9: Health Verification
  ✓ File check: src/main.py
  ✓ File check: requirements.txt
  ✓ File check: README.md
  ✓ Checkpoint: CP-9.1: Step 1 (1/5)
  ✓ Checkpoint: CP-9.2: Step 2 (2/5)
  ✓ Checkpoint: CP-9.3: Step 3 (3/5)
  ✓ Checkpoint: CP-9.4: Step 4 (4/5)
  ✓ Checkpoint: CP-9.5: Step 5 (5/5)
✅ Phase Completed: health_verification (1104ms)
  ✅ App is ready to run!

🎉 PIPELINE COMPLETO: App generada en tests/e2e/generated_apps/ecommerce_api_simple_1763919546
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ✅ Deployment                [██████████████████] 100%  (Files saved: 60/60)
  ✅ Code Repair               [██████████████████] 100%  (Tests fixed: 4/3)
  ✅ Validation                [██████████████████] 100%  (Tests: 47/50, Entities: 4/4, Endpoints: 21/17)
  ✅ Health Verification       [██████████████████] 100%
  ⏳ Learning                  [░░░░░░░░░░░░░░░░░░]   0%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 36s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [██████████████████████░░░]  90%
     10/11 phases completed
  🕐 Estimated Total:  00h 01m 46s | ETA: 18:40:53

================================================================================


🧠 Phase 10: Learning
  ✓ Checkpoint: CP-10.1: Execution status assessed (1/5)
Stored candidate 331814d6-d0b2-4ee6-8ad3-afc6e6f3b1e2
  ✓ Checkpoint: CP-10.2: Pattern registered (2/5)
  ✓ Checkpoint: CP-10.3: Checking promotion candidates (3/5)
Checking for patterns ready for promotion (mock mode)
  ✓ Checkpoint: CP-10.4: Promotion check complete (4/5)
    - Total candidates: 0
    - Promoted: 0
    - Failed: 0
  ✓ Checkpoint: CP-10.5: Learning phase complete (5/5)
✅ Phase Completed: learning (109ms)
  ✅ Learning phase complete
================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ✅ Deployment                [██████████████████] 100%  (Files saved: 60/60)
  ✅ Code Repair               [██████████████████] 100%  (Tests fixed: 4/3)
  ✅ Validation                [██████████████████] 100%  (Tests: 47/50, Entities: 4/4, Endpoints: 21/17)
  ✅ Health Verification       [██████████████████] 100%
  ✅ Learning                  [██████████████████] 100%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 36s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [█████████████████████████] 100%
     11/11 phases completed
  🕐 Estimated Total:  00h 01m 36s | ETA: 18:40:43

================================================================================


📊 Metrics saved to: tests/e2e/metrics/real_e2e_ecommerce_api_simple_1763919546.json


================================================================================
                    📊 E2E PIPELINE PROGRESS
================================================================================

  ✅ Spec Ingestion            [██████████████████] 100%  (Requirements: 24/24, Entities: 4/4)
  ✅ Requirements Analysis     [██████████████████] 100%  (crud: 12/12, authentication: 4/4, payment: 4/4, workflow: 2/2, search: 2/2)
  ✅ Multi-Pass Planning       [██████████████████] 100%  (Nodes: 24/24, Dependencies: 15/15)
  ✅ Atomization               [██████████████████] 100%  (Units: 21/24)
  ✅ DAG Construction          [██████████████████] 100%  (Nodes: 24/24, Edges: 15/15)
  ✅ Code Generation           [██████████████████] 100%  (Files: 60/60)
  ✅ Deployment                [██████████████████] 100%  (Files saved: 60/60)
  ✅ Code Repair               [██████████████████] 100%  (Tests fixed: 4/3)
  ✅ Validation                [██████████████████] 100%  (Tests: 47/50, Entities: 4/4, Endpoints: 21/17)
  ✅ Health Verification       [██████████████████] 100%
  ✅ Learning                  [██████████████████] 100%

================================================================================
📈 LIVE STATISTICS
--------------------------------------------------------------------------------
  ⏱️  Elapsed:  00h 01m 36s | 💾 Memory: 2879.5 MB (  9.0%) | 🔥 CPU:   0.0%
  🔄 Neo4j Queries:    145 | 🔍 Qdrant Queries:     45 | 🚀 Tokens Used:   750000

  📊 Overall Progress: [█████████████████████████] 100%
     11/11 phases completed
  🕐 Estimated Total:  00h 01m 36s | ETA: 18:40:43

================================================================================


==========================================================================================
                              📊 REPORTE COMPLETO E2E
==========================================================================================

🎯 EXECUTION SUMMARY
------------------------------------------------------------------------------------------
  Spec:                tests/e2e/test_specs/ecommerce_api_simple.md
  Output:              tests/e2e/generated_apps/ecommerce_api_simple_1763919546
  Status:              success
  Duration:            1.6 minutes (96846ms)
  Overall Progress:    104.8%
  Execution Success:   100.0%
  Overall Accuracy:    100.0%

🧪 TESTING & QUALITY
------------------------------------------------------------------------------------------
  Test Pass Rate:      94.0%
  Test Coverage:       0.0%
  Code Quality:        0.0%
  Contract Violations: 0
  Acceptance Criteria: 0/0

📚 PATTERN LEARNING & REUSE
------------------------------------------------------------------------------------------
  Pattern Reuse Rate:  0.0%
  Patterns Matched:    0
  Patterns Stored:     1
  Patterns Promoted:   0
  Patterns Reused:     0
  New Patterns:        0
  Candidates Created:  1
  Learning Time:       0.0ms

🔧 CODE REPAIR & RECOVERY
------------------------------------------------------------------------------------------
  Repair Applied:      True
  Repair Iterations:   3
  Repair Improvement:  1.2%
  Tests Fixed:         4
  Regressions:         0
  Repair Time:         2342.2ms

⚠️  ERROR TRACKING & RECOVERY
------------------------------------------------------------------------------------------
  Total Errors:        0
  Recovered Errors:    0
  Critical Errors:     0
  Recovery Rate:       0.0%

💾 RESOURCE USAGE
------------------------------------------------------------------------------------------
  Peak Memory:         100.5 MB
  Avg Memory:          37.1 MB
  Peak CPU:            0.0%
  Avg CPU:             0.0%

🗄️  DATABASE PERFORMANCE
------------------------------------------------------------------------------------------
  Neo4j Queries:       0
  Neo4j Avg Time:      0.0ms
  Qdrant Queries:      0
  Qdrant Avg Time:     0.0ms

⏱️  PHASE EXECUTION TIMES
------------------------------------------------------------------------------------------
  ✅ spec_ingestion             18505ms  (4/4 checkpoints)
  ✅ requirements_analysis        951ms  (5/5 checkpoints)
  ✅ multi_pass_planning          103ms  (5/5 checkpoints)
  ✅ atomization                 1303ms  (5/5 checkpoints)
  ✅ dag_construction            1604ms  (5/5 checkpoints)
  ✅ wave_execution             17926ms  (5/5 checkpoints)
  ✅ validation                   955ms  (8/5 checkpoints)
  ✅ deployment                   107ms  (5/5 checkpoints)
  ✅ health_verification         1104ms  (5/5 checkpoints)
  ✅ learning                     109ms  (5/5 checkpoints)

📋 SEMANTIC COMPLIANCE
------------------------------------------------------------------------------------------
  Overall Compliance:  99.6%
    ├─ Entities:       100.0% (4/4)
    ├─ Endpoints:      100.0% (21/17)
    └─ Validations:    98.0% (50/51)
       + Extra:        13 additional validations found (robustness)

  🎯 Spec-to-App Precision: 99.6%
     → Generated app fully implements spec requirements and executes successfully

📊 PRECISION & ACCURACY METRICS
------------------------------------------------------------------------------------------
  🎯 Overall Pipeline Performance:
     Accuracy:         100.0%
     Precision:        82.0%

  📊 Pattern Matching Performance:
     Precision:        80.0%
     Recall:           47.1%
     F1-Score:         59.3%

  🏷️  Classification Accuracy:
     Overall:          33.3%

🚀 HOW TO RUN THE GENERATED APP
------------------------------------------------------------------------------------------

  1. Navigate: cd tests/e2e/generated_apps/ecommerce_api_simple_1763919546
  2. Start:    docker-compose -f docker/docker-compose.yml up -d --build
  3. Health:   docker-compose -f docker/docker-compose.yml ps

  📍 Endpoints:
     - API:        http://localhost:8002
     - Docs:       http://localhost:8002/docs
     - Health:     http://localhost:8002/health/health
     - Metrics:    http://localhost:8002/metrics/metrics
     - Grafana:    http://localhost:3002 (devmatrix/admin)
     - Prometheus: http://localhost:9091
     - PostgreSQL: localhost:5433 (devmatrix/admin)

✅ CONTRACT VALIDATION
------------------------------------------------------------------------------------------
  ✅ All contracts validated successfully!

==========================================================================================