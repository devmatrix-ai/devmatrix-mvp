"""
RAG system API endpoints.

Provides endpoints for RAG operations, monitoring, and manual operations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from src.rag import (
    create_vector_store,
    create_retriever,
    create_feedback_service,
    create_embedding_model,
    RetrievalStrategy,
)
from src.rag.metrics import get_rag_metrics_tracker
from src.observability import get_logger

logger = get_logger("api.rag")
router = APIRouter(prefix="/rag", tags=["RAG"])

# Global instances (singleton pattern)
_embedding_model = None
_vector_store = None
_retriever = None
_feedback_service = None
_metrics = None


def get_instances():
    """Get or create RAG component instances."""
    global _embedding_model, _vector_store, _retriever, _feedback_service, _metrics

    try:
        if _embedding_model is None:
            _embedding_model = create_embedding_model()

        if _vector_store is None:
            _vector_store = create_vector_store(_embedding_model)

        if _retriever is None:
            _retriever = create_retriever(_vector_store, strategy=RetrievalStrategy.MMR)

        if _feedback_service is None:
            _feedback_service = create_feedback_service(_vector_store)

        if _metrics is None:
            _metrics = get_rag_metrics_tracker()

        return _vector_store, _retriever, _feedback_service, _metrics

    except Exception as e:
        logger.error("Failed to initialize RAG components", error=str(e))
        raise HTTPException(status_code=503, detail=f"RAG system unavailable: {str(e)}")


# Request/Response Models
class QueryRequest(BaseModel):
    """Query request model."""
    query: str
    top_k: Optional[int] = 5
    min_similarity: Optional[float] = 0.7
    strategy: Optional[str] = "mmr"
    filters: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    """Index request model."""
    code: str
    metadata: Dict[str, Any]


class BatchIndexRequest(BaseModel):
    """Batch index request model."""
    codes: List[str]
    metadatas: List[Dict[str, Any]]


class FeedbackRequest(BaseModel):
    """Feedback request model."""
    code: str
    feedback_type: str
    task_description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Endpoints

@router.get("/health")
async def rag_health_check() -> Dict[str, Any]:
    """
    Check RAG system health.

    Returns:
        Health status of all RAG components
    """
    try:
        vector_store, retriever, feedback_service, metrics = get_instances()

        # Test ChromaDB connection
        is_healthy, message = vector_store.health_check()

        if not is_healthy:
            return {
                "status": "unhealthy",
                "chromadb": "disconnected",
                "error": message
            }

        # Get stats
        stats = vector_store.get_stats()

        return {
            "status": "healthy",
            "chromadb": "connected",
            "components": {
                "vector_store": "operational",
                "retriever": "operational",
                "feedback_service": "operational",
                "metrics": "operational"
            },
            "statistics": {
                "total_examples": stats.get("total_examples", 0),
                "collection_name": stats.get("collection_name", "unknown")
            }
        }

    except Exception as e:
        logger.error("RAG health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/stats")
async def get_rag_stats() -> Dict[str, Any]:
    """
    Get RAG system statistics.

    Returns:
        Detailed statistics from vector store
    """
    try:
        vector_store, _, _, _ = get_instances()
        stats = vector_store.get_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error("Failed to get RAG stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_rag_metrics() -> Dict[str, Any]:
    """
    Get RAG system metrics.

    Returns:
        Metrics summary including performance and quality metrics
    """
    try:
        _, _, _, metrics = get_instances()
        summary = metrics.get_summary()

        return {
            "status": "success",
            "data": summary
        }

    except Exception as e:
        logger.error("Failed to get RAG metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/prometheus")
async def get_prometheus_metrics() -> str:
    """
    Get metrics in Prometheus format.

    Returns:
        Prometheus-formatted metrics for scraping
    """
    try:
        _, _, _, metrics = get_instances()
        return metrics.export_prometheus()

    except Exception as e:
        logger.error("Failed to export Prometheus metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_rag(request: QueryRequest) -> Dict[str, Any]:
    """
    Query the RAG system for similar code examples.

    Args:
        request: Query parameters

    Returns:
        List of similar code examples with metadata
    """
    try:
        _, retriever, _, metrics = get_instances()

        # Map string strategy to enum
        strategy_map = {
            "similarity": RetrievalStrategy.SIMILARITY,
            "mmr": RetrievalStrategy.MMR,
            "hybrid": RetrievalStrategy.HYBRID,
        }
        strategy = strategy_map.get(request.strategy.lower(), RetrievalStrategy.MMR)

        # Retrieve similar examples
        import time
        start = time.time()

        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            filters=request.filters,
            strategy=strategy
        )

        duration = time.time() - start

        # Record metrics
        metrics.record_retrieval(
            duration=duration,
            results_count=len(results),
            strategy=request.strategy,
            top_k=request.top_k,
            cache_hit=False  # API calls don't use cache
        )

        # Format results
        formatted_results = [
            {
                "id": r.id,
                "code": r.code,
                "metadata": r.metadata,
                "similarity": r.similarity,
                "rank": r.rank,
                "relevance_score": r.relevance_score,
            }
            for r in results
        ]

        return {
            "status": "success",
            "query": request.query,
            "strategy": request.strategy,
            "results_count": len(results),
            "duration_seconds": duration,
            "results": formatted_results
        }

    except Exception as e:
        logger.error("Query failed", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def index_code(request: IndexRequest) -> Dict[str, Any]:
    """
    Index a single code example.

    Args:
        request: Code and metadata to index

    Returns:
        Indexed code ID
    """
    try:
        vector_store, _, _, metrics = get_instances()

        # Validate code
        if not request.code or not request.code.strip():
            raise HTTPException(status_code=400, detail="Code cannot be empty")

        # Index code
        import time
        start = time.time()

        code_id = vector_store.add_example(
            code=request.code,
            metadata=request.metadata
        )

        duration = time.time() - start

        # Record metrics
        metrics.record_indexing(duration=duration, count=1, batch=False)

        logger.info("Code indexed", code_id=code_id, duration=duration)

        return {
            "status": "success",
            "code_id": code_id,
            "duration_seconds": duration
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Indexing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/batch")
async def batch_index_code(request: BatchIndexRequest) -> Dict[str, Any]:
    """
    Index multiple code examples at once.

    Args:
        request: List of codes and metadata to index

    Returns:
        List of indexed code IDs
    """
    try:
        vector_store, _, _, metrics = get_instances()

        # Validate
        if len(request.codes) != len(request.metadatas):
            raise HTTPException(
                status_code=400,
                detail="Number of codes must match number of metadata entries"
            )

        # Batch index
        import time
        start = time.time()

        code_ids = vector_store.add_batch(
            codes=request.codes,
            metadatas=request.metadatas
        )

        duration = time.time() - start

        # Record metrics
        metrics.record_indexing(duration=duration, count=len(code_ids), batch=True)

        logger.info(
            "Batch indexed",
            count=len(code_ids),
            duration=duration,
            rate=len(code_ids) / duration if duration > 0 else 0
        )

        return {
            "status": "success",
            "indexed_count": len(code_ids),
            "code_ids": code_ids,
            "duration_seconds": duration,
            "rate_per_second": len(code_ids) / duration if duration > 0 else 0
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Batch indexing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest) -> Dict[str, Any]:
    """
    Submit feedback for generated code.

    Args:
        request: Feedback details

    Returns:
        Feedback ID
    """
    try:
        _, _, feedback_service, metrics = get_instances()

        # Submit feedback based on type
        if request.feedback_type.lower() == "approval":
            feedback_id = feedback_service.record_approval(
                code=request.code,
                metadata=request.metadata or {},
                task_description=request.task_description
            )
            metrics.record_feedback(feedback_type="approval", auto_indexed=True)

        elif request.feedback_type.lower() == "rejection":
            feedback_id = feedback_service.record_rejection(
                code=request.code,
                metadata=request.metadata or {},
                reason=request.task_description or "No reason provided"
            )
            metrics.record_feedback(feedback_type="rejection", auto_indexed=False)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feedback type: {request.feedback_type}"
            )

        logger.info(
            "Feedback recorded",
            feedback_id=feedback_id,
            feedback_type=request.feedback_type
        )

        return {
            "status": "success",
            "feedback_id": feedback_id,
            "feedback_type": request.feedback_type,
            "auto_indexed": request.feedback_type.lower() == "approval"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Feedback submission failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/metrics")
async def get_feedback_metrics() -> Dict[str, Any]:
    """
    Get feedback service metrics.

    Returns:
        Feedback metrics including approval rates
    """
    try:
        _, _, feedback_service, _ = get_instances()
        metrics = feedback_service.get_metrics()

        return {
            "status": "success",
            "data": metrics
        }

    except Exception as e:
        logger.error("Failed to get feedback metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_cache() -> Dict[str, Any]:
    """
    Clear the retrieval cache.

    Returns:
        Number of cache entries cleared
    """
    try:
        _, retriever, _, _ = get_instances()
        count = retriever.clear_cache()

        logger.info("Cache cleared", entries_cleared=count)

        return {
            "status": "success",
            "entries_cleared": count
        }

    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_rag_config() -> Dict[str, Any]:
    """
    Get current RAG configuration.

    Returns:
        RAG system configuration
    """
    try:
        _, retriever, _, _ = get_instances()
        stats = retriever.get_stats()

        return {
            "status": "success",
            "config": stats
        }

    except Exception as e:
        logger.error("Failed to get config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
