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
    source_entity: str
    target_entity: str
    type: RelationshipType
    field_name: str
    back_populates: Optional[str] = None

class Entity(BaseModel):
    name: str
    attributes: List[Attribute]
    relationships: List[Relationship] = Field(default_factory=list)
    description: Optional[str] = None
    is_aggregate_root: bool = False

class DomainModelIR(BaseModel):
    entities: List[Entity]
    metadata: Dict[str, Any] = Field(default_factory=dict)
