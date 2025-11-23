"""
Pattern-Based Validation Extractor.

Applies validation patterns from validation_patterns.yaml to specifications
to automatically generate comprehensive validation rules.

Phase 1: Pattern-based extraction for 30-40% coverage improvement.

Author: DevMatrix Team
Date: 2025-11-23
"""
import re
import yaml
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass

from pydantic import ConfigDict

from src.cognitive.ir.validation_model import ValidationRule, ValidationType
from src.cognitive.ir.domain_model import Entity, Attribute, DataType
from src.cognitive.ir.api_model import Endpoint, HttpMethod
from src.observability import StructuredLogger

logger = StructuredLogger("pattern_validator", output_json=False)


@dataclass
class PatternMatch:
    """Represents a matched pattern with confidence score."""
    rule: ValidationRule
    confidence: float
    pattern_source: str


class PatternBasedValidator:
    """
    Extracts validation rules by matching patterns against specification.

    Applies patterns from validation_patterns.yaml based on:
    - Field data types (UUID, String, Integer, DateTime, Boolean, Decimal)
    - Field name semantics (email, password, phone, status, quantity, price)
    - Field constraints (unique, not_null, foreign_key)
    - Endpoint patterns (POST, GET, PUT, DELETE with path analysis)
    - Domain patterns (e-commerce, inventory, user-management, workflow)
    - Implicit patterns (created_at, updated_at, deleted_at, version, is_active)
    """

    def __init__(self, patterns_file: Optional[Path] = None):
        """
        Initialize the pattern validator.

        Args:
            patterns_file: Path to validation_patterns.yaml (default: auto-detect)
        """
        if patterns_file is None:
            # Auto-detect patterns file relative to this module
            patterns_file = Path(__file__).parent / "validation_patterns.yaml"

        self.patterns_file = patterns_file
        self.patterns = self._load_patterns()
        logger.info(f"Loaded validation patterns from {patterns_file}")

    def _load_patterns(self) -> Dict[str, Any]:
        """Load validation patterns from YAML file."""
        try:
            with open(self.patterns_file, 'r') as f:
                patterns = yaml.safe_load(f)
            logger.info(f"Successfully loaded {len(patterns)} pattern categories")
            return patterns
        except Exception as e:
            logger.error(f"Failed to load patterns file: {e}")
            return {}

    def extract_patterns(
        self,
        entities: List[Entity],
        endpoints: List[Endpoint],
        business_rules: Optional[List[Dict[str, Any]]] = None
    ) -> List[ValidationRule]:
        """
        Extract validation rules by matching patterns to specification.

        Args:
            entities: Domain model entities
            endpoints: API endpoints
            business_rules: Optional business rules (currently unused)

        Returns:
            List of ValidationRule objects with deduplication
        """
        all_matches: List[PatternMatch] = []

        # Apply type-based patterns
        all_matches.extend(self._extract_type_patterns(entities))

        # Apply semantic patterns
        all_matches.extend(self._extract_semantic_patterns(entities))

        # Apply constraint patterns
        all_matches.extend(self._extract_constraint_patterns(entities))

        # Apply endpoint patterns
        all_matches.extend(self._extract_endpoint_patterns(endpoints))

        # Apply domain patterns
        all_matches.extend(self._extract_domain_patterns(entities))

        # Apply implicit patterns
        all_matches.extend(self._extract_implicit_patterns(entities))

        # Deduplicate and convert to ValidationRule
        rules = self._deduplicate_rules(all_matches)

        logger.info(f"Extracted {len(rules)} validation rules from {len(all_matches)} matches")
        return rules

    def _extract_type_patterns(self, entities: List[Entity]) -> List[PatternMatch]:
        """Extract validation rules based on field data types."""
        matches: List[PatternMatch] = []
        type_patterns = self.patterns.get("type_patterns", {})

        for entity in entities:
            for field in entity.attributes:
                # Map DataType enum to pattern key
                type_key = self._map_data_type(field.data_type)
                if type_key not in type_patterns:
                    continue

                type_config = type_patterns[type_key]
                validations = type_config.get("validations", [])

                for validation in validations:
                    # Check applies_to pattern (field name matching)
                    applies_to = validation.get("applies_to", [])
                    if applies_to and not self._matches_field_name(field.name, applies_to):
                        continue

                    # Check applies_to_when conditions (constraint matching)
                    applies_to_when = validation.get("applies_to_when", [])
                    if applies_to_when and not self._matches_constraints(field, applies_to_when):
                        continue

                    # Create validation rule
                    rule = self._create_rule(
                        entity=entity.name,
                        attribute=field.name,
                        validation_type=validation["type"],
                        condition=validation.get("condition"),
                        error_message=validation["error_message"].format(attribute=field.name)
                    )

                    confidence = validation.get("confidence", 0.8)
                    matches.append(PatternMatch(
                        rule=rule,
                        confidence=confidence,
                        pattern_source=f"type_patterns.{type_key}"
                    ))

        logger.debug(f"Type patterns: {len(matches)} matches")
        return matches

    def _extract_semantic_patterns(self, entities: List[Entity]) -> List[PatternMatch]:
        """Extract validation rules based on field name semantics."""
        matches: List[PatternMatch] = []
        semantic_patterns = self.patterns.get("semantic_patterns", {})

        for entity in entities:
            for field in entity.attributes:
                for pattern_name, pattern_config in semantic_patterns.items():
                    # Match field name against regex pattern
                    pattern = pattern_config.get("pattern", "")
                    if not re.search(pattern, field.name, re.IGNORECASE):
                        continue

                    # Apply all validations for this semantic pattern
                    validations = pattern_config.get("validations", [])
                    for validation in validations:
                        rule = self._create_rule(
                            entity=entity.name,
                            attribute=field.name,
                            validation_type=validation["type"],
                            condition=validation.get("condition"),
                            error_message=validation["error_message"].format(attribute=field.name)
                        )

                        confidence = validation.get("confidence", 0.8)
                        matches.append(PatternMatch(
                            rule=rule,
                            confidence=confidence,
                            pattern_source=f"semantic_patterns.{pattern_name}"
                        ))

        logger.debug(f"Semantic patterns: {len(matches)} matches")
        return matches

    def _extract_constraint_patterns(self, entities: List[Entity]) -> List[PatternMatch]:
        """Extract validation rules based on field constraints."""
        matches: List[PatternMatch] = []
        constraint_patterns = self.patterns.get("constraint_patterns", {})

        for entity in entities:
            for field in entity.attributes:
                # Check unique constraint
                if field.is_unique:
                    unique_config = constraint_patterns.get("unique", {})
                    applies_to = unique_config.get("applies_to", [])

                    # Apply if field name matches pattern or no pattern specified
                    if not applies_to or self._matches_field_name(field.name, applies_to):
                        rule = self._create_rule(
                            entity=entity.name,
                            attribute=field.name,
                            validation_type=unique_config["validates"],
                            error_message=unique_config["error_message"].format(attribute=field.name)
                        )
                        matches.append(PatternMatch(
                            rule=rule,
                            confidence=unique_config.get("confidence", 0.9),
                            pattern_source="constraint_patterns.unique"
                        ))

                # Check not_null constraint
                if not field.is_nullable:
                    not_null_config = constraint_patterns.get("not_null", {})
                    rule = self._create_rule(
                        entity=entity.name,
                        attribute=field.name,
                        validation_type=not_null_config["validates"],
                        error_message=not_null_config["error_message"].format(attribute=field.name)
                    )
                    matches.append(PatternMatch(
                        rule=rule,
                        confidence=not_null_config.get("confidence", 0.95),
                        pattern_source="constraint_patterns.not_null"
                    ))

                # Check foreign_key constraint (field name ends with _id)
                if field.name.endswith("_id") and field.name != "id":
                    fk_config = constraint_patterns.get("foreign_key", {})
                    related_entity = field.name[:-3].title()  # Convert user_id -> User
                    rule = self._create_rule(
                        entity=entity.name,
                        attribute=field.name,
                        validation_type=fk_config["validates"],
                        error_message=fk_config["error_message"].format(related_entity=related_entity)
                    )
                    matches.append(PatternMatch(
                        rule=rule,
                        confidence=fk_config.get("confidence", 0.9),
                        pattern_source="constraint_patterns.foreign_key"
                    ))

        logger.debug(f"Constraint patterns: {len(matches)} matches")
        return matches

    def _extract_endpoint_patterns(self, endpoints: List[Endpoint]) -> List[PatternMatch]:
        """Extract validation rules based on endpoint patterns."""
        matches: List[PatternMatch] = []
        endpoint_patterns = self.patterns.get("endpoint_patterns", {})

        for endpoint in endpoints:
            method = endpoint.method.value
            if method not in endpoint_patterns:
                continue

            pattern_config = endpoint_patterns[method]
            path_patterns = pattern_config.get("path_patterns", [])

            # Check if endpoint path matches pattern
            path_matches = False
            for path_pattern in path_patterns:
                if re.match(path_pattern, endpoint.path):
                    path_matches = True
                    break

            if not path_matches:
                continue

            # Apply validations for this endpoint type
            validations = pattern_config.get("validations", [])
            for validation in validations:
                # Extract ID parameter from path if present
                id_param_match = re.search(r'\{([^}]+)\}', endpoint.path)
                id_param = id_param_match.group(1) if id_param_match else "id"

                # Replace placeholders in attribute and error message
                attribute = validation["attribute"]
                attribute = attribute.replace("{id_param}", id_param)
                attribute = attribute.replace("{method}", method)
                attribute = attribute.replace("{path}", endpoint.path)

                error_message = validation["error_message"]
                error_message = error_message.replace("{method}", method)
                error_message.replace("{path}", endpoint.path)

                rule = self._create_rule(
                    entity=f"Endpoint:{endpoint.operation_id}",
                    attribute=attribute,
                    validation_type=validation["type"],
                    condition=validation.get("condition"),
                    error_message=error_message
                )

                confidence = validation.get("confidence", 0.8)
                matches.append(PatternMatch(
                    rule=rule,
                    confidence=confidence,
                    pattern_source=f"endpoint_patterns.{method}"
                ))

        logger.debug(f"Endpoint patterns: {len(matches)} matches")
        return matches

    def _extract_domain_patterns(self, entities: List[Entity]) -> List[PatternMatch]:
        """Extract validation rules based on domain patterns."""
        matches: List[PatternMatch] = []
        domain_patterns = self.patterns.get("domain_patterns", {})

        # Detect domain by entity names
        entity_names = {e.name for e in entities}
        detected_domains = self._detect_domains(entity_names, domain_patterns)

        for domain_name in detected_domains:
            domain_config = domain_patterns[domain_name]
            patterns = domain_config.get("patterns", [])

            for entity in entities:
                # Check if entity is in domain's entity list
                if entity.name not in domain_config.get("entities", []):
                    continue

                for pattern in patterns:
                    # Find field matching pattern
                    field_name = pattern.get("field")
                    matching_fields = [f for f in entity.attributes if f.name == field_name]

                    if not matching_fields:
                        continue

                    field = matching_fields[0]
                    rule = self._create_rule(
                        entity=entity.name,
                        attribute=field.name,
                        validation_type=pattern["type"],
                        condition=pattern.get("condition"),
                        error_message=pattern["error_message"]
                    )

                    confidence = pattern.get("confidence", 0.85)
                    matches.append(PatternMatch(
                        rule=rule,
                        confidence=confidence,
                        pattern_source=f"domain_patterns.{domain_name}"
                    ))

        logger.debug(f"Domain patterns: {len(matches)} matches (domains: {detected_domains})")
        return matches

    def _extract_implicit_patterns(self, entities: List[Entity]) -> List[PatternMatch]:
        """Extract validation rules from implicit/conventional field names."""
        matches: List[PatternMatch] = []
        implicit_patterns = self.patterns.get("implicit_patterns", {})

        for entity in entities:
            for field in entity.attributes:
                # Check if field name matches implicit pattern
                if field.name in implicit_patterns:
                    pattern = implicit_patterns[field.name]
                    rule = self._create_rule(
                        entity=entity.name,
                        attribute=field.name,
                        validation_type=pattern["type"],
                        condition=pattern.get("condition"),
                        error_message=pattern["error_message"]
                    )

                    confidence = pattern.get("confidence", 0.9)
                    matches.append(PatternMatch(
                        rule=rule,
                        confidence=confidence,
                        pattern_source=f"implicit_patterns.{field.name}"
                    ))

        logger.debug(f"Implicit patterns: {len(matches)} matches")
        return matches

    def _detect_domains(
        self,
        entity_names: Set[str],
        domain_patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Detect which domain patterns apply based on entity names.

        Returns list of domain names that have at least 50% entity overlap.
        """
        detected = []

        for domain_name, domain_config in domain_patterns.items():
            domain_entities = set(domain_config.get("entities", []))
            overlap = len(entity_names & domain_entities)

            # Domain is detected if at least 50% of domain entities are present
            if overlap >= len(domain_entities) * 0.5:
                detected.append(domain_name)

        return detected

    def _deduplicate_rules(self, matches: List[PatternMatch]) -> List[ValidationRule]:
        """
        Deduplicate validation rules by (entity, attribute, type) key.

        When duplicates exist, keep the one with highest confidence.
        """
        # Group by deduplication key
        by_key: Dict[Tuple[str, str, str], List[PatternMatch]] = defaultdict(list)

        for match in matches:
            key = (match.rule.entity, match.rule.attribute, match.rule.type.value)
            by_key[key].append(match)

        # Keep highest confidence match for each key
        deduplicated: List[ValidationRule] = []
        for key, group in by_key.items():
            best_match = max(group, key=lambda m: m.confidence)
            deduplicated.append(best_match.rule)

            if len(group) > 1:
                logger.debug(
                    f"Deduplicated {len(group)} matches for {key}, "
                    f"kept {best_match.pattern_source} (confidence={best_match.confidence:.2f})"
                )

        return deduplicated

    def _create_rule(
        self,
        entity: str,
        attribute: str,
        validation_type: str,
        condition: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> ValidationRule:
        """Create a ValidationRule from pattern parameters."""
        return ValidationRule(
            entity=entity,
            attribute=attribute,
            type=ValidationType(validation_type.lower()),
            condition=condition,
            error_message=error_message,
            severity="error"
        )

    def _map_data_type(self, data_type: DataType) -> str:
        """Map DataType enum to pattern key."""
        mapping = {
            DataType.UUID: "UUID",
            DataType.STRING: "String",
            DataType.INTEGER: "Integer",
            DataType.FLOAT: "Decimal",
            DataType.BOOLEAN: "Boolean",
            DataType.DATETIME: "DateTime",
        }
        return mapping.get(data_type, "String")

    def _matches_field_name(self, field_name: str, patterns: List[str]) -> bool:
        """
        Check if field name matches any of the provided patterns.

        Patterns can contain wildcards:
        - "id" matches exactly "id"
        - "*_id" matches any field ending with "_id"
        - "is_*" matches any field starting with "is_"
        """
        for pattern in patterns:
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace("*", ".*")
            regex_pattern = f"^{regex_pattern}$"

            if re.match(regex_pattern, field_name, re.IGNORECASE):
                return True

        return False

    def _matches_constraints(self, field: Attribute, constraint_names: List[str]) -> bool:
        """
        Check if field has any of the specified constraints.

        Constraint names: required, primary_key, not_null, minimum, maximum, etc.
        """
        for constraint in constraint_names:
            if constraint == "required" and not field.is_nullable:
                return True
            if constraint == "primary_key" and field.is_primary_key:
                return True
            if constraint == "not_null" and not field.is_nullable:
                return True
            if constraint in field.constraints:
                return True

        return False


# Convenience function for quick usage
def extract_validation_patterns(
    entities: List[Entity],
    endpoints: List[Endpoint],
    business_rules: Optional[List[Dict[str, Any]]] = None
) -> List[ValidationRule]:
    """
    Quick function to extract validation patterns from specification.

    Args:
        entities: Domain model entities
        endpoints: API endpoints
        business_rules: Optional business rules

    Returns:
        List of ValidationRule objects
    """
    validator = PatternBasedValidator()
    return validator.extract_patterns(entities, endpoints, business_rules)
