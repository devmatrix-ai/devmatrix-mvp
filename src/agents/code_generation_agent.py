"""
Code Generation Agent

AI agent that generates Python code with human-in-loop approval.
Extends PlanningAgent to include code generation, review, and approval workflow.
"""

from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from src.llm.anthropic_client import AnthropicClient
from src.tools.workspace_manager import WorkspaceManager
from src.tools.git_operations import GitOperations
from src.state.postgres_manager import PostgresManager


# Message reducer
def add_messages(left: Sequence[dict], right: Sequence[dict]) -> Sequence[dict]:
    """Reducer to accumulate messages."""
    return list(left) + list(right)


class CodeGenState(TypedDict):
    """State for code generation agent."""
    user_request: str
    context: dict
    messages: Annotated[Sequence[dict], add_messages]

    # Planning
    plan: dict
    tasks: list

    # Code generation
    generated_code: str
    target_filename: str

    # Review
    review_feedback: str
    code_quality_score: float

    # Approval
    approval_status: Literal["pending", "approved", "rejected", "needs_modification"]
    user_feedback: str

    # File writing
    workspace_id: str
    file_written: bool
    file_path: str

    # Git integration
    git_enabled: bool
    git_commit_message: str
    git_commit_hash: str
    git_committed: bool

    # Decision logging
    decision_id: str


class CodeGenerationAgent:
    """
    Code generation agent with human-in-loop approval and Git integration.

    Workflow:
    1. Analyze user request
    2. Create implementation plan
    3. Generate Python code
    4. Self-review code quality
    5. Present for human approval
    6. Write to workspace if approved
    7. Auto-commit to Git with descriptive message
    8. Log decision to PostgreSQL

    Usage:
        agent = CodeGenerationAgent()
        result = agent.generate(
            user_request="Create a function to calculate fibonacci",
            workspace_id="my-workspace",
            git_enabled=True  # Enable auto-commit
        )
    """

    SYSTEM_PROMPT = """You are an expert Python software engineer.

Your role is to:
1. Understand user requirements clearly
2. Create detailed implementation plans
3. Generate clean, well-documented Python code
4. Follow Python best practices (PEP 8, type hints, docstrings)
5. Include error handling where appropriate
6. Write production-ready code

Guidelines:
- Always include docstrings for functions and classes
- Use type hints for function parameters and return values
- Handle edge cases and errors gracefully
- Write clean, readable code with clear variable names
- Follow PEP 8 style guidelines
- Add comments for complex logic
"""

    CODE_GENERATION_PROMPT = """Based on this implementation plan, generate complete Python code.

Plan:
{plan}

Requirements:
- Write complete, working Python code
- Include all necessary imports
- Add comprehensive docstrings
- Use type hints
- Include error handling
- Follow PEP 8 standards

Generate ONLY the Python code, no explanations. Output format:
```python
# Your code here
```
"""

    REVIEW_PROMPT = """Review this Python code for quality and correctness.

Code:
```python
{code}
```

Analyze:
1. Correctness: Does it work as intended?
2. Code quality: Is it clean and maintainable?
3. Best practices: Follows Python conventions?
4. Error handling: Handles edge cases?
5. Documentation: Clear docstrings?

Provide:
- Quality score (0-10)
- Brief feedback (2-3 sentences)

Format:
Score: X/10
Feedback: [your feedback]
"""

    COMMIT_MESSAGE_PROMPT = """Generate a concise, descriptive Git commit message for this code.

User Request: {request}
Filename: {filename}
Code Summary: {summary}

Follow conventional commit format:
- feat: new feature
- fix: bug fix
- refactor: code refactoring
- docs: documentation
- test: testing

Generate ONLY the commit message (one line, max 72 chars). Example:
feat: add fibonacci calculator function"""

    def __init__(self, api_key: str = None):
        """
        Initialize code generation agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        self.llm = AnthropicClient(api_key=api_key)
        self.console = Console()
        self.graph = self._build_graph()
        self.postgres = PostgresManager()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow with approval gates and Git integration."""
        workflow = StateGraph(CodeGenState)

        # Add nodes
        workflow.add_node("analyze", self._analyze_request)
        workflow.add_node("plan", self._create_plan)
        workflow.add_node("generate_code", self._generate_code)
        workflow.add_node("review_code", self._review_code)
        workflow.add_node("human_approval", self._human_approval)
        workflow.add_node("write_file", self._write_file)
        workflow.add_node("git_commit", self._git_commit)
        workflow.add_node("log_decision", self._log_decision)

        # Define edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "plan")
        workflow.add_edge("plan", "generate_code")
        workflow.add_edge("generate_code", "review_code")
        workflow.add_edge("review_code", "human_approval")

        # Conditional edges based on approval
        workflow.add_conditional_edges(
            "human_approval",
            self._route_approval,
            {
                "approved": "write_file",
                "rejected": "log_decision",
                "needs_modification": "generate_code"  # Loop back
            }
        )

        # After writing file, conditionally commit to git
        workflow.add_conditional_edges(
            "write_file",
            self._route_git,
            {
                "git_commit": "git_commit",
                "skip_git": "log_decision"
            }
        )

        workflow.add_edge("git_commit", "log_decision")
        workflow.add_edge("log_decision", END)

        return workflow.compile()

    def _analyze_request(self, state: CodeGenState) -> CodeGenState:
        """Analyze user request to extract requirements."""
        user_request = state["user_request"]

        analysis_prompt = f"""Analyze this code generation request:

Request: {user_request}

Extract:
1. What needs to be implemented? (function, class, module)
2. What are the inputs and outputs?
3. What are the key requirements?
4. What should the filename be? (e.g., calculator.py, utils.py)

Provide analysis in a structured format."""

        response = self.llm.generate(
            messages=[{"role": "user", "content": analysis_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.3
        )

        # Extract filename suggestion
        content = response['content']
        filename = "generated_code.py"  # default
        if ".py" in content.lower():
            # Try to extract filename from response
            import re
            match = re.search(r'(\w+\.py)', content)
            if match:
                filename = match.group(1)

        state["messages"].append({
            "role": "assistant",
            "content": f"Analysis: {response['content']}"
        })
        state["target_filename"] = filename

        return state

    def _create_plan(self, state: CodeGenState) -> CodeGenState:
        """Create detailed implementation plan."""
        user_request = state["user_request"]
        analysis = state["messages"][-1]["content"]

        planning_prompt = f"""Create a detailed implementation plan for this code.

Request: {user_request}
Analysis: {analysis}

Plan should include:
1. Function/class signatures
2. Key logic steps
3. Edge cases to handle
4. Imports needed

Be specific and actionable."""

        response = self.llm.generate(
            messages=[{"role": "user", "content": planning_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.5
        )

        state["plan"] = {"description": response['content']}
        state["messages"].append({
            "role": "assistant",
            "content": f"Plan: {response['content']}"
        })

        return state

    def _generate_code(self, state: CodeGenState) -> CodeGenState:
        """Generate Python code based on plan."""
        plan_text = state["plan"]["description"]
        user_feedback = state.get("user_feedback", "")

        # Include feedback if regenerating
        feedback_section = ""
        if user_feedback:
            feedback_section = f"\n\nUser Feedback:\n{user_feedback}\n\nPlease address this feedback in the updated code.\n"

        code_prompt = self.CODE_GENERATION_PROMPT.format(
            plan=plan_text
        ) + feedback_section

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

        state["generated_code"] = code
        state["messages"].append({
            "role": "assistant",
            "content": f"Generated code:\n```python\n{code}\n```"
        })

        return state

    def _review_code(self, state: CodeGenState) -> CodeGenState:
        """Self-review generated code."""
        code = state["generated_code"]

        review_prompt = self.REVIEW_PROMPT.format(code=code)

        response = self.llm.generate(
            messages=[{"role": "user", "content": review_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.3
        )

        # Parse score
        import re
        score_match = re.search(r'Score:\s*(\d+(?:\.\d+)?)', response['content'])
        score = float(score_match.group(1)) if score_match else 7.0

        state["code_quality_score"] = score
        state["review_feedback"] = response['content']
        state["messages"].append({
            "role": "assistant",
            "content": f"Code Review: {response['content']}"
        })

        return state

    def _human_approval(self, state: CodeGenState) -> CodeGenState:
        """Present code for human approval with interactive CLI."""
        code = state["generated_code"]
        filename = state["target_filename"]
        review = state["review_feedback"]
        score = state["code_quality_score"]

        # Display code with syntax highlighting
        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold cyan]Generated Code[/bold cyan]\n"
            f"Filename: [yellow]{filename}[/yellow]\n"
            f"Quality Score: [{'green' if score >= 8 else 'yellow'}]{score}/10[/]",
            border_style="cyan"
        ))

        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        self.console.print(syntax)

        # Show review feedback
        self.console.print(f"\n[bold]AI Review:[/bold]\n{review}\n")

        # Interactive prompt
        choice = Prompt.ask(
            "[bold]Action[/bold]",
            choices=["approve", "reject", "modify"],
            default="approve"
        )

        if choice == "approve":
            state["approval_status"] = "approved"
            self.console.print("[bold green]✓ Code approved![/bold green]\n")

        elif choice == "reject":
            state["approval_status"] = "rejected"
            self.console.print("[bold red]✗ Code rejected[/bold red]\n")

        else:  # modify
            feedback = Prompt.ask("[bold]What would you like to modify?[/bold]")
            state["approval_status"] = "needs_modification"
            state["user_feedback"] = feedback
            self.console.print(f"[bold yellow]↻ Regenerating with feedback...[/bold yellow]\n")

        return state

    def _route_approval(self, state: CodeGenState) -> str:
        """Route based on approval status."""
        return state["approval_status"]

    def _write_file(self, state: CodeGenState) -> CodeGenState:
        """Write approved code to workspace."""
        workspace_id = state["workspace_id"]
        filename = state["target_filename"]
        code = state["generated_code"]

        try:
            # Create workspace manager
            ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)

            # Create workspace if doesn't exist
            if not ws.base_path.exists():
                ws.create()

            # Write file
            file_path = ws.write_file(filename, code)

            state["file_written"] = True
            state["file_path"] = str(file_path)

            self.console.print(f"[bold green]✓ File written:[/bold green] {file_path}\n")

        except Exception as e:
            state["file_written"] = False
            state["file_path"] = ""
            self.console.print(f"[bold red]✗ Error writing file:[/bold red] {e}\n")

        return state

    def _route_git(self, state: CodeGenState) -> str:
        """Route to git commit if enabled and file was written successfully."""
        if state.get("git_enabled", False) and state.get("file_written", False):
            return "git_commit"
        return "skip_git"

    def _git_commit(self, state: CodeGenState) -> CodeGenState:
        """Auto-commit generated code to Git with descriptive message."""
        workspace_id = state["workspace_id"]
        filename = state["target_filename"]
        file_path = state["file_path"]
        user_request = state["user_request"]

        try:
            # Get workspace directory
            ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)
            workspace_dir = str(ws.base_path)

            # Initialize GitOperations
            git = GitOperations(workspace_dir)

            # Check if it's a git repository, if not initialize
            try:
                git.get_status()
            except ValueError:
                # Not a git repo, initialize it
                import subprocess
                subprocess.run(["git", "init"], cwd=workspace_dir, check=True, capture_output=True)
                git = GitOperations(workspace_dir)
                self.console.print("[dim]Initialized Git repository[/dim]\n")

            # Generate commit message using LLM
            commit_prompt = self.COMMIT_MESSAGE_PROMPT.format(
                request=user_request,
                filename=filename,
                summary=state.get("plan", {}).get("description", "")[:200]  # First 200 chars
            )

            response = self.llm.generate(
                messages=[{"role": "user", "content": commit_prompt}],
                system=self.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=100
            )

            commit_message = response['content'].strip()

            # Add file to git
            git.add_files([filename])

            # Commit
            commit_info = git.commit(commit_message)

            # Extract commit hash
            state["git_committed"] = True
            state["git_commit_message"] = commit_message
            state["git_commit_hash"] = commit_info.get("hash", "")[:8]  # Short hash

            self.console.print(
                f"[bold green]✓ Git commit:[/bold green] {state['git_commit_hash']} - {commit_message}\n"
            )

        except Exception as e:
            state["git_committed"] = False
            state["git_commit_message"] = ""
            state["git_commit_hash"] = ""
            self.console.print(f"[dim]Warning: Could not commit to Git: {e}[/dim]\n")

        return state

    def _log_decision(self, state: CodeGenState) -> CodeGenState:
        """Log approval decision and git commit to PostgreSQL."""
        try:
            # Create project if doesn't exist
            project_id = self.postgres.create_project(
                name=f"codegen_{state['workspace_id']}",
                description=state["user_request"]
            )

            # Prepare output data with git info
            output_data = {
                "code": state.get("generated_code", ""),
                "filename": state.get("target_filename", ""),
                "file_path": state.get("file_path", ""),
                "quality_score": state.get("code_quality_score", 0.0),
                "git_committed": state.get("git_committed", False),
                "git_commit_hash": state.get("git_commit_hash", ""),
                "git_commit_message": state.get("git_commit_message", "")
            }

            # Create task
            task_id = self.postgres.create_task(
                project_id=project_id,
                agent_name="CodeGenerationAgent",
                task_type="code_generation",
                input_data=state["user_request"],
                output_data=str(output_data),
                status="completed" if state["approval_status"] == "approved" else "rejected"
            )

            # Log decision with git info
            decision_rationale = state.get("user_feedback", "No feedback provided")
            if state.get("git_committed", False):
                decision_rationale += f"\n\nGit commit: {state.get('git_commit_hash', '')} - {state.get('git_commit_message', '')}"

            decision_id = self.postgres.log_decision(
                task_id=task_id,
                decision_point="human_approval",
                options=["approve", "reject", "modify"],
                selected_option=state["approval_status"],
                rationale=decision_rationale
            )

            state["decision_id"] = decision_id

            self.console.print(f"[dim]Decision logged: {decision_id}[/dim]\n")

        except Exception as e:
            self.console.print(f"[dim]Warning: Could not log decision: {e}[/dim]\n")

        return state

    def generate(self, user_request: str, workspace_id: str = None, context: dict = None, git_enabled: bool = True) -> dict:
        """
        Generate code from user request with human approval and optional Git integration.

        Args:
            user_request: User's code generation request
            workspace_id: Workspace ID for file writing (optional, auto-generated if not provided)
            context: Additional context (optional)
            git_enabled: Enable auto-commit to Git (default: True)

        Returns:
            Dictionary with generated code, approval status, file path, and git info
        """
        if workspace_id is None:
            import uuid
            workspace_id = f"codegen-{uuid.uuid4().hex[:8]}"

        initial_state = CodeGenState(
            user_request=user_request,
            context=context or {},
            messages=[],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="generated_code.py",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id=workspace_id,
            file_written=False,
            file_path="",
            git_enabled=git_enabled,
            git_commit_message="",
            git_commit_hash="",
            git_committed=False,
            decision_id=""
        )

        result = self.graph.invoke(initial_state)

        return {
            "generated_code": result.get("generated_code", ""),
            "target_filename": result.get("target_filename", ""),
            "approval_status": result.get("approval_status", ""),
            "file_written": result.get("file_written", False),
            "file_path": result.get("file_path", ""),
            "quality_score": result.get("code_quality_score", 0.0),
            "workspace_id": result.get("workspace_id", ""),
            "git_committed": result.get("git_committed", False),
            "git_commit_hash": result.get("git_commit_hash", ""),
            "git_commit_message": result.get("git_commit_message", ""),
            "messages": result.get("messages", [])
        }
