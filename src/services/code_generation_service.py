"""
Code Generation Service - MGE V2

Generates actual code for MasterPlan tasks using LLM.
This is the missing step between MasterPlan generation and Atomization.

Flow:
1. MasterPlan Generator creates tasks with descriptions
2. Code Generation Service generates code for each task (THIS SERVICE)
3. Atomization Service parses generated code into atoms
4. Wave Executor runs atoms in parallel

Author: DevMatrix Team
Date: 2025-11-10
"""

import uuid
import asyncio
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from src.models import MasterPlanTask
from src.llm import EnhancedAnthropicClient
from src.observability import StructuredLogger
from src.services.error_pattern_store import (
    ErrorPatternStore,
    ErrorPattern,
    SuccessPattern,
    get_error_pattern_store
)

logger = StructuredLogger("code_generation_service", output_json=True)


class CodeGenerationService:
    """
    Service for generating code from task descriptions using LLM.

    Features:
    - Task-specific prompt engineering
    - Retry logic with exponential backoff
    - Code extraction and validation
    - Token usage tracking
    - Support for multiple languages
    """

    def __init__(
        self,
        db: Session,
        llm_client: Optional[EnhancedAnthropicClient] = None,
        max_retries: int = 3,
        enable_feedback_loop: bool = True
    ):
        """
        Initialize code generation service.

        Args:
            db: Database session
            llm_client: LLM client (creates new if not provided)
            max_retries: Maximum retry attempts per task
            enable_feedback_loop: Enable cognitive feedback loop for learning
        """
        self.db = db
        self.llm_client = llm_client or EnhancedAnthropicClient()
        self.max_retries = max_retries
        self.enable_feedback_loop = enable_feedback_loop

        # Initialize error pattern store for cognitive feedback loop
        self.pattern_store = None
        if enable_feedback_loop:
            try:
                self.pattern_store = get_error_pattern_store()
                logger.info("Cognitive feedback loop enabled")
            except Exception as e:
                logger.warning(f"Could not initialize feedback loop: {e}")
                self.enable_feedback_loop = False

        logger.info(
            "CodeGenerationService initialized",
            extra={"max_retries": max_retries, "feedback_loop": self.enable_feedback_loop}
        )

    async def generate_code_for_task(self, task_id: uuid.UUID) -> Dict[str, Any]:
        """
        Generate code for a single task.

        Args:
            task_id: Task UUID

        Returns:
            Dict with generation results
        """
        logger.info(
            "Starting code generation",
            extra={"task_id": str(task_id)}
        )

        # Load task
        task = self.db.query(MasterPlanTask).filter(
            MasterPlanTask.task_id == task_id
        ).first()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Check if already generated
        if task.llm_response:
            logger.info(
                "Task already has generated code",
                extra={"task_id": str(task_id)}
            )
            return {
                "success": True,
                "already_generated": True,
                "code_length": len(task.llm_response)
            }

        # Track errors and code for feedback loop
        last_error = None
        last_code = None

        # Generate with retries (now with cognitive feedback loop)
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Attempting code generation",
                    extra={
                        "task_id": str(task_id),
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "feedback_loop": self.enable_feedback_loop and attempt > 1
                    }
                )

                # On retry attempts, consult cognitive feedback loop
                if attempt > 1 and self.enable_feedback_loop and self.pattern_store and last_error:
                    logger.info(
                        "Consulting cognitive feedback loop for retry",
                        extra={"task_id": str(task_id), "attempt": attempt}
                    )

                    # Search for similar errors in history
                    similar_errors = await self.pattern_store.search_similar_errors(
                        task_description=task.description,
                        error_message=str(last_error),
                        top_k=3
                    )

                    # Search for successful patterns
                    successful_patterns = await self.pattern_store.search_successful_patterns(
                        task_description=task.description,
                        top_k=5
                    )

                    logger.info(
                        "RAG feedback retrieved",
                        extra={
                            "task_id": str(task_id),
                            "similar_errors_found": len(similar_errors),
                            "successful_patterns_found": len(successful_patterns)
                        }
                    )

                    # Build enhanced prompt with feedback
                    prompt = self._build_prompt_with_feedback(
                        task,
                        similar_errors,
                        successful_patterns,
                        str(last_error)
                    )
                else:
                    # First attempt - use standard prompt
                    prompt = self._build_prompt(task)

                # Call LLM
                response = await self.llm_client.generate_with_caching(
                    task_type="code_generation",
                    complexity="medium",
                    cacheable_context={
                        "system_prompt": self._get_system_prompt()
                    },
                    variable_prompt=prompt,
                    temperature=0.0,  # Deterministic mode for reproducible precision
                    max_tokens=2000
                )

                # Extract code from response
                code = self._extract_code(response.get("content", ""))

                if not code:
                    raise ValueError("No code found in LLM response")

                # Validate code syntax (basic check)
                if not self._validate_code_syntax(code, task):
                    raise ValueError("Generated code has invalid syntax")

                # Update task in database
                task.llm_prompt = prompt
                task.llm_response = code
                task.llm_model = response.get("model", "claude-sonnet-4-5")
                task.llm_tokens_input = response.get("usage", {}).get("input_tokens", 0)
                task.llm_tokens_output = response.get("usage", {}).get("output_tokens", 0)
                task.llm_cached_tokens = response.get("usage", {}).get("cache_read_input_tokens", 0)
                task.llm_cost_usd = self._calculate_cost(response)

                self.db.commit()
                self.db.refresh(task)

                logger.info(
                    "Code generation successful",
                    extra={
                        "task_id": str(task_id),
                        "code_length": len(code),
                        "tokens_input": task.llm_tokens_input,
                        "tokens_output": task.llm_tokens_output,
                        "cost_usd": task.llm_cost_usd,
                        "attempt": attempt
                    }
                )

                # Store successful pattern in cognitive feedback loop
                if self.enable_feedback_loop and self.pattern_store:
                    try:
                        success_pattern = SuccessPattern(
                            success_id=str(uuid.uuid4()),
                            task_id=str(task_id),
                            task_description=task.description,
                            generated_code=code,
                            quality_score=1.0,  # Will be updated by quality analyzer
                            timestamp=datetime.now(),
                            metadata={
                                "task_name": task.name,
                                "complexity": task.complexity,
                                "attempt": attempt,
                                "used_feedback": attempt > 1
                            }
                        )
                        await self.pattern_store.store_success(success_pattern)
                        logger.info(
                            "Stored successful pattern in feedback loop",
                            extra={"task_id": str(task_id)}
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to store success pattern",
                            extra={"task_id": str(task_id), "error": str(e)}
                        )

                return {
                    "success": True,
                    "code_length": len(code),
                    "tokens": task.llm_tokens_input + task.llm_tokens_output,
                    "cost_usd": task.llm_cost_usd,
                    "attempt": attempt,
                    "used_feedback_loop": attempt > 1 and self.enable_feedback_loop
                }

            except Exception as e:
                last_error = e
                last_code = None

                logger.error(
                    "Code generation attempt failed",
                    extra={
                        "task_id": str(task_id),
                        "attempt": attempt,
                        "error": str(e)
                    },
                    exc_info=True
                )

                # Store error pattern in cognitive feedback loop
                if self.enable_feedback_loop and self.pattern_store:
                    try:
                        error_pattern = ErrorPattern(
                            error_id=str(uuid.uuid4()),
                            task_id=str(task_id),
                            task_description=task.description,
                            error_type="syntax_error" if "syntax" in str(e).lower() else "validation_error",
                            error_message=str(e),
                            failed_code=last_code or "",
                            attempt=attempt,
                            timestamp=datetime.now(),
                            metadata={
                                "task_name": task.name,
                                "complexity": task.complexity
                            }
                        )
                        await self.pattern_store.store_error(error_pattern)
                        logger.info(
                            "Stored error pattern in feedback loop",
                            extra={"task_id": str(task_id), "attempt": attempt}
                        )
                    except Exception as store_error:
                        logger.warning(
                            "Failed to store error pattern",
                            extra={"task_id": str(task_id), "error": str(store_error)}
                        )

                if attempt == self.max_retries:
                    # Final attempt failed, save error
                    task.last_error = f"Code generation failed after {self.max_retries} attempts: {str(e)}"
                    self.db.commit()

                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt
                    }

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        return {"success": False, "error": "Max retries exceeded"}

    def _build_prompt(self, task: MasterPlanTask) -> str:
        """
        Build task-specific prompt for code generation.

        Args:
            task: MasterPlan task

        Returns:
            Formatted prompt string
        """
        # Get target language
        language = self._detect_language(task)

        prompt = f"""Generate production-ready code for the following task:

**Task #{task.task_number}: {task.name}**

**Description**: {task.description}

**Requirements**:
- Language: {language}
- Target LOC: 50-100 lines
- Include proper imports
- Add type hints/annotations
- Include docstrings
- Follow best practices for {language}

**Complexity**: {task.complexity}

Generate ONLY the code, wrapped in a code block with the language specified.
Do not include explanations or additional text outside the code block."""

        return prompt

    def _build_prompt_with_feedback(
        self,
        task: MasterPlanTask,
        similar_errors: list,
        successful_patterns: list,
        last_error: str
    ) -> str:
        """
        Build enhanced prompt with RAG feedback from error patterns.

        Args:
            task: MasterPlan task
            similar_errors: List of similar historical errors
            successful_patterns: List of successful code patterns
            last_error: Error from previous attempt

        Returns:
            Enhanced prompt with learning feedback
        """
        language = self._detect_language(task)

        # Build base prompt
        prompt = f"""Generate production-ready code for the following task:

**Task #{task.task_number}: {task.name}**

**Description**: {task.description}

**Requirements**:
- Language: {language}
- Target LOC: 50-100 lines
- Include proper imports
- Add type hints/annotations
- Include docstrings
- Follow best practices for {language}

**Complexity**: {task.complexity}

---

**IMPORTANT - LEARN FROM PREVIOUS MISTAKES**:

**Previous Attempt Failed With**: {last_error}
"""

        # Add similar error patterns if available
        if similar_errors:
            prompt += "\n**⚠️ Similar Errors Found in History**:\n"
            for i, err in enumerate(similar_errors[:3], 1):
                prompt += f"\n{i}. Task: '{err.task_description}'\n"
                prompt += f"   Error: {err.error_message}\n"
                prompt += f"   Similarity: {err.similarity_score:.2%}\n"
                if err.failed_code:
                    prompt += f"   Failed Code Pattern: {err.failed_code[:200]}...\n"

        # Add successful patterns if available
        if successful_patterns:
            prompt += "\n**✅ Successful Patterns for Similar Tasks**:\n"
            for i, pattern in enumerate(successful_patterns[:3], 1):
                prompt += f"\n{i}. Task: '{pattern['task_description']}'\n"
                prompt += f"   Similarity: {pattern['similarity_score']:.2%}\n"
                prompt += f"   Quality Score: {pattern['quality_score']:.2f}/1.0\n"
                if pattern.get('generated_code'):
                    prompt += f"   Code Pattern:\n```{language}\n{pattern['generated_code'][:400]}\n```\n"

        prompt += """
---

**ACTION REQUIRED**:
1. Analyze the error from the previous attempt
2. Review similar historical errors to avoid the same mistakes
3. Study the successful patterns provided above
4. Generate CORRECT code that avoids these known pitfalls

Generate ONLY the code, wrapped in a code block with the language specified.
Do not include explanations or additional text outside the code block."""

        return prompt

    def _get_system_prompt(self) -> str:
        """Get system prompt for code generation."""
        return """You are an expert software engineer specialized in generating high-quality, production-ready code.

Your task is to generate complete, working code based on task descriptions. Follow these principles:

1. **Code Quality**:
   - Write clean, readable code
   - Follow language-specific best practices
   - Use meaningful variable and function names
   - Add appropriate comments for complex logic

2. **Structure**:
   - Include all necessary imports
   - Add type hints/annotations
   - Include docstrings for functions and classes
   - Handle errors appropriately

3. **Output Format**:
   - Wrap code in markdown code blocks with language specified
   - Example: ```python\\ncode here\\n```
   - Do not include explanations outside code blocks

4. **Scope**:
   - Generate 50-100 lines of code per task
   - Focus on the specific task requirements
   - Create complete, runnable code units

Generate code that is ready to be parsed and executed without modifications."""

    def _extract_code(self, content: str) -> str:
        """
        Extract code from LLM response (handles markdown code blocks).

        Args:
            content: LLM response content

        Returns:
            Extracted code
        """
        # Pattern for markdown code blocks
        pattern = r'```(?:\w+)?\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            # Return first code block
            return matches[0].strip()

        # If no code block found, return entire content
        return content.strip()

    def _validate_code_syntax(self, code: str, task: MasterPlanTask) -> bool:
        """
        Basic syntax validation.

        Args:
            code: Generated code
            task: Task for context

        Returns:
            True if code appears valid
        """
        # Basic checks
        if len(code) < 10:
            return False

        # Check for common code patterns
        has_structure = any([
            'def ' in code,      # Python function
            'class ' in code,    # Python/Java class
            'function ' in code, # JavaScript
            'const ' in code,    # JavaScript/TypeScript
            'import ' in code,   # Import statement
            'from ' in code,     # Python import
        ])

        return has_structure

    def _detect_language(self, task: MasterPlanTask) -> str:
        """
        Detect programming language for task.

        Args:
            task: MasterPlan task

        Returns:
            Language name (python, javascript, etc.)
        """
        # Check target files
        if task.target_files:
            file_path = task.target_files[0].lower()

            if file_path.endswith('.py'):
                return 'python'
            elif file_path.endswith(('.js', '.jsx')):
                return 'javascript'
            elif file_path.endswith(('.ts', '.tsx')):
                return 'typescript'
            elif file_path.endswith('.java'):
                return 'java'
            elif file_path.endswith('.go'):
                return 'go'

        # Check task name/description for language hints
        name_lower = task.name.lower()
        desc_lower = task.description.lower()

        if 'fastapi' in desc_lower or 'pydantic' in desc_lower or 'sqlalchemy' in name_lower:
            return 'python'
        elif 'react' in desc_lower or 'jsx' in desc_lower:
            return 'javascript'
        elif 'typescript' in desc_lower or 'tsx' in desc_lower:
            return 'typescript'

        # Default to python
        return 'python'

    def _calculate_cost(self, response: Dict[str, Any]) -> float:
        """
        Calculate LLM API cost.

        Args:
            response: LLM response with usage data

        Returns:
            Cost in USD
        """
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cached_tokens = usage.get("cache_read_input_tokens", 0)

        # Sonnet 4.5 pricing
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        cache_cost = (cached_tokens / 1_000_000) * 0.3  # Cache reads are cheaper

        return round(input_cost + output_cost + cache_cost, 4)
