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

import os
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
    ErrorPattern,
    SuccessPattern,
    get_error_pattern_store,
)
from src.services.file_type_detector import get_file_type_detector
from src.services.prompt_strategies import PromptStrategyFactory, PromptContext
from src.services.validation_strategies import ValidationStrategyFactory
from src.services.modular_architecture_generator import ModularArchitectureGenerator

# Pattern Bank for Production-Ready Code Generation (Task Group 8)
from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.patterns.production_patterns import (
    PRODUCTION_PATTERN_CATEGORIES,
    get_composition_order,
)

# Cognitive Feedback Loop - Pattern Promotion Pipeline (Milestone 4)
from src.cognitive.patterns.pattern_feedback_integration import (
    get_pattern_feedback_integration,
    PatternFeedbackIntegration,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

# DAG Synchronizer - Execution Metrics (Milestone 3)
try:
    from src.cognitive.services.dag_synchronizer import DAGSynchronizer, ExecutionMetrics

    DAG_SYNC_AVAILABLE = True
except ImportError:
    DAG_SYNC_AVAILABLE = False

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
        enable_feedback_loop: bool = True,
        enable_pattern_promotion: bool = True,
        enable_dag_sync: bool = True,
    ):
        """
        Initialize code generation service.

        Args:
            db: Database session
            llm_client: LLM client (creates new if not provided)
            max_retries: Maximum retry attempts per task
            enable_feedback_loop: Enable cognitive feedback loop for learning (legacy)
            enable_pattern_promotion: Enable pattern promotion pipeline (Milestone 4)
            enable_dag_sync: Enable DAG synchronization for execution metrics (Milestone 3)
        """
        self.db = db
        self.llm_client = llm_client or EnhancedAnthropicClient()
        self.max_retries = max_retries
        self.enable_feedback_loop = enable_feedback_loop
        self.enable_pattern_promotion = enable_pattern_promotion
        self.enable_dag_sync = enable_dag_sync

        # Initialize error pattern store for cognitive feedback loop (legacy)
        self.pattern_store = None
        if enable_feedback_loop:
            try:
                self.pattern_store = get_error_pattern_store()
                logger.info("Cognitive feedback loop enabled (legacy)")
            except Exception as e:
                logger.warning(f"Could not initialize legacy feedback loop: {e}")
                self.enable_feedback_loop = False

        # Initialize pattern promotion pipeline (Milestone 4)
        self.pattern_feedback: Optional[PatternFeedbackIntegration] = None
        if enable_pattern_promotion:
            try:
                self.pattern_feedback = get_pattern_feedback_integration(enable_auto_promotion=True)
                logger.info("Pattern promotion pipeline enabled (Milestone 4)")
            except Exception as e:
                logger.warning(f"Could not initialize pattern promotion: {e}")
                self.enable_pattern_promotion = False

        # Initialize DAG synchronizer for execution metrics (Milestone 3)
        self.dag_synchronizer = None
        if enable_dag_sync and DAG_SYNC_AVAILABLE:
            try:
                self.dag_synchronizer = DAGSynchronizer()
                logger.info("DAG synchronization enabled (Milestone 3)")
            except Exception as e:
                logger.warning(f"Could not initialize DAG sync: {e}")
                self.enable_dag_sync = False
        else:
            self.enable_dag_sync = False

        # Initialize modular architecture generator
        self.modular_generator = ModularArchitectureGenerator()

        # Initialize PatternBank for production-ready code generation (Task Group 8)
        self.pattern_bank: Optional[PatternBank] = None
        try:
            self.pattern_bank = PatternBank()
            self.pattern_bank.connect()
            logger.info("PatternBank initialized for production patterns (Task Group 8)")
        except Exception as e:
            logger.warning(f"Could not initialize PatternBank: {e}")

        logger.info(
            "CodeGenerationService initialized",
            extra={
                "max_retries": max_retries,
                "feedback_loop": self.enable_feedback_loop,
                "pattern_promotion": self.enable_pattern_promotion,
                "dag_sync": self.enable_dag_sync,
                "pattern_bank_enabled": self.pattern_bank is not None,
            },
        )

    async def generate_modular_app(self, spec_requirements) -> Dict[str, str]:
        """
        Generate modular FastAPI application (Task Group 2: Modular Architecture).

        Creates production-ready structure with:
        - src/core/ (config, database)
        - src/models/ (schemas.py, entities.py)
        - src/repositories/ (repository pattern)
        - src/services/ (business logic)
        - src/api/routes/ (endpoints)

        Args:
            spec_requirements: SpecRequirements object from SpecParser

        Returns:
            Dict[file_path, file_content] for all generated files
        """
        logger.info(
            "Generating modular application",
            extra={
                "entities_count": len(spec_requirements.entities),
                "endpoints_count": len(spec_requirements.endpoints),
            }
        )

        try:
            files = self.modular_generator.generate_modular_app(spec_requirements)

            logger.info(
                "Modular application generated successfully",
                extra={
                    "files_generated": len(files),
                    "file_list": list(files.keys())
                }
            )

            return files

        except Exception as e:
            logger.error(
                "Failed to generate modular application",
                extra={"error": str(e)},
                exc_info=True
            )
            raise

    async def generate_from_requirements(
        self,
        spec_requirements,
        allow_syntax_errors: bool = False,
        repair_context: Optional[str] = None
    ) -> str:
        """
        Generate code from SpecRequirements (Task Group 3.1.3)

        This is the core fix for Bug #3: The Generator Bug.
        Instead of returning hardcoded templates, we generate code based on
        the actual requirements, entities, and endpoints from the spec.

        ENHANCED for Phase 6.5: Now accepts optional repair_context to guide
        code repair iterations with detailed failure analysis.

        Args:
            spec_requirements: SpecRequirements object from SpecParser
            allow_syntax_errors: If True, return code even with syntax errors.
                                Useful when repair loop will fix errors post-generation.
            repair_context: Optional repair context with compliance failures and
                           instructions for fixing the code. Used in Phase 6.5 repair loop.

        Returns:
            Complete generated code as string (models + routes + main)
        """
        logger.info(
            "Generating code from requirements",
            extra={
                "requirements_count": len(spec_requirements.requirements),
                "entities_count": len(spec_requirements.entities),
                "endpoints_count": len(spec_requirements.endpoints),
                "is_repair": repair_context is not None,
            },
        )

        # FEATURE FLAG: Use production-ready templates if enabled (Task Group 8)
        production_mode = os.getenv("PRODUCTION_MODE", "false").lower() == "true"

        if production_mode:
            logger.info(
                "PRODUCTION_MODE enabled - using production-ready templates",
                extra={"pattern_bank_available": self.pattern_bank is not None}
            )

            # PRODUCTION MODE: Use ONLY PatternBank (Task Group 8)
            logger.info("Retrieving production-ready patterns from PatternBank")
            patterns = await self._retrieve_production_patterns(spec_requirements)

            # Count patterns retrieved
            total_patterns = sum(len(p) for p in patterns.values())
            logger.info(
                "Retrieved patterns from PatternBank",
                extra={"categories": len(patterns), "total_patterns": total_patterns}
            )

            # Compose all files from patterns
            logger.info("Composing production-ready application from patterns")
            files_dict = await self._compose_patterns(patterns, spec_requirements)

            # Add __init__.py files for Python packages
            package_dirs = [
                "src",
                "src/core",
                "src/models",
                "src/repositories",
                "src/services",
                "src/api",
                "src/api/routes",
                "tests",
                "tests/unit",
                "tests/integration",
            ]
            for pkg_dir in package_dirs:
                files_dict[f"{pkg_dir}/__init__.py"] = '"""Package initialization."""\n'

            # Check if generation succeeded
            if not files_dict:
                logger.warning(
                    "Modular generation produced no files - falling back to legacy LLM generation",
                    extra={
                        "reason": "ModularArchitectureGenerator may have failed or spec requirements incomplete"
                    }
                )
                # Disable production mode and use legacy generation
                production_mode = False
                # Continue to legacy mode below (will execute after this if block)
            else:
                # Convert multi-file dict to single string for compatibility
                # Format: "=== FILE: path/to/file.py ===\n<content>\n\n"
                code_parts = []
                for filepath, content in sorted(files_dict.items()):
                    code_parts.append(f"=== FILE: {filepath} ===")
                    code_parts.append(content)
                    code_parts.append("")  # Empty line separator

                generated_code = "\n".join(code_parts)

                logger.info(
                    "Production mode generation complete",
                    extra={
                        "files_generated": len(files_dict),
                        "code_length": len(generated_code),
                        "mode": "modular_architecture_generator"
                    }
                )

                return generated_code

        # If we reach here, either production_mode is False OR pattern generation failed
        if production_mode:
            # Should never reach here due to fallback logic above
            logger.error("Unexpected: production_mode=True but reached legacy generation")
            production_mode = False

        # LEGACY MODE: Single-file monolithic generation
        logger.info("Using legacy single-file generation mode")

        # Build comprehensive prompt from requirements
        prompt = self._build_requirements_prompt(spec_requirements)

        # If repair context provided, prepend it to guide the LLM
        if repair_context:
            prompt = repair_context + "\n\n" + prompt

        # Call LLM with requirements context
        try:
            response = await asyncio.wait_for(
                self.llm_client.generate_with_caching(
                    task_type="task_execution",  # Valid TaskType for code generation
                    complexity="high",
                    cacheable_context={"system_prompt": self._get_requirements_system_prompt()},
                    variable_prompt=prompt,
                    temperature=0.0,  # Deterministic for reproducibility
                    max_tokens=10000,  # Increased for complex apps (e-commerce with 17+ endpoints)
                ),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            logger.error("LLM call timed out for requirements generation")
            raise ValueError("Code generation from requirements timed out after 120 seconds")

        # Extract code from response
        generated_code = self._extract_code(response.get("content", ""))

        if not generated_code:
            raise ValueError("No code generated from requirements")

        # Validate syntax
        is_valid, syntax_error = self._validate_generated_code_syntax(generated_code)
        if not is_valid:
            if allow_syntax_errors:
                # Log warning but continue - repair loop will fix it
                logger.warning(
                    f"Generated code has syntax errors (will be repaired): {syntax_error}",
                    extra={"syntax_error": syntax_error}
                )
            else:
                # Strict mode - fail immediately
                raise ValueError(f"Generated code has syntax errors: {syntax_error}")

        logger.info(
            "Code generation from requirements successful",
            extra={
                "code_length": len(generated_code),
                "entities_expected": len(spec_requirements.entities),
                "endpoints_expected": len(spec_requirements.endpoints),
            },
        )

        return generated_code

    def _get_adaptive_output_instructions(self, spec_requirements) -> str:
        """
        Calculate adaptive output instructions based on spec complexity.

        Removes hard-coded 100-300 line limit to allow proper implementation
        of complex specs like e-commerce with multiple features.
        """
        entity_count = len(spec_requirements.entities)
        endpoint_count = len(spec_requirements.endpoints)
        business_logic_count = len(spec_requirements.business_logic) if spec_requirements.business_logic else 0

        # Calculate complexity score
        complexity_score = (entity_count * 50) + (endpoint_count * 30) + (business_logic_count * 20)

        if complexity_score < 300:
            # Simple spec: Single file is fine
            return """Output: Single Python file with complete FastAPI application.
Structure: Models → Storage → Routes → App initialization"""
        elif complexity_score < 800:
            # Medium spec: Allow modular structure
            return """Output: Modular structure with multiple sections or files as needed.
Suggested structure:
- Enums and constants
- Pydantic models (entities)
- Request/Response schemas
- Storage layer
- Route handlers
- App initialization
All in a single well-organized file or logically separated."""
        else:
            # Complex spec: Full project structure
            return """Output: Complete application structure matching spec complexity.
For complex specs (e-commerce, multi-feature):
- Generate ALL entities, endpoints, and business logic
- Organize code logically (models → routes → services)
- Include all specified features
- No artificial line limits - implement everything specified
Structure as needed to maintain clarity while implementing ALL requirements."""

    def _build_requirements_prompt(self, spec_requirements) -> str:
        """
        Build LLM prompt from SpecRequirements (Task Group 3.1.3)

        Constructs comprehensive prompt with:
        - Entity specifications with fields, types, constraints
        - Endpoint specifications with methods, paths, parameters
        - Business logic requirements (validations, calculations)
        - All functional requirements context
        """
        prompt_parts = []

        prompt_parts.append("# CODE GENERATION FROM SPECIFICATION")
        prompt_parts.append("")
        prompt_parts.append(
            f"Generate a complete FastAPI application for: {spec_requirements.metadata.get('spec_name', 'API')}"
        )
        prompt_parts.append("")

        # ENTITIES
        if spec_requirements.entities:
            prompt_parts.append("## ENTITIES")
            prompt_parts.append("")
            for entity in spec_requirements.entities:
                prompt_parts.append(f"### {entity.name}")
                if entity.description:
                    prompt_parts.append(f"Description: {entity.description}")
                prompt_parts.append("Fields:")
                for field in entity.fields:
                    field_spec = f"- {field.name}: {field.type}"
                    if not field.required:
                        field_spec += " (optional)"
                    if field.primary_key:
                        field_spec += " [PRIMARY KEY]"
                    if field.unique:
                        field_spec += " [UNIQUE]"
                    if field.default:
                        field_spec += f" (default: {field.default})"
                    if field.constraints:
                        field_spec += f" | Constraints: {', '.join(field.constraints)}"
                    prompt_parts.append(field_spec)

                if entity.validations:
                    prompt_parts.append("Validations:")
                    for validation in entity.validations:
                        prompt_parts.append(f"- {validation.field}: {validation.rule}")
                        if validation.error_message:
                            prompt_parts.append(f"  Error: {validation.error_message}")

                if entity.relationships:
                    prompt_parts.append("Relationships:")
                    for rel in entity.relationships:
                        prompt_parts.append(
                            f"- {rel.field_name} → {rel.target_entity} ({rel.type})"
                        )

                prompt_parts.append("")

        # ENDPOINTS
        if spec_requirements.endpoints:
            prompt_parts.append("## ENDPOINTS")
            prompt_parts.append("")
            for endpoint in spec_requirements.endpoints:
                endpoint_spec = f"### {endpoint.method} {endpoint.path}"
                prompt_parts.append(endpoint_spec)
                if endpoint.description:
                    prompt_parts.append(f"Description: {endpoint.description}")
                prompt_parts.append(f"Operation: {endpoint.operation}")
                prompt_parts.append(f"Entity: {endpoint.entity}")

                if endpoint.params:
                    prompt_parts.append("Parameters:")
                    for param in endpoint.params:
                        param_spec = f"- {param.name} ({param.type}) in {param.location}"
                        if not param.required:
                            param_spec += " [optional]"
                        if param.default:
                            param_spec += f" = {param.default}"
                        prompt_parts.append(param_spec)

                if endpoint.business_logic:
                    prompt_parts.append("Business Logic:")
                    for logic in endpoint.business_logic:
                        prompt_parts.append(f"- {logic}")

                if endpoint.response:
                    prompt_parts.append(
                        f"Response: {endpoint.response.status_code} - {endpoint.response.description}"
                    )
                    if endpoint.response.schema:
                        prompt_parts.append(f"  Schema: {endpoint.response.schema}")

                prompt_parts.append("")

        # CRITICAL: EXACT ENDPOINT SPECIFICATION
        if spec_requirements.endpoints:
            prompt_parts.append("## ⚠️  CRITICAL: USE THESE EXACT ENDPOINTS")
            prompt_parts.append("")
            prompt_parts.append("YOU MUST implement endpoints with EXACTLY these HTTP methods and paths:")
            prompt_parts.append("")
            for endpoint in spec_requirements.endpoints:
                prompt_parts.append(f"  {endpoint.method:6s} {endpoint.path}")
            prompt_parts.append("")
            prompt_parts.append("DO NOT modify the HTTP methods or paths shown above.")
            prompt_parts.append("DO NOT add path parameters unless shown above.")
            prompt_parts.append("DO NOT use different HTTP methods (e.g., POST instead of DELETE).")
            prompt_parts.append("")

        # BUSINESS LOGIC
        if spec_requirements.business_logic:
            prompt_parts.append("## BUSINESS LOGIC")
            prompt_parts.append("")
            for logic in spec_requirements.business_logic:
                prompt_parts.append(f"### {logic.type}: {logic.description}")
                if logic.conditions:
                    prompt_parts.append(f"Conditions: {', '.join(logic.conditions)}")
                if logic.actions:
                    prompt_parts.append(f"Actions: {', '.join(logic.actions)}")
                prompt_parts.append("")

        # FUNCTIONAL REQUIREMENTS
        if spec_requirements.requirements:
            prompt_parts.append("## FUNCTIONAL REQUIREMENTS")
            prompt_parts.append("")
            for req in spec_requirements.requirements:
                if req.type == "functional":
                    prompt_parts.append(f"**{req.id}. {req.description}**")
            prompt_parts.append("")

        # GENERATION INSTRUCTIONS
        prompt_parts.append("## GENERATION INSTRUCTIONS")
        prompt_parts.append("")
        prompt_parts.append("Generate a COMPLETE, PRODUCTION-READY FastAPI application:")
        prompt_parts.append("")
        prompt_parts.append(
            "1. **Pydantic Models**: Generate complete models for ALL entities with:"
        )
        prompt_parts.append("   - All fields with correct types")
        prompt_parts.append("   - Field validators for constraints (gt, ge, email, max_length)")
        prompt_parts.append("   - Proper Optional/default handling")
        prompt_parts.append("")
        prompt_parts.append(
            "2. **FastAPI Routes**: Generate complete endpoints for ALL operations:"
        )
        prompt_parts.append("   - Correct HTTP methods (GET, POST, PUT, DELETE)")
        prompt_parts.append("   - Path parameters with type hints")
        prompt_parts.append("   - Request/response models")
        prompt_parts.append("   - Storage layer (in-memory dicts for simple specs, can use database patterns for complex specs)")
        prompt_parts.append("")
        prompt_parts.append("3. **Business Logic**: Implement ALL validations and rules:")
        prompt_parts.append("   - Field validations (price > 0, stock >= 0, email format)")
        prompt_parts.append("   - Business rules (stock checks, calculations)")
        prompt_parts.append("   - Error handling with HTTPException (404, 400, 422)")
        prompt_parts.append("")
        prompt_parts.append("4. **Error Handling**: Include proper error responses:")
        prompt_parts.append("   - 404 for not found")
        prompt_parts.append("   - 400 for business rule violations")
        prompt_parts.append("   - 422 for validation errors")
        prompt_parts.append("")
        prompt_parts.append("5. **Code Quality**:")
        prompt_parts.append("   - NO TODO comments or placeholders")
        prompt_parts.append("   - Complete implementations only")
        prompt_parts.append("   - Type hints throughout")
        prompt_parts.append("   - Docstrings for classes and functions")
        prompt_parts.append("")

        # Add adaptive output instructions based on spec complexity
        adaptive_instructions = self._get_adaptive_output_instructions(spec_requirements)
        prompt_parts.append(adaptive_instructions)
        prompt_parts.append("")

        prompt_parts.append("CRITICAL: Implement ALL specified entities, endpoints, and business logic.")
        prompt_parts.append("Do NOT truncate or simplify - generate complete implementation matching the spec.")

        return "\n".join(prompt_parts)

    def _get_requirements_system_prompt(self) -> str:
        """System prompt for requirements-based generation (Task Group 3.1.3)"""
        return """You are an expert FastAPI backend engineer specialized in generating
production-ready APIs from specifications.

Your task is to generate COMPLETE, WORKING code that EXACTLY matches the specification requirements.

CRITICAL RULES:
1. **Specification Compliance**: ONLY generate entities, endpoints, and logic specified in the requirements
   - If spec says Product/Cart/Order → generate Product/Cart/Order (NOT Task)
   - If spec says /products endpoint → generate /products (NOT /tasks)
   - NEVER generate code from templates or examples - use ONLY the provided spec

2. **Pydantic Models**: Generate complete models with:
   - All fields with exact types from spec (UUID, str, Decimal, int, bool, datetime)
   - Field validators for constraints (Field(gt=0), Field(ge=0), EmailStr)
   - Optional fields marked correctly (Optional[str] or str | None)
   - Default values where specified

3. **FastAPI Routes**: Implement ALL endpoints with:
   - Correct HTTP methods matching spec
   - Path parameters with type hints
   - Request/response models from Pydantic
   - Appropriate storage layer (in-memory dicts for simple specs)
   - Complete CRUD logic (not placeholders)

4. **Business Logic**: Implement ALL rules:
   - Validations: price > 0, stock >= 0, email format, max_length
   - Calculations: totals, sums, aggregations
   - Stock management: checks and updates
   - State machines: status transitions

5. **Error Handling**: Include proper errors:
   - HTTPException(status_code=404, detail="Not found")
   - HTTPException(status_code=400, detail="Business rule violation")
   - HTTPException(status_code=422) for validation (automatic with Pydantic)

6. **Code Quality**:
   - NO TODO comments
   - NO NotImplementedError
   - NO placeholders or stubs
   - Complete implementations only
   - Type hints throughout
   - Docstrings for clarity

7. **Output Format**:
   - Organize code logically based on complexity
   - All imports at top
   - Models section
   - Storage initialization
   - Route handlers
   - Main app initialization
   - Wrap in ```python code blocks

8. **Structure Guidelines** (will be specified in user prompt based on spec complexity):
   - Follow the output structure specified in the user prompt
   - Simple specs: Single file is acceptable
   - Complex specs: May use modular structure or multiple sections
   - ALWAYS implement ALL specified features regardless of structure choice

Generate code that is ready to run with `uvicorn main:app --reload` without any modifications."""

    def _validate_generated_code_syntax(self, code: str) -> tuple[bool, str]:
        """
        Validate generated code syntax (simplified for requirements generation)

        Args:
            code: Generated code string

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

    async def generate_code_for_task(self, task_id: uuid.UUID) -> Dict[str, Any]:
        """
        Generate code for a single task.

        Args:
            task_id: Task UUID

        Returns:
            Dict with generation results
        """
        logger.info("Starting code generation", extra={"task_id": str(task_id)})

        # Load task
        task = self.db.query(MasterPlanTask).filter(MasterPlanTask.task_id == task_id).first()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Check if already generated
        if task.llm_response:
            logger.info("Task already has generated code", extra={"task_id": str(task_id)})
            return {
                "success": True,
                "already_generated": True,
                "code_length": len(task.llm_response),
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
                        "feedback_loop": self.enable_feedback_loop and attempt > 1,
                    },
                )

                # On retry attempts, consult cognitive feedback loop
                if attempt > 1 and self.enable_feedback_loop and self.pattern_store and last_error:
                    logger.info(
                        "Consulting cognitive feedback loop for retry",
                        extra={"task_id": str(task_id), "attempt": attempt},
                    )

                    # Search for similar errors in history
                    similar_errors = await self.pattern_store.search_similar_errors(
                        task_description=task.description, error_message=str(last_error), top_k=3
                    )

                    # Search for successful patterns
                    successful_patterns = await self.pattern_store.search_successful_patterns(
                        task_description=task.description, top_k=5
                    )

                    logger.info(
                        "RAG feedback retrieved",
                        extra={
                            "task_id": str(task_id),
                            "similar_errors_found": len(similar_errors),
                            "successful_patterns_found": len(successful_patterns),
                        },
                    )

                    # Build enhanced prompt with feedback
                    prompt = self._build_prompt_with_feedback(
                        task, similar_errors, successful_patterns, str(last_error)
                    )
                else:
                    # First attempt - use standard prompt
                    prompt = self._build_prompt(task)

                # Call LLM with timeout (FIX 1: Add 120s timeout to prevent hangs)
                # Using asyncio.wait_for() for Python 3.10 compatibility (asyncio.timeout() requires 3.11+)
                try:
                    response = await asyncio.wait_for(
                        self.llm_client.generate_with_caching(
                            task_type="task_execution",  # Valid TaskType
                            complexity="medium",
                            cacheable_context={"system_prompt": self._get_system_prompt()},
                            variable_prompt=prompt,
                            temperature=0.0,  # Deterministic mode for reproducible precision
                            max_tokens=2000,
                        ),
                        timeout=120.0,  # 120 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "LLM call timed out after 120 seconds",
                        extra={"task_id": str(task_id), "attempt": attempt},
                    )
                    raise ValueError("LLM generation timed out after 120 seconds")

                # Extract code from response
                code = self._extract_code(response.get("content", ""))

                if not code:
                    raise ValueError("No code found in LLM response")

                # Validate code syntax with detailed error feedback (OPTION A: Validation + Retry)
                is_valid, syntax_error = self._validate_code_syntax(code, task)
                if not is_valid:
                    # Raise with SPECIFIC syntax error for retry feedback loop
                    raise ValueError(f"Syntax validation failed: {syntax_error}")

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
                        "attempt": attempt,
                    },
                )

                # Store successful pattern in cognitive feedback loop (legacy)
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
                                "used_feedback": attempt > 1,
                            },
                        )
                        await self.pattern_store.store_success(success_pattern)
                        logger.info(
                            "Stored successful pattern in legacy feedback loop",
                            extra={"task_id": str(task_id)},
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to store success pattern",
                            extra={"task_id": str(task_id), "error": str(e)},
                        )

                # Register with pattern promotion pipeline (Milestone 4)
                if self.enable_pattern_promotion and self.pattern_feedback:
                    try:
                        # Create semantic signature from task metadata
                        signature = self._create_signature_from_task(task)

                        # Register successful code for pattern promotion
                        candidate_id = self.pattern_feedback.register_successful_generation(
                            code=code,
                            signature=signature,
                            execution_result=None,  # Will be populated after execution
                            task_id=task_id,
                            metadata={
                                "task_name": task.name,
                                "complexity": task.complexity,
                                "attempt": attempt,
                                "tokens_used": task.llm_tokens_input + task.llm_tokens_output,
                                "cost_usd": task.llm_cost_usd,
                            },
                        )
                        logger.info(
                            "Registered code with pattern promotion pipeline",
                            extra={"task_id": str(task_id), "candidate_id": candidate_id},
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to register with pattern promotion",
                            extra={"task_id": str(task_id), "error": str(e)},
                        )

                # Sync execution metrics to DAG (Milestone 3)
                if self.enable_dag_sync and self.dag_synchronizer:
                    try:
                        execution_metrics = ExecutionMetrics(
                            task_id=str(task_id),
                            name=task.name,
                            task_type="task_execution",  # Valid TaskType
                            duration_ms=0.0,  # Will be populated by orchestrator
                            resources={"memory_mb": 0.0, "cpu_percent": 0.0},
                            success=True,
                            success_rate=1.0 if attempt == 1 else (1.0 / attempt),
                            output_tokens=task.llm_tokens_output,
                            timestamp=datetime.now(),
                            error_message=None,
                            pattern_ids=[],  # Will be populated if patterns were used
                            metadata={
                                "attempt": attempt,
                                "used_feedback": attempt > 1,
                                "cost_usd": task.llm_cost_usd,
                            },
                        )

                        self.dag_synchronizer.sync_execution_metrics(
                            task_id=str(task_id), execution_metrics=execution_metrics
                        )

                        logger.info(
                            "Synced execution metrics to DAG", extra={"task_id": str(task_id)}
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to sync DAG metrics",
                            extra={"task_id": str(task_id), "error": str(e)},
                        )

                return {
                    "success": True,
                    "code_length": len(code),
                    "tokens": task.llm_tokens_input + task.llm_tokens_output,
                    "cost_usd": task.llm_cost_usd,
                    "attempt": attempt,
                    "used_feedback_loop": attempt > 1 and self.enable_feedback_loop,
                }

            except Exception as e:
                last_error = e
                last_code = None

                logger.error(
                    "Code generation attempt failed",
                    extra={"task_id": str(task_id), "attempt": attempt, "error": str(e)},
                    exc_info=True,
                )

                # Store error pattern in cognitive feedback loop
                if self.enable_feedback_loop and self.pattern_store:
                    try:
                        error_pattern = ErrorPattern(
                            error_id=str(uuid.uuid4()),
                            task_id=str(task_id),
                            task_description=task.description,
                            error_type=(
                                "syntax_error" if "syntax" in str(e).lower() else "validation_error"
                            ),
                            error_message=str(e),
                            failed_code=last_code or "",
                            attempt=attempt,
                            timestamp=datetime.now(),
                            metadata={"task_name": task.name, "complexity": task.complexity},
                        )
                        await self.pattern_store.store_error(error_pattern)
                        logger.info(
                            "Stored error pattern in feedback loop",
                            extra={"task_id": str(task_id), "attempt": attempt},
                        )
                    except Exception as store_error:
                        logger.warning(
                            "Failed to store error pattern",
                            extra={"task_id": str(task_id), "error": str(store_error)},
                        )

                if attempt == self.max_retries:
                    # Final attempt failed, save error
                    task.last_error = (
                        f"Code generation failed after {self.max_retries} attempts: {str(e)}"
                    )
                    self.db.commit()

                    return {"success": False, "error": str(e), "attempts": attempt}

                # Exponential backoff
                await asyncio.sleep(2**attempt)

        return {"success": False, "error": "Max retries exceeded"}

    def _build_prompt(self, task: MasterPlanTask) -> str:
        """
        Build file-type-specific prompt for code generation using Strategy Pattern.

        Args:
            task: MasterPlan task

        Returns:
            Formatted prompt string optimized for the detected file type
        """
        # Detect file type with confidence scoring
        detector = get_file_type_detector()
        file_type_detection = detector.detect(
            task_name=task.name, task_description=task.description, target_files=task.target_files
        )

        logger.info(
            "File type detected for prompt generation",
            extra={
                "task_id": str(task.task_id),
                "file_type": file_type_detection.file_type.value,
                "confidence": file_type_detection.confidence,
                "reasoning": file_type_detection.reasoning,
            },
        )

        # Create prompt context
        context = PromptContext(
            task_number=task.task_number,
            task_name=task.name,
            task_description=task.description,
            complexity=task.complexity,
            file_type_detection=file_type_detection,
        )

        # Get appropriate strategy and generate prompt
        strategy = PromptStrategyFactory.get_strategy(file_type_detection.file_type)
        prompt = strategy.generate_prompt(context)

        return prompt

    def _build_prompt_with_feedback(
        self, task: MasterPlanTask, similar_errors: list, successful_patterns: list, last_error: str
    ) -> str:
        """
        Build enhanced prompt with file-type-specific feedback using Strategy Pattern.

        Args:
            task: MasterPlan task
            similar_errors: List of similar historical errors
            successful_patterns: List of successful code patterns
            last_error: Error from previous attempt

        Returns:
            Enhanced prompt with explicit corrective instructions
        """
        # Detect file type with confidence scoring
        detector = get_file_type_detector()
        file_type_detection = detector.detect(
            task_name=task.name, task_description=task.description, target_files=task.target_files
        )

        logger.info(
            "File type detected for feedback prompt generation",
            extra={
                "task_id": str(task.task_id),
                "file_type": file_type_detection.file_type.value,
                "confidence": file_type_detection.confidence,
                "last_error": last_error[:200],
            },
        )

        # Create prompt context with feedback
        context = PromptContext(
            task_number=task.task_number,
            task_name=task.name,
            task_description=task.description,
            complexity=task.complexity,
            file_type_detection=file_type_detection,
            last_error=last_error,
            similar_errors=similar_errors,
            successful_patterns=successful_patterns,
        )

        # Get appropriate strategy and generate prompt with feedback
        strategy = PromptStrategyFactory.get_strategy(file_type_detection.file_type)
        prompt = strategy.generate_prompt_with_feedback(context)

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
   - **CRITICAL**: All internal imports MUST use 'code.' prefix
     ✅ Correct: from code.src.models.order import Order
     ❌ Wrong: from src.models.order import Order
   - Add type hints/annotations
   - Include docstrings for functions and classes
   - Handle errors appropriately

3. **Syntax Validation**:
   - **CRITICAL**: Code MUST compile with Python compile() without errors
   - ALWAYS include complete class declarations with 'class Name:'
   - NEVER generate methods without parent class
   - NEVER generate incomplete code fragments
   - Example of CORRECT structure:
     class Order:  # ✅ Complete class declaration
         def __init__(self, ...):
             ...
   - Example of WRONG structure:
     def __init__(self, ...):  # ❌ Missing class declaration
         ...

4. **Output Format**:
   - Wrap code in markdown code blocks with language specified
   - Example: ```python\\ncode here\\n```
   - Do not include explanations outside code blocks

5. **Scope**:
   - Generate 50-150 lines of COMPLETE, syntactically valid code per task
   - Focus on the specific task requirements
   - Create complete, runnable code units
   - NEVER truncate classes or functions to meet line limits
   - If code is too long, prioritize completeness over brevity

Generate code that is ready to be parsed and executed without modifications.
Code MUST pass Python compile() without SyntaxError."""

    def _extract_code(self, content: str) -> str:
        """
        Extract code from LLM response (handles markdown code blocks).
        FIX 2: Enhanced to properly remove markdown fences and language specifiers.

        Args:
            content: LLM response content

        Returns:
            Extracted code without markdown formatting
        """
        # Pattern for markdown code blocks with optional language specifier
        # Matches: ```python\ncode\n``` or ```\ncode\n```
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            # Return first code block, stripped of whitespace
            extracted = matches[0].strip()

            # Additional cleanup: remove any remaining markdown artifacts
            # Remove leading/trailing backticks that might remain
            extracted = extracted.strip("`").strip()

            return extracted

        # If no code block found, return entire content stripped
        # Remove any stray backticks
        cleaned = content.strip().strip("`").strip()
        return cleaned

    def _validate_code_syntax(self, code: str, task: MasterPlanTask) -> tuple[bool, str]:
        """
        File-type-specific validation using Strategy Pattern.

        Args:
            code: Generated code/content
            task: Task for context

        Returns:
            (is_valid, error_message) tuple - OPTION A: Returns detailed error for retry feedback
        """
        # Detect file type for appropriate validation
        detector = get_file_type_detector()
        file_type_detection = detector.detect(
            task_name=task.name, task_description=task.description, target_files=task.target_files
        )

        # Get appropriate validation strategy
        validator = ValidationStrategyFactory.get_strategy(file_type_detection.file_type)
        is_valid, error_message = validator.validate(code)

        if not is_valid:
            logger.warning(
                "Code validation failed",
                extra={
                    "task_id": str(task.task_id),
                    "file_type": file_type_detection.file_type.value,
                    "error": error_message,
                    "code_preview": str(code[:200]),  # Fix: hashable string instead of slice
                },
            )

        # OPTION A: Return full tuple for detailed error feedback in retry loop
        return is_valid, error_message

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

            if file_path.endswith(".py"):
                return "python"
            elif file_path.endswith((".js", ".jsx")):
                return "javascript"
            elif file_path.endswith((".ts", ".tsx")):
                return "typescript"
            elif file_path.endswith(".java"):
                return "java"
            elif file_path.endswith(".go"):
                return "go"

        # Check task name/description for language hints
        name_lower = task.name.lower()
        desc_lower = task.description.lower()

        if "fastapi" in desc_lower or "pydantic" in desc_lower or "sqlalchemy" in name_lower:
            return "python"
        elif "react" in desc_lower or "jsx" in desc_lower:
            return "javascript"
        elif "typescript" in desc_lower or "tsx" in desc_lower:
            return "typescript"

        # Default to python
        return "python"

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

    def _create_signature_from_task(self, task: MasterPlanTask) -> SemanticTaskSignature:
        """
        Create semantic signature from task metadata.

        Args:
            task: MasterPlan task

        Returns:
            Semantic task signature for pattern matching
        """
        # Detect file type for domain inference
        detector = get_file_type_detector()
        file_type_detection = detector.detect(
            task_name=task.name, task_description=task.description, target_files=task.target_files
        )

        # Infer intent from task name/description
        description_lower = task.description.lower()

        if any(word in description_lower for word in ["create", "implement", "add"]):
            intent = "create"
        elif any(word in description_lower for word in ["update", "modify", "refactor"]):
            intent = "update"
        elif any(word in description_lower for word in ["delete", "remove"]):
            intent = "delete"
        elif any(word in description_lower for word in ["validate", "check", "verify"]):
            intent = "validate"
        elif any(word in description_lower for word in ["transform", "convert", "parse"]):
            intent = "transform"
        else:
            intent = "process"

        # Create signature
        signature = SemanticTaskSignature(
            purpose=task.description[:200],  # Truncate to reasonable length
            intent=intent,
            inputs={},  # Could be inferred from description
            outputs={},  # Could be inferred from description
            domain=file_type_detection.file_type.value,
            constraints=[],
            security_level="standard",
        )

        return signature

    # === TASK GROUP 8: PRODUCTION PATTERN LIBRARY ===
    # Pattern composition system for production-ready code generation

    async def generate_production_app(self, spec_requirements) -> Dict[str, str]:
        """
        Generate complete production-ready application using pattern composition (Task Group 8).

        Uses existing PatternBank infrastructure instead of Jinja2 templates.
        Retrieves production-ready patterns from Qdrant and composes them into modular architecture.

        Args:
            spec_requirements: SpecRequirements object from SpecParser

        Returns:
            Dictionary mapping file paths to generated code
            {
                "src/core/config.py": "...",
                "src/core/database.py": "...",
                "src/models/entities.py": "...",
                ...
            }

        Raises:
            ValueError: If PatternBank not initialized or patterns not available
        """
        if not self.pattern_bank:
            raise ValueError("PatternBank not initialized - cannot generate production app")

        logger.info(
            "Generating production app using pattern composition",
            extra={
                "entities_count": len(spec_requirements.entities),
                "endpoints_count": len(spec_requirements.endpoints),
            },
        )

        # 1. Retrieve production-ready patterns by category
        patterns = await self._retrieve_production_patterns(spec_requirements)

        # 2. Compose patterns into modular architecture
        generated_files = await self._compose_patterns(patterns, spec_requirements)

        # 3. Validate production readiness
        validation_result = self._validate_production_readiness(generated_files)

        logger.info(
            "Production app generation complete",
            extra={
                "files_generated": len(generated_files),
                "production_score": validation_result.get("production_score", 0.0),
            },
        )

        return generated_files

    async def _retrieve_production_patterns(
        self, spec_requirements
    ) -> Dict[str, list]:
        """
        Retrieve production-ready patterns for all categories (Task Group 8).

        Uses SPECIFIC purpose strings from populate_production_patterns.py to ensure
        correct pattern retrieval via PatternBank.hybrid_search().

        Args:
            spec_requirements: SpecRequirements object

        Returns:
            Dictionary mapping category name to list of StoredPattern objects
            {
                "core_config": [StoredPattern(...), ...],
                "database_async": [StoredPattern(...), ...],
                ...
            }
        """
        # Exact purpose strings from populate_production_patterns.py
        # This ensures semantic search returns the CORRECT patterns
        SPECIFIC_PURPOSES = {
            "core_config": [
                "Pydantic settings configuration with environment variable support",
            ],
            "database_async": [
                "Async SQLAlchemy database connection and session management",
            ],
            "observability": [
                "Structured logging configuration with structlog and JSON output",
                "Request ID middleware for distributed tracing",
                "Global exception handler with structured logging",
                "Health check and readiness endpoints",
                "Prometheus metrics endpoint with business metrics",
            ],
            "models_pydantic": [
                "Pydantic schemas for request/response validation",
            ],
            "models_sqlalchemy": [
                "SQLAlchemy ORM models with timezone-aware timestamps",
            ],
            "repository_pattern": [
                "Repository pattern implementation for data access",
            ],
            "business_logic": [
                "Service layer for business logic",
            ],
            "api_routes": [
                # Entity-specific CRUD routes pattern
                "FastAPI CRUD endpoints with repository pattern",
            ],
            "security_hardening": [
                "Security utilities for HTML sanitization and rate limiting",
            ],
            "test_infrastructure": [
                "Pytest fixtures for database and client testing",
                "Test data factories for entities",
                "Unit tests for Pydantic schemas",
                "Unit tests for repository CRUD operations",
                "Unit tests for service business logic",
                "Integration tests for API endpoints",
                "Tests for logging, metrics, and health checks",
            ],
            "docker_infrastructure": [
                "Multi-stage Docker image with security best practices",
                "Full stack docker-compose with app, database, monitoring",
                "Isolated test environment with docker-compose",
                "Prometheus scrape configuration",
            ],
            "project_config": [
                # Config files typically generated without patterns
            ],
        }

        patterns = {}

        for category, config in PRODUCTION_PATTERN_CATEGORIES.items():
            category_patterns = []
            specific_purposes = SPECIFIC_PURPOSES.get(category, [])

            if not specific_purposes:
                # Fallback: Use generic search for categories without specific purposes
                logger.warning(
                    f"No specific purposes for {category}, using generic search",
                    extra={"category": category}
                )
                query_sig = SemanticTaskSignature(
                    purpose=f"production ready {category} implementation",
                    intent="implement",
                    inputs={},
                    outputs={},
                    domain=config["domain"],
                )
                results = self.pattern_bank.hybrid_search(
                    signature=query_sig,
                    domain=config["domain"],
                    production_ready=True,
                    top_k=3,
                )
                category_patterns.extend(results)
            else:
                # Search for EACH specific purpose string
                for purpose in specific_purposes:
                    query_sig = SemanticTaskSignature(
                        purpose=purpose,
                        intent="implement",
                        inputs={},
                        outputs={},
                        domain=config["domain"],
                    )

                    results = self.pattern_bank.hybrid_search(
                        signature=query_sig,
                        domain=config["domain"],
                        production_ready=True,
                        top_k=1,  # Only need 1 per specific purpose
                    )

                    if results:
                        category_patterns.append(results[0])
                        logger.debug(
                            f"✅ Found pattern: {purpose[:60]}",
                            extra={"category": category}
                        )
                    else:
                        logger.warning(
                            f"❌ Missing pattern: {purpose[:60]}",
                            extra={"category": category, "purpose": purpose}
                        )

            # Filter by success threshold
            patterns[category] = [
                p
                for p in category_patterns
                if p.success_rate >= config["success_threshold"]
            ]

            logger.info(
                f"Retrieved {len(patterns[category])} patterns for {category}",
                extra={"category": category, "count": len(patterns[category])}
            )

        return patterns

    async def _compose_patterns(
        self, patterns: Dict[str, list], spec_requirements
    ) -> Dict[str, str]:
        """
        Compose patterns into complete modular application (Task Group 8).

        Pattern composition order (priority-based):
        1. Core infrastructure (config, database, logging)
        2. Data layer (models, repositories)
        3. Service layer
        4. API layer (routes)
        5. Security patterns
        6. Testing patterns
        7. Docker and config files
        8. Main application entry point (separate search for domain="application")

        Args:
            patterns: Dictionary of patterns by category
            spec_requirements: SpecRequirements object

        Returns:
            Dictionary mapping file paths to generated code
        """
        files = {}

        # Get composition order (priority-based)
        composition_order = get_composition_order()

        for category in composition_order:
            if category not in patterns or not patterns[category]:
                logger.debug(f"No patterns found for category: {category}")
                continue

            # Compose patterns for this category
            category_files = await self._compose_category_patterns(
                category, patterns[category], spec_requirements
            )
            files.update(category_files)

        # Search for main.py separately (domain="application" not in categories)
        main_pattern_query = SemanticTaskSignature(
            purpose="fastapi application entry point",
            intent="implement",
            inputs={},
            outputs={},
            domain="application",
        )
        main_patterns = self.pattern_bank.hybrid_search(
            signature=main_pattern_query,
            domain="application",
            production_ready=True,
            top_k=1,
        )

        if main_patterns:
            files["src/main.py"] = self._adapt_pattern(main_patterns[0].code, spec_requirements)
            logger.debug("Added main.py from PatternBank")

        return files

    async def _compose_category_patterns(
        self, category: str, category_patterns: list, spec_requirements
    ) -> Dict[str, str]:
        """
        Compose patterns for a specific category (Task Group 8).

        Maps StoredPattern objects to output files by matching purpose strings.

        Args:
            category: Category name (e.g., "core_config", "database_async")
            category_patterns: List of StoredPattern objects for this category
            spec_requirements: SpecRequirements object

        Returns:
            Dictionary of files generated for this category
        """
        files = {}

        # Helper function to find pattern by purpose keyword
        def find_pattern_by_keyword(patterns, *keywords):
            for p in patterns:
                if any(kw.lower() in p.signature.purpose.lower() for kw in keywords):
                    return p
            return None

        # Core infrastructure patterns
        if category == "core_config":
            for p in category_patterns:
                if "pydantic" in p.signature.purpose.lower() or "configuration" in p.signature.purpose.lower():
                    files["src/core/config.py"] = self._adapt_pattern(p.code, spec_requirements)

        elif category == "database_async":
            for p in category_patterns:
                if "sqlalchemy" in p.signature.purpose.lower() or "database" in p.signature.purpose.lower():
                    files["src/core/database.py"] = self._adapt_pattern(p.code, spec_requirements)

        elif category == "observability":
            # Map each observability pattern to its file
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "structured logging" in purpose_lower or "structlog" in purpose_lower:
                    files["src/core/logging.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "request id" in purpose_lower or "middleware" in purpose_lower:
                    files["src/core/middleware.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "exception" in purpose_lower or "global exception" in purpose_lower:
                    files["src/core/exception_handlers.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "health check" in purpose_lower or "readiness" in purpose_lower:
                    files["src/api/routes/health.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "metrics" in purpose_lower or "prometheus" in purpose_lower:
                    files["src/api/routes/metrics.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Data Layer - Pydantic Models
        elif category == "models_pydantic":
            for p in category_patterns:
                if "pydantic" in p.signature.purpose.lower() or "schema" in p.signature.purpose.lower():
                    files["src/models/schemas.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Data Layer - SQLAlchemy Models
        elif category == "models_sqlalchemy":
            for p in category_patterns:
                if "sqlalchemy" in p.signature.purpose.lower() or "orm" in p.signature.purpose.lower():
                    files["src/models/entities.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Repository Pattern
        elif category == "repository_pattern":
            # Generate repository for each entity
            repo_pattern = find_pattern_by_keyword(category_patterns, "repository", "crud")
            if repo_pattern and spec_requirements.entities:
                for entity in spec_requirements.entities:
                    adapted = self._adapt_pattern(repo_pattern.code, spec_requirements)
                    # Replace entity placeholder
                    adapted = adapted.replace("{ENTITY_NAME}", entity.name)
                    adapted = adapted.replace("{entity_name}", entity.snake_name)
                    files[f"src/repositories/{entity.snake_name}_repository.py"] = adapted

        # Business Logic / Service Layer
        elif category == "business_logic":
            # Generate service for each entity
            service_pattern = find_pattern_by_keyword(category_patterns, "service", "business logic")
            if service_pattern and spec_requirements.entities:
                for entity in spec_requirements.entities:
                    adapted = self._adapt_pattern(service_pattern.code, spec_requirements)
                    # Replace entity placeholder
                    adapted = adapted.replace("{ENTITY_NAME}", entity.name)
                    adapted = adapted.replace("{entity_name}", entity.snake_name)
                    files[f"src/services/{entity.snake_name}_service.py"] = adapted

        # API Routes
        elif category == "api_routes":
            # Generate API route for each entity
            route_pattern = find_pattern_by_keyword(category_patterns, "fastapi", "crud", "endpoint")
            if route_pattern and spec_requirements.entities:
                # Use pattern if available
                for entity in spec_requirements.entities:
                    adapted = self._adapt_pattern(route_pattern.code, spec_requirements)
                    # Replace entity placeholder
                    adapted = adapted.replace("{ENTITY_NAME}", entity.name)
                    adapted = adapted.replace("{entity_name}", entity.snake_name)
                    files[f"src/api/routes/{entity.snake_name}.py"] = adapted
            elif spec_requirements.entities:
                # LLM FALLBACK: No pattern found, generate with LLM
                logger.warning(
                    "No pattern found for api_routes - using LLM fallback",
                    extra={"entity_count": len(spec_requirements.entities)}
                )

                # Generate CRUD routes for each entity using LLM
                for entity in spec_requirements.entities:
                    # Create context for LLM
                    entity_context = {
                        "entity_name": entity.name,
                        "snake_name": entity.snake_name,
                        "fields": [{"name": f.name, "type": f.type, "required": f.required} for f in entity.fields] if hasattr(entity, 'fields') else [],
                        "endpoints": [e for e in spec_requirements.endpoints if entity.snake_name in e.path.lower()]
                    }

                    # Use LLM to generate FastAPI CRUD routes
                    prompt = f"""Generate FastAPI CRUD routes for entity {entity.name}.

Entity Information:
- Name: {entity.name}
- Snake case: {entity.snake_name}
- Fields: {entity_context['fields']}
- Endpoints needed: {len(entity_context['endpoints'])}

Generate complete FastAPI route file with:
1. Import statements (FastAPI, Depends, HTTPException)
2. APIRouter instance
3. CRUD operations: GET all, GET by id, POST create, PUT update, DELETE
4. Dependency injection for service and database
5. Proper HTTP status codes and error handling
6. Pydantic schema validation

Use repository pattern and service layer architecture.
File: src/api/routes/{entity.snake_name}.py
"""

                    # TODO: Call LLM here (for now, use placeholder)
                    # generated_code = await self._generate_with_llm(prompt, entity_context)

                    # Placeholder until LLM integration
                    logger.info(
                        f"LLM fallback would generate: src/api/routes/{entity.snake_name}.py",
                        extra={"prompt_length": len(prompt)}
                    )

        # Security patterns
        elif category == "security_hardening":
            for p in category_patterns:
                if "security" in p.signature.purpose.lower() or "sanitization" in p.signature.purpose.lower():
                    files["src/core/security.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Testing patterns
        elif category == "test_infrastructure":
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "pytest fixtures" in purpose_lower or "conftest" in purpose_lower:
                    files["tests/conftest.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "test data factories" in purpose_lower or "factories" in purpose_lower:
                    files["tests/factories.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "unit tests for pydantic" in purpose_lower or "test_models" in purpose_lower:
                    files["tests/unit/test_models.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "unit tests for repository" in purpose_lower or "test_repositories" in purpose_lower:
                    files["tests/unit/test_repositories.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "unit tests for service" in purpose_lower or "test_services" in purpose_lower:
                    files["tests/unit/test_services.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "integration tests" in purpose_lower or "test_api" in purpose_lower:
                    files["tests/integration/test_api.py"] = self._adapt_pattern(p.code, spec_requirements)
                elif "tests for logging" in purpose_lower or "observability" in purpose_lower:
                    files["tests/test_observability.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Docker infrastructure
        elif category == "docker_infrastructure":
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "multi-stage docker" in purpose_lower or "dockerfile" in purpose_lower:
                    files["docker/Dockerfile"] = self._adapt_pattern(p.code, spec_requirements)
                elif "full stack docker-compose" in purpose_lower and "test" not in purpose_lower:
                    files["docker/docker-compose.yml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "test environment" in purpose_lower or "docker-compose.test" in purpose_lower:
                    files["docker/docker-compose.test.yml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "prometheus scrape" in purpose_lower or "prometheus.yml" in purpose_lower:
                    files["docker/prometheus.yml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "docker build exclusions" in purpose_lower or ".dockerignore" in purpose_lower:
                    files["docker/.dockerignore"] = self._adapt_pattern(p.code, spec_requirements)
                elif "grafana dashboard" in purpose_lower and "json" in purpose_lower:
                    files["docker/grafana/dashboards/app-metrics.json"] = self._adapt_pattern(p.code, spec_requirements)
                elif "dashboard provisioning" in purpose_lower or "dashboard-provider" in purpose_lower:
                    files["docker/grafana/dashboards/dashboard-provider.yml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "datasource" in purpose_lower or "prometheus datasource" in purpose_lower:
                    files["docker/grafana/datasources/prometheus.yml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "docker setup documentation" in purpose_lower or "readme" in purpose_lower.lower():
                    files["docker/README.md"] = self._adapt_pattern(p.code, spec_requirements)
                elif "troubleshooting" in purpose_lower:
                    files["docker/TROUBLESHOOTING.md"] = self._adapt_pattern(p.code, spec_requirements)
                elif "validation checklist" in purpose_lower:
                    files["docker/VALIDATION_CHECKLIST.md"] = self._adapt_pattern(p.code, spec_requirements)
                elif "validation script" in purpose_lower or ".sh" in purpose_lower:
                    files["docker/validate-docker-setup.sh"] = self._adapt_pattern(p.code, spec_requirements)

        # Project config
        elif category == "project_config":
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "pyproject" in purpose_lower or "toml" in purpose_lower:
                    files["pyproject.toml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "env" in purpose_lower and "example" in purpose_lower:
                    files[".env.example"] = self._adapt_pattern(p.code, spec_requirements)
                elif "gitignore" in purpose_lower:
                    files[".gitignore"] = self._adapt_pattern(p.code, spec_requirements)
                elif "makefile" in purpose_lower:
                    files["Makefile"] = self._adapt_pattern(p.code, spec_requirements)
                elif "pre-commit" in purpose_lower or "pre_commit" in purpose_lower:
                    files[".pre-commit-config.yaml"] = self._adapt_pattern(p.code, spec_requirements)
                elif "readme" in purpose_lower:
                    files["README.md"] = self._adapt_pattern(p.code, spec_requirements)

        return files

    def _adapt_pattern(self, pattern_code: str, spec_requirements) -> str:
        """
        Adapt pattern code to spec requirements (Task Group 8).

        Replace placeholder variables with actual spec values:
        - {APP_NAME} → spec.metadata.get("spec_name", "API")
        - {DATABASE_URL} → spec.config.get("database_url", "")
        - {ENTITY_NAME} → entity.name (for entity-specific patterns)

        Args:
            pattern_code: Pattern code with placeholders
            spec_requirements: SpecRequirements object

        Returns:
            Adapted code with placeholders replaced
        """
        adapted = pattern_code

        # App name
        app_name = spec_requirements.metadata.get("spec_name", "API")
        adapted = adapted.replace("{APP_NAME}", app_name)

        # Database URL (from metadata or default)
        database_url = spec_requirements.metadata.get(
            "database_url", "postgresql+asyncpg://user:password@localhost:5432/app"
        )
        adapted = adapted.replace("{DATABASE_URL}", database_url)

        # Additional adaptations can be added here as needed

        return adapted

    def _validate_production_readiness(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate production readiness of generated files (Task Group 8).

        Checks:
        - Core infrastructure files present (config, database, logging)
        - Security patterns included
        - Docker configuration available
        - Test infrastructure present

        Args:
            files: Dictionary of generated files

        Returns:
            Dictionary with validation results:
            {
                "production_ready": bool,
                "production_score": float (0.0-1.0),
                "missing_components": list[str],
                "recommendations": list[str]
            }
        """
        required_files = {
            "src/core/config.py": "configuration",
            "src/core/database.py": "database",
            "src/core/security.py": "security",
            "docker/Dockerfile": "docker",
            "tests/conftest.py": "testing",
        }

        missing_components = []
        for file_path, component in required_files.items():
            if file_path not in files:
                missing_components.append(component)

        # Calculate production score
        present_count = len(required_files) - len(missing_components)
        production_score = present_count / len(required_files)

        # Generate recommendations
        recommendations = []
        if "configuration" in missing_components:
            recommendations.append("Add pydantic-settings configuration for environment management")
        if "security" in missing_components:
            recommendations.append("Implement security hardening (rate limiting, CORS, sanitization)")
        if "docker" in missing_components:
            recommendations.append("Add Docker configuration for containerized deployment")
        if "testing" in missing_components:
            recommendations.append("Set up pytest infrastructure with async support")

        return {
            "production_ready": production_score >= 0.80,  # 80% threshold
            "production_score": round(production_score, 2),
            "missing_components": missing_components,
            "recommendations": recommendations,
        }
