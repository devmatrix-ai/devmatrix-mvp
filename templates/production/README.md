# Production Templates for DevMatrix

This directory contains Jinja2 templates for generating production-ready FastAPI applications.

## Template Organization

```
production/
├── core/           # Core infrastructure (config, database, logging, security, middleware)
├── models/         # Pydantic schemas and SQLAlchemy entities
├── repositories/   # Data access layer
├── services/       # Business logic layer
├── api/            # API routes and dependencies
├── tests/          # Test suite (pytest, conftest, factories)
├── docker/         # Docker infrastructure
└── configs/        # Configuration files (.env, pyproject.toml, etc.)
```

## Template Variables

All templates receive these variables:

```python
{
    "app_name": "task-api",
    "entities": [
        {
            "name": "Task",
            "snake_name": "task",
            "table_name": "tasks",
            "fields": [
                {
                    "name": "title",
                    "type": "str",
                    "constraints": {"min_length": 1, "max_length": 200},
                    "required": True
                },
                # ... more fields
            ]
        }
    ],
    "endpoints": [
        {"method": "POST", "path": "/tasks", "operation": "create"},
        # ... more endpoints
    ],
    "config": {
        "database": "postgresql",
        "async": True,
        "observability": True,
        "docker": True
    }
}
```

## Usage

Templates are rendered by `CodeGenerationService.generate_modular_app()`:

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates/production'))
template = env.get_template('core/config.py.j2')
rendered = template.render(app_name="task-api", ...)
```
