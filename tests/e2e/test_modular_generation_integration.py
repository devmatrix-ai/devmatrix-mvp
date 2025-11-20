"""
E2E Integration Test: Modular Architecture Generation

Tests the complete flow from spec parsing to modular app generation.

Author: System Architect
Date: 2025-11-20
"""

import pytest
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class MockField:
    """Mock field for testing"""
    name: str
    type: str
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    default: str = None
    constraints: List[str] = None


@dataclass
class MockEntity:
    """Mock entity for testing"""
    name: str
    snake_name: str
    fields: List[MockField]
    description: str = ""


@dataclass
class MockEndpoint:
    """Mock endpoint for testing"""
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
    requirements: List = None
    business_logic: List = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {"spec_name": "Task API"}
        if self.requirements is None:
            self.requirements = []
        if self.business_logic is None:
            self.business_logic = []


class TestModularGenerationIntegration:
    """Test end-to-end modular generation flow"""

    def setup_method(self):
        """Setup test fixtures"""
        from src.services.code_generation_service import CodeGenerationService

        # Mock database session (not actually used in this flow)
        class MockSession:
            pass

        self.service = CodeGenerationService(
            db=MockSession(),
            enable_feedback_loop=False,
            enable_pattern_promotion=False,
            enable_dag_sync=False
        )

        # Create realistic spec
        self.task_entity = MockEntity(
            name="Task",
            snake_name="task",
            fields=[
                MockField(name="id", type="uuid", primary_key=True),
                MockField(name="title", type="string", required=True),
                MockField(name="description", type="text", required=False),
                MockField(name="completed", type="boolean", required=True, default="False"),
                MockField(name="priority", type="integer", required=False),
                MockField(name="created_at", type="datetime"),
                MockField(name="updated_at", type="datetime"),
            ]
        )

        self.task_endpoints = [
            MockEndpoint("Task", "create", "POST", "/tasks"),
            MockEndpoint("Task", "read", "GET", "/tasks/{id}"),
            MockEndpoint("Task", "list", "GET", "/tasks"),
            MockEndpoint("Task", "update", "PUT", "/tasks/{id}"),
            MockEndpoint("Task", "delete", "DELETE", "/tasks/{id}"),
        ]

        self.spec = MockSpecRequirements(
            entities=[self.task_entity],
            endpoints=self.task_endpoints
        )

    @pytest.mark.asyncio
    async def test_modular_generation_creates_complete_app(self):
        """Test that modular generation creates all expected files"""
        files = await self.service.generate_modular_app(self.spec)

        # Verify structure
        assert len(files) >= 15, "Should generate at least 15 files"

        # Core files
        assert "src/core/config.py" in files
        assert "src/core/database.py" in files

        # Models
        assert "src/models/schemas.py" in files
        assert "src/models/entities.py" in files

        # Repositories
        assert "src/repositories/task_repository.py" in files

        # Services
        assert "src/services/task_service.py" in files

        # API
        assert "src/api/dependencies.py" in files
        assert "src/api/routes/task.py" in files
        assert "src/main.py" in files

        # Config files
        assert "requirements.txt" in files
        assert ".env.example" in files
        assert "README.md" in files

    @pytest.mark.asyncio
    async def test_generated_files_have_correct_content(self):
        """Test that generated files contain expected code patterns"""
        files = await self.service.generate_modular_app(self.spec)

        # Config should have pydantic-settings
        config = files["src/core/config.py"]
        assert "class Settings(BaseSettings):" in config
        assert "database_url:" in config

        # Database should have async engine
        database = files["src/core/database.py"]
        assert "create_async_engine" in database
        assert "async def get_db()" in database

        # Schemas should have strict mode
        schemas = files["src/models/schemas.py"]
        assert "ConfigDict(strict=True)" in schemas
        assert "class TaskCreate(" in schemas
        assert "class TaskUpdate(" in schemas

        # Entities should have timezone-aware datetimes
        entities = files["src/models/entities.py"]
        assert "DateTime(timezone=True)" in entities
        assert "datetime.now(timezone.utc)" in entities
        assert "class TaskEntity(Base):" in entities

        # Repository should have CRUD
        repository = files["src/repositories/task_repository.py"]
        assert "async def create(" in repository
        assert "async def get(" in repository
        assert "async def list(" in repository
        assert "async def update(" in repository
        assert "async def delete(" in repository

        # Service should use repository
        service = files["src/services/task_service.py"]
        assert "TaskRepository" in service
        assert "model_validate" in service
        assert "class TaskService:" in service

        # Routes should use service
        routes = files["src/api/routes/task.py"]
        assert "@router.post(" in routes
        assert "@router.get(" in routes
        assert "@router.put(" in routes
        assert "@router.delete(" in routes
        assert "Depends(get_task_service)" in routes

    @pytest.mark.asyncio
    async def test_multi_entity_generation(self):
        """Test generation with multiple entities"""
        # Add User entity
        user_entity = MockEntity(
            name="User",
            snake_name="user",
            fields=[
                MockField(name="id", type="uuid", primary_key=True),
                MockField(name="email", type="email", required=True, unique=True),
                MockField(name="name", type="string", required=True),
                MockField(name="is_active", type="boolean", required=True, default="True"),
            ]
        )

        user_endpoints = [
            MockEndpoint("User", "create", "POST", "/users"),
            MockEndpoint("User", "read", "GET", "/users/{id}"),
            MockEndpoint("User", "list", "GET", "/users"),
        ]

        multi_spec = MockSpecRequirements(
            entities=[self.task_entity, user_entity],
            endpoints=self.task_endpoints + user_endpoints
        )

        files = await self.service.generate_modular_app(multi_spec)

        # Should have files for both entities
        assert "src/repositories/task_repository.py" in files
        assert "src/repositories/user_repository.py" in files
        assert "src/services/task_service.py" in files
        assert "src/services/user_service.py" in files
        assert "src/api/routes/task.py" in files
        assert "src/api/routes/user.py" in files

        # Dependencies should include both
        deps = files["src/api/dependencies.py"]
        assert "TaskRepository" in deps
        assert "UserRepository" in deps
        assert "TaskService" in deps
        assert "UserService" in deps

        # Main should include both routers
        main = files["src/main.py"]
        assert "from src.api.routes import task" in main
        assert "from src.api.routes import user" in main
        assert "app.include_router(task.router)" in main
        assert "app.include_router(user.router)" in main

    @pytest.mark.asyncio
    async def test_generated_code_is_syntactically_valid_python(self):
        """Test that all generated Python files are syntactically valid"""
        files = await self.service.generate_modular_app(self.spec)

        python_files = [
            path for path in files.keys()
            if path.endswith('.py')
        ]

        for file_path in python_files:
            code = files[file_path]

            # Try to compile the code
            try:
                compile(code, file_path, 'exec')
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {file_path}: {e}")

    @pytest.mark.asyncio
    async def test_separation_of_concerns_maintained(self):
        """Test that separation of concerns is maintained across layers"""
        files = await self.service.generate_modular_app(self.spec)

        # Models should not have async functions
        schemas = files["src/models/schemas.py"]
        entities = files["src/models/entities.py"]
        assert "async def" not in schemas
        assert "async def" not in entities

        # Repositories should not have HTTPException
        repository = files["src/repositories/task_repository.py"]
        assert "HTTPException" not in repository
        assert "select(" in repository  # Should have SQL

        # Services should not have SQL
        service = files["src/services/task_service.py"]
        assert "select(" not in service
        assert "TaskRepository" in service  # Should use repository

        # Routes should not have SQL
        routes = files["src/api/routes/task.py"]
        assert "select(" not in routes
        assert "HTTPException" in routes  # Should have error handling
        assert "TaskService" in routes  # Should use service

    @pytest.mark.asyncio
    async def test_requirements_txt_has_all_dependencies(self):
        """Test that requirements.txt contains necessary dependencies"""
        files = await self.service.generate_modular_app(self.spec)
        requirements = files["requirements.txt"]

        required_packages = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "asyncpg",
            "pydantic-settings",
            "alembic"
        ]

        for package in required_packages:
            assert package in requirements, f"Missing package: {package}"

    @pytest.mark.asyncio
    async def test_env_example_has_required_vars(self):
        """Test that .env.example has required environment variables"""
        files = await self.service.generate_modular_app(self.spec)
        env_example = files[".env.example"]

        required_vars = [
            "APP_NAME",
            "DATABASE_URL",
            "LOG_LEVEL"
        ]

        for var in required_vars:
            assert var in env_example, f"Missing env var: {var}"

    @pytest.mark.asyncio
    async def test_readme_has_setup_instructions(self):
        """Test that README has setup and usage instructions"""
        files = await self.service.generate_modular_app(self.spec)
        readme = files["README.md"]

        assert "Quick Start" in readme or "Installation" in readme
        assert "uvicorn" in readme or "python" in readme
        assert "API Documentation" in readme or "docs" in readme


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
