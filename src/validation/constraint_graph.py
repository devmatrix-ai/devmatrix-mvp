"""
ConstraintGraph - Bipartite graph for multi-entity constraint tracking.

Tracks relationships between:
- Constraints ↔ Entities
- Transitions ↔ States
- Guards ↔ Steps

Used to:
- Detect multi-entity violations
- Find cascade effects of repairs
- Track constraint dependencies
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of nodes in the constraint graph."""
    CONSTRAINT = "constraint"
    ENTITY = "entity"
    TRANSITION = "transition"
    STATE = "state"
    GUARD = "guard"
    STEP = "step"


@dataclass
class GraphNode:
    """A node in the constraint graph."""
    node_id: str
    node_type: NodeType
    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge connecting two nodes."""
    from_node: str  # node_id
    to_node: str    # node_id
    edge_type: str  # e.g., "applies_to", "triggers", "guards"
    weight: float = 1.0


@dataclass
class CascadeEffect:
    """Represents a cascade effect from a repair."""
    source_constraint: str
    affected_constraints: List[str]
    affected_entities: List[str]
    risk_level: str  # low, medium, high


class ConstraintGraph:
    """
    Bipartite graph for tracking constraint-entity relationships.
    
    Enables:
    - Multi-entity violation detection
    - Cascade regression detection
    - Constraint chain analysis
    """
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        # Index for fast lookups
        self._entity_constraints: Dict[str, Set[str]] = {}  # entity → constraints
        self._constraint_entities: Dict[str, Set[str]] = {}  # constraint → entities
    
    def add_node(self, node_id: str, node_type: NodeType, name: str, **metadata) -> GraphNode:
        """Add a node to the graph."""
        node = GraphNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            metadata=metadata
        )
        self.nodes[node_id] = node
        return node
    
    def add_constraint(self, constraint_id: str, name: str, entities: List[str], **metadata):
        """Add a constraint and link it to entities."""
        # Add constraint node
        self.add_node(constraint_id, NodeType.CONSTRAINT, name, **metadata)
        
        # Track constraint → entities
        self._constraint_entities[constraint_id] = set()
        
        for entity in entities:
            entity_id = f"entity:{entity.lower()}"
            
            # Add entity node if not exists
            if entity_id not in self.nodes:
                self.add_node(entity_id, NodeType.ENTITY, entity)
            
            # Add edge
            self.edges.append(GraphEdge(
                from_node=constraint_id,
                to_node=entity_id,
                edge_type="applies_to"
            ))
            
            # Update indices
            self._constraint_entities[constraint_id].add(entity)
            if entity not in self._entity_constraints:
                self._entity_constraints[entity] = set()
            self._entity_constraints[entity].add(constraint_id)
    
    def add_transition(self, transition_id: str, entity: str, from_state: str, to_state: str):
        """Add a state transition."""
        self.add_node(transition_id, NodeType.TRANSITION, f"{from_state}→{to_state}")
        
        from_id = f"state:{entity}:{from_state}"
        to_id = f"state:{entity}:{to_state}"
        
        if from_id not in self.nodes:
            self.add_node(from_id, NodeType.STATE, from_state, entity=entity)
        if to_id not in self.nodes:
            self.add_node(to_id, NodeType.STATE, to_state, entity=entity)
        
        self.edges.append(GraphEdge(transition_id, from_id, "from"))
        self.edges.append(GraphEdge(transition_id, to_id, "to"))
    
    def find_affected_entities(self, constraint_id: str) -> List[str]:
        """Find all entities affected by a constraint."""
        return list(self._constraint_entities.get(constraint_id, set()))
    
    def find_constraints_for_entity(self, entity: str) -> List[str]:
        """Find all constraints that apply to an entity."""
        return list(self._entity_constraints.get(entity, set()))
    
    def is_multi_entity_constraint(self, constraint_id: str) -> bool:
        """Check if a constraint spans multiple entities."""
        entities = self._constraint_entities.get(constraint_id, set())
        return len(entities) > 1
    
    def detect_cascade_regression(self, constraint_id: str, fix_entities: List[str]) -> CascadeEffect:
        """Detect potential cascade effects from fixing a constraint."""
        affected_constraints = set()
        affected_entities = set(fix_entities)
        
        # Find other constraints that share entities
        for entity in fix_entities:
            for other_constraint in self._entity_constraints.get(entity, set()):
                if other_constraint != constraint_id:
                    affected_constraints.add(other_constraint)
                    # Add entities of affected constraints
                    affected_entities.update(self._constraint_entities.get(other_constraint, set()))
        
        risk = "low"
        if len(affected_constraints) > 3:
            risk = "high"
        elif len(affected_constraints) > 1:
            risk = "medium"
        
        return CascadeEffect(
            source_constraint=constraint_id,
            affected_constraints=list(affected_constraints),
            affected_entities=list(affected_entities),
            risk_level=risk
        )

