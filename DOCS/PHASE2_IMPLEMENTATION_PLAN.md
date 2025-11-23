# Phase 2: Implementation Plan - Step-by-Step Guide

Detailed implementation roadmap for transforming validation extraction from pattern-based (73%) to LLM-primary (97-100%).

---

## 🚀 PROGRESS TRACKER

**Status**: 🔜 IN PROGRESS (60% Complete)
**Current Date**: 2025-11-23
**Started**: 2025-11-23
**Target Completion**: 2025-12-07 (2 weeks)

**Progress Summary**:

- ✅ Week 1: Design & Schema (COMPLETE)
- ✅ Week 2: Implementation (COMPLETE)
- ⏳ Week 3: Testing & Validation (IN PROGRESS)
- ⏳ Week 4: Optimization & Documentation (PENDING)

---

## Overview

**Timeline**: 4 weeks (20 working days)
**Effort**: ~40-60 hours total
**Team**: 1 backend engineer + 1 reviewer
**Risk**: Low-Medium (LLM reliability, cost management)
**Overall Status**: 60% Complete - On Track ✅

---

## Week 1: Prompt Engineering & Schema Design (Days 1-5)

### Day 1-2: Prompt Design & Testing

#### Task 1.1: Design Field-Level Prompt (4h)

**Deliverables**:
- `prompts/field_validation_prompt.txt` - Final prompt template
- `prompts/field_examples.json` - Test examples with expected outputs
- `prompts/field_validation_guide.md` - Prompt engineering decisions

**Implementation**:
```python
# Create prompt templates directory
mkdir -p prompts/

# Field-level prompt (prompts/field_validation_prompt.txt)
"""
You are a backend validation expert analyzing OpenAPI specifications.

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
Return a JSON array of validation objects...
[format specification]

ANALYZE NOW:
"""
```

**Testing**:
```python
# Test prompt with sample User entity
python scripts/test_field_prompt.py --entity User --spec specs/ecommerce.yaml

# Expected output: 8-10 validations for User entity
# Validate against ground truth manually
```

**Success Criteria**:
- ✅ Prompt produces valid JSON 100% of the time
- ✅ Extracts 8+ validations for User entity
- ✅ Confidence scores are reasonable (0.7-0.95 range)

#### Task 1.2: Design Endpoint-Level Prompt (4h)

**Deliverables**:
- `prompts/endpoint_validation_prompt.txt`
- `prompts/endpoint_examples.json`
- `prompts/endpoint_validation_guide.md`

**Implementation**:
```python
# Endpoint-level prompt (prompts/endpoint_validation_prompt.txt)
"""
You are a backend API validation expert analyzing OpenAPI endpoints.

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
[... categories ...]

OUTPUT FORMAT:
[... format specification ...]

ANALYZE NOW:
"""
```

**Testing**:
```python
# Test prompt with POST /users endpoint
python scripts/test_endpoint_prompt.py --method POST --path /users --spec specs/ecommerce.yaml

# Expected output: 6-8 validations for endpoint
```

**Success Criteria**:
- ✅ Extracts request body validations
- ✅ Extracts path parameter validations
- ✅ Identifies HTTP method semantics (POST → body required)
- ✅ Infers validations from response codes (409 → uniqueness)

#### Task 1.3: Design Cross-Entity Prompt (4h)

**Deliverables**:
- `prompts/cross_entity_validation_prompt.txt`
- `prompts/cross_entity_examples.json`
- `prompts/cross_entity_validation_guide.md`

**Implementation**:
```python
# Cross-entity prompt (prompts/cross_entity_validation_prompt.txt)
"""
You are a backend architect analyzing OpenAPI specifications for cross-entity validations.

TASK: Identify validations that span multiple entities or involve relationships.

ENTITIES AND RELATIONSHIPS:
{entities_relationships_json}

ENDPOINTS OVERVIEW:
{endpoints_summary_json}

CROSS-ENTITY VALIDATION TYPES:
[... types ...]

OUTPUT FORMAT:
[... format specification ...]

ANALYZE NOW:
"""
```

**Testing**:
```python
# Test prompt with Order/OrderItem/Product relationships
python scripts/test_cross_entity_prompt.py --spec specs/ecommerce.yaml

# Expected output: 5-7 cross-entity validations
```

**Success Criteria**:
- ✅ Identifies foreign key relationships
- ✅ Infers business logic (stock checks, cascades)
- ✅ Detects workflow constraints (status transitions)

### Day 3: Pydantic Schema Design (4h)

#### Task 1.4: Define Validation Response Schema

**Deliverables**:
- `src/services/llm_validation_schema.py` - Pydantic models

**Implementation**:
```python
# src/services/llm_validation_schema.py

from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, List
from src.cognitive.ir.validation_model import ValidationType, ValidationRule

class LLMValidation(BaseModel):
    """Schema for LLM-extracted validation"""

    entity: str = Field(..., description="Entity/model name")
    attribute: str = Field(..., description="Field or parameter name")
    type: str = Field(..., description="Validation category (string)")
    condition: str = Field(..., description="Validation rule")
    error_message: str = Field(..., description="User-facing error message")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    rationale: str = Field(..., description="Why this validation exists")

    # Optional fields
    scope: Optional[Literal["request", "response", "both"]] = None
    related_entity: Optional[str] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    def to_validation_rule(self) -> ValidationRule:
        """Convert to internal ValidationRule format"""
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

        val_type = validation_type_map.get(self.type.upper(), ValidationType.PRESENCE)

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
        seen = set()
        unique = []
        for val in v:
            key = (val.entity, val.attribute, val.type, val.condition)
            if key not in seen:
                seen.add(key)
                unique.append(val)
        return unique
```

**Testing**:
```python
# Test Pydantic schema validation
python -m pytest tests/services/test_llm_validation_schema.py

# Test valid responses
# Test invalid responses (should raise validation errors)
# Test to_validation_rule() conversion
```

**Success Criteria**:
- ✅ Schema validates correct JSON responses
- ✅ Schema rejects invalid responses (missing fields, wrong types)
- ✅ `to_validation_rule()` conversion works correctly

### Day 4-5: Prompt Refinement & Validation (8h)

#### Task 1.5: Manual Testing & Refinement

**Approach**:
1. Run prompts on 5 sample entities/endpoints
2. Manually review LLM outputs for quality
3. Identify common issues (formatting, missing validations, false positives)
4. Refine prompts based on findings
5. Re-test until quality threshold reached

**Test Entities**:
- User (simple, 4 fields)
- Product (medium, 6 fields with stock)
- Order (complex, relationships, status)
- OrderItem (relationships, calculations)
- Category (simple, 3 fields)

**Quality Metrics**:
- JSON validity: >95% (should always return valid JSON)
- Validation completeness: >90% (catch all explicit validations)
- False positives: <10% (avoid spurious validations)
- Confidence accuracy: >85% (confidence matches actual correctness)

**Refinement Areas**:
- Adjust validation type categories (ensure LLM uses correct types)
- Add more examples to prompts (improve accuracy)
- Refine error message templates (consistent wording)
- Adjust confidence guidance (clearer criteria)

#### Task 1.6: Automated Testing Suite

**Deliverables**:
- `tests/services/test_llm_prompts.py` - Automated prompt tests

```python
# tests/services/test_llm_prompts.py

import pytest
from src.services.business_logic_extractor import BusinessLogicExtractor

@pytest.fixture
def extractor():
    return BusinessLogicExtractor()

def test_field_prompt_user_entity(extractor):
    """Test field-level prompt on User entity."""
    entity = {
        "name": "User",
        "fields": [
            {"name": "id", "type": "UUID", "required": True, "unique": True},
            {"name": "email", "type": "String", "required": True, "unique": True,
             "constraints": {"format": "email"}},
        ]
    }

    validations = extractor._extract_field_validations_llm({"entities": [entity]})

    # Should find 5+ validations (id: 3, email: 2+)
    assert len(validations) >= 5

    # Should include specific validations
    validation_tuples = [(v.entity, v.attribute, v.type) for v in validations]
    assert ("User", "id", ValidationType.FORMAT) in validation_tuples
    assert ("User", "email", ValidationType.UNIQUENESS) in validation_tuples


def test_endpoint_prompt_post_users(extractor):
    """Test endpoint-level prompt on POST /users."""
    endpoint = {
        "method": "POST",
        "path": "/users",
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "required": ["email", "name"]
                    }
                }
            }
        }
    }

    validations = extractor._extract_endpoint_validations_llm({"endpoints": [endpoint]})

    # Should find 3+ validations (body, email, name)
    assert len(validations) >= 3

    # Should include body required validation
    validation_tuples = [(v.entity, v.attribute, v.type) for v in validations]
    assert any("body" in attr.lower() for _, attr, _ in validation_tuples)


def test_cross_entity_prompt(extractor):
    """Test cross-entity prompt on Order/OrderItem/Product."""
    spec = {
        "entities": [
            {"name": "Order", "fields": [{"name": "customer_id", "type": "UUID"}]},
            {"name": "OrderItem", "fields": [
                {"name": "order_id", "type": "UUID"},
                {"name": "product_id", "type": "UUID"},
            ]},
        ]
    }

    validations = extractor._extract_cross_entity_validations_llm(spec)

    # Should find 2+ foreign key relationships
    assert len(validations) >= 2

    # Should include foreign key validations
    assert any(v.type == ValidationType.RELATIONSHIP for v in validations)
```

**Success Criteria**:
- ✅ All prompt tests pass
- ✅ Prompts produce consistent results (deterministic at temp=0)
- ✅ Coverage metrics meet targets (>90% completeness)

---

## Week 2: Core Implementation (Days 6-10)

### Day 6-7: LLM Extraction Methods (8h)

#### Task 2.1: Implement Field-Level Extraction

**Deliverables**:
- Modify `src/services/business_logic_extractor.py`

```python
# src/services/business_logic_extractor.py

def _extract_field_validations_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Extract field-level validations using LLM for ALL entity fields.
    Batches fields per entity to minimize API calls.
    """
    rules = []
    entities = spec.get("entities", [])

    if not entities:
        return rules

    # Load prompt template
    prompt_template = self._load_prompt_template("field_validation_prompt.txt")

    for entity in entities:
        entity_name = entity.get("name", "Unknown")
        fields = entity.get("fields", [])

        if not fields:
            continue

        # Prepare field data
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
        prompt = prompt_template.format(
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
                    logger.warning(f"Failed to convert validation: {e}")

        except Exception as e:
            logger.warning(f"LLM field extraction failed for {entity_name}: {e}")
            continue

    return rules


def _load_prompt_template(self, filename: str) -> str:
    """Load prompt template from prompts/ directory."""
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    template_path = prompts_dir / filename

    with open(template_path, 'r') as f:
        return f.read()
```

#### Task 2.2: Implement Endpoint-Level Extraction

```python
def _extract_endpoint_validations_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Extract endpoint-level validations using LLM for ALL endpoints.
    """
    rules = []
    endpoints = spec.get("endpoints", [])

    if not endpoints:
        return rules

    # Load prompt template
    prompt_template = self._load_prompt_template("endpoint_validation_prompt.txt")

    for endpoint in endpoints:
        method = endpoint.get("method", "GET").upper()
        path = endpoint.get("path", "")
        operation_id = endpoint.get("operation_id", "")

        # Prepare data
        request_body_json = json.dumps(endpoint.get("request_body", {}), indent=2)
        response_schemas_json = json.dumps(endpoint.get("responses", {}), indent=2)

        # Build prompt
        prompt = prompt_template.format(
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

            for val in validations:
                try:
                    rule = val.to_validation_rule()
                    rules.append(rule)
                except Exception as e:
                    logger.warning(f"Failed to convert validation: {e}")

        except Exception as e:
            logger.warning(f"LLM endpoint extraction failed for {method} {path}: {e}")
            continue

    return rules
```

#### Task 2.3: Implement Cross-Entity Extraction

```python
def _extract_cross_entity_validations_llm(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Extract cross-entity validations using LLM.
    Single call analyzing all entities and relationships.
    """
    rules = []
    entities = spec.get("entities", [])

    if not entities:
        return rules

    # Build relationships map
    relationships = {}
    for entity in entities:
        entity_name = entity.get("name", "")
        entity_fields = []

        for field in entity.get("fields", []):
            field_name = field.get("name", "")
            field_type = field.get("type", "")

            # Detect foreign keys
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
    endpoints_summary = [
        {
            "method": e.get("method", "GET"),
            "path": e.get("path", ""),
            "entity": self._infer_entity_from_path(e.get("path", ""), entities)
        }
        for e in spec.get("endpoints", [])
    ]

    # Prepare JSON
    entities_relationships_json = json.dumps(relationships, indent=2)
    endpoints_summary_json = json.dumps(endpoints_summary, indent=2)

    # Load prompt template
    prompt_template = self._load_prompt_template("cross_entity_validation_prompt.txt")

    # Build prompt
    prompt = prompt_template.format(
        entities_relationships_json=entities_relationships_json,
        endpoints_summary_json=endpoints_summary_json
    )

    # Call LLM
    try:
        response = self._call_llm(prompt)
        validations = self._parse_llm_response(response)

        for val in validations:
            try:
                rule = val.to_validation_rule()
                rules.append(rule)
            except Exception as e:
                logger.warning(f"Failed to convert validation: {e}")

    except Exception as e:
        logger.error(f"LLM cross-entity extraction failed: {e}")

    return rules
```

### Day 8: LLM API Integration (4h)

#### Task 2.4: Implement LLM Call & Parsing

```python
import time
import anthropic

class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 50):
        self.calls_per_minute = calls_per_minute
        self.call_times = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        self.call_times = [t for t in self.call_times if now - t < 60]

        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self.call_times.append(now)


def __init__(self):
    # Existing init code...
    self.rate_limiter = RateLimiter(calls_per_minute=50)


def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
    """Call Claude API with rate limiting and retry logic."""

    for attempt in range(max_retries):
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed()

            # Call API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.0,  # Deterministic
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
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
        from src.services.llm_validation_schema import LLMValidationResponse
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

### Day 9-10: Pipeline Integration (8h)

#### Task 2.5: Refactor Stage 7 in extract_validation_rules()

```python
def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
    """
    Extract ALL validation rules from specification.
    Phase 2: LLM-Primary extraction for comprehensive coverage.
    """
    rules = []

    # Stage 1-6: Direct, Pattern-based extraction (unchanged)
    if "entities" in spec:
        rules.extend(self._extract_from_entities(spec["entities"]))

    rules.extend(self._extract_from_field_descriptions(spec.get("entities", [])))

    if "endpoints" in spec:
        try:
            rules.extend(self._extract_from_endpoints(
                spec.get("endpoints", []),
                spec.get("entities", [])
            ))
        except Exception as e:
            logger.warning(f"Endpoint extraction failed: {e}")

    if "endpoints" in spec or "workflows" in spec:
        rules.extend(self._extract_from_workflows(spec))

    if "schema" in spec or "database_schema" in spec:
        rules.extend(self._extract_constraint_validations(spec))

    if "validation_rules" in spec or "business_rules" in spec:
        rules.extend(self._extract_business_rules(spec))

    # Stage 6.5: Pattern-based extraction
    try:
        pattern_rules = self._extract_pattern_rules(spec)
        rules.extend(pattern_rules)
        logger.info(f"Pattern extraction: {len(pattern_rules)} validations")
    except Exception as e:
        logger.warning(f"Pattern extraction failed: {e}")

    # Stage 7: LLM-Primary Extraction (NEW - Phase 2)
    try:
        llm_rules = []

        # Stage 7a: Field-level validations
        field_rules = self._extract_field_validations_llm(spec)
        llm_rules.extend(field_rules)
        logger.info(f"LLM field extraction: {len(field_rules)} validations")

        # Stage 7b: Endpoint validations
        endpoint_rules = self._extract_endpoint_validations_llm(spec)
        llm_rules.extend(endpoint_rules)
        logger.info(f"LLM endpoint extraction: {len(endpoint_rules)} validations")

        # Stage 7c: Cross-entity validations
        cross_rules = self._extract_cross_entity_validations_llm(spec)
        llm_rules.extend(cross_rules)
        logger.info(f"LLM cross-entity extraction: {len(cross_rules)} validations")

        rules.extend(llm_rules)
        logger.info(f"Total LLM extraction: {len(llm_rules)} validations")

    except Exception as e:
        logger.error(f"LLM extraction failed: {e}, continuing with pattern-only")

    # Stage 8: Deduplicate rules
    rules = self._deduplicate_rules(rules)
    logger.info(f"Final validation count after deduplication: {len(rules)}")

    return ValidationModelIR(rules=rules)
```

#### Task 2.6: Add Provenance Tracking

```python
# Modify ValidationRule to support metadata (if not already present)
# In src/cognitive/ir/validation_model.py

@dataclass
class ValidationRule:
    entity: str
    attribute: str
    type: ValidationType
    condition: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # NEW


# Update all extraction methods to add provenance

# In _extract_from_entities():
rule = ValidationRule(
    entity=entity_name,
    attribute=field_name,
    type=ValidationType.PRESENCE,
    error_message=f"{field_name} is required",
    metadata={"provenance": "direct"}  # NEW
)

# In _extract_pattern_rules():
rule = ValidationRule(
    entity=entity_name,
    attribute=field_name,
    type=ValidationType[val_type],
    condition=validation.get("condition", ""),
    error_message=error_msg,
    metadata={"provenance": "pattern"}  # NEW
)

# In LLMValidation.to_validation_rule():
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

## Week 3: Testing & Validation (Days 11-15)

### Day 11-12: Unit Testing (8h)

#### Task 3.1: Write Unit Tests for LLM Methods

```python
# tests/services/test_llm_extraction_methods.py

import pytest
from src.services.business_logic_extractor import BusinessLogicExtractor
from src.cognitive.ir.validation_model import ValidationType

@pytest.fixture
def extractor():
    return BusinessLogicExtractor()


class TestFieldLevelExtraction:
    """Test _extract_field_validations_llm()"""

    def test_extracts_basic_validations(self, extractor):
        spec = {
            "entities": [{
                "name": "User",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True},
                    {"name": "email", "type": "String", "required": True, "unique": True}
                ]
            }]
        }

        rules = extractor._extract_field_validations_llm(spec)

        # Should extract multiple validations
        assert len(rules) >= 3
        assert any(r.attribute == "id" for r in rules)
        assert any(r.attribute == "email" for r in rules)

    def test_handles_empty_entities(self, extractor):
        spec = {"entities": []}
        rules = extractor._extract_field_validations_llm(spec)
        assert rules == []

    def test_handles_missing_fields(self, extractor):
        spec = {"entities": [{"name": "User", "fields": []}]}
        rules = extractor._extract_field_validations_llm(spec)
        assert rules == []


class TestEndpointLevelExtraction:
    """Test _extract_endpoint_validations_llm()"""

    def test_extracts_post_endpoint_validations(self, extractor):
        spec = {
            "endpoints": [{
                "method": "POST",
                "path": "/users",
                "request_body": {"required": True}
            }]
        }

        rules = extractor._extract_endpoint_validations_llm(spec)

        # Should extract body required validation
        assert len(rules) >= 1
        assert any("body" in r.attribute.lower() for r in rules)


class TestCrossEntityExtraction:
    """Test _extract_cross_entity_validations_llm()"""

    def test_extracts_foreign_key_relationships(self, extractor):
        spec = {
            "entities": [
                {"name": "Order", "fields": [{"name": "customer_id", "type": "UUID"}]},
                {"name": "Customer", "fields": [{"name": "id", "type": "UUID"}]}
            ]
        }

        rules = extractor._extract_cross_entity_validations_llm(spec)

        # Should extract foreign key validation
        assert len(rules) >= 1
        assert any(r.type == ValidationType.RELATIONSHIP for r in rules)


class TestLLMHelpers:
    """Test _call_llm() and _parse_llm_response()"""

    def test_call_llm_success(self, extractor):
        prompt = "Return JSON: []"
        response = extractor._call_llm(prompt)
        assert isinstance(response, str)

    def test_parse_valid_json(self, extractor):
        response = '''[
            {
                "entity": "User",
                "attribute": "email",
                "type": "FORMAT",
                "condition": "email format",
                "error_message": "Invalid email",
                "confidence": 0.9,
                "rationale": "Schema defines email format"
            }
        ]'''

        validations = extractor._parse_llm_response(response)
        assert len(validations) == 1
        assert validations[0].entity == "User"

    def test_parse_handles_markdown(self, extractor):
        response = '''```json
        [{"entity": "User", "attribute": "email", "type": "FORMAT",
          "condition": "", "error_message": "", "confidence": 0.9, "rationale": ""}]
        ```'''

        validations = extractor._parse_llm_response(response)
        assert len(validations) == 1

    def test_parse_handles_invalid_json(self, extractor):
        response = "This is not JSON"
        validations = extractor._parse_llm_response(response)
        assert validations == []
```

### Day 13-14: E2E Testing (8h)

#### Task 3.2: Write E2E Tests for Phase 2 Coverage

```python
# tests/e2e/test_phase2_llm_validation.py

import pytest
from src.services.business_logic_extractor import BusinessLogicExtractor
from src.cognitive.ir.validation_model import ValidationType
import yaml

@pytest.fixture
def ecommerce_spec():
    """Load e-commerce spec for testing."""
    spec_path = "specs/ecommerce_openapi.yaml"
    with open(spec_path, 'r') as f:
        return yaml.safe_load(f)


class TestPhase2Coverage:
    """Test Phase 2 achieves 97%+ coverage target."""

    def test_achieves_60_plus_validations(self, ecommerce_spec):
        """Test Phase 2 extracts 60+ validations."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        # Expected: 60-62 validations
        assert len(validation_ir.rules) >= 60, \
            f"Expected ≥60 validations, got {len(validation_ir.rules)}"

    def test_achieves_97_percent_coverage(self, ecommerce_spec):
        """Test Phase 2 achieves 97%+ coverage."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        # Coverage calculation
        expected_total = 62  # Ground truth
        coverage = len(validation_ir.rules) / expected_total

        assert coverage >= 0.97, \
            f"Expected ≥97% coverage, got {coverage:.1%}"

    def test_llm_finds_missing_validations(self, ecommerce_spec):
        """Test LLM extraction finds validations pattern-based missed."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        # Specific validations LLM should find
        llm_expected = [
            ("User", "id", ValidationType.FORMAT),  # UUID format
            ("User", "email", ValidationType.UNIQUENESS),  # Email unique
            ("Order", "customer_id", ValidationType.RELATIONSHIP),  # FK
            ("OrderItem", "quantity", ValidationType.RANGE),  # Quantity range
            ("Product", "stock", ValidationType.STOCK_CONSTRAINT),  # Stock check
        ]

        for entity, attr, val_type in llm_expected:
            matching = next(
                (r for r in validation_ir.rules
                 if r.entity == entity and r.attribute == attr and r.type == val_type),
                None
            )
            assert matching is not None, \
                f"Expected {val_type} validation for {entity}.{attr}"


class TestValidationBreakdown:
    """Test validation distribution across categories."""

    def test_presence_validations(self, ecommerce_spec):
        """Test PRESENCE validations: expect 18."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        presence_rules = [r for r in validation_ir.rules if r.type == ValidationType.PRESENCE]
        assert len(presence_rules) >= 18

    def test_format_validations(self, ecommerce_spec):
        """Test FORMAT validations: expect 12."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        format_rules = [r for r in validation_ir.rules if r.type == ValidationType.FORMAT]
        assert len(format_rules) >= 12

    def test_relationship_validations(self, ecommerce_spec):
        """Test RELATIONSHIP validations: expect 10."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        rel_rules = [r for r in validation_ir.rules if r.type == ValidationType.RELATIONSHIP]
        assert len(rel_rules) >= 10


class TestDeduplication:
    """Test deduplication keeps best rules."""

    def test_keeps_highest_priority_rule(self, ecommerce_spec):
        """Test deduplication prefers direct > pattern > LLM."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        # Find User.email UNIQUENESS rule
        email_unique = next(
            (r for r in validation_ir.rules
             if r.entity == "User" and r.attribute == "email"
             and r.type == ValidationType.UNIQUENESS),
            None
        )

        assert email_unique is not None
        assert email_unique.metadata.get("provenance") in ["direct", "pattern"]
        # Should NOT be "llm" if direct/pattern found it

    def test_merges_complementary_conditions(self, ecommerce_spec):
        """Test deduplication merges conditions from multiple sources."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        # Find rules with merged conditions
        merged_rules = [r for r in validation_ir.rules if r.condition and " AND " in r.condition]

        # Should have some merged rules
        assert len(merged_rules) > 0
```

### Day 15: Performance & Cost Testing (4h)

#### Task 3.3: Benchmark Performance & Cost

```python
# tests/performance/test_phase2_performance.py

import pytest
import time
from src.services.business_logic_extractor import BusinessLogicExtractor

def test_extraction_time_under_30_seconds():
    """Test extraction completes within 30 seconds."""
    spec = load_ecommerce_spec()
    extractor = BusinessLogicExtractor()

    start = time.time()
    validation_ir = extractor.extract_validation_rules(spec)
    duration = time.time() - start

    assert duration < 30, f"Extraction took {duration:.1f}s (expected <30s)"


def test_llm_calls_under_15():
    """Test LLM calls are ≤15 per spec."""
    spec = load_ecommerce_spec()
    extractor = BusinessLogicExtractor()

    # Track LLM calls
    call_count = 0
    original_call = extractor._call_llm

    def tracked_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_call(*args, **kwargs)

    extractor._call_llm = tracked_call

    validation_ir = extractor.extract_validation_rules(spec)

    assert call_count <= 15, f"Made {call_count} LLM calls (expected ≤15)"


def test_cost_under_15_cents():
    """Test cost per spec is ≤$0.15."""
    # This would require token tracking in production
    # For now, estimate based on call count

    spec = load_ecommerce_spec()
    extractor = BusinessLogicExtractor()

    # Track calls
    call_count = 0
    original_call = extractor._call_llm

    def tracked_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_call(*args, **kwargs)

    extractor._call_llm = tracked_call

    validation_ir = extractor.extract_validation_rules(spec)

    # Estimate cost: ~$0.011 per call
    estimated_cost = call_count * 0.011

    assert estimated_cost <= 0.15, \
        f"Estimated cost ${estimated_cost:.3f} (expected ≤$0.15)"
```

---

## Week 4: Optimization & Polish (Days 16-20)

### Day 16-17: Optimization (8h)

#### Task 4.1: Optimize Batching Strategy

**Current**: 1 LLM call per entity (field-level) = 5 calls
**Optimization**: Batch multiple small entities in single call = 2-3 calls

```python
def _extract_field_validations_llm_optimized(self, spec: Dict[str, Any]) -> List[ValidationRule]:
    """
    Optimized version: batch small entities together.
    """
    rules = []
    entities = spec.get("entities", [])

    if not entities:
        return rules

    # Group entities by size
    small_entities = []  # ≤3 fields
    large_entities = []  # >3 fields

    for entity in entities:
        fields = entity.get("fields", [])
        if len(fields) <= 3:
            small_entities.append(entity)
        else:
            large_entities.append(entity)

    # Batch small entities (up to 3 per call)
    for i in range(0, len(small_entities), 3):
        batch = small_entities[i:i+3]
        rules.extend(self._extract_batch_field_validations(batch))

    # Process large entities individually
    for entity in large_entities:
        rules.extend(self._extract_single_entity_validations(entity))

    return rules
```

#### Task 4.2: Add Caching for Repeated Extractions

```python
import hashlib
import pickle
from pathlib import Path

class ExtractionCache:
    """Cache for LLM extraction results."""

    def __init__(self, cache_dir: Path = Path(".cache/validations")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, spec: Dict[str, Any]) -> str:
        """Generate cache key from spec."""
        spec_str = json.dumps(spec, sort_keys=True)
        return hashlib.sha256(spec_str.encode()).hexdigest()

    def get(self, spec: Dict[str, Any]) -> Optional[List[ValidationRule]]:
        """Get cached validations if available."""
        cache_key = self.get_cache_key(spec)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def set(self, spec: Dict[str, Any], rules: List[ValidationRule]):
        """Cache validation rules."""
        cache_key = self.get_cache_key(spec)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        with open(cache_file, 'wb') as f:
            pickle.dump(rules, f)


# In BusinessLogicExtractor.__init__():
self.cache = ExtractionCache()

# In extract_validation_rules():
# Check cache first
cached_rules = self.cache.get(spec)
if cached_rules:
    logger.info(f"Using cached validations ({len(cached_rules)} rules)")
    return ValidationModelIR(rules=cached_rules)

# ... normal extraction ...

# Cache result
self.cache.set(spec, rules)
```

### Day 18: Metrics & Logging (4h)

#### Task 4.3: Add Observability

```python
import logging
from dataclasses import dataclass, asdict
from typing import Dict

@dataclass
class ExtractionMetrics:
    """Metrics for validation extraction."""
    total_entities: int = 0
    total_fields: int = 0
    total_endpoints: int = 0

    direct_rules: int = 0
    pattern_rules: int = 0
    llm_field_rules: int = 0
    llm_endpoint_rules: int = 0
    llm_cross_entity_rules: int = 0

    llm_calls: int = 0
    extraction_time_seconds: float = 0.0

    final_rule_count: int = 0
    deduplication_savings: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


# In extract_validation_rules():
def extract_validation_rules(self, spec: Dict[str, Any]) -> ValidationModelIR:
    """Extract validations with metrics tracking."""

    metrics = ExtractionMetrics()
    start_time = time.time()

    # Track input size
    metrics.total_entities = len(spec.get("entities", []))
    metrics.total_fields = sum(
        len(e.get("fields", []))
        for e in spec.get("entities", [])
    )
    metrics.total_endpoints = len(spec.get("endpoints", []))

    rules = []

    # Stage 1-6: Direct/Pattern extraction
    direct_rules = self._extract_from_entities(spec["entities"])
    metrics.direct_rules = len(direct_rules)
    rules.extend(direct_rules)

    pattern_rules = self._extract_pattern_rules(spec)
    metrics.pattern_rules = len(pattern_rules)
    rules.extend(pattern_rules)

    # Stage 7: LLM extraction (with call tracking)
    original_call = self._call_llm
    def tracked_call(*args, **kwargs):
        metrics.llm_calls += 1
        return original_call(*args, **kwargs)
    self._call_llm = tracked_call

    field_rules = self._extract_field_validations_llm(spec)
    metrics.llm_field_rules = len(field_rules)
    rules.extend(field_rules)

    endpoint_rules = self._extract_endpoint_validations_llm(spec)
    metrics.llm_endpoint_rules = len(endpoint_rules)
    rules.extend(endpoint_rules)

    cross_rules = self._extract_cross_entity_validations_llm(spec)
    metrics.llm_cross_entity_rules = len(cross_rules)
    rules.extend(cross_rules)

    # Restore original
    self._call_llm = original_call

    # Stage 8: Deduplication
    pre_dedup_count = len(rules)
    rules = self._deduplicate_rules(rules)
    metrics.final_rule_count = len(rules)
    metrics.deduplication_savings = pre_dedup_count - len(rules)

    # Timing
    metrics.extraction_time_seconds = time.time() - start_time

    # Log metrics
    logger.info(f"Extraction metrics: {metrics.to_dict()}")

    return ValidationModelIR(rules=rules)
```

### Day 19-20: Documentation & Polish (8h)

#### Task 4.4: Update Documentation

**Deliverables**:
- Update `README.md` with Phase 2 achievements
- Create `DOCS/PHASE2_MIGRATION_GUIDE.md`
- Update `DOCS/LEARNING_LAYER_INTEGRATION.md`
- Create `DOCS/PHASE2_RESULTS.md` (performance report)

**README.md Update**:
```markdown
## Validation Extraction (Phase 2)

Phase 2 introduces LLM-primary validation extraction, achieving **97-100% coverage** (60-62/62 validations).

### Coverage Results

| Phase | Validations | Coverage | Improvement |
|-------|------------|----------|-------------|
| Phase 1 (Pattern-Based) | 45/62 | 73% | Baseline |
| Phase 2 (LLM-Primary) | 60-62/62 | 97-100% | +24-27% |

### LLM Extraction Strategy

Phase 2 uses 3 specialized LLM prompts:
1. **Field-Level**: Extracts validations for all entity fields
2. **Endpoint-Level**: Extracts request/response validations
3. **Cross-Entity**: Identifies relationships and business logic

### Performance

- **LLM Calls**: 7-11 per spec (optimized batching)
- **Cost**: ~$0.12 per spec (+$0.11 vs Phase 1)
- **Time**: ~20-25 seconds (acceptable)
- **ROI**: <$0.01 per validation (excellent)

### Usage

```python
from src.services.business_logic_extractor import BusinessLogicExtractor

extractor = BusinessLogicExtractor()
validation_ir = extractor.extract_validation_rules(spec)

print(f"Extracted {len(validation_ir.rules)} validations")
```
```

#### Task 4.5: Create Migration Guide

```markdown
# Phase 2 Migration Guide

## Upgrading from Phase 1 to Phase 2

Phase 2 is **backward compatible** with Phase 1. No changes required to existing code.

### What Changed

1. **New LLM Extraction Methods**:
   - `_extract_field_validations_llm()`
   - `_extract_endpoint_validations_llm()`
   - `_extract_cross_entity_validations_llm()`

2. **Enhanced Deduplication**:
   - Provenance tracking (`direct`, `pattern`, `llm`)
   - Confidence-based rule selection
   - Condition merging for complementary rules

3. **New Dependencies**:
   - Pydantic schemas (`src/services/llm_validation_schema.py`)
   - Prompt templates (`prompts/*.txt`)
   - Rate limiting (`RateLimiter` class)

### Breaking Changes

**None**. Phase 2 is fully backward compatible.

### Configuration

**Optional**: Set environment variable for API key (if not already set):
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**Optional**: Configure rate limiting (default: 50 calls/min):
```python
extractor = BusinessLogicExtractor()
extractor.rate_limiter.calls_per_minute = 30  # Adjust if needed
```

### Rollback

To revert to Phase 1 behavior, set environment variable:
```bash
export DISABLE_LLM_EXTRACTION=true
```

Or modify code:
```python
# In extract_validation_rules()
if not os.getenv("DISABLE_LLM_EXTRACTION"):
    # Stage 7: LLM extraction
    ...
```
```

---

## Success Criteria Checklist

### Functional Requirements
- [ ] Achieve 60-62 validations on e-commerce spec
- [ ] LLM extraction contributes 15-17 new validations
- [ ] All 3 LLM prompts work reliably (>95% JSON validity)
- [ ] Deduplication preserves highest priority rules
- [ ] Error handling prevents LLM failures from breaking pipeline

### Performance Requirements
- [ ] Total LLM calls per spec: ≤15
- [ ] Cost per spec: ≤$0.15
- [ ] Extraction time: ≤30 seconds
- [ ] Rate limiting prevents API errors

### Quality Requirements
- [ ] Validation confidence scores: 0.85+ for LLM rules
- [ ] False positives: <5%
- [ ] Missing validations: <3%
- [ ] Provenance tracking: 100% of rules

### Testing Requirements
- [ ] All unit tests pass (>95% code coverage)
- [ ] All E2E tests pass (coverage, breakdown, deduplication)
- [ ] Performance tests pass (time, cost, calls)
- [ ] Manual validation on 5+ sample specs

### Documentation Requirements
- [ ] README.md updated with Phase 2 results
- [ ] Migration guide created
- [ ] Prompt engineering guide created
- [ ] Performance report created
- [ ] Code comments and docstrings added

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| LLM returns invalid JSON | Medium | High | Retry logic, Pydantic validation, fallback | Engineer |
| Cost overruns (>$0.15/spec) | Low | Medium | Batching optimization, caching, monitoring | Engineer |
| Rate limiting errors | Low | Medium | RateLimiter class, exponential backoff | Engineer |
| False positives (>5%) | Medium | Medium | Confidence thresholds, manual review | Reviewer |
| Extraction time >30s | Low | Low | Batching, caching, parallel calls | Engineer |
| Missing validations (>3%) | Low | High | Comprehensive prompts, manual validation | Reviewer |

---

## Next Steps After Phase 2

### Phase 3: Advanced LLM Techniques (Future)
- Multi-turn conversations for complex validations
- Chain-of-thought prompting for transparency
- Few-shot examples in prompts
- Ensemble extraction (multiple models)

### Phase 4: Learning & Adaptation (Future)
- Fine-tune model on validated extractions
- Build validation pattern library
- Active learning for uncertain rules
- Feedback loop for prompt improvement

### Phase 5: Domain-Specific Extractors (Future)
- E-commerce validation templates
- Healthcare/HIPAA compliance rules
- Financial/SOX validation patterns
- SaaS multi-tenancy validations

---

## Conclusion

Phase 2 implementation plan provides a structured, 4-week roadmap to achieve **97-100% validation coverage** through LLM-primary extraction. The plan balances comprehensive coverage with cost-effectiveness, achieving <$0.01 per validation for an excellent ROI.

**Key Milestones**:
- Week 1: Prompt engineering & schema design
- Week 2: Core implementation (LLM methods + pipeline integration)
- Week 3: Testing & validation (unit + E2E + performance)
- Week 4: Optimization & polish (batching + caching + docs)

**Expected Outcome**: Production-ready Phase 2 system with 60-62 validations (97-100% coverage) on e-commerce spec.
