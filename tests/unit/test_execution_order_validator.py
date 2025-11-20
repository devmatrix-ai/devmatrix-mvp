"""
Unit tests for Execution Order Validation (M3.3)

Tests critical behaviors:
- CRUD ordering violations detected (read before create)
- Workflow ordering violations detected (checkout before cart)
- Validation score calculation is correct
- OrderingViolation structure works

Target: 2-8 focused tests, skip exhaustive entity/workflow combinations
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from src.cognitive.planning.multi_pass_planner import (
    MultiPassPlanner,
    OrderingViolation,
    ExecutionOrderResult
)


# ============================================================================
# Test Data Structures
# ============================================================================

@dataclass
class Requirement:
    """Requirement structure for testing"""
    id: str
    description: str
    operation: str = ""  # create, read, update, delete, list
    type: str = "functional"
    priority: str = "MUST"
    domain: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Wave:
    """Execution wave containing requirements"""
    wave_number: int
    requirements: List[Requirement] = field(default_factory=list)


@dataclass
class DAG:
    """Simple DAG structure for testing"""
    waves: List[Wave] = field(default_factory=list)

    def get_wave_for_requirement(self, req_id: str) -> Optional[int]:
        """Get wave number for a requirement ID"""
        for wave in self.waves:
            for req in wave.requirements:
                if req.id == req_id:
                    return wave.wave_number
        return None


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def planner():
    """Create MultiPassPlanner instance"""
    return MultiPassPlanner()


@pytest.fixture
def valid_crud_dag():
    """DAG with valid CRUD ordering: create → read → update → delete"""
    product_create = Requirement(
        id="F1",
        description="Create product with name, price, stock",
        operation="create"
    )
    product_list = Requirement(
        id="F2",
        description="List products with pagination",
        operation="list"
    )
    product_read = Requirement(
        id="F3",
        description="Get product by id",
        operation="read"
    )
    product_update = Requirement(
        id="F4",
        description="Update product name, price, stock",
        operation="update"
    )
    product_delete = Requirement(
        id="F5",
        description="Delete product by id",
        operation="delete"
    )

    return DAG(waves=[
        Wave(wave_number=1, requirements=[product_create]),
        Wave(wave_number=2, requirements=[product_list, product_read, product_update]),
        Wave(wave_number=3, requirements=[product_delete]),
    ])


@pytest.fixture
def invalid_crud_dag():
    """DAG with CRUD violation: read before create"""
    product_read = Requirement(
        id="F1",
        description="Get product by id",
        operation="read"
    )
    product_create = Requirement(
        id="F2",
        description="Create product with name, price, stock",
        operation="create"
    )

    return DAG(waves=[
        Wave(wave_number=1, requirements=[product_read]),
        Wave(wave_number=2, requirements=[product_create]),
    ])


@pytest.fixture
def valid_workflow_dag():
    """DAG with valid workflow ordering: create_cart → add_to_cart → checkout_cart"""
    create_cart = Requirement(
        id="F1",
        description="Create cart for customer",
        operation="create"
    )
    add_to_cart = Requirement(
        id="F2",
        description="Add item to shopping cart",
        operation="update"
    )
    checkout_cart = Requirement(
        id="F3",
        description="Checkout cart and create order",
        operation="update"  # Changed from "create" to avoid CRUD conflict
    )

    return DAG(waves=[
        Wave(wave_number=1, requirements=[create_cart]),
        Wave(wave_number=2, requirements=[add_to_cart]),
        Wave(wave_number=3, requirements=[checkout_cart]),
    ])


@pytest.fixture
def invalid_workflow_dag():
    """DAG with workflow violation: checkout before add_to_cart"""
    checkout_cart = Requirement(
        id="F1",
        description="Checkout cart and create order",
        operation="update"  # Changed from "create" to avoid CRUD issues
    )
    add_to_cart = Requirement(
        id="F2",
        description="Add item to shopping cart",
        operation="update"
    )

    return DAG(waves=[
        Wave(wave_number=1, requirements=[checkout_cart]),
        Wave(wave_number=2, requirements=[add_to_cart]),
    ])


@pytest.fixture
def multi_entity_workflow_dag():
    """DAG with multi-entity workflow: create_customer → create_cart → checkout"""
    create_customer = Requirement(
        id="F1",
        description="Register customer with email",
        operation="create"
    )
    create_cart = Requirement(
        id="F2",
        description="Create cart for customer",
        operation="create"
    )
    checkout = Requirement(
        id="F3",
        description="Checkout cart",
        operation="create"
    )

    return DAG(waves=[
        Wave(wave_number=1, requirements=[create_customer]),
        Wave(wave_number=2, requirements=[create_cart]),
        Wave(wave_number=3, requirements=[checkout]),
    ])


# ============================================================================
# Test 1: Valid CRUD Ordering
# ============================================================================

def test_valid_crud_ordering(planner, valid_crud_dag):
    """Test that valid CRUD ordering passes validation"""
    requirements = []
    for wave in valid_crud_dag.waves:
        requirements.extend(wave.requirements)

    result = planner.validate_execution_order(valid_crud_dag, requirements)

    # Should have no violations
    assert isinstance(result, ExecutionOrderResult), "Result should be ExecutionOrderResult"
    assert result.score == 1.0, f"Expected score 1.0, got {result.score}"
    assert len(result.violations) == 0, f"Expected 0 violations, got {len(result.violations)}"
    assert result.is_valid, "Valid ordering should pass validation"


# ============================================================================
# Test 2: CRUD Violation Detection
# ============================================================================

def test_crud_violation_detection(planner, invalid_crud_dag):
    """Test that CRUD violations are detected (read before create)"""
    requirements = []
    for wave in invalid_crud_dag.waves:
        requirements.extend(wave.requirements)

    result = planner.validate_execution_order(invalid_crud_dag, requirements)

    # Should detect violation
    assert isinstance(result, ExecutionOrderResult), "Result should be ExecutionOrderResult"
    assert result.score < 1.0, f"Expected score < 1.0, got {result.score}"
    assert len(result.violations) > 0, "Should detect CRUD violation"

    # Check violation details
    violation = result.violations[0]
    assert violation.entity == "product", f"Expected entity 'product', got '{violation.entity}'"
    assert violation.violation_type == "crud", f"Expected 'crud' violation, got '{violation.violation_type}'"
    assert "create" in violation.message.lower(), "Violation message should mention 'create'"
    assert "read" in violation.message.lower(), "Violation message should mention 'read'"


# ============================================================================
# Test 3: Valid Workflow Ordering
# ============================================================================

def test_valid_workflow_ordering(planner, valid_workflow_dag):
    """Test that valid workflow ordering passes validation"""
    requirements = []
    for wave in valid_workflow_dag.waves:
        requirements.extend(wave.requirements)

    result = planner.validate_execution_order(valid_workflow_dag, requirements)

    # Should have no violations
    assert isinstance(result, ExecutionOrderResult), "Result should be ExecutionOrderResult"
    assert result.score == 1.0, f"Expected score 1.0, got {result.score}"
    assert len(result.violations) == 0, f"Expected 0 violations, got {len(result.violations)}"
    assert result.is_valid, "Valid workflow ordering should pass validation"


# ============================================================================
# Test 4: Workflow Violation Detection
# ============================================================================

def test_workflow_violation_detection(planner, invalid_workflow_dag):
    """Test that workflow violations are detected (checkout before add_to_cart)"""
    requirements = []
    for wave in invalid_workflow_dag.waves:
        requirements.extend(wave.requirements)

    result = planner.validate_execution_order(invalid_workflow_dag, requirements)

    # Should detect violation
    assert isinstance(result, ExecutionOrderResult), "Result should be ExecutionOrderResult"
    assert result.score < 1.0, f"Expected score < 1.0, got {result.score}"
    assert len(result.violations) > 0, "Should detect workflow violation"

    # Check violation details
    violation = result.violations[0]
    assert violation.violation_type == "workflow", f"Expected 'workflow' violation, got '{violation.violation_type}'"
    assert "checkout" in violation.message.lower(), "Violation message should mention 'checkout'"


# ============================================================================
# Test 5: Multi-Entity Workflow
# ============================================================================

def test_multi_entity_workflow(planner, multi_entity_workflow_dag):
    """Test that multi-entity workflows are validated correctly"""
    requirements = []
    for wave in multi_entity_workflow_dag.waves:
        requirements.extend(wave.requirements)

    result = planner.validate_execution_order(multi_entity_workflow_dag, requirements)

    # Should pass (correct order: customer → cart → checkout)
    assert isinstance(result, ExecutionOrderResult), "Result should be ExecutionOrderResult"
    assert result.score == 1.0, f"Expected score 1.0, got {result.score}"
    assert len(result.violations) == 0, f"Expected 0 violations, got {len(result.violations)}"


# ============================================================================
# Test 6: Score Calculation
# ============================================================================

def test_score_calculation(planner):
    """Test that validation score is calculated correctly"""
    # Create DAG with 1 violation out of 4 checks
    # Checks: product (crud), customer (crud), cart (workflow), checkout (workflow)
    product_read = Requirement(
        id="F1",
        description="Get product by id",
        operation="read"
    )
    product_create = Requirement(
        id="F2",
        description="Create product",
        operation="create"
    )
    customer_create = Requirement(
        id="F3",
        description="Create customer",
        operation="create"
    )

    dag = DAG(waves=[
        Wave(wave_number=1, requirements=[product_read, customer_create]),
        Wave(wave_number=2, requirements=[product_create]),
    ])

    requirements = [product_read, product_create, customer_create]
    result = planner.validate_execution_order(dag, requirements)

    # Should have 1 violation (product read before create)
    # Score = 1.0 - (1 violation / total checks)
    assert len(result.violations) == 1, f"Expected 1 violation, got {len(result.violations)}"
    assert 0.0 < result.score < 1.0, f"Expected score between 0.0 and 1.0, got {result.score}"
    assert result.total_checks > 0, "Total checks should be > 0"


# ============================================================================
# Test 7: Empty DAG Handling
# ============================================================================

def test_empty_dag_handling(planner):
    """Test that empty DAG returns valid result"""
    empty_dag = DAG(waves=[])
    requirements = []

    result = planner.validate_execution_order(empty_dag, requirements)

    # Empty DAG should be considered valid (no violations)
    assert isinstance(result, ExecutionOrderResult), "Result should be ExecutionOrderResult"
    assert result.score == 1.0, f"Expected score 1.0 for empty DAG, got {result.score}"
    assert len(result.violations) == 0, "Empty DAG should have no violations"
    assert result.is_valid, "Empty DAG should be valid"


# ============================================================================
# Test 8: OrderingViolation Structure
# ============================================================================

def test_ordering_violation_structure():
    """Test that OrderingViolation structure works correctly"""
    violation = OrderingViolation(
        entity="product",
        violation_type="crud",
        message="Product read before create",
        expected_order="create → read",
        actual_order="read → create"
    )

    # Check fields
    assert violation.entity == "product"
    assert violation.violation_type == "crud"
    assert "read" in violation.message
    assert "create" in violation.expected_order
    assert "read" in violation.actual_order

    # Check string representation works
    str_repr = str(violation)
    assert len(str_repr) > 0, "String representation should work"
