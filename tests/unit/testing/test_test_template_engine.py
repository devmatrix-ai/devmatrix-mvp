"""
Unit tests for TestTemplateEngine

Tests test code generation from requirements:
- Pytest template generation with patterns
- Jest/Vitest template generation
- Import generation based on requirement text
- Fixture generation for different contexts
- Pattern recognition and code synthesis
"""
import pytest
from uuid import uuid4
from src.testing.test_template_engine import TestTemplateEngine
from src.testing.requirement_parser import Requirement


class TestTestTemplateEngine:
    """Test TestTemplateEngine functionality"""

    def setup_method(self):
        """Setup engine instance for each test"""
        self.engine = TestTemplateEngine()

    # ========================================
    # Pytest Template Generation Tests
    # ========================================

    def test_generate_pytest_return_value_numeric(self):
        """Test pytest generation for 'must return X' pattern with number"""
        req = Requirement(
            text="API must return 200 status",
            priority="must",
            requirement_id="test_must_0",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "def test_test_must_0():" in test_code
        assert "result = function_under_test()" in test_code
        assert "assert result == 200" in test_code
        assert "Requirement: API must return 200 status" in test_code
        assert "Priority: must" in test_code

    def test_generate_pytest_return_value_string(self):
        """Test pytest generation for 'must return X' with non-numeric value"""
        req = Requirement(
            text="Function must return success",
            priority="must",
            requirement_id="test_must_1",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "assert result == 'success'" in test_code

    def test_generate_pytest_exception(self):
        """Test pytest generation for 'must raise X' pattern"""
        req = Requirement(
            text="Invalid input must raise ValueError",
            priority="must",
            requirement_id="test_must_2",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "with pytest.raises(ValueError):" in test_code
        assert "function_under_test()" in test_code

    def test_generate_pytest_validation(self):
        """Test pytest generation for 'must validate X' pattern"""
        req = Requirement(
            text="System must validate email",
            priority="must",
            requirement_id="test_must_3",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "result = validate_email(input_data)" in test_code
        assert "assert result.is_valid == True" in test_code

    def test_generate_pytest_threshold_less_than(self):
        """Test pytest generation for 'must be < X' pattern"""
        req = Requirement(
            text="Response time must be <200ms",
            priority="must",
            requirement_id="test_must_4",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "import time" in test_code
        assert "start = time.time()" in test_code
        assert "duration_ms = (time.time() - start) * 1000" in test_code
        assert "assert duration_ms < 200" in test_code

    def test_generate_pytest_threshold_greater_than(self):
        """Test pytest generation for 'must be > X' pattern"""
        req = Requirement(
            text="Success rate should be >95",
            priority="should",
            requirement_id="test_should_0",
            section="SHOULD",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "assert result > 95" in test_code

    def test_generate_pytest_jwt_pattern(self):
        """Test pytest generation for JWT authentication pattern"""
        req = Requirement(
            text="User authentication must use JWT tokens",
            priority="must",
            requirement_id="test_must_5",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "result = authenticate_user(credentials)" in test_code
        assert "assert 'token' in result" in test_code
        assert "assert is_valid_jwt(result['token'])" in test_code

    def test_generate_pytest_acid_transaction(self):
        """Test pytest generation for ACID transaction pattern"""
        req = Requirement(
            text="Database transactions must be ACID compliant",
            priority="must",
            requirement_id="test_must_6",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "with transaction():" in test_code
        assert "result = perform_operation()" in test_code
        assert "assert transaction_committed()" in test_code

    def test_generate_pytest_responsive_design(self):
        """Test pytest generation for responsive design pattern"""
        req = Requirement(
            text="UI should be responsive on mobile devices",
            priority="should",
            requirement_id="test_should_1",
            section="SHOULD",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "viewport_sizes = [(320, 568), (768, 1024), (1920, 1080)]" in test_code
        assert "for width, height in viewport_sizes:" in test_code
        assert "assert layout_renders_correctly(width, height)" in test_code

    def test_generate_pytest_default_placeholder(self):
        """Test pytest generation falls back to placeholder for unknown patterns"""
        req = Requirement(
            text="System works correctly with edge cases",
            priority="should",
            requirement_id="test_should_2",
            section="SHOULD",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        assert "# TODO: Implement test for:" in test_code
        assert "assert True  # Replace with actual test" in test_code

    # ========================================
    # Jest/Vitest Template Generation Tests
    # ========================================

    def test_generate_jest_return_value_numeric(self):
        """Test Jest generation for 'must return X' with number"""
        req = Requirement(
            text="API must return 200",
            priority="must",
            requirement_id="test_must_0",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "describe('test_must_0', () => {" in test_code
        assert "it('API must return 200', async () => {" in test_code
        assert "const result = await functionUnderTest();" in test_code
        assert "expect(result).toBe(200);" in test_code

    def test_generate_jest_return_value_string(self):
        """Test Jest generation for 'must return X' with string"""
        req = Requirement(
            text="Function must return success",
            priority="must",
            requirement_id="test_must_1",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "expect(result).toBe('success');" in test_code

    def test_generate_jest_exception(self):
        """Test Jest generation for 'must throw X' pattern"""
        req = Requirement(
            text="Invalid input must throw TypeError",
            priority="must",
            requirement_id="test_must_2",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "await expect(() => functionUnderTest()).rejects.toThrow(TypeError);" in test_code

    def test_generate_jest_validation(self):
        """Test Jest generation for 'must validate X' pattern"""
        req = Requirement(
            text="System must validate email",
            priority="must",
            requirement_id="test_must_3",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "const result = validateEmail(inputData);" in test_code
        assert "expect(result.isValid).toBe(true);" in test_code

    def test_generate_jest_threshold_less_than(self):
        """Test Jest generation for 'must be < X' pattern"""
        req = Requirement(
            text="Response time must be <100ms",
            priority="must",
            requirement_id="test_must_4",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "const start = performance.now();" in test_code
        assert "const duration = performance.now() - start;" in test_code
        assert "expect(duration).toBeLessThan(100);" in test_code

    def test_generate_jest_jwt_pattern(self):
        """Test Jest generation for JWT authentication"""
        req = Requirement(
            text="Authentication must use JWT",
            priority="must",
            requirement_id="test_must_5",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "const result = await authenticateUser(credentials);" in test_code
        assert "expect(result).toHaveProperty('token');" in test_code
        assert "expect(isValidJWT(result.token)).toBe(true);" in test_code

    def test_generate_jest_responsive_design(self):
        """Test Jest generation for responsive design"""
        req = Requirement(
            text="UI must be responsive",
            priority="must",
            requirement_id="test_must_6",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "const viewportSizes = [" in test_code
        assert "{ width: 320, height: 568 }" in test_code
        assert "for (const { width, height } of viewportSizes)" in test_code

    def test_generate_jest_default_placeholder(self):
        """Test Jest generation falls back to placeholder"""
        req = Requirement(
            text="Unknown pattern requirement",
            priority="should",
            requirement_id="test_should_0",
            section="SHOULD",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "// TODO: Implement test for:" in test_code
        assert "expect(true).toBe(true);" in test_code

    # ========================================
    # Import Generation Tests
    # ========================================

    def test_get_test_imports_pytest_basic(self):
        """Test pytest imports generation - basic"""
        req = Requirement("Basic requirement", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('pytest', req)

        assert "import pytest" in imports

    def test_get_test_imports_pytest_jwt(self):
        """Test pytest imports for JWT pattern"""
        req = Requirement("Must use JWT tokens", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('pytest', req)

        assert "import pytest" in imports
        assert "from jose import jwt" in imports

    def test_get_test_imports_pytest_validation(self):
        """Test pytest imports for validation pattern"""
        req = Requirement("Must validate email", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('pytest', req)

        assert "from validators import is_valid_email, is_valid_url" in imports

    def test_get_test_imports_pytest_time(self):
        """Test pytest imports for time/latency pattern"""
        req = Requirement("Response time must be <100ms", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('pytest', req)

        assert "import time" in imports

    def test_get_test_imports_jest_basic(self):
        """Test Jest imports generation - basic"""
        req = Requirement("Basic requirement", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('jest', req)

        assert "import { describe, it, expect } from 'jest';" in imports

    def test_get_test_imports_vitest_basic(self):
        """Test Vitest imports generation - basic"""
        req = Requirement("Basic requirement", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('vitest', req)

        assert "import { describe, it, expect } from 'vitest';" in imports

    def test_get_test_imports_jest_jwt(self):
        """Test Jest imports for JWT pattern"""
        req = Requirement("Must use JWT", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('jest', req)

        assert "import jwt from 'jsonwebtoken';" in imports

    def test_get_test_imports_jest_validation(self):
        """Test Jest imports for validation pattern"""
        req = Requirement("Must validate email", "must", "id", "MUST", {})
        imports = self.engine.get_test_imports('jest', req)

        assert "import { isValidEmail, isValidUrl } from './validators';" in imports

    # ========================================
    # Fixture Generation Tests
    # ========================================

    def test_get_test_fixtures_pytest_database(self):
        """Test pytest fixture generation for database pattern"""
        req = Requirement("Database transaction must work", "must", "id", "MUST", {})
        fixtures = self.engine.get_test_fixtures('pytest', req)

        assert "@pytest.fixture" in fixtures
        assert "def db_session():" in fixtures
        assert "session = create_test_session()" in fixtures
        assert "session.rollback()" in fixtures

    def test_get_test_fixtures_pytest_authentication(self):
        """Test pytest fixture generation for auth pattern"""
        req = Requirement("Authentication must use JWT", "must", "id", "MUST", {})
        fixtures = self.engine.get_test_fixtures('pytest', req)

        assert "@pytest.fixture" in fixtures
        assert "def test_credentials():" in fixtures
        assert "'username': 'test_user'" in fixtures
        assert "'password': 'test_password'" in fixtures

    def test_get_test_fixtures_pytest_no_match(self):
        """Test pytest fixture generation returns empty for no pattern match"""
        req = Requirement("Simple requirement", "must", "id", "MUST", {})
        fixtures = self.engine.get_test_fixtures('pytest', req)

        assert fixtures == ""

    def test_get_test_fixtures_jest_database(self):
        """Test Jest fixture generation for database pattern"""
        req = Requirement("Database transaction must work", "must", "id", "MUST", {})
        fixtures = self.engine.get_test_fixtures('jest', req)

        assert "beforeEach(async () => {" in fixtures
        assert "await setupTestDatabase();" in fixtures
        assert "afterEach(async () => {" in fixtures
        assert "await cleanupTestDatabase();" in fixtures

    def test_get_test_fixtures_jest_authentication(self):
        """Test Jest fixture generation for auth pattern"""
        req = Requirement("JWT authentication required", "must", "id", "MUST", {})
        fixtures = self.engine.get_test_fixtures('jest', req)

        assert "const testCredentials = {" in fixtures
        assert "username: 'test_user'" in fixtures
        assert "password: 'test_password'" in fixtures

    def test_get_test_fixtures_jest_no_match(self):
        """Test Jest fixture generation returns empty for no pattern"""
        req = Requirement("Simple requirement", "must", "id", "MUST", {})
        fixtures = self.engine.get_test_fixtures('jest', req)

        assert fixtures == ""

    # ========================================
    # Edge Cases and Integration
    # ========================================

    def test_generate_pytest_with_hyphenated_id(self):
        """Test pytest handles requirement IDs with hyphens correctly"""
        req = Requirement(
            text="Test requirement",
            priority="must",
            requirement_id="test-must-with-hyphens-0",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        # Should convert hyphens to underscores
        assert "def test_test_must_with_hyphens_0():" in test_code

    def test_generate_jest_priority_in_comment(self):
        """Test Jest includes priority in comment"""
        req = Requirement(
            text="Critical requirement",
            priority="must",
            requirement_id="test_must_0",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_jest_test(req)

        assert "// Priority: must" in test_code

    def test_pattern_combination_pytest(self):
        """Test pytest handles requirement with multiple patterns"""
        req = Requirement(
            text="Validate email and return 200",
            priority="must",
            requirement_id="test_must_0",
            section="MUST",
            metadata={}
        )

        test_code = self.engine.generate_pytest_test(req)

        # Should match first pattern found (return in this case)
        assert "assert result == 200" in test_code
