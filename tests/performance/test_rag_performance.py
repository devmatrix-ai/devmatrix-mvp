"""
Performance tests and benchmarks for RAG system.

Tests embedding generation speed, retrieval performance, and scaling behavior.

To run: pytest tests/performance/test_rag_performance.py -v -s
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
import numpy as np

from src.rag.embeddings import EmbeddingModel
from src.rag.retriever import Retriever, RetrievalResult, RetrievalConfig, RetrievalStrategy
from src.rag.context_builder import ContextBuilder, ContextConfig, ContextTemplate


class TestEmbeddingPerformance:
    """Test embedding generation performance."""

    def test_single_embedding_speed(self):
        """Test single embedding generation speed."""
        model = EmbeddingModel()

        code = "def test_function(): pass"

        start = time.time()
        embedding = model.embed_text(code)
        duration = time.time() - start

        assert len(embedding) == model.dimension
        assert duration < 0.5  # Should complete in < 500ms

        print(f"\nSingle embedding generated in {duration*1000:.1f}ms")

    def test_batch_embedding_speed(self):
        """Test batch embedding generation speed."""
        model = EmbeddingModel()

        # Generate embeddings for 100 code snippets
        codes = [f"def function_{i}(): pass" for i in range(100)]

        start = time.time()
        embeddings = model.embed_batch(codes, batch_size=32)
        duration = time.time() - start

        assert len(embeddings) == 100
        assert duration < 5.0  # Should complete in < 5 seconds

        rate = len(codes) / duration
        print(f"\nGenerated {len(codes)} embeddings in {duration:.2f}s ({rate:.1f} codes/sec)")

    def test_embedding_consistency(self):
        """Test that same code produces same embedding."""
        model = EmbeddingModel()

        code = "def consistent_test(): return True"

        embedding1 = model.embed_text(code)
        embedding2 = model.embed_text(code)

        # Should be identical
        assert np.allclose(embedding1, embedding2, rtol=1e-5)

    def test_large_batch_performance(self):
        """Test performance with large batch."""
        model = EmbeddingModel()

        # 500 code snippets
        codes = [f"def large_batch_{i}(): return {i}" for i in range(500)]

        start = time.time()
        embeddings = model.embed_batch(codes, batch_size=50)
        duration = time.time() - start

        assert len(embeddings) == 500
        assert duration < 20.0  # Should complete in < 20 seconds

        rate = len(codes) / duration
        print(f"\nGenerated {len(codes)} embeddings in {duration:.2f}s ({rate:.1f} codes/sec)")


class TestRetrievalPerformance:
    """Test retrieval performance with mocked vector store."""

    @pytest.fixture
    def mock_retrieval_setup(self):
        """Setup mock retrieval components."""
        mock_vector_store = Mock()

        # Simulate 50 stored examples
        num_examples = 50
        mock_results = []

        for i in range(num_examples):
            mock_results.append({
                'id': f'code_{i}',
                'code': f'def function_{i}(): pass',
                'metadata': {'language': 'python', 'index': i},
                'similarity': 0.9 - (i * 0.01),  # Decreasing similarity
            })

        # Mock search_with_metadata (not search) - this is what Retriever calls
        mock_vector_store.search_with_metadata.return_value = mock_results

        # Mock embedding_model for MMR (MMR needs embeddings)
        mock_embedding_model = Mock()
        mock_embedding_model.embed_text.return_value = np.random.rand(384).tolist()
        mock_embedding_model.embed_batch.return_value = [
            np.random.rand(384).tolist() for _ in range(num_examples)
        ]
        mock_vector_store.embedding_model = mock_embedding_model

        config = RetrievalConfig(
            strategy=RetrievalStrategy.MMR,
            top_k=5,
            rerank=True,
            cache_enabled=False  # Disable cache for performance testing
        )

        retriever = Retriever(mock_vector_store, config)

        return retriever, mock_vector_store

    def test_retrieval_speed_basic(self, mock_retrieval_setup):
        """Test basic retrieval speed."""
        retriever, _ = mock_retrieval_setup

        query = "implement authentication function"

        start = time.time()
        results = retriever.retrieve(query, top_k=5)
        duration = time.time() - start

        assert len(results) <= 5
        assert duration < 1.0  # Should complete in < 1 second

        print(f"\nRetrieval completed in {duration*1000:.1f}ms")

    def test_batch_retrieval_performance(self, mock_retrieval_setup):
        """Test multiple retrieval performance."""
        retriever, _ = mock_retrieval_setup

        queries = [f"implement feature {i}" for i in range(20)]

        start = time.time()
        all_results = []
        for query in queries:
            results = retriever.retrieve(query, top_k=5)
            all_results.append(results)
        duration = time.time() - start

        assert len(all_results) == 20
        assert duration < 5.0  # Should complete in < 5 seconds

        rate = len(queries) / duration
        print(f"\nPerformed {len(queries)} retrievals in {duration:.2f}s ({rate:.1f} queries/sec)")

    def test_mmr_algorithm_performance(self, mock_retrieval_setup):
        """Test MMR algorithm performance."""
        retriever, _ = mock_retrieval_setup

        # MMR requires additional computation
        query = "test function"

        start = time.time()
        results = retriever.retrieve(query, top_k=10)
        duration = time.time() - start

        assert len(results) <= 10
        assert duration < 2.0  # MMR should complete in < 2 seconds

        print(f"\nMMR retrieval completed in {duration*1000:.1f}ms")

    def test_cache_performance_impact(self):
        """Test cache hit vs miss performance."""
        mock_vector_store = Mock()
        mock_vector_store.search_with_metadata.return_value = []

        # With cache enabled
        config_cached = RetrievalConfig(
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            cache_enabled=True
        )

        retriever_cached = Retriever(mock_vector_store, config_cached)

        query = "cached test query"

        # First call (cache miss)
        start = time.time()
        retriever_cached.retrieve(query)
        miss_duration = time.time() - start

        # Second call (cache hit)
        start = time.time()
        retriever_cached.retrieve(query)
        hit_duration = time.time() - start

        # Cache hit should be faster
        assert hit_duration < miss_duration

        speedup = miss_duration / hit_duration if hit_duration > 0 else float('inf')
        print(f"\nCache speedup: {speedup:.1f}x faster (miss: {miss_duration*1000:.1f}ms, hit: {hit_duration*1000:.1f}ms)")


class TestContextBuildingPerformance:
    """Test context building performance."""

    @pytest.fixture
    def sample_results(self):
        """Create sample retrieval results."""
        results = []
        for i in range(10):
            results.append(
                RetrievalResult(
                    id=f"id_{i}",
                    code=f"def function_{i}():\n" + "    pass\n" * 10,
                    metadata={'language': 'python', 'approved': i % 2 == 0},
                    similarity=0.9 - (i * 0.05),
                    rank=i + 1,
                    relevance_score=0.95 - (i * 0.05)
                )
            )
        return results

    def test_simple_template_speed(self, sample_results):
        """Test SIMPLE template building speed."""
        builder = ContextBuilder(ContextConfig(template=ContextTemplate.SIMPLE))

        start = time.time()
        context = builder.build_context("test query", sample_results)
        duration = time.time() - start

        assert len(context) > 0
        assert duration < 0.1  # Should complete in < 100ms

        print(f"\nSIMPLE template built in {duration*1000:.1f}ms ({len(context)} chars)")

    def test_detailed_template_speed(self, sample_results):
        """Test DETAILED template building speed."""
        builder = ContextBuilder(ContextConfig(template=ContextTemplate.DETAILED))

        start = time.time()
        context = builder.build_context("test query", sample_results)
        duration = time.time() - start

        assert len(context) > 0
        assert duration < 0.2  # Should complete in < 200ms

        print(f"\nDETAILED template built in {duration*1000:.1f}ms ({len(context)} chars)")

    def test_structured_template_speed(self, sample_results):
        """Test STRUCTURED template building speed."""
        builder = ContextBuilder(ContextConfig(template=ContextTemplate.STRUCTURED))

        start = time.time()
        context = builder.build_context("test query", sample_results)
        duration = time.time() - start

        assert len(context) > 0
        assert duration < 0.2  # Should complete in < 200ms

        print(f"\nSTRUCTURED template built in {duration*1000:.1f}ms ({len(context)} chars)")

    def test_large_context_performance(self):
        """Test performance with many large results."""
        # Create 50 large results
        large_results = []
        for i in range(50):
            large_results.append(
                RetrievalResult(
                    id=f"id_{i}",
                    code="def large_function():\n" + "    pass\n" * 100,  # ~600 chars each
                    metadata={'language': 'python'},
                    similarity=0.9,
                    rank=i + 1
                )
            )

        builder = ContextBuilder(ContextConfig(
            template=ContextTemplate.DETAILED,
            max_length=50000  # Allow large context
        ))

        start = time.time()
        context = builder.build_context("test query", large_results)
        duration = time.time() - start

        assert len(context) > 0
        assert duration < 1.0  # Should complete in < 1 second

        print(f"\nLarge context ({len(large_results)} results) built in {duration*1000:.1f}ms ({len(context)} chars)")

    def test_truncation_performance(self):
        """Test performance impact of truncation."""
        results = []
        for i in range(20):
            results.append(
                RetrievalResult(
                    id=f"id_{i}",
                    code="x" * 5000,  # Very long code
                    metadata={},
                    similarity=0.9,
                    rank=i + 1
                )
            )

        # With truncation
        builder_truncate = ContextBuilder(ContextConfig(
            truncate_code=True,
            max_code_length=100
        ))

        start = time.time()
        context_truncated = builder_truncate.build_context("test", results)
        truncate_duration = time.time() - start

        # Without truncation (will hit max_length limit)
        builder_no_truncate = ContextBuilder(ContextConfig(
            truncate_code=False,
            max_length=200000
        ))

        start = time.time()
        context_full = builder_no_truncate.build_context("test", results)
        full_duration = time.time() - start

        assert len(context_truncated) < len(context_full)
        # Truncation should be faster for large codes
        print(f"\nTruncation: {truncate_duration*1000:.1f}ms ({len(context_truncated)} chars)")
        print(f"No truncation: {full_duration*1000:.1f}ms ({len(context_full)} chars)")


class TestScalingBehavior:
    """Test scaling behavior with increasing data size."""

    def test_retrieval_scaling(self):
        """Test how retrieval performance scales with data size."""
        mock_vector_store = Mock()

        sizes = [100, 500, 1000, 5000]
        durations = []

        for size in sizes:
            # Simulate different sized datasets
            mock_results = [
                {
                    'id': f'code_{i}',
                    'code': f'def func_{i}(): pass',
                    'metadata': {},
                    'similarity': 0.9 - (i * 0.0001),
                }
                for i in range(min(size, 100))  # Return max 100 results
            ]

            mock_vector_store.search_with_metadata.return_value = mock_results

            config = RetrievalConfig(
                strategy=RetrievalStrategy.SIMILARITY,
                top_k=5,
                cache_enabled=False
            )

            retriever = Retriever(mock_vector_store, config)

            start = time.time()
            retriever.retrieve("test query")
            duration = time.time() - start
            durations.append(duration)

        print(f"\nScaling test:")
        for size, duration in zip(sizes, durations):
            print(f"  {size} examples: {duration*1000:.1f}ms")

        # Should scale sub-linearly
        assert all(d < 1.0 for d in durations)


class TestMemoryUsage:
    """Test memory efficiency."""

    def test_embedding_memory(self):
        """Test memory footprint of embeddings."""
        model = EmbeddingModel()

        # Single embedding
        embedding = model.embed_text("test code")

        # Each float64 is 8 bytes, so 384-dim should be ~3KB
        import sys
        size_bytes = sys.getsizeof(embedding)

        print(f"\nSingle embedding memory: {size_bytes} bytes ({size_bytes/1024:.1f} KB)")

        # Should be reasonable size
        assert size_bytes < 10000  # < 10KB

    def test_context_memory_efficiency(self, sample_results=[]):
        """Test context memory efficiency."""
        # Create sample if not provided
        if not sample_results:
            sample_results = [
                RetrievalResult(
                    id=f"id_{i}",
                    code="def test(): pass" * 10,
                    metadata={'language': 'python'},
                    similarity=0.9,
                    rank=i + 1
                )
                for i in range(10)
            ]

        builder = ContextBuilder()

        context = builder.build_context("test", sample_results)

        import sys
        size_bytes = sys.getsizeof(context)

        print(f"\nContext memory: {size_bytes} bytes ({size_bytes/1024:.1f} KB)")

        # Should be efficient
        assert size_bytes < 100000  # < 100KB for 10 results
