"""
Tests for Code Generation Agent with Human-in-Loop
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agents.code_generation_agent import CodeGenerationAgent, CodeGenState


class TestCodeGenerationAgent:
    """Test suite for CodeGenerationAgent."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock AnthropicClient for testing."""
        mock_client = Mock()
        mock_client.generate.return_value = {
            "content": "Test response",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "stop_reason": "end_turn"
        }
        return mock_client

    @pytest.fixture
    def agent(self, mock_llm_client, monkeypatch):
        """Create CodeGenerationAgent with mocked LLM."""
        with patch('src.agents.code_generation_agent.AnthropicClient') as mock_class:
            mock_class.return_value = mock_llm_client
            with patch('src.agents.code_generation_agent.PostgresManager'):
                agent = CodeGenerationAgent(api_key="test_key")
                return agent

    def test_init(self):
        """Test agent initialization."""
        with patch('src.agents.code_generation_agent.AnthropicClient'):
            with patch('src.agents.code_generation_agent.PostgresManager'):
                agent = CodeGenerationAgent(api_key="test_key_123")
                assert agent.graph is not None
                assert agent.console is not None
                assert agent.llm is not None

    def test_analyze_request(self, agent, mock_llm_client):
        """Test request analysis step."""
        mock_llm_client.generate.return_value = {
            "content": "Analysis: Function to calculate fibonacci\nFilename: fibonacci.py",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 50, "output_tokens": 30},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create a fibonacci function",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._analyze_request(state)

        assert len(result["messages"]) == 1
        assert "Analysis:" in result["messages"][0]["content"]
        assert result["target_filename"] == "fibonacci.py"

    def test_analyze_request_default_filename(self, agent, mock_llm_client):
        """Test analysis with default filename when not in response."""
        mock_llm_client.generate.return_value = {
            "content": "Analysis: Create a calculator",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 50, "output_tokens": 30},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create calculator",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._analyze_request(state)
        assert result["target_filename"] == "generated_code.py"  # default

    def test_create_plan(self, agent, mock_llm_client):
        """Test plan creation step."""
        mock_llm_client.generate.return_value = {
            "content": "Implementation plan:\n1. Define function signature\n2. Implement base cases\n3. Add recursive logic",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 80},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create fibonacci",
            context={},
            messages=[{"role": "assistant", "content": "Analysis done"}],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="fib.py",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._create_plan(state)

        assert "plan" in result
        assert "description" in result["plan"]
        assert len(result["messages"]) == 2

    def test_generate_code(self, agent, mock_llm_client):
        """Test code generation step."""
        code_content = """def fibonacci(n: int) -> int:
    \"\"\"Calculate fibonacci number.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""

        mock_llm_client.generate.return_value = {
            "content": f"```python\n{code_content}\n```",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 200, "output_tokens": 150},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create fibonacci",
            context={},
            messages=[],
            plan={"description": "Create recursive fibonacci function"},
            tasks=[],
            generated_code="",
            target_filename="fib.py",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._generate_code(state)

        assert "generated_code" in result
        assert "def fibonacci" in result["generated_code"]
        assert "```python" not in result["generated_code"]  # Should be extracted

    def test_generate_code_with_feedback(self, agent, mock_llm_client):
        """Test code regeneration with user feedback."""
        mock_llm_client.generate.return_value = {
            "content": "```python\n# Updated code\n```",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 200, "output_tokens": 100},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create fibonacci",
            context={},
            messages=[],
            plan={"description": "Plan"},
            tasks=[],
            generated_code="old code",
            target_filename="fib.py",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="needs_modification",
            user_feedback="Add type hints and docstring",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._generate_code(state)

        # Verify feedback was included in prompt
        call_args = mock_llm_client.generate.call_args
        assert "Add type hints" in call_args.kwargs["messages"][0]["content"]

    def test_review_code(self, agent, mock_llm_client):
        """Test code review step."""
        mock_llm_client.generate.return_value = {
            "content": "Score: 8.5/10\nFeedback: Good code with proper documentation.",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 150, "output_tokens": 50},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create fibonacci",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="def fibonacci(n): return n",
            target_filename="fib.py",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._review_code(state)

        assert result["code_quality_score"] == 8.5
        assert "review_feedback" in result
        assert "Good code" in result["review_feedback"]

    def test_review_code_no_score_in_response(self, agent, mock_llm_client):
        """Test review handles missing score."""
        mock_llm_client.generate.return_value = {
            "content": "Feedback: Code looks good",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 150, "output_tokens": 30},
            "stop_reason": "end_turn"
        }

        state = CodeGenState(
            user_request="Create fibonacci",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="def fibonacci(n): return n",
            target_filename="fib.py",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="pending",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        result = agent._review_code(state)

        assert result["code_quality_score"] == 7.0  # Default score

    def test_route_approval(self, agent):
        """Test approval routing logic."""
        state_approved = CodeGenState(
            user_request="",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="approved",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        assert agent._route_approval(state_approved) == "approved"

        state_rejected = dict(state_approved)
        state_rejected["approval_status"] = "rejected"
        assert agent._route_approval(state_rejected) == "rejected"

        state_modify = dict(state_approved)
        state_modify["approval_status"] = "needs_modification"
        assert agent._route_approval(state_modify) == "needs_modification"

    def test_write_file_success(self, agent):
        """Test successful file writing."""
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.write_file.return_value = "/tmp/test/fibonacci.py"
            mock_ws_class.return_value = mock_ws

            state = CodeGenState(
                user_request="",
                context={},
                messages=[],
                plan={},
                tasks=[],
                generated_code="def fib(): pass",
                target_filename="fibonacci.py",
                review_feedback="",
                code_quality_score=0.0,
                approval_status="approved",
                user_feedback="",
                workspace_id="test_workspace",
                file_written=False,
                file_path="",
                decision_id=""
            )

            result = agent._write_file(state)

            assert result["file_written"] is True
            assert result["file_path"] == "/tmp/test/fibonacci.py"
            mock_ws.write_file.assert_called_once_with("fibonacci.py", "def fib(): pass")

    def test_write_file_creates_workspace(self, agent):
        """Test workspace creation if doesn't exist."""
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = False
            mock_ws.write_file.return_value = "/tmp/test/code.py"
            mock_ws_class.return_value = mock_ws

            state = CodeGenState(
                user_request="",
                context={},
                messages=[],
                plan={},
                tasks=[],
                generated_code="code",
                target_filename="code.py",
                review_feedback="",
                code_quality_score=0.0,
                approval_status="approved",
                user_feedback="",
                workspace_id="new_workspace",
                file_written=False,
                file_path="",
                decision_id=""
            )

            result = agent._write_file(state)

            mock_ws.create.assert_called_once()
            assert result["file_written"] is True

    def test_write_file_error_handling(self, agent):
        """Test file writing error handling."""
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws_class.side_effect = Exception("Write error")

            state = CodeGenState(
                user_request="",
                context={},
                messages=[],
                plan={},
                tasks=[],
                generated_code="code",
                target_filename="code.py",
                review_feedback="",
                code_quality_score=0.0,
                approval_status="approved",
                user_feedback="",
                workspace_id="test",
                file_written=False,
                file_path="",
                decision_id=""
            )

            result = agent._write_file(state)

            assert result["file_written"] is False
            assert result["file_path"] == ""

    def test_log_decision_success(self, agent):
        """Test decision logging to PostgreSQL."""
        mock_postgres = Mock()
        mock_postgres.create_project.return_value = "project-123"
        mock_postgres.create_task.return_value = "task-456"
        mock_postgres.log_decision.return_value = "decision-789"
        agent.postgres = mock_postgres

        state = CodeGenState(
            user_request="Create fibonacci",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="def fib(): pass",
            target_filename="fib.py",
            review_feedback="",
            code_quality_score=8.5,
            approval_status="approved",
            user_feedback="Looks good",
            workspace_id="test_ws",
            file_written=True,
            file_path="/tmp/test/fib.py",
            decision_id=""
        )

        result = agent._log_decision(state)

        assert result["decision_id"] == "decision-789"
        mock_postgres.create_project.assert_called_once()
        mock_postgres.create_task.assert_called_once()
        mock_postgres.log_decision.assert_called_once()

    def test_log_decision_error_handling(self, agent):
        """Test decision logging handles errors gracefully."""
        mock_postgres = Mock()
        mock_postgres.create_project.side_effect = Exception("DB error")
        agent.postgres = mock_postgres

        state = CodeGenState(
            user_request="Test",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="code",
            target_filename="test.py",
            review_feedback="",
            code_quality_score=7.0,
            approval_status="rejected",
            user_feedback="",
            workspace_id="test",
            file_written=False,
            file_path="",
            decision_id=""
        )

        # Should not raise exception
        result = agent._log_decision(state)
        assert "decision_id" in result

    def test_generate_auto_workspace_id(self, agent, mock_llm_client):
        """Test generate creates workspace ID if not provided."""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "generated_code": "code",
                "approval_status": "approved",
                "workspace_id": "auto-generated"
            }

            result = agent.generate(user_request="Test")

            assert "workspace_id" in result
            # Verify workspace_id was passed to graph
            call_args = mock_graph.invoke.call_args[0][0]
            assert "workspace_id" in call_args

    def test_generate_with_custom_workspace(self, agent, mock_llm_client):
        """Test generate with custom workspace ID."""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "generated_code": "code",
                "approval_status": "approved",
                "workspace_id": "my-workspace"
            }

            result = agent.generate(
                user_request="Test",
                workspace_id="my-workspace"
            )

            assert result["workspace_id"] == "my-workspace"

    def test_generate_return_structure(self, agent):
        """Test generate returns expected structure."""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "generated_code": "def test(): pass",
                "target_filename": "test.py",
                "approval_status": "approved",
                "file_written": True,
                "file_path": "/tmp/test.py",
                "code_quality_score": 9.0,
                "workspace_id": "test-ws",
                "messages": []
            }

            result = agent.generate(user_request="Create test function")

            # Verify all expected keys
            assert "generated_code" in result
            assert "target_filename" in result
            assert "approval_status" in result
            assert "file_written" in result
            assert "file_path" in result
            assert "quality_score" in result
            assert "workspace_id" in result
            assert "messages" in result

    def test_system_prompt_structure(self):
        """Test system prompt has required elements."""
        prompt = CodeGenerationAgent.SYSTEM_PROMPT

        assert "Python" in prompt
        assert "code" in prompt.lower()
        assert "docstring" in prompt.lower()
        assert "type hint" in prompt.lower()
        assert "PEP 8" in prompt

    def test_route_git_enabled(self, agent):
        """Test git routing when git is enabled and file written."""
        state = CodeGenState(
            user_request="",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="approved",
            user_feedback="",
            workspace_id="test",
            file_written=True,
            file_path="/tmp/test.py",
            git_enabled=True,
            git_commit_message="",
            git_commit_hash="",
            git_committed=False,
            decision_id=""
        )

        assert agent._route_git(state) == "git_commit"

    def test_route_git_disabled(self, agent):
        """Test git routing when git is disabled."""
        state = CodeGenState(
            user_request="",
            context={},
            messages=[],
            plan={},
            tasks=[],
            generated_code="",
            target_filename="",
            review_feedback="",
            code_quality_score=0.0,
            approval_status="approved",
            user_feedback="",
            workspace_id="test",
            file_written=True,
            file_path="/tmp/test.py",
            git_enabled=False,
            git_commit_message="",
            git_commit_hash="",
            git_committed=False,
            decision_id=""
        )

        assert agent._route_git(state) == "skip_git"

    def test_git_commit_success(self, agent, mock_llm_client):
        """Test successful git commit."""
        mock_llm_client.generate.return_value = {
            "content": "feat: add calculator function",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 50, "output_tokens": 10},
            "stop_reason": "end_turn"
        }

        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws_class:
            with patch('src.agents.code_generation_agent.GitOperations') as mock_git_class:
                with patch('subprocess.run') as mock_subprocess:
                    # Setup mocks
                    mock_ws = Mock()
                    mock_ws.base_path = "/tmp/test_workspace"
                    mock_ws_class.return_value = mock_ws

                    mock_git = Mock()
                    mock_git.get_status.side_effect = ValueError("Not a git repo")  # First call fails
                    mock_git.commit.return_value = {"hash": "abc123def456"}
                    mock_git_class.return_value = mock_git

                    state = CodeGenState(
                        user_request="Create calculator",
                        context={},
                        messages=[],
                        plan={"description": "Build a calculator function"},
                        tasks=[],
                        generated_code="def calc(): pass",
                        target_filename="calc.py",
                        review_feedback="",
                        code_quality_score=8.0,
                        approval_status="approved",
                        user_feedback="",
                        workspace_id="test_ws",
                        file_written=True,
                        file_path="/tmp/test_workspace/calc.py",
                        git_enabled=True,
                        git_commit_message="",
                        git_commit_hash="",
                        git_committed=False,
                        decision_id=""
                    )

                    result = agent._git_commit(state)

                    assert result["git_committed"] is True
                    assert result["git_commit_message"] == "feat: add calculator function"
                    assert result["git_commit_hash"] == "abc123de"  # Short hash

                    mock_git.add_files.assert_called_once_with(["calc.py"])
                    mock_git.commit.assert_called_once()

    def test_git_commit_error_handling(self, agent):
        """Test git commit handles errors gracefully."""
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws_class.side_effect = Exception("Workspace error")

            state = CodeGenState(
                user_request="Test",
                context={},
                messages=[],
                plan={},
                tasks=[],
                generated_code="code",
                target_filename="test.py",
                review_feedback="",
                code_quality_score=7.0,
                approval_status="approved",
                user_feedback="",
                workspace_id="test",
                file_written=True,
                file_path="/tmp/test.py",
                git_enabled=True,
                git_commit_message="",
                git_commit_hash="",
                git_committed=False,
                decision_id=""
            )

            result = agent._git_commit(state)

            assert result["git_committed"] is False
            assert result["git_commit_hash"] == ""
            assert result["git_commit_message"] == ""

    def test_generate_with_git_enabled(self, agent):
        """Test generate with git enabled."""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "generated_code": "def test(): pass",
                "target_filename": "test.py",
                "approval_status": "approved",
                "file_written": True,
                "file_path": "/tmp/test.py",
                "code_quality_score": 9.0,
                "workspace_id": "test-ws",
                "git_committed": True,
                "git_commit_hash": "abc123",
                "git_commit_message": "feat: add test function",
                "messages": []
            }

            result = agent.generate(
                user_request="Create test function",
                git_enabled=True
            )

            # Verify git fields in result
            assert result["git_committed"] is True
            assert result["git_commit_hash"] == "abc123"
            assert result["git_commit_message"] == "feat: add test function"

            # Verify git_enabled was passed to initial state
            call_args = mock_graph.invoke.call_args[0][0]
            assert call_args["git_enabled"] is True

    def test_generate_with_git_disabled(self, agent):
        """Test generate with git disabled."""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "generated_code": "def test(): pass",
                "target_filename": "test.py",
                "approval_status": "approved",
                "file_written": True,
                "file_path": "/tmp/test.py",
                "code_quality_score": 9.0,
                "workspace_id": "test-ws",
                "git_committed": False,
                "git_commit_hash": "",
                "git_commit_message": "",
                "messages": []
            }

            result = agent.generate(
                user_request="Create test function",
                git_enabled=False
            )

            # Verify git fields in result
            assert result["git_committed"] is False
            assert result["git_commit_hash"] == ""

            # Verify git_enabled was passed to initial state
            call_args = mock_graph.invoke.call_args[0][0]
            assert call_args["git_enabled"] is False
