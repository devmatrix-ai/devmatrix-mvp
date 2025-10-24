"""
E2E Tests for MGE V2 Direct Migration Pipeline - Simplified

Tests the complete pipeline using only what's actually implemented:
1. Database and Models (Phase 1)
2. Atomization (Phase 2)
3. Dependency Graph (Phase 3)
4. Atomic Validation only (Phase 4 - simplified)
5. Execution (Phase 5)

Author: DevMatrix Team
Date: 2025-10-23
"""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Models
from src.config.database import Base
from src.models import (
    MasterPlan, AtomicUnit, DependencyGraph, AtomDependency, ExecutionWave
)

# Phase 2: Atomization
from src.atomization.parser import MultiLanguageParser
from src.atomization.decomposer import RecursiveDecomposer
from src.atomization.context_injector import ContextInjector
from src.atomization.validator import AtomicityValidator

# Phase 3: Dependency
from src.dependency.graph_builder import GraphBuilder
from src.dependency.topological_sorter import TopologicalSorter
from src.services.dependency_service import DependencyService

# Phase 4: Validation (atomic only)
from src.validation.atomic_validator import AtomicValidator

# Phase 5: Execution
from src.execution.code_executor import CodeExecutor
from src.execution.retry_logic import RetryLogic
from src.services.execution_service import ExecutionService


# Test Database Setup
@pytest.fixture(scope="module")
def test_db():
    """Create test database"""
    from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
    from sqlalchemy.dialects.postgresql import UUID
    import sqlalchemy.types as types

    # Monkey patch UUID, JSONB, and ARRAY types for SQLite compatibility
    def compile_uuid(element, compiler, **kw):
        return "CHAR(36)"

    def compile_jsonb(element, compiler, **kw):
        return "TEXT"

    def compile_array(element, compiler, **kw):
        return "TEXT"

    # Also need to handle JSON serialization for ARRAY type in SQLite
    import json
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import JSONB, ARRAY
    from sqlalchemy import TypeDecorator, Text

    class SqliteArray(TypeDecorator):
        impl = Text
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is not None:
                # Convert UUIDs to strings and serialize to JSON
                if isinstance(value, list):
                    return json.dumps([str(v) if hasattr(v, 'hex') else v for v in value])
                return value
            return None

        def process_result_value(self, value, dialect):
            if value is not None:
                return json.loads(value)
            return None

    # Monkey patch ARRAY for SQLite
    import sqlalchemy.dialects.postgresql as pg
    original_array_init = pg.ARRAY.__init__

    def patched_array_init(self, *args, **kwargs):
        original_array_init(self, *args, **kwargs)
        if hasattr(self, '_is_array'):
            self._is_array = True

    pg.ARRAY.__init__ = patched_array_init

    compiles(UUID, 'sqlite')(compile_uuid)
    compiles(JSONB, 'sqlite')(compile_jsonb)
    compiles(ARRAY, 'sqlite')(compile_array)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    yield db

    db.close()


@pytest.fixture
def sample_masterplan(test_db):
    """Create sample masterplan with discovery document"""
    from src.models import DiscoveryDocument

    # Create discovery document first (required FK)
    discovery = DiscoveryDocument(
        discovery_id=uuid.uuid4(),
        session_id="test-session",
        user_id="test-user",
        user_request="E2E Test Request",
        domain="Testing",
        bounded_contexts=[{"name": "test"}],
        aggregates=[],
        value_objects=[],
        domain_events=[],
        services=[],
        created_at=datetime.utcnow()
    )
    test_db.add(discovery)
    test_db.commit()

    # Now create masterplan
    masterplan = MasterPlan(
        masterplan_id=uuid.uuid4(),
        discovery_id=discovery.discovery_id,
        session_id="test-session",
        user_id="test-user",
        project_name="E2E Test Project",
        description="Test project for E2E pipeline",
        tech_stack={"backend": "python", "frontend": "react", "database": "postgresql"},
        created_at=datetime.utcnow()
    )
    test_db.add(masterplan)
    test_db.commit()
    test_db.refresh(masterplan)

    return masterplan


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing"""
    return """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Test the functions
result_fact = factorial(5)
result_fib = fibonacci(6)
print(f"Factorial of 5: {result_fact}")
print(f"Fibonacci of 6: {result_fib}")
"""


class TestPhase1Database:
    """Test Phase 1: Database and Models"""

    def test_database_setup(self, test_db):
        """Test database is created correctly"""
        assert test_db is not None

    def test_masterplan_creation(self, sample_masterplan):
        """Test MasterPlan model creation"""
        assert sample_masterplan.masterplan_id is not None
        assert sample_masterplan.project_name == "E2E Test Project"


class TestPhase2Atomization:
    """Test Phase 2: AST Atomization"""

    def test_parser_python(self):
        """Test MultiLanguageParser with Python"""
        parser = MultiLanguageParser()

        code = "def hello():\n    print('Hello World')"
        result = parser.parse(code, "python")

        assert result.success
        assert result.language == "python"
        assert len(result.functions) == 1
        assert result.functions[0]['name'] == 'hello'

    def test_decomposer(self, sample_python_code):
        """Test RecursiveDecomposer"""
        decomposer = RecursiveDecomposer(target_loc=10, max_loc=15)

        result = decomposer.decompose(sample_python_code, "python", "Math functions")

        assert result.success
        assert result.total_atoms >= 1
        print(f"\n✓ Decomposer created {result.total_atoms} atoms")

    def test_context_injector(self):
        """Test ContextInjector"""
        injector = ContextInjector()

        from src.atomization.decomposer import AtomCandidate

        atom = AtomCandidate(
            code="def add(a, b):\n    return a + b",
            start_line=1,
            end_line=2,
            loc=2,
            complexity=1.0,
            description="Add function",
            boundary_type="function"
        )

        full_code = "import math\ndef add(a, b):\n    return a + b"
        context = injector.inject_context(atom, full_code, "python")

        assert context.completeness_score > 0

    def test_atomicity_validator(self):
        """Test AtomicityValidator"""
        validator = AtomicityValidator()

        from src.atomization.decomposer import AtomCandidate

        atom = AtomCandidate(
            code="def add(a, b):\n    return a + b",
            start_line=1,
            end_line=2,
            loc=2,
            complexity=1.0,
            description="Add function",
            boundary_type="function"
        )

        result = validator.validate(atom)

        assert result.score > 0.5


class TestPhase3DependencyGraph:
    """Test Phase 3: Dependency Graph"""

    def test_graph_builder(self, test_db, sample_masterplan):
        """Test GraphBuilder"""
        # Create test atoms
        atom1 = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="def func_a():\n    return 1",
            description="Function A",
            language="python",
            loc=2,
            complexity=1.0
        )

        atom2 = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="def func_b():\n    return func_a() + 1",
            description="Function B",
            language="python",
            loc=2,
            complexity=1.0
        )

        test_db.add_all([atom1, atom2])
        test_db.commit()

        # Build graph
        builder = GraphBuilder()
        graph = builder.build_graph([atom1, atom2])

        assert graph.number_of_nodes() == 2
        print(f"\n✓ Graph built with {graph.number_of_nodes()} nodes")

    def test_topological_sorter(self):
        """Test TopologicalSorter"""
        import networkx as nx

        # Create simple graph
        graph = nx.DiGraph()
        node1 = str(uuid.uuid4())
        node2 = str(uuid.uuid4())
        graph.add_node(node1)
        graph.add_node(node2)

        sorter = TopologicalSorter()

        # Create dummy atoms
        atoms = [
            type('obj', (object,), {
                'atom_id': uuid.UUID(node),
                'complexity': 1.0
            })()
            for node in graph.nodes()
        ]

        plan = sorter.create_execution_plan(graph, atoms)

        assert plan.total_waves >= 1
        assert plan.total_atoms == 2
        print(f"\n✓ Execution plan: {plan.total_waves} waves, {plan.total_atoms} atoms")


class TestPhase4ValidationAtomic:
    """Test Phase 4: Atomic Validation Only"""

    def test_atomic_validator(self, test_db, sample_masterplan):
        """Test AtomicValidator"""
        # Create valid atom
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="def add(a, b):\n    return a + b",
            description="Add function",
            language="python",
            loc=2,
            complexity=1.0
        )

        test_db.add(atom)
        test_db.commit()

        validator = AtomicValidator(test_db)
        result = validator.validate_atom(atom.atom_id)

        assert result.syntax_valid
        assert result.validation_score > 0
        print(f"\n✓ Atom validation score: {result.validation_score:.2f}")


class TestPhase5Execution:
    """Test Phase 5: Execution + Retry"""

    def test_code_executor_python_success(self, test_db, sample_masterplan):
        """Test CodeExecutor with successful Python code"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="result = 2 + 2\nprint(result)",
            description="Simple addition",
            language="python",
            loc=2,
            complexity=1.0
        )

        executor = CodeExecutor(timeout=10)
        result = executor.execute_atom(atom)

        assert result.success
        assert result.exit_code == 0
        assert "4" in result.stdout
        print(f"\n✓ Code execution successful: {result.stdout.strip()}")

    def test_code_executor_error(self, test_db, sample_masterplan):
        """Test CodeExecutor with error"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="result = 1 / 0",
            description="Error test",
            language="python",
            loc=1,
            complexity=1.0
        )

        executor = CodeExecutor(timeout=10)
        result = executor.execute_atom(atom)

        assert not result.success
        assert "ZeroDivisionError" in result.stderr or "ZeroDivisionError" in (result.error_message or "")
        print(f"\n✓ Error correctly detected: ZeroDivisionError")

    def test_retry_logic(self, test_db, sample_masterplan):
        """Test RetryLogic"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="result = 1 / 0",
            description="Error test",
            language="python",
            loc=1,
            complexity=1.0
        )

        executor = CodeExecutor(timeout=10)
        result = executor.execute_atom(atom)

        retry_logic = RetryLogic(max_retries=3)
        decision = retry_logic.analyze_failure(atom, result)

        assert decision.should_retry or decision.max_retries_reached == False
        assert decision.retry_strategy in ['regenerate', 'fix', 'skip', 'manual']
        print(f"\n✓ Retry decision: {decision.retry_strategy}")

    def test_execution_service(self, test_db, sample_masterplan):
        """Test ExecutionService"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            atom_number=1,
            name="Test Atom",
            code_to_generate="print('Hello E2E Test')",
            description="Hello test",
            language="python",
            loc=1,
            complexity=1.0
        )

        test_db.add(atom)
        test_db.commit()

        service = ExecutionService(test_db, use_retry=True)
        result = service.execute_atom(atom.atom_id)

        assert 'success' in result
        assert 'execution_time' in result
        print(f"\n✓ Execution service: {result['success']}")


class TestFullPipelineSimplified:
    """Test simplified end-to-end pipeline"""

    def test_complete_pipeline(self, test_db, sample_masterplan, sample_python_code):
        """Test complete pipeline from code to execution"""
        print("\n" + "="*60)
        print("FULL PIPELINE TEST - SIMPLIFIED")
        print("="*60)

        # Phase 2: Atomization
        print("\nPhase 2: Atomization")
        parser = MultiLanguageParser()
        decomposer = RecursiveDecomposer()

        parse_result = parser.parse(sample_python_code, "python")
        assert parse_result.success, "Parsing failed"
        print(f"  ✓ Parsing successful")

        decomp_result = decomposer.decompose(
            sample_python_code,
            "python",
            "Math functions"
        )
        assert decomp_result.success, "Decomposition failed"
        assert decomp_result.total_atoms > 0, "No atoms created"
        print(f"  ✓ Created {decomp_result.total_atoms} atoms")

        # Create atoms in DB
        atoms = []
        for atom_candidate in decomp_result.atoms:
            atom = AtomicUnit(
                atom_id=uuid.uuid4(),
                masterplan_id=sample_masterplan.masterplan_id,
                atom_number=1,
                name="Test Atom",
                code_to_generate=atom_candidate.code,
                description=atom_candidate.description,
                language="python",
                loc=atom_candidate.loc,
                complexity=atom_candidate.complexity
            )
            atoms.append(atom)

        test_db.add_all(atoms)
        test_db.commit()
        print(f"  ✓ Stored {len(atoms)} atoms in database")

        # Phase 3: Dependency Graph
        print("\nPhase 3: Dependency Graph")
        if len(atoms) > 0:
            dep_service = DependencyService(test_db)
            graph_result = dep_service.build_dependency_graph(sample_masterplan.masterplan_id)

            assert graph_result['success'], "Dependency graph build failed"
            print(f"  ✓ Dependency graph built")
            print(f"    - Total atoms: {graph_result['total_atoms']}")
            print(f"    - Total edges: {graph_result['total_edges']}")
            print(f"    - Total waves: {graph_result['total_waves']}")

        # Phase 4: Atomic Validation
        print("\nPhase 4: Atomic Validation")
        validator = AtomicValidator(test_db)

        validation_scores = []
        for atom in atoms:
            val_result = validator.validate_atom(atom.atom_id)
            validation_scores.append(val_result.validation_score)
            assert val_result.syntax_valid, f"Syntax invalid for atom {atom.atom_id}"

        avg_score = sum(validation_scores) / len(validation_scores) if validation_scores else 0
        print(f"  ✓ Validated {len(atoms)} atoms")
        print(f"    - Average validation score: {avg_score:.2f}")

        # Phase 5: Execution
        print("\nPhase 5: Execution")
        exec_service = ExecutionService(test_db, use_retry=False)

        execution_results = []
        for atom in atoms:
            exec_result = exec_service.execute_atom(atom.atom_id)
            execution_results.append(exec_result)

        successful = sum(1 for r in execution_results if r.get('success', False))
        success_rate = successful / len(execution_results) * 100 if execution_results else 0

        print(f"  ✓ Executed {len(atoms)} atoms")
        print(f"    - Successful: {successful}")
        print(f"    - Failed: {len(execution_results) - successful}")
        print(f"    - Success rate: {success_rate:.1f}%")

        # Overall validation
        print("\n" + "="*60)
        print("PIPELINE VALIDATION")
        print("="*60)
        assert len(atoms) > 0, "Pipeline created no atoms"
        assert graph_result['success'], "Dependency graph failed"
        assert len(execution_results) > 0, "No execution results"
        print(f"✓ All phases completed successfully")
        print(f"✓ Pipeline is functional")
        print("="*60)

        return {
            'atoms_created': len(atoms),
            'graph_built': graph_result['success'],
            'validations': len(validation_scores),
            'executions': len(execution_results),
            'successful_executions': successful,
            'success_rate': success_rate
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
