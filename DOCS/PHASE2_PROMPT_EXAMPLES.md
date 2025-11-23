# Phase 2: LLM Prompt Examples & Expected Outputs

Concrete examples showing how Phase 2 LLM prompts extract validations from the e-commerce specification.

---

## Example 1: Field-Level Validation Extraction

### Input Spec (User Entity)

```json
{
  "name": "User",
  "fields": [
    {
      "name": "id",
      "type": "UUID",
      "required": true,
      "unique": true
    },
    {
      "name": "email",
      "type": "String",
      "required": true,
      "unique": true,
      "constraints": {
        "format": "email"
      }
    },
    {
      "name": "name",
      "type": "String",
      "required": true,
      "constraints": {
        "min_length": 2,
        "max_length": 100
      }
    },
    {
      "name": "created_at",
      "type": "DateTime",
      "required": true
    }
  ]
}
```

### LLM Prompt (Field-Level)

```
You are a backend validation expert analyzing OpenAPI specifications.

TASK: Extract ALL possible validations for the given fields.

CONTEXT:
Entity: User
Fields to analyze:
[
  {
    "name": "id",
    "type": "UUID",
    "required": true,
    "unique": true,
    "constraints": {},
    "description": ""
  },
  {
    "name": "email",
    "type": "String",
    "required": true,
    "unique": true,
    "constraints": {
      "format": "email"
    },
    "description": ""
  },
  {
    "name": "name",
    "type": "String",
    "required": true,
    "constraints": {
      "min_length": 2,
      "max_length": 100
    },
    "description": ""
  },
  {
    "name": "created_at",
    "type": "DateTime",
    "required": true,
    "constraints": {},
    "description": ""
  }
]

[... rest of prompt ...]

ANALYZE NOW:
```

### Expected LLM Output

```json
[
  {
    "entity": "User",
    "attribute": "id",
    "type": "FORMAT",
    "condition": "format: uuid v4",
    "error_message": "User ID must be a valid UUID",
    "confidence": 0.95,
    "rationale": "Field type is UUID, which requires UUID v4 format validation"
  },
  {
    "entity": "User",
    "attribute": "id",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "User ID is required",
    "confidence": 0.95,
    "rationale": "Field explicitly marked as required in schema"
  },
  {
    "entity": "User",
    "attribute": "id",
    "type": "UNIQUENESS",
    "condition": "unique: true",
    "error_message": "User ID must be unique",
    "confidence": 0.95,
    "rationale": "Field explicitly marked as unique in schema"
  },
  {
    "entity": "User",
    "attribute": "email",
    "type": "FORMAT",
    "condition": "format: email",
    "error_message": "Email must be a valid email address",
    "confidence": 0.95,
    "rationale": "Schema explicitly defines format: email constraint"
  },
  {
    "entity": "User",
    "attribute": "email",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Email is required",
    "confidence": 0.95,
    "rationale": "Field explicitly marked as required"
  },
  {
    "entity": "User",
    "attribute": "email",
    "type": "UNIQUENESS",
    "condition": "unique: true",
    "error_message": "Email must be unique",
    "confidence": 0.95,
    "rationale": "Email is marked as unique and is typical unique identifier"
  },
  {
    "entity": "User",
    "attribute": "name",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Name is required",
    "confidence": 0.95,
    "rationale": "Field explicitly marked as required"
  },
  {
    "entity": "User",
    "attribute": "name",
    "type": "RANGE",
    "condition": "length >= 2 AND length <= 100",
    "error_message": "Name must be between 2 and 100 characters",
    "confidence": 0.95,
    "rationale": "Schema defines min_length: 2 and max_length: 100"
  },
  {
    "entity": "User",
    "attribute": "created_at",
    "type": "FORMAT",
    "condition": "format: ISO 8601 datetime",
    "error_message": "Created at must be a valid datetime",
    "confidence": 0.95,
    "rationale": "Field type is DateTime requiring ISO 8601 format"
  },
  {
    "entity": "User",
    "attribute": "created_at",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Created at is required",
    "confidence": 0.95,
    "rationale": "Field explicitly marked as required"
  }
]
```

**Validations Found**: 10 (id: 3, email: 3, name: 2, created_at: 2)

**Pattern-Based Would Miss**:
- UUID format validation for `id`
- ISO 8601 datetime format for `created_at`
- Email uniqueness (pattern only checks "unique" flag, not semantic)

**LLM Advantage**: Understands semantic meaning of types (UUID → format validation, DateTime → ISO 8601)

---

## Example 2: Endpoint-Level Validation Extraction

### Input Spec (POST /users)

```json
{
  "method": "POST",
  "path": "/users",
  "operation_id": "createUser",
  "request_body": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "type": "object",
          "required": ["email", "name"],
          "properties": {
            "email": {
              "type": "string",
              "format": "email"
            },
            "name": {
              "type": "string",
              "minLength": 2,
              "maxLength": 100
            }
          }
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "User created successfully",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/User"
          }
        }
      }
    },
    "400": {
      "description": "Invalid request body"
    },
    "409": {
      "description": "Email already exists"
    }
  }
}
```

### LLM Prompt (Endpoint-Level)

```
You are a backend API validation expert analyzing OpenAPI endpoints.

TASK: Extract ALL request/response validations for the given endpoint.

ENDPOINT:
Method: POST
Path: /users
Operation: createUser

REQUEST BODY:
{
  "required": true,
  "content": {
    "application/json": {
      "schema": {
        "type": "object",
        "required": ["email", "name"],
        "properties": {
          "email": {
            "type": "string",
            "format": "email"
          },
          "name": {
            "type": "string",
            "minLength": 2,
            "maxLength": 100
          }
        }
      }
    }
  }
}

RESPONSE SCHEMAS:
{
  "201": {
    "description": "User created successfully",
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/User"
        }
      }
    }
  },
  "400": {
    "description": "Invalid request body"
  },
  "409": {
    "description": "Email already exists"
  }
}

[... rest of prompt ...]

ANALYZE NOW:
```

### Expected LLM Output

```json
[
  {
    "entity": "User",
    "attribute": "POST_body",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Request body is required",
    "confidence": 0.95,
    "rationale": "POST endpoint explicitly requires request body",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_email",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Email is required in request",
    "confidence": 0.95,
    "rationale": "Email is in required array of request body schema",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_email",
    "type": "FORMAT",
    "condition": "format: email",
    "error_message": "Email must be a valid email address",
    "confidence": 0.95,
    "rationale": "Request body schema defines format: email",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_email",
    "type": "UNIQUENESS",
    "condition": "unique: true",
    "error_message": "Email already exists",
    "confidence": 0.90,
    "rationale": "409 response indicates email uniqueness constraint",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_name",
    "type": "PRESENCE",
    "condition": "required: true",
    "error_message": "Name is required in request",
    "confidence": 0.95,
    "rationale": "Name is in required array of request body schema",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_name",
    "type": "RANGE",
    "condition": "length >= 2 AND length <= 100",
    "error_message": "Name must be between 2 and 100 characters",
    "confidence": 0.95,
    "rationale": "Request body schema defines minLength: 2 and maxLength: 100",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_content_type",
    "type": "FORMAT",
    "condition": "content-type: application/json",
    "error_message": "Content-Type must be application/json",
    "confidence": 0.90,
    "rationale": "Endpoint only accepts application/json content",
    "scope": "request"
  },
  {
    "entity": "User",
    "attribute": "POST_response_201",
    "type": "FORMAT",
    "condition": "schema: User",
    "error_message": "Response must conform to User schema",
    "confidence": 0.85,
    "rationale": "201 response references User schema",
    "scope": "response"
  }
]
```

**Validations Found**: 8

**Pattern-Based Would Miss**:
- Email uniqueness inferred from 409 response
- Content-Type header validation
- Response schema validation
- Request body requirement (POST semantics)

**LLM Advantage**: Understands HTTP semantics (POST requires body, 409 = conflict) and response codes

---

## Example 3: Cross-Entity Validation Extraction

### Input Spec (Order + OrderItem + Product)

```json
{
  "entities": [
    {
      "name": "Order",
      "fields": [
        {"name": "id", "type": "UUID"},
        {"name": "customer_id", "type": "UUID"},
        {"name": "status", "type": "String", "enum": ["pending", "confirmed", "shipped", "delivered"]},
        {"name": "total", "type": "Decimal"}
      ]
    },
    {
      "name": "OrderItem",
      "fields": [
        {"name": "id", "type": "UUID"},
        {"name": "order_id", "type": "UUID"},
        {"name": "product_id", "type": "UUID"},
        {"name": "quantity", "type": "Integer"},
        {"name": "price", "type": "Decimal"}
      ]
    },
    {
      "name": "Product",
      "fields": [
        {"name": "id", "type": "UUID"},
        {"name": "name", "type": "String"},
        {"name": "stock", "type": "Integer"},
        {"name": "price", "type": "Decimal"}
      ]
    }
  ],
  "endpoints": [
    {
      "method": "DELETE",
      "path": "/users/{id}",
      "operation_id": "deleteUser"
    },
    {
      "method": "POST",
      "path": "/orders",
      "operation_id": "createOrder"
    }
  ]
}
```

### LLM Prompt (Cross-Entity)

```
You are a backend architect analyzing OpenAPI specifications for cross-entity validations.

TASK: Identify validations that span multiple entities or involve relationships.

ENTITIES AND RELATIONSHIPS:
{
  "Order": [
    {
      "field": "customer_id",
      "type": "UUID",
      "references": "Customer"
    }
  ],
  "OrderItem": [
    {
      "field": "order_id",
      "type": "UUID",
      "references": "Order"
    },
    {
      "field": "product_id",
      "type": "UUID",
      "references": "Product"
    }
  ]
}

ENDPOINTS OVERVIEW:
[
  {
    "method": "DELETE",
    "path": "/users/{id}",
    "entity": "User"
  },
  {
    "method": "POST",
    "path": "/orders",
    "entity": "Order"
  }
]

[... rest of prompt ...]

ANALYZE NOW:
```

### Expected LLM Output

```json
[
  {
    "entity": "Order",
    "related_entity": "Customer",
    "attribute": "customer_id",
    "type": "RELATIONSHIP",
    "condition": "foreign_key: Customer.id exists",
    "error_message": "Customer with id '{id}' not found",
    "confidence": 0.95,
    "rationale": "Order references Customer via customer_id foreign key"
  },
  {
    "entity": "OrderItem",
    "related_entity": "Order",
    "attribute": "order_id",
    "type": "RELATIONSHIP",
    "condition": "foreign_key: Order.id exists",
    "error_message": "Order with id '{id}' not found",
    "confidence": 0.95,
    "rationale": "OrderItem references Order via order_id foreign key"
  },
  {
    "entity": "OrderItem",
    "related_entity": "Product",
    "attribute": "product_id",
    "type": "RELATIONSHIP",
    "condition": "foreign_key: Product.id exists",
    "error_message": "Product with id '{id}' not found",
    "confidence": 0.95,
    "rationale": "OrderItem references Product via product_id foreign key"
  },
  {
    "entity": "OrderItem",
    "related_entity": "Product",
    "attribute": "quantity",
    "type": "STOCK_CONSTRAINT",
    "condition": "product.stock >= orderitem.quantity",
    "error_message": "Insufficient stock for product",
    "confidence": 0.90,
    "rationale": "OrderItem quantity must not exceed Product stock"
  },
  {
    "entity": "User",
    "related_entity": "Order",
    "attribute": "delete_user",
    "type": "WORKFLOW_CONSTRAINT",
    "condition": "cascade: prevent if orders exist",
    "error_message": "Cannot delete user with existing orders",
    "confidence": 0.80,
    "rationale": "Business rule to preserve order history prevents user deletion"
  },
  {
    "entity": "Order",
    "related_entity": "OrderItem",
    "attribute": "status",
    "type": "WORKFLOW_CONSTRAINT",
    "condition": "status transition: pending → confirmed requires payment",
    "error_message": "Cannot confirm order without payment",
    "confidence": 0.75,
    "rationale": "Status transitions typically require business logic checks"
  },
  {
    "entity": "Order",
    "related_entity": "OrderItem",
    "attribute": "total",
    "type": "WORKFLOW_CONSTRAINT",
    "condition": "total = sum(orderitems.price * orderitems.quantity)",
    "error_message": "Order total must match sum of order items",
    "confidence": 0.85,
    "rationale": "Order total should be calculated from order items"
  }
]
```

**Validations Found**: 7

**Pattern-Based Would Miss**:
- Stock constraint (product.stock >= orderitem.quantity)
- User deletion cascade prevention
- Order status transition logic
- Order total calculation validation

**LLM Advantage**: Infers business logic relationships (stock checks, cascades, calculations) not explicit in spec

---

## Example 4: Combined Extraction Results

### Phase 1 (Pattern-Based): 45 validations

**Breakdown**:
- Direct extraction (entity fields): 30 validations
- Pattern rules (YAML): 15 validations
- LLM fallback: 0-2 validations

**Missing Categories**:
- Implicit format validations (UUID, datetime)
- Endpoint-specific validations (body required, content-type)
- Cross-entity business logic (stock checks, cascades)
- Response validations
- Security validations (authentication)

### Phase 2 (LLM-Primary): 60-62 validations

**Breakdown**:
- Direct extraction: 30 validations
- Pattern rules: 15 validations
- **LLM field-level: 12 validations** (NEW)
- **LLM endpoint-level: 8 validations** (NEW)
- **LLM cross-entity: 7 validations** (NEW)

**Total LLM Contribution**: 27 raw validations
**After Deduplication**: 15-17 unique validations (overlap with direct/pattern)

**Coverage Improvement**:
- Phase 1: 45/62 = 73%
- Phase 2: 60-62/62 = 97-100%
- Improvement: +24-27% coverage

---

## Example 5: Deduplication in Action

### Duplicate Scenario: User.email Uniqueness

**Rule 1 (Direct Extraction - Stage 1)**:
```json
{
  "entity": "User",
  "attribute": "email",
  "type": "UNIQUENESS",
  "condition": null,
  "error_message": "Email must be unique",
  "metadata": {"provenance": "direct"}
}
```

**Rule 2 (Pattern-Based - Stage 6.5)**:
```json
{
  "entity": "User",
  "attribute": "email",
  "type": "UNIQUENESS",
  "condition": "unique constraint on email column",
  "error_message": "Email must be unique",
  "metadata": {"provenance": "pattern"}
}
```

**Rule 3 (LLM Field-Level - Stage 7a)**:
```json
{
  "entity": "User",
  "attribute": "email",
  "type": "UNIQUENESS",
  "condition": "unique: true",
  "error_message": "Email must be unique",
  "metadata": {
    "provenance": "llm",
    "confidence": 0.95,
    "rationale": "Email is marked as unique and is typical unique identifier"
  }
}
```

### Deduplication Algorithm

```python
key = ("User", "email", "UNIQUENESS")

# Group rules by key
group = [rule1, rule2, rule3]

# Select best rule (highest provenance priority)
priority_map = {"direct": 3, "pattern": 2, "llm": 1}

best_rule = rule1  # provenance="direct" (priority=3)

# Merge conditions (combine complementary info)
conditions = [
    None,
    "unique constraint on email column",
    "unique: true"
]

merged_condition = "unique: true AND unique constraint on email column"

# Final deduplicated rule
final_rule = {
  "entity": "User",
  "attribute": "email",
  "type": "UNIQUENESS",
  "condition": "unique: true AND unique constraint on email column",
  "error_message": "Email must be unique",
  "metadata": {
    "provenance": "direct",
    "confidence": 0.95  # Inherit from LLM if available
  }
}
```

**Result**: 3 rules → 1 deduplicated rule with merged conditions

---

## Example 6: Cost & Performance Analysis

### E-Commerce Spec Characteristics

- **Entities**: 5 (User, Product, Order, OrderItem, Category)
- **Fields per Entity**: ~6 (avg)
- **Total Fields**: 30
- **Endpoints**: 15
- **Relationships**: 5 (customer_id, product_id, order_id, category_id, user_id)

### Phase 2 LLM Calls

**Field-Level Extraction**:
- Calls: 5 (1 per entity)
- Tokens per call: ~1500 (1000 input + 500 output)
- Total tokens: 7,500

**Endpoint-Level Extraction**:
- Calls: 5 (grouped by entity)
- Tokens per call: ~1500
- Total tokens: 7,500

**Cross-Entity Extraction**:
- Calls: 1 (entire spec)
- Tokens per call: ~2000
- Total tokens: 2,000

**Total**:
- **LLM Calls**: 11
- **Total Tokens**: 17,000
- **Input Tokens**: ~11,000 (65%)
- **Output Tokens**: ~6,000 (35%)

### Cost Calculation

**Model**: Claude Sonnet 3.5 (claude-3-5-sonnet-20241022)
- **Input**: $3 / 1M tokens
- **Output**: $15 / 1M tokens

**Cost Breakdown**:
- Input cost: 11,000 × $3 / 1M = $0.033
- Output cost: 6,000 × $15 / 1M = $0.090
- **Total cost**: $0.123 per spec

**Comparison**:
- Phase 1 cost: $0.01 (1 LLM call)
- Phase 2 cost: $0.12 (11 LLM calls)
- **Cost increase**: $0.11 per spec

**ROI Analysis**:
- Additional validations: +15
- Cost per validation: $0.11 / 15 = $0.0073
- Coverage improvement: +24% (73% → 97%)
- **Excellent ROI**: <$0.01 per validation for comprehensive coverage

### Time Performance

**Phase 1 (Pattern-Based)**:
- Direct extraction: 2s
- Pattern matching: 3s
- LLM fallback: 2s
- **Total**: ~7 seconds

**Phase 2 (LLM-Primary)**:
- Direct extraction: 2s
- Pattern matching: 3s
- LLM field-level: 5-8s (5 calls)
- LLM endpoint-level: 5-8s (5 calls)
- LLM cross-entity: 2s (1 call)
- **Total**: ~20-25 seconds

**Time increase**: +13-18 seconds (acceptable for comprehensive extraction)

---

## Summary

### Phase 2 LLM Extraction Advantages

1. **Semantic Understanding**: LLM understands type semantics (UUID → format, DateTime → ISO 8601)
2. **Business Logic Inference**: Infers cross-entity rules (stock checks, cascades) not explicit in spec
3. **HTTP Semantics**: Understands REST conventions (POST requires body, 409 = uniqueness conflict)
4. **Comprehensive Coverage**: Extracts validations from all dimensions (fields, endpoints, relationships)
5. **Confidence Scoring**: Assigns confidence based on explicitness (0.95 for spec, 0.75 for inferred)

### Expected Coverage Improvement

| Category | Phase 1 | Phase 2 | Improvement |
|----------|---------|---------|-------------|
| PRESENCE | 12 | 18 | +6 |
| FORMAT | 8 | 12 | +4 |
| UNIQUENESS | 6 | 8 | +2 |
| RANGE | 5 | 7 | +2 |
| RELATIONSHIP | 8 | 10 | +2 |
| STOCK_CONSTRAINT | 2 | 3 | +1 |
| STATUS_TRANSITION | 4 | 4 | 0 |
| **TOTAL** | **45** | **62** | **+17** |

### Cost-Benefit Analysis

- **Cost**: $0.12 per spec (+$0.11 vs Phase 1)
- **Coverage**: 97% vs 73% (+24%)
- **Validations**: 62 vs 45 (+17)
- **Cost per validation**: $0.0073 (excellent)
- **Time**: 25s vs 7s (+18s, acceptable)

**Conclusion**: Phase 2 LLM-Primary extraction is cost-effective and achieves near-complete validation coverage.
