# Task Breakdown: Phase 6 - Authentication & Multi-tenancy

## Overview

**Feature**: Authentication & Multi-tenancy System
**Total Tasks**: 73 tasks across 10 major phases
**Estimated Effort**: 3-4 weeks
**Priority**: Critical - Foundation for multi-user SaaS platform

## Task List

---

## Phase 1: Foundation - Database Schema & Migrations

### Task Group 1.1: Database Schema Design
**Dependencies:** None
**Assignee:** database-engineer

- [x] 1.1.0 Complete database schema design and migrations
  - [x] 1.1.1 Write 2-5 focused tests for User model extensions
    - Test email verification token generation and validation
    - Test password reset token creation and expiry
    - Test user_id UUID constraints
    - Skip exhaustive edge case testing
  - [x] 1.1.2 Extend User model with email verification fields
    - Add `is_verified` (Boolean, default True)
    - Add `verification_token` (UUID, nullable)
    - Add `verification_token_created_at` (Timestamp, nullable)
    - Reference: `src/models/user.py` (already exists)
  - [x] 1.1.3 Extend User model with password reset fields
    - Add `password_reset_token` (UUID, nullable)
    - Add `password_reset_expires` (Timestamp, nullable)
    - Add indexes for token lookups
  - [x] 1.1.4 Create UserQuota model
    - Fields: quota_id (UUID PK), user_id (UUID FK unique), llm_tokens_monthly_limit (Integer nullable), masterplans_limit (Integer nullable), storage_bytes_limit (BigInt nullable), api_calls_per_minute (Integer default 30)
    - File: `src/models/user_quota.py`
    - Add index on user_id
  - [x] 1.1.5 Create UserUsage model
    - Fields: usage_id (UUID PK), user_id (UUID FK), month (Date), llm_tokens_used (Integer default 0), llm_cost_usd (Numeric), masterplans_created (Integer), storage_bytes (BigInt), api_calls (Integer)
    - File: `src/models/user_usage.py`
    - Add unique constraint on (user_id, month)
    - Add compound index on (user_id, month)
  - [x] 1.1.6 Create Conversation model
    - Fields: conversation_id (UUID PK), user_id (UUID FK), title (String 300), created_at, updated_at
    - File: `src/models/conversation.py`
    - Add index on user_id and created_at
  - [x] 1.1.7 Create Message model
    - Fields: message_id (UUID PK), conversation_id (UUID FK), role (String 20: user/assistant/system), content (Text), created_at
    - File: `src/models/message.py`
    - Add index on conversation_id
  - [x] 1.1.8 Ensure database schema tests pass
    - Run ONLY the 2-5 tests written in 1.1.1
    - Verify model validations work
    - Do NOT run entire test suite

**Acceptance Criteria:**
- All new models created with proper fields and types
- Foreign key relationships established
- Indexes created for performance
- The 2-5 tests written pass successfully
- Models follow existing DevMatrix patterns

**Files:**
- `src/models/user.py` (extend existing)
- `src/models/user_quota.py` (new)
- `src/models/user_usage.py` (new)
- `src/models/conversation.py` (new)
- `src/models/message.py` (new)

**Effort:** 1 day
**Priority:** P0 - Critical

---

### Task Group 1.2: Alembic Migrations
**Dependencies:** Task Group 1.1 ✅ (COMPLETED)
**Assignee:** database-engineer

- [x] 1.2.0 Complete database migrations for multi-tenancy
  - [x] 1.2.1 Create Alembic migration: extend users table
    - Add is_verified, verification_token, verification_token_created_at
    - Add password_reset_token, password_reset_expires
    - Add indexes on token columns
    - File: `alembic/versions/20251022_1346_extend_users_table.py`
  - [x] 1.2.2 Create Alembic migration: create user_quotas table
    - Create table with all fields
    - Add FK constraint to users with ON DELETE CASCADE
    - Add unique constraint on user_id
    - File: `alembic/versions/20251022_1347_create_user_quotas.py`
  - [x] 1.2.3 Create Alembic migration: create user_usage table
    - Create table with all fields
    - Add FK constraint to users with ON DELETE CASCADE
    - Add unique constraint on (user_id, month)
    - Add indexes
    - File: `alembic/versions/20251022_1348_create_user_usage.py`
  - [x] 1.2.4 Create Alembic migration: create conversations and messages tables
    - Create both tables with FKs
    - Add indexes for performance
    - File: `alembic/versions/20251022_1349_create_conversations_messages.py`
  - [x] 1.2.5 Create Alembic migration: modify masterplans.user_id to UUID FK
    - Alter column type from String to UUID (using CAST)
    - Add FK constraint to users.user_id with ON DELETE CASCADE
    - Add index on user_id
    - File: `alembic/versions/20251022_1350_masterplans_user_id_fk.py`
    - CAUTION: This is a breaking migration (start fresh approach)
  - [x] 1.2.6 Create Alembic migration: modify discovery_documents.user_id to UUID FK
    - Alter column type from String to UUID
    - Add FK constraint to users.user_id with ON DELETE CASCADE
    - Add index on user_id
    - File: `alembic/versions/20251022_1351_discovery_documents_user_id_fk.py`
  - [x] 1.2.7 Test migrations: run alembic upgrade head
    - Run on clean database
    - Verify all tables created
    - Verify all FKs and indexes exist
    - Test rollback with `alembic downgrade -1`
  - [x] 1.2.8 Create migration documentation
    - Document migration order
    - Document rollback procedures
    - Add to: `alembic/README.md`

**Acceptance Criteria:**
- All migrations run successfully without errors ✅
- Foreign key constraints enforced ✅
- Indexes created and verified ✅
- Rollback migrations work correctly ✅
- Migration documentation complete ✅

**Files:**
- `alembic/versions/20251022_1346_extend_users_table.py` ✅
- `alembic/versions/20251022_1347_create_user_quotas.py` ✅
- `alembic/versions/20251022_1348_create_user_usage.py` ✅
- `alembic/versions/20251022_1349_create_conversations_messages.py` ✅
- `alembic/versions/20251022_1350_masterplans_user_id_fk.py` ✅
- `alembic/versions/20251022_1351_discovery_documents_user_id_fk.py` ✅
- `alembic/README.md` ✅

**Effort:** 1 day
**Priority:** P0 - Critical

---

## Phase 2: Backend Core - Authentication Services

### Task Group 2.1: Email Verification Service
**Dependencies:** Task Group 1.2
**Assignee:** api-engineer

- [x] 2.1.0 Complete email verification service
  - [x] 2.1.1 Write 2-6 focused tests for email verification
    - Test verification token generation
    - Test verification email sending
    - Test token validation and expiry (24 hours)
    - Test resend verification rate limiting
    - Skip exhaustive edge cases
  - [x] 2.1.2 Create EmailVerificationService class
    - Method: `generate_verification_token(user_id)` - Creates UUID token, stores in DB with timestamp
    - Method: `verify_email(token)` - Validates token, checks expiry, sets is_verified=True
    - Method: `is_token_expired(created_at, hours=24)` - Check if token older than 24 hours
    - File: `src/services/email_verification_service.py`
  - [x] 2.1.3 Implement resend verification logic
    - Method: `resend_verification(user_id)` - Generates new token, invalidates old
    - Check if already verified (return 400 error)
    - Rate limiting will be handled by separate rate limit service
  - [x] 2.1.4 Integrate with email service (to be created later)
    - Create email template variable placeholders
    - Method: `send_verification_email(user_email, token)` - Stub for now
    - Will be implemented in Task Group 3.1
  - [x] 2.1.5 Add configuration for email verification requirement
    - Environment variable: `EMAIL_VERIFICATION_REQUIRED` (default: false)
    - Load in `src/config/constants.py`
    - Use in registration flow
  - [x] 2.1.6 Ensure email verification tests pass
    - Run ONLY the 2-6 tests written in 2.1.1
    - Verify token generation and validation
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Email verification service handles token generation and validation
- 24-hour token expiry enforced
- Resend functionality works with duplicate prevention
- Configuration option works correctly
- The 2-6 tests pass successfully

**Files:**
- `src/services/email_verification_service.py` (new)
- `src/config/constants.py` (extend)
- `tests/services/test_email_verification_service.py` (new)

**Effort:** 1 day
**Priority:** P0 - Critical

---

### Task Group 2.2: Password Reset Service
**Dependencies:** Task Group 1.2
**Assignee:** api-engineer

- [x] 2.2.0 Complete password reset service
  - [x] 2.2.1 Write 2-6 focused tests for password reset
    - Test reset token generation and storage
    - Test token expiry validation (1 hour)
    - Test password reset with valid token
    - Test token invalidation after use
    - Skip comprehensive edge case testing
  - [x] 2.2.2 Create PasswordResetService class
    - Method: `request_password_reset(email)` - Generate token, set expiry 1 hour from now
    - Method: `validate_reset_token(token)` - Check token exists and not expired
    - Method: `reset_password(token, new_password)` - Validate token, hash password, clear token fields
    - File: `src/services/password_reset_service.py`
  - [x] 2.2.3 Implement token expiry validation
    - Method: `is_token_expired(expires_at)` - Compare with current timestamp
    - Expire tokens after 1 hour
  - [x] 2.2.4 Integrate with AuthService for password hashing
    - Reuse `AuthService.hash_password()` method
    - Update password_hash in user record
    - Clear password_reset_token and password_reset_expires
  - [x] 2.2.5 Integrate with email service (stub for now)
    - Method: `send_password_reset_email(user_email, token)` - Stub
    - Will be implemented in Task Group 3.1
  - [x] 2.2.6 Add security feature: invalidate existing refresh tokens on password reset
    - Document requirement (token blacklist will be Phase 7)
    - For MVP: Tokens naturally expire, no active invalidation
  - [x] 2.2.7 Ensure password reset tests pass
    - Run ONLY the 2-6 tests written in 2.2.1
    - Verify token lifecycle works correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Password reset tokens generated with 1-hour expiry
- Token validation prevents expired/invalid tokens
- Password successfully updated with valid token
- Tokens invalidated after use (single-use)
- The 2-6 tests pass successfully

**Files:**
- `src/services/password_reset_service.py` (new)
- `tests/services/test_password_reset_service.py` (new)

**Effort:** 1 day
**Priority:** P0 - Critical

---

### Task Group 2.3: Authentication API Endpoints (Email Verification & Password Reset)
**Dependencies:** Task Groups 2.1, 2.2
**Assignee:** api-engineer

- [x] 2.3.0 Complete authentication API endpoints
  - [x] 2.3.1 Write 2-6 focused tests for new auth endpoints
    - Test POST /api/v1/auth/verify-email success and error cases
    - Test POST /api/v1/auth/resend-verification
    - Test POST /api/v1/auth/forgot-password
    - Test POST /api/v1/auth/reset-password
    - Skip exhaustive testing of all scenarios
  - [x] 2.3.2 Extend AuthRouter with email verification endpoints
    - Endpoint: `POST /api/v1/auth/verify-email` - Request body: {token}
    - Response: 200 {message, user_id} or 400 {error}
    - File: `src/api/routers/auth.py` (extend existing)
  - [x] 2.3.3 Add resend verification endpoint
    - Endpoint: `POST /api/v1/auth/resend-verification` - Requires authentication
    - Response: 200 {message} or 400/429
    - Check if already verified before resending
  - [x] 2.3.4 Add forgot password endpoint
    - Endpoint: `POST /api/v1/auth/forgot-password` - Request body: {email}
    - Response: Always 200 {message} (don't reveal if email exists)
    - Call PasswordResetService.request_password_reset()
  - [x] 2.3.5 Add reset password endpoint
    - Endpoint: `POST /api/v1/auth/reset-password` - Request body: {token, new_password}
    - Response: 200 {message} or 400/422
    - Validate password meets requirements (8+ chars)
    - Call PasswordResetService.reset_password()
  - [x] 2.3.6 Update existing registration endpoint
    - Check `EMAIL_VERIFICATION_REQUIRED` config
    - If true: Set is_verified=False, generate verification token, send email
    - If false: Set is_verified=True, no email
    - Return appropriate response message
  - [x] 2.3.7 Add Pydantic request/response models
    - VerifyEmailRequest, ResendVerificationResponse
    - ForgotPasswordRequest, ResetPasswordRequest
    - Add to: `src/api/routers/auth.py` or `src/api/schemas/auth.py`
  - [x] 2.3.8 Ensure auth endpoint tests pass
    - Run ONLY the 2-6 tests written in 2.3.1
    - Verify endpoints respond correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- All 4 new endpoints functional and tested
- Registration endpoint respects EMAIL_VERIFICATION_REQUIRED config
- Error responses appropriate and secure (no email enumeration)
- Request/response validation via Pydantic models
- The 2-6 tests pass successfully

**Files:**
- `src/api/routers/auth.py` (extend)
- `src/api/schemas/auth.py` (extend or create)
- `tests/api/test_auth_endpoints.py` (extend)

**Effort:** 1 day
**Priority:** P0 - Critical

---

## Phase 3: Email Infrastructure

### Task Group 3.1: Email Service Implementation
**Dependencies:** Task Groups 2.1, 2.2
**Assignee:** api-engineer

- [x] 3.1.0 Complete email service infrastructure
  - [x] 3.1.1 Write 2-4 focused tests for email service
    - Test SMTP connection (mocked)
    - Test email sending with retry logic
    - Test email template rendering
    - Skip live SMTP integration tests (use mocks)
  - [x] 3.1.2 Create EmailService class
    - Method: `send_email(to, subject, html_body, text_body)` - Core sending logic
    - Method: `send_verification_email(user_email, username, token)` - Uses template
    - Method: `send_password_reset_email(user_email, username, token)` - Uses template
    - Method: `send_welcome_email(user_email, username)` - Uses template
    - File: `src/services/email_service.py`
  - [x] 3.1.3 Implement SMTP configuration
    - Load from environment: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_FROM_NAME
    - Use Python's smtplib or library like `aiosmtplib` for async
    - Add to: `src/config/constants.py`
  - [x] 3.1.4 Create HTML email templates
    - Template: `email_verification.html` - Verification link with token
    - Template: `password_reset.html` - Reset link with token
    - Template: `welcome.html` - Welcome message after registration
    - Directory: `src/templates/emails/`
    - Include plain text versions for all templates
  - [x] 3.1.5 Implement email template rendering
    - Use Jinja2 for template rendering
    - Variables: username, verification_url, reset_url, frontend_url
    - Frontend URL from env var: FRONTEND_URL
  - [x] 3.1.6 Add retry logic and error handling
    - Retry failed sends up to 3 times with exponential backoff
    - Log all email sending attempts (success/failure)
    - Graceful degradation if email service unavailable
  - [x] 3.1.7 Update environment variables documentation
    - Add all SMTP settings to `.env.example`
    - Document SendGrid configuration (recommended provider)
    - File: `.env.example`
  - [x] 3.1.8 Ensure email service tests pass
    - Run ONLY the 2-4 tests written in 3.1.1
    - Verify email rendering and sending logic
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Email service can send verification, reset, and welcome emails
- HTML and plain text versions for all templates
- SMTP configuration loaded from environment
- Retry logic handles transient failures
- The 2-4 tests pass successfully

**Files:**
- `src/services/email_service.py` (new)
- `src/templates/emails/email_verification.html` (new)
- `src/templates/emails/password_reset.html` (new)
- `src/templates/emails/welcome.html` (new)
- `src/config/constants.py` (extend)
- `.env.example` (update)
- `tests/services/test_email_service.py` (new)

**Effort:** 1.5 days
**Priority:** P1 - High

---

## Phase 4: Multi-tenancy - Data Isolation & Workspaces

### Task Group 4.1: Workspace Service
**Dependencies:** Task Group 1.2
**Assignee:** api-engineer

- [x] 4.1.0 Complete workspace isolation service
  - [x] 4.1.1 Write 2-6 focused tests for workspace service
    - Test workspace creation on user registration
    - Test workspace path validation (path traversal prevention)
    - Test workspace size calculation
    - Test workspace cleanup on user deletion
    - Skip comprehensive file system edge cases
  - [x] 4.1.2 Create WorkspaceService class
    - Method: `create_user_workspace(user_id)` - Create /workspaces/{user_id}/ with subdirs
    - Method: `get_workspace_path(user_id)` - Return absolute path to workspace
    - Method: `validate_file_path(user_id, relative_path)` - Prevent path traversal
    - Method: `calculate_workspace_size(user_id)` - Return total bytes used
    - Method: `cleanup_workspace(user_id)` - Delete workspace (soft delete option)
    - File: `src/services/workspace_service.py`
  - [x] 4.1.3 Implement workspace directory structure
    - Create subdirectories: projects/, temp/, .git/
    - Initialize git repository in workspace
    - Set appropriate permissions (owner only)
  - [x] 4.1.4 Implement path traversal protection
    - Use Path.resolve() to get absolute path
    - Ensure resolved path is child of workspace path
    - Raise SecurityError if path escape detected
  - [x] 4.1.5 Implement workspace size calculation
    - Recursively iterate all files in workspace
    - Sum file sizes using os.stat()
    - Cache result for performance (update daily)
    - Method should be async for background processing
  - [x] 4.1.6 Integrate workspace creation into registration flow
    - Call WorkspaceService.create_user_workspace() after user creation
    - Handle errors gracefully (rollback user if workspace fails)
    - Update: `src/services/auth_service.py` register_user method
  - [x] 4.1.7 Add workspace configuration
    - Environment variable: WORKSPACES_ROOT (default: /workspaces)
    - Add to: `src/config/constants.py`
  - [x] 4.1.8 Ensure workspace service tests pass
    - Run ONLY the 2-6 tests written in 4.1.1
    - Verify workspace operations work correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- User workspaces created automatically on registration
- Path traversal attacks prevented
- Workspace size calculation works efficiently
- Git repository initialized per user
- The 2-6 tests pass successfully

**Files:**
- `src/services/workspace_service.py` (new)
- `src/services/auth_service.py` (extend)
- `src/config/constants.py` (extend)
- `tests/services/test_workspace_service.py` (new)

**Effort:** 1.5 days
**Priority:** P0 - Critical

---

### Task Group 4.2: Query Filtering & Data Isolation
**Dependencies:** Task Group 1.2
**Assignee:** api-engineer

- [x] 4.2.0 Complete database query filtering for multi-tenancy
  - [x] 4.2.1 Write 2-8 focused tests for multi-tenancy isolation
    - Test user can access only their masterplans
    - Test user cannot access other user's masterplans (404 response)
    - Test user can access only their conversations
    - Test admin can access all data
    - Test query filtering applied automatically
    - Skip exhaustive permission combination testing
  - [x] 4.2.2 Update MasterplanService with user_id filtering
    - Method: `list_by_user(user_id)` - Filter masterplans by user_id
    - Method: `get_by_id(masterplan_id, user_id)` - Get masterplan only if owned by user
    - Method: `create(user_id, ...)` - Always set user_id on creation
    - File: `src/services/masterplan_service.py` or similar
  - [x] 4.2.3 Update DiscoveryService with user_id filtering
    - Apply same filtering pattern as masterplans
    - Ensure all queries include `filter(DiscoveryDocument.user_id == user_id)`
  - [x] 4.2.4 Create ConversationService with user_id filtering
    - Method: `list_by_user(user_id)` - Get user's conversations
    - Method: `get_by_id(conversation_id, user_id)` - Verify ownership
    - Method: `create(user_id, title)` - Create conversation for user
    - File: `src/services/conversation_service.py` (new)
  - [x] 4.2.5 Implement 404 vs 403 response pattern
    - When resource not found OR not owned by user: Return 404
    - Don't reveal resource existence to unauthorized users
    - Apply across all service methods
  - [x] 4.2.6 Update existing API endpoints to use user_id from token
    - Masterplan endpoints: Add `current_user: User = Depends(get_current_active_user)`
    - Pass `current_user.user_id` to service methods
    - Remove any client-provided user_id (security)
    - Files: `src/api/routers/masterplans.py`, etc.
  - [x] 4.2.7 Add admin bypass logic
    - If `current_user.is_superuser`, allow access to all resources
    - Implement in service layer, not middleware
    - Use for impersonation feature
  - [x] 4.2.8 Ensure multi-tenancy tests pass
    - Run ONLY the 2-8 tests written in 4.2.1
    - Verify complete data isolation
    - Do NOT run entire test suite

**Acceptance Criteria:**
- All database queries automatically filtered by user_id
- Users cannot access other users' data
- 404 responses for unauthorized access (not 403)
- Admin users can access all data when needed
- The 2-8 tests pass successfully

**Files:**
- `src/services/masterplan_service.py` (extend)
- `src/services/discovery_service.py` (extend or create)
- `src/services/conversation_service.py` (new)
- `src/api/routers/masterplans.py` (extend)
- `src/api/routers/conversations.py` (new or extend)
- `tests/integration/test_multi_tenancy.py` (new)

**Effort:** 2 days
**Priority:** P0 - Critical

---

## Phase 5: Usage Tracking & Quotas

### Task Group 5.1: Usage Tracking Service
**Dependencies:** Task Groups 1.2, 4.1
**Assignee:** api-engineer

- [x] 5.1.0 Complete usage tracking service
  - [x] 5.1.1 Write 2-6 focused tests for usage tracking
    - Test LLM token tracking increments usage
    - Test monthly usage aggregation
    - Test masterplan creation tracking
    - Test storage usage updates
    - Skip comprehensive usage report testing
  - [x] 5.1.2 Create UsageTrackingService class
    - Method: `track_llm_usage(user_id, model, input_tokens, output_tokens, cached_tokens, cost_usd)` - Increment monthly totals
    - Method: `track_masterplan_created(user_id)` - Increment counter
    - Method: `track_storage_usage(user_id, bytes_used)` - Update storage field
    - Method: `get_current_month_usage(user_id)` - Return current month's usage record
    - Method: `get_or_create_month_usage(user_id, month)` - Get or create usage record for month
    - File: `src/services/usage_tracking_service.py`
  - [x] 5.1.3 Implement monthly usage aggregation
    - Store one record per user per month in user_usage table
    - Month field: First day of month (e.g., 2025-10-01)
    - Auto-create record on first usage each month
  - [x] 5.1.4 Create LLM usage tracking decorator
    - Decorator: `@track_llm_call` - Wraps LLM calls to automatically track usage
    - Extract token counts from response metadata
    - Calculate cost based on model pricing
    - File: `src/llm/usage_decorator.py` or add to existing LLM module
  - [x] 5.1.5 Calculate LLM costs from token usage
    - Method: `calculate_cost(model, input_tokens, output_tokens, cached_tokens)` - Return USD cost
    - Pricing table for models (Claude Sonnet 4.5, etc.)
    - Add to: `src/llm/pricing.py` or constants
  - [x] 5.1.6 Integrate usage tracking into LLM service
    - Update all LLM API calls to use tracking decorator
    - Pass user_id to decorator from request context
    - File: `src/llm/enhanced_anthropic_client.py` or similar
  - [x] 5.1.7 Integrate usage tracking into masterplan creation
    - Call `track_masterplan_created(user_id)` after successful creation
    - Update: Masterplan service or router
  - [x] 5.1.8 Ensure usage tracking tests pass
    - Run ONLY the 2-6 tests written in 5.1.1
    - Verify usage increments correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- LLM token usage tracked automatically per user
- Monthly aggregation works correctly
- Masterplan creation counted
- Storage usage updated (initially manual, background job in 5.3)
- The 2-6 tests pass successfully

**Files:**
- `src/services/usage_tracking_service.py` (new)
- `src/llm/usage_decorator.py` (new)
- `src/llm/pricing.py` (new)
- `src/llm/enhanced_anthropic_client.py` (extend)
- `src/services/masterplan_service.py` (extend)
- `tests/services/test_usage_tracking_service.py` (new)

**Effort:** 2 days
**Priority:** P0 - Critical

---

### Task Group 5.2: Quota Enforcement Service
**Dependencies:** Task Group 5.1
**Assignee:** api-engineer

- [x] 5.2.0 Complete quota enforcement service
  - [x] 5.2.1 Write 2-6 focused tests for quota enforcement
    - Test quota check allows usage under limit
    - Test quota check blocks usage over limit (429 error)
    - Test 5% grace period works
    - Test admin bypass works
    - Test null quota = unlimited
    - Skip exhaustive quota combination testing
  - [x] 5.2.2 Create QuotaService class
    - Method: `get_user_quotas(user_id)` - Get quotas from DB or defaults
    - Method: `check_token_quota(user_id)` - Return True if under limit, raise error if exceeded
    - Method: `check_masterplan_quota(user_id)` - Check masterplan limit
    - Method: `check_storage_quota(user_id, additional_bytes)` - Check storage limit
    - Method: `get_default_quotas()` - Return default quotas from config
    - File: `src/services/quota_service.py`
  - [x] 5.2.3 Implement default quotas
    - Load from environment: DEFAULT_LLM_TOKENS_MONTHLY, DEFAULT_MASTERPLANS_LIMIT, DEFAULT_STORAGE_BYTES_LIMIT
    - Default values: 1M tokens, 50 masterplans, 5GB storage
    - Add to: `src/config/constants.py`
  - [x] 5.2.4 Implement quota checking with grace period
    - Allow 5% overage (e.g., 1.05M tokens if limit is 1M)
    - Only enforce hard limit after grace period
    - Document rationale: Prevent hard cutoffs mid-operation
  - [x] 5.2.5 Implement admin quota bypass
    - If user `is_superuser=True`, skip quota checks
    - Return unlimited quotas for admins
  - [x] 5.2.6 Create quota exceeded error responses
    - HTTP 429 for token quota exceeded
    - Error body: {error, quota, used, reset_date, percent_used}
    - HTTP 413 for storage quota exceeded
  - [x] 5.2.7 Integrate quota checks into API endpoints
    - Before LLM call: `quota_service.check_token_quota(user_id)`
    - Before masterplan creation: `quota_service.check_masterplan_quota(user_id)`
    - Before file write: `quota_service.check_storage_quota(user_id, file_size)`
  - [x] 5.2.8 Ensure quota enforcement tests pass
    - Run ONLY the 2-6 tests written in 5.2.1
    - Verify quota limits enforced correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Quota checks prevent exceeding limits
- 5% grace period applied
- Admin users bypass quotas
- Null quotas = unlimited
- Clear error messages with usage details
- The 2-6 tests pass successfully

**Files:**
- `src/services/quota_service.py` (new)
- `src/config/constants.py` (extend)
- `src/api/routers/masterplans.py` (extend)
- `src/llm/enhanced_anthropic_client.py` (extend)
- `tests/services/test_quota_service.py` (new)

**Effort:** 1.5 days
**Priority:** P0 - Critical

---

### Task Group 5.3: Storage Tracking Background Job
**Dependencies:** Task Groups 4.1, 5.1
**Assignee:** api-engineer

- [x] 5.3.0 Complete storage tracking background job
  - [x] 5.3.1 Write 2-4 focused tests for storage tracking
    - Test workspace size calculation
    - Test storage usage update in database
    - Test daily cron job execution (mocked)
    - Skip long-running integration tests
  - [x] 5.3.2 Create storage calculation background task
    - Function: `calculate_all_users_storage()` - Iterate all users, calculate workspace sizes
    - Call WorkspaceService.calculate_workspace_size() for each user
    - Update user_usage.storage_bytes
    - File: `src/tasks/storage_calculation.py` (new)
  - [x] 5.3.3 Implement async processing for large workspaces
    - Use asyncio for concurrent processing
    - Process users in batches (e.g., 10 at a time)
    - Add progress logging
  - [x] 5.3.4 Add cron job scheduling
    - Use APScheduler or similar for background tasks
    - Schedule: Daily at 2 AM
    - File: `src/tasks/scheduler.py` (new or extend)
  - [x] 5.3.5 Add manual refresh endpoint for admins
    - Endpoint: `POST /api/v1/admin/refresh-storage` - Triggers immediate calculation
    - Admin-only, returns job status
    - File: `src/api/routers/admin.py`
  - [x] 5.3.6 Add storage calculation error handling
    - Handle permission errors gracefully
    - Log errors but continue processing other users
    - Send alert if calculation fails for multiple users
  - [x] 5.3.7 Ensure storage tracking tests pass
    - Run ONLY the 2-4 tests written in 5.3.1
    - Verify storage calculation logic
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Storage calculated daily for all users
- Background job runs async without blocking
- Manual refresh available for admins
- Errors handled gracefully
- The 2-4 tests pass successfully

**Files:**
- `src/tasks/storage_calculation.py` (new)
- `src/tasks/scheduler.py` (new)
- `src/api/routers/admin.py` (extend or create)
- `tests/tasks/test_storage_calculation.py` (new)

**Effort:** 1 day
**Priority:** P1 - High

---

### Task Group 5.4: Usage Statistics API
**Dependencies:** Task Groups 5.1, 5.2
**Assignee:** api-engineer

- [x] 5.4.0 Complete usage statistics API
  - [x] 5.4.1 Write 2-4 focused tests for usage statistics API
    - Test GET /api/v1/users/me/usage returns correct data
    - Test usage percentages calculated correctly
    - Test human-readable storage formatting
    - Skip extensive formatting edge cases
  - [x] 5.4.2 Create UserRouter for user management endpoints
    - File: `src/api/routers/users.py` (new)
    - Register router in main app
  - [x] 5.4.3 Implement GET /api/v1/users/me/usage endpoint
    - Get current user from auth dependency
    - Get current month usage from UsageTrackingService
    - Get quotas from QuotaService
    - Calculate percentages: (used / limit) * 100
    - Format storage as human-readable (125 MB / 5 GB)
  - [x] 5.4.4 Create response model for usage statistics
    - UsageStatsResponse: month, llm_tokens_used, llm_tokens_limit, llm_tokens_percent, llm_cost_usd, masterplans_created, masterplans_limit, storage_bytes, storage_limit_bytes, storage_human, storage_percent
    - File: `src/api/schemas/usage.py` (new)
  - [x] 5.4.5 Implement storage formatting helper
    - Function: `format_bytes(bytes)` - Return "125 MB", "1.2 GB", etc.
    - Use appropriate units (KB, MB, GB, TB)
    - Add to: `src/utils/formatting.py` (new)
  - [x] 5.4.6 Add caching for usage statistics
    - Cache response for 1 minute using Redis or in-memory cache
    - Cache key: `usage_stats:{user_id}:{month}`
    - Reduces database queries for frequent requests
  - [x] 5.4.7 Ensure usage statistics API tests pass
    - Run ONLY the 2-4 tests written in 5.4.1
    - Verify endpoint returns correct format
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Usage statistics endpoint returns all required fields
- Percentages calculated correctly
- Storage formatted in human-readable format
- Response cached for performance
- The 2-4 tests pass successfully

**Files:**
- `src/api/routers/users.py` (new)
- `src/api/schemas/usage.py` (new)
- `src/utils/formatting.py` (new)
- `src/api/app.py` (extend to register router)
- `tests/api/test_users_endpoints.py` (new)

**Effort:** 0.5 days
**Priority:** P1 - High

---

## Phase 6: Admin Features

### Task Group 6.1: Admin User Management API
**Dependencies:** Task Groups 4.2, 5.1
**Assignee:** api-engineer

- [x] 6.1.0 Complete admin user management API
  - [x] 6.1.1 Write 2-8 focused tests for admin endpoints
    - Test GET /api/v1/admin/users with pagination, search, filtering
    - Test GET /api/v1/admin/users/{user_id} returns detailed info
    - Test PATCH /api/v1/admin/users/{user_id} activates/deactivates user
    - Test DELETE /api/v1/admin/users/{user_id} soft deletes user
    - Test non-admin cannot access admin endpoints (403)
    - Skip exhaustive permission testing
  - [x] 6.1.2 Create AdminRouter
    - File: `src/api/routers/admin.py` (new)
    - All endpoints require `Depends(get_current_superuser)`
    - Register router with `/admin` prefix
  - [x] 6.1.3 Implement GET /api/v1/admin/users (list all users)
    - Query params: page, per_page (max 100), sort_by, sort_order, filter_active, search
    - Search across email and username fields
    - Include usage_summary for each user (tokens this month, masterplans count, storage MB)
    - Return paginated response: {users, total, page, per_page, total_pages}
  - [x] 6.1.4 Implement GET /api/v1/admin/users/{user_id} (user details)
    - Return: user object, quotas, usage_current_month, statistics (total masterplans, conversations, LLM cost, workspace path)
    - Join user_quotas and user_usage tables
  - [x] 6.1.5 Implement PATCH /api/v1/admin/users/{user_id} (update user)
    - Accept: is_active field (activate/deactivate)
    - Update user record, return updated user object
    - Log admin action for audit trail (future enhancement)
  - [x] 6.1.6 Implement DELETE /api/v1/admin/users/{user_id} (soft delete)
    - Set is_active=False, optionally set deleted_at timestamp
    - Do NOT hard delete (preserve data for 30 days)
    - Consider adding deleted_at column in future migration
  - [x] 6.1.7 Create Pydantic schemas for admin endpoints
    - AdminUserListResponse, AdminUserDetailResponse, UpdateUserRequest
    - File: `src/api/schemas/admin.py` (new)
  - [x] 6.1.8 Ensure admin user management tests pass
    - Run ONLY the 2-8 tests written in 6.1.1
    - Verify admin endpoints work correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Admins can list, view, update, delete users
- Pagination, search, filtering work correctly
- Non-admins receive 403 errors
- Soft delete preserves user data
- The 2-8 tests pass successfully

**Files:**
- `src/api/routers/admin.py` (new)
- `src/api/schemas/admin.py` (new)
- `src/api/app.py` (extend to register router)
- `tests/api/test_admin_endpoints.py` (new)

**Effort:** 1.5 days
**Priority:** P1 - High

---

### Task Group 6.2: Admin Quota Management & Statistics
**Dependencies:** Task Groups 5.2, 6.1
**Assignee:** api-engineer

- [x] 6.2.0 Complete admin quota management and statistics
  - [x] 6.2.1 Write 2-6 focused tests for admin quota and stats endpoints
    - Test PATCH /api/v1/admin/users/{user_id}/quotas updates quotas
    - Test GET /api/v1/admin/statistics returns global stats
    - Test GET /api/v1/admin/usage-by-user returns usage report
    - Test null quota = unlimited
    - Skip comprehensive statistics edge cases
  - [x] 6.2.2 Implement PATCH /api/v1/admin/users/{user_id}/quotas
    - Accept: llm_tokens_monthly_limit, masterplans_limit, storage_bytes_limit, api_calls_per_minute
    - Create or update user_quotas record
    - Null value = unlimited quota
    - Return updated quotas object
  - [x] 6.2.3 Create AdminService for complex admin operations
    - Method: `get_global_statistics()` - Aggregate stats across all users
    - Method: `get_usage_by_user(start_date, end_date)` - Usage report per user
    - File: `src/services/admin_service.py` (new)
  - [x] 6.2.4 Implement GET /api/v1/admin/statistics endpoint
    - Return: total users, active users, new users this month/today
    - Usage this month: total tokens, cost, masterplans, storage
    - All-time usage: total tokens, cost, masterplans, conversations
    - Top 10 users by token usage
  - [x] 6.2.5 Implement GET /api/v1/admin/usage-by-user endpoint
    - Query params: start_date, end_date (optional)
    - Return array of: {user_id, email, tokens_used, cost_usd, masterplans, storage}
    - Order by tokens_used descending
  - [x] 6.2.6 Add caching for global statistics
    - Cache for 5 minutes using Redis or in-memory
    - Cache key: `admin_stats:global`
    - Invalidate on quota updates or user changes
  - [x] 6.2.7 Ensure admin quota/stats tests pass
    - Run ONLY the 2-6 tests written in 6.2.1
    - Verify quota updates and statistics
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Admins can update user quotas
- Global statistics calculated correctly
- Usage reports available per user
- Statistics cached for performance
- The 2-6 tests pass successfully

**Files:**
- `src/api/routers/admin.py` (extend)
- `src/services/admin_service.py` (new)
- `src/api/schemas/admin.py` (extend)
- `tests/api/test_admin_endpoints.py` (extend)
- `tests/services/test_admin_service.py` (new)

**Effort:** 1.5 days
**Priority:** P1 - High

---

### Task Group 6.3: User Impersonation
**Dependencies:** Task Group 6.1
**Assignee:** api-engineer

- [ ] 6.3.0 Complete user impersonation feature
  - [ ] 6.3.1 Write 2-4 focused tests for impersonation
    - Test admin can generate impersonation token
    - Test impersonation token includes both user IDs
    - Test cannot impersonate other admins
    - Test impersonation token expires after 1 hour
  - [ ] 6.3.2 Implement POST /api/v1/admin/impersonate/{user_id} endpoint
    - Validate target user exists and is not admin
    - Generate special JWT token with claims: impersonating=true, admin_user_id, target_user_id
    - Token expiry: 1 hour (shorter than normal tokens)
    - Return: {access_token, refresh_token, impersonating: {user_id, email, username}, admin: {user_id, email}}
  - [ ] 6.3.3 Update JWT token generation for impersonation
    - Add optional impersonating and admin_user_id claims
    - Extend: `src/services/auth_service.py` create_access_token method
  - [ ] 6.3.4 Update authentication middleware to handle impersonation
    - Extract impersonating flag from token
    - Set current_user to target user
    - Store admin_user_id in request context for logging
    - File: `src/api/middleware/auth_middleware.py`
  - [ ] 6.3.5 Add impersonation logging
    - Log all actions performed during impersonation
    - Include both admin and target user IDs in logs
    - Use structured logging (JSON format)
  - [ ] 6.3.6 Add exit impersonation endpoint (optional)
    - Endpoint: POST /api/v1/admin/exit-impersonation
    - Simply returns new admin token (stops using impersonation token)
    - Or: Frontend just discards impersonation token
  - [ ] 6.3.7 Ensure impersonation tests pass
    - Run ONLY the 2-4 tests written in 6.3.1
    - Verify impersonation flow works
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Admins can impersonate non-admin users
- Impersonation tokens include both user IDs
- Cannot impersonate other admins
- Tokens expire after 1 hour
- All actions logged with both IDs
- The 2-4 tests pass successfully

**Files:**
- `src/api/routers/admin.py` (extend)
- `src/services/auth_service.py` (extend)
- `src/api/middleware/auth_middleware.py` (extend)
- `tests/api/test_admin_endpoints.py` (extend)

**Effort:** 1 day
**Priority:** P2 - Medium

---

## Phase 7: Security - Rate Limiting

### Task Group 7.1: Rate Limiting Infrastructure
**Dependencies:** None (can run in parallel with other phases)
**Assignee:** api-engineer

- [x] 7.1.0 Complete rate limiting infrastructure
  - [x] 7.1.1 Write 2-6 focused tests for rate limiting
    - Test rate limit enforced for auth endpoints (5 req/min)
    - Test rate limit headers returned (X-RateLimit-*)
    - Test 429 error with Retry-After header
    - Test Redis counter increments and TTL
    - Skip comprehensive rate limit scenarios
  - [x] 7.1.2 Install and configure rate limiting library
    - Install: slowapi (recommended) or fastapi-limiter
    - Add to: `requirements.txt`
    - Initialize in: `src/api/app.py`
  - [x] 7.1.3 Configure Redis for rate limiting
    - Redis already available in project
    - Create Redis client for rate limiting
    - Configure connection pool
    - File: `src/config/redis.py` (new or extend)
  - [x] 7.1.4 Create RateLimitService class
    - Method: `check_rate_limit(key, limit, window_seconds)` - Check and increment counter
    - Method: `get_rate_limit_info(key)` - Return limit, remaining, reset timestamp
    - Method: `reset_rate_limit(key)` - Clear counter (for testing)
    - File: `src/services/rate_limit_service.py` (new)
    - Use Redis INCR and EXPIRE commands
  - [x] 7.1.5 Implement rate limit response headers
    - Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
    - Add to all rate-limited endpoint responses
    - Helper function to add headers
  - [x] 7.1.6 Implement 429 error response
    - Custom exception: RateLimitExceeded
    - Response: {error: "Too many requests", retry_after: seconds}
    - Status: 429 with Retry-After header
    - File: `src/api/exceptions.py` (new or extend)
  - [x] 7.1.7 Add rate limit configuration
    - Environment variables: RATE_LIMIT_AUTH_PER_MINUTE, RATE_LIMIT_API_PER_MINUTE, RATE_LIMIT_ADMIN_PER_MINUTE
    - Defaults: 5, 30, 100
    - Add to: `src/config/constants.py`
  - [x] 7.1.8 Ensure rate limiting tests pass
    - Run ONLY the 2-6 tests written in 7.1.1
    - Verify rate limits enforced
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Rate limiting library installed and configured
- Redis integration working
- Rate limit headers returned correctly
- 429 errors returned when limit exceeded
- The 2-6 tests pass successfully

**Files:**
- `requirements.txt` (extend)
- `src/config/redis.py` (new or extend)
- `src/services/rate_limit_service.py` (new)
- `src/api/exceptions.py` (new or extend)
- `src/config/constants.py` (extend)
- `tests/services/test_rate_limit_service.py` (new)

**Effort:** 1 day
**Priority:** P1 - High

---

### Task Group 7.2: Apply Rate Limits to Endpoints
**Dependencies:** Task Group 7.1
**Assignee:** api-engineer

- [x] 7.2.0 Complete rate limit application to endpoints
  - [x] 7.2.1 Write 2-4 focused tests for endpoint rate limiting
    - Test auth endpoints rate limited by IP
    - Test API endpoints rate limited by user_id
    - Test admin endpoints have higher limits
    - Skip testing all endpoint combinations
  - [x] 7.2.2 Apply rate limits to authentication endpoints
    - POST /api/v1/auth/login: 5 req/min per IP
    - POST /api/v1/auth/register: 5 req/min per IP
    - POST /api/v1/auth/forgot-password: 3 req/hour per IP
    - POST /api/v1/auth/reset-password: 5 req/min per IP
    - POST /api/v1/auth/resend-verification: 1 req/2min per user
    - Use IP address as rate limit key
  - [x] 7.2.3 Create rate limit decorators
    - Decorator: `@rate_limit_by_ip(limit, window)` - For unauthenticated endpoints
    - Decorator: `@rate_limit_by_user(limit, window)` - For authenticated endpoints
    - File: `src/api/decorators/rate_limit.py` (new)
  - [x] 7.2.4 Apply rate limits to API endpoints
    - Chat/conversation endpoints: 30 req/min per user
    - Masterplan endpoints: 20 req/min per user
    - User endpoints: 60 req/min per user
    - Use user_id from JWT as rate limit key
  - [x] 7.2.5 Apply rate limits to admin endpoints
    - All admin endpoints: 100 req/min per admin user
    - Higher limit due to dashboard usage patterns
  - [x] 7.2.6 Implement per-user rate limit overrides
    - Check user_quotas.api_calls_per_minute for custom limits
    - Fall back to default if not set
    - Premium users can have higher limits
  - [x] 7.2.7 Ensure endpoint rate limiting tests pass
    - Run ONLY the 2-4 tests written in 7.2.1
    - Verify rate limits applied correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- All critical endpoints rate limited
- Authentication endpoints limited by IP
- API endpoints limited by user_id
- Per-user rate limit overrides work
- The 2-4 tests pass successfully

**Files:**
- `src/api/decorators/rate_limit.py` (new)
- `src/api/routers/auth.py` (extend)
- `src/api/routers/users.py` (extend)
- `src/api/routers/admin.py` (extend)
- `src/api/routers/masterplans.py` (extend)
- `tests/integration/test_rate_limiting.py` (new)

**Effort:** 1 day
**Priority:** P1 - High

---

## Phase 8: Frontend - Authentication UI

### Task Group 8.1: Authentication Pages
**Dependencies:** Phase 2 (Backend auth endpoints)
**Assignee:** ui-designer

- [x] 8.1.0 Complete authentication pages
  - [ ] 8.1.1 Write 2-8 focused tests for authentication pages
    - Test login form submission
    - Test registration form validation
    - Test password reset flow
    - Test email verification page
    - Test form error handling
    - Skip comprehensive UI interaction tests
  - [ ] 8.1.2 Create LoginPage component
    - Form fields: email (type=email), password (type=password)
    - Links: "Forgot password?" → /forgot-password, "Create account" → /register
    - Submit calls auth API: POST /api/v1/auth/login
    - On success: Redirect to /dashboard or originally requested page
    - Show validation errors and API errors
    - File: `src/ui/src/pages/LoginPage.tsx`
  - [ ] 8.1.3 Create RegisterPage component
    - Form fields: email, username, password, confirm password
    - Password strength indicator (weak/medium/strong)
    - Password requirements checklist (8+ chars, passwords match)
    - Submit calls: POST /api/v1/auth/register
    - On success: Auto-login or show "Check email" message (based on config)
    - File: `src/ui/src/pages/RegisterPage.tsx`
  - [ ] 8.1.4 Create ForgotPasswordPage component
    - Form field: email
    - Submit calls: POST /api/v1/auth/forgot-password
    - Always show success message (don't reveal if email exists)
    - Link: "Remember your password? Login"
    - File: `src/ui/src/pages/ForgotPasswordPage.tsx`
  - [ ] 8.1.5 Create ResetPasswordPage component
    - Extract token from URL query params
    - Form fields: new password, confirm password
    - Password strength indicator
    - Submit calls: POST /api/v1/auth/reset-password with token
    - On success: Redirect to /login after 3 seconds
    - Handle expired token error
    - File: `src/ui/src/pages/ResetPasswordPage.tsx`
  - [ ] 8.1.6 Create VerifyEmailPage component
    - Extract token from URL query params
    - On load: Call POST /api/v1/auth/verify-email
    - Show: Success (checkmark + "Email verified") or Error (expired token)
    - Button: "Go to Dashboard" or "Request new verification"
    - File: `src/ui/src/pages/VerifyEmailPage.tsx`
  - [ ] 8.1.7 Create VerifyEmailPendingPage component
    - Show: "Please verify your email address"
    - Display user's email
    - Button: "Resend verification email" (with 2-min cooldown)
    - Note: "Check spam folder"
    - File: `src/ui/src/pages/VerifyEmailPendingPage.tsx`
  - [ ] 8.1.8 Create PasswordStrengthIndicator component
    - Reusable component for password fields
    - Visual: Progress bar or color-coded text
    - Rules: Weak (< 8 chars), Medium (8-12 chars), Strong (12+ chars with variety)
    - File: `src/ui/src/components/auth/PasswordStrengthIndicator.tsx`
  - [ ] 8.1.9 Apply DevMatrix design system
    - Use existing Tailwind CSS classes
    - Match dark mode color scheme
    - Use existing button, input, and card styles
    - Ensure responsive design (mobile, tablet, desktop)
  - [ ] 8.1.10 Ensure authentication pages tests pass
    - Run ONLY the 2-8 tests written in 8.1.1
    - Verify pages render and submit correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- All 6 authentication pages implemented
- Forms validate input client-side
- API errors displayed to user
- Password strength indicator works
- Design matches DevMatrix UI
- The 2-8 tests pass successfully

**Files:**
- `src/ui/src/pages/LoginPage.tsx` (new)
- `src/ui/src/pages/RegisterPage.tsx` (new)
- `src/ui/src/pages/ForgotPasswordPage.tsx` (new)
- `src/ui/src/pages/ResetPasswordPage.tsx` (new)
- `src/ui/src/pages/VerifyEmailPage.tsx` (new)
- `src/ui/src/pages/VerifyEmailPendingPage.tsx` (new)
- `src/ui/src/components/auth/PasswordStrengthIndicator.tsx` (new)

**Effort:** 2.5 days
**Priority:** P0 - Critical

---

### Task Group 8.2: Auth Context & Protected Routes
**Dependencies:** Task Group 8.1
**Assignee:** ui-designer

- [x] 8.2.0 Complete auth context and routing
  - [ ] 8.2.1 Write 2-6 focused tests for auth context
    - Test login updates auth state
    - Test logout clears auth state
    - Test token refresh logic
    - Test protected route redirects
    - Skip exhaustive context edge cases
  - [ ] 8.2.2 Create AuthContext and AuthProvider
    - State: user (User | null), isAuthenticated (boolean), isLoading (boolean)
    - Methods: login(email, password), logout(), refreshToken(), checkAuth()
    - Store tokens in httpOnly cookies (set by backend)
    - File: `src/ui/src/contexts/AuthContext.tsx`
  - [ ] 8.2.3 Implement login method
    - Call POST /api/v1/auth/login with credentials
    - On success: Set user state from response
    - Tokens automatically stored in cookies by backend
    - Handle errors: Invalid credentials, account inactive
  - [ ] 8.2.4 Implement logout method
    - Call POST /api/v1/auth/logout
    - Clear user state
    - Redirect to /login
  - [ ] 8.2.5 Implement checkAuth method
    - Call GET /api/v1/auth/me on app load
    - If successful: Set user state (user still authenticated)
    - If 401: Clear state (logged out)
    - Set isLoading=false after check
  - [ ] 8.2.6 Implement auto token refresh logic
    - Check access token expiry every 1 minute (setInterval)
    - If < 5 minutes remaining: Call POST /api/v1/auth/refresh
    - If refresh fails (401): Redirect to login
    - Extract expiry from JWT token (decode client-side)
  - [ ] 8.2.7 Create PrivateRoute component
    - Wrapper component for protected routes
    - If not authenticated: Redirect to /login?redirect={pathname}
    - If authenticated: Render children
    - File: `src/ui/src/components/routing/PrivateRoute.tsx`
  - [ ] 8.2.8 Create AdminRoute component
    - Wrapper for admin-only routes
    - If not authenticated: Redirect to /login
    - If not admin (is_superuser=false): Show 403 Forbidden page
    - If admin: Render children
    - File: `src/ui/src/components/routing/AdminRoute.tsx`
  - [ ] 8.2.9 Update App.tsx with AuthProvider and routes
    - Wrap app in <AuthProvider>
    - Add routes: /login, /register, /forgot-password, /reset-password, /verify-email
    - Wrap existing routes in <PrivateRoute>
    - Wrap admin routes in <AdminRoute>
  - [ ] 8.2.10 Implement global error handling
    - Intercept 401 errors: Redirect to /login
    - Intercept 403 errors: Show "Access Denied" message
    - Add axios/fetch interceptor
    - File: `src/ui/src/utils/apiClient.ts` (new or extend)
  - [ ] 8.2.11 Ensure auth context tests pass
    - Run ONLY the 2-6 tests written in 8.2.1
    - Verify auth state management works
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Auth context manages user state globally
- Login/logout work correctly
- Auto token refresh prevents expiry
- Protected routes redirect unauthenticated users
- Admin routes enforce superuser check
- Global error handling redirects on 401
- The 2-6 tests pass successfully

**Files:**
- `src/ui/src/contexts/AuthContext.tsx` (new)
- `src/ui/src/components/routing/PrivateRoute.tsx` (new)
- `src/ui/src/components/routing/AdminRoute.tsx` (new)
- `src/ui/src/App.tsx` (extend)
- `src/ui/src/utils/apiClient.ts` (new or extend)

**Effort:** 2 days
**Priority:** P0 - Critical

---

### Task Group 8.3: User Profile & Usage Display
**Dependencies:** Task Groups 5.4, 8.2
**Assignee:** ui-designer

- [x] 8.3.0 Complete user profile and usage UI
  - [ ] 8.3.1 Write 2-6 focused tests for profile and usage components
    - Test UserProfilePage renders user info
    - Test UsageStatsCard displays usage correctly
    - Test progress bar color changes based on percentage
    - Test usage badge in header updates
    - Skip comprehensive UI rendering tests
  - [ ] 8.3.2 Create UserProfilePage component
    - Section 1: Account Info (email, username, member since, last login)
    - Section 2: Usage Statistics (use UsageStatsCard component)
    - Buttons: "Change Password" (future), "Logout"
    - Fetch user data: GET /api/v1/auth/me
    - Fetch usage data: GET /api/v1/users/me/usage
    - File: `src/ui/src/pages/UserProfilePage.tsx`
  - [ ] 8.3.3 Create UsageStatsCard component
    - Reusable card showing one usage metric
    - Props: title, used, limit, unit, type (tokens/masterplans/storage)
    - Display: Progress bar, percentage, "X / Y" text
    - Color coding: Green (< 80%), Yellow (80-95%), Red (> 95%)
    - Show quota reset date for tokens
    - File: `src/ui/src/components/usage/UsageStatsCard.tsx`
  - [ ] 8.3.4 Create UsageBadge component for header
    - Display: Token icon + "45K / 100K" text
    - Color-coded based on percentage
    - Tooltip: "LLM tokens used this month"
    - Click: Navigate to /profile#usage
    - File: `src/ui/src/components/header/UsageBadge.tsx`
  - [ ] 8.3.5 Create UserMenu dropdown component
    - Trigger: Avatar icon + username
    - Menu items: Profile, Usage & Billing (future), Settings (future), Divider, Logout
    - File: `src/ui/src/components/header/UserMenu.tsx`
  - [ ] 8.3.6 Update Header component
    - Replace "Login" button with UserMenu (when authenticated)
    - Add UsageBadge next to UserMenu
    - File: `src/ui/src/components/Header.tsx` or similar (extend)
  - [ ] 8.3.7 Add route for profile page
    - Route: /profile → UserProfilePage
    - Protected route (requires authentication)
    - Update: `src/ui/src/App.tsx`
  - [ ] 8.3.8 Ensure profile/usage UI tests pass
    - Run ONLY the 2-6 tests written in 8.3.1
    - Verify components render correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- User profile page displays account info and usage
- Usage stats cards show progress with color coding
- Header shows usage badge and user menu
- All components match DevMatrix design
- The 2-6 tests pass successfully

**Files:**
- `src/ui/src/pages/UserProfilePage.tsx` (new)
- `src/ui/src/components/usage/UsageStatsCard.tsx` (new)
- `src/ui/src/components/header/UsageBadge.tsx` (new)
- `src/ui/src/components/header/UserMenu.tsx` (new)
- `src/ui/src/components/Header.tsx` (extend)
- `src/ui/src/App.tsx` (extend)

**Effort:** 1.5 days
**Priority:** P1 - High

---

### Task Group 8.4: Admin Dashboard UI (Optional - Time Permitting)
**Dependencies:** Task Groups 6.1, 6.2, 8.2
**Assignee:** ui-designer

- [x] 8.4.0 Complete admin dashboard UI (OPTIONAL)
  - [ ] 8.4.1 Write 2-6 focused tests for admin UI
    - Test AdminDashboardPage renders statistics
    - Test AdminUsersPage displays user list
    - Test user search and filtering
    - Test user detail page shows info
    - Skip comprehensive admin UI tests
  - [ ] 8.4.2 Create AdminDashboardPage component
    - Overview cards: Total users, active users, new users, total LLM cost
    - Charts: Usage over time (optional)
    - Top users table: By token usage
    - Fetch: GET /api/v1/admin/statistics
    - File: `src/ui/src/pages/admin/AdminDashboardPage.tsx`
  - [ ] 8.4.3 Create AdminUsersPage component
    - Table: Email, username, created date, last login, usage summary, actions
    - Search bar: Filter by email/username
    - Filters: Active/Inactive/All
    - Pagination controls
    - Actions: View details, Deactivate/Activate, Impersonate
    - Fetch: GET /api/v1/admin/users with pagination
    - File: `src/ui/src/pages/admin/AdminUsersPage.tsx`
  - [ ] 8.4.4 Create AdminUserDetailPage component
    - Sections: User info, quotas, current usage, lifetime stats
    - Buttons: Edit quotas, Deactivate, Impersonate, Delete
    - Fetch: GET /api/v1/admin/users/{user_id}
    - File: `src/ui/src/pages/admin/AdminUserDetailPage.tsx`
  - [ ] 8.4.5 Create EditQuotasModal component
    - Form: Token limit, masterplan limit, storage limit
    - Checkbox: Set to unlimited (null value)
    - Submit: PATCH /api/v1/admin/users/{user_id}/quotas
    - File: `src/ui/src/components/admin/EditQuotasModal.tsx`
  - [ ] 8.4.6 Add admin routes
    - Routes: /admin, /admin/users, /admin/users/:userId
    - Wrap in <AdminRoute>
    - Update: `src/ui/src/App.tsx`
  - [ ] 8.4.7 Add admin navigation
    - Add "Admin" link to header UserMenu (if is_superuser)
    - Link to /admin/dashboard
  - [ ] 8.4.8 Ensure admin UI tests pass
    - Run ONLY the 2-6 tests written in 8.4.1
    - Verify admin pages render correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- Admin dashboard shows global statistics
- Admin users page lists all users with search/filter
- Admin user detail page shows comprehensive info
- Quota editing works correctly
- Only superusers can access admin pages
- The 2-6 tests pass successfully

**Note:** This task group is optional and should only be completed if time permits. Basic admin functionality can be accessed via API tools (Postman) initially.

**Files:**
- `src/ui/src/pages/admin/AdminDashboardPage.tsx` (new)
- `src/ui/src/pages/admin/AdminUsersPage.tsx` (new)
- `src/ui/src/pages/admin/AdminUserDetailPage.tsx` (new)
- `src/ui/src/components/admin/EditQuotasModal.tsx` (new)
- `src/ui/src/App.tsx` (extend)

**Effort:** 2 days (OPTIONAL)
**Priority:** P2 - Medium (can be deferred to Phase 7)

---

## Phase 9: Testing & Quality Assurance

### Task Group 9.1: Integration Testing
**Dependencies:** All previous phases
**Assignee:** qa-engineer

- [x] 9.1.0 Complete integration testing
  - [x] 9.1.1 Review existing tests from all phases
    - Review tests from Task Groups 1.1, 2.1, 2.2, 2.3, 3.1, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 7.1, 8.1, 8.2, 8.3
    - Identify gaps in integration workflows
    - Total existing tests: approximately 30-70 tests
  - [x] 9.1.2 Analyze test coverage gaps for authentication & multi-tenancy
    - Focus on end-to-end user workflows
    - Identify missing integration points
    - Prioritize business-critical flows
    - DO NOT assess entire application coverage
  - [x] 9.1.3 Write up to 10 additional integration tests maximum
    - Test: Complete registration → email verification → login flow
    - Test: Password reset flow end-to-end
    - Test: Multi-user data isolation (User A cannot see User B's data)
    - Test: Quota enforcement blocks LLM calls when exceeded
    - Test: Admin can manage users and quotas
    - Test: Rate limiting prevents abuse
    - Test: Auto token refresh keeps user logged in
    - Test: Impersonation flow works correctly
    - DO NOT write comprehensive coverage for all scenarios
    - Focus on critical happy paths and key security checks
  - [x] 9.1.4 Run feature-specific tests only
    - Run ONLY tests related to Phase 6 features
    - Expected total: approximately 40-80 tests
    - DO NOT run entire DevMatrix test suite
    - Verify all critical workflows pass
  - [x] 9.1.5 Create test data fixtures
    - Fixture: Test users (regular and admin)
    - Fixture: User quotas (default and custom)
    - Fixture: Usage data samples
    - File: `tests/fixtures/auth_fixtures.py`
  - [x] 9.1.6 Document test coverage
    - Generate coverage report for Phase 6 code only
    - Document known gaps and justification
    - Add to: `tests/PHASE6_TEST_COVERAGE.md`

**Acceptance Criteria:**
- All feature-specific tests pass (40-80 tests total)
- No more than 10 additional tests added
- Critical user workflows covered
- Multi-tenancy isolation verified
- Security features tested
- Test coverage documented

**Files:**
- `tests/integration/test_auth_flow.py` (new)
- `tests/integration/test_password_reset_flow.py` (new)
- `tests/integration/test_multi_user_isolation.py` (extend existing)
- `tests/integration/test_quota_enforcement.py` (new)
- `tests/integration/test_admin_workflows.py` (new)
- `tests/fixtures/auth_fixtures.py` (new)
- `tests/PHASE6_TEST_COVERAGE.md` (new)

**Effort:** 1.5 days
**Priority:** P0 - Critical

---

### Task Group 9.2: Security Testing
**Dependencies:** Task Group 9.1
**Assignee:** qa-engineer

- [ ] 9.2.0 Complete security testing
  - [ ] 9.2.1 Test authentication security
    - Verify passwords hashed with bcrypt (not stored plaintext)
    - Verify tokens signed and cannot be tampered
    - Verify httpOnly cookies prevent XSS theft
    - Verify rate limiting prevents brute force
    - Test: Invalid token returns 401
    - Test: Expired token returns 401
  - [ ] 9.2.2 Test multi-tenancy security
    - Verify User A cannot access User B's masterplans via API
    - Verify User A cannot access User B's conversations
    - Verify User A cannot write to User B's workspace
    - Verify path traversal attacks blocked
    - Test returns 404 (not 403) for unauthorized access
  - [ ] 9.2.3 Test admin privilege escalation
    - Verify non-admin cannot access admin endpoints (403)
    - Verify cannot impersonate admin users
    - Verify admin token required for admin actions
    - Test non-admin cannot modify quotas
  - [ ] 9.2.4 Test SQL injection prevention
    - Attempt SQL injection in email field
    - Attempt SQL injection in search queries
    - Verify SQLAlchemy ORM prevents injection
  - [ ] 9.2.5 Test CSRF protection
    - Verify SameSite=Strict cookie flag prevents CSRF
    - Test cross-origin requests blocked by CORS
  - [ ] 9.2.6 Document security test results
    - List all security tests performed
    - Document any vulnerabilities found and fixed
    - File: `tests/SECURITY_TEST_RESULTS.md`

**Acceptance Criteria:**
- All security tests pass
- No data leakage between users
- No privilege escalation possible
- SQL injection prevented
- CSRF attacks blocked
- Security results documented

**Files:**
- `tests/security/test_authentication_security.py` (new)
- `tests/security/test_multi_tenancy_security.py` (new)
- `tests/security/test_admin_security.py` (new)
- `tests/SECURITY_TEST_RESULTS.md` (new)

**Effort:** 1 day
**Priority:** P0 - Critical

---

### Task Group 9.3: Performance Testing
**Dependencies:** Task Group 9.1
**Assignee:** qa-engineer

- [ ] 9.3.0 Complete performance testing
  - [ ] 9.3.1 Test authentication endpoint performance
    - Measure: POST /api/v1/auth/login response time
    - Target: < 200ms for 95th percentile
    - Test with 100 concurrent requests
  - [ ] 9.3.2 Test user data endpoint performance
    - Measure: GET /api/v1/users/me/usage response time
    - Target: < 100ms
    - Verify caching reduces DB queries
  - [ ] 9.3.3 Test admin statistics performance
    - Measure: GET /api/v1/admin/statistics response time
    - Target: < 500ms
    - Verify caching works (5-minute TTL)
  - [ ] 9.3.4 Test database query performance
    - Verify indexes used for user_id filters
    - Run EXPLAIN ANALYZE on critical queries
    - Identify and fix N+1 query problems
  - [ ] 9.3.5 Test rate limiting performance
    - Verify Redis rate limit checks are fast (< 10ms)
    - Test with 1000 concurrent requests
  - [ ] 9.3.6 Document performance test results
    - List all performance metrics
    - Identify bottlenecks and optimizations
    - File: `tests/PERFORMANCE_TEST_RESULTS.md`

**Acceptance Criteria:**
- Auth endpoints respond in < 200ms
- User endpoints respond in < 100ms
- Admin endpoints respond in < 500ms
- Database queries use indexes
- No N+1 query problems
- Results documented

**Files:**
- `tests/performance/test_auth_performance.py` (new)
- `tests/performance/test_api_performance.py` (new)
- `tests/PERFORMANCE_TEST_RESULTS.md` (new)

**Effort:** 0.5 days
**Priority:** P1 - High

---

## Phase 10: Documentation & Deployment

### Task Group 10.1: API Documentation
**Dependencies:** All backend phases
**Assignee:** tech-writer

- [ ] 10.1.0 Complete API documentation
  - [ ] 10.1.1 Update OpenAPI/Swagger documentation
    - Document all new endpoints with request/response schemas
    - Add authentication requirements (Bearer token)
    - Add rate limit information
    - Add error response examples
    - File: Auto-generated by FastAPI at `/docs`
  - [ ] 10.1.2 Create authentication API guide
    - Document registration flow with examples
    - Document login and token refresh
    - Document password reset flow
    - Document email verification
    - File: `DOCS/API_AUTHENTICATION.md`
  - [ ] 10.1.3 Create admin API guide
    - Document all admin endpoints
    - Document impersonation flow
    - Document quota management
    - File: `DOCS/API_ADMIN.md`
  - [ ] 10.1.4 Create usage tracking API guide
    - Document usage statistics endpoint
    - Explain quota enforcement
    - File: `DOCS/API_USAGE.md`
  - [ ] 10.1.5 Add authentication examples to existing guides
    - Update masterplan API examples to include auth headers
    - Update chat API examples
    - Files: Various DOCS files

**Acceptance Criteria:**
- OpenAPI docs include all Phase 6 endpoints
- Authentication guide complete with examples
- Admin guide covers all admin features
- Usage tracking documented
- Existing guides updated

**Files:**
- `DOCS/API_AUTHENTICATION.md` (new)
- `DOCS/API_ADMIN.md` (new)
- `DOCS/API_USAGE.md` (new)
- Various existing DOCS files (update)

**Effort:** 1 day
**Priority:** P1 - High

---

### Task Group 10.2: Deployment Documentation
**Dependencies:** Task Group 10.1
**Assignee:** tech-writer

- [ ] 10.2.0 Complete deployment documentation
  - [ ] 10.2.1 Document environment variables
    - Update .env.example with all new variables
    - Document all email settings (SMTP)
    - Document auth settings (JWT secrets, expiry)
    - Document quota defaults
    - Document rate limit settings
    - File: `.env.example`
  - [ ] 10.2.2 Create database migration guide
    - Document Alembic migration steps
    - Document rollback procedures
    - Document backup procedures
    - File: `DOCS/DATABASE_MIGRATIONS.md`
  - [ ] 10.2.3 Create initial admin setup guide
    - Document CLI command to create first admin
    - Document FIRST_USER_IS_ADMIN setting
    - Security warnings for production
    - File: `DOCS/ADMIN_SETUP.md`
  - [ ] 10.2.4 Create email service setup guide
    - Document SendGrid configuration
    - Document SMTP alternatives (AWS SES, Mailgun)
    - Document testing with MailHog/Mailtrap
    - File: `DOCS/EMAIL_SETUP.md`
  - [ ] 10.2.5 Update main README with Phase 6 features
    - Add authentication section
    - Add multi-tenancy overview
    - Update installation steps
    - File: `README.md`
  - [ ] 10.2.6 Create production deployment checklist
    - Environment variables to change
    - Security settings to verify
    - Database migrations to run
    - Email service to configure
    - First admin creation
    - File: `DOCS/PRODUCTION_DEPLOYMENT_CHECKLIST.md`

**Acceptance Criteria:**
- All environment variables documented
- Migration guide complete
- Admin setup documented
- Email service setup guide available
- README updated
- Production checklist ready

**Files:**
- `.env.example` (update)
- `DOCS/DATABASE_MIGRATIONS.md` (new)
- `DOCS/ADMIN_SETUP.md` (new)
- `DOCS/EMAIL_SETUP.md` (new)
- `README.md` (update)
- `DOCS/PRODUCTION_DEPLOYMENT_CHECKLIST.md` (new)

**Effort:** 1 day
**Priority:** P1 - High

---

### Task Group 10.3: User Documentation
**Dependencies:** Task Group 10.2
**Assignee:** tech-writer

- [ ] 10.3.0 Complete user documentation
  - [ ] 10.3.1 Create user registration guide
    - How to create account
    - Email verification process
    - Password requirements
    - File: `DOCS/USER_GUIDE_REGISTRATION.md`
  - [ ] 10.3.2 Create user profile guide
    - How to view usage statistics
    - Understanding quotas
    - How to change password (future)
    - File: `DOCS/USER_GUIDE_PROFILE.md`
  - [ ] 10.3.3 Create admin user guide
    - How to manage users
    - How to adjust quotas
    - How to impersonate users
    - How to view statistics
    - File: `DOCS/ADMIN_USER_GUIDE.md`
  - [ ] 10.3.4 Create troubleshooting guide
    - Password reset issues
    - Email not received
    - Quota exceeded errors
    - Login problems
    - File: `DOCS/TROUBLESHOOTING.md`

**Acceptance Criteria:**
- User guides cover all key features
- Admin guide complete
- Troubleshooting guide addresses common issues
- Documentation clear and well-formatted

**Files:**
- `DOCS/USER_GUIDE_REGISTRATION.md` (new)
- `DOCS/USER_GUIDE_PROFILE.md` (new)
- `DOCS/ADMIN_USER_GUIDE.md` (new)
- `DOCS/TROUBLESHOOTING.md` (new)

**Effort:** 1 day
**Priority:** P2 - Medium

---

### Task Group 10.4: Monitoring & Alerting Setup
**Dependencies:** All phases
**Assignee:** devops-engineer

- [ ] 10.4.0 Complete monitoring and alerting setup
  - [ ] 10.4.1 Set up authentication event logging
    - Log all login attempts (success/failure)
    - Log registration events
    - Log password reset requests
    - Log admin actions (impersonation, quota changes)
    - Use structured logging (JSON format)
  - [ ] 10.4.2 Set up rate limit violation monitoring
    - Track rate limit exceeded events
    - Alert if violations > 100/minute (potential attack)
    - Dashboard for rate limit metrics
  - [ ] 10.4.3 Set up quota usage monitoring
    - Alert when user exceeds 90% of quota
    - Track quota exceeded errors
    - Dashboard for quota usage trends
  - [ ] 10.4.4 Set up security event monitoring
    - Alert on multiple failed login attempts from same IP
    - Alert on admin privilege escalation attempts
    - Alert on suspicious data access patterns
  - [ ] 10.4.5 Create monitoring dashboard
    - Metrics: Total users, active users, new users per day
    - Metrics: LLM tokens used, costs
    - Metrics: API response times
    - Metrics: Error rates by endpoint
    - Tool: Grafana, DataDog, or similar
  - [ ] 10.4.6 Document monitoring setup
    - List all monitored metrics
    - Document alert thresholds
    - Document how to access dashboards
    - File: `DOCS/MONITORING.md`

**Acceptance Criteria:**
- All authentication events logged
- Rate limit violations monitored
- Quota usage alerts configured
- Security events monitored
- Monitoring dashboard operational
- Documentation complete

**Files:**
- `src/utils/structured_logging.py` (new)
- `monitoring/dashboards/` (new directory with configs)
- `DOCS/MONITORING.md` (new)

**Effort:** 1.5 days
**Priority:** P1 - High

---

## Summary by Specialist

### Database Engineer (4 days)
- Task Group 1.1: Database Schema Design ✅ COMPLETED
- Task Group 1.2: Alembic Migrations ✅ COMPLETED

### API Engineer (15 days)
- Task Group 2.1: Email Verification Service
- Task Group 2.2: Password Reset Service
- Task Group 2.3: Authentication API Endpoints
- Task Group 3.1: Email Service Implementation
- Task Group 4.1: Workspace Service
- Task Group 4.2: Query Filtering & Data Isolation
- Task Group 5.1: Usage Tracking Service
- Task Group 5.2: Quota Enforcement Service
- Task Group 5.3: Storage Tracking Background Job
- Task Group 5.4: Usage Statistics API
- Task Group 6.1: Admin User Management API
- Task Group 6.2: Admin Quota Management & Statistics
- Task Group 6.3: User Impersonation
- Task Group 7.1: Rate Limiting Infrastructure
- Task Group 7.2: Apply Rate Limits to Endpoints

### UI Designer (6 days)
- Task Group 8.1: Authentication Pages
- Task Group 8.2: Auth Context & Protected Routes
- Task Group 8.3: User Profile & Usage Display
- Task Group 8.4: Admin Dashboard UI (Optional)

### QA Engineer (3 days)
- Task Group 9.1: Integration Testing
- Task Group 9.2: Security Testing
- Task Group 9.3: Performance Testing

### Tech Writer (3 days)
- Task Group 10.1: API Documentation
- Task Group 10.2: Deployment Documentation
- Task Group 10.3: User Documentation

### DevOps Engineer (1.5 days)
- Task Group 10.4: Monitoring & Alerting Setup

**Total Effort: ~32.5 days across specialists (3-4 weeks with parallel work)**

---

## Execution Order & Dependencies

### Week 1: Foundation & Core Backend
1. **Phase 1**: Database Schema & Migrations (Days 1-2) ✅ COMPLETED
2. **Phase 2**: Authentication Services (Days 2-4)
3. **Phase 3**: Email Infrastructure (Days 4-5)

### Week 2: Multi-tenancy & Usage Tracking
4. **Phase 4**: Data Isolation & Workspaces (Days 6-8)
5. **Phase 5**: Usage Tracking & Quotas (Days 8-11)

### Week 3: Admin Features & Security
6. **Phase 6**: Admin Features (Days 12-14)
7. **Phase 7**: Rate Limiting (Days 14-16)

### Week 4: Frontend & Quality Assurance
8. **Phase 8**: Frontend UI (Days 17-21)
9. **Phase 9**: Testing & QA (Days 21-24)
10. **Phase 10**: Documentation & Deployment (Days 24-26)

**Buffer**: Days 27-30 for unexpected issues and polish

---

## Risk Mitigation

- **Email Delivery Issues**: Make verification optional via env var, test with local SMTP
- **Migration Failures**: Test on staging, maintain backups, have rollback plan
- **Multi-tenancy Data Leakage**: Comprehensive security testing in Phase 9
- **Performance Issues**: Performance testing in Phase 9, optimize before production
- **Scope Creep**: Admin UI (Task Group 8.4) is optional, can be deferred

---

## Definition of Done

A task is considered complete when:
1. All sub-tasks completed
2. 2-8 focused tests written and passing for that task group
3. Code reviewed and merged
4. Documentation updated (if applicable)
5. No blocking bugs or security issues
6. Acceptance criteria met

Phase 6 is complete when:
- All 73 tasks completed
- All tests passing (approximately 60-100 tests total)
- Security testing passed
- Performance benchmarks met
- Documentation complete
- Production deployment successful
