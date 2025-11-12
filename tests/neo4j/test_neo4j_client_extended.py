"""Extended Tests for Neo4j Client - New Methods with 100% Coverage"""

import pytest
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager

from src.neo4j_client import Neo4jClient


class TestNeo4jClientRelationships:
    """Test relationship creation methods"""

    @pytest.mark.asyncio
    async def test_create_relationship_success(self):
        """Test successful relationship creation"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 1})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.create_relationship(
            source_label="Template",
            source_id="jwt_v1",
            target_label="Category",
            target_id="auth",
            relationship_type="BELONGS_TO",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_create_relationship_with_properties(self):
        """Test relationship creation with properties"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 1})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.create_relationship(
            source_label="Template",
            source_id="jwt_v1",
            target_label="Template",
            target_id="jwt_v2",
            relationship_type="REPLACED_BY",
            properties={"reason": "improved", "version": 2},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_create_relationship_failure(self):
        """Test relationship creation failure"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 0})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.create_relationship(
            source_label="Template",
            source_id="nonexistent",
            target_label="Category",
            target_id="auth",
            relationship_type="BELONGS_TO",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_create_relationship_no_driver(self):
        """Test create relationship without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_relationship(
                source_label="Template",
                source_id="jwt_v1",
                target_label="Category",
                target_id="auth",
                relationship_type="BELONGS_TO",
            )


class TestNeo4jClientTemplateOperations:
    """Test template-specific operations"""

    @pytest.mark.asyncio
    async def test_batch_create_templates_success(self):
        """Test batch template creation"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"created": 5})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        templates = [
            {
                "id": f"template_{i}",
                "name": f"Template {i}",
                "category": "auth",
                "subcategory": "jwt",
                "framework": "fastapi",
                "language": "python",
                "precision": 0.95,
                "code": "code",
                "description": "desc",
                "complexity": "medium",
                "version": 1,
                "status": "active",
                "source": "internal",
            }
            for i in range(5)
        ]

        result = await client.batch_create_templates(templates)

        assert result["created"] == 5
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_batch_create_templates_empty(self):
        """Test batch creation with empty list"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"created": 0})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.batch_create_templates([])

        assert result["created"] == 0
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_find_similar_templates_success(self):
        """Test finding similar templates"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        similar_template = {
            "id": "jwt_v2",
            "name": "JWT V2",
            "precision": 0.96,
        }
        mock_record = {"template": similar_template, "score": 0.85}

        mock_session.run = AsyncMock()
        mock_session.run.return_value.__aiter__ = AsyncMock(
            return_value=iter([mock_record])
        )

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        # Mock the async iteration
        async def async_iter_mock():
            yield mock_record

        mock_session.run.return_value = async_iter_mock()

        result = await client.find_similar_templates(
            template_id="jwt_v1", limit=5, min_similarity=0.7
        )

        assert len(result) == 1
        assert result[0]["id"] == "jwt_v2"
        assert result[0]["similarity_score"] == 0.85

    @pytest.mark.asyncio
    async def test_find_similar_templates_empty(self):
        """Test find similar templates with no results"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        mock_session.run = AsyncMock()

        async def async_iter_mock():
            return
            yield  # Make it a generator

        mock_session.run.return_value = async_iter_mock()

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.find_similar_templates(
            template_id="jwt_v1", limit=5, min_similarity=0.7
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_template_with_dependencies_success(self):
        """Test getting template with all dependencies"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        full_template = {
            "template": {"id": "jwt_v1", "name": "JWT V1"},
            "category": {"id": "auth", "name": "Authentication"},
            "framework": {"id": "fastapi", "name": "FastAPI"},
            "dependencies": [{"id": "pyjwt", "name": "PyJWT"}],
            "patterns": [{"id": "ddd", "name": "Domain-Driven Design"}],
            "creator": {"id": "user_1", "name": "Admin"},
        }

        mock_result.single = AsyncMock(return_value={"full_template": full_template})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.get_template_with_dependencies("jwt_v1")

        assert result is not None
        assert result["template"]["id"] == "jwt_v1"
        assert result["category"]["name"] == "Authentication"
        assert len(result["dependencies"]) == 1

    @pytest.mark.asyncio
    async def test_get_template_with_dependencies_not_found(self):
        """Test getting template that doesn't exist"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.get_template_with_dependencies("nonexistent")

        assert result is None


class TestNeo4jClientCategoryOperations:
    """Test category-specific operations"""

    @pytest.mark.asyncio
    async def test_get_category_templates_success(self):
        """Test getting templates by category"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        template1 = {"id": "jwt_v1", "name": "JWT V1", "precision": 0.95}
        template2 = {"id": "oauth_v1", "name": "OAuth V1", "precision": 0.93}

        async def async_iter_mock():
            yield {"t": template1}
            yield {"t": template2}

        mock_session.run = AsyncMock(return_value=async_iter_mock())

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.get_category_templates("auth", status="active", limit=50)

        assert len(result) == 2
        assert result[0]["id"] == "jwt_v1"
        assert result[1]["id"] == "oauth_v1"

    @pytest.mark.asyncio
    async def test_get_category_templates_empty(self):
        """Test getting templates from empty category"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        async def async_iter_mock():
            return
            yield

        mock_session.run = AsyncMock(return_value=async_iter_mock())

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.get_category_templates("nonexistent")

        assert result == []


class TestNeo4jClientNodeCreation:
    """Test creation of support nodes (category, framework, pattern, dependency)"""

    @pytest.mark.asyncio
    async def test_create_category_success(self):
        """Test creating a category node"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"category_id": "auth"})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        category_data = {
            "id": "auth",
            "name": "Authentication",
            "icon": "🔐",
            "description": "Authentication templates",
            "order": 1,
        }

        result = await client.create_category(category_data)

        assert result == "auth"

    @pytest.mark.asyncio
    async def test_create_framework_success(self):
        """Test creating a framework node"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"framework_id": "fastapi"})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        framework_data = {
            "id": "fastapi",
            "name": "FastAPI",
            "type": "backend",
            "language": "python",
            "version_range": ">=0.95.0,<2.0",
            "ecosystem": ["pip"],
        }

        result = await client.create_framework(framework_data)

        assert result == "fastapi"

    @pytest.mark.asyncio
    async def test_create_pattern_success(self):
        """Test creating a pattern node"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"pattern_id": "ddd"})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        pattern_data = {
            "id": "ddd",
            "name": "Domain-Driven Design",
            "description": "DDD pattern",
            "category": "architectural",
            "complexity_level": 4,
            "use_cases": ["microservices", "large_projects"],
        }

        result = await client.create_pattern(pattern_data)

        assert result == "ddd"

    @pytest.mark.asyncio
    async def test_create_dependency_success(self):
        """Test creating a dependency node"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"dependency_id": "pyjwt"})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        dependency_data = {
            "id": "pyjwt",
            "name": "PyJWT",
            "language": "python",
            "version_range": ">=2.0.0,<3.0",
            "type": "runtime",
            "security_status": "secure",
        }

        result = await client.create_dependency(dependency_data)

        assert result == "pyjwt"


class TestNeo4jClientStats:
    """Test statistics and analytics methods"""

    @pytest.mark.asyncio
    async def test_get_database_stats_success(self):
        """Test getting comprehensive database statistics"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Setup multiple mock results for each query
        mock_results = [
            {"count": 30},  # Template count
            {"count": 5},   # TrezoComponent count
            {"count": 0},   # CustomComponent count
            {"count": 8},   # Pattern count
            {"count": 5},   # Framework count
            {"count": 20},  # Dependency count
            {"count": 4},   # Category count
            {"count": 0},   # MasterPlan count
            {"count": 0},   # Atom count
            {"count": 0},   # User count
            {"count": 0},   # Project count
            {"count": 50},  # Relationship count
            {"avg_precision": 0.92},  # Avg precision
        ]

        mock_session.run = AsyncMock()
        results_iter = iter(mock_results)

        async def mock_run_side_effect(*args, **kwargs):
            result_mock = AsyncMock()
            result_mock.single = AsyncMock(
                return_value=next(results_iter)
            )
            return result_mock

        mock_session.run = AsyncMock(side_effect=mock_run_side_effect)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        stats = await client.get_database_stats()

        assert stats["template_count"] == 30
        assert stats["trezocomponent_count"] == 5
        assert stats["relationship_count"] == 50
        assert stats["avg_template_precision"] == 0.92

    @pytest.mark.asyncio
    async def test_get_database_stats_empty_database(self):
        """Test getting stats from empty database"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # All counts are 0
        mock_results = [
            {"count": 0},  # Template
            {"count": 0},  # TrezoComponent
            {"count": 0},  # CustomComponent
            {"count": 0},  # Pattern
            {"count": 0},  # Framework
            {"count": 0},  # Dependency
            {"count": 0},  # Category
            {"count": 0},  # MasterPlan
            {"count": 0},  # Atom
            {"count": 0},  # User
            {"count": 0},  # Project
            {"count": 0},  # Relationships
            {"avg_precision": None},  # No avg
        ]

        results_iter = iter(mock_results)

        async def mock_run_side_effect(*args, **kwargs):
            result_mock = AsyncMock()
            result_mock.single = AsyncMock(return_value=next(results_iter))
            return result_mock

        mock_session.run = AsyncMock(side_effect=mock_run_side_effect)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        stats = await client.get_database_stats()

        assert stats["template_count"] == 0
        assert stats["relationship_count"] == 0
        assert stats["avg_template_precision"] == 0.0


class TestNeo4jClientNoDriver:
    """Test all methods fail properly when driver is not initialized"""

    @pytest.mark.asyncio
    async def test_batch_create_templates_no_driver(self):
        """Test batch template creation fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.batch_create_templates([
                {"id": "jwt_v1", "name": "JWT Auth", "category": "auth"}
            ])

    @pytest.mark.asyncio
    async def test_find_similar_templates_no_driver(self):
        """Test similar templates search fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.find_similar_templates("jwt_v1")

    @pytest.mark.asyncio
    async def test_get_template_with_dependencies_no_driver(self):
        """Test template dependency retrieval fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.get_template_with_dependencies("jwt_v1")

    @pytest.mark.asyncio
    async def test_get_category_templates_no_driver(self):
        """Test category template retrieval fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.get_category_templates("auth")

    @pytest.mark.asyncio
    async def test_create_category_no_driver(self):
        """Test category creation fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_category({"id": "auth", "name": "Auth"})

    @pytest.mark.asyncio
    async def test_create_framework_no_driver(self):
        """Test framework creation fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_framework({"id": "fastapi", "name": "FastAPI"})

    @pytest.mark.asyncio
    async def test_create_pattern_no_driver(self):
        """Test pattern creation fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_pattern({"id": "ddd", "name": "DDD"})

    @pytest.mark.asyncio
    async def test_create_dependency_no_driver(self):
        """Test dependency creation fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_dependency({"id": "jwt", "name": "JWT"})

    @pytest.mark.asyncio
    async def test_get_database_stats_no_driver(self):
        """Test database stats retrieval fails without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.get_database_stats()
