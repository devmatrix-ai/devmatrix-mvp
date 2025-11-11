# Templates Guide

## Overview

Los templates de infraestructura usan **Jinja2** para renderizado dinámico. Cada template es un archivo con placeholders `{{ variable }}` que se reemplazan con valores extraídos del MasterPlan.

## Template Directory Structure

```
templates/
├── docker/
│   ├── python_fastapi.dockerfile      # FastAPI multi-stage build
│   └── docker-compose.yml.j2          # Service orchestration
├── config/
│   ├── env_fastapi.example.j2         # Environment variables
│   └── requirements_fastapi.txt.j2    # Python dependencies
└── git/
    ├── README_fastapi.md.j2           # Project documentation
    └── gitignore_python.txt           # Version control exclusions
```

## Jinja2 Basics

### Variable Substitution

```jinja2
# Simple variable
PROJECT_NAME={{ project_name }}

# With default value
PORT={{ app_port|default(8000) }}

# String operations
SLUG={{ project_name|lower|replace(" ", "-") }}
```

### Conditional Blocks

```jinja2
{% if needs_redis -%}
# Redis configuration
REDIS_URL=redis://redis:6379/0
CACHE_TTL=300
{% endif -%}
```

**Nota**: El `-` en `{%-` y `-%}` elimina espacios en blanco.

### Loops

```jinja2
# API Endpoints
{% for endpoint in api_endpoints -%}
- **{{ endpoint.method }}** `{{ endpoint.path }}` - {{ endpoint.description }}
{% endfor -%}
```

### Comments

```jinja2
{# This is a comment, not rendered in output #}
```

## Available Templates

### 1. Dockerfile (FastAPI)

**Template**: `templates/docker/python_fastapi.dockerfile`

**Variables**:
```python
{
    "port": int,  # Application port (default: 8000)
}
```

**Key Features**:
- Multi-stage build (development + production)
- Health check on `/health` endpoint
- Non-root user in production
- PostgreSQL client tools included
- Optimized layer caching

**Usage**:
```python
template = jinja_env.get_template("docker/python_fastapi.dockerfile")
content = template.render(port=8000)
```

**Output Example**:
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose

**Template**: `templates/docker/docker-compose.yml.j2`

**Variables**:
```python
{
    "project_slug": str,        # "my-project"
    "app_port": int,            # 8000
    "db_user": str,             # "app_user"
    "db_password": str,         # secrets.token_hex(16)
    "db_name": str,             # "my_project"
    "needs_redis": bool         # Auto-detected
}
```

**Key Features**:
- App service with volume mounts for hot reload
- PostgreSQL with health checks
- Conditional Redis service
- Named volumes for data persistence
- Isolated network per project
- Dependency ordering (`depends_on`)

**Usage**:
```python
template = jinja_env.get_template("docker/docker-compose.yml.j2")
content = template.render(
    project_slug="my-project",
    app_port=8000,
    db_user="app_user",
    db_password=secrets.token_hex(16),
    db_name="my_project",
    needs_redis=True
)
```

**Output Example**:
```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: my-project-app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://app_user:abc123@postgres:5432/my_project
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
    networks:
      - my-project-network
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: my-project-postgres
    environment:
      - POSTGRES_USER=app_user
      - POSTGRES_PASSWORD=abc123
      - POSTGRES_DB=my_project
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - my-project-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_user -d my_project"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: my-project-redis
    volumes:
      - redis-data:/data
    networks:
      - my-project-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:

networks:
  my-project-network:
    driver: bridge
```

### 3. Environment Variables

**Template**: `templates/config/env_fastapi.example.j2`

**Variables**:
```python
{
    "project_name": str,
    "app_port": int,
    "db_user": str,
    "db_password": str,
    "db_name": str,
    "needs_redis": bool
}
```

**Key Features**:
- Comprehensive variable documentation
- Secure defaults (requires manual SECRET_KEY change)
- Conditional sections (Redis only if needed)
- Clear categorization (Application, Server, Database, Auth, Redis)

**Usage**:
```python
template = jinja_env.get_template("config/env_fastapi.example.j2")
content = template.render(
    project_name="My Project",
    app_port=8000,
    db_user="app_user",
    db_password="changeme",
    db_name="my_project",
    needs_redis=True
)
```

**Output Example**:
```bash
# Application
PROJECT_NAME=My Project
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://app_user:changeme@postgres:5432/my_project

# Authentication
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=300
```

### 4. Python Requirements

**Template**: `templates/config/requirements_fastapi.txt.j2`

**Variables**:
```python
{
    "fastapi_version": str,
    "uvicorn_version": str,
    "sqlalchemy_version": str,
    "alembic_version": str,
    "psycopg2_version": str,
    "python_jose_version": str,
    "passlib_version": str,
    "redis_version": str,
    "needs_redis": bool
}
```

**Key Features**:
- Version pinning for reproducibility
- Organized by category (FastAPI, Database, Authentication, Caching)
- Conditional dependencies (Redis only if needed)
- Standard versions with `|default()` filters

**Usage**:
```python
template = jinja_env.get_template("config/requirements_fastapi.txt.j2")
content = template.render(
    fastapi_version="0.104.1",
    uvicorn_version="0.24.0",
    sqlalchemy_version="2.0.23",
    needs_redis=True
)
```

**Output Example**:
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

# Caching
redis==5.0.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

### 5. README.md

**Template**: `templates/git/README_fastapi.md.j2`

**Variables**:
```python
{
    "project_name": str,
    "project_description": str,
    "app_port": int,
    "needs_redis": bool,
    "api_endpoints": List[Dict],  # [{"method": "GET", "path": "/users", "description": "..."}]
    "project_slug": str
}
```

**Key Features**:
- Comprehensive getting started guide
- Prerequisites and installation steps
- Project structure diagram
- Configuration instructions
- API endpoint documentation (auto-extracted)
- Testing and deployment guides
- Conditional sections (Redis, additional services)

**Sections**:
1. Project overview
2. Quick Start (prerequisites → installation → run)
3. Project Structure
4. Configuration
5. API Endpoints
6. Testing
7. Deployment
8. Contributing

**Usage**:
```python
template = jinja_env.get_template("git/README_fastapi.md.j2")
content = template.render(
    project_name="My API",
    project_description="A FastAPI backend for X",
    app_port=8000,
    needs_redis=True,
    api_endpoints=[
        {"method": "GET", "path": "/users", "description": "List all users"},
        {"method": "POST", "path": "/users", "description": "Create new user"}
    ],
    project_slug="my-api"
)
```

### 6. .gitignore

**Template**: `templates/git/gitignore_python.txt`

**Variables**: None (static file)

**Key Features**:
- Comprehensive Python patterns
- Virtual environment exclusions
- IDE configurations (VSCode, PyCharm, Sublime)
- OS-specific files (.DS_Store, Thumbs.db)
- Database files
- Test coverage reports

**Categories**:
- Python bytecode and cache
- Virtual environments
- Environment files
- IDE and editor files
- Test coverage
- Database files
- OS-specific files

**Output Example**:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual Environments
venv/
.venv/
env/
ENV/

# Environment
.env
.env.local
*.env
!.env.example

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.coverage
htmlcov/
.pytest_cache/

# Database
*.db
*.sqlite3

# OS
.DS_Store
Thumbs.db
```

## Creating Custom Templates

### Step 1: Create Template File

```bash
# Create new template
mkdir -p templates/custom/
touch templates/custom/mytemplate.yml.j2
```

### Step 2: Define Template Content

```jinja2
# mytemplate.yml.j2
name: {{ project_name }}
version: {{ version|default("1.0.0") }}

{% if enable_feature -%}
features:
  - feature_one
  - feature_two
{% endif -%}

services:
{% for service in services -%}
  - {{ service.name }}: {{ service.port }}
{% endfor -%}
```

### Step 3: Add Variables to Metadata Extraction

```python
# In infrastructure_generation_service.py
def _extract_project_metadata(self, ...):
    metadata = {
        # ... existing variables
        "version": "1.0.0",
        "enable_feature": self._detect_feature(tasks),
        "services": self._extract_services(tasks)
    }
    return metadata
```

### Step 4: Render in generate_infrastructure()

```python
# In generate_infrastructure()
try:
    template = self.jinja_env.get_template("custom/mytemplate.yml.j2")
    content = template.render(**metadata)
    output_path = workspace_path / "mytemplate.yml"
    output_path.write_text(content)
    files_generated.append("mytemplate.yml")
except Exception as e:
    logger.error(f"Failed to generate mytemplate.yml: {str(e)}")
    errors.append(f"mytemplate.yml: {str(e)}")
```

## Template Best Practices

### 1. Use Defaults for Optional Variables

```jinja2
# Good - provides fallback
PORT={{ app_port|default(8000) }}

# Bad - crashes if variable missing
PORT={{ app_port }}
```

### 2. Trim Whitespace Properly

```jinja2
# Good - clean output
{% if condition -%}
content
{% endif -%}

# Bad - extra blank lines
{% if condition %}
content
{% endif %}
```

### 3. Comment Complex Logic

```jinja2
{# Check if project needs Redis based on cache requirements #}
{% if needs_redis -%}
REDIS_URL=redis://redis:6379/0
{% endif -%}
```

### 4. Organize by Sections

```jinja2
# ======================
# Application Settings
# ======================
PROJECT_NAME={{ project_name }}

# ======================
# Database Configuration
# ======================
DATABASE_URL={{ database_url }}
```

### 5. Validate Required Variables

```python
# In service code
required_vars = ["project_name", "app_port", "db_user"]
for var in required_vars:
    if var not in metadata:
        raise ValueError(f"Missing required variable: {var}")
```

### 6. Use Filters for Transformations

```jinja2
# String transformations
{{ project_name|lower }}                    # lowercase
{{ project_name|upper }}                    # uppercase
{{ project_name|replace(" ", "-") }}        # replace spaces
{{ project_name|lower|replace(" ", "_") }}  # combine filters

# Default values
{{ version|default("1.0.0") }}

# List operations
{{ items|length }}                          # count
{{ items|first }}                           # first item
{{ items|last }}                            # last item
```

## Testing Templates

### Manual Testing

```python
from jinja2 import Environment, FileSystemLoader

# Load environment
env = Environment(loader=FileSystemLoader("templates/"))

# Render template
template = env.get_template("docker/docker-compose.yml.j2")
output = template.render(
    project_slug="test-project",
    app_port=8000,
    db_user="test_user",
    db_password="test_pass",
    db_name="test_db",
    needs_redis=True
)

# Verify output
assert "test-project-app" in output
assert "REDIS_URL" in output
print(output)
```

### Unit Testing

```python
def test_dockerfile_template():
    env = Environment(loader=FileSystemLoader("templates/"))
    template = env.get_template("docker/python_fastapi.dockerfile")

    output = template.render(port=8000)

    assert "EXPOSE 8000" in output
    assert "HEALTHCHECK" in output
    assert "uvicorn" in output
```

### Integration Testing

Current E2E test (`tests/test_mge_v2_e2e.py`) validates:
- All 6 templates render without errors
- Generated files have expected content
- docker-compose.yml is valid YAML
- .env.example contains required variables

## Troubleshooting

### Template Not Found

**Error**: `jinja2.exceptions.TemplateNotFound: docker/mytemplate.dockerfile`

**Solution**:
1. Verify file exists: `ls templates/docker/mytemplate.dockerfile`
2. Check templates directory in Docker: `docker exec devmatrix-api ls /app/templates/docker/`
3. Ensure Dockerfile copies templates: `COPY templates/ ./templates/`

### Undefined Variable

**Error**: `jinja2.exceptions.UndefinedError: 'missing_var' is undefined`

**Solution**:
1. Use `|default()` filter: `{{ missing_var|default("default_value") }}`
2. Add variable to metadata extraction: `metadata["missing_var"] = "value"`
3. Make block conditional: `{% if missing_var is defined %}`

### Rendering Error

**Error**: `TypeError: render() got unexpected keyword argument 'invalid_var'`

**Solution**:
1. Check variable names match between metadata and template
2. Use `**metadata` to pass all variables: `template.render(**metadata)`
3. Filter variables: `template.render(**{k: v for k, v in metadata.items() if k in allowed})`

### Whitespace Issues

**Problem**: Extra blank lines in generated file

**Solution**:
Use trim blocks in Jinja2 config:
```python
Environment(
    trim_blocks=True,      # Remove first newline after block
    lstrip_blocks=True     # Remove leading spaces before block
)
```

And use `-` in template:
```jinja2
{% if condition -%}
content
{% endif -%}
```

## Advanced Techniques

### Macros (Reusable Blocks)

```jinja2
{# Define macro #}
{% macro render_service(name, port) -%}
{{ name }}:
  image: {{ name }}:latest
  ports:
    - "{{ port }}:{{ port }}"
{% endmacro -%}

{# Use macro #}
services:
{{ render_service("app", 8000) }}
{{ render_service("redis", 6379) }}
```

### Template Inheritance

```jinja2
{# base_dockerfile.j2 #}
FROM {{ base_image }}

{% block install -%}
RUN apt-get update
{% endblock -%}

{% block copy -%}
COPY . .
{% endblock -%}

{# python_dockerfile.j2 #}
{% extends "base_dockerfile.j2" %}

{% block install -%}
{{ super() }}
RUN pip install -r requirements.txt
{% endblock -%}
```

### Variable Scoping

```jinja2
{% set db_host = "localhost" if debug else "postgres" %}
DATABASE_URL=postgresql://user@{{ db_host }}/db
```

### Conditional Imports

```jinja2
{% if needs_advanced_features -%}
{% include "advanced_config.j2" %}
{% endif -%}
```

## Next Steps

- **[Usage Examples](./usage-examples.md)** - Complete examples of generated projects
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions
- **[Architecture](./architecture.md)** - Technical design details
