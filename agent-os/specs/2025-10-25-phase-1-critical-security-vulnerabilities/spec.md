# Specification: Phase 1 - Critical Security Vulnerabilities

## Overview

**Goal**: Eliminate 8 P0 security vulnerabilities that block production deployment.

**Timeline**: 2 weeks (Weeks 1-2 of 10-week roadmap)

**Priority**: P0 - Critical

### Critical Vulnerabilities (8)
1. Hardcoded JWT secret key - authentication bypass risk
2. Rate limiting disabled - DDoS/brute force vulnerability
3. CORS wildcard with credentials - CSRF attack vector
4. No token blacklist/logout - stolen tokens remain valid
5. Default database credentials - unauthorized DB access
6. Bare except clauses - silent error suppression
7. SQL injection in RAG - data breach risk
8. No conversation ownership validation - massive data leak

---

## Technical Specifications

### P0-1: JWT Secret Management

**Current Issue**: Hardcoded fallback secret in `/src/services/auth_service.py` line 21.

**Fix Approach**:
- Load JWT_SECRET from environment variable with Pydantic Settings validation
- Application MUST fail on startup if JWT_SECRET missing
- No fallback value permitted

**Key Files**:
- `/src/services/auth_service.py` - Remove hardcoded secret, add validation
- `/src/config/settings.py` - Create Pydantic Settings class
- `/src/main.py` - Add startup validation

**Implementation**:
```python
# src/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str  # Required, no default

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_jwt_secret(self):
        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return self.JWT_SECRET

# src/main.py
@app.on_event("startup")
async def validate_config():
    try:
        settings = Settings()
        settings.validate_jwt_secret()
    except Exception as e:
        logger.critical(f"CRITICAL: JWT_SECRET environment variable is required. {e}")
        raise SystemExit(1)
```

---

### P0-2: Rate Limiting

**Current Issue**: Rate limit middleware exists at `/src/api/middleware/rate_limit_middleware.py` but disabled in production.

**Fix Approach**:
- Enable existing Redis-backed middleware
- Add per-endpoint override decorators for auth routes
- Implement standard rate limit headers
- Return HTTP 429 with Retry-After header when exceeded

**Key Files**:
- `/src/api/middleware/rate_limit_middleware.py` - Enhance existing middleware
- `/src/main.py` - Enable middleware in app initialization
- `/src/api/routers/auth.py` - Add stricter limits to auth endpoints

**Rate Limits**:
- Anonymous (by IP): 30 req/min global, 10 req/min on /auth/*
- Authenticated (by user_id): 100 req/min global, 20 req/min on /auth/*

**Response Headers**:
- `X-RateLimit-Limit`: Maximum requests in window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when window resets
- `Retry-After`: Seconds until reset (429 only)

**Redis Key Format**: `rate_limit:{user|ip}:{identifier}`

---

### P0-3: CORS Configuration

**Current Issue**: CORS allows wildcard origins with credentials enabled.

**Fix Approach**:
- Load allowed origins from CORS_ALLOWED_ORIGINS environment variable
- Parse as comma-separated list of exact origin strings
- Reject requests from unauthorized origins with HTTP 403
- Validate origin on every request

**Key Files**:
- `/src/main.py` - Configure CORSMiddleware with environment-based origins
- `/src/config/settings.py` - Add CORS_ALLOWED_ORIGINS setting

**Implementation**:
```python
# src/config/settings.py
class Settings(BaseSettings):
    CORS_ALLOWED_ORIGINS: str = ""  # Comma-separated

# src/main.py
from fastapi.middleware.cors import CORSMiddleware

settings = Settings()
allowed_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Exact string matching
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Environment Examples**:
- Development: `CORS_ALLOWED_ORIGINS="http://localhost:5173,http://localhost:3000"`
- Production: `CORS_ALLOWED_ORIGINS="https://app.devmatrix.com"`

---

### P0-4: Token Blacklist and Logout

**Current Issue**: No logout functionality - tokens remain valid until expiration even after logout.

**Fix Approach**:
- Add `jti` (JWT ID) claim to all tokens using UUID v4
- Store blacklisted tokens in Redis with TTL matching token expiration
- Check blacklist in auth middleware before validating token
- Implement logout endpoint that blacklists both access and refresh tokens

**Key Files**:
- `/src/services/auth_service.py` - Add jti to tokens, implement blacklist check
- `/src/api/routers/auth.py` - Add logout endpoint
- `/src/api/middleware/auth_middleware.py` - Check blacklist before user lookup

**Redis Key Format**:
- Access tokens: `blacklist:access:{jti}` (TTL: 3600 seconds)
- Refresh tokens: `blacklist:refresh:{jti}` (TTL: 2592000 seconds)

**Implementation**:
```python
# Token generation (add jti)
import uuid

payload = {
    "sub": str(user_id),
    "jti": str(uuid.uuid4()),  # Add JWT ID
    "type": "access",
    "exp": expire
}

# Token validation (check blacklist)
def validate_token(token: str):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    jti = payload.get("jti")
    token_type = payload.get("type", "access")

    # Check blacklist
    if redis_client.exists(f"blacklist:{token_type}:{jti}"):
        raise HTTPException(401, "Token has been revoked")

    return payload

# Logout endpoint
@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # Extract jti from current token and add to blacklist
    redis_client.setex(f"blacklist:access:{jti}", 3600, "1")
    return {"message": "Successfully logged out"}
```

---

### P0-5: Database Credentials

**Current Issue**: Default/hardcoded database credentials in development.

**Fix Approach**:
- Move all database credentials to environment variables
- Fail-fast on startup if DATABASE_URL missing
- Remove any hardcoded defaults

**Key Files**:
- `/src/config/database.py` - Load from environment only
- `/src/config/settings.py` - Add DATABASE_URL validation

**Implementation**:
```python
# src/config/settings.py
class Settings(BaseSettings):
    DATABASE_URL: str  # Required, no default

# src/config/database.py
from src.config.settings import Settings

settings = Settings()
engine = create_engine(settings.DATABASE_URL)
```

---

### P0-6: Exception Handling

**Current Issue**: Bare `except:` clauses throughout codebase suppress errors silently.

**Fix Approach**:
- Replace ALL bare except clauses with specific exception types
- Log all exceptions with stack traces and correlation_id
- Wrap in HTTPException with appropriate status codes
- Never suppress errors silently

**Key Files**:
- Search all `.py` files for `except:` and replace
- Common files: `/src/services/*.py`, `/src/api/routers/*.py`, `/src/rag/*.py`

**Exception Hierarchy**:
1. SQLAlchemyError - Database errors (500)
2. RedisError - Redis errors (500)
3. HTTPException - Re-raise unchanged
4. ValidationError - Input validation (400)
5. AnthropicError/APIError - LLM errors (502)
6. Exception - Fallback only (500)

**Pattern**:
```python
# BEFORE (vulnerable)
try:
    result = db.execute(query)
except:
    pass  # Silent failure

# AFTER (secure)
try:
    result = await db.execute(query)
except SQLAlchemyError as e:
    logger.error(f"Database query failed: {str(e)}", exc_info=True, extra={"correlation_id": correlation_id})
    raise HTTPException(status_code=500, detail="Database error occurred")
except HTTPException:
    raise  # Don't wrap
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True, extra={"correlation_id": correlation_id})
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

### P0-7: SQL Injection Prevention

**Current Issue**: String concatenation in SQL queries, especially RAG vector store queries.

**Fix Approach**:
- Use SQLAlchemy `text()` with bind parameters for all raw SQL
- Validate all ChromaDB inputs with Pydantic schemas
- Whitelist allowed filter keys
- Add SQL injection security tests

**Key Files**:
- `/src/rag/vector_store.py` - Parameterize ChromaDB queries
- `/src/api/routers/rag.py` - Add input validation
- All files using raw SQL or string formatting

**Implementation**:
```python
# SQLAlchemy - BEFORE (vulnerable)
query = f"SELECT * FROM conversations WHERE id = '{conversation_id}'"
result = db.execute(query)

# SQLAlchemy - AFTER (secure)
from sqlalchemy import text
query = text("SELECT * FROM conversations WHERE id = :id")
result = db.execute(query.bindparams(id=conversation_id))

# ChromaDB - Input validation
from pydantic import BaseModel, validator

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

    @validator('query')
    def sanitize_query(cls, v):
        if len(v) > 500:
            raise ValueError("Query too long")
        # Remove SQL special characters
        dangerous_chars = ["'", '"', "--", ";", "/*", "*/"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError("Invalid characters in query")
        return v

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Limit must be 1-100")
        return v
```

---

### P0-8: Conversation Ownership Validation

**Current Issue**: No validation that user owns the conversation they're accessing - allows data leak.

**Fix Approach**:
- Create `@require_resource_ownership("conversation")` decorator
- Validate `conversation.user_id == current_user.user_id`
- Allow superuser bypass (`is_superuser=True`)
- Apply to ALL conversation and message endpoints

**Key Files**:
- `/src/api/middleware/ownership_middleware.py` - Create new decorator
- `/src/api/routers/chat.py` - Apply decorator to all conversation endpoints

**Implementation**:
```python
# src/api/middleware/ownership_middleware.py
from functools import wraps
from fastapi import HTTPException, Depends
from src.models.conversation import Conversation
from src.api.middleware.auth_middleware import get_current_user

def require_resource_ownership(resource_type: str):
    """Decorator to enforce resource ownership."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract conversation_id from kwargs
            conversation_id = kwargs.get('conversation_id')
            current_user = kwargs.get('current_user')

            # Load conversation
            with get_db_context() as db:
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()

                if not conversation:
                    raise HTTPException(404, "Conversation not found")

                # Check ownership
                if conversation.user_id != current_user.user_id:
                    # Allow superuser bypass
                    if not current_user.is_superuser:
                        # Log failed access attempt
                        logger.warning(f"Unauthorized access attempt: user {current_user.user_id} tried to access conversation {conversation_id}")
                        raise HTTPException(403, "Access denied: You do not own this resource")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage in router
@router.get("/conversations/{conversation_id}")
@require_resource_ownership("conversation")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    # Ownership already validated
    return conversation
```

**Endpoints to Protect**:
- GET /conversations/{conversation_id}
- PUT /conversations/{conversation_id}
- DELETE /conversations/{conversation_id}
- GET /conversations/{conversation_id}/messages
- POST /conversations/{conversation_id}/messages
- PUT /conversations/{conversation_id}/messages/{message_id}
- DELETE /conversations/{conversation_id}/messages/{message_id}

---

## Implementation Plan

### New Files to Create

1. **`/src/config/settings.py`** - Pydantic Settings for configuration
   - JWT_SECRET validation
   - DATABASE_URL validation
   - CORS_ALLOWED_ORIGINS parsing
   - Fail-fast on startup

2. **`/src/observability/audit_logger.py`** - Audit logging service
   - Async logging to avoid blocking
   - Captures auth, authz, and modification events
   - Writes to audit_logs table

3. **`/src/api/responses/error_response.py`** - Standardized error responses
   - ErrorResponse Pydantic model
   - Global exception handler
   - Correlation ID injection

4. **`/src/api/middleware/correlation_id_middleware.py`** - Request correlation
   - Generate UUID v4 for each request
   - Store in request context
   - Include in all logs and error responses

5. **`/src/api/middleware/ownership_middleware.py`** - Resource ownership
   - Decorator for ownership validation
   - Superuser bypass logic
   - Audit logging integration

### Files to Modify

1. **`/src/services/auth_service.py`**
   - Remove hardcoded JWT_SECRET
   - Add jti to token payload
   - Implement blacklist check
   - Replace bare except clauses

2. **`/src/api/middleware/auth_middleware.py`**
   - Add blacklist check before user lookup
   - Add correlation_id to logs

3. **`/src/api/middleware/rate_limit_middleware.py`**
   - Enable in production
   - Add per-endpoint override support
   - Return standard headers

4. **`/src/main.py`**
   - Add Settings validation on startup
   - Configure CORS with environment origins
   - Enable rate limit middleware
   - Add correlation ID middleware
   - Add global exception handler

5. **`/src/api/routers/auth.py`**
   - Add logout endpoint
   - Apply stricter rate limits to auth routes

6. **`/src/api/routers/chat.py`**
   - Apply ownership decorator to all conversation endpoints

7. **`/src/rag/vector_store.py`**
   - Add input validation with Pydantic
   - Sanitize search queries

### Environment Variables

**Required**:
- `JWT_SECRET` - JWT signing secret (min 32 chars)
- `DATABASE_URL` - PostgreSQL connection string
- `CORS_ALLOWED_ORIGINS` - Comma-separated origin whitelist

**Optional** (with defaults):
- `REDIS_HOST` - Default: localhost
- `REDIS_PORT` - Default: 6379
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Default: 60
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Default: 30

### Testing Requirements

**Total New Tests**: 50+

**Test Categories**:

1. **JWT Secret Management (3 tests)**
   - Startup fails when JWT_SECRET missing
   - Token signing with environment secret
   - Minimum length validation

2. **Rate Limiting (8 tests)**
   - Anonymous hits global limit
   - Anonymous hits auth limit
   - Authenticated hits global limit
   - Authenticated hits auth limit
   - Headers present in response
   - 429 status on exceeded
   - Counter resets after window
   - Independent user limits

3. **CORS (5 tests)**
   - Allowed origin receives headers
   - Disallowed origin gets 403
   - Preflight OPTIONS handling
   - Multiple origins parsing
   - Credentials flag handling

4. **Token Blacklist (7 tests)**
   - Logout adds to blacklist
   - Blacklisted access token rejected
   - Blacklisted refresh token rejected
   - TTL matches expiration
   - Multiple logouts work
   - jti in all tokens
   - Both token types blacklisted

5. **SQL Injection (6 tests)**
   - Parameterized queries safe
   - ChromaDB injection blocked
   - Filter validation works
   - Input sanitization
   - Common patterns blocked (', ", --, UNION)
   - All endpoints tested

6. **Ownership Validation (10 tests)**
   - User accesses own conversation (success)
   - User accesses other conversation (403)
   - User updates other conversation (403)
   - User deletes other conversation (403)
   - Superuser accesses any (success)
   - Message endpoints inherit ownership
   - 403 for unauthorized
   - 404 for non-existent
   - Validation before other checks
   - Bulk operations respect ownership

7. **Exception Handling (5 tests)**
   - SQLAlchemyError caught and logged
   - HTTPException re-raised
   - Generic Exception wrapped
   - Stack trace in logs
   - Correlation_id in logs

8. **Error Response (6 tests)**
   - All required fields present
   - Error codes match conventions
   - Correlation_id is UUID v4
   - Timestamp is ISO 8601 UTC
   - Details field populated
   - No sensitive info exposed

**Coverage Target**: Maintain 92% overall, 95% for new security code

---

## Data Models

### ErrorResponse Schema

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Error code (e.g., AUTH_001)")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request correlation ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "AUTH_001",
                "message": "Invalid credentials",
                "details": {},
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-10-25T10:30:00Z"
            }
        }
```

**Error Code Conventions**:
- AUTH_xxx - Authentication errors (401)
- AUTHZ_xxx - Authorization errors (403)
- VAL_xxx - Validation errors (400)
- DB_xxx - Database errors (500)
- RATE_xxx - Rate limiting (429)
- SYS_xxx - System errors (500)

### Audit Log Table Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    result VARCHAR(20) NOT NULL CHECK (result IN ('success', 'denied')),
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
```

**Logged Events**:
- `auth.login`, `auth.logout`, `auth.token_refresh`, `auth.login_failed`
- `conversation.create`, `conversation.update`, `conversation.delete`
- `conversation.read_denied`, `conversation.update_denied`, `conversation.delete_denied`
- `message.create`, `message.update`, `message.delete`
- `message.create_denied`, `message.read_denied`, `message.update_denied`, `message.delete_denied`

### Redis Key Formats

**Rate Limiting**:
- Key: `rate_limit:{user|ip}:{identifier}`
- Value: Sorted set of request timestamps
- TTL: 120 seconds
- Example: `rate_limit:user:550e8400-e29b-41d4-a716-446655440000`

**Token Blacklist**:
- Key: `blacklist:{access|refresh}:{jti}`
- Value: "1"
- TTL: Matches token expiration (3600s for access, 2592000s for refresh)
- Example: `blacklist:access:660e8400-e29b-41d4-a716-446655440000`

---

## API Changes

### Error Response Format

**All error responses** will follow this format:

```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid credentials",
    "details": {},
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-25T10:30:00Z"
  }
}
```

**Response Headers**:
- `X-Correlation-ID`: Request correlation ID for tracing

### Rate Limit Headers

**All responses** will include:
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Unix timestamp when window resets

**429 Response** (rate limit exceeded):
- `Retry-After`: Seconds until limit resets

```json
{
  "error": {
    "code": "RATE_001",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 30,
      "retry_after": 45
    },
    "correlation_id": "...",
    "timestamp": "..."
  }
}
```

### Ownership Validation

**403 Response** (unauthorized access):

```json
{
  "error": {
    "code": "AUTHZ_001",
    "message": "Access denied: You do not own this resource",
    "details": {
      "resource_type": "conversation",
      "resource_id": "660e8400-e29b-41d4-a716-446655440000"
    },
    "correlation_id": "...",
    "timestamp": "..."
  }
}
```

### New Endpoints

**POST /api/v1/auth/logout**

Request:
```json
{
  "refresh_token": "optional-refresh-token-to-blacklist"
}
```

Response (200):
```json
{
  "message": "Successfully logged out"
}
```

---

## Reusable Components

### Existing Code to Leverage

**From `/src/api/middleware/auth_middleware.py`**:
- `get_current_user()` - User extraction from JWT
- `get_current_superuser()` - Admin validation
- Dependency injection pattern
- HTTPBearer security scheme

**From `/src/api/middleware/rate_limit_middleware.py`**:
- Redis-backed rate limiting structure
- Sliding window algorithm
- Rate limit header injection
- Per-user quota lookup pattern

**From `/src/state/redis_manager.py`**:
- Redis connection management
- Fallback mode with in-memory storage
- Automatic reconnection logic
- Health check pattern

**From `/src/models/conversation.py`**:
- Conversation model with user_id FK
- Indexed user_id column exists
- No schema migration needed

**From `/src/services/auth_service.py`**:
- Token generation pattern
- JWT encoding/decoding
- Password hashing utilities

### New Components Required

**`/src/config/settings.py`**:
- Centralizes all environment configuration
- Pydantic validation for required settings
- Fail-fast startup validation
- No existing pattern - new requirement

**`/src/observability/audit_logger.py`**:
- Async audit logging service
- Database table for audit logs
- Integration with middleware
- No existing pattern - new requirement

**`/src/api/responses/error_response.py`**:
- Standardized error format
- Global exception handler
- Correlation ID injection
- Current errors are inconsistent

**`/src/api/middleware/ownership_middleware.py`**:
- Resource ownership decorator
- Superuser bypass logic
- No existing authorization beyond authentication

---

## Testing & Deployment

### Test Categories

**Unit Tests** (function-level):
- Settings validation
- Token generation with jti
- Blacklist check logic
- Input sanitization
- Error response formatting
- Audit log creation

**Integration Tests** (endpoint-level):
- Full authentication flow with logout
- Rate limiting across multiple requests
- CORS on actual HTTP requests
- Ownership validation on endpoints
- End-to-end user journeys

**Security Tests** (malicious input):
- SQL injection attempts (', ", --, UNION, DROP)
- Authentication bypass attempts
- Authorization bypass attempts
- Rate limit evasion
- CSRF with disallowed origins
- Token reuse after logout

**Manual Testing** (end of Phase 1):
- Full penetration test
- Security team review
- Regression testing
- Performance benchmarking

### Success Criteria

**All 8 P0 vulnerabilities eliminated**:
- ✅ JWT_SECRET from environment, fail-fast
- ✅ Rate limiting active (Redis-backed)
- ✅ CORS restricted to whitelist
- ✅ Token blacklist for logout
- ✅ SQL injection prevented
- ✅ Ownership validation enforced
- ✅ Bare except clauses replaced
- ✅ Error responses standardized

**Testing complete**:
- ✅ 50+ new tests passing
- ✅ 92%+ coverage maintained
- ✅ Security tests pass
- ✅ Manual penetration test: zero critical findings

**Documentation complete**:
- ✅ Environment variables documented
- ✅ Error codes documented
- ✅ Deployment procedure documented

### Zero-Downtime Deployment

**Prerequisites**:
- Environment variables set in production
- Redis available and configured
- No database migrations needed (user_id exists)

**Deployment Steps**:

1. **Pre-deployment checks**
   ```bash
   # Verify environment variables
   echo $JWT_SECRET | wc -c  # Must be 32+ chars
   echo $DATABASE_URL
   echo $CORS_ALLOWED_ORIGINS

   # Run all tests
   pytest tests/ -v --cov=src
   ```

2. **Deploy to staging**
   ```bash
   # Deploy code
   git checkout main
   git pull origin main

   # Restart application
   systemctl restart devmatrix-api

   # Verify health
   curl https://staging.devmatrix.com/health
   ```

3. **Smoke test staging**
   - Login/logout flow
   - Rate limiting behavior
   - CORS headers
   - Ownership validation
   - Error response format

4. **Deploy to production**
   ```bash
   # Same as staging with production env vars
   # Enable middleware gradually via feature flags if needed
   ```

5. **Post-deployment verification**
   - Monitor error logs for 1 hour
   - Check Redis memory usage
   - Verify rate limiting effectiveness
   - Monitor audit log volume

**Rollback Procedure**:
```bash
# If issues detected
git revert <commit-hash>
systemctl restart devmatrix-api

# Or rollback to previous deployment
git checkout <previous-tag>
systemctl restart devmatrix-api
```

**Monitoring**:
- Alert on high rate limit violations
- Alert on blacklist size > 10,000
- Alert on startup failures (JWT_SECRET missing)
- Monitor audit log table growth

---

## Out of Scope

**Explicitly excluded from Phase 1** (deferred to later phases):

### Authentication Enhancements (Phase 6)
- Password complexity requirements
- Two-factor authentication (2FA)
- Multi-factor authentication (MFA)
- Account lockout after failed attempts
- Social login (Google, GitHub)

### Session Management (Phase 2/5)
- Concurrent session limits
- Session fingerprinting
- Session activity tracking
- Idle timeout enforcement
- Remember me functionality

### Security Headers (Phase 5)
- Complete CSP (Content Security Policy)
- HSTS (HTTP Strict Transport Security)
- X-Frame-Options with strict policies
- Phase 1: Only basic headers (X-XSS-Protection, X-Content-Type-Options)

### Advanced Access Control (Phase 2/6)
- IP whitelisting for admin endpoints
- Role-based access control (RBAC) beyond superuser
- Fine-grained permissions
- Resource-level permissions beyond ownership

### Compliance (Phase 5)
- GDPR data export automation
- GDPR right to erasure
- Compliance reporting
- Data retention policies

### Infrastructure (Phase 5)
- WAF (Web Application Firewall)
- Advanced DDoS protection
- Bot detection
- Intrusion detection system
- Sentry error reporting
- Log aggregation
- Metrics and tracing

**Focus**: Phase 1 eliminates production blockers only. Advanced features deferred to maintain 2-week timeline.
