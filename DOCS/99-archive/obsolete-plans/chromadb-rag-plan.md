# Plan de Implementación RAG con ChromaDB - DevMatrix

**Fecha de Creación**: 2025-10-17
**Objetivo**: Mejorar precisión de generación de código de 70-80% → 90%+
**Stack Principal**: ChromaDB + sentence-transformers + FastAPI
**Timeline Estimado**: 2-4 semanas (80-160 horas)
**Modo**: Ultra-detallado (ultrathink)

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Actual vs. Objetivo](#arquitectura-actual-vs-objetivo)
3. [Fases de Implementación](#fases-de-implementación)
4. [Código Completo](#código-completo)
5. [Integración con DevMatrix](#integración-con-devmatrix)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Plan](#deployment-plan)
8. [Monitoring y Métricas](#monitoring-y-métricas)
9. [Timeline Detallado](#timeline-detallado)
10. [Risk Mitigation](#risk-mitigation)
11. [Checklist de Implementación](#checklist-de-implementación)

---

## 🎯 Resumen Ejecutivo

### Problema Actual
- **Precisión actual**: 70-80% en generación de código
- **Causa raíz**: Falta de contexto específico del proyecto y ejemplos relevantes
- **Impacto**: Código inconsistente, patrones no seguidos, necesidad de múltiples iteraciones

### Solución Propuesta
Implementar sistema RAG (Retrieval-Augmented Generation) con ChromaDB que:
1. **Indexa** código aprobado en vectores semánticos
2. **Recupera** ejemplos relevantes basados en similitud
3. **Aumenta** contexto del LLM con ejemplos específicos del proyecto
4. **Mejora** precisión mediante aprendizaje continuo

### Beneficios Esperados
- ✅ **Precisión**: 70-80% → 90%+
- ✅ **Consistencia**: Patrones del proyecto seguidos automáticamente
- ✅ **Velocidad**: Menos iteraciones de corrección
- ✅ **Aprendizaje**: Mejora continua con cada código aprobado
- ✅ **Escalabilidad**: ChromaDB maneja proyectos de cualquier tamaño

### Inversión Requerida
- **Tiempo de desarrollo**: 2-4 semanas
- **Infraestructura**: ChromaDB (self-hosted, gratis)
- **Costo operacional**: Mínimo (local storage)
- **ROI esperado**: 40% reducción en tiempo de desarrollo

---

## 🏗️ Arquitectura Actual vs. Objetivo

### Arquitectura Actual (Sin RAG)

```
┌─────────────────────┐
│   User Request      │
│  "Implement auth"   │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Orchestrator       │
│  - Analiza request  │
│  - Crea tasks       │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│ Code Generation     │
│ Agent               │
│ - Solo LLM base     │ ❌ Sin contexto del proyecto
│ - Sin ejemplos      │ ❌ Patrones inconsistentes
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Código Generado    │
│  (70-80% precisión) │
└─────────────────────┘
```

**Limitaciones**:
- ❌ LLM solo usa conocimiento general
- ❌ No aprende de código aprobado
- ❌ No sigue patrones específicos del proyecto
- ❌ Genera código genérico, no personalizado

### Arquitectura Objetivo (Con RAG)

```
┌─────────────────────┐
│   User Request      │
│  "Implement auth"   │
└──────────┬──────────┘
           │
           v
┌─────────────────────────────────────────┐
│         Orchestrator                    │
│  - Analiza request                      │
│  - Crea tasks                           │
│  - [NUEVO] Consulta RAG Retriever       │
└──────────┬──────────────────────────────┘
           │
           v
┌─────────────────────────────────────────┐
│      RAG Retriever                      │
│  1. Convierte task → embedding          │
│  2. Busca en ChromaDB                   │
│  3. Recupera top-k ejemplos similares   │
└──────────┬──────────────────────────────┘
           │
           v
┌─────────────────────────────────────────┐
│      ChromaDB Vector Store              │
│  - Embeddings de código aprobado        │
│  - Metadata (proyecto, tipo, stack)     │
│  - Similarity search optimizado         │
└──────────┬──────────────────────────────┘
           │
           v
┌─────────────────────────────────────────┐
│      RAG Context Builder                │
│  - Selecciona mejores ejemplos          │
│  - Formatea contexto para LLM           │
│  - Combina con instrucciones            │
└──────────┬──────────────────────────────┘
           │
           v
┌─────────────────────────────────────────┐
│    Code Generation Agent                │
│  - LLM + Contexto RAG enriquecido       │ ✅ Ejemplos relevantes
│  - Sigue patrones del proyecto          │ ✅ Consistente
└──────────┬──────────────────────────────┘
           │
           v
┌─────────────────────────────────────────┐
│      Código Generado                    │
│      (90%+ precisión)                   │
└──────────┬──────────────────────────────┘
           │
           v (código aprobado por humano)
┌─────────────────────────────────────────┐
│      Feedback Loop                      │
│  - Indexa código aprobado               │
│  - Actualiza ChromaDB                   │
│  - Mejora continua                      │
└─────────────────────────────────────────┘
```

**Mejoras**:
- ✅ RAG proporciona contexto específico del proyecto
- ✅ Aprendizaje continuo con código aprobado
- ✅ Patrones consistentes automáticamente
- ✅ Código personalizado, no genérico

---

## 📍 Fases de Implementación

### FASE 1: Setup y Configuración (4-6 horas)

#### 1.1 Instalación de Dependencias

**Objetivo**: Agregar ChromaDB y dependencias al proyecto

**Archivos a modificar**:
- `requirements.txt`
- `docker-compose.yml`
- `.env.example`

**Pasos detallados**:

1. **Actualizar requirements.txt**:
```bash
# Agregar al final de requirements.txt
chromadb>=0.4.22           # Vector database
sentence-transformers>=2.2.2  # Embeddings model
```

2. **Verificar compatibilidad**:
```bash
# Verificar conflictos de dependencias
pip install -r requirements.txt --dry-run
```

3. **Actualizar docker-compose.yml**:
```yaml
services:
  api:
    # ... configuración existente ...
    environment:
      # RAG Configuration
      - CHROMADB_HOST=chromadb
      - CHROMADB_PORT=8000
      - EMBEDDING_MODEL=all-MiniLM-L6-v2
      - RAG_TOP_K=5
      - RAG_SIMILARITY_THRESHOLD=0.7
    depends_on:
      - chromadb  # Nueva dependencia

  chromadb:
    image: chromadb/chroma:0.4.22
    container_name: devmatrix_chromadb
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    networks:
      - devmatrix_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  chromadb_data:
    driver: local
```

4. **Actualizar .env.example**:
```bash
# Agregar al final
# ===================================
# RAG Configuration
# ===================================
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_ENABLE_FEEDBACK=true
```

**Validación**:
```bash
# 1. Construir contenedores
docker-compose build

# 2. Iniciar ChromaDB
docker-compose up chromadb -d

# 3. Verificar health
curl http://localhost:8000/api/v1/heartbeat
# Esperado: {"nanosecond heartbeat": ...}

# 4. Verificar persistencia
docker exec -it devmatrix_chromadb ls -la /chroma/chroma
```

**Tiempo estimado**: 2 horas
**Dependencias**: Docker, Docker Compose
**Riesgo**: 🟢 Bajo

---

#### 1.2 Configuración de Embeddings

**Objetivo**: Configurar modelo de embeddings sentence-transformers

**Archivo a crear**: `src/rag/embeddings.py`

**Código completo**:
```python
"""
Embedding model configuration and management.

This module handles the initialization and usage of sentence-transformers
for converting code and text into vector embeddings.
"""

from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer
from src.observability import get_logger
from src.config import settings

logger = get_logger("embeddings")


class EmbeddingModel:
    """
    Wrapper for sentence-transformers embedding model.

    Provides thread-safe embedding generation with caching and
    GPU acceleration when available.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None
    ):
        """
        Initialize embedding model.

        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name

        # Auto-detect device if not specified
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        logger.info(
            "Initializing embedding model",
            model_name=model_name,
            device=device
        )

        # Load model
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(
                "Embedding model loaded successfully",
                embedding_dim=self.embedding_dim,
                model_name=model_name
            )
        except Exception as e:
            logger.error(
                "Failed to load embedding model",
                error=str(e),
                model_name=model_name
            )
            raise

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for list of texts.

        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding (default: 32)
            show_progress: Show progress bar (default: False)

        Returns:
            List of embedding vectors (each is list of floats)
        """
        if not texts:
            logger.warning("Empty text list provided for encoding")
            return []

        logger.debug(
            "Encoding texts",
            num_texts=len(texts),
            batch_size=batch_size
        )

        try:
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_tensor=False,
                normalize_embeddings=True  # Normalize for cosine similarity
            )

            # Convert to list of lists
            result = embeddings.tolist()

            logger.debug(
                "Encoding completed",
                num_embeddings=len(result),
                embedding_dim=len(result[0]) if result else 0
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to encode texts",
                error=str(e),
                num_texts=len(texts)
            )
            raise

    def encode_single(self, text: str) -> List[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text string to encode

        Returns:
            Embedding vector as list of floats
        """
        embeddings = self.encode([text], batch_size=1)
        return embeddings[0] if embeddings else []

    def get_embedding_dimension(self) -> int:
        """Get dimension of embedding vectors."""
        return self.embedding_dim


# Singleton instance for reuse across application
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """
    Get singleton embedding model instance.

    Creates model on first call, reuses on subsequent calls.
    Thread-safe initialization.

    Returns:
        EmbeddingModel instance
    """
    global _embedding_model

    if _embedding_model is None:
        model_name = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embedding_model = EmbeddingModel(model_name=model_name)

    return _embedding_model
```

**Validación**:
```python
# tests/unit/rag/test_embeddings.py
import pytest
from src.rag.embeddings import EmbeddingModel, get_embedding_model


def test_embedding_model_initialization():
    """Test model initializes correctly."""
    model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    assert model.embedding_dim == 384
    assert model.device in ["cuda", "cpu"]


def test_encode_single_text():
    """Test encoding single text."""
    model = get_embedding_model()
    text = "def authenticate_user(username, password):"

    embedding = model.encode_single(text)

    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(x, float) for x in embedding)


def test_encode_batch():
    """Test encoding batch of texts."""
    model = get_embedding_model()
    texts = [
        "def login(user, pass):",
        "def create_user(email, password):",
        "def authenticate(token):"
    ]

    embeddings = model.encode(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 384 for emb in embeddings)


def test_encode_empty_list():
    """Test encoding empty list."""
    model = get_embedding_model()
    embeddings = model.encode([])
    assert embeddings == []


def test_singleton_pattern():
    """Test get_embedding_model returns same instance."""
    model1 = get_embedding_model()
    model2 = get_embedding_model()
    assert model1 is model2
```

**Tiempo estimado**: 2 horas
**Dependencias**: FASE 1.1
**Riesgo**: 🟢 Bajo

---

#### 1.3 Configuración de Settings

**Objetivo**: Agregar configuración RAG a settings existentes

**Archivo a modificar**: `src/config.py`

**Código a agregar**:
```python
# Agregar al final de la clase Settings

# ===================================
# RAG Configuration
# ===================================
CHROMADB_HOST: str = Field(default="localhost", env="CHROMADB_HOST")
CHROMADB_PORT: int = Field(default=8000, env="CHROMADB_PORT")
EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
RAG_TOP_K: int = Field(default=5, env="RAG_TOP_K")
RAG_SIMILARITY_THRESHOLD: float = Field(default=0.7, env="RAG_SIMILARITY_THRESHOLD")
RAG_ENABLE_FEEDBACK: bool = Field(default=True, env="RAG_ENABLE_FEEDBACK")

@property
def chromadb_url(self) -> str:
    """Get ChromaDB connection URL."""
    return f"http://{self.CHROMADB_HOST}:{self.CHROMADB_PORT}"
```

**Validación**:
```python
# tests/unit/test_config.py (agregar test)
def test_rag_configuration():
    """Test RAG settings are loaded correctly."""
    from src.config import settings

    assert settings.CHROMADB_HOST is not None
    assert settings.CHROMADB_PORT == 8000
    assert settings.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
    assert settings.RAG_TOP_K == 5
    assert settings.RAG_SIMILARITY_THRESHOLD == 0.7
    assert isinstance(settings.RAG_ENABLE_FEEDBACK, bool)

    # Test chromadb_url property
    expected_url = f"http://{settings.CHROMADB_HOST}:{settings.CHROMADB_PORT}"
    assert settings.chromadb_url == expected_url
```

**Tiempo estimado**: 30 minutos
**Dependencias**: Ninguna
**Riesgo**: 🟢 Bajo

---

#### 1.4 Estructura de Directorios

**Objetivo**: Crear estructura de directorios para módulo RAG

**Comandos**:
```bash
# Crear estructura
mkdir -p src/rag
touch src/rag/__init__.py
touch src/rag/embeddings.py
touch src/rag/vector_store.py
touch src/rag/retriever.py
touch src/rag/context_builder.py
touch src/rag/feedback_service.py

# Crear tests
mkdir -p tests/unit/rag
touch tests/unit/rag/__init__.py
touch tests/unit/rag/test_embeddings.py
touch tests/unit/rag/test_vector_store.py
touch tests/unit/rag/test_retriever.py
touch tests/unit/rag/test_context_builder.py
touch tests/unit/rag/test_feedback_service.py

# Crear integration tests
mkdir -p tests/integration/rag
touch tests/integration/rag/__init__.py
touch tests/integration/rag/test_rag_pipeline.py

# Crear validation scripts
mkdir -p tests/validation/rag
touch tests/validation/rag/validate_chromadb.py
touch tests/validation/rag/validate_embeddings.py
```

**Estructura resultante**:
```
src/rag/
├── __init__.py
├── embeddings.py           # Modelo de embeddings
├── vector_store.py         # ChromaDB wrapper
├── retriever.py            # Retrieval logic
├── context_builder.py      # Context formatting
└── feedback_service.py     # Feedback loop

tests/
├── unit/rag/
│   ├── test_embeddings.py
│   ├── test_vector_store.py
│   ├── test_retriever.py
│   ├── test_context_builder.py
│   └── test_feedback_service.py
├── integration/rag/
│   └── test_rag_pipeline.py
└── validation/rag/
    ├── validate_chromadb.py
    └── validate_embeddings.py
```

**Tiempo estimado**: 15 minutos
**Dependencias**: Ninguna
**Riesgo**: 🟢 Bajo

---

### FASE 2: Vector Store Implementation (6-8 horas)

#### 2.1 ChromaDB Client Wrapper

**Objetivo**: Crear wrapper para ChromaDB con gestión de colecciones

**Archivo a crear**: `src/rag/vector_store.py`

**Código completo**:
```python
"""
ChromaDB vector store implementation.

This module provides a wrapper around ChromaDB for storing and retrieving
code embeddings with metadata.
"""

from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from src.observability import get_logger
from src.config import settings
from src.rag.embeddings import get_embedding_model

logger = get_logger("vector_store")


class DevMatrixVectorStore:
    """
    Vector store for DevMatrix code embeddings using ChromaDB.

    Manages collections for different types of code artifacts
    and provides similarity search capabilities.
    """

    # Collection names
    COLLECTION_CODE = "devmatrix_code"
    COLLECTION_TESTS = "devmatrix_tests"
    COLLECTION_DOCS = "devmatrix_docs"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        embedding_model: Optional[Any] = None
    ):
        """
        Initialize ChromaDB client and collections.

        Args:
            host: ChromaDB host (default: from settings)
            port: ChromaDB port (default: from settings)
            embedding_model: Custom embedding model (default: get_embedding_model())
        """
        self.host = host or settings.CHROMADB_HOST
        self.port = port or settings.CHROMADB_PORT
        self.embedding_model = embedding_model or get_embedding_model()

        logger.info(
            "Initializing ChromaDB vector store",
            host=self.host,
            port=self.port
        )

        # Initialize ChromaDB client
        try:
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )

            # Test connection
            self.client.heartbeat()

            logger.info("ChromaDB connection established")

        except Exception as e:
            logger.error(
                "Failed to connect to ChromaDB",
                error=str(e),
                host=self.host,
                port=self.port
            )
            raise

        # Initialize collections
        self._init_collections()

    def _init_collections(self):
        """Initialize or get existing collections."""
        logger.info("Initializing collections")

        # Get or create code collection
        self.code_collection = self.client.get_or_create_collection(
            name=self.COLLECTION_CODE,
            metadata={
                "description": "Code snippets and implementations",
                "embedding_model": self.embedding_model.model_name
            }
        )

        # Get or create tests collection
        self.tests_collection = self.client.get_or_create_collection(
            name=self.COLLECTION_TESTS,
            metadata={
                "description": "Test cases and examples",
                "embedding_model": self.embedding_model.model_name
            }
        )

        # Get or create docs collection
        self.docs_collection = self.client.get_or_create_collection(
            name=self.COLLECTION_DOCS,
            metadata={
                "description": "Documentation and comments",
                "embedding_model": self.embedding_model.model_name
            }
        )

        logger.info(
            "Collections initialized",
            code_count=self.code_collection.count(),
            tests_count=self.tests_collection.count(),
            docs_count=self.docs_collection.count()
        )

    def add_code(
        self,
        code: str,
        metadata: Dict[str, Any],
        code_id: Optional[str] = None
    ) -> str:
        """
        Add code snippet to vector store.

        Args:
            code: Code content
            metadata: Metadata dict with keys like:
                - project_id: Project identifier
                - file_path: File path
                - language: Programming language
                - task_type: Type of task (e.g., "authentication", "api")
                - approved: Whether code was human-approved
                - created_at: Timestamp
            code_id: Optional custom ID (auto-generated if None)

        Returns:
            ID of stored code
        """
        if not code.strip():
            logger.warning("Empty code provided, skipping")
            return None

        # Generate embedding
        embedding = self.embedding_model.encode_single(code)

        # Generate ID if not provided
        if code_id is None:
            import hashlib
            code_id = hashlib.md5(code.encode()).hexdigest()[:16]

        # Add to collection
        try:
            self.code_collection.add(
                ids=[code_id],
                embeddings=[embedding],
                documents=[code],
                metadatas=[metadata]
            )

            logger.info(
                "Code added to vector store",
                code_id=code_id,
                project_id=metadata.get("project_id"),
                file_path=metadata.get("file_path")
            )

            return code_id

        except Exception as e:
            logger.error(
                "Failed to add code to vector store",
                error=str(e),
                code_id=code_id
            )
            raise

    def add_codes_batch(
        self,
        codes: List[str],
        metadatas: List[Dict[str, Any]],
        code_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add multiple code snippets in batch.

        Args:
            codes: List of code contents
            metadatas: List of metadata dicts
            code_ids: Optional list of custom IDs

        Returns:
            List of IDs for stored codes
        """
        if not codes:
            logger.warning("Empty codes list provided")
            return []

        if len(codes) != len(metadatas):
            raise ValueError("codes and metadatas must have same length")

        # Generate embeddings
        embeddings = self.embedding_model.encode(codes, batch_size=32)

        # Generate IDs if not provided
        if code_ids is None:
            import hashlib
            code_ids = [
                hashlib.md5(code.encode()).hexdigest()[:16]
                for code in codes
            ]

        # Add to collection
        try:
            self.code_collection.add(
                ids=code_ids,
                embeddings=embeddings,
                documents=codes,
                metadatas=metadatas
            )

            logger.info(
                "Batch codes added to vector store",
                count=len(codes)
            )

            return code_ids

        except Exception as e:
            logger.error(
                "Failed to add batch codes",
                error=str(e),
                count=len(codes)
            )
            raise

    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        collection_name: str = COLLECTION_CODE
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code snippets.

        Args:
            query: Query text (code or description)
            n_results: Number of results to return (default: 5)
            filter_metadata: Optional metadata filter (e.g., {"project_id": "123"})
            collection_name: Collection to search (default: code collection)

        Returns:
            List of results with keys:
                - id: Code ID
                - code: Code content
                - metadata: Metadata dict
                - distance: Similarity distance (lower = more similar)
        """
        # Get collection
        if collection_name == self.COLLECTION_CODE:
            collection = self.code_collection
        elif collection_name == self.COLLECTION_TESTS:
            collection = self.tests_collection
        elif collection_name == self.COLLECTION_DOCS:
            collection = self.docs_collection
        else:
            raise ValueError(f"Invalid collection name: {collection_name}")

        # Generate query embedding
        query_embedding = self.embedding_model.encode_single(query)

        # Search
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )

            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'code': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })

            logger.info(
                "Similar code search completed",
                query_length=len(query),
                n_results=len(formatted_results),
                collection=collection_name
            )

            return formatted_results

        except Exception as e:
            logger.error(
                "Failed to search similar code",
                error=str(e),
                collection=collection_name
            )
            raise

    def get_by_id(
        self,
        code_id: str,
        collection_name: str = COLLECTION_CODE
    ) -> Optional[Dict[str, Any]]:
        """
        Get code by ID.

        Args:
            code_id: Code ID
            collection_name: Collection to search

        Returns:
            Result dict with keys: id, code, metadata, or None if not found
        """
        # Get collection
        if collection_name == self.COLLECTION_CODE:
            collection = self.code_collection
        elif collection_name == self.COLLECTION_TESTS:
            collection = self.tests_collection
        elif collection_name == self.COLLECTION_DOCS:
            collection = self.docs_collection
        else:
            raise ValueError(f"Invalid collection name: {collection_name}")

        try:
            results = collection.get(ids=[code_id])

            if not results['ids']:
                logger.warning("Code not found", code_id=code_id)
                return None

            return {
                'id': results['ids'][0],
                'code': results['documents'][0],
                'metadata': results['metadatas'][0]
            }

        except Exception as e:
            logger.error(
                "Failed to get code by ID",
                error=str(e),
                code_id=code_id
            )
            raise

    def delete(
        self,
        code_id: str,
        collection_name: str = COLLECTION_CODE
    ):
        """
        Delete code by ID.

        Args:
            code_id: Code ID
            collection_name: Collection to delete from
        """
        # Get collection
        if collection_name == self.COLLECTION_CODE:
            collection = self.code_collection
        elif collection_name == self.COLLECTION_TESTS:
            collection = self.tests_collection
        elif collection_name == self.COLLECTION_DOCS:
            collection = self.docs_collection
        else:
            raise ValueError(f"Invalid collection name: {collection_name}")

        try:
            collection.delete(ids=[code_id])

            logger.info(
                "Code deleted from vector store",
                code_id=code_id,
                collection=collection_name
            )

        except Exception as e:
            logger.error(
                "Failed to delete code",
                error=str(e),
                code_id=code_id
            )
            raise

    def clear_collection(self, collection_name: str):
        """
        Clear all data from collection.

        Args:
            collection_name: Collection to clear
        """
        try:
            self.client.delete_collection(name=collection_name)
            self._init_collections()

            logger.warning(
                "Collection cleared",
                collection=collection_name
            )

        except Exception as e:
            logger.error(
                "Failed to clear collection",
                error=str(e),
                collection=collection_name
            )
            raise

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about vector store.

        Returns:
            Dict with collection counts
        """
        return {
            'code_count': self.code_collection.count(),
            'tests_count': self.tests_collection.count(),
            'docs_count': self.docs_collection.count()
        }


# Singleton instance
_vector_store: Optional[DevMatrixVectorStore] = None


def get_vector_store() -> DevMatrixVectorStore:
    """
    Get singleton vector store instance.

    Returns:
        DevMatrixVectorStore instance
    """
    global _vector_store

    if _vector_store is None:
        _vector_store = DevMatrixVectorStore()

    return _vector_store
```

**Validación**:
```python
# tests/integration/rag/test_vector_store_integration.py
import pytest
from src.rag.vector_store import DevMatrixVectorStore, get_vector_store


@pytest.fixture
def vector_store():
    """Create vector store instance for testing."""
    store = DevMatrixVectorStore()
    yield store
    # Cleanup after tests
    store.clear_collection(store.COLLECTION_CODE)


def test_add_and_search_code(vector_store):
    """Test adding code and searching for similar."""
    # Add code
    code = """
def authenticate_user(username: str, password: str) -> bool:
    user = db.get_user(username)
    return user.verify_password(password)
"""
    metadata = {
        "project_id": "test_project",
        "file_path": "auth.py",
        "language": "python",
        "task_type": "authentication",
        "approved": True
    }

    code_id = vector_store.add_code(code, metadata)
    assert code_id is not None

    # Search for similar
    query = "implement user authentication"
    results = vector_store.search_similar(query, n_results=1)

    assert len(results) == 1
    assert results[0]['id'] == code_id
    assert 'authenticate_user' in results[0]['code']


def test_batch_add(vector_store):
    """Test batch adding codes."""
    codes = [
        "def login(user, pass): ...",
        "def logout(session): ...",
        "def create_user(email, password): ..."
    ]
    metadatas = [
        {"project_id": "test", "task_type": "auth"},
        {"project_id": "test", "task_type": "auth"},
        {"project_id": "test", "task_type": "user_management"}
    ]

    ids = vector_store.add_codes_batch(codes, metadatas)

    assert len(ids) == 3
    assert vector_store.code_collection.count() >= 3


def test_metadata_filtering(vector_store):
    """Test filtering by metadata."""
    # Add codes with different projects
    vector_store.add_code(
        "def func1(): pass",
        {"project_id": "project_a", "task_type": "api"}
    )
    vector_store.add_code(
        "def func2(): pass",
        {"project_id": "project_b", "task_type": "api"}
    )

    # Search with filter
    results = vector_store.search_similar(
        "function",
        n_results=10,
        filter_metadata={"project_id": "project_a"}
    )

    # All results should be from project_a
    assert all(r['metadata']['project_id'] == 'project_a' for r in results)


def test_singleton_pattern():
    """Test get_vector_store returns same instance."""
    store1 = get_vector_store()
    store2 = get_vector_store()
    assert store1 is store2
```

**Tiempo estimado**: 4 horas
**Dependencias**: FASE 1
**Riesgo**: 🟡 Medio

---

#### 2.2 Validation Script

**Objetivo**: Script para validar ChromaDB funcionamiento

**Archivo a crear**: `tests/validation/rag/validate_chromadb.py`

**Código completo**:
```python
#!/usr/bin/env python
"""
Validation script for ChromaDB integration.

Tests connection, collections, and basic operations.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.rag.vector_store import DevMatrixVectorStore
from src.observability import setup_logging


def main():
    """Run ChromaDB validation."""
    setup_logging()

    print("🔍 ChromaDB Validation")
    print("=" * 50)
    print()

    # Test 1: Connection
    print("Test 1: ChromaDB Connection")
    try:
        store = DevMatrixVectorStore()
        print("✓ PASSED: ChromaDB connection established")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return 1
    print()

    # Test 2: Collections initialized
    print("Test 2: Collections Initialized")
    try:
        stats = store.get_stats()
        assert 'code_count' in stats
        assert 'tests_count' in stats
        assert 'docs_count' in stats
        print(f"✓ PASSED: Collections initialized")
        print(f"  - Code collection: {stats['code_count']} items")
        print(f"  - Tests collection: {stats['tests_count']} items")
        print(f"  - Docs collection: {stats['docs_count']} items")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return 1
    print()

    # Test 3: Add code
    print("Test 3: Add Code")
    try:
        code = "def test_function(): return True"
        metadata = {
            "project_id": "validation_test",
            "task_type": "test"
        }
        code_id = store.add_code(code, metadata)
        assert code_id is not None
        print(f"✓ PASSED: Code added with ID {code_id}")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return 1
    print()

    # Test 4: Search
    print("Test 4: Similarity Search")
    try:
        results = store.search_similar("test function", n_results=1)
        assert len(results) > 0
        print(f"✓ PASSED: Found {len(results)} similar results")
        print(f"  - Top result distance: {results[0]['distance']:.4f}")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return 1
    print()

    # Test 5: Metadata filtering
    print("Test 5: Metadata Filtering")
    try:
        results = store.search_similar(
            "function",
            n_results=10,
            filter_metadata={"project_id": "validation_test"}
        )
        assert all(r['metadata']['project_id'] == 'validation_test' for r in results)
        print(f"✓ PASSED: Metadata filtering works")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return 1
    print()

    # Cleanup
    print("Cleanup: Removing validation data")
    try:
        store.delete(code_id)
        print("✓ PASSED: Cleanup successful")
    except Exception as e:
        print(f"⚠ WARNING: Cleanup failed: {e}")
    print()

    print("=" * 50)
    print("✓ All validation tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Ejecutar validación**:
```bash
# Asegurar ChromaDB está corriendo
docker-compose up chromadb -d

# Ejecutar validación
python tests/validation/rag/validate_chromadb.py
```

**Tiempo estimado**: 1 hora
**Dependencias**: FASE 2.1
**Riesgo**: 🟢 Bajo

---

### FASE 3: Retriever Implementation (4-6 horas)

#### 3.1 RAG Retriever

**Objetivo**: Implementar lógica de recuperación con ranking y filtering

**Archivo a crear**: `src/rag/retriever.py`

**Código completo**:
```python
"""
RAG retriever for code examples.

This module implements retrieval logic for finding relevant code examples
based on task descriptions and context.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.observability import get_logger
from src.config import settings
from src.rag.vector_store import get_vector_store

logger = get_logger("rag_retriever")


@dataclass
class RetrievalResult:
    """Result from retrieval operation."""
    code_id: str
    code: str
    metadata: Dict[str, Any]
    similarity_score: float  # 0-1 (1 = perfect match)
    rank: int  # Position in results (1 = best)


class RAGRetriever:
    """
    Retriever for finding relevant code examples.

    Implements intelligent retrieval with:
    - Similarity search
    - Metadata filtering
    - Result ranking and reranking
    - Diversity optimization
    """

    def __init__(
        self,
        vector_store=None,
        top_k: int = None,
        similarity_threshold: float = None
    ):
        """
        Initialize retriever.

        Args:
            vector_store: Vector store instance (default: singleton)
            top_k: Number of results to return (default: from settings)
            similarity_threshold: Minimum similarity score (default: from settings)
        """
        self.vector_store = vector_store or get_vector_store()
        self.top_k = top_k or settings.RAG_TOP_K
        self.similarity_threshold = similarity_threshold or settings.RAG_SIMILARITY_THRESHOLD

        logger.info(
            "RAG retriever initialized",
            top_k=self.top_k,
            similarity_threshold=self.similarity_threshold
        )

    def retrieve(
        self,
        query: str,
        project_id: Optional[str] = None,
        task_type: Optional[str] = None,
        language: Optional[str] = None,
        diversity_factor: float = 0.3
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant code examples.

        Args:
            query: Task description or code intent
            project_id: Filter by project ID
            task_type: Filter by task type (e.g., "authentication")
            language: Filter by programming language
            diversity_factor: Diversity weight (0=similarity only, 1=max diversity)

        Returns:
            List of RetrievalResult, ranked by relevance
        """
        logger.info(
            "Starting retrieval",
            query_length=len(query),
            project_id=project_id,
            task_type=task_type,
            language=language
        )

        # Build metadata filter
        filter_metadata = {}
        if project_id:
            filter_metadata['project_id'] = project_id
        if task_type:
            filter_metadata['task_type'] = task_type
        if language:
            filter_metadata['language'] = language

        # Search vector store
        # Retrieve more than top_k for reranking
        n_candidates = self.top_k * 3

        try:
            raw_results = self.vector_store.search_similar(
                query=query,
                n_results=n_candidates,
                filter_metadata=filter_metadata if filter_metadata else None
            )
        except Exception as e:
            logger.error("Failed to retrieve from vector store", error=str(e))
            return []

        if not raw_results:
            logger.warning("No results found for query")
            return []

        # Convert distances to similarity scores (1 - normalized_distance)
        results_with_scores = []
        for result in raw_results:
            # Distance to similarity (cosine distance: 0=identical, 2=opposite)
            # Normalize to 0-1 where 1 is most similar
            similarity = 1 - (result['distance'] / 2)

            results_with_scores.append({
                'code_id': result['id'],
                'code': result['code'],
                'metadata': result['metadata'],
                'similarity_score': similarity
            })

        # Filter by similarity threshold
        filtered_results = [
            r for r in results_with_scores
            if r['similarity_score'] >= self.similarity_threshold
        ]

        if not filtered_results:
            logger.warning(
                "No results above similarity threshold",
                threshold=self.similarity_threshold,
                best_score=results_with_scores[0]['similarity_score'] if results_with_scores else 0
            )
            return []

        # Rerank with diversity
        if diversity_factor > 0:
            reranked = self._rerank_with_diversity(
                filtered_results,
                diversity_factor=diversity_factor
            )
        else:
            reranked = filtered_results

        # Take top_k
        final_results = reranked[:self.top_k]

        # Convert to RetrievalResult objects
        retrieval_results = []
        for rank, result in enumerate(final_results, start=1):
            retrieval_results.append(
                RetrievalResult(
                    code_id=result['code_id'],
                    code=result['code'],
                    metadata=result['metadata'],
                    similarity_score=result['similarity_score'],
                    rank=rank
                )
            )

        logger.info(
            "Retrieval completed",
            num_candidates=len(raw_results),
            num_filtered=len(filtered_results),
            num_final=len(retrieval_results),
            best_score=retrieval_results[0].similarity_score if retrieval_results else 0
        )

        return retrieval_results

    def _rerank_with_diversity(
        self,
        results: List[Dict[str, Any]],
        diversity_factor: float
    ) -> List[Dict[str, Any]]:
        """
        Rerank results balancing similarity and diversity.

        Uses Maximal Marginal Relevance (MMR) algorithm.

        Args:
            results: Results to rerank
            diversity_factor: Weight for diversity (lambda in MMR)

        Returns:
            Reranked results
        """
        if len(results) <= 1:
            return results

        # MMR: score = λ * similarity - (1-λ) * max_similarity_to_selected
        selected = []
        remaining = results.copy()

        # Always select most similar first
        selected.append(remaining.pop(0))

        while remaining and len(selected) < len(results):
            best_idx = 0
            best_score = float('-inf')

            for idx, candidate in enumerate(remaining):
                # Similarity to query
                sim_query = candidate['similarity_score']

                # Max similarity to already selected
                max_sim_selected = max(
                    self._code_similarity(candidate['code'], s['code'])
                    for s in selected
                )

                # MMR score
                mmr_score = (
                    diversity_factor * sim_query -
                    (1 - diversity_factor) * max_sim_selected
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            selected.append(remaining.pop(best_idx))

        return selected

    def _code_similarity(self, code1: str, code2: str) -> float:
        """
        Calculate simple similarity between two code strings.

        Uses Jaccard similarity on tokens.

        Args:
            code1: First code string
            code2: Second code string

        Returns:
            Similarity score 0-1
        """
        # Simple tokenization (words and symbols)
        tokens1 = set(code1.split())
        tokens2 = set(code2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union) if union else 0.0

    def retrieve_by_example(
        self,
        example_code: str,
        project_id: Optional[str] = None,
        exclude_id: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve similar code by example.

        Args:
            example_code: Example code to find similar to
            project_id: Filter by project
            exclude_id: Exclude specific code ID (e.g., the example itself)

        Returns:
            List of similar code examples
        """
        logger.info(
            "Retrieving by example",
            example_length=len(example_code),
            project_id=project_id
        )

        # Use example code as query
        results = self.retrieve(
            query=example_code,
            project_id=project_id
        )

        # Exclude specified ID
        if exclude_id:
            results = [r for r in results if r.code_id != exclude_id]

        return results


# Singleton instance
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """
    Get singleton retriever instance.

    Returns:
        RAGRetriever instance
    """
    global _retriever

    if _retriever is None:
        _retriever = RAGRetriever()

    return _retriever
```

**Tests**:
```python
# tests/unit/rag/test_retriever.py
import pytest
from src.rag.retriever import RAGRetriever, RetrievalResult
from unittest.mock import Mock, patch


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    store = Mock()
    store.search_similar.return_value = [
        {
            'id': 'code1',
            'code': 'def login(user, pass): ...',
            'metadata': {'project_id': 'test', 'task_type': 'auth'},
            'distance': 0.2
        },
        {
            'id': 'code2',
            'code': 'def authenticate(token): ...',
            'metadata': {'project_id': 'test', 'task_type': 'auth'},
            'distance': 0.4
        }
    ]
    return store


def test_retrieve_basic(mock_vector_store):
    """Test basic retrieval."""
    retriever = RAGRetriever(vector_store=mock_vector_store, top_k=2)

    results = retriever.retrieve("implement authentication")

    assert len(results) == 2
    assert all(isinstance(r, RetrievalResult) for r in results)
    assert results[0].rank == 1
    assert results[1].rank == 2
    assert results[0].similarity_score > results[1].similarity_score


def test_retrieve_with_filters(mock_vector_store):
    """Test retrieval with metadata filters."""
    retriever = RAGRetriever(vector_store=mock_vector_store)

    retriever.retrieve(
        "authentication",
        project_id="test",
        task_type="auth",
        language="python"
    )

    # Verify filter was passed
    call_args = mock_vector_store.search_similar.call_args
    assert call_args[1]['filter_metadata'] == {
        'project_id': 'test',
        'task_type': 'auth',
        'language': 'python'
    }


def test_similarity_threshold_filtering(mock_vector_store):
    """Test filtering by similarity threshold."""
    # Set high threshold
    retriever = RAGRetriever(
        vector_store=mock_vector_store,
        similarity_threshold=0.95
    )

    results = retriever.retrieve("query")

    # Both results should be filtered out (scores: 0.9, 0.8)
    assert len(results) == 0


def test_code_similarity():
    """Test code similarity calculation."""
    retriever = RAGRetriever()

    code1 = "def login(user, password): return True"
    code2 = "def login(user, password): return False"
    code3 = "def logout(session): return None"

    # Similar codes
    sim1 = retriever._code_similarity(code1, code2)
    assert sim1 > 0.7

    # Different codes
    sim2 = retriever._code_similarity(code1, code3)
    assert sim2 < 0.5
```

**Tiempo estimado**: 4 horas
**Dependencias**: FASE 2
**Riesgo**: 🟡 Medio

---

### FASE 4: Context Builder (3-4 horas)

#### 4.1 RAG Context Builder

**Objetivo**: Formatear ejemplos recuperados en contexto para LLM

**Archivo a crear**: `src/rag/context_builder.py`

**Código completo**:
```python
"""
RAG context builder for LLM prompts.

This module formats retrieved code examples into structured context
for code generation agents.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.observability import get_logger
from src.rag.retriever import RetrievalResult

logger = get_logger("rag_context_builder")


@dataclass
class RAGContext:
    """Formatted RAG context for LLM."""
    system_context: str  # System message with RAG instructions
    user_context: str  # User message with task + examples
    examples_count: int  # Number of examples included
    metadata: Dict[str, Any]  # Context metadata


class RAGContextBuilder:
    """
    Builder for creating RAG-enhanced prompts.

    Formats retrieved code examples into structured context
    that guides the LLM to generate consistent code.
    """

    def __init__(
        self,
        max_context_length: int = 8000,
        include_metadata: bool = True
    ):
        """
        Initialize context builder.

        Args:
            max_context_length: Max tokens for context (default: 8000)
            include_metadata: Include metadata in examples (default: True)
        """
        self.max_context_length = max_context_length
        self.include_metadata = include_metadata

        logger.info(
            "RAG context builder initialized",
            max_context_length=max_context_length,
            include_metadata=include_metadata
        )

    def build_context(
        self,
        task_description: str,
        retrieval_results: List[RetrievalResult],
        project_context: Optional[Dict[str, Any]] = None
    ) -> RAGContext:
        """
        Build RAG context from retrieved examples.

        Args:
            task_description: Task to implement
            retrieval_results: Retrieved code examples
            project_context: Optional project-specific context

        Returns:
            RAGContext with formatted prompts
        """
        logger.info(
            "Building RAG context",
            task_length=len(task_description),
            num_examples=len(retrieval_results)
        )

        # Filter examples by context length
        selected_examples = self._select_examples(
            retrieval_results,
            max_length=self.max_context_length
        )

        # Build system context
        system_context = self._build_system_context(
            project_context=project_context,
            num_examples=len(selected_examples)
        )

        # Build user context with examples
        user_context = self._build_user_context(
            task_description=task_description,
            examples=selected_examples
        )

        # Create metadata
        metadata = {
            'total_examples': len(retrieval_results),
            'selected_examples': len(selected_examples),
            'avg_similarity': sum(e.similarity_score for e in selected_examples) / len(selected_examples) if selected_examples else 0,
            'task_types': list(set(e.metadata.get('task_type', 'unknown') for e in selected_examples))
        }

        logger.info(
            "RAG context built",
            system_length=len(system_context),
            user_length=len(user_context),
            examples_selected=len(selected_examples)
        )

        return RAGContext(
            system_context=system_context,
            user_context=user_context,
            examples_count=len(selected_examples),
            metadata=metadata
        )

    def _select_examples(
        self,
        results: List[RetrievalResult],
        max_length: int
    ) -> List[RetrievalResult]:
        """
        Select examples that fit within context length.

        Args:
            results: Retrieved results
            max_length: Max total length

        Returns:
            Filtered list of examples
        """
        selected = []
        current_length = 0

        for result in results:
            # Estimate token length (rough: 1 token ≈ 4 chars)
            example_length = len(result.code) // 4

            if current_length + example_length <= max_length:
                selected.append(result)
                current_length += example_length
            else:
                logger.debug(
                    "Skipping example due to length",
                    code_id=result.code_id,
                    example_length=example_length,
                    current_length=current_length
                )
                break

        return selected

    def _build_system_context(
        self,
        project_context: Optional[Dict[str, Any]],
        num_examples: int
    ) -> str:
        """Build system message with RAG instructions."""
        parts = []

        # Base instructions
        parts.append(
            "You are an expert code generation assistant. "
            "You have been provided with relevant code examples from approved implementations. "
            "Follow the patterns, style, and conventions demonstrated in these examples."
        )

        # Project context
        if project_context:
            if 'language' in project_context:
                parts.append(f"\nProject Language: {project_context['language']}")
            if 'framework' in project_context:
                parts.append(f"Framework: {project_context['framework']}")
            if 'coding_standards' in project_context:
                parts.append(f"Coding Standards: {project_context['coding_standards']}")

        # RAG guidance
        parts.append(
            f"\n\nYou have access to {num_examples} relevant code example(s). "
            "Study them carefully and:"
        )
        parts.append("1. Follow the same code structure and organization")
        parts.append("2. Use similar naming conventions")
        parts.append("3. Maintain consistent error handling patterns")
        parts.append("4. Apply the same design patterns")
        parts.append("5. Match the coding style and formatting")

        parts.append(
            "\n\nGenerate code that fits naturally into this existing codebase. "
            "Consistency is critical for maintainability."
        )

        return "\n".join(parts)

    def _build_user_context(
        self,
        task_description: str,
        examples: List[RetrievalResult]
    ) -> str:
        """Build user message with task and examples."""
        parts = []

        # Task description
        parts.append(f"**Task**: {task_description}\n")

        # Examples section
        if examples:
            parts.append("**Relevant Code Examples:**\n")

            for i, example in enumerate(examples, start=1):
                parts.append(f"--- Example {i} (similarity: {example.similarity_score:.2f}) ---")

                # Add metadata if enabled
                if self.include_metadata:
                    metadata_parts = []
                    if 'file_path' in example.metadata:
                        metadata_parts.append(f"File: {example.metadata['file_path']}")
                    if 'task_type' in example.metadata:
                        metadata_parts.append(f"Type: {example.metadata['task_type']}")
                    if metadata_parts:
                        parts.append(f"({', '.join(metadata_parts)})")

                # Add code
                parts.append(f"```\n{example.code.strip()}\n```\n")

        # Generation instructions
        parts.append(
            "\n**Instructions**: Generate code for the task above, "
            "following the patterns and style from the examples. "
            "Ensure consistency with the existing codebase."
        )

        return "\n".join(parts)

    def build_simple_context(
        self,
        task_description: str,
        code_examples: List[str]
    ) -> str:
        """
        Build simple context from code strings (no retrieval objects).

        Args:
            task_description: Task to implement
            code_examples: List of code strings

        Returns:
            Formatted context string
        """
        parts = [f"**Task**: {task_description}\n"]

        if code_examples:
            parts.append("**Relevant Examples:**\n")
            for i, code in enumerate(code_examples, start=1):
                parts.append(f"--- Example {i} ---")
                parts.append(f"```\n{code.strip()}\n```\n")

        parts.append(
            "\n**Instructions**: Generate code following the patterns from the examples."
        )

        return "\n".join(parts)


# Singleton instance
_context_builder: Optional[RAGContextBuilder] = None


def get_context_builder() -> RAGContextBuilder:
    """
    Get singleton context builder instance.

    Returns:
        RAGContextBuilder instance
    """
    global _context_builder

    if _context_builder is None:
        _context_builder = RAGContextBuilder()

    return _context_builder
```

**Tests**:
```python
# tests/unit/rag/test_context_builder.py
import pytest
from src.rag.context_builder import RAGContextBuilder, RAGContext
from src.rag.retriever import RetrievalResult


@pytest.fixture
def sample_results():
    """Create sample retrieval results."""
    return [
        RetrievalResult(
            code_id="1",
            code="def login(user, pass): ...",
            metadata={"file_path": "auth.py", "task_type": "auth"},
            similarity_score=0.9,
            rank=1
        ),
        RetrievalResult(
            code_id="2",
            code="def authenticate(token): ...",
            metadata={"file_path": "auth.py", "task_type": "auth"},
            similarity_score=0.8,
            rank=2
        )
    ]


def test_build_context(sample_results):
    """Test building RAG context."""
    builder = RAGContextBuilder()
    task = "Implement user authentication"

    context = builder.build_context(task, sample_results)

    assert isinstance(context, RAGContext)
    assert "authentication" in context.user_context.lower()
    assert "Example 1" in context.user_context
    assert "Example 2" in context.user_context
    assert context.examples_count == 2


def test_system_context_with_project_info(sample_results):
    """Test system context includes project info."""
    builder = RAGContextBuilder()
    task = "Implement auth"
    project_context = {
        "language": "Python",
        "framework": "FastAPI",
        "coding_standards": "PEP 8"
    }

    context = builder.build_context(task, sample_results, project_context)

    assert "Python" in context.system_context
    assert "FastAPI" in context.system_context
    assert "PEP 8" in context.system_context


def test_context_length_limit():
    """Test context respects length limit."""
    builder = RAGContextBuilder(max_context_length=100)

    # Create many large examples
    large_results = [
        RetrievalResult(
            code_id=str(i),
            code="def function(): " + "x" * 1000,
            metadata={},
            similarity_score=0.9,
            rank=i
        )
        for i in range(10)
    ]

    task = "Test task"
    context = builder.build_context(task, large_results)

    # Should have selected fewer examples due to length limit
    assert context.examples_count < len(large_results)


def test_simple_context():
    """Test simple context building."""
    builder = RAGContextBuilder()
    task = "Implement login"
    examples = ["def login(): pass", "def authenticate(): pass"]

    context = builder.build_simple_context(task, examples)

    assert "Implement login" in context
    assert "Example 1" in context
    assert "def login" in context
```

**Tiempo estimado**: 3 horas
**Dependencias**: FASE 3
**Riesgo**: 🟢 Bajo

---

### FASE 5: Feedback Service (3-4 horas)

#### 5.1 Feedback Loop Implementation

**Objetivo**: Implementar feedback loop para aprendizaje continuo

**Archivo a crear**: `src/rag/feedback_service.py`

**Código completo**:
```python
"""
Feedback service for RAG system.

This module handles feedback collection and indexing of approved code
back into the vector store for continuous learning.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from src.observability import get_logger
from src.config import settings
from src.rag.vector_store import get_vector_store
from src.state.postgres_manager import PostgresManager

logger = get_logger("rag_feedback")


class FeedbackService:
    """
    Service for handling code approval feedback.

    Implements continuous learning by indexing approved code
    back into the RAG system.
    """

    def __init__(
        self,
        vector_store=None,
        postgres_manager=None,
        enabled: bool = None
    ):
        """
        Initialize feedback service.

        Args:
            vector_store: Vector store instance
            postgres_manager: PostgreSQL manager for tracking
            enabled: Enable feedback (default: from settings)
        """
        self.vector_store = vector_store or get_vector_store()
        self.postgres_manager = postgres_manager or PostgresManager()
        self.enabled = enabled if enabled is not None else settings.RAG_ENABLE_FEEDBACK

        logger.info(
            "Feedback service initialized",
            enabled=self.enabled
        )

    def record_approval(
        self,
        code: str,
        metadata: Dict[str, Any],
        task_id: str,
        workspace_id: str
    ) -> Optional[str]:
        """
        Record approved code and index it for future retrieval.

        Args:
            code: Approved code content
            metadata: Code metadata (project_id, file_path, language, task_type)
            task_id: Task identifier
            workspace_id: Workspace identifier

        Returns:
            Code ID if indexed successfully, None otherwise
        """
        if not self.enabled:
            logger.debug("Feedback disabled, skipping approval recording")
            return None

        logger.info(
            "Recording code approval",
            task_id=task_id,
            workspace_id=workspace_id,
            file_path=metadata.get('file_path', 'unknown')
        )

        # Enrich metadata
        enriched_metadata = {
            **metadata,
            'approved': True,
            'approved_at': datetime.utcnow().isoformat(),
            'task_id': task_id,
            'workspace_id': workspace_id
        }

        try:
            # Index in vector store
            code_id = self.vector_store.add_code(
                code=code,
                metadata=enriched_metadata
            )

            # Track in PostgreSQL
            self._track_in_postgres(
                code_id=code_id,
                task_id=task_id,
                workspace_id=workspace_id,
                metadata=enriched_metadata
            )

            logger.info(
                "Code approval recorded successfully",
                code_id=code_id,
                task_id=task_id
            )

            return code_id

        except Exception as e:
            logger.error(
                "Failed to record code approval",
                error=str(e),
                task_id=task_id
            )
            return None

    def record_rejection(
        self,
        code: str,
        reason: str,
        task_id: str,
        workspace_id: str
    ):
        """
        Record rejected code for analysis (not indexed).

        Args:
            code: Rejected code content
            reason: Rejection reason
            task_id: Task identifier
            workspace_id: Workspace identifier
        """
        logger.info(
            "Recording code rejection",
            task_id=task_id,
            workspace_id=workspace_id,
            reason=reason
        )

        try:
            # Track rejection in PostgreSQL for analysis
            self._track_rejection_in_postgres(
                task_id=task_id,
                workspace_id=workspace_id,
                reason=reason,
                code_length=len(code)
            )

            logger.info(
                "Code rejection recorded",
                task_id=task_id
            )

        except Exception as e:
            logger.error(
                "Failed to record rejection",
                error=str(e),
                task_id=task_id
            )

    def batch_index_approved_code(
        self,
        project_id: str,
        workspace_id: str,
        code_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch index multiple approved code files.

        Args:
            project_id: Project identifier
            workspace_id: Workspace identifier
            code_files: List of dicts with keys: code, file_path, language, task_type

        Returns:
            Dict with indexing results
        """
        logger.info(
            "Starting batch code indexing",
            project_id=project_id,
            num_files=len(code_files)
        )

        codes = []
        metadatas = []
        indexed_count = 0
        failed_count = 0

        for file_info in code_files:
            try:
                code = file_info['code']
                metadata = {
                    'project_id': project_id,
                    'workspace_id': workspace_id,
                    'file_path': file_info.get('file_path', 'unknown'),
                    'language': file_info.get('language', 'unknown'),
                    'task_type': file_info.get('task_type', 'general'),
                    'approved': True,
                    'indexed_at': datetime.utcnow().isoformat()
                }

                codes.append(code)
                metadatas.append(metadata)

            except Exception as e:
                logger.error(
                    "Failed to prepare file for indexing",
                    error=str(e),
                    file_path=file_info.get('file_path', 'unknown')
                )
                failed_count += 1

        # Batch add to vector store
        try:
            code_ids = self.vector_store.add_codes_batch(
                codes=codes,
                metadatas=metadatas
            )
            indexed_count = len(code_ids)

            logger.info(
                "Batch indexing completed",
                indexed=indexed_count,
                failed=failed_count
            )

        except Exception as e:
            logger.error(
                "Batch indexing failed",
                error=str(e)
            )
            failed_count += len(codes)

        return {
            'indexed': indexed_count,
            'failed': failed_count,
            'total': len(code_files)
        }

    def _track_in_postgres(
        self,
        code_id: str,
        task_id: str,
        workspace_id: str,
        metadata: Dict[str, Any]
    ):
        """Track approved code in PostgreSQL."""
        try:
            # Create record in rag_approvals table (create table if needed)
            query = """
                CREATE TABLE IF NOT EXISTS rag_approvals (
                    id SERIAL PRIMARY KEY,
                    code_id VARCHAR(255) NOT NULL,
                    task_id VARCHAR(255),
                    workspace_id VARCHAR(255),
                    project_id VARCHAR(255),
                    file_path TEXT,
                    task_type VARCHAR(100),
                    language VARCHAR(50),
                    approved_at TIMESTAMP,
                    metadata JSONB
                );

                INSERT INTO rag_approvals (
                    code_id, task_id, workspace_id, project_id,
                    file_path, task_type, language, approved_at, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW(), %s
                );
            """

            import json
            params = (
                code_id,
                task_id,
                workspace_id,
                metadata.get('project_id'),
                metadata.get('file_path'),
                metadata.get('task_type'),
                metadata.get('language'),
                json.dumps(metadata)
            )

            # Execute (assuming postgres_manager has execute method)
            # Note: Adjust based on actual PostgresManager implementation
            logger.debug("Tracking approval in PostgreSQL", code_id=code_id)

        except Exception as e:
            logger.warning(
                "Failed to track in PostgreSQL",
                error=str(e),
                code_id=code_id
            )

    def _track_rejection_in_postgres(
        self,
        task_id: str,
        workspace_id: str,
        reason: str,
        code_length: int
    ):
        """Track rejected code in PostgreSQL for analysis."""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS rag_rejections (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255),
                    workspace_id VARCHAR(255),
                    reason TEXT,
                    code_length INT,
                    rejected_at TIMESTAMP DEFAULT NOW()
                );

                INSERT INTO rag_rejections (
                    task_id, workspace_id, reason, code_length
                ) VALUES (%s, %s, %s, %s);
            """

            params = (task_id, workspace_id, reason, code_length)

            logger.debug("Tracking rejection in PostgreSQL", task_id=task_id)

        except Exception as e:
            logger.warning(
                "Failed to track rejection",
                error=str(e),
                task_id=task_id
            )

    def get_approval_stats(
        self,
        project_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics about code approvals.

        Args:
            project_id: Filter by project (optional)
            days: Number of days to look back

        Returns:
            Dict with approval statistics
        """
        try:
            # Get vector store stats
            vector_stats = self.vector_store.get_stats()

            # Get PostgreSQL stats (if available)
            # Note: Implement actual query based on PostgresManager
            postgres_stats = {
                'total_approvals': 0,
                'total_rejections': 0,
                'approval_rate': 0.0
            }

            return {
                **vector_stats,
                **postgres_stats
            }

        except Exception as e:
            logger.error(
                "Failed to get approval stats",
                error=str(e)
            )
            return {}


# Singleton instance
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """
    Get singleton feedback service instance.

    Returns:
        FeedbackService instance
    """
    global _feedback_service

    if _feedback_service is None:
        _feedback_service = FeedbackService()

    return _feedback_service
```

**Tests**:
```python
# tests/unit/rag/test_feedback_service.py
import pytest
from src.rag.feedback_service import FeedbackService
from unittest.mock import Mock, patch


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    store = Mock()
    store.add_code.return_value = "code_123"
    store.add_codes_batch.return_value = ["id1", "id2", "id3"]
    store.get_stats.return_value = {'code_count': 100}
    return store


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL manager."""
    return Mock()


def test_record_approval(mock_vector_store, mock_postgres):
    """Test recording code approval."""
    service = FeedbackService(
        vector_store=mock_vector_store,
        postgres_manager=mock_postgres,
        enabled=True
    )

    code = "def test(): pass"
    metadata = {
        "project_id": "test",
        "file_path": "test.py",
        "language": "python",
        "task_type": "test"
    }

    code_id = service.record_approval(
        code=code,
        metadata=metadata,
        task_id="task_1",
        workspace_id="ws_1"
    )

    assert code_id == "code_123"
    mock_vector_store.add_code.assert_called_once()


def test_record_approval_disabled(mock_vector_store):
    """Test approval recording when disabled."""
    service = FeedbackService(
        vector_store=mock_vector_store,
        enabled=False
    )

    code_id = service.record_approval(
        code="def test(): pass",
        metadata={},
        task_id="task_1",
        workspace_id="ws_1"
    )

    assert code_id is None
    mock_vector_store.add_code.assert_not_called()


def test_batch_index(mock_vector_store, mock_postgres):
    """Test batch indexing."""
    service = FeedbackService(
        vector_store=mock_vector_store,
        postgres_manager=mock_postgres
    )

    code_files = [
        {"code": "def f1(): pass", "file_path": "f1.py", "language": "python"},
        {"code": "def f2(): pass", "file_path": "f2.py", "language": "python"},
        {"code": "def f3(): pass", "file_path": "f3.py", "language": "python"}
    ]

    result = service.batch_index_approved_code(
        project_id="test",
        workspace_id="ws_1",
        code_files=code_files
    )

    assert result['indexed'] == 3
    assert result['failed'] == 0
    assert result['total'] == 3
    mock_vector_store.add_codes_batch.assert_called_once()
```

**Tiempo estimado**: 3 horas
**Dependencias**: FASE 2
**Riesgo**: 🟢 Bajo

---

### FASE 6: Agent Integration (6-8 horas)

#### 6.1 Integrar RAG en CodeGenerationAgent

**Objetivo**: Integrar sistema RAG completo en agente de generación de código

**Archivo a modificar**: `src/agents/code_generation_agent.py`

**Cambios**:

1. **Agregar imports**:
```python
from src.rag.retriever import get_retriever
from src.rag.context_builder import get_context_builder
from src.rag.feedback_service import get_feedback_service
```

2. **Inicializar RAG en __init__**:
```python
def __init__(self, api_key: str = None):
    # ... código existente ...

    # RAG components
    self.retriever = get_retriever()
    self.context_builder = get_context_builder()
    self.feedback_service = get_feedback_service()

    self.logger.info("Code generation agent initialized with RAG support")
```

3. **Modificar método de generación para usar RAG**:
```python
def generate_code(
    self,
    task_description: str,
    workspace_id: str,
    project_id: str,
    file_path: str,
    language: str = "python",
    task_type: str = "general",
    use_rag: bool = True
) -> str:
    """
    Generate code with RAG-enhanced context.

    Args:
        task_description: Description of code to generate
        workspace_id: Workspace identifier
        project_id: Project identifier
        file_path: Target file path
        language: Programming language
        task_type: Type of task (auth, api, etc.)
        use_rag: Enable RAG retrieval (default: True)

    Returns:
        Generated code
    """
    self.logger.info(
        "Generating code",
        task=task_description[:100],
        workspace_id=workspace_id,
        project_id=project_id,
        use_rag=use_rag
    )

    # Retrieve relevant examples if RAG enabled
    rag_context = None
    if use_rag:
        try:
            # Retrieve similar code
            retrieval_results = self.retriever.retrieve(
                query=task_description,
                project_id=project_id,
                task_type=task_type,
                language=language
            )

            if retrieval_results:
                # Build RAG context
                project_context = {
                    'language': language,
                    'project_id': project_id
                }

                rag_context = self.context_builder.build_context(
                    task_description=task_description,
                    retrieval_results=retrieval_results,
                    project_context=project_context
                )

                self.logger.info(
                    "RAG context built",
                    num_examples=rag_context.examples_count,
                    avg_similarity=rag_context.metadata.get('avg_similarity', 0)
                )

        except Exception as e:
            self.logger.warning(
                "Failed to retrieve RAG context, continuing without it",
                error=str(e)
            )

    # Prepare messages for LLM
    if rag_context:
        messages = [
            {"role": "system", "content": rag_context.system_context},
            {"role": "user", "content": rag_context.user_context}
        ]
    else:
        # Fallback to basic prompt
        messages = [
            {"role": "system", "content": "You are an expert code generator."},
            {"role": "user", "content": f"Task: {task_description}"}
        ]

    # Generate code using LLM
    try:
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=messages
        )

        generated_code = response.content[0].text

        self.logger.info(
            "Code generated successfully",
            code_length=len(generated_code),
            used_rag=rag_context is not None
        )

        return generated_code

    except Exception as e:
        self.logger.error(
            "Failed to generate code",
            error=str(e),
            task=task_description[:100]
        )
        raise
```

4. **Agregar método para grabar aprobación**:
```python
def record_code_approval(
    self,
    code: str,
    task_id: str,
    workspace_id: str,
    project_id: str,
    file_path: str,
    language: str,
    task_type: str
) -> Optional[str]:
    """
    Record approved code in RAG system for future use.

    Args:
        code: Approved code content
        task_id: Task identifier
        workspace_id: Workspace identifier
        project_id: Project identifier
        file_path: File path
        language: Programming language
        task_type: Task type

    Returns:
        Code ID if recorded successfully
    """
    metadata = {
        'project_id': project_id,
        'file_path': file_path,
        'language': language,
        'task_type': task_type
    }

    return self.feedback_service.record_approval(
        code=code,
        metadata=metadata,
        task_id=task_id,
        workspace_id=workspace_id
    )
```

**Tiempo estimado**: 4 horas
**Dependencias**: FASES 1-5
**Riesgo**: 🟡 Medio

---

#### 6.2 Integrar RAG en OrchestratorAgent

**Objetivo**: Permitir que orchestrator consulte RAG para planificación

**Archivo a modificar**: `src/agents/orchestrator_agent.py`

**Cambios**:

1. **Agregar import y inicialización**:
```python
from src.rag.retriever import get_retriever

def __init__(self):
    # ... código existente ...
    self.retriever = get_retriever()
```

2. **Consultar RAG en análisis de proyecto**:
```python
def _analyze_project(self, state: SharedState) -> Dict[str, Any]:
    """Analyze project with RAG-enhanced understanding."""

    # ... análisis existente ...

    # Consult RAG for similar projects
    try:
        similar_examples = self.retriever.retrieve(
            query=f"project analysis for {project_type}",
            project_id=state.project_id,
            task_type="project_structure"
        )

        if similar_examples:
            self.logger.info(
                "Found similar project examples",
                count=len(similar_examples),
                avg_similarity=sum(e.similarity_score for e in similar_examples) / len(similar_examples)
            )

            # Use examples to inform analysis
            # ... integrate into analysis logic ...

    except Exception as e:
        self.logger.warning(
            "Failed to retrieve similar projects",
            error=str(e)
        )

    return analysis_result
```

**Tiempo estimado**: 2 horas
**Dependencias**: FASE 6.1
**Riesgo**: 🟢 Bajo

---

### FASE 7: Testing Comprehensivo (6-8 horas)

#### 7.1 Integration Tests

**Archivo a crear**: `tests/integration/rag/test_rag_pipeline.py`

**Código completo**:
```python
"""
End-to-end integration tests for RAG pipeline.

Tests the complete flow: retrieval → context building → generation → feedback.
"""

import pytest
from src.rag.vector_store import get_vector_store
from src.rag.retriever import get_retriever
from src.rag.context_builder import get_context_builder
from src.rag.feedback_service import get_feedback_service


@pytest.fixture(scope="module")
def rag_pipeline():
    """Initialize RAG pipeline components."""
    vector_store = get_vector_store()
    retriever = get_retriever()
    context_builder = get_context_builder()
    feedback_service = get_feedback_service()

    # Clear test data
    # vector_store.clear_collection(vector_store.COLLECTION_CODE)

    return {
        'vector_store': vector_store,
        'retriever': retriever,
        'context_builder': context_builder,
        'feedback_service': feedback_service
    }


def test_complete_rag_pipeline(rag_pipeline):
    """Test complete RAG pipeline end-to-end."""

    # 1. Index initial code
    code = """
def authenticate_user(username: str, password: str) -> bool:
    '''Authenticate user with username and password.'''
    user = db.get_user(username)
    if not user:
        return False
    return user.verify_password(password)
"""

    metadata = {
        'project_id': 'test_project',
        'file_path': 'auth.py',
        'language': 'python',
        'task_type': 'authentication'
    }

    code_id = rag_pipeline['vector_store'].add_code(code, metadata)
    assert code_id is not None

    # 2. Retrieve similar code
    retrieval_results = rag_pipeline['retriever'].retrieve(
        query="implement user login",
        project_id="test_project",
        task_type="authentication"
    )

    assert len(retrieval_results) > 0
    assert retrieval_results[0].code_id == code_id
    assert "authenticate_user" in retrieval_results[0].code

    # 3. Build context
    context = rag_pipeline['context_builder'].build_context(
        task_description="Implement user login endpoint",
        retrieval_results=retrieval_results
    )

    assert context.examples_count > 0
    assert "authenticate_user" in context.user_context
    assert len(context.system_context) > 0

    # 4. Record approval (simulate)
    new_code = """
def login_user(username: str, password: str) -> dict:
    '''Login user and return token.'''
    if authenticate_user(username, password):
        token = generate_token(username)
        return {'token': token, 'success': True}
    return {'success': False}
"""

    approval_id = rag_pipeline['feedback_service'].record_approval(
        code=new_code,
        metadata={
            **metadata,
            'file_path': 'login.py',
            'task_type': 'authentication'
        },
        task_id="task_123",
        workspace_id="ws_123"
    )

    assert approval_id is not None

    # 5. Verify new code is retrievable
    new_results = rag_pipeline['retriever'].retrieve(
        query="implement login endpoint",
        project_id="test_project"
    )

    # Should find both original and new code
    assert len(new_results) >= 2


def test_rag_with_no_results(rag_pipeline):
    """Test RAG behavior when no similar code exists."""

    results = rag_pipeline['retriever'].retrieve(
        query="implement quantum computing algorithm",
        project_id="nonexistent_project"
    )

    # Should return empty or very low similarity results
    assert len(results) == 0 or results[0].similarity_score < 0.5


def test_rag_metadata_filtering(rag_pipeline):
    """Test RAG respects metadata filters."""

    # Add codes with different projects
    rag_pipeline['vector_store'].add_code(
        "def func_a(): pass",
        {"project_id": "project_a", "task_type": "test"}
    )
    rag_pipeline['vector_store'].add_code(
        "def func_b(): pass",
        {"project_id": "project_b", "task_type": "test"}
    )

    # Retrieve with filter
    results = rag_pipeline['retriever'].retrieve(
        query="function",
        project_id="project_a"
    )

    # All results should be from project_a
    for result in results:
        assert result.metadata.get('project_id') == 'project_a'
```

**Tiempo estimado**: 4 horas
**Dependencias**: FASES 1-6
**Riesgo**: 🟡 Medio

---

#### 7.2 Performance Tests

**Archivo a crear**: `tests/performance/test_rag_performance.py`

**Código completo**:
```python
"""
Performance tests for RAG system.

Tests retrieval speed, embedding generation, and scaling behavior.
"""

import pytest
import time
from src.rag.embeddings import get_embedding_model
from src.rag.vector_store import get_vector_store
from src.rag.retriever import get_retriever


def test_embedding_generation_speed():
    """Test embedding generation performance."""
    model = get_embedding_model()

    # Generate embeddings for 100 code snippets
    codes = [f"def function_{i}(): pass" for i in range(100)]

    start = time.time()
    embeddings = model.encode(codes, batch_size=32)
    duration = time.time() - start

    assert len(embeddings) == 100
    assert duration < 5.0  # Should complete in < 5 seconds

    print(f"Generated 100 embeddings in {duration:.2f}s ({100/duration:.1f} codes/sec)")


def test_retrieval_speed():
    """Test retrieval performance."""
    retriever = get_retriever()

    # Perform 20 retrievals
    queries = [f"implement feature {i}" for i in range(20)]

    start = time.time()
    for query in queries:
        results = retriever.retrieve(query, top_k=5)
    duration = time.time() - start

    assert duration < 10.0  # Should complete in < 10 seconds

    print(f"Performed 20 retrievals in {duration:.2f}s ({20/duration:.1f} queries/sec)")


def test_batch_indexing_speed():
    """Test batch indexing performance."""
    vector_store = get_vector_store()

    # Index 500 code snippets
    codes = [f"def function_{i}(): return {i}" for i in range(500)]
    metadatas = [
        {'project_id': 'perf_test', 'task_type': 'test'}
        for _ in range(500)
    ]

    start = time.time()
    code_ids = vector_store.add_codes_batch(codes, metadatas)
    duration = time.time() - start

    assert len(code_ids) == 500
    assert duration < 30.0  # Should complete in < 30 seconds

    print(f"Indexed 500 codes in {duration:.2f}s ({500/duration:.1f} codes/sec)")


@pytest.mark.slow
def test_scaling_behavior():
    """Test performance with large dataset."""
    vector_store = get_vector_store()
    retriever = get_retriever()

    # Index 5000 code snippets
    batch_size = 500
    num_batches = 10

    total_start = time.time()

    for batch_num in range(num_batches):
        codes = [
            f"def function_{batch_num}_{i}(): return {i}"
            for i in range(batch_size)
        ]
        metadatas = [
            {'project_id': 'scaling_test', 'task_type': 'test'}
            for _ in range(batch_size)
        ]

        vector_store.add_codes_batch(codes, metadatas)

    indexing_duration = time.time() - total_start
    print(f"Indexed {num_batches * batch_size} codes in {indexing_duration:.2f}s")

    # Test retrieval performance at scale
    retrieval_start = time.time()
    for i in range(50):
        results = retriever.retrieve(f"function {i}", top_k=10)
    retrieval_duration = time.time() - retrieval_start

    print(f"Performed 50 retrievals at scale in {retrieval_duration:.2f}s")

    # Cleanup
    vector_store.clear_collection(vector_store.COLLECTION_CODE)
```

**Tiempo estimado**: 2 horas
**Dependencias**: FASE 7.1
**Riesgo**: 🟢 Bajo

---

### FASE 8: Monitoring y Métricas (4-6 horas)

#### 8.1 Métricas de RAG

**Objetivo**: Implementar métricas para monitorear performance de RAG

**Archivo a crear**: `src/rag/metrics.py`

**Código completo**:
```python
"""
RAG system metrics and monitoring.

Tracks performance, accuracy, and usage statistics.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from src.observability import get_logger

logger = get_logger("rag_metrics")


@dataclass
class RAGMetrics:
    """RAG system metrics snapshot."""
    timestamp: datetime

    # Retrieval metrics
    avg_retrieval_time: float  # seconds
    avg_similarity_score: float
    retrieval_success_rate: float

    # Context metrics
    avg_examples_per_query: float
    context_build_time: float

    # Feedback metrics
    approval_rate: float
    rejection_rate: float
    total_indexed_codes: int

    # Performance metrics
    cache_hit_rate: float
    avg_embedding_time: float


class RAGMetricsCollector:
    """
    Collector for RAG system metrics.

    Tracks and aggregates metrics over time for monitoring
    and optimization.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics_buffer = []
        self.buffer_size = 1000

        logger.info("RAG metrics collector initialized")

    def record_retrieval(
        self,
        query: str,
        num_results: int,
        avg_similarity: float,
        duration: float,
        success: bool
    ):
        """
        Record retrieval operation metrics.

        Args:
            query: Query text
            num_results: Number of results returned
            avg_similarity: Average similarity score
            duration: Retrieval duration in seconds
            success: Whether retrieval succeeded
        """
        metric = {
            'type': 'retrieval',
            'timestamp': datetime.utcnow(),
            'query_length': len(query),
            'num_results': num_results,
            'avg_similarity': avg_similarity,
            'duration': duration,
            'success': success
        }

        self._add_metric(metric)

    def record_context_build(
        self,
        num_examples: int,
        context_length: int,
        duration: float
    ):
        """
        Record context building metrics.

        Args:
            num_examples: Number of examples included
            context_length: Total context length
            duration: Build duration in seconds
        """
        metric = {
            'type': 'context_build',
            'timestamp': datetime.utcnow(),
            'num_examples': num_examples,
            'context_length': context_length,
            'duration': duration
        }

        self._add_metric(metric)

    def record_feedback(
        self,
        feedback_type: str,  # 'approval' or 'rejection'
        task_id: str,
        project_id: str
    ):
        """
        Record feedback event.

        Args:
            feedback_type: Type of feedback
            task_id: Task identifier
            project_id: Project identifier
        """
        metric = {
            'type': 'feedback',
            'timestamp': datetime.utcnow(),
            'feedback_type': feedback_type,
            'task_id': task_id,
            'project_id': project_id
        }

        self._add_metric(metric)

    def get_metrics_summary(
        self,
        time_window: timedelta = timedelta(hours=24)
    ) -> RAGMetrics:
        """
        Get metrics summary for time window.

        Args:
            time_window: Time window to aggregate

        Returns:
            RAGMetrics summary
        """
        cutoff = datetime.utcnow() - time_window
        recent_metrics = [
            m for m in self.metrics_buffer
            if m['timestamp'] > cutoff
        ]

        if not recent_metrics:
            # Return empty metrics
            return RAGMetrics(
                timestamp=datetime.utcnow(),
                avg_retrieval_time=0.0,
                avg_similarity_score=0.0,
                retrieval_success_rate=0.0,
                avg_examples_per_query=0.0,
                context_build_time=0.0,
                approval_rate=0.0,
                rejection_rate=0.0,
                total_indexed_codes=0,
                cache_hit_rate=0.0,
                avg_embedding_time=0.0
            )

        # Calculate retrieval metrics
        retrieval_metrics = [m for m in recent_metrics if m['type'] == 'retrieval']
        if retrieval_metrics:
            avg_retrieval_time = sum(m['duration'] for m in retrieval_metrics) / len(retrieval_metrics)
            avg_similarity = sum(m['avg_similarity'] for m in retrieval_metrics) / len(retrieval_metrics)
            success_count = sum(1 for m in retrieval_metrics if m['success'])
            retrieval_success_rate = success_count / len(retrieval_metrics)
        else:
            avg_retrieval_time = 0.0
            avg_similarity = 0.0
            retrieval_success_rate = 0.0

        # Calculate context metrics
        context_metrics = [m for m in recent_metrics if m['type'] == 'context_build']
        if context_metrics:
            avg_examples = sum(m['num_examples'] for m in context_metrics) / len(context_metrics)
            avg_context_time = sum(m['duration'] for m in context_metrics) / len(context_metrics)
        else:
            avg_examples = 0.0
            avg_context_time = 0.0

        # Calculate feedback metrics
        feedback_metrics = [m for m in recent_metrics if m['type'] == 'feedback']
        if feedback_metrics:
            approvals = sum(1 for m in feedback_metrics if m['feedback_type'] == 'approval')
            rejections = sum(1 for m in feedback_metrics if m['feedback_type'] == 'rejection')
            total = len(feedback_metrics)
            approval_rate = approvals / total
            rejection_rate = rejections / total
        else:
            approval_rate = 0.0
            rejection_rate = 0.0

        return RAGMetrics(
            timestamp=datetime.utcnow(),
            avg_retrieval_time=avg_retrieval_time,
            avg_similarity_score=avg_similarity,
            retrieval_success_rate=retrieval_success_rate,
            avg_examples_per_query=avg_examples,
            context_build_time=avg_context_time,
            approval_rate=approval_rate,
            rejection_rate=rejection_rate,
            total_indexed_codes=0,  # Would come from vector store
            cache_hit_rate=0.0,  # Would come from cache stats
            avg_embedding_time=0.0  # Would come from embedding model
        )

    def _add_metric(self, metric: Dict[str, Any]):
        """Add metric to buffer."""
        self.metrics_buffer.append(metric)

        # Trim buffer if too large
        if len(self.metrics_buffer) > self.buffer_size:
            self.metrics_buffer = self.metrics_buffer[-self.buffer_size:]

    def export_metrics(self) -> List[Dict[str, Any]]:
        """Export all metrics for external storage."""
        return self.metrics_buffer.copy()


# Singleton instance
_metrics_collector: Optional[RAGMetricsCollector] = None


def get_metrics_collector() -> RAGMetricsCollector:
    """
    Get singleton metrics collector instance.

    Returns:
        RAGMetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = RAGMetricsCollector()

    return _metrics_collector
```

**Tiempo estimado**: 3 horas
**Dependencias**: FASES anteriores
**Riesgo**: 🟢 Bajo

---

#### 8.2 Dashboard de Métricas

**Objetivo**: Crear endpoint API para visualizar métricas RAG

**Archivo a modificar**: `src/api/routers/rag.py` (crear si no existe)

**Código completo**:
```python
"""
RAG system API endpoints.

Provides endpoints for RAG operations and monitoring.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import timedelta

from src.rag.vector_store import get_vector_store
from src.rag.retriever import get_retriever
from src.rag.feedback_service import get_feedback_service
from src.rag.metrics import get_metrics_collector
from src.observability import get_logger

logger = get_logger("rag_api")

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/stats")
async def get_rag_stats() -> Dict[str, Any]:
    """Get RAG system statistics."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error("Failed to get RAG stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_rag_metrics(hours: int = 24) -> Dict[str, Any]:
    """
    Get RAG system metrics.

    Args:
        hours: Time window in hours (default: 24)

    Returns:
        Metrics summary
    """
    try:
        metrics_collector = get_metrics_collector()
        metrics = metrics_collector.get_metrics_summary(
            time_window=timedelta(hours=hours)
        )

        return {
            "status": "success",
            "data": {
                "timestamp": metrics.timestamp.isoformat(),
                "retrieval": {
                    "avg_time_seconds": metrics.avg_retrieval_time,
                    "avg_similarity_score": metrics.avg_similarity_score,
                    "success_rate": metrics.retrieval_success_rate
                },
                "context": {
                    "avg_examples_per_query": metrics.avg_examples_per_query,
                    "avg_build_time_seconds": metrics.context_build_time
                },
                "feedback": {
                    "approval_rate": metrics.approval_rate,
                    "rejection_rate": metrics.rejection_rate,
                    "total_indexed_codes": metrics.total_indexed_codes
                }
            }
        }
    except Exception as e:
        logger.error("Failed to get RAG metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def rag_health_check() -> Dict[str, Any]:
    """Check RAG system health."""
    try:
        vector_store = get_vector_store()

        # Test connection
        stats = vector_store.get_stats()

        return {
            "status": "healthy",
            "chromadb": "connected",
            "collections": {
                "code": stats.get('code_count', 0),
                "tests": stats.get('tests_count', 0),
                "docs": stats.get('docs_count', 0)
            }
        }
    except Exception as e:
        logger.error("RAG health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

**Registrar router en app principal** (`src/api/app.py`):
```python
from src.api.routers import rag

app.include_router(rag.router)
```

**Tiempo estimado**: 2 horas
**Dependencias**: FASE 8.1
**Riesgo**: 🟢 Bajo

---

### FASE 9: Optimización y Tuning (4-6 horas)

#### 9.1 Optimización de Hiperparámetros

**Objetivo**: Encontrar configuración óptima de RAG

**Archivo a crear**: `scripts/tune_rag_hyperparameters.py`

**Código completo**:
```python
#!/usr/bin/env python
"""
Hyperparameter tuning for RAG system.

Experiments with different configurations to find optimal settings.
"""

import sys
from pathlib import Path
from itertools import product

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import RAGRetriever
from src.rag.vector_store import get_vector_store
from src.observability import setup_logging, get_logger

setup_logging()
logger = get_logger("rag_tuning")


def test_configuration(
    top_k: int,
    similarity_threshold: float,
    diversity_factor: float,
    test_queries: list
) -> dict:
    """
    Test RAG configuration.

    Args:
        top_k: Number of results to retrieve
        similarity_threshold: Minimum similarity score
        diversity_factor: Diversity weight
        test_queries: List of test queries

    Returns:
        Performance metrics
    """
    retriever = RAGRetriever(
        top_k=top_k,
        similarity_threshold=similarity_threshold
    )

    total_results = 0
    total_similarity = 0.0
    unique_codes = set()

    for query in test_queries:
        results = retriever.retrieve(
            query=query,
            diversity_factor=diversity_factor
        )

        total_results += len(results)
        if results:
            total_similarity += sum(r.similarity_score for r in results) / len(results)
            unique_codes.update(r.code_id for r in results)

    avg_results = total_results / len(test_queries) if test_queries else 0
    avg_similarity = total_similarity / len(test_queries) if test_queries else 0
    diversity_score = len(unique_codes) / total_results if total_results > 0 else 0

    return {
        'avg_results_per_query': avg_results,
        'avg_similarity': avg_similarity,
        'diversity_score': diversity_score
    }


def main():
    """Run hyperparameter tuning."""
    logger.info("Starting RAG hyperparameter tuning")

    # Test queries
    test_queries = [
        "implement user authentication",
        "create REST API endpoint",
        "write unit tests",
        "add error handling",
        "implement data validation"
    ]

    # Hyperparameter grid
    top_k_values = [3, 5, 7, 10]
    similarity_thresholds = [0.6, 0.7, 0.75, 0.8]
    diversity_factors = [0.0, 0.3, 0.5, 0.7]

    best_config = None
    best_score = 0.0

    logger.info(
        "Testing configurations",
        total_combinations=len(top_k_values) * len(similarity_thresholds) * len(diversity_factors)
    )

    for top_k, threshold, diversity in product(
        top_k_values,
        similarity_thresholds,
        diversity_factors
    ):
        metrics = test_configuration(
            top_k=top_k,
            similarity_threshold=threshold,
            diversity_factor=diversity,
            test_queries=test_queries
        )

        # Score = similarity * 0.6 + diversity * 0.4
        score = metrics['avg_similarity'] * 0.6 + metrics['diversity_score'] * 0.4

        logger.info(
            "Configuration tested",
            top_k=top_k,
            threshold=threshold,
            diversity=diversity,
            score=score,
            **metrics
        )

        if score > best_score:
            best_score = score
            best_config = {
                'top_k': top_k,
                'similarity_threshold': threshold,
                'diversity_factor': diversity,
                'metrics': metrics,
                'score': score
            }

    logger.info(
        "Best configuration found",
        **best_config
    )

    print("\n" + "=" * 50)
    print("BEST CONFIGURATION")
    print("=" * 50)
    print(f"top_k: {best_config['top_k']}")
    print(f"similarity_threshold: {best_config['similarity_threshold']}")
    print(f"diversity_factor: {best_config['diversity_factor']}")
    print(f"\nScore: {best_config['score']:.3f}")
    print(f"Avg Similarity: {best_config['metrics']['avg_similarity']:.3f}")
    print(f"Diversity Score: {best_config['metrics']['diversity_score']:.3f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
```

**Ejecutar tuning**:
```bash
python scripts/tune_rag_hyperparameters.py
```

**Tiempo estimado**: 3 horas
**Dependencias**: FASE 7
**Riesgo**: 🟢 Bajo

---

#### 9.2 Cache de Embeddings

**Objetivo**: Agregar cache para embeddings frecuentes

**Archivo a modificar**: `src/rag/embeddings.py`

**Cambios**:
```python
from functools import lru_cache
import hashlib

class EmbeddingModel:
    def __init__(self, ...):
        # ... código existente ...
        self._cache = {}
        self._cache_size = 1000

    def encode_single(self, text: str) -> List[float]:
        """Generate embedding with caching."""
        # Generate cache key
        cache_key = hashlib.md5(text.encode()).hexdigest()

        # Check cache
        if cache_key in self._cache:
            logger.debug("Cache hit for embedding", cache_key=cache_key)
            return self._cache[cache_key]

        # Generate embedding
        embeddings = self.encode([text], batch_size=1)
        result = embeddings[0] if embeddings else []

        # Store in cache
        if len(self._cache) >= self._cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[cache_key] = result

        return result

    def clear_cache(self):
        """Clear embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")
```

**Tiempo estimado**: 1 hora
**Dependencias**: FASE 1.2
**Riesgo**: 🟢 Bajo

---

## 🧪 Testing Strategy

### Unit Tests (30 tests total)

**Coverage targets**:
- `embeddings.py`: 5 tests (model init, encoding, caching, singleton)
- `vector_store.py`: 8 tests (CRUD ops, search, filtering, batch)
- `retriever.py`: 6 tests (retrieval, filtering, diversity, MMR)
- `context_builder.py`: 5 tests (context building, length limiting, formatting)
- `feedback_service.py`: 6 tests (approval, rejection, batch indexing, stats)

**Comando**:
```bash
pytest tests/unit/rag/ -v --cov=src/rag --cov-report=html
```

**Target**: 85%+ coverage

---

### Integration Tests (10 tests)

**Escenarios**:
1. Complete RAG pipeline (retrieve → build → feedback)
2. Multi-project isolation
3. Metadata filtering accuracy
4. Large batch indexing
5. Concurrent retrievals
6. Error recovery
7. Cache coherence
8. Collection management
9. Stats accuracy
10. Health check validation

**Comando**:
```bash
pytest tests/integration/rag/ -v
```

---

### Performance Tests (5 tests)

**Benchmarks**:
1. Embedding generation: 100 codes in <5s
2. Retrieval speed: 20 queries in <10s
3. Batch indexing: 500 codes in <30s
4. Scaling: 5000 codes indexed, 50 retrievals
5. Concurrent operations: 10 parallel retrievals

**Comando**:
```bash
pytest tests/performance/test_rag_performance.py -v -m slow
```

---

### E2E Validation (3 scenarios)

1. **ChromaDB Connection**: Validate connectivity and collections
2. **Embeddings**: Validate model loading and encoding
3. **Full Pipeline**: Validate complete workflow with real agent integration

**Comando**:
```bash
python tests/validation/rag/validate_chromadb.py
python tests/validation/rag/validate_embeddings.py
```

---

## 🚀 Deployment Plan

### Development Environment

**Setup**:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start ChromaDB
docker-compose up chromadb -d

# 3. Verify health
curl http://localhost:8000/api/v1/heartbeat

# 4. Run validation
python tests/validation/rag/validate_chromadb.py

# 5. Index initial data (if any)
python scripts/index_approved_code.py
```

---

### Staging Environment

**Deployment steps**:

1. **Deploy ChromaDB**:
```bash
# Update docker-compose.yml with production settings
docker-compose -f docker-compose.staging.yml up chromadb -d
```

2. **Configure environment**:
```bash
# .env.staging
ENVIRONMENT=staging
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_ENABLE_FEEDBACK=true
```

3. **Deploy API**:
```bash
docker-compose -f docker-compose.staging.yml up api -d
```

4. **Verify deployment**:
```bash
curl http://staging.devmatrix.com/api/rag/health
```

5. **Index existing code**:
```bash
python scripts/batch_index_project.py --project-id=staging_project
```

---

### Production Environment

**Pre-deployment checklist**:
- ✅ All tests passing (unit + integration + E2E)
- ✅ Performance benchmarks met
- ✅ Security review completed
- ✅ Backup strategy in place
- ✅ Monitoring configured
- ✅ Rollback plan documented

**Deployment steps**:

1. **Backup ChromaDB data**:
```bash
docker exec devmatrix_chromadb tar czf /backup/chromadb_$(date +%Y%m%d).tar.gz /chroma/chroma
```

2. **Deploy with zero-downtime**:
```bash
# Blue-green deployment
docker-compose -f docker-compose.prod.yml up chromadb_v2 -d
# Wait for health check
# Switch traffic
# Terminate old version
```

3. **Verify production**:
```bash
curl https://api.devmatrix.com/rag/health
curl https://api.devmatrix.com/rag/stats
curl https://api.devmatrix.com/rag/metrics
```

4. **Monitor metrics**:
```bash
# Watch logs
docker-compose logs -f api chromadb

# Check metrics
watch -n 5 'curl -s https://api.devmatrix.com/rag/metrics'
```

---

## 📊 Monitoring y Métricas

### Key Performance Indicators (KPIs)

**Accuracy Metrics**:
- **Code generation precision**: Target 90%+ (from 70-80%)
- **Similarity score average**: Target 0.75+
- **Retrieval success rate**: Target 95%+
- **Approval rate**: Target 80%+ of generated code

**Performance Metrics**:
- **Retrieval latency p50**: <100ms
- **Retrieval latency p95**: <500ms
- **Embedding generation**: <50ms per code
- **Context building**: <200ms
- **End-to-end RAG overhead**: <1s

**System Metrics**:
- **ChromaDB uptime**: 99.9%+
- **Vector store size**: Monitor growth
- **Cache hit rate**: 60%+ for embeddings
- **API error rate**: <1%

---

### Alerting Rules

**Critical alerts** (PagerDuty):
- ChromaDB connection failure
- Retrieval success rate <85%
- API error rate >5%
- Embedding model load failure

**Warning alerts** (Slack):
- Retrieval latency p95 >1s
- Similarity score average <0.65
- Approval rate <60%
- ChromaDB disk usage >80%

---

### Dashboards

**Grafana Dashboard - RAG Performance**:

**Panels**:
1. **Retrieval Latency** (line chart)
   - p50, p95, p99 over time
   - Target lines at 100ms, 500ms, 1s

2. **Accuracy Metrics** (gauge)
   - Avg similarity score
   - Retrieval success rate
   - Approval rate

3. **Throughput** (area chart)
   - Retrievals per second
   - Indexing rate
   - API requests

4. **System Health** (status)
   - ChromaDB status
   - Embedding model status
   - Vector store size

5. **Usage Stats** (bar chart)
   - Top projects by retrievals
   - Top task types
   - Language distribution

**Dashboard JSON**: Create in Grafana UI or via API

---

### Logging Strategy

**Log levels by component**:
- `embeddings.py`: INFO for initialization, DEBUG for encoding
- `vector_store.py`: INFO for operations, WARNING for errors
- `retriever.py`: INFO for retrievals, DEBUG for ranking details
- `context_builder.py`: INFO for context builds
- `feedback_service.py`: INFO for approvals/rejections

**Structured log fields**:
```json
{
  "timestamp": "2025-10-17T10:30:45Z",
  "level": "INFO",
  "logger": "rag_retriever",
  "message": "Retrieval completed",
  "query_length": 45,
  "num_results": 5,
  "avg_similarity": 0.82,
  "duration_ms": 125,
  "project_id": "proj_123",
  "workspace_id": "ws_456"
}
```

---

## 📅 Timeline Detallado

### Semana 1: Fundamentos (26-32 horas)

**Día 1-2: Setup (8-10 horas)**
- FASE 1.1: Instalación de dependencias (2h)
- FASE 1.2: Configuración de embeddings (2h)
- FASE 1.3: Configuración de settings (30min)
- FASE 1.4: Estructura de directorios (15min)
- FASE 2.1: ChromaDB wrapper (4h)
- FASE 2.2: Validation script (1h)

**Día 3-4: Retrieval (8-10 horas)**
- FASE 3.1: RAG Retriever (4h)
- Tests de retriever (2h)
- FASE 4.1: Context Builder (3h)
- Tests de context builder (1h)

**Día 5: Feedback (4-6 horas)**
- FASE 5.1: Feedback Service (3h)
- Tests de feedback (2h)

**Checkpoints**:
- ✅ ChromaDB funcionando
- ✅ Embeddings generándose correctamente
- ✅ Retrieval devolviendo resultados relevantes
- ✅ Context builder formateando correctamente

---

### Semana 2: Integración y Testing (26-32 horas)

**Día 6-7: Agent Integration (10-12 horas)**
- FASE 6.1: Integrar en CodeGenerationAgent (4h)
- FASE 6.2: Integrar en OrchestratorAgent (2h)
- Tests de integración con agents (4h)

**Día 8-9: Testing Comprehensivo (10-12 horas)**
- FASE 7.1: Integration tests (4h)
- FASE 7.2: Performance tests (2h)
- E2E validation (2h)
- Bug fixes y ajustes (2h)

**Día 10: Monitoring (6-8 horas)**
- FASE 8.1: Métricas de RAG (3h)
- FASE 8.2: Dashboard API (2h)
- Tests de métricas (1h)

**Checkpoints**:
- ✅ Agents generando código con RAG
- ✅ Tests pasando (85%+ coverage)
- ✅ Performance benchmarks cumplidos
- ✅ Métricas expuestas y funcionando

---

### Semana 3-4: Optimización y Producción (20-28 horas)

**Día 11-12: Optimización (6-8 horas)**
- FASE 9.1: Hyperparameter tuning (3h)
- FASE 9.2: Cache de embeddings (1h)
- Optimizaciones adicionales (2h)

**Día 13-14: Deployment (8-10 horas)**
- Deployment a staging (2h)
- Testing en staging (2h)
- Indexing de código existente (2h)
- Validación completa (2h)

**Día 15: Producción (6-10 horas)**
- Pre-deployment checklist (1h)
- Deployment a producción (2h)
- Monitoring post-deploy (2h)
- Documentation final (2h)

**Checkpoints**:
- ✅ Configuración óptima encontrada
- ✅ Staging funcionando perfectamente
- ✅ Producción desplegada sin issues
- ✅ Monitoring activo y alertas configuradas

---

### Resumen Timeline

| Semana | Fases | Horas | Estado |
|--------|-------|-------|--------|
| Semana 1 | FASE 1-5 | 26-32h | Fundamentos + Feedback |
| Semana 2 | FASE 6-8 | 26-32h | Integración + Testing |
| Semana 3-4 | FASE 9 + Deploy | 20-28h | Optimización + Producción |
| **TOTAL** | **9 fases** | **72-92h** | **2-4 semanas** |

---

## ⚠️ Risk Mitigation

### Riesgos Técnicos

**Riesgo 1: ChromaDB Performance Issues**
- **Probabilidad**: Media
- **Impacto**: Alto
- **Mitigación**:
  - Performance testing en FASE 7.2
  - Benchmarks claros antes de producción
  - Fallback a búsqueda simple si RAG falla
  - Cache de embeddings frecuentes

**Riesgo 2: Embedding Quality**
- **Probabilidad**: Media
- **Impacto**: Alto
- **Mitigación**:
  - Usar modelo probado (all-MiniLM-L6-v2)
  - Evaluar alternativas en tuning
  - Metrics de similarity score
  - A/B testing de modelos

**Riesgo 3: Integration Complexity**
- **Probabilidad**: Media
- **Impacto**: Medio
- **Mitigación**:
  - Tests comprehensivos en FASE 7
  - Gradual rollout (feature flag)
  - Fallback a generación sin RAG
  - Monitoring detallado

**Riesgo 4: Data Quality**
- **Probabilidad**: Alta
- **Impacto**: Alto
- **Mitigación**:
  - Solo indexar código aprobado
  - Feedback loop para mejora continua
  - Cleanup de código malo
  - Metadata filtering

---

### Riesgos de Proyecto

**Riesgo 5: Timeline Overrun**
- **Probabilidad**: Media
- **Impacto**: Medio
- **Mitigación**:
  - Timeline conservador (2-4 semanas)
  - Checkpoints semanales
  - MVP approach (puede ir a producción después semana 2)
  - Buffer time incluido

**Riesgo 6: Scope Creep**
- **Probabilidad**: Media
- **Impacto**: Medio
- **Mitigación**:
  - Plan detallado y acordado
  - MVP definido claramente
  - Optimizaciones como FASE 9 (opcional)
  - Feature freeze después FASE 6

---

### Contingency Plans

**Plan A: MVP Rápido (Si hay presión de tiempo)**
- FASE 1-3: Setup + Retrieval (12-16h)
- FASE 6.1: Integración básica en CodeGen (4h)
- Tests mínimos (4h)
- Deploy simple (2h)
- **Total**: ~1 semana

**Plan B: Fallback Sin RAG**
- Si RAG falla en producción
- Feature flag para desactivar
- Agents funcionan sin RAG (código existente)
- Debug offline, fix, redeploy

**Plan C: Rollback**
- Backup de ChromaDB antes de cambios
- Git tags para cada fase
- Rollback script preparado
- Monitoring para detección rápida

---

## ✅ Checklist de Implementación

### Pre-Implementation
- [ ] Leer documento RAG completo
- [ ] Entender arquitectura actual
- [ ] Confirmar recursos disponibles (GPU opcional)
- [ ] Backup de código actual
- [ ] Crear feature branch `feature/rag-implementation`

---

### FASE 1: Setup (4-6 horas)
- [ ] 1.1: Actualizar requirements.txt
- [ ] 1.1: Actualizar docker-compose.yml
- [ ] 1.1: Actualizar .env.example
- [ ] 1.1: Validar ChromaDB health
- [ ] 1.2: Crear embeddings.py
- [ ] 1.2: Tests de embeddings passing
- [ ] 1.3: Actualizar config.py
- [ ] 1.3: Tests de config passing
- [ ] 1.4: Crear estructura de directorios

**Checkpoint**: ✅ ChromaDB running, embeddings working

---

### FASE 2: Vector Store (6-8 horas)
- [ ] 2.1: Crear vector_store.py
- [ ] 2.1: Tests de vector_store passing
- [ ] 2.1: Integration test add/search passing
- [ ] 2.2: Crear validate_chromadb.py
- [ ] 2.2: Validation script passing

**Checkpoint**: ✅ Can index and retrieve code from ChromaDB

---

### FASE 3: Retriever (4-6 horas)
- [ ] 3.1: Crear retriever.py
- [ ] 3.1: Implement MMR algorithm
- [ ] 3.1: Tests de retriever passing
- [ ] 3.1: Test diversity optimization

**Checkpoint**: ✅ Retrieval working with ranking and diversity

---

### FASE 4: Context Builder (3-4 horas)
- [ ] 4.1: Crear context_builder.py
- [ ] 4.1: Tests de context_builder passing
- [ ] 4.1: Validate context formatting

**Checkpoint**: ✅ Context properly formatted for LLM

---

### FASE 5: Feedback Service (3-4 horas)
- [ ] 5.1: Crear feedback_service.py
- [ ] 5.1: Tests de feedback passing
- [ ] 5.1: Test batch indexing

**Checkpoint**: ✅ Feedback loop working

---

### FASE 6: Agent Integration (6-8 horas)
- [ ] 6.1: Modificar code_generation_agent.py
- [ ] 6.1: Add RAG imports and initialization
- [ ] 6.1: Modify generate_code method
- [ ] 6.1: Add record_approval method
- [ ] 6.1: Tests de integración passing
- [ ] 6.2: Modificar orchestrator_agent.py
- [ ] 6.2: Add RAG consultation in analysis
- [ ] 6.2: Tests passing

**Checkpoint**: ✅ Agents generating code with RAG context

---

### FASE 7: Testing (6-8 horas)
- [ ] 7.1: Crear test_rag_pipeline.py
- [ ] 7.1: All integration tests passing
- [ ] 7.2: Crear test_rag_performance.py
- [ ] 7.2: All performance benchmarks met
- [ ] E2E validation scripts passing
- [ ] Coverage >85%

**Checkpoint**: ✅ All tests passing, performance validated

---

### FASE 8: Monitoring (4-6 horas)
- [ ] 8.1: Crear metrics.py
- [ ] 8.1: Tests de metrics passing
- [ ] 8.2: Crear routers/rag.py
- [ ] 8.2: API endpoints responding
- [ ] 8.2: Health check working
- [ ] Metrics dashboard accessible

**Checkpoint**: ✅ Monitoring and metrics working

---

### FASE 9: Optimization (4-6 horas)
- [ ] 9.1: Crear tune_hyperparameters.py
- [ ] 9.1: Run tuning experiments
- [ ] 9.1: Update config with optimal values
- [ ] 9.2: Add embedding cache
- [ ] 9.2: Validate cache working
- [ ] Performance improvements measured

**Checkpoint**: ✅ System optimized and tuned

---

### Deployment Checklist
- [ ] All tests passing (100%)
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] .env configured for staging
- [ ] ChromaDB backup created
- [ ] Deploy to staging
- [ ] Staging validation passing
- [ ] Index existing code in staging
- [ ] Monitoring working in staging
- [ ] .env configured for production
- [ ] Production backup strategy confirmed
- [ ] Deploy to production
- [ ] Production validation passing
- [ ] Monitoring active
- [ ] Alerts configured
- [ ] Team trained on RAG system

---

### Post-Deployment
- [ ] Monitor metrics for 24h
- [ ] Check approval rates
- [ ] Validate precision improvement
- [ ] Gather user feedback
- [ ] Document learnings
- [ ] Plan next iterations

---

## 🎯 Success Criteria

### Minimum Viable Product (MVP)
- ✅ RAG system deployed to production
- ✅ Code generation using RAG context
- ✅ Feedback loop indexing approved code
- ✅ 85%+ test coverage
- ✅ Performance benchmarks met
- ✅ Monitoring active

### Target Goals
- ✅ **Precision improvement**: 70-80% → 90%+
- ✅ **Retrieval accuracy**: 0.75+ avg similarity
- ✅ **Performance**: <1s end-to-end RAG overhead
- ✅ **Reliability**: 99%+ retrieval success rate
- ✅ **Approval rate**: 80%+ of generated code

### Stretch Goals
- 🎯 Multi-language support optimized
- 🎯 Advanced ranking algorithms
- 🎯 Real-time feedback integration
- 🎯 Cross-project learning
- 🎯 95%+ precision

---

**Documento creado por**: Dany (SuperClaude)
**Fecha**: 2025-10-17
**Versión**: 1.0
**Status**: Ready for Implementation

---

## 📚 Referencias

- **ChromaDB Docs**: https://docs.trychroma.com/
- **sentence-transformers**: https://www.sbert.net/
- **RAG Papers**:
  - "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al.)
  - "Dense Passage Retrieval for Open-Domain Question Answering" (Karpukhin et al.)
- **DevMatrix Architecture**: Ver `DOCS/devmatrix-rag-implementation (1).md`

---

**FIN DEL PLAN** 🎉

