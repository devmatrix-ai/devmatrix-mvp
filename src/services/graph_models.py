"""
Graph Models for Entity Relationship Graph (Phase 3)

Defines data structures for building semantic graphs of entities,
relationships, and constraints for validation inference.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class CardinalityType(Enum):
    """Relationship cardinality types"""
    ONE_TO_ONE = "one-to-one"
    ONE_TO_MANY = "one-to-many"
    MANY_TO_MANY = "many-to-many"
    MANY_TO_ONE = "many-to-one"


class RelationshipDirection(Enum):
    """Relationship direction"""
    FORWARD = "forward"
    BACKWARD = "backward"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class AttributeNode:
    """Represents an entity attribute/field"""
    name: str
    type: str  # "string", "integer", "uuid", "datetime", etc.
    required: bool = False
    is_primary_key: bool = False
    is_unique: bool = False
    allowed_values: Optional[List[str]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern if applicable


@dataclass
class EntityNode:
    """Represents a business entity in the graph"""
    name: str
    attributes: Dict[str, AttributeNode] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)

    # Computed properties
    is_aggregate_root: bool = False
    domain_context: str = "default"  # Bounded context
    lifecycle_states: Optional[List[str]] = None  # Status values if stateful
    created_at: Optional[str] = None  # Timestamp field name
    updated_at: Optional[str] = None  # Timestamp field name
    deleted_at: Optional[str] = None  # Soft delete field name

    def add_attribute(self, attr: AttributeNode) -> None:
        """Add an attribute to this entity"""
        self.attributes[attr.name] = attr

    def get_primary_key(self) -> Optional[str]:
        """Get the primary key field name"""
        for attr_name, attr in self.attributes.items():
            if attr.is_primary_key:
                return attr_name
        return None

    def get_status_field(self) -> Optional[str]:
        """Get the status/state field name"""
        for attr_name in self.attributes.keys():
            if any(kw in attr_name.lower() for kw in ["status", "state", "stage"]):
                return attr_name
        return None


@dataclass
class RelationshipEdge:
    """Represents a relationship between two entities"""
    source: str  # Source entity name
    target: str  # Target entity name
    type: str  # "one-to-many", "many-to-many", etc.
    cardinality: Tuple[str, str]  # ("1", "N"), ("1", "1"), etc.
    direction: RelationshipDirection = RelationshipDirection.FORWARD

    # Relationship properties
    foreign_key_field: Optional[str] = None
    required: bool = False
    cascade_delete: bool = False
    cascade_update: bool = False
    depends_on: Optional[str] = None  # This relationship depends on another

    # Derived constraints and rules
    implied_constraints: List[Dict] = field(default_factory=list)
    business_rules: List[Dict] = field(default_factory=list)

    def add_constraint(self, constraint_type: str, description: str, confidence: float = 0.85) -> None:
        """Add an inferred constraint"""
        self.implied_constraints.append({
            "type": constraint_type,
            "description": description,
            "confidence": confidence
        })

    def add_business_rule(self, rule: str, confidence: float = 0.80) -> None:
        """Add an inferred business rule"""
        self.business_rules.append({
            "rule": rule,
            "confidence": confidence
        })


@dataclass
class GraphMetrics:
    """Metrics about the entity relationship graph"""
    total_entities: int = 0
    total_relationships: int = 0
    total_attributes: int = 0
    aggregate_roots: int = 0
    many_to_many_relationships: int = 0
    cascade_delete_relationships: int = 0
    max_relationship_depth: int = 0
    average_attributes_per_entity: float = 0.0


@dataclass
class InferredValidation:
    """A validation rule inferred from the graph"""
    entity: str
    attribute: Optional[str]
    validation_type: str  # PRESENCE, UNIQUENESS, RELATIONSHIP, etc.
    condition: str
    error_message: str
    source: str  # "cardinality", "cascade_delete", "workflow", "aggregate_root", etc.
    confidence: float  # 0.0-1.0
    related_entity: Optional[str] = None
    related_relationship: Optional[Tuple[str, str]] = None  # (source, target)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "entity": self.entity,
            "attribute": self.attribute,
            "type": self.validation_type,
            "condition": self.condition,
            "error_message": self.error_message,
            "source": self.source,
            "confidence": self.confidence,
            "related_entity": self.related_entity
        }
