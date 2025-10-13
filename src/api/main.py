"""
API Entry Point

Run the FastAPI application with uvicorn.

Usage:
    python -m src.api.main

Or with uvicorn:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn
from .app import create_app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
