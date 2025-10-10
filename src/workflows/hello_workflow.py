"""
Hello World Workflow - Simple LangGraph Workflow

This module demonstrates a minimal LangGraph workflow with:
- State definition
- Single agent node
- Basic workflow execution

This is the foundation for more complex multi-agent workflows.
"""

from langgraph.graph import StateGraph, END
from src.state.graph_state import AgentState
from src.agents.hello_agent import hello_agent_node


def create_hello_workflow() -> StateGraph:
    """
    Create a simple "Hello World" LangGraph workflow.

    Workflow structure:
    START → hello_agent → END

    Returns:
        Compiled LangGraph workflow ready for execution
    """
    # Create a StateGraph with AgentState schema
    workflow = StateGraph(AgentState)

    # Add the hello_agent node
    workflow.add_node("hello_agent", hello_agent_node)

    # Define the workflow edges (flow)
    workflow.set_entry_point("hello_agent")  # Start with hello_agent
    workflow.add_edge("hello_agent", END)  # Then end

    # Compile the workflow
    return workflow.compile()


def run_hello_workflow(user_request: str, workflow_id: str = "test-001") -> AgentState:
    """
    Execute the hello world workflow with a user request.

    Args:
        user_request: The user's input request
        workflow_id: Unique identifier for this workflow execution

    Returns:
        Final state after workflow execution
    """
    # Create the compiled workflow
    app = create_hello_workflow()

    # Initialize the starting state
    initial_state: AgentState = {
        "user_request": user_request,
        "messages": [],
        "current_task": "starting",
        "generated_code": "",
        "workflow_id": workflow_id,
        "agent_name": "",
        "error": None,
        "retry_count": 0,
    }

    # Execute the workflow
    final_state = app.invoke(initial_state)

    return final_state
