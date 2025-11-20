"""
Security Headers Middleware

Adds security headers to all HTTP responses to protect against common attacks.
Implements OWASP A05:2021 Security Misconfiguration prevention.

Security Headers:
- X-Content-Type-Options: Prevent MIME sniffing
- X-Frame-Options: Prevent clickjacking
- X-XSS-Protection: Enable browser XSS protection
- Strict-Transport-Security (HSTS): Force HTTPS
- Content-Security-Policy (CSP): Prevent XSS and data injection
- Referrer-Policy: Control referrer information
- Permissions-Policy: Control browser features

Created for Task Group 5: Security Hardening - Task 5.5
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from fastapi import Request

from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("security_headers_middleware")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all HTTP responses.

    Implements defense-in-depth security strategy through HTTP headers.
    Headers are applied to all responses except WebSocket connections.
    """

    def __init__(self, app):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self.settings = get_settings()

        # Log security headers configuration
        logger.info("Security headers middleware initialized")
        logger.info(f"Environment: {self.settings.ENVIRONMENT}")

        if self.settings.ENVIRONMENT == "production":
            logger.info("HSTS enabled (production mode)")
        else:
            logger.info("HSTS disabled (development mode)")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Add security headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint

        Returns:
            Response with security headers added
        """
        # Process request
        response: Response = await call_next(request)

        # Skip WebSocket connections (no headers needed)
        if request.url.path.startswith("/socket.io"):
            return response

        # ==========================================================
        # 1. X-Content-Type-Options: nosniff
        # ==========================================================
        # Prevents MIME sniffing attacks
        # Forces browsers to respect declared Content-Type
        # OWASP: A05:2021 Security Misconfiguration
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ==========================================================
        # 2. X-Frame-Options: DENY
        # ==========================================================
        # Prevents clickjacking attacks
        # Disallows embedding page in <iframe>, <frame>, <object>
        # OWASP: A04:2021 Insecure Design
        response.headers["X-Frame-Options"] = "DENY"

        # ==========================================================
        # 3. X-XSS-Protection: 1; mode=block
        # ==========================================================
        # Enables browser's built-in XSS filter (legacy support)
        # Modern browsers use CSP, but this helps older browsers
        # OWASP: A03:2021 Injection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # ==========================================================
        # 4. Strict-Transport-Security (HSTS)
        # ==========================================================
        # Forces HTTPS connections for 1 year
        # Only enabled in production (requires valid HTTPS cert)
        # OWASP: A02:2021 Cryptographic Failures
        if self.settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ==========================================================
        # 5. Content-Security-Policy (CSP)
        # ==========================================================
        # Prevents XSS, data injection, and other code injection attacks
        # OWASP: A03:2021 Injection
        #
        # CSP Directives:
        # - default-src 'self': Only load resources from same origin
        # - script-src: Allow scripts from same origin + inline (needed for Vite)
        # - style-src: Allow styles from same origin + inline (needed for Vite)
        # - img-src: Allow images from same origin + data URIs + HTTPS
        # - font-src: Allow fonts from same origin + data URIs
        # - connect-src: Allow connections to same origin + WebSocket
        # - frame-ancestors 'none': Prevent embedding (redundant with X-Frame-Options)
        # - base-uri 'self': Prevent base tag injection
        # - form-action 'self': Only submit forms to same origin

        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # 'unsafe-inline' + 'unsafe-eval' needed for Vite dev
            "style-src 'self' 'unsafe-inline'",  # 'unsafe-inline' needed for Vite dev
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' ws: wss:",  # WebSocket support
            "frame-ancestors 'none'",  # Prevent embedding
            "base-uri 'self'",  # Prevent base tag injection
            "form-action 'self'",  # Only submit forms to same origin
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # ==========================================================
        # 6. Referrer-Policy
        # ==========================================================
        # Controls how much referrer information is sent
        # strict-origin-when-cross-origin: Full URL for same-origin, origin only for cross-origin
        # OWASP: A01:2021 Broken Access Control (information leakage)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ==========================================================
        # 7. Permissions-Policy (formerly Feature-Policy)
        # ==========================================================
        # Controls which browser features can be used
        # Disables geolocation, microphone, camera by default
        # OWASP: A05:2021 Security Misconfiguration
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()"
        ]

        response.headers["Permissions-Policy"] = ", ".join(permissions)

        # ==========================================================
        # 8. X-Permitted-Cross-Domain-Policies: none
        # ==========================================================
        # Prevents Adobe Flash and PDF from loading cross-domain content
        # Legacy protection but still useful
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # ==========================================================
        # 9. X-Download-Options: noopen
        # ==========================================================
        # Prevents IE from opening downloads in same security context
        # Legacy IE protection
        response.headers["X-Download-Options"] = "noopen"

        return response


def create_security_headers_middleware(app):
    """
    Factory function to create and add security headers middleware.

    Args:
        app: FastAPI application

    Returns:
        App with security headers middleware added

    Usage:
        app = FastAPI()
        app = create_security_headers_middleware(app)
    """
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware added to application")
    return app
