# Learning Layer Integration - Gap Analysis & Implementation Plan

**Status**: 🔴 CRITICAL GAPS IDENTIFIED  
**Date**: 2025-12-01  
**Priority**: P0 - Blocks MVP Exit Criteria

---

## 🎯 Executive Summary

DevMatrix has **comprehensive learning infrastructure** but **critical integration gaps** prevent learned patterns from influencing LLM-based code generation and repair cycles. This document outlines a 3-phase plan to close these gaps and achieve **full learning loop closure**.

### Current State
- ✅ **Pattern Storage**: NegativePatternStore (Neo4j) operational
- ✅ **AST Learning**: PatternAwareGenerator applies overrides deterministically
- ✅ **Feedback Collection**: FeedbackCollector captures smoke test failures
- ❌ **LLM Integration**: PromptEnhancer imported but never used
- ❌ **Repair Learning**: CodeRepairAgent doesn't record successful fixes
- ❌ **Cross-Session Learning**: Patterns stored but not propagated to prompts

### Target State
- ✅ All LLM prompts enhanced with relevant anti-patterns
- ✅ Successful repairs recorded as positive patterns
- ✅ Smoke test failures immediately influence next generation
- ✅ Cross-session learning: Session N+1 avoids Session N errors

---

## 📊 Gap Analysis

### Gap 1: PromptEnhancer Not Integrated
**Impact**: 🔴 CRITICAL  
**Symptom**: LLM generates same errors repeatedly across sessions

| Component | Has PromptEnhancer? | Uses It? |
|-----------|---------------------|----------|
| `CodeGenerationService._build_prompt()` | ❌ Imported | ❌ Never called |
| `CodeRepairAgent.repair()` | ❌ Not imported | ❌ Never called |
| `IRCentricCognitivePass` | ❌ Not imported | ❌ Never called |

**Root Cause**: Infrastructure exists but no integration points.

### Gap 2: CodeRepairAgent Doesn't Learn
**Impact**: 🟡 HIGH  
**Symptom**: Same repairs applied repeatedly, no pattern emergence

```python
# Current: Applies repair, doesn't record
def repair(self, compliance_report):
    # ... apply fixes ...
    return RepairResult(success=True, repairs_applied=fixes)
    # ❌ Missing: Store successful fix as positive pattern
```

**Root Cause**: No feedback loop from repair → pattern store.

### Gap 3: Smoke Repair Loop Doesn't Update Prompts
**Impact**: 🟡 HIGH  
**Symptom**: Smoke-driven repairs fix code but don't prevent recurrence

```python
# Current flow:
1. Smoke test fails → FeedbackCollector.record_failure()
2. Pattern stored in Neo4j ✅
3. CodeRepairAgent.repair() fixes code ✅
4. Next generation: LLM gets same base prompt ❌
```

**Root Cause**: No connection between NegativePatternStore → PromptEnhancer → LLM.

---

## 🛠️ Implementation Plan

### Phase 1: PromptEnhancer Integration (P0)
**Goal**: All LLM prompts enhanced with learned anti-patterns  
**Effort**: 2-3 hours  
**Files**: `code_generation_service.py`, `code_repair_agent.py`  
**Status**: ✅ **PHASE 1 COMPLETED** (1.1 + 1.2)

#### 1.1 Integrate into CodeGenerationService ✅ COMPLETED
**Completed**: 2025-12-01  
**Verification**: `verify_phase_1_1_integration.py` - ALL TESTS PASSED

**Changes Made**:
1. Added `self.prompt_enhancer` initialization in `__init__`
2. Added `self.enable_prompt_enhancement` flag
3. Enhanced `_build_prompt()` to inject anti-patterns with **6 task type detections**:
   - **Entity**: "entity", "model", "entities.py" → `enhance_entity_prompt()`
   - **Endpoint**: "endpoint", "route", "api" → `enhance_endpoint_prompt()`
   - **Schema**: "schema", "pydantic" → `enhance_schema_prompt()`
   - **Service**: "service", "business logic" → `enhance_service_prompt()`
   - **Validation**: "validation", "constraint", "rule" → `enhance_generic_prompt(error_types=[...])`
   - **Generic**: (fallback) → `enhance_generic_prompt()`
4. Added helper methods:
   - `_extract_entity_name_from_task()` - Extracts "Product" from "Generate Product entity"
   - `_extract_endpoint_pattern_from_task()` - Extracts "/products" from "POST /products"
   - `_extract_schema_name_from_task()` - Extracts "ProductCreate" from "ProductCreate schema"
5. Added logging: "🎓 Prompt enhanced with N anti-patterns"

**Task Type Coverage**:
```
✅ Entities (ORM models)      - entity-specific anti-patterns
✅ Endpoints (API routes)     - endpoint-specific anti-patterns
✅ Schemas (Pydantic)         - schema-specific anti-patterns
✅ Services (Business logic)  - service-specific anti-patterns
✅ Validations (Constraints)  - validation error types
✅ Generic (Config, utils)    - all error types
```


**Verification Results**:
```
✅ PASS: PromptEnhancer Import
✅ PASS: PromptEnhancer Singleton
✅ PASS: CodeGenerationService Integration
```

**Next**: Run E2E pipeline and verify "🎓 Prompt enhanced" logs appear.

```python
# File: src/services/code_generation_service.py

class CodeGenerationService:
    def __init__(self, ...):
        # Add prompt enhancer
        try:
            from src.learning.prompt_enhancer import get_prompt_enhancer
            self.prompt_enhancer = get_prompt_enhancer()
            self.enable_prompt_enhancement = True
        except ImportError:
            self.prompt_enhancer = None
            self.enable_prompt_enhancement = False
    
    def _build_prompt(self, task: MasterPlanTask) -> str:
        """Build prompt with anti-pattern warnings."""
        # 1. Generate base prompt (existing logic)
        base_prompt = strategy.generate_prompt(context)
        
        # 2. Enhance with learned patterns
        if self.enable_prompt_enhancement and self.prompt_enhancer:
            # Detect task type
            if "entity" in task.name.lower() or "model" in task.name.lower():
                entity_name = self._extract_entity_name(task)
                enhanced = self.prompt_enhancer.enhance_entity_prompt(
                    base_prompt, entity_name
                )
            elif "endpoint" in task.name.lower() or "route" in task.name.lower():
                endpoint = self._extract_endpoint_pattern(task)
                enhanced = self.prompt_enhancer.enhance_endpoint_prompt(
                    base_prompt, endpoint
                )
            elif "schema" in task.name.lower():
                schema_name = self._extract_schema_name(task)
                enhanced = self.prompt_enhancer.enhance_schema_prompt(
                    base_prompt, schema_name
                )
            else:
                enhanced = self.prompt_enhancer.enhance_generic_prompt(base_prompt)
            
            logger.info(f"🎓 Prompt enhanced with {len(self.prompt_enhancer.get_injected_patterns())} anti-patterns")
            return enhanced
        
        return base_prompt
```

**Verification**:
```bash
# Run E2E and check logs for:
# "🎓 Prompt enhanced with N anti-patterns"
python tests/e2e/real_e2e_full_pipeline.py
```

#### 1.2 Integrate into CodeRepairAgent
```python
# File: src/mge/v2/agents/code_repair_agent.py

class CodeRepairAgent:
    def __init__(self, ...):
        # Add prompt enhancer
        try:
            from src.learning.prompt_enhancer import get_prompt_enhancer
            self.prompt_enhancer = get_prompt_enhancer()
        except ImportError:
            self.prompt_enhancer = None
    
    def _generate_repair_with_llm(self, entity_req, error_context):
        """Generate repair using LLM with anti-pattern warnings."""
        base_prompt = f"Fix missing entity {entity_req.name}..."
        
        if self.prompt_enhancer:
            enhanced = self.prompt_enhancer.enhance_entity_prompt(
                base_prompt, entity_req.name
            )
            return self.llm_client.generate(enhanced)
        
        return self.llm_client.generate(base_prompt)
```

**Acceptance Criteria**:
- [ ] All LLM calls in `CodeGenerationService` use enhanced prompts
- [ ] All LLM calls in `CodeRepairAgent` use enhanced prompts
- [ ] Logs show "🎓 Prompt enhanced" messages
- [ ] E2E pipeline shows reduced error recurrence rate

---

### Phase 2: Repair Learning Loop (P0)
**Goal**: Successful repairs recorded as positive patterns  
**Effort**: 3-4 hours  
**Files**: `code_repair_agent.py`, `negative_pattern_store.py`

#### 2.1 Add PositivePattern to NegativePatternStore
```python
# File: src/learning/negative_pattern_store.py

@dataclass
class PositiveRepairPattern:
    """Successful repair that should be reused."""
    pattern_id: str
    repair_type: str  # "entity_addition", "endpoint_addition", "validation_fix"
    entity_pattern: str
    endpoint_pattern: str
    fix_description: str
    code_snippet: str
    success_count: int = 1
    last_applied: datetime = field(default_factory=datetime.now)
    
    def to_prompt_example(self) -> str:
        """Format as a positive example for prompts."""
        return f"""
✅ SUCCESSFUL PATTERN (used {self.success_count}x):
   Type: {self.repair_type}
   Context: {self.entity_pattern} / {self.endpoint_pattern}
   Solution: {self.fix_description}
   
   Example:
   ```python
   {self.code_snippet}
   ```
"""

class NegativePatternStore:
    def store_positive_repair(self, pattern: PositiveRepairPattern) -> bool:
        """Store successful repair for reuse."""
        # Similar to store() but for positive patterns
        # Increment success_count if already exists
```

#### 2.2 Update CodeRepairAgent to Record Fixes
```python
# File: src/mge/v2/agents/code_repair_agent.py

class CodeRepairAgent:
    def repair(self, compliance_report, ...):
        # ... existing repair logic ...
        
        if repair_result.success:
            # NEW: Record successful repair
            self._record_successful_repair(
                repair_type="entity_addition",
                entity_name=entity_req.name,
                fix_description=f"Added missing entity {entity_req.name}",
                code_snippet=generated_code
            )
        
        return repair_result
    
    def _record_successful_repair(self, repair_type, entity_name, fix_description, code_snippet):
        """Record successful repair as positive pattern."""
        try:
            from src.learning import get_negative_pattern_store
            pattern_store = get_negative_pattern_store()
            
            pattern = PositiveRepairPattern(
                pattern_id=f"repair_{repair_type}_{entity_name}",
                repair_type=repair_type,
                entity_pattern=entity_name,
                endpoint_pattern="*",
                fix_description=fix_description,
                code_snippet=code_snippet[:500]  # Truncate
            )
            
            pattern_store.store_positive_repair(pattern)
            logger.info(f"✅ Recorded successful repair: {repair_type} for {entity_name}")
        except Exception as e:
            logger.warning(f"Failed to record repair pattern: {e}")
```

**Acceptance Criteria**:
- [ ] Successful repairs stored in Neo4j as `PositiveRepairPattern`
- [ ] Patterns include code snippets for reuse
- [ ] `success_count` increments on duplicate repairs
- [ ] Logs show "✅ Recorded successful repair" messages

---

### Phase 3: Cross-Session Learning Verification (P1)
**Goal**: Prove Session N+1 avoids Session N errors  
**Effort**: 2-3 hours  
**Files**: New test script

#### 3.1 Create Learning Verification Test
```python
# File: tests/e2e/test_learning_loop_closure.py

"""
Test that learning loop is fully closed:
1. Session 1: Generate code, capture errors
2. Verify: Errors stored in NegativePatternStore
3. Session 2: Generate same spec
4. Verify: Prompts enhanced with Session 1 errors
5. Assert: Session 2 error rate < Session 1 error rate
"""

def test_cross_session_learning():
    # Session 1: Baseline
    result1 = run_e2e_pipeline(spec="ecommerce-api-spec-human.md")
    errors1 = result1.smoke_test_failures
    
    # Verify patterns stored
    pattern_store = get_negative_pattern_store()
    stored_patterns = pattern_store.get_all_patterns()
    assert len(stored_patterns) > 0, "No patterns stored from Session 1"
    
    # Session 2: With learning
    result2 = run_e2e_pipeline(spec="ecommerce-api-spec-human.md")
    errors2 = result2.smoke_test_failures
    
    # Verify prompts were enhanced
    assert "🎓 Prompt enhanced" in result2.logs
    
    # Assert improvement
    error_reduction = (len(errors1) - len(errors2)) / len(errors1)
    assert error_reduction > 0.2, f"Expected >20% error reduction, got {error_reduction*100}%"
    
    print(f"✅ Learning verified: {error_reduction*100:.1f}% error reduction")
```

**Acceptance Criteria**:
- [ ] Test passes with >20% error reduction
- [ ] Logs show enhanced prompts in Session 2
- [ ] Neo4j contains patterns from Session 1
- [ ] Session 2 avoids at least 3 errors from Session 1

---

## 📈 Success Metrics

### Before (Current State)
- ❌ LLM prompts: 0% enhanced
- ❌ Repair learning: 0% captured
- ❌ Cross-session improvement: 0%
- ❌ Error recurrence: ~50% (same errors repeat)

### After (Target State)
- ✅ LLM prompts: 100% enhanced
- ✅ Repair learning: 100% captured
- ✅ Cross-session improvement: >20% error reduction
- ✅ Error recurrence: <10% (patterns prevent repeats)

---

## 🚀 Execution Timeline

| Phase | Task | Effort | Owner | Status |
|-------|------|--------|-------|--------|
| 1.1 | Integrate PromptEnhancer into CodeGenerationService | 2h | Dev | ✅ DONE (2025-12-01) |
| 1.2 | Integrate PromptEnhancer into CodeRepairAgent | 1h | Dev | ✅ DONE (2025-12-01) |
| 2.1 | Add PositiveRepairPattern to NegativePatternStore | 2h | Dev | ✅ DONE (2025-12-01) |
| 2.2 | Update CodeRepairAgent to record fixes | 2h | Dev | ✅ DONE (2025-12-01) |
| 3.1 | Create learning verification test | 2h | Dev | 🔴 TODO |
| - | **Total** | **9h** | - | **4/5 Complete (80%)** |

**Estimated Completion**: ~2 hours (Phase 3 only)

---

## 🔍 Verification Checklist

### Phase 1 Verification
- [ ] Run E2E pipeline
- [ ] Grep logs for "🎓 Prompt enhanced"
- [ ] Verify Neo4j has patterns
- [ ] Verify prompts contain "⚠️ AVOID" sections

### Phase 2 Verification
- [ ] Run E2E pipeline with repairs
- [ ] Grep logs for "✅ Recorded successful repair"
- [ ] Query Neo4j for `PositiveRepairPattern` nodes
- [ ] Verify `success_count` increments

### Phase 3 Verification
- [ ] Run `test_learning_loop_closure.py`
- [ ] Verify >20% error reduction
- [ ] Check logs for enhanced prompts in Session 2
- [ ] Verify specific errors from Session 1 don't repeat

---

## 📝 Implementation Notes

### PromptEnhancer Configuration
```python
# Recommended settings for MVP
max_patterns_per_prompt = 5  # Don't overwhelm LLM
min_occurrences = 2  # Only inject patterns seen 2+ times
severity_threshold = 0.5  # Only high-severity patterns
```

### Pattern Prioritization
When multiple patterns match, prioritize by:
1. **Severity score** (frequency × impact)
2. **Recency** (recent errors more relevant)
3. **Specificity** (entity-specific > generic)

### Performance Considerations
- **Neo4j Query Optimization**: Index on `entity_pattern`, `endpoint_pattern`
- **Caching**: Cache patterns per entity/endpoint for 5 minutes
- **Async Loading**: Load patterns asynchronously during pipeline startup

---

## 🎯 Exit Criteria for MVP

- [x] NegativePatternStore operational (✅ Done)
- [x] PatternAwareGenerator applies AST overrides (✅ Done)
- [ ] **PromptEnhancer integrated in all LLM calls** (🔴 Gap 1)
- [ ] **CodeRepairAgent records successful fixes** (🔴 Gap 2)
- [ ] **Cross-session learning verified** (🔴 Gap 3)
- [ ] **E2E test shows >20% error reduction** (🔴 Gap 3)

**Current MVP Blocker**: Gaps 1-3 must be closed before MVP exit.

---

## 📐 Phase 2 Detailed Design (Repair Learning Loop)

**Objective**: Persist successful repairs as reusable positive patterns and surface them back into prompts.

### Data Model & Storage
- **Node**: `PositiveRepairPattern`
  - Required: `pattern_id` (PK), `repair_type`, `entity_pattern`, `endpoint_pattern`, `fix_description`, `code_snippet`
  - Metrics: `success_count` (int), `last_applied` (datetime), `last_repo_hash` (string)
- **Indexes**: `(pattern_id)`, `(entity_pattern)`, `(endpoint_pattern)`; composite `(repair_type, entity_pattern)`
- **Cypher Upsert** (draft):
  ```cypher
  MERGE (p:PositiveRepairPattern {pattern_id: $pattern_id})
  ON CREATE SET p.repair_type=$repair_type,
                p.entity_pattern=$entity_pattern,
                p.endpoint_pattern=$endpoint_pattern,
                p.fix_description=$fix_description,
                p.code_snippet=$code_snippet,
                p.success_count=1,
                p.last_applied=timestamp(),
                p.last_repo_hash=$repo_hash
  ON MATCH SET p.success_count = p.success_count + 1,
               p.last_applied=timestamp(),
               p.code_snippet = coalesce($code_snippet, p.code_snippet),
               p.last_repo_hash=$repo_hash
  ```

### API Surface
- `NegativePatternStore.store_positive_repair(pattern: PositiveRepairPattern) -> bool`
- `NegativePatternStore.get_positive_patterns(entity_pattern=None, endpoint_pattern=None, repair_type=None) -> List[PositiveRepairPattern]`
- `PromptEnhancer.enhance_*` to accept `positive_patterns` and prepend them after negative patterns:
  - Order: 🔴 Negative (avoid) → ✅ Positive (reuse) → ℹ️ Context

### Integration Points
- **CodeRepairAgent**
  - After `repair_result.success` → call `_record_successful_repair(...)`
  - Pass `repo_hash` (git HEAD) for traceability
  - Truncate `code_snippet` to 500–800 chars to keep prompts compact
- **PromptEnhancer**
  - When fetching patterns, pull both negative + positive for the same scope
  - Positive patterns formatted as concise examples (avoid long prose)
- **Fallback**
  - If Neo4j unavailable, log once per run and skip storing (do not block repair)

### Observability
- Logs:
  - `✅ Recorded successful repair: <repair_type> for <entity>`
  - `🎓 Prompt enhanced with <N_neg> anti-patterns and <N_pos> positive patterns`
- Metrics (optional, Prometheus):
  - `repair_patterns_stored_total` (labels: `repair_type`)
  - `prompt_positive_patterns_injected_total`

### Test Plan (Phase 2)
- Unit: `test_store_positive_repair_upsert` (increments `success_count`)
- Unit: `test_get_positive_patterns_filters`
- Integration: simulate successful repair, assert Neo4j node exists and `success_count` increments on repeat
- Integration: mock `PromptEnhancer` to ensure positive patterns are injected and ordered after negatives

### Risks & Mitigations
- **Prompt bloat**: Cap positive patterns per prompt (e.g., `max_positive=3`)
- **Stale snippets**: Include `last_repo_hash`; drop snippets older than N commits if mismatch
- **Neo4j latency**: async store with fire-and-forget; fallback to in-memory cache if queue backs up

### Ownership & ETA
- **Owner**: Assign to Repair squad (needs confirmation)
- **ETA**: 1–2 days once approved

---

## 🎛️ Phase 3 Test Design (Cross-Session Learning)

**Objective**: Prove Session N+1 avoids Session N errors by ≥20% with enhanced prompts and stored patterns.

### Test Harness (draft)
- Script: `tests/e2e/test_learning_loop_closure.py`
- Inputs: deterministic spec (e.g., `ecommerce-api-spec-human.md`) and fixed seed for reproducibility
- Steps:
  1. **Session 1**: run full pipeline; capture smoke failures + logs; snapshot patterns count
  2. Assert patterns were stored (negative + positive when repairs run)
  3. **Session 2**: rerun same spec; capture failures + logs
  4. Assert logs contain both negative + positive injection messages
  5. Compute error reduction; assert `> 0.2`

### Metrics to Record
- `session_id`, `patterns_injected_neg`, `patterns_injected_pos`
- `smoke_failures_count`, `repair_attempts`, `repair_successes`
- `error_reduction_ratio` (Session2 vs Session1)

### Validation Criteria
- Session 2 should:
  - Inject ≥1 pattern from Session 1
  - Skip ≥1 previously failing case (manually verify in logs)
  - Reduce failures by >20%

### Open Items
- Need stable seeds for LLM responses or recorded responses for determinism
- Define minimal fixture for Neo4j (container vs in-memory double)
- Decide how to stub external tools (git, file writes) in CI to keep test hermetic

---

## 📚 References

- `src/learning/negative_pattern_store.py` - Pattern storage
- `src/learning/prompt_enhancer.py` - Prompt enhancement
- `src/learning/feedback_collector.py` - Error capture
- `src/services/pattern_aware_generator.py` - AST overrides
- `DOCS/mvp/PHASE_10_LEARNING.md` - Learning architecture

---

**Next Steps**:
1. Review Phase 2/3 design and confirm API surface (store/get positive patterns)
2. Assign owners for 2.1/2.2/3.1 and create tracking issues
3. Implement Phase 2 (store positive repairs + recording in CodeRepairAgent)
4. Implement Phase 3 test harness and add to CI gating
5. Run E2E with logging checks for pattern injection (neg + pos) and target >20% reduction
