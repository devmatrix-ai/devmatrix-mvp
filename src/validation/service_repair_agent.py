"""
SERVICE Repair Agent - Repairs business logic constraints by injecting guards.

This agent handles constraints that CodeRepairAgent cannot:
- status_transition → pre-guard checking entity status
- stock_constraint → pre-guard checking inventory levels
- workflow_constraint → pre-guard checking preconditions
- custom → marked as MANUAL (requires human review)

All guards are 100% domain-agnostic - derived from IR constraint metadata.
"""
import ast
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class GuardType(str, Enum):
    """Types of guards that can be injected."""
    STATUS_CHECK = "status_check"
    QUANTITY_CHECK = "quantity_check"
    EXISTENCE_CHECK = "existence_check"
    CUSTOM = "custom"


@dataclass
class GuardSpec:
    """Specification for a guard to inject."""
    guard_type: GuardType
    entity_var: str           # Variable name (e.g., 'cart')
    field_name: str           # Field to check (e.g., 'status')
    expected_value: str       # Expected value (e.g., 'OPEN')
    operator: str = "=="      # Comparison operator
    error_message: str = ""   # Custom error message
    comparison_var: Optional[str] = None  # For quantity checks (e.g., 'quantity')


@dataclass
class RepairResult:
    """Result of a service repair attempt."""
    success: bool
    file_path: str = ""
    method_name: str = ""
    guard_injected: str = ""
    error_message: str = ""
    is_manual: bool = False   # True if constraint requires manual review


class ServiceRepairAgent:
    """
    Repairs business logic constraints by injecting guards into service methods.
    
    100% domain-agnostic - all guard parameters come from IR constraint metadata.
    """
    
    # Guard templates - parameterized, no domain knowledge
    GUARD_TEMPLATES = {
        GuardType.STATUS_CHECK: '''
        # Guard: {constraint_name} (auto-generated from IR)
        if {entity_var}.{field_name} != "{expected_value}":
            raise HTTPException(
                status_code=422,
                detail=f"Cannot proceed: {entity_var} {field_name} is {{{entity_var}.{field_name}}}, expected {expected_value}"
            )
''',
        GuardType.QUANTITY_CHECK: '''
        # Guard: {constraint_name} (auto-generated from IR)
        if {entity_var}.{field_name} {operator} {comparison_var}:
            raise HTTPException(
                status_code=422,
                detail=f"Constraint failed: {entity_var}.{field_name} ({{{entity_var}.{field_name}}}) must be {operator_inverse} {{{comparison_var}}}"
            )
''',
        GuardType.EXISTENCE_CHECK: '''
        # Guard: {constraint_name} (auto-generated from IR)
        if not {entity_var}:
            raise HTTPException(
                status_code=404,
                detail="{entity_var} not found"
            )
''',
    }
    
    # Operator inverses for error messages
    OPERATOR_INVERSES = {
        '<': '>=',
        '<=': '>',
        '>': '<=',
        '>=': '<',
        '==': '!=',
        '!=': '==',
    }
    
    def __init__(self, app_path: Path, application_ir: Optional[Any] = None):
        """
        Initialize SERVICE Repair Agent.
        
        Args:
            app_path: Path to the generated application
            application_ir: Optional ApplicationIR for context
        """
        self.app_path = Path(app_path)
        self.application_ir = application_ir
        self.services_dir = self.app_path / "src" / "services"
        
    def repair_constraint(
        self,
        constraint_type: str,
        constraint_metadata: Dict[str, Any],
        target_method: str
    ) -> RepairResult:
        """
        Repair a business logic constraint by injecting a guard.
        
        Args:
            constraint_type: Type of constraint (status_transition, stock_constraint, etc.)
            constraint_metadata: IR metadata for the constraint
            target_method: Method name where guard should be injected
            
        Returns:
            RepairResult with outcome
        """
        # Route to appropriate handler
        if constraint_type == 'custom':
            return self._mark_as_manual(constraint_metadata, target_method)
        
        guard_spec = self._constraint_to_guard_spec(constraint_type, constraint_metadata)
        if not guard_spec:
            return RepairResult(
                success=False,
                error_message=f"Cannot generate guard for constraint type: {constraint_type}"
            )
        
        # Find target service file
        service_file = self._find_service_file(target_method, constraint_metadata)
        if not service_file or not service_file.exists():
            return RepairResult(
                success=False,
                error_message=f"Service file not found for method: {target_method}"
            )
        
        # Generate and inject guard
        guard_code = self._generate_guard(guard_spec, constraint_type)
        success = self._inject_guard(service_file, target_method, guard_code)
        
        return RepairResult(
            success=success,
            file_path=str(service_file),
            method_name=target_method,
            guard_injected=guard_code.strip() if success else "",
            error_message="" if success else "Failed to inject guard into method"
        )
    
    def _constraint_to_guard_spec(
        self,
        constraint_type: str,
        metadata: Dict[str, Any]
    ) -> Optional[GuardSpec]:
        """Convert IR constraint to GuardSpec."""
        if constraint_type == 'status_transition':
            return GuardSpec(
                guard_type=GuardType.STATUS_CHECK,
                entity_var=metadata.get('entity', 'entity').lower(),
                field_name=metadata.get('field', 'status'),
                expected_value=metadata.get('expected_value', metadata.get('from_status', 'ACTIVE')),
            )
        elif constraint_type in ('stock_constraint', 'quantity_constraint', 'inventory_constraint'):
            return GuardSpec(
                guard_type=GuardType.QUANTITY_CHECK,
                entity_var=metadata.get('entity', 'product').lower(),
                field_name=metadata.get('field', 'stock'),
                expected_value="",
                operator=metadata.get('operator', '<'),
                comparison_var=metadata.get('comparison_field', 'quantity'),
            )
        elif constraint_type == 'workflow_constraint':
            return GuardSpec(
                guard_type=GuardType.EXISTENCE_CHECK,
                entity_var=metadata.get('entity', 'entity').lower(),
                field_name="",
                expected_value="",
            )
        return None

    def _generate_guard(self, spec: GuardSpec, constraint_name: str) -> str:
        """Generate guard code from GuardSpec."""
        template = self.GUARD_TEMPLATES.get(spec.guard_type)
        if not template:
            return ""

        operator_inverse = self.OPERATOR_INVERSES.get(spec.operator, f"not {spec.operator}")

        return template.format(
            constraint_name=constraint_name,
            entity_var=spec.entity_var,
            field_name=spec.field_name,
            expected_value=spec.expected_value,
            operator=spec.operator,
            operator_inverse=operator_inverse,
            comparison_var=spec.comparison_var or 'value',
        )

    def _find_service_file(
        self,
        method_name: str,
        metadata: Dict[str, Any]
    ) -> Optional[Path]:
        """Find the service file containing the target method."""
        entity = metadata.get('entity', '').lower()
        if entity:
            service_file = self.services_dir / f"{entity}_service.py"
            if service_file.exists():
                return service_file

        # Fallback: search all service files
        if self.services_dir.exists():
            for service_file in self.services_dir.glob("*_service.py"):
                content = service_file.read_text()
                if f"def {method_name}" in content or f"async def {method_name}" in content:
                    return service_file
        return None

    def _inject_guard(self, service_file: Path, method_name: str, guard_code: str) -> bool:
        """Inject guard code at the beginning of a method."""
        try:
            content = service_file.read_text()

            # Find the method definition
            patterns = [
                rf'(async\s+def\s+{method_name}\s*\([^)]*\)[^:]*:)',
                rf'(def\s+{method_name}\s*\([^)]*\)[^:]*:)',
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    method_start = match.end()

                    # Skip docstring if present
                    after_def = content[method_start:method_start + 500]
                    docstring_match = re.match(r'\s*""".*?"""\s*', after_def, re.DOTALL)
                    if docstring_match:
                        insert_pos = method_start + docstring_match.end()
                    else:
                        # Find first newline after def
                        insert_pos = method_start

                    # Check if guard already exists
                    if guard_code.strip()[:50] in content:
                        logger.info(f"Guard already exists in {method_name}")
                        return True

                    # Inject guard
                    new_content = content[:insert_pos] + guard_code + content[insert_pos:]
                    service_file.write_text(new_content)

                    logger.info(f"✅ Injected guard into {service_file.name}::{method_name}")
                    return True

            logger.warning(f"Method {method_name} not found in {service_file}")
            return False

        except Exception as e:
            logger.error(f"Failed to inject guard: {e}")
            return False

    def _mark_as_manual(
        self,
        metadata: Dict[str, Any],
        target_method: str
    ) -> RepairResult:
        """Mark a constraint as requiring manual review."""
        logger.info(f"👁️ Constraint marked as MANUAL: {metadata.get('name', 'custom')} in {target_method}")
        return RepairResult(
            success=False,
            method_name=target_method,
            error_message="MANUAL_REVIEW_REQUIRED",
            is_manual=True
        )

    def repair_batch(
        self,
        constraints: List[Tuple[str, Dict[str, Any], str]]
    ) -> Dict[str, Any]:
        """
        Repair multiple constraints in batch.

        Args:
            constraints: List of (constraint_type, metadata, target_method) tuples

        Returns:
            Summary of repair results
        """
        results = {
            'total': len(constraints),
            'repaired': 0,
            'manual': 0,
            'failed': 0,
            'details': []
        }

        for constraint_type, metadata, target_method in constraints:
            result = self.repair_constraint(constraint_type, metadata, target_method)

            if result.success:
                results['repaired'] += 1
            elif result.is_manual:
                results['manual'] += 1
            else:
                results['failed'] += 1

            results['details'].append({
                'constraint_type': constraint_type,
                'method': target_method,
                'success': result.success,
                'is_manual': result.is_manual,
                'error': result.error_message
            })

        logger.info(
            f"SERVICE Repair: {results['repaired']} repaired, "
            f"{results['manual']} manual, {results['failed']} failed"
        )

        return results

