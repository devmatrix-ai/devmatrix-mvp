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

class APIModelIR(BaseModel):
    endpoints: List[Endpoint]
    schemas: List[APISchema] = Field(default_factory=list)
    base_path: str = "/api/v1"
    version: str = "v1"
