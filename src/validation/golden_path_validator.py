"""
Golden Path Validator - Validates critical business workflows.

Golden paths are the most important workflows that MUST work:
- E-commerce: Create Product → Add to Cart → Checkout → Pay → Complete
- E-commerce: Create Cart → Add Items → Remove Item → Clear Cart
- E-commerce: Create Order → Cancel Order

If a golden path fails, we fail fast - no point testing edge cases.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Awaitable
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class GoldenPathStatus(str, Enum):
    """Status of a golden path validation."""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class GoldenStep:
    """A step in a golden path."""
    order: int
    name: str
    method: str  # GET, POST, PUT, DELETE
    endpoint: str
    expected_status: int
    body: Optional[Dict[str, Any]] = None
    extract: Optional[Dict[str, str]] = None  # {"var_name": "$.response.id"}


@dataclass
class GoldenPath:
    """A golden path definition."""
    path_id: str
    name: str
    description: str
    steps: List[GoldenStep]
    priority: int = 1  # 1 = highest


@dataclass
class GoldenPathResult:
    """Result of validating a golden path."""
    path: GoldenPath
    status: GoldenPathStatus
    steps_passed: int
    steps_total: int
    failed_step: Optional[GoldenStep] = None
    error_detail: Optional[str] = None
    duration_ms: float = 0.0


class GoldenPathValidator:
    """
    Validates critical business workflows before full smoke tests.
    
    Benefits:
    - Fail fast on broken core functionality
    - Prioritize repair efforts
    - Track workflow health over time
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.paths: Dict[str, GoldenPath] = {}
        self.results: List[GoldenPathResult] = []
        self._http_client: Optional[Any] = None
    
    def register_path(self, path: GoldenPath):
        """Register a golden path for validation."""
        self.paths[path.path_id] = path
        logger.info(f"Registered golden path: {path.name}")
    
    def register_paths_from_ir(self, ir: Any):
        """
        Register golden paths from ApplicationIR flows.

        100% domain-agnostic - paths are derived from IR, not hardcoded.
        """
        if not ir:
            logger.warning("No IR provided for golden path registration")
            return

        try:
            # Extract flows from BehaviorModelIR
            behavior_ir = getattr(ir, 'behavior_model_ir', None)
            if not behavior_ir:
                return

            flows = getattr(behavior_ir, 'flows', [])
            for i, flow in enumerate(flows):
                flow_name = getattr(flow, 'name', f'flow_{i}')
                flow_id = getattr(flow, 'id', flow_name)

                # Build steps from flow operations
                steps = []
                operations = getattr(flow, 'operations', [])
                for j, op in enumerate(operations):
                    op_name = getattr(op, 'name', f'step_{j}')
                    method = getattr(op, 'method', 'POST')
                    endpoint = getattr(op, 'endpoint', f'/{flow_name}')
                    expected_status = getattr(op, 'expected_status', 200 if method == 'GET' else 201)
                    body = getattr(op, 'body', None)

                    steps.append(GoldenStep(
                        order=j + 1,
                        name=op_name,
                        method=method,
                        endpoint=endpoint,
                        expected_status=expected_status,
                        body=body
                    ))

                if steps:
                    self.register_path(GoldenPath(
                        path_id=f"ir:{flow_id}",
                        name=flow_name,
                        description=getattr(flow, 'description', ''),
                        priority=i + 1,
                        steps=steps
                    ))
        except Exception as e:
            logger.error(f"Failed to register paths from IR: {e}")
    
    async def validate_path(self, path: GoldenPath) -> GoldenPathResult:
        """Validate a single golden path."""
        import time
        start = time.time()
        
        steps_passed = 0
        context: Dict[str, Any] = {}
        
        for step in sorted(path.steps, key=lambda s: s.order):
            try:
                # Substitute variables in endpoint
                endpoint = self._substitute(step.endpoint, context)
                body = self._substitute_dict(step.body, context) if step.body else None
                
                # Execute step
                status, response = await self._execute_step(step.method, endpoint, body)
                
                if status != step.expected_status:
                    return GoldenPathResult(
                        path=path,
                        status=GoldenPathStatus.FAILED,
                        steps_passed=steps_passed,
                        steps_total=len(path.steps),
                        failed_step=step,
                        error_detail=f"Expected {step.expected_status}, got {status}",
                        duration_ms=(time.time() - start) * 1000
                    )
                
                # Extract variables for next steps
                if step.extract and response:
                    for var, jpath in step.extract.items():
                        context[var] = self._extract_value(response, jpath)
                
                steps_passed += 1
                
            except Exception as e:
                return GoldenPathResult(
                    path=path,
                    status=GoldenPathStatus.FAILED,
                    steps_passed=steps_passed,
                    steps_total=len(path.steps),
                    failed_step=step,
                    error_detail=str(e),
                    duration_ms=(time.time() - start) * 1000
                )
        
        return GoldenPathResult(
            path=path,
            status=GoldenPathStatus.PASSED,
            steps_passed=steps_passed,
            steps_total=len(path.steps),
            duration_ms=(time.time() - start) * 1000
        )
    
    async def validate_all(self) -> List[GoldenPathResult]:
        """Validate all registered golden paths."""
        self.results = []
        sorted_paths = sorted(self.paths.values(), key=lambda p: p.priority)
        
        for path in sorted_paths:
            result = await self.validate_path(path)
            self.results.append(result)
            
            if result.status == GoldenPathStatus.FAILED and path.priority == 1:
                logger.error(f"Critical golden path failed: {path.name}")
                break  # Fail fast on priority 1
        
        return self.results
    
    async def _execute_step(self, method: str, endpoint: str, body: Optional[Dict]) -> tuple:
        """Execute an HTTP step. Override for actual HTTP calls."""
        # Placeholder - in real use, inject httpx client
        logger.info(f"Would execute: {method} {endpoint}")
        return (200, {})
    
    def _substitute(self, template: str, context: Dict) -> str:
        """Substitute {var} placeholders."""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    def _substitute_dict(self, d: Dict, context: Dict) -> Dict:
        """Substitute in dict values."""
        return {k: self._substitute(str(v), context) if isinstance(v, str) else v 
                for k, v in d.items()}
    
    def _extract_value(self, response: Dict, jpath: str) -> Any:
        """Extract value from response using simple path."""
        # Simple implementation - $.field.subfield
        parts = jpath.replace('$.', '').split('.')
        value = response
        for part in parts:
            value = value.get(part, {}) if isinstance(value, dict) else None
        return value

