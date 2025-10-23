# Specification: Phase 6 - Authentication & Multi-tenancy

## Overview

### Feature Name
Authentication & Multi-tenancy System

### Description
Transform DevMatrix from a single-user local application into a production-ready multi-user SaaS platform with comprehensive authentication, user isolation, usage tracking, and admin capabilities.

### Priority
**Critical** - Foundation for all future features requiring user management and data isolation.

### Estimated Effort
**3-4 weeks** (full-stack implementation including frontend, backend, database migrations, testing)

### Business Value
- Enables multi-user deployment and revenue generation
- Provides user isolation and data security
- Tracks usage metrics for billing and quota enforcement
- Establishes admin tools for system management
- Prepares foundation for OAuth and team features

### Success Metrics
- Users can register, login, and manage their accounts
- 100% data isolation between users (zero data leakage)
- All LLM token usage tracked per user with 99.9% accuracy
- Admin dashboard operational with user management capabilities
- Authentication response times < 200ms
- Zero unauthorized access to user data

### Dependencies
- Existing User model and AuthService (already implemented)
- PostgreSQL database with UUID extension
- Redis for rate limiting
- SMTP service for email delivery (SendGrid recommended)
- React Router for frontend routing

### Risks
1. **Email delivery issues** - Mitigated by making verification optional via env var
2. **Database migration complexity** - Mitigated by starting fresh (no data migration)
3. **Token expiry during sessions** - Mitigated by auto-refresh logic
4. **Multi-tenancy data leakage** - Mitigated by comprehensive testing and query filtering
5. **Storage quota enforcement** - Mitigated by async calculation and grace periods

---

## Goals & Non-Goals

### Goals

**What we ARE building:**

1. **Complete Authentication System**
   - Email/password registration with validation
   - JWT-based authentication (access + refresh tokens)
   - Email verification flow (configurable)
   - Password reset via time-limited email tokens
   - Secure session management with httpOnly cookies
   - Login/logout with proper token handling

2. **Multi-tenancy & Data Isolation**
   - User-specific workspaces (`/workspaces/{user_id}/`)
   - Database foreign keys on all user data tables
   - Automatic query filtering by `user_id`
   - Complete separation between user data
   - Path traversal protection for file operations

3. **Usage Tracking & Quotas**
   - LLM token consumption tracking per user
   - Masterplan creation counting
   - Workspace storage tracking
   - Configurable per-user quotas (tokens, masterplans, storage)
   - Quota enforcement with grace periods
   - Usage statistics display in frontend

4. **Admin Capabilities**
   - User management (view, activate/deactivate, delete)
   - Global system statistics dashboard
   - User impersonation for debugging
   - Manual quota adjustments
   - Usage reports per user

5. **Rate Limiting**
   - Authentication endpoints (5 req/min per IP)
   - API endpoints (30 req/min per user)
   - LLM token limits (monthly quotas)
   - Admin endpoints (100 req/min)

6. **Frontend UI**
   - Login, registration, password reset pages
   - User profile with usage statistics
   - Protected routes requiring authentication
   - Admin dashboard (if time permits)
   - Header with user menu and usage badge

### Non-Goals

**What we are NOT building (deferred to future phases):**

- Teams/Organizations (Phase 8) - Multi-user collaboration
- Payment Integration - Stripe/billing system
- OAuth/Social Login - Google, GitHub authentication (foundation prepared)
- SSO/SAML (Phase 10) - Enterprise single sign-on
- Two-Factor Authentication (2FA) - Additional security layer
- Comprehensive Audit Logs (Phase 10) - Activity tracking
- API Keys - User-generated keys for integrations
- Workspace Sharing - Sharing masterplans between users
- Complex Role Systems - Beyond user/admin roles

---

## User Stories

### User Registration & Authentication (US-1 to US-4)

**US-1: User Registration**
- **As a new user**, I want to register with my email and password so that I can start using DevMatrix.
- **Acceptance Criteria**:
  - User accesses `/register` page with email, username, password fields
  - System validates input (email format, username 3-50 chars alphanumeric, password 8+ chars)
  - System checks email/username uniqueness and shows errors if duplicate
  - On success, user auto-logs in (if verification disabled) or sees "Check email" message
  - User workspace created at `/workspaces/{user_id}/`
  - Default quotas assigned

**US-2: Email Verification**
- **As a new user with verification required**, I want to verify my email so that I can use all features.
- **Acceptance Criteria**:
  - User receives verification email within 1 minute
  - Email contains clickable link with 24-hour valid token
  - Clicking link verifies email and shows success message
  - User can request new verification email (rate limited to 1 per 2 minutes)
  - Unverified users cannot create masterplans (when verification required)

**US-3: User Login**
- **As a registered user**, I want to login with my credentials so that I can access my masterplans.
- **Acceptance Criteria**:
  - User enters email and password on `/login` page
  - System validates credentials and returns tokens
  - Invalid credentials show "Invalid email or password" error
  - Inactive account shows "Account disabled" error
  - On success, redirect to dashboard
  - `last_login_at` timestamp updated

**US-4: Password Reset**
- **As a user who forgot their password**, I want to reset it via email so that I can regain access.
- **Acceptance Criteria**:
  - User clicks "Forgot password?" and enters email
  - System sends password reset email (if email exists)
  - Email contains reset link valid for 1 hour
  - User enters new password meeting requirements
  - User can login with new password
  - Old tokens invalidated after reset

### Multi-tenancy & Data Isolation (US-5 to US-7)

**US-5: Private Masterplans**
- **As a user**, I want to see only my own masterplans so that my work is private.
- **Acceptance Criteria**:
  - Dashboard shows only user's own masterplans
  - Attempting to access another user's masterplan returns 404 (not 403)
  - API queries automatically filtered by `user_id`

**US-6: Private Conversations**
- **As a user**, I want my chat conversations to be private so that my ideas are protected.
- **Acceptance Criteria**:
  - Conversation history shows only user's conversations
  - Cannot access other users' conversations via API or URL manipulation

**US-7: Isolated Workspace**
- **As a user**, I want my own workspace so that my code doesn't interfere with others.
- **Acceptance Criteria**:
  - Generated code stored in `/workspaces/{user_id}/`
  - User cannot access other users' workspaces
  - Git repository initialized per user
  - Workspace created automatically on registration

### Usage Tracking & Quotas (US-8 to US-11)

**US-8: View Usage Statistics**
- **As a user**, I want to see my current usage so that I know how much quota I've consumed.
- **Acceptance Criteria**:
  - Profile page displays LLM tokens with progress bar (e.g., 45K / 100K)
  - Shows masterplans created count
  - Shows storage usage in human-readable format (125 MB / 5 GB)
  - Shows quota reset date (first of next month)
  - Color-coded progress bars (green < 80%, yellow 80-95%, red > 95%)

**US-9: Quota Enforcement - Tokens**
- **As a system**, I want to prevent users from exceeding token quotas so that costs are controlled.
- **Acceptance Criteria**:
  - Before LLM call, check if user has quota remaining
  - If exceeded, return 429 error with usage details and reset date
  - Allow 5% grace period (1.05M if limit is 1M)
  - Admins can bypass limits

**US-10: Quota Enforcement - Masterplans**
- **As a system**, I want to limit masterplan creation so that abuse is prevented.
- **Acceptance Criteria**:
  - Before creating masterplan, check quota
  - If limit reached, show error with current count and limit
  - Admin can override limits

**US-11: Quota Enforcement - Storage**
- **As a system**, I want to limit workspace storage so that disk usage is controlled.
- **Acceptance Criteria**:
  - System tracks workspace size via daily background job
  - Before file write, check if quota exceeded
  - If exceeded, return 413 error with storage details
  - User can delete old projects to free space

### Admin Features (US-12 to US-17)

**US-12: View All Users**
- **As an admin**, I want to see all registered users so that I can manage the system.
- **Acceptance Criteria**:
  - Admin accesses `/admin/users` page
  - Shows all users with email, username, created date, last login, usage summary
  - Supports search, filtering by active status, sorting
  - Paginated (20 users per page)

**US-13: Deactivate User**
- **As an admin**, I want to deactivate abusive users so that they can't use the system.
- **Acceptance Criteria**:
  - Admin clicks "Deactivate" on user row
  - User's `is_active` set to false
  - User cannot login (gets "Account inactive" error)
  - Admin can reactivate user later

**US-14: View User Details**
- **As an admin**, I want to see detailed user information so that I can debug issues.
- **Acceptance Criteria**:
  - Admin clicks user to see detail page
  - Shows all user info, quotas, current month usage, lifetime statistics
  - Shows workspace path and size
  - Shows total LLM cost

**US-15: Adjust User Quotas**
- **As an admin**, I want to manually adjust quotas so that I can handle special cases.
- **Acceptance Criteria**:
  - Admin clicks "Edit Quotas" on user detail page
  - Form shows current quotas with input fields
  - Admin can change token limit, masterplan limit, storage limit
  - Setting to null = unlimited
  - Changes take effect immediately

**US-16: Impersonate User**
- **As an admin**, I want to impersonate users so that I can debug their issues.
- **Acceptance Criteria**:
  - Admin clicks "Impersonate" button
  - Admin logged in as that user
  - UI shows warning banner "You are impersonating user@example.com"
  - Admin can perform any action as that user
  - Admin can exit impersonation to return to their account
  - Cannot impersonate other admins

**US-17: View Global Statistics**
- **As an admin**, I want to see system-wide statistics so that I can monitor growth.
- **Acceptance Criteria**:
  - Admin dashboard shows total users, active users, new users this month
  - Shows total LLM tokens used and cost
  - Shows total masterplans created
  - Shows top users by token usage
  - Statistics cached for 5 minutes

### Session Management (US-18 to US-19)

**US-18: Stay Logged In**
- **As a user**, I want my session to stay active so that I don't have to login repeatedly.
- **Acceptance Criteria**:
  - User stays logged in for up to 30 days (refresh token expiry)
  - Access token refreshes automatically before expiry (< 5 min remaining)
  - User doesn't see login screen unless inactive for 30 days

**US-19: Secure Logout**
- **As a user**, I want to logout so that others can't access my account on shared computer.
- **Acceptance Criteria**:
  - User clicks "Logout" in menu
  - Tokens cleared from cookies
  - User redirected to login page
  - Attempting to access protected pages redirects to login

### Rate Limiting (US-20 to US-21)

**US-20: Prevent Brute Force**
- **As a system**, I want to rate limit login attempts so that brute force attacks are prevented.
- **Acceptance Criteria**:
  - After 5 failed login attempts from same IP in 1 minute, return 429 error
  - Error shows "Too many login attempts. Try again in X seconds."
  - Rate limit resets after 1 minute

**US-21: Prevent API Abuse**
- **As a system**, I want to rate limit API calls so that abuse is prevented.
- **Acceptance Criteria**:
  - Users limited to 30 API calls per minute (chat endpoints)
  - After limit exceeded, return 429 error with retry-after header
  - Response headers show limit, remaining, reset time
  - Premium users can have higher limits (configurable)

---

## Functional Requirements

### FR-AUTH: Authentication System

**FR-AUTH-001: User Registration** (NEW)
- User provides email, username, password
- Email validated for format and uniqueness
- Username validated (3-50 chars, alphanumeric + underscore/dash, unique)
- Password hashed with bcrypt (cost factor 12)
- User created with `is_active=True`, `is_superuser=False`
- Workspace created at `/workspaces/{user_id}/`
- Default quotas assigned
- Email verification behavior based on `EMAIL_VERIFICATION_REQUIRED` env var
- Returns access + refresh tokens on success

**FR-AUTH-002: Email Verification** (NEW)
- Verification token (UUID) generated on registration
- Verification email sent with link valid for 24 hours
- Endpoint `/api/v1/auth/verify-email` validates token and sets `is_verified=True`
- Endpoint `/api/v1/auth/resend-verification` sends new verification email (rate limited)
- If verification required, unverified users cannot create masterplans

**FR-AUTH-003: User Login** (EXISTING - ENHANCE)
- User provides email and password
- Password verified with bcrypt
- Account must be active (`is_active=True`)
- `last_login_at` timestamp updated
- Access token (1 hour) and refresh token (30 days) generated
- Tokens set as httpOnly cookies in response
- Failed attempts rate limited (5 per minute per IP)

**FR-AUTH-004: Password Reset** (NEW)
- Endpoint `/api/v1/auth/forgot-password` sends reset email (rate limited: 3 per hour per IP)
- Reset token (UUID) generated with 1-hour expiry
- Endpoint `/api/v1/auth/reset-password` validates token and updates password
- Old tokens invalidated after successful reset
- Always returns generic success message (prevent email enumeration)

**FR-AUTH-005: Token Management** (EXISTING - ENHANCE)
- Access tokens expire after 1 hour (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh tokens expire after 30 days (configurable via `JWT_REFRESH_TOKEN_EXPIRE_DAYS`)
- Endpoint `/api/v1/auth/refresh` generates new access token from refresh token
- Tokens stored in httpOnly cookies with Secure and SameSite=Strict flags
- Endpoint `/api/v1/auth/logout` clears cookies

**FR-AUTH-006: Session Security** (NEW)
- httpOnly cookies prevent XSS token theft
- Secure flag ensures HTTPS-only transmission (production)
- SameSite=Strict prevents CSRF attacks
- CORS configured to allow credentials from trusted frontend origin
- Token payload includes: user_id, email, username, is_superuser, type, exp, iat

### FR-TENANT: Multi-tenancy & Data Isolation

**FR-TENANT-001: Database Schema Migration** (NEW)
- Users table already exists with all required fields
- Add `is_verified`, `verification_token`, `verification_token_created_at` columns to users table
- Add `password_reset_token`, `password_reset_expires` columns to users table
- Create `user_quotas` table with FK to users
- Create `user_usage` table with FK to users and unique constraint on (user_id, month)
- Modify `discovery_documents.user_id` from String to UUID FK
- Modify `masterplans.user_id` from String to UUID FK
- Add `user_id` UUID FK to `conversations` table
- Create indexes on all user_id columns for performance

**FR-TENANT-002: Workspace Isolation** (NEW)
- Each user has workspace directory at `/workspaces/{user_id}/`
- Workspace created automatically on registration
- Workspace structure: `projects/`, `temp/`, `.git/`
- Git repository initialized per user workspace
- All file operations scoped to user's workspace
- Path traversal protection (validate paths don't escape workspace)
- Workspace size tracked for quota enforcement

**FR-TENANT-003: Query Filtering** (NEW)
- All database queries automatically filter by authenticated user's `user_id`
- Middleware extracts `user_id` from JWT token
- Queries use SQLAlchemy filters: `filter(Table.user_id == current_user.user_id)`
- Users cannot access other users' data even with direct API requests
- Return 404 (not 403) for unauthorized resource access (prevent enumeration)

**FR-TENANT-004: Data Integrity** (NEW)
- Foreign key constraints with `ON DELETE CASCADE` ensure referential integrity
- Unique constraints on users.email and users.username
- Database transactions for multi-step operations
- Soft delete option (set `is_active=false`, `deleted_at` timestamp) with 30-day retention

### FR-USAGE: Usage Tracking & Quotas

**FR-USAGE-001: LLM Token Tracking** (NEW)
- Track every LLM API call: user_id, model, input_tokens, output_tokens, cached_tokens, cost_usd, timestamp
- Aggregate monthly totals in `user_usage` table
- Check quota before LLM call: `current_month_tokens < quota.llm_tokens_monthly_limit`
- Return 429 error if quota exceeded with usage details and reset date
- Allow 5% grace period (1.05M tokens if limit is 1M)
- Decorator/middleware for automatic tracking

**FR-USAGE-002: Masterplan Tracking** (NEW)
- Increment `masterplans_created` counter in `user_usage` table on creation
- Check quota before creating: `user_masterplans_count < quota.masterplans_limit`
- Return 429 error if limit reached
- Admins bypass limits

**FR-USAGE-003: Storage Tracking** (NEW)
- Background job (daily cron) calculates workspace directory size
- Update `storage_bytes` in `user_usage` table
- Check quota on file write: `current_storage < quota.storage_bytes_limit`
- Return 413 error if storage quota exceeded
- Manual refresh button in admin dashboard

**FR-USAGE-004: Usage Statistics API** (NEW)
- Endpoint `GET /api/v1/users/me/usage` returns current month usage
- Response includes: tokens used/limit, masterplans created/limit, storage used/limit
- Display percentages and human-readable formats (125 MB / 5 GB)
- Cached for 1 minute for performance

**FR-USAGE-005: Configurable Quotas** (NEW)
- `user_quotas` table stores per-user overrides
- Default quotas: 1M tokens/month, 50 masterplans, 5 GB storage, 30 API calls/min
- Admin can override via `PATCH /api/v1/admin/users/{user_id}/quotas`
- `null` value = unlimited for that quota
- Changes take effect immediately

### FR-ADMIN: Admin Features

**FR-ADMIN-001: User Management** (NEW)
- Endpoint `GET /api/v1/admin/users` lists all users (paginated, searchable, sortable)
- Endpoint `GET /api/v1/admin/users/{user_id}` shows detailed user info
- Endpoint `PATCH /api/v1/admin/users/{user_id}` updates user (activate/deactivate)
- Endpoint `DELETE /api/v1/admin/users/{user_id}` soft deletes user
- All endpoints require `Depends(get_current_superuser)`

**FR-ADMIN-002: Global Statistics** (NEW)
- Endpoint `GET /api/v1/admin/statistics` returns system-wide stats
- Stats include: total users, active users, new users this month/today
- Usage this month: total tokens, cost, masterplans, storage
- All-time usage: total tokens, cost, masterplans, conversations
- Top users by token usage
- Cached for 5 minutes

**FR-ADMIN-003: User Impersonation** (NEW)
- Endpoint `POST /api/v1/admin/impersonate/{user_id}` generates impersonation token
- Token includes claims: `impersonating=true`, admin's user_id for audit trail
- Token valid for 1 hour max
- Cannot impersonate other admins
- All actions logged with both admin and impersonated user IDs

**FR-ADMIN-004: Quota Management** (NEW)
- Endpoint `PATCH /api/v1/admin/users/{user_id}/quotas` updates user quotas
- Can set token limit, masterplan limit, storage limit
- `null` = unlimited
- Endpoint `GET /api/v1/admin/usage-by-user` returns usage report per user

### FR-RATE: Rate Limiting

**FR-RATE-001: Authentication Endpoint Limits** (NEW)
- Endpoints `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/reset-password`
- Limit: 5 requests per minute per IP address
- Use Redis to store IP-based counters with TTL
- Response: 429 status with `Retry-After` header

**FR-RATE-002: API Endpoint Limits** (NEW)
- Chat/conversation endpoints: 30 requests per minute per user
- Masterplan endpoints: 20 requests per minute per user
- Admin endpoints: 100 requests per minute per admin
- Key: `user_id` from authenticated JWT
- Configurable per user via `user_quotas.api_calls_per_minute`

**FR-RATE-003: Rate Limit Headers** (NEW)
- All responses include rate limit headers:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Unix timestamp when limit resets
  - `Retry-After`: Seconds to wait (when 429 error)

### FR-UI: Frontend Implementation

**FR-UI-001: Authentication Pages** (NEW)
- `LoginPage.tsx`: Email/password form, "Forgot password?" link, "Create account" link
- `RegisterPage.tsx`: Email, username, password, confirm password fields, password strength indicator
- `ForgotPasswordPage.tsx`: Email input to request password reset
- `ResetPasswordPage.tsx`: New password form (accessed via email link with token)
- `VerifyEmailPage.tsx`: Email verification confirmation (accessed via email link)
- `VerifyEmailPendingPage.tsx`: Shows "Check your email" message with resend button

**FR-UI-002: User Profile** (NEW)
- `UserProfilePage.tsx`: Display user info (email, username, created date, last login)
- `UsageStatsCard.tsx`: Reusable component showing usage vs quotas with progress bars
- Shows LLM tokens, masterplans, storage with color-coded progress (green/yellow/red)
- "Change Password" and "Logout" buttons

**FR-UI-003: Navigation Updates** (NEW)
- Header updated with user menu dropdown (avatar + username trigger)
- Dropdown items: Profile, Usage & Billing, Settings, Divider, Logout
- Usage badge in header: Token icon with "45K / 100K" text, color-coded
- Click badge navigates to profile usage section

**FR-UI-004: Protected Routes** (NEW)
- `PrivateRoute.tsx`: Wrapper component that checks authentication
- All routes except `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email` require auth
- Unauthenticated users redirected to `/login?redirect={current_path}`
- After login, redirect to originally requested page
- `AdminRoute.tsx`: Wrapper for admin-only routes requiring `is_superuser=true`

**FR-UI-005: Auth Context** (NEW)
- `AuthProvider.tsx`: React Context provider for global auth state
- State: `user`, `isAuthenticated`, `isLoading`
- Methods: `login(email, password)`, `logout()`, `refreshToken()`, `checkAuth()`
- Auto-refresh logic: Check token expiry every 1 minute, refresh if < 5 min remaining
- Global error handling: 401 redirects to login, 403 shows access denied

---

## Technical Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Auth Pages      │  │ User Profile │  │ Protected Routes │   │
│  │ (Login/Register)│  │ & Usage      │  │ (Dashboard, Chat)│   │
│  └─────────────────┘  └──────────────┘  └──────────────────┘   │
│           │                    │                    │            │
│           └────────────────────┼────────────────────┘            │
│                                │                                 │
└────────────────────────────────┼─────────────────────────────────┘
                                 │ HTTPS (httpOnly cookies)
                                 │
┌────────────────────────────────┼─────────────────────────────────┐
│                         Backend (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Auth Middleware (JWT Validation)            │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │                    │                    │            │
│  ┌────────▼──────┐   ┌────────▼──────┐   ┌────────▼────────┐   │
│  │ Auth Router   │   │ User Router   │   │ Admin Router    │   │
│  │ (Login, Reg)  │   │ (Profile, Use)│   │ (Users, Stats)  │   │
│  └───────┬───────┘   └───────┬───────┘   └────────┬────────┘   │
│          │                   │                     │            │
│  ┌───────▼───────────────────▼─────────────────────▼────────┐   │
│  │                   Service Layer                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│   │
│  │  │AuthService│ │UsageService│ │QuotaService│ │AdminServ││   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘│   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────────────────▼────────────────────┐  ┌─────────┐ │
│  │         PostgreSQL Database                   │  │  Redis  │ │
│  │  ┌────────┐ ┌───────────┐ ┌────────────────┐│  │(Rate    │ │
│  │  │ users  │ │user_quotas│ │ user_usage     ││  │Limiting)│ │
│  │  │        │ │           │ │                ││  └─────────┘ │
│  │  └───┬────┘ └─────┬─────┘ └────────┬───────┘│              │
│  │      │            │                 │        │              │
│  │  ┌───▼────────────▼─────────────────▼──────┐│              │
│  │  │  masterplans, conversations, messages  ││              │
│  │  │  (all with user_id FK)                 ││              │
│  │  └──────────────────────────────────────────┘│              │
│  └─────────────────────────────────────────────┘              │
│                                                                 │
│  ┌─────────────────────────────────────────────┐               │
│  │       File System (User Workspaces)         │               │
│  │  /workspaces/{user_id_1}/                   │               │
│  │  /workspaces/{user_id_2}/                   │               │
│  └─────────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

### Database Schema

#### Existing Tables (Modified)

**users** (EXISTING - EXTEND)
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Account status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    is_verified BOOLEAN DEFAULT TRUE NOT NULL,  -- NEW

    -- Email verification
    verification_token UUID,  -- NEW
    verification_token_created_at TIMESTAMP,  -- NEW

    -- Password reset
    password_reset_token UUID,  -- NEW
    password_reset_expires TIMESTAMP,  -- NEW

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_verification_token ON users(verification_token);
CREATE INDEX idx_users_password_reset_token ON users(password_reset_token);
```

**masterplans** (MODIFY user_id)
```sql
-- Modify existing table
ALTER TABLE masterplans
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_masterplan_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

CREATE INDEX idx_masterplans_user ON masterplans(user_id);
```

**discovery_documents** (MODIFY user_id)
```sql
-- Modify existing table
ALTER TABLE discovery_documents
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_discovery_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

CREATE INDEX idx_discovery_user ON discovery_documents(user_id);
```

#### New Tables

**user_quotas**
```sql
CREATE TABLE user_quotas (
    quota_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Quota limits (NULL = unlimited)
    llm_tokens_monthly_limit INTEGER,
    masterplans_limit INTEGER,
    storage_bytes_limit BIGINT,
    api_calls_per_minute INTEGER DEFAULT 30,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_quotas_user ON user_quotas(user_id);
```

**user_usage**
```sql
CREATE TABLE user_usage (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    month DATE NOT NULL,  -- First day of month: '2025-10-01'

    -- Usage metrics
    llm_tokens_used INTEGER DEFAULT 0,
    llm_cost_usd NUMERIC(10, 4) DEFAULT 0.0,
    masterplans_created INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, month)
);

CREATE INDEX idx_user_usage_user_month ON user_usage(user_id, month);
CREATE INDEX idx_user_usage_month ON user_usage(month);
```

**conversations** (NEW)
```sql
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(300),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
```

**messages** (NEW)
```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);
```

### API Endpoints

#### Authentication Endpoints

**POST /api/v1/auth/register**
- **Description**: Register new user
- **Auth**: None required
- **Rate Limit**: 5 req/min per IP
- **Request**:
```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "SecurePass123!"
}
```
- **Response** (201):
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "john_doe",
    "is_active": true,
    "is_superuser": false,
    "is_verified": true,
    "created_at": "2025-10-22T10:00:00Z"
  }
}
```
- **Errors**: 400 (email/username exists), 422 (validation error)

**POST /api/v1/auth/login**
- **Description**: Authenticate user
- **Auth**: None required
- **Rate Limit**: 5 req/min per IP
- **Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```
- **Response** (200): Same as register
- **Errors**: 401 (invalid credentials), 403 (account inactive)

**POST /api/v1/auth/verify-email**
- **Description**: Verify email with token
- **Auth**: None required
- **Request**:
```json
{
  "token": "verification-uuid"
}
```
- **Response** (200):
```json
{
  "message": "Email verified successfully",
  "user_id": "uuid"
}
```
- **Errors**: 400 (expired/invalid token)

**POST /api/v1/auth/resend-verification**
- **Description**: Resend verification email
- **Auth**: Required
- **Rate Limit**: 1 req per 2 minutes per user
- **Response** (200):
```json
{
  "message": "Verification email sent"
}
```
- **Errors**: 400 (already verified), 429 (too many requests)

**POST /api/v1/auth/forgot-password**
- **Description**: Request password reset
- **Auth**: None required
- **Rate Limit**: 3 req/hour per IP
- **Request**:
```json
{
  "email": "user@example.com"
}
```
- **Response** (200):
```json
{
  "message": "If that email exists, a reset link has been sent"
}
```

**POST /api/v1/auth/reset-password**
- **Description**: Reset password with token
- **Auth**: None required
- **Request**:
```json
{
  "token": "reset-uuid",
  "new_password": "NewSecurePass123!"
}
```
- **Response** (200):
```json
{
  "message": "Password reset successfully"
}
```
- **Errors**: 400 (expired/invalid token), 422 (weak password)

**POST /api/v1/auth/refresh**
- **Description**: Refresh access token (EXISTING)
- **Auth**: Refresh token in cookie
- **Request**: Empty body (token from cookie)
- **Response** (200):
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```
- **Errors**: 401 (invalid/expired refresh token)

**GET /api/v1/auth/me**
- **Description**: Get current user info (EXISTING)
- **Auth**: Required
- **Response** (200):
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "john_doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-10-22T10:00:00Z",
  "last_login_at": "2025-10-22T14:30:00Z"
}
```
- **Errors**: 401 (missing/invalid token), 403 (account inactive)

**POST /api/v1/auth/logout**
- **Description**: Logout user (EXISTING)
- **Auth**: Required
- **Response** (200):
```json
{
  "message": "Successfully logged out"
}
```

#### User Management Endpoints

**GET /api/v1/users/me/usage**
- **Description**: Get current user's usage statistics
- **Auth**: Required
- **Response** (200):
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

**PATCH /api/v1/users/me**
- **Description**: Update current user profile
- **Auth**: Required
- **Request**:
```json
{
  "username": "new_username"
}
```
- **Response** (200): Updated user object
- **Errors**: 400 (username taken), 422 (validation error)

#### Admin Endpoints

**GET /api/v1/admin/users**
- **Description**: List all users
- **Auth**: Admin required
- **Rate Limit**: 100 req/min
- **Query Params**: `page=1`, `per_page=20`, `sort_by=created_at`, `sort_order=desc`, `filter_active=all`, `search=query`
- **Response** (200):
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

**GET /api/v1/admin/users/{user_id}**
- **Description**: Get detailed user information
- **Auth**: Admin required
- **Response** (200):
```json
{
  "user": { /* user object */ },
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

**PATCH /api/v1/admin/users/{user_id}**
- **Description**: Update user (activate/deactivate)
- **Auth**: Admin required
- **Request**:
```json
{
  "is_active": false
}
```
- **Response** (200): Updated user object

**DELETE /api/v1/admin/users/{user_id}**
- **Description**: Soft delete user
- **Auth**: Admin required
- **Response** (200):
```json
{
  "message": "User deleted successfully"
}
```

**PATCH /api/v1/admin/users/{user_id}/quotas**
- **Description**: Update user quotas
- **Auth**: Admin required
- **Request**:
```json
{
  "llm_tokens_monthly_limit": 10000000,
  "masterplans_limit": null,
  "storage_bytes_limit": 53687091200
}
```
- **Response** (200): Updated quotas object

**POST /api/v1/admin/impersonate/{user_id}**
- **Description**: Generate impersonation token
- **Auth**: Admin required
- **Response** (200):
```json
{
  "access_token": "impersonation_token",
  "refresh_token": "impersonation_refresh_token",
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
- **Errors**: 403 (cannot impersonate admins)

**GET /api/v1/admin/statistics**
- **Description**: Get global system statistics
- **Auth**: Admin required
- **Response** (200):
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

**GET /api/v1/admin/usage-by-user**
- **Description**: Get usage report per user
- **Auth**: Admin required
- **Query Params**: `month=2025-10` (optional, defaults to current month)
- **Response** (200):
```json
{
  "month": "2025-10",
  "users": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "username": "john_doe",
      "llm_tokens": 45000,
      "llm_cost_usd": 1.23,
      "masterplans": 5,
      "storage_gb": 0.125
    }
  ]
}
```

### Frontend Components

#### New Components

**Authentication Pages**

1. **LoginPage.tsx**
   - Props: None (uses router for navigation)
   - State: `email`, `password`, `error`, `loading`
   - Features: Form validation, error display, "Forgot password?" link, "Create account" link
   - Design: Centered card with DevMatrix branding, dark mode support

2. **RegisterPage.tsx**
   - Props: None
   - State: `email`, `username`, `password`, `confirmPassword`, `error`, `loading`, `passwordStrength`
   - Features: Client-side validation, password strength indicator, duplicate error handling
   - Design: Similar to login page with additional fields

3. **ForgotPasswordPage.tsx**
   - Props: None
   - State: `email`, `submitted`, `error`, `loading`
   - Features: Email input, success message after submission
   - Design: Simple centered form

4. **ResetPasswordPage.tsx**
   - Props: None (token from URL query param)
   - State: `password`, `confirmPassword`, `error`, `loading`, `success`
   - Features: Password validation, success redirect to login after 3 seconds
   - Design: Centered form with password strength indicator

5. **VerifyEmailPage.tsx**
   - Props: None (token from URL query param)
   - State: `verifying`, `success`, `error`
   - Features: Auto-verify on mount, success/error display, "Go to Dashboard" button
   - Design: Centered status display with icon

6. **VerifyEmailPendingPage.tsx**
   - Props: None
   - State: `email`, `resending`, `resendSuccess`
   - Features: "Resend verification email" button with 2-minute cooldown
   - Design: Centered message with email display

**User Profile Components**

7. **UserProfilePage.tsx**
   - Props: None (uses auth context for user)
   - State: `loading`, `usage`, `error`
   - Features: Account info section, usage stats section, "Change Password" modal, "Logout" button
   - Design: Two-column layout (info left, usage right)

8. **UsageStatsCard.tsx** (Reusable)
   - Props: `type: 'tokens' | 'masterplans' | 'storage'`, `used: number`, `limit: number | null`, `unit: string`
   - State: None (stateless component)
   - Features: Progress bar with color coding, percentage display, quota reset info
   - Design: Card with title, progress bar, numbers

9. **UserMenu.tsx**
   - Props: `user: User`, `onLogout: () => void`
   - State: `isOpen`
   - Features: Dropdown with avatar, menu items (Profile, Settings, Logout), click outside to close
   - Design: Header dropdown with user avatar and name

10. **UsageBadge.tsx**
    - Props: `tokensUsed: number`, `tokensLimit: number`
    - State: None
    - Features: Token icon, usage display, color-coded by percentage, click to navigate to profile
    - Design: Compact badge in header

**Auth Infrastructure**

11. **PrivateRoute.tsx**
    - Props: `children: ReactNode`
    - State: None (uses auth context)
    - Features: Checks authentication, redirects to login with return URL, shows loading state
    - Design: Transparent wrapper

12. **AdminRoute.tsx**
    - Props: `children: ReactNode`
    - State: None (uses auth context)
    - Features: Checks authentication and superuser status, shows 403 page if not admin
    - Design: Transparent wrapper

13. **AuthProvider.tsx** (Context)
    - Props: `children: ReactNode`
    - State: `user: User | null`, `isAuthenticated: boolean`, `isLoading: boolean`
    - Methods: `login()`, `logout()`, `refreshToken()`, `checkAuth()`
    - Features: Auto-refresh timer, global error handling, token from cookies
    - Design: Context provider wrapper

14. **PasswordStrengthIndicator.tsx**
    - Props: `password: string`
    - State: `strength: 'weak' | 'medium' | 'strong'`
    - Features: Real-time password strength calculation, color-coded bar, requirements checklist
    - Design: Horizontal bar with label

#### Modified Components

15. **App.tsx**
    - Changes: Wrap with `AuthProvider`, add auth routes, update routing
    - New routes: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/profile`
    - Protected existing routes: `/`, `/chat`, `/masterplans`, `/settings`

16. **Header.tsx** (or Sidebar in App.tsx)
    - Changes: Add `UserMenu` component, add `UsageBadge` component
    - Replace login button with user menu (when authenticated)
    - Show usage badge next to user menu

### Service Layer

#### New Services

**1. email_service.py**
```python
class EmailService:
    def send_verification_email(user_email: str, verification_token: UUID) -> bool
    def send_password_reset_email(user_email: str, reset_token: UUID) -> bool
    def send_welcome_email(user_email: str, username: str) -> bool
```

**2. password_reset_service.py**
```python
class PasswordResetService:
    def request_reset(email: str) -> bool
    def verify_reset_token(token: UUID) -> Optional[User]
    def reset_password(token: UUID, new_password: str) -> bool
    def cleanup_expired_tokens() -> int
```

**3. email_verification_service.py**
```python
class EmailVerificationService:
    def generate_verification_token(user: User) -> UUID
    def send_verification_email(user: User) -> bool
    def verify_email(token: UUID) -> bool
    def resend_verification(user: User) -> bool
```

**4. usage_tracking_service.py**
```python
class UsageTrackingService:
    def track_llm_usage(user_id: UUID, tokens: int, cost_usd: float, model: str) -> None
    def track_masterplan_created(user_id: UUID) -> None
    def track_storage_usage(user_id: UUID, bytes_added: int) -> None
    def get_current_month_usage(user_id: UUID) -> Dict[str, Any]
    def get_usage_statistics(user_id: UUID, start_date: date, end_date: date) -> List[Dict]
```

**5. quota_service.py**
```python
class QuotaService:
    def get_user_quotas(user_id: UUID) -> Dict[str, Optional[int]]
    def check_quota_exceeded(user_id: UUID, quota_type: str) -> bool
    def check_tokens_available(user_id: UUID, estimated_tokens: int) -> bool
    def check_masterplans_available(user_id: UUID) -> bool
    def check_storage_available(user_id: UUID, bytes_needed: int) -> bool
    def update_quotas(user_id: UUID, quotas: Dict[str, Optional[int]]) -> None
```

**6. workspace_service.py**
```python
class WorkspaceService:
    def create_workspace(user_id: UUID) -> Path
    def get_workspace_path(user_id: UUID) -> Path
    def validate_path(user_id: UUID, relative_path: str) -> Path
    def calculate_workspace_size(user_id: UUID) -> int
    def cleanup_workspace(user_id: UUID) -> None
    def initialize_git_repo(user_id: UUID) -> None
```

**7. admin_service.py**
```python
class AdminService:
    def list_users(page: int, per_page: int, filters: Dict) -> Dict[str, Any]
    def get_user_details(user_id: UUID) -> Dict[str, Any]
    def update_user(user_id: UUID, updates: Dict) -> User
    def delete_user(user_id: UUID) -> bool
    def generate_impersonation_token(admin_id: UUID, target_user_id: UUID) -> str
    def get_global_statistics() -> Dict[str, Any]
    def get_usage_by_user(month: Optional[date]) -> List[Dict]
```

#### Modified Services

**8. auth_service.py** (EXISTING - ENHANCE)
- Add email verification token generation
- Add password reset token generation
- Enhance cookie-based token setting
- Add impersonation token generation

**9. masterplan_service.py** (MODIFY)
- Add `user_id` parameter to all methods
- Add quota checks before creation
- Track masterplan creation in usage
- Filter queries by `user_id`

**10. chat_service.py** (MODIFY)
- Add `user_id` parameter to conversation methods
- Filter conversations by `user_id`
- Track LLM usage per user

### Data Flow Diagrams

#### Authentication Flow
```
User Registration:
┌──────┐      ┌─────────┐      ┌──────────┐      ┌──────────┐      ┌──────┐
│Client│      │API Route│      │AuthService│     │  Database │     │Workspace│
└──┬───┘      └────┬────┘      └─────┬────┘      └─────┬────┘      └──┬───┘
   │                │                 │                 │               │
   │ POST /register │                 │                 │               │
   ├───────────────>│                 │                 │               │
   │                │ validate input  │                 │               │
   │                ├────────────────>│                 │               │
   │                │                 │ check duplicates│               │
   │                │                 ├────────────────>│               │
   │                │                 │<────────────────┤               │
   │                │                 │ hash password   │               │
   │                │                 │ create user     │               │
   │                │                 ├────────────────>│               │
   │                │                 │<────────────────┤               │
   │                │                 │                 │ create dir    │
   │                │                 ├─────────────────┼──────────────>│
   │                │                 │                 │<───────────────┤
   │                │                 │ generate tokens │               │
   │                │                 │ set cookies     │               │
   │                │<────────────────┤                 │               │
   │ 201 + cookies  │                 │                 │               │
   │<───────────────┤                 │                 │               │
   │ redirect /dashboard             │                 │               │
   │                │                 │                 │               │

User Login:
┌──────┐      ┌─────────┐      ┌──────────┐      ┌─────────┐
│Client│      │API Route│      │AuthService│     │Database │
└──┬───┘      └────┬────┘      └─────┬────┘      └────┬────┘
   │ POST /login    │                 │                │
   ├───────────────>│                 │                │
   │                │ validate input  │                │
   │                ├────────────────>│                │
   │                │                 │ find user      │
   │                │                 ├───────────────>│
   │                │                 │<───────────────┤
   │                │                 │ verify password│
   │                │                 │ update last_login│
   │                │                 ├───────────────>│
   │                │                 │ generate tokens│
   │                │<────────────────┤                │
   │ 200 + cookies  │                 │                │
   │<───────────────┤                 │                │
   │ redirect /dashboard             │                │
```

#### Password Reset Flow
```
┌──────┐     ┌────────┐     ┌────────────┐     ┌────────┐     ┌─────────┐
│Client│     │API Route│    │ResetService│    │EmailServ│    │Database │
└──┬───┘     └────┬───┘     └─────┬──────┘     └────┬───┘     └────┬────┘
   │ forgot pwd    │               │                 │              │
   ├──────────────>│               │                 │              │
   │               │ request reset │                 │              │
   │               ├──────────────>│                 │              │
   │               │               │ find user       │              │
   │               │               ├─────────────────┼─────────────>│
   │               │               │<────────────────┼──────────────┤
   │               │               │ generate token  │              │
   │               │               ├─────────────────┼─────────────>│
   │               │               │                 │              │
   │               │               │ send email      │              │
   │               │               ├────────────────>│              │
   │               │               │                 │ SMTP         │
   │               │               │                 ├─────────────>│
   │               │<──────────────┤                 │              │
   │ 200 success   │               │                 │              │
   │<──────────────┤               │                 │              │
   │               │               │                 │              │
   │ (user clicks email link)      │                 │              │
   │               │               │                 │              │
   │ reset pwd     │               │                 │              │
   ├──────────────>│               │                 │              │
   │               │ verify token  │                 │              │
   │               ├──────────────>│                 │              │
   │               │               │ validate token  │              │
   │               │               ├─────────────────┼─────────────>│
   │               │               │<────────────────┼──────────────┤
   │               │               │ hash new pwd    │              │
   │               │               │ update user     │              │
   │               │               ├─────────────────┼─────────────>│
   │               │<──────────────┤                 │              │
   │ 200 success   │               │                 │              │
   │<──────────────┤               │                 │              │
   │ redirect /login               │                 │              │
```

#### Multi-tenancy Data Isolation
```
User A requests masterplan:
┌───────┐     ┌─────────┐     ┌──────────┐     ┌────────────┐
│User A │     │API Route│     │Middleware│     │  Database  │
└───┬───┘     └────┬────┘     └────┬─────┘     └─────┬──────┘
    │              │               │                  │
    │ GET /masterplans            │                  │
    ├─────────────>│               │                  │
    │              │ verify token  │                  │
    │              ├──────────────>│                  │
    │              │ extract user_id (A)             │
    │              │<──────────────┤                  │
    │              │               │                  │
    │              │ query with filter(user_id=A)    │
    │              ├─────────────────────────────────>│
    │              │               │                  │
    │              │               │ SELECT * FROM masterplans
    │              │               │ WHERE user_id = 'A'
    │              │               │                  │
    │              │ [User A's masterplans only]     │
    │              │<─────────────────────────────────┤
    │ 200 + data   │               │                  │
    │<─────────────┤               │                  │
    │              │               │                  │

User B tries to access User A's masterplan:
┌───────┐     ┌─────────┐     ┌──────────┐     ┌────────────┐
│User B │     │API Route│     │Middleware│     │  Database  │
└───┬───┘     └────┬────┘     └────┬─────┘     └─────┬──────┘
    │              │               │                  │
    │ GET /masterplans/{A's ID}   │                  │
    ├─────────────>│               │                  │
    │              │ verify token  │                  │
    │              ├──────────────>│                  │
    │              │ extract user_id (B)             │
    │              │<──────────────┤                  │
    │              │               │                  │
    │              │ query with filter(id=A's ID AND user_id=B)
    │              ├─────────────────────────────────>│
    │              │               │                  │
    │              │               │ SELECT * FROM masterplans
    │              │               │ WHERE id = 'A_ID' AND user_id = 'B'
    │              │               │                  │
    │              │ (no results)  │                  │
    │              │<─────────────────────────────────┤
    │ 404 Not Found│               │                  │
    │<─────────────┤               │                  │
```

#### Usage Tracking Flow
```
User makes LLM call:
┌──────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌─────────┐
│Client│    │API Route │    │LLM Service│   │UsageService│   │Database │
└──┬───┘    └────┬─────┘    └─────┬────┘    └─────┬─────┘    └────┬────┘
   │ chat msg     │                │                │               │
   ├─────────────>│                │                │               │
   │              │ check quota    │                │               │
   │              ├────────────────┼────────────────>│               │
   │              │                │                │ get usage     │
   │              │                │                ├──────────────>│
   │              │                │                │<──────────────┤
   │              │                │                │ check limit   │
   │              │<───────────────┼────────────────┤               │
   │              │ (OK)           │                │               │
   │              │                │                │               │
   │              │ call LLM       │                │               │
   │              ├───────────────>│                │               │
   │              │                │ Anthropic API  │               │
   │              │                ├───────────────>│               │
   │              │                │<───────────────┤               │
   │              │                │ (tokens: 1500) │               │
   │              │                │                │               │
   │              │                │ track usage    │               │
   │              │                ├────────────────>│               │
   │              │                │                │ UPDATE usage  │
   │              │                │                │ SET tokens += 1500
   │              │                │                ├──────────────>│
   │              │<───────────────┤                │               │
   │ response     │                │                │               │
   │<─────────────┤                │                │               │
```

---

## Database Migrations

### Migration Plan

**Step 1: Create Migration File**
```bash
alembic revision -m "add_authentication_and_multi_tenancy"
```

**Step 2: Migration Content (alembic/versions/xxx_add_auth.py)**

```python
"""add authentication and multi-tenancy

Revision ID: xxx
Revises: previous_revision
Create Date: 2025-10-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add new columns to users table
    op.add_column('users', sa.Column('is_verified', sa.Boolean(),
                  nullable=False, server_default='true'))
    op.add_column('users', sa.Column('verification_token',
                  postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('verification_token_created_at',
                  sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token',
                  postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires',
                  sa.DateTime(), nullable=True))

    # Create indexes on new columns
    op.create_index('idx_users_verification_token', 'users',
                    ['verification_token'])
    op.create_index('idx_users_password_reset_token', 'users',
                    ['password_reset_token'])

    # 2. Create user_quotas table
    op.create_table(
        'user_quotas',
        sa.Column('quota_id', postgresql.UUID(as_uuid=True),
                  primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  nullable=False, unique=True),
        sa.Column('llm_tokens_monthly_limit', sa.Integer(), nullable=True),
        sa.Column('masterplans_limit', sa.Integer(), nullable=True),
        sa.Column('storage_bytes_limit', sa.BigInteger(), nullable=True),
        sa.Column('api_calls_per_minute', sa.Integer(),
                  nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'))
    )

    # Foreign key
    op.create_foreign_key('fk_quota_user', 'user_quotas', 'users',
                          ['user_id'], ['user_id'], ondelete='CASCADE')

    # Index
    op.create_index('idx_user_quotas_user', 'user_quotas', ['user_id'])

    # 3. Create user_usage table
    op.create_table(
        'user_usage',
        sa.Column('usage_id', postgresql.UUID(as_uuid=True),
                  primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('llm_tokens_used', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('llm_cost_usd', sa.Numeric(10, 4),
                  nullable=False, server_default='0.0'),
        sa.Column('masterplans_created', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('storage_bytes', sa.BigInteger(),
                  nullable=False, server_default='0'),
        sa.Column('api_calls', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'))
    )

    # Foreign key and unique constraint
    op.create_foreign_key('fk_usage_user', 'user_usage', 'users',
                          ['user_id'], ['user_id'], ondelete='CASCADE')
    op.create_unique_constraint('uq_user_usage_user_month', 'user_usage',
                                ['user_id', 'month'])

    # Indexes
    op.create_index('idx_user_usage_user_month', 'user_usage',
                    ['user_id', 'month'])
    op.create_index('idx_user_usage_month', 'user_usage', ['month'])

    # 4. Create conversations table
    op.create_table(
        'conversations',
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True),
                  primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'))
    )

    # Foreign key
    op.create_foreign_key('fk_conversation_user', 'conversations', 'users',
                          ['user_id'], ['user_id'], ondelete='CASCADE')

    # Indexes
    op.create_index('idx_conversations_user', 'conversations', ['user_id'])
    op.create_index('idx_conversations_created', 'conversations',
                    ['created_at'], postgresql_ops={'created_at': 'DESC'})

    # 5. Create messages table
    op.create_table(
        'messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True),
                  primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()'))
    )

    # Foreign key
    op.create_foreign_key('fk_message_conversation', 'messages',
                          'conversations', ['conversation_id'],
                          ['conversation_id'], ondelete='CASCADE')

    # Indexes
    op.create_index('idx_messages_conversation', 'messages',
                    ['conversation_id'])
    op.create_index('idx_messages_created', 'messages', ['created_at'],
                    postgresql_ops={'created_at': 'DESC'})

    # 6. Modify existing tables - discovery_documents
    # Change user_id from String to UUID FK
    op.execute('ALTER TABLE discovery_documents ALTER COLUMN user_id TYPE UUID USING user_id::uuid')
    op.create_foreign_key('fk_discovery_user', 'discovery_documents', 'users',
                          ['user_id'], ['user_id'], ondelete='CASCADE')
    op.create_index('idx_discovery_user', 'discovery_documents', ['user_id'])

    # 7. Modify existing tables - masterplans
    # Change user_id from String to UUID FK
    op.execute('ALTER TABLE masterplans ALTER COLUMN user_id TYPE UUID USING user_id::uuid')
    op.create_foreign_key('fk_masterplan_user', 'masterplans', 'users',
                          ['user_id'], ['user_id'], ondelete='CASCADE')
    op.create_index('idx_masterplans_user', 'masterplans', ['user_id'])


def downgrade():
    # Reverse all changes

    # Drop indexes and foreign keys
    op.drop_index('idx_masterplans_user', 'masterplans')
    op.drop_constraint('fk_masterplan_user', 'masterplans', type_='foreignkey')
    op.execute('ALTER TABLE masterplans ALTER COLUMN user_id TYPE VARCHAR(100)')

    op.drop_index('idx_discovery_user', 'discovery_documents')
    op.drop_constraint('fk_discovery_user', 'discovery_documents', type_='foreignkey')
    op.execute('ALTER TABLE discovery_documents ALTER COLUMN user_id TYPE VARCHAR(100)')

    # Drop tables
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('user_usage')
    op.drop_table('user_quotas')

    # Drop columns from users
    op.drop_index('idx_users_password_reset_token', 'users')
    op.drop_index('idx_users_verification_token', 'users')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'verification_token_created_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
```

**Step 3: Apply Migration**
```bash
# Backup database first
pg_dump devmatrix_db > backup_pre_auth_$(date +%Y%m%d).sql

# Run migration
alembic upgrade head

# Verify
psql devmatrix_db -c "\dt"
psql devmatrix_db -c "\d users"
psql devmatrix_db -c "\d user_quotas"
psql devmatrix_db -c "\d user_usage"
```

**Step 4: Create Initial Admin**
```bash
# Option 1: CLI command
python -m src.cli.create_admin \
  --email admin@devmatrix.com \
  --username admin \
  --password <secure-password>

# Option 2: SQL (if CLI not ready)
psql devmatrix_db <<EOF
INSERT INTO users (email, username, password_hash, is_superuser, is_verified)
VALUES (
  'admin@devmatrix.com',
  'admin',
  '<bcrypt-hash>',
  true,
  true
);
EOF
```

---

## Reusable Components

### Existing Code to Leverage

**Backend (Python)**

1. **User Model** (`src/models/user.py`)
   - Complete implementation with UUID, email, username, password_hash
   - Includes `is_active`, `is_superuser`, timestamps
   - `to_dict()` method for JSON serialization
   - **Action**: Extend with new columns (is_verified, tokens)

2. **AuthService** (`src/services/auth_service.py`)
   - Password hashing/verification with bcrypt
   - JWT token creation/verification (access + refresh)
   - User registration with duplicate checks
   - Login with validation and last_login update
   - **Action**: Add email verification and password reset methods

3. **Auth API Router** (`src/api/routers/auth.py`)
   - Registration, login, refresh, me, logout endpoints
   - Request/response Pydantic models
   - Error handling and logging
   - **Action**: Add new endpoints for verification and reset

4. **Auth Middleware** (`src/api/middleware/auth_middleware.py`)
   - `get_current_user()`, `get_current_active_user()`, `get_current_superuser()`
   - Token extraction from Authorization header
   - User account status validation
   - **Action**: Add cookie-based token extraction

5. **Database Configuration** (`src/config/database.py`)
   - SQLAlchemy Base and get_db_context
   - PostgreSQL connection management
   - **Action**: No changes needed

6. **Observability** (`src/observability/`)
   - Logging with get_logger
   - **Action**: Add auth event logging

**Frontend (React/TypeScript)**

7. **App Routing** (`src/ui/src/App.tsx`)
   - React Router with Routes and navigation
   - Sidebar navigation with FiHome, FiMessageSquare, FiTarget, FiSettings icons
   - Dark mode support with ThemeContext
   - **Action**: Add auth routes, wrap with AuthProvider, add PrivateRoute

8. **Tailwind Design System**
   - Dark mode classes (dark:bg-gray-900, dark:text-white)
   - Primary colors (primary-600, primary-700)
   - Card layouts with borders (border-gray-200 dark:border-gray-700)
   - Button styles (px-6 py-3 bg-primary-600 rounded-lg)
   - **Action**: Reuse for auth pages

9. **React Hooks**
   - Custom hooks pattern (useChatStore, useTheme)
   - **Action**: Create useAuth hook

10. **Component Patterns**
    - Card-based layouts for content sections
    - Loading states with spinners
    - Error message display
    - **Action**: Reuse in auth forms

**Infrastructure**

11. **Redis** (Already configured)
    - Used for rate limiting
    - **Action**: Add rate limit middleware

12. **Alembic Migrations** (Already configured)
    - Migration system in place
    - **Action**: Create new migration for auth tables

### New Components Required

**Backend**

1. **Email Service** - Doesn't exist yet, need SMTP integration
2. **Password Reset Service** - Core logic for token generation and validation
3. **Email Verification Service** - Token management and verification flow
4. **Usage Tracking Service** - Track LLM tokens, masterplans, storage
5. **Quota Service** - Check and enforce quotas
6. **Workspace Service** - File system operations with user isolation
7. **Admin Service** - Admin-specific operations and statistics
8. **Rate Limiting Middleware** - slowapi integration with Redis

**Frontend**

9. **All Authentication Pages** - Login, Register, ForgotPassword, ResetPassword, VerifyEmail pages don't exist
10. **User Profile Page** - Profile with usage stats doesn't exist
11. **Auth Context/Provider** - Global auth state management doesn't exist
12. **Protected Route Wrappers** - PrivateRoute and AdminRoute don't exist
13. **User Menu Dropdown** - Header user menu doesn't exist
14. **Usage Badge** - Token usage indicator doesn't exist

**Why New Code is Needed:**
- Existing auth is basic (login/register only)
- No email verification or password reset flows
- No multi-tenancy (user_id filtering) in queries
- No usage tracking or quota enforcement
- No admin capabilities
- Frontend has no auth UI or protected routes

---

## Security Considerations

### Password Security
- Bcrypt hashing with cost factor 12 (already implemented)
- Minimum 8 characters, no maximum (allow passphrases)
- Password reset tokens single-use and expire after 1 hour
- Invalidate all refresh tokens after password reset

### Token Security
- JWT signed with HS256 algorithm
- Access tokens short-lived (1 hour) to limit exposure
- Refresh tokens long-lived (30 days) but httpOnly
- Token payload: user_id, email, username, is_superuser, type, exp, iat
- No sensitive data in JWT (no password hashes, payment info)
- Impersonation tokens include admin_id for audit trail

### Session Security
- httpOnly cookies prevent XSS token theft (JavaScript cannot access)
- Secure flag ensures HTTPS-only transmission (production)
- SameSite=Strict prevents CSRF attacks
- CORS configured to allow only trusted frontend origin
- Credentials required for all API calls

### API Security
- All endpoints (except auth) require valid JWT
- Rate limiting prevents brute force and DoS attacks
- Input validation via Pydantic models
- SQL injection prevented by SQLAlchemy ORM
- Path traversal protection in file operations (workspace validation)
- User isolation: Users can only access their own resources

### Email Security
- Password reset links expire after 1 hour
- Verification links expire after 24 hours
- Don't reveal whether email exists (forgot password)
- Rate limit email sending to prevent spam
- Use SPF, DKIM, DMARC for email authentication (SMTP provider)

### Admin Security
- All admin endpoints require `is_superuser=true`
- Cannot impersonate other admins
- Impersonation tokens expire after 1 hour
- All admin actions logged with user IDs

### Data Security
- Foreign key constraints enforce referential integrity
- `ON DELETE CASCADE` ensures consistent cleanup
- Automatic query filtering by user_id
- Return 404 (not 403) for unauthorized resources (prevent enumeration)
- Workspace path validation prevents directory traversal

---

## Non-Functional Requirements

### Performance Targets

**API Response Times**
- Authentication endpoints: < 200ms (excluding email sending)
- User data endpoints: < 100ms
- Admin endpoints: < 500ms
- Rate limit checks: < 10ms (Redis lookup)

**Database Performance**
- Indexes on all foreign keys (user_id columns)
- Compound index on user_usage(user_id, month)
- Connection pooling (SQLAlchemy default pool size: 5-20)
- Query optimization: Use select_related for joins
- Pagination for all list endpoints (max 100 items per page)

**Caching Strategy**
- User quotas cached in Redis (5 minute TTL)
- Usage statistics cached (1 minute TTL)
- Global statistics cached (5 minute TTL)
- Rate limiting uses Redis for fast counter checks

**Scalability**
- Stateless JWT allows horizontal scaling
- Rate limiting uses shared Redis
- Session data in database, not in-memory
- User data partitionable by user_id

### Reliability

**Error Handling**
- Consistent error format:
```json
{
  "error": "Error message",
  "detail": "Additional details",
  "code": "ERROR_CODE"
}
```
- Log all errors with context (user_id, endpoint, timestamp)
- Graceful degradation: If email service down, allow registration with warning

**Data Integrity**
- Foreign key constraints ensure referential integrity
- Unique constraints on email, username
- Database transactions for multi-step operations
- Cascading deletes for user data cleanup

**Monitoring**
- Log all authentication events (login, logout, failed attempts)
- Track rate limit violations
- Monitor quota usage and alert when users exceed 90%
- Track API error rates and slow endpoints

### Observability

**Logging**
- All auth events (registration, login, logout, password reset)
- Rate limit violations with IP and user_id
- Quota exceeded errors
- Admin actions (user updates, impersonation)
- LLM token usage per call

**Metrics to Track**
- User registration rate
- Login success/failure rate
- Token refresh rate
- Password reset request rate
- Average LLM tokens per user
- Storage usage trends
- API error rates by endpoint

**Alerts to Configure**
- Failed login rate > 10 per minute (potential attack)
- Email service down
- Rate limit violations > 100 per minute
- Database connection errors
- Any user exceeding 90% of quota (upsell opportunity)

---

## Testing Strategy

### Unit Tests (90%+ Coverage)

**Backend Services**
- `tests/services/test_auth_service.py` (extend existing)
  - Test email verification token generation
  - Test password reset token generation
  - Test token expiry validation

- `tests/services/test_email_service.py` (new)
  - Test SMTP connection
  - Test email template rendering
  - Test send failures and retries

- `tests/services/test_password_reset_service.py` (new)
  - Test reset request flow
  - Test token validation
  - Test password update
  - Test expired token handling

- `tests/services/test_usage_tracking_service.py` (new)
  - Test LLM token tracking
  - Test masterplan counting
  - Test storage calculation
  - Test monthly aggregation

- `tests/services/test_quota_service.py` (new)
  - Test quota checks
  - Test grace periods
  - Test unlimited quotas (null values)

- `tests/services/test_workspace_service.py` (new)
  - Test workspace creation
  - Test path validation (prevent traversal)
  - Test size calculation

**Backend API**
- `tests/api/test_auth_endpoints.py` (extend existing)
  - Test all new endpoints (verify-email, resend-verification, forgot-password, reset-password)
  - Test rate limiting
  - Test error cases

- `tests/api/test_admin_endpoints.py` (new)
  - Test user management endpoints
  - Test impersonation
  - Test statistics endpoints
  - Test authorization (non-admin access denied)

### Integration Tests

**Full Authentication Flows**
- `tests/integration/test_auth_flow.py`
  - Test: Register → Verify Email → Login → Use API → Logout
  - Test: Register → Login (verification disabled)
  - Test: Forgot Password → Reset → Login
  - Test: Login → Token Refresh → Use API

**Multi-tenancy Tests**
- `tests/integration/test_multi_tenancy.py`
  - Test: User A cannot access User B's masterplans
  - Test: User A cannot access User B's conversations
  - Test: User A cannot access User B's workspace files
  - Test: All queries automatically filtered by user_id
  - Test: Direct API calls with wrong user_id return 404

**Usage Tracking Tests**
- `tests/integration/test_usage_tracking.py`
  - Test: LLM call tracked correctly
  - Test: Quota exceeded returns 429
  - Test: Masterplan creation increments counter
  - Test: Storage calculation updates usage

**Rate Limiting Tests**
- `tests/integration/test_rate_limiting.py`
  - Test: 6th login attempt within 1 minute returns 429
  - Test: 31st API call within 1 minute returns 429
  - Test: Rate limit headers present
  - Test: Rate limit resets after time window

### End-to-End Tests

**Frontend + Backend**
- `tests/e2e/test_auth_ui.py`
  - Test: User completes registration via UI
  - Test: User logs in via UI
  - Test: Password reset via UI works end-to-end
  - Test: Protected routes redirect to login
  - Test: Usage stats display correctly

**Admin Flows**
- `tests/e2e/test_admin_ui.py`
  - Test: Admin can view all users
  - Test: Admin can deactivate user
  - Test: Admin can adjust quotas
  - Test: Admin can impersonate user

### Security Tests

**Penetration Testing**
- Test: SQL injection attempts blocked
- Test: XSS attempts blocked (httpOnly cookies)
- Test: Path traversal attempts blocked (workspace)
- Test: CSRF attempts blocked (SameSite cookies)
- Test: User cannot access other user's data via API manipulation

**Authentication Security**
- Test: Expired tokens rejected
- Test: Invalid tokens rejected
- Test: Inactive user cannot login
- Test: Password reset token single-use
- Test: Brute force attempts rate limited

### Performance Tests

**Load Testing**
- Test: 100 concurrent logins (< 200ms avg response)
- Test: 1000 API calls with rate limiting (check Redis performance)
- Test: Large user list pagination (1000+ users)

---

## Deployment Plan

### Environment Variables

**Required New Variables** (add to .env.example):

```bash
# Email Configuration
EMAIL_VERIFICATION_REQUIRED=false
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxxxx
SMTP_FROM_EMAIL=noreply@devmatrix.com
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

# Session (existing, verify values)
JWT_SECRET_KEY=your-secret-key-change-in-production-IMPORTANT
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Database (existing)
DATABASE_URL=postgresql://user:pass@localhost:5432/devmatrix_db

# Redis (existing)
REDIS_URL=redis://localhost:6379/0
```

### Database Migration Steps

**Pre-Deployment Checklist**
1. [ ] Backup production database: `pg_dump devmatrix_db > backup_$(date +%Y%m%d).sql`
2. [ ] Test migration on staging environment
3. [ ] Verify rollback procedure works
4. [ ] Schedule maintenance window (expected: 5-10 minutes)

**Deployment Steps**
```bash
# 1. Backup database
pg_dump devmatrix_db > backup_pre_auth_$(date +%Y%m%d_%H%M%S).sql

# 2. Run migration
alembic upgrade head

# 3. Verify schema
psql devmatrix_db <<EOF
\dt
\d users
\d user_quotas
\d user_usage
\d conversations
\d messages
SELECT * FROM alembic_version;
EOF

# 4. Create initial admin
python -m src.cli.create_admin \
  --email admin@devmatrix.com \
  --username admin \
  --password $(openssl rand -base64 32)

# 5. Verify admin created
psql devmatrix_db -c "SELECT user_id, email, is_superuser FROM users WHERE is_superuser = true;"

# 6. Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@devmatrix.com","password":"<admin-password>"}'
```

### Rollback Plan

**If migration fails or issues found:**

```bash
# 1. Stop application
systemctl stop devmatrix-api

# 2. Rollback database migration
alembic downgrade -1

# 3. Restore from backup (if needed)
psql devmatrix_db < backup_pre_auth_YYYYMMDD_HHMMSS.sql

# 4. Restart application with old code
git checkout previous_release
systemctl start devmatrix-api

# 5. Verify system operational
curl http://localhost:8000/api/v1/health
```

### Monitoring Setup

**Post-Deployment Monitoring**

1. **Application Logs**
   - Monitor for authentication errors: `tail -f logs/app.log | grep "auth"`
   - Monitor for rate limit violations: `tail -f logs/app.log | grep "429"`
   - Monitor for quota exceeded: `tail -f logs/app.log | grep "quota"`

2. **Database Monitoring**
   - Check connection pool usage
   - Monitor slow queries: `SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;`
   - Monitor table sizes: `SELECT pg_size_pretty(pg_total_relation_size('users'));`

3. **Redis Monitoring**
   - Check memory usage: `redis-cli info memory`
   - Monitor rate limit keys: `redis-cli keys "rate_limit:*"`

4. **Email Service Monitoring**
   - Check SendGrid dashboard for delivery rates
   - Monitor bounce and spam rates
   - Set up alerts for service issues

5. **User Metrics**
   - Track registration rate (expected spike on launch)
   - Monitor login success rate (should be > 95%)
   - Track quota usage trends

### Feature Flags

**Progressive Rollout** (if desired):

```python
# config/feature_flags.py
FEATURES = {
    "email_verification": os.getenv("EMAIL_VERIFICATION_REQUIRED", "false") == "true",
    "rate_limiting": os.getenv("ENABLE_RATE_LIMITING", "true") == "true",
    "usage_tracking": os.getenv("ENABLE_USAGE_TRACKING", "true") == "true",
    "admin_dashboard": os.getenv("ENABLE_ADMIN_DASHBOARD", "true") == "true"
}
```

This allows disabling features quickly if issues arise.

---

## Migration Strategy

### Decision: Start Fresh

**Rationale:**
- No existing production users with data to migrate
- Clean slate simplifies initial rollout
- Avoid complexity of migrating String user_ids to UUID FKs
- Faster time to production

**Implications:**
- Current local development data will be discarded
- First production deployment will have no users
- Developers will need to re-register after deployment

### Initial Superuser Creation

**Option 1: CLI Command** (Recommended for Production)
```bash
python -m src.cli.create_admin \
  --email admin@devmatrix.com \
  --username admin \
  --password <secure-password>
```

**Option 2: First User is Admin** (Convenient for Development)
- Set `FIRST_USER_IS_ADMIN=true` in .env
- First user to register gets `is_superuser=true`
- Subsequent users are normal users
- **Important**: Disable in production to prevent wrong user becoming admin

**Recommendation**: Use Option 1 for production, Option 2 for development

### Data Cleanup Steps

If you have existing test data:

```bash
# Option 1: Drop and recreate database
dropdb devmatrix_db
createdb devmatrix_db
psql devmatrix_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
alembic upgrade head

# Option 2: Delete all data from tables (keeps schema)
psql devmatrix_db <<EOF
TRUNCATE TABLE messages CASCADE;
TRUNCATE TABLE conversations CASCADE;
TRUNCATE TABLE masterplans CASCADE;
TRUNCATE TABLE discovery_documents CASCADE;
TRUNCATE TABLE users CASCADE;
EOF
```

---

## Open Questions & Decisions

### Decisions Made

1. **JWT Storage**: httpOnly cookies (more secure than localStorage)
2. **Token Expiry**: 1 hour access, 30 days refresh (balances security and UX)
3. **Email Verification**: Optional via env var (allows phased rollout)
4. **Password Reset Tokens**: Store in users table (simpler than separate table)
5. **Rate Limiting Library**: slowapi (mature, good docs)
6. **Email Service**: SendGrid (simple, reliable, good free tier)
7. **Soft Delete**: `is_active=false` with 30-day retention (allows recovery)
8. **Storage Calculation**: Daily cron job (async, doesn't block writes)
9. **Impersonation Duration**: 1 hour max (security balance)
10. **Default Quotas**: 1M tokens/month, 50 masterplans, 5 GB storage, 30 API calls/min
11. **Migration Strategy**: Start fresh (no data migration)
12. **First Admin**: CLI command (secure, explicit)

### Remaining Open Questions

*None* - All questions resolved based on requirements analysis.

---

## Acceptance Criteria

### Authentication (FR-AUTH)

**Registration**
- [ ] User can register with valid email, username (3-50 chars), password (8+ chars)
- [ ] System rejects duplicate email with "Email already registered" error
- [ ] System rejects duplicate username with "Username already taken" error
- [ ] Password hashed with bcrypt (cost factor 12) before storage
- [ ] User created with `is_active=True`, `is_superuser=False`
- [ ] If `EMAIL_VERIFICATION_REQUIRED=false`, user created with `is_verified=True`
- [ ] If `EMAIL_VERIFICATION_REQUIRED=true`, verification email sent
- [ ] User workspace created at `/workspaces/{user_id}/`
- [ ] Default quotas assigned
- [ ] Access and refresh tokens returned in response

**Email Verification**
- [ ] Verification email sent on registration (when required)
- [ ] Email contains link with 24-hour valid token
- [ ] Clicking link calls `/api/v1/auth/verify-email` and sets `is_verified=True`
- [ ] Invalid/expired token returns 400 error with clear message
- [ ] User can resend verification email (rate limited: 1 per 2 minutes)
- [ ] Already verified user sees "Email already verified" message

**Login**
- [ ] User can login with valid email and password
- [ ] Invalid credentials return 401 "Invalid email or password"
- [ ] Inactive account returns 403 "Account is inactive"
- [ ] `last_login_at` timestamp updated on success
- [ ] Access token (1 hour) and refresh token (30 days) returned
- [ ] Tokens set as httpOnly cookies
- [ ] Failed login attempts rate limited (5 per minute per IP)

**Password Reset**
- [ ] User can request reset via `/api/v1/auth/forgot-password`
- [ ] Reset email sent (if email exists)
- [ ] Email contains link with 1-hour valid token
- [ ] User can reset password with valid token
- [ ] Invalid/expired token returns 400 error
- [ ] New password meets requirements (8+ chars)
- [ ] Always returns generic success message (prevent email enumeration)
- [ ] Rate limited: 3 requests per hour per IP

**Token Management**
- [ ] Access tokens expire after 1 hour (configurable)
- [ ] Refresh tokens expire after 30 days (configurable)
- [ ] `/api/v1/auth/refresh` generates new access token
- [ ] Expired refresh token returns 401
- [ ] Tokens stored in httpOnly cookies with Secure and SameSite=Strict
- [ ] `/api/v1/auth/logout` clears cookies

### Multi-tenancy (FR-TENANT)

**Database Schema**
- [ ] `users` table has new columns: `is_verified`, `verification_token`, `verification_token_created_at`, `password_reset_token`, `password_reset_expires`
- [ ] `user_quotas` table exists with FK to users
- [ ] `user_usage` table exists with unique constraint on (user_id, month)
- [ ] `conversations` table exists with user_id FK
- [ ] `messages` table exists with conversation_id FK
- [ ] `discovery_documents.user_id` changed to UUID FK
- [ ] `masterplans.user_id` changed to UUID FK
- [ ] All indexes created for performance

**Workspace Isolation**
- [ ] Each user has directory at `/workspaces/{user_id}/`
- [ ] Workspace created automatically on registration
- [ ] Git repository initialized in workspace
- [ ] File operations scoped to user's workspace
- [ ] Path traversal attempts blocked (validation returns error)

**Query Filtering**
- [ ] All masterplan queries filtered by current user's `user_id`
- [ ] All conversation queries filtered by current user's `user_id`
- [ ] Attempting to access another user's resource returns 404 (not 403)
- [ ] User cannot access other users' data via direct API calls

### Usage Tracking (FR-USAGE)

**Token Tracking**
- [ ] Every LLM call tracked: user_id, model, tokens, cost, timestamp
- [ ] Monthly totals aggregated in `user_usage` table
- [ ] Quota checked before LLM call
- [ ] Returns 429 if quota exceeded with usage details
- [ ] 5% grace period allowed (1.05M if limit is 1M)
- [ ] Usage displayed in `/api/v1/users/me/usage` response

**Masterplan Tracking**
- [ ] Masterplan creation increments `masterplans_created` counter
- [ ] Quota checked before creation
- [ ] Returns 429 if limit reached
- [ ] Count displayed in user profile

**Storage Tracking**
- [ ] Daily background job calculates workspace size
- [ ] `storage_bytes` updated in `user_usage` table
- [ ] Quota checked on file writes
- [ ] Returns 413 if storage quota exceeded
- [ ] Storage displayed with human-readable format (125 MB / 5 GB)

### Admin Features (FR-ADMIN)

**User Management**
- [ ] Admin can view all users via `/api/v1/admin/users` (paginated)
- [ ] Admin can search and filter users
- [ ] Admin can view individual user details
- [ ] Admin can activate/deactivate users
- [ ] Admin can soft delete users
- [ ] All admin endpoints require `is_superuser=true`
- [ ] Non-admin users get 403 error

**Global Statistics**
- [ ] Admin can view stats via `/api/v1/admin/statistics`
- [ ] Shows total/active users, new users this month/today
- [ ] Shows total LLM usage and cost this month and all-time
- [ ] Shows top users by token usage
- [ ] Statistics cached for 5 minutes

**Quota Management**
- [ ] Admin can view user quotas
- [ ] Admin can update quotas via `/api/v1/admin/users/{user_id}/quotas`
- [ ] Setting quota to `null` = unlimited
- [ ] Changes take effect immediately

**Impersonation**
- [ ] Admin can impersonate users via `/api/v1/admin/impersonate/{user_id}`
- [ ] Impersonation token includes `impersonating=true` claim
- [ ] Token valid for 1 hour max
- [ ] Cannot impersonate other admins (returns 403)
- [ ] All actions logged with both admin and target user IDs

### Rate Limiting (FR-RATE)

**Authentication Endpoints**
- [ ] Login/register/reset limited to 5 requests per minute per IP
- [ ] Uses Redis for counter storage
- [ ] Returns 429 status when exceeded
- [ ] Response includes `Retry-After` header

**API Endpoints**
- [ ] Chat endpoints limited to 30 requests per minute per user
- [ ] Masterplan endpoints limited to 20 requests per minute
- [ ] Admin endpoints limited to 100 requests per minute
- [ ] Rate limits configurable per user in `user_quotas`

**Rate Limit Headers**
- [ ] All responses include `X-RateLimit-Limit`
- [ ] All responses include `X-RateLimit-Remaining`
- [ ] All responses include `X-RateLimit-Reset`
- [ ] 429 responses include `Retry-After`

### Frontend (FR-UI)

**Authentication Pages**
- [ ] Login page exists at `/login`
- [ ] Registration page exists at `/register`
- [ ] Forgot password page exists at `/forgot-password`
- [ ] Reset password page exists at `/reset-password`
- [ ] Email verification page exists at `/verify-email`
- [ ] All pages match DevMatrix design system (dark mode, Tailwind)

**User Profile**
- [ ] Profile page exists at `/profile`
- [ ] Shows account info: email, username, created date, last login
- [ ] Shows usage stats: tokens, masterplans, storage with progress bars
- [ ] Progress bars color-coded: green < 80%, yellow 80-95%, red > 95%
- [ ] "Change Password" button works
- [ ] "Logout" button clears session and redirects to login

**Navigation**
- [ ] Header shows user menu dropdown (avatar + username)
- [ ] Dropdown includes: Profile, Settings, Logout
- [ ] Header shows usage badge with token consumption
- [ ] Badge color-coded by percentage
- [ ] Clicking badge navigates to profile

**Protected Routes**
- [ ] All routes except auth pages require authentication
- [ ] Unauthenticated users redirected to `/login?redirect={path}`
- [ ] After login, redirect to originally requested page
- [ ] Admin routes require `is_superuser=true`
- [ ] Non-admin users see 403 error on admin routes

**Auth State**
- [ ] Auth context provides `user`, `isAuthenticated`, `login()`, `logout()`
- [ ] Token auto-refresh works (refresh when < 5 min remaining)
- [ ] 401 errors redirect to login globally
- [ ] User state persists across page refreshes

### Security

**Password Security**
- [ ] Passwords hashed with bcrypt cost factor 12
- [ ] Minimum 8 characters enforced
- [ ] Password reset tokens expire after 1 hour
- [ ] Password reset tokens single-use

**Token Security**
- [ ] JWT signed with HS256
- [ ] Access tokens expire after 1 hour
- [ ] Refresh tokens expire after 30 days
- [ ] No sensitive data in JWT payload

**Session Security**
- [ ] httpOnly cookies prevent XSS
- [ ] Secure flag set in production
- [ ] SameSite=Strict prevents CSRF
- [ ] CORS allows only trusted origin

**API Security**
- [ ] All protected endpoints require valid JWT
- [ ] Rate limiting prevents brute force
- [ ] Input validation via Pydantic
- [ ] Path traversal blocked in file ops

### Performance

**Response Times**
- [ ] Auth endpoints < 200ms
- [ ] User data endpoints < 100ms
- [ ] Admin endpoints < 500ms
- [ ] Rate limit checks < 10ms

**Database**
- [ ] Indexes on all user_id columns
- [ ] Compound index on user_usage(user_id, month)
- [ ] Queries use pagination (max 100 items)

**Caching**
- [ ] User quotas cached (5 min TTL)
- [ ] Usage stats cached (1 min TTL)
- [ ] Global stats cached (5 min TTL)

### Testing

**Unit Tests**
- [ ] All new services have 90%+ test coverage
- [ ] Auth service tests pass
- [ ] Email service tests pass
- [ ] Usage tracking tests pass
- [ ] Quota service tests pass

**Integration Tests**
- [ ] Full auth flow test passes (register → verify → login → use)
- [ ] Multi-tenancy isolation test passes
- [ ] Usage tracking test passes
- [ ] Rate limiting test passes

**E2E Tests**
- [ ] User can complete registration via UI
- [ ] User can login via UI
- [ ] Password reset via UI works
- [ ] Protected routes redirect correctly
- [ ] Admin can manage users via UI

---

## Appendix

### Glossary

- **JWT (JSON Web Token)**: Stateless authentication token format
- **Bcrypt**: Password hashing algorithm with salt
- **httpOnly Cookie**: Cookie that JavaScript cannot access (XSS protection)
- **SameSite Cookie**: Cookie that browsers only send to same-origin requests (CSRF protection)
- **Rate Limiting**: Restricting number of requests per time window
- **Multi-tenancy**: Single application serving multiple isolated users/organizations
- **Quota**: Limit on resource consumption (tokens, storage, etc.)
- **Soft Delete**: Marking record as deleted without removing from database
- **UUID**: Universally Unique Identifier (128-bit number)
- **FK (Foreign Key)**: Database constraint linking records across tables
- **SMTP**: Simple Mail Transfer Protocol (email sending)
- **Redis**: In-memory data store for caching and rate limiting
- **Alembic**: Database migration tool for SQLAlchemy
- **CORS (Cross-Origin Resource Sharing)**: Browser security for API access from different domains

### References

**Existing Code Files**:
- `src/models/user.py` - User model (extend)
- `src/services/auth_service.py` - Auth service (extend)
- `src/api/routers/auth.py` - Auth endpoints (extend)
- `src/api/middleware/auth_middleware.py` - Auth middleware (extend)
- `src/config/database.py` - Database config (use as-is)
- `src/ui/src/App.tsx` - Main app (modify for auth)

**External Documentation**:
- JWT: https://jwt.io/introduction
- Bcrypt: https://github.com/pyca/bcrypt
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- React Router: https://reactrouter.com/en/main
- Tailwind CSS: https://tailwindcss.com/docs
- Alembic: https://alembic.sqlalchemy.org/en/latest/

**Design References**:
- Use existing DevMatrix UI patterns (dark mode, Tailwind classes)
- Card-based layouts from masterplans pages
- Form styles from settings page
- Button styles from chat interface
- Progress bars from task execution UI

### Timeline

**Week 1: Backend Foundation**
- Day 1-2: Database migrations and models
- Day 3-4: Email verification and password reset services
- Day 5: Usage tracking and quota services

**Week 2: Backend API & Admin**
- Day 1-2: New API endpoints (verify, reset, usage)
- Day 3-4: Admin endpoints and services
- Day 5: Rate limiting integration

**Week 3: Frontend**
- Day 1-2: Auth pages (login, register, reset, verify)
- Day 3-4: User profile and usage stats
- Day 5: Protected routes and auth context

**Week 4: Testing & Polish**
- Day 1-2: Unit and integration tests
- Day 3: E2E tests and security tests
- Day 4: Performance optimization and caching
- Day 5: Documentation and deployment prep

**Total**: 4 weeks (20 working days)

---

## Summary

This specification provides a comprehensive blueprint for implementing Phase 6: Authentication & Multi-tenancy in DevMatrix. The implementation will:

1. Build on existing auth foundation (User model, AuthService, JWT)
2. Add complete email verification and password reset flows
3. Implement multi-tenancy with database FKs and workspace isolation
4. Track usage (LLM tokens, masterplans, storage) with quota enforcement
5. Provide admin capabilities (user management, statistics, impersonation)
6. Add rate limiting to prevent abuse
7. Create full frontend UI (auth pages, profile, protected routes)
8. Ensure security (httpOnly cookies, bcrypt, path validation)
9. Achieve performance targets (< 200ms auth, caching, indexes)
10. Include comprehensive testing (90%+ coverage, E2E, security)

All functional requirements, technical designs, API endpoints, database schemas, and acceptance criteria are documented for developers to implement from. The specification prioritizes security, performance, and user experience while preparing the foundation for future OAuth and team features.
