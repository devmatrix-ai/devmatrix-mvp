"""
Causal Chain Builder - Tracks cause → effect chains for debugging.

When a test fails, we need to know:
- What IR constraint caused it?
- What flow step failed?
- What previous repairs might have broken it?

This provides full traceability from violation → root cause.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CauseType(str, Enum):
    """Types of root causes."""
    IR_CONSTRAINT = "ir_constraint"
    FLOW_STEP = "flow_step"
    PREVIOUS_REPAIR = "previous_repair"
    MISSING_GUARD = "missing_guard"
    INVALID_TRANSITION = "invalid_transition"
    REFERENCE_MISSING = "reference_missing"
    UNKNOWN = "unknown"


@dataclass
class CauseNode:
    """A node in the causal chain."""
    node_id: str
    cause_type: CauseType
    description: str
    ir_path: Optional[str] = None  # e.g., "behavior.flows[0].steps[2]"
    entity: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CausalChain:
    """Complete causal chain from violation to root cause."""
    chain_id: str
    violation_id: str
    status_code: int
    error_detail: str
    endpoint: Optional[str] = None
    causes: List[CauseNode] = field(default_factory=list)
    root_cause: Optional[CauseNode] = None
    previous_repairs: List[str] = field(default_factory=list)
    
    def add_cause(self, cause: CauseNode):
        """Add a cause to the chain."""
        self.causes.append(cause)
        # Latest cause is usually root
        self.root_cause = cause
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        parts = [f"Violation: {self.status_code} on {self.endpoint}"]
        parts.append(f"Detail: {self.error_detail}")
        if self.root_cause:
            parts.append(f"Root Cause: {self.root_cause.cause_type.value} - {self.root_cause.description}")
        if self.previous_repairs:
            parts.append(f"Related Repairs: {len(self.previous_repairs)}")
        return " | ".join(parts)


class CausalChainBuilder:
    """
    Builds causal chains from violations.
    
    Integrates with:
    - IRBackpropagationEngine for IR node mapping
    - ConstraintGraph for multi-entity analysis
    - Repair history for regression detection
    """
    
    def __init__(self):
        self.chains: Dict[str, CausalChain] = {}
        self.repair_history: List[Dict[str, Any]] = []
        self._counter = 0
    
    def build_chain(
        self,
        status_code: int,
        error_detail: str,
        endpoint: Optional[str] = None,
        entity: Optional[str] = None,
        ir_path: Optional[str] = None
    ) -> CausalChain:
        """Build a causal chain for a violation."""
        self._counter += 1
        chain_id = f"chain:{self._counter}"
        violation_id = f"viol:{status_code}:{hash(error_detail) % 10000}"
        
        chain = CausalChain(
            chain_id=chain_id,
            violation_id=violation_id,
            status_code=status_code,
            error_detail=error_detail,
            endpoint=endpoint
        )
        
        # Analyze and add causes
        cause = self._analyze_cause(status_code, error_detail, entity, ir_path)
        chain.add_cause(cause)
        
        # Check for related previous repairs
        chain.previous_repairs = self._find_related_repairs(entity, endpoint)
        
        self.chains[chain_id] = chain
        logger.info(f"Built causal chain: {chain.get_summary()}")
        
        return chain
    
    def _analyze_cause(
        self,
        status_code: int,
        error_detail: str,
        entity: Optional[str],
        ir_path: Optional[str]
    ) -> CauseNode:
        """Analyze error to determine cause type."""
        error_lower = error_detail.lower() if error_detail else ""
        
        cause_type = CauseType.UNKNOWN
        description = error_detail
        
        # Determine cause type from error patterns
        if 'stock' in error_lower or 'inventory' in error_lower or 'quantity' in error_lower:
            cause_type = CauseType.MISSING_GUARD
            description = "Stock/quantity guard missing or insufficient"
        elif 'status' in error_lower or 'transition' in error_lower or 'cannot' in error_lower:
            cause_type = CauseType.INVALID_TRANSITION
            description = "Invalid status transition attempted"
        elif 'not found' in error_lower or '404' in str(status_code):
            cause_type = CauseType.REFERENCE_MISSING
            description = "Referenced entity not found"
        elif ir_path:
            cause_type = CauseType.IR_CONSTRAINT
            description = f"IR constraint at {ir_path}"
        
        return CauseNode(
            node_id=f"cause:{self._counter}",
            cause_type=cause_type,
            description=description,
            ir_path=ir_path,
            entity=entity
        )
    
    def _find_related_repairs(
        self,
        entity: Optional[str],
        endpoint: Optional[str]
    ) -> List[str]:
        """Find previous repairs that might be related."""
        related = []
        for repair in self.repair_history:
            if entity and repair.get('entity') == entity:
                related.append(repair.get('repair_id', 'unknown'))
            elif endpoint and repair.get('endpoint') == endpoint:
                related.append(repair.get('repair_id', 'unknown'))
        return related
    
    def record_repair(self, repair_id: str, entity: str, endpoint: str, fix_type: str):
        """Record a repair for future reference."""
        self.repair_history.append({
            'repair_id': repair_id,
            'entity': entity,
            'endpoint': endpoint,
            'fix_type': fix_type,
            'timestamp': datetime.now()
        })
    
    def get_chains_for_entity(self, entity: str) -> List[CausalChain]:
        """Get all chains involving an entity."""
        return [c for c in self.chains.values() 
                if any(cause.entity == entity for cause in c.causes)]
    
    def get_regression_candidates(self) -> List[CausalChain]:
        """Get chains that might be regressions from previous repairs."""
        return [c for c in self.chains.values() if len(c.previous_repairs) > 0]

