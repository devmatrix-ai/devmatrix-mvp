# Task Breakdown: Phase 1 - Critical Security Vulnerabilities

## Overview
Total Tasks: 7 Groups, 100+ Sub-tasks
Total New Tests: 50+
Timeline: 2 weeks (Weeks 1-2 of 10-week roadmap)
Priority: P0 - Critical

## Task List

### Group 1: Foundation & Configuration Layer
**Specialist:** Backend Engineer
**Dependencies:** None
**Estimated Time:** 2-3 days

- [x] 1.0 Complete foundation and configuration infrastructure
  - [x] 1.1 Write 2-8 focused tests for configuration validation
    - Test application fails on startup when JWT_SECRET missing
    - Test application fails when JWT_SECRET < 32 characters
    - Test application fails when DATABASE_URL missing
    - Test CORS_ALLOWED_ORIGINS parses comma-separated list correctly
    - Test configuration loads successfully with all required variables
    - Test environment variable validation on startup
  - [x] 1.2 Create `/src/config/settings.py` with Pydantic Settings
    - Implement Settings class extending BaseSettings
    - Add JWT_SECRET field (required, no default)
    - Add JWT_SECRET validator (minimum 32 characters)
    - Add DATABASE_URL field (required, no default)
    - Add CORS_ALLOWED_ORIGINS field (string, comma-separated)
    - Add optional fields: REDIS_HOST, REDIS_PORT, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS
    - Configure env_file = ".env"
    - Configure case_sensitive = True
  - [x] 1.3 Update `/src/main.py` to add startup validation
    - Import Settings from config
    - Add @app.on_event("startup") handler
    - Load Settings() in startup handler
    - Call settings.validate_jwt_secret()
    - Wrap in try/except with critical logging
    - Raise SystemExit(1) on validation failure
    - Test startup fails appropriately
  - [x] 1.4 Create `.env.example` with all required variables
    - Add JWT_SECRET with example (show minimum 32 chars)
    - Add DATABASE_URL with example connection string
    - Add CORS_ALLOWED_ORIGINS with examples for dev/staging/prod
    - Add optional variables with defaults
    - Add comments explaining each variable
    - Add security warnings for sensitive variables
  - [x] 1.5 Update `/src/services/auth_service.py` to use Settings
    - Import Settings from config
    - Remove hardcoded JWT_SECRET fallback (line 21)
    - Load settings = Settings() in module
    - Replace JWT_SECRET references with settings.JWT_SECRET
    - Update token expiration to use settings values
    - Verify no hardcoded secrets remain
  - [x] 1.6 Update `/src/config/database.py` to use Settings
    - Import Settings from config
    - Remove any hardcoded database credentials
    - Load DATABASE_URL from settings.DATABASE_URL
    - Update engine creation to use settings.DATABASE_URL
    - Verify fail-fast on missing DATABASE_URL
  - [x] 1.7 Ensure foundation layer tests pass
    - Run ONLY the 2-8 tests written in 1.1
    - Verify application fails on startup without required vars
    - Verify application starts successfully with all vars
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 1.1 pass
- Application fails fast on startup if JWT_SECRET missing
- Application fails fast on startup if DATABASE_URL missing
- JWT_SECRET must be minimum 32 characters
- All secrets loaded from environment only
- No hardcoded fallback values exist
- Settings validated via Pydantic

---

### Group 2: Core Security Infrastructure
**Specialist:** Backend Engineer
**Dependencies:** Group 1 (Settings)
**Estimated Time:** 3-4 days

- [x] 2.0 Complete core security infrastructure
  - [x] 2.1 Write 2-8 focused tests for security infrastructure
    - Test ErrorResponse model includes all required fields
    - Test correlation_id is valid UUID v4
    - Test timestamp is ISO 8601 UTC format
    - Test correlation_id middleware generates unique ID per request
    - Test correlation_id appears in response headers
    - Test global exception handler converts exceptions to ErrorResponse
    - Test error codes match conventions (AUTH_*, AUTHZ_*, etc.)
  - [x] 2.2 Create `/src/api/responses/error_response.py`
    - Import Pydantic BaseModel, Field, datetime, uuid
    - Create ErrorResponse class extending BaseModel
    - Add fields: code (str), message (str), details (Dict), correlation_id (str), timestamp (str)
    - Set default for correlation_id: lambda: str(uuid.uuid4())
    - Set default for timestamp: lambda: datetime.utcnow().isoformat() + "Z"
    - Set default for details: empty dict
    - Add Config class with json_schema_extra example
    - Document error code conventions in docstring
  - [x] 2.3 Create `/src/api/middleware/correlation_id_middleware.py`
    - Import FastAPI Request, Response, uuid
    - Create correlation_id_middleware function
    - Generate UUID v4 for each request
    - Store in request.state.correlation_id
    - Add X-Correlation-ID to response headers
    - Ensure middleware runs before all other middleware
  - [x] 2.4 Update `/src/main.py` to add global exception handler
    - Import ErrorResponse from responses
    - Import HTTPException, Request, Response
    - Create @app.exception_handler(Exception) function
    - Extract correlation_id from request.state
    - Convert exception to ErrorResponse format
    - Map exception types to error codes (AUTH_*, AUTHZ_*, DB_*, etc.)
    - Return JSONResponse with ErrorResponse
    - Include X-Correlation-ID in response headers
  - [x] 2.5 Update `/src/main.py` to add correlation_id middleware
    - Import correlation_id_middleware
    - Add app.middleware("http")(correlation_id_middleware)
    - Ensure middleware runs first in chain
    - Test correlation_id available in request handlers
  - [x] 2.6 Replace bare except clauses across codebase
    - Search all .py files for "except:" patterns
    - Replace with specific exception types: SQLAlchemyError, RedisError, HTTPException, ValidationError, AnthropicError, Exception
    - Add logging with correlation_id for all exceptions
    - Use logger.error with exc_info=True for stack traces
    - Wrap exceptions in HTTPException with appropriate status codes
    - Database errors: HTTP 500 "Database error occurred"
    - Validation errors: HTTP 400 "Invalid input"
    - Re-raise HTTPException unchanged
    - Common files to update: `/src/services/*.py`, `/src/api/routers/*.py`, `/src/rag/*.py`
  - [x] 2.7 Update `/src/services/auth_service.py` exception handling
    - Replace bare except clauses
    - Add specific exception handling for database errors
    - Add correlation_id to all log statements
    - Wrap exceptions in HTTPException
  - [x] 2.8 Ensure security infrastructure tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify ErrorResponse format is correct
    - Verify correlation_id in all responses
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 2.1 pass
- ErrorResponse model complete with all fields
- Correlation ID generated for every request
- Correlation ID in logs and response headers
- Global exception handler converts all exceptions
- All bare except clauses replaced with specific types
- All exceptions logged with stack traces
- Error codes follow conventions

---

### Group 3: Authentication Security Layer
**Specialist:** Backend Engineer
**Dependencies:** Groups 1-2 (Settings, Error Infrastructure)
**Estimated Time:** 3-4 days

- [x] 3.0 Complete authentication security layer
  - [x] 3.1 Write 2-8 focused tests for authentication security
    - Test jti claim included in access tokens
    - Test jti claim included in refresh tokens
    - Test logout adds access token to blacklist
    - Test logout adds refresh token to blacklist
    - Test blacklisted access token rejected with 401
    - Test blacklisted refresh token rejected with 401
    - Test blacklist TTL matches token expiration
    - Test token reuse after logout fails
  - [x] 3.2 Update `/src/services/auth_service.py` to add jti to tokens
    - Import uuid
    - Add jti to access token payload: "jti": str(uuid.uuid4())
    - Add jti to refresh token payload: "jti": str(uuid.uuid4())
    - Store token type in payload: "type": "access" or "refresh"
    - Ensure jti included in all token generation functions
  - [x] 3.3 Update `/src/services/auth_service.py` to implement blacklist check
    - Import redis_client from state/redis_manager
    - Create check_token_blacklist function
    - Extract jti and type from token payload
    - Check Redis for key: blacklist:{type}:{jti}
    - If exists, raise HTTPException(401, "Token has been revoked")
    - Return payload if not blacklisted
  - [x] 3.4 Update token validation to check blacklist before user lookup
    - Modify validate_token function
    - Decode JWT token
    - Call check_token_blacklist(payload)
    - If blacklisted, raise 401 immediately
    - If not blacklisted, proceed with user lookup
  - [x] 3.5 Create logout endpoint in `/src/api/routers/auth.py`
    - Add @router.post("/logout") endpoint
    - Accept optional refresh_token in request body
    - Extract jti from current access token (from get_current_user)
    - Extract jti from refresh_token if provided
    - Add access token to blacklist: redis.setex(f"blacklist:access:{jti}", 3600, "1")
    - Add refresh token to blacklist if provided: redis.setex(f"blacklist:refresh:{jti}", 2592000, "1")
    - Return 200 with message: "Successfully logged out"
    - Handle errors with proper error codes
  - [x] 3.6 Update `/src/api/middleware/auth_middleware.py` to check blacklist
    - Import check_token_blacklist from auth_service
    - In get_current_user function, after decoding token
    - Call check_token_blacklist before user lookup
    - If blacklisted, raise 401 immediately
    - Add correlation_id to log statements
  - [x] 3.7 Ensure authentication security tests pass
    - Run ONLY the 2-8 tests written in 3.1
    - Verify jti in all tokens
    - Verify logout blacklists tokens
    - Verify blacklisted tokens rejected
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 3.1 pass (8/8 passing)
- jti claim in all access and refresh tokens
- Logout endpoint blacklists both token types
- Blacklisted tokens rejected with 401
- Redis TTL matches token expiration
- Token reuse after logout fails
- Auth middleware checks blacklist first

---

### Group 4: Authorization & Access Control Layer
**Specialist:** Backend Engineer
**Dependencies:** Groups 1-3 (Settings, Error Infrastructure, Auth Security)
**Estimated Time:** 3-4 days

- [x] 4.0 Complete authorization and access control layer
  - [x] 4.1 Write 2-8 focused tests for authorization
    - Test user can access own conversation (200)
    - Test user cannot access other's conversation (403)
    - Test user cannot update other's conversation (403)
    - Test user cannot delete other's conversation (403)
    - Test superuser can access any conversation (200)
    - Test ownership validation on message endpoints (403)
    - Test 404 for non-existent conversation
    - Test ownership check before other validations
  - [x] 4.2 Create `/src/api/middleware/ownership_middleware.py`
    - Import functools.wraps, FastAPI HTTPException, Depends
    - Import Conversation model, get_current_user, get_db_context
    - Create require_resource_ownership(resource_type: str) decorator
    - Extract conversation_id from kwargs
    - Extract current_user from kwargs
    - Load conversation from database
    - If not found, raise HTTPException(404, "Conversation not found")
    - Check conversation.user_id == current_user.user_id
    - If mismatch and not superuser, log warning and raise HTTPException(403, "Access denied: You do not own this resource")
    - If superuser, allow access
    - Return wrapped function
  - [x] 4.3 Apply ownership decorator to conversation endpoints
    - Update `/src/api/routers/chat.py`
    - Import require_resource_ownership from middleware
    - Apply @require_resource_ownership("conversation") to:
      - GET /conversations/{conversation_id}
      - PUT /conversations/{conversation_id}
      - DELETE /conversations/{conversation_id}
      - GET /conversations/{conversation_id}/messages
      - POST /conversations/{conversation_id}/messages
    - Ensure conversation_id and current_user in function parameters
  - [x] 4.4 Apply ownership decorator to message endpoints
    - Update `/src/api/routers/chat.py`
    - Apply @require_resource_ownership("conversation") to:
      - PUT /conversations/{conversation_id}/messages/{message_id}
      - DELETE /conversations/{conversation_id}/messages/{message_id}
    - Message ownership inherits from conversation ownership
  - [x] 4.5 Create audit_logs database table
    - Create migration file for audit_logs table
    - Add columns: id (UUID PK), timestamp (TIMESTAMP WITH TIME ZONE), user_id (UUID FK), action (VARCHAR), resource_type (VARCHAR), resource_id (UUID), result (VARCHAR CHECK), ip_address (VARCHAR), user_agent (TEXT), metadata (JSONB)
    - Add indexes: timestamp, user_id, resource (type + id), action
    - Run migration
  - [x] 4.6 Create `/src/observability/audit_logger.py`
    - Import asyncio, datetime, uuid
    - Import database session, AuditLog model
    - Create AuditLogger class
    - Add async log_event method
    - Accept parameters: user_id, action, resource_type, resource_id, result, ip_address, user_agent, metadata
    - Create AuditLog record
    - Insert into database asynchronously
    - Handle errors gracefully (log but don't block request)
  - [x] 4.7 Integrate audit logging into ownership middleware
    - Import AuditLogger
    - Log failed authorization attempts
    - Action: "{resource_type}.read_denied", "{resource_type}.update_denied", etc.
    - Include user_id, resource_type, resource_id, result="denied"
    - Extract IP from request headers (X-Forwarded-For or direct)
    - Extract User-Agent from request headers
    - Call audit_logger.log_event asynchronously
  - [x] 4.8 Integrate audit logging into auth endpoints
    - Update `/src/api/routers/auth.py`
    - Log auth.login on successful login
    - Log auth.login_failed on failed login
    - Log auth.logout on logout
    - Log auth.token_refresh on token refresh
    - Include user_id, IP address, user_agent
  - [x] 4.9 Integrate audit logging into modification endpoints
    - Update `/src/api/routers/chat.py`
    - Log conversation.create on POST /conversations
    - Log conversation.update on PUT /conversations/{id}
    - Log conversation.delete on DELETE /conversations/{id}
    - Log message.create on POST /conversations/{id}/messages
    - Log message.update on PUT messages endpoint
    - Log message.delete on DELETE messages endpoint
  - [x] 4.10 Ensure authorization layer tests pass
    - Run ONLY the 2-8 tests written in 4.1
    - Verify ownership validation works
    - Verify superuser bypass works
    - Verify 403 for unauthorized access
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 4.1 pass
- Ownership middleware decorator complete
- Applied to all conversation and message endpoints
- Superuser bypass works correctly
- 403 for unauthorized access with clear message
- 404 for non-existent resources
- Audit logs table created with indexes
- Audit logger service implemented
- Auth events logged (login, logout, failures)
- Authorization failures logged
- Modification events logged (create, update, delete)
- Successful reads NOT logged (Phase 1 exclusion)

---

### Group 5: API Security Layer
**Specialist:** Backend Engineer
**Dependencies:** Groups 1-4 (all previous layers)
**Estimated Time:** 3-4 days

- [ ] 5.0 Complete API security layer
  - [ ] 5.1 Write 2-8 focused tests for API security
    - Test anonymous user hits global rate limit (429)
    - Test anonymous user hits auth endpoint limit (429)
    - Test authenticated user hits global limit (429)
    - Test rate limit headers present (X-RateLimit-*)
    - Test allowed CORS origin receives headers
    - Test disallowed CORS origin rejected (403)
    - Test SQL injection attempts blocked
    - Test parameterized queries safe from injection
  - [ ] 5.2 Update `/src/api/middleware/rate_limit_middleware.py`
    - Enable middleware (currently disabled)
    - Implement Redis-backed rate limiting
    - Add per-IP rate limits: 30 req/min global, 10 req/min on /auth/*
    - Add per-user rate limits: 100 req/min global, 20 req/min on /auth/*
    - Use Redis key format: rate_limit:{user|ip}:{identifier}
    - Implement sliding window algorithm
    - Add rate limit headers to all responses:
      - X-RateLimit-Limit (max requests per window)
      - X-RateLimit-Remaining (requests remaining)
      - X-RateLimit-Reset (Unix timestamp when resets)
    - Return HTTP 429 when limit exceeded
    - Add Retry-After header on 429 response
    - Support per-endpoint override decorators
    - Set Redis TTL to 120 seconds
  - [ ] 5.3 Update `/src/main.py` to enable rate limiting
    - Import rate_limit_middleware
    - Add app.middleware("http")(rate_limit_middleware)
    - Ensure middleware runs after correlation_id middleware
    - Configure Redis connection for rate limiting
  - [ ] 5.4 Add stricter rate limits to auth endpoints
    - Update `/src/api/routers/auth.py`
    - Apply @rate_limit decorator to auth endpoints
    - Anonymous: 10 req/min on /auth/*
    - Authenticated: 20 req/min on /auth/*
    - Override global limits for sensitive endpoints
  - [ ] 5.5 Update `/src/main.py` to configure CORS from environment
    - Import CORSMiddleware from fastapi.middleware.cors
    - Import Settings
    - Load allowed_origins from settings.CORS_ALLOWED_ORIGINS
    - Parse as comma-separated list: [o.strip() for o in origins.split(",") if o.strip()]
    - Add CORSMiddleware with:
      - allow_origins=allowed_origins (exact string matching)
      - allow_credentials=True
      - allow_methods=["*"]
      - allow_headers=["*"]
    - Remove any wildcard origin configurations
    - Test preflight OPTIONS requests
    - Validate origin on every request
  - [ ] 5.6 Update `/src/rag/vector_store.py` for SQL injection prevention
    - Add input validation with Pydantic schemas
    - Create SearchRequest schema with query and limit fields
    - Add validator for query: max length 500, no SQL special characters
    - Add validator for limit: 1-100 range
    - Sanitize query input: remove ', ", --, ;, /*, */
    - Whitelist allowed filter keys
    - Use parameterized queries for ChromaDB
    - Never use string concatenation for queries
  - [ ] 5.7 Update all database queries to use parameterized queries
    - Search for string concatenation in SQL: f"SELECT", f"INSERT", f"UPDATE", f"DELETE"
    - Replace with SQLAlchemy text() and bindparams
    - Example: text("SELECT * FROM conversations WHERE id = :id").bindparams(id=conv_id)
    - Update queries in: `/src/services/*.py`, `/src/api/routers/*.py`
    - Verify all queries use ORM or parameterized text()
  - [ ] 5.8 Ensure API security layer tests pass
    - Run ONLY the 2-8 tests written in 5.1
    - Verify rate limiting works
    - Verify CORS configuration works
    - Verify SQL injection prevention works
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 5.1 pass
- Rate limiting enabled with Redis backing
- Rate limits enforced: 30/100 req/min global, 10/20 req/min auth
- Rate limit headers in all responses
- HTTP 429 when limits exceeded
- CORS origins from environment (comma-separated)
- Disallowed origins rejected with 403
- Preflight OPTIONS handled correctly
- All SQL queries parameterized
- ChromaDB inputs validated and sanitized
- SQL injection attempts blocked

---

### Group 6: Testing & Quality Assurance
**Specialist:** QA Engineer / Backend Engineer
**Dependencies:** Groups 1-5 (all implementation complete)
**Estimated Time:** 3-4 days

- [ ] 6.0 Complete comprehensive testing and quality assurance
  - [ ] 6.1 Review existing tests from Groups 1-5
    - Review 2-8 tests from Group 1 (Foundation)
    - Review 2-8 tests from Group 2 (Security Infrastructure)
    - Review 2-8 tests from Group 3 (Authentication)
    - Review 2-8 tests from Group 4 (Authorization)
    - Review 2-8 tests from Group 5 (API Security)
    - Total existing tests: approximately 10-40 tests
  - [ ] 6.2 Analyze test coverage gaps for Phase 1 features only
    - Run coverage report: pytest --cov=src --cov-report=html
    - Identify critical paths without coverage
    - Focus on security-critical code paths
    - Identify integration points between layers
    - Focus ONLY on Phase 1 feature gaps
    - Do NOT assess entire application coverage
    - Prioritize end-to-end security workflows
  - [ ] 6.3 Write additional unit tests (maximum 10 tests)
    - JWT secret validation tests (minimum length, missing)
    - Token generation with jti tests
    - Blacklist check logic tests
    - Rate limit counter logic tests
    - Ownership validation logic tests
    - Input sanitization tests
    - Error response formatting tests
    - Audit log creation tests
    - Settings validation tests
    - CORS origin parsing tests
  - [ ] 6.4 Write integration tests (5-10 tests)
    - Full authentication flow: login -> access resource -> logout -> access fails
    - Rate limiting: exceed limit -> get 429 -> wait -> succeed
    - CORS: allowed origin -> preflight -> request succeeds
    - Ownership: user A creates conversation -> user B access fails -> admin accesses succeeds
    - SQL injection: malicious input -> validation blocks -> safe query executes
    - Token blacklist: logout -> token blacklisted -> token rejected
    - Audit logging: action triggers -> audit log created -> fields correct
  - [ ] 6.5 Write security-specific tests (5-10 tests)
    - SQL injection attempts: ', ", --, UNION, DROP TABLE
    - Authentication bypass: forged token, expired token, modified payload
    - Authorization bypass: modify user_id, access other resources
    - Rate limit evasion: multiple IPs, rotating users
    - CSRF with disallowed origins
    - Token reuse after logout
    - Blacklist TTL expiration
    - XSS in error messages
  - [ ] 6.6 Run feature-specific tests only
    - Run tests related to Phase 1 features only
    - Do NOT run entire application test suite
    - Expected total: approximately 30-60 tests maximum
    - Generate coverage report for new code
    - Verify 95%+ coverage on new code
    - Verify 92%+ coverage maintained overall
  - [ ] 6.7 Perform manual security testing
    - Test JWT_SECRET missing scenario
    - Test rate limiting with real requests
    - Test CORS with browser requests
    - Test logout and token blacklist
    - Test SQL injection on all endpoints
    - Test ownership validation manually
    - Test error responses and correlation IDs
    - Test audit logs created correctly
    - Document all findings
  - [ ] 6.8 Perform manual penetration testing
    - Attempt to bypass authentication
    - Attempt to bypass authorization
    - Attempt SQL injection on all inputs
    - Attempt rate limit evasion
    - Attempt CSRF attacks
    - Attempt to access other users' data
    - Attempt to reuse logged-out tokens
    - Document zero critical findings
  - [ ] 6.9 Generate security test report
    - Summarize all test results
    - Document test coverage by P0 issue
    - List all security test scenarios
    - Document penetration testing results
    - Verify zero critical vulnerabilities
    - List any minor findings for Phase 2+

**Acceptance Criteria:**
- All feature-specific tests pass (30-60 tests total)
- No more than 10 additional unit tests added
- Critical security workflows covered
- Integration tests cover end-to-end flows
- Security tests cover all attack vectors
- Manual penetration testing completed
- Zero critical vulnerabilities found
- 95%+ coverage on new code
- 92%+ overall coverage maintained
- Testing focused exclusively on Phase 1 features
- Security test report generated

---

### Group 7: Documentation & Deployment
**Specialist:** DevOps Engineer / Technical Writer
**Dependencies:** Groups 1-6 (all implementation and testing complete)
**Estimated Time:** 2-3 days

- [ ] 7.0 Complete documentation and deployment preparation
  - [ ] 7.1 Document environment variables
    - Create environment variables documentation
    - Document JWT_SECRET: purpose, format, minimum length, generation
    - Document DATABASE_URL: format, examples, security notes
    - Document CORS_ALLOWED_ORIGINS: format, examples for dev/staging/prod
    - Document optional variables: REDIS_HOST, REDIS_PORT, token expiration
    - Add security warnings for sensitive variables
    - Document fail-fast behavior when missing
    - Add to .env.example with clear comments
  - [ ] 7.2 Document error codes and meanings
    - Create error codes documentation
    - List all error codes: AUTH_*, AUTHZ_*, VAL_*, DB_*, RATE_*, SYS_*
    - Document HTTP status code for each
    - Document when each error is returned
    - Document error response format
    - Document correlation_id usage
    - Add examples for each error type
  - [ ] 7.3 Document audit log schema and events
    - Create audit logging documentation
    - Document audit_logs table schema
    - List all logged events: auth, authz failures, modifications
    - Document event naming convention
    - Document fields: user_id, action, resource_type, resource_id, result, IP, user_agent
    - Document Phase 1 exclusions (successful reads)
    - Document querying audit logs
    - Add retention policy notes
  - [ ] 7.4 Document rate limiting strategy
    - Create rate limiting documentation
    - Document global limits: 30 req/min anonymous, 100 req/min authenticated
    - Document auth endpoint limits: 10 req/min anonymous, 20 req/min authenticated
    - Document rate limit headers
    - Document 429 response format
    - Document Retry-After header
    - Document Redis key format
    - Document per-endpoint overrides
  - [ ] 7.5 Document ownership validation rules
    - Create authorization documentation
    - Document ownership validation logic
    - Document superuser bypass rules
    - List all protected endpoints
    - Document 403 error for unauthorized access
    - Document 404 for non-existent resources
    - Document message ownership inheritance
    - Add examples of successful and failed access
  - [ ] 7.6 Create deployment documentation
    - Create deployment guide
    - Document prerequisites: environment variables, Redis, PostgreSQL
    - Document pre-deployment checks
    - Document staging deployment steps
    - Document smoke testing procedure
    - Document production deployment steps
    - Document rollback procedure
    - Document zero-downtime deployment strategy
    - Document monitoring and alerting
  - [ ] 7.7 Create zero-downtime deployment checklist
    - Verify environment variables set
    - Verify Redis available and configured
    - Verify PostgreSQL accessible
    - Run all tests in CI
    - Deploy to staging
    - Run smoke tests on staging
    - Verify health check endpoint
    - Deploy to production
    - Monitor error logs for 1 hour
    - Verify rate limiting active
    - Verify audit logging active
    - Document rollback trigger conditions
  - [ ] 7.8 Update API documentation
    - Update API docs with new error format
    - Document correlation_id in responses
    - Document rate limit headers
    - Document new logout endpoint
    - Document error codes for each endpoint
    - Add examples of error responses
    - Document authentication flow with blacklist
  - [ ] 7.9 Create security testing guide
    - Document how to run security tests
    - Document penetration testing procedure
    - Document security test scenarios
    - Document expected results
    - Document how to verify P0 fixes
    - Document security validation checklist
  - [ ] 7.10 Prepare production environment
    - Generate strong JWT_SECRET (32+ chars)
    - Set DATABASE_URL for production
    - Set CORS_ALLOWED_ORIGINS for production domain
    - Configure Redis for production
    - Set optional variables if needed
    - Verify all environment variables set
    - Test configuration validation
    - Document environment setup

**Acceptance Criteria:**
- Environment variables documented with examples
- Error codes documented with meanings
- Audit log schema and events documented
- Rate limiting strategy documented
- Ownership validation rules documented
- Deployment guide complete with steps
- Zero-downtime deployment checklist ready
- API documentation updated
- Security testing guide complete
- Production environment prepared
- All documentation reviewed and approved

---

## Execution Order

Recommended implementation sequence:
1. **Group 1: Foundation & Configuration Layer** (Days 1-2) - COMPLETE
   - Critical foundation for all other work
   - Settings validation must be done first
   - Enables fail-fast behavior

2. **Group 2: Core Security Infrastructure** (Days 3-5) - COMPLETE
   - ErrorResponse and correlation_id needed by all layers
   - Exception handling patterns used everywhere
   - Must be in place before auth/authz layers

3. **Group 3: Authentication Security Layer** (Days 6-8) - COMPLETE
   - Token blacklist and logout functionality
   - Depends on Settings and ErrorResponse
   - Must be done before authorization layer

4. **Group 4: Authorization & Access Control Layer** (Days 9-11) - COMPLETE
   - Ownership validation and audit logging
   - Depends on auth layer being secure
   - Critical for data leak prevention

5. **Group 5: API Security Layer** (Days 12-14)
   - Rate limiting, CORS, SQL injection prevention
   - Depends on all previous layers
   - Final security hardening

6. **Group 6: Testing & Quality Assurance** (Days 15-17)
   - Comprehensive testing of all P0 fixes
   - Integration and security testing
   - Manual penetration testing

7. **Group 7: Documentation & Deployment** (Days 18-19)
   - Documentation and deployment prep
   - Production environment setup
   - Final readiness checks

---

## Testing Strategy

### Test Distribution by Group

**Group 1 (Foundation):** 2-8 focused tests (8/8 passing)
- Configuration validation tests
- Startup failure tests
- Settings loading tests

**Group 2 (Security Infrastructure):** 2-8 focused tests (8/8 passing)
- ErrorResponse format tests
- Correlation ID tests
- Exception handling tests

**Group 3 (Authentication):** 2-8 focused tests (8/8 passing)
- Token blacklist tests
- Logout functionality tests
- jti claim tests

**Group 4 (Authorization):** 2-8 focused tests (7/7 written, infrastructure complete)
- Ownership validation tests
- Superuser bypass tests
- Audit logging tests

**Group 5 (API Security):** 2-8 focused tests
- Rate limiting tests
- CORS tests
- SQL injection prevention tests

**Group 6 (Testing):** Maximum 10 additional tests
- Fill critical gaps only
- Integration tests (5-10)
- Security tests (5-10)
- Unit tests (max 10)

**Total Tests:** Approximately 30-60 tests for Phase 1 features

### Test Coverage Goals

- **Overall coverage:** Maintain 92%+ (existing baseline)
- **New code coverage:** 95%+ for all P0 fixes
- **Security-critical code:** 100% coverage
- **Integration coverage:** All P0 workflows covered
- **Security testing:** All attack vectors tested

### Test Types

**Unit Tests (function-level):**
- Settings validation
- Token generation with jti
- Blacklist check logic
- Rate limit calculations
- Ownership validation logic
- Input sanitization
- Error response formatting
- Audit log creation

**Integration Tests (endpoint-level):**
- Full authentication flow with logout
- Rate limiting across requests
- CORS on HTTP requests
- Ownership validation on endpoints
- Audit logging for user journeys
- SQL injection prevention

**Security Tests (penetration):**
- SQL injection attempts
- Authentication bypass attempts
- Authorization bypass attempts
- Rate limit evasion
- CSRF attacks
- Token reuse after logout
- XSS in error messages

**Manual Tests:**
- Full penetration testing
- Security review
- Regression testing
- Performance benchmarking

---

## Success Criteria

### Phase 1 Complete When:

**All 8 P0 Vulnerabilities Fixed:**
- [x] JWT_SECRET from environment (fail-fast if missing)
- [ ] Rate limiting enabled (Redis-backed)
- [x] CORS restricted to whitelisted origins
- [x] Token blacklist for logout
- [ ] SQL injection prevented via parameterized queries
- [x] Conversation ownership validated
- [x] Bare except clauses replaced
- [x] Error responses standardized with correlation_id

**Testing Complete:**
- [ ] 30-60 new tests passing (unit, integration, security)
- [ ] 92%+ test coverage maintained overall
- [ ] 95%+ coverage for new security code
- [ ] All security test scenarios pass
- [ ] Manual penetration testing: zero critical findings

**Audit Logging Active:**
- [x] Audit logs table created with indexes
- [x] All authentication events logged
- [x] All authorization failures logged
- [x] All modification events logged

**Documentation Complete:**
- [x] Environment variables documented
- [ ] Error codes documented
- [ ] Audit log schema documented
- [ ] Rate limiting strategy documented
- [ ] Deployment guide complete

**Deployment Ready:**
- [ ] Zero-downtime deployment verified
- [ ] No database migrations required
- [ ] Rollback procedure tested
- [ ] Production environment prepared
- [ ] Configuration validation works

**Security Validated:**
- [ ] Penetration testing passed (zero critical vulnerabilities)
- [ ] SQL injection tests pass
- [ ] Authentication bypass attempts fail
- [ ] Authorization bypass attempts fail
- [ ] Rate limiting blocks excessive requests
- [ ] CSRF attacks blocked
- [ ] Logged-out tokens rejected

---

## Important Notes

### Constraints

- **Focused testing:** Each group writes 2-8 tests maximum during development
- **Test verification:** Run ONLY newly written tests during development, not entire suite
- **Gap filling:** Testing group adds maximum 10 additional tests if needed
- **Coverage target:** 95%+ for new code, 92%+ overall
- **Zero-downtime:** No database migrations required (user_id exists)
- **Timeline:** 2 weeks maximum (19 working days)

### Test-Driven Approach

Each task group follows this pattern:
1. Start with writing 2-8 focused tests (x.1 sub-task)
2. Implement functionality to make tests pass
3. End with running ONLY those tests (final sub-task)
4. Do NOT run entire test suite during development

Testing group (Group 6) handles:
- Reviewing all tests from Groups 1-5
- Identifying critical gaps
- Adding maximum 10 additional tests
- Running feature-specific tests only
- Manual penetration testing

### Out of Scope

Phase 1 focuses ONLY on 8 P0 vulnerabilities. Explicitly excluded:
- Password complexity requirements (Phase 6)
- 2FA/MFA (Phase 6)
- Account lockout policies (Phase 6)
- Advanced session management (Phase 2/5)
- Complete security headers (Phase 5)
- IP whitelisting (Phase 2/6)
- GDPR compliance automation (Phase 5)
- Sentry error reporting (Phase 5)
- Advanced logging/metrics (Phase 5)

### Performance Requirements

- Rate limiting adds <10ms latency
- Blacklist checks add <5ms latency
- Ownership validation adds <10ms latency
- Audit logging doesn't block requests (async)
- No performance regression on existing endpoints

### Rollback Strategy

If issues detected after deployment:
1. Monitor error logs for 1 hour post-deployment
2. If critical issues: `git revert <commit-hash>`
3. Restart application: `systemctl restart devmatrix-api`
4. Verify health check: `curl /health`
5. Re-deploy when fixed

---

## File Reference

### New Files to Create (5)

1. `/src/config/settings.py` - Pydantic Settings for configuration
2. `/src/observability/audit_logger.py` - Audit logging service
3. `/src/api/responses/error_response.py` - Standardized error responses
4. `/src/api/middleware/correlation_id_middleware.py` - Request correlation
5. `/src/api/middleware/ownership_middleware.py` - Resource ownership validation

### Files to Modify (7)

1. `/src/services/auth_service.py` - JWT secret, jti, blacklist
2. `/src/api/middleware/auth_middleware.py` - Blacklist check
3. `/src/api/middleware/rate_limit_middleware.py` - Enable and enhance
4. `/src/main.py` - Startup validation, CORS, middleware
5. `/src/api/routers/auth.py` - Logout endpoint
6. `/src/api/routers/chat.py` - Ownership decorator
7. `/src/rag/vector_store.py` - Input validation

### Database Changes

1. Create `audit_logs` table (no migration to existing tables)

---

## Absolute File Paths

All file paths in this document are relative to project root. Use absolute paths during implementation:
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/config/settings.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/observability/audit_logger.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/responses/error_response.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/middleware/correlation_id_middleware.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/middleware/ownership_middleware.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/services/auth_service.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/middleware/auth_middleware.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/middleware/rate_limit_middleware.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/main.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/routers/auth.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/routers/chat.py`
- `/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/rag/vector_store.py`
