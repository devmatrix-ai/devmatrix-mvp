"""
Planning Agent

AI agent that breaks down user requests into actionable tasks.
Uses LangGraph for state management and Anthropic Claude for reasoning.
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from src.llm.anthropic_client import AnthropicClient


class PlanningState(TypedDict):
    """State for planning agent."""
    user_request: str
    context: dict
    plan: dict
    tasks: list
    messages: Annotated[Sequence[dict], lambda x, y: x + y]


class PlanningAgent:
    """
    Planning agent that breaks down requests into tasks.

    Usage:
        agent = PlanningAgent()
        result = agent.plan("Create a REST API for user management")
    """

    SYSTEM_PROMPT = """You are an expert technical planner for software development.

Your role is to:
1. Analyze user requests and understand their requirements
2. Break down complex requests into clear, actionable tasks
3. Consider dependencies and logical ordering of tasks
4. Provide realistic estimates and identify potential risks

Output your plan in the following JSON format:
{
    "summary": "Brief summary of the request",
    "requirements": ["List of key requirements"],
    "tasks": [
        {
            "id": 1,
            "title": "Task title",
            "description": "Detailed description",
            "dependencies": [list of task IDs this depends on],
            "estimated_time": "time estimate (e.g., '2 hours', '1 day')",
            "complexity": "low|medium|high"
        }
    ],
    "risks": ["Potential risks or challenges"],
    "next_steps": "Immediate next action to take"
}

Be thorough but concise. Focus on actionable, well-defined tasks."""

    def __init__(self, api_key: str = None):
        """
        Initialize planning agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        self.llm = AnthropicClient(api_key=api_key)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(PlanningState)

        # Add nodes
        workflow.add_node("analyze", self._analyze_request)
        workflow.add_node("generate_plan", self._generate_plan)
        workflow.add_node("validate_plan", self._validate_plan)

        # Define edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "generate_plan")
        workflow.add_edge("generate_plan", "validate_plan")
        workflow.add_edge("validate_plan", END)

        return workflow.compile()

    def _analyze_request(self, state: PlanningState) -> PlanningState:
        """Analyze user request to extract requirements."""
        user_request = state["user_request"]
        context = state.get("context", {})

        analysis_prompt = f"""Analyze this development request:

Request: {user_request}

Context: {context if context else 'No additional context provided'}

Extract and list:
1. Core requirements
2. Technical constraints
3. Success criteria
4. Implicit requirements that might not be stated

Respond in a structured format."""

        response = self.llm.generate(
            messages=[{"role": "user", "content": analysis_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.3,
        )

        state["messages"].append({
            "role": "assistant",
            "content": f"Analysis: {response['content']}"
        })

        return state

    def _generate_plan(self, state: PlanningState) -> PlanningState:
        """Generate detailed task breakdown."""
        user_request = state["user_request"]
        analysis = state["messages"][-1]["content"]

        planning_prompt = f"""Based on this analysis, create a detailed implementation plan:

Original Request: {user_request}

{analysis}

Generate a comprehensive plan following the JSON format specified in the system prompt.
Ensure tasks are:
- Specific and actionable
- Properly ordered with dependencies
- Have realistic time estimates
- Include all necessary steps (setup, implementation, testing, documentation)"""

        response = self.llm.generate(
            messages=[{"role": "user", "content": planning_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=4096,
        )

        # Try to parse JSON from response
        import json
        import re

        # Extract JSON from markdown code blocks if present
        content = response['content']
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # Try to find JSON object in response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

        try:
            plan = json.loads(content)
            state["plan"] = plan
            state["tasks"] = plan.get("tasks", [])
        except json.JSONDecodeError:
            # Fallback: store raw response
            state["plan"] = {"raw_response": response['content']}
            state["tasks"] = []

        state["messages"].append({
            "role": "assistant",
            "content": response['content']
        })

        return state

    def _validate_plan(self, state: PlanningState) -> PlanningState:
        """Validate and refine the plan."""
        plan = state.get("plan", {})

        if not plan or "raw_response" in plan:
            # Plan generation failed, return as is
            return state

        # Check for common issues
        tasks = plan.get("tasks", [])
        if not tasks:
            state["messages"].append({
                "role": "system",
                "content": "Warning: No tasks generated in plan"
            })
            return state

        # Validate dependencies
        task_ids = set(task["id"] for task in tasks)
        for task in tasks:
            for dep_id in task.get("dependencies", []):
                if dep_id not in task_ids:
                    state["messages"].append({
                        "role": "system",
                        "content": f"Warning: Task {task['id']} has invalid dependency {dep_id}"
                    })

        state["messages"].append({
            "role": "system",
            "content": f"Plan validated: {len(tasks)} tasks, {len(plan.get('risks', []))} risks identified"
        })

        return state

    def plan(self, user_request: str, context: dict = None) -> dict:
        """
        Create a plan from user request.

        Args:
            user_request: User's development request
            context: Additional context (optional)

        Returns:
            Dictionary with plan, tasks, and messages
        """
        initial_state = {
            "user_request": user_request,
            "context": context or {},
            "plan": {},
            "tasks": [],
            "messages": [],
        }

        result = self.graph.invoke(initial_state)

        return {
            "plan": result.get("plan", {}),
            "tasks": result.get("tasks", []),
            "messages": result.get("messages", []),
        }

    def format_plan(self, plan_result: dict) -> str:
        """
        Format plan result for display.

        Args:
            plan_result: Result from plan() method

        Returns:
            Formatted string representation
        """
        plan = plan_result.get("plan", {})

        if "raw_response" in plan:
            return f"Plan (raw):\n{plan['raw_response']}"

        output = []
        output.append(f"📋 Summary: {plan.get('summary', 'N/A')}\n")

        # Requirements
        reqs = plan.get("requirements", [])
        if reqs:
            output.append("✅ Requirements:")
            for req in reqs:
                output.append(f"  • {req}")
            output.append("")

        # Tasks
        tasks = plan.get("tasks", [])
        if tasks:
            output.append(f"📝 Tasks ({len(tasks)}):")
            for task in tasks:
                deps = task.get("dependencies", [])
                deps_str = f" [depends on: {', '.join(map(str, deps))}]" if deps else ""
                output.append(
                    f"  {task['id']}. {task['title']} "
                    f"({task.get('estimated_time', 'unknown')}, "
                    f"{task.get('complexity', 'unknown')} complexity){deps_str}"
                )
                output.append(f"     {task.get('description', '')}")
            output.append("")

        # Risks
        risks = plan.get("risks", [])
        if risks:
            output.append("⚠️  Risks:")
            for risk in risks:
                output.append(f"  • {risk}")
            output.append("")

        # Next steps
        next_steps = plan.get("next_steps", "")
        if next_steps:
            output.append(f"🚀 Next Steps: {next_steps}")

        return "\n".join(output)
