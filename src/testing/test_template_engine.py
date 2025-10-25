"""
Test template generation for pytest, Jest, Vitest

Generates executable test code from requirements using pattern matching.
"""
from typing import Dict, Optional
import re
import logging
from .requirement_parser import Requirement

logger = logging.getLogger(__name__)


class TestTemplateEngine:
    """
    Generate executable tests from requirements using templates

    Supports:
    - pytest for Python atoms
    - Jest/Vitest for TypeScript/JavaScript atoms
    """

    def __init__(self):
        # Pytest template
        self.pytest_template = """
import pytest
from uuid import UUID

def test_{test_id}():
    '''
    Requirement: {requirement_text}
    Priority: {priority}
    '''
    {test_body}
"""

        # Jest/Vitest template
        self.jest_template = """
import {{ describe, it, expect }} from 'vitest';

describe('{requirement_id}', () => {{
  it('{requirement_text}', async () => {{
    // Priority: {priority}
    {test_body}
  }});
}});
"""

    def generate_pytest_test(
        self,
        requirement: Requirement,
        atom_context: Optional[Dict] = None
    ) -> str:
        """
        Generate pytest test from requirement

        Args:
            requirement: Parsed requirement
            atom_context: Optional context (imports, functions, etc.)

        Returns:
            Complete pytest test code
        """
        test_id = requirement.requirement_id.replace('-', '_')

        # Analyze requirement text to generate appropriate test body
        test_body = self._analyze_requirement_for_pytest(requirement, atom_context)

        return self.pytest_template.format(
            test_id=test_id,
            requirement_text=requirement.text,
            priority=requirement.priority,
            test_body=test_body
        )

    def generate_jest_test(
        self,
        requirement: Requirement,
        atom_context: Optional[Dict] = None
    ) -> str:
        """
        Generate Jest/Vitest test from requirement
        """
        test_body = self._analyze_requirement_for_jest(requirement, atom_context)

        return self.jest_template.format(
            requirement_id=requirement.requirement_id,
            requirement_text=requirement.text,
            priority=requirement.priority,
            test_body=test_body
        )

    def _analyze_requirement_for_pytest(
        self,
        req: Requirement,
        context: Optional[Dict] = None
    ) -> str:
        """
        Analyze requirement text and generate appropriate pytest assertions

        Examples:
        - "must return 200 status" → assert response.status_code == 200
        - "must validate email format" → assert is_valid_email(email)
        - "must raise ValueError" → with pytest.raises(ValueError)
        """
        text = req.text.lower()

        # Pattern: "must return X"
        if 'return' in text:
            match = re.search(r'return\s+(\w+)', text)
            if match:
                expected_value = match.group(1)
                # Try to detect if it's a number
                try:
                    int(expected_value)
                    return f"    result = function_under_test()\n    assert result == {expected_value}"
                except ValueError:
                    return f"    result = function_under_test()\n    assert result == '{expected_value}'"

        # Pattern: "must raise X exception"
        if 'raise' in text or 'throw' in text:
            match = re.search(r'raise\s+(\w+)', text)
            if match:
                exception_type = match.group(1)
                return f"    with pytest.raises({exception_type}):\n        function_under_test()"

        # Pattern: "must validate X"
        if 'validate' in text:
            match = re.search(r'validate\s+(\w+)', text)
            if match:
                validation_target = match.group(1)
                return f"    result = validate_{validation_target}(input_data)\n    assert result.is_valid == True"

        # Pattern: "must be < X" or "must be > X"
        if match := re.search(r'(must be|should be)\s*([<>]=?)\s*(\d+)', text):
            operator = match.group(2)
            value = match.group(3)
            return f"    result = function_under_test()\n    assert result {operator} {value}"

        # Pattern: "must use JWT"
        if 'use jwt' in text or 'jwt token' in text:
            return """    result = authenticate_user(credentials)
    assert 'token' in result
    assert is_valid_jwt(result['token'])"""

        # Pattern: "must be ACID compliant"
        if 'acid' in text or 'transaction' in text:
            return """    with transaction():
        result = perform_operation()
        # Verify atomicity, consistency, isolation, durability
        assert transaction_committed()"""

        # Pattern: "must be responsive"
        if 'responsive' in text or 'mobile' in text:
            return """    # Test responsive design
    viewport_sizes = [(320, 568), (768, 1024), (1920, 1080)]
    for width, height in viewport_sizes:
        assert layout_renders_correctly(width, height)"""

        # Pattern: "response time" or "latency"
        if 'response time' in text or 'latency' in text:
            match = re.search(r'<\s*(\d+)\s*(ms|seconds?)', text)
            if match:
                threshold = match.group(1)
                unit = match.group(2)
                multiplier = 1 if 'ms' in unit else 1000
                return f"""    import time
    start = time.time()
    result = function_under_test()
    duration_ms = (time.time() - start) * 1000
    assert duration_ms < {int(threshold) * multiplier}"""

        # Default: placeholder for manual implementation
        return f"    # TODO: Implement test for: {req.text}\n    assert True  # Replace with actual test"

    def _analyze_requirement_for_jest(
        self,
        req: Requirement,
        context: Optional[Dict] = None
    ) -> str:
        """
        Analyze requirement and generate Jest/Vitest assertions
        """
        text = req.text.lower()

        # Pattern: "must return X"
        if 'return' in text:
            match = re.search(r'return\s+(\w+)', text)
            if match:
                expected_value = match.group(1)
                try:
                    int(expected_value)
                    return f"    const result = await functionUnderTest();\n    expect(result).toBe({expected_value});"
                except ValueError:
                    return f"    const result = await functionUnderTest();\n    expect(result).toBe('{expected_value}');"

        # Pattern: "must throw X"
        if 'throw' in text or 'raise' in text:
            match = re.search(r'(throw|raise)\s+(\w+)', text)
            if match:
                exception_type = match.group(2)
                return f"    await expect(() => functionUnderTest()).rejects.toThrow({exception_type});"

        # Pattern: "must validate X"
        if 'validate' in text:
            match = re.search(r'validate\s+(\w+)', text)
            if match:
                validation_target = match.group(1)
                return f"    const result = validate{validation_target.capitalize()}(inputData);\n    expect(result.isValid).toBe(true);"

        # Pattern: "must be < X" or "must be > X"
        if match := re.search(r'(must be|should be)\s*([<>]=?)\s*(\d+)', text):
            operator = match.group(2)
            value = match.group(3)
            js_operator = operator.replace('<', 'toBeLessThan').replace('>', 'toBeGreaterThan')
            if '=' in operator:
                js_operator += 'OrEqual'
            return f"    const result = await functionUnderTest();\n    expect(result).{js_operator}({value});"

        # Pattern: "must use JWT"
        if 'use jwt' in text or 'jwt token' in text:
            return """    const result = await authenticateUser(credentials);
    expect(result).toHaveProperty('token');
    expect(isValidJWT(result.token)).toBe(true);"""

        # Pattern: "must be responsive"
        if 'responsive' in text or 'mobile' in text:
            return """    const viewportSizes = [
      { width: 320, height: 568 },
      { width: 768, height: 1024 },
      { width: 1920, height: 1080 }
    ];
    for (const { width, height } of viewportSizes) {
      expect(await layoutRendersCorrectly(width, height)).toBe(true);
    }"""

        # Pattern: "response time" or "latency"
        if 'response time' in text or 'latency' in text:
            match = re.search(r'<\s*(\d+)\s*(ms|seconds?)', text)
            if match:
                threshold = match.group(1)
                unit = match.group(2)
                multiplier = 1 if 'ms' in unit else 1000
                return f"""    const start = performance.now();
    const result = await functionUnderTest();
    const duration = performance.now() - start;
    expect(duration).toBeLessThan({int(threshold) * multiplier});"""

        # Default
        return f"    // TODO: Implement test for: {req.text}\n    expect(true).toBe(true);  // Replace with actual test"

    def get_test_imports(self, language: str, requirement: Requirement) -> str:
        """
        Generate necessary imports based on requirement and language

        Args:
            language: 'pytest', 'jest', or 'vitest'
            requirement: Requirement being tested

        Returns:
            Import statements as string
        """
        text = requirement.text.lower()
        imports = []

        if language == 'pytest':
            # Always include pytest
            imports.append("import pytest")

            # Add specific imports based on patterns
            if 'raise' in text or 'exception' in text:
                # pytest.raises already imported
                pass

            if 'jwt' in text:
                imports.append("from jose import jwt")

            if 'validate' in text:
                imports.append("from validators import is_valid_email, is_valid_url")

            if 'time' in text or 'latency' in text or 'response time' in text:
                imports.append("import time")

        elif language in ['jest', 'vitest']:
            # Always include test framework
            imports.append(f"import {{ describe, it, expect }} from '{language}';")

            # Add specific imports
            if 'jwt' in text:
                imports.append("import jwt from 'jsonwebtoken';")

            if 'validate' in text:
                imports.append("import { isValidEmail, isValidUrl } from './validators';")

            if 'time' in text or 'latency' in text or 'response time' in text:
                # performance API is built-in
                pass

        return '\n'.join(imports)

    def get_test_fixtures(self, language: str, requirement: Requirement) -> str:
        """
        Generate test fixtures/setup based on requirement

        Args:
            language: 'pytest', 'jest', or 'vitest'
            requirement: Requirement being tested

        Returns:
            Fixture code as string
        """
        text = requirement.text.lower()
        fixtures = []

        if language == 'pytest':
            if 'database' in text or 'transaction' in text:
                fixtures.append("""
@pytest.fixture
def db_session():
    '''Database session fixture'''
    session = create_test_session()
    yield session
    session.rollback()
    session.close()
""")

            if 'authentication' in text or 'jwt' in text:
                fixtures.append("""
@pytest.fixture
def test_credentials():
    '''Test user credentials'''
    return {
        'username': 'test_user',
        'password': 'test_password'
    }
""")

        elif language in ['jest', 'vitest']:
            if 'database' in text or 'transaction' in text:
                fixtures.append("""
beforeEach(async () => {
  await setupTestDatabase();
});

afterEach(async () => {
  await cleanupTestDatabase();
});
""")

            if 'authentication' in text or 'jwt' in text:
                fixtures.append("""
const testCredentials = {
  username: 'test_user',
  password: 'test_password'
};
""")

        return '\n'.join(fixtures)
