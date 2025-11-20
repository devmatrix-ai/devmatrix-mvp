"""
DAG Builder for Cognitive Architecture with Neo4j

Constructs and manages Directed Acyclic Graphs (DAGs) representing atomic task
dependencies using Neo4j graph database. Provides cycle detection, topological
sorting, and parallelization level assignment.

Key Features:
- Neo4j graph storage for task dependencies
- Cypher-based cycle detection
- Topological sorting by dependency levels
- Parallelization level assignment
- Query optimization for <1s performance

Spec Reference: Section 3.6 - DAG Builder (Neo4j)
Target Coverage: >90%
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class DAGBuilder:
    """
    DAG Builder for atomic task dependency management using Neo4j.

    Manages graph construction, cycle detection, topological sorting,
    and parallelization level assignment for cognitive planning system.

    Example:
        >>> builder = DAGBuilder(uri="bolt://localhost:7687", user="neo4j", password="password")
        >>> builder.initialize_schema()
        >>> dag_id = builder.build_dag(atomic_tasks)
        >>> levels = builder.topological_sort(dag_id)
        >>> builder.close()
    """

    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        """
        Initialize DAG Builder with Neo4j connection.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"DAGBuilder initialized with Neo4j at {uri}")

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed")

    def initialize_schema(self):
        """
        Initialize Neo4j schema with constraints and indexes.

        Creates:
        - Unique constraint on AtomicTask.id
        - Index on AtomicTask.dag_id for fast filtering
        - Index on AtomicTask.level for parallelization queries
        """
        with self.driver.session() as session:
            # Create unique constraint on task ID
            session.run("""
                CREATE CONSTRAINT atomic_task_id_unique IF NOT EXISTS
                FOR (t:AtomicTask)
                REQUIRE t.id IS UNIQUE
            """)

            # Create index on dag_id for fast DAG filtering
            session.run("""
                CREATE INDEX atomic_task_dag_id IF NOT EXISTS
                FOR (t:AtomicTask)
                ON (t.dag_id)
            """)

            # Create index on level for parallelization queries
            session.run("""
                CREATE INDEX atomic_task_level IF NOT EXISTS
                FOR (t:AtomicTask)
                ON (t.level)
            """)

            logger.info("Neo4j schema initialized successfully")

    def build_dag(self, atomic_tasks: List[Dict[str, Any]]) -> str:
        """
        Build DAG from atomic tasks in Neo4j.

        Creates nodes for each atomic task and DEPENDS_ON relationships
        based on task dependencies.

        Args:
            atomic_tasks: List of atomic task dictionaries with keys:
                - id: Task identifier (required)
                - name: Meaningful task name (required, prevents name=None)
                - purpose: Task purpose/description (required)
                - domain: Task domain (optional, default: "general")
                - intent: Task intent/action type (optional)
                - max_loc: Maximum lines of code (optional, default: 10)
                - depends_on: List of task IDs this task depends on (optional, default: [])

        Returns:
            dag_id: Unique identifier for this DAG

        Example:
            >>> tasks = [
            ...     {"id": "atom_1", "name": "validation_validate_input", "purpose": "Validate",
            ...      "domain": "validation", "intent": "validate", "depends_on": []},
            ...     {"id": "atom_2", "name": "processing_transform_data", "purpose": "Process",
            ...      "domain": "processing", "intent": "transform", "depends_on": ["atom_1"]}
            ... ]
            >>> dag_id = builder.build_dag(tasks)
        """
        dag_id = f"dag_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow().isoformat()

        with self.driver.session() as session:
            # Create nodes for each atomic task
            for task in atomic_tasks:
                task_id = task.get("id", "")
                task_name = task.get("name", "")  # Extract name from task dictionary
                purpose = task.get("purpose", "")
                domain = task.get("domain", "general")
                intent = task.get("intent", "")
                max_loc = task.get("max_loc", 10)

                # CRITICAL FIX: Always persist task name to prevent name=None nodes
                # If name is missing from task dict, generate one from id as fallback
                if not task_name:
                    task_name = task_id.replace("atom_", "unnamed_task_")
                    logger.warning(f"Task {task_id} missing 'name' field, generated fallback: {task_name}")

                session.run("""
                    MERGE (t:AtomicTask {id: $task_id})
                    SET t.dag_id = $dag_id,
                        t.name = $task_name,
                        t.purpose = $purpose,
                        t.domain = $domain,
                        t.intent = $intent,
                        t.max_loc = $max_loc,
                        t.created_at = $timestamp
                """, task_id=task_id, dag_id=dag_id, task_name=task_name, purpose=purpose, domain=domain,
                    intent=intent, max_loc=max_loc, timestamp=timestamp)

            # Create DEPENDS_ON relationships
            for task in atomic_tasks:
                task_id = task.get("id", "")
                dependencies = task.get("depends_on", [])

                for dep_id in dependencies:
                    session.run("""
                        MATCH (t:AtomicTask {id: $task_id}),
                              (d:AtomicTask {id: $dep_id})
                        MERGE (t)-[:DEPENDS_ON]->(d)
                    """, task_id=task_id, dep_id=dep_id)

        logger.info(f"DAG {dag_id} built with {len(atomic_tasks)} tasks")
        return dag_id

    def detect_cycles(self, dag_id: str) -> List[List[str]]:
        """
        Detect circular dependencies in DAG using Neo4j Cypher.

        Uses Cypher pattern matching to find paths where a task depends on itself
        through a chain of DEPENDS_ON relationships.

        Args:
            dag_id: DAG identifier to check

        Returns:
            List of cycles, where each cycle is a list of task IDs forming the cycle.
            Empty list if no cycles found.

        Example:
            >>> cycles = builder.detect_cycles("dag_abc123")
            >>> if cycles:
            ...     print(f"Found {len(cycles)} cycle(s)")
        """
        with self.driver.session() as session:
            # Find cycles: tasks that depend on themselves through a path
            result = session.run("""
                MATCH path = (t:AtomicTask)-[:DEPENDS_ON*]->(t)
                WHERE t.dag_id = $dag_id
                RETURN [node in nodes(path) | node.id] as cycle
            """, dag_id=dag_id)

            cycles = []
            for record in result:
                cycle = record.get("cycle", [])
                if cycle:
                    cycles.append(cycle)

        if cycles:
            logger.warning(f"Detected {len(cycles)} cycle(s) in DAG {dag_id}")
        else:
            logger.info(f"No cycles detected in DAG {dag_id}")

        return cycles

    def topological_sort(self, dag_id: str) -> Dict[int, List[str]]:
        """
        Perform topological sort on DAG to assign dependency levels.

        Assigns each task to a level based on its position in the dependency chain:
        - Level 0: Tasks with no dependencies
        - Level 1: Tasks depending only on Level 0 tasks
        - Level N: Tasks depending on Level N-1 (or lower) tasks

        Args:
            dag_id: DAG identifier to sort

        Returns:
            Dictionary mapping level (int) to list of task IDs at that level

        Example:
            >>> levels = builder.topological_sort("dag_abc123")
            >>> print(f"Level 0 tasks: {levels[0]}")  # Can execute first
            >>> print(f"Level 1 tasks: {levels[1]}")  # Depend on Level 0
        """
        with self.driver.session() as session:
            # Calculate level for each task using Cypher
            # Level = length of longest path to a root task (task with no dependencies)
            session.run("""
                MATCH (t:AtomicTask)
                WHERE t.dag_id = $dag_id
                OPTIONAL MATCH path = (t)-[:DEPENDS_ON*]->(root:AtomicTask)
                WHERE NOT exists((root)-[:DEPENDS_ON]->())
                WITH t, COALESCE(MAX(length(path)), 0) as level
                SET t.level = level
            """, dag_id=dag_id)

            # Retrieve tasks grouped by level
            result = session.run("""
                MATCH (t:AtomicTask)
                WHERE t.dag_id = $dag_id
                RETURN t.id as task_id, t.level as level
                ORDER BY t.level
            """, dag_id=dag_id)

            # Group tasks by level
            levels: Dict[int, List[str]] = {}
            for record in result:
                task_id = record["task_id"]
                level = record["level"]

                if level not in levels:
                    levels[level] = []
                levels[level].append(task_id)

        logger.info(f"Topological sort complete for DAG {dag_id}: {len(levels)} levels")
        return levels

    def assign_parallelization_levels(self, dag_id: str) -> Dict[int, List[str]]:
        """
        Assign parallelization levels to tasks.

        Tasks at the same level can execute in parallel since they have no
        dependencies on each other (only on previous levels).

        This is essentially the same as topological sort, but explicitly
        named for parallelization semantics.

        Args:
            dag_id: DAG identifier

        Returns:
            Dictionary mapping parallel level to list of task IDs

        Example:
            >>> parallel_levels = builder.assign_parallelization_levels("dag_abc123")
            >>> # All tasks in parallel_levels[0] can run simultaneously
            >>> # All tasks in parallel_levels[1] can run after level 0 completes
        """
        # Use topological sort as it already groups tasks by parallel execution levels
        parallel_levels = self.topological_sort(dag_id)

        logger.info(f"Parallelization levels assigned for DAG {dag_id}")
        return parallel_levels


# ============================================================================
# Module-Level Functions (for backward compatibility and convenience)
# ============================================================================

def initialize_neo4j_schema(uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
    """
    Initialize Neo4j schema (convenience function).

    Args:
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password
    """
    builder = DAGBuilder(uri=uri, user=user, password=password)
    builder.initialize_schema()
    builder.close()


def build_dag(
    atomic_tasks: List[Dict[str, Any]],
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "password"
) -> str:
    """
    Build DAG from atomic tasks (convenience function).

    Args:
        atomic_tasks: List of atomic task dictionaries
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password

    Returns:
        dag_id: Unique DAG identifier
    """
    builder = DAGBuilder(uri=uri, user=user, password=password)
    dag_id = builder.build_dag(atomic_tasks)
    builder.close()
    return dag_id


def detect_cycles(
    dag_id: str,
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "password"
) -> List[List[str]]:
    """
    Detect cycles in DAG (convenience function).

    Args:
        dag_id: DAG identifier
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password

    Returns:
        List of cycles found
    """
    builder = DAGBuilder(uri=uri, user=user, password=password)
    cycles = builder.detect_cycles(dag_id)
    builder.close()
    return cycles


def topological_sort(
    dag_id: str,
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "password"
) -> Dict[int, List[str]]:
    """
    Perform topological sort on DAG (convenience function).

    Args:
        dag_id: DAG identifier
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password

    Returns:
        Dictionary mapping level to task IDs
    """
    builder = DAGBuilder(uri=uri, user=user, password=password)
    levels = builder.topological_sort(dag_id)
    builder.close()
    return levels


def assign_parallelization_levels(
    dag_id: str,
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "password"
) -> Dict[int, List[str]]:
    """
    Assign parallelization levels (convenience function).

    Args:
        dag_id: DAG identifier
        uri: Neo4j connection URI
        user: Neo4j username
        password: str = "password"

    Returns:
        Dictionary mapping parallel level to task IDs
    """
    builder = DAGBuilder(uri=uri, user=user, password=password)
    parallel_levels = builder.assign_parallelization_levels(dag_id)
    builder.close()
    return parallel_levels
