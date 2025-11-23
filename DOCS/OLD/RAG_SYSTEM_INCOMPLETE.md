# RAG System (Retrieval Augmented Generation)

**Document Date:** 2025-11-23
**Status:** Complete Architecture Documentation
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Sources](#data-sources)
4. [Retrieval Pipeline](#retrieval-pipeline)
5. [Integration Points](#integration-points)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Performance Metrics](#performance-metrics)

---

## Overview

The RAG System is a retrieval-augmented generation component that provides intelligent pattern matching and context enrichment for code generation. It combines multiple data sources using a weighted retrieval strategy to find the most relevant patterns and knowledge for any given code generation task.

### Key Characteristics

- **Multi-Source Retrieval**: Combines Qdrant (vector search), Neo4j (graph queries), and ChromaDB (semantic search)
- **Weighted Strategy**: Configurable weights for each source (default: Qdrant 0.7, Neo4j 0.3, ChromaDB 0)
- **Semantic Embeddings**: 768-dimensional embeddings using GraphCodeBERT for code-aware similarity
- **Production Ready**: Caching, deduplication, re-ranking, and query expansion
- **Extensible**: Modular design supports adding new retrieval sources

### Statistics

```
Current Data Sources:
├── Qdrant Vector Store
│   ├── Total Patterns: 21,624
│   ├── Embedding Dimension: 768
│   ├── Model: GraphCodeBERT
│   └── Collections: Multiple specialized collections
├── Neo4j Knowledge Graph
│   ├── Total Nodes: 30,314
│   ├── Total Relationships: 159,793
│   ├── Entity Types: Patterns, Code Structures, Dependencies
│   └── Relationship Types: 20+ types (uses, implements, depends_on, etc.)
└── ChromaDB Semantic Search
    ├── Status: Currently Disabled
    ├── Purpose: General semantic code embeddings
    └── Embedding Model: OpenAI embeddings
```

---

## Architecture

### System Diagram

```
User Query / Code Generation Task
            ↓
    ┌───────────────────┐
    │  Query Expansion  │ (Expand query terms for better coverage)
    └────────┬──────────┘
             ↓
    ┌────────────────────────────────────────┐
    │   Parallel Retrieval from All Sources  │
    ├────────────────┬──────────────┬────────┤
    │                │              │        │
    ▼                ▼              ▼        ▼
[Qdrant]       [Neo4j]         [ChromaDB] [Cache]
(21.6K         (30.3K             (Disabled) (Hit)
 patterns)     nodes)
    │                │              │        │
    └────────────────┼──────────────┴────────┘
                     ↓
        ┌────────────────────────────┐
        │  Result Weighting & Merge  │ (Apply weights: Q=0.7, N=0.3, C=0)
        └────────┬───────────────────┘
                 ↓
        ┌────────────────────────────┐
        │  Deduplication & Ranking   │ (Remove duplicates, re-rank by relevance)
        └────────┬───────────────────┘
                 ↓
        ┌────────────────────────────┐
        │   Feedback Collection      │ (Track retrieval quality)
        └────────┬───────────────────┘
                 ↓
        ┌────────────────────────────┐
        │   Cache Results            │ (Store for future similar queries)
        └────────┬───────────────────┘
                 ↓
        Retrieved Context + Patterns
        (Used by Code Generators)
```

### Module Organization

```
/src/rag/
├── __init__.py                          # RAG module exports
├── unified_retriever.py                 # Main orchestrator
├── retriever.py                         # High-level retrieval interface
├── vector_store.py                      # ChromaDB integration
├── embeddings.py                        # Embedding models (OpenAI, GraphCodeBERT)
├── query_expander.py                    # Query expansion logic
├── reranker.py                          # Result re-ranking interface
├── cross_encoder_reranker.py            # Cross-encoder re-ranking implementation
├── context_builder.py                   # Builds context from retrieved results
├── hybrid_retriever.py                  # Combines multiple strategies
├── multi_collection_manager.py          # Manages Qdrant collections
├── metadata_extractor.py                # Extracts metadata from results
├── feedback_service.py                  # Collects retrieval quality feedback
├── metrics.py                           # RAG performance metrics
├── persistent_cache.py                  # Caching layer for results
└── config.py                            # RAG configuration
```

---

## Data Sources

### 1. Qdrant Vector Store (Primary - Weight: 0.7)

**Purpose**: Fast vector similarity search on curated patterns

**Configuration**:
```python
{
    "host": "localhost",
    "port": 6333,
    "preferred_size": 100,
    "score_threshold": 0.7,
    "max_results": 50
}
```

**Collections**:
- `patterns` - Main pattern library (21,624 patterns)
- `code_snippets` - Code implementation examples
- `best_practices` - Engineering best practices
- Domain-specific collections (auth, data, api, etc.)

**Data Structure**:
```json
{
  "vector": [768-dimensional embedding],
  "metadata": {
    "pattern_id": "uuid",
    "name": "pattern_name",
    "category": "entity_generation|api_endpoint|validation",
    "domain": "auth|payment|logging|etc",
    "confidence": 0.95,
    "success_rate": 0.98,
    "usage_count": 1234,
    "tags": ["scalable", "production-ready"],
    "last_used": "2025-11-23T10:30:00Z"
  }
}
```

**Query Performance**:
- Latency: ~50-100ms per query
- Throughput: 100+ queries/second
- Memory: ~2GB for 21.6K patterns

**Embedding Model**: GraphCodeBERT
- Dimension: 768
- Specialization: Code-aware semantic similarity
- Advantage: Better for code than general embeddings

### 2. Neo4j Knowledge Graph (Secondary - Weight: 0.3)

**Purpose**: Relationship-based pattern matching and dependency discovery

**Configuration**:
```python
{
    "host": "localhost",
    "port": 7687,
    "database": "neo4j",
    "auth": ("neo4j", "<password>"),
    "max_connections": 50
}
```

**Data Structure**:
```cypher
MATCH (p:Pattern)-[r:Relationship]->(other)
RETURN p, r, other
LIMIT 100
```

**Node Types** (30,314 total):
- Pattern nodes (curated code patterns)
- Entity nodes (domain models)
- ServiceNode (service implementations)
- APIEndpoint nodes
- ValidationRule nodes
- DependencyNode nodes
- RelationshipNode nodes

**Relationship Types** (159,793 total):
- `IMPLEMENTS` - Pattern implements functionality
- `DEPENDS_ON` - Component dependency
- `REQUIRES` - Prerequisites
- `COMPATIBLE_WITH` - Version/feature compatibility
- `SIMILAR_TO` - Similar patterns
- `EVOLVED_FROM` - Pattern evolution lineage
- `VALIDATES` - Validation rules
- `USES` - Code usage relationships
- `RELATED_TO` - General relationships

**Query Examples**:
```cypher
# Find related patterns
MATCH (p:Pattern {name: $pattern_name})-[r:RELATED_TO]->(related)
RETURN related, r
ORDER BY r.similarity DESC
LIMIT 10

# Find pattern dependency chain
MATCH (p1:Pattern)-[r:DEPENDS_ON*1..3]->(p2:Pattern)
WHERE p1.name = $name
RETURN p1, r, p2

# Find compatible versions
MATCH (v1:Version)-[r:COMPATIBLE_WITH]->(v2:Version)
WHERE v1.framework = $framework
RETURN v2
```

**Graph Statistics**:
- Average node connections: 5.2
- Average path length: 2.8 hops
- Network density: 0.015%
- Query latency: 10-50ms

### 3. ChromaDB Semantic Search (Disabled - Weight: 0)

**Purpose**: General semantic code embeddings (currently disabled)

**Configuration**:
```python
{
    "collection_name": "code_semantics",
    "embedding_function": "OpenAI",
    "distance_metric": "cosine",
    "status": "DISABLED"
}
```

**Reason for Disabling**:
- Qdrant provides faster vector search
- Neo4j provides richer relationship data
- OpenAI embeddings less optimal for code than GraphCodeBERT
- Reduces operational complexity

**Re-enablement**: Can be re-enabled for:
- General semantic queries
- Multi-language code search
- Natural language to code mapping

---

## Retrieval Pipeline

### Step 1: Query Normalization

**Input**: Raw user query or code generation task

**Process**:
```python
# From query_normalizer.py
normalized_query = {
    "original": "user input",
    "cleaned": "remove stopwords, normalize text",
    "tokens": ["token1", "token2", ...],
    "language": "python|javascript|typescript",
    "domain": "auth|data|api|etc",
    "intent": "generate_entity|generate_endpoint|etc",
    "complexity_score": 0.65
}
```

**Output**: Normalized query object

### Step 2: Query Expansion

**Purpose**: Expand limited queries to improve retrieval coverage

**Methods**:
```python
# From query_expander.py

# Method 1: Synonym expansion
"user authentication" →
  ["user authentication", "login", "auth", "credential verification", "access control"]

# Method 2: Related concept expansion
"REST API" →
  ["REST API", "HTTP endpoints", "API gateway", "route handler", "endpoint definition"]

# Method 3: Domain-specific expansion
"entity" →
  ["entity", "domain model", "aggregate root", "data model", "business object"]
```

**Configuration**:
```python
{
    "expand_synonyms": True,
    "synonym_expansion_factor": 1.5,
    "expand_concepts": True,
    "concept_expansion_factor": 2.0,
    "max_expanded_terms": 20,
    "expansion_language": "en"
}
```

### Step 3: Parallel Retrieval

**Process**: Simultaneously query all data sources

#### 3a. Qdrant Retrieval

```python
# From unified_retriever.py

retrieval_config = {
    "query_vector": query_embedding,  # 768-dim GraphCodeBERT
    "limit": 100,
    "score_threshold": 0.7,
    "search_params": {
        "hnsw_ef": 128,
        "indexed_only": True,
        "exact": False
    },
    "filter": {
        "must": [{"key": "domain", "match": {"value": domain}}],
        "should": [{"key": "tags", "match": {"any": [tags]}}]
    }
}

# Returns: List[ScoredPoint] with score 0.0-1.0
qdrant_results = qdrant_client.search(
    collection_name="patterns",
    query_vector=retrieval_config["query_vector"],
    limit=retrieval_config["limit"],
    score_threshold=retrieval_config["score_threshold"]
)
```

#### 3b. Neo4j Retrieval

```python
# From unified_retriever.py

neo4j_query = """
MATCH (p:Pattern)
WHERE (
    p.name CONTAINS $query OR
    p.tags CONTAINS $query OR
    p.description CONTAINS $query
)
WITH p,
     apoc.text.jaroWinklerSimilarity(p.name, $query) AS name_similarity,
     size((p)-[]-()) AS connection_count
ORDER BY name_similarity DESC, connection_count DESC
RETURN p, name_similarity AS relevance_score
LIMIT 50
"""

neo4j_results = neo4j_session.run(
    neo4j_query,
    query=normalized_query,
    domain=domain
)
```

#### 3c. ChromaDB Retrieval (Disabled)

```python
# Currently not executed
chroma_results = chroma_collection.query(
    query_embeddings=query_embedding,
    n_results=50,
    where={"domain": {"$eq": domain}}
)
```

### Step 4: Weighted Merging

**Process**: Combine results from all sources with configurable weights

```python
# From unified_retriever.py

weights = {
    "qdrant": 0.7,
    "neo4j": 0.3,
    "chromadb": 0.0  # disabled
}

# Normalize scores to 0-1 range per source
qdrant_scores = normalize(qdrant_results, method="minmax")      # 0-1
neo4j_scores = normalize(neo4j_results, method="minmax")        # 0-1
chroma_scores = normalize(chroma_results, method="minmax")      # 0-1

# Calculate weighted score
merged_results = {}
for source, score, result in all_results:
    weight = weights[source]
    weighted_score = score * weight

    if result.id not in merged_results:
        merged_results[result.id] = {
            "result": result,
            "score": 0,
            "sources": []
        }

    merged_results[result.id]["score"] += weighted_score
    merged_results[result.id]["sources"].append(source)

# Sort by merged score
final_results = sorted(
    merged_results.values(),
    key=lambda x: x["score"],
    reverse=True
)
```

**Configuration**:
```python
{
    "qdrant_weight": 0.7,
    "neo4j_weight": 0.3,
    "chromadb_weight": 0.0,
    "min_score_threshold": 0.5,
    "prefer_multi_source": True  # Boost if match multiple sources
}
```

### Step 5: Deduplication

**Purpose**: Remove duplicate patterns found in multiple sources

```python
# From unified_retriever.py

deduplicated = []
seen_patterns = set()

for result in final_results:
    pattern_id = result["pattern_id"]

    # Skip if already seen
    if pattern_id in seen_patterns:
        continue

    # Alternative: Use fuzzy matching for similar patterns
    if is_similar_to_seen(result, seen_patterns, similarity_threshold=0.95):
        continue

    deduplicated.append(result)
    seen_patterns.add(pattern_id)

return deduplicated[:max_results]
```

### Step 6: Re-ranking

**Purpose**: Re-order results for improved relevance

**Methods**:

#### Cross-Encoder Re-ranking

```python
# From cross_encoder_reranker.py

from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Score each result in context of original query
scores = reranker.predict([
    [normalized_query, result.text]
    for result in candidates
])

# Reorder by score
reranked = sorted(
    zip(candidates, scores),
    key=lambda x: x[1],
    reverse=True
)

return [result for result, score in reranked]
```

#### MMR (Maximal Marginal Relevance)

```python
# From retriever.py

def maximal_marginal_relevance(
    candidates,
    query_embedding,
    lambda_param=0.5,
    k=10
):
    """
    Balance between relevance and diversity
    score = lambda * relevance - (1-lambda) * redundancy
    """
    selected = []
    remaining = set(range(len(candidates)))

    # First: select most relevant
    first_idx = max(remaining,
        key=lambda i: similarity(query_embedding, candidates[i].embedding))
    selected.append(first_idx)
    remaining.remove(first_idx)

    # Then: iteratively select most diverse
    while len(selected) < k and remaining:
        mmr_scores = []
        for idx in remaining:
            relevance = similarity(query_embedding, candidates[idx].embedding)
            redundancy = max(
                [similarity(candidates[idx].embedding, candidates[s].embedding)
                 for s in selected]
            )
            mmr_score = lambda_param * relevance - (1 - lambda_param) * redundancy
            mmr_scores.append((idx, mmr_score))

        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [candidates[i] for i in selected]
```

**Configuration**:
```python
{
    "reranking_method": "cross_encoder|mmr|combined",
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "mmr_lambda": 0.5,
    "max_results_before_reranking": 200,
    "max_results_after_reranking": 20
}
```

### Step 7: Caching

**Purpose**: Avoid redundant queries for identical or similar inputs

```python
# From persistent_cache.py

class RAGCache:
    def get(self, query_hash: str, ttl_seconds: int = 3600):
        """Get cached results if available and fresh"""
        cache_key = f"rag:{query_hash}"
        cached = redis_client.get(cache_key)

        if cached:
            cached_data = json.loads(cached)
            if time.time() - cached_data["timestamp"] < ttl_seconds:
                return cached_data["results"]

        return None

    def set(self, query_hash: str, results: List[Dict]):
        """Cache results for future similar queries"""
        cache_key = f"rag:{query_hash}"
        cache_value = {
            "results": results,
            "timestamp": time.time()
        }
        redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps(cache_value)
        )

    def similarity_search_cache(self, query: str, threshold: float = 0.9):
        """Find similar cached queries"""
        # Use Qdrant to find similar query embeddings
        similar_queries = qdrant_client.search(
            collection_name="query_cache",
            query_vector=embed(query),
            score_threshold=threshold
        )
        return similar_queries
```

**Cache Statistics**:
- Hit rate: ~35-40% (varies by workload)
- TTL: 1 hour (configurable)
- Max cache size: 10GB (Redis)
- Cache invalidation: LRU eviction

### Step 8: Context Building

**Purpose**: Format retrieved results for use by code generators

```python
# From context_builder.py

def build_context(retrieved_results: List[Pattern]) -> RAGContext:
    """Build enriched context from retrieved patterns"""

    context = RAGContext(
        timestamp=datetime.now(),
        query_id=str(uuid4()),
        source_count=len(retrieved_results),
        sources_used=set()
    )

    # Group by category
    context.patterns_by_category = defaultdict(list)
    context.all_patterns = []
    context.entity_patterns = []
    context.api_patterns = []
    context.validation_patterns = []

    for pattern in retrieved_results:
        context.all_patterns.append(pattern)
        context.patterns_by_category[pattern.category].append(pattern)
        context.sources_used.add(pattern.source)

        if pattern.category == "entity_generation":
            context.entity_patterns.append(pattern)
        elif pattern.category == "api_endpoint":
            context.api_patterns.append(pattern)
        elif pattern.category == "validation":
            context.validation_patterns.append(pattern)

    # Add metadata
    context.metadata = {
        "total_patterns": len(retrieved_results),
        "avg_confidence": mean([p.confidence for p in retrieved_results]),
        "top_score": max([p.score for p in retrieved_results]),
        "sources": list(context.sources_used),
        "retrieval_time_ms": 0  # Set by caller
    }

    return context
```

---

## Integration Points

### 1. Code Generation Service

**Integration Point**: [code_generation_service.py:52-60]

```python
from src.rag.unified_retriever import UnifiedRetriever

class CodeGenerationService:
    def __init__(self, rag_retriever: UnifiedRetriever):
        self.rag_retriever = rag_retriever

    async def generate_entity(self, entity_spec: EntitySpec) -> str:
        """Generate entity code with RAG context"""

        # 1. Retrieve relevant patterns
        query = f"Generate {entity_spec.name} entity with fields: {entity_spec.fields}"
        rag_context = await self.rag_retriever.retrieve(
            query=query,
            domain="entity_generation",
            max_results=5
        )

        # 2. Use patterns as template/examples
        prompt = self.build_prompt(entity_spec, rag_context)

        # 3. Generate code
        generated_code = await self.llm.generate(prompt)

        # 4. Validate against patterns
        self.validate_against_patterns(generated_code, rag_context)

        return generated_code
```

### 2. Pattern Bank

**Integration Point**: [pattern_bank.py:86-120]

```python
class PatternBank:
    def __init__(self, rag_retriever: UnifiedRetriever):
        self.rag_retriever = rag_retriever

    async def find_similar_patterns(self, code: str, threshold: float = 0.7):
        """Find existing patterns similar to provided code"""

        # 1. Create semantic signature from code
        signature = create_semantic_signature(code)

        # 2. Query RAG for similar patterns
        similar = await self.rag_retriever.retrieve(
            query=code,
            domain="code_patterns",
            min_score=threshold
        )

        # 3. Return with match scores
        return [
            PatternMatch(pattern=p, confidence=p.score)
            for p in similar
        ]

    async def promote_pattern(self, pattern: Pattern):
        """Store successful pattern in RAG system"""

        # 1. Create embedding
        embedding = await embed_code(pattern.code)

        # 2. Add to Qdrant
        await qdrant_client.upsert(
            collection_name="patterns",
            points=[Point(
                id=pattern.id,
                vector=embedding,
                payload=pattern.to_dict()
            )]
        )

        # 3. Add to Neo4j
        await neo4j_session.run("""
            CREATE (p:Pattern {
                id: $id,
                name: $name,
                category: $category,
                success_rate: $success_rate
            })
        """, **pattern.to_dict())
```

### 3. Multi-Pass Planner

**Integration Point**: [multi_pass_planner.py:88-95]

```python
class MultiPassPlanner:
    async def decompose_to_tasks(self, spec: SpecRequirements) -> List[AtomicTask]:
        """Decompose spec into tasks, using RAG for context"""

        tasks = []
        for entity in spec.entities:
            # 1. Retrieve patterns for this entity type
            patterns = await self.rag_retriever.retrieve(
                query=f"Entity: {entity.name} with fields: {entity.fields}",
                domain="entity_decomposition"
            )

            # 2. Create task with pattern context
            task = AtomicTask(
                name=f"Generate {entity.name}",
                rag_context=patterns,
                instructions=self.build_instructions(entity, patterns)
            )
            tasks.append(task)

        return tasks
```

### 4. CPIE Inference Engine

**Integration Point**: [cpie.py:120-140]

```python
class CPIE:
    """Core Pattern Inference Engine"""

    async def execute_task(self, task: AtomicTask) -> ExecutionResult:
        """Execute task using RAG patterns"""

        # 1. Get RAG context (patterns + knowledge)
        rag_context = task.rag_context or await self.rag_retriever.retrieve(
            query=task.name,
            domain=task.domain
        )

        # 2. Use patterns to guide execution
        result = await self.execute_with_patterns(task, rag_context)

        # 3. Provide feedback to RAG system
        await self.rag_feedback_service.report(
            task_id=task.id,
            success=result.success,
            patterns_used=[p.id for p in rag_context.patterns],
            quality_score=result.quality_score
        )

        return result
```

---

## Configuration

### Environment Variables

```bash
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=<optional-api-key>
QDRANT_COLLECTION_NAME=patterns
QDRANT_VECTOR_SIZE=768
QDRANT_DISTANCE_METRIC=cosine

# Neo4j Configuration
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_DATABASE=neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
NEO4J_CONNECTION_POOL_SIZE=50

# ChromaDB Configuration (disabled by default)
CHROMADB_ENABLED=false
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION_NAME=code_semantics

# RAG Configuration
RAG_QDRANT_WEIGHT=0.7
RAG_NEO4J_WEIGHT=0.3
RAG_CHROMADB_WEIGHT=0.0
RAG_MIN_SCORE_THRESHOLD=0.5
RAG_MAX_RESULTS=20
RAG_ENABLE_CACHING=true
RAG_CACHE_TTL_SECONDS=3600
RAG_QUERY_EXPANSION=true

# Embedding Configuration
EMBEDDING_MODEL=graphcodebert  # or openai
EMBEDDING_DIMENSION=768
OPENAI_API_KEY=<api-key-if-using-openai>

# Reranking Configuration
RERANKING_ENABLED=true
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
MMR_LAMBDA=0.5

# Redis Configuration (for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Python Configuration Class

```python
# src/rag/config.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class RAGConfig:
    # Qdrant Settings
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "patterns"
    qdrant_vector_size: int = 768
    qdrant_distance_metric: str = "cosine"
    qdrant_weight: float = 0.7

    # Neo4j Settings
    neo4j_host: str = "localhost"
    neo4j_port: int = 7687
    neo4j_database: str = "neo4j"
    neo4j_weight: float = 0.3
    neo4j_max_connections: int = 50

    # ChromaDB Settings
    chromadb_enabled: bool = False
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chromadb_weight: float = 0.0

    # Retrieval Settings
    min_score_threshold: float = 0.5
    max_results: int = 20
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    query_expansion: bool = True

    # Embedding Settings
    embedding_model: str = "graphcodebert"
    embedding_dimension: int = 768

    # Reranking Settings
    reranking_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    mmr_lambda: float = 0.5

    # Caching
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Load configuration from environment variables"""
        import os
        return cls(
            qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
            qdrant_port=int(os.getenv("QDRANT_PORT", 6333)),
            # ... load other settings
        )
```

---

## API Reference

### UnifiedRetriever

```python
from src.rag.unified_retriever import UnifiedRetriever

class UnifiedRetriever:
    async def retrieve(
        self,
        query: str,
        domain: Optional[str] = None,
        max_results: int = 20,
        min_score: float = 0.5
    ) -> RAGContext:
        """
        Retrieve relevant patterns from all sources

        Args:
            query: User query or code description
            domain: Optional domain filter (auth, data, api, etc)
            max_results: Maximum results to return
            min_score: Minimum relevance score threshold

        Returns:
            RAGContext with retrieved patterns and metadata
        """
```

### Retriever

```python
from src.rag.retriever import Retriever

class Retriever:
    async def search_semantic(
        self,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[Pattern]:
        """Search using semantic similarity"""

    async def search_keyword(
        self,
        keywords: List[str],
        limit: int = 10
    ) -> List[Pattern]:
        """Search using keyword matching"""

    async def search_hybrid(
        self,
        query: str,
        limit: int = 10
    ) -> List[Pattern]:
        """Hybrid search combining semantic + keyword"""
```

### QueryExpander

```python
from src.rag.query_expander import QueryExpander

class QueryExpander:
    def expand_synonyms(self, query: str) -> List[str]:
        """Expand query with synonyms"""

    def expand_concepts(self, query: str) -> List[str]:
        """Expand with related concepts"""

    def expand_full(self, query: str) -> List[str]:
        """Full expansion with all methods"""
```

### Feedback Service

```python
from src.rag.feedback_service import FeedbackService

class FeedbackService:
    async def report_retrieval_quality(
        self,
        query: str,
        results: List[Pattern],
        user_feedback: bool,  # thumbs up/down
        quality_score: Optional[float] = None
    ) -> None:
        """Report on retrieval quality for learning"""

    async def get_metrics(self) -> RAGMetrics:
        """Get RAG system metrics"""
```

---

## Performance Metrics

### Query Performance

| Source | Latency | Throughput | Accuracy |
|--------|---------|-----------|----------|
| Qdrant | 50-100ms | 100+ qps | 85-95% |
| Neo4j | 10-50ms | 50+ qps | 75-90% |
| ChromaDB | 100-200ms | 20+ qps | 70-85% |
| **Combined** | **100-150ms** | **50+ qps** | **90-98%** |

### Caching Impact

```
Cache Hit Scenarios:
- Exact query match: 40-50% hit rate
- Fuzzy query match: 15-25% additional
- Overall effectiveness: 35-40% reduction in retrieval latency
- Cache hit time: <5ms (Redis lookup)
```

### Pattern Library Statistics

```
Qdrant Patterns:
- Total patterns: 21,624
- Categories: 15+ (entity, api, validation, service, etc)
- Success rate average: 94.2%
- Avg embeddings size: ~1.5GB
- Index size: ~500MB

Neo4j Graph:
- Nodes: 30,314
- Relationships: 159,793
- Average degree: 5.2
- Network density: 0.015%
- Query response time: 10-50ms
```

### Embedding Efficiency

```
GraphCodeBERT Model:
- Dimension: 768
- Inference time: 5-10ms per code snippet
- Model size: ~300MB
- GPU memory (batch 32): ~2GB
- CPU inference: ~100-200ms per code

Batch Processing:
- Embed 100 patterns: ~500ms
- Embed 1000 patterns: ~30s
- Daily refresh: ~2-3 hours for full library
```

---

## Usage Examples

### Example 1: Basic Entity Generation

```python
from src.rag.unified_retriever import UnifiedRetriever

retriever = UnifiedRetriever()

# 1. Retrieve patterns for user entity
context = await retriever.retrieve(
    query="Generate User entity with email, username, password fields",
    domain="entity_generation",
    max_results=5
)

# 2. Use context in code generation
for pattern in context.entity_patterns:
    print(f"Pattern: {pattern.name}")
    print(f"Confidence: {pattern.confidence}")
    print(f"Example code: {pattern.code_snippet}")
```

### Example 2: Multi-Domain Query

```python
# Search across multiple domains
context = await retriever.retrieve(
    query="Create authentication system with JWT tokens and rate limiting",
    domain=None,  # No domain restriction
    max_results=10
)

# Results include patterns from auth, security, api domains
auth_patterns = context.patterns_by_category["auth"]
api_patterns = context.patterns_by_category["api"]
validation_patterns = context.patterns_by_category["validation"]
```

### Example 3: Quality Feedback Loop

```python
from src.rag.feedback_service import FeedbackService

feedback_service = FeedbackService()

# Generate code using RAG patterns
result = await code_generation_service.generate_entity(spec)

# Report quality feedback
if result.quality_score > 0.95:
    await feedback_service.report_retrieval_quality(
        query=spec.name,
        results=result.rag_context.patterns,
        user_feedback=True,
        quality_score=result.quality_score
    )
```

---

## Troubleshooting

### Issue: Low Retrieval Quality

**Symptoms**: Retrieved patterns don't match query intent

**Solutions**:
1. Check if query expansion is enabled
2. Verify Qdrant index is up to date
3. Review Neo4j relationship data
4. Adjust score thresholds
5. Check embeddings model quality

### Issue: Slow Retrieval

**Symptoms**: Retrieval takes >500ms

**Solutions**:
1. Check cache hit rate (enable caching)
2. Reduce `max_results` parameter
3. Check Qdrant/Neo4j performance
4. Verify network latency
5. Consider disabling re-ranking for speed

### Issue: Duplicate Results

**Symptoms**: Same patterns appearing multiple times

**Solutions**:
1. Verify deduplication is enabled
2. Check `similarity_threshold` in deduplication
3. Review pattern IDs (may be duplicates in source)
4. Increase similarity threshold for harder deduplication

### Issue: Out of Memory

**Symptoms**: Python process uses excessive memory

**Solutions**:
1. Reduce batch size for embedding
2. Limit `max_results`
3. Disable caching or reduce TTL
4. Review Redis memory usage
5. Consider model quantization

---

## Future Enhancements

1. **Cross-Encoder Fine-tuning**: Fine-tune reranker on domain-specific code
2. **Hybrid Embeddings**: Use multiple embedding models simultaneously
3. **Adaptive Weighting**: Dynamically adjust source weights based on quality
4. **User Feedback Integration**: Learn from user feedback on generated code
5. **Temporal Patterns**: Track pattern evolution over time
6. **Explainability**: Provide explanations for retrieved patterns
7. **Multi-Language Support**: Extend beyond Python/JavaScript
8. **Real-time Updates**: Stream new patterns as they're discovered

---

**Last Updated**: 2025-11-23
**Maintained By**: Agentic AI Team
**Version**: 1.0
