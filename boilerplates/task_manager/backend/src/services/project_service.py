"""Project service for project management."""

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.project import Project
from src.schemas.project import ProjectCreate, ProjectUpdate
from .base_crud import BaseCRUDService


class ProjectService(BaseCRUDService[Project, ProjectCreate, ProjectUpdate]):
    """Service for project operations."""

    def __init__(self):
        super().__init__(Project)
