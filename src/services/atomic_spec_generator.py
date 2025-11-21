"""
AtomicSpec Generator - Proactive Atomization (Fase 2)

Generates atomic specifications from MasterPlanTask BEFORE code generation.

Flow:
1. Receive MasterPlanTask + DiscoveryDocument
2. Generate N atomic specs (3-7 specs, ~10 LOC each)
3. Validate each spec (pre-generation validation)
4. Reject invalid specs and re-generate
5. Return validated specs ready for code generation

Integrates with Fase 1:
- temperature=0.0 (determinism)
- seed=42 (reproducibility)
- Prompt caching for efficiency

Author: DevMatrix Team
Date: 2025-11-12
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import logging

from src.models.masterplan import MasterPlanTask, DiscoveryDocument, TaskComplexity as DBTaskComplexity
from src.models.atomic_spec import AtomicSpec
from src.services.atomic_spec_validator import AtomicSpecValidator
from src.llm import EnhancedAnthropicClient, TaskType, TaskComplexity

logger = logging.getLogger(__name__)


# System Prompt for Atomic Spec Generation
ATOMIC_SPEC_SYSTEM_PROMPT = """You are an expert software architect specializing in atomic code decomposition.

IMPORTANT: Always respond in English, regardless of the input language.

Your task is to generate ATOMIC SPECIFICATIONS (not code!) for implementing tasks.

## Atomic Specification Philosophy:

Each spec MUST represent EXACTLY ~10 lines of code (LOC):
- **Target**: 10 LOC
- **Minimum**: 5 LOC
- **Maximum**: 15 LOC

## Atomicity Criteria:

1. **Single Responsibility**: ONE clear purpose (one action verb in description)
2. **Independence**: No shared state with sibling specs
3. **Testability**: Clear input/output with test cases
4. **Complexity**: Cyclomatic complexity ≤ 3.0
5. **Type Safety**: Explicit input/output types
6. **Context Completeness**: All imports and dependencies specified
7. **Determinism**: Same input → same output
8. **Purity** (preferred): No side effects when possible

## Output Format:

Return a JSON array of AtomicSpec objects. Each spec must follow this structure:

```json
[
  {
    "description": "Validate user email format using regex pattern",
    "input_types": {
      "email": "str"
    },
    "output_type": "bool",
    "target_loc": 10,
    "complexity_limit": 2.0,
    "imports_required": [
      "import re"
    ],
    "dependencies": [],
    "preconditions": [
      "email is not None",
      "email is str"
    ],
    "postconditions": [
      "returns True if valid email format",
      "returns False if invalid email format"
    ],
    "test_cases": [
      {
        "input": {"email": "test@example.com"},
        "output": true
      },
      {
        "input": {"email": "invalid-email"},
        "output": false
      }
    ],
    "must_be_pure": true,
    "must_be_idempotent": true,
    "language": "python"
  }
]
```

## Guidelines:

- Break tasks into **3-7 atomic specs**
- Each spec = ~10 LOC of actual implementation
- Specs must be **independently executable**
- Provide **at least 1 test case** per spec
- Use **explicit types** (Python type hints, TypeScript types, etc.)
- Specify **all required imports**
- Define **clear preconditions/postconditions**
- **Prefer pure functions** when possible
- **One action verb** per description (create, validate, transform, etc.)

## CRITICAL Rules:

1. **Return ONLY valid JSON**, no markdown, no explanations outside the JSON
2. **Each spec must be atomic** (10 LOC target, max 15)
3. **Test cases are MANDATORY** (at least 1 per spec)
4. **Types are MANDATORY** (input_types and output_type)
5. **Description must be concise** (max 200 chars, one responsibility)

## Example Task Breakdown:

**Task**: "Create User SQLAlchemy model with validation"

**Breakdown into Atomic Specs**:
1. "Import SQLAlchemy base classes and types" (3 LOC)
2. "Define User class with table name and primary key" (5 LOC)
3. "Add email field with unique constraint" (7 LOC)
4. "Add password_hash field with validation" (8 LOC)
5. "Add timestamp fields (created_at, updated_at)" (6 LOC)

Total: 5 specs, ~29 LOC (reasonable for a model with validation)
"""


class AtomicSpecGenerator:
    """
    AtomicSpec Generator - Proactive atomization

    Generates atomic specifications from MasterPlanTask BEFORE code generation.

    Usage:
        generator = AtomicSpecGenerator()
        specs = await generator.generate_specs_from_task(task, discovery)

        # specs is a list of validated AtomicSpec instances
        for spec in specs:
            # Generate code from spec (Fase 3)
            code = await code_generator.generate(spec)
    """

    def __init__(
        self,
        llm_client: Optional[EnhancedAnthropicClient] = None,
        validator: Optional[AtomicSpecValidator] = None,
        max_retries: int = 3
    ):
        """
        Initialize generator

        Args:
            llm_client: LLM client for generation (creates new if None)
            validator: Spec validator (creates new if None)
            max_retries: Maximum retry attempts for invalid specs
        """
        self.llm = llm_client or EnhancedAnthropicClient()
        self.validator = validator or AtomicSpecValidator()
        self.max_retries = max_retries

        logger.info(
            f"AtomicSpecGenerator initialized (max_retries={max_retries})"
        )

    async def generate_specs_from_task(
        self,
        task: MasterPlanTask,
        discovery: DiscoveryDocument,
        retry_invalid: bool = True
    ) -> List[AtomicSpec]:
        """
        Generate atomic specs from a MasterPlanTask

        Args:
            task: MasterPlanTask to atomize
            discovery: Discovery context for generation
            retry_invalid: Whether to retry if specs are invalid

        Returns:
            List of validated AtomicSpec instances

        Raises:
            ValueError: If unable to generate valid specs after max_retries
        """
        logger.info(
            f"Generating atomic specs for task {task.task_number}: {task.name}"
        )

        attempt = 0
        last_invalid_specs = []

        while attempt < self.max_retries:
            attempt += 1

            try:
                # Generate specs with LLM
                specs = await self._generate_specs_llm(
                    task,
                    discovery,
                    retry_feedback=last_invalid_specs if attempt > 1 else None
                )

                logger.info(f"Generated {len(specs)} specs (attempt {attempt})")

                # Validate all specs
                valid_specs, invalid_specs = self.validator.validate_batch(specs)

                if len(invalid_specs) == 0:
                    # All specs valid - success!
                    logger.info(
                        f"✅ All {len(valid_specs)} specs validated successfully"
                    )

                    # Validate dependency graph
                    graph_valid, graph_errors = self.validator.validate_dependency_graph(specs)
                    if not graph_valid:
                        logger.warning(
                            f"Dependency graph validation failed: {graph_errors}"
                        )
                        if retry_invalid and attempt < self.max_retries:
                            logger.info("Retrying due to dependency graph errors...")
                            continue
                        else:
                            raise ValueError(
                                f"Dependency graph validation failed: {graph_errors}"
                            )

                    return valid_specs

                # Some specs invalid
                logger.warning(
                    f"⚠️  {len(invalid_specs)} invalid specs out of {len(specs)}"
                )

                for spec, result in invalid_specs:
                    logger.warning(
                        f"  - {spec.description}\n"
                        f"    Errors: {', '.join(result.errors)}"
                    )

                if not retry_invalid or attempt >= self.max_retries:
                    # Don't retry or max retries reached
                    break

                # Store invalid specs for feedback
                last_invalid_specs = invalid_specs
                logger.info(f"Retrying with validation feedback...")

            except Exception as e:
                logger.error(f"Error generating specs (attempt {attempt}): {e}")
                if attempt >= self.max_retries:
                    raise
                logger.info("Retrying after error...")

        # Failed after all retries
        raise ValueError(
            f"Failed to generate valid atomic specs after {self.max_retries} attempts. "
            f"Last attempt had {len(last_invalid_specs)} invalid specs."
        )

    async def _generate_specs_llm(
        self,
        task: MasterPlanTask,
        discovery: DiscoveryDocument,
        retry_feedback: Optional[List[tuple]] = None
    ) -> List[AtomicSpec]:
        """
        Generate specs using LLM

        Args:
            task: MasterPlanTask to atomize
            discovery: Discovery context
            retry_feedback: Previous invalid specs for retry feedback

        Returns:
            List of AtomicSpec instances (unvalidated)
        """
        # Build context from discovery
        context = self._build_discovery_context(discovery)

        # Build prompt
        prompt = self._build_generation_prompt(task, context, retry_feedback)

        logger.debug(f"Generating specs with LLM (temp=0.0, deterministic)")

        # Generate with Fase 1 params (temp=0, seed=42)
        response = await self.llm.generate_with_caching(
            task_type="task_execution",  # Valid TaskType
            complexity=self._map_task_complexity(task.complexity),
            cacheable_context={
                "system_prompt": ATOMIC_SPEC_SYSTEM_PROMPT,
                "discovery_context": context
            },
            variable_prompt=prompt,
            max_tokens=4000,
            temperature=0.0,  # Fase 1: Determinismo
            # Note: seed parameter depends on LLM support
        )

        # Parse response to AtomicSpec list
        specs = self._parse_specs_response(
            response["content"],
            task.task_id
        )

        logger.info(
            f"LLM generated {len(specs)} specs "
            f"(cost: ${response.get('cost_usd', 0):.4f})"
        )

        return specs

    def _build_discovery_context(self, discovery: DiscoveryDocument) -> Dict[str, Any]:
        """Build discovery context for prompt"""
        return {
            "domain": discovery.domain,
            "bounded_contexts": discovery.bounded_contexts,
            "aggregates": discovery.aggregates,
            "value_objects": discovery.value_objects,
            "services": discovery.services,
            "domain_events": discovery.domain_events
        }

    def _build_generation_prompt(
        self,
        task: MasterPlanTask,
        context: Dict,
        retry_feedback: Optional[List[tuple]] = None
    ) -> str:
        """
        Build prompt for spec generation

        Args:
            task: MasterPlanTask to atomize
            context: Discovery context
            retry_feedback: Previous invalid specs with errors (for retry)

        Returns:
            Generation prompt
        """
        prompt_parts = [
            "Generate atomic specifications for this task:\n",
            f"**Task #{task.task_number}**: {task.name}",
            f"**Description**: {task.description}",
            f"**Complexity**: {task.complexity.value}",
            f"**Target Files**: {', '.join(task.target_files or [])}",
            "",
            "**Discovery Context**:",
            f"- Domain: {context['domain']}",
            f"- Bounded Contexts: {len(context['bounded_contexts'])} contexts",
            f"- Aggregates: {len(context['aggregates'])} aggregates",
            f"- Services: {len(context['services'])} services",
            "",
            "**Requirements**:",
            "1. Generate **3-7 atomic specifications** (each ~10 LOC)",
            "2. Each spec MUST be **independently executable**",
            "3. Each spec MUST have **clear input/output types**",
            "4. Each spec MUST have **at least 1 test case**",
            "5. Complexity limit: **≤3.0 per spec**",
            "6. Target LOC: **10 (min 5, max 15)**",
            "7. **One responsibility per spec** (one action verb)",
            ""
        ]

        # Add retry feedback if this is a retry
        if retry_feedback:
            prompt_parts.extend([
                "**RETRY FEEDBACK** (previous attempt had validation errors):",
                ""
            ])
            for spec, result in retry_feedback[:3]:  # Show top 3 errors
                prompt_parts.append(
                    f"❌ Spec '{spec.description}' failed validation:"
                )
                for error in result.errors[:2]:  # Show top 2 errors per spec
                    prompt_parts.append(f"   - {error}")
            prompt_parts.extend([
                "",
                "Please fix these issues in the new generation.",
                ""
            ])

        prompt_parts.extend([
            "Return a JSON array of AtomicSpec objects following the schema.",
            "**CRITICAL**: Return ONLY valid JSON, no markdown, no explanations."
        ])

        return "\n".join(prompt_parts)

    def _map_task_complexity(self, task_complexity: DBTaskComplexity) -> TaskComplexity:
        """Map task complexity to LLM complexity enum"""
        mapping = {
            DBTaskComplexity.LOW: TaskComplexity.LOW,
            DBTaskComplexity.MEDIUM: TaskComplexity.MEDIUM,
            DBTaskComplexity.HIGH: TaskComplexity.HIGH,
            DBTaskComplexity.CRITICAL: TaskComplexity.CRITICAL
        }
        return mapping.get(task_complexity, TaskComplexity.MEDIUM)

    def _parse_specs_response(
        self,
        content: str,
        task_id: UUID
    ) -> List[AtomicSpec]:
        """
        Parse LLM response to AtomicSpec list

        Args:
            content: LLM response content
            task_id: Task ID to associate specs with

        Returns:
            List of AtomicSpec instances

        Raises:
            ValueError: If JSON is invalid or malformed
        """
        # Extract JSON from markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Parse JSON
        try:
            specs_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            logger.debug(f"Content: {content[:500]}")
            raise ValueError(f"Invalid JSON from LLM: {e}")

        # Ensure it's a list
        if not isinstance(specs_data, list):
            raise ValueError(
                f"Expected JSON array, got {type(specs_data).__name__}"
            )

        # Convert to AtomicSpec instances
        specs = []
        for i, spec_data in enumerate(specs_data):
            # Add required fields
            spec_data["task_id"] = str(task_id)
            spec_data["sequence_number"] = i + 1

            try:
                spec = AtomicSpec(**spec_data)
                specs.append(spec)
            except Exception as e:
                logger.error(
                    f"Failed to parse spec {i + 1}: {e}\n"
                    f"Data: {spec_data}"
                )
                raise ValueError(f"Failed to parse spec {i + 1}: {e}")

        logger.debug(f"Parsed {len(specs)} AtomicSpec instances from LLM response")
        return specs
