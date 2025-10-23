# Spec Requirements: Phase 6 - Authentication & Multi-tenancy

## Overview

### Feature Description
Implement comprehensive user authentication and multi-tenancy system to transform DevMatrix from a single-user local application into a multi-user SaaS platform. This foundational phase enables multiple users to securely register, authenticate, and use DevMatrix with completely isolated workspaces, while tracking usage metrics and enforcing per-user quotas.

### Goals
1. **Secure Authentication**: Implement industry-standard authentication with JWT tokens, bcrypt password hashing, and email verification
2. **Multi-tenancy**: Enable complete isolation between users - each user sees only their own data (masterplans, conversations, workspace files)
3. **Usage Tracking**: Track LLM token consumption, masterplan creation, and storage usage per user for future billing and quota enforcement
4. **Admin Capabilities**: Provide comprehensive admin tools to manage users, view statistics, and adjust quotas
5. **Scalability Foundation**: Prepare authentication architecture to support future OAuth integration (Google, GitHub)
6. **Production Security**: Implement rate limiting, secure session management, and password reset flows

### Success Criteria
- Users can register with email/password and receive verification emails
- Authentication works via JWT tokens with 1-hour access tokens and 30-day refresh tokens
- Each user can only access their own masterplans, conversations, and workspace files
- Admin users can view all users, statistics, and manage quotas
- Usage tracking captures all LLM token consumption per user
- Rate limiting prevents API abuse
- Password reset flow works securely with time-limited tokens
- Frontend displays user-specific usage statistics
- All existing DevMatrix features work with authentication enabled

---

## In Scope

### User Authentication
- Email/password registration with username
- Email verification system (configurable - users created as verified by default via .env)
- JWT-based authentication (access + refresh tokens)
- Password reset via email with time-limited tokens
- Login/logout functionality
- Session management with httpOnly cookies (recommended approach)

### Multi-tenancy & Data Isolation
- Add `user_id` foreign key to all existing tables (conversations, masterplans, discovery_documents, etc.)
- Workspace isolation: `/workspaces/{user_id}/` directory structure
- Database queries filtered by `user_id` automatically
- Users can only see/access their own data

### Usage Tracking & Quotas
- Track per user (configurable from users table or future backoffice):
  - LLM tokens consumed (monthly)
  - Number of masterplans created
  - Storage usage (workspace files)
- All limits configurable per user in database
- Display usage statistics in frontend UI

### Admin Features
- Admin dashboard with capabilities:
  - View all users and their statistics
  - Deactivate/reactivate user accounts
  - Impersonate users (to debug issues)
  - Manually adjust user quotas
  - View global system statistics (total users, total tokens, etc.)
- Admin-only API endpoints protected by `is_superuser` flag

### Frontend UI
- Login page with email/password form
- Registration page with email, username, password
- Password reset flow (request reset, email with link, reset password)
- User profile page showing:
  - Account info (email, username, created date)
  - Usage statistics (tokens this month, masterplans count, storage)
  - Logout button
- Usage stats displayed in main UI (e.g., header showing "Tokens: 45K/100K this month")

### Rate Limiting
Implement rate limiting for:
- **Authentication endpoints**: 5 requests per minute per IP (login, register, password reset)
- **Chat/conversation endpoints**: 30 requests per minute per user
- **LLM token limits**: Configurable per user (e.g., 1M tokens/month default)
- **Admin endpoints**: 100 requests per minute per admin

### Session Management
- JWT access tokens: 1 hour expiry (already configured)
- JWT refresh tokens: 30 days expiry (already configured)
- Token storage: httpOnly cookies for security (recommended)
- Automatic token refresh before expiry
- Secure logout with token cleanup

### Email System
- Email verification emails with clickable verification link
- Password reset emails with time-limited token (1 hour expiry)
- Welcome emails on successful registration
- Email service: Configurable SMTP settings in .env (recommend SendGrid or similar)

---

## Out of Scope

Explicitly deferred to future phases:

- **Teams/Organizations**: Multi-user collaboration within teams (Phase 8)
- **Payment Integration**: Stripe/payment processing for paid plans
- **OAuth/Social Login**: Google and GitHub OAuth (foundation prepared, implementation deferred)
- **SSO/SAML**: Enterprise single sign-on (Phase 10)
- **Two-Factor Authentication (2FA)**: Additional security layer
- **Audit Logs**: Comprehensive activity logging (Phase 10)
- **API Keys**: User-generated API keys for external integrations
- **Workspace Sharing**: Sharing masterplans between users
- **Role Hierarchy**: Complex role systems beyond user/admin

---

## Existing Implementation

The following authentication components are **already implemented** and production-ready:

### Database Model: User
**File**: `src/models/user.py`

```python
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
```

**Features**:
- UUID primary key
- Email and username uniqueness enforced
- Password hashing support
- Active/superuser flags
- Timestamp tracking
- `to_dict()` method for JSON serialization (excludes password_hash)

### Authentication Service
**File**: `src/services/auth_service.py`

**Implemented Methods**:
- `hash_password(password: str)` - Bcrypt password hashing
- `verify_password(plain, hashed)` - Password verification
- `create_access_token(user_id, email, username)` - 1-hour JWT access tokens
- `create_refresh_token(user_id)` - 30-day JWT refresh tokens
- `verify_access_token(token)` - Token validation and decoding
- `verify_refresh_token(token)` - Refresh token validation
- `register_user(email, username, password)` - User registration with duplicate checks
- `login(email, password)` - Authentication with token generation
- `refresh_access_token(refresh_token)` - Generate new access token
- `get_current_user(token)` - Get user from token

**JWT Configuration** (from .env):
- `JWT_SECRET_KEY` - Secret for signing tokens
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Default: 60 (1 hour)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Default: 30

### Authentication API Endpoints
**File**: `src/api/routers/auth.py`

**Implemented Endpoints**:
- `POST /api/v1/auth/register` - Register new user (returns access + refresh tokens)
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info (requires auth)
- `POST /api/v1/auth/logout` - Logout (stateless JWT, client-side token deletion)
- `GET /api/v1/auth/health` - Health check

**Request/Response Models**:
- `RegisterRequest` - Email, username, password validation
- `LoginRequest` - Email, password
- `RefreshTokenRequest` - Refresh token
- `TokenResponse` - Access token, refresh token, expiry, user info
- `UserResponse` - User profile data

### Authentication Middleware
**File**: `src/api/middleware/auth_middleware.py`

**Implemented Dependencies**:
- `get_token_from_header()` - Extract Bearer token from Authorization header
- `get_current_user()` - Get authenticated user from token
- `get_current_active_user()` - Ensure user account is active
- `get_current_superuser()` - Ensure user has admin privileges
- `get_optional_user()` - Get user if authenticated, None otherwise (for optional auth endpoints)

**Security Features**:
- Bearer token validation
- Token expiry checking
- User account status validation
- Superuser privilege checking

---

## What Needs to be Built

### Gap Analysis

Based on the existing implementation and user requirements, the following components need to be built:

#### 1. Email Verification System
**Status**: NOT IMPLEMENTED

**Required**:
- Database migration: Add `is_verified` and `verification_token` columns to users table
- Email verification service with token generation
- Email templates for verification emails
- API endpoint: `POST /api/v1/auth/verify-email` (with token parameter)
- API endpoint: `POST /api/v1/auth/resend-verification` (resend verification email)
- Environment variable: `EMAIL_VERIFICATION_REQUIRED` (default: False - users created as verified)
- Email sending integration (SMTP configuration)

#### 2. Password Reset Flow
**Status**: NOT IMPLEMENTED

**Required**:
- Database migration: Add `password_reset_token` and `password_reset_expires` columns to users table
- Password reset service with time-limited tokens (1-hour expiry)
- Email templates for password reset emails
- API endpoint: `POST /api/v1/auth/forgot-password` (send reset email)
- API endpoint: `POST /api/v1/auth/reset-password` (verify token and set new password)
- Token cleanup for expired tokens

#### 3. Multi-tenancy Database Schema
**Status**: PARTIALLY IMPLEMENTED

**Required Migrations**:
- Add `user_id` foreign key to:
  - `discovery_documents` table (currently has user_id as String, needs FK to users.user_id)
  - `masterplans` table (currently has user_id as String, needs FK to users.user_id)
  - `conversations` table (needs user_id UUID FK added)
  - `messages` table (inherits from conversations, no direct FK needed)
  - Future tables: Any new tables must include user_id FK

**Note**: `discovery_documents` and `masterplans` already have `user_id` field as String(100), but need migration to change to UUID FK referencing users.user_id

#### 4. Workspace Isolation
**Status**: NOT IMPLEMENTED

**Required**:
- File system service for managing per-user workspaces: `/workspaces/{user_id}/`
- Workspace initialization on user registration
- Workspace cleanup on user deletion (or soft-delete with retention)
- Update all file operations to use user-specific workspace paths
- Git repository initialization per user workspace
- Workspace size tracking for usage quotas

#### 5. Usage Tracking System
**Status**: NOT IMPLEMENTED

**Required**:
- Database table: `user_usage` with fields:
  - `usage_id` (UUID, primary key)
  - `user_id` (UUID, FK to users)
  - `month` (Date, indexed - e.g., 2025-10-01)
  - `llm_tokens_used` (Integer, default 0)
  - `llm_cost_usd` (Float, default 0.0)
  - `masterplans_created` (Integer, default 0)
  - `storage_bytes` (BigInteger, default 0)
  - `api_calls` (Integer, default 0)
  - `created_at`, `updated_at` (DateTime)

- Database table: `user_quotas` with fields:
  - `quota_id` (UUID, primary key)
  - `user_id` (UUID, FK to users, unique)
  - `llm_tokens_monthly_limit` (Integer, nullable - null means unlimited)
  - `masterplans_limit` (Integer, nullable)
  - `storage_bytes_limit` (BigInteger, nullable)
  - `api_calls_per_minute` (Integer, default 30)
  - `created_at`, `updated_at` (DateTime)

- Service: `usage_tracking_service.py` with methods:
  - `track_llm_usage(user_id, tokens, cost_usd, model)`
  - `track_masterplan_created(user_id)`
  - `track_storage_usage(user_id, bytes_added)`
  - `get_current_month_usage(user_id)`
  - `check_quota_exceeded(user_id, quota_type)`
  - `get_usage_statistics(user_id, start_date, end_date)`

- Integration: Update all LLM calls to track usage per user
- Integration: Update masterplan creation to track usage
- Integration: Add storage calculation cron job/background task

#### 6. Rate Limiting Implementation
**Status**: NOT IMPLEMENTED

**Required**:
- Install rate limiting library: `slowapi` or `fastapi-limiter`
- Redis integration for distributed rate limiting (Redis already available)
- Rate limit decorators for endpoints:
  - Authentication endpoints: 5 req/min per IP
  - Chat endpoints: 30 req/min per user
  - Admin endpoints: 100 req/min per admin
- Rate limit headers in responses (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
- Custom error response for rate limit exceeded (429 status)

#### 7. Admin Dashboard API
**Status**: NOT IMPLEMENTED

**Required Endpoints**:
- `GET /api/v1/admin/users` - List all users with pagination, filtering
- `GET /api/v1/admin/users/{user_id}` - Get specific user details
- `PATCH /api/v1/admin/users/{user_id}` - Update user (activate/deactivate, change quotas)
- `DELETE /api/v1/admin/users/{user_id}` - Soft delete user
- `POST /api/v1/admin/impersonate/{user_id}` - Generate impersonation token
- `GET /api/v1/admin/statistics` - Global statistics
  - Total users, active users, new users this month
  - Total LLM tokens used (all users)
  - Total masterplans created
  - Total storage used
  - Cost breakdown by user
- `GET /api/v1/admin/usage-by-user` - Usage report per user
- `PATCH /api/v1/admin/users/{user_id}/quotas` - Manually adjust quotas

**Protection**: All endpoints require `Depends(get_current_superuser)`

#### 8. Frontend UI Components
**Status**: NOT IMPLEMENTED

**Required React Components**:

**Authentication Pages**:
- `LoginPage.tsx` - Login form with email/password, "Forgot password?" link
- `RegisterPage.tsx` - Registration form with email, username, password, password confirmation
- `ForgotPasswordPage.tsx` - Email input to request password reset
- `ResetPasswordPage.tsx` - New password form (accessed via email link with token)
- `VerifyEmailPage.tsx` - Email verification confirmation (accessed via email link)

**User Profile**:
- `UserProfilePage.tsx` - Display user info and usage statistics
- `UsageStatsCard.tsx` - Reusable component showing current usage vs. quotas
  - LLM Tokens: 45,000 / 100,000 this month (with progress bar)
  - Masterplans: 5 / 50
  - Storage: 125 MB / 5 GB

**Navigation Updates**:
- Add user menu dropdown to header (username, profile, logout)
- Add usage badge to header showing token consumption

**Admin UI** (if time permits, otherwise Phase 7):
- `AdminDashboardPage.tsx` - Overview statistics
- `AdminUsersPage.tsx` - User management table
- `AdminUserDetailPage.tsx` - Individual user management

**Protected Routes**:
- Update React Router to require authentication for all pages
- Add `PrivateRoute` component that checks authentication
- Add `AdminRoute` component that checks superuser status
- Redirect unauthenticated users to login page

**State Management**:
- Auth context/provider for managing user state globally
- Token storage in httpOnly cookies (via API set-cookie headers)
- Automatic token refresh logic
- Global auth error handling (401/403 → redirect to login)

#### 9. Data Migration Strategy
**Status**: PLANNING REQUIRED

**Decision**: Start fresh (no existing data migration)

**Implications**:
- No need to migrate existing conversations or masterplans to new user accounts
- Clean slate for production deployment
- First user to register can be designated as superuser via database update

**Initial Superuser Creation**:
- Option 1: CLI command to create initial admin: `python -m src.cli.create_admin --email admin@example.com`
- Option 2: First registered user automatically becomes superuser (configurable via .env: `FIRST_USER_IS_ADMIN=true`)

#### 10. Email Service Integration
**Status**: NOT IMPLEMENTED

**Required**:
- Email service abstraction: `src/services/email_service.py`
- SMTP configuration in .env:
  - `SMTP_HOST` (e.g., smtp.sendgrid.net)
  - `SMTP_PORT` (587)
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `SMTP_FROM_EMAIL` (e.g., noreply@devmatrix.app)
  - `SMTP_FROM_NAME` (e.g., DevMatrix)

- Email templates (HTML + plain text):
  - `email_verification.html` - Verification link email
  - `password_reset.html` - Password reset link email
  - `welcome.html` - Welcome email after successful registration

- Email sending methods:
  - `send_verification_email(user_email, verification_token)`
  - `send_password_reset_email(user_email, reset_token)`
  - `send_welcome_email(user_email, username)`

**Recommendation**: Use SendGrid, AWS SES, or similar transactional email service

#### 11. Session Management Improvements
**Status**: NEEDS ENHANCEMENT

**Current**: JWT tokens returned in JSON response, client stores in localStorage

**Required**: Switch to httpOnly cookies for security

**Changes**:
- Update `/auth/login` and `/auth/register` endpoints to set httpOnly cookies instead of returning tokens in response
- Add `Set-Cookie` headers with:
  - `access_token` - httpOnly, Secure, SameSite=Strict, Max-Age=3600
  - `refresh_token` - httpOnly, Secure, SameSite=Strict, Max-Age=2592000
- Update middleware to read tokens from cookies instead of Authorization header
- Add CORS configuration to allow credentials
- Update frontend to send `credentials: 'include'` in fetch requests

**Fallback**: Support both cookie-based AND header-based auth for API flexibility

---

## Functional Requirements

### 1. User Authentication

#### 1.1 Registration Flow
**As a new user**, I want to register with email and password so that I can use DevMatrix.

**Requirements**:
- User provides: email, username, password
- Email must be valid format and unique
- Username must be 3-50 characters, alphanumeric + underscore/dash, unique
- Password must be 8-100 characters minimum
- Password is hashed with bcrypt (cost factor 12) before storage
- User account created with `is_active=True`, `is_superuser=False`
- Email verification behavior based on `EMAIL_VERIFICATION_REQUIRED` env var:
  - If `true`: `is_verified=False`, verification email sent
  - If `false` (default): `is_verified=True`, no email sent
- User workspace created at `/workspaces/{user_id}/`
- Default quotas assigned from `user_quotas` table or defaults
- Response includes access token, refresh token, and user info
- Welcome email sent (if email service configured)

**Edge Cases**:
- Email already exists → 400 error "Email already registered"
- Username already taken → 400 error "Username already taken"
- Weak password → 422 validation error with requirements
- Invalid email format → 422 validation error

#### 1.2 Email Verification
**As a registered user**, I want to verify my email so that my account is fully activated.

**Requirements**:
- Verification token generated: UUID, stored in `verification_token` column
- Verification email sent with link: `https://app.devmatrix.com/verify-email?token={token}`
- Link valid for 24 hours
- Clicking link calls `POST /api/v1/auth/verify-email` with token
- On success: `is_verified=True`, `verification_token=NULL`
- User can request new verification email via `POST /api/v1/auth/resend-verification`
- If `EMAIL_VERIFICATION_REQUIRED=true`, unverified users cannot create masterplans

**Edge Cases**:
- Token expired → 400 error "Verification link expired. Request new link."
- Invalid token → 400 error "Invalid verification link"
- Already verified → 200 success "Email already verified"

#### 1.3 Login Flow
**As a registered user**, I want to login with my credentials so that I can access my masterplans.

**Requirements**:
- User provides: email, password
- System validates credentials against database
- Password verified using bcrypt comparison
- Account must be active (`is_active=True`)
- `last_login_at` timestamp updated
- Access token (1 hour) and refresh token (30 days) generated
- Tokens set as httpOnly cookies in response
- User info returned in response body

**Edge Cases**:
- Invalid email → 401 error "Invalid email or password"
- Invalid password → 401 error "Invalid email or password"
- Account inactive → 403 error "Account is inactive"
- Too many failed login attempts (5 in 1 hour) → 429 error "Too many login attempts. Try again later."

#### 1.4 Token Refresh
**As an authenticated user**, I want my session to refresh automatically so that I don't have to login repeatedly.

**Requirements**:
- Frontend detects access token expiring soon (< 5 minutes remaining)
- Frontend calls `POST /api/v1/auth/refresh` with refresh token from cookie
- Refresh token validated and decoded
- New access token generated and set as cookie
- If refresh token expired → 401 error, redirect to login

#### 1.5 Logout
**As an authenticated user**, I want to logout so that my session ends securely.

**Requirements**:
- User clicks logout button
- Frontend calls `POST /api/v1/auth/logout`
- Server clears cookies by setting Max-Age=0
- Frontend clears any local auth state
- User redirected to login page

### 2. Email Verification

#### 2.1 Configurable Verification Requirement
**As a system administrator**, I want to configure whether email verification is required so that I can control user onboarding.

**Requirements**:
- Environment variable: `EMAIL_VERIFICATION_REQUIRED` (default: `false`)
- If `false`: Users created with `is_verified=True`, no verification email sent
- If `true`: Users created with `is_verified=False`, verification email sent
- Unverified users (when required) have restricted actions:
  - Cannot create masterplans
  - Cannot generate code
  - Can view profile and request new verification email

**Design Note**: This allows smooth initial rollout without email service, but enforces verification when email is configured.

#### 2.2 Verification Email Sending
**As a new user with verification required**, I want to receive a verification email so that I can activate my account.

**Requirements**:
- Email sent immediately after registration
- Email contains verification link with token
- Link format: `{FRONTEND_URL}/verify-email?token={verification_token}`
- Email template includes:
  - Welcome message
  - Clear call-to-action button "Verify Email"
  - Expiry notice (link valid for 24 hours)
  - Plain text and HTML versions
- Token is UUID v4, stored in database with `created_at` timestamp

#### 2.3 Resend Verification Email
**As an unverified user**, I want to resend my verification email if I didn't receive it.

**Requirements**:
- Endpoint: `POST /api/v1/auth/resend-verification` (requires authentication)
- Rate limit: 1 request per 2 minutes per user
- Generate new verification token (invalidate old one)
- Send new verification email
- Response: "Verification email sent. Please check your inbox."

**Edge Cases**:
- Already verified → 400 error "Email already verified"
- Too many requests → 429 error "Please wait 2 minutes before requesting another email"

### 3. Password Reset

#### 3.1 Request Password Reset
**As a user who forgot their password**, I want to request a password reset so that I can regain access.

**Requirements**:
- Endpoint: `POST /api/v1/auth/forgot-password` with email
- No authentication required
- Rate limit: 3 requests per hour per IP
- Process:
  - Look up user by email
  - Generate password reset token (UUID v4)
  - Store token in `password_reset_token` with `password_reset_expires` = 1 hour from now
  - Send password reset email
- Email contains reset link: `{FRONTEND_URL}/reset-password?token={reset_token}`
- Response: Always "If that email exists, a password reset link has been sent." (prevent email enumeration)

**Security Considerations**:
- Don't reveal whether email exists in system
- Tokens are single-use (deleted after use)
- Tokens expire after 1 hour
- Old tokens invalidated when new one requested

#### 3.2 Reset Password
**As a user with a reset token**, I want to set a new password so that I can login again.

**Requirements**:
- Endpoint: `POST /api/v1/auth/reset-password` with token and new_password
- Validate token exists and not expired
- Validate new password meets requirements (8+ chars)
- Hash new password with bcrypt
- Update `password_hash`, clear `password_reset_token` and `password_reset_expires`
- Invalidate all existing refresh tokens for this user (security best practice)
- Response: "Password reset successful. Please login with your new password."

**Edge Cases**:
- Token expired → 400 error "Reset link expired. Request a new one."
- Invalid token → 400 error "Invalid reset link"
- Weak password → 422 validation error

### 4. Multi-tenancy & Data Isolation

#### 4.1 User-specific Data Filtering
**As a user**, I want to see only my own masterplans and conversations so that my data is private.

**Requirements**:
- All database queries automatically filter by `user_id`
- Middleware extracts `user_id` from JWT token
- Queries like:
  ```python
  # Get user's masterplans
  masterplans = db.query(MasterPlan).filter(MasterPlan.user_id == current_user.user_id).all()

  # Get user's conversations
  conversations = db.query(Conversation).filter(Conversation.user_id == current_user.user_id).all()
  ```
- Users cannot access other users' data even with direct API requests
- Attempting to access another user's resource returns 404 (not 403, to prevent resource enumeration)

**Security**:
- SQLAlchemy scoping to always include `user_id` filter
- Never trust client-provided `user_id` - always use authenticated user's ID
- Audit logs for any data access (future enhancement)

#### 4.2 Workspace Isolation
**As a user**, I want my own isolated workspace so that my code is separate from other users.

**Requirements**:
- Workspace directory structure: `/workspaces/{user_id}/`
- Created automatically on user registration
- Workspace contents:
  - `projects/` - User's generated projects
  - `temp/` - Temporary files for generation
  - `.git/` - Git repository initialized per user
- All file operations scoped to user's workspace
- No cross-user file access possible
- Workspace size tracked for quota enforcement

**File Service Updates**:
```python
def get_user_workspace_path(user_id: UUID) -> Path:
    return Path(f"/workspaces/{user_id}")

def write_file(user_id: UUID, relative_path: str, content: str):
    workspace = get_user_workspace_path(user_id)
    full_path = workspace / relative_path
    # Ensure path doesn't escape workspace (security check)
    if not full_path.resolve().is_relative_to(workspace.resolve()):
        raise SecurityError("Path traversal attempt detected")
    full_path.write_text(content)
```

#### 4.3 Database Foreign Key Migration
**As a system**, I need all data tables to reference the users table so that data integrity is enforced.

**Required Migration**:
```sql
-- Conversations table (new table to be created)
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(300),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Modify existing tables
ALTER TABLE discovery_documents
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_discovery_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE masterplans
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_masterplan_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

-- Add indexes for performance
CREATE INDEX idx_conversations_user ON conversations(user_id);
```

**Note**: `ON DELETE CASCADE` ensures if user is deleted, all their data is deleted. For soft-delete approach, use trigger instead.

### 5. Usage Tracking & Quotas

#### 5.1 LLM Token Tracking
**As a system**, I want to track all LLM token usage per user so that I can enforce quotas and calculate costs.

**Requirements**:
- Track every LLM API call:
  - `user_id`
  - `model` (e.g., "claude-sonnet-4.5")
  - `input_tokens`
  - `output_tokens`
  - `cached_tokens` (for prompt caching)
  - `cost_usd` (calculated from model pricing)
  - `timestamp`
- Aggregate monthly totals in `user_usage` table
- Update on every LLM call via decorator or middleware
- Check quota before LLM call:
  - If `current_month_tokens >= quota.llm_tokens_monthly_limit` → 429 error "Monthly token quota exceeded"

**Implementation**:
```python
@track_llm_usage
async def call_llm(user_id: UUID, prompt: str, model: str):
    # Check quota first
    quota_service.check_quota(user_id, "tokens")

    # Make LLM call
    response = await anthropic.messages.create(...)

    # Tracking happens in decorator
    return response
```

#### 5.2 Masterplan Creation Tracking
**As a system**, I want to track masterplan creation per user so that I can enforce limits.

**Requirements**:
- Increment `masterplans_created` counter in `user_usage` table
- Check quota before creating masterplan:
  - If `user_masterplans_count >= quota.masterplans_limit` → 429 error "Masterplan limit reached"
- Allow admins to bypass limits

#### 5.3 Storage Tracking
**As a system**, I want to track workspace storage usage per user so that I can enforce disk quotas.

**Requirements**:
- Background job calculates workspace directory size daily
- Update `storage_bytes` in `user_usage` table
- Check quota on file write operations:
  - If `current_storage >= quota.storage_bytes_limit` → 413 error "Storage quota exceeded"
- Display human-readable storage (e.g., "125 MB / 5 GB") in frontend

**Background Job**:
```python
def calculate_user_storage(user_id: UUID):
    workspace_path = get_user_workspace_path(user_id)
    total_size = sum(f.stat().st_size for f in workspace_path.rglob('*') if f.is_file())
    usage_service.update_storage(user_id, total_size)
```

#### 5.4 Usage Statistics API
**As a user**, I want to view my current usage statistics so that I know how much quota I've consumed.

**Endpoint**: `GET /api/v1/users/me/usage`

**Response**:
```json
{
  "month": "2025-10",
  "llm_tokens_used": 45000,
  "llm_tokens_limit": 100000,
  "llm_tokens_percent": 45.0,
  "llm_cost_usd": 1.23,
  "masterplans_created": 5,
  "masterplans_limit": 50,
  "storage_bytes": 131072000,
  "storage_limit_bytes": 5368709120,
  "storage_human": "125 MB / 5 GB",
  "storage_percent": 2.4
}
```

#### 5.5 Configurable Per-User Quotas
**As an admin**, I want to configure different quotas for different users so that I can offer tiered plans.

**Requirements**:
- `user_quotas` table with per-user overrides
- Default quotas (applied to all new users):
  - `llm_tokens_monthly_limit`: 1,000,000 (1M tokens/month)
  - `masterplans_limit`: 50
  - `storage_bytes_limit`: 5 GB (5,368,709,120 bytes)
  - `api_calls_per_minute`: 30
- Admin can override any quota via API:
  - `PATCH /api/v1/admin/users/{user_id}/quotas`
  ```json
  {
    "llm_tokens_monthly_limit": 10000000,  // 10M tokens for premium user
    "masterplans_limit": null,  // Unlimited masterplans
    "storage_bytes_limit": 53687091200  // 50 GB
  }
  ```
- `null` value means unlimited for that quota

### 6. Session Management

#### 6.1 httpOnly Cookie Storage (Recommended)
**As a user**, I want my authentication tokens stored securely so that they can't be stolen by XSS attacks.

**Requirements**:
- Access token stored in httpOnly cookie:
  - Name: `access_token`
  - httpOnly: true (JavaScript can't access)
  - Secure: true (HTTPS only in production)
  - SameSite: Strict (CSRF protection)
  - Max-Age: 3600 (1 hour)
  - Path: /api
- Refresh token stored in httpOnly cookie:
  - Name: `refresh_token`
  - Same flags as access token
  - Max-Age: 2592000 (30 days)
- CORS configured to allow credentials:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://app.devmatrix.com"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"]
  )
  ```

**Frontend Changes**:
- All API requests include `credentials: 'include'`
- No token storage in localStorage or sessionStorage
- Tokens automatically sent with every request

#### 6.2 Automatic Token Refresh
**As a user**, I want my session to stay active so that I don't get logged out while working.

**Requirements**:
- Frontend checks access token expiry before each request
- If token expires in < 5 minutes, refresh it first
- Refresh logic:
  ```typescript
  async function ensureValidToken() {
    const tokenExpiry = getTokenExpiry(); // Read from JWT
    const now = Date.now();

    if (tokenExpiry - now < 5 * 60 * 1000) { // < 5 minutes
      await refreshToken();
    }
  }

  async function refreshToken() {
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include'
    });

    if (!response.ok) {
      // Refresh token expired, redirect to login
      redirectToLogin();
    }
  }
  ```
- Refresh happens silently in background
- If refresh fails (expired refresh token), redirect to login

#### 6.3 Token Expiry Configuration
**As a system administrator**, I want to configure token expiry times so that I can balance security and usability.

**Requirements**:
- Environment variables:
  - `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60)
  - `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (default: 30)
- Shorter access tokens = more secure, more frequent refreshes
- Longer refresh tokens = better UX, stay logged in longer
- Recommended production values:
  - Access token: 15-60 minutes
  - Refresh token: 7-30 days

### 7. Admin Features

#### 7.1 User Management
**As an admin**, I want to view all users so that I can manage the system.

**Endpoint**: `GET /api/v1/admin/users`

**Query Parameters**:
- `page` (default: 1)
- `per_page` (default: 20, max: 100)
- `sort_by` (options: created_at, email, username, last_login_at)
- `sort_order` (asc/desc)
- `filter_active` (true/false/all)
- `search` (search email or username)

**Response**:
```json
{
  "users": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "username": "john_doe",
      "is_active": true,
      "is_superuser": false,
      "is_verified": true,
      "created_at": "2025-10-01T10:00:00Z",
      "last_login_at": "2025-10-22T14:30:00Z",
      "usage_summary": {
        "llm_tokens_this_month": 45000,
        "masterplans_count": 5,
        "storage_mb": 125
      }
    }
  ],
  "total": 156,
  "page": 1,
  "per_page": 20,
  "total_pages": 8
}
```

#### 7.2 Deactivate User
**As an admin**, I want to deactivate user accounts so that I can handle abuse.

**Endpoint**: `PATCH /api/v1/admin/users/{user_id}`

**Request**:
```json
{
  "is_active": false
}
```

**Effects**:
- User's `is_active` set to `false`
- User cannot login (gets 403 error)
- Existing sessions remain valid until tokens expire (or implement token blacklist)
- User's data remains in database (soft delete)

**Reactivation**: Same endpoint with `"is_active": true`

#### 7.3 View User Details
**As an admin**, I want to view detailed user information so that I can debug issues.

**Endpoint**: `GET /api/v1/admin/users/{user_id}`

**Response**:
```json
{
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "john_doe",
    "is_active": true,
    "is_superuser": false,
    "is_verified": true,
    "created_at": "2025-10-01T10:00:00Z",
    "last_login_at": "2025-10-22T14:30:00Z"
  },
  "quotas": {
    "llm_tokens_monthly_limit": 1000000,
    "masterplans_limit": 50,
    "storage_bytes_limit": 5368709120
  },
  "usage_current_month": {
    "llm_tokens_used": 45000,
    "llm_cost_usd": 1.23,
    "masterplans_created": 5,
    "storage_bytes": 131072000
  },
  "statistics": {
    "total_masterplans": 12,
    "total_conversations": 34,
    "total_llm_cost_usd": 5.67,
    "workspace_path": "/workspaces/{user_id}"
  }
}
```

#### 7.4 Adjust User Quotas
**As an admin**, I want to manually adjust user quotas so that I can handle special cases.

**Endpoint**: `PATCH /api/v1/admin/users/{user_id}/quotas`

**Request**:
```json
{
  "llm_tokens_monthly_limit": 10000000,
  "masterplans_limit": null,
  "storage_bytes_limit": 53687091200
}
```

**Effects**:
- Updates or creates record in `user_quotas` table
- Changes take effect immediately
- User can now exceed previous limits

#### 7.5 Impersonate User
**As an admin**, I want to impersonate users so that I can debug their issues.

**Endpoint**: `POST /api/v1/admin/impersonate/{user_id}`

**Response**:
```json
{
  "access_token": "special_impersonation_token",
  "refresh_token": "special_refresh_token",
  "impersonating": {
    "user_id": "target_user_id",
    "email": "target@example.com",
    "username": "target_user"
  },
  "admin": {
    "user_id": "admin_user_id",
    "email": "admin@example.com"
  }
}
```

**Security Requirements**:
- Token includes claim: `"impersonating": true`
- Token includes admin's user_id for audit trail
- All actions logged with both admin and impersonated user IDs
- Impersonation token valid for 1 hour max
- Cannot impersonate other admins
- Display warning banner in UI: "You are impersonating user@example.com"

#### 7.6 Global Statistics
**As an admin**, I want to view global system statistics so that I can monitor growth.

**Endpoint**: `GET /api/v1/admin/statistics`

**Response**:
```json
{
  "users": {
    "total": 156,
    "active": 142,
    "new_this_month": 23,
    "new_today": 3
  },
  "usage_this_month": {
    "total_llm_tokens": 4500000,
    "total_llm_cost_usd": 123.45,
    "total_masterplans_created": 89,
    "total_storage_gb": 12.5
  },
  "usage_all_time": {
    "total_llm_tokens": 45000000,
    "total_llm_cost_usd": 1234.56,
    "total_masterplans": 567,
    "total_conversations": 1234
  },
  "top_users": [
    {
      "user_id": "uuid",
      "email": "poweruser@example.com",
      "llm_tokens_this_month": 500000,
      "llm_cost_this_month_usd": 15.67
    }
  ]
}
```

### 8. Rate Limiting

#### 8.1 Authentication Endpoint Limits
**As a system**, I want to rate limit authentication endpoints so that I prevent brute force attacks.

**Requirements**:
- Endpoints: `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/reset-password`
- Limit: 5 requests per minute per IP address
- Response when exceeded:
  ```json
  {
    "error": "Too many requests",
    "retry_after": 45  // seconds
  }
  ```
  Status: 429 Too Many Requests
- Headers:
  - `X-RateLimit-Limit: 5`
  - `X-RateLimit-Remaining: 0`
  - `X-RateLimit-Reset: 1698012345` (Unix timestamp)
  - `Retry-After: 45` (seconds)

**Implementation**: Use Redis to store IP-based counters with TTL

#### 8.2 API Endpoint Limits
**As a system**, I want to rate limit API endpoints per user so that I prevent abuse.

**Requirements**:
- Chat/conversation endpoints: 30 requests per minute per user
- Masterplan endpoints: 20 requests per minute per user
- General API endpoints: 60 requests per minute per user
- Admin endpoints: 100 requests per minute per admin
- Key: `user_id` from authenticated JWT
- Same response format and headers as authentication limits

**Quota-based Rate Limiting**:
- Users can have custom `api_calls_per_minute` in `user_quotas` table
- Premium users might have 100 req/min, free users 30 req/min

#### 8.3 LLM Token Rate Limiting
**As a system**, I want to prevent users from exceeding monthly token quotas so that costs stay controlled.

**Requirements**:
- Check before every LLM call: `current_month_tokens + estimated_tokens <= quota`
- If exceeded:
  ```json
  {
    "error": "Monthly token quota exceeded",
    "quota": 1000000,
    "used": 1000234,
    "reset_date": "2025-11-01T00:00:00Z"
  }
  ```
  Status: 429 Too Many Requests
- Allow admin override: Admins can make LLM calls on behalf of users even if quota exceeded
- Grace period: Allow 5% overage (1.05M tokens if limit is 1M) to avoid hard cutoffs mid-operation

### 9. Frontend UI Requirements

#### 9.1 Login Page
**As a user**, I want to login with my credentials so that I can access DevMatrix.

**Requirements**:
- URL: `/login`
- Form fields:
  - Email (type=email, required)
  - Password (type=password, required)
  - "Remember me" checkbox (extends refresh token to 90 days)
- Buttons:
  - "Login" (primary button)
  - "Forgot password?" (link to `/forgot-password`)
  - "Create account" (link to `/register`)
- Validation:
  - Client-side email format validation
  - Show error messages from API (invalid credentials, account inactive)
- Loading state: Disable form and show spinner during login
- Success: Redirect to `/dashboard` or previously attempted page
- Design: Match existing DevMatrix UI (dark mode, Tailwind CSS)

#### 9.2 Registration Page
**As a new user**, I want to register an account so that I can use DevMatrix.

**Requirements**:
- URL: `/register`
- Form fields:
  - Email (type=email, required)
  - Username (type=text, required, 3-50 chars, alphanumeric + _-)
  - Password (type=password, required, 8+ chars)
  - Confirm Password (type=password, must match password)
- Password strength indicator (weak/medium/strong)
- Buttons:
  - "Create Account" (primary)
  - "Already have an account? Login" (link to `/login`)
- Validation:
  - Client-side validation for all fields
  - Show password requirements checklist:
    - ✓ At least 8 characters
    - ✓ Passwords match
  - Show API errors (email exists, username taken)
- Success behavior:
  - If `EMAIL_VERIFICATION_REQUIRED=false`: Auto-login and redirect to `/dashboard`
  - If `EMAIL_VERIFICATION_REQUIRED=true`: Show message "Verification email sent. Please check your inbox." and redirect to `/verify-email-pending`

#### 9.3 Email Verification Pages
**As a user**, I want clear feedback on email verification so that I know what to do.

**Pending Verification Page** (`/verify-email-pending`):
- Message: "Please verify your email address"
- Subtitle: "We sent a verification link to {email}"
- Button: "Resend verification email" (with 2-minute cooldown)
- Note: "Didn't receive the email? Check your spam folder."

**Verification Success Page** (`/verify-email?token={token}`):
- On load: Call API to verify token
- Success: Show checkmark icon, "Email verified successfully!", button "Go to Dashboard"
- Error: Show error message, button "Request new verification email"

#### 9.4 Password Reset Pages
**Forgot Password Page** (`/forgot-password`):
- Form field: Email (required)
- Button: "Send Reset Link"
- Success: "If that email exists, a reset link has been sent. Please check your inbox."
- Link: "Remember your password? Login"

**Reset Password Page** (`/reset-password?token={token}`):
- Form fields:
  - New Password (required, 8+ chars)
  - Confirm New Password (must match)
- Password strength indicator
- Button: "Reset Password"
- Success: "Password reset successfully! Please login.", redirect to `/login` after 3 seconds
- Error (expired token): "Reset link expired. Please request a new one.", button to `/forgot-password`

#### 9.5 User Profile & Usage Dashboard
**As a user**, I want to view my account info and usage so that I know my current quota status.

**Profile Page** (`/profile`):

**Account Section**:
- Email: user@example.com (verified ✓)
- Username: john_doe
- Member since: October 1, 2025
- Last login: October 22, 2025 at 2:30 PM
- Button: "Change Password"
- Button: "Logout"

**Usage Statistics Section**:
- LLM Tokens This Month:
  - Progress bar: 45,000 / 100,000 (45%)
  - Color: Green if < 80%, Yellow if 80-95%, Red if > 95%
  - Text: "45K tokens used of 100K monthly quota"
  - Subtext: "Quota resets on November 1, 2025"

- Masterplans:
  - Count: 5 / 50
  - Text: "5 masterplans created (50 max)"

- Storage:
  - Progress bar: 125 MB / 5 GB (2.4%)
  - Text: "125 MB used of 5 GB storage"

**Cost This Month** (if enabled):
- Estimated cost: $1.23
- Text: "Based on your LLM usage"

**Action Links**:
- "View billing history" (future)
- "Upgrade plan" (future)

#### 9.6 Navigation & Header Updates
**As a user**, I want to see my account status in the header so that I'm aware of my usage.

**Header Changes**:
- Replace "Login" button with user menu dropdown
- User menu trigger: Avatar icon + username
- Dropdown menu items:
  - "Profile"
  - "Usage & Billing"
  - "Settings"
  - Divider
  - "Logout"

**Usage Badge** (in header):
- Icon: Token/lightning bolt icon
- Text: "45K / 100K" (current tokens / limit)
- Tooltip: "LLM tokens used this month. Click to view details."
- Click: Navigate to `/profile#usage`
- Color coding:
  - Gray: < 50%
  - Blue: 50-80%
  - Yellow: 80-95%
  - Red: > 95%

#### 9.7 Protected Routes
**As a system**, I want to protect routes so that unauthenticated users are redirected to login.

**Requirements**:
- All routes except `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email` require authentication
- Protected route component checks for valid access token
- If not authenticated: Redirect to `/login?redirect={current_path}`
- After successful login: Redirect back to originally requested page

**Admin Routes**:
- Routes starting with `/admin/` require `is_superuser=true`
- If not superuser: Show 403 error page "Access denied. Admin privileges required."

**Implementation**:
```typescript
function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to={`/login?redirect=${location.pathname}`} />;
  }

  return children;
}

function AdminRoute({ children }) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (!user.is_superuser) {
    return <ForbiddenPage />;
  }

  return children;
}
```

#### 9.8 Auth Context/Provider
**As a frontend**, I need centralized auth state so that all components can access user info.

**Requirements**:
- React Context: `AuthContext` with provider `AuthProvider`
- State:
  - `user` (User object or null)
  - `isAuthenticated` (boolean)
  - `isLoading` (boolean, true during initial load)
- Methods:
  - `login(email, password)`
  - `logout()`
  - `refreshToken()`
  - `checkAuth()` (verify token on app load)
- Auto-refresh logic:
  - Check token expiry every 1 minute
  - Refresh if < 5 minutes remaining
- Error handling:
  - 401 errors globally redirect to login
  - 403 errors show access denied message

**Usage**:
```typescript
function SomeComponent() {
  const { user, isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return <div>Welcome {user.username}!</div>;
}
```

---

## Technical Requirements

### Database Changes

#### New Tables

**1. user_quotas**
```sql
CREATE TABLE user_quotas (
    quota_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    llm_tokens_monthly_limit INTEGER,  -- NULL = unlimited
    masterplans_limit INTEGER,
    storage_bytes_limit BIGINT,
    api_calls_per_minute INTEGER DEFAULT 30,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_quotas_user ON user_quotas(user_id);
```

**2. user_usage**
```sql
CREATE TABLE user_usage (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    month DATE NOT NULL,  -- First day of month, e.g., '2025-10-01'

    llm_tokens_used INTEGER DEFAULT 0,
    llm_cost_usd NUMERIC(10, 4) DEFAULT 0.0,
    masterplans_created INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, month)
);

CREATE INDEX idx_user_usage_user_month ON user_usage(user_id, month);
CREATE INDEX idx_user_usage_month ON user_usage(month);
```

**3. conversations** (if not already created)
```sql
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(300),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_created ON conversations(created_at);
```

**4. messages** (if not already created)
```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);
```

**5. password_reset_tokens** (alternative: add columns to users table)
```sql
-- Option 1: Add to users table (recommended for simplicity)
ALTER TABLE users ADD COLUMN password_reset_token UUID;
ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP;

-- Option 2: Separate table (better for audit trail)
CREATE TABLE password_reset_tokens (
    token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token UUID UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_password_reset_token ON password_reset_tokens(token);
CREATE INDEX idx_password_reset_user ON password_reset_tokens(user_id);
```

**6. email_verification_tokens** (alternative: add columns to users table)
```sql
-- Option 1: Add to users table (recommended)
ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN verification_token UUID;
ALTER TABLE users ADD COLUMN verification_token_created_at TIMESTAMP;

-- Option 2: Separate table
CREATE TABLE email_verification_tokens (
    token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token UUID UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### Table Modifications

**1. Modify discovery_documents**
```sql
-- Change user_id from String to UUID FK
ALTER TABLE discovery_documents
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_discovery_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
```

**2. Modify masterplans**
```sql
-- Change user_id from String to UUID FK
ALTER TABLE masterplans
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_masterplan_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
```

### API Changes

#### New Endpoints

**Authentication**:
- `POST /api/v1/auth/verify-email` - Verify email with token
- `POST /api/v1/auth/resend-verification` - Resend verification email
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token

**User Management**:
- `GET /api/v1/users/me` - Get current user profile (duplicate of /auth/me, for consistency)
- `PATCH /api/v1/users/me` - Update current user profile
- `GET /api/v1/users/me/usage` - Get current user's usage statistics

**Admin**:
- `GET /api/v1/admin/users` - List all users (paginated)
- `GET /api/v1/admin/users/{user_id}` - Get user details
- `PATCH /api/v1/admin/users/{user_id}` - Update user (activate/deactivate)
- `DELETE /api/v1/admin/users/{user_id}` - Delete user
- `PATCH /api/v1/admin/users/{user_id}/quotas` - Update user quotas
- `POST /api/v1/admin/impersonate/{user_id}` - Impersonate user
- `GET /api/v1/admin/statistics` - Global statistics
- `GET /api/v1/admin/usage-by-user` - Usage report per user

#### Modified Endpoints

All existing endpoints that create or query data need to:
1. Require authentication (add `current_user: User = Depends(get_current_active_user)`)
2. Filter by `user_id` automatically
3. Check quotas before creation operations

**Example**:
```python
@router.post("/api/v1/masterplans")
async def create_masterplan(
    request: CreateMasterplanRequest,
    current_user: User = Depends(get_current_active_user)
):
    # Check quota
    quota_service.check_quota(current_user.user_id, "masterplans")

    # Create masterplan with user_id
    masterplan = await masterplan_service.create(
        user_id=current_user.user_id,
        ...
    )

    # Track usage
    await usage_service.track_masterplan_created(current_user.user_id)

    return masterplan

@router.get("/api/v1/masterplans")
async def list_masterplans(
    current_user: User = Depends(get_current_active_user)
):
    # Automatically filter by user_id
    masterplans = await masterplan_service.list_by_user(current_user.user_id)
    return masterplans
```

### Frontend Components

**New Components**:
- `LoginPage.tsx`
- `RegisterPage.tsx`
- `ForgotPasswordPage.tsx`
- `ResetPasswordPage.tsx`
- `VerifyEmailPage.tsx`
- `VerifyEmailPendingPage.tsx`
- `UserProfilePage.tsx`
- `UsageStatsCard.tsx` (reusable)
- `UserMenu.tsx` (dropdown in header)
- `UsageBadge.tsx` (token usage in header)
- `PrivateRoute.tsx` (wrapper for protected routes)
- `AdminRoute.tsx` (wrapper for admin routes)
- `AuthProvider.tsx` (context provider)
- `PasswordStrengthIndicator.tsx`

**Modified Components**:
- `App.tsx` - Add AuthProvider, update routes
- `Header.tsx` - Add UserMenu and UsageBadge
- All pages - Wrap with PrivateRoute

### Services

**New Service Files**:
- `src/services/email_service.py` - Email sending abstraction
- `src/services/password_reset_service.py` - Password reset logic
- `src/services/email_verification_service.py` - Email verification logic
- `src/services/usage_tracking_service.py` - Usage tracking and quota enforcement
- `src/services/quota_service.py` - Quota checking and enforcement
- `src/services/workspace_service.py` - User workspace management
- `src/services/admin_service.py` - Admin-specific operations

**Modified Services**:
- `src/services/masterplan_service.py` - Add user_id parameter, quota checks
- `src/services/chat_service.py` - Add user_id filtering
- All LLM-calling services - Add usage tracking

### Configuration

**New Environment Variables**:
```bash
# Email Configuration
EMAIL_VERIFICATION_REQUIRED=false
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxxxx
SMTP_FROM_EMAIL=noreply@devmatrix.app
SMTP_FROM_NAME=DevMatrix

# Frontend URL (for email links)
FRONTEND_URL=https://app.devmatrix.com

# Default Quotas
DEFAULT_LLM_TOKENS_MONTHLY=1000000
DEFAULT_MASTERPLANS_LIMIT=50
DEFAULT_STORAGE_BYTES_LIMIT=5368709120
DEFAULT_API_CALLS_PER_MINUTE=30

# Admin
FIRST_USER_IS_ADMIN=true

# Rate Limiting
RATE_LIMIT_AUTH_PER_MINUTE=5
RATE_LIMIT_API_PER_MINUTE=30
RATE_LIMIT_ADMIN_PER_MINUTE=100

# Session
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

### Testing Requirements

**New Test Files**:
- `tests/services/test_auth_service.py` (already exists, extend)
- `tests/services/test_email_service.py`
- `tests/services/test_password_reset_service.py`
- `tests/services/test_usage_tracking_service.py`
- `tests/services/test_quota_service.py`
- `tests/api/test_auth_endpoints.py` (already exists, extend)
- `tests/api/test_admin_endpoints.py`
- `tests/integration/test_multi_tenancy.py`
- `tests/integration/test_rate_limiting.py`

**Test Coverage Goals**:
- Unit tests: 90%+ coverage for all new services
- Integration tests: Full auth flow (register → verify → login → use API → logout)
- Multi-tenancy tests: Ensure users can't access each other's data
- Rate limiting tests: Verify limits enforced correctly
- Admin tests: Verify admin-only endpoints are protected

---

## Non-Functional Requirements

### Security

#### 1. Password Security
- Bcrypt hashing with cost factor 12 (already implemented)
- Minimum 8 characters, no maximum (allow passphrases)
- No password strength requirements beyond length (users can choose weak passwords, but we recommend strong ones)
- Password reset tokens single-use and expire after 1 hour
- Email verification tokens expire after 24 hours

#### 2. Token Security
- JWT tokens signed with HS256 (already implemented)
- Access tokens short-lived (1 hour) to limit exposure
- Refresh tokens long-lived (30 days) but stored securely in httpOnly cookies
- Token payload includes: user_id, email, username, is_superuser, type (access/refresh)
- No sensitive data in JWT (no password hashes, payment info, etc.)
- Token blacklisting for logout (optional, requires Redis)

#### 3. Session Security
- httpOnly cookies prevent XSS attacks from stealing tokens
- Secure flag ensures cookies only sent over HTTPS (production)
- SameSite=Strict prevents CSRF attacks
- CORS configured to allow only trusted frontend origins
- Credentials required for all API calls

#### 4. API Security
- All endpoints (except auth) require valid JWT
- Rate limiting prevents brute force and DoS attacks
- Input validation via Pydantic models
- SQL injection prevented by SQLAlchemy ORM
- Path traversal protection in file operations
- User isolation: Users can only access their own resources

#### 5. Email Security
- Password reset links expire after 1 hour
- Verification links expire after 24 hours
- Don't reveal whether email exists (forgot password)
- Rate limit email sending to prevent spam
- Use SPF, DKIM, DMARC for email authentication

### Performance

#### 1. Database Performance
- Indexes on all foreign keys (user_id columns)
- Compound index on user_usage(user_id, month)
- Connection pooling (SQLAlchemy default)
- Query optimization: Use select_related for joins
- Pagination for all list endpoints (max 100 items per page)

#### 2. API Performance
- Response time targets:
  - Auth endpoints: < 200ms (excluding email sending)
  - User data endpoints: < 100ms
  - Admin endpoints: < 500ms
- Caching:
  - User quotas cached in Redis (5 minute TTL)
  - Usage statistics cached (1 minute TTL)
- Rate limiting uses Redis for fast counter checks
- WebSocket connections maintain their own auth state (no re-verification on every message)

#### 3. Storage Performance
- Workspace size calculation runs async (background job)
- Don't block API requests on storage calculation
- Update storage usage daily, not on every file write

### Scalability

#### 1. Horizontal Scaling
- Stateless JWT allows multiple API servers
- Rate limiting uses Redis (shared state)
- Session data in database, not in-memory
- No server-side session storage

#### 2. Database Scaling
- User data partitionable by user_id
- Usage data partitionable by month
- Indexes support efficient filtering
- Soft delete instead of hard delete (preserve foreign key integrity)

#### 3. Storage Scaling
- User workspaces isolated (can be on different volumes)
- S3/object storage integration possible (future)
- Workspace size tracking allows proactive cleanup

### Reliability

#### 1. Error Handling
- All API endpoints return consistent error format:
  ```json
  {
    "error": "Error message",
    "detail": "Additional details",
    "code": "ERROR_CODE"
  }
  ```
- Log all errors with context (user_id, endpoint, timestamp)
- Graceful degradation: If email service down, allow registration but warn user

#### 2. Data Integrity
- Foreign key constraints ensure referential integrity
- Unique constraints on email, username
- Database transactions for multi-step operations
- Cascading deletes for user data cleanup

#### 3. Monitoring
- Log all authentication events (login, logout, failed attempts)
- Track rate limit violations
- Monitor quota usage and alert when users exceed 90%
- Track API error rates and slow endpoints

---

## User Stories

### User Registration & Login

**US-1: User Registration**
- **As a new user**, I want to register with my email and password so that I can start using DevMatrix.
- **Acceptance Criteria**:
  - User can access `/register` page
  - User enters email, username, password
  - System validates input and shows errors if invalid
  - System checks if email/username already exists
  - On success, user is logged in automatically (if verification not required)
  - If verification required, user sees "Check your email" message

**US-2: Email Verification**
- **As a new user with verification required**, I want to verify my email so that I can use all features.
- **Acceptance Criteria**:
  - User receives verification email within 1 minute
  - Email contains clickable verification link
  - Clicking link verifies email and shows success message
  - User can then login and use all features
  - User can request new verification email if needed

**US-3: User Login**
- **As a registered user**, I want to login with my credentials so that I can access my masterplans.
- **Acceptance Criteria**:
  - User can access `/login` page
  - User enters email and password
  - System validates credentials
  - On success, user is redirected to dashboard
  - Invalid credentials show clear error message
  - Inactive account shows "Account disabled" message

**US-4: Password Reset**
- **As a user who forgot their password**, I want to reset it via email so that I can regain access.
- **Acceptance Criteria**:
  - User clicks "Forgot password?" link
  - User enters email address
  - User receives password reset email (if email exists)
  - Email contains reset link valid for 1 hour
  - User clicks link and enters new password
  - User can then login with new password

### Multi-tenancy & Data Isolation

**US-5: Private Masterplans**
- **As a user**, I want to see only my own masterplans so that my work is private.
- **Acceptance Criteria**:
  - User's dashboard shows only their masterplans
  - Attempting to access another user's masterplan returns 404
  - No leakage of other users' data in any API endpoint

**US-6: Private Conversations**
- **As a user**, I want my chat conversations to be private so that my ideas are protected.
- **Acceptance Criteria**:
  - User sees only their own conversation history
  - Cannot access other users' conversations via API

**US-7: Isolated Workspace**
- **As a user**, I want my own workspace so that my code doesn't interfere with others.
- **Acceptance Criteria**:
  - User's generated code goes to `/workspaces/{user_id}/`
  - User cannot access other users' workspaces
  - Git repository initialized in user's workspace
  - Workspace created automatically on registration

### Usage Tracking & Quotas

**US-8: View Usage Statistics**
- **As a user**, I want to see my current usage so that I know how much quota I've consumed.
- **Acceptance Criteria**:
  - User can view usage on profile page
  - Shows LLM tokens used this month with progress bar
  - Shows masterplans created count
  - Shows storage usage
  - Shows when quota resets (first of next month)

**US-9: Quota Enforcement - Tokens**
- **As a system**, I want to prevent users from exceeding token quotas so that costs are controlled.
- **Acceptance Criteria**:
  - Before LLM call, system checks if user has quota remaining
  - If quota exceeded, API returns 429 error
  - Error message shows usage and reset date
  - User can still use non-LLM features

**US-10: Quota Enforcement - Masterplans**
- **As a system**, I want to limit masterplan creation so that abuse is prevented.
- **Acceptance Criteria**:
  - Before creating masterplan, system checks quota
  - If limit reached, show error with upgrade CTA (future)
  - Admin can override limits

**US-11: Quota Enforcement - Storage**
- **As a system**, I want to limit workspace storage so that disk usage is controlled.
- **Acceptance Criteria**:
  - System tracks workspace size
  - Before file write, check if quota exceeded
  - If exceeded, show error message
  - User can delete old projects to free space

### Admin Features

**US-12: View All Users**
- **As an admin**, I want to see all registered users so that I can manage the system.
- **Acceptance Criteria**:
  - Admin can access `/admin/users` page
  - Page shows all users with email, username, created date, last login
  - Page supports search, filtering, sorting
  - Page is paginated (20 users per page)

**US-13: Deactivate User**
- **As an admin**, I want to deactivate abusive users so that they can't use the system.
- **Acceptance Criteria**:
  - Admin can click "Deactivate" on user row
  - User's `is_active` set to false
  - User cannot login (gets "Account inactive" error)
  - Admin can reactivate user later

**US-14: View User Details**
- **As an admin**, I want to see detailed user information so that I can debug issues.
- **Acceptance Criteria**:
  - Admin clicks on user to see detail page
  - Shows all user info, quotas, usage statistics
  - Shows workspace path and size
  - Shows total LLM cost for this user

**US-15: Adjust User Quotas**
- **As an admin**, I want to manually adjust quotas so that I can handle special cases.
- **Acceptance Criteria**:
  - Admin can click "Edit Quotas" on user detail page
  - Shows form with current quotas
  - Admin can change token limit, masterplan limit, storage limit
  - Changes take effect immediately
  - Setting to null = unlimited

**US-16: Impersonate User**
- **As an admin**, I want to impersonate users so that I can debug their issues.
- **Acceptance Criteria**:
  - Admin clicks "Impersonate" button
  - Admin is logged in as that user
  - UI shows warning banner "You are impersonating user@example.com"
  - Admin can perform any action as that user
  - Admin can exit impersonation to return to their account

**US-17: View Global Statistics**
- **As an admin**, I want to see system-wide statistics so that I can monitor growth.
- **Acceptance Criteria**:
  - Admin dashboard shows:
    - Total users, active users, new users this month
    - Total LLM tokens used (all users)
    - Total LLM cost this month
    - Total masterplans created
    - Top users by token usage
  - Statistics updated in real-time or cached for 5 minutes

### Session Management

**US-18: Stay Logged In**
- **As a user**, I want my session to stay active so that I don't have to login repeatedly.
- **Acceptance Criteria**:
  - User stays logged in for up to 30 days (refresh token expiry)
  - Access token refreshes automatically before expiry
  - User doesn't see login screen unless inactive for 30 days

**US-19: Secure Logout**
- **As a user**, I want to logout so that others can't access my account on shared computer.
- **Acceptance Criteria**:
  - User clicks "Logout" in menu
  - Tokens are cleared from cookies
  - User is redirected to login page
  - Attempting to access protected pages redirects to login

### Rate Limiting

**US-20: Prevent Brute Force**
- **As a system**, I want to rate limit login attempts so that brute force attacks are prevented.
- **Acceptance Criteria**:
  - After 5 failed login attempts from same IP in 1 minute, return 429 error
  - Error message shows "Too many login attempts. Try again in X seconds."
  - Rate limit resets after 1 minute
  - Successful login resets counter

**US-21: Prevent API Abuse**
- **As a system**, I want to rate limit API calls so that abuse is prevented.
- **Acceptance Criteria**:
  - Users limited to 30 API calls per minute
  - After limit exceeded, return 429 error
  - Response headers show limit and remaining calls
  - Premium users can have higher limits (configurable)

---

## Acceptance Criteria

### Authentication

**Registration**:
- [ ] User can register with valid email, username, password
- [ ] System rejects duplicate email with clear error message
- [ ] System rejects duplicate username with clear error message
- [ ] Password is hashed with bcrypt before storage
- [ ] User account created with `is_active=True`, `is_superuser=False`
- [ ] Email verification behavior controlled by `EMAIL_VERIFICATION_REQUIRED` env var
- [ ] User workspace created at `/workspaces/{user_id}/`
- [ ] Default quotas assigned from configuration

**Email Verification**:
- [ ] If `EMAIL_VERIFICATION_REQUIRED=true`, verification email sent on registration
- [ ] Verification email contains valid link with token
- [ ] Clicking link verifies email (`is_verified=True`)
- [ ] Invalid/expired token shows error message
- [ ] User can resend verification email (rate limited)

**Login**:
- [ ] User can login with valid email and password
- [ ] Invalid credentials return 401 error
- [ ] Inactive account returns 403 error
- [ ] `last_login_at` timestamp updated on successful login
- [ ] Access and refresh tokens returned/set as cookies
- [ ] Failed login attempts are rate limited (5 per minute per IP)

**Password Reset**:
- [ ] User can request password reset via email
- [ ] Password reset email sent (if email exists)
- [ ] Reset link contains valid token
- [ ] Token expires after 1 hour
- [ ] User can reset password with valid token
- [ ] Invalid/expired token shows error message
- [ ] New password meets requirements (8+ chars)

**Token Management**:
- [ ] Access tokens expire after 1 hour (configurable)
- [ ] Refresh tokens expire after 30 days (configurable)
- [ ] Refresh token can generate new access token
- [ ] Expired refresh token requires re-login
- [ ] Tokens stored in httpOnly cookies (production)

**Logout**:
- [ ] Logout clears tokens from cookies
- [ ] User redirected to login page
- [ ] Subsequent API calls with cleared tokens return 401

### Multi-tenancy

**Data Isolation**:
- [ ] User sees only their own masterplans
- [ ] User sees only their own conversations
- [ ] Attempting to access another user's resource returns 404
- [ ] Database queries automatically filtered by `user_id`
- [ ] Foreign keys enforce referential integrity

**Workspace Isolation**:
- [ ] Each user has workspace at `/workspaces/{user_id}/`
- [ ] Workspace created on registration
- [ ] File operations scoped to user's workspace
- [ ] Path traversal attempts blocked
- [ ] Git repository initialized per user

**Database Schema**:
- [ ] `users` table exists with all required fields
- [ ] `user_quotas` table exists
- [ ] `user_usage` table exists
- [ ] `discovery_documents.user_id` is UUID FK to users
- [ ] `masterplans.user_id` is UUID FK to users
- [ ] `conversations.user_id` is UUID FK to users
- [ ] All indexes created for performance

### Usage Tracking

**Token Tracking**:
- [ ] All LLM calls tracked with user_id, tokens, cost
- [ ] Monthly totals aggregated in `user_usage` table
- [ ] Quota checked before LLM call
- [ ] 429 error if quota exceeded
- [ ] Usage displayed in user profile

**Masterplan Tracking**:
- [ ] Masterplan creation increments counter
- [ ] Quota checked before creation
- [ ] 429 error if limit reached
- [ ] Count displayed in user profile

**Storage Tracking**:
- [ ] Workspace size calculated (daily background job)
- [ ] Storage usage updated in `user_usage` table
- [ ] Quota checked on file writes
- [ ] 413 error if storage exceeded
- [ ] Storage displayed in user profile with human-readable format

### Admin Features

**User Management**:
- [ ] Admin can view all users (paginated)
- [ ] Admin can search and filter users
- [ ] Admin can view individual user details
- [ ] Admin can activate/deactivate users
- [ ] Admin can delete users (soft delete)
- [ ] All admin endpoints require `is_superuser=true`

**Quota Management**:
- [ ] Admin can view user quotas
- [ ] Admin can manually adjust quotas
- [ ] Quota changes take effect immediately
- [ ] Setting quota to null = unlimited

**Impersonation**:
- [ ] Admin can impersonate users
- [ ] Impersonation token includes both admin and target user IDs
- [ ] UI shows impersonation warning banner
- [ ] Admin can exit impersonation
- [ ] Cannot impersonate other admins

**Statistics**:
- [ ] Admin can view global statistics
- [ ] Statistics show total users, active users, new users
- [ ] Statistics show total LLM usage and cost
- [ ] Statistics show top users by usage
- [ ] Statistics cached for performance (5 minute TTL)

### Rate Limiting

**Authentication Endpoints**:
- [ ] Login limited to 5 requests per minute per IP
- [ ] Register limited to 5 requests per minute per IP
- [ ] Password reset limited to 3 requests per hour per IP
- [ ] 429 error returned when limit exceeded
- [ ] Response headers show rate limit status

**API Endpoints**:
- [ ] Chat endpoints limited to 30 requests per minute per user
- [ ] Masterplan endpoints limited to 20 requests per minute per user
- [ ] Admin endpoints limited to 100 requests per minute per admin
- [ ] Rate limits configurable per user in `user_quotas` table

**LLM Token Limits**:
- [ ] Monthly token quota enforced per user
- [ ] 429 error if quota exceeded
- [ ] 5% grace period allowed (1.05M if limit is 1M)
- [ ] Admins can bypass limits

### Frontend

**Pages**:
- [ ] Login page exists and works
- [ ] Registration page exists and works
- [ ] Forgot password page exists and works
- [ ] Reset password page exists and works
- [ ] Email verification page exists and works
- [ ] User profile page exists and shows usage
- [ ] All pages match DevMatrix design system

**Protected Routes**:
- [ ] All routes (except auth) require authentication
- [ ] Unauthenticated users redirected to login
- [ ] After login, redirected to originally requested page
- [ ] Admin routes require `is_superuser=true`
- [ ] Non-admin users see 403 error on admin routes

**Navigation**:
- [ ] Header shows user menu dropdown
- [ ] User menu includes Profile, Logout
- [ ] Header shows usage badge with token consumption
- [ ] Usage badge color-coded by percentage

**Auth State**:
- [ ] Auth context provides user, isAuthenticated, login, logout
- [ ] Token auto-refresh logic works
- [ ] 401 errors redirect to login globally
- [ ] User state persists across page refreshes

---

## Migration Strategy

### Decision: Start Fresh

**Rationale**:
- No existing production users with data to migrate
- Clean slate simplifies initial rollout
- Avoid complexity of migrating String user_ids to UUID FKs
- Faster time to production

**Implications**:
- Current local development data will be discarded
- First production deployment will have no users
- Developers will need to re-register after deployment

### Initial Superuser Creation

**Option 1: CLI Command** (Recommended)
```bash
python -m src.cli.create_admin \
  --email admin@devmatrix.com \
  --username admin \
  --password <secure-password>
```

**Option 2: First User is Admin**
- Set `FIRST_USER_IS_ADMIN=true` in .env
- First user to register gets `is_superuser=true`
- Subsequent users are normal users

**Recommendation**: Use Option 1 for production, Option 2 for development

### Database Migration Steps

**Step 1: Backup Current Database**
```bash
pg_dump devmatrix_db > backup_pre_auth_$(date +%Y%m%d).sql
```

**Step 2: Run Alembic Migrations**
```bash
# Create migration
alembic revision -m "add_authentication_and_multi_tenancy"

# Review generated migration file
# Edit alembic/versions/xxx_add_authentication_and_multi_tenancy.py

# Apply migration
alembic upgrade head
```

**Step 3: Verify Schema**
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Check foreign keys
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f';
```

**Step 4: Create Initial Admin**
```bash
python -m src.cli.create_admin \
  --email admin@devmatrix.com \
  --username admin \
  --password $(openssl rand -base64 32)
```

**Step 5: Test Authentication**
- Register new user via API
- Login with new user
- Verify workspace created
- Create masterplan as user
- Verify data isolated

---

## Design References

### UI Design System

**Use Existing DevMatrix UI as Guide**:
- Dark mode color scheme (already implemented)
- Tailwind CSS utility classes
- Component patterns from existing pages
- Typography and spacing from current design
- Button styles, form inputs, cards

**Specific References**:
- **Login/Register Forms**: Similar to existing form inputs in masterplan creation
- **User Menu Dropdown**: Similar to other dropdowns in UI (if any)
- **Usage Stats**: Card-based layout similar to masterplan cards
- **Progress Bars**: Reuse progress bar component from task execution UI
- **Admin Dashboard**: Table-based layout for user list

**Color Coding for Usage**:
- Green: 0-80% of quota
- Yellow: 80-95% of quota
- Red: 95-100% of quota
- Pulsing red: Over 100%

### Email Templates

**Design Guidelines**:
- Simple, clean HTML emails
- Responsive design (mobile-friendly)
- Plain text fallback for all emails
- Consistent branding with DevMatrix
- Clear call-to-action buttons
- Footer with unsubscribe link (future)

**Template Structure**:
```
[DevMatrix Logo]

[Email Title]

[Email Body]

[Call-to-Action Button]

[Additional Information]

[Footer]
  DevMatrix | [Privacy Policy] | [Terms of Service]
```

---

## Dependencies & Tools

### Backend Dependencies (Add to requirements.txt)

```
# Email
sendgrid==6.10.0  # OR python-smtp-client

# Rate Limiting
slowapi==0.1.9
# OR
fastapi-limiter==0.1.5

# Already installed (verify versions)
bcrypt>=4.0.0
pyjwt>=2.8.0
sqlalchemy>=2.0.0
alembic>=1.12.0
redis>=5.0.0
```

### Frontend Dependencies (Add to package.json)

```json
{
  "dependencies": {
    "react-router-dom": "^6.20.0",  // Protected routes
    "js-cookie": "^3.0.5"  // Cookie handling (if needed)
  }
}
```

### Development Tools

**Database Management**:
- pgAdmin or DBeaver for schema inspection
- Alembic for migrations

**Email Testing**:
- MailHog or Mailtrap for local email testing
- SendGrid sandbox for development

**API Testing**:
- Postman or Insomnia for endpoint testing
- pytest for automated tests

---

## Success Metrics

### Launch Criteria

Before considering Phase 6 complete, verify:

**Functionality**:
- [ ] Users can register and login successfully
- [ ] Email verification works (if enabled)
- [ ] Password reset flow works end-to-end
- [ ] Multi-tenancy: Users see only their own data
- [ ] Workspace isolation: Each user has own directory
- [ ] Usage tracking: All LLM calls tracked per user
- [ ] Quotas enforced: Token, masterplan, storage limits work
- [ ] Rate limiting: Auth and API endpoints rate limited
- [ ] Admin features: All admin endpoints functional
- [ ] Frontend: All UI pages implemented and styled

**Security**:
- [ ] Passwords hashed with bcrypt
- [ ] Tokens stored in httpOnly cookies (production)
- [ ] CORS configured correctly
- [ ] Rate limiting prevents brute force
- [ ] No SQL injection vulnerabilities
- [ ] No path traversal vulnerabilities
- [ ] Users cannot access other users' data

**Performance**:
- [ ] Auth endpoints respond in < 200ms
- [ ] User data endpoints respond in < 100ms
- [ ] Database queries use indexes
- [ ] Rate limiting uses Redis (fast)
- [ ] No N+1 query problems

**Testing**:
- [ ] Unit tests for all new services (90%+ coverage)
- [ ] Integration tests for auth flows
- [ ] Multi-tenancy tests pass
- [ ] Rate limiting tests pass
- [ ] Admin endpoint tests pass

**Documentation**:
- [ ] API documentation updated (OpenAPI/Swagger)
- [ ] README updated with authentication setup
- [ ] Environment variables documented
- [ ] Migration guide written
- [ ] Admin user guide written

### Post-Launch Monitoring

**Metrics to Track**:
- User registration rate
- Login success rate
- Failed login attempts (brute force detection)
- Password reset requests
- Email verification rate
- Average LLM tokens per user
- Quota exceeded errors (identify users needing upgrades)
- Rate limit violations
- API error rates (4xx, 5xx)

**Alerts to Configure**:
- Failed login rate > 10 per minute (potential attack)
- Email service down
- Rate limit violations > 100 per minute
- Database connection errors
- Any user exceeding 90% of quota (upsell opportunity)

---

## Risk Factors & Mitigation

### Technical Risks

**Risk 1: Email Delivery Issues**
- **Impact**: Users can't verify email or reset passwords
- **Mitigation**:
  - Use reliable email service (SendGrid, AWS SES)
  - Implement retry logic for failed sends
  - Make verification optional via env var
  - Log all email sending attempts for debugging

**Risk 2: Token Expiry During Long Sessions**
- **Impact**: Users get logged out unexpectedly
- **Mitigation**:
  - Implement auto-refresh logic in frontend
  - Refresh tokens before expiry (< 5 min remaining)
  - Show warning before logout due to inactivity
  - Preserve form data across re-authentication

**Risk 3: Database Migration Failures**
- **Impact**: Production downtime, data loss
- **Mitigation**:
  - Test migrations thoroughly on staging
  - Backup database before migration
  - Use reversible migrations (down() methods)
  - Monitor migration progress
  - Have rollback plan ready

**Risk 4: Storage Quota Enforcement**
- **Impact**: Users can't create files, error messages confusing
- **Mitigation**:
  - Calculate storage async (don't block file writes)
  - Show clear error messages with current usage
  - Allow 5% overage grace period
  - Provide cleanup tools for users

### Security Risks

**Risk 5: Brute Force Attacks**
- **Impact**: Unauthorized access to user accounts
- **Mitigation**:
  - Rate limit login attempts (5 per minute)
  - Monitor failed login patterns
  - Consider CAPTCHA after 3 failed attempts
  - Alert on suspicious activity

**Risk 6: Token Theft (XSS, Man-in-the-Middle)**
- **Impact**: Account takeover
- **Mitigation**:
  - Use httpOnly cookies (can't be stolen by JS)
  - Enforce HTTPS in production (Secure flag)
  - SameSite=Strict for CSRF protection
  - Short access token expiry (1 hour)

**Risk 7: Data Leakage Between Users**
- **Impact**: Privacy breach, regulatory issues
- **Mitigation**:
  - Comprehensive multi-tenancy tests
  - Always filter queries by user_id
  - Never trust client-provided user_id
  - Return 404 (not 403) for unauthorized resources
  - Regular security audits

### Operational Risks

**Risk 8: Quota Misconfiguration**
- **Impact**: Users blocked unexpectedly or costs explode
- **Mitigation**:
  - Sensible defaults (1M tokens/month)
  - Admin dashboard to monitor usage
  - Alerts when users approach limits
  - Easy quota adjustment for admins

**Risk 9: Email Service Costs**
- **Impact**: Unexpected email bills
- **Mitigation**:
  - Choose service with predictable pricing
  - Rate limit verification/reset emails
  - Monitor daily email volume
  - Set up billing alerts

**Risk 10: First User Admin Auto-Promotion**
- **Impact**: Wrong user becomes admin in production
- **Mitigation**:
  - Disable `FIRST_USER_IS_ADMIN` in production
  - Use CLI command for admin creation
  - Document admin creation process clearly
  - Audit superuser list regularly

---

## Open Questions

### Resolved (Based on User Answers)

1. **Social Login**: Email/password now, OAuth foundation prepared for future ✓
2. **Email Verification**: YES, but configurable via .env (default: users created verified) ✓
3. **Password Reset**: YES, email-based with 1-hour token expiry ✓
4. **Multi-tenancy Database**: YES, shared database with user_id FKs ✓
5. **Workspace Isolation**: YES, `/workspaces/{user_id}/` ✓
6. **Usage Limits**: Everything configurable per user from users table/backoffice ✓
7. **API Keys**: NO, not in this phase ✓
8. **JWT Sessions**: Recommended httpOnly cookies, 1h access + 30d refresh ✓
9. **Admin Capabilities**: ALL requested (view users, impersonate, adjust quotas, statistics) ✓
10. **User Permissions**: Private only (no sharing yet) ✓
11. **Migration**: Start fresh (no data migration) ✓
12. **Frontend UI**: YES, full UI with usage stats ✓
13. **Rate Limiting**: Recommended specific limits per endpoint type ✓
14. **Out of Scope**: Teams, Payment, SSO, 2FA, Audit logs deferred ✓
15. **Existing Code**: Documented what's already implemented ✓
16. **Visual Assets**: None provided, use existing UI as design guide ✓

### Still Open (For Implementation)

1. **Email Service Provider**: Which to use - SendGrid, AWS SES, Mailgun?
   - **Recommendation**: SendGrid (simple, reliable, good free tier)

2. **Rate Limiting Library**: slowapi or fastapi-limiter?
   - **Recommendation**: slowapi (more mature, better documentation)

3. **Password Reset Token Storage**: Add columns to users table or separate table?
   - **Recommendation**: Add columns to users table (simpler for MVP)

4. **Token Blacklisting**: Implement for logout or rely on short expiry?
   - **Recommendation**: Rely on short expiry for MVP, add blacklisting in Phase 7 if needed

5. **Soft Delete vs Hard Delete**: When user deleted, what happens to data?
   - **Recommendation**: Soft delete (set `is_active=false`, `deleted_at` timestamp) with 30-day retention

6. **Storage Calculation Frequency**: Daily, hourly, or on-demand?
   - **Recommendation**: Daily background job (cron) + manual refresh button in admin

7. **Impersonation Duration**: 1 hour, 8 hours, or until logout?
   - **Recommendation**: 1 hour max, admin can re-impersonate if needed

---

This requirements document is comprehensive and ready for handoff to the spec-writer phase.

