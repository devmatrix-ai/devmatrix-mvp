"""Validation Strategy Pattern - File-type-specific code validation."""

from src.services.file_type_detector import FileType


class ValidationStrategy:
    """Base strategy for code validation."""

    def validate(self, code: str) -> tuple[bool, str]:
        """
        Validate code syntax.

        Args:
            code: Code to validate

        Returns:
            (is_valid, error_message) tuple
        """
        try:
            compile(code, "<generated>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Compilation error: {str(e)}"


class ValidationStrategyFactory:
    """Factory for creating file-type-specific validation strategies."""

    @staticmethod
    def get_strategy(file_type: FileType) -> ValidationStrategy:
        """Get appropriate validation strategy for file type."""
        # For now, return same strategy for all types
        # Can be extended with JavaScript/TypeScript specific validators
        return ValidationStrategy()
