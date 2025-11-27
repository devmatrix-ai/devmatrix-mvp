# ApplicationIR System

**Version**: 2.0
**Date**: November 2025
**Status**: Production

---

## Overview

ApplicationIR is the **single source of truth** for all code generation in DevMatrix. It provides a canonical, machine-readable representation of the application specification.

---

## ApplicationIR Structure

**File**: `src/cognitive/ir/application_ir.py`

```python
class ApplicationIR(BaseModel):
    app_id: UUID
    name: str

    domain_model: DomainModelIR        # Entities, relationships
    api_model: APIModelIR              # Endpoints, schemas
    infrastructure_model: InfrastructureModelIR  # DB, config
    behavior_model: BehaviorModelIR    # Flows, invariants
    validation_model: ValidationModelIR  # Rules, constraints

    phase_status: Dict[str, str]
    version: str = "1.0.0"
```

---

## IR Components

### DomainModelIR

Entities and their relationships:

```python
class DomainModelIR(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]

class Entity(BaseModel):
    name: str
    attributes: List[Attribute]
    constraints: List[str]
    description: Optional[str]

class Attribute(BaseModel):
    name: str
    type: str
    nullable: bool = False
    auto_generated: bool = False
    default: Optional[Any] = None
    constraints: List[str] = []
```

### APIModelIR

Endpoints and schemas:

```python
class APIModelIR(BaseModel):
    endpoints: List[Endpoint]
    schemas: List[Schema]

class Endpoint(BaseModel):
    method: str  # GET, POST, PUT, DELETE
    path: str
    description: str
    request_body: Optional[Schema]
    response: Schema
    tags: List[str]
```

### BehaviorModelIR

Business flows and invariants:

```python
class BehaviorModelIR(BaseModel):
    flows: List[Flow]
    invariants: List[Invariant]

class Flow(BaseModel):
    name: str
    type: FlowType  # WORKFLOW, EVENT, ASYNC
    trigger: str
    steps: List[Step]
    description: str

class Invariant(BaseModel):
    entity: str
    description: str
    enforcement_level: str  # "strict", "soft"
```

### ValidationModelIR

Validation rules and constraints:

```python
class ValidationModelIR(BaseModel):
    rules: List[ValidationRule]

class ValidationRule(BaseModel):
    entity: str
    attribute: str
    validation_type: ValidationType  # FORMAT, RANGE, PRESENCE, etc.
    parameters: Dict[str, Any]
    enforcement: EnforcementStrategy
    description: str

class ValidationType(Enum):
    FORMAT = "format"
    RANGE = "range"
    PRESENCE = "presence"
    UNIQUENESS = "uniqueness"
    RELATIONSHIP = "relationship"
    STATUS_TRANSITION = "status_transition"
```

---

## SpecToApplicationIR

**File**: `src/specs/spec_to_application_ir.py`

Converts natural language specs to ApplicationIR:

```python
class SpecToApplicationIR:
    """One-time LLM extraction with caching."""

    async def get_application_ir(
        self,
        spec_content: str,
        spec_name: str,
        force_refresh: bool = False
    ) -> ApplicationIR:
        # Check cache first
        cache_key = self._compute_hash(spec_content)
        if not force_refresh:
            cached = self._load_from_cache(cache_key)
            if cached:
                return cached

        # LLM extraction (one-time)
        ir = await self._extract_with_llm(spec_content)

        # Cache for future use
        self._save_to_cache(cache_key, ir)
        return ir
```

### Streaming Support

For large specs (>50KB), streaming is used:

```python
async with client.messages.stream(
    model="claude-sonnet-4-5-20250929",
    max_tokens=8192,
    messages=[{"role": "user", "content": extraction_prompt}]
) as stream:
    async for text in stream.text_stream:
        full_response += text
```

---

## IR Usage by Pipeline Phase

| Phase | IR Usage | Details |
|-------|----------|---------|
| **1** | **EXTRACTS** | `SpecToApplicationIR` generates ApplicationIR |
| **1.5** | Yes | ValidationModelIR enrichment |
| **2** | Yes | `get_dag_ground_truth()` from ApplicationIR |
| **3** | **MIGRATED** | DAG nodes from IR (entities, endpoints, flows) |
| **4** | No | Internal atomization |
| **5** | Yes | Inherits IR nodes from Phase 3 |
| **6** | **REQUIRES** | `generate_from_application_ir()` |
| **6.5** | **REQUIRES** | TestGeneratorFromIR |
| **6.6** | **REQUIRES** | ServiceGeneratorFromIR |
| **7** | **MIGRATED** | CodeRepairAgent uses ApplicationIR |
| **8** | No | Test execution |
| **9** | **REQUIRES** | ComplianceValidator against IR |
| **10-11** | No | Health check, learning |

---

## Convenience Methods

ApplicationIR provides convenience methods for pipeline phases:

```python
class ApplicationIR(BaseModel):
    # ...

    def get_entities(self) -> List[Entity]:
        """Get all entities from DomainModelIR."""
        return self.domain_model.entities

    def get_endpoints(self) -> List[Endpoint]:
        """Get all endpoints from APIModelIR."""
        return self.api_model.endpoints

    def get_flows(self) -> List[Flow]:
        """Get all flows from BehaviorModelIR."""
        return self.behavior_model.flows

    def get_dag_ground_truth(self) -> Dict[str, Any]:
        """Generate DAG ground truth for planning phases."""
        return {
            "entities": [e.name for e in self.get_entities()],
            "endpoints": [f"{ep.method} {ep.path}" for ep in self.get_endpoints()],
            "flows": [f.name for f in self.get_flows()],
            "relationships": self._extract_relationships()
        }

    def get_dag_nodes(self) -> List[Dict[str, Any]]:
        """Get DAG nodes from all IR models."""
        nodes = []

        # Entities from DomainModelIR
        for entity in self.get_entities():
            nodes.append({
                "id": f"entity_{entity.name}",
                "name": entity.name,
                "type": "entity",
                "source": "DomainModelIR"
            })

        # Endpoints from APIModelIR
        for endpoint in self.get_endpoints():
            endpoint_id = f"{endpoint.method}_{endpoint.path}".replace("/", "_")
            nodes.append({
                "id": endpoint_id,
                "name": f"{endpoint.method} {endpoint.path}",
                "type": "endpoint",
                "source": "APIModelIR"
            })

        # Flows from BehaviorModelIR
        for flow in self.get_flows():
            nodes.append({
                "id": f"flow_{flow.name}".replace(" ", "_"),
                "name": flow.name,
                "type": "flow",
                "source": "BehaviorModelIR"
            })

        return nodes
```

---

## IR-Based Services

### TestGeneratorFromIR

**File**: `src/services/ir_test_generator.py`

```python
from src.services.ir_test_generator import (
    generate_all_tests_from_ir,
    TestGeneratorFromIR,
    IntegrationTestGeneratorFromIR,
    APIContractValidatorFromIR
)

# Generate all tests
generated_files = generate_all_tests_from_ir(application_ir, output_dir)
```

| Validation Type | Test Generated |
|-----------------|----------------|
| PRESENCE | `test_{entity}_{attr}_required()` |
| FORMAT | `test_{entity}_{attr}_format()` |
| RANGE | `test_{entity}_{attr}_range()` |
| UNIQUENESS | `test_{entity}_{attr}_unique()` |
| RELATIONSHIP | `test_{entity}_{attr}_relationship()` |
| STATUS_TRANSITION | `test_{entity}_{attr}_transitions()` |

### ServiceGeneratorFromIR

**File**: `src/services/ir_service_generator.py`

```python
from src.services.ir_service_generator import ServiceGeneratorFromIR

generator = ServiceGeneratorFromIR(behavior_model)
service_code = generator.generate_service()
flow_coverage = generator.get_flow_coverage_report()
```

### IRComplianceChecker

**File**: `src/services/ir_compliance_checker.py`

```python
from src.services.ir_compliance_checker import (
    check_full_ir_compliance,
    EntityComplianceChecker,
    FlowComplianceChecker,
    ConstraintComplianceChecker
)

# Full compliance check
reports = check_full_ir_compliance(application_ir, generated_app_path)
# Returns: {"entity": Report, "flow": Report, "constraint": Report}
```

---

## Caching Architecture

IR uses a **multi-tier caching strategy** to maximize performance and resilience:

```
Request ──► TIER 1: Redis (Primary)
               │ TTL: 7 days (auto-expire)
               │ Key: ir_cache:{spec_name}_{hash8}
               │
               ▼ Miss?
           TIER 2: Filesystem (Fallback)
               │ Path: .cache/ir/{spec_name}_{hash8}.json
               │ Auto warm-up → Redis
               │
               ▼ Miss?
           TIER 3: LLM Generation
               │ Save → Redis + Filesystem
               ▼
           Return ApplicationIR
```

### Redis Methods

| Method | Purpose |
|--------|---------|
| `redis.cache_ir(key, data)` | Store IR with 7-day TTL |
| `redis.get_cached_ir(key)` | Retrieve from Redis |
| `redis.clear_ir_cache(spec)` | SCAN-based flush (non-blocking) |
| `redis.get_ir_cache_stats()` | Cache statistics |

### SCAN-based Flush Strategy

Uses Redis SCAN (not KEYS) for production-safe cache clearing:

- Non-blocking: Iterates in batches of 100 keys
- Safe for large datasets
- Pattern-based: `ir_cache:{spec_name}_*`

**Full Documentation**: [REDIS_IR_CACHE.md](../REDIS_IR_CACHE.md)

---

## ConstraintIR

**File**: `src/cognitive/ir/constraint_ir.py`

Typed constraint representation for IR-native matching:

```python
@dataclass
class ConstraintIR:
    entity: str
    field: str
    constraint_type: str  # FORMAT, RANGE, PRESENCE, etc.
    value: Any
    enforcement: str  # STRICT, SOFT, WARNING

    @classmethod
    def from_validation_string(cls, validation_str: str) -> "ConstraintIR":
        """Parse validation string to typed ConstraintIR."""
        # Pattern matching for common formats
        # "price: ge(0.01)" -> ConstraintIR(field="price", type="RANGE", value={"ge": 0.01})
        pass
```

---

## Benefits of IR-Centric Architecture

| Aspect | Before | After |
|--------|--------|-------|
| **Single Source of Truth** | Multiple (SpecReqs, configs) | ApplicationIR |
| **Domain-Specific Logic** | Hardcoded (e-commerce) | Generic, ANY domain |
| **Business Flow Capture** | Manual mapping | Automatic extraction |
| **Validation Rules** | Pattern-based | Comprehensive IR |
| **Code Generation Accuracy** | ~70% | ~100% (IR-driven) |
| **Spec -> Code Alignment** | Loose | Tight (IR-enforced) |

---

## Related Documentation

- [02-ARCHITECTURE.md](02-ARCHITECTURE.md) - Stratified architecture
- [05-CODE_GENERATION.md](05-CODE_GENERATION.md) - Generation pipeline
- [06-VALIDATION.md](06-VALIDATION.md) - Validation system

---

*DevMatrix - ApplicationIR System*
