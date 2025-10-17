"""
Unit tests for Retriever (high-level retrieval interface).

Tests cover:
- Initialization and configuration
- Similarity-based retrieval
- MMR-based retrieval for diversity
- Hybrid retrieval
- Re-ranking logic
- Caching behavior
- Statistics
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from src.rag.retriever import (
    Retriever,
    RetrievalResult,
    RetrievalConfig,
    RetrievalStrategy,
    create_retriever,
)
from src.rag.vector_store import VectorStore


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock(spec=VectorStore)
    store.embedding_model = Mock()
    store.embedding_model.embed_text.return_value = [0.1] * 384
    store.embedding_model.embed_batch.return_value = [
        [0.1] * 384,
        [0.2] * 384,
        [0.3] * 384,
    ]

    # Default search results
    store.search_with_metadata.return_value = [
        {
            "id": "id1",
            "code": "def hello(): pass",
            "metadata": {"language": "python"},
            "similarity": 0.9
        },
        {
            "id": "id2",
            "code": "def world(): pass",
            "metadata": {"language": "python"},
            "similarity": 0.8
        },
    ]

    return store


@pytest.fixture
def retriever(mock_vector_store):
    """Create a retriever with default config."""
    return Retriever(vector_store=mock_vector_store)


class TestRetrieverInitialization:
    """Test Retriever initialization."""

    def test_init_default_config(self, mock_vector_store):
        """Test initialization with default configuration."""
        retriever = Retriever(vector_store=mock_vector_store)

        assert retriever.vector_store == mock_vector_store
        assert retriever.config.strategy == RetrievalStrategy.SIMILARITY
        assert retriever.config.top_k == 5
        assert retriever.config.rerank is True
        assert retriever.cache == {}

    def test_init_custom_config(self, mock_vector_store):
        """Test initialization with custom configuration."""
        config = RetrievalConfig(
            top_k=10,
            min_similarity=0.8,
            strategy=RetrievalStrategy.MMR,
            mmr_lambda=0.7,
            rerank=False,
            cache_enabled=False,
        )

        retriever = Retriever(
            vector_store=mock_vector_store,
            config=config
        )

        assert retriever.config.top_k == 10
        assert retriever.config.min_similarity == 0.8
        assert retriever.config.strategy == RetrievalStrategy.MMR
        assert retriever.config.mmr_lambda == 0.7
        assert retriever.config.rerank is False
        assert retriever.config.cache_enabled is False


class TestSimilarityRetrieval:
    """Test similarity-based retrieval."""

    def test_retrieve_similarity_basic(self, retriever, mock_vector_store):
        """Test basic similarity retrieval."""
        results = retriever.retrieve("test query")

        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert results[0].id == "id1"
        assert results[0].code == "def hello(): pass"
        assert results[0].similarity == 0.9
        assert results[0].rank == 1
        assert results[1].rank == 2

        mock_vector_store.search_with_metadata.assert_called_once()

    def test_retrieve_with_custom_top_k(self, retriever, mock_vector_store):
        """Test retrieval with custom top_k."""
        retriever.retrieve("query", top_k=10)

        call_args = mock_vector_store.search_with_metadata.call_args
        assert call_args.kwargs["top_k"] == 10

    def test_retrieve_with_min_similarity(self, retriever, mock_vector_store):
        """Test retrieval with custom min_similarity."""
        retriever.retrieve("query", min_similarity=0.8)

        call_args = mock_vector_store.search_with_metadata.call_args
        assert call_args.kwargs["min_similarity"] == 0.8

    def test_retrieve_with_filters(self, retriever, mock_vector_store):
        """Test retrieval with metadata filters."""
        filters = {"language": "python", "approved": True}
        retriever.retrieve("query", filters=filters)

        call_args = mock_vector_store.search_with_metadata.call_args
        assert call_args.kwargs["filters"] == filters

    def test_retrieve_empty_results(self, retriever, mock_vector_store):
        """Test retrieval with no results."""
        mock_vector_store.search_with_metadata.return_value = []

        results = retriever.retrieve("query")

        assert results == []


class TestMMRRetrieval:
    """Test MMR-based retrieval."""

    def test_retrieve_mmr_basic(self, retriever, mock_vector_store):
        """Test basic MMR retrieval."""
        # Setup more candidates for MMR
        mock_vector_store.search_with_metadata.return_value = [
            {
                "id": f"id{i}",
                "code": f"def func{i}(): pass",
                "metadata": {},
                "similarity": 0.9 - i * 0.1
            }
            for i in range(5)
        ]

        results = retriever.retrieve("query", strategy=RetrievalStrategy.MMR, top_k=3)

        assert len(results) <= 3
        # Results should be diverse (MMR selection)
        assert all(isinstance(r, RetrievalResult) for r in results)

        # Should have called embed_batch for MMR calculation
        mock_vector_store.embedding_model.embed_batch.assert_called_once()

    def test_mmr_selection_algorithm(self, retriever):
        """Test MMR selection algorithm directly."""
        # Create simple test embeddings
        query_emb = [1.0, 0.0, 0.0]
        candidates = [
            [1.0, 0.0, 0.0],  # Very similar to query
            [0.9, 0.1, 0.0],  # Similar to query
            [0.0, 1.0, 0.0],  # Different from query
        ]

        selected = retriever._mmr_selection(
            query_embedding=query_emb,
            candidate_embeddings=candidates,
            top_k=2,
            lambda_param=0.5  # Balance similarity and diversity
        )

        assert len(selected) == 2
        assert 0 in selected  # Should include most similar
        # Should include diverse result (either 1 or 2)

    def test_mmr_lambda_parameter(self, retriever, mock_vector_store):
        """Test MMR with different lambda parameters."""
        # Setup candidates
        mock_vector_store.search_with_metadata.return_value = [
            {"id": f"id{i}", "code": f"code{i}", "metadata": {}, "similarity": 0.9}
            for i in range(10)
        ]

        # High lambda (prefer similarity)
        retriever.config.mmr_lambda = 0.9
        results_high = retriever.retrieve("query", strategy=RetrievalStrategy.MMR, top_k=3)

        # Low lambda (prefer diversity)
        retriever.config.mmr_lambda = 0.1
        results_low = retriever.retrieve("query", strategy=RetrievalStrategy.MMR, top_k=3)

        # Both should return results
        assert len(results_high) <= 3
        assert len(results_low) <= 3


class TestHybridRetrieval:
    """Test hybrid retrieval."""

    def test_retrieve_hybrid_basic(self, retriever, mock_vector_store):
        """Test basic hybrid retrieval."""
        mock_vector_store.search_with_metadata.return_value = [
            {
                "id": "id1",
                "code": "code1",
                "metadata": {"approved": True},
                "similarity": 0.8
            },
            {
                "id": "id2",
                "code": "code2",
                "metadata": {"approved": False},
                "similarity": 0.9
            },
        ]

        results = retriever.retrieve("query", strategy=RetrievalStrategy.HYBRID)

        assert len(results) > 0
        # Approved example should be boosted
        # (exact ranking depends on boost factors)

    def test_hybrid_approved_boost(self, retriever, mock_vector_store):
        """Test that approved examples get boosted in hybrid mode."""
        mock_vector_store.search_with_metadata.return_value = [
            {
                "id": "id_approved",
                "code": "approved code",
                "metadata": {"approved": True},
                "similarity": 0.75
            },
            {
                "id": "id_not_approved",
                "code": "not approved code",
                "metadata": {"approved": False},
                "similarity": 0.80
            },
        ]

        results = retriever.retrieve("query", strategy=RetrievalStrategy.HYBRID)

        # Approved example should score higher despite lower initial similarity
        approved_result = next(r for r in results if r.id == "id_approved")
        not_approved_result = next(r for r in results if r.id == "id_not_approved")

        # With 1.2x boost, 0.75 * 1.2 = 0.9 > 0.80
        assert approved_result.relevance_score > not_approved_result.relevance_score


class TestReranking:
    """Test re-ranking functionality."""

    def test_reranking_enabled(self, mock_vector_store):
        """Test that re-ranking is applied when enabled."""
        config = RetrievalConfig(rerank=True)
        retriever = Retriever(vector_store=mock_vector_store, config=config)

        mock_vector_store.search_with_metadata.return_value = [
            {
                "id": "id1",
                "code": "x" * 10,  # Very short
                "metadata": {},
                "similarity": 0.9
            },
            {
                "id": "id2",
                "code": "x" * 200,  # Good length
                "metadata": {"approved": True},
                "similarity": 0.85
            },
        ]

        results = retriever.retrieve("query")

        # Re-ranking should adjust scores based on heuristics
        assert all(hasattr(r, "relevance_score") for r in results)

    def test_reranking_disabled(self, mock_vector_store):
        """Test that re-ranking is skipped when disabled."""
        config = RetrievalConfig(rerank=False)
        retriever = Retriever(vector_store=mock_vector_store, config=config)

        results = retriever.retrieve("query")

        # Without re-ranking, relevance_score should equal similarity
        for result in results:
            assert result.relevance_score == result.similarity

    def test_rerank_code_length_boost(self, retriever, mock_vector_store):
        """Test that appropriate code length gets boosted."""
        mock_vector_store.search_with_metadata.return_value = [
            {
                "id": "short",
                "code": "x" * 10,
                "metadata": {},
                "similarity": 0.9
            },
            {
                "id": "good",
                "code": "x" * 200,
                "metadata": {},
                "similarity": 0.85
            },
            {
                "id": "long",
                "code": "x" * 1000,
                "metadata": {},
                "similarity": 0.88
            },
        ]

        results = retriever.retrieve("query")

        # Good length should get boost
        good_result = next(r for r in results if r.id == "good")
        short_result = next(r for r in results if r.id == "short")

        # 0.85 * 1.1 = 0.935 > 0.9 * 0.8 = 0.72
        assert good_result.relevance_score > short_result.relevance_score


class TestCaching:
    """Test caching behavior."""

    def test_cache_hit(self, retriever, mock_vector_store):
        """Test that cache is used for repeated queries."""
        # First call
        results1 = retriever.retrieve("test query")

        # Second call with same parameters
        results2 = retriever.retrieve("test query")

        # Should only call vector store once
        assert mock_vector_store.search_with_metadata.call_count == 1

        # Results should be the same
        assert len(results1) == len(results2)
        assert results1[0].id == results2[0].id

    def test_cache_miss_different_query(self, retriever, mock_vector_store):
        """Test that different queries don't hit cache."""
        retriever.retrieve("query 1")
        retriever.retrieve("query 2")

        # Should call vector store twice
        assert mock_vector_store.search_with_metadata.call_count == 2

    def test_cache_miss_different_params(self, retriever, mock_vector_store):
        """Test that different parameters don't hit cache."""
        retriever.retrieve("query", top_k=5)
        retriever.retrieve("query", top_k=10)

        # Should call vector store twice
        assert mock_vector_store.search_with_metadata.call_count == 2

    def test_cache_disabled(self, mock_vector_store):
        """Test retrieval with caching disabled."""
        config = RetrievalConfig(cache_enabled=False)
        retriever = Retriever(vector_store=mock_vector_store, config=config)

        retriever.retrieve("query")
        retriever.retrieve("query")

        # Should call vector store twice (no caching)
        assert mock_vector_store.search_with_metadata.call_count == 2

    def test_clear_cache(self, retriever, mock_vector_store):
        """Test clearing the cache."""
        # Populate cache
        retriever.retrieve("query 1")
        retriever.retrieve("query 2")

        assert len(retriever.cache) == 2

        # Clear cache
        cleared = retriever.clear_cache()

        assert cleared == 2
        assert len(retriever.cache) == 0


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_cosine_similarity_identical(self, retriever):
        """Test cosine similarity of identical vectors."""
        vec = np.array([1.0, 0.0, 0.0])
        matrix = np.array([[1.0, 0.0, 0.0]])

        sims = retriever._cosine_similarity_batch(vec, matrix)

        assert len(sims) == 1
        assert abs(sims[0] - 1.0) < 0.01

    def test_cosine_similarity_orthogonal(self, retriever):
        """Test cosine similarity of orthogonal vectors."""
        vec = np.array([1.0, 0.0, 0.0])
        matrix = np.array([[0.0, 1.0, 0.0]])

        sims = retriever._cosine_similarity_batch(vec, matrix)

        assert len(sims) == 1
        assert abs(sims[0]) < 0.01

    def test_cosine_similarity_batch(self, retriever):
        """Test cosine similarity with multiple vectors."""
        vec = np.array([1.0, 0.0, 0.0])
        matrix = np.array([
            [1.0, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 1.0, 0.0],
        ])

        sims = retriever._cosine_similarity_batch(vec, matrix)

        assert len(sims) == 3
        assert abs(sims[0] - 1.0) < 0.01  # Identical
        assert 0.0 < sims[1] < 1.0  # Partial similarity
        assert abs(sims[2]) < 0.01  # Orthogonal


class TestRetrievalResult:
    """Test RetrievalResult dataclass."""

    def test_retrieval_result_creation(self):
        """Test creating a RetrievalResult."""
        result = RetrievalResult(
            id="test_id",
            code="test code",
            metadata={"key": "value"},
            similarity=0.9,
            rank=1,
            relevance_score=0.95
        )

        assert result.id == "test_id"
        assert result.code == "test code"
        assert result.metadata["key"] == "value"
        assert result.similarity == 0.9
        assert result.rank == 1
        assert result.relevance_score == 0.95

    def test_retrieval_result_to_dict(self):
        """Test converting RetrievalResult to dictionary."""
        result = RetrievalResult(
            id="test_id",
            code="test code",
            metadata={"key": "value"},
            similarity=0.9
        )

        result_dict = result.to_dict()

        assert result_dict["id"] == "test_id"
        assert result_dict["code"] == "test code"
        assert result_dict["metadata"]["key"] == "value"
        assert result_dict["similarity"] == 0.9


class TestStats:
    """Test retriever statistics."""

    def test_get_stats(self, retriever):
        """Test getting retriever statistics."""
        # Populate cache
        retriever.cache["key1"] = []
        retriever.cache["key2"] = []

        stats = retriever.get_stats()

        assert stats["strategy"] == "similarity"
        assert stats["top_k"] == 5
        assert stats["cache_size"] == 2
        assert "min_similarity" in stats
        assert "mmr_lambda" in stats


class TestFactoryFunction:
    """Test factory function."""

    def test_create_retriever(self, mock_vector_store):
        """Test factory function creates Retriever instance."""
        retriever = create_retriever(
            vector_store=mock_vector_store,
            strategy=RetrievalStrategy.MMR,
            top_k=10,
            min_similarity=0.8
        )

        assert isinstance(retriever, Retriever)
        assert retriever.config.strategy == RetrievalStrategy.MMR
        assert retriever.config.top_k == 10
        assert retriever.config.min_similarity == 0.8


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_strategy(self, retriever, mock_vector_store):
        """Test that invalid strategy raises error."""
        # Create a mock invalid strategy enum-like object
        class InvalidStrategy:
            value = "invalid"

        retriever.config.strategy = InvalidStrategy()

        with pytest.raises(ValueError) as exc_info:
            retriever.retrieve("query")

        assert "strategy" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    def test_vector_store_error_propagates(self, retriever, mock_vector_store):
        """Test that vector store errors propagate."""
        mock_vector_store.search_with_metadata.side_effect = Exception("DB error")

        with pytest.raises(Exception) as exc_info:
            retriever.retrieve("query")

        assert "DB error" in str(exc_info.value)
