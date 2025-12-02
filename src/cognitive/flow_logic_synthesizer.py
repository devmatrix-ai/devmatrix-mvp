"""
FlowLogicSynthesizer - Domain-Agnostic Guard Synthesizer

This module synthesizes Guard IR from ApplicationIR constraints.
It is 100% domain-agnostic: it never knows about Cart, Order, Product, etc.
All it sees are entities, fields, and constraint metadata from the IR.

The output is Guard IR (GuardSpec, FlowGuards) which is then translated
to concrete Python by CodeGenerationService using a varmap.
"""

import logging
from typing import Dict, Optional, Any, List

from .guard_ir import (
    GuardSpec, FlowGuards, FlowKey,
    ComparisonExpr, MembershipExpr, ExistsExpr, NotEmptyExpr,
    GuardExpr
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

        Args:
            app_ir: The ApplicationIR containing behavior flows and constraints

        Returns:
            Dictionary mapping (entity_name, operation_name) to FlowGuards
        """
        guards_by_flow: Dict[FlowKey, FlowGuards] = {}

        # Get behavior model if available
        behavior = getattr(app_ir, 'behavior', None)
        if not behavior:
            logger.debug("No behavior model in IR, returning empty guards")
            return guards_by_flow

        # Get flows from behavior
        flows = getattr(behavior, 'flows', []) or []

        for flow in flows:
            entity_name = getattr(flow, 'entity_name', None) or getattr(flow, 'entity', None)
            operation_name = getattr(flow, 'operation_name', None) or getattr(flow, 'name', None)

            if not entity_name or not operation_name:
                continue

            key: FlowKey = (entity_name, operation_name)
            guards_by_flow[key] = self._build_guards_for_flow(app_ir, flow)

            if guards_by_flow[key].pre or guards_by_flow[key].post:
                logger.info(f"Synthesized {len(guards_by_flow[key].pre)} pre-guards, "
                           f"{len(guards_by_flow[key].post)} post-guards for {key}")

        return guards_by_flow

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

        return GuardSpec(
            expr=expr,
            error_code=422,
            message="Quantity exceeds available stock",
            source_constraint_id=getattr(c, 'id', 'unknown'),
            phase="pre"
        )

    def _quantity_constraint_guard(self, c: Any) -> Optional[GuardSpec]:
        """Generate guard for quantity constraint (e.g., qty > 0)."""
        metadata = getattr(c, 'metadata', {}) or {}
        entity = metadata.get('entity')
        field_name = metadata.get('field', 'quantity')
        op = metadata.get('op', '>')
        value = metadata.get('value', 0)

        if not entity:
            return None

        expr = ComparisonExpr(
            left=(f"entity:{entity}", field_name),
            op=op,
            right=value
        )

        return GuardSpec(
            expr=expr,
            error_code=422,
            message=f"Invalid {field_name} value",
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

