# Code Generation Bug Fixes - November 26, 2025

## Summary

This document tracks bug fixes applied to the DevMatrix code generation pipeline following QA analysis of generated applications.

---

## Bug #1: requirements.txt Not Generated (IR-centric Mode)

**Status**: FIXED

**Root Cause**: The `generate_from_application_ir()` method (used by E2E pipeline) was missing the call to `_generate_with_llm_fallback()` that generates essential files like `requirements.txt`, `README.md`, and `poetry.lock`.

**Files Modified**:
- `src/services/code_generation_service.py`

**Changes**:
1. Modified `_generate_with_llm_fallback()` to accept both `spec_requirements` (legacy) and `application_ir` (IR-centric) as optional parameters
2. Added call to `_generate_with_llm_fallback()` in `generate_from_application_ir()` after `_compose_patterns()`
3. Updated `_generate_readme_md()` to detect and handle both `ApplicationIR` and `SpecRequirements` for extracting project metadata

**Code Snippet** (line 621-628):
```python
# Fallback for missing essential files (requirements.txt, README.md, etc.)
logger.info("Checking for missing essential files")
llm_generated = await self._generate_with_llm_fallback(
    files_dict,
    spec_requirements=None,
    application_ir=app_ir
)
files_dict.update(llm_generated)
```

---

## Bug #2: Route↔Service Method Mismatch (get_all vs list)

**Status**: FIXED

**Root Cause**: Route generator in `code_generation_service.py` was calling `service.get_all(skip=0, limit=100)` but Service template uses `service.list(page, size)`.

**Files Modified**:
- `src/services/code_generation_service.py` (line 3209-3214)

**Before**:
```python
body += f'''    {entity_plural} = await service.get_all(skip=0, limit=100)
return {entity_plural}
'''
```

**After**:
```python
body += f'''    result = await service.list(page=1, size=100)
return result.items
'''
```

---

## Bug #3: PUT Endpoints Using Wrong Schema (ProductCreate vs ProductUpdate)

**Status**: FIXED

**Root Cause**: Route generator used `*Create` schema for both POST and PUT methods. PUT should use `*Update` schema (with optional fields).

**Files Modified**:
- `src/services/code_generation_service.py` (line 3195-3199)

**Before**:
```python
if method in ['post', 'put']:
    params.append(f'{entity_snake}_data: {entity.name}Create')
```

**After**:
```python
if method == 'post':
    params.append(f'{entity_snake}_data: {entity.name}Create')
elif method == 'put':
    params.append(f'{entity_snake}_data: {entity.name}Update')
```

---

## Bug #4: Missing Custom Operations (deactivate, clear)

**Status**: FIXED

**Root Cause**: `ModularArchitectureGenerator` only handled 5 CRUD operations (create, read, list, update, delete). Custom operations like `deactivate` and `clear` were ignored, causing incorrect code generation.

**Files Modified**:
- `src/services/modular_architecture_generator.py` (line 752-786)
- `src/services/production_code_generators.py` (line 1221-1238)

**Changes**:
1. Added route handlers for `deactivate` and `clear` operations in `ModularArchitectureGenerator`
2. Added `clear_items()` method to Service template
3. Added `clear_items()` and `count()` methods to Repository template

**New Operations**:
```python
# Deactivate: POST /{id}/deactivate
# - Gets entity by ID
# - Updates is_active=False using Update schema

# Clear: POST /{id}/clear
# - Gets entity by ID
# - Calls service.clear_items(id) to remove child items
```

---

## Bug #5: Dead Code (Endpoints with pass)

**Status**: FIXED

**Root Cause**: `CodeRepairAgent._generate_endpoint_function_ast()` was generating placeholder endpoints with only `pass` in the body, creating dead/non-functional code.

**Files Modified**:
- `src/mge/v2/agents/code_repair_agent.py` (line 629-769)

**Changes**:
1. GET endpoints now generate real code: `service.list(page=1, size=100)` + return items
2. POST endpoints now generate real code: `service.create(data)`
3. Other methods raise `NotImplementedError` with clear message instead of silent `pass`

**Example Generated Code**:
```python
@router.get("/")
async def list_products(db: AsyncSession = Depends(get_db)):
    service = ProductService(db)
    result = await service.list(page=1, size=100)
    return result.items
```

---

## Validation

All modified files pass Python syntax validation:
- `python -m py_compile src/services/code_generation_service.py` ✅
- `python -m py_compile src/services/modular_architecture_generator.py` ✅
- `python -m py_compile src/services/production_code_generators.py` ✅
- `python -m py_compile src/mge/v2/agents/code_repair_agent.py` ✅

---

## Next Steps

1. Run E2E test to verify all fixes work together
2. QA the generated application to confirm:
   - `requirements.txt` is generated
   - GET /products/ returns list (not 500 error)
   - PUT endpoints accept partial updates
   - Custom endpoints (deactivate, clear) work correctly
   - No dead code with `pass`

---

## Related Documents

- [IR_MATCHING_IMPROVEMENT_PLAN.md](IR_MATCHING_IMPROVEMENT_PLAN.md) - IR Compliance validation improvements
- [PIPELINE_E2E_PHASES.md](PIPELINE_E2E_PHASES.md) - E2E pipeline phase documentation
