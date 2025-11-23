"""
Application Intermediate Representation (Root).

The single source of truth for the application being generated.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from src.cognitive.ir.domain_model import DomainModelIR
from src.cognitive.ir.api_model import APIModelIR
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR
from src.cognitive.ir.behavior_model import BehaviorModelIR
from src.cognitive.ir.validation_model import ValidationModelIR

class ApplicationIR(BaseModel):
    """
    Root Aggregate for the Application Intermediate Representation.
    """
    app_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    
    # Sub-models
    domain_model: DomainModelIR
    api_model: APIModelIR
    infrastructure_model: InfrastructureModelIR
    behavior_model: BehaviorModelIR = Field(default_factory=BehaviorModelIR)
    validation_model: ValidationModelIR = Field(default_factory=ValidationModelIR)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    # Phase tracking
    phase_status: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        frozen = False  # Allow updates during builder phase, but treat as immutable between phases ideally
