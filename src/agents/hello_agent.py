"""
Hello World Agent - Simple LangGraph Agent Node

This is a minimal agent node for testing LangGraph functionality.
It demonstrates the basic pattern: receive state → process → return updated state.
"""

from typing import Any
from src.state.graph_state import AgentState


def hello_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Simple agent node that greets the user.

    This node demonstrates the basic LangGraph pattern:
    1. Receive current state
    2. Process (in this case, create a greeting)
    3. Return state updates

    Args:
        state: Current AgentState from the workflow

    Returns:
        Dictionary with state updates (partial state)
    """
    user_request = state.get("user_request", "")
    workflow_id = state.get("workflow_id", "unknown")

    # Create a simple greeting message
    greeting = f"Hello! I received your request: '{user_request}'"

    # Create a message for the messages list
    message = {
        "role": "assistant",
        "content": greeting,
        "workflow_id": workflow_id,
    }

    # Return state updates
    # LangGraph will merge these updates with the existing state
    return {
        "messages": [message],
        "current_task": "greeting_complete",
        "agent_name": "hello_agent",
        "generated_code": f"# Hello World from Devmatrix!\n# Request: {user_request}\n",
    }
