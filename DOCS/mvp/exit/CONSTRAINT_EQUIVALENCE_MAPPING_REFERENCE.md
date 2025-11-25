# Constraint Equivalence Mapping Reference

**Document Version**: 1.0
**Date**: November 25, 2025
**Status**: 🟡 Reference for Phase 2 Implementation
**Purpose**: Canonical mappings for SemanticNormalizer and UnifiedConstraintExtractor

---

## 📋 Entity Name Equivalences

### Core E-Commerce Entities

| Canonical | Variations | Sources | Notes |
|-----------|-----------|---------|-------|
| `Product` | product, PRODUCT, prod, item, items | OpenAPI, AST, Business Logic | Base product entity |
| `Order` | order, ORDER, purchase, orders | OpenAPI, AST | Purchase orders |
| `OrderItem` | order_item, orderItem, order_line, line_item, items | OpenAPI, AST | Line items in orders |
| `User` | user, USER, customer, account, person | OpenAPI, AST | System users |
| `Inventory` | inventory, stock, warehouse, stock_item | OpenAPI, Business Logic | Stock management |
| `Category` | category, categories, cat | OpenAPI, AST | Product categories |
| `Review` | review, rating, reviews | OpenAPI, AST | Product reviews |
| `PaymentMethod` | payment_method, payment, paymentMethod | OpenAPI, AST | Payment information |

### General Rules
- Snake_case → camelCase → PascalCase (all resolve to canonical form)
- Plurals → Singular (items → item, then map to canonical entity)
- Abbreviations → Full name (prod → Product, cat → Category)
- Entity-specific abbreviations documented separately

---

## 🏷️ Field Name Equivalences

### Product Entity Fields

| Canonical | Variations | Constraint Type | Notes |
|-----------|-----------|-----------------|-------|
| `id` | productId, product_id, ID, pk | PRIMARY_KEY | Immutable |
| `name` | product_name, productName, title | REQUIRED, STRING_LENGTH | Required, max 255 |
| `description` | productDescription, desc, detail | REQUIRED, STRING_LENGTH | Optional in some contexts |
| `price` | unitPrice, unit_price, amount, cost, unitCost | RANGE_MIN, RANGE_MAX, FORMAT_NUMERIC | >0, ≤999999 |
| `quantity` | stock, inventory, qty, qty_available, quantity_available, stock_qty | RANGE_MIN, FORMAT_NUMERIC | ≥0 |
| `sku` | product_sku, SKU, sku_code, code | UNIQUE, STRING_LENGTH | Immutable |
| `category` | categoryId, category_id, category_name, categories | FOREIGN_KEY, REQUIRED | References Category |
| `status` | product_status, productStatus, state, availability | ENUM, REQUIRED | ACTIVE, INACTIVE, ARCHIVED |
| `createdAt` | created_at, created, creationDate, creation_date | TIMESTAMP, IMMUTABLE | Auto-set by system |
| `updatedAt` | updated_at, modified_at, modifiedAt, last_updated | TIMESTAMP, IMMUTABLE | Auto-updated |
| `deletedAt` | deleted_at, deletedAt, archived_at | TIMESTAMP, SOFT_DELETE | Soft delete marker |
| `weight` | product_weight, productWeight, mass | RANGE_MIN, FORMAT_NUMERIC | ≥0 |
| `dimensions` | size, productDimensions, product_dimensions | STRING_LENGTH, FORMAT_JSON | Structured data |
| `isActive` | is_active, active, enabled, visibility | BOOLEAN, DEFAULT | Default true |
| `tags` | product_tags, tag, labels | FORMAT_JSON_ARRAY | Array of strings |

### Order Entity Fields

| Canonical | Variations | Constraint Type | Notes |
|-----------|-----------|-----------------|-------|
| `id` | orderId, order_id, ID, order_number | PRIMARY_KEY | Immutable |
| `userId` | user_id, customerId, customer_id | FOREIGN_KEY, REQUIRED | References User |
| `status` | order_status, orderStatus, state | ENUM, REQUIRED | PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED |
| `totalPrice` | total, totalAmount, total_amount, grandTotal, grand_total | RANGE_MIN, FORMAT_NUMERIC | Computed from items |
| `shippingAddress` | shipping_address, shippingAddr, address | REQUIRED, FORMAT_JSON | Structured address |
| `billingAddress` | billing_address, billingAddr, billing | REQUIRED, FORMAT_JSON | Structured address |
| `shippingMethod` | shipping, shippingMethod, shipping_method | ENUM | STANDARD, EXPRESS, OVERNIGHT |
| `trackingNumber` | tracking_number, trackingNumber, tracking | STRING_LENGTH, UNIQUE | Only when shipped |
| `notes` | order_notes, notes, comments | STRING_LENGTH, OPTIONAL | Customer notes |
| `createdAt` | created_at, created, order_date | TIMESTAMP, IMMUTABLE | Order creation |
| `updatedAt` | updated_at, modified_at, last_updated | TIMESTAMP | Order modification |
| `deliveredAt` | delivered_at, delivery_date | TIMESTAMP, OPTIONAL | Delivery time |

### User Entity Fields

| Canonical | Variations | Constraint Type | Notes |
|-----------|-----------|-----------------|-------|
| `id` | userId, user_id, ID | PRIMARY_KEY | Immutable |
| `email` | user_email, emailAddress, email_address | UNIQUE, REQUIRED, FORMAT_EMAIL | Immutable |
| `firstName` | first_name, firstName, given_name | REQUIRED, STRING_LENGTH | Max 100 |
| `lastName` | last_name, lastName, family_name | REQUIRED, STRING_LENGTH | Max 100 |
| `phoneNumber` | phone_number, phoneNumber, phone | OPTIONAL, FORMAT_PHONE | International format |
| `address` | user_address, billing_address, street | OPTIONAL, STRING_LENGTH | Max 500 |
| `city` | city_name, city | OPTIONAL, STRING_LENGTH | Max 100 |
| `country` | country_code, country, country_name | OPTIONAL, STRING_LENGTH | ISO 3166 |
| `postalCode` | postal_code, postalCode, zip, zipcode | OPTIONAL, FORMAT_POSTAL | Country-specific |
| `password` | passwordHash, password_hash, hashed_password | IMMUTABLE, STRING_LENGTH | Never exposed |
| `status` | user_status, userStatus, state, account_status | ENUM | ACTIVE, INACTIVE, SUSPENDED |
| `createdAt` | created_at, created, registration_date | TIMESTAMP, IMMUTABLE | Account creation |
| `updatedAt` | updated_at, modified_at | TIMESTAMP | Last update |
| `lastLogin` | last_login, lastLoginDate, last_login_date | TIMESTAMP, OPTIONAL | For analytics |

---

## 🔤 Constraint Type Equivalences

### Format Constraints

| Canonical | Pattern Variations | Examples | Notes |
|-----------|-------------------|----------|-------|
| `FORMAT_EMAIL` | email, EmailStr, valid_email, email_validator, must_be_valid_email | `EmailStr`, `email: required`, `validator: email` | Regex: RFC 5322 |
| `FORMAT_PHONE` | phone, phone_number, phonenumber, phone_validator | `PhoneStr`, `phone: required` | International format |
| `FORMAT_URL` | url, URL, http, https, uri, valid_url | `HttpUrl`, `url: required` | RFC 3986 |
| `FORMAT_UUID` | uuid, UUID, guid, uuid4 | `uuid: uuid4`, `UUID` | Standard UUID format |
| `FORMAT_DATE` | date, datetime, timestamp, Date, DateTime | `date: ISO8601`, `datetime: required` | ISO 8601 |
| `FORMAT_TIME` | time, time_of_day, Time | `time: HH:MM:SS` | ISO 8601 time |
| `FORMAT_NUMERIC` | numeric, number, num, float, int, integer | `Numeric`, `gt=0` | Includes integers |
| `FORMAT_JSON` | json, JSON, json_object, object | `dict`, `model_dump_json` | Serialized JSON |
| `FORMAT_JSON_ARRAY` | json_array, array, list, items | `List[T]`, `array` | JSON array format |
| `FORMAT_ENUM` | enum, choice, choices, ENUM | `Enum`, `enum: [A, B, C]` | Predefined values |
| `FORMAT_POSTAL` | postal_code, zipcode, zip, postal | `PostalCode`, `pattern: ^[0-9]{5}$` | Country-specific |
| `FORMAT_SLUG` | slug, slugified, slug_field | `slug: lowercase_with_hyphens` | URL-safe string |

### Range Constraints

| Canonical | Pattern Variations | Examples | Semantics |
|-----------|-------------------|----------|-----------|
| `RANGE_MIN` | ge, gte, gt, min, minimum, >=, >, minimum_value | `ge=0`, `gt=0`, `min: 1` | Lower bound (inclusive/exclusive) |
| `RANGE_MAX` | le, lte, lt, max, maximum, <=, <, maximum_value | `le=1000`, `lt=100`, `max: 999` | Upper bound (inclusive/exclusive) |
| `STRING_LENGTH` | length, maxLength, max_length, minLength, min_length | `max_length: 255`, `length: 1-500` | Min/max string chars |
| `ARRAY_LENGTH` | min_items, max_items, minItems, maxItems | `min_items: 1`, `max_items: 100` | Min/max array elements |

### Uniqueness Constraints

| Canonical | Pattern Variations | Examples | Notes |
|-----------|-------------------|----------|-------|
| `UNIQUE` | unique, distinct, no_duplicates, one_of_a_kind | `unique: true`, `UNIQUE`, `distinct: true` | Single field uniqueness |
| `UNIQUE_TOGETHER` | unique_together, composite_unique, combined_unique | `unique_together: [field1, field2]` | Multi-field uniqueness |
| `PRIMARY_KEY` | primary, pk, primary_key, primary_identifier | `PRIMARY KEY`, `pk: true` | Entity identifier |
| `FOREIGN_KEY` | foreign_key, fk, references, ref | `FOREIGN KEY`, `references: other_table` | Referential integrity |

### State Constraints

| Canonical | Pattern Variations | Examples | Notes |
|-----------|-------------------|----------|-------|
| `REQUIRED` | required, not_null, not null, mandatory, must_have | `required: true`, `NOT NULL` | Field presence |
| `OPTIONAL` | optional, nullable, null_allowed, can_be_null | `optional: true`, `nullable: true` | Field omission allowed |
| `DEFAULT` | default, default_value, default_to | `default: "ACTIVE"`, `default: 0` | Default value |
| `IMMUTABLE` | immutable, readonly, read_only, frozen, exclude, exclude_update | `exclude: True`, `immutable: true` | No modification after creation |
| `COMPUTED` | computed, computed_field, readonly_computed, generated, derived | `computed_field`, `Field(exclude=True)` | Calculated from others |

### Validity Constraints

| Canonical | Pattern Variations | Examples | Notes |
|-----------|-------------------|----------|-------|
| `ENUM` | enum, choice, choices, ENUM | `Enum[A,B,C]`, `choices: [value1, value2]` | Predefined set |
| `REGEX` | regex, pattern, regex_pattern, match | `pattern: ^[A-Z]{3}$` | Regular expression |
| `CUSTOM_VALIDATION` | validator, custom, validation_rule | `validator: custom_func` | Business logic |

---

## 🔗 Enforcement Type Mappings

### Source → Canonical Enforcement

| Source | Representation | Canonical Enforcement | Behavior |
|--------|-----------------|----------------------|----------|
| **OpenAPI** | `required: true` | VALIDATOR | Validation at API boundary |
| **OpenAPI** | Schema constraint | VALIDATOR | Schema validation |
| **Pydantic** | `Field(gt=0)` | VALIDATOR | Model field validator |
| **Pydantic** | `Field(exclude=True)` | IMMUTABLE | Exclude from serialization |
| **Pydantic** | `@computed_field` | COMPUTED_FIELD | Derived value |
| **SQLAlchemy** | `nullable=False` | VALIDATOR | Database NOT NULL |
| **SQLAlchemy** | `unique=True` | VALIDATOR | Database UNIQUE constraint |
| **SQLAlchemy** | `primary_key=True` | VALIDATOR | Database PRIMARY KEY |
| **SQLAlchemy** | `onupdate=None` | IMMUTABLE | Database prevents update |
| **Business Logic** | Custom validator | BUSINESS_LOGIC | Application-level validation |
| **Business Logic** | State machine | STATE_MACHINE | Complex state transitions |

---

## 📋 Complete Mapping Examples

### Example 1: Email Constraint

**Raw Extractions**:
```python
# OpenAPI
{"entity": "User", "field": "email", "constraint": "email format", "source": "openapi"}

# Pydantic
{"entity": "User", "field": "email", "constraint": "EmailStr", "source": "ast_pydantic"}

# SQLAlchemy
{"entity": "User", "field": "email", "constraint": "String(255)", "source": "ast_sqlalchemy"}
```

**After Normalization** (Phase 2):
```python
NormalizedRule(
    entity="User",
    field="email",
    constraint_type="FORMAT_EMAIL",
    enforcement_type="VALIDATOR",
    confidence=0.95,
)
```

**Constraint Key**: `User.email.FORMAT_EMAIL` (1 unique constraint, 3 sources found)

---

### Example 2: Price Range Constraint

**Raw Extractions**:
```python
# OpenAPI
{"entity": "Product", "field": "unitPrice", "constraint": "greater than 0", "value": 0}

# Pydantic
{"entity": "Product", "field": "price", "constraint": "gt", "value": 0}

# SQLAlchemy
{"entity": "Product", "field": "price", "constraint": "CheckConstraint", "value": ">0"}
```

**After Normalization** (Phase 2):
```python
NormalizedRule(
    entity="Product",
    field="price",  # Canonical: price (not unitPrice)
    constraint_type="RANGE_MIN",
    value=0,
    enforcement_type="VALIDATOR",
    confidence=0.92,
)
```

**Constraint Key**: `Product.price.RANGE_MIN` (1 unique constraint, 3 sources)

---

### Example 3: Immutability Constraint

**Raw Extractions**:
```python
# OpenAPI
{"entity": "User", "field": "email", "constraint": "immutable", "enforcement": "description"}

# Pydantic
{"entity": "User", "field": "email", "constraint": "Field(..., exclude=True)", "enforcement": "model"}

# Business Logic
{"entity": "User", "field": "email", "constraint": "never update after creation", "enforcement": "business_logic"}
```

**After Normalization** (Phase 2):
```python
NormalizedRule(
    entity="User",
    field="email",
    constraint_type="IMMUTABLE",
    enforcement_type="IMMUTABLE",
    confidence=0.90,  # Business logic has lower confidence
)
```

**Constraint Key**: `User.email.IMMUTABLE` (1 unique constraint, 3 sources)

---

## 🎯 Implementation Notes for Phase 2

### Fuzzy Matching Strategy

1. **Exact Match** (confidence = 1.0): Identical canonical names
2. **Case Variation** (confidence = 0.95): Different cases of same word
3. **Snake/Camel Case** (confidence = 0.93): snake_case ↔ camelCase conversion
4. **Plural/Singular** (confidence = 0.90): items ↔ item mapping
5. **Synonym** (confidence = 0.85): price ↔ unit_price mapping
6. **Pattern Inference** (confidence = 0.75): Regex matching for types
7. **Uncertain** (confidence < 0.7): Flag for manual review

### Confidence Scoring

```python
def compute_confidence(normalization_step: str) -> float:
    mapping = {
        "exact_match": 1.0,
        "case_variation": 0.95,
        "snake_camel": 0.93,
        "plural_singular": 0.90,
        "synonym_mapping": 0.85,
        "pattern_inference": 0.75,
        "fallback": 0.50,
    }
    return mapping.get(normalization_step, 0.50)
```

### Logging Requirements

Each normalization should log:
```
📝 Normalizing: {raw_rule}
   Entity: {from} → {to} (confidence: {c})
   Field: {from} → {to} (confidence: {c})
   Type: {from} → {to} (confidence: {c})
   Final: {entity}.{field}.{type} @ {final_confidence}
```

---

## 📊 Expected Coverage

**Phase 2 Target**: 100% constraint coverage with ≥0.75 confidence

| Confidence Level | Expectation | Action |
|-----------------|-------------|--------|
| ≥0.95 | Exact matches, high certainty | Accept automatically |
| 0.85-0.95 | Fuzzy matches, clear semantics | Accept with confidence tracking |
| 0.75-0.85 | Pattern matches, inference-based | Accept with logging |
| <0.75 | Uncertain matches | Flag for manual review |

---

**Status**: Reference complete. Ready for Phase 2 implementation.
**Usage**: Copy relevant sections into SemanticNormalizer and UnifiedConstraintExtractor implementations.
**Maintenance**: Update as new entity/field/constraint types are encountered.
