"""
Hierarchical Extraction Data Models

Data structures for two-pass hierarchical LLM extraction to avoid truncation.
Pass 1 extracts global context, Pass 2 extracts entity details with context windows.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EntitySummary:
    """
    High-level entity summary from Pass 1 extraction.

    Attributes:
        name: Entity name (e.g., "Order", "Customer")
        location: Character position in spec where entity is defined
        description: Brief entity description
        relationships: List of related entity names
    """
    name: str
    location: int
    description: str
    relationships: List[str]


@dataclass
class Relationship:
    """
    Entity relationship captured in Pass 1.

    Attributes:
        source: Source entity name
        target: Target entity name
        type: Relationship type ("one_to_many", "many_to_many", "one_to_one")
        description: Relationship description
    """
    source: str
    target: str
    type: str  # "one_to_many", "many_to_many", "one_to_one"
    description: str


@dataclass
class EndpointSummary:
    """
    High-level endpoint summary from Pass 1.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: Endpoint path (e.g., "/api/orders/{id}")
        entity: Related entity name if applicable
    """
    method: str
    path: str
    entity: Optional[str]


@dataclass
class GlobalContext:
    """
    Complete global context extracted in Pass 1 from full spec.

    This structure captures the domain overview, entity relationships,
    business logic, and endpoints WITHOUT field-level details.
    Pass 2 uses this context to extract detailed entity fields.

    Attributes:
        domain: Domain description (e.g., "E-commerce platform")
        entities: List of entity summaries with locations
        relationships: List of entity relationships
        business_logic: List of business rules and constraints
        endpoints: List of endpoint summaries
    """
    domain: str
    entities: List[EntitySummary]
    relationships: List[Relationship]
    business_logic: List[str]
    endpoints: List[EndpointSummary]


@dataclass
class Field:
    """
    Field detail extracted in Pass 2.

    Attributes:
        name: Field name (e.g., "order_total", "created_at")
        type: Field type (string, integer, decimal, boolean, datetime, uuid)
        description: Field description and business meaning
        required: Whether field is required
        constraints: List of constraints (e.g., "unique", "length:1-255", "pattern:email")
        enforcement_type: "normal", "computed", "immutable", or "validator"
        enforcement_details: Details about enforcement (computed/immutable/validator)
    """
    name: str
    type: str
    description: str
    required: bool
    constraints: List[str]
    enforcement_type: str  # "normal", "computed", "immutable", "validator"
    enforcement_details: Optional[str] = None


@dataclass
class EntityDetail:
    """
    Complete entity details extracted in Pass 2.

    Attributes:
        entity: Entity name
        fields: List of fields in the entity
    """
    entity: str
    fields: List[Field]
