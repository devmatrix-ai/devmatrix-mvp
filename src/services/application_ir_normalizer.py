"""
Application IR Normalizer

Normalizes ApplicationIR to structure compatible with Jinja2 templates.
Bridges the gap between the cognitive IR model and existing code generation templates.
"""

from typing import List, Dict, Any, Optional
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DataType, Entity, Attribute
from src.cognitive.ir.api_model import Endpoint, HttpMethod, APIParameter
import re


class ApplicationIRNormalizer:
    """Normaliza ApplicationIR a estructura compatible con templates Jinja2.

    Los templates Jinja2 esperan:
    - entities: List[Entity]
    - Entity.name: str
    - Entity.plural: str
    - Entity.fields: List[Field]
    - Field.name: str
    - Field.type: str (uno de: str, int, UUID, datetime, bool, decimal)
    - Field.required: bool
    - Field.default: any

    ApplicationIR proporciona:
    - domain_model.entities: List[Entity]
    - Entity.name: str
    - Entity.attributes: List[Attribute]
    - Attribute.name: str
    - Attribute.data_type: DataTypeEnum
    - Attribute.is_nullable: bool
    - Attribute.default_value: any
    """

    # DataType mapping from ApplicationIR to template format
    DATATYPE_MAPPING = {
        DataType.STRING: 'str',
        DataType.INTEGER: 'int',
        DataType.FLOAT: 'float',
        DataType.BOOLEAN: 'bool',
        DataType.DATETIME: 'datetime',
        DataType.UUID: 'UUID',
        DataType.JSON: 'json',
        DataType.ENUM: 'str',  # Enums are represented as strings in templates
    }

    # HTTP Method mapping
    HTTP_METHOD_MAPPING = {
        HttpMethod.GET: 'GET',
        HttpMethod.POST: 'POST',
        HttpMethod.PUT: 'PUT',
        HttpMethod.DELETE: 'DELETE',
        HttpMethod.PATCH: 'PATCH',
    }

    def __init__(self, app_ir: ApplicationIR):
        """Initialize normalizer with ApplicationIR instance."""
        self.app_ir = app_ir

    def get_entities(self) -> List[Dict[str, Any]]:
        """Convierte ApplicationIR entities a formato compatible con templates.

        Returns:
            List of entity dictionaries with normalized structure
        """
        entities = []

        for entity in self.app_ir.domain_model.entities:
            normalized_entity = {
                'name': entity.name,
                'plural': self.pluralize(entity.name),
                'fields': self._normalize_attributes(entity.attributes),
                'description': entity.description or f"{entity.name} entity",
                'is_aggregate_root': entity.is_aggregate_root,
                'relationships': self._normalize_relationships(entity.relationships) if entity.relationships else []
            }
            entities.append(normalized_entity)

        return entities

    def _normalize_attributes(self, attributes: List[Attribute]) -> List[Dict[str, Any]]:
        """Convert Attribute list to field dictionary format.

        Args:
            attributes: List of ApplicationIR Attribute objects

        Returns:
            List of field dictionaries compatible with templates
        """
        fields = []

        # Always add standard fields that templates expect
        standard_fields = [
            {'name': 'id', 'type': 'UUID', 'required': True, 'primary_key': True},
            {'name': 'created_at', 'type': 'datetime', 'required': True},
            {'name': 'updated_at', 'type': 'datetime', 'required': True}
        ]

        # Check if these fields already exist in attributes
        existing_field_names = {attr.name for attr in attributes}

        for std_field in standard_fields:
            if std_field['name'] not in existing_field_names:
                fields.append(std_field)

        # Process actual attributes
        for attr in attributes:
            field = {
                'name': attr.name,
                'type': self.datatype_to_string(attr.data_type),
                'required': not attr.is_nullable,
                'default': attr.default_value,
                'unique': attr.is_unique,
                'primary_key': attr.is_primary_key,
                'description': attr.description or '',
            }

            # Add constraints if they exist
            if attr.constraints:
                field['constraints'] = attr.constraints

            fields.append(field)

        return fields

    def _normalize_relationships(self, relationships: List[Any]) -> List[Dict[str, Any]]:
        """Normalize relationship information for templates.

        Args:
            relationships: List of relationship objects

        Returns:
            List of normalized relationship dictionaries
        """
        normalized = []

        for rel in relationships:
            normalized.append({
                'source_entity': rel.source_entity,
                'target_entity': rel.target_entity,
                'type': rel.type.value if hasattr(rel.type, 'value') else str(rel.type),
                'field_name': rel.field_name,
                'back_populates': rel.back_populates
            })

        return normalized

    def get_endpoints(self) -> List[Dict[str, Any]]:
        """Convierte ApplicationIR endpoints a formato compatible.

        Returns:
            List of endpoint dictionaries with normalized structure
        """
        endpoints = []

        for endpoint in self.app_ir.api_model.endpoints:
            normalized_endpoint = {
                'path': endpoint.path,
                'method': self._normalize_http_method(endpoint.method),
                'operation_id': endpoint.operation_id,
                'summary': endpoint.summary or '',
                'description': endpoint.description or '',
                'parameters': self._normalize_parameters(endpoint.parameters),
                'auth_required': endpoint.auth_required,
                'tags': endpoint.tags or [],
            }

            # Add request schema if exists
            if endpoint.request_schema:
                normalized_endpoint['request_schema'] = {
                    'name': endpoint.request_schema.name,
                    'fields': self._normalize_schema_fields(endpoint.request_schema.fields)
                }

            # Add response schema if exists
            if endpoint.response_schema:
                normalized_endpoint['response_schema'] = {
                    'name': endpoint.response_schema.name,
                    'fields': self._normalize_schema_fields(endpoint.response_schema.fields)
                }

            # Extract entity name from path (e.g., /products -> Product)
            entity_name = self._extract_entity_from_path(endpoint.path)
            if entity_name:
                normalized_endpoint['entity'] = entity_name

            # Determine operation type (CRUD or custom)
            normalized_endpoint['operation'] = self._determine_operation(
                endpoint.method, endpoint.path
            )

            endpoints.append(normalized_endpoint)

        return endpoints

    def _normalize_http_method(self, method: HttpMethod) -> str:
        """Convert HttpMethod enum to string.

        Args:
            method: HttpMethod enum

        Returns:
            String representation of HTTP method
        """
        return self.HTTP_METHOD_MAPPING.get(method, method.value if hasattr(method, 'value') else str(method))

    def _normalize_parameters(self, parameters: List[APIParameter]) -> List[Dict[str, Any]]:
        """Normalize API parameters for templates.

        Args:
            parameters: List of APIParameter objects

        Returns:
            List of normalized parameter dictionaries
        """
        params = []

        for param in parameters:
            params.append({
                'name': param.name,
                'location': param.location.value if hasattr(param.location, 'value') else str(param.location),
                'type': param.data_type,
                'required': param.required,
                'description': param.description or ''
            })

        return params

    def _normalize_schema_fields(self, fields: List[Any]) -> List[Dict[str, Any]]:
        """Normalize schema fields for templates.

        Args:
            fields: List of schema field objects

        Returns:
            List of normalized field dictionaries
        """
        normalized = []

        for field in fields:
            normalized.append({
                'name': field.name,
                'type': field.type,
                'required': field.required,
                'description': field.description or ''
            })

        return normalized

    def _extract_entity_from_path(self, path: str) -> Optional[str]:
        """Extract entity name from API path.

        Args:
            path: API endpoint path (e.g., /products, /api/v1/users)

        Returns:
            Entity name in singular form or None
        """
        # Remove API prefix if present
        clean_path = re.sub(r'^/api/v\d+/', '/', path)

        # Extract the main resource name
        match = re.match(r'^/([a-z_]+)', clean_path)
        if match:
            resource = match.group(1)
            # Convert to singular and capitalize
            return self.singularize(resource.capitalize())

        return None

    def _determine_operation(self, method: HttpMethod, path: str) -> str:
        """Determine CRUD operation type from method and path.

        Args:
            method: HTTP method
            path: API endpoint path

        Returns:
            Operation type (create, list, get, update, delete, custom)
        """
        method_str = self._normalize_http_method(method)

        # Check for ID parameter in path
        has_id = '{id}' in path or '/{id}' in path or bool(re.search(r'/\{[^}]+\}$', path))

        if method_str == 'GET' and not has_id:
            return 'list'
        elif method_str == 'GET' and has_id:
            return 'get'
        elif method_str == 'POST':
            return 'create'
        elif method_str in ['PUT', 'PATCH'] and has_id:
            return 'update'
        elif method_str == 'DELETE' and has_id:
            return 'delete'
        else:
            return 'custom'

    def get_context(self) -> Dict[str, Any]:
        """Retorna contexto completo para templates.

        Returns:
            Complete context dictionary for Jinja2 templates
        """
        context = {
            'app_name': self.app_ir.name,
            'app_id': str(self.app_ir.app_id),
            'entities': self.get_entities(),
            'endpoints': self.get_endpoints(),
            'python_version': '3.11',
            'description': self.app_ir.description or f"{self.app_ir.name} application",
            'version': self.app_ir.version,
            'created_at': self.app_ir.created_at.isoformat() if self.app_ir.created_at else None,
            'updated_at': self.app_ir.updated_at.isoformat() if self.app_ir.updated_at else None,
        }

        # Add infrastructure context if available
        if hasattr(self.app_ir, 'infrastructure_model') and self.app_ir.infrastructure_model:
            context['infrastructure'] = {
                'database': getattr(self.app_ir.infrastructure_model, 'database_config', {}),
                'docker': getattr(self.app_ir.infrastructure_model, 'docker_config', {}),
                'deployment': getattr(self.app_ir.infrastructure_model, 'deployment_config', {})
            }

        # Add behavior model context if available
        if hasattr(self.app_ir, 'behavior_model') and self.app_ir.behavior_model:
            context['behavior'] = {
                'business_rules': getattr(self.app_ir.behavior_model, 'business_rules', []),
                'workflows': getattr(self.app_ir.behavior_model, 'workflows', [])
            }

        # Add validation model context if available
        if hasattr(self.app_ir, 'validation_model') and self.app_ir.validation_model:
            context['validations'] = {
                'rules': getattr(self.app_ir.validation_model, 'validation_rules', []),
                'constraints': getattr(self.app_ir.validation_model, 'constraints', [])
            }

        return context

    def datatype_to_string(self, data_type: DataType) -> str:
        """Convert DataType enum to string representation for templates.

        Args:
            data_type: DataType enum value

        Returns:
            String representation of the data type
        """
        return self.DATATYPE_MAPPING.get(data_type, 'str')

    def pluralize(self, entity_name: str) -> str:
        """Generate plural form of entity name.

        Args:
            entity_name: Singular entity name (e.g., "Product", "Category")

        Returns:
            Plural form (e.g., "Products", "Categories")
        """
        # Handle common irregular plurals
        irregular_plurals = {
            'Person': 'People',
            'Child': 'Children',
            'Foot': 'Feet',
            'Tooth': 'Teeth',
            'Goose': 'Geese',
            'Man': 'Men',
            'Woman': 'Women',
            'Mouse': 'Mice',
            'Ox': 'Oxen'
        }

        if entity_name in irregular_plurals:
            return irregular_plurals[entity_name]

        # Handle words ending in specific patterns
        if entity_name.endswith('y') and len(entity_name) > 1 and entity_name[-2] not in 'aeiou':
            # e.g., Category -> Categories, City -> Cities
            return entity_name[:-1] + 'ies'
        elif entity_name.endswith(('s', 'ss', 'sh', 'ch', 'x', 'z', 'o')):
            # e.g., Class -> Classes, Box -> Boxes, Dish -> Dishes
            return entity_name + 'es'
        elif entity_name.endswith('fe'):
            # e.g., Wife -> Wives
            return entity_name[:-2] + 'ves'
        elif entity_name.endswith('f'):
            # e.g., Wolf -> Wolves
            return entity_name[:-1] + 'ves'
        else:
            # Default: just add 's'
            return entity_name + 's'

    def singularize(self, plural_name: str) -> str:
        """Generate singular form from plural name.

        Args:
            plural_name: Plural entity name (e.g., "products", "categories")

        Returns:
            Singular form (e.g., "Product", "Category")
        """
        # Handle common irregular singulars
        irregular_singulars = {
            'people': 'Person',
            'children': 'Child',
            'feet': 'Foot',
            'teeth': 'Tooth',
            'geese': 'Goose',
            'men': 'Man',
            'women': 'Woman',
            'mice': 'Mouse',
            'oxen': 'Ox'
        }

        lower_plural = plural_name.lower()
        if lower_plural in irregular_singulars:
            return irregular_singulars[lower_plural]

        # Handle words ending in specific patterns
        if plural_name.endswith('ies') and len(plural_name) > 3:
            # e.g., categories -> category
            singular = plural_name[:-3] + 'y'
        elif plural_name.endswith('ves'):
            # e.g., wolves -> wolf, wives -> wife
            if plural_name.endswith('lves'):
                singular = plural_name[:-3] + 'f'
            else:
                singular = plural_name[:-3] + 'fe'
        elif plural_name.endswith('es') and len(plural_name) > 2:
            # Check if it's a special case
            if plural_name.endswith(('sses', 'shes', 'ches', 'xes', 'zes')):
                singular = plural_name[:-2]
            elif plural_name.endswith('oes'):
                singular = plural_name[:-2]
            else:
                singular = plural_name[:-2]
        elif plural_name.endswith('s') and not plural_name.endswith('ss'):
            # e.g., products -> product
            singular = plural_name[:-1]
        else:
            # Return as-is if pattern doesn't match
            singular = plural_name

        # Capitalize first letter
        return singular.capitalize()

    def validate_normalization(self) -> Dict[str, Any]:
        """Validate that normalization produced valid output.

        Returns:
            Validation report with any issues found
        """
        issues = []
        warnings = []

        # Check entities
        entities = self.get_entities()
        if not entities:
            issues.append("No entities found in ApplicationIR")
        else:
            for entity in entities:
                if not entity.get('name'):
                    issues.append(f"Entity missing name: {entity}")
                if not entity.get('fields'):
                    warnings.append(f"Entity {entity.get('name')} has no fields")
                if not entity.get('plural'):
                    issues.append(f"Entity {entity.get('name')} missing plural form")

        # Check endpoints
        endpoints = self.get_endpoints()
        if not endpoints:
            warnings.append("No endpoints found in ApplicationIR")
        else:
            for endpoint in endpoints:
                if not endpoint.get('path'):
                    issues.append(f"Endpoint missing path: {endpoint}")
                if not endpoint.get('method'):
                    issues.append(f"Endpoint missing method: {endpoint}")

        # Check context
        context = self.get_context()
        if not context.get('app_name'):
            issues.append("Missing application name")
        if not context.get('app_id'):
            issues.append("Missing application ID")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'entity_count': len(entities),
            'endpoint_count': len(endpoints)
        }