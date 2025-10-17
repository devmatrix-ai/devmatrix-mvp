"""
Embedding model for RAG system.

This module provides semantic embeddings for code and text using sentence-transformers.
Embeddings are used to convert code snippets into vector representations for similarity search.
"""

from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

from src.observability import get_logger


class EmbeddingModel:
    """
    Wrapper for sentence-transformers embedding model.

    Provides semantic embeddings for code and text, optimized for similarity search
    in the RAG system.

    Attributes:
        model_name: Name of the sentence-transformers model
        model: Loaded SentenceTransformer instance
        dimension: Embedding vector dimension
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model.

        Args:
            model_name: Name of the sentence-transformers model to use.
                       Default: all-MiniLM-L6-v2 (384 dimensions, balanced performance)
                       Alternative: all-mpnet-base-v2 (768 dimensions, higher quality)
        """
        self.logger = get_logger("rag.embeddings")
        self.model_name = model_name

        try:
            self.logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.logger.info(
                f"Embedding model loaded successfully",
                model=model_name,
                dimension=self.dimension
            )
        except Exception as e:
            self.logger.error(
                f"Failed to load embedding model",
                model=model_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            self.logger.debug(
                "Generating embedding for single text",
                text_length=len(text)
            )

            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )

            # Convert to list for ChromaDB compatibility
            embedding_list = embedding.tolist()

            self.logger.debug(
                "Embedding generated successfully",
                embedding_dimension=len(embedding_list)
            )

            return embedding_list

        except Exception as e:
            self.logger.error(
                "Failed to generate embedding",
                error=str(e),
                error_type=type(e).__name__,
                text_length=len(text)
            )
            raise

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once (default: 32)
            show_progress: Whether to show progress bar (default: False)

        Returns:
            List of embedding vectors, one per input text

        Raises:
            ValueError: If texts list is empty
            Exception: If embedding generation fails
        """
        if not texts:
            raise ValueError("Cannot embed empty list of texts")

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            self.logger.info(
                "Generating embeddings for batch",
                batch_size=len(valid_texts),
                processing_batch_size=batch_size
            )

            # Generate embeddings
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )

            # Convert to list of lists for ChromaDB compatibility
            embeddings_list = embeddings.tolist()

            self.logger.info(
                "Batch embeddings generated successfully",
                count=len(embeddings_list),
                embedding_dimension=len(embeddings_list[0]) if embeddings_list else 0
            )

            return embeddings_list

        except Exception as e:
            self.logger.error(
                "Failed to generate batch embeddings",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(valid_texts)
            )
            raise

    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Integer representing the embedding dimension
        """
        return self.dimension

    def compute_similarity(
        self,
        embedding1: Union[List[float], np.ndarray],
        embedding2: Union[List[float], np.ndarray]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between 0 and 1 (higher = more similar)

        Raises:
            ValueError: If embeddings have different dimensions
        """
        # Convert to numpy arrays if needed
        emb1 = np.array(embedding1) if isinstance(embedding1, list) else embedding1
        emb2 = np.array(embedding2) if isinstance(embedding2, list) else embedding2

        if len(emb1) != len(emb2):
            raise ValueError(
                f"Embedding dimensions don't match: {len(emb1)} vs {len(emb2)}"
            )

        # Compute cosine similarity
        # similarity = (A · B) / (||A|| * ||B||)
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Ensure result is in [0, 1] range
        return float(max(0.0, min(1.0, similarity)))


def create_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingModel:
    """
    Factory function to create an embedding model instance.

    Args:
        model_name: Name of the sentence-transformers model

    Returns:
        Initialized EmbeddingModel instance
    """
    return EmbeddingModel(model_name=model_name)
