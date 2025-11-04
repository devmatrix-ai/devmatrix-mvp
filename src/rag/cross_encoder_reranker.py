"""
Cross-Encoder Based Re-ranker for RAG

Uses BERT-based cross-encoders for semantic re-ranking of retrieval results.
Cross-encoders understand query-document relationships better than dual-encoders.
"""

from typing import List, Optional
import numpy as np

from src.observability import get_logger


class CrossEncoderReranker:
    """Re-ranks results using cross-encoder semantic similarity."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k: int = 5,
        min_score: float = 0.0,
    ):
        """
        Initialize cross-encoder re-ranker.

        Args:
            model_name: HuggingFace model ID for cross-encoder
                       "cross-encoder/ms-marco-MiniLM-L-6-v2" is lightweight (~180MB)
            top_k: Return top-k results after re-ranking
            min_score: Minimum score threshold for results
        """
        self.logger = get_logger("rag.cross_encoder_reranker")
        self.model_name = model_name
        self.top_k = top_k
        self.min_score = min_score
        self.model = None

        # Lazy load model on first use
        self._model_loaded = False

    def _ensure_model_loaded(self):
        """Load model on first use (lazy loading)."""
        if self._model_loaded:
            return

        try:
            from sentence_transformers import CrossEncoder

            self.logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            self._model_loaded = True
            self.logger.info("Cross-encoder model loaded successfully")

        except ImportError:
            self.logger.warning(
                "sentence_transformers not installed. Install with: "
                "pip install sentence-transformers"
            )
            self.model = None
            self._model_loaded = True

        except Exception as e:
            self.logger.error(
                f"Failed to load cross-encoder model",
                error=str(e),
                model=self.model_name
            )
            self.model = None
            self._model_loaded = True

    def rerank(
        self,
        query: str,
        results: List["RetrievalResult"],
        return_scores: bool = False,
    ) -> List["RetrievalResult"]:
        """
        Re-rank results using cross-encoder semantic similarity.

        Args:
            query: Original query text
            results: Retrieved results to re-rank
            return_scores: Whether to return (result, score) tuples

        Returns:
            Re-ranked results (or list of (result, score) tuples if return_scores=True)
        """
        if not results:
            return results if not return_scores else []

        # Ensure model is loaded
        self._ensure_model_loaded()

        # Fallback if model unavailable
        if self.model is None:
            self.logger.warning("Cross-encoder unavailable, returning results unchanged")
            return results

        try:
            # Extract result codes
            result_codes = []
            for result in results:
                code = getattr(result, "code", None) or getattr(result, "content", "")
                result_codes.append(code)

            # Prepare query-document pairs for cross-encoder
            query_doc_pairs = [[query, code] for code in result_codes]

            # Get cross-encoder scores
            self.logger.debug(
                f"Cross-encoder scoring {len(results)} results",
                result_count=len(results)
            )

            scores = self.model.predict(query_doc_pairs, show_progress_bar=False)

            # If scores are 2D (multi-label), take the first column
            if len(scores.shape) > 1:
                scores = scores[:, 0]

            # Create (result, score) pairs
            result_score_pairs = list(zip(results, scores))

            # Filter by min_score if set
            if self.min_score > 0:
                result_score_pairs = [
                    (r, s) for r, s in result_score_pairs
                    if s >= self.min_score
                ]

            # Sort by score (descending)
            result_score_pairs.sort(key=lambda x: x[1], reverse=True)

            # Take top-k
            final_pairs = result_score_pairs[:self.top_k]

            # Update results with cross-encoder scores
            for i, (result, score) in enumerate(final_pairs, 1):
                result.rank = i
                result.relevance_score = float(score)
                # Store cross-encoder score in metadata for debugging
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["cross_encoder_score"] = float(score)

            self.logger.info(
                f"Cross-encoder re-ranking complete",
                input_count=len(results),
                output_count=len(final_pairs),
                min_score=self.min_score,
                top_k=self.top_k,
            )

            if return_scores:
                return [(r, s) for r, s in final_pairs]
            else:
                return [r for r, _ in final_pairs]

        except Exception as e:
            self.logger.error(
                f"Cross-encoder re-ranking failed",
                error=str(e),
                result_count=len(results)
            )
            # Fallback: return results unchanged
            return results

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        self._ensure_model_loaded()

        if self.model is None:
            return {
                "status": "unavailable",
                "reason": "Model failed to load or sentence-transformers not installed",
            }

        try:
            return {
                "status": "loaded",
                "model": self.model_name,
                "model_type": type(self.model).__name__,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }


def create_cross_encoder_reranker(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    top_k: int = 5,
) -> CrossEncoderReranker:
    """Factory function to create cross-encoder re-ranker."""
    return CrossEncoderReranker(
        model_name=model_name,
        top_k=top_k,
    )
