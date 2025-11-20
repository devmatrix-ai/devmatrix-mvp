"""File Type Detector - Determines file type from task context."""

from enum import Enum
from typing import Optional, List
from dataclasses import dataclass


class FileType(Enum):
    """Supported file types for code generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


@dataclass
class FileTypeDetection:
    """Result of file type detection."""
    file_type: FileType
    confidence: float
    reasoning: str


class FileTypeDetector:
    """
    Detects file type from task context.

    Stub implementation for E2E testing.
    """

    def detect(
        self,
        task_name: str,
        task_description: str,
        target_files: Optional[List[str]] = None
    ) -> FileTypeDetection:
        """
        Detect file type from task context.

        Args:
            task_name: Name of the task
            task_description: Description of what needs to be done
            target_files: Optional list of target file paths

        Returns:
            FileTypeDetection with file type and confidence
        """
        # Check target files first
        if target_files:
            for file_path in target_files:
                if file_path.endswith('.py'):
                    return FileTypeDetection(
                        file_type=FileType.PYTHON,
                        confidence=0.95,
                        reasoning="Target file has .py extension"
                    )
                elif file_path.endswith(('.js', '.jsx')):
                    return FileTypeDetection(
                        file_type=FileType.JAVASCRIPT,
                        confidence=0.95,
                        reasoning="Target file has .js/.jsx extension"
                    )
                elif file_path.endswith(('.ts', '.tsx')):
                    return FileTypeDetection(
                        file_type=FileType.TYPESCRIPT,
                        confidence=0.95,
                        reasoning="Target file has .ts/.tsx extension"
                    )

        # Fallback to Python for most cases
        return FileTypeDetection(
            file_type=FileType.PYTHON,
            confidence=0.7,
            reasoning="Default to Python for unspecified file type"
        )


# Singleton instance
_detector_instance: Optional[FileTypeDetector] = None


def get_file_type_detector() -> FileTypeDetector:
    """Get singleton file type detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = FileTypeDetector()
    return _detector_instance
