"""Database engine and session configuration."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://taskmanager:taskmanager@localhost:5432/taskmanager")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("DEBUG", "False") == "True",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
