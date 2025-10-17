"""
Unit tests for ImplementationAgent with RAG integration.

Tests cover:
- RAG initialization (enabled/disabled)
- Code generation with RAG context
- Code generation without RAG context
- Code approval recording
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.agents.implementation_agent import ImplementationAgent


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    mock = Mock()
    mock.generate.return_value = {
        'content': '```python\ndef test_function():\n    pass\n```'
    }
    return mock


@pytest.fixture
def mock_rag_components():
    """Create mock RAG components."""
    return {
        'embedding_model': Mock(),
        'vector_store': Mock(),
        'retriever': Mock(),
        'context_builder': Mock(),
        'feedback_service': Mock()
    }


class TestRAGInitialization:
    """Test RAG initialization in ImplementationAgent."""

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    def test_init_with_rag_enabled(
        self,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed
    ):
        """Test initialization with RAG enabled."""
        agent = ImplementationAgent(enable_rag=True)

        assert agent.rag_enabled is True
        assert hasattr(agent, 'retriever')
        assert hasattr(agent, 'context_builder')
        assert hasattr(agent, 'feedback_service')

        mock_embed.assert_called_once()
        mock_store.assert_called_once()
        mock_retriever.assert_called_once()
        mock_context.assert_called_once()
        mock_feedback.assert_called_once()

    def test_init_with_rag_disabled(self):
        """Test initialization with RAG disabled."""
        agent = ImplementationAgent(enable_rag=False)

        assert agent.rag_enabled is False
        assert not hasattr(agent, 'retriever')

    @patch('src.agents.implementation_agent.create_embedding_model')
    def test_init_rag_failure_graceful(self, mock_embed):
        """Test graceful fallback when RAG initialization fails."""
        mock_embed.side_effect = Exception("ChromaDB not available")

        agent = ImplementationAgent(enable_rag=True)

        # Should fall back to disabled
        assert agent.rag_enabled is False


class TestCodeGenerationWithRAG:
    """Test code generation with RAG enhancement."""

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    def test_generate_with_rag_context(
        self,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed,
        mock_llm_client
    ):
        """Test code generation uses RAG context when available."""
        # Setup mock retrieval results
        mock_result = Mock()
        mock_result.similarity = 0.9
        mock_retriever.return_value.retrieve.return_value = [mock_result]

        mock_context.return_value.build_context.return_value = "# Example code\ndef example(): pass"

        agent = ImplementationAgent(enable_rag=True)
        agent.llm = mock_llm_client

        code = agent._generate_code(
            description="Create a test function",
            files=["test.py"],
            dependency_context="",
            metadata={"language": "python"}
        )

        # Should have called retriever
        mock_retriever.return_value.retrieve.assert_called_once()

        # Should have called context builder
        mock_context.return_value.build_context.assert_called_once()

        # Should have called LLM with enhanced system prompt
        call_args = mock_llm_client.generate.call_args
        system_prompt = call_args.kwargs['system']
        assert "Similar Code Examples" in system_prompt

        # Should return extracted code
        assert "def test_function():" in code

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    def test_generate_without_rag_results(
        self,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed,
        mock_llm_client
    ):
        """Test code generation when no RAG results found."""
        # Setup mock with no results
        mock_retriever.return_value.retrieve.return_value = []

        agent = ImplementationAgent(enable_rag=True)
        agent.llm = mock_llm_client

        code = agent._generate_code(
            description="Create a unique function",
            files=["unique.py"],
            dependency_context="",
            metadata={"language": "python"}
        )

        # Should have tried retrieval
        mock_retriever.return_value.retrieve.assert_called_once()

        # Should NOT have called context builder
        mock_context.return_value.build_context.assert_not_called()

        # Should have called LLM with basic system prompt
        call_args = mock_llm_client.generate.call_args
        system_prompt = call_args.kwargs['system']
        assert "Similar Code Examples" not in system_prompt

    def test_generate_without_rag_disabled(self, mock_llm_client):
        """Test code generation when RAG is disabled."""
        agent = ImplementationAgent(enable_rag=False)
        agent.llm = mock_llm_client

        code = agent._generate_code(
            description="Create a function",
            files=["test.py"],
            dependency_context="",
            metadata={"language": "python"}
        )

        # Should have called LLM with basic system prompt
        call_args = mock_llm_client.generate.call_args
        system_prompt = call_args.kwargs['system']
        assert "Similar Code Examples" not in system_prompt

        assert "def test_function():" in code


class TestCodeApprovalRecording:
    """Test code approval recording functionality."""

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    def test_record_approval_success(
        self,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed
    ):
        """Test successful code approval recording."""
        mock_feedback.return_value.record_approval.return_value = "feedback_123"

        agent = ImplementationAgent(enable_rag=True)

        feedback_id = agent.record_code_approval(
            code="def approved(): pass",
            task_id="task_1",
            workspace_id="ws_1",
            metadata={"language": "python"}
        )

        assert feedback_id == "feedback_123"
        mock_feedback.return_value.record_approval.assert_called_once()

    def test_record_approval_rag_disabled(self):
        """Test approval recording when RAG is disabled."""
        agent = ImplementationAgent(enable_rag=False)

        feedback_id = agent.record_code_approval(
            code="def test(): pass",
            task_id="task_1",
            workspace_id="ws_1"
        )

        assert feedback_id is None

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    def test_record_approval_error_handling(
        self,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed
    ):
        """Test error handling in approval recording."""
        mock_feedback.return_value.record_approval.side_effect = Exception("Database error")

        agent = ImplementationAgent(enable_rag=True)

        feedback_id = agent.record_code_approval(
            code="def test(): pass",
            task_id="task_1",
            workspace_id="ws_1"
        )

        # Should return None on error
        assert feedback_id is None


class TestLanguageInference:
    """Test language inference from file extensions."""

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    @patch('src.agents.implementation_agent.WorkspaceManager')
    def test_language_inference_python(
        self,
        mock_ws,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed,
        mock_llm_client
    ):
        """Test Python language inference."""
        mock_ws.return_value.base_path.exists.return_value = True
        mock_ws.return_value.write_file.return_value = "/path/test.py"

        mock_retriever.return_value.retrieve.return_value = []

        agent = ImplementationAgent(enable_rag=True)
        agent.llm = mock_llm_client

        scratchpad = Mock()
        scratchpad.read_artifacts.return_value = []

        task = {
            "id": "task_1",
            "description": "Create function",
            "files": ["test.py"]
        }

        context = {
            "workspace_id": "ws_1",
            "scratchpad": scratchpad
        }

        result = agent.execute(task, context)

        # Should have inferred Python
        assert result["success"] is True

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    @patch('src.agents.implementation_agent.WorkspaceManager')
    def test_language_inference_javascript(
        self,
        mock_ws,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed,
        mock_llm_client
    ):
        """Test JavaScript language inference."""
        mock_ws.return_value.base_path.exists.return_value = True
        mock_ws.return_value.write_file.return_value = "/path/test.js"

        mock_retriever.return_value.retrieve.return_value = []

        agent = ImplementationAgent(enable_rag=True)
        agent.llm = mock_llm_client

        scratchpad = Mock()
        scratchpad.read_artifacts.return_value = []

        task = {
            "id": "task_1",
            "description": "Create function",
            "files": ["test.js"]
        }

        context = {
            "workspace_id": "ws_1",
            "scratchpad": scratchpad
        }

        result = agent.execute(task, context)

        # Should have inferred JavaScript
        assert result["success"] is True


class TestErrorHandling:
    """Test error handling in RAG operations."""

    @patch('src.agents.implementation_agent.create_embedding_model')
    @patch('src.agents.implementation_agent.create_vector_store')
    @patch('src.agents.implementation_agent.create_retriever')
    @patch('src.agents.implementation_agent.create_context_builder')
    @patch('src.agents.implementation_agent.create_feedback_service')
    def test_rag_retrieval_error_continues(
        self,
        mock_feedback,
        mock_context,
        mock_retriever,
        mock_store,
        mock_embed,
        mock_llm_client
    ):
        """Test that retrieval errors don't crash generation."""
        mock_retriever.return_value.retrieve.side_effect = Exception("Retrieval error")

        agent = ImplementationAgent(enable_rag=True)
        agent.llm = mock_llm_client

        # Should not raise
        code = agent._generate_code(
            description="Create function",
            files=["test.py"],
            dependency_context="",
            metadata={"language": "python"}
        )

        # Should still generate code
        assert "def test_function():" in code

        # LLM should have been called with basic prompt
        call_args = mock_llm_client.generate.call_args
        system_prompt = call_args.kwargs['system']
        assert "Similar Code Examples" not in system_prompt
