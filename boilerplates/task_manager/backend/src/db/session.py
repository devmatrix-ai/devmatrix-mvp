"""Database session configuration."""

from sqlalchemy.orm import Session
from .engine import SessionLocal as _SessionLocal


class SessionLocal(_SessionLocal):
    """Session factory with additional configuration."""

    pass
