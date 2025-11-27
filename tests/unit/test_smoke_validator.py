"""
Unit tests for RuntimeSmokeTestValidator (Task 10).

Tests cover:
- Path parameter substitution
- Payload generation for different entity types
- Error response parsing
- Violation creation
- Fix hint generation
- Data models

Note: These tests do NOT start a real server. They test the helper methods
that can be unit tested in isolation. Integration tests for the full
smoke test are in the E2E pipeline.

Reference: IMPROVEMENT_ROADMAP.md Task 10.10
"""

import pytest
from pathlib import Path

from src.validation.runtime_smoke_validator import (
    RuntimeSmokeTestValidator,
    EndpointTestResult,
    SmokeTestResult,
)
from src.cognitive.ir.api_model import Endpoint, HttpMethod, APISchema, APISchemaField


class TestPathParameterSubstitution:
    """Test _substitute_path_params() method."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temp directory."""
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/products/{id}", "/products/test-id-123"),
            ("/products/{product_id}", "/products/test-product-123"),
            ("/customers/{customer_id}", "/customers/test-customer-123"),
            ("/carts/{cart_id}", "/carts/test-cart-123"),
            ("/orders/{order_id}", "/orders/test-order-123"),
            ("/users/{user_id}", "/users/test-user-123"),
            ("/products/{product_id}/reviews/{review_id}", "/products/test-product-123/reviews/test-id-123"),
            ("/api/v1/products", "/api/v1/products"),  # No params
            ("/items/{item_id}/details", "/items/test-item-123/details"),
        ],
    )
    def test_substitute_path_params(self, validator, path, expected):
        """Test path parameter substitution with various patterns."""
        assert validator._substitute_path_params(path) == expected


class TestFieldValueGeneration:
    """Test _generate_field_value() method."""

    @pytest.fixture
    def validator(self, tmp_path):
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    @pytest.mark.parametrize(
        ("field_name", "field_type", "expected"),
        [
            # Name-based inference
            ("email", "string", "test@example.com"),
            ("user_email", "str", "test@example.com"),
            ("customer_id", "uuid", "00000000-0000-0000-0000-000000000001"),
            ("product_id", "string", "test-id-123"),
            ("name", "string", "Test Name"),
            ("full_name", "str", "Test Name"),
            ("description", "string", "Test description"),
            ("price", "float", 99.99),
            ("total_amount", "decimal", 99.99),
            ("quantity", "int", 10),
            ("stock", "integer", 10),
            ("status", "string", "active"),
            ("url", "string", "https://example.com"),
            ("image_link", "str", "https://example.com"),
            ("is_active", "bool", True),
            # Type-based defaults (name-based inference takes precedence)
            ("enabled", "bool", True),
            ("items", "list", []),
            ("metadata", "dict", {}),
            # Default to string
            ("unknown_field", "unknown_type", "test_value"),
        ],
    )
    def test_generate_field_value(self, validator, field_name, field_type, expected):
        """Test field value generation based on name and type."""
        assert validator._generate_field_value(field_name, field_type) == expected


class TestPayloadGeneration:
    """Test payload generation for different entity types."""

    @pytest.fixture
    def validator(self, tmp_path):
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    def test_infer_payload_product(self, validator):
        """Test product payload inference."""
        endpoint = Endpoint(
            path="/products",
            method=HttpMethod.POST,
            operation_id="createProduct"
        )
        payload = validator._infer_payload_from_context(endpoint)

        assert "name" in payload
        assert "price" in payload
        assert payload["price"] == 99.99

    def test_infer_payload_customer(self, validator):
        """Test customer payload inference."""
        endpoint = Endpoint(
            path="/customers",
            method=HttpMethod.POST,
            operation_id="createCustomer"
        )
        payload = validator._infer_payload_from_context(endpoint)

        assert "email" in payload
        assert payload["email"] == "test@example.com"

    def test_infer_payload_cart(self, validator):
        """Test cart payload inference."""
        endpoint = Endpoint(
            path="/carts",
            method=HttpMethod.POST,
            operation_id="createCart"
        )
        payload = validator._infer_payload_from_context(endpoint)

        assert "customer_id" in payload

    def test_infer_payload_order(self, validator):
        """Test order payload inference."""
        endpoint = Endpoint(
            path="/orders",
            method=HttpMethod.POST,
            operation_id="createOrder"
        )
        payload = validator._infer_payload_from_context(endpoint)

        assert "customer_id" in payload

    def test_infer_payload_generic(self, validator):
        """Test generic payload inference."""
        endpoint = Endpoint(
            path="/unknown",
            method=HttpMethod.POST,
            operation_id="createUnknown"
        )
        payload = validator._infer_payload_from_context(endpoint)

        assert "name" in payload


class TestErrorResponseParsing:
    """Test _parse_error_response() method."""

    @pytest.fixture
    def validator(self, tmp_path):
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    @pytest.mark.parametrize(
        ("response_text", "expected_type", "expected_message_contains"),
        [
            ("NameError: name 'undefined_var' is not defined", "NameError", "undefined_var"),
            ("TypeError: argument must be string, not int", "TypeError", "argument must be string"),
            ("AttributeError: 'NoneType' object has no attribute 'get'", "AttributeError", "NoneType"),
            ("KeyError: 'missing_key'", "KeyError", "missing_key"),
            ("ValueError: invalid literal", "ValueError", "invalid literal"),
            ("ImportError: No module named 'foo'", "ImportError", "No module named"),
            ("ModuleNotFoundError: No module named 'bar'", "ModuleNotFoundError", "No module named"),
            ("Internal Server Error", "HTTP_500", "Internal Server Error"),
        ],
    )
    def test_parse_error_response(self, validator, response_text, expected_type, expected_message_contains):
        """Test error response parsing extracts error type and message."""
        result = validator._parse_error_response(response_text)

        assert result["type"] == expected_type
        assert expected_message_contains in result["message"]

    def test_parse_error_with_stack_trace(self, validator):
        """Test parsing response with full stack trace."""
        response = '''Traceback (most recent call last):
  File "/app/src/api/routes/product.py", line 42, in get_product
    return product_service.get(product_id)
  File "/app/src/services/product.py", line 15, in get
    raise NameError("undefined_var")
NameError: name 'undefined_var' is not defined'''

        result = validator._parse_error_response(response)

        assert result["type"] == "NameError"
        assert "undefined_var" in result["message"]
        assert "stack_trace" in result
        assert result["file"] == "/app/src/api/routes/product.py"
        assert result["line"] == 42


class TestViolationCreation:
    """Test _create_violation() and related methods."""

    @pytest.fixture
    def validator(self, tmp_path):
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    def test_create_violation_format(self, validator):
        """Test violation has Code Repair compatible format."""
        endpoint = Endpoint(
            path="/products/{product_id}",
            method=HttpMethod.GET,
            operation_id="getProduct"
        )
        result = EndpointTestResult(
            endpoint_path="/products/{product_id}",
            method="GET",
            success=False,
            status_code=500,
            error_type="NameError",
            error_message="name 'product_service' is not defined",
            stack_trace="Traceback...",
            response_time_ms=150.0
        )

        violation = validator._create_violation(endpoint, result)

        assert violation["type"] == "runtime_error"
        assert violation["severity"] == "critical"
        assert violation["endpoint"] == "GET /products/{product_id}"
        assert violation["error_type"] == "NameError"
        assert violation["error_message"] == "name 'product_service' is not defined"
        assert "fix_hint" in violation
        assert "file" in violation

    def test_infer_file_from_endpoint(self, validator):
        """Test file path inference from endpoint."""
        endpoint = Endpoint(
            path="/products/{product_id}",
            method=HttpMethod.GET,
            operation_id="getProduct"
        )

        file_path = validator._infer_file_from_endpoint(endpoint)
        assert "product.py" in file_path
        assert "routes" in file_path

    def test_infer_file_from_nested_endpoint(self, validator):
        """Test file path inference from nested endpoint."""
        endpoint = Endpoint(
            path="/customers/{id}/orders",
            method=HttpMethod.GET,
            operation_id="getCustomerOrders"
        )

        file_path = validator._infer_file_from_endpoint(endpoint)
        # Should extract first non-versioning resource from path
        assert "routes" in file_path


class TestFixHintGeneration:
    """Test _generate_fix_hint() method."""

    @pytest.fixture
    def validator(self, tmp_path):
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    @pytest.mark.parametrize(
        ("error_type", "expected_contains"),
        [
            ("NameError", "undefined"),
            ("TypeError", "signature"),
            ("AttributeError", "method exists"),
            ("KeyError", ".get()"),
            ("ValueError", "validation"),
            ("ImportError", "module path"),
            ("ModuleNotFoundError", "requirements.txt"),
            ("HTTP_500", "implementation"),
            ("ConnectionError", "server"),
            ("TimeoutError", "loops"),
            ("UnknownError", "runtime errors"),
        ],
    )
    def test_generate_fix_hint(self, validator, error_type, expected_contains):
        """Test fix hint generation for different error types."""
        result = EndpointTestResult(
            endpoint_path="/test",
            method="GET",
            success=False,
            error_type=error_type,
            error_message="test error"
        )

        hint = validator._generate_fix_hint(result)
        assert expected_contains.lower() in hint.lower()


class TestDataModels:
    """Test EndpointTestResult and SmokeTestResult data models."""

    def test_endpoint_test_result_success(self):
        """Test successful endpoint result."""
        result = EndpointTestResult(
            endpoint_path="/products",
            method="GET",
            success=True,
            status_code=200,
            response_time_ms=50.0
        )

        assert result.success
        assert result.status_code == 200
        assert result.error_type is None

    def test_endpoint_test_result_failure(self):
        """Test failed endpoint result."""
        result = EndpointTestResult(
            endpoint_path="/products/{id}",
            method="GET",
            success=False,
            status_code=500,
            error_type="NameError",
            error_message="undefined var",
            stack_trace="Traceback...",
            response_time_ms=100.0
        )

        assert not result.success
        assert result.error_type == "NameError"
        assert result.stack_trace is not None

    def test_smoke_test_result_passed(self):
        """Test smoke test result when all tests pass."""
        result = SmokeTestResult(
            passed=True,
            endpoints_tested=10,
            endpoints_passed=10,
            endpoints_failed=0,
            violations=[],
            results=[],
            total_time_ms=500.0,
            server_startup_time_ms=100.0
        )

        assert result.passed
        assert result.endpoints_failed == 0
        assert len(result.violations) == 0

    def test_smoke_test_result_failed(self):
        """Test smoke test result when some tests fail."""
        violations = [
            {"type": "runtime_error", "error_type": "NameError", "endpoint": "GET /products"}
        ]
        result = SmokeTestResult(
            passed=False,
            endpoints_tested=10,
            endpoints_passed=8,
            endpoints_failed=2,
            violations=violations,
            results=[],
            total_time_ms=600.0,
            server_startup_time_ms=150.0
        )

        assert not result.passed
        assert result.endpoints_failed == 2
        assert len(result.violations) == 1


class TestMinimalPayloadWithSchema:
    """Test _generate_minimal_payload() with schema information."""

    @pytest.fixture
    def validator(self, tmp_path):
        return RuntimeSmokeTestValidator(app_dir=tmp_path)

    def test_payload_from_schema(self, validator):
        """Test payload generation using endpoint schema."""
        schema = APISchema(
            name="ProductCreate",
            fields=[
                APISchemaField(name="name", type="string", required=True),
                APISchemaField(name="price", type="float", required=True),
                APISchemaField(name="description", type="string", required=False),
            ]
        )

        endpoint = Endpoint(
            path="/products",
            method=HttpMethod.POST,
            operation_id="createProduct",
            request_schema=schema
        )

        payload = validator._generate_minimal_payload(endpoint)

        # Should include required fields
        assert "name" in payload
        assert "price" in payload
        # Optional fields may or may not be included
        assert payload["name"] == "Test Name"
        assert payload["price"] == 99.99
