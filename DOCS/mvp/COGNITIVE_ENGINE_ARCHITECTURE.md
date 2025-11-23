# Cognitive Engine Architecture (Cognitive Compiler)

The **Cognitive Engine** is the intelligence core of DevMatrix. It operates as a **Cognitive Compiler**, transforming unstructured intent into deterministic, validated software through a pipeline of Analysis, IR Construction, Generation, and Learning.

## 1. System Overview

The engine operates as a pipeline of specialized components, each responsible for a specific cognitive task.

```mermaid
graph TD
    subgraph "Phase 1: Analysis & IR (Compiler Frontend)"
        User[User Request] -->|Raw Text| Parser[SpecParser]
        Parser -->|SpecRequirements| Builder[IRBuilder]
        Builder -->|ApplicationIR| IR_DB[(Neo4j: IR Graph)]
    end
    
    subgraph "Phase 2: Learning & Context (Optimizer)"
        IR_DB -->|Context| RAG[UnifiedRAGRetriever]
        ErrorDB[(Neo4j: Error Graph)] -->|Error Patterns| RAG
        VectorDB[(Qdrant: Embeddings)] -->|Code Examples| RAG
    end
    
    subgraph "Phase 3: Generation (Compiler Backend)"
        RAG -->|Augmented Context| Prompt[PromptBuilder]
        Prompt -->|Mega-Prompt| LLM[LLM (Claude/GPT-4)]
        LLM -->|Source Code| Gen[BackendGenerator]
    end
    
    subgraph "Phase 4: Validation & Learning (Runtime)"
        Gen -->|Candidate Code| DualVal[DualValidator]
        DualVal -->|Score| Feedback[PatternFeedbackIntegration]
        Feedback -- Score >= 0.8 --> Promote[PatternBank]
        Feedback -- Score < 0.8 --> ErrorStore[ErrorPatternStore]
        ErrorStore --> ErrorDB
    end
```

## 2. Component Deep Dive

### 2.1 SpecParser (`src/parsing/spec_parser.py`)
**Responsibility**: Natural Language Understanding (NLU).
-   **Input**: Markdown files, Chat messages.
-   **Process**:
    1.  **Regex Extraction**: Identifies entities, endpoints, and functional requirements (F-tags).
    2.  **Heuristic Classification**: Determines data types and relationships.
-   **Output**: `SpecRequirements` object.

### 2.2 IRBuilder (`src/cognitive/ir/ir_builder.py`)
**Responsibility**: Deterministic Model Construction.
-   **Input**: `SpecRequirements`.
-   **Process**:
    1.  **Domain Mapping**: Converts `EntitySpec` to `DomainModelIR`.
    2.  **API Mapping**: Converts `EndpointSpec` to `APIModelIR`.
    3.  **Behavior Mapping**: Converts logic to `BehaviorModelIR` (Flows, Invariants).
    4.  **Validation Mapping**: Converts constraints to `ValidationModelIR` (Rules).
-   **Output**: `ApplicationIR` (Pydantic Model).
    -   Acts as the **Immutable Contract** for the generation phase.

### 2.3 UnifiedRAGRetriever (`src/rag/unified_retriever.py`)
**Responsibility**: Context Retrieval & Optimization.
-   **Strategy**: Hybrid Search.
    -   **Semantic Search (Qdrant)**: Uses `GraphCodeBERT` embeddings.
    -   **Graph Traversal (Neo4j)**: Finds historical error patterns.
-   **Task Ontology**:
    -   `CRUD`: Standard operations.
    -   `WORKFLOW`: Complex multi-step logic.
    -   `VALIDATION`: Data integrity rules.
    -   `ORCHESTRATION`: Cross-service coordination.

### 2.4 CodeGenerationService (`src/services/code_generation_service.py`)
**Responsibility**: Orchestration & Synthesis.
-   **PromptBuilder**: Formalizes prompt construction.
    ```python
    class PromptBuilder:
        def with_system_context(self, role)...
        def with_ir_summary(self, ir)...
        def with_rag_results(self, context)...
        def with_task_instruction(self, desc)...
    ```
-   **BackendGenerator**: Abstract interface for multi-stack support.
    ```python
    class BackendGenerator(ABC):
        def generate_models(self, ir): ...
        def generate_routes(self, ir): ...
        def generate_services(self, ir): ...
    ```

### 2.5 DualValidator (`src/cognitive/patterns/pattern_feedback_integration.py`)
**Responsibility**: Quality Assurance.
-   **Mechanism**: Consensus Voting (Claude 3 Sonnet + GPT-4 Turbo).
-   **Thresholds**: Approval (Both >= 0.8), Agreement (Delta <= 0.1).

## 3. Data Models & Schema

### 3.1 Neo4j Graph Schema
Used for structural knowledge, error tracking, and IR persistence.

**Nodes**:
-   `(:Application {app_id, name})`
-   `(:DomainEntity {name})`
-   `(:APIEndpoint {path, method})`
-   `(:BehaviorFlow {name, type})`
-   `(:ValidationRule {entity, attribute, type})`
-   `(:Pattern {id, code, score})`
-   `(:CodeGenerationError {error_type, message})`

**Relationships**:
-   `(:Application)-[:HAS_MODEL]->(:DomainEntity)`
-   `(:Application)-[:DEFINES_BEHAVIOR]->(:BehaviorFlow)`
-   `(:DomainEntity)-[:HAS_RULE]->(:ValidationRule)`
-   `(:APIEndpoint)-[:USES_PATTERN]->(:Pattern)`
-   `(:Pattern)-[:HAS_ERROR]->(:CodeGenerationError)`

### 3.2 Qdrant Vector Schema
Used for semantic similarity search.

**Collection**: `devmatrix_patterns`
-   **Vector**: 768-dim (GraphCodeBERT).
-   **Payload**: `code`, `language`, `tags`, `quality_score`.

## 4. Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ENABLE_AUTO_PROMOTION` | Automatically promote high-quality code | `True` |
| `ENABLE_DUAL_VALIDATION` | Require both Claude and GPT-4 | `True` |
| `RAG_STRATEGY` | `semantic`, `graph`, `hybrid` | `hybrid` |
| `IR_VERSIONING` | Enable IR version history in Neo4j | `True` |
| `ERROR_CLASSIFIER_MODEL` | Model used for error grouping | `gpt-4-turbo` |

## 5. Extension Points

-   **Multi-Stack**: Implement `BackendGenerator` for Django, Node.js, Go.
-   **New Validators**: Add static analysis tools to `DualValidator`.
-   **Custom RAG**: Implement new retrieval strategies in `UnifiedRAGRetriever`.
