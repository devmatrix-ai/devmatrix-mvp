"""
FastAPI Application Factory

Creates and configures the FastAPI application with all routes and middleware.
Updated for Phase 1 Critical Security Vulnerabilities - Group 5: API Security Layer
Updated for Phase 2 Task Group 10: Resource Sharing & Collaboration
Updated for Phase 2 Task Group 12: Enhanced Audit Logging (Read Operations)
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
from pathlib import Path
import sys
import uuid

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from ..observability import StructuredLogger, HealthCheck, MetricsMiddleware, setup_logging
from ..observability.global_metrics import metrics_collector
from .routers import workflows, executions, metrics, health, websocket, rag, chat, masterplans, auth, usage, admin, validation, execution_v2, atomization, dependency, review, testing, conversations


# Initialize logging system
setup_logging()

# Global instances
logger = StructuredLogger("api", output_json=True)
health_check = HealthCheck()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting API application")

    # ========================================
    # Phase 1 Security: Configuration Validation
    # ========================================
    try:
        from ..config.settings import get_settings

        settings = get_settings()

        # Validate JWT_SECRET (fail-fast if invalid)
        settings.validate_jwt_secret()

        logger.info("Configuration validation passed")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"CORS origins configured: {len(settings.get_cors_origins_list())}")

    except ValidationError as e:
        logger.critical(f"CRITICAL: Configuration validation failed. {e}")
        logger.critical("Application cannot start without required environment variables.")
        logger.critical("Please check .env file and ensure JWT_SECRET and DATABASE_URL are set.")
        sys.exit(1)
    except ValueError as e:
        logger.critical(f"CRITICAL: Configuration validation failed. {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"CRITICAL: Unexpected error during startup validation. {e}")
        sys.exit(1)

    # Register health checks
    def system_health():
        from ..observability import ComponentHealth, HealthStatus
        return ComponentHealth(
            name="system",
            status=HealthStatus.HEALTHY,
            message="System operational"
        )

    health_check.register("system", system_health)

    yield

    # Shutdown
    logger.info("Shutting down API application")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Devmatrix API",
        description="REST API for AI-powered workflow orchestration",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ========================================
    # Phase 1 Security: Correlation ID Middleware
    # ========================================
    # This MUST run first to ensure correlation_id is available
    # in all subsequent middleware and handlers
    from .middleware.correlation_id_middleware import correlation_id_middleware
    app.middleware("http")(correlation_id_middleware)

    # ========================================
    # Phase 1 Security: CORS Configuration
    # ========================================
    # Load CORS origins from environment (not wildcard)
    from ..config.settings import get_settings

    try:
        settings = get_settings()
        allowed_origins = settings.get_cors_origins_list()

        # If no origins configured, use empty list (no CORS)
        # This is safer than wildcard
        if not allowed_origins:
            logger.warning("No CORS origins configured. CORS will be restrictive.")
            allowed_origins = []

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,  # Exact string matching only
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        logger.info(f"CORS configured with {len(allowed_origins)} allowed origins")
    except Exception as e:
        logger.error(f"Failed to configure CORS: {e}")
        # Continue with empty origins (restrictive CORS)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ========================================
    # Phase 1 Security: Rate Limiting Middleware
    # Group 5.3: Enable rate limiting with Redis backing
    # ========================================
    from .middleware.rate_limit_middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting middleware enabled")

    # ========================================
    # Phase 2 Task Group 12: Enhanced Audit Logging Middleware
    # ========================================
    # This MUST run AFTER auth middleware (to get user_id)
    # but BEFORE request processing
    from .middleware.audit_middleware import AuditMiddleware
    app.add_middleware(AuditMiddleware)
    logger.info("Enhanced audit logging middleware enabled (read operations)")

    # Add metrics middleware
    app.add_middleware(MetricsMiddleware, metrics_collector=metrics_collector)

    # Include routers
    app.include_router(auth.router)  # Authentication (includes /api/v1 prefix)
    app.include_router(usage.router)  # Usage & Quotas (includes /api/v1 prefix)
    app.include_router(admin.router)  # Admin (includes /api/v1 prefix)
    app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])  # Phase 2: Sharing
    app.include_router(workflows.router, prefix="/api/v1")
    app.include_router(executions.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(websocket.router, prefix="/api/v1")
    app.include_router(rag.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(masterplans.router)

    # MGE V2 Routers (all include /api/v2 prefix)
    app.include_router(atomization.router)  # Phase 2: Atomization
    app.include_router(dependency.router)  # Phase 3: Dependency Graph
    app.include_router(validation.router)  # Phase 4: Validation
    app.include_router(execution_v2.router)  # Phase 5: Execution
    app.include_router(review.router)  # Phase 6: Human Review
    app.include_router(testing.router)  # Phase 6 Week 12: Acceptance Testing

    # Mount Socket.IO app
    app.mount("/socket.io", websocket.sio_app)

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        # Mount assets directory at /assets (for Vite build)
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # Mount entire static dir at /static (fallback)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # Serve index.html at root
        from fastapi.responses import FileResponse

        @app.get("/", include_in_schema=False)
        async def serve_frontend():
            """Serve the web UI."""
            return FileResponse(str(static_dir / "index.html"))

    # API info endpoint
    @app.get("/api", tags=["root"])
    async def api_info() -> Dict[str, Any]:
        """API information endpoint."""
        return {
            "name": "Devmatrix API",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/api/v1/health",
            "ui": "/",
        }

    # ========================================
    # Phase 1 Security: Global Exception Handler
    # ========================================
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Global exception handler that converts all exceptions to ErrorResponse format.

        Exception Handling Strategy:
        1. HTTPException - Re-raise unchanged (already in correct format)
        2. SQLAlchemyError - Database errors (500)
        3. ValidationError - Input validation errors (400)
        4. Exception - Catch-all for unexpected errors (500)

        All errors include:
        - Correlation ID for tracing
        - Proper error codes
        - Stack traces in logs
        - X-Correlation-ID header
        """
        from .responses.error_response import ErrorResponse

        # Extract correlation_id from request state (set by middleware)
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))

        # Re-raise HTTPException unchanged (FastAPI handles these correctly)
        if isinstance(exc, HTTPException):
            # Log but don't wrap HTTPException
            logger.warning(
                f"HTTP exception: {exc.status_code} - {exc.detail}",
                extra={"correlation_id": correlation_id}
            )
            raise exc

        # Database errors
        if isinstance(exc, SQLAlchemyError):
            logger.error(
                f"Database error: {str(exc)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )

            error_response = ErrorResponse(
                code="DB_001",
                message="Database error occurred",
                details={"error_type": type(exc).__name__},
                correlation_id=correlation_id
            )

            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(),
                headers={"X-Correlation-ID": correlation_id}
            )

        # Validation errors
        if isinstance(exc, (ValidationError, ValueError)):
            logger.warning(
                f"Validation error: {str(exc)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )

            error_response = ErrorResponse(
                code="VAL_001",
                message="Invalid input",
                details={"error": str(exc)},
                correlation_id=correlation_id
            )

            return JSONResponse(
                status_code=400,
                content=error_response.model_dump(),
                headers={"X-Correlation-ID": correlation_id}
            )

        # Catch-all for unexpected errors
        logger.error(
            f"Unexpected error: {str(exc)}",
            exc_info=True,
            extra={"correlation_id": correlation_id}
        )

        error_response = ErrorResponse(
            code="SYS_001",
            message="Internal server error",
            details={"error_type": type(exc).__name__},
            correlation_id=correlation_id
        )

        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(),
            headers={"X-Correlation-ID": correlation_id}
        )

    return app
