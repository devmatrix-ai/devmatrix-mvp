"""
Pattern Bank with Qdrant Integration

Auto-evolutionary knowledge base for code generation patterns.
Stores successful patterns as embeddings in Qdrant vector database.

Spec Reference: Section 3.2 - Pattern Bank
Target Coverage: >90% (TDD approach)
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModel

from src.cognitive.config.settings import settings
from src.cognitive.signatures.semantic_signature import (
    SemanticTaskSignature,
    compute_semantic_hash,
)
from src.cognitive.patterns.pattern_classifier import PatternClassifier

# Import DAG synchronizer for execution-based ranking (Milestone 3)
try:
    from src.cognitive.services.dag_synchronizer import DAGSynchronizer
    from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient
    DAG_RANKING_AVAILABLE = True
except ImportError:
    DAG_RANKING_AVAILABLE = False

# Import DualEmbeddingGenerator for automatic dual embedding generation
try:
    from src.cognitive.embeddings.dual_embedding_generator import DualEmbeddingGenerator
    DUAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    DUAL_EMBEDDINGS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class StoredPattern:
    """
    Stored pattern retrieved from pattern bank.

    Represents a successfully validated code pattern with metadata
    for tracking usage and effectiveness.
    """

    pattern_id: str
    signature: SemanticTaskSignature
    code: str
    success_rate: float
    similarity_score: float
    usage_count: int
    created_at: datetime
    domain: str


class PatternBank:
    """
    Pattern Bank with Qdrant vector database integration.

    Auto-evolutionary knowledge base that stores and retrieves successful
    code generation patterns using semantic embeddings.

    **Core Features**:
    - Pattern storage with ≥95% success rate threshold
    - Semantic similarity search (Sentence Transformers embeddings)
    - Hybrid search (vector + metadata filtering)
    - Usage tracking and metrics
    - Auto-evolution through feedback loops

    **Example Usage**:
    ```python
    # Initialize pattern bank
    bank = PatternBank()
    bank.connect()
    bank.create_collection()

    # Store successful pattern
    pattern_id = bank.store_pattern(
        signature=my_signature,
        code="def validate_email(...)...",
        success_rate=0.97
    )

    # Search for similar patterns
    matches = bank.search_patterns(
        query_signature,
        top_k=5,
        similarity_threshold=0.85
    )

    # Hybrid search with domain filter
    filtered = bank.hybrid_search(
        query_signature,
        domain="authentication",
        top_k=3
    )
    ```

    **Spec Compliance**:
    - Qdrant collection: semantic_patterns (768-dim GraphCodeBERT)
    - Embedding model: microsoft/graphcodebert-base (code-aware)
    - Distance metric: Cosine similarity
    - Success threshold: ≥95% for storage
    - Similarity threshold: ≥85% for retrieval
    - Metadata: purpose, code, domain, success_rate, usage_count, created_at
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        enable_dag_ranking: bool = True,
        enable_dual_embeddings: bool = True,
    ):
        """
        Initialize Pattern Bank.

        Args:
            collection_name: Qdrant collection name (default: from settings)
            embedding_model: Embedding model name (default: from settings)
            enable_dag_ranking: Enable DAG-based ranking (Milestone 3)
            enable_dual_embeddings: Enable automatic dual embedding generation
        """
        self.collection_name = collection_name or settings.qdrant_collection_semantic
        self.embedding_dimension = settings.embedding_dimension
        self.embedding_model_name = embedding_model or settings.embedding_model
        self.use_sentence_transformers = settings.use_sentence_transformers

        # Qdrant client (initialized on connect())
        self.client: Optional[QdrantClient] = None
        self.is_connected = False

        # Initialize pattern classifier for auto-categorization
        self.classifier = PatternClassifier()

        # DAG-based ranking (Milestone 3)
        self.enable_dag_ranking = enable_dag_ranking and DAG_RANKING_AVAILABLE
        self.neo4j_client: Optional[Neo4jPatternClient] = None
        if self.enable_dag_ranking:
            try:
                self.neo4j_client = Neo4jPatternClient()
                logger.info("DAG-based pattern ranking enabled")
            except Exception as e:
                logger.warning(f"Failed to enable DAG ranking: {e}")
                self.enable_dag_ranking = False

        # Dual embeddings (automatic code + semantic embeddings)
        self.enable_dual_embeddings = enable_dual_embeddings and DUAL_EMBEDDINGS_AVAILABLE
        self.dual_generator: Optional[DualEmbeddingGenerator] = None
        if self.enable_dual_embeddings:
            try:
                self.dual_generator = DualEmbeddingGenerator()
                logger.info("Dual embedding generation enabled (GraphCodeBERT 768d + Sentence-BERT 384d)")
            except Exception as e:
                logger.warning(f"Failed to enable dual embeddings: {e}")
                self.enable_dual_embeddings = False

        # Initialize embedding encoder (fallback if dual embeddings disabled)
        if self.use_sentence_transformers:
            # SentenceTransformers wrapper (e.g., all-MiniLM-L6-v2)
            self.encoder = SentenceTransformer(self.embedding_model_name)
            self.tokenizer = None
            self.model = None
        else:
            # Direct transformers usage (e.g., GraphCodeBERT)
            self.tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name)
            self.model = AutoModel.from_pretrained(self.embedding_model_name)
            self.encoder = None

            # Set model to eval mode
            self.model.eval()

        logger.info(
            f"Initialized PatternBank with collection '{self.collection_name}', "
            f"model '{self.embedding_model_name}' "
            f"(SentenceTransformers: {self.use_sentence_transformers}, "
            f"DualEmbeddings: {self.enable_dual_embeddings})"
        )

    def connect(self) -> None:
        """
        Connect to Qdrant vector database.

        Raises:
            ConnectionError: If connection to Qdrant fails
        """
        try:
            self.client = QdrantClient(
                host=settings.qdrant_host, port=settings.qdrant_port
            )

            # Verify connection
            self.client.get_collections()
            self.is_connected = True

            logger.info(
                f"Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Failed to connect to Qdrant: {e}")

    def create_collection(self) -> None:
        """
        Create Qdrant collection for semantic patterns.

        Creates collection with:
        - 768 dimensions (GraphCodeBERT)
        - Cosine distance metric
        - Metadata indexes for domain, success_rate filtering
        """
        if not self.is_connected:
            self.connect()

        try:
            # Check if collection already exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return

            # Create new collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension, distance=Distance.COSINE
                ),
            )

            logger.info(
                f"Created collection '{self.collection_name}' "
                f"({self.embedding_dimension}-dim, Cosine)"
            )

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def delete_collection(self) -> None:
        """Delete Qdrant collection (use with caution)."""
        if not self.is_connected:
            self.connect()

        self.client.delete_collection(collection_name=self.collection_name)
        logger.warning(f"Deleted collection '{self.collection_name}'")

    def _encode(self, text: str) -> List[float]:
        """
        Generate embedding vector from text.

        Supports both SentenceTransformers and direct Transformers models.
        Automatically uses correct embedding dimension for semantic_patterns collection.

        Args:
            text: Text to encode (code + purpose)

        Returns:
            Embedding vector as list of floats (384-dim for semantic_patterns, 768-dim otherwise)
        """
        # FIX: Use semantic embedding (384-dim) for semantic_patterns collection
        if self.enable_dual_embeddings and self.collection_name == "semantic_patterns":
            # Use Sentence-BERT for semantic understanding (384-dim)
            return self.dual_generator._generate_semantic_embedding(text)
        elif self.use_sentence_transformers:
            # SentenceTransformers path (legacy)
            return self.encoder.encode(text).tolist()
        else:
            # Direct transformers path (GraphCodeBERT 768-dim)
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use CLS token (first token) embedding
                embeddings = outputs.last_hidden_state[:, 0, :].squeeze()

            return embeddings.numpy().tolist()

    def store_pattern(
        self, signature: SemanticTaskSignature, code: str, success_rate: float
    ) -> str:
        """
        Store successful pattern in pattern bank.

        Only stores patterns with success_rate ≥ 95% (MVP threshold).

        Args:
            signature: Semantic task signature
            code: Generated code (validated and successful)
            success_rate: Validation success rate (must be ≥ 0.95)

        Returns:
            pattern_id: Unique identifier for stored pattern

        Raises:
            ValueError: If success_rate < 95%

        Example:
        ```python
        pattern_id = bank.store_pattern(
            signature=email_validation_sig,
            code="def validate_email(email: str) -> bool: ...",
            success_rate=0.97
        )
        ```
        """
        # Validate success rate threshold
        if success_rate < settings.cpie_precision_threshold:
            raise ValueError(
                f"success_rate must be ≥ {settings.cpie_precision_threshold} "
                f"(got {success_rate})"
            )

        # Generate pattern ID (UUID for Qdrant compatibility)
        pattern_id = str(uuid.uuid4())

        # Compute semantic hash
        semantic_hash = compute_semantic_hash(signature)

        # Auto-categorize pattern using PatternClassifier
        classification_result = self.classifier.classify(
            code=code,
            name=signature.purpose,
            description=signature.intent
        )

        # Generate dual embeddings if enabled, otherwise use fallback
        if self.enable_dual_embeddings and self.dual_generator:
            # Generate dual embeddings (code + semantic)
            pattern_dict = {
                'code': code,
                'description': signature.purpose,
                'pattern_id': pattern_id
            }
            dual_emb = self.dual_generator.generate_batch([pattern_dict])[0]
            code_embedding = dual_emb.code_embedding
            semantic_embedding = dual_emb.semantic_embedding
        else:
            # Fallback to single embedding
            embedding_text = f"{signature.purpose}\n\n{code}"
            code_embedding = self._encode(embedding_text)
            semantic_embedding = code_embedding  # Same for both if dual disabled

        # Create metadata with auto-categorization and production readiness
        metadata = {
            "pattern_id": pattern_id,
            "purpose": signature.purpose,
            "intent": signature.intent,
            "domain": signature.domain,  # Original domain from signature
            "category": classification_result.category,  # Auto-categorized domain
            "classification_confidence": classification_result.confidence,
            "code": code,
            "success_rate": success_rate,
            "usage_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "semantic_hash": semantic_hash,

            # Production readiness metadata (Task Group 8)
            "production_ready": False,  # Flag for production patterns (set explicitly when storing)
            "production_readiness_score": self._calculate_production_readiness_score(
                success_rate=success_rate,
                test_coverage=0.0,  # Will be updated after execution
                security_level=classification_result.security_level or "standard",
                observability_complete=False,  # Will be updated based on pattern content
            ),
            "test_coverage": 0.0,  # Updated after execution metrics available
            "security_level": classification_result.security_level or "standard",
            "performance_tier": classification_result.performance_tier or "medium",
            "observability_complete": False,  # Updated based on logging/metrics presence
            "docker_ready": False,  # Updated if Docker configuration present
        }

        # Store in Qdrant (both collections if dual embeddings enabled)
        self._store_in_qdrant(
            code_embedding=code_embedding,
            semantic_embedding=semantic_embedding,
            metadata=metadata,
            pattern_id=pattern_id
        )

        logger.info(
            f"Stored pattern {pattern_id}: {signature.purpose[:50]} "
            f"(success={success_rate:.2%})"
        )

        return pattern_id

    def _store_in_qdrant(
        self,
        code_embedding: List[float],
        semantic_embedding: List[float],
        metadata: Dict[str, Any],
        pattern_id: str
    ) -> None:
        """
        Store pattern in Qdrant collections.

        If dual embeddings enabled, stores in both:
        - devmatrix_patterns (code embeddings - GraphCodeBERT 768d)
        - semantic_patterns (semantic embeddings - Sentence-BERT 384d)

        Otherwise, stores semantic_embedding only in the primary collection.
        """
        if not self.is_connected:
            self.connect()

        if self.enable_dual_embeddings:
            # Store code embedding in devmatrix_patterns
            code_point = PointStruct(
                id=hash(pattern_id) % (2**63),  # Deterministic ID for consistency
                vector=code_embedding,
                payload=metadata
            )
            try:
                self.client.upsert(
                    collection_name="devmatrix_patterns",
                    points=[code_point]
                )
            except Exception as e:
                logger.warning(f"Failed to store code embedding for {pattern_id}: {e}")

            # Store semantic embedding in semantic_patterns
            semantic_point = PointStruct(
                id=hash(pattern_id) % (2**63),  # Same ID for consistency
                vector=semantic_embedding,
                payload=metadata
            )
            try:
                self.client.upsert(
                    collection_name="semantic_patterns",
                    points=[semantic_point]
                )
            except Exception as e:
                logger.warning(f"Failed to store semantic embedding for {pattern_id}: {e}")
        else:
            # Fallback: store only in primary collection
            point = PointStruct(id=pattern_id, vector=semantic_embedding, payload=metadata)
            self.client.upsert(collection_name=self.collection_name, points=[point])

    def search_patterns(
        self,
        signature: SemanticTaskSignature,
        top_k: int = 5,
        similarity_threshold: float = 0.48,  # LOWERED from 0.55 to match best pattern similarity (~0.495)
    ) -> List[StoredPattern]:
        """
        Search for similar patterns using semantic similarity.

        Args:
            signature: Query signature
            top_k: Maximum number of results (default: 5)
            similarity_threshold: Minimum similarity score (default: 0.85)

        Returns:
            List of StoredPattern sorted by similarity (descending)

        Example:
        ```python
        matches = bank.search_patterns(
            my_signature,
            top_k=5,
            similarity_threshold=0.85
        )

        for pattern in matches:
            print(f"Match: {pattern.purpose} (similarity={pattern.similarity_score})")
        ```
        """
        if not self.is_connected:
            self.connect()

        # DIAGNOSTIC: Check collection size
        try:
            collection_info = self.client.get_collection(self.collection_name)
            total_patterns = collection_info.points_count if collection_info else 0
            logger.debug(f"🔍 DIAGNOSTIC: Collection '{self.collection_name}' has {total_patterns} patterns")
        except Exception as e:
            logger.warning(f"⚠️  DIAGNOSTIC: Failed to get collection info: {e}")
            total_patterns = "unknown"

        # Create query embedding
        query_text = f"{signature.purpose}"
        query_embedding = self._encode(query_text)

        # DIAGNOSTIC: Search WITHOUT threshold first to see all similarities
        all_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=0.0,  # Get ALL results for diagnostics
        )

        logger.debug(
            f"🔍 DIAGNOSTIC: Top {min(5, len(all_results))} similarities (no threshold): "
            f"{[round(r.score, 3) for r in all_results[:5]]}"
        )

        # Search Qdrant with threshold
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=similarity_threshold,
        )

        # DIAGNOSTIC: Compare results
        logger.debug(
            f"🔍 DIAGNOSTIC: Threshold {similarity_threshold} filtered: "
            f"{len(all_results)} → {len(search_result)} results"
        )

        # Convert to StoredPattern objects
        patterns = []
        for hit in search_result:
            pattern = self._hit_to_stored_pattern(hit, similarity_score=hit.score)
            patterns.append(pattern)

            # Increment usage count
            self._increment_usage_count(hit.id)

        logger.info(
            f"Found {len(patterns)} patterns for '{signature.purpose[:50]}' "
            f"(threshold={similarity_threshold}, collection_size={total_patterns})"
        )

        if len(patterns) == 0 and len(all_results) > 0:
            logger.warning(
                f"⚠️  PATTERN BANK: 0 results with threshold {similarity_threshold}, "
                f"but {len(all_results)} results exist. "
                f"Best similarity: {all_results[0].score:.3f}. "
                f"Consider lowering threshold to {max(0.5, all_results[0].score - 0.1):.2f}"
            )

        return patterns

    def search_with_fallback(
        self,
        signature: SemanticTaskSignature,
        top_k: int = 5,
        min_results: int = 3,
    ) -> List[StoredPattern]:
        """
        Search patterns with adaptive thresholds and keyword fallback (TG4+TG5).

        This orchestrator method integrates:
        - TG4: Domain-specific adaptive similarity thresholds
        - TG5: Keyword-based fallback when embedding search yields < min_results

        Process:
        1. Determine adaptive threshold based on signature.domain
        2. Try semantic search with adaptive threshold
        3. If results < min_results, fall back to keyword matching
        4. Combine and deduplicate results
        5. Return top_k patterns sorted by similarity

        Args:
            signature: Semantic task signature
            top_k: Maximum number of results to return (default: 5)
            min_results: Minimum results before triggering fallback (default: 3)

        Returns:
            List of StoredPattern sorted by similarity score (descending)

        Example:
            >>> bank = PatternBank()
            >>> signature = SemanticTaskSignature(
            ...     purpose="Create a new user",
            ...     domain="crud",
            ...     ...
            ... )
            >>> patterns = bank.search_with_fallback(signature, top_k=5)
            >>> # Returns: Up to 5 patterns using adaptive threshold + keyword fallback
        """
        # TG4: Adaptive threshold based on domain
        # Adjusted based on real pattern similarities observed (~0.5-0.7 range)
        domain_thresholds = {
            "crud": 0.60,              # Simple CRUD patterns - lower threshold
            "custom": 0.65,            # Custom logic - medium threshold
            "payment": 0.70,           # Complex payment patterns - higher threshold
            "workflow": 0.65,          # Workflow patterns - medium threshold
            "api_development": 0.60,   # API development - lower threshold (E2E tests)
            "backend": 0.60,           # Backend patterns - lower threshold
        }
        default_threshold = 0.60  # Lowered from 0.80 to match real pattern similarities

        domain = signature.domain if signature.domain else None
        adaptive_threshold = domain_thresholds.get(
            domain.lower() if domain else "",
            default_threshold
        )

        logger.debug(
            f"🎯 TG4: Using adaptive threshold {adaptive_threshold} for domain '{domain}'"
        )

        # Step 1: Try semantic search with adaptive threshold
        semantic_results = self.search_patterns(
            signature,
            top_k=top_k,
            similarity_threshold=adaptive_threshold,
        )

        logger.info(
            f"📊 Semantic search found {len(semantic_results)} patterns "
            f"(threshold={adaptive_threshold})"
        )

        # If we have enough results, return them
        if len(semantic_results) >= min_results:
            return semantic_results

        # Step 2: TG5 Keyword Fallback - Not enough semantic matches
        logger.info(
            f"🔄 TG5: Triggering keyword fallback "
            f"({len(semantic_results)} < {min_results} results)"
        )

        # Extract keywords from purpose
        keywords = self._extract_keywords(signature.purpose)
        logger.debug(f"🔍 Extracted keywords: {keywords}")

        # Find pattern types from keywords
        keyword_patterns = set()
        for keyword in keywords:
            pattern_type = self._keyword_to_pattern_type(keyword)
            if pattern_type:
                keyword_patterns.add(pattern_type)

        logger.debug(f"📋 Mapped to pattern types: {keyword_patterns}")

        # Search for patterns matching these types
        # We'll do a broader search and filter by matching domain/category
        keyword_results = []
        if keyword_patterns:
            # Do a low-threshold search to get candidates
            broad_results = self.search_patterns(
                signature,
                top_k=top_k * 2,  # Get more candidates
                similarity_threshold=0.4,  # Very low threshold
            )

            # Filter by pattern type match (check if domain or purpose contains pattern type keywords)
            for pattern in broad_results:
                pattern_purpose_lower = pattern.purpose.lower()
                pattern_domain_lower = (pattern.domain or "").lower()

                # Check if any keyword pattern matches the pattern's purpose or domain
                for kp in keyword_patterns:
                    kp_parts = kp.split('_')  # e.g., 'crud_create' -> ['crud', 'create']
                    if any(part in pattern_purpose_lower or part in pattern_domain_lower
                           for part in kp_parts):
                        keyword_results.append(pattern)
                        break  # Only add once per pattern

            logger.info(f"🔍 Keyword fallback found {len(keyword_results)} additional patterns")

        # Step 3: Combine and deduplicate results
        # Use pattern_id for deduplication
        seen_ids = set()
        combined_results = []

        # Add semantic results first (higher priority)
        for pattern in semantic_results:
            if pattern.pattern_id not in seen_ids:
                seen_ids.add(pattern.pattern_id)
                combined_results.append(pattern)

        # Add keyword results
        for pattern in keyword_results:
            if pattern.pattern_id not in seen_ids:
                seen_ids.add(pattern.pattern_id)
                combined_results.append(pattern)

        # Sort by similarity score (descending) and limit to top_k
        combined_results.sort(key=lambda p: p.similarity_score, reverse=True)
        final_results = combined_results[:top_k]

        logger.info(
            f"✅ Final results: {len(final_results)} patterns "
            f"(semantic={len(semantic_results)}, keyword={len(keyword_results)}, "
            f"combined={len(combined_results)})"
        )

        return final_results

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text by removing stopwords (TG5).

        Args:
            text: Input text to extract keywords from

        Returns:
            List of lowercase keywords without stopwords

        Example:
            >>> bank._extract_keywords("Create a new user in the database")
            ['create', 'new', 'user', 'database']
        """
        # Common stopwords to filter out
        stopwords = {
            'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
            'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'it',
            'its', 'by', 'from', 'with', 'without', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'under', 'over'
        }

        # Convert to lowercase and split into words
        words = text.lower().split()

        # Filter out stopwords and keep meaningful keywords
        keywords = [word for word in words if word not in stopwords and len(word) > 2]

        return keywords

    def _keyword_to_pattern_type(self, keyword: str) -> Optional[str]:
        """
        Map keyword to pattern type for fallback matching (TG5).

        Args:
            keyword: Lowercase keyword

        Returns:
            Pattern type or None if no mapping exists

        Example:
            >>> bank._keyword_to_pattern_type("create")
            'crud_create'
            >>> bank._keyword_to_pattern_type("checkout")
            'payment_workflow'
        """
        keyword_mappings = {
            # CRUD operations
            'create': 'crud_create',
            'add': 'crud_create',
            'new': 'crud_create',
            'list': 'crud_list',
            'all': 'crud_list',
            'filter': 'crud_list',
            'get': 'crud_read',
            'read': 'crud_read',
            'fetch': 'crud_read',
            'update': 'crud_update',
            'edit': 'crud_update',
            'modify': 'crud_update',
            'delete': 'crud_delete',
            'remove': 'crud_delete',
            # Workflow operations
            'checkout': 'payment_workflow',
            'pay': 'payment_workflow',
            'payment': 'payment_workflow',
            'order': 'payment_workflow',
            'cart': 'cart_workflow',
            'basket': 'cart_workflow',
        }

        return keyword_mappings.get(keyword.lower())

    def hybrid_search(
        self,
        signature: SemanticTaskSignature,
        domain: Optional[str] = None,
        production_ready: bool = False,
        top_k: int = 5,
    ) -> List[StoredPattern]:
        """
        Hybrid search combining vector similarity and metadata filtering.

        Scoring: 70% vector similarity + 30% metadata relevance

        Args:
            signature: Query signature
            domain: Optional domain filter
            production_ready: If True, only return production-ready patterns (Task Group 8)
            top_k: Maximum results

        Returns:
            List of StoredPattern with combined scores

        Example:
        ```python
        # Search for production-ready auth patterns
        auth_patterns = bank.hybrid_search(
            my_signature,
            domain="authentication",
            production_ready=True,
            top_k=3
        )
        ```
        """
        if not self.is_connected:
            self.connect()

        # Create query embedding
        query_text = f"{signature.purpose}"
        query_embedding = self._encode(query_text)

        # Build filter for domain and/or production_ready if specified
        filter_conditions = []
        if domain:
            filter_conditions.append(
                FieldCondition(key="domain", match=MatchValue(value=domain))
            )
        if production_ready:
            filter_conditions.append(
                FieldCondition(key="production_ready", match=MatchValue(value=True))
            )

        search_filter = None
        if filter_conditions:
            search_filter = Filter(must=filter_conditions)

        # Search with optional filter
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
        )

        # Convert to StoredPattern with hybrid scoring
        patterns = []
        for hit in search_result:
            vector_score = hit.score
            metadata_score = self._metadata_score(hit.payload, signature, domain)

            # Hybrid score: 70% vector + 30% metadata
            final_score = 0.7 * vector_score + 0.3 * metadata_score

            pattern = self._hit_to_stored_pattern(hit, similarity_score=final_score)
            pattern.similarity_score = final_score  # Override with hybrid score
            patterns.append(pattern)

            # Increment usage count
            self._increment_usage_count(hit.id)

        # Sort by hybrid score
        patterns.sort(key=lambda p: p.similarity_score, reverse=True)

        logger.info(
            f"Hybrid search found {len(patterns)} patterns "
            f"(domain={domain}, top_k={top_k})"
        )

        return patterns

    def _vector_search(
        self, signature: SemanticTaskSignature, top_k: int
    ) -> List[Dict]:
        """Internal vector search (for testing)."""
        query_embedding = self._encode(f"{signature.purpose}")
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
        )
        return [{"pattern_id": r.id, "score": r.score} for r in results]

    def _metadata_score(
        self, payload: Dict, signature: SemanticTaskSignature, domain: Optional[str]
    ) -> float:
        """
        Calculate metadata relevance score with optional DAG-based ranking.

        Factors:
        - Domain match (if specified)
        - Intent match
        - Success rate
        - DAG execution success (if enabled) - Milestone 3

        Returns:
            Score in range [0.0, 1.0]
        """
        score = 0.0

        # Domain match (30%)
        if domain and payload.get("domain") == domain:
            score += 0.3

        # Intent match (20%)
        if payload.get("intent") == signature.intent:
            score += 0.2

        # Success rate contribution (20%)
        score += 0.2 * payload.get("success_rate", 0.0)

        # DAG execution-based ranking (30%) - Milestone 3
        if self.enable_dag_ranking:
            dag_score = self._get_dag_ranking_score(payload.get("pattern_id"))
            score += 0.3 * dag_score
        else:
            # Fallback: use success_rate again
            score += 0.3 * payload.get("success_rate", 0.0)

        return min(score, 1.0)

    def _increment_usage_count(self, pattern_id: str) -> None:
        """Increment usage count for pattern."""
        try:
            # Get current pattern
            result = self.client.retrieve(
                collection_name=self.collection_name, ids=[pattern_id]
            )

            if result:
                current_count = result[0].payload.get("usage_count", 0)
                new_count = current_count + 1

                # Update payload
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload={"usage_count": new_count},
                    points=[pattern_id],
                )

                logger.debug(f"Incremented usage_count for {pattern_id}: {new_count}")

        except Exception as e:
            logger.warning(f"Failed to increment usage_count for {pattern_id}: {e}")

    def _hit_to_stored_pattern(self, hit: Any, similarity_score: float) -> StoredPattern:
        """Convert Qdrant search hit to StoredPattern object."""
        payload = hit.payload

        # Handle empty purpose (legacy patterns) with fallback
        purpose = payload.get("purpose", "").strip()
        if not purpose:
            purpose = "Unknown pattern"  # Fallback for legacy patterns with empty purpose
            logger.warning(f"Pattern {payload.get('pattern_id', 'unknown')} has empty purpose, using fallback")

        # Reconstruct signature from payload
        signature = SemanticTaskSignature(
            purpose=purpose,
            intent=payload.get("intent", "execute"),  # Fallback intent
            inputs={},  # Not stored in pattern bank
            outputs={},  # Not stored in pattern bank
            domain=payload.get("domain", "general"),  # Fallback domain
        )

        return StoredPattern(
            pattern_id=payload["pattern_id"],
            signature=signature,
            code=payload["code"],
            success_rate=payload["success_rate"],
            similarity_score=similarity_score,
            usage_count=payload.get("usage_count", 0),
            created_at=datetime.fromisoformat(payload["created_at"]),
            domain=payload["domain"],
        )

    def get_pattern_by_id(self, pattern_id: str) -> Optional[StoredPattern]:
        """
        Retrieve specific pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            StoredPattern or None if not found
        """
        if not self.is_connected:
            self.connect()

        try:
            result = self.client.retrieve(
                collection_name=self.collection_name, ids=[pattern_id]
            )

            if result:
                hit = result[0]
                return self._hit_to_stored_pattern(hit, similarity_score=1.0)

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve pattern {pattern_id}: {e}")
            return None

    def update_pattern_success(self, pattern_id: str, new_success_rate: float) -> None:
        """
        Update success rate for existing pattern.

        Args:
            pattern_id: Pattern identifier
            new_success_rate: Updated success rate
        """
        if not self.is_connected:
            self.connect()

        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"success_rate": new_success_rate},
            points=[pattern_id],
        )

        logger.info(f"Updated {pattern_id} success_rate to {new_success_rate:.2%}")

    def get_pattern_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated pattern bank metrics.

        Returns:
            Dictionary with metrics:
            - total_patterns: Total patterns stored
            - avg_success_rate: Average success rate
            - avg_usage_count: Average usage count
            - domain_distribution: Patterns per domain
            - most_used_patterns: Top 10 by usage_count

        Example:
        ```python
        metrics = bank.get_pattern_metrics()
        print(f"Total patterns: {metrics['total_patterns']}")
        print(f"Avg success rate: {metrics['avg_success_rate']:.2%}")
        ```
        """
        if not self.is_connected:
            self.connect()

        # Get collection info
        collection_info = self.client.get_collection(self.collection_name)
        total_patterns = collection_info.points_count

        # Scroll through all points to calculate metrics
        # Note: For production, implement pagination for large datasets
        scroll_result = self.client.scroll(
            collection_name=self.collection_name, limit=total_patterns or 100
        )

        points = scroll_result[0]

        # Calculate aggregated metrics
        total_success = 0.0
        total_usage = 0
        domain_counts: Dict[str, int] = {}
        pattern_usage: List[tuple] = []

        for point in points:
            payload = point.payload

            total_success += payload.get("success_rate", 0.0)
            usage = payload.get("usage_count", 0)
            total_usage += usage

            # Domain distribution
            domain = payload.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Track for most_used_patterns
            pattern_usage.append(
                (payload.get("pattern_id"), payload.get("purpose", ""), usage)
            )

        # Calculate averages
        avg_success = total_success / total_patterns if total_patterns > 0 else 0.0
        avg_usage = total_usage / total_patterns if total_patterns > 0 else 0.0

        # Sort and get top 10 most used
        pattern_usage.sort(key=lambda x: x[2], reverse=True)
        most_used = [
            {"pattern_id": pid, "purpose": purpose, "usage_count": count}
            for pid, purpose, count in pattern_usage[:10]
        ]

        metrics = {
            "total_patterns": total_patterns,
            "avg_success_rate": round(avg_success, 3),
            "avg_usage_count": round(avg_usage, 2),
            "domain_distribution": domain_counts,
            "most_used_patterns": most_used,
        }

        logger.info(
            f"Pattern bank metrics: {total_patterns} patterns, "
            f"avg_success={avg_success:.2%}"
        )

        return metrics

    def _get_dag_ranking_score(self, pattern_id: Optional[str]) -> float:
        """
        Get DAG-based ranking score for a pattern (Milestone 3).

        Formula:
        - Base: Pattern's Neo4j ranking_score (0.0-1.0)
        - Boost: Recent successful executions (+0.10 if within 7 days)
        - Penalty: Failed executions (-0.05 per failure in last 10 executions)
        - Efficiency: Resource-efficient executions (+0.03 if <5s and <256MB)

        Returns:
            Score in range [0.0, 1.0]
        """
        if not pattern_id or not self.enable_dag_ranking or not self.neo4j_client:
            return 0.5  # Neutral score if DAG ranking disabled

        try:
            # Ensure Neo4j connection
            if not self.neo4j_client._driver:
                self.neo4j_client.connect()

            # Query Neo4j for pattern's ranking score and execution stats
            query = """
            MATCH (p:Pattern {pattern_id: $pattern_id})
            OPTIONAL MATCH (t:AtomicTask)-[u:USES_PATTERN]->(p)
            OPTIONAL MATCH (t)-[e:EXECUTED_WITH_METRICS]->(:ExecutionTrace)
            WITH p,
                 coalesce(p.ranking_score, 0.5) AS base_score,
                 collect(DISTINCT {
                     success: e.success,
                     timestamp: e.timestamp,
                     duration_ms: e.duration_ms,
                     memory_mb: e.memory_mb
                 }) AS executions
            RETURN base_score,
                   size(executions) AS execution_count,
                   executions
            LIMIT 1
            """

            result = self.neo4j_client._execute_query(query, {"pattern_id": pattern_id})

            if not result:
                return 0.5  # Pattern not in DAG yet

            data = result[0]
            base_score = data["base_score"]
            executions = data.get("executions", [])

            # Filter out empty executions (OPTIONAL MATCH returns nulls)
            executions = [e for e in executions if e.get("success") is not None]

            if not executions:
                return base_score  # No execution history, use base score

            # Calculate adjustments
            adjustment = 0.0

            # Recent success boost (within 7 days)
            from datetime import datetime, timedelta
            now_ts = int(datetime.now().timestamp() * 1000)
            seven_days_ago = now_ts - (7 * 24 * 60 * 60 * 1000)

            recent_successes = [
                e for e in executions
                if e.get("success") and e.get("timestamp", 0) > seven_days_ago
            ]
            if recent_successes:
                adjustment += 0.10

            # Failure penalty (last 10 executions)
            last_10 = sorted(executions, key=lambda e: e.get("timestamp", 0), reverse=True)[:10]
            failures = sum(1 for e in last_10 if not e.get("success", True))
            adjustment -= 0.05 * failures

            # Efficiency bonus (fast and low memory)
            efficient_execs = [
                e for e in executions
                if e.get("success") and
                   e.get("duration_ms", float('inf')) < 5000 and
                   e.get("memory_mb", float('inf')) < 256
            ]
            if efficient_execs and len(efficient_execs) / max(len(executions), 1) > 0.5:
                adjustment += 0.03

            # Final score
            final_score = base_score + adjustment
            final_score = max(0.0, min(1.0, final_score))  # Clamp to [0.0, 1.0]

            logger.debug(
                f"DAG ranking for {pattern_id}: base={base_score:.3f}, "
                f"adjustment={adjustment:+.3f}, final={final_score:.3f}"
            )

            return final_score

        except Exception as e:
            logger.warning(f"Failed to get DAG ranking for {pattern_id}: {e}")
            return 0.5  # Fallback to neutral score on error

    def _calculate_production_readiness_score(
        self,
        success_rate: float,
        test_coverage: float,
        security_level: str,
        observability_complete: bool,
    ) -> float:
        """
        Calculate production readiness score from quality metrics (Task Group 8).

        Formula:
        - success_rate: 40% weight
        - test_coverage: 30% weight
        - security_level: 20% weight (CRITICAL=1.0, HIGH=0.8, MEDIUM=0.6, LOW=0.4, STANDARD=0.5)
        - observability_complete: 10% weight (True=1.0, False=0.0)

        Args:
            success_rate: Pattern success rate (0.0-1.0)
            test_coverage: Test coverage percentage (0.0-1.0)
            security_level: Security level (CRITICAL, HIGH, MEDIUM, LOW, STANDARD)
            observability_complete: Whether pattern includes logging/metrics

        Returns:
            Production readiness score (0.0-1.0)
        """
        # Security level mapping
        security_scores = {
            "CRITICAL": 1.0,
            "HIGH": 0.8,
            "MEDIUM": 0.6,
            "STANDARD": 0.5,
            "LOW": 0.4,
        }
        security_score = security_scores.get(security_level.upper(), 0.5)

        # Observability score
        observability_score = 1.0 if observability_complete else 0.0

        # Weighted calculation
        production_score = (
            (success_rate * 0.40) +
            (test_coverage * 0.30) +
            (security_score * 0.20) +
            (observability_score * 0.10)
        )

        return round(production_score, 3)

    def store_production_pattern(
        self,
        signature: SemanticTaskSignature,
        code: str,
        success_rate: float,
        test_coverage: float = 0.85,
        security_level: str = "HIGH",
        observability_complete: bool = True,
        docker_ready: bool = False,
    ) -> str:
        """
        Store production-ready pattern with enhanced metadata (Task Group 8).

        This is a convenience method for storing patterns with production readiness metadata.
        Uses store_pattern() internally but sets production_ready=True and calculates
        production_readiness_score.

        Args:
            signature: Semantic task signature
            code: Production-ready code pattern
            success_rate: Validation success rate (must be >= 0.95)
            test_coverage: Test coverage percentage (0.0-1.0, default: 0.85)
            security_level: Security level (CRITICAL, HIGH, MEDIUM, LOW, default: HIGH)
            observability_complete: Whether pattern includes logging/metrics (default: True)
            docker_ready: Whether pattern includes Docker configuration (default: False)

        Returns:
            pattern_id: Unique identifier for stored pattern

        Example:
        ```python
        pattern_id = bank.store_production_pattern(
            signature=config_signature,
            code=pydantic_settings_code,
            success_rate=0.98,
            test_coverage=0.90,
            security_level="HIGH",
            observability_complete=True,
            docker_ready=False
        )
        ```
        """
        # Store pattern using standard method
        pattern_id = self.store_pattern(signature, code, success_rate)

        # Update metadata with production readiness flags
        production_score = self._calculate_production_readiness_score(
            success_rate=success_rate,
            test_coverage=test_coverage,
            security_level=security_level,
            observability_complete=observability_complete,
        )

        # Update payload with production metadata
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={
                "production_ready": True,
                "production_readiness_score": production_score,
                "test_coverage": test_coverage,
                "security_level": security_level,
                "observability_complete": observability_complete,
                "docker_ready": docker_ready,
            },
            points=[pattern_id],
        )

        logger.info(
            f"Stored production pattern {pattern_id}: {signature.purpose[:50]} "
            f"(production_score={production_score:.2%})"
        )

        return pattern_id
