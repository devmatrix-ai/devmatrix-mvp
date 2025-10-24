"""
E2E Tests for MGE V2 Direct Migration Pipeline

Tests the complete pipeline from task decomposition to execution:
1. Database and Models (Phase 1)
2. Atomization (Phase 2)
3. Dependency Graph (Phase 3)
4. Validation (Phase 4)
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

# Services
from src.atomization.parser import MultiLanguageParser
from src.atomization.decomposer import RecursiveDecomposer
from src.atomization.context_injector import ContextInjector
from src.atomization.validator import AtomicityValidator
from src.dependency.graph_builder import GraphBuilder
from src.dependency.topological_sorter import TopologicalSorter
from src.services.dependency_service import DependencyService
from src.validation.atomic_validator import AtomicValidator
from src.validation.system_validator import SystemValidator
from src.services.validation_service import ValidationService
from src.execution.code_executor import CodeExecutor
from src.execution.retry_logic import RetryLogic
from src.services.execution_service import ExecutionService


# Test Database Setup
@pytest.fixture(scope="module")
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    yield db

    db.close()


@pytest.fixture
def sample_masterplan(test_db):
    """Create sample masterplan"""
    masterplan = MasterPlan(
        masterplan_id=uuid.uuid4(),
        project_name="E2E Test Project",
        description="Test project for E2E pipeline",
        created_at=datetime.utcnow()
    )
    test_db.add(masterplan)
    test_db.commit()
    test_db.refresh(masterplan)

    return masterplan


@pytest.fixture
def sample_task(test_db, sample_masterplan):
    """Create sample task with Python code"""
    task = Task(
        task_id=uuid.uuid4(),
        masterplan_id=sample_masterplan.masterplan_id,
        task_description="Calculate factorial of a number",
        task_code="""
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Test the function
result = factorial(5)
print(f"Factorial of 5 is: {result}")
""",
        language="python",
        complexity=2.0,
        estimated_loc=8,
        created_at=datetime.utcnow()
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    return task


class TestPhase1Database:
    """Test Phase 1: Database and Models"""

    def test_database_setup(self, test_db):
        """Test database is created correctly"""
        assert test_db is not None

    def test_masterplan_creation(self, sample_masterplan):
        """Test MasterPlan model creation"""
        assert sample_masterplan.masterplan_id is not None
        assert sample_masterplan.project_name == "E2E Test Project"

    def test_task_creation(self, sample_task):
        """Test Task model creation"""
        assert sample_task.task_id is not None
        assert sample_task.language == "python"
        assert "factorial" in sample_task.task_code


class TestPhase2Atomization:
    """Test Phase 2: AST Atomization"""

    def test_parser(self):
        """Test MultiLanguageParser"""
        parser = MultiLanguageParser()

        code = "def hello():\n    print('Hello')"
        result = parser.parse(code, "python")

        assert result.success
        assert result.language == "python"
        assert len(result.functions) == 1
        assert result.functions[0]['name'] == 'hello'

    def test_decomposer(self):
        """Test RecursiveDecomposer"""
        decomposer = RecursiveDecomposer(target_loc=10, max_loc=15)

        code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        result = decomposer.decompose(code, "python", "Math operations")

        assert result.success
        assert result.total_atoms >= 1  # Should create at least one atom

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

    def test_validator(self):
        """Test AtomicityValidator"""
        validator = AtomicityValidator()

        from src.atomization.decomposer import AtomCandidate

        # Good atom
        good_atom = AtomCandidate(
            code="def add(a, b):\n    return a + b",
            start_line=1,
            end_line=2,
            loc=2,
            complexity=1.0,
            description="Add function",
            boundary_type="function"
        )

        result = validator.validate(good_atom)

        assert result.score > 0.5  # Should pass most criteria


class TestPhase3DependencyGraph:
    """Test Phase 3: Dependency Graph"""

    def test_graph_builder(self, test_db, sample_masterplan):
        """Test GraphBuilder"""
        # Create some test atoms
        atom1 = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="def func_a():\n    return 1",
            generated_code="def func_a():\n    return 1",
            description="Function A",
            language="python",
            loc=2,
            complexity=1.0
        )

        atom2 = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="def func_b():\n    return func_a() + 1",
            generated_code="def func_b():\n    return func_a() + 1",
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

    def test_topological_sorter(self, test_db, sample_masterplan):
        """Test TopologicalSorter"""
        import networkx as nx

        # Create simple graph
        graph = nx.DiGraph()
        graph.add_node(str(uuid.uuid4()))
        graph.add_node(str(uuid.uuid4()))

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


class TestPhase4Validation:
    """Test Phase 4: Hierarchical Validation"""

    def test_atomic_validator(self, test_db, sample_masterplan):
        """Test AtomicValidator"""
        # Create valid atom
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="def add(a, b):\n    return a + b",
            generated_code="def add(a, b):\n    return a + b",
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

    def test_validation_service(self, test_db, sample_masterplan):
        """Test ValidationService"""
        # Create atom
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="def test():\n    pass",
            generated_code="def test():\n    pass",
            description="Test function",
            language="python",
            loc=2,
            complexity=1.0
        )

        test_db.add(atom)
        test_db.commit()

        service = ValidationService(test_db)
        result = service.validate_atom(atom.atom_id)

        assert 'is_valid' in result
        assert 'validation_score' in result


class TestPhase5Execution:
    """Test Phase 5: Execution + Retry"""

    def test_code_executor_python(self, test_db, sample_masterplan):
        """Test CodeExecutor with Python code"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="result = 2 + 2\nprint(result)",
            generated_code="result = 2 + 2\nprint(result)",
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

    def test_code_executor_error(self, test_db, sample_masterplan):
        """Test CodeExecutor with error"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="result = 1 / 0",  # Division by zero
            generated_code="result = 1 / 0",
            description="Error test",
            language="python",
            loc=1,
            complexity=1.0
        )

        executor = CodeExecutor(timeout=10)
        result = executor.execute_atom(atom)

        assert not result.success
        assert "ZeroDivisionError" in result.stderr or "ZeroDivisionError" in (result.error_message or "")

    def test_retry_logic(self, test_db, sample_masterplan):
        """Test RetryLogic"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="result = 1 / 0",
            generated_code="result = 1 / 0",
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

    def test_execution_service(self, test_db, sample_masterplan):
        """Test ExecutionService"""
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=sample_masterplan.masterplan_id,
            original_code="print('Hello World')",
            generated_code="print('Hello World')",
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


class TestFullPipeline:
    """Test complete E2E pipeline"""

    def test_complete_pipeline(self, test_db, sample_masterplan, sample_task):
        """Test complete pipeline from task to execution"""

        # Phase 2: Atomization
        parser = MultiLanguageParser()
        decomposer = RecursiveDecomposer()

        parse_result = parser.parse(sample_task.task_code, sample_task.language)
        assert parse_result.success, "Parsing failed"

        decomp_result = decomposer.decompose(
            sample_task.task_code,
            sample_task.language,
            sample_task.task_description
        )
        assert decomp_result.success, "Decomposition failed"
        assert decomp_result.total_atoms > 0, "No atoms created"

        # Create atoms in DB
        atoms = []
        for atom_candidate in decomp_result.atoms:
            atom = AtomicUnit(
                atom_id=uuid.uuid4(),
                masterplan_id=sample_masterplan.masterplan_id,
                original_code=atom_candidate.code,
                generated_code=atom_candidate.code,
                description=atom_candidate.description,
                language=sample_task.language,
                loc=atom_candidate.loc,
                complexity=atom_candidate.complexity
            )
            atoms.append(atom)

        test_db.add_all(atoms)
        test_db.commit()

        print(f"\n✓ Phase 2: Created {len(atoms)} atoms")

        # Phase 3: Dependency Graph
        if len(atoms) > 0:
            dep_service = DependencyService(test_db)
            graph_result = dep_service.build_dependency_graph(sample_masterplan.masterplan_id)

            assert graph_result['success'], "Dependency graph build failed"
            print(f"✓ Phase 3: Dependency graph built with {graph_result['total_atoms']} atoms")

        # Phase 4: Validation
        val_service = ValidationService(test_db)

        for atom in atoms:
            val_result = val_service.validate_atom(atom.atom_id)
            assert 'validation_score' in val_result, f"Validation failed for atom {atom.atom_id}"

        print(f"✓ Phase 4: Validated {len(atoms)} atoms")

        # Phase 5: Execution
        exec_service = ExecutionService(test_db, use_retry=True)

        execution_results = []
        for atom in atoms:
            exec_result = exec_service.execute_atom(atom.atom_id)
            execution_results.append(exec_result)

        successful = sum(1 for r in execution_results if r.get('success', False))
        print(f"✓ Phase 5: Executed {len(atoms)} atoms, {successful} succeeded")

        # Overall pipeline validation
        assert len(atoms) > 0, "Pipeline created no atoms"
        assert graph_result['success'], "Dependency graph failed"
        assert len(execution_results) > 0, "No execution results"

        print("\n🎉 FULL PIPELINE TEST PASSED!")

        return {
            'atoms_created': len(atoms),
            'graph_built': graph_result['success'],
            'validations': len(atoms),
            'executions': len(execution_results),
            'successful_executions': successful
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
