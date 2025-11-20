"""
Unit Tests for Modular Architecture Generator

Tests Task Group 2: Modular Architecture implementation

Author: System Architect
Date: 2025-11-20
"""

import pytest
from dataclasses import dataclass
from typing import List, Dict
from src.services.modular_architecture_generator import ModularArchitectureGenerator, EntitySpec


@dataclass
class MockField:
    """Mock field specification"""
    name: str
    type: str
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    default: str = None
    constraints: List[str] = None


@dataclass
class MockEntity:
    """Mock entity specification"""
    name: str
    snake_name: str
    fields: List[MockField]
    description: str = ""


@dataclass
class MockEndpoint:
    """Mock endpoint specification"""
    entity: str
    operation: str
    method: str
    path: str
    description: str = ""


@dataclass
class MockSpecRequirements:
    """Mock spec requirements"""
    entities: List[MockEntity]
    endpoints: List[MockEndpoint]
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {"spec_name": "Test API"}


class TestModularArchitectureGenerator:
    """Test modular architecture generation"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = ModularArchitectureGenerator()

        # Create mock entity
        self.mock_entity = MockEntity(
            name="Task",
            snake_name="task",
            fields=[
                MockField(name="id", type="uuid", primary_key=True),
                MockField(name="title", type="string", required=True),
                MockField(name="description", type="text", required=False),
                MockField(name="completed", type="boolean", required=True, default="False"),
                MockField(name="created_at", type="datetime"),
                MockField(name="updated_at", type="datetime"),
            ],
            description="Task management entity"
        )

        # Create mock endpoints
        self.mock_endpoints = [
            MockEndpoint(entity="Task", operation="create", method="POST", path="/tasks"),
            MockEndpoint(entity="Task", operation="read", method="GET", path="/tasks/{id}"),
            MockEndpoint(entity="Task", operation="list", method="GET", path="/tasks"),
            MockEndpoint(entity="Task", operation="update", method="PUT", path="/tasks/{id}"),
            MockEndpoint(entity="Task", operation="delete", method="DELETE", path="/tasks/{id}"),
        ]

        # Create mock spec
        self.mock_spec = MockSpecRequirements(
            entities=[self.mock_entity],
            endpoints=self.mock_endpoints
        )

    def test_generate_modular_app_creates_all_files(self):
        """Test that all required files are generated"""
        files = self.generator.generate_modular_app(self.mock_spec)

        expected_files = [
            "src/core/__init__.py",
            "src/core/config.py",
            "src/core/database.py",
            "src/models/__init__.py",
            "src/models/schemas.py",
            "src/models/entities.py",
            "src/repositories/__init__.py",
            "src/repositories/task_repository.py",
            "src/services/__init__.py",
            "src/services/task_service.py",
            "src/api/__init__.py",
            "src/api/dependencies.py",
            "src/api/routes/__init__.py",
            "src/api/routes/task.py",
            "src/main.py",
            "requirements.txt",
            ".env.example",
            "README.md",
        ]

        for file_path in expected_files:
            assert file_path in files, f"Missing expected file: {file_path}"

    def test_generate_config_contains_settings(self):
        """Test that config.py contains Settings class"""
        config_code = self.generator._generate_config()

        assert "class Settings(BaseSettings):" in config_code
        assert "pydantic_settings import BaseSettings" in config_code
        assert "database_url:" in config_code
        assert "app_name:" in config_code
        assert "log_level:" in config_code

    def test_generate_database_contains_async_engine(self):
        """Test that database.py contains async engine setup"""
        db_code = self.generator._generate_database()

        assert "create_async_engine" in db_code
        assert "async_sessionmaker" in db_code
        assert "declarative_base" in db_code
        assert "async def get_db()" in db_code
        assert "pool_size=" in db_code

    def test_generate_schemas_contains_all_schema_types(self):
        """Test that schemas.py contains Base, Create, Update, Response schemas"""
        schemas_code = self.generator._generate_schemas(self.mock_spec)

        assert "class TaskBase(BaseModel):" in schemas_code
        assert "class TaskCreate(TaskBase):" in schemas_code
        assert "class TaskUpdate(BaseModel):" in schemas_code
        assert "class Task(TaskBase):" in schemas_code
        assert "model_config = ConfigDict(strict=True)" in schemas_code
        assert "from_attributes=True" in schemas_code

    def test_generate_entities_contains_sqlalchemy_models(self):
        """Test that entities.py contains SQLAlchemy models"""
        entities_code = self.generator._generate_entities(self.mock_spec)

        assert "class TaskEntity(Base):" in entities_code
        assert '__tablename__ = "task"' in entities_code
        assert "Column(UUID(as_uuid=True), primary_key=True" in entities_code
        assert "DateTime(timezone=True)" in entities_code
        assert "datetime.now(timezone.utc)" in entities_code

    def test_generate_repository_contains_crud_methods(self):
        """Test that repository contains all CRUD methods"""
        repo_code = self.generator._generate_repository(self.mock_entity)

        assert "class TaskRepository:" in repo_code
        assert "async def create(" in repo_code
        assert "async def get(" in repo_code
        assert "async def list(" in repo_code
        assert "async def update(" in repo_code
        assert "async def delete(" in repo_code
        assert "TaskCreate" in repo_code
        assert "TaskUpdate" in repo_code

    def test_generate_service_contains_business_logic_methods(self):
        """Test that service contains business logic methods"""
        service_code = self.generator._generate_service(self.mock_entity)

        assert "class TaskService:" in service_code
        assert "async def create(" in service_code
        assert "async def get(" in service_code
        assert "async def list(" in service_code
        assert "async def update(" in service_code
        assert "async def delete(" in service_code
        assert "TaskRepository" in service_code
        assert "model_validate" in service_code

    def test_generate_dependencies_contains_di_functions(self):
        """Test that dependencies.py contains dependency injection functions"""
        deps_code = self.generator._generate_dependencies(self.mock_spec)

        assert "def get_task_repository(" in deps_code
        assert "def get_task_service(" in deps_code
        assert "Depends(get_db)" in deps_code
        assert "Depends(get_task_repository)" in deps_code

    def test_generate_routes_contains_all_endpoints(self):
        """Test that routes contain all specified endpoints"""
        routes_code = self.generator._generate_routes(self.mock_entity, self.mock_spec)

        assert "router = APIRouter(" in routes_code
        assert "@router.post(" in routes_code
        assert "@router.get(" in routes_code
        assert "@router.put(" in routes_code
        assert "@router.delete(" in routes_code
        assert "HTTPException" in routes_code
        assert "status_code=404" in routes_code

    def test_generate_main_includes_all_routers(self):
        """Test that main.py includes all entity routers"""
        main_code = self.generator._generate_main(self.mock_spec)

        assert "from fastapi import FastAPI" in main_code
        assert "from src.api.routes import task" in main_code
        assert "app.include_router(task.router)" in main_code
        assert "app = FastAPI(" in main_code

    def test_generate_requirements_contains_dependencies(self):
        """Test that requirements.txt contains all dependencies"""
        requirements = self.generator._generate_requirements()

        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "sqlalchemy" in requirements
        assert "asyncpg" in requirements
        assert "pydantic-settings" in requirements
        assert "alembic" in requirements

    def test_field_type_mapping(self):
        """Test field type mapping from spec to Python types"""
        assert self.generator._map_field_type("string") == "str"
        assert self.generator._map_field_type("integer") == "int"
        assert self.generator._map_field_type("boolean") == "bool"
        assert self.generator._map_field_type("datetime") == "datetime"
        assert self.generator._map_field_type("uuid") == "UUID"

    def test_sqlalchemy_type_mapping(self):
        """Test SQLAlchemy type mapping from spec types"""
        assert "String" in self.generator._map_sqlalchemy_type("string")
        assert "Integer" in self.generator._map_sqlalchemy_type("integer")
        assert "Boolean" in self.generator._map_sqlalchemy_type("boolean")
        assert "DateTime(timezone=True)" in self.generator._map_sqlalchemy_type("datetime")
        assert "UUID(as_uuid=True)" in self.generator._map_sqlalchemy_type("uuid")

    def test_multiple_entities_generate_multiple_files(self):
        """Test that multiple entities generate all required files"""
        # Add second entity
        second_entity = MockEntity(
            name="User",
            snake_name="user",
            fields=[
                MockField(name="id", type="uuid", primary_key=True),
                MockField(name="email", type="email", required=True, unique=True),
                MockField(name="name", type="string", required=True),
            ]
        )

        second_endpoints = [
            MockEndpoint(entity="User", operation="create", method="POST", path="/users"),
            MockEndpoint(entity="User", operation="read", method="GET", path="/users/{id}"),
        ]

        multi_spec = MockSpecRequirements(
            entities=[self.mock_entity, second_entity],
            endpoints=self.mock_endpoints + second_endpoints
        )

        files = self.generator.generate_modular_app(multi_spec)

        # Check both entities have files
        assert "src/repositories/task_repository.py" in files
        assert "src/repositories/user_repository.py" in files
        assert "src/services/task_service.py" in files
        assert "src/services/user_service.py" in files
        assert "src/api/routes/task.py" in files
        assert "src/api/routes/user.py" in files

        # Check dependencies include both
        deps_code = files["src/api/dependencies.py"]
        assert "TaskRepository" in deps_code
        assert "UserRepository" in deps_code
        assert "TaskService" in deps_code
        assert "UserService" in deps_code

    def test_timezone_aware_datetimes(self):
        """Test that generated code uses timezone-aware datetimes"""
        entities_code = self.generator._generate_entities(self.mock_spec)

        assert "DateTime(timezone=True)" in entities_code
        assert "datetime.now(timezone.utc)" in entities_code
        assert "datetime.utcnow" not in entities_code

    def test_strict_mode_enabled_in_schemas(self):
        """Test that Pydantic strict mode is enabled"""
        schemas_code = self.generator._generate_schemas(self.mock_spec)

        assert "model_config = ConfigDict(strict=True)" in schemas_code

    def test_proper_separation_of_concerns(self):
        """Test that files maintain separation of concerns"""
        files = self.generator.generate_modular_app(self.mock_spec)

        # Models should not have business logic
        schemas = files["src/models/schemas.py"]
        entities = files["src/models/entities.py"]
        assert "async def" not in schemas
        assert "async def" not in entities

        # Repositories should only have data access
        repo = files["src/repositories/task_repository.py"]
        assert "AsyncSession" in repo
        assert "select(" in repo
        assert "HTTPException" not in repo

        # Services should have business logic
        service = files["src/services/task_service.py"]
        assert "TaskRepository" in service
        assert "model_validate" in service
        assert "select(" not in service

        # Routes should only handle HTTP
        routes = files["src/api/routes/task.py"]
        assert "HTTPException" in routes
        assert "TaskService" in routes
        assert "select(" not in routes
