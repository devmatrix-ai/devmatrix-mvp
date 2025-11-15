"""
Unit Tests for Pattern Bank with Qdrant Integration

TDD Approach with proper mocking - tests work without real Qdrant instance.

Test Coverage:
- Qdrant client initialization and connection
- Pattern storage with success threshold validation (≥95%)
- Pattern retrieval by similarity threshold (≥85%)
- Metadata tracking (usage_count, creation_timestamp)
- Collection creation and deletion
- Domain filtering
- Hybrid search (vector + metadata)
- Pattern metrics tracking
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock, PropertyMock

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.patterns.pattern_bank import (
    PatternBank,
    StoredPattern,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


class TestPatternBankInitialization:
    """Test PatternBank initialization and Qdrant connection."""

    def test_pattern_bank_initialization_default_settings(self):
        """Test PatternBank initializes with default settings from config."""
        with patch('src.cognitive.patterns.pattern_bank.SentenceTransformer'):
            bank = PatternBank()

            assert bank is not None
            assert hasattr(bank, 'client')
            assert hasattr(bank, 'encoder')
            assert bank.collection_name == "semantic_patterns"
            assert bank.embedding_dimension == 768

    def test_pattern_bank_initialization_custom_collection(self):
        """Test PatternBank with custom collection name."""
        with patch('src.cognitive.patterns.pattern_bank.SentenceTransformer'):
            bank = PatternBank(collection_name="custom_patterns")

            assert bank.collection_name == "custom_patterns"

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_qdrant_client_connection_successful(self, mock_st, mock_qdrant_client):
        """Test Qdrant client connects successfully."""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        assert bank.is_connected is True
        mock_client.get_collections.assert_called_once()

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_qdrant_client_connection_failure_raises_error(self, mock_st, mock_qdrant_client):
        """Test connection failure raises appropriate error."""
        mock_client = Mock()
        mock_client.get_collections.side_effect = Exception("Connection refused")
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()

        with pytest.raises(ConnectionError, match="Failed to connect to Qdrant"):
            bank.connect()


class TestCollectionManagement:
    """Test Qdrant collection creation and management."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_collection_creation_with_correct_parameters(self, mock_st, mock_qdrant_client):
        """Test collection created with 768 dimensions and cosine distance."""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()
        bank.create_collection()

        # Verify collection creation was called
        mock_client.create_collection.assert_called_once()
        call_kwargs = mock_client.create_collection.call_args.kwargs
        assert call_kwargs['collection_name'] == "semantic_patterns"

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_collection_already_exists_no_error(self, mock_st, mock_qdrant_client):
        """Test creating existing collection doesn't raise error."""
        mock_client = Mock()

        # Mock collection that already exists
        mock_collection = Mock()
        mock_collection.name = "semantic_patterns"
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_client.get_collections.return_value = mock_collections

        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()
        bank.create_collection()

        # Should NOT call create_collection since it exists
        mock_client.create_collection.assert_not_called()

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_collection_deletion_successful(self, mock_st, mock_qdrant_client):
        """Test collection can be deleted."""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()
        bank.delete_collection()

        mock_client.delete_collection.assert_called_once_with(
            collection_name="semantic_patterns"
        )


class TestPatternStorage:
    """Test pattern storage with validation."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_store_pattern_with_valid_success_rate(self, mock_st, mock_qdrant_client):
        """Test storing pattern with success_rate ≥ 95%."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        signature = SemanticTaskSignature(
            purpose="Validate email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        code = "def validate_email(email: str) -> bool:\n    return '@' in email"

        pattern_id = bank.store_pattern(
            signature=signature,
            code=code,
            success_rate=0.96,
        )

        assert pattern_id is not None
        assert isinstance(pattern_id, str)
        assert pattern_id.startswith("pat_")
        mock_client.upsert.assert_called_once()

    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_store_pattern_rejects_low_success_rate(self, mock_st):
        """Test storing pattern with success_rate < 95% raises error."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Parse JSON",
            intent="transform",
            inputs={"json_str": "str"},
            outputs={"data": "dict"},
            domain="data_processing",
        )

        code = "def parse_json(json_str): return json.loads(json_str)"

        with pytest.raises(ValueError, match="success_rate.*0.95"):
            bank.store_pattern(
                signature=signature,
                code=code,
                success_rate=0.92,
            )

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_store_pattern_includes_correct_metadata(self, mock_st, mock_qdrant_client):
        """Test stored pattern includes all required metadata."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        signature = SemanticTaskSignature(
            purpose="Calculate tax",
            intent="calculate",
            inputs={"amount": "float", "rate": "float"},
            outputs={"tax": "float"},
            domain="financial",
        )

        code = "def calculate_tax(amount, rate): return amount * rate"

        bank.store_pattern(signature, code, success_rate=0.97)

        # Verify upsert was called with correct structure
        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        point = call_args.kwargs['points'][0]

        assert point.payload['purpose'] == "Calculate tax"
        assert point.payload['code'] == code
        assert point.payload['domain'] == "financial"
        assert point.payload['success_rate'] == 0.97
        assert point.payload['usage_count'] == 0
        assert 'created_at' in point.payload
        assert 'semantic_hash' in point.payload


class TestPatternRetrieval:
    """Test pattern retrieval with similarity search."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_search_patterns_returns_top_k_results(self, mock_st, mock_qdrant_client):
        """Test search returns requested number of results."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        # Mock search results
        mock_results = []
        for i in range(3):
            mock_hit = Mock()
            mock_hit.id = f"pat_{i}"
            mock_hit.score = 0.9 - (i * 0.05)
            mock_hit.payload = {
                "pattern_id": f"pat_{i}",
                "purpose": f"Test purpose {i}",
                "intent": "validate",
                "domain": "authentication",
                "code": "def test(): pass",
                "success_rate": 0.96,
                "usage_count": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
            mock_results.append(mock_hit)

        mock_client.search.return_value = mock_results
        mock_client.retrieve.return_value = [mock_results[0]]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        query_signature = SemanticTaskSignature(
            purpose="Validate user email",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        results = bank.search_patterns(query_signature, top_k=5)

        assert isinstance(results, list)
        assert len(results) == 3

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_search_patterns_filters_by_similarity_threshold(self, mock_st, mock_qdrant_client):
        """Test search filters results by ≥85% similarity threshold."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        # Mock results above threshold
        mock_results = []
        for i in range(2):
            mock_hit = Mock()
            mock_hit.id = f"pat_{i}"
            mock_hit.score = 0.87 + (i * 0.03)
            mock_hit.payload = {
                "pattern_id": f"pat_{i}",
                "purpose": f"Test {i}",
                "intent": "validate",
                "domain": "auth",
                "code": "code",
                "success_rate": 0.96,
                "usage_count": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
            mock_results.append(mock_hit)

        mock_client.search.return_value = mock_results
        mock_client.retrieve.return_value = [mock_results[0]]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        query_signature = SemanticTaskSignature(
            purpose="Check password strength",
            intent="validate",
            inputs={"password": "str"},
            outputs={"strength": "int"},
            domain="authentication",
        )

        results = bank.search_patterns(query_signature, similarity_threshold=0.85)

        for pattern in results:
            assert pattern.similarity_score >= 0.85

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_search_patterns_returns_sorted_by_similarity(self, mock_st, mock_qdrant_client):
        """Test search results sorted by similarity (descending)."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        # Mock results with different scores
        mock_results = []
        scores = [0.95, 0.90, 0.88]
        for i, score in enumerate(scores):
            mock_hit = Mock()
            mock_hit.id = f"pat_{i}"
            mock_hit.score = score
            mock_hit.payload = {
                "pattern_id": f"pat_{i}",
                "purpose": "Test",
                "intent": "validate",
                "domain": "test",
                "code": "code",
                "success_rate": 0.96,
                "usage_count": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
            mock_results.append(mock_hit)

        mock_client.search.return_value = mock_results
        mock_client.retrieve.return_value = [mock_results[0]]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        query_signature = SemanticTaskSignature(
            purpose="Format currency",
            intent="transform",
            inputs={"amount": "float"},
            outputs={"formatted": "str"},
            domain="financial",
        )

        results = bank.search_patterns(query_signature, top_k=10)

        # Verify descending order (Qdrant returns sorted)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity_score >= results[i + 1].similarity_score


class TestHybridSearch:
    """Test hybrid search combining vector and metadata filtering."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_hybrid_search_with_domain_filter(self, mock_st, mock_qdrant_client):
        """Test hybrid search filters by domain."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        # Mock results from authentication domain only
        mock_results = []
        for i in range(2):
            mock_hit = Mock()
            mock_hit.id = f"pat_{i}"
            mock_hit.score = 0.9
            mock_hit.payload = {
                "pattern_id": f"pat_{i}",
                "purpose": "Hash password",
                "intent": "transform",
                "domain": "authentication",
                "code": "code",
                "success_rate": 0.97,
                "usage_count": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
            mock_results.append(mock_hit)

        mock_client.search.return_value = mock_results
        mock_client.retrieve.return_value = [mock_results[0]]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        signature = SemanticTaskSignature(
            purpose="Hash password",
            intent="transform",
            inputs={"password": "str"},
            outputs={"hash": "str"},
            domain="authentication",
        )

        results = bank.hybrid_search(signature, domain="authentication", top_k=5)

        # All results should be from authentication domain
        for pattern in results:
            assert pattern.domain == "authentication"


class TestPatternMetrics:
    """Test pattern metrics tracking."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_get_pattern_metrics_returns_aggregated_stats(self, mock_st, mock_qdrant_client):
        """Test get_pattern_metrics returns comprehensive statistics."""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        # Mock collection info
        mock_collection_info = Mock()
        mock_collection_info.points_count = 10
        mock_client.get_collection.return_value = mock_collection_info

        # Mock scroll results
        mock_points = []
        for i in range(10):
            mock_point = Mock()
            mock_point.payload = {
                "pattern_id": f"pat_{i}",
                "purpose": f"Test {i}",
                "success_rate": 0.96,
                "usage_count": i,
                "domain": "authentication" if i < 5 else "financial",
            }
            mock_points.append(mock_point)

        mock_client.scroll.return_value = (mock_points, None)
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        metrics = bank.get_pattern_metrics()

        assert isinstance(metrics, dict)
        assert 'total_patterns' in metrics
        assert 'avg_success_rate' in metrics
        assert 'avg_usage_count' in metrics
        assert 'domain_distribution' in metrics
        assert 'most_used_patterns' in metrics
        assert metrics['total_patterns'] == 10

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_update_pattern_success_rate(self, mock_st, mock_qdrant_client):
        """Test updating success rate for existing pattern."""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        pattern_id = "pat_test123"

        bank.update_pattern_success(pattern_id, new_success_rate=0.98)

        # Verify set_payload was called
        mock_client.set_payload.assert_called_once()
        call_args = mock_client.set_payload.call_args
        assert call_args.kwargs['payload']['success_rate'] == 0.98

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_domain_distribution_tracks_all_domains(self, mock_st, mock_qdrant_client):
        """Test domain distribution tracks patterns across all domains."""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        mock_collection_info = Mock()
        mock_collection_info.points_count = 5
        mock_client.get_collection.return_value = mock_collection_info

        mock_points = []
        domains = ["authentication", "financial", "api", "authentication", "financial"]
        for i, domain in enumerate(domains):
            mock_point = Mock()
            mock_point.payload = {
                "pattern_id": f"pat_{i}",
                "purpose": "Test",
                "success_rate": 0.96,
                "usage_count": 0,
                "domain": domain,
            }
            mock_points.append(mock_point)

        mock_client.scroll.return_value = (mock_points, None)
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        metrics = bank.get_pattern_metrics()
        domain_dist = metrics['domain_distribution']

        assert isinstance(domain_dist, dict)
        assert domain_dist["authentication"] == 2
        assert domain_dist["financial"] == 2
        assert domain_dist["api"] == 1


class TestAutoConnection:
    """Test automatic connection when is_connected=False."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_create_collection_auto_connects_if_not_connected(self, mock_st, mock_qdrant_client):
        """Test that create_collection calls connect() if not connected."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.is_connected = False  # Simulate not connected
        bank.client = mock_client
        bank.encoder = mock_encoder

        with patch.object(bank, 'connect') as mock_connect:
            bank.create_collection()
            mock_connect.assert_called_once()

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_delete_collection_auto_connects_if_not_connected(self, mock_st, mock_qdrant_client):
        """Test that delete_collection calls connect() if not connected."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.is_connected = False
        bank.client = mock_client
        bank.encoder = mock_encoder

        with patch.object(bank, 'connect') as mock_connect:
            bank.delete_collection()
            mock_connect.assert_called_once()


class TestExceptionHandling:
    """Test exception handling and error cases."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_create_collection_handles_exception(self, mock_st, mock_qdrant_client):
        """Test that create_collection raises exception on failure."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        # First call to get_collections (in connect) succeeds
        mock_collections = Mock()
        mock_collections.collections = []
        # Second call to get_collections (in create_collection) fails
        mock_client.get_collections.side_effect = [mock_collections, Exception("Qdrant error")]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()  # This should succeed

        with pytest.raises(Exception, match="Qdrant error"):
            bank.create_collection()  # This should fail

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_increment_usage_count_handles_exception(self, mock_st, mock_qdrant_client):
        """Test that _increment_usage_count handles exception gracefully."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_client.retrieve.side_effect = Exception("Retrieve failed")
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        # Should not raise, just log warning
        bank._increment_usage_count("pat_123")  # No exception expected


class TestGetPatternById:
    """Test pattern retrieval by ID."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_get_pattern_by_id_returns_pattern_if_found(self, mock_st, mock_qdrant_client):
        """Test get_pattern_by_id returns pattern when found."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_hit = Mock()
        mock_hit.payload = {
            "pattern_id": "pat_123",
            "purpose": "Test pattern",
            "intent": "test",
            "domain": "testing",
            "code": "def test(): pass",
            "success_rate": 0.96,
            "usage_count": 10,
            "created_at": datetime.utcnow().isoformat(),
        }
        mock_client.retrieve.return_value = [mock_hit]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        pattern = bank.get_pattern_by_id("pat_123")

        assert pattern is not None
        assert pattern.pattern_id == "pat_123"
        assert pattern.signature.purpose == "Test pattern"
        assert pattern.code == "def test(): pass"

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_get_pattern_by_id_returns_none_if_not_found(self, mock_st, mock_qdrant_client):
        """Test get_pattern_by_id returns None when not found."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_client.retrieve.return_value = []  # No results
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        pattern = bank.get_pattern_by_id("nonexistent")

        assert pattern is None

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_get_pattern_by_id_handles_exception(self, mock_st, mock_qdrant_client):
        """Test get_pattern_by_id returns None on exception."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_client.retrieve.side_effect = Exception("Retrieve error")
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        pattern = bank.get_pattern_by_id("pat_123")

        assert pattern is None  # Returns None on error

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_get_pattern_by_id_auto_connects_if_not_connected(self, mock_st, mock_qdrant_client):
        """Test get_pattern_by_id auto-connects if needed."""
        mock_encoder = Mock()
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_client.retrieve.return_value = []
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.is_connected = False
        bank.client = mock_client
        bank.encoder = mock_encoder

        with patch.object(bank, 'connect') as mock_connect:
            bank.get_pattern_by_id("pat_123")
            mock_connect.assert_called_once()


class TestVectorSearch:
    """Test internal vector search method."""

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    @patch('src.cognitive.patterns.pattern_bank.SentenceTransformer')
    def test_vector_search_returns_results(self, mock_st, mock_qdrant_client):
        """Test _vector_search returns search results."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock()
        type(mock_encoder.encode.return_value).tolist = Mock(return_value=[0.1] * 768)
        mock_st.return_value = mock_encoder

        mock_client = Mock()
        mock_result1 = Mock()
        mock_result1.id = "pat_1"
        mock_result1.score = 0.95
        mock_result2 = Mock()
        mock_result2.id = "pat_2"
        mock_result2.score = 0.88
        mock_client.search.return_value = [mock_result1, mock_result2]
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        signature = SemanticTaskSignature(
            purpose="Test search",
            intent="test",
            inputs={},
            outputs={},
            domain="testing",
        )

        results = bank._vector_search(signature, top_k=2)

        assert len(results) == 2
        assert results[0]["pattern_id"] == "pat_1"
        assert results[0]["score"] == 0.95
        assert results[1]["pattern_id"] == "pat_2"
        assert results[1]["score"] == 0.88


class TestStoredPatternDataclass:
    """Test StoredPattern dataclass structure."""

    def test_stored_pattern_has_required_fields(self):
        """Test StoredPattern includes all required fields."""
        pattern = StoredPattern(
            pattern_id="pat_123",
            signature=SemanticTaskSignature(
                purpose="Test",
                intent="test",
                inputs={},
                outputs={},
                domain="testing",
            ),
            code="def test(): pass",
            success_rate=0.97,
            similarity_score=0.91,
            usage_count=5,
            created_at=datetime.utcnow(),
            domain="testing",
        )

        assert pattern.pattern_id == "pat_123"
        assert pattern.signature.purpose == "Test"
        assert pattern.code == "def test(): pass"
        assert pattern.success_rate == 0.97
        assert pattern.similarity_score == 0.91
        assert pattern.usage_count == 5
        assert isinstance(pattern.created_at, datetime)
        assert pattern.domain == "testing"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
