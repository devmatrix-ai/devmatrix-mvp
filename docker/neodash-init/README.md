# NeoDash Initialization

Pre-configured dashboards and setup instructions for NeoDash graph visualization.

## Quick Start

1. **NeoDash auto-configures** on first run at http://localhost:5005
2. **Connection is automatic** - connects to bolt://neo4j:7687
3. **No authentication needed** - credentials from environment

## Creating Your First Dashboard

### Dashboard 1: Pattern Overview
```cypher
// Nodes overview
MATCH (n)
RETURN count(n) AS node_count,
       labels(n)[0] AS node_type

// Relationships overview
MATCH (n)-[r]->(m)
RETURN type(r) AS relationship_type, count(r) AS count
```

### Dashboard 2: Pattern Network
```cypher
// Top connected patterns
MATCH (p:Pattern)-[r:CONNECTS_TO]->(target)
WITH p, count(r) AS connection_count
ORDER BY connection_count DESC
LIMIT 20
RETURN p.name AS pattern, connection_count
```

### Dashboard 3: Pattern Dependencies
```cypher
// Pattern dependency graph
MATCH path = (p1:Pattern)-[*1..3]->(p2:Pattern)
WHERE p1 <> p2
RETURN p1, relationships(path), p2
LIMIT 50
```

## NeoDash Features

### Visualization Types
- **Graph Visualization**: Node-edge network visualization
- **Table**: Structured data display
- **Bar Chart**: Category comparisons
- **Pie Chart**: Distribution analysis
- **Line Chart**: Trend analysis
- **Map**: Geographic data (if lat/long available)

### Dashboard Components

1. **Parameter input** - Filter query parameters
2. **Query editor** - Write/modify Cypher queries
3. **Visualization selector** - Choose display format
4. **Export/Share** - Save dashboards as JSON

## Import/Export Dashboards

### Export Dashboard
1. Open dashboard
2. Click "Save Dashboard" (💾)
3. Dashboard saves locally

### Export as JSON
```bash
# Access NeoDash API
curl http://localhost:5005/api/dashboards
```

### Import Saved Dashboard
1. Click "Load Dashboard"
2. Select saved JSON file
3. Dashboard configures automatically

## Advanced Queries for Dashboards

### Query Pattern Relationships
```cypher
MATCH (p1:Pattern)-[:DEPENDS_ON]->(p2:Pattern)
RETURN p1.name AS from_pattern,
       p2.name AS to_pattern,
       count(*) AS dependency_count
ORDER BY dependency_count DESC
```

### Find Pattern Clusters
```cypher
MATCH (p:Pattern)
WITH p, size((p)-[]->()) AS outbound,
          size((p)<-[]-()) AS inbound
RETURN p.name,
       labels(p) AS types,
       outbound + inbound AS total_connections
ORDER BY total_connections DESC
LIMIT 30
```

### Trace Pattern Lineage
```cypher
MATCH (origin:Pattern {name: 'InitialPattern'})
MATCH path = (origin)-[:EVOLVES_TO*1..5]->(descendant:Pattern)
RETURN [p in nodes(path) | p.name] AS lineage
```

### Performance Metrics
```cypher
MATCH (p:Pattern)
RETURN p.name AS pattern,
       p.success_rate AS success,
       p.avg_execution_time AS execution_time,
       p.usage_count AS times_used
ORDER BY usage_count DESC
```

## Best Practices

### Dashboard Organization
1. **Overview Dashboard**: High-level statistics
2. **Pattern Navigator**: Interactive pattern explorer
3. **Dependency Graph**: Understand relationships
4. **Performance Monitor**: Track efficiency metrics

### Query Optimization
- Use `LIMIT` for large result sets
- Index frequently queried properties
- Use `EXPLAIN` to analyze query plans

### Naming Conventions
- Use descriptive dashboard names
- Include query purpose in notes
- Document parameter meanings

## Common Cypher Patterns

### Find All Patterns of Type
```cypher
MATCH (p:Pattern:SpecificType)
RETURN p
LIMIT 100
```

### Count Nodes by Type
```cypher
CALL db.nodeTypeStats()
YIELD nodeType, nodeCount
RETURN nodeType, nodeCount
ORDER BY nodeCount DESC
```

### List All Relationships
```cypher
CALL db.relationshipTypes()
YIELD relationshipType
RETURN relationshipType
```

### Find Circular Dependencies
```cypher
MATCH (p:Pattern)-[*2..]->(p)
RETURN p.name AS circular_pattern,
       length(p) AS cycle_length
```

## Accessing NeoDash

### Web Interface
```
URL: http://localhost:5005
Auto-connected to: bolt://neo4j:7687
User: neo4j (from .env)
```

### Keyboard Shortcuts
- `⌘+S` / `Ctrl+S`: Save dashboard
- `⌘+K` / `Ctrl+K`: Quick search
- `Escape`: Close dialogs

## Troubleshooting

### Can't See Data in Dashboards

**Check Neo4j is running:**
```bash
curl http://localhost:7474
docker-compose logs neo4j
```

**Verify data exists:**
```bash
docker exec devmatrix-neo4j cypher-shell \
  -u neo4j -p devmatrix \
  "MATCH (n) RETURN COUNT(n) LIMIT 1"
```

**Try simple query first:**
```cypher
MATCH (n) RETURN n LIMIT 10
```

### Dashboard Won't Save

**Clear browser cache:**
- Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
- Clear "All time"
- Reload page

**Check browser console:**
- Open DevTools (F12)
- Look for error messages

### Connection Lost

**Restart services:**
```bash
docker-compose restart neo4j neodash
docker-compose logs neodash
```

## Resources

- [NeoDash Documentation](https://neo4j.com/docs/neodash/current/)
- [Cypher Query Language](https://neo4j.com/developer/cypher/)
- [Neo4j Pattern Library](https://neo4j.com/developer/graph-patterns/)

---

**NeoDash Version:** Latest
**Neo4j Version:** 5.26 Community
**Last Updated:** 2025-11-23
