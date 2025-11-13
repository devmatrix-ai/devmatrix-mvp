"""Test configuration and fixtures."""

import pytest
import os
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.base import Base
from src.models.user import User
from src.models.task import Task
from src.models.project import Project
from src.services.user_service import UserService
from src.schemas.user import UserCreate


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    return TestingSessionLocal, override_get_db


@pytest.fixture
def db_session(test_db):
    """Get database session for test."""
    TestingSessionLocal, _ = test_db
    connection = TestingSessionLocal.kw["bind"].connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def organization_id():
    """Generate organization ID."""
    return str(uuid4())


@pytest.fixture
def test_user(db_session, organization_id):
    """Create test user."""
    user_data = UserCreate(
        email="test@example.com",
        username="testuser",
        password="TestPassword123!",
        full_name="Test User",
        organization_id=organization_id,
    )
    user = UserService.create_user(db_session, obj_in=user_data)
    return user


@pytest.fixture
def test_user_token(test_user):
    """Generate test user JWT token."""
    return UserService.create_access_token(test_user.id, test_user.organization_id)


@pytest.fixture
def test_project(db_session, test_user, organization_id):
    """Create test project."""
    from src.schemas.project import ProjectCreate
    from src.services.project_service import ProjectService

    project_data = ProjectCreate(
        name="Test Project",
        description="A test project",
        owner_id=test_user.id,
        organization_id=organization_id,
    )
    project_service = ProjectService()
    project = project_service.create(db_session, obj_in=project_data, organization_id=organization_id)
    return project


@pytest.fixture
def test_task(db_session, test_user, test_project, organization_id):
    """Create test task."""
    from src.schemas.task import TaskCreate
    from src.services.task_service import TaskService

    task_data = TaskCreate(
        name="Test Task",
        description="A test task",
        status="todo",
        priority="medium",
        project_id=test_project.id,
        user_id=test_user.id,
        organization_id=organization_id,
    )
    task_service = TaskService()
    task = task_service.create_task(db_session, obj_in=task_data)
    return task
