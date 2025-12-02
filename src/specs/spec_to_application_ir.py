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
import os
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

# IR-Level Best Practice Inference (Phase 0 - single source of truth)
from src.services.inferred_endpoint_enricher import enrich_api_model
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
from src.cognitive.ir.tests_model import TestsModelIR
from src.utils.constraint_helpers import normalize_constraints
from src.state.redis_manager import RedisManager

# Logger must be defined before conditional imports that may use it
logger = logging.getLogger(__name__)

# TestsIRGenerator: Auto-generates TestsModelIR from full ApplicationIR
# Uses DomainModelIR, APIModelIR, BehaviorModelIR, and ValidationModelIR
try:
    from src.services.tests_ir_generator import generate_tests_ir
    TESTS_IR_GENERATOR_AVAILABLE = True
except ImportError:
    TESTS_IR_GENERATOR_AVAILABLE = False
    logger.debug("TestsIRGenerator not available - TestsModelIR will be empty")

# Neo4j persistence (Sprint 7)
try:
    from src.cognitive.services.ir_persistence_service import IRPersistenceService
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

# Feature flag for Neo4j persistence
USE_NEO4J_CACHE = os.getenv("USE_NEO4J_CACHE", "false").lower() == "true"


# =========================================================================
# Bug #I3 Fix: LLM Output Validation Schema
# Validates JSON structure before building ApplicationIR
# =========================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Dict


class LLMAttributeSchema(BaseModel):
    """Validates attribute structure from LLM output."""
    name: str
    data_type: str = "string"
    is_primary_key: bool = False
    is_nullable: bool = False
    is_unique: bool = False
    default_value: Optional[Any] = None
    description: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)


class LLMRelationshipSchema(BaseModel):
    """Validates relationship structure from LLM output."""
    target_entity: str
    type: str = "many_to_one"
    field_name: Optional[str] = None
    back_populates: Optional[str] = None


class LLMEntitySchema(BaseModel):
    """Validates entity structure from LLM output."""
    name: str
    description: Optional[str] = None
    is_aggregate_root: bool = False
    attributes: List[LLMAttributeSchema] = Field(default_factory=list)
    relationships: List[LLMRelationshipSchema] = Field(default_factory=list)


class LLMParameterSchema(BaseModel):
    """Validates parameter structure from LLM output."""
    name: str
    location: str = "query"
    data_type: str = "string"
    required: bool = False
    description: Optional[str] = None


class LLMEndpointSchema(BaseModel):
    """Validates endpoint structure from LLM output."""
    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    auth_required: bool = True
    tags: List[str] = Field(default_factory=list)
    parameters: List[LLMParameterSchema] = Field(default_factory=list)
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None


class LLMStepSchema(BaseModel):
    """Validates step structure from LLM output."""
    order: int = 0
    description: str = ""
    action: str = ""
    target_entity: Optional[str] = None
    condition: Optional[str] = None


class LLMFlowSchema(BaseModel):
    """Validates flow structure from LLM output."""
    name: str
    type: str = "workflow"
    trigger: str = ""
    description: Optional[str] = None
    target_entities: List[str] = Field(default_factory=list)
    steps: List[LLMStepSchema] = Field(default_factory=list)


class LLMValidationRuleSchema(BaseModel):
    """Validates validation rule structure from LLM output."""
    entity: str
    attribute: Optional[str] = None
    type: str
    condition: str
    error_message: Optional[str] = None


class LLMOutputSchema(BaseModel):
    """
    Validates complete LLM output structure.

    Bug #I3 Fix: Ensures LLM output has required fields before building IR.
    Missing fields get defaults; invalid fields raise ValidationError.
    """
    app_name: str = "Application"
    app_description: str = ""
    entities: List[LLMEntitySchema] = Field(default_factory=list)
    endpoints: List[LLMEndpointSchema] = Field(default_factory=list)
    flows: List[LLMFlowSchema] = Field(default_factory=list)
    validation_rules: List[LLMValidationRuleSchema] = Field(default_factory=list)
    entity_dependencies: List[Dict[str, str]] = Field(default_factory=list)

    @validator('entities')
    def validate_entities_not_empty(cls, v):
        if not v:
            logger.warning("⚠️ LLM returned no entities - spec may be malformed")
        return v

    @validator('endpoints')
    def validate_endpoints_not_empty(cls, v):
        if not v:
            logger.warning("⚠️ LLM returned no endpoints - spec may be malformed")
        return v


def _validate_llm_output(ir_data: dict) -> dict:
    """
    Bug #I3 Fix: Validate and normalize LLM output.

    Converts raw dict to Pydantic model and back to dict.
    This ensures:
    1. Required fields are present (with defaults if missing)
    2. Types are correct
    3. Nested structures are valid

    Returns:
        Validated and normalized dict

    Raises:
        RuntimeError if validation fails completely
    """
    try:
        validated = LLMOutputSchema(**ir_data)
        # Convert back to dict, which now has all defaults filled in
        return validated.model_dump()
    except Exception as e:
        logger.error(f"❌ LLM output validation failed: {e}")
        # Log what we got for debugging
        logger.debug(f"Raw ir_data keys: {ir_data.keys() if isinstance(ir_data, dict) else 'NOT A DICT'}")
        raise RuntimeError(f"LLM output validation failed: {e}")


# Bug #16 Fix: Spanish→English translation dictionary for flow names
# DevMatrix works internally in English only - this post-processes LLM output
SPANISH_TO_ENGLISH = {
    # Verbs (infinitive and conjugated forms)
    "crear": "create", "listar": "list", "obtener": "get", "ver": "view",
    "actualizar": "update", "eliminar": "delete", "agregar": "add",
    "procesar": "process", "cancelar": "cancel", "vaciar": "clear",
    "desactivar": "deactivate", "activar": "activate", "registrar": "register",
    "pagar": "pay", "checkout": "checkout",
    # Nouns
    "producto": "product", "productos": "products", "carrito": "cart",
    "orden": "order", "órdenes": "orders", "ordenes": "orders",
    "cliente": "customer", "clientes": "customers",
    "ítem": "item", "item": "item", "items": "items",
    "pago": "payment", "cantidad": "quantity", "detalles": "details",
    "activos": "active", "actual": "current", "simulado": "simulated",
    # Prepositions and articles (to remove or translate)
    "del": "of", "de": "of", "al": "to", "el": "the", "la": "the",
    "los": "the", "las": "the", "un": "a", "una": "a",
}


def _translate_to_english(text: str) -> str:
    """
    Bug #16 Fix: Translate Spanish flow names to English.

    This is post-processing because LLM sometimes ignores translation instructions.
    DevMatrix internally works ONLY in English.

    Examples:
        "F1: Crear Producto" → "F1: Create Product"
        "F9: Agregar Ítem al Carrito" → "F9: Add Item to Cart"
    """
    if not text:
        return text

    # Preserve the F# prefix if present
    prefix = ""
    rest = text
    if text.startswith("F") and ":" in text[:5]:
        colon_idx = text.index(":")
        prefix = text[:colon_idx + 1] + " "
        rest = text[colon_idx + 1:].strip()

    # Split into words and translate each
    words = rest.split()
    translated_words = []

    for word in words:
        # Preserve capitalization
        lower_word = word.lower()
        # Remove accents for matching
        lower_word_clean = lower_word.replace("í", "i").replace("é", "e").replace("á", "a").replace("ó", "o").replace("ú", "u")

        if lower_word in SPANISH_TO_ENGLISH:
            english = SPANISH_TO_ENGLISH[lower_word]
            # Preserve original capitalization
            if word[0].isupper():
                english = english.capitalize()
            translated_words.append(english)
        elif lower_word_clean in SPANISH_TO_ENGLISH:
            english = SPANISH_TO_ENGLISH[lower_word_clean]
            if word[0].isupper():
                english = english.capitalize()
            translated_words.append(english)
        else:
            translated_words.append(word)

    # Clean up: remove "of the" patterns, join words
    result = " ".join(translated_words)
    # Clean common patterns
    result = result.replace(" Of The ", " ").replace(" of the ", " ")
    result = result.replace(" The ", " ").replace(" the ", " ")
    result = result.replace(" To The ", " To ").replace(" to the ", " to ")
    result = result.replace(" Of ", " ").replace(" of ", " ")
    result = result.replace("  ", " ").strip()

    return prefix + result


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

    CACHE_DIR = Path(".devmatrix/ir_cache")  # Filesystem fallback
    # Bug #I5 Fix: Configurable LLM model via env var
    DEFAULT_LLM_MODEL = "claude-sonnet-4-5-20250929"  # Sonnet 4.5 - balanced speed/quality

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        use_neo4j: Optional[bool] = None,
        llm_model: Optional[str] = None
    ):
        """Initialize the converter with Redis as primary cache.

        Args:
            cache_dir: Optional custom cache directory
            use_neo4j: Enable Neo4j persistence (default: from USE_NEO4J_CACHE env var)
            llm_model: LLM model to use (default: from DEVMATRIX_LLM_MODEL env var or DEFAULT_LLM_MODEL)
        """
        if ANTHROPIC_AVAILABLE:
            self.client = AsyncAnthropic()
        else:
            self.client = None
            logger.warning("Anthropic not available - LLM extraction disabled")

        # Bug #I5 Fix: Configurable LLM model
        self.llm_model = llm_model or os.getenv("DEVMATRIX_LLM_MODEL", self.DEFAULT_LLM_MODEL)
        logger.info(f"🤖 Using LLM model: {self.llm_model}")

        # Filesystem cache as fallback (cold start, debugging)
        self.CACHE_DIR = cache_dir or self.CACHE_DIR
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Redis as primary cache (fast, TTL auto-expire)
        self.redis = RedisManager(enable_fallback=True)

        # Neo4j persistence (Sprint 7)
        self.use_neo4j = use_neo4j if use_neo4j is not None else USE_NEO4J_CACHE
        self._neo4j_service = None
        if self.use_neo4j and NEO4J_AVAILABLE:
            try:
                self._neo4j_service = IRPersistenceService()
                logger.info("🗄️ Neo4j persistence enabled")
            except Exception as e:
                logger.warning(f"Neo4j persistence unavailable: {e}")
                self._neo4j_service = None

    async def get_application_ir(
        self,
        spec_markdown: str,
        spec_path: str = "spec.md",
        force_refresh: bool = False
    ) -> ApplicationIR:
        """
        Get ApplicationIR for spec, using multi-tier cache.

        CACHE STRATEGY:
        1. Redis (primary) - fast, TTL auto-expire (7 days)
        2. Filesystem (fallback) - cold start recovery, debugging
        3. LLM generation - only when no cache exists

        Args:
            spec_markdown: Raw markdown content of specification
            spec_path: Path to spec file (for cache key and naming)
            force_refresh: Force regeneration even if cached

        Returns:
            ApplicationIR representing the spec
        """
        spec_hash = self._hash_spec(spec_markdown)
        code_version = self._get_code_version_hash()  # Bug #44 Fix
        cache_key = f"{Path(spec_path).stem}_{spec_hash[:8]}_{code_version}"
        cache_path = self.CACHE_DIR / f"{cache_key}.json"

        if not force_refresh:
            # TIER 1: Try Redis first (fast)
            cached_data = self.redis.get_cached_ir(cache_key)
            if cached_data:
                try:
                    ir_dict = cached_data.get("application_ir")
                    if ir_dict:
                        app_ir = ApplicationIR.model_validate(ir_dict)
                        logger.info(f"📦 Redis cache hit for {cache_key}")
                        return app_ir
                except Exception as e:
                    logger.warning(f"Redis cache invalid, falling back: {e}")

            # TIER 2: Try filesystem fallback (cold start)
            if cache_path.exists():
                try:
                    app_ir = self._load_from_cache(cache_path)
                    logger.info(f"📁 Filesystem cache hit for {cache_key}")
                    # Warm up Redis with filesystem data
                    self._cache_to_redis(app_ir, cache_key, spec_hash, spec_path)
                    return app_ir
                except Exception as e:
                    logger.warning(f"Filesystem cache invalid: {e}")

        # TIER 3: Generate with LLM
        logger.info(f"🤖 Generating ApplicationIR with LLM for {spec_path}")
        application_ir = await self._generate_with_llm(spec_markdown, spec_path)

        # Save to all caches
        self._save_to_cache(application_ir, cache_path, spec_hash, spec_path)
        self._cache_to_redis(application_ir, cache_key, spec_hash, spec_path)

        # TIER 4: Neo4j persistence (Sprint 7)
        if self._neo4j_service:
            try:
                self._persist_to_neo4j(application_ir, cache_key)
            except Exception as e:
                logger.warning(f"Neo4j persistence failed (non-blocking): {e}")

        return application_ir

    def _persist_to_neo4j(self, application_ir: ApplicationIR, app_id: str) -> str:
        """
        Persist ApplicationIR to Neo4j graph database.

        Sprint 7: Integration with Neo4j for graph-native storage.

        Args:
            application_ir: ApplicationIR to persist
            app_id: Application identifier (cache key)

        Returns:
            str: The app_id used for persistence
        """
        if not self._neo4j_service:
            raise RuntimeError("Neo4j service not initialized")

        saved_id = self._neo4j_service.save_application_ir(application_ir, app_id=app_id)
        logger.info(f"🗄️ Persisted ApplicationIR to Neo4j: {saved_id}")
        return saved_id

    def load_from_neo4j(self, app_id: str) -> Optional[ApplicationIR]:
        """
        Load ApplicationIR from Neo4j graph database.

        Sprint 7: Load from Neo4j for cross-session access.

        Args:
            app_id: Application identifier

        Returns:
            ApplicationIR if found, None otherwise
        """
        if not self._neo4j_service:
            logger.warning("Neo4j service not available")
            return None

        return self._neo4j_service.load_application_ir(app_id)

    def _cache_to_redis(
        self,
        application_ir: ApplicationIR,
        cache_key: str,
        spec_hash: str,
        spec_path: str
    ):
        """Save ApplicationIR to Redis cache."""
        cache_data = {
            "spec_hash": spec_hash,
            "spec_path": spec_path,
            "generated_at": datetime.utcnow().isoformat(),
            "application_ir": application_ir.model_dump(mode="json"),
        }
        if self.redis.cache_ir(cache_key, cache_data):
            logger.info(f"💾 Cached ApplicationIR to Redis: {cache_key}")

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

        # Bug #I3 Fix: Validate LLM output structure before building IR
        ir_data = _validate_llm_output(ir_data)
        logger.info(
            f"✅ LLM output validated: {len(ir_data.get('entities', []))} entities, "
            f"{len(ir_data.get('endpoints', []))} endpoints"
        )

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
      "name": "F1: English Flow Name (NEVER Spanish, ALWAYS translate)",
      "type": "workflow|state_transition|policy|event_handler",
      "trigger": "What triggers this flow (in English)",
      "description": "Description in English (translate if spec is Spanish)",
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

*******************************************************************************
** MANDATORY TRANSLATION RULE - READ THIS CAREFULLY **
*******************************************************************************
ALL OUTPUT MUST BE IN ENGLISH. If the spec is in Spanish, French, German, or
any other language, YOU MUST TRANSLATE to English.

FLOW NAMES - MUST BE IN ENGLISH:
  WRONG: "F1: Crear Producto"           → DO NOT OUTPUT THIS
  RIGHT: "F1: Create Product"           → OUTPUT THIS INSTEAD

  WRONG: "F9: Agregar Ítem al Carrito"  → DO NOT OUTPUT THIS
  RIGHT: "F9: Add Item to Cart"         → OUTPUT THIS INSTEAD

  WRONG: "F13: Procesar Pago"           → DO NOT OUTPUT THIS
  RIGHT: "F13: Process Payment"         → OUTPUT THIS INSTEAD

TRANSLATION TABLE (use these):
  crear → create, listar → list, obtener → get, actualizar → update,
  eliminar → delete, agregar → add, procesar → process, cancelar → cancel,
  ver → view, vaciar → clear, desactivar → deactivate, activar → activate,
  producto → product, carrito → cart, orden → order, cliente → customer,
  ítem/item → item, pago → payment, cantidad → quantity

If you output Spanish text in flow names, the system will FAIL.
*******************************************************************************

SPECIFICATION:
{spec_markdown}

Output JSON only, no explanation:"""

    async def _generate_with_streaming(self, prompt: str, max_retries: int = 3) -> str:
        """Stream LLM response for large specs to avoid 10-min timeout.

        Bug #I6 Fix: Added retry logic with exponential backoff.
        """
        import asyncio

        last_error = None
        for attempt in range(max_retries):
            response_text = ""
            try:
                async with self.client.messages.stream(
                    model=self.llm_model,  # Bug #I5 Fix: Use configurable model
                    max_tokens=32000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                ) as stream:
                    async for text in stream.text_stream:
                        response_text += text
                        if len(response_text) % 10000 == 0:
                            logger.debug(f"  📊 Streamed {len(response_text)} chars...")

                logger.info(f"✅ Streaming complete: {len(response_text)} chars")
                return response_text

            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"⚠️ LLM attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)

        logger.error(f"❌ All {max_retries} LLM attempts failed")
        raise last_error or RuntimeError("LLM streaming failed after all retries")

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

        # PHASE 0: IR-Level Best Practice Inference
        # Enrich with inferred endpoints (list, delete, health, metrics)
        # All inferred endpoints are marked with inferred=True for traceability
        # Bug #47 Fix: Pass domain_model and flows_data for advanced inference
        api_model = enrich_api_model(
            api_model,
            domain_model=domain_model,
            flows_data=ir_data.get("flows", [])
        )

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
        # Bug #I2 Fix: Pass api_model for endpoint inference
        behavior_model = self._build_behavior_model(ir_data, api_model)

        # Build ApplicationIR (without tests_model first - we need the full IR to generate it)
        app_name = ir_data.get("app_name", Path(spec_path).stem)

        app_ir = ApplicationIR(
            name=app_name,
            description=ir_data.get("app_description", f"Generated from {spec_path}"),
            domain_model=domain_model,
            api_model=api_model,
            infrastructure_model=infrastructure_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            phase_status={"spec_extraction": "complete"},
        )

        # Bug #I1 Fix: Auto-generate TestsModelIR from full ApplicationIR
        # Uses: DomainModelIR → SeedEntityIR, APIModelIR → EndpointTestSuite,
        #       BehaviorModelIR → FlowTestSuite, ValidationModelIR → edge cases
        if TESTS_IR_GENERATOR_AVAILABLE:
            try:
                tests_model = generate_tests_ir(app_ir)
                app_ir.tests_model = tests_model
                logger.info(
                    f"✅ TestsModelIR auto-generated: "
                    f"{len(tests_model.seed_entities)} seeds, "
                    f"{len(tests_model.endpoint_suites)} endpoint suites, "
                    f"{len(tests_model.flow_suites)} flow suites"
                )
            except Exception as e:
                logger.warning(f"⚠️ TestsModelIR generation failed: {e}")
                # Continue with empty tests_model - not blocking
        else:
            logger.warning("⚠️ TestsIRGenerator not available - TestsModelIR empty")

        return app_ir

    def _build_behavior_model(self, ir_data: dict, api_model: Optional[APIModelIR] = None) -> BehaviorModelIR:
        """Build BehaviorModelIR from extracted flows and entity dependencies.

        Bug #I2 Fix: Populate IRFlow extension fields for cognitive code generation.
        """
        flows = []
        invariants = []

        # Process flows from LLM extraction
        for flow_data in ir_data.get("flows", []):
            steps = []
            entities_from_steps = set()

            for step_data in flow_data.get("steps", []):
                step = Step(
                    order=step_data.get("order", 0),
                    description=step_data.get("description", ""),
                    action=step_data.get("action", ""),
                    target_entity=step_data.get("target_entity"),
                    condition=step_data.get("condition"),
                )
                steps.append(step)
                # Collect entities from steps
                if step.target_entity:
                    entities_from_steps.add(step.target_entity)

            # Bug #16 Fix: Translate flow name from Spanish to English
            raw_name = flow_data.get("name", "Unknown")
            translated_name = _translate_to_english(raw_name)

            # Bug #I2 Fix: Generate flow_id from name
            flow_id = translated_name.lower().replace(" ", "_").replace("-", "_").replace(":", "")
            # Remove common prefixes like "f1_", "f2_" etc
            import re
            flow_id = re.sub(r'^f\d+_', '', flow_id)

            # Bug #I2 Fix: Extract primary entity (first in target_entities or first in steps)
            target_entities = flow_data.get("target_entities", [])
            primary_entity = target_entities[0] if target_entities else None
            if not primary_entity and entities_from_steps:
                primary_entity = sorted(entities_from_steps)[0]

            # Bug #I2 Fix: Combine entities from target_entities and steps
            all_entities = list(set(target_entities) | entities_from_steps)

            # Bug #I2 Fix: Infer endpoint from flow name and primary entity
            endpoint = self._infer_endpoint_from_flow(flow_id, primary_entity, api_model)

            # Bug #I2 Fix: Generate implementation name
            impl_name = flow_id.replace("_flow", "").replace("flow_", "")

            # Bug #I2 Fix: Infer constraint types from flow type and steps
            constraint_types = self._infer_constraint_types(flow_data, steps)

            # Bug #I2 Fix: Extract preconditions from trigger and steps
            preconditions = self._extract_preconditions(flow_data, steps)

            flow = Flow(
                name=translated_name,
                type=self._parse_flow_type(flow_data.get("type", "workflow")),
                trigger=flow_data.get("trigger", ""),
                steps=steps,
                description=flow_data.get("description"),
                # IRFlow extension fields (Bug #I2)
                flow_id=flow_id,
                primary_entity=primary_entity,
                entities_involved=all_entities,
                constraint_types=constraint_types,
                preconditions=preconditions,
                endpoint=endpoint,
                implementation_name=impl_name,
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

    # =========================================================================
    # Bug #I2 Fix: IRFlow Helper Methods
    # =========================================================================

    def _infer_endpoint_from_flow(
        self,
        flow_id: str,
        primary_entity: Optional[str],
        api_model: Optional[APIModelIR]
    ) -> Optional[str]:
        """Infer API endpoint from flow name and primary entity.

        Matches flow_id patterns to endpoints:
        - add_item_to_cart → POST /carts/{id}/items
        - checkout → POST /orders/{id}/checkout
        - create_order → POST /orders
        """
        if not api_model or not primary_entity:
            return None

        entity_lower = primary_entity.lower()
        flow_lower = flow_id.lower()

        # Common action patterns
        action_method_map = {
            "create": "POST",
            "add": "POST",
            "checkout": "POST",
            "cancel": "POST",
            "process": "POST",
            "update": "PUT",
            "delete": "DELETE",
            "get": "GET",
            "list": "GET",
        }

        # Try to match endpoint by flow pattern
        for endpoint in api_model.endpoints:
            path_lower = endpoint.path.lower()
            method = endpoint.method.value

            # Check if entity is in path
            if entity_lower not in path_lower and f"{entity_lower}s" not in path_lower:
                continue

            # Match action in flow_id to HTTP method
            for action, expected_method in action_method_map.items():
                if action in flow_lower and method == expected_method:
                    # Found a match
                    return f"{method} {endpoint.path}"

        return None

    def _infer_constraint_types(self, flow_data: dict, steps: list) -> list[str]:
        """Infer constraint types from flow data and steps."""
        constraints = set()

        flow_type = flow_data.get("type", "").lower()
        flow_name = flow_data.get("name", "").lower()

        # Infer from flow type
        if flow_type == "state_transition":
            constraints.add("status_transition")
        if flow_type == "policy":
            constraints.add("business_logic")

        # Infer from flow type (domain-agnostic)
        # NOTE: Flow names are derived from spec, not hardcoded patterns
        if flow_type in ["transaction", "multi_step"]:
            constraints.add("workflow_constraint")

        # Infer from step actions
        for step in steps:
            action = step.action.lower() if step.action else ""
            if action == "validate":
                constraints.add("validation_constraint")
            if "status" in (step.description or "").lower():
                constraints.add("status_transition")

        return list(constraints)

    def _extract_preconditions(self, flow_data: dict, steps: list) -> list[str]:
        """Extract preconditions from flow trigger and first steps."""
        preconditions = []

        trigger = flow_data.get("trigger", "")
        if trigger:
            # Convert trigger to precondition format
            preconditions.append(f"trigger: {trigger}")

        # First step with condition is a precondition
        for step in steps:
            if step.condition:
                preconditions.append(step.condition)
                break  # Only take first condition as precondition

        return preconditions

    def _extract_implicit_rules(self, entity_name: str, attr: Attribute) -> list[ValidationRule]:
        """Extract implicit validation rules from attribute constraints."""
        rules = []
        # Bug #36 fix: normalize constraints to dict (can be list or dict)
        constraints = normalize_constraints(attr.constraints)

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

    def _get_code_version_hash(self) -> str:
        """
        Bug #44 Fix: Hash of IR-related source files for cache invalidation.

        When IR extraction/validation code changes, the cache should be invalidated
        even if the spec content hasn't changed.

        Bug #I8 Fix: Expanded list of files that affect IR generation.
        """
        files_to_hash = [
            # IR Models
            "src/cognitive/ir/api_model.py",
            "src/cognitive/ir/domain_model.py",
            "src/cognitive/ir/behavior_model.py",
            "src/cognitive/ir/validation_model.py",
            "src/cognitive/ir/tests_model.py",
            "src/cognitive/ir/infrastructure_model.py",
            "src/cognitive/ir/application_ir.py",
            # IR Builders/Generators
            "src/cognitive/ir/ir_builder.py",
            "src/specs/spec_to_application_ir.py",
            "src/services/tests_ir_generator.py",
            # Enrichers and Extractors
            "src/services/business_logic_extractor.py",
            "src/services/inferred_endpoint_enricher.py",
            # Validators
            "src/validation/compliance_validator.py",
        ]
        combined = ""
        for f in files_to_hash:
            file_path = Path(f)
            if file_path.exists():
                combined += hashlib.md5(file_path.read_bytes()).hexdigest()
        return hashlib.md5(combined.encode()).hexdigest()[:8]

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
        """
        Clear cached ApplicationIR from both Redis and filesystem.

        FLUSH STRATEGY:
        - Redis: Uses SCAN (non-blocking, safe for production)
        - Filesystem: Direct file deletion

        Args:
            spec_path: If provided, only clear cache for this spec.
                      If None, clear ALL IR cache entries.
        """
        spec_name = Path(spec_path).stem if spec_path else None

        # Clear Redis first (uses SCAN, non-blocking)
        redis_deleted = self.redis.clear_ir_cache(spec_name)
        if redis_deleted > 0:
            logger.info(f"🗑️ Cleared {redis_deleted} entries from Redis IR cache")

        # Clear filesystem
        if spec_path:
            pattern = f"{spec_name}_*.json"
            for cache_file in self.CACHE_DIR.glob(pattern):
                cache_file.unlink()
                logger.info(f"🗑️ Removed filesystem cache: {cache_file}")
        else:
            for cache_file in self.CACHE_DIR.glob("*.json"):
                cache_file.unlink()
                logger.info(f"🗑️ Removed filesystem cache: {cache_file}")

    def get_cache_info(self, spec_path: str) -> dict[str, Any]:
        """Get information about cached ApplicationIR from both tiers."""
        spec_name = Path(spec_path).stem
        pattern = f"{spec_name}_*.json"

        info = {
            "cached": False,
            "redis_cached": False,
            "filesystem_cached": False,
        }

        # Check Redis first
        redis_stats = self.redis.get_ir_cache_stats()
        redis_keys = [k for k in redis_stats.get("keys", []) if spec_name in str(k)]
        if redis_keys:
            info["redis_cached"] = True
            info["redis_keys"] = redis_keys
            info["redis_source"] = redis_stats.get("source", "unknown")

        # Check filesystem
        cache_files = list(self.CACHE_DIR.glob(pattern))
        if cache_files:
            info["filesystem_cached"] = True
            cache_file = cache_files[0]
            info["cache_path"] = str(cache_file)

            try:
                with open(cache_file) as f:
                    data = json.load(f)

                validation_rules_count = len(
                    data.get("application_ir", {})
                    .get("validation_model", {})
                    .get("rules", [])
                )

                info["spec_hash"] = data.get("spec_hash", "")[:8]
                info["generated_at"] = data.get("generated_at")
                info["rules_count"] = validation_rules_count
                info["entities_count"] = len(
                    data.get("application_ir", {})
                    .get("domain_model", {})
                    .get("entities", [])
                )
            except Exception as e:
                info["filesystem_error"] = str(e)

        info["cached"] = info["redis_cached"] or info["filesystem_cached"]
        return info


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
