# Smoke Test Improvement Plan

## Bug #107: LLM-Driven Smoke Test Generation

**Date**: 2025-11-28
**Priority**: CRITICAL
**Affects**: Phase 8.5 (Runtime Smoke Testing)

---

## 📊 Implementation Progress

| Phase | Description | Status | Files | Notes |
|-------|-------------|--------|-------|-------|
| **0** | Quick Fix: UUID mismatch | ✅ DONE | `runtime_smoke_validator.py:443` | Changed `...004` → `...005` for orders |
| **1** | Data Models | ✅ DONE | `smoke_test_models.py` | TestScenario, SmokeTestPlan, ScenarioResult |
| **2** | Planner Agent | ✅ DONE | `agents/planner_agent.py` | LLM generates scenarios from IR |
| **3** | Seed Data Agent | ✅ DONE | `agents/seed_data_agent.py` | LLM generates seed_db.py from plan |
| **4** | Executor Agent | ✅ DONE | `agents/executor_agent.py` | HTTP execution (no LLM needed) |
| **5** | Validator Agent | ✅ DONE | `agents/validation_agent.py` | LLM analyzes failures |
| **6** | Orchestrator | ✅ DONE | `smoke_test_orchestrator.py` | Coordinates all agents |
| **7** | Pipeline Integration | ✅ DONE | `validation/__init__.py` | Exported all new components |
| **8** | E2E Test | ✅ DONE | Verification script | All components verified |

**Legend**: ⬜ TODO | 🔄 IN PROGRESS | ✅ DONE | ❌ BLOCKED

### Progress Summary

```text
Total Phases: 9
Completed:    9/9 (100%)
In Progress:  0/9
Blocked:      0/9

Last Updated: 2025-11-28
```

### Quick Validation Checklist

After each phase, verify:

- [x] **Phase 0**: Orders endpoint returns 200 (not 404)
- [x] **Phase 1**: Models import without errors
- [x] **Phase 2**: Planner generates valid JSON plan
- [x] **Phase 3**: Seed script is valid Python
- [x] **Phase 4**: Executor can hit endpoints
- [x] **Phase 5**: Validator produces analysis
- [x] **Phase 6**: Orchestrator runs full flow
- [x] **Phase 7**: Pipeline calls orchestrator
- [x] **Phase 8**: E2E passes with strict validation

---

## 1. Problem Statement

### Current Behavior (WRONG)
```python
# runtime_smoke_validator.py:399
# Success (including 4xx which might be expected for invalid test data)
return EndpointTestResult(
    endpoint_path=endpoint.path,
    method=endpoint.method.value,
    success=True,  # ← 404 is marked as success!
    status_code=response.status_code,
    response_time_ms=response_time
)
```

**Result**: Any response with status_code < 500 is considered "success", including 404 Not Found.

### Why Fixed Rules Don't Work
- APIs are infinitely varied (ecommerce, healthcare, IoT, social, etc.)
- Each domain has unique validation rules, business logic, error codes
- Hardcoded scenarios only work for one API type
- We need **dynamic, LLM-generated test scenarios** based on the actual spec/IR

---

## 2. LLM-Driven Architecture

### 2.1 Core Concept

Instead of hardcoded rules, the LLM analyzes:
1. **The API Specification** (OpenAPI/markdown spec)
2. **The IR (Intermediate Representation)** with entities, endpoints, business rules
3. **Generated Seed Data** with actual UUIDs and test values

And generates:
- **Test scenarios per endpoint** with expected status codes
- **Valid payloads** for happy path testing
- **Invalid payloads** specific to each endpoint's validation rules
- **Seed data requirements** for each entity type

### 2.2 New Component: `LLMSmokeTestGenerator`

```python
class LLMSmokeTestGenerator:
    """
    Uses LLM to generate comprehensive smoke test scenarios
    for ANY API based on its specification and IR.
    """

    async def generate_test_plan(
        self,
        ir: ApplicationIR,
        spec_content: str
    ) -> SmokeTestPlan:
        """
        Generate complete smoke test plan using LLM.

        Returns:
            SmokeTestPlan with:
            - seed_data: Dict of entities with test UUIDs and values
            - scenarios: List of TestScenario for each endpoint
        """
        prompt = self._build_generation_prompt(ir, spec_content)
        response = await self.llm.generate(prompt)
        return self._parse_test_plan(response)
```

### 2.3 LLM Prompt Structure

```python
SMOKE_TEST_GENERATION_PROMPT = """
You are generating smoke test scenarios for an API.

## API Specification
{spec_content}

## Intermediate Representation
Entities: {ir.entities}
Endpoints: {ir.endpoints}
Business Rules: {ir.business_rules}

## Your Task
Generate a complete smoke test plan in JSON format:

{{
  "seed_data": {{
    "<entity_name>": {{
      "uuid": "00000000-0000-4000-8000-00000000000X",
      "fields": {{ ... valid field values ... }}
    }}
  }},
  "scenarios": [
    {{
      "endpoint": "GET /products/{{id}}",
      "name": "happy_path",
      "description": "Get existing product",
      "path_params": {{ "id": "00000000-0000-4000-8000-000000000001" }},
      "payload": null,
      "expected_status": 200,
      "expected_response_contains": ["name", "price"]
    }},
    {{
      "endpoint": "GET /products/{{id}}",
      "name": "not_found",
      "description": "Get non-existent product",
      "path_params": {{ "id": "99999999-9999-4000-8000-999999999999" }},
      "payload": null,
      "expected_status": 404
    }},
    {{
      "endpoint": "POST /products",
      "name": "validation_error_negative_price",
      "description": "Reject negative price",
      "payload": {{ "name": "Test", "price": -10 }},
      "expected_status": [400, 422]
    }}
  ]
}}

## Rules
1. Every endpoint MUST have a happy_path scenario expecting 200/201/204
2. Endpoints with {{id}} params MUST have a not_found scenario expecting 404
3. POST/PUT/PATCH endpoints MUST have validation_error scenarios
4. Use the business rules to create domain-specific error scenarios
5. Seed data UUIDs must be predictable (00000000-0000-4000-8000-...)
6. Non-existent UUIDs must be different (99999999-9999-4000-8000-...)
"""
```

### 2.4 Output: SmokeTestPlan

```python
@dataclass
class TestScenario:
    endpoint: str                    # "GET /products/{id}"
    name: str                        # "happy_path", "not_found", etc.
    description: str                 # Human-readable
    path_params: Dict[str, str]      # UUID substitutions
    query_params: Optional[Dict]     # Query string params
    payload: Optional[Dict]          # Request body
    expected_status: Union[int, List[int]]  # 200 or [400, 422]
    expected_response_contains: Optional[List[str]]  # Response validation

@dataclass
class SeedDataEntity:
    entity_name: str
    uuid: str
    fields: Dict[str, Any]

@dataclass
class SmokeTestPlan:
    seed_data: List[SeedDataEntity]
    scenarios: List[TestScenario]

    def get_scenarios_for_endpoint(self, path: str, method: str) -> List[TestScenario]:
        return [s for s in self.scenarios if s.endpoint == f"{method} {path}"]
```

---

## 3. Integration Flow

### 3.1 Pipeline Integration

```
Phase 6: Code Generation
    ↓
Phase 7: Test Generation
    ↓
Phase 8: Validation (contract tests)
    ↓
Phase 8.4: LLM Smoke Test Plan Generation  ← NEW
    ↓
Phase 8.5: Seed Data Generation (from plan)
    ↓
Phase 8.6: Runtime Smoke Execution
    ↓
Phase 9: Deployment
```

### 3.2 New Phase: LLM Smoke Test Plan Generation

```python
async def phase_8_4_generate_smoke_plan(
    self,
    ir: ApplicationIR,
    spec_path: Path
) -> SmokeTestPlan:
    """Generate LLM-driven smoke test plan."""

    generator = LLMSmokeTestGenerator(llm_client=self.llm)

    spec_content = spec_path.read_text()
    plan = await generator.generate_test_plan(ir, spec_content)

    # Save plan for debugging/reference
    plan_path = self.app_dir / "smoke_test_plan.json"
    plan_path.write_text(plan.to_json())

    return plan
```

### 3.3 Modified Seed Data Generation

```python
async def phase_8_5_generate_seed_data(
    self,
    plan: SmokeTestPlan,
    ir: ApplicationIR
) -> str:
    """Generate seed_db.py from LLM smoke test plan."""

    seed_code = generate_seed_script(
        entities=plan.seed_data,
        ir=ir
    )

    return seed_code
```

### 3.4 Modified Runtime Smoke Execution

```python
async def phase_8_6_execute_smoke_tests(
    self,
    plan: SmokeTestPlan
) -> SmokeTestResults:
    """Execute smoke tests using LLM-generated plan."""

    results = []
    for scenario in plan.scenarios:
        result = await self._execute_scenario(scenario)
        results.append(result)

    return SmokeTestResults(
        scenarios=results,
        passed=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success)
    )

async def _execute_scenario(self, scenario: TestScenario) -> ScenarioResult:
    """Execute single scenario and validate against expected status."""

    # Build request
    url = self._build_url(scenario.endpoint, scenario.path_params)
    method = scenario.endpoint.split()[0]

    # Execute
    response = await self._make_request(method, url, scenario.payload)

    # Validate
    expected = scenario.expected_status
    if isinstance(expected, list):
        success = response.status_code in expected
    else:
        success = response.status_code == expected

    return ScenarioResult(
        scenario=scenario,
        actual_status=response.status_code,
        success=success,
        error=None if success else f"Expected {expected}, got {response.status_code}"
    )
```

---

## 4. LLM Generation Examples

### 4.1 E-commerce API

**Input IR:**
```yaml
entities:
  - Product: {name, price, stock}
  - Order: {customer_id, status, total}
business_rules:
  - price > 0
  - stock >= 0
  - can't checkout empty cart
```

**LLM Output:**
```json
{
  "scenarios": [
    {"endpoint": "POST /products", "name": "happy_path", "expected_status": 201},
    {"endpoint": "POST /products", "name": "negative_price", "payload": {"price": -10}, "expected_status": 422},
    {"endpoint": "POST /orders/{id}/checkout", "name": "empty_cart", "expected_status": 422}
  ]
}
```

### 4.2 Healthcare API

**Input IR:**
```yaml
entities:
  - Patient: {name, dob, ssn}
  - Appointment: {patient_id, doctor_id, datetime}
business_rules:
  - SSN must be valid format
  - appointment can't be in the past
  - patient must exist for appointment
```

**LLM Output:**
```json
{
  "scenarios": [
    {"endpoint": "POST /patients", "name": "invalid_ssn", "payload": {"ssn": "invalid"}, "expected_status": 422},
    {"endpoint": "POST /appointments", "name": "past_date", "payload": {"datetime": "2020-01-01"}, "expected_status": 422},
    {"endpoint": "POST /appointments", "name": "invalid_patient", "payload": {"patient_id": "nonexistent"}, "expected_status": 404}
  ]
}
```

### 4.3 IoT API

**Input IR:**
```yaml
entities:
  - Device: {serial, type, firmware_version}
  - Reading: {device_id, value, timestamp}
business_rules:
  - serial must be unique
  - value must be within device type range
```

**LLM Output:**
```json
{
  "scenarios": [
    {"endpoint": "POST /devices", "name": "duplicate_serial", "expected_status": 409},
    {"endpoint": "POST /readings", "name": "value_out_of_range", "expected_status": 422}
  ]
}
```

---

## 5. Implementation Plan

### Phase 1: LLM Smoke Test Generator (Core)

**New File**: `src/validation/llm_smoke_test_generator.py`

```python
class LLMSmokeTestGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate_test_plan(self, ir: ApplicationIR, spec: str) -> SmokeTestPlan:
        prompt = self._build_prompt(ir, spec)
        response = await self.llm.generate(prompt, response_format="json")
        return SmokeTestPlan.from_json(response)

    def _build_prompt(self, ir: ApplicationIR, spec: str) -> str:
        return SMOKE_TEST_GENERATION_PROMPT.format(
            spec_content=spec,
            entities=ir.entities_summary(),
            endpoints=ir.endpoints_summary(),
            business_rules=ir.business_rules_summary()
        )
```

### Phase 2: Seed Data from Plan

**Modify**: `src/services/production_code_generators.py`

```python
def generate_seed_data_from_plan(plan: SmokeTestPlan, ir: ApplicationIR) -> str:
    """Generate seed_db.py using LLM-generated plan."""

    seed_entries = []
    for entity in plan.seed_data:
        seed_entries.append(f"""
    test_{entity.entity_name.lower()} = {entity.entity_name}Entity(
        id=UUID("{entity.uuid}"),
        {', '.join(f'{k}={repr(v)}' for k, v in entity.fields.items())}
    )
    session.add(test_{entity.entity_name.lower()})
""")

    return SEED_TEMPLATE.format(seed_entries='\n'.join(seed_entries))
```

### Phase 3: Scenario Executor

**Modify**: `src/validation/runtime_smoke_validator.py`

```python
class RuntimeSmokeValidator:
    async def run_with_plan(self, plan: SmokeTestPlan) -> SmokeTestResults:
        """Execute smoke tests using LLM-generated plan."""

        results = []
        for scenario in plan.scenarios:
            result = await self._execute_scenario(scenario)
            results.append(result)

            # Log each scenario result
            status_icon = "✅" if result.success else "❌"
            logger.info(f"{status_icon} {scenario.endpoint} [{scenario.name}]: "
                       f"{result.actual_status} (expected {scenario.expected_status})")

        return SmokeTestResults(scenarios=results)
```

### Phase 4: Pipeline Integration

**Modify**: `src/agents/orchestrator_agent.py`

```python
async def run_pipeline(self, spec_path: Path) -> PipelineResult:
    # ... existing phases ...

    # Phase 8.4: Generate LLM smoke test plan
    smoke_generator = LLMSmokeTestGenerator(self.llm)
    smoke_plan = await smoke_generator.generate_test_plan(ir, spec_content)

    # Phase 8.5: Generate seed data from plan
    seed_code = generate_seed_data_from_plan(smoke_plan, ir)
    (app_dir / "scripts" / "seed_db.py").write_text(seed_code)

    # Phase 8.6: Execute smoke tests
    smoke_validator = RuntimeSmokeValidator(app_dir)
    smoke_results = await smoke_validator.run_with_plan(smoke_plan)
```

---

## 6. File Changes Required

| File | Change | Description |
|------|--------|-------------|
| **NEW** `src/validation/llm_smoke_test_generator.py` | Create | LLM-based test plan generation |
| **NEW** `src/validation/smoke_test_models.py` | Create | Data models (TestScenario, SmokeTestPlan) |
| `src/validation/runtime_smoke_validator.py` | Modify | Execute scenarios from plan, strict validation |
| `src/services/production_code_generators.py` | Modify | Generate seed data from plan |
| `src/agents/orchestrator_agent.py` | Modify | Add Phase 8.4, integrate plan |

---

## 7. Success Criteria

### MVP
- [ ] LLM generates test plan from any API spec
- [ ] Every endpoint has at least happy_path scenario
- [ ] Happy path must return 200/201/204 (strict)
- [ ] 404 only accepted in not_found scenarios
- [ ] Seed data matches plan UUIDs

### Full Implementation
- [ ] Domain-specific validation error scenarios
- [ ] Business rule violation scenarios
- [ ] Response body validation (contains expected fields)
- [ ] smoke_test_plan.json saved for debugging
- [ ] Detailed HTML report per scenario

---

## 8. Example Output

```
=== Phase 8.4: LLM Smoke Test Plan Generation ===
Generated 47 scenarios for 31 endpoints
  - Happy path: 31
  - Not found: 20
  - Validation errors: 15
  - Business rule errors: 6

=== Phase 8.6: Runtime Smoke Tests ===

GET /products
  ✅ happy_path: 200 (expected 200)

GET /products/{id}
  ✅ happy_path: 200 (expected 200)
  ✅ not_found: 404 (expected 404)

POST /products
  ✅ happy_path: 201 (expected 201)
  ✅ negative_price: 422 (expected [400, 422])
  ✅ missing_name: 422 (expected [400, 422])

POST /orders/{id}/checkout
  ✅ happy_path: 200 (expected 200)
  ✅ not_found: 404 (expected 404)
  ✅ empty_cart: 422 (expected 422)

Summary: 47 scenarios
  ✅ Passed: 47
  ❌ Failed: 0
```

---

## 9. Advantages of LLM Approach

| Aspect | Hardcoded Rules | LLM-Driven |
|--------|-----------------|------------|
| **Flexibility** | Only works for known API types | Works for ANY API |
| **Domain Knowledge** | None | Understands business rules |
| **Maintenance** | Manual updates per API type | Auto-adapts to spec |
| **Coverage** | Generic scenarios | Domain-specific scenarios |
| **Scalability** | Doesn't scale | Scales to any complexity |

---

---

## 10. Determinism Strategy

### 10.1 Problem: LLM Non-Determinism

LLMs can generate different outputs for the same input. We need **consistency** without **hardcoded rules**.

### 10.2 Solution: IR-Driven Generation

The LLM doesn't invent - it **reads and interprets** the IR:

```
┌─────────────────────────────────────────────────────────────┐
│                    DETERMINISM SOURCES                       │
│                                                              │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐         │
│  │    IR      │    │   SPEC     │    │  SCHEMAS   │         │
│  │ (entities, │ +  │ (business  │ +  │ (field     │ = INPUT │
│  │ endpoints) │    │  rules)    │    │  types)    │         │
│  └────────────┘    └────────────┘    └────────────┘         │
│                           │                                  │
│                           ▼                                  │
│                  ┌─────────────────┐                        │
│                  │   LLM READS &   │                        │
│                  │   INTERPRETS    │                        │
│                  │  (temp=0)       │                        │
│                  └─────────────────┘                        │
│                           │                                  │
│                           ▼                                  │
│                  ┌─────────────────┐                        │
│                  │  DETERMINISTIC  │                        │
│                  │     OUTPUT      │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 What the LLM Reads (Not Invents)

| Source | LLM Reads | Generates |
|--------|-----------|-----------|
| **IR Endpoints** | `GET /products/{id}` | Scenario for that exact path |
| **IR Entities** | `Product: {name, price, stock}` | Seed data with those fields |
| **IR Field Types** | `price: Decimal, stock: Integer` | Valid/invalid values for types |
| **Spec Business Rules** | "price must be > 0" | Scenario with `price: -10` |
| **Spec Validations** | "email must be unique" | Scenario testing duplicate email |
| **IR Relationships** | `Order.customer_id → Customer.id` | FK dependency in seed order |

### 10.4 Determinism Techniques

```python
class DeterministicLLMConfig:
    """Configuration for deterministic LLM outputs."""

    temperature: float = 0.0          # No randomness
    seed: int = 42                    # Fixed seed if supported
    response_format: str = "json"     # Structured output

    # Validation ensures completeness
    required_coverage = {
        "happy_path": "ALL endpoints",
        "not_found": "endpoints with {id} param",
        "validation_error": "endpoints with request body"
    }
```

### 10.5 IR as Single Source of Truth

```python
# The IR contains everything needed - LLM just interprets
@dataclass
class ApplicationIR:
    entities: List[Entity]           # What data exists
    endpoints: List[Endpoint]        # What operations exist
    business_rules: List[Rule]       # What constraints exist
    relationships: List[Relationship] # How data connects

# LLM Prompt Strategy: "Read and Map"
DETERMINISTIC_PROMPT = """
You are generating smoke tests by READING the IR, not inventing rules.

## IR Data (Source of Truth)
{ir_json}

## Your Task
For EACH endpoint in the IR, generate scenarios by:

1. READ the endpoint definition
2. READ the request/response schemas
3. READ any business rules that mention this endpoint
4. MAP to test scenarios:
   - happy_path: Use valid data from schema
   - not_found: Only if endpoint has {id} parameter
   - validation_error: Only if schema has constraints (min, max, pattern, required)
   - business_rule_error: Only if IR.business_rules mentions this endpoint

DO NOT invent scenarios not supported by the IR.
DO NOT skip scenarios that ARE supported by the IR.
"""
```

### 10.6 Validation Layer (Ensures Completeness)

```python
class PlanValidator:
    """Validates that LLM output covers all IR elements."""

    def validate(self, plan: SmokeTestPlan, ir: ApplicationIR) -> ValidationResult:
        errors = []

        # Every endpoint must have happy_path
        for endpoint in ir.endpoints:
            key = f"{endpoint.method} {endpoint.path}"
            if not self._has_scenario(plan, key, "happy_path"):
                errors.append(f"Missing happy_path for {key}")

        # Endpoints with {id} must have not_found
        for endpoint in ir.endpoints:
            if "{" in endpoint.path:  # Has path param
                key = f"{endpoint.method} {endpoint.path}"
                if not self._has_scenario(plan, key, "not_found"):
                    errors.append(f"Missing not_found for {key}")

        # POST/PUT/PATCH with schema must have validation_error
        for endpoint in ir.endpoints:
            if endpoint.method in ["POST", "PUT", "PATCH"] and endpoint.request_schema:
                key = f"{endpoint.method} {endpoint.path}"
                if not self._has_scenario(plan, key, "validation_error"):
                    errors.append(f"Missing validation_error for {key}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 10.7 Deterministic UUID Assignment

```python
# UUIDs are deterministic based on entity order in IR
def generate_deterministic_uuid(entity_name: str, ir: ApplicationIR) -> str:
    """Generate predictable UUID based on entity position in IR."""
    entity_index = next(
        i for i, e in enumerate(ir.entities)
        if e.name == entity_name
    )
    # UUID format: 00000000-0000-4000-8000-00000000000X
    return f"00000000-0000-4000-8000-{str(entity_index + 1).zfill(12)}"

# Not-found UUIDs also deterministic
def generate_not_found_uuid(entity_name: str, ir: ApplicationIR) -> str:
    entity_index = next(
        i for i, e in enumerate(ir.entities)
        if e.name == entity_name
    )
    return f"99999999-9999-4000-8000-{str(entity_index + 1).zfill(12)}"
```

### 10.8 Example: IR → Deterministic Scenarios

**Input IR:**
```json
{
  "entities": [
    {"name": "Product", "fields": [
      {"name": "name", "type": "string", "required": true},
      {"name": "price", "type": "decimal", "required": true, "min": 0.01}
    ]}
  ],
  "endpoints": [
    {"method": "GET", "path": "/products"},
    {"method": "GET", "path": "/products/{id}"},
    {"method": "POST", "path": "/products", "request_schema": "ProductCreate"}
  ],
  "business_rules": [
    {"description": "price must be positive", "applies_to": "Product.price"}
  ]
}
```

**Deterministic Output (always the same):**
```json
{
  "seed_data": [
    {
      "entity_name": "Product",
      "uuid": "00000000-0000-4000-8000-000000000001",
      "fields": {"name": "Test Product", "price": 99.99}
    }
  ],
  "scenarios": [
    {
      "endpoint": "GET /products",
      "name": "happy_path",
      "expected_status": 200,
      "reason": "IR has this endpoint, always needs happy_path"
    },
    {
      "endpoint": "GET /products/{id}",
      "name": "happy_path",
      "path_params": {"id": "00000000-0000-4000-8000-000000000001"},
      "expected_status": 200,
      "reason": "IR has this endpoint with {id}"
    },
    {
      "endpoint": "GET /products/{id}",
      "name": "not_found",
      "path_params": {"id": "99999999-9999-4000-8000-000000000001"},
      "expected_status": 404,
      "reason": "IR endpoint has {id} param, must test not_found"
    },
    {
      "endpoint": "POST /products",
      "name": "happy_path",
      "payload": {"name": "New Product", "price": 50.00},
      "expected_status": 201,
      "reason": "IR has POST endpoint with request_schema"
    },
    {
      "endpoint": "POST /products",
      "name": "validation_error_negative_price",
      "payload": {"name": "Bad Product", "price": -10},
      "expected_status": [400, 422],
      "reason": "IR.business_rules says 'price must be positive'"
    },
    {
      "endpoint": "POST /products",
      "name": "validation_error_missing_name",
      "payload": {"price": 50.00},
      "expected_status": [400, 422],
      "reason": "IR.entities.Product.fields.name has required=true"
    }
  ]
}
```

### 10.9 Summary: Determinism Without Hard Rules

| Aspect | Hard Rules (Bad) | IR-Driven (Good) |
|--------|------------------|------------------|
| "All POST need validation_error" | ❌ Imposed | ✅ Only if schema has constraints |
| "404 for all {id} endpoints" | ❌ Imposed | ✅ Only if path has {id} param |
| "Test negative price" | ❌ Imposed | ✅ Only if IR says "price > 0" |
| UUID assignment | ❌ Random | ✅ Deterministic from entity index |
| Output consistency | ❌ Varies | ✅ Same IR → Same output |

---

## 11. Specialized Agent Architecture

### 11.1 Agent Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SMOKE TEST ORCHESTRATOR                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   PLANNER    │  │  SEED DATA   │  │   EXECUTOR   │              │
│  │    AGENT     │→ │    AGENT     │→ │    AGENT     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                │                  │                       │
│         ▼                ▼                  ▼                       │
│  ┌──────────────────────────────────────────────────┐              │
│  │              VALIDATOR AGENT                      │              │
│  │         (Results Analysis & Reporting)            │              │
│  └──────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Agent Definitions

#### Agent 1: SmokeTestPlannerAgent

**Purpose**: Analyze API spec and IR to generate comprehensive test scenarios

**Input**:
- API Specification (markdown/OpenAPI)
- Application IR (entities, endpoints, business rules)

**Output**: `SmokeTestPlan` with all scenarios

```python
class SmokeTestPlannerAgent:
    """
    Specialized agent for generating smoke test plans.
    Understands API semantics, HTTP conventions, and domain logic.
    """

    SYSTEM_PROMPT = """
    You are an expert API test engineer. Your job is to analyze an API
    specification and generate comprehensive smoke test scenarios.

    For each endpoint, you MUST generate:
    1. happy_path: Valid request → expect 200/201/204
    2. not_found (if has {id}): Invalid UUID → expect 404
    3. validation_error (if POST/PUT/PATCH): Invalid payload → expect 400/422
    4. business_rule_error: Domain-specific violations → expect 422

    You understand:
    - REST conventions (GET=read, POST=create, PUT=replace, PATCH=update, DELETE=remove)
    - Status code semantics (200=OK, 201=Created, 204=NoContent, 400=BadRequest, 404=NotFound, 422=Unprocessable)
    - Domain-specific business rules and how to violate them for testing
    """

    async def generate_plan(
        self,
        spec: str,
        ir: ApplicationIR
    ) -> SmokeTestPlan:
        prompt = f"""
        ## API Specification
        {spec}

        ## Entities
        {self._format_entities(ir)}

        ## Endpoints
        {self._format_endpoints(ir)}

        ## Business Rules
        {self._format_business_rules(ir)}

        Generate a complete SmokeTestPlan in JSON format.
        """

        response = await self.llm.generate(
            system=self.SYSTEM_PROMPT,
            user=prompt,
            response_format="json"
        )

        return SmokeTestPlan.from_json(response)
```

---

#### Agent 2: SeedDataAgent

**Purpose**: Generate seed data that matches the test plan

**Input**:
- `SmokeTestPlan` with required UUIDs
- Application IR with entity schemas

**Output**: `seed_db.py` script

```python
class SeedDataAgent:
    """
    Specialized agent for generating realistic seed data.
    Ensures data integrity, relationships, and test compatibility.
    """

    SYSTEM_PROMPT = """
    You are a database seeding expert. Your job is to generate Python code
    that creates test data for smoke testing.

    Requirements:
    1. Use predictable UUIDs matching the test plan (00000000-0000-4000-8000-...)
    2. Create valid relationships between entities (FK constraints)
    3. Use realistic but simple test values
    4. Handle all required fields per entity schema
    5. Generate idempotent seed script (can run multiple times)

    Output format: Pure Python code for seed_db.py
    """

    async def generate_seed_script(
        self,
        plan: SmokeTestPlan,
        ir: ApplicationIR
    ) -> str:
        # Extract required entities from plan
        required_entities = self._extract_required_entities(plan)

        prompt = f"""
        ## Required Seed Data
        {json.dumps(plan.seed_data, indent=2)}

        ## Entity Schemas
        {self._format_entity_schemas(ir)}

        ## Relationships
        {self._format_relationships(ir)}

        Generate a complete seed_db.py script that:
        1. Creates all required test entities
        2. Uses the exact UUIDs from the plan
        3. Handles relationships correctly (create parents before children)
        4. Is idempotent (handles duplicates gracefully)
        """

        response = await self.llm.generate(
            system=self.SYSTEM_PROMPT,
            user=prompt,
            response_format="code"
        )

        return self._extract_python_code(response)
```

---

#### Agent 3: ScenarioExecutorAgent

**Purpose**: Execute test scenarios and collect raw results

**Input**:
- `SmokeTestPlan` with scenarios
- Running server base URL

**Output**: `List[ScenarioResult]` with raw HTTP responses

```python
class ScenarioExecutorAgent:
    """
    Specialized agent for executing HTTP requests.
    Handles request building, timing, and response capture.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def execute_all(
        self,
        plan: SmokeTestPlan
    ) -> List[ScenarioResult]:
        results = []

        for scenario in plan.scenarios:
            result = await self._execute_scenario(scenario)
            results.append(result)

            # Log progress
            icon = "✅" if result.status_matches else "❌"
            logger.info(
                f"{icon} {scenario.endpoint} [{scenario.name}]: "
                f"{result.actual_status} (expected {scenario.expected_status})"
            )

        return results

    async def _execute_scenario(
        self,
        scenario: TestScenario
    ) -> ScenarioResult:
        # Build URL with path params
        url = self._build_url(scenario)
        method = scenario.endpoint.split()[0]

        start_time = time.time()

        try:
            response = await self._make_request(
                method=method,
                url=url,
                payload=scenario.payload,
                query_params=scenario.query_params
            )

            return ScenarioResult(
                scenario=scenario,
                actual_status=response.status_code,
                response_body=response.text,
                response_time_ms=(time.time() - start_time) * 1000,
                status_matches=self._check_status_match(
                    response.status_code,
                    scenario.expected_status
                )
            )

        except Exception as e:
            return ScenarioResult(
                scenario=scenario,
                actual_status=None,
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
                status_matches=False
            )

    def _check_status_match(
        self,
        actual: int,
        expected: Union[int, List[int]]
    ) -> bool:
        if isinstance(expected, list):
            return actual in expected
        return actual == expected
```

---

#### Agent 4: ValidationAgent

**Purpose**: Analyze results, identify patterns, and generate reports

**Input**:
- `List[ScenarioResult]` from executor
- `SmokeTestPlan` for context

**Output**: `SmokeTestReport` with analysis and recommendations

```python
class ValidationAgent:
    """
    Specialized agent for analyzing test results.
    Uses LLM to understand failures and provide insights.
    """

    SYSTEM_PROMPT = """
    You are a QA analysis expert. Your job is to analyze smoke test results
    and provide actionable insights.

    You identify:
    1. Pattern of failures (all 404s? all POST failures?)
    2. Root cause analysis (missing seed data? wrong routes? validation issues?)
    3. Severity classification (critical vs minor)
    4. Recommended fixes with specific file/code references

    Be concise but thorough. Prioritize actionable recommendations.
    """

    async def analyze_results(
        self,
        results: List[ScenarioResult],
        plan: SmokeTestPlan
    ) -> SmokeTestReport:
        # Calculate metrics
        metrics = self._calculate_metrics(results)

        # If all passed, simple report
        if metrics.failed == 0:
            return SmokeTestReport(
                metrics=metrics,
                status="PASSED",
                summary="All smoke tests passed successfully",
                failures=[],
                recommendations=[]
            )

        # Use LLM to analyze failures
        failures = [r for r in results if not r.status_matches]

        prompt = f"""
        ## Test Metrics
        Total: {metrics.total}
        Passed: {metrics.passed}
        Failed: {metrics.failed}

        ## Failed Scenarios
        {self._format_failures(failures)}

        ## Test Plan Context
        {self._format_plan_context(plan)}

        Analyze these failures and provide:
        1. Root cause analysis
        2. Pattern identification
        3. Severity assessment
        4. Specific recommendations to fix
        """

        analysis = await self.llm.generate(
            system=self.SYSTEM_PROMPT,
            user=prompt
        )

        return SmokeTestReport(
            metrics=metrics,
            status="FAILED",
            summary=f"{metrics.failed} of {metrics.total} scenarios failed",
            failures=failures,
            analysis=analysis,
            recommendations=self._extract_recommendations(analysis)
        )
```

---

### 10.3 Orchestrator

```python
class SmokeTestOrchestrator:
    """
    Coordinates all smoke test agents through the complete workflow.
    """

    def __init__(self, llm_client: LLMClient):
        self.planner = SmokeTestPlannerAgent(llm_client)
        self.seed_generator = SeedDataAgent(llm_client)
        self.validator = ValidationAgent(llm_client)

    async def run_smoke_tests(
        self,
        spec_path: Path,
        ir: ApplicationIR,
        app_dir: Path
    ) -> SmokeTestReport:
        """
        Complete smoke test workflow using specialized agents.
        """

        # Phase 1: Generate test plan
        logger.info("🎯 Phase 1: Generating smoke test plan...")
        spec_content = spec_path.read_text()
        plan = await self.planner.generate_plan(spec_content, ir)
        logger.info(f"   Generated {len(plan.scenarios)} scenarios")

        # Save plan for debugging
        (app_dir / "smoke_test_plan.json").write_text(plan.to_json())

        # Phase 2: Generate seed data
        logger.info("🌱 Phase 2: Generating seed data...")
        seed_script = await self.seed_generator.generate_seed_script(plan, ir)
        (app_dir / "scripts" / "seed_db.py").write_text(seed_script)

        # Phase 3: Start server and seed
        logger.info("🚀 Phase 3: Starting server...")
        server = await self._start_server(app_dir)

        try:
            # Phase 4: Execute scenarios
            logger.info("🧪 Phase 4: Executing scenarios...")
            executor = ScenarioExecutorAgent(base_url=server.url)
            results = await executor.execute_all(plan)

            # Phase 5: Analyze results
            logger.info("📊 Phase 5: Analyzing results...")
            report = await self.validator.analyze_results(results, plan)

            return report

        finally:
            await self._stop_server(server)
```

---

### 10.4 Data Models

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
import json

@dataclass
class TestScenario:
    """Single test scenario for an endpoint."""
    endpoint: str                              # "GET /products/{id}"
    name: str                                  # "happy_path", "not_found"
    description: str                           # Human-readable
    path_params: Dict[str, str] = field(default_factory=dict)
    query_params: Optional[Dict[str, str]] = None
    payload: Optional[Dict[str, Any]] = None
    expected_status: Union[int, List[int]] = 200
    expected_response_contains: Optional[List[str]] = None

@dataclass
class SeedDataEntity:
    """Seed data for a single entity."""
    entity_name: str
    uuid: str
    fields: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)  # FK dependencies

@dataclass
class SmokeTestPlan:
    """Complete smoke test plan generated by PlannerAgent."""
    seed_data: List[SeedDataEntity]
    scenarios: List[TestScenario]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> 'SmokeTestPlan':
        parsed = json.loads(data)
        return cls(
            seed_data=[SeedDataEntity(**e) for e in parsed['seed_data']],
            scenarios=[TestScenario(**s) for s in parsed['scenarios']]
        )

@dataclass
class ScenarioResult:
    """Result of executing a single scenario."""
    scenario: TestScenario
    actual_status: Optional[int]
    response_body: Optional[str] = None
    response_time_ms: float = 0
    status_matches: bool = False
    error: Optional[str] = None

@dataclass
class TestMetrics:
    """Aggregated test metrics."""
    total: int
    passed: int
    failed: int
    happy_path_passed: int
    happy_path_total: int
    avg_response_time_ms: float

@dataclass
class SmokeTestReport:
    """Final report from ValidationAgent."""
    metrics: TestMetrics
    status: str  # "PASSED" | "FAILED"
    summary: str
    failures: List[ScenarioResult]
    analysis: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
```

---

### 10.5 Agent Communication Protocol

```yaml
Agent Communication Flow:

1. Orchestrator → PlannerAgent:
   Input: {spec_content, ir}
   Output: SmokeTestPlan

2. Orchestrator → SeedDataAgent:
   Input: {plan, ir}
   Output: seed_db.py (string)

3. Orchestrator → ScenarioExecutorAgent:
   Input: {plan, base_url}
   Output: List[ScenarioResult]

4. Orchestrator → ValidationAgent:
   Input: {results, plan}
   Output: SmokeTestReport

Error Handling:
- PlannerAgent failure → Abort with plan generation error
- SeedDataAgent failure → Retry with simplified entities
- ExecutorAgent failure → Mark scenario as error, continue others
- ValidationAgent failure → Return raw results without analysis
```

---

### 10.6 Prompt Templates per Agent

#### PlannerAgent Prompt

```python
PLANNER_PROMPT = """
## Context
You are analyzing an API to generate smoke test scenarios.

## API Specification
{spec}

## Entities (from IR)
{entities}

## Endpoints (from IR)
{endpoints}

## Business Rules
{business_rules}

## Your Task
Generate a JSON object with this structure:

{{
  "seed_data": [
    {{
      "entity_name": "Product",
      "uuid": "00000000-0000-4000-8000-000000000001",
      "fields": {{"name": "Test Product", "price": 99.99, "stock": 100}},
      "depends_on": []
    }}
  ],
  "scenarios": [
    {{
      "endpoint": "GET /products",
      "name": "happy_path",
      "description": "List all products",
      "expected_status": 200
    }},
    {{
      "endpoint": "GET /products/{{id}}",
      "name": "happy_path",
      "description": "Get existing product",
      "path_params": {{"id": "00000000-0000-4000-8000-000000000001"}},
      "expected_status": 200
    }},
    {{
      "endpoint": "GET /products/{{id}}",
      "name": "not_found",
      "description": "Get non-existent product",
      "path_params": {{"id": "99999999-9999-4000-8000-999999999999"}},
      "expected_status": 404
    }}
  ]
}}

## Rules
1. EVERY endpoint needs a happy_path scenario
2. Endpoints with {{id}} need a not_found scenario
3. POST/PUT/PATCH need validation_error scenarios
4. Use business rules to create domain-specific error scenarios
5. UUIDs: seed data = 00000000-..., not found = 99999999-...
"""
```

#### SeedDataAgent Prompt

```python
SEED_DATA_PROMPT = """
## Context
Generate a Python script to seed test data for smoke testing.

## Required Entities
{required_entities}

## Entity Schemas (from IR)
{entity_schemas}

## Relationships
{relationships}

## Output Requirements
1. Use exact UUIDs from the plan
2. Create entities in dependency order (parents first)
3. Handle duplicate key errors gracefully
4. Use async SQLAlchemy patterns
5. Include proper imports

Generate ONLY the Python code, no explanations.
"""
```

#### ValidationAgent Prompt

```python
VALIDATION_PROMPT = """
## Context
Analyze smoke test failures and provide insights.

## Test Results Summary
Total: {total} | Passed: {passed} | Failed: {failed}

## Failed Scenarios
{failed_scenarios}

## Questions to Answer
1. What pattern do you see in the failures?
2. What is the likely root cause?
3. How severe is this issue? (Critical/High/Medium/Low)
4. What specific fix would you recommend?

Be concise and actionable.
"""
```

---

## Appendix: Implementation Checklist

### Files to Create

- [ ] `src/validation/smoke_test_models.py` - Data models
- [ ] `src/validation/agents/planner_agent.py` - Test plan generation
- [ ] `src/validation/agents/seed_data_agent.py` - Seed script generation
- [ ] `src/validation/agents/executor_agent.py` - Scenario execution
- [ ] `src/validation/agents/validation_agent.py` - Results analysis
- [ ] `src/validation/smoke_test_orchestrator.py` - Coordination

### Files to Modify

- [ ] `src/validation/runtime_smoke_validator.py` - Integrate with orchestrator
- [ ] `src/agents/orchestrator_agent.py` - Add new phases
- [ ] `src/services/production_code_generators.py` - Remove hardcoded seed logic
