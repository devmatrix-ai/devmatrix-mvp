"""
Integration tests for Phase 6: Code Generation
Task Group 3.2.1

These tests verify that Phase 6:
- Calls CodeGenerationService.generate_from_requirements()
- Does NOT use hardcoded templates
- Generates different code for different specs
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from tests.e2e.real_e2e_full_pipeline import RealE2ETest
from src.parsing.spec_parser import SpecRequirements, Entity, Field, Endpoint, Requirement


@pytest.mark.asyncio
async def test_phase_6_calls_code_generation_service():
    """
    Test that Phase 6 calls CodeGenerationService.generate_from_requirements()
    instead of hardcoded template method
    """
    # Create test instance with simple spec
    spec_file = "tests/e2e/test_specs/simple_task_api.md"
    test = RealE2ETest(spec_file)

    # Mock the code generator to track calls
    test.code_generator = MagicMock()
    test.code_generator.generate_from_requirements = AsyncMock(return_value="""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Task API"}
""")

    # Setup Phase 1 output (structured requirements)
    test.spec_requirements = SpecRequirements(
        requirements=[
            Requirement(
                id="F1",
                type="functional",
                priority="MUST",
                description="CRUD operations for tasks",
                domain="crud",
                dependencies=[]
            )
        ],
        entities=[
            Entity(
                name="Task",
                fields=[
                    Field(name="id", type="UUID", primary_key=True, required=True),
                    Field(name="title", type="str", required=True)
                ],
                relationships=[],
                validations=[]
            )
        ],
        endpoints=[
            Endpoint(
                method="POST",
                path="/tasks",
                entity="Task",
                operation="create",
                params=[],
                business_logic=[]
            )
        ],
        business_logic=[],
        metadata={"spec_name": "simple_task_api"}
    )

    # Run Phase 6
    await test._phase_6_code_generation()

    # Verify CodeGenerationService.generate_from_requirements was called
    test.code_generator.generate_from_requirements.assert_called_once()

    # Verify it was called with SpecRequirements
    call_args = test.code_generator.generate_from_requirements.call_args
    assert call_args is not None
    assert call_args[0][0] == test.spec_requirements  # First positional arg


@pytest.mark.asyncio
async def test_phase_6_output_is_not_hardcoded_template():
    """
    Test that Phase 6 output is NOT the hardcoded Task template
    when processing an ecommerce spec
    """
    # Create test instance with ecommerce spec
    spec_file = "tests/e2e/test_specs/ecommerce_api_simple.md"
    if not Path(spec_file).exists():
        pytest.skip("Ecommerce spec not available")

    test = RealE2ETest(spec_file)

    # Mock code generator to return ecommerce-specific code
    test.code_generator = MagicMock()
    test.code_generator.generate_from_requirements = AsyncMock(return_value="""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Ecommerce API")

class Product(BaseModel):
    id: int
    name: str
    price: float

class Cart(BaseModel):
    id: int
    items: list

@app.post("/products")
async def create_product(product: Product):
    return product

@app.post("/cart/checkout")
async def checkout(cart: Cart):
    return {"status": "success"}
""")

    # Setup Phase 1 output with ecommerce entities
    test.spec_requirements = SpecRequirements(
        requirements=[
            Requirement(
                id="F1",
                type="functional",
                priority="MUST",
                description="Manage products",
                domain="crud",
                dependencies=[]
            )
        ],
        entities=[
            Entity(name="Product", fields=[], relationships=[], validations=[]),
            Entity(name="Cart", fields=[], relationships=[], validations=[])
        ],
        endpoints=[
            Endpoint(method="POST", path="/products", entity="Product", operation="create", params=[], business_logic=[]),
            Endpoint(method="POST", path="/cart/checkout", entity="Cart", operation="checkout", params=[], business_logic=[])
        ],
        business_logic=[],
        metadata={"spec_name": "ecommerce_api"}
    )

    # Run Phase 6
    await test._phase_6_code_generation()

    # Verify generated code is NOT Task template
    generated_code = test.generated_code
    assert isinstance(generated_code, dict), "Generated code should be a dict of files"

    # Check that generated code contains ecommerce entities
    all_code = "\n".join(generated_code.values())
    assert "Product" in all_code, "Generated code should contain Product entity"
    assert "Cart" in all_code, "Generated code should contain Cart entity"

    # Verify it does NOT contain hardcoded Task entity
    # (unless "task" is part of legitimate ecommerce terminology)
    assert "class Task(BaseModel)" not in all_code, "Should NOT generate Task entity for ecommerce spec"


@pytest.mark.asyncio
async def test_phase_6_generates_different_code_for_different_specs():
    """
    Test that Phase 6 generates different code for different specifications
    """
    # Test 1: Simple task API
    task_test = RealE2ETest("tests/e2e/test_specs/simple_task_api.md")
    task_test.code_generator = MagicMock()
    task_test.code_generator.generate_from_requirements = AsyncMock(return_value="""
from fastapi import FastAPI
class Task(BaseModel):
    pass
""")

    task_test.spec_requirements = SpecRequirements(
        requirements=[],
        entities=[Entity(name="Task", fields=[], relationships=[], validations=[])],
        endpoints=[],
        business_logic=[],
        metadata={"spec_name": "task_api"}
    )

    await task_test._phase_6_code_generation()
    task_code = "\n".join(task_test.generated_code.values())

    # Test 2: Ecommerce API
    ecommerce_test = RealE2ETest("tests/e2e/test_specs/ecommerce_api_simple.md")
    ecommerce_test.code_generator = MagicMock()
    ecommerce_test.code_generator.generate_from_requirements = AsyncMock(return_value="""
from fastapi import FastAPI
class Product(BaseModel):
    pass
class Cart(BaseModel):
    pass
""")

    ecommerce_test.spec_requirements = SpecRequirements(
        requirements=[],
        entities=[
            Entity(name="Product", fields=[], relationships=[], validations=[]),
            Entity(name="Cart", fields=[], relationships=[], validations=[])
        ],
        endpoints=[],
        business_logic=[],
        metadata={"spec_name": "ecommerce_api"}
    )

    await ecommerce_test._phase_6_code_generation()
    ecommerce_code = "\n".join(ecommerce_test.generated_code.values())

    # Verify different code was generated
    assert "Task" in task_code and "Product" not in task_code, "Task spec should generate Task code"
    assert "Product" in ecommerce_code and "Task" not in ecommerce_code, "Ecommerce spec should generate Product code"
    assert task_code != ecommerce_code, "Different specs should generate different code"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
