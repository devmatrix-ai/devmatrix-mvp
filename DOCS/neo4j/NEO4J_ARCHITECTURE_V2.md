# Neo4j 5.26 Architecture for DevMatrix V2.1 Hybrid System

**Version**: 2.1
**Date**: November 12, 2025
**Status**: ARCHITECTURE APPROVED - Ready for Implementation
**Database**: Neo4j Community Edition 5.26

---

## 📋 Executive Summary

DevMatrix V2.1 uses a **hybrid architecture** combining:
- **PostgreSQL**: Relational data (masterplans, tasks, atoms, users)
- **Redis**: Temporal state and caching
- **ChromaDB**: RAG embeddings for semantic code search
- **Neo4j**: Knowledge graph for templates, components, patterns, and their relationships

This document defines the complete Neo4j graph model, indexing strategy, query patterns, and integration architecture.

---

## 🎯 Core Goals

1. **Template Registry**: Store 30 backend templates with metadata
2. **Component Knowledge Graph**: 380+ Trezo UI components + custom components
3. **Relationship Tracking**: Dependencies, patterns, frameworks, similarities
4. **Fast Search**: Category + features + precision queries
5. **Recommendations**: Find similar templates, suggest alternatives
6. **Audit Trail**: Track which templates generated which atoms/masterplans
7. **Performance**: Sub-second queries, support 10K+ templates

---

## 🏗️ Graph Schema - Complete Model

### Node Types (11 Total)

#### 1. **Template** - Backend code patterns
```cypher
(:Template {
  id: STRING UNIQUE,                    # "jwt_auth_v1"
  name: STRING,                         # "JWT Authentication Service"
  category: STRING,                     # "auth", "api", "ddd", "data"
  subcategory: STRING,                  # "authentication", "token_management"
  framework: STRING,                    # "fastapi", "django"
  language: STRING,                     # "python"
  precision: FLOAT,                     # 0.0 to 1.0 (how well it solves problem)
  code: TEXT,                           # Actual template code
  description: TEXT,                    # Long description
  complexity: STRING,                   # "simple", "medium", "complex"
  version: INTEGER,                     # 1, 2, 3...
  status: STRING,                       # "active", "deprecated", "beta"
  created_at: DATETIME,
  updated_at: DATETIME,
  source: STRING                        # "internal", "community", "generated"
})
```

#### 2. **TrezoComponent** - Pre-built UI components
```cypher
(:TrezoComponent {
  id: STRING UNIQUE,                    # "datatable_v1_trezo"
  name: STRING,                         # "DataTable"
  category: STRING,                     # "table", "form", "modal", "chart"
  features: LIST<STRING>,               # ["sorting", "filtering", "pagination"]
  framework: STRING,                    # "react", "vue", "angular"
  precision: FLOAT,                     # 0.95 to 1.0 (Trezo is high quality)
  code: TEXT,                           # TSX/JSX code
  dependencies: LIST<STRING>,           # ["@mui/data-grid", "react"]
  accessibility: STRING,                # "wcag2a", "wcag2aa"
  responsive: BOOLEAN,                  # true/false
  created_at: DATETIME,
  source: STRING                        # "trezo"
})
```

#### 3. **CustomComponent** - Generated UI components
```cypher
(:CustomComponent {
  id: STRING UNIQUE,
  name: STRING,
  category: STRING,
  framework: STRING,
  code: TEXT,
  precision: FLOAT,                     # 0.7 to 0.95 (LLM generated)
  created_from_template_id: STRING,     # Reference to Template
  generated_at: DATETIME,
  status: STRING                        # "draft", "review", "approved"
})
```

#### 4. **Pattern** - Design patterns
```cypher
(:Pattern {
  id: STRING UNIQUE,                    # "ddd", "crud", "repository"
  name: STRING,                         # "Domain-Driven Design"
  description: TEXT,
  category: STRING,                     # "architectural", "behavioral"
  complexity_level: INTEGER,            # 1-5
  use_cases: LIST<STRING>,
  created_at: DATETIME
})
```

#### 5. **Framework** - Technology frameworks
```cypher
(:Framework {
  id: STRING UNIQUE,                    # "fastapi", "react"
  name: STRING,
  type: STRING,                         # "backend", "frontend"
  language: STRING,                     # "python", "typescript"
  version_range: STRING,                # ">=0.95.0,<2.0"
  ecosystem: LIST<STRING>,              # Package managers
  created_at: DATETIME
})
```

#### 6. **Dependency** - External packages
```cypher
(:Dependency {
  id: STRING UNIQUE,                    # "pyjwt", "react-table"
  name: STRING,
  language: STRING,                     # "python", "javascript"
  version_range: STRING,                # "2.0.0" or ">=2.0,<3.0"
  type: STRING,                         # "runtime", "dev", "optional"
  security_status: STRING,              # "secure", "vulnerable", "deprecated"
  created_at: DATETIME
})
```

#### 7. **Category** - Classification taxonomy
```cypher
(:Category {
  id: STRING UNIQUE,                    # "auth", "api", "data"
  name: STRING,
  icon: STRING,                         # emoji or icon name
  parent: STRING,                       # For hierarchical organization
  description: TEXT,
  order: INTEGER                        # Display order
})
```

#### 8. **MasterPlan** - MGE V2 masterplans (synced from PostgreSQL)
```cypher
(:MasterPlan {
  id: STRING UNIQUE,
  title: STRING,
  user_id: STRING,
  status: STRING,                       # "draft", "executing", "completed"
  phases: INTEGER,
  tasks_count: INTEGER,
  precision_score: FLOAT,
  created_at: DATETIME,
  updated_at: DATETIME
})
```

#### 9. **Atom** - MGE V2 atoms (synced from PostgreSQL)
```cypher
(:Atom {
  id: STRING UNIQUE,
  masterplan_id: STRING,
  name: STRING,
  type: STRING,                         # "code", "component", "config"
  content: TEXT,
  status: STRING,
  generated_from_template_id: STRING,   # Tracking
  precision: FLOAT,
  created_at: DATETIME
})
```

#### 10. **User** - Users in the system
```cypher
(:User {
  id: STRING UNIQUE,
  username: STRING,
  email: STRING,
  role: STRING,                         # "admin", "user", "viewer"
  created_at: DATETIME,
  profile_data: MAP
})
```

#### 11. **Project** - Projects/applications
```cypher
(:Project {
  id: STRING UNIQUE,
  name: STRING,
  user_id: STRING,
  framework: STRING,
  description: TEXT,
  created_at: DATETIME,
  updated_at: DATETIME
})
```

---

### Relationship Types (15 Total)

| Relationship | From | To | Properties | Purpose |
|---|---|---|---|---|
| `REQUIRES` | Template | Dependency | `optional: BOOLEAN` | List dependencies |
| `IMPLEMENTS` | Template | Pattern | `completeness: FLOAT` | Which pattern |
| `USES` | Template | Framework | `version: STRING` | Framework requirement |
| `SIMILAR_TO` | Template | Template | `similarity_score: FLOAT` | Recommendation |
| `BELONGS_TO` | Template | Category | `primary: BOOLEAN` | Categorization |
| `EXTENDS` | Component | Component | `override_count: INTEGER` | Inheritance |
| `COMPOSED_OF` | Component | Component | `position: INTEGER` | Composition |
| `GENERATED_FROM` | Atom | Template | `confidence: FLOAT` | Track generation |
| `PART_OF` | Atom | MasterPlan | none | Organization |
| `CREATED_BY` | Template | User | `version: INTEGER` | Authorship |
| `USED_IN` | Template | Project | `usage_count: INTEGER` | Usage tracking |
| `HAS_VARIANT` | Template | Template | `variant_type: STRING` | Alternatives |
| `REPLACED_BY` | Template | Template | `reason: STRING` | Deprecation |
| `DEPENDS_ON` | Template | Template | `order: INTEGER` | Inter-dependencies |
| `RECOMMENDS` | Template | Template | `score: FLOAT` | Suggestions |

---

## 🔍 Indexing & Constraints Strategy

### Uniqueness Constraints (Critical for Data Integrity)
```cypher
-- Node IDs must be unique
CREATE CONSTRAINT template_id_unique IF NOT EXISTS
FOR (t:Template) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT trezo_component_id_unique IF NOT EXISTS
FOR (c:TrezoComponent) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT custom_component_id_unique IF NOT EXISTS
FOR (c:CustomComponent) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS
FOR (p:Pattern) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT framework_id_unique IF NOT EXISTS
FOR (f:Framework) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT dependency_id_unique IF NOT EXISTS
FOR (d:Dependency) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT category_id_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT masterplan_id_unique IF NOT EXISTS
FOR (m:MasterPlan) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT atom_id_unique IF NOT EXISTS
FOR (a:Atom) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;
```

### Range Indexes (Query Performance)
```cypher
-- Frequently filtered properties
CREATE INDEX template_precision IF NOT EXISTS
FOR (t:Template) ON (t.precision);

CREATE INDEX template_created_at IF NOT EXISTS
FOR (t:Template) ON (t.created_at);

CREATE INDEX template_category IF NOT EXISTS
FOR (t:Template) ON (t.category);

CREATE INDEX template_framework IF NOT EXISTS
FOR (t:Template) ON (t.framework);

CREATE INDEX template_status IF NOT EXISTS
FOR (t:Template) ON (t.status);

CREATE INDEX trezo_component_precision IF NOT EXISTS
FOR (c:TrezoComponent) ON (c.precision);

CREATE INDEX atom_precision IF NOT EXISTS
FOR (a:Atom) ON (a.precision);

CREATE INDEX atom_status IF NOT EXISTS
FOR (a:Atom) ON (a.status);
```

### Composite Indexes (Multi-Property Queries)
```cypher
-- Frequently used together
CREATE INDEX template_category_framework IF NOT EXISTS
FOR (t:Template) ON (t.category, t.framework);

CREATE INDEX template_category_precision IF NOT EXISTS
FOR (t:Template) ON (t.category, t.precision);

CREATE INDEX template_framework_status IF NOT EXISTS
FOR (t:Template) ON (t.framework, t.status);

CREATE INDEX trezo_component_category_features IF NOT EXISTS
FOR (c:TrezoComponent) ON (c.category);
-- Note: Features is LIST, use APOC for fuzzy matching

CREATE INDEX atom_masterplan_status IF NOT EXISTS
FOR (a:Atom) ON (a.masterplan_id, a.status);
```

### Full-Text Search Indexes (Text Search)
```cypher
-- For semantic search over text fields
CREATE FULLTEXT INDEX template_name_description IF NOT EXISTS
FOR (t:Template) ON EACH [t.name, t.description];

CREATE FULLTEXT INDEX trezo_component_name_description IF NOT EXISTS
FOR (c:TrezoComponent) ON EACH [c.name];

CREATE FULLTEXT INDEX pattern_name_description IF NOT EXISTS
FOR (p:Pattern) ON EACH [p.name, p.description];
```

### Vector Indexes (Similarity Search - if using embeddings)
```cypher
-- For cosine similarity on embeddings
-- Requires Neo4j 5.11+ with vector index support
-- CREATE VECTOR INDEX template_embedding IF NOT EXISTS
-- FOR (t:Template) ON (t.embedding)
-- OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_metric`: 'cosine'}}

-- Note: Will implement once embedding model is selected
```

---

## 🗄️ Database Organization

**Decision**: Single database with label-based organization

**Rationale**:
- ✅ Supports cross-domain queries (Template → MasterPlan)
- ✅ Better performance for related data
- ✅ Simpler operational management
- ✅ Neo4j routing works seamlessly

**Database Name**: `devmatrix`

**Label Strategy**:
```
All data in single database:
  - Use labels for type distinction
  - Use properties for additional filtering
  - Leverage label + property combos for efficiency
```

---

## 🔄 Integration Architecture

### Data Flow Between Systems

```
┌─────────────────────────────────────────────────────────────────┐
│                      DevMatrix V2.1 Hybrid                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   PostgreSQL     │  │      Redis       │  │     ChromaDB     │
│                  │  │                  │  │                  │
│ - masterplans    │  │ - Session state  │  │ - Code embeddings│
│ - atoms          │  │ - Query cache    │  │ - Semantic search│
│ - tasks          │  │ - Temp results   │  │ - RAG vectors    │
│ - users          │  │                  │  │                  │
│ - projects       │  │                  │  │                  │
└────────┬─────────┘  └──────────────────┘  └──────────────────┘
         │
         │ Sync (batch nightly)
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Neo4j (5.26)                             │
│                                                                  │
│ • Templates (30)          • Relationships (15 types)             │
│ • TrezoComponents (380+)   • Similarity scoring                  │
│ • Patterns                 • Full-text search                    │
│ • Frameworks               • Vector similarity (optional)        │
│ • Dependencies             • APOC procedures                     │
│ • Categories               • Graph algorithms (GDS)              │
│ • MasterPlans (sync)                                             │
│ • Atoms (sync)                                                   │
│ • Users (sync)                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Sync Strategy

#### PostgreSQL → Neo4j (Nightly Batch)
```python
# Sync masterplans, atoms, users
- Query PostgreSQL for changes since last sync
- Upsert into Neo4j using MERGE with timestamps
- Create relationships based on tracking columns
- Update search indexes
```

#### Neo4j → Redis (Real-time Cache)
```python
# Cache hot queries
- Template searches by category+framework
- Component recommendations
- Similar template queries
- TTL: 24 hours for data, 1 hour for user-specific
```

#### ChromaDB Integration
```python
# One-way: Neo4j → ChromaDB (for enhanced search)
- Extract code from templates
- Generate embeddings via ChromaDB
- Store embedding IDs in Neo4j
- Use for fuzzy/semantic matching
```

---

## 📊 Sample Cypher Queries (Production-Ready)

### 1. Find Templates by Category + Framework
```cypher
MATCH (t:Template)
WHERE t.category = $category
  AND t.framework = $framework
  AND t.status = 'active'
RETURN t
ORDER BY t.precision DESC
LIMIT $limit;
```

### 2. Get Template with All Dependencies
```cypher
MATCH (t:Template {id: $template_id})
OPTIONAL MATCH (t)-[r:REQUIRES]->(d:Dependency)
OPTIONAL MATCH (t)-[r2:IMPLEMENTS]->(p:Pattern)
OPTIONAL MATCH (t)-[r3:USES]->(f:Framework)
RETURN t, collect({dep: d, optional: r.optional}) as dependencies,
       collect(p) as patterns, collect(f) as frameworks;
```

### 3. Find Similar Templates (Recommendation)
```cypher
MATCH (t:Template {id: $template_id})
MATCH (t)-[sim:SIMILAR_TO]->(similar)
WHERE similar.status = 'active'
RETURN similar, sim.similarity_score
ORDER BY sim.similarity_score DESC
LIMIT $limit;
```

### 4. Search Templates by Text
```cypher
CALL db.index.fulltext.queryNodes('template_name_description', $search_text)
YIELD node as t, score
WHERE t.status = 'active'
RETURN t, score
ORDER BY score DESC
LIMIT $limit;
```

### 5. Get Trezo Components by Features
```cypher
MATCH (c:TrezoComponent)
WHERE c.category = $category
  AND c.precision >= 0.85
  // Note: Features LIST matching requires APOC
RETURN c
ORDER BY c.precision DESC
LIMIT $limit;
```

### 6. Track Template Usage in Masterplans
```cypher
MATCH (t:Template {id: $template_id})
<-[gen:GENERATED_FROM]-(a:Atom)
-[part:PART_OF]->(mp:MasterPlan)
RETURN mp, a, gen.confidence
ORDER BY a.created_at DESC;
```

### 7. Find Templates for Atom Generation
```cypher
MATCH (c:Category {id: $category_id})
<-[bt:BELONGS_TO]-(t:Template)
WHERE t.status = 'active'
  AND t.precision >= 0.85
OPTIONAL MATCH (t)-[req:REQUIRES]->(d:Dependency)
RETURN t, collect({dep: d, optional: req.optional}) as dependencies
ORDER BY t.precision DESC
LIMIT $limit;
```

### 8. Recommend Alternative Templates
```cypher
MATCH (t:Template {id: $template_id})
-[r1:SIMILAR_TO|RECOMMENDS]->(rec:Template)
WHERE rec.status = 'active'
OPTIONAL MATCH (rec)-[req:REQUIRES]->(d:Dependency)
RETURN rec, r1.score as score,
       collect(d.name) as dependencies
ORDER BY score DESC
LIMIT 5;
```

### 9. Calculate Template Precision Average by Category
```cypher
MATCH (c:Category)<-[bt:BELONGS_TO]-(t:Template)
WHERE t.status = 'active'
RETURN c.name, avg(t.precision) as avg_precision, count(t) as template_count
ORDER BY avg_precision DESC;
```

### 10. Find Dependencies with Security Issues
```cypher
MATCH (t:Template)-[req:REQUIRES]->(d:Dependency)
WHERE d.security_status = 'vulnerable'
RETURN t.name, d.name, d.security_status;
```

### 11. List All Frameworks and Their Templates
```cypher
MATCH (f:Framework)<-[uses:USES]-(t:Template)
WHERE t.status = 'active'
RETURN f.name, collect(t.name) as templates, count(t) as count
ORDER BY count DESC;
```

### 12. Get Complete Template Information
```cypher
MATCH (t:Template {id: $template_id})
OPTIONAL MATCH (t)-[:BELONGS_TO]->(cat:Category)
OPTIONAL MATCH (t)-[:USES]->(f:Framework)
OPTIONAL MATCH (t)-[:REQUIRES]->(dep:Dependency)
OPTIONAL MATCH (t)-[:IMPLEMENTS]->(p:Pattern)
OPTIONAL MATCH (t)-[:CREATED_BY]->(u:User)
RETURN {
  template: t,
  category: cat,
  framework: f,
  dependencies: collect(DISTINCT dep),
  patterns: collect(DISTINCT p),
  creator: u
} as full_template;
```

### 13. Find Templates Used in Active Projects
```cypher
MATCH (proj:Project)<-[used:USED_IN]-(t:Template)
-[gen:GENERATED_FROM]-(a:Atom)
-[part:PART_OF]->(mp:MasterPlan)
WHERE mp.status IN ['executing', 'planning']
RETURN DISTINCT t, proj, count(a) as atoms_generated
ORDER BY atoms_generated DESC;
```

### 14. Batch Create Relationships
```cypher
UNWIND $relationships as rel
MATCH (source) WHERE id(source) = rel.source_id
MATCH (target) WHERE id(target) = rel.target_id
CREATE (source)-[r:SIMILAR_TO {similarity_score: rel.score}]->(target)
RETURN count(r) as relationships_created;
```

### 15. Get Templates Needing Review
```cypher
MATCH (t:Template)
WHERE t.status IN ['beta', 'deprecated']
  OR NOT EXISTS((t)-[:CREATED_BY]->())
  OR NOT EXISTS((t)-[:BELONGS_TO]->())
RETURN t.id, t.name, t.status, 'Missing info' as issue
ORDER BY t.created_at;
```

---

## 🚀 Implementation Roadmap

### Phase 1: Schema Setup (Week 1)
1. Run all constraint creation queries
2. Create range indexes
3. Create composite indexes
4. Create full-text indexes
5. Verify schema integrity

### Phase 2: Template Ingestion (Week 1-2)
1. Define 30 backend templates
2. Ingest into Neo4j via Neo4jClient
3. Create BELONGS_TO relationships
4. Create REQUIRES relationships
5. Validate all 30 templates exist

### Phase 3: Advanced Features (Week 2-3)
1. Trezo components ingestion (380+)
2. Similarity scoring (vector or cosine)
3. Full-text search integration
4. APOC procedures for complex queries

### Phase 4: Integration (Week 3)
1. PostgreSQL sync scripts
2. Redis caching layer
3. Query optimization
4. Performance testing

### Phase 5: Monitoring (Ongoing)
1. Query performance metrics
2. Index utilization
3. Relationship distribution
4. Cache hit rates

---

## 📈 Performance Targets

| Query | Target | Index Strategy |
|-------|--------|-----------------|
| Find templates by category | <10ms | Range index on category |
| Find template with deps | <50ms | Composite index + traversal |
| Full-text search | <100ms | Full-text index |
| Similarity search | <200ms | Vector index (if used) |
| Batch operations (1K) | <5s | UNWIND + bulk writes |

---

## 🔐 Data Integrity & Consistency

### Constraints Enforced
- ✅ All node IDs are UNIQUE
- ✅ Relationships only between valid node types
- ✅ Required properties are NOT NULL
- ✅ Precision values 0.0-1.0

### Audit Trail
- ✅ All nodes have `created_at` timestamp
- ✅ Modified nodes have `updated_at` timestamp
- ✅ GENERATED_FROM relationships track template usage
- ✅ CREATED_BY relationships track authorship

### Data Validation
- ✅ Precision must be between 0.0 and 1.0
- ✅ Status must be in allowed enum
- ✅ Category must exist for BELONGS_TO
- ✅ Framework must exist for USES

---

## 🛠️ Operations & Maintenance

### Backup Strategy
```bash
# Full backup (daily)
neo4j-admin database backup --to-path=/backups devmatrix

# Incremental (hourly)
# Configure in neo4j.conf
```

### Monitoring Queries
```cypher
-- Check index usage
SHOW INDEXES;

-- Check constraints
SHOW CONSTRAINTS;

-- Database statistics
CALL apoc.meta.stats();

-- Largest nodes
MATCH (n) RETURN labels(n) as label, count(*) as count
ORDER BY count DESC;
```

### Maintenance
```cypher
-- Rebuild indexes (after large data load)
REINDEX DATABASE devmatrix;

-- Verify database consistency
CALL apoc.util.validatePredicate(true, 'Consistency check passed');
```

---

## 📚 Dependencies & Prerequisites

### Required
- Neo4j 5.26 Community Edition
- APOC Core (bundled)
- Python 3.10+ with neo4j driver

### Optional
- APOC Extended (for advanced procedures)
- GDS (Graph Data Science) for algorithms
- Bloom (visual graph exploration)

---

## ✅ Validation Checklist

Before going live:

- [ ] All 11 node types exist in database
- [ ] All 15 relationship types defined
- [ ] All uniqueness constraints created
- [ ] All range indexes created
- [ ] All composite indexes created
- [ ] All full-text indexes created
- [ ] 30 templates fully ingested
- [ ] 380+ Trezo components ingested
- [ ] All relationships created correctly
- [ ] Sample queries all pass
- [ ] Performance targets met
- [ ] Sync from PostgreSQL working
- [ ] Cache invalidation working
- [ ] Backup strategy tested

---

## 🔗 Related Documents

- [Neo4jClient Implementation](../../src/neo4j_client.py)
- [Backend Templates Definition](./BACKEND_TEMPLATES.md) - To be created
- [Trezo Components Ingestion](./TREZO_INGESTION.md) - To be created
- [Query Performance Tuning](./QUERY_OPTIMIZATION.md) - To be created

---

**Document Status**: ✅ APPROVED FOR IMPLEMENTATION
**Next Step**: Create `init_neo4j_schema.py` script to deploy this architecture
