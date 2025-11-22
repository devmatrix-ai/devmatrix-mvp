"""
Enhanced Specification Parser for Code Generation Pipeline

Parses functional requirements from markdown specs including:
- Markdown headers: **F1. Description**, ### Section
- Entity definitions with fields, types, constraints
- Endpoint specifications with methods, paths, parameters
- Business logic: validations, rules, calculations

Target: Extract 17/17 functional requirements from ecommerce spec
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import re
import logging
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures (from spec.md)
# ============================================================================


@dataclass
class Requirement:
    """Single parsed requirement"""

    id: str  # "F1", "NF1"
    type: str  # "functional", "non_functional"
    priority: str  # "MUST", "SHOULD", "COULD"
    description: str  # Full requirement text
    domain: str = ""  # "crud", "auth", "payment", "workflow" (filled by classifier)
    dependencies: List[str] = field(default_factory=list)  # ["F2", "F3"]


@dataclass
class Field:
    """Entity field definition"""

    name: str  # "id", "price"
    type: str  # "UUID", "Decimal", "str", "int"
    required: bool = True
    primary_key: bool = False
    unique: bool = False
    constraints: List[str] = field(default_factory=list)  # ["gt=0", "email_format"]
    default: Optional[str] = None
    description: str = ""


@dataclass
class Relationship:
    """Entity relationship definition"""

    type: str  # "ForeignKey", "OneToMany", "ManyToMany"
    target_entity: str  # "Product", "Customer"
    field_name: str  # "customer_id", "items"
    optional: bool = False


@dataclass
class Validation:
    """Business validation rule"""

    field: str  # "price", "email", "stock"
    rule: str  # "> 0", "email_format", ">= 0"
    error_message: str = ""


@dataclass
class Entity:
    """Entity/Model definition extracted from spec"""

    name: str  # "Product", "Customer"
    fields: List[Field] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    validations: List[Validation] = field(default_factory=list)
    description: str = ""

    @property
    def snake_name(self) -> str:
        """Convert entity name to snake_case for use in file/variable names"""
        # Convert CamelCase to snake_case: Product → product, CustomerOrder → customer_order
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


@dataclass
class Param:
    """Endpoint parameter"""

    name: str  # "page", "customer_id"
    type: str  # "int", "UUID"
    location: str  # "query", "path", "body"
    required: bool = True
    default: Optional[str] = None


@dataclass
class ResponseSpec:
    """Endpoint response specification"""

    status_code: int  # 200, 201, 404, 400
    description: str  # "Success", "Not Found"
    schema: Optional[str] = None  # "Product", "List[Product]"


@dataclass
class Endpoint:
    """API endpoint specification"""

    method: str  # "POST", "GET", "PUT", "DELETE"
    path: str  # "/products", "/cart/checkout"
    entity: str  # "Product", "Cart"
    operation: str  # "create", "list", "update", "delete", "custom"
    params: List[Param] = field(default_factory=list)
    response: Optional[ResponseSpec] = None
    business_logic: List[str] = field(default_factory=list)  # ["validate_stock", "calculate_total"]
    description: str = ""


@dataclass
class BusinessLogic:
    """Business logic rule or calculation"""

    type: str  # "validation", "calculation", "state_machine"
    description: str  # "Validate stock on checkout"
    conditions: List[str] = field(default_factory=list)  # ["stock > quantity"]
    actions: List[str] = field(default_factory=list)  # ["decrease_stock"]


@dataclass
class SpecRequirements:
    """Complete parsed specification"""

    requirements: List[Requirement] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    endpoints: List[Endpoint] = field(default_factory=list)
    business_logic: List[BusinessLogic] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    classification_ground_truth: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dag_ground_truth: Dict[str, Any] = field(default_factory=dict)
    validation_ground_truth: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SpecParser Implementation
# ============================================================================


class SpecParser:
    """
    Enhanced markdown parser for functional requirements

    Extracts:
    - Functional requirements (F1-F99) from bold headers **F1. Description**
    - Non-functional requirements (NF1-NF99)
    - Entities with fields, types, constraints
    - Endpoints with methods, paths, parameters
    - Business logic (validations, rules, state machines)
    """

    def __init__(self) -> None:
        # Regex patterns for requirement extraction
        # Pattern for **F1. Description** format
        self.functional_req_pattern = re.compile(r"\*\*F(\d+)\.\s+(.+?)\*\*", re.MULTILINE)

        # Pattern for **NF1. Description** format
        self.non_functional_req_pattern = re.compile(r"\*\*NF(\d+)\.\s+(.+?)\*\*", re.MULTILINE)

        # Pattern for numbered functional requirements: "1. **Create Task**: Description"
        self.numbered_functional_pattern = re.compile(
            r"^\d+\.\s+\*\*([^*]+)\*\*:\s*(.+)$", re.MULTILINE
        )

        # Pattern for API endpoint definitions: "- `POST /tasks` - Description"
        self.endpoint_definition_pattern = re.compile(
            r"^-\s+`(GET|POST|PUT|PATCH|DELETE)\s+(/[^\`]+)`\s+-\s+(.+)$", re.MULTILINE
        )

        # Pattern for entity definitions (sections with entity names)
        self.entity_section_pattern = re.compile(r"^\d+\.\s+\*\*(\w+)\*\*\s*$", re.MULTILINE)

        # Pattern for alternative entity format: **EntityName**:
        self.entity_alt_pattern = re.compile(r"^\*\*(\w+)\*\*:\s*$", re.MULTILINE)

        # Pattern for field definitions: "- name (type, constraints)"
        self.field_pattern = re.compile(r"^\s*-\s+(\w+)\s*\(([^)]+)\)\s*$", re.MULTILINE)

        # Pattern for field definitions: "- name: type description"
        self.field_alt_pattern = re.compile(r"^\s*-\s+(\w+):\s+(.+?)(?:\s*\(|$)", re.MULTILINE)

        # Pattern for constraints: price > 0, stock >= 0
        self.constraint_pattern = re.compile(
            r"([<>=]+)\s*(\d+)|(\w+)\s+format|único|obligatorio|opcional|por defecto|default",
            re.IGNORECASE,
        )

        # Pattern for HTTP methods in text
        self.http_method_pattern = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\b")

        # Pattern for paths: /products, /cart/{id}
        self.path_pattern = re.compile(r"`?(/[\w/{}\-]+)`?")

    def parse(self, spec_path: Path) -> SpecRequirements:
        """
        Parse specification markdown file

        Args:
            spec_path: Path to markdown specification file

        Returns:
            SpecRequirements with all extracted components
        """
        try:
            content = spec_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read spec file {spec_path}: {e}")
            return SpecRequirements()

        logger.info(f"Parsing specification: {spec_path.name}")

        result = SpecRequirements()

        # Extract all components
        result.requirements = self._extract_requirements(content)
        result.entities = self._extract_entities(content)
        result.endpoints = self._extract_endpoints(content, result.requirements)
        result.business_logic = self._extract_business_logic(content, result.requirements)

        # Extract ground truth (optional sections for validation)
        result.classification_ground_truth = self._parse_classification_ground_truth(content)
        result.dag_ground_truth = self._parse_dag_ground_truth(content)
        result.validation_ground_truth = self._parse_validation_ground_truth(content)

        # If classification ground truth is missing, generate it with LLM from natural language
        if not result.classification_ground_truth and result.endpoints:
            logger.info("Classification ground truth not found, generating from endpoints with LLM...")
            result.classification_ground_truth = self._generate_classification_ground_truth_with_llm(
                content, result.endpoints
            )

        # If validation ground truth is missing, generate it with LLM from natural language
        if not result.validation_ground_truth and result.business_logic:
            logger.info("Validation ground truth not found, generating from business logic with LLM...")
            result.validation_ground_truth = self._generate_validation_ground_truth_with_llm(
                content, result.business_logic
            )

        # Metadata
        result.metadata = {
            "source_file": str(spec_path),
            "total_requirements": len(result.requirements),
            "functional_count": sum(1 for r in result.requirements if r.type == "functional"),
            "non_functional_count": sum(
                1 for r in result.requirements if r.type == "non_functional"
            ),
            "entity_count": len(result.entities),
            "endpoint_count": len(result.endpoints),
            "business_logic_count": len(result.business_logic),
        }

        logger.info(
            f"Parsed {result.metadata['total_requirements']} requirements "
            f"({result.metadata['functional_count']} functional, "
            f"{result.metadata['non_functional_count']} non-functional), "
            f"{result.metadata['entity_count']} entities, "
            f"{result.metadata['endpoint_count']} endpoints, "
            f"{result.metadata['business_logic_count']} business rules"
        )

        return result

    def _extract_requirements(self, content: str) -> List[Requirement]:
        """Extract functional and non-functional requirements from markdown"""
        requirements = []

        # Extract functional requirements (F1-F99) - format: **F1. Description**
        for match in self.functional_req_pattern.finditer(content):
            req_num = match.group(1)
            description = match.group(2).strip()

            # Find full requirement text after the header
            requirements.append(
                Requirement(
                    id=f"F{req_num}",
                    type="functional",
                    priority="MUST",  # Default, classifier will refine
                    description=description,
                    domain="",  # Will be filled by classifier
                    dependencies=[],
                )
            )

        # If no functional requirements found with **F1.** format, try numbered format
        # Format: "1. **Create Task**: Description"
        if not any(r.type == "functional" for r in requirements):
            for match in self.numbered_functional_pattern.finditer(content):
                operation = match.group(1).strip()
                description = match.group(2).strip()

                # Generate ID based on operation index
                func_count = len([r for r in requirements if r.type == "functional"]) + 1

                requirements.append(
                    Requirement(
                        id=f"F{func_count}",
                        type="functional",
                        priority="MUST",
                        description=f"{operation}: {description}",
                        domain="",
                        dependencies=[],
                    )
                )

        # Extract non-functional requirements (NF1-NF99)
        for match in self.non_functional_req_pattern.finditer(content):
            req_num = match.group(1)
            description = match.group(2).strip()

            requirements.append(
                Requirement(
                    id=f"NF{req_num}",
                    type="non_functional",
                    priority="SHOULD",  # Default
                    description=description,
                    domain="",
                    dependencies=[],
                )
            )

        # Sort by ID for consistency (numeric sorting)
        def sort_key(req: Requirement) -> tuple:
            # Extract numeric part for proper sorting
            match = re.search(r"(\d+)", req.id)
            num = int(match.group(1)) if match else 0
            return (req.type, num)

        requirements.sort(key=sort_key)

        return requirements

    def _extract_entities(self, content: str) -> List[Entity]:
        """Extract entity definitions from spec"""
        entities = []

        # Find sections that define entities
        # Look for patterns like "1. **Product**" or "**Product**:" in domain model section
        lines = content.split("\n")
        current_entity = None
        in_entity_section = False

        for i, line in enumerate(lines):
            # Detect entity definition headers (format 1: "1. **Product**")
            entity_match = self.entity_section_pattern.search(line)
            if not entity_match:
                # Try alternative format: "**Task**:"
                entity_match = self.entity_alt_pattern.search(line)

            if entity_match:
                entity_name = entity_match.group(1)
                # Common entity names (exclude nested/sub-entities like CartItem, OrderItem)
                main_entities = ["Product", "Customer", "Cart", "Order", "Task", "User"]
                if entity_name in main_entities:
                    if current_entity:
                        entities.append(current_entity)
                    current_entity = Entity(name=entity_name)
                    in_entity_section = True
                    continue

            # Extract fields from entity section
            if in_entity_section and current_entity:
                # Check if we hit next entity or end of section
                if line.strip().startswith("#") or (
                    line.strip() and not line.strip().startswith("-")
                ):
                    if line.strip() and not any(
                        line.strip().startswith(c) for c in ["-", "*", "`"]
                    ):
                        # Next section started
                        in_entity_section = False
                        continue

                # Parse field line: "- name (type, constraints)"
                field_match = self.field_pattern.search(line)
                if field_match:
                    field_name = field_match.group(1)
                    field_info = field_match.group(2)
                    field_obj = self._parse_field(field_name, field_info)
                    current_entity.fields.append(field_obj)
                else:
                    # Try alternative format: "- name: type description"
                    field_alt_match = self.field_alt_pattern.search(line)
                    if field_alt_match:
                        field_name = field_alt_match.group(1)
                        field_info = field_alt_match.group(2)
                        field_obj = self._parse_field_alt(field_name, field_info)
                        current_entity.fields.append(field_obj)

        # Add last entity
        if current_entity:
            entities.append(current_entity)

        return entities

    def _parse_field(self, name: str, info: str) -> Field:
        """Parse field definition from text"""
        # Extract type (first word)
        parts = [p.strip() for p in info.split(",")]
        field_type = parts[0] if parts else "str"

        # Map common types
        type_mapping = {
            "uuid": "UUID",
            "string": "str",
            "int": "int",
            "decimal": "Decimal",
            "float": "float",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "date": "date",
        }
        field_type = type_mapping.get(field_type.lower(), field_type)

        # Extract constraints
        constraints = []
        required = True
        primary_key = False
        unique = False
        default = None

        for part in parts[1:]:
            part_lower = part.lower()

            # Check for constraints
            if "obligatorio" in part_lower or "required" in part_lower:
                required = True
            elif "opcional" in part_lower or "optional" in part_lower:
                required = False
            elif "único" in part_lower or "unique" in part_lower:
                unique = True
            elif "primary" in part_lower or "pk" in part_lower:
                primary_key = True
            elif ">" in part or ">=" in part or "<" in part or "<=" in part:
                constraints.append(part.strip())
            elif "format" in part_lower:
                constraints.append(part.strip())
            elif "default" in part_lower or "por defecto" in part_lower:
                # Extract default value
                default_match = re.search(r"default[:\s]+([^\s,]+)", part, re.IGNORECASE)
                if default_match:
                    default = default_match.group(1)
                    # Fields with defaults are not required
                    required = False

        return Field(
            name=name,
            type=field_type,
            required=required,
            primary_key=primary_key,
            unique=unique,
            constraints=constraints,
            default=default,
        )

    def _parse_field_alt(self, name: str, info: str) -> Field:
        """Parse field definition from alternative format: 'name: type description'"""
        # Extract type from info
        parts = info.split()
        if not parts:
            return Field(name=name, type="str")

        field_type = parts[0]

        # Map common types
        type_mapping = {
            "unique": "UUID",
            "identifier": "UUID",
            "string": "str",
            "integer": "int",
            "int": "int",
            "decimal": "Decimal",
            "float": "float",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "timestamp": "datetime",
            "date": "date",
        }
        field_type = type_mapping.get(field_type.lower(), field_type)

        # Check for constraints in description
        info_lower = info.lower()
        constraints = []
        required = True

        if "required" in info_lower:
            required = True
        elif "optional" in info_lower:
            required = False

        if "max" in info_lower:
            max_match = re.search(r"max[:\s]+(\d+)", info_lower)
            if max_match:
                constraints.append(f"max_length={max_match.group(1)}")

        if "default" in info_lower:
            default_match = re.search(r"default[:\s]+(\w+)", info_lower)
            if default_match:
                return Field(
                    name=name,
                    type=field_type,
                    required=required,
                    constraints=constraints,
                    default=default_match.group(1),
                )

        return Field(name=name, type=field_type, required=required, constraints=constraints)

    def _extract_endpoints(self, content: str, requirements: List[Requirement]) -> List[Endpoint]:
        """Extract endpoint specifications from requirements and endpoint definitions"""
        endpoints = []

        # First, try to extract from explicit endpoint definitions (e.g., "- `POST /tasks` - Description")
        for match in self.endpoint_definition_pattern.finditer(content):
            method = match.group(1)
            path = match.group(2)
            description = match.group(3).strip()

            # Detect operation and entity from path and description
            operation = self._detect_operation(description.lower())
            entity = self._detect_entity_from_path(path)

            endpoint = Endpoint(
                method=method,
                path=path,
                entity=entity,
                operation=operation,
                business_logic=[],
                description=description,
            )
            endpoints.append(endpoint)

        # If no explicit endpoints found, extract from requirements
        if not endpoints:
            for req in requirements:
                if req.type != "functional":
                    continue

                # Detect operation type from requirement text
                desc_lower = req.description.lower()

                # Detect CRUD operations
                operation = self._detect_operation(desc_lower)
                method = self._detect_http_method(desc_lower, operation)
                entity = self._detect_entity(desc_lower)
                path = self._generate_path(entity, operation, desc_lower)


                # Extract business logic references
                business_logic = self._detect_business_logic_refs(req.description)

                endpoint = Endpoint(
                    method=method,
                    path=path,
                    entity=entity,
                    operation=operation,
                    business_logic=business_logic,
                    description=req.description,
                )

                endpoints.append(endpoint)

        return endpoints

    def _detect_operation(self, text: str) -> str:
        """Detect operation type from requirement text"""
        if any(word in text for word in ["create", "register", "add"]):
            return "create"
        elif any(word in text for word in ["list", "get all"]):
            return "list"
        elif any(word in text for word in ["get", "view", "detail", "retrieve"]):
            return "read"
        elif any(word in text for word in ["update", "modify", "change"]):
            return "update"
        elif any(word in text for word in ["delete", "remove", "deactivate", "clear"]):
            return "delete"
        elif any(word in text for word in ["checkout", "payment", "simulate", "cancel"]):
            return "custom"
        else:
            return "custom"

    def _detect_http_method(self, text: str, operation: str) -> str:
        """Detect HTTP method from text and operation"""
        # Direct method mentions
        method_match = self.http_method_pattern.search(text.upper())
        if method_match:
            return method_match.group(1)

        # Infer from operation
        operation_method_map = {
            "create": "POST",
            "list": "GET",
            "read": "GET",
            "update": "PUT",
            "delete": "DELETE",
            "custom": "POST",
        }
        return operation_method_map.get(operation, "GET")

    def _detect_entity(self, text: str) -> str:
        """Detect entity name from requirement text (English only)"""
        text_lower = text.lower()

        # Priority detection for specific patterns
        # F8: "Create cart for customer" → Cart (not Customer)
        if "cart" in text_lower and "create" in text_lower:
            return "Cart"

        # F12: "Clear cart" → Cart (operation on cart items)
        if "cart" in text_lower and "clear" in text_lower:
            return "Cart"

        # "item" operations on cart → Cart entity (not Item)
        if "item" in text_lower and ("cart" in text_lower or "quantity" in text_lower):
            return "Cart"

        # Payment operations → Order entity
        if "payment" in text_lower:
            return "Order"

        # List orders of customer → Customer (nested resource)
        if "list" in text_lower and "order" in text_lower and "customer" in text_lower:
            return "Customer"

        # Check for main entities (priority order: Cart, Product, Order, Customer, Task, User)
        priority_entities = ["Cart", "Product", "Order", "Customer", "Task", "User"]
        for entity in priority_entities:
            if entity.lower() in text_lower:
                return entity

        return "Unknown"

    def _detect_entity_from_path(self, path: str) -> str:
        """Detect entity name from API path"""
        # Extract entity from path like /tasks, /products/{id}, /cart/checkout
        path_parts = [p for p in path.split("/") if p and "{" not in p]

        if not path_parts:
            return "Unknown"

        # Get first significant part (entity name plural)
        entity_plural = path_parts[0]

        # Map plurals to singular entity names
        plural_mapping = {
            "tasks": "Task",
            "products": "Product",
            "customers": "Customer",
            "carts": "Cart",
            "orders": "Order",
            "users": "User",
            "items": "Item",
        }

        return plural_mapping.get(entity_plural, entity_plural.capitalize())

    def _generate_path(self, entity: str, operation: str, text: str) -> str:
        """Generate API path from entity and operation (English only)"""
        # Check if path is explicitly mentioned
        path_match = self.path_pattern.search(text)
        if path_match:
            return path_match.group(1)

        # Generate standard RESTful path
        entity_lower = entity.lower() + "s"  # pluralize
        text_lower = text.lower()

        # Nested resource: items in cart
        if entity == "Cart" and ("item" in text_lower or "clear" in text_lower):
            if operation == "create" or "add" in text_lower:
                return f"/{entity_lower}/{{id}}/items"
            elif operation == "update" or "quantity" in text_lower:
                return f"/{entity_lower}/{{id}}/items/{{item_id}}"
            elif operation == "delete" or "clear" in text_lower:
                # F12: Clear cart → DELETE /carts/{id}/items
                return f"/{entity_lower}/{{id}}/items"

        # Nested resource: orders of customer
        if "order" in text_lower and entity == "Customer":
            return f"/{entity_lower}/{{id}}/orders"

        # Standard CRUD operations
        if operation in ["list", "create"]:
            return f"/{entity_lower}"
        elif operation in ["read", "update", "delete"]:
            return f"/{entity_lower}/{{id}}"
        else:
            # Custom operations with entity ID context
            if "checkout" in text_lower:
                return f"/{entity_lower}/{{id}}/checkout"
            elif "payment" in text_lower:
                return f"/{entity_lower}/{{id}}/payment"
            elif "cancel" in text_lower:
                return f"/{entity_lower}/{{id}}/cancel"
            else:
                return f"/{entity_lower}/action"

    def _detect_business_logic_refs(self, text: str) -> List[str]:
        """Detect business logic references in requirement text"""
        logic_refs = []

        text_lower = text.lower()

        # Validation keywords
        if any(word in text_lower for word in ["validar", "validate", "verificar", "verify"]):
            logic_refs.append("validation")

        # Stock/inventory
        if any(word in text_lower for word in ["stock", "inventario", "inventory"]):
            logic_refs.append("check_stock")

        # Calculation
        if any(word in text_lower for word in ["calcular", "calculate", "suma", "sum", "total"]):
            logic_refs.append("calculate_total")

        # State changes
        if any(
            word in text_lower for word in ["cambiar estado", "change status", "marcar", "mark"]
        ):
            logic_refs.append("change_status")

        return logic_refs

    def _extract_business_logic(
        self, content: str, requirements: List[Requirement]
    ) -> List[BusinessLogic]:
        """Extract business logic rules from spec"""
        logger.info("=== _extract_business_logic() called ===")
        business_logic = []
        seen_descriptions = set()  # Avoid duplicates

        # Extract validations from Business Validations section (format: **V1. Description**)
        validation_pattern = re.compile(r"\*\*V(\d+)\.\s+(.+?)\*\*", re.MULTILINE)
        validation_matches = list(validation_pattern.finditer(content))
        logger.info(f"Found {len(validation_matches)} validation headers in Business Validations section")

        for match in validation_matches:
            val_num = match.group(1)
            description = match.group(2).strip()

            # Get full validation text (look for lines after header)
            full_desc = description
            if full_desc not in seen_descriptions:
                business_logic.append(
                    BusinessLogic(type="validation", description=full_desc)
                )
                seen_descriptions.add(full_desc)
                logger.debug(f"Added validation V{val_num}: {full_desc}")

        # Extract validation rules from requirements
        for req in requirements:
            desc_lower = req.description.lower()

            # Detect validations
            if any(
                word in desc_lower
                for word in [
                    "validar",
                    "validate",
                    "verificar",
                    "verify",
                    "devolver 400",
                    "devolver 404",
                ]
            ):
                if req.description not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(type="validation", description=req.description)
                    )
                    seen_descriptions.add(req.description)

            # Detect calculations
            if any(
                word in desc_lower
                for word in [
                    "calcular",
                    "calculate",
                    "suma",
                    "sum",
                    "total",
                    "descontar",
                    "discount",
                ]
            ):
                if req.description not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(type="calculation", description=req.description)
                    )
                    seen_descriptions.add(req.description)

            # Detect state machines
            if any(
                word in desc_lower
                for word in ["cambiar estado", "change status", "marcar", "mark", "pending", "paid"]
            ):
                if req.description not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(type="state_machine", description=req.description)
                    )
                    seen_descriptions.add(req.description)

            # Detect stock management
            if "stock" in desc_lower:
                if req.description not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(type="validation", description=req.description)
                    )
                    seen_descriptions.add(req.description)

            # Detect email/format validations
            if "email" in desc_lower or "format" in desc_lower:
                if req.description not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(type="validation", description=req.description)
                    )
                    seen_descriptions.add(req.description)

        # Extract validations from entity constraints
        lines = content.split("\n")
        for line in lines:
            line_lower = line.lower()

            # Price validations
            if "price" in line_lower and (">" in line and "0" in line):
                desc = "Price validation: must be greater than 0"
                if desc not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(type="validation", description=desc, conditions=["price > 0"])
                    )
                    seen_descriptions.add(desc)

            # Stock validations
            if "stock" in line_lower and (">=" in line or "≥" in line):
                desc = "Stock validation: must be non-negative"
                if desc not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(
                            type="validation", description=desc, conditions=["stock >= 0"]
                        )
                    )
                    seen_descriptions.add(desc)

            # Email validations
            if "email" in line_lower and ("format" in line_lower or "formato" in line_lower):
                desc = "Email validation: must be valid email format"
                if desc not in seen_descriptions:
                    business_logic.append(
                        BusinessLogic(
                            type="validation", description=desc, conditions=["email_format"]
                        )
                    )
                    seen_descriptions.add(desc)

        return business_logic

    def _parse_classification_ground_truth(self, content: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse Classification Ground Truth section from spec (YAML format).

        Expected format:
        ## Classification Ground Truth

        F1_create_product:
          domain: crud
          risk: high
          rationale: Creates product entity

        Returns:
            Dictionary mapping requirement_id -> {domain, risk, rationale}
        """
        import yaml

        ground_truth = {}

        try:
            # Try format 1: Classification Ground Truth with ```yaml blocks
            # Allow optional whitespace (including blank lines) between header and ```yaml
            section_pattern_blocks = re.compile(
                r'##\s+Classification\s+Ground\s+Truth.*?\n\s*```yaml\n(.*?)\n```',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern_blocks.search(content)

            if match:
                yaml_content = match.group(1).strip()
            else:
                # Try format 2: Plain YAML without code blocks
                # Capture everything from header until next ## section or end of file
                section_pattern_plain = re.compile(
                    r'##\s+Classification\s+Ground\s+Truth.*?\n(.*?)(?=\n##|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                match = section_pattern_plain.search(content)

                if not match:
                    logger.debug("No Classification Ground Truth section found in spec")
                    return ground_truth

                yaml_content = match.group(1).strip()

            # Parse YAML
            data = yaml.safe_load(yaml_content)

            if data and isinstance(data, dict):
                ground_truth = data
                logger.info(f"Loaded classification ground truth for {len(ground_truth)} requirements")

        except Exception as e:
            logger.warning(f"Failed to parse Classification Ground Truth: {e}")

        return ground_truth

    def _parse_dag_ground_truth(self, content: str) -> Dict[str, Any]:
        """
        Parse Expected Dependency Graph section from spec (YAML format).

        Expected format:
        ## Expected Dependency Graph (Ground Truth)

        ```yaml
        nodes:
          - create_product
          - list_products
          ...

        edges:
          - create_product → list_products
          ...
        ```

        Returns:
            Dictionary with 'nodes' (list) and 'edges' (list of tuples)
        """
        import yaml
        import re as regex_module

        dag_gt = {}

        try:
            # Try format 1: Expected Dependency Graph with ```yaml blocks
            # Allow optional whitespace (including blank lines) between header and ```yaml
            section_pattern_blocks = re.compile(
                r'##\s+Expected\s+Dependency\s+Graph.*?\n\s*```yaml\n(.*?)\n```',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern_blocks.search(content)

            if match:
                yaml_content = match.group(1).strip()
            else:
                # Try format 2: Plain YAML without code blocks
                # Capture everything from header until next ## section or end of file
                section_pattern_plain = re.compile(
                    r'##\s+Expected\s+Dependency\s+Graph.*?\n(.*?)(?=\n##|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                match = section_pattern_plain.search(content)

                if not match:
                    logger.debug("No Expected Dependency Graph section found in spec")
                    return dag_gt

                yaml_content = match.group(1).strip()

            # Parse YAML
            data = yaml.safe_load(yaml_content)

            if data and isinstance(data, dict):
                # Extract nodes
                if 'nodes' in data:
                    # Handle both formats: "nodes: 17" (count) and list of nodes
                    nodes_data = data['nodes']
                    if isinstance(nodes_data, list):
                        dag_gt['nodes'] = nodes_data
                        dag_gt['node_count'] = len(nodes_data)
                    elif isinstance(nodes_data, int):
                        dag_gt['node_count'] = nodes_data

                # Extract edges
                if 'edges' in data:
                    # Handle both formats: "edges: 15" (count) and list of edges
                    edges_data = data['edges']
                    if isinstance(edges_data, list):
                        # Parse edge strings like "create_product → list_products"
                        parsed_edges = []
                        edge_pattern = regex_module.compile(r'(\w+)\s*(?:→|->)\s*(\w+)')

                        for edge_item in edges_data:
                            if isinstance(edge_item, str):
                                edge_match = edge_pattern.search(edge_item)
                                if edge_match:
                                    from_node = edge_match.group(1)
                                    to_node = edge_match.group(2)
                                    parsed_edges.append((from_node, to_node))

                        dag_gt['edges'] = parsed_edges
                        dag_gt['edge_count'] = len(parsed_edges)
                    elif isinstance(edges_data, int):
                        dag_gt['edge_count'] = edges_data

                logger.info(
                    f"Loaded DAG ground truth: "
                    f"{dag_gt.get('node_count', 0)} nodes, "
                    f"{dag_gt.get('edge_count', 0)} edges"
                )

        except Exception as e:
            logger.warning(f"Failed to parse Expected Dependency Graph: {e}")

        return dag_gt

    def _parse_validation_ground_truth(self, content: str) -> Dict[str, Any]:
        """
        Parse Validation Ground Truth section from spec (YAML format).

        Expected format:
        ## Validation Ground Truth

        ```yaml
        validation_count: 6

        validations:
          V1_product_price:
            entity: Product
            field: price
            constraint: gt=0
            description: "Product price must be greater than 0"
          ...
        ```

        Returns:
            Dictionary with 'validation_count' and 'validations' dict
        """
        import yaml

        val_gt = {}

        try:
            # Try format 1: Validation Ground Truth with ```yaml blocks
            # Allow optional whitespace (including blank lines) between header and ```yaml
            section_pattern_blocks = re.compile(
                r'##\s+Validation\s+Ground\s+Truth.*?\n\s*```yaml\n(.*?)\n```',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern_blocks.search(content)

            if match:
                yaml_content = match.group(1).strip()
            else:
                # Try format 2: Plain YAML without code blocks
                # Capture everything from header until next ## section or end of file
                section_pattern_plain = re.compile(
                    r'##\s+Validation\s+Ground\s+Truth.*?\n(.*?)(?=\n##|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                match = section_pattern_plain.search(content)

                if not match:
                    logger.debug("No Validation Ground Truth section found in spec")
                    return val_gt

                yaml_content = match.group(1).strip()

            # Parse YAML
            data = yaml.safe_load(yaml_content)

            if data and isinstance(data, dict):
                # Extract validation_count
                if 'validation_count' in data:
                    val_gt['validation_count'] = data['validation_count']

                # Extract validations
                if 'validations' in data and isinstance(data['validations'], dict):
                    val_gt['validations'] = data['validations']

                logger.info(
                    f"Loaded validation ground truth: "
                    f"{val_gt.get('validation_count', 0)} validations defined"
                )

        except Exception as e:
            logger.warning(f"Failed to parse Validation Ground Truth: {e}")

        return val_gt

    def _generate_classification_ground_truth_with_llm(
        self, content: str, endpoints: List['Endpoint']
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate classification ground truth from natural language spec using LLM.

        This allows specs to be written in any format - the LLM extracts and
        structures the ground truth in standard YAML format.

        Args:
            content: Raw markdown spec content
            endpoints: Parsed endpoints

        Returns:
            Dictionary mapping node names to domain/risk classifications
        """
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

            # Build endpoint summary for LLM
            endpoint_list = "\n".join([
                f"- {ep.method} {ep.path}: {ep.description}"
                for ep in endpoints
            ])

            prompt = f"""Analyze this API specification and generate classification ground truth in YAML format.

# Specification
{content[:3000]}  # Limit context to avoid token limits

# Detected Endpoints
{endpoint_list}

# Task
Generate a YAML classification for each endpoint. For each endpoint, assign:
- A unique requirement ID (F1, F2, etc. sequentially)
- domain: crud | workflow | payment | auth | integration
- risk: low | medium | high

Format:
```yaml
F{{ID}}_{{node_name}}:
  domain: {{domain}}
  risk: {{risk}}
```

Where node_name is derived from the endpoint operation (e.g., create_product, list_products, get_product).

Rules:
- CRUD operations (GET, POST single items, PUT, DELETE) → crud domain, low-medium risk
- Workflows (checkout, payment processing, multi-step operations) → workflow/payment domain, medium-high risk
- List/search operations → crud domain, low risk
- Payment operations → payment domain, high risk

Generate ONLY the YAML block, no explanation."""

            import asyncio

            client = EnhancedAnthropicClient()

            from src.config.constants import DEFAULT_MODEL

            # Handle both sync and async contexts
            try:
                # Try to get running loop (we're inside async context)
                loop = asyncio.get_running_loop()
                # We're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(
                            prompt=prompt,
                            model=DEFAULT_MODEL,
                            max_tokens=2000,
                            temperature=0.0
                        )
                    )
                    response = future.result(timeout=60)
            except RuntimeError:
                # No running loop, we can use run_until_complete
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                response = loop.run_until_complete(
                    client.generate(
                        prompt=prompt,
                        model=DEFAULT_MODEL,
                        max_tokens=2000,
                        temperature=0.0
                    )
                )

            # Response could be SimpleResponse object with .text attribute
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', '')
            else:
                response_text = str(response)

            # Debug: log response for development
            logger.debug(f"LLM response (first 500 chars): {response_text[:500]}")

            # Extract YAML from response
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if not yaml_match:
                # Try without code blocks
                yaml_match = re.search(r'(F\d+_\w+:.*)', response_text, re.DOTALL)

            if yaml_match:
                yaml_content = yaml_match.group(1)
                classification_gt = yaml.safe_load(yaml_content)

                logger.info(
                    f"✅ Generated classification ground truth with LLM: "
                    f"{len(classification_gt)} entries"
                )
                return classification_gt
            else:
                logger.warning(f"LLM response did not contain valid YAML. Response preview: {response_text[:200]}")
                return {}

        except ImportError:
            logger.warning("EnhancedAnthropicClient not available, skipping LLM generation")
            return {}
        except Exception as e:
            logger.warning(f"Failed to generate classification ground truth with LLM: {e}")
            return {}

    def _generate_validation_ground_truth_with_llm(
        self, content: str, business_logic: List['BusinessLogic']
    ) -> Dict[str, Any]:
        """
        Generate validation ground truth from natural language spec using LLM.

        Extracts validation rules from Business Validations section and structures
        them in YAML format for ComplianceValidator.

        Args:
            content: Raw markdown spec content
            business_logic: Parsed business logic including validations

        Returns:
            Dictionary with 'validation_count' and 'validations' dict
        """
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

            # Filter only validations from business logic
            validations_list = [bl for bl in business_logic if bl.type == "validation"]

            if not validations_list:
                logger.debug("No validations found in business logic, skipping LLM generation")
                return {}

            # Build validation summary for LLM
            validation_descriptions = "\n".join([
                f"- {val.description}"
                for val in validations_list
            ])

            prompt = f"""Generate COMPLETE validation ground truth for perfect code generation.

# Specification
{content[:3000]}

# Explicit Validations from Spec
{validation_descriptions}

# STEP-BY-STEP PROCESS (Follow this exactly):

## Step 1: Read each validation description CAREFULLY
For each validation like "Stock >= 0" or "Quantity > 0":
- Identify the FIELD being validated (e.g., "stock", "quantity")
- Identify the OPERATOR (e.g., >=, >, <, <=, ==)
- Identify the NUMERIC VALUE (e.g., 0, 1, 100) - THIS MUST BE A NUMBER, NEVER A FIELD NAME

## Step 2: Map to correct constraint format
- "Stock >= 0" → constraint: ge=0 (NOT ge=stock, NOT ge=quantity)
- "Quantity > 0" → constraint: gt=0 (NOT gt=quantity, NOT gt=stock)
- "Price > 0" → constraint: gt=0 (NOT gt=price)
- "Email format" → constraint: email_format (keyword, no value)
- "ID is UUID" → constraint: uuid_format (keyword, no value)

## Step 3: Determine which ENTITY has this FIELD
Look at the spec to find which entity (Product, Customer, Cart, etc.) has this field.
IMPORTANT: Don't confuse similar field names across different entities!

## Step 4: Generate validation entry
Create one validation entry with:
- entity: EntityName (capitalized)
- field: field_name (lowercase)
- constraint: the_constraint (MUST be number or keyword, NEVER a field name)
- description: simple one-line description

# COMMON ERRORS TO AVOID:

❌ WRONG: constraint: ge=quantity (using field name as value)
✅ RIGHT: constraint: ge=0 (using number as value)

❌ WRONG: constraint: gt=stock (using field name as value)
✅ RIGHT: constraint: gt=0 (using number as value)

❌ WRONG: entity: CartItem, field: stock, constraint: ge=0 (wrong entity - stock is in Product, not CartItem!)
✅ RIGHT: entity: Product, field: stock, constraint: ge=0

❌ WRONG: entity: Product, field: quantity, constraint: gt=0 (wrong entity - quantity is in CartItem/OrderItem, not Product!)
✅ RIGHT: entity: CartItem, field: quantity, constraint: gt=0

# VALIDATION TYPES TO GENERATE:

1. **Explicit validations** from Business Validations section (analyze each one carefully)
2. **Implicit validations** for production code:
   - UUID format for all ID fields
   - Email format for email fields
   - Required for non-nullable fields
   - Enum for status/type fields with fixed values
   - Min/max lengths for strings
   - Positive/non-negative for numeric fields that shouldn't be negative

Format:
```yaml
validation_count: {{total_count}}

validations:
  V{{ID}}_{{entity}}_{{field}}:
    entity: {{EntityName}}
    field: {{field_name}}
    constraint: {{constraint_type}}
    description: {{simple_validation_description}}
```

# ALLOWED CONSTRAINT TYPES (constraint value must be NUMBER or KEYWORD - NEVER a field name):

Numeric Constraints (value MUST be a number):
- gt=0 → "greater than 0" (example: price > 0, quantity > 0)
- ge=0 → "greater than or equal to 0" (example: stock >= 0, total >= 0)
- lt=100 → "less than 100" (use actual number, not field name)
- le=100 → "less than or equal to 100" (use actual number, not field name)

Format Constraints (keyword only, NO value):
- email_format → for email fields
- uuid_format → for ID fields (Product.id, Customer.id, etc.)

Presence Constraints (keyword only, NO value):
- required → field must be present and not null

Value Constraints (WITH values - extract from spec):
- enum=VALUE1,VALUE2,VALUE3 → for status/type fields with fixed allowed values
  Example: If spec says 'status: enum ["OPEN", "CLOSED"]' → constraint: enum=OPEN,CLOSED
  Example: If spec says 'status: enum ["PENDING", "PAID", "CANCELLED"]' → constraint: enum=PENDING,PAID,CANCELLED

String Length Constraints (value MUST be a number):
- min_length=1 → minimum string length (use actual number)
- max_length=255 → maximum string length (use actual number)

# VALIDATION CHECKLIST (Check each constraint you write):

Before writing "constraint: X", ask yourself:
1. ✅ Is X a NUMBER (0, 1, 100) or a KEYWORD (required, email_format)?
2. ❌ Is X a field name (quantity, stock, price)? → WRONG! Use the numeric value instead
3. ✅ Does this constraint match the validation description exactly?
4. ✅ Am I using the correct entity for this field?

Example showing CORRECT constraint mapping:
```yaml
validation_count: 8

validations:
  # Example 1: "Price > 0" → constraint MUST be gt=0 (the number), NOT gt=price (field name)
  V1_product_price:
    entity: Product
    field: price
    constraint: gt=0
    description: Product price must be greater than 0

  # Example 2: "Stock >= 0" → constraint MUST be ge=0 (the number), NOT ge=stock or ge=quantity
  V2_product_stock:
    entity: Product
    field: stock
    constraint: ge=0
    description: Product stock must be non-negative

  # Example 3: "Cart item quantity > 0" → entity is CartItem (where quantity field exists), NOT Product
  V3_cartitem_quantity:
    entity: CartItem
    field: quantity
    constraint: gt=0
    description: Cart item quantity must be greater than 0

  # Example 4: "Email format" → constraint is keyword email_format, NO value needed
  V4_customer_email_format:
    entity: Customer
    field: email
    constraint: email_format
    description: Customer email must be valid email format

  # Example 5: All ID fields need UUID format (implicit validation)
  V5_product_id:
    entity: Product
    field: id
    constraint: uuid_format
    description: Product ID must be valid UUID

  # Example 6: Non-nullable fields need required constraint (implicit validation)
  V6_product_name:
    entity: Product
    field: name
    constraint: required
    description: Product name is required

  # Example 7: Email fields need BOTH email_format AND required (two separate validations)
  V7_customer_email_required:
    entity: Customer
    field: email
    constraint: required
    description: Customer email is required

  # Example 8: Status fields with fixed values need enum constraint WITH VALUES
  # If spec says: status: enum ["PENDING_PAYMENT", "PAID", "CANCELLED"]
  # Then extract the values and write: constraint: enum=PENDING_PAYMENT,PAID,CANCELLED
  V8_order_status:
    entity: Order
    field: status
    constraint: enum=PENDING_PAYMENT,PAID,CANCELLED
    description: Order status must be PENDING_PAYMENT, PAID, or CANCELLED
```

CRITICAL YAML FORMATTING RULES:
1. DO NOT use quotes around description values - write them directly without quotes
2. Keep descriptions simple and on a single line
3. Avoid special characters, apostrophes, or quotes in descriptions
4. Each description must be valid YAML without escaping

FINAL REMINDER BEFORE YOU START:
- Read each validation SLOWLY and CAREFULLY
- For "Stock >= 0" write constraint: ge=0 (the NUMBER zero, NOT the word "stock" or "quantity")
- For "Quantity > 0" write constraint: gt=0 (the NUMBER zero, NOT the word "quantity")
- NEVER EVER use a field name (like stock, quantity, price) as a constraint value
- Always use the ACTUAL NUMERIC VALUE from the validation description
- Double-check each entity-field mapping before writing it

Generate validation ground truth that represents what PERFECT production code should have.
This ground truth will be used to validate the generated code, so include ALL validations needed.

Generate ONLY the YAML block, no explanation."""

            import asyncio

            client = EnhancedAnthropicClient()

            from src.config.constants import DEFAULT_MODEL

            # Handle both sync and async contexts
            try:
                # Try to get running loop (we're inside async context)
                loop = asyncio.get_running_loop()
                # We're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(
                            prompt=prompt,
                            model=DEFAULT_MODEL,
                            max_tokens=2000,
                            temperature=0.0
                        )
                    )
                    response = future.result(timeout=60)
            except RuntimeError:
                # No running loop, we can use run_until_complete
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                response = loop.run_until_complete(
                    client.generate(
                        prompt=prompt,
                        model=DEFAULT_MODEL,
                        max_tokens=2000,
                        temperature=0.0
                    )
                )

            # Response could be SimpleResponse object with .text attribute
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', '')
            else:
                response_text = str(response)

            # Debug: log response for development
            logger.debug(f"LLM validation response (first 500 chars): {response_text[:500]}")

            # Extract YAML from response
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if not yaml_match:
                # Try without code blocks
                yaml_match = re.search(r'(validation_count:.*)', response_text, re.DOTALL)

            if yaml_match:
                yaml_content = yaml_match.group(1)
                validation_gt = yaml.safe_load(yaml_content)

                logger.info(
                    f"✅ Generated validation ground truth with LLM: "
                    f"{validation_gt.get('validation_count', 0)} validations"
                )
                return validation_gt
            else:
                logger.warning(f"LLM response did not contain valid YAML. Response preview: {response_text[:200]}")
                return {}

        except ImportError:
            logger.warning("EnhancedAnthropicClient not available, skipping LLM validation generation")
            return {}
        except Exception as e:
            logger.warning(f"Failed to generate validation ground truth with LLM: {e}")
            return {}
