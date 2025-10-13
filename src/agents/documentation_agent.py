"""
Documentation Agent

Specialized agent for documentation generation in multi-agent workflows.
Generates docstrings, README files, and API documentation from code.
"""

from typing import Dict, Any, Optional, Set
from pathlib import Path

from src.llm.anthropic_client import AnthropicClient
from src.tools.workspace_manager import WorkspaceManager
from src.state.shared_scratchpad import SharedScratchpad, Artifact, ArtifactType
from src.agents.agent_registry import AgentCapability


class DocumentationAgent:
    """
    Agent specialized in documentation generation.

    Capabilities:
    - API_DOCUMENTATION: Generate API reference documentation
    - USER_DOCUMENTATION: Generate user guides and tutorials
    - CODE_DOCUMENTATION: Generate docstrings and code comments

    Usage:
        agent = DocumentationAgent()

        task = {
            "id": "task_3",
            "description": "Generate docstrings for Calculator class",
            "task_type": "documentation",
            "dependencies": ["task_1"],
            "files": ["docs/api.md"]
        }

        context = {
            "workspace_id": "my-project",
            "scratchpad": scratchpad_instance
        }

        result = agent.execute(task, context)
    """

    SYSTEM_PROMPT = """You are an expert technical writer specializing in Python documentation.

Your role is to:
1. Generate clear, comprehensive documentation for Python code
2. Write Google-style docstrings for functions, classes, and modules
3. Create well-structured README files with examples
4. Follow documentation best practices
5. Make documentation accessible to developers of all levels

Guidelines:
- Use Google-style docstrings (Args:, Returns:, Raises:, Examples:)
- Include type hints in documentation
- Provide clear examples for complex functions
- Explain the "why" not just the "what"
- Use proper Markdown formatting
- Keep explanations concise but complete
- Add usage examples where appropriate
"""

    DOCSTRING_GENERATION_PROMPT = """Generate comprehensive documentation for this code.

Task Description: {description}

Code to Document:
```python
{code_to_document}
```

Target Documentation Files: {files}

Requirements:
- Add Google-style docstrings to all functions and classes
- Include Args, Returns, Raises, and Examples sections
- Add module-level docstring at the top
- Explain complex logic with inline comments
- Provide usage examples for main functions/classes
- Use proper type hints in docstring descriptions
- Keep explanations clear and concise

Output the COMPLETE code with added documentation in this format:
```python
# Your documented code here
```

Do not include explanations outside the code block."""

    README_GENERATION_PROMPT = """Generate a comprehensive README.md file for this code.

Task Description: {description}

Code to Document:
```python
{code_to_document}
```

Requirements:
- Create a well-structured README.md
- Include: Title, Description, Installation, Usage, API Reference, Examples
- Add code examples showing how to use the main functionality
- Include any dependencies or requirements
- Add badges if appropriate (version, license, etc.)
- Use proper Markdown formatting with headers, code blocks, lists
- Make it beginner-friendly but comprehensive

Output ONLY the README content in Markdown format.

Do not include explanations outside the content."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize documentation agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        self.llm = AnthropicClient(api_key=api_key)
        self.name = "DocumentationAgent"

    def get_capabilities(self) -> Set[AgentCapability]:
        """Return agent capabilities."""
        return {
            AgentCapability.API_DOCUMENTATION,
            AgentCapability.USER_DOCUMENTATION,
            AgentCapability.CODE_DOCUMENTATION
        }

    def get_name(self) -> str:
        """Return agent name."""
        return self.name

    def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute documentation task.

        Args:
            task: Task dictionary with:
                - id: Task identifier
                - description: Task description
                - task_type: Type of task
                - dependencies: List of dependency task IDs
                - files: List of target documentation files
            context: Execution context with:
                - workspace_id: Workspace identifier
                - scratchpad: SharedScratchpad instance (optional)
                - doc_type: Type of documentation ("docstring" or "readme")

        Returns:
            Result dictionary with:
                - success: Boolean indicating success
                - output: Generated documentation or error message
                - artifacts: List of created artifact IDs
                - error: Error message if failed
        """
        task_id = task["id"]
        description = task["description"]
        files = task.get("files", ["docs/documentation.md"])
        dependencies = task.get("dependencies", [])

        workspace_id = context.get("workspace_id", "default")
        scratchpad = context.get("scratchpad")
        doc_type = context.get("doc_type", "docstring")  # "docstring" or "readme"

        try:
            # Mark task as started in scratchpad
            if scratchpad:
                scratchpad.mark_task_started(task_id, self.name)

            # Read code from dependency artifacts
            code_to_document = self._read_code_from_dependencies(
                dependencies,
                scratchpad
            ) if scratchpad else ""

            if not code_to_document:
                raise ValueError("No code found to document. Dependencies may be missing.")

            # Generate documentation based on type
            if doc_type == "readme":
                documentation = self._generate_readme(description, code_to_document, files)
            else:
                documentation = self._generate_docstrings(description, code_to_document, files)

            # Write documentation to workspace
            file_paths = self._write_to_workspace(workspace_id, files, documentation)

            # Write artifact to scratchpad
            artifact_ids = []
            if scratchpad:
                artifact = Artifact(
                    artifact_type=ArtifactType.DOCUMENTATION,
                    content=documentation,
                    created_by=self.name,
                    task_id=task_id,
                    metadata={
                        "files": file_paths,
                        "doc_type": doc_type,
                        "language": "python"
                    }
                )
                scratchpad.write_artifact(artifact)
                artifact_ids.append(artifact.id)

                # Mark task as completed
                scratchpad.mark_task_completed(task_id, self.name)

            return {
                "success": True,
                "output": documentation,
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

    def _generate_docstrings(
        self,
        description: str,
        code_to_document: str,
        files: list
    ) -> str:
        """
        Generate docstrings for code using LLM.

        Args:
            description: Task description
            code_to_document: Code to generate docstrings for
            files: Target documentation files

        Returns:
            Code with added docstrings
        """
        doc_prompt = self.DOCSTRING_GENERATION_PROMPT.format(
            description=description,
            code_to_document=code_to_document,
            files=", ".join(files)
        )

        response = self.llm.generate(
            messages=[{"role": "user", "content": doc_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096
        )

        # Extract code from markdown if present
        documentation = response['content']
        import re
        code_match = re.search(r'```python\n(.*?)\n```', documentation, re.DOTALL)
        if code_match:
            documentation = code_match.group(1)

        return documentation

    def _generate_readme(
        self,
        description: str,
        code_to_document: str,
        files: list
    ) -> str:
        """
        Generate README file using LLM.

        Args:
            description: Task description
            code_to_document: Code to generate README for
            files: Target README files

        Returns:
            Generated README content
        """
        readme_prompt = self.README_GENERATION_PROMPT.format(
            description=description,
            code_to_document=code_to_document
        )

        response = self.llm.generate(
            messages=[{"role": "user", "content": readme_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096
        )

        # Extract markdown content (might be wrapped in code blocks)
        documentation = response['content']
        import re

        # Try to extract from markdown code block
        markdown_match = re.search(r'```markdown\n(.*?)\n```', documentation, re.DOTALL)
        if markdown_match:
            documentation = markdown_match.group(1)
        else:
            # Try plain code block
            code_match = re.search(r'```\n(.*?)\n```', documentation, re.DOTALL)
            if code_match:
                documentation = code_match.group(1)

        return documentation

    def _read_code_from_dependencies(
        self,
        dependencies: list,
        scratchpad: SharedScratchpad
    ) -> str:
        """
        Read code from dependency task artifacts.

        Args:
            dependencies: List of dependency task IDs
            scratchpad: SharedScratchpad instance

        Returns:
            Code from dependency artifacts
        """
        if not dependencies:
            return ""

        code_parts = []
        for dep_task_id in dependencies:
            artifacts = scratchpad.read_artifacts(
                task_id=dep_task_id,
                artifact_type=ArtifactType.CODE
            )

            for artifact in artifacts:
                code_parts.append(artifact.content)

        return "\n\n".join(code_parts) if code_parts else ""

    def _write_to_workspace(
        self,
        workspace_id: str,
        files: list,
        documentation: str
    ) -> list:
        """
        Write generated documentation to workspace files.

        Args:
            workspace_id: Workspace identifier
            files: List of target documentation files
            documentation: Generated documentation

        Returns:
            List of written file paths
        """
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)

        # Create workspace if doesn't exist
        if not ws.base_path.exists():
            ws.create()

        file_paths = []
        for filename in files:
            # Handle nested paths (e.g., "docs/api/reference.md")
            if "/" in filename:
                parts = filename.split("/")
                parent_dirs = "/".join(parts[:-1])
                actual_filename = parts[-1]

                # Create nested directory structure
                ws.create_dir(parent_dirs)
                full_path = f"{parent_dirs}/{actual_filename}"
            else:
                full_path = filename

            # Write file
            file_path = ws.write_file(full_path, documentation)
            file_paths.append(str(file_path))

        return file_paths

    def __repr__(self) -> str:
        """String representation."""
        return f"DocumentationAgent(name={self.name})"
