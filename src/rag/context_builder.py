"""
Context builder for RAG system.

This module formats retrieved code examples into structured context for LLM prompts.
It handles template formatting, token limiting, and metadata enrichment.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from src.rag.retriever import RetrievalResult
from src.config import RAG_MAX_CONTEXT_LENGTH
from src.observability import get_logger


class ContextTemplate(Enum):
    """Context formatting templates."""
    SIMPLE = "simple"  # Minimal formatting, just code
    DETAILED = "detailed"  # Code + metadata + explanations
    CONVERSATIONAL = "conversational"  # Natural language format
    STRUCTURED = "structured"  # XML-like structured format


@dataclass
class ContextConfig:
    """
    Configuration for context building.

    Attributes:
        template: Template to use for formatting
        max_length: Maximum context length in characters
        include_metadata: Whether to include metadata
        include_similarity: Whether to show similarity scores
        separator: Separator between examples
        truncate_code: Whether to truncate long code examples
        max_code_length: Maximum length per code example
    """
    template: ContextTemplate = ContextTemplate.DETAILED
    max_length: int = RAG_MAX_CONTEXT_LENGTH
    include_metadata: bool = True
    include_similarity: bool = True
    separator: str = "\n" + "="*80 + "\n"
    truncate_code: bool = False
    max_code_length: int = 1000


class ContextBuilder:
    """
    Formats retrieved examples into LLM-ready context.

    Provides flexible formatting with multiple templates, token limiting,
    and metadata enrichment for RAG-enhanced prompts.

    Attributes:
        config: Context building configuration
        logger: Structured logger
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        """
        Initialize context builder.

        Args:
            config: Optional context configuration
        """
        self.logger = get_logger("rag.context_builder")
        self.config = config or ContextConfig()

        self.logger.info(
            "ContextBuilder initialized",
            template=self.config.template.value,
            max_length=self.config.max_length
        )

    def build_context(
        self,
        query: str,
        results: List[RetrievalResult],
        template: Optional[ContextTemplate] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """
        Build formatted context from retrieval results.

        Args:
            query: Original query
            results: Retrieved code examples
            template: Template to use (overrides config)
            max_length: Max length in characters (overrides config)

        Returns:
            Formatted context string ready for LLM prompt

        Raises:
            ValueError: If inputs are invalid
        """
        if not results:
            self.logger.warning("No results to build context from")
            return ""

        effective_template = template or self.config.template
        effective_max_length = max_length or self.config.max_length

        try:
            self.logger.debug(
                "Building context",
                query_length=len(query),
                results_count=len(results),
                template=effective_template.value
            )

            # Select formatting function based on template
            if effective_template == ContextTemplate.SIMPLE:
                context = self._build_simple_context(results)
            elif effective_template == ContextTemplate.DETAILED:
                context = self._build_detailed_context(query, results)
            elif effective_template == ContextTemplate.CONVERSATIONAL:
                context = self._build_conversational_context(query, results)
            elif effective_template == ContextTemplate.STRUCTURED:
                context = self._build_structured_context(query, results)
            else:
                raise ValueError(f"Unknown template: {effective_template}")

            # Truncate if needed
            if len(context) > effective_max_length:
                context = self._truncate_context(context, effective_max_length)
                self.logger.warning(
                    "Context truncated",
                    original_length=len(context),
                    max_length=effective_max_length
                )

            self.logger.info(
                "Context built",
                context_length=len(context),
                results_count=len(results)
            )

            return context

        except Exception as e:
            self.logger.error(
                "Failed to build context",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _build_simple_context(self, results: List[RetrievalResult]) -> str:
        """
        Build simple context with minimal formatting.

        Args:
            results: Retrieved examples

        Returns:
            Simple formatted context
        """
        examples = []

        for i, result in enumerate(results, 1):
            code = self._maybe_truncate_code(result.code)
            examples.append(f"Example {i}:\n{code}")

        return self.config.separator.join(examples)

    def _build_detailed_context(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> str:
        """
        Build detailed context with metadata and explanations.

        Args:
            query: Original query
            results: Retrieved examples

        Returns:
            Detailed formatted context
        """
        parts = [
            "# Retrieved Code Examples",
            f"\nQuery: {query}",
            f"Found {len(results)} relevant example(s):\n"
        ]

        for i, result in enumerate(results, 1):
            example_parts = [f"\n## Example {i} (Rank {result.rank})"]

            # Add similarity if configured
            if self.config.include_similarity:
                example_parts.append(
                    f"**Relevance**: {result.similarity:.2f} "
                    f"(Score: {result.relevance_score:.2f})"
                )

            # Add metadata if configured
            if self.config.include_metadata and result.metadata:
                metadata_str = self._format_metadata(result.metadata)
                if metadata_str:
                    example_parts.append(f"**Metadata**: {metadata_str}")

            # Add code
            code = self._maybe_truncate_code(result.code)
            example_parts.append(f"\n```\n{code}\n```")

            parts.append("\n".join(example_parts))

        return "\n".join(parts)

    def _build_conversational_context(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> str:
        """
        Build conversational context in natural language.

        Args:
            query: Original query
            results: Retrieved examples

        Returns:
            Conversational formatted context
        """
        if not results:
            return f"I couldn't find any examples matching '{query}'."

        intro = (
            f"Based on your request '{query}', "
            f"I found {len(results)} relevant code example"
        )
        intro += "s:" if len(results) > 1 else ":"

        examples = []
        for i, result in enumerate(results, 1):
            # Extract language from metadata
            language = result.metadata.get("language", "code")

            example_intro = f"\n{i}. Here's a {language} example"

            # Add context from metadata
            if result.metadata.get("approved"):
                example_intro += " (verified and approved)"

            if self.config.include_similarity:
                similarity_pct = int(result.similarity * 100)
                example_intro += f" with {similarity_pct}% relevance"

            example_intro += ":"

            code = self._maybe_truncate_code(result.code)
            examples.append(f"{example_intro}\n\n```{language}\n{code}\n```")

        return intro + "\n".join(examples)

    def _build_structured_context(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> str:
        """
        Build structured context in XML-like format.

        Args:
            query: Original query
            results: Retrieved examples

        Returns:
            Structured formatted context
        """
        parts = [
            "<retrieved_examples>",
            f"  <query>{self._escape_xml(query)}</query>",
            f"  <count>{len(results)}</count>",
            "  <examples>"
        ]

        for result in results:
            parts.append(f'    <example id="{result.id}" rank="{result.rank}">')

            if self.config.include_similarity:
                parts.append(f"      <similarity>{result.similarity:.3f}</similarity>")
                parts.append(f"      <score>{result.relevance_score:.3f}</score>")

            if self.config.include_metadata and result.metadata:
                parts.append("      <metadata>")
                for key, value in result.metadata.items():
                    parts.append(f"        <{key}>{self._escape_xml(str(value))}</{key}>")
                parts.append("      </metadata>")

            code = self._maybe_truncate_code(result.code)
            parts.append(f"      <code><![CDATA[\n{code}\n      ]]></code>")
            parts.append("    </example>")

        parts.append("  </examples>")
        parts.append("</retrieved_examples>")

        return "\n".join(parts)

    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Format metadata dictionary into readable string.

        Args:
            metadata: Metadata dictionary

        Returns:
            Formatted metadata string
        """
        # Filter out internal/verbose fields
        exclude_keys = {"indexed_at", "code_length"}
        filtered = {
            k: v for k, v in metadata.items()
            if k not in exclude_keys
        }

        if not filtered:
            return ""

        parts = []
        for key, value in filtered.items():
            # Format key nicely
            formatted_key = key.replace("_", " ").title()
            parts.append(f"{formatted_key}: {value}")

        return ", ".join(parts)

    def _maybe_truncate_code(self, code: str) -> str:
        """
        Truncate code if configured and necessary.

        Args:
            code: Code string

        Returns:
            Original or truncated code
        """
        if not self.config.truncate_code:
            return code

        if len(code) <= self.config.max_code_length:
            return code

        truncated = code[:self.config.max_code_length]
        return truncated + "\n... (truncated)"

    def _truncate_context(self, context: str, max_length: int) -> str:
        """
        Truncate context to fit within max length.

        Args:
            context: Full context string
            max_length: Maximum allowed length

        Returns:
            Truncated context
        """
        if len(context) <= max_length:
            return context

        # Try to truncate at a natural boundary
        truncated = context[:max_length - 100]  # Leave room for message

        # Find last newline or separator
        last_newline = truncated.rfind("\n")
        if last_newline > max_length * 0.8:  # If reasonably close
            truncated = truncated[:last_newline]

        return truncated + "\n\n... (context truncated due to length)"

    def _escape_xml(self, text: str) -> str:
        """
        Escape XML special characters.

        Args:
            text: Text to escape

        Returns:
            XML-escaped text
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def build_system_prompt(
        self,
        task: str,
        results: List[RetrievalResult],
        instructions: Optional[str] = None,
    ) -> str:
        """
        Build complete system prompt with retrieved examples.

        Args:
            task: Task description
            results: Retrieved examples
            instructions: Optional additional instructions

        Returns:
            Complete system prompt string
        """
        parts = [
            "You are a helpful coding assistant. "
            "Use the following examples as reference for completing the task."
        ]

        if instructions:
            parts.append(f"\nInstructions: {instructions}")

        parts.append(f"\nTask: {task}")

        if results:
            context = self.build_context(task, results)
            parts.append(f"\n{context}")

            parts.append(
                "\nUse these examples as guidance, "
                "but adapt them appropriately to the specific task."
            )
        else:
            parts.append("\nNo specific examples found. Use your best judgment.")

        return "\n".join(parts)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).

        Uses simple heuristic: ~4 characters per token on average.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4

    def get_stats(self) -> Dict[str, Any]:
        """
        Get context builder statistics.

        Returns:
            Dictionary with configuration stats
        """
        return {
            "template": self.config.template.value,
            "max_length": self.config.max_length,
            "include_metadata": self.config.include_metadata,
            "include_similarity": self.config.include_similarity,
            "truncate_code": self.config.truncate_code,
            "max_code_length": self.config.max_code_length,
        }


def create_context_builder(
    template: ContextTemplate = ContextTemplate.DETAILED,
    max_length: int = RAG_MAX_CONTEXT_LENGTH,
) -> ContextBuilder:
    """
    Factory function to create a context builder instance.

    Args:
        template: Context template to use
        max_length: Maximum context length

    Returns:
        Initialized ContextBuilder instance
    """
    config = ContextConfig(
        template=template,
        max_length=max_length,
    )

    return ContextBuilder(config=config)
