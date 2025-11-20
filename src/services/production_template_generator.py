"""
Production Template Generator

Renders all production-ready templates from /templates/production/
Implements Task Groups 3-7:
- Task Group 3: Observability (logging, middleware, health, metrics)
- Task Group 4: Testing (pytest, fixtures, unit/integration tests)
- Task Group 5: Security (sanitization, rate limiting)
- Task Group 6: Docker (Dockerfile, docker-compose, Prometheus, Grafana)
- Task Group 7: CI/CD (.gitignore, pytest.ini, Makefile)

Author: System Architect
Date: 2025-11-20
"""

import os
from pathlib import Path
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader, Template
import structlog

logger = structlog.get_logger(__name__)


class ProductionTemplateGenerator:
    """
    Generates production-ready files from Jinja2 templates.

    Complements ModularArchitectureGenerator (Task Group 2) by adding:
    - Observability infrastructure
    - Complete test suite
    - Security hardening
    - Docker infrastructure
    - CI/CD configuration
    """

    def __init__(self):
        """Initialize Jinja2 environment with production templates"""
        # Get template directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.template_dir = project_root / "templates" / "production"

        if not self.template_dir.exists():
            logger.error("Template directory not found", path=str(self.template_dir))
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # Don't escape Python code
            trim_blocks=True,
            lstrip_blocks=True
        )

        logger.info("Production template generator initialized", template_dir=str(self.template_dir))

    def generate_production_files(self, spec_requirements) -> Dict[str, str]:
        """
        Generate all production-ready files from templates.

        Args:
            spec_requirements: SpecRequirements object from parser

        Returns:
            Dict[file_path, file_content] for all generated files
        """
        files = {}

        # Extract context variables from spec_requirements
        context = self._build_template_context(spec_requirements)

        # 1. Task Group 3: Observability
        files.update(self._generate_observability_files(context))

        # 2. Task Group 4: Testing
        files.update(self._generate_test_files(context, spec_requirements))

        # 3. Task Group 5: Security
        files.update(self._generate_security_files(context))

        # 4. Task Group 6: Docker
        files.update(self._generate_docker_files(context))

        # 5. Task Group 7: Configuration files
        files.update(self._generate_config_files(context))

        logger.info("Production files generated from templates", file_count=len(files))
        return files

    def _build_template_context(self, spec_requirements) -> Dict:
        """Build context dictionary for template rendering"""
        # Extract metadata
        app_name = spec_requirements.metadata.get('spec_name', 'FastAPI Application')

        # Get entities
        entities = []
        for entity in spec_requirements.entities:
            entities.append({
                'name': entity.name,
                'snake_name': entity.snake_name,
                'fields': [
                    {
                        'name': field.name,
                        'type': field.type,
                        'required': field.required,
                        'default': field.default
                    }
                    for field in entity.fields
                ]
            })

        return {
            'app_name': app_name,
            'entities': entities,
            'has_entities': len(entities) > 0,
            'first_entity': entities[0] if entities else None
        }

    def _generate_observability_files(self, context: Dict) -> Dict[str, str]:
        """Generate Task Group 3: Observability files"""
        files = {}

        # Core observability
        files['src/core/logging.py'] = self._render_template('core/logging.py.j2', context)
        files['src/core/middleware.py'] = self._render_template('core/middleware.py.j2', context)
        files['src/core/exception_handlers.py'] = self._render_template('core/exception_handlers.py.j2', context)

        # Health and metrics endpoints
        files['src/api/health.py'] = self._render_template('api/health.py.j2', context)
        files['src/api/metrics.py'] = self._render_template('api/metrics.py.j2', context)

        logger.debug("Generated observability files", count=len(files))
        return files

    def _generate_test_files(self, context: Dict, spec_requirements) -> Dict[str, str]:
        """Generate Task Group 4: Test suite"""
        files = {}

        # Test configuration
        files['tests/__init__.py'] = ''
        files['tests/conftest.py'] = self._render_template('tests/conftest.py.j2', context)
        files['tests/factories.py'] = self._render_template('tests/factories.py.j2', context)
        files['tests/test_observability.py'] = self._render_template('tests/test_observability.py.j2', context)

        # Unit tests
        files['tests/unit/__init__.py'] = ''
        files['tests/unit/test_models.py'] = self._render_template('tests/unit/test_models.py.j2', context)
        files['tests/unit/test_repositories.py'] = self._render_template('tests/unit/test_repositories.py.j2', context)
        files['tests/unit/test_services.py'] = self._render_template('tests/unit/test_services.py.j2', context)

        # Integration tests
        files['tests/integration/__init__.py'] = ''
        files['tests/integration/test_api.py'] = self._render_template('tests/integration/test_api.py.j2', context)

        # Pytest configuration
        files['pytest.ini'] = self._generate_pytest_ini()
        files['.coveragerc'] = self._generate_coveragerc()

        logger.debug("Generated test files", count=len(files))
        return files

    def _generate_security_files(self, context: Dict) -> Dict[str, str]:
        """Generate Task Group 5: Security files"""
        files = {}

        files['src/core/security.py'] = self._render_template('core/security.py.j2', context)

        logger.debug("Generated security files", count=len(files))
        return files

    def _generate_docker_files(self, context: Dict) -> Dict[str, str]:
        """Generate Task Group 6: Docker infrastructure"""
        files = {}

        # Docker core files
        files['Dockerfile'] = self._render_template('docker/Dockerfile.j2', context)
        files['docker-compose.yml'] = self._render_template('docker/docker-compose.yml.j2', context)
        files['docker-compose.test.yml'] = self._render_template('docker/docker-compose.test.yml.j2', context)
        files['.dockerignore'] = self._render_template('docker/.dockerignore.j2', context)

        # Prometheus
        files['prometheus.yml'] = self._render_template('docker/prometheus.yml.j2', context)

        # Grafana
        files['grafana/dashboards/app-metrics.json'] = self._render_template('docker/grafana/dashboards/app-metrics.json.j2', context)
        files['grafana/dashboards/dashboard-provider.yml'] = self._render_template('docker/grafana/dashboards/dashboard-provider.yml.j2', context)
        files['grafana/datasources/prometheus.yml'] = self._render_template('docker/grafana/datasources/prometheus.yml.j2', context)

        # Docker documentation
        files['DOCKER_README.md'] = self._render_template('docker/README.md.j2', context)
        files['TROUBLESHOOTING.md'] = self._render_template('docker/TROUBLESHOOTING.md.j2', context)
        files['VALIDATION_CHECKLIST.md'] = self._render_template('docker/VALIDATION_CHECKLIST.md.j2', context)
        files['validate-docker-setup.sh'] = self._render_template('docker/validate-docker-setup.sh.j2', context)

        logger.debug("Generated docker files", count=len(files))
        return files

    def _generate_config_files(self, context: Dict) -> Dict[str, str]:
        """Generate Task Group 7: CI/CD and configuration files"""
        files = {}

        # Git
        files['.gitignore'] = self._generate_gitignore()

        # Pre-commit hooks
        files['.pre-commit-config.yaml'] = self._generate_precommit_config()

        # Makefile
        files['Makefile'] = self._generate_makefile()

        # Alembic
        files['alembic.ini'] = self._generate_alembic_ini()

        # GitHub Actions
        files['.github/workflows/ci.yml'] = self._generate_github_actions_ci()

        logger.debug("Generated config files", count=len(files))
        return files

    def _render_template(self, template_path: str, context: Dict) -> str:
        """Render a Jinja2 template with context"""
        try:
            template = self.jinja_env.get_template(template_path)
            return template.render(**context)
        except Exception as e:
            logger.error(
                "Failed to render template",
                template=template_path,
                error=str(e),
                exc_info=True
            )
            raise

    def _generate_pytest_ini(self) -> str:
        """Generate pytest.ini configuration"""
        return """[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
"""

    def _generate_coveragerc(self) -> str:
        """Generate .coveragerc configuration"""
        return """[run]
source = src
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */alembic/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
"""

    def _generate_gitignore(self) -> str:
        """Generate .gitignore file"""
        return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.hypothesis/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# OS
.DS_Store
Thumbs.db

# Alembic
alembic/versions/*.pyc
"""

    def _generate_precommit_config(self) -> str:
        """Generate .pre-commit-config.yaml"""
        return """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=100", "--extend-ignore=E203,W503"]
"""

    def _generate_makefile(self) -> str:
        """Generate Makefile with common commands"""
        return """# Makefile for FastAPI Application

.PHONY: help install test lint format run docker-up docker-down clean

help:
\t@echo "Available commands:"
\t@echo "  make install      - Install dependencies"
\t@echo "  make test        - Run tests with coverage"
\t@echo "  make lint        - Run linting checks"
\t@echo "  make format      - Format code with black/isort"
\t@echo "  make run         - Run application locally"
\t@echo "  make docker-up   - Start Docker services"
\t@echo "  make docker-down - Stop Docker services"
\t@echo "  make clean       - Remove cache files"

install:
\tpip install -r requirements.txt
\tpip install -r requirements-dev.txt

test:
\tpytest

lint:
\tflake8 src tests
\tmypy src

format:
\tblack src tests
\tisort src tests

run:
\tuvicorn src.main:app --reload

docker-up:
\tdocker-compose up -d

docker-down:
\tdocker-compose down

clean:
\tfind . -type d -name __pycache__ -exec rm -rf {} +
\tfind . -type f -name "*.pyc" -delete
\trm -rf .pytest_cache .coverage htmlcov
"""

    def _generate_alembic_ini(self) -> str:
        """Generate alembic.ini configuration"""
        return """[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

    def _generate_github_actions_ci(self) -> str:
        """Generate .github/workflows/ci.yml"""
        return """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          flake8 src tests
          black --check src tests
          isort --check-only src tests

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
        run: |
          pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
"""
