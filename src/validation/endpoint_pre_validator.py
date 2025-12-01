"""
Endpoint Pre-Validator - Bug #10 Fix

Compares IR endpoints vs generated route files BEFORE running smoke tests.
Identifies missing endpoints and generates them using LLM if needed.

This closes the gap where CodeRepair only handles endpoints detected by
Compliance Report (from OpenAPI), but some endpoints may never be generated
in the first place (like action endpoints: /products/{id}/deactivate).

Reference: DOCS/mvp/exit/SMOKE_AND_LEARNING_FIX_PLAN.md Bug #10
"""
import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EndpointGap:
    """Represents a missing endpoint that needs to be generated."""
    method: str
    path: str
    operation_id: str
    entity_name: str
    description: str = ""
    is_action: bool = False  # True for /activate, /deactivate, /checkout, etc.
    
    @property
    def signature(self) -> str:
        return f"{self.method} {self.path}"


@dataclass
class PreValidationResult:
    """Result of endpoint pre-validation."""
    ir_endpoints: List[str] = field(default_factory=list)
    code_endpoints: List[str] = field(default_factory=list)
    missing_endpoints: List[EndpointGap] = field(default_factory=list)
    extra_endpoints: List[str] = field(default_factory=list)
    coverage_rate: float = 0.0
    
    @property
    def has_gaps(self) -> bool:
        return len(self.missing_endpoints) > 0


class EndpointPreValidator:
    """
    Validates that all IR endpoints exist in generated code BEFORE smoke tests.
    
    This pre-emptive check catches missing endpoints that would otherwise
    only be discovered as 404 errors during smoke testing.
    """
    
    # Patterns for action endpoints that are commonly missing
    ACTION_PATTERNS = [
        r'/\{[^}]+\}/activate',
        r'/\{[^}]+\}/deactivate', 
        r'/\{[^}]+\}/checkout',
        r'/\{[^}]+\}/pay',
        r'/\{[^}]+\}/cancel',
        r'/\{[^}]+\}/clear',
        r'/\{[^}]+\}/items',
    ]
    
    def __init__(self, app_ir, output_path: Path):
        self.app_ir = app_ir
        self.output_path = output_path
        self.routes_dir = output_path / "src" / "api" / "routes"
        
    def validate(self) -> PreValidationResult:
        """
        Compare IR endpoints vs generated route files.

        Returns:
            PreValidationResult with gaps identified
        """
        result = PreValidationResult()

        # 1. Extract endpoints from IR
        ir_endpoints = self._extract_ir_endpoints()
        result.ir_endpoints = [f"{e.method.upper()} {self._normalize_path(e.path)}" for e in ir_endpoints]

        # 2. Extract endpoints from generated code (already normalized)
        code_endpoints = self._extract_code_endpoints()
        result.code_endpoints = code_endpoints

        # 3. Find gaps using normalized paths
        ir_set = set(result.ir_endpoints)
        code_set = set(code_endpoints)

        missing = ir_set - code_set
        extra = code_set - ir_set

        # 4. Create EndpointGap objects for missing
        for sig in missing:
            parts = sig.split(' ', 1)
            if len(parts) == 2:
                method, normalized_path = parts
                # Find matching IR endpoint for metadata (use original path)
                ir_ep = next((e for e in ir_endpoints
                             if e.method.upper() == method.upper() and
                             self._normalize_path(e.path) == normalized_path), None)

                # Use original path from IR for repair (not normalized)
                original_path = ir_ep.path if ir_ep else normalized_path

                gap = EndpointGap(
                    method=method,
                    path=original_path,
                    operation_id=ir_ep.operation_id if ir_ep else f"{method.lower()}_{normalized_path.replace('/', '_')}",
                    entity_name=self._extract_entity_from_path(original_path),
                    description=ir_ep.description if ir_ep and hasattr(ir_ep, 'description') else "",
                    is_action=any(re.search(p, normalized_path) for p in self.ACTION_PATTERNS)
                )
                result.missing_endpoints.append(gap)

        result.extra_endpoints = list(extra)

        # Bug #170 Fix: Calculate coverage correctly
        # coverage_rate = matched endpoints / total IR endpoints
        matched = len(ir_set & code_set)
        result.coverage_rate = matched / len(ir_set) if ir_set else 1.0

        # Bug #179 Fix: Log debugging info for normalization issues
        if matched == 0 and len(ir_set) > 0 and len(code_set) > 0:
            self._log_normalization_debug(ir_set, code_set)

        return result

    def _log_normalization_debug(self, ir_set: set, code_set: set):
        """Log debugging info when no endpoints match (Bug #179)."""
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[Bug #179] No endpoint matches found!")
        logger.warning(f"  IR sample (first 3): {list(ir_set)[:3]}")
        logger.warning(f"  Code sample (first 3): {list(code_set)[:3]}")

    def _normalize_path(self, path: str) -> str:
        """Normalize path parameters for comparison.

        Converts /products/{product_id} to /products/{id}
        This allows matching between IR paths and code paths.
        """
        return re.sub(r'\{[^}]+\}', '{id}', path)
    
    def _extract_ir_endpoints(self) -> List:
        """Extract endpoints from ApplicationIR."""
        if not self.app_ir or not self.app_ir.api_model:
            return []
        return list(self.app_ir.api_model.endpoints)
    
    def _extract_code_endpoints(self) -> List[str]:
        """Extract endpoints from generated route files using AST."""
        endpoints = []
        
        if not self.routes_dir.exists():
            logger.warning(f"Routes directory not found: {self.routes_dir}")
            return endpoints
            
        for route_file in self.routes_dir.glob("*.py"):
            if route_file.name.startswith("_"):
                continue
            try:
                endpoints.extend(self._parse_route_file(route_file))
            except Exception as e:
                logger.warning(f"Failed to parse {route_file}: {e}")
                
        return endpoints
    
    def _parse_route_file(self, file_path: Path) -> List[str]:
        """Parse a route file and extract endpoint signatures."""
        endpoints = []
        content = file_path.read_text()
        
        # Match @router.get("/path"), @router.post("/path"), etc.
        pattern = r'@router\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern, content, re.IGNORECASE):
            method = match.group(1).upper()
            path = match.group(2)
            # Normalize path params: {product_id} -> {id}
            normalized = re.sub(r'\{[^}]+\}', '{id}', path)
            endpoints.append(f"{method} {normalized}")
            
        return endpoints
    
    def _extract_entity_from_path(self, path: str) -> str:
        """Extract entity name from path (e.g., /products/{id} -> Product)."""
        parts = path.strip('/').split('/')
        if parts:
            entity = parts[0].rstrip('s').capitalize()
            return entity
        return "Unknown"

