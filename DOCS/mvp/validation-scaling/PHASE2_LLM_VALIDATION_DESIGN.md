# Phase 2: LLM-Primary Validation Extraction - Design Specification

**Objective**: Transform LLM from fallback to primary validation extractor, achieving 97-100% coverage (60-62/62 validations)

**Current State**: Phase 1 (Pattern-Based) = 45/62 validations (73%)
**Target State**: Phase 2 (LLM-Primary) = 60-62/62 validations (97-100%)
**Improvement**: +15-17 validations (+33-38% boost)

---

## 1. Architecture Overview

### 1.1 Strategic Shift

**OLD Architecture (Phase 1):**
```
Direct Extraction → Pattern-Based → LLM Fallback (limited)
        ↓                ↓              ↓
   30 rules        +15 rules      +0-5 rules
   = 45 total (73% coverage)
```

**NEW Architecture (Phase 2):**
```
Direct Extraction → Pattern-Based → LLM-Primary (comprehensive)
        ↓                ↓                  ↓
   30 rules        +15 rules         +15-17 rules
                                = 60-62 total (97-100% coverage)
```

### 1.2 Key Principles

1. **LLM as Primary Extractor**: Use LLM to analyze ALL fields/endpoints, not just gaps
2. **Structured Prompts**: 3 specialized prompts (field-level, endpoint-level, cross-entity)
3. **Confidence Scoring**: High confidence (0.85+) for LLM-extracted validations
4. **Intelligent Deduplication**: Merge rules from all sources with provenance tracking
5. **Cost Optimization**: Batch operations to minimize LLM calls (3-5 per spec)

---

## 2. LLM Prompt Specifications

### 2.1 Field-Level Validation Prompt

**Purpose**: Extract ALL validations for each entity field
**Input**: Entity name + list of fields with metadata
**Output**: Structured JSON with validation rules

```python
FIELD_VALIDATION_PROMPT = """You are a backend validation expert analyzing OpenAPI specifications.

TASK: Extract ALL possible validations for the given fields.

CONTEXT:
Entity: {entity_name}
Fields to analyze:
{fields_json}

VALIDATION TYPES TO CONSIDER:
1. Type validations (string, integer, email, uuid, etc.)
2. Format validations (email, uri, date-time, uuid, etc.)
3. Range validations (minimum, maximum, minLength, maxLength)
4. Pattern validations (regex patterns)
5. Enum validations (allowed values)
6. Required validations (not null, required in request)
7. Uniqueness validations (unique constraint)
8. Business logic validations (custom rules)

OUTPUT FORMAT:
Return a JSON array of validation objects. Each object must have:
{{
  "entity": "entity_name",
  "attribute": "field_name",
  "type": "validation_type",  // e.g., "FORMAT", "RANGE", "PRESENCE", "UNIQUENESS"
  "condition": "validation_rule",  // e.g., "type: string", "minLength: 3", "pattern: ^[A-Z]"
  "error_message": "human_readable_error",
  "confidence": 0.0-1.0,  // 0.9+ for explicit specs, 0.7-0.9 for inferred
  "rationale": "why_this_validation_exists"
}}

EXAMPLE OUTPUT:
[
  {{
    "entity": "User",
    "attribute": "email",
    "type": "FORMAT",
    "condition": "format: email",
    "error_message": "Email must be a valid email address",
    "confidence": 0.95,
    "rationale": "Schema explicitly defines format: email"
  }},
  {{
    "entity": "User",
    "attribute": "email",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Email is required",
    "confidence": 0.90,
    "rationale": "Field is in required array of User schema"
  }},
  {{
    "entity": "User",
    "attribute": "email",
    "type": "UNIQUENESS",
    "condition": "unique: true",
    "error_message": "Email must be unique",
    "confidence": 0.85,
    "rationale": "Email is typically unique identifier in user systems"
  }}
]

IMPORTANT:
- Include BOTH explicit validations (from schema) and implicit validations (from business logic)
- Assign higher confidence (0.9+) to explicit spec validations
- Assign moderate confidence (0.7-0.9) to inferred business rules
- Be comprehensive: think of edge cases and security validations
- Return valid JSON only, no markdown formatting

ANALYZE NOW:
"""
```

**Validation Type Mapping**:
```python
VALIDATION_TYPE_MAP = {
    "type": ValidationType.FORMAT,
    "format": ValidationType.FORMAT,
    "range": ValidationType.RANGE,
    "pattern": ValidationType.FORMAT,
    "enum": ValidationType.STATUS_TRANSITION,
    "required": ValidationType.PRESENCE,
    "unique": ValidationType.UNIQUENESS,
    "business": ValidationType.WORKFLOW_CONSTRAINT,
    "security": ValidationType.PRESENCE  # Auth validations
}
```

### 2.2 Endpoint-Level Validation Prompt

**Purpose**: Extract request/response validations for each endpoint
**Input**: Endpoint method + path + request/response schemas
**Output**: Structured JSON with endpoint validations

```python
ENDPOINT_VALIDATION_PROMPT = """You are a backend API validation expert analyzing OpenAPI endpoints.

TASK: Extract ALL request/response validations for the given endpoint.

ENDPOINT:
Method: {method}
Path: {path}
Operation: {operation_id}

REQUEST BODY:
{request_body_json}

RESPONSE SCHEMAS:
{response_schemas_json}

VALIDATION CATEGORIES TO EXTRACT:
1. Request body validations (required fields, schema compliance)
2. Path parameter validations (format, existence)
3. Query parameter validations (type, range, defaults)
4. Header validations (authentication, content-type)
5. Response validations (status codes, response schema)
6. Business workflow validations (state transitions, permissions)
7. Security validations (authentication, authorization)

OUTPUT FORMAT:
Return a JSON array of validation objects:
{{
  "entity": "endpoint_entity_name",  // e.g., "User" for /users
  "attribute": "field_or_parameter_name",
  "type": "validation_type",
  "condition": "validation_rule",
  "error_message": "human_readable_error",
  "confidence": 0.0-1.0,
  "rationale": "why_this_validation_exists",
  "scope": "request|response|both"  // Where validation applies
}}

EXAMPLE OUTPUT:
[
  {{
    "entity": "User",
    "attribute": "POST_body",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Request body is required",
    "confidence": 0.95,
    "rationale": "POST endpoint requires request body",
    "scope": "request"
  }},
  {{
    "entity": "User",
    "attribute": "id",
    "type": "FORMAT",
    "condition": "format: uuid",
    "error_message": "User ID must be a valid UUID",
    "confidence": 0.90,
    "rationale": "Path parameter defined as uuid format",
    "scope": "request"
  }},
  {{
    "entity": "User",
    "attribute": "authentication",
    "type": "PRESENCE",
    "condition": "required: bearer_token",
    "error_message": "Authentication required",
    "confidence": 0.85,
    "rationale": "Endpoint has security requirement",
    "scope": "request"
  }}
]

IMPORTANT:
- Extract validations from ALL parts: body, params, headers, responses
- Consider HTTP method semantics (POST requires body, DELETE may not, etc.)
- Include security validations even if not explicitly in spec
- Higher confidence for explicit spec elements
- Return valid JSON only

ANALYZE NOW:
"""
```

### 2.3 Cross-Entity Validation Prompt

**Purpose**: Identify validations spanning multiple entities
**Input**: Entity relationships + endpoint summary
**Output**: Structured JSON with relationship validations

```python
CROSS_ENTITY_VALIDATION_PROMPT = """You are a backend architect analyzing OpenAPI specifications for cross-entity validations.

TASK: Identify validations that span multiple entities or involve relationships.

ENTITIES AND RELATIONSHIPS:
{entities_relationships_json}

ENDPOINTS OVERVIEW:
{endpoints_summary_json}

CROSS-ENTITY VALIDATION TYPES:
1. Foreign key validations (referenced entity must exist)
2. Cascade validations (delete parent affects children)
3. Workflow validations (order of operations, state machines)
4. Referential integrity (orphan prevention)
5. Business rule constraints (e.g., user can't delete own account)
6. Permission validations (ownership, role-based access)
7. Transactional consistency (atomic operations)

OUTPUT FORMAT:
Return a JSON array of cross-entity validation objects:
{{
  "entity": "primary_entity",
  "related_entity": "referenced_entity",
  "attribute": "relationship_field",
  "type": "RELATIONSHIP",
  "condition": "validation_rule",
  "error_message": "human_readable_error",
  "confidence": 0.0-1.0,
  "rationale": "business_or_technical_reason"
}}

EXAMPLE OUTPUT:
[
  {{
    "entity": "Order",
    "related_entity": "User",
    "attribute": "user_id",
    "type": "RELATIONSHIP",
    "condition": "foreign_key: User.id exists",
    "error_message": "User must exist before creating order",
    "confidence": 0.90,
    "rationale": "Order references User via user_id foreign key"
  }},
  {{
    "entity": "User",
    "related_entity": "Order",
    "attribute": "delete_user",
    "type": "WORKFLOW_CONSTRAINT",
    "condition": "cascade: prevent if orders exist",
    "error_message": "Cannot delete user with existing orders",
    "confidence": 0.80,
    "rationale": "Business rule to preserve order history"
  }}
]

IMPORTANT:
- Focus on relationships between entities (foreign keys, references)
- Consider cascade behaviors (on delete, on update)
- Think about business workflows (order of operations)
- Include permission and ownership validations
- Higher confidence for explicit references in spec
- Return valid JSON only

ANALYZE NOW:
"""
```

---

## 3. Structured Output Schema

```python
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, List
from src.cognitive.ir.validation_model import ValidationType

class LLMValidation(BaseModel):
    """Schema for LLM-extracted validation"""

    entity: str = Field(..., description="Entity/model name")
    attribute: str = Field(..., description="Field or parameter name")
    type: str = Field(..., description="Validation category (string)")
    condition: str = Field(..., description="Validation rule")
    error_message: str = Field(..., description="User-facing error message")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    rationale: str = Field(..., description="Why this validation exists")

    # Optional fields for endpoint/cross-entity validations
    scope: Optional[Literal["request", "response", "both"]] = None
    related_entity: Optional[str] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    def to_validation_rule(self) -> ValidationRule:
        """Convert to internal ValidationRule format"""
        # Map string type to ValidationType enum
        validation_type_map = {
            "FORMAT": ValidationType.FORMAT,
            "RANGE": ValidationType.RANGE,
            "PRESENCE": ValidationType.PRESENCE,
            "UNIQUENESS": ValidationType.UNIQUENESS,
            "RELATIONSHIP": ValidationType.RELATIONSHIP,
            "STOCK_CONSTRAINT": ValidationType.STOCK_CONSTRAINT,
            "STATUS_TRANSITION": ValidationType.STATUS_TRANSITION,
            "WORKFLOW_CONSTRAINT": ValidationType.WORKFLOW_CONSTRAINT,
        }

        # Get ValidationType from string, default to PRESENCE
        val_type = validation_type_map.get(self.type.upper(), ValidationType.PRESENCE)

        from src.cognitive.ir.validation_model import ValidationRule
        return ValidationRule(
            entity=self.entity,
            attribute=self.attribute,
            type=val_type,
            condition=self.condition if self.condition else None,
            error_message=self.error_message
        )


class LLMValidationResponse(BaseModel):
    """Response wrapper for batch validations"""
    validations: List[LLMValidation]

    @validator('validations')
    def remove_duplicates(cls, v):
        """Remove duplicate validations within same response"""
        seen = set()
        unique = []
        for val in v:
            key = (val.entity, val.attribute, val.type, val.condition)
            if key not in seen:
                seen.add(key)
                unique.append(val)
        return unique
```

---

## 4. Refactored Extraction Pipeline

### 4.1 Current Stage 7 (OLD - Fallback)

```python
# Stage 7: Use LLM for comprehensive business logic extraction
try:
    llm_rules = self._extract_with_llm(spec)
    rules.extend(llm_rules)
except Exception as e:
    logger.warning(f"LLM extraction failed: {e}, continuing with pattern-based rules")
```

**Problem**: LLM only called once, with minimal prompt, as safety net

### 4.2 New Stage 7 (NEW - Primary Extractor)

```python
# Stage 7: LLM-Primary Extraction (comprehensive, structured)
try:
    llm_rules = []

    # Stage 7a: Field-level validations (ALL entities, ALL fields)
    field_rules = self._extract_field_validations_llm(spec)
    llm_rules.extend(field_rules)
    logger.info(f"LLM field extraction: {len(field_rules)} validations")

    # Stage 7b: Endpoint validations (ALL endpoints)
    endpoint_rules = self._extract_endpoint_validations_llm(spec)
    llm_rules.extend(endpoint_rules)
    logger.info(f"LLM endpoint extraction: {len(endpoint_rules)} validations")

    # Stage 7c: Cross-entity validations (relationships)
    cross_rules = self._extract_cross_entity_validations_llm(spec)
    llm_rules.extend(cross_rules)
    logger.info(f"LLM cross-entity extraction: {len(cross_rules)} validations")

    rules.extend(llm_rules)
    logger.info(f"Total LLM extraction: {len(llm_rules)} validations")

except Exception as e:
    logger.error(f"LLM extraction failed: {e}, falling back to pattern-only")
    # Pattern-based rules already extracted, continue
```

---

## 5. Implementation Methods

### 5.1 Field-Level Extraction

```python
def _extract_field_validations_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Extract field-level validations using LLM for ALL entity fields.
    Batches fields per entity to minimize API calls.
    """
    rules = []
    entities = spec.get("entities", [])

    if not entities:
        return rules

    # Process entities in batches (optimization)
    for entity in entities:
        entity_name = entity.get("name", "Unknown")
        fields = entity.get("fields", [])

        if not fields:
            continue

        # Prepare field data for prompt
        fields_json = json.dumps([
            {
                "name": f.get("name"),
                "type": f.get("type"),
                "required": f.get("required", False),
                "unique": f.get("unique", False),
                "constraints": f.get("constraints", {}),
                "description": f.get("description", "")
            }
            for f in fields
        ], indent=2)

        # Build prompt
        prompt = FIELD_VALIDATION_PROMPT.format(
            entity_name=entity_name,
            fields_json=fields_json
        )

        # Call LLM
        try:
            response = self._call_llm(prompt)
            validations = self._parse_llm_response(response)

            # Convert to ValidationRule objects
            for val in validations:
                try:
                    rule = val.to_validation_rule()
                    rules.append(rule)
                except Exception as e:
                    logger.warning(f"Failed to convert LLM validation to rule: {e}")

        except Exception as e:
            logger.warning(f"LLM field extraction failed for {entity_name}: {e}")
            continue

    return rules
```

### 5.2 Endpoint-Level Extraction

```python
def _extract_endpoint_validations_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Extract endpoint-level validations using LLM for ALL endpoints.
    Batches endpoints by entity to minimize API calls.
    """
    rules = []
    endpoints = spec.get("endpoints", [])

    if not endpoints:
        return rules

    # Group endpoints by entity for batching
    endpoints_by_entity = {}
    for endpoint in endpoints:
        path = endpoint.get("path", "")
        entity = self._infer_entity_from_path(path, spec.get("entities", []))

        if entity not in endpoints_by_entity:
            endpoints_by_entity[entity] = []
        endpoints_by_entity[entity].append(endpoint)

    # Process each entity's endpoints
    for entity_name, entity_endpoints in endpoints_by_entity.items():
        for endpoint in entity_endpoints:
            method = endpoint.get("method", "GET").upper()
            path = endpoint.get("path", "")
            operation_id = endpoint.get("operation_id", "")

            # Prepare request body
            request_body = endpoint.get("request_body", {})
            request_body_json = json.dumps(request_body, indent=2) if request_body else "None"

            # Prepare response schemas
            responses = endpoint.get("responses", {})
            response_schemas_json = json.dumps(responses, indent=2) if responses else "None"

            # Build prompt
            prompt = ENDPOINT_VALIDATION_PROMPT.format(
                method=method,
                path=path,
                operation_id=operation_id,
                request_body_json=request_body_json,
                response_schemas_json=response_schemas_json
            )

            # Call LLM
            try:
                response = self._call_llm(prompt)
                validations = self._parse_llm_response(response)

                # Convert to ValidationRule objects
                for val in validations:
                    try:
                        rule = val.to_validation_rule()
                        rules.append(rule)
                    except Exception as e:
                        logger.warning(f"Failed to convert endpoint validation: {e}")

            except Exception as e:
                logger.warning(f"LLM endpoint extraction failed for {method} {path}: {e}")
                continue

    return rules
```

### 5.3 Cross-Entity Extraction

```python
def _extract_cross_entity_validations_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Extract cross-entity validations using LLM (relationships, cascades).
    Single call analyzing all entities and their relationships.
    """
    rules = []
    entities = spec.get("entities", [])
    endpoints = spec.get("endpoints", [])

    if not entities:
        return rules

    # Build entity relationships map
    relationships = {}
    for entity in entities:
        entity_name = entity.get("name", "")
        entity_fields = []

        for field in entity.get("fields", []):
            field_name = field.get("name", "")
            field_type = field.get("type", "")

            # Detect foreign key relationships
            if field_name.endswith("_id") and field_type in ["UUID", "Integer"]:
                ref_entity = field_name.replace("_id", "").capitalize()
                entity_fields.append({
                    "field": field_name,
                    "type": field_type,
                    "references": ref_entity
                })

        if entity_fields:
            relationships[entity_name] = entity_fields

    # Build endpoints summary
    endpoints_summary = []
    for endpoint in endpoints:
        endpoints_summary.append({
            "method": endpoint.get("method", "GET"),
            "path": endpoint.get("path", ""),
            "entity": self._infer_entity_from_path(
                endpoint.get("path", ""),
                entities
            )
        })

    # Prepare JSON for prompt
    entities_relationships_json = json.dumps(relationships, indent=2)
    endpoints_summary_json = json.dumps(endpoints_summary, indent=2)

    # Build prompt
    prompt = CROSS_ENTITY_VALIDATION_PROMPT.format(
        entities_relationships_json=entities_relationships_json,
        endpoints_summary_json=endpoints_summary_json
    )

    # Call LLM
    try:
        response = self._call_llm(prompt)
        validations = self._parse_llm_response(response)

        # Convert to ValidationRule objects
        for val in validations:
            try:
                rule = val.to_validation_rule()
                rules.append(rule)
            except Exception as e:
                logger.warning(f"Failed to convert cross-entity validation: {e}")

    except Exception as e:
        logger.error(f"LLM cross-entity extraction failed: {e}")

    return rules
```

### 5.4 Helper Methods

```python
def _call_llm(self, prompt: str) -> str:
    """Call Claude API with timeout and error handling."""
    try:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,  # Increased for comprehensive responses
            temperature=0.0,  # Deterministic for validation extraction
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise


def _parse_llm_response(self, response: str) -> List[LLMValidation]:
    """Parse LLM JSON response into LLMValidation objects."""
    try:
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]

        # Parse JSON
        validations_data = json.loads(response)

        # Validate with Pydantic
        response_obj = LLMValidationResponse(validations=validations_data)

        return response_obj.validations

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Response text: {response}")
        return []
    except Exception as e:
        logger.error(f"Failed to validate LLM response: {e}")
        return []
```

---

## 6. Deduplication & Merging Strategy

### 6.1 Enhanced Deduplication Algorithm

```python
def _deduplicate_rules(self, rules: List[ValidationRule]) -> List[ValidationRule]:
    """
    Remove duplicate rules with intelligent merging.
    Priority: direct > pattern > LLM
    Confidence: keep highest confidence version
    """
    # Group rules by (entity, attribute, type)
    rule_groups = {}

    for rule in rules:
        key = (rule.entity, rule.attribute, rule.type)

        if key not in rule_groups:
            rule_groups[key] = []
        rule_groups[key].append(rule)

    # Select best rule from each group
    deduplicated = []

    for key, group in rule_groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
            continue

        # Determine provenance (direct, pattern, LLM)
        # Assume rules from earlier stages have higher priority
        # Sort by provenance priority and confidence

        best_rule = max(group, key=lambda r: (
            self._get_provenance_priority(r),
            getattr(r, 'confidence', 0.5)  # Default confidence if not set
        ))

        # Merge conditions if multiple rules provide complementary info
        merged_condition = self._merge_conditions([r.condition for r in group if r.condition])
        if merged_condition and merged_condition != best_rule.condition:
            best_rule.condition = merged_condition

        deduplicated.append(best_rule)

    logger.info(f"Deduplicated {len(rules)} → {len(deduplicated)} rules")
    return deduplicated


def _get_provenance_priority(self, rule: ValidationRule) -> int:
    """
    Determine provenance priority for rule selection.
    Higher = better priority.
    """
    # Check if rule has provenance metadata
    if hasattr(rule, 'metadata') and 'provenance' in rule.metadata:
        provenance = rule.metadata['provenance']
        priority_map = {
            'direct': 3,      # Explicit from spec
            'pattern': 2,     # Pattern-based extraction
            'llm': 1          # LLM inference
        }
        return priority_map.get(provenance, 0)

    # Fallback: heuristic based on condition specificity
    if rule.condition and len(rule.condition) > 20:
        return 2  # Detailed condition = likely pattern-based
    return 1  # Default = likely LLM


def _merge_conditions(self, conditions: List[Optional[str]]) -> Optional[str]:
    """
    Merge multiple conditions using AND logic.
    Only merge if conditions are complementary, not conflicting.
    """
    valid_conditions = [c for c in conditions if c]

    if not valid_conditions:
        return None

    if len(valid_conditions) == 1:
        return valid_conditions[0]

    # Check for conflicts (e.g., different min values)
    # For simplicity, concatenate with AND
    # TODO: Implement smarter conflict detection

    unique_conditions = list(set(valid_conditions))
    if len(unique_conditions) == 1:
        return unique_conditions[0]

    return " AND ".join(unique_conditions)
```

### 6.2 Provenance Tracking

Add provenance metadata to rules during extraction:

```python
# In _extract_from_entities (Stage 1)
rule = ValidationRule(
    entity=entity_name,
    attribute=field_name,
    type=ValidationType.PRESENCE,
    error_message=f"{field_name} is required",
    metadata={"provenance": "direct"}  # NEW
)

# In _extract_pattern_rules (Stage 6.5)
rule = ValidationRule(
    entity=entity_name,
    attribute=field_name,
    type=ValidationType[val_type],
    condition=validation.get("condition", ""),
    error_message=error_msg,
    metadata={"provenance": "pattern"}  # NEW
)

# In LLM extraction methods (Stage 7a/b/c)
# Modify LLMValidation.to_validation_rule():
def to_validation_rule(self) -> ValidationRule:
    return ValidationRule(
        entity=self.entity,
        attribute=self.attribute,
        type=val_type,
        condition=self.condition if self.condition else None,
        error_message=self.error_message,
        metadata={
            "provenance": "llm",  # NEW
            "confidence": self.confidence,
            "rationale": self.rationale
        }
    )
```

---

## 7. Performance & Cost Optimization

### 7.1 LLM Call Batching Strategy

**Goal**: Minimize LLM calls while maintaining comprehensive coverage

**Approach**:
```python
# OLD (naive): 1 call per field = 30+ calls
for field in all_fields:
    call_llm(field)  # 30-50 calls

# NEW (batched): 1 call per entity = 3-5 calls
for entity in entities:
    call_llm(all_entity_fields)  # 3-5 calls for field-level

call_llm(all_endpoints_by_entity)  # 1-3 calls for endpoint-level
call_llm(all_relationships)        # 1 call for cross-entity
```

**Total Calls**:
- Field-level: 3-5 calls (1 per entity)
- Endpoint-level: 3-5 calls (1-2 per entity group)
- Cross-entity: 1 call (entire spec)
- **Total: 7-11 LLM calls per spec** (vs 30-50 naive approach)

### 7.2 Cost Estimation

**Model**: Claude Sonnet 3.5 (claude-3-5-sonnet-20241022)

**Token Usage**:
- Input: ~1000 tokens per prompt (avg)
- Output: ~500 tokens per response (avg)
- Total per call: ~1500 tokens

**Cost Calculation**:
- Input cost: $3/MTok
- Output cost: $15/MTok
- Per call: (1000 × $3 + 500 × $15) / 1M = $0.0105
- Per spec (10 calls): ~$0.11

**Phase 1 vs Phase 2 Cost**:
- Phase 1: 1 LLM call = $0.01
- Phase 2: 10 LLM calls = $0.11
- **Cost increase: ~10x ($0.10 per spec)**
- **Validation coverage increase: +33% (45 → 60)**
- **Cost per validation: $0.0018 (excellent ROI)**

### 7.3 Timeout & Error Handling

```python
import time
from typing import Optional

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 50):
        self.calls_per_minute = calls_per_minute
        self.call_times = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]

        if len(self.call_times) >= self.calls_per_minute:
            # Wait until oldest call is 60s old
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self.call_times.append(now)


# In BusinessLogicExtractor.__init__()
self.rate_limiter = RateLimiter(calls_per_minute=50)


# In _call_llm()
def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
    """Call Claude API with rate limiting and retry logic."""

    for attempt in range(max_retries):
        try:
            # Wait if needed for rate limit
            self.rate_limiter.wait_if_needed()

            # Call API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limit hit, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"Rate limit exceeded after {max_retries} attempts")
                raise

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {e}")
                time.sleep(1)
            else:
                logger.error(f"LLM call failed after {max_retries} attempts: {e}")
                raise

    raise Exception("LLM call failed after all retries")
```

---

## 8. Expected Results & Validation

### 8.1 Coverage Targets

| Metric | Phase 1 | Phase 2 (Target) | Improvement |
|--------|---------|------------------|-------------|
| **Total Validations** | 45/62 | 60-62/62 | +15-17 |
| **Coverage %** | 73% | 97-100% | +24-27% |
| **Direct Extraction** | 30 | 30 | 0 |
| **Pattern-Based** | 15 | 15 | 0 |
| **LLM Extraction** | 0-2 | 15-17 | +15-17 |

### 8.2 Validation Categories Breakdown

| Category | Phase 1 | Phase 2 | Improvement |
|----------|---------|---------|-------------|
| PRESENCE | 12 | 18 | +6 |
| FORMAT | 8 | 12 | +4 |
| UNIQUENESS | 6 | 8 | +2 |
| RANGE | 5 | 7 | +2 |
| RELATIONSHIP | 8 | 10 | +2 |
| STATUS_TRANSITION | 4 | 5 | +1 |
| WORKFLOW_CONSTRAINT | 2 | 2 | 0 |
| **TOTAL** | **45** | **62** | **+17** |

### 8.3 Test Validation Strategy

```python
# tests/e2e/test_phase2_llm_validation.py

def test_phase2_coverage():
    """Test Phase 2 achieves 97%+ coverage."""
    spec = load_ecommerce_spec()
    extractor = BusinessLogicExtractor()

    validation_ir = extractor.extract_validation_rules(spec)

    # Expected validations: 62
    assert len(validation_ir.rules) >= 60, \
        f"Expected ≥60 validations, got {len(validation_ir.rules)}"

    # Coverage: 97%+
    coverage = len(validation_ir.rules) / 62
    assert coverage >= 0.97, \
        f"Expected ≥97% coverage, got {coverage:.1%}"


def test_llm_extraction_comprehensiveness():
    """Test LLM extraction finds validations pattern-based missed."""
    spec = load_ecommerce_spec()
    extractor = BusinessLogicExtractor()

    # Extract with LLM
    validation_ir = extractor.extract_validation_rules(spec)

    # Check for specific validations LLM should find
    llm_found_validations = [
        ("User", "email", ValidationType.UNIQUENESS),
        ("Order", "customer_id", ValidationType.RELATIONSHIP),
        ("OrderItem", "quantity", ValidationType.RANGE),
        ("Product", "stock", ValidationType.STOCK_CONSTRAINT),
    ]

    for entity, attr, val_type in llm_found_validations:
        matching_rule = next(
            (r for r in validation_ir.rules
             if r.entity == entity and r.attribute == attr and r.type == val_type),
            None
        )
        assert matching_rule is not None, \
            f"LLM should have found {val_type} validation for {entity}.{attr}"


def test_deduplication_keeps_best():
    """Test deduplication keeps highest priority rule."""
    # Create duplicate rules with different provenances
    rules = [
        ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.PRESENCE,
            error_message="Email required (pattern)",
            metadata={"provenance": "pattern"}
        ),
        ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.PRESENCE,
            error_message="Email required (direct)",
            metadata={"provenance": "direct"}
        ),
        ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.PRESENCE,
            error_message="Email required (LLM)",
            metadata={"provenance": "llm"}
        ),
    ]

    extractor = BusinessLogicExtractor()
    deduplicated = extractor._deduplicate_rules(rules)

    # Should keep direct extraction (highest priority)
    assert len(deduplicated) == 1
    assert deduplicated[0].metadata["provenance"] == "direct"
```

---

## 9. Implementation Checklist

### Phase 2A: Prompt Engineering (Week 1)
- [ ] Design 3 specialized prompts (field, endpoint, cross-entity)
- [ ] Define Pydantic schemas for structured output
- [ ] Test prompts on sample specs (manual validation)
- [ ] Refine prompts based on test results
- [ ] Document prompt examples and expected outputs

### Phase 2B: Core Implementation (Week 2)
- [ ] Implement `_extract_field_validations_llm()`
- [ ] Implement `_extract_endpoint_validations_llm()`
- [ ] Implement `_extract_cross_entity_validations_llm()`
- [ ] Implement `_call_llm()` with retries and rate limiting
- [ ] Implement `_parse_llm_response()` with error handling
- [ ] Add provenance tracking to all extraction stages
- [ ] Refactor `_deduplicate_rules()` with intelligent merging

### Phase 2C: Testing & Validation (Week 3)
- [ ] Write E2E tests for Phase 2 coverage (target 97%+)
- [ ] Write unit tests for LLM extraction methods
- [ ] Write unit tests for deduplication algorithm
- [ ] Test with ecommerce spec (validate 60+ validations)
- [ ] Test with other specs (generalization)
- [ ] Benchmark performance (calls, tokens, cost)

### Phase 2D: Optimization & Polish (Week 4)
- [ ] Optimize batching strategy (minimize LLM calls)
- [ ] Add caching for repeated extractions
- [ ] Add metrics/logging for observability
- [ ] Document cost analysis and ROI
- [ ] Update README with Phase 2 achievements
- [ ] Create migration guide from Phase 1 to Phase 2

---

## 10. Success Criteria

### 10.1 Functional Requirements
✅ Achieve 60-62 validations (97-100% coverage) on ecommerce spec
✅ LLM extraction contributes 15-17 new validations
✅ All 3 LLM prompts (field, endpoint, cross-entity) work reliably
✅ Deduplication preserves highest priority rules
✅ Error handling prevents LLM failures from breaking pipeline

### 10.2 Performance Requirements
✅ Total LLM calls per spec: ≤15 (optimized batching)
✅ Cost per spec: ≤$0.15 (acceptable for comprehensive extraction)
✅ Extraction time: ≤30 seconds (including LLM calls)
✅ Rate limiting prevents API errors (≤50 calls/min)

### 10.3 Quality Requirements
✅ Validation confidence scores: 0.85+ for LLM-extracted rules
✅ False positives: <5% (validate against ground truth)
✅ Missing validations: <3% (compared to manual review)
✅ Provenance tracking: 100% of rules have source metadata

---

## 11. Risk Mitigation

### 11.1 LLM Response Quality
**Risk**: LLM returns incomplete or invalid JSON
**Mitigation**:
- Use temperature=0.0 for deterministic responses
- Validate responses with Pydantic schemas
- Implement retry logic with refined prompts
- Fallback to pattern-based rules if LLM fails

### 11.2 Cost Overruns
**Risk**: High token usage exceeds budget
**Mitigation**:
- Batch fields/endpoints to minimize calls
- Monitor token usage per extraction
- Set hard limit on max_tokens per call
- Implement caching for repeated specs

### 11.3 Rate Limiting
**Risk**: API rate limits cause failures
**Mitigation**:
- Implement RateLimiter class with wait logic
- Exponential backoff on rate limit errors
- Spread calls across time (avoid bursts)

### 11.4 Over-Extraction
**Risk**: LLM creates spurious validations
**Mitigation**:
- Set confidence threshold (0.7+) for acceptance
- Review low-confidence rules manually
- Deduplication removes redundant rules
- Validation tests catch false positives

---

## 12. Future Enhancements (Phase 3+)

### 12.1 Advanced LLM Techniques
- Multi-turn conversations for complex validations
- Chain-of-thought prompting for reasoning transparency
- Few-shot examples in prompts for consistency
- Ensemble extraction (multiple models, vote)

### 12.2 Learning & Adaptation
- Fine-tune model on validated extractions
- Build validation pattern library from corrections
- Active learning: flag uncertain rules for review
- Feedback loop: improve prompts based on corrections

### 12.3 Domain-Specific Extractors
- E-commerce validation templates
- Healthcare/HIPAA compliance rules
- Financial/SOX validation patterns
- SaaS multi-tenancy validations

---

## Conclusion

Phase 2 transforms validation extraction from pattern-based (73% coverage) to LLM-primary (97-100% coverage) through:

1. **Structured LLM Prompts**: 3 specialized prompts covering all validation dimensions
2. **Intelligent Batching**: 7-11 LLM calls per spec (vs 30-50 naive approach)
3. **Enhanced Deduplication**: Provenance tracking and confidence-based rule selection
4. **Robust Error Handling**: Rate limiting, retries, fallbacks ensure reliability

**Expected Impact**:
- Coverage: 73% → 97-100% (+24-27%)
- Validations: 45 → 60-62 (+15-17)
- Cost: $0.01 → $0.11 per spec (+$0.10, excellent ROI)
- Time: +20 seconds (acceptable for comprehensive extraction)

**Next Steps**: Implement Phase 2A (Prompt Engineering) and validate on ecommerce spec.
