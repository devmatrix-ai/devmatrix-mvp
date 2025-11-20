"""
Integration tests for Phase 1 SpecParser integration into E2E pipeline

Tests verify that Phase 1 now uses SpecParser to extract structured requirements
instead of simple line extraction, fixing the parser bug.

Target: Phase 1 outputs SpecRequirements with 17 functional requirements, 4 entities, 17 endpoints
"""
import pytest
from pathlib import Path
from src.parsing.spec_parser import SpecParser, SpecRequirements


class TestPhase1SpecParserIntegration:
    """Integration tests for Phase 1 with SpecParser"""

    @pytest.fixture
    def ecommerce_spec_path(self):
        return Path("/home/kwar/code/agentic-ai/tests/e2e/test_specs/ecommerce_api_simple.md")

    @pytest.fixture
    def simple_task_spec_path(self):
        return Path("/home/kwar/code/agentic-ai/tests/e2e/test_specs/simple_task_api.md")

    def test_phase1_ecommerce_spec_returns_structured_requirements(self, ecommerce_spec_path):
        """
        Test Phase 1 integration with ecommerce spec extracts all requirements

        BEFORE: Phase 1 extracted 55 lines (wrong - only list items)
        AFTER: Phase 1 extracts 17 functional + 7 non-functional requirements, 4 entities, 17 endpoints (structured)
        """
        # Simulate Phase 1 behavior with SpecParser
        parser = SpecParser()
        result = parser.parse(ecommerce_spec_path)

        # Verify structured output instead of string list
        assert isinstance(result, SpecRequirements), "Phase 1 should output SpecRequirements dataclass"

        # Verify all functional requirements extracted (17 functional + 7 non-functional = 24 total)
        functional_reqs = [r for r in result.requirements if r.type == "functional"]
        non_functional_reqs = [r for r in result.requirements if r.type == "non_functional"]

        assert len(functional_reqs) == 17, (
            f"Phase 1 should extract 17 functional requirements, got {len(functional_reqs)}"
        )
        assert len(non_functional_reqs) == 7, (
            f"Phase 1 should extract 7 non-functional requirements, got {len(non_functional_reqs)}"
        )
        assert len(result.requirements) == 24, (
            f"Phase 1 should extract 24 total requirements (17 F + 7 NF), got {len(result.requirements)}"
        )

        # Verify all entities extracted
        assert len(result.entities) == 4, (
            f"Phase 1 should extract 4 entities (Product, Customer, Cart, Order), got {len(result.entities)}"
        )
        entity_names = {e.name for e in result.entities}
        assert entity_names == {"Product", "Customer", "Cart", "Order"}

        # Verify all endpoints extracted
        assert len(result.endpoints) == 17, (
            f"Phase 1 should extract 17 endpoints, got {len(result.endpoints)}"
        )

        # Verify metadata includes counts
        assert result.metadata['functional_count'] == 17
        assert result.metadata['non_functional_count'] == 7
        assert result.metadata['total_requirements'] == 24
        assert result.metadata['entity_count'] == 4
        assert result.metadata['endpoint_count'] == 17

        # Verify checkpoint data structure compatibility
        # Phase 1 should be able to store this in checkpoint
        checkpoint_data = {
            "spec_requirements": {
                "requirements": [
                    {"id": r.id, "type": r.type, "description": r.description}
                    for r in result.requirements
                ],
                "entities": [
                    {"name": e.name, "field_count": len(e.fields)}
                    for e in result.entities
                ],
                "endpoints": [
                    {"method": ep.method, "path": ep.path, "entity": ep.entity}
                    for ep in result.endpoints
                ],
                "metadata": result.metadata
            }
        }
        assert checkpoint_data is not None
        assert len(checkpoint_data["spec_requirements"]["requirements"]) == 24

    def test_phase1_simple_task_api_regression(self, simple_task_spec_path):
        """
        Test Phase 1 integration with simple_task_api maintains baseline

        Regression test: Simple task API should still work correctly
        Expected: 4 functional requirements, 1 entity (Task), 5 endpoints
        """
        parser = SpecParser()
        result = parser.parse(simple_task_spec_path)

        # Verify structured output
        assert isinstance(result, SpecRequirements)

        # Verify functional requirements
        functional_reqs = [r for r in result.requirements if r.type == "functional"]
        assert len(functional_reqs) >= 4, (
            f"Simple task API should have at least 4 CRUD requirements, got {len(functional_reqs)}"
        )

        # Verify Task entity
        task_entities = [e for e in result.entities if e.name == "Task"]
        assert len(task_entities) == 1, "Should find Task entity"

        # Verify Task entity has required fields
        task_entity = task_entities[0]
        field_names = {f.name for f in task_entity.fields}
        assert "id" in field_names
        assert "title" in field_names
        assert "completed" in field_names or "status" in field_names

        # Verify CRUD endpoints
        assert len(result.endpoints) >= 4, (
            f"Simple task API should have at least 4 CRUD endpoints, got {len(result.endpoints)}"
        )

        # Verify HTTP methods
        methods = {ep.method for ep in result.endpoints}
        assert "POST" in methods, "Should have POST (create)"
        assert "GET" in methods, "Should have GET (read/list)"

    def test_phase1_malformed_spec_error_handling(self):
        """
        Test Phase 1 handles malformed specs gracefully

        Should not crash, should return empty SpecRequirements
        """
        parser = SpecParser()

        # Create temp malformed spec
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Malformed Spec\n\nNo requirements here!\n")
            malformed_path = Path(f.name)

        try:
            result = parser.parse(malformed_path)

            # Should return SpecRequirements even if empty
            assert isinstance(result, SpecRequirements)

            # May have 0 requirements for truly malformed spec
            # This is acceptable - no crash is the important part
            assert isinstance(result.requirements, list)
            assert isinstance(result.entities, list)
            assert isinstance(result.endpoints, list)

        finally:
            # Cleanup
            malformed_path.unlink()
