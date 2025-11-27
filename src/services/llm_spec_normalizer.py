"""
LLM-based Specification Normalizer (Option B)

Converts markdown/natural language specs to formal JSON format using Claude.
This allows DevMatrix to accept specs in ANY format while maintaining
validation extraction consistency.

Architecture:
  markdown spec → LLMSpecNormalizer → JSON formal → validation extraction
"""

import json
import logging
from typing import Any, Dict, Optional

# Bug #22 Fix: Use EnhancedAnthropicClient for global metrics tracking
from src.llm import EnhancedAnthropicClient

logger = logging.getLogger(__name__)


class SpecValidationError(Exception):
    """Raised when normalized spec fails validation"""
    pass


class LLMSpecNormalizer:
    """
    Normalizes markdown/natural language specs to formal JSON format using Claude.

    This is Option B from the architectural evaluation:
    - Input: Markdown specification (ecommerce_api_simple.md style)
    - Process: Claude understands and extracts all constraints
    - Output: Formal JSON (ecommerce_api_formal.json style)

    Bug #10 Fix: Now tracks token usage for stratum metrics.
    """

    # Token tracking for Bug #10
    last_input_tokens: int = 0
    last_output_tokens: int = 0

    NORMALIZATION_PROMPT = """You are a JSON conversion expert. Convert the markdown specification below into VALID JSON format ONLY.

CRITICAL: Your output must be PURE JSON - nothing else. No markdown code blocks, no explanations, no text before or after the JSON.

Output format (pure JSON, no decorations):
{{"entities": [...], "relationships": [...], "endpoints": [...]}}

Entity structure:
{{"name": "EntityName", "fields": [{{"name": "field_name", "type": "string", "required": true, "unique": false, "is_primary_key": false}}]}}

Field types: string, integer, decimal, UUID, datetime, boolean
Field attributes: required (bool), unique (bool), is_primary_key (bool), minimum (number), maximum (number), min_length (number), max_length (number), allowed_values (array)

Relationship structure:
{{"from": "Entity1", "to": "Entity2", "type": "one-to-many", "foreign_key": "fk_name", "required": true, "cascade_delete": false}}

Endpoint structure:
{{"method": "GET", "path": "/api/path", "name": "Endpoint Name", "parameters": ["param1"]}}

Rules for conversion:
1. Extract all entities with their fields
2. For each field, identify: type, required, unique, primary_key, constraints
3. Extract all relationships and foreign keys
4. Extract all API endpoints
5. CRITICAL: ALL field names MUST be in English using snake_case convention, regardless of the spec language:
   - "estado_activo" → "is_active"
   - "nombre_completo" → "full_name"
   - "fecha_de_registro" → "registration_date"
   - "fecha_creacion" or "creation_date" → "created_at"
   - "cliente_propietario" → "customer_id"
   - "monto_total" → "total_amount"
   - "precio_unitario" → "unit_price"
   - "cantidad" → "quantity"
   - "producto" → "product_id" (if it's a foreign key)
   - Use standard Python/SQLAlchemy naming conventions (snake_case, English)

Markdown specification:

{spec_markdown}

RESPOND WITH ONLY VALID JSON. START WITH {{ AND END WITH }}. NO MARKDOWN. NO EXPLANATIONS."""

    def __init__(self, model: Optional[str] = None):
        """Initialize with Anthropic client"""
        # Bug #22 Fix: Use EnhancedAnthropicClient for global metrics tracking
        self._enhanced_client = EnhancedAnthropicClient()
        self.client = self._enhanced_client.anthropic  # Access underlying sync client
        # Use provided model or default to best available
        if model is None:
            model = "claude-sonnet-4-5-20250929"  # Sonnet for semantic analysis
        self.model = model

    def normalize(self, markdown_spec: str) -> Dict[str, Any]:
        """
        Convert markdown spec to formal JSON using Claude.

        Args:
            markdown_spec: Raw markdown specification text

        Returns:
            dict: Formal specification as JSON structure

        Raises:
            SpecValidationError: If JSON is invalid or incomplete
        """
        logger.info("Starting LLM spec normalization...")
        logger.debug(f"Input spec length: {len(markdown_spec)} chars")

        # Call Claude to normalize
        prompt = self.NORMALIZATION_PROMPT.format(spec_markdown=markdown_spec)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Bug #10 Fix: Track token usage for stratum metrics
            self.last_input_tokens = response.usage.input_tokens
            self.last_output_tokens = response.usage.output_tokens
            logger.info(f"LLM tokens: input={self.last_input_tokens}, output={self.last_output_tokens}")

            # Bug #22 Fix: Record usage to global metrics for E2E tracking
            EnhancedAnthropicClient._record_global_usage(
                input_tokens=self.last_input_tokens,
                output_tokens=self.last_output_tokens
            )

            json_text = response.content[0].text.strip()
            logger.debug(f"LLM response length: {len(json_text)} chars")

            # Extract JSON from response (handle markdown code blocks)
            if "```" in json_text:
                # Find first { and last }
                start_idx = json_text.find("{")
                end_idx = json_text.rfind("}")
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = json_text[start_idx:end_idx+1]
            elif not json_text.startswith("{"):
                # Try to find JSON object in response
                start_idx = json_text.find("{")
                if start_idx >= 0:
                    end_idx = json_text.rfind("}")
                    if end_idx > start_idx:
                        json_text = json_text[start_idx:end_idx+1]

            # Parse and validate JSON
            formal_spec = json.loads(json_text)
            logger.info("JSON parsed successfully")

            # Validate structure
            self._validate_structure(formal_spec)
            logger.info("Structure validation passed")

            return formal_spec

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"LLM output: {json_text[:500]}...")
            raise SpecValidationError(f"Invalid JSON from LLM: {e}")

    def _validate_structure(self, spec: Dict[str, Any]) -> None:
        """
        Validate that the normalized spec has required structure.

        Raises:
            SpecValidationError: If structure is invalid
        """
        # Check root keys
        if not isinstance(spec, dict):
            raise SpecValidationError("Spec must be a dictionary")

        if "entities" not in spec:
            raise SpecValidationError("Spec missing 'entities' key")

        # Validate entities
        entities = spec.get("entities", [])
        if not isinstance(entities, list):
            raise SpecValidationError("'entities' must be a list")

        if len(entities) == 0:
            raise SpecValidationError("'entities' must have at least 1 entity")

        for entity in entities:
            if not isinstance(entity, dict):
                raise SpecValidationError("Entity must be a dict")
            if "name" not in entity or "fields" not in entity:
                raise SpecValidationError(f"Entity missing 'name' or 'fields': {entity}")

            if not isinstance(entity["fields"], list):
                raise SpecValidationError(f"Entity '{entity['name']}' fields must be a list")

            if len(entity["fields"]) == 0:
                raise SpecValidationError(f"Entity '{entity['name']}' must have at least 1 field")

        # Validate relationships (if present)
        if "relationships" in spec:
            relationships = spec["relationships"]
            if not isinstance(relationships, list):
                raise SpecValidationError("'relationships' must be a list")

            for rel in relationships:
                if not isinstance(rel, dict):
                    raise SpecValidationError("Relationship must be a dict")
                if "from" not in rel or "to" not in rel:
                    raise SpecValidationError(f"Relationship missing 'from' or 'to': {rel}")

        # Validate endpoints (if present)
        if "endpoints" in spec:
            endpoints = spec["endpoints"]
            if not isinstance(endpoints, list):
                raise SpecValidationError("'endpoints' must be a list")

        logger.info("All structural validations passed")

    def get_last_token_usage(self) -> tuple:
        """
        Get token usage from last normalize() call.

        Bug #10 Fix: Provides token counts for stratum metrics integration.

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        return (self.last_input_tokens, self.last_output_tokens)


class HybridSpecNormalizer:
    """
    Hybrid spec normalizer with retry and fallback (Option C).

    This wraps LLMSpecNormalizer with:
    - Automatic retry on failure
    - Manual fallback option
    - Detailed logging

    Architecture:
      markdown spec
        ↓
      Attempt 1: LLM normalization → validate
        ├─ Success → return
        └─ Failure → retry with improved prompt
      Attempt 2: LLM normalization (improved prompt)
        ├─ Success → return
        └─ Failure → use fallback
      Manual fallback: return pre-created formal JSON
    """

    def __init__(self, model: Optional[str] = None,
                 max_retries: int = 2,
                 fallback_spec: Optional[Dict[str, Any]] = None):
        """
        Initialize hybrid normalizer.

        Args:
            model: Claude model to use
            max_retries: Number of attempts (including first attempt)
            fallback_spec: Pre-created JSON to use if all retries fail
        """
        self.llm_normalizer = LLMSpecNormalizer(model=model)
        self.max_retries = max_retries
        self.fallback_spec = fallback_spec

    def normalize(self, markdown_spec: str) -> Dict[str, Any]:
        """
        Normalize spec with retry and fallback.

        Args:
            markdown_spec: Raw markdown specification

        Returns:
            dict: Formal specification
        """
        logger.info(f"Starting hybrid normalization (max {self.max_retries} attempts)...")

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries}")
                spec = self.llm_normalizer.normalize(markdown_spec)
                logger.info(f"✅ Normalization succeeded on attempt {attempt + 1}")
                return spec

            except SpecValidationError as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying (attempt {attempt + 2}/{self.max_retries})...")
                else:
                    # Last attempt failed, try fallback
                    logger.error("All LLM normalization attempts failed")

                    if self.fallback_spec:
                        logger.warning("Using fallback specification")
                        return self.fallback_spec
                    else:
                        logger.error("No fallback specification available")
                        raise

        raise RuntimeError("Hybrid normalization failed (should not reach here)")

    def set_fallback(self, fallback_spec: Dict[str, Any]) -> None:
        """Set or update the fallback specification."""
        self.fallback_spec = fallback_spec
        logger.info("Fallback specification updated")
