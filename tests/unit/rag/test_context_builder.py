"""
Unit tests for ContextBuilder (context formatting).

Tests cover:
- Initialization and configuration
- Simple template formatting
- Detailed template formatting
- Conversational template formatting
- Structured template formatting
- Context truncation
- Metadata formatting
- System prompt building
"""

import pytest
from src.rag.context_builder import (
    ContextBuilder,
    ContextConfig,
    ContextTemplate,
    create_context_builder,
)
from src.rag.retriever import RetrievalResult


@pytest.fixture
def sample_results():
    """Create sample retrieval results."""
    return [
        RetrievalResult(
            id="id1",
            code="def hello():\n    return 'world'",
            metadata={"language": "python", "approved": True},
            similarity=0.95,
            rank=1,
            relevance_score=0.96
        ),
        RetrievalResult(
            id="id2",
            code="def greet(name):\n    return f'Hello, {name}!'",
            metadata={"language": "python", "approved": False},
            similarity=0.85,
            rank=2,
            relevance_score=0.87
        ),
    ]


@pytest.fixture
def context_builder():
    """Create context builder with default config."""
    return ContextBuilder()


class TestContextBuilderInitialization:
    """Test ContextBuilder initialization."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        builder = ContextBuilder()

        assert builder.config.template == ContextTemplate.DETAILED
        assert builder.config.max_length == 8000
        assert builder.config.include_metadata is True
        assert builder.config.include_similarity is True

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = ContextConfig(
            template=ContextTemplate.SIMPLE,
            max_length=5000,
            include_metadata=False,
            include_similarity=False,
            truncate_code=True,
            max_code_length=500,
        )

        builder = ContextBuilder(config=config)

        assert builder.config.template == ContextTemplate.SIMPLE
        assert builder.config.max_length == 5000
        assert builder.config.include_metadata is False
        assert builder.config.truncate_code is True


class TestSimpleTemplate:
    """Test simple template formatting."""

    def test_simple_template_basic(self, context_builder, sample_results):
        """Test basic simple template formatting."""
        context = context_builder.build_context(
            query="test query",
            results=sample_results,
            template=ContextTemplate.SIMPLE
        )

        assert "Example 1:" in context
        assert "Example 2:" in context
        assert "def hello():" in context
        assert "def greet(name):" in context
        # Simple template should not include metadata
        assert "Relevance" not in context

    def test_simple_template_empty_results(self, context_builder):
        """Test simple template with no results."""
        context = context_builder.build_context(
            query="test",
            results=[],
            template=ContextTemplate.SIMPLE
        )

        assert context == ""

    def test_simple_template_single_result(self, context_builder):
        """Test simple template with single result."""
        result = RetrievalResult(
            id="id1",
            code="test code",
            metadata={},
            similarity=0.9,
            rank=1
        )

        context = context_builder.build_context(
            query="test",
            results=[result],
            template=ContextTemplate.SIMPLE
        )

        assert "Example 1:" in context
        assert "test code" in context
        assert "Example 2:" not in context


class TestDetailedTemplate:
    """Test detailed template formatting."""

    def test_detailed_template_basic(self, context_builder, sample_results):
        """Test basic detailed template formatting."""
        context = context_builder.build_context(
            query="greeting function",
            results=sample_results,
            template=ContextTemplate.DETAILED
        )

        assert "# Retrieved Code Examples" in context
        assert "Query: greeting function" in context
        assert "Found 2 relevant example(s)" in context
        assert "## Example 1 (Rank 1)" in context
        assert "## Example 2 (Rank 2)" in context

    def test_detailed_template_with_similarity(self, context_builder, sample_results):
        """Test detailed template includes similarity scores."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.DETAILED
        )

        assert "Relevance" in context
        assert "0.95" in context  # Similarity score
        assert "0.96" in context  # Relevance score

    def test_detailed_template_with_metadata(self, context_builder, sample_results):
        """Test detailed template includes metadata."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.DETAILED
        )

        assert "Metadata" in context
        assert "Language: python" in context
        assert "Approved: True" in context

    def test_detailed_template_without_metadata(self, sample_results):
        """Test detailed template without metadata."""
        config = ContextConfig(include_metadata=False)
        builder = ContextBuilder(config=config)

        context = builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.DETAILED
        )

        assert "Metadata" not in context

    def test_detailed_template_without_similarity(self, sample_results):
        """Test detailed template without similarity scores."""
        config = ContextConfig(include_similarity=False)
        builder = ContextBuilder(config=config)

        context = builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.DETAILED
        )

        assert "Relevance" not in context


class TestConversationalTemplate:
    """Test conversational template formatting."""

    def test_conversational_template_basic(self, context_builder, sample_results):
        """Test basic conversational template."""
        context = context_builder.build_context(
            query="greeting function",
            results=sample_results,
            template=ContextTemplate.CONVERSATIONAL
        )

        assert "Based on your request 'greeting function'" in context
        assert "I found 2 relevant code examples:" in context
        assert "1. Here's a python example" in context
        assert "2. Here's a python example" in context

    def test_conversational_approved_badge(self, context_builder, sample_results):
        """Test conversational template shows approved badge."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.CONVERSATIONAL
        )

        assert "verified and approved" in context

    def test_conversational_similarity_percentage(self, context_builder, sample_results):
        """Test conversational template shows similarity as percentage."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.CONVERSATIONAL
        )

        assert "95% relevance" in context
        assert "85% relevance" in context

    def test_conversational_single_vs_plural(self, context_builder):
        """Test conversational template handles singular/plural correctly."""
        single_result = [
            RetrievalResult(
                id="id1",
                code="code",
                metadata={"language": "python"},
                similarity=0.9,
                rank=1
            )
        ]

        context = context_builder.build_context(
            query="test",
            results=single_result,
            template=ContextTemplate.CONVERSATIONAL
        )

        assert "1 relevant code example:" in context


class TestStructuredTemplate:
    """Test structured template formatting."""

    def test_structured_template_basic(self, context_builder, sample_results):
        """Test basic structured template."""
        context = context_builder.build_context(
            query="test query",
            results=sample_results,
            template=ContextTemplate.STRUCTURED
        )

        assert "<retrieved_examples>" in context
        assert "<query>test query</query>" in context
        assert "<count>2</count>" in context
        assert "<examples>" in context
        assert "</retrieved_examples>" in context

    def test_structured_template_example_attributes(self, context_builder, sample_results):
        """Test structured template includes example attributes."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.STRUCTURED
        )

        assert 'id="id1"' in context
        assert 'rank="1"' in context
        assert 'id="id2"' in context
        assert 'rank="2"' in context

    def test_structured_template_with_similarity(self, context_builder, sample_results):
        """Test structured template includes similarity."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.STRUCTURED
        )

        assert "<similarity>0.950</similarity>" in context
        assert "<score>0.960</score>" in context

    def test_structured_template_with_metadata(self, context_builder, sample_results):
        """Test structured template includes metadata."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.STRUCTURED
        )

        assert "<metadata>" in context
        assert "<language>python</language>" in context
        assert "<approved>True</approved>" in context

    def test_structured_template_cdata(self, context_builder, sample_results):
        """Test structured template uses CDATA for code."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.STRUCTURED
        )

        assert "<code><![CDATA[" in context
        assert "]]></code>" in context

    def test_structured_template_xml_escaping(self, context_builder):
        """Test XML special characters are escaped."""
        result = RetrievalResult(
            id="id1",
            code="if x < 5 && y > 3:",
            metadata={"tag": "<test>"},
            similarity=0.9,
            rank=1
        )

        context = context_builder.build_context(
            query="test & query",
            results=[result],
            template=ContextTemplate.STRUCTURED
        )

        assert "test &amp; query" in context
        assert "&lt;test&gt;" in context


class TestCodeTruncation:
    """Test code truncation functionality."""

    def test_truncate_code_when_enabled(self):
        """Test code is truncated when configured."""
        config = ContextConfig(
            truncate_code=True,
            max_code_length=20
        )
        builder = ContextBuilder(config=config)

        result = RetrievalResult(
            id="id1",
            code="x" * 100,  # Long code
            metadata={},
            similarity=0.9,
            rank=1
        )

        context = builder.build_context(
            query="test",
            results=[result],
            template=ContextTemplate.SIMPLE
        )

        assert "... (truncated)" in context
        # Should not contain full code
        assert "x" * 100 not in context

    def test_no_truncate_when_disabled(self):
        """Test code is not truncated when disabled."""
        config = ContextConfig(truncate_code=False)
        builder = ContextBuilder(config=config)

        result = RetrievalResult(
            id="id1",
            code="x" * 100,
            metadata={},
            similarity=0.9,
            rank=1
        )

        context = builder.build_context(
            query="test",
            results=[result],
            template=ContextTemplate.SIMPLE
        )

        assert "... (truncated)" not in context
        assert "x" * 100 in context

    def test_no_truncate_short_code(self):
        """Test short code is not truncated even when enabled."""
        config = ContextConfig(
            truncate_code=True,
            max_code_length=100
        )
        builder = ContextBuilder(config=config)

        result = RetrievalResult(
            id="id1",
            code="short code",
            metadata={},
            similarity=0.9,
            rank=1
        )

        context = builder.build_context(
            query="test",
            results=[result],
            template=ContextTemplate.SIMPLE
        )

        assert "... (truncated)" not in context
        assert "short code" in context


class TestContextTruncation:
    """Test context truncation functionality."""

    def test_context_truncated_when_too_long(self):
        """Test context is truncated when exceeding max length."""
        config = ContextConfig(max_length=100)
        builder = ContextBuilder(config=config)

        # Create results that will generate long context
        results = [
            RetrievalResult(
                id=f"id{i}",
                code="x" * 50,
                metadata={},
                similarity=0.9,
                rank=i
            )
            for i in range(10)
        ]

        context = builder.build_context(
            query="test",
            results=results,
            template=ContextTemplate.SIMPLE
        )

        assert len(context) <= 100
        assert "... (context truncated due to length)" in context

    def test_context_not_truncated_when_short(self, context_builder, sample_results):
        """Test short context is not truncated."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.SIMPLE
        )

        assert "... (context truncated due to length)" not in context


class TestMetadataFormatting:
    """Test metadata formatting functionality."""

    def test_format_metadata_basic(self, context_builder):
        """Test basic metadata formatting."""
        metadata = {
            "language": "python",
            "approved": True,
            "file_path": "/test/file.py"
        }

        formatted = context_builder._format_metadata(metadata)

        assert "Language: python" in formatted
        assert "Approved: True" in formatted
        assert "File Path: /test/file.py" in formatted

    def test_format_metadata_excludes_internal_fields(self, context_builder):
        """Test internal fields are excluded from formatting."""
        metadata = {
            "language": "python",
            "indexed_at": "2024-01-01",
            "code_length": 100
        }

        formatted = context_builder._format_metadata(metadata)

        assert "language" in formatted.lower()
        assert "indexed_at" not in formatted
        assert "code_length" not in formatted

    def test_format_metadata_empty(self, context_builder):
        """Test formatting empty metadata."""
        formatted = context_builder._format_metadata({})
        assert formatted == ""

    def test_format_metadata_only_internal(self, context_builder):
        """Test formatting metadata with only internal fields."""
        metadata = {
            "indexed_at": "2024-01-01",
            "code_length": 100
        }

        formatted = context_builder._format_metadata(metadata)
        assert formatted == ""


class TestSystemPrompt:
    """Test system prompt building."""

    def test_build_system_prompt_basic(self, context_builder, sample_results):
        """Test basic system prompt building."""
        prompt = context_builder.build_system_prompt(
            task="Create a greeting function",
            results=sample_results
        )

        assert "helpful coding assistant" in prompt
        assert "Task: Create a greeting function" in prompt
        assert "Use these examples as guidance" in prompt

    def test_build_system_prompt_with_instructions(self, context_builder, sample_results):
        """Test system prompt with custom instructions."""
        prompt = context_builder.build_system_prompt(
            task="Test task",
            results=sample_results,
            instructions="Follow PEP 8 style guide"
        )

        assert "Instructions: Follow PEP 8 style guide" in prompt

    def test_build_system_prompt_no_results(self, context_builder):
        """Test system prompt with no results."""
        prompt = context_builder.build_system_prompt(
            task="Test task",
            results=[]
        )

        assert "No specific examples found" in prompt
        assert "Use your best judgment" in prompt


class TestTokenEstimation:
    """Test token estimation functionality."""

    def test_estimate_tokens_basic(self, context_builder):
        """Test basic token estimation."""
        # Approximate: 1 token ≈ 4 characters
        text = "a" * 100

        tokens = context_builder.estimate_tokens(text)

        assert tokens == 25  # 100 / 4

    def test_estimate_tokens_empty(self, context_builder):
        """Test token estimation with empty text."""
        tokens = context_builder.estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_realistic(self, context_builder, sample_results):
        """Test token estimation on realistic context."""
        context = context_builder.build_context(
            query="test",
            results=sample_results,
            template=ContextTemplate.DETAILED
        )

        tokens = context_builder.estimate_tokens(context)

        # Should have reasonable token count
        assert tokens > 0
        assert tokens < 10000


class TestStats:
    """Test statistics functionality."""

    def test_get_stats(self, context_builder):
        """Test getting context builder statistics."""
        stats = context_builder.get_stats()

        assert stats["template"] == "detailed"
        assert stats["max_length"] == 8000
        assert stats["include_metadata"] is True
        assert stats["include_similarity"] is True
        assert stats["truncate_code"] is False


class TestFactoryFunction:
    """Test factory function."""

    def test_create_context_builder(self):
        """Test factory function creates ContextBuilder instance."""
        builder = create_context_builder(
            template=ContextTemplate.SIMPLE,
            max_length=5000
        )

        assert isinstance(builder, ContextBuilder)
        assert builder.config.template == ContextTemplate.SIMPLE
        assert builder.config.max_length == 5000


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_template(self, context_builder, sample_results):
        """Test invalid template raises error."""
        # Create a mock invalid template enum-like object
        class InvalidTemplate:
            value = "invalid"

        context_builder.config.template = InvalidTemplate()

        with pytest.raises(ValueError) as exc_info:
            context_builder.build_context("test", sample_results)

        assert "template" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
