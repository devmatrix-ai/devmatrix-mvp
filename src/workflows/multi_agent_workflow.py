"""
Multi-Agent Workflow

Orchestrates multiple specialized agents using LangGraph for complex task execution.
Integrates OrchestratorAgent, AgentRegistry, SharedScratchpad, and ParallelExecutor.
"""

from typing import Dict, Any, List, TypedDict, Annotated, Sequence
from src.observability import get_logger
from langgraph.graph import StateGraph, END
import operator
from pathlib import Path

from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.agent_registry import AgentRegistry, AgentCapability, TaskType
from src.agents.implementation_agent import ImplementationAgent
from src.agents.testing_agent import TestingAgent
from src.agents.documentation_agent import DocumentationAgent
from src.agents.parallel_executor import ParallelExecutor
from src.state.shared_scratchpad import SharedScratchpad
from src.state.postgres_manager import PostgresManager
from src.performance.performance_monitor import PerformanceMonitor
from src.performance.cache_manager import CacheManager


class MultiAgentState(TypedDict):
    """State for multi-agent workflow."""
    # Input
    project_request: str
    workspace_id: str

    # Orchestration
    tasks: List[Dict[str, Any]]
    dependency_graph: Dict[str, List[str]]

    # Execution
    scratchpad: SharedScratchpad
    registry: AgentRegistry
    executor: ParallelExecutor
    performance_monitor: PerformanceMonitor
    cache_manager: CacheManager

    # Results
    completed_tasks: List[str]
    failed_tasks: List[str]
    execution_stats: Dict[str, Any]
    performance_metrics: Dict[str, Any]

    # Messages
    messages: Annotated[Sequence[str], operator.add]

    # Status
    status: str  # "planning", "executing", "completed", "failed"
    error: str


class MultiAgentWorkflow:
    """
    Orchestrates multiple specialized agents using LangGraph.

    Workflow:
    1. Plan: OrchestratorAgent decomposes project into tasks
    2. Register: Register specialized agents in AgentRegistry
    3. Execute: ParallelExecutor runs tasks using appropriate agents
    4. Finalize: Collect results and clean up

    Features:
    - Dynamic task decomposition
    - Capability-based agent routing
    - Parallel task execution
    - Inter-agent communication via SharedScratchpad
    - Error handling and recovery

    Usage:
        workflow = MultiAgentWorkflow(workspace_id="my-project")
        result = workflow.run("Build a calculator with tests and docs")
    """

    def __init__(
        self,
        workspace_id: str,
        max_workers: int = 4,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        postgres_config: Dict[str, Any] = None,
        enable_performance_monitoring: bool = True,
        enable_caching: bool = True
    ):
        """
        Initialize multi-agent workflow.

        Args:
            workspace_id: Workspace identifier
            max_workers: Maximum concurrent workers for parallel execution
            redis_host: Redis host for SharedScratchpad
            redis_port: Redis port for SharedScratchpad
            postgres_config: PostgreSQL configuration (optional)
            enable_performance_monitoring: Enable performance monitoring (default: True)
            enable_caching: Enable LLM response caching (default: True)
        """
        self.workspace_id = workspace_id
        self.max_workers = max_workers
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_caching = enable_caching

        # Initialize components
        self.orchestrator = OrchestratorAgent()
        self.registry = AgentRegistry()
        self.scratchpad = SharedScratchpad(
            redis_host=redis_host,
            redis_port=redis_port
        )
        self.executor = ParallelExecutor(max_workers=max_workers)

        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor() if enable_performance_monitoring else None

        # Initialize cache manager
        self.cache_manager = CacheManager() if enable_caching else None

        # Optional PostgreSQL tracking
        self.postgres = None
        if postgres_config:
            self.postgres = PostgresManager(**postgres_config)

        # Register specialized agents
        self._register_agents()

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _register_agents(self):
        """Register all specialized agents in the registry."""
        # Implementation Agent
        impl_agent = ImplementationAgent()
        self.registry.register_agent(
            name="ImplementationAgent",
            agent_instance=impl_agent,
            capabilities=impl_agent.get_capabilities(),
            priority=10,
            tags=["code", "python"]
        )

        # Testing Agent
        test_agent = TestingAgent()
        self.registry.register_agent(
            name="TestingAgent",
            agent_instance=test_agent,
            capabilities=test_agent.get_capabilities(),
            priority=8,
            tags=["testing", "pytest"]
        )

        # Documentation Agent
        doc_agent = DocumentationAgent()
        self.registry.register_agent(
            name="DocumentationAgent",
            agent_instance=doc_agent,
            capabilities=doc_agent.get_capabilities(),
            priority=6,
            tags=["documentation", "markdown"]
        )

    def _build_graph(self) -> StateGraph:
        """Build LangGraph state machine for multi-agent workflow."""
        graph = StateGraph(MultiAgentState)

        # Add nodes
        graph.add_node("plan", self._plan_node)
        graph.add_node("execute", self._execute_node)
        graph.add_node("finalize", self._finalize_node)

        # Add edges
        graph.set_entry_point("plan")
        graph.add_edge("plan", "execute")
        graph.add_edge("execute", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    def _plan_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        Plan node: Decompose project into tasks.

        Uses OrchestratorAgent to analyze request and create task plan.
        """
        state["messages"].append("🎯 Planning: Decomposing project into tasks")
        state["status"] = "planning"

        try:
            # Orchestrate project decomposition
            result = self.orchestrator.orchestrate(
                project_request=state["project_request"],
                workspace_id=state["workspace_id"]
            )

            if not result["success"]:
                state["status"] = "failed"
                state["error"] = f"Planning failed: {result.get('error', 'Unknown error')}"
                return state

            # Extract tasks and dependency graph
            state["tasks"] = result["plan"]["tasks"]
            state["dependency_graph"] = result["dependency_graph"]

            # Initialize execution components
            state["scratchpad"] = self.scratchpad
            state["registry"] = self.registry
            state["executor"] = self.executor

            state["messages"].append(f"✅ Plan created: {len(state['tasks'])} tasks identified")

            return state

        except Exception as e:
            state["status"] = "failed"
            state["error"] = f"Planning exception: {str(e)}"
            return state

    def _execute_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        Execute node: Run tasks in parallel using appropriate agents.

        Uses ParallelExecutor to run tasks with dependency management.
        """
        state["messages"].append("⚙️ Executing: Running tasks with specialized agents")
        state["status"] = "executing"

        monitor = state.get("performance_monitor")

        try:
            # Create executor function that routes to appropriate agents
            def agent_executor(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
                """Execute single task using appropriate agent."""
                task_type = task.get("task_type", "implementation")
                task_id = task.get("id", "unknown")

                # Find appropriate agent
                agent_result = state["registry"].find_agent_for_task({
                    "task_type": task_type,
                    "description": task["description"]
                })

                if not agent_result["success"]:
                    if monitor:
                        monitor.record_task_completion(success=False)
                    return {
                        "success": False,
                        "error": f"No agent found for task type: {task_type}",
                        "output": None
                    }

                # Get agent instance and execute with performance tracking
                agent_name = agent_result["agent_name"]
                agent = state["registry"].get_agent_instance(agent_name)

                # Track agent execution
                if monitor:
                    with monitor.track_agent(agent_name) as timer:
                        with monitor.track_task(task_id):
                            result = agent.execute(task, context)

                            # Record tokens if present in result
                            if "usage" in result:
                                usage = result["usage"]
                                timer.record_tokens(
                                    input_tokens=usage.get("input_tokens", 0),
                                    output_tokens=usage.get("output_tokens", 0)
                                )

                            # Record task completion
                            monitor.record_task_completion(
                                success=result.get("success", False),
                                skipped=result.get("skipped", False)
                            )
                else:
                    result = agent.execute(task, context)

                return result

            # Execute tasks in parallel
            context = {
                "workspace_id": state["workspace_id"],
                "scratchpad": state["scratchpad"],
                "cache_manager": state.get("cache_manager")
            }

            execution_result = state["executor"].execute_tasks(
                tasks=state["tasks"],
                executor_func=agent_executor,
                context=context
            )

            # Store results
            state["completed_tasks"] = execution_result["completed_tasks"]
            state["failed_tasks"] = execution_result["failed_tasks"]
            state["execution_stats"] = execution_result["stats"]

            # Record parallel time saved in monitor
            if monitor and execution_result["stats"].get("parallel_time_saved", 0) > 0:
                monitor.record_parallel_time_saved(
                    execution_result["stats"]["parallel_time_saved"]
                )

            # Update messages
            stats = execution_result["stats"]
            state["messages"].append(
                f"✅ Execution complete: {stats['successful']} successful, "
                f"{stats['failed']} failed, {stats['skipped']} skipped"
            )

            if stats["parallel_time_saved"] > 0:
                state["messages"].append(
                    f"⚡ Parallel execution saved {stats['parallel_time_saved']:.2f}s"
                )

            # Check if any critical tasks failed
            if stats["failed"] > 0:
                state["status"] = "completed_with_errors"
            else:
                state["status"] = "completed"

            return state

        except Exception as e:
            if monitor:
                monitor.record_task_completion(success=False)
            state["status"] = "failed"
            state["error"] = f"Execution exception: {str(e)}"
            return state

    def _finalize_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        Finalize node: Collect results and clean up.

        Aggregates artifacts, updates tracking, and prepares final output.
        """
        state["messages"].append("📊 Finalizing: Collecting results")

        try:
            # Collect all artifacts from scratchpad
            all_artifacts = state["scratchpad"].read_artifacts()

            state["messages"].append(
                f"✅ Finalization complete: {len(all_artifacts)} artifacts created"
            )

            # Track in PostgreSQL if available
            if self.postgres:
                try:
                    # Create project entry
                    project_id = self.postgres.create_project(
                        name=f"workflow_{state['workspace_id']}",
                        description=state.get("project_request", "Multi-agent workflow execution")
                    )

                    # Log completed tasks
                    for task_id in state["completed_tasks"]:
                        task_data = next((t for t in state["tasks"] if t["id"] == task_id), None)
                        if task_data:
                            self.postgres.create_task(
                                project_id=project_id,
                                agent_name=task_data.get("assigned_agent", "unknown"),
                                task_type=task_data.get("task_type", "unknown"),
                                input_data=task_data.get("description", ""),
                                output_data=str(task_data.get("output", {})),
                                status="completed"
                            )

                    # Log failed tasks
                    for task_id in state["failed_tasks"]:
                        task_data = next((t for t in state["tasks"] if t["id"] == task_id), None)
                        if task_data:
                            self.postgres.create_task(
                                project_id=project_id,
                                agent_name=task_data.get("assigned_agent", "unknown"),
                                task_type=task_data.get("task_type", "unknown"),
                                input_data=task_data.get("description", ""),
                                output_data=task_data.get("error", "Task failed"),
                                status="failed"
                            )

                    state["messages"].append(
                        f"📊 PostgreSQL: Logged {len(state['completed_tasks'])} completed, "
                        f"{len(state['failed_tasks'])} failed tasks"
                    )

                except Exception as e:
                    # Don't fail workflow if logging fails
                    state["messages"].append(f"⚠️ PostgreSQL logging failed: {e}")

            return state

        except Exception as e:
            state["messages"].append(f"⚠️ Finalization warning: {str(e)}")
            return state

    def run(self, project_request: str, show_performance_report: bool = False) -> Dict[str, Any]:
        """
        Run multi-agent workflow for project request.

        Args:
            project_request: Description of project to build
            show_performance_report: Print performance report after execution

        Returns:
            Dictionary with:
                - success: Boolean indicating overall success
                - tasks: List of executed tasks
                - completed_tasks: List of completed task IDs
                - failed_tasks: List of failed task IDs
                - execution_stats: Execution statistics
                - performance_metrics: Performance monitoring data
                - messages: List of status messages
                - error: Error message if failed
        """
        # Start performance monitoring
        if self.performance_monitor:
            self.performance_monitor.start()

        # Initialize state
        initial_state = MultiAgentState(
            project_request=project_request,
            workspace_id=self.workspace_id,
            tasks=[],
            dependency_graph={},
            scratchpad=self.scratchpad,
            registry=self.registry,
            executor=self.executor,
            performance_monitor=self.performance_monitor,
            cache_manager=self.cache_manager,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            performance_metrics={},
            messages=[],
            status="initialized",
            error=""
        )

        # Run workflow
        final_state = self.graph.invoke(initial_state)

        # End performance monitoring
        if self.performance_monitor:
            self.performance_monitor.end()

            # Get cache stats if available
            if self.cache_manager:
                cache_stats = self.cache_manager.get_stats()
                self.performance_monitor.metrics.cache_hits = cache_stats.get("hits", 0)
                self.performance_monitor.metrics.cache_misses = cache_stats.get("misses", 0)

            performance_metrics = self.performance_monitor.get_metrics().to_dict()

            # Print report if requested
            if show_performance_report:
                self.logger.info("Performance report", report=self.performance_monitor.generate_report())
        else:
            performance_metrics = {}

        # Format result
        return {
            "success": final_state["status"] in ["completed", "completed_with_errors"],
            "status": final_state["status"],
            "tasks": final_state["tasks"],
            "completed_tasks": final_state["completed_tasks"],
            "failed_tasks": final_state["failed_tasks"],
            "execution_stats": final_state["execution_stats"],
            "performance_metrics": performance_metrics,
            "messages": final_state["messages"],
            "error": final_state.get("error", "")
        }

    def get_workflow_visualization(self) -> str:
        """
        Get workflow graph visualization.

        Returns:
            String representation of workflow graph
        """
        try:
            from langgraph.graph import Graph
            return str(self.graph.get_graph())
        except:
            return "Workflow: plan → execute → finalize"

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MultiAgentWorkflow(workspace_id={self.workspace_id}, "
            f"max_workers={self.max_workers}, "
            f"agents={len(self.registry)})"
        )
