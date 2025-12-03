"""
Domain Model Intermediate Representation.

Defines the entities, attributes, and relationships that make up the business domain.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    UUID = "UUID"
    JSON = "json"
    ENUM = "enum"

class Attribute(BaseModel):
    name: str
    data_type: DataType
    is_primary_key: bool = False
    is_nullable: bool = False
    is_unique: bool = False
    default_value: Optional[Any] = None
    description: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)

class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

class Relationship(BaseModel):
    """
    Relationship between entities.

    Extended for nested resource APIs (Bug #218 Fix):
    - path_segment: URL segment for nested routes (e.g., "items" for /carts/{id}/items)
    - fk_field: Foreign key field in child (e.g., "cart_id")
    - is_nested_resource: Whether this creates a nested API route
    - child_id_param: Path parameter name for child (e.g., "item_id")
    """
    source_entity: str  # Parent entity (e.g., "Cart")
    target_entity: str  # Child entity (e.g., "CartItem")
    type: RelationshipType
    field_name: str  # Relationship field name (e.g., "items")
    back_populates: Optional[str] = None

    # Nested resource API fields (domain-agnostic)
    path_segment: Optional[str] = None  # URL path segment (e.g., "items")
    fk_field: Optional[str] = None  # FK field in child (e.g., "cart_id")
    is_nested_resource: bool = False  # Generates nested routes like /{parent}/{id}/{segment}
    child_id_param: Optional[str] = None  # Path param name (e.g., "item_id")

    # Field mappings for auto-population (e.g., CartItem.unit_price <- Product.price)
    field_mappings: Dict[str, str] = Field(default_factory=dict)  # {child_field: "RefEntity.field"}


class NestedResourceInfo(BaseModel):
    """
    Resolved nested resource information derived from Relationship.
    Used by code generators for domain-agnostic nested route generation.
    """
    parent_entity: str  # e.g., "Cart"
    child_entity: str  # e.g., "CartItem"
    path_segment: str  # e.g., "items"
    fk_field: str  # e.g., "cart_id"
    child_id_param: str  # e.g., "item_id"
    reference_fk: Optional[str] = None  # e.g., "product_id" (what the item references)
    reference_entity: Optional[str] = None  # e.g., "Product"
    field_mappings: Dict[str, str] = Field(default_factory=dict)


class Entity(BaseModel):
    name: str
    attributes: List[Attribute]
    relationships: List[Relationship] = Field(default_factory=list)
    description: Optional[str] = None
    is_aggregate_root: bool = False

class DomainModelIR(BaseModel):
    entities: List[Entity]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # =========================================================================
    # Nested Resource Query Methods (Domain-Agnostic)
    # =========================================================================

    def get_nested_resources(self) -> List[NestedResourceInfo]:
        """
        Get all nested resource relationships from the IR.

        Returns NestedResourceInfo for each parent-child relationship that
        generates nested API routes (e.g., /carts/{id}/items/{item_id}).

        100% IR-driven: Only returns relationships explicitly marked with is_nested_resource=True.
        No heuristics, no guessing from entity names.
        """
        nested = []

        for entity in self.entities:
            for rel in entity.relationships:
                if rel.is_nested_resource and rel.type == RelationshipType.ONE_TO_MANY:
                    # All info comes from IR - no inference
                    nested.append(NestedResourceInfo(
                        parent_entity=entity.name,
                        child_entity=rel.target_entity,
                        path_segment=rel.path_segment,
                        fk_field=rel.fk_field,
                        child_id_param=rel.child_id_param,
                        reference_fk=rel.field_mappings.get('_reference_fk'),
                        reference_entity=rel.field_mappings.get('_reference_entity'),
                        field_mappings={k: v for k, v in rel.field_mappings.items() if not k.startswith('_')},
                    ))

        return nested

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name (case-insensitive)."""
        name_lower = name.lower()
        for entity in self.entities:
            if entity.name.lower() == name_lower:
                return entity
        return None

    def get_nested_resource_for_child(self, child_entity: str) -> Optional[NestedResourceInfo]:
        """Get nested resource info for a child entity."""
        for nr in self.get_nested_resources():
            if nr.child_entity.lower() == child_entity.lower():
                return nr
        return None

    def get_nested_resource_for_parent(self, parent_entity: str) -> Optional[NestedResourceInfo]:
        """Get nested resource info for a parent entity."""
        for nr in self.get_nested_resources():
            if nr.parent_entity.lower() == parent_entity.lower():
                return nr
        return None
