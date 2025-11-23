# Phase 4: API Documentation

**Status**: ✅ **COMPLETE**
**Updated**: 2025-11-23
**Goal**: Generate OpenAPI 3.0 specification for all generated applications

---

## 1. OpenAPI 3.0 Specification Generation

### 1.1 Automatic Generation from ApplicationIR

Every generated application includes a complete OpenAPI 3.0 specification that is automatically generated from the ApplicationIR model:

```
ApplicationIR
├── domain_model (entities & attributes)
├── api_model (endpoints & parameters)
└── infrastructure_model (servers & security)
    ↓
OpenAPIGenerator
    ↓
openapi.json / openapi.yaml
```

### 1.2 Generation Process

```python
from src.services.openapi_generator import OpenAPIGenerator
from src.cognitive.ir.application_ir import ApplicationIR

# Load ApplicationIR for the project
app_ir = ApplicationIR.load("path/to/app.ir.json")

# Generate OpenAPI spec
generator = OpenAPIGenerator(app_ir)

# Export as JSON
generator.save_json("openapi.json")

# Or export as YAML
generator.save_yaml("openapi.yaml")

# Get spec as dict for further processing
spec_dict = generator.generate_spec()
```

### 1.3 Specification Contents

The generated OpenAPI spec includes:

**📋 Info Section:**
- API title and description
- API version
- Contact and license information

**🛣️ Paths Section:**
- All endpoints with HTTP method
- Request/response schemas
- Parameters (path, query, header, body)
- Status codes and error responses
- Security requirements

**🔐 Components Section:**
- Entity schemas (Base, Create, Response variants)
- Error response schema
- Security schemes (JWT Bearer)
- Reusable parameters

**🏷️ Tags:**
- Endpoint grouping by resource type
- Tag descriptions for organization

### 1.4 Example Generated Spec

```yaml
openapi: 3.0.0
info:
  title: E-Commerce API
  description: Generated API for e-commerce platform
  version: 1.0.0

servers:
  - url: http://localhost:8000
    description: Development Server

paths:
  /customers:
    post:
      summary: Create a new customer
      operationId: post_customers
      tags:
        - customers
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CustomerCreate'
      responses:
        '201':
          description: Customer created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CustomerResponse'
        '400':
          description: Invalid input
        '409':
          description: Email already exists (uniqueness violation)

  /customers/{id}:
    get:
      summary: Get customer by ID
      operationId: get_customer_by_id
      tags:
        - customers
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Customer found
        '404':
          description: Customer not found

components:
  schemas:
    CustomerBase:
      type: object
      properties:
        email:
          type: string
          format: email
          description: Customer email address
        full_name:
          type: string
          minLength: 1
          maxLength: 255
          description: Customer full name
      required:
        - email
        - full_name

    CustomerResponse:
      allOf:
        - $ref: '#/components/schemas/CustomerBase'
        - type: object
          properties:
            id:
              type: string
              format: uuid
            created_at:
              type: string
              format: date-time

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

## 2. Documentation Variants

### 2.1 JSON Format
- **File**: `openapi.json`
- **Use**: Tool integration, SDK generation, API testing
- **Size**: Compact, efficient for parsing
- **Tools**: Swagger UI, Postman, API clients

### 2.2 YAML Format
- **File**: `openapi.yaml`
- **Use**: Human reading, version control, documentation
- **Size**: More readable, with comments
- **Tools**: ReDoc, API documentation portals

### 2.3 Interactive Documentation
- **Tool**: Swagger UI
- **URL**: `http://localhost:8000/docs`
- **Features**: Try-it-out, parameter validation, response examples
- **Auto-generated**: From FastAPI with OpenAPI support

---

## 3. Integration Points

### 3.1 FastAPI Auto-Generation
Generated FastAPI apps automatically expose OpenAPI specs:

```python
# In main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="E-Commerce API",
    description="Generated API",
    version="1.0.0"
)

# FastAPI automatically generates:
# GET /openapi.json - OpenAPI spec (JSON)
# GET /docs - Swagger UI
# GET /redoc - ReDoc documentation
```

### 3.2 Custom OpenAPI Configuration
Applications can customize the generated spec:

```python
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    # Generate spec from ApplicationIR
    generator = OpenAPIGenerator(app_ir)
    spec = generator.generate_spec()

    # Add custom modifications if needed
    spec["info"]["x-custom-field"] = "value"

    app.openapi_schema = spec
    return app.openapi_schema

app.openapi = custom_openapi
```

---

## 4. Schema Mapping

### 4.1 Entity Schemas

Each entity generates three schema variants:

**Base Schema** (common properties):
```json
{
  "CustomerBase": {
    "type": "object",
    "properties": {
      "email": {"type": "string", "format": "email"},
      "full_name": {"type": "string"}
    },
    "required": ["email", "full_name"]
  }
}
```

**Create Schema** (for POST requests):
```json
{
  "CustomerCreate": {
    "allOf": [
      {"$ref": "#/components/schemas/CustomerBase"}
    ]
  }
}
```

**Response Schema** (with ID and timestamps):
```json
{
  "CustomerResponse": {
    "allOf": [
      {"$ref": "#/components/schemas/CustomerBase"},
      {
        "type": "object",
        "properties": {
          "id": {"type": "string", "format": "uuid"},
          "created_at": {"type": "string", "format": "date-time"}
        },
        "required": ["id", "created_at"]
      }
    ]
  }
}
```

### 4.2 Constraint Mapping

Field constraints are reflected in OpenAPI schema:

| Constraint | OpenAPI Property | Example |
|-----------|------------------|---------|
| required | required array | `"required": ["email"]` |
| unique | in description | `"description": "must be unique"` |
| min_length | minLength | `"minLength": 1` |
| max_length | maxLength | `"maxLength": 255` |
| pattern | pattern | `"pattern": "^[^@]+@[^@]+\\..*$"` |
| min/max value | minimum/maximum | `"minimum": 0`, `"maximum": 100` |

---

## 5. Endpoint Documentation

### 5.1 HTTP Methods & Statuses

All endpoints automatically document:

**GET Endpoints:**
- 200 OK - Resource found
- 404 Not Found - Resource doesn't exist
- 400 Bad Request - Invalid parameters

**POST Endpoints:**
- 201 Created - Resource created successfully
- 400 Bad Request - Invalid input
- 409 Conflict - Uniqueness violation / FK constraint
- 422 Unprocessable Entity - Validation error

**PUT/PATCH Endpoints:**
- 200 OK - Resource updated
- 404 Not Found - Resource doesn't exist
- 409 Conflict - Conflict (e.g., email taken)

**DELETE Endpoints:**
- 204 No Content - Successfully deleted
- 404 Not Found - Resource doesn't exist

### 5.2 Parameter Documentation

```yaml
parameters:
  - name: id
    in: path
    required: true
    description: Entity ID (UUID format)
    schema:
      type: string
      format: uuid

  - name: skip
    in: query
    description: Number of records to skip (pagination)
    schema:
      type: integer
      default: 0
      minimum: 0

  - name: limit
    in: query
    description: Maximum records to return (pagination)
    schema:
      type: integer
      default: 10
      minimum: 1
      maximum: 100
```

### 5.3 Request/Response Examples

```yaml
requestBody:
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/CustomerCreate'
      examples:
        basic:
          value:
            email: "john@example.com"
            full_name: "John Doe"

responses:
  '201':
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/CustomerResponse'
        examples:
          success:
            value:
              id: "550e8400-e29b-41d4-a716-446655440000"
              email: "john@example.com"
              full_name: "John Doe"
              created_at: "2025-11-23T10:30:00Z"
```

---

## 6. Validation & Quality

### 6.1 OpenAPI Validation
Generated specs are validated against OpenAPI 3.0 standard:

```bash
# Validate OpenAPI spec
npx openapi-spec-validator openapi.json

# Check for errors
swagger-cli validate openapi.json
```

### 6.2 Documentation Quality Checks
- ✅ All endpoints documented
- ✅ All parameters described
- ✅ Response schemas defined
- ✅ Error codes documented
- ✅ Security schemes specified
- ✅ Examples provided

---

## 7. Usage & Distribution

### 7.1 Direct Access
Generated apps expose documentation endpoints:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **Raw Spec**: `/openapi.json`

### 7.2 SDK Generation
Use OpenAPI spec to generate client SDKs:

```bash
# Generate Python SDK
openapi-generator-cli generate -i openapi.json -g python-client -o sdk/python

# Generate JavaScript SDK
openapi-generator-cli generate -i openapi.json -g javascript -o sdk/javascript

# Generate TypeScript SDK
openapi-generator-cli generate -i openapi.json -g typescript-fetch -o sdk/typescript
```

### 7.3 API Documentation Portal
Host spec on documentation portal:
```bash
# ReDoc static HTML
redoc-cli bundle openapi.json -o docs.html

# Postman Collection
swagger-cli bundle openapi.json --outfile postman.json --type postman
```

---

## 8. Implementation Status

### Phase 4 ✅
- [x] OpenAPIGenerator service created
- [x] Integration with ApplicationIR
- [x] Schema generation from domain model
- [x] Endpoint documentation
- [x] Error response schemas
- [x] Parameter documentation
- [x] Security scheme definition

### Phase 4.1 (Future)
- [ ] Example values in responses
- [ ] Webhook documentation
- [ ] GraphQL schema generation
- [ ] SDK generation automation
- [ ] API portal integration

---

## 9. Success Criteria

✅ **Achieved:**
- Complete OpenAPI 3.0 spec generation
- All endpoints documented
- Automatic schema generation
- Error code mapping
- Parameter validation
- Security configuration

🎯 **Goals:**
- Auto-generated at build time
- No manual documentation needed
- Always in sync with code
- SDK generation ready
- Multiple format support (JSON/YAML)

---

**Owner**: DevMatrix Phase 4 Team
**Updated**: 2025-11-23
**Status**: ✅ **COMPLETE** - OpenAPI generation framework implemented
