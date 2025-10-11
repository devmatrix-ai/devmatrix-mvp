"""
End-to-End Tests for Code Generation Agent

Tests the complete workflow from user request to generated code file,
including approval flow, git integration, and PostgreSQL logging.
"""

import pytest
import os
import time
from pathlib import Path
from unittest.mock import patch, Mock
from src.agents.code_generation_agent import CodeGenerationAgent


class TestE2ECodeGeneration:
    """End-to-end test suite for CodeGenerationAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocked LLM for E2E tests."""
        with patch('src.agents.code_generation_agent.AnthropicClient') as mock_class:
            with patch('src.agents.code_generation_agent.PostgresManager'):
                # Mock Prompt.ask to avoid stdin issues in tests
                with patch('src.agents.code_generation_agent.Prompt.ask') as mock_prompt:
                    mock_prompt.return_value = "approve"  # Default to approve

                    mock_client = Mock()
                    mock_class.return_value = mock_client
                    agent = CodeGenerationAgent()
                    agent.llm = mock_client
                    yield agent

    def test_e2e_fibonacci_generation(self, agent, tmp_path):
        """E2E: Generate fibonacci function with approval and git commit."""
        # Mock LLM responses for each step
        responses = [
            # Analysis
            {"content": "Analysis: Function to calculate fibonacci numbers\nFilename: fibonacci.py", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 30}, "stop_reason": "end_turn"},
            # Planning
            {"content": "Plan: 1. Define function signature\n2. Handle base cases (n=0, n=1)\n3. Implement recursive logic", "model": "claude", "usage": {"input_tokens": 100, "output_tokens": 50}, "stop_reason": "end_turn"},
            # Code generation
            {"content": """```python
def fibonacci(n: int) -> int:
    \"\"\"Calculate nth fibonacci number.

    Args:
        n: Position in fibonacci sequence (0-indexed)

    Returns:
        The nth fibonacci number
    \"\"\"
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
```""", "model": "claude", "usage": {"input_tokens": 200, "output_tokens": 150}, "stop_reason": "end_turn"},
            # Review
            {"content": "Score: 8.5/10\nFeedback: Clean implementation with proper docstring and type hints. Good handling of base cases.", "model": "claude", "usage": {"input_tokens": 150, "output_tokens": 50}, "stop_reason": "end_turn"},
            # Commit message
            {"content": "feat: add fibonacci calculator function", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 10}, "stop_reason": "end_turn"}
        ]

        agent.llm.generate.side_effect = responses

        # Mock human approval (auto-approve)
        with patch.object(agent, '_human_approval') as mock_approval:
            def auto_approve(state):
                state["approval_status"] = "approved"
                return state
            mock_approval.side_effect = auto_approve

            # Mock git operations
            with patch('src.agents.code_generation_agent.GitOperations') as mock_git_class:
                with patch('subprocess.run'):
                    mock_git = Mock()
                    mock_git.get_status.side_effect = ValueError("Not a git repo")
                    mock_git.commit.return_value = {"hash": "abc123def456"}
                    mock_git_class.return_value = mock_git

                    # Execute E2E workflow
                    start_time = time.time()

                    result = agent.generate(
                        user_request="Create a fibonacci function",
                        workspace_id=f"e2e-test-{tmp_path.name}",
                        git_enabled=True
                    )

                    elapsed = time.time() - start_time

                    # Verify results
                    assert result["approval_status"] == "approved"
                    assert result["file_written"] is True
                    assert "fibonacci.py" in result["file_path"]
                    assert "def fibonacci" in result["generated_code"]
                    assert result["quality_score"] == 8.5
                    assert result["git_committed"] is True
                    assert result["git_commit_message"] == "feat: add fibonacci calculator function"

                    # Performance check: should complete in <10 seconds
                    assert elapsed < 10.0, f"E2E test took {elapsed:.2f}s, expected <10s"

    def test_e2e_class_generation(self, agent, tmp_path):
        """E2E: Generate a class with methods."""
        responses = [
            # Analysis
            {"content": "Analysis: Calculator class with basic operations\nFilename: calculator.py", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 30}, "stop_reason": "end_turn"},
            # Planning
            {"content": "Plan: 1. Create Calculator class\n2. Add methods: add, subtract, multiply, divide\n3. Include error handling for division by zero", "model": "claude", "usage": {"input_tokens": 100, "output_tokens": 50}, "stop_reason": "end_turn"},
            # Code generation
            {"content": """```python
class Calculator:
    \"\"\"Simple calculator with basic arithmetic operations.\"\"\"

    def add(self, a: float, b: float) -> float:
        \"\"\"Add two numbers.\"\"\"
        return a + b

    def subtract(self, a: float, b: float) -> float:
        \"\"\"Subtract b from a.\"\"\"
        return a - b

    def multiply(self, a: float, b: float) -> float:
        \"\"\"Multiply two numbers.\"\"\"
        return a * b

    def divide(self, a: float, b: float) -> float:
        \"\"\"Divide a by b.

        Raises:
            ValueError: If b is zero
        \"\"\"
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
```""", "model": "claude", "usage": {"input_tokens": 200, "output_tokens": 200}, "stop_reason": "end_turn"},
            # Review
            {"content": "Score: 9.0/10\nFeedback: Excellent implementation with proper error handling and comprehensive docstrings.", "model": "claude", "usage": {"input_tokens": 150, "output_tokens": 40}, "stop_reason": "end_turn"},
            # Commit message
            {"content": "feat: add Calculator class with basic operations", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 10}, "stop_reason": "end_turn"}
        ]

        agent.llm.generate.side_effect = responses

        with patch.object(agent, '_human_approval') as mock_approval:
            def auto_approve(state):
                state["approval_status"] = "approved"
                return state
            mock_approval.side_effect = auto_approve

            with patch('src.agents.code_generation_agent.GitOperations') as mock_git_class:
                with patch('subprocess.run'):
                    mock_git = Mock()
                    mock_git.get_status.side_effect = ValueError("Not a git repo")
                    mock_git.commit.return_value = {"hash": "def456abc789"}
                    mock_git_class.return_value = mock_git

                    result = agent.generate(
                        user_request="Create a Calculator class",
                        workspace_id=f"e2e-test-{tmp_path.name}",
                        git_enabled=True
                    )

                    assert result["approval_status"] == "approved"
                    assert "class Calculator" in result["generated_code"]
                    assert "def add" in result["generated_code"]
                    assert "def divide" in result["generated_code"]
                    assert result["quality_score"] == 9.0
                    assert result["git_committed"] is True

    def test_e2e_feedback_loop(self, agent, tmp_path):
        """E2E: Test feedback loop with modification request."""
        responses = [
            # Analysis
            {"content": "Analysis: Simple greeting function\nFilename: greeter.py", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 20}, "stop_reason": "end_turn"},
            # Planning
            {"content": "Plan: Create a function that greets a user by name", "model": "claude", "usage": {"input_tokens": 80, "output_tokens": 30}, "stop_reason": "end_turn"},
            # First code generation (without type hints)
            {"content": """```python
def greet(name):
    return f"Hello, {name}!"
```""", "model": "claude", "usage": {"input_tokens": 150, "output_tokens": 50}, "stop_reason": "end_turn"},
            # Review
            {"content": "Score: 6.0/10\nFeedback: Missing type hints and docstring.", "model": "claude", "usage": {"input_tokens": 100, "output_tokens": 30}, "stop_reason": "end_turn"},
            # Second code generation (WITH type hints after feedback)
            {"content": """```python
def greet(name: str) -> str:
    \"\"\"Greet a person by name.

    Args:
        name: Person's name

    Returns:
        Greeting message
    \"\"\"
    return f"Hello, {name}!"
```""", "model": "claude", "usage": {"input_tokens": 180, "output_tokens": 80}, "stop_reason": "end_turn"},
            # Review (second attempt)
            {"content": "Score: 9.0/10\nFeedback: Much better with type hints and docstring!", "model": "claude", "usage": {"input_tokens": 120, "output_tokens": 30}, "stop_reason": "end_turn"},
            # Commit message
            {"content": "feat: add greeter function with type hints", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 10}, "stop_reason": "end_turn"}
        ]

        agent.llm.generate.side_effect = responses

        # Mock Prompt.ask to return different values: first modify, then feedback, then approve
        call_count = [0]

        def prompt_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "modify"  # First call: request modification
            elif call_count[0] == 2:
                return "Add type hints and docstring"  # Second call: feedback text
            else:
                return "approve"  # Third call: approve the regenerated code

        with patch('src.agents.code_generation_agent.Prompt.ask', side_effect=prompt_side_effect):
            with patch('src.agents.code_generation_agent.GitOperations') as mock_git_class:
                with patch('subprocess.run'):
                    mock_git = Mock()
                    mock_git.get_status.side_effect = ValueError("Not a git repo")
                    mock_git.commit.return_value = {"hash": "feedback123"}
                    mock_git_class.return_value = mock_git

                    result = agent.generate(
                        user_request="Create a greeting function",
                        workspace_id=f"e2e-test-{tmp_path.name}",
                        git_enabled=True
                    )

                    # Should have gone through feedback loop
                    assert result["approval_status"] == "approved"
                    assert "name: str" in result["generated_code"]
                    assert '"""' in result["generated_code"]
                    assert result["quality_score"] == 9.0

                    # Should have been called three times (modify + feedback + approve)
                    assert call_count[0] == 3

    def test_e2e_rejection_flow(self, agent, tmp_path):
        """E2E: Test rejection flow (no file written)."""
        responses = [
            # Analysis
            {"content": "Analysis: Bad code\nFilename: bad.py", "model": "claude", "usage": {"input_tokens": 30, "output_tokens": 20}, "stop_reason": "end_turn"},
            # Planning
            {"content": "Plan: Write bad code", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 20}, "stop_reason": "end_turn"},
            # Code generation
            {"content": """```python
def bad():
    pass
```""", "model": "claude", "usage": {"input_tokens": 100, "output_tokens": 30}, "stop_reason": "end_turn"},
            # Review
            {"content": "Score: 3.0/10\nFeedback: This code is too simplistic and doesn't do anything useful.", "model": "claude", "usage": {"input_tokens": 80, "output_tokens": 30}, "stop_reason": "end_turn"}
        ]

        agent.llm.generate.side_effect = responses

        # Mock Prompt.ask to return "reject"
        with patch('src.agents.code_generation_agent.Prompt.ask', return_value="reject"):
            result = agent.generate(
                user_request="Create bad code",
                workspace_id=f"e2e-test-{tmp_path.name}",
                git_enabled=True
            )

            # Should be rejected
            assert result["approval_status"] == "rejected"
            assert result["file_written"] is False
            assert result["git_committed"] is False
            assert result["file_path"] == ""

    def test_e2e_without_git(self, agent, tmp_path):
        """E2E: Generate code without git integration."""
        responses = [
            # Analysis
            {"content": "Analysis: Simple add function\nFilename: math_utils.py", "model": "claude", "usage": {"input_tokens": 40, "output_tokens": 20}, "stop_reason": "end_turn"},
            # Planning
            {"content": "Plan: Create add function with type hints", "model": "claude", "usage": {"input_tokens": 70, "output_tokens": 30}, "stop_reason": "end_turn"},
            # Code generation
            {"content": """```python
def add(a: int, b: int) -> int:
    \"\"\"Add two integers.\"\"\"
    return a + b
```""", "model": "claude", "usage": {"input_tokens": 120, "output_tokens": 50}, "stop_reason": "end_turn"},
            # Review
            {"content": "Score: 8.0/10\nFeedback: Simple and clean implementation.", "model": "claude", "usage": {"input_tokens": 90, "output_tokens": 25}, "stop_reason": "end_turn"}
        ]

        agent.llm.generate.side_effect = responses

        with patch.object(agent, '_human_approval') as mock_approval:
            def auto_approve(state):
                state["approval_status"] = "approved"
                return state
            mock_approval.side_effect = auto_approve

            result = agent.generate(
                user_request="Create an add function",
                workspace_id=f"e2e-test-{tmp_path.name}",
                git_enabled=False  # Git disabled
            )

            assert result["approval_status"] == "approved"
            assert result["file_written"] is True
            assert result["git_committed"] is False
            assert result["git_commit_hash"] == ""
            assert result["git_commit_message"] == ""

    def test_e2e_performance_benchmark(self, agent, tmp_path):
        """E2E: Performance test - should complete in <10 seconds."""
        responses = [
            {"content": "Analysis: Performance test\nFilename: perf.py", "model": "claude", "usage": {"input_tokens": 30, "output_tokens": 15}, "stop_reason": "end_turn"},
            {"content": "Plan: Simple function", "model": "claude", "usage": {"input_tokens": 50, "output_tokens": 20}, "stop_reason": "end_turn"},
            {"content": "```python\ndef perf(): return True\n```", "model": "claude", "usage": {"input_tokens": 80, "output_tokens": 20}, "stop_reason": "end_turn"},
            {"content": "Score: 7.0/10\nFeedback: Works.", "model": "claude", "usage": {"input_tokens": 60, "output_tokens": 15}, "stop_reason": "end_turn"},
            {"content": "feat: add performance test function", "model": "claude", "usage": {"input_tokens": 40, "output_tokens": 8}, "stop_reason": "end_turn"}
        ]

        agent.llm.generate.side_effect = responses

        with patch.object(agent, '_human_approval') as mock_approval:
            def auto_approve(state):
                state["approval_status"] = "approved"
                return state
            mock_approval.side_effect = auto_approve

            with patch('src.agents.code_generation_agent.GitOperations') as mock_git_class:
                with patch('subprocess.run'):
                    mock_git = Mock()
                    mock_git.get_status.side_effect = ValueError("Not a git repo")
                    mock_git.commit.return_value = {"hash": "perf123"}
                    mock_git_class.return_value = mock_git

                    # Benchmark: run 3 times and check average
                    times = []
                    for i in range(3):
                        # Reset side_effect for each run
                        agent.llm.generate.side_effect = responses.copy()

                        start = time.time()
                        result = agent.generate(
                            user_request="Create performance test",
                            workspace_id=f"e2e-perf-{tmp_path.name}-{i}",
                            git_enabled=True
                        )
                        elapsed = time.time() - start
                        times.append(elapsed)

                        assert result["approval_status"] == "approved"

                    avg_time = sum(times) / len(times)
                    max_time = max(times)

                    # Performance requirements
                    assert avg_time < 5.0, f"Average time {avg_time:.2f}s exceeds 5s"
                    assert max_time < 10.0, f"Max time {max_time:.2f}s exceeds 10s"

                    print(f"\n✓ Performance: avg={avg_time:.2f}s, max={max_time:.2f}s, min={min(times):.2f}s")
