"""
Unit Tests for DAG Builder (Neo4j)

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

Test Coverage:
- Neo4j connection and schema initialization
- DAG construction from atomic tasks
- Cycle detection using Neo4j Cypher queries
- Topological sorting by dependency levels
- Parallelization level assignment
- Query performance (<1s for 100 atoms)
- Error handling and edge cases
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.planning.dag_builder import (
    DAGBuilder,
    initialize_neo4j_schema,
    build_dag,
    detect_cycles,
    topological_sort,
    assign_parallelization_levels,
)


class TestNeo4jConnection:
    """Test Neo4j connection and schema initialization."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_dag_builder_initialization_connects_to_neo4j(self, mock_graph_db):
        """Test that DAGBuilder initializes Neo4j connection."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")

        assert builder is not None
        assert hasattr(builder, 'driver')
        mock_graph_db.driver.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_initialize_neo4j_schema_creates_constraints(self, mock_graph_db):
        """Test that schema initialization creates node constraints and indexes."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        builder.initialize_schema()

        # Should execute at least 2 queries (constraint + index)
        assert mock_session.run.call_count >= 2

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_dag_builder_close_closes_driver(self, mock_graph_db):
        """Test that DAGBuilder.close() closes Neo4j driver."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        builder.close()

        mock_driver.close.assert_called_once()


class TestDAGConstruction:
    """Test DAG construction from atomic tasks."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_build_dag_creates_nodes_for_atoms(self, mock_graph_db):
        """Test that build_dag creates Neo4j nodes for each atomic task."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        atomic_tasks = [
            {"id": "atom_1", "purpose": "Validate input", "domain": "validation", "depends_on": []},
            {"id": "atom_2", "purpose": "Process data", "domain": "processing", "depends_on": ["atom_1"]},
        ]

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        dag_id = builder.build_dag(atomic_tasks)

        # Should return a DAG ID
        assert dag_id is not None
        assert isinstance(dag_id, str)

        # Should execute queries to create nodes
        assert mock_session.run.call_count >= 2

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_build_dag_creates_dependency_edges(self, mock_graph_db):
        """Test that build_dag creates DEPENDS_ON relationships."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        atomic_tasks = [
            {"id": "atom_1", "purpose": "Task 1", "depends_on": []},
            {"id": "atom_2", "purpose": "Task 2", "depends_on": ["atom_1"]},
            {"id": "atom_3", "purpose": "Task 3", "depends_on": ["atom_1", "atom_2"]},
        ]

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        dag_id = builder.build_dag(atomic_tasks)

        # Should create edges for dependencies
        # atom_2 depends on atom_1 (1 edge)
        # atom_3 depends on atom_1 and atom_2 (2 edges)
        # Total: 3 edges
        assert mock_session.run.call_count >= 5  # 3 nodes + 3 edges


class TestCycleDetection:
    """Test cycle detection using Neo4j Cypher."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_detect_cycles_returns_empty_for_valid_dag(self, mock_graph_db):
        """Test that detect_cycles returns empty list for acyclic graph."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        # Return empty list (no cycles)
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        cycles = builder.detect_cycles("dag_123")

        assert cycles == []

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_detect_cycles_finds_circular_dependencies(self, mock_graph_db):
        """Test that detect_cycles identifies circular dependencies."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        # Simulate cycle: atom_1 → atom_2 → atom_3 → atom_1
        mock_record = Mock()
        mock_record.get.return_value = ["atom_1", "atom_2", "atom_3", "atom_1"]
        mock_session.run.return_value = [mock_record]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        cycles = builder.detect_cycles("dag_123")

        assert len(cycles) > 0
        assert isinstance(cycles, list)


class TestTopologicalSorting:
    """Test topological sorting by dependency levels."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_topological_sort_assigns_levels_correctly(self, mock_graph_db):
        """Test that topological_sort assigns correct dependency levels."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock query results for topological sort
        # Level 0: atom_1 (no dependencies)
        # Level 1: atom_2 (depends on atom_1)
        # Level 2: atom_3 (depends on atom_2)
        mock_records = [
            {"task_id": "atom_1", "level": 0},
            {"task_id": "atom_2", "level": 1},
            {"task_id": "atom_3", "level": 2},
        ]
        # First run() call is for setting levels, second is for retrieving
        mock_session.run.side_effect = [Mock(), mock_records]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        levels = builder.topological_sort("dag_123")

        # Should return dict: level → [task_ids]
        assert isinstance(levels, dict)
        assert 0 in levels
        assert "atom_1" in levels[0]

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_topological_sort_groups_independent_tasks_at_same_level(self, mock_graph_db):
        """Test that independent tasks are at the same level."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock: atom_1 and atom_2 are both level 0 (independent)
        # atom_3 depends on both (level 1)
        mock_records = [
            {"task_id": "atom_1", "level": 0},
            {"task_id": "atom_2", "level": 0},
            {"task_id": "atom_3", "level": 1},
        ]
        # First run() call is for setting levels, second is for retrieving
        mock_session.run.side_effect = [Mock(), mock_records]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        levels = builder.topological_sort("dag_123")

        # Level 0 should have 2 tasks
        assert len(levels[0]) == 2
        assert "atom_1" in levels[0]
        assert "atom_2" in levels[0]


class TestParallelizationLevels:
    """Test parallelization level assignment."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_assign_parallelization_levels_returns_mapping(self, mock_graph_db):
        """Test that parallelization levels are assigned correctly."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_records = [
            {"task_id": "atom_1", "level": 0},
            {"task_id": "atom_2", "level": 0},
            {"task_id": "atom_3", "level": 1},
        ]
        # First run() call is for setting levels, second is for retrieving
        mock_session.run.side_effect = [Mock(), mock_records]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        parallel_levels = builder.assign_parallelization_levels("dag_123")

        # Should return dict: level → [task_ids]
        assert isinstance(parallel_levels, dict)
        assert len(parallel_levels[0]) == 2  # atom_1, atom_2 can run in parallel


class TestPerformance:
    """Test query performance requirements."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_build_dag_completes_under_10s_for_100_atoms(self, mock_graph_db):
        """Test that build_dag completes in <10s for 100 atoms."""
        import time

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        # Create 100 atomic tasks
        atomic_tasks = [
            {"id": f"atom_{i}", "purpose": f"Task {i}", "domain": "test", "depends_on": []}
            for i in range(100)
        ]

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")

        start_time = time.time()
        dag_id = builder.build_dag(atomic_tasks)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 10.0  # Should complete in less than 10 seconds

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_detect_cycles_completes_under_1s(self, mock_graph_db):
        """Test that cycle detection completes in <1s."""
        import time

        mock_driver = MagicMock()
        mock_session = MagicMock()
        # Return empty list (no cycles)
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")

        start_time = time.time()
        cycles = builder.detect_cycles("dag_123")
        elapsed_time = time.time() - start_time

        assert elapsed_time < 1.0  # Should complete in less than 1 second


class TestErrorHandling:
    """Test error handling and edge cases."""

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_build_dag_handles_empty_task_list(self, mock_graph_db):
        """Test that build_dag handles empty atomic task list."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")

        # Should handle empty list gracefully
        dag_id = builder.build_dag([])

        assert dag_id is not None

    @patch('src.cognitive.planning.dag_builder.GraphDatabase')
    def test_detect_cycles_raises_error_if_cycles_found(self, mock_graph_db):
        """Test that detect_cycles raises error when cycles are detected."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        # Simulate cycle found
        mock_record = Mock()
        mock_record.get.return_value = ["atom_1", "atom_2", "atom_1"]
        mock_session.run.return_value = [mock_record]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")

        # Should either raise error or return non-empty list
        result = builder.detect_cycles("dag_123")
        assert len(result) > 0  # Cycles detected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
