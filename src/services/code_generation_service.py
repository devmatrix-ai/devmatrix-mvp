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
        max_retries: int = 3
    ):
        """
        Initialize code generation service.

        Args:
            db: Database session
            llm_client: LLM client (creates new if not provided)
            max_retries: Maximum retry attempts per task
        """
        self.db = db
        self.llm_client = llm_client or EnhancedAnthropicClient()
        self.max_retries = max_retries

        logger.info(
            "CodeGenerationService initialized",
            extra={"max_retries": max_retries}
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

        # Build prompt
        prompt = self._build_prompt(task)

        # Generate with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Attempting code generation",
                    extra={
                        "task_id": str(task_id),
                        "attempt": attempt,
                        "max_retries": self.max_retries
                    }
                )

                # Call LLM
                response = await self.llm_client.generate_with_caching(
                    task_type="code_generation",
                    complexity="medium",
                    cacheable_context={
                        "system_prompt": self._get_system_prompt()
                    },
                    variable_prompt=prompt,
                    temperature=0.3,  # Lower temperature for more consistent code
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
                        "cost_usd": task.llm_cost_usd
                    }
                )

                return {
                    "success": True,
                    "code_length": len(code),
                    "tokens": task.llm_tokens_input + task.llm_tokens_output,
                    "cost_usd": task.llm_cost_usd,
                    "attempt": attempt
                }

            except Exception as e:
                logger.error(
                    "Code generation attempt failed",
                    extra={
                        "task_id": str(task_id),
                        "attempt": attempt,
                        "error": str(e)
                    },
                    exc_info=True
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
