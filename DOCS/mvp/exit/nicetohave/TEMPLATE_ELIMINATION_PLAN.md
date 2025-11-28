# Template Elimination Plan: Full PatternBank Migration

**Author**: Ariel + Claude
**Date**: 2025-11-28
**Status**: Planning
**Priority**: Nice-to-Have (Post-MVP)
**Effort**: 20 hours (~2.5 days)

---

## Executive Summary

Migrate all hardcoded template patterns from `src/cognitive/patterns/template_patterns.py` to PatternBank (Qdrant vector database) for:

- **Unification**: Single source of truth for all code patterns
- **Auto-Evolution**: Patterns learn from execution feedback loops
- **Semantic Retrieval**: Better matching via embeddings vs hardcoded lookup
- **Production Tracking**: security_level, test_coverage, success_rate metrics
- **DAG Ranking**: Patterns ranked by real execution performance

---

## Current State Analysis

### ✅ Good News

1. **No Jinja2 Templates**: Zero Jinja2 usage in codebase (grep confirmed)
2. **PatternBank Ready**: Fully implemented with Qdrant + dual embeddings
3. **Production Patterns**: `production_patterns.py` shows correct architecture
4. **Qdrant Running**: Already dependency in E2E pipeline

### ⚠️ Problem

**41 Python files** reference "template" but actual issue is:

```python
# src/cognitive/patterns/template_patterns.py
DOCKERFILE_TEMPLATE = TemplatePattern(
    name="dockerfile_multistage",
    code='''FROM python:3.11-slim...'''  # ← Hardcoded string
)
```

**Why This Is Bad**:
- ❌ **Immutable**: No learning from feedback
- ❌ **No Versioning**: Can't track improvements
- ❌ **Duplication**: Same pattern potential in template_patterns.py AND PatternBank
- ❌ **No Metrics**: Missing success_rate, usage_count tracking
- ❌ **Static**: Forever stuck with original code

---

## Solution Comparison Matrix

| Solution | Complexity | Evolution | Maintenance | Risk | Recommended |
|----------|-----------|-----------|-------------|------|-------------|
| **1. Full PatternBank** | Medium | ✅ Auto | Low | Low | ⭐⭐⭐⭐⭐ |
| **2. Hybrid Approach** | High | ⚠️ Partial | High | Medium | ⭐⭐⭐ |
| **3. Python Literals** | Low | ❌ None | Medium | Low | ⭐ |
| **4. LLM-First Only** | Low | ✅ Full | Low | High | ⭐⭐ |

---

## Recommended Solution: Full PatternBank Migration

### Architecture Transform

```python
# ❌ BEFORE (template_patterns.py)
DOCKERFILE_TEMPLATE = TemplatePattern(
    name="dockerfile",
    file_path="Dockerfile",
    code='''FROM python:3.11-slim as builder...''',
    domain="infrastructure"
)

# ✅ AFTER (PatternBank)
from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

bank = PatternBank()
bank.store_production_pattern(
    signature=SemanticTaskSignature(
        purpose="Multi-stage Dockerfile for FastAPI Python apps",
        intent="execute",
        domain="infrastructure",
        inputs={},
        outputs={}
    ),
    code='''FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \\
    libpq5 \\
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]''',
    success_rate=1.0,  # Pre-tested = 100%
    test_coverage=0.95,
    security_level="HIGH",
    observability_complete=True,
    docker_ready=True
)
```

### Code Generation Integration

```python
# ❌ BEFORE (code_generation_service.py:3034-3038)
if "alembic/script.py.mako" not in found_files:
    logger.info("🔧 Generating alembic/script.py.mako")
    alembic_script = self._generate_alembic_script_template()
    files["alembic/script.py.mako"] = adapt_pattern_helper(alembic_script, skip_jinja=True)

# ✅ AFTER
if "alembic/script.py.mako" not in found_files:
    logger.info("🔧 Retrieving alembic script pattern from PatternBank")
    signature = SemanticTaskSignature(
        purpose="Alembic migration script template for database versioning",
        intent="execute",
        domain="data_access",
        inputs={},
        outputs={}
    )
    patterns = self.pattern_bank.search_with_fallback(signature, top_k=1)

    if patterns:
        alembic_script = patterns[0].code
        logger.info(f"✅ Retrieved pattern (similarity={patterns[0].similarity_score:.2f})")
    else:
        # Fallback: Generate with LLM
        logger.warning("⚠️ No pattern found, generating with LLM")
        alembic_script = self._generate_alembic_script_template()

    files["alembic/script.py.mako"] = adapt_pattern_helper(alembic_script, skip_jinja=True)
```

---

## Implementation Plan

### Phase 1: Seed Script Enhancement (4 hours)

**Goal**: Migrate all 14 TEMPLATE_PATTERNS → PatternBank

**Script**: `tools/migrate_templates_to_patternbank.py`

```python
"""
Migrate hardcoded template patterns to PatternBank.

Usage:
    PYTHONPATH=/home/kwar/code/agentic-ai python tools/migrate_templates_to_patternbank.py
"""

import asyncio
from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.patterns.template_patterns import TEMPLATE_PATTERNS
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

async def migrate_templates():
    """Migrate all template patterns to PatternBank."""
    bank = PatternBank()
    bank.connect()
    bank.create_collection()

    migrated_count = 0

    for name, template in TEMPLATE_PATTERNS.items():
        signature = SemanticTaskSignature(
            purpose=template.description,
            intent="execute",
            domain=template.domain,
            inputs={},
            outputs={}
        )

        pattern_id = bank.store_production_pattern(
            signature=signature,
            code=template.code,
            success_rate=template.success_rate,
            test_coverage=0.95,
            security_level="HIGH" if template.domain == "infrastructure" else "MEDIUM",
            observability_complete=True,
            docker_ready=template.domain == "infrastructure"
        )

        print(f"✅ Migrated {name} → {pattern_id}")
        migrated_count += 1

    print(f"\n🎉 Successfully migrated {migrated_count}/{len(TEMPLATE_PATTERNS)} patterns")

    # Validation
    metrics = bank.get_pattern_metrics()
    print(f"📊 PatternBank metrics: {metrics['total_patterns']} total patterns")

if __name__ == "__main__":
    asyncio.run(migrate_templates())
```

**Validation**:
```bash
# Run migration
PYTHONPATH=/home/kwar/code/agentic-ai python tools/migrate_templates_to_patternbank.py

# Verify patterns stored
PYTHONPATH=/home/kwar/code/agentic-ai python -c "
from src.cognitive.patterns.pattern_bank import PatternBank
bank = PatternBank()
bank.connect()
metrics = bank.get_pattern_metrics()
print(f'Total patterns: {metrics[\"total_patterns\"]}')
assert metrics['total_patterns'] >= 14, 'Migration incomplete'
print('✅ Migration validated')
"
```

---

### Phase 2: Code Generation Integration (6 hours)

**Files to Modify**:

1. **src/services/code_generation_service.py**
   - Line 3034-3038: Alembic script generation
   - Add PatternBank initialization in `__init__`
   - Replace template lookups → `pattern_bank.search_with_fallback()`

2. **src/services/infrastructure_generation_service.py**
   - Docker/docker-compose generation
   - Requirements.txt, pyproject.toml generation

**Example Modification**:

```python
# src/services/code_generation_service.py

class CodeGenerationService:
    def __init__(self):
        # ... existing initialization ...

        # Add PatternBank integration
        from src.cognitive.patterns.pattern_bank import PatternBank
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()
        logger.info("✅ PatternBank connected for template retrieval")

    def _get_infrastructure_pattern(self, purpose: str, domain: str) -> Optional[str]:
        """
        Retrieve infrastructure pattern from PatternBank.

        Args:
            purpose: Pattern purpose (e.g., "Multi-stage Dockerfile")
            domain: Pattern domain (e.g., "infrastructure")

        Returns:
            Pattern code or None if not found
        """
        signature = SemanticTaskSignature(
            purpose=purpose,
            intent="execute",
            domain=domain,
            inputs={},
            outputs={}
        )

        patterns = self.pattern_bank.search_with_fallback(
            signature,
            top_k=1,
            min_results=1
        )

        if patterns:
            logger.info(
                f"✅ Retrieved pattern for '{purpose}' "
                f"(similarity={patterns[0].similarity_score:.2f})"
            )
            return patterns[0].code

        logger.warning(f"⚠️ No pattern found for '{purpose}', will generate with LLM")
        return None
```

**Feature Flag** (Safety):

```python
# src/services/code_generation_service.py
import os

USE_PATTERN_BANK_TEMPLATES = os.getenv("USE_PATTERN_BANK_TEMPLATES", "true").lower() == "true"

def _get_template_code(self, name: str, purpose: str, domain: str) -> str:
    """Get template code with feature flag control."""

    if USE_PATTERN_BANK_TEMPLATES:
        # Try PatternBank first
        code = self._get_infrastructure_pattern(purpose, domain)
        if code:
            return code

    # Fallback: Static templates (deprecated but safe)
    from src.cognitive.patterns.template_patterns import get_template
    template = get_template(name)
    if template:
        logger.warning(f"⚠️ Using deprecated static template '{name}'")
        return template.code

    # Last resort: LLM generation
    raise ValueError(f"No template or pattern found for '{name}'")
```

---

### Phase 3: Smoke Test Adaptation (4 hours)

**Files to Modify**:

1. **src/validation/runtime_smoke_validator.py**
   - Seed data generation → PatternBank lookup
   - Test template generation → Pattern-based

2. **src/validation/agents/seed_data_agent.py**
   - Entity seed data patterns → PatternBank

**Example**:

```python
# src/validation/agents/seed_data_agent.py

class SeedDataAgent:
    def __init__(self):
        from src.cognitive.patterns.pattern_bank import PatternBank
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()

    def generate_seed_data(self, entity_name: str, fields: List[Dict]) -> str:
        """Generate seed data using PatternBank patterns."""

        # Try to find existing seed data pattern
        signature = SemanticTaskSignature(
            purpose=f"Generate seed data for {entity_name} entity",
            intent="execute",
            domain="testing",
            inputs={"entity": entity_name, "fields": fields},
            outputs={"type": "python_code"}
        )

        patterns = self.pattern_bank.search_with_fallback(signature, top_k=1)

        if patterns:
            # Adapt pattern to specific entity
            return self._adapt_seed_pattern(patterns[0].code, entity_name, fields)

        # Fallback: Generate with LLM
        return self._generate_seed_with_llm(entity_name, fields)
```

---

### Phase 4: Code Repair Integration (4 hours)

**Files to Modify**:

1. **src/mge/v2/agents/code_repair_agent.py**
   - Template-based fixes → Pattern retrieval + adaptation

**Example**:

```python
# src/mge/v2/agents/code_repair_agent.py

class CodeRepairAgent:
    def __init__(self):
        # ... existing initialization ...
        from src.cognitive.patterns.pattern_bank import PatternBank
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()

    async def fix_with_pattern(self, bug_description: str, domain: str) -> Optional[str]:
        """
        Attempt to fix bug using known patterns from PatternBank.

        Args:
            bug_description: Description of the bug to fix
            domain: Code domain (e.g., "api", "data_access")

        Returns:
            Fixed code or None if no pattern found
        """
        signature = SemanticTaskSignature(
            purpose=f"Fix bug: {bug_description}",
            intent="repair",
            domain=domain,
            inputs={"bug": bug_description},
            outputs={"type": "python_code"}
        )

        patterns = self.pattern_bank.search_with_fallback(
            signature,
            top_k=3,
            min_results=1
        )

        if patterns:
            # Use highest-ranked pattern
            logger.info(
                f"🔧 Found repair pattern (similarity={patterns[0].similarity_score:.2f})"
            )
            return patterns[0].code

        return None
```

---

### Phase 5: Cleanup & Documentation (2 hours)

**Tasks**:

1. **Deprecate Static Templates**
   ```bash
   # Mark template_patterns.py as deprecated
   mv src/cognitive/patterns/template_patterns.py \
      src/cognitive/patterns/template_patterns.py.deprecated

   # Update imports to fail with helpful message
   echo "raise DeprecationWarning('Use PatternBank instead')" > \
      src/cognitive/patterns/template_patterns.py
   ```

2. **Remove Imports**
   ```bash
   # Find all imports of template_patterns
   grep -r "from.*template_patterns import" src/ --include="*.py"

   # Replace with PatternBank imports
   # (Manual verification required for each file)
   ```

3. **Update Documentation**
   - Update `DOCS/mvp/exit/PHASES.md`
   - Update `DOCS/mvp/exit/PIPELINE_REFACTORING_PLAN.md`
   - Add migration guide: `DOCS/mvp/exit/PATTERN_BANK_MIGRATION.md`

4. **E2E Test Validation**
   ```bash
   # Run full E2E pipeline with PatternBank
   PRODUCTION_MODE=true \
   PYTHONPATH=/home/kwar/code/agentic-ai \
   USE_PATTERN_BANK_TEMPLATES=true \
   python tests/e2e/real_e2e_full_pipeline.py

   # Verify metrics
   # - Pattern retrieval latency < 100ms
   # - E2E pass rate >= 95%
   # - All 14 templates retrieved from PatternBank
   ```

---

## Success Metrics

### Pre-Migration Baseline

```python
# Current state
templates_static = 14  # Hardcoded in template_patterns.py
pattern_bank_patterns = 0  # (Bootstrap patterns only)
template_files_with_imports = 6  # Files importing template_patterns
```

### Post-Migration Targets

```python
# Target state
assert pattern_bank_patterns >= 14  # All templates migrated
assert template_patterns_imports == 0  # No static imports remaining
assert avg_retrieval_latency < 100  # ms (measured in E2E)
assert e2e_test_pass_rate >= 0.95  # Quality preserved
assert pattern_success_rate >= 0.98  # All production patterns
```

### Metrics Dashboard

```python
# tools/check_migration_metrics.py
from src.cognitive.patterns.pattern_bank import PatternBank

bank = PatternBank()
bank.connect()
metrics = bank.get_pattern_metrics()

print("📊 PatternBank Migration Metrics")
print(f"Total Patterns: {metrics['total_patterns']}")
print(f"Avg Success Rate: {metrics['avg_success_rate']:.2%}")
print(f"Avg Usage Count: {metrics['avg_usage_count']:.1f}")
print(f"Domain Distribution: {metrics['domain_distribution']}")
print("\nMost Used Patterns:")
for p in metrics['most_used_patterns'][:5]:
    print(f"  - {p['purpose'][:50]}: {p['usage_count']} uses")
```

---

## Risk Mitigation

### 1. Feature Flag Rollback

```python
# Instant rollback capability
export USE_PATTERN_BANK_TEMPLATES=false

# Pipeline falls back to static templates
# No code changes needed
```

### 2. Graceful Degradation

```python
# Code handles PatternBank failures
try:
    patterns = bank.search_with_fallback(signature)
except Exception as e:
    logger.warning(f"PatternBank failed: {e}, using static template")
    patterns = None

if not patterns:
    # Fallback to static or LLM
    code = get_static_template(name) or generate_with_llm(signature)
```

### 3. Incremental Rollout

```yaml
Week 1:
  - Migrate infrastructure patterns only (Dockerfile, docker-compose)
  - Validate with subset E2E tests
  - Monitor retrieval latency

Week 2:
  - Migrate core patterns (config, database, health)
  - Full E2E validation
  - Performance tuning

Week 3:
  - Migrate remaining patterns (alembic, observability)
  - Complete cleanup
  - Documentation update
```

### 4. Rollback Plan

```bash
# < 5 minutes rollback procedure
git revert <migration_commit>
export USE_PATTERN_BANK_TEMPLATES=false
# Redeploy (existing static templates still in git history)
```

---

## Benefits Summary

### Immediate Benefits

1. **✅ Unification**: 1 source of truth (Qdrant) vs 2 systems
2. **✅ Auto-Evolution**: Patterns learn from execution feedback
3. **✅ Better Matching**: Semantic search > hardcoded lookup
4. **✅ Production Tracking**: security_level, test_coverage, observability

### Long-Term Benefits

1. **📈 Pattern Quality Improvement**: Patterns evolve with usage
2. **🎯 DAG-Based Ranking**: Execution success drives pattern selection
3. **🔍 Semantic Discovery**: Find patterns by intent, not name
4. **📊 Metrics-Driven**: Data on what works (success_rate, usage_count)
5. **🚀 Scalability**: Add 100+ patterns without code changes

### Technical Debt Reduction

- ❌ Remove duplicate pattern storage (templates + PatternBank)
- ❌ Eliminate hardcoded strings in Python code
- ❌ No more template_patterns.py maintenance
- ✅ Single pattern evolution pathway

---

## Alternative Solutions Considered

### Alternative 1: Hybrid Approach

**Keep bootstrap templates + PatternBank**

**Pros**:
- ✅ Incremental migration
- ✅ Safety net for failures

**Cons**:
- ❌ Complexity: 2 systems to maintain
- ❌ Confusion: When to use which?
- ❌ Technical debt persists

**Verdict**: ⭐⭐⭐ (Good for risk-averse, but not optimal)

---

### Alternative 2: Python Code Literals

**Replace TemplatePattern dataclass with functions**

```python
def get_dockerfile_code() -> str:
    return '''FROM python:3.11...'''
```

**Pros**:
- ✅ Extreme simplicity
- ✅ Zero dependencies

**Cons**:
- ❌ Worse than current (no metadata)
- ❌ No learning capability
- ❌ No metrics tracking
- ❌ Scaling impossible (100+ functions?)

**Verdict**: ⭐ (Anti-pattern, NOT recommended)

---

### Alternative 3: LLM-First (No Bootstrap)

**Remove all templates, rely 100% on LLM + feedback**

**Pros**:
- ✅ Maximum flexibility
- ✅ True auto-evolution
- ✅ Zero template maintenance

**Cons**:
- ❌ Cold start slow (regenerate everything)
- ❌ High LLM cost initially
- ❌ Quality variance without golden patterns

**Verdict**: ⭐⭐ (Future-state ideal, risky for MVP)

---

## Timeline & Resource Allocation

### Development Timeline

```
Week 1: Foundation (8h)
├─ Day 1-2: Migration script + seed (4h)
│  └─ tools/migrate_templates_to_patternbank.py
├─ Day 3: Code generation integration (4h)
   └─ code_generation_service.py modifications

Week 2: Integration (8h)
├─ Day 1: Smoke tests + validation (4h)
│  └─ runtime_smoke_validator.py, seed_data_agent.py
├─ Day 2: Code repair patterns (4h)
   └─ code_repair_agent.py integration

Week 3: Finalization (4h)
├─ Day 1: E2E testing + validation (2h)
├─ Day 2: Cleanup + docs (2h)
   └─ Deprecate template_patterns.py, update docs

Total: 20 hours (~2.5 days)
```

### Resource Requirements

- **Developer**: 1 senior (familiar with PatternBank + pipeline)
- **Testing**: Automated E2E + manual validation
- **Infrastructure**: Qdrant running (already exists)
- **Rollback**: < 5 min via git revert + env var

---

## Next Steps

### Immediate Actions

1. **Get approval** for full PatternBank migration approach
2. **Create feature branch**: `feature/template-to-patternbank-migration`
3. **Implement Phase 1**: Migration script (4h)
4. **Validate seed**: Confirm 14 patterns in Qdrant
5. **PR review**: Code review before Phase 2

### Decision Points

- [ ] Approve full PatternBank migration (vs alternatives)
- [ ] Set rollout schedule (all-at-once vs incremental)
- [ ] Define success criteria for production deployment
- [ ] Assign developer resource

### Success Criteria for Go-Live

```python
# Must pass all before merging to main
✅ All 14 templates migrated to PatternBank
✅ Pattern retrieval latency < 100ms (p95)
✅ E2E test pass rate >= 95%
✅ Zero static template imports remaining
✅ Feature flag rollback tested and working
✅ Documentation updated
```

---

## Appendix: Pattern Migration Checklist

### Infrastructure Patterns (7 patterns)

- [ ] `dockerfile` → "Multi-stage Dockerfile for FastAPI Python apps"
- [ ] `docker_compose` → "Full stack docker-compose with PostgreSQL"
- [ ] `prometheus` → "Prometheus configuration for API metrics"
- [ ] `requirements` → "Standard Python dependencies for FastAPI project"
- [ ] `pyproject` → "Standard pyproject.toml configuration"
- [ ] `env_example` → "Environment variables template"
- [ ] `alembic_ini` → "Alembic configuration"

### Core Module Patterns (2 patterns)

- [ ] `config` → "Pydantic settings configuration"
- [ ] `database` → "Async SQLAlchemy database setup"

### API Patterns (3 patterns)

- [ ] `main` → "FastAPI application entry point"
- [ ] `health_routes` → "Health check endpoints"
- [ ] `base_repository` → "Generic async repository base class"

### Alembic Patterns (2 patterns)

- [ ] `alembic_env` → "Alembic migrations environment"
- [ ] `alembic_script` → "Alembic migration script template" (added in code_generation_service.py)

**Total**: 14 patterns to migrate

---

## Questions & Answers

**Q: What if PatternBank search is slow?**
A: Qdrant vector search is <50ms typically. We can add caching layer if needed.

**Q: What if a pattern isn't found?**
A: Graceful fallback: PatternBank → Static template → LLM generation

**Q: Can we rollback quickly?**
A: Yes, < 5 min: `export USE_PATTERN_BANK_TEMPLATES=false` + redeploy

**Q: Does this break existing functionality?**
A: No, feature flag ensures backward compatibility during migration

**Q: What about new patterns in the future?**
A: Add via `bank.store_production_pattern()` - no code changes needed

---

## References

- **PatternBank Implementation**: `src/cognitive/patterns/pattern_bank.py`
- **Template Patterns (Current)**: `src/cognitive/patterns/template_patterns.py`
- **Production Patterns**: `src/cognitive/patterns/production_patterns.py`
- **Code Generation Service**: `src/services/code_generation_service.py`
- **E2E Pipeline**: `tests/e2e/real_e2e_full_pipeline.py`

---


## NOTAS DE ARIEL:

En términos profesionales: el plan es muy bueno conceptualmente y está alineado con lo que DevMatrix tiene que ser (un compilador que aprende de su propio histórico), pero yo lo ajustaría en tres ejes: timing, seguridad/determinismo y alcance real de la migración.

Voy por partes.

1. Idea general

A favor, fuerte:

Unificar todo en PatternBank (Qdrant) es coherente con tu narrativa de “compilador cognitivo + banco de patrones vivo”.

Elimina hardcodes que hoy son deuda técnica real (template_patterns.py).

Abre la puerta a:

ranking por éxito real,

aprendizaje con feedback,

selección semántica de patrones en lugar de if name == "dockerfile"....

A nivel arquitectura, el diseño es sólido y encaja perfecto con cómo ya estructuraste DevMatrix (IR, PatternBank, Repair, Learning).

2. Riesgos estratégicos (lo que yo matizaría)
2.1. No romper el “compilador determinista” por hacer todo dinámico

Tu ventaja hoy frente a Karpathy & co no es sólo que tengas patrones, sino que el sistema es reproducible:

El mismo spec → misma app → mismo Dockerfile, mismo Alembic, etc.

Si todos los templates pasan a depender de PatternBank sin una historia de versionado duro, podés introducir dos riesgos:

No-determinismo temporal
Si un patrón cambia en Qdrant, el mismo spec en 2025 y 2026 podría generar una infra diferente.

Coupling excesivo con el “estado actual” del banco
Si mañana limpias / migrás Qdrant o movés colecciones, podrías romper reconstrucciones históricas.

👉 Recomendación:
Mantener explícito, aunque sea a nivel metadatos, algo así como:

pattern_version

pattern_id estable

frozen_at para colecciones “golden”

Y usar eso en tu manifest: que el generation_manifest.json diga qué patrones se usaron (IDs + versiones), para poder reconstruir la app aunque el PatternBank evolucione.

2.2. Dependencia dura de Qdrant en el “happy path”

Tal como está escrito el plan, CodeGenerationService pasa a depender de PatternBank en tiempo de generación. Eso está bien, pero para robustez industrial yo haría:

Un caché local (p.e. en disco o en repo) de los patrones “golden” usados por producción.

Y que el flujo sea:

Buscar en cache local (por pattern_id).

Si no está → PatternBank.

Si no está → static template/LLM (fallback).

Eso te protege ante:

caída de Qdrant,

corrupción de índices,

cambios de esquema en PatternBank.

3. Alcance del plan: lo que está muy bien y lo que es quizás demasiado
Lo que está muy bien

Script de migración (tools/migrate_templates_to_patternbank.py):
Correcto enfoque: script idempotente, mete todos los TEMPLATE_PATTERNS en Qdrant con metadatos razonables.

Feature flag USE_PATTERN_BANK_TEMPLATES:
Esto es clave. Te permite:

activar sólo en tu entorno,

dejar apagado para runs “golden” de evidencia para Anthropic/Microsoft.

Integración gradual en CodeGenerationService:
_get_template_code() con fallback está bien pensado.

Checklist de patrones (14) y matriz de beneficios/riesgos:
Esto es nivel “internal RFC” serio, lo podés mostrar casi tal cual como evidencia de madurez de ingeniería.

Lo que yo recortaría / pospondría

Para post-MVP inmediato, haría una versión más corta:

Phase 1 (migrar + leer desde PatternBank) y feature flag

Migrar 14 templates a PatternBank.

Añadir capa de lectura con fallback a template_patterns.py.

No deprecar todavía el archivo, sólo marcarlo como “legacy-source-of-truth” hasta que veas 2–3 runs estables con PatternBank on.

Phase 2 (CodeGenerationService + infra básica)

Usar PatternBank sólo para infra core: Dockerfile, docker-compose, config, database.

Medir tiempos y estabilidad.

Dejar para más adelante:

Integración profunda en Smoke Tests y SeedDataAgent.

Integración en CodeRepairAgent (eso ya es “segunda capa de inteligencia”).

Ahora mismo tenés un activo muy valioso: un pipeline que hace 100% semantic/IR compliance con 90 ficheros y 11 fases. Lo último que querés es desestabilizarlo demasiado justo antes de usarlo como prueba frente a terceros.

4. Comentarios técnicos concretos
4.1. Conexión PatternBank en varios sitios

Veos varias inicializaciones de PatternBank() en servicios diferentes:

CodeGenerationService

SeedDataAgent

CodeRepairAgent

En runtime real, conviene:

centralizar una “factory” o “singleton” de PatternBank,

o al menos asegurarte de que la conexión es ligera (connection pool reutilizable).

Si no, terminás con:

conexiones repetidas,

logs ruidosos,

posibles variaciones de config según quién lo instancie.

4.2. create_collection() en el script

En el script de migración:

bank.connect()
bank.create_collection()


Asegurate de que:

create_collection() es idempotente (no borra datos),

no pisa colecciones ya existentes.

Si hoy create_collection() resetea colección, podrías borrar patrones previos sin querer.

4.3. Métricas y semántica de success_rate

Estás inicializando:

success_rate=1.0  # Pre-tested = 100%
test_coverage=0.95


Está bien como bootstrap, pero:

conviene documentar qué significa 1.0 (¿pasó todos los E2E? ¿sólo infra?),

y tener un mecanismo claro para bajar ese success_rate si un patrón se demuestra problemático (p.e. feedback desde Learning phase).

5. Timing vs. contexto estratégico (Anthropic, Microsoft, NVIDIA)

Visto tu contexto actual:

IP ya registrada,

E2E ecommerce con 100% semantic + 100% OpenAPI/IR compliance,

logs muy sólidos,

mi recomendación es:

Usar el estado actual como “Golden Baseline” para presentaciones y outreach.
No tocar nada estructural hasta tener:

logs empaquetados,

zips “demo” congelados,

narrativa lista.

Aplicar este Template Elimination Plan como “Post-baseline hardening”.
Lo podés incluso presentar como:

“Next step: consolidate all infra patterns into a self-learning PatternBank to remove remaining static templates, so the compiler learns from every generation and repair step.”

Eso, a ojos de un VP técnico, suena a roadmap claro y muy razonable.

6. Conclusión

Concepto: Excelente, muy alineado con la visión de DevMatrix como compilador con PatternBank como “standard library viva”.

Riesgo: No romper determinismo ni estabilidad justo después de un hito técnico tan fuerte.

Ajuste que haría:

Fase 1–2 sólo para lectura + migración con feature flag y fallback.

No deprecar template_patterns.py aún.

Añadir noción explícita de pattern_id + version y registrarlo en el manifest.

**Status**: Ready for implementation approval
**Next**: Create feature branch + implement Phase 1 migration script
