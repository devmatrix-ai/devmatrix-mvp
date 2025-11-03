"""
Lightweight RAG re-ranker.

Provides a simple heuristic re-ranking that can be enabled in the Retriever.
This avoids external API calls and improves ordering by favoring curated items
and medium-length snippets.
"""

from typing import List

from src.observability import get_logger


class Reranker:
    """Heuristic re-ranker for retrieval results."""

    def __init__(
        self,
        curated_bonus: float = 0.05,
        medium_len_min: int = 200,
        medium_len_max: int = 1200,
        medium_len_bonus: float = 0.02,
        short_long_penalty: float = -0.01,
        use_content_fallback: bool = True,
    ):
        self.logger = get_logger("rag.reranker")
        self.curated_bonus = curated_bonus
        self.medium_len_min = medium_len_min
        self.medium_len_max = medium_len_max
        self.medium_len_bonus = medium_len_bonus
        self.short_long_penalty = short_long_penalty
        self.use_content_fallback = use_content_fallback

    def rerank(self, query: str, results: List["RetrievalResult"]) -> List["RetrievalResult"]:
        """
        Re-rank results based on a simple composite score and return a new list.

        Score = base_similarity
                + curated_bonus
                + length_bonus (favor medium length)
        """
        if not results:
            return results

        def composite_score(r: "RetrievalResult") -> float:
            base = getattr(r, "similarity", 0.0) or 0.0
            meta = getattr(r, "metadata", {}) or {}
            source = str(meta.get("source_collection") or meta.get("collection") or "")
            curated_bonus = self.curated_bonus if "curated" in source else 0.0

            # Prefer code field; optionally fall back to content if configured
            text = getattr(r, "code", None)
            if (text is None or text == "") and self.use_content_fallback:
                text = getattr(r, "content", "") or ""
            if text is None:
                text = ""

            length = len(text)
            if self.medium_len_min <= length <= self.medium_len_max:
                length_bonus = self.medium_len_bonus
            elif length < max(0, self.medium_len_min // 2) or length > self.medium_len_max * 3 + 400:
                # Keep a mild penalty for extremely short/long snippets
                length_bonus = self.short_long_penalty
            else:
                length_bonus = 0.0

            return base + curated_bonus + length_bonus

        # Precompute scores to avoid duplicate computation during sort and assignment
        scored = [(r, composite_score(r)) for r in results]
        scored.sort(key=lambda t: t[1], reverse=True)
        ranked = [r for r, _ in scored]

        # Re-assign ranks and persist computed score
        for i, (r, score) in enumerate(scored, 1):
            r.rank = i
            r.relevance_score = score

        self.logger.debug(
            "Re-ranking complete",
            count=len(results)
        )

        return ranked


