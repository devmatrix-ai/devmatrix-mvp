"""
Retry Logic - LLM-Powered Intelligent Retry

Analyzes execution failures and determines retry strategy with LLM feedback.

Features:
- Error pattern analysis
- LLM-based code correction
- Retry decision making
- Progressive retry strategies
- Learning from failures

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re

from .code_executor import ExecutionResult
from src.models import AtomicUnit

logger = logging.getLogger(__name__)


@dataclass
class RetryDecision:
    """Decision on whether and how to retry"""
    should_retry: bool
    retry_strategy: str  # 'regenerate', 'fix', 'skip', 'manual'
    reason: str
    suggested_fix: Optional[str] = None
    llm_feedback: Optional[str] = None
    max_retries_reached: bool = False
    confidence: float = 0.0  # 0.0-1.0


@dataclass
class RetryHistory:
    """History of retry attempts for an atom"""
    atom_id: uuid.UUID
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    total_attempts: int = 0
    last_error: Optional[str] = None
    error_patterns: List[str] = field(default_factory=list)


class RetryLogic:
    """
    Retry logic - LLM-powered intelligent retry

    Retry strategies:
    1. **Regenerate**: Generate completely new code (for unclear errors)
    2. **Fix**: Apply targeted fix to existing code (for clear errors)
    3. **Skip**: Skip this atom if non-critical
    4. **Manual**: Requires manual intervention

    Error categories:
    - Syntax errors: Quick fix (add missing brackets, etc.)
    - Import errors: Add missing imports
    - Type errors: Fix type mismatches
    - Runtime errors: Analyze and fix logic
    - Timeout errors: Optimize code
    """

    def __init__(
        self,
        max_retries: int = 3,
        use_llm: bool = True,
        auto_fix: bool = True
    ):
        """
        Initialize retry logic

        Args:
            max_retries: Maximum retry attempts per atom
            use_llm: Use LLM for code correction
            auto_fix: Attempt automatic fixes
        """
        self.max_retries = max_retries
        self.use_llm = use_llm
        self.auto_fix = auto_fix
        self.retry_history: Dict[uuid.UUID, RetryHistory] = {}

        logger.info(f"RetryLogic initialized (max_retries={max_retries}, use_llm={use_llm}, auto_fix={auto_fix})")

    def analyze_failure(
        self,
        atom: AtomicUnit,
        execution_result: ExecutionResult
    ) -> RetryDecision:
        """
        Analyze execution failure and decide retry strategy

        Args:
            atom: Failed atomic unit
            execution_result: Execution result with error details

        Returns:
            RetryDecision with retry strategy
        """
        logger.info(f"Analyzing failure for atom: {atom.atom_id}")

        # Get retry history
        if atom.atom_id not in self.retry_history:
            self.retry_history[atom.atom_id] = RetryHistory(atom_id=atom.atom_id)

        history = self.retry_history[atom.atom_id]

        # Check max retries
        if history.total_attempts >= self.max_retries:
            return RetryDecision(
                should_retry=False,
                retry_strategy='manual',
                reason=f"Max retries ({self.max_retries}) reached",
                max_retries_reached=True
            )

        # Categorize error
        error_category = self._categorize_error(execution_result)
        logger.debug(f"Error category: {error_category}")

        # Decide strategy based on error category
        if error_category == "syntax":
            decision = self._handle_syntax_error(atom, execution_result)
        elif error_category == "import":
            decision = self._handle_import_error(atom, execution_result)
        elif error_category == "type":
            decision = self._handle_type_error(atom, execution_result)
        elif error_category == "runtime":
            decision = self._handle_runtime_error(atom, execution_result)
        elif error_category == "timeout":
            decision = self._handle_timeout_error(atom, execution_result)
        else:
            decision = RetryDecision(
                should_retry=True,
                retry_strategy='regenerate',
                reason=f"Unknown error category: {error_category}",
                confidence=0.3
            )

        # Update history
        history.attempts.append({
            'timestamp': datetime.utcnow().isoformat(),
            'error_category': error_category,
            'strategy': decision.retry_strategy,
            'error_message': execution_result.error_message
        })
        history.total_attempts += 1
        history.last_error = execution_result.error_message
        if error_category not in history.error_patterns:
            history.error_patterns.append(error_category)

        logger.info(f"Retry decision: {decision.retry_strategy} (confidence={decision.confidence:.2f})")
        return decision

    def _categorize_error(self, result: ExecutionResult) -> str:
        """Categorize error type from execution result"""
        error_msg = (result.stderr or '') + (result.error_message or '')

        # Syntax errors
        if 'SyntaxError' in error_msg or 'syntax error' in error_msg.lower():
            return 'syntax'

        # Import errors
        if 'ModuleNotFoundError' in error_msg or 'ImportError' in error_msg or 'Cannot find module' in error_msg:
            return 'import'

        # Type errors
        if 'TypeError' in error_msg or 'type error' in error_msg.lower():
            return 'type'

        # Timeout
        if result.exception_type == 'TimeoutError' or 'timed out' in error_msg.lower():
            return 'timeout'

        # Runtime errors (default)
        return 'runtime'

    def _handle_syntax_error(
        self,
        atom: AtomicUnit,
        result: ExecutionResult
    ) -> RetryDecision:
        """Handle syntax errors"""
        error_msg = result.stderr or result.error_message or ''

        # Common syntax fixes
        suggested_fix = None

        if 'unexpected EOF' in error_msg.lower():
            suggested_fix = "Add missing closing bracket/brace"
        elif 'invalid syntax' in error_msg.lower() and ':' in error_msg:
            # Try to extract line number
            match = re.search(r'line (\d+)', error_msg)
            if match:
                line_num = int(match.group(1))
                suggested_fix = f"Fix syntax error at line {line_num}"

        return RetryDecision(
            should_retry=True,
            retry_strategy='fix' if suggested_fix else 'regenerate',
            reason="Syntax error detected",
            suggested_fix=suggested_fix,
            confidence=0.8 if suggested_fix else 0.5
        )

    def _handle_import_error(
        self,
        atom: AtomicUnit,
        result: ExecutionResult
    ) -> RetryDecision:
        """Handle import errors"""
        error_msg = result.stderr or result.error_message or ''

        # Extract missing module
        missing_module = None
        if 'No module named' in error_msg:
            match = re.search(r"No module named '([^']+)'", error_msg)
            if match:
                missing_module = match.group(1)

        suggested_fix = None
        if missing_module:
            suggested_fix = f"Add import for '{missing_module}' or install package"

        return RetryDecision(
            should_retry=True,
            retry_strategy='fix',
            reason=f"Missing import: {missing_module}" if missing_module else "Import error",
            suggested_fix=suggested_fix,
            confidence=0.9 if missing_module else 0.6
        )

    def _handle_type_error(
        self,
        atom: AtomicUnit,
        result: ExecutionResult
    ) -> RetryDecision:
        """Handle type errors"""
        error_msg = result.stderr or result.error_message or ''

        # Extract type mismatch details
        suggested_fix = None
        if 'expected' in error_msg.lower() and 'got' in error_msg.lower():
            suggested_fix = "Fix type mismatch (check function signatures and variable types)"

        return RetryDecision(
            should_retry=True,
            retry_strategy='fix',
            reason="Type error detected",
            suggested_fix=suggested_fix,
            confidence=0.7
        )

    def _handle_runtime_error(
        self,
        atom: AtomicUnit,
        result: ExecutionResult
    ) -> RetryDecision:
        """Handle runtime errors"""
        error_msg = result.stderr or result.error_message or ''

        # Common runtime errors
        suggested_fix = None

        if 'division by zero' in error_msg.lower():
            suggested_fix = "Add check to prevent division by zero"
        elif 'NoneType' in error_msg and 'has no attribute' in error_msg:
            suggested_fix = "Add None check before attribute access"
        elif 'index out of range' in error_msg.lower():
            suggested_fix = "Add bounds checking for list/array access"
        elif 'KeyError' in error_msg:
            suggested_fix = "Add key existence check for dictionary access"

        # For unclear runtime errors, use LLM
        strategy = 'fix' if suggested_fix else 'regenerate' if self.use_llm else 'manual'

        return RetryDecision(
            should_retry=True,
            retry_strategy=strategy,
            reason="Runtime error detected",
            suggested_fix=suggested_fix,
            confidence=0.8 if suggested_fix else 0.4
        )

    def _handle_timeout_error(
        self,
        atom: AtomicUnit,
        result: ExecutionResult
    ) -> RetryDecision:
        """Handle timeout errors"""
        return RetryDecision(
            should_retry=True,
            retry_strategy='regenerate',
            reason="Execution timeout - code may have infinite loop or be too slow",
            suggested_fix="Optimize code: check for infinite loops, reduce complexity",
            confidence=0.6
        )

    def generate_llm_fix_prompt(
        self,
        atom: AtomicUnit,
        execution_result: ExecutionResult,
        decision: RetryDecision
    ) -> str:
        """
        Generate prompt for LLM to fix code

        Args:
            atom: Failed atom
            execution_result: Execution result
            decision: Retry decision

        Returns:
            Prompt string for LLM
        """
        prompt = f"""Fix the following code that failed execution:

**Original Code:**
```{atom.language}
{atom.generated_code}
```

**Execution Error:**
```
{execution_result.stderr or execution_result.error_message}
```

**Error Analysis:**
- Error Category: {decision.reason}
- Suggested Fix: {decision.suggested_fix or 'Analyze and fix'}

**Requirements:**
1. Fix the error while maintaining the original intent
2. Keep the code atomic (≤15 LOC, complexity <3.0)
3. Add necessary imports
4. Add error handling if needed
5. Test that the fix resolves the specific error

**Return only the corrected code, no explanations.**
"""
        return prompt

    def apply_auto_fix(
        self,
        atom: AtomicUnit,
        decision: RetryDecision
    ) -> Optional[str]:
        """
        Apply automatic fix to code

        Args:
            atom: Atom to fix
            decision: Retry decision with suggested fix

        Returns:
            Fixed code or None if auto-fix not possible
        """
        if not self.auto_fix or not decision.suggested_fix:
            return None

        code = atom.generated_code

        # Apply simple automatic fixes
        if 'Add missing closing bracket' in decision.suggested_fix:
            # Count brackets
            open_count = code.count('(') + code.count('[') + code.count('{')
            close_count = code.count(')') + code.count(']') + code.count('}')

            if open_count > close_count:
                # Add missing closing brackets
                diff = open_count - close_count
                code += ')' * diff

        # Add more auto-fixes here as needed

        return code if code != atom.generated_code else None

    def get_retry_stats(self, masterplan_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Get retry statistics

        Args:
            masterplan_id: Optional filter by masterplan

        Returns:
            Dictionary with retry statistics
        """
        total_retries = sum(h.total_attempts for h in self.retry_history.values())
        max_retries_hit = sum(1 for h in self.retry_history.values() if h.total_attempts >= self.max_retries)

        error_counts = {}
        for history in self.retry_history.values():
            for pattern in history.error_patterns:
                error_counts[pattern] = error_counts.get(pattern, 0) + 1

        return {
            'total_atoms_with_retries': len(self.retry_history),
            'total_retry_attempts': total_retries,
            'avg_retries_per_atom': total_retries / len(self.retry_history) if self.retry_history else 0,
            'max_retries_reached': max_retries_hit,
            'error_patterns': error_counts
        }
