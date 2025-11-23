"""
Business Logic Extractor

Analyzes specifications and extracts business logic validation rules
that should be included in ValidationModelIR.

Patterns it recognizes:
- unique: email, username
- references: customer_id, product_id (FK constraints)
- stock/inventory: quantity, available
- status transitions: pending -> processing -> completed
- workflows: multi-step sequences
"""
from typing import List, Dict, Any, Optional
from src.cognitive.ir.validation_model import ValidationRule, ValidationType, ValidationModelIR
import re
import anthropic


class BusinessLogicExtractor:
    """Extracts business logic constraints from specifications."""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-3-5-sonnet-20241022"

    def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
        """
        Extract validation rules from specification.
        Uses LLM to intelligently identify business logic constraints.
        """
        rules = []

        # Extract from entities
        if "entities" in spec:
            rules.extend(self._extract_from_entities(spec["entities"]))

        # Extract from endpoints/workflows
        if "endpoints" in spec or "workflows" in spec:
            rules.extend(self._extract_from_workflows(spec))

        # Use LLM for complex business logic extraction
        llm_rules = self._extract_with_llm(spec)
        rules.extend(llm_rules)

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

                # Check for uniqueness constraints
                if constraints.get("unique"):
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.UNIQUENESS,
                        error_message=f"{field_name} must be unique"
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

    def _spec_to_string(self, spec: Dict[str, Any]) -> str:
        """Convert spec to readable string format."""
        result = []

        if "name" in spec:
            result.append(f"App Name: {spec['name']}")

        if "entities" in spec:
            result.append("\nEntities:")
            for entity in spec["entities"]:
                result.append(f"  - {entity.get('name')}:")
                for field in entity.get("fields", []):
                    result.append(f"    - {field.get('name')}: {field.get('type')}")

        if "workflows" in spec:
            result.append("\nWorkflows:")
            for workflow in spec["workflows"]:
                result.append(f"  - {workflow.get('name')}")
                for step in workflow.get("steps", []):
                    result.append(f"    - {step.get('name')}")

        return "\n".join(result)
