"""
Phase 3.5: Spec to ApplicationIR Converter.

Converts spec markdown to ApplicationIR using LLM.
Runs ONCE per spec, result is cached as JSON for 100% deterministic subsequent runs.

This is the GROUND TRUTH for validation:
- SPEC → ApplicationIR (LLM, cached)
- ApplicationIR → ValidationModelIR (deterministic)
- Code → ValidationModelIR (Phase 2)
- Compare IR vs IR (Phase 3)
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Any
from datetime import datetime
import uuid

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    DataType,
    Relationship,
    RelationshipType,
)
from src.cognitive.ir.api_model import (
    APIModelIR,
    Endpoint,
    HttpMethod,
    APISchema,
    APISchemaField,
    APIParameter,
    ParameterLocation,
)
from src.cognitive.ir.infrastructure_model import (
    InfrastructureModelIR,
    DatabaseConfig,
    DatabaseType,
    ObservabilityConfig,
)
from src.cognitive.ir.behavior_model import BehaviorModelIR, Flow, FlowType, Step, Invariant
from src.cognitive.ir.validation_model import (
    ValidationType,
    EnforcementType,
    ValidationRule,
    ValidationModelIR,
)

logger = logging.getLogger(__name__)


class SpecToApplicationIR:
    """
    Convert spec markdown to ApplicationIR using LLM.

    This is a ONE-TIME operation that runs when:
    1. Spec changes (detected via hash)
    2. No cached ApplicationIR exists
    3. Force refresh requested

    Result is cached as JSON for 100% deterministic subsequent runs.

    Usage:
        converter = SpecToApplicationIR()
        app_ir = await converter.get_application_ir(spec_markdown, "ecommerce-spec.md")

        # Second call uses cache (0 LLM calls)
        app_ir = await converter.get_application_ir(spec_markdown, "ecommerce-spec.md")
    """

    CACHE_DIR = Path(".devmatrix/ir_cache")
    LLM_MODEL = "claude-sonnet-4-5-20250929"  # Sonnet 4.5 - balanced speed/quality for spec extraction

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the converter."""
        if ANTHROPIC_AVAILABLE:
            self.client = AsyncAnthropic()
        else:
            self.client = None
            logger.warning("Anthropic not available - LLM extraction disabled")

        self.CACHE_DIR = cache_dir or self.CACHE_DIR
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def get_application_ir(
        self,
        spec_markdown: str,
        spec_path: str = "spec.md",
        force_refresh: bool = False
    ) -> ApplicationIR:
        """
        Get ApplicationIR for spec, using cache if available.

        Args:
            spec_markdown: Raw markdown content of specification
            spec_path: Path to spec file (for cache key and naming)
            force_refresh: Force regeneration even if cached

        Returns:
            ApplicationIR representing the spec
        """
        spec_hash = self._hash_spec(spec_markdown)
        cache_path = self.CACHE_DIR / f"{Path(spec_path).stem}_{spec_hash[:8]}.json"

        # Check cache first
        if not force_refresh and cache_path.exists():
            logger.info(f"📦 Loading cached ApplicationIR from {cache_path}")
            return self._load_from_cache(cache_path)

        # Generate with LLM
        logger.info(f"🤖 Generating ApplicationIR with LLM for {spec_path}")
        application_ir = await self._generate_with_llm(spec_markdown, spec_path)

        # Cache for future use
        self._save_to_cache(application_ir, cache_path, spec_hash, spec_path)
        logger.info(f"💾 Cached ApplicationIR to {cache_path}")

        return application_ir

    async def _generate_with_llm(
        self,
        spec_markdown: str,
        spec_path: str
    ) -> ApplicationIR:
        """Generate ApplicationIR from spec using LLM."""
        if not self.client:
            raise RuntimeError("Anthropic client not available - set ANTHROPIC_API_KEY")

        prompt = self._build_extraction_prompt(spec_markdown)

        try:
            # Always use streaming (SDK enforces it for potentially long operations)
            logger.info(f"📡 Streaming IR extraction from {spec_path}")
            response_text = await self._generate_with_streaming(prompt)
        except Exception as e:
            logger.error(f"❌ LLM extraction failed: {e}")
            raise RuntimeError(f"Failed to generate ApplicationIR from spec: {e}")

        try:
            json_str = self._extract_json(response_text)
            ir_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}\nResponse: {response_text[:200]}")
            raise RuntimeError(f"Invalid JSON response from LLM: {e}")
        except (IndexError, AttributeError) as e:
            logger.error(f"❌ Response parsing failed: {e}")
            raise RuntimeError(f"Invalid response structure from LLM: {e}")

        return self._build_application_ir(ir_data, spec_path)

    def _build_extraction_prompt(self, spec_markdown: str) -> str:
        """Build the LLM prompt for comprehensive spec extraction."""
        return f"""Extract ALL information from this API specification to create a complete ApplicationIR.

Be EXHAUSTIVE. Extract every entity, field, constraint, endpoint, and validation rule.

Output ONLY valid JSON in this EXACT format:

{{
  "app_name": "Application Name",
  "app_description": "Description",

  "entities": [
    {{
      "name": "EntityName",
      "description": "Entity description",
      "is_aggregate_root": true,
      "attributes": [
        {{
          "name": "fieldName",
          "data_type": "string|integer|float|boolean|datetime|UUID|json|enum",
          "is_primary_key": false,
          "is_nullable": false,
          "is_unique": false,
          "default_value": null,
          "description": "Field description",
          "constraints": {{
            "min_length": null,
            "max_length": null,
            "min_value": null,
            "max_value": null,
            "pattern": null,
            "enum_values": null,
            "format": null
          }}
        }}
      ],
      "relationships": [
        {{
          "target_entity": "OtherEntity",
          "type": "one_to_many|many_to_one|one_to_one|many_to_many",
          "field_name": "related_field_name",
          "back_populates": "parent_field_name"
        }}
      ]
    }}
  ],

  "endpoints": [
    {{
      "path": "/entities",
      "method": "GET|POST|PUT|DELETE|PATCH",
      "operation_id": "list_entities",
      "summary": "List all entities",
      "description": "Returns paginated list",
      "auth_required": true,
      "tags": ["entities"],
      "parameters": [
        {{
          "name": "skip",
          "location": "query|path|header",
          "data_type": "integer",
          "required": false,
          "description": "Pagination offset"
        }}
      ],
      "request_schema": {{
        "name": "EntityCreate",
        "fields": [
          {{"name": "field1", "type": "string", "required": true}}
        ]
      }},
      "response_schema": {{
        "name": "EntityResponse",
        "fields": [
          {{"name": "id", "type": "UUID", "required": true}}
        ]
      }}
    }}
  ],

  "validation_rules": [
    {{
      "entity": "EntityName",
      "attribute": "fieldName",
      "type": "FORMAT|RANGE|PRESENCE|UNIQUENESS|RELATIONSHIP|STATUS_TRANSITION|STOCK_CONSTRAINT|WORKFLOW_CONSTRAINT|CUSTOM",
      "condition": "description of the constraint",
      "error_message": "Custom error message if specified"
    }}
  ],

  "flows": [
    {{
      "name": "Flow Name from spec",
      "type": "workflow|state_transition|policy|event_handler",
      "trigger": "What triggers this flow",
      "description": "Description of the flow from spec",
      "target_entities": ["Entity1", "Entity2"],
      "steps": [
        {{
          "order": 1,
          "description": "Step description",
          "action": "validate|create|update|delete|calculate",
          "target_entity": "EntityName",
          "condition": "Optional condition for this step"
        }}
      ],
      "preconditions": ["Flow that must happen before this one"],
      "postconditions": ["State after flow completes"]
    }}
  ],

  "entity_dependencies": [
    {{
      "from_entity": "SourceEntity",
      "to_entity": "TargetEntity",
      "dependency_type": "requires|uses|creates"
    }}
  ],

  "database": {{
    "type": "postgresql",
    "name": "app_db"
  }}
}}

VALIDATION TYPE MAPPING:
- Email validation → FORMAT (condition: "valid email")
- Min/max length → FORMAT (condition: "length between X and Y")
- Min/max value, positive, > 0 → RANGE (condition: "> 0", "between X and Y")
- Required/not null → PRESENCE
- Unique → UNIQUENESS
- Foreign key → RELATIONSHIP
- Status/state enums → STATUS_TRANSITION
- Resource availability constraints → STOCK_CONSTRAINT
- Workflow sequences → WORKFLOW_CONSTRAINT
- Other business rules → CUSTOM

FLOW TYPE MAPPING:
- Multi-step processes (any sequential operations) → workflow
- State changes (status field transitions) → state_transition
- Business rules that must always hold → policy
- Triggered by external events → event_handler

FLOW EXTRACTION INSTRUCTIONS:
- Look for "Flujos Principales", "Use Cases", "Flows", "Casos de Uso", "Workflows" sections
- Each numbered flow (F1, F2, etc.) or use case should become a flow entry
- target_entities: ALL entities this flow reads or modifies
- steps: Break down the flow into atomic actions
- preconditions: Flows that must happen before this one (based on spec dependencies)

ENTITY DEPENDENCY EXTRACTION:
- "EntityA requires EntityB" → from_entity: EntityA, to_entity: EntityB, dependency_type: requires
- "FlowX uses EntityC" → from_entity: FlowX, to_entity: EntityC, dependency_type: uses
- "FlowY creates EntityD" → from_entity: FlowY, to_entity: EntityD, dependency_type: creates

IMPORTANT:
1. Extract ALL constraints, even implicit ones (e.g., numeric fields often imply ≥ 0)
2. Include CRUD endpoints for each entity
3. Include relationship endpoints (e.g., /parent/{{id}}/children)
4. Be thorough with validation rules
5. Extract ALL flows from the spec, including CRUD operations as simple flows
6. Extract entity dependencies from relationships and flow descriptions

SPECIFICATION:
{spec_markdown}

Output JSON only, no explanation:"""

    async def _generate_with_streaming(self, prompt: str) -> str:
        """Stream LLM response for large specs to avoid 10-min timeout."""
        response_text = ""

        try:
            async with self.client.messages.stream(
                model=self.LLM_MODEL,
                max_tokens=32000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            ) as stream:
                async for text in stream.text_stream:
                    response_text += text
                    if len(response_text) % 10000 == 0:
                        logger.debug(f"  📊 Streamed {len(response_text)} chars...")
        except Exception as e:
            logger.error(f"❌ Streaming failed: {e}")
            raise

        logger.info(f"✅ Streaming complete: {len(response_text)} chars")
        return response_text

    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try ```json block
        if "```json" in response:
            start = response.index("```json") + 7
            try:
                end = response.index("```", start)
                return response[start:end].strip()
            except ValueError:
                # No closing ```, take rest of response
                return response[start:].strip()

        # Try plain ``` block
        if "```" in response:
            start = response.index("```") + 3
            try:
                end = response.index("```", start)
                return response[start:end].strip()
            except ValueError:
                return response[start:].strip()

        # Try to find JSON object directly
        if "{" in response:
            start = response.index("{")
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(response[start:], start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return response[start:i+1].strip()

        return response.strip()

    def _build_application_ir(self, ir_data: dict, spec_path: str) -> ApplicationIR:
        """Convert parsed JSON to ApplicationIR object."""
        # Build DomainModelIR
        entities = []
        for entity_data in ir_data.get("entities", []):
            attributes = []
            for attr_data in entity_data.get("attributes", []):
                attr = Attribute(
                    name=attr_data["name"],
                    data_type=self._parse_data_type(attr_data.get("data_type", "string")),
                    is_primary_key=attr_data.get("is_primary_key", False),
                    is_nullable=attr_data.get("is_nullable", False),
                    is_unique=attr_data.get("is_unique", False),
                    default_value=attr_data.get("default_value"),
                    description=attr_data.get("description"),
                    constraints=attr_data.get("constraints", {}),
                )
                attributes.append(attr)

            relationships = []
            for rel_data in entity_data.get("relationships", []):
                rel = Relationship(
                    source_entity=entity_data["name"],
                    target_entity=rel_data["target_entity"],
                    type=self._parse_relationship_type(rel_data.get("type", "many_to_one")),
                    field_name=rel_data.get("field_name", rel_data["target_entity"].lower()),
                    back_populates=rel_data.get("back_populates"),
                )
                relationships.append(rel)

            entity = Entity(
                name=entity_data["name"],
                attributes=attributes,
                relationships=relationships,
                description=entity_data.get("description"),
                is_aggregate_root=entity_data.get("is_aggregate_root", False),
            )
            entities.append(entity)

        domain_model = DomainModelIR(entities=entities)

        # Build APIModelIR
        endpoints = []
        schemas = []
        for ep_data in ir_data.get("endpoints", []):
            parameters = []
            for param_data in ep_data.get("parameters", []):
                param = APIParameter(
                    name=param_data["name"],
                    location=self._parse_parameter_location(param_data.get("location", "query")),
                    data_type=param_data.get("data_type", "string"),
                    required=param_data.get("required", False),
                    description=param_data.get("description"),
                )
                parameters.append(param)

            request_schema = None
            if ep_data.get("request_schema"):
                req_schema_data = ep_data["request_schema"]
                request_schema = APISchema(
                    name=req_schema_data["name"],
                    fields=[
                        APISchemaField(
                            name=f["name"],
                            type=f["type"],
                            required=f.get("required", True),
                            description=f.get("description"),
                        )
                        for f in req_schema_data.get("fields", [])
                    ]
                )
                schemas.append(request_schema)

            response_schema = None
            if ep_data.get("response_schema"):
                resp_schema_data = ep_data["response_schema"]
                response_schema = APISchema(
                    name=resp_schema_data["name"],
                    fields=[
                        APISchemaField(
                            name=f["name"],
                            type=f["type"],
                            required=f.get("required", True),
                            description=f.get("description"),
                        )
                        for f in resp_schema_data.get("fields", [])
                    ]
                )
                schemas.append(response_schema)

            endpoint = Endpoint(
                path=ep_data["path"],
                method=self._parse_http_method(ep_data.get("method", "GET")),
                operation_id=ep_data.get("operation_id", ep_data["path"].replace("/", "_")),
                summary=ep_data.get("summary"),
                description=ep_data.get("description"),
                parameters=parameters,
                request_schema=request_schema,
                response_schema=response_schema,
                auth_required=ep_data.get("auth_required", True),
                tags=ep_data.get("tags", []),
            )
            endpoints.append(endpoint)

        api_model = APIModelIR(endpoints=endpoints, schemas=schemas)

        # Build InfrastructureModelIR
        db_data = ir_data.get("database", {"type": "postgresql", "name": "app_db"})
        db_type = self._parse_database_type(db_data.get("type", "postgresql"))
        db_name = db_data.get("name", "app_db")
        db_user = db_data.get("user", f"{db_name}_user")  # app_db → app_db_user
        db_port = db_data.get("port", 5432 if db_type == DatabaseType.POSTGRESQL else 3306)

        infrastructure_model = InfrastructureModelIR(
            database=DatabaseConfig(
                type=db_type,
                host=db_data.get("host", "localhost"),
                port=db_port,
                name=db_name,
                user=db_user,
                password_env_var=db_data.get("password_env_var", f"{db_name.upper()}_PASSWORD"),
            )
        )

        # Build ValidationModelIR
        validation_rules = []
        for rule_data in ir_data.get("validation_rules", []):
            rule = ValidationRule(
                entity=rule_data.get("entity", ""),
                attribute=rule_data.get("attribute", ""),
                type=self._parse_validation_type(rule_data.get("type", "CUSTOM")),
                condition=rule_data.get("condition"),
                error_message=rule_data.get("error_message"),
                enforcement_type=EnforcementType.DESCRIPTION,  # Spec = intent only
            )
            validation_rules.append(rule)

        # Also extract implicit validation rules from entity constraints
        for entity in entities:
            for attr in entity.attributes:
                implicit_rules = self._extract_implicit_rules(entity.name, attr)
                validation_rules.extend(implicit_rules)

        validation_model = ValidationModelIR(rules=validation_rules)

        # Build BehaviorModelIR from extracted flows
        behavior_model = self._build_behavior_model(ir_data)

        # Build ApplicationIR
        app_name = ir_data.get("app_name", Path(spec_path).stem)

        return ApplicationIR(
            name=app_name,
            description=ir_data.get("app_description", f"Generated from {spec_path}"),
            domain_model=domain_model,
            api_model=api_model,
            infrastructure_model=infrastructure_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            phase_status={"spec_extraction": "complete"},
        )

    def _build_behavior_model(self, ir_data: dict) -> BehaviorModelIR:
        """Build BehaviorModelIR from extracted flows and entity dependencies."""
        flows = []
        invariants = []

        # Process flows from LLM extraction
        for flow_data in ir_data.get("flows", []):
            steps = []
            for step_data in flow_data.get("steps", []):
                step = Step(
                    order=step_data.get("order", 0),
                    description=step_data.get("description", ""),
                    action=step_data.get("action", ""),
                    target_entity=step_data.get("target_entity"),
                    condition=step_data.get("condition"),
                )
                steps.append(step)

            flow = Flow(
                name=flow_data.get("name", "Unknown"),
                type=self._parse_flow_type(flow_data.get("type", "workflow")),
                trigger=flow_data.get("trigger", ""),
                steps=steps,
                description=flow_data.get("description"),
            )
            flows.append(flow)

        # Process entity dependencies as invariants
        for dep_data in ir_data.get("entity_dependencies", []):
            invariant = Invariant(
                entity=dep_data.get("from_entity", ""),
                description=f"{dep_data.get('from_entity')} {dep_data.get('dependency_type', 'requires')} {dep_data.get('to_entity')}",
                enforcement_level="strict",
            )
            invariants.append(invariant)

        return BehaviorModelIR(flows=flows, invariants=invariants)

    def _parse_flow_type(self, type_str: str) -> FlowType:
        """Parse flow type string to enum."""
        type_map = {
            "workflow": FlowType.WORKFLOW,
            "state_transition": FlowType.STATE_TRANSITION,
            "policy": FlowType.POLICY,
            "event_handler": FlowType.EVENT_HANDLER,
        }
        return type_map.get(type_str.lower(), FlowType.WORKFLOW)

    def _extract_implicit_rules(self, entity_name: str, attr: Attribute) -> list[ValidationRule]:
        """Extract implicit validation rules from attribute constraints."""
        rules = []
        constraints = attr.constraints or {}

        # Required/presence
        if not attr.is_nullable:
            rules.append(ValidationRule(
                entity=entity_name,
                attribute=attr.name,
                type=ValidationType.PRESENCE,
                condition="required",
                enforcement_type=EnforcementType.DESCRIPTION,
            ))

        # Uniqueness
        if attr.is_unique:
            rules.append(ValidationRule(
                entity=entity_name,
                attribute=attr.name,
                type=ValidationType.UNIQUENESS,
                condition="unique",
                enforcement_type=EnforcementType.DESCRIPTION,
            ))

        # Range constraints
        min_val = constraints.get("min_value")
        max_val = constraints.get("max_value")
        if min_val is not None or max_val is not None:
            parts = []
            if min_val is not None:
                parts.append(f">= {min_val}")
            if max_val is not None:
                parts.append(f"<= {max_val}")

            condition = ", ".join(parts)
            if condition:  # Only add if we have actual constraints
                rules.append(ValidationRule(
                    entity=entity_name,
                    attribute=attr.name,
                    type=ValidationType.RANGE,
                    condition=condition,
                    enforcement_type=EnforcementType.DESCRIPTION,
                ))

        # Format constraints (pattern or format string)
        format_cond = constraints.get("format") or constraints.get("pattern")
        if format_cond:
            rules.append(ValidationRule(
                entity=entity_name,
                attribute=attr.name,
                type=ValidationType.FORMAT,
                condition=format_cond,
                enforcement_type=EnforcementType.DESCRIPTION,
            ))

        # Length constraints (also FORMAT)
        min_len = constraints.get("min_length")
        max_len = constraints.get("max_length")
        if min_len is not None or max_len is not None:
            parts = []
            if min_len is not None:
                parts.append(f"length >= {min_len}")
            if max_len is not None:
                parts.append(f"length <= {max_len}")

            condition = ", ".join(parts)
            if condition:  # Only add if we have actual constraints
                rules.append(ValidationRule(
                    entity=entity_name,
                    attribute=attr.name,
                    type=ValidationType.FORMAT,
                    condition=condition,
                    enforcement_type=EnforcementType.DESCRIPTION,
                ))

        # Enum constraints
        enum_vals = constraints.get("enum_values")
        if enum_vals:
            # Convert list to readable format
            if isinstance(enum_vals, list):
                enum_str = ", ".join(str(v) for v in enum_vals)
            else:
                enum_str = str(enum_vals)

            rules.append(ValidationRule(
                entity=entity_name,
                attribute=attr.name,
                type=ValidationType.STATUS_TRANSITION,
                condition=f"one of: {enum_str}",
                enforcement_type=EnforcementType.DESCRIPTION,
            ))

        return rules

    def _parse_data_type(self, type_str: str) -> DataType:
        """Parse data type string to enum."""
        type_map = {
            "string": DataType.STRING,
            "integer": DataType.INTEGER,
            "int": DataType.INTEGER,
            "float": DataType.FLOAT,
            "decimal": DataType.FLOAT,
            "boolean": DataType.BOOLEAN,
            "bool": DataType.BOOLEAN,
            "datetime": DataType.DATETIME,
            "date": DataType.DATETIME,
            "uuid": DataType.UUID,
            "json": DataType.JSON,
            "enum": DataType.ENUM,
        }
        return type_map.get(type_str.lower(), DataType.STRING)

    def _parse_relationship_type(self, type_str: str) -> RelationshipType:
        """Parse relationship type string to enum."""
        type_map = {
            "one_to_one": RelationshipType.ONE_TO_ONE,
            "one_to_many": RelationshipType.ONE_TO_MANY,
            "many_to_one": RelationshipType.MANY_TO_ONE,
            "many_to_many": RelationshipType.MANY_TO_MANY,
        }
        return type_map.get(type_str.lower(), RelationshipType.MANY_TO_ONE)

    def _parse_http_method(self, method_str: str) -> HttpMethod:
        """Parse HTTP method string to enum."""
        method_map = {
            "GET": HttpMethod.GET,
            "POST": HttpMethod.POST,
            "PUT": HttpMethod.PUT,
            "DELETE": HttpMethod.DELETE,
            "PATCH": HttpMethod.PATCH,
        }
        return method_map.get(method_str.upper(), HttpMethod.GET)

    def _parse_parameter_location(self, location_str: str) -> ParameterLocation:
        """Parse parameter location string to enum."""
        loc_map = {
            "query": ParameterLocation.QUERY,
            "path": ParameterLocation.PATH,
            "header": ParameterLocation.HEADER,
            "cookie": ParameterLocation.COOKIE,
        }
        return loc_map.get(location_str.lower(), ParameterLocation.QUERY)

    def _parse_database_type(self, type_str: str) -> DatabaseType:
        """Parse database type string to enum."""
        type_map = {
            "postgresql": DatabaseType.POSTGRESQL,
            "postgres": DatabaseType.POSTGRESQL,
            "mysql": DatabaseType.MYSQL,
            "sqlite": DatabaseType.SQLITE,
            "mongodb": DatabaseType.MONGODB,
            "neo4j": DatabaseType.NEO4J,
        }
        return type_map.get(type_str.lower(), DatabaseType.POSTGRESQL)

    def _parse_validation_type(self, type_str: str) -> ValidationType:
        """Parse validation type string to Phase 4 enum."""
        type_map = {
            "FORMAT": ValidationType.FORMAT,
            "RANGE": ValidationType.RANGE,
            "PRESENCE": ValidationType.PRESENCE,
            "UNIQUENESS": ValidationType.UNIQUENESS,
            "RELATIONSHIP": ValidationType.RELATIONSHIP,
            "STATUS_TRANSITION": ValidationType.STATUS_TRANSITION,
            "STOCK_CONSTRAINT": ValidationType.STOCK_CONSTRAINT,
            "WORKFLOW_CONSTRAINT": ValidationType.WORKFLOW_CONSTRAINT,
            "CUSTOM": ValidationType.CUSTOM,
        }
        return type_map.get(type_str.upper(), ValidationType.CUSTOM)

    def _hash_spec(self, spec_markdown: str) -> str:
        """Generate hash of spec content for cache invalidation."""
        return hashlib.sha256(spec_markdown.encode()).hexdigest()

    def _load_from_cache(self, cache_path: Path) -> ApplicationIR:
        """Load ApplicationIR from cached JSON."""
        try:
            with open(cache_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Corrupted cache file: {cache_path} - {e}")
            cache_path.unlink()  # Remove corrupted cache
            raise RuntimeError(f"Cache corrupted, removed: {cache_path}")
        except FileNotFoundError:
            raise RuntimeError(f"Cache file not found: {cache_path}")

        # Reconstruct ApplicationIR from cached dict
        try:
            ir_dict = data.get("application_ir")
            if not ir_dict:
                raise ValueError("Missing 'application_ir' in cache")

            app_ir = ApplicationIR.model_validate(ir_dict)
            logger.info(f"✅ Loaded cached ApplicationIR from {cache_path}")
            return app_ir
        except Exception as e:
            logger.error(f"❌ Failed to reconstruct ApplicationIR from cache: {e}")
            cache_path.unlink()  # Remove invalid cache
            raise RuntimeError(f"Invalid cache format, removed: {cache_path}")

    def _save_to_cache(
        self,
        application_ir: ApplicationIR,
        cache_path: Path,
        spec_hash: str,
        spec_path: str
    ):
        """Save ApplicationIR to cache."""
        cache_data = {
            "spec_hash": spec_hash,
            "spec_path": spec_path,
            "generated_at": datetime.utcnow().isoformat(),
            "application_ir": application_ir.model_dump(mode="json"),
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2, default=str)

    def clear_cache(self, spec_path: Optional[str] = None):
        """Clear cached ApplicationIR files."""
        if spec_path:
            pattern = f"{Path(spec_path).stem}_*.json"
            for cache_file in self.CACHE_DIR.glob(pattern):
                cache_file.unlink()
                logger.info(f"🗑️ Removed cache: {cache_file}")
        else:
            for cache_file in self.CACHE_DIR.glob("*.json"):
                cache_file.unlink()
                logger.info(f"🗑️ Removed cache: {cache_file}")

    def get_cache_info(self, spec_path: str) -> dict[str, Any]:
        """Get information about cached ApplicationIR."""
        pattern = f"{Path(spec_path).stem}_*.json"
        cache_files = list(self.CACHE_DIR.glob(pattern))

        if not cache_files:
            return {"cached": False}

        cache_file = cache_files[0]
        with open(cache_file) as f:
            data = json.load(f)

        validation_rules_count = len(
            data.get("application_ir", {})
            .get("validation_model", {})
            .get("rules", [])
        )

        return {
            "cached": True,
            "cache_path": str(cache_file),
            "spec_hash": data.get("spec_hash", "")[:8],
            "generated_at": data.get("generated_at"),
            "rules_count": validation_rules_count,
            "entities_count": len(
                data.get("application_ir", {})
                .get("domain_model", {})
                .get("entities", [])
            ),
        }


# Sync wrapper for non-async contexts
def get_application_ir_sync(
    spec_markdown: str,
    spec_path: str = "spec.md",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None
) -> ApplicationIR:
    """
    Synchronous wrapper for get_application_ir.

    Uses asyncio.run() internally.
    """
    import asyncio

    converter = SpecToApplicationIR(cache_dir=cache_dir)
    return asyncio.run(converter.get_application_ir(
        spec_markdown, spec_path, force_refresh
    ))
