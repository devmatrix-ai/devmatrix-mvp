"""
Behavior Model Intermediate Representation.

Defines the dynamic behavior of the system: flows, invariants, policies, and state transitions.

Extended for IR-Centric Cognitive Code Generation (Bug #160 / Proposal v2.0).
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import hashlib


class FlowType(str, Enum):
    WORKFLOW = "workflow"      # Complex multi-step process
    STATE_TRANSITION = "state_transition"
    POLICY = "policy"          # Invariant or rule
    EVENT_HANDLER = "event_handler"


class Step(BaseModel):
    order: int
    description: str
    action: str
    target_entity: Optional[str] = None
    condition: Optional[str] = None


class Flow(BaseModel):
    """
    Flow represents a behavioral unit in the IR.

    Extended with IRFlow fields for IR-Centric Cognitive Code Generation.
    These fields enable:
    - Semantic pattern matching (by flow, not file path)
    - Function-level code enhancement
    - IR contract extraction for LLM prompts
    - Cache key generation based on IR semantics
    """
    # Original fields
    name: str
    type: FlowType
    trigger: str  # e.g., "On Checkout", "Before Save"
    steps: List[Step] = Field(default_factory=list)
    description: Optional[str] = None

    # =========================================================================
    # IRFlow Extension Fields (for Cognitive Code Generation)
    # All optional for backwards compatibility
    # =========================================================================

    # Unique identifier for the flow (e.g., "add_item_to_cart")
    flow_id: Optional[str] = None

    # Primary entity this flow operates on (e.g., "Cart")
    primary_entity: Optional[str] = None

    # All entities involved in this flow (e.g., ["Cart", "Product", "CartItem"])
    entities_involved: List[str] = Field(default_factory=list)

    # Constraint types applied (e.g., ["stock_constraint", "workflow_constraint"])
    constraint_types: List[str] = Field(default_factory=list)

    # Preconditions that must be true before flow executes
    # e.g., ["cart.status == 'open'", "product.exists", "quantity > 0"]
    preconditions: List[str] = Field(default_factory=list)

    # Postconditions that must be true after flow executes
    # e.g., ["cart_item.added", "product.stock.decreased"]
    postconditions: List[str] = Field(default_factory=list)

    # API endpoint this flow implements (e.g., "POST /carts/{id}/items")
    endpoint: Optional[str] = None

    # Function name in generated code (e.g., "add_item_to_cart")
    implementation_name: Optional[str] = None

    # File where this flow is implemented (e.g., "src/services/cart_service.py")
    implementation_file: Optional[str] = None

    # Version for cache invalidation
    version: str = "1.0.0"

    # =========================================================================
    # IRFlow Methods
    # =========================================================================

    def get_flow_id(self) -> str:
        """Get or generate flow_id."""
        if self.flow_id:
            return self.flow_id
        # Generate from name if not set
        return self.name.lower().replace(" ", "_").replace("-", "_")

    def get_cache_key_components(self) -> Dict[str, Any]:
        """Get components for generating cache key."""
        return {
            "flow_id": self.get_flow_id(),
            "version": self.version,
            "entities": sorted(self.entities_involved),
            "constraints": sorted(self.constraint_types),
        }

    def compute_semantic_hash(self) -> str:
        """Compute hash based on semantic properties (for caching)."""
        components = self.get_cache_key_components()
        key_str = f"{components['flow_id']}:{components['version']}:{':'.join(components['entities'])}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def matches_entity(self, entity_name: str) -> bool:
        """Check if this flow involves a specific entity."""
        if self.primary_entity and self.primary_entity.lower() == entity_name.lower():
            return True
        return any(e.lower() == entity_name.lower() for e in self.entities_involved)

    def matches_constraint_type(self, constraint_type: str) -> bool:
        """Check if this flow has a specific constraint type."""
        return any(
            ct.lower() == constraint_type.lower()
            for ct in self.constraint_types
        )

    def to_ir_contract_dict(self) -> Dict[str, Any]:
        """Export as dictionary for IR contract building."""
        return {
            "flow_id": self.get_flow_id(),
            "name": self.name,
            "primary_entity": self.primary_entity,
            "entities_involved": self.entities_involved,
            "constraint_types": self.constraint_types,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "endpoint": self.endpoint,
            "implementation_name": self.implementation_name,
            "implementation_file": self.implementation_file,
        }

class Invariant(BaseModel):
    """A condition that must always be true."""
    entity: str
    description: str
    expression: Optional[str] = None  # e.g., "balance >= 0"
    enforcement_level: str = "strict" # strict, eventual

class BehaviorModelIR(BaseModel):
    flows: List[Flow] = Field(default_factory=list)
    invariants: List[Invariant] = Field(default_factory=list)

    # =========================================================================
    # Query Methods for IR-Centric Cognitive Code Generation
    # =========================================================================

    def get_flows_for_file(self, file_path: str) -> List[Flow]:
        """
        Get all flows implemented in a specific file.

        Used by IRCentricCognitivePass to map files → flows.
        """
        # Normalize path for comparison
        normalized = file_path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]

        return [
            flow for flow in self.flows
            if flow.implementation_file and normalized.endswith(
                flow.implementation_file.replace("\\", "/").lstrip("./")
            )
        ]

    def get_flows_for_entity(self, entity_name: str) -> List[Flow]:
        """Get all flows involving a specific entity."""
        return [
            flow for flow in self.flows
            if flow.matches_entity(entity_name)
        ]

    def get_flows_for_endpoint(self, endpoint: str) -> List[Flow]:
        """Get flows matching an endpoint pattern."""
        # Normalize endpoint for comparison
        normalized = endpoint.lower().strip()
        return [
            flow for flow in self.flows
            if flow.endpoint and flow.endpoint.lower().strip() == normalized
        ]

    def get_flows_by_constraint_type(self, constraint_type: str) -> List[Flow]:
        """Get all flows with a specific constraint type."""
        return [
            flow for flow in self.flows
            if flow.matches_constraint_type(constraint_type)
        ]

    def get_all_constraint_types(self) -> List[str]:
        """Get unique list of all constraint types across flows."""
        types = set()
        for flow in self.flows:
            types.update(flow.constraint_types)
        return sorted(types)

    def get_all_entities_in_flows(self) -> List[str]:
        """Get unique list of all entities involved in flows."""
        entities = set()
        for flow in self.flows:
            if flow.primary_entity:
                entities.add(flow.primary_entity)
            entities.update(flow.entities_involved)
        return sorted(entities)
