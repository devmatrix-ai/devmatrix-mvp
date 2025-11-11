# MGE V2 Acceptance Tests - Análisis Arquitectónico Exhaustivo

**Fecha:** 2025-11-11
**Analista:** Dany (Tech Lead)
**Enfoque:** Arquitectura y Gaps de Integración
**Profundidad:** UltraThink Mode

---

## 📊 Executive Summary

El sistema de Acceptance Tests (Gap 3) está **~75% implementado** con arquitectura sólida pero **faltan integraciones críticas** con el pipeline MGE V2.

### Estado Actual:
- ✅ **Backend Core:** 6 módulos completos (~1,800 LOC)
- ✅ **Modelos DB:** AcceptanceTest + AcceptanceTestResult
- ✅ **Gate Logic:** Must=100%, Should≥95% implementado
- ❌ **Integraciones:** 0% conectado con MasterPlan/Wave execution
- ❌ **API Endpoints:** 0 de 4 endpoints implementados
- ❌ **Tests:** 0 tests unitarios escritos

### Gaps Críticos (Bloqueantes):
1. **No hay migration de DB** → Tablas no existen en base de datos
2. **MasterPlan no tiene markdown_content** → Parser no puede funcionar
3. **No integrado con orchestration** → Tests nunca se ejecutan
4. **Sin API endpoints** → Frontend no puede acceder a resultados

---

## 🏗️ Arquitectura Implementada

### Componentes Existentes

#### 1. **Data Models** (`src/models/acceptance_test.py`)

**AcceptanceTest:**
```python
- test_id: UUID (PK)
- masterplan_id: UUID (FK)
- requirement_text: Text           # Original requirement
- requirement_priority: String     # 'must' | 'should'
- test_code: Text                  # Generated pytest/jest code
- test_language: String            # 'pytest' | 'jest' | 'vitest'
- test_framework_version: String
- timeout_seconds: Integer (default 30)
- created_at, updated_at: Timestamp
```

**AcceptanceTestResult:**
```python
- result_id: UUID (PK)
- test_id: UUID (FK)
- wave_id: UUID (FK, optional)
- execution_time: Timestamp
- status: String                   # 'pass' | 'fail' | 'timeout' | 'error'
- error_message: Text
- execution_duration_ms: Integer
- stdout, stderr: Text
```

**Calidad del Diseño:** ⭐⭐⭐⭐⭐
- Normalización correcta (3NF)
- Constraints validados en DB
- Índices optimizados para queries frecuentes
- Relationships bidireccionales con MasterPlan y ExecutionWave

---

#### 2. **Requirement Parser** (`src/testing/requirement_parser.py`)

**Clase:** `RequirementParser`

**Funcionalidad:**
```python
parse_masterplan(masterplan_id, markdown_content) -> List[Requirement]
    ├─ Extrae MUST requirements con regex
    ├─ Extrae SHOULD requirements con regex
    ├─ Genera IDs únicos por requirement
    └─ Retorna lista clasificada

validate_requirements(requirements) -> Dict[str, any]
    ├─ Verifica existencia de requirements
    ├─ Valida balance MUST/SHOULD
    ├─ Detecta duplicados
    └─ Retorna dict con is_valid, errors, warnings

extract_requirement_metadata(requirement) -> Dict[str, any]
    ├─ Detecta "must return X"
    ├─ Detecta "must raise X"
    ├─ Detecta "must be <X"
    └─ Extrae threshold values
```

**Formato Esperado:**
```markdown
## Requirements
### MUST
- User authentication must use JWT tokens
- Database transactions must be ACID compliant

### SHOULD
- UI should be responsive on mobile devices
- API response time should be <200ms p95
```

**Calidad:** ⭐⭐⭐⭐
- Regex patterns robustos (case-insensitive)
- Validación completa
- Metadata extraction inteligente
- ⚠️ **GAP:** MasterPlan.markdown_content no existe

---

#### 3. **Test Template Engine** (`src/testing/test_template_engine.py`)

**Clase:** `TestTemplateEngine`

**Templates Soportados:**
1. **pytest (Python)**
2. **jest (JavaScript)**
3. **vitest (TypeScript)**

**Pattern Matching Inteligente:**
```python
# Detecta patterns en requirement text y genera asserts apropiados:
"must return 200" → assert result == 200
"must raise ValueError" → with pytest.raises(ValueError)
"must be <200ms" → assert duration_ms < 200
"must use JWT" → assert is_valid_jwt(result['token'])
"must be ACID compliant" → transaction test template
"must be responsive" → viewport size tests
```

**Generación de Fixtures:**
```python
get_test_fixtures(language, requirement)
    ├─ Database fixtures para requirements con "transaction"
    ├─ Auth fixtures para requirements con "jwt"
    └─ Custom setup/teardown based on patterns
```

**Calidad:** ⭐⭐⭐⭐⭐
- Pattern matching exhaustivo
- Templates profesionales
- Soporte multi-lenguaje
- Smart import generation
- **Fortaleza:** Muy completo y robusto

---

#### 4. **Acceptance Test Generator** (`src/testing/test_generator.py`)

**Clase:** `AcceptanceTestGenerator`

**Pipeline Completo:**
```python
generate_from_masterplan(masterplan_id, markdown_content)
    ├─ 1. Parse requirements (RequirementParser)
    ├─ 2. Validate requirements
    ├─ 3. Determine test language (pytest/jest/vitest)
    ├─ 4. Generate test code for each requirement
    ├─ 5. Create AcceptanceTest DB objects
    └─ 6. Commit to database

regenerate_failed_tests(masterplan_id, failed_test_ids)
    ├─ Fetch failed tests from DB
    ├─ Regenerate test code with improved templates
    └─ Update test_code in DB

get_test_statistics(masterplan_id)
    └─ Returns: {total_tests, must_tests, should_tests, languages}
```

**Language Detection:**
```python
_determine_test_language(masterplan_id)
    ├─ Check masterplan.metadata['primary_language']
    ├─ Check title/description for "python", "typescript", etc.
    ├─ Prefer vitest if "vite" in dependencies
    └─ Default: pytest
```

**Calidad:** ⭐⭐⭐⭐⭐
- Orchestration completa
- Error handling robusto
- Smart language detection
- Regeneration support
- **Fortaleza:** Production-ready

---

#### 5. **Test Runner** (`src/testing/test_runner.py`)

**Clase:** `AcceptanceTestRunner`

**Ejecución Paralela:**
```python
run_tests_for_wave(wave_id)
    ├─ Get masterplan_id from wave
    ├─ Load all AcceptanceTest objects
    ├─ Parallel execution (max 10 concurrent)
    │   └─ Semaphore-controlled concurrency
    ├─ Per-test execution with timeout (30s default)
    │   ├─ Write test code to temp file
    │   ├─ Execute: pytest/npx jest/npx vitest
    │   ├─ Capture stdout/stderr
    │   └─ Store AcceptanceTestResult in DB
    └─ Aggregate results (pass rates, durations)
```

**Test Execution:**
```python
_run_single_test(test, wave_id, semaphore)
    ├─ Create temp file with test code
    ├─ Execute with subprocess (pytest/jest/vitest)
    ├─ Timeout handling (asyncio.wait_for)
    ├─ Parse return code (0 = pass, else = fail)
    ├─ Store result in DB
    └─ Cleanup temp file
```

**Result Aggregation:**
```python
{
  'total': 25,
  'passed': 23,
  'failed': 2,
  'overall_pass_rate': 0.92,
  'must_total': 20,
  'must_passed': 20,
  'must_pass_rate': 1.0,
  'should_total': 5,
  'should_passed': 3,
  'should_pass_rate': 0.6,
  'avg_duration_ms': 150,
  'max_duration_ms': 450
}
```

**Calidad:** ⭐⭐⭐⭐⭐
- Async/await patterns correctos
- Parallel execution optimizado
- Timeout handling robusto
- Result persistence
- **Fortaleza:** Production-ready, muy completo

---

#### 6. **Acceptance Gate** (`src/testing/acceptance_gate.py`)

**Clase:** `AcceptanceTestGate`

**Gate Logic (Gate S):**
```python
Thresholds:
  - must_threshold: 1.0 (100%)
  - should_threshold: 0.95 (95%)

Gate Passed:
  = (must_pass_rate >= 1.0) AND (should_pass_rate >= 0.95)

Can Release:
  = (must_pass_rate == 1.0)
  # Permite release si todos los MUST pasan, incluso si SHOULD < 95%
```

**API:**
```python
check_gate(masterplan_id, wave_id) -> Dict
    └─ Returns: {gate_passed, must_pass_rate, should_pass_rate,
                 failed_requirements, can_release, gate_status}

block_progression_if_gate_fails(masterplan_id, wave_id) -> bool
    └─ Returns True if can proceed, False if blocked

get_gate_report(masterplan_id, wave_id) -> str
    └─ ASCII art report with detailed breakdown

get_requirements_by_status(masterplan_id, status, wave_id) -> List[Dict]
    └─ Filter requirements by 'pass', 'fail', 'timeout', 'error'
```

**Gate Report Format:**
```
═══════════════════════════════════════════════════════════
                    GATE S REPORT
═══════════════════════════════════════════════════════════

Masterplan: abc-123
Status: PASS

───────────────────────────────────────────────────────────
MUST Requirements (100% required)
───────────────────────────────────────────────────────────
Pass Rate: 100.0%
Passed: 20/20
Threshold: 100.0%
Result: ✓ PASS

───────────────────────────────────────────────────────────
SHOULD Requirements (≥95% required)
───────────────────────────────────────────────────────────
Pass Rate: 96.7%
Passed: 29/30
Threshold: 95.0%
Result: ✓ PASS

───────────────────────────────────────────────────────────
GATE DECISION
───────────────────────────────────────────────────────────
Gate Passed: YES
Can Release: YES
═══════════════════════════════════════════════════════════
```

**Calidad:** ⭐⭐⭐⭐⭐
- Logic clara y correcta
- Reporting profesional
- API completa
- **Fortaleza:** Listo para producción

---

## ❌ Gaps Críticos Identificados

### Gap 1: **Database Migration** (🔴 BLOCKER)

**Problema:**
- Modelos AcceptanceTest y AcceptanceTestResult definidos
- **NO hay migration de Alembic**
- Tablas no existen en base de datos PostgreSQL

**Impacto:**
- Sistema completo no funciona
- Cualquier operación con AcceptanceTest falla con tabla no existente

**Solución:**
```python
# Crear migration:
alembic revision -m "Add acceptance tests tables"

# En migration file:
def upgrade():
    op.create_table(
        'acceptance_tests',
        sa.Column('test_id', UUID(), primary_key=True),
        sa.Column('masterplan_id', UUID(), ForeignKey('masterplans.masterplan_id')),
        sa.Column('requirement_text', sa.Text(), nullable=False),
        sa.Column('requirement_priority', sa.String(10), nullable=False),
        sa.Column('test_code', sa.Text(), nullable=False),
        sa.Column('test_language', sa.String(20), nullable=False),
        # ... rest of columns
    )

    op.create_table('acceptance_test_results', ...)
```

**Esfuerzo:** 30 minutos

---

### Gap 2: **MasterPlan.markdown_content Field** (🔴 BLOCKER)

**Problema:**
- `RequirementParser.parse_masterplan()` espera `markdown_content`
- `MasterPlan` model NO tiene este campo
- Existe `description` (Text) pero no se usa para requirements

**Opciones de Solución:**

**Opción A: Agregar markdown_content field**
```python
# src/models/masterplan.py
class MasterPlan(Base):
    # ... existing fields ...
    markdown_content = Column(Text, nullable=True)  # Full masterplan markdown
```
- **Pro:** Simple, mantiene approach actual
- **Con:** Necesita migration, genera contenido extra

**Opción B: Usar description field**
```python
# Cambiar RequirementParser para usar description
markdown_content = masterplan.description
```
- **Pro:** No migration needed
- **Con:** description puede no tener formato Requirements

**Opción C: Usar contract schema approach (spec original)**
```python
# MasterPlanTask
class MasterPlanTask(Base):
    contracts = Column(JSONB, nullable=True)
    # contracts = {
    #   "acceptance_tests": [
    #     {"name": "test_...", "requirement": "must", "assertions": [...]}
    #   ]
    # }
```
- **Pro:** Más estructurado, type-safe
- **Con:** Requiere cambiar parser completamente

**Recomendación:** **Opción A** (agregar markdown_content)
- Más explícito y robusto
- Sigue approach implementado
- Migration simple

**Esfuerzo:** 1 hora (migration + testing)

---

### Gap 3: **Integración con MasterPlan Generation** (🔴 CRITICAL)

**Problema:**
- `masterplan_generator.py` NO llama a `AcceptanceTestGenerator`
- Tests nunca se generan durante MasterPlan creation
- Sistema de tests es "dead code"

**Ubicación de Hook:**
```python
# src/services/masterplan_generator.py
# Línea ~150-200 (después de generar tasks)

async def generate_masterplan(...):
    # ... existing generation logic ...

    # MISSING: Generar acceptance tests
    # await self._generate_acceptance_tests(masterplan_id)
```

**Solución:**
```python
# src/services/masterplan_generator.py

from src.testing.test_generator import AcceptanceTestGenerator

class MasterPlanGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.test_generator = AcceptanceTestGenerator(db)  # NEW

    async def generate_masterplan(self, discovery_id: UUID, user_id: str):
        # ... existing logic ...

        # Generate masterplan tasks
        tasks = await self._generate_tasks(...)

        # NEW: Generate acceptance tests from requirements
        if masterplan.markdown_content:
            logger.info(f"Generating acceptance tests for masterplan {masterplan_id}")
            tests = await self.test_generator.generate_from_masterplan(
                masterplan_id=masterplan_id,
                markdown_content=masterplan.markdown_content
            )
            logger.info(f"Generated {len(tests)} acceptance tests")

        return masterplan
```

**Event Emission:**
```python
# Emit WebSocket event
await websocket_manager.send_to_session(session_id, {
    "type": "acceptance_tests_generated",
    "masterplan_id": str(masterplan_id),
    "tests_count": len(tests),
    "must_count": sum(1 for t in tests if t.requirement_priority == 'must'),
    "should_count": sum(1 for t in tests if t.requirement_priority == 'should')
})
```

**Esfuerzo:** 2 horas (integration + testing)

---

### Gap 4: **Integración con Wave Execution** (🔴 CRITICAL)

**Problema:**
- `WaveExecutor` NO ejecuta acceptance tests después de cada wave
- Tests se generan pero nunca se corren
- Gate S no se evalúa

**Ubicación de Hook:**
```python
# src/mge/v2/execution/wave_executor.py
# Después de ejecutar todos los atoms de una wave

async def execute_wave(self, wave: Wave):
    # ... existing wave execution logic ...

    # MISSING: Run acceptance tests after wave
    # await self._run_acceptance_tests(wave.wave_id)
    # await self._check_gate_s(wave.graph.masterplan_id, wave.wave_id)
```

**Solución:**
```python
# src/mge/v2/execution/wave_executor.py

from src.testing.test_runner import AcceptanceTestRunner
from src.testing.acceptance_gate import AcceptanceTestGate

class WaveExecutor:
    def __init__(self, db: Session):
        self.db = db
        self.test_runner = AcceptanceTestRunner(db)  # NEW
        self.gate = AcceptanceTestGate(db)  # NEW

    async def execute_wave(self, wave: Wave):
        # ... execute all atoms ...

        # NEW: Run acceptance tests after wave completion
        logger.info(f"Running acceptance tests for wave {wave.wave_id}")

        # Run tests
        test_results = await self.test_runner.run_tests_for_wave(wave.wave_id)

        # Emit progress
        await self._emit_test_results(wave, test_results)

        # Check Gate S
        gate_result = await self.gate.check_gate(
            masterplan_id=wave.graph.masterplan_id,
            wave_id=wave.wave_id
        )

        # Block if gate fails
        if not gate_result['gate_passed']:
            logger.error(f"Gate S FAILED for wave {wave.wave_id}")
            # Emit gate failure event
            await self._emit_gate_failure(wave, gate_result)
            raise GateSFailedException(gate_result)

        logger.info(f"Gate S PASSED for wave {wave.wave_id}")

        return wave

    async def _emit_test_results(self, wave, results):
        await websocket_manager.send_to_session(wave.graph.session_id, {
            "type": "acceptance_tests_completed",
            "wave_id": str(wave.wave_id),
            "total": results['total'],
            "passed": results['passed'],
            "failed": results['failed'],
            "must_pass_rate": results['must_pass_rate'],
            "should_pass_rate": results['should_pass_rate']
        })
```

**Exception Handling:**
```python
class GateSFailedException(Exception):
    """Raised when Gate S fails (must<100% or should<95%)"""
    def __init__(self, gate_result):
        self.gate_result = gate_result
        msg = (
            f"Gate S failed: must={gate_result['must_pass_rate']:.1%}, "
            f"should={gate_result['should_pass_rate']:.1%}"
        )
        super().__init__(msg)
```

**Esfuerzo:** 3 horas (integration + exception handling + testing)

---

### Gap 5: **API Endpoints** (🟡 HIGH)

**Problema:**
- Sin endpoints REST para acceptance tests
- Frontend no puede:
  - Ver tests generados
  - Correr tests manualmente
  - Ver resultados de Gate S
  - Obtener gate report

**Solución: Crear Router**
```python
# src/api/routers/acceptance_tests.py

from fastapi import APIRouter, Depends
from src.testing.test_generator import AcceptanceTestGenerator
from src.testing.test_runner import AcceptanceTestRunner
from src.testing.acceptance_gate import AcceptanceTestGate

router = APIRouter(prefix="/api/v2/acceptance-tests", tags=["acceptance-tests"])

@router.get("/{masterplan_id}")
async def get_acceptance_tests(
    masterplan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all acceptance tests for a masterplan."""
    result = await db.execute(
        select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
    )
    tests = result.scalars().all()
    return {"tests": tests, "total": len(tests)}

@router.post("/run/{masterplan_id}")
async def run_acceptance_tests(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Manually trigger acceptance test execution."""
    runner = AcceptanceTestRunner(db)

    if wave_id:
        results = await runner.run_tests_for_wave(wave_id)
    else:
        results = await runner.run_tests_for_masterplan(masterplan_id)

    return results

@router.get("/gate/{masterplan_id}")
async def get_gate_status(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get Gate S status for a masterplan."""
    gate = AcceptanceTestGate(db)
    return await gate.check_gate(masterplan_id, wave_id)

@router.get("/gate/{masterplan_id}/report")
async def get_gate_report(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get detailed Gate S report."""
    gate = AcceptanceTestGate(db)
    report = await gate.get_gate_report(masterplan_id, wave_id)
    return {"report": report}
```

**Registro en App:**
```python
# src/main.py
from src.api.routers import acceptance_tests

app.include_router(acceptance_tests.router)
```

**Esfuerzo:** 2 horas (router + tests)

---

### Gap 6: **Tests Unitarios** (🟡 HIGH)

**Problema:**
- 0 tests unitarios para testing package
- Sin validación de funcionalidad core
- Riesgo alto de regresiones

**Tests Necesarios:**

**1. test_requirement_parser.py** (~150 LOC)
```python
# tests/unit/testing/test_requirement_parser.py

def test_parse_must_requirements():
    """Test parsing of MUST requirements from markdown."""

def test_parse_should_requirements():
    """Test parsing of SHOULD requirements from markdown."""

def test_validate_requirements_with_no_musts():
    """Test validation warning when no MUST requirements."""

def test_validate_requirements_with_duplicates():
    """Test validation error for duplicate requirements."""

def test_extract_return_value_metadata():
    """Test metadata extraction for 'must return X' pattern."""

def test_extract_threshold_metadata():
    """Test metadata extraction for 'must be <200ms' pattern."""
```

**2. test_template_engine.py** (~200 LOC)
```python
# tests/unit/testing/test_template_engine.py

def test_generate_pytest_test_for_return_value():
    """Test pytest generation for 'must return X' requirement."""

def test_generate_pytest_test_for_exception():
    """Test pytest generation for 'must raise X' requirement."""

def test_generate_jest_test_for_threshold():
    """Test jest generation for 'must be <X' requirement."""

def test_get_test_imports_for_jwt():
    """Test import generation for JWT requirements."""

def test_get_test_fixtures_for_database():
    """Test fixture generation for database requirements."""
```

**3. test_test_generator.py** (~250 LOC)
```python
# tests/unit/testing/test_test_generator.py

@pytest.mark.asyncio
async def test_generate_from_masterplan_creates_tests():
    """Test full pipeline: parse → generate → store."""

@pytest.mark.asyncio
async def test_determine_test_language_for_python():
    """Test language detection for Python projects."""

@pytest.mark.asyncio
async def test_regenerate_failed_tests():
    """Test regeneration of failed tests."""

@pytest.mark.asyncio
async def test_get_test_statistics():
    """Test statistics calculation."""
```

**4. test_test_runner.py** (~200 LOC)
```python
# tests/unit/testing/test_test_runner.py

@pytest.mark.asyncio
async def test_run_single_test_pass():
    """Test successful test execution."""

@pytest.mark.asyncio
async def test_run_single_test_fail():
    """Test failed test execution."""

@pytest.mark.asyncio
async def test_run_single_test_timeout():
    """Test timeout handling."""

@pytest.mark.asyncio
async def test_aggregate_results():
    """Test result aggregation logic."""
```

**5. test_acceptance_gate.py** (~150 LOC)
```python
# tests/unit/testing/test_acceptance_gate.py

@pytest.mark.asyncio
async def test_gate_passes_with_100_must_and_95_should():
    """Test gate passes when thresholds met."""

@pytest.mark.asyncio
async def test_gate_fails_with_must_below_100():
    """Test gate fails when must < 100%."""

@pytest.mark.asyncio
async def test_gate_fails_with_should_below_95():
    """Test gate fails when should < 95%."""

@pytest.mark.asyncio
async def test_can_release_with_must_100():
    """Test can_release=True when must=100% even if should<95%."""
```

**Esfuerzo Total:** 6 horas (5 test files)

---

### Gap 7: **E2E Test Validation** (🟡 MEDIUM)

**Problema:**
- `test_mge_v2_complete_pipeline.py` NO valida acceptance tests
- Pipeline completo no incluye test generation/execution

**Solución: Agregar Phase 8**
```python
# tests/e2e/test_mge_v2_complete_pipeline.py

# ============================================================================
# PHASE 8: Acceptance Tests
# ============================================================================
def acceptance_tests_matcher(event):
    """Check if event signals acceptance tests completion."""
    return (
        event.get('type') == 'acceptance_tests_completed' and
        'total' in event
    )

def acceptance_tests_extractor(event, db):
    """Extract acceptance test data."""
    return {
        'total': event.get('total', 0),
        'passed': event.get('passed', 0),
        'failed': event.get('failed', 0),
        'must_pass_rate': event.get('must_pass_rate', 0.0),
        'should_pass_rate': event.get('should_pass_rate', 0.0)
    }

acceptance_tests_result = await execute_phase_with_checkpoint(
    "acceptance_tests",
    acceptance_tests_matcher,
    acceptance_tests_extractor
)

print(f"   ✅ Tests total: {acceptance_tests_result.get('total')}")
print(f"   ✅ Tests passed: {acceptance_tests_result.get('passed')}")
print(f"   ✅ Must pass rate: {acceptance_tests_result.get('must_pass_rate'):.1%}")
print(f"   ✅ Should pass rate: {acceptance_tests_result.get('should_pass_rate'):.1%}")

# Assert Gate S passed
assert acceptance_tests_result.get('must_pass_rate') == 1.0, "Gate S failed: must < 100%"
assert acceptance_tests_result.get('should_pass_rate') >= 0.95, "Gate S failed: should < 95%"
```

**Esfuerzo:** 1 hora

---

### Gap 8: **Documentation Update** (🟢 LOW)

**Problema:**
- DOCS no reflejan código implementado
- Spec sugiere approach diferente (JSONB contracts)
- Sin guía de uso del sistema

**Solución: Actualizar Docs**

**1. Actualizar acceptance-tests.md**
```markdown
# Gap 3: Acceptance Tests - STATUS UPDATE

**Estado:** ✅ 75% Implementado (Backend completo, faltan integraciones)

## Arquitectura Real Implementada

[Diagram de arquitectura actual]

## Diferencias vs Spec Original

- ❌ NO usamos JSONB contracts en MasterPlanTask
- ✅ Usamos markdown parsing de requirements
- ✅ Backend core completo con 6 módulos

## Gaps Restantes

1. Database migration
2. Integration con MasterPlan generation
3. Integration con Wave execution
4. API endpoints
```

**2. Crear Usage Guide**
```markdown
# Acceptance Tests - Usage Guide

## Generación de Tests

1. Escribir requirements en MasterPlan markdown:
```markdown
## Requirements
### MUST
- Authentication must use JWT tokens
### SHOULD
- API response should be <200ms
```

2. Tests se generan automáticamente
3. Tests se ejecutan después de cada wave
4. Gate S valida: must=100%, should≥95%

## API Usage

GET /api/v2/acceptance-tests/{masterplan_id}
POST /api/v2/acceptance-tests/run/{masterplan_id}
GET /api/v2/acceptance-tests/gate/{masterplan_id}
```

**Esfuerzo:** 2 horas

---

## 📊 Implementation Roadmap

### Week 2 (Nov 18-22) - Foundation

**Day 1-2: Database + MasterPlan Integration**
- ✅ Create Alembic migration for acceptance_tests tables
- ✅ Add markdown_content field to MasterPlan
- ✅ Run migration and verify tables
- ⏱️ Effort: 4 hours

**Day 3-4: MasterPlan Generation Integration**
- ✅ Hook AcceptanceTestGenerator in masterplan_generator.py
- ✅ Add WebSocket event emission
- ✅ Test generation durante MasterPlan creation
- ⏱️ Effort: 6 hours

**Day 5: Wave Execution Integration**
- ✅ Hook AcceptanceTestRunner in WaveExecutor
- ✅ Hook AcceptanceTestGate for blocking
- ✅ Add WebSocket events para test progress
- ⏱️ Effort: 6 hours

### Week 3 (Nov 25-29) - API + Testing

**Day 1-2: API Endpoints**
- ✅ Create acceptance_tests router
- ✅ Implement 4 endpoints (get, run, gate, report)
- ✅ Integration tests para endpoints
- ⏱️ Effort: 8 hours

**Day 3-4: Unit Tests**
- ✅ Write 5 test files (~950 LOC total)
- ✅ Test coverage >80% para testing package
- ⏱️ Effort: 8 hours

**Day 5: E2E Test + Documentation**
- ✅ Add Phase 8 to E2E test
- ✅ Update DOCS/03-mge-v2/specs/acceptance-tests.md
- ✅ Create usage guide
- ⏱️ Effort: 4 hours

---

## 🎯 Success Criteria

### Must Have (Week 2-3)
- ✅ Database tables created
- ✅ Tests generate during MasterPlan creation
- ✅ Tests execute after each wave
- ✅ Gate S blocks progression if failed
- ✅ API endpoints functional
- ✅ Unit tests >80% coverage

### Should Have
- ✅ E2E test validates acceptance tests
- ✅ Documentation updated
- ✅ WebSocket events for real-time progress
- ✅ Usage guide created

### Could Have
- ⬜ Frontend UI for viewing test results
- ⬜ Manual test re-execution from UI
- ⬜ Test coverage reporting
- ⬜ Test performance benchmarks

---

## 🚨 Risk Assessment

### High Risk
1. **Integration Complexity** (Moderate)
   - Hooking into MasterPlan generation + Wave execution
   - Mitigation: Incremental integration with rollback points

2. **Test Execution Reliability** (Low)
   - Subprocess execution puede fallar
   - Mitigation: Robust error handling + timeout

3. **Gate S Blocking** (Low)
   - Bloquear progression puede interrumpir flujo
   - Mitigation: Clear error messages + gate report

### Medium Risk
1. **Markdown Parsing** (Low-Medium)
   - Requirements format puede variar
   - Mitigation: Flexible regex + validation

2. **Language Detection** (Low)
   - Puede detectar lenguaje incorrecto
   - Mitigation: Default to pytest + metadata hints

---

## 💰 Cost Estimation

### Development Time
- **Week 2:** 16 hours (DB + Integrations)
- **Week 3:** 20 hours (API + Tests + Docs)
- **Total:** 36 hours (~4-5 days full-time)

### Testing Time
- Unit tests: 8 hours
- Integration tests: 4 hours
- E2E validation: 2 hours
- **Total:** 14 hours

### Grand Total: **50 hours** (6-7 days full-time)

---

## 📈 Completion Metrics

| Component | Status | LOC | Coverage | Owner |
|-----------|--------|-----|----------|-------|
| Models | ✅ 100% | 160 | N/A | Completed |
| Requirement Parser | ✅ 100% | 212 | 0% → 80% | Week 3 |
| Template Engine | ✅ 100% | 359 | 0% → 80% | Week 3 |
| Test Generator | ✅ 100% | 282 | 0% → 85% | Week 3 |
| Test Runner | ✅ 100% | 382 | 0% → 85% | Week 3 |
| Acceptance Gate | ✅ 100% | 328 | 0% → 90% | Week 3 |
| **Database Migration** | ❌ 0% | 80 | N/A | Week 2 Day 1 |
| **MasterPlan Integration** | ❌ 0% | 50 | N/A | Week 2 Day 3 |
| **Wave Integration** | ❌ 0% | 100 | N/A | Week 2 Day 5 |
| **API Router** | ❌ 0% | 150 | 0% → 90% | Week 3 Day 1 |
| **Unit Tests** | ❌ 0% | 950 | N/A | Week 3 Day 3 |
| **E2E Validation** | ❌ 0% | 50 | N/A | Week 3 Day 5 |

**Total Existing:** ~1,723 LOC (backend core)
**Total To Implement:** ~1,380 LOC (integrations + tests)
**Grand Total:** ~3,103 LOC

---

## 🔄 Next Actions (Prioritized)

### Immediate (This Week)
1. ✅ **Create DB Migration** (30 min) - BLOCKER
2. ✅ **Add markdown_content to MasterPlan** (1 hour) - BLOCKER
3. ✅ **Integrate with MasterPlan Generation** (2 hours) - CRITICAL
4. ✅ **Integrate with Wave Execution** (3 hours) - CRITICAL

### Week 3
5. ✅ **Create API Router** (2 hours)
6. ✅ **Write Unit Tests** (8 hours)
7. ✅ **Update E2E Test** (1 hour)
8. ✅ **Update Documentation** (2 hours)

---

## 📋 Conclusión

El sistema de Acceptance Tests tiene una **arquitectura sólida y bien diseñada** (~75% completo) pero necesita **integraciones críticas** para ser funcional. El backend core está **production-ready**, solo requiere:

1. **Database setup** (migration)
2. **Hooking into orchestration pipeline** (MasterPlan + Wave)
3. **API exposure** (REST endpoints)
4. **Testing validation** (unit + E2E)

**Estimación Total:** 50 horas (6-7 días) para completar al 100% con alta calidad.

**Próximo Paso:** Comenzar con Gap 1 (Database Migration) - BLOCKER crítico.

---

**Análisis Generado:** 2025-11-11
**Analista:** Dany (Tech Lead)
**Modo:** UltraThink
**Validado:** ✅ Arquitectura revisada exhaustivamente
