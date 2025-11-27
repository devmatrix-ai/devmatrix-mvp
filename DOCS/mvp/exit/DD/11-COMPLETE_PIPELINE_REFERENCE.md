# Complete Pipeline Reference

**Version**: 3.0
**Date**: November 2025
**Status**: Comprehensive Technical Reference
**Source**: Extracted from actual codebase (~378 Python files)

---

## Executive Summary

This document provides **exhaustive technical documentation** of the DevMatrix Cognitive Code Generation Engine, covering every component from natural language specification ingestion to running, validated application deployment. All information is extracted from the actual source code.

**Pipeline Overview**:
```
Natural Language Spec → SpecParser → ApplicationIR → Multi-Pass Planner →
DAG Construction → CPIE Inference → Code Generation → Validation →
Code Repair → Test Generation → Running Application
```

---

## Table of Contents

1. [Phase 1: Specification Ingestion](#phase-1-specification-ingestion)
2. [Phase 2: ApplicationIR Extraction](#phase-2-applicationir-extraction)
3. [Phase 3: Requirements Classification](#phase-3-requirements-classification)
4. [Phase 4: Cognitive Planning](#phase-4-cognitive-planning)
5. [Phase 5: Pattern Inference (CPIE)](#phase-5-pattern-inference-cpie)
6. [Phase 6: Code Generation](#phase-6-code-generation)
7. [Phase 7: Validation & Compliance](#phase-7-validation--compliance)
8. [Phase 8: Code Repair](#phase-8-code-repair)
9. [Phase 9: Test Generation](#phase-9-test-generation)
10. [Phase 10: Application Deployment](#phase-10-application-deployment)
11. [Supporting Infrastructure](#supporting-infrastructure)

---

## Phase 1: Specification Ingestion

### 1.1 SpecParser (`src/parsing/spec_parser.py`)

**Purpose**: Parse natural language specifications and extract structured requirements.

```python
class SpecParser:
    """
    Parses markdown specifications into structured SpecRequirements.

    Extracts:
    - Functional requirements (F1, F2, etc.)
    - Non-functional requirements (NF1, NF2, etc.)
    - Entities with fields and constraints
    - API endpoints with parameters
    - Validation rules
    """

    def parse(self, spec_path: Path) -> SpecRequirements:
        """Parse spec file and return structured requirements."""
```

**Data Structures Output**:

```python
@dataclass
class SpecRequirements:
    requirements: List[Requirement]  # F1, F2, NF1, etc.
    entities: List[Entity]           # Product, Customer, Order
    endpoints: List[Endpoint]        # GET /products, POST /orders
    validation_rules: List[ValidationRule]
    metadata: Dict[str, Any]         # spec_name, domain, complexity
```

```python
@dataclass
class Requirement:
    id: str              # "F1", "NF2"
    type: str            # "functional", "non_functional"
    priority: str        # "MUST", "SHOULD", "COULD"
    description: str     # Natural language description
    domain: str          # "CRUD", "Payment", "Workflow"
    dependencies: List[str]  # ["F1", "F2"]
```

```python
@dataclass
class Entity:
    name: str            # "Product"
    fields: List[Field]  # price, name, stock
    relationships: List[Relationship]
    validations: List[str]

@dataclass
class Field:
    name: str            # "price"
    type: str            # "Decimal"
    required: bool       # True
    default: Any         # None
    constraints: List[str]  # ["gt=0", "unique"]
```

### 1.2 Hierarchical Models (`src/parsing/hierarchical_models.py`)

**Purpose**: Provide structured data models for parsed specifications.

```python
@dataclass
class GlobalContext:
    """High-level context from spec header."""
    domain: str           # "E-commerce API"
    spec_name: str        # "ecommerce-api-spec"
    complexity: float     # 0.0-1.0
    entities: List[EntitySummary]
    endpoints: List[EndpointSummary]

@dataclass
class EntitySummary:
    name: str
    description: str
    field_count: int
    relationship_count: int

@dataclass
class EntityDetail:
    """Detailed entity with all fields and constraints."""
    name: str
    plural: str
    fields: List[Field]
    relationships: List[Relationship]
    validations: List[ValidationRule]
```

---

## Phase 2: ApplicationIR Extraction

### 2.1 SpecToApplicationIR (`src/specs/spec_to_application_ir.py`)

**Purpose**: Convert parsed specifications into the central ApplicationIR using LLM extraction.

```python
class SpecToApplicationIR:
    """
    LLM-based converter from spec markdown to ApplicationIR.

    Features:
    - Caches IR as JSON for deterministic subsequent runs
    - Uses Claude Sonnet for extraction
    - Hash-based cache invalidation
    - Produces complete ApplicationIR with all 5 sub-models
    """

    async def get_application_ir(
        self,
        spec_content: str,
        spec_name: str,
        force_refresh: bool = False
    ) -> ApplicationIR:
        """
        Extract or retrieve cached ApplicationIR from spec.

        Returns:
            ApplicationIR with:
            - domain_model: Entities and relationships
            - api_model: Endpoints and schemas
            - behavior_model: Workflows and state machines
            - validation_model: Validation rules and constraints
            - infrastructure_model: Database and deployment config
        """
```

### 2.2 ApplicationIR Root (`src/cognitive/ir/application_ir.py`)

**Purpose**: Central aggregate combining all sub-IRs as single source of truth.

```python
@dataclass
class ApplicationIR:
    """
    Root aggregate for complete application specification.

    This is the SINGLE SOURCE OF TRUTH for code generation.
    All downstream phases reference ApplicationIR, not raw specs.
    """

    # Identity
    app_id: UUID
    name: str
    description: str

    # Sub-Models (5 total)
    domain_model: DomainModelIR        # Entities, attributes, relationships
    api_model: APIModelIR              # Endpoints, parameters, schemas
    behavior_model: BehaviorModelIR    # Workflows, state machines, invariants
    validation_model: ValidationModelIR  # Validation rules, enforcement strategies
    infrastructure_model: InfrastructureModelIR  # Database, Docker, observability

    # Metadata
    created_at: datetime
    updated_at: datetime
    version: str
    phase_status: Dict[str, str]  # {"parsing": "complete", "generation": "pending"}

    # Convenience Methods
    def get_entities(self) -> List[Entity]:
        """Get all entities from DomainModelIR."""
        return self.domain_model.entities if self.domain_model else []

    def get_endpoints(self) -> List[Endpoint]:
        """Get all endpoints from APIModelIR."""
        return self.api_model.endpoints if self.api_model else []

    def get_flows(self) -> List[Flow]:
        """Get all flows from BehaviorModelIR."""
        return self.behavior_model.flows if self.behavior_model else []

    def get_validation_rules(self) -> List[ValidationRule]:
        """Get all validation rules from ValidationModelIR."""
        return self.validation_model.rules if self.validation_model else []

    def get_dag_nodes(self) -> List[Dict]:
        """Get nodes for DAG construction from all sub-IRs."""
```

### 2.3 DomainModelIR (`src/cognitive/ir/domain_model.py`)

**Purpose**: Define entities, their attributes, and relationships.

```python
class DataType(Enum):
    """Supported data types for entity attributes."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    UUID = "uuid"
    JSON = "json"
    ENUM = "enum"
    DECIMAL = "decimal"

class RelationshipType(Enum):
    """Types of entity relationships."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

@dataclass
class Attribute:
    """Entity attribute definition."""
    name: str              # "price"
    data_type: DataType    # DataType.DECIMAL
    is_primary_key: bool   # False
    is_nullable: bool      # False
    is_unique: bool        # False
    default_value: Any     # None
    constraints: Dict[str, Any]  # {"min": 0, "max": 10000}
    description: str       # "Product price in USD"

@dataclass
class Relationship:
    """Entity relationship definition."""
    source_entity: str     # "Order"
    target_entity: str     # "Customer"
    type: RelationshipType # ONE_TO_MANY
    field_name: str        # "customer_id"
    back_populates: str    # "orders"
    on_delete: str         # "CASCADE"

@dataclass
class Entity:
    """Complete entity definition."""
    name: str              # "Product"
    attributes: List[Attribute]
    relationships: List[Relationship]
    description: str
    is_aggregate_root: bool  # True for main entities

@dataclass
class DomainModelIR:
    """Complete domain model with all entities."""
    entities: List[Entity]

    def get_entity(self, name: str) -> Optional[Entity]:
        """Get entity by name (case-insensitive)."""
```

### 2.4 APIModelIR (`src/cognitive/ir/api_model.py`)

**Purpose**: Define REST API structure with endpoints, parameters, and schemas.

```python
class HttpMethod(Enum):
    """HTTP methods for API endpoints."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class ParameterLocation(Enum):
    """Parameter locations in HTTP requests."""
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"

class InferenceSource(Enum):
    """Source of inferred API elements."""
    SPEC = "spec"                       # Explicitly in specification
    CRUD_BEST_PRACTICE = "crud_best_practice"  # Inferred from CRUD patterns
    INFRA_BEST_PRACTICE = "infra_best_practice"  # Health, metrics endpoints
    PATTERN_BANK = "pattern_bank"       # From PatternBank

@dataclass
class APIParameter:
    """API endpoint parameter."""
    name: str              # "product_id"
    location: ParameterLocation  # PATH
    data_type: str         # "uuid"
    required: bool         # True
    description: str       # "Product identifier"
    default: Any           # None

@dataclass
class APISchema:
    """Request/response schema definition."""
    name: str              # "ProductCreate"
    fields: List[APISchemaField]

@dataclass
class APISchemaField:
    """Schema field definition."""
    name: str              # "price"
    type: str              # "Decimal"
    required: bool         # True
    description: str       # "Product price"

@dataclass
class Endpoint:
    """Complete API endpoint definition."""
    path: str              # "/products/{product_id}"
    method: HttpMethod     # GET
    operation_id: str      # "get_product"
    summary: str           # "Get product by ID"
    description: str       # Detailed description
    parameters: List[APIParameter]
    request_schema: Optional[APISchema]
    response_schema: Optional[APISchema]
    auth_required: bool    # True
    tags: List[str]        # ["Products"]
    inference_source: InferenceSource  # SPEC or CRUD_BEST_PRACTICE

@dataclass
class APIModelIR:
    """Complete API model with all endpoints."""
    endpoints: List[Endpoint]
    global_tags: List[str]
    base_path: str         # "/api/v1"

    def get_endpoints_by_tag(self, tag: str) -> List[Endpoint]:
        """Get all endpoints with specific tag."""
```

### 2.5 ValidationModelIR (`src/cognitive/ir/validation_model.py`)

**Purpose**: Define validation rules with enforcement strategies. **Critical for 100% compliance**.

```python
class ValidationType(Enum):
    """Types of validation rules."""
    FORMAT = "format"             # Email, phone, regex patterns
    RANGE = "range"               # min/max values
    PRESENCE = "presence"         # Required fields
    UNIQUENESS = "uniqueness"     # Unique constraints
    RELATIONSHIP = "relationship" # Foreign key, referential integrity
    STOCK_CONSTRAINT = "stock_constraint"  # Inventory rules
    STATUS_TRANSITION = "status_transition"  # State machine rules
    WORKFLOW_CONSTRAINT = "workflow_constraint"  # Business workflow rules
    CUSTOM = "custom"             # Custom validation logic

class EnforcementType(Enum):
    """How validation is enforced in generated code."""
    DESCRIPTION = "description"     # Documentation only (NOT enforced)
    VALIDATOR = "validator"         # Pydantic validator
    COMPUTED_FIELD = "computed_field"  # @computed_field decorator
    IMMUTABLE = "immutable"         # Field(exclude=True), onupdate=None
    STATE_MACHINE = "state_machine" # FSM validators
    BUSINESS_LOGIC = "business_logic"  # Service layer enforcement

@dataclass
class EnforcementStrategy:
    """Detailed enforcement implementation."""
    type: EnforcementType         # COMPUTED_FIELD
    implementation: str           # "pydantic_computed_field"
    applied_at: List[str]         # ["schema", "entity"]
    template_name: Optional[str]  # "computed_field_template"
    parameters: Dict[str, Any]    # {"formula": "sum(items)"}
    code_snippet: Optional[str]   # Actual code to generate
    description: str              # Human-readable description

@dataclass
class ValidationRule:
    """Complete validation rule definition."""
    entity: str            # "Order"
    attribute: str         # "total_amount"
    type: ValidationType   # ValidationType.RANGE
    condition: str         # "total_amount > 0"
    error_message: str     # "Total must be positive"
    severity: str          # "error", "warning"
    enforcement_type: EnforcementType  # COMPUTED_FIELD
    enforcement: EnforcementStrategy   # Full strategy
    enforcement_code: Optional[str]    # Generated code
    applied_at: List[str]  # ["schema", "entity", "service"]

@dataclass
class ValidationModelIR:
    """Complete validation model with all rules."""
    rules: List[ValidationRule]
    test_cases: List[Dict]  # Generated test cases

    def get_rules_by_entity(self, entity: str) -> List[ValidationRule]:
        """Get all validation rules for an entity."""

    def get_rules_by_type(self, vtype: ValidationType) -> List[ValidationRule]:
        """Get all rules of specific type."""
```

### 2.6 BehaviorModelIR (`src/cognitive/ir/behavior_model.py`)

**Purpose**: Define system dynamics, workflows, and state machines.

```python
class FlowType(Enum):
    """Types of behavioral flows."""
    WORKFLOW = "workflow"             # Multi-step business process
    STATE_TRANSITION = "state_transition"  # FSM transitions
    POLICY = "policy"                 # Business rules
    EVENT_HANDLER = "event_handler"   # Event-driven logic

@dataclass
class Step:
    """Step in a workflow or state machine."""
    order: int             # 1, 2, 3...
    description: str       # "Validate cart items"
    action: str            # "validate_stock"
    target_entity: str     # "Product"
    condition: Optional[str]  # "cart.items.length > 0"

@dataclass
class Flow:
    """Complete workflow or state machine definition."""
    name: str              # "checkout_flow"
    type: FlowType         # WORKFLOW
    trigger: str           # "POST /checkout"
    steps: List[Step]
    description: str
    preconditions: List[str]   # ["cart_not_empty"]
    postconditions: List[str]  # ["order_created", "stock_decremented"]

@dataclass
class Invariant:
    """Business invariant that must always hold."""
    entity: str            # "Product"
    description: str       # "Stock must never be negative"
    expression: str        # "stock >= 0"
    enforcement_level: str # "database", "application", "both"

@dataclass
class BehaviorModelIR:
    """Complete behavior model with flows and invariants."""
    flows: List[Flow]
    invariants: List[Invariant]

    def get_flows_by_type(self, flow_type: FlowType) -> List[Flow]:
        """Get all flows of specific type."""

    def get_state_transitions(self, entity: str) -> List[Flow]:
        """Get state transition flows for entity."""
```

### 2.7 InfrastructureModelIR (`src/cognitive/ir/infrastructure_model.py`)

**Purpose**: Define database, deployment, and observability configuration.

```python
class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    NEO4J = "neo4j"
    QDRANT = "qdrant"

@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    type: DatabaseType     # POSTGRESQL
    host: str              # "localhost"
    port: int              # 5432
    name: str              # "api_db"
    user: str              # "api_user"
    password_env_var: str  # "DB_PASSWORD"

@dataclass
class ContainerService:
    """Docker container service definition."""
    name: str              # "api"
    image: str             # "python:3.11-slim"
    ports: List[str]       # ["8000:8000"]
    environment: Dict[str, str]
    volumes: List[str]
    depends_on: List[str]  # ["db", "redis"]

@dataclass
class ObservabilityConfig:
    """Observability and monitoring configuration."""
    logging_enabled: bool
    metrics_enabled: bool
    tracing_enabled: bool
    health_check_path: str  # "/health"
    metrics_path: str       # "/metrics"

@dataclass
class InfrastructureModelIR:
    """Complete infrastructure configuration."""
    database: DatabaseConfig
    vector_db: Optional[DatabaseConfig]  # Qdrant for patterns
    graph_db: Optional[DatabaseConfig]   # Neo4j for DAGs
    containers: List[ContainerService]
    observability: ObservabilityConfig
```

---

## Phase 3: Requirements Classification

### 3.1 RequirementsClassifier (`src/classification/requirements_classifier.py`)

**Purpose**: Semantic classification of requirements for optimal processing.

```python
class RequirementsClassifier:
    """
    Hybrid semantic classification using keyword matching + embeddings.

    Classifies requirements by:
    - Domain: CRUD, Authentication, Payment, Workflow, Search, Custom
    - Priority: MUST, SHOULD, COULD, WON'T
    - Complexity: 0.0-1.0 score
    - Risk Level: low, medium, high
    - Dependencies: Requirement relationships

    Performance:
    - BEFORE: Keyword matching with 42% accuracy, 6% functional recall
    - AFTER: Semantic classification with ≥90% accuracy, ≥90% functional recall
    """

    def classify(self, requirement: Requirement) -> ClassificationResult:
        """
        Classify a single requirement.

        Returns:
            ClassificationResult with domain, priority, complexity, risk, dependencies
        """

    def classify_batch(self, requirements: List[Requirement]) -> List[ClassificationResult]:
        """Classify multiple requirements efficiently."""
```

---

## Phase 4: Cognitive Planning

### 4.1 Multi-Pass Planner (`src/cognitive/planning/multi_pass_planner.py`)

**Purpose**: Six-pass planning decomposition for systematic code generation.

```python
class MultiPassPlanner:
    """
    Six-pass planning decomposition.

    Passes:
    1. Requirements Analysis: Extract entities, attributes, relationships, use cases
    2. Architecture Design: Define modules, patterns, cross-cutting concerns
    3. Contract Definition: APIs, schemas, validation rules
    4. Integration Points: Dependencies, cycle detection, dependency matrix
    5. Atomic Breakdown: Decompose into 50-120 atoms with signatures ≤10 LOC
    6. Validation & Optimization: Tarjan's algorithm, cycle detection, parallelization

    Output: 50-120 atomic tasks with semantic signatures
    """

    def __init__(self, application_ir: ApplicationIR):
        self.ir = application_ir

    def plan(self) -> PlanResult:
        """
        Execute all 6 planning passes.

        Returns:
            PlanResult with:
            - atomic_tasks: List of AtomicTask (50-120 tasks)
            - dependency_graph: DAG of task dependencies
            - execution_waves: Ordered waves for parallel execution
            - validation_report: Pass validation results
        """

    def _pass_1_requirements_analysis(self) -> RequirementsAnalysis:
        """Extract entities, attributes, relationships from IR."""

    def _pass_2_architecture_design(self) -> ArchitectureDesign:
        """Define modules, patterns, cross-cutting concerns."""

    def _pass_3_contract_definition(self) -> ContractDefinition:
        """Define APIs, schemas, validation rules."""

    def _pass_4_integration_points(self) -> IntegrationAnalysis:
        """Identify dependencies, detect cycles, build dependency matrix."""

    def _pass_5_atomic_breakdown(self) -> List[AtomicTask]:
        """Decompose into atomic tasks (≤10 LOC each)."""

    def _pass_6_validation_optimization(self) -> ValidationResult:
        """
        Validate and optimize the plan.

        Uses Tarjan's algorithm for cycle detection.
        Assigns parallelization levels.
        Validates CRUD, workflow sequencing.
        """

@dataclass
class AtomicTask:
    """Single atomic unit of code generation."""
    task_id: str
    purpose: str           # "Create product entity"
    signature: SemanticTaskSignature
    dependencies: List[str]  # Task IDs
    estimated_loc: int     # ≤10
    domain: str            # "crud", "payment", "workflow"
    parallelization_level: int  # 0, 1, 2... (wave number)
```

### 4.2 DAG Builder (`src/cognitive/planning/dag_builder.py`)

**Purpose**: Construct directed acyclic graphs for task dependencies using Neo4j.

```python
class DAGBuilder:
    """
    Builds execution DAGs with Neo4j backend.

    Features:
    - Neo4j graph storage
    - Cypher-based cycle detection
    - Topological sorting by dependency levels
    - Parallelization level assignment
    - <1s query performance target
    """

    def __init__(self):
        self.neo4j_client = Neo4jClient()

    def build_dag(self, atomic_tasks: List[AtomicTask]) -> DAG:
        """
        Build DAG from atomic tasks.

        Returns:
            DAG with nodes, edges, and execution waves
        """

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles using Tarjan's algorithm via Cypher."""

    def get_execution_waves(self) -> List[List[AtomicTask]]:
        """
        Get tasks organized into execution waves.

        Wave N depends only on waves 0 to N-1.
        Tasks within same wave can run in parallel.
        """

    def get_topological_order(self) -> List[AtomicTask]:
        """Get tasks in dependency-respecting order."""
```

### 4.3 Semantic Signatures (`src/cognitive/signatures/semantic_signature.py`)

**Purpose**: Task signature representation for pattern matching.

```python
@dataclass
class SemanticTaskSignature:
    """
    Semantic signature for pattern matching.

    Used by CPIE to find similar patterns in PatternBank.
    """
    purpose: str           # "Validate email format"
    intent: str            # "validate", "create", "update"
    inputs: Dict[str, str]   # {"email": "str"}
    outputs: Dict[str, str]  # {"is_valid": "bool"}
    domain: str            # "authentication", "crud", "payment"
    constraints: List[str]   # ["max_length:255"]
    security_level: str    # "standard", "high", "critical"

def compute_semantic_hash(signature: SemanticTaskSignature) -> str:
    """Compute unique hash for signature (used for caching)."""
```

---

## Phase 5: Pattern Inference (CPIE)

### 5.1 PatternBank (`src/cognitive/patterns/pattern_bank.py`)

**Purpose**: Auto-evolutionary knowledge base with Qdrant vector storage.

```python
class PatternBank:
    """
    Pattern Bank with Qdrant vector database integration.

    Features:
    - Pattern storage with ≥95% success rate threshold
    - Semantic similarity search (Sentence Transformers)
    - Hybrid search (vector + metadata filtering)
    - Dual embeddings (GraphCodeBERT 768d + Sentence-BERT 384d)
    - DAG-based ranking (execution success history)
    - Usage tracking and metrics
    - Auto-evolution through feedback loops

    Collections:
    - semantic_patterns: 384-dim Sentence-BERT embeddings
    - devmatrix_patterns: 768-dim GraphCodeBERT embeddings
    """

    def __init__(
        self,
        collection_name: str = "semantic_patterns",
        enable_dag_ranking: bool = True,
        enable_dual_embeddings: bool = True
    ):
        self.client = QdrantClient()
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")

    def store_pattern(
        self,
        signature: SemanticTaskSignature,
        code: str,
        success_rate: float  # Must be ≥0.95
    ) -> str:
        """
        Store successful pattern in pattern bank.

        Only stores patterns with success_rate ≥ 95%.

        Returns:
            pattern_id: UUID for stored pattern
        """

    def search_patterns(
        self,
        signature: SemanticTaskSignature,
        top_k: int = 5,
        similarity_threshold: float = 0.60
    ) -> List[StoredPattern]:
        """
        Search for similar patterns using semantic similarity.

        Returns patterns sorted by similarity (descending).
        """

    def search_with_fallback(
        self,
        signature: SemanticTaskSignature,
        top_k: int = 5,
        min_results: int = 3
    ) -> List[StoredPattern]:
        """
        Search with adaptive thresholds and keyword fallback.

        TG4: Domain-specific adaptive thresholds
        TG5: Keyword-based fallback when embedding search yields < min_results
        """

    def hybrid_search(
        self,
        signature: SemanticTaskSignature,
        domain: Optional[str] = None,
        production_ready: bool = False,
        top_k: int = 5
    ) -> List[StoredPattern]:
        """
        Hybrid search: 70% vector similarity + 30% metadata relevance.
        """

@dataclass
class StoredPattern:
    """Retrieved pattern from pattern bank."""
    pattern_id: str
    signature: SemanticTaskSignature
    code: str
    success_rate: float
    similarity_score: float
    usage_count: int
    created_at: datetime
    domain: str

# Domain-specific adaptive thresholds
DOMAIN_THRESHOLDS = {
    "crud": 0.60,      # Simple CRUD patterns
    "custom": 0.65,    # Custom logic
    "payment": 0.70,   # Complex payment patterns
    "workflow": 0.65,  # Workflow patterns
    "api_development": 0.60,
    "backend": 0.60,
}
```

### 5.2 CPIE - Cognitive Pattern Inference Engine (`src/cognitive/inference/cpie.py`)

**Purpose**: Core inference engine for atomic code generation.

```python
class CPIE:
    """
    Cognitive Pattern Inference Engine.

    Strategy:
    1. Pattern matching from Pattern Bank (≥85% similarity)
    2. First-principles generation when no patterns match
    3. Retry mechanism with context enrichment (max 3 retries)
    4. Constraint enforcement (max 10 LOC, syntax, type hints, no TODOs)
    5. Co-reasoning with Claude (strategy) + DeepSeek (implementation)
    6. Synthesis validation for quality assurance

    Specification Compliance:
    - Pattern matching threshold: ≥85% similarity
    - Max LOC per atom: 10 lines
    - Retry limit: 3 attempts
    - Success target: ≥95% precision
    """

    def __init__(
        self,
        pattern_bank: PatternBank,
        co_reasoning_system: Any,
        max_retries: int = 3,
        similarity_threshold: float = 0.85,
        max_loc: int = 10
    ):
        self.pattern_bank = pattern_bank
        self.co_reasoning_system = co_reasoning_system
        self.max_retries = max_retries
        self.max_loc = max_loc

    def infer(self, signature: SemanticTaskSignature) -> Optional[str]:
        """
        Infer code for atomic task from semantic signature.

        Strategy:
        1. Try pattern matching (≥85% similarity)
        2. If no pattern, use first-principles generation
        3. Validate constraints (max LOC, syntax, types, no TODOs)
        4. Retry with enriched context if validation fails

        Returns:
            Generated code string or None if all attempts fail
        """

def infer_from_pattern(
    signature: SemanticTaskSignature,
    pattern_bank: PatternBank,
    co_reasoning_system: Any
) -> Optional[str]:
    """
    Infer code by adapting similar pattern from Pattern Bank.

    Steps:
    1. Calculate adaptive threshold based on domain
    2. Search Pattern Bank for similar patterns
    3. Generate adaptation strategy using Claude
    4. Generate adapted code using DeepSeek
    """

def infer_from_first_principles(
    signature: SemanticTaskSignature,
    co_reasoning_system: Any
) -> Optional[str]:
    """
    Generate code from first principles (no pattern match).

    Steps:
    1. Generate strategy using Claude
    2. Generate code using DeepSeek
    """

def validate_constraints(code: str, max_loc: int = 10) -> Tuple[bool, List[str]]:
    """
    Validate generated code against quality constraints.

    Constraints:
    1. Maximum lines of code (default: 10)
    2. Valid Python syntax
    3. Full type hints
    4. No TODO comments
    5. Single responsibility
    """

def retry_with_context(
    signature: SemanticTaskSignature,
    previous_failure: Dict[str, str],
    enriched_context: str,
    co_reasoning_system: Any,
    max_retries: int = 3
) -> Optional[str]:
    """
    Retry code generation with enriched context from failures.
    """
```

---

## Phase 6: Code Generation

### 6.1 CodeGenerationService (`src/services/code_generation_service.py`)

**Purpose**: MGE V2 code generation orchestrator.

```python
class CodeGenerationService:
    """
    Service for generating code from ApplicationIR using LLM.

    Features:
    - PatternBank integration for production-ready patterns
    - ApplicationIR Normalizer for template rendering
    - Cognitive Feedback Loop for pattern promotion
    - Production-ready code generators fallback
    - DAG synchronization for execution metrics
    - Behavior code generation (workflows, state machines)

    Flow:
    1. MasterPlan Generator creates tasks
    2. CodeGenerationService generates code (THIS SERVICE)
    3. Atomization Service parses into atoms
    4. Wave Executor runs atoms in parallel
    """

    def __init__(
        self,
        db: Session,
        enable_feedback_loop: bool = True,
        enable_pattern_promotion: bool = True,
        enable_dag_sync: bool = True
    ):
        self.llm_client = EnhancedAnthropicClient()
        self.pattern_bank = PatternBank()
        self.modular_generator = ModularArchitectureGenerator()
        self.behavior_generator = BehaviorCodeGenerator()

    async def generate_from_application_ir(
        self,
        application_ir: ApplicationIR,
        allow_syntax_errors: bool = False,
        repair_context: Optional[str] = None
    ) -> str:
        """
        Generate code directly from ApplicationIR (IR-centric approach).

        Steps:
        1. Validate IR has minimum required data
        2. Persist IR to Neo4j
        3. Retrieve production patterns from PatternBank
        4. Compose patterns into files
        5. Generate behavior code (workflows, state machines)
        6. Add __init__.py files
        7. Return as formatted string

        Returns:
            Complete generated code with file markers:
            "=== FILE: path/to/file.py ===\n<content>\n\n"
        """

    async def _retrieve_production_patterns(
        self,
        app_ir: ApplicationIR
    ) -> Dict[str, List[StoredPattern]]:
        """
        Retrieve production-ready patterns from PatternBank.

        Categories:
        - entities: Entity definitions
        - schemas: Pydantic schemas
        - config: Configuration
        - routes: API endpoints
        - services: Business logic
        """

    async def _compose_patterns(
        self,
        patterns: Dict[str, List[StoredPattern]],
        app_ir: ApplicationIR
    ) -> Dict[str, str]:
        """
        Compose patterns into complete file structure.

        Returns:
            Dict[file_path, file_content]
        """
```

### 6.2 Production Code Generators (`src/services/production_code_generators.py`)

**Purpose**: Hardcoded generators producing 100% correct production code.

```python
def generate_entities(
    entities: List[Dict[str, Any]],
    validation_ground_truth: dict = None
) -> str:
    """
    Generate SQLAlchemy ORM entities dynamically from IR.

    Features:
    - Type mapping from spec types to SQLAlchemy
    - Foreign key detection
    - Constraint handling (unique, nullable)
    - Immutable field support (onupdate=None)
    - Auto-generated __repr__

    Returns:
        Complete entities.py code
    """

def generate_schemas(
    entities: List[Dict[str, Any]],
    validation_ground_truth: Dict[str, Any] = None
) -> str:
    """
    Generate Pydantic schemas for request/response validation.

    Generates:
    - BaseSchema with UUID-friendly JSON encoding
    - {Entity}Create schema (excludes auto-generated fields)
    - {Entity}Update schema (excludes immutable fields)
    - {Entity}Response schema (all fields)

    Returns:
        Complete schemas.py code
    """

def generate_config() -> str:
    """
    Generate Pydantic settings configuration.

    Includes:
    - Database configuration
    - Logging settings
    - Security settings
    - Redis configuration

    Returns:
        Complete config.py code
    """

def generate_service_method(
    entity: Dict[str, Any],
    method_type: str  # "create", "read", "update", "delete", "list"
) -> str:
    """Generate service layer method for entity."""

def generate_initial_migration(entities: List[Dict[str, Any]]) -> str:
    """Generate Alembic migration for entities."""

def validate_generated_files(files: Dict[str, str]) -> Dict[str, bool]:
    """Validate syntax of all generated files."""
```

### 6.3 BehaviorCodeGenerator (`src/services/behavior_code_generator.py`)

**Purpose**: Generate workflows, state machines, and validators from BehaviorModelIR.

```python
class BehaviorCodeGenerator:
    """
    Generates business logic code from BehaviorModelIR.

    Generates:
    - Workflow implementations (checkout, registration)
    - State machine validators (order status transitions)
    - Business rule validators
    - Event handlers
    """

    def generate_business_logic(
        self,
        behavior_model: BehaviorModelIR
    ) -> Dict[str, str]:
        """
        Generate all business logic files.

        Returns:
            Dict[file_path, file_content] with:
            - src/services/workflows/*.py
            - src/services/state_machines/*.py
            - src/services/validators/*.py
            - src/services/events/*.py
        """
```

---

## Phase 7: Validation & Compliance

### 7.1 ComplianceValidator (`src/validation/compliance_validator.py`)

**Purpose**: Semantic validation of generated code against specification.

```python
class ComplianceValidator:
    """
    Validates generated code against specification requirements.

    Calculates compliance by comparing:
    1. Expected entities (from IR) vs Implemented entities (from code)
    2. Expected endpoints (from IR) vs Implemented endpoints (from code)
    3. Expected validations (from IR) vs Implemented validations (from code)

    Overall compliance = weighted average:
    - Entities: 40%
    - Endpoints: 40%
    - Validations: 20%

    Threshold: FAIL if overall < 0.80 (80%)
    """

    def __init__(
        self,
        use_semantic_matching: bool = True,
        application_ir: Optional[ApplicationIR] = None
    ):
        self.analyzer = CodeAnalyzer()
        self.semantic_matcher = SemanticMatcher() if use_semantic_matching else None
        self.application_ir = application_ir

    def validate(
        self,
        spec_requirements: SpecRequirements,
        generated_code: str
    ) -> ComplianceReport:
        """
        Validate generated code against specification.

        Returns:
            ComplianceReport with detailed analysis
        """

    def validate_from_app(
        self,
        spec_requirements: SpecRequirements,
        output_path: Path
    ) -> ComplianceReport:
        """
        Validate using OpenAPI schema from running app.

        Critical fix for 0% compliance bug:
        - Dynamically imports generated FastAPI app
        - Reads OpenAPI schema
        - Finds ALL entities and endpoints across modular architecture
        """

@dataclass
class ComplianceReport:
    """Detailed compliance report."""
    overall_compliance: float  # 0.0-1.0

    # Entities
    entities_implemented: List[str]
    entities_expected: List[str]

    # Endpoints
    endpoints_implemented: List[str]
    endpoints_expected: List[str]

    # Validations
    validations_implemented: List[str]
    validations_expected: List[str]
    validations_found: List[str]  # All found, including extras

    # Missing
    missing_requirements: List[str]

    # Per-category
    compliance_details: Dict[str, float]
    # {"entities": 0.95, "endpoints": 1.0, "validations": 0.80}
```

### 7.2 IR Compliance Checker (`src/services/ir_compliance_checker.py`)

**Purpose**: Strict IR-based compliance checking.

```python
def check_full_ir_compliance(
    application_ir: ApplicationIR,
    output_path: Path,
    mode: ValidationMode = ValidationMode.STRICT
) -> Dict[str, ComplianceReport]:
    """
    Check compliance against all IR models.

    Modes:
    - STRICT: Exact matching required
    - RELAXED: Allows synonyms and partial matches

    Returns reports for:
    - entity_compliance
    - endpoint_compliance
    - validation_compliance
    - behavior_compliance
    """
```

---

## Phase 8: Code Repair

### 8.1 CodeRepairAgent (`src/mge/v2/agents/code_repair_agent.py`)

**Purpose**: AST-based targeted repairs instead of full regeneration.

```python
class CodeRepairAgent:
    """
    AST-based code repair agent for targeted fixes.

    Capabilities:
    - Add missing entities to src/models/entities.py
    - Add missing endpoints to src/api/routes/*.py
    - Add missing validations to schemas
    - Preserve existing code (only add what's missing)
    - Automatic rollback if patch fails

    Modes:
    - IR-centric: Uses ApplicationIR as source of truth (preferred)
    - Legacy: Uses spec_requirements
    """

    def __init__(
        self,
        output_path: Path,
        application_ir: Optional[ApplicationIR] = None,
        llm_client: Optional[EnhancedAnthropicClient] = None
    ):
        self.output_path = output_path
        self.entities_file = output_path / "src" / "models" / "entities.py"
        self.routes_dir = output_path / "src" / "api" / "routes"
        self.application_ir = application_ir

    async def repair(
        self,
        compliance_report: ComplianceReport,
        spec_requirements: Optional[SpecRequirements] = None,
        max_attempts: int = 3
    ) -> RepairResult:
        """
        Attempt to repair code based on compliance failures.

        Uses targeted AST patching:
        - Missing entities → Add to entities.py
        - Missing endpoints → Add to appropriate route file
        - Missing validations → Add to schemas.py

        Returns:
            RepairResult with success status and files modified
        """

    async def _repair_from_ir(
        self,
        compliance_report: ComplianceReport
    ) -> RepairResult:
        """
        Repair using ApplicationIR as source of truth.

        Uses DomainModelIR for entity definitions.
        Uses APIModelIR for endpoints.
        """

    def repair_missing_entity(self, entity: Entity) -> bool:
        """Add missing entity to entities.py using AST patching."""

    def repair_missing_endpoint(self, endpoint: Endpoint) -> Optional[str]:
        """Add missing endpoint to route file using AST patching."""

    async def repair_missing_validation(
        self,
        validation_str: str,
        spec_requirements: SpecRequirements
    ) -> bool:
        """Add missing validation to schemas.py."""

@dataclass
class RepairResult:
    """Result of code repair attempt."""
    success: bool
    repaired_files: List[str]
    repairs_applied: List[str]
    error_message: Optional[str] = None
```

### 8.2 Repair Loop (in E2E Pipeline)

**Purpose**: Iterative repair with compliance targets.

```python
# From tests/e2e/real_e2e_full_pipeline.py

async def _execute_repair_loop(
    self,
    initial_compliance_report: ComplianceReport,
    test_results: Dict,
    main_code: str,
    max_iterations: int = 3,
    precision_target: float = 1.00
) -> RepairResult:
    """
    Execute repair loop with compliance targets.

    Steps per iteration:
    1. Analyze failures
    2. Search RAG for similar patterns
    3. Generate repair proposal
    4. Create backup before applying
    5. Apply repair to generated code
    6. Re-validate compliance
    7. Check for regression
    8. Store repair attempt in ErrorPatternStore

    Thresholds:
    - MIN_ACCEPTABLE_COMPLIANCE: 0.65 (stops if below)
    - COMPLIANCE_THRESHOLD: 0.80 (target)
    - REPAIR_IMPROVEMENT_THRESHOLD: 0.85 (post-repair target)
    """
```

---

## Phase 9: Test Generation

### 9.1 IR Test Generator (`src/services/ir_test_generator.py`)

**Purpose**: Generate tests from ValidationModelIR.

```python
def generate_all_tests_from_ir(
    application_ir: ApplicationIR,
    tests_output_dir: Path
) -> List[str]:
    """
    Generate tests from ApplicationIR.

    Generates:
    - test_validation_rules.py: Tests for validation rules
    - test_integration_flows.py: Tests for workflow flows
    - test_api_contracts.py: Tests for API contracts

    Returns:
        List of generated file paths
    """

def generate_validation_tests(
    validation_model: ValidationModelIR
) -> str:
    """Generate tests for validation rules."""

def generate_flow_tests(
    behavior_model: BehaviorModelIR
) -> str:
    """Generate tests for workflow flows."""

def generate_contract_tests(
    api_model: APIModelIR
) -> str:
    """Generate API contract tests."""

def get_flow_coverage_report(
    application_ir: ApplicationIR,
    services_dir: Path
) -> Dict:
    """
    Check flow coverage.

    Returns:
        {
            "coverage_percentage": 0.85,
            "implemented_flows": [...],
            "total_flows": 10,
            "missing_flows": [...]
        }
    """
```

---

## Phase 10: Application Deployment

### 10.1 Output Structure

```
generated_app/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic settings
│   │   ├── database.py            # SQLAlchemy setup
│   │   └── dependencies.py        # FastAPI dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy Base
│   │   ├── entities.py            # ORM entities
│   │   └── schemas.py             # Pydantic schemas
│   ├── repositories/
│   │   └── {entity}_repository.py # Repository pattern
│   ├── services/
│   │   ├── {entity}_service.py    # Business logic
│   │   ├── workflows/             # Workflow implementations
│   │   ├── state_machines/        # State machine validators
│   │   └── validators/            # Business rule validators
│   └── api/
│       └── routes/
│           ├── health.py          # Health check endpoint
│           └── {entity}_router.py # Entity CRUD endpoints
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
│       └── 001_initial_migration.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── .env.example
├── generation_manifest.json       # Generation metadata
├── stratum_metrics.json          # Stratum classification
└── quality_gate.json             # Quality gate results
```

### 10.2 Stratum Classification

```python
# File classification by generation stratum

TEMPLATE_STRATUM = [
    # Infrastructure files (deterministic, no LLM needed)
    "docker-compose.yml", "Dockerfile", "requirements.txt",
    "pyproject.toml", "alembic.ini", "prometheus.yml",
    "core/config.py", "core/database.py", "routes/health.py",
    "models/base.py", "main.py", "README.md", ".env"
]

AST_STRATUM = [
    # Structured code (IR → AST → Code, deterministic)
    "models/entities.py", "models/schemas.py",
    "repositories/", "alembic/versions/", "routes/"
]

LLM_STRATUM = [
    # Business logic (requires LLM for complex logic)
    "services/", "_flow.py", "_business.py", "_custom.py"
]

QA_STRATUM = [
    # Validation files
    "tests/", "quality_gate.json"
]
```

---

## Supporting Infrastructure

### Neo4j Integration (`src/cognitive/infrastructure/neo4j_client.py`)

```python
class Neo4jClient:
    """Neo4j database client for DAG storage and IR persistence."""

    def connect(self): ...
    def close(self): ...
    def execute_query(self, query: str, params: dict): ...

class Neo4jIRRepository:
    """Repository for persisting ApplicationIR to Neo4j."""

    def save_application_ir(self, ir: ApplicationIR): ...
    def load_application_ir(self, app_id: UUID) -> ApplicationIR: ...
```

### Qdrant Integration (`src/cognitive/infrastructure/qdrant_client.py`)

```python
class QdrantPatternClient:
    """Qdrant client for pattern bank storage."""

    # Collections:
    # - semantic_patterns: 384-dim (Sentence-BERT)
    # - devmatrix_patterns: 768-dim (GraphCodeBERT)
```

### RAG System (`src/rag/`)

```python
class UnifiedRetriever:
    """Unified RAG retrieval (Neo4j + Qdrant)."""

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]: ...
```

### LLM Client (`src/llm/enhanced_anthropic_client.py`)

```python
class EnhancedAnthropicClient:
    """
    Enhanced Anthropic API client.

    Features:
    - Prompt caching
    - Streaming support
    - Retry logic
    - Token tracking
    """
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Spec → IR extraction | <30s | ~15s |
| Multi-pass planning | <10s | ~5s |
| Code generation | <2 min | ~2.7 min |
| Compliance validation | <10s | ~5s |
| Full E2E pipeline | <10 min | ~8 min |
| Pattern similarity threshold | ≥60% | 60% |
| Compliance threshold | ≥80% | 90-98% |
| Max LOC per atom | 10 | 10 |
| Pattern success threshold | ≥95% | 95% |

---

## Related Documentation

- [02-ARCHITECTURE.md](02-ARCHITECTURE.md) - System architecture overview
- [04-IR_SYSTEM.md](04-IR_SYSTEM.md) - Detailed IR documentation
- [05-CODE_GENERATION.md](05-CODE_GENERATION.md) - Generation details
- [06-VALIDATION.md](06-VALIDATION.md) - Validation system
- [07-TESTING.md](07-TESTING.md) - E2E pipeline phases

---

*DevMatrix - Complete Pipeline Reference*
*Comprehensive Technical Documentation - November 2025*
