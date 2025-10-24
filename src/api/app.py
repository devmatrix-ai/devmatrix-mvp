"""
FastAPI Application Factory

Creates and configures the FastAPI application with all routes and middleware.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..observability import StructuredLogger, HealthCheck, MetricsMiddleware, setup_logging
from ..observability.global_metrics import metrics_collector
from .routers import workflows, executions, metrics, health, websocket, rag, chat, masterplans, auth, usage, admin, validation, execution_v2, atomization, dependency, review


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

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware (must be before other middleware)
    # DISABLED FOR E2E TESTING - Re-enable for production
    # from ..api.middleware.rate_limit_middleware import RateLimitMiddleware
    # app.add_middleware(RateLimitMiddleware)

    # Add metrics middleware
    app.add_middleware(MetricsMiddleware, metrics_collector=metrics_collector)

    # Include routers
    app.include_router(auth.router)  # Authentication (includes /api/v1 prefix)
    app.include_router(usage.router)  # Usage & Quotas (includes /api/v1 prefix)
    app.include_router(admin.router)  # Admin (includes /api/v1 prefix)
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

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
            },
        )

    return app
