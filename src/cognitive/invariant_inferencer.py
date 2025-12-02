"""
Invariant Inferencer - Infers derived invariants from domain model.

A cognitive compiler MUST infer implicit rules that aren't explicit in specs:
- Quantity conservation: {container}.add_item(qty) → {resource}.{quantity_field} -= qty
- Status implication: {entity}.complete() → {related}.{status_field} = 'approved'
- Cascade effects: {entity}.cancel() → restore_quantities()
- Referential integrity: {child}.{parent}_id → {parent}.exists()

This closes the gap for multi-entity constraint handling.
Domain-agnostic: All entity/field names derived from IR.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class InvariantType(str, Enum):
    """Types of invariants that can be inferred."""
    STOCK_CONSERVATION = "stock_conservation"
    STATUS_IMPLICATION = "status_implication"
    CASCADE_EFFECT = "cascade_effect"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    BALANCE_CONSERVATION = "balance_conservation"
    QUANTITY_CONSTRAINT = "quantity_constraint"


@dataclass
class CanonicalInvariant:
    """An inferred invariant in canonical form."""
    invariant_id: str
    invariant_type: InvariantType
    description: str
    source_entity: str
    target_entity: Optional[str] = None
    trigger: Optional[str] = None  # e.g., "add_item", "complete" (from IR flows)
    effect: Optional[str] = None   # e.g., "{quantity_field} -= qty" (from IR fields)
    confidence: float = 1.0


@dataclass
class Implication:
    """A cross-entity implication."""
    trigger_entity: str
    trigger_condition: str  # e.g., "status == 'completed'"
    implied_entity: str
    implied_condition: str  # e.g., "payment.status == 'approved'"


class InvariantInferencer:
    """
    Infers derived invariants from domain model and flows.
    Domain-agnostic: Uses IR field patterns, not hardcoded entity names.

    Analyzes:
    - Entity relationships (foreign keys, references)
    - Flow preconditions/postconditions
    - Status field patterns
    - Quantity/stock field patterns
    """

    # Field classification from IR type annotations (100% domain-agnostic)
    # These are type patterns, not domain-specific field names
    NUMERIC_TYPES = {'int', 'integer', 'float', 'decimal', 'number'}
    STATUS_TYPES = {'enum', 'status', 'state'}  # Type annotations, not field names
    REFERENCE_PATTERNS = {'_id', 'id', '_ref'}
    
    def __init__(self):
        self.inferred: List[CanonicalInvariant] = []
        self.implications: List[Implication] = []
        self._counter = 0
    
    def infer_from_ir(self, ir: Any) -> List[CanonicalInvariant]:
        """Infer all invariants from ApplicationIR."""
        self.inferred = []
        
        # Infer from entities
        if hasattr(ir, 'domain') and ir.domain:
            for entity in ir.domain.entities:
                self._infer_from_entity(entity)
        
        # Infer from relationships
        if hasattr(ir, 'domain') and ir.domain:
            for rel in getattr(ir.domain, 'relationships', []):
                self._infer_from_relationship(rel)
        
        # Infer from flows
        if hasattr(ir, 'behavior') and ir.behavior:
            for flow in ir.behavior.flows:
                self._infer_from_flow(flow)
        
        logger.info(f"Inferred {len(self.inferred)} invariants")
        return self.inferred
    
    def _infer_from_entity(self, entity: Any):
        """Infer invariants from entity fields."""
        entity_name = getattr(entity, 'name', str(entity))
        fields = getattr(entity, 'fields', [])
        
        for fld in fields:
            field_name = getattr(fld, 'name', str(fld)).lower()
            
            # Quantity conservation inference (domain-agnostic)
            if any(qty_pattern in field_name for qty_pattern in self.QUANTITY_FIELDS):
                self._counter += 1
                self.inferred.append(CanonicalInvariant(
                    invariant_id=f"inv:{self._counter}",
                    invariant_type=InvariantType.STOCK_CONSERVATION,
                    description=f"{entity_name}.{field_name} must remain >= 0",
                    source_entity=entity_name,
                    trigger="decrement",
                    effect=f"{field_name} >= 0",
                    confidence=0.9
                ))
            
            # Referential integrity inference
            if any(ref in field_name for ref in self.REFERENCE_PATTERNS):
                if field_name.endswith('_id') and field_name != 'id':
                    ref_entity = field_name[:-3].title()
                    self._counter += 1
                    self.inferred.append(CanonicalInvariant(
                        invariant_id=f"inv:{self._counter}",
                        invariant_type=InvariantType.REFERENTIAL_INTEGRITY,
                        description=f"{entity_name}.{field_name} references {ref_entity}",
                        source_entity=entity_name,
                        target_entity=ref_entity,
                        trigger="create/update",
                        effect=f"{ref_entity}.exists({field_name})",
                        confidence=0.85
                    ))
    
    def _infer_from_relationship(self, rel: Any):
        """Infer invariants from entity relationships."""
        source = getattr(rel, 'source_entity', getattr(rel, 'from_entity', None))
        target = getattr(rel, 'target_entity', getattr(rel, 'to_entity', None))
        rel_type = getattr(rel, 'type', 'reference')
        
        if source and target:
            self._counter += 1
            self.inferred.append(CanonicalInvariant(
                invariant_id=f"inv:{self._counter}",
                invariant_type=InvariantType.REFERENTIAL_INTEGRITY,
                description=f"{source} → {target} ({rel_type})",
                source_entity=source,
                target_entity=target,
                effect=f"{target}.exists",
                confidence=0.95
            ))
    
    def _infer_from_flow(self, flow: Any):
        """Infer invariants from flow definitions."""
        flow_name = getattr(flow, 'name', '')
        entities = getattr(flow, 'entities_involved', [])
        postconds = getattr(flow, 'postconditions', [])
        
        # Multi-entity flow → likely cascade effect
        if len(entities) > 1:
            self._counter += 1
            self.inferred.append(CanonicalInvariant(
                invariant_id=f"inv:{self._counter}",
                invariant_type=InvariantType.CASCADE_EFFECT,
                description=f"Flow '{flow_name}' affects: {', '.join(entities)}",
                source_entity=entities[0] if entities else "Unknown",
                target_entity=entities[1] if len(entities) > 1 else None,
                trigger=flow_name,
                confidence=0.8
            ))
        
        # Infer implications from postconditions
        for postcond in postconds:
            if '→' in postcond or '->' in postcond:
                self._parse_implication(postcond, flow_name)
    
    def _parse_implication(self, postcond: str, flow_name: str):
        """Parse an implication from postcondition."""
        parts = postcond.replace('→', '->').split('->')
        if len(parts) == 2:
            trigger = parts[0].strip()
            effect = parts[1].strip()
            self.implications.append(Implication(
                trigger_entity=flow_name,
                trigger_condition=trigger,
                implied_entity="*",
                implied_condition=effect
            ))
    
    def detect_cross_entity_implications(self, ir: Any) -> List[Implication]:
        """Detect implications across entities."""
        # First infer from IR if not done
        if not self.inferred:
            self.infer_from_ir(ir)
        return self.implications
    
    def get_invariants_for_entity(self, entity: str) -> List[CanonicalInvariant]:
        """Get all invariants involving an entity."""
        return [inv for inv in self.inferred 
                if inv.source_entity.lower() == entity.lower() 
                or (inv.target_entity and inv.target_entity.lower() == entity.lower())]

