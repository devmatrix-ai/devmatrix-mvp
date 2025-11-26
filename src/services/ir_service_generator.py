"""
Service Generator from BehaviorModelIR.

Generates service methods from flows and invariants defined in the IR.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.cognitive.ir.behavior_model import (
    BehaviorModelIR,
    Flow,
    FlowType,
    Step,
    Invariant
)
from src.cognitive.ir.domain_model import DomainModelIR, Entity
from src.cognitive.ir.application_ir import ApplicationIR


@dataclass
class GeneratedMethod:
    """Represents a generated service method."""
    name: str
    flow_name: str
    flow_type: FlowType
    code: str
    target_entity: Optional[str] = None


class ServiceGeneratorFromIR:
    """
    Generate service methods from BehaviorModelIR flows.

    Transforms flows into executable service methods with:
    - Step-by-step implementation comments
    - Validation logic from invariants
    - Entity-specific business logic
    """

    def __init__(
        self,
        behavior_model: BehaviorModelIR,
        domain_model: Optional[DomainModelIR] = None
    ):
        self.behavior_model = behavior_model
        self.domain_model = domain_model
        self.entity_names = self._extract_entity_names()

    def _extract_entity_names(self) -> List[str]:
        """Extract entity names from domain model."""
        if self.domain_model and self.domain_model.entities:
            return [e.name for e in self.domain_model.entities]
        return []

    def _normalize_method_name(self, name: str) -> str:
        """Convert flow name to valid Python method name."""
        # Remove special chars, convert spaces to underscores
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name.strip())
        name = name.lower()
        # Ensure valid Python identifier
        if name and name[0].isdigit():
            name = f"flow_{name}"
        return name or "unnamed_flow"

    def _infer_target_entity(self, flow: Flow) -> Optional[str]:
        """Infer target entity from flow name or steps."""
        # Check flow name for entity reference
        flow_name_lower = flow.name.lower()
        for entity in self.entity_names:
            if entity.lower() in flow_name_lower:
                return entity

        # Check steps for target_entity
        for step in flow.steps:
            if step.target_entity:
                return step.target_entity

        return None

    def _generate_step_code(self, step: Step, indent: str = "        ") -> str:
        """Generate code for a single step."""
        lines = []

        # Step comment
        lines.append(f"{indent}# Step {step.order}: {step.description}")

        # Generate action placeholder based on action type
        action_lower = step.action.lower()

        if "validate" in action_lower or "check" in action_lower:
            lines.append(f"{indent}# TODO: Implement validation - {step.action}")
            if step.condition:
                lines.append(f"{indent}# Condition: {step.condition}")
            lines.append(f"{indent}pass  # Validation placeholder")

        elif "create" in action_lower or "insert" in action_lower:
            if step.target_entity:
                lines.append(f"{indent}# Create {step.target_entity}")
                lines.append(f"{indent}# new_{step.target_entity.lower()} = await self.repo.create(data)")
            lines.append(f"{indent}pass  # Create placeholder")

        elif "update" in action_lower or "modify" in action_lower:
            if step.target_entity:
                lines.append(f"{indent}# Update {step.target_entity}")
                lines.append(f"{indent}# await self.repo.update(id, data)")
            lines.append(f"{indent}pass  # Update placeholder")

        elif "delete" in action_lower or "remove" in action_lower:
            lines.append(f"{indent}pass  # Delete placeholder")

        elif "notify" in action_lower or "send" in action_lower:
            lines.append(f"{indent}# TODO: Implement notification - {step.action}")
            lines.append(f"{indent}logger.info(f\"Notification: {step.description}\")")

        elif "calculate" in action_lower or "compute" in action_lower:
            lines.append(f"{indent}# TODO: Implement calculation - {step.action}")
            lines.append(f"{indent}result = None  # Calculation placeholder")

        else:
            lines.append(f"{indent}# Action: {step.action}")
            lines.append(f"{indent}pass  # Generic action placeholder")

        return "\n".join(lines)

    def _generate_invariant_check(self, invariant: Invariant, indent: str = "        ") -> str:
        """Generate validation code for an invariant."""
        lines = []
        lines.append(f"{indent}# Invariant: {invariant.description}")

        if invariant.expression:
            lines.append(f"{indent}# Expression: {invariant.expression}")
            lines.append(f"{indent}# if not ({invariant.expression}):")
            lines.append(f'{indent}#     raise ValueError("{invariant.description}")')
        else:
            lines.append(f"{indent}# TODO: Implement invariant check for {invariant.entity}")

        return "\n".join(lines)

    def generate_flow_method(self, flow: Flow) -> GeneratedMethod:
        """Generate a service method from a flow."""
        method_name = self._normalize_method_name(flow.name)
        target_entity = self._infer_target_entity(flow)

        # Build method signature
        lines = []
        lines.append(f"    async def {method_name}(self, **kwargs) -> Any:")
        lines.append(f'        """')
        lines.append(f'        {flow.name}')
        lines.append(f'        ')
        if flow.description:
            lines.append(f'        {flow.description}')
            lines.append(f'        ')
        lines.append(f'        Flow Type: {flow.type.value}')
        lines.append(f'        Trigger: {flow.trigger}')
        lines.append(f'        """')

        # Add related invariants as validations
        related_invariants = self._get_related_invariants(target_entity)
        if related_invariants:
            lines.append(f"        # === Invariant Validations ===")
            for inv in related_invariants:
                lines.append(self._generate_invariant_check(inv))
            lines.append("")

        # Generate steps
        if flow.steps:
            lines.append(f"        # === Flow Steps ===")
            sorted_steps = sorted(flow.steps, key=lambda s: s.order)
            for step in sorted_steps:
                lines.append(self._generate_step_code(step))
                lines.append("")
        else:
            lines.append(f"        # No steps defined - implement business logic here")
            lines.append(f"        pass")

        # Return statement
        lines.append(f"        # Return result")
        lines.append(f"        return {{'status': 'completed', 'flow': '{flow.name}'}}")

        code = "\n".join(lines)

        return GeneratedMethod(
            name=method_name,
            flow_name=flow.name,
            flow_type=flow.type,
            code=code,
            target_entity=target_entity
        )

    def _get_related_invariants(self, entity: Optional[str]) -> List[Invariant]:
        """Get invariants related to an entity."""
        if not entity or not self.behavior_model.invariants:
            return []

        return [
            inv for inv in self.behavior_model.invariants
            if inv.entity.lower() == entity.lower()
        ]

    def generate_all_methods(self) -> List[GeneratedMethod]:
        """Generate methods for all flows."""
        methods = []
        for flow in self.behavior_model.flows:
            method = self.generate_flow_method(flow)
            methods.append(method)
        return methods

    def generate_service_additions(self, entity_name: str) -> str:
        """
        Generate additional methods to add to an entity's service.

        Returns Python code for methods related to the entity.
        """
        methods = self.generate_all_methods()

        # Filter methods related to this entity
        entity_methods = [
            m for m in methods
            if m.target_entity and m.target_entity.lower() == entity_name.lower()
        ]

        if not entity_methods:
            return ""

        code_parts = []
        code_parts.append(f"\n    # === Generated from BehaviorModelIR ===")

        for method in entity_methods:
            code_parts.append(method.code)
            code_parts.append("")

        return "\n".join(code_parts)

    def generate_standalone_service(self) -> str:
        """
        Generate a standalone service with all flow methods.

        For flows not tied to a specific entity.
        """
        methods = self.generate_all_methods()

        # Filter methods without specific entity
        standalone_methods = [m for m in methods if not m.target_entity]

        if not standalone_methods:
            return ""

        lines = []
        lines.append('"""')
        lines.append('Business Flow Service')
        lines.append('')
        lines.append('Generated from BehaviorModelIR flows.')
        lines.append('"""')
        lines.append('from typing import Any, Dict, Optional')
        lines.append('from sqlalchemy.ext.asyncio import AsyncSession')
        lines.append('import logging')
        lines.append('')
        lines.append('logger = logging.getLogger(__name__)')
        lines.append('')
        lines.append('')
        lines.append('class BusinessFlowService:')
        lines.append('    """Service for business flows not tied to specific entities."""')
        lines.append('')
        lines.append('    def __init__(self, db: AsyncSession):')
        lines.append('        self.db = db')
        lines.append('')

        for method in standalone_methods:
            lines.append(method.code)
            lines.append('')

        return "\n".join(lines)


class ServiceEnhancer:
    """
    Enhance existing service files with methods from BehaviorModelIR.

    Reads existing service, adds new methods from flows.
    """

    def __init__(self, generator: ServiceGeneratorFromIR):
        self.generator = generator

    def enhance_service_file(
        self,
        service_path: Path,
        entity_name: str
    ) -> Optional[str]:
        """
        Add flow-based methods to existing service file.

        Returns enhanced code or None if no additions.
        """
        if not service_path.exists():
            return None

        additions = self.generator.generate_service_additions(entity_name)
        if not additions:
            return None

        existing_code = service_path.read_text()

        # Find last method or end of class
        # Insert before final closing of class
        insert_marker = "\n# === Generated from BehaviorModelIR ==="

        if insert_marker in existing_code:
            # Already has generated methods - skip
            return None

        # Find insertion point (before last line of class)
        lines = existing_code.split('\n')

        # Find class definition end by looking for unindented lines after class
        in_class = False
        insert_idx = len(lines) - 1

        for i, line in enumerate(lines):
            if line.startswith('class ') and 'Service' in line:
                in_class = True
            elif in_class and line and not line.startswith(' ') and not line.startswith('\t'):
                insert_idx = i
                break

        # Insert additions before end
        lines.insert(insert_idx, additions)

        return '\n'.join(lines)


def generate_services_from_ir(
    app_ir: ApplicationIR,
    output_dir: Path
) -> Dict[str, Path]:
    """
    Generate or enhance services from ApplicationIR.

    Args:
        app_ir: The ApplicationIR containing behavior model
        output_dir: Directory where services should be generated/enhanced

    Returns:
        Dict mapping entity names to generated/enhanced file paths
    """
    generated_files = {}

    if not app_ir.behavior_model:
        return generated_files

    generator = ServiceGeneratorFromIR(
        behavior_model=app_ir.behavior_model,
        domain_model=app_ir.domain_model
    )

    # Generate methods for all flows
    methods = generator.generate_all_methods()

    if not methods:
        return generated_files

    services_dir = output_dir / "src" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    # Group methods by entity
    entity_methods: Dict[str, List[GeneratedMethod]] = {}
    standalone_methods: List[GeneratedMethod] = []

    for method in methods:
        if method.target_entity:
            entity_name = method.target_entity
            if entity_name not in entity_methods:
                entity_methods[entity_name] = []
            entity_methods[entity_name].append(method)
        else:
            standalone_methods.append(method)

    # Generate/enhance entity services
    for entity_name, entity_method_list in entity_methods.items():
        service_name = f"{entity_name.lower()}_service.py"
        service_path = services_dir / service_name

        additions = generator.generate_service_additions(entity_name)
        if additions:
            # Create a file with the additions
            additions_file = services_dir / f"{entity_name.lower()}_flow_methods.py"
            additions_file.write_text(f'''"""
Flow methods for {entity_name}Service.

Generated from BehaviorModelIR.
Add these methods to {service_name}.
"""
from typing import Any

# Methods to add to {entity_name}Service:
{additions}
''')
            generated_files[f"{entity_name}_flows"] = additions_file

    # Generate standalone service if needed
    if standalone_methods:
        standalone_code = generator.generate_standalone_service()
        if standalone_code:
            standalone_path = services_dir / "business_flow_service.py"
            standalone_path.write_text(standalone_code)
            generated_files["business_flows"] = standalone_path

    return generated_files


def get_flow_coverage_report(
    app_ir: ApplicationIR,
    services_dir: Path
) -> Dict[str, Any]:
    """
    Check which flows from IR are implemented in services.

    Returns coverage report.
    """
    report = {
        "total_flows": 0,
        "implemented_flows": 0,
        "missing_flows": [],
        "coverage_percentage": 0.0
    }

    if not app_ir.behavior_model or not app_ir.behavior_model.flows:
        return report

    flows = app_ir.behavior_model.flows
    report["total_flows"] = len(flows)

    # Read all service files
    service_content = ""
    if services_dir.exists():
        for service_file in services_dir.glob("*.py"):
            service_content += service_file.read_text().lower()

    # Check each flow
    implemented = 0
    missing = []

    for flow in flows:
        method_name = ServiceGeneratorFromIR(
            app_ir.behavior_model
        )._normalize_method_name(flow.name)

        # Check if method exists in services
        if f"def {method_name}" in service_content or f"async def {method_name}" in service_content:
            implemented += 1
        else:
            missing.append({
                "flow_name": flow.name,
                "method_name": method_name,
                "type": flow.type.value
            })

    report["implemented_flows"] = implemented
    report["missing_flows"] = missing
    report["coverage_percentage"] = (
        (implemented / len(flows) * 100) if flows else 0.0
    )

    return report
