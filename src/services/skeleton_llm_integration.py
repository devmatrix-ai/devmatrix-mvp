"""
Skeleton + LLM Integration Service - Phase 6

Integrates the SkeletonGenerator with the LLM stratum for constrained code generation.
The LLM only fills designated slots, cannot modify structural elements.

Flow:
1. SkeletonGenerator creates structural code with LLM_SLOT markers
2. LLM receives skeleton + slot context, fills only the slots
3. LLMSlotFiller validates and integrates LLM content
4. Final code has LLM markers stripped
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from src.services.skeleton_generator import (
    SkeletonGenerator,
    LLMSlotFiller,
    LLMSlot,
    SlotType,
    SlotValidationResult,
    create_skeleton_for_entity,
    create_skeleton_for_service,
    create_skeleton_for_router,
    create_skeleton_for_schema,
)
from src.services.stratum_classification import (
    Stratum,
    AtomKind,
    get_stratum_by_kind,
    classify_file,
    is_llm_allowed,
)

logger = logging.getLogger(__name__)


class LLMGenerationMode(str, Enum):
    """How the LLM should generate code."""

    SLOT_FILL = "slot_fill"        # Fill designated slots only
    FULL_GENERATION = "full"       # Full code generation (legacy)
    REPAIR = "repair"              # Targeted repair patches


@dataclass
class SlotContext:
    """Context provided to LLM for filling a slot."""

    slot_name: str
    slot_type: SlotType
    description: str
    entity_context: Dict[str, Any]
    ir_context: Dict[str, Any]
    constraints: List[str]
    examples: List[str] = field(default_factory=list)


@dataclass
class SlotFillRequest:
    """Request for LLM to fill slots in skeleton code."""

    skeleton_code: str
    template_type: str
    slots_to_fill: List[SlotContext]
    generation_context: Dict[str, Any]


@dataclass
class SlotFillResult:
    """Result of LLM slot filling."""

    success: bool
    filled_code: str
    validation_results: List[SlotValidationResult]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SkeletonLLMIntegration:
    """
    Orchestrates skeleton generation + LLM slot filling.

    This is the main integration point between deterministic skeleton
    generation and LLM-based business logic filling.
    """

    def __init__(
        self,
        strict_mode: bool = True,
        max_retries: int = 2,
    ):
        """
        Initialize the integration service.

        Args:
            strict_mode: If True, reject invalid slot content
            max_retries: Max retries for LLM slot filling
        """
        self.strict_mode = strict_mode
        self.max_retries = max_retries
        self.generator = SkeletonGenerator(strict_mode=strict_mode)
        self.filler = LLMSlotFiller(self.generator, strict_mode=strict_mode)

    def generate_with_skeleton(
        self,
        atom_kind: AtomKind,
        ir_context: Dict[str, Any],
        llm_callback: Optional[callable] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate code using skeleton + LLM slot filling.

        Args:
            atom_kind: Type of code to generate
            ir_context: IR data for generation context
            llm_callback: Optional callback for LLM slot filling

        Returns:
            Tuple of (generated code, generation metadata)
        """
        stratum = get_stratum_by_kind(atom_kind)

        if stratum == Stratum.TEMPLATE:
            return self._generate_template(atom_kind, ir_context)
        elif stratum == Stratum.AST:
            return self._generate_ast(atom_kind, ir_context)
        elif stratum == Stratum.LLM:
            return self._generate_llm_with_skeleton(
                atom_kind, ir_context, llm_callback
            )
        else:
            raise ValueError(f"Unknown stratum: {stratum}")

    def _generate_template(
        self,
        atom_kind: AtomKind,
        ir_context: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate template stratum code (no LLM, no slots)."""
        metadata = {
            "stratum": Stratum.TEMPLATE.value,
            "atom_kind": atom_kind.value,
            "llm_used": False,
            "slots_filled": 0,
        }

        # Template generation uses hardcoded patterns
        # This is handled by existing template generators
        return "", metadata

    def _generate_ast(
        self,
        atom_kind: AtomKind,
        ir_context: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate AST stratum code (deterministic from IR)."""
        metadata = {
            "stratum": Stratum.AST.value,
            "atom_kind": atom_kind.value,
            "llm_used": False,
            "slots_filled": 0,
        }

        # AST generation is deterministic from IR
        # Map atom kinds to skeleton generators
        if atom_kind == AtomKind.ENTITY_MODEL:
            entity_name = ir_context.get("entity_name", "Unknown")
            table_name = ir_context.get("table_name")
            skeleton = create_skeleton_for_entity(entity_name, table_name)

            # For AST, we fill slots deterministically from IR
            slot_contents = self._extract_ast_slot_contents(
                atom_kind, ir_context
            )

            filled, results = self.filler.fill_slots(
                skeleton, slot_contents, "entity"
            )

            # Strip markers for final code
            final_code = self.filler.strip_markers(filled)
            metadata["slots_filled"] = len(slot_contents)

            return final_code, metadata

        elif atom_kind == AtomKind.PYDANTIC_SCHEMA:
            entity_name = ir_context.get("entity_name", "Unknown")
            skeleton = create_skeleton_for_schema(entity_name)

            slot_contents = self._extract_ast_slot_contents(
                atom_kind, ir_context
            )

            filled, results = self.filler.fill_slots(
                skeleton, slot_contents, "schema"
            )

            final_code = self.filler.strip_markers(filled)
            metadata["slots_filled"] = len(slot_contents)

            return final_code, metadata

        # Default: return empty (handled by existing generators)
        return "", metadata

    def _generate_llm_with_skeleton(
        self,
        atom_kind: AtomKind,
        ir_context: Dict[str, Any],
        llm_callback: Optional[callable] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate LLM stratum code using skeleton + slot filling.

        This is the core innovation: LLM only fills designated slots.
        """
        metadata = {
            "stratum": Stratum.LLM.value,
            "atom_kind": atom_kind.value,
            "llm_used": True,
            "slots_filled": 0,
            "validation_errors": [],
        }

        # Get skeleton template based on atom kind
        skeleton, template_type = self._get_skeleton_for_llm_atom(
            atom_kind, ir_context
        )

        if not skeleton:
            # Fallback to full LLM generation (legacy)
            metadata["llm_used"] = True
            metadata["fallback_to_full"] = True
            return "", metadata

        # Get slot contexts for LLM
        slot_contexts = self._build_slot_contexts(
            template_type, ir_context
        )

        if llm_callback is None:
            # No LLM callback, return skeleton with unfilled slots
            metadata["llm_used"] = False
            return skeleton, metadata

        # Fill slots with LLM
        result = self._fill_slots_with_llm(
            skeleton,
            template_type,
            slot_contexts,
            ir_context,
            llm_callback,
        )

        if not result.success:
            metadata["validation_errors"] = result.errors
            # Return skeleton with partial fills
            return result.filled_code, metadata

        # Strip markers for final code
        final_code = self.filler.strip_markers(result.filled_code)
        metadata["slots_filled"] = len(slot_contexts)

        return final_code, metadata

    def _get_skeleton_for_llm_atom(
        self,
        atom_kind: AtomKind,
        ir_context: Dict[str, Any],
    ) -> Tuple[str, str]:
        """
        Get the appropriate skeleton template for an LLM atom.

        Returns:
            Tuple of (skeleton_code, template_type)
        """
        entity_name = ir_context.get("entity_name", "Service")

        if atom_kind == AtomKind.FLOW_SERVICE:
            skeleton = create_skeleton_for_service(entity_name)
            return skeleton, "service"

        elif atom_kind == AtomKind.CUSTOM_ENDPOINT:
            skeleton = create_skeleton_for_router(entity_name)
            return skeleton, "router"

        elif atom_kind == AtomKind.BUSINESS_RULE:
            # Business rules use service template
            skeleton = create_skeleton_for_service(entity_name)
            return skeleton, "service"

        # No skeleton for other LLM atoms
        return "", ""

    def _build_slot_contexts(
        self,
        template_type: str,
        ir_context: Dict[str, Any],
    ) -> List[SlotContext]:
        """Build context for each slot in the template."""
        template = self.generator.get_template(template_type)
        if not template:
            return []

        contexts = []
        for slot in template.slots:
            ctx = SlotContext(
                slot_name=slot.name,
                slot_type=slot.slot_type,
                description=slot.description,
                entity_context=ir_context.get("entity", {}),
                ir_context=ir_context,
                constraints=[c.value for c in slot.constraints],
                examples=self._get_slot_examples(slot, ir_context),
            )
            contexts.append(ctx)

        return contexts

    def _get_slot_examples(
        self,
        slot: LLMSlot,
        ir_context: Dict[str, Any],
    ) -> List[str]:
        """Get examples for a slot based on its type."""
        examples = []

        if slot.slot_type == SlotType.BUSINESS_LOGIC:
            examples.append("# Check business rules before proceeding")
            examples.append("# Apply validation logic")

        elif slot.slot_type == SlotType.VALIDATION:
            examples.append("if not data.is_valid():")
            examples.append("    raise ValueError('Invalid data')")

        elif slot.slot_type == SlotType.QUERY:
            examples.append("query = query.options(selectinload(Entity.items))")

        elif slot.slot_type == SlotType.TRANSFORMATION:
            examples.append("name=data.name,")
            examples.append("price=data.price,")

        return examples

    def _fill_slots_with_llm(
        self,
        skeleton: str,
        template_type: str,
        slot_contexts: List[SlotContext],
        ir_context: Dict[str, Any],
        llm_callback: callable,
    ) -> SlotFillResult:
        """
        Use LLM to fill slots in skeleton code.

        Args:
            skeleton: Skeleton code with LLM_SLOT markers
            template_type: Type of template for validation
            slot_contexts: Context for each slot
            ir_context: Full IR context
            llm_callback: Function to call LLM

        Returns:
            SlotFillResult with filled code and validation
        """
        prompt = self._build_slot_fill_prompt(
            skeleton, slot_contexts, ir_context
        )

        for attempt in range(self.max_retries + 1):
            try:
                # Call LLM to fill slots
                llm_response = llm_callback(prompt)

                # Parse slot contents from LLM response
                slot_contents = self._parse_llm_slot_response(llm_response)

                # Fill and validate
                filled_code, validation_results = self.filler.fill_slots(
                    skeleton, slot_contents, template_type
                )

                # Check for validation errors
                errors = []
                warnings = []
                for result in validation_results:
                    errors.extend(result.errors)
                    warnings.extend(result.warnings)

                if errors and self.strict_mode:
                    if attempt < self.max_retries:
                        # Retry with error feedback
                        prompt = self._add_error_feedback(prompt, errors)
                        continue

                return SlotFillResult(
                    success=len(errors) == 0,
                    filled_code=filled_code,
                    validation_results=validation_results,
                    errors=errors,
                    warnings=warnings,
                )

            except Exception as e:
                logger.error(f"LLM slot fill error: {e}")
                if attempt == self.max_retries:
                    return SlotFillResult(
                        success=False,
                        filled_code=skeleton,
                        validation_results=[],
                        errors=[str(e)],
                    )

        return SlotFillResult(
            success=False,
            filled_code=skeleton,
            validation_results=[],
            errors=["Max retries exceeded"],
        )

    def _build_slot_fill_prompt(
        self,
        skeleton: str,
        slot_contexts: List[SlotContext],
        ir_context: Dict[str, Any],
    ) -> str:
        """Build the prompt for LLM slot filling."""
        prompt_parts = [
            "You are filling designated slots in a code skeleton.",
            "You may ONLY modify content between [LLM_SLOT:start:name] and [LLM_SLOT:end:name] markers.",
            "Do NOT add imports, define new classes, or modify structure.",
            "",
            "=== SKELETON CODE ===",
            skeleton,
            "",
            "=== SLOTS TO FILL ===",
        ]

        for ctx in slot_contexts:
            prompt_parts.append(f"\n### Slot: {ctx.slot_name}")
            prompt_parts.append(f"Type: {ctx.slot_type.value}")
            prompt_parts.append(f"Description: {ctx.description}")
            if ctx.constraints:
                prompt_parts.append(f"Constraints: {', '.join(ctx.constraints)}")
            if ctx.examples:
                prompt_parts.append("Examples:")
                for ex in ctx.examples:
                    prompt_parts.append(f"  {ex}")

        prompt_parts.append("\n=== IR CONTEXT ===")
        prompt_parts.append(f"Entity: {ir_context.get('entity_name', 'Unknown')}")

        if "fields" in ir_context:
            prompt_parts.append("Fields:")
            for f in ir_context["fields"]:
                prompt_parts.append(f"  - {f.get('name')}: {f.get('type')}")

        prompt_parts.append("\n=== RESPONSE FORMAT ===")
        prompt_parts.append("For each slot, provide:")
        prompt_parts.append("```slot:slot_name")
        prompt_parts.append("# Your code here")
        prompt_parts.append("```")

        return "\n".join(prompt_parts)

    def _parse_llm_slot_response(
        self,
        llm_response: str,
    ) -> Dict[str, str]:
        """Parse slot contents from LLM response."""
        import re

        slot_contents = {}

        # Pattern: ```slot:slot_name\ncode\n```
        pattern = r"```slot:(\w+)\n(.*?)```"
        matches = re.finditer(pattern, llm_response, re.DOTALL)

        for match in matches:
            slot_name = match.group(1)
            content = match.group(2).strip()
            slot_contents[slot_name] = content

        return slot_contents

    def _add_error_feedback(
        self,
        original_prompt: str,
        errors: List[str],
    ) -> str:
        """Add error feedback to prompt for retry."""
        feedback = [
            "",
            "=== PREVIOUS ATTEMPT HAD ERRORS ===",
            "Please fix these issues:",
        ]
        for error in errors:
            feedback.append(f"- {error}")
        feedback.append("")
        feedback.append("Remember: Do NOT add imports or define new classes/functions.")

        return original_prompt + "\n".join(feedback)

    def _extract_ast_slot_contents(
        self,
        atom_kind: AtomKind,
        ir_context: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Extract slot contents deterministically from IR for AST stratum.

        This is used when we want deterministic generation without LLM.
        """
        slot_contents = {}

        if atom_kind == AtomKind.ENTITY_MODEL:
            # Generate columns from IR fields
            fields = ir_context.get("fields", [])
            columns = []
            for field in fields:
                name = field.get("name")
                ftype = field.get("type", "str")
                required = field.get("required", True)

                # Skip system fields
                if name in ["id", "created_at", "updated_at"]:
                    continue

                sql_type = self._map_type_to_sqlalchemy(ftype)
                nullable = "False" if required else "True"
                columns.append(
                    f"    {name}: Mapped[{self._get_python_type(ftype)}] = "
                    f"mapped_column({sql_type}, nullable={nullable})"
                )

            slot_contents["entity_columns"] = "\n".join(columns)

        elif atom_kind == AtomKind.PYDANTIC_SCHEMA:
            # Generate schema fields from IR
            fields = ir_context.get("fields", [])

            base_fields = []
            for field in fields:
                name = field.get("name")
                ftype = field.get("type", "str")
                required = field.get("required", True)

                # Skip system fields
                if name in ["id", "created_at", "updated_at"]:
                    continue

                py_type = self._get_python_type(ftype)
                if required:
                    base_fields.append(f"    {name}: {py_type}")
                else:
                    base_fields.append(f"    {name}: Optional[{py_type}] = None")

            slot_contents["schema_base_fields"] = "\n".join(base_fields)

            # Update fields are all optional
            update_fields = []
            for field in fields:
                name = field.get("name")
                ftype = field.get("type", "str")

                if name in ["id", "created_at", "updated_at"]:
                    continue

                py_type = self._get_python_type(ftype)
                update_fields.append(f"    {name}: Optional[{py_type}] = None")

            slot_contents["schema_update_fields"] = "\n".join(update_fields)

        return slot_contents

    def _map_type_to_sqlalchemy(self, field_type: str) -> str:
        """Map field type to SQLAlchemy column type."""
        type_map = {
            "str": "String(255)",
            "string": "String(255)",
            "int": "Integer",
            "integer": "Integer",
            "float": "Numeric(10, 2)",
            "decimal": "Numeric(10, 2)",
            "bool": "Boolean",
            "boolean": "Boolean",
            "datetime": "DateTime(timezone=True)",
            "uuid": "UUID(as_uuid=False)",
            "text": "Text",
        }
        return type_map.get(field_type.lower(), "String(255)")

    def _get_python_type(self, field_type: str) -> str:
        """Get Python type annotation for a field type."""
        type_map = {
            "str": "str",
            "string": "str",
            "int": "int",
            "integer": "int",
            "float": "float",
            "decimal": "float",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "uuid": "str",
            "text": "str",
        }
        return type_map.get(field_type.lower(), "str")


def create_slot_fill_request(
    atom_kind: AtomKind,
    ir_context: Dict[str, Any],
) -> SlotFillRequest:
    """
    Create a slot fill request for a given atom kind.

    This is a convenience function for external callers.

    Args:
        atom_kind: Type of code to generate
        ir_context: IR data for generation

    Returns:
        SlotFillRequest ready for LLM processing
    """
    integration = SkeletonLLMIntegration()

    entity_name = ir_context.get("entity_name", "Unknown")

    # Get skeleton based on atom kind
    if atom_kind in [AtomKind.FLOW_SERVICE, AtomKind.BUSINESS_RULE]:
        skeleton = create_skeleton_for_service(entity_name)
        template_type = "service"
    elif atom_kind == AtomKind.CUSTOM_ENDPOINT:
        skeleton = create_skeleton_for_router(entity_name)
        template_type = "router"
    else:
        skeleton = ""
        template_type = ""

    slot_contexts = integration._build_slot_contexts(template_type, ir_context)

    return SlotFillRequest(
        skeleton_code=skeleton,
        template_type=template_type,
        slots_to_fill=slot_contexts,
        generation_context=ir_context,
    )


def validate_llm_slot_content(
    slot_name: str,
    content: str,
    template_type: str,
) -> SlotValidationResult:
    """
    Validate LLM-generated content for a slot.

    Args:
        slot_name: Name of the slot
        content: LLM-generated content
        template_type: Template type for slot lookup

    Returns:
        Validation result
    """
    integration = SkeletonLLMIntegration()
    template = integration.generator.get_template(template_type)

    slot_def = None
    if template:
        slot_def = template.get_slot(slot_name)

    return integration.filler._validate_slot_content(
        slot_name, content, slot_def
    )
