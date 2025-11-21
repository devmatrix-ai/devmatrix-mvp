"""
GraphCodeBERT Singleton - P3 Fix

Singleton pattern para evitar cargar GraphCodeBERT múltiples veces.

PROBLEM (from QA analysis):
- GraphCodeBERT se cargaba múltiples veces (2-3 veces en logs)
- Cada carga: ~10-30 segundos + ~300MB RAM
- No había patrón singleton para compartir instancia

SOLUTION:
- Thread-safe singleton con lazy initialization
- Single instance compartida entre todos los servicios
- Reduce startup time ~50%, memory ~300MB

USAGE:
```python
# En lugar de:
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('microsoft/graphcodebert-base')

# Usar:
from src.models.graphcodebert_singleton import get_graphcodebert
model = get_graphcodebert()
```

Created: 2025-11-21
Reference: P3 fix for DevMatrix QA evaluation
"""

import threading
import warnings
import logging
from typing import Optional
from sentence_transformers import SentenceTransformer


class GraphCodeBERTSingleton:
    """
    Thread-safe singleton for GraphCodeBERT model.

    Ensures only one instance of the model is loaded across
    the entire application, regardless of how many services
    request it.
    """

    _instance: Optional[SentenceTransformer] = None
    _lock = threading.Lock()
    _loaded = False

    @classmethod
    def get_instance(cls) -> SentenceTransformer:
        """
        Get singleton instance of GraphCodeBERT.

        Thread-safe lazy initialization. Only loads model once,
        then returns cached instance on subsequent calls.

        Returns:
            SentenceTransformer instance with GraphCodeBERT model
        """
        # Fast path: if already loaded, return immediately (no lock)
        if cls._loaded:
            return cls._instance

        # Slow path: acquire lock and load if needed
        with cls._lock:
            # Double-check: another thread might have loaded while we waited
            if cls._loaded:
                return cls._instance

            # Load model (only happens once)
            cls._instance = cls._load_model()
            cls._loaded = True

            return cls._instance

    @classmethod
    def _load_model(cls) -> SentenceTransformer:
        """
        Load GraphCodeBERT model with warnings suppressed.

        This is called exactly once during application lifetime.

        Returns:
            SentenceTransformer with GraphCodeBERT
        """
        logger = logging.getLogger(__name__)

        try:
            # Suppress all transformers/sentence-transformers warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                warnings.filterwarnings("ignore", category=UserWarning)
                warnings.filterwarnings("ignore", category=FutureWarning)
                warnings.filterwarnings("ignore", message=".*pooler.*")
                warnings.filterwarnings("ignore", message=".*Some weights.*not initialized.*")
                warnings.filterwarnings("ignore", message=".*You should probably TRAIN.*")
                warnings.filterwarnings("ignore", message=".*No sentence-transformers model found.*")
                warnings.filterwarnings("ignore", message=".*Creating a new one.*")
                warnings.filterwarnings("ignore", message=".*RobertaModel.*")

                # Suppress transformers logger
                transformers_logger = logging.getLogger("transformers")
                transformers_logger.setLevel(logging.CRITICAL)
                transformers_logger.propagate = False

                # Suppress modeling_utils logger
                modeling_logger = logging.getLogger("transformers.modeling_utils")
                modeling_logger.setLevel(logging.CRITICAL)
                modeling_logger.propagate = False

                # Suppress sentence-transformers logger
                st_logger = logging.getLogger("sentence_transformers")
                st_logger.setLevel(logging.CRITICAL)
                st_logger.propagate = False

                logger.info("⏳ Loading GraphCodeBERT model (singleton, first time only)...")

                model = SentenceTransformer('microsoft/graphcodebert-base')

                logger.info("✅ GraphCodeBERT singleton loaded (768-dim embeddings)")

                return model

        except Exception as e:
            logger.error(f"Failed to load GraphCodeBERT singleton: {e}")
            raise

    @classmethod
    def reset(cls):
        """
        Reset singleton (for testing only).

        This allows tests to reload the model with different
        configurations. Should NOT be used in production.
        """
        with cls._lock:
            cls._instance = None
            cls._loaded = False


# Convenience function for cleaner imports
def get_graphcodebert() -> SentenceTransformer:
    """
    Get GraphCodeBERT singleton instance.

    This is the main entry point for all code that needs
    GraphCodeBERT embeddings.

    Returns:
        SentenceTransformer with GraphCodeBERT model

    Example:
        ```python
        from src.models.graphcodebert_singleton import get_graphcodebert

        model = get_graphcodebert()
        embedding = model.encode("def factorial(n): return 1 if n == 0 else n * factorial(n-1)")
        ```
    """
    return GraphCodeBERTSingleton.get_instance()
