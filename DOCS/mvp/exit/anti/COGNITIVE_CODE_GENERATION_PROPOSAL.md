# Cognitive Code Generation - Architectural Proposal

**Status:** Draft v2.0
**Author:** DevMatrix Architecture
**Date:** 2025-11-30
**Architecture:** **IR-Centric** (IR is source of truth, constrains all operations)

---

## 📊 Implementation Progress Tracker

| Phase | Task | Status | File/Location | Notes |
|-------|------|--------|---------------|-------|
| **1. Infrastructure** | | | | |
| 1.1 | Add `IRFlow` to BehaviorModelIR | ⏳ Pending | `src/cognitive/ir/behavior_model.py` | Extended Flow model |
| 1.2 | `get_patterns_for_flow()` in NegativePatternStore | ⏳ Pending | `src/learning/negative_pattern_store.py` | New query method |
| 1.3 | `get_patterns_for_constraint_type()` | ⏳ Pending | `src/learning/negative_pattern_store.py` | New query method |
| 1.4 | `store_cognitive_regression()` | ⏳ Pending | `src/learning/negative_pattern_store.py` | New store method |
| 1.5 | Create `CognitiveCache` class | ⏳ Pending | `src/cognitive/cache/cognitive_cache.py` | IR-based keys |
| **2. Core Implementation** | | | | |
| 2.1 | Create `IRCentricCognitivePass` class | ⏳ Pending | `src/cognitive/passes/ir_centric_cognitive_pass.py` | Main cognitive pass |
| 2.2 | Implement function-level AST extraction | ⏳ Pending | Same file | `_extract_flow_functions()` |
| 2.3 | Implement IR Guard prompt generation | ⏳ Pending | Same file | `_build_ir_guard()` |
| 2.4 | Wire to `IRComplianceValidator` | ⏳ Pending | Same file | Reuse existing validator |
| **3. Integration** | | | | |
| 3.1 | Create `CognitiveCodeGenerationService` | ⏳ Pending | `src/services/cognitive_code_generation_service.py` | Wrapper service |
| 3.2 | Add feature flag `ENABLE_COGNITIVE_PASS` | ⏳ Pending | Config/env | Master switch |
| 3.3 | Add baseline comparison mode | ⏳ Pending | Service | A/B testing |
| 3.4 | Integrate metrics collection | ⏳ Pending | Service | Prevention rate |
| **4. Optimization** | | | | |
| 4.1 | Profile token usage | ⏳ Pending | - | Analysis |
| 4.2 | Tune cache TTL | ⏳ Pending | `CognitiveCache` | Performance |
| 4.3 | Add parallel function processing | ⏳ Pending | `IRCentricCognitivePass` | Async batching |
| 4.4 | Tune rollback thresholds | ⏳ Pending | Config | Safety tuning |

**Legend:** ✅ Done | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Last Updated:** 2025-11-30

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
    primary_entity: str             # Main entity (Cart)
    entities_involved: List[str]    # All entities (Cart, Product, CartItem)
    constraint_types: List[str]     # stock_constraint, workflow_constraint
    preconditions: List[str]        # cart.open, product.exists, qty > 0
    postconditions: List[str]       # cart_item added, stock decreased
    endpoint: str                   # POST /carts/{id}/items
    implementation_name: str        # Function name in code

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
        """Replace function in file with enhanced version."""
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

        return ValidationResult(
            files=per_file_results,
            ir_compliance=ir_result,
            all_passed=ir_result.semantic_compliance >= 0.95
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

*Document created: 2025-11-30*
*Updated: 2025-11-30 v2.0 - IR-Centric refinements*
*For: DevMatrix Cognitive Compiler Architecture*
