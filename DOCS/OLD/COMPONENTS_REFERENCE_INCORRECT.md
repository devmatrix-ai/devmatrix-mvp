# Components Reference Guide

**Document Date:** 2025-11-23
**Status:** Complete Component Documentation
**Version:** 1.0
**Scope:** Detailed reference for all system components

---

## Overview

This document provides a comprehensive reference for every major component in the agentic-ai system, including its purpose, location, key methods, and integration points.

### Quick Navigation

- [Cognitive Engine Components](#cognitive-engine-components)
- [Code Generation Components](#code-generation-components)
- [RAG System Components](#rag-system-components)
- [Data Models & ORM](#data-models--orm)
- [API Components](#api-components)
- [Infrastructure Components](#infrastructure-components)
- [Support Services](#support-services)

---

## Cognitive Engine Components

### 1. Orchestrator MVP

**Path**: `src/cognitive/orchestration/orchestrator_mvp.py`

**Purpose**: Main orchestrator for the 11-phase pipeline

**Key Methods**:
```python
async def orchestrate_specification(
    spec: SpecRequirements,
    context: Optional[ExecutionContext] = None
) -> ExecutionResult:
    """
    Execute full 11-phase pipeline for a specification

    Args:
        spec: Input specification from user
        context: Optional execution context with RAG patterns

    Returns:
        ExecutionResult with generated code and artifacts
    """

async def execute_phase(
    phase: int,
    input_data: Any,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG
) -> PhaseResult:
    """
    Execute single phase with error handling and retries

    Args:
        phase: Phase number (1-11)
        input_data: Data from previous phase
        retry_config: Retry configuration

    Returns:
        PhaseResult with status and output
    """

async def track_progress(
    execution_id: str
) -> ProgressStatus:
    """Track current execution progress across phases"""

async def handle_phase_failure(
    phase: int,
    error: Exception
) -> RecoveryStrategy:
    """Determine recovery strategy for phase failure"""
```

**Integration Points**:
- Called by: `POST /api/masterplans/{id}/execute` endpoint
- Calls: All phase handlers, CPIE, Pattern Bank
- Uses: RAG retriever for pattern context
- Updates: Redis execution state, PostgreSQL results

**Dependencies**:
```python
from src.cognitive.planning import MultiPassPlanner
from src.cognitive.planning import DAGBuilder
from src.cognitive.inference import CPIE
from src.cognitive.patterns import PatternBank
from src.cognitive.validation import EnsembleValidator
from src.rag import UnifiedRetriever
```

---

### 2. IR Builder & Management

**Path**: `src/cognitive/ir/`

#### 2.1 ApplicationIR (Root Model)

**Path**: `src/cognitive/ir/application_ir.py`

**Purpose**: Root aggregate for application definition

**Structure**:
```python
@dataclass
class ApplicationIR:
    app_id: UUID
    name: str
    description: str
    domain_model: DomainModelIR
    api_model: APIModelIR
    infrastructure_model: InfrastructureModelIR
    behavior_model: BehaviorModelIR
    validation_model: ValidationModelIR
    phase_status: Dict[str, str]      # Phase → status mapping
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"
```

#### 2.2 Domain Model

**Path**: `src/cognitive/ir/domain_model.py`

**Purpose**: Define entities, attributes, and relationships

**Key Classes**:
```python
@dataclass
class Entity:
    name: str
    attributes: List[Attribute]
    relationships: List[Relationship]
    is_aggregate_root: bool = False
    description: str = ""
    constraints: Optional[Dict] = None

@dataclass
class Attribute:
    name: str
    data_type: DataType
    is_primary_key: bool = False
    is_nullable: bool = True
    is_unique: bool = False
    default_value: Optional[Any] = None

@dataclass
class Relationship:
    source_entity: str
    target_entity: str
    type: RelationshipType
    field_name: str
    cardinality: Cardinality = "one_to_many"
    back_populates: Optional[str] = None
    cascade_delete: bool = False
```

#### 2.3 API Model

**Path**: `src/cognitive/ir/api_model.py`

**Purpose**: Define REST API endpoints

**Key Classes**:
```python
@dataclass
class Endpoint:
    path: str
    method: HttpMethod
    operation_id: str
    parameters: List[APIParameter]
    request_schema: Optional[APISchema]
    response_schema: Optional[APISchema]
    auth_required: bool = True
    tags: List[str] = field(default_factory=list)
    rate_limit: Optional[RateLimit] = None

@dataclass
class APISchema:
    type: str  # "object", "array", etc
    properties: Dict[str, Any]
    required: List[str]
    example: Optional[Dict] = None
```

#### 2.4 IR Builder

**Path**: `src/cognitive/ir/ir_builder.py`

**Purpose**: Construct ApplicationIR from specifications

**Key Methods**:
```python
class IRBuilder:
    async def build_from_spec(
        self,
        spec: SpecRequirements
    ) -> ApplicationIR:
        """Build complete ApplicationIR from specification"""

    async def extract_domain_model(
        self,
        spec: SpecRequirements
    ) -> DomainModelIR:
        """Extract domain model from spec"""

    async def extract_api_model(
        self,
        domain_model: DomainModelIR
    ) -> APIModelIR:
        """Generate API model from domain model"""

    async def extract_infrastructure_model(
        self,
        spec: SpecRequirements
    ) -> InfrastructureModelIR:
        """Extract infrastructure requirements"""

    async def normalize_ir(
        self,
        ir: ApplicationIR
    ) -> ApplicationIR:
        """Normalize IR for consistency"""
```

---

### 3. Planning Components

**Path**: `src/cognitive/planning/`

#### 3.1 Multi-Pass Planner

**Purpose**: Decompose specifications into atomic tasks

**Key Methods**:
```python
class MultiPassPlanner:
    async def decompose_to_tasks(
        self,
        spec: SpecRequirements
    ) -> List[AtomicTask]:
        """
        Multi-pass decomposition:
        Pass 1: High-level tasks
        Pass 2: Atomize large tasks
        Pass 3: Add dependencies
        Pass 4: Create semantic signatures
        """

    async def create_semantic_signatures(
        self,
        tasks: List[AtomicTask]
    ) -> List[SemanticSignature]:
        """Create semantic signatures for pattern matching"""
```

**Task Output**:
```python
@dataclass
class AtomicTask:
    id: UUID
    task_type: str  # entity|endpoint|validation|etc
    name: str
    description: str
    inputs: List[str]               # Input dependencies
    outputs: List[str]              # Output artifacts
    rag_context: Optional[RAGContext] = None
    estimated_complexity: float = 0.5
    success_criteria: List[str] = field(default_factory=list)
```

#### 3.2 DAG Builder

**Purpose**: Build dependency graph for parallel execution

**Key Methods**:
```python
class DAGBuilder:
    async def build_dag(
        self,
        tasks: List[AtomicTask]
    ) -> ExecutionDAG:
        """
        Build directed acyclic graph:
        1. Analyze dependencies
        2. Create edges
        3. Topological sort
        4. Identify execution levels
        """

    def get_execution_levels(
        self,
        dag: ExecutionDAG
    ) -> List[List[AtomicTask]]:
        """Return tasks grouped by execution level (for parallelization)"""

    def validate_dag(
        self,
        dag: ExecutionDAG
    ) -> ValidationResult:
        """Validate DAG for cycles and consistency"""
```

**DAG Structure**:
```python
@dataclass
class ExecutionDAG:
    nodes: Dict[str, AtomicTask]      # Task ID → Task
    edges: List[Tuple[str, str]]      # (from_task_id, to_task_id)
    levels: List[List[str]]           # Execution levels (task IDs)
    criticality_path: List[str]       # Critical path for optimization
    parallelization_factor: float     # Estimated parallelization gain
```

---

### 4. CPIE - Core Pattern Inference Engine

**Path**: `src/cognitive/inference/cpie.py`

**Purpose**: Execute individual tasks using patterns

**Key Methods**:
```python
class CPIE:
    async def execute_task(
        self,
        task: AtomicTask,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute task with pattern inference:
        1. Retrieve patterns from RAG
        2. Select best matching pattern
        3. Apply pattern
        4. Generate code
        5. Validate output
        """

    async def execute_with_patterns(
        self,
        task: AtomicTask,
        rag_context: RAGContext
    ) -> TaskResult:
        """Execute using specific patterns"""

    async def fallback_execute(
        self,
        task: AtomicTask
    ) -> TaskResult:
        """Fallback if pattern execution fails"""
```

---

### 5. Pattern Bank

**Path**: `src/cognitive/patterns/pattern_bank.py`

**Purpose**: Manage pattern library with auto-evolution

**Key Methods**:
```python
class PatternBank:
    async def find_matching_patterns(
        self,
        task: AtomicTask,
        top_k: int = 5
    ) -> List[PatternMatch]:
        """Find patterns matching task description"""

    async def retrieve_pattern(
        self,
        pattern_id: UUID
    ) -> Pattern:
        """Retrieve specific pattern"""

    async def promote_pattern(
        self,
        pattern: Pattern,
        execution_metrics: ExecutionMetrics
    ) -> None:
        """
        Promote pattern to higher tier if successful:
        Tier 1 (Low): Success rate < 70%
        Tier 2 (Medium): Success rate 70-90%
        Tier 3 (High): Success rate 90-95%
        Tier 4 (Production): Success rate > 95%
        """

    async def update_pattern_usage(
        self,
        pattern_id: UUID,
        execution_result: ExecutionResult
    ) -> None:
        """Update pattern usage statistics"""

    def get_pattern_statistics(self) -> PatternLibraryStats:
        """Get library statistics (total, by type, success rates)"""
```

**Pattern Structure**:
```python
@dataclass
class Pattern:
    id: UUID
    name: str
    category: str              # entity|api|validation|etc
    domain: str                # auth|data|api|etc
    code: str                  # Template code
    tier: PatternTier          # 1-4
    success_rate: float        # 0-1
    usage_count: int
    created_at: datetime
    last_used: datetime
    embedding: Optional[List[float]]  # 768-dim GraphCodeBERT
    tags: List[str]
    metadata: Dict[str, Any]
```

---

### 6. Validation System

**Path**: `src/cognitive/validation/`

#### 6.1 Ensemble Validator

**Purpose**: Multi-validator ensemble for comprehensive checks

**Key Methods**:
```python
class EnsembleValidator:
    async def validate(
        self,
        artifact: CodeArtifact
    ) -> ValidationResult:
        """
        Run all validators:
        1. Syntax validator
        2. Type validator
        3. Semantic validator
        4. Business rule validator
        5. Performance validator
        """

    async def validate_with_weights(
        self,
        artifact: CodeArtifact,
        validator_weights: Dict[str, float]
    ) -> WeightedValidationResult:
        """Validate with weighted scoring"""

    async def collect_validator_feedback(
        self
    ) -> ValidatorFeedbackReport:
        """Collect feedback from all validators"""
```

#### 6.2 E2E Production Validator

**Purpose**: End-to-end production readiness validation

**Key Methods**:
```python
class E2EProductionValidator:
    async def validate_complete_system(
        self,
        generated_code: GeneratedApplication
    ) -> ProductionReadinessReport:
        """
        Validate entire system:
        1. Code quality checks
        2. Security scanning
        3. Performance profiling
        4. Dependency analysis
        5. Deployment readiness
        """

    async def check_production_readiness(
        self,
        app: GeneratedApplication
    ) -> ReadinessScore:
        """Score application for production readiness (0-100)"""
```

---

### 7. Semantic Signatures

**Path**: `src/cognitive/signatures/semantic_signature.py`

**Purpose**: Create semantic representation of tasks for matching

**Key Methods**:
```python
class SemanticSignature:
    @staticmethod
    async def create_from_task(
        task: AtomicTask
    ) -> SemanticSignature:
        """Create signature from task description"""

    @staticmethod
    async def create_from_code(
        code: str
    ) -> SemanticSignature:
        """Create signature from code"""

    def similarity_to(
        self,
        other: 'SemanticSignature'
    ) -> float:
        """Calculate similarity (0-1)"""

    def to_embedding(self) -> List[float]:
        """Convert to 768-dim embedding"""
```

---

## Code Generation Components

### 1. Code Generation Service

**Path**: `src/services/code_generation_service.py`

**Purpose**: Main service for code generation

**Key Methods**:
```python
class CodeGenerationService:
    async def generate_entity(
        self,
        entity_spec: EntitySpec,
        rag_context: Optional[RAGContext] = None
    ) -> GeneratedEntity:
        """Generate SQLAlchemy entity model"""

    async def generate_endpoint(
        self,
        endpoint_spec: EndpointSpec,
        domain_model: DomainModelIR
    ) -> GeneratedEndpoint:
        """Generate FastAPI endpoint"""

    async def generate_validation_code(
        self,
        validation_spec: ValidationSpec
    ) -> GeneratedTests:
        """Generate pytest test code"""

    async def generate_migrations(
        self,
        changes: SchemaChanges
    ) -> List[MigrationFile]:
        """Generate Alembic migrations"""
```

### 2. Behavior Code Generator

**Path**: `src/services/behavior_code_generator.py`

**Purpose**: Generate business logic code

**Key Methods**:
```python
class BehaviorCodeGenerator:
    async def generate_service_methods(
        self,
        entity: Entity,
        behaviors: List[Behavior]
    ) -> ServiceClass:
        """Generate service class with CRUD methods"""

    async def generate_business_rules(
        self,
        rules: List[BusinessRule]
    ) -> RuleImplementation:
        """Generate business rule enforcement code"""

    async def generate_workflow_code(
        self,
        workflow: WorkflowDefinition
    ) -> WorkflowImplementation:
        """Generate workflow execution code"""
```

### 3. Validation Code Generator

**Path**: `src/services/validation_code_generator.py`

**Purpose**: Generate test and validation code

**Key Methods**:
```python
class ValidationCodeGenerator:
    async def generate_unit_tests(
        self,
        entity: Entity
    ) -> List[TestFile]:
        """Generate unit tests for entity"""

    async def generate_integration_tests(
        self,
        endpoint: Endpoint
    ) -> List[TestFile]:
        """Generate integration tests for endpoint"""

    async def generate_e2e_tests(
        self,
        workflow: Workflow
    ) -> List[TestFile]:
        """Generate end-to-end tests"""

    async def generate_validation_rules(
        self,
        entity: Entity
    ) -> ValidationRuleSet:
        """Generate validation rules"""
```

### 4. OpenAPI Generator

**Path**: `src/services/openapi_generator.py`

**Purpose**: Generate OpenAPI/Swagger documentation

**Key Methods**:
```python
class OpenAPIGenerator:
    async def generate_spec(
        self,
        api_model: APIModelIR
    ) -> OpenAPISpec:
        """Generate complete OpenAPI specification"""

    async def generate_schemas(
        self,
        domain_model: DomainModelIR
    ) -> Dict[str, JSONSchema]:
        """Generate JSON schemas for all entities"""

    async def generate_documentation(
        self,
        api_spec: OpenAPISpec
    ) -> DocumentationHTML:
        """Generate interactive API documentation"""
```

### 5. Modular Architecture Generator

**Path**: `src/services/modular_architecture_generator.py`

**Purpose**: Generate modular code structure

**Key Methods**:
```python
class ModularArchitectureGenerator:
    async def generate_project_structure(
        self,
        app_config: AppConfig
    ) -> ProjectStructure:
        """
        Generate directory structure:
        src/
          models/
          services/
          api/
          config/
          ...
        """

    async def generate_module_files(
        self,
        modules: List[Module]
    ) -> List[ModuleFile]:
        """Generate Python module files with __init__.py"""

    async def generate_imports(
        self,
        dependencies: DependencyGraph
    ) -> ImportStatements:
        """Generate correct import statements"""
```

---

## RAG System Components

See [RAG_SYSTEM.md](RAG_SYSTEM.md) for comprehensive RAG documentation.

### Key Components:

1. **UnifiedRetriever** - Main orchestrator
2. **Retriever** - Core retrieval interface
3. **Vector Store** (ChromaDB) - Semantic embeddings
4. **Embeddings** - Model management
5. **Query Expander** - Query enhancement
6. **Reranker** - Result re-ranking
7. **Context Builder** - Result formatting
8. **Feedback Service** - Quality tracking

---

## Data Models & ORM

### Core Models

**Path**: `src/models/`

#### User Management
```python
class User(Base):
    __tablename__ = "users"
    id: UUID
    email: str (unique)
    username: str (unique)
    password_hash: str
    is_active: bool
    created_at, updated_at: datetime

class Role(Base):
    __tablename__ = "roles"
    id: UUID
    name: str (unique)
    permissions: List[str]

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: UUID (FK → users)
    role_id: UUID (FK → roles)
```

#### Chat & Conversation
```python
class Conversation(Base):
    __tablename__ = "conversations"
    id: UUID
    user_id: UUID (FK → users)
    title: str
    created_at, updated_at: datetime

class Message(Base):
    __tablename__ = "messages"
    id: UUID
    conversation_id: UUID (FK → conversations)
    role: str ("user" | "assistant")
    content: str
    timestamp: datetime
```

#### Execution & Planning
```python
class MasterPlan(Base):
    __tablename__ = "masterplans"
    id: UUID
    application_id: UUID
    user_id: UUID
    status: str
    created_at, updated_at: datetime

class MasterPlanTask(Base):
    __tablename__ = "masterplan_tasks"
    id: UUID
    masterplan_id: UUID (FK)
    task_name: str
    status: str
    rag_context: JSON
    result: Optional[str]
```

#### Validation & Quality
```python
class ValidationResult(Base):
    __tablename__ = "validation_results"
    id: UUID
    execution_id: UUID
    validator_type: str
    passed: bool
    details: JSON
    timestamp: datetime

class AcceptanceTest(Base):
    __tablename__ = "acceptance_tests"
    id: UUID
    application_id: UUID
    name: str
    scenario: str
    input_data: JSON
    expected_outcome: str
```

#### Audit & Security
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: UUID
    user_id: UUID (FK)
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    timestamp: datetime
    ip_address: str

class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: UUID
    event_type: str
    severity: str ("low"|"medium"|"high"|"critical")
    description: str
    timestamp: datetime
```

---

## API Components

**Path**: `src/api/routers/`

### Router Overview

| Router | Purpose | Key Endpoints |
|--------|---------|---------------|
| auth | Authentication/Authorization | /login, /register, /token |
| chat | Chat conversations | /chat, /chat/stream, /chat/history |
| masterplans | Execution planning | /masterplans, /masterplans/{id}/execute |
| executions | Execution tracking | /executions, /executions/{id}/status |
| rag | RAG operations | /rag/retrieve, /rag/patterns |
| validation | Code validation | /validate, /validate/results |
| health | System health | /health, /ready, /live |
| review | Code review | /review, /review/{id}/approve |
| atomization | Task atomization | /atomization, /atomization/{id} |

### Request/Response Pattern

```python
# Standard request
@router.post("/api/endpoint")
async def handle_request(
    request: RequestModel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ResponseModel:
    """Handle request with auth and DB session"""

# Standard response
@dataclass
class ResponseModel:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = field(default_factory=lambda: str(uuid4()))
```

---

## Infrastructure Components

### 1. Database Layer

**Path**: `src/core/database.py`

```python
class Database:
    @staticmethod
    def get_engine() -> Engine:
        """Get SQLAlchemy engine"""

    @staticmethod
    def get_session() -> Session:
        """Get database session"""

    @staticmethod
    async def init_db():
        """Initialize database schema"""

    @staticmethod
    async def health_check() -> bool:
        """Check database connectivity"""
```

### 2. Cache Layer

**Path**: `src/core/cache.py`

```python
class Cache:
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Get value from Redis"""

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis with TTL"""

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete value from Redis"""

    @staticmethod
    async def health_check() -> bool:
        """Check Redis connectivity"""
```

### 3. Security

**Path**: `src/core/security.py`

```python
class Security:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""

    @staticmethod
    def verify_password(password: str, hash: str) -> bool:
        """Verify password against hash"""

    @staticmethod
    def create_jwt_token(data: dict, expires_in: int) -> str:
        """Create JWT token"""

    @staticmethod
    def verify_jwt_token(token: str) -> dict:
        """Verify and decode JWT token"""
```

---

## Support Services

### 1. Masterplan Services

**Path**: `src/services/masterplan_*.py`

```python
class MasterPlanGenerator:
    async def generate_from_spec(
        self,
        spec: SpecRequirements
    ) -> MasterPlan:
        """Generate execution plan from specification"""

class MasterPlanExecutionService:
    async def execute_plan(
        self,
        plan: MasterPlan
    ) -> ExecutionResult:
        """Execute masterplan"""
```

### 2. Error Handling

**Path**: `src/services/error_pattern_*.py`

```python
class ErrorPatternStore:
    async def analyze_error(
        self,
        error: Exception
    ) -> ErrorPattern:
        """Analyze error and find pattern"""

    async def get_solution(
        self,
        error_pattern: ErrorPattern
    ) -> Solution:
        """Get solution for error pattern"""
```

### 3. Business Logic Extraction

**Path**: `src/services/business_logic_extractor.py`

```python
class BusinessLogicExtractor:
    async def extract_from_spec(
        self,
        spec: SpecRequirements
    ) -> BusinessLogicDefinition:
        """Extract business logic from specification"""

    async def generate_rules(
        self,
        logic: BusinessLogicDefinition
    ) -> List[BusinessRule]:
        """Generate executable business rules"""
```

### 4. File Writing

**Path**: `src/services/file_writer_service.py`

```python
class FileWriterService:
    async def write_files(
        self,
        files: List[GeneratedFile],
        output_dir: str
    ) -> WriteResult:
        """Write generated files to directory"""

    async def create_project_structure(
        self,
        structure: ProjectStructure,
        base_dir: str
    ) -> bool:
        """Create directory structure"""
```

---

## Service Dependencies

### Common Import Pattern

```python
# Most services follow this dependency injection pattern:

from fastapi import Depends
from src.core.database import get_db
from src.core.security import get_current_user
from src.cognitive.orchestration import OrchestratorMVP
from src.rag.unified_retriever import UnifiedRetriever

class MyService:
    def __init__(
        self,
        orchestrator: OrchestratorMVP = Depends(),
        rag_retriever: UnifiedRetriever = Depends(),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        self.orchestrator = orchestrator
        self.rag_retriever = rag_retriever
        self.db = db
        self.current_user = current_user
```

---

## Testing Components

**Path**: `tests/`

```
tests/
├── unit/                 # Unit tests for individual components
├── integration/          # Integration tests for component interactions
├── e2e/                  # End-to-end tests
├── fixtures/             # Shared test fixtures
├── conftest.py          # Pytest configuration
└── test_*.py            # Test files
```

### Test Structure

```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestMyComponent:
    @pytest.fixture
    def my_component(self):
        """Create test instance"""
        return MyComponent()

    @pytest.mark.asyncio
    async def test_method(self, my_component):
        """Test component method"""
        result = await my_component.method()
        assert result is not None

    def test_with_mock(self):
        """Test with mocks"""
        mock_dep = Mock()
        component = MyComponent(dep=mock_dep)
        component.use_dep()
        mock_dep.method.assert_called_once()
```

---

## Configuration Components

**Path**: `src/config/`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Agentic AI"

    # Database Configuration
    database_url: str = "postgresql://user:pass@localhost/db"
    database_echo: bool = False

    # Cache Configuration
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600

    # RAG Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    neo4j_url: str = "bolt://localhost:7687"

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600

    # Feature Flags
    enable_rag: bool = True
    enable_pattern_learning: bool = True

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        import os
        return cls(
            api_port=int(os.getenv("API_PORT", 8000)),
            database_url=os.getenv("DATABASE_URL"),
            # ... load other settings
        )
```

---

## Dependency Graph

```
RequestHandler (API Router)
    ├── Authentication/Authorization
    ├── Validation (Pydantic)
    │
    ├→ Service Layer
    │   ├── CodeGenerationService
    │   │   ├── RAG UnifiedRetriever
    │   │   ├── CPIE Inference Engine
    │   │   ├── Pattern Bank
    │   │   └── Validators (Ensemble)
    │   │
    │   ├── MasterPlanService
    │   │   ├── IR Builder
    │   │   ├── Multi-Pass Planner
    │   │   └── DAG Builder
    │   │
    │   └── ExecutionService
    │       ├── Orchestrator MVP
    │       └── Progress Tracking
    │
    ├→ Data Access Layer
    │   ├── PostgreSQL (SQLAlchemy)
    │   ├── Redis (Cache)
    │   ├── Neo4j (Graph)
    │   └── Qdrant (Vector DB)
    │
    └→ Infrastructure
        ├── Security (JWT, Hashing)
        ├── Logging
        ├── Metrics
        └── Error Handling
```

---

**Last Updated**: 2025-11-23
**Maintained By**: Agentic AI Team
**Version**: 1.0
