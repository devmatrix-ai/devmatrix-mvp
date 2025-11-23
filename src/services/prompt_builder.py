"""
Prompt Builder.

Formalizes the construction of prompts for the LLM, ensuring reproducibility and versioning.
"""
from typing import List, Optional, Dict, Any
from src.cognitive.ir.application_ir import ApplicationIR

class PromptBuilder:
    """
    Builder for constructing LLM prompts in a structured, reproducible way.
    """

    def __init__(self):
        self.system_role: str = "You are an expert software engineer."
        self.context_parts: List[str] = []
        self.task_instruction: str = ""
        self.constraints: List[str] = []
        self.examples: List[str] = []

    def with_system_role(self, role: str) -> 'PromptBuilder':
        """Set the system role."""
        self.system_role = role
        return self

    def with_ir_summary(self, ir: ApplicationIR) -> 'PromptBuilder':
        """Add comprehensive ApplicationIR summary to context."""
        summary = [
            "## ARCHITECTURE CONTEXT (ApplicationIR)",
            f"**App Name**: {ir.name}",
            f"**Description**: {ir.description}",
            f"**Version**: {ir.version}",
            "",
            "### Domain Model",
        ]
        
        # Add entity details
        for entity in ir.domain_model.entities:
            summary.append(f"**Entity: {entity.name}**")
            summary.append(f"  - Description: {entity.description or 'N/A'}")
            summary.append(f"  - Attributes: {len(entity.attributes)}")
            for attr in entity.attributes[:5]:  # Show first 5 attributes
                required = "required" if not attr.is_nullable else "optional"
                unique = ", unique" if attr.is_unique else ""
                summary.append(f"    - {attr.name}: {attr.data_type.value} ({required}{unique})")
            if len(entity.attributes) > 5:
                summary.append(f"    - ... and {len(entity.attributes) - 5} more")
        
        summary.append("")
        summary.append("### API Model")
        summary.append(f"**Total Endpoints**: {len(ir.api_model.endpoints)}")
        
        # Group endpoints by entity
        endpoints_by_entity = {}
        for endpoint in ir.api_model.endpoints:
            # Extract entity from path (simple heuristic)
            path_parts = endpoint.path.strip("/").split("/")
            entity_name = path_parts[-1] if path_parts else "unknown"
            if entity_name not in endpoints_by_entity:
                endpoints_by_entity[entity_name] = []
            endpoints_by_entity[entity_name].append(endpoint)
        
        for entity_name, endpoints in endpoints_by_entity.items():
            summary.append(f"**{entity_name.capitalize()}**:")
            for ep in endpoints[:3]:  # Show first 3 endpoints per entity
                summary.append(f"  - {ep.method.value} {ep.path}")
            if len(endpoints) > 3:
                summary.append(f"  - ... and {len(endpoints) - 3} more")
        
        summary.append("")
        summary.append("### Infrastructure")
        summary.append(f"**Database**: {ir.infrastructure_model.database.type.value}")
        summary.append(f"  - Host: {ir.infrastructure_model.database.host}")
        summary.append(f"  - Port: {ir.infrastructure_model.database.port}")
        summary.append(f"  - Name: {ir.infrastructure_model.database.name}")
        
        if ir.infrastructure_model.vector_db:
            summary.append(f"**Vector DB**: {ir.infrastructure_model.vector_db.type.value}")
        
        if ir.infrastructure_model.graph_db:
            summary.append(f"**Graph DB**: {ir.infrastructure_model.graph_db.type.value}")
        
        obs = ir.infrastructure_model.observability
        summary.append(f"**Observability**:")
        summary.append(f"  - Logging: {'Enabled' if obs.logging_enabled else 'Disabled'}")
        summary.append(f"  - Metrics: {'Enabled' if obs.metrics_enabled else 'Disabled'}")
        summary.append(f"  - Tracing: {'Enabled' if obs.tracing_enabled else 'Disabled'}")
        
        summary.append("")
        summary.append("### Behavior Model")
        summary.append(f"**Flows**: {len(ir.behavior_model.flows)} defined")
        if ir.behavior_model.flows:
            for flow in ir.behavior_model.flows[:2]:  # Show first 2 flows
                summary.append(f"  - {flow.name} ({flow.flow_type.value})")
        
        summary.append(f"**Invariants**: {len(ir.behavior_model.invariants)} defined")
        if ir.behavior_model.invariants:
            for inv in ir.behavior_model.invariants[:2]:  # Show first 2 invariants
                summary.append(f"  - {inv.name}: {inv.condition}")
        
        summary.append("")
        summary.append("### Validation Model")
        summary.append(f"**Rules**: {len(ir.validation_model.rules)} defined")
        if ir.validation_model.rules:
            for rule in ir.validation_model.rules[:3]:  # Show first 3 rules
                summary.append(f"  - {rule.field}: {rule.validation_type.value}")
        
        summary.append(f"**Test Cases**: {len(ir.validation_model.test_cases)} defined")
            
        self.context_parts.append("\n".join(summary))
        return self

    def with_rag_results(self, results: List[Any]) -> 'PromptBuilder':
        """Add RAG retrieval results to context."""
        if not results:
            return self
            
        rag_context = ["\n## REFERENCE EXAMPLES (Use these patterns if relevant):"]
        for i, result in enumerate(results, 1):
            rag_context.append(f"\n### Example {i} (Source: {result.source})")
            # Truncate content if too long
            content = result.content[:1500] + "..." if len(result.content) > 1500 else result.content
            rag_context.append(f"```python\n{content}\n```")
            
        self.context_parts.append("\n".join(rag_context))
        return self

    def with_task_instruction(self, instruction: str) -> 'PromptBuilder':
        """Set the main task instruction."""
        self.task_instruction = instruction
        return self
        
    def add_constraint(self, constraint: str) -> 'PromptBuilder':
        """Add a constraint."""
        self.constraints.append(constraint)
        return self

    def build(self) -> str:
        """Construct the final prompt string."""
        parts = []
        
        # 1. Context
        if self.context_parts:
            parts.extend(self.context_parts)
            parts.append("")
            
        # 2. Task
        if self.task_instruction:
            parts.append("## TASK")
            parts.append(self.task_instruction)
            parts.append("")
            
        # 3. Constraints
        if self.constraints:
            parts.append("## CONSTRAINTS")
            for c in self.constraints:
                parts.append(f"- {c}")
                
        return "\n".join(parts)
