"""
Failure Classifier for IR-Agnostic Runtime Repair.

Phase 2.1: Classifies smoke test failures using only IR semantics.

Three failure types:
1. MISSING_PRECONDITION - Required entity/state doesn't exist
2. WRONG_STATUS_CODE - IR says valid, code returns error
3. MISSING_SIDE_EFFECT - Postcondition not satisfied after execution
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import structlog

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.behavior_model import Flow

logger = structlog.get_logger(__name__)


class FailureType(str, Enum):
    """Classification of smoke test failures."""
    MISSING_PRECONDITION = "missing_precondition"  # 404 - entity doesn't exist
    WRONG_STATUS_CODE = "wrong_status_code"        # IR says valid, got error
    MISSING_SIDE_EFFECT = "missing_side_effect"    # Postcondition not met
    VALIDATION_ERROR = "validation_error"          # 422 - payload invalid
    UNKNOWN = "unknown"                            # Cannot classify


@dataclass
class ClassifiedFailure:
    """A smoke test failure with classification."""
    endpoint_path: str
    http_method: str
    expected_status: int
    actual_status: int
    failure_type: FailureType
    details: Dict[str, Any]
    suggested_repair: Optional[str] = None
    ir_flow: Optional[Flow] = None


class FailureClassifier:
    """
    Classifies smoke test failures using IR semantics.
    
    Domain-agnostic: Uses only IR models, never entity names.
    """
    
    def __init__(self, app_ir: ApplicationIR):
        self.app_ir = app_ir
        self._flow_map = self._build_flow_map()
    
    def _build_flow_map(self) -> Dict[str, Flow]:
        """Build endpoint → flow mapping."""
        flow_map = {}
        for flow in self.app_ir.get_flows():
            if flow.endpoint:
                flow_map[flow.endpoint.lower()] = flow
        return flow_map
    
    def classify(
        self,
        endpoint_path: str,
        http_method: str,
        expected_status: int,
        actual_status: int,
        request_body: Optional[Dict] = None,
        response_body: Optional[Dict] = None
    ) -> ClassifiedFailure:
        """
        Classify a smoke test failure.
        
        Returns ClassifiedFailure with type and suggested repair.
        """
        details: Dict[str, Any] = {
            "request_body": request_body,
            "response_body": response_body,
        }
        
        # Find associated flow
        endpoint_key = f"{http_method.upper()} {endpoint_path}".lower()
        flow = self._flow_map.get(endpoint_key)
        
        # Classification logic
        failure_type = self._classify_by_status_codes(
            expected_status, actual_status, response_body
        )
        
        # Add IR-based context
        if flow:
            details["flow_name"] = flow.name
            details["preconditions"] = flow.preconditions
            details["postconditions"] = flow.postconditions
        
        # Generate suggested repair
        suggested_repair = self._suggest_repair(failure_type, details)
        
        return ClassifiedFailure(
            endpoint_path=endpoint_path,
            http_method=http_method,
            expected_status=expected_status,
            actual_status=actual_status,
            failure_type=failure_type,
            details=details,
            suggested_repair=suggested_repair,
            ir_flow=flow
        )
    
    def _classify_by_status_codes(
        self,
        expected: int,
        actual: int,
        response_body: Optional[Dict]
    ) -> FailureType:
        """Classify based on status code patterns."""
        
        # 404 when expecting success → Missing precondition
        if actual == 404 and expected in [200, 201, 204]:
            return FailureType.MISSING_PRECONDITION
        
        # 422 when expecting success → Validation error
        if actual == 422 and expected in [200, 201]:
            return FailureType.VALIDATION_ERROR
        
        # 500 → Usually missing side effect or code bug
        if actual == 500:
            return FailureType.MISSING_SIDE_EFFECT
        
        # Expected error but got success → Wrong status code
        if expected in [400, 404, 422] and actual in [200, 201, 204]:
            return FailureType.WRONG_STATUS_CODE
        
        # Expected success but got different error
        if expected in [200, 201, 204] and actual in [400, 422]:
            return FailureType.VALIDATION_ERROR
        
        return FailureType.UNKNOWN
    
    def _suggest_repair(
        self,
        failure_type: FailureType,
        details: Dict[str, Any]
    ) -> str:
        """Generate domain-agnostic repair suggestion."""
        
        if failure_type == FailureType.MISSING_PRECONDITION:
            return "Seed missing entity before test execution"
        
        if failure_type == FailureType.VALIDATION_ERROR:
            return "Check request body matches IR schema requirements"
        
        if failure_type == FailureType.WRONG_STATUS_CODE:
            return "Update route handler to return correct status code from IR"
        
        if failure_type == FailureType.MISSING_SIDE_EFFECT:
            preconditions = details.get("preconditions", [])
            if preconditions:
                return f"Ensure preconditions are met: {preconditions}"
            return "Check service layer implements required business logic"
        
        return "Manual investigation required"
    
    def classify_batch(
        self,
        failures: List[Dict[str, Any]]
    ) -> List[ClassifiedFailure]:
        """Classify multiple failures."""
        return [
            self.classify(
                endpoint_path=f["endpoint_path"],
                http_method=f["http_method"],
                expected_status=f["expected_status"],
                actual_status=f["actual_status"],
                request_body=f.get("request_body"),
                response_body=f.get("response_body")
            )
            for f in failures
        ]

