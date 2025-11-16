"""
Unified RAG Retriever - ChromaDB + Qdrant + Neo4j Integration

Combines three retrieval sources for comprehensive code pattern matching:
- ChromaDB: General semantic code embeddings
- Qdrant: 21,624 curated patterns from pattern library
- Neo4j: 30,314 nodes + 159,793 relationships (knowledge graph)
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from neo4j import GraphDatabase

from src.rag.embeddings import EmbeddingModel, create_embedding_model
from src.rag.vector_store import VectorStore, create_vector_store
from src.cognitive.config.settings import CognitiveSettings
from src.observability import get_logger


logger = get_logger("rag.unified_retriever")


@dataclass
class UnifiedRetrievalResult:
    """Result from unified RAG retrieval."""
    content: str
    source: str  # "chroma" | "qdrant" | "neo4j"
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    rank: int = 0


class UnifiedRAGRetriever:
    """
    Unified RAG retriever combining ChromaDB + Qdrant + Neo4j.

    Retrieval strategy:
    1. Query all three sources in parallel
    2. Merge results with weighted scoring:
       - ChromaDB: 0.3 (general semantic search)
       - Qdrant: 0.5 (curated patterns - highest weight)
       - Neo4j: 0.2 (graph relationships)
    3. Deduplicate by content similarity
    4. Return top_k ranked results
    """

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        chroma_store: Optional[VectorStore] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ):
        """
        Initialize unified RAG retriever.

        Args:
            embedding_model: Embedding model for query vectorization
            chroma_store: ChromaDB vector store (optional)
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.logger = logger
        self.settings = CognitiveSettings()

        # Initialize embedding model (OpenAI for general use)
        self.embeddings = embedding_model or create_embedding_model()

        # Initialize separate embedding model for Qdrant (768-dim)
        # Using GraphCodeBERT (collection rebuilt with this model)
        self.qdrant_embeddings = None
        try:
            from sentence_transformers import SentenceTransformer
            # Use GraphCodeBERT for code-aware embeddings (768-dim)
            self.qdrant_embeddings = SentenceTransformer('microsoft/graphcodebert-base')
            self.logger.info("Loaded GraphCodeBERT model for Qdrant (768-dim, code-aware)")
        except Exception as e:
            self.logger.warning(f"Could not load GraphCodeBERT for Qdrant: {e}")

        # Initialize ChromaDB
        self.chroma_enabled = False
        self.chroma = None
        try:
            self.chroma = chroma_store or create_vector_store(self.embeddings)
            self.chroma_enabled = True
            self.logger.info("ChromaDB initialized successfully")
        except Exception as e:
            self.logger.warning(f"ChromaDB initialization failed: {e}")

        # Initialize Qdrant (21,624 patterns)
        self.qdrant_enabled = False
        self.qdrant = None
        try:
            qhost = qdrant_host or getattr(self.settings, 'qdrant_host', 'localhost')
            qport = qdrant_port or getattr(self.settings, 'qdrant_port', 6333)

            self.qdrant = QdrantClient(host=qhost, port=qport)
            # Verify connection
            collections = self.qdrant.get_collections()
            self.qdrant_enabled = True
            self.logger.info(f"Qdrant initialized successfully at {qhost}:{qport}")
        except Exception as e:
            self.logger.warning(f"Qdrant initialization failed: {e}")

        # Initialize Neo4j (30,314 nodes)
        self.neo4j_enabled = False
        self.neo4j_driver = None
        try:
            n_uri = neo4j_uri or getattr(self.settings, 'neo4j_uri', 'bolt://localhost:7687')
            n_user = neo4j_user or getattr(self.settings, 'neo4j_user', 'neo4j')
            n_pass = neo4j_password or getattr(self.settings, 'neo4j_password', 'devmatrix')

            self.neo4j_driver = GraphDatabase.driver(n_uri, auth=(n_user, n_pass))
            # Verify connection
            with self.neo4j_driver.session() as session:
                session.run("MATCH (n) RETURN count(n) LIMIT 1")
            self.neo4j_enabled = True
            self.logger.info(f"Neo4j initialized successfully at {n_uri}")
        except Exception as e:
            self.logger.warning(f"Neo4j initialization failed: {e}")

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        chroma_weight: float = 0.3,
        qdrant_weight: float = 0.5,
        neo4j_weight: float = 0.2,
        **kwargs
    ) -> List[UnifiedRetrievalResult]:
        """
        Retrieve from all sources and merge results.

        Args:
            query: Search query
            top_k: Number of results to return
            chroma_weight: Weight for ChromaDB scores (default 0.3)
            qdrant_weight: Weight for Qdrant scores (default 0.5)
            neo4j_weight: Weight for Neo4j scores (default 0.2)

        Returns:
            List of unified retrieval results, ranked by weighted score
        """
        # Parallel retrieval from all sources
        tasks = []

        if self.chroma_enabled:
            tasks.append(self._retrieve_from_chroma(query, top_k * 2))

        if self.qdrant_enabled:
            tasks.append(self._retrieve_from_qdrant(query, top_k * 2))

        if self.neo4j_enabled:
            tasks.append(self._retrieve_from_neo4j(query, top_k * 2))

        if not tasks:
            self.logger.warning("No RAG sources enabled")
            return []

        # Execute parallel retrieval
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge and weight results
        all_results = []
        weights = {
            'chroma': chroma_weight,
            'qdrant': qdrant_weight,
            'neo4j': neo4j_weight
        }

        for result, source in zip(results, ['chroma', 'qdrant', 'neo4j'][:len(results)]):
            if isinstance(result, Exception):
                self.logger.error(f"Retrieval from {source} failed: {result}")
                continue

            if not result:
                continue

            # Apply weighted scoring
            weight = weights.get(source, 1.0)
            for item in result:
                item.score *= weight
                item.source = source
                all_results.append(item)

        # Deduplicate by content similarity (simple hash-based for now)
        unique_results = self._deduplicate_results(all_results)

        # Sort by weighted score
        unique_results.sort(key=lambda x: x.score, reverse=True)

        # Assign ranks
        for rank, result in enumerate(unique_results[:top_k], 1):
            result.rank = rank

        self.logger.info(
            f"Retrieved {len(unique_results[:top_k])} results from "
            f"{sum([self.chroma_enabled, self.qdrant_enabled, self.neo4j_enabled])} sources"
        )

        return unique_results[:top_k]

    async def _retrieve_from_chroma(self, query: str, top_k: int) -> List[UnifiedRetrievalResult]:
        """Retrieve from ChromaDB."""
        if not self.chroma or not self.chroma_enabled:
            return []

        try:
            # Use existing retriever interface
            from src.rag.retriever import create_retriever
            retriever = create_retriever(self.chroma, top_k=top_k)
            results = retriever.retrieve(query)

            return [
                UnifiedRetrievalResult(
                    content=r.code,
                    source='chroma',
                    score=r.score,
                    metadata=r.metadata,
                )
                for r in results
            ]
        except Exception as e:
            self.logger.error(f"ChromaDB retrieval failed: {e}")
            return []

    async def _retrieve_from_qdrant(self, query: str, top_k: int) -> List[UnifiedRetrievalResult]:
        """Retrieve from Qdrant pattern library (21,624 patterns)."""
        if not self.qdrant or not self.qdrant_enabled:
            return []

        try:
            # Generate query embedding using GraphCodeBERT (768-dim, code-aware)
            if self.qdrant_embeddings is None:
                self.logger.warning("Qdrant embeddings not available")
                return []

            query_embedding = self.qdrant_embeddings.encode(query).tolist()

            # Search in devmatrix_patterns collection
            search_results = self.qdrant.search(
                collection_name="devmatrix_patterns",
                query_vector=query_embedding,
                limit=top_k
            )

            return [
                UnifiedRetrievalResult(
                    content=hit.payload.get('content', ''),
                    source='qdrant',
                    score=hit.score,
                    metadata=hit.payload,
                )
                for hit in search_results
            ]
        except Exception as e:
            self.logger.error(f"Qdrant retrieval failed: {e}")
            return []

    async def _retrieve_from_neo4j(self, query: str, top_k: int) -> List[UnifiedRetrievalResult]:
        """Retrieve from Neo4j knowledge graph (30,314 nodes)."""
        if not self.neo4j_driver or not self.neo4j_enabled:
            return []

        try:
            # Keyword-based graph search using actual Neo4j schema
            # Schema: Pattern nodes have 'code', 'description', 'name' properties
            with self.neo4j_driver.session() as session:
                result = session.run(
                    """
                    MATCH (n)
                    WHERE n.description CONTAINS $query
                       OR n.code CONTAINS $query
                       OR n.name CONTAINS $query
                    RETURN n.code AS code,
                           n.description AS description,
                           n.name AS name,
                           labels(n) AS labels,
                           id(n) AS node_id
                    LIMIT $limit
                    """,
                    parameters={"query": query, "limit": top_k}
                )

                records = list(result)

                return [
                    UnifiedRetrievalResult(
                        content=record['code'] or record['description'] or record['name'] or '',
                        source='neo4j',
                        score=0.5,  # Fixed score for now, could use graph metrics
                        metadata={
                            'labels': record['labels'],
                            'node_id': record['node_id'],
                            'name': record['name'],
                            'description': record['description'],
                        }
                    )
                    for record in records
                    if record['code'] or record['description'] or record['name']
                ]
        except Exception as e:
            self.logger.error(f"Neo4j retrieval failed: {e}")
            return []

    def _deduplicate_results(self, results: List[UnifiedRetrievalResult]) -> List[UnifiedRetrievalResult]:
        """Deduplicate results by content hash."""
        seen_hashes = set()
        unique = []

        for result in results:
            content_hash = hash(result.content[:500])  # Hash first 500 chars

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(result)

        return unique

    def close(self):
        """Close all connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()


def create_unified_retriever(
    embedding_model: Optional[EmbeddingModel] = None,
    **kwargs
) -> UnifiedRAGRetriever:
    """
    Factory function to create UnifiedRAGRetriever.

    Args:
        embedding_model: Optional embedding model
        **kwargs: Additional configuration

    Returns:
        UnifiedRAGRetriever instance
    """
    return UnifiedRAGRetriever(embedding_model=embedding_model, **kwargs)
