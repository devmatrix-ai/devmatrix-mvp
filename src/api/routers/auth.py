"""
Authentication API Endpoints

Provides user registration, login, token refresh, user info endpoints,
email verification, and password reset functionality.

Extended with Task Group 2.3: Email Verification & Password Reset endpoints
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field

from src.services.auth_service import AuthService
from src.services.email_verification_service import EmailVerificationService
from src.services.password_reset_service import PasswordResetService
from src.models.user import User
from src.api.middleware.auth_middleware import get_current_user, get_current_active_user
from src.config.constants import EMAIL_VERIFICATION_REQUIRED
from src.observability import get_logger

logger = get_logger("auth_router")

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Initialize services
auth_service = AuthService()
email_verification_service = EmailVerificationService()
password_reset_service = PasswordResetService()


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


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Optional[dict] = None


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


# ============================================================================
# Existing Endpoints
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register new user account.

    Creates a new user with the provided credentials and returns access/refresh tokens.

    Task 2.3.6: Updated to support EMAIL_VERIFICATION_REQUIRED configuration.

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
    - 400: Email or username already exists
    - 422: Validation error (invalid email, weak password, etc.)
    """
    try:
        # Register user
        user = auth_service.register_user(
            email=request.email,
            username=request.username,
            password=request.password
        )

        # Task 2.3.6: Check EMAIL_VERIFICATION_REQUIRED config
        if EMAIL_VERIFICATION_REQUIRED:
            # Set user as unverified and generate verification token
            from src.config.database import get_db_context
            with get_db_context() as db:
                db_user = db.query(User).filter(User.user_id == user.user_id).first()
                db_user.is_verified = False
                db.commit()
                db.refresh(db_user)

            # Generate and send verification token
            token = email_verification_service.generate_verification_token(user.user_id)
            email_verification_service.send_verification_email(user.email, token, user.username)

            logger.info(f"User registered (verification required): {user.user_id} ({request.email})")

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
            logger.info(f"User registered (no verification): {user.user_id} ({request.email})")

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

    except ValueError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and get tokens.

    Validates credentials and returns access/refresh tokens if successful.

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
    - access_token: JWT access token (valid for 1 hour)
    - refresh_token: JWT refresh token (valid for 30 days)
    - user: User information

    **Errors**:
    - 401: Invalid email or password
    - 403: Account is inactive
    """
    try:
        tokens = auth_service.login(
            email=request.email,
            password=request.password
        )

        logger.info(f"User logged in via API: {request.email}")
        return tokens

    except ValueError as e:
        logger.warning(f"Login failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token.

    Generates a new access token from a valid refresh token.

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
        tokens = auth_service.refresh_access_token(request.refresh_token)

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
    - is_superuser: Admin flag
    - is_verified: Email verification status
    - created_at: Registration date
    - last_login_at: Last login timestamp

    **Errors**:
    - 401: Missing or invalid token
    - 403: Account is inactive
    """
    logger.debug(f"User info requested: {current_user.user_id}")
    return current_user.to_dict()


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.

    Note: Since we're using stateless JWT, this endpoint primarily serves
    as a confirmation. The client should delete the stored tokens.

    In production, you may want to implement token blacklisting.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/logout \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - message: Logout confirmation

    **Errors**:
    - 401: Missing or invalid token
    """
    logger.info(f"User logged out: {current_user.user_id}")
    return {"message": "Successfully logged out"}


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
    - 400: Invalid or expired token
    - 422: Password validation error (less than 8 characters)
    """
    try:
        # Convert string to UUID
        token_uuid = UUID(request.token)

        # Reset password
        success = password_reset_service.reset_password(token_uuid, request.new_password)

        if not success:
            logger.warning(f"Password reset failed for token: {request.token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid or expired reset token"}
            )

        logger.info(f"Password reset successful for token: {request.token}")

        return ResetPasswordResponse(
            message="Password has been reset successfully. You can now login with your new password."
        )

    except ValueError as e:
        logger.warning(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid token format"}
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
        "email_verification_required": EMAIL_VERIFICATION_REQUIRED
    }
