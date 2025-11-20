"""
Populate PatternBank with Production-Ready Patterns

Reads Jinja2 templates from /templates/production/ and stores them as
production-ready patterns in PatternBank (Qdrant).

Implements Task Group 8 pattern storage.

Usage:
    python tools/populate_production_patterns.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cognitive.patterns.pattern_bank import PatternBank, SemanticTaskSignature


def populate_patterns():
    """Populate PatternBank with all production templates"""

    # Initialize PatternBank
    bank = PatternBank()
    bank.connect()

    project_root = Path(__file__).parent.parent
    template_dir = project_root / "templates" / "production"

    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}")
        return

    print(f"📂 Reading templates from: {template_dir}")

    # Define pattern mappings: (template_path, signature, metadata)
    patterns = [
        # Task Group 3: Observability
        {
            "file": "core/logging.py.j2",
            "purpose": "Structured logging configuration with structlog and JSON output",
            "intent": "Configure structured logging with context variables for production observability",
            "domain": "observability",
            "success_rate": 0.98,
            "test_coverage": 0.90,
            "security_level": "MEDIUM",
            "observability_complete": True,
        },
        {
            "file": "core/middleware.py.j2",
            "purpose": "Request ID middleware for distributed tracing",
            "intent": "Generate and track request IDs across service boundaries",
            "domain": "observability",
            "success_rate": 0.98,
            "test_coverage": 0.85,
            "security_level": "MEDIUM",
            "observability_complete": True,
        },
        {
            "file": "core/exception_handlers.py.j2",
            "purpose": "Global exception handler with structured logging",
            "intent": "Catch and log all unhandled exceptions with full context",
            "domain": "observability",
            "success_rate": 0.97,
            "test_coverage": 0.80,
            "security_level": "HIGH",
            "observability_complete": True,
        },
        {
            "file": "api/health.py.j2",
            "purpose": "Health check and readiness endpoints",
            "intent": "Provide /health and /ready endpoints for Kubernetes probes",
            "domain": "observability",
            "success_rate": 0.99,
            "test_coverage": 0.95,
            "security_level": "LOW",
            "observability_complete": True,
        },
        {
            "file": "api/metrics.py.j2",
            "purpose": "Prometheus metrics endpoint with business metrics",
            "intent": "Expose /metrics endpoint with HTTP and business metrics",
            "domain": "observability",
            "success_rate": 0.97,
            "test_coverage": 0.85,
            "security_level": "LOW",
            "observability_complete": True,
        },

        # Task Group 4: Testing
        {
            "file": "tests/conftest.py.j2",
            "purpose": "Pytest fixtures for database and client testing",
            "intent": "Provide reusable test fixtures with proper cleanup",
            "domain": "testing",
            "success_rate": 0.98,
            "test_coverage": 1.0,
            "security_level": "LOW",
            "observability_complete": False,
        },
        {
            "file": "tests/factories.py.j2",
            "purpose": "Test data factories for entities",
            "intent": "Generate realistic test data with customizable attributes",
            "domain": "testing",
            "success_rate": 0.97,
            "test_coverage": 0.90,
            "security_level": "LOW",
            "observability_complete": False,
        },
        {
            "file": "tests/unit/test_models.py.j2",
            "purpose": "Unit tests for Pydantic schemas",
            "intent": "Test schema validation, strict mode, and type coercion",
            "domain": "testing",
            "success_rate": 0.96,
            "test_coverage": 0.95,
            "security_level": "LOW",
            "observability_complete": False,
        },
        {
            "file": "tests/unit/test_repositories.py.j2",
            "purpose": "Unit tests for repository CRUD operations",
            "intent": "Test data access layer with mocked database",
            "domain": "testing",
            "success_rate": 0.95,
            "test_coverage": 0.90,
            "security_level": "LOW",
            "observability_complete": False,
        },
        {
            "file": "tests/unit/test_services.py.j2",
            "purpose": "Unit tests for service business logic",
            "intent": "Test service layer with mocked repositories",
            "domain": "testing",
            "success_rate": 0.95,
            "test_coverage": 0.85,
            "security_level": "LOW",
            "observability_complete": False,
        },
        {
            "file": "tests/integration/test_api.py.j2",
            "purpose": "Integration tests for API endpoints",
            "intent": "Test complete request/response cycle with real database",
            "domain": "testing",
            "success_rate": 0.95,
            "test_coverage": 0.80,
            "security_level": "MEDIUM",
            "observability_complete": False,
        },
        {
            "file": "tests/test_observability.py.j2",
            "purpose": "Tests for logging, metrics, and health checks",
            "intent": "Verify observability infrastructure works correctly",
            "domain": "testing",
            "success_rate": 0.96,
            "test_coverage": 0.90,
            "security_level": "LOW",
            "observability_complete": True,
        },

        # Task Group 5: Security
        {
            "file": "core/security.py.j2",
            "purpose": "Security utilities for HTML sanitization and rate limiting",
            "intent": "Prevent XSS attacks and rate limit abuse",
            "domain": "security",
            "success_rate": 0.98,
            "test_coverage": 0.90,
            "security_level": "CRITICAL",
            "observability_complete": False,
        },

        # Task Group 6: Docker
        {
            "file": "docker/Dockerfile.j2",
            "purpose": "Multi-stage Docker image with security best practices",
            "intent": "Build optimized production Docker image",
            "domain": "infrastructure",
            "success_rate": 0.97,
            "test_coverage": 0.70,
            "security_level": "HIGH",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/docker-compose.yml.j2",
            "purpose": "Full stack docker-compose with app, database, monitoring",
            "intent": "Orchestrate all services (app, PostgreSQL, Redis, Prometheus, Grafana)",
            "domain": "infrastructure",
            "success_rate": 0.96,
            "test_coverage": 0.60,
            "security_level": "MEDIUM",
            "observability_complete": True,
            "docker_ready": True,
        },
        {
            "file": "docker/docker-compose.test.yml.j2",
            "purpose": "Isolated test environment with docker-compose",
            "intent": "Run tests in containerized environment",
            "domain": "infrastructure",
            "success_rate": 0.95,
            "test_coverage": 0.85,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/prometheus.yml.j2",
            "purpose": "Prometheus scrape configuration",
            "intent": "Configure Prometheus to scrape app metrics",
            "domain": "infrastructure",
            "success_rate": 0.98,
            "test_coverage": 0.50,
            "security_level": "LOW",
            "observability_complete": True,
            "docker_ready": True,
        },
        {
            "file": "docker/.dockerignore.j2",
            "purpose": "Docker build exclusions",
            "intent": "Exclude unnecessary files from Docker build context",
            "domain": "configuration",
            "success_rate": 0.99,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/grafana/dashboards/app-metrics.json.j2",
            "purpose": "Grafana dashboard for application metrics",
            "intent": "Visualize HTTP requests, duration, and business metrics",
            "domain": "infrastructure",
            "success_rate": 0.95,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": True,
            "docker_ready": True,
        },
        {
            "file": "docker/grafana/dashboards/dashboard-provider.yml.j2",
            "purpose": "Grafana dashboard provisioning configuration",
            "intent": "Auto-load dashboards on Grafana startup",
            "domain": "configuration",
            "success_rate": 0.98,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/grafana/datasources/prometheus.yml.j2",
            "purpose": "Grafana Prometheus datasource configuration",
            "intent": "Configure Prometheus as Grafana datasource",
            "domain": "configuration",
            "success_rate": 0.98,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/README.md.j2",
            "purpose": "Docker setup documentation",
            "intent": "Guide users through Docker deployment",
            "domain": "documentation",
            "success_rate": 0.99,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/TROUBLESHOOTING.md.j2",
            "purpose": "Docker troubleshooting guide",
            "intent": "Help users debug common Docker issues",
            "domain": "documentation",
            "success_rate": 0.98,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/VALIDATION_CHECKLIST.md.j2",
            "purpose": "Docker validation checklist",
            "intent": "Verify Docker setup is correct",
            "domain": "documentation",
            "success_rate": 0.99,
            "test_coverage": 0.0,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },
        {
            "file": "docker/validate-docker-setup.sh.j2",
            "purpose": "Docker setup validation script",
            "intent": "Automated Docker setup verification",
            "domain": "infrastructure",
            "success_rate": 0.97,
            "test_coverage": 0.70,
            "security_level": "LOW",
            "observability_complete": False,
            "docker_ready": True,
        },

        # Core templates (used by ModularArchitectureGenerator but also store as patterns)
        {
            "file": "core/config.py.j2",
            "purpose": "Pydantic settings configuration with environment variable support",
            "intent": "Type-safe configuration management with .env file support",
            "domain": "configuration",
            "success_rate": 0.99,
            "test_coverage": 0.85,
            "security_level": "MEDIUM",
            "observability_complete": False,
        },
        {
            "file": "core/database.py.j2",
            "purpose": "Async SQLAlchemy database connection and session management",
            "intent": "Configure async database engine with connection pooling",
            "domain": "data_access",
            "success_rate": 0.98,
            "test_coverage": 0.80,
            "security_level": "HIGH",
            "observability_complete": False,
        },
        {
            "file": "models/schemas.py.j2",
            "purpose": "Pydantic schemas for request/response validation",
            "intent": "Type-safe API contracts with strict validation",
            "domain": "data_modeling",
            "success_rate": 0.97,
            "test_coverage": 0.90,
            "security_level": "HIGH",
            "observability_complete": False,
        },
        {
            "file": "models/entities.py.j2",
            "purpose": "SQLAlchemy ORM models with timezone-aware timestamps",
            "intent": "Database table definitions with proper indexing",
            "domain": "data_modeling",
            "success_rate": 0.97,
            "test_coverage": 0.85,
            "security_level": "MEDIUM",
            "observability_complete": False,
        },
        {
            "file": "repositories/repository.py.j2",
            "purpose": "Repository pattern implementation for data access",
            "intent": "Async CRUD operations with proper error handling",
            "domain": "data_access",
            "success_rate": 0.96,
            "test_coverage": 0.85,
            "security_level": "MEDIUM",
            "observability_complete": False,
        },
        {
            "file": "services/service.py.j2",
            "purpose": "Service layer for business logic",
            "intent": "Business logic with entity-schema conversion",
            "domain": "business_logic",
            "success_rate": 0.95,
            "test_coverage": 0.80,
            "security_level": "MEDIUM",
            "observability_complete": False,
        },
        {
            "file": "main.py.j2",
            "purpose": "FastAPI application entry point with middleware and routes",
            "intent": "Initialize app with observability and security middleware",
            "domain": "application",
            "success_rate": 0.98,
            "test_coverage": 0.75,
            "security_level": "HIGH",
            "observability_complete": True,
        },
    ]

    stored_count = 0
    failed_count = 0

    for pattern_def in patterns:
        try:
            template_path = template_dir / pattern_def["file"]

            if not template_path.exists():
                print(f"⚠️  Template not found: {pattern_def['file']}")
                failed_count += 1
                continue

            # Read template content
            with open(template_path, 'r') as f:
                code = f.read()

            # Create signature
            signature = SemanticTaskSignature(
                purpose=pattern_def["purpose"],
                intent=pattern_def["intent"],
                domain=pattern_def["domain"],
            )

            # Store as production pattern
            pattern_id = bank.store_production_pattern(
                signature=signature,
                code=code,
                success_rate=pattern_def["success_rate"],
                test_coverage=pattern_def["test_coverage"],
                security_level=pattern_def["security_level"],
                observability_complete=pattern_def["observability_complete"],
                docker_ready=pattern_def.get("docker_ready", False),
            )

            print(f"✅ Stored: {pattern_def['file'][:60]} (id={pattern_id[:8]})")
            stored_count += 1

        except Exception as e:
            print(f"❌ Failed to store {pattern_def['file']}: {e}")
            failed_count += 1

    print(f"\n📊 Summary:")
    print(f"   ✅ Stored: {stored_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📦 Total: {len(patterns)}")


if __name__ == "__main__":
    populate_patterns()
