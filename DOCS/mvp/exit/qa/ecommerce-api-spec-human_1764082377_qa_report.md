# QA Report: ecommerce-api-spec-human_1764082377

**Date**: 2025-11-25
**Environment**: Docker (localhost:8002)
**App Version**: Generated E-Commerce API
**Tester**: Automated QA Suite + Manual Verification

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 20 |
| **Passed** | 15 |
| **Failed** | 5 |
| **Warnings** | 3 |
| **Pass Rate** | 75.0% |
| **Status** | 🔴 **CRITICAL BUGS BLOCKING CORE FUNCTIONALITY** |

### Critical Issues Found
- **5 blocker bugs** preventing core CRUD operations
- **3 service/route method mismatches** causing 500 errors
- **1 entity/migration mismatch** causing database errors

---

## Infrastructure Status

### Docker Containers
| Container | Image | Status | Port |
|-----------|-------|--------|------|
| app_app | docker-app | ✅ Healthy | 8002 |
| app_postgres | postgres:16-alpine | ✅ Healthy | 5433 |
| app_prometheus | prom/prometheus | ✅ Running | 9091 |
| app_grafana | grafana/grafana | ✅ Running | 3002 |

### Health Endpoints
| Endpoint | Status | Response |
|----------|--------|----------|
| `GET /health/health` | ✅ 200 | `{"status":"ok","service":"API"}` |
| `GET /health/ready` | ✅ 200 | OK |
| `GET /metrics` | ✅ 200 | Prometheus metrics |
| `GET /` | ✅ 200 | Root response |
| `GET /docs` | ✅ 200 | Swagger UI |

---

## Bug Report

### 🔴 BUG-001: ProductService.get_all() Method Missing (BLOCKER)

**Severity**: CRITICAL
**Affected Endpoints**: `GET /products/`
**Root Cause**: Route calls `service.get_all()` but service only has `list()`

**Error Message**:
```
AttributeError: 'ProductService' object has no attribute 'get_all'
```

**Location**:
- `src/api/routes/product.py:38` - calls `service.get_all(skip=0, limit=100)`
- `src/services/product_service.py` - only has `list(page, size)`

**Fix Required**:
```python
# In product.py:38, change:
products = await service.get_all(skip=0, limit=100)
# To:
products = await service.list(page=1, size=100)
```

---

### 🔴 BUG-002: Customer Entity/Migration Mismatch (BLOCKER)

**Severity**: CRITICAL
**Affected Endpoints**: `GET /customers/{id}`, `POST /customers/`
**Root Cause**: Entity defines `registration_date` column but migration didn't create it

**Error Message**:
```
asyncpg.exceptions.UndefinedColumnError: column customers.registration_date does not exist
```

**Entity Definition** (`src/models/entities.py:37-39`):
```python
registration_date = Column(DateTime(timezone=True), nullable=False,
    default=lambda : datetime.now(timezone.utc))
```

**Actual Database Schema**:
```
customers table:
 - id (uuid)
 - created_at (timestamp)
 - email (varchar)
 - full_name (varchar)
 # MISSING: registration_date
```

**Fix Required**:
- Option A: Add migration to add `registration_date` column
- Option B: Remove `registration_date` from entity definition

---

### 🔴 BUG-003: Entity Syntax Errors (CRITICAL)

**Severity**: HIGH
**Location**: `src/models/entities.py`
**Issue**: Multiple Column definitions have invalid `default_factory` parameter

**Problematic Code**:
```python
# Line 17 - ProductEntity
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    unique=True, default_factory=uuid.uuid4)  # ❌ default_factory is not valid

# Line 37-39 - CustomerEntity
registration_date = Column(DateTime(timezone=True), nullable=False,
    default=lambda : datetime.now(timezone.utc), default_factory=
    datetime.utcnow)  # ❌ default_factory is not valid
```

**Note**: SQLAlchemy Column does NOT support `default_factory`. This is a Pydantic/dataclass concept. The code works because Python ignores unknown keyword arguments in some contexts, but it's incorrect.

---

### 🟡 BUG-004: 404 Not Found Returns 500 Instead

**Severity**: MEDIUM
**Affected Endpoints**:
- `GET /customers/{non-existent-id}` - returns 500
- `GET /orders/{non-existent-id}` - returns 500

**Expected**: 404 Not Found
**Actual**: 500 Internal Server Error

**Root Cause**: Database errors (from BUG-002) are not being handled properly, escalating to 500 instead of returning 404.

---

### 🟡 BUG-005: Invalid UUID Returns 500 Instead of 422

**Severity**: MEDIUM
**Affected Endpoints**: All `/{id}` endpoints
**Input**: `GET /products/not-a-uuid`

**Expected**: 422 Validation Error
**Actual**: 500 Internal Server Error

---

## Test Results by Category

### Health & Infrastructure ✅
| Test | Status | Details |
|------|--------|---------|
| GET /health/health | ✅ PASS | 200 OK |
| GET /health/ready | ✅ PASS | 200 OK |
| GET /metrics | ✅ PASS | 200 OK |
| GET / (root) | ✅ PASS | 200 OK |

### Products CRUD 🔴
| Test | Status | Details |
|------|--------|---------|
| GET /products/ (list) | ❌ FAIL | 500 - AttributeError: get_all |
| POST /products/ (create) | ❌ FAIL | 500 - Same error cascading |
| POST /products/ (negative price) | ✅ PASS | 422 validation |
| POST /products/ (negative stock) | ✅ PASS | 422 validation |
| POST /products/ (missing fields) | ✅ PASS | 422 validation |
| GET /products/{id} (not found) | ✅ PASS | 404 |

### Customers 🔴
| Test | Status | Details |
|------|--------|---------|
| POST /customers/ (create) | ❌ FAIL | 500 - registration_date column missing |
| POST /customers/ (invalid email) | ✅ PASS | 422 validation |
| GET /customers/{id} (not found) | ❌ FAIL | 500 instead of 404 |

### Orders 🔴
| Test | Status | Details |
|------|--------|---------|
| GET /orders/{id} (not found) | ❌ FAIL | 500 instead of 404 |

### Validation & Edge Cases
| Test | Status | Details |
|------|--------|---------|
| Invalid UUID format | ⚠️ WARN | 500 instead of 422 |
| Wrong Content-Type | ✅ PASS | 422 |
| Malformed JSON | ✅ PASS | 422 |
| Method Not Allowed | ✅ PASS | 405 |
| Very long name | ✅ PASS | 422 |
| Extreme price value | ⚠️ WARN | 500 error |
| Extreme stock value | ⚠️ WARN | 500 error |

### Performance ✅
| Test | Status | Details |
|------|--------|---------|
| Health check latency | ✅ PASS | 1.7ms avg (< 100ms threshold) |
| GET /products/ latency | ✅ PASS | 4.9ms (< 500ms threshold) |

---

## API Schema Analysis

### Discovered Required Fields

**ProductCreate**:
- `name` (string) - required
- `price` (number) - required
- `stock` (integer) - required
- `is_active` (boolean) - **required** (not typical, should have default)
- `description` (string) - optional

**CustomerCreate**:
- `email` (string) - required
- `full_name` (string) - required

**CartCreate**:
- `customer_id` (UUID) - required
- `status` (string) - optional
- `items` (array) - **required** (should be optional for empty cart)

**OrderCreate**:
- `customer_id` (UUID) - required
- `order_status` (string) - **required** (should have default "pending")
- `payment_status` (string) - optional
- `items` (array) - required

---

## Recommendations

### Immediate Fixes Required (P0)

1. **Fix ProductService method mismatch**
   ```python
   # product.py:38
   products = await service.list(page=1, size=100)
   ```

2. **Fix Customer entity/migration mismatch**
   - Add migration: `alembic revision --autogenerate -m "add registration_date"`
   - Or remove column from entity

3. **Fix default_factory syntax errors**
   - Remove all `default_factory=` parameters from SQLAlchemy Column definitions

### Short-term Improvements (P1)

4. **Improve error handling**
   - Return proper 404 for not found resources
   - Return 422 for invalid UUID formats
   - Don't expose internal errors to clients

5. **Schema defaults**
   - `is_active` should default to `True`
   - `order_status` should default to `"pending"`
   - `items` in CartCreate should be optional (empty array default)

### Long-term Improvements (P2)

6. **Add comprehensive integration tests**
7. **Implement proper database connection error handling**
8. **Add request/response logging for debugging**

---

## Test Environment Details

```yaml
Docker Compose: docker/docker-compose.yml
API Port: 8002
PostgreSQL Port: 5433
Grafana Port: 3002
Prometheus Port: 9091

Database: app_db
User: devmatrix
```

---

## Appendix: Full Error Logs

### Error 1: ProductService.get_all AttributeError
```
File "/app/src/api/routes/product.py", line 38, in listar_productos_activos_con_paginación
    products = await service.get_all(skip=0, limit=100)
AttributeError: 'ProductService' object has no attribute 'get_all'
```

### Error 2: Customer registration_date Column Missing
```
asyncpg.exceptions.UndefinedColumnError: column customers.registration_date does not exist
[SQL: SELECT customers.id, customers.email, customers.full_name, customers.registration_date, customers.created_at
FROM customers WHERE customers.id = $1::UUID]
```

---

**Report Generated**: 2025-11-25T16:10:00+01:00
**QA Framework**: Custom Python + requests
**Total Execution Time**: ~15 seconds
