"""
API Model Intermediate Representation.

Defines the endpoints, request/response schemas, and API structure.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class ParameterLocation(str, Enum):
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"

class APIParameter(BaseModel):
    name: str
    location: ParameterLocation
    data_type: str
    required: bool = True
    description: Optional[str] = None

class APISchemaField(BaseModel):
    name: str
    type: str
    required: bool = True
    description: Optional[str] = None

class APISchema(BaseModel):
    name: str
    fields: List[APISchemaField]

class InferenceSource(str, Enum):
    """Source of inferred endpoints."""
    SPEC = "spec"                    # Explicitly in spec
    CRUD_BEST_PRACTICE = "crud_best_practice"  # list, delete inferred
    INFRA_BEST_PRACTICE = "infra_best_practice"  # health, metrics
    PATTERN_BANK = "pattern_bank"    # From successful patterns


class Endpoint(BaseModel):
    path: str
    method: HttpMethod
    operation_id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[APIParameter] = Field(default_factory=list)
    request_schema: Optional[APISchema] = None
    response_schema: Optional[APISchema] = None
    auth_required: bool = True
    tags: List[str] = Field(default_factory=list)

    # Inference tracking - IR as single source of truth
    inferred: bool = False
    inference_source: InferenceSource = InferenceSource.SPEC
    inference_reason: Optional[str] = None

class APIModelIR(BaseModel):
    endpoints: List[Endpoint]
    schemas: List[APISchema] = Field(default_factory=list)
    # Bug #65 Fix: Changed from "/api/v1" to "" to match generated code
    # Generated routers don't use API prefix (e.g., router mounted directly without prefix)
    base_path: str = ""
    version: str = "v1"
