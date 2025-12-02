"""
IR Backpropagation Engine - Maps runtime failures back to IR nodes.

This enables IR-grounded repair:
- Each violation maps to an IR element
- Each fix updates both code AND IR
- Guarantees consistency between IR and generated code

The repair cycle becomes:
  IR → code → tests → violations → IR causality → repair → IR consistency
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class IRNodeType(str, Enum):
    """Types of IR nodes that can be referenced."""
    FLOW = "flow"
    STEP = "step"
    INVARIANT = "invariant"
    CONSTRAINT = "constraint"
    ENTITY = "entity"
    ENDPOINT = "endpoint"
    GUARD = "guard"
    PREDICATE = "predicate"


@dataclass
class IRNodeReference:
    """Reference to a node in the IR."""
    node_type: IRNodeType
    node_id: str
    path: str  # e.g., "behavior.flows[0].steps[2]"
    entity: Optional[str] = None
    flow_id: Optional[str] = None


@dataclass
class ViolationCausality:
    """Maps a violation to its IR cause."""
    violation_id: str
    status_code: int
    error_detail: str
    ir_node: Optional[IRNodeReference]
    confidence: float = 0.0
    inferred_constraint_type: Optional[str] = None


@dataclass  
class RepairIntent:
    """An intent to repair, grounded in IR."""
    intent_id: str
    ir_node: IRNodeReference
    repair_type: str  # guard_add, transition_add, validation_add
    description: str
    code_changes: List[str] = field(default_factory=list)


class IRBackpropagationEngine:
    """
    Engine for mapping runtime failures back to IR nodes.
    
    Provides:
    - Violation → IR node mapping
    - IR-consistent repair generation
    - Backpropagation of fixes to IR
    """
    
    def __init__(self, ir: Optional[Any] = None):
        """Initialize with optional ApplicationIR."""
        self.ir = ir
        self._flow_index: Dict[str, IRNodeReference] = {}
        self._entity_index: Dict[str, List[IRNodeReference]] = {}
        if ir:
            self._build_indices()
    
    def _build_indices(self):
        """Build indices for fast IR node lookup."""
        if not self.ir:
            return
        
        # Index flows
        if hasattr(self.ir, 'behavior') and self.ir.behavior:
            for i, flow in enumerate(self.ir.behavior.flows):
                flow_id = flow.get_flow_id() if hasattr(flow, 'get_flow_id') else flow.name
                ref = IRNodeReference(
                    node_type=IRNodeType.FLOW,
                    node_id=flow_id,
                    path=f"behavior.flows[{i}]",
                    entity=getattr(flow, 'primary_entity', None),
                    flow_id=flow_id
                )
                self._flow_index[flow_id] = ref
                
                # Index by entity
                entities = getattr(flow, 'entities_involved', [])
                for entity in entities:
                    if entity not in self._entity_index:
                        self._entity_index[entity] = []
                    self._entity_index[entity].append(ref)
    
    def map_failure_to_ir_node(
        self, 
        status_code: int,
        error_detail: str,
        endpoint: Optional[str] = None,
        entity: Optional[str] = None
    ) -> ViolationCausality:
        """Map a runtime failure to an IR node."""
        violation_id = f"viol:{status_code}:{hash(error_detail) % 10000}"
        
        ir_node = None
        confidence = 0.0
        constraint_type = None
        
        # Infer constraint type from IR (100% domain-agnostic)
        constraint_type = 'validation'  # default

        # Look up constraint type from ValidationModelIR
        if entity and hasattr(self, '_ir') and self._ir:
            validation_ir = getattr(self._ir, 'validation_model_ir', None)
            if validation_ir:
                rules = getattr(validation_ir, 'rules', [])
                for rule in rules:
                    rule_entity = getattr(rule, 'entity', '')
                    if rule_entity.lower() == entity.lower():
                        constraint_type = getattr(rule, 'type', 'validation')
                        break
        
        # Try to find matching flow
        if entity and entity in self._entity_index:
            refs = self._entity_index[entity]
            if refs:
                ir_node = refs[0]  # Take first matching
                confidence = 0.7
        
        # Try endpoint matching
        if endpoint and not ir_node:
            for flow_id, ref in self._flow_index.items():
                if flow_id in endpoint.lower() or endpoint.lower() in flow_id:
                    ir_node = ref
                    confidence = 0.6
                    break
        
        return ViolationCausality(
            violation_id=violation_id,
            status_code=status_code,
            error_detail=error_detail,
            ir_node=ir_node,
            confidence=confidence,
            inferred_constraint_type=constraint_type
        )
    
    def generate_repair_intent(self, causality: ViolationCausality) -> Optional[RepairIntent]:
        """Generate a repair intent from a violation causality."""
        if not causality.ir_node:
            return None

        intent_id = f"intent:{causality.violation_id}"

        # Determine repair type based on constraint type (from IR, not hardcoded)
        constraint_type = causality.inferred_constraint_type
        repair_type = "validation_add"

        # Map constraint types to repair types (generic, not domain-specific)
        if constraint_type in ['comparison', 'guard', 'invariant']:
            repair_type = "guard_add"
        elif constraint_type in ['status_transition', 'workflow']:
            repair_type = "transition_add"

        return RepairIntent(
            intent_id=intent_id,
            ir_node=causality.ir_node,
            repair_type=repair_type,
            description=f"Add {repair_type} for {causality.ir_node.node_id}"
        )

    def backpropagate_fix(self, intent: RepairIntent) -> Dict[str, Any]:
        """
        Backpropagate a fix to update the IR.

        Returns the IR modifications to apply.
        """
        modifications = {
            'node_path': intent.ir_node.path,
            'node_type': intent.ir_node.node_type.value,
            'repair_type': intent.repair_type,
            'updates': {}
        }

        # Generic repair types (no domain-specific keywords)
        if intent.repair_type == 'guard_add':
            modifications['updates']['add_guard'] = {
                'name': f"guard_for_{intent.ir_node.node_id}",
                'type': 'comparison'  # generic
            }
        elif intent.repair_type == 'transition_add':
            modifications['updates']['add_transition'] = {
                'from': '*',
                'to': '*'
            }

        logger.info(f"Backpropagating fix to IR: {modifications}")
        return modifications

