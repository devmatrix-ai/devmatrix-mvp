# Plan Ultra-Detallado: Production Ready Local

**Objetivo**: Transformar el sistema de "MVP funcional con mocks" a "Production Ready Local" con APIs reales y monitoreo funcional.

**Definición de "Production Ready Local"**:
- ✅ Todo corre localmente (docker-compose)
- ✅ APIs reales (no mocks): Anthropic API, Git operations, PostgreSQL, Redis, ChromaDB
- ✅ Tests de integración reales (E2E sin mocks)
- ✅ Monitoreo funcional (Prometheus + Grafana locales)
- ✅ Observabilidad completa (logs estructurados, métricas, tracing)
- ✅ Validación exhaustiva de todos los componentes
- ❌ NO requiere: Deployment cloud, CI/CD, Kubernetes, infraestructura remota

**Estado Actual Analizado**:
- ✅ docker-compose.yml completo con 5 servicios (postgres, redis, chromadb, api, ui)
- ✅ AnthropicClient con API real implementada (retry, circuit breaker, cache)
- ❌ 15 archivos de test con `patch()` mockeando APIs
- ❌ E2E tests mockean: AnthropicClient, GitOperations, PostgresManager
- ❌ Sin Grafana/Prometheus en docker-compose
- ❌ Sin validación de servicios reales en tests

---

## FASE 1: Pre-requisitos de Infraestructura Local

**Duración estimada**: 2-3 horas
**Prioridad**: 🔴 CRÍTICA (bloqueante para todo lo demás)

### Objetivo
Garantizar que todos los servicios locales estén funcionando correctamente y sean accesibles para los tests.

### 1.1 Validar Servicios Existentes en Docker Compose

**Tareas**:

```bash
# 1. Detener todo lo que esté corriendo
docker-compose down -v

# 2. Limpiar volúmenes anteriores (CUIDADO: borra datos)
docker volume prune -f

# 3. Verificar imágenes necesarias
docker pull pgvector/pgvector:pg16
docker pull redis:7-alpine
docker pull chromadb/chroma:0.4.22

# 4. Iniciar servicios core (sin UI de desarrollo)
docker-compose up -d postgres redis chromadb

# 5. Esperar inicialización (30 segundos)
sleep 30

# 6. Verificar health de cada servicio
docker-compose ps  # Todos deben estar "healthy"

# 7. Validar conectividad PostgreSQL
docker exec -it devmatrix-postgres pg_isready -U devmatrix
# Esperado: "devmatrix-postgres:5432 - accepting connections"

# 8. Validar conectividad Redis
docker exec -it devmatrix-redis redis-cli ping
# Esperado: "PONG"

# 9. Validar conectividad ChromaDB
curl -f http://localhost:8000/api/v1/heartbeat
# Esperado: HTTP 200 con timestamp
```

**Criterios de Aceptación**:
- ✅ `docker-compose ps` muestra 3 servicios con status "healthy"
- ✅ PostgreSQL responde a `pg_isready`
- ✅ Redis responde "PONG"
- ✅ ChromaDB heartbeat retorna HTTP 200
- ✅ No hay errores en logs: `docker-compose logs | grep -i error`

**Troubleshooting**:
```bash
# Si PostgreSQL no inicia
docker-compose logs postgres | tail -50

# Si Redis no responde
docker-compose logs redis | tail -50

# Si ChromaDB falla
docker-compose logs chromadb | tail -50

# Reiniciar servicio específico
docker-compose restart postgres
```

---

### 1.2 Configurar Variables de Entorno para Tests

**Archivo**: `.env.test`

**Contenido**:
```bash
# ==================================
# Test Environment Configuration
# ==================================

# Anthropic API (REAL - requiere API key válida)
ANTHROPIC_API_KEY=sk-ant-your_real_api_key_here

# PostgreSQL (local docker)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=devmatrix_test
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix

# Redis (local docker)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ChromaDB (local docker)
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION=devmatrix_test

# RAG Configuration
RAG_ENABLED=true
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_EMBEDDING_DIM=384
RAG_TOP_K=3
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CACHE_ENABLED=true
RAG_CACHE_DIR=.cache/rag_test

# Git Configuration
GIT_USER_NAME=DevMatrix Test
GIT_USER_EMAIL=test@devmatrix.local

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text
LOG_FILE=

# Test-specific
ENVIRONMENT=test
WORKSPACE_DIR=./workspace_test
```

**Comandos**:
```bash
# 1. Crear archivo .env.test
cp .env.example .env.test

# 2. Editar con API key real de Anthropic
# IMPORTANTE: DEBES tener una API key válida
nano .env.test  # o vim, code, etc.

# 3. Validar que API key funciona
python -c "
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv('.env.test')
api_key = os.getenv('ANTHROPIC_API_KEY')
assert api_key and api_key.startswith('sk-ant-'), 'Invalid API key format'

client = Anthropic(api_key=api_key)
msg = client.messages.create(
    model='claude-haiku-4-5-20251001',
    max_tokens=50,
    messages=[{'role': 'user', 'content': 'Reply with: OK'}]
)
print(f'✅ Anthropic API working: {msg.content[0].text}')
"
```

**Criterios de Aceptación**:
- ✅ `.env.test` existe y contiene ANTHROPIC_API_KEY válida
- ✅ Script de validación imprime "✅ Anthropic API working: OK"
- ✅ Conexión a servicios locales funciona

---

### 1.3 Crear Base de Datos de Test

**Script**: `scripts/setup_test_database.py`

```python
#!/usr/bin/env python3
"""
Setup test database with proper schema and extensions.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv('.env.test')

def setup_test_db():
    # Connect to postgres (default database)
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        user=os.getenv('POSTGRES_USER', 'devmatrix'),
        password=os.getenv('POSTGRES_PASSWORD', 'devmatrix'),
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Drop and recreate test database
    db_name = os.getenv('POSTGRES_DB', 'devmatrix_test')

    print(f"Dropping database {db_name} if exists...")
    cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")

    print(f"Creating database {db_name}...")
    cursor.execute(f"CREATE DATABASE {db_name}")

    cursor.close()
    conn.close()

    # Connect to test database and install extensions
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        user=os.getenv('POSTGRES_USER', 'devmatrix'),
        password=os.getenv('POSTGRES_PASSWORD', 'devmatrix'),
        database=db_name
    )
    cursor = conn.cursor()

    print("Installing pgvector extension...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

    print("Creating schema...")
    # Add your schema creation here
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_generation_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            workspace_id VARCHAR(255),
            user_request TEXT,
            generated_code TEXT,
            approval_status VARCHAR(50),
            quality_score FLOAT,
            metadata JSONB
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Test database {db_name} ready")

if __name__ == "__main__":
    setup_test_db()
```

**Comandos**:
```bash
# 1. Crear script
touch scripts/setup_test_database.py
chmod +x scripts/setup_test_database.py

# 2. Ejecutar setup
python scripts/setup_test_database.py

# 3. Verificar database existe
docker exec -it devmatrix-postgres psql -U devmatrix -l | grep devmatrix_test

# 4. Verificar extensión pgvector
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "\dx" | grep vector
```

**Criterios de Aceptación**:
- ✅ Database `devmatrix_test` existe
- ✅ Extensión `vector` instalada
- ✅ Tabla `code_generation_logs` creada
- ✅ Script imprime "✅ Test database devmatrix_test ready"

---

### 1.4 Seedear RAG con Datos de Test

**Comandos**:
```bash
# 1. Asegurar que ChromaDB está corriendo
curl -f http://localhost:8000/api/v1/heartbeat

# 2. Ejecutar script de seeding
python scripts/seed_rag_examples.py

# 3. Verificar que se indexaron ejemplos
python -c "
from src.rag import create_embedding_model, create_vector_store

embedding_model = create_embedding_model()
vector_store = create_vector_store(
    embedding_model,
    collection_name='devmatrix_code_examples'
)

count = vector_store.count()
print(f'✅ RAG indexed {count} examples')
assert count > 10, f'Expected >10 examples, got {count}'
"

# 4. Test retrieval
python -c "
from src.rag import create_embedding_model, create_vector_store, create_retriever

embedding_model = create_embedding_model()
vector_store = create_vector_store(embedding_model)
retriever = create_retriever(vector_store)

results = retriever.retrieve('authentication function', top_k=3)
print(f'✅ Retrieved {len(results)} similar examples')
for i, result in enumerate(results, 1):
    print(f'  {i}. Similarity: {result.similarity:.3f}')
"
```

**Criterios de Aceptación**:
- ✅ Seed script completa sin errores
- ✅ ChromaDB contiene >10 ejemplos
- ✅ Retrieval funciona y retorna resultados
- ✅ Similarity scores >0.6

---

### 1.5 Configurar Git para Tests

**Comandos**:
```bash
# 1. Crear directorio de workspace para tests
mkdir -p workspace_test
cd workspace_test

# 2. Inicializar repositorio git
git init

# 3. Configurar usuario de test
git config user.name "DevMatrix Test"
git config user.email "test@devmatrix.local"

# 4. Crear commit inicial
touch .gitkeep
git add .gitkeep
git commit -m "chore: init test workspace"

# 5. Verificar configuración
git log --oneline
# Esperado: 1 commit con mensaje "chore: init test workspace"

cd ..

# 6. Crear .gitignore para workspace_test
echo "workspace_test/" >> .gitignore
```

**Criterios de Aceptación**:
- ✅ Directorio `workspace_test/` existe con git inicializado
- ✅ Usuario git configurado correctamente
- ✅ Commit inicial creado
- ✅ `.gitignore` incluye `workspace_test/`

---

## FASE 2: Refactorización de Tests (Eliminar Mocks)

**Duración estimada**: 8-12 horas
**Prioridad**: 🔴 CRÍTICA

### Objetivo
Convertir todos los tests que usan mocks para que usen servicios reales.

### 2.1 Crear Fixtures de Pytest para Servicios Reales

**Archivo**: `tests/conftest.py`

```python
"""
Pytest configuration and shared fixtures for real service testing.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
import tempfile
import shutil

# Load test environment
load_dotenv('.env.test')

from src.llm.anthropic_client import AnthropicClient
from src.state.postgres_manager import PostgresManager
from src.state.redis_manager import RedisManager
from src.rag import create_embedding_model, create_vector_store, create_retriever
from src.tools.workspace_manager import WorkspaceManager


@pytest.fixture(scope="session")
def anthropic_api_key():
    """Get real Anthropic API key from environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not api_key.startswith("sk-ant-"):
        pytest.skip("ANTHROPIC_API_KEY not configured - skipping real API tests")
    return api_key


@pytest.fixture(scope="session")
def real_anthropic_client(anthropic_api_key):
    """Create real Anthropic client (no mocks)."""
    return AnthropicClient(
        api_key=anthropic_api_key,
        model="claude-haiku-4-5-20251001",
        enable_cache=False,  # Disable cache for tests to get fresh responses
        enable_retry=True,
        enable_circuit_breaker=False  # Disable for faster test failures
    )


@pytest.fixture(scope="function")
def real_postgres_manager():
    """Create real PostgreSQL manager connected to test database."""
    manager = PostgresManager(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "devmatrix_test"),
        user=os.getenv("POSTGRES_USER", "devmatrix"),
        password=os.getenv("POSTGRES_PASSWORD", "devmatrix")
    )

    yield manager

    # Cleanup: truncate test tables after each test
    try:
        manager.execute("TRUNCATE TABLE code_generation_logs CASCADE")
    except:
        pass


@pytest.fixture(scope="function")
def real_redis_manager():
    """Create real Redis manager."""
    manager = RedisManager(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD", "")
    )

    yield manager

    # Cleanup: flush test keys
    try:
        # Only delete keys with test prefix
        for key in manager.client.scan_iter(match="test:*"):
            manager.client.delete(key)
    except:
        pass


@pytest.fixture(scope="function")
def real_rag_system():
    """Create real RAG system with ChromaDB."""
    embedding_model = create_embedding_model()

    # Use unique collection for each test
    test_collection = f"test_{pytest.current_test.name}"
    vector_store = create_vector_store(
        embedding_model,
        collection_name=test_collection
    )
    retriever = create_retriever(vector_store)

    yield {
        "embedding_model": embedding_model,
        "vector_store": vector_store,
        "retriever": retriever
    }

    # Cleanup: delete test collection
    try:
        vector_store.delete_collection()
    except:
        pass


@pytest.fixture(scope="function")
def real_workspace():
    """Create real temporary workspace with git."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="devmatrix_test_")
    workspace_path = Path(temp_dir)

    # Initialize git
    import subprocess
    subprocess.run(
        ["git", "init"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "DevMatrix Test"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@devmatrix.local"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )

    # Create initial commit
    gitkeep = workspace_path / ".gitkeep"
    gitkeep.touch()
    subprocess.run(
        ["git", "add", ".gitkeep"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "chore: init test workspace"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )

    yield workspace_path

    # Cleanup: remove temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def real_workspace_manager(real_workspace):
    """Create WorkspaceManager with real git-enabled workspace."""
    workspace_id = real_workspace.name
    return WorkspaceManager(
        workspace_id=workspace_id,
        base_path=real_workspace
    )


# Session-scoped markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "real_api: marks tests that use real Anthropic API (may be slow and cost money)"
    )
    config.addinivalue_line(
        "markers", "real_services: marks tests that require real PostgreSQL, Redis, ChromaDB"
    )
    config.addinivalue_line(
        "markers", "e2e: marks end-to-end tests with full workflow"
    )
```

**Criterios de Aceptación**:
- ✅ Fixtures crean conexiones reales a servicios
- ✅ Fixtures incluyen cleanup automático
- ✅ `pytest --collect-only` no falla
- ✅ Markers custom registrados

---

### 2.2 Refactorizar Test E2E Principal

**Archivo**: `tests/integration/test_e2e_code_generation_real.py`

```python
"""
End-to-End Tests with REAL Services (No Mocks)

IMPORTANT:
- Uses real Anthropic API (costs money, ~$0.01-0.10 per test)
- Uses real PostgreSQL, Redis, ChromaDB
- Uses real Git operations
- Slower than mocked tests (~30-60 seconds per test)

Run with: pytest -v -m real_api tests/integration/test_e2e_code_generation_real.py
"""

import pytest
import time
from pathlib import Path

from src.agents.code_generation_agent import CodeGenerationAgent


@pytest.mark.real_api
@pytest.mark.real_services
@pytest.mark.e2e
class TestE2ERealServices:
    """E2E tests using REAL services (no mocks)."""

    @pytest.fixture
    def real_agent(self, real_anthropic_client, real_postgres_manager):
        """Create CodeGenerationAgent with real services."""
        agent = CodeGenerationAgent(
            api_key=real_anthropic_client.api_key,
            postgres_manager=real_postgres_manager,
            enable_cache=False  # Disable cache for predictable tests
        )
        return agent

    def test_e2e_fibonacci_real_api(self, real_agent, real_workspace_manager):
        """
        E2E: Generate fibonacci with REAL Anthropic API.

        This test:
        1. Calls real Claude API for analysis, planning, code generation, review
        2. Writes to real filesystem
        3. Commits to real git repository
        4. Logs to real PostgreSQL

        Expected cost: ~$0.02-0.05
        Expected time: 20-40 seconds
        """
        start_time = time.time()

        # Execute with real API (no mocks)
        result = real_agent.generate(
            user_request="Create a fibonacci function with memoization",
            workspace_id=real_workspace_manager.workspace_id,
            git_enabled=True,
            # Auto-approve for test (would be manual in production)
            auto_approve=True
        )

        elapsed = time.time() - start_time

        # Verify results
        assert result["success"] is True, f"Generation failed: {result.get('error')}"
        assert result["approval_status"] == "approved"
        assert result["file_written"] is True
        assert "fibonacci" in result["file_path"].lower()
        assert "def fibonacci" in result["generated_code"]
        assert "memoization" in result["generated_code"] or "cache" in result["generated_code"]
        assert result["quality_score"] >= 7.0, f"Quality too low: {result['quality_score']}"
        assert result["git_committed"] is True
        assert len(result["git_commit_hash"]) == 40  # SHA-1 hash

        # Verify file exists on filesystem
        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.read_text() == result["generated_code"]

        # Verify git commit
        import subprocess
        git_log = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=file_path.parent,
            capture_output=True,
            text=True,
            check=True
        )
        assert result["git_commit_hash"][:7] in git_log.stdout

        # Performance: should complete in <60 seconds
        assert elapsed < 60.0, f"Test took {elapsed:.2f}s, expected <60s"

        print(f"\n✅ Real API test passed in {elapsed:.2f}s")
        print(f"   Cost: ~${result['usage']['input_tokens'] * 0.000003 + result['usage']['output_tokens'] * 0.000015:.4f}")

    def test_e2e_class_generation_real(self, real_agent, real_workspace_manager):
        """E2E: Generate Calculator class with real API."""
        result = real_agent.generate(
            user_request="Create a Calculator class with add, subtract, multiply, divide methods",
            workspace_id=real_workspace_manager.workspace_id,
            git_enabled=True,
            auto_approve=True
        )

        assert result["success"] is True
        assert "class Calculator" in result["generated_code"]
        assert "def add" in result["generated_code"]
        assert "def divide" in result["generated_code"]
        assert "ZeroDivisionError" in result["generated_code"] or "division by zero" in result["generated_code"].lower()
        assert result["quality_score"] >= 7.0
        assert result["git_committed"] is True

    def test_e2e_with_rag_enhancement(
        self,
        real_agent,
        real_workspace_manager,
        real_rag_system
    ):
        """E2E: Test RAG-enhanced code generation."""
        # First, index an example
        vector_store = real_rag_system["vector_store"]
        vector_store.add_example(
            code="""
def authenticate_user(username: str, password: str) -> bool:
    '''Authenticate user with bcrypt password hashing.'''
    import bcrypt
    stored_hash = get_password_hash(username)
    return bcrypt.checkpw(password.encode(), stored_hash)
""",
            metadata={"language": "python", "pattern": "authentication", "approved": True}
        )

        # Now generate similar code (should use RAG example)
        result = real_agent.generate(
            user_request="Create a user authentication function with secure password hashing",
            workspace_id=real_workspace_manager.workspace_id,
            git_enabled=True,
            auto_approve=True,
            enable_rag=True
        )

        assert result["success"] is True
        assert "bcrypt" in result["generated_code"] or "hashlib" in result["generated_code"]
        assert "password" in result["generated_code"].lower()
        assert result["quality_score"] >= 7.5  # Should be higher with RAG

    def test_e2e_error_recovery_real(self, real_agent, real_workspace_manager):
        """E2E: Test error recovery with real API."""
        # Request intentionally vague to trigger low quality score
        result = real_agent.generate(
            user_request="Make a thing",
            workspace_id=real_workspace_manager.workspace_id,
            git_enabled=False,
            auto_approve=False  # Manual review required
        )

        # Agent should still complete but with lower quality
        assert result["success"] is True
        assert result["generated_code"] != ""
        # Quality score might be lower for vague request
        assert result["quality_score"] >= 3.0

    @pytest.mark.slow
    def test_e2e_performance_benchmark_real(self, real_agent, real_workspace_manager):
        """E2E: Performance benchmark with real API (3 iterations)."""
        times = []
        costs = []

        for i in range(3):
            start = time.time()

            result = real_agent.generate(
                user_request=f"Create a simple add function (iteration {i})",
                workspace_id=f"{real_workspace_manager.workspace_id}_{i}",
                git_enabled=True,
                auto_approve=True
            )

            elapsed = time.time() - start
            times.append(elapsed)

            # Calculate cost
            cost = (
                result['usage']['input_tokens'] * 0.000003 +
                result['usage']['output_tokens'] * 0.000015
            )
            costs.append(cost)

            assert result["success"] is True

        avg_time = sum(times) / len(times)
        max_time = max(times)
        total_cost = sum(costs)

        # Performance requirements (more lenient for real API)
        assert avg_time < 40.0, f"Average time {avg_time:.2f}s exceeds 40s"
        assert max_time < 60.0, f"Max time {max_time:.2f}s exceeds 60s"
        assert total_cost < 0.50, f"Total cost ${total_cost:.4f} exceeds $0.50"

        print(f"\n✅ Performance benchmark:")
        print(f"   Avg: {avg_time:.2f}s | Max: {max_time:.2f}s | Min: {min(times):.2f}s")
        print(f"   Total cost: ${total_cost:.4f}")
```

**Comandos**:
```bash
# 1. Crear nuevo archivo de test real
touch tests/integration/test_e2e_code_generation_real.py

# 2. Ejecutar tests reales (CON API key válida)
pytest -v -m real_api tests/integration/test_e2e_code_generation_real.py

# 3. Ejecutar solo un test específico
pytest -v tests/integration/test_e2e_code_generation_real.py::TestE2ERealServices::test_e2e_fibonacci_real_api

# 4. Ver coverage
pytest --cov=src --cov-report=html -m real_api tests/integration/

# 5. Ejecutar con timing detallado
pytest -v --durations=10 -m real_api tests/integration/
```

**Criterios de Aceptación**:
- ✅ Tests pasan con API real de Anthropic
- ✅ Tests completan en <60s cada uno
- ✅ Costo por test <$0.10
- ✅ Git commits reales se crean
- ✅ Files escritos al filesystem existen
- ✅ PostgreSQL logs registrados

---

### 2.3 Configurar pytest.ini

**Archivo**: `pytest.ini`

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require services)
    e2e: End-to-end tests (full workflow)
    real_api: Tests using real Anthropic API (slow, costs money)
    real_services: Tests requiring real PostgreSQL/Redis/ChromaDB
    slow: Tests that take >30 seconds
    smoke: Quick smoke tests

# Output
addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings

# Coverage
# (add --cov when needed)

# Timeouts (requires pytest-timeout)
timeout = 120
timeout_method = thread

# Environment
env_files =
    .env.test

# Logging
log_cli = false
log_cli_level = INFO
log_file = tests/test.log
log_file_level = DEBUG
```

**Comandos**:
```bash
# Ejecutar solo unit tests (rápidos, sin API)
pytest -m unit

# Ejecutar integration tests (requieren servicios locales)
pytest -m "integration and not real_api"

# Ejecutar E2E con API real (lento, cuesta dinero)
pytest -m "e2e and real_api"

# Ejecutar smoke tests (validación rápida)
pytest -m smoke

# Ejecutar TODO excepto tests caros
pytest -m "not real_api"

# Parallel execution (requiere pytest-xdist)
pytest -n auto -m unit
```

---

## FASE 3: Observabilidad Local (Grafana + Prometheus)

**Duración estimada**: 4-6 horas
**Prioridad**: 🟡 IMPORTANTE

### Objetivo
Configurar stack completo de monitoreo local con métricas exportadas y visualizadas.

### 3.1 Añadir Prometheus y Grafana a docker-compose.yml

**Modificación a**: `docker-compose.yml`

```yaml
  # Prometheus (Metrics Collection)
  prometheus:
    image: prom/prometheus:latest
    container_name: devmatrix-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=7d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - devmatrix-network
    profiles:
      - monitoring

  # Grafana (Metrics Visualization)
  grafana:
    image: grafana/grafana:latest
    container_name: devmatrix-grafana
    restart: unless-stopped
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://localhost:3001
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./docker/grafana/dashboards:/var/lib/grafana/dashboards:ro
    depends_on:
      - prometheus
    networks:
      - devmatrix-network
    profiles:
      - monitoring

volumes:
  prometheus_data:
    name: devmatrix-prometheus-data
  grafana_data:
    name: devmatrix-grafana-data
```

---

### 3.2 Configurar Prometheus

**Archivo**: `docker/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'devmatrix-local'
    environment: 'development'

# Alerting (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Scrape configs
scrape_configs:
  # DevMatrix API
  - job_name: 'devmatrix-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/metrics/prometheus'
    scrape_interval: 10s

  # PostgreSQL (if using postgres_exporter)
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    # Requires postgres_exporter sidecar

  # Redis (if using redis_exporter)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    # Requires redis_exporter sidecar

  # ChromaDB
  - job_name: 'chromadb'
    static_configs:
      - targets: ['chromadb:8000']
    metrics_path: '/metrics'

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

**Comandos**:
```bash
# 1. Crear directorio
mkdir -p docker/prometheus

# 2. Crear archivo de configuración
touch docker/prometheus/prometheus.yml

# 3. Validar sintaxis YAML
python -c "import yaml; yaml.safe_load(open('docker/prometheus/prometheus.yml'))"

# 4. Iniciar Prometheus
docker-compose --profile monitoring up -d prometheus

# 5. Verificar que scraping funciona
curl http://localhost:9090/api/v1/targets

# 6. Query de ejemplo
curl 'http://localhost:9090/api/v1/query?query=up'
```

---

### 3.3 Configurar Grafana Datasource

**Archivo**: `docker/grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: "POST"
```

---

### 3.4 Crear Dashboard de Grafana

**Archivo**: `docker/grafana/dashboards/devmatrix-overview.json`

```json
{
  "dashboard": {
    "title": "DevMatrix - Overview",
    "tags": ["devmatrix", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "API Response Time (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "id": 3,
        "title": "LLM API Calls",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(llm_requests_total)",
            "legendFormat": "Total Calls"
          }
        ]
      },
      {
        "id": 4,
        "title": "Code Generation Success Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "sum(rate(code_generation_success_total[5m])) / sum(rate(code_generation_attempts_total[5m])) * 100"
          }
        ]
      },
      {
        "id": 5,
        "title": "PostgreSQL Connections",
        "type": "stat",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends"
          }
        ]
      },
      {
        "id": 6,
        "title": "Redis Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "redis_memory_used_bytes"
          }
        ]
      },
      {
        "id": 7,
        "title": "RAG Vector Store Size",
        "type": "stat",
        "targets": [
          {
            "expr": "chromadb_collection_count"
          }
        ]
      }
    ]
  }
}
```

**Configuración de provisioning**:

**Archivo**: `docker/grafana/provisioning/dashboards/default.yml`

```yaml
apiVersion: 1

providers:
  - name: 'DevMatrix Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

**Comandos**:
```bash
# 1. Crear estructura de directorios
mkdir -p docker/grafana/provisioning/{datasources,dashboards}
mkdir -p docker/grafana/dashboards

# 2. Crear archivos de configuración
# (copiar contenido de arriba)

# 3. Iniciar Grafana
docker-compose --profile monitoring up -d grafana

# 4. Abrir Grafana en navegador
xdg-open http://localhost:3001
# Usuario: admin
# Password: admin (o desde .env)

# 5. Verificar datasource conectado
curl -u admin:admin http://localhost:3001/api/datasources

# 6. Verificar dashboards cargados
curl -u admin:admin http://localhost:3001/api/search
```

**Criterios de Aceptación**:
- ✅ Prometheus corriendo en :9090
- ✅ Grafana corriendo en :3001
- ✅ Datasource Prometheus conectado
- ✅ Dashboard "DevMatrix - Overview" visible
- ✅ Métricas siendo scraped cada 15s

---

## FASE 4: Tests de Integración Completos

**Duración estimada**: 6-8 horas
**Prioridad**: 🔴 CRÍTICA

### Objetivo
Suite completa de tests de integración que validan el sistema end-to-end con servicios reales.

### 4.1 Test Suite de RAG Real

**Archivo**: `tests/integration/test_rag_real_services.py`

```python
"""Integration tests for RAG system with real ChromaDB."""

import pytest
from src.rag import (
    create_embedding_model,
    create_vector_store,
    create_retriever,
    RetrievalStrategy
)


@pytest.mark.real_services
class TestRAGRealChromaDB:
    """RAG tests with real ChromaDB (no mocks)."""

    def test_indexing_and_retrieval_real(self, real_rag_system):
        """Test full indexing and retrieval cycle."""
        vector_store = real_rag_system["vector_store"]
        retriever = real_rag_system["retriever"]

        # Index examples
        examples = [
            ("def add(a, b): return a + b", {"language": "python", "pattern": "arithmetic"}),
            ("def subtract(a, b): return a - b", {"language": "python", "pattern": "arithmetic"}),
            ("def multiply(a, b): return a * b", {"language": "python", "pattern": "arithmetic"}),
            ("def authenticate(user, pw): return check_password(user, pw)", {"language": "python", "pattern": "auth"}),
        ]

        for code, metadata in examples:
            vector_store.add_example(code, metadata)

        # Verify count
        assert vector_store.count() == 4

        # Test retrieval
        results = retriever.retrieve("addition function", top_k=2)

        assert len(results) == 2
        assert "add" in results[0].code
        assert results[0].similarity > 0.6

    def test_mmr_strategy_real(self, real_rag_system):
        """Test MMR retrieval strategy for diversity."""
        vector_store = real_rag_system["vector_store"]

        # Index similar examples
        for i in range(5):
            vector_store.add_example(
                f"def add_{i}(a, b): return a + b",
                {"language": "python", "version": i}
            )

        # Retrieve with MMR
        retriever = real_rag_system["retriever"]
        results = retriever.retrieve(
            "addition function",
            top_k=3,
            strategy=RetrievalStrategy.MMR
        )

        assert len(results) == 3
        # Results should be diverse (not all identical)
        versions = [r.metadata.get("version") for r in results]
        assert len(set(versions)) > 1  # At least 2 different versions

    def test_persistent_cache_real(self, real_rag_system):
        """Test persistent embedding cache."""
        embedding_model = real_rag_system["embedding_model"]

        query = "test query for caching"

        # First embedding (cache miss)
        import time
        start = time.time()
        emb1 = embedding_model.embed_text(query)
        time_uncached = time.time() - start

        # Second embedding (cache hit)
        start = time.time()
        emb2 = embedding_model.embed_text(query)
        time_cached = time.time() - start

        # Verify cache hit is faster
        assert time_cached < time_uncached / 2, "Cache should be at least 2x faster"

        # Verify embeddings are identical
        assert emb1 == emb2

        # Verify cache stats
        if hasattr(embedding_model, 'cache'):
            stats = embedding_model.cache.get_stats()
            assert stats.hit_rate > 0
```

---

### 4.2 Test Suite Multi-Agent Real

**Archivo**: `tests/integration/test_multi_agent_real.py`

```python
"""Integration tests for multi-agent workflow with real services."""

import pytest
from src.workflows.multi_agent_workflow import MultiAgentWorkflow
from src.agents.orchestrator_agent import OrchestratorAgent
from src.state.shared_scratchpad import SharedScratchpad


@pytest.mark.real_api
@pytest.mark.real_services
@pytest.mark.e2e
class TestMultiAgentReal:
    """Multi-agent workflow tests with real services."""

    @pytest.fixture
    def real_workflow(self, real_anthropic_client, real_postgres_manager, real_redis_manager):
        """Create multi-agent workflow with real services."""
        scratchpad = SharedScratchpad(
            redis_manager=real_redis_manager,
            postgres_manager=real_postgres_manager
        )

        orchestrator = OrchestratorAgent(
            api_key=real_anthropic_client.api_key
        )

        workflow = MultiAgentWorkflow(
            orchestrator=orchestrator,
            scratchpad=scratchpad
        )

        return workflow

    def test_parallel_task_execution_real(self, real_workflow, real_workspace_manager):
        """Test parallel execution of independent tasks."""
        import time
        start = time.time()

        result = real_workflow.execute(
            user_request="Create two independent utility functions: one for JSON validation and one for date formatting",
            workspace_id=real_workspace_manager.workspace_id
        )

        elapsed = time.time() - start

        assert result["success"] is True
        assert len(result["completed_tasks"]) == 2

        # Parallel execution should be faster than sequential
        # (though with API calls, speedup may be minimal)
        assert elapsed < 120.0

    def test_dependent_task_workflow_real(self, real_workflow, real_workspace_manager):
        """Test workflow with task dependencies."""
        result = real_workflow.execute(
            user_request="Create a User model, then create tests for it, then create API endpoints",
            workspace_id=real_workspace_manager.workspace_id
        )

        assert result["success"] is True
        assert len(result["completed_tasks"]) >= 3

        # Verify tasks executed in order
        task_types = [t["type"] for t in result["completed_tasks"]]
        assert "implementation" in task_types[0].lower()
        assert "test" in task_types[1].lower()
        assert "api" in task_types[2].lower() or "endpoint" in task_types[2].lower()
```

---

## FASE 5: Validación Final y Documentación

**Duración estimada**: 3-4 horas
**Prioridad**: 🟡 IMPORTANTE

### Objetivo
Validar que todo el sistema funciona end-to-end y documentar el proceso de setup.

### 5.1 Script de Validación Completa

**Archivo**: `scripts/validate_local_production.py`

```python
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

    # Check docker-compose
    result = subprocess.run(
        ["docker-compose", "ps"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print_error("docker-compose not available or services not running")
        return False

    services = ["postgres", "redis", "chromadb"]
    all_healthy = True

    for service in services:
        if service in result.stdout and "healthy" in result.stdout:
            print_success(f"{service} is healthy")
        else:
            print_error(f"{service} is NOT healthy")
            all_healthy = False

    return all_healthy


def validate_anthropic_api():
    """Validate Anthropic API connectivity."""
    print_header("VALIDATING ANTHROPIC API")

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or not api_key.startswith("sk-ant-"):
        print_error("ANTHROPIC_API_KEY not configured or invalid format")
        return False

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
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
            f"http://{os.getenv('CHROMADB_HOST', 'localhost')}:{os.getenv('CHROMADB_PORT', 8000)}/api/v1/heartbeat",
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
            collection_name="validation_test"
        )

        # Add test example
        vector_store.add_example(
            "def validate(): return True",
            {"type": "validation"}
        )

        count = vector_store.count()
        print_success(f"ChromaDB vector operations working: {count} documents")

        # Cleanup
        vector_store.delete_collection()

        return True

    except Exception as e:
        print_error(f"ChromaDB failed: {str(e)}")
        return False


def validate_git_workspace():
    """Validate Git workspace setup."""
    print_header("VALIDATING GIT WORKSPACE")

    workspace_path = Path("workspace_test")

    if not workspace_path.exists():
        print_error("workspace_test/ does not exist")
        return False

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
        print_error("Git NOT initialized in workspace_test/")
        return False

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

    # Check Prometheus
    try:
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        if response.status_code == 200:
            print_success("Prometheus is healthy")
        else:
            print_warning("Prometheus not responding (may not be started)")
    except:
        print_warning("Prometheus not available (start with: docker-compose --profile monitoring up)")

    # Check Grafana
    try:
        response = requests.get("http://localhost:3001/api/health", timeout=5)
        if response.status_code == 200:
            print_success("Grafana is healthy")
        else:
            print_warning("Grafana not responding")
    except:
        print_warning("Grafana not available (start with: docker-compose --profile monitoring up)")

    return True  # Non-critical


def run_smoke_tests():
    """Run smoke tests."""
    print_header("RUNNING SMOKE TESTS")

    result = subprocess.run(
        ["pytest", "-v", "-m", "smoke", "--tb=short"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success("Smoke tests PASSED")
        return True
    else:
        print_error("Smoke tests FAILED")
        print(result.stdout)
        return False


def main():
    """Run all validations."""
    print(f"{bcolors.BOLD}DevMatrix Local Production Validation{bcolors.ENDC}\n")

    results = {
        "Docker Services": validate_docker_services(),
        "Anthropic API": validate_anthropic_api(),
        "PostgreSQL": validate_postgresql(),
        "Redis": validate_redis(),
        "ChromaDB": validate_chromadb(),
        "Git Workspace": validate_git_workspace(),
        "Monitoring Stack": validate_monitoring(),
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

    if passed == total:
        print_success("✨ System is PRODUCTION READY (Local) ✨")
        return 0
    else:
        print_error("⚠️  System has failures - see above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Comandos**:
```bash
# Ejecutar validación completa
python scripts/validate_local_production.py

# Expected output:
# ✅ All services healthy
# ✅ APIs working
# ✅ Tests passing
# ✨ System is PRODUCTION READY (Local) ✨
```

---

### 5.2 Runbook de Operaciones Locales

**Archivo**: `DOCS/LOCAL_OPERATIONS_RUNBOOK.md`

```markdown
# Runbook: Operaciones Locales Production-Ready

## Inicio Rápido

### Start All Services
\`\`\`bash
# Start core services
docker-compose up -d postgres redis chromadb

# Start monitoring (optional)
docker-compose --profile monitoring up -d prometheus grafana

# Start API
docker-compose up -d api

# Verify all healthy
docker-compose ps
\`\`\`

### Stop All Services
\`\`\`bash
docker-compose down
\`\`\`

### Restart Single Service
\`\`\`bash
docker-compose restart postgres
\`\`\`

---

## Validación de Sistema

### Health Checks
\`\`\`bash
# PostgreSQL
docker exec -it devmatrix-postgres pg_isready

# Redis
docker exec -it devmatrix-redis redis-cli ping

# ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# API
curl http://localhost:8000/api/v1/health/live
\`\`\`

### Run Validation Script
\`\`\`bash
python scripts/validate_local_production.py
\`\`\`

---

## Testing

### Run All Tests
\`\`\`bash
# Unit tests (fast, no external deps)
pytest -m unit

# Integration tests (requires services)
pytest -m "integration and not real_api"

# E2E with real API (slow, costs money)
pytest -m "e2e and real_api"
\`\`\`

### Run Specific Test
\`\`\`bash
pytest -v tests/integration/test_e2e_code_generation_real.py::TestE2ERealServices::test_e2e_fibonacci_real_api
\`\`\`

---

## Monitoring

### Access Dashboards
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

### View Metrics
\`\`\`bash
# API metrics
curl http://localhost:8000/api/v1/metrics/prometheus

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=up'
\`\`\`

---

## Troubleshooting

### Service Won't Start
\`\`\`bash
# Check logs
docker-compose logs [service-name]

# Example: PostgreSQL logs
docker-compose logs postgres | tail -50

# Restart with fresh volumes
docker-compose down -v
docker-compose up -d
\`\`\`

### Tests Failing
\`\`\`bash
# Check environment
cat .env.test | grep ANTHROPIC_API_KEY

# Validate services
python scripts/validate_local_production.py

# Run with verbose output
pytest -v -s --tb=long
\`\`\`

### API Rate Limits
\`\`\`bash
# Check circuit breaker status
curl http://localhost:8000/api/v1/health/circuit-breaker

# Reset circuit breaker (if needed)
# Restart API service
docker-compose restart api
\`\`\`

---

## Maintenance

### Backup Data
\`\`\`bash
# PostgreSQL
docker exec devmatrix-postgres pg_dump -U devmatrix devmatrix_test > backup.sql

# ChromaDB
docker cp devmatrix-chromadb:/chroma/chroma ./chromadb_backup/

# Redis (if needed)
docker exec devmatrix-redis redis-cli BGSAVE
\`\`\`

### Clean Up Test Data
\`\`\`bash
# Truncate test tables
python scripts/cleanup_test_data.py

# Or manual
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "TRUNCATE TABLE code_generation_logs CASCADE"
\`\`\`

### Update Dependencies
\`\`\`bash
# Pull latest images
docker-compose pull

# Rebuild API
docker-compose build --no-cache api

# Restart with new images
docker-compose up -d
\`\`\`

---

## Cost Management

### Estimate API Costs
\`\`\`python
# After test run
import json

with open('test_results.json') as f:
    results = json.load(f)

total_cost = sum(
    r['usage']['input_tokens'] * 0.000003 +
    r['usage']['output_tokens'] * 0.000015
    for r in results
)

print(f"Total cost: ${total_cost:.4f}")
\`\`\`

### Limit API Usage
- Set `ANTHROPIC_API_MAX_CALLS=100` in `.env.test`
- Use `pytest -k "specific_test"` to run subset
- Enable caching: `RAG_CACHE_ENABLED=true`
\`\`\`
```

---

### 5.3 Criterios de Aceptación Final

**Checklist de Production Ready Local**:

#### 🔴 Requisitos Críticos

- [ ] **Docker Services**
  - [ ] PostgreSQL healthy y accesible
  - [ ] Redis healthy y accesible
  - [ ] ChromaDB healthy y accesible
  - [ ] Todos con health checks pasando

- [ ] **API Real de Anthropic**
  - [ ] ANTHROPIC_API_KEY configurada y válida
  - [ ] Tests pueden llamar API real
  - [ ] Rate limiting y retry funcionando
  - [ ] Circuit breaker funcional

- [ ] **Tests Sin Mocks**
  - [ ] E2E tests usan Anthropic API real (no mocks)
  - [ ] Git operations son reales (no mocks)
  - [ ] PostgreSQL operations son reales
  - [ ] Fixtures de pytest configuradas
  - [ ] `pytest -m real_api` pasa todos los tests

- [ ] **RAG Funcional**
  - [ ] ChromaDB indexando correctamente
  - [ ] Retrieval retorna resultados relevantes
  - [ ] Persistent cache funcionando
  - [ ] Similarity scores >0.6

#### 🟡 Requisitos Importantes

- [ ] **Monitoreo Local**
  - [ ] Prometheus scrapeando métricas
  - [ ] Grafana visualizando datos
  - [ ] Dashboard "DevMatrix Overview" funcional
  - [ ] Datasource conectado

- [ ] **Observabilidad**
  - [ ] Logs estructurados en stdout
  - [ ] Métricas exportadas a Prometheus
  - [ ] Health endpoints respondiendo

- [ ] **Documentación**
  - [ ] Runbook de operaciones completo
  - [ ] Scripts de validación ejecutables
  - [ ] README actualizado

#### 🟢 Requisitos Recomendados

- [ ] **Performance**
  - [ ] E2E tests completan en <60s
  - [ ] Costo por test <$0.10
  - [ ] RAG retrieval <500ms

- [ ] **Developer Experience**
  - [ ] Comandos one-liner para start/stop
  - [ ] Validación automática en CI (opcional)
  - [ ] Scripts de cleanup automatizados

---

## Comandos de Ejecución Fase por Fase

### FASE 1: Setup (Ejecutar primero)
```bash
# 1. Servicios
docker-compose up -d postgres redis chromadb
sleep 30
docker-compose ps  # Verificar healthy

# 2. Environment
cp .env.example .env.test
nano .env.test  # Agregar ANTHROPIC_API_KEY real

# 3. Database
python scripts/setup_test_database.py

# 4. RAG Seeding
python scripts/seed_rag_examples.py

# 5. Git Workspace
mkdir -p workspace_test
cd workspace_test && git init && cd ..
```

### FASE 2: Tests (Después de setup)
```bash
# 1. Crear conftest.py con fixtures
# (copiar contenido de 2.1)

# 2. Crear test_e2e_code_generation_real.py
# (copiar contenido de 2.2)

# 3. Ejecutar tests
pytest -v -m real_api tests/integration/test_e2e_code_generation_real.py
```

### FASE 3: Monitoring (Opcional pero recomendado)
```bash
# 1. Configurar Prometheus
mkdir -p docker/prometheus
# (crear prometheus.yml)

# 2. Configurar Grafana
mkdir -p docker/grafana/{provisioning,dashboards}
# (crear datasource y dashboard configs)

# 3. Iniciar monitoring stack
docker-compose --profile monitoring up -d prometheus grafana

# 4. Abrir Grafana
xdg-open http://localhost:3001
```

### FASE 4: Tests Completos
```bash
# Ejecutar suite completa
pytest -v -m real_services

# Ejecutar con coverage
pytest --cov=src --cov-report=html -m real_services
```

### FASE 5: Validación Final
```bash
# Script de validación
python scripts/validate_local_production.py

# Expected: ✨ System is PRODUCTION READY (Local) ✨
```

---

## Tiempo Total Estimado

| Fase | Duración | Prioridad |
|------|----------|-----------|
| FASE 1: Pre-requisitos | 2-3 horas | 🔴 CRÍTICA |
| FASE 2: Refactorización Tests | 8-12 horas | 🔴 CRÍTICA |
| FASE 3: Monitoring | 4-6 horas | 🟡 IMPORTANTE |
| FASE 4: Tests Integración | 6-8 horas | 🔴 CRÍTICA |
| FASE 5: Validación | 3-4 horas | 🟡 IMPORTANTE |
| **TOTAL** | **23-33 horas** | **(3-4 días laborales)** |

---

## Criterios de Éxito

Al completar este plan, el sistema debe cumplir:

1. ✅ **Tests sin mocks**: E2E tests llaman Anthropic API real
2. ✅ **Servicios locales**: PostgreSQL, Redis, ChromaDB funcionando
3. ✅ **Git real**: Commits reales en workspace local
4. ✅ **RAG funcional**: ChromaDB indexando y retrieving
5. ✅ **Monitoreo local**: Prometheus + Grafana operacionales
6. ✅ **Validación completa**: `validate_local_production.py` pasa 100%
7. ✅ **Documentación**: Runbook completo y actualizado

**Resultado**: Sistema "Production Ready Local" - funcional con APIs reales, sin deployment en la nube.

---

**Próximos Pasos Opcionales**:
- CI/CD local con GitHub Actions self-hosted runners
- Pre-commit hooks para validación automática
- Load testing con Locust local
- Backup/restore procedures automatizados
