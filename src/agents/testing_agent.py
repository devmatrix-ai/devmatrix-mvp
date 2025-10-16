"""
Testing Agent

Specialized agent for test generation and execution in multi-agent workflows.
Generates pytest tests and executes them to verify code correctness.
"""

import subprocess
from typing import Dict, Any, Optional, Set
from pathlib import Path

from src.llm.anthropic_client import AnthropicClient
from src.tools.workspace_manager import WorkspaceManager
from src.state.shared_scratchpad import SharedScratchpad, Artifact, ArtifactType
from src.agents.agent_registry import AgentCapability


class TestingAgent:
    """
    Agent specialized in test generation and execution.

    Capabilities:
    - UNIT_TESTING: Generate and run unit tests
    - INTEGRATION_TESTING: Generate and run integration tests
    - E2E_TESTING: Generate and run end-to-end tests

    Usage:
        agent = TestingAgent()

        task = {
            "id": "task_2",
            "description": "Create tests for User model",
            "task_type": "testing",
            "dependencies": ["task_1"],
            "files": ["tests/test_user.py"]
        }

        context = {
            "workspace_id": "my-project",
            "scratchpad": scratchpad_instance
        }

        result = agent.execute(task, context)
    """

    SYSTEM_PROMPT = """You are an expert Python test engineer specializing in pytest.

Your role is to:
1. Generate comprehensive pytest tests for Python code
2. Follow pytest best practices and conventions
3. Write clear, maintainable, well-documented tests
4. Cover edge cases, error conditions, and happy paths
5. Use appropriate pytest features (fixtures, parametrize, markers)
6. Create isolated, independent, repeatable tests

Guidelines:
- Use descriptive test names: test_<function>_<scenario>_<expected>
- Include docstrings explaining what each test verifies
- Use pytest fixtures for setup/teardown
- Test one thing per test function
- Use parametrize for multiple test cases
- Mock external dependencies appropriately
- Aim for high code coverage
- Keep tests fast and independent
"""

    TEST_GENERATION_PROMPT = """Generate pytest tests for this code.

Task Description: {description}

Code to Test:
```python
{code_to_test}
```

Target Test Files: {files}

Requirements:
- Write complete, working pytest tests
- Include all necessary imports
- Add comprehensive docstrings for each test
- Cover normal cases, edge cases, and error conditions
- Use pytest fixtures where appropriate
- Use parametrize for multiple test cases
- Mock external dependencies if needed
- Follow pytest naming conventions (test_*)

Output ONLY the test code in this format:
```python
# Your test code here
```

Do not include explanations outside the code block."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize testing agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        # Use Claude Sonnet 4.5 for fast test generation
        self.llm = AnthropicClient(api_key=api_key, model="claude-sonnet-4-5-20250929")
        self.name = "TestingAgent"

    def get_capabilities(self) -> Set[AgentCapability]:
        """Return agent capabilities."""
        return {
            AgentCapability.UNIT_TESTING,
            AgentCapability.INTEGRATION_TESTING,
            AgentCapability.E2E_TESTING
        }

    def get_name(self) -> str:
        """Return agent name."""
        return self.name

    def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute testing task.

        Args:
            task: Task dictionary with:
                - id: Task identifier
                - description: Task description
                - task_type: Type of task
                - dependencies: List of dependency task IDs
                - files: List of target test files
            context: Execution context with:
                - workspace_id: Workspace identifier
                - scratchpad: SharedScratchpad instance (optional)
                - run_tests: Whether to execute tests (default: True)

        Returns:
            Result dictionary with:
                - success: Boolean indicating success
                - output: Generated tests or error message
                - artifacts: List of created artifact IDs
                - test_results: Results from test execution
                - error: Error message if failed
        """
        task_id = task["id"]
        description = task["description"]
        files = task.get("files", ["tests/test_generated.py"])
        dependencies = task.get("dependencies", [])

        workspace_id = context.get("workspace_id", "default")
        scratchpad = context.get("scratchpad")
        run_tests = context.get("run_tests", True)

        try:
            # Mark task as started in scratchpad
            if scratchpad:
                scratchpad.mark_task_started(task_id, self.name)

            # Read code from dependency artifacts (scratchpad) or outputs (workspace)
            if scratchpad:
                code_to_test = self._read_code_from_dependencies(dependencies, scratchpad)
            else:
                # Fallback: read from dependency outputs
                code_to_test = self._read_code_from_workspace(
                    workspace_id,
                    dependencies,
                    context.get("dependency_outputs", {})
                )

            if not code_to_test:
                raise ValueError("No code found to test. Dependencies may be missing.")

            # Generate test code
            test_code = self._generate_tests(description, code_to_test, files)

            # Write tests to workspace
            file_paths = self._write_to_workspace(workspace_id, files, test_code)

            # Execute tests if requested
            test_results = None
            if run_tests:
                test_results = self._run_tests(workspace_id, file_paths)

            # Write artifacts to scratchpad
            artifact_ids = []
            if scratchpad:
                # Write test artifact
                test_artifact = Artifact(
                    artifact_type=ArtifactType.TEST,
                    content=test_code,
                    created_by=self.name,
                    task_id=task_id,
                    metadata={
                        "files": file_paths,
                        "language": "python",
                        "framework": "pytest"
                    }
                )
                scratchpad.write_artifact(test_artifact)
                artifact_ids.append(test_artifact.id)

                # Write test results artifact if tests were run
                if test_results:
                    result_artifact = Artifact(
                        artifact_type=ArtifactType.RESULT,
                        content=test_results,
                        created_by=self.name,
                        task_id=task_id,
                        metadata={
                            "type": "test_execution",
                            "passed": test_results.get("passed", False)
                        }
                    )
                    scratchpad.write_artifact(result_artifact)
                    artifact_ids.append(result_artifact.id)

                # Mark task as completed
                scratchpad.mark_task_completed(task_id, self.name)

            return {
                "success": True,
                "output": test_code,
                "artifacts": artifact_ids,
                "file_paths": file_paths,
                "test_results": test_results,
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
                "test_results": None,
                "error": str(e)
            }

    def _generate_tests(
        self,
        description: str,
        code_to_test: str,
        files: list
    ) -> str:
        """
        Generate pytest tests using LLM.

        Args:
            description: Task description
            code_to_test: Code to generate tests for
            files: Target test files

        Returns:
            Generated pytest code
        """
        test_prompt = self.TEST_GENERATION_PROMPT.format(
            description=description,
            code_to_test=code_to_test,
            files=", ".join(files)
        )

        response = self.llm.generate(
            messages=[{"role": "user", "content": test_prompt}],
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

    def _read_code_from_workspace(
        self,
        workspace_id: str,
        dependencies: list,
        dependency_outputs: Dict[str, Any]
    ) -> str:
        """
        Read code from workspace files (fallback when SharedScratchpad unavailable).

        Args:
            workspace_id: Workspace identifier
            dependencies: List of dependency task IDs
            dependency_outputs: Outputs from dependency tasks

        Returns:
            Code from workspace files
        """
        if not dependencies:
            return ""

        code_parts = []
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)

        for dep_task_id in dependencies:
            # Get file paths from dependency output
            dep_output = dependency_outputs.get(dep_task_id, {})
            file_paths = dep_output.get("file_paths", [])

            for file_path in file_paths:
                try:
                    # Read file from workspace
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists():
                        with open(file_path_obj, 'r') as f:
                            code_parts.append(f.read())
                except Exception as e:
                    # Skip files that can't be read
                    continue

        return "\n\n".join(code_parts) if code_parts else ""

    def _write_to_workspace(
        self,
        workspace_id: str,
        files: list,
        test_code: str
    ) -> list:
        """
        Write generated tests to workspace files.

        Args:
            workspace_id: Workspace identifier
            files: List of target test files
            test_code: Generated test code

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
            file_path = ws.write_file(filename, test_code)
            file_paths.append(str(file_path))

        return file_paths

    def _run_tests(
        self,
        workspace_id: str,
        test_files: list
    ) -> Dict[str, Any]:
        """
        Execute pytest tests.

        Args:
            workspace_id: Workspace identifier
            test_files: List of test file paths

        Returns:
            Dictionary with test results:
                - passed: Boolean indicating if all tests passed
                - exit_code: Pytest exit code
                - output: Test execution output
                - num_tests: Number of tests run
        """
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)
        workspace_dir = str(ws.base_path)

        try:
            # Run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse output to extract test count
            output = result.stdout + result.stderr
            num_tests = self._parse_test_count(output)

            return {
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "output": output,
                "num_tests": num_tests
            }

        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "exit_code": -1,
                "output": "Test execution timed out after 30 seconds",
                "num_tests": 0
            }
        except Exception as e:
            return {
                "passed": False,
                "exit_code": -1,
                "output": f"Error running tests: {str(e)}",
                "num_tests": 0
            }

    def _parse_test_count(self, output: str) -> int:
        """
        Parse number of tests from pytest output.

        Args:
            output: Pytest output

        Returns:
            Number of tests run
        """
        import re

        # Look for patterns like "5 passed" or "3 failed, 2 passed"
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0

        return passed + failed

    def __repr__(self) -> str:
        """String representation."""
        return f"TestingAgent(name={self.name})"
