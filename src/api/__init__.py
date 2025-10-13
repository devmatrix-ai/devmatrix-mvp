"""
REST API Module

Provides FastAPI-based REST API for workflow management and execution.
"""

from .app import create_app

__all__ = ["create_app"]
