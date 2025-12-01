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
from typing import Dict, Any, Optional, List
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
from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository
from src.cognitive.patterns.production_patterns import (
    PRODUCTION_PATTERN_CATEGORIES,
    get_composition_order,
)

# ApplicationIR Normalizer for Template Rendering
from src.services.application_ir_normalizer import ApplicationIRNormalizer

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
from src.services.behavior_code_generator import BehaviorCodeGenerator

# Active Learning - Error Knowledge Repository
try:
    from src.cognitive.services.error_knowledge_repository import ErrorKnowledgeRepository
    ACTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ACTIVE_LEARNING_AVAILABLE = False

# Generation Feedback Loop - Anti-Pattern Prevention (NEW)
try:
    from src.learning.prompt_enhancer import get_prompt_enhancer, GenerationPromptEnhancer
    from src.learning.negative_pattern_store import get_negative_pattern_store
    GENERATION_FEEDBACK_AVAILABLE = True
except ImportError:
    GENERATION_FEEDBACK_AVAILABLE = False

# Cognitive Code Generation Service - IR-Centric Enhancement (Bug #143-160)
try:
    from src.services.cognitive_code_generation_service import (
        CognitiveCodeGenerationService,
        create_cognitive_service,
    )
    COGNITIVE_GENERATION_AVAILABLE = True
except ImportError:
    COGNITIVE_GENERATION_AVAILABLE = False


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
        enable_active_learning: bool = True,
        enable_cognitive_pass: bool = True,
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
            enable_active_learning: Enable Active Learning for error avoidance (LEARNING_GAPS Phase 1)
            enable_cognitive_pass: Enable IR-Centric Cognitive Pass for code enhancement (Bug #143-160)
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

        # Initialize Active Learning for error avoidance (LEARNING_GAPS Phase 1)
        self.enable_active_learning = enable_active_learning
        self.error_knowledge_repo: Optional["ErrorKnowledgeRepository"] = None
        if enable_active_learning and ACTIVE_LEARNING_AVAILABLE:
            try:
                self.error_knowledge_repo = ErrorKnowledgeRepository()
                logger.info("Active Learning enabled (LEARNING_GAPS Phase 1)")
            except Exception as e:
                logger.warning(f"Could not initialize Active Learning: {e}")
                self.enable_active_learning = False
        else:
            self.enable_active_learning = False

        # Initialize PromptEnhancer for anti-pattern injection (LEARNING_GAPS Phase 1.1)
        self.enable_prompt_enhancement = True
        self.prompt_enhancer: Optional["GenerationPromptEnhancer"] = None
        if GENERATION_FEEDBACK_AVAILABLE:
            try:
                self.prompt_enhancer = get_prompt_enhancer()
                logger.info("🎓 PromptEnhancer initialized (LEARNING_GAPS Phase 1.1)")
            except Exception as e:
                logger.warning(f"Could not initialize PromptEnhancer: {e}")
                self.enable_prompt_enhancement = False
        else:
            self.enable_prompt_enhancement = False
            logger.debug("PromptEnhancer not available (missing imports)")


        # Bug #168: Initialize AntiPatternAdvisor for route generation advice
        self.anti_pattern_advisor = None
        try:
            from src.learning.anti_pattern_advisor import get_anti_pattern_advisor
            self.anti_pattern_advisor = get_anti_pattern_advisor()
            logger.info("🛡️ AntiPatternAdvisor initialized (Bug #168)")
        except Exception as e:
            logger.debug(f"AntiPatternAdvisor not available: {e}")

        # Initialize modular architecture generator
        self.modular_generator = ModularArchitectureGenerator()

        # Initialize behavior code generator for workflow/state machine generation
        self.behavior_generator = BehaviorCodeGenerator()

        # Initialize PatternBank for production-ready code generation (Task Group 8)
        self.pattern_bank: Optional[PatternBank] = None
        try:
            self.pattern_bank = PatternBank()
            self.pattern_bank.connect()
            logger.info("PatternBank initialized for production patterns (Task Group 8)")
        except Exception as e:
            logger.warning(f"Could not initialize PatternBank: {e}")

        # Initialize Unified RAG Retriever (Milestone 4 - Learning Layer)
        self.rag_retriever = None
        if enable_feedback_loop:
            try:
                from src.rag.unified_retriever import create_unified_retriever
                self.rag_retriever = create_unified_retriever()
                logger.info("Unified RAG Retriever initialized (Neo4j + Qdrant)")
            except Exception as e:
                logger.warning(f"Could not initialize Unified RAG Retriever: {e}")

        # Initialize Cognitive Code Generation Service (Bug #143-160)
        # This service provides IR-centric cognitive enhancement post-generation
        self.enable_cognitive_pass = enable_cognitive_pass
        self.cognitive_service: Optional["CognitiveCodeGenerationService"] = None
        if enable_cognitive_pass and COGNITIVE_GENERATION_AVAILABLE:
            # Note: cognitive_service is initialized lazily in generate_from_application_ir
            # because it requires the ApplicationIR which is only available at generation time
            logger.info("Cognitive Pass enabled (Bug #143-160) - will initialize per-generation")
        else:
            self.enable_cognitive_pass = False
            if enable_cognitive_pass:
                logger.warning("Cognitive Pass requested but not available (missing imports)")

        logger.info(
            "CodeGenerationService initialized",
            extra={
                "max_retries": max_retries,
                "feedback_loop": self.enable_feedback_loop,
                "pattern_promotion": self.enable_pattern_promotion,
                "dag_sync": self.enable_dag_sync,
                "active_learning": self.enable_active_learning,
                "prompt_enhancement": self.enable_prompt_enhancement,
                "cognitive_pass": self.enable_cognitive_pass,
                "pattern_bank_enabled": self.pattern_bank is not None,
                "rag_enabled": self.rag_retriever is not None,
            },
        )

    # ============================================================================
    # ApplicationIR Conversion Helpers (Phase 1 Refactoring)
    # ============================================================================

    def _ir_entity_to_pattern_entity(self, ir_entity) -> Dict[str, Any]:
        """
        Convert ApplicationIR Entity to PatternBank entity format.

        Args:
            ir_entity: Entity from ApplicationIR.domain_model.entities

        Returns:
            Dictionary in PatternBank entity format
        """
        return {
            "name": ir_entity.name,
            "fields": [
                {
                    "name": attr.name,
                    "type": attr.data_type.value,
                    "required": not attr.is_nullable,
                    "unique": attr.is_unique,
                    "default": attr.default_value,
                    "description": attr.description or "",
                }
                for attr in ir_entity.attributes
            ],
            "relationships": [
                {
                    "source": rel.source_entity,
                    "target": rel.target_entity,
                    "type": rel.type.value,
                    "field_name": rel.field_name,
                    "back_populates": rel.back_populates,
                }
                for rel in ir_entity.relationships
            ],
            "description": ir_entity.description or "",
        }

    def _ir_endpoint_to_pattern_endpoint(self, ir_endpoint) -> Dict[str, Any]:
        """
        Convert ApplicationIR Endpoint to PatternBank endpoint format.

        Args:
            ir_endpoint: Endpoint from ApplicationIR.api_model.endpoints

        Returns:
            Dictionary in PatternBank endpoint format
        """
        return {
            "path": ir_endpoint.path,
            "method": ir_endpoint.method.value,
            "operation_id": ir_endpoint.operation_id,
            "summary": ir_endpoint.summary or "",
            "description": ir_endpoint.description or "",
            "parameters": [
                {
                    "name": param.name,
                    "location": param.location.value,
                    "type": param.data_type,
                    "required": param.required,
                    "description": param.description or "",
                }
                for param in ir_endpoint.parameters
            ],
            "request_schema": ir_endpoint.request_schema.name if ir_endpoint.request_schema else None,
            "response_schema": ir_endpoint.response_schema.name if ir_endpoint.response_schema else None,
            "auth_required": ir_endpoint.auth_required,
            "tags": ir_endpoint.tags,
        }

    # ============================================================================
    # Active Learning - Error Avoidance (LEARNING_GAPS Phase 1)
    # ============================================================================

    def _get_avoidance_context(self, app_ir) -> Optional[str]:
        """
        Query learned errors and build avoidance context for code generation.

        This method combines TWO sources of learned errors:
        1. ErrorKnowledgeRepository (original Active Learning)
        2. NegativePatternStore (Generation Feedback Loop - NEW)

        The Generation Feedback Loop closes the gap between smoke test failures
        and code generation, preventing the same errors from recurring.

        Args:
            app_ir: ApplicationIR object with domain_model and api_model

        Returns:
            Avoidance context string or None if no learned errors available
        """
        avoidance_parts = []

        # SOURCE 1: ErrorKnowledgeRepository (original Active Learning)
        if self.enable_active_learning and self.error_knowledge_repo:
            try:
                all_errors = []

                # Query errors for each endpoint pattern
                if app_ir.api_model and app_ir.api_model.endpoints:
                    for endpoint in app_ir.api_model.endpoints:
                        entity_type = self._extract_entity_from_endpoint(endpoint)
                        path_pattern = self._normalize_endpoint_pattern(endpoint.path)
                        pattern_category = self._infer_pattern_category(endpoint)

                        errors = self.error_knowledge_repo.get_relevant_errors(
                            endpoint_pattern=f"{endpoint.method.value} {path_pattern}",
                            entity_type=entity_type,
                            pattern_category=pattern_category,
                            min_confidence=0.6
                        )
                        all_errors.extend(errors)

                # Deduplicate errors by signature
                seen_signatures = set()
                unique_errors = []
                for error in all_errors:
                    if error.error_signature not in seen_signatures:
                        seen_signatures.add(error.error_signature)
                        unique_errors.append(error)

                if unique_errors:
                    avoidance_context = self.error_knowledge_repo.build_avoidance_context(
                        unique_errors,
                        max_errors=10
                    )
                    avoidance_parts.append(avoidance_context)

                    logger.info(
                        "Built avoidance context from ErrorKnowledgeRepo",
                        extra={"unique_errors_count": len(unique_errors)}
                    )

            except Exception as e:
                logger.warning(f"ErrorKnowledgeRepo avoidance failed (non-blocking): {e}")

        # SOURCE 2: NegativePatternStore (Generation Feedback Loop - NEW)
        if GENERATION_FEEDBACK_AVAILABLE:
            try:
                prompt_enhancer = get_prompt_enhancer()
                pattern_store = get_negative_pattern_store()

                # Get statistics first
                stats = pattern_store.get_statistics()
                if stats.get("total_patterns", 0) > 0:
                    # Build anti-pattern warnings for each entity
                    entity_warnings = []

                    if app_ir.domain_model and app_ir.domain_model.entities:
                        for entity in app_ir.domain_model.entities:
                            entity_name = entity.name if hasattr(entity, 'name') else str(entity)
                            patterns = pattern_store.get_patterns_for_entity(
                                entity_name=entity_name,
                                min_occurrences=2  # Only patterns seen 2+ times
                            )
                            for p in patterns[:3]:  # Top 3 per entity
                                warning = p.to_prompt_warning()
                                if warning not in entity_warnings:
                                    entity_warnings.append(warning)

                    # Also get generic patterns (import errors, type errors)
                    for error_type in ["import", "attribute", "type"]:
                        patterns = pattern_store.get_patterns_by_error_type(
                            error_type=error_type,
                            min_occurrences=2
                        )
                        for p in patterns[:2]:  # Top 2 per error type
                            warning = p.to_prompt_warning()
                            if warning not in entity_warnings:
                                entity_warnings.append(warning)

                    if entity_warnings:
                        # Format as anti-pattern warnings
                        anti_pattern_context = "\n\nGENERATION ANTI-PATTERNS (from smoke test failures):"
                        for i, warning in enumerate(entity_warnings[:10], 1):
                            anti_pattern_context += f"\n{i}. {warning}"

                        avoidance_parts.append(anti_pattern_context)

                        # Visible logging for debugging learning loop
                        print(f"🎓 Anti-patterns injected: {len(entity_warnings)} warnings from {stats.get('total_patterns', 0)} stored patterns")

                        logger.info(
                            "Built avoidance context from NegativePatternStore",
                            extra={
                                "anti_patterns_count": len(entity_warnings),
                                "total_stored": stats.get("total_patterns", 0)
                            }
                        )

            except Exception as e:
                logger.warning(f"NegativePatternStore avoidance failed (non-blocking): {e}")

        # Combine all avoidance contexts
        if not avoidance_parts:
            logger.debug("No avoidance context available from any source")
            return None

        combined_context = "\n".join(avoidance_parts)
        logger.info(
            "Combined avoidance context ready",
            extra={"total_length": len(combined_context)}
        )

        return combined_context

    def _extract_entity_from_endpoint(self, endpoint) -> Optional[str]:
        """Extract entity type from endpoint path."""
        path = endpoint.path.lower()
        # Remove path parameters and extract resource name
        # e.g., /products/{id} -> products -> product
        parts = [p for p in path.split('/') if p and not p.startswith('{')]
        if parts:
            # Singularize (simple heuristic)
            resource = parts[0]
            if resource.endswith('s') and not resource.endswith('ss'):
                return resource[:-1]  # products -> product
            return resource
        return None

    def _normalize_endpoint_pattern(self, path: str) -> str:
        """Normalize endpoint path to pattern (replace specific IDs with {id})."""
        import re
        # Replace {param_name} with {id} for generic pattern matching
        return re.sub(r'\{[^}]+\}', '{id}', path)

    def _infer_pattern_category(self, endpoint) -> str:
        """Infer pattern category from endpoint characteristics."""
        method = endpoint.method.value.upper()
        path = endpoint.path.lower()

        # Infer based on HTTP method and path patterns
        if method == "POST" and "/{id}/" in path:
            return "nested_create"
        elif method == "POST":
            return "service"  # Create operations typically in service layer
        elif method == "GET" and "{id}" in path:
            return "repository"  # Single item fetch
        elif method == "GET":
            return "repository"  # List operations
        elif method in ("PUT", "PATCH"):
            return "service"  # Update operations
        elif method == "DELETE":
            return "repository"  # Delete operations
        else:
            return "service"  # Default to service layer

    async def _apply_antipattern_repair_pass(
        self,
        files_dict: Dict[str, str],
        avoidance_context: str,
        app_ir
    ) -> Dict[str, str]:
        """
        Apply Anti-Pattern Repair Pass to generated code.

        This method fixes Bug #1: avoidance_context was calculated but never used.
        After PatternBank composes templates, this pass uses LLM to apply
        learned anti-patterns to prevent known errors.

        Args:
            files_dict: Dictionary of file_path -> file_content from PatternBank
            avoidance_context: String with anti-pattern warnings from _get_avoidance_context
            app_ir: ApplicationIR for context

        Returns:
            Updated files_dict with repairs applied
        """
        # Target files that commonly have anti-pattern issues
        TARGET_PATTERNS = [
            "src/api/routes/",
            "src/models/entities.py",
            "src/models/schemas.py",
            "src/services/",
            "src/repositories/",
        ]

        files_to_repair = []
        for file_path in files_dict:
            if any(pattern in file_path for pattern in TARGET_PATTERNS):
                # Skip __init__.py files
                if file_path.endswith("__init__.py"):
                    continue
                files_to_repair.append(file_path)

        if not files_to_repair:
            logger.debug("No files match anti-pattern repair targets")
            return files_dict

        logger.info(
            f"🔧 Anti-Pattern Repair: Processing {len(files_to_repair)} files",
            extra={"files": files_to_repair}
        )

        repaired_count = 0
        for file_path in files_to_repair:
            original_content = files_dict[file_path]

            try:
                repaired_content = await self._repair_file_with_antipatterns(
                    file_path, original_content, avoidance_context, app_ir
                )

                if repaired_content and repaired_content != original_content:
                    files_dict[file_path] = repaired_content
                    repaired_count += 1
                    logger.info(f"    ✅ Repaired: {file_path}")

            except Exception as e:
                logger.warning(f"    ⚠️ Repair failed for {file_path}: {e}")
                # Keep original content on failure

        print(f"🎓 Anti-Pattern Repair Pass: {repaired_count}/{len(files_to_repair)} files updated")

        return files_dict

    async def _repair_file_with_antipatterns(
        self,
        file_path: str,
        content: str,
        avoidance_context: str,
        app_ir
    ) -> Optional[str]:
        """
        Use LLM to repair a single file based on anti-patterns.

        Args:
            file_path: Path of the file being repaired
            content: Current file content
            avoidance_context: Anti-pattern warnings to apply
            app_ir: ApplicationIR for context

        Returns:
            Repaired content or None if no changes needed
        """
        # Skip small files (likely just boilerplate)
        if len(content) < 100:
            return None

        # Build repair prompt
        prompt = f"""You are a code repair assistant. Your task is to fix potential issues in the following Python code based on learned anti-patterns from previous failures.

## ANTI-PATTERNS TO AVOID
{avoidance_context}

## FILE TO REPAIR: {file_path}
```python
{content}
```

## INSTRUCTIONS
1. Review the code for any violations of the anti-patterns listed above
2. Fix ONLY the issues related to the anti-patterns - do not change working code
3. Common fixes include:
   - Adding missing imports
   - Fixing incorrect HTTP status codes (e.g., 204 for DELETE should return nothing)
   - Adding proper error handling for edge cases
   - Fixing type mismatches in Pydantic models
4. Return the COMPLETE fixed code, not just the changes
5. If no changes are needed, return the original code exactly as-is

## FIXED CODE (complete file):
```python
"""

        try:
            # Use the LLM provider
            response = await self.llm_provider.generate(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.1  # Low temperature for conservative fixes
            )

            # Extract code from response
            repaired_code = self._extract_code_from_response(response)

            if repaired_code and len(repaired_code) > 50:
                return repaired_code
            else:
                return None

        except Exception as e:
            logger.warning(f"LLM repair failed for {file_path}: {e}")
            return None

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract Python code from LLM response."""
        import re

        # Try to extract code block
        code_match = re.search(r'```python\s*(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # If no code block, check if response looks like Python code
        if response.strip().startswith(('import ', 'from ', 'class ', 'def ', '#')):
            return response.strip()

        return None

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

        DEPRECATED: Use generate_from_application_ir() with SpecToApplicationIR instead.
        This method uses legacy IRBuilder which has hardcoded generic flows.

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
        import warnings
        warnings.warn(
            "generate_from_requirements() is deprecated. "
            "Use generate_from_application_ir() with SpecToApplicationIR for production.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.info(
            "Generating code from requirements",
            extra={
                "requirements_count": len(spec_requirements.requirements),
                "entities_count": len(spec_requirements.entities),
                "endpoints_count": len(spec_requirements.endpoints),
                "is_repair": repair_context is not None,
            },
        )

        # Build ApplicationIR (Milestone 4) - ALWAYS construct IR
        from src.cognitive.ir.ir_builder import IRBuilder
        app_ir = IRBuilder.build_from_spec(spec_requirements)
        logger.info(f"ApplicationIR constructed: {app_ir.name} (ID: {app_ir.app_id})")

        # Persist Initial IR to Neo4j
        repo = Neo4jIRRepository()
        repo.save_application_ir(app_ir)
        repo.close()
        logger.info(
            "ApplicationIR persisted to Neo4j",
            extra={
                "app_id": str(app_ir.app_id),
                "app_name": app_ir.name,
                "uses_application_ir": True
            }
        )

        # PRODUCTION MODE: Use PatternBank and modular architecture
        logger.info(
            "Using production-ready templates",
            extra={"pattern_bank_available": self.pattern_bank is not None}
        )

        logger.info("Retrieving production-ready patterns from PatternBank")

        # PHASE 1 REFACTORING: Pass app_ir instead of spec_requirements
        patterns = await self._retrieve_production_patterns(app_ir=app_ir)

        # Count patterns retrieved
        total_patterns = sum(len(p) for p in patterns.values())
        logger.info(
            "Retrieved patterns from PatternBank",
            extra={
                "categories": len(patterns),
                "total_patterns": total_patterns,
                "uses_application_ir": True
            }
        )

        # Compose all files from patterns
        logger.info("Composing production-ready application from patterns")

        try:
            # PHASE 1 REFACTORING: Pass app_ir instead of spec_requirements
            files_dict = await self._compose_patterns(patterns, app_ir=app_ir)

            # Fallback for missing essential files
            logger.info("Checking for missing essential files")
            llm_generated = await self._generate_with_llm_fallback(files_dict, spec_requirements)
            files_dict.update(llm_generated)

            # Generate behavior code (workflows, state machines, validators)
            if app_ir and app_ir.behavior_model:
                logger.info('Generating behavior code from BehaviorModelIR')
                behavior_files = self.behavior_generator.generate_business_logic(app_ir.behavior_model)
                
                logger.info(
                    'Generated behavior code',
                    extra={
                        'files_count': len(behavior_files),
                        'workflows': len([f for f in behavior_files if 'workflows' in f]),
                        'state_machines': len([f for f in behavior_files if 'state_machines' in f]),
                        'validators': len([f for f in behavior_files if 'validators' in f]),
                        'event_handlers': len([f for f in behavior_files if 'events' in f]),
                    }
                )
                
                # Add behavior files to the generated files dict
                files_dict.update(behavior_files)
            else:
                logger.info('No BehaviorModelIR found, skipping behavior generation')


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
                logger.error(
                    "Modular generation produced no files",
                    extra={
                        "reason": "ModularArchitectureGenerator may have failed or spec requirements incomplete"
                    }
                )
                raise RuntimeError("Failed to generate application files")

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

        except Exception as syntax_error:
            # RECORD ERROR (Milestone 4)
            if self.enable_feedback_loop and self.pattern_store:
                error_id = str(uuid.uuid4())
                await self.pattern_store.store_error(
                    ErrorPattern(
                        error_id=error_id,
                        task_id="requirements_gen",
                        task_description=spec_requirements.metadata.get('spec_name', 'API'),
                        error_type="syntax_error",
                        error_message=str(syntax_error),
                        failed_code=str(syntax_error),
                        attempt=1,
                        timestamp=datetime.now()
                    )
                )

            if allow_syntax_errors:
                # Log warning but continue - repair loop will fix it
                logger.warning(
                    f"Generated code has syntax errors (will be repaired): {syntax_error}",
                    extra={"syntax_error": str(syntax_error)}
                )
                # Return partial generated code
                return str(syntax_error)
            else:
                # Strict mode - fail immediately
                raise ValueError(f"Generated code has syntax errors: {syntax_error}")

        # RECORD SUCCESS CANDIDATE (Milestone 4 - Pattern Promotion)
        if self.enable_pattern_promotion and self.pattern_feedback:
            try:
                await self.pattern_feedback.register_candidate(
                    code=generated_code,
                    spec_metadata=spec_requirements.metadata,
                    validation_result={"syntax_valid": True}
                )
                logger.info("Registered pattern candidate for promotion")
            except Exception as e:
                logger.warning(f"Failed to register pattern candidate: {e}")

        logger.info(
            "Code generation from requirements successful",
            extra={
                "code_length": len(generated_code),
                "entities_expected": len(spec_requirements.entities),
                "endpoints_expected": len(spec_requirements.endpoints),
            },
        )

        return generated_code

    async def generate_from_application_ir(
        self,
        application_ir,
        allow_syntax_errors: bool = False,
        repair_context: Optional[str] = None
    ) -> str:
        """
        Generate code directly from ApplicationIR (IR-centric approach)

        This method accepts pre-built ApplicationIR from Phase 1 (spec extraction),
        avoiding duplication of IR construction and avoiding the need to rebuild
        from spec_requirements.

        Args:
            application_ir: ApplicationIR object from SpecToApplicationIR
            allow_syntax_errors: If True, return code even with syntax errors.
                                Useful when repair loop will fix errors post-generation.
            repair_context: Optional repair context with compliance failures and
                           instructions for fixing the code. Used in Phase 6.5 repair loop.

        Returns:
            Complete generated code as string (models + routes + main)
        """
        app_ir = application_ir
        logger.info(
            "Generating code from ApplicationIR (IR-centric)",
            extra={
                "app_name": app_ir.name,
                "app_id": str(app_ir.app_id),
                "has_domain_model": app_ir.domain_model is not None,
                "has_api_model": app_ir.api_model is not None,
                "has_behavior_model": app_ir.behavior_model is not None,
                "has_validation_model": app_ir.validation_model is not None,
                "is_repair": repair_context is not None,
            },
        )

        # PRE-GENERATION VALIDATION: Ensure IR has minimum required data
        validation_errors = self._validate_ir_for_generation(app_ir)
        if validation_errors:
            error_msg = f"ApplicationIR validation failed: {'; '.join(validation_errors)}"
            logger.error(
                error_msg,
                extra={
                    "validation_errors": validation_errors,
                    "app_name": app_ir.name,
                    "phase": "pre_generation"
                }
            )
            if allow_syntax_errors:
                # Return fallback structure instead of crashing
                return self._generate_fallback_structure(app_ir, error_msg)
            else:
                raise ValueError(error_msg)

        logger.info(
            "IR validation passed",
            extra={
                "entities_count": len(app_ir.domain_model.entities) if app_ir.domain_model else 0,
                "endpoints_count": len(app_ir.api_model.endpoints) if app_ir.api_model else 0,
                "phase": "pre_generation"
            }
        )

        # ACTIVE LEARNING: Query learned errors for avoidance context (LEARNING_GAPS Phase 1)
        avoidance_context = self._get_avoidance_context(app_ir)
        if avoidance_context:
            logger.info(
                "Active Learning: Avoidance context prepared",
                extra={
                    "avoidance_context_length": len(avoidance_context),
                    "phase": "pre_generation"
                }
            )
            # Merge avoidance context with repair_context if provided
            if repair_context:
                repair_context = f"{repair_context}\n\n{avoidance_context}"
            else:
                repair_context = avoidance_context

        # Persist ApplicationIR to Neo4j
        repo = Neo4jIRRepository()
        repo.save_application_ir(app_ir)
        repo.close()
        logger.info(
            "ApplicationIR persisted to Neo4j",
            extra={
                "app_id": str(app_ir.app_id),
                "app_name": app_ir.name,
                "uses_application_ir": True
            }
        )

        # PRODUCTION MODE: Use PatternBank and modular architecture
        logger.info(
            "Using production-ready templates",
            extra={"pattern_bank_available": self.pattern_bank is not None}
        )

        logger.info("Retrieving production-ready patterns from PatternBank")

        # Pass app_ir to retrieve patterns
        patterns = await self._retrieve_production_patterns(app_ir=app_ir)

        # Count patterns retrieved
        total_patterns = sum(len(p) for p in patterns.values())
        logger.info(
            "Retrieved patterns from PatternBank",
            extra={
                "categories": len(patterns),
                "total_patterns": total_patterns,
                "uses_application_ir": True
            }
        )

        # Compose all files from patterns
        logger.info("Composing production-ready application from patterns")

        try:
            # Pass app_ir to compose patterns
            files_dict = await self._compose_patterns(patterns, app_ir=app_ir)

            # Fallback for missing essential files (requirements.txt, README.md, etc.)
            logger.info("Checking for missing essential files")
            llm_generated = await self._generate_with_llm_fallback(
                files_dict,
                spec_requirements=None,
                application_ir=app_ir
            )
            files_dict.update(llm_generated)

            # Generate behavior code (workflows, state machines, validators)
            if app_ir and app_ir.behavior_model:
                logger.info('Generating behavior code from BehaviorModelIR')
                behavior_files = self.behavior_generator.generate_business_logic(app_ir.behavior_model)

                logger.info(
                    'Generated behavior code',
                    extra={
                        'files_count': len(behavior_files),
                        'workflows': len([f for f in behavior_files if 'workflows' in f]),
                        'state_machines': len([f for f in behavior_files if 'state_machines' in f]),
                        'validators': len([f for f in behavior_files if 'validators' in f]),
                        'event_handlers': len([f for f in behavior_files if 'events' in f]),
                    }
                )

                # Add behavior files to the generated files dict
                files_dict.update(behavior_files)
            else:
                logger.info('No BehaviorModelIR found, skipping behavior generation')

            # ANTI-PATTERN REPAIR PASS: Apply learned patterns to prevent known errors
            # This fixes Bug #1: avoidance_context calculated but never used
            if avoidance_context:
                logger.info(
                    "🔧 Applying Anti-Pattern Repair Pass",
                    extra={"avoidance_context_length": len(avoidance_context)}
                )
                files_dict = await self._apply_antipattern_repair_pass(
                    files_dict, avoidance_context, app_ir
                )

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
                logger.error(
                    "Modular generation produced no files",
                    extra={
                        "reason": "ModularArchitectureGenerator may have failed or ApplicationIR incomplete"
                    }
                )
                raise RuntimeError("Failed to generate application files")

            # POST-GENERATION VALIDATION: Ensure output has minimum required structure
            structure_errors = self._validate_generated_structure(files_dict)
            if structure_errors:
                error_msg = f"Generated structure incomplete: {'; '.join(structure_errors)}"
                logger.error(
                    error_msg,
                    extra={
                        "structure_errors": structure_errors,
                        "files_generated": list(files_dict.keys()),
                        "phase": "post_generation"
                    }
                )
                if allow_syntax_errors:
                    # Log but continue - repair loop may fix it
                    logger.warning(
                        "Structure validation failed but allow_syntax_errors=True, continuing",
                        extra={"errors": structure_errors}
                    )
                else:
                    raise RuntimeError(error_msg)

            logger.info(
                "Structure validation passed",
                extra={
                    "files_count": len(files_dict),
                    "has_main": "src/main.py" in files_dict,
                    "has_entities": "src/models/entities.py" in files_dict,
                    "has_schemas": "src/models/schemas.py" in files_dict,
                    "phase": "post_generation"
                }
            )

            # COGNITIVE PASS: IR-Centric Enhancement (Bug #143-160)
            # Enhance generated code using learned patterns and IR contracts
            if self.enable_cognitive_pass and COGNITIVE_GENERATION_AVAILABLE:
                files_dict = await self._apply_cognitive_pass(files_dict, app_ir)

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
                    "mode": "ir_centric_generation"
                }
            )

        except Exception as gen_error:
            # RECORD ERROR (Milestone 4)
            if self.enable_feedback_loop and self.pattern_store:
                error_id = str(uuid.uuid4())
                await self.pattern_store.store_error(
                    ErrorPattern(
                        error_id=error_id,
                        task_id="ir_gen",
                        task_description=app_ir.name,
                        error_type="generation_error",
                        error_message=str(gen_error),
                        failed_code=str(gen_error),
                        attempt=1,
                        timestamp=datetime.now()
                    )
                )

            # Log the full error with traceback for debugging
            import traceback
            logger.error(
                f"Code generation from ApplicationIR failed: {gen_error}",
                extra={
                    "error_type": type(gen_error).__name__,
                    "error_message": str(gen_error),
                    "traceback": traceback.format_exc()
                }
            )

            # ALWAYS FAIL ON GENERATION ERROR - No fallback mode
            # This ensures we see the real error and can fix it
            logger.error(
                f"🛑 Code generation failed - NO FALLBACK: {gen_error}",
                extra={"fallback_mode": False, "allow_syntax_errors": allow_syntax_errors}
            )
            raise ValueError(f"Code generation failed: {gen_error}") from gen_error

        # RECORD SUCCESS CANDIDATE (Milestone 4 - Pattern Promotion)
        if self.enable_pattern_promotion and self.pattern_feedback:
            try:
                await self.pattern_feedback.register_candidate(
                    code=generated_code,
                    spec_metadata={"app_name": app_ir.name, "app_id": str(app_ir.app_id)},
                    validation_result={"syntax_valid": True}
                )
                logger.info("Registered pattern candidate for promotion")
            except Exception as e:
                logger.warning(f"Failed to register pattern candidate: {e}")

        logger.info(
            "Code generation from ApplicationIR successful",
            extra={
                "code_length": len(generated_code),
                "app_name": app_ir.name,
                "uses_ir_centric": True,
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
        prompt_parts.append("   - Field validations using Pydantic Field: Field(gt=0) for price, Field(ge=0) for stock, EmailStr for email")
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

   CRITICAL: NEVER mix Field parameters with comparison operators
   ❌ WRONG: Field(..., gt=0, >= 0)  # INVALID SYNTAX
   ✅ CORRECT: Field(..., gt=0)  # Use ONLY Field parameters, not comparison operators

3. **FastAPI Routes**: Implement ALL endpoints with:
   - Correct HTTP methods matching spec
   - Path parameters with type hints
   - Request/response models from Pydantic
   - Appropriate storage layer (in-memory dicts for simple specs)
   - Complete CRUD logic (not placeholders)

4. **Business Logic**: Implement ALL rules:
   - Validations using Pydantic Field: Field(gt=0) for positive numbers, Field(ge=0) for non-negative, EmailStr for email, Field(max_length=N) for strings
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
        generated_prompt = strategy.generate_prompt(context)

        # Extract prompt text from GeneratedPrompt object
        base_prompt = generated_prompt.prompt if hasattr(generated_prompt, 'prompt') else generated_prompt
        
        # LEARNING_GAPS Phase 1.1: Enhance prompt with learned anti-patterns
        if self.enable_prompt_enhancement and self.prompt_enhancer:
            try:
                # Detect task type from task name/description
                task_lower = task.name.lower() + " " + task.description.lower()
                
                if "entity" in task_lower or "model" in task_lower or "entities.py" in task_lower:
                    # Entity generation task
                    entity_name = self._extract_entity_name_from_task(task)
                    if entity_name:
                        enhanced = self.prompt_enhancer.enhance_entity_prompt(base_prompt, entity_name)
                        injected_count = len(self.prompt_enhancer.get_injected_patterns())
                        logger.info(f"🎓 Prompt enhanced for entity '{entity_name}' with {injected_count} anti-patterns")
                        return enhanced
                
                elif "endpoint" in task_lower or "route" in task_lower or "api" in task_lower:
                    # Endpoint generation task
                    endpoint_pattern = self._extract_endpoint_pattern_from_task(task)
                    if endpoint_pattern:
                        enhanced = self.prompt_enhancer.enhance_endpoint_prompt(base_prompt, endpoint_pattern)
                        injected_count = len(self.prompt_enhancer.get_injected_patterns())
                        logger.info(f"🎓 Prompt enhanced for endpoint '{endpoint_pattern}' with {injected_count} anti-patterns")
                        return enhanced
                
                elif "schema" in task_lower or "pydantic" in task_lower:
                    # Schema generation task
                    schema_name = self._extract_schema_name_from_task(task)
                    if schema_name:
                        enhanced = self.prompt_enhancer.enhance_schema_prompt(base_prompt, schema_name)
                        injected_count = len(self.prompt_enhancer.get_injected_patterns())
                        logger.info(f"🎓 Prompt enhanced for schema '{schema_name}' with {injected_count} anti-patterns")
                        return enhanced
                
                elif "service" in task_lower or "business logic" in task_lower:
                    # Service/business logic generation task
                    entity_name = self._extract_entity_name_from_task(task)
                    if entity_name:
                        enhanced = self.prompt_enhancer.enhance_service_prompt(base_prompt, entity_name)
                        injected_count = len(self.prompt_enhancer.get_injected_patterns())
                        logger.info(f"🎓 Prompt enhanced for service '{entity_name}' with {injected_count} anti-patterns")
                        return enhanced
                
                elif "validation" in task_lower or "constraint" in task_lower or "rule" in task_lower:
                    # Validation/constraint generation task
                    # Use generic enhancement with validation-specific error types
                    enhanced = self.prompt_enhancer.enhance_generic_prompt(
                        base_prompt, 
                        error_types=["ValidationError", "IntegrityError", "ConstraintViolation"]
                    )
                    injected_count = len(self.prompt_enhancer.get_injected_patterns())
                    if injected_count > 0:
                        logger.info(f"🎓 Prompt enhanced for validation with {injected_count} anti-patterns")
                    return enhanced

                
                # Generic enhancement for other tasks
                enhanced = self.prompt_enhancer.enhance_generic_prompt(base_prompt)
                injected_count = len(self.prompt_enhancer.get_injected_patterns())
                if injected_count > 0:
                    logger.info(f"🎓 Prompt enhanced (generic) with {injected_count} anti-patterns")
                return enhanced
                
            except Exception as e:
                logger.warning(f"Failed to enhance prompt: {e}, using base prompt")
                return base_prompt
        
        return base_prompt


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
        generated_prompt = strategy.generate_prompt_with_feedback(context)

        # Extract prompt text from GeneratedPrompt object
        return generated_prompt.prompt if hasattr(generated_prompt, 'prompt') else generated_prompt

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
   - Example: ```python\ncode here\n```
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

    def _extract_entity_name_from_task(self, task: MasterPlanTask) -> Optional[str]:
        """Extract entity name from task description/name (LEARNING_GAPS Phase 1.1)."""
        import re
        text = task.name + " " + task.description
        
        # "Generate/Create Product entity" -> "Product"
        match = re.search(r'(?:generate|create|implement|add)\s+(\w+)\s+(?:entity|model)', text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        
        # "entities.py for Cart" -> "Cart"
        match = re.search(r'entities\.py\s+for\s+(\w+)', text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        
        return None
    
    def _extract_endpoint_pattern_from_task(self, task: MasterPlanTask) -> Optional[str]:
        """Extract endpoint pattern from task description/name (LEARNING_GAPS Phase 1.1)."""
        import re
        text = task.name + " " + task.description
        
        # "POST /products" -> "/products"
        match = re.search(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/{}-]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # "endpoint for /products" -> "/products"
        match = re.search(r'endpoint\s+for\s+(/[\w/{}-]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_schema_name_from_task(self, task: MasterPlanTask) -> Optional[str]:
        """Extract schema name from task description/name (LEARNING_GAPS Phase 1.1)."""
        import re
        text = task.name + " " + task.description
        
        # "ProductCreate schema" -> "ProductCreate"
        match = re.search(r'(\w+(?:Create|Update|Response|List|Base))\s+schema', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # "Pydantic Product model" -> "Product"
        match = re.search(r'Pydantic\s+(\w+)\s+model', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None

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

        # 2.5. Fallback for missing essential files (no patterns available)
        # Uses LLM with context to generate code when patterns are unavailable
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
        self, app_ir=None, spec_requirements=None
    ) -> Dict[str, list]:
        """
        Retrieve production-ready patterns for all categories (Task Group 8).

        Uses SPECIFIC purpose strings from populate_production_patterns.py to ensure
        correct pattern retrieval via PatternBank.hybrid_search().

        **Phase 1 Refactoring**: Now accepts ApplicationIR as primary input with
        backward compatibility for spec_requirements.

        Args:
            app_ir: ApplicationIR object (preferred, primary input)
            spec_requirements: SpecRequirements object (deprecated, backward compat)

        Returns:
            Dictionary mapping category name to list of StoredPattern objects
            {
                "core_config": [StoredPattern(...), ...],
                "database_async": [StoredPattern(...), ...],
                ...
            }

        Raises:
            ValueError: If neither app_ir nor spec_requirements is provided
        """
        # Validate inputs
        if app_ir is None and spec_requirements is None:
            raise ValueError("Either app_ir or spec_requirements must be provided")

        # Deprecation warning if using spec_requirements
        if spec_requirements is not None and app_ir is None:
            logger.warning(
                "Using spec_requirements in _retrieve_production_patterns is deprecated. "
                "Please migrate to ApplicationIR.",
                extra={"migration_phase": "phase_1"}
            )

        # Log source of patterns
        if app_ir is not None:
            logger.info(
                "Extracting patterns from ApplicationIR",
                extra={
                    "app_id": str(app_ir.app_id),
                    "entities_count": len(app_ir.domain_model.entities),
                    "endpoints_count": len(app_ir.api_model.endpoints),
                    "uses_application_ir": True,
                }
            )
        else:
            logger.info(
                "Extracting patterns from SpecRequirements (deprecated path)",
                extra={
                    "entities_count": len(spec_requirements.entities) if hasattr(spec_requirements, 'entities') else 0,
                    "endpoints_count": len(spec_requirements.endpoints) if hasattr(spec_requirements, 'endpoints') else 0,
                    "uses_application_ir": False,
                }
            )
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
        self, patterns: Dict[str, list], app_ir=None, spec_requirements=None
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

        **Phase 1 Refactoring**: Now accepts ApplicationIR as primary input with
        backward compatibility for spec_requirements.

        Args:
            patterns: Dictionary of patterns by category
            app_ir: ApplicationIR object (preferred, primary input)
            spec_requirements: SpecRequirements object (deprecated, backward compat)

        Returns:
            Dictionary mapping file paths to generated code

        Raises:
            ValueError: If neither app_ir nor spec_requirements is provided
        """
        # Validate inputs
        if app_ir is None and spec_requirements is None:
            raise ValueError("Either app_ir or spec_requirements must be provided")

        # Deprecation warning if using spec_requirements
        if spec_requirements is not None and app_ir is None:
            logger.warning(
                "Using spec_requirements in _compose_patterns is deprecated. "
                "Please migrate to ApplicationIR.",
                extra={"migration_phase": "phase_1"}
            )

        # Log source of composition
        if app_ir is not None:
            logger.info(
                "Composing patterns from ApplicationIR",
                extra={
                    "app_id": str(app_ir.app_id),
                    "entities_count": len(app_ir.domain_model.entities),
                    "endpoints_count": len(app_ir.api_model.endpoints),
                    "flows_count": len(app_ir.behavior_model.flows),
                    "uses_application_ir": True,
                }
            )
        else:
            logger.info(
                "Composing patterns from SpecRequirements (deprecated path)",
                extra={"uses_application_ir": False}
            )

        files = {}

        # Get composition order (priority-based)
        composition_order = get_composition_order()

        for category in composition_order:
            if category not in patterns or not patterns[category]:
                logger.debug(f"No patterns found for category: {category}")
                continue

            # Compose patterns for this category
            # Use app_ir if available, otherwise fall back to spec_requirements
            category_files = await self._compose_category_patterns(
                category,
                patterns[category],
                app_ir if app_ir is not None else spec_requirements
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

        # Always try PatternBank first, fallback to generator
        if exact_main:
            # Use app_ir if available, otherwise fall back to spec_requirements
            files["src/main.py"] = self._adapt_pattern(
                exact_main.code,
                app_ir=app_ir,
                spec_requirements=spec_requirements
            )
            logger.info("✅ Added main.py from PatternBank")
        else:
            # Fallback: Generate main.py directly if not found in PatternBank
            # Use app_ir if available, otherwise fall back to spec_requirements
            main_py_code = self._generate_main_py(app_ir if app_ir is not None else spec_requirements)
            files["src/main.py"] = main_py_code
            logger.info("✅ Generated main.py (fallback from pattern not found)")

        return files

    async def _generate_with_llm_fallback(
        self, existing_files: Dict[str, str], spec_requirements=None, application_ir=None
    ) -> Dict[str, str]:
        """
        Generate missing essential files using LLM when no patterns available.

        Uses IR context to generate code, then iterates with repair loop learning if needed.
        Supports both spec_requirements (legacy) and application_ir (IR-centric) modes.

        Args:
            existing_files: Dictionary of files already generated from patterns
            spec_requirements: SpecRequirements with project context (legacy mode)
            application_ir: ApplicationIR for IR-centric generation (preferred)

        Returns:
            Dictionary of generated files for missing essentials (hardcoded or LLM-based)
        """
        logger.info(
            "🔍 Checking for missing essential files",
            extra={
                "existing_count": len(existing_files),
                "mode": "ir_centric" if application_ir else "spec_requirements"
            }
        )
        llm_files = {}

        # Define essential files that should exist
        # Note: requirements.txt and poetry.lock don't need spec_requirements
        # README.md is ALWAYS required - generates minimal version if no context
        essential_files = {
            "requirements.txt": self._generate_requirements_txt,
            "poetry.lock": self._generate_poetry_lock,
            "README.md": self._generate_readme_md,  # Always include README
        }

        # Generate missing files using IR-aware generators
        for file_path, generator_func in essential_files.items():
            # Bug fix: Also regenerate if file exists but is empty/too short
            existing_content = existing_files.get(file_path, "")
            needs_generation = (
                file_path not in existing_files or
                (file_path == "README.md" and len(existing_content.strip()) < 100)  # README needs content
            )

            if needs_generation:
                reason = "no pattern in PatternBank" if file_path not in existing_files else "existing content too short"
                logger.info(
                    f"🤖 Generating {file_path} ({reason})",
                    extra={"file": file_path}
                )
                try:
                    # Pass either spec_requirements or application_ir
                    context = spec_requirements if spec_requirements else application_ir
                    content = await generator_func(context, existing_files)
                    llm_files[file_path] = content
                    logger.info(f"✅ Generated: {file_path}")
                except Exception as e:
                    logger.error(
                        f"❌ Generation failed for {file_path}: {e}",
                        extra={"file": file_path, "error": str(e)}
                    )
                    # Don't fail the entire generation, continue with other files

        return llm_files

    async def _generate_requirements_txt(
        self, spec_requirements, existing_files: Dict[str, str]
    ) -> str:
        """Generate requirements.txt - always use hardcoded verified versions for stability."""
        return self._generate_requirements_hardcoded()

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
        self, context_source, existing_files: Dict[str, str]
    ) -> str:
        """Generate README.md using LLM with rich context.

        Supports both SpecRequirements (legacy) and ApplicationIR (IR-centric).
        Falls back to minimal README if no context provided.
        """
        # If no context provided, generate minimal README
        if context_source is None:
            logger.info("Generating minimal README.md (no context provided)")
            file_structure = "\n".join([
                f"- {path}" for path in sorted(existing_files.keys())[:20]
            ])
            return f"""# FastAPI Application

Production-ready FastAPI application generated by DevMatrix.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn src.main:app --reload
```

## Project Structure

```
{file_structure}
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
pytest tests/ -v
```

---
Generated by DevMatrix Code Generation Engine
"""

        # Detect if we're using ApplicationIR or SpecRequirements
        is_application_ir = hasattr(context_source, 'domain_model') and hasattr(context_source, 'api_model')

        if is_application_ir:
            # ApplicationIR mode
            project_name = context_source.name or "FastAPI Application"
            description = context_source.description or "Production-ready FastAPI application"
            version = context_source.version or "1.0.0"

            # Extract entities from DomainModelIR
            entities = context_source.domain_model.entities if context_source.domain_model else []
            entity_details = "\n".join([
                f"- **{e.name}**: {', '.join(f.name for f in e.fields)}"
                for e in entities
            ])

            # Extract endpoints from APIModelIR
            endpoints = context_source.api_model.endpoints if context_source.api_model else []
            endpoint_details = "\n".join([
                f"- `{ep.method} {ep.path}`: {ep.description or 'No description'}"
                for ep in endpoints[:10]  # Limit to first 10
            ])
            endpoint_count = len(endpoints)
        else:
            # SpecRequirements mode (legacy)
            project_name = context_source.metadata.get("project_name", "FastAPI Application")
            description = context_source.metadata.get("description", "Production-ready FastAPI application")
            version = context_source.metadata.get("version", "1.0.0")

            entity_details = "\n".join([
                f"- **{e.name}**: {', '.join(f.name for f in e.fields)}"
                for e in context_source.entities
            ])

            endpoint_details = "\n".join([
                f"- `{ep.method} {ep.path}`: {ep.description}"
                for ep in context_source.endpoints[:10]  # Limit to first 10
            ])
            endpoint_count = len(context_source.endpoints)

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
{"... and more" if endpoint_count > 10 else ""}

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
        try:
            response = await self.llm_client.generate_with_caching(
                task_type="documentation",
                complexity="medium",
                cacheable_context={"system_prompt": "You are a technical documentation expert specializing in README files for FastAPI projects."},
                variable_prompt=context,
                max_tokens=2500,
                temperature=0.5  # Balanced creativity for documentation
            )

            content = response["content"].strip()

            # Fix #5: Validate LLM response, use fallback if too short
            if len(content) < 200:
                logger.warning(f"⚠️ LLM README response too short ({len(content)} chars), using fallback")
                return self._generate_readme_fallback(project_name, description, entity_details, endpoint_details, file_structure)

            return content

        except Exception as e:
            logger.error(f"❌ LLM README generation failed: {e}, using fallback")
            return self._generate_readme_fallback(project_name, description, entity_details, endpoint_details, file_structure)

    def _generate_readme_fallback(
        self,
        project_name: str,
        description: str,
        entity_details: str,
        endpoint_details: str,
        file_structure: str
    ) -> str:
        """Fix #5: Generate fallback README when LLM fails."""
        return f'''# {project_name}

{description}

## Features

{entity_details}

## API Endpoints

{endpoint_details}

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker (optional)

### Installation

```bash
# Clone and setup
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Run migrations
alembic upgrade head

# Start the server
uvicorn src.main:app --reload
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

```bash
pytest tests/ -v --cov=src
```

## Project Structure

```
{file_structure}
```

## Docker

```bash
docker-compose up -d
```

---
Generated by DevMatrix Code Generation Engine
'''

    async def _compose_category_patterns(
        self, category: str, category_patterns: list, spec_or_ir
    ) -> Dict[str, str]:
        """
        Compose patterns for a specific category (Task Group 8).

        Maps StoredPattern objects to output files by matching purpose strings.

        **Phase 1 Refactoring**: Now accepts ApplicationIR as primary input with
        backward compatibility for spec_or_ir.

        Args:
            category: Category name (e.g., "core_config", "database_async")
            category_patterns: List of StoredPattern objects for this category
            spec_or_ir: SpecRequirements or ApplicationIR object

        Returns:
            Dictionary of files generated for this category
        """
        # Detect type of input (ApplicationIR or SpecRequirements)
        from src.cognitive.ir.application_ir import ApplicationIR
        is_app_ir = isinstance(spec_or_ir, ApplicationIR)

        # Unified accessors for entities and endpoints
        def get_entities():
            """Get entities from either ApplicationIR or SpecRequirements."""
            if is_app_ir:
                return spec_or_ir.domain_model.entities if spec_or_ir.domain_model else []
            else:
                return spec_or_ir.entities or []

        def get_endpoints():
            """Get endpoints from either ApplicationIR or SpecRequirements."""
            if is_app_ir:
                return spec_or_ir.api_model.endpoints if spec_or_ir.api_model else []
            else:
                return spec_or_ir.endpoints or []

        def get_entity_fields(entity):
            """Get fields from entity, handling both ApplicationIR and SpecRequirements structures."""
            # ApplicationIR uses 'attributes', SpecRequirements uses 'fields'
            if hasattr(entity, 'attributes'):
                # Normalize ApplicationIR attributes to look like SpecRequirements fields
                # Create a simple wrapper class to hold field data
                class NormalizedField:
                    def __init__(self, name, type_, required, default, constraints=None):
                        self.name = name
                        self.type = type_
                        self.required = required
                        self.default = default
                        self.constraints = constraints or {}

                normalized_fields = []
                for attr in entity.attributes:
                    field_type = attr.data_type.value if hasattr(attr.data_type, 'value') else str(attr.data_type)
                    normalized_fields.append(NormalizedField(
                        name=attr.name,
                        type_=field_type,
                        required=not attr.is_nullable,
                        default=attr.default_value,
                        constraints=getattr(attr, 'constraints', {}),
                    ))
                return normalized_fields
            else:
                return getattr(entity, 'fields', [])

        def get_entity_snake_name(entity):
            """Get snake_name from entity, handling both ApplicationIR and SpecRequirements."""
            # Check if entity already has snake_name (SpecRequirements)
            if hasattr(entity, 'snake_name'):
                return entity.snake_name
            else:
                # For ApplicationIR, convert entity.name to snake_case
                import re
                name = entity.name
                # Convert to snake_case
                s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        def get_validation_ground_truth():
            """Get validation ground truth from either ApplicationIR or SpecRequirements."""
            # 1. Try to use local spec_or_ir if it's ApplicationIR
            if is_app_ir and spec_or_ir.validation_model:
                return {
                    "rules": [r.dict() for r in spec_or_ir.validation_model.rules],
                    "test_cases": [tc.dict() for tc in spec_or_ir.validation_model.test_cases]
                }
            
            # 2. Fallback to self.app_ir if available (even if spec_or_ir is SpecRequirements)
            if hasattr(self, 'app_ir') and self.app_ir and hasattr(self.app_ir, 'validation_model') and self.app_ir.validation_model:
                return {
                    "rules": [r.dict() for r in self.app_ir.validation_model.rules],
                    "test_cases": [tc.dict() for tc in self.app_ir.validation_model.test_cases]
                }

            # 3. Fallback to legacy validation_ground_truth on SpecRequirements
            if not is_app_ir:
                return getattr(spec_or_ir, 'validation_ground_truth', {})
            
            return {}

        # Helper to adapt pattern with correct parameters
        def adapt_pattern_helper(code, current_entity=None, skip_jinja=False):
            """Helper to adapt pattern, auto-detecting spec_or_ir type."""
            if is_app_ir:
                return self._adapt_pattern(code, app_ir=spec_or_ir, current_entity=current_entity, skip_jinja=skip_jinja)
            else:
                return self._adapt_pattern(code, spec_requirements=spec_or_ir, current_entity=current_entity, skip_jinja=skip_jinja)

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
                        files["src/core/config.py"] = adapt_pattern_helper(p.code)
                        logger.info(f"✅ Mapped: src/core/config.py", extra={"purpose": p.signature.purpose[:60]})

        elif category == "database_async":
            # Bug #30 fix: Use hardcoded database module with lazy initialization
            # instead of PatternBank pattern to avoid "asyncio extension requires
            # an async driver" errors during pytest import
            logger.info("🔧 Generating database module with lazy initialization (Bug #30 fix)")
            files["src/core/database.py"] = self._generate_database_module()

        elif category == "observability":
            # Map each observability pattern to its file
            # Order matters: most specific patterns first to avoid false matches
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                # Bug #31 fix: Use hardcoded exception handlers with jsonable_encoder
                # instead of PatternBank pattern to avoid unnecessary auto-repair
                if "exception" in purpose_lower or "global exception" in purpose_lower:
                    logger.info("🔧 Generating exception handlers with jsonable_encoder (Bug #31 fix)")
                    files["src/core/exception_handlers.py"] = self._generate_exception_handlers()
                # Check request ID middleware specifically
                elif "request id" in purpose_lower:
                    files["src/core/middleware.py"] = adapt_pattern_helper(p.code)
                # Logging configuration (check after exception handler)
                elif "structlog" in purpose_lower and "configuration" in purpose_lower:
                    files["src/core/logging.py"] = adapt_pattern_helper(p.code)
                # Health checks
                elif "health check" in purpose_lower or "readiness" in purpose_lower:
                    files["src/api/routes/health.py"] = adapt_pattern_helper(p.code)
                # Prometheus metrics
                elif "metrics" in purpose_lower or "prometheus" in purpose_lower:
                    files["src/api/routes/metrics.py"] = adapt_pattern_helper(p.code)

            # Always use optimized routes (better than patterns)
            logger.info("🔧 Generating optimized metrics route")
            files["src/api/routes/metrics.py"] = self._generate_metrics_route()

            logger.info("🔧 Generating health routes with SQLAlchemy 2.0 text() fix")
            files["src/api/routes/health.py"] = self._generate_health_routes()

            logger.info("🔧 Generating middleware with relaxed CSP for Swagger UI")
            files["src/core/middleware.py"] = self._generate_middleware()

        # Data Layer - Pydantic Models
        elif category == "models_pydantic":
            # Use hardcoded production-ready schemas generator
            entities = get_entities()
            if entities:
                schemas_code = generate_schemas(
                    [{"name": e.name, "plural": e.name.lower() + "s", "fields": get_entity_fields(e)} for e in entities],
                    validation_ground_truth=get_validation_ground_truth()
                )
                if schemas_code:
                    files["src/models/schemas.py"] = schemas_code
                    logger.info(f"✅ Generated: src/models/schemas.py (hardcoded production generator)")
                else:
                    # Fallback to pattern matching
                    for p in category_patterns:
                        if "pydantic" in p.signature.purpose.lower() or "schema" in p.signature.purpose.lower():
                            files["src/models/schemas.py"] = adapt_pattern_helper(p.code)
            else:
                # Fallback to pattern matching if no entities
                for p in category_patterns:
                    if "pydantic" in p.signature.purpose.lower() or "schema" in p.signature.purpose.lower():
                        files["src/models/schemas.py"] = adapt_pattern_helper(p.code)

        # Data Layer - SQLAlchemy Models
        elif category == "models_sqlalchemy":
            # Use dynamic production-ready entities generator
            entities = get_entities()
            if entities:
                entities_code = generate_entities(
                    [{"name": e.name, "plural": e.name.lower() + "s", "fields": get_entity_fields(e), "relationships": getattr(e, 'relationships', [])} for e in entities],
                    validation_ground_truth=get_validation_ground_truth()  # NEW: Pass validation ground truth
                )
                if entities_code:
                    files["src/models/entities.py"] = entities_code
                    logger.info(f"✅ Generated: src/models/entities.py (hardcoded production generator)")
                else:
                    # Fallback to pattern matching
                    for p in category_patterns:
                        if "sqlalchemy" in p.signature.purpose.lower() or "orm" in p.signature.purpose.lower():
                            files["src/models/entities.py"] = adapt_pattern_helper(p.code)
            else:
                # Fallback to pattern matching if no entities
                for p in category_patterns:
                    if "sqlalchemy" in p.signature.purpose.lower() or "orm" in p.signature.purpose.lower():
                        files["src/models/entities.py"] = adapt_pattern_helper(p.code)

        # Repository Pattern
        elif category == "repository_pattern":
            # Generate repository for each entity
            repo_pattern = find_pattern_by_keyword(category_patterns, "repository", "crud")
            entities = get_entities()
            if repo_pattern and entities:
                for entity in entities:
                    # Pass current entity to _adapt_pattern so Jinja2 has access to {{ entity.name }}
                    adapted = adapt_pattern_helper(repo_pattern.code, current_entity=entity)
                    files[f"src/repositories/{get_entity_snake_name(entity)}_repository.py"] = adapted

        # Business Logic / Service Layer
        elif category == "business_logic":
            # Generate service for each entity using hardcoded production-ready generator
            entities = get_entities()
            if entities:
                # Bug #109: Convert entities to list of dicts for IR-based detection
                all_entities_list = []
                for e in entities:
                    entity_dict = {'name': e.name, 'fields': []}
                    for f in e.attributes:
                        if isinstance(f, dict):
                            entity_dict['fields'].append(f)
                        elif hasattr(f, 'name'):
                            field_dict = {'name': f.name}
                            if hasattr(f, 'data_type'):
                                field_dict['data_type'] = f.data_type
                            if hasattr(f, 'constraints'):
                                field_dict['constraints'] = f.constraints
                            entity_dict['fields'].append(field_dict)
                    all_entities_list.append(entity_dict)

                for entity in entities:
                    # Bug #109: Pass IR and all_entities for dynamic field detection
                    # Bug #165 Fix: Use spec_or_ir directly when it's ApplicationIR,
                    # not self.app_ir which is never set in this context
                    ir_to_pass = spec_or_ir if is_app_ir else getattr(self, 'app_ir', None)
                    service_code = generate_service_method(
                        entity.name,
                        entity.attributes,
                        ir=ir_to_pass,
                        all_entities=all_entities_list
                    )
                    if service_code:
                        # INJECT VALIDATIONS if app_ir is available
                        try:
                            if hasattr(self, 'app_ir') and self.app_ir and hasattr(self.app_ir, 'validation_model'):
                                from src.services.validation_code_generator import ValidationCodeGenerator

                                # Get rules for this entity
                                validation_rules = [
                                    rule for rule in self.app_ir.validation_model.rules
                                    if rule.entity == entity.name
                                ]

                                if validation_rules:
                                    # Create validation model with just this entity's rules
                                    from src.cognitive.ir.validation_model import ValidationModelIR
                                    entity_validation_model = ValidationModelIR(rules=validation_rules)

                                    # Generate validation code
                                    validator_gen = ValidationCodeGenerator()
                                    validation_code_dict = validator_gen.generate_validation_code(entity_validation_model)

                                    # Inject into service
                                    if entity.name in validation_code_dict:
                                        validation_code = validation_code_dict[entity.name]
                                        service_code = validator_gen.inject_validation_into_service(
                                            service_code, entity.name, validation_code
                                        )
                                        logger.info(f"✅ Injected validations into src/services/{get_entity_snake_name(entity)}_service.py")
                        except Exception as e:
                            logger.warning(f"⚠️  Could not inject validations: {e}")

                        files[f"src/services/{get_entity_snake_name(entity)}_service.py"] = service_code
                        logger.info(f"✅ Generated: src/services/{get_entity_snake_name(entity)}_service.py (hardcoded)")
                    else:
                        # Fallback to pattern matching
                        service_pattern = find_pattern_by_keyword(category_patterns, "service", "business logic")
                        if service_pattern:
                            adapted = adapt_pattern_helper(service_pattern.code, current_entity=entity)

                            # INJECT VALIDATIONS into template-generated service
                            try:
                                if hasattr(self, 'app_ir') and self.app_ir and hasattr(self.app_ir, 'validation_model'):
                                    from src.services.validation_code_generator import ValidationCodeGenerator

                                    # Get rules for this entity
                                    validation_rules = [
                                        rule for rule in self.app_ir.validation_model.rules
                                        if rule.entity == entity.name
                                    ]

                                    if validation_rules:
                                        # Create validation model with just this entity's rules
                                        from src.cognitive.ir.validation_model import ValidationModelIR
                                        entity_validation_model = ValidationModelIR(rules=validation_rules)

                                        # Generate validation code
                                        validator_gen = ValidationCodeGenerator()
                                        validation_code_dict = validator_gen.generate_validation_code(entity_validation_model)

                                        # Inject into service
                                        if entity.name in validation_code_dict:
                                            validation_code = validation_code_dict[entity.name]
                                            adapted = validator_gen.inject_validation_into_service(
                                                adapted, entity.name, validation_code
                                            )
                                            logger.info(f"✅ Injected validations into template-generated service for {entity.name}")
                            except Exception as e:
                                logger.warning(f"⚠️  Could not inject validations into template service: {e}")

                            files[f"src/services/{get_entity_snake_name(entity)}_service.py"] = adapted
            else:
                # Fallback to pattern matching if no entities
                service_pattern = find_pattern_by_keyword(category_patterns, "service", "business logic")
                if service_pattern and entities:
                    for entity in entities:
                        adapted = adapt_pattern_helper(service_pattern.code, current_entity=entity)

                        # INJECT VALIDATIONS into template-generated service
                        try:
                            if hasattr(self, 'app_ir') and self.app_ir and hasattr(self.app_ir, 'validation_model'):
                                from src.services.validation_code_generator import ValidationCodeGenerator

                                # Get rules for this entity
                                validation_rules = [
                                    rule for rule in self.app_ir.validation_model.rules
                                    if rule.entity == entity.name
                                ]

                                if validation_rules:
                                    # Create validation model with just this entity's rules
                                    from src.cognitive.ir.validation_model import ValidationModelIR
                                    entity_validation_model = ValidationModelIR(rules=validation_rules)

                                    # Generate validation code
                                    validator_gen = ValidationCodeGenerator()
                                    validation_code_dict = validator_gen.generate_validation_code(entity_validation_model)

                                    # Inject into service
                                    if entity.name in validation_code_dict:
                                        validation_code = validation_code_dict[entity.name]
                                        adapted = validator_gen.inject_validation_into_service(
                                            adapted, entity.name, validation_code
                                        )
                                        logger.info(f"✅ Injected validations into template-generated service for {entity.name}")
                        except Exception as e:
                            logger.warning(f"⚠️  Could not inject validations into template service: {e}")

                        files[f"src/services/{get_entity_snake_name(entity)}_service.py"] = adapted

        # API Routes - ALWAYS use LLM with pattern as guide (Milestone 5+ improvement)
        elif category == "api_routes":
            # Get pattern as EXAMPLE/GUIDE (not final code)
            route_pattern = find_pattern_by_keyword(category_patterns, "fastapi", "crud", "endpoint")

            entities = get_entities()
            endpoints = get_endpoints()
            if entities:
                logger.info(
                    "🤖 Generating spec-adapted API routes with LLM (pattern as guide)",
                    extra={"entity_count": len(entities), "has_pattern": route_pattern is not None}
                )

                # Generate route for each entity using LLM with pattern as guide
                for entity in entities:
                    # Extract endpoints specific to this entity from spec
                    # Use endpoint.entity field (set by LLM parser) for accurate grouping
                    # Fallback to path-based matching if entity field is missing
                    entity_snake = get_entity_snake_name(entity)
                    entity_plural = f"{entity_snake}s"
                    
                    entity_endpoints = []
                    for e in endpoints:
                        # Try entity field first (LLM-parsed)
                        if hasattr(e, 'entity') and e.entity:
                            if e.entity.lower() == entity.name.lower():
                                entity_endpoints.append(e)
                        else:
                            # Fallback to path-based matching
                            if (e.path.lstrip('/').startswith(entity_plural + '/') or
                                e.path.lstrip('/').startswith(entity_plural) or
                                e.path == f"/{entity_plural}"):
                                entity_endpoints.append(e)

                    # Generate route using LLM with pattern as style guide
                    # For api_routes, pass spec_or_ir based on type
                    spec_arg = spec_or_ir if not is_app_ir else None
                    
                    entity_snake = get_entity_snake_name(entity)
                    route_code = await self._generate_route_with_llm(
                        entity=entity,
                        endpoints=entity_endpoints,
                        pattern_code=route_pattern.code if route_pattern else None,
                        spec_requirements=spec_arg
                    )

                    files[f"src/api/routes/{entity_snake}.py"] = route_code

        # Security patterns
        elif category == "security_hardening":
            for p in category_patterns:
                if "security" in p.signature.purpose.lower() or "sanitization" in p.signature.purpose.lower():
                    files["src/core/security.py"] = adapt_pattern_helper(p.code)

        # Testing patterns
        # FIXED (Bug #11): Remove skip_jinja=True - test templates need Jinja2 rendering
        # to properly generate entity-specific test code from ApplicationIR context
        elif category == "test_infrastructure":
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "pytest fixtures" in purpose_lower or "conftest" in purpose_lower:
                    files["tests/conftest.py"] = adapt_pattern_helper(p.code)
                elif "test data factories" in purpose_lower or "factories" in purpose_lower:
                    # Bug #52 Fix: Skip PatternBank template - has invalid Jinja2 syntax
                    # (uuid4().hex[:8] is Python, not Jinja2). Use AST generator instead.
                    if is_app_ir:
                        # Get normalized entities from ApplicationIRNormalizer
                        normalizer = ApplicationIRNormalizer(spec_or_ir)
                        normalized_entities = normalizer.get_entities()
                        if normalized_entities:
                            files["tests/factories.py"] = self._generate_test_factories(normalized_entities)
                            logger.info("✅ Generated tests/factories.py from AST (Bug #52 fix)")
                        else:
                            logger.warning("⚠️ No entities found, skipping factories.py generation")
                    else:
                        # Fallback to pattern for non-IR mode (legacy)
                        files["tests/factories.py"] = adapt_pattern_helper(p.code)
                # Bug #50 fix: Skip test_models.py from PatternBank - imports incorrect schema names
                # (imports 'Product' but schemas.py has 'ProductCreate', 'ProductResponse', etc.)
                # IR-generated tests in tests/generated/ are used instead
                elif "unit tests for pydantic" in purpose_lower or "test_models" in purpose_lower:
                    logger.info("Skipping test_models.py from PatternBank (Bug #50: imports incorrect schema names)")
                    pass  # Skip - imports 'Product' but schemas.py has 'ProductCreate', 'ProductResponse'
                # Bug #27 fix: Skip test_repositories and test_api from PatternBank
                # These templates have invalid Jinja syntax ({% set found.value %} without namespace)
                # IR-generated tests in tests/generated/ are used instead
                elif "unit tests for repository" in purpose_lower or "test_repositories" in purpose_lower:
                    logger.info("Skipping test_repositories.py from PatternBank (using IR-generated tests)")
                    pass  # Skip - IR-generated tests are better
                # Bug #50 fix: Skip test_services.py from PatternBank - imports non-existent factories
                # (imports 'tests.factories' but factories.py doesn't exist or has wrong exports)
                elif "unit tests for service" in purpose_lower or "test_services" in purpose_lower:
                    logger.info("Skipping test_services.py from PatternBank (Bug #50: imports non-existent factories)")
                    pass  # Skip - imports 'tests.factories' which doesn't exist
                elif "integration tests" in purpose_lower or "test_api" in purpose_lower:
                    logger.info("Skipping test_api.py from PatternBank (using IR-generated tests)")
                    pass  # Skip - IR-generated tests are better
                elif "tests for logging" in purpose_lower or "observability" in purpose_lower:
                    files["tests/test_observability.py"] = adapt_pattern_helper(p.code)

        # Docker infrastructure
        elif category == "docker_infrastructure":
            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "multi-stage docker" in purpose_lower or "dockerfile" in purpose_lower:
                    files["docker/Dockerfile"] = adapt_pattern_helper(p.code)
                elif "full stack docker-compose" in purpose_lower and "test" not in purpose_lower:
                    files["docker/docker-compose.yml"] = adapt_pattern_helper(p.code)
                elif "test environment" in purpose_lower or "docker-compose.test" in purpose_lower:
                    files["docker/docker-compose.test.yml"] = adapt_pattern_helper(p.code)
                elif "prometheus scrape" in purpose_lower or "prometheus.yml" in purpose_lower:
                    files["docker/prometheus.yml"] = adapt_pattern_helper(p.code)
                elif "docker build exclusions" in purpose_lower or ".dockerignore" in purpose_lower:
                    files["docker/.dockerignore"] = adapt_pattern_helper(p.code)
                elif "grafana dashboard" in purpose_lower and "json" in purpose_lower:
                    files["docker/grafana/dashboards/app-metrics.json"] = adapt_pattern_helper(p.code)
                elif "dashboard provisioning" in purpose_lower or "dashboard-provider" in purpose_lower:
                    files["docker/grafana/dashboards/dashboard-provider.yml"] = adapt_pattern_helper(p.code)
                elif "datasource" in purpose_lower or "prometheus datasource" in purpose_lower:
                    files["docker/grafana/datasources/prometheus.yml"] = adapt_pattern_helper(p.code)
                elif "docker setup documentation" in purpose_lower or "readme" in purpose_lower.lower():
                    files["docker/README.md"] = adapt_pattern_helper(p.code)
                elif "troubleshooting" in purpose_lower:
                    files["docker/TROUBLESHOOTING.md"] = adapt_pattern_helper(p.code)
                elif "validation checklist" in purpose_lower:
                    files["docker/VALIDATION_CHECKLIST.md"] = adapt_pattern_helper(p.code)
                elif "validation script" in purpose_lower or ".sh" in purpose_lower:
                    files["docker/validate-docker-setup.sh"] = adapt_pattern_helper(p.code)

            # Always use optimized Docker files (better than patterns)
            logger.info("🔧 Generating optimized pip-based Dockerfile")
            files["docker/Dockerfile"] = self._generate_dockerfile(None)

            logger.info("🔧 Generating optimized docker-compose.yml")
            files["docker/docker-compose.yml"] = self._generate_docker_compose(None)

            # Ensure Prometheus and Grafana configurations exist
            logger.info("🔧 Generating Prometheus scrape configuration")
            files["docker/prometheus.yml"] = self._generate_prometheus_config()

            logger.info("🔧 Generating Grafana provisioning files")
            files["docker/grafana/dashboards/dashboard-provider.yml"] = self._generate_grafana_dashboard_provider()
            files["docker/grafana/datasources/prometheus.yml"] = self._generate_grafana_prometheus_datasource()

            # Bug #85: Generate seed script for test data
            logger.info("🔧 Generating seed_db.py for test data initialization")
            files["scripts/seed_db.py"] = self._generate_seed_db_script(spec_or_ir)

        # Project config & Alembic migrations
        elif category == "project_config":
            found_files = set()

            for p in category_patterns:
                purpose_lower = p.signature.purpose.lower()
                if "pyproject" in purpose_lower or "toml" in purpose_lower:
                    files["pyproject.toml"] = adapt_pattern_helper(p.code)
                    found_files.add("pyproject.toml")
                elif "env" in purpose_lower and "example" in purpose_lower:
                    files[".env.example"] = adapt_pattern_helper(p.code)
                    found_files.add(".env.example")
                elif "gitignore" in purpose_lower:
                    files[".gitignore"] = adapt_pattern_helper(p.code)
                    found_files.add(".gitignore")
                elif "makefile" in purpose_lower:
                    files["Makefile"] = adapt_pattern_helper(p.code)
                    found_files.add("Makefile")
                elif "pre-commit" in purpose_lower or "pre_commit" in purpose_lower:
                    files[".pre-commit-config.yaml"] = adapt_pattern_helper(p.code)
                    found_files.add(".pre-commit-config.yaml")
                elif "alembic.ini" in purpose_lower or ("alembic" in purpose_lower and "config" in purpose_lower):
                    files["alembic.ini"] = adapt_pattern_helper(p.code)
                    found_files.add("alembic.ini")
                elif "alembic/env" in purpose_lower or ("alembic" in purpose_lower and "env" in purpose_lower):
                    files["alembic/env.py"] = adapt_pattern_helper(p.code)
                    found_files.add("alembic/env.py")
                elif "readme" in purpose_lower:
                    files["README.md"] = adapt_pattern_helper(p.code)
                    found_files.add("README.md")

            # Fallback for missing critical files (always generate if missing)
            if "alembic.ini" not in found_files:
                logger.info("🔧 Generating alembic.ini")
                spec_arg = spec_or_ir if not is_app_ir else None
                files["alembic.ini"] = self._generate_alembic_ini(spec_arg)

            if "alembic/env.py" not in found_files:
                logger.info("🔧 Generating alembic/env.py")
                spec_arg = spec_or_ir if not is_app_ir else None
                files["alembic/env.py"] = self._generate_alembic_env(spec_arg)

            if "alembic/script.py.mako" not in found_files:
                logger.info("🔧 Generating alembic/script.py.mako")
                alembic_script = self._generate_alembic_script_template()
                files["alembic/script.py.mako"] = adapt_pattern_helper(alembic_script, skip_jinja=True)

            # Generate initial migration
            entities = get_entities()
            if entities:
                logger.info("🔧 Generating initial migration")

                def _entity_to_dict(entity) -> dict:
                    """Convert parsed entity to a plain dict for the migration generator."""
                    fields = []
                    raw_fields = getattr(entity, "attributes", None) or getattr(entity, "fields", []) or []
                    for f in raw_fields:
                        if hasattr(f, "data_type"):
                            field_type = f.data_type.value if hasattr(f.data_type, 'value') else str(f.data_type)
                            fields.append({
                                "name": f.name,
                                "type": field_type,
                                "required": not getattr(f, "is_nullable", False),
                                "default": getattr(f, "default_value", None),
                                "constraints": getattr(f, "constraints", {}),
                            })
                        else:
                            fields.append({
                                "name": getattr(f, "name", None),
                                "type": getattr(f, "type", None),
                                "required": getattr(f, "required", None),
                                "default": getattr(f, "default", None),
                                "constraints": getattr(f, "constraints", None),
                            })
                    return {
                        "name": getattr(entity, "name", "Unknown"),
                        "plural": (getattr(entity, "name", "Unknown") + "s").lower(),
                        "fields": fields,
                    }

                migration_code = generate_initial_migration([_entity_to_dict(e) for e in entities])
                if migration_code:
                    files["alembic/versions/001_initial.py"] = migration_code

            if "pyproject.toml" not in found_files:
                logger.info("🔧 Generating pyproject.toml")
                spec_arg = spec_or_ir if not is_app_ir else None
                files["pyproject.toml"] = self._generate_pyproject_toml(spec_arg)

            if ".env.example" not in found_files:
                logger.info("🔧 Generating .env.example")
                files[".env.example"] = self._generate_env_example()

            if ".gitignore" not in found_files:
                logger.info("🔧 Generating .gitignore")
                files[".gitignore"] = self._generate_gitignore()

            if "Makefile" not in found_files:
                logger.info("🔧 Generating Makefile")
                files["Makefile"] = self._generate_makefile()

        # Log summary for this category
        logger.info(
            f"📦 Category {category} composed",
            extra={
                "files_generated": len(files),
                "file_list": list(files.keys())
            }
        )

        return files

    def _adapt_pattern(self, pattern_code: str, spec_requirements=None, current_entity=None, skip_jinja: bool = False, app_ir=None) -> str:
        """
        Adapt pattern code to spec requirements or ApplicationIR (Task Group 8).

        Supports two placeholder styles:
        1. Jinja2 templates: {{ app_name }}, {% if entities %}, {% for entity in entities %}
        2. Simple placeholders: {APP_NAME}, {DATABASE_URL}, {ENTITY_IMPORTS}, {ENTITY_ROUTERS}

        **Phase 1 Refactoring**: Now accepts ApplicationIR as primary input with
        backward compatibility for spec_requirements.

        Args:
            pattern_code: Pattern code with placeholders (Jinja2 or simple style)
            spec_requirements: SpecRequirements object (deprecated, backward compat)
            current_entity: Optional entity object for entity-specific patterns
            skip_jinja: Skip Jinja2 rendering
            app_ir: ApplicationIR object (preferred, primary input)

        Returns:
            Adapted code with placeholders replaced
        """
        # Handle both ApplicationIR and SpecRequirements
        if app_ir is not None:
            # PRIMARY PATH: Extract from ApplicationIR using Normalizer
            logger.info(
                "Using ApplicationIR with normalizer for template rendering",
                extra={"app_id": str(app_ir.app_id)}
            )
            normalizer = ApplicationIRNormalizer(app_ir)
            context = normalizer.get_context()

            # Add backward compatibility fields
            app_name = context["app_name"]
            app_name_snake = app_name.replace("-", "_").replace(" ", "_").lower()
            context["app_name_snake"] = app_name_snake
            database_url = "postgresql+asyncpg://user:password@localhost:5432/app"
            context["database_url"] = database_url

            entities = context.get("entities", [])

            # Build entity imports and routers for backward compatibility
            entity_imports = []
            entity_routers = []
            for entity in entities:
                entity_snake = entity.get("snake_name", entity.get("name", "").lower().replace(" ", "_"))
                entity_imports.append(f"from src.api.routes import {entity_snake}")
                entity_routers.append(f"app.include_router({entity_snake}.router)")

            imports_str = "\n".join(entity_imports) if entity_imports else ""
            routers_str = "\n".join(entity_routers) if entity_routers else ""

        elif spec_requirements is not None:
            # BACKWARD COMPATIBILITY PATH: Extract from SpecRequirements
            logger.warning(
                "Using SpecRequirements in template rendering (deprecated). "
                "Please migrate to ApplicationIR.",
                extra={"migration_phase": "phase_2"}
            )
            app_name = spec_requirements.metadata.get("spec_name", "API")
            app_name_snake = app_name.replace("-", "_").replace(" ", "_").lower()
            database_url = spec_requirements.metadata.get(
                "database_url", "postgresql+asyncpg://user:password@localhost:5432/app"
            )
            entities_list = spec_requirements.entities

            # Build entities list with snake_case names for Jinja2
            entities = []
            entity_imports = []
            entity_routers = []

            for entity in entities_list:
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
        else:
            raise ValueError("Either app_ir or spec_requirements must be provided")

        # Add current entity to context if provided (for entity-specific patterns)
        if current_entity:
            entity_snake = current_entity.name.lower().replace(" ", "_")
            context["entity"] = {
                "name": current_entity.name,
                "snake_name": entity_snake,
            }
            # Add common variables for Jinja2 templates ({{id}}, {{entity_name}}, etc.)
            context["id"] = "{id}"  # For path parameters like @router.get("/{{id}}") → /@router.get("/{id}")
            context["entity_name"] = entity_snake  # For function names like get_{{entity_name}}
            context["ENTITY_NAME"] = current_entity.name  # For class names like {{ENTITY_NAME}}Response

        rendered = pattern_code

        # Render Jinja2 template (handles {{ }} and {% %} syntax) unless explicitly skipped
        if not skip_jinja:
            try:
                # Create Environment with custom filters for template rendering
                import re as regex_module
                from jinja2 import Environment

                def snake_case_filter(value):
                    """Convert CamelCase to snake_case."""
                    if not value:
                        return value
                    return regex_module.sub(r'(?<!^)(?=[A-Z])', '_', str(value)).lower()

                env = Environment()
                env.filters['snake_case'] = snake_case_filter

                template = env.from_string(pattern_code)
                rendered = template.render(context)
            except Exception as e:
                # If Jinja2 rendering fails (e.g., syntax error in template),
                # fall back to simple string replacement without breaking the pipeline
                logger.warning(
                    f"Jinja2 template rendering failed: {e}. Falling back to simple replacement.",
                    extra={"error": str(e)}
                )

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

    async def _generate_route_with_llm(
        self,
        entity,
        endpoints: list,
        pattern_code: str | None,
        spec_requirements
    ) -> str:
        """
        Generate API route code directly from spec endpoints (no LLM).

        Builds routes with EXACT paths from spec for 100% compliance.

        Args:
            entity: Entity object with name, fields, etc.
            endpoints: List of Endpoint objects specific to this entity
            pattern_code: Pattern code to use as example/guide (IGNORED for now)
            spec_requirements: Full spec requirements object

        Returns:
            Generated route code as string
        """
        # Convert CamelCase to snake_case correctly (CartItem → cart_item)
        import re
        entity_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity.name).lower()
        entity_plural = f"{entity_snake}s"  # Always define this for use in function bodies
        
        # Determine router prefix from actual endpoint paths
        # Extract common prefix from all endpoints for this entity
        router_prefix = None
        if endpoints:
            # Get first path segment from first endpoint as router prefix
            first_path = endpoints[0].path
            # Extract first segment: /cart/... → /cart, /products/... → /products
            match = re.match(r'^(/[^/]+)', first_path)
            if match:
                router_prefix = match.group(1)
        
        # Fallback to entity_plural if no endpoints or detection failed
        if not router_prefix:
            router_prefix = f"/{entity_plural}"
        
        # Determine tag name from router prefix (remove leading slash)
        tag_name = router_prefix.lstrip('/')

        # Bug #134 Fix: Detect if any endpoints use nested resources (e.g., /items)
        # If so, we need to import the child entity schemas too
        has_items_endpoints = any('/items' in ep.path for ep in endpoints)
        item_imports = f', {entity.name}ItemCreate, {entity.name}ItemUpdate' if has_items_endpoints else ''

        # Start building the route file
        code = f'''"""
FastAPI Routes for {entity.name}

Spec-compliant endpoints with:
- Repository pattern integration
- Service layer architecture
- Proper error handling
- Pydantic validation
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.schemas import {entity.name}Create, {entity.name}Update, {entity.name}Response{item_imports}
from src.services.{entity_snake}_service import {entity.name}Service

router = APIRouter(
    prefix="{router_prefix}",
    tags=["{tag_name}"],
)


'''

        # Bug #168: Query AntiPatternAdvisor for entity-specific advice
        anti_pattern_advice = None
        if self.anti_pattern_advisor:
            try:
                anti_pattern_advice = self.anti_pattern_advisor.get_advice_for_entity(entity.name)
                if anti_pattern_advice.has_advice():
                    logger.info(
                        f"🛡️ AntiPattern advice for {entity.name}",
                        extra={
                            "entity": entity.name,
                            "avoid_count": len(anti_pattern_advice.avoid_patterns),
                            "use_count": len(anti_pattern_advice.use_patterns),
                            "high_risk": anti_pattern_advice.high_risk_count,
                        }
                    )
            except Exception as e:
                logger.debug(f"Could not get anti-pattern advice: {e}")

        # Log endpoints being generated for debugging
        logger.info(
            f"Generating routes for {entity.name}",
            extra={
                "entity": entity.name,
                "endpoint_count": len(endpoints),
                "endpoints": [f"{ep.method} {ep.path}" for ep in endpoints],
                "router_prefix": router_prefix
            }
        )

        # Generate each endpoint from spec
        import re
        for ep in endpoints:
            # Convert absolute path to relative path
            relative_path = ep.path
            if relative_path.startswith(router_prefix):
                relative_path = relative_path[len(router_prefix):]
            if not relative_path:
                relative_path = ""  # Bug #75 Fix: Empty path instead of "/" to avoid HTTP 307 redirects

            # Determine response model and status code
            method = ep.method.lower()
            if method == 'post':
                status_code = "status.HTTP_201_CREATED"
                response_model = f"{entity.name}Response"
            elif method == 'delete':
                status_code = "status.HTTP_204_NO_CONTENT"
                response_model = None
            elif method == 'put':
                status_code = None
                response_model = f"{entity.name}Response"
            else:  # GET
                # Check if it's a list endpoint (root path)
                if relative_path == "" or relative_path == "/":
                    response_model = f"List[{entity.name}Response]"
                else:
                    response_model = f"{entity.name}Response"
                status_code = None

            # Generate function name from description
            func_name = ep.description.lower().replace(' ', '_') if ep.description else f"{method}_{entity_snake}"
            func_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in func_name)

            # Build decorator
            decorator = f'@router.{method}("{relative_path}"'
            if response_model:
                decorator += f', response_model={response_model}'
            if status_code:
                decorator += f', status_code={status_code}'
            decorator += ')'

            # Extract path parameters
            path_params = re.findall(r'\{(\w+)\}', relative_path)

            # Build function signature
            params = []
            for param in path_params:
                # Bug #76 Fix: Use UUID type for ID parameters (e.g., product_id, id, customer_id)
                if param.endswith('_id') or param == 'id':
                    params.append(f'{param}: UUID')
                else:
                    params.append(f'{param}: str')

            # Bug #104 Fix: Detect action endpoints BEFORE adding body parameter
            # Action endpoints (deactivate, clear, checkout, etc.) don't require request body
            custom_ops_no_body = ['checkout', 'pay', 'cancel', 'deactivate', 'activate', 'clear']
            is_action_endpoint = any(f'/{op}' in relative_path for op in custom_ops_no_body)

            # Bug #134 Fix: Detect nested resource endpoints (e.g., /carts/{cart_id}/items)
            # For these, use the child entity schema (CartItemCreate) not parent (CartCreate)
            is_items_endpoint = '/items' in relative_path and not relative_path.endswith('/items/{item_id}')
            schema_entity_name = f'{entity.name}Item' if is_items_endpoint else entity.name
            schema_entity_snake = f'{entity_snake}_item' if is_items_endpoint else entity_snake

            # Add request body for POST/PUT/PATCH - but NOT for action endpoints
            if method == 'post' and not is_action_endpoint:
                params.append(f'{schema_entity_snake}_data: {schema_entity_name}Create')
            elif method == 'put':
                params.append(f'{schema_entity_snake}_data: {schema_entity_name}Update')
            elif method == 'patch' and not is_action_endpoint:
                # Bug #104b Fix: PATCH needs body for updates (but not for activate/deactivate actions)
                params.append(f'{schema_entity_snake}_data: {schema_entity_name}Update')

            params.append('db: AsyncSession = Depends(get_db)')
            params_str = ',\n    '.join(params)

            # Build function body
            body = f'''    """
    {ep.description or f'{method.upper()} {relative_path}'}
    """
    service = {entity.name}Service(db)
'''

            if method == 'get':
                if response_model and 'List[' in response_model:
                    # List endpoint - use service.list(page, size) which matches Service template
                    body += f'''    result = await service.list(page=1, size=100)
    return result.items
'''
                else:
                    # Single item endpoint
                    id_param = path_params[0] if path_params else 'id'
                    body += f'''    {entity_snake} = await service.get_by_id({id_param})

    if not {entity_snake}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    return {entity_snake}
'''
            elif method == 'post':
                # Bug #80b Fix: Detect custom operations for POST endpoints
                # POST can be used for: create (default), checkout, pay, cancel, deactivate, add_item, clear
                operation = None
                custom_ops_no_body = ['checkout', 'pay', 'cancel', 'deactivate', 'activate', 'clear']
                custom_ops_with_body = ['items']  # e.g., POST /carts/{id}/items

                # Bug #82 Fix: Map route path operations to service method names
                # /clear -> clear_items(), /checkout -> checkout(), etc.
                operation_method_map = {
                    'clear': 'clear_items',
                }

                for op in custom_ops_no_body:
                    if f'/{op}' in relative_path:
                        # Use mapped method name if exists, otherwise use operation name
                        operation = operation_method_map.get(op, op)
                        break

                if not operation:
                    for op in custom_ops_with_body:
                        if f'/{op}' in relative_path:
                            operation = f'add_{op.rstrip("s")}'  # items -> add_item
                            break

                if operation:
                    id_param = path_params[0] if path_params else 'id'

                    if operation == 'add_item':
                        # add_item needs request body
                        # Bug #166 Fix: Check existence first to return proper 404
                        body += f'''    # Bug #166 Fix: Check existence first to return proper 404
    existing = await service.get({id_param})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    {entity_snake} = await service.add_item({id_param}, {schema_entity_snake}_data.model_dump() if hasattr({schema_entity_snake}_data, 'model_dump') else {schema_entity_snake}_data)
    return {entity_snake}
'''
                    else:
                        # Custom operation without body (checkout, pay, cancel, deactivate, activate)
                        # Bug #166 Fix: Check existence first to return proper 404
                        body += f'''    # Bug #166 Fix: Check existence first to return proper 404
    existing = await service.get({id_param})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    {entity_snake} = await service.{operation}({id_param})
    return {entity_snake}
'''
                else:
                    # Default: standard create operation
                    # Bug #139 Fix: Use schema_entity_snake for consistent variable names
                    body += f'''    {entity_snake} = await service.create({schema_entity_snake}_data)
    return {entity_snake}
'''
            elif method == 'put':
                id_param = path_params[0] if path_params else 'id'
                # Bug #166 Fix: Check existence BEFORE update to return 404 instead of 422
                # This ensures we return 404 (not found) rather than letting Pydantic
                # validation errors (422) mask the fact that the resource doesn't exist
                body += f'''    # Bug #166 Fix: Check existence first to return proper 404
    existing = await service.get({id_param})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    {entity_snake} = await service.update({id_param}, {schema_entity_snake}_data)
    return {entity_snake}
'''
            elif method == 'delete':
                id_param = path_params[0] if path_params else 'id'
                body += f'''    success = await service.delete({id_param})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    return None
'''
            elif method == 'patch':
                # Bug #73 Fix: Handle PATCH for custom operations like activate/deactivate
                id_param = path_params[0] if path_params else 'id'

                # Detect operation from path suffix (e.g., /activate, /deactivate)
                operation = None
                if '/activate' in relative_path:
                    operation = 'activate'
                elif '/deactivate' in relative_path:
                    operation = 'deactivate'

                if operation:
                    # Custom operation: call service.{operation}(id)
                    # Bug #166 Fix: Check existence first to return proper 404
                    body += f'''    # Bug #166 Fix: Check existence first to return proper 404
    existing = await service.get({id_param})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    {entity_snake} = await service.{operation}({id_param})
    return {entity_snake}
'''
                else:
                    # Generic PATCH: call service.update(id, data) - partial update
                    # Bug #166 Fix: Check existence first to return proper 404
                    body += f'''    # Bug #166 Fix: Check existence first to return proper 404
    existing = await service.get({id_param})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.name} with id {{{id_param}}} not found"
        )

    {entity_snake} = await service.update({id_param}, {schema_entity_snake}_data)
    return {entity_snake}
'''

            # Assemble the endpoint function
            code += f'''{decorator}
async def {func_name}(
    {params_str}
):
{body}

'''

        return code

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

    def _validate_ir_for_generation(self, app_ir) -> List[str]:
        """Validate ApplicationIR has minimum required data for code generation.

        PRE-GENERATION VALIDATION: Ensures IR integrity before attempting generation.
        This separates "IR incomplete" errors from "generation bug" errors.

        Args:
            app_ir: ApplicationIR object to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check if IR exists
        if app_ir is None:
            errors.append("ApplicationIR is None")
            return errors

        # Check DomainModelIR (required for entities)
        if not app_ir.domain_model:
            errors.append("DomainModelIR is missing")
        elif not app_ir.domain_model.entities:
            errors.append("DomainModelIR has no entities")
        else:
            # Validate each entity has attributes
            for entity in app_ir.domain_model.entities:
                if not hasattr(entity, 'attributes') or not entity.attributes:
                    errors.append(f"Entity '{entity.name}' has no attributes")

        # Check APIModelIR (required for endpoints)
        if not app_ir.api_model:
            errors.append("APIModelIR is missing")
        elif not app_ir.api_model.endpoints:
            errors.append("APIModelIR has no endpoints")

        # Check app metadata
        if not hasattr(app_ir, 'name') or not app_ir.name:
            errors.append("ApplicationIR has no name")

        if not hasattr(app_ir, 'app_id') or not app_ir.app_id:
            errors.append("ApplicationIR has no app_id")

        return errors

    def _validate_generated_structure(self, files_dict: Dict[str, str]) -> List[str]:
        """Validate generated files have minimum required structure.

        POST-GENERATION VALIDATION: Ensures output integrity before returning.
        This prevents partial/broken output from reaching downstream phases.

        Args:
            files_dict: Dictionary of generated file paths to content

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Required files for a valid FastAPI app
        required_files = [
            "src/main.py",
            "src/models/entities.py",
            "src/models/schemas.py",
        ]

        for required_file in required_files:
            if required_file not in files_dict:
                errors.append(f"Missing required file: {required_file}")
            elif not files_dict[required_file] or len(files_dict[required_file].strip()) < 50:
                errors.append(f"File too small or empty: {required_file}")

        # Check for at least one route file
        route_files = [f for f in files_dict.keys() if f.startswith("src/api/routes/") and f.endswith(".py")]
        if len(route_files) < 2:  # health.py + at least one entity route
            errors.append(f"Insufficient route files: found {len(route_files)}, expected at least 2")

        # Validate main.py has FastAPI app
        if "src/main.py" in files_dict:
            main_content = files_dict["src/main.py"]
            if "FastAPI" not in main_content:
                errors.append("src/main.py does not contain FastAPI app")
            if "FALLBACK MODE" in main_content:
                errors.append("src/main.py is in FALLBACK MODE (generation failed)")

        return errors

    async def _apply_cognitive_pass(
        self,
        files_dict: Dict[str, str],
        app_ir
    ) -> Dict[str, str]:
        """Apply IR-Centric Cognitive Pass to enhance generated code.

        This method applies learned patterns and IR contracts to improve
        the generated code quality. It uses the CognitiveCodeGenerationService
        which implements:
        - IR-based semantic caching
        - Function-level enhancement
        - IR Guard prompts for constraint enforcement
        - Rollback on IR violations
        - Graceful degradation on failures

        Part of Bug #143-160 IR-Centric Cognitive Code Generation.

        Args:
            files_dict: Dictionary of file paths to content
            app_ir: ApplicationIR with flows and contracts

        Returns:
            Enhanced files_dict (original if enhancement fails/disabled)
        """
        try:
            # Initialize cognitive service with current IR
            from src.services.cognitive_code_generation_service import create_cognitive_service
            from src.learning.negative_pattern_store import get_negative_pattern_store

            pattern_store = get_negative_pattern_store()
            self.cognitive_service = create_cognitive_service(
                ir=app_ir,
                pattern_store=pattern_store,
                llm_client=self.llm_client,
            )

            logger.info(
                "Starting Cognitive Pass",
                extra={
                    "files_count": len(files_dict),
                    "enabled": self.cognitive_service.is_enabled(),
                    "phase": "cognitive_enhancement"
                }
            )

            # Bug #164 Fix: Expand cognitive pass to ALL code files (not just LLM stratum)
            # Previously only applied to services/workflows/routes (~6% of files).
            # Now includes models/, repositories/, validators/ for full learning coverage.
            # (Skip __init__.py, config files, static infrastructure files)
            enhancement_targets = [
                {"path": path, "content": content}
                for path, content in files_dict.items()
                if path.endswith(".py")
                and not path.endswith("__init__.py")
                and not path.endswith("conftest.py")
                and (
                    "services/" in path
                    or "workflows/" in path
                    or "routes/" in path
                    or "models/" in path        # Bug #164: AST stratum
                    or "repositories/" in path  # Bug #164: AST stratum
                    or "validators/" in path    # Bug #164: AST stratum
                    or "state_machines/" in path  # Bug #164: AST stratum
                )
            ]

            if not enhancement_targets:
                logger.info("No files eligible for cognitive enhancement")
                return files_dict

            # Process files through cognitive pass
            results = await self.cognitive_service.process_files(enhancement_targets)

            # Update files_dict with enhanced content
            enhanced_count = 0
            for result in results:
                if result.success and result.enhanced_content != result.original_content:
                    files_dict[result.file_path] = result.enhanced_content
                    enhanced_count += 1

            # Get metrics
            metrics = self.cognitive_service.get_metrics_dict()

            logger.info(
                "Cognitive Pass completed",
                extra={
                    "files_enhanced": enhanced_count,
                    "total_processed": len(results),
                    "functions_enhanced": metrics.get("functions_enhanced", 0),
                    "prevention_rate": metrics.get("prevention_rate", 0),
                    "cache_hits": metrics.get("cache_hits", 0),
                    "phase": "cognitive_enhancement"
                }
            )

            return files_dict

        except Exception as e:
            # Graceful degradation: log and return original
            logger.warning(
                f"Cognitive Pass failed, using original code: {e}",
                extra={
                    "error": str(e),
                    "phase": "cognitive_enhancement"
                }
            )
            return files_dict

    def _generate_fallback_structure(self, app_ir, error_message: str) -> str:
        """Generate minimal valid app structure when generation fails.

        CRITICAL: This method ensures that even when generation fails, we return
        a syntactically valid structure (not error messages as code).

        The fallback structure:
        - Contains valid Python syntax
        - Has the expected directory structure
        - Includes clear error markers in comments
        - Can be parsed by downstream pipeline phases

        Args:
            app_ir: ApplicationIR object (may have incomplete data)
            error_message: The error that caused generation to fail

        Returns:
            Multi-file string with minimal valid structure
        """
        logger.warning(
            "Generating fallback structure due to generation failure",
            extra={"error": error_message[:200], "app_name": getattr(app_ir, 'name', 'Unknown')}
        )

        # Extract entity names safely from IR
        entity_names = []
        try:
            if app_ir and hasattr(app_ir, 'domain_model') and app_ir.domain_model:
                entity_names = [e.name for e in app_ir.domain_model.entities]
        except Exception:
            entity_names = ['Entity']  # Fallback name

        # Generate minimal valid files
        files = {}

        # 1. Main entry point (always valid)
        files["src/main.py"] = f'''"""
API Entry Point - FALLBACK MODE

WARNING: This file was generated in fallback mode due to a generation error.
Original error: {error_message[:500]}

Please investigate and regenerate.
"""
from fastapi import FastAPI

app = FastAPI(
    title="API (Fallback Mode)",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {{"status": "fallback_mode", "error": "Generation failed, check logs"}}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "unhealthy", "reason": "fallback_mode"}}
'''

        # 2. Config (minimal valid)
        files["src/core/config.py"] = '''"""
Configuration - FALLBACK MODE
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Minimal settings."""
    app_name: str = "API (Fallback)"
    debug: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    """Get settings singleton."""
    return Settings()
'''

        # 3. Database (minimal valid)
        files["src/core/database.py"] = '''"""
Database - FALLBACK MODE
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
'''

        # 4. Entities (minimal valid with entity names)
        entity_classes = []
        for name in entity_names:
            entity_classes.append(f'''
class {name}Entity(Base):
    """Fallback entity for {name}."""
    __tablename__ = "{name.lower()}s"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
''')

        files["src/models/entities.py"] = f'''"""
SQLAlchemy Models - FALLBACK MODE
"""
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from src.core.database import Base

{"".join(entity_classes) if entity_classes else "# No entities defined"}
'''

        # 5. Schemas (minimal valid)
        schema_classes = []
        for name in entity_names:
            schema_classes.append(f'''
class {name}Base(BaseModel):
    """Base schema for {name}."""
    pass


class {name}Create({name}Base):
    """Create schema for {name}."""
    pass


class {name}Response({name}Base):
    """Response schema for {name}."""
    id: UUID
''')

        files["src/models/schemas.py"] = f'''"""
Pydantic Schemas - FALLBACK MODE
"""
from pydantic import BaseModel
from uuid import UUID

{"".join(schema_classes) if schema_classes else "# No schemas defined"}
'''

        # 6. __init__.py files
        for pkg in ["src", "src/core", "src/models", "src/api", "src/api/routes"]:
            files[f"{pkg}/__init__.py"] = '"""Package initialization - FALLBACK MODE."""\n'

        # 7. Health routes
        files["src/api/routes/health.py"] = '''"""
Health Routes - FALLBACK MODE
"""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health():
    """Health check."""
    return {"status": "unhealthy", "mode": "fallback"}
'''

        # Convert to multi-file string format
        code_parts = []
        for filepath, content in sorted(files.items()):
            code_parts.append(f"=== FILE: {filepath} ===")
            code_parts.append(content)
            code_parts.append("")

        logger.info(
            "Generated fallback structure",
            extra={"files_count": len(files), "mode": "fallback"}
        )

        return "\n".join(code_parts)

    def _generate_main_py(self, spec_requirements) -> str:
        """Generate main.py entry point with FastAPI app, middleware, and routes.

        CRITICAL FIX: Always enable /docs and /redoc for API documentation.
        In production, disable via reverse proxy (nginx/ALB) if needed, not in code.

        Handles both SpecRequirements and ApplicationIR inputs.
        """
        # Handle both SpecRequirements and ApplicationIR inputs
        if spec_requirements is None:
            entities_list = []
        elif hasattr(spec_requirements, 'entities'):
            # SpecRequirements object
            entities_list = spec_requirements.entities
        elif hasattr(spec_requirements, 'domain_model'):
            # ApplicationIR object
            entities_list = spec_requirements.domain_model.entities if spec_requirements.domain_model else []
        else:
            entities_list = []

        # Build entity imports and routers
        imports = []
        routers = []
        for entity in entities_list:
            # Convert CamelCase to snake_case correctly (CartItem → cart_item)
            import re
            entity_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity.name).lower()
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
        "health": "/health",
        "ready": "/health/ready",
        "metrics": "/metrics"
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
        # Handle both SpecRequirements and None (when called with ApplicationIR)
        if spec_requirements is None:
            app_name = "app"
            python_version = "3.11"
        else:
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
asyncio_default_fixture_loop_scope = "function"
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
        # Handle both SpecRequirements and None (when called with ApplicationIR)
        if spec_requirements is None:
            app_name = "app"
        else:
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
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check endpoint (Bug #84: Use urllib instead of requests - requests not installed)
# Bug #130 Fix: Use correct health endpoint path (/health, not /health/health)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

# Run migrations and start application
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000
'''

    def _generate_docker_compose(self, spec_requirements) -> str:
        """Generate docker-compose.yml with all services."""
        # Handle both SpecRequirements and None (when called with ApplicationIR)
        if spec_requirements is None:
            app_name = "app"
        else:
            app_name = spec_requirements.metadata.get("app_name", "app")

        # Use ports that don't conflict with DevMatrix services
        app_port = 8002  # DevMatrix uses 8001
        postgres_port = 5433  # DevMatrix uses 5432
        prometheus_port = 9091  # 9090 is often occupied
        grafana_port = 3002  # 3001 is occupied

        return f'''version: '3.8'

services:
  # Bug #85 + #99: DB init service runs Alembic migrations + seeds test data
  db-init:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: {app_name}_db_init
    environment:
      - DATABASE_URL=postgresql+asyncpg://devmatrix:admin@postgres:5432/{app_name}_db
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - app-network
    # Bug #99: Run alembic THEN seed to ensure migrations are tracked in alembic_version
    command: sh -c "alembic upgrade head && python scripts/seed_db.py"
    restart: "no"

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
      db-init:
        condition: service_completed_successfully
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      # Bug #130 Fix: Use correct health endpoint path (/health, not /health/health)
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"]
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

    def _generate_seed_db_script(self, spec_requirements) -> str:
        """
        Generate seed_db.py script for test data initialization.

        Bug #85 Fix: Creates tables and seeds test data for smoke testing.
        This ensures endpoints with {id} parameters have real resources.
        """
        # Extract entities from spec_requirements or ApplicationIR
        entities_list = []
        if spec_requirements is not None:
            if hasattr(spec_requirements, 'entities'):
                entities_list = spec_requirements.entities
            elif hasattr(spec_requirements, 'domain_model') and spec_requirements.domain_model:
                entities_list = spec_requirements.domain_model.entities

        # Build entity-specific seed code dynamically from IR attributes
        # Bug #94 Fix: Read actual entity attributes from IR instead of hardcoding field names
        seed_blocks = []

        # Predictable UUIDs for smoke testing (by entity index)
        # This ensures consistent IDs across test runs
        uuid_base = "00000000-0000-4000-8000-00000000000"
        entity_uuids = {}  # Map entity_name -> uuid for FK references

        # First pass: assign UUIDs to all entities
        for idx, entity in enumerate(entities_list, start=1):
            entity_uuids[entity.name.lower()] = f"{uuid_base}{idx}"

        # Skip join/item entities (they require parent entities to exist first)
        skip_entities = {'cartitem', 'orderitem', 'lineitem', 'basketitem'}

        for idx, entity in enumerate(entities_list, start=1):
            entity_name = entity.name
            entity_snake = entity_name.lower()

            # Skip join tables - they need parent entities
            if entity_snake in skip_entities:
                continue

            # Bug #92 Fix: Entity classes have "Entity" suffix
            entity_class = f"{entity_name}Entity"
            test_uuid = entity_uuids.get(entity_snake, f"{uuid_base}9")

            # Build field assignments from actual IR attributes
            field_assignments = []
            field_assignments.append(f'id=UUID("{test_uuid}")')

            # Get entity attributes from IR
            attributes = getattr(entity, 'attributes', []) or []

            for attr in attributes:
                attr_name = attr.name
                # Skip id (already set), created_at/updated_at (auto-generated), and relationships
                if attr_name in ('id', 'created_at', 'updated_at'):
                    continue

                # Get data type
                data_type = attr.data_type.value if hasattr(attr.data_type, 'value') else str(attr.data_type)
                data_type_lower = data_type.lower()

                # Bug #98 Fix: Check if nullable - seed all non-nullable fields
                # Default to False (NOT NULL) to ensure required fields get values
                # Note: IR uses 'is_nullable' attribute (domain_model.py:24)
                is_nullable = getattr(attr, 'is_nullable', False)
                has_default = getattr(attr, 'default_value', None) is not None

                # Skip fields that are both nullable AND have defaults (truly optional)
                if is_nullable and has_default:
                    continue

                # Generate appropriate test value based on data type
                if 'uuid' in data_type_lower:
                    # FK reference - try to find the referenced entity
                    if '_id' in attr_name:
                        ref_entity = attr_name.replace('_id', '')
                        ref_uuid = entity_uuids.get(ref_entity, entity_uuids.get('customer', f'{uuid_base}2'))
                        field_assignments.append(f'{attr_name}=UUID("{ref_uuid}")')
                    else:
                        field_assignments.append(f'{attr_name}=UUID("{uuid_base}9")')
                elif 'string' in data_type_lower or 'str' in data_type_lower or 'varchar' in data_type_lower:
                    # String field - generate appropriate test value
                    if 'email' in attr_name.lower():
                        field_assignments.append(f'{attr_name}="test@example.com"')
                    elif 'name' in attr_name.lower():
                        field_assignments.append(f'{attr_name}="Test {entity_name}"')
                    elif 'status' in attr_name.lower():
                        # Bug #167: Business-appropriate status values based on entity type
                        # Orders/Carts need "pending" for checkout operations to work
                        entity_lower = entity_name.lower()
                        if 'payment' in attr_name.lower():
                            field_assignments.append(f'{attr_name}="UNPAID"')
                        elif entity_lower in ['order', 'cart', 'basket', 'checkout'] or 'order' in attr_name.lower():
                            field_assignments.append(f'{attr_name}="PENDING"')
                        else:
                            field_assignments.append(f'{attr_name}="ACTIVE"')
                    elif 'description' in attr_name.lower():
                        field_assignments.append(f'{attr_name}="Test description for {entity_name}"')
                    else:
                        field_assignments.append(f'{attr_name}="test_value"')
                elif 'int' in data_type_lower or 'integer' in data_type_lower:
                    if 'quantity' in attr_name.lower() or 'stock' in attr_name.lower():
                        field_assignments.append(f'{attr_name}=100')
                    else:
                        field_assignments.append(f'{attr_name}=1')
                elif 'float' in data_type_lower or 'decimal' in data_type_lower or 'numeric' in data_type_lower:
                    if 'price' in attr_name.lower() or 'amount' in attr_name.lower():
                        field_assignments.append(f'{attr_name}=99.99')
                    else:
                        field_assignments.append(f'{attr_name}=1.0')
                elif 'bool' in data_type_lower:
                    if 'active' in attr_name.lower():
                        field_assignments.append(f'{attr_name}=True')
                    else:
                        field_assignments.append(f'{attr_name}=True')
                elif 'enum' in data_type_lower:
                    # Bug #102 Fix: Look for enum_values in attr.constraints, not attr directly
                    # IR structure: attr.constraints.enum_values contains the valid values
                    constraints = getattr(attr, 'constraints', None) or {}
                    if isinstance(constraints, dict):
                        enum_values = constraints.get('enum_values', None)
                    else:
                        # Handle constraints as object
                        enum_values = getattr(constraints, 'enum_values', None)

                    # Also check direct attribute (legacy support)
                    if not enum_values:
                        enum_values = getattr(attr, 'enum_values', None) or getattr(attr, 'allowed_values', None)

                    # Priority: 1) First enum value, 2) default_value from IR, 3) hardcoded fallbacks
                    if enum_values and len(enum_values) > 0:
                        # Use first enum value
                        field_assignments.append(f'{attr_name}="{enum_values[0]}"')
                    elif has_default and isinstance(attr.default_value, str):
                        # Bug #102: Use IR's default_value if available
                        field_assignments.append(f'{attr_name}="{attr.default_value}"')
                    elif 'payment' in attr_name.lower():
                        field_assignments.append(f'{attr_name}="PENDING"')
                    elif 'order' in attr_name.lower():
                        field_assignments.append(f'{attr_name}="PENDING_PAYMENT"')
                    elif 'status' in attr_name.lower():
                        field_assignments.append(f'{attr_name}="OPEN"')
                    else:
                        field_assignments.append(f'{attr_name}="ACTIVE"')
                # Skip datetime fields - they usually have defaults

            # Only create seed if we have meaningful fields beyond just id
            if len(field_assignments) > 1:
                fields_str = ',\n                '.join(field_assignments)
                seed_blocks.append(f'''            # Seed {entity_name} with predictable UUID for smoke testing
            from src.models.entities import {entity_class}
            from uuid import UUID
            test_{entity_snake} = {entity_class}(
                {fields_str}
            )
            session.add(test_{entity_snake})
            logger.info("✅ Created test {entity_name} with ID {test_uuid}")''')

        seed_code = "\n".join(seed_blocks) if seed_blocks else "            pass  # No entities to seed"

        return f'''#!/usr/bin/env python3
"""
Database Initialization and Seed Script

Bug #85 Fix: Creates tables and seeds test data for smoke testing.
Run this before starting the app to ensure test resources exist.

Usage:
    python scripts/seed_db.py
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

logger = structlog.get_logger(__name__)


async def init_database():
    """
    Initialize database tables.

    Bug #99 Fix: When called from Docker, Alembic runs first via docker-compose.
    This function is kept for standalone usage but handles "already exists" gracefully.
    """
    from src.core.database import init_db
    logger.info("🔄 Creating database tables (if not exists)...")
    try:
        await init_db()
        logger.info("✅ Database tables created")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("ℹ️ Tables already exist (alembic ran first)")
        else:
            raise


async def seed_test_data():
    """Seed minimal test data for smoke testing.

    Bug #143 Fix: Use direct session creation instead of get_db() generator.
    The generator pattern causes issues when exiting with 'break' - the
    generator cleanup code tries another commit which can trigger rollback.
    """
    from src.core.database import _get_session_maker

    logger.info("🌱 Seeding test data...")

    session_maker = _get_session_maker()
    async with session_maker() as session:
        try:
{seed_code}
            await session.commit()
            logger.info("✅ Test data seeded successfully")
        except Exception as e:
            await session.rollback()
            # Ignore duplicate key errors (data already exists)
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                logger.info("ℹ️ Test data already exists, skipping seed")
            else:
                logger.error(f"❌ Failed to seed data: {{e}}")
                raise


async def main():
    """Initialize database and seed test data."""
    logger.info("🚀 Starting database initialization...")

    try:
        await init_database()
        await seed_test_data()
        logger.info("✅ Database initialization complete!")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {{e}}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
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

    def _generate_middleware(self) -> str:
        """
        Generate middleware with proper CSP for FastAPI docs.

        CRITICAL FIX: CSP allows Swagger UI resources from CDN.
        Enables /docs and /redoc to load properly without CSP violations.

        CSP Policy:
        - default-src 'self': Only same-origin by default
        - style-src 'self' cdn.jsdelivr.net: Allow Swagger UI CSS
        - script-src 'self' cdn.jsdelivr.net 'unsafe-inline': Allow Swagger UI JS + inline init
        - img-src 'self' fastapi.tiangolo.com data:: Allow FastAPI favicon + inline images
        """
        return '''"""
Custom Middleware

Request ID tracking, metrics, and security headers.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog
from uuid import uuid4
import time
from prometheus_client import Counter, Histogram

# Initialize logger
logger = structlog.get_logger(__name__)

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics for Prometheus."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    CSP allows FastAPI docs (/docs, /redoc) to load Swagger UI from CDN.
    In production, use reverse proxy (nginx, ALB) for stricter CSP if needed.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CSP: Allow Swagger UI resources for /docs and /redoc
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' cdn.jsdelivr.net; "
            "script-src 'self' cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' fastapi.tiangolo.com data:"
        )

        return response
'''

    def _generate_health_routes(self) -> str:
        """
        Generate health check routes with correct SQLAlchemy text() usage.

        CRITICAL FIX: Uses text("SELECT 1") instead of "SELECT 1" to avoid
        SQLAlchemy deprecation warning.

        Provides two endpoints:
        - /health: Basic liveness check (Bug #130 fix: was /health/health)
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


@router.get("")
async def health_check():
    """
    Basic health check - always returns OK.
    Bug #129 Fix: Changed from /health to "" (prefix already adds /health)

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

    def _generate_database_module(self) -> str:
        """
        Generate database.py with lazy initialization.

        Bug #30 fix: Uses lazy initialization to avoid creating the engine
        at module import time. This prevents "asyncio extension requires
        an async driver" errors when pytest imports conftest.py which
        imports database.py before the test DATABASE_URL is configured.

        The engine is only created when get_db() or init_db() is called.
        """
        return '''"""
Database Configuration and Session Management

Provides async database connection using SQLAlchemy 2.0+ with AsyncEngine.
Uses lazy initialization to avoid engine creation at import time.
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import declarative_base
from src.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)

# Create declarative base for models
Base = declarative_base()

# Lazy initialization - engine created on first use
_engine: Optional[AsyncEngine] = None
_async_session: Optional[async_sessionmaker] = None


def _get_engine() -> AsyncEngine:
    """
    Get or create the database engine (lazy initialization).

    Bug #30 fix: Engine is created on first access, not at module import.
    This allows tests to override DATABASE_URL before engine creation.

    Bug #77 fix: Added pool_timeout and SQLite-specific connect_args to prevent
    connection pool exhaustion and thread locking issues.

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _engine
    if _engine is None:
        settings = get_settings()

        # Bug #77: Build engine kwargs with timeout and SQLite support
        engine_kwargs = {
            "echo": settings.db_echo,
            "pool_pre_ping": True,
            "future": True,
            "pool_timeout": 30,  # Bug #77: Don't wait forever for connections
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }

        # Bug #77: SQLite-specific configuration
        # SQLite doesn't support pool_size/max_overflow, needs different config
        if "sqlite" in settings.database_url.lower():
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            # For SQLite, use StaticPool to avoid connection issues
            from sqlalchemy.pool import StaticPool
            engine_kwargs["poolclass"] = StaticPool
        else:
            # PostgreSQL/MySQL configuration
            engine_kwargs["pool_size"] = settings.db_pool_size
            engine_kwargs["max_overflow"] = settings.db_max_overflow

        _engine = create_async_engine(settings.database_url, **engine_kwargs)
        logger.info("database_engine_created", url=settings.database_url[:50] + "[truncated]")
    return _engine


def _get_session_maker() -> async_sessionmaker:
    """
    Get or create the session factory (lazy initialization).

    Returns:
        async_sessionmaker: SQLAlchemy async session factory
    """
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session


# Module-level engine accessor (for compatibility)
# Note: Cannot use @property on module functions - use direct function call
def get_engine() -> AsyncEngine:
    """Get the database engine (lazy initialization)."""
    return _get_engine()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session for request
    """
    session_maker = _get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in models.
    Should only be used for development/testing.
    Use Alembic migrations for production.

    Bug #97 Fix: Import models before create_all to ensure
    they are registered in Base.metadata.

    Bug #99 Fix: Use checkfirst=True to be idempotent - prevents
    "DuplicateTable" errors when alembic also creates tables.
    """
    # Bug #97: Import models to register them in Base.metadata
    # This prevents "relation does not exist" errors when seed_db.py
    # calls init_db() before importing entity classes
    import src.models.entities  # noqa: F401 - Required for create_all

    engine = _get_engine()
    async with engine.begin() as conn:
        # Bug #99: checkfirst=True makes this idempotent
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
        logger.info("Database tables created")


async def close_db() -> None:
    """
    Close database connections.

    Properly disposes of the connection pool.
    """
    global _engine, _async_session
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session = None
        logger.info("Database connections closed")
'''

    def _generate_exception_handlers(self) -> str:
        """
        Generate exception handlers with jsonable_encoder.

        Bug #31 fix: Always includes jsonable_encoder for UUID serialization
        to avoid triggering unnecessary auto-repair during validation.
        """
        return '''"""
Global Exception Handlers

Centralized error handling for consistent API responses.
Uses jsonable_encoder for proper UUID serialization.
"""
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSON response with error details
    """
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "path": request.url.path,
            "request_id": request.headers.get("X-Request-ID")
        })
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions (4xx, 5xx).

    Args:
        request: The request that caused the exception
        exc: The HTTP exception that was raised

    Returns:
        JSON response with error details
    """
    log_level = "warning" if 400 <= exc.status_code < 500 else "error"
    getattr(logger, log_level)(
        "http_exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({
            "error": f"http_{exc.status_code}",
            "message": exc.detail,
            "path": request.url.path,
            "request_id": request.headers.get("X-Request-ID")
        })
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.

    Args:
        request: The request that caused the validation error
        exc: The validation exception that was raised

    Returns:
        JSON response with validation error details
    """
    logger.warning(
        "validation_error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "error": "validation_error",
            "message": "Request validation failed",
            "errors": errors,
            "path": request.url.path,
            "request_id": request.headers.get("X-Request-ID")
        })
    )
'''

    def _generate_test_factories(self, entities: list) -> str:
        """
        Generate test data factories for entities (AST stratum).

        Bug #52 Fix: The PatternBank template for factories.py had invalid Jinja2
        syntax (uuid4().hex[:8] is Python, not Jinja2). This method generates
        factories programmatically from ApplicationIR entities.

        Args:
            entities: List of normalized entity dictionaries from ApplicationIRNormalizer

        Returns:
            Generated Python code for test factories
        """
        import re

        code_lines = [
            '"""',
            'Test Data Factories',
            '',
            'Factory classes for creating test data with realistic defaults.',
            '"""',
            'from datetime import datetime, timezone',
            'from decimal import Decimal',
            'from uuid import uuid4',
            'from typing import Dict, Any, List',
            '',
        ]

        # Collect imports for all entity schemas
        imports = []
        for entity in entities:
            entity_name = entity.get('name', '')
            imports.append(f'{entity_name}Create')

        if imports:
            code_lines.append(f'from src.models.schemas import {", ".join(imports)}')
            code_lines.append('')
            code_lines.append('')

        # Generate factory class for each entity
        for entity in entities:
            entity_name = entity.get('name', '')
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
            fields = entity.get('fields', [])

            code_lines.append(f'class {entity_name}Factory:')
            code_lines.append(f'    """Factory for creating {entity_name} test data."""')
            code_lines.append('')
            code_lines.append('    @staticmethod')
            code_lines.append(f'    def create(**kwargs: Any) -> {entity_name}Create:')
            code_lines.append('        """')
            code_lines.append(f'        Create {entity_name}Create schema with realistic defaults.')
            code_lines.append('')
            code_lines.append('        Args:')
            code_lines.append('            **kwargs: Override default values')
            code_lines.append('')
            code_lines.append('        Returns:')
            code_lines.append(f'            {entity_name}Create schema')
            code_lines.append('        """')
            code_lines.append('        defaults: Dict[str, Any] = {')

            # Generate default values for each field
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'str')
                is_primary_key = field.get('primary_key', False)
                default_value = field.get('default')

                # Skip primary keys and timestamps (they're auto-generated)
                if is_primary_key or field_name in ['id', 'created_at', 'updated_at']:
                    continue

                # Generate appropriate default based on type
                if field_type == 'str':
                    code_lines.append(f'            "{field_name}": f"{field_name}_{{uuid4().hex[:8]}}",')
                elif field_type == 'bool':
                    default_val = default_value if default_value is not None else False
                    code_lines.append(f'            "{field_name}": {default_val},')
                elif field_type == 'int':
                    default_val = default_value if default_value is not None else 0
                    code_lines.append(f'            "{field_name}": {default_val},')
                elif field_type in ['float', 'Decimal']:
                    default_val = default_value if default_value is not None else 'Decimal("99.99")'
                    if isinstance(default_val, (int, float)):
                        default_val = f'Decimal("{default_val}")'
                    code_lines.append(f'            "{field_name}": {default_val},')
                elif field_type == 'datetime':
                    code_lines.append(f'            "{field_name}": datetime.now(timezone.utc),')
                elif field_type == 'UUID':
                    code_lines.append(f'            "{field_name}": uuid4(),')

            code_lines.append('        }')
            code_lines.append('        defaults.update(kwargs)')
            code_lines.append(f'        return {entity_name}Create(**defaults)')
            code_lines.append('')
            code_lines.append('    @staticmethod')
            code_lines.append(f'    def create_batch(n: int, **kwargs: Any) -> List[{entity_name}Create]:')
            code_lines.append('        """')
            code_lines.append(f'        Create multiple {entity_name}Create schemas.')
            code_lines.append('')
            code_lines.append('        Args:')
            code_lines.append('            n: Number of instances to create')
            code_lines.append('            **kwargs: Override default values for all instances')
            code_lines.append('')
            code_lines.append('        Returns:')
            code_lines.append(f'            List of {entity_name}Create schemas')
            code_lines.append('        """')
            code_lines.append(f'        return [{entity_name}Factory.create(**kwargs) for _ in range(n)]')
            code_lines.append('')
            code_lines.append('')

        return '\n'.join(code_lines)

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
