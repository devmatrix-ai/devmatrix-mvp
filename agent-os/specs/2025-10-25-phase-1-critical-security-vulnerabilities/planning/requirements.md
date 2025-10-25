# Spec Requirements: Phase 1 - Critical Security Vulnerabilities

## Initial Description

Fix all 8 critical security issues including hardcoded secrets, rate limiting, CORS, token blacklist, SQL injection, and authorization bypasses to eliminate immediate production blockers.

This is the first phase of a comprehensive remediation project for DevMatrix MVP. The analysis has identified 8 critical (P0) security vulnerabilities that must be fixed before production deployment:

1. Hardcoded JWT secret key (authentication bypass risk)
2. Rate limiting disabled (DDoS/brute force vulnerability)
3. CORS wildcard with credentials (CSRF attack vector)
4. No token blacklist/logout (stolen tokens remain valid)
5. Default database credentials (unauthorized DB access)
6. Bare except clauses (silent error suppression)
7. SQL injection in RAG (data breach risk)
8. No conversation ownership validation (massive data leak)

**Project Type:** Security remediation and hardening
**Priority:** P0 - Critical
**Timeline:** Weeks 1-2 of the 10-week roadmap
**Goal:** Eliminate all immediate production blockers and critical security vulnerabilities

---

## Requirements Discussion

### First Round Questions

**Q1: JWT Secret Management - Should we fail-fast if JWT_SECRET is missing, or provide a fallback development secret?**

**Answer:** JWT_SECRET required with NO fallback (fail-fast if missing). Environment-based management sufficient for Phase 1. Rotation documentation deferred to Phase 5.

**Requirements:**
- JWT_SECRET must be loaded from environment variable
- Application MUST fail on startup if JWT_SECRET is not set
- No hardcoded fallback value permitted
- Implement Pydantic Settings validation to enforce this requirement
- Add clear error message when JWT_SECRET is missing: "CRITICAL: JWT_SECRET environment variable is required. Application cannot start without it."

---

**Q2: Rate Limiting Configuration - What rate limits should we enforce? Should we use different limits for authenticated vs anonymous users?**

**Answer:** Redis-backed with per-endpoint overrides:
- Anonymous (by IP): 30 req/min global, 10 req/min on /auth/*
- Authenticated (by user_id): 100 req/min global, 20 req/min on /auth/*
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- Per-endpoint decorators for stricter limits on auth endpoints

**Requirements:**
- Implement Redis-backed distributed rate limiting
- Anonymous users (identified by IP address):
  - Global limit: 30 requests per minute
  - Auth endpoints (/auth/*): 10 requests per minute
- Authenticated users (identified by user_id):
  - Global limit: 100 requests per minute
  - Auth endpoints (/auth/*): 20 requests per minute
- Return standard rate limit headers on ALL responses:
  - `X-RateLimit-Limit`: Maximum requests allowed in window
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when window resets
- When rate limit exceeded:
  - Return HTTP 429 (Too Many Requests)
  - Include `Retry-After` header with seconds until reset
- Support per-endpoint decorator for custom limits
- Store rate limit counters in Redis with TTL matching window duration

---

**Q3: CORS Allowed Origins - Which domains should be whitelisted for CORS? Should we use regex patterns or exact string matching?**

**Answer:**
- Environment variable: CORS_ALLOWED_ORIGINS (comma-separated)
- String matching only (no regex) for Phase 1
- Example: "http://localhost:5173,https://app.devmatrix.com,https://staging.devmatrix.com"

**Requirements:**
- Read allowed origins from CORS_ALLOWED_ORIGINS environment variable
- Parse as comma-separated list of exact origin strings
- Use exact string matching (no wildcard, no regex) in Phase 1
- Remove credentials flag for any origins not in whitelist
- Implement proper preflight (OPTIONS) request handling
- Validate origin on EVERY request, not just preflight
- For local development, example configuration:
  ```
  CORS_ALLOWED_ORIGINS="http://localhost:5173,http://localhost:3000"
  ```
- For staging:
  ```
  CORS_ALLOWED_ORIGINS="https://staging.devmatrix.com"
  ```
- For production:
  ```
  CORS_ALLOWED_ORIGINS="https://app.devmatrix.com"
  ```
- Reject requests from origins not in whitelist with HTTP 403

---

**Q4: Token Blacklist Implementation - Should we blacklist only access tokens, or both access and refresh tokens?**

**Answer:** Implement for BOTH access and refresh tokens in Redis:
- Access tokens: TTL = 60 min
- Refresh tokens: TTL = 30 days
- Key format: blacklist:access:{jti} and blacklist:refresh:{jti}
- Add jti (JWT ID) to all generated tokens

**Requirements:**
- Add `jti` (JWT ID) claim to ALL tokens (access and refresh)
  - Use UUID v4 for jti value
  - Include jti in token payload when encoding
- Blacklist implementation:
  - Access tokens: Store in Redis as `blacklist:access:{jti}` with TTL = 3600 seconds (60 min)
  - Refresh tokens: Store in Redis as `blacklist:refresh:{jti}` with TTL = 2592000 seconds (30 days)
  - TTL matches token expiration to allow automatic cleanup
- Token validation middleware:
  - Extract jti from token
  - Check Redis for blacklist:{token_type}:{jti}
  - If exists, reject with HTTP 401 and message "Token has been revoked"
- Logout endpoint:
  - Accept current access token
  - Extract jti from access token
  - If refresh token provided, extract its jti
  - Add both to Redis blacklist
  - Return 200 with message "Successfully logged out"
- Automatic cleanup: Redis TTL handles expired token removal

---

**Q5: SQL Injection Prevention - Should we implement parameterized queries only, or also add query validation middleware?**

**Answer:** Parameterization + input validation:
- Use SQLAlchemy text() with bind parameters
- Validate inputs before ChromaDB query construction
- No query validation middleware in Phase 1

**Requirements:**
- SQLAlchemy queries:
  - Use `text()` with bind parameters for all raw SQL
  - Example: `text("SELECT * FROM conversations WHERE id = :id").bindparams(id=conversation_id)`
  - NEVER use string concatenation or f-strings for SQL
  - Rely on SQLAlchemy ORM for most queries (inherently parameterized)
- ChromaDB queries:
  - Validate all user inputs before constructing queries
  - Use Pydantic schemas to validate:
    - Search query strings (max length, allowed characters)
    - Filter parameters (type checking, range validation)
    - Limit/offset parameters (positive integers only)
  - Whitelist allowed filter keys
  - Sanitize input strings to remove SQL special characters
- Add SQL injection tests to security test suite:
  - Test common injection patterns (', ", --, ;, UNION, DROP)
  - Verify parameterized queries prevent injection
  - Test ChromaDB search with malicious inputs
- Query validation middleware: Deferred to Phase 5

---

**Q6: Conversation Ownership Validation - Should admins be able to access all conversations, or should we enforce strict ownership even for superusers?**

**Answer:** Middleware decorator @require_resource_ownership("conversation"):
- Strict validation: conversation.user_id == current_user.user_id
- Admin bypass: is_superuser=True can read all
- Apply to all conversation and message endpoints

**Requirements:**
- Create middleware decorator: `@require_resource_ownership("conversation")`
- Ownership validation logic:
  - Extract conversation_id from path parameters
  - Load conversation from database
  - Check: `conversation.user_id == current_user.user_id`
  - If match: Allow access
  - If mismatch and user is superuser (`is_superuser=True`): Allow access
  - If mismatch and NOT superuser: Return HTTP 403 with message "Access denied: You do not own this resource"
- Apply decorator to ALL endpoints:
  - GET /conversations/{conversation_id}
  - PUT /conversations/{conversation_id}
  - DELETE /conversations/{conversation_id}
  - GET /conversations/{conversation_id}/messages
  - POST /conversations/{conversation_id}/messages
  - PUT /conversations/{conversation_id}/messages/{message_id}
  - DELETE /conversations/{conversation_id}/messages/{message_id}
- Message ownership inherits from conversation:
  - When accessing messages, validate parent conversation ownership
  - No separate message.user_id check needed
- Create comprehensive authorization test suite:
  - Test user accessing own conversations: SUCCESS
  - Test user accessing other's conversations: HTTP 403
  - Test superuser accessing any conversation: SUCCESS
  - Test accessing non-existent conversations: HTTP 404
  - Test all CRUD operations (GET, PUT, DELETE)
  - Minimum 20 test cases covering all endpoints

---

**Q7: Bare Except Clause Replacement - Should we replace bare excepts with specific exception types, or implement a global error handler?**

**Answer:** Replace with specific exception types + logging:
```python
try:
    # operation
except SQLAlchemyError as e:
    logger.error(f"DB error: {str(e)}", exc_info=True)
    raise HTTPException(500, "Database error")
except HTTPException:
    raise
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    raise HTTPException(500, "Internal server error")
```
Sentry reporting deferred to Phase 5

**Requirements:**
- Identify and replace ALL bare `except:` clauses in codebase
- Use specific exception hierarchy:
  1. **Database exceptions**: `SQLAlchemyError` (or specific: IntegrityError, OperationalError)
  2. **Redis exceptions**: `RedisError`, `ConnectionError`
  3. **HTTP exceptions**: `HTTPException` (FastAPI) - always re-raise
  4. **LLM API exceptions**: `AnthropicError`, `APIError`, `RateLimitError`
  5. **Validation exceptions**: `ValidationError` (Pydantic)
  6. **Generic fallback**: `Exception` (only as final catch)
- Logging requirements for each exception:
  - Log at ERROR level
  - Include exception message: `str(e)`
  - Include full stack trace: `exc_info=True`
  - Include correlation_id if available
  - Example: `logger.error(f"DB error: {str(e)}", exc_info=True, extra={"correlation_id": correlation_id})`
- HTTPException handling:
  - If HTTPException caught: Re-raise immediately (don't wrap)
  - If other exception: Wrap in HTTPException with appropriate status code
  - Database errors: HTTP 500 "Database error"
  - Validation errors: HTTP 400 "Invalid input"
  - Unexpected errors: HTTP 500 "Internal server error"
- Do NOT implement Sentry reporting yet (Phase 5)
- Pattern to follow:
  ```python
  try:
      result = await db.execute(query)
  except SQLAlchemyError as e:
      logger.error(f"Database query failed: {str(e)}", exc_info=True)
      raise HTTPException(status_code=500, detail="Database error occurred")
  except HTTPException:
      raise  # Don't wrap existing HTTP exceptions
  except Exception as e:
      logger.error(f"Unexpected error in operation: {str(e)}", exc_info=True)
      raise HTTPException(status_code=500, detail="Internal server error")
  ```

---

**Q8: Error Response Standardization - What should the standard error response schema look like?**

**Answer:** Schema with correlation_id:
```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid credentials",
    "details": {},
    "correlation_id": "uuid-v4",
    "timestamp": "2025-10-25T10:30:00Z"
  }
}
```

**Requirements:**
- Create Pydantic model `ErrorResponse` with fields:
  - `code`: String error code (e.g., "AUTH_001", "AUTHZ_001", "DB_001")
  - `message`: Human-readable error message
  - `details`: Optional dict for additional context (default: empty dict)
  - `correlation_id`: UUID v4 for request tracing
  - `timestamp`: ISO 8601 timestamp in UTC
- Implement global exception handler in FastAPI:
  - Catch all exceptions
  - Convert to ErrorResponse format
  - Return with appropriate HTTP status code
- Error code conventions:
  - AUTH_xxx: Authentication errors (401)
  - AUTHZ_xxx: Authorization errors (403)
  - VAL_xxx: Validation errors (400)
  - DB_xxx: Database errors (500)
  - RATE_xxx: Rate limiting errors (429)
  - SYS_xxx: System/unexpected errors (500)
- Example error codes:
  - AUTH_001: Invalid credentials
  - AUTH_002: Token expired
  - AUTH_003: Token revoked
  - AUTHZ_001: Resource access denied
  - VAL_001: Invalid input format
  - RATE_001: Rate limit exceeded
  - DB_001: Database connection error
  - SYS_001: Internal server error
- Correlation ID:
  - Generate UUID v4 at request start (middleware)
  - Store in request context
  - Include in all log statements
  - Include in all error responses
  - Return in `X-Correlation-ID` response header
- Timestamp format: ISO 8601 with UTC timezone (e.g., "2025-10-25T10:30:00Z")
- Do NOT expose sensitive details (stack traces, SQL queries) in production
- Details field usage:
  - Validation errors: Include field names and validation failures
  - Rate limit errors: Include retry_after seconds
  - Production: Minimal details for security
  - Development: More verbose details for debugging

---

**Q9: Audit Logging Scope - What events should we audit log in Phase 1?**

**Answer:** Log in Phase 1:
- All auth events (login/logout/token refresh/failures)
- All conversation/message access attempts (success + failures)
- All failed authorization checks
- NO successful reads (defer to Phase 5)

Schema:
```python
{
    "timestamp": "ISO8601",
    "user_id": "uuid",
    "action": "conversation.read",
    "resource_type": "conversation",
    "resource_id": "uuid",
    "result": "success|denied",
    "ip_address": "string",
    "user_agent": "string"
}
```

**Requirements:**
- Create `audit_logs` table with schema:
  - `id`: UUID primary key
  - `timestamp`: DateTime (UTC, indexed)
  - `user_id`: UUID (nullable for anonymous actions, indexed)
  - `action`: String (e.g., "auth.login", "conversation.read")
  - `resource_type`: String (e.g., "conversation", "message", "user")
  - `resource_id`: UUID (nullable, indexed)
  - `result`: String ("success" or "denied")
  - `ip_address`: String (client IP address)
  - `user_agent`: String (browser user agent)
  - `metadata`: JSONB (additional context, optional)
- Create audit logger service at `/src/observability/audit_logger.py`
- Events to log in Phase 1:

  **Authentication events (ALL):**
  - `auth.login` - User login attempt (success/denied)
  - `auth.logout` - User logout (always success)
  - `auth.token_refresh` - Token refresh attempt (success/denied)
  - `auth.login_failed` - Failed login (wrong password, invalid user)

  **Authorization events (FAILURES ONLY):**
  - `conversation.read_denied` - Failed conversation access
  - `conversation.update_denied` - Failed conversation update
  - `conversation.delete_denied` - Failed conversation deletion
  - `message.create_denied` - Failed message creation
  - `message.read_denied` - Failed message access
  - `message.update_denied` - Failed message update
  - `message.delete_denied` - Failed message deletion

  **Modification events (ALL):**
  - `conversation.create` - New conversation created (always success)
  - `conversation.update` - Conversation updated
  - `conversation.delete` - Conversation deleted
  - `message.create` - New message created
  - `message.update` - Message updated
  - `message.delete` - Message deleted

  **Explicitly EXCLUDED in Phase 1:**
  - Successful read operations (GET endpoints)
  - System/background operations
  - Health check endpoint access
- Audit logging implementation:
  - Call audit logger after authorization check
  - Call audit logger on successful modification
  - Call audit logger on failed authentication
  - Extract IP from request headers (X-Forwarded-For or direct)
  - Extract User-Agent from request headers
  - Log asynchronously to avoid blocking requests
- Example audit log entry:
  ```python
  {
      "timestamp": "2025-10-25T10:30:00Z",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "action": "conversation.read_denied",
      "resource_type": "conversation",
      "resource_id": "660e8400-e29b-41d4-a716-446655440000",
      "result": "denied",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
  }
  ```
- Defer to Phase 5: Successful read logging, log aggregation, compliance reporting

---

**Q10: Zero-Downtime Deployment - Does the conversations table already have a user_id column, or do we need a migration?**

**Answer:**
- user_id column ALREADY EXISTS in conversations table
- No schema changes needed
- Only add validation in code (middleware)

**Requirements:**
- NO database migration required
- Verify existing schema:
  - conversations table has `user_id` column (UUID)
  - Foreign key to users table exists
  - Column is indexed for performance
- Implementation is code-only:
  - Add ownership validation middleware (see Q6)
  - No ALTER TABLE statements needed
  - No downtime required for deployment
  - No data migration scripts needed
- Verify in existing codebase:
  - Check SQLAlchemy Conversation model for user_id field
  - Verify foreign key relationship to User model
  - Confirm user_id is populated on conversation creation
- Deployment strategy:
  - Deploy code changes with middleware
  - No coordination with database team needed
  - Can roll out incrementally
  - Rollback is simple (remove middleware)

---

**Q11: Testing Coverage - What level of testing is expected for each P0 fix?**

**Answer:** For each P0 fix:
- Unit tests (function-level)
- Integration tests (endpoint-level)
- Security-specific tests (malicious inputs, bypass attempts)
- Manual security testing at end of Phase 1
- Target: Maintain 92% coverage, add ~50 new tests

**Requirements:**
- Maintain existing 92% test coverage throughout all changes
- Add approximately 50 new tests for P0 fixes:

  **1. JWT Secret Management (3 tests):**
  - Test startup fails when JWT_SECRET not set
  - Test token signing with environment-based secret
  - Test token validation with correct secret

  **2. Rate Limiting (8 tests):**
  - Test anonymous user hits global limit
  - Test anonymous user hits auth endpoint limit
  - Test authenticated user hits global limit
  - Test authenticated user hits auth endpoint limit
  - Test rate limit headers present in response
  - Test 429 status when limit exceeded
  - Test rate limit counter resets after window
  - Test different users have independent limits

  **3. CORS Configuration (5 tests):**
  - Test allowed origin receives CORS headers
  - Test disallowed origin receives 403
  - Test preflight OPTIONS request handling
  - Test multiple allowed origins parsing
  - Test credentials flag only for whitelisted origins

  **4. Token Blacklist (7 tests):**
  - Test logout adds token to blacklist
  - Test blacklisted access token rejected
  - Test blacklisted refresh token rejected
  - Test token blacklist TTL matches expiration
  - Test multiple logouts don't error
  - Test jti included in all tokens
  - Test logout with both access and refresh tokens

  **5. SQL Injection Prevention (6 tests):**
  - Test SQLAlchemy parameterized queries safe
  - Test ChromaDB search with SQL injection attempts
  - Test filter parameters validated
  - Test malicious input sanitized
  - Test common injection patterns blocked (', ", --, UNION)
  - Test parameterized queries for all endpoints

  **6. Conversation Ownership (10 tests):**
  - Test user can access own conversation
  - Test user cannot access other's conversation (GET)
  - Test user cannot update other's conversation (PUT)
  - Test user cannot delete other's conversation (DELETE)
  - Test superuser can access any conversation
  - Test ownership validation on message endpoints
  - Test 403 for unauthorized access
  - Test 404 for non-existent conversations
  - Test ownership check happens before other validations
  - Test bulk operations respect ownership

  **7. Exception Handling (5 tests):**
  - Test SQLAlchemyError caught and logged
  - Test HTTPException re-raised unchanged
  - Test unexpected Exception caught and wrapped
  - Test error logging includes stack trace
  - Test correlation_id included in logs

  **8. Error Response Format (6 tests):**
  - Test error response includes all required fields
  - Test error codes match conventions
  - Test correlation_id is UUID v4
  - Test timestamp is ISO 8601 UTC
  - Test details field for validation errors
  - Test sensitive info not exposed in production

  **9. Audit Logging (10 tests):**
  - Test login success logged
  - Test login failure logged
  - Test logout logged
  - Test token refresh logged
  - Test failed authorization logged
  - Test conversation creation logged
  - Test conversation deletion logged
  - Test audit log includes all required fields
  - Test IP address captured correctly
  - Test user_agent captured correctly

- Integration tests (endpoint-level):
  - Test full authentication flow with blacklist
  - Test rate limiting across multiple requests
  - Test CORS on actual HTTP requests
  - Test ownership validation on real endpoints
  - Test audit logging for complete user journeys

- Security-specific tests (penetration testing):
  - Attempt SQL injection on all input fields
  - Attempt authentication bypass with forged tokens
  - Attempt authorization bypass with modified requests
  - Attempt to exceed rate limits and verify blocking
  - Attempt CSRF with disallowed origins
  - Attempt to access other users' conversations
  - Attempt to reuse logged-out tokens

- Manual security testing at end of Phase 1:
  - Full penetration test of all P0 fixes
  - Security review by security team
  - Verify no regressions in existing security
  - Document any remaining risks for Phase 2+

- Coverage requirements:
  - Overall coverage: Maintain 92%+
  - New code coverage: 95%+ for all P0 fixes
  - Security-critical code: 100% coverage
  - Run coverage report in CI on every commit

---

**Q12: Phase 1 Exclusions - What should explicitly NOT be included in Phase 1?**

**Answer:** Explicitly exclude:
- Password complexity requirements
- 2FA/MFA
- Account lockout policies
- Advanced session management
- Complete security headers (CSP, HSTS)
- IP whitelisting for admin

Focus ONLY on the 8 P0 issues.

**Requirements:**
- Phase 1 scope is LIMITED to 8 P0 security vulnerabilities:
  1. JWT secret management
  2. Rate limiting
  3. CORS configuration
  4. Token blacklist
  5. SQL injection prevention
  6. Conversation ownership validation
  7. Exception handling
  8. Error response standardization
  9. Audit logging (supporting requirement)

- Explicitly OUT OF SCOPE for Phase 1:

  **Authentication enhancements (defer to Phase 6):**
  - Password complexity requirements (minimum length, special characters)
  - Two-factor authentication (2FA)
  - Multi-factor authentication (MFA)
  - Account lockout after failed login attempts
  - Password reset functionality enhancements
  - Social login (Google, GitHub, etc.)

  **Session management (defer to Phase 2/5):**
  - Advanced session management (concurrent session limits)
  - Session fingerprinting
  - Session activity tracking
  - Idle timeout enforcement
  - Remember me functionality

  **Security headers (partial in Phase 1, complete in Phase 5):**
  - Phase 1: Basic security headers only (X-XSS-Protection, X-Content-Type-Options)
  - Phase 5: Complete headers (CSP, HSTS, X-Frame-Options with strict policies)

  **Advanced access control (defer to Phase 2/6):**
  - IP whitelisting for admin endpoints
  - Role-based access control (RBAC) beyond basic superuser
  - Fine-grained permissions system
  - Resource-level permissions beyond ownership

  **Compliance features (defer to Phase 5):**
  - GDPR data export
  - GDPR right to erasure automation
  - Compliance reporting automation
  - Data retention policy enforcement

  **Infrastructure security (defer to Phase 5):**
  - WAF (Web Application Firewall) integration
  - DDoS protection beyond rate limiting
  - Bot detection
  - Intrusion detection system

- Clear focus: Address ONLY the 8 P0 vulnerabilities
- Rationale: Phase 1 eliminates production blockers; advanced features come later
- Timeline: 2 weeks maximum; additional features would delay critical fixes

---

### Existing Code to Reference

**Similar Features Identified:**

1. **Middleware patterns**: `/src/api/middleware/auth_middleware.py`
   - Reference for creating ownership validation middleware
   - Existing `get_current_user()` function to reuse
   - Existing `get_current_superuser()` function for admin bypass
   - Pattern for dependency injection in FastAPI

2. **Rate limit middleware**: `/src/api/middleware/rate_limit_middleware.py`
   - Middleware exists but currently DISABLED
   - Re-enable and enhance with Redis backing
   - Add per-user and per-endpoint configuration
   - Reference existing structure

3. **Authorization patterns**: In `auth_middleware.py`
   - `get_current_user()`: Extract user from JWT token
   - `get_current_superuser()`: Admin user validation
   - Dependency injection pattern for endpoints

4. **Redis usage**: `/src/state/redis_manager.py`
   - Existing Redis connection management
   - Reuse for rate limiting counters
   - Reuse for token blacklist storage
   - Reference connection retry patterns

5. **Error handling**: Currently inconsistent across codebase
   - CREATE NEW: `/src/api/responses/error_response.py`
   - Standardize error response format
   - Implement global exception handler
   - No existing pattern to reference

6. **Audit logging**: Does not exist
   - CREATE NEW: `/src/observability/audit_logger.py`
   - Create audit logs table schema
   - Implement async logging service
   - No existing pattern to reference

**Components to Potentially Reuse:**
- Auth middleware dependency injection pattern
- Redis connection pooling and retry logic
- SQLAlchemy session management
- Pydantic validation schemas
- FastAPI exception handlers

**Backend Logic to Reference:**
- Token generation and validation in auth service
- Database query patterns in conversation service
- WebSocket connection management (for ownership validation)
- Environment configuration loading

---

### Follow-up Questions

No follow-up questions were required. All clarifying questions were answered comprehensively in the first round.

---

## Visual Assets

### Files Provided:

No visual assets provided.

### Visual Insights:

N/A - This is a backend security remediation project. Visual assets not applicable.

The spec will include:
- Flow diagrams for authentication with token blacklist
- Flow diagrams for rate limiting logic
- Flow diagrams for authorization middleware
- Example JSON responses for error formats
- Example audit log entries
- Architecture diagrams showing security layers

These will be created by spec-writer as part of specification documentation.

---

## Requirements Summary

### Functional Requirements

**1. Secure Secrets Management**
- Load JWT_SECRET from environment (fail-fast if missing)
- Implement Pydantic Settings validation
- No hardcoded secrets anywhere in codebase
- Clear error messages for missing configuration

**2. Comprehensive Rate Limiting**
- Redis-backed distributed rate limiting
- Per-IP limits: 30 req/min global, 10 req/min on /auth/*
- Per-user limits: 100 req/min global, 20 req/min on /auth/*
- Standard rate limit headers (X-RateLimit-*)
- HTTP 429 when limits exceeded
- Per-endpoint decorator support

**3. Strict CORS Configuration**
- Environment-based origin whitelist (comma-separated)
- Exact string matching (no regex in Phase 1)
- Proper preflight handling
- Validate origin on every request
- Reject unauthorized origins with HTTP 403

**4. Token Blacklist and Logout**
- Add jti (JWT ID) to all tokens
- Blacklist access tokens (60 min TTL) and refresh tokens (30 day TTL)
- Store in Redis: `blacklist:access:{jti}` and `blacklist:refresh:{jti}`
- Middleware checks blacklist on every request
- Logout endpoint blacklists both token types
- Automatic cleanup via Redis TTL

**5. SQL Injection Prevention**
- Use SQLAlchemy text() with bind parameters
- Parameterized queries for all database operations
- Validate ChromaDB inputs before query construction
- Pydantic schemas for input validation
- Whitelist filter keys
- Security test suite for injection patterns

**6. Conversation Ownership Validation**
- Middleware decorator `@require_resource_ownership("conversation")`
- Validate conversation.user_id == current_user.user_id
- Admin bypass for superusers (is_superuser=True)
- Apply to ALL conversation and message endpoints
- HTTP 403 for unauthorized access
- 20+ authorization test cases

**7. Comprehensive Exception Handling**
- Replace ALL bare except clauses
- Use specific exception types (SQLAlchemyError, RedisError, etc.)
- Log all exceptions with stack traces and correlation_id
- Wrap exceptions in HTTPException with appropriate status codes
- Re-raise HTTPException unchanged
- Error logging at ERROR level with exc_info=True

**8. Standardized Error Responses**
- ErrorResponse Pydantic model with fields: code, message, details, correlation_id, timestamp
- Global exception handler in FastAPI
- Consistent error codes (AUTH_*, AUTHZ_*, VAL_*, DB_*, RATE_*, SYS_*)
- Correlation ID in response and X-Correlation-ID header
- ISO 8601 timestamps in UTC
- Minimal details in production (security)

**9. Comprehensive Audit Logging**
- Create audit_logs table with full schema
- Audit logger service at `/src/observability/audit_logger.py`
- Log authentication events (login, logout, token refresh, failures)
- Log authorization failures (conversation/message access denied)
- Log modification events (create, update, delete)
- Exclude successful reads in Phase 1
- Capture user_id, action, resource, result, IP, user_agent
- Async logging to avoid blocking requests

### Reusability Opportunities

**Existing Middleware to Enhance:**
- `/src/api/middleware/auth_middleware.py` - Add ownership validation decorator
- `/src/api/middleware/rate_limit_middleware.py` - Re-enable with Redis backing

**Existing Services to Reference:**
- `/src/state/redis_manager.py` - Redis connection patterns for blacklist and rate limiting
- Auth service - Token generation/validation patterns

**New Components to Create:**
- `/src/api/responses/error_response.py` - Standardized error responses
- `/src/observability/audit_logger.py` - Audit logging service
- `/src/api/middleware/correlation_id_middleware.py` - Correlation ID injection
- `/src/api/middleware/ownership_middleware.py` - Resource ownership validation

**Database Patterns to Reuse:**
- SQLAlchemy session management
- Query patterns from conversation service
- Transaction handling patterns

### Scope Boundaries

**In Scope (Phase 1):**
1. JWT secret from environment with fail-fast validation
2. Redis-backed rate limiting (per-IP and per-user)
3. CORS origin whitelist from environment
4. Token blacklist for logout (access + refresh tokens)
5. SQL injection prevention via parameterized queries
6. Conversation ownership validation middleware
7. Replace bare except clauses with specific exceptions
8. Standardized error response format with correlation_id
9. Audit logging for auth, authz, and modifications
10. 50+ new tests (unit, integration, security)
11. Maintain 92% test coverage
12. Manual security testing at end of Phase 1

**Out of Scope (Deferred to Later Phases):**
- Password complexity requirements (Phase 6)
- 2FA/MFA (Phase 6)
- Account lockout policies (Phase 6)
- Advanced session management (Phase 2/5)
- Complete security headers (CSP, HSTS) (Phase 5)
- IP whitelisting for admin (Phase 2/6)
- GDPR compliance automation (Phase 5)
- Sentry error reporting (Phase 5)
- Log aggregation (Phase 5)
- Query validation middleware (Phase 5)
- Successful read operation logging (Phase 5)
- Password reset enhancements (Phase 6)
- Role-based access control beyond superuser (Phase 6)
- WAF integration (Phase 5)
- DDoS protection beyond rate limiting (Phase 5)

### Technical Considerations

**Integration Points:**
- FastAPI middleware stack (add CORS, rate limiting, correlation ID, ownership validation)
- Redis for token blacklist and rate limiting counters
- PostgreSQL for audit_logs table
- SQLAlchemy for parameterized queries
- Pydantic for configuration validation and error responses
- Existing auth_middleware for user authentication

**Existing System Constraints:**
- Must maintain 92% test coverage
- user_id column already exists (no schema migration needed)
- Redis already in use (expand usage)
- Cannot break existing API contracts
- Must support zero-downtime deployment
- Must work with existing authentication flow

**Technology Preferences:**
- Pydantic Settings for configuration management
- Redis for distributed state (blacklist, rate limits)
- SQLAlchemy text() with bind parameters for raw SQL
- FastAPI dependency injection for middleware
- Python logging with structured fields
- pytest for testing

**Similar Code Patterns to Follow:**
- Middleware pattern: `/src/api/middleware/auth_middleware.py`
- Redis usage: `/src/state/redis_manager.py`
- Dependency injection: `get_current_user()`, `get_current_superuser()`
- Pydantic models: Existing request/response schemas
- FastAPI exception handlers: Extend existing patterns
- Test structure: Existing 244-test pytest suite

**Performance Considerations:**
- Rate limiting Redis operations must be fast (<10ms)
- Blacklist checks on every request must not add latency
- Audit logging must be async to avoid blocking
- Ownership validation queries must be optimized (indexed user_id)
- Correlation ID generation must be lightweight
- Error response formatting must not slow down error paths

**Security Requirements:**
- JWT_SECRET minimum 32 characters (enforce in validation)
- Token blacklist prevents replay attacks
- Rate limiting prevents brute force and DDoS
- CORS prevents CSRF attacks
- Parameterized queries prevent SQL injection
- Ownership validation prevents horizontal privilege escalation
- Error responses don't leak sensitive information
- Audit logs capture security-relevant events

**Deployment Strategy:**
- No database migrations required (user_id exists)
- Deploy code changes incrementally
- Enable rate limiting gradually (monitor false positives)
- Enable audit logging from day one (required for security)
- Zero-downtime deployment supported
- Rollback strategy: Remove middleware, restore old code

**Testing Strategy:**
- Unit tests: 50+ new tests for each P0 fix
- Integration tests: Full endpoint testing with security scenarios
- Security tests: Malicious input testing, bypass attempts
- Manual penetration testing: End of Phase 1
- Coverage: Maintain 92%, target 95% for new code
- CI/CD: Run all tests on every commit
- Load testing: Verify rate limiting doesn't degrade performance

**Monitoring and Observability:**
- Log all rate limit violations
- Log all authorization failures
- Log all audit events
- Include correlation_id in all logs
- Monitor rate limiting effectiveness
- Monitor blacklist size growth
- Alert on high rate limit violations
- Defer metrics/tracing to Phase 5

**Documentation Requirements:**
- Document all environment variables
- Document error codes and meanings
- Document audit log schema
- Document rate limiting strategy
- Document ownership validation rules
- Document testing approach
- Document deployment procedure
- Update API documentation with new error formats

---

## Success Criteria

**Phase 1 Complete When:**

1. **Security Vulnerabilities Eliminated (8/8 P0 issues):**
   - ✅ JWT_SECRET loaded from environment, fail-fast if missing
   - ✅ Rate limiting active (Redis-backed, per-IP, per-user)
   - ✅ CORS restricted to whitelisted origins only
   - ✅ Token blacklist implemented for logout
   - ✅ SQL injection prevented via parameterized queries
   - ✅ Conversation ownership validated on all endpoints
   - ✅ All bare except clauses replaced with specific exceptions
   - ✅ Error responses standardized with correlation_id

2. **Testing Coverage:**
   - ✅ 50+ new tests added (unit, integration, security)
   - ✅ 92%+ test coverage maintained
   - ✅ 95%+ coverage for new security code
   - ✅ All security test scenarios pass
   - ✅ Manual penetration testing completed with zero critical findings

3. **Audit Logging:**
   - ✅ Audit logs table created and indexed
   - ✅ All authentication events logged
   - ✅ All authorization failures logged
   - ✅ All modification events logged
   - ✅ Logs include user_id, action, resource, result, IP, user_agent

4. **Documentation:**
   - ✅ All environment variables documented
   - ✅ Error codes and meanings documented
   - ✅ Audit log schema documented
   - ✅ Testing approach documented
   - ✅ Deployment procedure documented

5. **Deployment Readiness:**
   - ✅ Zero-downtime deployment verified
   - ✅ No database migrations required
   - ✅ Rollback procedure tested
   - ✅ Configuration validation on startup works
   - ✅ Production environment variables prepared

6. **Security Validation:**
   - ✅ Penetration testing passed (zero critical vulnerabilities)
   - ✅ SQL injection tests pass
   - ✅ Authentication bypass attempts fail
   - ✅ Authorization bypass attempts fail
   - ✅ Rate limiting blocks excessive requests
   - ✅ CSRF attacks from unauthorized origins blocked
   - ✅ Logged-out tokens rejected

7. **Performance:**
   - ✅ Rate limiting adds <10ms latency
   - ✅ Blacklist checks add <5ms latency
   - ✅ Ownership validation adds <10ms latency
   - ✅ Audit logging doesn't block requests (async)
   - ✅ No performance regression on existing endpoints

**Definition of Done for Each P0 Fix:**
- Code implemented and peer reviewed
- Unit tests written and passing
- Integration tests written and passing
- Security tests written and passing
- Documentation updated
- No regression in existing tests
- Coverage maintained at 92%+
- Manual testing completed
- Security team approved

**Phase 1 Acceptance Criteria:**
- Security team signs off on all P0 fixes
- All 50+ new tests passing in CI
- Zero critical vulnerabilities in security scan
- Manual penetration testing report shows zero critical/high findings
- Documentation complete and reviewed
- Deployment to staging successful
- Performance benchmarks met
- Ready for Phase 2 (P1 reliability issues)
