# Troubleshooting Guide - DevMatrix Local Production

Guía completa de solución de problemas para el sistema DevMatrix corriendo localmente.

## Tabla de Contenidos

1. [Docker Services](#docker-services)
2. [Database Issues](#database-issues)
3. [API Connection Problems](#api-connection-problems)
4. [Test Failures](#test-failures)
5. [Performance Issues](#performance-issues)
6. [Monitoring Problems](#monitoring-problems)

---

## Docker Services

### Problema: Servicio no inicia

**Síntomas:**
```bash
docker compose ps
# Muestra servicio con status "Exit 1" o "Restarting"
```

**Diagnóstico:**
```bash
# Ver logs del servicio
docker compose logs postgres --tail 50
docker compose logs redis --tail 50
docker compose logs chromadb --tail 50
```

**Soluciones:**

1. **Puerto ya en uso:**
   ```bash
   # Verificar qué está usando el puerto
   netstat -tulpn | grep 5432  # PostgreSQL
   netstat -tulpn | grep 6379  # Redis
   netstat -tulpn | grep 8001  # ChromaDB

   # Matar proceso conflictivo
   sudo kill -9 <PID>

   # O cambiar puerto en .env
   echo "POSTGRES_PORT=5433" >> .env
   ```

2. **Volúmenes corruptos:**
   ```bash
   # Detener y eliminar volúmenes
   docker compose down -v

   # Reiniciar desde cero
   docker compose up -d
   ```

3. **Permisos de archivos:**
   ```bash
   # Dar permisos correctos
   sudo chown -R $USER:$USER .
   chmod -R 755 docker/
   ```

### Problema: Service "healthy" pero no responde

**Síntomas:**
- `docker compose ps` muestra "healthy"
- Pero conexiones fallan

**Diagnóstico:**
```bash
# Probar conexión directa
docker exec -it devmatrix-postgres pg_isready
docker exec -it devmatrix-redis redis-cli ping
curl http://localhost:8001/api/v2/heartbeat
```

**Soluciones:**

1. **Restart del servicio:**
   ```bash
   docker compose restart postgres
   ```

2. **Verificar networking:**
   ```bash
   # Ver red Docker
   docker network ls
   docker network inspect devmatrix-network
   ```

3. **Reiniciar Docker Engine:**
   ```bash
   sudo systemctl restart docker
   ```

---

## Database Issues

### PostgreSQL: Connection Refused

**Síntomas:**
```
psycopg2.OperationalError: could not connect to server
```

**Diagnóstico:**
```bash
# Verificar que PostgreSQL está running
docker compose ps postgres

# Test de conexión
docker exec -it devmatrix-postgres pg_isready -U devmatrix

# Ver logs
docker compose logs postgres | tail -50
```

**Soluciones:**

1. **Verificar credenciales en .env.test:**
   ```bash
   cat .env.test | grep POSTGRES
   # Debe coincidir con docker-compose.yml
   ```

2. **Recrear database:**
   ```bash
   python scripts/setup_test_database.py
   ```

3. **Verificar que tablas existen:**
   ```bash
   docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test -c "\dt"
   ```

### PostgreSQL: pgvector Extension Missing

**Síntomas:**
```
ERROR:  type "vector" does not exist
```

**Solución:**
```bash
# Instalar extensión manualmente
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "CREATE EXTENSION IF NOT EXISTS vector"

# Verificar instalación
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix_test \
  -c "SELECT * FROM pg_extension WHERE extname='vector'"
```

### Redis: Connection Timeout

**Síntomas:**
```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```

**Diagnóstico:**
```bash
# Verificar Redis running
docker compose ps redis

# Test PING
docker exec -it devmatrix-redis redis-cli ping
```

**Soluciones:**

1. **Restart Redis:**
   ```bash
   docker compose restart redis
   ```

2. **Verificar puerto:**
   ```bash
   netstat -tulpn | grep 6379
   ```

3. **Limpiar datos corruptos:**
   ```bash
   docker exec -it devmatrix-redis redis-cli FLUSHALL
   docker compose restart redis
   ```

### ChromaDB: API Version Mismatch

**Síntomas:**
```
404 Not Found: /api/v1/heartbeat
```

**Solución:**
```bash
# ChromaDB usa /api/v2/ en versiones nuevas
curl http://localhost:8001/api/v2/heartbeat

# Actualizar código para usar v2
# Ya está corregido en fixtures actuales
```

### ChromaDB: Collection Already Exists

**Síntomas:**
```
ValueError: Collection already exists: test_collection
```

**Solución:**
```bash
# Eliminar colección manualmente
python -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8001)
try:
    client.delete_collection('test_collection')
    print('Collection deleted')
except:
    print('Collection does not exist')
"
```

---

## API Connection Problems

### Anthropic API: Invalid API Key

**Síntomas:**
```
anthropic.AuthenticationError: Invalid API key
```

**Diagnóstico:**
```bash
# Verificar API key configurada
cat .env.test | grep ANTHROPIC_API_KEY

# Verificar formato
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.test')
key = os.getenv('ANTHROPIC_API_KEY')
print(f'Key starts with: {key[:10]}...')
print(f'Valid format: {key.startswith(\"sk-ant-\")}')
"
```

**Soluciones:**

1. **Configurar API key válida:**
   ```bash
   # Obtener key de: https://console.anthropic.com/
   echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> .env.test
   ```

2. **Verificar que .env.test se está cargando:**
   ```bash
   # En pytest debe cargar automáticamente via pyproject.toml
   # Verificar en pyproject.toml:
   grep "env_files" pyproject.toml
   ```

### Anthropic API: Rate Limit Exceeded

**Síntomas:**
```
anthropic.RateLimitError: Rate limit exceeded
```

**Soluciones:**

1. **Esperar y reintentar:**
   ```bash
   # Esperar 60 segundos
   sleep 60

   # Ejecutar tests con menor paralelismo
   pytest -n 1  # Sequential
   ```

2. **Reducir frecuencia de tests:**
   ```bash
   # Ejecutar solo tests críticos
   pytest -m smoke

   # Ejecutar un test a la vez
   pytest -k "test_fibonacci" -m real_api
   ```

3. **Habilitar caché:**
   ```bash
   # En .env.test
   echo "RAG_CACHE_ENABLED=true" >> .env.test
   ```

### Anthropic API: Circuit Breaker Open

**Síntomas:**
```
CircuitBreakerError: Circuit breaker is OPEN
```

**Diagnóstico:**
```bash
# Ver estado del circuit breaker
# (requiere endpoint en API)
curl http://localhost:8000/api/v1/health/circuit-breaker
```

**Soluciones:**

1. **Esperar reset automático:**
   ```bash
   # Circuit breaker se cierra después de timeout
   sleep 60
   ```

2. **Restart servicio API:**
   ```bash
   docker compose restart api
   ```

3. **Deshabilitar para tests:**
   ```python
   # En conftest.py fixture
   AnthropicClient(
       api_key=api_key,
       enable_circuit_breaker=False  # Para tests
   )
   ```

---

## Test Failures

### Tests: Import Errors

**Síntomas:**
```
ImportError: No module named 'src'
```

**Soluciones:**

1. **Verificar PYTHONPATH:**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   pytest
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verificar directorio actual:**
   ```bash
   # Debe ejecutarse desde raíz del proyecto
   pwd  # Debe terminar en /agentic-ai
   cd /path/to/agentic-ai
   pytest
   ```

### Tests: Fixture Not Found

**Síntomas:**
```
fixture 'real_postgres_manager' not found
```

**Soluciones:**

1. **Verificar conftest.py existe:**
   ```bash
   ls tests/conftest.py
   ```

2. **Verificar fixture definida:**
   ```bash
   grep "real_postgres_manager" tests/conftest.py
   ```

3. **Recrear conftest.py:**
   ```bash
   # Copiar desde plan o repositorio
   ```

### Tests: ChromaDB Metadata Error

**Síntomas:**
```
ValueError: Expected metadata value to be a str, int, float, bool, or None, got list
```

**Solución:**
```python
# Convertir listas a strings separados por comas
metadata = {
    "tags": ",".join(tags_list),  # Correcto
    # "tags": tags_list  # ❌ Incorrecto
}
```

### Tests: Timing Out

**Síntomas:**
```
FAILED tests/... - Failed: Timeout >120s
```

**Soluciones:**

1. **Aumentar timeout:**
   ```bash
   # En pyproject.toml
   timeout = 180  # Aumentar de 120 a 180
   ```

2. **Ejecutar test individual:**
   ```bash
   pytest -v tests/integration/test_e2e_code_generation_real.py::test_fibonacci --timeout=300
   ```

3. **Verificar servicios no están lentos:**
   ```bash
   docker stats  # Verificar CPU/Memory
   ```

---

## Performance Issues

### Tests Muy Lentos

**Diagnóstico:**
```bash
# Ver tiempos de ejecución
pytest --durations=10
```

**Soluciones:**

1. **Ejecutar en paralelo (solo unit tests):**
   ```bash
   pytest -n auto -m unit
   ```

2. **Skip tests lentos:**
   ```bash
   pytest -m "not slow"
   ```

3. **Usar caché agresivamente:**
   ```bash
   # En .env.test
   RAG_CACHE_ENABLED=true
   RAG_CACHE_TTL_DAYS=30
   ```

### ChromaDB Retrieval Lento

**Síntomas:**
- Retrieval toma >2 segundos

**Soluciones:**

1. **Reducir dimensionalidad embedding:**
   ```bash
   # En .env.test
   RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2  # 384 dims (más rápido)
   # vs all-mpnet-base-v2  # 768 dims (más lento)
   ```

2. **Reducir top_k:**
   ```bash
   RAG_TOP_K=3  # En vez de 5 o más
   ```

3. **Habilitar caché de embeddings:**
   ```bash
   RAG_CACHE_ENABLED=true
   ```

---

## Monitoring Problems

### Prometheus No Scraping

**Síntomas:**
- Targets muestran "DOWN" en http://localhost:9090/targets

**Diagnóstico:**
```bash
# Ver targets
curl http://localhost:9090/api/v1/targets

# Ver logs de Prometheus
docker compose logs prometheus --tail 50
```

**Soluciones:**

1. **Verificar configuración:**
   ```bash
   # Validar prometheus.yml
   docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

2. **Verificar endpoints existen:**
   ```bash
   # API debe exponer métricas
   curl http://localhost:8000/api/v1/metrics/prometheus
   ```

3. **Restart Prometheus:**
   ```bash
   docker compose restart prometheus
   ```

### Grafana No Muestra Datos

**Síntomas:**
- Dashboard vacío o "No data"

**Diagnóstico:**
```bash
# Verificar datasource conectado
curl -u admin:admin http://localhost:3001/api/datasources

# Query directa a Prometheus
curl 'http://localhost:9090/api/v1/query?query=up'
```

**Soluciones:**

1. **Verificar datasource configurado:**
   ```bash
   # Debe estar en provisioning
   cat docker/grafana/provisioning/datasources/prometheus.yml
   ```

2. **Recrear datasource:**
   - Ir a Grafana → Configuration → Data Sources
   - Delete "Prometheus"
   - Add new Prometheus
   - URL: http://prometheus:9090

3. **Verificar queries en dashboard:**
   - Edit panel
   - Verificar query syntax
   - Test query directamente

---

## Emergency Procedures

### Complete System Reset

```bash
# ⚠️ ESTO BORRA TODO

# 1. Stop everything
docker compose down -v

# 2. Remove all containers
docker rm -f $(docker ps -a -q)

# 3. Remove volumes
docker volume prune -f

# 4. Restart from scratch
docker compose up -d postgres redis chromadb

# 5. Wait for healthy
sleep 30

# 6. Recreate test database
python scripts/setup_test_database.py

# 7. Seed RAG
python scripts/seed_rag_examples.py

# 8. Validate
python scripts/validate_local_production.py
```

### Recover from Corrupted State

```bash
# 1. Backup current state (if possible)
mkdir -p recovery/$(date +%Y%m%d_%H%M%S)
docker cp devmatrix-postgres:/var/lib/postgresql/data recovery/$(date +%Y%m%d_%H%M%S)/postgres || true

# 2. Stop services
docker compose down

# 3. Clear workspace
rm -rf workspace_test/

# 4. Restart services
docker compose up -d

# 5. Recreate everything
python scripts/setup_test_database.py
python scripts/seed_rag_examples.py
mkdir -p workspace_test && cd workspace_test && git init && cd ..

# 6. Validate
python scripts/validate_local_production.py
```

---

## Getting More Help

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > diagnostic_report.txt <<EOF
=== System Info ===
$(uname -a)
$(docker --version)
$(docker compose version)
$(python --version)

=== Docker Services ===
$(docker compose ps)

=== Service Logs ===
$(docker compose logs --tail 20)

=== Environment ===
$(cat .env.test | grep -v API_KEY | grep -v PASSWORD)

=== Test Results ===
$(pytest --collect-only 2>&1 | tail -50)
EOF

echo "Diagnostic report saved to: diagnostic_report.txt"
```

### Enable Debug Logging

```bash
# En .env.test
LOG_LEVEL=DEBUG

# En pytest
pytest -v -s --log-cli-level=DEBUG

# En Docker logs
docker compose logs -f --tail 100
```

---

**Last Updated**: 2025-10-17
**Version**: 1.0
