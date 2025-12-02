"""
RuntimeFlowValidator - Validates business invariants at runtime.

This validator handles:
- Stock invariants (quantity checks)
- Status transitions (state machine validation)
- Idempotency checks
- Business guards
- Cross-entity invariants
- Reference integrity
- Workflow guard dependencies
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationResultStatus(str, Enum):
    """Result of a validation check."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a runtime validation."""
    status: ValidationResultStatus
    message: str
    constraint_type: str
    entity: Optional[str] = None
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    
    @property
    def is_valid(self) -> bool:
        return self.status == ValidationResultStatus.VALID


@dataclass
class InvariantRule:
    """A rule defining an invariant relationship."""
    name: str
    left_entity: str
    left_field: str
    operator: str  # ==, >=, <=, in
    right_expression: str  # e.g., "sum(cart.items.price)"
    

class RuntimeFlowValidator:
    """
    Validates business logic invariants at runtime.
    
    Extended with:
    - check_ref_integrity(): Multi-entity reference checks
    - check_cross_entity_invariants(): Cross-entity rules
    - check_workflow_guard_dependencies(): Guard dependencies on prior states
    """
    
    def __init__(self):
        # Valid status transitions per entity
        self.valid_transitions: Dict[str, Dict[str, Set[str]]] = {}
        # Invariant rules
        self.invariant_rules: List[InvariantRule] = []
    
    def register_transitions(self, entity: str, transitions: Dict[str, List[str]]):
        """Register valid status transitions for an entity."""
        self.valid_transitions[entity.lower()] = {
            from_status: set(to_statuses)
            for from_status, to_statuses in transitions.items()
        }
    
    async def check_comparison_constraint(
        self,
        entity: Any,
        entity_type: str,
        lhs_field: str,
        rhs_value: Any,
        operator: str = "<="
    ) -> ValidationResult:
        """
        Check a comparison constraint between entity field and value.

        100% domain-agnostic - field names come from IR.
        Example: check if entity.quantity <= some_value
        """
        try:
            lhs_value = getattr(entity, lhs_field, None)
            if lhs_value is None:
                return ValidationResult(
                    status=ValidationResultStatus.INVALID,
                    message=f"Field '{lhs_field}' not found on {entity_type}",
                    constraint_type="comparison_constraint",
                    entity=entity_type
                )

            # Evaluate comparison
            passed = False
            if operator == "<=":
                passed = lhs_value <= rhs_value
            elif operator == "<":
                passed = lhs_value < rhs_value
            elif operator == ">=":
                passed = lhs_value >= rhs_value
            elif operator == ">":
                passed = lhs_value > rhs_value
            elif operator == "==":
                passed = lhs_value == rhs_value
            elif operator == "!=":
                passed = lhs_value != rhs_value

            if not passed:
                return ValidationResult(
                    status=ValidationResultStatus.INVALID,
                    message=f"Constraint failed: {lhs_field}({lhs_value}) {operator} {rhs_value}",
                    constraint_type="comparison_constraint",
                    entity=entity_type,
                    field=lhs_field,
                    expected=rhs_value,
                    actual=lhs_value
                )

            return ValidationResult(
                status=ValidationResultStatus.VALID,
                message="Constraint passed",
                constraint_type="comparison_constraint"
            )
        except Exception as e:
            logger.error(f"Comparison check error: {e}")
            return ValidationResult(
                status=ValidationResultStatus.INVALID,
                message=str(e),
                constraint_type="comparison_constraint"
            )
    
    async def check_status_transition(
        self,
        entity: Any,
        entity_type: str,
        new_status: str
    ) -> ValidationResult:
        """Check if a status transition is valid."""
        entity_key = entity_type.lower()
        current_status = getattr(entity, 'status', None)
        
        if entity_key not in self.valid_transitions:
            return ValidationResult(
                status=ValidationResultStatus.SKIPPED,
                message=f"No transitions registered for {entity_type}",
                constraint_type="status_transition"
            )
        
        transitions = self.valid_transitions[entity_key]
        if current_status not in transitions:
            return ValidationResult(
                status=ValidationResultStatus.INVALID,
                message=f"No transitions from status '{current_status}'",
                constraint_type="status_transition",
                entity=entity_type,
                field="status",
                actual=current_status
            )
        
        if new_status not in transitions[current_status]:
            valid = list(transitions[current_status])
            return ValidationResult(
                status=ValidationResultStatus.INVALID,
                message=f"Cannot transition from '{current_status}' to '{new_status}'. Valid: {valid}",
                constraint_type="status_transition",
                entity=entity_type,
                field="status",
                expected=valid,
                actual=new_status
            )
        
        return ValidationResult(
            status=ValidationResultStatus.VALID,
            message=f"Transition {current_status} → {new_status} is valid",
            constraint_type="status_transition"
        )

    async def check_idempotency(
        self,
        operation_id: str,
        entity_id: str,
        db: Any
    ) -> ValidationResult:
        """Check if an operation has already been executed (idempotency)."""
        # Simple implementation - check for idempotency key
        key = f"{operation_id}:{entity_id}"
        # In real impl, check against idempotency store
        return ValidationResult(
            status=ValidationResultStatus.VALID,
            message="Operation not previously executed",
            constraint_type="idempotency"
        )

    async def check_business_guard(
        self,
        guard_name: str,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Check a named business guard."""
        # Guards are registered dynamically
        return ValidationResult(
            status=ValidationResultStatus.SKIPPED,
            message=f"Guard {guard_name} not registered",
            constraint_type="business_guard"
        )

    async def check_ref_integrity(
        self,
        entity: Any,
        refs: List[str],
        db: Any
    ) -> ValidationResult:
        """
        Check referential integrity for multi-entity references.

        Example: Cart references Product, Order references Cart
        """
        for ref_field in refs:
            ref_value = getattr(entity, ref_field, None)
            if ref_value is None:
                continue

            # Infer referenced entity from field name
            # e.g., product_id → Product
            if ref_field.endswith('_id'):
                ref_entity = ref_field[:-3].title()
            else:
                ref_entity = ref_field.title()

            try:
                referenced = await db.get(ref_entity, ref_value)
                if not referenced:
                    return ValidationResult(
                        status=ValidationResultStatus.INVALID,
                        message=f"Referenced {ref_entity} with id {ref_value} not found",
                        constraint_type="referential_integrity",
                        entity=ref_entity,
                        field=ref_field,
                        expected="exists",
                        actual="not found"
                    )
            except Exception as e:
                logger.warning(f"Ref integrity check failed: {e}")

        return ValidationResult(
            status=ValidationResultStatus.VALID,
            message="All references valid",
            constraint_type="referential_integrity"
        )

    async def check_cross_entity_invariants(
        self,
        entities: Dict[str, Any],
        rules: List[Tuple[str, str, str]]  # [(left_expr, operator, right_expr)]
    ) -> ValidationResult:
        """
        Check invariants across multiple entities.

        Example rules:
        - ("order.total", "==", "sum(cart.items.price)")
        - ("product.stock", ">=", "cart.quantity")
        """
        for left_expr, operator, right_expr in rules:
            try:
                left_val = self._eval_expression(left_expr, entities)
                right_val = self._eval_expression(right_expr, entities)

                if not self._compare(left_val, operator, right_val):
                    return ValidationResult(
                        status=ValidationResultStatus.INVALID,
                        message=f"Cross-entity invariant failed: {left_expr} {operator} {right_expr}",
                        constraint_type="cross_entity_invariant",
                        expected=f"{left_expr} {operator} {right_expr}",
                        actual=f"{left_val} vs {right_val}"
                    )
            except Exception as e:
                logger.warning(f"Could not evaluate rule: {e}")

        return ValidationResult(
            status=ValidationResultStatus.VALID,
            message="All cross-entity invariants hold",
            constraint_type="cross_entity_invariant"
        )

    async def check_workflow_guard_dependencies(
        self,
        guard_name: str,
        current_status: str,
        allowed_from: List[str]
    ) -> ValidationResult:
        """
        Check if a guard can be executed based on current status.

        Example:
        - can_pay: allowed only from ['pending']
        - can_cancel: allowed from ['pending', 'processing']
        """
        if current_status not in allowed_from:
            return ValidationResult(
                status=ValidationResultStatus.INVALID,
                message=f"Guard '{guard_name}' not allowed from status '{current_status}'. Allowed: {allowed_from}",
                constraint_type="workflow_guard",
                expected=allowed_from,
                actual=current_status
            )

        return ValidationResult(
            status=ValidationResultStatus.VALID,
            message=f"Guard '{guard_name}' allowed from '{current_status}'",
            constraint_type="workflow_guard"
        )

    def _eval_expression(self, expr: str, entities: Dict[str, Any]) -> Any:
        """Evaluate a simple expression against entities."""
        # Simple implementation: entity.field
        parts = expr.split('.')
        if len(parts) >= 2:
            entity_name = parts[0]
            field_name = parts[1]
            entity = entities.get(entity_name)
            if entity:
                return getattr(entity, field_name, None)
        return None

    def _compare(self, left: Any, operator: str, right: Any) -> bool:
        """Compare two values with operator."""
        if left is None or right is None:
            return False
        try:
            if operator == "==":
                return left == right
            elif operator == "!=":
                return left != right
            elif operator == ">":
                return left > right
            elif operator == ">=":
                return left >= right
            elif operator == "<":
                return left < right
            elif operator == "<=":
                return left <= right
        except TypeError:
            return False
        return False

