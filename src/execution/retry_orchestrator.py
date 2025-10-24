"""
RetryOrchestrator - Smart retry logic with temperature adjustment

Orchestrates retry attempts for failed atoms with adaptive temperature,
error analysis, and feedback generation.

Author: DevMatrix Team
Date: 2025-10-24
"""

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from sqlalchemy.orm import Session

from ..models import AtomicUnit
from ..observability import StructuredLogger


logger = StructuredLogger("retry_orchestrator", output_json=True)


class ErrorCategory(Enum):
    """Error categories for analysis"""
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    LOGIC_ERROR = "logic_error"
    TIMEOUT = "timeout"
    DEPENDENCY_ERROR = "dependency_error"
    CONTEXT_INSUFFICIENT = "context_insufficient"
    UNKNOWN = "unknown"


@dataclass
class RetryAttempt:
    """Record of a single retry attempt"""
    attempt_number: int
    temperature: float
    error_category: ErrorCategory
    error_message: str
    feedback_prompt: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = False


@dataclass
class RetryHistory:
    """Complete retry history for an atom"""
    atom_id: uuid.UUID
    total_attempts: int
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_success: bool = False
    total_retry_time_seconds: float = 0.0


class RetryOrchestrator:
    """
    Orchestrates retry logic for failed atom executions.

    Features:
    - Adaptive temperature adjustment (0.7 → 0.5 → 0.3)
    - Error category analysis
    - Exponential backoff strategy
    - Feedback prompt generation
    - Retry history tracking
    - Configurable max attempts
    """

    # Temperature schedule: attempt → temperature
    TEMPERATURE_SCHEDULE = {
        1: 0.7,  # First retry: creative
        2: 0.5,  # Second retry: balanced
        3: 0.3,  # Third retry: deterministic
    }

    # Backoff schedule: attempt → seconds
    BACKOFF_SCHEDULE = {
        1: 1.0,   # 1 second
        2: 2.0,   # 2 seconds
        3: 4.0,   # 4 seconds
    }

    def __init__(
        self,
        db: Session,
        max_attempts: int = 3,
        enable_backoff: bool = True
    ):
        """
        Initialize RetryOrchestrator

        Args:
            db: Database session
            max_attempts: Maximum retry attempts per atom (default: 3)
            enable_backoff: Enable exponential backoff (default: True)
        """
        self.db = db
        self.max_attempts = max_attempts
        self.enable_backoff = enable_backoff

        # Retry history tracking
        self._retry_histories: Dict[uuid.UUID, RetryHistory] = {}

    async def retry_atom(
        self,
        atom: AtomicUnit,
        error: str,
        attempt: int,
        code_generator: Optional[Any] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        Retry failed atom execution with adaptive strategy

        Args:
            atom: Failed atom to retry
            error: Error message from previous attempt
            attempt: Current attempt number (1-indexed)
            code_generator: Optional code generation function

        Returns:
            Tuple of (success, generated_code, feedback_message)
        """
        if attempt > self.max_attempts:
            logger.warning(
                f"Max retry attempts ({self.max_attempts}) exceeded for atom {atom.atom_id}",
                extra={
                    "atom_id": str(atom.atom_id),
                    "attempt": attempt
                }
            )
            return False, None, f"Max retry attempts ({self.max_attempts}) exceeded"

        logger.info(
            f"Retrying atom {atom.atom_id} (attempt {attempt}/{self.max_attempts})",
            extra={
                "atom_id": str(atom.atom_id),
                "attempt": attempt,
                "max_attempts": self.max_attempts,
                "error": error[:100]  # Log first 100 chars
            }
        )

        # Analyze error
        error_category = self.analyze_error(error)

        # Get temperature for this attempt
        temperature = self.adjust_temperature(attempt)

        # Apply backoff if enabled
        if self.enable_backoff:
            backoff_time = self.apply_backoff(attempt)
            if backoff_time > 0:
                logger.debug(f"Applying backoff: {backoff_time}s")
                time.sleep(backoff_time)

        # Generate retry prompt with feedback
        retry_prompt = self.generate_retry_prompt(atom, error, error_category)

        # Track attempt
        retry_attempt = RetryAttempt(
            attempt_number=attempt,
            temperature=temperature,
            error_category=error_category,
            error_message=error,
            feedback_prompt=retry_prompt
        )

        # Attempt code generation with adjusted temperature
        success = False
        generated_code = None

        try:
            if code_generator:
                # Call code generator with retry context
                generated_code = await code_generator(
                    atom=atom,
                    retry_count=attempt,
                    temperature=temperature,
                    feedback=retry_prompt
                )
                success = True
                retry_attempt.success = True

                # Update atom
                atom.generated_code = generated_code
                atom.status = "completed"
                atom.completed_at = datetime.utcnow()
                self.db.commit()

                logger.info(
                    f"Atom {atom.atom_id} retry succeeded (attempt {attempt})",
                    extra={
                        "atom_id": str(atom.atom_id),
                        "attempt": attempt,
                        "temperature": temperature
                    }
                )

            else:
                # Mock for testing
                success = True
                generated_code = f"# Retried code (attempt {attempt})"
                retry_attempt.success = True

        except Exception as e:
            logger.error(
                f"Atom {atom.atom_id} retry failed (attempt {attempt}): {str(e)}",
                extra={
                    "atom_id": str(atom.atom_id),
                    "attempt": attempt,
                    "error": str(e)
                },
                exc_info=True
            )
            retry_attempt.success = False

        # Track retry attempt
        self._track_retry_attempt(atom.atom_id, retry_attempt)

        feedback_message = retry_prompt if not success else "Retry successful"

        return success, generated_code, feedback_message

    def analyze_error(self, error: str) -> ErrorCategory:
        """
        Analyze error message and categorize

        Args:
            error: Error message string

        Returns:
            ErrorCategory classification
        """
        error_lower = error.lower()

        # Syntax errors
        if any(keyword in error_lower for keyword in [
            'syntaxerror', 'syntax error', 'invalid syntax',
            'unexpected token', 'parsing error'
        ]):
            return ErrorCategory.SYNTAX_ERROR

        # Type errors
        if any(keyword in error_lower for keyword in [
            'typeerror', 'type error', 'type mismatch',
            'cannot convert', 'incompatible type'
        ]):
            return ErrorCategory.TYPE_ERROR

        # Logic errors
        if any(keyword in error_lower for keyword in [
            'logic error', 'assertion failed', 'incorrect result',
            'validation failed', 'test failed'
        ]):
            return ErrorCategory.LOGIC_ERROR

        # Timeout errors
        if any(keyword in error_lower for keyword in [
            'timeout', 'time out', 'timed out', 'deadline exceeded'
        ]):
            return ErrorCategory.TIMEOUT

        # Dependency errors
        if any(keyword in error_lower for keyword in [
            'dependencies not satisfied', 'dependency', 'missing import',
            'module not found', 'cannot find'
        ]):
            return ErrorCategory.DEPENDENCY_ERROR

        # Context insufficient
        if any(keyword in error_lower for keyword in [
            'context', 'information missing', 'insufficient',
            'needs more context'
        ]):
            return ErrorCategory.CONTEXT_INSUFFICIENT

        return ErrorCategory.UNKNOWN

    def adjust_temperature(self, attempt: int) -> float:
        """
        Get temperature for retry attempt

        Temperature schedule:
        - Attempt 1: 0.7 (creative, explore alternatives)
        - Attempt 2: 0.5 (balanced approach)
        - Attempt 3: 0.3 (deterministic, conservative)

        Args:
            attempt: Retry attempt number (1-indexed)

        Returns:
            Temperature value (0.0-1.0)
        """
        temperature = self.TEMPERATURE_SCHEDULE.get(attempt, 0.3)

        logger.debug(
            f"Temperature for attempt {attempt}: {temperature}",
            extra={"attempt": attempt, "temperature": temperature}
        )

        return temperature

    def apply_backoff(self, attempt: int) -> float:
        """
        Calculate backoff time for retry attempt

        Backoff schedule:
        - Attempt 1: 1 second
        - Attempt 2: 2 seconds
        - Attempt 3: 4 seconds

        Args:
            attempt: Retry attempt number (1-indexed)

        Returns:
            Backoff time in seconds
        """
        if not self.enable_backoff:
            return 0.0

        backoff = self.BACKOFF_SCHEDULE.get(attempt, 4.0)

        logger.debug(
            f"Backoff for attempt {attempt}: {backoff}s",
            extra={"attempt": attempt, "backoff_seconds": backoff}
        )

        return backoff

    def generate_retry_prompt(
        self,
        atom: AtomicUnit,
        error: str,
        error_category: ErrorCategory
    ) -> str:
        """
        Generate feedback prompt for retry attempt

        Args:
            atom: Failed atom
            error: Error message
            error_category: Categorized error type

        Returns:
            Feedback prompt string
        """
        # Base prompt with error context
        prompt = f"""Previous attempt failed with {error_category.value}.

Error: {error}

Original task:
- Description: {atom.description}
- File: {atom.file_path}
- Language: {atom.language}

"""

        # Category-specific guidance
        if error_category == ErrorCategory.SYNTAX_ERROR:
            prompt += """Focus on:
- Correct syntax for {language}
- Proper indentation and structure
- Missing or extra brackets, parentheses
- Correct use of keywords and operators
""".format(language=atom.language)

        elif error_category == ErrorCategory.TYPE_ERROR:
            prompt += """Focus on:
- Type consistency and compatibility
- Proper type annotations (if applicable)
- Type conversions and casting
- Interface/contract adherence
"""

        elif error_category == ErrorCategory.LOGIC_ERROR:
            prompt += """Focus on:
- Algorithm correctness
- Edge case handling
- Input validation
- Expected vs actual behavior
"""

        elif error_category == ErrorCategory.TIMEOUT:
            prompt += """Focus on:
- Algorithm efficiency (reduce complexity)
- Avoid infinite loops
- Optimize nested iterations
- Consider early returns
"""

        elif error_category == ErrorCategory.DEPENDENCY_ERROR:
            prompt += """Focus on:
- Required imports/dependencies
- Module availability
- Correct dependency names
- Import order and structure
"""

        elif error_category == ErrorCategory.CONTEXT_INSUFFICIENT:
            prompt += """Focus on:
- Using available context effectively
- Making reasonable assumptions
- Simplifying requirements if needed
- Core functionality first
"""

        else:
            prompt += """Focus on:
- Review error message carefully
- Address root cause
- Simplify approach if complex
- Test incrementally
"""

        prompt += f"\nAttempt to generate correct code for: {atom.description}"

        return prompt

    def _track_retry_attempt(
        self,
        atom_id: uuid.UUID,
        attempt: RetryAttempt
    ):
        """
        Track retry attempt in history

        Args:
            atom_id: Atom ID
            attempt: RetryAttempt record
        """
        if atom_id not in self._retry_histories:
            self._retry_histories[atom_id] = RetryHistory(
                atom_id=atom_id,
                total_attempts=0
            )

        history = self._retry_histories[atom_id]
        history.attempts.append(attempt)
        history.total_attempts += 1

        if attempt.success:
            history.final_success = True

    def track_retry_history(self, atom_id: uuid.UUID) -> Optional[RetryHistory]:
        """
        Get retry history for an atom

        Args:
            atom_id: Atom ID

        Returns:
            RetryHistory or None if no history
        """
        return self._retry_histories.get(atom_id)

    def get_retry_statistics(self) -> Dict[str, Any]:
        """
        Get overall retry statistics

        Returns:
            Statistics dictionary with retry metrics
        """
        if not self._retry_histories:
            return {
                "total_atoms_retried": 0,
                "total_attempts": 0,
                "success_rate": 0.0,
                "avg_attempts_to_success": 0.0,
                "error_categories": {}
            }

        total_atoms = len(self._retry_histories)
        total_attempts = sum(h.total_attempts for h in self._retry_histories.values())
        successful_atoms = sum(1 for h in self._retry_histories.values() if h.final_success)

        # Calculate average attempts to success
        successful_histories = [h for h in self._retry_histories.values() if h.final_success]
        avg_attempts = (
            sum(h.total_attempts for h in successful_histories) / len(successful_histories)
            if successful_histories else 0.0
        )

        # Count error categories
        error_categories: Dict[str, int] = {}
        for history in self._retry_histories.values():
            for attempt in history.attempts:
                cat = attempt.error_category.value
                error_categories[cat] = error_categories.get(cat, 0) + 1

        return {
            "total_atoms_retried": total_atoms,
            "total_attempts": total_attempts,
            "successful_atoms": successful_atoms,
            "success_rate": (successful_atoms / total_atoms * 100) if total_atoms > 0 else 0.0,
            "avg_attempts_to_success": avg_attempts,
            "error_categories": error_categories,
            "max_attempts": self.max_attempts
        }

    def reset_history(self):
        """Reset all retry history"""
        self._retry_histories.clear()
        logger.info("Retry history reset")
