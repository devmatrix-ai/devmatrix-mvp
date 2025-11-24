"""
Tests for LLM Validation Extractor (Phase 2)

Validates the aggressive LLM-based validation extraction functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.llm_validation_extractor import LLMValidationExtractor, ExtractionResult
from src.cognitive.ir.validation_model import ValidationRule, ValidationType


@pytest.fixture
def sample_spec():
    """Sample specification for testing."""
    return {
        "name": "TodoApp",
        "entities": [
            {
                "name": "User",
                "fields": [
                    {
                        "name": "email",
                        "type": "String",
                        "required": True,
                        "unique": True,
                        "description": "User email address"
                    },
                    {
                        "name": "password",
                        "type": "String",
                        "required": True,
                        "description": "User password (hashed)"
                    },
                    {
                        "name": "username",
                        "type": "String",
                        "required": True,
                        "unique": True
                    }
                ]
            },
            {
                "name": "Todo",
                "fields": [
                    {
                        "name": "title",
                        "type": "String",
                        "required": True
                    },
                    {
                        "name": "user_id",
                        "type": "UUID",
                        "required": True
                    },
                    {
                        "name": "status",
                        "type": "String",
                        "enum": ["pending", "in_progress", "completed"]
                    }
                ]
            }
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/todos/{id}",
                "description": "Get todo by ID"
            },
            {
                "method": "POST",
                "path": "/todos",
                "description": "Create new todo"
            }
        ]
    }


class TestLLMValidationExtractor:
    """Test suite for LLM Validation Extractor."""

    def test_initialization(self):
        """Test extractor initializes correctly."""
        extractor = LLMValidationExtractor()

        assert extractor.model == "claude-3-5-sonnet-20241022"
        assert extractor.max_retries == 3
        assert extractor.batch_size == 12
        assert extractor.total_tokens_used == 0
        assert extractor.total_api_calls == 0

    @patch('src.services.llm_validation_extractor.Anthropic')
    def test_extract_field_validations(self, mock_anthropic, sample_spec):
        """Test field validation extraction with mocked LLM."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='''[
            {
                "entity": "User",
                "attribute": "email",
                "type": "FORMAT",
                "condition": "email format",
                "error_message": "Email must be valid",
                "confidence": 0.95,
                "rationale": "Email field requires format validation"
            },
            {
                "entity": "User",
                "attribute": "email",
                "type": "UNIQUENESS",
                "condition": "unique",
                "error_message": "Email must be unique",
                "confidence": 0.95,
                "rationale": "Email marked as unique"
            },
            {
                "entity": "User",
                "attribute": "password",
                "type": "FORMAT",
                "condition": "min length 8",
                "error_message": "Password must be at least 8 characters",
                "confidence": 0.90,
                "rationale": "Password security requirement"
            }
        ]''')]
        mock_message.usage = MagicMock(input_tokens=500, output_tokens=200)
        mock_client.messages.create.return_value = mock_message

        # Execute
        extractor = LLMValidationExtractor()
        result = extractor._extract_field_validations(sample_spec)

        # Verify
        assert isinstance(result, ExtractionResult)
        assert len(result.rules) == 3
        assert result.confidence_avg > 0.9
        assert result.token_count == 700

    @patch('src.services.llm_validation_extractor.Anthropic')
    def test_extract_endpoint_validations(self, mock_anthropic, sample_spec):
        """Test endpoint validation extraction."""
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='''[
            {
                "entity": "Endpoint:GET",
                "attribute": "id",
                "type": "FORMAT",
                "condition": "uuid format",
                "error_message": "ID must be valid UUID",
                "confidence": 0.95,
                "rationale": "Path parameter requires UUID validation"
            },
            {
                "entity": "Endpoint:POST",
                "attribute": "body",
                "type": "PRESENCE",
                "condition": "required",
                "error_message": "Request body is required",
                "confidence": 0.98,
                "rationale": "POST requires body"
            }
        ]''')]
        mock_message.usage = MagicMock(input_tokens=400, output_tokens=150)
        mock_client.messages.create.return_value = mock_message

        extractor = LLMValidationExtractor()
        result = extractor._extract_endpoint_validations(sample_spec)

        assert len(result.rules) == 2
        assert any(r.attribute == "id" for r in result.rules)
        assert any(r.attribute == "body" for r in result.rules)

    @patch('src.services.llm_validation_extractor.Anthropic')
    def test_extract_cross_entity_validations(self, mock_anthropic, sample_spec):
        """Test cross-entity validation extraction."""
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='''[
            {
                "entity": "Todo",
                "attribute": "user_id",
                "type": "RELATIONSHIP",
                "condition": "references User.id",
                "error_message": "User not found",
                "confidence": 0.98,
                "rationale": "Foreign key constraint"
            },
            {
                "entity": "Todo",
                "attribute": "status",
                "type": "STATUS_TRANSITION",
                "condition": "pending -> in_progress -> completed",
                "error_message": "Invalid status transition",
                "confidence": 0.90,
                "rationale": "Workflow state machine"
            }
        ]''')]
        mock_message.usage = MagicMock(input_tokens=600, output_tokens=180)
        mock_client.messages.create.return_value = mock_message

        extractor = LLMValidationExtractor()
        result = extractor._extract_cross_entity_validations(sample_spec)

        assert len(result.rules) == 2
        assert any(r.type == ValidationType.RELATIONSHIP for r in result.rules)
        assert any(r.type == ValidationType.STATUS_TRANSITION for r in result.rules)

    def test_json_extraction_from_markdown(self):
        """Test JSON extraction from markdown code blocks."""
        extractor = LLMValidationExtractor()

        response = '''Here are the validations:
```json
[
    {
        "entity": "User",
        "attribute": "email",
        "type": "FORMAT"
    }
]
```
        '''

        json_text = extractor._extract_json_from_response(response)
        assert json_text is not None
        assert json_text.strip().startswith('[')

    def test_json_extraction_from_plain_array(self):
        """Test JSON extraction from plain array."""
        extractor = LLMValidationExtractor()

        response = '[{"entity": "User", "attribute": "email", "type": "FORMAT"}]'

        json_text = extractor._extract_json_from_response(response)
        assert json_text == response

    def test_dict_to_validation_rule_valid(self):
        """Test converting valid dict to ValidationRule."""
        extractor = LLMValidationExtractor()

        rule_dict = {
            "entity": "User",
            "attribute": "email",
            "type": "FORMAT",
            "condition": "email format",
            "error_message": "Invalid email",
            "confidence": 0.95
        }

        rule = extractor._dict_to_validation_rule(rule_dict)

        assert rule is not None
        assert rule.entity == "User"
        assert rule.attribute == "email"
        assert rule.type == ValidationType.FORMAT

    def test_dict_to_validation_rule_invalid_type(self):
        """Test handling invalid validation type."""
        extractor = LLMValidationExtractor()

        rule_dict = {
            "entity": "User",
            "attribute": "email",
            "type": "INVALID_TYPE",
            "error_message": "Invalid email"
        }

        rule = extractor._dict_to_validation_rule(rule_dict)
        assert rule is None

    def test_dict_to_validation_rule_missing_fields(self):
        """Test handling missing required fields."""
        extractor = LLMValidationExtractor()

        rule_dict = {
            "entity": "User",
            "type": "FORMAT"
            # Missing attribute
        }

        rule = extractor._dict_to_validation_rule(rule_dict)
        assert rule is None

    @patch('src.services.llm_validation_extractor.Anthropic')
    def test_retry_logic_on_timeout(self, mock_anthropic):
        """Test retry logic handles API timeout."""
        from anthropic import APITimeoutError

        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        # First call fails, second succeeds
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='[]')]
        mock_message.usage = MagicMock(input_tokens=100, output_tokens=50)

        mock_client.messages.create.side_effect = [
            APITimeoutError("Timeout"),
            mock_message
        ]

        extractor = LLMValidationExtractor()

        with patch('time.sleep'):  # Skip actual sleep
            response, tokens = extractor._call_llm_with_retry("test prompt")

        assert response == '[]'
        assert mock_client.messages.create.call_count == 2

    def test_fallback_json_parsing(self):
        """Test fallback parsing for malformed JSON."""
        extractor = LLMValidationExtractor()

        malformed = '''
        {"entity": "User", "attribute": "email", "type": "FORMAT", "confidence": 0.9}
        Some text in between
        {"entity": "User", "attribute": "password", "type": "FORMAT", "confidence": 0.85}
        '''

        rules, confidences = extractor._fallback_json_parsing(malformed)

        assert len(rules) == 2
        assert len(confidences) == 2
        assert all(r.entity == "User" for r in rules)

    @patch('src.services.llm_validation_extractor.Anthropic')
    def test_extract_all_validations_integration(self, mock_anthropic, sample_spec):
        """Test complete extraction pipeline."""
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        # Mock responses for all three extraction stages
        field_response = '''[
            {"entity": "User", "attribute": "email", "type": "FORMAT",
             "error_message": "Invalid email", "confidence": 0.95}
        ]'''

        endpoint_response = '''[
            {"entity": "Endpoint:GET", "attribute": "id", "type": "FORMAT",
             "error_message": "Invalid ID", "confidence": 0.90}
        ]'''

        cross_response = '''[
            {"entity": "Todo", "attribute": "user_id", "type": "RELATIONSHIP",
             "error_message": "User not found", "confidence": 0.95}
        ]'''

        mock_messages = [
            MagicMock(
                content=[MagicMock(text=field_response)],
                usage=MagicMock(input_tokens=500, output_tokens=100)
            ),
            MagicMock(
                content=[MagicMock(text=endpoint_response)],
                usage=MagicMock(input_tokens=400, output_tokens=80)
            ),
            MagicMock(
                content=[MagicMock(text=cross_response)],
                usage=MagicMock(input_tokens=600, output_tokens=120)
            )
        ]

        mock_client.messages.create.side_effect = mock_messages

        extractor = LLMValidationExtractor()
        rules = extractor.extract_all_validations(sample_spec)

        # Verify
        assert len(rules) == 3
        assert extractor.total_api_calls == 3
        assert extractor.total_tokens_used == 1800

        # Check rule types
        assert any(r.type == ValidationType.FORMAT for r in rules)
        assert any(r.type == ValidationType.RELATIONSHIP for r in rules)

    def test_prompt_field_validation_structure(self):
        """Test field validation prompt structure."""
        extractor = LLMValidationExtractor()

        field_contexts = [
            {
                "entity": "User",
                "field_name": "email",
                "field_type": "String",
                "description": "User email",
                "constraints": {"unique": True},
                "required": True,
                "unique": True,
                "field": {}
            }
        ]

        prompt = extractor._create_field_validation_prompt(field_contexts)

        assert "email" in prompt
        assert "User" in prompt
        assert "FORMAT" in prompt
        assert "UNIQUENESS" in prompt
        assert "confidence" in prompt

    def test_prompt_endpoint_validation_structure(self):
        """Test endpoint validation prompt structure."""
        extractor = LLMValidationExtractor()

        endpoints = [
            {"method": "GET", "path": "/users/{id}"},
            {"method": "POST", "path": "/users", "request_body": {"email": "string"}}
        ]
        entities = [{"name": "User"}]

        prompt = extractor._create_endpoint_validation_prompt(endpoints, entities)

        assert "/users/{id}" in prompt
        assert "GET" in prompt
        assert "POST" in prompt
        assert "User" in prompt

    def test_prompt_cross_entity_validation_structure(self):
        """Test cross-entity validation prompt structure."""
        extractor = LLMValidationExtractor()

        spec = {
            "entities": [
                {"name": "User", "fields": [{"name": "id", "type": "UUID"}]},
                {"name": "Todo", "fields": [{"name": "user_id", "type": "UUID"}]}
            ],
            "endpoints": [{"method": "GET", "path": "/todos"}],
            "workflows": [{"name": "order_processing"}]
        }

        prompt = extractor._create_cross_entity_validation_prompt(spec)

        assert "User" in prompt
        assert "Todo" in prompt
        assert "RELATIONSHIP" in prompt
        assert "STATUS_TRANSITION" in prompt
        assert "order_processing" in prompt
