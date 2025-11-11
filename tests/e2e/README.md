# MGE V2 E2E Tests

End-to-end tests para validar el pipeline completo de MGE V2 desde el request del usuario hasta el código generado y listo para ejecutar.

## Tests Disponibles

### 1. `test_complete_mge_v2_pipeline_fastapi`
Test completo del pipeline para un proyecto FastAPI.

**Duración esperada:** ~12 minutos
**Costo esperado:** ~$7

**Valida:**
- ✅ Discovery (DDD analysis)
- ✅ MasterPlan generation (120+ tasks)
- ✅ Code generation (LLM)
- ✅ Atomization (10 LOC atoms)
- ✅ Wave execution
- ✅ File writing
- ✅ Infrastructure generation (Docker, configs)

### 2. `test_mge_v2_performance_benchmark`
Benchmark de performance para medir tiempos de cada fase.

**Duración esperada:** ~10 minutos

**Targets:**
- Discovery: < 30s
- MasterPlan: < 90s
- Code Generation: < 300s
- Total: < 720s (12 min)

## Requisitos

### 1. Base de Datos Test
```bash
# Crear base de datos de test
createdb -U devmatrix devmatrix_test

# O con Docker
docker exec devmatrix-postgres createdb -U devmatrix devmatrix_test
```

### 2. Variables de Entorno
```bash
# .env o export
export ANTHROPIC_API_KEY="sk-ant-..."
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="devmatrix_test"
export POSTGRES_USER="devmatrix"
export POSTGRES_PASSWORD="devmatrix"
```

### 3. Dependencias
```bash
pip install pytest pytest-asyncio
```

## Ejecución

### Ejecutar todos los tests E2E
```bash
cd /home/kwar/code/agentic-ai
pytest tests/e2e/ -v -s --tb=short
```

### Ejecutar test específico
```bash
# Test completo
pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_complete_mge_v2_pipeline_fastapi -v -s

# Benchmark
pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_mge_v2_performance_benchmark -v -s
```

### Ejecutar con marcadores
```bash
# Solo tests E2E
pytest -m e2e -v -s

# Solo benchmarks
pytest -m benchmark -v -s
```

## Output Esperado

```
🚀 Starting MGE V2 E2E Test - FastAPI Project
================================================================================

📝 User Request: Create a FastAPI REST API for task management system...
👤 User ID: 73f995ee-a911-4a81-8420-0c49908cc80d
🔑 Session ID: abc123...

📊 Streaming events:

[10:15:30] 📍 discovery: Analyzing request and extracting domain information...
[10:15:35] 📍 discovery: Generating...
[10:16:00] ✅ COMPLETE: Discovery Document created successfully

[10:16:05] 📍 masterplan_generation: Generating MasterPlan (120 tasks)...
[10:17:30] ✅ COMPLETE: MasterPlan generated successfully

[10:17:35] 📍 code_generation: Generating code for 120 tasks...
[10:22:30] ✅ COMPLETE: Code generation complete: 120 tasks → 8,500 LOC

[10:22:35] 📍 atomization: Atomizing generated code into 10 LOC atoms...
[10:23:30] ✅ COMPLETE: Atomization complete: 850 atoms created

[10:23:35] 📍 execution: Starting wave-based execution (850 atoms)...
[10:26:30] ✅ COMPLETE: Wave execution complete: 8 waves

[10:26:35] 📍 file_writing: Writing 850 atoms to workspace...
[10:26:40] ✅ COMPLETE: Successfully wrote 45 files

[10:26:45] 📍 infrastructure_generation: Generating project infrastructure...
[10:26:47] ✅ COMPLETE: Infrastructure generated: 6 files (fastapi)

================================================================================
📊 E2E Test Results
================================================================================

🔍 PHASE 1: Discovery Validation
   ✅ Discovery ID: abc123...
   ✅ Domain: Task Management
   ✅ Bounded Contexts: 3
   ✅ Aggregates: 8
   ✅ Entities: 12

📋 PHASE 2: MasterPlan Validation
   ✅ MasterPlan ID: def456...
   ✅ Project Name: task-management-api
   ✅ Total Phases: 6
   ✅ Total Milestones: 18
   ✅ Total Tasks: 120

💻 PHASE 3: Code Generation Validation
   ✅ Tasks with code: 120/120
   ✅ Total LOC generated: 8,500
   ✅ Avg LOC per task: 71
   ✅ Total generation cost: $6.80

⚛️  PHASE 4: Atomization Validation
   ✅ Total atoms: 850
   ✅ Avg LOC per atom: 10.0
   ✅ Avg atomicity score: 92.5%
   ✅ Atoms with dependencies: 320

📁 PHASE 5: File Writing Validation
   ✅ Workspace path: /tmp/mge_v2_workspace/def456.../task-management-api
   ✅ Python files generated: 45
   ✅ Workspace exists: True

🏗️  PHASE 6: Infrastructure Validation
   ✅ Dockerfile: True
   ✅ docker-compose.yml: True
   ✅ .env.example: True
   ✅ .gitignore: True
   ✅ requirements.txt: True
   ✅ README.md: True

🎯 PHASE 7: Final Validation
   ✅ Total tasks: 120
   ✅ Total atoms: 850
   ✅ Total waves: 8
   ✅ Execution time: 180.5s

⏱️  PERFORMANCE SUMMARY
   ✅ Total duration: 677.2s (11.3 min)
   ✅ Total cost: $6.80
   ✅ Tasks generated: 120
   ✅ Atoms generated: 850
   ✅ Files written: 45

================================================================================
✅ E2E Test PASSED!
================================================================================
```

## Troubleshooting

### Error: "Database not found"
```bash
# Crear base de datos de test
createdb -U devmatrix devmatrix_test
```

### Error: "ANTHROPIC_API_KEY not set"
```bash
# Agregar a .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Error: "Connection refused"
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps
docker-compose up -d devmatrix-postgres
```

### Test toma mucho tiempo
Esto es normal! El pipeline completo tarda ~10-12 minutos porque:
- Code generation: ~5 minutos (120 tasks con LLM)
- Atomization: ~1 minuto (parsing 8K LOC)
- Wave execution: ~3 minutos (850 atoms en 8 waves)

### Workspace no se crea
Verificar permisos:
```bash
mkdir -p /tmp/mge_v2_workspace
chmod 777 /tmp/mge_v2_workspace
```

## Limpieza

### Limpiar workspaces de test
```bash
rm -rf /tmp/mge_v2_workspace/*
```

### Limpiar base de datos de test
```bash
dropdb -U devmatrix devmatrix_test
createdb -U devmatrix devmatrix_test
```

## Métricas de Éxito

### ✅ Test Pasa Si:
- Todas las fases completan sin errores
- MasterPlan genera ≥ 50 tasks
- Code generation genera ≥ 5,000 LOC
- Atomization crea ≥ 500 atoms
- Files se escriben correctamente
- Infrastructure files existen
- Duración < 720s (12 min)
- Costo < $10

### ⚠️ Test Falla Si:
- Alguna fase no completa
- Errores de LLM
- Atomization falla
- Workspace no se crea
- Duración > 720s
- Costo > $10

## Next Steps

Después de ejecutar el test exitosamente:

1. **Deploy a Staging**
   ```bash
   docker-compose -f docker-compose.staging.yml up -d
   ```

2. **Monitor Performance**
   - Grafana dashboard
   - CloudWatch metrics
   - Sentry error tracking

3. **Gradual Rollout**
   - 10% traffic → staging
   - Monitor 24h
   - 50% traffic
   - Monitor 48h
   - 100% traffic

## Referencias

- **MGE V2 Docs:** `DOCS/MGE_V2/`
- **Status Report:** `DOCS/mge_v2_final_status_report.md`
- **Implementation Plan:** `DOCS/mge_v2_analysis_and_implementation_plan.md`
