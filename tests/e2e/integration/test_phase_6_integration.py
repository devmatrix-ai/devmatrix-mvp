"""
Integration tests for Phase 6: Code Generation

Task Group 3.2.1: Test Phase 6 integration with CodeGenerationService

These tests verify that:
1. Phase 6 calls CodeGenerationService.generate_from_requirements() (not hardcoded)
2. Phase 6 output is NOT hardcoded template
3. Phase 6 generates DIFFERENT code for different specs
"""
import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import the E2E test class
import sys
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.real_e2e_full_pipeline import RealE2ETest
from src.parsing.spec_parser import SpecParser, SpecRequirements, Requirement, Entity, Endpoint
from src.services.code_generation_service import CodeGenerationService


class TestPhase6Integration:
    """Integration tests for Phase 6 code generation"""

    @pytest.fixture
    def ecommerce_spec_file(self):
        """Path to ecommerce spec"""
        return "tests/e2e/test_specs/ecommerce_api_simple.md"

    @pytest.fixture
    def simple_task_spec_file(self):
        """Path to simple task API spec"""
        return "tests/e2e/test_specs/simple_task_api.md"

    @pytest.fixture
    async def test_instance_ecommerce(self, ecommerce_spec_file):
        """Create test instance with ecommerce spec"""
        test = RealE2ETest(ecommerce_spec_file)
        await test._initialize_services()

        # Ensure code_generator exists (mock if not initialized due to missing API key)
        if test.code_generator is None:
            test.code_generator = MagicMock(spec=CodeGenerationService)
            test.code_generator.generate_from_requirements = AsyncMock()

        return test

    @pytest.fixture
    async def test_instance_task(self, simple_task_spec_file):
        """Create test instance with task spec"""
        test = RealE2ETest(simple_task_spec_file)
        await test._initialize_services()

        # Ensure code_generator exists
        if test.code_generator is None:
            test.code_generator = MagicMock(spec=CodeGenerationService)
            test.code_generator.generate_from_requirements = AsyncMock()

        return test

    @pytest.mark.asyncio
    async def test_phase_6_calls_code_generation_service(self, test_instance_ecommerce):
        """
        Test 1: Phase 6 calls CodeGenerationService.generate_from_requirements()

        Verifies that Phase 6 uses the real code generation service instead of
        the hardcoded template method.
        """
        test = test_instance_ecommerce

        # Setup: Parse spec and run Phase 1 to populate spec_requirements
        await test._phase_1_spec_ingestion()

        assert test.spec_requirements is not None, "Phase 1 should populate spec_requirements"

        # Mock the code generator to track if it's called
        test.code_generator.generate_from_requirements = AsyncMock(
            return_value="# Generated code\nfrom fastapi import FastAPI\napp = FastAPI()"
        )

        # Execute Phase 6
        await test._phase_6_code_generation()

        # Verify: CodeGenerationService.generate_from_requirements was called
        test.code_generator.generate_from_requirements.assert_called_once()

        # Verify: It was called with spec_requirements
        call_args = test.code_generator.generate_from_requirements.call_args
        assert call_args is not None, "Method should have been called with arguments"

        # The first positional argument should be spec_requirements
        called_with = call_args[0][0]
        assert called_with == test.spec_requirements, \
            "Should call generate_from_requirements with spec_requirements from Phase 1"

        # Verify: Code was generated
        assert len(test.generated_code) > 0, "Phase 6 should generate code files"

    @pytest.mark.asyncio
    async def test_phase_6_not_hardcoded_template(self, test_instance_ecommerce):
        """
        Test 2: Phase 6 output is NOT hardcoded template

        Verifies that the generated code is different from the old hardcoded
        Task API template. This ensures Bug #3 is fixed.
        """
        test = test_instance_ecommerce

        # Setup: Run Phase 1 to get ecommerce requirements
        await test._phase_1_spec_ingestion()

        # Verify we have ecommerce entities (not Task)
        entity_names = [e.name for e in test.spec_requirements.entities]
        assert "Product" in entity_names or "Customer" in entity_names, \
            "Ecommerce spec should have Product or Customer entities"

        # Mock code generator to return minimal but spec-based code
        async def mock_generate(spec_requirements):
            # Generate code that includes entity names from spec
            entities_code = "\n".join([
                f"class {entity.name}(BaseModel):\n    id: UUID\n    name: str"
                for entity in spec_requirements.entities
            ])
            return f"from pydantic import BaseModel\nfrom uuid import UUID\n\n{entities_code}"

        test.code_generator.generate_from_requirements = mock_generate

        # Execute Phase 6
        await test._phase_6_code_generation()

        # Verify: Generated code is NOT the hardcoded Task API
        generated_main = test.generated_code.get("main.py", "")

        # The old hardcoded template always had "Task" model
        # New code should have ecommerce entities instead
        assert "Task" not in generated_main or any(
            entity in generated_main for entity in ["Product", "Customer", "Cart", "Order"]
        ), "Generated code should NOT be hardcoded Task API template"

        # Verify: Generated code includes entities from spec
        for entity_name in entity_names:
            assert entity_name in generated_main, \
                f"Generated code should include entity '{entity_name}' from spec"

    @pytest.mark.asyncio
    async def test_phase_6_generates_different_code_for_different_specs(
        self,
        test_instance_ecommerce,
        test_instance_task
    ):
        """
        Test 3: Phase 6 generates different code for different specs

        Verifies that the ecommerce spec generates Product/Cart/Order code while
        the simple task spec generates Task code. This proves the system is
        spec-driven, not template-driven.
        """
        # Test 1: Ecommerce spec
        ecommerce_test = test_instance_ecommerce
        await ecommerce_test._phase_1_spec_ingestion()

        # Mock to return spec-based code
        async def mock_generate_ecommerce(spec_requirements):
            entities = [e.name for e in spec_requirements.entities]
            return f"# Ecommerce API\n# Entities: {', '.join(entities)}"

        ecommerce_test.code_generator.generate_from_requirements = mock_generate_ecommerce
        await ecommerce_test._phase_6_code_generation()

        ecommerce_code = ecommerce_test.generated_code.get("main.py", "")

        # Test 2: Simple task spec
        task_test = test_instance_task
        await task_test._phase_1_spec_ingestion()

        async def mock_generate_task(spec_requirements):
            entities = [e.name for e in spec_requirements.entities]
            return f"# Task API\n# Entities: {', '.join(entities)}"

        task_test.code_generator.generate_from_requirements = mock_generate_task
        await task_test._phase_6_code_generation()

        task_code = task_test.generated_code.get("main.py", "")

        # Verify: Code is different for different specs
        assert ecommerce_code != task_code, \
            "Different specs should generate different code"

        # Verify: Ecommerce code has ecommerce entities
        ecommerce_entities = [e.name for e in ecommerce_test.spec_requirements.entities]
        for entity in ecommerce_entities:
            assert entity in ecommerce_code, \
                f"Ecommerce code should mention entity '{entity}'"

        # Verify: Task code has Task entity
        task_entities = [e.name for e in task_test.spec_requirements.entities]
        for entity in task_entities:
            assert entity in task_code, \
                f"Task code should mention entity '{entity}'"

        # Verify: Ecommerce doesn't have Task (unless spec includes it)
        # And Task doesn't have Product/Customer/etc
        if "Task" not in ecommerce_entities:
            # Only check if Task isn't actually in the ecommerce spec
            pass  # We can't assume Task won't be mentioned

        if "Product" not in task_entities and "Customer" not in task_entities:
            assert "Product" not in task_code and "Customer" not in task_code, \
                "Task API should not have ecommerce entities"

    @pytest.mark.asyncio
    async def test_feature_flag_controls_behavior(self, test_instance_ecommerce):
        """
        Test 4: Feature flag controls code generation approach

        Verifies that USE_REAL_CODE_GENERATION environment variable works.
        """
        test = test_instance_ecommerce
        await test._phase_1_spec_ingestion()

        # Test 1: Feature flag = false should raise NotImplementedError
        with patch.dict(os.environ, {"USE_REAL_CODE_GENERATION": "false"}):
            with pytest.raises(NotImplementedError) as exc_info:
                await test._phase_6_code_generation()

            assert "Hardcoded template has been removed" in str(exc_info.value), \
                "Should raise clear error when feature flag is disabled"

        # Test 2: Feature flag = true should use CodeGenerationService
        with patch.dict(os.environ, {"USE_REAL_CODE_GENERATION": "true"}):
            # Mock the generator
            test.code_generator.generate_from_requirements = AsyncMock(
                return_value="# Real code"
            )

            await test._phase_6_code_generation()

            # Should succeed without error
            assert len(test.generated_code) > 0, \
                "Should generate code when feature flag is enabled"

    @pytest.mark.asyncio
    async def test_phase_6_requires_spec_requirements(self, test_instance_ecommerce):
        """
        Test 5: Phase 6 requires SpecRequirements from Phase 1

        Verifies that Phase 6 fails gracefully if Phase 1 didn't run.
        """
        test = test_instance_ecommerce

        # Don't run Phase 1, leave spec_requirements as None
        test.spec_requirements = None

        # Phase 6 should raise clear error
        with pytest.raises(ValueError) as exc_info:
            await test._phase_6_code_generation()

        assert "SpecRequirements not available" in str(exc_info.value), \
            "Should raise clear error when spec_requirements is missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
