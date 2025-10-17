"""
RAG (Retrieval-Augmented Generation) module for DevMatrix.

This module provides semantic code search and retrieval capabilities to improve
code generation accuracy by providing relevant examples to the LLM.

Components:
    - embeddings: Semantic embedding generation using sentence-transformers
    - vector_store: ChromaDB wrapper for storing and querying code embeddings
    - retriever: High-level retrieval interface with ranking and filtering
    - context_builder: Formats retrieved examples into LLM prompts
    - feedback_service: Learns from approved code to improve retrieval quality

Usage:
    from src.rag import (
        create_embedding_model,
        create_vector_store,
        create_retriever,
        RetrievalStrategy,
    )

    # Initialize components
    embeddings = create_embedding_model()
    vector_store = create_vector_store(embeddings)
    retriever = create_retriever(
        vector_store,
        strategy=RetrievalStrategy.MMR,
        top_k=5
    )

    # Add code examples
    vector_store.add_example(
        code="def hello(): return 'world'",
        metadata={"language": "python", "approved": True}
    )

    # Retrieve similar examples with diversity
    results = retriever.retrieve("greeting function")
    for result in results:
        print(f"Rank {result.rank}: {result.code[:50]}...")
"""

from src.rag.embeddings import EmbeddingModel, create_embedding_model
from src.rag.vector_store import VectorStore, create_vector_store
from src.rag.retriever import (
    Retriever,
    RetrievalResult,
    RetrievalConfig,
    RetrievalStrategy,
    create_retriever,
)
from src.rag.context_builder import (
    ContextBuilder,
    ContextConfig,
    ContextTemplate,
    create_context_builder,
)
from src.rag.feedback_service import (
    FeedbackService,
    FeedbackType,
    FeedbackEntry,
    FeedbackMetrics,
    create_feedback_service,
)
from src.rag.metrics import (
    RAGMetrics,
    get_rag_metrics_tracker,
    get_rag_metrics,
)
from src.rag.persistent_cache import (
    PersistentEmbeddingCache,
    CacheEntry,
    CacheStats,
    get_cache,
)

__all__ = [
    "EmbeddingModel",
    "create_embedding_model",
    "VectorStore",
    "create_vector_store",
    "Retriever",
    "RetrievalResult",
    "RetrievalConfig",
    "RetrievalStrategy",
    "create_retriever",
    "ContextBuilder",
    "ContextConfig",
    "ContextTemplate",
    "create_context_builder",
    "FeedbackService",
    "FeedbackType",
    "FeedbackEntry",
    "FeedbackMetrics",
    "create_feedback_service",
    "RAGMetrics",
    "get_rag_metrics_tracker",
    "get_rag_metrics",
    "PersistentEmbeddingCache",
    "CacheEntry",
    "CacheStats",
    "get_cache",
]
