"""
LangGraph State Definitions

This module defines the state schemas used in LangGraph workflows.
State is passed between nodes and modified throughout the workflow.
"""

from typing import TypedDict, Annotated, Sequence
from operator import add


class AgentState(TypedDict):
    """
    Base state for agent workflows in Devmatrix.

    This state is passed through the LangGraph workflow and modified by each node.
    Using Annotated with operator.add allows LangGraph to accumulate messages.
    """

    # User's original request
    user_request: str

    # Messages accumulated during workflow (using reducer for accumulation)
    messages: Annotated[Sequence[dict], add]

    # Current task being executed
    current_task: str

    # Generated code (if any)
    generated_code: str

    # Workflow metadata
    workflow_id: str
    agent_name: str
    project_id: str
    task_id: str

    # Error tracking
    error: str | None
    retry_count: int


class PlanningState(TypedDict):
    """
    State specific to the Planning Agent workflow.

    Used during the discovery and planning phase before code generation.
    """

    # User's original request
    user_request: str

    # Clarifying questions asked by agent
    questions: Annotated[Sequence[str], add]

    # User's answers to questions
    answers: Annotated[Sequence[str], add]

    # Generated specification
    specification: str

    # Approved by user
    approved: bool

    # Planning metadata
    planning_id: str
    created_at: str
