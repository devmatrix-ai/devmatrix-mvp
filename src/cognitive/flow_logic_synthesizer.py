"""
FlowLogicSynthesizer - Domain-Agnostic Guard Synthesizer

This module synthesizes Guard IR from ApplicationIR constraints.
It is 100% domain-agnostic: it never knows about Cart, Order, Product, etc.
All it sees are entities, fields, and constraint metadata from the IR.

The output is Guard IR (GuardSpec, FlowGuards) which is then translated
to concrete Python by CodeGenerationService using a varmap.

Architecture:
    IR (constraints) → FlowLogicSynthesizer → Guard IR → CodeGenerationService → Python

The synthesizer ONLY produces abstract expressions (GuardExpr).
It NEVER generates Python code - that's CodeGenerationService's job.
"""

import logging
from typing import Dict, Optional, Any, List, Set

from .guard_ir import (
    GuardSpec, FlowGuards, FlowKey,
    ComparisonExpr, MembershipExpr, ExistsExpr, NotEmptyExpr, LogicalExpr,
    GuardExpr, make_entity_ref, make_input_ref
)

logger = logging.getLogger(__name__)


class FlowLogicSynthesizer:
    """
    Synthesizes Guard IR from ApplicationIR constraints.

    This class is completely domain-agnostic. It reads constraint metadata
    from the IR and produces abstract guard expressions that reference
    entities and fields by name, not by concrete variable names.
    """

    def __init__(self, constraint_graph=None, routing_matrix=None):
        """
        Initialize the synthesizer.

        Args:
            constraint_graph: Optional ConstraintGraph for constraint lookup
            routing_matrix: Optional ValidationRoutingMatrix for layer routing
        """
        self._graph = constraint_graph
        self._routing = routing_matrix

    def synthesize_for_app(self, app_ir: Any) -> Dict[FlowKey, FlowGuards]:
        """
        Synthesize guards for all flows in an ApplicationIR.

        This is the main entry point. It:
        1. Extracts constraints from ValidationModelIR (status_transition, stock_constraint, etc.)
        2. Extracts constraints from BehaviorModelIR flows
        3. Synthesizes Guard IR for each (entity, operation) pair

        Args:
            app_ir: The ApplicationIR containing behavior flows and constraints

        Returns:
            Dictionary mapping (entity_name, operation_name) to FlowGuards
        """
        guards_by_flow: Dict[FlowKey, FlowGuards] = {}
        entities_seen: Set[str] = set()

        # =========================================================
        # 1. Extract guards from ValidationModelIR rules
        # =========================================================
        validation_model = getattr(app_ir, 'validation_model', None)
        if validation_model:
            rules = getattr(validation_model, 'rules', []) or []
            guards_from_validation = self._synthesize_from_validation_rules(rules)
            for key, flow_guards in guards_from_validation.items():
                guards_by_flow[key] = flow_guards
                entities_seen.add(key[0])
            logger.info(f"FlowLogicSynthesizer: Extracted guards for {len(guards_from_validation)} flows from ValidationModelIR")

        # =========================================================
        # 2. Extract guards from BehaviorModelIR flows
        # =========================================================
        behavior = getattr(app_ir, 'behavior', None)
        if behavior:
            flows = getattr(behavior, 'flows', []) or []
            for flow in flows:
                entity_name = getattr(flow, 'entity_name', None) or getattr(flow, 'entity', None)
                operation_name = getattr(flow, 'operation_name', None) or getattr(flow, 'name', None)

                if not entity_name or not operation_name:
                    continue

                key: FlowKey = (entity_name, operation_name)
                flow_guards = self._build_guards_for_flow(app_ir, flow)

                # Merge with existing guards from validation
                if key in guards_by_flow:
                    existing = guards_by_flow[key]
                    guards_by_flow[key] = FlowGuards(
                        pre=existing.pre + flow_guards.pre,
                        post=existing.post + flow_guards.post,
                        invariants=existing.invariants + flow_guards.invariants
                    )
                else:
                    guards_by_flow[key] = flow_guards

                entities_seen.add(entity_name)

        # =========================================================
        # 3. Log synthesis summary
        # =========================================================
        total_pre = sum(len(fg.pre) for fg in guards_by_flow.values())
        total_post = sum(len(fg.post) for fg in guards_by_flow.values())
        total_invariants = sum(len(fg.invariants) for fg in guards_by_flow.values())
        logger.info(f"FlowLogicSynthesizer: Synthesized {total_pre} pre-guards, "
                   f"{total_post} post-guards, {total_invariants} invariants "
                   f"for {len(guards_by_flow)} flows across {len(entities_seen)} entities")

        return guards_by_flow

    def _synthesize_from_validation_rules(self, rules: List[Any]) -> Dict[FlowKey, FlowGuards]:
        """
        Synthesize guards from ValidationModelIR rules.

        This extracts status_transition, stock_constraint, workflow_constraint, and custom
        rules and converts them to Guard IR.
        """
        guards_by_entity: Dict[str, FlowGuards] = {}

        for rule in rules:
            rule_type = getattr(rule, 'type', None)
            if not rule_type:
                continue

            # Get entity name from rule
            entity = getattr(rule, 'entity', None)
            if not entity:
                continue

            # Convert ValidationType enum to string if needed
            type_str = rule_type.value if hasattr(rule_type, 'value') else str(rule_type)

            # Only process business logic constraints
            if type_str not in ('status_transition', 'stock_constraint', 'workflow_constraint', 'custom'):
                continue

            # Build constraint metadata from rule
            constraint = self._rule_to_constraint(rule, type_str)
            if not constraint:
                continue

            guard = self._constraint_to_guard(None, constraint)
            if not guard:
                continue

            # Add to entity's guards
            if entity not in guards_by_entity:
                guards_by_entity[entity] = FlowGuards(pre=[], post=[], invariants=[])

            if guard.phase == "pre":
                guards_by_entity[entity].pre.append(guard)
            elif guard.phase == "post":
                guards_by_entity[entity].post.append(guard)
            else:
                guards_by_entity[entity].invariants.append(guard)

        # Convert to FlowKey format - use "*" for operation to apply to all operations
        result: Dict[FlowKey, FlowGuards] = {}
        for entity, flow_guards in guards_by_entity.items():
            # These guards apply to updates/transitions
            result[(entity, "*")] = flow_guards

        return result

    def _rule_to_constraint(self, rule: Any, type_str: str) -> Optional[Any]:
        """Convert a ValidationRule to a constraint-like object for processing."""
        from dataclasses import dataclass

        @dataclass
        class ConstraintAdapter:
            type: str
            id: str
            metadata: Dict[str, Any]
            description: str = ""

        entity = getattr(rule, 'entity', '')
        attribute = getattr(rule, 'attribute', '')
        condition = getattr(rule, 'condition', '')
        error_message = getattr(rule, 'error_message', '')

        metadata: Dict[str, Any] = {}

        if type_str == 'status_transition':
            # Parse condition like "status in [PENDING, PAID]" or extract from attribute
            metadata = {
                'entity': entity,
                'field': attribute if attribute else 'status',
                'allowed_from': self._parse_allowed_values(condition),
                'allowed_to': []
            }
        elif type_str == 'stock_constraint':
            # Parse stock constraint - look for pattern like "quantity <= stock"
            lhs, rhs, op = self._parse_comparison(condition, entity, attribute)
            metadata = {
                'lhs': lhs,
                'rhs': rhs,
                'op': op
            }
        elif type_str == 'workflow_constraint':
            # Parse workflow constraint
            metadata = {
                'entity': entity,
                'field': attribute,
                'check': 'not_empty' if 'not empty' in condition.lower() else 'exists',
                'message': error_message or condition
            }
        elif type_str == 'custom':
            # Parse custom constraint
            metadata = {
                'entity': entity,
                'field': attribute,
                'pattern': condition,
                'description': error_message or condition
            }

        return ConstraintAdapter(
            type=type_str,
            id=f"{entity}.{attribute}.{type_str}",
            metadata=metadata,
            description=error_message or condition
        )

    def _parse_allowed_values(self, condition: str) -> List[str]:
        """Parse allowed values from condition string like 'status in [PENDING, PAID]'."""
        if not condition:
            return []

        # Look for [value1, value2] pattern
        import re
        match = re.search(r'\[([^\]]+)\]', condition)
        if match:
            values = [v.strip().strip("'\"") for v in match.group(1).split(',')]
            return values

        # Look for "in (value1, value2)" pattern
        match = re.search(r'in\s*\(([^)]+)\)', condition, re.IGNORECASE)
        if match:
            values = [v.strip().strip("'\"") for v in match.group(1).split(',')]
            return values

        return []

    def _parse_comparison(self, condition: str, entity: str, attribute: str) -> tuple:
        """Parse comparison from condition string (100% domain-agnostic)."""
        import re

        # Default: lhs is entity.attribute, rhs/op extracted from condition
        lhs = {'entity': entity, 'field': attribute, 'role': 'entity'}
        rhs = {'entity': '', 'field': '', 'role': 'value'}
        op = '<='

        if not condition:
            return lhs, rhs, op

        # Pattern: field op entity.field (e.g., "quantity <= other.limit")
        match = re.search(r'(\w+)\s*([<>=!]+)\s*(\w+)\.(\w+)', condition)
        if match:
            lhs_field, op_str, rhs_entity, rhs_field = match.groups()
            lhs = {'entity': entity, 'field': lhs_field, 'role': 'entity'}
            rhs = {'entity': rhs_entity, 'field': rhs_field, 'role': 'entity'}
            op = op_str
        else:
            # Pattern: field op value (e.g., "count >= 0")
            match2 = re.search(r'(\w+)\s*([<>=!]+)\s*(\d+)', condition)
            if match2:
                lhs_field, op_str, value = match2.groups()
                lhs = {'entity': entity, 'field': lhs_field, 'role': 'entity'}
                rhs = {'entity': '', 'field': value, 'role': 'literal'}
                op = op_str

        return lhs, rhs, op

    def _build_guards_for_flow(self, app_ir: Any, flow: Any) -> FlowGuards:
        """Build guards for a single flow from its constraints."""
        pre: List[GuardSpec] = []
        post: List[GuardSpec] = []
        invariants: List[GuardSpec] = []

        # Get constraints from flow or via constraint graph
        constraints = self._get_constraints_for_flow(flow)

        for constraint in constraints:
            guard = self._constraint_to_guard(flow, constraint)
            if guard:
                phase_map = {"pre": pre, "post": post, "invariant": invariants}
                phase_map.get(guard.phase, pre).append(guard)

        return FlowGuards(pre=pre, post=post, invariants=invariants)

    def _get_constraints_for_flow(self, flow: Any) -> list:
        """Get constraints associated with a flow."""
        # Try constraint graph first
        if self._graph:
            flow_id = getattr(flow, 'id', None)
            if flow_id:
                graph_constraints = self._graph.get_constraints_for_flow(flow_id)
                if graph_constraints:
                    return graph_constraints

        # Fallback to flow's own constraints
        return getattr(flow, 'constraints', []) or []

    def _constraint_to_guard(self, flow: Any, constraint: Any) -> Optional[GuardSpec]:
        """Convert a constraint to a GuardSpec based on its type."""
        constraint_type = getattr(constraint, 'type', None)
        if not constraint_type:
            return None

        # Check routing matrix for layer
        if self._routing:
            layer = self._routing.get_layer_for_constraint(constraint_type)
            if layer and layer not in ("WORKFLOW", "BEHAVIOR", "RUNTIME"):
                return None

        # Route based on constraint type
        handlers = {
            "status_transition": self._status_transition_guard,
            "workflow_constraint": self._workflow_guard,
            "stock_constraint": self._stock_constraint_guard,
            "quantity_constraint": self._quantity_constraint_guard,
            "custom": self._custom_guard,
            "relationship": self._relationship_guard,
        }

        handler = handlers.get(constraint_type)
        if handler:
            return handler(constraint)

        return None

    def _status_transition_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard for status transition constraint."""
        metadata = getattr(c, 'metadata', {}) or {}
        entity = metadata.get('entity')
        field_name = metadata.get('field', 'status')
        allowed_from = metadata.get('allowed_from', [])

        if not entity or not allowed_from:
            return None

        expr = MembershipExpr(
            left=(f"entity:{entity}", field_name),
            op="in",
            right=allowed_from
        )

        return GuardSpec(
            expr=expr,
            error_code=422,
            message="Invalid status transition",
            source_constraint_id=getattr(c, 'id', 'unknown'),
            phase="pre"
        )

    def _stock_constraint_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard for stock/inventory constraint."""
        metadata = getattr(c, 'metadata', {}) or {}
        lhs = metadata.get('lhs', {})
        rhs = metadata.get('rhs', {})
        op = metadata.get('op', '<=')

        if not lhs or not rhs:
            return None

        lhs_entity = lhs.get('entity', '')
        lhs_field = lhs.get('field', '')
        rhs_entity = rhs.get('entity', '')
        rhs_field = rhs.get('field', '')

        if not all([lhs_entity, lhs_field, rhs_entity, rhs_field]):
            return None

        expr = ComparisonExpr(
            left=(f"entity:{lhs_entity}", lhs_field),
            op=op,
            right=(f"entity:{rhs_entity}", rhs_field)
        )

        # Domain-agnostic message from constraint metadata
        message = metadata.get('message', getattr(c, 'description', None)) or "Comparison constraint violated"

        return GuardSpec(
            expr=expr,
            error_code=422,
            message=message,
            source_constraint_id=getattr(c, 'id', 'unknown'),
            phase="pre"
        )

    def _quantity_constraint_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard for numeric field constraint (e.g., field > 0)."""
        metadata = getattr(c, 'metadata', {}) or {}
        entity = metadata.get('entity')
        field_name = metadata.get('field', '')
        op = metadata.get('op', '>')
        value = metadata.get('value', 0)

        if not entity or not field_name:
            return None

        expr = ComparisonExpr(
            left=(f"entity:{entity}", field_name),
            op=op,
            right=value
        )

        # Domain-agnostic message from constraint metadata
        message = metadata.get('message', getattr(c, 'description', None)) or f"Invalid {field_name} value"

        return GuardSpec(
            expr=expr,
            error_code=422,
            message=message,
            source_constraint_id=getattr(c, 'id', 'unknown'),
            phase="pre"
        )

    def _workflow_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard for workflow constraint."""
        metadata = getattr(c, 'metadata', {}) or {}
        entity = metadata.get('entity')
        field_name = metadata.get('field')
        check_type = metadata.get('check', 'not_empty')

        if not entity:
            return None

        if check_type == 'not_empty' and field_name:
            expr = NotEmptyExpr(target=(f"entity:{entity}", field_name))
        elif check_type == 'exists':
            expr = ExistsExpr(target=(f"entity:{entity}", field_name or 'id'), kind="entity")
        else:
            return None

        return GuardSpec(
            expr=expr,
            error_code=422,
            message=metadata.get('message', 'Workflow constraint violated'),
            source_constraint_id=getattr(c, 'id', 'unknown'),
            phase="pre"
        )

    def _relationship_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard for relationship existence constraint."""
        metadata = getattr(c, 'metadata', {}) or {}
        entity = metadata.get('entity')
        related_field = metadata.get('related_field', 'id')

        if not entity:
            return None

        expr = ExistsExpr(
            target=(f"entity:{entity}", related_field),
            kind="relation"
        )

        return GuardSpec(
            expr=expr,
            error_code=404,
            message=f"Related {entity} not found",
            source_constraint_id=getattr(c, 'id', 'unknown'),
            phase="pre"
        )

    def _custom_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard from custom constraint description."""
        metadata = getattr(c, 'metadata', {}) or {}
        description = getattr(c, 'description', '') or metadata.get('description', '')

        # Parse structured custom constraints
        expr_data = metadata.get('expr')
        if expr_data:
            expr = self._parse_expr_data(expr_data)
            if expr:
                return GuardSpec(
                    expr=expr,
                    error_code=metadata.get('error_code', 422),
                    message=metadata.get('message', description or 'Constraint violated'),
                    source_constraint_id=getattr(c, 'id', 'unknown'),
                    phase=metadata.get('phase', 'pre')
                )

        return None

    def _parse_expr_data(self, expr_data: dict) -> Optional[GuardExpr]:
        """Parse structured expression data into GuardExpr."""
        expr_type = expr_data.get('type')

        if expr_type == 'comparison':
            return ComparisonExpr(
                left=tuple(expr_data['left']),
                op=expr_data['op'],
                right=tuple(expr_data['right']) if isinstance(expr_data['right'], list) else expr_data['right']
            )
        elif expr_type == 'membership':
            return MembershipExpr(
                left=tuple(expr_data['left']),
                op=expr_data['op'],
                right=expr_data['right']
            )
        elif expr_type == 'exists':
            return ExistsExpr(
                target=tuple(expr_data['target']),
                kind=expr_data.get('kind', 'entity')
            )
        elif expr_type == 'not_empty':
            return NotEmptyExpr(target=tuple(expr_data['target']))

        return None

