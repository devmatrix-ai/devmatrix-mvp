"""
Infrastructure Model Intermediate Representation.

Defines the infrastructure components, database configuration, and deployment settings.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    NEO4J = "neo4j"
    QDRANT = "qdrant"

class ContainerService(BaseModel):
    name: str
    image: str
    ports: List[str] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    volumes: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)

class DatabaseConfig(BaseModel):
    type: DatabaseType
    host: str = "localhost"
    port: int
    name: str
    user: str
    password_env_var: str

class ObservabilityConfig(BaseModel):
    logging_enabled: bool = True
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    health_check_path: str = "/health"

class InfrastructureModelIR(BaseModel):
    database: DatabaseConfig
    vector_db: Optional[DatabaseConfig] = None
    graph_db: Optional[DatabaseConfig] = None
    containers: List[ContainerService] = Field(default_factory=list)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    docker_compose_version: str = "3.8"
