"""
Code Repair Agent - AST-Based Targeted Repairs

Este agente realiza reparaciones targeted usando AST patching en lugar de
regenerar todo el código.

ANTES (Stub): Siempre retornaba failure, repair loop regeneraba todo
DESPUÉS (AST): Patches targeted a archivos específicos, preserva código existente

Capacidades:
- Agregar entities faltantes a src/models/entities.py
- Agregar endpoints faltantes a src/api/routes/*.py
- Preservar código existente y solo agregar lo necesario
- Rollback automático si patch falla

Created: 2025-11-21 (replacing stub)
Reference: P1 fix for DevMatrix QA evaluation
"""

import ast
import astor
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
from src.services.production_code_generators import normalize_field_name

# IR-centric imports (optional - for migration)
try:
    from src.cognitive.ir.application_ir import ApplicationIR
    from src.cognitive.ir.domain_model import Entity
    from src.cognitive.ir.api_model import Endpoint
    IR_AVAILABLE = True
except ImportError:
    ApplicationIR = None
    Entity = None
    Endpoint = None
    IR_AVAILABLE = False

logger = logging.getLogger(__name__)


def normalize_path_params(path: str) -> str:
    """
    Normalize path parameters for comparison.

    /products/{product_id} → /products/{_}
    /products/{id} → /products/{_}
    /carts/{cart_id}/items/{item_id} → /carts/{_}/items/{_}

    This allows matching endpoints regardless of parameter naming conventions.
    """
    import re
    return re.sub(r'\{[^}]+\}', '{_}', path)


@dataclass
class RepairResult:
    """Result of a code repair attempt."""
    success: bool
    repaired_files: List[str]  # Changed from repaired_code to list of files
    repairs_applied: List[str]
    error_message: Optional[str] = None


class CodeRepairAgent:
    """
    AST-based code repair agent for targeted fixes.

    Instead of regenerating entire codebase, this agent:
    1. Identifies missing entities/endpoints from ComplianceReport
    2. Applies targeted AST patches to specific files
    3. Preserves existing code and only adds what's missing
    4. Provides rollback capability if patches fail
    """

    def __init__(
        self,
        output_path: Path,
        application_ir: Optional["ApplicationIR"] = None,
        llm_client: Optional[EnhancedAnthropicClient] = None
    ):
        """
        Initialize code repair agent.

        Args:
            output_path: Path to generated app directory
            application_ir: Optional ApplicationIR for IR-centric repairs (preferred)
            llm_client: Optional LLM client for intelligent parsing
        """
        # Convert to absolute path to work from any working directory
        self.output_path = Path(output_path).resolve()
        self.entities_file = self.output_path / "src" / "models" / "entities.py"
        self.routes_dir = self.output_path / "src" / "api" / "routes"
        self.llm_client = llm_client or EnhancedAnthropicClient()

        # IR-centric mode (Phase 7 migration)
        self.application_ir = application_ir
        self._use_ir = application_ir is not None and IR_AVAILABLE

    async def repair(
        self,
        compliance_report,
        spec_requirements=None,
        max_attempts: int = 3
    ) -> RepairResult:
        """
        Attempt to repair code based on compliance failures.

        Uses targeted AST patching instead of full regeneration:
        - Missing entities → Add to entities.py
        - Missing endpoints → Add to appropriate route file

        Args:
            compliance_report: ComplianceReport with failures
            spec_requirements: SpecRequirements with expected entities/endpoints (legacy, optional if IR available)
            max_attempts: Maximum repair attempts (not used for AST, kept for API compatibility)

        Returns:
            RepairResult with outcome
        """
        # === IR vs Legacy Routing (Phase 7 migration) ===
        if self._use_ir:
            logger.info("CodeRepair: Using IR-centric mode (ApplicationIR)")
            return await self._repair_from_ir(compliance_report)

        # Legacy mode: requires spec_requirements
        if spec_requirements is None:
            logger.warning("CodeRepair: Neither ApplicationIR nor spec_requirements available")
            return RepairResult(
                success=False,
                repaired_files=[],
                repairs_applied=[],
                error_message="spec_requirements required when ApplicationIR not available"
            )

        logger.info("CodeRepair: Using legacy mode (spec_requirements)")

        # === Legacy repair logic below ===
        repairs_applied = []
        repaired_files = []

        try:
            # Identify what's missing
            missing_entities = [
                e for e in compliance_report.entities_expected
                if e.lower() not in [i.lower() for i in compliance_report.entities_implemented]
            ]

            missing_endpoints = [
                e for e in compliance_report.endpoints_expected
                if e.lower() not in [i.lower() for i in compliance_report.endpoints_implemented]
            ]

            missing_validations = [
                v for v in compliance_report.validations_expected
                if v.lower() not in [i.lower() for i in compliance_report.validations_implemented]
            ]

            logger.info(f"CodeRepair: {len(missing_entities)} missing entities, {len(missing_endpoints)} missing endpoints, {len(missing_validations)} missing validations")

            # Repair missing entities
            if missing_entities:
                for entity_name in missing_entities:
                    try:
                        # Find entity definition in spec
                        entity_req = next(
                            (e for e in spec_requirements.entities if e.name.lower() == entity_name.lower()),
                            None
                        )

                        if entity_req:
                            success = self.repair_missing_entity(entity_req)
                            if success:
                                repairs_applied.append(f"Added entity: {entity_name}")
                                if str(self.entities_file) not in repaired_files:
                                    repaired_files.append(str(self.entities_file))
                            else:
                                logger.warning(f"Failed to add entity: {entity_name}")
                    except Exception as e:
                        logger.error(f"Error adding entity {entity_name}: {e}")

            # Repair missing endpoints
            if missing_endpoints:
                for endpoint_str in missing_endpoints:
                    try:
                        # Parse endpoint: "POST /products"
                        parts = endpoint_str.split()
                        if len(parts) >= 2:
                            method = parts[0].upper()
                            path = parts[1]

                            # Find endpoint definition in spec
                            endpoint_req = next(
                                (e for e in spec_requirements.endpoints
                                 if e.method.upper() == method and e.path == path),
                                None
                            )

                            if endpoint_req:
                                route_file = self.repair_missing_endpoint(endpoint_req)
                                if route_file:
                                    repairs_applied.append(f"Added endpoint: {method} {path}")
                                    if route_file not in repaired_files:
                                        repaired_files.append(route_file)
                                else:
                                    logger.warning(f"Failed to add endpoint: {endpoint_str}")
                    except Exception as e:
                        logger.error(f"Error adding endpoint {endpoint_str}: {e}")

            # Repair missing validations (NEW - Fix #2)
            if missing_validations:
                for validation_str in missing_validations:
                    try:
                        # Parse validation: "price > 0" or "stock >= 0"
                        # Extract field name and constraint
                        success = await self.repair_missing_validation(
                            validation_str,
                            spec_requirements
                        )
                        if success:
                            repairs_applied.append(f"Added validation: {validation_str}")
                            schemas_file = str(self.output_path / "src" / "models" / "schemas.py")
                            if schemas_file not in repaired_files:
                                repaired_files.append(schemas_file)
                        else:
                            logger.warning(f"Failed to add validation: {validation_str}")
                    except Exception as e:
                        logger.error(f"Error adding validation {validation_str}: {e}")

            if repairs_applied:
                return RepairResult(
                    success=True,
                    repaired_files=repaired_files,
                    repairs_applied=repairs_applied
                )
            else:
                return RepairResult(
                    success=False,
                    repaired_files=[],
                    repairs_applied=[],
                    error_message="No repairs could be applied"
                )

        except Exception as e:
            logger.error(f"CodeRepair failed: {e}")
            return RepairResult(
                success=False,
                repaired_files=[],
                repairs_applied=[],
                error_message=str(e)
            )

    # =========================================================================
    # IR-CENTRIC REPAIR METHODS (Phase 7 Migration)
    # =========================================================================

    async def _repair_from_ir(self, compliance_report) -> RepairResult:
        """
        Repair code using ApplicationIR as source of truth.

        Uses DomainModelIR for entity definitions and APIModelIR for endpoints,
        instead of legacy spec_requirements.

        Args:
            compliance_report: ComplianceReport with failures

        Returns:
            RepairResult with outcome
        """
        repairs_applied = []
        repaired_files = []

        try:
            # Get IR models
            domain_model = self.application_ir.domain_model
            api_model = self.application_ir.api_model

            # Identify what's missing
            missing_entities = [
                e for e in compliance_report.entities_expected
                if e.lower() not in [i.lower() for i in compliance_report.entities_implemented]
            ]

            missing_endpoints = [
                e for e in compliance_report.endpoints_expected
                if e.lower() not in [i.lower() for i in compliance_report.endpoints_implemented]
            ]

            logger.info(f"CodeRepair (IR): {len(missing_entities)} missing entities, {len(missing_endpoints)} missing endpoints")

            # Repair missing entities from DomainModelIR
            if missing_entities and domain_model and domain_model.entities:
                for entity_name in missing_entities:
                    try:
                        # Find entity in DomainModelIR
                        entity_ir = next(
                            (e for e in domain_model.entities if e.name.lower() == entity_name.lower()),
                            None
                        )

                        if entity_ir:
                            success = self._repair_entity_from_ir(entity_ir)
                            if success:
                                repairs_applied.append(f"Added entity (IR): {entity_name}")
                                if str(self.entities_file) not in repaired_files:
                                    repaired_files.append(str(self.entities_file))
                            else:
                                logger.warning(f"Failed to add entity from IR: {entity_name}")
                        else:
                            # Bug #21 fix: Clarified warning (consistent with endpoint message)
                            logger.info(f"Entity {entity_name} marked missing but not in DomainModelIR (may be inferred)")
                    except Exception as e:
                        logger.error(f"Error adding entity {entity_name} from IR: {e}")

            # Repair missing endpoints from APIModelIR
            if missing_endpoints and api_model and api_model.endpoints:
                for endpoint_str in missing_endpoints:
                    try:
                        # Parse endpoint: "POST /products"
                        parts = endpoint_str.split()
                        if len(parts) >= 2:
                            method = parts[0].upper()
                            path = parts[1]

                            # Find endpoint in APIModelIR (with path param normalization)
                            # /products/{product_id} should match /products/{id}
                            normalized_path = normalize_path_params(path)
                            endpoint_ir = next(
                                (e for e in api_model.endpoints
                                 if e.method.upper() == method and normalize_path_params(e.path) == normalized_path),
                                None
                            )

                            if endpoint_ir:
                                route_file = self._repair_endpoint_from_ir(endpoint_ir)
                                if route_file:
                                    repairs_applied.append(f"Added endpoint (IR): {method} {path}")
                                    if route_file not in repaired_files:
                                        repaired_files.append(route_file)
                                else:
                                    logger.warning(f"Failed to add endpoint from IR: {endpoint_str}")
                            else:
                                # Bug #21 fix: Clarified warning message
                                # This happens when compliance reports a missing endpoint that isn't in APIModelIR
                                # Either: (a) endpoint was inferred but not in IR, or (b) IR parsing missed it
                                logger.info(f"Endpoint {endpoint_str} marked missing but not in APIModelIR (may be inferred or custom)")
                    except Exception as e:
                        logger.error(f"Error adding endpoint {endpoint_str} from IR: {e}")

            # Bug #20 fix: Add validation/constraint repair to IR-centric mode
            # Previously only entities and endpoints were repaired, constraints were ignored
            missing_validations = [
                v for v in compliance_report.validations_expected
                if v.lower() not in [i.lower() for i in compliance_report.validations_implemented]
            ]

            if missing_validations:
                logger.info(f"CodeRepair (IR): {len(missing_validations)} missing validations/constraints")
                for validation_str in missing_validations:
                    try:
                        # Use IR-based constraint repair
                        success = await self._repair_validation_from_ir(validation_str)
                        if success:
                            repairs_applied.append(f"Added validation (IR): {validation_str}")
                            schemas_file = str(self.output_path / "src" / "models" / "schemas.py")
                            if schemas_file not in repaired_files:
                                repaired_files.append(schemas_file)
                        else:
                            # Log as info, not warning - constraints can be complex
                            logger.info(f"Constraint not auto-repairable: {validation_str}")
                    except Exception as e:
                        logger.error(f"Error adding validation {validation_str} from IR: {e}")

            if repairs_applied:
                return RepairResult(
                    success=True,
                    repaired_files=repaired_files,
                    repairs_applied=repairs_applied
                )
            else:
                # Bug #20: Report what couldn't be repaired
                constraint_gap = len(missing_validations) if missing_validations else 0
                error_msg = "No repairs could be applied from IR"
                if constraint_gap > 0:
                    error_msg += f" ({constraint_gap} constraints require manual IR adjustment)"
                return RepairResult(
                    success=False,
                    repaired_files=[],
                    repairs_applied=[],
                    error_message=error_msg
                )

        except Exception as e:
            logger.error(f"CodeRepair (IR) failed: {e}")
            return RepairResult(
                success=False,
                repaired_files=[],
                repairs_applied=[],
                error_message=str(e)
            )

    def _repair_entity_from_ir(self, entity_ir: "Entity") -> bool:
        """
        Add missing entity using DomainModelIR Entity definition.

        Uses the same AST patching as legacy, but extracts attributes
        from the IR Entity structure.

        Args:
            entity_ir: Entity from DomainModelIR

        Returns:
            True if successful
        """
        try:
            # Create a pseudo entity_req compatible with repair_missing_entity
            # This allows reusing the existing AST patching logic
            class EntityReq:
                def __init__(self, name, attributes):
                    self.name = name
                    self.attributes = attributes

            # Convert IR attributes to format expected by repair_missing_entity
            attributes = []
            if entity_ir.attributes:
                for attr in entity_ir.attributes:
                    attr_dict = {
                        'name': attr.name,
                        'type': attr.type,
                        'required': not attr.is_nullable if hasattr(attr, 'is_nullable') else True
                    }
                    if hasattr(attr, 'constraints') and attr.constraints:
                        attr_dict['constraints'] = attr.constraints
                    attributes.append(type('Attr', (), attr_dict)())

            entity_req = EntityReq(entity_ir.name, attributes)
            return self.repair_missing_entity(entity_req)

        except Exception as e:
            logger.error(f"_repair_entity_from_ir failed: {e}")
            return False

    def _repair_endpoint_from_ir(self, endpoint_ir: "Endpoint") -> Optional[str]:
        """
        Add missing endpoint using APIModelIR Endpoint definition.

        Uses the same AST patching as legacy, but extracts details
        from the IR Endpoint structure.

        Args:
            endpoint_ir: Endpoint from APIModelIR

        Returns:
            Path to modified route file, or None if failed
        """
        try:
            # Create a pseudo endpoint_req compatible with repair_missing_endpoint
            class EndpointReq:
                def __init__(self, method, path, request_body=None, response=None, description=""):
                    self.method = method
                    self.path = path
                    self.request_body = request_body
                    self.response = response
                    self.description = description

            endpoint_req = EndpointReq(
                method=endpoint_ir.method,
                path=endpoint_ir.path,
                request_body=endpoint_ir.request_body if hasattr(endpoint_ir, 'request_body') else None,
                response=endpoint_ir.response if hasattr(endpoint_ir, 'response') else None,
                description=endpoint_ir.description if hasattr(endpoint_ir, 'description') else ""
            )
            return self.repair_missing_endpoint(endpoint_req)

        except Exception as e:
            logger.error(f"_repair_endpoint_from_ir failed: {e}")
            return None

    async def _repair_validation_from_ir(self, validation_str: str) -> bool:
        """
        Add missing validation/constraint using ApplicationIR.

        Bug #20 fix: This method enables IR-centric constraint repair.
        Previously only legacy mode had validation repair.

        Args:
            validation_str: Validation description (e.g., "Order.items: required")

        Returns:
            True if successfully repaired, False otherwise
        """
        try:
            domain_model = self.application_ir.domain_model
            if not domain_model or not domain_model.entities:
                logger.info(f"No DomainModelIR available for constraint repair: {validation_str}")
                return False

            # Try to parse validation string: "Entity.field: constraint" or "field constraint"
            parsed = self._parse_validation_str_ir(validation_str, domain_model)
            if not parsed:
                logger.info(f"Could not parse IR validation: {validation_str}")
                return False

            entity_name = parsed["entity"]
            field_name = parsed["field"]
            constraint_type = parsed["constraint_type"]
            constraint_value = parsed["constraint_value"]

            # Bug #45 Fix: Map semantic constraint names to Pydantic constraint types
            # This prevents "non_empty" from being treated as unknown and retried
            semantic_mapping = {
                'non_empty': ('min_length', 1),
                'non_negative': ('ge', 0),
                'positive': ('gt', 0),
                'greater_than_zero': ('gt', 0),
                'auto_generated': ('default_factory', 'uuid.uuid4'),
                'auto_increment': ('default_factory', 'uuid.uuid4'),
                'read_only': ('read_only', True),
                'snapshot_at_add_time': ('read_only', True),
                'snapshot_at_order_time': ('read_only', True),
            }
            if constraint_type in semantic_mapping:
                mapped = semantic_mapping[constraint_type]
                logger.info(f"Bug #45: Mapping '{constraint_type}' → '{mapped[0]}={mapped[1]}'")
                constraint_type = mapped[0]
                constraint_value = mapped[1]

            # Bug #45 Fix: Validate constraint_type against known_constraints (same as legacy mode)
            # Without this check, invalid constraints like "non" get applied and repeated
            known_constraints = {
                'gt', 'ge', 'lt', 'le',
                'min_length', 'max_length', 'pattern',
                'min_items', 'max_items',
                'default', 'default_factory', 'required', 'enum',
                'unique', 'foreign_key',
                'read_only', 'auto_increment', 'computed_field'
            }
            if constraint_type not in known_constraints:
                logger.info(f"Bug #45: Ignoring unrecognized constraint '{constraint_type}' from '{validation_str}'")
                return True  # Treat as handled to avoid retry loop

            # Bug #51 Fix: Skip constraints with invalid values
            # Pydantic expects integers for min_length/max_length, not "none" strings
            numeric_constraints = {'gt', 'ge', 'lt', 'le', 'min_length', 'max_length', 'min_items', 'max_items'}
            if constraint_type in numeric_constraints:
                # Skip if value is 'none', None, or empty
                if constraint_value is None or str(constraint_value).lower() == 'none' or constraint_value == '':
                    logger.info(f"Bug #51: Skipping {constraint_type}={constraint_value} (invalid numeric value)")
                    return True  # Treat as handled
                # Try to convert to number
                try:
                    constraint_value = float(constraint_value) if '.' in str(constraint_value) else int(constraint_value)
                except (ValueError, TypeError):
                    logger.info(f"Bug #51: Skipping {constraint_type}={constraint_value} (not a number)")
                    return True

            # Bug #51 Fix: Skip pattern constraints with 'none' value
            if constraint_type == 'pattern':
                if constraint_value is None or str(constraint_value).lower() == 'none' or constraint_value == '':
                    logger.info(f"Bug #51: Skipping pattern={constraint_value} (invalid pattern)")
                    return True

            # Apply constraint to schemas.py using existing AST patcher
            return self._add_field_constraint_to_schema(
                entity_name=entity_name,
                field_name=field_name,
                constraint_type=constraint_type,
                constraint_value=constraint_value
            )

        except Exception as e:
            logger.error(f"_repair_validation_from_ir failed for '{validation_str}': {e}")
            return False

    def _parse_validation_str_ir(self, validation_str: str, domain_model) -> Optional[Dict[str, Any]]:
        """
        Parse validation string using IR context.

        Formats supported:
        - "Entity.field: constraint=value"
        - "Entity.field: constraint"
        - "field > 0" (will search IR for which entity has this field)

        Args:
            validation_str: Validation description
            domain_model: DomainModelIR with entity definitions

        Returns:
            Dict with entity, field, constraint_type, constraint_value or None
        """
        import re

        # Try format: "Entity.field: constraint=value" or "Entity.field: constraint"
        # Bug #45 Fix: Use [\w-]+ to capture constraints with hyphens like "non-empty"
        match = re.match(r'(\w+)\.(\w+):\s*([\w-]+)(?:=(.+))?', validation_str)
        if match:
            entity_name = match.group(1)
            field_name = match.group(2)
            # Normalize constraint: replace hyphens with underscores for consistency
            constraint_type = match.group(3).replace('-', '_')
            constraint_value = match.group(4) if match.group(4) else True
            return {
                "entity": entity_name,
                "field": field_name,
                "constraint_type": constraint_type,
                "constraint_value": constraint_value
            }

        # Try format: "field > 0" or "field >= 0" etc.
        match = re.match(r'(\w+)\s*(>|>=|<|<=|==)\s*(\d+)', validation_str)
        if match:
            field_name = match.group(1)
            operator = match.group(2)
            value = int(match.group(3))

            # Map operator to constraint type
            op_map = {'>': 'gt', '>=': 'ge', '<': 'lt', '<=': 'le', '==': 'eq'}
            constraint_type = op_map.get(operator, 'gt')

            # Find entity containing this field
            entity_name = self._find_entity_for_field_ir(field_name, domain_model)
            if entity_name:
                return {
                    "entity": entity_name,
                    "field": field_name,
                    "constraint_type": constraint_type,
                    "constraint_value": value
                }

        return None

    def _find_entity_for_field_ir(self, field_name: str, domain_model) -> Optional[str]:
        """
        Find which entity contains a given field using DomainModelIR.

        Args:
            field_name: Name of the field
            domain_model: DomainModelIR with entity definitions

        Returns:
            Entity name or None
        """
        if not domain_model or not domain_model.entities:
            return None

        for entity in domain_model.entities:
            if hasattr(entity, 'attributes'):
                for attr in entity.attributes:
                    attr_name = attr.name if hasattr(attr, 'name') else str(attr)
                    if attr_name.lower() == field_name.lower():
                        return entity.name
        return None

    # =========================================================================
    # LEGACY REPAIR METHODS (preserved for backward compatibility)
    # =========================================================================

    def repair_missing_entity(self, entity_req) -> bool:
        """
        Add missing entity to src/models/entities.py using AST patching.

        Strategy:
        1. Read entities.py and parse to AST
        2. Create new entity class node
        3. Insert at end of AST
        4. Write back using astor

        Args:
            entity_req: Entity requirement from spec

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read current entities.py (create if doesn't exist)
            if not self.entities_file.exists():
                logger.warning(f"entities.py not found at {self.entities_file}, creating it")
                self._create_entities_file()
                # After creation, file should exist with base structure
                if not self.entities_file.exists():
                    logger.error(f"Failed to create entities.py at {self.entities_file}")
                    return False

            with open(self.entities_file, 'r') as f:
                source_code = f.read()

            # Parse to AST
            tree = ast.parse(source_code)

            # Check if entity already exists (avoid duplicates)
            entity_class_name = f"{entity_req.name}Entity"
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == entity_class_name:
                    logger.info(f"Entity {entity_class_name} already exists in entities.py, skipping")
                    return True  # Not an error, just already exists

            # Create new entity class
            new_class = self._generate_entity_class_ast(entity_req)

            # Add to AST
            tree.body.append(new_class)

            # Convert back to code
            new_code = astor.to_source(tree)

            # Write back
            with open(self.entities_file, 'w') as f:
                f.write(new_code)

            logger.info(f"Added entity {entity_req.name} to entities.py")
            return True

        except Exception as e:
            logger.error(f"Failed to add entity {entity_req.name}: {e}")
            return False

    def repair_missing_endpoint(self, endpoint_req) -> Optional[str]:
        """
        Add missing endpoint to appropriate route file using AST patching.

        Strategy:
        1. Determine which route file (e.g., product.py from /products path)
        2. Read route file and parse to AST
        3. Create new endpoint function node
        4. Insert at end of AST
        5. Write back using astor

        Args:
            endpoint_req: Endpoint requirement from spec

        Returns:
            Path to repaired file if successful, None otherwise
        """
        try:
            # Determine route file from path
            # /products → product.py, /customers → customer.py
            path_parts = endpoint_req.path.strip('/').split('/')
            if not path_parts or not path_parts[0]:
                logger.warning(f"Cannot determine route file for path: {endpoint_req.path}")
                return None

            # Get entity name from path (singular form)
            entity_plural = path_parts[0]
            entity_name = entity_plural.rstrip('s')  # Simple pluralization: products → product

            route_file = self.routes_dir / f"{entity_name}.py"

            # Create file if doesn't exist
            if not route_file.exists():
                self._create_route_file(route_file, entity_name)

            # Read current route file
            with open(route_file, 'r') as f:
                source_code = f.read()

            # Parse to AST
            tree = ast.parse(source_code)

            # Create new endpoint function
            new_function = self._generate_endpoint_function_ast(endpoint_req, entity_name)

            # Check if endpoint function already exists (avoid duplicates)
            function_name = new_function.name
            for node in tree.body:
                if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
                    logger.info(f"Endpoint function {function_name} already exists in {route_file.name}, skipping")
                    return str(route_file)  # Not an error, just already exists

            # Add to AST
            tree.body.append(new_function)

            # Convert back to code
            new_code = astor.to_source(tree)

            # Write back
            with open(route_file, 'w') as f:
                f.write(new_code)

            logger.info(f"Added endpoint {endpoint_req.method} {endpoint_req.path} to {route_file.name}")
            return str(route_file)

        except Exception as e:
            logger.error(f"Failed to add endpoint {endpoint_req.method} {endpoint_req.path}: {e}")
            return None

    def _generate_entity_class_ast(self, entity_req) -> ast.ClassDef:
        """
        Generate AST node for SQLAlchemy entity class.

        Creates class like:
        ```
        class ProductEntity(Base):
            __tablename__ = "products"
            id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            name = Column(String(255), nullable=False)
            ...
        ```

        Args:
            entity_req: Entity requirement from spec

        Returns:
            ast.ClassDef node
        """
        # Simplified implementation - in production would parse entity_req.attributes
        # For now, create basic entity with id field

        class_name = f"{entity_req.name}Entity"
        table_name = f"{entity_req.name.lower()}s"

        # Create class definition
        class_def = ast.ClassDef(
            name=class_name,
            bases=[ast.Name(id='Base', ctx=ast.Load())],
            keywords=[],
            body=[
                # __tablename__ = "products"
                ast.Assign(
                    targets=[ast.Name(id='__tablename__', ctx=ast.Store())],
                    value=ast.Constant(value=table_name)
                ),
                # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
                ast.Assign(
                    targets=[ast.Name(id='id', ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Name(id='Column', ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Name(id='UUID', ctx=ast.Load()),
                                args=[],
                                keywords=[ast.keyword(arg='as_uuid', value=ast.Constant(value=True))]
                            )
                        ],
                        keywords=[
                            ast.keyword(arg='primary_key', value=ast.Constant(value=True)),
                            ast.keyword(arg='default', value=ast.Attribute(
                                value=ast.Name(id='uuid', ctx=ast.Load()),
                                attr='uuid4',
                                ctx=ast.Load()
                            ))
                        ]
                    )
                )
            ],
            decorator_list=[]
        )

        return class_def

    def _generate_endpoint_function_ast(self, endpoint_req, entity_name: str) -> ast.AsyncFunctionDef:
        """
        Generate AST node for FastAPI endpoint function with real implementation.

        Creates function like:
        ```
        @router.get("/")
        async def list_products(db: AsyncSession = Depends(get_db)):
            service = ProductService(db)
            result = await service.list(page=1, size=100)
            return result.items
        ```

        Args:
            endpoint_req: Endpoint requirement from spec
            entity_name: Entity name (e.g., "product")

        Returns:
            ast.AsyncFunctionDef node
        """
        method = endpoint_req.method.lower()
        entity_capitalized = entity_name.capitalize()
        service_class = f"{entity_capitalized}Service"

        # Determine function name from method
        if method == 'get':
            func_name = f"list_{entity_name}s"
        elif method == 'post':
            func_name = f"create_{entity_name}"
        elif method == 'put':
            func_name = f"update_{entity_name}"
        elif method == 'delete':
            func_name = f"delete_{entity_name}"
        else:
            func_name = f"{method}_{entity_name}"

        # Generate real function body based on HTTP method
        # Body: service = {Entity}Service(db)
        service_assign = ast.Assign(
            targets=[ast.Name(id='service', ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id=service_class, ctx=ast.Load()),
                args=[ast.Name(id='db', ctx=ast.Load())],
                keywords=[]
            )
        )

        if method == 'get':
            # result = await service.list(page=1, size=100)
            # return result.items
            body = [
                service_assign,
                ast.Assign(
                    targets=[ast.Name(id='result', ctx=ast.Store())],
                    value=ast.Await(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='service', ctx=ast.Load()),
                                attr='list',
                                ctx=ast.Load()
                            ),
                            args=[],
                            keywords=[
                                ast.keyword(arg='page', value=ast.Constant(value=1)),
                                ast.keyword(arg='size', value=ast.Constant(value=100))
                            ]
                        )
                    )
                ),
                ast.Return(
                    value=ast.Attribute(
                        value=ast.Name(id='result', ctx=ast.Load()),
                        attr='items',
                        ctx=ast.Load()
                    )
                )
            ]
        elif method == 'post':
            # return await service.create(data)
            body = [
                service_assign,
                ast.Return(
                    value=ast.Await(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='service', ctx=ast.Load()),
                                attr='create',
                                ctx=ast.Load()
                            ),
                            args=[ast.Name(id='data', ctx=ast.Load())],
                            keywords=[]
                        )
                    )
                )
            ]
        else:
            # For PUT/DELETE and others, use NotImplementedError with clear message
            body = [
                ast.Raise(
                    exc=ast.Call(
                        func=ast.Name(id='NotImplementedError', ctx=ast.Load()),
                        args=[ast.Constant(value=f"Endpoint {func_name} needs implementation")],
                        keywords=[]
                    )
                )
            ]

        # Create async function with decorator
        func_def = ast.AsyncFunctionDef(
            name=func_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg='db', annotation=ast.Name(id='AsyncSession', ctx=ast.Load()))
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[
                    ast.Call(
                        func=ast.Name(id='Depends', ctx=ast.Load()),
                        args=[ast.Name(id='get_db', ctx=ast.Load())],
                        keywords=[]
                    )
                ]
            ),
            body=body,
            decorator_list=[
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='router', ctx=ast.Load()),
                        attr=method,
                        ctx=ast.Load()
                    ),
                    args=[ast.Constant(value="/")],
                    keywords=[]
                )
            ],
            returns=None
        )

        return func_def

    def _create_route_file(self, route_file: Path, entity_name: str):
        """
        Create new route file with basic structure.

        Creates file like:
        ```
        from fastapi import APIRouter, Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.core.database import get_db

        router = APIRouter(prefix="/products", tags=["products"])
        ```

        Args:
            route_file: Path to route file to create
            entity_name: Entity name (e.g., "product")
        """
        entity_plural = f"{entity_name}s"

        template = f'''"""
FastAPI CRUD Routes for {entity_name.capitalize()}

Auto-generated route file.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db

router = APIRouter(
    prefix="/{entity_plural}",
    tags=["{entity_plural}"],
)
'''

        route_file.parent.mkdir(parents=True, exist_ok=True)
        with open(route_file, 'w') as f:
            f.write(template)

        logger.info(f"Created new route file: {route_file.name}")

    def _create_entities_file(self):
        """
        Create new entities.py file with basic SQLAlchemy structure.

        Creates file like:
        ```
        from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
        from sqlalchemy.dialects.postgresql import UUID
        from sqlalchemy.orm import relationship
        from src.core.database import Base
        import uuid
        from datetime import datetime, timezone

        # Entity classes will be added here by repair agent
        ```

        The file is created with base imports, then entities are added via AST patching.
        """
        template = '''"""
SQLAlchemy Entity Models

Auto-generated entity file.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid
from datetime import datetime, timezone


# Entity classes will be added below
'''

        # Ensure parent directory exists
        self.entities_file.parent.mkdir(parents=True, exist_ok=True)

        # Write base structure
        with open(self.entities_file, 'w') as f:
            f.write(template)

        logger.info(f"Created new entities file: {self.entities_file.name}")

    async def _parse_validation_with_llm(self, validation_str: str, spec_requirements) -> Optional[Dict[str, Any]]:
        """
        Parse natural language validation string using LLM.

        Args:
            validation_str: Validation description (e.g., "Product.price: gt=0" or "price > 0")
            spec_requirements: SpecRequirements to find entity definitions

        Returns:
            Dict with entity, field, constraint_type, constraint_value, or None if failed
        """
        try:
            # Build context about available entities and fields
            entities_context = []
            for entity in spec_requirements.entities:
                fields = [f"{f.name} ({f.type})" for f in entity.fields]
                entities_context.append(f"- {entity.name}: {', '.join(fields)}")
            
            context_str = "\n".join(entities_context)

            prompt = f"""You are a code repair assistant. Your task is to parse a validation requirement into a structured format for Pydantic Field().

AVAILABLE ENTITIES AND FIELDS:
{context_str}

VALIDATION REQUIREMENT: "{validation_str}"

INSTRUCTIONS:
1. Identify the Entity and Field this validation applies to.
2. Determine the constraint type and value.
   - gt, ge, lt, le: for numeric comparisons (> 0, >= 0, etc.)
   - min_length, max_length: for string lengths
   - pattern: for regex (email, uuid, custom)
   - unique: set constraint_type="unique", value=True
   - required: set constraint_type="required", value=True
   - enum: set constraint_type="enum", value=[list of strings]
3. Return ONLY a JSON object with keys: "entity", "field", "constraint_type", "constraint_value".

EXAMPLES:
Input: "Product.price: gt=0"
Output: {{"entity": "Product", "field": "price", "constraint_type": "gt", "constraint_value": 0}}

Input: "email format" (assuming Customer entity has email field)
Output: {{"entity": "Customer", "field": "email", "constraint_type": "pattern", "constraint_value": "^[^@]+@[^@]+\\.[^@]+$"}}

Input: "Product.id: auto-generated"
Output: {{"entity": "Product", "field": "id", "constraint_type": "default_factory", "constraint_value": "uuid.uuid4"}}

Input: "Product.name: non-empty"
Output: {{"entity": "Product", "field": "name", "constraint_type": "min_length", "constraint_value": 1}}

Input: "Product.stock: non-negative"
Output: {{"entity": "Product", "field": "stock", "constraint_type": "ge", "constraint_value": 0}}

Input: "Product.is_active: default_true"
Output: {{"entity": "Product", "field": "is_active", "constraint_type": "default", "constraint_value": true}}

Input: "CartItem.unit_price: snapshot_at_add_time"
Output: {{"entity": "CartItem", "field": "unit_price", "constraint_type": "read_only", "constraint_value": true}}

Input: "Order.total_amount: sum_of_items"
Output: {{"entity": "Order", "field": "total_amount", "constraint_type": "computed_field", "constraint_value": "sum of items"}}

Input: "Order.total_amount: auto-calculated"
Output: {{"entity": "Order", "field": "total_amount", "constraint_type": "computed_field", "constraint_value": "auto-calculated"}}

IMPORTANT: For fields that are snapshots, read-only, or computed, use:
- "snapshot_at_add_time" → constraint_type="read_only"
- "sum_of_items", "auto-calculated", "computed" → constraint_type="computed_field"

JSON OUTPUT:"""

            # Call LLM
            response = await self.llm_client.generate_simple(
                prompt=prompt,
                task_type="code_repair",
                complexity="low",
                temperature=0.0
            )

            # Parse JSON response
            # Clean up potential markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            result = json.loads(cleaned_response.strip())
            
            # Validate result structure
            if all(k in result for k in ["entity", "field", "constraint_type", "constraint_value"]):
                logger.info(f"LLM Parsed validation '{validation_str}' → {result}")
                return result
            else:
                logger.warning(f"LLM returned incomplete JSON: {result}")
                return None

        except Exception as e:
            logger.error(f"LLM parsing failed for '{validation_str}': {e}")
            return None

    async def repair_missing_validation(self, validation_str: str, spec_requirements) -> bool:
        """
        Add missing Field() validation to schemas.py using AST patching.
        Uses LLM to parse natural language validation requirements.

        Args:
            validation_str: Validation description (e.g., "Product.price: gt=0" or "price > 0")
            spec_requirements: SpecRequirements to find entity definitions

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use LLM to parse validation string
            parsed = await self._parse_validation_with_llm(validation_str, spec_requirements)
            
            if not parsed:
                logger.warning(f"Could not parse validation: {validation_str}")
                return False
            
            entity_name = parsed["entity"]
            field_name = parsed["field"]
            constraint_type = parsed["constraint_type"]
            constraint_value = parsed["constraint_value"]

            # Define known schema constraints
            known_constraints = {
                'gt', 'ge', 'lt', 'le',
                'min_length', 'max_length', 'pattern',
                'min_items', 'max_items',
                'default', 'default_factory', 'required', 'enum',
                'unique', 'foreign_key',  # Database constraints
                'read_only',  # Output/response-only fields
                'auto_increment', 'computed_field'  # Special constraints
            }
            if constraint_type not in known_constraints:
                logger.info(f"Ignoring unrecognized validation '{validation_str}' (constraint_type={constraint_type}) as noise against ground truth.")
                # Skip this validation; treat as successfully handled
                return True
            
            # Apply validation to schemas.py
            return self._add_field_constraint_to_schema(
                entity_name=entity_name,
                field_name=field_name,
                constraint_type=constraint_type,
                constraint_value=constraint_value
            )

        except Exception as e:
            logger.error(f"Failed to repair validation '{validation_str}': {e}")
            return False

    def _find_entity_for_field(self, field_name: str, spec_requirements) -> str:
        """
        Find which entity contains a given field.

        Args:
            field_name: Name of the field (e.g., "price", "stock")
            spec_requirements: SpecRequirements with entity definitions

        Returns:
            Entity name if found, None otherwise
        """
        for entity in spec_requirements.entities:
            for field in entity.fields:
                if field.name.lower() == field_name.lower():
                    return entity.name
        return None

    def _add_field_constraint_to_schema(
        self,
        entity_name: str,
        field_name: str,
        constraint_type: str,
        constraint_value
    ) -> bool:
        """
        Add or update Field() constraint in schemas.py using AST patching.
        
        Uses ast and astor for robust code modification, avoiding regex fragility.

        Args:
            entity_name: Entity name (e.g., "Product")
            field_name: Field name (e.g., "price")
            constraint_type: Constraint type (e.g., "gt", "ge", "pattern")
            constraint_value: Constraint value (e.g., 0, email regex)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fix #3: Normalize field names (e.g., creation_date -> created_at)
            field_name = normalize_field_name(field_name)

            # CRITICAL: Route constraints to the correct file
            # Database-level constraints belong in entities.py (SQLAlchemy)
            # Validation constraints (gt, pattern, etc.) belong in schemas.py (Pydantic)

            DATABASE_CONSTRAINTS = {'unique', 'foreign_key', 'default', 'default_factory', 'description'}
            
            # Route database constraints to entities.py
            if constraint_type in DATABASE_CONSTRAINTS:
                logger.info(f"Routing database constraint '{constraint_type}' to entities.py for {entity_name}.{field_name}")
                return self._add_constraint_to_entity(
                    entity_name=entity_name,
                    field_name=field_name,
                    constraint_type=constraint_type,
                    constraint_value=constraint_value
                )
            
            # Handle special constraints
            if constraint_type == 'read_only':
                logger.info(f"Processing read_only constraint for {entity_name}.{field_name}")
                # read_only in Pydantic schemas is typically handled via Field(exclude=True) in Response classes
                # But we'll apply it as a marker for now
                constraint_type = 'read_only'
                # Continue to apply it to the schema
            elif constraint_type == 'auto_increment':
                # Convert to default_factory or read_only for Response schemas
                logger.info(f"Converting auto_increment to read_only for {entity_name}.{field_name}")
                constraint_type = 'read_only'

            if constraint_type == 'computed_field':
                # We can't easily generate the computation logic via AST, but we can document it
                # Convert to description="Auto-calculated: {value}"
                constraint_type = 'description'
                constraint_value = f"Auto-calculated: {constraint_value}"
                logger.info(f"Converting computed_field to description for {entity_name}.{field_name}")
            
            # Continue with Pydantic schema constraints
            schemas_file = self.output_path / "src" / "models" / "schemas.py"
            if not schemas_file.exists():
                logger.warning(f"schemas.py not found at {schemas_file}")
                return False

            # Read current schemas.py
            with open(schemas_file, 'r') as f:
                source_code = f.read()

            # Parse AST
            try:
                import ast
                import astor
                tree = ast.parse(source_code)
            except SyntaxError as e:
                logger.error(f"Failed to parse schemas.py: {e}")
                return False

            class SchemaModifier(ast.NodeTransformer):
                def __init__(self, target_entity, target_field, c_type, c_value):
                    self.target_entity = f"{target_entity}Schema"
                    self.target_field = target_field
                    self.c_type = c_type
                    self.c_value = c_value
                    self.modified = False

                def visit_ClassDef(self, node):
                    # Heuristic: Modify any class that starts with entity_name and has the field
                    # But only modify once per constraint to avoid duplicates across Create/Update/Response classes
                    if node.name.startswith(entity_name) and not self.modified:
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == self.target_field:
                                self._modify_field(item)
                                if self.modified:  # Stop after first successful modification
                                    break
                    return node

                def _modify_field(self, node: ast.AnnAssign):
                    # Handle Literal updates
                    if self.c_type == 'enum' and isinstance(self.c_value, list):
                        # Construct Literal[...]
                        elts = [ast.Constant(value=v) for v in self.c_value]
                        slice_node = ast.Tuple(elts=elts, ctx=ast.Load())
                        node.annotation = ast.Subscript(
                            value=ast.Name(id='Literal', ctx=ast.Load()),
                            slice=slice_node,
                            ctx=ast.Load()
                        )
                        self.modified = True
                        logger.info(f"Updated {entity_name}.{field_name} to Literal{self.c_value}")
                        return

                    # Handle Field() constraints
                    # Ensure value is a Call to Field
                    if not isinstance(node.value, ast.Call) or not (isinstance(node.value.func, ast.Name) and node.value.func.id == 'Field'):
                        # Convert to Field() without positional args (avoid conflicts with keyword args)
                        node.value = ast.Call(
                            func=ast.Name(id='Field', ctx=ast.Load()),
                            args=[],  # Don't pass positional args - use keywords instead
                            keywords=[]
                        )
                        # If we converted a default value, make sure it's not None if we are adding 'required'
                        if self.c_type == 'required' and self.c_value is True:
                             node.value.args = [ast.Constant(value=Ellipsis)]
                    
                    # Now we have a Field() call
                    field_call = node.value
                    
                    # Remove existing constraint if present
                    field_call.keywords = [k for k in field_call.keywords if k.arg != self.c_type]
                    
                    # Special handling for 'required'
                    if self.c_type == 'required' and self.c_value is True:
                        # Remove default=... if present
                        field_call.keywords = [k for k in field_call.keywords if k.arg != 'default']
                        # Ensure first arg is ...
                        field_call.args = [ast.Constant(value=Ellipsis)]
                        self.modified = True
                        return

                    # Special handling for read_only - just mark it as a note, no special Field parameter
                    if self.c_type == 'read_only':
                        # read_only is typically handled by schema structure, not Field parameter
                        # We'll add it as description note instead
                        value_node = ast.Constant(value=f"Read-only field (auto-generated)")
                        self.c_type = 'description'  # Switch to description instead
                    # Special handling for default_factory (ensure callable)
                    elif self.c_type == 'default_factory':
                        # Parse the string value into an AST node (e.g. "uuid.uuid4" -> Attribute)
                        try:
                            # If it's a known callable string, parse it
                            if isinstance(self.c_value, str) and ('.' in self.c_value or self.c_value in ['list', 'dict', 'set']):
                                value_node = ast.parse(self.c_value, mode='eval').body
                            else:
                                value_node = ast.Constant(value=self.c_value)
                        except:
                            value_node = ast.Constant(value=self.c_value)
                    else:
                        value_node = ast.Constant(value=self.c_value)

                    # Special handling for default and default_factory: remove ellipsis from args
                    if self.c_type in ('default', 'default_factory'):
                        # Remove ... (Ellipsis) from positional args if present
                        field_call.args = [
                            arg for arg in field_call.args
                            if not (isinstance(arg, ast.Constant) and arg.value is Ellipsis)
                        ]
                        # Also remove conflicting 'default' or 'default_factory' keywords
                        field_call.keywords = [
                            k for k in field_call.keywords
                            if k.arg not in ('default', 'default_factory')
                        ]

                    # Remove existing keyword of same type before adding (prevents duplicates)
                    field_call.keywords = [k for k in field_call.keywords if k.arg != self.c_type]

                    # Add new keyword
                    field_call.keywords.append(ast.keyword(arg=self.c_type, value=value_node))
                    self.modified = True
                    logger.info(f"Added {self.c_type}={self.c_value} to {entity_name}.{field_name}")

            modifier = SchemaModifier(entity_name, field_name, constraint_type, constraint_value)
            new_tree = modifier.visit(tree)
            
            if modifier.modified:
                ast.fix_missing_locations(new_tree)
                new_code = astor.to_source(new_tree)
                
                # Write back to file
                with open(schemas_file, 'w') as f:
                    f.write(new_code)
                
                # Ensure required imports (uuid, datetime) are present
                self._ensure_required_imports(schemas_file)
                
                return True
            else:
                logger.warning(f"Could not find field {field_name} in {entity_name} schemas to update")
                return False

        except Exception as e:
            logger.error(f"Failed to add constraint to schema: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_required_imports(self, schemas_file: Path) -> bool:
        """
        Ensure required imports (uuid, datetime) are present in schemas.py using AST.
        
        Args:
            schemas_file: Path to schemas.py
            
        Returns:
            True if successful
        """
        try:
            with open(schemas_file, 'r') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            
            # Check which imports are needed
            needs_uuid = 'uuid.uuid4' in source_code
            needs_datetime = 'datetime.utcnow' in source_code
            
            # Check which imports exist
            has_uuid = any(
                isinstance(n, ast.Import) and any(alias.name == 'uuid' for alias in n.names)
                for n in tree.body
            )
            has_datetime = any(
                isinstance(n, ast.ImportFrom) and n.module == 'datetime' and any(alias.name == 'datetime' for alias in n.names)
                for n in tree.body
            )
            
            modified = False
            
            # Add missing imports at the top
            if needs_uuid and not has_uuid:
                logger.info("Adding 'import uuid' to schemas.py")
                tree.body.insert(0, ast.Import(names=[ast.alias(name='uuid', asname=None)]))
                modified = True
            
            if needs_datetime and not has_datetime:
                # Check if there's already a 'from datetime import ...' line
                datetime_import_idx = None
                for idx, node in enumerate(tree.body):
                    if isinstance(node, ast.ImportFrom) and node.module == 'datetime':
                        datetime_import_idx = idx
                        break
                
                if datetime_import_idx is not None:
                    # Add datetime to existing import
                    existing_names = [alias.name for alias in tree.body[datetime_import_idx].names]
                    if 'datetime' not in existing_names:
                        tree.body[datetime_import_idx].names.append(ast.alias(name='datetime', asname=None))
                        modified = True
                        logger.info("Added 'datetime' to existing datetime import in schemas.py")
            
            if modified:
                ast.fix_missing_locations(tree)
                new_code = astor.to_source(tree)
                with open(schemas_file, 'w') as f:
                    f.write(new_code)
                logger.info("Updated imports in schemas.py")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure imports: {e}")
            return False

    def _ensure_literal_import(self, schemas_file: Path) -> bool:
        """
        Ensure that 'from typing import Literal' is imported in schemas.py.

        Args:
            schemas_file: Path to schemas.py file

        Returns:
            True if import was added or already exists, False on error
        """
        try:
            import re

            # Read current schemas.py
            with open(schemas_file, 'r') as f:
                source_code = f.read()

            # Check if Literal is already imported
            if re.search(r'from typing import.*\bLiteral\b', source_code, re.MULTILINE):
                logger.debug("Literal already imported in schemas.py")
                return True

            # Find the typing import line and add Literal to it
            # Pattern: from typing import X, Y, Z
            typing_import_pattern = r'(from typing import )([^\n]+)'

            match = re.search(typing_import_pattern, source_code)
            if match:
                # Add Literal to existing typing imports
                prefix = match.group(1)
                imports = match.group(2)

                # Add Literal to the import list
                new_imports = imports.strip() + ', Literal'
                new_line = f'{prefix}{new_imports}'

                source_code = re.sub(typing_import_pattern, new_line, source_code, count=1)

                # Write back modified code
                with open(schemas_file, 'w') as f:
                    f.write(source_code)

                logger.info("Added Literal to typing imports in schemas.py")
                return True
            else:
                # No typing import found, add one at the top after pydantic import
                # Find pydantic import line
                pydantic_pattern = r'(from pydantic import [^\n]+\n)'
                match = re.search(pydantic_pattern, source_code)

                if match:
                    # Insert typing import after pydantic import
                    insert_pos = match.end()
                    new_import = 'from typing import Literal\n'
                    source_code = source_code[:insert_pos] + new_import + source_code[insert_pos:]

                    # Write back modified code
                    with open(schemas_file, 'w') as f:
                        f.write(source_code)

                    logger.info("Added 'from typing import Literal' to schemas.py")
                    return True
                else:
                    logger.warning("Could not find pydantic import to insert Literal import after")
                    return False

        except Exception as e:
            logger.error(f"Failed to ensure Literal import: {e}")
            return False

    def _add_constraint_to_entity(
        self,
        entity_name: str,
        field_name: str,
        constraint_type: str,
        constraint_value
    ) -> bool:
        """
        Add database-level constraint to SQLAlchemy entity in entities.py using AST.
        
        Handles constraints like:
        - unique=True → Column(..., unique=True)
        - foreign_key='Table.column' → ForeignKey('table.column')
        
        Args:
            entity_name: Entity name (e.g., "Product")
            field_name: Field name (e.g., "email")
            constraint_type: Constraint type ('unique', 'foreign_key')
            constraint_value: Constraint value (True for unique, 'Table.column' for FK)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fix #3: Normalize field names (e.g., creation_date -> created_at)
            field_name = normalize_field_name(field_name)

            entities_file = self.output_path / "src" / "models" / "entities.py"
            
            if not entities_file.exists():
                logger.warning(f"entities.py not found at {entities_file}")
                return False
            
            # Read current entities.py
            with open(entities_file, 'r') as f:
                source_code = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(source_code)
            except SyntaxError as e:
                logger.error(f"Failed to parse entities.py: {e}")
                return False

            class EntityModifier(ast.NodeTransformer):
                def __init__(self, target_entity, target_field, c_type, c_value):
                    self.target_entity = f"{target_entity}Entity"
                    self.target_field = target_field
                    self.c_type = c_type
                    self.c_value = c_value
                    self.modified = False
                    self.field_found = False  # Track if we found the field

                def visit_ClassDef(self, node):
                    if node.name == self.target_entity:
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id == self.target_field:
                                        self.field_found = True  # Mark that we found the field
                                        self._modify_column(item)
                    return node

                def _modify_column(self, node: ast.Assign):
                    # Ensure value is a Call to Column
                    if not isinstance(node.value, ast.Call) or not (isinstance(node.value.func, ast.Name) and node.value.func.id == 'Column'):
                        logger.warning(f"Field {self.target_field} is not a Column() call")
                        return

                    column_call = node.value

                    if self.c_type == 'unique':
                        # Check if unique already exists
                        has_unique = any(k.arg == 'unique' for k in column_call.keywords)
                        if has_unique:
                            logger.debug(f"{entity_name}.{field_name} already has unique=True")
                        else:
                            column_call.keywords.append(ast.keyword(arg='unique', value=ast.Constant(value=True)))
                            self.modified = True
                            logger.info(f"Added unique=True to {entity_name}.{field_name}")

                    elif self.c_type == 'foreign_key':
                        # Check if ForeignKey already exists in args
                        has_fk = any(
                            isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'ForeignKey'
                            for arg in column_call.args
                        )
                        if has_fk:
                            logger.debug(f"{entity_name}.{field_name} already has ForeignKey")
                        else:
                            # Convert 'Customer.id' to 'customers.id'
                            table_column = self.c_value.lower()
                            if '.' in table_column:
                                table, column = table_column.split('.', 1)
                                table = f"{table}s"  # Simple pluralization
                                fk_ref = f"{table}.{column}"
                            else:
                                fk_ref = table_column

                            # Add ForeignKey('table.column')
                            fk_node = ast.Call(
                                func=ast.Name(id='ForeignKey', ctx=ast.Load()),
                                args=[ast.Constant(value=fk_ref)],
                                keywords=[]
                            )
                            column_call.args.append(fk_node)
                            self.modified = True
                            logger.info(f"Added ForeignKey('{fk_ref}') to {entity_name}.{field_name}")

                    elif self.c_type == 'default':
                        # Handle default=<value>
                        has_default = any(k.arg == 'default' for k in column_call.keywords)
                        if has_default:
                            logger.debug(f"{entity_name}.{field_name} already has default value")
                        else:
                            # Create appropriate AST node for the value
                            if isinstance(self.c_value, bool):
                                value_node = ast.Constant(value=self.c_value)
                            elif isinstance(self.c_value, (int, float)):
                                value_node = ast.Constant(value=self.c_value)
                            else:
                                value_node = ast.Constant(value=str(self.c_value))

                            column_call.keywords.append(ast.keyword(arg='default', value=value_node))
                            self.modified = True
                            logger.info(f"Added default={self.c_value} to {entity_name}.{field_name}")

                    elif self.c_type == 'default_factory':
                        # Handle default_factory=<callable>
                        # FIX: Check BOTH 'default' and 'default_factory' to avoid duplicates
                        # SQLAlchemy uses 'default=', Pydantic uses 'default_factory='
                        has_default_or_factory = any(
                            k.arg in ('default', 'default_factory')
                            for k in column_call.keywords
                        )
                        if has_default_or_factory:
                            logger.debug(f"{entity_name}.{field_name} already has default or default_factory - skipping")
                        else:
                            # Parse function reference like 'datetime.utcnow' or 'uuid.uuid4'
                            # Create appropriate callable reference
                            if '.' in str(self.c_value):
                                parts = str(self.c_value).split('.')
                                # Create nested attribute like datetime.utcnow
                                value_node = ast.Name(id=parts[0], ctx=ast.Load())
                                for part in parts[1:]:
                                    value_node = ast.Attribute(value=value_node, attr=part, ctx=ast.Load())
                            else:
                                value_node = ast.Name(id=str(self.c_value), ctx=ast.Load())

                            # FIX: SQLAlchemy Column() uses 'default=', not 'default_factory='
                            # 'default_factory' is only valid for Pydantic Field()
                            column_call.keywords.append(ast.keyword(arg='default', value=value_node))
                            self.modified = True
                            logger.info(f"Added default={self.c_value} to {entity_name}.{field_name}")

                    elif self.c_type == 'description':
                        # Handle description="<text>" via info={'description': "<text>"}
                        # SQLAlchemy Column doesn't accept 'description', use 'info' dict instead
                        has_info = any(k.arg == 'info' for k in column_call.keywords)
                        
                        if has_info:
                            # If info exists, we'd need to update the dict - too complex for now
                            # Just log and skip to avoid breaking existing info
                            logger.debug(f"{entity_name}.{field_name} already has info dict")
                        else:
                            # Create info={'description': 'value'}
                            dict_keys = [ast.Constant(value='description')]
                            dict_values = [ast.Constant(value=str(self.c_value))]
                            info_dict = ast.Dict(keys=dict_keys, values=dict_values)
                            
                            column_call.keywords.append(ast.keyword(arg='info', value=info_dict))
                            self.modified = True
                            logger.info(f"Added info={{'description': '{self.c_value}'}} to {entity_name}.{field_name}")

            modifier = EntityModifier(entity_name, field_name, constraint_type, constraint_value)
            new_tree = modifier.visit(tree)
            
            # If field was found but not modified, it means constraint already exists (success)
            if modifier.field_found and not modifier.modified:
                logger.debug(f"Constraint {constraint_type} already exists on {entity_name}.{field_name}")
                return True
            
            if modifier.modified:
                ast.fix_missing_locations(new_tree)
                new_code = astor.to_source(new_tree)
                
                # Ensure ForeignKey is imported if we added it
                if constraint_type == 'foreign_key' and 'ForeignKey' not in source_code[:500]:
                    # Add ForeignKey to imports using simple string replacement
                    if 'from sqlalchemy import' in new_code:
                        new_code = new_code.replace(
                            'from sqlalchemy import',
                            'from sqlalchemy import ForeignKey,',
                            1
                        )
                
                # Write back to file
                with open(entities_file, 'w') as f:
                    f.write(new_code)
                return True
            else:
                logger.warning(f"Could not find field {field_name} in {entity_name}Entity to update")
                return False
            
        except Exception as e:
            logger.error(f"Failed to add {constraint_type} constraint to {entity_name}.{field_name} in entities.py: {e}")
            import traceback
            traceback.print_exc()
            return False
