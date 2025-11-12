"""Integration Tests for Neo4j Client - Real Database Connection"""

import pytest
import asyncio
from src.neo4j_client import Neo4jClient


@pytest.mark.asyncio
class TestNeo4jIntegration:
    """Integration tests against real Neo4j instance"""

    @pytest.fixture
    async def client(self):
        """Create client and setup"""
        client = Neo4jClient(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="devmatrix123"
        )
        yield client
        # Cleanup
        if client.driver:
            await client.close()

    async def test_real_connection(self, client):
        """Test connecting to real Neo4j instance"""
        result = await client.connect()
        assert result is True
        assert client.driver is not None

    async def test_real_verification(self, client):
        """Test connection verification against real instance"""
        await client.connect()
        result = await client.verify_connection()
        assert result is True

    async def test_real_schema_initialization(self, client):
        """Test schema creation against real instance"""
        await client.connect()
        results = await client.init_schema()

        # All constraints/indexes should be created successfully
        assert results["template_id_constraint"] is True
        assert results["component_id_constraint"] is True
        assert results["trezo_index"] is True
        assert results["precision_index"] is True

    async def test_real_create_and_find_template(self, client):
        """Test creating and finding templates in real database"""
        await client.connect()
        await client.init_schema()

        # Create template
        template_data = {
            "id": "test_jwt_template_001",
            "name": "JWT Auth Template",
            "category": "auth",
            "framework": "fastapi",
            "precision": 0.98,
            "code": "async def verify_token(token: str): pass",
            "description": "JWT authentication template"
        }

        template_id = await client.create_template(template_data)
        assert template_id == "test_jwt_template_001"

        # Verify template was created by getting stats
        stats = await client.get_stats()
        assert stats["templates"] >= 1

    async def test_real_create_and_find_component(self, client):
        """Test creating and finding components in real database"""
        await client.connect()
        await client.init_schema()

        # Create component
        component_data = {
            "id": "test_datatable_comp_001",
            "name": "DataTable Component",
            "category": "ui",
            "source": "trezo",
            "precision": 0.96,
            "code": "<DataTable columns={columns} data={data} />",
            "features": ["sorting", "filtering", "pagination"]
        }

        comp_id = await client.create_component(component_data)
        assert comp_id == "test_datatable_comp_001"

        # Find component by features
        found = await client.find_component_by_features(
            category="ui",
            features=["sorting"],
            source="trezo"
        )
        assert found is not None
        assert found["id"] == "test_datatable_comp_001"

    async def test_real_multiple_templates(self, client):
        """Test creating multiple templates"""
        await client.connect()
        await client.init_schema()

        template_ids = []
        for i in range(5):
            template_data = {
                "id": f"test_template_{i:03d}",
                "name": f"Template {i}",
                "category": "auth" if i < 2 else "api",
                "framework": "fastapi",
                "precision": 0.90 + (i * 0.01),
                "code": f"async def func_{i}(): pass",
                "description": f"Test template {i}"
            }
            template_id = await client.create_template(template_data)
            template_ids.append(template_id)

        assert len(template_ids) == 5
        assert all(tid is not None for tid in template_ids)

    async def test_real_multiple_components(self, client):
        """Test creating multiple components"""
        await client.connect()
        await client.init_schema()

        component_ids = []
        features_list = [
            ["sorting"],
            ["filtering"],
            ["pagination"],
            ["sorting", "filtering"],
            ["sorting", "filtering", "pagination"]
        ]

        for i, features in enumerate(features_list):
            component_data = {
                "id": f"test_component_{i:03d}",
                "name": f"Component {i}",
                "category": "ui",
                "source": "trezo",
                "precision": 0.85 + (i * 0.02),
                "code": f"<Component{i} />",
                "features": features
            }
            comp_id = await client.create_component(component_data)
            component_ids.append(comp_id)

        assert len(component_ids) == 5
        assert all(cid is not None for cid in component_ids)

    async def test_real_stats(self, client):
        """Test statistics retrieval from real database"""
        await client.connect()
        await client.init_schema()

        # Create some data
        await client.create_template({
            "id": "stats_template_001",
            "name": "Stats Template",
            "category": "auth",
            "framework": "fastapi",
            "precision": 0.95,
            "code": "async def test(): pass",
            "description": "Test for stats"
        })

        await client.create_component({
            "id": "stats_component_001",
            "name": "Stats Component",
            "category": "ui",
            "source": "trezo",
            "precision": 0.92,
            "code": "<Stats />",
            "features": ["display"]
        })

        # Get stats
        stats = await client.get_stats()
        assert isinstance(stats, dict)
        assert "templates" in stats
        assert "components" in stats
        assert "trezo_components" in stats
        assert stats["templates"] >= 1
        assert stats["components"] >= 1
        assert stats["trezo_components"] >= 1

    async def test_close_connection(self, client):
        """Test closing real connection"""
        await client.connect()
        assert client.driver is not None
        await client.close()
        # Should not raise an error

    async def test_connection_uri_port(self, client):
        """Test connection using correct URI and port"""
        assert client.uri == "bolt://localhost:7687"
        assert client.user == "neo4j"
        assert client.password == "devmatrix123"

    async def test_custom_connection_params(self):
        """Test client with custom connection parameters"""
        client = Neo4jClient(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="devmatrix123"
        )
        assert client.uri == "bolt://localhost:7687"
        assert client.user == "neo4j"
        assert client.password == "devmatrix123"
        await client.close()

    async def test_sequential_operations(self, client):
        """Test sequential operations on real database"""
        await client.connect()
        await client.init_schema()

        # Create template
        template_id = await client.create_template({
            "id": "seq_test_001",
            "name": "Sequential Test",
            "category": "test",
            "framework": "fastapi",
            "precision": 0.95,
            "code": "test",
            "description": "test"
        })
        assert template_id is not None

        # Create component
        component_id = await client.create_component({
            "id": "seq_comp_001",
            "name": "Sequential Component",
            "category": "ui",
            "source": "trezo",
            "precision": 0.90,
            "code": "test",
            "features": ["test"]
        })
        assert component_id is not None

        # Get stats
        stats = await client.get_stats()
        assert stats["templates"] >= 1
        assert stats["components"] >= 1

        # Verify connection still works
        result = await client.verify_connection()
        assert result is True


@pytest.mark.asyncio
async def test_neo4j_integration_sanity():
    """Quick sanity check that Neo4j is running"""
    client = Neo4jClient()
    try:
        result = await client.connect()
        assert result is True
        await client.close()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
