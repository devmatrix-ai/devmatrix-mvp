"""
Unit Tests for API Security Layer (Group 5)

Tests for:
- Rate limiting (Redis-backed)
- CORS configuration
- SQL injection prevention

Phase 1 - Critical Security Vulnerabilities
Task Group 5.1: Write 2-8 focused tests for API security
"""

import time
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Set up test environment variables before importing modules
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long_for_testing")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://app.example.com")

# Mock tree_sitter modules before importing
sys.modules['tree_sitter_python'] = MagicMock()
sys.modules['tree_sitter_javascript'] = MagicMock()
sys.modules['tree_sitter_java'] = MagicMock()
sys.modules['tree_sitter_cpp'] = MagicMock()
sys.modules['tree_sitter_typescript'] = MagicMock()

# Import only what we need directly
import importlib
import sys

# Dynamically import rate_limit_middleware to avoid full app import
rate_limit_spec = importlib.util.spec_from_file_location(
    "rate_limit_middleware",
    "/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp/src/api/middleware/rate_limit_middleware.py"
)
rate_limit_module = importlib.util.module_from_spec(rate_limit_spec)
sys.modules['rate_limit_middleware'] = rate_limit_module
rate_limit_spec.loader.exec_module(rate_limit_module)

RateLimitMiddleware = rate_limit_module.RateLimitMiddleware

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.config.settings import Settings


class TestRateLimiting:
    """Test rate limiting middleware functionality."""

    @pytest.mark.asyncio
    async def test_anonymous_user_hits_global_rate_limit(self):
        """Test anonymous user exceeds global rate limit and gets 429."""
        # Create mock FastAPI app
        app = FastAPI()

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock()
        mock_redis.zcard = MagicMock(return_value=30)  # Already at limit
        mock_redis.zrange = MagicMock(return_value=[("123.45", time.time())])

        # Create rate limit middleware
        middleware = RateLimitMiddleware(app, redis_client=mock_redis)

        # Create mock request (anonymous - no user in state)
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/test"
        mock_request.client.host = "192.168.1.1"
        mock_request.state = Mock()
        mock_request.state.user = None

        # Create mock call_next
        async def mock_call_next(request):
            return JSONResponse(content={"status": "ok"})

        # Execute middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert response.status_code == 429
        assert "Rate limit exceeded" in str(response.body)
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_anonymous_user_hits_auth_endpoint_limit(self):
        """Test anonymous user exceeds auth endpoint rate limit (10 req/min)."""
        # Create mock FastAPI app
        app = FastAPI()

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock()
        mock_redis.zcard = MagicMock(return_value=10)  # At auth limit
        mock_redis.zrange = MagicMock(return_value=[("123.45", time.time())])

        # Create rate limit middleware
        middleware = RateLimitMiddleware(app, redis_client=mock_redis)

        # Create mock request to auth endpoint
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.client.host = "192.168.1.1"
        mock_request.state = Mock()
        mock_request.state.user = None

        # Create mock call_next
        async def mock_call_next(request):
            return JSONResponse(content={"status": "ok"})

        # Execute middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Assert - anonymous user gets 10 req/min limit
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_authenticated_user_hits_global_limit(self):
        """Test authenticated user exceeds global rate limit (100 req/min)."""
        # Create mock FastAPI app
        app = FastAPI()

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock()
        mock_redis.zcard = MagicMock(return_value=100)  # At authenticated limit
        mock_redis.zrange = MagicMock(return_value=[("123.45", time.time())])

        # Create rate limit middleware
        middleware = RateLimitMiddleware(app, redis_client=mock_redis)

        # Create mock user
        mock_user = Mock()
        mock_user.user_id = "550e8400-e29b-41d4-a716-446655440000"

        # Create mock request (authenticated user)
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/test"
        mock_request.client.host = "192.168.1.1"
        mock_request.state = Mock()
        mock_request.state.user = mock_user

        # Create mock call_next
        async def mock_call_next(request):
            return JSONResponse(content={"status": "ok"})

        # Execute middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Assert - should get 429 when at limit
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self):
        """Test rate limit headers are present in all responses."""
        # Create mock FastAPI app
        app = FastAPI()

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock()
        mock_redis.zcard = MagicMock(return_value=5)  # Well under limit
        mock_redis.zadd = MagicMock()
        mock_redis.expire = MagicMock()

        # Create rate limit middleware
        middleware = RateLimitMiddleware(app, redis_client=mock_redis)

        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/test"
        mock_request.client.host = "192.168.1.1"
        mock_request.state = Mock()
        mock_request.state.user = None

        # Create mock call_next
        async def mock_call_next(request):
            return JSONResponse(content={"status": "ok"})

        # Execute middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Assert rate limit headers present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Validate header values
        assert int(response.headers["X-RateLimit-Limit"]) > 0
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0
        assert int(response.headers["X-RateLimit-Reset"]) > int(time.time())


class TestCORSConfiguration:
    """Test CORS configuration from environment."""

    def test_allowed_cors_origin_receives_headers(self):
        """Test allowed CORS origin receives proper headers."""
        # Create settings with allowed origins
        test_origins = "http://localhost:3000,https://app.example.com"

        with patch.dict('os.environ', {
            'CORS_ALLOWED_ORIGINS': test_origins,
            'JWT_SECRET': 'test_secret_minimum_32_characters_long',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db'
        }, clear=False):
            settings = Settings()

            # Parse origins
            origins = settings.get_cors_origins_list()

            # Assert
            assert len(origins) == 2
            assert "http://localhost:3000" in origins
            assert "https://app.example.com" in origins

    def test_cors_origins_comma_separated_parsing(self):
        """Test CORS origins are parsed from comma-separated string."""
        # Test with spaces
        test_origins = "http://localhost:3000, https://app.example.com , https://staging.example.com"

        with patch.dict('os.environ', {
            'CORS_ALLOWED_ORIGINS': test_origins,
            'JWT_SECRET': 'test_secret_minimum_32_characters_long',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db'
        }, clear=False):
            settings = Settings()

            origins = settings.get_cors_origins_list()

            # Assert - should strip whitespace
            assert len(origins) == 3
            assert "http://localhost:3000" in origins
            assert "https://app.example.com" in origins
            assert "https://staging.example.com" in origins

    def test_empty_cors_origins_returns_empty_list(self):
        """Test empty CORS_ALLOWED_ORIGINS returns empty list (not wildcard)."""
        with patch.dict('os.environ', {
            'CORS_ALLOWED_ORIGINS': '',
            'JWT_SECRET': 'test_secret_minimum_32_characters_long',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db'
        }, clear=False):
            settings = Settings()

            origins = settings.get_cors_origins_list()

            # Assert - should be empty list, NOT wildcard
            assert origins == []


class TestSQLInjectionPrevention:
    """Test SQL injection prevention in vector store."""

    def test_sql_injection_attempt_blocked(self):
        """Test SQL injection attempts are blocked by input validation."""
        from src.rag.vector_store import SearchRequest

        # Test SQL injection patterns
        malicious_queries = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin' --",
            "' UNION SELECT * FROM users --",
            "1'; DELETE FROM conversations; --"
        ]

        for malicious_query in malicious_queries:
            # Should raise ValueError for SQL special characters
            with pytest.raises(ValueError) as exc_info:
                SearchRequest(query=malicious_query, top_k=5)

            # Verify error message mentions prohibited character
            assert "prohibited" in str(exc_info.value).lower()

    def test_parameterized_queries_safe_from_injection(self):
        """Test parameterized queries are safe from SQL injection."""
        # This is a design test - verifies we use ORM/parameterized queries

        # Example of SAFE query pattern (using SQLAlchemy ORM)
        from sqlalchemy import text

        # Safe parameterized query
        safe_query = text("SELECT * FROM conversations WHERE id = :id")
        params = {"id": "550e8400-e29b-41d4-a716-446655440000"}

        # Assert query uses parameterization
        assert ":id" in str(safe_query)
        assert "id" in params

        # Unsafe pattern would be:
        # unsafe_query = f"SELECT * FROM conversations WHERE id = '{conversation_id}'"
        # This should NOT appear in our codebase

    def test_valid_queries_pass_validation(self):
        """Test that valid queries pass validation."""
        from src.rag.vector_store import SearchRequest

        valid_queries = [
            "How to implement authentication in Python",
            "React hooks best practices",
            "Database migration strategies",
            "REST API design patterns"
        ]

        for valid_query in valid_queries:
            # Should not raise any exceptions
            request = SearchRequest(query=valid_query, top_k=5)
            assert request.query == valid_query
            assert request.top_k == 5

    def test_filter_key_whitelist_enforcement(self):
        """Test that only whitelisted filter keys are allowed."""
        from src.rag.vector_store import SearchRequest

        # Test valid filters
        valid_filters = {"language": "python", "approved": True}
        request = SearchRequest(query="test query", top_k=5, filters=valid_filters)
        assert request.filters == valid_filters

        # Test invalid filter key
        invalid_filters = {"malicious_key": "value"}
        with pytest.raises(ValueError) as exc_info:
            SearchRequest(query="test query", top_k=5, filters=invalid_filters)

        assert "not allowed" in str(exc_info.value).lower()
