"""
Tests for TestTemplateEngine

Tests test code generation from requirements using pattern matching.
"""
import pytest
from uuid import uuid4

from src.testing.requirement_parser import Requirement
from src.testing.test_template_engine import TestTemplateEngine


class TestTestTemplateEngine:
    """Test TestTemplateEngine functionality"""

    @pytest.fixture
    def engine(self):
        """Create TestTemplateEngine instance"""
        return TestTemplateEngine()

    @pytest.fixture
    def masterplan_id(self):
        """Generate test masterplan ID"""
        return uuid4()

    def test_generate_pytest_return_pattern(self, engine, masterplan_id):
        """Test pytest generation for 'must return' pattern"""
        req = Requirement(
            text="Must return status code 200",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "def test_" in test_code
        assert "assert" in test_code
        assert "200" in test_code or "status" in test_code.lower()

    def test_generate_pytest_raise_pattern(self, engine, masterplan_id):
        """Test pytest generation for 'must raise' pattern"""
        req = Requirement(
            text="Must raise ValueError for invalid input",
            priority='must',
            requirement_id=f"{masterplan_id}_must_1",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "pytest.raises" in test_code
        assert "ValueError" in test_code

    def test_generate_pytest_jwt_pattern(self, engine, masterplan_id):
        """Test pytest generation for JWT authentication pattern"""
        req = Requirement(
            text="Must use JWT tokens for authentication",
            priority='must',
            requirement_id=f"{masterplan_id}_must_2",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "token" in test_code.lower()
        assert "assert" in test_code

    def test_generate_pytest_validation_pattern(self, engine, masterplan_id):
        """Test pytest generation for validation pattern"""
        req = Requirement(
            text="Must validate email format before registration",
            priority='must',
            requirement_id=f"{masterplan_id}_must_3",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "validate" in test_code.lower() or "email" in test_code.lower()
        assert "assert" in test_code

    def test_generate_pytest_rate_limit_pattern(self, engine, masterplan_id):
        """Test pytest generation for rate limiting pattern"""
        req = Requirement(
            text="Must implement rate limiting (5 attempts/minute)",
            priority='must',
            requirement_id=f"{masterplan_id}_must_4",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "rate" in test_code.lower() or "limit" in test_code.lower()
        assert "5" in test_code or "minute" in test_code.lower()

    def test_generate_pytest_contains_test_function(self, engine, masterplan_id):
        """Test generated pytest contains valid test function"""
        req = Requirement(
            text="Must do something",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert test_code.strip().startswith("def test_")
        assert "():" in test_code or "()" in test_code

    def test_generate_jest_return_pattern(self, engine, masterplan_id):
        """Test Jest generation for 'must return' pattern"""
        req = Requirement(
            text="Must return user object",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_jest_test(req)

        assert "test(" in test_code or "it(" in test_code
        assert "expect(" in test_code
        assert "user" in test_code.lower()

    def test_generate_jest_async_pattern(self, engine, masterplan_id):
        """Test Jest async function generation"""
        req = Requirement(
            text="Must fetch data from API",
            priority='must',
            requirement_id=f"{masterplan_id}_must_1",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_jest_test(req)

        assert "async" in test_code or "await" in test_code or "Promise" in test_code

    def test_generate_jest_contains_test_block(self, engine, masterplan_id):
        """Test generated Jest contains valid test block"""
        req = Requirement(
            text="Must do something",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_jest_test(req)

        assert "test(" in test_code or "it(" in test_code
        assert "expect(" in test_code

    def test_fallback_pattern_pytest(self, engine, masterplan_id):
        """Test fallback pattern for unrecognized requirement (pytest)"""
        req = Requirement(
            text="Must implement some complex business logic",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "def test_" in test_code
        assert "assert" in test_code
        # Should contain generic implementation marker
        assert "# TODO" in test_code or "pass" in test_code or "implement" in test_code.lower()

    def test_fallback_pattern_jest(self, engine, masterplan_id):
        """Test fallback pattern for unrecognized requirement (Jest)"""
        req = Requirement(
            text="Must implement some complex business logic",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_jest_test(req)

        assert "test(" in test_code or "it(" in test_code
        assert "expect(" in test_code

    def test_context_integration_pytest(self, engine, masterplan_id):
        """Test context parameter affects pytest generation"""
        req = Requirement(
            text="Must return user data",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        context = {
            'framework': 'FastAPI',
            'language': 'Python',
            'test_framework': 'pytest'
        }

        test_code = engine.generate_pytest_test(req, context)

        assert "def test_" in test_code
        # Context should influence generation
        assert "user" in test_code.lower()

    def test_multiple_patterns_in_requirement(self, engine, masterplan_id):
        """Test requirement with multiple patterns"""
        req = Requirement(
            text="Must validate input and return 400 for errors",
            priority='must',
            requirement_id=f"{masterplan_id}_must_0",
            section='MUST',
            metadata={}
        )

        test_code = engine.generate_pytest_test(req)

        assert "validate" in test_code.lower()
        assert "400" in test_code or "error" in test_code.lower()
