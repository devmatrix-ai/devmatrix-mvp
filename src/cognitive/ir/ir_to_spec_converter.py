"""
IR to Spec Converter.

Converts ApplicationIR back to SpecRequirements format to enable reuse of existing
ModularArchitectureGenerator. This is a pragmatic bridge between the new IR-based
architecture and the legacy spec-based code generation.
"""
from typing import List, Dict, Any
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import Entity as IREntity, Attribute, DataType
from src.cognitive.ir.api_model import Endpoint as IREndpoint, HttpMethod
from src.parsing.spec_parser import SpecRequirements, Entity, Field, Endpoint


class IRToSpecConverter:
    """Converts ApplicationIR to SpecRequirements format."""

    @staticmethod
    def convert(app_ir: ApplicationIR) -> SpecRequirements:
        """
        Convert ApplicationIR to SpecRequirements.
        
        Args:
            app_ir: The ApplicationIR to convert
            
        Returns:
            SpecRequirements compatible with ModularArchitectureGenerator
        """
        # Convert entities
        entities = IRToSpecConverter._convert_entities(app_ir.domain_model.entities)
        
        # Convert endpoints
        endpoints = IRToSpecConverter._convert_endpoints(app_ir.api_model.endpoints)
        
        # Build metadata
        metadata = {
            "spec_name": app_ir.name,
            "description": app_ir.description,
            "version": app_ir.version,
            "database_type": app_ir.infrastructure_model.database.type.value,
        }
        
        # Create SpecRequirements
        spec = SpecRequirements(
            entities=entities,
            endpoints=endpoints,
            requirements=[],  # Not needed for code generation
            metadata=metadata
        )
        
        return spec

    @staticmethod
    def _convert_entities(ir_entities: List[IREntity]) -> List[Entity]:
        """Convert IR entities to Spec entities."""
        spec_entities = []
        
        for ir_entity in ir_entities:
            # Convert attributes to fields
            fields = IRToSpecConverter._convert_attributes(ir_entity.attributes)
            
            # Create Entity (snake_name is a computed property)
            entity = Entity(
                name=ir_entity.name,
                fields=fields,
                description=ir_entity.description or ""
            )
            
            spec_entities.append(entity)
        
        return spec_entities

    @staticmethod
    def _convert_attributes(ir_attributes: List[Attribute]) -> List[Field]:
        """Convert IR attributes to Spec fields."""
        fields = []
        
        for attr in ir_attributes:
            field = Field(
                name=attr.name,
                type=IRToSpecConverter._map_data_type(attr.data_type),
                required=not attr.is_nullable,  # required = NOT nullable
                unique=attr.is_unique,
                default=attr.default_value
            )
            fields.append(field)
        
        return fields

    @staticmethod
    def _convert_endpoints(ir_endpoints: List[IREndpoint]) -> List[Endpoint]:
        """Convert IR endpoints to Spec endpoints."""
        spec_endpoints = []
        
        for ir_endpoint in ir_endpoints:
            # Infer operation from HTTP method and path
            operation = IRToSpecConverter._infer_operation(
                ir_endpoint.method,
                ir_endpoint.path
            )
            
            # Extract entity name from path (e.g., /api/v1/products -> Product)
            entity_name = IRToSpecConverter._extract_entity_from_path(ir_endpoint.path)
            
            endpoint = Endpoint(
                path=ir_endpoint.path,
                method=ir_endpoint.method.value,
                operation=operation,
                entity=entity_name,
                description=ir_endpoint.description or ""
            )
            
            spec_endpoints.append(endpoint)
        
        return spec_endpoints

    @staticmethod
    def _map_data_type(data_type: DataType) -> str:
        """Map IR DataType to Spec type string."""
        type_map = {
            DataType.STRING: "string",
            DataType.INTEGER: "integer",
            DataType.FLOAT: "float",
            DataType.BOOLEAN: "boolean",
            DataType.DATETIME: "datetime",
            DataType.UUID: "uuid",
            DataType.JSON: "string",  # JSON stored as string in spec
            DataType.ENUM: "string",  # ENUM stored as string in spec
        }
        return type_map.get(data_type, "string")

    @staticmethod
    def _infer_operation(method: HttpMethod, path: str) -> str:
        """Infer CRUD operation from HTTP method and path."""
        # Check if path has ID parameter
        has_id = "{id}" in path or "/{id}" in path
        
        if method == HttpMethod.POST:
            return "create"
        elif method == HttpMethod.GET:
            return "read" if has_id else "list"
        elif method == HttpMethod.PUT or method == HttpMethod.PATCH:
            return "update"
        elif method == HttpMethod.DELETE:
            return "delete"
        else:
            return "custom"

    @staticmethod
    def _extract_entity_from_path(path: str) -> str:
        """
        Extract entity name from API path.
        
        Examples:
            /api/v1/products -> Product
            /api/v1/products/{id} -> Product
            /products -> Product
        """
        # Remove leading/trailing slashes
        path = path.strip("/")
        
        # Split by slash
        parts = path.split("/")
        
        # Find the resource name (usually last non-parameter part)
        for part in reversed(parts):
            if not part.startswith("{") and not part.endswith("}"):
                # Convert plural to singular and capitalize
                entity_name = part.rstrip("s")  # Simple pluralization removal
                return entity_name.capitalize()
        
        return "Unknown"

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert PascalCase to snake_case."""
        import re
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before uppercase letters preceded by lowercase
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
