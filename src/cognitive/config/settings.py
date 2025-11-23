"""
Cognitive Architecture Settings

Centralized configuration using Pydantic for validation and type safety.
All settings loaded from environment variables with secure defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class CognitiveSettings(BaseSettings):
    """
    Cognitive Architecture Configuration

    All settings are loaded from environment variables.
    See .env.example for required configuration.
    """

    # Neo4j Configuration (Existing Infrastructure)
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j Bolt URI for pattern graph database"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        default="devmatrix",
        description="Neo4j password"
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name"
    )

    # Qdrant Configuration (Existing Infrastructure)
    qdrant_host: str = Field(
        default="localhost",
        description="Qdrant vector database host"
    )
    qdrant_port: int = Field(
        default=6333,
        description="Qdrant HTTP API port"
    )
    qdrant_collection_patterns: str = Field(
        default="devmatrix_patterns",
        description="Existing collection with 21,624 patterns"
    )
    qdrant_collection_semantic: str = Field(
        default="semantic_patterns",
        description="New collection for semantic task signatures"
    )

    # Embeddings Configuration
    embedding_model: str = Field(
        default="microsoft/graphcodebert-base",
        description="GraphCodeBERT model for code-aware semantic embeddings"
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension (768 for GraphCodeBERT)"
    )
    use_sentence_transformers: bool = Field(
        default=False,
        description="Use SentenceTransformers wrapper (False for GraphCodeBERT)"
    )

    # Pattern Bank Configuration
    pattern_similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity for pattern matching"
    )
    pattern_reuse_target: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Target pattern reuse rate (30% MVP, 50% final)"
    )

    # CPIE Configuration
    cpie_max_inference_time: int = Field(
        default=5,
        gt=0,
        description="Maximum inference time per atom in seconds (MVP target)"
    )
    cpie_precision_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Minimum precision to store pattern in bank"
    )

    # Validation Configuration
    e2e_precision_target: float = Field(
        default=0.88,
        ge=0.0,
        le=1.0,
        description="E2E precision target for MVP (88%)"
    )
    atomic_precision_target: float = Field(
        default=0.92,
        ge=0.0,
        le=1.0,
        description="Atomic precision target for MVP (92%)"
    )
    unit_test_coverage_target: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Unit test coverage requirement (95%)"
    )

    # Co-Reasoning Configuration
    co_reasoning_enabled: bool = Field(
        default=True,
        description="Enable Claude + DeepSeek co-reasoning"
    )

    # LRM Configuration (Phase 2)
    lrm_enabled: bool = Field(
        default=False,
        description="Enable Large Reasoning Model (o1/DeepSeek-R1)"
    )
    lrm_complexity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Complexity threshold to trigger LRM (0.8 = top 20%)"
    )

    # API Keys (Loaded from .env)
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API Key for Claude"
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API Key for GPT-4"
    )

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env (other components)


# Global settings instance
settings = CognitiveSettings()
