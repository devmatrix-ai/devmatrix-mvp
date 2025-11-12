"""Tests for Neo4j Client - 100% Coverage Required"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from contextlib import asynccontextmanager
from src.neo4j_client import Neo4jClient


class TestNeo4jClientInit:
    """Test Neo4jClient initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        client = Neo4jClient()
        assert client.uri == "bolt://localhost:7687"
        assert client.user == "neo4j"
        assert client.password == "devmatrix123"
        assert client.driver is None

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        client = Neo4jClient(
            uri="bolt://custom:7687",
            user="custom_user",
            password="custom_pass"
        )
        assert client.uri == "bolt://custom:7687"
        assert client.user == "custom_user"
        assert client.password == "custom_pass"


class TestNeo4jClientConnection:
    """Test Neo4j connection methods"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection"""
        client = Neo4jClient()

        with patch('src.neo4j_client.AsyncGraphDatabase.driver') as mock_driver_class:
            mock_driver = AsyncMock()
            mock_session = AsyncMock()
            mock_session.run = AsyncMock(return_value=None)

            # Create proper async context manager
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session

            mock_driver.session = mock_session_context
            mock_driver_class.return_value = mock_driver

            result = await client.connect()

            assert result is True
            assert client.driver is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure"""
        client = Neo4jClient()

        with patch('src.neo4j_client.AsyncGraphDatabase.driver') as mock_driver:
            mock_driver.side_effect = Exception("Connection failed")

            result = await client.connect()

            assert result is False

    @pytest.mark.asyncio
    async def test_close_with_driver(self):
        """Test closing connection"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        client.driver = mock_driver

        await client.close()

        mock_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_driver(self):
        """Test close when no driver exists"""
        client = Neo4jClient()
        client.driver = None

        await client.close()

    @pytest.mark.asyncio
    async def test_connect_verification_failure(self):
        """Test connection success but verification fails"""
        client = Neo4jClient()

        with patch('src.neo4j_client.AsyncGraphDatabase.driver') as mock_driver_class:
            mock_driver = AsyncMock()
            mock_session = AsyncMock()
            mock_session.run = AsyncMock(side_effect=Exception("Verification failed"))

            @asynccontextmanager
            async def mock_session_context():
                yield mock_session

            mock_driver.session = mock_session_context
            mock_driver_class.return_value = mock_driver

            result = await client.connect()

            assert result is False
            assert client.driver is not None


class TestNeo4jClientSchema:
    """Test schema initialization"""

    @pytest.mark.asyncio
    async def test_init_schema_success(self):
        """Test successful schema initialization"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=None)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        results = await client.init_schema()

        assert results["template_id_constraint"] is True
        assert results["component_id_constraint"] is True
        assert results["trezo_index"] is True
        assert results["precision_index"] is True

    @pytest.mark.asyncio
    async def test_init_schema_no_driver(self):
        """Test schema init with no driver"""
        client = Neo4jClient()
        client.driver = None

        results = await client.init_schema()

        assert results == {}

    @pytest.mark.asyncio
    async def test_init_schema_partial_failure(self):
        """Test schema init when some constraints fail"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        call_count = [0]

        async def run_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call fails
                raise Exception("Already exists")
            return None

        mock_session.run = AsyncMock(side_effect=run_side_effect)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        results = await client.init_schema()

        assert results["template_id_constraint"] is True
        assert results["component_id_constraint"] is False
        assert results["trezo_index"] is True
        assert results["precision_index"] is True

    @pytest.mark.asyncio
    async def test_init_schema_all_constraints_fail(self):
        """Test schema init when all constraints fail"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Database error"))

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        results = await client.init_schema()

        assert results["template_id_constraint"] is False
        assert results["component_id_constraint"] is False
        assert results["trezo_index"] is False
        assert results["precision_index"] is False


class TestNeo4jClientTemplates:
    """Test template operations"""

    @pytest.mark.asyncio
    async def test_create_template_success(self):
        """Test successful template creation"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"template_id": "temp_123"})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        template_data = {
            "id": "temp_123",
            "name": "JWT Auth",
            "category": "auth",
            "framework": "fastapi",
            "precision": 0.99,
            "code": "def jwt_auth(): pass",
            "description": "JWT authentication service"
        }

        result = await client.create_template(template_data)

        assert result == "temp_123"

    @pytest.mark.asyncio
    async def test_create_template_no_driver(self):
        """Test template creation without driver"""
        client = Neo4jClient()
        client.driver = None

        template_data = {
            "id": "temp_123",
            "name": "JWT Auth",
            "category": "auth",
            "framework": "fastapi",
            "precision": 0.99,
            "code": "def jwt_auth(): pass",
            "description": "JWT authentication service"
        }

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_template(template_data)

    @pytest.mark.asyncio
    async def test_create_template_failure(self):
        """Test template creation failure"""
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

        template_data = {
            "id": "temp_123",
            "name": "JWT Auth",
            "category": "auth",
            "framework": "fastapi",
            "precision": 0.99,
            "code": "def jwt_auth(): pass",
            "description": "JWT authentication service"
        }

        result = await client.create_template(template_data)

        assert result is None


class TestNeo4jClientComponents:
    """Test component operations"""

    @pytest.mark.asyncio
    async def test_create_component_success(self):
        """Test successful component creation"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"component_id": "comp_123"})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        component_data = {
            "id": "comp_123",
            "name": "DataTable",
            "category": "ui",
            "source": "trezo",
            "precision": 0.95,
            "code": "<DataTable />",
            "features": ["sorting", "filtering"]
        }

        result = await client.create_component(component_data)

        assert result == "comp_123"

    @pytest.mark.asyncio
    async def test_create_component_no_driver(self):
        """Test component creation without driver"""
        client = Neo4jClient()
        client.driver = None

        component_data = {
            "id": "comp_123",
            "name": "DataTable",
            "category": "ui",
            "source": "trezo",
            "precision": 0.95,
            "code": "<DataTable />",
            "features": ["sorting", "filtering"]
        }

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.create_component(component_data)

    @pytest.mark.asyncio
    async def test_find_component_by_features_success(self):
        """Test successful component search"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {
            "id": "comp_123",
            "name": "DataTable",
            "precision": 0.95,
            "code": "<DataTable />",
            "features": ["sorting"]
        }
        mock_result.single = AsyncMock(return_value=mock_record)

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.find_component_by_features(
            category="ui",
            features=["sorting", "filtering"],
            source="trezo"
        )

        assert result is not None
        assert result["id"] == "comp_123"
        assert result["name"] == "DataTable"

    @pytest.mark.asyncio
    async def test_find_component_by_features_not_found(self):
        """Test component search with no results"""
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

        result = await client.find_component_by_features(
            category="ui",
            features=["sorting"]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_component_by_features_without_source(self):
        """Test component search without source filter"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {
            "id": "comp_456",
            "name": "CustomTable",
            "precision": 0.90,
            "code": "<CustomTable />",
            "features": ["sorting"]
        }
        mock_result.single = AsyncMock(return_value=mock_record)

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.find_component_by_features(
            category="ui",
            features=["sorting"]
        )

        assert result is not None
        assert result["id"] == "comp_456"

    @pytest.mark.asyncio
    async def test_find_component_no_driver(self):
        """Test component search without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.find_component_by_features(category="ui", features=["sorting"])


class TestNeo4jClientStats:
    """Test statistics methods"""

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Test getting database statistics"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        mock_result_templates = AsyncMock()
        mock_result_templates.single = AsyncMock(return_value={"count": 30})

        mock_result_components = AsyncMock()
        mock_result_components.single = AsyncMock(return_value={"count": 380})

        mock_result_trezo = AsyncMock()
        mock_result_trezo.single = AsyncMock(return_value={"count": 380})

        mock_session.run = AsyncMock(
            side_effect=[
                mock_result_templates,
                mock_result_components,
                mock_result_trezo,
            ]
        )

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        stats = await client.get_stats()

        assert stats["templates"] == 30
        assert stats["components"] == 380
        assert stats["trezo_components"] == 380

    @pytest.mark.asyncio
    async def test_get_stats_no_driver(self):
        """Test getting stats without driver"""
        client = Neo4jClient()
        client.driver = None

        with pytest.raises(RuntimeError, match="Driver not initialized"):
            await client.get_stats()


class TestNeo4jClientVerify:
    """Test connection verification"""

    @pytest.mark.asyncio
    async def test_verify_connection_success(self):
        """Test successful connection verification"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"test": 1})

        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.verify_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_connection_failure(self):
        """Test connection verification failure"""
        client = Neo4jClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Connection failed"))

        @asynccontextmanager
        async def mock_session_context():
            yield mock_session

        mock_driver.session = mock_session_context
        client.driver = mock_driver

        result = await client.verify_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_connection_no_driver(self):
        """Test verification with no driver"""
        client = Neo4jClient()
        client.driver = None

        result = await client.verify_connection()

        assert result is False
