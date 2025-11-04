"""
Hybrid Retriever - Combines Semantic + Keyword + Metadata Ranking

Implements multi-stage retrieval:
1. Semantic search (embeddings) - get broad candidate set
2. Keyword matching (BM25) - filter/re-rank by keyword relevance
3. Metadata ranking - boost by framework/task_type/pattern match

This addresses the limitation of pure semantic search for generic queries
like "Middleware patterns" (semantic score: 0.018).
"""

from typing import List, Dict, Any, Tuple
import re
from collections import defaultdict
from rank_bm25 import BM25Okapi

from src.observability import get_logger

logger = get_logger(__name__)


class HybridRetriever:
    """Hybrid retrieval system combining semantic, keyword, and metadata ranking."""

    def __init__(self, documents: List[Dict[str, Any]]):
        """
        Initialize hybrid retriever with documents.

        Args:
            documents: List of documents with 'id', 'code', 'metadatas'
        """
        self.documents = documents
        self.logger = logger

        # Build BM25 index on code content
        self.logger.info(f"Initializing BM25 index for {len(documents)} documents...")
        self.codes = [doc['code'] for doc in documents]
        self.tokenized_codes = [self._tokenize(code) for code in self.codes]
        self.bm25 = BM25Okapi(self.tokenized_codes)
        self.logger.info("✅ BM25 index ready")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def hybrid_search(
        self,
        query: str,
        semantic_results: List[Tuple[str, float]],
        top_k: int = 5,
        weights: Dict[str, float] = None
    ) -> List[Tuple[str, float, str]]:
        """
        Perform hybrid search combining semantic, keyword, and metadata.

        Args:
            query: Search query
            semantic_results: List of (doc_id, semantic_similarity) from ChromaDB
            top_k: Number of results to return
            weights: Weight distribution {'semantic': 0.5, 'keyword': 0.3, 'metadata': 0.2}

        Returns:
            List of (doc_id, hybrid_score, rank_reason)
        """
        if weights is None:
            weights = {'semantic': 0.5, 'keyword': 0.3, 'metadata': 0.2}

        self.logger.debug(
            f"Hybrid search with weights: semantic={weights['semantic']}, "
            f"keyword={weights['keyword']}, metadata={weights['metadata']}"
        )

        # Stage 1: Get semantic scores from ChromaDB results
        semantic_scores = {doc_id: score for doc_id, score in semantic_results}

        # Stage 2: Calculate BM25 keyword scores for query
        query_tokens = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(query_tokens)

        # Normalize BM25 scores to 0-1 range
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
        normalized_bm25 = {
            self.documents[i]['id']: score / max_bm25
            for i, score in enumerate(bm25_scores)
        }

        # Stage 3: Calculate metadata boost scores
        metadata_boost = self._calculate_metadata_boost(query)

        # Stage 4: Combine all scores
        hybrid_scores = {}
        for doc in self.documents:
            doc_id = doc['id']

            # Get scores (default 0 if not found)
            semantic_score = semantic_scores.get(doc_id, 0.0)
            keyword_score = normalized_bm25.get(doc_id, 0.0)
            metadata_score = metadata_boost.get(doc_id, 0.0)

            # Weighted combination
            hybrid_score = (
                weights['semantic'] * semantic_score +
                weights['keyword'] * keyword_score +
                weights['metadata'] * metadata_score
            )

            # Determine why this ranked high
            scores = {
                'semantic': semantic_score,
                'keyword': keyword_score,
                'metadata': metadata_score
            }
            dominant = max(scores, key=scores.get)

            hybrid_scores[doc_id] = (hybrid_score, dominant, scores)

        # Sort by hybrid score and return top-k
        ranked = sorted(
            [(doc_id, score, reason) for doc_id, (score, reason, _) in hybrid_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )

        self.logger.debug(
            f"Hybrid ranking complete",
            total_documents=len(hybrid_scores),
            top_result=f"{ranked[0][0]}={ranked[0][1]:.3f}({ranked[0][2]})" if ranked else None
        )

        return ranked[:top_k]

    def _calculate_metadata_boost(self, query: str) -> Dict[str, float]:
        """
        Calculate boost scores based on metadata matches.

        Strategy:
        - Match query keywords to framework/pattern/task_type
        - Boost documents with explicit metadata matches
        """
        boost_scores = defaultdict(float)

        # Extract keywords from query
        query_tokens = set(self._tokenize(query))

        for doc in self.documents:
            doc_id = doc['id']
            metadata = doc.get('metadatas', {})

            # Extract all metadata as searchable text
            metadata_text = ' '.join([
                str(metadata.get('framework', '')),
                str(metadata.get('pattern', '')),
                str(metadata.get('task_type', '')),
                str(metadata.get('language', '')),
                str(metadata.get('tags', ''))
            ]).lower()

            metadata_tokens = set(self._tokenize(metadata_text))

            # Calculate Jaccard similarity between query and metadata
            if query_tokens and metadata_tokens:
                intersection = len(query_tokens & metadata_tokens)
                union = len(query_tokens | metadata_tokens)
                jaccard_sim = intersection / union if union > 0 else 0
                boost_scores[doc_id] = jaccard_sim

        return dict(boost_scores)

    def get_candidate_set_from_semantic(
        self,
        semantic_results: List[Tuple[str, float]],
        candidate_expansion: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Expand candidate set from semantic results.

        For queries with low semantic similarity, expand the candidate set
        to allow keyword and metadata to help.

        Args:
            semantic_results: Initial semantic search results
            candidate_expansion: Multiply candidate set size by this factor

        Returns:
            Expanded semantic results
        """
        # If top result has low similarity, expand candidates
        if semantic_results and semantic_results[0][1] < 0.4:
            self.logger.debug(
                f"Low semantic similarity ({semantic_results[0][1]:.3f}), "
                f"expanding candidate set"
            )
            # Return more candidates to give keyword/metadata a chance
            expand_size = max(len(semantic_results) * candidate_expansion, 20)
            return semantic_results[:expand_size]

        return semantic_results

    def analyze_retrieval(
        self,
        query: str,
        results: List[Tuple[str, float, str]],
        doc_map: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze retrieval results for debugging and monitoring.

        Args:
            query: Original query
            results: Hybrid search results
            doc_map: Optional mapping of doc_id to full document

        Returns:
            Analysis dictionary with insights
        """
        if not results:
            return {'query': query, 'results': 0, 'analysis': 'No results'}

        analysis = {
            'query': query,
            'results_count': len(results),
            'top_result': results[0][0],
            'top_score': results[0][1],
            'top_reason': results[0][2],
            'score_distribution': {
                'semantic': sum(1 for r in results if r[2] == 'semantic') / len(results),
                'keyword': sum(1 for r in results if r[2] == 'keyword') / len(results),
                'metadata': sum(1 for r in results if r[2] == 'metadata') / len(results)
            }
        }

        return analysis


def create_hybrid_retriever(documents: List[Dict[str, Any]]) -> HybridRetriever:
    """Factory function to create HybridRetriever."""
    return HybridRetriever(documents)
