"""
RAG Metrics Collection

Provides specialized metrics for monitoring RAG system performance.
Integrates with the global MetricsCollector for Prometheus exposition.
"""

from typing import Optional, Dict, Any
from src.observability.metrics_collector import MetricsCollector
from src.observability import get_logger

# Singleton metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None
_logger = get_logger("rag.metrics")


def get_rag_metrics() -> MetricsCollector:
    """
    Get or create the RAG metrics collector singleton.

    Returns:
        Shared MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        _logger.info("RAG metrics collector initialized")
    return _metrics_collector


class RAGMetrics:
    """
    RAG-specific metrics tracking.

    Tracks:
    - Embedding generation performance
    - Retrieval latency and accuracy
    - Cache hit rates
    - Feedback loop metrics
    - Vector store operations
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize RAG metrics.

        Args:
            metrics_collector: Optional metrics collector instance
        """
        self.metrics = metrics_collector or get_rag_metrics()
        self.logger = get_logger("rag.metrics")

    # === Embedding Metrics ===

    def record_embedding_generation(
        self,
        duration: float,
        count: int = 1,
        dimension: int = 384,
    ):
        """
        Record embedding generation metrics.

        Args:
            duration: Time taken in seconds
            count: Number of embeddings generated
            dimension: Embedding dimension
        """
        self.metrics.observe_histogram(
            "rag_embedding_duration_seconds",
            duration,
            labels={"dimension": str(dimension)},
            help_text="Time to generate embeddings"
        )

        self.metrics.increment_counter(
            "rag_embeddings_generated_total",
            value=count,
            labels={"dimension": str(dimension)},
            help_text="Total number of embeddings generated"
        )

        # Calculate embeddings per second
        if duration > 0:
            rate = count / duration
            self.metrics.set_gauge(
                "rag_embedding_generation_rate",
                rate,
                labels={"dimension": str(dimension)},
                help_text="Embeddings generated per second"
            )

    # === Retrieval Metrics ===

    def record_retrieval(
        self,
        duration: float,
        results_count: int,
        strategy: str,
        top_k: int,
        cache_hit: bool = False,
    ):
        """
        Record retrieval metrics.

        Args:
            duration: Retrieval time in seconds
            results_count: Number of results returned
            strategy: Retrieval strategy (similarity, mmr, hybrid)
            top_k: Requested number of results
            cache_hit: Whether cache was hit
        """
        labels = {"strategy": strategy}

        self.metrics.observe_histogram(
            "rag_retrieval_duration_seconds",
            duration,
            labels=labels,
            help_text="Time to retrieve examples"
        )

        self.metrics.increment_counter(
            "rag_retrievals_total",
            labels=labels,
            help_text="Total number of retrievals"
        )

        self.metrics.observe_histogram(
            "rag_retrieval_results_count",
            results_count,
            labels=labels,
            help_text="Number of results returned"
        )

        if cache_hit:
            self.metrics.increment_counter(
                "rag_retrieval_cache_hits_total",
                labels=labels,
                help_text="Cache hits"
            )
        else:
            self.metrics.increment_counter(
                "rag_retrieval_cache_misses_total",
                labels=labels,
                help_text="Cache misses"
            )

    def record_retrieval_error(self, strategy: str, error_type: str):
        """
        Record retrieval error.

        Args:
            strategy: Retrieval strategy
            error_type: Type of error
        """
        self.metrics.increment_counter(
            "rag_retrieval_errors_total",
            labels={"strategy": strategy, "error_type": error_type},
            help_text="Retrieval errors"
        )

    # === Context Building Metrics ===

    def record_context_building(
        self,
        duration: float,
        results_count: int,
        context_length: int,
        template: str,
        truncated: bool = False,
    ):
        """
        Record context building metrics.

        Args:
            duration: Time to build context in seconds
            results_count: Number of results used
            context_length: Final context length in characters
            template: Template type used
            truncated: Whether context was truncated
        """
        labels = {"template": template}

        self.metrics.observe_histogram(
            "rag_context_build_duration_seconds",
            duration,
            labels=labels,
            help_text="Time to build context"
        )

        self.metrics.increment_counter(
            "rag_context_builds_total",
            labels=labels,
            help_text="Total contexts built"
        )

        self.metrics.observe_histogram(
            "rag_context_length_chars",
            context_length,
            labels=labels,
            help_text="Context length in characters"
        )

        if truncated:
            self.metrics.increment_counter(
                "rag_context_truncations_total",
                labels=labels,
                help_text="Contexts that were truncated"
            )

    # === Vector Store Metrics ===

    def record_indexing(
        self,
        duration: float,
        count: int = 1,
        batch: bool = False,
    ):
        """
        Record indexing metrics.

        Args:
            duration: Indexing time in seconds
            count: Number of examples indexed
            batch: Whether this was batch indexing
        """
        labels = {"batch": str(batch).lower()}

        self.metrics.observe_histogram(
            "rag_indexing_duration_seconds",
            duration,
            labels=labels,
            help_text="Time to index examples"
        )

        self.metrics.increment_counter(
            "rag_examples_indexed_total",
            value=count,
            labels=labels,
            help_text="Total examples indexed"
        )

        # Calculate indexing rate
        if duration > 0:
            rate = count / duration
            self.metrics.set_gauge(
                "rag_indexing_rate",
                rate,
                labels=labels,
                help_text="Examples indexed per second"
            )

    def update_vector_store_stats(self, total_examples: int, collection_size_mb: float):
        """
        Update vector store statistics.

        Args:
            total_examples: Total examples in store
            collection_size_mb: Collection size in megabytes
        """
        self.metrics.set_gauge(
            "rag_vector_store_examples_total",
            total_examples,
            help_text="Total examples in vector store"
        )

        self.metrics.set_gauge(
            "rag_vector_store_size_mb",
            collection_size_mb,
            help_text="Vector store size in MB"
        )

    # === Feedback Loop Metrics ===

    def record_feedback(
        self,
        feedback_type: str,
        auto_indexed: bool = False,
    ):
        """
        Record feedback event.

        Args:
            feedback_type: Type of feedback (approval, rejection, etc.)
            auto_indexed: Whether code was auto-indexed
        """
        self.metrics.increment_counter(
            "rag_feedback_events_total",
            labels={"type": feedback_type},
            help_text="Total feedback events"
        )

        if auto_indexed:
            self.metrics.increment_counter(
                "rag_auto_indexed_total",
                help_text="Examples auto-indexed from feedback"
            )

    def update_feedback_metrics(self, metrics: Dict[str, Any]):
        """
        Update feedback service metrics.

        Args:
            metrics: Metrics dictionary from feedback service
        """
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                self.metrics.set_gauge(
                    f"rag_feedback_{key}",
                    float(value),
                    help_text=f"Feedback metric: {key}"
                )

    # === Quality Metrics ===

    def record_similarity_score(self, score: float, strategy: str):
        """
        Record similarity score distribution.

        Args:
            score: Similarity score (0.0-1.0)
            strategy: Retrieval strategy
        """
        self.metrics.observe_histogram(
            "rag_similarity_scores",
            score,
            labels={"strategy": strategy},
            help_text="Distribution of similarity scores"
        )

    def record_mmr_score(self, score: float):
        """
        Record MMR score.

        Args:
            score: MMR score
        """
        self.metrics.observe_histogram(
            "rag_mmr_scores",
            score,
            help_text="Distribution of MMR scores"
        )

    # === Health Metrics ===

    def set_health_status(self, component: str, healthy: bool):
        """
        Set health status for RAG component.

        Args:
            component: Component name (embeddings, vector_store, retriever, etc.)
            healthy: Whether component is healthy
        """
        self.metrics.set_gauge(
            "rag_component_health",
            1.0 if healthy else 0.0,
            labels={"component": component},
            help_text="RAG component health (1=healthy, 0=unhealthy)"
        )

    # === Export ===

    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics
        """
        return self.metrics.export_prometheus()

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of RAG metrics.

        Returns:
            Dictionary with key metrics
        """
        summary = {}

        # Embedding stats
        embedding_stats = self.metrics.get_histogram_stats("rag_embedding_duration_seconds")
        if embedding_stats["count"] > 0:
            summary["embedding_avg_duration_ms"] = embedding_stats["avg"] * 1000
            summary["embeddings_generated"] = self.metrics.get_counter("rag_embeddings_generated_total")

        # Retrieval stats
        retrieval_stats = self.metrics.get_histogram_stats("rag_retrieval_duration_seconds")
        if retrieval_stats["count"] > 0:
            summary["retrieval_avg_duration_ms"] = retrieval_stats["avg"] * 1000
            summary["retrievals_total"] = self.metrics.get_counter("rag_retrievals_total")

            # Cache hit rate
            hits = self.metrics.get_counter("rag_retrieval_cache_hits_total")
            misses = self.metrics.get_counter("rag_retrieval_cache_misses_total")
            total = hits + misses
            if total > 0:
                summary["cache_hit_rate"] = hits / total

        # Indexing stats
        indexing_stats = self.metrics.get_histogram_stats("rag_indexing_duration_seconds")
        if indexing_stats["count"] > 0:
            summary["indexing_avg_duration_ms"] = indexing_stats["avg"] * 1000
            summary["examples_indexed"] = self.metrics.get_counter("rag_examples_indexed_total")

        # Vector store stats
        total_examples = self.metrics.get_gauge("rag_vector_store_examples_total")
        if total_examples is not None:
            summary["vector_store_examples"] = total_examples

        # Feedback stats
        summary["feedback_events"] = self.metrics.get_counter("rag_feedback_events_total")
        summary["auto_indexed"] = self.metrics.get_counter("rag_auto_indexed_total")

        return summary


# Global RAG metrics instance
_rag_metrics: Optional[RAGMetrics] = None


def get_rag_metrics_tracker() -> RAGMetrics:
    """
    Get or create the global RAG metrics tracker.

    Returns:
        Shared RAGMetrics instance
    """
    global _rag_metrics
    if _rag_metrics is None:
        _rag_metrics = RAGMetrics()
        _logger.info("RAG metrics tracker initialized")
    return _rag_metrics
