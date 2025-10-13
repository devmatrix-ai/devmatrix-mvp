"""
FastAPI Application Factory

Creates and configures the FastAPI application with all routes and middleware.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..observability import StructuredLogger, MetricsCollector, HealthCheck
from .routers import workflows, executions, metrics, health


# Global instances
logger = StructuredLogger("api", output_json=True)
metrics_collector = MetricsCollector()
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

    # Include routers
    app.include_router(workflows.router, prefix="/api/v1")
    app.include_router(executions.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "name": "Devmatrix API",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/api/v1/health",
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
