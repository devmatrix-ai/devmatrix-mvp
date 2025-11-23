# Architectural Rules - PERMANENT

## Rule #1: NO Manual Ground Truth in Code 🚨

**CRITICAL PRINCIPLE**: Ground truth baselines must NEVER be manually defined in code.

### The Rule
```
❌ DO NOT: Hardcode validation lists, entity counts, or baseline requirements
❌ DO NOT: Use manual YAML definitions as "source of truth"
❌ DO NOT: Mix manual definitions with LLM extraction

✅ DO: Let LLM extraction be the ONLY ground truth
✅ DO: Measure compliance against what the system actually extracts
✅ DO: Trust the automated process, not manual lists
```

### Why This Matters
- Manual definitions limit thinking ("we think there are 82 validations")
- LLM extraction discovers more ("actually there are 133 validations")
- Manual baselines hide what the system is missing
- LLM extraction drives improvement (extract 50 → 100 → 150)

### Real Example: The Mistake We Made
**WRONG APPROACH:**
```yaml
# In ecommerce_api_simple.md
validations:
  V001: Product.id uuid_format
  V002: Product.name required
  # ... manually list 82 validations
```
Then measure: `43_implemented / 82_defined = 52%`

**CORRECT APPROACH:**
```
1. LLM extracts from spec automatically → 133 validations
2. Code generation implements validations → 43 validations
3. Measure: 43_implemented / 133_extracted = 32.3%
4. Gap analysis: 90 validations not yet implemented
```

### This Rule Applies To
- ✅ Validation ground truth (must use LLM extraction)
- ✅ Entity definitions (let parser extract, don't list manually)
- ✅ Endpoint baselines (measure against generated, not pre-defined)
- ✅ Test coverage targets (use actual metrics, not guesses)
- ✅ API specifications (extracted from spec, not manually written)

### When to Document, Not Define
- Document the PHILOSOPHY (e.g., `minimum_required: 30`)
- Document the PROCESS (`validation_count: unlimited`)
- Document the APPROACH (LLM extraction first, then fallback)
- BUT: Never pre-define the actual baseline values

### Enforcement
If you see manual lists like this in code:
```python
# WRONG:
EXPECTED_VALIDATIONS = [
    "Product.id.uuid_format",
    "Product.name.required",
    # ... hardcoded list
]

# RIGHT:
# Extract from LLM output, compare against that
extracted_validations = llm_extract_validations(spec)
implemented_validations = code_analyzer.extract_validations(generated_code)
compliance = len(implemented_validations) / len(extracted_validations)
```

---

## Rule #2: Trust the System, Not the Manual

**Corollary to Rule #1**: When the LLM extracts something the manual list missed, the LLM is right.

- LLM found 133 validations? ✅ That's what we implement against
- Manual YAML only had 82? ❌ That baseline was incomplete
- Gap exists? ✅ That's reality, not a bug

---

## Implementation Checklist
Before committing code with ground truth logic:
- [ ] Is this extracting from automated process (LLM, code analyzer)?
- [ ] Is this comparing against extracted values, not manual lists?
- [ ] Would removing manual definitions still work?
- [ ] Are we measuring what the system actually produces?

If you answer "no" to any of these, the code violates this rule.

---

## Historical Context
- **Old approach**: Limited ground truth to 52-132 validations (arbitrary)
- **Current approach**: Unlimited extraction, only minimum threshold (30)
- **This rule**: Enforce that the baseline is what LLM extracts, never manual

Date established: November 23, 2025
Enforcer: Ariel
Status: NON-NEGOTIABLE 🚨
