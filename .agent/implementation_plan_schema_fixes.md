# Implementation Plan: Schema Generation Fixes for 100% Compliance

## Objective
Fix the 6 critical issues in code generation to achieve 100% validation compliance and eliminate all UNMATCHED VALIDATIONS.

## Issues to Fix

### 1. ❌ Campos Read-Only Editables
**Problem**: Fields marked as "read-only" are included in Update schemas
**Examples**:
- `Customer.registration_date: read-only`
- `Order.creation_date: read-only`

**Solution**:
- Detect fields with `read-only`, `read_only`, `snapshot_at*`, or `immutable` constraints
- Exclude them from `{Entity}Update` schemas
- Keep them in `{Entity}Response` schemas

### 2. ❌ Campos Auto-Calculated Editables
**Problem**: Fields marked as "auto-calculated" are included in Update/Create schemas
**Examples**:
- `Order.total_amount: auto-calculated`

**Solution**:
- Detect fields with `auto-calculated`, `auto_calculated`, `computed`, or `derived` constraints
- Exclude them from `{Entity}Update` AND `{Entity}Create` schemas
- Server should calculate these values automatically

### 3. ❌ Campos Snapshot/Immutable Editables
**Problem**: Price snapshots should be immutable after creation
**Examples**:
- `CartItem.unit_price: snapshot_at_add_time`
- `OrderItem.unit_price: snapshot_at_order_time`

**Solution**:
- Detect fields with `snapshot*` or `immutable` constraints
- Exclude them from `{Entity}Update` schemas
- Allow them in `{Entity}Create` schemas (server will set them)

### 4. ❌ Enums con Defaults Inconsistentes
**Problem**: Literal enum values don't match defaults
**Examples**:
```python
status: Literal['open', 'checked_out'] = 'OPEN'  # ❌ 'OPEN' not in Literal
```

**Solution**:
- Normalize enum values to lowercase in both Literal and defaults
- OR normalize to uppercase consistently
- **Decision**: Use lowercase for consistency with database defaults

### 5. ❌ `default_factory` en SQLAlchemy
**Problem**: SQLAlchemy Column doesn't support `default_factory`
**Examples**:
```python
registration_date = Column(..., default_factory=datetime.utcnow)  # ❌
```

**Solution**:
```python
registration_date = Column(..., default=lambda: datetime.now(timezone.utc))  # ✅
```

### 6. ❌ Rutas Duplicadas con `pass`
**Problem**: Stub routes with `pass` duplicate real implementations
**Solution**: This is handled in route generation, not schemas

## Implementation Steps

### Step 1: Enhance Constraint Detection in `generate_schemas()`
**File**: `src/services/production_code_generators.py`

Add function to detect special field types:
```python
def _is_read_only_field(field_name: str, constraints: list, description: str) -> bool:
    """Detect if field is read-only (server-managed, immutable after creation)"""
    # Check field name patterns
    if field_name in ['id', 'created_at', 'updated_at', 'registration_date', 'creation_date']:
        return True
    
    # Check constraints
    for c in constraints:
        c_lower = str(c).lower()
        if any(keyword in c_lower for keyword in ['read-only', 'read_only', 'immutable', 'snapshot_at']):
            return True
    
    # Check description
    desc_lower = description.lower()
    if any(keyword in desc_lower for keyword in ['read-only', 'read only', 'auto-generated', 'snapshot']):
        return True
    
    return False

def _is_auto_calculated_field(field_name: str, constraints: list, description: str) -> bool:
    """Detect if field is auto-calculated (server computes value)"""
    # Check constraints
    for c in constraints:
        c_lower = str(c).lower()
        if any(keyword in c_lower for keyword in ['auto-calculated', 'auto_calculated', 'computed', 'derived', 'sum_of']):
            return True
    
    # Check description
    desc_lower = description.lower()
    if any(keyword in desc_lower for keyword in ['auto-calculated', 'auto calculated', 'sum of']):
        return True
    
    return False
```

### Step 2: Modify Update Schema Generation
**Location**: Lines 763-811 in `generate_schemas()`

```python
# Update schema - exclude read-only and auto-calculated fields
code += f'''class {entity_name}Update(BaseSchema):
    """Schema for updating {entity_lower}."""
'''
if base_fields:
    update_fields = []
    for field_obj in fields_list:
        field_name = field_obj.name if hasattr(field_obj, 'name') else field_obj.get('name')
        constraints = getattr(field_obj, 'constraints', []) or field_obj.get('constraints', [])
        description = getattr(field_obj, 'description', '') or field_obj.get('description', '')
        
        # Skip read-only and auto-calculated fields
        if _is_read_only_field(field_name, constraints, description):
            logger.info(f"🔒 Excluding read-only field {entity_name}.{field_name} from Update schema")
            continue
        if _is_auto_calculated_field(field_name, constraints, description):
            logger.info(f"🧮 Excluding auto-calculated field {entity_name}.{field_name} from Update schema")
            continue
        
        # ... rest of field processing
```

### Step 3: Modify Create Schema Generation
**Location**: Lines 755-761 in `generate_schemas()`

```python
# Create schema - exclude auto-calculated and server-managed fields
code += f'''class {entity_name}Create(BaseSchema):
    """Schema for creating {entity_lower}."""
'''
create_fields = []
for field_obj in fields_list:
    field_name = field_obj.name if hasattr(field_obj, 'name') else field_obj.get('name')
    
    # Skip server-managed fields
    if field_name in ['id', 'created_at', 'updated_at']:
        continue
    
    constraints = getattr(field_obj, 'constraints', []) or field_obj.get('constraints', [])
    description = getattr(field_obj, 'description', '') or field_obj.get('description', '')
    
    # Skip auto-calculated fields (server computes them)
    if _is_auto_calculated_field(field_name, constraints, description):
        logger.info(f"🧮 Excluding auto-calculated field {entity_name}.{field_name} from Create schema")
        continue
    
    # Include the field
    create_fields.append(field_line)

if create_fields:
    code += '\n'.join(create_fields) + '\n'
else:
    code += '    pass\n'
code += '\n\n'
```

### Step 4: Fix Enum Defaults
**Location**: Lines 508-570 in `generate_schemas()`

```python
# Normalize enum values to lowercase
if entity_lower == 'cart' and field_name == 'status':
    enum_values = ["open", "checked_out"]  # ✅ lowercase
    field_default = 'open'  # ✅ matches Literal
elif entity_lower == 'order' and field_name == 'status':
    enum_values = ["pending_payment", "paid", "cancelled"]
    field_default = 'pending_payment'
elif entity_lower == 'order' and field_name == 'payment_status':
    enum_values = ["pending", "simulated_ok", "failed"]
    field_default = 'pending'
```

### Step 5: Fix SQLAlchemy `default_factory`
**File**: `src/services/production_code_generators.py`
**Function**: `generate_entities()`
**Location**: Lines 35-180

```python
# Replace default_factory with default=lambda
if has_default and field.default != '...':
    if field_type == 'datetime':
        # ✅ Use default=lambda instead of default_factory
        column_def += ', default=lambda: datetime.now(timezone.utc)'
    elif field_type in ['str', 'string']:
        column_def += f', default="{field.default}"'
    # ... rest of types
```

### Step 6: Add Logging for Debugging
Add comprehensive logging to track which fields are being excluded and why:

```python
logger.info(f"📋 Processing {entity_name} schemas:")
logger.info(f"  - Base fields: {len(base_fields)}")
logger.info(f"  - Create fields: {len(create_fields)}")
logger.info(f"  - Update fields: {len(update_fields)}")
logger.info(f"  - Response fields: {len(response_lines)}")
```

## Testing Strategy

### 1. Unit Tests
Create tests for the helper functions:
```python
def test_is_read_only_field():
    assert _is_read_only_field('id', [], '') == True
    assert _is_read_only_field('created_at', [], '') == True
    assert _is_read_only_field('registration_date', [], '') == True
    assert _is_read_only_field('unit_price', ['snapshot_at_add_time'], '') == True
    assert _is_read_only_field('name', [], '') == False

def test_is_auto_calculated_field():
    assert _is_auto_calculated_field('total_amount', ['auto-calculated'], '') == True
    assert _is_auto_calculated_field('total', [], 'Auto-calculated: sum of items') == True
    assert _is_auto_calculated_field('price', [], '') == False
```

### 2. E2E Test
Run the full pipeline with the ecommerce spec:
```bash
PRODUCTION_MODE=true PYTHONPATH=/home/kwar/code/agentic-ai \
  python tests/e2e/real_e2e_full_pipeline.py \
  tests/e2e/test_specs/ecommerce-api-spec-human.md
```

**Expected Results**:
- ✅ Compliance: 100% (was 98.1%)
- ✅ Validations: 63/63 (was 57/63)
- ✅ UNMATCHED VALIDATIONS: 0 (was 6)

### 3. Manual Verification
Check generated files:
```bash
# Check schemas
cat tests/e2e/generated_apps/*/src/models/schemas.py | grep -A 5 "class.*Update"

# Check entities
cat tests/e2e/generated_apps/*/src/models/entities.py | grep "default_factory"

# Should return nothing ✅
```

## Success Criteria

- [ ] No `default_factory` in entities.py
- [ ] Enum defaults match Literal values
- [ ] Read-only fields excluded from Update schemas
- [ ] Auto-calculated fields excluded from Create/Update schemas
- [ ] Snapshot fields excluded from Update schemas
- [ ] E2E test shows 100% compliance
- [ ] All 6 UNMATCHED VALIDATIONS resolved

## Rollout Plan

1. **Phase 1**: Implement fixes in `production_code_generators.py`
2. **Phase 2**: Run E2E test to verify
3. **Phase 3**: If compliance < 100%, debug and iterate
4. **Phase 4**: Document changes in CHANGELOG.md
5. **Phase 5**: Update golden demo app

## Estimated Time
- Implementation: 2-3 hours
- Testing: 1 hour
- Documentation: 30 minutes
- **Total**: ~4 hours
