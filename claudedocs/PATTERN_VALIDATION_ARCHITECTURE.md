# Pattern-Based Validation Scaling Architecture

**Date**: 2025-11-23
**Author**: System Architect
**Goal**: Scale validation coverage from 22/62 (35%) to 62/62 (100%)
**Approach**: Pattern Rule System (Phase 1) with extensibility for Phases 2 & 3

---

## 1. SYSTEM OVERVIEW

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     BusinessLogicExtractor                              │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    EXTRACTION PIPELINE                             │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │                                                                     │  │
│  │  Stage 1: Entity Field Extraction (Pattern-Based)                 │  │
│  │           ↓                                                         │  │
│  │  Stage 2: Field Description Extraction (Semantic)                 │  │
│  │           ↓                                                         │  │
│  │  Stage 3: Endpoint Extraction (HTTP Patterns)                     │  │
│  │           ↓                                                         │  │
│  │  Stage 4: Workflow Extraction (State Machines)                    │  │
│  │           ↓                                                         │  │
│  │  Stage 5: Constraint Extraction (Schema Analysis)                 │  │
│  │           ↓                                                         │  │
│  │  Stage 6: Business Rule Extraction (Explicit Rules)               │  │
│  │           ↓                                                         │  │
│  │  ┌──────────────────────────────────────────────────────────┐     │  │
│  │  │       NEW: Stage 7 - Pattern-Based Validator             │     │  │
│  │  │                                                            │     │  │
│  │  │  ┌─────────────────────────────────────────────────┐     │     │  │
│  │  │  │        PatternMatcher                           │     │     │  │
│  │  │  │  - Type-based patterns                          │     │     │  │
│  │  │  │  - Semantic patterns (email, phone, etc.)       │     │     │  │
│  │  │  │  - Endpoint patterns (POST, GET, etc.)          │     │     │  │
│  │  │  │  - Constraint patterns (unique, not_null)       │     │     │  │
│  │  │  │  - Domain patterns (e-commerce, inventory)      │     │     │  │
│  │  │  │  - Relationship patterns (FK, M2M)              │     │     │  │
│  │  │  │  - Workflow patterns (state machines)           │     │     │  │
│  │  │  │  - Implicit patterns (created_at, etc.)         │     │     │  │
│  │  │  └─────────────────────────────────────────────────┘     │     │  │
│  │  │                        ↓                                  │     │  │
│  │  │  ┌─────────────────────────────────────────────────┐     │     │  │
│  │  │  │     PatternScorer                               │     │     │  │
│  │  │  │  - Confidence scoring                           │     │     │  │
│  │  │  │  - Pattern match ranking                        │     │     │  │
│  │  │  │  - Multi-pattern aggregation                    │     │     │  │
│  │  │  └─────────────────────────────────────────────────┘     │     │  │
│  │  │                        ↓                                  │     │  │
│  │  │  ┌─────────────────────────────────────────────────┐     │     │  │
│  │  │  │    ValidationRuleGenerator                      │     │     │  │
│  │  │  │  - Apply matched patterns                       │     │     │  │
│  │  │  │  - Interpolate error messages                   │     │     │  │
│  │  │  │  - Set confidence levels                        │     │     │  │
│  │  │  └─────────────────────────────────────────────────┘     │     │  │
│  │  └──────────────────────────────────────────────────────────┘     │  │
│  │           ↓                                                         │  │
│  │  Stage 8: LLM-Based Extraction (Fallback/Enhancement)             │  │
│  │           ↓                                                         │  │
│  │  ┌──────────────────────────────────────────────────────────┐     │  │
│  │  │       Stage 9: DEDUPLICATION ENGINE                      │     │  │
│  │  │                                                            │     │  │
│  │  │  Key: (entity, attribute, type, condition_hash)          │     │  │
│  │  │  Strategy: Highest confidence wins                        │     │  │
│  │  │  Merge: Combine error messages, keep best metadata       │     │  │
│  │  └──────────────────────────────────────────────────────────┘     │  │
│  │           ↓                                                         │  │
│  │  Return: ValidationModelIR(rules=[...])                            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Integration Sequence Diagram

```
Spec Input
    │
    ├─► Stage 1-6: Current Extractors
    │       │
    │       ├─► Rules Set A (direct extraction)
    │       │
    ├─► Stage 7: PatternBasedValidator  ← NEW
    │       │
    │       ├─► Load validation_patterns.yaml
    │       │
    │       ├─► PatternMatcher.match_all(spec)
    │       │       │
    │       │       ├─► match_type_patterns(entities)
    │       │       ├─► match_semantic_patterns(fields)
    │       │       ├─► match_endpoint_patterns(endpoints)
    │       │       ├─► match_constraint_patterns(constraints)
    │       │       ├─► match_domain_patterns(entities)
    │       │       ├─► match_relationship_patterns(fields)
    │       │       ├─► match_workflow_patterns(endpoints)
    │       │       └─► match_implicit_patterns(fields)
    │       │
    │       ├─► PatternScorer.score_matches(matches)
    │       │       │
    │       │       └─► Return: [(pattern, confidence), ...]
    │       │
    │       ├─► ValidationRuleGenerator.generate(scored_matches)
    │       │       │
    │       │       └─► Rules Set B (pattern-based)
    │       │
    ├─► Stage 8: LLM Extractor
    │       │
    │       ├─► Rules Set C (LLM-based)
    │       │
    ├─► Stage 9: Deduplicator
    │       │
    │       ├─► Merge Rules A + B + C
    │       │
    │       ├─► Remove duplicates by key
    │       │
    │       ├─► Resolve conflicts (highest confidence)
    │       │
    │       └─► Final Rules Set
    │
    └─► ValidationModelIR(rules=final_rules)
```

---

## 2. COMPONENT INTERFACES

### 2.1 PatternMatcher Component

```python
"""
Pattern matching engine for validation rule detection.
Matches fields, endpoints, and entities to validation patterns from YAML.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import yaml


class PatternType(str, Enum):
    """Types of validation patterns."""
    TYPE_BASED = "type_based"           # Based on field type (UUID, String, etc.)
    SEMANTIC = "semantic"               # Based on field name semantics (email, phone)
    ENDPOINT = "endpoint"               # Based on HTTP endpoint patterns
    CONSTRAINT = "constraint"           # Based on constraints (unique, not_null)
    DOMAIN = "domain"                   # Based on business domain (e-commerce, etc.)
    RELATIONSHIP = "relationship"       # Based on relationships (FK, M2M)
    WORKFLOW = "workflow"               # Based on workflow states
    IMPLICIT = "implicit"               # Based on implicit conventions (created_at)


@dataclass
class PatternMatch:
    """Represents a matched pattern with context."""
    pattern_type: PatternType
    pattern_name: str                   # e.g., "email", "UUID", "unique"
    entity: str
    attribute: str
    validation_type: str                # ValidationType enum value
    condition: Optional[str] = None
    error_message: str = ""
    confidence: float = 0.0             # Base confidence from pattern
    context: Dict[str, Any] = None      # Additional matching context

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class PatternMatcher:
    """
    Matches specification elements to validation patterns.

    Pattern matching strategy:
    1. Load patterns from YAML (cached)
    2. Match each entity/field/endpoint against patterns
    3. Score matches based on specificity and confidence
    4. Return ranked matches for rule generation
    """

    def __init__(self, patterns_file: str = "src/services/validation_patterns.yaml"):
        """
        Initialize pattern matcher.

        Args:
            patterns_file: Path to validation patterns YAML file
        """
        self.patterns_file = patterns_file
        self.patterns: Dict[str, Any] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load and cache patterns from YAML file."""
        with open(self.patterns_file, 'r') as f:
            self.patterns = yaml.safe_load(f)

    def match_all(self, spec: Dict[str, Any]) -> List[PatternMatch]:
        """
        Match all patterns against specification.

        Args:
            spec: Application specification dictionary

        Returns:
            List of all pattern matches with confidence scores
        """
        matches = []

        # Extract entities for matching
        entities = spec.get("entities", [])
        endpoints = spec.get("endpoints", [])

        # Match each pattern type
        matches.extend(self.match_type_patterns(entities))
        matches.extend(self.match_semantic_patterns(entities))
        matches.extend(self.match_endpoint_patterns(endpoints))
        matches.extend(self.match_constraint_patterns(entities))
        matches.extend(self.match_domain_patterns(entities, spec.get("domain")))
        matches.extend(self.match_relationship_patterns(entities))
        matches.extend(self.match_workflow_patterns(entities))
        matches.extend(self.match_implicit_patterns(entities))

        return matches

    def match_type_patterns(self, entities: List[Dict[str, Any]]) -> List[PatternMatch]:
        """
        Match type-based patterns (UUID, String, Integer, etc.).

        Strategy:
        - Check field type attribute
        - Match against type_patterns in YAML
        - Apply all validations for matched type
        - Check applies_to_when conditions

        Returns:
            List of pattern matches for type-based validations
        """
        matches = []
        type_patterns = self.patterns.get("type_patterns", {})

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type", "").lower()

                # Normalize field type (e.g., "string" -> "String")
                normalized_type = field_type.capitalize()

                # Check if type has patterns
                if normalized_type in type_patterns:
                    type_pattern = type_patterns[normalized_type]
                    validations = type_pattern.get("validations", [])

                    for validation in validations:
                        # Check if validation applies
                        if self._validation_applies(field, validation):
                            matches.append(PatternMatch(
                                pattern_type=PatternType.TYPE_BASED,
                                pattern_name=normalized_type,
                                entity=entity_name,
                                attribute=field_name,
                                validation_type=validation.get("type"),
                                condition=validation.get("condition"),
                                error_message=self._interpolate_message(
                                    validation.get("error_message", ""),
                                    {"attribute": field_name, **field}
                                ),
                                confidence=validation.get("confidence", 0.7),
                                context={
                                    "field_type": field_type,
                                    "pattern_description": type_pattern.get("description"),
                                    "applies_to": validation.get("applies_to", []),
                                    "applies_to_when": validation.get("applies_to_when", [])
                                }
                            ))

        return matches

    def match_semantic_patterns(self, entities: List[Dict[str, Any]]) -> List[PatternMatch]:
        """
        Match semantic patterns (email, phone, password, etc.).

        Strategy:
        - Check field name against semantic regex patterns
        - Match patterns like "email", "phone", "password"
        - Apply all validations for matched semantic type

        Returns:
            List of pattern matches for semantic validations
        """
        matches = []
        semantic_patterns = self.patterns.get("semantic_patterns", {})

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            for field in fields:
                field_name = field.get("name", "").lower()

                # Check each semantic pattern
                for pattern_name, pattern_config in semantic_patterns.items():
                    pattern_regex = pattern_config.get("pattern", "")

                    # Check if field name matches pattern
                    if re.search(pattern_regex, field_name, re.IGNORECASE):
                        validations = pattern_config.get("validations", [])

                        for validation in validations:
                            matches.append(PatternMatch(
                                pattern_type=PatternType.SEMANTIC,
                                pattern_name=pattern_name,
                                entity=entity_name,
                                attribute=field.get("name"),
                                validation_type=validation.get("type"),
                                condition=validation.get("condition"),
                                error_message=self._interpolate_message(
                                    validation.get("error_message", ""),
                                    {"attribute": field.get("name")}
                                ),
                                confidence=validation.get("confidence", 0.8),
                                context={
                                    "pattern_description": pattern_config.get("description"),
                                    "pattern_regex": pattern_regex,
                                    "field_name": field_name
                                }
                            ))

        return matches

    def match_endpoint_patterns(self, endpoints: List[Dict[str, Any]]) -> List[PatternMatch]:
        """
        Match endpoint patterns (POST, GET, PUT, DELETE).

        Strategy:
        - Check HTTP method (POST, GET, etc.)
        - Match path pattern against regex
        - Apply method-specific validations

        Returns:
            List of pattern matches for endpoint validations
        """
        matches = []
        endpoint_patterns = self.patterns.get("endpoint_patterns", {})

        for endpoint in endpoints:
            method = endpoint.get("method", "").upper()
            path = endpoint.get("path", "")
            entity = endpoint.get("entity", "Endpoint")

            # Check if method has patterns
            if method in endpoint_patterns:
                method_pattern = endpoint_patterns[method]
                path_patterns = method_pattern.get("path_patterns", [])

                # Check if path matches any pattern
                path_matches = any(
                    re.match(p, path) for p in path_patterns
                )

                if path_matches or not path_patterns:  # Apply if pattern matches or no pattern specified
                    validations = method_pattern.get("validations", [])

                    for validation in validations:
                        # Extract ID parameter from path if present
                        id_param = self._extract_id_param(path)

                        # Interpolate attribute (e.g., {id_param} -> actual param name)
                        attribute = validation.get("attribute", "").replace("{id_param}", id_param)

                        matches.append(PatternMatch(
                            pattern_type=PatternType.ENDPOINT,
                            pattern_name=method,
                            entity=entity,
                            attribute=attribute,
                            validation_type=validation.get("type"),
                            condition=validation.get("condition"),
                            error_message=self._interpolate_message(
                                validation.get("error_message", ""),
                                {"method": method, "path": path, id_param: id_param}
                            ),
                            confidence=validation.get("confidence", 0.85),
                            context={
                                "method": method,
                                "path": path,
                                "path_patterns": path_patterns
                            }
                        ))

        return matches

    def match_constraint_patterns(self, entities: List[Dict[str, Any]]) -> List[PatternMatch]:
        """Match constraint patterns (unique, not_null, foreign_key, check)."""
        matches = []
        constraint_patterns = self.patterns.get("constraint_patterns", {})

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            for field in fields:
                field_name = field.get("name")
                constraints = field.get("constraints", {})

                # Check each constraint pattern
                for constraint_name, constraint_pattern in constraint_patterns.items():
                    applies_to = constraint_pattern.get("applies_to", [])

                    # Check if field has this constraint
                    has_constraint = (
                        constraints.get(constraint_name) or
                        field.get(constraint_name) or
                        self._field_matches_constraint(field_name, applies_to)
                    )

                    if has_constraint:
                        matches.append(PatternMatch(
                            pattern_type=PatternType.CONSTRAINT,
                            pattern_name=constraint_name,
                            entity=entity_name,
                            attribute=field_name,
                            validation_type=constraint_pattern.get("validates"),
                            condition=constraint_pattern.get("condition"),
                            error_message=self._interpolate_message(
                                constraint_pattern.get("error_message", ""),
                                {"attribute": field_name}
                            ),
                            confidence=constraint_pattern.get("confidence", 0.9),
                            context={
                                "constraint_name": constraint_name,
                                "description": constraint_pattern.get("description")
                            }
                        ))

        return matches

    def match_domain_patterns(
        self,
        entities: List[Dict[str, Any]],
        domain: Optional[str] = None
    ) -> List[PatternMatch]:
        """Match domain-specific patterns (e-commerce, inventory, user-management)."""
        matches = []
        domain_patterns = self.patterns.get("domain_patterns", {})

        # Auto-detect domain if not provided
        if not domain:
            domain = self._detect_domain(entities)

        # Check if domain has patterns
        if domain and domain in domain_patterns:
            domain_pattern = domain_patterns[domain]
            domain_entities = domain_pattern.get("entities", [])
            domain_validations = domain_pattern.get("patterns", [])

            for entity in entities:
                entity_name = entity.get("name")

                # Check if entity is in domain
                if entity_name in domain_entities:
                    fields = entity.get("fields", [])

                    for validation in domain_validations:
                        field_pattern = validation.get("field")

                        # Find matching fields
                        for field in fields:
                            field_name = field.get("name")

                            if re.search(field_pattern, field_name, re.IGNORECASE):
                                matches.append(PatternMatch(
                                    pattern_type=PatternType.DOMAIN,
                                    pattern_name=domain,
                                    entity=entity_name,
                                    attribute=field_name,
                                    validation_type=validation.get("type"),
                                    condition=validation.get("condition"),
                                    error_message=validation.get("error_message", ""),
                                    confidence=validation.get("confidence", 0.85),
                                    context={
                                        "domain": domain,
                                        "domain_entities": domain_entities
                                    }
                                ))

        return matches

    def match_relationship_patterns(self, entities: List[Dict[str, Any]]) -> List[PatternMatch]:
        """Match relationship patterns (one_to_many, many_to_one, many_to_many)."""
        matches = []
        relationship_patterns = self.patterns.get("relationship_patterns", {})

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            for field in fields:
                field_name = field.get("name")

                # Check each relationship pattern
                for rel_name, rel_pattern in relationship_patterns.items():
                    pattern_regex = rel_pattern.get("pattern", "")

                    # Check if field matches relationship pattern
                    if re.search(pattern_regex, field_name, re.IGNORECASE):
                        matches.append(PatternMatch(
                            pattern_type=PatternType.RELATIONSHIP,
                            pattern_name=rel_name,
                            entity=entity_name,
                            attribute=field_name,
                            validation_type=rel_pattern.get("validates"),
                            condition=None,
                            error_message=self._interpolate_message(
                                rel_pattern.get("error_message", ""),
                                {
                                    "attribute": field_name,
                                    "related_entity": self._extract_related_entity(field_name)
                                }
                            ),
                            confidence=rel_pattern.get("confidence", 0.85),
                            context={
                                "relationship_type": rel_name,
                                "description": rel_pattern.get("description")
                            }
                        ))

        return matches

    def match_workflow_patterns(self, entities: List[Dict[str, Any]]) -> List[PatternMatch]:
        """Match workflow state patterns (order_workflow, user_workflow, task_workflow)."""
        matches = []
        workflow_patterns = self.patterns.get("workflow_patterns", {})

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            # Look for status/state fields
            for field in fields:
                field_name = field.get("name", "").lower()

                if "status" in field_name or "state" in field_name:
                    # Check for enum values
                    enum_values = field.get("enum", [])

                    if enum_values:
                        # Try to match workflow type
                        workflow_type = self._detect_workflow_type(entity_name, enum_values)

                        if workflow_type and workflow_type in workflow_patterns:
                            workflow = workflow_patterns[workflow_type]
                            valid_states = workflow.get("states", [])

                            matches.append(PatternMatch(
                                pattern_type=PatternType.WORKFLOW,
                                pattern_name=workflow_type,
                                entity=entity_name,
                                attribute=field.get("name"),
                                validation_type="STATUS_TRANSITION",
                                condition=f"status in {valid_states}",
                                error_message=f"Invalid {field.get('name')} transition",
                                confidence=0.9,
                                context={
                                    "workflow_type": workflow_type,
                                    "valid_states": valid_states,
                                    "transitions": workflow.get("validations", [])
                                }
                            ))

        return matches

    def match_implicit_patterns(self, entities: List[Dict[str, Any]]) -> List[PatternMatch]:
        """Match implicit patterns (created_at, updated_at, is_active, etc.)."""
        matches = []
        implicit_patterns = self.patterns.get("implicit_patterns", {})

        for entity in entities:
            entity_name = entity.get("name")
            fields = entity.get("fields", [])

            for field in fields:
                field_name = field.get("name", "").lower()

                # Check each implicit pattern
                for pattern_name, pattern_config in implicit_patterns.items():
                    # Exact match on field name
                    if field_name == pattern_name.lower():
                        matches.append(PatternMatch(
                            pattern_type=PatternType.IMPLICIT,
                            pattern_name=pattern_name,
                            entity=entity_name,
                            attribute=field.get("name"),
                            validation_type=pattern_config.get("type"),
                            condition=pattern_config.get("condition"),
                            error_message=pattern_config.get("error_message", ""),
                            confidence=pattern_config.get("confidence", 0.9),
                            context={
                                "implicit_convention": pattern_name
                            }
                        ))

        return matches

    # Helper methods

    def _validation_applies(self, field: Dict[str, Any], validation: Dict[str, Any]) -> bool:
        """Check if validation applies to field based on conditions."""
        # Check applies_to conditions (field name patterns)
        applies_to = validation.get("applies_to", [])
        if applies_to:
            field_name = field.get("name", "")
            matched = any(
                self._field_matches_pattern(field_name, pattern)
                for pattern in applies_to
            )
            if not matched:
                return False

        # Check applies_to_when conditions (field attributes)
        applies_to_when = validation.get("applies_to_when", [])
        if applies_to_when:
            matched = any(
                field.get(attr) or field.get("constraints", {}).get(attr)
                for attr in applies_to_when
            )
            if not matched:
                return False

        return True

    def _field_matches_pattern(self, field_name: str, pattern: str) -> bool:
        """Check if field name matches pattern (supports wildcards)."""
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", field_name, re.IGNORECASE))

    def _field_matches_constraint(self, field_name: str, applies_to: List[str]) -> bool:
        """Check if field name matches constraint pattern."""
        return any(
            self._field_matches_pattern(field_name, pattern)
            for pattern in applies_to
        )

    def _interpolate_message(self, message: str, context: Dict[str, Any]) -> str:
        """Interpolate placeholders in error message."""
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in message:
                message = message.replace(placeholder, str(value))
        return message

    def _extract_id_param(self, path: str) -> str:
        """Extract ID parameter from path."""
        match = re.search(r'\{([^}]+)\}', path)
        return match.group(1) if match else "id"

    def _extract_related_entity(self, field_name: str) -> str:
        """Extract related entity name from field (e.g., 'customer_id' -> 'customer')."""
        return field_name.replace("_id", "").replace("_ids", "")

    def _detect_domain(self, entities: List[Dict[str, Any]]) -> Optional[str]:
        """Auto-detect domain from entity names."""
        entity_names = {e.get("name", "").lower() for e in entities}

        # E-commerce detection
        if {"product", "order", "orderitem"} & entity_names:
            return "e-commerce"

        # Inventory detection
        if {"inventoryitem", "stocklevel", "movement"} & entity_names:
            return "inventory"

        # User management detection
        if {"user", "role", "permission"} & entity_names:
            return "user-management"

        # Workflow detection
        if {"task", "workflowstate", "transition"} & entity_names:
            return "workflow"

        return None

    def _detect_workflow_type(self, entity_name: str, enum_values: List[str]) -> Optional[str]:
        """Detect workflow type from entity name and status values."""
        entity_lower = entity_name.lower()
        enum_set = {v.lower() for v in enum_values}

        # Order workflow
        if "order" in entity_lower and {"pending", "confirmed", "shipped"} & enum_set:
            return "order_workflow"

        # User workflow
        if "user" in entity_lower and {"active", "inactive", "suspended"} & enum_set:
            return "user_workflow"

        # Task workflow
        if "task" in entity_lower and {"todo", "in_progress", "done"} & enum_set:
            return "task_workflow"

        return None
```

### 2.2 PatternScorer Component

```python
"""
Scoring engine for pattern matches.
Ranks pattern matches by confidence and specificity.
"""

from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ScoredMatch:
    """Pattern match with aggregated score."""
    match: PatternMatch
    final_score: float          # Aggregated confidence score
    specificity: float          # How specific the match is
    pattern_count: int          # How many patterns matched this field

    def __lt__(self, other):
        """Enable sorting by final_score (descending)."""
        return self.final_score > other.final_score


class PatternScorer:
    """
    Scores and ranks pattern matches.

    Scoring algorithm:
    1. Base confidence from pattern definition
    2. Specificity bonus (exact match > pattern match > wildcard)
    3. Pattern type weighting (semantic > type > implicit)
    4. Multi-pattern aggregation (multiple patterns = higher confidence)
    """

    PATTERN_TYPE_WEIGHTS = {
        PatternType.SEMANTIC: 1.2,      # Highest: email, phone clearly indicate validation
        PatternType.CONSTRAINT: 1.15,   # High: explicit constraints
        PatternType.DOMAIN: 1.1,        # High: domain-specific rules
        PatternType.TYPE_BASED: 1.0,    # Baseline: type-based patterns
        PatternType.RELATIONSHIP: 1.0,  # Baseline: relationship patterns
        PatternType.ENDPOINT: 0.95,     # Slightly lower: endpoint patterns
        PatternType.WORKFLOW: 0.95,     # Slightly lower: workflow patterns
        PatternType.IMPLICIT: 0.9,      # Lower: implicit conventions
    }

    def score_matches(self, matches: List[PatternMatch]) -> List[ScoredMatch]:
        """
        Score and rank all pattern matches.

        Args:
            matches: List of raw pattern matches

        Returns:
            List of scored matches, sorted by final_score (descending)
        """
        # Group matches by (entity, attribute) for multi-pattern analysis
        grouped = self._group_by_field(matches)

        scored = []
        for (entity, attribute), field_matches in grouped.items():
            # Score each match
            for match in field_matches:
                base_confidence = match.confidence
                specificity = self._calculate_specificity(match)
                type_weight = self.PATTERN_TYPE_WEIGHTS.get(match.pattern_type, 1.0)
                multi_pattern_bonus = self._calculate_multi_pattern_bonus(field_matches)

                # Final score: base * specificity * type_weight * multi_pattern_bonus
                final_score = base_confidence * specificity * type_weight * multi_pattern_bonus

                # Clamp to [0.0, 1.0]
                final_score = min(1.0, max(0.0, final_score))

                scored.append(ScoredMatch(
                    match=match,
                    final_score=final_score,
                    specificity=specificity,
                    pattern_count=len(field_matches)
                ))

        # Sort by final_score descending
        scored.sort()

        return scored

    def _group_by_field(
        self,
        matches: List[PatternMatch]
    ) -> Dict[Tuple[str, str], List[PatternMatch]]:
        """Group matches by (entity, attribute) for aggregation."""
        grouped = {}
        for match in matches:
            key = (match.entity, match.attribute)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(match)
        return grouped

    def _calculate_specificity(self, match: PatternMatch) -> float:
        """
        Calculate specificity score for match.

        Specificity levels:
        - Exact field name match (e.g., "email"): 1.2
        - Semantic pattern match (e.g., "user_email" matches "email"): 1.1
        - Type-based match (e.g., String type): 1.0
        - Wildcard match (e.g., "*_id"): 0.9
        """
        context = match.context or {}

        # Semantic patterns with exact regex match
        if match.pattern_type == PatternType.SEMANTIC:
            pattern_regex = context.get("pattern_regex", "")
            if pattern_regex and "^" in pattern_regex and "$" in pattern_regex:
                return 1.2  # Exact match
            return 1.1  # Pattern match

        # Constraint patterns (explicit constraints)
        if match.pattern_type == PatternType.CONSTRAINT:
            return 1.15

        # Implicit patterns (exact field name match)
        if match.pattern_type == PatternType.IMPLICIT:
            return 1.1

        # Type-based patterns
        if match.pattern_type == PatternType.TYPE_BASED:
            applies_to = context.get("applies_to", [])
            if applies_to and "*" not in str(applies_to):
                return 1.05  # Specific field names
            return 1.0  # Type only

        # Endpoint patterns
        if match.pattern_type == PatternType.ENDPOINT:
            path_patterns = context.get("path_patterns", [])
            if path_patterns:
                return 1.05  # Specific path pattern
            return 1.0  # Method only

        # Default
        return 1.0

    def _calculate_multi_pattern_bonus(self, field_matches: List[PatternMatch]) -> float:
        """
        Calculate bonus for fields matched by multiple patterns.

        Strategy:
        - 1 pattern: 1.0 (no bonus)
        - 2 patterns: 1.05 (5% bonus)
        - 3+ patterns: 1.1 (10% bonus, capped)

        Rationale: Multiple independent patterns agreeing increases confidence
        """
        pattern_count = len(field_matches)

        if pattern_count == 1:
            return 1.0
        elif pattern_count == 2:
            return 1.05
        else:
            return 1.1  # Capped at 10%
```

### 2.3 ValidationRuleGenerator Component

```python
"""
Generates ValidationRule objects from scored pattern matches.
"""

from typing import List
from src.cognitive.ir.validation_model import ValidationRule, ValidationType


class ValidationRuleGenerator:
    """
    Generates ValidationRule objects from pattern matches.

    Strategy:
    1. Take scored matches
    2. Convert to ValidationRule objects
    3. Set confidence levels
    4. Interpolate error messages
    """

    def generate(self, scored_matches: List[ScoredMatch]) -> List[ValidationRule]:
        """
        Generate validation rules from scored matches.

        Args:
            scored_matches: List of scored pattern matches

        Returns:
            List of ValidationRule objects
        """
        rules = []

        for scored in scored_matches:
            match = scored.match

            # Convert validation_type string to ValidationType enum
            try:
                validation_type = ValidationType(match.validation_type.lower())
            except ValueError:
                # Skip if invalid validation type
                continue

            # Create ValidationRule
            rule = ValidationRule(
                entity=match.entity,
                attribute=match.attribute,
                type=validation_type,
                condition=match.condition,
                error_message=match.error_message or self._default_error_message(
                    match.entity,
                    match.attribute,
                    validation_type
                ),
                severity="error"
            )

            # Add metadata for tracking (optional, if ValidationRule supports it)
            # rule.metadata = {
            #     "pattern_type": match.pattern_type,
            #     "pattern_name": match.pattern_name,
            #     "confidence": scored.final_score,
            #     "specificity": scored.specificity,
            # }

            rules.append(rule)

        return rules

    def _default_error_message(
        self,
        entity: str,
        attribute: str,
        validation_type: ValidationType
    ) -> str:
        """Generate default error message if not provided."""
        messages = {
            ValidationType.FORMAT: f"{attribute} has invalid format",
            ValidationType.RANGE: f"{attribute} is out of valid range",
            ValidationType.PRESENCE: f"{attribute} is required",
            ValidationType.UNIQUENESS: f"{attribute} must be unique",
            ValidationType.RELATIONSHIP: f"Invalid {attribute} reference",
            ValidationType.STOCK_CONSTRAINT: f"Insufficient {attribute}",
            ValidationType.STATUS_TRANSITION: f"Invalid {attribute} transition",
            ValidationType.WORKFLOW_CONSTRAINT: f"Invalid workflow state",
        }
        return messages.get(validation_type, f"{attribute} validation failed")
```

### 2.4 PatternBasedValidator (Main Orchestrator)

```python
"""
Pattern-based validation rule extractor.
Orchestrates PatternMatcher, PatternScorer, and ValidationRuleGenerator.
"""

from typing import Dict, Any, List
from src.cognitive.ir.validation_model import ValidationRule


class PatternBasedValidator:
    """
    Orchestrates pattern-based validation rule extraction.

    Pipeline:
    1. PatternMatcher: Match spec against patterns
    2. PatternScorer: Score and rank matches
    3. ValidationRuleGenerator: Generate ValidationRule objects
    """

    def __init__(self, patterns_file: str = "src/services/validation_patterns.yaml"):
        """Initialize pattern-based validator."""
        self.matcher = PatternMatcher(patterns_file)
        self.scorer = PatternScorer()
        self.generator = ValidationRuleGenerator()

    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """
        Extract validation rules from specification using patterns.

        Args:
            spec: Application specification dictionary

        Returns:
            List of ValidationRule objects from pattern matches
        """
        # Step 1: Match patterns
        matches = self.matcher.match_all(spec)

        # Step 2: Score matches
        scored_matches = self.scorer.score_matches(matches)

        # Step 3: Generate rules
        rules = self.generator.generate(scored_matches)

        return rules
```

---

## 3. INTEGRATION INTO BUSINESSLOGICEXTRACTOR

### Modified Pipeline

```python
# In BusinessLogicExtractor.extract_validation_rules()

def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
    """
    Extract ALL validation rules from specification.
    Enhanced with pattern-based extraction (Phase 1).
    """
    rules = []

    # Stage 1-6: Current extractors (unchanged)
    if "entities" in spec:
        rules.extend(self._extract_from_entities(spec["entities"]))
    rules.extend(self._extract_from_field_descriptions(spec.get("entities", [])))
    if "endpoints" in spec:
        try:
            rules.extend(self._extract_from_endpoints(spec.get("endpoints", []), spec.get("entities", [])))
        except Exception as e:
            logger.warning(f"Endpoint extraction failed: {e}")
    if "endpoints" in spec or "workflows" in spec:
        rules.extend(self._extract_from_workflows(spec))
    if "schema" in spec or "database_schema" in spec:
        rules.extend(self._extract_constraint_validations(spec))
    if "validation_rules" in spec or "business_rules" in spec:
        rules.extend(self._extract_business_rules(spec))

    # ✅ NEW: Stage 7 - Pattern-Based Extraction
    try:
        pattern_validator = PatternBasedValidator()
        pattern_rules = pattern_validator.extract_rules(spec)
        rules.extend(pattern_rules)
        logger.info(f"Pattern-based extraction added {len(pattern_rules)} rules")
    except Exception as e:
        logger.warning(f"Pattern-based extraction failed: {e}")

    # Stage 8: LLM-Based Extraction (unchanged)
    try:
        llm_rules = self._extract_with_llm(spec)
        rules.extend(llm_rules)
    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}, continuing with pattern-based rules")

    # ✅ ENHANCED: Stage 9 - Deduplication with confidence-based resolution
    rules = self._deduplicate_rules_advanced(rules)

    return ValidationModelIR(rules=rules)
```

---

## 4. DEDUPLICATION STRATEGY

### Deduplication Algorithm

```python
def _deduplicate_rules_advanced(self, rules: List[ValidationRule]) -> List[ValidationRule]:
    """
    Advanced deduplication with confidence-based conflict resolution.

    Deduplication key: (entity, attribute, type, condition_hash)

    Conflict resolution:
    - If multiple rules have same key, keep the one with highest confidence
    - Merge error messages (combine if different, keep best if similar)
    - Preserve metadata from highest-confidence rule

    Args:
        rules: List of validation rules (possibly with duplicates)

    Returns:
        Deduplicated list of validation rules
    """
    # Group rules by deduplication key
    grouped = {}

    for rule in rules:
        # Create deduplication key
        condition_hash = hash(rule.condition) if rule.condition else 0
        key = (rule.entity, rule.attribute, rule.type, condition_hash)

        if key not in grouped:
            grouped[key] = []
        grouped[key].append(rule)

    # Resolve conflicts for each group
    deduplicated = []

    for key, rule_group in grouped.items():
        if len(rule_group) == 1:
            # No conflict, keep as-is
            deduplicated.append(rule_group[0])
        else:
            # Conflict: merge rules
            merged = self._merge_rules(rule_group)
            deduplicated.append(merged)

    return deduplicated


def _merge_rules(self, rule_group: List[ValidationRule]) -> ValidationRule:
    """
    Merge multiple rules with same key.

    Strategy:
    - Keep rule with best metadata (if available)
    - Combine error messages if different
    - Prefer more specific condition
    """
    # Sort by confidence (if metadata available) or condition specificity
    sorted_rules = sorted(
        rule_group,
        key=lambda r: (
            r.metadata.get("confidence", 0.5) if hasattr(r, "metadata") else 0.5,
            len(r.condition or "")
        ),
        reverse=True
    )

    # Take best rule as base
    best_rule = sorted_rules[0]

    # Combine error messages if different
    error_messages = {r.error_message for r in rule_group if r.error_message}
    if len(error_messages) > 1:
        # Multiple different error messages - combine
        combined_message = " OR ".join(error_messages)
        best_rule.error_message = combined_message

    return best_rule
```

### Deduplication Key Design

```python
# Deduplication key components:
#
# 1. entity: EntityName (e.g., "User", "Product")
# 2. attribute: field_name (e.g., "email", "price")
# 3. type: ValidationType (e.g., UNIQUENESS, FORMAT)
# 4. condition_hash: hash(condition) to differentiate similar validations
#
# Example duplicates:
#
# Rule A (from entity extraction):
#   entity="User", attribute="email", type=UNIQUENESS, condition=None
#
# Rule B (from pattern matching):
#   entity="User", attribute="email", type=UNIQUENESS, condition=None
#
# Key: ("User", "email", UNIQUENESS, hash(None)) - SAME KEY = DUPLICATE
#
# Conflict resolution: Keep rule with highest confidence score
```

---

## 5. SCALABILITY & EXTENSIBILITY

### Plugin Architecture for Phase 2 & 3

```python
"""
Extension points for future phases.

Phase 2: Aggressive LLM Extraction
Phase 3: Graph-Based Inference
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ValidationExtractor(ABC):
    """
    Abstract base class for validation extractors.

    Allows plugging in new extraction strategies without modifying core pipeline.
    """

    @abstractmethod
    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Extract validation rules from specification."""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """
        Return extraction priority (higher = runs earlier).

        Priority order:
        - 100: Pattern-based (Phase 1)
        - 80: Aggressive LLM (Phase 2)
        - 60: Graph inference (Phase 3)
        - 40: Fallback LLM
        """
        pass


class PatternBasedExtractor(ValidationExtractor):
    """Phase 1: Pattern-based extraction."""

    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        validator = PatternBasedValidator()
        return validator.extract_rules(spec)

    def get_priority(self) -> int:
        return 100


class AggressiveLLMExtractor(ValidationExtractor):
    """
    Phase 2: Aggressive LLM extraction with structured prompting.

    TODO: Implement in Phase 2
    - Few-shot examples from pattern matches
    - Structured JSON schema output
    - Confidence scoring
    - Multiple LLM calls for coverage
    """

    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        # Phase 2 implementation
        raise NotImplementedError("Phase 2: Aggressive LLM extraction")

    def get_priority(self) -> int:
        return 80


class GraphInferenceExtractor(ValidationExtractor):
    """
    Phase 3: Graph-based inference from entity relationships.

    TODO: Implement in Phase 3
    - Build entity relationship graph
    - Infer validation rules from graph structure
    - Transitive closure analysis
    - Constraint propagation
    """

    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        # Phase 3 implementation
        raise NotImplementedError("Phase 3: Graph-based inference")

    def get_priority(self) -> int:
        return 60


class ExtractorRegistry:
    """
    Registry for validation extractors.

    Allows dynamic registration and execution of extractors.
    """

    def __init__(self):
        self.extractors: List[ValidationExtractor] = []

    def register(self, extractor: ValidationExtractor):
        """Register a new extractor."""
        self.extractors.append(extractor)
        # Sort by priority (descending)
        self.extractors.sort(key=lambda e: e.get_priority(), reverse=True)

    def extract_all(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        """Run all registered extractors in priority order."""
        all_rules = []

        for extractor in self.extractors:
            try:
                rules = extractor.extract_rules(spec)
                all_rules.extend(rules)
                logger.info(f"{extractor.__class__.__name__} extracted {len(rules)} rules")
            except NotImplementedError:
                # Skip unimplemented extractors
                continue
            except Exception as e:
                logger.warning(f"{extractor.__class__.__name__} failed: {e}")

        return all_rules


# Usage in BusinessLogicExtractor:

def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
    """
    Extract ALL validation rules using pluggable extractors.
    """
    rules = []

    # Stage 1-6: Current extractors (backward compatibility)
    # ... (existing code)

    # NEW: Pluggable extractor system
    registry = ExtractorRegistry()

    # Register Phase 1 (implemented)
    registry.register(PatternBasedExtractor())

    # Register Phase 2 (future)
    # registry.register(AggressiveLLMExtractor())

    # Register Phase 3 (future)
    # registry.register(GraphInferenceExtractor())

    # Run all registered extractors
    extractor_rules = registry.extract_all(spec)
    rules.extend(extractor_rules)

    # Deduplicate
    rules = self._deduplicate_rules_advanced(rules)

    return ValidationModelIR(rules=rules)
```

### Memory & Performance Considerations

```python
"""
Performance optimization strategies for pattern matching at scale.
"""

# Strategy 1: Pattern Caching
# - Load YAML patterns once, cache in memory
# - Compile regex patterns once, reuse across spec analysis

class PatternMatcher:
    def __init__(self, patterns_file: str):
        self.patterns_file = patterns_file
        self.patterns: Dict[str, Any] = {}
        self._compiled_patterns: Dict[str, re.Pattern] = {}  # ✅ Regex cache
        self._load_patterns()
        self._compile_patterns()  # ✅ Pre-compile all regex

    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        semantic_patterns = self.patterns.get("semantic_patterns", {})
        for pattern_name, pattern_config in semantic_patterns.items():
            pattern_regex = pattern_config.get("pattern", "")
            if pattern_regex:
                self._compiled_patterns[pattern_name] = re.compile(pattern_regex, re.IGNORECASE)


# Strategy 2: Batch Processing
# - Process all fields in parallel (if spec is large)
# - Use multiprocessing for large specifications (>100 entities)

from concurrent.futures import ThreadPoolExecutor

def match_all(self, spec: Dict[str, Any]) -> List[PatternMatch]:
    """Match all patterns with optional parallelization."""
    entities = spec.get("entities", [])
    endpoints = spec.get("endpoints", [])

    if len(entities) > 100:
        # Large spec: use parallel processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.match_type_patterns, entities),
                executor.submit(self.match_semantic_patterns, entities),
                executor.submit(self.match_endpoint_patterns, endpoints),
                # ... other matchers
            ]
            matches = []
            for future in futures:
                matches.extend(future.result())
        return matches
    else:
        # Small spec: sequential processing
        return self._match_sequential(entities, endpoints)


# Strategy 3: Lazy Loading
# - Load patterns only when needed
# - Cache results per spec (if same spec analyzed multiple times)

class PatternMatcher:
    def __init__(self, patterns_file: str):
        self.patterns_file = patterns_file
        self.patterns: Dict[str, Any] = None  # ✅ Lazy load
        self._spec_cache: Dict[str, List[PatternMatch]] = {}  # ✅ Result cache

    def match_all(self, spec: Dict[str, Any]) -> List[PatternMatch]:
        # Check cache first
        spec_hash = hash(json.dumps(spec, sort_keys=True))
        if spec_hash in self._spec_cache:
            return self._spec_cache[spec_hash]

        # Load patterns if not loaded
        if self.patterns is None:
            self._load_patterns()

        # Match and cache
        matches = self._match_sequential(spec.get("entities", []), spec.get("endpoints", []))
        self._spec_cache[spec_hash] = matches

        return matches


# Strategy 4: Memory Limits
# - Limit cache size (LRU eviction)
# - Clear cache after large operations

from functools import lru_cache

class PatternMatcher:
    @lru_cache(maxsize=128)  # ✅ Limit cache to 128 specs
    def match_all_cached(self, spec_json: str) -> List[PatternMatch]:
        """Cached version of match_all."""
        spec = json.loads(spec_json)
        return self.match_all(spec)
```

---

## 6. TYPE SYSTEM ENHANCEMENTS

### ValidationRule Enhancements (Optional)

```python
# Current ValidationRule (from validation_model.py):

class ValidationRule(BaseModel):
    entity: str
    attribute: str
    type: ValidationType
    condition: Optional[str] = None
    error_message: Optional[str] = None
    severity: str = "error"


# ✅ PROPOSED: Enhanced ValidationRule with metadata

class ValidationRule(BaseModel):
    entity: str
    attribute: str
    type: ValidationType
    condition: Optional[str] = None
    error_message: Optional[str] = None
    severity: str = "error"

    # ✅ NEW: Pattern metadata (optional, for Phase 1 tracking)
    source: Optional[str] = None          # "pattern", "llm", "direct"
    pattern_type: Optional[str] = None    # "semantic", "type_based", etc.
    pattern_name: Optional[str] = None    # "email", "UUID", etc.
    confidence: Optional[float] = None    # 0.0-1.0

    class Config:
        # Allow extra fields for future extensibility
        extra = "allow"


# ✅ This enhancement is OPTIONAL for Phase 1
# If not added, pattern matching still works - just no metadata tracking
```

### Pattern Structure (Already in YAML)

The pattern YAML structure is already well-designed. No changes needed.

---

## 7. EXTENSION POINTS FOR PHASE 2 & 3

### Phase 2: Aggressive LLM Extraction

```python
"""
Phase 2 Extension Point: Aggressive LLM with Few-Shot Examples

Strategy:
1. Use pattern matches as few-shot examples for LLM
2. Structured JSON schema for output validation
3. Multiple LLM calls for comprehensive coverage
4. Confidence scoring based on LLM certainty
"""

class AggressiveLLMExtractor(ValidationExtractor):
    """
    Phase 2: LLM extraction with pattern-guided few-shot prompting.
    """

    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        # Get pattern matches as examples
        pattern_validator = PatternBasedValidator()
        pattern_rules = pattern_validator.extract_rules(spec)

        # Build few-shot examples from pattern rules
        few_shot_examples = self._build_few_shot_examples(pattern_rules)

        # LLM prompt with examples
        prompt = self._build_prompt(spec, few_shot_examples)

        # Call LLM with structured output
        llm_rules = self._call_llm_structured(prompt)

        # Score LLM rules by confidence
        scored_rules = self._score_llm_rules(llm_rules)

        return scored_rules

    def _build_few_shot_examples(self, pattern_rules: List[ValidationRule]) -> str:
        """Convert pattern rules to few-shot examples."""
        # Take top 10 pattern rules as examples
        examples = []
        for rule in pattern_rules[:10]:
            examples.append({
                "entity": rule.entity,
                "attribute": rule.attribute,
                "type": rule.type.value,
                "condition": rule.condition,
                "error_message": rule.error_message
            })
        return json.dumps(examples, indent=2)

    def _call_llm_structured(self, prompt: str) -> List[ValidationRule]:
        """
        Call LLM with structured output schema.

        Uses Anthropic's JSON schema validation for guaranteed structure.
        """
        # Implementation with structured output
        pass
```

### Phase 3: Graph-Based Inference

```python
"""
Phase 3 Extension Point: Graph-Based Validation Inference

Strategy:
1. Build entity relationship graph from spec
2. Infer validation rules from graph structure
3. Transitive closure analysis (if A->B and B->C, then A->C)
4. Constraint propagation (FK constraints imply presence validations)
"""

class GraphInferenceExtractor(ValidationExtractor):
    """
    Phase 3: Graph-based validation inference from entity relationships.
    """

    def extract_rules(self, spec: Dict[str, Any]) -> List[ValidationRule]:
        # Build entity graph
        graph = self._build_entity_graph(spec)

        # Infer FK validations from edges
        fk_rules = self._infer_fk_validations(graph)

        # Infer transitive constraints
        transitive_rules = self._infer_transitive_constraints(graph)

        # Infer workflow validations from state graphs
        workflow_rules = self._infer_workflow_validations(graph)

        return fk_rules + transitive_rules + workflow_rules

    def _build_entity_graph(self, spec: Dict[str, Any]) -> nx.Graph:
        """Build directed graph of entity relationships."""
        import networkx as nx

        graph = nx.DiGraph()
        entities = spec.get("entities", [])

        for entity in entities:
            entity_name = entity.get("name")
            graph.add_node(entity_name)

            for field in entity.get("fields", []):
                field_name = field.get("name")

                # Detect FK relationships
                if field_name.endswith("_id"):
                    related_entity = field_name.replace("_id", "").capitalize()
                    graph.add_edge(entity_name, related_entity,
                                   field=field_name,
                                   type="foreign_key")

        return graph

    def _infer_fk_validations(self, graph: nx.Graph) -> List[ValidationRule]:
        """Infer validation rules from FK edges."""
        rules = []

        for source, target, data in graph.edges(data=True):
            if data.get("type") == "foreign_key":
                field = data.get("field")

                # FK implies presence validation
                rules.append(ValidationRule(
                    entity=source,
                    attribute=field,
                    type=ValidationType.PRESENCE,
                    error_message=f"{field} is required",
                    source="graph_inference",
                    confidence=0.9
                ))

                # FK implies relationship validation
                rules.append(ValidationRule(
                    entity=source,
                    attribute=field,
                    type=ValidationType.RELATIONSHIP,
                    error_message=f"Invalid {target} reference",
                    source="graph_inference",
                    confidence=0.95
                ))

        return rules
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: Pattern-Based Validation (Current)

**Goal**: 30-40% coverage improvement (22/62 → 44-50/62)

**Timeline**: 1-2 weeks

**Implementation Steps**:

1. ✅ Create `validation_patterns.yaml` (DONE)
2. ⬜ Implement `PatternMatcher` component
3. ⬜ Implement `PatternScorer` component
4. ⬜ Implement `ValidationRuleGenerator` component
5. ⬜ Implement `PatternBasedValidator` orchestrator
6. ⬜ Integrate into `BusinessLogicExtractor` (Stage 7)
7. ⬜ Enhance `_deduplicate_rules` → `_deduplicate_rules_advanced`
8. ⬜ Add unit tests for pattern matching
9. ⬜ Run E2E test and measure coverage improvement

**Success Criteria**:
- Pattern matching covers 8 pattern types
- Deduplication prevents double-counting
- Coverage reaches 70-80% (44-50/62 validations)

### Phase 2: Aggressive LLM Extraction

**Goal**: 20-30% additional coverage improvement

**Timeline**: 2-3 weeks

**Implementation Steps**:
1. Implement `AggressiveLLMExtractor`
2. Use pattern matches as few-shot examples
3. Structured JSON schema for LLM output
4. Multiple LLM calls for comprehensive coverage
5. Confidence scoring and filtering

**Success Criteria**:
- LLM extraction covers edge cases missed by patterns
- Coverage reaches 90-95% (56-59/62 validations)

### Phase 3: Graph-Based Inference

**Goal**: Final 5-10% coverage improvement

**Timeline**: 2-3 weeks

**Implementation Steps**:
1. Implement entity relationship graph builder
2. Implement FK inference
3. Implement transitive constraint inference
4. Implement workflow state inference

**Success Criteria**:
- Graph inference covers complex relational validations
- Coverage reaches 100% (62/62 validations)

---

## 9. TESTING STRATEGY

### Unit Tests

```python
# tests/test_pattern_matcher.py

def test_type_pattern_matching():
    """Test type-based pattern matching."""
    spec = {
        "entities": [
            {
                "name": "User",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True}
                ]
            }
        ]
    }

    matcher = PatternMatcher()
    matches = matcher.match_type_patterns(spec["entities"])

    # Should match UUID type patterns (FORMAT + PRESENCE)
    assert len(matches) == 2
    assert any(m.validation_type == "FORMAT" and m.attribute == "id" for m in matches)
    assert any(m.validation_type == "PRESENCE" and m.attribute == "id" for m in matches)


def test_semantic_pattern_matching():
    """Test semantic pattern matching."""
    spec = {
        "entities": [
            {
                "name": "User",
                "fields": [
                    {"name": "email", "type": "String"}
                ]
            }
        ]
    }

    matcher = PatternMatcher()
    matches = matcher.match_semantic_patterns(spec["entities"])

    # Should match email semantic patterns (FORMAT + PRESENCE + UNIQUENESS)
    assert len(matches) == 3
    assert any(m.validation_type == "FORMAT" for m in matches)
    assert any(m.validation_type == "UNIQUENESS" for m in matches)


def test_deduplication():
    """Test deduplication with conflict resolution."""
    rules = [
        ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.UNIQUENESS,
            error_message="Email must be unique",
            confidence=0.9
        ),
        ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.UNIQUENESS,
            error_message="Duplicate email",
            confidence=0.85
        ),
    ]

    extractor = BusinessLogicExtractor()
    deduplicated = extractor._deduplicate_rules_advanced(rules)

    # Should keep only one rule (highest confidence)
    assert len(deduplicated) == 1
    assert deduplicated[0].confidence == 0.9
```

### Integration Tests

```python
# tests/test_pattern_integration.py

def test_full_pattern_extraction():
    """Test full pattern-based extraction pipeline."""
    spec = load_test_spec("e-commerce")

    validator = PatternBasedValidator()
    rules = validator.extract_rules(spec)

    # Should extract rules for all major patterns
    assert len(rules) > 20

    # Should have rules for common validations
    email_rules = [r for r in rules if r.attribute == "email"]
    assert any(r.type == ValidationType.UNIQUENESS for r in email_rules)
    assert any(r.type == ValidationType.FORMAT for r in email_rules)


def test_businesslogic_extractor_integration():
    """Test integration with BusinessLogicExtractor."""
    spec = load_test_spec("e-commerce")

    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(spec)

    # Should have rules from all stages (including pattern-based)
    assert len(validation_ir.rules) > 30

    # Should have no duplicates
    rule_keys = [(r.entity, r.attribute, r.type) for r in validation_ir.rules]
    assert len(rule_keys) == len(set(rule_keys))
```

---

## 10. SUCCESS METRICS

### Coverage Metrics

```python
# Expected coverage improvement per phase:

BASELINE_COVERAGE = 22 / 62  # 35.5%

PHASE_1_TARGET = 44 / 62     # 70.9% (+35.4% improvement)
PHASE_2_TARGET = 56 / 62     # 90.3% (+19.4% improvement)
PHASE_3_TARGET = 62 / 62     # 100% (+9.7% improvement)

# Validation types coverage:
#
# Phase 1 (Pattern-Based):
# - FORMAT: 90% coverage
# - PRESENCE: 95% coverage
# - UNIQUENESS: 85% coverage
# - RANGE: 80% coverage
# - RELATIONSHIP: 70% coverage
# - STOCK_CONSTRAINT: 60% coverage
# - STATUS_TRANSITION: 65% coverage
# - WORKFLOW_CONSTRAINT: 50% coverage
#
# Phase 2 (Aggressive LLM):
# - All types: +15-20% coverage
#
# Phase 3 (Graph Inference):
# - RELATIONSHIP: 100% coverage
# - WORKFLOW_CONSTRAINT: 100% coverage
```

### Quality Metrics

```python
# Precision: % of extracted rules that are correct
PRECISION_TARGET = 0.95  # 95% of pattern-matched rules should be valid

# Recall: % of actual validations that are extracted
RECALL_TARGET = 1.0      # 100% coverage goal (Phase 3)

# F1 Score: Harmonic mean of precision and recall
F1_TARGET = 0.97         # (2 * 0.95 * 1.0) / (0.95 + 1.0)

# Deduplication effectiveness
DUPLICATE_RATE_TARGET = 0.05  # <5% duplicates after deduplication
```

---

## SUMMARY

### Key Deliverables

1. ✅ **PatternMatcher**: 8 pattern types, confidence scoring, comprehensive matching
2. ✅ **PatternScorer**: Specificity calculation, multi-pattern aggregation
3. ✅ **ValidationRuleGenerator**: Rule generation, error message interpolation
4. ✅ **PatternBasedValidator**: Orchestrator component
5. ✅ **Integration**: Stage 7 in BusinessLogicExtractor pipeline
6. ✅ **Deduplication**: Advanced conflict resolution algorithm
7. ✅ **Extensibility**: Plugin architecture for Phases 2 & 3
8. ✅ **Type System**: Enhanced ValidationRule with metadata (optional)

### Expected Impact

- **Coverage**: 35% → 70% (Phase 1), → 90% (Phase 2), → 100% (Phase 3)
- **Precision**: 95% (pattern matches are highly reliable)
- **Maintainability**: Pattern YAML is easy to extend
- **Performance**: <1s for pattern matching on typical specs
- **Extensibility**: Clean plugin architecture for future phases

### Next Steps

1. Implement Phase 1 components (1-2 weeks)
2. Run E2E test and measure coverage
3. Iterate on patterns based on gaps
4. Plan Phase 2 implementation

---

**End of Architecture Document**
