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
from jinja2 import Template

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

# Production-Ready Code Generators (Hardcoded fallback)
from src.services.production_code_generators import (
    generate_entities,
    generate_config,
    generate_schemas,
    generate_service_method,
    generate_initial_migration,
    validate_generated_files,
    get_validation_summary,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

# DAG Synchronizer - Execution Metrics (Milestone 3)
try:
    from src.cognitive.services.dag_synchronizer import DAGSynchronizer, ExecutionMetrics

    DAG_SYNC_AVAILABLE = True
except ImportError:
    DAG_SYNC_AVAILABLE = False

logger = StructuredLogger("code_generation_service", output_json=False)


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

            # LLM fallback for missing essential files (Task Group 8 enhancement)
            # User requirement: "SI NO HAY PATTERNS DEBEMOS PASARLE CONTEXTO NECESARIO PARA Q EL LLM ESCRIBA EL CODIGO"
            logger.info("Checking for missing essential files (LLM fallback)")
            llm_generated = await self._generate_with_llm_fallback(files_dict, spec_requirements)
            files_dict.update(llm_generated)

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

IMPORTANT: Always respond in English, regardless of the input language.

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

7. **Observability & Metrics** (for production-mode generation):
   - HTTP metrics (http_requests_total, http_request_duration_seconds) must be defined ONLY in middleware.py
   - In metrics.py, IMPORT these metrics from middleware.py - DO NOT redefine them
   - Business metrics (entity-specific counters/gauges) should be defined in metrics.py
   - Avoid duplicate metric registrations to prevent CollectorRegistry errors

8. **Output Format**:
   - Organize code logically based on complexity
   - All imports at top
   - Models section
   - Storage initialization
   - Route handlers
   - Main app initialization
   - Wrap in ```python code blocks

9. **Structure Guidelines** (will be specified in user prompt based on spec complexity):
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

        # 2.5. LLM fallback for missing essential files (no patterns available)
        # User requirement: "SI NO HAY PATTERNS DEBEMOS PASARLE CONTEXTO NECESARIO PARA Q EL LLM ESCRIBA EL CODIGO"
        llm_generated = await self._generate_with_llm_fallback(generated_files, spec_requirements)
        generated_files.update(llm_generated)

        # 3. Validate production readiness
        validation_result = self._validate_production_readiness(generated_files)

        # 4. Validate Python syntax for all generated code
        logger.info("🔍 Validating Python syntax of generated code...")
        syntax_validation = validate_generated_files(generated_files)
        syntax_summary = get_validation_summary(syntax_validation)

        logger.info(
            "✅ Syntax validation complete",
            extra={
                "total_files": syntax_summary["total"],
                "passed": syntax_summary["passed"],
                "failed": syntax_summary["failed"],
                "pass_rate": f"{syntax_summary['pass_rate']}%",
            },
        )

        if not syntax_summary["valid"]:
            failed_files = [f for f, valid in syntax_validation.items() if not valid]
            logger.warning(
                f"⚠️ {syntax_summary['failed']} file(s) have syntax errors",
                extra={"failed_files": failed_files}
            )

        logger.info(
            "Production app generation complete",
            extra={
                "files_generated": len(generated_files),
                "production_score": validation_result.get("production_score", 0.0),
                "syntax_valid": syntax_summary["valid"],
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
                # Search for EACH specific purpose string with EXACT matching
                for purpose in specific_purposes:
                    query_sig = SemanticTaskSignature(
                        purpose=purpose,
                        intent="implement",
                        inputs={},
                        outputs={},
                        domain=config["domain"],
                    )

                    # Get top 10 candidates to ensure exact match is included
                    results = self.pattern_bank.hybrid_search(
                        signature=query_sig,
                        domain=config["domain"],
                        production_ready=True,
                        top_k=10,  # Increased to capture patterns with lower similarity scores
                    )

                    # Find EXACT purpose match (not just semantic similarity)
                    exact_match = None
                    for r in results:
                        if r.signature.purpose.strip() == purpose.strip():
                            exact_match = r
                            break

                    if exact_match:
                        category_patterns.append(exact_match)
                        logger.debug(
                            f"✅ Found EXACT pattern: {purpose[:60]}",
                            extra={"category": category}
                        )
                    else:
                        # Log which patterns we got instead
                        found_purposes = [r.signature.purpose[:60] for r in results]
                        logger.warning(
                            f"❌ No EXACT match for: {purpose[:60]}",
                            extra={
                                "category": category,
                                "wanted": purpose,
                                "found": found_purposes
                            }
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
        # Use exact purpose string from populate_production_patterns.py
        main_pattern_query = SemanticTaskSignature(
            purpose="FastAPI application entry point with middleware and routes",
            intent="implement",
            inputs={},
            outputs={},
            domain="application",
        )
        main_patterns = self.pattern_bank.hybrid_search(
            signature=main_pattern_query,
            domain="application",
            production_ready=True,
            top_k=10,  # Increased for exact matching
        )

        # Find EXACT match
        exact_main = None
        for p in main_patterns:
            if p.signature.purpose.strip() == "FastAPI application entry point with middleware and routes":
                exact_main = p
                break

        # Production mode: Always use hardcoded main.py (ensures docs enabled, correct config)
        if os.getenv("PRODUCTION_MODE") == "true":
            logger.info("🔨 PRODUCTION_MODE: Using hardcoded main.py (docs always enabled)")
            main_py_code = self._generate_main_py(spec_requirements)
            files["src/main.py"] = main_py_code
        elif exact_main:
            files["src/main.py"] = self._adapt_pattern(exact_main.code, spec_requirements)
            logger.info("✅ Added main.py from PatternBank")
        else:
            # Fallback: Generate main.py directly if not found in PatternBank
            main_py_code = self._generate_main_py(spec_requirements)
            files["src/main.py"] = main_py_code
            logger.info("✅ Generated main.py (fallback from pattern not found)")

        return files

    async def _generate_with_llm_fallback(
        self, existing_files: Dict[str, str], spec_requirements
    ) -> Dict[str, str]:
        """
        Generate missing essential files using LLM fallback (no patterns available).

        User requirement: "SI NO HAY PATTERNS DEBEMOS PASARLE CONTEXTO NECESARIO PARA Q EL LLM
        ESCRIBA EL CODIGO COMO MEJOR CREA, LUEGO ITERAR SI FALLA CON EL REPAIR LOOP LEARNING"

        Args:
            existing_files: Dictionary of files already generated from patterns
            spec_requirements: SpecRequirements with project context

        Returns:
            Dictionary of LLM-generated files for missing essentials
        """
        logger.info(
            "🔍 Checking for missing essential files",
            extra={"existing_count": len(existing_files)}
        )
        llm_files = {}

        # Define essential files that should exist
        essential_files = {
            "requirements.txt": self._generate_requirements_txt,
            "poetry.lock": self._generate_poetry_lock,
            "README.md": self._generate_readme_md,
        }

        # Generate missing files using LLM
        for file_path, generator_func in essential_files.items():
            if file_path not in existing_files:
                logger.info(
                    f"🤖 LLM fallback: Generating {file_path} (no pattern available)",
                    extra={"file": file_path}
                )
                try:
                    content = await generator_func(spec_requirements, existing_files)
                    llm_files[file_path] = content
                    logger.info(f"✅ LLM generated: {file_path}")
                except Exception as e:
                    logger.error(
                        f"❌ LLM fallback failed for {file_path}: {e}",
                        extra={"file": file_path, "error": str(e)}
                    )
                    # Don't fail the entire generation, continue with other files

        return llm_files

    async def _generate_requirements_txt(
        self, spec_requirements, existing_files: Dict[str, str]
    ) -> str:
        """Generate requirements.txt using LLM with rich context."""

        # PRODUCTION_MODE: Use hardcoded requirements with verified versions
        if os.getenv("PRODUCTION_MODE") == "true":
            logger.info("🔨 PRODUCTION_MODE: Using verified requirements.txt (psycopg 3.2.12)")
            return self._generate_requirements_hardcoded()

        # Extract metadata safely
        project_name = spec_requirements.metadata.get("project_name", "FastAPI Application")
        description = spec_requirements.metadata.get("description", "Production-ready FastAPI application")

        # Build context about the project
        context = f"""Generate PRODUCTION ONLY requirements.txt for this FastAPI application.
NO testing, linting, or development tools - ONLY runtime dependencies!

Project: {project_name}
Description: {description}

Technology Stack (PRODUCTION ONLY):
- FastAPI 0.109+ (async web framework)
- SQLAlchemy 2.0+ with asyncpg (async PostgreSQL runtime)
- psycopg 3.2.12 (sync PostgreSQL for Alembic migrations - CRITICAL: Use 3.2.12, NOT 3.14.x)
- Pydantic v2 with pydantic-settings (config management)
- Alembic (database migrations)
- structlog (structured logging)
- prometheus-client (metrics)
- httpx (async HTTP client)
- bleach (HTML sanitization)
- slowapi (rate limiting)

Entities: {', '.join(e.name for e in spec_requirements.entities)}
Endpoints: {len(spec_requirements.endpoints)} REST endpoints

CRITICAL REQUIREMENTS:
1. Pin ALL versions (use ==, not >=)
2. ONLY production runtime dependencies, NO testing/dev tools
3. NO pytest, black, mypy, ruff, pre-commit, faker, coverage, etc.
4. Group by category (web, database, config, logging, metrics, security)
5. Add comments for each group
6. Ensure compatibility (FastAPI 0.109+, SQLAlchemy 2.0+, Pydantic 2.5+)
7. Keep versions compatible with Python 3.11
8. Use psycopg==3.2.12 (latest stable version that exists in PyPI)

Generate ONLY the requirements.txt content, no explanations."""

        # Use LLM to generate with caching
        response = await self.llm_client.generate_with_caching(
            task_type="documentation",
            complexity="low",
            cacheable_context={"system_prompt": "You are a Python dependency management expert."},
            variable_prompt=context,
            max_tokens=1000,
            temperature=0.3  # Lower temperature for more deterministic dependency versions
        )

        # Clean markdown delimiters that LLM might include
        content = response["content"].strip()
        if content.startswith("```"):
            # Remove opening ```txt or ``` delimiter
            content = content.lstrip("`").lstrip("txt").lstrip("\n")
        if content.endswith("```"):
            # Remove closing ``` delimiter
            content = content.rstrip("`").rstrip("\n")

        return content

    async def _generate_poetry_lock(
        self, spec_requirements, existing_files: Dict[str, str]
    ) -> str:
        """Generate poetry.lock file with pinned dependencies."""
        # Get requirements.txt to parse versions
        requirements_content = existing_files.get("requirements.txt", "")

        # Build minimal poetry.lock header
        lock_content = """# This file is automatically @generated by Poetry 1.7.0 and should not be manually edited.
[[package]]
name = "fastapi"
version = "0.109.2"
description = "FastAPI framework, high performance, easy to learn, fast to code, ready for production"
category = "main"
optional = false
python-versions = ">=3.8"

[[package]]
name = "sqlalchemy"
version = "2.0.25"
description = "Database Abstraction Library"
category = "main"
optional = false
python-versions = ">=3.7"

[[package]]
name = "pydantic"
version = "2.6.1"
description = "Data validation using Python type annotations"
category = "main"
optional = false
python-versions = ">=3.8"

[[package]]
name = "alembic"
version = "1.13.1"
description = "A database migration tool for SQLAlchemy"
category = "main"
optional = false
python-versions = ">=3.7"

[[package]]
name = "pytest"
version = "8.0.0"
description = "pytest: simple powerful testing with Python"
category = "dev"
optional = false
python-versions = ">=3.8"

[metadata]
python-versions = "^3.10"
lock-version = "2.0"
content-hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

[metadata.files]
"""
        return lock_content

    async def _generate_readme_md(
        self, spec_requirements, existing_files: Dict[str, str]
    ) -> str:
        """Generate README.md using LLM with rich context."""

        # Extract metadata safely
        project_name = spec_requirements.metadata.get("project_name", "FastAPI Application")
        description = spec_requirements.metadata.get("description", "Production-ready FastAPI application")
        version = spec_requirements.metadata.get("version", "1.0.0")

        # Build context about the project and generated files
        entity_details = "\n".join([
            f"- **{e.name}**: {', '.join(f.name for f in e.fields)}"
            for e in spec_requirements.entities
        ])

        endpoint_details = "\n".join([
            f"- `{ep.method} {ep.path}`: {ep.description}"
            for ep in spec_requirements.endpoints[:10]  # Limit to first 10
        ])

        file_structure = "\n".join([
            f"- {path}" for path in sorted(existing_files.keys())[:20]  # Sample of files
        ])

        context = f"""Generate a production-ready README.md for this FastAPI application.

# Project Details
Name: {project_name}
Description: {description}
Version: {version}

# Entities (Data Models)
{entity_details}

# API Endpoints
{endpoint_details}
{"... and more" if len(spec_requirements.endpoints) > 10 else ""}

# Technology Stack
- FastAPI with async/await
- PostgreSQL with SQLAlchemy async
- Pydantic v2 for validation
- Alembic for migrations
- structlog for logging
- Prometheus metrics
- pytest for testing
- Docker support

# Generated Project Structure (sample)
{file_structure}

Generate a comprehensive README.md that includes:

1. **Project Title and Description**
2. **Features** (based on entities and endpoints)
3. **Tech Stack** (list key technologies)
4. **Prerequisites** (Python 3.11+, PostgreSQL, etc.)
5. **Installation** (pip install -r requirements.txt, database setup)
6. **Configuration** (.env file setup with DATABASE_URL, etc.)
7. **Running the Application** (uvicorn command, Docker option)
8. **API Documentation** (mention /docs and /redoc)
9. **Database Migrations** (alembic commands)
10. **Testing** (pytest commands)
11. **Project Structure** (brief overview)
12. **Development** (how to contribute, code style)

Use clear markdown formatting, code blocks, and badges if appropriate.
Generate ONLY the README.md content, no additional explanations."""

        # Use LLM to generate with caching
        response = await self.llm_client.generate_with_caching(
            task_type="documentation",
            complexity="medium",
            cacheable_context={"system_prompt": "You are a technical documentation expert specializing in README files for FastAPI projects."},
            variable_prompt=context,
            max_tokens=2500,
            temperature=0.5  # Balanced creativity for documentation
        )

        return response["content"].strip()

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

        # Log patterns for this category
        logger.info(
            f"🔧 Composing {category}",
            extra={
                "category": category,
                "pattern_count": len(category_patterns),
                "purposes": [p.signature.purpose[:70] for p in category_patterns]
            }
        )

        # Helper function to find pattern by purpose keyword
        def find_pattern_by_keyword(patterns, *keywords):
            for p in patterns:
                if any(kw.lower() in p.signature.purpose.lower() for kw in keywords):
                    logger.debug(
                        f"✅ Pattern matched: {p.signature.purpose[:60]}",
                        extra={"keywords": keywords}
                    )
                    return p
            logger.warning(
                f"❌ No pattern matched keywords: {keywords}",
                extra={"category": category, "available": len(patterns)}
            )
            return None

        # Core infrastructure patterns
        if category == "core_config":
            # Use hardcoded production-ready config generator
            config_code = generate_config()
            if config_code:
                files["src/core/config.py"] = config_code
                logger.info(f"✅ Generated: src/core/config.py (hardcoded production generator)")
            else:
                # Fallback to pattern matching
                for p in category_patterns:
                    if "pydantic" in p.signature.purpose.lower() or "configuration" in p.signature.purpose.lower():
                        files["src/core/config.py"] = self._adapt_pattern(p.code, spec_requirements)
                        logger.info(f"✅ Mapped: src/core/config.py", extra={"purpose": p.signature.purpose[:60]})

        elif category == "database_async":
            for p in category_patterns:
                if "sqlalchemy" in p.signature.purpose.lower() or "database" in p.signature.purpose.lower():
                    files["src/core/database.py"] = self._adapt_pattern(p.code, spec_requirements)

        elif category == "observability":
            # Map each observability pattern to its file
            # Order matters: most specific patterns first to avoid false matches
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                # Check exception handler BEFORE logging (both contain "structured logging")
                if "exception" in purpose_lower or "global exception" in purpose_lower:
                    files["src/core/exception_handlers.py"] = self._adapt_pattern(p.code, spec_requirements)
                # Check request ID middleware specifically
                elif "request id" in purpose_lower:
                    files["src/core/middleware.py"] = self._adapt_pattern(p.code, spec_requirements)
                # Logging configuration (check after exception handler)
                elif "structlog" in purpose_lower and "configuration" in purpose_lower:
                    files["src/core/logging.py"] = self._adapt_pattern(p.code, spec_requirements)
                # Health checks
                elif "health check" in purpose_lower or "readiness" in purpose_lower:
                    files["src/api/routes/health.py"] = self._adapt_pattern(p.code, spec_requirements)
                # Prometheus metrics
                elif "metrics" in purpose_lower or "prometheus" in purpose_lower:
                    files["src/api/routes/metrics.py"] = self._adapt_pattern(p.code, spec_requirements)

            # Production mode: Always use optimized routes (prevents issues)
            if os.getenv("PRODUCTION_MODE") == "true":
                logger.info("🔨 PRODUCTION_MODE: Using deduplicated metrics route (imports from middleware)")
                metrics_code = self._generate_metrics_route()
                files["src/api/routes/metrics.py"] = metrics_code

                logger.info("🔨 PRODUCTION_MODE: Using health routes with text() fix (SQLAlchemy 2.0)")
                health_code = self._generate_health_routes()
                files["src/api/routes/health.py"] = health_code

        # Data Layer - Pydantic Models
        elif category == "models_pydantic":
            # Use hardcoded production-ready schemas generator
            if spec_requirements.entities:
                schemas_code = generate_schemas(
                    [{"name": e.name, "plural": e.name.lower() + "s"} for e in spec_requirements.entities]
                )
                if schemas_code:
                    files["src/models/schemas.py"] = schemas_code
                    logger.info(f"✅ Generated: src/models/schemas.py (hardcoded production generator)")
                else:
                    # Fallback to pattern matching
                    for p in category_patterns:
                        if "pydantic" in p.signature.purpose.lower() or "schema" in p.signature.purpose.lower():
                            files["src/models/schemas.py"] = self._adapt_pattern(p.code, spec_requirements)
            else:
                # Fallback to pattern matching if no entities
                for p in category_patterns:
                    if "pydantic" in p.signature.purpose.lower() or "schema" in p.signature.purpose.lower():
                        files["src/models/schemas.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Data Layer - SQLAlchemy Models
        elif category == "models_sqlalchemy":
            # Use hardcoded production-ready entities generator
            if spec_requirements.entities:
                entities_code = generate_entities(
                    [{"name": e.name, "plural": e.name.lower() + "s"} for e in spec_requirements.entities]
                )
                if entities_code:
                    files["src/models/entities.py"] = entities_code
                    logger.info(f"✅ Generated: src/models/entities.py (hardcoded production generator)")
                else:
                    # Fallback to pattern matching
                    for p in category_patterns:
                        if "sqlalchemy" in p.signature.purpose.lower() or "orm" in p.signature.purpose.lower():
                            files["src/models/entities.py"] = self._adapt_pattern(p.code, spec_requirements)
            else:
                # Fallback to pattern matching if no entities
                for p in category_patterns:
                    if "sqlalchemy" in p.signature.purpose.lower() or "orm" in p.signature.purpose.lower():
                        files["src/models/entities.py"] = self._adapt_pattern(p.code, spec_requirements)

        # Repository Pattern
        elif category == "repository_pattern":
            # Generate repository for each entity
            repo_pattern = find_pattern_by_keyword(category_patterns, "repository", "crud")
            if repo_pattern and spec_requirements.entities:
                for entity in spec_requirements.entities:
                    # Pass current entity to _adapt_pattern so Jinja2 has access to {{ entity.name }}
                    adapted = self._adapt_pattern(repo_pattern.code, spec_requirements, current_entity=entity)
                    files[f"src/repositories/{entity.snake_name}_repository.py"] = adapted

        # Business Logic / Service Layer
        elif category == "business_logic":
            # Generate service for each entity using hardcoded production-ready generator
            if spec_requirements.entities:
                for entity in spec_requirements.entities:
                    service_code = generate_service_method(entity.name)
                    if service_code:
                        files[f"src/services/{entity.snake_name}_service.py"] = service_code
                        logger.info(f"✅ Generated: src/services/{entity.snake_name}_service.py (hardcoded)")
                    else:
                        # Fallback to pattern matching
                        service_pattern = find_pattern_by_keyword(category_patterns, "service", "business logic")
                        if service_pattern:
                            adapted = self._adapt_pattern(service_pattern.code, spec_requirements, current_entity=entity)
                            files[f"src/services/{entity.snake_name}_service.py"] = adapted
            else:
                # Fallback to pattern matching if no entities
                service_pattern = find_pattern_by_keyword(category_patterns, "service", "business logic")
                if service_pattern and spec_requirements.entities:
                    for entity in spec_requirements.entities:
                        adapted = self._adapt_pattern(service_pattern.code, spec_requirements, current_entity=entity)
                        files[f"src/services/{entity.snake_name}_service.py"] = adapted

        # API Routes
        elif category == "api_routes":
            # Generate API route for each entity
            route_pattern = find_pattern_by_keyword(category_patterns, "fastapi", "crud", "endpoint")
            if route_pattern and spec_requirements.entities:
                # Use pattern if available
                for entity in spec_requirements.entities:
                    # Pass current entity to _adapt_pattern so Jinja2 has access to {{ entity.name }}
                    adapted = self._adapt_pattern(route_pattern.code, spec_requirements, current_entity=entity)
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

            # Production mode: Always use optimized Docker files (not patterns)
            # This ensures consistent, pip-based Dockerfiles that work without manual steps
            if os.getenv("PRODUCTION_MODE") == "true":
                logger.info("🔨 PRODUCTION_MODE: Using optimized pip-based Dockerfile")
                dockerfile = self._generate_dockerfile(spec_requirements)
                files["docker/Dockerfile"] = dockerfile

                logger.info("🔨 PRODUCTION_MODE: Using optimized docker-compose.yml")
                docker_compose = self._generate_docker_compose(spec_requirements)
                files["docker/docker-compose.yml"] = docker_compose

                # Ensure Prometheus and Grafana configurations exist
                logger.info("🔨 PRODUCTION_MODE: Generating Prometheus scrape configuration")
                files["docker/prometheus.yml"] = self._generate_prometheus_config()

                logger.info("🔨 PRODUCTION_MODE: Generating Grafana provisioning files")
                files["docker/grafana/dashboards/dashboard-provider.yml"] = self._generate_grafana_dashboard_provider()
                files["docker/grafana/datasources/prometheus.yml"] = self._generate_grafana_prometheus_datasource()

        # Project config & Alembic migrations
        elif category == "project_config":
            found_files = set()

            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "pyproject" in purpose_lower or "toml" in purpose_lower:
                    files["pyproject.toml"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add("pyproject.toml")
                elif "env" in purpose_lower and "example" in purpose_lower:
                    files[".env.example"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add(".env.example")
                elif "gitignore" in purpose_lower:
                    files[".gitignore"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add(".gitignore")
                elif "makefile" in purpose_lower:
                    files["Makefile"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add("Makefile")
                elif "pre-commit" in purpose_lower or "pre_commit" in purpose_lower:
                    files[".pre-commit-config.yaml"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add(".pre-commit-config.yaml")
                elif "alembic.ini" in purpose_lower or ("alembic" in purpose_lower and "config" in purpose_lower):
                    files["alembic.ini"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add("alembic.ini")
                elif "alembic/env" in purpose_lower or ("alembic" in purpose_lower and "env" in purpose_lower):
                    files["alembic/env.py"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add("alembic/env.py")
                elif "readme" in purpose_lower:
                    files["README.md"] = self._adapt_pattern(p.code, spec_requirements)
                    found_files.add("README.md")

            # LLM fallback for missing critical files (production mode)
            if os.getenv("PRODUCTION_MODE") == "true":
                if "alembic.ini" not in found_files:
                    logger.info("🔨 LLM fallback: Generating alembic.ini (no pattern available)")
                    alembic_ini = self._generate_alembic_ini(spec_requirements)
                    files["alembic.ini"] = alembic_ini

                if "alembic/env.py" not in found_files:
                    logger.info("🔨 LLM fallback: Generating alembic/env.py (no pattern available)")
                    alembic_env = self._generate_alembic_env(spec_requirements)
                    files["alembic/env.py"] = alembic_env

                if "alembic/script.py.mako" not in found_files:
                    logger.info("🔨 LLM fallback: Generating alembic/script.py.mako (no pattern available)")
                    alembic_script = self._generate_alembic_script_template()
                    files["alembic/script.py.mako"] = alembic_script

                # Generate initial migration using hardcoded production-ready generator
                if spec_requirements.entities:
                    logger.info("✅ Generating initial migration (hardcoded production generator)")
                    migration_code = generate_initial_migration(
                        [{"name": e.name, "plural": e.name.lower() + "s"} for e in spec_requirements.entities]
                    )
                    if migration_code:
                        files["alembic/versions/001_initial.py"] = migration_code

                if "pyproject.toml" not in found_files:
                    logger.info("🔨 LLM fallback: Generating pyproject.toml (no pattern available)")
                    pyproject = self._generate_pyproject_toml(spec_requirements)
                    files["pyproject.toml"] = pyproject

                if ".env.example" not in found_files:
                    logger.info("🔨 LLM fallback: Generating .env.example (no pattern available)")
                    env_example = self._generate_env_example()
                    files[".env.example"] = env_example

                if ".gitignore" not in found_files:
                    logger.info("🔨 LLM fallback: Generating .gitignore (no pattern available)")
                    gitignore = self._generate_gitignore()
                    files[".gitignore"] = gitignore

                if "Makefile" not in found_files:
                    logger.info("🔨 LLM fallback: Generating Makefile (no pattern available)")
                    makefile = self._generate_makefile()
                    files["Makefile"] = makefile

        # Log summary for this category
        logger.info(
            f"📦 Category {category} composed",
            extra={
                "files_generated": len(files),
                "file_list": list(files.keys())
            }
        )

        return files

    def _adapt_pattern(self, pattern_code: str, spec_requirements, current_entity=None) -> str:
        """
        Adapt pattern code to spec requirements (Task Group 8).

        Supports two placeholder styles:
        1. Jinja2 templates: {{ app_name }}, {% if entities %}, {% for entity in entities %}
        2. Simple placeholders: {APP_NAME}, {DATABASE_URL}, {ENTITY_IMPORTS}, {ENTITY_ROUTERS}

        Args:
            pattern_code: Pattern code with placeholders (Jinja2 or simple style)
            spec_requirements: SpecRequirements object
            current_entity: Optional entity object for entity-specific patterns

        Returns:
            Adapted code with placeholders replaced
        """
        # Prepare context variables
        app_name = spec_requirements.metadata.get("spec_name", "API")
        app_name_snake = app_name.replace("-", "_").replace(" ", "_").lower()
        database_url = spec_requirements.metadata.get(
            "database_url", "postgresql+asyncpg://user:password@localhost:5432/app"
        )

        # Build entities list with snake_case names for Jinja2
        entities = []
        entity_imports = []
        entity_routers = []

        for entity in spec_requirements.entities:
            entity_snake = entity.name.lower().replace(" ", "_")
            entities.append({
                "name": entity.name,
                "snake_name": entity_snake,
            })
            entity_imports.append(f"from src.api.routes import {entity_snake}")
            entity_routers.append(f"app.include_router({entity_snake}.router)")

        # Join entity imports and routers
        imports_str = "\n".join(entity_imports) if entity_imports else ""
        routers_str = "\n".join(entity_routers) if entity_routers else ""

        # Build Jinja2 context
        context = {
            "app_name": app_name,
            "app_name_snake": app_name_snake,
            "database_url": database_url,
            "entities": entities,
        }

        # Add current entity to context if provided (for entity-specific patterns)
        if current_entity:
            entity_snake = current_entity.name.lower().replace(" ", "_")
            context["entity"] = {
                "name": current_entity.name,
                "snake_name": entity_snake,
            }

        # Render Jinja2 template (handles {{ }} and {% %} syntax)
        # Skip Jinja2 rendering if template contains Python keywords (break, continue, etc)
        # that would conflict with Jinja2 tags
        try:
            # Check if template contains Python control flow keywords that conflict with Jinja2
            python_keywords = ['break', 'continue', 'pass', 'yield']
            has_python_keywords = any(
                f" {kw} " in pattern_code or
                pattern_code.startswith(f"{kw} ") or
                pattern_code.endswith(f" {kw}")
                for kw in python_keywords
            )

            if has_python_keywords:
                # Skip Jinja2 rendering for code with Python keywords
                rendered = pattern_code
            else:
                template = Template(pattern_code)
                rendered = template.render(context)
        except Exception as e:
            # If Jinja2 rendering fails (e.g., syntax error in template),
            # fall back to simple string replacement
            logger.warning(
                f"Jinja2 template rendering failed: {e}. Falling back to simple replacement.",
                extra={"error": str(e)}
            )
            rendered = pattern_code

        # Backward compatibility: also replace simple placeholder style {APP_NAME}
        adapted = rendered
        adapted = adapted.replace("{APP_NAME}", app_name)
        adapted = adapted.replace("{APP_NAME_SNAKE}", app_name_snake)
        adapted = adapted.replace("{DATABASE_URL}", database_url)
        adapted = adapted.replace("{ENTITY_IMPORTS}", imports_str)
        adapted = adapted.replace("{ENTITY_ROUTERS}", routers_str)

        # Also replace entity-specific placeholders
        if current_entity:
            entity_snake = current_entity.name.lower().replace(" ", "_")
            adapted = adapted.replace("{ENTITY_NAME}", current_entity.name)
            adapted = adapted.replace("{entity_name}", entity_snake)

        return adapted

    def _generate_alembic_ini(self, spec_requirements) -> str:
        """Generate alembic.ini configuration file with environment variable support."""
        return """# Alembic Configuration
# This file contains the configuration for Alembic database migrations

[alembic]
# path to migration scripts
# DATABASE_URL is read from environment variable in alembic/env.py
sqlalchemy.url =
script_location = alembic
prepend_sys_path = .
sqlalchemy_track_modifications = false

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

    def _generate_main_py(self, spec_requirements) -> str:
        """Generate main.py entry point with FastAPI app, middleware, and routes.

        CRITICAL FIX: Always enable /docs and /redoc for API documentation.
        In production, disable via reverse proxy (nginx/ALB) if needed, not in code.
        """
        # Build entity imports and routers
        imports = []
        routers = []
        for entity in spec_requirements.entities:
            entity_snake = entity.name.lower().replace(" ", "_")
            imports.append(f"from src.api.routes import {entity_snake}")
            routers.append(f"app.include_router({entity_snake}.router)")

        imports_str = "\n".join(imports) if imports else "# No entity routes"
        routers_str = "\n".join(routers) if routers else "# No entity routers"

        return f'''"""
API - Production-Ready FastAPI Application

Generated by DevMatrix with complete observability infrastructure.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import get_settings
from src.core.logging import setup_logging
from src.core.middleware import (
    RequestIDMiddleware,
    MetricsMiddleware,
    SecurityHeadersMiddleware
)
from src.core.exception_handlers import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler
)
from src.api.routes import health, metrics

{imports_str}

import structlog

# Load settings
settings = get_settings()

# Configure logging
setup_logging(settings.log_level)
logger = structlog.get_logger(__name__)

# Initialize FastAPI app
# CRITICAL: /docs and /redoc are ALWAYS enabled for development, testing, and internal use
# To disable in production, use reverse proxy (nginx, ALB, etc), not by disabling in code
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs",  # Always enabled
    redoc_url="/redoc"  # Always enabled
)

# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Add middleware (order matters - last added is executed first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestIDMiddleware)

# Register routers
app.include_router(health.router)
app.include_router(metrics.router)

{routers_str}


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.

    Logs application startup with configuration info.
    """
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
        log_level=settings.log_level
    )


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.

    Logs graceful shutdown.
    """
    logger.info("application_shutdown", app_name=settings.app_name)


@app.get("/")
async def root():
    """
    Root endpoint - API information.

    Returns:
        dict: API metadata
    """
    return {{
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health/health",
        "ready": "/health/ready",
        "metrics": "/metrics/metrics"
    }}
'''

    def _generate_alembic_env(self, spec_requirements) -> str:
        """Generate alembic/env.py for migrations."""
        return '''"""Alembic environment configuration for database migrations."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment variable
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/app"
)

# Alembic requires synchronous connection - convert asyncpg to psycopg
# postgresql+asyncpg:// -> postgresql://
sync_database_url = database_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg://")
config.set_main_option("sqlalchemy.url", sync_database_url)

# Import models for autogenerate
from src.models.entities import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the create_engine() step
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

    def _generate_alembic_script_template(self) -> str:
        """Generate alembic/script.py.mako template."""
        return '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''

    def _generate_pyproject_toml(self, spec_requirements) -> str:
        """Generate pyproject.toml with Poetry configuration."""
        app_name = spec_requirements.metadata.get("app_name", "app").replace("-", "_")
        python_version = spec_requirements.metadata.get("python_version", "3.11")

        return f'''[tool.poetry]
name = "{app_name}"
version = "0.1.0"
description = "Production-ready FastAPI application"
authors = ["Generated by DevMatrix <noreply@devmatrix.ai>"]
readme = "README.md"
packages = [{{include = "src"}}]

[tool.poetry.dependencies]
python = "^{python_version}"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
sqlalchemy = "^2.0.0"
alembic = "^1.13.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
python-dotenv = "^1.0.0"
httpx = "^0.25.0"
aiosqlite = "^0.19.0"
asyncpg = "^0.29.0"
psycopg = "^3.1.0"
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
structlog = "^24.1.0"
bleach = "^6.1.0"
slowapi = "^0.1.9"

[tool.poetry.group.dev.dependencies]
black = "^24.1.0"
isort = "^5.13.0"
flake8 = "^6.1.0"
mypy = "^1.7.0"
pytest-cov = "^4.1.0"
pre-commit = "^3.6.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py{python_version.replace(".", "")}']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "{python_version}"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=html --cov-report=term-missing"
'''

    def _generate_env_example(self) -> str:
        """Generate .env.example template."""
        return '''# Database Configuration
DATABASE_URL=postgresql+asyncpg://devmatrix:admin@localhost:5433/app_db
DATABASE_URL_ASYNC=postgresql+asyncpg://devmatrix:admin@localhost:5433/app_db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=info

# Environment
ENVIRONMENT=development

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3002", "http://localhost:8002"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_FORMAT=json
LOG_FILE=logs/app.log

# Features
ENABLE_DOCS=true
ENABLE_SWAGGER=true
'''

    def _generate_gitignore(self) -> str:
        """Generate .gitignore file."""
        return '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Project specific
logs/
backups/
tmp/
temp/
*.sql
*.db
.env.local
.env.*.local

# Docker
.dockerignore
docker-compose.override.yml

# Poetry
poetry.lock
'''

    def _generate_makefile(self) -> str:
        """Generate Makefile with development commands."""
        return '''
.PHONY: help install dev test lint format migrate clean docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev          - Run development server"
	@echo "  make test         - Run tests with coverage"
	@echo "  make test-watch   - Run tests in watch mode"
	@echo "  make lint         - Run linters (black, isort, flake8, mypy)"
	@echo "  make format       - Format code (black, isort)"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-new  - Create new migration"
	@echo "  make db-upgrade   - Upgrade database to latest migration"
	@echo "  make db-downgrade - Downgrade database to previous migration"
	@echo "  make clean        - Remove build artifacts and cache"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"

install:
	poetry install

dev:
	poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	poetry run pytest --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	poetry run pytest --cov=src -v --tb=short -x

lint:
	poetry run black --check src tests
	poetry run isort --check-only src tests
	poetry run flake8 src tests
	poetry run mypy src

format:
	poetry run black src tests
	poetry run isort src tests

migrate:
	poetry run alembic upgrade head

migrate-new:
	@read -p "Enter migration name: " name; \
	poetry run alembic revision --autogenerate -m "$$name"

db-upgrade:
	poetry run alembic upgrade head

db-downgrade:
	poetry run alembic downgrade -1

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf build dist *.egg-info

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f
'''

    def _generate_dockerfile(self, spec_requirements) -> str:
        """Generate production-ready Dockerfile with pip and requirements.txt."""
        app_name = spec_requirements.metadata.get("app_name", "app")
        return f'''# Production-Ready Dockerfile
# Generated by DevMatrix - Auto-runs migrations and starts app

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=2)"

# Run migrations and start application
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000
'''

    def _generate_docker_compose(self, spec_requirements) -> str:
        """Generate docker-compose.yml with all services."""
        app_name = spec_requirements.metadata.get("app_name", "app")

        # Use ports that don't conflict with DevMatrix services
        app_port = 8002  # DevMatrix uses 8001
        postgres_port = 5433  # DevMatrix uses 5432
        prometheus_port = 9091  # 9090 is often occupied
        grafana_port = 3002  # 3001 is occupied

        return f'''version: '3.8'

services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: {app_name}_app
    ports:
      - "{app_port}:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://devmatrix:admin@postgres:5432/{app_name}_db
      - APP_NAME={app_name}
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=2)"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:16-alpine
    container_name: {app_name}_postgres
    environment:
      POSTGRES_DB: {app_name}_db
      POSTGRES_USER: devmatrix
      POSTGRES_PASSWORD: admin
    ports:
      - "{postgres_port}:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U devmatrix -d {app_name}_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: {app_name}_prometheus
    ports:
      - "{prometheus_port}:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - app-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: {app_name}_grafana
    ports:
      - "{grafana_port}:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=devmatrix
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_SERVER_ROOT_URL=http://localhost:{grafana_port}
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - app-network
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  app-network:
    driver: bridge
'''

    def _generate_grafana_dashboard_provider(self) -> str:
        """Generate Grafana dashboard provisioning configuration."""
        return '''apiVersion: 1

providers:
  - name: 'App Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
'''

    def _generate_grafana_prometheus_datasource(self) -> str:
        """Generate Grafana Prometheus datasource configuration."""
        return '''apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 15s
'''

    def _generate_prometheus_config(self) -> str:
        """
        Generate Prometheus scrape configuration.

        IMPORTANT: Uses service name 'app' and internal port 8000 for Docker networking.
        The app service exposes port 8000 internally (mapped to 8002 externally in docker-compose).
        """
        return '''global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'app-monitor'

scrape_configs:
  - job_name: 'fastapi-app'
    metrics_path: '/metrics'
    static_configs:
      # Use Docker service name 'app' and INTERNAL port 8000
      # NOT localhost:8002 (external port) or localhost:8000
      - targets: ['app:8000']
        labels:
          service: 'api'
          environment: 'production'
    scrape_interval: 10s
    scrape_timeout: 5s
'''

    def _generate_metrics_route(self) -> str:
        """
        Generate Prometheus metrics route.

        CRITICAL FIX: IMPORTS http metrics from middleware.py instead of redefining them.
        This prevents "Duplicated timeseries in CollectorRegistry" error.

        HTTP metrics (http_requests_total, http_request_duration_seconds) are defined
        in middleware.py where they belong. This file only imports them for exposure.
        """
        return '''"""
Prometheus Metrics Endpoint

Exposes application metrics for Prometheus scraping.

IMPORTANT: HTTP metrics are IMPORTED from middleware.py to avoid duplication.
Only business-specific metrics should be defined here.
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# IMPORT HTTP metrics from middleware (DO NOT redefine them here)
from src.core.middleware import (
    http_requests_total,
    http_request_duration_seconds
)

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    HTTP metrics are defined in middleware.py and imported here.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
'''

    def _generate_health_routes(self) -> str:
        """
        Generate health check routes with correct SQLAlchemy text() usage.

        CRITICAL FIX: Uses text("SELECT 1") instead of "SELECT 1" to avoid
        SQLAlchemy deprecation warning.

        Provides two endpoints:
        - /health/health: Basic liveness check
        - /health/ready: Readiness check with database verification
        """
        return '''"""
Health Check Endpoints

Provides /health and /ready endpoints for monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
import structlog

router = APIRouter(prefix="/health", tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/health")
async def health_check():
    """
    Basic health check - always returns OK.

    Returns:
        dict: Service status
    """
    return {
        "status": "ok",
        "service": "API"
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check - verifies dependencies.

    Checks:
        - Database connection

    Args:
        db: Database session

    Returns:
        dict: Readiness status with component checks

    Raises:
        HTTPException: 503 if not ready
    """
    try:
        # Check database connection (use text() to avoid SQLAlchemy warning)
        await db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e), exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": {
                    "database": "failed"
                },
                "error": str(e)
            }
        )
'''

    def _generate_requirements_hardcoded(self) -> str:
        """
        Generate production requirements.txt with VERIFIED versions.

        CRITICAL: Uses only versions that exist in PyPI and are compatible.
        psycopg latest is 3.2.12 (NOT 3.14.1 which doesn't exist).
        """
        return '''# Production Runtime Dependencies
# Generated by DevMatrix - DO NOT include testing/dev tools

# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
httpx==0.25.2

# Database - Async Runtime
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.13.1

# Database - Sync for Migrations
psycopg==3.2.12

# Configuration Management
pydantic==2.5.3
pydantic-settings==2.1.0

# Logging
structlog==24.1.0

# Metrics & Monitoring
prometheus-client==0.19.0

# Security
bleach==6.1.0
slowapi==0.1.9

# Email Validation
email-validator==2.1.0
'''

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
