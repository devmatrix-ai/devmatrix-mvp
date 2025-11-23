"""
Validation Code Generator

Automatically generates validation logic from ValidationModelIR rules.
Uses LLM when needed for complex custom validations.
"""
from typing import List, Optional, Dict, Any
from src.cognitive.ir.validation_model import ValidationRule, ValidationType, ValidationModelIR
import anthropic


class ValidationCodeGenerator:
    """Generates validation code from validation rules."""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-3-5-sonnet-20241022"

    def generate_validation_code(self, validation_model: ValidationModelIR) -> Dict[str, str]:
        """
        Generate validation code for all rules.
        Returns dict mapping entity names to their validation code.
        """
        validation_code = {}

        # Group rules by entity
        rules_by_entity = self._group_rules_by_entity(validation_model.rules)

        for entity, rules in rules_by_entity.items():
            code_blocks = []

            for rule in rules:
                if rule.type == ValidationType.UNIQUENESS:
                    code = self._generate_uniqueness_validation(rule)
                elif rule.type == ValidationType.RELATIONSHIP:
                    code = self._generate_relationship_validation(rule)
                elif rule.type == ValidationType.STOCK_CONSTRAINT:
                    code = self._generate_stock_validation(rule)
                elif rule.type == ValidationType.STATUS_TRANSITION:
                    code = self._generate_status_transition_validation(rule)
                elif rule.type == ValidationType.WORKFLOW_CONSTRAINT:
                    code = self._generate_workflow_validation(rule)
                elif rule.type == ValidationType.CUSTOM:
                    code = self._generate_custom_validation(rule)
                else:
                    continue

                if code:
                    code_blocks.append(code)

            if code_blocks:
                validation_code[entity] = "\n\n".join(code_blocks)

        return validation_code

    def _group_rules_by_entity(self, rules: List[ValidationRule]) -> Dict[str, List[ValidationRule]]:
        """Group validation rules by entity."""
        grouped = {}
        for rule in rules:
            if rule.entity not in grouped:
                grouped[rule.entity] = []
            grouped[rule.entity].append(rule)
        return grouped

    def _generate_uniqueness_validation(self, rule: ValidationRule) -> str:
        """Generate uniqueness validation code."""
        entity = rule.entity
        attr = rule.attribute
        error_msg = rule.error_message or f"{attr} must be unique"

        # Use snake_case for repository methods
        repo_method = f"get_by_{attr.lower()}"

        return f"""# Validate {attr} uniqueness
existing = await {self._repo_var(entity)}.{repo_method}(data.{attr})
if existing:
    raise ValueError("{error_msg}")"""

    def _generate_relationship_validation(self, rule: ValidationRule) -> str:
        """Generate foreign key relationship validation code."""
        entity = rule.entity
        attr = rule.attribute
        # Extract referenced entity (e.g., "customer_id" -> "customer")
        ref_entity = attr.replace("_id", "").replace("_", " ").title().replace(" ", "")
        error_msg = rule.error_message or f"{ref_entity} with id '{{{attr}}}' not found"

        return f"""# Validate foreign key relationship: {attr} must reference existing {ref_entity}
{ref_entity.lower()}_repo = {ref_entity}Repository(self.db)
{ref_entity.lower()} = await {ref_entity.lower()}_repo.get(data.{attr})
if not {ref_entity.lower()}:
    raise ValueError("{error_msg}")"""

    def _generate_stock_validation(self, rule: ValidationRule) -> str:
        """Generate stock/inventory constraint validation code."""
        entity = rule.entity
        attr = rule.attribute
        error_msg = rule.error_message or f"Insufficient {attr}"
        condition = rule.condition or "product.stock < item.quantity"

        return f"""# Validate stock availability
product_repo = ProductRepository(self.db)
for item in data.items:
    product = await product_repo.get(item.product_id)
    if not product:
        raise ValueError("Product not found")
    if {condition}:
        raise ValueError("{error_msg}")"""

    def _generate_status_transition_validation(self, rule: ValidationRule) -> str:
        """Generate status transition validation code."""
        entity = rule.entity
        attr = rule.attribute
        error_msg = rule.error_message or f"Invalid {attr} transition"
        condition = rule.condition or "new_status not in VALID_TRANSITIONS"

        return f"""# Validate status transition
allowed_transitions = {rule.condition or '["pending", "processing", "completed"]'}
if data.{attr} not in allowed_transitions:
    raise ValueError("{error_msg}")"""

    def _generate_workflow_validation(self, rule: ValidationRule) -> str:
        """Generate workflow constraint validation code."""
        entity = rule.entity
        error_msg = rule.error_message or "Invalid workflow sequence"

        return f"""# Validate workflow constraint
# {error_msg}
# Implementation depends on specific workflow definition
if {rule.condition or 'not self._is_valid_workflow()'}:
    raise ValueError("{error_msg}")"""

    def _generate_custom_validation(self, rule: ValidationRule) -> str:
        """Generate custom validation using LLM when needed."""
        # Use LLM to generate custom validation logic
        prompt = f"""Generate Python async validation code for:
Entity: {rule.entity}
Attribute: {rule.attribute}
Condition: {rule.condition}
Error Message: {rule.error_message}

Return only the validation code, no explanations."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    def _repo_var(self, entity: str) -> str:
        """Get repository variable name for entity."""
        return f"self.repo"

    def inject_validation_into_service(
        self,
        service_code: str,
        entity: str,
        validation_code: str
    ) -> str:
        """
        Inject validation code into service's create method.
        Finds the create method and inserts validation before repository operation.
        """
        # Find the create method
        create_method_start = service_code.find(f"async def create(self,")
        if create_method_start == -1:
            return service_code

        # Find the first "await self.repo.create"
        repo_create_start = service_code.find(
            "await self.repo.create",
            create_method_start
        )

        if repo_create_start == -1:
            return service_code

        # Find the line start (backtrack to previous newline)
        line_start = service_code.rfind("\n", 0, repo_create_start) + 1

        # Insert validation code with proper indentation
        indent = " " * (len(service_code[line_start:repo_create_start]) - len(service_code[line_start:repo_create_start].lstrip()))
        validation_indented = "\n".join([
            indent + line if line.strip() else line
            for line in validation_code.split("\n")
        ])

        result = (
            service_code[:line_start] +
            validation_indented + "\n\n" +
            service_code[line_start:]
        )

        return result
