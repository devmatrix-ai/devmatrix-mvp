# Stratified Code Generation Architecture

**Date**: November 26, 2025
**Status**: DESIGN APPROVED
**Priority**: CRITICAL - Core Architecture Decision
**Author**: Ariel + Dany

---

## Executive Summary

DevMatrix adopts a **4-stratum architecture** for code generation that minimizes LLM usage where deterministic approaches suffice, while preserving LLM power for genuinely complex business logic.

**Core Principle**:
> "If it can be templated and tested once, it never touches LLM again."

---

## The 4 Strata

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STRATUM 4: QA / VALIDATION                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • py_compile validation                                     │   │
│  │  • alembic upgrade head                                      │   │
│  │  • OpenAPI contract validation                               │   │
│  │  • IR compliance (strict/relaxed)                            │   │
│  │  • Smoke tests (health, CRUD happy paths)                    │   │
│  │  • Regression detection (known bugs → block promotion)       │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                    STRATUM 3: LLM                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • Multi-entity workflows (checkout, payments)               │   │
│  │  • Complex business invariants                               │   │
│  │  • Non-trivial DTO mappings                                  │   │
│  │  • Repair patches with IR context                            │   │
│  │  • Edge case handlers                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                    STRATUM 2: AST-BASED                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • SQLAlchemy models from DomainModelIR                      │   │
│  │  • Pydantic schemas (*Base, *Create, *Update, *Read)         │   │
│  │  • Repositories with inferred methods                        │   │
│  │  • Alembic migrations (function→sa.text, literal→literal)    │   │
│  │  • Deterministic normalizations (names, routes, tags)        │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                    STRATUM 1: TEMPLATE                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • Project structure (src/, alembic/, docker/, etc.)         │   │
│  │  • docker-compose.yml, Dockerfile, grafana, prometheus       │   │
│  │  • requirements.txt, pyproject.toml, README.md               │   │
│  │  • Generic CRUD patterns (create/list/get/update/delete)     │   │
│  │  • Base models (id, timestamps, is_active)                   │   │
│  │  • Health endpoints, metrics, configs                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Stratum 1: TEMPLATE (Boilerplate)

### Objective
**Never let an LLM break infrastructure or basic CRUD.**

### What Goes Here

| Category | Files/Patterns |
|----------|----------------|
| **Project Structure** | `src/`, `alembic/`, `docker/`, `metrics/`, `tests/` |
| **Infrastructure** | `docker-compose.yml`, `Dockerfile`, `prometheus.yml`, `grafana/` |
| **Config** | `requirements.txt`, `pyproject.toml`, `.env.example`, `alembic.ini` |
| **Base Models** | `id: UUID`, `created_at`, `updated_at`, `is_active` |
| **Generic CRUD** | `create()`, `list()`, `get()`, `update()`, `delete()` |
| **Health/Metrics** | `GET /health/health`, `GET /health/ready`, `GET /metrics` |
| **Documentation** | Basic `README.md` template |

### Implementation
```python
# PatternBank categories for TEMPLATE stratum
TEMPLATE_CATEGORIES = [
    "infrastructure/docker",
    "infrastructure/observability",
    "core/config",
    "core/database",
    "models/base",
    "repository/generic",
    "routes/health",
    "project/structure"
]
```

### Rule
> If it can be templated and tested once, it lives here forever.

---

## Stratum 2: AST-BASED (Deterministic from IR)

### Objective
**Everything derivable mechanically from IR must use rules + AST, not free text.**

### What Goes Here

| Category | Generation Rule |
|----------|-----------------|
| **SQLAlchemy Models** | `DomainModelIR.entities` → Column types, nullability, FK, relationships |
| **Pydantic Schemas** | `APIModelIR.schemas` → *Base, *Create, *Update, *Read |
| **Repositories** | `DomainModelIR.entities` → entity-specific methods (`find_by_email`, etc.) |
| **Routes (CRUD)** | `APIModelIR.endpoints` → standard endpoints with correct schemas |
| **Migrations** | `DomainModelIR` → Alembic with deterministic rules |

### Critical Rules for Migrations

```python
# server_default handling - DETERMINISTIC, NO LLM
def generate_server_default(field_type: str, default_value: Any) -> str:
    """
    Rule: SQL function → sa.text(), everything else → literal
    """
    SQL_FUNCTIONS = ['now()', 'gen_random_uuid()', 'current_timestamp']

    if isinstance(default_value, str):
        default_lower = default_value.lower()

        # SQL function → sa.text()
        if any(fn in default_lower for fn in SQL_FUNCTIONS):
            return f"sa.text('{default_value}')"

        # String literal → quoted string
        return f"'{default_value}'"

    # Numeric/boolean → literal
    return str(default_value)
```

### Pydantic Schema Rules

```python
# Schema field derivation - DETERMINISTIC
def generate_schema_fields(entity: Entity, schema_type: str) -> List[Field]:
    """
    Rule: Only fields that exist in entity, with correct optionality
    """
    fields = []
    for attr in entity.attributes:
        if schema_type == "Create":
            # Required if not auto-generated and not nullable
            required = not attr.auto_generated and not attr.nullable
        elif schema_type == "Update":
            # All optional for partial updates
            required = False
        elif schema_type == "Read":
            # All fields, including auto-generated
            required = True

        fields.append(Field(
            name=attr.name,
            type=attr.python_type,
            required=required,
            # NO PHANTOM FIELDS - only what's in entity
        ))
    return fields
```

### Rule
> If the information is structured in IR, it resolves with deterministic transforms + AST, not LLM.

---

## Stratum 3: LLM (Complex Business Logic)

### Objective
**Spend "intelligence" only where it genuinely adds value.**

### What Goes Here

| Category | Examples |
|----------|----------|
| **Multi-entity Workflows** | `create_order` with stock checks, discounts, payments |
| **Complex Invariants** | "Cannot pay CANCELLED/REFUNDED order" |
| **State Machines** | Checkout flow, activation/suspension workflows |
| **Repair Patches** | IR-guided fixes for detected compliance gaps |
| **DTO Mappings** | Non-trivial external API → domain transformations |

### LLM Constraints

```python
# LLM NEVER writes:
LLM_FORBIDDEN = [
    "infrastructure/*",
    "migrations/*",
    "models/base.py",
    "core/config.py",
    "routes/health.py",
    "docker-compose.yml",
    "Dockerfile",
]

# LLM works ONLY in defined slots:
LLM_ALLOWED_SLOTS = [
    "services/*_flow_methods.py",      # Business flow implementations
    "services/*_business_rules.py",     # Complex invariant handlers
    "routes/*_custom_endpoints.py",     # Non-CRUD endpoints
    "repair_patches/*.py",              # Localized fixes
]
```

### LLM Invocation Pattern

```python
async def generate_with_llm(
    slot: str,
    ir_context: ApplicationIR,
    existing_code: Optional[str] = None
) -> str:
    """
    LLM generates ONLY within allowed slots, with full IR context.
    """
    assert slot in LLM_ALLOWED_SLOTS, f"LLM cannot write to {slot}"

    prompt = f"""
    Generate ONLY the business logic for: {slot}

    IR Context:
    - Entities: {ir_context.domain_model.entities}
    - Flows: {ir_context.behavior_model.flows}
    - Invariants: {ir_context.behavior_model.invariants}

    Constraints:
    - Do NOT modify infrastructure, models, or CRUD
    - Work within the existing structure
    - Follow existing patterns in: {existing_code[:500] if existing_code else 'N/A'}
    """

    return await llm_client.generate(prompt)
```

### Rule
> LLM is a discovery tool for patterns. Stable patterns graduate to AST/Template.

---

## Stratum 4: QA / VALIDATION (Deterministic Judge)

### Objective
**Every stratum is validated deterministically before acceptance.**

### Validation Layers

```python
class ValidationPipeline:
    """Deterministic validation for all generated code."""

    def validate_structural(self, files: Dict[str, str]) -> ValidationResult:
        """
        1. py_compile all modules
        2. AST parse for syntax errors
        3. No functions with only `pass` or `raise NotImplementedError`
        """

    def validate_database(self, app_path: Path) -> ValidationResult:
        """
        1. alembic upgrade head against test DB
        2. Verify all tables created
        3. Verify constraints applied
        """

    def validate_contract(self, app_ir: ApplicationIR, app_path: Path) -> ValidationResult:
        """
        1. OpenAPI vs IR: entities, endpoints, validations
        2. IR strict compliance (internal metric)
        3. IR relaxed compliance (external quality metric)
        """

    def validate_smoke(self, app_path: Path) -> ValidationResult:
        """
        1. docker-compose up
        2. GET /health/health → 200
        3. 1-2 happy path tests per entity
        """

    def detect_regressions(self, files: Dict[str, str]) -> List[Regression]:
        """
        Check for known bugs that should never reappear:
        - server_default=sa.text('OPEN') instead of 'OPEN'
        - service.get_all() instead of service.list()
        - ProductCreate in PUT instead of ProductUpdate
        """
```

### Regression Blockers

```python
# Known bugs that block PatternBank promotion
KNOWN_REGRESSIONS = [
    {
        "id": "REG-001",
        "pattern": r"server_default=sa\.text\(['\"](?!.*\(\))[^'\"]+['\"]\)",
        "description": "String literal wrapped in sa.text() instead of plain string",
        "severity": "critical",
        "action": "block_promotion"
    },
    {
        "id": "REG-002",
        "pattern": r"service\.get_all\(",
        "description": "Using get_all() instead of list()",
        "severity": "high",
        "action": "block_promotion"
    },
    {
        "id": "REG-003",
        "pattern": r"def \w+\([^)]*\):\s*pass\s*$",
        "description": "Function with only pass (dead code)",
        "severity": "critical",
        "action": "block_promotion"
    }
]
```

---

## Integration with Current Engine

### Atom Classification

```python
@dataclass
class Atom:
    id: str
    type: str
    content: Dict[str, Any]

    # NEW: Stratum classification
    complexity: Literal["template", "ast", "llm"]  # Predicted by classifier
    risk_level: Literal["low", "medium", "high"]

    # Existing
    dependencies: List[str]
    metadata: Dict[str, Any]
```

### Generation Router

```python
class StratifiedRouter:
    """Routes atoms to appropriate generation stratum."""

    def route(self, atom: Atom, ir: ApplicationIR) -> GeneratedCode:
        if atom.complexity == "template":
            return self.template_generator.generate(atom)

        elif atom.complexity == "ast":
            return self.ast_generator.generate(atom, ir)

        elif atom.complexity == "llm":
            code = self.llm_generator.generate(atom, ir)

            # LLM output ALWAYS goes through extra validation
            validation = self.validator.validate_llm_output(code, atom)
            if not validation.passed:
                raise LLMValidationError(validation.issues)

            return code
```

### Complexity Classifier

```python
class ComplexityClassifier:
    """Classifies atoms into complexity strata."""

    TEMPLATE_PATTERNS = [
        "infrastructure/*",
        "config/*",
        "health/*",
        "base_models",
        "generic_crud",
    ]

    AST_PATTERNS = [
        "entity_model",
        "pydantic_schema",
        "repository",
        "crud_endpoint",
        "migration",
    ]

    def classify(self, atom: Atom) -> Literal["template", "ast", "llm"]:
        if any(p in atom.type for p in self.TEMPLATE_PATTERNS):
            return "template"

        if any(p in atom.type for p in self.AST_PATTERNS):
            return "ast"

        # Complex business logic → LLM
        if atom.has_multi_entity_flow or atom.has_complex_invariants:
            return "llm"

        # Default: AST if IR-derivable, else LLM
        return "ast" if atom.is_ir_derivable else "llm"
```

---

## Pattern Promotion (Learning Phase)

### Promotion Flow

```
LLM generates code
       │
       ▼
   QA validates ────────────── FAIL → discard
       │
       ▼ PASS
   Store as candidate
       │
       ▼
   Pattern repeats in 3+ projects?
       │
       ▼ YES
   Extract deterministic rule
       │
       ▼
   Add to AST generators ────── Now AST-based, no LLM needed
       │
       ▼
   Pattern stable for 10+ uses?
       │
       ▼ YES
   Promote to TEMPLATE ─────── Now static, pre-tested, immutable
```

### Implementation

```python
class PatternPromoter:
    """Promotes successful LLM patterns to lower strata."""

    async def check_promotion_candidates(self):
        candidates = await self.pattern_store.get_stable_candidates(
            min_uses=3,
            success_rate=1.0,  # 100% success required
            no_regressions=True
        )

        for candidate in candidates:
            if candidate.is_extractable_as_rule:
                # Promote LLM → AST
                rule = self.extract_ast_rule(candidate)
                await self.ast_generator.add_rule(rule)
                await self.pattern_store.mark_promoted(candidate, "ast")

            elif candidate.uses >= 10 and candidate.is_static:
                # Promote AST → TEMPLATE
                template = self.extract_template(candidate)
                await self.pattern_bank.add_template(template)
                await self.pattern_store.mark_promoted(candidate, "template")
```

---

## Migration Plan

### Phase 1: Classify Existing Code (Week 1)

1. Audit all generators in `production_code_generators.py`
2. Tag each generation function with target stratum
3. Identify LLM calls that should be AST-based

### Phase 2: Extract Templates (Week 2)

1. Move infrastructure patterns to PatternBank
2. Create static templates for:
   - Project structure
   - Docker configs
   - Health endpoints
   - Base models

### Phase 3: Refactor AST Generators (Week 3-4)

1. Create pure IR→Code generators for:
   - SQLAlchemy models
   - Pydantic schemas
   - Repositories
   - Migrations
2. Add deterministic rules (e.g., `server_default` handling)

### Phase 4: Constrain LLM (Week 5)

1. Implement `LLM_ALLOWED_SLOTS`
2. Add slot validation to LLM calls
3. Enhance IR context in prompts

### Phase 5: Promotion Pipeline (Week 6)

1. Implement `PatternPromoter`
2. Add regression detection
3. Enable automatic promotion flow

---

## Success Metrics

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| LLM calls per generation | ~50 | <10 | Stratification |
| Infra bugs | ~5% | 0% | Template stratum |
| Migration bugs | ~10% | 0% | AST rules |
| Generation time | ~2.7min | <1min | Less LLM |
| Pattern reuse rate | ~0% | >60% | Promotion pipeline |
| Regression rate | Unknown | 0% | Blocker checks |

---

## Appendix: Bug → Stratum Mapping

| Bug ID | Description | Root Cause | Correct Stratum |
|--------|-------------|------------|-----------------|
| BUG-001 | `server_default=sa.text('OPEN')` | LLM generating migration | AST |
| BUG-002 | `service.get_all()` vs `service.list()` | LLM pattern mismatch | TEMPLATE |
| BUG-003 | `ProductCreate` in PUT endpoint | LLM schema confusion | AST |
| BUG-004 | Functions with only `pass` | LLM incomplete generation | AST + QA |
| BUG-005 | Missing `requirements.txt` | LLM forgot file | TEMPLATE |

---

## Conclusion

This architecture transforms DevMatrix from a "prompt engineering tool" to a **formal semantic code generator**:

- **TEMPLATE**: Pre-tested, immutable, zero risk
- **AST**: Deterministic, IR-driven, reproducible
- **LLM**: Constrained, validated, promotes to AST
- **QA**: Deterministic judge, regression blocker

The LLM becomes a **pattern discovery tool**, not the production engine.

---

*"Use LLM to discover patterns, but ship templates and AST."*
