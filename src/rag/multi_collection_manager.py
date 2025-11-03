"""
Multi-Collection Manager for RAG System

Manages intelligent searches across multiple ChromaDB collections with fallback strategies.
Collections are organized by quality/source:
- devmatrix_curated: High-quality curated examples (priority)
- devmatrix_project_code: Actual project code (fallback)
- devmatrix_standards: Project standards and patterns (reference)
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

from src.config import (
    RAG_SIMILARITY_THRESHOLD_CURATED,
    RAG_SIMILARITY_THRESHOLD_PROJECT,
    RAG_SIMILARITY_THRESHOLD_STANDARDS,
)
from src.observability import get_logger
from .vector_store import VectorStore

logger = get_logger("rag.multi_collection_manager")


@dataclass
class SearchResult:
    """Result from a search query."""
    similarity: float
    content: str
    metadata: Dict[str, Any]
    collection: str
    id: Optional[str] = None


class MultiCollectionManager:
    """
    Manages searches across multiple collections with intelligent fallback.
    
    Strategy:
    1. Search in curated collection first (highest quality)
    2. If insufficient high-quality results, search in project code
    3. Combine and re-rank by similarity
    4. Filter by collection-specific thresholds
    """
    
    def __init__(self, embedding_model):
        """Initialize multi-collection manager."""
        self.embedding_model = embedding_model
        
        # Initialize separate vector stores for each collection
        self.curated = VectorStore(
            embedding_model,
            collection_name="devmatrix_curated",
        )
        self.project_code = VectorStore(
            embedding_model,
            collection_name="devmatrix_project_code",
        )
        self.standards = VectorStore(
            embedding_model,
            collection_name="devmatrix_standards",
        )
        
        logger.info("MultiCollectionManager initialized with 3 collections")
    
    def search_with_fallback(
        self,
        query: str,
        top_k: int = 5,
        include_low_quality: bool = False
    ) -> List[SearchResult]:
        """
        Search across collections with intelligent fallback.
        
        Args:
            query: Search query
            top_k: Number of results to return
            include_low_quality: Include results below thresholds
        
        Returns:
            List of SearchResult objects sorted by similarity
        """
        results: List[SearchResult] = []
        
        try:
            # Phase 1: Search in curated collection (highest priority)
            logger.info(f"Searching curated collection for: {query[:50]}...")
            curated_results = self.curated.search(query, top_k=top_k)
            
            curated_high_quality = []
            for result in curated_results:
                sim = result.get('similarity', 0)
                if sim >= RAG_SIMILARITY_THRESHOLD_CURATED or include_low_quality:
                    curated_high_quality.append(
                        SearchResult(
                            similarity=sim,
                            content=result.get('code', ''),
                            metadata=result.get('metadata', {}),
                            collection="curated",
                            id=result.get('id')
                        )
                    )
            
            results.extend(curated_high_quality)
            
            # Phase 2: If we don't have enough results, search project code
            if len(curated_high_quality) < top_k // 2:
                logger.info(f"Low curated results ({len(curated_high_quality)}), searching project code...")
                project_results = self.project_code.search(query, top_k=top_k)
                
                for result in project_results:
                    sim = result.get('similarity', 0)
                    if sim >= RAG_SIMILARITY_THRESHOLD_PROJECT or include_low_quality:
                        results.append(
                            SearchResult(
                                similarity=sim,
                                content=result.get('code', ''),
                                metadata=result.get('metadata', {}),
                                collection="project_code",
                                id=result.get('id')
                            )
                        )
            
            # Phase 3: Optionally search standards for context
            if len(results) < top_k * 0.7:
                logger.info("Supplementing with standards...")
                standards_results = self.standards.search(query, top_k=top_k // 3)
                
                for result in standards_results:
                    sim = result.get('similarity', 0)
                    if sim >= RAG_SIMILARITY_THRESHOLD_STANDARDS or include_low_quality:
                        # Avoid duplicates
                        if not any(
                            r.id == result.get('id')
                            for r in results
                            if r.id
                        ):
                            results.append(
                                SearchResult(
                                    similarity=sim,
                                    content=result.get('code', ''),
                                    metadata=result.get('metadata', {}),
                                    collection="standards",
                                    id=result.get('id')
                                )
                            )
            
            # Re-rank by similarity (descending)
            results.sort(key=lambda r: r.similarity, reverse=True)
            
            # Return top_k results
            final_results = results[:top_k]
            
            logger.info(
                f"Multi-collection search completed",
                query_length=len(query),
                total_results=len(final_results),
                curated_count=sum(1 for r in final_results if r.collection == "curated"),
                project_count=sum(1 for r in final_results if r.collection == "project_code"),
                standards_count=sum(1 for r in final_results if r.collection == "standards"),
            )
            
            return final_results
        
        except Exception as e:
            logger.error(f"Multi-collection search failed: {str(e)}")
            return []
    
    def search_single_collection(
        self,
        query: str,
        collection: str = "curated",
        top_k: int = 5
    ) -> List[SearchResult]:
        """Search a specific collection."""
        try:
            if collection == "curated":
                vector_store = self.curated
                threshold = RAG_SIMILARITY_THRESHOLD_CURATED
            elif collection == "project_code":
                vector_store = self.project_code
                threshold = RAG_SIMILARITY_THRESHOLD_PROJECT
            elif collection == "standards":
                vector_store = self.standards
                threshold = RAG_SIMILARITY_THRESHOLD_STANDARDS
            else:
                logger.error(f"Unknown collection: {collection}")
                return []
            
            raw_results = vector_store.search(query, top_k=top_k)
            
            results = []
            for result in raw_results:
                sim = result.get('similarity', 0)
                if sim >= threshold:
                    results.append(
                        SearchResult(
                            similarity=sim,
                            content=result.get('code', ''),
                            metadata=result.get('metadata', {}),
                            collection=collection,
                            id=result.get('id')
                        )
                    )
            
            return results
        
        except Exception as e:
            logger.error(f"Single collection search failed: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections."""
        try:
            curated_count = self.curated.collection.count()
            project_count = self.project_code.collection.count()
            standards_count = self.standards.collection.count()
            
            return {
                "curated": {
                    "count": curated_count,
                    "threshold": RAG_SIMILARITY_THRESHOLD_CURATED
                },
                "project_code": {
                    "count": project_count,
                    "threshold": RAG_SIMILARITY_THRESHOLD_PROJECT
                },
                "standards": {
                    "count": standards_count,
                    "threshold": RAG_SIMILARITY_THRESHOLD_STANDARDS
                },
                "total": curated_count + project_count + standards_count
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
