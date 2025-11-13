"""Task Manager FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.config import settings
from src.routers import api_router
from src.db import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Task Manager API",
    description="A comprehensive task management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def root():
    """Root endpoint."""
    return {
        "message": "Task Manager API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


# Include API router
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
