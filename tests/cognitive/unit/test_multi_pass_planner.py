"""
Unit Tests for Multi-Pass Planning System

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

Test Coverage:
- Pass 1: Requirements Analysis (entities, attributes, relationships)
- Pass 2: Architecture Design (modules, patterns, dependencies)
- Pass 3: Contract Definition (APIs, schemas, validation)
- Pass 4: Integration Points (dependencies, execution order, cycles)
- Pass 5: Atomic Breakdown (50-120 atoms with signatures)
- Pass 6: Validation & Optimization (Tarjan, cycle detection)
- Complete pipeline (plan_complete) end-to-end execution
- JSON schema generation and validation
"""

import pytest
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, patch

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.planning.multi_pass_planner import (
    MultiPassPlanner,
    pass_1_requirements_analysis,
    pass_2_architecture_design,
    pass_3_contract_definition,
    pass_4_integration_points,
    pass_5_atomic_breakdown,
    pass_6_validation,
    plan_complete,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


class TestPass1RequirementsAnalysis:
    """Test Pass 1: Requirements Analysis."""

    def test_pass_1_extracts_entities_from_requirements(self):
        """Test that Pass 1 extracts entities (nouns) from requirements text."""
        spec = """
        Build a user authentication system with login and registration.
        Users have email, password, and profile information.
        System should validate credentials and manage sessions.
        """

        result = pass_1_requirements_analysis(spec)

        # Should extract entities
        assert "entities" in result
        entities = result["entities"]

        # Expected entities: User, Authentication, Login, Registration, Session, Profile
        assert len(entities) >= 3
        assert any("user" in str(entity).lower() for entity in entities)
        assert any("session" in str(entity).lower() for entity in entities)

    def test_pass_1_extracts_attributes_for_entities(self):
        """Test that Pass 1 extracts attributes for each entity."""
        spec = """
        User entity has email (string), password (hashed), and created_at (timestamp).
        Product has name, price (decimal), and inventory_count (integer).
        """

        result = pass_1_requirements_analysis(spec)

        # Should have entities with attributes
        assert "entities" in result
        entities = result["entities"]

        # At least one entity should have attributes
        assert len(entities) > 0
        # Check that entities have attribute lists
        for entity in entities:
            if isinstance(entity, dict):
                assert "attributes" in entity or "name" in entity

    def test_pass_1_identifies_relationships_between_entities(self):
        """Test that Pass 1 identifies relationships between entities."""
        spec = """
        A User can have multiple Orders.
        Each Order belongs to one User.
        Orders contain multiple OrderItems.
        """

        result = pass_1_requirements_analysis(spec)

        # Should identify relationships
        assert "relationships" in result
        relationships = result["relationships"]

        # Should find User-Order and Order-OrderItem relationships
        assert len(relationships) >= 1

    def test_pass_1_identifies_use_cases(self):
        """Test that Pass 1 identifies use cases and user flows."""
        spec = """
        Users can register with email and password.
        Users can login with credentials.
        Users can view their order history.
        """

        result = pass_1_requirements_analysis(spec)

        # Should identify use cases
        assert "use_cases" in result
        use_cases = result["use_cases"]

        # Should extract at least 2 use cases
        assert len(use_cases) >= 2


class TestPass2ArchitectureDesign:
    """Test Pass 2: Architecture Design."""

    def test_pass_2_defines_modules_from_entities(self):
        """Test that Pass 2 creates modules based on entities from Pass 1."""
        requirements = {
            "entities": [
                {"name": "User", "attributes": ["email", "password"]},
                {"name": "Order", "attributes": ["total", "status"]},
                {"name": "Payment", "attributes": ["amount", "method"]},
            ],
            "relationships": [],
            "use_cases": [],
        }

        result = pass_2_architecture_design(requirements)

        # Should define modules
        assert "modules" in result
        modules = result["modules"]

        # Should have modules for major entities
        assert len(modules) >= 2

    def test_pass_2_assigns_architectural_patterns(self):
        """Test that Pass 2 assigns architectural patterns (MVC, layered, etc.)."""
        requirements = {
            "entities": [
                {"name": "User", "attributes": ["email"]},
                {"name": "Product", "attributes": ["name"]},
            ],
            "relationships": [],
            "use_cases": ["User registration", "Product listing"],
        }

        result = pass_2_architecture_design(requirements)

        # Should assign patterns
        assert "patterns" in result or "architecture_pattern" in result

        # Should identify cross-cutting concerns
        assert "cross_cutting_concerns" in result or "concerns" in result


class TestPass3ContractDefinition:
    """Test Pass 3: Contract Definition."""

    def test_pass_3_defines_apis_for_modules(self):
        """Test that Pass 3 defines API contracts for each module."""
        architecture = {
            "modules": [
                {"name": "UserModule", "entities": ["User"]},
                {"name": "OrderModule", "entities": ["Order"]},
            ],
            "patterns": "layered",
        }

        result = pass_3_contract_definition(architecture)

        # Should define APIs
        assert "contracts" in result or "apis" in result

        # Each module should have contract definitions
        if "contracts" in result:
            assert len(result["contracts"]) >= 1

    def test_pass_3_specifies_data_schemas(self):
        """Test that Pass 3 specifies input/output schemas for APIs."""
        architecture = {
            "modules": [
                {"name": "AuthModule", "entities": ["User", "Session"]},
            ],
            "patterns": "MVC",
        }

        result = pass_3_contract_definition(architecture)

        # Should have schemas
        assert "schemas" in result or "contracts" in result

        # Schemas should have input/output definitions
        if "schemas" in result:
            assert len(result["schemas"]) > 0


class TestPass4IntegrationPoints:
    """Test Pass 4: Integration Points."""

    def test_pass_4_identifies_module_dependencies(self):
        """Test that Pass 4 identifies inter-module dependencies."""
        contracts = {
            "contracts": [
                {"module": "AuthModule", "depends_on": []},
                {"module": "OrderModule", "depends_on": ["AuthModule", "PaymentModule"]},
                {"module": "PaymentModule", "depends_on": ["AuthModule"]},
            ]
        }

        result = pass_4_integration_points(contracts)

        # Should create dependency matrix
        assert "dependencies" in result or "dependency_matrix" in result

    def test_pass_4_detects_circular_dependencies(self):
        """Test that Pass 4 detects and flags circular dependencies."""
        contracts = {
            "contracts": [
                {"module": "A", "depends_on": ["B"]},
                {"module": "B", "depends_on": ["C"]},
                {"module": "C", "depends_on": ["A"]},  # Circular: A→B→C→A
            ]
        }

        # Should either raise exception or return cycle detection result
        result = pass_4_integration_points(contracts)

        # Should flag circular dependency
        assert "has_cycles" in result or "cycles_detected" in result
        if "has_cycles" in result:
            assert result["has_cycles"] is True


class TestPass5AtomicBreakdown:
    """Test Pass 5: Atomic Breakdown."""

    def test_pass_5_creates_50_to_120_atoms(self):
        """Test that Pass 5 decomposes system into 50-120 atomic tasks."""
        integration = {
            "modules": [
                {"name": "UserModule", "functions": ["register", "login", "logout"]},
                {"name": "OrderModule", "functions": ["create_order", "list_orders"]},
            ],
            "dependencies": {},
        }

        result = pass_5_atomic_breakdown(integration)

        # Should return list of atoms
        assert isinstance(result, list) or "atoms" in result

        atoms = result if isinstance(result, list) else result["atoms"]

        # Should have 50-120 atoms
        assert 50 <= len(atoms) <= 120

    def test_pass_5_atoms_have_max_10_loc(self):
        """Test that Pass 5 ensures each atom is ≤10 LOC."""
        integration = {
            "modules": [
                {"name": "TestModule", "functions": ["test_function"]},
            ],
            "dependencies": {},
        }

        result = pass_5_atomic_breakdown(integration)

        atoms = result if isinstance(result, list) else result["atoms"]

        # Each atom should have max_loc constraint
        for atom in atoms:
            if isinstance(atom, dict):
                assert "max_loc" in atom or "estimated_loc" in atom
                if "max_loc" in atom:
                    assert atom["max_loc"] <= 10

    def test_pass_5_assigns_semantic_signatures(self):
        """Test that Pass 5 assigns semantic signatures to atoms."""
        integration = {
            "modules": [
                {"name": "ValidationModule", "functions": ["validate_email"]},
            ],
            "dependencies": {},
        }

        result = pass_5_atomic_breakdown(integration)

        atoms = result if isinstance(result, list) else result["atoms"]

        # At least some atoms should have signatures
        assert len(atoms) > 0
        for atom in atoms[:5]:  # Check first 5
            if isinstance(atom, dict):
                assert "signature" in atom or "purpose" in atom


class TestPass6Validation:
    """Test Pass 6: Validation & Optimization."""

    def test_pass_6_uses_tarjan_for_cycle_detection(self):
        """Test that Pass 6 uses Tarjan's algorithm for cycle detection."""
        atoms = [
            {"id": "atom_1", "depends_on": ["atom_2"]},
            {"id": "atom_2", "depends_on": ["atom_3"]},
            {"id": "atom_3", "depends_on": ["atom_1"]},  # Cycle
        ]

        is_valid, validated_atoms = pass_6_validation(atoms)

        # Should detect cycle and mark as invalid
        assert is_valid is False or "cycles" in str(validated_atoms)

    def test_pass_6_validates_dependency_ordering(self):
        """Test that Pass 6 validates dependency ordering is possible."""
        atoms = [
            {"id": "atom_1", "depends_on": []},
            {"id": "atom_2", "depends_on": ["atom_1"]},
            {"id": "atom_3", "depends_on": ["atom_1", "atom_2"]},
        ]

        is_valid, validated_atoms = pass_6_validation(atoms)

        # Should pass validation (no cycles)
        assert is_valid is True

    def test_pass_6_identifies_parallelization_opportunities(self):
        """Test that Pass 6 identifies atoms that can run in parallel."""
        atoms = [
            {"id": "atom_1", "depends_on": []},
            {"id": "atom_2", "depends_on": []},  # Can run parallel with atom_1
            {"id": "atom_3", "depends_on": ["atom_1", "atom_2"]},
        ]

        is_valid, validated_atoms = pass_6_validation(atoms)

        # Should identify parallelization
        assert is_valid is True
        # validated_atoms might include parallel execution groups
        if isinstance(validated_atoms, dict) and "parallel_groups" in validated_atoms:
            assert len(validated_atoms["parallel_groups"]) > 0


class TestCompletePipeline:
    """Test complete 6-pass pipeline execution."""

    def test_plan_complete_executes_all_6_passes(self):
        """Test that plan_complete runs all 6 passes end-to-end."""
        spec = """
        Build a simple task management system.
        Users can create, update, and delete tasks.
        Tasks have title, description, and due_date.
        """

        result = plan_complete(spec)

        # Should have all pass results
        assert "pass_1" in result or "requirements_analysis" in result
        assert "pass_2" in result or "architecture_design" in result
        assert "pass_3" in result or "contract_definition" in result
        assert "pass_4" in result or "integration_points" in result
        assert "pass_5" in result or "atomic_breakdown" in result
        assert "pass_6" in result or "validation" in result

    def test_plan_complete_passes_data_between_phases(self):
        """Test that plan_complete passes output of each phase to next."""
        spec = """
        Simple authentication system with user login.
        """

        result = plan_complete(spec)

        # Pass 2 should receive Pass 1 output
        # Pass 3 should receive Pass 2 output
        # Verify chain is maintained
        assert result is not None

        # Final result should include atoms
        if "pass_5" in result or "atomic_breakdown" in result:
            atoms_key = "pass_5" if "pass_5" in result else "atomic_breakdown"
            atoms = result[atoms_key]
            assert len(atoms) > 0 if isinstance(atoms, list) else "atoms" in atoms


class TestMultiPassPlannerClass:
    """Test MultiPassPlanner class orchestration."""

    def test_multi_pass_planner_initialization(self):
        """Test that MultiPassPlanner initializes correctly."""
        planner = MultiPassPlanner()

        assert planner is not None
        assert hasattr(planner, "plan") or hasattr(planner, "execute")

    def test_multi_pass_planner_plan_method(self):
        """Test that MultiPassPlanner.plan() executes complete pipeline."""
        spec = """
        E-commerce product catalog with search and filtering.
        """

        planner = MultiPassPlanner()
        result = planner.plan(spec)

        # Should return complete plan with all passes
        assert result is not None
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
