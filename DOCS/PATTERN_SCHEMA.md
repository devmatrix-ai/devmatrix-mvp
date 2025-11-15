# Pattern Schema Documentation

**Date**: 2025-11-15
**Status**: Active Production Data
**Purpose**: Document existing pattern storage schema in Neo4j and Qdrant for cognitive architecture integration

---

## Overview

DevMatrix has **51,695 patterns** extracted from 9 production repositories, stored in two complementary systems:

- **Neo4j**: 30,071 patterns with graph relationships
- **Qdrant**: 21,624 patterns with vector embeddings

**Extraction Date**: 2025-11-14
**Source Repositories**: Supabase, Next.js, FastAPI, Prisma, tRPC, Next-auth, Flowbite React, fullstack-next-fastapi, fastapi-nextjs

---

## Neo4j Schema (Graph Database)

### Connection Details
- **URI**: `bolt://localhost:7687`
- **User**: `neo4j`
- **Password**: `devmatrix`
- **Ports**: 7474 (HTTP/Browser), 7687 (Bolt protocol)

### Node Types

#### 1. Pattern Node (30,071 nodes)

**Properties**:
```python
{
    "pattern_id": str,          # Unique ID: "{repo}_{type}_{name}_{hash}"
    "name": str,                # Function/class/component name
    "pattern_type": str,        # "function", "class", "component", "hook", etc.
    "language": str,            # "python", "javascript", "typescript"
    "framework": str,           # "fastapi", "nextjs", "react", "supabase", etc.
    "category": str,            # "auth", "api", "database", "ui", "utils", "other"
    "repo_name": str,           # Source repository name
    "file_path": str,           # Relative path in source repo
    "complexity": int,          # Cyclomatic complexity (1-10+)
    "loc": int,                 # Lines of code (2-500+)
    "hash": str,                # Content hash (16 chars hex)
    "code": str,                # Full source code
    "description": str,         # Auto-generated description
    "extracted_at": str         # ISO 8601 timestamp
}
```

**Example**:
```cypher
(:Pattern {
    pattern_id: "supabase_function_add_numbers_2fa223737338cdbc",
    name: "add_numbers",
    pattern_type: "function",
    language: "python",
    framework: "supabase",
    category: "other",
    repo_name: "supabase",
    file_path: "_internal/fixtures/python.py",
    complexity: 5,
    loc: 2,
    hash: "2fa223737338cdbc",
    code: "def add_numbers(a, b):\n    return a + b",
    description: "Function 'add_numbers' - supabase other implementation",
    extracted_at: "2025-11-14T03:33:52.574063"
})
```

#### 2. Tag Node (21 nodes)

**Properties**:
```python
{
    "name": str  # Tag name
}
```

**All Tags**:
`unknown`, `other`, `ui`, `api`, `auth`, `database`, `config`, `utils`, `component`, `hook`, `middleware`, `model`, `schema`, `service`, `controller`, `route`, `test`, `type`, `constant`, `helper`, `validator`

#### 3. Category Node (13 nodes)

**Properties**:
```python
{
    "name": str  # Category name
}
```

**All Categories**:
- `Authentication`
- `Backend`
- `Database`
- `Domain Models`
- `Frontend`
- `Infrastructure`
- `api`
- `auth`
- `config`
- `database`
- `other`
- `ui`
- `utils`

#### 4. Framework Node (6 nodes)

**Properties**:
```python
{
    "name": str  # Framework name
}
```

**All Frameworks**:
- `fastapi`
- `nextjs`
- `prisma`
- `react`
- `sqlalchemy`
- `supabase`

#### 5. Repository Node (9 nodes)

**Properties**:
```python
{
    "name": str  # Repository name
}
```

**All Repositories**:
- `fastapi` (2,196 patterns)
- `fastapi-nextjs` (54 patterns)
- `flowbite-react` (499 patterns)
- `fullstack-next-fastapi` (189 patterns)
- `next-auth` (404 patterns)
- `next.js` (37,426 patterns)
- `prisma` (1,414 patterns)
- `supabase` (6,509 patterns)
- `trpc` (440 patterns)

#### 6. Template Node (10 nodes)

**Properties**: Unknown (requires further investigation)

#### 7. Dependency Node (84 nodes)

**Properties**: Unknown (requires further investigation)

### Relationships

#### Pattern → Tag (HAS_TAG)
```cypher
(:Pattern)-[:HAS_TAG]->(:Tag)
```
Multiple tags per pattern allowed.

#### Pattern → Category (IN_CATEGORY)
```cypher
(:Pattern)-[:IN_CATEGORY]->(:Category)
```
One category per pattern.

#### Pattern → Framework (USES_FRAMEWORK)
```cypher
(:Pattern)-[:USES_FRAMEWORK]->(:Framework)
```
One framework per pattern.

#### Pattern → Repository (FROM_REPO)
```cypher
(:Pattern)-[:FROM_REPO]->(:Repository)
```
One repository per pattern.

#### Pattern → Pattern (DEPENDS_ON) - 84 relationships
```cypher
(:Pattern)-[:DEPENDS_ON]->(:Pattern)
```
Code-level dependencies between patterns (limited extraction).

### Common Queries

#### Find patterns by framework
```cypher
MATCH (p:Pattern)-[:USES_FRAMEWORK]->(f:Framework {name: 'fastapi'})
RETURN p
LIMIT 10
```

#### Find auth patterns
```cypher
MATCH (p:Pattern)-[:IN_CATEGORY]->(c:Category {name: 'auth'})
RETURN p.name, p.code
LIMIT 5
```

#### Find patterns with dependencies
```cypher
MATCH (p1:Pattern)-[:DEPENDS_ON]->(p2:Pattern)
RETURN p1.name, p2.name
```

#### Find reusable dependency chains
```cypher
MATCH path=(p1:Pattern)-[:DEPENDS_ON*1..3]->(p2:Pattern)
WHERE p1.category = 'auth'
RETURN path
LIMIT 5
```

#### Distribution by framework
```cypher
MATCH (p:Pattern)-[:USES_FRAMEWORK]->(f:Framework)
RETURN f.name, count(p) as pattern_count
ORDER BY pattern_count DESC
```

---

## Qdrant Schema (Vector Database)

### Connection Details
- **Host**: `localhost`
- **Port**: 6333 (HTTP API), 6334 (gRPC)
- **Collections**:
  - `devmatrix_patterns` (21,624 patterns)
  - `semantic_patterns` (0 patterns - ready for use)

### Collection: `devmatrix_patterns`

**Configuration**:
```json
{
    "vectors": {
        "size": 768,
        "distance": "Cosine"
    },
    "indexed_vectors_count": 18755,
    "points_count": 21624,
    "segments_count": 4
}
```

**Vector Embeddings**: 768-dimensional Sentence Transformers embeddings

**Payload Schema**:
```python
{
    # Identifiers
    "pattern_id": str,          # Unique ID matching Neo4j
    "name": str,                # Pattern name
    "hash": str,                # Content hash (16 chars)

    # Classification
    "pattern_type": str,        # "function", "class", "component", etc.
    "language": str,            # "python", "javascript", "typescript"
    "framework": str,           # Framework name
    "category": str,            # Category name
    "repo_name": str,           # Source repository

    # Location
    "file_path": str,           # Relative path in source repo

    # Metrics
    "complexity": int,          # Cyclomatic complexity
    "loc": int,                 # Lines of code

    # Metadata
    "extracted_at": str,        # ISO 8601 timestamp
    "tags": str,                # Comma-separated tag list
    "dependencies": str,        # Comma-separated dependencies

    # Content
    "code": str,                # Full source code
    "document": str             # Formatted text for embedding
}
```

**Example Point**:
```json
{
    "id": "000915fd-8256-5a47-891d-a757f396b35b",
    "payload": {
        "pattern_id": "next.js_function_normalizeListenerOptions_8852aa3e91808a9c",
        "name": "normalizeListenerOptions",
        "pattern_type": "function",
        "language": "javascript",
        "framework": "nextjs",
        "category": "other",
        "repo_name": "next.js",
        "file_path": "react-dom-experimental/cjs/react-dom-profiling.profiling.js",
        "complexity": 4,
        "loc": 12,
        "hash": "8852aa3e91808a9c",
        "extracted_at": "2025-11-14T03:34:10.739752",
        "tags": "nextjs, other",
        "dependencies": "",
        "code": "function normalizeListenerOptions(opts) {...}",
        "document": "Pattern: normalizeListenerOptions\nType: function\n..."
    },
    "vector": [0.123, -0.456, 0.789, ...]  // 768 dimensions
}
```

### Collection: `semantic_patterns` (Empty - Ready for Use)

**Purpose**: Store cognitive architecture generated patterns with semantic task signatures

**Configuration**:
```json
{
    "vectors": {
        "size": 768,
        "distance": "Cosine"
    },
    "points_count": 0
}
```

**Planned Payload Schema** (for cognitive architecture):
```python
{
    # From existing schema
    "pattern_id": str,
    "name": str,
    "pattern_type": str,
    "language": str,
    "framework": str,
    "category": str,
    "code": str,

    # NEW: Semantic Task Signature fields
    "semantic_hash": str,           # SHA256 of semantic properties
    "purpose": str,                 # Normalized task objective
    "intent": str,                  # Action verb (create, validate, etc.)
    "inputs": dict,                 # {param_name: type_name}
    "outputs": dict,                # {return_name: type_name}
    "domain": str,                  # "auth", "crud", "api", etc.
    "constraints": list,            # ["max_10_loc", "async", etc.]
    "security_level": str,          # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    "performance_tier": str,        # "LOW", "MEDIUM", "HIGH"
    "idempotency": bool,            # Is task idempotent?

    # NEW: Pattern quality metrics
    "precision_score": float,       # Validation precision (0.0-1.0)
    "usage_count": int,             # How many times reused
    "success_rate": float,          # Success rate when applied
    "first_generated_at": str,      # ISO 8601 timestamp
    "last_used_at": str,            # ISO 8601 timestamp

    # NEW: Source tracking
    "generated_by": str,            # "cognitive_architecture_v1"
    "adapted_from": str,            # Pattern ID if adapted from existing
    "similarity_to_source": float   # Similarity score if adapted
}
```

### Common Queries

#### Semantic search for similar patterns
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Search for auth-related patterns
results = client.search(
    collection_name="devmatrix_patterns",
    query_vector=embedding,  # 768-dim vector
    limit=5,
    score_threshold=0.85,
    query_filter={
        "must": [
            {"key": "category", "match": {"value": "auth"}}
        ]
    }
)
```

#### Filter by framework and complexity
```python
results = client.scroll(
    collection_name="devmatrix_patterns",
    scroll_filter={
        "must": [
            {"key": "framework", "match": {"value": "fastapi"}},
            {"key": "complexity", "range": {"lte": 5}}
        ]
    },
    limit=10
)
```

#### Hybrid search (vector + metadata)
```python
results = client.search(
    collection_name="devmatrix_patterns",
    query_vector=embedding,
    query_filter={
        "must": [
            {"key": "language", "match": {"value": "python"}},
            {"key": "pattern_type", "match": {"value": "function"}}
        ]
    },
    limit=10,
    score_threshold=0.80
)
```

---

## Integration with Cognitive Architecture

### Pattern Reuse Strategy

**Phase 1: Search Existing Patterns**
1. Query `devmatrix_patterns` collection in Qdrant (21K+ patterns)
2. Use semantic embeddings to find similar patterns (≥85% similarity)
3. Filter by framework, language, category as needed
4. Retrieve top 5 candidates

**Phase 2: Adapt or Generate**
- If similarity ≥ 0.85: Adapt existing pattern via Claude reasoning
- If similarity < 0.85: Generate from first principles via CPIE

**Phase 3: Store New Patterns**
- If precision ≥ 95%: Store in `semantic_patterns` collection
- Track usage, success rate, and relationships

### Neo4j DAG Construction

**Use Existing Pattern Relationships**:
1. Query Neo4j for patterns with DEPENDS_ON relationships
2. Analyze dependency chains for similar tasks
3. Leverage existing dependency patterns for DAG construction
4. Add new AtomicTask nodes alongside Pattern nodes

**Coexistence Strategy**:
- **Pattern nodes**: Reference patterns from extraction (read-only)
- **AtomicTask nodes**: New generated tasks (read-write)
- **DEPENDS_ON relationships**: Both pattern→pattern and task→task

---

## Data Quality & Coverage

### Pattern Distribution by Repository

| Repository | Patterns | Percentage |
|------------|----------|------------|
| next.js | 37,426 | 76.2% |
| supabase | 6,509 | 13.2% |
| fastapi | 2,196 | 4.5% |
| prisma | 1,414 | 2.9% |
| flowbite-react | 499 | 1.0% |
| trpc | 440 | 0.9% |
| next-auth | 404 | 0.8% |
| fullstack-next-fastapi | 189 | 0.4% |
| fastapi-nextjs | 54 | 0.1% |

### Pattern Distribution by Type

Most common pattern types (inferred from naming):
- Functions (majority)
- Classes
- React Components
- Hooks
- Middleware
- Models
- Controllers
- Routes

### Language Distribution

- **JavaScript**: ~70% (Next.js dominance)
- **TypeScript**: ~20% (Next.js, Prisma, tRPC)
- **Python**: ~10% (FastAPI, Supabase)

### Framework Coverage

- ✅ Next.js (frontend + fullstack)
- ✅ FastAPI (backend API)
- ✅ React (UI components)
- ✅ Prisma (ORM/database)
- ✅ Supabase (backend services)
- ✅ tRPC (API contracts)
- ❌ Vue, Angular, Django, Flask (not covered)

---

## Recommendations for Cognitive Architecture

### 1. Leverage Existing Patterns Immediately

**High-Value Patterns**:
- FastAPI route patterns (2,196 available)
- Next.js component patterns (37,426 available)
- Auth patterns from Supabase and Next-auth
- Database patterns from Prisma

**Usage**:
- Use as reference for CPIE pattern adaptation
- Bootstrap semantic_patterns collection with best patterns
- Learn dependency patterns from Neo4j relationships

### 2. Extend Schema Gradually

**Phase 1** (Week 1): Read-only access
- Query existing patterns
- No schema modifications
- Learn from existing data

**Phase 2** (Week 2+): Write new patterns
- Add semantic_patterns collection
- Store cognitive-generated patterns
- Track quality metrics

### 3. Metadata Enrichment Opportunities

**Missing Data** (could be added):
- Semantic embeddings in Neo4j (currently only in Qdrant)
- Usage statistics (never tracked yet)
- Success metrics (no validation history)
- User ratings (no human feedback)

**Future Enhancements**:
- Link Neo4j patterns to Qdrant vectors (cross-reference)
- Add performance benchmarks to patterns
- Track pattern evolution over time

### 4. Query Optimization

**Index Creation** (if not exists):
```cypher
// Neo4j indexes
CREATE INDEX pattern_name_idx FOR (p:Pattern) ON (p.name);
CREATE INDEX pattern_framework_idx FOR (p:Pattern) ON (p.framework);
CREATE INDEX pattern_category_idx FOR (p:Pattern) ON (p.category);
```

**Qdrant Optimization**:
- Patterns already indexed (18,755 of 21,624)
- Additional indexing happens automatically
- Consider payload indexes for frequently filtered fields

---

## Python Client Integration

### Neo4j Client Example

```python
from neo4j import GraphDatabase

class Neo4jPatternClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def get_patterns_by_category(self, category: str, limit: int = 10):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Pattern)-[:IN_CATEGORY]->(c:Category {name: $category})
                RETURN p
                LIMIT $limit
            """, category=category, limit=limit)
            return [record["p"] for record in result]

    def get_dependency_chain(self, pattern_name: str):
        with self.driver.session() as session:
            result = session.run("""
                MATCH path=(p1:Pattern {name: $name})-[:DEPENDS_ON*1..3]->(p2:Pattern)
                RETURN path
            """, name=pattern_name)
            return list(result)
```

### Qdrant Client Example

```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

class QdrantPatternClient:
    def __init__(self, host: str, port: int):
        self.client = QdrantClient(host=host, port=port)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

    def search_similar_patterns(
        self,
        query: str,
        framework: str = None,
        limit: int = 5,
        threshold: float = 0.85
    ):
        # Encode query
        query_vector = self.encoder.encode(query).tolist()

        # Build filter
        filter_conditions = {}
        if framework:
            filter_conditions = {
                "must": [
                    {"key": "framework", "match": {"value": framework}}
                ]
            }

        # Search
        results = self.client.search(
            collection_name="devmatrix_patterns",
            query_vector=query_vector,
            query_filter=filter_conditions if filter_conditions else None,
            limit=limit,
            score_threshold=threshold
        )

        return results
```

---

## Next Steps

1. **Create Python clients** (`src/cognitive/infrastructure/`)
   - `neo4j_client.py` (~150 LOC)
   - `qdrant_client.py` (~120 LOC)

2. **Test connectivity** against existing data
   - Query 30K patterns from Neo4j
   - Search 21K patterns from Qdrant
   - Verify schema matches documentation

3. **Document edge cases**
   - Missing fields handling
   - Empty relationships
   - Duplicate patterns

4. **Add environment variables** to `.env`
   ```bash
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=devmatrix
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_COLLECTION_PATTERNS=devmatrix_patterns
   QDRANT_COLLECTION_SEMANTIC=semantic_patterns
   ```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: Production Data - Ready for Integration
**Total Patterns**: 51,695 (30K Neo4j + 21K Qdrant)
