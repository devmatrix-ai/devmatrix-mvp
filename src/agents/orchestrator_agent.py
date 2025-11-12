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
from src.state.shared_scratchpad import SharedScratchpad
from src.observability import get_logger


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

    SYSTEM_PROMPT = """Sos un arquitecto de software experto y orquestador de proyectos, pero hablás de manera natural y amigable con el usuario.

Tu rol es:
1. Analizar los requerimientos y alcance del proyecto
2. Descomponer proyectos complejos en tareas atómicas y manejables
3. Identificar dependencias entre tareas
4. Asignar tareas a agentes especializados
5. Asegurar una estructura de proyecto coherente

Pautas:
- Pensá como un arquitecto de software senior pero sin ser pedante
- Considerá best practices y design patterns
- Identificá límites claros entre tareas
- Minimizá dependencias para ejecución paralela
- Asegurá completitud (no te pierdas componentes críticos)
- Hablá de manera natural y conversacional, como si estuvieras charlando con un compañero
- Si hay algo que no queda claro, preguntá
- Mantené un tono amigable y profesional, pero no formal"""

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

    def __init__(self, api_key: str = None, agent_registry: AgentRegistry = None, progress_callback=None, enable_rag: bool = True):
        """
        Initialize orchestrator agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
            agent_registry: Agent registry for agent selection (optional, creates default if not provided)
            progress_callback: Optional callback function for progress updates
            enable_rag: Enable RAG for task decomposition enhancement (default: True)
        """
        # Use Claude Opus 4.1 for complex orchestration reasoning
        self.llm = AnthropicClient(api_key=api_key, model="claude-opus-4-1-20250805")
        self.console = Console()
        self.logger = get_logger("orchestrator")
        self.registry = agent_registry or AgentRegistry()
        self.progress_callback = progress_callback
        self.graph = self._build_graph()

        # PostgreSQL is optional - NOTE: Projects table no longer used
        try:
            self.postgres = PostgresManager()
        except Exception:
            self.postgres = None

        # Initialize RAG components if enabled
        self.rag_enabled = enable_rag
        self.retriever = None
        self.context_builder = None

        if enable_rag:
            try:
                from src.rag import (
                    create_embedding_model,
                    create_vector_store,
                    create_retriever,
                    create_context_builder,
                    RetrievalStrategy,
                    ContextTemplate,
                )

                embedding_model = create_embedding_model()
                vector_store = create_vector_store(embedding_model)
                self.retriever = create_retriever(
                    vector_store,
                    strategy=RetrievalStrategy.MMR,
                    top_k=3  # Get 3 similar task breakdowns
                )
                self.context_builder = create_context_builder(
                    template=ContextTemplate.SIMPLE  # Simple format for prompts
                )

                self.logger.info("RAG enabled for task decomposition")

            except Exception as e:
                self.logger.warning(
                    "RAG initialization failed, continuing without RAG",
                    error=str(e),
                    error_type=type(e).__name__
                )
                self.rag_enabled = False

    def _emit_progress(self, event_type: str, data: dict):
        """
        Emit progress event via callback if available.

        Args:
            event_type: Type of event (e.g., 'task_start', 'task_complete', 'phase_start')
            data: Event data dictionary
        """
        if self.progress_callback:
            try:
                self.progress_callback(event_type, data)
            except Exception as e:
                # Don't let callback errors break orchestration
                self.logger.warning("Progress callback error",
                    event_type=event_type,
                    error=str(e),
                    error_type=type(e).__name__
                )

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow for orchestration."""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("analyze_project", self._analyze_project)
        workflow.add_node("decompose_tasks", self._decompose_tasks)
        workflow.add_node("build_dependency_graph", self._build_dependency_graph)
        workflow.add_node("assign_agents", self._assign_agents)
        workflow.add_node("display_plan", self._display_plan)
        workflow.add_node("execute_tasks", self._execute_tasks)  # NEW: Task execution
        workflow.add_node("finalize", self._finalize)

        # Define edges
        workflow.set_entry_point("analyze_project")
        workflow.add_edge("analyze_project", "decompose_tasks")
        workflow.add_edge("decompose_tasks", "build_dependency_graph")
        workflow.add_edge("build_dependency_graph", "assign_agents")
        workflow.add_edge("assign_agents", "display_plan")
        workflow.add_edge("display_plan", "execute_tasks")  # NEW: Execute after displaying plan
        workflow.add_edge("execute_tasks", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _analyze_project(self, state: OrchestratorState) -> OrchestratorState:
        """Analyze project scope and complexity."""
        user_request = state["user_request"]

        self.logger.info("Starting project analysis phase",
            user_request=user_request[:100],  # First 100 chars
            workspace_id=state.get("workspace_id", "unknown")
        )

        # Emit phase start event
        self._emit_progress('phase_start', {
            'phase': 'analyze_project',
            'message': 'Analizando alcance del proyecto...'
        })

        analysis_prompt = self.PROJECT_ANALYSIS_PROMPT.format(request=user_request)

        response = self.llm.generate(
            messages=[{"role": "user", "content": analysis_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.0  # Deterministic mode
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

        self.logger.info("Project analysis completed",
            project_type=project_type,
            complexity=complexity,
            workspace_id=state.get("workspace_id", "unknown")
        )

        # Display visual panel for user
        self.console.print(Panel.fit(
            f"[bold cyan]Project Analysis[/bold cyan]\n\n"
            f"Type: [yellow]{project_type}[/yellow]\n"
            f"Complexity: [{'red' if complexity > 0.7 else 'yellow' if complexity > 0.4 else 'green'}]{complexity:.1f}[/]\n",
            border_style="cyan"
        ))

        # Emit phase complete event
        self._emit_progress('phase_complete', {
            'phase': 'analyze_project',
            'project_type': project_type,
            'complexity': complexity
        })

        return state

    def _decompose_tasks(self, state: OrchestratorState) -> OrchestratorState:
        """Decompose project into atomic tasks."""
        user_request = state["user_request"]
        project_type = state["project_type"]
        complexity = state["complexity"]

        self.logger.info("Starting task decomposition phase",
            project_type=project_type,
            complexity=complexity,
            workspace_id=state.get("workspace_id", "unknown")
        )

        # Emit phase start event
        self._emit_progress('phase_start', {
            'phase': 'decompose_tasks',
            'message': 'Descomponiendo proyecto en tareas...'
        })

        # Try to retrieve similar task breakdowns from RAG
        rag_context = ""
        if self.rag_enabled and self.retriever:
            try:
                query = f"{project_type} project: {user_request}"
                results = self.retriever.retrieve(
                    query=query,
                    top_k=3,
                    min_similarity=0.65,  # Lower threshold for task breakdowns
                    filters={"task_type": "task_breakdown"}  # Filter for task breakdown examples
                )

                if results:
                    rag_context = self.context_builder.build_context(query, results)
                    self.logger.info(
                        "Retrieved similar task breakdowns",
                        num_results=len(results),
                        avg_similarity=sum(r.similarity for r in results) / len(results) if results else 0,
                        workspace_id=state.get("workspace_id", "unknown")
                    )

            except Exception as e:
                self.logger.warning(
                    "RAG retrieval failed during task decomposition",
                    error=str(e),
                    error_type=type(e).__name__,
                    workspace_id=state.get("workspace_id", "unknown")
                )

        # Build decomposition prompt (with or without RAG context)
        decomposition_prompt = self.TASK_DECOMPOSITION_PROMPT.format(
            request=user_request,
            project_type=project_type,
            complexity=complexity
        )

        # Add RAG context if available
        if rag_context:
            decomposition_prompt = f"""{decomposition_prompt}

Similar Task Breakdown Examples (for reference):
{rag_context}

Use these examples as inspiration for task decomposition patterns, but adapt to the specific requirements above.
"""

        response = self.llm.generate(
            messages=[{"role": "user", "content": decomposition_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.0,  # Deterministic mode
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

        self.logger.info("Task decomposition completed",
            num_tasks=len(tasks),
            task_types=[t["task_type"] for t in tasks],
            workspace_id=state.get("workspace_id", "unknown")
        )

        # Emit phase complete event
        self._emit_progress('phase_complete', {
            'phase': 'decompose_tasks',
            'num_tasks': len(tasks)
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
                self.logger.warning("Circular dependency detected",
                    task_id=task_id,
                    dependencies=dependency_graph.get(task_id, []),
                    workspace_id=state.get("workspace_id", "unknown")
                )

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
                self.logger.warning("No agent available for task",
                    task_id=task['id'],
                    task_type=task_type_str,
                    workspace_id=state.get("workspace_id", "unknown")
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

    def _execute_tasks(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute tasks respecting dependencies.

        Uses topological sort to ensure tasks execute in correct order,
        with parallel execution for independent tasks.
        """
        tasks = state["tasks"]
        dependency_graph = state["dependency_graph"]
        workspace_id = state["workspace_id"]

        # Emit execution start event
        self._emit_progress('execution_start', {
            'total_tasks': len(tasks),
            'workspace_id': workspace_id
        })

        self.console.print("\n")
        self.console.print(Panel.fit(
            "[bold green]🚀 Starting Task Execution[/bold green]",
            border_style="green"
        ))

        # Create shared scratchpad for inter-agent communication (if Redis is available)
        try:
            scratchpad = SharedScratchpad(workspace_id=workspace_id)
        except Exception as e:
            self.logger.warning("Could not create SharedScratchpad",
                workspace_id=workspace_id,
                error=str(e),
                error_type=type(e).__name__
            )
            self.logger.info("Continuing without SharedScratchpad - inter-agent communication disabled",
                workspace_id=workspace_id
            )
            scratchpad = None

        # Initialize task status tracking
        completed_tasks = []
        failed_tasks = []
        task_outputs = {}  # task_id -> output

        # Topological sort for execution order
        execution_order = self._topological_sort(tasks, dependency_graph)

        if not execution_order:
            self.logger.error("Circular dependencies detected in task graph",
                workspace_id=workspace_id,
                num_tasks=len(tasks),
                dependency_graph=dependency_graph
            )
            self.console.print("[bold red]Error: Circular dependencies detected![/bold red]\n")
            state["success"] = False
            state["error_message"] = "Circular dependencies detected in task graph"
            return state

        # Execute tasks in order
        for idx, task in enumerate(execution_order):
            task_id = task["id"]
            task_type = task["task_type"]
            assigned_agent = task["assigned_agent"]

            # Emit task start event
            self._emit_progress('task_start', {
                'task_id': task_id,
                'task_type': task_type,
                'description': task['description'],
                'agent': assigned_agent,
                'progress': f"{idx + 1}/{len(execution_order)}"
            })

            self.logger.info("Executing task",
                task_id=task_id,
                task_type=task_type,
                agent=assigned_agent,
                progress=f"{idx + 1}/{len(execution_order)}",
                workspace_id=workspace_id
            )

            self.console.print(f"\n[cyan]Executing {task_id}[/cyan]: {task['description']}")
            self.console.print(f"  Agent: [yellow]{assigned_agent}[/yellow]")

            # Check if dependencies are met
            dependencies_met = all(
                dep_id in completed_tasks
                for dep_id in task["dependencies"]
            )

            if not dependencies_met:
                self.logger.warning("Task dependencies not met",
                    task_id=task_id,
                    dependencies=task["dependencies"],
                    completed_tasks=completed_tasks,
                    workspace_id=workspace_id
                )
                self.console.print(f"  [red]❌ Dependencies not met, skipping[/red]")
                failed_tasks.append(task_id)
                task["status"] = "failed"

                # Emit task failure event
                self._emit_progress('task_failed', {
                    'task_id': task_id,
                    'error': 'Dependencies not met'
                })
                continue

            # Get agent instance
            try:
                agent = self.registry.get_agent(assigned_agent, api_key=self.llm.api_key)
            except ValueError:
                self.logger.error("Agent not found",
                    agent_name=assigned_agent,
                    task_id=task_id,
                    workspace_id=workspace_id
                )
                self.console.print(f"  [red]❌ Agent '{assigned_agent}' not found[/red]")
                failed_tasks.append(task_id)
                task["status"] = "failed"
                continue

            # Prepare execution context
            context = {
                "workspace_id": workspace_id,
                "scratchpad": scratchpad,
                "dependency_outputs": {
                    dep_id: task_outputs.get(dep_id)
                    for dep_id in task["dependencies"]
                }
            }

            # Execute task
            try:
                result = agent.execute(task, context)

                if result.get("success"):
                    self.logger.info("Task completed successfully",
                        task_id=task_id,
                        agent=assigned_agent,
                        output_files=result.get("file_paths", []),
                        workspace_id=workspace_id
                    )
                    self.console.print(f"  [green]✓ Completed successfully[/green]")
                    completed_tasks.append(task_id)
                    task["status"] = "completed"
                    task["output"] = result.get("output", {})
                    task_outputs[task_id] = result

                    # Emit task complete event
                    self._emit_progress('task_complete', {
                        'task_id': task_id,
                        'output_files': result.get("file_paths", []),
                        'completed': len(completed_tasks),  # Current count of completed tasks
                        'total_tasks': len(tasks)  # Total tasks
                    })
                else:
                    error_msg = result.get("error", "Unknown error")
                    self.logger.error("Task execution failed",
                        task_id=task_id,
                        agent=assigned_agent,
                        error=error_msg,
                        workspace_id=workspace_id
                    )
                    self.console.print(f"  [red]❌ Failed: {error_msg}[/red]")
                    failed_tasks.append(task_id)
                    task["status"] = "failed"

                    # Emit task failure event
                    self._emit_progress('task_failed', {
                        'task_id': task_id,
                        'error': error_msg
                    })

            except Exception as e:
                self.logger.error("Task execution exception",
                    task_id=task_id,
                    agent=assigned_agent,
                    error=str(e),
                    error_type=type(e).__name__,
                    workspace_id=workspace_id,
                    exc_info=True
                )
                self.console.print(f"  [red]❌ Exception: {str(e)}[/red]")
                failed_tasks.append(task_id)
                task["status"] = "failed"

                # Emit task failure event
                self._emit_progress('task_failed', {
                    'task_id': task_id,
                    'error': str(e)
                })

        # Update state
        state["completed_tasks"] = completed_tasks
        state["failed_tasks"] = failed_tasks
        state["tasks"] = tasks  # Update with new statuses

        self.logger.info("Task execution phase completed",
            total_tasks=len(tasks),
            completed=len(completed_tasks),
            failed=len(failed_tasks),
            success=len(failed_tasks) == 0,
            workspace_id=workspace_id
        )

        # Display summary panel for user
        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold]Execution Summary[/bold]\n\n"
            f"✓ Completed: [green]{len(completed_tasks)}[/green]\n"
            f"❌ Failed: [red]{len(failed_tasks)}[/red]\n"
            f"📊 Total: {len(tasks)}",
            border_style="green" if not failed_tasks else "yellow"
        ))

        state["success"] = len(failed_tasks) == 0
        if failed_tasks:
            state["error_message"] = f"Failed tasks: {', '.join(failed_tasks)}"

        # Emit execution complete event
        self._emit_progress('execution_complete', {
            'total_tasks': len(tasks),
            'completed': len(completed_tasks),
            'failed': len(failed_tasks),
            'success': len(failed_tasks) == 0
        })

        return state

    def _topological_sort(
        self,
        tasks: List[Task],
        dependency_graph: Dict[str, List[str]]
    ) -> List[Task]:
        """
        Topological sort of tasks based on dependencies.

        Returns tasks in execution order, or empty list if circular dependency.
        """
        # Build in-degree map
        in_degree = {task["id"]: 0 for task in tasks}
        for task_id, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:  # Only count dependencies that exist
                    in_degree[task_id] += 1

        # Find tasks with no dependencies
        queue = [task for task in tasks if in_degree[task["id"]] == 0]
        result = []

        while queue:
            # Take task with no dependencies
            current_task = queue.pop(0)
            result.append(current_task)
            current_id = current_task["id"]

            # Find tasks that depend on current task
            for task in tasks:
                if current_id in dependency_graph.get(task["id"], []):
                    in_degree[task["id"]] -= 1
                    if in_degree[task["id"]] == 0:
                        queue.append(task)

        # If not all tasks processed, there's a cycle
        if len(result) != len(tasks):
            return []

        return result

    def _finalize(self, state: OrchestratorState) -> OrchestratorState:
        """
        Finalize orchestration and log results.

        NOTE: Projects table persistence removed - use masterplans tables exclusively.
        """
        # success already set by _execute_tasks
        # completed_tasks and failed_tasks already set by _execute_tasks

        # Log completion
        self.logger.info("Orchestration finalized",
            workspace_id=state.get("workspace_id", "unknown"),
            success=state.get("success", False),
            total_tasks=len(state.get("tasks", [])),
            completed_tasks=len(state.get("completed_tasks", [])),
            failed_tasks=len(state.get("failed_tasks", []))
        )

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
