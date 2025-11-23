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
- Pattern-based validation (Phase 1)
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from src.cognitive.ir.validation_model import ValidationRule, ValidationType, ValidationModelIR
from src.services.llm_validation_extractor import LLMValidationExtractor
import re
import yaml
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

        # Load validation patterns from YAML (Phase 1)
        self.yaml_patterns = self._load_yaml_patterns()

        # Initialize LLM extractor (Phase 2)
        self.llm_extractor = LLMValidationExtractor()

    def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
        """
        Extract ALL validation rules from specification.
        Comprehensive 8-stage approach with Phase 2 aggressive LLM extraction:
        1. Entity field validation (constraints, types)
        2. Endpoint validation (request/response parameters)
        3. Field type inference (implicit validations)
        4. Constraint inference (CHECK, UNIQUE, FK, schema)
        5. Business rule extraction (explicit rules)
        6. Pattern-based validation (Phase 1 - YAML patterns)
        7. LLM-based extraction (Phase 2 - PRIMARY comprehensive extraction)
        8. Deduplication
        """
        rules = []

        # Stage 1: Extract from entities (pattern-based)
        if "entities" in spec:
            rules.extend(self._extract_from_entities(spec["entities"]))

        # Stage 2: Extract from field descriptions and constraints
        rules.extend(self._extract_from_field_descriptions(spec.get("entities", [])))

        # Stage 3: Extract from endpoints (request/response validation)
        if "endpoints" in spec:
            try:
                rules.extend(self._extract_from_endpoints(spec.get("endpoints", []), spec.get("entities", [])))
            except Exception as e:
                logger.warning(f"Endpoint extraction failed: {e}")

        # Stage 4: Extract from workflows/status transitions
        if "endpoints" in spec or "workflows" in spec:
            rules.extend(self._extract_from_workflows(spec))

        # Stage 5: Extract implicit constraint validations from schema
        if "schema" in spec or "database_schema" in spec:
            rules.extend(self._extract_constraint_validations(spec))

        # Stage 6: Extract explicit business rules
        if "validation_rules" in spec or "business_rules" in spec:
            rules.extend(self._extract_business_rules(spec))

        # Stage 6.5: Extract pattern-based validation (Phase 1 - Pattern Rule System)
        try:
            pattern_rules = self._extract_pattern_rules(spec)
            rules.extend(pattern_rules)
            logger.info(f"Phase 1 pattern-based extraction: {len(pattern_rules)} validations")
        except Exception as e:
            logger.warning(f"Pattern-based extraction failed: {e}, continuing with LLM")

        # Stage 7: Use AGGRESSIVE LLM extraction (Phase 2 - PRIMARY extractor)
        try:
            llm_rules = self.llm_extractor.extract_all_validations(spec)
            rules.extend(llm_rules)
            logger.info(
                f"Phase 2 LLM extraction: {len(llm_rules)} validations, "
                f"{self.llm_extractor.total_tokens_used} tokens, "
                f"{self.llm_extractor.total_api_calls} API calls"
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}, continuing with pattern-based rules only")

        # Stage 8: Deduplicate rules (same entity+attribute+type = duplicate)
        initial_count = len(rules)
        rules = self._deduplicate_rules(rules)
        logger.info(f"Deduplication: {initial_count} → {len(rules)} rules ({initial_count - len(rules)} duplicates removed)")

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

                # String type validation (fallback for basic string fields)
                if field_type == "string" and field_name not in ["description", "notes", "comment"]:
                    # Already covered by more specific rules above
                    pass
                elif field_type == "string" and field_name in ["description", "notes", "comment", "comments", "text"]:
                    # Generic string field - add basic string format validation
                    rules.append(ValidationRule(
                        entity=entity_name,
                        attribute=field_name,
                        type=ValidationType.FORMAT,
                        condition="non-empty string",
                        error_message=f"{field_name} must be a valid string"
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

    def _extract_from_endpoints(self, endpoints: List[Dict[str, Any]], entities: List[Dict[str, Any]] = None) -> List[ValidationRule]:
        """Extract validation rules from API endpoints (request/response parameters)."""
        rules = []
        entities = entities or []

        for endpoint in endpoints:
            endpoint_path = endpoint.get("path", "")
            endpoint_method = endpoint.get("method", "").upper()
            endpoint_entity = endpoint.get("entity") or self._infer_entity_from_path(endpoint_path, entities)

            # Path parameter validation
            if "{" in endpoint_path:
                param_name = endpoint_path.split("{")[1].split("}")[0]
                rules.append(ValidationRule(
                    entity=endpoint_entity or "Endpoint",
                    attribute=f"{endpoint_method}_{param_name}",
                    type=ValidationType.PRESENCE,
                    error_message=f"{param_name} path parameter is required"
                ))
                rules.append(ValidationRule(
                    entity=endpoint_entity or "Endpoint",
                    attribute=f"{endpoint_method}_{param_name}",
                    type=ValidationType.FORMAT,
                    condition="uuid format",
                    error_message=f"{param_name} must be a valid UUID"
                ))

            # Query parameter validation
            if endpoint_method == "GET" and "query_params" in endpoint:
                for param in endpoint.get("query_params", []):
                    param_name = param.get("name")
                    rules.append(ValidationRule(
                        entity=endpoint_entity or "Endpoint",
                        attribute=f"{endpoint_method}_query_{param_name}",
                        type=ValidationType.FORMAT,
                        error_message=f"Query parameter {param_name} has invalid format"
                    ))

            # Request body validation
            if endpoint_method in ["POST", "PUT", "PATCH"]:
                rules.append(ValidationRule(
                    entity=endpoint_entity or "Endpoint",
                    attribute=f"{endpoint_method}_body",
                    type=ValidationType.PRESENCE,
                    error_message=f"Request body is required for {endpoint_method} {endpoint_path}"
                ))

        return rules

    def _extract_constraint_validations(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Extract validation rules from database schema constraints (CHECK, UNIQUE, FK)."""
        rules = []

        schema = spec.get("schema") or spec.get("database_schema") or ""
        if not schema:
            return rules

        # Extract CHECK constraints
        check_pattern = re.compile(r'CHECK\s*\(([^)]+)\)', re.IGNORECASE)
        for match in check_pattern.finditer(str(schema)):
            constraint = match.group(1)
            if "IN" in constraint.upper():
                rules.append(ValidationRule(
                    entity="Database",
                    attribute=constraint[:50],
                    type=ValidationType.STATUS_TRANSITION,
                    condition=constraint,
                    error_message=f"Value violates CHECK constraint: {constraint}"
                ))

        # Extract UNIQUE constraints
        unique_pattern = re.compile(r'UNIQUE\s*\(([^)]+)\)', re.IGNORECASE)
        for match in unique_pattern.finditer(str(schema)):
            field = match.group(1).strip()
            rules.append(ValidationRule(
                entity="Database",
                attribute=field,
                type=ValidationType.UNIQUENESS,
                error_message=f"{field} must be unique"
            ))

        # Extract foreign key constraints
        fk_pattern = re.compile(r'FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(\w+)', re.IGNORECASE)
        for match in fk_pattern.finditer(str(schema)):
            field = match.group(1).strip()
            ref_table = match.group(2).strip()
            rules.append(ValidationRule(
                entity="Database",
                attribute=field,
                type=ValidationType.RELATIONSHIP,
                error_message=f"{field} must reference valid {ref_table} record"
            ))

        return rules

    def _extract_business_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Extract validation rules from explicit business rules section."""
        rules = []

        # Get business rules from different possible fields
        business_rules = spec.get("validation_rules") or spec.get("business_rules") or []

        if isinstance(business_rules, str):
            # Parse string rules
            for i, rule_text in enumerate(business_rules.split("\n")):
                if rule_text.strip():
                    rules.append(ValidationRule(
                        entity="BusinessRule",
                        attribute=f"rule_{i}",
                        type=ValidationType.PRESENCE,
                        condition=rule_text.strip(),
                        error_message=f"Business rule violated: {rule_text.strip()[:100]}"
                    ))
        elif isinstance(business_rules, list):
            # Parse list rules
            for i, rule in enumerate(business_rules):
                if isinstance(rule, dict):
                    rules.append(ValidationRule(
                        entity=rule.get("entity", "BusinessRule"),
                        attribute=rule.get("attribute", f"rule_{i}"),
                        type=ValidationType.PRESENCE,
                        condition=rule.get("description", ""),
                        error_message=rule.get("error", "Business rule violated")
                    ))
                else:
                    rules.append(ValidationRule(
                        entity="BusinessRule",
                        attribute=f"rule_{i}",
                        type=ValidationType.PRESENCE,
                        condition=str(rule),
                        error_message=f"Business rule violated: {str(rule)[:100]}"
                    ))

        return rules

    def _infer_entity_from_path(self, path: str, entities: List[Dict[str, Any]]) -> str:
        """Infer entity name from API endpoint path."""
        # Extract resource name from path (e.g., /todos/{id} -> todos)
        parts = path.strip("/").split("/")
        if parts and parts[0]:
            resource_name = parts[0].rstrip("s")  # Remove trailing 's' for pluralization

            # Try to find matching entity
            for entity in entities:
                entity_name = entity.get("name", "").lower()
                if resource_name.lower() == entity_name.lower():
                    return entity.get("name")

            # Return capitalized resource name if no match found
            return resource_name.capitalize()

        return "Endpoint"

    def _load_yaml_patterns(self) -> Dict[str, Any]:
        """Load validation patterns from YAML file (Phase 1)."""
        try:
            patterns_file = Path(__file__).parent / "validation_patterns.yaml"
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    patterns = yaml.safe_load(f) or {}
                logger.info(f"Loaded validation patterns from {patterns_file}")
                return patterns
            else:
                logger.warning(f"Patterns file not found: {patterns_file}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load YAML patterns: {e}")
            return {}

    def _extract_pattern_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """
        Extract validation rules using pattern matching from validation_patterns.yaml.
        Phase 1: Pattern-based extraction for 30-40% coverage improvement.
        """
        rules = []
        if not self.yaml_patterns:
            return rules

        entities = spec.get("entities", [])
        endpoints = spec.get("endpoints", [])

        # Apply type-based patterns
        type_patterns = self.yaml_patterns.get("type_patterns", {})
        for entity in entities:
            entity_name = entity.get("name", "")
            for field in entity.get("fields", []):
                field_name = field.get("name", "")
                field_type = field.get("type", "")

                # Match against type patterns
                if field_type in type_patterns:
                    type_config = type_patterns[field_type]
                    for validation in type_config.get("validations", []):
                        # Check applies_to_when conditions
                        applies_to_when = validation.get("applies_to_when", [])
                        if applies_to_when:
                            # Check if field has any of the required conditions
                            has_condition = False
                            for condition in applies_to_when:
                                if (field.get(condition) or
                                    field.get("constraints", {}).get(condition)):
                                    has_condition = True
                                    break
                            if not has_condition:
                                continue

                        # Check applies_to field name patterns
                        applies_to = validation.get("applies_to", [])
                        if applies_to:
                            # Check if field name matches any pattern
                            name_matches = False
                            for pattern in applies_to:
                                if self._matches_pattern(field_name, pattern):
                                    name_matches = True
                                    break
                            if not name_matches and applies_to_when:
                                # If applies_to specified but no match, skip
                                continue

                        # Create validation rule
                        val_type = validation.get("type", "")
                        error_msg = validation.get("error_message", "").format(
                            attribute=field_name,
                            entity=entity_name
                        )

                        try:
                            rule = ValidationRule(
                                entity=entity_name,
                                attribute=field_name,
                                type=ValidationType[val_type],
                                condition=validation.get("condition", ""),
                                error_message=error_msg
                            )
                            rules.append(rule)
                        except (KeyError, ValueError) as e:
                            logger.debug(f"Failed to create rule: {e}")

        # Apply semantic patterns
        semantic_patterns = self.yaml_patterns.get("semantic_patterns", {})
        for entity in entities:
            entity_name = entity.get("name", "")
            for field in entity.get("fields", []):
                field_name = field.get("name", "")

                for semantic_name, semantic_config in semantic_patterns.items():
                    pattern = semantic_config.get("pattern", "")
                    if not pattern:
                        continue

                    # Match field name against semantic pattern
                    if not re.search(pattern, field_name, re.IGNORECASE):
                        continue

                    # Apply validations for this semantic pattern
                    for validation in semantic_config.get("validations", []):
                        val_type = validation.get("type", "")
                        error_msg = validation.get("error_message", "").format(
                            attribute=field_name
                        )

                        try:
                            rule = ValidationRule(
                                entity=entity_name,
                                attribute=field_name,
                                type=ValidationType[val_type],
                                condition=validation.get("condition", ""),
                                error_message=error_msg
                            )
                            rules.append(rule)
                        except (KeyError, ValueError) as e:
                            logger.debug(f"Failed to create semantic rule: {e}")

        # Apply endpoint patterns
        endpoint_patterns = self.yaml_patterns.get("endpoint_patterns", {})
        for endpoint in endpoints:
            method = endpoint.get("method", "").upper()
            if method not in endpoint_patterns:
                continue

            path = endpoint.get("path", "")
            endpoint_config = endpoint_patterns[method]
            path_patterns = endpoint_config.get("path_patterns", [])

            # Check if endpoint path matches pattern
            path_matches = False
            for path_pattern in path_patterns:
                if re.match(path_pattern, path):
                    path_matches = True
                    break

            if not path_matches:
                continue

            # Apply validations for this endpoint method
            for validation in endpoint_config.get("validations", []):
                attribute = validation.get("attribute", "")
                # Extract ID parameter from path if present
                id_param_match = re.search(r'\{([^}]+)\}', path)
                id_param = id_param_match.group(1) if id_param_match else "id"

                # Replace placeholders
                attribute = attribute.replace("{id_param}", id_param)
                attribute = attribute.replace("{method}", method)
                attribute = attribute.replace("{path}", path)

                error_msg = validation.get("error_message", "").format(
                    method=method,
                    path=path,
                    id_param=id_param
                )

                val_type = validation.get("type", "")
                try:
                    rule = ValidationRule(
                        entity=f"Endpoint:{method}",
                        attribute=attribute,
                        type=ValidationType[val_type],
                        condition=validation.get("condition", ""),
                        error_message=error_msg
                    )
                    rules.append(rule)
                except (KeyError, ValueError) as e:
                    logger.debug(f"Failed to create endpoint rule: {e}")

        logger.info(f"Pattern-based extraction found {len(rules)} validation rules")
        return rules

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches a pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern.startswith("*"):
            return value.endswith(pattern[1:])
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        return value == pattern
