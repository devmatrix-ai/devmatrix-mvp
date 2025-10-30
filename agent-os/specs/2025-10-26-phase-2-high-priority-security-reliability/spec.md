# Specification: Phase 2 - High Priority Security & Reliability

## Goal

Harden authentication mechanisms, implement enterprise-grade role-based access control (RBAC), enable secure resource sharing, and establish comprehensive security monitoring infrastructure to achieve SOC 2 Type 1 compliance readiness.

## User Stories

- As a system administrator, I want to enforce strong password policies so that user accounts are protected against weak credentials
- As a security team member, I want to detect and respond to suspicious login activity so that account compromise attempts are quickly identified
- As an authenticated user, I want my session to automatically timeout after inactivity so that my account remains secure on shared devices
- As a user, I want to enable two-factor authentication so that my account has an additional layer of protection
- As an administrator, I want to assign different roles to users so that access is appropriately restricted based on job function
- As a project owner, I want to share conversations with specific team members so that we can collaborate securely
- As a security administrator, I want real-time alerts for security events so that I can respond immediately to potential threats
- As a compliance officer, I want audit logs retained for 7 years so that we meet regulatory requirements

## Core Requirements

### Sub-Phase 2.1: Authentication Hardening

**Password Complexity (NIST-Compliant)**
- 12-character minimum length (no maximum up to 128 chars)
- Entropy-based validation using zxcvbn library
- Ban top 10,000 common passwords
- Prevent passwords containing user's email/username
- Real-time strength feedback (weak/fair/good/strong)
- Backward compatibility: Legacy passwords grandfathered with 30-day grace period

**Account Lockout Protection**
- Trigger: 5 failed attempts within 15 minutes
- Exponential backoff: 15min → 30min → 1hr → 2hrs → 4hrs (max)
- Account-based (not IP-based) to prevent blocking legitimate shared IPs
- Admin manual unlock capability
- Auto-unlock background job (runs every 5 minutes)
- Alert admins when account locked 3+ times in 24 hours

**Session Timeout Management**
- Dual timeout: 30-minute idle + 12-hour absolute
- Activity tracking: Any API request resets idle timer
- Redis-based session metadata storage
- Frontend warning modal at 5 minutes before idle timeout
- Keep-alive endpoint to extend sessions
- Graceful logout with informative messaging

### Sub-Phase 2.2: Advanced Authentication & Authorization

**IP-Based Access Controls**
- Whitelist admin endpoints to specific IP ranges
- CIDR notation support (e.g., 192.168.1.0/24)
- X-Forwarded-For header support for cloud deployments
- Protected endpoints: /api/v1/admin/*, role promotion, audit logs, system config
- Clear 403 error messages
- Log all rejected admin access attempts

**2FA/MFA Foundation (TOTP)**
- TOTP (RFC 6238) compatible with Google Authenticator, Authy, 1Password
- QR code generation for easy enrollment
- 6-digit codes with 30-second time window
- 6 single-use backup codes per user
- Optional enforcement (admin can enable per-user or globally)
- 7-day grace period when enforcement enabled
- Encrypted secret storage at rest (Fernet symmetric encryption)
- Rate limiting: max 3 2FA verification attempts per minute

**Role-Based Access Control (RBAC)**
- 4 predefined hierarchical roles: superadmin > admin > user > viewer
- Many-to-many user-role relationship
- Superadmin: All permissions, cannot be deleted, at least one must exist
- Admin: Manage users, view all conversations, access audit logs (cannot assign admin/superadmin roles)
- User: Full CRUD on own resources, share conversations
- Viewer: Read-only access to shared resources
- Auto-assign "user" role to new registrations
- Audit log all role assignments with assigned_by tracking

**Granular Permission System**
- Permission format: resource:action (e.g., "conversation:read")
- Permissions mapped by role (no separate permission table)
- Resources: conversation, message, user, audit, system
- Actions: read, write, delete, share, promote, configure
- Ownership-based checks for user/viewer roles
- Decorator-based permission enforcement

**Resource Sharing & Collaboration**
- User-to-user conversation sharing (no teams/orgs in Phase 2)
- 3 permission levels: view (read-only), comment (read + write messages), edit (full access except delete/re-share)
- Owner retains full control (delete, revoke shares)
- Email notifications when conversation shared
- No expiration dates (manual revoke only)
- Cannot share same conversation to same user twice

### Sub-Phase 2.3: Security Monitoring & Compliance

**Enhanced Audit Logging (Read Operations)**
- Log 100% of read operations (extends Phase 1 write-only logging)
- Events: conversation.read, message.read, user.read
- Exclude: Health checks, static assets, /auth/session/keep-alive
- Same schema as Phase 1 audit_logs table
- Async logging (non-blocking)
- 90-day hot storage, 7-year cold storage (S3)
- Table partitioning by month for performance

**Security Event Monitoring**
- Batch processing every 5 minutes
- New security_events table with event_type, severity, user_id, event_data (JSONB)
- Monitored events:
  - Failed login clusters (5+ in 10 minutes)
  - Geo-location changes (IP country change via GeoIP2)
  - Privilege escalation (role changed to admin/superadmin)
  - Unusual access patterns (access at atypical hours)
  - Multiple 403s (10+ in 5 minutes)
  - Account lockout events
  - 2FA disabled when enforced
  - Multiple concurrent sessions from different countries
- Severity levels: low, medium, high, critical
- Admin dashboard to view and resolve events
- Baseline building over 30 days for anomaly detection

**Alert System Implementation**
- Multi-channel: Email (primary), Slack webhook (optional), PagerDuty (optional for critical)
- Alert recipients: Admins for all alerts, affected users for own events
- Throttling: Max 1 alert per event type per user per hour
- Severity determines channels:
  - Critical: Email + Slack + PagerDuty
  - High: Email + Slack
  - Medium: Email only
  - Low: No real-time alert (dashboard only)
- Jinja2 email templates
- Slack block formatting
- PagerDuty Events API v2 integration
- Async alert sending (non-blocking)

**Log Retention & Management**
- Audit logs: 90 days PostgreSQL (hot), 7 years S3 (cold)
- Security events: 90 days PostgreSQL (hot), 7 years S3 (cold)
- Alert history: 1 year PostgreSQL (purge after 1 year)
- Automatic monthly archival on 1st of month at 2am
- Compressed JSON (gzip) format
- S3 structure: s3://bucket/audit-logs/YYYY/MM/table_YYYY_MM.json.gz
- Manifest files with row_count, file_size, checksum (SHA256)
- Admin-initiated restoration capability
- Temporary table for restored logs (auto-purge after 7 days)
- Superadmin-only manual purge with confirmation

### Sub-Phase 2.4: Input Validation & Security Headers

**Comprehensive Security Headers**
- Content-Security-Policy (CSP): Report-only for 1 week, then strict enforcement
  - Report-only: Allow unsafe-inline/unsafe-eval for compatibility check
  - Strict: default-src 'self', no unsafe-inline, block-all-mixed-content, upgrade-insecure-requests
  - CSP violation reporting endpoint: POST /api/v1/security/csp-report
- Strict-Transport-Security (HSTS): max-age=31536000; includeSubDomains; preload
- X-Frame-Options: DENY (prevents clickjacking)
- X-Content-Type-Options: nosniff (prevents MIME-sniffing)
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: Disable geolocation, camera, microphone, payment
- SecurityHeadersMiddleware applies to all routes
- Admin toggle to switch CSP from report-only to enforcement

**Advanced Input Validation**
- Pydantic schemas on ALL API endpoints (audit for gaps)
- Content-Length limits per endpoint type:
  - Chat messages: 100 KB
  - User profile updates: 50 KB
  - Bulk operations: 50 MB
  - Default: 10 MB
- Strict validation: extra='forbid' (reject unknown fields)
- Range validation: Min/max values for integers, min/max length for strings
- Type validation: Enforce correct types (str, int, UUID, EmailStr)
- Path traversal prevention: Validate file paths with pathlib.Path.resolve()
- Clear validation error responses with field names

**JSON Validation Hardening**
- Maximum depth: 10 levels of nesting
- Maximum size: 10 MB per JSON request
- Reject unknown fields (strict schema validation)
- JSONValidationMiddleware checks depth before Pydantic parsing
- StrictBaseModel base class with max_anystr_length=1_000_000
- Field-level validation errors in responses

## Visual Design

No visual assets (backend/security work)

## Reusable Components

### Existing Code to Leverage

**Authentication Infrastructure (Phase 1)**
- User model (src/models/user.py): Extend with new columns for lockout, 2FA, session tracking
- AuthService (src/services/auth_service.py): Reuse password hashing, JWT creation, token blacklist
- AuditLog model (src/models/audit_log.py): Extend for read operations
- AuditLogger service (src/observability/audit_logger.py): Add log_read_operation() method

**Middleware Patterns**
- AuthMiddleware (src/api/middleware/auth_middleware.py): Base pattern for new decorators (@require_role, @require_permission)
- RateLimitMiddleware (src/api/middleware/rate_limit_middleware.py): Pattern for SecurityHeadersMiddleware, ContentLengthMiddleware, JSONValidationMiddleware
- CorrelationIdMiddleware (src/api/middleware/correlation_id_middleware.py): Pattern for request tracing

**Database & Configuration**
- Settings (src/config/settings.py): Extend with new config values (session timeouts, 2FA settings, admin IP whitelist)
- Database context manager (src/config/database.py): Reuse for new models
- Conversation model (src/models/conversation.py): Extend for sharing relationship
- RedisManager (src/state/redis_manager.py): Reuse for session metadata storage

**Logging & Observability**
- Structured logger (src/observability/structured_logger.py): Use for all new services
- Metrics collector (src/observability/metrics_collector.py): Track security event metrics

### New Components Required

**Models (5 new tables)**
- Role model: System roles (superadmin, admin, user, viewer)
- UserRole model: Many-to-many user-role assignment
- ConversationShare model: Conversation sharing with permission levels
- SecurityEvent model: Security anomaly detection events
- AlertHistory model: Alert delivery tracking

**Services**
- PasswordValidator service: zxcvbn integration, common password checking
- AccountLockoutService: Track failed attempts, enforce lockout, exponential backoff
- TOTPService: pyotp integration, QR code generation, backup codes
- RBACService: Role/permission checking, role assignment
- PermissionService: Resource-level permission validation
- IPWhitelistMiddleware: CIDR range parsing, X-Forwarded-For handling
- SecurityMonitoringService: Anomaly detection algorithms, batch processing
- AlertService: Multi-channel alert delivery (email, Slack, PagerDuty)
- LogArchivalService: S3 archival, restoration, partition management
- SecurityHeadersMiddleware: CSP, HSTS, and other security headers
- ContentLengthMiddleware: Request size validation
- JSONValidationMiddleware: Depth and size validation

**Why New Code is Needed**
- Role and permission models: Phase 1 only had is_superuser flag (binary admin check)
- 2FA/TOTP: No existing MFA infrastructure
- Security monitoring: No existing anomaly detection or event correlation
- Alert system: No existing multi-channel notification infrastructure
- Log archival: No existing long-term storage solution
- Security headers: No existing CSP or header security middleware
- Advanced validation: Phase 1 had basic Pydantic schemas but gaps remain

## Technical Approach

### Database Schema Changes

**Extend users table:**
```sql
ALTER TABLE users
  ADD COLUMN password_last_changed TIMESTAMP WITH TIME ZONE,
  ADD COLUMN legacy_password BOOLEAN DEFAULT FALSE,
  ADD COLUMN failed_login_attempts INTEGER DEFAULT 0,
  ADD COLUMN locked_until TIMESTAMP WITH TIME ZONE,
  ADD COLUMN last_failed_login TIMESTAMP WITH TIME ZONE,
  ADD COLUMN totp_secret TEXT,
  ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN totp_backup_codes JSONB,
  ADD COLUMN last_login_ip VARCHAR(50),
  ADD COLUMN last_login_country VARCHAR(2);
```

**New roles table:**
```sql
CREATE TABLE roles (
  role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  role_name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  is_system BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_roles_name ON roles(role_name);
```

**New user_roles table:**
```sql
CREATE TABLE user_roles (
  user_role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
  assigned_by UUID REFERENCES users(user_id),
  assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, role_id)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

**New conversation_shares table:**
```sql
CREATE TABLE conversation_shares (
  share_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE CASCADE,
  shared_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
  shared_with UUID REFERENCES users(user_id) ON DELETE CASCADE,
  permission_level VARCHAR(20) CHECK (permission_level IN ('view', 'comment', 'edit')),
  shared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(conversation_id, shared_with)
);

CREATE INDEX idx_conversation_shares_conversation_id ON conversation_shares(conversation_id);
CREATE INDEX idx_conversation_shares_shared_with ON conversation_shares(shared_with);
```

**New security_events table:**
```sql
CREATE TABLE security_events (
  event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  event_data JSONB NOT NULL,
  detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMP WITH TIME ZONE,
  resolved_by UUID REFERENCES users(user_id)
);

CREATE INDEX idx_security_events_user_id ON security_events(user_id);
CREATE INDEX idx_security_events_detected_at ON security_events(detected_at);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_resolved ON security_events(resolved);

-- Partition by month (example)
CREATE TABLE security_events_2025_10 PARTITION OF security_events
  FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

**New alert_history table:**
```sql
CREATE TABLE alert_history (
  alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  security_event_id UUID REFERENCES security_events(event_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  alert_type VARCHAR(50) NOT NULL,
  sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  status VARCHAR(20) CHECK (status IN ('sent', 'failed', 'throttled')),
  error_message TEXT
);

CREATE INDEX idx_alert_history_user_id ON alert_history(user_id);
CREATE INDEX idx_alert_history_sent_at ON alert_history(sent_at);
```

**Partition audit_logs table:**
```sql
-- Convert to partitioned table
CREATE TABLE audit_logs_new (LIKE audit_logs INCLUDING ALL) PARTITION BY RANGE (timestamp);
-- Create partitions for current and future months
-- Migrate data
-- Drop old table and rename new
```

### API Endpoints

**Authentication Hardening**
- GET /api/v1/auth/me - Get current user (check for legacy password warning)
- POST /api/v1/auth/session/keep-alive - Extend session idle timeout
- POST /api/v1/admin/users/{user_id}/unlock - Admin unlock account

**2FA/MFA**
- POST /api/v1/auth/2fa/enable - Start 2FA enrollment, return QR code
- POST /api/v1/auth/2fa/verify - Verify TOTP code to complete enrollment
- POST /api/v1/auth/2fa/disable - Disable 2FA for current user
- GET /api/v1/auth/2fa/backup-codes - Get remaining backup codes
- POST /api/v1/auth/2fa/regenerate-backup-codes - Generate new backup codes
- POST /api/v1/auth/login - Extended to handle 2FA flow (return requires_2fa + temp_token)
- POST /api/v1/auth/login/2fa - Complete login with 2FA code

**RBAC**
- GET /api/v1/admin/roles - List all roles
- POST /api/v1/admin/users/{user_id}/roles - Assign role to user
- DELETE /api/v1/admin/users/{user_id}/roles/{role_id} - Remove role from user
- GET /api/v1/users/{user_id}/roles - Get user's roles
- GET /api/v1/users/{user_id}/permissions - Get effective permissions

**Conversation Sharing**
- POST /api/v1/conversations/{conversation_id}/share - Share conversation
- GET /api/v1/conversations/{conversation_id}/shares - List shares for conversation
- PATCH /api/v1/conversations/{conversation_id}/shares/{share_id} - Update share permission
- DELETE /api/v1/conversations/{conversation_id}/shares/{share_id} - Revoke share
- GET /api/v1/conversations/shared-with-me - List conversations shared with current user

**Security Monitoring**
- GET /api/v1/admin/security/events - List security events (paginated)
- GET /api/v1/admin/security/events/{event_id} - Get event details
- PATCH /api/v1/admin/security/events/{event_id}/resolve - Mark event as resolved
- GET /api/v1/admin/security/csp-violations - List CSP violations (last 7 days)
- POST /api/v1/admin/security/csp/enforce - Switch CSP to strict mode

**Log Management**
- POST /api/v1/admin/logs/archive - Manually trigger archival
- POST /api/v1/admin/logs/restore - Restore partition from S3
- DELETE /api/v1/admin/logs/purge - Permanent deletion (superadmin only)

**CSP Violation Reporting**
- POST /api/v1/security/csp-report - Public endpoint for browser CSP reports

### Request/Response Schemas

**2FA Enrollment Response:**
```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "secret": "JBSWY3DPEHPK3PXP",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344",
    "44332211",
    "55667788",
    "88776655"
  ]
}
```

**2FA Login Flow Response:**
```json
{
  "requires_2fa": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Share Conversation Request:**
```json
{
  "user_email": "alice@example.com",
  "permission": "view"
}
```

**Share Conversation Response:**
```json
{
  "share_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "660e8400-e29b-41d4-a716-446655440000",
  "shared_with": {
    "user_id": "770e8400-e29b-41d4-a716-446655440000",
    "email": "alice@example.com",
    "username": "alice"
  },
  "permission": "view",
  "shared_at": "2025-10-26T15:30:00Z"
}
```

**Security Event Response:**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440000",
  "event_type": "failed_login_cluster",
  "severity": "high",
  "user_id": "990e8400-e29b-41d4-a716-446655440000",
  "event_data": {
    "failed_attempts": 5,
    "ip_addresses": ["192.168.1.100"],
    "time_window": "10 minutes"
  },
  "detected_at": "2025-10-26T15:45:00Z",
  "resolved": false
}
```

**Validation Error Response (Enhanced):**
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
  "correlation_id": "abc123-def456-ghi789",
  "timestamp": "2025-10-26T15:50:00Z"
}
```

### Configuration Settings (Add to Settings class)

```python
# Password Policy
PASSWORD_MIN_LENGTH: int = Field(default=12, description="Minimum password length")
PASSWORD_MAX_LENGTH: int = Field(default=128, description="Maximum password length")
PASSWORD_MIN_ENTROPY: int = Field(default=3, description="Minimum zxcvbn score (0-4)")

# Account Lockout
ACCOUNT_LOCKOUT_THRESHOLD: int = Field(default=5, description="Failed attempts before lockout")
ACCOUNT_LOCKOUT_WINDOW_MINUTES: int = Field(default=15, description="Time window for failed attempts")
ACCOUNT_LOCKOUT_DURATIONS: str = Field(default="15,30,60,120,240", description="Lockout durations in minutes")

# Session Timeout
SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=30, description="Session idle timeout")
SESSION_ABSOLUTE_TIMEOUT_HOURS: int = Field(default=12, description="Session absolute timeout")

# Admin IP Whitelist
ADMIN_IP_WHITELIST: str = Field(default="", description="Comma-separated IPs/CIDR ranges")

# 2FA
TOTP_ISSUER_NAME: str = Field(default="DevMatrix", description="TOTP issuer name for QR codes")
TOTP_DIGITS: int = Field(default=6, description="TOTP code length")
TOTP_INTERVAL: int = Field(default=30, description="TOTP time window in seconds")
ENFORCE_2FA: bool = Field(default=False, description="Globally enforce 2FA")

# Security Monitoring
SECURITY_MONITORING_INTERVAL_MINUTES: int = Field(default=5, description="Security event detection interval")
GEOIP2_DATABASE_PATH: str = Field(default="", description="Path to GeoIP2 database file")

# Alerts
SLACK_WEBHOOK_URL: str = Field(default="", description="Slack webhook URL for alerts")
PAGERDUTY_API_KEY: str = Field(default="", description="PagerDuty API key for critical alerts")
ALERT_THROTTLE_HOURS: int = Field(default=1, description="Hours to throttle duplicate alerts")

# Log Retention
LOG_RETENTION_HOT_DAYS: int = Field(default=90, description="Days to keep logs in PostgreSQL")
LOG_RETENTION_COLD_YEARS: int = Field(default=7, description="Years to keep logs in S3")
S3_BUCKET_NAME: str = Field(default="", description="S3 bucket for log archival")
S3_ACCESS_KEY: str = Field(default="", description="S3 access key")
S3_SECRET_KEY: str = Field(default="", description="S3 secret key")

# Security Headers
CSP_REPORT_ONLY: bool = Field(default=True, description="Use CSP report-only mode")
CSP_REPORT_URI: str = Field(default="/api/v1/security/csp-report", description="CSP report endpoint")

# Input Validation
JSON_MAX_DEPTH: int = Field(default=10, description="Maximum JSON nesting depth")
JSON_MAX_SIZE_MB: int = Field(default=10, description="Maximum JSON request size in MB")
```

### Decorator Examples

**@require_role decorator:**
```python
from functools import wraps
from fastapi import HTTPException, status, Depends
from src.api.middleware.auth_middleware import get_current_active_user
from src.models.user import User

def require_role(required_role: str):
    """Require user to have specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            rbac_service = RBACService()
            if not rbac_service.user_has_role(current_user.user_id, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires '{required_role}' role"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.get("/admin/users")
@require_role("admin")
async def list_users(current_user: User = Depends(get_current_active_user)):
    ...
```

**@require_permission decorator:**
```python
def require_permission(permission: str):
    """Require user to have specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            permission_service = PermissionService()
            # Extract resource_id from kwargs if present
            resource_id = kwargs.get('conversation_id') or kwargs.get('message_id')
            if not permission_service.user_can(current_user, permission, resource_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.get("/conversations/{conversation_id}")
@require_permission("conversation:read")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user)
):
    ...
```

### Service Implementation Patterns

**PasswordValidator service:**
```python
from zxcvbn import zxcvbn
from typing import Dict, Any

class PasswordValidator:
    def __init__(self):
        # Load common passwords list
        self.common_passwords = self._load_common_passwords()

    def validate(self, password: str, user_inputs: list = None) -> Dict[str, Any]:
        """
        Validate password strength.

        Returns:
            {
                "valid": bool,
                "score": int (0-4),
                "feedback": str,
                "errors": list
            }
        """
        errors = []

        # Check length
        if len(password) < 12:
            errors.append("Password must be at least 12 characters")

        if len(password) > 128:
            errors.append("Password must be no more than 128 characters")

        # Check common passwords
        if password.lower() in self.common_passwords:
            errors.append("Password is too common")

        # Check against user inputs
        if user_inputs:
            for user_input in user_inputs:
                if user_input.lower() in password.lower():
                    errors.append(f"Password cannot contain '{user_input}'")

        # Check entropy with zxcvbn
        result = zxcvbn(password, user_inputs=user_inputs or [])
        score = result['score']

        if score < 3 and len(password) < 16:
            errors.append(result['feedback']['warning'] or "Password is too weak")

        return {
            "valid": len(errors) == 0,
            "score": score,
            "feedback": self._get_feedback(score),
            "errors": errors
        }

    def _get_feedback(self, score: int) -> str:
        feedback_map = {
            0: "weak",
            1: "weak",
            2: "fair",
            3: "good",
            4: "strong"
        }
        return feedback_map.get(score, "unknown")
```

**AccountLockoutService:**
```python
from datetime import datetime, timedelta
from typing import Optional

class AccountLockoutService:
    def __init__(self):
        self.threshold = 5
        self.window_minutes = 15
        self.lockout_durations = [15, 30, 60, 120, 240]  # minutes

    async def record_failed_attempt(self, user_id: str, ip_address: str) -> Dict[str, Any]:
        """
        Record failed login attempt and check if lockout should trigger.

        Returns:
            {
                "locked": bool,
                "locked_until": datetime or None,
                "attempts_remaining": int
            }
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            # Increment attempts
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.utcnow()

            # Check if should lock
            if user.failed_login_attempts >= self.threshold:
                # Calculate lockout duration based on history
                lockout_count = self._get_lockout_count(user_id)
                duration_index = min(lockout_count, len(self.lockout_durations) - 1)
                duration_minutes = self.lockout_durations[duration_index]

                user.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
                db.commit()

                return {
                    "locked": True,
                    "locked_until": user.locked_until,
                    "attempts_remaining": 0
                }

            db.commit()

            return {
                "locked": False,
                "locked_until": None,
                "attempts_remaining": self.threshold - user.failed_login_attempts
            }

    async def reset_attempts(self, user_id: str):
        """Reset failed login attempts after successful login"""
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            user.failed_login_attempts = 0
            user.last_failed_login = None
            db.commit()

    async def unlock_account(self, user_id: str, admin_user_id: str):
        """Admin manual unlock"""
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

            # Audit log
            await AuditLogger.log_event(
                user_id=admin_user_id,
                action="user.unlock",
                result="success",
                resource_type="user",
                resource_id=user_id
            )
```

### Background Jobs (APScheduler)

**Security monitoring job:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5)
async def detect_security_events():
    """Run security event detection every 5 minutes"""
    service = SecurityMonitoringService()
    await service.detect_failed_login_clusters()
    await service.detect_geo_changes()
    await service.detect_unusual_access_patterns()
    await service.detect_privilege_escalations()
    # ... other detections
```

**Log archival job:**
```python
@scheduler.scheduled_job('cron', day=1, hour=2)  # 1st of month at 2am
async def archive_old_logs():
    """Archive logs older than 90 days to S3"""
    service = LogArchivalService()
    await service.archive_old_partitions()
```

**Auto-unlock job:**
```python
@scheduler.scheduled_job('interval', minutes=5)
async def auto_unlock_expired_lockouts():
    """Auto-unlock accounts whose lockout period has expired"""
    with get_db_context() as db:
        now = datetime.utcnow()
        locked_users = db.query(User).filter(
            User.locked_until != None,
            User.locked_until <= now
        ).all()

        for user in locked_users:
            user.locked_until = None
            user.failed_login_attempts = 0

        db.commit()
```

## Out of Scope

**Deferred to Phase 3 (Medium Priority):**
- Teams/Organizations multi-tenancy
- File uploads (user avatars, attachments)
- Advanced permission delegation
- Conversation templates
- Bulk operations

**Deferred to Phase 4 (Compliance):**
- WebAuthn/FIDO2 hardware keys
- Biometric authentication
- GDPR data export/deletion automation
- PCI-DSS compliance

**Deferred to Phase 5 (Integrations):**
- OAuth2 provider (allow third-party apps)
- Real-time threat intelligence feeds
- SIEM integration (Splunk, ELK)
- Security Information Event Manager

**Deferred to Phase 6 (Advanced Auth):**
- SMS 2FA (insecure, low priority)
- Social login (Google, GitHub, Microsoft)
- SSO/SAML enterprise integration
- LDAP/Active Directory integration

**Never Planned:**
- Blockchain-based authentication
- Face recognition authentication
- Password recovery "security questions" (security anti-pattern)
- Voice authentication

## Success Criteria

**Authentication Hardening:**
- 95%+ of active users have passwords meeting new policy within 60 days
- Account lockout reduces brute force attempts by 90%
- Session timeout reduces unauthorized access incidents to zero
- Zero password-related vulnerabilities in penetration testing

**Authorization:**
- 100% of admin actions protected by RBAC
- Zero privilege escalation vulnerabilities in penetration testing
- Conversation sharing used by 30%+ of active users within 90 days
- All permission checks complete in <50ms (p95)

**Security Monitoring:**
- 100% of security events detected within 5 minutes of occurrence
- 95%+ of critical alerts delivered within 1 minute
- Zero false positives for critical alerts
- <5% false positive rate for high severity alerts
- All anomaly detection algorithms have >90% precision

**Compliance:**
- 100% audit log retention compliance (7 years)
- Zero critical vulnerabilities in CSP validation
- 100% of API endpoints have input validation
- All security headers present on 100% of responses
- Archival process completes successfully 12/12 months

**Testing:**
- 100+ new tests passing (60 unit, 30 integration, 10 security)
- 95%+ code coverage on Phase 2 features
- Zero critical vulnerabilities found in security review
- All tests execute in <5 minutes

**Performance:**
- API p95 latency remains <200ms with new middleware
- Database query performance not degraded by new indexes
- Redis session storage <10ms p95
- Security monitoring job completes in <30 seconds

**Documentation:**
- All new endpoints documented in OpenAPI/Swagger
- Security runbooks created for incident response
- Admin guides for role management and security monitoring
- Compliance documentation for SOC 2 audit readiness
