"""
Unit tests for Enhanced Dependency Inference (M3.2)

Tests critical behaviors:
- CRUD dependencies inferred correctly (create before read/update/delete)
- Entity grouping works correctly
- Entity extraction from requirements works
- Edge deduplication works

Target: 2-8 focused tests, skip exhaustive entity/operation combinations
"""

import pytest
from dataclasses import dataclass, field
from typing import List
from src.cognitive.planning.multi_pass_planner import MultiPassPlanner


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
class Edge:
    """Dependency edge structure"""
    from_node: str
    to_node: str
    type: str
    reason: str = ""


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def planner():
    """Create MultiPassPlanner instance"""
    return MultiPassPlanner()


@pytest.fixture
def product_requirements():
    """Sample Product entity CRUD requirements"""
    return [
        Requirement(
            id="F1",
            description="Create product with name, price, stock",
            operation="create"
        ),
        Requirement(
            id="F2",
            description="List products with pagination",
            operation="list"
        ),
        Requirement(
            id="F3",
            description="Get product by id",
            operation="read"
        ),
        Requirement(
            id="F4",
            description="Update product name, price, stock",
            operation="update"
        ),
        Requirement(
            id="F5",
            description="Delete product by id",
            operation="delete"
        ),
    ]


@pytest.fixture
def customer_requirements():
    """Sample Customer entity CRUD requirements"""
    return [
        Requirement(
            id="F6",
            description="Register customer with email and name",
            operation="create"
        ),
        Requirement(
            id="F7",
            description="Get customer by id",
            operation="read"
        ),
    ]


# ============================================================================
# Test 1: Entity Extraction
# ============================================================================

def test_extract_entity_from_requirement(planner):
    """Test that entity extraction identifies entities correctly"""
    # Product entity
    req_product = Requirement(
        id="F1",
        description="Create product with name and price"
    )
    entity = planner._extract_entity(req_product)
    assert entity == "product", f"Expected 'product', got '{entity}'"

    # Customer entity
    req_customer = Requirement(
        id="F2",
        description="Register customer with email"
    )
    entity = planner._extract_entity(req_customer)
    assert entity == "customer", f"Expected 'customer', got '{entity}'"

    # Cart entity
    req_cart = Requirement(
        id="F3",
        description="Add item to cart"
    )
    entity = planner._extract_entity(req_cart)
    assert entity == "cart", f"Expected 'cart', got '{entity}'"

    # Unknown entity (fallback)
    req_unknown = Requirement(
        id="F4",
        description="Process something without known entity"
    )
    entity = planner._extract_entity(req_unknown)
    assert entity == "unknown", f"Expected 'unknown', got '{entity}'"


# ============================================================================
# Test 2: Entity Grouping
# ============================================================================

def test_group_by_entity(planner, product_requirements, customer_requirements):
    """Test that requirements are grouped by entity correctly"""
    all_requirements = product_requirements + customer_requirements

    grouped = planner._group_by_entity(all_requirements)

    # Should have 2 groups: product and customer
    assert "product" in grouped, "Product entity not found in groups"
    assert "customer" in grouped, "Customer entity not found in groups"

    # Product group should have 5 requirements (F1-F5)
    assert len(grouped["product"]) == 5, f"Expected 5 product reqs, got {len(grouped['product'])}"

    # Customer group should have 2 requirements (F6-F7)
    assert len(grouped["customer"]) == 2, f"Expected 2 customer reqs, got {len(grouped['customer'])}"

    # Verify IDs are correct
    product_ids = [req.id for req in grouped["product"]]
    assert set(product_ids) == {"F1", "F2", "F3", "F4", "F5"}

    customer_ids = [req.id for req in grouped["customer"]]
    assert set(customer_ids) == {"F6", "F7"}


# ============================================================================
# Test 3: CRUD Dependency Inference - Basic
# ============================================================================

def test_crud_dependencies_basic(planner, product_requirements):
    """Test basic CRUD dependency inference: create before other operations"""
    edges = planner._crud_dependencies(product_requirements)

    # Create (F1) should have edges TO read (F3), update (F4), delete (F5), list (F2)
    # Edges are from create TO other operations (create must happen first)

    # Find all edges from create requirement
    create_edges = [e for e in edges if e.from_node == "F1"]

    # Should have 4 edges: F1 -> F2 (list), F1 -> F3 (read), F1 -> F4 (update), F1 -> F5 (delete)
    assert len(create_edges) == 4, f"Expected 4 edges from create, got {len(create_edges)}"

    # Verify target nodes
    target_nodes = {e.to_node for e in create_edges}
    assert target_nodes == {"F2", "F3", "F4", "F5"}, f"Expected F2-F5 as targets, got {target_nodes}"

    # Verify edge type
    for edge in create_edges:
        assert edge.type == "crud_dependency", f"Expected 'crud_dependency', got '{edge.type}'"


# ============================================================================
# Test 4: CRUD Dependency Inference - Multiple Entities
# ============================================================================

def test_crud_dependencies_multiple_entities(planner, product_requirements, customer_requirements):
    """Test CRUD dependencies with multiple entities (no cross-entity edges)"""
    all_requirements = product_requirements + customer_requirements

    edges = planner._crud_dependencies(all_requirements)

    # Product: F1 -> F2, F3, F4, F5 (4 edges)
    product_edges = [e for e in edges if e.from_node == "F1"]
    assert len(product_edges) == 4, f"Expected 4 product edges, got {len(product_edges)}"

    # Customer: F6 -> F7 (1 edge)
    customer_edges = [e for e in edges if e.from_node == "F6"]
    assert len(customer_edges) == 1, f"Expected 1 customer edge, got {len(customer_edges)}"

    # Total: 5 edges (4 product + 1 customer)
    assert len(edges) == 5, f"Expected 5 total edges, got {len(edges)}"

    # Verify no cross-entity dependencies (product create shouldn't depend on customer)
    for edge in edges:
        if edge.from_node in ["F1", "F2", "F3", "F4", "F5"]:
            assert edge.to_node in ["F1", "F2", "F3", "F4", "F5"], \
                f"Product edge should stay within product: {edge.from_node} -> {edge.to_node}"
        if edge.from_node in ["F6", "F7"]:
            assert edge.to_node in ["F6", "F7"], \
                f"Customer edge should stay within customer: {edge.from_node} -> {edge.to_node}"


# ============================================================================
# Test 5: CRUD Dependencies - No Create Requirement
# ============================================================================

def test_crud_dependencies_no_create(planner):
    """Test that no edges are created when there's no create operation"""
    requirements = [
        Requirement(id="F1", description="Get product by id", operation="read"),
        Requirement(id="F2", description="Update product", operation="update"),
    ]

    edges = planner._crud_dependencies(requirements)

    # No create requirement, so no CRUD edges should be generated
    assert len(edges) == 0, f"Expected 0 edges without create operation, got {len(edges)}"


# ============================================================================
# Test 6: Edge Deduplication
# ============================================================================

def test_validate_edges_deduplication(planner):
    """Test that duplicate edges are removed"""
    duplicate_edges = [
        Edge(from_node="F1", to_node="F2", type="crud_dependency", reason="Test 1"),
        Edge(from_node="F1", to_node="F2", type="crud_dependency", reason="Test 2"),  # duplicate
        Edge(from_node="F1", to_node="F3", type="crud_dependency", reason="Test 3"),
        Edge(from_node="F2", to_node="F3", type="explicit", reason="Test 4"),
    ]

    validated = planner._validate_edges(duplicate_edges)

    # Should have 3 unique edges (F1->F2 deduplicated)
    assert len(validated) == 3, f"Expected 3 unique edges after dedup, got {len(validated)}"

    # Verify edge pairs
    edge_pairs = {(e.from_node, e.to_node) for e in validated}
    assert edge_pairs == {("F1", "F2"), ("F1", "F3"), ("F2", "F3")}, \
        f"Expected 3 unique pairs, got {edge_pairs}"


# ============================================================================
# Test 7: CRUD Dependencies with operation field missing
# ============================================================================

def test_crud_dependencies_operation_missing(planner):
    """Test graceful handling when operation field is missing/empty"""
    requirements = [
        Requirement(id="F1", description="Create product", operation="create"),
        Requirement(id="F2", description="Something about product", operation=""),  # empty operation
    ]

    # Should not crash, handle gracefully
    edges = planner._crud_dependencies(requirements)

    # F1 has create, F2 has no valid operation, so no edge to F2
    assert len(edges) == 0, f"Expected 0 edges with invalid operation, got {len(edges)}"


# ============================================================================
# Test 8: Integrated Enhanced Inference
# ============================================================================

def test_infer_dependencies_enhanced(planner, product_requirements):
    """Test integrated enhanced inference combines all strategies"""
    # This tests the full pipeline: explicit + CRUD + pattern-based + validation

    edges = planner.infer_dependencies_enhanced(product_requirements)

    # Should have CRUD edges from create to other operations
    # At minimum: F1 -> F2, F1 -> F3, F1 -> F4, F1 -> F5
    assert len(edges) >= 4, f"Expected at least 4 CRUD edges, got {len(edges)}"

    # Verify create edges exist
    create_edges = [e for e in edges if e.from_node == "F1"]
    assert len(create_edges) >= 4, f"Expected at least 4 edges from create, got {len(create_edges)}"

    # Verify no duplicate edges
    edge_pairs = [(e.from_node, e.to_node) for e in edges]
    assert len(edge_pairs) == len(set(edge_pairs)), "Found duplicate edges after validation"
