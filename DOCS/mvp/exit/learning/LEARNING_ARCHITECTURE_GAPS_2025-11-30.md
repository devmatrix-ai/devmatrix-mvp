# Learning System Architecture Gaps Analysis
## Date: 2025-11-30

## Executive Summary

Analysis of the complete learning pipeline reveals **4 critical architectural gaps** that prevent learned anti-patterns from benefiting most of the generated code. While the learning loop was recently closed (Bug #163), the system currently only applies learning to ~6% of generated code.

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GENERATION PIPELINE                                 │
├──────────────────┬──────────────────┬───────────────────────────────────────┤
│    TEMPLATE      │       AST        │              LLM                       │
│    (~32%)        │     (~62%)       │            (~6%)                       │
├──────────────────┼──────────────────┼───────────────────────────────────────┤
│ Static files:    │ IR transforms:   │ Business logic:                        │
│ - docker-compose │ - entities.py    │ - *_flow_methods.py                    │
│ - config.py      │ - schemas.py     │ - *_business_rules.py                  │
│ - main.py        │ - repositories   │ - *_custom.py endpoints                │
│ - requirements   │ - services       │ - repair_patches                       │
│ - health.py      │ - routes         │                                        │
├──────────────────┼──────────────────┼───────────────────────────────────────┤
│ Learning: NONE   │ Learning: NONE   │ Learning: prompt_enhancer              │
│                  │                  │           IRCentricCognitivePass       │
└──────────────────┴──────────────────┴───────────────────────────────────────┘
```

## Gap #1: CognitiveCodeGenerationService NOT INTEGRATED

**Severity**: CRITICAL
**Impact**: Cognitive pass never executes in production

### Evidence
- `src/services/cognitive_code_generation_service.py` exists (517 lines)
- `IRCentricCognitivePass` implemented and tested
- **BUT**: No agent or orchestrator imports or uses it

```python
# Search results show NO usage:
grep -r "cognitive_code_generation|CognitiveCodeGeneration" src/agents/
# Result: No files found
```

### Root Cause
The service was built but never wired into the generation pipeline. The main `code_generation_service.py` doesn't call `CognitiveCodeGenerationService.process_files()`.

### Solution
Wire `CognitiveCodeGenerationService` into the generation pipeline:
1. Import in `code_generation_service.py`
2. Call after AST/TEMPLATE generation for LLM-eligible files
3. Enable via feature flag `ENABLE_COGNITIVE_PASS=true`

---

## Gap #2: Learning ONLY Applied to LLM Stratum (~6%)

**Severity**: HIGH
**Impact**: 94% of code never benefits from learned patterns

### Evidence
From `src/services/stratum_classification.py`:
```python
# Stratum distribution:
TEMPLATE_GENERATORS = {...}  # ~32% of files
AST_GENERATORS = {...}       # ~62% of files
LLM_GENERATORS = {...}       # ~6% of files
```

From `src/services/llm_guardrails.py`:
```python
LLM_ALLOWED_SLOTS: Set[str] = {
    "src/services/*_flow_methods.py",
    "src/services/*_business_rules.py",
    "src/routes/*_custom.py",
    "repair_patches/*.py",
}
```

From `src/learning/prompt_enhancer.py`:
```python
# Enhancer only injects into LLM prompts:
class GenerationPromptEnhancer:
    def enhance_entity_prompt(self, base_prompt: str, ...):
        # Only enhances LLM prompts!
```

### Root Cause
The learning system was designed for LLM-only enhancement. TEMPLATE and AST stratums are deterministic and don't use LLM, so they never receive anti-pattern guidance.

### Problem Manifestation
1. Smoke test detects error in `entities.py` (AST stratum)
2. Anti-pattern created: "IntegrityError on FK field"
3. Next run: `entities.py` regenerated from AST (same templates)
4. Same error occurs because AST doesn't see anti-patterns

### Solution Options

**Option A: Modify AST Templates Based on Patterns**
- When pattern count for entity > threshold, modify AST generator
- Example: If "IntegrityError on FK" pattern exists, AST adds nullable=True

**Option B: Post-AST LLM Review Pass**
- After AST generation, run LLM review for files with relevant patterns
- LLM sees anti-patterns and can suggest fixes
- More token cost but more flexible

**Option C: Pattern-Aware Template Selection** (Recommended)
- Create multiple template variants for common error patterns
- Select template based on matching anti-patterns in NegativePatternStore
- Deterministic but pattern-informed

---

## Gap #3: Learning Loop Closure Partial (Bug #163 Fixed)

**Severity**: MEDIUM (Recently Fixed)
**Impact**: Anti-patterns now have correct_code_snippet after repair

### Evidence (Before Fix)
```python
# error_knowledge_bridge.py:177-184
anti_pattern = GenerationAntiPattern(
    ...
    correct_code_snippet="",  # EMPTY - never filled!
)
```

### Solution Implemented (Bug #163)
Added `update_correct_snippet()` and `find_pattern_by_error()` to `NegativePatternStore`, wired `SmokeRepairOrchestrator` to update patterns on successful repair.

### Current State
- Smoke failures create anti-patterns
- Successful repairs update `correct_code_snippet`
- **BUT**: Only LLM prompts use these patterns

---

## Gap #4: TEMPLATE/AST Cannot Learn From Errors

**Severity**: HIGH
**Impact**: Templates repeat same mistakes indefinitely

### Evidence
From `src/services/template_generator.py`:
```python
# Templates are static Python strings:
TEMPLATE_DOCKER_COMPOSE = '''
version: "3.8"
...
'''

def generate_docker_compose() -> str:
    return TEMPLATE_DOCKER_COMPOSE  # No pattern awareness!
```

From `src/services/production_code_generators.py`:
```python
# AST generation is deterministic from IR:
def generate_entities(domain_model_ir: DomainModelIR) -> str:
    # Builds Python AST from IR fields
    # No pattern consultation!
```

### Root Cause
TEMPLATE and AST generation are by design deterministic and LLM-free. They have no mechanism to consult `NegativePatternStore` for historical failures.

### Solution: Pattern-Aware Generation Layer

```python
# Proposed: src/services/pattern_aware_generator.py

class PatternAwareGenerator:
    """
    Wrapper that injects pattern awareness into any generation stratum.
    """

    def __init__(self, pattern_store: NegativePatternStore):
        self.pattern_store = pattern_store

    def get_field_adjustments(self, entity_name: str) -> Dict[str, Any]:
        """
        Get field adjustments based on historical patterns.

        Example:
            If pattern "IntegrityError on category_id" exists with
            correct_code = "nullable=True", return:
            {"category_id": {"nullable": True}}
        """
        patterns = self.pattern_store.get_patterns_for_entity(entity_name)
        adjustments = {}
        for p in patterns:
            if p.correct_code_snippet and p.field_pattern:
                # Parse correct_code for adjustments
                adjustments[p.field_pattern] = self._parse_adjustment(p)
        return adjustments

    def wrap_ast_generator(
        self,
        generator_func: Callable,
        entity_name: str,
    ) -> str:
        """Wrap AST generator with pattern awareness."""
        adjustments = self.get_field_adjustments(entity_name)
        if not adjustments:
            return generator_func()  # No patterns, use standard

        # Inject adjustments into IR before generation
        return generator_func(field_overrides=adjustments)
```

---

## Implementation Roadmap

### Phase 1: Quick Wins (Immediate)
- [ ] Wire `CognitiveCodeGenerationService` into pipeline
- [ ] Enable via `ENABLE_COGNITIVE_PASS` feature flag
- [ ] Add metrics for cognitive pass usage

### Phase 2: AST Pattern Awareness
- [ ] Create `PatternAwareGenerator` wrapper
- [ ] Modify `production_code_generators.py` to accept field overrides
- [ ] Add pattern consultation before AST generation

### Phase 3: Template Variants
- [ ] Identify top 5 recurring TEMPLATE errors
- [ ] Create variant templates for each error type
- [ ] Implement template selection based on patterns

### Phase 4: Full Learning Integration
- [ ] All stratums consult NegativePatternStore
- [ ] Metrics dashboard for prevention rate per stratum
- [ ] A/B testing framework for learning effectiveness

---

## Files to Modify

### Phase 1
1. `src/services/code_generation_service.py` - Wire cognitive service
2. `src/agents/orchestrator_agent.py` - Call cognitive pass
3. Add feature flag support

### Phase 2
1. `src/services/production_code_generators.py` - Accept field overrides
2. `src/services/pattern_aware_generator.py` - NEW FILE
3. `src/learning/negative_pattern_store.py` - Add query methods

### Phase 3
1. `src/services/template_generator.py` - Template variants
2. `src/services/stratum_classification.py` - Pattern-aware routing

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Code using learning | 6% | 100% |
| Prevention rate | 0% | >50% |
| Repeat error rate | High | <10% |
| Cognitive pass usage | 0 | All LLM files |

---

## References

- Bug #163: Learning Loop Closure - FIXED
- Bug #162: Pattern Store API - FIXED
- [GENERATION_FEEDBACK_LOOP.md](./GENERATION_FEEDBACK_LOOP.md)
- [LEARNING_SYSTEM_ARCHITECTURE.md](./LEARNING_SYSTEM_ARCHITECTURE.md)
