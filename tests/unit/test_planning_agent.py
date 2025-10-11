"""
Tests for Planning Agent with LangGraph
"""

import json
import pytest
from unittest.mock import Mock, patch
from src.agents.planning_agent import PlanningAgent, PlanningState


class TestPlanningAgent:
    """Test suite for PlanningAgent."""

    @pytest.fixture
    def mock_llm_client(self, monkeypatch):
        """Mock AnthropicClient for testing."""
        mock_client = Mock()

        # Default response for analysis
        mock_client.generate.return_value = {
            "content": "Requirements: User authentication, data storage",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "stop_reason": "end_turn"
        }

        return mock_client

    @pytest.fixture
    def agent(self, mock_llm_client, monkeypatch):
        """Create PlanningAgent with mocked LLM."""
        with patch('src.agents.planning_agent.AnthropicClient') as mock_class:
            mock_class.return_value = mock_llm_client
            agent = PlanningAgent(api_key="test_key")
            return agent

    def test_init_with_api_key(self):
        """Test agent initialization with API key."""
        with patch('src.agents.planning_agent.AnthropicClient') as mock_class:
            agent = PlanningAgent(api_key="test_key_123")
            mock_class.assert_called_once_with(api_key="test_key_123")
            assert agent.graph is not None

    def test_init_without_api_key(self):
        """Test agent initialization without API key uses env var."""
        with patch('src.agents.planning_agent.AnthropicClient') as mock_class:
            agent = PlanningAgent()
            mock_class.assert_called_once_with(api_key=None)

    def test_analyze_request(self, agent, mock_llm_client):
        """Test request analysis step."""
        state = PlanningState(
            user_request="Create a REST API",
            context={},
            plan={},
            tasks=[],
            messages=[]
        )

        mock_llm_client.generate.return_value = {
            "content": "Core requirements: API endpoints, authentication",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 50, "output_tokens": 30},
            "stop_reason": "end_turn"
        }

        result = agent._analyze_request(state)

        assert len(result["messages"]) == 1
        assert "Analysis:" in result["messages"][0]["content"]
        assert "API endpoints" in result["messages"][0]["content"]

        # Verify LLM was called with correct prompt
        mock_llm_client.generate.assert_called_once()
        call_args = mock_llm_client.generate.call_args
        assert "Create a REST API" in call_args.kwargs["messages"][0]["content"]
        assert call_args.kwargs["temperature"] == 0.3

    def test_generate_plan_with_valid_json(self, agent, mock_llm_client):
        """Test plan generation with valid JSON response."""
        state = PlanningState(
            user_request="Create a REST API",
            context={},
            plan={},
            tasks=[],
            messages=[{"role": "assistant", "content": "Analysis complete"}]
        )

        plan_json = {
            "summary": "REST API development",
            "requirements": ["Authentication", "Database"],
            "tasks": [
                {
                    "id": 1,
                    "title": "Setup project",
                    "description": "Initialize project structure",
                    "dependencies": [],
                    "estimated_time": "2 hours",
                    "complexity": "low"
                },
                {
                    "id": 2,
                    "title": "Create API endpoints",
                    "description": "Implement REST endpoints",
                    "dependencies": [1],
                    "estimated_time": "1 day",
                    "complexity": "medium"
                }
            ],
            "risks": ["Security vulnerabilities"],
            "next_steps": "Setup development environment"
        }

        mock_llm_client.generate.return_value = {
            "content": f"```json\n{json.dumps(plan_json)}\n```",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 200, "output_tokens": 150},
            "stop_reason": "end_turn"
        }

        result = agent._generate_plan(state)

        assert result["plan"] == plan_json
        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["title"] == "Setup project"
        assert result["tasks"][1]["dependencies"] == [1]

    def test_generate_plan_json_without_code_block(self, agent, mock_llm_client):
        """Test plan generation with JSON not in code block."""
        state = PlanningState(
            user_request="Create API",
            context={},
            plan={},
            tasks=[],
            messages=[{"role": "assistant", "content": "Analysis"}]
        )

        plan_json = {
            "summary": "API development",
            "requirements": ["Auth"],
            "tasks": [{"id": 1, "title": "Setup", "dependencies": [],
                      "estimated_time": "1h", "complexity": "low"}],
            "risks": [],
            "next_steps": "Start coding"
        }

        mock_llm_client.generate.return_value = {
            "content": f"Here's the plan: {json.dumps(plan_json)}",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 80},
            "stop_reason": "end_turn"
        }

        result = agent._generate_plan(state)

        assert result["plan"] == plan_json
        assert len(result["tasks"]) == 1

    def test_generate_plan_invalid_json(self, agent, mock_llm_client):
        """Test plan generation with invalid JSON response."""
        state = PlanningState(
            user_request="Create API",
            context={},
            plan={},
            tasks=[],
            messages=[{"role": "assistant", "content": "Analysis"}]
        )

        mock_llm_client.generate.return_value = {
            "content": "This is not valid JSON at all",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "stop_reason": "end_turn"
        }

        result = agent._generate_plan(state)

        # Should fallback to raw response
        assert "raw_response" in result["plan"]
        assert result["tasks"] == []
        assert result["plan"]["raw_response"] == "This is not valid JSON at all"

    def test_validate_plan_success(self, agent):
        """Test plan validation with valid plan."""
        state = PlanningState(
            user_request="Create API",
            context={},
            plan={
                "summary": "API development",
                "tasks": [
                    {"id": 1, "title": "Setup", "dependencies": []},
                    {"id": 2, "title": "Implement", "dependencies": [1]}
                ],
                "risks": ["Security"]
            },
            tasks=[
                {"id": 1, "title": "Setup", "dependencies": []},
                {"id": 2, "title": "Implement", "dependencies": [1]}
            ],
            messages=[]
        )

        result = agent._validate_plan(state)

        # Should add validation message
        assert len(result["messages"]) == 1
        assert "Plan validated" in result["messages"][0]["content"]
        assert "2 tasks" in result["messages"][0]["content"]
        assert "1 risks" in result["messages"][0]["content"]

    def test_validate_plan_no_tasks(self, agent):
        """Test plan validation with no tasks."""
        state = PlanningState(
            user_request="Create API",
            context={},
            plan={"summary": "API", "tasks": []},
            tasks=[],
            messages=[]
        )

        result = agent._validate_plan(state)

        # Should add warning message
        assert len(result["messages"]) == 1
        assert "Warning: No tasks generated" in result["messages"][0]["content"]

    def test_validate_plan_invalid_dependencies(self, agent):
        """Test plan validation with invalid task dependencies."""
        state = PlanningState(
            user_request="Create API",
            context={},
            plan={
                "tasks": [
                    {"id": 1, "title": "Setup", "dependencies": []},
                    {"id": 2, "title": "Implement", "dependencies": [99]}  # Invalid
                ]
            },
            tasks=[
                {"id": 1, "title": "Setup", "dependencies": []},
                {"id": 2, "title": "Implement", "dependencies": [99]}
            ],
            messages=[]
        )

        result = agent._validate_plan(state)

        # Should add warning about invalid dependency
        warnings = [msg for msg in result["messages"] if "Warning" in msg["content"]]
        assert len(warnings) == 1
        assert "invalid dependency 99" in warnings[0]["content"]

    def test_validate_plan_raw_response(self, agent):
        """Test validation with raw response (failed JSON parsing)."""
        state = PlanningState(
            user_request="Create API",
            context={},
            plan={"raw_response": "Not JSON"},
            tasks=[],
            messages=[]
        )

        result = agent._validate_plan(state)

        # Should return state unchanged
        assert result["plan"] == {"raw_response": "Not JSON"}
        assert len(result["messages"]) == 0

    def test_plan_full_workflow(self, agent, mock_llm_client):
        """Test complete planning workflow."""
        # Mock LLM responses for each step
        responses = [
            # Analysis step
            {
                "content": "Requirements: Authentication, data storage, API endpoints",
                "model": "claude-3-5-sonnet-20241022",
                "usage": {"input_tokens": 50, "output_tokens": 30},
                "stop_reason": "end_turn"
            },
            # Plan generation step
            {
                "content": json.dumps({
                    "summary": "User management API",
                    "requirements": ["Auth", "Database"],
                    "tasks": [
                        {"id": 1, "title": "Setup", "dependencies": [],
                         "estimated_time": "1h", "complexity": "low"},
                        {"id": 2, "title": "Implement", "dependencies": [1],
                         "estimated_time": "1d", "complexity": "medium"}
                    ],
                    "risks": ["Security"],
                    "next_steps": "Initialize project"
                }),
                "model": "claude-3-5-sonnet-20241022",
                "usage": {"input_tokens": 200, "output_tokens": 150},
                "stop_reason": "end_turn"
            }
        ]
        mock_llm_client.generate.side_effect = responses

        result = agent.plan(
            user_request="Create a user management API",
            context={"framework": "FastAPI"}
        )

        # Check result structure
        assert "plan" in result
        assert "tasks" in result
        assert "messages" in result

        # Check plan content
        assert result["plan"]["summary"] == "User management API"
        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["title"] == "Setup"
        assert result["tasks"][1]["dependencies"] == [1]

        # Check messages
        assert len(result["messages"]) > 0

    def test_format_plan_with_valid_plan(self, agent):
        """Test plan formatting for display."""
        plan_result = {
            "plan": {
                "summary": "REST API development",
                "requirements": ["Authentication", "Database"],
                "tasks": [
                    {
                        "id": 1,
                        "title": "Setup project",
                        "description": "Initialize structure",
                        "dependencies": [],
                        "estimated_time": "2 hours",
                        "complexity": "low"
                    },
                    {
                        "id": 2,
                        "title": "Create endpoints",
                        "description": "Implement REST endpoints",
                        "dependencies": [1],
                        "estimated_time": "1 day",
                        "complexity": "medium"
                    }
                ],
                "risks": ["Security vulnerabilities", "Performance issues"],
                "next_steps": "Setup development environment"
            },
            "tasks": [],
            "messages": []
        }

        formatted = agent.format_plan(plan_result)

        # Check formatted output contains all sections
        assert "Summary: REST API development" in formatted
        assert "Requirements:" in formatted
        assert "Authentication" in formatted
        assert "Tasks (2):" in formatted
        assert "1. Setup project" in formatted
        assert "(2 hours, low complexity)" in formatted
        assert "2. Create endpoints" in formatted
        assert "[depends on: 1]" in formatted
        assert "Risks:" in formatted
        assert "Security vulnerabilities" in formatted
        assert "Next Steps: Setup development environment" in formatted

    def test_format_plan_with_raw_response(self, agent):
        """Test formatting of raw response (failed JSON parsing)."""
        plan_result = {
            "plan": {"raw_response": "This is the raw plan text"},
            "tasks": [],
            "messages": []
        }

        formatted = agent.format_plan(plan_result)

        assert "Plan (raw):" in formatted
        assert "This is the raw plan text" in formatted

    def test_format_plan_minimal(self, agent):
        """Test formatting with minimal plan data."""
        plan_result = {
            "plan": {
                "summary": "Minimal plan"
            },
            "tasks": [],
            "messages": []
        }

        formatted = agent.format_plan(plan_result)

        assert "Summary: Minimal plan" in formatted
        # Should handle missing sections gracefully

    def test_system_prompt_structure(self):
        """Test that system prompt has required structure."""
        prompt = PlanningAgent.SYSTEM_PROMPT

        # Check key elements
        assert "technical planner" in prompt.lower()
        assert "json" in prompt.lower()
        assert "summary" in prompt
        assert "requirements" in prompt
        assert "tasks" in prompt
        assert "risks" in prompt
        assert "next_steps" in prompt
        assert "dependencies" in prompt
