"""Prompt Strategy Pattern - File-type-specific prompt generation."""

from dataclasses import dataclass
from typing import Optional, List, Any
from src.services.file_type_detector import FileType, FileTypeDetection


@dataclass
class PromptContext:
    """Context for prompt generation."""
    task_number: int
    task_name: str
    task_description: str
    complexity: str
    file_type_detection: FileTypeDetection
    last_error: Optional[str] = None
    similar_errors: Optional[List[Any]] = None
    successful_patterns: Optional[List[Any]] = None


class PromptStrategy:
    """Base strategy for prompt generation."""

    def generate_prompt(self, context: PromptContext) -> str:
        """Generate basic prompt for task."""
        return f"""# Task {context.task_number}: {context.task_name}

{context.task_description}

Complexity: {context.complexity}
File Type: {context.file_type_detection.file_type.value}

Generate complete, working code for this task."""

    def generate_prompt_with_feedback(self, context: PromptContext) -> str:
        """Generate prompt with error feedback."""
        prompt_parts = []

        if context.last_error:
            prompt_parts.append(f"PREVIOUS ATTEMPT FAILED: {context.last_error}\n")

        if context.similar_errors:
            prompt_parts.append("Similar errors from history:")
            for err in context.similar_errors[:3]:
                prompt_parts.append(f"- {err.error_message}")
            prompt_parts.append("")

        if context.successful_patterns:
            prompt_parts.append("Successful patterns for similar tasks:")
            for pattern in context.successful_patterns[:3]:
                prompt_parts.append(f"- {pattern.get('task_description', 'N/A')}")
            prompt_parts.append("")

        # Add base prompt
        prompt_parts.append(self.generate_prompt(context))

        return "\n".join(prompt_parts)


class PromptStrategyFactory:
    """Factory for creating file-type-specific prompt strategies."""

    @staticmethod
    def get_strategy(file_type: FileType) -> PromptStrategy:
        """Get appropriate strategy for file type."""
        # For now, return same strategy for all types
        # Can be extended with Python/JavaScript/TypeScript specific strategies
        return PromptStrategy()
