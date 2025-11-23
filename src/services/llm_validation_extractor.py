"""
LLM-Based Validation Extractor (Phase 2)

Aggressive LLM extraction as PRIMARY validation source.
Uses Claude API with structured prompts to extract comprehensive validation rules.

Features:
- Three specialized extraction methods (fields, endpoints, cross-entity)
- Batching strategy to minimize API calls
- Robust JSON parsing with fallback strategies
- Retry logic with exponential backoff
- Confidence scoring for each rule
- Comprehensive error handling
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import re
import time
import logging
from anthropic import Anthropic, APIError, APITimeoutError
from src.cognitive.ir.validation_model import ValidationRule, ValidationType

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of a validation extraction attempt."""
    rules: List[ValidationRule]
    token_count: int
    confidence_avg: float
    errors: List[str]


class LLMValidationExtractor:
    """
    LLM-based validation extractor using Claude API.

    Primary extraction strategy (Phase 2) designed to extract 15-20 additional
    validations beyond pattern-based extraction (Phase 1).

    Extraction Strategy:
    1. Batch field validations (10-15 fields per call)
    2. Individual endpoint validations
    3. Single cross-entity validation call

    Total expected API calls: 3-5 per spec
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM extractor with Claude API client.

        Args:
            api_key: Optional Anthropic API key (defaults to env var)
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = "claude-3-5-sonnet-20241022"
        self.max_retries = 3
        self.retry_delay_base = 1.0  # seconds
        self.batch_size = 12  # fields per batch for optimal token usage

        # Track token usage for cost monitoring
        self.total_tokens_used = 0
        self.total_api_calls = 0

    def extract_all_validations(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """
        Extract ALL validation rules from specification using LLM.

        Primary entry point for comprehensive validation extraction.

        Args:
            spec: Application specification dictionary

        Returns:
            List of ValidationRule objects with confidence scores
        """
        all_rules = []

        # Stage 1: Field-level validations (batched)
        try:
            field_result = self._extract_field_validations(spec)
            all_rules.extend(field_result.rules)
            logger.info(
                f"Field extraction: {len(field_result.rules)} rules, "
                f"avg confidence: {field_result.confidence_avg:.2f}, "
                f"tokens: {field_result.token_count}"
            )
        except Exception as e:
            logger.error(f"Field validation extraction failed: {e}")

        # Stage 2: Endpoint validations
        try:
            endpoint_result = self._extract_endpoint_validations(spec)
            all_rules.extend(endpoint_result.rules)
            logger.info(
                f"Endpoint extraction: {len(endpoint_result.rules)} rules, "
                f"avg confidence: {endpoint_result.confidence_avg:.2f}, "
                f"tokens: {endpoint_result.token_count}"
            )
        except Exception as e:
            logger.error(f"Endpoint validation extraction failed: {e}")

        # Stage 3: Cross-entity and workflow validations
        try:
            cross_result = self._extract_cross_entity_validations(spec)
            all_rules.extend(cross_result.rules)
            logger.info(
                f"Cross-entity extraction: {len(cross_result.rules)} rules, "
                f"avg confidence: {cross_result.confidence_avg:.2f}, "
                f"tokens: {cross_result.token_count}"
            )
        except Exception as e:
            logger.error(f"Cross-entity validation extraction failed: {e}")

        logger.info(
            f"LLM extraction complete: {len(all_rules)} total rules, "
            f"{self.total_tokens_used} tokens, {self.total_api_calls} API calls"
        )

        return all_rules

    def _extract_field_validations(self, spec: Dict[str, Any]) -> ExtractionResult:
        """
        Extract field-level validation rules with batching.

        Processes fields in batches of 12 to minimize API calls while
        maintaining comprehensive analysis.

        Args:
            spec: Application specification

        Returns:
            ExtractionResult with field validation rules
        """
        entities = spec.get("entities", [])
        all_rules = []
        total_tokens = 0
        confidence_scores = []
        errors = []

        # Collect all fields with entity context
        field_contexts = []
        for entity in entities:
            entity_name = entity.get("name", "")
            for field in entity.get("fields", []):
                field_contexts.append({
                    "entity": entity_name,
                    "field": field,
                    "field_name": field.get("name", ""),
                    "field_type": field.get("type", ""),
                    "description": field.get("description", ""),
                    "constraints": field.get("constraints", {}),
                    "required": field.get("required", False),
                    "unique": field.get("unique", False)
                })

        # Process in batches
        for i in range(0, len(field_contexts), self.batch_size):
            batch = field_contexts[i:i + self.batch_size]

            try:
                prompt = self._create_field_validation_prompt(batch)
                response_text, tokens = self._call_llm_with_retry(prompt)

                rules, confidences = self._parse_validation_response(response_text)
                all_rules.extend(rules)
                confidence_scores.extend(confidences)
                total_tokens += tokens

                logger.debug(
                    f"Batch {i//self.batch_size + 1}: "
                    f"{len(rules)} rules extracted from {len(batch)} fields"
                )
            except Exception as e:
                error_msg = f"Field batch {i//self.batch_size + 1} failed: {e}"
                errors.append(error_msg)
                logger.warning(error_msg)

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return ExtractionResult(
            rules=all_rules,
            token_count=total_tokens,
            confidence_avg=avg_confidence,
            errors=errors
        )

    def _extract_endpoint_validations(self, spec: Dict[str, Any]) -> ExtractionResult:
        """
        Extract endpoint-level validation rules.

        Analyzes API endpoints for request/response validation requirements.

        Args:
            spec: Application specification

        Returns:
            ExtractionResult with endpoint validation rules
        """
        endpoints = spec.get("endpoints", [])
        if not endpoints:
            return ExtractionResult(rules=[], token_count=0, confidence_avg=0.0, errors=[])

        all_rules = []
        confidence_scores = []
        total_tokens = 0
        errors = []

        try:
            prompt = self._create_endpoint_validation_prompt(endpoints, spec.get("entities", []))
            response_text, tokens = self._call_llm_with_retry(prompt)

            rules, confidences = self._parse_validation_response(response_text)
            all_rules.extend(rules)
            confidence_scores.extend(confidences)
            total_tokens += tokens
        except Exception as e:
            error_msg = f"Endpoint extraction failed: {e}"
            errors.append(error_msg)
            logger.error(error_msg)

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return ExtractionResult(
            rules=all_rules,
            token_count=total_tokens,
            confidence_avg=avg_confidence,
            errors=errors
        )

    def _extract_cross_entity_validations(self, spec: Dict[str, Any]) -> ExtractionResult:
        """
        Extract cross-entity and workflow validation rules.

        Identifies relationship constraints, workflow transitions, and business rules
        that span multiple entities.

        Args:
            spec: Application specification

        Returns:
            ExtractionResult with cross-entity validation rules
        """
        all_rules = []
        confidence_scores = []
        total_tokens = 0
        errors = []

        try:
            prompt = self._create_cross_entity_validation_prompt(spec)
            response_text, tokens = self._call_llm_with_retry(prompt)

            rules, confidences = self._parse_validation_response(response_text)
            all_rules.extend(rules)
            confidence_scores.extend(confidences)
            total_tokens += tokens
        except Exception as e:
            error_msg = f"Cross-entity extraction failed: {e}"
            errors.append(error_msg)
            logger.error(error_msg)

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return ExtractionResult(
            rules=all_rules,
            token_count=total_tokens,
            confidence_avg=avg_confidence,
            errors=errors
        )

    def _create_field_validation_prompt(self, field_contexts: List[Dict[str, Any]]) -> str:
        """
        Create structured prompt for field-level validation extraction.

        Args:
            field_contexts: List of field context dicts with entity, field details

        Returns:
            Formatted prompt string
        """
        # Build field descriptions
        field_descriptions = []
        for ctx in field_contexts:
            desc = (
                f"- Entity: {ctx['entity']}\n"
                f"  Field: {ctx['field_name']}\n"
                f"  Type: {ctx['field_type']}\n"
                f"  Required: {ctx['required']}\n"
                f"  Unique: {ctx['unique']}\n"
            )
            if ctx['description']:
                desc += f"  Description: {ctx['description']}\n"
            if ctx['constraints']:
                desc += f"  Constraints: {ctx['constraints']}\n"
            field_descriptions.append(desc)

        prompt = f"""Analyze these database fields and extract ALL validation rules needed.

FIELDS TO ANALYZE:
{chr(10).join(field_descriptions)}

For EACH field, identify ALL validations considering:
1. Data type constraints (format, pattern, structure)
2. Semantic meaning (email → email format, password → strength, phone → format)
3. Uniqueness requirements (email, username typically unique)
4. Range constraints (min/max length, min/max value)
5. Relationship constraints (foreign keys, references)
6. Business logic (stock > 0, status transitions, quantity constraints)

Return a JSON array ONLY (no markdown, no explanation):
[
  {{
    "entity": "EntityName",
    "attribute": "field_name",
    "type": "PRESENCE|FORMAT|RANGE|UNIQUENESS|RELATIONSHIP|STOCK_CONSTRAINT|STATUS_TRANSITION|WORKFLOW_CONSTRAINT",
    "condition": "specific condition or constraint description",
    "error_message": "user-friendly error message",
    "confidence": 0.95,
    "rationale": "brief explanation why this validation is needed"
  }}
]

VALIDATION TYPES:
- PRESENCE: Required fields, not null
- FORMAT: Email, phone, URL, UUID, datetime patterns
- RANGE: Min/max length, min/max value constraints
- UNIQUENESS: Unique email, username, identifier
- RELATIONSHIP: Foreign key references, entity existence
- STOCK_CONSTRAINT: Inventory availability, quantity checks
- STATUS_TRANSITION: Valid state changes, enum values
- WORKFLOW_CONSTRAINT: Process sequence, multi-step validation

Be comprehensive - extract ALL implicit and explicit validations."""

        return prompt

    def _create_endpoint_validation_prompt(
        self,
        endpoints: List[Dict[str, Any]],
        entities: List[Dict[str, Any]]
    ) -> str:
        """
        Create structured prompt for endpoint validation extraction.

        Args:
            endpoints: List of API endpoint definitions
            entities: List of entity definitions for context

        Returns:
            Formatted prompt string
        """
        # Build endpoint descriptions
        endpoint_descriptions = []
        for ep in endpoints:
            desc = (
                f"- Method: {ep.get('method', 'GET').upper()}\n"
                f"  Path: {ep.get('path', '')}\n"
            )
            if ep.get('parameters'):
                desc += f"  Parameters: {ep['parameters']}\n"
            if ep.get('request_body'):
                desc += f"  Request Body: {ep['request_body']}\n"
            if ep.get('description'):
                desc += f"  Description: {ep['description']}\n"
            endpoint_descriptions.append(desc)

        # Entity names for context
        entity_names = [e.get('name', '') for e in entities]

        prompt = f"""Analyze these API endpoints and extract ALL validation rules.

ENDPOINTS:
{chr(10).join(endpoint_descriptions)}

AVAILABLE ENTITIES:
{', '.join(entity_names)}

For EACH endpoint, identify validations for:
1. Path parameters (required, format, type)
   - ID parameters must be valid UUIDs
   - ID must reference existing entity
2. Query parameters (optional/required, format, constraints)
   - Pagination: page >= 1, limit > 0
   - Filters: valid values, format
3. Request body (structure, required fields, constraints)
   - All required fields present
   - Field formats and types
   - Cross-field validations
4. Response validations (expected structure)

Return JSON array ONLY (no markdown):
[
  {{
    "entity": "Endpoint:METHOD" or "EntityName",
    "attribute": "parameter_name or body_field",
    "type": "PRESENCE|FORMAT|RANGE|RELATIONSHIP|...",
    "condition": "specific constraint",
    "error_message": "user-friendly error",
    "confidence": 0.90,
    "rationale": "why this validation is needed"
  }}
]

Extract ALL request/response validations comprehensively."""

        return prompt

    def _create_cross_entity_validation_prompt(self, spec: Dict[str, Any]) -> str:
        """
        Create structured prompt for cross-entity validation extraction.

        Args:
            spec: Complete application specification

        Returns:
            Formatted prompt string
        """
        # Build comprehensive spec summary
        entities = spec.get("entities", [])
        endpoints = spec.get("endpoints", [])
        workflows = spec.get("workflows", [])

        entity_summary = []
        for entity in entities:
            fields = [f"{f.get('name')}:{f.get('type')}" for f in entity.get('fields', [])[:5]]
            entity_summary.append(f"- {entity.get('name')}: {', '.join(fields)}")

        endpoint_summary = [f"- {e.get('method', 'GET')} {e.get('path', '')}" for e in endpoints[:10]]
        workflow_summary = [f"- {w.get('name', '')}" for w in workflows[:5]]

        prompt = f"""Analyze this complete application specification and identify cross-entity validation rules.

ENTITIES:
{chr(10).join(entity_summary)}

ENDPOINTS:
{chr(10).join(endpoint_summary)}

WORKFLOWS:
{chr(10).join(workflow_summary) if workflow_summary else "None defined"}

Identify validations that span multiple entities or workflows:

1. RELATIONSHIP CONSTRAINTS:
   - Foreign key validations (customer_id must reference Customer)
   - Cascade rules (delete order → delete order_items)
   - Referential integrity

2. WORKFLOW STATE TRANSITIONS:
   - Order status: pending → processing → shipped → delivered
   - Payment status: unpaid → paid → refunded
   - Valid state transitions and invalid sequences

3. BUSINESS RULE VALIDATIONS:
   - Stock constraints (order.quantity <= product.stock)
   - Authorization rules (user can only modify own resources)
   - Temporal constraints (end_date > start_date)
   - Aggregation rules (total_price = sum(item_prices))

4. CROSS-ENTITY CONSTRAINTS:
   - One user cannot have duplicate orders with same items
   - Product cannot be deleted if referenced in orders
   - Inventory updates must be atomic with order creation

Return JSON array ONLY (no markdown):
[
  {{
    "entity": "EntityName or WorkflowName",
    "attribute": "related_field or workflow_step",
    "type": "RELATIONSHIP|STATUS_TRANSITION|STOCK_CONSTRAINT|WORKFLOW_CONSTRAINT",
    "condition": "detailed constraint description",
    "error_message": "user-friendly error",
    "confidence": 0.85,
    "rationale": "why this cross-entity validation is critical"
  }}
]

Focus on business-critical cross-entity validations."""

        return prompt

    def _call_llm_with_retry(self, prompt: str) -> Tuple[str, int]:
        """
        Call Claude API with exponential backoff retry logic.

        Args:
            prompt: Formatted prompt string

        Returns:
            Tuple of (response_text, token_count)

        Raises:
            Exception after max retries exhausted
        """
        for attempt in range(self.max_retries):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text
                token_count = message.usage.input_tokens + message.usage.output_tokens

                self.total_tokens_used += token_count
                self.total_api_calls += 1

                return response_text, token_count

            except APITimeoutError as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.warning(f"API timeout, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"API timeout after {self.max_retries} attempts")
                    raise

            except APIError as e:
                if attempt < self.max_retries - 1 and e.status_code >= 500:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.warning(f"API error {e.status_code}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"API error: {e}")
                    raise

            except Exception as e:
                logger.error(f"Unexpected error calling LLM: {e}")
                raise

    def _parse_validation_response(self, response_text: str) -> Tuple[List[ValidationRule], List[float]]:
        """
        Parse LLM response into ValidationRule objects.

        Handles various response formats:
        - Pure JSON array
        - JSON wrapped in markdown code blocks
        - Malformed JSON with recovery attempts

        Args:
            response_text: Raw LLM response

        Returns:
            Tuple of (rules_list, confidence_scores)
        """
        rules = []
        confidences = []

        # Extract JSON from response (may be wrapped in markdown)
        json_text = self._extract_json_from_response(response_text)
        if not json_text:
            logger.warning("No JSON found in LLM response")
            return rules, confidences

        # Parse JSON
        try:
            rules_data = json.loads(json_text)

            if not isinstance(rules_data, list):
                logger.warning(f"Expected JSON array, got {type(rules_data)}")
                return rules, confidences

            # Convert each rule dict to ValidationRule
            for i, rule_dict in enumerate(rules_data):
                try:
                    rule = self._dict_to_validation_rule(rule_dict)
                    if rule:
                        rules.append(rule)
                        confidences.append(rule_dict.get('confidence', 0.8))
                except Exception as e:
                    logger.warning(f"Failed to parse rule {i}: {e}, skipping")
                    continue

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}, attempting fallback parsing")
            # Fallback: try to extract individual objects
            rules, confidences = self._fallback_json_parsing(json_text)

        return rules, confidences

    def _extract_json_from_response(self, response_text: str) -> Optional[str]:
        """
        Extract JSON content from LLM response.

        Handles:
        - Pure JSON
        - JSON in markdown code blocks
        - JSON with surrounding text

        Args:
            response_text: Raw response text

        Returns:
            Extracted JSON string or None
        """
        # Remove markdown code blocks if present
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        code_match = re.search(code_block_pattern, response_text)
        if code_match:
            return code_match.group(1).strip()

        # Try to find JSON array
        json_array_pattern = r'\[\s*\{[\s\S]*\}\s*\]'
        json_match = re.search(json_array_pattern, response_text)
        if json_match:
            return json_match.group(0).strip()

        # Fallback: assume entire response is JSON
        if response_text.strip().startswith('['):
            return response_text.strip()

        return None

    def _dict_to_validation_rule(self, rule_dict: Dict[str, Any]) -> Optional[ValidationRule]:
        """
        Convert parsed dict to ValidationRule object.

        Validates required fields and converts type string to enum.

        Args:
            rule_dict: Parsed rule dictionary

        Returns:
            ValidationRule object or None if invalid
        """
        # Required fields
        entity = rule_dict.get('entity')
        attribute = rule_dict.get('attribute')
        type_str = rule_dict.get('type', '').upper()

        if not entity or not attribute or not type_str:
            logger.warning(f"Missing required fields in rule: {rule_dict}")
            return None

        # Convert type string to enum
        try:
            validation_type = ValidationType[type_str]
        except KeyError:
            logger.warning(f"Invalid validation type: {type_str}, skipping rule")
            return None

        # Create ValidationRule
        return ValidationRule(
            entity=entity,
            attribute=attribute,
            type=validation_type,
            condition=rule_dict.get('condition'),
            error_message=rule_dict.get('error_message')
        )

    def _fallback_json_parsing(self, json_text: str) -> Tuple[List[ValidationRule], List[float]]:
        """
        Fallback parser for malformed JSON.

        Attempts to extract individual JSON objects even if array structure is broken.

        Args:
            json_text: Malformed JSON text

        Returns:
            Tuple of (rules_list, confidence_scores)
        """
        rules = []
        confidences = []

        # Find individual objects
        object_pattern = r'\{[^{}]*\}'
        matches = re.finditer(object_pattern, json_text)

        for match in matches:
            obj_text = match.group(0)
            try:
                rule_dict = json.loads(obj_text)
                rule = self._dict_to_validation_rule(rule_dict)
                if rule:
                    rules.append(rule)
                    confidences.append(rule_dict.get('confidence', 0.7))
            except Exception as e:
                logger.debug(f"Failed to parse object: {e}")
                continue

        if rules:
            logger.info(f"Fallback parsing recovered {len(rules)} rules")

        return rules, confidences
