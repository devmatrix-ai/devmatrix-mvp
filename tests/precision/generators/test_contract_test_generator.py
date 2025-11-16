"""
Unit Tests for ContractTestGenerator

Tests contract extraction and test generation from discovery documents.
"""

import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch, MagicMock
from tests.precision.generators.contract_test_generator import (
    ContractTestGenerator,
    Contract,
    ContractTest,
)


class TestRequirementParsing:
    """Test requirement parsing from discovery documents."""

    def test_parse_simple_requirements(self):
        """Should parse numbered requirements from discovery doc."""
        discovery_doc = """
Build a simple API:

1. Create user endpoint
2. Get user by ID
3. Update user details
4. Delete user
"""
        generator = ContractTestGenerator(api_key="test-key")
        requirements = generator.parse_requirements(discovery_doc)

        assert len(requirements) == 4
        assert requirements[0]["id"] == 1
        assert requirements[0]["text"] == "Create user endpoint"
        assert requirements[3]["id"] == 4
        assert requirements[3]["text"] == "Delete user"

    def test_parse_requirements_with_modules(self):
        """Should detect module sections."""
        discovery_doc = """
**User Module:**
1. Create user
2. Get user

**Admin Module:**
3. List all users
4. Ban user
"""
        generator = ContractTestGenerator(api_key="test-key")
        requirements = generator.parse_requirements(discovery_doc)

        assert len(requirements) == 4
        assert requirements[0]["module"] == "User Module"
        assert requirements[1]["module"] == "User Module"
        assert requirements[2]["module"] == "Admin Module"
        assert requirements[3]["module"] == "Admin Module"

    def test_parse_technical_requirements(self):
        """Should extract technical requirements section."""
        discovery_doc = """
1. Create user endpoint
2. Get user by ID

**Technical Requirements:**
- Use SQLAlchemy for ORM
- Hash passwords with bcrypt
- Validate email format
"""
        generator = ContractTestGenerator(api_key="test-key")
        requirements = generator.parse_requirements(discovery_doc)

        assert len(requirements) == 2
        assert len(requirements[0]["technical_reqs"]) == 3
        assert "Use SQLAlchemy for ORM" in requirements[0]["technical_reqs"]
        assert "Hash passwords with bcrypt" in requirements[0]["technical_reqs"]

    def test_parse_empty_document(self):
        """Should handle empty discovery document."""
        generator = ContractTestGenerator(api_key="test-key")
        requirements = generator.parse_requirements("")

        assert requirements == []

    def test_parse_no_numbered_requirements(self):
        """Should handle document without numbered requirements."""
        discovery_doc = """
This is just a description without any numbered requirements.
It should return empty list.
"""
        generator = ContractTestGenerator(api_key="test-key")
        requirements = generator.parse_requirements(discovery_doc)

        assert requirements == []


class TestContractExtraction:
    """Test contract extraction using Claude API."""

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_extract_contracts_success(self, mock_anthropic):
        """Should extract contracts from requirement using Claude API."""
        # Mock API response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    {
                        "preconditions": [
                            {
                                "description": "Database must be connected",
                                "implied_from": "technical requirement",
                            }
                        ],
                        "postconditions": [
                            {
                                "description": "User record created in database",
                                "implied_from": "requirement",
                            }
                        ],
                        "invariants": [
                            {
                                "description": "Email must be unique",
                                "implied_from": "validation requirement",
                            }
                        ],
                    }
                )
            )
        ]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = ContractTestGenerator(api_key="test-key")
        requirement = {
            "id": 1,
            "text": "Create user with email",
            "module": "User Module",
            "technical_reqs": ["Use SQLAlchemy", "Validate email"],
        }

        contracts = generator.extract_contracts(requirement, "full doc context")

        assert len(contracts) == 3
        assert contracts[0].contract_type == "precondition"
        assert contracts[0].description == "Database must be connected"
        assert contracts[1].contract_type == "postcondition"
        assert contracts[2].contract_type == "invariant"

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_extract_contracts_with_markdown_response(self, mock_anthropic):
        """Should handle API response with markdown code blocks."""
        # Mock API response with markdown
        mock_client = Mock()
        mock_response = Mock()
        contracts_json = {
            "preconditions": [{"description": "User must exist", "implied_from": "req"}],
            "postconditions": [],
            "invariants": [],
        }
        mock_response.content = [
            Mock(text=f"```json\n{json.dumps(contracts_json)}\n```")
        ]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = ContractTestGenerator(api_key="test-key")
        requirement = {
            "id": 1,
            "text": "Delete user",
            "module": None,
            "technical_reqs": [],
        }

        contracts = generator.extract_contracts(requirement, "doc")

        assert len(contracts) == 1
        assert contracts[0].description == "User must exist"

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_extract_contracts_invalid_json(self, mock_anthropic):
        """Should handle invalid JSON response gracefully."""
        # Mock API response with invalid JSON
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="This is not valid JSON")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = ContractTestGenerator(api_key="test-key")
        requirement = {
            "id": 1,
            "text": "Create user",
            "module": None,
            "technical_reqs": [],
        }

        contracts = generator.extract_contracts(requirement, "doc")

        # Should return empty list on parse failure
        assert contracts == []


class TestTestCodeGeneration:
    """Test pytest code generation."""

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_generate_test_code_success(self, mock_anthropic):
        """Should generate pytest test code from contracts."""
        # Mock API response
        mock_client = Mock()
        mock_response = Mock()
        test_code = '''def test_requirement_001_contract_validation():
    """Test: Create user"""
    # Precondition: Database connected
    assert db.is_connected()

    # Execute: Create user
    user = create_user(email="test@example.com")

    # Postcondition: User created
    assert user is not None
    assert user.id is not None'''

        mock_response.content = [Mock(text=test_code)]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = ContractTestGenerator(api_key="test-key")
        requirement = {
            "id": 1,
            "text": "Create user",
            "technical_reqs": ["Use SQLAlchemy"],
        }
        contracts = [
            Contract(
                contract_type="precondition",
                description="Database connected",
                requirement_id=1,
                requirement_text="Create user",
            ),
            Contract(
                contract_type="postcondition",
                description="User created",
                requirement_id=1,
                requirement_text="Create user",
            ),
        ]

        code = generator.generate_test_code(requirement, contracts)

        assert "def test_requirement_001_contract_validation" in code
        assert "assert db.is_connected()" in code
        assert "assert user is not None" in code

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_generate_test_code_with_markdown(self, mock_anthropic):
        """Should extract code from markdown code blocks."""
        # Mock API response with markdown
        mock_client = Mock()
        mock_response = Mock()
        test_code = "def test_001():\n    assert True"
        mock_response.content = [Mock(text=f"```python\n{test_code}\n```")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = ContractTestGenerator(api_key="test-key")
        requirement = {"id": 1, "text": "Test", "technical_reqs": []}
        contracts = []

        code = generator.generate_test_code(requirement, contracts)

        assert code == test_code
        assert "```" not in code  # Markdown removed


class TestEndToEndGeneration:
    """Test complete contract test generation pipeline."""

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_generate_tests_complete_pipeline(self, mock_anthropic):
        """Should generate complete contract tests from discovery doc."""
        # Mock API responses
        mock_client = Mock()

        # Contract extraction response for req #1 (has contracts)
        contracts_response_1 = Mock()
        contracts_response_1.content = [
            Mock(
                text=json.dumps(
                    {
                        "preconditions": [
                            {"description": "DB connected", "implied_from": "tech"}
                        ],
                        "postconditions": [
                            {"description": "User created", "implied_from": "req"}
                        ],
                        "invariants": [],
                    }
                )
            )
        ]

        # Test code generation response for req #1
        test_code_response_1 = Mock()
        test_code_response_1.content = [
            Mock(text="def test_requirement_001_contract_validation():\n    pass")
        ]

        # Contract extraction response for req #2 (no contracts - will be skipped)
        contracts_response_2 = Mock()
        contracts_response_2.content = [
            Mock(
                text=json.dumps(
                    {"preconditions": [], "postconditions": [], "invariants": []}
                )
            )
        ]

        # Setup mock to return different responses for each call
        # Order: extract_contracts(req1) → generate_test(req1) → extract_contracts(req2)
        mock_client.messages.create.side_effect = [
            contracts_response_1,
            test_code_response_1,
            contracts_response_2,  # req #2 has no contracts, will be skipped
        ]
        mock_anthropic.return_value = mock_client

        discovery_doc = """
1. Create user with email
2. Get user by ID

**Technical Requirements:**
- Use SQLAlchemy
"""

        generator = ContractTestGenerator(api_key="test-key")
        contract_tests = generator.generate_tests(discovery_doc)

        assert len(contract_tests) == 1  # Only first req has contracts
        assert contract_tests[0].requirement_id == 1
        assert len(contract_tests[0].contracts) == 2  # 1 pre + 1 post
        assert "def test_requirement_001" in contract_tests[0].test_code

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_write_test_file(self, mock_anthropic, tmp_path):
        """Should write contract tests to pytest file."""
        # Create mock contract tests
        contract_test = ContractTest(
            test_name="test_requirement_001_contract_validation",
            requirement_id=1,
            requirement_text="Create user",
            contracts=[
                Contract(
                    contract_type="precondition",
                    description="DB connected",
                    requirement_id=1,
                    requirement_text="Create user",
                )
            ],
            test_code="def test_requirement_001_contract_validation():\n    pass",
        )

        generator = ContractTestGenerator(api_key="test-key")
        output_dir = tmp_path / "tests"
        generator.write_test_file([contract_test], output_dir, "user_module")

        # Verify file created
        test_file = output_dir / "test_user_module_contracts.py"
        assert test_file.exists()

        # Verify file content
        content = test_file.read_text()
        assert "Contract Tests - user_module" in content
        assert "DO NOT EDIT" in content
        assert "import pytest" in content
        assert "def test_requirement_001_contract_validation" in content

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_generate_from_discovery_statistics(self, mock_anthropic, tmp_path):
        """Should return accurate statistics from generation."""
        # Mock API responses
        mock_client = Mock()

        contracts_response = Mock()
        contracts_response.content = [
            Mock(
                text=json.dumps(
                    {
                        "preconditions": [{"description": "Pre1", "implied_from": "r"}],
                        "postconditions": [
                            {"description": "Post1", "implied_from": "r"},
                            {"description": "Post2", "implied_from": "r"},
                        ],
                        "invariants": [{"description": "Inv1", "implied_from": "r"}],
                    }
                )
            )
        ]

        test_code_response = Mock()
        test_code_response.content = [Mock(text="def test_001():\n    pass")]

        mock_client.messages.create.side_effect = [
            contracts_response,
            test_code_response,
        ]
        mock_anthropic.return_value = mock_client

        discovery_doc = "1. Create user"

        generator = ContractTestGenerator(api_key="test-key")
        stats = generator.generate_from_discovery(
            discovery_doc=discovery_doc,
            output_dir=tmp_path,
            module_name="test_module",
        )

        assert stats["tests_generated"] == 1
        assert stats["contracts_extracted"] == 4  # 1 pre + 2 post + 1 inv
        assert stats["preconditions"] == 1
        assert stats["postconditions"] == 2
        assert stats["invariants"] == 1
        assert stats["test_file"] == "test_test_module_contracts.py"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_api_key(self):
        """Should raise error if API key not provided."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY required"):
                ContractTestGenerator()

    def test_api_key_from_environment(self):
        """Should use API key from environment variable."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-test-key"}):
            generator = ContractTestGenerator()
            assert generator.api_key == "env-test-key"

    def test_api_key_from_parameter(self):
        """Should use API key from parameter over environment."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
            generator = ContractTestGenerator(api_key="param-key")
            assert generator.api_key == "param-key"

    @patch("tests.precision.generators.contract_test_generator.anthropic.Anthropic")
    def test_skip_requirements_without_contracts(self, mock_anthropic):
        """Should skip requirements that have no contracts."""
        # Mock API response with empty contracts
        mock_client = Mock()
        contracts_response = Mock()
        contracts_response.content = [
            Mock(
                text=json.dumps(
                    {"preconditions": [], "postconditions": [], "invariants": []}
                )
            )
        ]
        mock_client.messages.create.return_value = contracts_response
        mock_anthropic.return_value = mock_client

        discovery_doc = "1. Create user"

        generator = ContractTestGenerator(api_key="test-key")
        contract_tests = generator.generate_tests(discovery_doc)

        # Should skip requirement with no contracts
        assert len(contract_tests) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
