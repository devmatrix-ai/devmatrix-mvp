"""
IR-to-Repair Mapper for Domain-Agnostic Code Fixes.

Phase 2.3-2.4: Maps IR semantics to AST repair actions.

Repair types:
1. STATUS_CODE_FIX - Change response status code to match IR
2. SCHEMA_FIX - Update request schema validation
3. SEED_FIX - Add missing seed data
4. SERVICE_FIX - Inject service call from IR flow
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import structlog
import re

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.behavior_model import Flow
from src.validation.failure_classifier import ClassifiedFailure, FailureType

logger = structlog.get_logger(__name__)


class RepairType(str, Enum):
    """Types of code repairs."""
    STATUS_CODE_FIX = "status_code_fix"
    SCHEMA_FIX = "schema_fix"
    SEED_FIX = "seed_fix"
    SERVICE_FIX = "service_fix"
    NO_REPAIR = "no_repair"


@dataclass
class RepairAction:
    """A specific repair action to apply."""
    repair_type: RepairType
    target_file: str
    target_function: Optional[str] = None
    description: str = ""
    code_change: Optional[str] = None
    line_number: Optional[int] = None
    priority: int = 1  # 1 = highest


class IRRepairMapper:
    """
    Maps classified failures to repair actions using IR semantics.
    
    Domain-agnostic: Uses IR models only, never hardcodes entity names.
    """
    
    def __init__(self, app_ir: ApplicationIR, app_dir: str = ""):
        self.app_ir = app_ir
        self.app_dir = app_dir
        self._endpoint_map = self._build_endpoint_map()
    
    def _build_endpoint_map(self) -> Dict[str, Any]:
        """Build endpoint path → IR endpoint mapping."""
        endpoint_map = {}
        for ep in self.app_ir.get_endpoints():
            key = f"{ep.method.value.upper()} {ep.path}".lower()
            endpoint_map[key] = ep
        return endpoint_map
    
    def map_to_repairs(self, failure: ClassifiedFailure) -> List[RepairAction]:
        """
        Map a classified failure to repair actions.
        
        Returns list of RepairActions sorted by priority.
        """
        repairs = []
        
        if failure.failure_type == FailureType.MISSING_PRECONDITION:
            repairs.extend(self._map_missing_precondition(failure))
        
        elif failure.failure_type == FailureType.VALIDATION_ERROR:
            repairs.extend(self._map_validation_error(failure))
        
        elif failure.failure_type == FailureType.WRONG_STATUS_CODE:
            repairs.extend(self._map_wrong_status_code(failure))
        
        elif failure.failure_type == FailureType.MISSING_SIDE_EFFECT:
            repairs.extend(self._map_missing_side_effect(failure))
        
        # Sort by priority
        repairs.sort(key=lambda r: r.priority)
        return repairs
    
    def _map_missing_precondition(self, failure: ClassifiedFailure) -> List[RepairAction]:
        """Map MISSING_PRECONDITION to seed fixes."""
        # Extract entity from path
        entity = self._extract_entity_from_path(failure.endpoint_path)
        
        return [
            RepairAction(
                repair_type=RepairType.SEED_FIX,
                target_file="scripts/seed_db.py",
                description=f"Add seed data for {entity} entity",
                priority=1
            )
        ]
    
    def _map_validation_error(self, failure: ClassifiedFailure) -> List[RepairAction]:
        """Map VALIDATION_ERROR to schema fixes."""
        entity = self._extract_entity_from_path(failure.endpoint_path)
        route_file = f"src/api/routes/{entity.lower()}.py"
        
        repairs = []
        
        # Check if request body matches IR schema
        endpoint_key = f"{failure.http_method} {failure.endpoint_path}".lower()
        ir_endpoint = self._endpoint_map.get(endpoint_key)
        
        if ir_endpoint and ir_endpoint.request_body:
            repairs.append(RepairAction(
                repair_type=RepairType.SCHEMA_FIX,
                target_file=route_file,
                target_function=self._get_handler_name(failure),
                description=f"Update request schema to match IR: {ir_endpoint.request_body.name if hasattr(ir_endpoint.request_body, 'name') else 'schema'}",
                priority=2
            ))
        
        return repairs
    
    def _map_wrong_status_code(self, failure: ClassifiedFailure) -> List[RepairAction]:
        """Map WRONG_STATUS_CODE to status code fixes."""
        entity = self._extract_entity_from_path(failure.endpoint_path)
        route_file = f"src/api/routes/{entity.lower()}.py"
        
        return [
            RepairAction(
                repair_type=RepairType.STATUS_CODE_FIX,
                target_file=route_file,
                target_function=self._get_handler_name(failure),
                description=f"Change status_code from {failure.actual_status} to {failure.expected_status}",
                code_change=f"status_code={failure.expected_status}",
                priority=1
            )
        ]
    
    def _map_missing_side_effect(self, failure: ClassifiedFailure) -> List[RepairAction]:
        """Map MISSING_SIDE_EFFECT to service fixes."""
        entity = self._extract_entity_from_path(failure.endpoint_path)
        service_file = f"src/services/{entity.lower()}_service.py"
        
        repairs = []
        
        # Get postconditions from flow
        if failure.ir_flow:
            for postcondition in failure.ir_flow.postconditions:
                repairs.append(RepairAction(
                    repair_type=RepairType.SERVICE_FIX,
                    target_file=service_file,
                    description=f"Implement postcondition: {postcondition}",
                    priority=3
                ))
        
        return repairs if repairs else [
            RepairAction(
                repair_type=RepairType.SERVICE_FIX,
                target_file=service_file,
                description="Check business logic implementation",
                priority=3
            )
        ]
    
    def _extract_entity_from_path(self, path: str) -> str:
        """Extract primary entity from endpoint path."""
        # /products/{id} → Product
        # /carts/{id}/items → Cart
        parts = path.strip("/").split("/")
        if parts:
            entity = parts[0].rstrip("s")  # Remove plural 's'
            return entity.title()
        return "Unknown"
    
    def _get_handler_name(self, failure: ClassifiedFailure) -> str:
        """Generate route handler function name."""
        method = failure.http_method.lower()
        entity = self._extract_entity_from_path(failure.endpoint_path).lower()
        return f"{method}_{entity}"

