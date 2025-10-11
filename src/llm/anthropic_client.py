"""
Anthropic Claude Client

Wrapper for Anthropic API with retry logic and error handling.
"""

import os
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AnthropicClient:
    """
    Anthropic Claude API client.

    Usage:
        client = AnthropicClient()
        response = client.generate(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are a helpful assistant"
        )
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model to use (default: claude-3-5-sonnet-20241022)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. "
                "Set it in .env file or pass as argument."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional API parameters

        Returns:
            Dictionary with response data including content and usage
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
                **kwargs
            )

            return {
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
            }

        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}") from e

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate completion with tool use.

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            system: System prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Dictionary with response including tool calls if any
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
                tools=tools,
            )

            # Parse response for tool calls
            tool_calls = []
            text_content = ""

            for content_block in response.content:
                if content_block.type == "text":
                    text_content += content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    })

            return {
                "content": text_content,
                "tool_calls": tool_calls,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
            }

        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}") from e

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in EUR for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in EUR
        """
        # Claude 3.5 Sonnet pricing (as of 2024)
        # Input: $3 per 1M tokens
        # Output: $15 per 1M tokens
        input_cost_eur = (input_tokens / 1_000_000) * 3 * 0.92  # USD to EUR ~0.92
        output_cost_eur = (output_tokens / 1_000_000) * 15 * 0.92

        return input_cost_eur + output_cost_eur
