"""
API Model Graph Repository
---------------------------
Specialized Neo4j repository for persisting and querying APIModelIR with optimized
graph structure for endpoints, schemas, and parameters.

Graph Schema:
- APIModelIR node: Root node for the API model
- Endpoint nodes: API endpoints with HAS_ENDPOINT relationships
- APIParameter nodes: Endpoint parameters with HAS_PARAMETER relationships
- APISchema nodes: Request/response schemas with REQUEST_SCHEMA and RESPONSE_SCHEMA relationships
- APISchemaField nodes: Schema fields with HAS_FIELD relationships

Performance Optimizations:
- UNWIND batching for bulk operations (reduces roundtrips)
- Transaction-based operations for atomicity
- Batch sizes optimized for Neo4j performance
"""

from typing import Dict, Any, List, Optional
import logging
import json

from neo4j import GraphDatabase, Transaction

from src.cognitive.config.settings import settings
from src.cognitive.ir.api_model import (
    APIModelIR,
    Endpoint,
    APIParameter,
    APISchema,
    APISchemaField,
    HttpMethod,
    ParameterLocation,
    InferenceSource,
)

logger = logging.getLogger(__name__)


class APIModelPersistenceError(RuntimeError):
    """Raised when persisting or loading APIModelIR fails."""


class APIModelGraphRepository:
    """
    Repository for APIModelIR graph operations.

    Provides optimized methods for:
    - Saving complete API models with batch operations
    - Loading API models with schema reconstruction
    - Querying endpoints and schemas
    - Managing API lifecycle
    """

    def __init__(self) -> None:
        """Initialize repository with Neo4j driver from settings."""
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            database=settings.neo4j_database,
        )
        logger.info(
            "APIModelGraphRepository initialized with URI %s", settings.neo4j_uri
        )

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("APIModelGraphRepository connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def save_api_model(self, app_id: str, api_model: APIModelIR) -> None:
        """
        Persist complete APIModelIR to Neo4j graph.

        Creates:
        - APIModelIR root node
        - Endpoint nodes with HAS_ENDPOINT relationships
        - APIParameter nodes with HAS_PARAMETER relationships
        - APISchema nodes with HAS_SCHEMA relationships
        - APISchemaField nodes with HAS_FIELD relationships
        - REQUEST_SCHEMA and RESPONSE_SCHEMA edges linking endpoints to schemas

        Args:
            app_id: Application identifier
            api_model: APIModelIR instance to persist

        Raises:
            APIModelPersistenceError: If persistence fails
        """
        try:
            with self.driver.session() as session:
                session.write_transaction(
                    self._tx_save_api_model, app_id, api_model
                )
            logger.info(
                "APIModelIR for app %s persisted successfully with %d endpoints, %d schemas",
                app_id,
                len(api_model.endpoints),
                len(api_model.schemas),
            )
        except Exception as exc:
            logger.exception("Failed to persist APIModelIR for app %s", app_id)
            raise APIModelPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_save_api_model(
        tx: Transaction, app_id: str, api_model: APIModelIR
    ) -> None:
        """
        Transaction function to save APIModelIR with batch operations.

        Args:
            tx: Neo4j transaction
            app_id: Application identifier
            api_model: APIModelIR to persist
        """
        api_model_id = f"{app_id}_api"

        # 1. Create/update APIModelIR root node
        tx.run(
            """
            MERGE (api:APIModelIR {api_model_id: $api_model_id})
            SET api.app_id = $app_id,
                api.base_path = $base_path,
                api.version = $version,
                api.endpoint_count = $endpoint_count,
                api.schema_count = $schema_count,
                api.updated_at = timestamp()
            """,
            {
                "api_model_id": api_model_id,
                "app_id": app_id,
                "base_path": api_model.base_path,
                "version": api_model.version,
                "endpoint_count": len(api_model.endpoints),
                "schema_count": len(api_model.schemas),
            },
        )

        # 2. Batch create Endpoint nodes with HAS_ENDPOINT relationships
        endpoint_batch = []
        for endpoint in api_model.endpoints:
            # Normalize path for ID (remove leading slash and braces)
            path_normalized = endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
            endpoint_id = f"{api_model_id}_{endpoint.method.value}_{path_normalized}"

            endpoint_batch.append(
                {
                    "endpoint_id": endpoint_id,
                    "api_model_id": api_model_id,
                    "path": endpoint.path,
                    "method": endpoint.method.value,
                    "operation_id": endpoint.operation_id,
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "auth_required": endpoint.auth_required,
                    "tags": json.dumps(endpoint.tags),
                    "inferred": endpoint.inferred,
                    "inference_source": endpoint.inference_source.value,
                    "inference_reason": endpoint.inference_reason,
                }
            )

        if endpoint_batch:
            tx.run(
                """
                UNWIND $endpoints AS ep
                MERGE (e:Endpoint {endpoint_id: ep.endpoint_id})
                SET e.api_model_id = ep.api_model_id,
                    e.path = ep.path,
                    e.method = ep.method,
                    e.operation_id = ep.operation_id,
                    e.summary = ep.summary,
                    e.description = ep.description,
                    e.auth_required = ep.auth_required,
                    e.tags = ep.tags,
                    e.inferred = ep.inferred,
                    e.inference_source = ep.inference_source,
                    e.inference_reason = ep.inference_reason,
                    e.updated_at = timestamp()
                WITH e, ep
                MERGE (api:APIModelIR {api_model_id: ep.api_model_id})
                MERGE (api)-[:HAS_ENDPOINT]->(e)
                """,
                {"endpoints": endpoint_batch},
            )

        # 3. Batch create APIParameter nodes with HAS_PARAMETER relationships
        parameter_batch = []
        for endpoint in api_model.endpoints:
            path_normalized = endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
            endpoint_id = f"{api_model_id}_{endpoint.method.value}_{path_normalized}"

            for param in endpoint.parameters:
                parameter_id = f"{endpoint_id}_{param.name}"
                parameter_batch.append(
                    {
                        "parameter_id": parameter_id,
                        "endpoint_id": endpoint_id,
                        "name": param.name,
                        "location": param.location.value,
                        "data_type": param.data_type,
                        "required": param.required,
                        "description": param.description,
                    }
                )

        if parameter_batch:
            tx.run(
                """
                UNWIND $parameters AS param
                MERGE (p:APIParameter {parameter_id: param.parameter_id})
                SET p.endpoint_id = param.endpoint_id,
                    p.name = param.name,
                    p.location = param.location,
                    p.data_type = param.data_type,
                    p.required = param.required,
                    p.description = param.description,
                    p.updated_at = timestamp()
                WITH p, param
                MERGE (e:Endpoint {endpoint_id: param.endpoint_id})
                MERGE (e)-[:HAS_PARAMETER]->(p)
                """,
                {"parameters": parameter_batch},
            )

        # 4. Batch create APISchema nodes with HAS_SCHEMA relationships
        schema_batch = []
        for schema in api_model.schemas:
            schema_id = f"{api_model_id}_schema_{schema.name}"
            schema_batch.append(
                {
                    "schema_id": schema_id,
                    "api_model_id": api_model_id,
                    "name": schema.name,
                    "field_count": len(schema.fields),
                }
            )

        if schema_batch:
            tx.run(
                """
                UNWIND $schemas AS s
                MERGE (schema:APISchema {schema_id: s.schema_id})
                SET schema.api_model_id = s.api_model_id,
                    schema.name = s.name,
                    schema.field_count = s.field_count,
                    schema.updated_at = timestamp()
                WITH schema, s
                MERGE (api:APIModelIR {api_model_id: s.api_model_id})
                MERGE (api)-[:HAS_SCHEMA]->(schema)
                """,
                {"schemas": schema_batch},
            )

        # 5. Batch create APISchemaField nodes with HAS_FIELD relationships
        field_batch = []
        for schema in api_model.schemas:
            schema_id = f"{api_model_id}_schema_{schema.name}"
            for field in schema.fields:
                field_id = f"{schema_id}_{field.name}"
                field_batch.append(
                    {
                        "field_id": field_id,
                        "schema_id": schema_id,
                        "name": field.name,
                        "type": field.type,
                        "required": field.required,
                        "description": field.description,
                    }
                )

        if field_batch:
            tx.run(
                """
                UNWIND $fields AS f
                MERGE (field:APISchemaField {field_id: f.field_id})
                SET field.schema_id = f.schema_id,
                    field.name = f.name,
                    field.type = f.type,
                    field.required = f.required,
                    field.description = f.description,
                    field.updated_at = timestamp()
                WITH field, f
                MERGE (schema:APISchema {schema_id: f.schema_id})
                MERGE (schema)-[:HAS_FIELD]->(field)
                """,
                {"fields": field_batch},
            )

        # 6. Create REQUEST_SCHEMA and RESPONSE_SCHEMA relationships
        schema_link_batch = []
        for endpoint in api_model.endpoints:
            path_normalized = endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
            endpoint_id = f"{api_model_id}_{endpoint.method.value}_{path_normalized}"

            if endpoint.request_schema:
                schema_link_batch.append(
                    {
                        "endpoint_id": endpoint_id,
                        "schema_name": endpoint.request_schema.name,
                        "relationship_type": "REQUEST_SCHEMA",
                    }
                )

            if endpoint.response_schema:
                schema_link_batch.append(
                    {
                        "endpoint_id": endpoint_id,
                        "schema_name": endpoint.response_schema.name,
                        "relationship_type": "RESPONSE_SCHEMA",
                    }
                )

        # Separate batches for REQUEST_SCHEMA and RESPONSE_SCHEMA
        request_schemas = [
            link for link in schema_link_batch if link["relationship_type"] == "REQUEST_SCHEMA"
        ]
        response_schemas = [
            link for link in schema_link_batch if link["relationship_type"] == "RESPONSE_SCHEMA"
        ]

        if request_schemas:
            tx.run(
                """
                UNWIND $links AS link
                MATCH (e:Endpoint {endpoint_id: link.endpoint_id})
                MATCH (s:APISchema {api_model_id: $api_model_id, name: link.schema_name})
                MERGE (e)-[:REQUEST_SCHEMA]->(s)
                """,
                {"links": request_schemas, "api_model_id": api_model_id},
            )

        if response_schemas:
            tx.run(
                """
                UNWIND $links AS link
                MATCH (e:Endpoint {endpoint_id: link.endpoint_id})
                MATCH (s:APISchema {api_model_id: $api_model_id, name: link.schema_name})
                MERGE (e)-[:RESPONSE_SCHEMA]->(s)
                """,
                {"links": response_schemas, "api_model_id": api_model_id},
            )

        logger.info(
            "Persisted %d endpoints, %d parameters, %d schemas, %d fields for app %s",
            len(endpoint_batch),
            len(parameter_batch),
            len(schema_batch),
            len(field_batch),
            app_id,
        )

    def load_api_model(self, app_id: str) -> APIModelIR:
        """
        Load APIModelIR from Neo4j graph by app_id.

        Reconstructs complete API model including:
        - All endpoints with parameters
        - All schemas with fields
        - Request/response schema relationships

        Args:
            app_id: Application identifier

        Returns:
            Reconstructed APIModelIR instance

        Raises:
            APIModelPersistenceError: If loading fails or model not found
        """
        try:
            with self.driver.session() as session:
                api_model = session.read_transaction(
                    self._tx_load_api_model, app_id
                )
            logger.info(
                "APIModelIR for app %s loaded successfully with %d endpoints",
                app_id,
                len(api_model.endpoints),
            )
            return api_model
        except Exception as exc:
            logger.exception("Failed to load APIModelIR for app %s", app_id)
            raise APIModelPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_load_api_model(tx: Transaction, app_id: str) -> APIModelIR:
        """
        Transaction function to load APIModelIR from graph.

        Args:
            tx: Neo4j transaction
            app_id: Application identifier

        Returns:
            Reconstructed APIModelIR

        Raises:
            APIModelPersistenceError: If model not found
        """
        api_model_id = f"{app_id}_api"

        # 1. Load APIModelIR root node
        result = tx.run(
            """
            MATCH (api:APIModelIR {api_model_id: $api_model_id})
            RETURN api.base_path AS base_path,
                   api.version AS version
            """,
            {"api_model_id": api_model_id},
        )
        record = result.single()
        if not record:
            raise APIModelPersistenceError(
                f"APIModelIR not found for app_id: {app_id}"
            )

        base_path = record["base_path"]
        version = record["version"]

        # 2. Load all endpoints with their parameters
        result = tx.run(
            """
            MATCH (api:APIModelIR {api_model_id: $api_model_id})-[:HAS_ENDPOINT]->(e:Endpoint)
            OPTIONAL MATCH (e)-[:HAS_PARAMETER]->(p:APIParameter)
            OPTIONAL MATCH (e)-[:REQUEST_SCHEMA]->(req:APISchema)
            OPTIONAL MATCH (e)-[:RESPONSE_SCHEMA]->(res:APISchema)
            RETURN e.endpoint_id AS endpoint_id,
                   e.path AS path,
                   e.method AS method,
                   e.operation_id AS operation_id,
                   e.summary AS summary,
                   e.description AS description,
                   e.auth_required AS auth_required,
                   e.tags AS tags,
                   e.inferred AS inferred,
                   e.inference_source AS inference_source,
                   e.inference_reason AS inference_reason,
                   collect(DISTINCT {
                       name: p.name,
                       location: p.location,
                       data_type: p.data_type,
                       required: p.required,
                       description: p.description
                   }) AS parameters,
                   req.name AS request_schema_name,
                   res.name AS response_schema_name
            ORDER BY e.path, e.method
            """,
            {"api_model_id": api_model_id},
        )

        endpoints = []
        schema_names = set()

        for record in result:
            # Parse parameters
            parameters = []
            for param_dict in record["parameters"]:
                if param_dict["name"]:  # Skip empty entries from collect
                    parameters.append(
                        APIParameter(
                            name=param_dict["name"],
                            location=ParameterLocation(param_dict["location"]),
                            data_type=param_dict["data_type"],
                            required=param_dict["required"],
                            description=param_dict["description"],
                        )
                    )

            # Track schema names for later loading
            if record["request_schema_name"]:
                schema_names.add(record["request_schema_name"])
            if record["response_schema_name"]:
                schema_names.add(record["response_schema_name"])

            endpoints.append(
                Endpoint(
                    path=record["path"],
                    method=HttpMethod(record["method"]),
                    operation_id=record["operation_id"],
                    summary=record["summary"],
                    description=record["description"],
                    parameters=parameters,
                    request_schema=None,  # Will be populated after loading schemas
                    response_schema=None,  # Will be populated after loading schemas
                    auth_required=record["auth_required"],
                    tags=json.loads(record["tags"]) if record["tags"] else [],
                    inferred=record["inferred"],
                    inference_source=InferenceSource(record["inference_source"]),
                    inference_reason=record["inference_reason"],
                )
            )

        # 3. Load all schemas with their fields
        result = tx.run(
            """
            MATCH (api:APIModelIR {api_model_id: $api_model_id})-[:HAS_SCHEMA]->(s:APISchema)
            OPTIONAL MATCH (s)-[:HAS_FIELD]->(f:APISchemaField)
            RETURN s.name AS schema_name,
                   collect({
                       name: f.name,
                       type: f.type,
                       required: f.required,
                       description: f.description
                   }) AS fields
            ORDER BY s.name
            """,
            {"api_model_id": api_model_id},
        )

        schemas = []
        schema_map = {}

        for record in result:
            # Parse fields
            fields = []
            for field_dict in record["fields"]:
                if field_dict["name"]:  # Skip empty entries from collect
                    fields.append(
                        APISchemaField(
                            name=field_dict["name"],
                            type=field_dict["type"],
                            required=field_dict["required"],
                            description=field_dict["description"],
                        )
                    )

            schema = APISchema(
                name=record["schema_name"],
                fields=fields,
            )
            schemas.append(schema)
            schema_map[schema.name] = schema

        # 4. Link schemas to endpoints (reload endpoint-schema relationships)
        result = tx.run(
            """
            MATCH (api:APIModelIR {api_model_id: $api_model_id})-[:HAS_ENDPOINT]->(e:Endpoint)
            OPTIONAL MATCH (e)-[:REQUEST_SCHEMA]->(req:APISchema)
            OPTIONAL MATCH (e)-[:RESPONSE_SCHEMA]->(res:APISchema)
            RETURN e.endpoint_id AS endpoint_id,
                   req.name AS request_schema_name,
                   res.name AS response_schema_name
            """,
            {"api_model_id": api_model_id},
        )

        endpoint_schemas = {}
        for record in result:
            endpoint_schemas[record["endpoint_id"]] = {
                "request": record["request_schema_name"],
                "response": record["response_schema_name"],
            }

        # 5. Populate request/response schemas in endpoints
        for endpoint in endpoints:
            path_normalized = endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
            endpoint_id = f"{api_model_id}_{endpoint.method.value}_{path_normalized}"

            if endpoint_id in endpoint_schemas:
                req_name = endpoint_schemas[endpoint_id]["request"]
                res_name = endpoint_schemas[endpoint_id]["response"]

                if req_name and req_name in schema_map:
                    endpoint.request_schema = schema_map[req_name]
                if res_name and res_name in schema_map:
                    endpoint.response_schema = schema_map[res_name]

        return APIModelIR(
            endpoints=endpoints,
            schemas=schemas,
            base_path=base_path,
            version=version,
        )
