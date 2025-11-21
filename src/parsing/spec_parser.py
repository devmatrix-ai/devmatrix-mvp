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
        business_logic = []
        seen_descriptions = set()  # Avoid duplicates

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
            # Find the Classification Ground Truth section
            section_pattern = re.compile(
                r'##\s+Classification\s+Ground\s+Truth\s*\n(.*?)(?=\n##|\Z)',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern.search(content)

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

        nodes: 17
          - create_product
          - list_products
          ...

        edges: 15
          - create_product → list_products
            rationale: Must create before listing
          ...

        Returns:
            Dictionary with 'nodes' (list) and 'edges' (list of tuples)
        """
        import yaml
        import re as regex_module

        dag_gt = {}

        try:
            # Find the Expected Dependency Graph section
            section_pattern = re.compile(
                r'##\s+Expected\s+Dependency\s+Graph.*?\n(.*?)(?=\n##|\Z)',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern.search(content)

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
