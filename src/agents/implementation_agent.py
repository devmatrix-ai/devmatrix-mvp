"""
Implementation Agent

Specialized agent for code generation tasks in multi-agent workflows.
Generates Python code based on task specifications and writes artifacts to SharedScratchpad.

Now enhanced with RAG (Retrieval-Augmented Generation) to use similar code examples
for improved accuracy and consistency.
"""

from typing import Dict, Any, Optional, Set
from src.llm.anthropic_client import AnthropicClient
from src.tools.workspace_manager import WorkspaceManager
from src.state.shared_scratchpad import SharedScratchpad, Artifact, ArtifactType
from src.agents.agent_registry import AgentCapability
from src.rag import (
    create_embedding_model,
    create_vector_store,
    create_retriever,
    create_context_builder,
    create_feedback_service,
    RetrievalStrategy,
    ContextTemplate,
)
from src.observability import get_logger


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


IMPORTANT: Always respond in English, regardless of the input language.
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

    def __init__(self, api_key: Optional[str] = None, enable_rag: bool = True):
        """
        Initialize implementation agent with optional RAG support.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
            enable_rag: Whether to enable RAG for enhanced code generation
        """
        # Use Claude Sonnet 4.5 for fast code generation
        self.llm = AnthropicClient(api_key=api_key, model="claude-haiku-4-5-20251001")
        self.name = "ImplementationAgent"
        self.logger = get_logger("agents.implementation")

        # Initialize RAG components if enabled
        self.rag_enabled = enable_rag
        if self.rag_enabled:
            try:
                # Create RAG pipeline
                embedding_model = create_embedding_model()
                vector_store = create_vector_store(embedding_model)
                self.retriever = create_retriever(
                    vector_store,
                    strategy=RetrievalStrategy.MMR,  # Use MMR for diversity
                    top_k=3  # Retrieve top 3 examples
                )
                self.context_builder = create_context_builder(
                    template=ContextTemplate.DETAILED  # Detailed context for LLM
                )
                self.feedback_service = create_feedback_service(
                    vector_store,
                    enabled=True
                )

                self.logger.info(
                    "RAG pipeline initialized successfully",
                    retriever_strategy="MMR",
                    top_k=3
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to initialize RAG pipeline, continuing without RAG",
                    error=str(e),
                    error_type=type(e).__name__
                )
                self.rag_enabled = False

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

            # Extract metadata for RAG
            # Infer language from file extensions
            language = "python"  # Default
            if files:
                first_file = files[0]
                if first_file.endswith(".js") or first_file.endswith(".ts"):
                    language = "javascript"
                elif first_file.endswith(".java"):
                    language = "java"
                elif first_file.endswith(".go"):
                    language = "go"
                # Add more as needed

            rag_metadata = {
                "language": language,
                "task_type": task.get("task_type", "general"),
                "workspace_id": workspace_id,
                "task_id": task_id,
            }

            # Generate code with optional RAG enhancement
            code = self._generate_code(description, files, dependency_context, rag_metadata)

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
        dependency_context: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate Python code using LLM with optional RAG enhancement.

        Args:
            description: Task description
            files: Target files
            dependency_context: Context from dependency artifacts
            metadata: Optional metadata for RAG retrieval (language, project_id, etc.)

        Returns:
            Generated Python code
        """
        rag_context = None

        # Try to retrieve similar code examples if RAG is enabled
        if self.rag_enabled:
            try:
                self.logger.debug(
                    "Attempting RAG retrieval",
                    query=description[:100],
                    metadata=metadata
                )

                # Retrieve similar examples
                results = self.retriever.retrieve(query=description)

                if results:
                    # Build RAG context
                    rag_context = self.context_builder.build_context(
                        query=description,
                        results=results
                    )

                    self.logger.info(
                        "RAG context built successfully",
                        num_examples=len(results),
                        avg_similarity=sum(r.similarity for r in results) / len(results),
                        context_length=len(rag_context)
                    )
                else:
                    self.logger.debug("No similar examples found in vector store")

            except Exception as e:
                self.logger.warning(
                    "Failed to retrieve RAG context, continuing without it",
                    error=str(e),
                    error_type=type(e).__name__
                )

        # Build the code generation prompt
        code_prompt = self.CODE_GENERATION_PROMPT.format(
            description=description,
            files=", ".join(files),
            dependencies=dependency_context or "None"
        )

        # Enhance system prompt with RAG context if available
        system_prompt = self.SYSTEM_PROMPT
        if rag_context:
            system_prompt += f"\n\n# Similar Code Examples\n\nHere are similar code examples from the codebase that may help guide your implementation:\n\n{rag_context}\n\nUse these examples as reference, but adapt them to the specific requirements of this task."

        response = self.llm.generate(
            messages=[{"role": "user", "content": code_prompt}],
            system=system_prompt,
            temperature=0.0,  # Deterministic mode
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

    def record_code_approval(
        self,
        code: str,
        task_id: str,
        workspace_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Record approved code in RAG system for future retrieval.

        This method should be called when code is verified/approved to
        automatically index it for future similar tasks.

        Args:
            code: Approved code content
            task_id: Task identifier
            workspace_id: Workspace identifier
            metadata: Optional metadata (project_id, file_path, language, task_type, etc.)

        Returns:
            Feedback ID if recorded successfully, None otherwise
        """
        if not self.rag_enabled:
            self.logger.debug(
                "RAG not enabled, skipping code approval recording",
                task_id=task_id
            )
            return None

        try:
            # Prepare metadata
            approval_metadata = metadata or {}
            approval_metadata.update({
                "task_id": task_id,
                "workspace_id": workspace_id,
                "agent": self.name
            })

            # Record approval through feedback service
            feedback_id = self.feedback_service.record_approval(
                code=code,
                metadata=approval_metadata,
                task_description=approval_metadata.get("task_description"),
                user_id=approval_metadata.get("user_id")
            )

            self.logger.info(
                "Code approval recorded successfully",
                feedback_id=feedback_id,
                task_id=task_id,
                code_length=len(code)
            )

            return feedback_id

        except Exception as e:
            self.logger.error(
                "Failed to record code approval",
                error=str(e),
                error_type=type(e).__name__,
                task_id=task_id
            )
            return None

    def __repr__(self) -> str:
        """String representation."""
        rag_status = "RAG enabled" if self.rag_enabled else "RAG disabled"
        return f"ImplementationAgent(name={self.name}, {rag_status})"
