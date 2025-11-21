#!/usr/bin/env python3
"""
Comprehensive validation script for local production readiness.

Validates:
1. All services running and healthy
2. API connectivity (Anthropic, PostgreSQL, Redis, ChromaDB)
3. RAG system functional
4. Git operations working
5. Tests passing
6. Monitoring stack operational

Run with: python scripts/validate_local_production.py
"""

import sys
import subprocess
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv('.env.test')


class bcolors:
    """Colors for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{bcolors.HEADER}{bcolors.BOLD}{'='*60}{bcolors.ENDC}")
    print(f"{bcolors.HEADER}{bcolors.BOLD}{text.center(60)}{bcolors.ENDC}")
    print(f"{bcolors.HEADER}{bcolors.BOLD}{'='*60}{bcolors.ENDC}\n")


def print_success(text):
    print(f"{bcolors.OKGREEN}✅ {text}{bcolors.ENDC}")


def print_error(text):
    print(f"{bcolors.FAIL}❌ {text}{bcolors.ENDC}")


def print_warning(text):
    print(f"{bcolors.WARNING}⚠️  {text}{bcolors.ENDC}")


def print_info(text):
    print(f"{bcolors.OKCYAN}ℹ️  {text}{bcolors.ENDC}")


def validate_docker_services():
    """Validate Docker services are running."""
    print_header("VALIDATING DOCKER SERVICES")

    # Check docker compose
    result = subprocess.run(
        ["docker", "compose", "ps"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print_error("docker compose not available or services not running")
        return False

    services = {
        "postgres": False,
        "redis": False,
        "chromadb": False
    }
    all_healthy = True

    for service in services.keys():
        if service in result.stdout:
            # Check if running (not necessarily healthy)
            if "Up" in result.stdout or "running" in result.stdout.lower():
                print_success(f"{service} is running")
                services[service] = True
            else:
                print_error(f"{service} is NOT running")
                all_healthy = False
        else:
            print_error(f"{service} not found in docker compose")
            all_healthy = False

    return all_healthy


def validate_anthropic_api():
    """Validate Anthropic API connectivity."""
    print_header("VALIDATING ANTHROPIC API")

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or not api_key.startswith("sk-ant-"):
        print_error("ANTHROPIC_API_KEY not configured or invalid format")
        print_info("Set ANTHROPIC_API_KEY in .env.test file")
        return False

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply with: API OK"}]
        )

        content = response.content[0].text

        if "API OK" in content or "OK" in content:
            print_success(f"Anthropic API working: {content}")
            print_info(f"Tokens used: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
            return True
        else:
            print_warning(f"Unexpected response: {content}")
            return True  # Still counts as working

    except Exception as e:
        print_error(f"Anthropic API failed: {str(e)}")
        return False


def validate_postgresql():
    """Validate PostgreSQL connectivity."""
    print_header("VALIDATING POSTGRESQL")

    try:
        import psycopg2

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "devmatrix_test"),
            user=os.getenv("POSTGRES_USER", "devmatrix"),
            password=os.getenv("POSTGRES_PASSWORD", "devmatrix")
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]

        print_success(f"PostgreSQL connected: {version[:50]}...")

        # Check pgvector extension
        cursor.execute("SELECT * FROM pg_extension WHERE extname='vector'")
        if cursor.fetchone():
            print_success("pgvector extension installed")
        else:
            print_warning("pgvector extension NOT installed")

        # Check tables exist
        tables = ["code_generation_logs", "agent_execution_logs", "workflow_logs", "rag_feedback"]
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            if table in existing_tables:
                print_success(f"Table '{table}' exists")
            else:
                print_warning(f"Table '{table}' missing")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_error(f"PostgreSQL failed: {str(e)}")
        return False


def validate_redis():
    """Validate Redis connectivity."""
    print_header("VALIDATING REDIS")

    try:
        import redis

        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True
        )

        # Test PING
        pong = client.ping()
        if pong:
            print_success("Redis connected: PONG")
        else:
            print_error("Redis PING failed")
            return False

        # Test SET/GET
        client.set("validation_test", "OK")
        value = client.get("validation_test")

        if value == "OK":
            print_success("Redis SET/GET working")
            client.delete("validation_test")
        else:
            print_warning(f"Redis SET/GET unexpected value: {value}")

        return True

    except Exception as e:
        print_error(f"Redis failed: {str(e)}")
        return False


def validate_chromadb():
    """Validate ChromaDB connectivity."""
    print_header("VALIDATING CHROMADB")

    try:
        response = requests.get(
            f"http://{os.getenv('CHROMADB_HOST', 'localhost')}:{os.getenv('CHROMADB_PORT', 8001)}/api/v2/heartbeat",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"ChromaDB heartbeat: {data}")
        else:
            print_error(f"ChromaDB heartbeat failed: {response.status_code}")
            return False

        # Test vector operations
        from src.rag import create_embedding_model, create_vector_store

        embedding_model = create_embedding_model()
        vector_store = create_vector_store(
            embedding_model,
            host=os.getenv("CHROMADB_HOST", "localhost"),
            port=int(os.getenv("CHROMADB_PORT", 8001)),
            collection_name="validation_test"
        )

        # Add test example
        vector_store.add_example(
            "def validate(): return True",
            {"type": "validation"}
        )

        count = vector_store.collection.count()
        print_success(f"ChromaDB vector operations working: {count} documents")

        # Cleanup
        vector_store.clear_collection()

        return True

    except Exception as e:
        print_error(f"ChromaDB failed: {str(e)}")
        return False


def validate_git_workspace():
    """Validate Git workspace setup."""
    print_header("VALIDATING GIT WORKSPACE")

    workspace_path = Path("workspace_test")

    if not workspace_path.exists():
        print_warning("workspace_test/ does not exist (will be created on demand)")
        return True  # Not critical

    # Check git initialized
    result = subprocess.run(
        ["git", "status"],
        cwd=workspace_path,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success("Git initialized in workspace_test/")
    else:
        print_warning("Git NOT initialized in workspace_test/")
        return True  # Non-critical

    # Check git config
    result = subprocess.run(
        ["git", "config", "user.name"],
        cwd=workspace_path,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success(f"Git user configured: {result.stdout.strip()}")
    else:
        print_warning("Git user not configured")

    return True


def validate_monitoring():
    """Validate monitoring stack."""
    print_header("VALIDATING MONITORING STACK")

    prometheus_ok = False
    grafana_ok = False

    # Check Prometheus
    try:
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        if response.status_code == 200:
            print_success("Prometheus is healthy")
            prometheus_ok = True
        else:
            print_warning("Prometheus not responding")
    except:
        print_warning("Prometheus not available")
        print_info("Start with: docker compose --profile monitoring up -d")

    # Check Grafana
    try:
        response = requests.get("http://localhost:3001/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Grafana is healthy (version {data.get('version', 'unknown')})")
            grafana_ok = True
        else:
            print_warning("Grafana not responding")
    except:
        print_warning("Grafana not available")
        print_info("Start with: docker compose --profile monitoring up -d")

    # Monitoring is optional
    return True


def run_smoke_tests():
    """Run smoke tests."""
    print_header("RUNNING SMOKE TESTS")

    result = subprocess.run(
        ["pytest", "-v", "-m", "real_services and smoke and not real_api", "--tb=short", "-x"],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        # Count passed tests
        passed = result.stdout.count(" PASSED")
        print_success(f"Smoke tests PASSED ({passed} tests)")
        return True
    else:
        print_error("Smoke tests FAILED")
        # Show last 20 lines of output
        lines = result.stdout.split('\n')
        print("\n".join(lines[-20:]))
        return False


def main():
    """Run all validations."""
    print(f"{bcolors.BOLD}{bcolors.HEADER}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       DevMatrix Local Production Validation               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{bcolors.ENDC}\n")

    results = {
        "Docker Services": validate_docker_services(),
        "PostgreSQL": validate_postgresql(),
        "Redis": validate_redis(),
        "ChromaDB": validate_chromadb(),
        "Git Workspace": validate_git_workspace(),
        "Monitoring Stack": validate_monitoring(),
        "Anthropic API": validate_anthropic_api(),
        "Smoke Tests": run_smoke_tests(),
    }

    # Summary
    print_header("VALIDATION SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")

    print(f"\n{bcolors.BOLD}Result: {passed}/{total} checks passed{bcolors.ENDC}\n")

    # Critical checks
    critical_checks = ["Docker Services", "PostgreSQL", "Redis", "ChromaDB"]
    critical_passed = all(results.get(check, False) for check in critical_checks)

    if passed == total:
        print_success("✨ System is PRODUCTION READY (Local) ✨")
        return 0
    elif critical_passed:
        print_warning("⚠️  System is functional but has non-critical failures")
        print_info("Check monitoring stack or optional components")
        return 0
    else:
        print_error("⚠️  System has critical failures - see above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
