"""
Behavior Lowering Protocol - Deterministic transformation of BehaviorModelIR to ICBR.

This is the core of the Cognitive Compiler's determinism guarantee:
- Same BehaviorModelIR input → Same ICBR output
- No LLM involvement
- Pure functional transformation

The lowering process:
1. Extract predicates from preconditions/postconditions
2. Canonicalize guards from flow steps
3. Extract atomic operations from steps
4. Build state transitions from flows
5. Derive invariants from relationships
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
import re
from dataclasses import dataclass

from .ir.behavior_model import BehaviorModelIR, Flow, FlowType, Invariant, Step
from .ir.icbr import (
    ICBR, CanonicalPredicate, CanonicalGuard, AtomicOperation, 
    StateTransition, CanonicalInvariant, PredicateType, OperationType
)

logger = logging.getLogger(__name__)


@dataclass
class LoweringResult:
    """Result of behavior lowering."""
    icbr: ICBR
    warnings: List[str]
    stats: Dict[str, int]


class BehaviorLoweringProtocol:
    """
    Deterministic Behavior Lowering Protocol.
    
    Transforms BehaviorModelIR → ICBR with guaranteed determinism.
    """
    
    def __init__(self):
        self.predicate_counter = 0
        self.guard_counter = 0
        self.operation_counter = 0
        self.transition_counter = 0
    
    def lower(self, behavior_ir: BehaviorModelIR) -> LoweringResult:
        """
        Lower BehaviorModelIR to ICBR.
        
        This is the main entry point for the deterministic lowering.
        """
        icbr = ICBR()
        warnings = []
        
        # Process each flow
        for flow in behavior_ir.flows:
            try:
                self._lower_flow(flow, icbr)
            except Exception as e:
                warnings.append(f"Failed to lower flow '{flow.name}': {e}")
        
        # Process invariants
        for invariant in behavior_ir.invariants:
            try:
                self._lower_invariant(invariant, icbr)
            except Exception as e:
                warnings.append(f"Failed to lower invariant: {e}")
        
        # Track source flows
        icbr.source_flows = [f.get_flow_id() for f in behavior_ir.flows]
        
        stats = {
            'predicates': len(icbr.predicates),
            'guards': len(icbr.guards),
            'operations': len(icbr.operations),
            'transitions': len(icbr.transitions),
            'invariants': len(icbr.invariants),
        }
        
        logger.info(f"Lowered BehaviorModelIR: {stats}")
        
        return LoweringResult(icbr=icbr, warnings=warnings, stats=stats)
    
    def _lower_flow(self, flow: Flow, icbr: ICBR):
        """Lower a single flow to ICBR elements."""
        flow_id = flow.get_flow_id()
        
        # 1. Lower preconditions to predicates + guards
        guard_predicates = []
        for precond in flow.preconditions:
            pred = self._parse_precondition(precond, flow)
            if pred:
                icbr.predicates[pred.predicate_id] = pred
                guard_predicates.append(pred.predicate_id)
        
        # Create guard from preconditions
        if guard_predicates:
            guard_id = f"guard:{flow_id}"
            guard = CanonicalGuard(
                guard_id=guard_id,
                name=f"{flow.name} preconditions",
                predicates=guard_predicates,
                error_code=422,
                error_message=f"Preconditions for {flow.name} not met"
            )
            icbr.guards[guard_id] = guard
        
        # 2. Lower steps to operations
        for step in flow.steps:
            op = self._parse_step(step, flow)
            if op:
                icbr.operations[op.operation_id] = op
        
        # 3. Lower state transitions
        if flow.type == FlowType.STATE_TRANSITION:
            transition = self._extract_transition(flow)
            if transition:
                icbr.transitions[transition.transition_id] = transition
    
    def _parse_precondition(self, precond: str, flow: Flow) -> Optional[CanonicalPredicate]:
        """Parse a precondition string into a canonical predicate."""
        self.predicate_counter += 1
        pred_id = f"pred:{self.predicate_counter}"
        
        # Pattern: entity.field == value
        match = re.match(r"(\w+)\.(\w+)\s*(==|!=|>|<|>=|<=)\s*['\"]?(\w+)['\"]?", precond)
        if match:
            entity, field, op, value = match.groups()
            return CanonicalPredicate(
                predicate_id=pred_id,
                predicate_type=PredicateType.COMPARISON if op != '==' else PredicateType.STATE,
                entity=entity,
                field=field,
                operator=op,
                value=value,
                expression=precond
            )
        
        # Pattern: entity.exists
        if '.exists' in precond:
            entity = precond.split('.')[0]
            return CanonicalPredicate(
                predicate_id=pred_id,
                predicate_type=PredicateType.EXISTENCE,
                entity=entity,
                expression=precond
            )
        
        # Fallback: raw expression
        entity = flow.primary_entity or "Unknown"
        return CanonicalPredicate(
            predicate_id=pred_id,
            predicate_type=PredicateType.COMPARISON,
            entity=entity,
            expression=precond
        )
    
    def _parse_step(self, step: Step, flow: Flow) -> Optional[AtomicOperation]:
        """Parse a step into an atomic operation."""
        self.operation_counter += 1
        op_id = f"op:{self.operation_counter}"
        
        action_lower = step.action.lower()
        op_type = OperationType.UPDATE  # default
        
        if 'create' in action_lower or 'add' in action_lower:
            op_type = OperationType.CREATE
        elif 'delete' in action_lower or 'remove' in action_lower:
            op_type = OperationType.DELETE
        elif 'decrement' in action_lower or 'decrease' in action_lower or 'reduce' in action_lower:
            op_type = OperationType.DECREMENT
        elif 'increment' in action_lower or 'increase' in action_lower:
            op_type = OperationType.INCREMENT
        elif 'transition' in action_lower or 'change status' in action_lower:
            op_type = OperationType.TRANSITION
        elif 'validate' in action_lower or 'check' in action_lower:
            op_type = OperationType.VALIDATE
        
        return AtomicOperation(
            operation_id=op_id,
            operation_type=op_type,
            entity=step.target_entity or flow.primary_entity or "Unknown"
        )
    
    def _extract_transition(self, flow: Flow) -> Optional[StateTransition]:
        """Extract state transition from a flow."""
        self.transition_counter += 1
        # This would need more sophisticated parsing
        # For now, create placeholder
        return StateTransition(
            transition_id=f"trans:{self.transition_counter}",
            entity=flow.primary_entity or "Unknown",
            from_state="*",
            to_state="*"
        )
    
    def _lower_invariant(self, invariant: Invariant, icbr: ICBR):
        """Lower an invariant to ICBR."""
        self.predicate_counter += 1
        pred_id = f"pred:{self.predicate_counter}"
        
        pred = CanonicalPredicate(
            predicate_id=pred_id,
            predicate_type=PredicateType.COMPARISON,
            entity=invariant.entity,
            expression=invariant.expression or invariant.description
        )
        icbr.predicates[pred_id] = pred
        
        inv_id = f"inv:{invariant.entity}:{len(icbr.invariants)}"
        canonical_inv = CanonicalInvariant(
            invariant_id=inv_id,
            entity=invariant.entity,
            description=invariant.description,
            predicate_id=pred_id,
            enforcement_level=invariant.enforcement_level
        )
        icbr.invariants[inv_id] = canonical_inv

