"""
Unit Tests for Pattern Bank with Qdrant Integration

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

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
from unittest.mock import Mock, patch, MagicMock

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
        bank = PatternBank()

        assert bank is not None
        assert hasattr(bank, 'client')  # Qdrant client
        assert hasattr(bank, 'encoder')  # Sentence Transformers encoder
        assert bank.collection_name == "semantic_patterns"
        assert bank.embedding_dimension == 768

    def test_pattern_bank_initialization_custom_collection(self):
        """Test PatternBank with custom collection name."""
        bank = PatternBank(collection_name="custom_patterns")

        assert bank.collection_name == "custom_patterns"

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    def test_qdrant_client_connection_successful(self, mock_qdrant_client):
        """Test Qdrant client connects successfully."""
        mock_client = Mock()
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.connect()

        assert bank.is_connected is True
        mock_client.get_collections.assert_called_once()

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    def test_qdrant_client_connection_failure_raises_error(self, mock_qdrant_client):
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
    def test_collection_creation_with_correct_parameters(self, mock_qdrant_client):
        """Test collection created with 768 dimensions and cosine distance."""
        mock_client = Mock()
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.create_collection()

        # Verify collection creation with correct parameters
        call_args = mock_client.create_collection.call_args
        assert call_args[1]['collection_name'] == "semantic_patterns"
        assert call_args[1]['vectors_config'].size == 768
        assert call_args[1]['vectors_config'].distance == "Cosine"

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    def test_collection_already_exists_no_error(self, mock_qdrant_client):
        """Test creating existing collection doesn't raise error."""
        mock_client = Mock()
        mock_client.get_collection.return_value = Mock()  # Collection exists
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()

        # Should not raise error
        bank.create_collection()

    @patch('src.cognitive.patterns.pattern_bank.QdrantClient')
    def test_collection_deletion_successful(self, mock_qdrant_client):
        """Test collection can be deleted."""
        mock_client = Mock()
        mock_qdrant_client.return_value = mock_client

        bank = PatternBank()
        bank.delete_collection()

        mock_client.delete_collection.assert_called_once_with(
            collection_name="semantic_patterns"
        )


class TestPatternStorage:
    """Test pattern storage with validation."""

    def test_store_pattern_with_valid_success_rate(self):
        """Test storing pattern with success_rate ≥ 95%."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Validate email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        code = """
def validate_email(email: str) -> bool:
    return "@" in email and "." in email
"""

        pattern_id = bank.store_pattern(
            signature=signature,
            code=code,
            success_rate=0.96,  # Above 95% threshold
        )

        assert pattern_id is not None
        assert isinstance(pattern_id, str)

    def test_store_pattern_rejects_low_success_rate(self):
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

        with pytest.raises(ValueError, match="success_rate.*95%"):
            bank.store_pattern(
                signature=signature,
                code=code,
                success_rate=0.92,  # Below 95% threshold
            )

    def test_store_pattern_includes_correct_metadata(self):
        """Test stored pattern includes all required metadata."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Calculate tax",
            intent="calculate",
            inputs={"amount": "float", "rate": "float"},
            outputs={"tax": "float"},
            domain="financial",
        )

        code = "def calculate_tax(amount, rate): return amount * rate"

        with patch.object(bank, '_store_in_qdrant') as mock_store:
            bank.store_pattern(signature, code, success_rate=0.97)

            # Verify metadata structure
            call_args = mock_store.call_args[0]
            metadata = call_args[1]

            assert metadata['purpose'] == "Calculate tax"
            assert metadata['code'] == code
            assert metadata['domain'] == "financial"
            assert metadata['success_rate'] == 0.97
            assert metadata['usage_count'] == 0
            assert 'created_at' in metadata
            assert 'semantic_hash' in metadata


class TestPatternRetrieval:
    """Test pattern retrieval with similarity search."""

    def test_search_patterns_returns_top_k_results(self):
        """Test search returns requested number of results."""
        bank = PatternBank()

        query_signature = SemanticTaskSignature(
            purpose="Validate user email",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        results = bank.search_patterns(query_signature, top_k=5)

        assert isinstance(results, list)
        assert len(results) <= 5

    def test_search_patterns_filters_by_similarity_threshold(self):
        """Test search filters results by ≥85% similarity threshold."""
        bank = PatternBank()

        query_signature = SemanticTaskSignature(
            purpose="Check password strength",
            intent="validate",
            inputs={"password": "str"},
            outputs={"strength": "int"},
            domain="authentication",
        )

        results = bank.search_patterns(query_signature, similarity_threshold=0.85)

        # All results should have similarity ≥ 0.85
        for pattern in results:
            assert pattern.similarity_score >= 0.85

    def test_search_patterns_returns_sorted_by_similarity(self):
        """Test search results sorted by similarity (descending)."""
        bank = PatternBank()

        query_signature = SemanticTaskSignature(
            purpose="Format currency",
            intent="transform",
            inputs={"amount": "float"},
            outputs={"formatted": "str"},
            domain="financial",
        )

        results = bank.search_patterns(query_signature, top_k=10)

        # Verify descending order
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity_score >= results[i + 1].similarity_score

    def test_search_patterns_increments_usage_count(self):
        """Test search increments usage_count for returned patterns."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Sanitize HTML",
            intent="transform",
            inputs={"html": "str"},
            outputs={"safe_html": "str"},
            domain="security",
        )

        # Store pattern first
        pattern_id = bank.store_pattern(signature, "def sanitize(html): ...", 0.98)

        # Search should increment usage_count
        with patch.object(bank, '_increment_usage_count') as mock_increment:
            bank.search_patterns(signature, top_k=1)

            # Verify usage count was incremented
            mock_increment.assert_called()


class TestHybridSearch:
    """Test hybrid search combining vector and metadata filtering."""

    def test_hybrid_search_with_domain_filter(self):
        """Test hybrid search filters by domain."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Hash password",
            intent="transform",
            inputs={"password": "str"},
            outputs={"hash": "str"},
            domain="authentication",
        )

        results = bank.hybrid_search(
            signature,
            domain="authentication",  # Filter by domain
            top_k=5
        )

        # All results should be from authentication domain
        for pattern in results:
            assert pattern.domain == "authentication"

    def test_hybrid_search_combines_vector_and_metadata_scores(self):
        """Test hybrid search combines vector (70%) and metadata (30%) scores."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Encrypt data",
            intent="transform",
            inputs={"data": "str"},
            outputs={"encrypted": "str"},
            domain="security",
        )

        with patch.object(bank, '_vector_search') as mock_vector:
            with patch.object(bank, '_metadata_score') as mock_metadata:
                mock_vector.return_value = [{"pattern_id": "p1", "score": 0.9}]
                mock_metadata.return_value = 0.8

                results = bank.hybrid_search(signature, domain="security")

                # Verify scoring combination
                # Expected: 0.7 * 0.9 + 0.3 * 0.8 = 0.87
                assert abs(results[0].final_score - 0.87) < 0.01

    def test_hybrid_search_without_domain_uses_vector_only(self):
        """Test hybrid search without domain uses vector search only."""
        bank = PatternBank()

        signature = SemanticTaskSignature(
            purpose="Parse CSV",
            intent="transform",
            inputs={"csv_str": "str"},
            outputs={"rows": "List[dict]"},
            domain="data_processing",
        )

        results = bank.hybrid_search(signature, domain=None, top_k=3)

        # Should work without domain filter
        assert isinstance(results, list)


class TestPatternMetrics:
    """Test pattern metrics tracking."""

    def test_get_pattern_metrics_returns_aggregated_stats(self):
        """Test get_pattern_metrics returns comprehensive statistics."""
        bank = PatternBank()

        metrics = bank.get_pattern_metrics()

        assert isinstance(metrics, dict)
        assert 'total_patterns' in metrics
        assert 'avg_success_rate' in metrics
        assert 'avg_usage_count' in metrics
        assert 'domain_distribution' in metrics
        assert 'most_used_patterns' in metrics

    def test_update_pattern_success_rate(self):
        """Test updating success rate for existing pattern."""
        bank = PatternBank()

        # Store initial pattern
        signature = SemanticTaskSignature(
            purpose="Validate phone number",
            intent="validate",
            inputs={"phone": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        pattern_id = bank.store_pattern(signature, "def validate_phone(...)", 0.96)

        # Update success rate
        bank.update_pattern_success(pattern_id, new_success_rate=0.98)

        # Verify update
        pattern = bank.get_pattern_by_id(pattern_id)
        assert pattern.success_rate == 0.98

    def test_domain_distribution_tracks_all_domains(self):
        """Test domain distribution tracks patterns across all domains."""
        bank = PatternBank()

        metrics = bank.get_pattern_metrics()
        domain_dist = metrics['domain_distribution']

        assert isinstance(domain_dist, dict)
        # Example: {"authentication": 5, "financial": 3, "api": 2, ...}
        for domain, count in domain_dist.items():
            assert isinstance(domain, str)
            assert isinstance(count, int)
            assert count >= 0


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
