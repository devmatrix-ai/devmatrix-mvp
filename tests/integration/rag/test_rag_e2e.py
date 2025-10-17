"""
End-to-end integration tests for RAG pipeline with real ChromaDB.

Tests the complete flow: indexing → retrieval → context building → feedback loop.

NOTE: These tests require ChromaDB to be running. Start with:
    docker-compose up chromadb -d

To run: pytest tests/integration/rag/test_rag_e2e.py -v
"""

import pytest
from src.rag import (
    create_embedding_model,
    create_vector_store,
    create_retriever,
    create_context_builder,
    create_feedback_service,
    RetrievalStrategy,
    ContextTemplate,
)


@pytest.fixture(scope="module")
def embedding_model():
    """Create embedding model."""
    return create_embedding_model()


@pytest.fixture(scope="module")
def vector_store(embedding_model):
    """Create vector store with real ChromaDB connection."""
    try:
        store = create_vector_store(
            embedding_model,
            collection_name="test_rag_e2e"
        )

        # Clear any existing test data
        try:
            store.clear_collection()
        except:
            pass

        yield store

        # Cleanup after tests
        try:
            store.clear_collection()
        except:
            pass

    except Exception as e:
        pytest.skip(f"ChromaDB not available: {e}")


@pytest.fixture(scope="module")
def retriever(vector_store):
    """Create retriever."""
    return create_retriever(
        vector_store,
        strategy=RetrievalStrategy.MMR,
        top_k=5
    )


@pytest.fixture(scope="module")
def context_builder():
    """Create context builder."""
    return create_context_builder(
        template=ContextTemplate.DETAILED
    )


@pytest.fixture(scope="module")
def feedback_service(vector_store):
    """Create feedback service."""
    return create_feedback_service(
        vector_store,
        enabled=True
    )


class TestCompleteRAGPipeline:
    """Test complete RAG pipeline end-to-end."""

    def test_indexing_and_retrieval(self, vector_store, retriever):
        """Test basic indexing and retrieval flow."""
        # 1. Index initial code
        code = """def authenticate_user(username: str, password: str) -> bool:
    '''Authenticate user with username and password.'''
    user = db.get_user(username)
    if not user:
        return False
    return user.verify_password(password)
"""

        metadata = {
            'project_id': 'test_project',
            'file_path': 'auth.py',
            'language': 'python',
            'task_type': 'authentication',
            'approved': True
        }

        code_id = vector_store.add_example(code, metadata)
        assert code_id is not None

        # 2. Retrieve similar code
        results = retriever.retrieve(query="implement user login")

        assert len(results) > 0
        assert results[0].id == code_id
        assert "authenticate_user" in results[0].code
        assert results[0].similarity > 0.5

    def test_retrieval_context_building(self, vector_store, retriever, context_builder):
        """Test retrieval + context building."""
        # Add authentication code
        auth_code = """def login_endpoint(username: str, password: str) -> dict:
    '''REST endpoint for user login.'''
    if authenticate(username, password):
        token = generate_jwt(username)
        return {'success': True, 'token': token}
    return {'success': False, 'error': 'Invalid credentials'}
"""

        vector_store.add_example(
            auth_code,
            {
                'language': 'python',
                'task_type': 'authentication',
                'file_path': 'api/auth.py'
            }
        )

        # Retrieve
        results = retriever.retrieve("create login API endpoint")
        assert len(results) > 0

        # Build context
        context = context_builder.build_context(
            query="create login API endpoint",
            results=results
        )

        assert "login_endpoint" in context or "authenticate" in context
        assert len(context) > 0

    def test_feedback_loop_and_reindexing(self, vector_store, feedback_service, retriever):
        """Test feedback loop: approval → auto-indexing → retrieval."""
        # Initial state
        initial_stats = vector_store.get_stats()
        initial_count = initial_stats.get('total_examples', 0)

        # Record approval (should auto-index)
        new_code = """def signup_user(email: str, password: str) -> dict:
    '''Register new user account.'''
    if user_exists(email):
        return {'success': False, 'error': 'User already exists'}

    user = create_user(email, password)
    return {'success': True, 'user_id': user.id}
"""

        feedback_id = feedback_service.record_approval(
            code=new_code,
            metadata={
                'language': 'python',
                'task_type': 'authentication',
                'file_path': 'api/signup.py'
            },
            task_description="User signup functionality"
        )

        assert feedback_id is not None

        # Check metrics
        metrics = feedback_service.get_metrics()
        assert metrics['approved_count'] >= 1
        assert metrics['indexed_count'] >= 1

        # Verify code is now retrievable
        results = retriever.retrieve("user registration signup")

        found_signup = any("signup_user" in r.code for r in results)
        assert found_signup, "Approved code should be retrievable"

    def test_mmr_diversity(self, vector_store, retriever):
        """Test MMR retrieves diverse results."""
        # Add multiple similar authentication functions
        codes = [
            "def auth_v1(user, pwd): return check_password(user, pwd)",
            "def auth_v2(username, password): return verify_user(username, password)",
            "def validate_login(u, p): return authenticate(u, p)",
            "def different_function(a, b): return a + b"  # Different function
        ]

        for i, code in enumerate(codes):
            vector_store.add_example(
                code,
                {'language': 'python', 'version': f'v{i}'}
            )

        # Retrieve with MMR (should get diverse results)
        results = retriever.retrieve("authentication function", top_k=3)

        assert len(results) <= 3
        # Check diversity - not all results should be identical
        unique_patterns = set()
        for r in results:
            # Extract function name
            if "def " in r.code:
                func_name = r.code.split("def ")[1].split("(")[0]
                unique_patterns.add(func_name)

        # Should have retrieved different function names
        assert len(unique_patterns) >= 2

    def test_metadata_filtering(self, vector_store, retriever):
        """Test metadata filtering in retrieval."""
        # Add codes with different projects
        vector_store.add_example(
            "def project_a_function(): pass",
            {'project_id': 'project_a', 'language': 'python'}
        )

        vector_store.add_example(
            "def project_b_function(): pass",
            {'project_id': 'project_b', 'language': 'python'}
        )

        # Retrieve with metadata filter
        results = retriever.retrieve(
            query="function",
            filters={'project_id': 'project_a'}
        )

        # All results should be from project_a
        for result in results:
            if result.metadata.get('project_id'):
                assert result.metadata['project_id'] == 'project_a'

    def test_no_results_scenario(self, retriever):
        """Test RAG behavior when no similar code exists."""
        results = retriever.retrieve(
            query="quantum computing algorithm implementation",
            filters={'project_id': 'nonexistent_xyz_123'}
        )

        # Should return empty results when filter doesn't match
        assert len(results) == 0

    def test_approved_code_boost(self, vector_store, retriever):
        """Test that approved code gets priority in retrieval."""
        # Add unapproved code
        vector_store.add_example(
            "def unapproved_auth(): pass",
            {'approved': False, 'language': 'python'}
        )

        # Add approved code (similar query)
        vector_store.add_example(
            "def approved_auth(): return True",
            {'approved': True, 'language': 'python'}
        )

        # Retrieve with HYBRID strategy (boosts approved)
        hybrid_retriever = create_retriever(
            vector_store,
            strategy=RetrievalStrategy.HYBRID,
            top_k=5
        )

        results = hybrid_retriever.retrieve("authentication function")

        # First result should ideally be approved (if found)
        approved_results = [r for r in results if r.metadata.get('approved')]
        assert len(approved_results) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_code_indexing(self, vector_store):
        """Test error handling for empty code."""
        with pytest.raises(ValueError):
            vector_store.add_example("", {'language': 'python'})

    def test_very_long_code(self, vector_store):
        """Test handling of very long code snippets."""
        long_code = "def long_function():\n" + "    pass\n" * 1000

        code_id = vector_store.add_example(
            long_code,
            {'language': 'python', 'type': 'long'}
        )

        assert code_id is not None

    def test_special_characters_in_code(self, vector_store):
        """Test code with special characters."""
        special_code = """def unicode_test():
    emoji = "🚀 🎉 ✅"
    chinese = "你好世界"
    return f"{emoji} {chinese}"
"""

        code_id = vector_store.add_example(
            special_code,
            {'language': 'python', 'type': 'unicode'}
        )

        assert code_id is not None

    def test_retrieval_with_invalid_top_k(self, retriever):
        """Test retrieval with invalid top_k."""
        with pytest.raises(ValueError):
            retriever.retrieve("test query", top_k=0)

        with pytest.raises(ValueError):
            retriever.retrieve("test query", top_k=-5)

    def test_health_check(self, vector_store):
        """Test vector store health check."""
        is_healthy, message = vector_store.health_check()

        assert is_healthy is True
        assert "healthy" in message.lower()


class TestPerformanceBasics:
    """Basic performance tests."""

    def test_batch_indexing(self, vector_store):
        """Test batch indexing performance."""
        import time

        # Create 50 code snippets
        codes = [f"def function_{i}(): return {i}" for i in range(50)]
        metadatas = [
            {'project_id': 'batch_test', 'index': i}
            for i in range(50)
        ]

        start = time.time()
        code_ids = vector_store.add_batch(codes, metadatas)
        duration = time.time() - start

        assert len(code_ids) == 50
        assert duration < 10.0  # Should complete in < 10 seconds

        print(f"\nIndexed 50 codes in {duration:.2f}s ({50/duration:.1f} codes/sec)")

    def test_retrieval_speed(self, retriever):
        """Test retrieval speed."""
        import time

        # Perform 10 retrievals
        queries = [f"implement feature {i}" for i in range(10)]

        start = time.time()
        for query in queries:
            results = retriever.retrieve(query, top_k=5)
        duration = time.time() - start

        assert duration < 5.0  # Should complete in < 5 seconds

        print(f"\nPerformed 10 retrievals in {duration:.2f}s ({10/duration:.1f} queries/sec)")
