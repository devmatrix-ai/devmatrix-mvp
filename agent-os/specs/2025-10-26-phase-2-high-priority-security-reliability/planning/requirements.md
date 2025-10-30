# Phase 2: High Priority Security & Reliability - Requirements

**Date:** 2025-10-26
**Phase:** 2 of 10
**Priority:** P1 - High Priority
**Timeline:** 2 weeks (Weeks 3-4 of 10-week roadmap)

---

## Overview

Phase 2 addresses 15 P1 (High Priority) security issues to harden authentication, enable enterprise-grade authorization, and implement comprehensive security monitoring. This builds on Phase 1's foundation of 8 P0 critical vulnerability fixes.

---

## Sub-Phase 2.1: Authentication Hardening (3 Issues)

### 1. Password Complexity Requirements

**Decision:** Modern NIST approach (NIST SP 800-63B)

**Requirements:**
- Minimum length: 12 characters (no maximum, up to 128 chars)
- NO composition requirements (no forced uppercase/lowercase/numbers/special chars)
- Entropy-based validation using zxcvbn library
- Ban top 10,000 common passwords (use SecLists common-passwords.txt)
- Check against user's email/username (prevent "password123" when email is "password123@example.com")
- Real-time password strength feedback during input (weak/fair/good/strong)

**Rationale:** Length > complexity. NIST guidelines show composition rules lead to predictable patterns (e.g., "Password1!"). Longer passphrases are more secure and memorable.

**Implementation:**
- Add `password_policy` configuration to Settings
- Create `PasswordValidator` service with zxcvbn integration
- Update registration and password reset endpoints
- Add password strength meter to frontend (future)

**Backward Compatibility:**
- Existing users: Mark as `legacy_password=True` in database
- On next login: Show warning "Your password doesn't meet new security requirements"
- Grace period: 30 days before forcing password reset
- Email notification sent to users about policy change

---

### 2. Account Lockout Protection

**Decision:** Account-based lockout with exponential backoff

**Requirements:**
- Lockout trigger: 5 failed login attempts within 15 minutes
- Initial lockout duration: 15 minutes
- Exponential backoff for repeated lockouts: 30 min, 1 hour, 2 hours, 4 hours (max)
- Lockout applies to account (not IP) to prevent blocking legitimate users on shared IPs
- Clear error message: "Account locked due to multiple failed login attempts. Try again in X minutes."
- No CAPTCHA (reduces friction for legitimate users)
- Admin can manually unlock accounts
- Lockout counter resets after successful login

**Implementation:**
- Add to User model: `failed_login_attempts` (int), `locked_until` (timestamp), `last_failed_login` (timestamp)
- Create `AccountLockoutService` to track and enforce lockouts
- Update login endpoint to check lockout status before password verification
- Add admin endpoint: POST /admin/users/{user_id}/unlock
- Background job: Auto-unlock expired lockouts (every 5 minutes)

**Security Events:**
- Log failed login attempts (includes IP, user agent, timestamp)
- Log account lockouts (includes attempt count, lockout duration)
- Alert admins when account locked 3+ times in 24 hours (potential targeted attack)

---

### 3. Session Timeout Management

**Decision:** Dual timeout (idle + absolute) with soft redirect

**Requirements:**
- **Idle timeout:** 30 minutes of no activity
- **Absolute timeout:** 12 hours (max session duration regardless of activity)
- Activity tracking: Any API request resets idle timer
- On timeout: Soft redirect to login page with message "Your session has expired. Please log in again."
- Token blacklist: Add expired token to Redis blacklist (same mechanism as logout)
- Frontend warning: Show modal at 5 minutes before idle timeout: "You'll be logged out in 5 minutes. Click here to stay logged in."
- "Stay logged in" action: Send keep-alive ping to reset idle timer

**Implementation:**
- Store session metadata in Redis: `session:{user_id}:{token_jti}` with TTL of 30 minutes
- Update session TTL on every authenticated request (via middleware)
- Add `issued_at` claim to JWT payload
- Check absolute timeout: `current_time - issued_at > 12 hours`
- Create `/api/v1/auth/session/keep-alive` endpoint (resets idle timer)
- Frontend: Set up timer to show warning modal and auto-logout

**Settings:**
- `SESSION_IDLE_TIMEOUT_MINUTES=30` (configurable)
- `SESSION_ABSOLUTE_TIMEOUT_HOURS=12` (configurable)

---

## Sub-Phase 2.2: Advanced Authentication & Authorization (5 Issues)

### 4. IP-Based Access Controls

**Decision:** CIDR range support with X-Forwarded-For handling

**Requirements:**
- Restrict admin endpoints to whitelisted IPs/CIDR ranges
- Environment variable: `ADMIN_IP_WHITELIST=192.168.1.0/24,10.0.0.1,203.0.113.5`
- Support both single IPs and CIDR notation (e.g., /24, /16)
- Check `X-Forwarded-For` header first (for cloud deployments behind load balancers)
- Fallback to `request.client.host` if X-Forwarded-For not present
- Apply to admin-specific endpoints: `/api/v1/admin/*`, `/api/v1/users/*/promote`
- Return HTTP 403 with clear message: "Access denied. Admin access restricted to whitelisted IPs."
- Log all rejected admin access attempts with IP address

**Protected Endpoints:**
- All routes under `/api/v1/admin/*`
- User role promotion endpoints
- Audit log access endpoints
- System configuration endpoints

**Implementation:**
- Create `IPWhitelistMiddleware` or decorator `@require_admin_ip`
- Parse CIDR ranges using `ipaddress` module
- Cache parsed whitelist in memory (reload on config change)
- Add middleware to check IP before auth middleware (fail fast)

---

### 5. 2FA/MFA Foundation

**Decision:** TOTP (Time-based One-Time Password) with optional enforcement

**Requirements:**
- Algorithm: TOTP (RFC 6238) compatible with Google Authenticator, Authy, 1Password, etc.
- QR code generation for easy enrollment (use `qrcode` library)
- 6-digit codes, 30-second time window
- Backup codes: Generate 6 single-use backup codes during enrollment
- User can regenerate backup codes (invalidates old ones)
- Optional enforcement: 2FA optional by default, admin can enforce per-user or globally
- Grace period: When admin enables enforcement, give users 7 days to enroll before blocking access

**Enrollment Flow:**
1. User navigates to `/settings/security/2fa/enable`
2. Backend generates secret key
3. Backend returns QR code (data URI) and text secret
4. User scans QR code with authenticator app
5. User enters 6-digit code to verify
6. Backend validates code, enables 2FA, generates backup codes
7. User downloads/saves backup codes

**Login Flow with 2FA:**
1. User enters email + password
2. If 2FA enabled: Return `{requires_2fa: true, temp_token: "xxx"}`
3. Frontend shows 2FA code input
4. User enters 6-digit code
5. Backend validates code with temp_token
6. On success: Return access_token and refresh_token
7. On failure: Increment 2FA failure counter (max 3 attempts, then re-authenticate)

**Backup Code Flow:**
1. User clicks "Use backup code instead"
2. User enters one of 6 backup codes
3. Backend validates and marks code as used
4. Show warning: "You have X backup codes remaining. Generate new codes."

**Implementation:**
- Add to User model: `totp_secret` (encrypted), `totp_enabled` (bool), `totp_backup_codes` (JSON array, encrypted)
- Create `TOTPService` with pyotp integration
- Add endpoints: POST /auth/2fa/enable, POST /auth/2fa/disable, POST /auth/2fa/verify, GET /auth/2fa/backup-codes, POST /auth/2fa/regenerate-backup-codes
- Update login endpoint to handle 2FA flow
- Add admin setting: `ENFORCE_2FA=false` (global), per-user `2fa_required` flag

**Security:**
- Encrypt TOTP secrets and backup codes at rest (use Fernet symmetric encryption)
- Rate limit 2FA verification: max 3 attempts per minute
- Audit log: 2FA enrollment, disablement, failed attempts, backup code usage

---

### 6. Role-Based Access Control (RBAC)

**Decision:** Flexible roles table with many-to-many user_roles

**Requirements:**
- 4 predefined roles with hierarchical permissions:
  - **superadmin:** All permissions, can't be deleted, at least one must exist
  - **admin:** Manage users, view all conversations, access audit logs
  - **user:** Default role, manage own resources
  - **viewer:** Read-only access to shared resources

**Hierarchical Permissions:**
```
superadmin > admin > user > viewer

superadmin:
  - All permissions
  - Assign/remove any role
  - Delete users
  - Access system configuration

admin:
  - View all conversations (but not modify)
  - Manage users (create, update, assign user/viewer roles)
  - Access audit logs
  - Cannot assign admin or superadmin roles

user:
  - Full CRUD on own conversations
  - Share conversations with others
  - Update own profile
  - Cannot access other users' resources (unless shared)

viewer:
  - Read-only access to shared conversations
  - Cannot create or modify anything
  - Can view own profile
```

**Database Schema:**
```sql
-- roles table
CREATE TABLE roles (
  role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  role_name VARCHAR(50) UNIQUE NOT NULL,  -- 'superadmin', 'admin', 'user', 'viewer'
  description TEXT,
  is_system BOOLEAN DEFAULT FALSE,  -- Cannot be deleted if true
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- user_roles table (many-to-many)
CREATE TABLE user_roles (
  user_role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
  assigned_by UUID REFERENCES users(user_id),  -- Who assigned this role
  assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, role_id)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

**Implementation:**
- Create `Role` and `UserRole` models
- Create `RBACService` with methods: `user_has_role()`, `user_has_any_role()`, `assign_role()`, `remove_role()`
- Create decorator: `@require_role('admin')` or `@require_any_role(['admin', 'superadmin'])`
- Seed database with 4 system roles on migration
- Auto-assign "user" role to new registrations
- Update existing users: Migrate all to "user" role

**Role Assignment:**
- Only admin and superadmin can assign roles
- Admin can assign: user, viewer
- Superadmin can assign: admin, superadmin
- Audit log all role assignments with assigned_by

---

### 7. Granular Permission System

**Decision:** RBAC roles map to permission sets (no separate framework)

**Requirements:**
- Permissions defined by role, not separately assignable
- Permission format: `resource:action`

**Permission Matrix:**
```
Resource: conversation
Actions: read, write, delete, share

Resource: message
Actions: read, write, delete

Resource: user
Actions: read, write, delete, promote

Resource: audit
Actions: read

Resource: system
Actions: configure

Permission Mapping by Role:
superadmin:
  - conversation:* (all)
  - message:* (all)
  - user:* (all)
  - audit:read
  - system:configure

admin:
  - conversation:read (all conversations)
  - message:read (all messages)
  - user:read, user:write, user:promote (to user/viewer only)
  - audit:read

user:
  - conversation:* (own only)
  - message:* (own only)
  - user:read (own only), user:write (own only)

viewer:
  - conversation:read (shared only)
  - message:read (shared only)
  - user:read (own only)
```

**Implementation:**
- Create `PermissionService` with method: `user_can(user, 'conversation:read', conversation_id)`
- Check role first, then check ownership/sharing
- Decorator: `@require_permission('conversation:write')` (automatically checks ownership)
- No permissions table - permissions are hardcoded in RBACService based on roles

**Permission Checks:**
```python
# Example usage in endpoint
@router.get("/conversations/{conversation_id}")
@require_permission("conversation:read")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    # Permission check happens in decorator:
    # 1. Check if user has role that grants conversation:read
    # 2. If admin/superadmin: Allow access to any conversation
    # 3. If user/viewer: Check ownership or sharing
    # 4. If no access: Raise 403
    ...
```

---

### 8. Resource Sharing & Collaboration

**Decision:** User-to-user conversation sharing with permission levels

**Requirements:**
- Share conversations with specific users (not teams/orgs)
- 3 permission levels:
  - **view:** Read-only access to conversation and messages
  - **comment:** Read + write messages (but can't edit conversation title/settings)
  - **edit:** Full access (read/write conversation and messages, but can't delete or re-share)
- Owner retains full control (delete, revoke shares)
- No expiration dates (manual revoke only, keep it simple)
- Share notification: Email sent to recipient when conversation is shared

**Database Schema:**
```sql
CREATE TABLE conversation_shares (
  share_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE CASCADE,
  shared_by UUID REFERENCES users(user_id) ON DELETE SET NULL,  -- Original sharer
  shared_with UUID REFERENCES users(user_id) ON DELETE CASCADE,  -- Recipient
  permission_level VARCHAR(20) CHECK (permission_level IN ('view', 'comment', 'edit')),
  shared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(conversation_id, shared_with)  -- Can't share same conversation to same user twice
);

CREATE INDEX idx_conversation_shares_conversation_id ON conversation_shares(conversation_id);
CREATE INDEX idx_conversation_shares_shared_with ON conversation_shares(shared_with);
```

**API Endpoints:**
```
POST /api/v1/conversations/{conversation_id}/share
  Body: {user_email: "alice@example.com", permission: "view"}
  Returns: {share_id, shared_with, permission}

GET /api/v1/conversations/{conversation_id}/shares
  Returns: [{share_id, shared_with, permission, shared_at}]

PATCH /api/v1/conversations/{conversation_id}/shares/{share_id}
  Body: {permission: "edit"}
  Returns: Updated share

DELETE /api/v1/conversations/{conversation_id}/shares/{share_id}
  Returns: 204 No Content

GET /api/v1/conversations/shared-with-me
  Returns: List of conversations shared with current user
```

**Implementation:**
- Create `ConversationShare` model
- Update ownership middleware: Check shares when ownership check fails
- Permission enforcement: view → read only, comment → read + write messages, edit → read + write conversation
- Audit log: Share creation, permission changes, revocation
- Email notification service: Send email when conversation is shared

**Sharing Rules:**
- Only owner can share (not recipients)
- Can't share with yourself
- Can't share if conversation already shared with user (update permission instead)
- Deleting conversation deletes all shares
- Deleting user removes shares where they are recipient

---

## Sub-Phase 2.3: Security Monitoring & Compliance (4 Issues)

### 9. Enhanced Audit Logging (Read Operations)

**Decision:** Log 100% of read operations (no sampling)

**Requirements:**
- Extend Phase 1's audit logger to include read operations
- Log events: `conversation.read`, `message.read`, `user.read`
- **Exclude:** Health checks (`/health`, `/metrics`), static assets, high-frequency system operations
- Same fields as Phase 1: user_id, action, resource_type, resource_id, result, ip_address, user_agent, correlation_id, timestamp
- Use existing `audit_logs` table from Phase 1
- Async logging (don't block requests)

**Volume Management:**
- Retention: 90-day hot storage, 7-year cold storage (S3)
- Table partitioning: Partition by month for performance
- Automatic archival: Monthly job moves old partitions to S3

**Implementation:**
- Update audit_logger.py: Add `log_read_operation()` method
- Apply to endpoints: GET /conversations, GET /conversations/{id}, GET /messages
- Add middleware: Auto-log all GET requests (with exclusions)
- Create archival script: Compress and upload to S3, drop partition

**Exclusions List:**
```python
AUDIT_LOG_EXCLUSIONS = [
    "/health",
    "/metrics",
    "/static/*",
    "/api/v1/auth/session/keep-alive",
    "/api/v1/auth/me"  # High frequency
]
```

---

### 10. Security Event Monitoring

**Decision:** Batch processing every 5 minutes with anomaly detection

**Requirements:**
- Detect security events and anomalies through pattern analysis
- Processing frequency: Every 5 minutes (batch job)
- Store events in new `security_events` table

**Monitored Events:**
1. **Failed Login Clusters:** 5+ failed logins from same account in 10 minutes
2. **Geo-Location Changes:** IP country change detected (requires GeoIP2 database)
3. **Privilege Escalation:** User role changed to admin/superadmin
4. **Unusual Access Patterns:** Access at unusual hours (e.g., 2am-5am when user typically accesses 9am-5pm)
5. **Multiple 403s:** 10+ authorization failures in 5 minutes (potential enumeration attack)
6. **Account Lockout Events:** Account locked due to failed attempts
7. **2FA Disabled:** User disables 2FA (especially if admin enforced)
8. **Session Anomalies:** Multiple concurrent sessions from different countries

**Database Schema:**
```sql
CREATE TABLE security_events (
  event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_type VARCHAR(50) NOT NULL,  -- 'failed_login_cluster', 'geo_change', etc.
  severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  event_data JSONB NOT NULL,  -- Details specific to event type
  detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMP WITH TIME ZONE,
  resolved_by UUID REFERENCES users(user_id)
);

CREATE INDEX idx_security_events_user_id ON security_events(user_id);
CREATE INDEX idx_security_events_detected_at ON security_events(detected_at);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_resolved ON security_events(resolved);

-- Partition by month
CREATE TABLE security_events_2025_10 PARTITION OF security_events
  FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

**Event Severity:**
```
critical:
  - Privilege escalation to superadmin
  - Multiple concurrent logins from different countries

high:
  - Failed login cluster (potential brute force)
  - Geo-location change to high-risk country
  - 2FA disabled when enforced

medium:
  - Unusual access patterns
  - Multiple 403s (potential enumeration)

low:
  - Account lockout (might be legitimate user forgetting password)
  - Single geo-location change
```

**Implementation:**
- Create `SecurityMonitoringService` with detection methods
- Create scheduled job (APScheduler): Run every 5 minutes
- Job workflow:
  1. Query audit logs and auth logs for last 5 minutes
  2. Run detection algorithms
  3. Create security_events for detected anomalies
  4. Trigger alerts for high/critical severity
- Baseline building: Track user's typical access patterns over 30 days
- Admin dashboard: View security events, mark as resolved

**Anomaly Detection Algorithms:**
```python
# Failed login cluster
SELECT user_id, COUNT(*) as failures
FROM audit_logs
WHERE action = 'auth.login_failed'
  AND timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY user_id
HAVING COUNT(*) >= 5

# Geo-location change
SELECT user_id, ip_address, country
FROM audit_logs
WHERE action = 'auth.login'
  AND timestamp > NOW() - INTERVAL '5 minutes'
  AND country != (SELECT country FROM user_locations WHERE user_id = audit_logs.user_id ORDER BY last_seen DESC LIMIT 1)
```

---

### 11. Alert System Implementation

**Decision:** Multi-channel alerts with throttling

**Requirements:**
- Alert channels: Email (primary), Slack webhook (optional), PagerDuty (optional, for critical)
- Alert recipients: Admins for all alerts, affected users for their own security events
- Alert throttling: Maximum 1 alert per event type per user per hour (prevent spam)
- Alert severity determines channels:
  - **critical:** Email + Slack + PagerDuty
  - **high:** Email + Slack
  - **medium:** Email only
  - **low:** No real-time alert (admin dashboard only)

**Alert Templates:**
```
Subject: [CRITICAL] Multiple failed login attempts detected

Hi {user_name},

We detected {count} failed login attempts on your account from IP {ip_address} ({country}).

If this was you, you can ignore this message. If not, your password may be compromised.

Recommended actions:
- Change your password immediately
- Enable 2FA if not already enabled
- Review recent activity in your account

Time: {timestamp}
Correlation ID: {correlation_id}

---

Subject: [HIGH] Unusual login location detected

Hi {user_name},

We detected a login from a new location:
- IP: {ip_address}
- Location: {city}, {country}
- Time: {timestamp}

If this was you, no action needed. If not, secure your account immediately.

[Review Activity] [Change Password]
```

**Database Schema:**
```sql
CREATE TABLE alert_history (
  alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  security_event_id UUID REFERENCES security_events(event_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  alert_type VARCHAR(50) NOT NULL,  -- 'email', 'slack', 'pagerduty'
  sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  status VARCHAR(20) CHECK (status IN ('sent', 'failed', 'throttled')),
  error_message TEXT
);

CREATE INDEX idx_alert_history_user_id ON alert_history(user_id);
CREATE INDEX idx_alert_history_sent_at ON alert_history(sent_at);
```

**Throttling Logic:**
```python
# Check if alert already sent in last hour
SELECT COUNT(*) FROM alert_history
WHERE user_id = :user_id
  AND alert_type = :alert_type
  AND sent_at > NOW() - INTERVAL '1 hour'

# If count > 0: Skip alert, log as 'throttled'
```

**Implementation:**
- Create `AlertService` with methods: `send_email_alert()`, `send_slack_alert()`, `send_pagerduty_alert()`
- Configuration via Settings: `SLACK_WEBHOOK_URL`, `PAGERDUTY_API_KEY`, `ALERT_THROTTLE_HOURS=1`
- Email templates using Jinja2
- Slack message format: Use blocks for rich formatting
- PagerDuty integration: Use Events API v2
- Async alert sending (don't block security monitoring job)

**Admin Controls:**
- Admin settings page: Enable/disable channels, configure webhooks
- Per-user alert preferences: Users can opt out of non-critical alerts
- Test alert button: Send test alert to verify configuration

---

### 12. Log Retention & Management

**Decision:** 90-day hot storage + 7-year cold storage with auto-archival

**Requirements:**
- **Audit logs:** 90 days in PostgreSQL (hot), 7 years in S3 (cold)
- **Security events:** 90 days in PostgreSQL (hot), 7 years in S3 (cold)
- **Alert history:** 1 year in PostgreSQL, no archival (purge after 1 year)
- Automatic archival: Monthly job runs on 1st of month
- Manual purge: Superadmin only, with confirmation
- Compliance: Meets SOC 2, ISO 27001, GDPR requirements (7-year retention)

**Archival Process:**
1. Select partition older than 90 days
2. Export to compressed JSON (gzip)
3. Upload to S3: `s3://bucket/audit-logs/2025/10/audit_logs_2025_10.json.gz`
4. Verify upload successful
5. Drop partition from PostgreSQL
6. Log archival event

**S3 Structure:**
```
s3://devmatrix-audit-logs/
  audit-logs/
    2025/
      10/
        audit_logs_2025_10.json.gz
        audit_logs_2025_10.manifest.json  # Metadata: row count, size, checksum
      11/
        audit_logs_2025_11.json.gz
    2024/
      ...
  security-events/
    2025/
      10/
        security_events_2025_10.json.gz
```

**Manifest File Format:**
```json
{
  "table": "audit_logs",
  "partition": "2025_10",
  "row_count": 1523456,
  "file_size_bytes": 45678900,
  "checksum": "sha256:abc123...",
  "archived_at": "2025-11-01T00:15:23Z",
  "archived_by": "system",
  "s3_path": "s3://devmatrix-audit-logs/audit-logs/2025/10/audit_logs_2025_10.json.gz"
}
```

**Implementation:**
- Create `LogArchivalService` with methods: `archive_partition()`, `restore_from_archive()`
- Scheduled job (APScheduler): Run on 1st of month at 2am
- Settings: `S3_BUCKET_NAME`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `ARCHIVAL_AGE_DAYS=90`
- Admin endpoint: POST /admin/logs/archive (manual trigger)
- Admin endpoint: POST /admin/logs/restore (restore partition from S3 for investigation)
- Superadmin endpoint: DELETE /admin/logs/purge (permanent deletion with confirmation)

**Retrieval from Cold Storage:**
- Admin can request restoration of archived logs
- Download from S3, decompress, load into temporary table
- Query temporary table (read-only)
- Auto-purge temporary table after 7 days or admin dismissal

**Compliance Documentation:**
- Document retention policy in SECURITY_COMPLIANCE.md
- Log all archival and purge operations in system logs
- Annual audit: Verify S3 archives are intact (checksum validation)

---

## Sub-Phase 2.4: Input Validation & Security Headers (3 Issues)

### 13. Comprehensive Security Headers

**Decision:** Report-only CSP for 1 week, then strict enforcement

**Requirements:**
- Implement 6 critical security headers
- CSP: Start in report-only mode, switch to enforcement after 1 week
- All headers applied via middleware (single source of truth)

**Security Headers:**
```
Content-Security-Policy (CSP):
  Report-only (Week 1): Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; report-uri /api/v1/security/csp-report

  Strict (Week 2+): Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; upgrade-insecure-requests; block-all-mixed-content

Strict-Transport-Security (HSTS):
  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  (31536000 seconds = 1 year, required for preload list)

X-Frame-Options:
  X-Frame-Options: DENY
  (Prevents clickjacking, no iframes allowed)

X-Content-Type-Options:
  X-Content-Type-Options: nosniff
  (Prevents MIME-type sniffing attacks)

Referrer-Policy:
  Referrer-Policy: strict-origin-when-cross-origin
  (Only send origin for cross-origin requests)

Permissions-Policy:
  Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()
  (Disable dangerous features not needed by app)
```

**CSP Violation Reporting:**
- Endpoint: POST /api/v1/security/csp-report
- Log violations to `security_events` table
- Admin dashboard: View CSP violations during report-only phase
- Review violations, adjust CSP policy if needed (e.g., allow CDNs)
- After 1 week: Switch to enforcement if <10 violations/day

**Implementation:**
- Create `SecurityHeadersMiddleware`
- Configuration via Settings: `CSP_REPORT_ONLY=true` (toggle enforcement)
- Apply middleware to all routes (including static assets)
- CSP violation handler: Parse report, log to security_events
- Admin endpoint: GET /admin/security/csp-violations (last 7 days)
- Admin toggle: POST /admin/security/csp/enforce (switch from report-only to strict)

**Testing:**
- Browser console: Check headers in DevTools Network tab
- Online tools: securityheaders.com, csp-evaluator.withgoogle.com
- Penetration test: Attempt clickjacking, XSS, MIME-sniffing

**Exceptions:**
- Development mode (`DEBUG=true`): Relaxed CSP to allow hot-reload
- Staging: Report-only mode permanently enabled for testing

---

### 14. Advanced Input Validation

**Decision:** No file uploads in Phase 2, focus on API validation

**Requirements:**
- Apply Pydantic schemas to ALL API endpoints (Phase 1 had gaps)
- Content-length limits per endpoint type
- Path traversal prevention in any file path handling
- Defer file uploads to Phase 3

**Content-Length Limits:**
```
API endpoints (POST/PUT):
  - Default: 10 MB
  - Chat messages: 100 KB
  - User profile updates: 50 KB
  - Bulk operations: 50 MB

GET requests:
  - No body expected, reject if Content-Length > 0
```

**Pydantic Schema Enforcement:**
- Create schemas for ALL request bodies (no implicit parsing)
- Strict validation: Reject unknown fields (`extra='forbid'`)
- Type validation: Enforce correct types (str, int, UUID, etc.)
- Range validation: Min/max values for integers, min/max length for strings
- Regex validation: Email format, UUID format, etc.

**Example Schemas:**
```python
from pydantic import BaseModel, Field, EmailStr, constr, validator

class UserRegistrationRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=12, max_length=128)
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)

    class Config:
        extra = 'forbid'  # Reject unknown fields

class ConversationCreateRequest(BaseModel):
    title: constr(min_length=1, max_length=200)
    context: Optional[constr(max_length=10000)] = None

    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v

    class Config:
        extra = 'forbid'
```

**Path Traversal Prevention:**
- Validate all file paths (if any) to prevent `../` attacks
- Use `pathlib.Path.resolve()` and check if result is within allowed directory
- Example: User avatars (future), file downloads (logs)

```python
from pathlib import Path

def safe_file_path(user_input: str, base_dir: Path) -> Path:
    """Validate file path is within base_dir"""
    full_path = (base_dir / user_input).resolve()
    if not str(full_path).startswith(str(base_dir.resolve())):
        raise ValueError("Invalid file path: Path traversal detected")
    return full_path
```

**Implementation:**
- Audit all endpoints: Ensure Pydantic schema on request body
- Create `ContentLengthMiddleware`: Check Content-Length header before parsing body
- Add validators to existing schemas (many already have them from Phase 1)
- Create `InputValidationUtils` module with reusable validators
- Update error responses: Include field names and validation errors

**Validation Error Response:**
```json
{
  "code": "VAL_001",
  "message": "Validation error",
  "details": {
    "errors": [
      {
        "field": "password",
        "message": "Password must be at least 12 characters",
        "type": "value_error.str.min_length"
      },
      {
        "field": "email",
        "message": "Invalid email format",
        "type": "value_error.email"
      }
    ]
  },
  "correlation_id": "...",
  "timestamp": "..."
}
```

---

### 15. JSON Validation Hardening

**Decision:** Strict validation with depth and size limits

**Requirements:**
- Reject unknown fields (strict schema validation)
- Depth limit: Maximum 10 levels of nesting
- Size limit: Maximum 10 MB per JSON request
- Expose field names in validation errors (helpful for developers, not a security risk)

**JSON Depth Limit:**
```python
import json

def validate_json_depth(data: dict, max_depth: int = 10, current_depth: int = 0):
    """Recursively check JSON depth"""
    if current_depth > max_depth:
        raise ValueError(f"JSON depth exceeds maximum of {max_depth} levels")

    if isinstance(data, dict):
        for value in data.values():
            validate_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            validate_json_depth(item, max_depth, current_depth + 1)
```

**JSON Size Limit:**
- Already handled by Content-Length middleware (10 MB default)
- Additional parsing limit: Use `json.loads(data, parse_constant=lambda x: None)` to prevent number parsing attacks

**Pydantic Configuration:**
```python
class StrictBaseModel(BaseModel):
    """Base model with strict validation"""

    class Config:
        extra = 'forbid'  # Reject unknown fields
        max_anystr_length = 1_000_000  # Max string length: 1 MB
        # JSON depth handled by middleware, not Pydantic
```

**Implementation:**
- Create `JSONValidationMiddleware`: Check depth and size before Pydantic parsing
- Update all request models to inherit from `StrictBaseModel`
- Add `validate_json_depth()` to middleware
- Settings: `JSON_MAX_DEPTH=10`, `JSON_MAX_SIZE_MB=10`
- Error response: Include specific validation errors

**Attack Prevention:**
```json
// Deeply nested attack (prevented by depth limit)
{
  "a": {
    "b": {
      "c": {
        "d": {
          "e": {
            "f": {
              "g": {
                "h": {
                  "i": {
                    "j": {
                      "k": "too deep"  // Rejected at depth 11
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

// Unknown field attack (prevented by extra='forbid')
{
  "email": "user@example.com",
  "password": "secret",
  "admin": true  // Rejected: Unknown field
}

// Large string attack (prevented by size limit)
{
  "message": "A".repeat(2_000_000)  // Rejected: Content-Length > 10 MB
}
```

---

## Cross-Cutting Requirements

### Timeline & Parallelism

**Total Duration:** 2 weeks (1 engineer, full-time)

**Critical Path:**
1. Sub-Phase 2.1: Authentication Hardening (Days 1-3) - Must be first
2. Sub-Phase 2.2: RBAC & Permissions (Days 4-8) - Depends on 2.1
3. Sub-Phase 2.3: Security Monitoring (Days 9-11) - Can start after 2.1
4. Sub-Phase 2.4: Headers & Validation (Days 12-14) - Can be parallel with 2.3

**Parallel Work Opportunities:**
- Sub-Phase 2.3 and 2.4 can be developed in parallel (different files, no conflicts)
- 2FA enrollment UI can be developed while RBAC backend is in progress
- Security monitoring can be built while authentication hardening is being tested

---

### Testing Strategy

**Target:** 100+ new tests

**Test Distribution:**
- **Unit tests:** 60 tests
  - Password validation: 10 tests (entropy, common passwords, edge cases)
  - Account lockout: 8 tests (trigger, backoff, unlock)
  - Session timeout: 8 tests (idle, absolute, keep-alive)
  - 2FA: 12 tests (enrollment, verification, backup codes)
  - RBAC: 10 tests (role assignment, permission checks, hierarchy)
  - Sharing: 8 tests (create, update, delete, permissions)
  - Security monitoring: 4 tests (detection algorithms, mocked data)

- **Integration tests:** 30 tests
  - Full auth flow with 2FA: 5 tests
  - Password reset with new policy: 3 tests
  - Account lockout and unlock flow: 3 tests
  - Session timeout with keep-alive: 3 tests
  - Role-based authorization across endpoints: 8 tests
  - Conversation sharing and access: 5 tests
  - Security event detection end-to-end: 3 tests

- **Security tests:** 10 tests
  - Password policy bypass attempts: 2 tests
  - Account lockout evasion: 2 tests
  - RBAC privilege escalation: 2 tests
  - Sharing permission bypass: 2 tests
  - CSP violation detection: 2 tests

**Testing Tools:**
- pytest for all tests
- pytest-asyncio for async tests
- freezegun for time-based tests (session timeout, lockout expiry)
- fakeredis for Redis mocking
- pytest-mock for service mocking

---

### Backward Compatibility

**Existing Users:**
- Passwords: Grandfathered (mark as `legacy_password=True`), force reset on next login with 30-day grace period
- 2FA: Optional by default, not enforced
- Roles: Auto-migrate all users to "user" role
- Sessions: Existing tokens honored until expiry, then new timeout rules apply
- Sharing: No existing shares, new feature

**Database Migration:**
- 5 new tables: `roles`, `user_roles`, `conversation_shares`, `security_events`, `alert_history`
- Extend `users` table: Add 10+ new columns for 2FA, lockout, session tracking
- Partition existing `audit_logs` table by month (ALTER TABLE)
- Seed `roles` table with 4 system roles

**Migration Script:**
```sql
-- Add new columns to users table
ALTER TABLE users
  ADD COLUMN password_last_changed TIMESTAMP WITH TIME ZONE,
  ADD COLUMN legacy_password BOOLEAN DEFAULT FALSE,
  ADD COLUMN failed_login_attempts INTEGER DEFAULT 0,
  ADD COLUMN locked_until TIMESTAMP WITH TIME ZONE,
  ADD COLUMN last_failed_login TIMESTAMP WITH TIME ZONE,
  ADD COLUMN totp_secret TEXT,  -- Encrypted
  ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN totp_backup_codes JSONB,  -- Encrypted
  ADD COLUMN last_login_ip VARCHAR(50),
  ADD COLUMN last_login_country VARCHAR(2);

-- Mark all existing users as having legacy passwords
UPDATE users SET legacy_password = TRUE WHERE password IS NOT NULL;

-- Create new tables (roles, user_roles, etc.)
-- Insert default roles
INSERT INTO roles (role_name, description, is_system) VALUES
  ('superadmin', 'Full system access', TRUE),
  ('admin', 'Administrative access', TRUE),
  ('user', 'Standard user', TRUE),
  ('viewer', 'Read-only access', TRUE);

-- Assign all existing users to "user" role
INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id
FROM users u
CROSS JOIN roles r
WHERE r.role_name = 'user';
```

**Rollback Plan:**
- Phase 2 migrations are additive (no data loss)
- Can roll back code without rolling back migrations (new columns ignored)
- If critical issue: Disable features via feature flags (e.g., `ENFORCE_PASSWORD_POLICY=false`)

---

### Exclusions (Deferred to Later Phases)

**Phase 3 (Medium Priority):**
- Teams/Organizations
- File uploads (user avatars, attachments)
- Advanced permission delegation

**Phase 4 (Compliance):**
- WebAuthn/FIDO2 (hardware keys)
- Biometric authentication

**Phase 5 (Integrations):**
- OAuth2 provider (allow third-party apps)
- Real-time threat intelligence feeds
- SIEM integration (Splunk, ELK)

**Phase 6 (Advanced Auth):**
- SMS 2FA (insecure, low priority)
- Social login (Google, GitHub)
- SSO/SAML

**Never:**
- Blockchain-based authentication
- Face recognition
- Password recovery "security questions"

---

## Success Metrics

**Authentication Hardening:**
- [ ] 95%+ of active users have passwords meeting new policy within 60 days
- [ ] Account lockout reduces brute force attempts by 90%
- [ ] Session timeout reduces unauthorized access incidents to zero

**Authorization:**
- [ ] 100% of admin actions protected by RBAC
- [ ] Zero privilege escalation vulnerabilities in penetration testing
- [ ] Conversation sharing used by 30%+ of active users within 90 days

**Security Monitoring:**
- [ ] 100% of security events detected within 5 minutes
- [ ] 95%+ of critical alerts delivered within 1 minute
- [ ] Zero false positives for critical alerts

**Compliance:**
- [ ] 100% audit log retention compliance (7 years)
- [ ] Zero critical vulnerabilities in CSP validation
- [ ] 100% of API endpoints have input validation

**Testing:**
- [ ] 100+ new tests passing
- [ ] 95%+ code coverage on Phase 2 features
- [ ] Zero critical vulnerabilities found in security review

---

## Summary

Phase 2 builds on Phase 1's critical security foundation to create an enterprise-ready authentication and authorization system. With password policies, account lockout, 2FA, RBAC, comprehensive monitoring, and strict input validation, DevMatrix will be ready for SOC 2 Type 1 compliance and enterprise customer deployments.

All requirements are documented, technical decisions made, and implementation path clear. Ready for specification writing and task breakdown.
