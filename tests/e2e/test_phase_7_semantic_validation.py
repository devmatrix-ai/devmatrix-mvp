"""
Integration tests for Phase 7 semantic validation

Tests that Phase 7 validates generated code against spec requirements
and correctly fails when compliance is below threshold.

Task Group 4.2.1: Write integration tests for Phase 7 enhancement
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

from src.parsing.spec_parser import SpecParser, SpecRequirements, Entity, Endpoint, Field, Requirement
from src.validation.compliance_validator import ComplianceValidator, ComplianceReport, ComplianceValidationError


class TestPhase7SemanticValidation:
    """Test Phase 7 semantic validation integration"""

    @pytest.fixture
    def sample_ecommerce_spec_requirements(self):
        """Sample ecommerce spec with Product, Customer, Cart, Order entities"""
        return SpecRequirements(
            entities=[
                Entity(name="Product", fields=[
                    Field(name="id", type="UUID", constraints=["primary_key=True"]),
                    Field(name="name", type="str", constraints=["min_length=1"]),
                    Field(name="price", type="Decimal", constraints=["gt=0"]),
                    Field(name="stock", type="int", constraints=["ge=0"])
                ], relationships=[], validations=[]),
                Entity(name="Customer", fields=[
                    Field(name="id", type="UUID", constraints=["primary_key=True"]),
                    Field(name="email", type="str", constraints=["email_format"])
                ], relationships=[], validations=[]),
                Entity(name="Cart", fields=[
                    Field(name="id", type="UUID", constraints=["primary_key=True"])
                ], relationships=[], validations=[]),
                Entity(name="Order", fields=[
                    Field(name="id", type="UUID", constraints=["primary_key=True"])
                ], relationships=[], validations=[])
            ],
            endpoints=[
                Endpoint(method="POST", path="/products", entity="Product", operation="create", params=[], response=None, business_logic=[]),
                Endpoint(method="GET", path="/products", entity="Product", operation="list", params=[], response=None, business_logic=[]),
                Endpoint(method="GET", path="/products/{id}", entity="Product", operation="read", params=[], response=None, business_logic=[]),
                Endpoint(method="POST", path="/customers", entity="Customer", operation="create", params=[], response=None, business_logic=[]),
                Endpoint(method="POST", path="/cart", entity="Cart", operation="create", params=[], response=None, business_logic=[])
            ],
            requirements=[
                Requirement(id="F1", type="functional", priority="MUST", description="Product CRUD operations", domain="crud", dependencies=[]),
                Requirement(id="F2", type="functional", priority="MUST", description="Customer management", domain="crud", dependencies=[]),
                Requirement(id="F3", type="functional", priority="MUST", description="Shopping cart", domain="crud", dependencies=[])
            ],
            business_logic=[],
            metadata={"spec_name": "ecommerce_api_simple"}
        )

    @pytest.fixture
    def sample_task_spec_requirements(self):
        """Sample task API spec with Task entity only"""
        return SpecRequirements(
            entities=[
                Entity(name="Task", fields=[
                    Field(name="id", type="UUID", constraints=["primary_key=True"]),
                    Field(name="title", type="str", constraints=["min_length=1"]),
                    Field(name="completed", type="bool", constraints=[])
                ], relationships=[], validations=[])
            ],
            endpoints=[
                Endpoint(method="POST", path="/tasks", entity="Task", operation="create", params=[], response=None, business_logic=[]),
                Endpoint(method="GET", path="/tasks", entity="Task", operation="list", params=[], response=None, business_logic=[]),
                Endpoint(method="GET", path="/tasks/{id}", entity="Task", operation="read", params=[], response=None, business_logic=[]),
                Endpoint(method="PUT", path="/tasks/{id}", entity="Task", operation="update", params=[], response=None, business_logic=[]),
                Endpoint(method="DELETE", path="/tasks/{id}", entity="Task", operation="delete", params=[], response=None, business_logic=[])
            ],
            requirements=[
                Requirement(id="F1", type="functional", priority="MUST", description="Task CRUD", domain="crud", dependencies=[])
            ],
            business_logic=[],
            metadata={"spec_name": "simple_task_api"}
        )

    @pytest.fixture
    def correct_ecommerce_code(self):
        """Generated code that CORRECTLY implements ecommerce spec"""
        return '''
from fastapi import FastAPI
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal

app = FastAPI()

class Product(BaseModel):
    id: UUID
    name: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    stock: int = Field(ge=0)

class Customer(BaseModel):
    id: UUID
    email: str

class Cart(BaseModel):
    id: UUID

class Order(BaseModel):
    id: UUID

@app.post("/products")
async def create_product(product: Product):
    return {"id": product.id}

@app.get("/products")
async def list_products():
    return []

@app.get("/products/{id}")
async def get_product(id: UUID):
    return {"id": id}

@app.post("/customers")
async def create_customer(customer: Customer):
    return {"id": customer.id}

@app.post("/cart")
async def create_cart(cart: Cart):
    return {"id": cart.id}
'''

    @pytest.fixture
    def wrong_task_code(self):
        """Generated code that INCORRECTLY implements Task API (for ecommerce spec)"""
        return '''
from fastapi import FastAPI
from pydantic import BaseModel
from uuid import UUID

app = FastAPI()

class Task(BaseModel):
    id: UUID
    title: str
    completed: bool = False

@app.post("/tasks")
async def create_task(task: Task):
    return {"id": task.id}

@app.get("/tasks")
async def list_tasks():
    return []

@app.get("/tasks/{id}")
async def get_task(id: UUID):
    return {"id": id}
'''

    @pytest.fixture
    def correct_task_code(self):
        """Generated code that CORRECTLY implements task spec"""
        return '''
from fastapi import FastAPI
from pydantic import BaseModel, Field
from uuid import UUID

app = FastAPI()

class Task(BaseModel):
    id: UUID
    title: str = Field(min_length=1)
    completed: bool = False

@app.post("/tasks")
async def create_task(task: Task):
    return {"id": task.id}

@app.get("/tasks")
async def list_tasks():
    return []

@app.get("/tasks/{id}")
async def get_task(id: UUID):
    return {"id": id}

@app.put("/tasks/{id}")
async def update_task(id: UUID, task: Task):
    return {"id": id}

@app.delete("/tasks/{id}")
async def delete_task(id: UUID):
    return {"deleted": True}
'''

    def test_phase_7_validates_correct_code_passes(
        self,
        sample_ecommerce_spec_requirements,
        correct_ecommerce_code
    ):
        """
        Test that Phase 7 PASSES when generated code correctly implements spec

        Given: Ecommerce spec with Product/Customer/Cart/Order entities
        When: Generated code implements all entities and endpoints
        Then: Compliance should be >= 80% and validation should PASS
        """
        validator = ComplianceValidator()

        # Validate (should not raise exception)
        report = validator.validate(
            spec_requirements=sample_ecommerce_spec_requirements,
            generated_code=correct_ecommerce_code
        )

        # Assert high compliance
        assert report.overall_compliance >= 0.80, \
            f"Expected compliance >= 80%, got {report.overall_compliance:.1%}"

        # Assert entities implemented
        assert len(report.entities_implemented) >= 3, \
            f"Expected at least 3 entities, found {len(report.entities_implemented)}"

        # Assert endpoints implemented
        assert len(report.endpoints_implemented) >= 3, \
            f"Expected at least 3 endpoints, found {len(report.endpoints_implemented)}"

    def test_phase_7_validates_wrong_code_fails(
        self,
        sample_ecommerce_spec_requirements,
        wrong_task_code
    ):
        """
        Test that Phase 7 FAILS when generated code is wrong (Task API for ecommerce spec)

        Given: Ecommerce spec expecting Product/Customer/Cart/Order
        When: Generated code only implements Task entity (WRONG)
        Then: Compliance should be < 80% and validation should FAIL
        """
        validator = ComplianceValidator()

        # Validate
        report = validator.validate(
            spec_requirements=sample_ecommerce_spec_requirements,
            generated_code=wrong_task_code
        )

        # Assert low compliance (this is the BUG - currently not caught!)
        assert report.overall_compliance < 0.80, \
            f"Expected compliance < 80% for wrong code, got {report.overall_compliance:.1%}"

        # Assert wrong entities detected
        assert "Task" in report.entities_implemented, \
            "Should detect Task entity in wrong code"
        assert "Product" not in report.entities_implemented, \
            "Should NOT detect Product entity"

        # Assert missing requirements reported
        assert len(report.missing_requirements) > 0, \
            "Should report missing requirements"

    def test_phase_7_validates_task_code_for_task_spec_passes(
        self,
        sample_task_spec_requirements,
        correct_task_code
    ):
        """
        Test that Phase 7 PASSES when Task code correctly implements Task spec

        Given: Task spec with Task entity and CRUD endpoints
        When: Generated code implements Task entity with all CRUD operations
        Then: Compliance should be >= 80% and validation should PASS
        """
        validator = ComplianceValidator()

        # Validate
        report = validator.validate(
            spec_requirements=sample_task_spec_requirements,
            generated_code=correct_task_code
        )

        # Assert high compliance
        assert report.overall_compliance >= 0.80, \
            f"Expected compliance >= 80%, got {report.overall_compliance:.1%}"

        # Assert Task entity implemented
        assert "Task" in report.entities_implemented, \
            "Should detect Task entity"

        # Assert all CRUD endpoints implemented
        assert len(report.endpoints_implemented) >= 4, \
            f"Expected at least 4 CRUD endpoints, found {len(report.endpoints_implemented)}"

    def test_phase_7_validate_or_raise_fails_below_threshold(
        self,
        sample_ecommerce_spec_requirements,
        wrong_task_code
    ):
        """
        Test that validate_or_raise() raises exception when compliance < threshold

        This is the behavior Phase 7 will use to fail the E2E test.
        """
        validator = ComplianceValidator()

        # Should raise ComplianceValidationError
        with pytest.raises(ComplianceValidationError) as exc_info:
            validator.validate_or_raise(
                spec_requirements=sample_ecommerce_spec_requirements,
                generated_code=wrong_task_code,
                threshold=0.80
            )

        # Check error message contains useful info
        error_msg = str(exc_info.value)
        assert "Compliance validation FAILED" in error_msg, \
            "Error message should indicate validation failure"
        assert "threshold" in error_msg.lower(), \
            "Error message should mention threshold"

    def test_phase_7_validate_or_raise_passes_above_threshold(
        self,
        sample_ecommerce_spec_requirements,
        correct_ecommerce_code
    ):
        """
        Test that validate_or_raise() succeeds when compliance >= threshold
        """
        validator = ComplianceValidator()

        # Should NOT raise exception
        report = validator.validate_or_raise(
            spec_requirements=sample_ecommerce_spec_requirements,
            generated_code=correct_ecommerce_code,
            threshold=0.80
        )

        # Assert report returned successfully
        assert report.overall_compliance >= 0.80, \
            f"Expected compliance >= 80%, got {report.overall_compliance:.1%}"

    def test_compliance_report_includes_all_metadata(
        self,
        sample_ecommerce_spec_requirements,
        correct_ecommerce_code
    ):
        """
        Test that ComplianceReport includes all required metadata for checkpoints

        Phase 7 will store this in checkpoint for metrics tracking.
        """
        validator = ComplianceValidator()
        report = validator.validate(
            spec_requirements=sample_ecommerce_spec_requirements,
            generated_code=correct_ecommerce_code
        )

        # Check all required fields present
        assert hasattr(report, 'overall_compliance'), "Missing overall_compliance"
        assert hasattr(report, 'entities_implemented'), "Missing entities_implemented"
        assert hasattr(report, 'endpoints_implemented'), "Missing endpoints_implemented"
        assert hasattr(report, 'missing_requirements'), "Missing missing_requirements"
        assert hasattr(report, 'compliance_details'), "Missing compliance_details"

        # Check compliance_details structure
        assert 'entities' in report.compliance_details, "Missing entities score"
        assert 'endpoints' in report.compliance_details, "Missing endpoints score"
        assert 'validations' in report.compliance_details, "Missing validations score"
