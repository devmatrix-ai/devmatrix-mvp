"""
OpenAPI 3.0 Specification Generator

Automatically generates OpenAPI 3.0 documentation from ApplicationIR.
"""
from typing import Dict, Any, List, Optional
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DataType
import json


class OpenAPIGenerator:
    """Generates OpenAPI 3.0 specifications from ApplicationIR."""

    def __init__(self, app_ir: ApplicationIR):
        self.app_ir = app_ir

    def generate_spec(self) -> Dict[str, Any]:
        """
        Generate complete OpenAPI 3.0 specification.
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.app_ir.name,
                "description": self.app_ir.description or "",
                "version": self.app_ir.version
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development Server"
                }
            ],
            "paths": self._generate_paths(),
            "components": self._generate_components(),
            "tags": self._generate_tags()
        }

        return spec

    def _generate_paths(self) -> Dict[str, Any]:
        """Generate paths section from API model."""
        paths = {}

        for endpoint in self.app_ir.api_model.endpoints:
            path = endpoint.path
            method = endpoint.http_method.value.lower()

            if path not in paths:
                paths[path] = {}

            # Request body schema
            request_body = None
            if endpoint.request_schema:
                request_body = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{endpoint.request_schema}"
                            }
                        }
                    }
                }

            # Response schemas
            responses = {
                "200": {
                    "description": f"Successfully retrieved {endpoint.summary}",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{endpoint.response_schema}"
                            } if endpoint.response_schema else {}
                        }
                    }
                },
                "400": {
                    "description": "Invalid input",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                },
                "404": {
                    "description": "Resource not found",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                },
                "500": {
                    "description": "Server error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                }
            }

            # Parameters
            parameters = []
            for param in endpoint.parameters:
                param_def = {
                    "name": param.name,
                    "in": param.location.value if hasattr(param.location, 'value') else param.location,
                    "required": param.required,
                    "schema": {
                        "type": self._map_param_type(param.parameter_type or "string")
                    }
                }
                parameters.append(param_def)

            # Operation definition
            operation = {
                "summary": endpoint.summary,
                "description": endpoint.description or endpoint.summary,
                "operationId": f"{endpoint.http_method.value}_{endpoint.path.replace('/', '_')}",
                "tags": [endpoint.tags[0] if endpoint.tags else "default"],
                "parameters": parameters if parameters else None,
                "responses": responses
            }

            if request_body:
                operation["requestBody"] = request_body

            # Add authentication if needed
            if endpoint.requires_auth:
                operation["security"] = [{"bearerAuth": []}]

            # Clean up None values
            operation = {k: v for k, v in operation.items() if v is not None}

            paths[path][method] = operation

        return paths

    def _generate_components(self) -> Dict[str, Any]:
        """Generate components (schemas, security schemes, etc)."""
        components = {
            "schemas": self._generate_schemas(),
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }

        return components

    def _generate_schemas(self) -> Dict[str, Any]:
        """Generate all entity schemas from domain model."""
        schemas = {}

        # Generate schema for each entity
        for entity in self.app_ir.domain_model.entities:
            # Base schema
            properties = {}
            required = []

            for attr in entity.attributes:
                prop_def = {
                    "type": self._map_data_type(attr.data_type),
                    "description": attr.description or f"{attr.name} field"
                }

                # Add constraints
                if attr.data_type == DataType.STRING:
                    prop_def["minLength"] = 1
                    if attr.constraints and "max_length" in attr.constraints:
                        prop_def["maxLength"] = attr.constraints["max_length"]
                elif attr.data_type == DataType.INTEGER:
                    if attr.constraints and "ge" in attr.constraints:
                        prop_def["minimum"] = attr.constraints["ge"]
                    if attr.constraints and "le" in attr.constraints:
                        prop_def["maximum"] = attr.constraints["le"]

                properties[attr.name] = prop_def

                if not attr.is_nullable:
                    required.append(attr.name)

            schemas[f"{entity.name}Base"] = {
                "type": "object",
                "properties": properties,
                "required": required
            }

            # Create, Read, Update, Delete variants
            schemas[f"{entity.name}Create"] = {
                "allOf": [
                    {"$ref": f"#/components/schemas/{entity.name}Base"},
                    {"type": "object", "properties": {}}
                ]
            }

            schemas[f"{entity.name}Response"] = {
                "allOf": [
                    {"$ref": f"#/components/schemas/{entity.name}Base"},
                    {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "format": "uuid",
                                "description": "Entity ID"
                            },
                            "created_at": {
                                "type": "string",
                                "format": "date-time",
                                "description": "Creation timestamp"
                            }
                        },
                        "required": ["id", "created_at"]
                    }
                ]
            }

        # Error response schema
        schemas["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "string",
                    "description": "Error message"
                },
                "status_code": {
                    "type": "integer",
                    "description": "HTTP status code"
                }
            },
            "required": ["detail", "status_code"]
        }

        return schemas

    def _generate_tags(self) -> List[Dict[str, str]]:
        """Generate tag definitions for organizing operations."""
        tags = []
        seen_tags = set()

        for endpoint in self.app_ir.api_model.endpoints:
            for tag in endpoint.tags:
                if tag not in seen_tags:
                    tags.append({
                        "name": tag,
                        "description": f"Operations related to {tag}"
                    })
                    seen_tags.add(tag)

        return tags if tags else [{"name": "default", "description": "Default operations"}]

    def _map_data_type(self, dt: DataType) -> str:
        """Map internal DataType to OpenAPI type."""
        mapping = {
            DataType.STRING: "string",
            DataType.INTEGER: "integer",
            DataType.FLOAT: "number",
            DataType.BOOLEAN: "boolean",
            DataType.DATETIME: "string",  # format: date-time
            DataType.UUID: "string",  # format: uuid
            DataType.JSON: "object",
            DataType.TEXT: "string"
        }
        return mapping.get(dt, "string")

    def _map_param_type(self, param_type: str) -> str:
        """Map parameter type to OpenAPI type."""
        param_type = param_type.lower()
        if "int" in param_type:
            return "integer"
        elif "bool" in param_type:
            return "boolean"
        elif "float" in param_type or "decimal" in param_type:
            return "number"
        elif "uuid" in param_type:
            return "string"
        else:
            return "string"

    def to_json(self) -> str:
        """Export spec as JSON string."""
        return json.dumps(self.generate_spec(), indent=2)

    def to_yaml(self) -> str:
        """Export spec as YAML string."""
        import yaml
        return yaml.dump(self.generate_spec(), default_flow_style=False)

    def save_json(self, filepath: str) -> None:
        """Save spec to JSON file."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())

    def save_yaml(self, filepath: str) -> None:
        """Save spec to YAML file."""
        with open(filepath, 'w') as f:
            f.write(self.to_yaml())
