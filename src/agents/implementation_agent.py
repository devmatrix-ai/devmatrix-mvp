"""
Implementation Agent

Specialized agent for code generation tasks in multi-agent workflows.
Generates Python code based on task specifications and writes artifacts to SharedScratchpad.
"""

from typing import Dict, Any, Optional, Set
from src.llm.anthropic_client import AnthropicClient
from src.tools.workspace_manager import WorkspaceManager
from src.state.shared_scratchpad import SharedScratchpad, Artifact, ArtifactType
from src.agents.agent_registry import AgentCapability


class ImplementationAgent:
    """
    Agent specialized in Python code implementation.

    Capabilities:
    - CODE_GENERATION: Generate Python functions, classes, modules
    - API_DESIGN: Design clean APIs and interfaces
    - REFACTORING: Improve and refactor existing code

    Usage:
        agent = ImplementationAgent()

        task = {
            "id": "task_1",
            "description": "Create a User model with validation",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["models/user.py"]
        }

        context = {
            "workspace_id": "my-project",
            "scratchpad": scratchpad_instance
        }

        result = agent.execute(task, context)
    """

    SYSTEM_PROMPT = """You are an expert Python software engineer specializing in clean, production-ready code.

Your role is to:
1. Generate high-quality Python code based on task specifications
2. Follow Python best practices (PEP 8, type hints, docstrings)
3. Write clean, maintainable, well-documented code
4. Include proper error handling and edge case management
5. Create modular, testable code

Guidelines:
- Always include comprehensive docstrings
- Use type hints for all function parameters and return values
- Handle errors gracefully with appropriate exceptions
- Write clear, self-documenting code with meaningful names
- Follow SOLID principles and design patterns where appropriate
- Keep functions focused and cohesive
- Add inline comments for complex logic only
"""

    CODE_GENERATION_PROMPT = """Generate Python code for this task.

Task Description: {description}

Target Files: {files}

Dependencies (completed tasks you can reference):
{dependencies}

Requirements:
- Write complete, working Python code
- Include all necessary imports at the top
- Add comprehensive docstrings (Google style)
- Use type hints for all functions/methods
- Include error handling where appropriate
- Follow PEP 8 style guidelines
- Make code modular and testable

Output ONLY the Python code in this format:
```python
# Your code here
```

Do not include explanations outside the code block."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize implementation agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        # Use Claude Sonnet 4.5 for fast code generation
        self.llm = AnthropicClient(api_key=api_key, model="claude-sonnet-4-5-20250929")
        self.name = "ImplementationAgent"

    def get_capabilities(self) -> Set[AgentCapability]:
        """Return agent capabilities."""
        return {
            AgentCapability.CODE_GENERATION,
            AgentCapability.API_DESIGN,
            AgentCapability.REFACTORING
        }

    def get_name(self) -> str:
        """Return agent name."""
        return self.name

    def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute implementation task.

        Args:
            task: Task dictionary with:
                - id: Task identifier
                - description: Task description
                - task_type: Type of task
                - dependencies: List of dependency task IDs
                - files: List of target files
            context: Execution context with:
                - workspace_id: Workspace identifier
                - scratchpad: SharedScratchpad instance (optional)
                - dependency_outputs: Outputs from dependency tasks (optional)

        Returns:
            Result dictionary with:
                - success: Boolean indicating success
                - output: Generated code or error message
                - artifacts: List of created artifact IDs
                - error: Error message if failed
        """
        task_id = task["id"]
        description = task["description"]
        files = task.get("files", ["main.py"])
        dependencies = task.get("dependencies", [])

        workspace_id = context.get("workspace_id", "default")
        scratchpad = context.get("scratchpad")

        try:
            # Mark task as started in scratchpad
            if scratchpad:
                scratchpad.mark_task_started(task_id, self.name)

            # Read dependency artifacts if any
            dependency_context = self._read_dependency_artifacts(
                dependencies,
                scratchpad
            ) if scratchpad else ""

            # Generate code
            code = self._generate_code(description, files, dependency_context)

            # Write code to workspace
            file_paths = self._write_to_workspace(workspace_id, files, code)

            # Write artifact to scratchpad
            artifact_ids = []
            if scratchpad:
                artifact = Artifact(
                    artifact_type=ArtifactType.CODE,
                    content=code,
                    created_by=self.name,
                    task_id=task_id,
                    metadata={
                        "files": file_paths,
                        "language": "python"
                    }
                )
                scratchpad.write_artifact(artifact)
                artifact_ids.append(artifact.id)

                # Mark task as completed
                scratchpad.mark_task_completed(task_id, self.name)

            return {
                "success": True,
                "output": code,
                "artifacts": artifact_ids,
                "file_paths": file_paths,
                "error": None
            }

        except Exception as e:
            # Mark task as failed in scratchpad
            if scratchpad:
                scratchpad.mark_task_failed(task_id, self.name, str(e))

            return {
                "success": False,
                "output": None,
                "artifacts": [],
                "file_paths": [],
                "error": str(e)
            }

    def _generate_code(
        self,
        description: str,
        files: list,
        dependency_context: str
    ) -> str:
        """
        Generate Python code using LLM.

        Args:
            description: Task description
            files: Target files
            dependency_context: Context from dependency artifacts

        Returns:
            Generated Python code
        """
        code_prompt = self.CODE_GENERATION_PROMPT.format(
            description=description,
            files=", ".join(files),
            dependencies=dependency_context or "None"
        )

        response = self.llm.generate(
            messages=[{"role": "user", "content": code_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096
        )

        # Extract code from markdown if present
        code = response['content']
        import re
        code_match = re.search(r'```python\n(.*?)\n```', code, re.DOTALL)
        if code_match:
            code = code_match.group(1)

        return code

    def _read_dependency_artifacts(
        self,
        dependencies: list,
        scratchpad: SharedScratchpad
    ) -> str:
        """
        Read artifacts from dependency tasks.

        Args:
            dependencies: List of dependency task IDs
            scratchpad: SharedScratchpad instance

        Returns:
            Formatted context string from dependency artifacts
        """
        if not dependencies:
            return ""

        context_parts = []
        for dep_task_id in dependencies:
            artifacts = scratchpad.read_artifacts(task_id=dep_task_id)

            for artifact in artifacts:
                if artifact.type == "code":
                    context_parts.append(
                        f"Task {dep_task_id} code:\n```python\n{artifact.content}\n```"
                    )
                elif artifact.type == "analysis":
                    context_parts.append(
                        f"Task {dep_task_id} analysis:\n{artifact.content}"
                    )

        return "\n\n".join(context_parts) if context_parts else ""

    def _write_to_workspace(
        self,
        workspace_id: str,
        files: list,
        code: str
    ) -> list:
        """
        Write generated code to workspace files.

        Args:
            workspace_id: Workspace identifier
            files: List of target files
            code: Generated code

        Returns:
            List of written file paths
        """
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)

        # Create workspace if doesn't exist
        if not ws.base_path.exists():
            ws.create()

        file_paths = []
        for filename in files:
            # Write file (WorkspaceManager handles parent directory creation)
            file_path = ws.write_file(filename, code)
            file_paths.append(str(file_path))

        return file_paths

    def __repr__(self) -> str:
        """String representation."""
        return f"ImplementationAgent(name={self.name})"
