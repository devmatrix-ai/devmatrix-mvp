# Infrastructure Generation Architecture

## System Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MGE V2 Orchestrator                       │
│  (src/services/mge_v2_orchestration_service.py)            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Step 6: Infrastructure Generation
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          InfrastructureGenerationService                    │
│  (src/services/infrastructure_generation_service.py)        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Detect    │→ │   Extract   │→ │   Render    │       │
│  │ Project Type│  │  Metadata   │  │  Templates  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ 6 Infrastructure Files
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Workspace Directory                      │
│  /workspace/project-name/                                   │
│  ├── Dockerfile                                             │
│  ├── docker-compose.yml                                     │
│  ├── .env.example                                           │
│  ├── requirements.txt                                       │
│  ├── README.md                                              │
│  └── .gitignore                                             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. InfrastructureGenerationService

**Location**: `src/services/infrastructure_generation_service.py` (555 lines)

**Responsibilities**:
- Detect project type from MasterPlan tasks
- Extract metadata for template rendering
- Render Jinja2 templates with dynamic variables
- Write infrastructure files to workspace

**Key Methods**:

```python
class InfrastructureGenerationService:
    """Service for generating complete project infrastructure."""

    def __init__(self, db: Session, templates_dir: str = None):
        """Initialize with database session and templates directory."""
        self.db = db
        self.templates_dir = Path(templates_dir) or Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    async def generate_infrastructure(
        self,
        masterplan_id: uuid.UUID,
        workspace_path: Path
    ) -> Dict[str, Any]:
        """
        Main entry point - generates ALL infrastructure files.

        Returns:
            {
                "success": bool,
                "project_type": str,
                "files_generated": List[str],
                "metadata": Dict[str, Any],
                "errors": List[str]
            }
        """
        # 1. Load MasterPlan and tasks from database
        # 2. Detect project type (fastapi, express, react)
        # 3. Extract metadata (ports, services, dependencies)
        # 4. Generate each infrastructure file
        # 5. Return results with detailed info

    def _detect_project_type(
        self,
        masterplan: MasterPlan,
        tasks: List[MasterPlanTask]
    ) -> str:
        """
        Auto-detect project type using keyword analysis.

        Algorithm:
        1. Concatenate project_name + description + all task names/descriptions
        2. Convert to lowercase
        3. Search for framework-specific keywords
        4. Return first match or "unknown"

        Keyword Sets:
        - FastAPI: ["fastapi", "uvicorn", "pydantic"]
        - Express: ["express", "node.js", "nodejs"]
        - React: ["react", "nextjs", "next.js"]
        """

    def _extract_project_metadata(
        self,
        masterplan: MasterPlan,
        tasks: List[MasterPlanTask],
        project_type: str
    ) -> Dict[str, Any]:
        """
        Extract all metadata needed for template rendering.

        Extracted Data:
        - project_name: From MasterPlan.project_name
        - project_slug: Lowercase with hyphens
        - project_description: From MasterPlan.description
        - app_port: 8000 (FastAPI) or 3000 (Express/React)
        - db_user: "app_user"
        - db_password: secrets.token_hex(16)
        - db_name: project_slug with underscores
        - needs_redis: Detected from keywords ["redis", "cache", "caching"]
        - api_endpoints: Extracted from task descriptions
        - dependencies: Extracted from task names
        """
```

### 2. Template System (Jinja2)

**Templates Directory**: `/templates/`

**Template Organization**:

```
templates/
├── docker/              # Containerization
│   ├── python_fastapi.dockerfile
│   ├── nodejs_express.dockerfile  (planned)
│   └── docker-compose.yml.j2
├── config/              # Configuration files
│   ├── env_fastapi.example.j2
│   ├── env_express.example.j2     (planned)
│   └── requirements_fastapi.txt.j2
├── git/                 # Version control
│   ├── README_fastapi.md.j2
│   ├── README_express.md.j2       (planned)
│   ├── gitignore_python.txt
│   └── gitignore_nodejs.txt       (planned)
├── cicd/                # CI/CD (planned)
│   ├── github_actions.yml.j2
│   └── gitlab_ci.yml.j2
└── database/            # DB migrations (planned)
    ├── alembic_env.py.j2
    └── init_sql.j2
```

**Jinja2 Configuration**:

```python
self.jinja_env = Environment(
    loader=FileSystemLoader(str(self.templates_dir)),
    autoescape=select_autoescape(['html', 'xml']),  # Security
    trim_blocks=True,      # Clean whitespace
    lstrip_blocks=True     # Better formatting
)
```

### 3. Integration with MGE V2 Orchestrator

**Location**: `src/services/mge_v2_orchestration_service.py`

**Integration Point**: Step 6 after file writing

```python
# Step 6: Generate Infrastructure (Docker, configs, docs)
yield {
    "type": "status",
    "phase": "infrastructure_generation",
    "message": "Generating project infrastructure (Docker, configs, docs)...",
    "timestamp": datetime.utcnow().isoformat()
}

from src.services.infrastructure_generation_service import InfrastructureGenerationService
from pathlib import Path

infra_service = InfrastructureGenerationService(db=self.db)

if workspace_path:
    infra_result = await infra_service.generate_infrastructure(
        masterplan_id=masterplan_id,
        workspace_path=Path(workspace_path)
    )

    if infra_result["success"]:
        yield {
            "type": "status",
            "phase": "infrastructure_generation",
            "message": f"Infrastructure generated: {infra_result['files_generated']} files ({infra_result['project_type']})",
            "files_generated": infra_result['files_generated'],
            "project_type": infra_result['project_type'],
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        yield {
            "type": "error",
            "phase": "infrastructure_generation",
            "message": f"Infrastructure generation failed: {infra_result.get('errors', [])}",
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Detection Algorithms

### Project Type Detection

**Algorithm**: Keyword-based classification

```python
def _detect_project_type(self, masterplan: MasterPlan, tasks: List[MasterPlanTask]) -> str:
    # Aggregate all text
    text = f"{masterplan.project_name} {masterplan.description or ''}"
    for task in tasks:
        text += f" {task.name} {task.description}"
    text = text.lower()

    # Search for framework keywords
    if any(keyword in text for keyword in ["fastapi", "uvicorn", "pydantic"]):
        return "fastapi"
    elif any(keyword in text for keyword in ["express", "node.js", "nodejs"]):
        return "express"
    elif any(keyword in text for keyword in ["react", "nextjs", "next.js"]):
        return "react"

    return "unknown"
```

**Keyword Sets**:

| Framework | Keywords |
|-----------|----------|
| FastAPI | `fastapi`, `uvicorn`, `pydantic` |
| Express | `express`, `node.js`, `nodejs` |
| React | `react`, `nextjs`, `next.js` |

### Redis Detection

**Algorithm**: Cache-related keyword search

```python
def _detect_redis_requirement(self, masterplan: MasterPlan, tasks: List[MasterPlanTask]) -> bool:
    text = f"{masterplan.project_name} {masterplan.description or ''}"
    for task in tasks:
        text += f" {task.name} {task.description}"

    return any(keyword in text.lower() for keyword in ["redis", "cache", "caching"])
```

### Port Assignment

**Algorithm**: Framework-based default ports

```python
def _determine_port(self, project_type: str) -> int:
    port_map = {
        "fastapi": 8000,
        "express": 3000,
        "react": 3000,
        "nextjs": 3000
    }
    return port_map.get(project_type, 8000)
```

### API Endpoint Extraction

**Algorithm**: Pattern matching in task descriptions

```python
def _extract_api_endpoints(self, tasks: List[MasterPlanTask]) -> List[Dict[str, Any]]:
    endpoints = []

    for task in tasks:
        description = task.description.lower()

        # Look for HTTP method keywords
        if any(method in description for method in ["get", "post", "put", "delete"]):
            # Extract endpoint path using regex
            path_match = re.search(r'/[a-zA-Z0-9/_-]+', description)
            if path_match:
                endpoints.append({
                    "path": path_match.group(0),
                    "method": self._extract_http_method(description),
                    "description": task.description
                })

    return endpoints
```

## Template Variables

### Common Variables (All Templates)

```python
{
    "project_name": str,        # "My Project"
    "project_slug": str,        # "my-project"
    "project_description": str, # "A FastAPI application"
    "app_port": int,            # 8000 or 3000
    "timestamp": str            # ISO format
}
```

### Database Variables

```python
{
    "db_type": str,             # "postgresql", "mysql", "mongodb"
    "db_user": str,             # "app_user"
    "db_password": str,         # secrets.token_hex(16)
    "db_name": str,             # "my_project"
    "db_port": int              # 5432, 3306, 27017
}
```

### Service Variables

```python
{
    "needs_redis": bool,        # Auto-detected from keywords
    "needs_celery": bool,       # Future: async tasks
    "needs_nginx": bool         # Future: reverse proxy
}
```

### Dependency Variables

```python
{
    "fastapi_version": str,     # "0.104.1"
    "uvicorn_version": str,     # "0.24.0"
    "sqlalchemy_version": str,  # "2.0.23"
    # ... more versioned dependencies
}
```

## Error Handling

### Error Types

1. **Template Not Found** - Fall back to default or skip
2. **Rendering Error** - Log error, continue with other files
3. **File Write Error** - Permission issues, disk full
4. **Database Error** - MasterPlan not found

### Error Recovery Strategy

```python
try:
    # Attempt to generate infrastructure
    result = await self.generate_infrastructure(masterplan_id, workspace_path)
except Exception as e:
    logger.error(f"Infrastructure generation failed: {str(e)}")
    # Return partial success with error details
    return {
        "success": False,
        "files_generated": [],
        "errors": [str(e)],
        "project_type": "unknown"
    }
```

## Security Considerations

### 1. Password Generation

```python
import secrets

db_password = secrets.token_hex(16)  # Cryptographically secure
```

### 2. Template Autoescape

```python
autoescape=select_autoescape(['html', 'xml'])  # Prevent XSS
```

### 3. .gitignore Protection

Ensures sensitive files are never committed:
```
.env
*.env
!.env.example
```

### 4. Non-Root Container User

Production Dockerfile creates unprivileged user:
```dockerfile
RUN useradd -m -u 1000 devmatrix && \
    chown -R devmatrix:devmatrix /app
USER devmatrix
```

## Performance Optimization

### 1. Template Caching

Jinja2 automatically caches compiled templates in memory.

### 2. Parallel File Writing

```python
import asyncio

async def write_all_files(self, files: List[Tuple[Path, str]]):
    tasks = [self._write_file(path, content) for path, content in files]
    await asyncio.gather(*tasks)
```

### 3. Lazy Loading

Templates are only loaded when needed, not all at startup.

## Testing Strategy

### Unit Tests (Planned)

```python
def test_detect_fastapi_project():
    service = InfrastructureGenerationService(db=mock_db)
    masterplan = MasterPlan(project_name="API", description="FastAPI backend")
    tasks = [MasterPlanTask(name="Create uvicorn server")]

    project_type = service._detect_project_type(masterplan, tasks)
    assert project_type == "fastapi"
```

### Integration Tests

Current E2E test in `tests/test_mge_v2_e2e.py`:
- Generates complete project
- Verifies 24 files created (18 code + 6 infrastructure)
- Validates docker-compose.yml syntax
- Checks .env.example has required variables

## Extensibility

### Adding New Project Types

1. **Create templates** in `templates/docker/`, `templates/config/`, etc.
2. **Add detection keywords** in `_detect_project_type()`
3. **Define port mapping** in `_determine_port()`
4. **Update metadata extraction** for framework-specific needs

### Adding New Infrastructure Files

1. **Create Jinja2 template** in appropriate subdirectory
2. **Add rendering logic** in `generate_infrastructure()`
3. **Update metadata extraction** if new variables needed
4. **Add validation** to ensure file was created correctly

## Future Enhancements

1. **CI/CD Templates** - GitHub Actions, GitLab CI, CircleCI
2. **Database Migrations** - Alembic, TypeORM migrations
3. **Monitoring** - Prometheus, Grafana configs
4. **Load Balancing** - Nginx reverse proxy configs
5. **Cloud Deployment** - AWS, GCP, Azure deployment configs
6. **Kubernetes** - k8s manifests for container orchestration
