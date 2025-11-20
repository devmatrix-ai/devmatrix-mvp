"""
Debug script to see which patterns are retrieved but not mapped to files.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.cognitive.patterns.pattern_bank import PatternBank, SemanticTaskSignature
from src.cognitive.patterns.production_patterns import PRODUCTION_PATTERN_CATEGORIES


async def debug_pattern_retrieval():
    """Debug which patterns are retrieved and which are mapped."""

    # Initialize PatternBank
    bank = PatternBank()
    bank.connect()

    print("=" * 80)
    print("DEBUGGING PATTERN RETRIEVAL AND MAPPING")
    print("=" * 80)
    print()

    all_patterns = {}
    total_patterns = 0

    # Retrieve patterns for each category (same as _retrieve_production_patterns)
    for category, config in PRODUCTION_PATTERN_CATEGORIES.items():
        query_sig = SemanticTaskSignature(
            purpose=f"production ready {category} implementation",
            intent="implement",
            inputs={},
            outputs={},
            domain=config["domain"],
        )

        category_patterns = bank.hybrid_search(
            signature=query_sig,
            domain=config["domain"],
            production_ready=True,
            top_k=3,
        )

        # Filter by success threshold
        filtered_patterns = [
            p for p in category_patterns
            if p.success_rate >= config["success_threshold"]
        ]

        all_patterns[category] = filtered_patterns
        total_patterns += len(filtered_patterns)

        print(f"📁 Category: {category}")
        print(f"   Domain: {config['domain']}")
        print(f"   Retrieved: {len(category_patterns)} patterns")
        print(f"   After filtering: {len(filtered_patterns)} patterns")

        if filtered_patterns:
            print(f"   Patterns:")
            for i, p in enumerate(filtered_patterns, 1):
                print(f"      {i}. {p.signature.purpose[:70]}")
                print(f"         Success rate: {p.success_rate}")
                print(f"         Domain: {p.signature.domain}")
        print()

    print("=" * 80)
    print(f"TOTAL PATTERNS RETRIEVED: {total_patterns}")
    print("=" * 80)
    print()

    # Now check which patterns would be mapped by current logic
    print("=" * 80)
    print("CHECKING WHICH PATTERNS WOULD BE MAPPED")
    print("=" * 80)
    print()

    mapped_count = 0
    unmapped_patterns = []

    for category, patterns in all_patterns.items():
        print(f"📁 Category: {category} ({len(patterns)} patterns)")

        for p in patterns:
            purpose_lower = p.signature.purpose.lower()
            would_map = False
            mapped_to = None

            # Check if this pattern would be mapped (simulate _compose_category_patterns logic)
            if category == "core_config":
                if "pydantic" in purpose_lower or "configuration" in purpose_lower:
                    would_map = True
                    mapped_to = "src/core/config.py"

            elif category == "database_async":
                if "sqlalchemy" in purpose_lower or "database" in purpose_lower:
                    would_map = True
                    mapped_to = "src/core/database.py"

            elif category == "observability":
                if "structured logging" in purpose_lower or "structlog" in purpose_lower:
                    would_map = True
                    mapped_to = "src/core/logging.py"
                elif "request id" in purpose_lower or "middleware" in purpose_lower:
                    would_map = True
                    mapped_to = "src/core/middleware.py"
                elif "exception" in purpose_lower or "global exception" in purpose_lower:
                    would_map = True
                    mapped_to = "src/core/exception_handlers.py"
                elif "health check" in purpose_lower or "readiness" in purpose_lower:
                    would_map = True
                    mapped_to = "src/api/routes/health.py"
                elif "metrics" in purpose_lower or "prometheus" in purpose_lower:
                    would_map = True
                    mapped_to = "src/api/routes/metrics.py"

            elif category == "models_pydantic":
                if "pydantic" in purpose_lower or "schema" in purpose_lower:
                    would_map = True
                    mapped_to = "src/models/schemas.py"

            elif category == "models_sqlalchemy":
                if "sqlalchemy" in purpose_lower or "orm" in purpose_lower:
                    would_map = True
                    mapped_to = "src/models/entities.py"

            elif category == "repository_pattern":
                if "repository" in purpose_lower or "crud" in purpose_lower:
                    would_map = True
                    mapped_to = "src/repositories/{entity}_repository.py"

            elif category == "business_logic":
                if "service" in purpose_lower or "business logic" in purpose_lower:
                    would_map = True
                    mapped_to = "src/services/{entity}_service.py"

            elif category == "api_routes":
                if "fastapi" in purpose_lower or "crud" in purpose_lower or "endpoint" in purpose_lower:
                    would_map = True
                    mapped_to = "src/api/routes/{entity}.py"

            elif category == "security_hardening":
                if "security" in purpose_lower or "sanitization" in purpose_lower:
                    would_map = True
                    mapped_to = "src/core/security.py"

            elif category == "test_infrastructure":
                if "pytest fixtures" in purpose_lower or "conftest" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/conftest.py"
                elif "test data factories" in purpose_lower or "factories" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/factories.py"
                elif "unit tests for pydantic" in purpose_lower or "test_models" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/unit/test_models.py"
                elif "unit tests for repository" in purpose_lower or "test_repositories" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/unit/test_repositories.py"
                elif "unit tests for service" in purpose_lower or "test_services" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/unit/test_services.py"
                elif "integration tests" in purpose_lower or "test_api" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/integration/test_api.py"
                elif "tests for logging" in purpose_lower or "observability" in purpose_lower:
                    would_map = True
                    mapped_to = "tests/test_observability.py"

            elif category == "docker_infrastructure":
                if "multi-stage docker" in purpose_lower or "dockerfile" in purpose_lower:
                    would_map = True
                    mapped_to = "docker/Dockerfile"
                elif "full stack docker-compose" in purpose_lower and "test" not in purpose_lower:
                    would_map = True
                    mapped_to = "docker/docker-compose.yml"
                elif "test environment" in purpose_lower or "docker-compose.test" in purpose_lower:
                    would_map = True
                    mapped_to = "docker/docker-compose.test.yml"
                elif "prometheus scrape" in purpose_lower or "prometheus.yml" in purpose_lower:
                    would_map = True
                    mapped_to = "docker/prometheus.yml"
                # Add more docker patterns...

            elif category == "project_config":
                if "pyproject" in purpose_lower or "toml" in purpose_lower:
                    would_map = True
                    mapped_to = "pyproject.toml"
                elif "env" in purpose_lower and "example" in purpose_lower:
                    would_map = True
                    mapped_to = ".env.example"
                elif "gitignore" in purpose_lower:
                    would_map = True
                    mapped_to = ".gitignore"
                elif "makefile" in purpose_lower:
                    would_map = True
                    mapped_to = "Makefile"
                # Add more config patterns...

            if would_map:
                mapped_count += 1
                print(f"   ✅ MAPPED: {p.signature.purpose[:60]}")
                print(f"      → {mapped_to}")
            else:
                unmapped_patterns.append((category, p))
                print(f"   ❌ NOT MAPPED: {p.signature.purpose[:60]}")

        print()

    print("=" * 80)
    print(f"SUMMARY")
    print("=" * 80)
    print(f"Total patterns retrieved: {total_patterns}")
    print(f"Patterns that would be mapped: {mapped_count}")
    print(f"Patterns NOT mapped: {len(unmapped_patterns)}")
    print()

    if unmapped_patterns:
        print("=" * 80)
        print("UNMAPPED PATTERNS (NEED ATTENTION)")
        print("=" * 80)
        for category, p in unmapped_patterns:
            print(f"Category: {category}")
            print(f"Purpose: {p.signature.purpose}")
            print(f"Domain: {p.signature.domain}")
            print(f"Success rate: {p.success_rate}")
            print()


if __name__ == "__main__":
    asyncio.run(debug_pattern_retrieval())
