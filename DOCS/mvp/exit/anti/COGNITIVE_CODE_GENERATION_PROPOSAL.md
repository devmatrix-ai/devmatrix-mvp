# Cognitive Code Generation - Architectural Proposal

**Status:** RFC v2.1
**Author:** DevMatrix Architecture
**Date:** 2025-11-30
**Architecture:** **IR-Centric** (IR is source of truth, constrains all operations)

---

## 📊 Implementation Progress Tracker

| Phase | Task | Status | File/Location | Notes |
|-------|------|--------|---------------|-------|
| **1. Infrastructure** | | | | |
| 1.1 | Add `IRFlow` to BehaviorModelIR | ✅ Done | `src/cognitive/ir/behavior_model.py` | Extended Flow model |
| 1.2 | `get_patterns_for_flow()` in NegativePatternStore | ✅ Done | `src/learning/negative_pattern_store.py` | Semantic flow matching |
| 1.3 | `get_patterns_for_constraint_type()` | ✅ Done | `src/learning/negative_pattern_store.py` | Constraint type mapping |
| 1.4 | `store_cognitive_regression()` | ✅ Done | `src/learning/negative_pattern_store.py` | + CognitiveRegressionPattern dataclass |
| 1.5 | Create `CognitiveCache` class | ✅ Done | `src/cognitive/cache/cognitive_cache.py` | IR-based keys, LRU eviction |
| **2. Core Implementation** | | | | |
| 2.1 | Create `IRCentricCognitivePass` class | ✅ Done | `src/cognitive/passes/ir_centric_cognitive_pass.py` | Main cognitive pass |
| 2.2 | Implement function-level AST extraction | ✅ Done | Same file | `_extract_flow_functions()` |
| 2.3 | Implement IR Guard prompt generation | ✅ Done | Same file | `_build_ir_guard()` |
| 2.4 | Wire to `IRComplianceValidator` | ✅ Done | Same file | `_validate_against_ir()` |
| **3. Integration** | | | | |
| 3.1 | Create `CognitiveCodeGenerationService` | ✅ Done | `src/services/cognitive_code_generation_service.py` | Wrapper service |
| 3.2 | Add feature flag `ENABLE_COGNITIVE_PASS` | ✅ Done | Same file | Env var control |
| 3.3 | Add baseline comparison mode | ✅ Done | Same file | `_compare_baseline()` |
| 3.4 | Integrate metrics collection | ✅ Done | Same file | `CognitiveGenerationMetrics` |
| **4. Optimization** | | | | |
| 4.1 | Profile token usage | ⏳ Pending | - | Analysis |
| 4.2 | Tune cache TTL | ⏳ Pending | `CognitiveCache` | Performance |
| 4.3 | Add parallel function processing | ⏳ Pending | `IRCentricCognitivePass` | Async batching |
| 4.4 | Tune rollback thresholds | ⏳ Pending | Config | Safety tuning |
| **5. Pipeline Integration** | | | | |
| 5.1 | Wire into CodeGenerationService | ✅ Done | `src/services/code_generation_service.py` | `_apply_cognitive_pass()` method |
| 5.2 | Add Circuit Breaker pattern | ✅ Done | `src/services/cognitive_code_generation_service.py` | `CognitiveCircuitBreaker` class |
| 5.3 | Add structured logging | ⏳ Pending | All cognitive files | Observability |
| 5.4 | E2E validation | ✅ Done | `tests/e2e/` | Test: Ariel_test_006_25_023 |

**Legend:** ✅ Done | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Last Updated:** 2025-11-30 (Phase 5.4 Complete - E2E Validation)

---

## E2E Test Results (Ariel_test_006_25_023)

**Test Date:** 2025-11-30
**Spec:** `ecommerce-api-spec-human.md`
**Output:** `tests/e2e/generated_apps/ecommerce-api-spec-human_1764502279`

### Pipeline Performance

| Metric | Value | Status |
|--------|-------|--------|
| **Semantic Compliance** | 99.9% | ✅ |
| **Entities** | 100% (6/6) | ✅ |
| **Endpoints** | 100% (34/33) | ✅ |
| **Validations** | 99.4% (307/309) | ✅ |
| **Pipeline Precision** | 78.8% | ✅ |
| **Files Generated** | 96 | ✅ |
| **Tests Generated** | 265 | ✅ |
| **LLM Tokens** | 6,102 (~$0.05) | ✅ |

### Phase Execution Times

| Phase | Time | Checkpoints |
|-------|------|-------------|
| spec_ingestion | 236.3s | 4/4 ✅ |
| requirements_analysis | 0.5s | 5/5 ✅ |
| multi_pass_planning | 0.1s | 5/5 ✅ |
| atomization | 1.3s | 5/5 ✅ |
| dag_construction | 4.9s | 5/5 ✅ |
| wave_execution | 1.3s | 5/5 ✅ |
| validation | 15.4s | 10/5 ✅ |
| deployment | 0.3s | 7/5 ✅ |
| health_verification | 1.1s | 5/5 ✅ |
| learning | 0.1s | 5/5 ✅ |

### Smoke Test Results

| Metric | Value |
|--------|-------|
| Pass Rate | 86.7% (26/30) |
| HTTP 500 Errors | 4 (complex workflows) |

**Failing Endpoints (HTTP 500):**
- `POST /carts/{id}/items` - add_item_to_cart workflow
- `POST /orders/{id}/pay` - pay_order workflow
- `POST /orders/{id}/cancel` - cancel_order workflow
- `POST /carts/{id}/checkout` - checkout workflow

**Root Cause:** Complex workflow endpoints require runtime debugging with Docker rebuild enabled.

### Resource Usage

| Metric | Value |
|--------|-------|
| Peak Memory | 104.9 MB |
| Avg Memory | 44.5 MB |
| Peak CPU | 10.0% |
| Avg CPU | 0.8% |

### Conclusions

1. **IR-Centric Pipeline:** ✅ Working correctly (99.9% semantic compliance)
2. **Code Generation:** ✅ 96 files generated successfully
3. **Test Generation:** ✅ 265 tests generated from IR
4. **Validation:** ✅ Full validation pipeline passed
5. **Smoke Tests:** ⚠️ 86.7% pass rate (4 complex workflow failures)

**Next Steps:**
- Phase 5.3: Add structured logging for cognitive pass observability
- Fix workflow endpoints (separate bug ticket)
- Enable Docker rebuild in smoke repair loop for runtime fixes

---

## Architectural Philosophy: IR-Centric vs IR-Adjacent

| Approach | Description | This Proposal |
|----------|-------------|---------------|
| **IR-Adjacent** | IR passed but not deeply integrated | ❌ |
| **IR-Constrained** | IR provides boundaries, flexible within | ❌ |
| **IR-Centric** | IR is source of truth, drives and validates everything | ✅ |

**IR-Centric Principles:**

1. **IR as Contract**: Every generated file has an IR contract (schemas, endpoints, relationships)
2. **IRFlow as Semantic Unit**: Pattern matching pivots on IRFlow, not file paths
3. **Function-Level Granularity**: Enhance individual functions implementing IRFlows
4. **Post-Enhancement Validation**: LLM output validated against IR before acceptance
5. **Rollback on Violation**: If enhanced code violates IR, revert to template output

---

## Problem Statement

DevMatrix claims to be a "Cognitive Compiler" but the current code generation is **stateless**:

| Component | Uses Learning? | Reality |
|-----------|---------------|---------|
| PatternBank | NO | Static templates |
| ProductionCodeGenerators | NO | Hardcoded Python |
| BehaviorCodeGenerator | NO | Template-based |
| CodeRepairAgent | YES | Only post-generation |

**Result:** The system learns but doesn't apply learning during generation.

---

## Vision: True Cognitive Compilation

A cognitive compiler should have these properties:

1. **Memory**: Remember past failures and successes
2. **Adaptation**: Generate different code based on learned patterns
3. **Prevention**: Avoid known errors at compile time, not runtime
4. **Evolution**: Improve over time without code changes

---

## Core Data Structures

### IRFlow: The Semantic Unit

```python
@dataclass
class IRFlow:
    """The semantic unit for cognitive enhancement."""
    flow_id: str                    # e.g., "add_item_to_cart"
    name: str                       # Human-readable name
    version: str                    # Contract version (see below)
    primary_entity: str             # Main entity (Cart)
    entities_involved: List[str]    # All entities (Cart, Product, CartItem)
    constraint_types: List[str]     # stock_constraint, workflow_constraint
    preconditions: List[str]        # cart.open, product.exists, qty > 0
    postconditions: List[str]       # cart_item added, stock decreased
    endpoint: str                   # POST /carts/{id}/items
    implementation_name: str        # Function name in code

### IRFlow Version Strategy

The `version` field is CRITICAL for cache invalidation. Two strategies:

**Strategy A: IR-Global Version** (Simpler)
```python
# All flows inherit ApplicationIR version
flow.version = ir.version  # e.g., "1.0.0"
```

**Strategy B: Semantic Hash** (More Granular)
```python
# Version derived from flow content
flow.version = hash(
    flow.preconditions,
    flow.postconditions,
    flow.constraint_types,
    flow.entities_involved
)[:8]
```

**Implementation (current)**: Using Strategy A + semantic hash for cache key components.
Without version tracking, cache may serve stale code when spec changes.

@dataclass
class FlowFunction:
    """Maps IRFlow to actual code function."""
    ir_flow: IRFlow
    file_path: str
    function_name: str
    function_code: str
    start_line: int
    end_line: int
```

### IRContract: Per-Flow Contract

```python
@dataclass
class IRContract:
    """Contract extracted from ApplicationIR for a specific IRFlow."""
    flow: IRFlow
    schemas: List[str]           # Pydantic schemas this flow must use
    relationships: List[str]     # Related entities and their types
    required_imports: List[str]  # Imports mandated by IR
    invariants: List[str]        # Rules that must never be violated
```

---

## Proposed Architecture: Multi-Pass Cognitive Pipeline

### Pass 1: Template Pass (Deterministic)

```python
# UNCHANGED - Keep existing PatternBank
class TemplatePass:
    """Fast, deterministic generation of boilerplate."""

    def generate(self, ir: ApplicationIR) -> Dict[str, str]:
        # Existing PatternBank + ProductionCodeGenerators
        return self.pattern_bank.compose(ir)
```

**Output:** 95% of code (models, routes, config, tests structure)

### Pass 2: Cognitive Pass (IR-Centric, Flow-Level Enhancement)

```python
class IRCentricCognitivePass:
    """
    TRUE IR-Centric cognitive enhancement.

    Key Principles:
    1. IRFlow is the semantic unit (not file paths)
    2. Function-level granularity (not whole files)
    3. IR constrains what LLM can modify
    4. IR validates output before acceptance
    5. Rollback on IR contract violation
    """

    def __init__(self):
        self.pattern_store = get_negative_pattern_store()
        self.llm_client = get_anthropic_client()
        self.ir_validator = get_ir_compliance_validator()  # Use existing!
        self.cache = CognitiveCache()

    async def enhance(
        self,
        base_code: Dict[str, str],
        ir: ApplicationIR
    ) -> Dict[str, str]:
        """
        IR-Centric enhancement pipeline at FUNCTION level.

        For each file:
        1. Map file → IRFlows it implements
        2. For each IRFlow:
           a. Extract flow function from code
           b. Get patterns for this IRFlow (semantic, not path-based)
           c. Check cache
           d. Enhance function with IR Guard
           e. Validate against IR contract
           f. Apply or rollback
        """
        enhanced = dict(base_code)

        for file_path, code in base_code.items():
            # Step 1: Get IRFlows implemented in this file
            flows = ir.get_flows_for_file(file_path)
            if not flows:
                continue

            # Step 2: Extract flow functions
            flow_functions = self._extract_flow_functions(file_path, code, flows)

            for flow_fn in flow_functions:
                # Step 3: Get patterns for IRFlow (semantic matching)
                patterns = self._get_patterns_for_ir_flow(flow_fn.ir_flow)
                if not patterns:
                    continue

                # Step 4: Check cache
                cache_key = self._compute_cache_key(flow_fn.ir_flow, patterns)
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    enhanced[file_path] = self._apply_function_patch(
                        enhanced[file_path], flow_fn, cached_result
                    )
                    continue

                # Step 5: Extract IR contract for this flow
                ir_contract = self._extract_ir_contract(flow_fn.ir_flow, ir)

                # Step 6: Enhance function with IR Guard
                enhanced_function = await self._cognitive_enhance_function(
                    flow_fn, patterns, ir_contract
                )

                # Step 7: Validate against IR contract
                validation = self.ir_validator.validate_function_against_ir(
                    enhanced_function, ir_contract, ir
                )

                if validation.passed:
                    # Apply patch to file
                    enhanced[file_path] = self._apply_function_patch(
                        enhanced[file_path], flow_fn, enhanced_function
                    )
                    self.cache.set(cache_key, enhanced_function)
                    logger.info(f"✅ {flow_fn.function_name}: Enhanced and IR-compliant")
                else:
                    # ROLLBACK - record cognitive regression
                    logger.warning(
                        f"⚠️ {flow_fn.function_name}: Enhancement violated IR contract, reverted"
                        f"\n   Violations: {validation.violations}"
                    )
                    self._record_cognitive_regression(flow_fn, patterns, validation)

        return enhanced

    def _extract_flow_functions(
        self,
        file_path: str,
        code: str,
        flows: List[IRFlow]
    ) -> List[FlowFunction]:
        """Map IRFlows → actual functions in this file."""
        import ast
        tree = ast.parse(code)

        flow_functions = []
        for ir_flow in flows:
            fn_name = ir_flow.implementation_name
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                    flow_functions.append(FlowFunction(
                        ir_flow=ir_flow,
                        file_path=file_path,
                        function_name=fn_name,
                        function_code=ast.get_source_segment(code, node),
                        start_line=node.lineno,
                        end_line=node.end_lineno
                    ))
                    break

        return flow_functions

    def _get_patterns_for_ir_flow(
        self,
        ir_flow: IRFlow
    ) -> List[GenerationAntiPattern]:
        """
        Query patterns SEMANTICALLY matched to IRFlow.

        NOT: "get patterns for cart_service.py"
        YES: "get patterns for add_item_to_cart flow with Cart, Product entities"
        """
        patterns = []

        # 1. Patterns for this specific flow
        patterns.extend(
            self.pattern_store.get_patterns_for_flow(
                flow_name=ir_flow.name,
                min_occurrences=1
            )
        )

        # 2. Patterns for entities involved
        for entity_name in ir_flow.entities_involved:
            patterns.extend(
                self.pattern_store.get_patterns_for_entity(
                    entity_name=entity_name,
                    min_occurrences=1
                )
            )

        # 3. Patterns for constraint types
        for constraint_type in ir_flow.constraint_types:
            patterns.extend(
                self.pattern_store.get_patterns_for_constraint_type(
                    constraint_type=constraint_type,
                    min_occurrences=1
                )
            )

        # 4. Patterns by exception type
        for error_type in ["AttributeError", "TypeError", "IntegrityError", "KeyError"]:
            patterns.extend(
                self.pattern_store.get_patterns_by_exception(
                    exception_class=error_type,
                    min_occurrences=1
                )
            )

        # Deduplicate and limit
        seen = set()
        unique = []
        for p in patterns:
            if p.pattern_id not in seen:
                seen.add(p.pattern_id)
                unique.append(p)
        return unique[:10]

    def _compute_cache_key(
        self,
        ir_flow: IRFlow,
        patterns: List[GenerationAntiPattern]
    ) -> str:
        """Cache key based on IR semantics, not code text."""
        import hashlib
        pattern_ids = sorted([p.pattern_id for p in patterns])
        key_data = f"{ir_flow.flow_id}:{ir_flow.version}:{':'.join(pattern_ids)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _extract_ir_contract(
        self,
        ir_flow: IRFlow,
        ir: ApplicationIR
    ) -> IRContract:
        """Build IR contract for a specific flow."""
        schemas = []
        for entity in ir_flow.entities_involved:
            if entity in ir.entities:
                schemas.extend([
                    f"{entity}Create",
                    f"{entity}Update",
                    f"{entity}Response"
                ])

        return IRContract(
            flow=ir_flow,
            schemas=list(set(schemas)),
            relationships=[
                rel for e in ir_flow.entities_involved
                if e in ir.entities
                for rel in ir.entities[e].relationships
            ],
            required_imports=self._infer_imports(ir_flow, ir),
            invariants=ir_flow.preconditions + ir_flow.postconditions
        )

    async def _cognitive_enhance_function(
        self,
        flow_fn: FlowFunction,
        anti_patterns: List[GenerationAntiPattern],
        ir_contract: IRContract
    ) -> str:
        """
        LLM enhancement with IR as INVIOLABLE contract.

        The IR Guard tells LLM exactly what it can and cannot modify.
        """
        warnings = self._build_warnings(anti_patterns)
        ir_guard = self._build_ir_guard(ir_contract)

        prompt = f"""You are an AI code optimizer for a FastAPI application.

{ir_guard}

## Anti-Pattern Warnings (from previous smoke test failures)
{warnings}

## Function to Optimize
```python
{flow_fn.function_code}
```

## Task
1. Check if the function contains any of the anti-patterns listed above
2. If yes, fix them using the correct patterns shown
3. The IR CONTRACT is INVIOLABLE - do not change semantics
4. If no issues found, return the function unchanged

Return ONLY the corrected function code, no explanations.
"""

        response = await self.llm_client.generate(prompt)
        return self._extract_code(response)

    def _build_ir_guard(self, contract: IRContract) -> str:
        """Build compressed IR Guard for prompt."""
        flow = contract.flow

        # Compact format to save tokens
        pre = ", ".join(flow.preconditions[:3]) if flow.preconditions else "none"
        post = ", ".join(flow.postconditions[:3]) if flow.postconditions else "none"
        entities = ", ".join(flow.entities_involved)

        return f"""## IR CONTRACT (INVIOLABLE - source of truth)
Flow: {flow.name}
Entities: {entities}
Pre: {pre}
Post: {post}

You MUST NOT:
- Change entity semantics or relationships
- Remove precondition/postcondition checks
- Alter schemas: {', '.join(contract.schemas[:5])}
- Break invariants

You CAN:
- Fix null checks and error handling
- Correct attribute access patterns
- Fix import statements
- Improve exception messages
"""

    def _build_warnings(self, patterns: List[GenerationAntiPattern]) -> str:
        """Build compact warning section from anti-patterns."""
        warnings = []
        for i, p in enumerate(patterns[:5], 1):  # Limit to 5
            bad = p.bad_code_snippet[:80] if p.bad_code_snippet else "..."
            good = p.correct_code_snippet[:80] if p.correct_code_snippet else "..."
            warnings.append(f"""
{i}. {p.exception_class}: {p.error_message_pattern[:50]}
   BAD: {bad}
   GOOD: {good}
""")
        return "\n".join(warnings)

    def _apply_function_patch(
        self,
        file_code: str,
        flow_fn: FlowFunction,
        new_function: str
    ) -> str:
        """
        Replace function in file with enhanced version.

        NOTE (v1 Implementation): Line-based replacement.
        - Depends on lineno/end_lineno being accurate
        - May break with multiple decorators or comments above function
        - Roadmap: v2 will use AST-safe replacement via ast.unparse() (Python 3.9+)
        """
        lines = file_code.split('\n')
        new_lines = (
            lines[:flow_fn.start_line - 1] +
            new_function.split('\n') +
            lines[flow_fn.end_line:]
        )
        return '\n'.join(new_lines)

    def _record_cognitive_regression(
        self,
        flow_fn: FlowFunction,
        patterns: List[GenerationAntiPattern],
        validation
    ) -> None:
        """Record failed enhancement as cognitive regression anti-pattern."""
        regression = CognitiveRegressionPattern(
            ir_flow=flow_fn.ir_flow.name,
            anti_patterns_applied=[p.pattern_id for p in patterns],
            result="ir_contract_violation",
            violations=validation.violations,
            timestamp=datetime.now()
        )
        self.pattern_store.store_cognitive_regression(regression)
```

### Pass 3: Validation Pass (IR-Integrated Static Analysis)

```python
class ValidationPass:
    """Static + IR validation before deployment."""

    def __init__(self):
        self.syntax_checker = SyntaxChecker()
        self.import_checker = ImportChecker()
        self.ir_compliance_checker = get_ir_compliance_validator()  # Reuse existing!

    def validate(
        self,
        code: Dict[str, str],
        ir: ApplicationIR
    ) -> ValidationResult:
        """Validate both syntax and IR compliance."""
        per_file_results = []

        for file_path, content in code.items():
            per_file_results.append({
                "file": file_path,
                "syntax": self.syntax_checker.check(content),
                "imports": self.import_checker.check(content, code),
            })

        # IR compliance at system level (use existing ComplianceValidator)
        ir_result = self.ir_compliance_checker.validate_full(code, ir)

        # NOTE: Threshold is configurable via COGNITIVE_PASS_ROLLBACK_THRESHOLD
        # Aligns with QUALITY_GATE_ENV settings (dev/prod)
        threshold = float(os.getenv("COGNITIVE_PASS_ROLLBACK_THRESHOLD", "0.95"))

        return ValidationResult(
            files=per_file_results,
            ir_compliance=ir_result,
            all_passed=ir_result.semantic_compliance >= threshold
        )
```

### Pass 4: Runtime Pass (Existing Smoke Test)

```python
# UNCHANGED - Keep existing SmokeRepairOrchestrator
# But now it stores patterns for Pass 2 of next run
```

---

## Rollback Policy

### Hard Rollback Triggers (Entire CognitivePass)

| Trigger | Action |
|---------|--------|
| IR semantic compliance drops below baseline | Rollback all cognitive changes |
| Syntax errors introduced | Rollback all cognitive changes |
| >3 functions fail validation | Rollback all cognitive changes |

### Granular Rollback (Per-Function)

| Trigger | Action |
|---------|--------|
| Function violates IR contract | Revert that function only |
| Function breaks more tests | Revert that function only |
| IR compliance for flow decreases | Revert that function only |

### Cognitive Regression Recording

When enhancement fails, record as learning:

```python
@dataclass
class CognitiveRegressionPattern:
    """Records failed enhancement attempts for future avoidance."""
    ir_flow: str                    # Flow that was enhanced
    anti_patterns_applied: List[str] # Patterns that were applied
    result: str                      # "ir_contract_violation", "test_regression"
    violations: List[str]            # Specific violations
    timestamp: datetime
```

---

## Caching Strategy

### Cache Key (IR-Based, Not Code-Based)

```python
cache_key = hash(
    ir_flow.flow_id,
    ir_flow.version,
    sorted(anti_pattern_ids),
    cognitive_pass_version
)
```

### Cache Invalidation

- When IR flow definition changes → Invalidate
- When anti-patterns are updated → Invalidate
- When cognitive pass version changes → Invalidate
- When pattern is promoted to template → Invalidate

---

## Metrics: Measuring "Errors Prevented"

### Operational Definition

```python
# For each spec and pipeline version:
baseline_smoke_failures = smoke_failures_without_cognitive_pass
cognitive_smoke_failures = smoke_failures_with_cognitive_pass

errors_prevented = max(0, baseline_smoke_failures - cognitive_smoke_failures)
prevention_rate = errors_prevented / max(1, baseline_smoke_failures)
```

### Aggregation Dimensions

| Dimension | Example |
|-----------|---------|
| By Flow | "checkout prevented 45% of errors" |
| By Constraint Type | "stock_constraint prevented 60% of errors" |
| By Entity | "Cart-related errors reduced 50%" |
| By Exception Type | "AttributeError reduced 70%" |

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| First smoke pass rate | 65-70% | 85-90% |
| Repair iterations needed | 2-3 | 0-1 |
| Patterns actually used | 0% | 100% |
| Prevention rate | 0% | 50%+ |
| Cognitive regressions | N/A | <5% of enhancements |

---

## Integration Point: CognitiveCodeGenerationService

```python
class CognitiveCodeGenerationService:
    """
    Multi-pass cognitive code generation.
    """

    def __init__(self):
        self.template_pass = TemplatePass()
        self.cognitive_pass = IRCentricCognitivePass()
        self.validation_pass = ValidationPass()

    async def generate(
        self,
        ir: ApplicationIR,
        enable_cognitive: bool = True,
        baseline_mode: bool = False  # For A/B comparison
    ) -> GenerationResult:
        """Generate code using multi-pass cognitive pipeline."""

        # Pass 1: Template generation
        logger.info("Pass 1: Template generation...")
        base_code = await self.template_pass.generate(ir)

        # Store baseline for comparison
        if baseline_mode:
            return GenerationResult(files=base_code, cognitive_enabled=False)

        # Pass 2: Cognitive enhancement
        cognitive_files = 0
        if enable_cognitive:
            logger.info("Pass 2: Cognitive enhancement (IR-Centric)...")
            enhanced_code = await self.cognitive_pass.enhance(base_code, ir)
            cognitive_files = len([
                f for f in enhanced_code
                if enhanced_code[f] != base_code.get(f)
            ])
            logger.info(f"  Cognitively enhanced {cognitive_files} functions")
        else:
            enhanced_code = base_code

        # Pass 3: Validation (static + IR)
        logger.info("Pass 3: Static + IR validation...")
        validation = self.validation_pass.validate(enhanced_code, ir)

        # Rollback if validation fails
        if not validation.all_passed:
            logger.warning(f"Validation failed, rolling back cognitive changes")
            enhanced_code = base_code
            cognitive_files = 0

        return GenerationResult(
            files=enhanced_code,
            validation=validation,
            cognitive_enabled=enable_cognitive,
            metadata={
                "template_files": len(base_code),
                "cognitive_files": cognitive_files,
                "ir_compliance": validation.ir_compliance.score,
            }
        )
```

---

## NegativePatternStore: New Methods Required

```python
# Methods needed for IR-Centric cognitive pass
class NegativePatternStore:
    # Existing
    def get_patterns_for_entity(entity_name, min_occurrences) -> List[Pattern]: ...
    def get_patterns_by_exception(exception_class, min_occurrences) -> List[Pattern]: ...

    # NEW - Required for IR-Centric
    def get_patterns_for_flow(flow_name, min_occurrences) -> List[Pattern]: ...
    def get_patterns_for_constraint_type(constraint_type, min_occurrences) -> List[Pattern]: ...
    def get_patterns_for_relationship(from_entity, to_entity, rel_type) -> List[Pattern]: ...
    def store_cognitive_regression(regression: CognitiveRegressionPattern) -> None: ...
```

---

## Implementation Plan

### Phase 1: Infrastructure

1. Add `IRFlow` to ApplicationIR (or extract from existing features)
2. Implement `get_patterns_for_flow()` in NegativePatternStore
3. Implement `get_patterns_for_constraint_type()` in NegativePatternStore
4. Create `CognitiveCache` with IR-based keys

### Phase 2: Core Implementation

1. Create `IRCentricCognitivePass` class
2. Implement function-level extraction with AST
3. Implement IR Guard prompt generation
4. Wire to existing `IRComplianceValidator`

### Phase 3: Integration

1. Create `CognitiveCodeGenerationService`
2. Add feature flag `ENABLE_COGNITIVE_PASS`
3. Add baseline comparison mode
4. Integrate metrics collection

### Phase 4: Optimization

1. Profile token usage
2. Tune cache TTL
3. Add parallel function processing
4. Tune rollback thresholds

---

## Non-Functional Requirements

1. **Determinism**: Same IR + patterns → same output (modulo LLM variance)
2. **Reproducibility**: Log all inputs for debugging
3. **IR Inviolability**: IR contract can NEVER be violated
4. **Graceful Degradation**: If cognitive pass fails, use template output
5. **Observability**: Log all enhancements, rollbacks, cache hits

---

## Feature Flags

```python
COGNITIVE_PASS_ENABLED = True      # Master switch
COGNITIVE_PASS_CACHE_ENABLED = True # Enable caching
COGNITIVE_PASS_MAX_FUNCTIONS = 20   # Max functions per run
COGNITIVE_PASS_ROLLBACK_THRESHOLD = 0.95  # Min IR compliance
```

---

## Open Questions Resolved

| Question | Answer |
|----------|--------|
| File vs Function granularity? | **Function** - maps to IRFlow semantic unit |
| How to cache? | **IR-based key**: `hash(flow_id, version, pattern_ids)` |
| What if cognitive introduces bugs? | **Rollback + record as CognitiveRegressionPattern** |
| How to measure prevention? | **A/B comparison**: baseline vs cognitive mode |

---

## Baseline Mode Clarification

**Important:** Baseline mode does NOT run cognitive enhancement and validation in the same process.

```python
# Baseline mode returns template code ONLY
if baseline_mode:
    return GenerationResult(files=base_code, cognitive_enabled=False)
```

**A/B Comparison Strategy:**

| Run Type | Cognitive Pass | Smoke Tests | Purpose |
|----------|---------------|-------------|---------|
| Baseline Run | OFF | YES | Measure unenhanced failure rate |
| Cognitive Run | ON | YES | Measure enhanced failure rate |

**Metrics collection:**

- Baseline metrics obtained from dedicated runs with `ENABLE_COGNITIVE_PASS=false`
- Cognitive metrics obtained from runs with `ENABLE_COGNITIVE_PASS=true`
- Prevention rate = `(baseline_failures - cognitive_failures) / baseline_failures`

**Why separate runs?**

1. Avoids confounding variables in same-process comparison
2. Enables clean A/B testing with identical specs
3. Simplifies debugging and attribution of failures
4. Allows parallel execution of both runs for faster feedback

---

## Concurrency & Thread Safety

### CognitiveCache Thread Safety

```python
class CognitiveCache:
    """
    Thread/Async Safety Notes:

    Current Implementation (v1):
    - In-memory dict is NOT thread-safe for concurrent writes
    - Safe for single-threaded async (one event loop)
    - File persistence uses simple write (no locking)

    Production Hardening (v2 roadmap):
    - Use threading.Lock for dict operations
    - Use asyncio.Lock for async contexts
    - Consider redis/memcached for distributed caching
    """

    def __init__(self):
        self._cache: Dict[str, CachedEnhancement] = {}
        self._lock = threading.Lock()  # v2: Add for thread safety

    def get(self, key: str) -> Optional[CachedEnhancement]:
        with self._lock:  # v2: Thread-safe read
            return self._cache.get(key)
```

### Async Enhancement Parallelization

```python
# Current: Sequential function processing
for flow_fn in flow_functions:
    result = await self._enhance_function(flow_fn)

# v2 Roadmap: Parallel with semaphore control
async def enhance_parallel(self, flow_functions: List[FlowFunction]):
    semaphore = asyncio.Semaphore(self.max_concurrent)

    async def bounded_enhance(fn):
        async with semaphore:
            return await self._enhance_function(fn)

    return await asyncio.gather(*[
        bounded_enhance(fn) for fn in flow_functions
    ])
```

### Recommendations

| Scenario | Strategy |
|----------|----------|
| Single E2E run | Current impl safe (single async context) |
| Parallel E2E runs | Use separate cache instances per run |
| Production multi-tenant | Add explicit locking or use Redis |
| High-volume testing | Implement connection pooling for LLM client |

---

## Compatibility with Existing Components

### Integration Points

| Component | Integration | Changes Required |
|-----------|------------|------------------|
| `ProductionCodeGenerators` | Pass 1 (Template) | None - used as-is |
| `PatternBank` | Pass 1 (Template) | None - used as-is |
| `IRComplianceValidator` | Pass 2-3 (Validation) | None - reused existing |
| `SmokeRepairOrchestrator` | Pass 4 (Runtime) | None - stores patterns for next run |
| `NegativePatternStore` | Pass 2 (Pattern fetch) | Added 4 new methods |
| `OrchestratorAgent` | Pipeline coordination | Add cognitive pass toggle |

### Import Graph

```text
OrchestratorAgent
    └── CognitiveCodeGenerationService
            ├── IRCentricCognitivePass
            │       ├── NegativePatternStore (existing + new methods)
            │       ├── CognitiveCache (NEW)
            │       └── IRComplianceValidator (existing)
            └── ValidationPass
                    └── IRComplianceValidator (existing)
```

### Migration Path

1. **Phase 1**: Deploy with `ENABLE_COGNITIVE_PASS=false` (no behavior change)
2. **Phase 2**: Enable for specific specs via config
3. **Phase 3**: A/B testing with baseline comparisons
4. **Phase 4**: Full rollout with monitoring

---

## Failure Modes & Graceful Degradation

### Failure Hierarchy

| Level | Failure | Recovery | Impact |
|-------|---------|----------|--------|
| L1 | Single function enhancement fails | Use template code for that function | Minimal |
| L2 | IR validation rejects enhancement | Rollback to template, log regression | Minimal |
| L3 | LLM API timeout/error | Skip cognitive pass, use template | Medium |
| L4 | Cache corruption | Clear cache, continue without | Low |
| L5 | Pattern store unavailable | Skip pattern fetch, use empty list | Medium |
| L6 | AST parsing fails | Skip file enhancement | Low |

### Graceful Degradation Strategy

```python
async def enhance_with_fallback(self, flow_fn: FlowFunction) -> str:
    """Enhancement with multi-level fallback."""
    try:
        # Try full cognitive enhancement
        enhanced = await self._cognitive_enhance_function(flow_fn)

        # Validate against IR
        if self._validate_against_ir(enhanced, flow_fn.ir_flow):
            return enhanced
        else:
            logger.warning(f"IR validation failed, using template")
            return flow_fn.function_code

    except LLMAPIError as e:
        logger.error(f"LLM API error: {e}, falling back to template")
        return flow_fn.function_code

    except Exception as e:
        logger.error(f"Unexpected error: {e}, falling back to template")
        return flow_fn.function_code
```

### Circuit Breaker Pattern

```python
class CognitiveCircuitBreaker:
    """Disable cognitive pass after repeated failures."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 300):
        self.failures = 0
        self.threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "open"
            logger.warning("Circuit breaker OPEN - cognitive pass disabled")

    def should_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open: try once
```

---

## Configuration & Observability

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_COGNITIVE_PASS` | `true` | Master switch for cognitive enhancement |
| `COGNITIVE_BASELINE_MODE` | `false` | Return template code only (for A/B) |
| `COGNITIVE_PASS_ROLLBACK_THRESHOLD` | `0.95` | Min IR compliance to accept enhancement |
| `COGNITIVE_CACHE_TTL_HOURS` | `24` | Cache entry time-to-live |
| `COGNITIVE_MAX_PATTERNS` | `5` | Max patterns per function enhancement |
| `COGNITIVE_MAX_FUNCTIONS` | `20` | Max functions to enhance per file |
| `COGNITIVE_LLM_TIMEOUT` | `30` | LLM API timeout in seconds |
| `COGNITIVE_CIRCUIT_BREAKER_THRESHOLD` | `5` | Failures before disabling pass |

### Structured Logging

```python
# Enhancement attempt
logger.info(
    "cognitive_enhancement_attempt",
    extra={
        "flow_id": flow.flow_id,
        "function": func_name,
        "patterns_count": len(patterns),
        "cache_hit": cache_hit,
    }
)

# Enhancement result
logger.info(
    "cognitive_enhancement_result",
    extra={
        "flow_id": flow.flow_id,
        "function": func_name,
        "success": validation.passed,
        "ir_compliance": validation.score,
        "tokens_used": tokens,
        "duration_ms": duration,
    }
)

# Rollback event
logger.warning(
    "cognitive_enhancement_rollback",
    extra={
        "flow_id": flow.flow_id,
        "function": func_name,
        "reason": "ir_contract_violation",
        "violations": violations,
    }
)
```

### Metrics Export

```python
@dataclass
class CognitiveMetricsExport:
    """Metrics for observability dashboards."""

    # Counters
    total_enhancements_attempted: int
    total_enhancements_successful: int
    total_enhancements_rolled_back: int
    total_cache_hits: int
    total_cache_misses: int

    # Gauges
    current_cache_size: int
    current_patterns_loaded: int

    # Histograms
    enhancement_duration_ms: List[float]
    tokens_per_enhancement: List[int]
    ir_compliance_scores: List[float]

    # Rates (calculated)
    @property
    def success_rate(self) -> float:
        if self.total_enhancements_attempted == 0:
            return 0.0
        return self.total_enhancements_successful / self.total_enhancements_attempted

    @property
    def cache_hit_rate(self) -> float:
        total = self.total_cache_hits + self.total_cache_misses
        if total == 0:
            return 0.0
        return self.total_cache_hits / total

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        return f"""
# HELP cognitive_enhancements_total Total enhancement attempts
# TYPE cognitive_enhancements_total counter
cognitive_enhancements_total{{status="attempted"}} {self.total_enhancements_attempted}
cognitive_enhancements_total{{status="successful"}} {self.total_enhancements_successful}
cognitive_enhancements_total{{status="rolled_back"}} {self.total_enhancements_rolled_back}

# HELP cognitive_cache_operations Cache operations
# TYPE cognitive_cache_operations counter
cognitive_cache_operations{{type="hit"}} {self.total_cache_hits}
cognitive_cache_operations{{type="miss"}} {self.total_cache_misses}

# HELP cognitive_success_rate Enhancement success rate
# TYPE cognitive_success_rate gauge
cognitive_success_rate {self.success_rate:.4f}
"""
```

### Health Check Endpoint

```python
@router.get("/health/cognitive")
async def cognitive_health():
    """Health check for cognitive code generation."""
    service = get_cognitive_service()

    return {
        "status": "healthy" if service.is_enabled() else "disabled",
        "enabled": service.is_enabled(),
        "cache_size": len(service._cache),
        "patterns_loaded": len(service._pattern_store),
        "metrics": service.get_metrics_dict(),
        "circuit_breaker": service._circuit_breaker.state,
    }
```

---

*Document created: 2025-11-30*
*Updated: 2025-11-30 v2.0 - IR-Centric refinements*
*Updated: 2025-11-30 v2.1 - RFC hardening: Baseline mode, Concurrency, Compatibility, Failure modes, Observability*
*For: DevMatrix Cognitive Compiler Architecture*
