"""
Integration Test: Pattern-Based Code Generation

Tests the complete flow:
1. Populate pattern bank with templates
2. Generate code using patterns
3. Verify generated code quality

Usage:
    pytest tests/integration/test_pattern_based_generation.py -v
"""

import pytest
import asyncio
from pathlib import Path

from src.cognitive.patterns.pattern_bank import PatternBank
from src.services.pattern_based_generation import (
    PatternBasedGenerator,
    GenerationContext
)
from src.llm.claude_client import ClaudeClient
from src.cognitive.config.settings import settings


class TestPatternBasedGeneration:
    """Test pattern-based code generation."""

    @pytest.fixture(scope="class")
    def pattern_bank(self):
        """Setup pattern bank."""
        bank = PatternBank()
        bank.connect()
        return bank

    @pytest.fixture(scope="class")
    def llm_client(self):
        """Setup LLM client."""
        return ClaudeClient(api_key=settings.anthropic_api_key)

    @pytest.fixture(scope="class")
    def generator(self, pattern_bank, llm_client):
        """Setup pattern generator."""
        return PatternBasedGenerator(
            pattern_bank=pattern_bank,
            llm_client=llm_client,
            use_llm_adaptation=True
        )

    @pytest.fixture
    def context(self):
        """Sample generation context."""
        return GenerationContext(
            project_name="test_ecommerce_api",
            api_version="v1",
            python_version="3.11",
            database_url="postgresql+asyncpg://user:pass@localhost/testdb"
        )

    @pytest.mark.asyncio
    async def test_generate_dockerfile_from_pattern(self, generator, context):
        """Test Dockerfile generation using pattern bank."""
        # Generate
        dockerfile = await generator.generate_dockerfile(context)

        # Assertions
        assert dockerfile is not None
        assert len(dockerfile) > 0

        # Check key content
        assert "FROM python:3.11" in dockerfile
        assert "test_ecommerce_api" in dockerfile  # Project name substituted
        assert "WORKDIR /app" in dockerfile
        assert "COPY requirements.txt" in dockerfile
        assert "uvicorn" in dockerfile

        print("\n✅ Dockerfile generated successfully")
        print(f"Length: {len(dockerfile)} chars")
        print(f"Preview:\n{dockerfile[:200]}...")

    @pytest.mark.asyncio
    async def test_generate_docker_compose_from_pattern(self, generator, context):
        """Test Docker Compose generation using pattern bank."""
        # Generate
        docker_compose = await generator.generate_docker_compose(context)

        # Assertions
        assert docker_compose is not None
        assert "services:" in docker_compose
        assert "app:" in docker_compose
        assert "postgres:" in docker_compose
        assert "redis:" in docker_compose
        assert "prometheus:" in docker_compose
        assert "grafana:" in docker_compose

        # Check Docker networking (app:8000 not localhost:8000)
        assert "app:8000" in docker_compose
        assert "prometheus:9090" in docker_compose

        print("\n✅ Docker Compose generated successfully")
        print(f"Services found: app, postgres, redis, prometheus, grafana")

    @pytest.mark.asyncio
    async def test_generate_requirements_from_pattern(self, generator, context):
        """Test requirements.txt generation using pattern bank."""
        # Generate
        requirements = await generator.generate_requirements_txt(context)

        # Assertions
        assert requirements is not None
        assert "fastapi" in requirements
        assert "sqlalchemy" in requirements
        assert "asyncpg" in requirements
        assert "psycopg==3.2.12" in requirements  # Verified version
        assert "alembic" in requirements
        assert "prometheus-client" in requirements

        print("\n✅ requirements.txt generated successfully")
        print(f"Dependencies: {len(requirements.splitlines())} lines")

    @pytest.mark.asyncio
    async def test_generate_main_py_from_pattern(self, generator, context):
        """Test main.py generation using pattern bank."""
        # Generate
        main_py = await generator.generate_main_py(context)

        # Assertions
        assert main_py is not None
        assert "from fastapi import FastAPI" in main_py
        assert "app = FastAPI" in main_py
        assert "CORS" in main_py or "CORSMiddleware" in main_py
        assert "/health" in main_py or "health" in main_py
        assert "structlog" in main_py or "logger" in main_py

        print("\n✅ main.py generated successfully")
        print(f"Features: CORS, Health checks, Logging")

    @pytest.mark.asyncio
    async def test_generate_makefile_from_pattern(self, generator, context):
        """Test Makefile generation using pattern bank."""
        # Generate
        makefile = await generator.generate_makefile(context)

        # Assertions
        assert makefile is not None
        assert "test:" in makefile
        assert "run:" in makefile
        assert "docker-up:" in makefile or "docker" in makefile
        assert "migrate:" in makefile or "alembic" in makefile

        print("\n✅ Makefile generated successfully")
        print(f"Targets: test, run, docker, migrate")

    @pytest.mark.asyncio
    async def test_generate_prometheus_config_from_pattern(self, generator, context):
        """Test Prometheus config generation using pattern bank."""
        # Generate
        prometheus_yml = await generator.generate_prometheus_config(context)

        # Assertions
        assert prometheus_yml is not None
        assert "scrape_configs:" in prometheus_yml
        assert "app:8000" in prometheus_yml  # Docker service name, not localhost
        assert "/metrics" in prometheus_yml

        print("\n✅ Prometheus config generated successfully")
        print(f"Scrape target: app:8000")

    @pytest.mark.asyncio
    async def test_generate_metrics_route_from_pattern(self, generator, context):
        """Test metrics route generation using pattern bank."""
        # Generate
        metrics_route = await generator.generate_metrics_route(context)

        # Assertions
        assert metrics_route is not None
        assert "from prometheus_client import" in metrics_route
        assert "generate_latest" in metrics_route
        assert "/metrics" in metrics_route
        assert "from src.core.middleware import" in metrics_route  # Imports metrics

        print("\n✅ Metrics route generated successfully")
        print(f"Feature: Imports metrics from middleware (no duplication)")

    @pytest.mark.asyncio
    async def test_pattern_search_fallback(self, generator, context):
        """Test pattern search with fallback to LLM generation."""
        # Try to generate something not in pattern bank
        code = await generator.generate_from_pattern(
            purpose="Generate Kubernetes Helm chart for FastAPI application",
            context=context,
            domain="infrastructure",
            fallback_to_llm=True
        )

        # Assertions - should generate from scratch
        assert code is not None
        assert len(code) > 0

        print("\n✅ Fallback to LLM generation works")
        print(f"Generated: {len(code)} chars (from scratch)")

    @pytest.mark.asyncio
    async def test_simple_substitution_mode(self, pattern_bank, llm_client, context):
        """Test pattern generation with simple substitution (no LLM)."""
        # Create generator with substitution only
        generator = PatternBasedGenerator(
            pattern_bank=pattern_bank,
            llm_client=llm_client,
            use_llm_adaptation=False  # No LLM, just substitution
        )

        # Generate
        dockerfile = await generator.generate_dockerfile(context)

        # Assertions
        assert dockerfile is not None
        assert "test_ecommerce_api" in dockerfile  # Placeholder substituted
        assert "{{project_name}}" not in dockerfile  # No remaining placeholders

        print("\n✅ Simple substitution mode works")
        print(f"Mode: Placeholder substitution only (faster)")

    @pytest.mark.asyncio
    async def test_pattern_bank_metrics(self, pattern_bank):
        """Test pattern bank has patterns populated."""
        # Get metrics
        metrics = pattern_bank.get_pattern_metrics()

        # Assertions
        assert metrics["total_patterns"] > 0  # Should have patterns
        assert metrics["avg_success_rate"] >= 0.95  # High quality patterns

        print("\n📊 Pattern Bank Metrics:")
        print(f"   Total patterns: {metrics['total_patterns']}")
        print(f"   Avg success rate: {metrics['avg_success_rate']:.2%}")
        print(f"   Domains: {list(metrics['domain_distribution'].keys())}")

    @pytest.mark.asyncio
    async def test_generation_performance(self, generator, context):
        """Test generation performance (should be fast with patterns)."""
        import time

        start = time.time()

        # Generate multiple files
        dockerfile = await generator.generate_dockerfile(context)
        requirements = await generator.generate_requirements_txt(context)
        makefile = await generator.generate_makefile(context)

        elapsed = time.time() - start

        # Assertions
        assert dockerfile is not None
        assert requirements is not None
        assert makefile is not None
        assert elapsed < 30.0  # Should be fast (< 30 seconds for 3 files)

        print(f"\n⚡ Performance: Generated 3 files in {elapsed:.2f}s")


# Run specific tests
if __name__ == "__main__":
    import sys

    # Run tests
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto"] + sys.argv[1:])
