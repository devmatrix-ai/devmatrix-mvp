#!/usr/bin/env python
"""
RAG Seed Examples Script

Populates ChromaDB with high-quality curated code examples for common patterns.
These examples serve as the foundation for RAG-enhanced code generation.

Usage:
    python scripts/seed_rag_examples.py [--clear] [--batch-size 50]
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
    RetrievalStrategy,
)
from src.observability import get_logger

logger = get_logger("seed_rag_examples")


# Curated Code Examples with Metadata
SEED_EXAMPLES: List[Tuple[str, Dict[str, Any]]] = [
    # Authentication Patterns
    (
        """async def authenticate_user(username: str, password: str) -> Optional[User]:
    \"\"\"Authenticate user with username and password.\"\"\"
    user = await db.users.find_one({"username": username})
    if not user:
        return None

    if not verify_password(password, user["hashed_password"]):
        return None

    return User(**user)""",
        {
            "language": "python",
            "pattern": "authentication",
            "task_type": "user_auth",
            "framework": "fastapi",
            "complexity": "medium",
            "tags": ["security", "async", "database"],
            "approved": True,
        },
    ),
    (
        """def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    \"\"\"Create JWT access token.\"\"\"
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt""",
        {
            "language": "python",
            "pattern": "jwt_token",
            "task_type": "token_generation",
            "framework": "pyjwt",
            "complexity": "medium",
            "tags": ["jwt", "security", "authentication"],
            "approved": True,
        },
    ),
    # CRUD Operations
    (
        """async def create_item(item: ItemCreate, db: Session) -> Item:
    \"\"\"Create new item in database.\"\"\"
    db_item = Item(**item.dict())
    db.add(db_item)

    try:
        await db.commit()
        await db.refresh(db_item)
        return db_item
    except IntegrityError:
        await db.rollback()
        raise ValueError("Item already exists")""",
        {
            "language": "python",
            "pattern": "crud_create",
            "task_type": "database_operation",
            "framework": "sqlalchemy",
            "complexity": "low",
            "tags": ["crud", "database", "async", "error_handling"],
            "approved": True,
        },
    ),
    (
        """async def get_items_paginated(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Dict[str, Any] = None
) -> List[Item]:
    \"\"\"Get paginated list of items with optional filters.\"\"\"
    query = db.query(Item)

    if filters:
        for key, value in filters.items():
            if hasattr(Item, key):
                query = query.filter(getattr(Item, key) == value)

    items = await query.offset(skip).limit(limit).all()
    return items""",
        {
            "language": "python",
            "pattern": "crud_read",
            "task_type": "database_query",
            "framework": "sqlalchemy",
            "complexity": "medium",
            "tags": ["crud", "pagination", "filtering", "query"],
            "approved": True,
        },
    ),
    # Error Handling
    (
        """@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    \"\"\"Handle HTTP exceptions with structured logging.\"\"\"
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )""",
        {
            "language": "python",
            "pattern": "error_handling",
            "task_type": "exception_handler",
            "framework": "fastapi",
            "complexity": "medium",
            "tags": ["error_handling", "logging", "middleware"],
            "approved": True,
        },
    ),
    # Testing Patterns
    (
        """@pytest.fixture
async def test_client():
    \"\"\"Create test client with database.\"\"\"
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_create_user(test_client):
    \"\"\"Test user creation endpoint.\"\"\"
    response = await test_client.post(
        "/api/v1/users",
        json={"username": "testuser", "email": "test@example.com"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data""",
        {
            "language": "python",
            "pattern": "testing",
            "task_type": "api_test",
            "framework": "pytest",
            "complexity": "medium",
            "tags": ["testing", "async", "fixtures", "api"],
            "approved": True,
        },
    ),
    # Validation Patterns
    (
        """from pydantic import BaseModel, validator, Field

class UserCreate(BaseModel):
    \"\"\"User creation model with validation.\"\"\"
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    password: str = Field(..., min_length=8)

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.isalnum(), 'must be alphanumeric'
        return v

    @validator('password')
    def password_strength(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('must contain at least one uppercase letter')
        return v""",
        {
            "language": "python",
            "pattern": "validation",
            "task_type": "data_validation",
            "framework": "pydantic",
            "complexity": "medium",
            "tags": ["validation", "pydantic", "security"],
            "approved": True,
        },
    ),
    # Async Patterns
    (
        """async def fetch_multiple_sources(urls: List[str]) -> List[Dict[str, Any]]:
    \"\"\"Fetch data from multiple sources concurrently.\"\"\"
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [
            r for r in results
            if not isinstance(r, Exception)
        ]

        return valid_results

async def fetch_url(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    \"\"\"Fetch single URL with timeout and retry.\"\"\"
    for attempt in range(3):
        try:
            async with session.get(url, timeout=10) as response:
                return await response.json()
        except asyncio.TimeoutError:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)""",
        {
            "language": "python",
            "pattern": "async_concurrent",
            "task_type": "concurrent_fetch",
            "framework": "aiohttp",
            "complexity": "high",
            "tags": ["async", "concurrency", "retry", "error_handling"],
            "approved": True,
        },
    ),
    # Caching Patterns
    (
        """from functools import lru_cache
from datetime import datetime, timedelta

class TimedCache:
    \"\"\"Simple timed cache implementation.\"\"\"
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Any:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        self.cache[key] = (value, datetime.now())

    def clear(self):
        self.cache.clear()

# Usage with decorator
def cached(cache: TimedCache):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            result = cache.get(key)
            if result is None:
                result = await func(*args, **kwargs)
                cache.set(key, result)
            return result
        return wrapper
    return decorator""",
        {
            "language": "python",
            "pattern": "caching",
            "task_type": "cache_implementation",
            "framework": "standard_library",
            "complexity": "medium",
            "tags": ["caching", "decorator", "optimization"],
            "approved": True,
        },
    ),
    # Task Decomposition Pattern
    (
        """def decompose_web_app_tasks(requirements: str) -> List[Task]:
    \"\"\"Decompose web application into structured tasks.\"\"\"
    return [
        Task(
            name="Setup Project Structure",
            description="Initialize project with framework and dependencies",
            dependencies=[],
            priority="high",
            estimated_time="1h"
        ),
        Task(
            name="Design Database Schema",
            description="Create data models and relationships",
            dependencies=["Setup Project Structure"],
            priority="high",
            estimated_time="2h"
        ),
        Task(
            name="Implement Authentication",
            description="User auth with JWT tokens",
            dependencies=["Design Database Schema"],
            priority="high",
            estimated_time="3h"
        ),
        Task(
            name="Create API Endpoints",
            description="RESTful API for CRUD operations",
            dependencies=["Implement Authentication"],
            priority="medium",
            estimated_time="4h"
        ),
        Task(
            name="Write Tests",
            description="Unit and integration tests",
            dependencies=["Create API Endpoints"],
            priority="high",
            estimated_time="3h"
        ),
    ]""",
        {
            "language": "python",
            "pattern": "task_decomposition",
            "task_type": "task_breakdown",
            "project_type": "web_application",
            "complexity": "medium",
            "tags": ["planning", "orchestration", "dependencies"],
            "approved": True,
        },
    ),
    (
        """def decompose_ml_pipeline_tasks(requirements: str) -> List[Task]:
    \"\"\"Decompose ML pipeline into structured tasks.\"\"\"
    return [
        Task(
            name="Data Collection",
            description="Gather and validate data sources",
            dependencies=[],
            priority="high",
            estimated_time="2h"
        ),
        Task(
            name="Data Preprocessing",
            description="Clean, normalize, and transform data",
            dependencies=["Data Collection"],
            priority="high",
            estimated_time="3h"
        ),
        Task(
            name="Feature Engineering",
            description="Create and select relevant features",
            dependencies=["Data Preprocessing"],
            priority="medium",
            estimated_time="4h"
        ),
        Task(
            name="Model Training",
            description="Train and tune ML model",
            dependencies=["Feature Engineering"],
            priority="high",
            estimated_time="5h"
        ),
        Task(
            name="Model Evaluation",
            description="Evaluate model performance and metrics",
            dependencies=["Model Training"],
            priority="high",
            estimated_time="2h"
        ),
        Task(
            name="Model Deployment",
            description="Deploy model to production",
            dependencies=["Model Evaluation"],
            priority="medium",
            estimated_time="3h"
        ),
    ]""",
        {
            "language": "python",
            "pattern": "task_decomposition",
            "task_type": "task_breakdown",
            "project_type": "machine_learning",
            "complexity": "high",
            "tags": ["ml", "planning", "pipeline", "orchestration"],
            "approved": True,
        },
    ),
    # Logging Patterns
    (
        """from src.observability import get_logger

logger = get_logger(__name__)

async def process_payment(payment: Payment) -> PaymentResult:
    \"\"\"Process payment with structured logging.\"\"\"
    logger.info(
        "Processing payment",
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency
    )

    try:
        result = await payment_gateway.charge(payment)

        logger.info(
            "Payment successful",
            payment_id=payment.id,
            transaction_id=result.transaction_id,
            duration_ms=result.duration
        )

        return result

    except PaymentError as e:
        logger.error(
            "Payment failed",
            payment_id=payment.id,
            error_code=e.code,
            error_message=str(e)
        )
        raise""",
        {
            "language": "python",
            "pattern": "logging",
            "task_type": "structured_logging",
            "framework": "custom",
            "complexity": "low",
            "tags": ["logging", "observability", "error_handling"],
            "approved": True,
        },
    ),
    # Configuration Management
    (
        """from pydantic import BaseSettings, Field
from functools import lru_cache

class Settings(BaseSettings):
    \"\"\"Application settings with validation.\"\"\"
    app_name: str = "MyApp"
    debug: bool = False

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = 5

    # API Keys
    api_key: str = Field(..., env="API_KEY")
    secret_key: str = Field(..., env="SECRET_KEY")

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    \"\"\"Get cached settings instance.\"\"\"
    return Settings()""",
        {
            "language": "python",
            "pattern": "configuration",
            "task_type": "config_management",
            "framework": "pydantic",
            "complexity": "low",
            "tags": ["configuration", "settings", "environment"],
            "approved": True,
        },
    ),
]


def seed_examples(
    vector_store,
    examples: List[Tuple[str, Dict[str, Any]]],
    batch_size: int = 50,
    clear_first: bool = False,
) -> int:
    """
    Seed vector store with curated examples.

    Args:
        vector_store: Vector store instance
        examples: List of (code, metadata) tuples
        batch_size: Batch size for indexing
        clear_first: Whether to clear collection first

    Returns:
        Number of examples indexed
    """
    if clear_first:
        logger.info("Clearing existing collection...")
        count = vector_store.clear_collection()
        logger.info(f"Cleared {count} existing examples")

    logger.info(f"Seeding {len(examples)} examples...")

    # Process in batches
    total_indexed = 0

    for i in range(0, len(examples), batch_size):
        batch = examples[i : i + batch_size]
        codes = [code for code, _ in batch]

        # Convert list values to strings for ChromaDB compatibility
        metadatas = []
        for _, metadata in batch:
            cleaned_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, list):
                    cleaned_metadata[key] = ",".join(str(v) for v in value)
                else:
                    cleaned_metadata[key] = value
            metadatas.append(cleaned_metadata)

        try:
            code_ids = vector_store.add_batch(codes, metadatas)
            total_indexed += len(code_ids)

            logger.info(
                f"Batch indexed",
                batch_num=i // batch_size + 1,
                batch_size=len(code_ids),
                total=total_indexed,
            )

        except Exception as e:
            logger.error(f"Batch indexing failed", batch_num=i // batch_size + 1, error=str(e))
            continue

    return total_indexed


def verify_seeding(vector_store) -> bool:
    """
    Verify that seeding was successful.

    Args:
        vector_store: Vector store instance

    Returns:
        True if verification passed
    """
    logger.info("Verifying seeded examples...")

    # Check total count
    stats = vector_store.get_stats()
    total = stats.get("total_examples", 0)

    if total == 0:
        logger.error("No examples found after seeding")
        return False

    logger.info(f"Total examples: {total}")

    # Test retrieval for different patterns
    test_queries = [
        ("user authentication with JWT", "authentication"),
        ("create database record", "crud_create"),
        ("error handling in API", "error_handling"),
        ("async concurrent requests", "async_concurrent"),
    ]

    from src.rag import create_retriever

    retriever = create_retriever(vector_store, top_k=3)

    for query, expected_pattern in test_queries:
        results = retriever.retrieve(query, min_similarity=0.5)

        if not results:
            logger.warning(f"No results for query: {query}")
            continue

        # Check if expected pattern is in results
        found = any(expected_pattern in r.metadata.get("pattern", "") for r in results)

        if found:
            logger.info(
                f"Query successful",
                query=query,
                results_count=len(results),
                top_similarity=results[0].similarity,
            )
        else:
            logger.warning(
                f"Expected pattern not found",
                query=query,
                expected=expected_pattern,
                found_patterns=[r.metadata.get("pattern") for r in results],
            )

    logger.info("Verification complete")
    return True


def main():
    """Main seeding script."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed RAG with code examples")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before seeding",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for indexing (default: 50)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify seeding (default: True)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("RAG Seed Examples Script")
    print("=" * 60)

    # Initialize RAG components
    try:
        logger.info("Initializing RAG components...")
        embedding_model = create_embedding_model()
        vector_store = create_vector_store(embedding_model)

        logger.info("RAG components initialized")

    except Exception as e:
        logger.error("Failed to initialize RAG", error=str(e))
        print(f"\n❌ Initialization failed: {str(e)}")
        print("\nPlease ensure:")
        print("  1. ChromaDB is running: docker-compose up chromadb -d")
        print("  2. CHROMADB_HOST and CHROMADB_PORT are configured in .env")
        return 1

    # Seed examples
    try:
        print(f"\n📦 Seeding {len(SEED_EXAMPLES)} examples...")
        if args.clear:
            print("⚠️  Clearing existing collection first...")

        indexed_count = seed_examples(
            vector_store,
            SEED_EXAMPLES,
            batch_size=args.batch_size,
            clear_first=args.clear,
        )

        print(f"\n✅ Successfully indexed {indexed_count} examples")

    except Exception as e:
        logger.error("Seeding failed", error=str(e))
        print(f"\n❌ Seeding failed: {str(e)}")
        return 1

    # Verify seeding
    if args.verify:
        print("\n🔍 Verifying seeded examples...")

        try:
            success = verify_seeding(vector_store)

            if success:
                print("\n✅ Verification passed")
            else:
                print("\n⚠️  Verification completed with warnings")

        except Exception as e:
            logger.error("Verification failed", error=str(e))
            print(f"\n❌ Verification failed: {str(e)}")
            return 1

    # Final stats
    stats = vector_store.get_stats()
    print("\n" + "=" * 60)
    print("Final Statistics")
    print("=" * 60)
    print(f"  Collection: {stats.get('collection_name', 'unknown')}")
    print(f"  Total examples: {stats.get('total_examples', 0)}")
    print(f"  Embedding dimension: {stats.get('embedding_dimension', 0)}")
    print("\n✅ Seeding complete! RAG is ready to use.")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
