#!/usr/bin/env python3
"""
Populate Pattern Bank with Production Templates

Migrates hardcoded templates from code_generation_service.py to semantic patterns
in the pattern bank for dynamic retrieval during code generation.

Usage:
    python scripts/populate_template_patterns.py
"""

import logging
from typing import Dict, List
from datetime import datetime

from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.services.code_generation_service import CodeGenerationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TemplatePatternPopulator:
    """
    Populates pattern bank with production templates.

    Converts hardcoded templates into searchable patterns that the LLM can
    retrieve and adapt during code generation.
    """

    def __init__(self):
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()

        # Initialize code generation service to extract templates
        self.code_gen = CodeGenerationService(
            pattern_bank=None,  # Don't need pattern bank for extraction
            llm_client=None
        )

    def populate_all(self):
        """Populate all template patterns."""
        logger.info("🚀 Starting template pattern population...")

        # Infrastructure patterns
        self._populate_docker_patterns()
        self._populate_config_patterns()
        self._populate_build_patterns()

        # Code patterns
        self._populate_core_code_patterns()
        self._populate_route_patterns()

        # Documentation patterns
        self._populate_documentation_patterns()

        logger.info("✅ Template pattern population completed!")

    def _populate_docker_patterns(self):
        """Populate Docker infrastructure patterns."""
        logger.info("📦 Populating Docker patterns...")

        # 1. Dockerfile pattern
        dockerfile_signature = SemanticTaskSignature(
            purpose="Generate production-ready Dockerfile for FastAPI application",
            intent="create",
            inputs={"framework": "FastAPI", "python_version": "3.11"},
            outputs={"file": "Dockerfile"},
            domain="infrastructure"
        )

        # Get template from code generation service
        spec_requirements = {
            "project_name": "{{project_name}}",
            "api_version": "v1"
        }
        dockerfile_code = self.code_gen._generate_dockerfile(spec_requirements)

        # Store as pattern with template placeholders
        pattern_id = self.pattern_bank.store_production_pattern(
            signature=dockerfile_signature,
            code=dockerfile_code,
            success_rate=0.98,  # High success rate for production templates
            test_coverage=0.90,
            security_level="HIGH",
            observability_complete=True,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored Dockerfile pattern: {pattern_id}")

        # 2. Docker Compose pattern
        docker_compose_signature = SemanticTaskSignature(
            purpose="Generate Docker Compose configuration with PostgreSQL, Redis, Prometheus, Grafana",
            intent="create",
            inputs={"services": ["app", "db", "redis", "prometheus", "grafana"]},
            outputs={"file": "docker/docker-compose.yml"},
            domain="infrastructure"
        )

        docker_compose_code = self.code_gen._generate_docker_compose(spec_requirements)

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=docker_compose_signature,
            code=docker_compose_code,
            success_rate=0.98,
            test_coverage=0.90,
            security_level="HIGH",
            observability_complete=True,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored Docker Compose pattern: {pattern_id}")

        # 3. Prometheus Config pattern
        prometheus_signature = SemanticTaskSignature(
            purpose="Generate Prometheus scrape configuration for FastAPI metrics",
            intent="create",
            inputs={"target": "app:8000", "scrape_interval": "15s"},
            outputs={"file": "docker/prometheus.yml"},
            domain="infrastructure"
        )

        prometheus_code = self.code_gen._generate_prometheus_config()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=prometheus_signature,
            code=prometheus_code,
            success_rate=0.98,
            test_coverage=0.85,
            security_level="MEDIUM",
            observability_complete=True,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored Prometheus config pattern: {pattern_id}")

        # 4. Grafana Dashboard Provider
        grafana_dashboard_signature = SemanticTaskSignature(
            purpose="Generate Grafana dashboard provider configuration",
            intent="create",
            inputs={"dashboard_path": "/var/lib/grafana/dashboards"},
            outputs={"file": "docker/grafana/provisioning/dashboards/dashboard-provider.yml"},
            domain="infrastructure"
        )

        grafana_dashboard_code = self.code_gen._generate_grafana_dashboard_provider()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=grafana_dashboard_signature,
            code=grafana_dashboard_code,
            success_rate=0.98,
            test_coverage=0.85,
            security_level="MEDIUM",
            observability_complete=True,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored Grafana dashboard provider pattern: {pattern_id}")

        # 5. Grafana Prometheus Datasource
        grafana_datasource_signature = SemanticTaskSignature(
            purpose="Generate Grafana Prometheus datasource configuration",
            intent="create",
            inputs={"prometheus_url": "http://prometheus:9090"},
            outputs={"file": "docker/grafana/provisioning/datasources/prometheus.yml"},
            domain="infrastructure"
        )

        grafana_datasource_code = self.code_gen._generate_grafana_prometheus_datasource()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=grafana_datasource_signature,
            code=grafana_datasource_code,
            success_rate=0.98,
            test_coverage=0.85,
            security_level="MEDIUM",
            observability_complete=True,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored Grafana datasource pattern: {pattern_id}")

    def _populate_config_patterns(self):
        """Populate configuration file patterns."""
        logger.info("⚙️  Populating configuration patterns...")

        # 1. Alembic INI
        alembic_ini_signature = SemanticTaskSignature(
            purpose="Generate Alembic configuration for database migrations with dual-driver support",
            intent="create",
            inputs={"db_url": "postgresql+asyncpg://", "migration_dir": "alembic/versions"},
            outputs={"file": "alembic.ini"},
            domain="infrastructure"
        )

        spec_requirements = {"project_name": "{{project_name}}"}
        alembic_ini_code = self.code_gen._generate_alembic_ini(spec_requirements)

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=alembic_ini_signature,
            code=alembic_ini_code,
            success_rate=0.98,
            test_coverage=0.90,
            security_level="MEDIUM",
            observability_complete=False,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored Alembic INI pattern: {pattern_id}")

        # 2. .env.example
        env_example_signature = SemanticTaskSignature(
            purpose="Generate .env.example template with all environment variables",
            intent="create",
            inputs={"variables": ["DATABASE_URL", "REDIS_URL", "LOG_LEVEL"]},
            outputs={"file": ".env.example"},
            domain="infrastructure"
        )

        env_example_code = self.code_gen._generate_env_example()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=env_example_signature,
            code=env_example_code,
            success_rate=0.98,
            test_coverage=0.85,
            security_level="HIGH",
            observability_complete=False,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored .env.example pattern: {pattern_id}")

        # 3. .gitignore
        gitignore_signature = SemanticTaskSignature(
            purpose="Generate comprehensive .gitignore for Python FastAPI project",
            intent="create",
            inputs={"language": "Python", "framework": "FastAPI"},
            outputs={"file": ".gitignore"},
            domain="infrastructure"
        )

        gitignore_code = self.code_gen._generate_gitignore()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=gitignore_signature,
            code=gitignore_code,
            success_rate=0.98,
            test_coverage=0.80,
            security_level="MEDIUM",
            observability_complete=False,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored .gitignore pattern: {pattern_id}")

        # 4. pyproject.toml
        pyproject_signature = SemanticTaskSignature(
            purpose="Generate pyproject.toml for Poetry package management",
            intent="create",
            inputs={"package_manager": "poetry", "python_version": "^3.11"},
            outputs={"file": "pyproject.toml"},
            domain="infrastructure"
        )

        pyproject_code = self.code_gen._generate_pyproject_toml(spec_requirements)

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=pyproject_signature,
            code=pyproject_code,
            success_rate=0.98,
            test_coverage=0.85,
            security_level="MEDIUM",
            observability_complete=False,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored pyproject.toml pattern: {pattern_id}")

    def _populate_build_patterns(self):
        """Populate build and dependency patterns."""
        logger.info("🔨 Populating build patterns...")

        # 1. Makefile
        makefile_signature = SemanticTaskSignature(
            purpose="Generate Makefile with common development commands (test, run, migrate, docker)",
            intent="create",
            inputs={"commands": ["test", "run", "migrate", "docker-up", "docker-down"]},
            outputs={"file": "Makefile"},
            domain="infrastructure"
        )

        makefile_code = self.code_gen._generate_makefile()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=makefile_signature,
            code=makefile_code,
            success_rate=0.98,
            test_coverage=0.80,
            security_level="LOW",
            observability_complete=False,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored Makefile pattern: {pattern_id}")

        # 2. requirements.txt (hardcoded with verified versions)
        requirements_signature = SemanticTaskSignature(
            purpose="Generate requirements.txt with verified PyPI versions for production FastAPI app",
            intent="create",
            inputs={
                "dependencies": ["fastapi", "sqlalchemy", "asyncpg", "psycopg", "alembic"],
                "verified_versions": True
            },
            outputs={"file": "requirements.txt"},
            domain="infrastructure"
        )

        requirements_code = self.code_gen._generate_requirements_hardcoded()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=requirements_signature,
            code=requirements_code,
            success_rate=0.98,
            test_coverage=0.95,
            security_level="HIGH",
            observability_complete=False,
            docker_ready=True
        )

        logger.info(f"  ✅ Stored requirements.txt pattern: {pattern_id}")

    def _populate_core_code_patterns(self):
        """Populate core code patterns."""
        logger.info("💻 Populating core code patterns...")

        # 1. main.py (FastAPI app entrypoint)
        main_py_signature = SemanticTaskSignature(
            purpose="Generate FastAPI main.py with CORS, middleware, health checks, and metrics",
            intent="create",
            inputs={
                "framework": "FastAPI",
                "features": ["CORS", "logging", "metrics", "health_checks"]
            },
            outputs={"file": "src/main.py"},
            domain="code"
        )

        spec_requirements = {"project_name": "{{project_name}}"}
        main_py_code = self.code_gen._generate_main_py(spec_requirements)

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=main_py_signature,
            code=main_py_code,
            success_rate=0.98,
            test_coverage=0.90,
            security_level="HIGH",
            observability_complete=True,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored main.py pattern: {pattern_id}")

        # 2. Alembic env.py
        alembic_env_signature = SemanticTaskSignature(
            purpose="Generate Alembic env.py with async support and dual-driver compatibility",
            intent="create",
            inputs={"async_support": True, "drivers": ["asyncpg", "psycopg"]},
            outputs={"file": "alembic/env.py"},
            domain="code"
        )

        alembic_env_code = self.code_gen._generate_alembic_env(spec_requirements)

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=alembic_env_signature,
            code=alembic_env_code,
            success_rate=0.98,
            test_coverage=0.90,
            security_level="MEDIUM",
            observability_complete=True,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored Alembic env.py pattern: {pattern_id}")

        # 3. Alembic script template
        alembic_script_signature = SemanticTaskSignature(
            purpose="Generate Alembic migration script template with upgrade/downgrade functions",
            intent="create",
            inputs={"template_type": "migration", "revision_type": "standard"},
            outputs={"file": "alembic/script.py.mako"},
            domain="code"
        )

        alembic_script_code = self.code_gen._generate_alembic_script_template()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=alembic_script_signature,
            code=alembic_script_code,
            success_rate=0.98,
            test_coverage=0.85,
            security_level="MEDIUM",
            observability_complete=False,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored Alembic script template pattern: {pattern_id}")

    def _populate_route_patterns(self):
        """Populate API route patterns."""
        logger.info("🛤️  Populating route patterns...")

        # 1. Metrics route (Prometheus)
        metrics_route_signature = SemanticTaskSignature(
            purpose="Generate Prometheus metrics route that imports metrics from middleware",
            intent="create",
            inputs={"metrics_source": "middleware", "endpoint": "/metrics"},
            outputs={"file": "src/api/routes/metrics.py"},
            domain="code"
        )

        metrics_route_code = self.code_gen._generate_metrics_route()

        pattern_id = self.pattern_bank.store_production_pattern(
            signature=metrics_route_signature,
            code=metrics_route_code,
            success_rate=0.98,
            test_coverage=0.90,
            security_level="LOW",
            observability_complete=True,
            docker_ready=False
        )

        logger.info(f"  ✅ Stored metrics route pattern: {pattern_id}")

    def _populate_documentation_patterns(self):
        """Populate documentation patterns."""
        logger.info("📚 Populating documentation patterns...")

        # Note: README generation is async and uses LLM,
        # so we'll skip it for now or handle separately
        logger.info("  ⏭️  Skipping README pattern (requires async LLM generation)")


def main():
    """Main entry point."""
    populator = TemplatePatternPopulator()
    populator.populate_all()

    # Show pattern bank stats
    metrics = populator.pattern_bank.get_pattern_metrics()
    logger.info(f"\n📊 Pattern Bank Metrics:")
    logger.info(f"   Total patterns: {metrics['total_patterns']}")
    logger.info(f"   Avg success rate: {metrics['avg_success_rate']:.2%}")
    logger.info(f"   Domain distribution: {metrics['domain_distribution']}")


if __name__ == "__main__":
    main()
