# Phases 0-2: Foundation (Existing)

**Document**: 04 of 15
**Purpose**: Document existing DevMatrix MVP phases that remain unchanged in v2

---

## Overview

Phases 0-2 are **already implemented** in DevMatrix MVP and work well. MGE v2 **keeps them unchanged** and builds on top of them.

**No changes needed** - just understand them for context.

---

## Phase 0: Discovery

### Purpose
Convert user ideas into structured Domain-Driven Design (DDD) specifications.

### Current Implementation

**Technology**: FastAPI + PostgreSQL + Claude Sonnet 4.5

**Process**:
```python
# Conversational intake
def discovery_flow(user_input: str) -> Project:
    """
    Interactive conversation to understand project requirements.
    """
    # 1. Initial requirements gathering
    requirements = gather_requirements(user_input)

    # 2. DDD modeling
    domain_model = create_ddd_model(requirements)

    # 3. Tech stack selection
    tech_stack = select_tech_stack(domain_model, requirements)

    # 4. Create project
    project = Project(
        requirements=requirements,
        domain_model=domain_model,
        tech_stack=tech_stack
    )

    return project
```

### DDD Components

**Entities**:
```python
# Example: E-commerce domain
entities = {
    'User': ['id', 'email', 'name', 'created_at'],
    'Product': ['id', 'name', 'price', 'inventory'],
    'Order': ['id', 'user_id', 'total', 'status'],
    'OrderItem': ['id', 'order_id', 'product_id', 'quantity']
}
```

**Value Objects**:
```python
value_objects = {
    'Address': ['street', 'city', 'country', 'postal_code'],
    'Money': ['amount', 'currency'],
    'Email': ['value']
}
```

**Aggregates**:
```python
aggregates = {
    'OrderAggregate': {
        'root': 'Order',
        'entities': ['OrderItem'],
        'value_objects': ['Money', 'Address']
    }
}
```

**Bounded Contexts**:
```python
bounded_contexts = {
    'Catalog': ['Product', 'Category', 'Inventory'],
    'Sales': ['Order', 'OrderItem', 'Payment'],
    'Identity': ['User', 'Authentication', 'Authorization']
}
```

### Database Schema

```sql
-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- DDD model (JSONB for flexibility)
    domain_model JSONB NOT NULL,
    tech_stack JSONB NOT NULL,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'discovery'
);

-- Domain entities
CREATE TABLE domain_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    properties JSONB NOT NULL,
    relationships JSONB,
    bounded_context VARCHAR(255)
);
```

### Output Example

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "E-commerce Platform",
  "domain_model": {
    "bounded_contexts": [
      {
        "name": "Catalog",
        "entities": [
          {
            "name": "Product",
            "properties": {
              "id": "UUID",
              "name": "String(255)",
              "price": "Decimal(10,2)",
              "inventory": "Integer"
            },
            "relationships": {
              "category": "Category (many-to-one)"
            }
          }
        ]
      }
    ]
  },
  "tech_stack": {
    "backend": "Python 3.11 + FastAPI",
    "database": "PostgreSQL 15",
    "frontend": "React 18 + TypeScript"
  }
}
```

### Success Metrics

✅ **Current Performance**:
- 95% of users complete discovery successfully
- Average time: 15-20 minutes
- DDD models produce quality specifications
- Clear requirements for Phase 1

---

## Phase 1: RAG Retrieval

### Purpose
Find relevant patterns, examples, and best practices from past projects using semantic search.

### Current Implementation

**Technology**: ChromaDB + Claude Sonnet 4.5

**Process**:
```python
import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

def rag_retrieval(project: Project) -> RAGContext:
    """
    Retrieve relevant patterns from past projects.
    """
    # 1. Create semantic query from DDD model
    query = create_semantic_query(project.domain_model)

    # 2. Search ChromaDB
    collection = client.get_collection("code_patterns")
    results = collection.query(
        query_texts=[query],
        n_results=10
    )

    # 3. Filter and rank results
    relevant_patterns = filter_by_relevance(results, threshold=0.7)

    # 4. Extract best practices
    best_practices = extract_best_practices(relevant_patterns)

    return RAGContext(
        patterns=relevant_patterns,
        best_practices=best_practices
    )
```

### ChromaDB Collections

**Code Patterns Collection**:
```python
# Schema
code_patterns_schema = {
    'id': 'pattern_uuid',
    'metadata': {
        'language': 'python',
        'framework': 'fastapi',
        'pattern_type': 'authentication',
        'complexity': 'medium',
        'success_rate': 0.95
    },
    'document': 'code snippet or description',
    'embedding': [0.123, 0.456, ...]  # 1536-dimensional
}

# Example: Authentication pattern
collection.add(
    ids=['auth_jwt_001'],
    metadatas=[{
        'language': 'python',
        'framework': 'fastapi',
        'pattern_type': 'authentication',
        'complexity': 'medium'
    }],
    documents=["""
    JWT authentication with refresh tokens:
    - Use bcrypt for password hashing
    - Store refresh tokens in Redis
    - Rotate tokens every 24 hours
    - Implement rate limiting
    """]
)
```

### Retrieval Strategy

**Query Construction**:
```python
def create_semantic_query(domain_model: dict) -> str:
    """
    Convert DDD model to semantic search query.
    """
    entities = [e['name'] for e in domain_model['entities']]
    relationships = extract_relationships(domain_model)
    tech_stack = domain_model.get('tech_stack', {})

    query = f"""
    Project with entities: {', '.join(entities)}
    Relationships: {', '.join(relationships)}
    Technology: {tech_stack.get('backend', 'unknown')}
    Patterns needed: CRUD operations, authentication, validation
    """

    return query
```

**Result Filtering**:
```python
def filter_by_relevance(results: dict, threshold: float) -> list:
    """
    Filter search results by relevance score.
    """
    filtered = []

    for doc, metadata, distance in zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ):
        # ChromaDB uses cosine distance (lower = more similar)
        similarity = 1 - distance

        if similarity >= threshold:
            filtered.append({
                'document': doc,
                'metadata': metadata,
                'similarity': similarity
            })

    # Sort by similarity (descending)
    filtered.sort(key=lambda x: x['similarity'], reverse=True)

    return filtered
```

### Database Schema

```sql
-- RAG context storage
CREATE TABLE rag_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),

    -- Retrieved patterns (JSONB for flexibility)
    patterns JSONB NOT NULL,
    best_practices JSONB NOT NULL,

    -- Relevance metrics
    avg_similarity FLOAT,
    pattern_count INTEGER,

    -- Timestamps
    retrieved_at TIMESTAMP DEFAULT NOW()
);
```

### Output Example

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "patterns": [
    {
      "type": "authentication",
      "similarity": 0.92,
      "code": "JWT implementation with refresh tokens...",
      "metadata": {
        "language": "python",
        "framework": "fastapi",
        "success_rate": 0.95
      }
    },
    {
      "type": "database_model",
      "similarity": 0.88,
      "code": "SQLAlchemy models for e-commerce...",
      "metadata": {
        "language": "python",
        "framework": "sqlalchemy",
        "success_rate": 0.91
      }
    }
  ],
  "best_practices": [
    "Use bcrypt for password hashing (strength 12)",
    "Implement rate limiting: 5 requests/min for auth",
    "Store refresh tokens in Redis with TTL",
    "Use database transactions for order creation"
  ]
}
```

### Success Metrics

✅ **Current Performance**:
- Average similarity score: 0.85
- Patterns retrieved per project: 8-12
- Relevance to final implementation: 78%
- Reduces implementation errors by 23%

---

## Phase 2: Masterplan Generation

### Purpose
Create hierarchical project plan: Phases → Milestones → Tasks with dependencies.

### Current Implementation

**Technology**: Claude Sonnet 4.5 + PostgreSQL

**Process**:
```python
def generate_masterplan(
    project: Project,
    rag_context: RAGContext
) -> Masterplan:
    """
    Generate hierarchical masterplan from DDD model and RAG context.
    """
    # 1. Create phases
    phases = create_phases(project.domain_model)

    # 2. For each phase, create milestones
    for phase in phases:
        phase.milestones = create_milestones(phase, rag_context)

        # 3. For each milestone, create tasks
        for milestone in phase.milestones:
            milestone.tasks = create_tasks(milestone, rag_context)

    # 4. Identify dependencies
    add_dependencies(phases)

    return Masterplan(phases=phases)
```

### Hierarchy Structure

**Phases** (4-6 per project):
```python
phases = [
    Phase(
        name="Setup & Infrastructure",
        order=1,
        estimated_hours=16
    ),
    Phase(
        name="Core Domain Models",
        order=2,
        estimated_hours=24,
        depends_on=[1]  # Depends on phase 1
    ),
    Phase(
        name="Business Logic & Services",
        order=3,
        estimated_hours=32,
        depends_on=[2]
    ),
    Phase(
        name="API Layer",
        order=4,
        estimated_hours=20,
        depends_on=[2, 3]
    ),
    Phase(
        name="Frontend & Integration",
        order=5,
        estimated_hours=28,
        depends_on=[4]
    )
]
```

**Milestones** (3-5 per phase):
```python
# Example: Phase 2 "Core Domain Models"
milestones = [
    Milestone(
        name="User & Authentication Models",
        phase_id=2,
        order=1,
        estimated_hours=8
    ),
    Milestone(
        name="Product & Catalog Models",
        phase_id=2,
        order=2,
        estimated_hours=6
    ),
    Milestone(
        name="Order & Payment Models",
        phase_id=2,
        order=3,
        estimated_hours=10,
        depends_on=[1]  # Depends on milestone 1
    )
]
```

**Tasks** (8-12 per milestone):
```python
# Example: Milestone "User & Authentication Models"
tasks = [
    Task(
        name="Create User SQLAlchemy Model",
        milestone_id=1,
        description="User model with email, password_hash, created_at",
        estimated_loc=80,
        estimated_hours=2,
        complexity=1.2
    ),
    Task(
        name="Create Authentication Service",
        milestone_id=1,
        description="JWT token generation and validation",
        estimated_loc=120,
        estimated_hours=3,
        complexity=1.5,
        depends_on=[1]  # Depends on task 1
    ),
    Task(
        name="Implement Password Hashing",
        milestone_id=1,
        description="Bcrypt password hashing with salt",
        estimated_loc=40,
        estimated_hours=1,
        complexity=1.0
    )
]
```

### LLM Prompt Structure

```python
MASTERPLAN_PROMPT = """
You are an expert software architect creating a detailed project plan.

**Project Context**:
{project_name}
{domain_model}

**Technology Stack**:
{tech_stack}

**Retrieved Patterns** (from similar projects):
{rag_patterns}

**Your Task**:
Create a hierarchical masterplan with:
1. Phases (4-6 major project phases)
2. Milestones (3-5 per phase)
3. Tasks (8-12 per milestone, ~80 LOC each)

**Requirements**:
- Logical dependency order (dependencies before dependents)
- Realistic time estimates
- Clear descriptions for each task
- Balance complexity across phases

**Output Format**: JSON
"""
```

### Database Schema

```sql
-- Phases
CREATE TABLE phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    order_num INTEGER NOT NULL,
    estimated_hours FLOAT,
    depends_on UUID[],  -- Array of phase IDs
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Milestones
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phase_id UUID REFERENCES phases(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    order_num INTEGER NOT NULL,
    estimated_hours FLOAT,
    depends_on UUID[],  -- Array of milestone IDs
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone_id UUID REFERENCES milestones(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_loc INTEGER DEFAULT 80,
    estimated_hours FLOAT,
    complexity FLOAT DEFAULT 1.0,
    depends_on UUID[],  -- Array of task IDs
    status VARCHAR(50) DEFAULT 'pending',
    code TEXT,  -- Generated code (will be populated in execution)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Dependencies (explicit table for complex queries)
CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_type VARCHAR(50) NOT NULL,  -- 'phase', 'milestone', 'task'
    from_id UUID NOT NULL,
    to_type VARCHAR(50) NOT NULL,
    to_id UUID NOT NULL,
    dependency_type VARCHAR(50) DEFAULT 'sequential',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dependencies_from ON dependencies(from_type, from_id);
CREATE INDEX idx_dependencies_to ON dependencies(to_type, to_id);
```

### Output Example

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "phases": [
    {
      "id": "phase_1",
      "name": "Setup & Infrastructure",
      "order": 1,
      "estimated_hours": 16,
      "milestones": [
        {
          "id": "milestone_1_1",
          "name": "Project Scaffolding",
          "order": 1,
          "estimated_hours": 4,
          "tasks": [
            {
              "id": "task_1_1_1",
              "name": "Initialize FastAPI Project",
              "description": "Create project structure with main.py, routers/, models/, services/",
              "estimated_loc": 60,
              "estimated_hours": 1,
              "complexity": 1.0
            },
            {
              "id": "task_1_1_2",
              "name": "Setup PostgreSQL Connection",
              "description": "Configure SQLAlchemy engine, session, and base models",
              "estimated_loc": 80,
              "estimated_hours": 1.5,
              "complexity": 1.2,
              "depends_on": ["task_1_1_1"]
            }
          ]
        }
      ]
    }
  ],
  "statistics": {
    "total_phases": 5,
    "total_milestones": 18,
    "total_tasks": 142,
    "estimated_total_hours": 180,
    "estimated_total_loc": 11360
  }
}
```

### Dependency Validation

```python
def validate_dependencies(masterplan: Masterplan) -> bool:
    """
    Ensure no circular dependencies and valid references.
    """
    # Build dependency graph
    graph = {}

    for phase in masterplan.phases:
        graph[phase.id] = phase.depends_on or []

        for milestone in phase.milestones:
            graph[milestone.id] = milestone.depends_on or []

            for task in milestone.tasks:
                graph[task.id] = task.depends_on or []

    # Check for cycles
    visited = set()
    rec_stack = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True  # Cycle detected

        rec_stack.remove(node)
        return False

    # Check all nodes
    for node in graph:
        if node not in visited:
            if has_cycle(node):
                raise ValueError(f"Circular dependency detected involving {node}")

    return True
```

### Success Metrics

✅ **Current Performance**:
- Plans generated: 100% success rate
- Average tasks per project: 140-160
- Dependency validation: 98% pass rate
- Realistic estimates: Within 15% of actual time
- Clear task descriptions: 92% implementable without clarification

---

## Integration with v2

### How Phases 0-2 Connect to v2

**Phase 0 → Phase 3**:
```
Discovery (DDD model)
→ Masterplan (Tasks)
→ AST Atomization (AtomicUnits)
```

**Phase 1 → Phase 3**:
```
RAG (Patterns)
→ Context Injection (95% completeness)
→ AtomicUnit context enrichment
```

**Phase 2 → Phase 4**:
```
Masterplan (Task dependencies)
→ Dependency Graph (Atom dependencies)
→ Topological Sort (Generation order)
```

### v2 Enhancement Points

1. **Finer Granularity**:
   - MVP: 80 LOC tasks → 25 LOC subtasks
   - v2: 25 LOC subtasks → 10 LOC atoms ✅

2. **Better Context**:
   - MVP: 70% context completeness
   - v2: 95% context completeness ✅

3. **Dependency Precision**:
   - MVP: Task-level dependencies (coarse)
   - v2: Atom-level dependencies (fine) ✅

---

## No Changes Needed

**These phases work well** - no modifications required for v2:

✅ Discovery produces quality DDD models
✅ RAG retrieves relevant patterns effectively
✅ Masterplan creates logical hierarchies
✅ Existing database schema is sufficient
✅ LLM prompts are well-tuned

**Just add**:
- Phase 3 (AST Atomization) ← Next document
- Phase 4 (Dependency Graph)
- Phase 5 (Hierarchical Validation)
- Phase 6 (Execution + Retry)
- Phase 7 (Human Review)

---

**Next Document**: [05_PHASE_3_AST_ATOMIZATION.md](05_PHASE_3_AST_ATOMIZATION.md) - AST parsing and recursive decomposition
