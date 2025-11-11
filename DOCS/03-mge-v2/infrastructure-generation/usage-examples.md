# Infrastructure Generation - Usage Examples

## Complete End-to-End Examples

### Example 1: FastAPI REST API with PostgreSQL

**User Request**: "Create a REST API for managing tasks with user authentication"

#### Generated Project Structure

```
task-manager-api/
├── Dockerfile                    # Multi-stage FastAPI container
├── docker-compose.yml            # App + PostgreSQL orchestration
├── .env.example                  # Environment configuration template
├── requirements.txt              # Python dependencies
├── README.md                     # Complete project documentation
├── .gitignore                    # Python exclusions
├── src/
│   ├── main.py                   # FastAPI app entry point
│   ├── models/
│   │   ├── user.py              # User SQLAlchemy model
│   │   └── task.py              # Task SQLAlchemy model
│   ├── api/
│   │   ├── auth.py              # Authentication endpoints
│   │   └── tasks.py             # Task CRUD endpoints
│   ├── services/
│   │   ├── auth_service.py      # JWT token handling
│   │   └── task_service.py      # Business logic
│   └── database.py              # Database connection
└── tests/
    ├── test_auth.py
    └── test_tasks.py
```

#### Generated Infrastructure Files

**1. Dockerfile** (Python FastAPI multi-stage)
```dockerfile
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. docker-compose.yml** (No Redis detected)
```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: task-manager-api-app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://app_user:7f3a9b2c1e4d6f8a@postgres:5432/task_manager_api
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./src:/app/src
    networks:
      - task-manager-api-network
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: task-manager-api-postgres
    environment:
      - POSTGRES_USER=app_user
      - POSTGRES_PASSWORD=7f3a9b2c1e4d6f8a
      - POSTGRES_DB=task_manager_api
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - task-manager-api-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_user -d task_manager_api"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:

networks:
  task-manager-api-network:
    driver: bridge
```

**3. .env.example**
```bash
# Application
PROJECT_NAME=Task Manager API
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://app_user:changeme@postgres:5432/task_manager_api

# Authentication
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**4. requirements.txt**
```txt
# FastAPI and dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

**5. README.md** (Excerpt)
```markdown
# Task Manager API

A FastAPI backend for managing tasks with user authentication

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourorg/task-manager-api.git
cd task-manager-api
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Edit `.env` and change `SECRET_KEY` to a secure value:
```bash
openssl rand -hex 32
```

4. Start services:
```bash
docker-compose up -d
```

5. Verify API is running:
```bash
curl http://localhost:8000/health
```

### API Endpoints

#### Authentication
- **POST** `/api/v1/auth/register` - Register new user
- **POST** `/api/v1/auth/login` - Login and get JWT token

#### Tasks
- **GET** `/api/v1/tasks` - List all tasks
- **POST** `/api/v1/tasks` - Create new task
- **GET** `/api/v1/tasks/{id}` - Get task by ID
- **PUT** `/api/v1/tasks/{id}` - Update task
- **DELETE** `/api/v1/tasks/{id}` - Delete task

### Interactive Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
```

#### Running the Project

```bash
# 1. Navigate to generated directory
cd /workspace/task-manager-api

# 2. Copy and configure environment
cp .env.example .env
# Edit SECRET_KEY in .env

# 3. Start all services
docker-compose up -d

# 4. Watch logs
docker-compose logs -f app

# 5. Test API
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Open in browser
```

#### Expected Output

```bash
$ docker-compose up -d
[+] Running 3/3
 ✔ Network task-manager-api-network      Created
 ✔ Container task-manager-api-postgres   Healthy
 ✔ Container task-manager-api-app        Started

$ curl http://localhost:8000/health
{"status":"healthy","database":"connected"}

$ docker-compose ps
NAME                        STATUS          PORTS
task-manager-api-app        Up 2 minutes    0.0.0.0:8000->8000/tcp
task-manager-api-postgres   Up 2 minutes    5432/tcp
```

---

### Example 2: FastAPI API with Redis Caching

**User Request**: "Build an API for product catalog with caching layer"

**Detected Configuration**:
- Project type: `fastapi` (keywords: "API", "FastAPI")
- Redis required: `true` (keywords: "caching layer")
- Port: `8000` (FastAPI default)

#### Key Differences from Example 1

**docker-compose.yml** includes Redis:
```yaml
services:
  app:
    # ... app config
    environment:
      - DATABASE_URL=postgresql://app_user:pass@postgres:5432/product_catalog
      - REDIS_URL=redis://redis:6379/0  # ⭐ ADDED
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy      # ⭐ ADDED

  postgres:
    # ... postgres config

  redis:                                 # ⭐ ADDED SERVICE
    image: redis:7-alpine
    container_name: product-catalog-redis
    volumes:
      - redis-data:/data
    networks:
      - product-catalog-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:                            # ⭐ ADDED VOLUME
```

**.env.example** includes Redis config:
```bash
# ... other config

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=300
```

**requirements.txt** includes Redis:
```txt
# ... other dependencies

# Caching
redis==5.0.1
```

#### Running with Redis

```bash
# Start all services
docker-compose up -d

# Verify Redis is running
docker-compose ps
# Shows: app, postgres, redis (all healthy)

# Test Redis connection
docker-compose exec redis redis-cli ping
# Output: PONG

# Check cache in action
curl http://localhost:8000/api/v1/products  # Cache MISS (slow)
curl http://localhost:8000/api/v1/products  # Cache HIT (fast)
```

---

### Example 3: Express.js API (Future)

**User Request**: "Create a Node.js REST API with Express"

**Detected Configuration**:
- Project type: `express` (keywords: "Node.js", "Express")
- Port: `3000` (Express default)

#### Generated Structure (Planned)

```
express-api/
├── Dockerfile                    # Node.js multi-stage
├── docker-compose.yml            # App + MongoDB
├── .env.example
├── package.json                  # Instead of requirements.txt
├── README.md
├── .gitignore                    # Node.js exclusions
└── src/
    ├── app.js
    ├── models/
    ├── routes/
    ├── middleware/
    └── config/
```

**Dockerfile** (Node.js - Planned):
```dockerfile
FROM node:18-alpine as base

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "src/app.js"]
```

**package.json** template would include:
```json
{
  "name": "{{ project_slug }}",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2",
    "mongoose": "^8.0.0",
    "dotenv": "^16.3.1",
    "cors": "^2.8.5",
    "helmet": "^7.1.0"
  }
}
```

---

## Complete Workflow Examples

### Workflow 1: Generate → Deploy → Develop

```bash
# 1. Generate project via API
curl -X POST http://localhost:8000/api/v1/masterplan/generate \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "E-commerce API",
    "description": "REST API for online store with product catalog, cart, and orders"
  }'

# 2. Navigate to generated project
cd /workspace/e-commerce-api

# 3. Review generated files
ls -la
# Output:
# Dockerfile
# docker-compose.yml
# .env.example
# requirements.txt
# README.md
# .gitignore
# src/

# 4. Configure environment
cp .env.example .env
nano .env  # Edit SECRET_KEY and other sensitive values

# 5. Start development environment
docker-compose up -d

# 6. Monitor logs
docker-compose logs -f app

# 7. Develop with hot reload
# Edit files in src/ - changes automatically reload

# 8. Run tests
docker-compose exec app pytest

# 9. Check code quality
docker-compose exec app black src/
docker-compose exec app flake8 src/

# 10. Commit to Git
git init
git add .
git commit -m "Initial project structure"
git remote add origin https://github.com/yourorg/e-commerce-api.git
git push -u origin main
```

### Workflow 2: Generate → Test → Deploy to Production

```bash
# 1. Generate project (same as above)

# 2. Run complete test suite
docker-compose exec app pytest --cov=src --cov-report=html

# 3. Check test coverage
open htmlcov/index.html

# 4. Build production image
docker build -t e-commerce-api:1.0.0 .

# 5. Tag for registry
docker tag e-commerce-api:1.0.0 registry.example.com/e-commerce-api:1.0.0

# 6. Push to registry
docker push registry.example.com/e-commerce-api:1.0.0

# 7. Deploy to production
kubectl apply -f k8s/deployment.yml
# OR
docker stack deploy -c docker-compose.prod.yml e-commerce
```

### Workflow 3: Multiple Projects with Different Configs

```bash
# Project 1: Simple API (no Redis)
curl -X POST .../generate -d '{"project_name": "Simple API", "description": "Basic CRUD API"}'
cd /workspace/simple-api
docker-compose up -d
# Services: app + postgres (2 services)

# Project 2: API with Caching (with Redis)
curl -X POST .../generate -d '{"project_name": "Cached API", "description": "API with Redis caching"}'
cd /workspace/cached-api
docker-compose up -d
# Services: app + postgres + redis (3 services)

# Project 3: Different Port
# Edit .env: PORT=8001
docker-compose up -d
# App runs on localhost:8001 instead of 8000
```

---

## Testing Generated Projects

### Unit Tests

Test that services start correctly:

```bash
# Start services
docker-compose up -d

# Wait for health checks
sleep 10

# Test app health
curl -f http://localhost:8000/health || exit 1

# Test database connection
docker-compose exec postgres pg_isready -U app_user || exit 1

# Test Redis (if present)
docker-compose exec redis redis-cli ping | grep PONG || exit 1

# Cleanup
docker-compose down -v
```

### Integration Tests

Test full application workflow:

```python
# tests/test_integration.py
import pytest
import httpx

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_user_registration_and_login():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Register user
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "username": "testuser"
        })
        assert response.status_code == 201

        # 2. Login
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/tasks", headers=headers)
        assert response.status_code == 200
```

### Load Tests

Verify performance with caching:

```bash
# Install Apache Bench
apt-get install apache2-utils

# Test without cache
ab -n 1000 -c 10 http://localhost:8000/api/v1/products
# Result: ~50 req/sec

# Warm up cache
curl http://localhost:8000/api/v1/products

# Test with cache
ab -n 1000 -c 10 http://localhost:8000/api/v1/products
# Result: ~500 req/sec (10x improvement with Redis)
```

---

## Customization Examples

### Example 1: Change Database to MySQL

**1. Edit docker-compose.yml:**
```yaml
# Replace postgres service
mysql:
  image: mysql:8
  container_name: project-mysql
  environment:
    - MYSQL_ROOT_PASSWORD=rootpass
    - MYSQL_DATABASE=project_db
    - MYSQL_USER=app_user
    - MYSQL_PASSWORD=pass123
  volumes:
    - mysql-data:/var/lib/mysql
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
```

**2. Update app environment:**
```yaml
app:
  environment:
    - DATABASE_URL=mysql://app_user:pass123@mysql:3306/project_db
```

**3. Update requirements.txt:**
```txt
# Replace psycopg2-binary with
pymysql==1.1.0
```

### Example 2: Add Nginx Reverse Proxy

**1. Create nginx.conf:**
```nginx
upstream app {
    server app:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**2. Add to docker-compose.yml:**
```yaml
nginx:
  image: nginx:alpine
  container_name: project-nginx
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - app
  networks:
    - project-network
```

**3. Update app (remove port exposure):**
```yaml
app:
  # ports:
  #   - "8000:8000"  # Remove - only nginx exposes ports
```

### Example 3: Add CI/CD with GitHub Actions

**Create .github/workflows/ci.yml:**
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 10

      - name: Run tests
        run: docker-compose exec -T app pytest

      - name: Check coverage
        run: docker-compose exec -T app pytest --cov=src

      - name: Cleanup
        run: docker-compose down -v
```

---

## Production Deployment Examples

### Example 1: Docker Swarm

```bash
# 1. Initialize swarm
docker swarm init

# 2. Create production compose file
cp docker-compose.yml docker-compose.prod.yml

# 3. Add deploy constraints
# Edit docker-compose.prod.yml:
services:
  app:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure

# 4. Deploy stack
docker stack deploy -c docker-compose.prod.yml myapp

# 5. Scale services
docker service scale myapp_app=5
```

### Example 2: Kubernetes

```bash
# 1. Build and push image
docker build -t registry.example.com/myapp:1.0.0 .
docker push registry.example.com/myapp:1.0.0

# 2. Generate Kubernetes manifests (future feature)
# Would create:
# - deployment.yml
# - service.yml
# - ingress.yml
# - configmap.yml
# - secret.yml

# 3. Deploy to cluster
kubectl apply -f k8s/

# 4. Verify deployment
kubectl get pods
kubectl get services
```

---

## Troubleshooting Examples

### Example 1: Database Connection Failed

**Problem**: App can't connect to database

**Solution**:
```bash
# 1. Check if postgres is healthy
docker-compose ps
# postgres should show "healthy"

# 2. Check logs
docker-compose logs postgres

# 3. Verify connection manually
docker-compose exec postgres psql -U app_user -d project_db
# Should connect successfully

# 4. Check DATABASE_URL in app
docker-compose exec app env | grep DATABASE_URL
```

### Example 2: Redis Connection Timeout

**Problem**: App times out connecting to Redis

**Solution**:
```bash
# 1. Verify Redis is running
docker-compose ps redis

# 2. Test Redis directly
docker-compose exec redis redis-cli ping
# Should return PONG

# 3. Check network connectivity
docker-compose exec app ping redis
# Should resolve and ping successfully

# 4. Verify REDIS_URL
docker-compose exec app env | grep REDIS_URL
```

## Next Steps

- **[Templates Guide](./templates-guide.md)** - Customize infrastructure templates
- **[Troubleshooting](./troubleshooting.md)** - Fix common issues
- **[Architecture](./architecture.md)** - Understand system design
