"""
Production-Ready Code Generators

Hardcoded generators that produce 100% correct code for production apps.
These are used as fallback when LLM-generated patterns are incomplete.
"""

import ast
from collections import defaultdict
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Bug #164 Fix: Import PatternAwareGenerator for AST stratum learning
try:
    from src.services.pattern_aware_generator import get_field_overrides_for_entity
    PATTERN_AWARE_AVAILABLE = True
except ImportError:
    PATTERN_AWARE_AVAILABLE = False
    def get_field_overrides_for_entity(entity_name: str):
        return {}

# Fix #3: Field name normalization mapping
# Maps spec/IR field names to standard code field names
FIELD_NAME_MAPPING = {
    "creation_date": "created_at",
    "modification_date": "updated_at",
    "fecha_creacion": "created_at",
    "fecha_modificacion": "updated_at",
}

def normalize_field_name(field_name: str) -> str:
    """
    Normalize field names from spec/IR to standard code names.

    Args:
        field_name: Original field name from spec or IR

    Returns:
        Normalized field name for code generation
    """
    return FIELD_NAME_MAPPING.get(field_name.lower(), field_name)


def validate_python_syntax(code: str, filename: str = "generated") -> bool:
    """
    Validate that generated code has correct Python syntax.

    Args:
        code: Python code string
        filename: File name for error reporting

    Returns:
        True if valid, False otherwise
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        logger.error(f"❌ Syntax error in {filename}: {e.msg} at line {e.lineno}")
        return False


# =============================================================================
# Pre-Generation Validation (Bug #140: Validate assumptions before generating)
# =============================================================================

def validate_template_assumptions(
    entity_name: str,
    all_entities: List[Dict],
    child_info: Dict[str, Any],
    ir: Any = None
) -> Dict[str, Any]:
    """
    Validate template assumptions against IR reality BEFORE generating code.

    Bug #140 Fix: Templates were generating code that imports non-existent entities
    (e.g., ChildItemEntity when only the parent entity exists).

    This function checks what the IR actually contains and returns flags
    telling the template what it CAN and CANNOT generate.

    Args:
        entity_name: Name of entity being generated (e.g., "Product")
        all_entities: List of all entities from IR
        child_info: Result from find_child_entity()
        ir: ApplicationIR (optional, for additional context)

    Returns:
        Dict with validation results:
            - can_generate_clear_items: bool
            - child_entity_class: str or None
            - child_fk_field: str or None
            - available_entities: List[str]
            - warnings: List[str]
    """
    result = {
        "can_generate_clear_items": False,
        "child_entity_class": None,
        "child_fk_field": None,
        "available_entities": [],
        "warnings": [],
    }

    # Build list of available entities for reference
    for entity in all_entities:
        name = entity.get('name', '')
        if name:
            result["available_entities"].append(name)

    # Check if child entity actually exists
    if child_info.get("found"):
        child_name = child_info.get("entity_name", "")
        child_class = child_info.get("entity_class", "")

        # Verify the child entity is in the available entities
        if child_name in result["available_entities"] or any(
            e.lower() == child_name.lower() for e in result["available_entities"]
        ):
            result["can_generate_clear_items"] = True
            result["child_entity_class"] = child_class
            result["child_fk_field"] = child_info.get("fk_field")
            logger.debug(f"✅ Entity {entity_name} has verified child: {child_name}")
        else:
            # Child was inferred but doesn't exist - DON'T generate clear_items
            result["warnings"].append(
                f"Inferred child {child_name} not found in entities. "
                f"Available: {result['available_entities']}"
            )
            logger.warning(
                f"⚠️ Bug #140 prevention: {entity_name} claimed child {child_name} "
                f"but it doesn't exist. Skipping clear_items generation."
            )
    else:
        # No child entity - that's fine, just don't generate clear_items
        logger.debug(f"Entity {entity_name} has no child relationships")

    return result


def validate_import_exists(
    import_name: str,
    available_entities: List[str]
) -> bool:
    """
    Validate that an entity import will succeed.

    Args:
        import_name: Entity class name to import (e.g., "SomeItemEntity")
        available_entities: List of available entity names

    Returns:
        True if import should succeed, False if it would fail
    """
    # Extract base name from class (SomeItemEntity -> SomeItem)
    base_name = import_name.replace("Entity", "")

    # Check if any entity matches
    for entity in available_entities:
        if entity.lower() == base_name.lower():
            return True
        if entity.lower() == import_name.lower().replace("entity", ""):
            return True

    return False


# =============================================================================
# IR-Based Dynamic Detection Helpers (Bug #109: Eliminate hardcoding)
# =============================================================================

def _map_status_values(status_values: List[str]) -> Dict[str, str]:
    """
    Map semantic status concepts to actual values from an enum list.

    Bug #109: Instead of hardcoding "PENDING_PAYMENT", "CANCELLED", etc.,
    we derive them from the actual enum values in the IR.

    Returns dict mapping semantic concepts to actual values:
        - initial: First/default status
        - open: Status for open/active items
        - cancelled: Status for cancelled items
        - paid: Status for paid items
        - checked_out: Status for checked out carts
        - pending_payment: Status awaiting payment
    """
    result = {}

    if not status_values:
        return result

    # First value is typically the initial status
    result["initial"] = status_values[0]

    # Map by pattern matching (case-insensitive)
    for value in status_values:
        value_lower = value.lower()

        if "open" in value_lower or "active" in value_lower:
            result["open"] = value
        elif "cancel" in value_lower:
            result["cancelled"] = value
        elif "paid" in value_lower and "unpaid" not in value_lower:
            result["paid"] = value
        elif "check" in value_lower and "out" in value_lower:
            result["checked_out"] = value
        elif "pending" in value_lower:
            if "payment" in value_lower:
                result["pending_payment"] = value
            elif "initial" not in result:
                result["initial"] = value
        elif "confirm" in value_lower:
            result["confirmed"] = value
        elif "ship" in value_lower:
            result["shipped"] = value
        elif "deliver" in value_lower:
            result["delivered"] = value
        elif "complet" in value_lower:
            result["completed"] = value

    return result


def find_status_field(entity_name: str, entity_fields: List[Dict], ir: Any = None) -> Dict[str, Any]:
    """
    Find the status field for an entity from its fields or IR.

    Returns dict with:
        - field_name: The actual field name (e.g., "order_status", "status")
        - values: List of valid values if available
        - initial_value: Default/initial status value
        - is_enum: Whether field is an enum type

    Bug #109: Derives field info from IR instead of hardcoding.
    """
    result = {
        "field_name": None,
        "values": [],
        "initial_value": None,
        "is_enum": False
    }

    # 1. Search in entity fields for status-like field
    for field in entity_fields:
        field_name = field.get('name', '').lower()
        # Look for status fields: "{entity}_status", "status", "{action}_status"
        if 'status' in field_name:
            result["field_name"] = field.get('name')
            result["is_enum"] = 'enum' in field.get('data_type', '').lower()

            # Extract enum values from field constraints
            constraints = field.get('constraints', {})
            if isinstance(constraints, dict):
                enum_values = constraints.get('enum_values', [])
                if enum_values:
                    result["values"] = enum_values
                    result["initial_value"] = enum_values[0]  # First value is typically initial

            # Check for default value
            if field.get('default_value'):
                result["initial_value"] = field.get('default_value')

            break  # Use first status field found

    # 2. If IR available, try to get state machine info
    if ir and hasattr(ir, 'behavior_model') and ir.behavior_model:
        # Check for state machine defining this entity's states
        for flow in ir.behavior_model.flows:
            if flow.type and 'state' in str(flow.type).lower():
                # This might define state transitions
                if entity_name.lower() in flow.name.lower():
                    # Extract states from flow steps
                    for step in flow.steps:
                        if step.action and 'status' in step.action.lower():
                            # Parse action for status values
                            pass

    return result


def find_child_entity(entity_name: str, entities: List[Dict], ir: Any = None) -> Dict[str, Any]:
    """
    Find child entity for parent-child relationships (e.g., Parent -> ParentItem).

    Returns dict with:
        - entity_name: Child entity name (derived from IR)
        - entity_class: Class name for code (e.g., "{ChildName}Entity")
        - fk_field: Foreign key field name (e.g., "{parent}_id")
        - found: Boolean indicating if child was found
        - auto_populated_fields: List of fields to fetch from referenced entities
        - reference_fk: FK to referenced entity (e.g., "product_id")
        - reference_entity: Referenced entity name (e.g., "Product")

    Bug #109: Derives relationships from IR instead of hardcoding.
    Bug #203: Detects auto-populated fields from referenced entities (domain-agnostic).
    """
    result = {
        "entity_name": None,
        "entity_class": None,
        "fk_field": None,
        "found": False,
        "auto_populated_fields": [],  # Bug #203: Fields to fetch from referenced entity
        "reference_fk": None,         # Bug #203: FK field to referenced entity
        "reference_entity": None,     # Bug #203: Referenced entity name
    }

    parent_lower = entity_name.lower()
    expected_fk = f"{parent_lower}_id"

    # Look for entities that have FK to this entity
    for entity in entities:
        entity_name_check = entity.get('name', '').lower()

        # Check if entity name suggests it's a child (e.g., "{Parent}Item" for "{Parent}")
        if parent_lower in entity_name_check and entity_name_check != parent_lower:
            child_fields = entity.get('fields', [])

            # Check fields for FK to parent
            for field in child_fields:
                field_name = field.get('name', '').lower()
                if field_name == expected_fk or 'fk' in field.get('data_type', '').lower():
                    result["entity_name"] = entity.get('name')
                    result["entity_class"] = f"{entity.get('name')}Entity"
                    result["fk_field"] = field.get('name')
                    result["found"] = True

                    # Bug #203: Detect auto-populated fields and referenced entity
                    _detect_auto_populated_fields(
                        result, child_fields, expected_fk, entities
                    )
                    return result

    # Also check IR domain model for explicit relationships
    if ir and hasattr(ir, 'domain_model') and ir.domain_model:
        if hasattr(ir.domain_model, 'relationships'):
            for rel in ir.domain_model.relationships:
                if hasattr(rel, 'source') and rel.source.lower() == parent_lower:
                    result["entity_name"] = rel.target
                    result["entity_class"] = f"{rel.target}Entity"
                    result["fk_field"] = f"{parent_lower}_id"
                    result["found"] = True
                    return result

    return result


def _detect_auto_populated_fields(
    result: Dict[str, Any],
    child_fields: List[Dict],
    parent_fk: str,
    all_entities: List[Dict]
) -> None:
    """
    Bug #203: Detect fields in child entity that should be auto-populated from referenced entities.

    Domain-agnostic detection:
    - Find FK fields OTHER than the parent FK (e.g., product_id in CartItem)
    - Find non-nullable fields that aren't in a typical create request
    - Match field names with fields in the referenced entity (e.g., unit_price ↔ price)

    This enables generating code like:
        ref_entity = await db.get(RefEntity, data['ref_id'])
        child_data['child_field'] = ref_entity.field
    """
    # Price field name patterns (domain-agnostic)
    PRICE_PATTERNS = ('price', 'unit_price', 'amount', 'cost', 'rate', 'fee')

    # Find other FK fields (not the parent FK)
    other_fks = []
    for field in child_fields:
        fname = field.get('name', '').lower()
        if fname.endswith('_id') and fname != 'id' and fname != parent_fk.lower():
            other_fks.append({
                'fk_field': field.get('name'),
                'ref_entity': fname.replace('_id', '').title()
            })

    if not other_fks:
        return

    # Use first other FK as reference entity
    ref_fk = other_fks[0]
    result["reference_fk"] = ref_fk['fk_field']
    result["reference_entity"] = ref_fk['ref_entity']

    # Find non-nullable fields that look like they should come from the referenced entity
    child_field_names = {f.get('name', '').lower() for f in child_fields}

    # Find the referenced entity's fields
    ref_entity_fields = []
    for entity in all_entities:
        if entity.get('name', '').lower() == ref_fk['ref_entity'].lower():
            ref_entity_fields = entity.get('fields', [])
            break

    # Match child fields with ref entity fields
    for child_field in child_fields:
        child_fname = child_field.get('name', '').lower()

        # Skip id, FK fields, and timestamps
        if child_fname in ('id', 'created_at', 'updated_at') or child_fname.endswith('_id'):
            continue

        # Check if this field matches any price pattern
        is_price_field = any(p in child_fname for p in PRICE_PATTERNS)

        if is_price_field:
            # Find corresponding field in ref entity
            for ref_field in ref_entity_fields:
                ref_fname = ref_field.get('name', '').lower()
                if any(p in ref_fname for p in PRICE_PATTERNS):
                    result["auto_populated_fields"].append({
                        'child_field': child_field.get('name'),
                        'ref_field': ref_field.get('name'),
                    })
                    break


def find_workflow_operations(entity_name: str, ir: Any) -> List[Dict[str, Any]]:
    """
    Find workflow operations for an entity from IR flows.

    Returns list of operations with:
        - name: Operation name (e.g., "pay", "cancel", "checkout")
        - precondition_status: Required status before operation
        - postcondition_status: Status after operation
        - affects_stock: Whether operation affects inventory
        - method: HTTP method for endpoint

    Bug #109: Derives operations from IR flows instead of hardcoding.
    Bug #192: Now uses Flow.preconditions/postconditions directly.
    """
    import re
    operations = []

    if not ir or not hasattr(ir, 'behavior_model') or not ir.behavior_model:
        return operations

    entity_lower = entity_name.lower()

    for flow in ir.behavior_model.flows:
        # Check if flow targets this entity
        flow_name = flow.name.lower() if flow.name else ""
        primary_entity = (getattr(flow, 'primary_entity', None) or '').lower()

        if entity_lower in flow_name or entity_lower == primary_entity or any(
            entity_lower in (step.target_entity or "").lower()
            for step in flow.steps
        ):
            operation = {
                "name": flow.name,
                "precondition_status": None,
                "postcondition_status": None,
                "affects_stock": False,
                "method": "POST"
            }

            # Bug #192: Extract from Flow.preconditions/postconditions first
            preconditions = getattr(flow, 'preconditions', []) or []
            postconditions = getattr(flow, 'postconditions', []) or []
            constraint_types = getattr(flow, 'constraint_types', []) or []

            # Check preconditions for status requirements
            for precond in preconditions:
                precond_lower = precond.lower()
                # Match patterns like "status = 'OPEN'" or "cart.status == OPEN"
                match = re.search(r'status\s*[=!<>]+\s*["\']?(\w+)', precond_lower)
                if match:
                    operation["precondition_status"] = match.group(1).upper()
                    break

            # Check postconditions for status changes
            for postcond in postconditions:
                postcond_lower = postcond.lower()
                match = re.search(r'status\s*[=:→]\s*["\']?(\w+)', postcond_lower)
                if match:
                    operation["postcondition_status"] = match.group(1).upper()
                    break

            # Check if operation affects stock
            if 'stock_constraint' in constraint_types or any(
                'stock' in (c or '').lower() for c in constraint_types
            ):
                operation["affects_stock"] = True

            # Fallback: Parse flow steps for status transitions
            if not operation["precondition_status"] or not operation["postcondition_status"]:
                for step in flow.steps:
                    action = (step.action or "").lower()
                    condition = (step.condition or "").lower()

                    # Detect precondition from step condition
                    if 'status' in condition and not operation["precondition_status"]:
                        match = re.search(r'status\s*[=!<>]+\s*["\']?(\w+)', condition)
                        if match:
                            operation["precondition_status"] = match.group(1).upper()

                    # Detect postcondition from step action
                    if 'status' in action and not operation["postcondition_status"]:
                        match = re.search(r'status\s*[=:]\s*["\']?(\w+)', action)
                        if match:
                            operation["postcondition_status"] = match.group(1).upper()

                    # Detect stock/quantity operations (heuristic keywords)
                    if any(kw in action for kw in ['stock', 'inventory', 'quantity', 'decrement', 'increment']):
                        operation["affects_stock"] = True

            operations.append(operation)

    return operations


def _extract_operation_name(flow_name: str, entity_name: str) -> str:
    """
    Extract service method name from IR flow name, removing entity reference.

    Bug #143 Fix: Convert flow names to method names dynamically.
    Bug #166 Fix: Remove parenthetical expressions that create invalid Python identifiers.

    Examples:
        "Pay Order" → "pay"
        "Add Item to Cart" → "add_item"
        "Cancel Order" → "cancel"
        "Checkout Cart" → "checkout"
        "F9: Add Item to Cart" → "add_item"
        "Checkout (Create Order)" → "checkout"
        "Pay (Simulated)" → "pay"

    Args:
        flow_name: Name from IR BehaviorModel flow (e.g., "Pay Order")
        entity_name: Entity this operation belongs to (e.g., "Order")

    Returns:
        Snake_case method name (e.g., "pay")
    """
    if not flow_name:
        return ""

    import re
    name = flow_name.lower()
    entity_lower = entity_name.lower()

    # Bug #166 Fix: Remove parenthetical expressions FIRST
    # "Checkout (Create Order)" → "Checkout", "Pay (Simulated)" → "Pay"
    name = re.sub(r'\s*\([^)]*\)', '', name)

    # Remove flow ID prefixes like "F9: " or "F1: "
    name = re.sub(r'^f\d+:\s*', '', name)

    # Remove entity name variations: "pay order" → "pay", "order pay" → "pay"
    name = name.replace(f" {entity_lower}", "")
    name = name.replace(f"{entity_lower} ", "")
    name = name.replace(f" to {entity_lower}", "")  # "add item to cart" → "add item"
    name = name.replace(f" from {entity_lower}", "")  # "remove item from cart" → "remove item"

    # Bug #165 Fix: Remove trailing prepositions left after entity removal
    # "add item to" → "add item", "remove from" → "remove"
    name = re.sub(r'\s+(to|from|in|at|for)$', '', name.strip())

    # Convert to snake_case: "add item" → "add_item"
    name = re.sub(r'\s+', '_', name.strip())

    # Clean up multiple underscores and any remaining invalid characters
    name = re.sub(r'[^a-z0-9_]', '', name)  # Only keep valid Python identifier chars
    name = re.sub(r'_+', '_', name).strip('_')

    return name


def _generate_workflow_method_body(
    entity_name: str,
    op_name: str,
    flow_name: str,
    precondition_status: str,
    postcondition_status: str,
    affects_stock: bool,
    needs_data: bool,
    status_field_name: str,
    child_info: Dict[str, Any] = None
) -> str:
    """
    Generate method body with real behavior logic.

    Replaces TODO stubs with actual:
    - Status precondition checks
    - Stock invariant checks
    - Status transitions
    - Child entity creation (Bug #200 Fix)
    - Proper error handling

    Bug #200 Fix: Now receives child_info to generate actual child entity creation.
    """
    import re
    entity_lower = entity_name.lower()
    entity_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    status_field = status_field_name or 'status'
    child_info = child_info or {}

    # Method signature
    if needs_data:
        sig = f'''
    async def {op_name}(self, id: UUID, data: dict) -> Optional[{entity_name}Response]:'''
    else:
        sig = f'''
    async def {op_name}(self, id: UUID) -> Optional[{entity_name}Response]:'''

    # Docstring
    doc = f'''
        """
        {flow_name} operation for {entity_name}.

        Generated from IR BehaviorModel flow with behavior guards.
        """'''

    # Get entity
    get_entity = f'''
        db_obj = await self.repo.get(id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="{entity_name} not found")'''

    # Precondition check - Bug #201 Fix: Case-insensitive status comparison
    # Pydantic Literal may use lowercase ('open') while IR/flows use uppercase ('OPEN')
    precond = ""
    if precondition_status:
        precond = f'''

        # Behavior guard: Check precondition status (case-insensitive)
        current_status = getattr(db_obj, '{status_field}', None)
        if current_status and current_status.upper() != '{precondition_status}'.upper():
            raise HTTPException(
                status_code=422,
                detail=f"{entity_name} must be in '{precondition_status}' status, got '{{current_status}}'"
            )'''

    # Stock check for operations that affect stock
    # Domain-agnostic stock check: Uses fields from IR, not hardcoded names
    stock_check = ""
    if affects_stock and needs_data:
        # The actual field names should come from IR.stock_fields or entity.quantity_field
        stock_check = f'''

        # Behavior guard: Check stock invariant (fields from IR)
        # TODO: Replace hardcoded 'quantity' with ir.get_quantity_field(entity)
        quantity_field = getattr(self, '_quantity_field', 'quantity')
        if quantity_field in data:
            await self.validator.check_stock_invariant(db_obj, data.get(quantity_field, 1))'''

    # Bug #200 Fix: Generate business logic for add_item operations
    # When op_name contains 'add_item' and we have child_info, generate child entity creation
    business_logic = ""
    is_add_item_op = 'add_item' in op_name or ('add' in op_name and 'item' in op_name.lower())

    if is_add_item_op and child_info.get("found") and needs_data:
        child_entity_class = child_info.get("entity_class", f"{entity_name}ItemEntity")
        child_fk_field = child_info.get("fk_field", f"{entity_snake}_id")
        child_entity_name = child_info.get("entity_name", f"{entity_name}Item")

        # Bug #203: Get auto-populated fields from referenced entity
        auto_fields = child_info.get("auto_populated_fields", [])
        ref_fk = child_info.get("reference_fk")
        ref_entity = child_info.get("reference_entity")

        # Build the fetch-from-reference code if needed
        fetch_ref_code = ""
        auto_populate_code = ""

        if auto_fields and ref_fk and ref_entity:
            ref_entity_class = f"{ref_entity}Entity"
            fetch_ref_code = f'''
        # Bug #203 Fix: Fetch referenced entity for auto-populated fields
        from src.models.entities import {ref_entity_class}
        from sqlalchemy import select
        ref_id = data.get('{ref_fk}')
        if not ref_id:
            raise HTTPException(status_code=422, detail="Missing {ref_fk}")
        ref_stmt = select({ref_entity_class}).where({ref_entity_class}.id == ref_id)
        ref_result = await self.db.execute(ref_stmt)
        ref_obj = ref_result.scalar_one_or_none()
        if not ref_obj:
            raise HTTPException(status_code=422, detail="{ref_entity} not found")
'''
            # Generate auto-populate assignments
            for af in auto_fields:
                child_field = af.get('child_field')
                ref_field = af.get('ref_field')
                auto_populate_code += f"        child_data['{child_field}'] = ref_obj.{ref_field}\n"

        business_logic = f'''

        # Bug #200 Fix: Create child entity from IR-derived relationship
        from src.models.entities import {child_entity_class}
{fetch_ref_code}
        # Build child entity data with parent FK
        child_data = dict(data)
        child_data['{child_fk_field}'] = id
{auto_populate_code}
        # Create the child entity
        child_obj = {child_entity_class}(**child_data)
        self.db.add(child_obj)
        await self.db.flush()
        logger.info(f"Created {child_entity_name} for {entity_name} id={{str(id)}}")'''

    # Status transition
    transition = ""
    if postcondition_status:
        transition = f'''

        # Apply status transition
        db_obj.{status_field} = '{postcondition_status}'
        await self.db.flush()'''

    # Return
    ret = f'''

        await self.db.refresh(db_obj)
        logger.info(f"{entity_name} {op_name}: id={{str(id)}}")
        return {entity_name}Response.model_validate(db_obj)
'''

    return sig + doc + get_entity + precond + stock_check + business_logic + transition + ret


def get_status_transition_code(
    entity_name: str,
    status_field: Dict[str, Any],
    from_status: str,
    to_status: str,
    error_code: int = 400
) -> str:
    """
    Generate status validation and transition code dynamically.

    Bug #109: Generates code using actual field names from IR.
    """
    field_name = status_field.get("field_name", "status")

    return f'''
        if db_{entity_name.lower()}.{field_name} != "{from_status}":
            raise HTTPException(
                status_code={error_code},
                detail=f"Cannot perform operation on {entity_name.lower()} with status {{db_{entity_name.lower()}.{field_name}}}. Required status: {from_status}."
            )
'''


def generate_entities(entities: List[Dict[str, Any]], validation_ground_truth: dict = None) -> str:
    """
    Generate SQLAlchemy ORM entities dynamically from entity fields.

    Args:
        entities: List of entity dicts with 'name', 'plural', and 'fields'
        validation_ground_truth: Optional validation ground truth with enforcement info

    Returns:
        Complete entities.py code
    """
    code = '''"""
SQLAlchemy ORM Models

Database entity definitions with proper table names and columns.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from src.core.database import Base


'''

    # Type mapping from spec types to SQLAlchemy types
    type_mapping = {
        'UUID': 'UUID(as_uuid=True)',
        'uuid': 'UUID(as_uuid=True)',
        'str': 'String(255)',
        'string': 'String(255)',
        'int': 'Integer',
        'integer': 'Integer',
        'Decimal': 'Numeric(10, 2)',
        'decimal': 'Numeric(10, 2)',
        'float': 'Numeric(10, 2)',
        'datetime': 'DateTime(timezone=True)',
        'bool': 'Boolean',
        'boolean': 'Boolean',
        'text': 'Text',
    }

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_plural = entity.get('plural', f'{entity_name}s').lower()
        fields = entity.get('fields', [])

        # Bug #164 Fix: Get pattern-aware overrides from learned anti-patterns
        field_overrides = get_field_overrides_for_entity(entity_name)
        if field_overrides and PATTERN_AWARE_AVAILABLE:
            logger.info(f"🎓 AST Learning: {len(field_overrides)} field overrides for {entity_name} from learned patterns")

        code += f'''
class {entity_name}Entity(Base):
    """SQLAlchemy model for {entity_plural} table."""

    __tablename__ = "{entity_plural}"


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
'''

        # Track generated relationships to avoid duplicates
        generated_rels = set()
        generated_targets = set()

        # Generate explicit relationships from IR
        relationships = entity.get('relationships', [])
        for rel in relationships:
            # Handle both dict and object access
            if isinstance(rel, dict):
                r_name = rel.get('field_name')
                r_target = rel.get('target_entity')
                r_back_populates = rel.get('back_populates')
                r_type = rel.get('type')
            else:
                r_name = getattr(rel, 'field_name', '')
                r_target = getattr(rel, 'target_entity', '')
                r_back_populates = getattr(rel, 'back_populates', None)
                r_type = getattr(rel, 'type', '')

            if not r_name or not r_target:
                continue

            # Normalize target name (ensure Entity suffix)
            target_cls = f"{r_target}Entity" if not r_target.endswith('Entity') else r_target
            
            # Default lazy load
            lazy = "select"
            if r_type == "one_to_many" or r_type == "many_to_many":
                lazy = "selectin"
            
            # Check overrides
            if r_name in field_overrides:
                override = field_overrides[r_name]
                if 'lazy' in override:
                    lazy = override['lazy']
            
            rel_def = f'    {r_name} = relationship("{target_cls}", lazy="{lazy}"'
            if r_back_populates:
                rel_def += f', back_populates="{r_back_populates}"'
            rel_def += ')\n'
            
            code += rel_def
            generated_rels.add(r_name)
            generated_targets.add(target_cls)



        # Generate columns dynamically from entity fields
        # Skip system fields that are added automatically (id, created_at, updated_at)
        for field in fields:
            # Handle both dict and object access for field properties
            if isinstance(field, dict):
                f_name = field.get('name', '')
                f_type = field.get('type', 'str')
                f_required = field.get('required', False)
                f_default = field.get('default', None)
                f_constraints = field.get('constraints', [])
            else:
                f_name = getattr(field, 'name', '')
                f_type = getattr(field, 'type', 'str')
                f_required = getattr(field, 'required', False)
                f_default = getattr(field, 'default', None)
                f_constraints = getattr(field, 'constraints', [])

            field_name = normalize_field_name(f_name)  # Fix #3: normalize field names

            # Skip system fields - they are added separately
            if field_name in ['id', 'created_at', 'updated_at']:
                continue

            field_type = f_type
            is_required = f_required
            has_default = f_default is not None
            constraints = f_constraints

            # NEW: Check for immutable enforcement from validation ground truth
            enforcement = _get_enforcement_for_field(entity_name, field_name, validation_ground_truth)
            is_immutable = enforcement and enforcement.get('enforcement_type') == 'immutable'

            # Map field type to SQLAlchemy type
            sql_type = type_mapping.get(field_type, 'String(255)')

            # Determine nullable
            nullable = not is_required

            # Bug #164 Fix: Apply learned pattern overrides (e.g., IntegrityError → nullable=True)
            if field_name in field_overrides:
                override = field_overrides[field_name]
                if 'nullable' in override:
                    nullable = override['nullable']
                    logger.info(f"🎓 Pattern Override: {entity_name}.{field_name} nullable={nullable} (learned from previous IntegrityError)")

            # Handle foreign keys (fields ending with _id)
            if field_name.endswith('_id') and field_type == 'UUID':
                # Infer parent table name: cart_id -> carts
                parent_snake = field_name[:-3]
                # Simple pluralization (add 's') - robust enough for standard naming
                # Ideally we'd look up the entity plural, but this is a safe heuristic for now
                parent_table = f"{parent_snake}s"
                
                # Foreign key reference
                code += f'    {field_name} = Column(UUID(as_uuid=True), ForeignKey("{parent_table}.id"), nullable={nullable})\n'
            else:
                # Regular column
                column_def = f'    {field_name} = Column({sql_type}'

                # Add nullable
                column_def += f', nullable={nullable}'

                # Add unique if constraint specifies it (NOT based on field name)
                # NOTE: Hardcoded field_name == 'email' REMOVED - Phase: Hardcoding Elimination
                # Unique constraint should come from IR/spec constraints
                constraint_strs = [str(c).lower() for c in constraints] if constraints else []
                if any('unique' in c for c in constraint_strs):
                    column_def += ', unique=True'

                # Add default if exists
                if has_default and f_default != '...':
                    if field_type == 'datetime':
                        column_def += ', default=lambda: datetime.now(timezone.utc)'
                    elif field_type in ['str', 'string']:
                        column_def += f', default="{f_default}"'
                    elif field_type in ['int', 'integer', 'Decimal', 'decimal', 'float']:
                        column_def += f', default={f_default}'
                    elif field_type in ['bool', 'boolean']:
                        # Capitalize boolean strings (true/false → True/False)
                        if isinstance(f_default, str):
                            bool_value = 'True' if f_default.lower() == 'true' else 'False'
                            column_def += f', default={bool_value}'
                        else:
                            column_def += f', default={f_default}'

                # NEW: Add onupdate=None for immutable fields
                if is_immutable:
                    logger.info(f"🔒 Adding onupdate=None to immutable field {entity_name}.{field_name}")
                    column_def += ', onupdate=None'

                column_def += ')\n'
                code += column_def

        # Always add created_at for consistency
        code += '    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))\n'

        # Generate relationships (Forward: Many-to-One)
        for field in fields:
            # Handle both dict and object access
            if isinstance(field, dict):
                f_name = field.get('name', '')
                f_type = field.get('type', 'str')
            else:
                f_name = getattr(field, 'name', '')
                f_type = getattr(field, 'type', 'str')

            field_name = normalize_field_name(f_name)
            if field_name.endswith('_id') and f_type == 'UUID':
                # Infer parent name: cart_id -> Cart
                parent_snake = field_name[:-3]
                parent_name = ''.join(word.capitalize() for word in parent_snake.split('_'))
                
                # Check if parent entity exists in the list
                parent_exists = any(e.get('name') == parent_name for e in entities)
                if parent_exists:
                    # Determine back_populates name on the parent
                    # Agnostic approach: Use the plural of this entity (e.g. {Entity}Item -> {entity}_items)
                    back_populates = entity_plural

                    # Check for lazy_load override
                    lazy = "select" # Default
                    if field_name in field_overrides: # Check override on the FK field
                        override = field_overrides[field_name]
                        if 'lazy' in override:
                            lazy = override['lazy']
                            logger.info(f"🎓 Pattern Override: {entity_name}.{parent_snake} lazy={lazy} (learned from AttributeError)")
                    
                    # Add relationship if not already generated explicitly
                    target_cls = f"{parent_name}Entity"
                    if parent_snake not in generated_rels and target_cls not in generated_targets:
                        # e.g. cart = relationship("CartEntity", back_populates="cart_items", lazy="select")
                        code += f'    {parent_snake} = relationship("{parent_name}Entity", back_populates="{back_populates}", lazy="{lazy}")\n'
                        generated_rels.add(parent_snake)
                        generated_targets.add(target_cls)

        # Generate relationships (Backward: One-to-Many)
        # Scan other entities to see if they point to us
        for other_entity in entities:
            other_name = other_entity.get('name')
            if other_name == entity_name:
                continue
            
            other_fields = other_entity.get('fields', [])
            for f in other_fields:
                # Handle both dict and object access
                if isinstance(f, dict):
                    raw_name = f.get('name', '')
                else:
                    raw_name = getattr(f, 'name', '')
                
                f_name = normalize_field_name(raw_name)
                # If other entity has our_id (e.g. {Parent}Item has {parent}_id)
                target_fk = f"{entity_name.lower()}_id"
                # Handle snake_case entity names if needed, but simple lower() covers most
                # e.g. Cart -> cart_id. Order -> order_id.
                
                # Convert entity_name to snake_case for the FK check
                import re
                ent_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
                target_fk_snake = f"{ent_snake}_id"

                if f_name == target_fk or f_name == target_fk_snake:
                    # Found a child entity!
                    # Determine collection name
                    # Agnostic approach: Use the plural of the child entity (e.g. {Child} -> {child}s)
                    collection_name = other_entity.get('plural', f"{other_name}s").lower()

                    # Back reference name on the child (derived from FK field)
                    # e.g. {Child} has '{parent}' relationship
                    back_populates = ent_snake

                    # Check for lazy_load override on the collection
                    lazy = "selectin" # Default for collections (async friendly)
                    if collection_name in field_overrides:
                        override = field_overrides[collection_name]
                        if 'lazy' in override:
                            lazy = override['lazy']
                            logger.info(f"🎓 Pattern Override: {entity_name}.{collection_name} lazy={lazy} (learned from AttributeError)")
                    
                    # Add relationship if not already generated explicitly
                    target_cls = f"{other_name}Entity"
                    if collection_name not in generated_rels and target_cls not in generated_targets:
                        code += f'    {collection_name} = relationship("{other_name}Entity", back_populates="{back_populates}", lazy="{lazy}")\n'
                        generated_rels.add(collection_name)
                        generated_targets.add(target_cls)

        # Generate __repr__ method
        # NOTE: Hardcoded field names REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
        # Use first non-system field as display field (no preference for specific names)
        display_field = None
        for field in fields:
            # Handle both dict and object access
            if isinstance(field, dict):
                f_name = field.get('name', '')
            else:
                f_name = getattr(field, 'name', '')
            
            # Skip system fields
            if f_name not in ['id', 'created_at', 'updated_at']:
                display_field = f_name
                break

        if display_field:
            code += f'''
    def __repr__(self):
        return f"<{entity_name} {{self.id}}: {{getattr(self, '{display_field}', 'N/A')}}>"
'''
        else:
            code += f'''
    def __repr__(self):
        return f"<{entity_name} {{self.id}}>"
'''

    # Ensure typing imports include optional Literal helper if used
    import re
    need_literal = "Literal[" in code
    # Always include Literal to avoid missing import after post-generation repairs
    import_line = "from typing import List, Optional, Literal"
    code = re.sub(r'^from typing import [^\n]+', import_line, code, count=1, flags=re.MULTILINE)

    return code.strip()


def generate_config() -> str:
    """
    Generate Pydantic settings configuration with proper defaults.

    Returns:
        Complete config.py code
    """
    return '''"""
Application Configuration

Uses pydantic-settings for type-safe configuration with .env support.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore unknown environment variables
    )

    # Application
    app_name: str = "API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/api_db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Logging
    log_level: str = "INFO"

    # Security
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "100/minute"

    # Optional - Redis configuration (if needed)
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
'''


def _get_enforcement_for_field(entity_name: str, field_name: str, validation_ground_truth: dict) -> dict:
    """
    Get enforcement strategy for a field from validation ground truth.

    Args:
        entity_name: Name of the entity
        field_name: Name of the field (or 'attribute' in ApplicationIR terms)
        validation_ground_truth: Validation ground truth from ApplicationIR

    Returns:
        Dict with enforcement_type, enforcement_code, applied_at or None if not found
    """
    if not validation_ground_truth or 'rules' not in validation_ground_truth:
        return None

    # Search for matching rule
    for rule in validation_ground_truth['rules']:
        rule_entity = rule.get('entity', '')
        rule_field = rule.get('attribute', '')  # ApplicationIR uses 'attribute'

        if rule_entity == entity_name and rule_field == field_name:
            # Found matching rule
            enforcement_type = rule.get('enforcement_type', 'description')
            enforcement_code = rule.get('enforcement_code')
            applied_at = rule.get('applied_at', [])

            logger.info(f"🎯 Found enforcement for {entity_name}.{field_name}: type={enforcement_type}")

            return {
                'enforcement_type': enforcement_type,
                'enforcement_code': enforcement_code,
                'applied_at': applied_at,
                'rule_type': rule.get('type', ''),
                'condition': rule.get('condition', '')
            }

    return None


def _should_exclude_from_create(entity_name: str, field_name: str, validation_constraints: dict) -> bool:
    """
    Determine if a field should be excluded from Create schema.

    Args:
        entity_name: Name of the entity
        field_name: Name of the field
        validation_constraints: Dictionary of validation constraints from ground truth

    Returns:
        True if field should be excluded from Create schema
    """
    # Always exclude server-managed fields
    if field_name in ['id', 'created_at', 'updated_at']:
        return True

    # Check validation constraints from ground truth
    constraints = validation_constraints.get((entity_name, field_name), [])
    for constraint in constraints:
        constraint_str = str(constraint).lower()
        # Exclude auto-calculated fields (server computes them)
        if any(kw in constraint_str for kw in ['auto-calculated', 'auto_calculated', 'computed', 'sum_of']):
            return True
        # Exclude auto-generated read-only fields
        if field_name in ['registration_date', 'creation_date'] and 'read' in constraint_str:
            return True

    # Bug #127 Fix: unit_price in *Item entities is auto-calculated from Product.price
    # This is a common e-commerce pattern where the price is captured from product at add time
    entity_lower = entity_name.lower()
    if entity_lower.endswith('item') and field_name == 'unit_price':
        return True

    # Bug #127 Fix: Parent FK in *Item entities is auto-set from route parameter
    # The parent_id comes from the route path (/parents/{id}/items), not request body
    # Domain-agnostic: Exclude parent FKs (first *_id field), keep item reference FK (second *_id)
    if entity_lower.endswith('item') and field_name.endswith('_id'):
        # The parent FK is excluded, but the item reference FK (e.g., product_id) is kept
        # Heuristic: Keep FKs that reference non-parent entities (typically the "what" being added)
        # Parent FK is usually first alphabetically or matches parent entity name
        parent_name_guess = entity_lower.replace('item', '')  # cartitem -> cart
        if parent_name_guess and field_name.startswith(parent_name_guess):
            return True  # This is the parent FK, exclude it

    return False


def _should_exclude_from_update(entity_name: str, field_name: str, validation_constraints: dict) -> bool:
    """
    Determine if a field should be excluded from Update schema.
    
    Args:
        entity_name: Name of the entity
        field_name: Name of the field
        validation_constraints: Dictionary of validation constraints from ground truth
    
    Returns:
        True if field should be excluded from Update schema
    """
    # Always exclude server-managed fields
    if field_name in ['id', 'created_at', 'updated_at']:
        return True
    
    # Check validation constraints from ground truth
    constraints = validation_constraints.get((entity_name, field_name), [])
    for constraint in constraints:
        constraint_str = str(constraint).lower()
        # Exclude read-only fields (immutable after creation)
        if any(kw in constraint_str for kw in ['read-only', 'read_only', 'immutable']):
            return True
        # Exclude snapshot fields (captured at creation, immutable)
        if any(kw in constraint_str for kw in ['snapshot_at', 'snapshot']):
            return True
        # Exclude auto-calculated fields (server computes them)
        if any(kw in constraint_str for kw in ['auto-calculated', 'auto_calculated', 'computed', 'sum_of']):
            return True

    # NOTE: Hardcoded fallbacks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Exclusions now come exclusively from validation_constraints (ApplicationIR or GT)

    return False


def generate_schemas(entities: List[Dict[str, Any]], validation_ground_truth: Dict[str, Any] = None, endpoint_schemas: List[Dict[str, Any]] = None) -> str:
    """
    Generate Pydantic schemas for request/response validation.

    Args:
        entities: List of entity dicts with 'name', 'plural', and 'fields'
        validation_ground_truth: Optional validation ground truth from spec parser
        endpoint_schemas: Optional list of endpoint-specific schemas from IR (Bug #200)
                         Each schema has 'name' and 'fields' (list of field dicts)

    Returns:
        Complete schemas.py code
    """
    code = '''"""
Pydantic Request/Response Schemas

Type-safe data validation for API endpoints.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import List, Optional, Literal
from decimal import Decimal


class BaseSchema(BaseModel):
    """Base schema with UUID-friendly JSON encoding."""

    model_config = ConfigDict(
        json_encoders={UUID: str},
        from_attributes=True,
    )


'''
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    # NOTE: Hardcoded domain-specific classes REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Item schemas are now generated dynamically:
    # 1. From ApplicationIR.domain_model.entities (all child entities derived from IR)
    # 2. From validation_ground_truth synthetic_entities (if validation rules reference them)
    # 3. Generic ItemSchema fallback is added below if needed

    # Track whether we need generic item fallback (will be set after synthetic_entities processing)
    _needs_item_fallback = False

    literal_used = False

    # Build validation constraint lookup from ground truth
    validation_lookup = {}  # {(entity, field): constraint}
    validation_constraints = defaultdict(list)  # {(entity, field): [constraints]}
    validation_entities = {}  # entity -> list of (field, constraint)
    if validation_ground_truth:
        # Handle legacy SpecRequirements format
        if 'validations' in validation_ground_truth:
            for val_id, val_data in validation_ground_truth['validations'].items():
                entity_name = val_data.get('entity')
                field_name = normalize_field_name(val_data.get('field') or '')  # Fix #3
                constraint = val_data.get('constraint')
                if entity_name and field_name and constraint:
                    validation_lookup[(entity_name, field_name)] = constraint
                    if constraint not in validation_constraints[(entity_name, field_name)]:
                        validation_constraints[(entity_name, field_name)].append(constraint)
                    validation_entities.setdefault(entity_name, []).append((field_name, constraint))
                    logger.debug(f"📋 Validation ground truth (legacy): {entity_name}.{field_name} → {constraint}")

        # Handle ApplicationIR format (list of rules)
        if 'rules' in validation_ground_truth:
            for rule in validation_ground_truth['rules']:
                # Handle both dict and object access
                if isinstance(rule, dict):
                    entity_name = rule.get('entity')
                    field_name = normalize_field_name(rule.get('attribute') or '')  # Fix #3
                    v_type = rule.get('type', '')
                    condition = rule.get('condition', '')
                else:
                    entity_name = getattr(rule, 'entity', None)
                    field_name = normalize_field_name(getattr(rule, 'attribute', None) or '')  # Fix #3
                    v_type = getattr(rule, 'type', '')
                    condition = getattr(rule, 'condition', '')

                # Construct constraint string
                constraint = f"{v_type}"
                if condition:
                    constraint += f": {condition}"
                
                if entity_name and field_name:
                    if constraint not in validation_constraints[(entity_name, field_name)]:
                        validation_constraints[(entity_name, field_name)].append(constraint)
                    validation_entities.setdefault(entity_name, []).append((field_name, constraint))
                    logger.debug(f"📋 Validation ground truth (IR): {entity_name}.{field_name} → {constraint}")

    # Type mapping from spec types to Python/Pydantic types
    type_mapping = {
        'UUID': 'UUID',
        'uuid': 'UUID',
        'str': 'str',
        'string': 'str',
        'int': 'int',
        'integer': 'int',
        'float': 'float',
        'Decimal': 'Decimal',
        'decimal': 'Decimal',
        'bool': 'bool',
        'boolean': 'bool',
        'datetime': 'datetime',
        'date': 'datetime',
        'enum': 'str',   # fallback; Literal applied when values provided via constraints
        'list': 'List[str]',   # safe default when item type unknown
        'array': 'List[str]',
    }

    # Create synthetic entities from validation ground truth (domain-agnostic: any child entity)
    existing_entity_names = {e.get('name', 'Unknown') for e in entities}
    synthetic_entities = []

    def _infer_type(field_name: str, constraint: str) -> str:
        """
        Infer field type from constraint text or field name pattern.

        NOTE: Phase: Hardcoding Elimination (Nov 25, 2025)
        - FIRST: Try to extract type from constraint text (IR source)
        - SECOND: Use generic patterns (not domain-specific names)
        """
        constraint_lower = (constraint or "").lower()
        name_lower = field_name.lower()

        # PRIORITY 1: Extract type from constraint text (from IR)
        if 'uuid' in constraint_lower:
            return 'UUID'
        if 'integer' in constraint_lower or 'int' in constraint_lower:
            return 'int'
        if 'decimal' in constraint_lower or 'numeric' in constraint_lower or 'float' in constraint_lower:
            return 'Decimal'
        if 'boolean' in constraint_lower or 'bool' in constraint_lower:
            return 'bool'
        if 'datetime' in constraint_lower or 'timestamp' in constraint_lower:
            return 'datetime'

        # PRIORITY 2: Generic patterns from field name (not domain-specific)
        if name_lower == 'id' or name_lower.endswith('_id'):
            return 'UUID'

        # Default to string (safest)
        return 'str'

    for ent_name, fields_list in validation_entities.items():
        if ent_name not in existing_entity_names:
            synthetic = {
                'name': ent_name,
                'plural': f"{ent_name}s",
                'fields': []
            }
            seen_fields = set()
            for fname, constraint in fields_list:
                if fname in seen_fields:
                    continue
                seen_fields.add(fname)
                ftype = _infer_type(fname, constraint)
                synthetic['fields'].append({
                    'name': fname,
                    'type': ftype,
                    'required': True,
                    'constraints': [constraint],
                })
            synthetic_entities.append(synthetic)

    if synthetic_entities:
        logger.info(f"🧩 Adding synthetic entities from validation ground truth: {[e['name'] for e in synthetic_entities]}")
        entities = list(entities) + synthetic_entities

    # Sort entities so that child entities (ending in 'Item') are defined before parents
    def _entity_priority(ent: Dict[str, Any]) -> int:
        name = str(ent.get('name', '')).lower()
        if name.endswith('item'):
            return 0
        return 1

    entities = sorted(entities, key=_entity_priority)

    # NOTE: Domain-specific names REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Generic item schema detection: entities that need item schemas are detected by:
    # 1. Having a field of type List[*] (e.g., items: List[{Entity}Item])
    # 2. Their corresponding *Item entity not being in the entity list
    entity_names_lower = {str(e.get('name', '')).lower() for e in entities}

    # Detect entities that have List fields (potential parent entities needing item schemas)
    entities_with_list_fields = set()
    for entity in entities:
        fields = entity.get('fields', []) or []
        for field in fields:
            if hasattr(field, 'type'):
                ft = str(getattr(field, 'type', '')).lower()
            elif isinstance(field, dict):
                ft = str(field.get('type', '')).lower()
            else:
                ft = ''
            if 'list' in ft or 'array' in ft:
                entities_with_list_fields.add(str(entity.get('name', '')).lower())
                break

    # Check if corresponding *Item entities exist for parent entities
    missing_item_schemas = []
    for parent_name in entities_with_list_fields:
        item_name = f"{parent_name}item"
        if item_name not in entity_names_lower:
            missing_item_schemas.append(parent_name)

    # Add generic ItemSchema fallback if any parent entity needs item schemas
    if missing_item_schemas:
        logger.info(f"📦 Adding generic ItemSchema fallback for: {missing_item_schemas}")
        code += '''from typing import Dict, Any

# Generic item schema - specific item entities should come from ApplicationIR
ItemSchema = Dict[str, Any]


'''
        # Generate generic item classes for each missing item entity
        for parent_name in missing_item_schemas:
            item_class_name = f"{parent_name.title()}Item"
            code += f'''class {item_class_name}(BaseModel):
    """Generic item for {parent_name} - fields should come from ApplicationIR."""
    model_config = ConfigDict(extra="allow")


'''

    # NOTE: gt_defaults for constraint hardening REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Constraints now come exclusively from:
    # 1. ApplicationIR.validation_model.rules (from spec parsing)
    # 2. validation_constraints parameter (from ground truth)
    # If constraints are missing, they should be added to the spec, not hardcoded here.

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_lower = entity_name.lower()
        fields_list = entity.get('fields', []) or []

        # If ground truth has constraints for fields not present in the spec, synthesize those fields
        existing_field_names = {f.name if hasattr(f, "name") else f.get("name") for f in fields_list}
        missing_from_gt = []
        for (gt_entity, gt_field), gt_cons in validation_constraints.items():
            if gt_entity == entity_name and gt_field not in existing_field_names:
                missing_from_gt.append((gt_field, gt_cons))
        for fname, gt_cons in missing_from_gt:
            inferred_type = _infer_type(fname, ",".join(gt_cons))
            required_flag = any(c == 'required' for c in gt_cons)
            fields_list.append({
                'name': fname,
                'type': inferred_type,
                'required': required_flag,
                'default': None,
                'constraints': list(gt_cons),
            })
            existing_field_names.add(fname)

        # Build field definitions for Pydantic
        pydantic_fields = []
        for field_obj in fields_list:
            # Extract field attributes
            if hasattr(field_obj, 'name'):
                field_name = normalize_field_name(field_obj.name)  # Fix #3
                field_type = getattr(field_obj, 'type', 'str')
                required = getattr(field_obj, 'required', True)
                field_default = getattr(field_obj, 'default', None)
                description = getattr(field_obj, 'description', '')
                constraints = getattr(field_obj, 'constraints', [])
            else:
                # Fallback for dict-based fields
                field_name = normalize_field_name(field_obj.get('name', 'unknown'))  # Fix #3
                field_type = field_obj.get('type', 'str')
                required = field_obj.get('required', True)
                field_default = field_obj.get('default', None)
                description = field_obj.get('description', '')
                constraints = field_obj.get('constraints', [])

            # Ensure constraints is a mutable list
            if constraints is None:
                constraints = []
            elif not isinstance(constraints, list):
                constraints = list(constraints)

            # Bug #164 Fix: Apply learned pattern overrides to Schemas too
            # If ORM is made nullable OR explicitly optional, Schema should be Optional
            field_overrides = get_field_overrides_for_entity(entity_name) if PATTERN_AWARE_AVAILABLE else {}
            if field_name in field_overrides:
                override = field_overrides[field_name]
                if ('nullable' in override and override['nullable']) or \
                   ('optional' in override and override['optional']):
                    required = False
                    field_default = None
                    logger.info(f"🎓 Schema Override: {entity_name}.{field_name} made Optional (learned from patterns)")

            # NOTE: Hardening constraint injection REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Constraints now come from validation_constraints parameter only

            # Map type to Python type
            python_type = type_mapping.get(field_type, field_type)

            # Fix #4: Detect relationship fields (e.g., {Parent}.items → List[{Parent}ItemResponse])
            # Check if field name suggests a relationship and corresponding entity exists
            if field_name == 'items':
                # Construct potential item entity name: Order → OrderItem
                item_entity_name = f"{entity_name}Item"
                if item_entity_name.lower() in entity_names_lower:
                    python_type = f"List[{item_entity_name}Response]"
                    required = False
                    field_default = []
                    logger.info(f"🔗 Detected relationship field {entity_name}.{field_name} → List[{item_entity_name}Response]")

            # Special-case server-managed fields: make them optional on input schemas
            if field_name in ['id', 'created_at']:
                required = False
                field_default = None
                # Remove min/max constraints to avoid blocking creates
                constraints = [c for c in constraints if not str(c).startswith(('min_', 'max_'))]

            # Handle list/array with explicit item type e.g., list[{Child}] or List[{Child}]
            ft_str = str(field_type)
            ft_lower = ft_str.lower()
            if ft_lower.startswith('list[') or ft_lower.startswith('array['):
                inner = ft_str[ft_str.find('[') + 1: ft_str.rfind(']')].strip()
                inner_mapped = type_mapping.get(inner, inner or 'str')
                base_inner = {'uuid', 'str', 'int', 'float', 'decimal', 'bool', 'datetime'}
                if isinstance(inner_mapped, str) and inner_mapped.lower() not in base_inner and not inner_mapped.startswith('List['):
                    inner_mapped = 'str'
                python_type = f"List[{inner_mapped}]"

            # Normalize unknown types to safe defaults
            base_types = {'uuid', 'str', 'int', 'float', 'decimal', 'bool', 'datetime', 'list', 'dict'}
            if isinstance(python_type, str) and python_type.lower() not in base_types and not python_type.startswith('List['):
                python_type = 'str'

            # Detect enum constraints (format: enum=VAL1,VAL2) or enum type
            enum_values = None
            enum_from_constraint = False
            # NOTE: Hardcoded enums for cart/order REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Enums now come exclusively from constraints or field type definition
            if ft_lower.startswith('enum'):
                # Try to parse inline enum values: enum["OPEN","CLOSED"] or enum OPEN,CLOSED
                import re
                match = re.search(r'enum[^\w\d]*[\[\(]?([^\]\)]*)', ft_str, re.IGNORECASE)
                if match:
                    raw_vals = match.group(1)
                    if raw_vals:
                        enum_values = [v.strip().strip('"').strip("'") for v in raw_vals.split(',') if v.strip()]
            if constraints:
                for constraint in list(constraints):
                    if isinstance(constraint, str) and constraint.lower().startswith('enum='):
                        enum_values = [v.strip() for v in constraint.split('=', 1)[1].split(',') if v.strip()]
                        enum_from_constraint = True
                        constraints.remove(constraint)
                        break

            if enum_values:
                literal_vals = ', '.join([f'"{v}"' for v in enum_values])
                python_type = f'Literal[{literal_vals}]'
                literal_used = True
                # Mark as required by default for enums
                required = True
            else:
                # If enum was declared without values, keep it as str to avoid NameError
                if ft_lower.startswith('enum'):
                    python_type = 'str'

            # Check validation ground truth first (highest priority)
            gt_constraints = validation_constraints.get((entity_name, field_name), [])
            required_from_gt = any(c == 'required' for c in gt_constraints)
            for gt_constraint in gt_constraints:
                logger.info(f"✅ Using validation ground truth for {entity_name}.{field_name}: {gt_constraint}")
                if gt_constraint not in constraints:
                    constraints.append(gt_constraint)

            # NOTE: Hardcoded field_name == 'items' REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # List detection now based ONLY on type, not field name
            # If this is a list type field, use generic type. Relationships should come from IR.
            if ft_lower.startswith('list') or ft_lower.startswith('array'):
                # Use generic list type - specific item types should be defined via IR relationships
                if python_type not in ('List[Dict[str, Any]]',) and not python_type.startswith('List['):
                    python_type = 'List[Dict[str, Any]]'
                # Allow empty list on create
                required = required_from_gt
                field_default = None if required_from_gt else (field_default or [])
                # Remove any injected min_items to avoid 422 on empty lists
                constraints = [c for c in constraints if not str(c).startswith('min_items')]

            # NOTE: Hardcoded status defaults for cart/order REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Status field defaults should come from spec/IR field_default, not hardcoded here
            # If a status field needs a default, define it in the spec

            # If ground truth requires the field, drop defaults to force Field(...)
            if required_from_gt:
                required = True
                field_default = None

            # Build Field() constraints based on type and constraints list
            field_constraints = {}  # Use dict to track constraint types and avoid duplicates

            # Parse constraints from spec first (to get the authoritative values)
            for constraint in constraints:
                if isinstance(constraint, str):
                    constraint = constraint.strip()
                    # NORMALIZATION: Convert to lowercase and replace spaces with underscores
                    # This handles variations like "email format" vs "email_format"
                    constraint_normalized = constraint.lower().replace(' ', '_')

                    # Capture enum constraints and convert to Literal to avoid leaking into Field kwargs
                    if constraint_normalized.startswith('enum='):
                        raw_vals = constraint.split('=', 1)[1] if '=' in constraint else ''
                        enum_values = [v.strip().strip('"').strip("'") for v in raw_vals.split(',') if v.strip()]
                        literal_used = True
                        if enum_values:
                            literal_vals = ', '.join([f'"{v}"' for v in enum_values])
                            python_type = f'Literal[{literal_vals}]'
                        continue

                    # Parse operator syntax: ">= 0", "> 0", "< 10", etc.
                    if constraint.startswith('>='):
                        value = constraint[2:].strip()
                        field_constraints['ge'] = f'ge={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'ge={value}' for {field_name}")
                    elif constraint.startswith('>'):
                        value = constraint[1:].strip()
                        field_constraints['gt'] = f'gt={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'gt={value}' for {field_name}")
                    elif constraint.startswith('<='):
                        value = constraint[2:].strip()
                        field_constraints['le'] = f'le={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'le={value}' for {field_name}")
                    elif constraint.startswith('<'):
                        value = constraint[1:].strip()
                        field_constraints['lt'] = f'lt={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'lt={value}' for {field_name}")
                    # NEW: Parse range format: "range:>0", "range:>=1", "range: >= 0.01", "range:0-100"
                    elif constraint.startswith('range:') or constraint.startswith('range '):
                        range_part = constraint.split(':', 1)[1].strip() if ':' in constraint else constraint[6:].strip()

                        # Handle compound ranges like "0-100" (without operators)
                        if '-' in range_part and not any(op in range_part for op in ['>=', '<=', '>', '<']):
                            parts = range_part.split('-')
                            if len(parts) == 2:
                                min_val, max_val = parts[0].strip(), parts[1].strip()
                                field_constraints['ge'] = f'ge={min_val}'
                                field_constraints['le'] = f'le={max_val}'
                                logger.debug(f"✅ Parsed range '{constraint}' → ge={min_val}, le={max_val} for {field_name}")
                        # Handle operator-based ranges like ">=1", ">0"
                        elif range_part.startswith('>='):
                            value = range_part[2:].strip()
                            field_constraints['ge'] = f'ge={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → ge={value} for {field_name}")
                        elif range_part.startswith('>'):
                            value = range_part[1:].strip()
                            field_constraints['gt'] = f'gt={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → gt={value} for {field_name}")
                        elif range_part.startswith('<='):
                            value = range_part[2:].strip()
                            field_constraints['le'] = f'le={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → le={value} for {field_name}")
                        elif range_part.startswith('<'):
                            value = range_part[1:].strip()
                            field_constraints['lt'] = f'lt={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → lt={value} for {field_name}")
                        else:
                            logger.warning(f"⚠️ Unknown range format '{constraint}' for {field_name} - SKIPPING")
                    # NEW: Skip unparseable constraint types (business rules go to service layer)
                    elif constraint.startswith('custom:') or constraint.startswith('custom '):
                        logger.debug(f"ℹ️ Skipping custom rule for {field_name}: {constraint[:60]}... (handled in service layer)")
                    elif constraint.startswith('format:') or constraint.startswith('format '):
                        # Handle format constraints that should be converted
                        format_part = constraint.split(':', 1)[1].strip() if ':' in constraint else constraint[7:].strip()
                        if 'length' in format_part.lower():
                            # "format: length >= 1" → skip (already handled by min_length)
                            logger.debug(f"ℹ️ Skipping length format constraint for {field_name}: {constraint[:60]}...")
                        else:
                            logger.debug(f"ℹ️ Skipping format constraint for {field_name}: {constraint[:60]}...")
                    # Parse named constraints (MUST be proper format like "ge=0", NOT "range: >= 1")
                    elif '=' in constraint and ':' not in constraint:
                        # Direct constraint like "gt=0", "min_length=1"
                        key = constraint.split('=')[0]
                        field_constraints[key] = constraint
                        logger.debug(f"✅ Parsed named constraint '{constraint}' → key='{key}' for {field_name}")
                    # Use normalized version for matching keyword constraints
                    elif constraint_normalized == 'email_format':
                        field_constraints['pattern'] = 'pattern=r"^[^@]+@[^@]+\\.[^@]+$"'
                        logger.debug(f"✅ Parsed email_format constraint for {field_name}")
                    elif constraint_normalized == 'positive':
                        field_constraints['gt'] = 'gt=0'
                        logger.debug(f"✅ Parsed 'positive' → 'gt=0' for {field_name}")
                    elif constraint_normalized == 'non_negative':
                        field_constraints['ge'] = 'ge=0'
                        logger.debug(f"✅ Parsed 'non_negative' → 'ge=0' for {field_name}")
                    # NEW: Handle constraint types from validation ground truth
                    elif constraint_normalized == 'required':
                        # Mark field as required (will prevent Optional and default)
                        required = True
                        logger.debug(f"✅ Parsed 'required' constraint for {field_name}")
                    elif constraint_normalized == 'uuid_format':
                        # Bug #103 Fix: Do NOT add pattern= to UUID fields
                        # The UUID type in Pydantic already validates format correctly
                        # Adding pattern= forces string type validation, causing ValidationError
                        # when SQLAlchemy returns actual UUID objects from the database
                        logger.debug(f"ℹ️ Skipping pattern= for 'uuid_format' on {field_name} (Bug #103 fix - UUID type validates format)")
                    elif constraint_normalized == 'enum':
                        # Mark that this field needs enum validation (handled separately)
                        field_constraints['_is_enum'] = True
                        logger.debug(f"✅ Parsed 'enum' constraint for {field_name}")
                    elif constraint_normalized == 'business_rule':
                        # Business rules are not field-level validations, skip
                        logger.debug(f"ℹ️ Skipping 'business_rule' constraint for {field_name} (not a field validation)")
                    # =========================================================
                    # Phase 1: Constraint Parser Enhancement (Bug #167)
                    # Handle "type: value" format constraints from ValidationModelIR
                    # =========================================================
                    elif constraint_normalized.startswith('presence_') or constraint_normalized.startswith('presence:'):
                        # "presence: required" → mark field as required
                        required = True
                        logger.debug(f"✅ Parsed 'presence: required' → required=True for {field_name}")
                    elif constraint_normalized.startswith('uniqueness_') or constraint_normalized.startswith('uniqueness:'):
                        # "uniqueness: unique" → skip (DB constraint, not Pydantic)
                        # Uniqueness is enforced at database level, not schema level
                        logger.debug(f"ℹ️ Skipping 'uniqueness' constraint for {field_name} (enforced at DB level)")
                    elif constraint_normalized in ('min_value', 'max_value', 'min_length', 'max_length'):
                        # Standalone constraint name without value - skip with info
                        # These need actual values to be useful (e.g., "min_value=0")
                        logger.debug(f"ℹ️ Skipping standalone '{constraint}' for {field_name} (no value provided)")
                    elif constraint_normalized in ('pattern', 'format', 'enum_values'):
                        # Standalone constraint name without value - skip with info
                        # These need actual values (e.g., "pattern=r'^...$'")
                        logger.debug(f"ℹ️ Skipping standalone '{constraint}' for {field_name} (no value provided)")
                    elif constraint_normalized.startswith('relationship_') or constraint_normalized.startswith('relationship:'):
                        # "relationship: must reference existing X" → FK validation
                        # This is enforced at service/DB level, not schema
                        logger.debug(f"ℹ️ Skipping 'relationship' constraint for {field_name} (enforced at service/DB level)")
                    elif constraint_normalized.startswith('status_transition') or constraint_normalized.startswith('workflow_'):
                        # Status transitions are enforced in service layer
                        logger.debug(f"ℹ️ Skipping '{constraint_normalized}' for {field_name} (enforced in service layer)")
                    elif constraint_normalized == 'unique':
                        # Simple "unique" constraint - DB level
                        logger.debug(f"ℹ️ Skipping 'unique' constraint for {field_name} (enforced at DB level)")
                    elif constraint_normalized.startswith('stock_constraint'):
                        # Stock constraints are business logic - enforced in service layer
                        logger.debug(f"ℹ️ Skipping 'stock_constraint' for {field_name} (enforced in service layer)")
                    elif constraint_normalized.startswith('custom'):
                        # Custom constraints are business logic
                        logger.debug(f"ℹ️ Skipping 'custom' constraint for {field_name} (enforced in service layer)")
                    else:
                        logger.warning(f"⚠️ Unparsed constraint '{constraint}' (normalized: '{constraint_normalized}') for {field_name} - SKIPPING")
                else:
                    logger.warning(f"⚠️ Non-string constraint {constraint} (type={type(constraint)}) for {field_name}")

            # Add type-specific default constraints (only if not already set)
            is_literal = isinstance(python_type, str) and python_type.startswith('Literal[')
            is_str_like = python_type == 'str'  # ← FIXED: Literal types are NOT string-like

            # NOTE: Hardcoded field_name checks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Email pattern now detected by constraint, not field name
            # Check if field has email validation constraint from IR/spec
            constraint_strs_lower = [str(c).lower() for c in constraints] if constraints else []
            has_email_constraint = any(
                kw in c for c in constraint_strs_lower
                for kw in ['email', 'valid_email', 'format:email', 'email_format']
            )

            if is_str_like and has_email_constraint:
                # Email validation with pattern - detected from constraint, not field name
                if 'pattern' not in field_constraints:
                    field_constraints['pattern'] = 'pattern=r"^[^@]+@[^@]+\\.[^@]+$"'
            elif is_str_like:
                # Default min_length=1 for required strings to ensure not empty
                # NOTE: NOT applied to Literal types (enums) - they don't need length validation
                if required and 'min_length' not in field_constraints:
                    field_constraints['min_length'] = 'min_length=1'
                # Add reasonable max_length to trigger validation in OpenAPI
                if 'max_length' not in field_constraints:
                    field_constraints['max_length'] = 'max_length=255'
            elif python_type in ['Decimal', 'int', 'float']:
                # NOTE: Hardcoded field names for gt/ge REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
                # Numeric constraints should come from IR/spec, not inferred from field names
                # If spec says field > 0, the constraint should be in validation_constraints
                # Only add ge=0 as safe default for ALL numerics (non-negative is common)
                # Specific gt=0 (positive) should come from spec constraints
                if 'gt' not in field_constraints and 'ge' not in field_constraints:
                    # Check if spec already defines positivity constraint
                    has_positive_constraint = any(
                        kw in c for c in constraint_strs_lower
                        for kw in ['positive', 'gt=0', 'gt:0', '>0', 'greater_than_zero']
                    )
                    if has_positive_constraint:
                        field_constraints['gt'] = 'gt=0'
                    # Don't add default ge=0 - let spec define constraints explicitly

            # Handle enum fields - remove marker and note for future enhancement
            is_enum_field = field_constraints.pop('_is_enum', False)
            if is_enum_field:
                logger.info(f"ℹ️ Field {entity_name}.{field_name} marked as enum - using Literal or Enum would be ideal")
                # For now, we'll let it be a string field with the constraints
                # Future enhancement: Generate Literal['value1', 'value2'] or Enum class

            # Convert dict to list for joining
            field_constraints_list = list(field_constraints.values())

            # Convert JavaScript/JSON boolean values to Python
            python_default = field_default
            use_default_factory = False  # Flag for datetime.now() factory pattern
            if field_default is not None:
                if isinstance(field_default, str):
                    if field_default.lower() == 'true':
                        python_default = 'True'
                    elif field_default.lower() == 'false':
                        python_default = 'False'
                    # NEW: Handle "now" default for datetime fields (Bug #17 fix)
                    # Match: 'now', 'now()', 'datetime.now()', 'datetime.now', etc.
                    elif field_default.lower().replace('()', '').replace('datetime.', '') == 'now':
                        if python_type == 'datetime' or 'datetime' in str(python_type).lower():
                            # Use default_factory pattern for dynamic datetime
                            use_default_factory = True
                            python_default = None  # Will be handled specially
                            logger.debug(f"✅ Converting '{field_default}' default to default_factory=datetime.now for {field_name}")
                        else:
                            # Not a datetime field, skip the "now" default
                            python_default = None
                            logger.warning(f"⚠️ '{field_default}' default on non-datetime field {field_name} - removing default")

            # NEW: Check for enforcement strategy from validation ground truth
            enforcement = _get_enforcement_for_field(entity_name, field_name, validation_ground_truth)

            # Handle special enforcement types
            if enforcement:
                enf_type = enforcement.get('enforcement_type', 'description')

                # 1. Computed field - generate @computed_field property
                if enf_type == 'computed_field':
                    logger.info(f"✨ Generating @computed_field for {entity_name}.{field_name}")
                    # Extract calculation logic from enforcement_code or condition
                    calc_code = enforcement.get('enforcement_code')
                    if not calc_code:
                        # Fallback: generate placeholder based on field name
                        if 'total' in field_name.lower():
                            calc_code = f"return sum(item.unit_price * item.quantity for item in self.items)"
                        else:
                            calc_code = "pass  # Extension point: Implement calculation logic"

                    pydantic_fields.append(f"""    @computed_field
    @property
    def {field_name}(self) -> {python_type}:
        {calc_code}""")
                    continue  # Skip normal field generation

                # 2. Immutable field - generate with exclude=True
                elif enf_type == 'immutable':
                    logger.info(f"🔒 Generating immutable field for {entity_name}.{field_name}")
                    # Immutable fields should be excluded from input schemas
                    if field_constraints_list:
                        constraints_str = ', '.join(field_constraints_list)
                        pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., {constraints_str}, exclude=True)")
                    else:
                        pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., exclude=True)")
                    continue  # Skip normal field generation

                # 3. Business logic enforcement - add description marker
                elif enf_type == 'business_logic':
                    logger.info(f"⚙️ Business logic enforcement for {entity_name}.{field_name} (handled at service layer)")
                    # Business logic is enforced in service layer, not schema
                    # Still generate normal field but add description
                    description = f"Enforced by business logic: {enforcement.get('condition', '')}"
                    if field_constraints_list:
                        constraints_str = ', '.join(field_constraints_list)
                        pydantic_fields.append(f'    {field_name}: {python_type} = Field(..., {constraints_str}, description="{description}")')
                    else:
                        pydantic_fields.append(f'    {field_name}: {python_type} = Field(..., description="{description}")')
                    continue  # Skip normal field generation

            # NEW: Handle datetime fields with "now" default using default_factory
            if use_default_factory:
                # Use Field with default_factory for datetime.now()
                if field_constraints_list:
                    constraints_str = ', '.join(field_constraints_list)
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(default_factory=datetime.now, {constraints_str})")
                else:
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(default_factory=datetime.now)")
                logger.debug(f"✅ Generated datetime field with default_factory: {field_name}")
                continue  # Skip normal field generation

            # Build field definition with or without Field() (EXISTING LOGIC)
            if field_constraints_list:
                # Use Field() with constraints
                constraints_str = ', '.join(field_constraints_list)
                if required and not python_default:
                    # Required field: Field(...)
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., {constraints_str})")
                elif python_default is not None:
                    # Bug #17 safety net: catch any "now" variants in constrained fields
                    if isinstance(python_default, str) and python_default.lower().replace('()', '').replace('datetime.', '') == 'now':
                        if python_type == 'datetime' or 'datetime' in str(python_type).lower():
                            pydantic_fields.append(f"    {field_name}: {python_type} = Field(default_factory=datetime.now, {constraints_str})")
                            logger.debug(f"✅ Safety net (constrained): caught '{python_default}' for {field_name}")
                            continue
                        else:
                            pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = Field(None, {constraints_str})")
                            continue
                    # Field with default value
                    needs_quotes = python_type == 'str' or (isinstance(python_type, str) and python_type.startswith('Literal['))
                    default_val = f'"{python_default}"' if needs_quotes else python_default
                    pydantic_fields.append(f'    {field_name}: {python_type} = Field({default_val}, {constraints_str})')
                else:
                    # Optional field
                    pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = Field(None, {constraints_str})")
            else:
                # No constraints, use simple type annotation
                # NOTE: Hardcoded field_name == 'items' checks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
                # List types are now handled generically by type, not field name
                if required and not python_default:
                    # Required field without default
                    pydantic_fields.append(f"    {field_name}: {python_type}")
                elif python_default is not None:
                    # Bug #17 safety net: catch any "now" variants that escaped earlier detection
                    if isinstance(python_default, str) and python_default.lower().replace('()', '').replace('datetime.', '') == 'now':
                        if python_type == 'datetime' or 'datetime' in str(python_type).lower():
                            pydantic_fields.append(f"    {field_name}: {python_type} = Field(default_factory=datetime.now)")
                            logger.debug(f"✅ Safety net: caught '{python_default}' for {field_name}, using default_factory")
                            continue
                        else:
                            python_default = None  # Skip invalid now default
                            pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = None")
                            continue
                    # Field with default value
                    needs_quotes = python_type == 'str' or (isinstance(python_type, str) and python_type.startswith('Literal['))
                    default_val = f'"{python_default}"' if needs_quotes else python_default
                    pydantic_fields.append(f'    {field_name}: {python_type} = {default_val}')
                else:
                    # Optional field (not required, no default)
                    pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = None")

        # Base schema - includes core fields (server-managed made optional above)
        base_fields = []
        managed_fields = []
        for line in pydantic_fields:
            fname = line.strip().split(':', 1)[0]
            if fname in ['id', 'created_at']:
                managed_fields.append(line)
            else:
                base_fields.append(line)

        code += f'''class {entity_name}Base(BaseSchema):
    """Base schema for {entity_lower}."""
'''
        if base_fields:
            code += '\n'.join(base_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Create schema - exclude server-managed and auto-calculated fields
        code += f'''class {entity_name}Create(BaseSchema):
    \"\"\"Schema for creating {entity_lower}.\"\"\"
'''
        create_fields = []
        for field_line in base_fields:
            fname = field_line.strip().split(':', 1)[0]
            # Check if field should be excluded
            if _should_exclude_from_create(entity_name, fname, validation_constraints):
                logger.info(f"🚫 Excluding {entity_name}.{fname} from Create schema")
                continue
            create_fields.append(field_line)

        if create_fields:
            code += '\n'.join(create_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Update schema - all fields optional for partial updates, excluding read-only/auto-calculated
        code += f'''class {entity_name}Update(BaseSchema):
    """Schema for updating {entity_lower}."""
'''
        if base_fields:
            # Make all fields optional for updates, preserving Field() constraints
            update_fields = []
            for field_line in base_fields:
                # Extract field name and type
                field_def = field_line.strip()
                if ': ' in field_def:
                    field_part = field_def.split(': ', 1)
                    fname = field_part[0]
                    rest = field_part[1]
                    
                    # Check if field should be excluded from updates
                    if _should_exclude_from_update(entity_name, fname, validation_constraints):
                        logger.info(f"🔒 Excluding {entity_name}.{fname} from Update schema")
                        continue

                    # Check if it uses Field()
                    if ' = Field(' in rest:
                        # Extract type and Field() part
                        type_part = rest.split(' = Field(')[0]
                        field_part_match = rest.split(' = Field(')[1]
                        # Replace first argument with None and keep constraints
                        if field_part_match.startswith('...'):
                            # Field(..., constraints) → Field(None, constraints)
                            field_constraints = field_part_match.replace('...', 'None', 1)
                        else:
                            # Field(default, constraints) → Field(None, constraints)
                            # Find the first comma to replace default with None
                            if ',' in field_part_match:
                                field_constraints = 'None' + field_part_match[field_part_match.index(','):]
                            else:
                                # No constraints, just default
                                field_constraints = 'None' + field_part_match[field_part_match.index(')'):]

                        # Make type Optional if not already
                        if not type_part.startswith('Optional['):
                            update_fields.append(f"    {fname}: Optional[{type_part}] = Field({field_constraints}")
                        else:
                            update_fields.append(f"    {fname}: {type_part} = Field({field_constraints}")
                    else:
                        # Simple type annotation, make it Optional
                        ftype = rest.split(' = ')[0]  # Remove default if present
                        if ftype.startswith('Optional['):
                            update_fields.append(f"    {fname}: {ftype} = None")
                        else:
                            update_fields.append(f"    {fname}: Optional[{ftype}] = None")
            code += '\n'.join(update_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Response schema (WITH Response suffix for consistency with routes)
        code += f'''class {entity_name}Response({entity_name}Base):
    """Response schema for {entity_lower}."""
'''
        # Bug #103 Fix EXPANDED: Remove pattern= from ALL UUID fields in Response schemas
        # pattern= forces string type in Pydantic, causing ValidationError when receiving UUID objects from SQLAlchemy
        # The UUID type already validates format correctly without pattern constraint
        response_lines = []
        for field_line in base_fields:
            # If line contains UUID type and pattern=, remove the pattern
            if 'UUID' in field_line and 'pattern=' in field_line:
                # Remove pattern=... from Field() - handles both pattern='...' and pattern=r"..."
                import re
                cleaned = re.sub(r",?\s*pattern=r?['\"][^'\"]+['\"]", '', field_line)
                # Also clean up any trailing comma before closing paren
                cleaned = re.sub(r',\s*\)', ')', cleaned)
                response_lines.append(cleaned)
            else:
                response_lines.append(field_line)
        # Ensure managed fields are present (id, created_at) and required
        for mline in managed_fields or []:
            mname = mline.strip().split(':', 1)[0]
            if mname == 'created_at':
                response_lines.append("    created_at: datetime")
                continue
            # Bug #103 Fix: Do NOT add pattern= to UUID fields
            # pattern= forces string type in Pydantic, causing ValidationError when receiving UUID objects
            # The UUID type already validates format correctly without pattern
            response_lines.append(f"    {mname}: UUID = Field(...)")
        if not managed_fields:
            response_lines.extend([
                "    id: UUID",
                "    created_at: datetime",
            ])

        # Bug #117 Fix: Add items and total_price to container entities (Cart, Order)
        # REMOVED: This was e-commerce specific logic. DevMatrix should be agnostic.
        # Relationships and computed fields should be defined in the ApplicationIR/Spec.
        # If they are missing, the parser/IR needs to be improved, not hardcoded here.


        code += '\n'.join(response_lines) + '\n\n'

        # List schema (uses {entity_name}Response for items)
        code += f'''class {entity_name}List(BaseSchema):
    """List response with pagination."""
    items: List[{entity_name}Response]
    total: int
    page: int


'''

    # Bug #200: Generate endpoint-specific schemas from IR
    # These are schemas defined in endpoint.request_schema (derived from IR, not hardcoded)
    # ONLY generate schemas that don't already exist from entity definitions
    if endpoint_schemas:
        # Build set of already-generated schema names from entities
        existing_schema_names = set()
        for entity in entities:
            entity_name = entity.get('name', '')
            if entity_name:
                existing_schema_names.add(f"{entity_name}Base")
                existing_schema_names.add(f"{entity_name}Create")
                existing_schema_names.add(f"{entity_name}Update")
                existing_schema_names.add(f"{entity_name}Response")
                existing_schema_names.add(f"{entity_name}List")

        generated_schema_names = set()  # Track to avoid duplicates within endpoint_schemas
        for ep_schema in endpoint_schemas:
            schema_name = ep_schema.get('name')
            schema_fields = ep_schema.get('fields', [])

            # Skip if no name, already generated, or exists from entity definitions
            if not schema_name or schema_name in generated_schema_names or schema_name in existing_schema_names:
                continue

            generated_schema_names.add(schema_name)

            # Build Pydantic class for this endpoint schema
            code += f'''class {schema_name}(BaseSchema):
    """Endpoint-specific request schema (from IR)."""
'''
            if schema_fields:
                for field in schema_fields:
                    fname = field.get('name', 'unknown')
                    ftype = field.get('type', 'str')
                    frequired = field.get('required', True)

                    # Map IR types to Python types
                    type_map = {
                        'string': 'str',
                        'integer': 'int',
                        'number': 'float',
                        'decimal': 'Decimal',
                        'boolean': 'bool',
                        'uuid': 'UUID',
                    }
                    python_type = type_map.get(ftype.lower(), ftype)

                    if frequired:
                        code += f"    {fname}: {python_type}\n"
                    else:
                        code += f"    {fname}: Optional[{python_type}] = None\n"
            else:
                code += "    pass\n"
            code += "\n\n"

        if generated_schema_names:
            logger.info(f"✅ Generated {len(generated_schema_names)} endpoint-specific schemas from IR: {sorted(generated_schema_names)}")

    return code.strip()


def _generate_behavior_guards(
    entity_name: str,
    has_stock: bool,
    has_status: bool,
    status_field_name: str,
    status_values: List[str]
) -> str:
    """
    Generate behavior guard class for entity validation.

    This creates a Validator class that checks:
    - Stock invariants (for entities with stock/quantity fields)
    - Status transitions (for entities with status fields)
    - Create/Update/Delete preconditions

    Returns complete Python class code as string.
    """
    entity_lower = entity_name.lower()

    # Build valid transitions map from status values
    transitions_code = ""
    if has_status and status_values:
        # Build transition rules: each status can transition to next ones in sequence
        # Plus common patterns like any -> CANCELLED
        transition_lines = []
        for i, status in enumerate(status_values):
            next_statuses = []
            if i + 1 < len(status_values):
                next_statuses.append(status_values[i + 1])
            # CANCELLED is usually a terminal from any non-terminal
            if "CANCEL" not in status.upper() and "CANCELLED" in [s.upper() for s in status_values]:
                cancelled = next(s for s in status_values if "CANCEL" in s.upper())
                if cancelled not in next_statuses:
                    next_statuses.append(cancelled)
            if next_statuses:
                transition_lines.append(f'            "{status}": {next_statuses},')

        if transition_lines:
            transitions_code = "\n".join(transition_lines)

    guards = f'''
class {entity_name}Validator:
    """
    Behavior guards for {entity_name}.

    Generated from BehaviorModelIR invariants and constraints.
    Validates preconditions before operations.
    """

    # Valid status transitions
    VALID_TRANSITIONS = {{
{transitions_code if transitions_code else '        # No status transitions defined'}
    }}

    async def check_create_preconditions(self, data) -> None:
        """Validate preconditions for create operation."""
        # Extension point: Add entity-specific create validations
        pass

    async def check_update_preconditions(self, entity, data) -> None:
        """Validate preconditions for update operation."""
        data_dict = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else data
'''

    # Add status transition check if entity has status
    if has_status and status_field_name:
        guards += f'''
        # Check status transition validity
        if "{status_field_name}" in data_dict:
            new_status = data_dict["{status_field_name}"]
            current_status = getattr(entity, "{status_field_name}", None)

            if current_status and current_status in self.VALID_TRANSITIONS:
                valid_next = self.VALID_TRANSITIONS[current_status]
                if new_status not in valid_next:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Cannot transition {entity_name} from '{{current_status}}' to '{{new_status}}'. Valid: {{valid_next}}"
                    )
'''

    # Add stock check if entity has stock/quantity fields (detected from IR field names)
    if has_stock:
        guards += f'''
    async def check_stock_invariant(self, entity, requested_qty: int) -> None:
        """Validate stock is sufficient. Field names derived from IR."""
        # Domain-agnostic: check common stock field patterns from IR
        stock_fields = ['stock', 'quantity', 'inventory', 'available', 'count']
        current_stock = 0
        for sf in stock_fields:
            val = getattr(entity, sf, None)
            if val is not None:
                current_stock = val
                break
        if current_stock < requested_qty:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient stock: {{current_stock}} < {{requested_qty}}"
            )
'''

    guards += f'''
    async def check_delete_preconditions(self, entity) -> None:
        """Validate preconditions for delete operation."""
        # Extension point: Add entity-specific delete validations
        pass
'''

    return guards


def generate_service_method(entity_name: str, attributes: list = None, ir: Any = None, all_entities: list = None) -> str:
    """
    Generate a complete service method without indentation errors.

    Args:
        entity_name: Name of the entity
        attributes: List of entity attributes for field-based logic detection
        ir: Optional ApplicationIR for dynamic field detection (Bug #109)
        all_entities: Optional list of all entities for relationship detection

    Returns:
        Complete service file code
    """
    # Default to empty list if not provided
    if attributes is None:
        attributes = []
    if all_entities is None:
        all_entities = []

    # Bug #109: Use IR-based detection for dynamic field names
    # Handle both dict and Pydantic model objects
    def _get_field_value(f, key, default=''):
        """Safely get value from dict or object attribute."""
        if isinstance(f, dict):
            return f.get(key, default)
        return getattr(f, key, default)

    entity_fields = [
        {'name': _get_field_value(f, 'name', ''),
         'data_type': _get_field_value(f, 'data_type', ''),
         'constraints': _get_field_value(f, 'constraints', {}),
         'default_value': _get_field_value(f, 'default_value', None)}
        for f in attributes
    ]

    # Detect status field dynamically from IR
    status_info = find_status_field(entity_name, entity_fields, ir)
    status_field_name = status_info.get("field_name") or "status"
    status_values = status_info.get("values", [])

    # Bug #109: Derive status values from IR instead of hardcoding
    # Bug #141: Removed unused status variables (open, cancelled, paid, checked_out, pending_payment)
    # Only initial_status is needed for generic service generation
    status_map = _map_status_values(status_values)
    initial_status = status_map.get("initial", "PENDING")

    # Detect child entity dynamically
    child_info = find_child_entity(entity_name, all_entities, ir)

    # Bug #140 Fix: Validate template assumptions BEFORE generating code
    # This prevents generating imports for entities that don't exist
    template_validation = validate_template_assumptions(
        entity_name=entity_name,
        all_entities=all_entities,
        child_info=child_info,
        ir=ir
    )

    # Log any validation warnings
    for warning in template_validation.get("warnings", []):
        logger.warning(f"Template validation: {warning}")

    # Get workflow operations from IR
    workflow_ops = find_workflow_operations(entity_name, ir) if ir else []

    logger.debug(f"Bug #109: Entity {entity_name} - status_field={status_field_name}, child={child_info}, workflows={len(workflow_ops)}")
    logger.debug(f"Bug #140: Template validation - can_generate_clear_items={template_validation['can_generate_clear_items']}")
    # Convert CamelCase to snake_case ({Entity} → {entity})
    import re
    entity_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    plural = f"{entity_snake}s"

    # Determine which guards to generate based on entity type (domain-agnostic field detection)
    stock_field_patterns = ('stock', 'quantity', 'inventory', 'available', 'count')
    has_stock = any(_get_field_value(f, 'name', '').lower() in stock_field_patterns for f in attributes)
    has_status = status_field_name and status_field_name != "status"  # Real status field found

    # Build behavior guards section
    behavior_guards = _generate_behavior_guards(entity_name, has_stock, has_status, status_field_name, status_values)

    base_service = f'''"""
FastAPI Service for {entity_name}

Business logic and data access patterns.
Includes RuntimeFlowValidator guards for business logic enforcement.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging
from fastapi import HTTPException

from src.models.schemas import {entity_name}Create, {entity_name}Update, {entity_name}Response, {entity_name}List
from src.repositories.{entity_snake}_repository import {entity_name}Repository
from src.models.entities import {entity_name}Entity

logger = logging.getLogger(__name__)

{behavior_guards}

class {entity_name}Service:
    """Business logic for {entity_name} with behavior guards."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = {entity_name}Repository(db)
        self.validator = {entity_name}Validator()

    async def create(self, data: {entity_name}Create) -> {entity_name}Response:
        """Create a new {entity_name.lower()} with precondition checks."""
        # Behavior guard: validate create preconditions
        await self.validator.check_create_preconditions(data)

        db_obj = await self.repo.create(data)
        return {entity_name}Response.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[{entity_name}Response]:
        """Get {entity_name.lower()} by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return {entity_name}Response.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[{entity_name}Response]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> {entity_name}List:
        """List {plural} with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return {entity_name}List(
            items=[{entity_name}Response.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: {entity_name}Update) -> Optional[{entity_name}Response]:
        """Update {entity_name.lower()} with transition validation."""
        # Get current state for transition validation
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # Behavior guard: validate update/transition
        await self.validator.check_update_preconditions(db_obj, data)

        db_obj = await self.repo.update(id, data)
        if db_obj:
            return {entity_name}Response.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete {entity_name.lower()} with guard check."""
        db_obj = await self.repo.get(id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="{entity_name} not found")

        # Behavior guard: validate delete is allowed
        await self.validator.check_delete_preconditions(db_obj)

        return await self.repo.delete(id)
'''

    # Bug #140 Fix: Only add clear_items() for entities that have child relationships
    # Previously this was in base template, causing ImportError for entities without children
    if child_info.get("found"):
        child_entity_class = child_info.get("entity_class", f"{entity_name}ItemEntity")
        child_fk_field = child_info.get("fk_field", f"{entity_snake}_id")
        base_service += f'''
    async def clear_items(self, id: UUID) -> Optional[{entity_name}Response]:
        """
        Clear all items/children from this {entity_name.lower()}.

        Used for entities that have child relationships (parent → children).
        Returns the updated entity after clearing items.

        Bug #105 Fix: Uses direct SQLAlchemy delete instead of non-existent repo method.
        Bug #140 Fix: Only generated for entities with verified child relationships.
        """
        # Get the entity first
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # Bug #105 Fix: Clear items directly using SQLAlchemy delete
        from sqlalchemy import delete
        from src.models.entities import {child_entity_class}
        await self.db.execute(
            delete({child_entity_class}).where({child_entity_class}.{child_fk_field} == id)
        )
        await self.db.flush()

        # Return the updated entity
        refreshed = await self.repo.get(id)
        return {entity_name}Response.model_validate(refreshed) if refreshed else None
'''

    # Bug #141 Fix: SPEC-AGNOSTIC field detection - NO entity name hardcoding
    # Detection is purely based on field presence from IR
    field_names = {f.name if hasattr(f, 'name') else f.get('name', '') for f in attributes}

    # Bug #141 Fix: Detect entities with is_active field - spec-agnostic
    # Any entity with is_active field gets activate/deactivate methods
    has_is_active = 'is_active' in field_names

    # Add activate/deactivate methods for entities with is_active field
    if has_is_active:
        base_service += f'''
    async def activate(self, id: UUID) -> Optional[{entity_name}Response]:
        """
        Activate {entity_name.lower()} by setting is_active to True.

        Bug #80a Fix: Custom operation method for activate endpoint.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        db_obj.is_active = True
        await self.db.flush()
        await self.db.refresh(db_obj)

        logger.info(f"{entity_name} activated: {entity_snake}_id={str(id)}")
        return {entity_name}Response.model_validate(db_obj)

    async def deactivate(self, id: UUID) -> Optional[{entity_name}Response]:
        """
        Deactivate {entity_name.lower()} by setting is_active to False.

        Bug #80a Fix: Custom operation method for deactivate endpoint.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        db_obj.is_active = False
        await self.db.flush()
        await self.db.refresh(db_obj)

        logger.info(f"{entity_name} deactivated: {entity_snake}_id={str(id)}")
        return {entity_name}Response.model_validate(db_obj)
'''

    # Bug #141 Fix: REMOVED hardcoded domain-specific business logic
    # Previous code had ~250 lines of hardcoded methods for specific domains.
    # These were spec-specific and should be generated from IR operations, not templates.
    # Custom business operations should be defined in the API spec and generated via IR.

    # Bug #143 Fix: Generate methods for IR-derived custom operations
    # Now we actually USE workflow_ops to generate the methods!
    generated_ops = set()  # Track generated ops to avoid duplicates
    crud_ops = {'create', 'read', 'update', 'delete', 'list', 'get', 'get_by_id', 'clear_items', 'activate', 'deactivate'}

    for op in workflow_ops:
        flow_name = op.get('name', '') or ''
        op_name = _extract_operation_name(flow_name, entity_name)

        # Skip if no valid operation name, or it's a CRUD op, or already generated
        if not op_name or op_name in crud_ops or op_name in generated_ops:
            continue

        generated_ops.add(op_name)
        logger.debug(f"Bug #143: Generating {op_name}() method for {entity_name} from flow '{flow_name}'")

        # Get operation metadata for generating proper behavior
        precondition_status = op.get('precondition_status', '')
        postcondition_status = op.get('postcondition_status', '')
        affects_stock = op.get('affects_stock', False)

        # Determine if this operation needs a data parameter (e.g., add_item)
        needs_data = 'add' in op_name or 'item' in op_name

        # Bug #200 Fix: Pass child_info to generate actual child entity creation
        method_body = _generate_workflow_method_body(
            entity_name, op_name, flow_name,
            precondition_status, postcondition_status,
            affects_stock, needs_data, status_field_name,
            child_info=child_info  # Bug #200: Enable child entity creation
        )
        base_service += method_body

    if generated_ops:
        logger.info(f"Bug #143: Generated {len(generated_ops)} custom operations for {entity_name}: {generated_ops}")

    return base_service


def generate_initial_migration(entities: List[Dict[str, Any]]) -> str:
    """
    Generate initial Alembic migration file.

    Args:
        entities: List of entities to create

    Returns:
        Complete migration code
    """
    code = '''"""
Initial migration - Create database tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables."""
'''

    # Map spec types to Alembic/SQLAlchemy column types
    type_mapping = {
        'UUID': 'postgresql.UUID(as_uuid=True)',
        'uuid': 'postgresql.UUID(as_uuid=True)',
        'str': 'sa.String(255)',
        'string': 'sa.String(255)',
        'text': 'sa.Text',
        'int': 'sa.Integer',
        'integer': 'sa.Integer',
        'float': 'sa.Numeric(10, 2)',
        'Decimal': 'sa.Numeric(10, 2)',
        'decimal': 'sa.Numeric(10, 2)',
        'datetime': 'sa.DateTime(timezone=True)',
        'date': 'sa.DateTime(timezone=True)',
        'bool': 'sa.Boolean',
        'boolean': 'sa.Boolean',
    }

    # NOTE: gt_defaults REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Fields now come from ApplicationIR.domain_model.entities.attributes
    # via _entity_to_dict in code_generation_service.py
    # If fields are empty, it's a bug in the upstream pipeline, not something to patch here.

    def _infer_sql_type(fname: str, field_type: str = None) -> str:
        """
        Infer SQL type from field name or explicit type.

        NOTE: Phase: Hardcoding Elimination (Nov 25, 2025)
        This function now PREFERS explicit field_type from IR over name inference.
        Name-based inference is ONLY used as fallback when type is missing.
        """
        # FIRST: Use explicit type if provided (from IR)
        if field_type:
            ft_lower = field_type.lower()
            if ft_lower in type_mapping:
                return type_mapping[ft_lower]
            if 'uuid' in ft_lower:
                return 'postgresql.UUID(as_uuid=True)'
            if 'decimal' in ft_lower or 'numeric' in ft_lower:
                return 'sa.Numeric(10, 2)'
            if 'int' in ft_lower:
                return 'sa.Integer'
            if 'bool' in ft_lower:
                return 'sa.Boolean'
            if 'datetime' in ft_lower or 'timestamp' in ft_lower:
                return 'sa.DateTime(timezone=True)'
            if 'list' in ft_lower or 'array' in ft_lower:
                return 'sa.String(255)'  # Store as JSON string

        # FALLBACK: Name-based inference (when type not provided)
        # NOTE: This is a fallback - types should come from ApplicationIR
        fl = fname.lower()
        if fl.endswith('_id') or fl == 'id':
            return 'postgresql.UUID(as_uuid=True)'
        if fl in ['created_at', 'updated_at']:
            return 'sa.DateTime(timezone=True)'
        # Default to String for unknown fields
        return 'sa.String(255)'

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_plural = entity.get('plural', f'{entity_name}s').lower()
        # Support both dict-based and object-based entities
        if hasattr(entity, 'fields'):
            fields = getattr(entity, 'fields', []) or []
        else:
            fields = entity.get('fields', []) or []
        if not fields:
            # NOTE: No longer using gt_defaults fallback - Phase: Hardcoding Elimination (Nov 25, 2025)
            # If fields are empty, it indicates a bug in ApplicationIR population
            # Log warning but don't synthesize fake fields
            logger.warning(f"⚠️ Entity '{entity_name}' has no fields - check ApplicationIR.domain_model.entities.attributes")

        code += f'''
    op.create_table(
        '{entity_plural}',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
'''

        for field in fields:
            # Support both objects and dicts
            if hasattr(field, 'name'):
                fname = field.name
                ftype = getattr(field, 'type', None) or 'str'
                required = getattr(field, 'required', True)
                default = getattr(field, 'default', None)
            else:
                fname = field.get('name', 'unknown')
                ftype = field.get('type') or 'str'
                required = field.get('required')
                default = field.get('default', None)

            if fname in ['id', 'created_at']:
                continue

            # Default required to True when unspecified to avoid generating nullable columns accidentally
            if required is None:
                required = True

            # Infer a type if missing or unknown - now passes ftype to prefer IR type over name inference
            col_type = type_mapping.get(ftype, _infer_sql_type(fname, ftype))
            nullable = not bool(required)

            column_def = f"        sa.Column('{fname}', {col_type}, nullable={str(nullable)})"

            # NOTE: Hardcoded fname == 'email' REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Unique constraint should come from field constraints, not field name
            # Check if field has unique constraint from IR/spec
            field_constraints = field.get('constraints', {}) if isinstance(field, dict) else getattr(field, 'constraints', {})
            constraint_strs = [str(c).lower() for c in (field_constraints if isinstance(field_constraints, list) else [field_constraints])]
            if any('unique' in c for c in constraint_strs):
                column_def = column_def.rstrip(')') + ', unique=True)'

            # Simple defaults - DETERMINISTIC RULE (AST stratum, not LLM)
            # Rule: SQL function → sa.text(), everything else → literal string
            if default not in [None, '...']:
                SQL_FUNCTIONS = ['now()', 'gen_random_uuid()', 'current_timestamp', 'uuid_generate_v4()']
                default_str = str(default).lower()

                if ftype in ['datetime', 'date']:
                    # Datetime defaults are SQL functions → sa.text()
                    column_def = column_def.rstrip(')') + ", server_default=sa.text('now()'))"
                elif any(fn in default_str for fn in SQL_FUNCTIONS):
                    # SQL function → sa.text()
                    column_def = column_def.rstrip(')') + f", server_default=sa.text('{default}'))"
                elif ftype in ['str', 'string', 'text']:
                    # String literal → plain quoted string (NOT sa.text!)
                    column_def = column_def.rstrip(')') + f", server_default='{default}')"
                elif ftype in ['bool', 'boolean']:
                    # Boolean → plain string literal
                    bool_default = 'true' if str(default).lower() == 'true' else 'false'
                    column_def = column_def.rstrip(')') + f", server_default='{bool_default}')"
                elif ftype in ['int', 'integer', 'float', 'decimal', 'numeric']:
                    # Numeric → plain literal (no quotes)
                    column_def = column_def.rstrip(')') + f", server_default='{default}')"
                else:
                    # Unknown type → plain string (safe default)
                    column_def = column_def.rstrip(')') + f", server_default='{default}')"

            code += column_def + ',\n'

        code += f'''        sa.PrimaryKeyConstraint('id')
    )
'''

    code += '''

def downgrade() -> None:
    """Drop all tables."""
'''

    for entity in entities:
        entity_plural = entity.get('plural', f'{entity["name"]}s').lower()
        code += f'''    op.drop_table('{entity_plural}')
'''

    return code.strip()


def validate_generated_files(files: Dict[str, str]) -> Dict[str, bool]:
    """
    Validate syntax of all generated Python files.

    Args:
        files: Dict of filename -> code

    Returns:
        Dict of filename -> is_valid
    """
    results = {}

    for filename, code in files.items():
        if filename.endswith('.py'):
            is_valid = validate_python_syntax(code, filename)
            results[filename] = is_valid

            if is_valid:
                logger.info(f"✅ Valid: {filename}")
            else:
                logger.error(f"❌ Invalid: {filename}")

    return results


def get_validation_summary(results: Dict[str, bool]) -> Dict[str, Any]:
    """
    Get summary of validation results.

    Args:
        results: Results from validate_generated_files

    Returns:
        Summary dict with total, passed, failed
    """
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "valid": failed == 0,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
    }
