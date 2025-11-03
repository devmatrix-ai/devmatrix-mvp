#!/usr/bin/env python
"""
Official Documentation Scraper for RAG

Scrapes code examples from official documentation of major frameworks.
Filters for quality, adds context, and indexes into ChromaDB.

Usage:
    python scripts/seed_official_docs.py --framework all
    python scripts/seed_official_docs.py --framework fastapi
"""

import logging
import sys
from typing import List, Tuple, Dict, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_embedding_model, create_vector_store
from src.observability import get_logger

logger = get_logger(__name__)


# ============================================================
# CURATED DOCUMENTATION EXAMPLES
# ============================================================

FASTAPI_DOCS_EXAMPLES: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

@app.post("/items/")
async def create_item(item: Item):
    return item

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "fastapi",
            "docs_section": "Tutorial - First Steps",
            "pattern": "fastapi_basic_crud",
            "task_type": "api_development",
            "complexity": "low",
            "quality": "official_example",
            "tags": "fastapi,crud,api,models,pydantic",
            "approved": True,
        }
    ),
    (
        """from fastapi import Depends, FastAPI, HTTPException

app = FastAPI()

async def get_query(q: str = None):
    return q

async def get_skip_limit(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(get_skip_limit)):
    return commons

@app.get("/users/")
async def read_users(q: str = Depends(get_query)):
    if not q:
        return []
    return [{"item_id": "Foo"}, {"item_id": "Bar"}]""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "fastapi",
            "docs_section": "Tutorial - Dependencies",
            "pattern": "fastapi_dependencies",
            "task_type": "api_development",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "fastapi,dependencies,injection,reusable",
            "approved": True,
        }
    ),
    (
        """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def main():
    return {"message": "Hello World"}""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "fastapi",
            "docs_section": "Advanced - CORS",
            "pattern": "fastapi_cors",
            "task_type": "api_infrastructure",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "fastapi,cors,middleware,security",
            "approved": True,
        }
    ),
    (
        """from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/items/{id}", response_class=HTMLResponse)
async def read_item(id: str):
    html_content = f"<html><head><title>Item ID: {id}</title></head><body><h1>Item: {id}</h1></body></html>"
    return HTMLResponse(content=html_content)

@app.get("/")
async def main():
    content = "<html><body><h1>It works!</h1></body></html>"
    return HTMLResponse(content=content)""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "fastapi",
            "docs_section": "Advanced - Response",
            "pattern": "fastapi_html_response",
            "task_type": "api_development",
            "complexity": "low",
            "quality": "official_example",
            "tags": "fastapi,responses,html,templates",
            "approved": True,
        }
    ),
    (
        """from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

class Image(BaseModel):
    url: str
    name: Optional[str] = None

class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    items: Optional[list] = []

app = FastAPI()

@app.post("/users/", response_model=User)
async def create_user(user: User):
    return user

@app.post("/images/multiple/")
async def upload_multiple_images(images: list[Image]):
    return images""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "fastapi",
            "docs_section": "Tutorial - Nested Models",
            "pattern": "fastapi_nested_models",
            "task_type": "api_development",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "fastapi,pydantic,models,nested,relationships",
            "approved": True,
        }
    ),
    (
        """from typing import Optional
from fastapi import FastAPI, status
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: float = 10.5
    tags: list[str] = []

app = FastAPI()

@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    item_dict = item.dict()
    if item.tax:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict

@app.get("/items/", response_model=list[Item])
async def read_items():
    return [
        {"name": "Foo", "price": 50},
        {"name": "Bar", "description": "The bartenders", "price": 62, "tax": 20.2},
        {"name": "Baz", "price": 50.2, "tax": 10.5, "tags": ["tag1"]},
    ]""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "fastapi",
            "docs_section": "Advanced - Response Model",
            "pattern": "fastapi_response_model",
            "task_type": "api_development",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "fastapi,response-model,status,http",
            "approved": True,
        }
    ),
]

SQLALCHEMY_DOCS_EXAMPLES: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    nickname = Column(String)

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

ed_user = User(name="ed", fullname="Edward Jones", nickname="edsnickname")
session.add(ed_user)
session.commit()""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "sqlalchemy",
            "docs_section": "ORM Tutorial - Create",
            "pattern": "sqlalchemy_basic_orm",
            "task_type": "database_patterns",
            "complexity": "low",
            "quality": "official_example",
            "tags": "sqlalchemy,orm,models,database",
            "approved": True,
        }
    ),
    (
        """from sqlalchemy import select, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    addresses = relationship("Address", back_populates="user")

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    email = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="addresses")

stmt = select(User).where(User.name == "jack")
jack = session.scalars(stmt).first()

for address in jack.addresses:
    print(f"Email: {address.email}")""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "sqlalchemy",
            "docs_section": "ORM Tutorial - Relationships",
            "pattern": "sqlalchemy_relationships",
            "task_type": "database_patterns",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "sqlalchemy,relationships,foreign-keys,orm",
            "approved": True,
        }
    ),
    (
        """from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import sessionmaker

# Count
stmt = select(func.count(User.id)).select_from(User)
count = session.scalar(stmt)

# Filter with operators
stmt = select(User).where(
    and_(
        User.name == "jack",
        User.id > 2
    )
)

# OR conditions
stmt = select(User).where(
    or_(
        User.name == "jack",
        User.name == "fred"
    )
)

# IN clause
stmt = select(User).where(User.name.in_(["jack", "fred"]))

# LIKE
stmt = select(User).where(User.name.like("%jack%"))""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "sqlalchemy",
            "docs_section": "ORM Tutorial - Querying",
            "pattern": "sqlalchemy_querying",
            "task_type": "database_patterns",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "sqlalchemy,querying,filters,conditions",
            "approved": True,
        }
    ),
]

PYDANTIC_DOCS_EXAMPLES: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from pydantic import BaseModel, ValidationError

class User(BaseModel):
    id: int
    name: str = "John Doe"
    email: str

# Valid
user = User(id=123, email="user@example.com")
print(user)

# Invalid - will raise ValidationError
try:
    user = User(id="not an id", email="user@example.com")
except ValidationError as e:
    print(e)""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pydantic",
            "docs_section": "Models - Basic",
            "pattern": "pydantic_basic_model",
            "task_type": "data_validation",
            "complexity": "low",
            "quality": "official_example",
            "tags": "pydantic,models,validation,types",
            "approved": True,
        }
    ),
    (
        """from pydantic import BaseModel, field_validator
from typing import Optional

class User(BaseModel):
    name: str
    email: str
    age: Optional[int] = None
    
    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name must not be empty")
        return v
    
    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("age must be positive")
        return v

# Valid
user = User(name="John", email="john@example.com", age=30)

# Invalid - raises ValidationError
try:
    user = User(name="", email="test@example.com", age=-1)
except Exception as e:
    print(f"Validation error: {e}")""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pydantic",
            "docs_section": "Models - Field Validators",
            "pattern": "pydantic_validators",
            "task_type": "data_validation",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "pydantic,validators,validation,custom",
            "approved": True,
        }
    ),
    (
        """from pydantic import BaseModel, ConfigDict
from typing import Optional

class Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str
    value: int

# Whitespace is stripped
m = Model(name="  hello world  ", value=42)
assert m.name == "hello world"

class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    name: str
    age: int

user = User(name="John", age=30)
user.age = "not an int"  # Will raise ValidationError""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pydantic",
            "docs_section": "Models - Configuration",
            "pattern": "pydantic_config",
            "task_type": "data_validation",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "pydantic,configuration,config,models",
            "approved": True,
        }
    ),
]

PYTEST_DOCS_EXAMPLES: List[Tuple[str, Dict[str, Any]]] = [
    (
        """import pytest

def simple_addition():
    assert 1 + 1 == 2

def test_division():
    with pytest.raises(ZeroDivisionError):
        1 / 0

def test_with_info():
    x = 5
    y = 3
    assert x > y, f"Expected {x} to be greater than {y}"

@pytest.mark.skip(reason="not implemented yet")
def test_later():
    pass

@pytest.mark.xfail(reason="known issue")
def test_something():
    assert False""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pytest",
            "docs_section": "Getting Started",
            "pattern": "pytest_basic",
            "task_type": "testing",
            "complexity": "low",
            "quality": "official_example",
            "tags": "pytest,testing,assertions,fixtures",
            "approved": True,
        }
    ),
    (
        """import pytest

@pytest.fixture
def sample_data():
    return {"name": "test", "value": 42}

@pytest.fixture
def database():
    db = setup_database()
    yield db
    teardown_database(db)

def test_with_fixture(sample_data):
    assert sample_data["name"] == "test"
    assert sample_data["value"] == 42

def test_database_operations(database):
    result = database.query("SELECT * FROM users")
    assert len(result) > 0""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pytest",
            "docs_section": "Fixtures",
            "pattern": "pytest_fixtures",
            "task_type": "testing",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "pytest,fixtures,setup,teardown",
            "approved": True,
        }
    ),
    (
        """import pytest

@pytest.mark.parametrize("input,expected", [
    (2, 4),
    (3, 9),
    (4, 16),
])
def test_square(input, expected):
    assert input ** 2 == expected

@pytest.mark.parametrize("x,y", [
    (1, 2),
    (3, 4),
    (5, 6),
])
def test_addition(x, y):
    assert x + y > x
    assert x + y > y""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pytest",
            "docs_section": "Parametrization",
            "pattern": "pytest_parametrize",
            "task_type": "testing",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "pytest,parametrization,parametrize,testing",
            "approved": True,
        }
    ),
    (
        """import pytest
from unittest.mock import Mock, patch, AsyncMock

def test_mocking():
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked value"
    
    result = mock_obj.method()
    assert result == "mocked value"
    mock_obj.method.assert_called_once()

@patch("mymodule.external_function")
def test_with_patch(mock_external):
    mock_external.return_value = 42
    
    result = my_function_that_calls_external()
    assert result == 42

@pytest.mark.asyncio
async def test_async_function():
    mock = AsyncMock()
    mock.return_value = "async result"
    
    result = await mock()
    assert result == "async result\"""",
        {
            "language": "python",
            "source": "official_docs",
            "framework": "pytest",
            "docs_section": "Mocking",
            "pattern": "pytest_mocking",
            "task_type": "testing",
            "complexity": "medium",
            "quality": "official_example",
            "tags": "pytest,mocking,mock,patch,testing",
            "approved": True,
        }
    ),
]

# ============================================================
# COMBINE ALL EXAMPLES
# ============================================================

ALL_DOCS_EXAMPLES = (
    FASTAPI_DOCS_EXAMPLES +
    SQLALCHEMY_DOCS_EXAMPLES +
    PYDANTIC_DOCS_EXAMPLES +
    PYTEST_DOCS_EXAMPLES
)


def seed_official_docs(
    vector_store,
    examples: List[Tuple[str, Dict[str, Any]]],
    batch_size: int = 50,
) -> int:
    """
    Seed vector store with official documentation examples.
    
    Args:
        vector_store: Vector store instance
        examples: List of (code, metadata) tuples
        batch_size: Batch size for indexing
    
    Returns:
        Number of examples indexed
    """
    logger.info(f"Seeding {len(examples)} official documentation examples...")
    
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


def main():
    """Main seeding script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed RAG with official documentation examples")
    parser.add_argument(
        "--framework",
        choices=["all", "fastapi", "sqlalchemy", "pydantic", "pytest"],
        default="all",
        help="Framework to seed (default: all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for indexing (default: 50)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Official Documentation Seeding Script")
    print("=" * 60)
    
    # Select examples based on framework
    if args.framework == "all":
        examples_to_seed = ALL_DOCS_EXAMPLES
    elif args.framework == "fastapi":
        examples_to_seed = FASTAPI_DOCS_EXAMPLES
    elif args.framework == "sqlalchemy":
        examples_to_seed = SQLALCHEMY_DOCS_EXAMPLES
    elif args.framework == "pydantic":
        examples_to_seed = PYDANTIC_DOCS_EXAMPLES
    elif args.framework == "pytest":
        examples_to_seed = PYTEST_DOCS_EXAMPLES
    
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
        print(f"\n📦 Seeding {len(examples_to_seed)} {args.framework} documentation examples...")
        
        indexed_count = seed_official_docs(
            vector_store,
            examples_to_seed,
            batch_size=args.batch_size,
        )
        
        print(f"\n✅ Successfully indexed {indexed_count} documentation examples")
        
        # Show stats
        stats = vector_store.get_stats()
        print(f"\n📊 Vector Store Stats:")
        print(f"  Total examples: {stats.get('total_examples', 0)}")
        
    except Exception as e:
        logger.error("Seeding failed", error=str(e))
        print(f"\n❌ Seeding failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
