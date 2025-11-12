"""
Retry Orchestrator for MGE V2 Execution

Intelligent retry logic with temperature backoff and error feedback.
"""

import asyncio
import logging
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
from uuid import UUID

from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
from src.mge.v2.validation.atomic_validator import AtomicValidator, AtomicValidationResult
from src.mge.v2.validation.models import ValidationSeverity
from .metrics import (
    RETRY_ATTEMPTS_TOTAL,
    RETRY_TEMPERATURE_CHANGES,
    update_success_rate,
)

# Optional tracing support
try:
    from src.mge.v2.tracing import TraceCollector
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    TraceCollector = None

logger = logging.getLogger(__name__)


@dataclass
class RetryResult:
    """Result of retry execution."""
    code: str
    validation_result: AtomicValidationResult
    attempts_used: int
    success: bool
    error_message: Optional[str] = None


class RetryOrchestrator:
    """
    Orchestrates code generation with intelligent retry logic.

    Features:
    - 4 attempts total (1 initial + 3 retries)
    - Temperature backoff: 0.7 → 0.5 → 0.3 → 0.3
    - Error feedback to LLM on retries
    - Success early-exit
    - Prometheus metrics emission
    """

    MAX_ATTEMPTS = 4
    TEMPERATURE_SCHEDULE = [0.7, 0.5, 0.3, 0.3]  # Initial + 3 retries

    def __init__(
        self,
        llm_client: EnhancedAnthropicClient,
        validator: AtomicValidator,
        trace_collector: Optional['TraceCollector'] = None
    ):
        """
        Initialize RetryOrchestrator.

        Args:
            llm_client: LLM client for code generation
            validator: Validator for generated code
            trace_collector: Optional trace collector for E2E tracing
        """
        self.llm_client = llm_client
        self.validator = validator
        self.trace_collector = trace_collector

    async def execute_with_retry(
        self,
        atom_spec,  # AtomicUnit type (avoiding circular import)
        dependencies: List,  # List[AtomicUnit]
        masterplan_id: Optional[UUID] = None
    ) -> RetryResult:
        """
        Execute code generation with retry loop.

        Args:
            atom_spec: Atomic unit specification
            dependencies: List of dependency atoms (already generated)
            masterplan_id: Optional masterplan ID for invalidation

        Returns:
            RetryResult with code, validation, and attempt count
        """
        errors = []
        code = ""
        validation_result = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            temperature = self.TEMPERATURE_SCHEDULE[attempt - 1]
            attempt_start = time.time()

            logger.info(
                f"Attempt {attempt}/{self.MAX_ATTEMPTS} for {atom_spec.name} "
                f"(temperature={temperature})"
            )

            # Emit temperature change metric
            if attempt > 1:
                prev_temp = self.TEMPERATURE_SCHEDULE[attempt - 2]
                RETRY_TEMPERATURE_CHANGES.labels(
                    from_temp=str(prev_temp),
                    to_temp=str(temperature)
                ).inc()

            try:
                # Generate code
                code = await self._generate_code(
                    atom_spec=atom_spec,
                    dependencies=dependencies,
                    temperature=temperature,
                    attempt_number=attempt,
                    previous_errors=errors if attempt > 1 else None,
                    masterplan_id=masterplan_id
                )

                # Update atom with generated code
                atom_spec.code = code

                # Validate
                validation_result = await self.validator.validate(atom_spec)

                # Calculate attempt duration
                attempt_duration_ms = (time.time() - attempt_start) * 1000

                # Emit retry attempt metric
                RETRY_ATTEMPTS_TOTAL.labels(
                    atom_id=str(atom_spec.id),
                    attempt_number=str(attempt)
                ).inc()

                # Record retry attempt in trace
                if self.trace_collector and hasattr(atom_spec, 'id'):
                    self.trace_collector.record_retry_attempt(
                        atom_id=atom_spec.id,
                        attempt=attempt,
                        temperature=temperature,
                        success=validation_result.passed,
                        duration_ms=attempt_duration_ms,
                        error_feedback=errors if attempt > 1 else None
                    )

                if validation_result.passed:
                    logger.info(f"✅ Success on attempt {attempt} for {atom_spec.name}")
                    update_success_rate()
                    return RetryResult(
                        code=code,
                        validation_result=validation_result,
                        attempts_used=attempt,
                        success=True
                    )

                # Failed - collect errors for next attempt
                errors = [
                    issue.message
                    for issue in validation_result.issues
                    if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
                ]

                logger.warning(
                    f"❌ Attempt {attempt} failed for {atom_spec.name}: "
                    f"{len(errors)} error(s)"
                )

            except Exception as e:
                logger.error(f"Exception during attempt {attempt} for {atom_spec.name}: {e}")
                errors.append(f"Exception: {str(e)}")

                # Calculate attempt duration
                attempt_duration_ms = (time.time() - attempt_start) * 1000

                # Emit retry attempt metric
                RETRY_ATTEMPTS_TOTAL.labels(
                    atom_id=str(atom_spec.id),
                    attempt_number=str(attempt)
                ).inc()

                # Record failed retry attempt in trace
                if self.trace_collector and hasattr(atom_spec, 'id'):
                    self.trace_collector.record_retry_attempt(
                        atom_id=atom_spec.id,
                        attempt=attempt,
                        temperature=temperature,
                        success=False,
                        duration_ms=attempt_duration_ms,
                        error_feedback=[str(e)]
                    )

        # All attempts failed
        logger.error(
            f"⚠️ All {self.MAX_ATTEMPTS} attempts failed for {atom_spec.name}"
        )
        update_success_rate()

        return RetryResult(
            code=code,
            validation_result=validation_result or self._create_failure_result(errors),
            attempts_used=self.MAX_ATTEMPTS,
            success=False,
            error_message=f"Failed after {self.MAX_ATTEMPTS} attempts: {'; '.join(errors[:3])}"
        )

    async def _generate_code(
        self,
        atom_spec,
        dependencies: List,
        temperature: float,
        attempt_number: int,
        previous_errors: Optional[List[str]],
        masterplan_id: Optional[UUID]
    ) -> str:
        """
        Generate code using LLM client.

        Args:
            atom_spec: Atomic unit specification
            dependencies: Dependency atoms
            temperature: Temperature for generation
            attempt_number: Current attempt number
            previous_errors: Errors from previous attempts
            masterplan_id: Masterplan ID for caching

        Returns:
            Generated code
        """
        # Build prompt
        prompt = self._build_prompt(
            atom_spec=atom_spec,
            dependencies=dependencies,
            attempt_number=attempt_number,
            previous_errors=previous_errors
        )

        # Build cacheable context (static parts)
        cacheable_context = {
            "system_prompt": self._build_system_prompt(atom_spec),
            "dependencies": self._format_dependencies(dependencies),
        }

        # Call LLM with caching
        response = await self.llm_client.generate_with_caching(
            task_type="atom_code_generation",
            complexity=atom_spec.complexity if hasattr(atom_spec, "complexity") else "medium",
            cacheable_context=cacheable_context,
            variable_prompt=prompt,
            temperature=temperature,
            max_tokens=4096,
            masterplan_id=str(masterplan_id) if masterplan_id else None
        )

        # Extract code from response
        code = response.get("content", "")
        return self._extract_code(code)

    def _build_system_prompt(self, atom_spec) -> str:
        """Build system prompt for LLM."""
        language = atom_spec.language if hasattr(atom_spec, "language") else "Python"

        return f"""You are an expert {language} developer.
Your task is to generate high-quality, production-ready code that:
1. Follows {language} best practices and conventions
2. Includes proper type hints and docstrings
3. Is atomic and focused (single responsibility)
4. Uses dependencies correctly
5. Passes all validation checks"""

    def _build_prompt(
        self,
        atom_spec,
        dependencies: List,
        attempt_number: int,
        previous_errors: Optional[List[str]]
    ) -> str:
        """Build generation prompt."""
        # Extract atom info
        name = atom_spec.name if hasattr(atom_spec, "name") else "unknown"
        description = atom_spec.description if hasattr(atom_spec, "description") else ""
        estimated_loc = atom_spec.estimated_loc if hasattr(atom_spec, "estimated_loc") else 15
        language = atom_spec.language if hasattr(atom_spec, "language") else "Python"

        prompt = f"""**Task**: Generate code for this atomic unit:
- **Name**: {name}
- **Description**: {description}
- **Target LOC**: ~{estimated_loc} lines
- **Language**: {language}

**Requirements**:
1. Generate ONLY the code for this specific unit
2. Use dependencies shown (already validated)
3. Follow {language} conventions
4. Include type hints and docstrings
5. Keep it atomic (~{estimated_loc} LOC)
6. Ensure code is syntactically correct and complete
"""

        # Add context if available
        if hasattr(atom_spec, "context") and atom_spec.context:
            context = atom_spec.context
            if "file_context" in context:
                file_ctx = context["file_context"]
                prompt += f"\n**File Context**:\n"
                prompt += f"- File: {file_ctx.get('file_path', 'N/A')}\n"
                if "imports" in file_ctx:
                    prompt += f"- Imports: {file_ctx.get('imports', [])}\n"

            if "parent_context" in context and context["parent_context"]:
                prompt += f"- Parent scope: {context['parent_context']}\n"

        # Add retry information if this is a retry
        if attempt_number > 1 and previous_errors:
            prompt += f"""

**RETRY ATTEMPT {attempt_number}**:
Previous generation failed with these errors:
{chr(10).join(f'- {err}' for err in previous_errors[:5])}

Please fix these issues in this attempt.
"""

        prompt += "\n\nGenerate the code now:"

        return prompt

    def _format_dependencies(self, dependencies: List) -> str:
        """Format dependencies for context."""
        if not dependencies:
            return "# No dependencies"

        formatted = []
        for dep in dependencies[:10]:  # Max 10 for context
            name = dep.name if hasattr(dep, "name") else "unknown"
            code = dep.code if hasattr(dep, "code") else ""

            if code:
                formatted.append(f"# {name}")
                formatted.append(code)
                formatted.append("")

        if len(dependencies) > 10:
            formatted.append(f"# ... and {len(dependencies) - 10} more dependencies")

        return "\n".join(formatted)

    def _extract_code(self, response_text: str) -> str:
        """Extract code from LLM response."""
        # Remove markdown code blocks
        if "```" in response_text:
            parts = response_text.split("```")
            for i, part in enumerate(parts):
                # Odd indices are code blocks
                if i % 2 == 1:
                    lines = part.strip().split('\n')
                    # Skip language identifier if present
                    if lines and lines[0].strip() in [
                        "python", "typescript", "javascript", "js", "ts", "jsx", "tsx"
                    ]:
                        lines = lines[1:]
                    return '\n'.join(lines)

        # No code blocks, return as is
        return response_text.strip()

    def _create_failure_result(self, errors: List[str]) -> AtomicValidationResult:
        """Create a validation result for failure case."""
        from src.mge.v2.validation.models import ValidationIssue

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="retry_failure",
                message=f"All retry attempts failed: {error}",
                location={"line": 0, "column": 0}
            )
            for error in errors[:3]
        ]

        return AtomicValidationResult(
            passed=False,
            issues=issues,
            metrics={}
        )
