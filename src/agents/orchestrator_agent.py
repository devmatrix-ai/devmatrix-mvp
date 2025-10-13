"""
Orchestrator Agent

Multi-agent coordination system that decomposes complex tasks,
assigns them to specialized agents, and orchestrates their execution.
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from langgraph.graph import StateGraph, END
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from src.llm.anthropic_client import AnthropicClient
from src.state.postgres_manager import PostgresManager
from src.agents.agent_registry import AgentRegistry, TaskType


# Message reducer
def add_messages(left: Sequence[dict], right: Sequence[dict]) -> Sequence[dict]:
    """Reducer to accumulate messages."""
    return list(left) + list(right)


class Task(TypedDict):
    """Represents a single task in the decomposition."""
    id: str
    description: str
    task_type: str  # 'implementation', 'testing', 'documentation'
    dependencies: List[str]  # List of task IDs this depends on
    assigned_agent: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    output: Dict[str, Any]


class OrchestratorState(TypedDict):
    """State for orchestrator agent."""
    user_request: str
    context: dict
    messages: Annotated[Sequence[dict], add_messages]

    # Project understanding
    project_type: str  # 'simple_function', 'module', 'api', 'library'
    complexity: float  # 0-1 scale

    # Task decomposition
    tasks: List[Task]
    dependency_graph: Dict[str, List[str]]  # task_id -> [dependent_task_ids]

    # Execution
    completed_tasks: List[str]  # List of completed task IDs
    failed_tasks: List[str]

    # Results
    workspace_id: str
    project_structure: Dict[str, Any]  # File structure and paths
    success: bool
    error_message: str


class OrchestratorAgent:
    """
    Orchestrator agent that coordinates multiple specialized agents.

    Workflow:
    1. Analyze project scope and complexity
    2. Decompose into atomic tasks
    3. Build dependency graph
    4. Assign tasks to specialized agents
    5. Execute tasks (respecting dependencies)
    6. Aggregate results

    Usage:
        orchestrator = OrchestratorAgent()
        result = orchestrator.orchestrate(
            user_request="Create a REST API for user management",
            workspace_id="my-api-project"
        )
    """

    SYSTEM_PROMPT = """You are an expert software architect and project orchestrator.

Your role is to:
1. Analyze project requirements and scope
2. Break down complex projects into atomic, manageable tasks
3. Identify dependencies between tasks
4. Assign tasks to specialized agents
5. Ensure coherent project structure

Guidelines:
- Think like a senior software architect
- Consider best practices and design patterns
- Identify clear task boundaries
- Minimize dependencies for parallel execution
- Ensure completeness (don't miss critical components)
"""

    PROJECT_ANALYSIS_PROMPT = """Analyze this project request and determine its scope and complexity.

Request: {request}

Analyze:
1. What type of project is this? (simple function, module, API, library, etc.)
2. What are the main components needed?
3. How complex is this project? (0-1 scale where 0=trivial, 1=very complex)
4. What programming languages/frameworks are involved?

Provide structured analysis:
Project Type: [type]
Complexity: [0-1]
Components: [list]
Languages: [list]
"""

    TASK_DECOMPOSITION_PROMPT = """Decompose this project into atomic tasks for specialized agents.

Project Request: {request}
Project Type: {project_type}
Complexity: {complexity}

Available Agent Types:
- implementation: Generates Python code (functions, classes, modules)
- testing: Generates and runs tests (pytest)
- documentation: Generates README, docstrings, API docs

For each task, provide:
1. Task ID (unique identifier, e.g., task_1, task_2)
2. Description (clear, specific description of what to implement)
3. Task Type (implementation, testing, or documentation)
4. Dependencies (which task IDs must be completed first)
5. Estimated Files (what files this task will create/modify)

Format your response as a JSON array:
```json
[
  {{
    "id": "task_1",
    "description": "Create User model with validation",
    "task_type": "implementation",
    "dependencies": [],
    "files": ["models/user.py"]
  }},
  {{
    "id": "task_2",
    "description": "Create tests for User model",
    "task_type": "testing",
    "dependencies": ["task_1"],
    "files": ["tests/test_user.py"]
  }}
]
```

Important:
- Keep tasks atomic and focused
- Minimize dependencies for parallelization
- Implementation tasks should come before testing tasks
- Documentation tasks usually come last
- Aim for 3-10 tasks total (don't over-decompose)
"""

    def __init__(self, api_key: str = None, agent_registry: AgentRegistry = None):
        """
        Initialize orchestrator agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
            agent_registry: Agent registry for agent selection (optional, creates default if not provided)
        """
        self.llm = AnthropicClient(api_key=api_key)
        self.console = Console()
        self.registry = agent_registry or AgentRegistry()
        self.graph = self._build_graph()
        self.postgres = PostgresManager()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow for orchestration."""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("analyze_project", self._analyze_project)
        workflow.add_node("decompose_tasks", self._decompose_tasks)
        workflow.add_node("build_dependency_graph", self._build_dependency_graph)
        workflow.add_node("assign_agents", self._assign_agents)
        workflow.add_node("display_plan", self._display_plan)
        workflow.add_node("finalize", self._finalize)

        # Define edges
        workflow.set_entry_point("analyze_project")
        workflow.add_edge("analyze_project", "decompose_tasks")
        workflow.add_edge("decompose_tasks", "build_dependency_graph")
        workflow.add_edge("build_dependency_graph", "assign_agents")
        workflow.add_edge("assign_agents", "display_plan")
        workflow.add_edge("display_plan", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _analyze_project(self, state: OrchestratorState) -> OrchestratorState:
        """Analyze project scope and complexity."""
        user_request = state["user_request"]

        analysis_prompt = self.PROJECT_ANALYSIS_PROMPT.format(request=user_request)

        response = self.llm.generate(
            messages=[{"role": "user", "content": analysis_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.3
        )

        content = response['content']

        # Parse response to extract project type and complexity
        project_type = "module"  # default
        complexity = 0.5  # default

        import re

        # Extract project type
        type_match = re.search(r'Project Type:\s*(.+)', content, re.IGNORECASE)
        if type_match:
            project_type = type_match.group(1).strip().lower()

        # Extract complexity
        complexity_match = re.search(r'Complexity:\s*(\d+\.?\d*)', content, re.IGNORECASE)
        if complexity_match:
            try:
                complexity = float(complexity_match.group(1))
                complexity = max(0.0, min(1.0, complexity))  # Clamp to [0, 1]
            except ValueError:
                pass

        state["project_type"] = project_type
        state["complexity"] = complexity
        state["messages"].append({
            "role": "assistant",
            "content": f"Project Analysis:\n{content}"
        })

        self.console.print(Panel.fit(
            f"[bold cyan]Project Analysis[/bold cyan]\n\n"
            f"Type: [yellow]{project_type}[/yellow]\n"
            f"Complexity: [{'red' if complexity > 0.7 else 'yellow' if complexity > 0.4 else 'green'}]{complexity:.1f}[/]\n",
            border_style="cyan"
        ))

        return state

    def _decompose_tasks(self, state: OrchestratorState) -> OrchestratorState:
        """Decompose project into atomic tasks."""
        user_request = state["user_request"]
        project_type = state["project_type"]
        complexity = state["complexity"]

        decomposition_prompt = self.TASK_DECOMPOSITION_PROMPT.format(
            request=user_request,
            project_type=project_type,
            complexity=complexity
        )

        response = self.llm.generate(
            messages=[{"role": "user", "content": decomposition_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=4096
        )

        # Parse JSON response
        import json
        import re

        content = response['content']

        # Extract JSON from markdown if present
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array in the content
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            json_str = json_match.group(0) if json_match else '[]'

        try:
            tasks_data = json.loads(json_str)
            if not tasks_data:  # Check for empty list after successful parse
                raise ValueError("Empty task list")
        except (json.JSONDecodeError, ValueError):
            # Fallback: create a single task
            tasks_data = [{
                "id": "task_1",
                "description": user_request,
                "task_type": "implementation",
                "dependencies": [],
                "files": ["main.py"]
            }]

        # Convert to Task TypedDict
        tasks = []
        for task_data in tasks_data:
            task = Task(
                id=task_data.get("id", f"task_{len(tasks) + 1}"),
                description=task_data.get("description", ""),
                task_type=task_data.get("task_type", "implementation"),
                dependencies=task_data.get("dependencies", []),
                assigned_agent="",  # Will be assigned later
                status="pending",
                output={}
            )
            tasks.append(task)

        state["tasks"] = tasks
        state["messages"].append({
            "role": "assistant",
            "content": f"Task Decomposition:\n{json.dumps(tasks_data, indent=2)}"
        })

        return state

    def _build_dependency_graph(self, state: OrchestratorState) -> OrchestratorState:
        """Build dependency graph from tasks."""
        tasks = state["tasks"]

        # Create dependency graph
        dependency_graph = {}
        for task in tasks:
            dependency_graph[task["id"]] = task["dependencies"]

        state["dependency_graph"] = dependency_graph

        # Validate no circular dependencies (simple check)
        visited = set()
        def has_cycle(task_id, path):
            if task_id in path:
                return True
            if task_id in visited:
                return False
            visited.add(task_id)
            for dep in dependency_graph.get(task_id, []):
                if has_cycle(dep, path + [task_id]):
                    return True
            return False

        for task_id in dependency_graph:
            if has_cycle(task_id, []):
                self.console.print(f"[bold red]Warning: Circular dependency detected for {task_id}[/bold red]\n")

        return state

    def _assign_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Assign specialized agents to tasks based on capabilities."""
        tasks = state["tasks"]

        # Task type mapping to TaskType enum
        type_mapping = {
            "implementation": TaskType.IMPLEMENTATION,
            "testing": TaskType.TESTING,
            "documentation": TaskType.DOCUMENTATION,
            "analysis": TaskType.ANALYSIS,
            "refactoring": TaskType.REFACTORING
        }

        # Assign agents to tasks
        for task in tasks:
            task_type_str = task["task_type"]
            task_type = type_mapping.get(task_type_str, TaskType.IMPLEMENTATION)

            # Find best agent for this task type
            agent_name = self.registry.find_agent_for_task(task_type)

            if agent_name:
                task["assigned_agent"] = agent_name
            else:
                # No agent available for this task type - mark as unassigned
                task["assigned_agent"] = "unassigned"
                self.console.print(
                    f"[yellow]Warning: No agent available for task {task['id']} "
                    f"(type: {task_type_str})[/yellow]\n"
                )

        return state

    def _display_plan(self, state: OrchestratorState) -> OrchestratorState:
        """Display execution plan to user."""
        tasks = state["tasks"]
        dependency_graph = state["dependency_graph"]

        self.console.print("\n")
        self.console.print(Panel.fit(
            "[bold cyan]Execution Plan[/bold cyan]",
            border_style="cyan"
        ))

        # Create tree visualization
        tree = Tree("🎯 [bold]Project Tasks[/bold]")

        # Group tasks by type
        impl_tasks = [t for t in tasks if t["task_type"] == "implementation"]
        test_tasks = [t for t in tasks if t["task_type"] == "testing"]
        doc_tasks = [t for t in tasks if t["task_type"] == "documentation"]

        if impl_tasks:
            impl_branch = tree.add("💻 [cyan]Implementation Tasks[/cyan]")
            for task in impl_tasks:
                deps_str = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
                agent_str = f" [agent: {task['assigned_agent']}]" if task.get('assigned_agent') else ""
                impl_branch.add(f"[yellow]{task['id']}[/yellow]: {task['description']}{deps_str}{agent_str}")

        if test_tasks:
            test_branch = tree.add("🧪 [green]Testing Tasks[/green]")
            for task in test_tasks:
                deps_str = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
                agent_str = f" [agent: {task['assigned_agent']}]" if task.get('assigned_agent') else ""
                test_branch.add(f"[yellow]{task['id']}[/yellow]: {task['description']}{deps_str}{agent_str}")

        if doc_tasks:
            doc_branch = tree.add("📝 [blue]Documentation Tasks[/blue]")
            for task in doc_tasks:
                deps_str = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
                agent_str = f" [agent: {task['assigned_agent']}]" if task.get('assigned_agent') else ""
                doc_branch.add(f"[yellow]{task['id']}[/yellow]: {task['description']}{deps_str}{agent_str}")

        self.console.print(tree)
        self.console.print("\n")

        # Show parallelization opportunities
        independent_tasks = [t for t in tasks if not t["dependencies"]]
        if len(independent_tasks) > 1:
            self.console.print(
                f"[dim]⚡ {len(independent_tasks)} tasks can run in parallel[/dim]\n"
            )

        return state

    def _finalize(self, state: OrchestratorState) -> OrchestratorState:
        """Finalize orchestration and prepare for execution."""
        state["success"] = True
        state["completed_tasks"] = []
        state["failed_tasks"] = []

        # Log to PostgreSQL
        try:
            project_id = self.postgres.create_project(
                name=f"orchestrated_{state['workspace_id']}",
                description=state["user_request"]
            )

            task_id = self.postgres.create_task(
                project_id=project_id,
                agent_name="OrchestratorAgent",
                task_type="orchestration",
                input_data=state["user_request"],
                output_data=str({
                    "project_type": state["project_type"],
                    "complexity": state["complexity"],
                    "num_tasks": len(state["tasks"])
                }),
                status="completed"
            )

        except Exception as e:
            self.console.print(f"[dim]Warning: Could not log orchestration: {e}[/dim]\n")

        return state

    def orchestrate(self, user_request: str, workspace_id: str = None, context: dict = None) -> dict:
        """
        Orchestrate multi-agent execution for complex projects.

        Args:
            user_request: User's project request
            workspace_id: Workspace ID (optional, auto-generated if not provided)
            context: Additional context (optional)

        Returns:
            Dictionary with task decomposition and execution plan
        """
        if workspace_id is None:
            import uuid
            workspace_id = f"orchestrated-{uuid.uuid4().hex[:8]}"

        initial_state = OrchestratorState(
            user_request=user_request,
            context=context or {},
            messages=[],
            project_type="",
            complexity=0.0,
            tasks=[],
            dependency_graph={},
            completed_tasks=[],
            failed_tasks=[],
            workspace_id=workspace_id,
            project_structure={},
            success=False,
            error_message=""
        )

        result = self.graph.invoke(initial_state)

        return {
            "workspace_id": result.get("workspace_id", ""),
            "project_type": result.get("project_type", ""),
            "complexity": result.get("complexity", 0.0),
            "tasks": result.get("tasks", []),
            "dependency_graph": result.get("dependency_graph", {}),
            "success": result.get("success", False),
            "messages": result.get("messages", [])
        }
