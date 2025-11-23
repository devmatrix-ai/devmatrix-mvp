"""
Business Logic Extractor

Analyzes specifications and extracts business logic validation rules
that should be included in ValidationModelIR.

Comprehensive extraction of:
- Uniqueness constraints (email, username, etc.)
- Foreign key relationships (customer_id, product_id, etc.)
- Stock/inventory management
- Status transitions and workflows
- Email/format validation
- Range constraints (min/max)
- Required fields and data types
- Business rule patterns from spec text
"""
from typing import List, Dict, Any, Optional
from src.cognitive.ir.validation_model import ValidationRule, ValidationType, ValidationModelIR
import re
import anthropic
import logging

logger = logging.getLogger(__name__)


class BusinessLogicExtractor:
    """Extracts business logic constraints from specifications - Comprehensive."""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-3-5-sonnet-20241022"
        self.validation_patterns = {
            'email': re.compile(r'\bemail\b', re.IGNORECASE),
            'unique': re.compile(r'\bunique\b|\bdistinct\b', re.IGNORECASE),
            'stock': re.compile(r'\bstock\b|\binventory\b|\bquantity\b|\bavailable\b', re.IGNORECASE),
            'status': re.compile(r'\bstatus\b|\bstate\b', re.IGNORECASE),
            'required': re.compile(r'\brequired\b|\bmandatory\b', re.IGNORECASE),
            'reference': re.compile(r'_id$|foreign key|references', re.IGNORECASE),
        }

    def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
        """
        Extract ALL validation rules from specification.
        Multi-stage approach:
        1. Pattern-based extraction (fast, reliable)
        2. LLM-based extraction (comprehensive, flexible)
        3. Relationship inference (FK, cross-entity)
        """
        rules = []

        # Stage 1: Extract from entities (pattern-based)
        if "entities" in spec:
            rules.extend(self._extract_from_entities(spec["entities"]))

        # Stage 2: Extract from field descriptions and constraints
        rules.extend(self._extract_from_field_descriptions(spec.get("entities", [])))

        # Stage 3: Extract from endpoints/workflows
        if "endpoints" in spec or "workflows" in spec:
            rules.extend(self._extract_from_workflows(spec))

        # Stage 4: Use LLM for comprehensive business logic extraction
        try:
            llm_rules = self._extract_with_llm(spec)
            rules.extend(llm_rules)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, continuing with pattern-based rules")

        # Stage 5: Deduplicate rules (same entity+attribute+type = duplicate)
        rules = self._deduplicate_rules(rules)

        return ValidationModelIR(rules=rules)

    def _extract_from_entities(self, entities: List[Dict[str, Any]]) -> List[ValidationRule]:
        """Extract validation rules from entity definitions."""
        rules = []

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type")
                constraints = field.get("constraints", {})

                # Check for required/presence constraints
                if field.get("required") or constraints.get("required"):
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.PRESENCE,
                        error_message=f"{field_name} is required"
                    ))

                # Check for uniqueness constraints (both direct and nested)
                if field.get("unique") or constraints.get("unique"):
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.UNIQUENESS,
                        error_message=f"{field_name} must be unique"
                    ))

                # Check for range constraints (min/max length/value)
                min_length = field.get("min_length") or constraints.get("min_length")
                max_length = field.get("max_length") or constraints.get("max_length")
                minimum = field.get("minimum") or constraints.get("minimum")
                maximum = field.get("maximum") or constraints.get("maximum")

                if min_length or max_length or minimum or maximum:
                    condition_parts = []
                    if min_length is not None:
                        condition_parts.append(f"length >= {min_length}")
                    if max_length is not None:
                        condition_parts.append(f"length <= {max_length}")
                    if minimum is not None:
                        condition_parts.append(f"value >= {minimum}")
                    if maximum is not None:
                        condition_parts.append(f"value <= {maximum}")

                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.RANGE,
                        condition=" AND ".join(condition_parts),
                        error_message=f"{field_name} is out of valid range"
                    ))

                # Check for foreign key constraints
                if field_type == "UUID" and field_name.endswith("_id"):
                    ref_entity = field_name.replace("_id", "")
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.RELATIONSHIP,
                        error_message=f"{ref_entity} with id '{{id}}' not found"
                    ))

                # Check for stock/inventory constraints
                if field_name in ["stock", "quantity", "available"]:
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.STOCK_CONSTRAINT,
                        condition="product.stock >= item.quantity",
                        error_message="Insufficient stock"
                    ))

                # Check for status fields with enums
                if field_name == "status" and "enum" in field:
                    values = field.get("enum", [])
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.STATUS_TRANSITION,
                        condition=f"status in {values}",
                        error_message="Invalid status transition"
                    ))

        return rules

    def _extract_from_workflows(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Extract validation rules from workflows/endpoints."""
        rules = []

        # Check for workflow definitions
        workflows = spec.get("workflows", [])
        endpoints = spec.get("endpoints", [])

        for workflow in workflows:
            name = workflow.get("name")
            steps = workflow.get("steps", [])

            # Workflow sequence is important - validate order
            if len(steps) > 1:
                rules.append(ValidationRule(
                    entity=name,
                    attribute="workflow_step",
                    type=ValidationType.WORKFLOW_CONSTRAINT,
                    condition=f"steps in {[s.get('name') for s in steps]}",
                    error_message=f"Invalid workflow sequence for {name}"
                ))

        return rules

    def _extract_with_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Use LLM to intelligently extract complex business logic rules."""
        prompt = f"""Analyze this application specification and identify business logic validation rules.

Specification:
{self._spec_to_string(spec)}

Return a JSON list of validation rules with this structure:
[
  {{
    "entity": "EntityName",
    "attribute": "field_name",
    "type": "uniqueness|relationship|stock_constraint|status_transition|workflow_constraint",
    "condition": "description or code condition",
    "error_message": "user-friendly error message"
  }}
]

Focus on:
1. Unique constraints (email, username, etc.)
2. Foreign key relationships (references to other entities)
3. Inventory/stock constraints
4. Status transition rules
5. Workflow/process constraints

Return ONLY the JSON array, no other text."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            import json
            rules_data = json.loads(response_text)

            rules = []
            for rule_data in rules_data:
                rules.append(ValidationRule(**rule_data))

            return rules
        except Exception as e:
            # If LLM extraction fails, return empty list
            # The pattern-based extraction above already caught common cases
            return []

    def _extract_from_field_descriptions(self, entities: List[Dict[str, Any]]) -> List[ValidationRule]:
        """Extract validation rules from field descriptions and names."""
        rules = []

        for entity in entities:
            entity_name = entity.get("name")
            for field in entity.get("fields", []):
                field_name = field.get("name")
                field_desc = field.get("description", "").lower()
                field_type = field.get("type", "").lower()

                # Email validation (from name or description)
                if "email" in field_name.lower() or "email" in field_desc:
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="email format",
                        error_message=f"{field_name} must be a valid email address"
                    ))

                # URL validation
                if "url" in field_name.lower() or "url" in field_desc:
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="url format",
                        error_message=f"{field_name} must be a valid URL"
                    ))

                # Phone validation
                if "phone" in field_name.lower() or "phone" in field_desc:
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="phone format",
                        error_message=f"{field_name} must be a valid phone number"
                    ))

                # UUID validation for UUID types
                if field_type == "uuid":
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="uuid v4 format",
                        error_message=f"{field_name} must be a valid UUID"
                    ))

                # Datetime validation
                if field_type == "datetime" or "timestamp" in field_name.lower():
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="ISO 8601 datetime format",
                        error_message=f"{field_name} must be a valid datetime"
                    ))

                # Decimal/currency validation
                if field_type == "decimal" or "price" in field_name.lower() or "amount" in field_name.lower():
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="decimal format with up to 2 decimal places",
                        error_message=f"{field_name} must be a valid decimal number"
                    ))

                # Range constraints from description
                if "min" in field_desc or "maximum" in field_desc or "range" in field_desc:
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.RANGE,
                        condition="extract from description",
                        error_message=f"{field_name} is out of valid range"
                    ))

                # Enum/Status validation
                if "enum" in field or "values" in field:
                    allowed_values = field.get("enum") or field.get("values", [])
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.STATUS_TRANSITION,
                        condition=f"in {allowed_values}",
                        error_message=f"{field_name} must be one of {allowed_values}"
                    ))

        return rules

    def _deduplicate_rules(self, rules: List[ValidationRule]) -> List[ValidationRule]:
        """Remove duplicate rules (same entity+attribute+type)."""
        seen = {}
        deduplicated = []

        for rule in rules:
            key = (rule.entity, rule.attribute, rule.type)
            if key not in seen:
                seen[key] = rule
                deduplicated.append(rule)

        return deduplicated

    def _spec_to_string(self, spec: Dict[str, Any]) -> str:
        """Convert spec to readable string format."""
        result = []

        if "name" in spec:
            result.append(f"App Name: {spec['name']}")

        if "entities" in spec:
            result.append("\nEntities:")
            for entity in spec["entities"]:
                entity_name = entity.get('name')
                result.append(f"  - {entity_name}:")
                for field in entity.get("fields", []):
                    field_name = field.get('name')
                    field_type = field.get('type')
                    field_desc = field.get('description', '')
                    unique_marker = " (unique)" if field.get('unique') else ""
                    req_marker = " (required)" if field.get('required') else ""
                    result.append(f"    - {field_name}: {field_type}{unique_marker}{req_marker}")
                    if field_desc:
                        result.append(f"      Description: {field_desc}")

        if "workflows" in spec:
            result.append("\nWorkflows:")
            for workflow in spec["workflows"]:
                result.append(f"  - {workflow.get('name')}")
                for step in workflow.get("steps", []):
                    result.append(f"    - {step.get('name')}")

        return "\n".join(result)
