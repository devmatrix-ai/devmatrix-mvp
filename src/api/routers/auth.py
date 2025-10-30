"""
Authentication API Endpoints

Provides user registration, login, token refresh, user info endpoints,
email verification, and password reset functionality.

Extended with Task Group 2.3: Email Verification & Password Reset endpoints
Updated with Group 3: Token blacklist and logout functionality
Updated with Group 4: Audit logging for auth events
Updated with Phase 2 Task Group 2: Password Complexity Requirements (NIST-compliant)
Updated with Phase 2 Task Group 7: Auto-assign "user" role on registration
Updated with Phase 2 Task Group 9: 2FA/MFA Foundation (TOTP)
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr, Field

from src.services.auth_service import AuthService
from src.services.email_verification_service import EmailVerificationService
from src.services.password_reset_service import PasswordResetService
from src.services.password_validator import PasswordValidator
from src.services.session_service import SessionService
from src.services.rbac_service import RBACService
from src.services.totp_service import TOTPService
import jwt
from src.models.user import User
from src.api.middleware.auth_middleware import get_current_user, get_current_active_user, get_token_from_header
from src.config.constants import EMAIL_VERIFICATION_REQUIRED
from src.config.settings import get_settings
from src.config.database import get_db_context
from src.observability import get_logger
from src.observability.audit_logger import audit_logger

logger = get_logger("auth_router")
settings = get_settings()

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Initialize services
auth_service = AuthService()
email_verification_service = EmailVerificationService()
password_reset_service = PasswordResetService()
password_validator = PasswordValidator()
session_service = SessionService()
rbac_service = RBACService()
totp_service = TOTPService()


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=100)

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "password": "SecurePassword123!"
            }
        }


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str

    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class LogoutRequest(BaseModel):
    """Logout request (optional refresh token)"""
    refresh_token: Optional[str] = Field(None, description="Optional refresh token to blacklist")

    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Optional[dict] = None
    requires_2fa: Optional[bool] = Field(None, description="True if user has 2FA enabled and needs to complete 2FA flow")
    temp_token: Optional[str] = Field(None, description="Temporary token for completing 2FA flow (valid 5 minutes)")


class UserResponse(BaseModel):
    """User info response"""
    user_id: str
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: Optional[str]
    last_login_at: Optional[str]
    requires_password_update: Optional[bool] = Field(None, description="True if user has legacy password past grace period")
    totp_enabled: Optional[bool] = Field(None, description="True if user has 2FA enabled")


# Task 2.3.7: Pydantic models for new endpoints
class VerifyEmailRequest(BaseModel):
    """Email verification request"""
    token: str = Field(..., description="Email verification token UUID")

    class Config:
        schema_extra = {
            "example": {
                "token": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class VerifyEmailResponse(BaseModel):
    """Email verification response"""
    message: str
    user_id: str


class ResendVerificationResponse(BaseModel):
    """Resend verification response"""
    message: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ForgotPasswordResponse(BaseModel):
    """Forgot password response"""
    message: str


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str = Field(..., description="Password reset token UUID")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password (8+ characters)")

    class Config:
        schema_extra = {
            "example": {
                "token": "550e8400-e29b-41d4-a716-446655440000",
                "new_password": "NewSecurePassword123!"
            }
        }


class ResetPasswordResponse(BaseModel):
    """Reset password response"""
    message: str


# Phase 2 Task Group 9: 2FA/MFA Request/Response Models
class Enable2FAResponse(BaseModel):
    """2FA enrollment response"""
    qr_code: str = Field(..., description="Base64-encoded QR code image (data URI)")
    secret: str = Field(..., description="Base32-encoded TOTP secret (for manual entry)")
    backup_codes: List[str] = Field(..., description="6 single-use backup codes")


class Verify2FARequest(BaseModel):
    """2FA verification request"""
    code: str = Field(..., description="6-digit TOTP code or 8-character backup code")

    class Config:
        schema_extra = {
            "example": {
                "code": "123456"
            }
        }


class Verify2FAResponse(BaseModel):
    """2FA verification response"""
    message: str
    totp_enabled: bool


class Disable2FARequest(BaseModel):
    """Disable 2FA request"""
    password: str = Field(..., description="Current password for confirmation")

    class Config:
        schema_extra = {
            "example": {
                "password": "MyPassword123!"
            }
        }


class Disable2FAResponse(BaseModel):
    """Disable 2FA response"""
    message: str
    totp_enabled: bool


class BackupCodesResponse(BaseModel):
    """Backup codes response"""
    backup_codes: List[str] = Field(..., description="Remaining unused backup codes (hashed)")
    codes_count: int = Field(..., description="Number of remaining backup codes")


class RegenerateBackupCodesResponse(BaseModel):
    """Regenerate backup codes response"""
    backup_codes: List[str] = Field(..., description="6 new single-use backup codes")
    message: str


class Login2FARequest(BaseModel):
    """Complete 2FA login request"""
    temp_token: str = Field(..., description="Temporary token from initial login")
    code: str = Field(..., description="6-digit TOTP code or 8-character backup code")

    class Config:
        schema_extra = {
            "example": {
                "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "code": "123456"
            }
        }


# ============================================================================
# Existing Endpoints
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request_obj: RegisterRequest, request: Request):
    """
    Register new user account.

    Creates a new user with the provided credentials and returns access/refresh tokens.

    Task 2.3.6: Updated to support EMAIL_VERIFICATION_REQUIRED configuration.
    Task 4.8: Added audit logging for registration events.
    Phase 2 Task Group 2: Added NIST-compliant password validation.
    Phase 2 Task Group 7: Auto-assign "user" role on registration.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/register \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "user@example.com",
        "username": "john_doe",
        "password": "SecurePassword123!"
      }'
    ```

    **Returns**:
    - access_token: JWT access token (valid for 1 hour)
    - refresh_token: JWT refresh token (valid for 30 days)
    - user: User information

    **Errors**:
    - 400: Email or username already exists, or password validation failed
    - 422: Validation error (invalid email, weak password, etc.)
    """
    try:
        # Phase 2 Task Group 2: Validate password complexity
        validation_result = password_validator.validate(
            password=request_obj.password,
            user_inputs=[request_obj.email, request_obj.username]
        )

        if not validation_result["valid"]:
            logger.warning(
                f"Registration failed: Password validation errors for {request_obj.email}",
                extra={"errors": validation_result["errors"]}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Password does not meet security requirements",
                    "validation_errors": validation_result["errors"],
                    "password_strength": validation_result["feedback"]
                }
            )

        # Register user
        user = auth_service.register_user(
            email=request_obj.email,
            username=request_obj.username,
            password=request_obj.password
        )

        # Phase 2 Task Group 2: Set password_last_changed and legacy_password=False for new users
        with get_db_context() as db:
            db_user = db.query(User).filter(User.user_id == user.user_id).first()
            db_user.password_last_changed = datetime.utcnow()
            db_user.legacy_password = False  # New users meet current policy
            db.commit()
            db.refresh(db_user)

        # Phase 2 Task Group 7: Auto-assign "user" role to new registrations
        try:
            rbac_service.assign_role(
                user_id=user.user_id,
                role_name="user",
                assigned_by_user_id=None  # System assignment
            )
            logger.info(f"Auto-assigned 'user' role to new user: {user.user_id}")
        except Exception as e:
            # Log error but don't fail registration
            logger.error(f"Failed to auto-assign user role: {str(e)}", exc_info=True)

        # Task 2.3.6: Check EMAIL_VERIFICATION_REQUIRED config
        if EMAIL_VERIFICATION_REQUIRED:
            # Set user as unverified and generate verification token
            with get_db_context() as db:
                db_user = db.query(User).filter(User.user_id == user.user_id).first()
                db_user.is_verified = False
                db.commit()
                db.refresh(db_user)

            # Generate and send verification token
            token = email_verification_service.generate_verification_token(user.user_id)
            email_verification_service.send_verification_email(user.email, token, user.username)

            logger.info(f"User registered (verification required): {user.user_id} ({request_obj.email})")

            # Still generate tokens but notify about verification
            access_token = auth_service.create_access_token(
                user_id=user.user_id,
                email=user.email,
                username=user.username
            )
            refresh_token = auth_service.create_refresh_token(user_id=user.user_id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,  # 1 hour
                "user": {
                    **user.to_dict(),
                    "verification_required": True,
                    "message": "Please check your email to verify your account"
                }
            }
        else:
            # Email verification not required, user is automatically verified
            logger.info(f"User registered (no verification): {user.user_id} ({request_obj.email})")

            # Generate tokens
            access_token = auth_service.create_access_token(
                user_id=user.user_id,
                email=user.email,
                username=user.username
            )
            refresh_token = auth_service.create_refresh_token(user_id=user.user_id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,  # 1 hour
                "user": user.to_dict()
            }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest, request: Request):
    """
    Authenticate user and get tokens.

    Validates credentials and returns access/refresh tokens if successful.
    Task 4.8: Added audit logging for login events.
    Phase 2 Task Group 9: Extended to handle 2FA flow.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "user@example.com",
        "password": "SecurePassword123!"
      }'
    ```

    **Returns**:
    - If 2FA disabled: access_token, refresh_token, user
    - If 2FA enabled: requires_2fa=true, temp_token (valid 5 minutes)

    **Errors**:
    - 401: Invalid email or password
    - 403: Account is inactive or locked
    """
    try:
        tokens = auth_service.login(
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            email=login_request.email,
            password=login_request.password
        )

        # Extract user_id from tokens for audit logging
        user_id = None
        if tokens and tokens.get('user'):
            user_id = UUID(tokens['user']['user_id'])

        # Phase 2 Task Group 9: Check if user has 2FA enabled
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if user and user.has_2fa_enabled():
                # User has 2FA enabled - return temp token for 2FA completion
                logger.info(f"User {user_id} requires 2FA completion")

                # Create temporary token (valid 5 minutes)
                temp_token = auth_service.create_temp_2fa_token(
                    user_id=user_id,
                    email=user.email
                )

                return {
                    "access_token": "",
                    "refresh_token": None,
                    "token_type": "bearer",
                    "expires_in": 0,
                    "requires_2fa": True,
                    "temp_token": temp_token,
                    "user": None
                }

        # No 2FA - proceed with normal login
        # Log successful login
        await audit_logger.log_auth_event(
            user_id=user_id,
            action="auth.login",
            result="success",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"User logged in via API: {login_request.email}")

        # Phase 2 Task Group 4: Create session metadata in Redis
        if tokens and tokens.get('access_token'):
            try:
                access_payload = jwt.decode(
                    tokens['access_token'],
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                jti = access_payload.get('jti')
                iat = access_payload.get('iat')

                if jti and iat and user_id:
                    issued_at = datetime.utcfromtimestamp(iat)
                    session_created = session_service.create_session(
                        user_id=user_id,
                        token_jti=jti,
                        issued_at=issued_at
                    )

                    if session_created:
                        logger.debug(f"Session created for user {user_id}")
                    else:
                        logger.warning(f"Failed to create session for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create session metadata: {str(e)}")
                # Don't fail login if session creation fails

        return tokens

    except HTTPException as e:
        # Phase 2 Task Group 3: Account lockout (403) - re-raise without additional logging
        # (already logged by AccountLockoutService)
        logger.warning(f"Login blocked: {e.detail}")
        raise

    except ValueError as e:
        # Log failed login
        await audit_logger.log_auth_event(
            user_id=None,  # Unknown user
            action="auth.login_failed",
            result="denied",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.warning(f"Login failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/login/2fa", response_model=TokenResponse)
async def login_2fa(login_2fa_request: Login2FARequest, request: Request):
    """
    Complete 2FA login flow.

    Verifies TOTP code (or backup code) and returns full access/refresh tokens.
    Phase 2 Task Group 9: 2FA/MFA Foundation.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/login/2fa \\
      -H "Content-Type: application/json" \\
      -d '{
        "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "code": "123456"
      }'
    ```

    **Returns**:
    - access_token: JWT access token (valid for 1 hour)
    - refresh_token: JWT refresh token (valid for 30 days)
    - user: User information

    **Errors**:
    - 401: Invalid temp token, expired temp token, or invalid 2FA code
    - 429: Rate limited (max 3 attempts per minute)
    """
    try:
        # Decode temp token
        try:
            temp_payload = jwt.decode(
                login_2fa_request.temp_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            logger.warning("2FA login failed: Temp token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA session expired. Please log in again."
            )
        except jwt.InvalidTokenError:
            logger.warning("2FA login failed: Invalid temp token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA session token"
            )

        user_id = UUID(temp_payload.get("user_id"))
        user_email = temp_payload.get("email")
        token_type = temp_payload.get("type")

        # Verify temp token is for 2FA
        if token_type != "2fa_temp":
            logger.warning(f"2FA login failed: Invalid token type {token_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Rate limiting check
        if not totp_service.check_rate_limit(user_id):
            logger.warning(f"2FA login rate limited for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many 2FA attempts. Please wait 1 minute and try again."
            )

        # Get user from database
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user or not user.has_2fa_enabled():
                logger.warning(f"2FA login failed: User {user_id} does not have 2FA enabled")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="2FA not enabled for this account"
                )

            # Decrypt TOTP secret
            decrypted_secret = totp_service.decrypt_secret(user.totp_secret)

            # Verify TOTP code
            is_valid_totp = totp_service.verify_totp(decrypted_secret, login_2fa_request.code)

            if is_valid_totp:
                logger.info(f"2FA login successful with TOTP code for user {user_id}")
            else:
                # Try backup code
                if user.totp_backup_codes:
                    is_valid_backup, remaining_codes = totp_service.verify_backup_code(
                        login_2fa_request.code,
                        user.totp_backup_codes
                    )

                    if is_valid_backup:
                        # Update backup codes in database
                        user.totp_backup_codes = remaining_codes
                        db.commit()
                        logger.info(f"2FA login successful with backup code for user {user_id} ({len(remaining_codes)} codes remaining)")
                    else:
                        logger.warning(f"2FA login failed: Invalid code for user {user_id}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid 2FA code"
                        )
                else:
                    logger.warning(f"2FA login failed: Invalid TOTP code for user {user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid 2FA code"
                    )

        # 2FA verification successful - generate full tokens
        access_token = auth_service.create_access_token(
            user_id=user_id,
            email=user_email,
            username=user.username
        )
        refresh_token = auth_service.create_refresh_token(user_id=user_id)

        # Create session metadata
        try:
            access_payload = jwt.decode(
                access_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            jti = access_payload.get('jti')
            iat = access_payload.get('iat')

            if jti and iat:
                issued_at = datetime.utcfromtimestamp(iat)
                session_service.create_session(
                    user_id=user_id,
                    token_jti=jti,
                    issued_at=issued_at
                )
        except Exception as e:
            logger.error(f"Failed to create session metadata: {str(e)}")

        # Log successful 2FA login
        await audit_logger.log_auth_event(
            user_id=user_id,
            action="auth.2fa_login",
            result="success",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"2FA login completed successfully for user {user_id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour
            "user": user.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest, request: Request):
    """
    Refresh access token.

    Generates a new access token from a valid refresh token.
    Task 4.8: Added audit logging for token refresh events.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/refresh \\
      -H "Content-Type: application/json" \\
      -d '{
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      }'
    ```

    **Returns**:
    - access_token: New JWT access token (valid for 1 hour)

    **Errors**:
    - 401: Invalid or expired refresh token
    - 403: Account is inactive
    """
    try:
        tokens = auth_service.refresh_access_token(refresh_request.refresh_token)

        # Extract user_id from tokens for audit logging
        user_id = None
        if tokens and tokens.get('user'):
            user_id = UUID(tokens['user']['user_id'])

        # Log token refresh
        await audit_logger.log_auth_event(
            user_id=user_id,
            action="auth.token_refresh",
            result="success",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info("Access token refreshed via API")
        return tokens

    except ValueError as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.

    Returns information about the currently logged-in user.
    Phase 2 Task Group 2: Added legacy password warning.
    Phase 2 Task Group 9: Added 2FA status.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/auth/me \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - user_id: User UUID
    - email: Email address
    - username: Username
    - is_active: Account status
    - is_superuser: Admin privileges flag
    - is_verified: Email verification status
    - created_at: Registration date
    - last_login_at: Last login timestamp
    - requires_password_update: True if user has legacy password past grace period (30 days)
    - totp_enabled: True if user has 2FA enabled

    **Errors**:
    - 401: Missing or invalid token
    - 403: Account is inactive
    """
    logger.debug(f"User info requested: {current_user.user_id}")

    # Phase 2 Task Group 2: Check for legacy password warning
    requires_password_update = False
    if current_user.legacy_password and current_user.password_last_changed:
        # Grace period is 30 days
        grace_period_days = 30
        days_since_change = (datetime.utcnow() - current_user.password_last_changed).days
        if days_since_change > grace_period_days:
            requires_password_update = True

    user_dict = current_user.to_dict()
    user_dict["requires_password_update"] = requires_password_update
    user_dict["totp_enabled"] = current_user.has_2fa_enabled()

    return user_dict


@router.post("/logout")
async def logout(
    request: Request,
    logout_request: Optional[LogoutRequest] = None,
    access_token: str = Depends(get_token_from_header),
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user and blacklist tokens.

    Group 3 Security Update: Now implements token blacklisting.
    Task 4.8: Added audit logging for logout events.
    - Blacklists the current access token (required)
    - Optionally blacklists refresh token if provided in request body

    **Example**:
    ```bash
    # Logout with access token only
    curl -X POST http://localhost:8000/api/v1/auth/logout \\
      -H "Authorization: Bearer <access_token>"

    # Logout with both tokens
    curl -X POST http://localhost:8000/api/v1/auth/logout \\
      -H "Authorization: Bearer <access_token>" \\
      -H "Content-Type: application/json" \\
      -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
    ```

    **Returns**:
    - message: Logout confirmation
    - blacklisted_tokens: List of token types blacklisted

    **Errors**:
    - 401: Missing or invalid token
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    blacklisted_tokens = []

    # Blacklist access token (required)
    success = auth_service.blacklist_token(access_token, token_type="access", correlation_id=correlation_id)
    if success:
        blacklisted_tokens.append("access")
        logger.info(
            f"Access token blacklisted for user: {current_user.user_id}",
            extra={"correlation_id": correlation_id}
        )

    # Blacklist refresh token if provided (optional)
    if logout_request and logout_request.refresh_token:
        success = auth_service.blacklist_token(
            logout_request.refresh_token,
            token_type="refresh",
            correlation_id=correlation_id
        )
        if success:
            blacklisted_tokens.append("refresh")
            logger.info(
                f"Refresh token blacklisted for user: {current_user.user_id}",
                extra={"correlation_id": correlation_id}
            )


    # Phase 2 Task Group 4: Delete Redis session metadata
    try:
        access_payload = jwt.decode(
            access_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        jti = access_payload.get('jti')

        if jti:
            session_deleted = session_service.delete_session(
                user_id=current_user.user_id,
                token_jti=jti
            )

            if session_deleted:
                logger.info(f"Session deleted for user {current_user.user_id}")
            else:
                logger.debug(f"Session not found or already deleted for user {current_user.user_id}")
    except Exception as e:
        logger.error(f"Failed to delete session metadata: {str(e)}")
        # Don't fail logout if session deletion fails

    # Log logout event
    await audit_logger.log_auth_event(
        user_id=current_user.user_id,
        action="auth.logout",
        result="success",
        ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=correlation_id
    )

    logger.info(
        f"User logged out: {current_user.user_id}",
        extra={"correlation_id": correlation_id}
    )

    return {
        "message": "Successfully logged out",
        "blacklisted_tokens": blacklisted_tokens
    }




class KeepAliveResponse(BaseModel):
    """Keep-alive response"""
    success: bool
    extended_until: str


@router.post("/session/keep-alive", response_model=KeepAliveResponse)
async def keep_alive_session(
    request: Request,
    access_token: str = Depends(get_token_from_header),
    current_user: User = Depends(get_current_active_user)
):
    """
    Extend session idle timeout (keep-alive).

    Resets the session idle timer to 30 minutes from now.
    Phase 2 Task Group 4: Session Timeout Management.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/session/keep-alive \
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - success: True if session extended
    - extended_until: ISO timestamp when session will expire

    **Errors**:
    - 401: Missing or invalid token
    - 400: Failed to extend session
    """
    try:
        # Decode access token to get jti
        access_payload = jwt.decode(
            access_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        jti = access_payload.get('jti')

        if not jti:
            logger.warning(f"Keep-alive failed: Token missing jti for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token format"
            )

        # Extend session
        extended_until = session_service.extend_session(
            user_id=current_user.user_id,
            token_jti=jti
        )

        if not extended_until:
            logger.warning(f"Keep-alive failed: Could not extend session for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extend session. Session may have expired."
            )

        logger.debug(f"Session extended for user {current_user.user_id} until {extended_until}")

        return KeepAliveResponse(
            success=True,
            extended_until=extended_until.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Keep-alive failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend session"
        )

# ============================================================================
# Task 2.3: New Email Verification & Password Reset Endpoints
# ============================================================================

@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(request: VerifyEmailRequest):
    """
    Verify user email with token.

    Task 2.3.2: Email verification endpoint.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/verify-email \\
      -H "Content-Type: application/json" \\
      -d '{
        "token": "550e8400-e29b-41d4-a716-446655440000"
      }'
    ```

    **Returns**:
    - message: Success message
    - user_id: Verified user's UUID

    **Errors**:
    - 400: Invalid or expired token
    """
    try:
        # Convert string to UUID
        token_uuid = UUID(request.token)

        # Verify email (returns tuple of success, user_id)
        success, user_id = email_verification_service.verify_email(token_uuid)

        if not success:
            logger.warning(f"Email verification failed for token: {request.token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid or expired verification token"}
            )

        logger.info(f"Email verified successfully for user: {user_id}")

        return VerifyEmailResponse(
            message="Email verified successfully",
            user_id=str(user_id)
        )

    except ValueError as e:
        logger.warning(f"Email verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid token format"}
        )


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(current_user: User = Depends(get_current_active_user)):
    """
    Resend email verification.

    Task 2.3.3: Resend verification endpoint (requires authentication).

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/resend-verification \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - message: Success message

    **Errors**:
    - 400: User already verified
    - 401: Not authenticated
    - 429: Rate limited (handled by rate limiter in future task group)
    """
    try:
        # Attempt to resend verification
        email_verification_service.resend_verification(current_user.user_id)

        logger.info(f"Verification email resent for user: {current_user.user_id}")

        return ResendVerificationResponse(
            message="Verification email has been sent. Please check your inbox."
        )

    except ValueError as e:
        logger.warning(f"Resend verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)}
        )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset email.

    Task 2.3.4: Forgot password endpoint.

    Security: Always returns 200 to prevent email enumeration.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/forgot-password \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "user@example.com"
      }'
    ```

    **Returns**:
    - message: Generic success message (regardless of email existence)

    **Errors**:
    - None (always returns 200 for security)
    """
    # Request password reset (returns None if email doesn't exist)
    password_reset_service.request_password_reset(request.email)

    # Always return success to prevent email enumeration
    logger.info(f"Password reset requested for email: {request.email}")

    return ForgotPasswordResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password with token.

    Task 2.3.5: Reset password endpoint.
    Phase 2 Task Group 2: Added NIST-compliant password validation.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/reset-password \\
      -H "Content-Type: application/json" \\
      -d '{
        "token": "550e8400-e29b-41d4-a716-446655440000",
        "new_password": "NewSecurePassword123!"
      }'
    ```

    **Returns**:
    - message: Success message

    **Errors**:
    - 400: Invalid or expired token, or password validation failed
    - 422: Password validation error (less than 8 characters)
    """
    try:
        # Convert string to UUID
        token_uuid = UUID(request.token)

        # Phase 2 Task Group 2: Get user info from token first to validate password
        with get_db_context() as db:
            user = db.query(User).filter(
                User.password_reset_token == token_uuid,
                User.password_reset_expires > datetime.utcnow()
            ).first()

            if not user:
                logger.warning(f"Password reset failed: Invalid or expired token {request.token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "Invalid or expired reset token"}
                )

            # Validate password complexity
            validation_result = password_validator.validate(
                password=request.new_password,
                user_inputs=[user.email, user.username]
            )

            if not validation_result["valid"]:
                logger.warning(
                    f"Password reset failed: Password validation errors for user {user.user_id}",
                    extra={"errors": validation_result["errors"]}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Password does not meet security requirements",
                        "validation_errors": validation_result["errors"],
                        "password_strength": validation_result["feedback"]
                    }
                )

        # Reset password
        success = password_reset_service.reset_password(token_uuid, request.new_password)

        if not success:
            logger.warning(f"Password reset failed for token: {request.token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid or expired reset token"}
            )

        # Phase 2 Task Group 2: Update password_last_changed and clear legacy_password flag
        with get_db_context() as db:
            user = db.query(User).filter(User.password_reset_token == token_uuid).first()
            if user:
                user.password_last_changed = datetime.utcnow()
                user.legacy_password = False  # Password now meets current policy
                db.commit()

        logger.info(f"Password reset successful for token: {request.token}")

        return ResetPasswordResponse(
            message="Password has been reset successfully. You can now login with your new password."
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid token format"}
        )


# ============================================================================
# Phase 2 Task Group 9: 2FA/MFA Endpoints
# ============================================================================

@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(current_user: User = Depends(get_current_active_user)):
    """
    Start 2FA enrollment and generate QR code.

    Phase 2 Task Group 9: 2FA/MFA Foundation (TOTP).

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/2fa/enable \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - qr_code: Base64-encoded QR code image (data URI) for authenticator app
    - secret: Base32-encoded TOTP secret (for manual entry)
    - backup_codes: 6 single-use backup codes (store securely)

    **Errors**:
    - 400: 2FA already enabled
    - 401: Not authenticated
    """
    try:
        # Check if 2FA already enabled
        if current_user.has_2fa_enabled():
            logger.warning(f"2FA enable failed: Already enabled for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is already enabled for this account"
            )

        # Generate TOTP secret
        secret = totp_service.generate_secret()

        # Generate QR code
        qr_code = totp_service.generate_qr_code(secret, current_user.email)

        # Generate backup codes
        backup_codes = totp_service.generate_backup_codes()
        hashed_backup_codes = totp_service.hash_backup_codes(backup_codes)

        # Encrypt secret before storage
        encrypted_secret = totp_service.encrypt_secret(secret)

        # Store encrypted secret and hashed backup codes in database (NOT YET ENABLED)
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == current_user.user_id).first()
            user.totp_secret = encrypted_secret
            user.totp_backup_codes = hashed_backup_codes
            # Don't enable yet - wait for verification
            user.totp_enabled = False
            db.commit()

        logger.info(f"2FA enrollment started for user {current_user.user_id}")

        return Enable2FAResponse(
            qr_code=qr_code,
            secret=secret,  # Return plain secret for manual entry
            backup_codes=backup_codes  # Return plain backup codes for user to store
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA enable failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA"
        )


@router.post("/2fa/verify", response_model=Verify2FAResponse)
async def verify_2fa(
    verify_request: Verify2FARequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify TOTP code to complete 2FA enrollment.

    Phase 2 Task Group 9: 2FA/MFA Foundation (TOTP).

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/2fa/verify \\
      -H "Authorization: Bearer <access_token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "code": "123456"
      }'
    ```

    **Returns**:
    - message: Success message
    - totp_enabled: True (2FA now enabled)

    **Errors**:
    - 400: Invalid TOTP code or 2FA not initialized
    - 401: Not authenticated
    """
    try:
        # Check if user has initiated 2FA enrollment
        if not current_user.totp_secret:
            logger.warning(f"2FA verify failed: Not initialized for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA enrollment not started. Call /2fa/enable first."
            )

        # Check if already enabled
        if current_user.totp_enabled:
            logger.warning(f"2FA verify failed: Already enabled for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is already enabled"
            )

        # Decrypt secret
        decrypted_secret = totp_service.decrypt_secret(current_user.totp_secret)

        # Verify TOTP code
        is_valid = totp_service.verify_totp(decrypted_secret, verify_request.code)

        if not is_valid:
            logger.warning(f"2FA verify failed: Invalid code for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA code. Please try again."
            )

        # Enable 2FA
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == current_user.user_id).first()
            user.totp_enabled = True
            db.commit()

        logger.info(f"2FA enabled successfully for user {current_user.user_id}")

        return Verify2FAResponse(
            message="2FA has been enabled successfully",
            totp_enabled=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verify failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify 2FA code"
        )


@router.post("/2fa/disable", response_model=Disable2FAResponse)
async def disable_2fa(
    disable_request: Disable2FARequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Disable 2FA for current user (requires password confirmation).

    Phase 2 Task Group 9: 2FA/MFA Foundation (TOTP).

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/2fa/disable \\
      -H "Authorization: Bearer <access_token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "password": "MyPassword123!"
      }'
    ```

    **Returns**:
    - message: Success message
    - totp_enabled: False (2FA now disabled)

    **Errors**:
    - 400: 2FA not enabled, or incorrect password
    - 401: Not authenticated
    """
    try:
        # Check if 2FA is enabled
        if not current_user.has_2fa_enabled():
            logger.warning(f"2FA disable failed: Not enabled for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled for this account"
            )

        # Verify password
        try:
            auth_service.authenticate_user(current_user.email, disable_request.password)
        except ValueError:
            logger.warning(f"2FA disable failed: Incorrect password for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

        # Disable 2FA
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == current_user.user_id).first()
            user.totp_enabled = False
            user.totp_secret = None
            user.totp_backup_codes = None
            db.commit()

        logger.info(f"2FA disabled for user {current_user.user_id}")

        return Disable2FAResponse(
            message="2FA has been disabled successfully",
            totp_enabled=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA disable failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA"
        )


@router.get("/2fa/backup-codes", response_model=BackupCodesResponse)
async def get_backup_codes(current_user: User = Depends(get_current_active_user)):
    """
    Get remaining unused backup codes.

    Phase 2 Task Group 9: 2FA/MFA Foundation (TOTP).

    Note: Returns hashed codes (for display purposes only, cannot be used).
    User must regenerate codes if they lose them.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/auth/2fa/backup-codes \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - backup_codes: List of remaining backup codes (hashed, display only)
    - codes_count: Number of remaining backup codes

    **Errors**:
    - 400: 2FA not enabled
    - 401: Not authenticated
    """
    try:
        # Check if 2FA is enabled
        if not current_user.has_2fa_enabled():
            logger.warning(f"Get backup codes failed: 2FA not enabled for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled for this account"
            )

        # Get backup codes
        backup_codes = current_user.totp_backup_codes or []

        logger.debug(f"Retrieved {len(backup_codes)} backup codes for user {current_user.user_id}")

        return BackupCodesResponse(
            backup_codes=backup_codes,
            codes_count=len(backup_codes)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get backup codes failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve backup codes"
        )


@router.post("/2fa/regenerate-backup-codes", response_model=RegenerateBackupCodesResponse)
async def regenerate_backup_codes(
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate new backup codes (invalidates old ones).

    Phase 2 Task Group 9: 2FA/MFA Foundation (TOTP).

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/2fa/regenerate-backup-codes \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - backup_codes: 6 new single-use backup codes (store securely)
    - message: Success message

    **Errors**:
    - 400: 2FA not enabled
    - 401: Not authenticated
    """
    try:
        # Check if 2FA is enabled
        if not current_user.has_2fa_enabled():
            logger.warning(f"Regenerate backup codes failed: 2FA not enabled for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled for this account"
            )

        # Generate new backup codes
        backup_codes = totp_service.generate_backup_codes()
        hashed_backup_codes = totp_service.hash_backup_codes(backup_codes)

        # Update database
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == current_user.user_id).first()
            user.totp_backup_codes = hashed_backup_codes
            db.commit()

        logger.info(f"Backup codes regenerated for user {current_user.user_id}")

        return RegenerateBackupCodesResponse(
            backup_codes=backup_codes,
            message="New backup codes generated successfully. Store them securely."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regenerate backup codes failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def auth_health():
    """
    Health check for authentication service.

    **Example**:
    ```bash
    curl http://localhost:8000/api/v1/auth/health
    ```

    **Returns**:
    - status: Service status
    - message: Status message
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "message": "Authentication service is operational",
        "email_verification_required": EMAIL_VERIFICATION_REQUIRED,
        "password_min_length": settings.PASSWORD_MIN_LENGTH,
        "password_max_length": settings.PASSWORD_MAX_LENGTH,
        "2fa_available": True
    }
