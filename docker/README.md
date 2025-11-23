# DevMatrix Docker Services

Complete containerized DevMatrix stack with Neo4j graph database, NeoDash UI, Qdrant vector search, PostgreSQL, Redis, and monitoring tools.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         FastAPI Application (8001)              │
│         - Pattern Generation                    │
│         - Code Synthesis                        │
│         - Cognitive Architecture                │
└────────┬────────────┬──────────────┬───────────┘
         │            │              │
    ┌────▼──┐  ┌──────▼────┐  ┌─────▼──────┐
    │Neo4j  │  │ Qdrant    │  │PostgreSQL  │
    │(7687) │  │ (6333)    │  │ (5432)     │
    └───┬───┘  └───────────┘  └────────────┘
        │
    ┌───▼────────────────┐
    │NeoDash Dashboard   │
    │ (5005) - Navigator │
    └────────────────────┘

    + Redis (6379) - Session State
    + Prometheus (9090) - Metrics
    + Grafana (3001) - Visualization
```

## 📦 Services

### Core Services (Always Running)

| Service | Port | Purpose | Technology |
|---------|------|---------|------------|
| **Neo4j** | 7474, 7687 | Graph Database | Neo4j 5.26 Community |
| **NeoDash** | 5005 | Graph Explorer UI | Neo4j's Dashboard |
| **Qdrant** | 6333, 6334 | Vector Database | Qdrant Latest |
| **PostgreSQL** | 5432 | Relational Database | pgvector:pg16 |
| **Redis** | 6379 | Cache & State | Redis 7-alpine |
| **FastAPI** | 8001 | Backend API | Python 3.11 |

### Optional Services (Profiles)

**`--profile dev`**
- Vite UI Development Server (3000)

**`--profile monitoring`**
- Prometheus (9090)
- Grafana (3001)
- PostgreSQL Exporter (9187)
- Redis Exporter (9121)

**`--profile tools`**
- pgAdmin (5050)

**`--profile memgraph`** (EXPERIMENTAL)
- Memgraph Graph Database (7688 - Alternative to Neo4j)
- Memgraph Lab (3002 - Graph Explorer)

## 🚀 Quick Start

### Prerequisites
```bash
# Install Docker & Docker Compose
docker --version  # >= 20.10
docker-compose --version  # >= 2.0

# Optional: For GPU support
nvidia-docker --version
```

### Startup Profiles

```bash
# Start core services only (fastest)
./docker/start-services.sh

# Or explicitly
docker-compose up -d

# With development UI
./docker/start-services.sh dev
docker-compose --profile dev up -d

# With monitoring
./docker/start-services.sh monitoring
docker-compose --profile monitoring up -d

# Everything
./docker/start-services.sh all
docker-compose --profile dev --profile tools --profile monitoring up -d
```

### Verify Services

```bash
# Check running containers
docker ps -a

# Check service health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## 🔍 Accessing Services

### Neo4j Browser (Classic)
```
URL: http://localhost:7474
Auth: neo4j / devmatrix (from .env)
```

### NeoDash (Recommended for Neo4j Graphs)
```
URL: http://localhost:5005
Auto-connected to bolt://neo4j:7687
No setup needed - just start exploring!

Features:
- Interactive graph visualization
- Pattern navigation
- Relationship exploration
- Custom dashboards
```

### Memgraph Lab (Alternative Graph Database - Optional)
```
URL: http://localhost:3002 (when using --profile memgraph)
Connected to bolt://localhost:7688 (Memgraph database)
Auto-configured on startup

Features:
- High-performance graph database (faster than Neo4j in some scenarios)
- Interactive graph explorer
- Pattern analysis and visualization
- Real-time query execution

Enable with:
docker-compose --profile memgraph up
```

### NeoDash First-Time Setup
1. Open http://localhost:5005
2. Connection auto-configures
3. Start creating dashboards:
   - Click "New Dashboard"
   - Add visualizations
   - Save for later use

### PostgreSQL Access

**Via psql:**
```bash
psql -h localhost -U devmatrix -d devmatrix
```

**Via pgAdmin (if tools profile enabled):**
```
URL: http://localhost:5050
Email: admin@devmatrix.local
Password: admin
```

### Qdrant Vector DB
```
REST API: http://localhost:6333
gRPC: localhost:6334

Example:
curl http://localhost:6333/health
```

### Metrics & Monitoring

**Prometheus:**
```
URL: http://localhost:9090
Scrape interval: 15s
Data retention: 7 days
```

**Grafana:**
```
URL: http://localhost:3001
Default: admin / admin
Pre-configured datasources: Prometheus
```

## 📝 Configuration

### Environment Variables (.env)

**Neo4j & NeoDash:**
```env
NEO4J_USER=neo4j
NEO4J_PASSWORD=devmatrix
NEO4J_PAGECACHE=512M
NEO4J_HEAP=1G
NEODASH_PORT=5005
NEODASH_STANDALONE_MODE=true
```

**Qdrant:**
```env
QDRANT_HTTP_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_COLLECTION_PATTERNS=devmatrix_patterns
QDRANT_COLLECTION_SEMANTIC=semantic_patterns
```

**Database:**
```env
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix
REDIS_PORT=6379
```

### Custom Configuration

Edit `.env` file:
```bash
cp .env.example .env
nano .env  # Update values
docker-compose up -d
```

## 🛠️ Common Operations

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f neo4j
docker-compose logs -f neodash
docker-compose logs -f postgres
```

### Access Service Shells
```bash
# PostgreSQL
docker exec -it devmatrix-postgres psql -U devmatrix

# Redis
docker exec -it devmatrix-redis redis-cli

# Neo4j Cypher
docker exec -it devmatrix-neo4j cypher-shell
```

### Data Persistence
```bash
# Volumes created automatically
docker volume ls | grep devmatrix

# Backup volumes
docker run -v devmatrix-neo4j-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/neo4j-backup.tar.gz -C /data .

# Restore volumes
docker run -v devmatrix-neo4j-data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/neo4j-backup.tar.gz -C /data
```

### Stop & Cleanup

```bash
# Stop running services (keeps data)
docker-compose down

# Stop and remove volumes (DELETE DATA)
docker-compose down -v

# Prune unused resources
docker system prune -a
```

### Resource Limits

Current limits in docker-compose.yml:
- **API CPU:** 2 cores
- **API Memory:** 4GB
- **Neo4j Memory:** 1GB heap + 512MB pagecache

Adjust for your hardware:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

## 🐛 Troubleshooting

### Services Not Starting

**Check health:**
```bash
docker-compose ps
# Look for "healthy" vs "starting" vs "unhealthy"
```

**View detailed logs:**
```bash
docker-compose logs [service-name]
```

### Neo4j Connection Failed

```bash
# Verify Neo4j is running
curl http://localhost:7474

# Check credentials in .env
docker exec devmatrix-neo4j cypher-shell -u neo4j -p devmatrix

# Restart Neo4j
docker-compose restart neo4j
```

### NeoDash Can't Connect

```bash
# Verify Neo4j is healthy (wait ~30s)
docker ps | grep neo4j
# Should show "healthy" in STATUS

# Restart NeoDash
docker-compose restart neodash

# Check NeoDash logs
docker-compose logs neodash
```

### Out of Disk Space

```bash
# Check volume usage
docker system df

# Clean up unused volumes
docker volume prune

# Reduce retention periods in Prometheus/Grafana
```

### PostgreSQL Performance

```bash
# Check connections
docker exec devmatrix-postgres \
  psql -U devmatrix -c "SELECT count(*) FROM pg_stat_activity;"

# View query logs
docker-compose logs postgres | grep "duration:"
```

## 📊 Monitoring & Debugging

### Query Neo4j Graph
```bash
# Via cypher-shell
docker exec -it devmatrix-neo4j cypher-shell \
  -u neo4j -p devmatrix \
  "MATCH (n) RETURN COUNT(n) AS node_count"

# Via Browser
http://localhost:7474 → "MATCH (n) RETURN COUNT(n)"
```

### Search Qdrant Collections
```bash
curl http://localhost:6333/collections

# View specific collection
curl http://localhost:6333/collections/devmatrix_patterns
```

### Monitor API Health
```bash
curl http://localhost:8001/api/v1/health/live
curl http://localhost:8001/api/v1/health/ready
```

## 🔐 Security Notes

### Default Credentials (CHANGE IN PRODUCTION)

| Service | User | Password |
|---------|------|----------|
| Neo4j | neo4j | devmatrix |
| PostgreSQL | devmatrix | devmatrix |
| Grafana | admin | admin |
| pgAdmin | admin@devmatrix.local | admin |

### Recommended Security Steps

1. **Change all default passwords:**
   ```env
   NEO4J_PASSWORD=<strong-password>
   POSTGRES_PASSWORD=<strong-password>
   GRAFANA_ADMIN_PASSWORD=<strong-password>
   ```

2. **Restrict network access:**
   ```yaml
   ports:
     - "127.0.0.1:7474:7474"  # localhost only
   ```

3. **Use secrets management:**
   ```bash
   docker secret create db_password -
   # Reference in compose: ${DB_PASSWORD}
   ```

## 📚 Documentation

- [DevMatrix Architecture](../DOCS/01-architecture/)
- [API Reference](../DOCS/04-api-reference/)
- [DevOps Guide](../DOCS/DEVOPS_GUIDE.md)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

## 🆘 Getting Help

```bash
# Check Docker version compatibility
docker-compose version

# Validate compose file
docker-compose config

# Get service info
docker inspect devmatrix-neo4j

# View resource usage
docker stats
```

---

**Last Updated:** 2025-11-23
**Status:** 🟢 Production Ready
