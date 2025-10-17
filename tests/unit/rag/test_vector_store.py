"""
Unit tests for VectorStore (ChromaDB wrapper).

Tests cover:
- Connection and initialization
- Adding examples (single and batch)
- Searching with various filters
- Deleting examples
- Statistics and health checks
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.rag.vector_store import VectorStore, create_vector_store
from src.rag.embeddings import EmbeddingModel


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model."""
    model = Mock(spec=EmbeddingModel)
    model.model_name = "test-model"
    model.get_dimension.return_value = 384
    model.embed_text.return_value = [0.1] * 384
    model.embed_batch.return_value = [[0.1] * 384, [0.2] * 384]
    return model


@pytest.fixture
def mock_chromadb_client():
    """Create a mock ChromaDB client."""
    with patch("src.rag.vector_store.chromadb.HttpClient") as mock_client_class:
        mock_client = MagicMock()
        mock_collection = MagicMock()

        # Setup collection mock
        mock_collection.count.return_value = 0
        mock_collection.add.return_value = None
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        mock_collection.get.return_value = {"ids": []}
        mock_collection.delete.return_value = None

        # Setup client mock
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.delete_collection.return_value = None
        mock_client_class.return_value = mock_client

        yield mock_client, mock_collection


class TestVectorStoreInitialization:
    """Test VectorStore initialization and connection."""

    def test_init_success(self, mock_embedding_model, mock_chromadb_client):
        """Test successful initialization."""
        mock_client, mock_collection = mock_chromadb_client

        vector_store = VectorStore(
            embedding_model=mock_embedding_model,
            host="localhost",
            port=8000
        )

        assert vector_store.embedding_model == mock_embedding_model
        assert vector_store.collection_name == "devmatrix_code_examples"
        assert vector_store.distance_metric == "cosine"
        mock_client.get_or_create_collection.assert_called_once()

    def test_init_custom_parameters(self, mock_embedding_model, mock_chromadb_client):
        """Test initialization with custom parameters."""
        mock_client, _ = mock_chromadb_client

        vector_store = VectorStore(
            embedding_model=mock_embedding_model,
            host="custom-host",
            port=9000,
            collection_name="custom_collection",
            distance_metric="l2"
        )

        assert vector_store.collection_name == "custom_collection"
        assert vector_store.distance_metric == "l2"

    def test_init_connection_failure(self, mock_embedding_model):
        """Test initialization with connection failure."""
        with patch("src.rag.vector_store.chromadb.HttpClient") as mock_client:
            mock_client.side_effect = Exception("Connection failed")

            with pytest.raises(Exception) as exc_info:
                VectorStore(embedding_model=mock_embedding_model)

            assert "Connection failed" in str(exc_info.value)


class TestAddExample:
    """Test adding single examples."""

    def test_add_example_success(self, mock_embedding_model, mock_chromadb_client):
        """Test successfully adding a single example."""
        mock_client, mock_collection = mock_chromadb_client
        mock_collection.count.return_value = 1

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        code = "def hello(): return 'world'"
        metadata = {"language": "python"}

        example_id = vector_store.add_example(code, metadata)

        assert example_id is not None
        mock_embedding_model.embed_text.assert_called_once_with(code)
        mock_collection.add.assert_called_once()

    def test_add_example_with_custom_id(self, mock_embedding_model, mock_chromadb_client):
        """Test adding example with custom ID."""
        _, mock_collection = mock_chromadb_client

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        custom_id = "custom-123"
        code = "def test(): pass"

        example_id = vector_store.add_example(code, example_id=custom_id)

        assert example_id == custom_id

    def test_add_example_empty_code(self, mock_embedding_model, mock_chromadb_client):
        """Test adding empty code raises ValueError."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        with pytest.raises(ValueError) as exc_info:
            vector_store.add_example("")

        assert "empty" in str(exc_info.value).lower()

    def test_add_example_metadata_enrichment(self, mock_embedding_model, mock_chromadb_client):
        """Test that metadata is enriched with timestamps."""
        _, mock_collection = mock_chromadb_client

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        code = "def test(): pass"
        metadata = {"language": "python"}

        vector_store.add_example(code, metadata)

        # Check that add was called with enriched metadata
        call_args = mock_collection.add.call_args
        added_metadata = call_args.kwargs["metadatas"][0]

        assert "indexed_at" in added_metadata
        assert "code_length" in added_metadata
        assert added_metadata["language"] == "python"


class TestAddBatch:
    """Test adding multiple examples in batch."""

    def test_add_batch_success(self, mock_embedding_model, mock_chromadb_client):
        """Test successfully adding a batch of examples."""
        _, mock_collection = mock_chromadb_client

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        codes = ["def hello(): pass", "def world(): pass"]
        metadatas = [{"language": "python"}, {"language": "python"}]

        example_ids = vector_store.add_batch(codes, metadatas)

        assert len(example_ids) == 2
        mock_embedding_model.embed_batch.assert_called_once()
        mock_collection.add.assert_called_once()

    def test_add_batch_empty_list(self, mock_embedding_model, mock_chromadb_client):
        """Test adding empty batch raises ValueError."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        with pytest.raises(ValueError) as exc_info:
            vector_store.add_batch([])

        assert "empty" in str(exc_info.value).lower()

    def test_add_batch_metadata_length_mismatch(self, mock_embedding_model, mock_chromadb_client):
        """Test mismatched metadata length raises ValueError."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        codes = ["code1", "code2"]
        metadatas = [{"key": "value"}]  # Wrong length

        with pytest.raises(ValueError) as exc_info:
            vector_store.add_batch(codes, metadatas)

        assert "length" in str(exc_info.value).lower()

    def test_add_batch_custom_ids(self, mock_embedding_model, mock_chromadb_client):
        """Test adding batch with custom IDs."""
        _, mock_collection = mock_chromadb_client

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        codes = ["code1", "code2"]
        custom_ids = ["id1", "id2"]

        example_ids = vector_store.add_batch(codes, example_ids=custom_ids)

        assert example_ids == custom_ids


class TestSearch:
    """Test similarity search functionality."""

    def test_search_success(self, mock_embedding_model, mock_chromadb_client):
        """Test successful search."""
        _, mock_collection = mock_chromadb_client

        # Mock search results
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["code1", "code2"]],
            "metadatas": [[{"lang": "py"}, {"lang": "py"}]],
            "distances": [[0.1, 0.3]]
        }

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        results = vector_store.search("test query", top_k=2)

        assert len(results) == 2
        assert results[0]["id"] == "id1"
        assert results[0]["code"] == "code1"
        assert "similarity" in results[0]
        mock_embedding_model.embed_text.assert_called_with("test query")

    def test_search_empty_query(self, mock_embedding_model, mock_chromadb_client):
        """Test search with empty query raises ValueError."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        with pytest.raises(ValueError) as exc_info:
            vector_store.search("")

        assert "empty" in str(exc_info.value).lower()

    def test_search_invalid_top_k(self, mock_embedding_model, mock_chromadb_client):
        """Test search with invalid top_k raises ValueError."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        with pytest.raises(ValueError) as exc_info:
            vector_store.search("query", top_k=0)

        assert "top_k" in str(exc_info.value).lower()

    def test_search_with_filters(self, mock_embedding_model, mock_chromadb_client):
        """Test search with metadata filters."""
        _, mock_collection = mock_chromadb_client

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        where_filter = {"language": "python"}
        vector_store.search("query", where=where_filter)

        # Verify filter was passed to ChromaDB
        call_args = mock_collection.query.call_args
        assert call_args.kwargs["where"] == where_filter

    def test_search_similarity_conversion(self, mock_embedding_model, mock_chromadb_client):
        """Test that distances are converted to similarities correctly."""
        _, mock_collection = mock_chromadb_client

        # Mock with known distance
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["code1"]],
            "metadatas": [[{}]],
            "distances": [[0.2]]  # Distance 0.2 -> Similarity 0.8
        }

        vector_store = VectorStore(embedding_model=mock_embedding_model)
        results = vector_store.search("query")

        assert abs(results[0]["similarity"] - 0.8) < 0.01


class TestSearchWithMetadata:
    """Test search with metadata and similarity thresholds."""

    def test_search_with_similarity_threshold(self, mock_embedding_model, mock_chromadb_client):
        """Test filtering by similarity threshold."""
        _, mock_collection = mock_chromadb_client

        # Mock results with varying similarities
        mock_collection.query.return_value = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["code1", "code2", "code3"]],
            "metadatas": [[{}, {}, {}]],
            "distances": [[0.1, 0.4, 0.7]]  # Similarities: 0.9, 0.6, 0.3
        }

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        results = vector_store.search_with_metadata("query", top_k=3, min_similarity=0.5)

        # Should only return results with similarity >= 0.5
        assert len(results) == 2
        assert all(r["similarity"] >= 0.5 for r in results)

    def test_search_with_invalid_threshold(self, mock_embedding_model, mock_chromadb_client):
        """Test invalid similarity threshold raises ValueError."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        with pytest.raises(ValueError) as exc_info:
            vector_store.search_with_metadata("query", min_similarity=1.5)

        assert "similarity" in str(exc_info.value).lower()


class TestDeleteExample:
    """Test deleting examples."""

    def test_delete_example_success(self, mock_embedding_model, mock_chromadb_client):
        """Test successfully deleting an example."""
        _, mock_collection = mock_chromadb_client

        # Mock: example exists
        mock_collection.get.return_value = {"ids": ["id1"]}

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        result = vector_store.delete_example("id1")

        assert result is True
        mock_collection.delete.assert_called_once_with(ids=["id1"])

    def test_delete_example_not_found(self, mock_embedding_model, mock_chromadb_client):
        """Test deleting non-existent example returns False."""
        _, mock_collection = mock_chromadb_client

        # Mock: example doesn't exist
        mock_collection.get.return_value = {"ids": []}

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        result = vector_store.delete_example("nonexistent")

        assert result is False
        mock_collection.delete.assert_not_called()


class TestDeleteBatch:
    """Test deleting multiple examples."""

    def test_delete_batch_success(self, mock_embedding_model, mock_chromadb_client):
        """Test successfully deleting a batch."""
        _, mock_collection = mock_chromadb_client

        # Mock: all examples exist
        mock_collection.get.return_value = {"ids": ["id1", "id2"]}

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        deleted_count = vector_store.delete_batch(["id1", "id2"])

        assert deleted_count == 2
        mock_collection.delete.assert_called_once()

    def test_delete_batch_empty_list(self, mock_embedding_model, mock_chromadb_client):
        """Test deleting empty batch returns 0."""
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        deleted_count = vector_store.delete_batch([])

        assert deleted_count == 0


class TestStats:
    """Test statistics and health checks."""

    def test_get_stats(self, mock_embedding_model, mock_chromadb_client):
        """Test getting vector store statistics."""
        _, mock_collection = mock_chromadb_client
        mock_collection.count.return_value = 42

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        stats = vector_store.get_stats()

        assert stats["total_examples"] == 42
        assert stats["collection_name"] == "devmatrix_code_examples"
        assert stats["distance_metric"] == "cosine"
        assert stats["embedding_dimension"] == 384
        assert stats["embedding_model"] == "test-model"

    def test_health_check_healthy(self, mock_embedding_model, mock_chromadb_client):
        """Test health check when vector store is healthy."""
        _, mock_collection = mock_chromadb_client

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        is_healthy, message = vector_store.health_check()

        assert is_healthy is True
        assert "healthy" in message.lower()

    def test_health_check_unhealthy(self, mock_embedding_model, mock_chromadb_client):
        """Test health check when vector store is unhealthy."""
        _, mock_collection = mock_chromadb_client

        # Initialize successfully first
        vector_store = VectorStore(embedding_model=mock_embedding_model)

        # Then make count fail for health check
        mock_collection.count.side_effect = Exception("Connection lost")

        is_healthy, message = vector_store.health_check()

        assert is_healthy is False
        assert "unhealthy" in message.lower()


class TestClearCollection:
    """Test clearing the entire collection."""

    def test_clear_collection(self, mock_embedding_model, mock_chromadb_client):
        """Test clearing all examples from collection."""
        mock_client, mock_collection = mock_chromadb_client
        mock_collection.count.return_value = 10

        vector_store = VectorStore(embedding_model=mock_embedding_model)

        deleted_count = vector_store.clear_collection()

        assert deleted_count == 10
        mock_client.delete_collection.assert_called_once()
        # Should recreate collection after deleting
        assert mock_client.get_or_create_collection.call_count == 2  # Once in init, once in clear


class TestFactoryFunction:
    """Test factory function."""

    def test_create_vector_store(self, mock_embedding_model, mock_chromadb_client):
        """Test factory function creates VectorStore instance."""
        vector_store = create_vector_store(
            embedding_model=mock_embedding_model,
            host="localhost",
            port=8000
        )

        assert isinstance(vector_store, VectorStore)
        assert vector_store.embedding_model == mock_embedding_model
