#!/usr/bin/env python
"""
ChromaDB Validation Script

Validates ChromaDB installation and connectivity for the RAG system.
Tests all major operations to ensure the vector store is working correctly.

Usage:
    python scripts/validate_chromadb.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
    create_retriever,
    RetrievalStrategy,
)
from src.observability import get_logger

logger = get_logger("validate_chromadb")


def test_chromadb_connection():
    """Test basic ChromaDB connection."""
    print("\n🔍 Testing ChromaDB connection...")

    try:
        embedding_model = create_embedding_model()
        vector_store = create_vector_store(
            embedding_model,
            collection_name="validation_test"
        )

        is_healthy, message = vector_store.health_check()

        if is_healthy:
            print(f"  ✅ ChromaDB connection: {message}")
            return vector_store
        else:
            print(f"  ❌ ChromaDB unhealthy: {message}")
            return None

    except Exception as e:
        print(f"  ❌ Connection failed: {str(e)}")
        return None


def test_embedding_generation(embedding_model):
    """Test embedding generation."""
    print("\n🧪 Testing embedding generation...")

    try:
        test_code = "def hello_world(): return 'Hello, World!'"

        # Single embedding
        embedding = embedding_model.embed_text(test_code)
        print(f"  ✅ Single embedding: dimension={len(embedding)}")

        # Batch embeddings
        codes = [f"def function_{i}(): pass" for i in range(10)]
        embeddings = embedding_model.embed_batch(codes, batch_size=5)
        print(f"  ✅ Batch embeddings: count={len(embeddings)}")

        return True

    except Exception as e:
        print(f"  ❌ Embedding generation failed: {str(e)}")
        return False


def test_indexing(vector_store):
    """Test adding examples to vector store."""
    print("\n📝 Testing indexing...")

    try:
        # Add single example
        code_id = vector_store.add_example(
            code="def add(a, b): return a + b",
            metadata={"language": "python", "type": "function"}
        )
        print(f"  ✅ Single add: id={code_id}")

        # Add batch
        codes = [
            "def multiply(a, b): return a * b",
            "def subtract(a, b): return a - b",
            "def divide(a, b): return a / b if b != 0 else None",
        ]
        metadatas = [
            {"language": "python", "type": "function", "operation": "multiply"},
            {"language": "python", "type": "function", "operation": "subtract"},
            {"language": "python", "type": "function", "operation": "divide"},
        ]

        batch_ids = vector_store.add_batch(codes, metadatas)
        print(f"  ✅ Batch add: count={len(batch_ids)}")

        return True

    except Exception as e:
        print(f"  ❌ Indexing failed: {str(e)}")
        return False


def test_retrieval(vector_store):
    """Test retrieval with different strategies."""
    print("\n🔍 Testing retrieval...")

    try:
        # Similarity search
        retriever = create_retriever(
            vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=3
        )

        results = retriever.retrieve("arithmetic function")
        print(f"  ✅ Similarity search: {len(results)} results")

        if results:
            print(f"    Top result similarity: {results[0].similarity:.3f}")

        # MMR search
        retriever_mmr = create_retriever(
            vector_store,
            strategy=RetrievalStrategy.MMR,
            top_k=3
        )

        results_mmr = retriever_mmr.retrieve("arithmetic function")
        print(f"  ✅ MMR search: {len(results_mmr)} results")

        # Test with metadata filter
        results_filtered = retriever.retrieve(
            "function",
            filters={"operation": "multiply"}
        )
        print(f"  ✅ Filtered search: {len(results_filtered)} results")

        return True

    except Exception as e:
        print(f"  ❌ Retrieval failed: {str(e)}")
        return False


def test_stats(vector_store):
    """Test getting vector store statistics."""
    print("\n📊 Testing statistics...")

    try:
        stats = vector_store.get_stats()

        print(f"  ✅ Stats retrieved:")
        print(f"    Collection: {stats.get('collection_name', 'unknown')}")
        print(f"    Total examples: {stats.get('total_examples', 0)}")
        print(f"    Embedding dimension: {stats.get('embedding_dimension', 0)}")

        return True

    except Exception as e:
        print(f"  ❌ Stats retrieval failed: {str(e)}")
        return False


def test_cleanup(vector_store):
    """Test cleanup operations."""
    print("\n🧹 Testing cleanup...")

    try:
        # Clear collection
        count = vector_store.clear_collection()
        print(f"  ✅ Cleared: {count} examples removed")

        # Verify empty
        stats = vector_store.get_stats()
        if stats.get('total_examples', 0) == 0:
            print(f"  ✅ Verification: Collection is empty")
        else:
            print(f"  ⚠️  Warning: Collection not empty after clear")

        return True

    except Exception as e:
        print(f"  ❌ Cleanup failed: {str(e)}")
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("ChromaDB Validation Script")
    print("=" * 60)

    results = {
        "connection": False,
        "embeddings": False,
        "indexing": False,
        "retrieval": False,
        "stats": False,
        "cleanup": False,
    }

    # Test 1: Connection
    vector_store = test_chromadb_connection()
    results["connection"] = vector_store is not None

    if not vector_store:
        print("\n❌ Critical: Cannot connect to ChromaDB. Please ensure:")
        print("  1. ChromaDB is running: docker-compose up chromadb -d")
        print("  2. CHROMADB_HOST and CHROMADB_PORT are correctly configured in .env")
        print("  3. Firewall allows connection to ChromaDB port")
        sys.exit(1)

    # Test 2: Embeddings
    try:
        embedding_model = create_embedding_model()
        results["embeddings"] = test_embedding_generation(embedding_model)
    except Exception as e:
        print(f"\n❌ Embedding model initialization failed: {str(e)}")

    # Test 3: Indexing
    if results["connection"]:
        results["indexing"] = test_indexing(vector_store)

    # Test 4: Retrieval
    if results["indexing"]:
        results["retrieval"] = test_retrieval(vector_store)

    # Test 5: Stats
    if results["connection"]:
        results["stats"] = test_stats(vector_store)

    # Test 6: Cleanup
    if results["connection"]:
        results["cleanup"] = test_cleanup(vector_store)

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name.replace('_', ' ').title()}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)

    if all_passed:
        print("🎉 All validation tests passed!")
        print("\nChromaDB is properly configured and ready for use.")
        return 0
    else:
        print("⚠️  Some validation tests failed.")
        print("\nPlease review the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
