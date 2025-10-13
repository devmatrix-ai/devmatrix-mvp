"""
Pytest configuration for API tests.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.routers.workflows import workflows_db
from src.api.routers.executions import executions_db


@pytest.fixture(scope="function")
def app():
    """Create FastAPI application."""
    return create_app()


@pytest.fixture(scope="function")
async def client(app):
    """Create async test client with proper ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_databases():
    """Clear all databases before each test."""
    workflows_db.clear()
    executions_db.clear()
    yield
    workflows_db.clear()
    executions_db.clear()
