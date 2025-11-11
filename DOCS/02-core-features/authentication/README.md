# Authentication & Multi-Tenancy System - Complete Guide

This document provides a comprehensive overview of the authentication and multi-tenancy system implemented in Devmatrix MVP.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [API Endpoints](#api-endpoints)
5. [Database Schema](#database-schema)
6. [Security](#security)
7. [Testing](#testing)
8. [Configuration](#configuration)
9. [Usage Examples](#usage-examples)

## Overview

The authentication system provides enterprise-grade user management, authentication, and multi-tenancy capabilities:

- **JWT-based authentication** with access and refresh tokens
- **Email verification** for new user accounts
- **Password reset** with secure token-based flow
- **Multi-tenant data isolation** at the user level
- **Usage tracking and quotas** for resource management
- **Admin features** for user and quota management
- **Rate limiting** to prevent API abuse

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Middleware:                                                 │
│  - CORS                                                      │
│  - Rate Limiting (Redis-backed)                              │
│  - Metrics Collection                                        │
├─────────────────────────────────────────────────────────────┤
│  Routers:                                                    │
│  - /api/v1/auth      (Authentication)                        │
│  - /api/v1/admin     (Admin Management)                      │
│  - /api/v1/usage     (Usage & Quotas)                        │
├─────────────────────────────────────────────────────────────┤
│  Services:                                                   │
│  - AuthService               (JWT & Auth)                    │
│  - EmailService              (SMTP)                          │
│  - EmailVerificationService  (Verification)                  │
│  - PasswordResetService      (Reset)                         │
│  - TenancyService            (Multi-tenant)                  │
│  - UsageTrackingService      (Quotas)                        │
│  - AdminService              (Management)                    │
├─────────────────────────────────────────────────────────────┤
│  Database:                                                   │
│  - PostgreSQL (Users, Quotas, Usage, Conversations)          │
│  - Redis (Rate Limiting)                                     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Registration Flow**:
   ```
   User → POST /api/v1/auth/register
        → AuthService.register_user()
        → EmailVerificationService.send_verification_email()
        → Response with JWT tokens
   ```

2. **Login Flow**:
   ```
   User → POST /api/v1/auth/login
        → AuthService.login()
        → Verify credentials
        → Update last_login_at
        → Generate JWT tokens
        → Response with tokens + user info
   ```

3. **Protected Endpoint Flow**:
   ```
   User → Request with Bearer token
        → RateLimitMiddleware (check rate limit)
        → get_current_user() (verify JWT)
        → Store user in request.state
        → Execute endpoint
        → Response with rate limit headers
   ```

## Features

### 1. Authentication

#### User Registration
- Email and username uniqueness validation
- Password strength validation (min 8 chars)
- Bcrypt password hashing
- Optional email verification
- Automatic JWT token generation

#### Login
- Email + password authentication
- JWT access token (1 hour expiry)
- JWT refresh token (30 days expiry)
- Last login timestamp tracking
- Account status validation

#### Token Management
- Stateless JWT tokens
- Token type validation (access vs refresh)
- Automatic expiry handling
- Secure token refresh flow

### 2. Email Verification

- UUID-based verification tokens
- 24-hour token expiry
- Resend verification capability
- HTML email templates
- Production SMTP support
- Development console logging

### 3. Password Reset

- Secure token-based flow
- 1-hour token expiry
- Email enumeration protection (always returns 200)
- Password validation on reset
- Token cleanup after use

### 4. Multi-Tenancy

- User-level data isolation
- Automatic query scoping
- Ownership verification
- CASCADE delete for data cleanup
- Security best practices (404 instead of 403)

See [MULTI_TENANCY.md](./MULTI_TENANCY.md) for detailed documentation.

### 5. Usage Tracking

- LLM token consumption tracking
- Accurate cost calculation (USD and EUR)
- Prompt caching support (90% cost reduction)
- Monthly usage aggregation
- Resource usage tracking (masterplans, storage, API calls)

### 6. Quota Management

- Per-user quota limits:
  - Monthly LLM tokens
  - Masterplans count
  - Storage bytes
  - API calls per minute
- Quota enforcement before operations
- Unlimited defaults (null values)

### 7. Admin Features

- User management (list, view, update, delete)
- Quota management (set, update, remove)
- System statistics
- Top users by usage
- Superuser-only access

### 8. Rate Limiting

- Redis-based sliding window algorithm
- Per-user limits based on quotas
- Default: 30 req/min (authenticated), 10 req/min (unauthenticated)
- Rate limit headers in responses
- Fail-open on Redis failure

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login user | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No |
| GET | `/api/v1/auth/me` | Get current user info | Yes |
| POST | `/api/v1/auth/logout` | Logout user | Yes |
| POST | `/api/v1/auth/verify-email` | Verify email | No |
| POST | `/api/v1/auth/resend-verification` | Resend verification | Yes |
| POST | `/api/v1/auth/forgot-password` | Request password reset | No |
| POST | `/api/v1/auth/reset-password` | Reset password | No |
| GET | `/api/v1/auth/health` | Health check | No |

### Usage & Quota Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/usage/current` | Get current month usage | Yes |
| GET | `/api/v1/usage/quota` | Get user quota | Yes |
| GET | `/api/v1/usage/status` | Get quota status with warnings | Yes |
| GET | `/api/v1/usage/history` | Get usage history | Yes |

### Admin Endpoints (Superuser Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/users/{id}` | Get user details |
| PATCH | `/api/v1/admin/users/{id}/status` | Update user status |
| DELETE | `/api/v1/admin/users/{id}` | Delete user |
| PUT | `/api/v1/admin/users/{id}/quota` | Set user quota |
| DELETE | `/api/v1/admin/users/{id}/quota` | Remove quota |
| GET | `/api/v1/admin/stats` | System statistics |
| GET | `/api/v1/admin/stats/top-users` | Top users by usage |

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT TRUE,
    verification_token UUID,
    verification_token_created_at TIMESTAMP,
    password_reset_token UUID,
    password_reset_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);
```

### User Quotas Table

```sql
CREATE TABLE user_quotas (
    quota_id UUID PRIMARY KEY,
    user_id UUID UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    llm_tokens_monthly_limit INTEGER,
    masterplans_limit INTEGER,
    storage_bytes_limit BIGINT,
    api_calls_per_minute INTEGER DEFAULT 30
);
```

### User Usage Table

```sql
CREATE TABLE user_usage (
    usage_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    month DATE NOT NULL,
    llm_tokens_used INTEGER DEFAULT 0,
    llm_cost_usd NUMERIC(10, 4) DEFAULT 0.0,
    masterplans_created INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    UNIQUE(user_id, month)
);
```

## Security

### Password Security

- **Bcrypt hashing** with automatic salt generation
- **Minimum 8 characters** password requirement
- **Password complexity** validation (via Pydantic)
- **No password in responses** (excluded from to_dict())

### Token Security

- **HS256 algorithm** for JWT signing
- **Short-lived access tokens** (1 hour)
- **Long-lived refresh tokens** (30 days)
- **Token type validation** (access vs refresh)
- **Stateless authentication** (no session storage)

### API Security

- **Bearer token authentication**
- **Rate limiting** to prevent brute force
- **CORS configuration** for web clients
- **Input validation** via Pydantic models
- **SQL injection protection** via SQLAlchemy ORM

### Multi-Tenancy Security

- **Automatic query scoping** by user_id
- **Ownership verification** before access
- **404 responses** to hide resource existence
- **CASCADE delete** for data cleanup
- **Audit logging** of unauthorized attempts

## Testing

### Unit Tests (tests/unit/test_auth_service.py)

- Password hashing and verification
- User registration (success, duplicates)
- Token generation and validation
- Login (success, failures, inactive users)
- Token refresh
- Current user retrieval

### Integration Tests (tests/integration/test_auth_api.py)

- All API endpoints
- Full request-response cycles
- Authentication flows
- Email verification workflow
- Password reset workflow
- Error handling and status codes

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_auth_service.py

# Run specific test
pytest tests/unit/test_auth_service.py::TestAuthService::test_login_success
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production-IMPORTANT
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Email Verification
EMAIL_VERIFICATION_REQUIRED=false
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS=24

# Email Service
EMAIL_ENABLED=false
EMAIL_FROM_ADDRESS=noreply@devmatrix.local
EMAIL_FROM_NAME=Devmatrix

# SMTP Configuration (if EMAIL_ENABLED=true)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
SMTP_USE_SSL=false

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:5173

# Redis (for rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Usage Examples

### Registration

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "john_doe",
    "password": "SecurePassword123!"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### Get Current User

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Get Usage Stats

```bash
curl -X GET http://localhost:8000/api/v1/usage/current \
  -H "Authorization: Bearer <access_token>"
```

### Admin: List Users

```bash
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer <superuser_token>"
```

### Admin: Set User Quota

```bash
curl -X PUT http://localhost:8000/api/v1/admin/users/<user_id>/quota \
  -H "Authorization: Bearer <superuser_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_tokens_monthly_limit": 1000000,
    "masterplans_limit": 10,
    "api_calls_per_minute": 60
  }'
```

## Production Deployment

### Checklist

- [ ] Change `JWT_SECRET_KEY` to a strong random value
- [ ] Set `EMAIL_ENABLED=true` and configure SMTP
- [ ] Configure Redis for distributed rate limiting
- [ ] Set appropriate CORS origins (not `*`)
- [ ] Enable HTTPS (required for secure cookies)
- [ ] Set `EMAIL_VERIFICATION_REQUIRED=true` for production
- [ ] Configure database backups
- [ ] Set up monitoring and logging
- [ ] Review and set appropriate quota defaults
- [ ] Test email delivery
- [ ] Create first superuser account

### Creating First Superuser

```python
from src.services.auth_service import AuthService
from src.config.database import get_db_context
from src.models.user import User

# Register user
auth = AuthService()
user = auth.register_user(
    email="admin@yourdomain.com",
    username="admin",
    password="strong-password-here"
)

# Make superuser
with get_db_context() as db:
    db_user = db.query(User).filter(User.user_id == user.user_id).first()
    db_user.is_superuser = True
    db.commit()
```

## Troubleshooting

### Email Not Sending

- Check `EMAIL_ENABLED=true` in .env
- Verify SMTP credentials
- Check SMTP port and TLS settings
- Review logs for SMTP errors
- Test SMTP connection manually

### Rate Limiting Not Working

- Verify Redis is running (`redis-cli ping`)
- Check Redis connection in logs
- System falls back to allowing all requests if Redis fails

### Token Expired Errors

- Access tokens expire after 1 hour (configurable)
- Use refresh token to get new access token
- Check system clock is synchronized (NTP)

### Multi-Tenancy Issues

- Always use `TenancyService` for queries
- Never trust client-provided user IDs
- Check ownership before allowing access
- Review audit logs for unauthorized attempts

## Summary

The authentication and multi-tenancy system provides a robust foundation for the Devmatrix MVP:

- ✅ Secure JWT-based authentication
- ✅ Email verification and password reset
- ✅ Complete data isolation per user
- ✅ Usage tracking and quota enforcement
- ✅ Admin management capabilities
- ✅ Rate limiting for API protection
- ✅ Comprehensive test coverage
- ✅ Production-ready configuration

For more information, see:
- [Multi-Tenancy Guide](./MULTI_TENANCY.md)
- [API Documentation](http://localhost:8000/docs) (when server is running)
