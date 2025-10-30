# Tech Stack: Phase 2 - High Priority Security & Reliability

Complete technical stack documentation for Phase 2 of the DevMatrix MVP Security Remediation project, including new security libraries, authentication enhancements, monitoring tools, and integration points.

---

## Overview

Phase 2 builds on Phase 1's critical security foundation by adding enterprise-grade authentication, authorization, monitoring, and validation capabilities. This document focuses on new technologies, libraries, and integration points introduced in Phase 2.

**Phase 1 Foundation (Inherited):**
- Environment-based configuration with Pydantic Settings
- JWT-based authentication with token blacklisting
- Redis-backed rate limiting and caching
- Standardized error responses with correlation IDs
- Basic audit logging infrastructure
- Parameterized queries for SQL injection prevention

**Phase 2 Additions:**
- Password complexity validation and strength checking
- Account lockout with exponential backoff
- Session timeout management
- 2FA/MFA with TOTP
- Role-based access control (RBAC)
- Granular permission system
- Security event monitoring and alerting
- Advanced input validation (file uploads, size limits)
- Comprehensive security headers

---

## Authentication & Session Management

### Password Security

**passlib 1.7+** - Comprehensive password hashing library
- **Features:**
  - Multiple password hashing schemes (bcrypt, argon2, scrypt)
  - Password strength estimation
  - Common password detection
  - Password policy enforcement
- **Phase 2 Usage:**
  - Validate password complexity requirements
  - Check against common password blacklist
  - Password strength meter (0-100 score)
  - Secure password hashing (already using bcrypt from Phase 1)

**zxcvbn-python 4.4+** - Password strength estimation
- **Features:**
  - Realistic password strength estimation
  - Pattern matching (keyboard patterns, sequences, repeats)
  - Dictionary attack resistance scoring
  - Feedback for password improvement
- **Phase 2 Usage:**
  - Real-time password strength meter
  - User-friendly strength feedback
  - Minimum strength threshold enforcement

**common-passwords library** - Top 10,000 weak passwords blacklist
- **Data Source:** Compiled from breach databases
- **Format:** Text file with one password per line
- **Phase 2 Usage:**
  - Block commonly used weak passwords
  - Case-insensitive matching
  - Regular blacklist updates

### Account Lockout & Rate Limiting

**Redis 7+** (inherited from Phase 1, extended usage)
- **Phase 2 New Use Cases:**
  - Failed login attempt tracking per user
  - Account lockout state with TTL (30 minutes default)
  - Exponential backoff state tracking
  - IP-based brute force detection across users
  - Session activity tracking for timeout calculation

**Redis Key Formats (Phase 2):**
```
lockout:user:{user_id}           # Value: attempt count, TTL: cooldown period
lockout:ip:{ip_address}          # Value: attempt count, TTL: sliding window
session:activity:{session_id}    # Value: last_activity timestamp, TTL: idle timeout
session:metadata:{session_id}    # Value: JSON metadata (IP, user_agent, geo), TTL: absolute timeout
```

### Session Management

**FastAPI Sessions** - Session management middleware
- **Alternative: itsdangerous** - Signed session data (if using cookie-based sessions)
- **Phase 2 Usage:**
  - Session metadata storage (creation time, last activity, IP, user agent)
  - Dual timeout tracking (idle and absolute)
  - Session renewal on activity
  - Session enumeration for user dashboard
  - Session termination (logout specific session)

**ScheduledTask (APScheduler 3.10+)** - Background job scheduler
- **Features:**
  - Cron-like job scheduling
  - Interval-based job execution
  - Job persistence across restarts
  - Concurrent job execution
- **Phase 2 Usage:**
  - Automatic session cleanup (expired sessions)
  - Account unlock scheduler (after cooldown)
  - Share expiration cleanup
  - Log archival scheduler

### Two-Factor Authentication (2FA/MFA)

**pyotp 2.9+** - Python One-Time Password library (TOTP/HOTP implementation)
- **Features:**
  - RFC 6238 compliant TOTP (Time-based OTP)
  - RFC 4226 compliant HOTP (HMAC-based OTP)
  - Secret key generation
  - QR code provisioning URI generation
  - Configurable time window and digest algorithm
- **Phase 2 Usage:**
  - Generate TOTP secrets for user enrollment
  - Validate TOTP codes with time window (±30s default)
  - Create provisioning URIs for QR codes
  - Backup code generation (cryptographically random)

**qrcode 7.4+** - QR code generation library
- **Features:**
  - Pure Python QR code generator
  - Multiple output formats (PNG, SVG, ASCII)
  - Configurable error correction levels
  - Image embedding support
- **Phase 2 Usage:**
  - Generate QR codes for 2FA enrollment
  - Display QR codes in API responses (base64 PNG)
  - Support for authenticator apps (Google Authenticator, Authy, 1Password)

**Pillow (PIL) 10.0+** - Python Imaging Library (dependency for qrcode)
- **Features:**
  - Image processing and manipulation
  - Multiple image format support
  - Drawing and text rendering
- **Phase 2 Usage:**
  - QR code image generation
  - QR code styling and branding (optional)

### IP-Based Access Control

**ipaddress** - Python standard library for IP address manipulation
- **Features:**
  - IPv4 and IPv6 address objects
  - Network (CIDR) notation support
  - IP address validation
  - Range checking (IP in network)
- **Phase 2 Usage:**
  - Parse and validate IP addresses
  - Check if IP is in whitelist (CIDR ranges)
  - IP range validation in admin UI

**geoip2 4.7+** - MaxMind GeoIP2 client (optional)
- **Features:**
  - Geographic IP lookup (country, city, coordinates)
  - ASN (Autonomous System Number) lookup
  - Connection type detection
  - Free GeoLite2 database support
- **Phase 2 Usage (Optional):**
  - Geographic location for audit logs
  - Country-based access blocking
  - Anomaly detection (unusual login location)
  - Compliance with data residency requirements

**MaxMind GeoLite2 Database** - Free IP geolocation database
- **Format:** MMDB (MaxMind Database)
- **Update Frequency:** Weekly updates available
- **License:** Creative Commons Attribution-ShareAlike 4.0
- **Phase 2 Usage:**
  - Offline IP geolocation (no external API calls)
  - Privacy-friendly (no data sent to third party)

---

## Authorization & Access Control

### Role-Based Access Control (RBAC)

**Custom RBAC Implementation** - Built on SQLAlchemy and Pydantic
- **Components:**
  - Role model with permissions JSON field
  - User-role relationship (one-to-one for Phase 2, many-to-many future)
  - Permission inheritance from roles to users
  - Decorator-based role validation (@require_role)
  - Efficient permission caching in Redis

**Predefined Roles (Phase 2):**
```python
ROLES = {
    "viewer": {
        "permissions": ["conversation:read", "message:read"],
        "rate_limit": "50/minute",
        "session_timeout": "30 minutes"
    },
    "developer": {
        "permissions": ["conversation:*", "message:*", "masterplan:*"],
        "rate_limit": "100/minute",
        "session_timeout": "2 hours"
    },
    "admin": {
        "permissions": ["*:*", "user:manage", "role:assign"],
        "rate_limit": "200/minute",
        "session_timeout": "4 hours"
    },
    "superadmin": {
        "permissions": ["*:*"],
        "rate_limit": "unlimited",
        "session_timeout": "8 hours"
    }
}
```

### Granular Permission System

**Permission Format:** `{resource}:{action}`
- **Resources:** conversation, message, masterplan, user, role, system
- **Actions:** read, write, delete, share, admin, * (wildcard)
- **Examples:**
  - `conversation:read` - Read conversations
  - `conversation:*` - All conversation actions
  - `*:*` - All actions on all resources (superadmin)

**Permission Caching Strategy:**
- **Cache Layer:** Redis with 5-minute TTL
- **Cache Key:** `permissions:user:{user_id}`
- **Cache Value:** JSON array of permission strings
- **Invalidation:** On role change, permission grant/revoke
- **Fallback:** Database query if cache miss

### Resource Sharing & Collaboration

**ConversationShare Model** - Resource-level permissions
- **Fields:**
  - conversation_id (FK to conversations)
  - shared_with_user_id (FK to users)
  - shared_by_user_id (FK to users)
  - permission_level (read, write, admin)
  - expires_at (optional expiration)
  - created_at
- **Access Logic:**
  - Check ownership OR share existence
  - Validate permission level for action
  - Respect expiration date
  - Audit all shared access

---

## Security Monitoring & Alerting

### Security Event Processing

**Custom Event Processing System** - Real-time security event detection
- **Architecture:**
  - Event publisher (middleware, services)
  - Event stream (Redis Streams or in-memory queue)
  - Event processor (async background worker)
  - Event storage (PostgreSQL security_events table)
  - Alert generator (triggers on patterns)

**Redis Streams 7+** - Event streaming for real-time processing
- **Features:**
  - Append-only log structure
  - Consumer groups for parallel processing
  - Message acknowledgment and retries
  - Persistent message storage
- **Phase 2 Usage:**
  - Security event stream (failed logins, permission denials, anomalies)
  - Real-time event processing (<1s latency)
  - Event correlation across time windows
  - Buffering during high load

**Event Types (Phase 2):**
```
auth.login.failed          # Failed login attempt
auth.login.success         # Successful login
auth.lockout.triggered     # Account locked due to failed attempts
auth.lockout.unlocked      # Account unlocked (auto or manual)
auth.2fa.failed            # 2FA validation failed
auth.session.timeout       # Session expired
authz.permission.denied    # Permission check failed
authz.role.changed         # User role modified
security.anomaly.detected  # Anomaly detection triggered
security.brute_force       # Brute force attack pattern detected
```

### Anomaly Detection

**scikit-learn 1.3+** - Machine learning library (optional, for advanced anomaly detection)
- **Features:**
  - Isolation Forest algorithm for anomaly detection
  - One-Class SVM for novelty detection
  - Statistical outlier detection
- **Phase 2 Usage (Optional):**
  - Detect unusual login times (compared to user's baseline)
  - Detect abnormal API usage patterns
  - Identify velocity anomalies (too many requests too fast)
  - Geographic anomalies (login from unusual location)

**Baseline Anomaly Detection (Phase 2 Core):**
- **Statistical Approach:** Mean + 3 standard deviations
- **Metrics Tracked:**
  - Login time distribution per user
  - API request rate per user
  - Geographic login locations per user
  - Session duration distribution
- **Thresholds:**
  - Configurable sensitivity (1-5 sigma)
  - Per-user baselines (calculated over 30 days)
  - Global baselines for new users

### Alert System

**SMTP (smtplib)** - Python standard library for email
- **Features:**
  - TLS/SSL support
  - HTML email support
  - Attachment support
- **Phase 2 Usage:**
  - Email alerts for critical security events
  - Daily/weekly security digest emails
  - Compliance report delivery
  - Alert template rendering (HTML)

**Jinja2 3.1+** - Template engine for email and report generation
- **Features:**
  - Template inheritance and includes
  - Auto-escaping for security
  - Filters and custom functions
  - Async template rendering
- **Phase 2 Usage:**
  - Email alert templates (HTML and plain text)
  - Security report templates
  - Compliance report templates
  - Alert message formatting

**requests 2.31+** - HTTP library for webhook delivery
- **Features:**
  - Slack webhook integration
  - PagerDuty API integration
  - Custom webhook delivery
  - Retry logic with exponential backoff
  - Timeout configuration
- **Phase 2 Usage:**
  - Slack alert delivery (webhooks)
  - PagerDuty incident creation (optional)
  - Custom webhook delivery for integrations
  - Alert delivery tracking (success/failure)

**Slack SDK for Python 3.21+** (optional, alternative to webhooks)
- **Features:**
  - Rich message formatting (Block Kit)
  - Interactive buttons and modals
  - File uploads
  - Rate limit handling
- **Phase 2 Usage (Optional):**
  - Rich Slack notifications with buttons
  - Interactive incident response (acknowledge, resolve)
  - Security dashboard in Slack

**PagerDuty API Client** (optional, pypd 1.1+)
- **Features:**
  - Incident creation and management
  - Escalation policy support
  - On-call schedule integration
  - Incident notes and status updates
- **Phase 2 Usage (Optional):**
  - Create PagerDuty incidents for critical alerts
  - Integrate with on-call rotation
  - Automatic incident acknowledgment tracking

### Log Retention & Archival

**PostgreSQL 16+ Table Partitioning** - Native table partitioning
- **Features:**
  - Range partitioning by date
  - Automatic partition creation
  - Efficient partition pruning in queries
  - Partition-level retention policies
- **Phase 2 Usage:**
  - Partition audit_logs table by month
  - Partition security_events table by month
  - Fast queries on recent data
  - Easy archival of old partitions

**boto3 1.28+** - AWS SDK for Python (for S3 archival)
- **Features:**
  - S3 object upload and download
  - Multipart upload for large files
  - Server-side encryption
  - Lifecycle policies
- **Phase 2 Usage:**
  - Archive old log partitions to S3
  - Cost-effective long-term storage (S3 Glacier)
  - Compliance retention (7 years for security logs)

**Azure Blob Storage SDK** (alternative: azure-storage-blob 12.18+)
- **Features:**
  - Blob upload and download
  - Tiered storage (Hot, Cool, Archive)
  - Data encryption at rest
  - Lifecycle management
- **Phase 2 Usage (Alternative to S3):**
  - Archive logs to Azure Blob Storage
  - Use Archive tier for cost optimization
  - Compliance retention

**Log Integrity (Cryptographic Signing):**
- **hashlib** - Python standard library for hashing
- **Approach:** Hash chaining (each log entry includes hash of previous entry)
- **Algorithm:** SHA-256
- **Storage:** Hash stored in log metadata, initial hash in separate integrity table
- **Verification:** Replay hash chain to detect tampering

**pg_dump / pg_restore** - PostgreSQL backup utilities
- **Features:**
  - Full and incremental backups
  - Table-level backup (specific log tables)
  - Parallel backup and restore
  - Compressed backups
- **Phase 2 Usage:**
  - Backup log partitions before archival
  - Restore archived logs for compliance queries
  - Disaster recovery for audit logs

---

## Input Validation & Security Headers

### File Upload Security

**python-magic 0.4+** - File type detection library
- **Features:**
  - MIME type detection based on file content (magic numbers)
  - No reliance on file extensions
  - libmagic integration (C library)
- **Phase 2 Usage:**
  - Validate uploaded file MIME type
  - Prevent MIME type spoofing (extension vs content mismatch)
  - Detect malicious files disguised as safe types

**libmagic** - C library for file type detection
- **Platform:**
  - Linux: `sudo apt-get install libmagic1`
  - macOS: `brew install libmagic`
  - Windows: Included in python-magic-bin
- **Dependency:** Required by python-magic

**filetype 1.2+** - Pure Python file type detection (alternative)
- **Features:**
  - No C dependencies (pure Python)
  - Magic number-based detection
  - Supports 100+ file types
- **Phase 2 Usage (Alternative):**
  - File type detection without libmagic dependency
  - Portable across platforms

**Virus Scanning Integration (Optional):**

**pyclamd 0.4+** - ClamAV Python client
- **Features:**
  - Scan files for malware
  - Network daemon communication
  - Scan results parsing
- **Phase 2 Usage (Optional):**
  - Scan uploaded files before storage
  - Integrate with ClamAV daemon
  - Quarantine infected files

**ClamAV** - Open-source antivirus engine
- **Features:**
  - Signature-based malware detection
  - Regular signature updates
  - Network daemon (clamd)
- **Deployment:** Docker container or system service
- **Phase 2 Usage (Optional):**
  - Run ClamAV daemon for file scanning
  - Update virus definitions daily

**Cloud Virus Scanning (Alternative):**
- **VirusTotal API** - Multi-engine virus scanning
- **Cloudmersive Virus Scan API** - Cloud-based scanning
- **Phase 2 Usage:** Submit uploaded files to cloud scanning service

### Request Size & JSON Validation

**FastAPI Request Validation** - Built-in features (extended for Phase 2)
- **Features:**
  - Request body size limits (via Starlette)
  - JSON schema validation (via Pydantic)
  - Query parameter validation
  - Path parameter validation
- **Phase 2 Extensions:**
  - Custom JSON depth validator
  - Recursive structure detector
  - Content-length enforcement middleware
  - JSON complexity limits (keys, arrays)

**Starlette Middleware** - ASGI middleware framework (FastAPI dependency)
- **Phase 2 Usage:**
  - Request size limit middleware (checks Content-Length header)
  - JSON depth validation middleware
  - Content-type validation middleware
  - Charset enforcement middleware

**JSON Validation Limits (Phase 2):**
```python
JSON_MAX_DEPTH = 10           # Prevent deeply nested JSON
JSON_MAX_ARRAY_LENGTH = 1000  # Prevent large arrays
JSON_MAX_STRING_LENGTH = 10240  # 10KB max string
JSON_MAX_OBJECT_KEYS = 100    # Prevent objects with many keys
REQUEST_BODY_MAX_SIZE = 10 * 1024 * 1024  # 10MB
```

### Security Headers

**Security Headers Middleware (Custom Implementation)**
- **Headers Implemented:**

  **Content-Security-Policy (CSP):**
  ```
  default-src 'self';
  script-src 'self' https://cdn.devmatrix.com 'nonce-{random}';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self';
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  report-uri /api/v1/csp-report
  ```

  **Strict-Transport-Security (HSTS):**
  ```
  max-age=63072000; includeSubDomains; preload
  ```

  **X-Frame-Options:**
  ```
  DENY
  ```

  **X-Content-Type-Options:**
  ```
  nosniff
  ```

  **Referrer-Policy:**
  ```
  strict-origin-when-cross-origin
  ```

  **Permissions-Policy:**
  ```
  camera=(), microphone=(), geolocation=(), payment=()
  ```

**CSP Nonce Generation:**
- **secrets.token_urlsafe(16)** - Cryptographically random nonce
- **Per-request nonce** - New nonce for each request
- **Nonce injection** - Add nonce to inline scripts (if needed)
- **Middleware integration** - Nonce available in request context

**CSP Violation Reporting:**
- **Endpoint:** POST /api/v1/csp-report
- **Log violations** - Store CSP violation reports
- **Alert on violations** - Trigger alerts for repeated violations
- **Analysis** - Identify XSS attack attempts

---

## Database & ORM

### PostgreSQL Extensions (Phase 2)

**uuid-ossp Extension** - UUID generation (already enabled in Phase 1)
- **Usage:** Default UUID primary keys
- **Functions:** uuid_generate_v4()

**pg_trgm Extension** - Trigram text search (for log search)
- **Features:**
  - Fuzzy text search
  - Similarity scoring
  - GIN/GiST indexes for text search
- **Phase 2 Usage:**
  - Efficient audit log search
  - Security event search and filtering
  - User search by name/email

**pg_cron Extension** (optional) - PostgreSQL job scheduler
- **Features:**
  - Cron-like job scheduling in PostgreSQL
  - SQL-based job definitions
  - Job history tracking
- **Phase 2 Usage (Optional):**
  - Database-level log cleanup jobs
  - Partition maintenance jobs
  - Archive old partitions
- **Alternative:** Use APScheduler in Python application

### SQLAlchemy Patterns (Phase 2)

**Table Partitioning:**
```python
# audit_logs partitioned by month
audit_logs_2025_01 = Table(
    'audit_logs_2025_01',
    metadata,
    Column(...),
    postgresql_partition_by='RANGE (timestamp)',
    postgresql_partition_of='audit_logs',
    postgresql_partition_for='VALUES FROM (\'2025-01-01\') TO (\'2025-02-01\')'
)
```

**Efficient Querying:**
```python
# Use selectinload for eager loading
query = select(User).options(selectinload(User.role))

# Use joinedload for one-to-one relationships
query = select(User).options(joinedload(User.permissions))

# Use subqueryload for large collections
query = select(User).options(subqueryload(User.conversations))
```

**Permission Queries (Optimized):**
```python
# Check permission with caching
def has_permission(user_id: UUID, permission: str) -> bool:
    # Try cache first
    cache_key = f"permissions:user:{user_id}"
    cached = redis.get(cache_key)
    if cached:
        return permission in json.loads(cached)

    # Query database
    permissions = db.query(Permission).filter(
        Permission.user_id == user_id
    ).all()

    # Cache for 5 minutes
    redis.setex(cache_key, 300, json.dumps([p.name for p in permissions]))

    return permission in [p.name for p in permissions]
```

---

## Testing & Validation

### Security Testing Tools

**bandit 1.7+** - Python security linter (inherited from Phase 1, extended)
- **Phase 2 New Checks:**
  - Password storage validation (no plaintext passwords)
  - Cryptographic random number usage (secrets module)
  - TOTP secret generation security
  - File upload handling security
  - SQL injection patterns (extended)

**safety 2.3+** - Dependency vulnerability scanner (inherited from Phase 1)
- **Phase 2 New Dependencies:**
  - Scan pyotp, qrcode, passlib, geoip2, etc.
  - Check for known vulnerabilities in auth libraries

**OWASP ZAP (Zed Attack Proxy)** - Security testing tool
- **Features:**
  - Automated vulnerability scanning
  - Active and passive scanning
  - API security testing
  - Authentication testing
- **Phase 2 Testing:**
  - Test 2FA implementation
  - Test RBAC bypass attempts
  - Test session timeout enforcement
  - Test security headers (automated)
  - Test file upload restrictions

**Mozilla Observatory CLI** - Security header testing
- **Features:**
  - Automated header checking
  - CSP validation
  - TLS configuration testing
  - Grading (A+ to F)
- **Phase 2 Testing:**
  - Validate all security headers present
  - Verify CSP configuration
  - Check HSTS preload eligibility
  - Ensure A+ grade

### Load Testing with Security Features

**Locust 2.15+** - Load testing framework (inherited from Phase 1, extended)
- **Phase 2 Load Tests:**
  - Authentication with 2FA (login flow under load)
  - Permission checks under load (RBAC performance)
  - Audit logging under load (no log loss)
  - Alert system under load (alert delivery reliability)
  - Session management under load (timeout accuracy)

**Load Testing Scenarios:**
```python
# Test authentication with lockout
class AuthLoadTest(HttpUser):
    @task
    def login_with_2fa(self):
        # Login with username/password
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test@example.com",
            "password": "SecurePassword123!"
        })
        # Validate 2FA challenge returned
        # Submit TOTP code
        # Measure total authentication time
```

---

## Development & Deployment Tools

### Background Job Processing

**APScheduler 3.10+** - Advanced Python Scheduler
- **Features:**
  - Cron-like scheduling
  - Interval-based scheduling
  - Date-based scheduling
  - Job persistence (database or Redis)
  - Concurrent job execution
- **Phase 2 Jobs:**
  - Session cleanup (every 5 minutes)
  - Account auto-unlock (every 1 minute)
  - Share expiration cleanup (every 10 minutes)
  - Log archival (daily at 2 AM)
  - Log rotation (weekly)
  - Anomaly baseline recalculation (daily)

**Celery 5.3+** (alternative for distributed background jobs)
- **Features:**
  - Distributed task queue
  - Redis or RabbitMQ backend
  - Task retries and error handling
  - Task monitoring (Flower)
- **Phase 2 Usage (Optional):**
  - Distribute log archival jobs
  - Parallel virus scanning
  - Async alert delivery
  - Security event processing at scale

### Environment Configuration

**python-dotenv 1.0+** - .env file loader (inherited from Phase 1)
- **Phase 2 New Variables:** 50+ new environment variables
- **Validation:** Pydantic Settings validates all on startup

**Pydantic Settings 2.0+** - Type-safe configuration (inherited from Phase 1, extended)
- **Phase 2 Extensions:**
  - SecuritySettings class (password policies, lockout config, 2FA config)
  - MonitoringSettings class (alert configuration, log retention)
  - ValidationSettings class (file upload limits, JSON limits)
  - Settings inheritance and composition

---

## External Services & APIs

### Required Services (Phase 2)

**SMTP Server** - Email delivery (new requirement)
- **Options:**
  - SendGrid (cloud service, 100 emails/day free)
  - AWS SES (Simple Email Service)
  - Mailgun
  - Self-hosted SMTP (Postfix, Sendmail)
- **Configuration:**
  - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
  - TLS/SSL configuration
  - From address and display name

**Slack Workspace** (optional) - Alert delivery
- **Setup:**
  - Create Slack app
  - Enable Incoming Webhooks
  - Generate webhook URL
- **Configuration:**
  - SLACK_WEBHOOK_URL environment variable

**Cloud Storage** (optional but recommended) - Log archival
- **Options:**
  - AWS S3 (most common, cost-effective)
  - Azure Blob Storage
  - Google Cloud Storage
  - Backblaze B2 (budget option)
  - MinIO (self-hosted S3-compatible)
- **Configuration:**
  - Storage URL, access keys, bucket name
  - Lifecycle policies for automatic archival to Glacier/Archive tier

### Optional Services (Phase 2)

**PagerDuty** - On-call alerting and incident management
- **Features:**
  - On-call rotation management
  - Escalation policies
  - Mobile app for alerts
  - Incident tracking
- **Configuration:**
  - PAGERDUTY_INTEGRATION_KEY environment variable

**MaxMind GeoIP2** - IP geolocation service
- **Free Option:** GeoLite2 database (local lookup, no API calls)
- **Paid Option:** GeoIP2 Precision API (more accurate, real-time)
- **Configuration:**
  - Database file path (GeoLite2) or API key (GeoIP2 Precision)

**ClamAV Daemon** - Virus scanning
- **Deployment Options:**
  - Docker container (easiest)
  - System service (Linux)
  - Cloud service (Cloudmersive, VirusTotal API)
- **Configuration:**
  - CLAMAV_HOST, CLAMAV_PORT environment variables

**VirusTotal API** - Multi-engine virus scanning (alternative to ClamAV)
- **Features:**
  - 70+ antivirus engines
  - File reputation database
  - API for file scanning
- **Limits:** Free tier 4 requests/minute
- **Configuration:**
  - VIRUSTOTAL_API_KEY environment variable

---

## Security Compliance & Standards

### Authentication Standards

**RFC 6238** - TOTP: Time-Based One-Time Password Algorithm
- **Implementation:** pyotp library
- **Configuration:**
  - Time step: 30 seconds
  - Digest algorithm: SHA-1 (standard), SHA-256 (optional)
  - Code digits: 6
  - Time window: ±1 time step (90 seconds total)

**NIST SP 800-63B** - Digital Identity Guidelines (Authentication)
- **Compliance:**
  - Password complexity requirements (12+ characters)
  - Common password blocking (top 10,000)
  - Account lockout with exponential backoff
  - Session timeout (idle and absolute)
  - 2FA for privileged accounts

**OWASP Authentication Cheat Sheet**
- **Compliance:**
  - Secure password storage (bcrypt with cost factor 12+)
  - No password hints or knowledge-based authentication
  - Account lockout (not username enumeration)
  - 2FA for sensitive operations
  - Session management best practices

### Authorization Standards

**NIST RBAC Standard** - Role-Based Access Control
- **Implementation:**
  - Core RBAC (users, roles, permissions)
  - Hierarchical RBAC (role inheritance, future)
  - Constrained RBAC (separation of duties, future)

**OWASP Authorization Cheat Sheet**
- **Compliance:**
  - Deny by default (explicit permission required)
  - Least privilege principle
  - Resource-level authorization
  - Audit all authorization decisions
  - Separation of authorization logic from business logic

### Logging & Monitoring Standards

**OWASP Logging Cheat Sheet**
- **Compliance:**
  - Log all authentication events (success and failure)
  - Log all authorization decisions (grant and deny)
  - Log all data access and modifications
  - Include timestamp, user ID, IP, action, result
  - Secure log storage (integrity verification)
  - No sensitive data in logs (passwords, tokens)

**SOC 2 Type 1 Requirements** (Security)
- **Compliance:**
  - Logical access controls (authentication, authorization)
  - Security monitoring and incident response
  - Audit logging with retention policies
  - Change management (permission changes logged)
  - Vulnerability management (security testing)

**ISO 27001:2022** - Information Security Management
- **Compliance:**
  - Access control policy (RBAC)
  - User authentication (password policies, 2FA)
  - Audit logging and monitoring
  - Incident management (alert system)
  - Security event analysis

**GDPR** - General Data Protection Regulation
- **Compliance:**
  - Audit trail for data access (read logging)
  - Right to erasure (soft delete, data retention)
  - Data breach notification (alert system)
  - Access control (RBAC, permissions)
  - Consent management (share acceptance)

---

## Performance Considerations

### Caching Strategy (Phase 2 Extensions)

**Permission Caching:**
- **TTL:** 5 minutes (balance freshness and performance)
- **Invalidation:** On role change, permission grant/revoke
- **Pattern:** Cache-aside (check cache, query DB, populate cache)
- **Impact:** 95%+ cache hit rate expected (permissions rarely change)

**Session Metadata Caching:**
- **TTL:** Equal to session timeout (30 minutes idle, 12 hours absolute)
- **Storage:** Redis hashes for efficient field updates
- **Updates:** Last activity timestamp on every request
- **Impact:** Reduces database load for session validation

**RBAC Role Caching:**
- **TTL:** 1 hour (roles change infrequently)
- **Invalidation:** On role modification
- **Pattern:** Cache-through (update cache on write)

### Database Performance

**New Indexes (Phase 2):**
```sql
-- User security fields
CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_users_locked ON users(locked_until) WHERE locked_until IS NOT NULL;
CREATE INDEX idx_users_totp ON users(totp_enabled) WHERE totp_enabled = true;

-- Permissions
CREATE INDEX idx_user_permissions_user ON user_permissions(user_id);
CREATE INDEX idx_user_permissions_resource ON user_permissions(resource_type, resource_id);

-- Sharing
CREATE INDEX idx_conversation_shares_conversation ON conversation_shares(conversation_id);
CREATE INDEX idx_conversation_shares_user ON conversation_shares(shared_with_user_id);
CREATE INDEX idx_conversation_shares_expires ON conversation_shares(expires_at) WHERE expires_at IS NOT NULL;

-- Security events
CREATE INDEX idx_security_events_type ON security_events(event_type);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_detected ON security_events(detected_at);
CREATE INDEX idx_security_events_user ON security_events(user_id);

-- Audit logs (partitioned)
CREATE INDEX idx_audit_logs_session ON audit_logs(session_id);
CREATE INDEX idx_audit_logs_correlation ON audit_logs(correlation_id);
```

**Query Optimization:**
- **Eager loading:** Use selectinload/joinedload for related entities
- **Pagination:** All list endpoints (security events, audit logs)
- **Partition pruning:** Date-based queries on partitioned tables
- **Index-only scans:** Cover common queries with indexes

### Monitoring Performance Impact

**Expected Overhead (Phase 2):**
- **Audit logging (read operations):** +2-5ms per request (async logging)
- **Permission checking (with cache):** +1-3ms per request (cache hit)
- **Permission checking (cache miss):** +10-20ms per request (database query)
- **Session timeout checking:** +1-2ms per request (Redis lookup)
- **Security headers:** +0.5-1ms per request (middleware)
- **Total expected impact:** +5-10ms per request (with 95% cache hit rate)

**Optimization Strategies:**
- Async audit logging (non-blocking)
- Permission caching in Redis (5-minute TTL)
- Batch session updates (update last_activity every 30 seconds, not every request)
- Connection pooling (reuse database connections)
- Efficient queries (indexes, eager loading)

---

## Development Workflow (Phase 2)

### Local Development Setup

**New Services (Docker Compose):**
```yaml
version: '3.8'
services:
  # Inherited from Phase 1: postgresql, redis, chromadb

  # New in Phase 2
  clamav:
    image: clamav/clamav:latest
    ports:
      - "3310:3310"
    volumes:
      - clamav-data:/var/lib/clamav

  mailhog:  # Email testing (SMTP server + web UI)
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

  minio:  # S3-compatible storage (local testing)
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio-data:/data
```

### Testing Workflow (Phase 2)

**Security Testing:**
```bash
# Run security linters
bandit -r src/
safety check

# Run OWASP ZAP scan
zap-cli quick-scan http://localhost:8000

# Run security header check
python scripts/check_security_headers.py

# Run SQL injection tests
pytest tests/security/test_sql_injection.py

# Run authentication tests (including 2FA)
pytest tests/security/test_authentication.py

# Run authorization tests (RBAC, permissions)
pytest tests/security/test_authorization.py
```

**Load Testing:**
```bash
# Run load test with security features
locust -f tests/load/test_auth_under_load.py --host http://localhost:8000

# Specific scenarios
locust -f tests/load/test_rbac_performance.py
locust -f tests/load/test_audit_logging_performance.py
```

**Manual Testing:**
```bash
# Test 2FA enrollment
curl -X POST http://localhost:8000/api/v1/auth/2fa/enroll \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "MyPassword123!"}'

# Test account lockout
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "test@example.com", "password": "wrong"}'
done

# Test session timeout
sleep 1800  # Wait 30 minutes (idle timeout)
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN"  # Should return 401
```

---

## Version Information (Phase 2)

**New Dependencies:**
- **passlib:** 1.7.4
- **zxcvbn-python:** 4.4.28
- **pyotp:** 2.9.0
- **qrcode:** 7.4.2
- **Pillow:** 10.1.0
- **geoip2:** 4.7.0 (optional)
- **python-magic:** 0.4.27
- **pyclamd:** 0.4.0 (optional)
- **APScheduler:** 3.10.4
- **boto3:** 1.28.85 (optional, for S3)
- **azure-storage-blob:** 12.18.3 (optional, for Azure)

**Updated Dependencies:**
- **Redis:** 7.2+ (extended usage)
- **PostgreSQL:** 16+ (table partitioning, pg_trgm)
- **FastAPI:** 0.104+ (extended middleware)

**Python Version:** 3.12+ (unchanged from Phase 1)

---

## Cost Estimates (Phase 2 Additions)

**Infrastructure Costs:**
- **Email Service (SendGrid):** $0-15/month (100-40,000 emails)
- **Cloud Storage (S3):** $5-20/month (log archival, 100GB-1TB)
- **GeoIP Database (GeoLite2):** Free
- **ClamAV (self-hosted):** $0 (Docker container)
- **PagerDuty (optional):** $25-100/user/month
- **Total Phase 2 Addition:** $5-35/month (+ optional PagerDuty)

**LLM Costs:** No change from Phase 1 (200 EUR/month)

**Total Estimated (Phase 1 + Phase 2):** $80-235/month (excluding LLM)

---

## Notes

- **Phase 2 Focus:** Authentication hardening, authorization, monitoring, validation
- **New Libraries:** 10+ new libraries for security features
- **External Services:** SMTP (required), Slack/PagerDuty (optional), S3/Azure (recommended)
- **Performance Impact:** <10ms additional latency with optimizations
- **Test Coverage:** 150+ new tests for Phase 2 features
- **Compliance:** SOC 2 Type 1 ready, ISO 27001 alignment, GDPR compliance
- **Deployment:** Zero-downtime deployment possible (no breaking changes)
