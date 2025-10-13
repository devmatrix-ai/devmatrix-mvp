"""
Tests for Anthropic Claude API Client
"""

import os
import pytest
from unittest.mock import Mock, MagicMock
from src.llm.anthropic_client import AnthropicClient


class TestAnthropicClient:
    """Test suite for AnthropicClient."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        client = AnthropicClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert client.model == "claude-3-5-sonnet-20241022"

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization with environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env_key_456")
        client = AnthropicClient()
        assert client.api_key == "env_key_456"

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            AnthropicClient()

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        client = AnthropicClient(api_key="test_key", model="claude-3-opus-20240229")
        assert client.model == "claude-3-opus-20240229"

    def test_generate_basic(self, monkeypatch):
        """Test basic text generation."""
        # Mock the Anthropic client
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello, how can I help?")]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = Mock(input_tokens=10, output_tokens=20)
        mock_response.stop_reason = "end_turn"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test_key", enable_cache=False)
        monkeypatch.setattr(client, "client", mock_client)

        result = client.generate(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are a helpful assistant"
        )

        assert result["content"] == "Hello, how can I help?"
        assert result["model"] == "claude-3-5-sonnet-20241022"
        assert result["usage"]["input_tokens"] == 10
        assert result["usage"]["output_tokens"] == 20
        assert result["stop_reason"] == "end_turn"

        # Verify API call
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert call_kwargs["max_tokens"] == 4096
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["system"] == "You are a helpful assistant"
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]

    def test_generate_with_custom_params(self, monkeypatch):
        """Test generation with custom parameters."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = Mock(input_tokens=5, output_tokens=10)
        mock_response.stop_reason = "end_turn"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test_key", enable_cache=False)
        monkeypatch.setattr(client, "client", mock_client)

        result = client.generate(
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=2000,
            temperature=0.3
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 2000
        assert call_kwargs["temperature"] == 0.3

    def test_generate_api_error(self, monkeypatch):
        """Test generation handles API errors."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")

        client = AnthropicClient(api_key="test_key", enable_cache=False)
        monkeypatch.setattr(client, "client", mock_client)

        with pytest.raises(RuntimeError, match="Anthropic API error: API Error"):
            client.generate(messages=[{"role": "user", "content": "Test"}])

    def test_generate_with_tools(self, monkeypatch):
        """Test generation with tool use."""
        # Mock response with tool call
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Let me search for that."

        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "tool_123"
        mock_tool_block.name = "search"
        mock_tool_block.input = {"query": "weather"}

        mock_response = Mock()
        mock_response.content = [mock_text_block, mock_tool_block]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = Mock(input_tokens=15, output_tokens=25)
        mock_response.stop_reason = "tool_use"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test_key")
        monkeypatch.setattr(client, "client", mock_client)

        tools = [{"name": "search", "description": "Search tool"}]
        result = client.generate_with_tools(
            messages=[{"role": "user", "content": "What's the weather?"}],
            tools=tools
        )

        assert result["content"] == "Let me search for that."
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "tool_123"
        assert result["tool_calls"][0]["name"] == "search"
        assert result["tool_calls"][0]["input"] == {"query": "weather"}
        assert result["stop_reason"] == "tool_use"

        # Verify tools passed to API
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tools"] == tools

    def test_generate_with_tools_no_tool_calls(self, monkeypatch):
        """Test generation with tools but no tool calls."""
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "The weather is sunny."

        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = Mock(input_tokens=10, output_tokens=15)
        mock_response.stop_reason = "end_turn"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test_key")
        monkeypatch.setattr(client, "client", mock_client)

        tools = [{"name": "search", "description": "Search tool"}]
        result = client.generate_with_tools(
            messages=[{"role": "user", "content": "What's the weather?"}],
            tools=tools
        )

        assert result["content"] == "The weather is sunny."
        assert result["tool_calls"] == []
        assert result["stop_reason"] == "end_turn"

    def test_generate_with_tools_api_error(self, monkeypatch):
        """Test tool generation handles API errors."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Tool API Error")

        client = AnthropicClient(api_key="test_key")
        monkeypatch.setattr(client, "client", mock_client)

        with pytest.raises(RuntimeError, match="Anthropic API error: Tool API Error"):
            client.generate_with_tools(
                messages=[{"role": "user", "content": "Test"}],
                tools=[]
            )

    def test_count_tokens(self):
        """Test token counting estimation."""
        client = AnthropicClient(api_key="test_key")

        # ~4 characters per token
        assert client.count_tokens("Hello") == 1  # 5 chars = 1 token
        assert client.count_tokens("Hello world") == 2  # 11 chars = 2 tokens
        assert client.count_tokens("A" * 100) == 25  # 100 chars = 25 tokens

    def test_calculate_cost(self):
        """Test cost calculation in EUR."""
        client = AnthropicClient(api_key="test_key")

        # Claude 3.5 Sonnet: $3 per 1M input, $15 per 1M output
        # USD to EUR ~0.92

        # 1M input tokens = $3 * 0.92 = 2.76 EUR
        cost = client.calculate_cost(input_tokens=1_000_000, output_tokens=0)
        assert abs(cost - 2.76) < 0.01

        # 1M output tokens = $15 * 0.92 = 13.8 EUR
        cost = client.calculate_cost(input_tokens=0, output_tokens=1_000_000)
        assert abs(cost - 13.8) < 0.01

        # Combined: 100k input + 50k output
        # Input: (100k / 1M) * 3 * 0.92 = 0.276 EUR
        # Output: (50k / 1M) * 15 * 0.92 = 0.69 EUR
        # Total: 0.966 EUR
        cost = client.calculate_cost(input_tokens=100_000, output_tokens=50_000)
        assert abs(cost - 0.966) < 0.01

    def test_calculate_cost_small_values(self):
        """Test cost calculation with small token counts."""
        client = AnthropicClient(api_key="test_key")

        # Small request: 100 input, 200 output
        cost = client.calculate_cost(input_tokens=100, output_tokens=200)
        assert cost > 0
        assert cost < 0.01  # Should be very small
