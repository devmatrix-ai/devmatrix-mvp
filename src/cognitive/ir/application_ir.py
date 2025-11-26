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

    # ============================================================
    # Convenience Methods (IR-centric accessors)
    # ============================================================

    def get_entities(self) -> list:
        """Get all entities from DomainModelIR."""
        if self.domain_model and self.domain_model.entities:
            return self.domain_model.entities
        return []

    def get_endpoints(self) -> list:
        """Get all endpoints from APIModelIR."""
        if self.api_model and self.api_model.endpoints:
            return self.api_model.endpoints
        return []

    def get_flows(self) -> list:
        """Get all flows from BehaviorModelIR."""
        if self.behavior_model and self.behavior_model.flows:
            return self.behavior_model.flows
        return []

    def get_validation_rules(self) -> list:
        """Get all validation rules from ValidationModelIR."""
        if self.validation_model and self.validation_model.rules:
            return self.validation_model.rules
        return []

    def get_dag_ground_truth(self) -> dict:
        """
        Derive DAG ground truth for multi-pass planning.

        Returns:
            Dict with node_count (entities + flows) and edge_count (invariants + relationships).
        """
        entity_count = len(self.get_entities())
        flow_count = len(self.get_flows())

        # Count edges: invariants + entity relationships
        edge_count = 0
        if self.behavior_model and self.behavior_model.invariants:
            edge_count = len(self.behavior_model.invariants)

        for entity in self.get_entities():
            if hasattr(entity, 'relationships') and entity.relationships:
                edge_count += len(entity.relationships)

        return {
            "node_count": entity_count + flow_count,
            "edge_count": edge_count,
            "entities": entity_count,
            "flows": flow_count,
            "source": "ApplicationIR"
        }

    def get_requirements_summary(self) -> dict:
        """
        Get summary of all requirements/components in the IR.

        Returns:
            Dict with counts: total, functional, entities, endpoints, validations, flows.
        """
        entity_count = len(self.get_entities())
        endpoint_count = len(self.get_endpoints())
        validation_count = len(self.get_validation_rules())
        flow_count = len(self.get_flows())

        # Functional = entities + endpoints + flows (things that generate code)
        functional_count = entity_count + endpoint_count + flow_count

        return {
            "total": functional_count + validation_count,
            "functional": functional_count,
            "entities": entity_count,
            "endpoints": endpoint_count,
            "validations": validation_count,
            "flows": flow_count,
            "source": "ApplicationIR"
        }

    def get_metadata(self) -> dict:
        """Get IR metadata as dict."""
        return {
            "app_id": str(self.app_id),
            "spec_name": self.name,
            "description": self.description or "",
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source": "ApplicationIR"
        }
