"""
Pattern-Based Code Generation

Uses semantic pattern bank instead of hardcoded templates for flexible,
evolutionary code generation.

Usage:
    generator = PatternBasedGenerator(pattern_bank)
    dockerfile = await generator.generate_from_pattern(
        purpose="Generate production-ready Dockerfile for FastAPI application",
        context={"project_name": "my_api", "python_version": "3.11"}
    )
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


@dataclass
class GenerationContext:
    """Context for pattern-based generation."""

    project_name: str
    api_version: str = "v1"
    python_version: str = "3.11"
    database_url: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


class PatternBasedGenerator:
    """
    Generates code using patterns from pattern bank instead of templates.

    Benefits:
    - No hardcoded templates
    - Patterns evolve with usage
    - LLM adapts patterns to context
    - Searchable by semantic similarity
    """

    def __init__(
        self,
        pattern_bank: PatternBank,
        llm_client: ClaudeClient,
        use_llm_adaptation: bool = True
    ):
        """
        Initialize pattern-based generator.

        Args:
            pattern_bank: Pattern bank for searching patterns
            llm_client: LLM client for adapting patterns to context
            use_llm_adaptation: If True, use LLM to adapt patterns (default: True)
                                If False, just substitute placeholders
        """
        self.pattern_bank = pattern_bank
        self.llm_client = llm_client
        self.use_llm_adaptation = use_llm_adaptation

    async def generate_from_pattern(
        self,
        purpose: str,
        context: GenerationContext,
        domain: str = "infrastructure",
        fallback_to_llm: bool = True
    ) -> str:
        """
        Generate code by searching for similar pattern and adapting it to context.

        Process:
        1. Create semantic signature from purpose
        2. Search pattern bank for similar patterns
        3. If found: Adapt pattern to context (LLM or simple substitution)
        4. If not found: Generate from scratch with LLM (if fallback enabled)

        Args:
            purpose: What to generate (e.g., "Generate Dockerfile for FastAPI")
            context: Generation context with variables
            domain: Pattern domain (infrastructure, code, documentation)
            fallback_to_llm: If True, generate from scratch if no pattern found

        Returns:
            Generated code adapted to context

        Example:
            >>> context = GenerationContext(
            ...     project_name="ecommerce_api",
            ...     python_version="3.11"
            ... )
            >>> dockerfile = await generator.generate_from_pattern(
            ...     purpose="Generate production-ready Dockerfile for FastAPI application",
            ...     context=context,
            ...     domain="infrastructure"
            ... )
        """
        # 1. Create signature for pattern search
        signature = SemanticTaskSignature(
            purpose=purpose,
            intent="create",
            inputs=self._context_to_inputs(context),
            outputs={"file": "generated_file"},
            domain=domain
        )

        # 2. Search pattern bank
        logger.info(f"🔍 Searching pattern bank for: {purpose[:60]}...")
        patterns = self.pattern_bank.search_with_fallback(
            signature=signature,
            top_k=3,
            min_results=1
        )

        if not patterns:
            logger.warning(f"⚠️  No patterns found for: {purpose[:60]}")

            if fallback_to_llm:
                logger.info("🤖 Falling back to LLM generation from scratch...")
                return await self._generate_from_scratch(purpose, context, domain)
            else:
                raise ValueError(f"No pattern found for: {purpose}")

        # 3. Use best matching pattern
        best_pattern = patterns[0]
        logger.info(
            f"✅ Found pattern: {best_pattern.signature.purpose[:60]} "
            f"(similarity={best_pattern.similarity_score:.2%})"
        )

        # 4. Adapt pattern to context
        if self.use_llm_adaptation:
            # LLM adaptation: More flexible, handles complex transformations
            adapted_code = await self._adapt_pattern_with_llm(
                pattern_code=best_pattern.code,
                pattern_purpose=best_pattern.signature.purpose,
                context=context
            )
        else:
            # Simple substitution: Faster, but less flexible
            adapted_code = self._substitute_placeholders(
                pattern_code=best_pattern.code,
                context=context
            )

        return adapted_code

    def _context_to_inputs(self, context: GenerationContext) -> Dict[str, Any]:
        """Convert GenerationContext to signature inputs."""
        inputs = {
            "project_name": context.project_name,
            "api_version": context.api_version,
            "python_version": context.python_version
        }

        if context.database_url:
            inputs["database_url"] = context.database_url

        if context.additional_context:
            inputs.update(context.additional_context)

        return inputs

    async def _adapt_pattern_with_llm(
        self,
        pattern_code: str,
        pattern_purpose: str,
        context: GenerationContext
    ) -> str:
        """
        Adapt pattern to context using LLM.

        The LLM receives:
        - The pattern code (with placeholders like {{project_name}})
        - The target context (actual values)
        - Instructions to substitute and adapt

        Benefits over simple substitution:
        - Handles complex transformations
        - Can add context-specific logic
        - More intelligent adaptation
        """
        prompt = f"""You are adapting a code pattern to a specific project context.

**Pattern Purpose**: {pattern_purpose}

**Pattern Code (with placeholders)**:
```
{pattern_code}
```

**Target Context**:
- Project name: {context.project_name}
- API version: {context.api_version}
- Python version: {context.python_version}
{f"- Database URL: {context.database_url}" if context.database_url else ""}
{self._format_additional_context(context.additional_context) if context.additional_context else ""}

**Instructions**:
1. Replace all placeholders ({{{{var}}}}) with actual values from context
2. Adapt the code to fit the specific project needs
3. Keep the overall structure and best practices from the pattern
4. Return ONLY the adapted code, no explanations

**Output**: Return the complete adapted code."""

        # Call LLM
        response = await self.llm_client.generate(
            prompt=prompt,
            task_type="documentation",  # Low complexity task
            complexity="low"
        )

        # Extract code from response (handle code blocks if present)
        adapted_code = self._extract_code_from_response(response)

        return adapted_code

    def _substitute_placeholders(
        self,
        pattern_code: str,
        context: GenerationContext
    ) -> str:
        """
        Simple placeholder substitution without LLM.

        Replaces:
        - {{project_name}} → context.project_name
        - {{api_version}} → context.api_version
        - etc.

        Faster but less flexible than LLM adaptation.
        """
        substitutions = {
            "project_name": context.project_name,
            "api_version": context.api_version,
            "python_version": context.python_version,
        }

        if context.database_url:
            substitutions["database_url"] = context.database_url

        if context.additional_context:
            substitutions.update(context.additional_context)

        # Apply substitutions
        adapted_code = pattern_code
        for key, value in substitutions.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            adapted_code = adapted_code.replace(placeholder, str(value))

        return adapted_code

    async def _generate_from_scratch(
        self,
        purpose: str,
        context: GenerationContext,
        domain: str
    ) -> str:
        """
        Generate code from scratch when no pattern is found.

        Uses LLM with detailed instructions.
        """
        prompt = f"""Generate production-ready code for the following purpose:

**Purpose**: {purpose}

**Project Context**:
- Project name: {context.project_name}
- API version: {context.api_version}
- Python version: {context.python_version}
- Domain: {domain}
{f"- Database URL: {context.database_url}" if context.database_url else ""}
{self._format_additional_context(context.additional_context) if context.additional_context else ""}

**Requirements**:
1. Follow production best practices
2. Include proper error handling and validation
3. Add comprehensive docstrings
4. Use type hints where applicable
5. Make it secure and maintainable

**Output**: Return ONLY the code, no explanations."""

        response = await self.llm_client.generate(
            prompt=prompt,
            task_type="code_generation",
            complexity="medium"
        )

        return self._extract_code_from_response(response)

    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract code from LLM response.

        Handles:
        - Code blocks (```...```)
        - Plain text
        """
        # Check if response contains code blocks
        if "```" in response:
            # Extract code from first code block
            parts = response.split("```")
            if len(parts) >= 3:
                code_block = parts[1]
                # Remove language identifier (e.g., ```python)
                lines = code_block.split("\n")
                if lines[0].strip() in ["python", "yaml", "toml", "dockerfile", "makefile", ""]:
                    code = "\n".join(lines[1:])
                else:
                    code = code_block
                return code.strip()

        # No code blocks, return as-is
        return response.strip()

    def _format_additional_context(self, additional_context: Optional[Dict[str, Any]]) -> str:
        """Format additional context for prompt."""
        if not additional_context:
            return ""

        lines = []
        for key, value in additional_context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    async def generate_dockerfile(self, context: GenerationContext) -> str:
        """Generate Dockerfile using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate production-ready Dockerfile for FastAPI application",
            context=context,
            domain="infrastructure"
        )

    async def generate_docker_compose(self, context: GenerationContext) -> str:
        """Generate Docker Compose configuration using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate Docker Compose configuration with PostgreSQL, Redis, Prometheus, Grafana",
            context=context,
            domain="infrastructure"
        )

    async def generate_requirements_txt(self, context: GenerationContext) -> str:
        """Generate requirements.txt using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate requirements.txt with verified PyPI versions for production FastAPI app",
            context=context,
            domain="infrastructure"
        )

    async def generate_main_py(self, context: GenerationContext) -> str:
        """Generate main.py using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate FastAPI main.py with CORS, middleware, health checks, and metrics",
            context=context,
            domain="code"
        )

    async def generate_alembic_ini(self, context: GenerationContext) -> str:
        """Generate alembic.ini using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate Alembic configuration for database migrations with dual-driver support",
            context=context,
            domain="infrastructure"
        )

    async def generate_makefile(self, context: GenerationContext) -> str:
        """Generate Makefile using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate Makefile with common development commands (test, run, migrate, docker)",
            context=context,
            domain="infrastructure"
        )

    async def generate_prometheus_config(self, context: GenerationContext) -> str:
        """Generate Prometheus config using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate Prometheus scrape configuration for FastAPI metrics",
            context=context,
            domain="infrastructure"
        )

    async def generate_metrics_route(self, context: GenerationContext) -> str:
        """Generate metrics route using pattern bank."""
        return await self.generate_from_pattern(
            purpose="Generate Prometheus metrics route that imports metrics from middleware",
            context=context,
            domain="code"
        )


# Convenience function for quick usage
async def generate_from_pattern_bank(
    purpose: str,
    project_name: str,
    pattern_bank: PatternBank,
    llm_client: ClaudeClient,
    **kwargs
) -> str:
    """
    Quick helper to generate code from pattern bank.

    Example:
        >>> code = await generate_from_pattern_bank(
        ...     purpose="Generate Dockerfile for FastAPI",
        ...     project_name="my_api",
        ...     pattern_bank=pattern_bank,
        ...     llm_client=llm_client,
        ...     python_version="3.11"
        ... )
    """
    context = GenerationContext(
        project_name=project_name,
        additional_context=kwargs
    )

    generator = PatternBasedGenerator(pattern_bank, llm_client)

    return await generator.generate_from_pattern(
        purpose=purpose,
        context=context
    )
