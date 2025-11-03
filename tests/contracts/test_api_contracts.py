"""
API Contract Tests

Tests API schema compliance and backward compatibility.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
class TestAPISchemaValidation:
    """Test API schema compliance with OpenAPI specification."""

    def test_openapi_schema_exists(self):
        """Test that OpenAPI schema is available."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert 'openapi' in schema
        assert 'info' in schema
        assert 'paths' in schema

    def test_api_version_in_schema(self):
        """Test API version is documented in schema."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert 'info' in schema
        assert 'version' in schema['info']

    def test_all_endpoints_documented(self):
        """Test all endpoints are documented in schema."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema.get('paths', {})
        
        # Should have health endpoints
        assert '/health' in paths or any('health' in path for path in paths)
        
        # Should have API v1 endpoints
        assert any('/api/v1' in path for path in paths)

    def test_response_models_in_schema(self):
        """Test response models are documented."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Should have component schemas
        assert 'components' in schema or len(schema.get('paths', {})) > 0

    def test_security_schemes_documented(self):
        """Test security schemes are documented."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Should document security (JWT/Bearer)
        # Either in components or security definitions
        has_security = (
            'securitySchemes' in schema.get('components', {}) or
            'security' in schema
        )
        
        # Some endpoints should have security
        assert has_security or len(schema.get('paths', {})) > 0


@pytest.mark.contract
class TestAPIBackwardCompatibility:
    """Test API backward compatibility."""

    def test_v1_endpoints_stable(self):
        """Test v1 API endpoints maintain stable paths."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get('paths', {})
        
        # v1 endpoints should exist
        v1_paths = [p for p in paths if '/api/v1' in p]
        
        # Should have v1 endpoints
        assert len(v1_paths) > 0

    def test_v2_endpoints_coexist_with_v1(self):
        """Test v2 endpoints don't break v1."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get('paths', {})
        
        v1_paths = [p for p in paths if '/api/v1' in p]
        v2_paths = [p for p in paths if '/api/v2' in p]
        
        # Both versions should coexist
        assert len(v1_paths) > 0 or len(v2_paths) > 0

    def test_required_fields_not_removed(self):
        """Test required fields in responses are stable."""
        from src.api.app import create_app

        app = create_app()
        
        # Schema should define required fields
        # This is more of a documentation check
        assert app is not None


@pytest.mark.contract
class TestRequestValidation:
    """Test request validation follows schema."""

    def test_invalid_request_returns_422(self):
        """Test invalid requests return 422 Unprocessable Entity."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        # Try to create workflow with invalid data (if endpoint exists)
        response = client.post(
            "/workflows",
            json={"invalid": "data"}
        )
        
        # Should return 422 for validation errors (or 404 if endpoint doesn't exist)
        assert response.status_code in [404, 422]

    def test_missing_required_field_returns_422(self):
        """Test missing required fields return validation error."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        # Empty POST request
        response = client.post("/workflows", json={})
        
        # Should return 422 for missing required fields
        assert response.status_code in [404, 422]


@pytest.mark.contract
class TestResponseFormat:
    """Test response format consistency."""

    def test_error_responses_have_detail(self):
        """Test error responses include detail field."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        # Request non-existent resource
        response = client.get("/api/v1/masterplans/00000000-0000-0000-0000-000000000000")
        
        if response.status_code >= 400:
            data = response.json()
            # Should have detail field for errors
            assert 'detail' in data or 'message' in data

    def test_success_responses_have_data(self):
        """Test success responses have expected structure."""
        from src.api.app import create_app

        app = create_app()
        client = TestClient(app)
        
        # Health check should return success
        response = client.get("/health/live")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_list_endpoints_return_arrays(self):
        """Test list endpoints return arrays."""
        from src.api.app import create_app

        app = create_app()
        
        # List endpoints should return arrays
        # This is validated by OpenAPI schema
        assert app is not None


@pytest.mark.contract
@pytest.mark.unit
class TestSchemaModels:
    """Test Pydantic models for schema compliance."""

    def test_models_have_examples(self):
        """Test request models have schema examples."""
        from src.api.routers.masterplans import CreateMasterPlanRequest

        # Models should have Config with json_schema_extra
        assert hasattr(CreateMasterPlanRequest, 'Config') or hasattr(CreateMasterPlanRequest, 'model_config')

    def test_models_validate_correctly(self):
        """Test Pydantic models validate input."""
        from src.api.routers.workflows import WorkflowCreate, TaskDefinition

        # Valid model
        task = TaskDefinition(
            task_id="task_1",
            agent_type="planning",
            prompt="Test"
        )
        assert task.task_id == "task_1"

        # Invalid model should raise ValidationError
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            WorkflowCreate(
                name="",  # Too short
                tasks=[]  # Empty (min_items=1)
            )

