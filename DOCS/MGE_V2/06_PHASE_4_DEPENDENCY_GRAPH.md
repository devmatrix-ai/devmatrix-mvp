# Phase 4: Dependency Graph

**Document**: 06 of 15
**Purpose**: Build dependency graph, topological sort, and parallel execution planning

---

## Overview

**Phase 4 solves the compound error problem** by ensuring dependencies are generated BEFORE dependents.

**Key Innovation**: Topological ordering prevents error cascade.

---

## The Problem (Recap)

**Without dependency ordering**:
```python
# Wrong order: Generate in random sequence
Atom 50: verify_user() generated first
  → References user.email_verified (doesn't exist yet!)
  → LLM invents it or fails

Atom 1: User model generated later
  → Has email_verified field
  → But Atom 50 already has wrong reference!
```

**With dependency ordering**:
```python
# Right order: Generate dependencies first
Atom 1: User model generated first
  → Defines email_verified field
  → Validated ✅

Atom 50: verify_user() generated second
  → Sees validated Atom 1 with correct field
  → References email_verified correctly ✅
```

---

## Architecture

```
AtomicUnits (from Phase 3)
└─> Dependency Analyzer
    └─> Build Graph (NetworkX or Neo4j)
        └─> Detect Cycles
            └─> Topological Sort
                └─> Identify Parallel Groups
                    └─> Calculate Execution Order
                        └─> Store in PostgreSQL
```

---

## Component 1: Dependency Analyzer

### Dependency Types

```python
from enum import Enum

class DependencyType(Enum):
    """Types of dependencies between atoms."""

    IMPORT = "import"           # Import statements
    DATA = "data"               # Data flow (function calls, variable references)
    CONTROL = "control"         # Control flow (if depends on condition)
    TYPE = "type"               # Type dependencies (class inheritance)
    TEMPORAL = "temporal"       # Must execute in order (database migrations)

class DependencyStrength(Enum):
    """Strength of dependency relationship."""

    REQUIRED = 1.0      # Hard dependency - must execute first
    PREFERRED = 0.7     # Soft dependency - better if executes first
    OPTIONAL = 0.3      # Nice to have - no strict requirement
```

### Implementation

```python
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

@dataclass
class Dependency:
    """Represents a dependency between two atoms."""
    from_atom_id: str
    to_atom_id: str
    dependency_type: DependencyType
    strength: float  # 0.0 - 1.0
    reason: str  # Human-readable explanation

class DependencyAnalyzer:
    """
    Analyze dependencies between atomic units.
    """

    def __init__(self, atoms: List[AtomicUnit]):
        self.atoms = {a.id: a for a in atoms}
        self.dependencies = []

    def analyze_all_dependencies(self) -> List[Dependency]:
        """
        Analyze dependencies for all atoms.

        Returns:
            List of Dependency objects
        """
        print("🔍 Analyzing dependencies...")

        for atom in self.atoms.values():
            # Analyze each dependency already identified in atom
            for dep_id in atom.depends_on:
                dep = self._analyze_dependency(atom.id, dep_id)
                if dep:
                    self.dependencies.append(dep)

            # Discover additional dependencies
            additional_deps = self._discover_implicit_dependencies(atom)
            self.dependencies.extend(additional_deps)

        print(f"  ✅ Found {len(self.dependencies)} dependencies")

        # Remove duplicates
        self.dependencies = self._deduplicate_dependencies(self.dependencies)

        return self.dependencies

    def _analyze_dependency(
        self,
        from_id: str,
        to_id: str
    ) -> Dependency:
        """
        Analyze a specific dependency relationship.

        Args:
            from_id: Dependent atom ID
            to_id: Dependency atom ID

        Returns:
            Dependency object with type and strength
        """
        from_atom = self.atoms[from_id]
        to_atom = self.atoms[to_id]

        # Determine dependency type
        dep_type = self._determine_dependency_type(from_atom, to_atom)

        # Calculate strength
        strength = self._calculate_dependency_strength(from_atom, to_atom, dep_type)

        # Generate explanation
        reason = self._explain_dependency(from_atom, to_atom, dep_type)

        return Dependency(
            from_atom_id=from_id,
            to_atom_id=to_id,
            dependency_type=dep_type,
            strength=strength,
            reason=reason
        )

    def _determine_dependency_type(
        self,
        from_atom: AtomicUnit,
        to_atom: AtomicUnit
    ) -> DependencyType:
        """
        Determine the type of dependency.

        Logic:
        1. If to_atom is import → IMPORT
        2. If from_atom calls function in to_atom → DATA
        3. If from_atom inherits from class in to_atom → TYPE
        4. Else → DATA (default)
        """
        # Check import
        if to_atom.node_type in ['import_statement', 'import_from_statement']:
            return DependencyType.IMPORT

        # Check type dependency (inheritance)
        if 'class' in to_atom.node_type.lower() and 'class' in from_atom.node_type.lower():
            # Check if from_atom inherits from to_atom
            if self._check_inheritance(from_atom, to_atom):
                return DependencyType.TYPE

        # Check function call (data dependency)
        if 'function' in to_atom.node_type.lower():
            if self._check_function_call(from_atom, to_atom):
                return DependencyType.DATA

        # Default: data dependency
        return DependencyType.DATA

    def _calculate_dependency_strength(
        self,
        from_atom: AtomicUnit,
        to_atom: AtomicUnit,
        dep_type: DependencyType
    ) -> float:
        """
        Calculate dependency strength (0.0 - 1.0).

        Factors:
        - Dependency type (IMPORT=1.0, TYPE=0.9, DATA=0.8)
        - Number of references
        - Context importance
        """
        # Base strength by type
        base_strength = {
            DependencyType.IMPORT: 1.0,
            DependencyType.TYPE: 0.9,
            DependencyType.DATA: 0.8,
            DependencyType.CONTROL: 0.85,
            DependencyType.TEMPORAL: 1.0
        }

        strength = base_strength.get(dep_type, 0.7)

        # Adjust based on reference count
        ref_count = self._count_references(from_atom, to_atom)
        if ref_count > 3:
            strength = min(1.0, strength + 0.1)

        # Adjust based on criticality
        if self._is_critical_dependency(from_atom, to_atom):
            strength = 1.0

        return strength

    def _explain_dependency(
        self,
        from_atom: AtomicUnit,
        to_atom: AtomicUnit,
        dep_type: DependencyType
    ) -> str:
        """Generate human-readable explanation."""
        explanations = {
            DependencyType.IMPORT: f"{from_atom.name} imports from {to_atom.name}",
            DependencyType.DATA: f"{from_atom.name} calls/references {to_atom.name}",
            DependencyType.TYPE: f"{from_atom.name} inherits from {to_atom.name}",
            DependencyType.CONTROL: f"{from_atom.name} control flow depends on {to_atom.name}",
            DependencyType.TEMPORAL: f"{from_atom.name} must execute after {to_atom.name}"
        }

        return explanations.get(dep_type, f"{from_atom.name} depends on {to_atom.name}")

    def _discover_implicit_dependencies(
        self,
        atom: AtomicUnit
    ) -> List[Dependency]:
        """
        Discover dependencies not explicitly marked.

        Strategies:
        1. Analyze imports
        2. Find function calls
        3. Check variable references
        4. Detect class inheritance
        """
        implicit_deps = []

        # Already-marked dependencies
        marked = set(atom.depends_on)

        # Check all other atoms
        for other_id, other_atom in self.atoms.items():
            if other_id == atom.id or other_id in marked:
                continue

            # Check if atom references other_atom
            if self._has_implicit_dependency(atom, other_atom):
                dep = Dependency(
                    from_atom_id=atom.id,
                    to_atom_id=other_id,
                    dependency_type=DependencyType.DATA,
                    strength=0.7,
                    reason=f"Implicit: {atom.name} references {other_atom.name}"
                )
                implicit_deps.append(dep)

        return implicit_deps

    def _has_implicit_dependency(
        self,
        from_atom: AtomicUnit,
        to_atom: AtomicUnit
    ) -> bool:
        """
        Check if from_atom implicitly depends on to_atom.

        Simple heuristic: Check if to_atom's name appears in from_atom's code.
        """
        # Extract definition names from to_atom
        to_definitions = self._extract_definition_names(to_atom)

        # Check if any appear in from_atom
        for definition in to_definitions:
            if definition in from_atom.code:
                return True

        return False

    def _extract_definition_names(self, atom: AtomicUnit) -> Set[str]:
        """Extract function/class/variable names defined in atom."""
        names = set()

        # Extract from atom name
        if ':' in atom.name:
            name = atom.name.split(':')[1].strip()
            names.add(name)

        # Extract from code (simplified)
        import re

        # Functions
        func_matches = re.findall(r'def\s+(\w+)', atom.code)
        names.update(func_matches)

        # Classes
        class_matches = re.findall(r'class\s+(\w+)', atom.code)
        names.update(class_matches)

        return names

    def _check_inheritance(self, from_atom: AtomicUnit, to_atom: AtomicUnit) -> bool:
        """Check if from_atom inherits from to_atom."""
        # Extract class names
        to_class = self._extract_class_name(to_atom)
        if not to_class:
            return False

        # Check if to_class appears in from_atom's class definition
        import re
        inheritance_pattern = rf'class\s+\w+\([^)]*{to_class}[^)]*\)'
        return bool(re.search(inheritance_pattern, from_atom.code))

    def _extract_class_name(self, atom: AtomicUnit) -> str:
        """Extract class name from atom."""
        import re
        match = re.search(r'class\s+(\w+)', atom.code)
        return match.group(1) if match else None

    def _check_function_call(self, from_atom: AtomicUnit, to_atom: AtomicUnit) -> bool:
        """Check if from_atom calls function in to_atom."""
        func_name = self._extract_function_name(to_atom)
        if not func_name:
            return False

        # Check if func_name appears as function call in from_atom
        import re
        call_pattern = rf'{func_name}\s*\('
        return bool(re.search(call_pattern, from_atom.code))

    def _extract_function_name(self, atom: AtomicUnit) -> str:
        """Extract function name from atom."""
        import re
        match = re.search(r'def\s+(\w+)', atom.code)
        return match.group(1) if match else None

    def _count_references(self, from_atom: AtomicUnit, to_atom: AtomicUnit) -> int:
        """Count how many times from_atom references to_atom."""
        to_names = self._extract_definition_names(to_atom)

        count = 0
        for name in to_names:
            count += from_atom.code.count(name)

        return count

    def _is_critical_dependency(
        self,
        from_atom: AtomicUnit,
        to_atom: AtomicUnit
    ) -> bool:
        """
        Check if dependency is critical (strength = 1.0).

        Critical if:
        - to_atom is import
        - to_atom is base class
        - from_atom cannot work without to_atom
        """
        # Imports are always critical
        if to_atom.node_type in ['import_statement', 'import_from_statement']:
            return True

        # Base classes are critical
        if self._check_inheritance(from_atom, to_atom):
            return True

        return False

    def _deduplicate_dependencies(
        self,
        dependencies: List[Dependency]
    ) -> List[Dependency]:
        """Remove duplicate dependencies."""
        seen = set()
        unique = []

        for dep in dependencies:
            key = (dep.from_atom_id, dep.to_atom_id)
            if key not in seen:
                seen.add(key)
                unique.append(dep)

        return unique
```

---

## Component 2: Graph Builder

### Using NetworkX (Recommended)

**Why NetworkX?**
- Pure Python (easy install)
- Excellent algorithms (topological sort, cycle detection)
- Good performance for 800 nodes
- Well-documented
- Can export to Neo4j later if needed

### Implementation

```python
import networkx as nx
from typing import List, Set, Tuple

class DependencyGraph:
    """
    Build and analyze dependency graph using NetworkX.
    """

    def __init__(self):
        # Directed graph (edges point from dependent → dependency)
        self.graph = nx.DiGraph()

        # Metadata
        self.atoms = {}
        self.dependencies = []

    def build_from_atoms(
        self,
        atoms: List[AtomicUnit],
        dependencies: List[Dependency]
    ):
        """
        Build graph from atoms and dependencies.

        Graph structure:
        - Nodes: Atomic units (with metadata)
        - Edges: Dependencies (from dependent TO dependency)
        """
        print("🏗️ Building dependency graph...")

        # Store for reference
        self.atoms = {a.id: a for a in atoms}
        self.dependencies = dependencies

        # Add nodes
        for atom in atoms:
            self.graph.add_node(
                atom.id,
                name=atom.name,
                atom_number=atom.atom_number,
                estimated_loc=atom.estimated_loc,
                complexity=atom.complexity,
                node_type=atom.node_type
            )

        # Add edges (from dependent TO dependency)
        for dep in dependencies:
            self.graph.add_edge(
                dep.from_atom_id,  # Source: dependent
                dep.to_atom_id,     # Target: dependency
                dependency_type=dep.dependency_type.value,
                strength=dep.strength,
                reason=dep.reason
            )

        print(f"  ✅ Graph: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")

    def validate_graph(self) -> Tuple[bool, List[str]]:
        """
        Validate graph for issues.

        Checks:
        1. No cycles (DAG required)
        2. No isolated components (all connected)
        3. No self-loops

        Returns:
            (is_valid, errors)
        """
        errors = []

        # Check for cycles
        if not nx.is_directed_acyclic_graph(self.graph):
            cycles = list(nx.simple_cycles(self.graph))
            errors.append(f"CRITICAL: Graph has {len(cycles)} cycles")

            # Show first cycle
            if cycles:
                cycle = cycles[0]
                cycle_names = [self.graph.nodes[n]['name'] for n in cycle]
                errors.append(f"  Example cycle: {' → '.join(cycle_names)}")

        # Check for self-loops
        self_loops = list(nx.nodes_with_selfloops(self.graph))
        if self_loops:
            errors.append(f"CRITICAL: {len(self_loops)} atoms depend on themselves")

        # Check connectivity (warning, not error)
        if not nx.is_weakly_connected(self.graph):
            num_components = nx.number_weakly_connected_components(self.graph)
            errors.append(f"WARNING: Graph has {num_components} disconnected components")

        is_valid = len([e for e in errors if 'CRITICAL' in e]) == 0

        return is_valid, errors

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect all cycles in the graph.

        Returns:
            List of cycles (each cycle is list of atom IDs)
        """
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except nx.NetworkXNoCycle:
            return []

    def get_strongly_connected_components(self) -> List[Set[str]]:
        """
        Find strongly connected components (potential cycle groups).

        Returns:
            List of components (each is set of atom IDs)
        """
        return list(nx.strongly_connected_components(self.graph))

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort to get generation order.

        Returns:
            List of atom IDs in dependency order (dependencies first)

        Raises:
            NetworkXError if graph has cycles
        """
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Cannot topologically sort graph with cycles")

        # Topological sort
        # Result: dependencies appear before dependents
        return list(nx.topological_sort(self.graph))

    def identify_parallel_groups(self) -> List[Set[str]]:
        """
        Identify atoms that can be generated in parallel.

        Strategy:
        1. Group by topological level
        2. Atoms at same level have no dependencies on each other

        Returns:
            List of parallel groups (each is set of atom IDs)
        """
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Cannot identify parallel groups in cyclic graph")

        # Get topological generations (levels)
        generations = list(nx.topological_generations(self.graph))

        # Convert to sets for easier manipulation
        parallel_groups = [set(gen) for gen in generations]

        print(f"  ✅ Found {len(parallel_groups)} parallel execution levels")

        # Show distribution
        for i, group in enumerate(parallel_groups):
            print(f"     Level {i}: {len(group)} atoms (parallel)")

        return parallel_groups

    def calculate_critical_path(self) -> Tuple[List[str], float]:
        """
        Calculate critical path (longest path in graph).

        Critical path determines minimum execution time.

        Returns:
            (path, total_complexity)
        """
        # Use longest path algorithm
        # Weight by complexity (higher complexity = longer execution)

        # Add weight attribute
        for node in self.graph.nodes:
            atom = self.atoms[node]
            self.graph.nodes[node]['weight'] = atom.complexity

        # Find longest path
        try:
            path = nx.dag_longest_path(self.graph, weight='weight')
            total_complexity = sum(self.graph.nodes[n]['weight'] for n in path)

            return path, total_complexity
        except nx.NetworkXError:
            return [], 0.0

    def get_execution_order(self) -> List[Tuple[int, Set[str]]]:
        """
        Get complete execution order with parallel groups.

        Returns:
            List of (level, atom_ids) tuples
        """
        parallel_groups = self.identify_parallel_groups()

        execution_order = [
            (level, group)
            for level, group in enumerate(parallel_groups)
        ]

        return execution_order

    def visualize_graph(self, output_path: str):
        """
        Visualize graph (requires matplotlib).

        Args:
            output_path: Path to save image
        """
        import matplotlib.pyplot as plt

        pos = nx.spring_layout(self.graph, k=0.5, iterations=50)

        # Draw nodes
        nx.draw_networkx_nodes(
            self.graph,
            pos,
            node_size=300,
            node_color='lightblue',
            alpha=0.8
        )

        # Draw edges
        nx.draw_networkx_edges(
            self.graph,
            pos,
            edge_color='gray',
            arrows=True,
            arrowsize=10,
            alpha=0.5
        )

        # Draw labels
        labels = {n: self.graph.nodes[n]['name'][:20] for n in self.graph.nodes}
        nx.draw_networkx_labels(
            self.graph,
            pos,
            labels,
            font_size=8
        )

        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  ✅ Graph visualization saved to {output_path}")

    def export_to_neo4j(self, neo4j_uri: str, username: str, password: str):
        """
        Export graph to Neo4j database (optional).

        Args:
            neo4j_uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
        """
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))

        with driver.session() as session:
            # Clear existing data
            session.run("MATCH (n:Atom) DETACH DELETE n")

            # Create nodes
            for node_id in self.graph.nodes:
                atom = self.atoms[node_id]
                session.run("""
                    CREATE (a:Atom {
                        id: $id,
                        name: $name,
                        atom_number: $atom_number,
                        estimated_loc: $estimated_loc,
                        complexity: $complexity,
                        node_type: $node_type
                    })
                """, {
                    'id': node_id,
                    'name': atom.name,
                    'atom_number': atom.atom_number,
                    'estimated_loc': atom.estimated_loc,
                    'complexity': atom.complexity,
                    'node_type': atom.node_type
                })

            # Create edges
            for dep in self.dependencies:
                session.run("""
                    MATCH (from:Atom {id: $from_id})
                    MATCH (to:Atom {id: $to_id})
                    CREATE (from)-[:DEPENDS_ON {
                        type: $type,
                        strength: $strength,
                        reason: $reason
                    }]->(to)
                """, {
                    'from_id': dep.from_atom_id,
                    'to_id': dep.to_atom_id,
                    'type': dep.dependency_type.value,
                    'strength': dep.strength,
                    'reason': dep.reason
                })

        driver.close()
        print(f"  ✅ Graph exported to Neo4j at {neo4j_uri}")
```

---

## Component 3: Cycle Breaker

### Handling Cycles

**Cycles are BAD** - they create impossible execution order:
```
Atom A depends on Atom B
Atom B depends on Atom C
Atom C depends on Atom A  ← CYCLE!

Cannot generate: Need A before B, B before C, C before A
```

### Strategies

```python
class CycleBreaker:
    """
    Break cycles in dependency graph.
    """

    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def break_cycles(self) -> List[Tuple[str, str]]:
        """
        Break cycles by removing weakest edges.

        Strategy:
        1. Detect all cycles
        2. For each cycle, find weakest edge
        3. Remove edge
        4. Repeat until DAG

        Returns:
            List of removed edges (from_id, to_id)
        """
        removed_edges = []

        while not nx.is_directed_acyclic_graph(self.graph.graph):
            # Find one cycle
            cycle = next(nx.simple_cycles(self.graph.graph))

            # Find weakest edge in cycle
            weakest_edge = self._find_weakest_edge_in_cycle(cycle)

            # Remove edge
            from_id, to_id = weakest_edge
            self.graph.graph.remove_edge(from_id, to_id)

            removed_edges.append(weakest_edge)

            print(f"  ⚠️ Removed edge: {from_id} → {to_id} to break cycle")

        print(f"  ✅ Broke {len(removed_edges)} cycles")

        return removed_edges

    def _find_weakest_edge_in_cycle(self, cycle: List[str]) -> Tuple[str, str]:
        """
        Find weakest edge in cycle.

        Weakest = lowest strength or least critical dependency type.
        """
        edges_in_cycle = []

        for i in range(len(cycle)):
            from_id = cycle[i]
            to_id = cycle[(i + 1) % len(cycle)]

            if self.graph.graph.has_edge(from_id, to_id):
                edge_data = self.graph.graph.edges[from_id, to_id]
                edges_in_cycle.append((from_id, to_id, edge_data['strength']))

        # Sort by strength (ascending)
        edges_in_cycle.sort(key=lambda x: x[2])

        # Return weakest edge
        return edges_in_cycle[0][0], edges_in_cycle[0][1]

    def suggest_refactoring(self, cycle: List[str]) -> str:
        """
        Suggest refactoring to eliminate cycle.

        Common patterns:
        - Extract interface
        - Dependency injection
        - Merge atoms
        """
        cycle_names = [self.graph.graph.nodes[n]['name'] for n in cycle]

        suggestion = f"""
        Cycle detected: {' → '.join(cycle_names)}

        Refactoring suggestions:
        1. Extract common interface used by all atoms in cycle
        2. Use dependency injection instead of direct references
        3. Consider merging atoms in cycle into single larger unit
        4. Break circular logic by introducing intermediary
        """

        return suggestion
```

---

## Component 4: Execution Planner

### Generation Order

```python
from typing import List, Tuple, Set
from dataclasses import dataclass

@dataclass
class ExecutionLevel:
    """Represents a level in execution plan."""
    level: int
    atom_ids: Set[str]
    parallelizable: bool
    estimated_time: float  # seconds
    dependencies_completed: Set[int]  # Previous levels that must complete

class ExecutionPlanner:
    """
    Plan execution order with parallelization.
    """

    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def create_execution_plan(self) -> List[ExecutionLevel]:
        """
        Create complete execution plan.

        Returns:
            List of ExecutionLevels in order
        """
        print("📋 Creating execution plan...")

        # Get parallel groups
        parallel_groups = self.graph.identify_parallel_groups()

        # Build execution levels
        execution_plan = []

        for level, atom_ids in enumerate(parallel_groups):
            # Calculate estimated time
            estimated_time = self._estimate_level_time(atom_ids)

            # Determine dependencies (all previous levels)
            deps_completed = set(range(level))

            execution_level = ExecutionLevel(
                level=level,
                atom_ids=atom_ids,
                parallelizable=len(atom_ids) > 1,
                estimated_time=estimated_time,
                dependencies_completed=deps_completed
            )

            execution_plan.append(execution_level)

        # Print summary
        self._print_plan_summary(execution_plan)

        return execution_plan

    def _estimate_level_time(self, atom_ids: Set[str]) -> float:
        """
        Estimate execution time for a level (in seconds).

        Assumptions:
        - Each LOC takes ~2 seconds to generate
        - Parallel execution reduces time
        - Add overhead for validation
        """
        total_loc = sum(
            self.graph.atoms[aid].estimated_loc
            for aid in atom_ids
        )

        # Base time: 2 seconds per LOC
        base_time = total_loc * 2.0

        # Parallel factor (max 100 concurrent)
        parallel_factor = min(len(atom_ids), 100)

        # Parallel time
        parallel_time = base_time / parallel_factor

        # Add validation overhead (10%)
        total_time = parallel_time * 1.1

        return total_time

    def _print_plan_summary(self, plan: List[ExecutionLevel]):
        """Print execution plan summary."""
        print(f"\n📊 Execution Plan Summary:")
        print(f"  Total levels: {len(plan)}")

        total_atoms = sum(len(level.atom_ids) for level in plan)
        parallel_atoms = sum(len(level.atom_ids) for level in plan if level.parallelizable)

        print(f"  Total atoms: {total_atoms}")
        print(f"  Parallelizable: {parallel_atoms} ({parallel_atoms/total_atoms*100:.1f}%)")

        total_time = sum(level.estimated_time for level in plan)
        print(f"  Estimated time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")

        print(f"\n  Level breakdown:")
        for level in plan[:10]:  # Show first 10
            print(f"    Level {level.level}: {len(level.atom_ids)} atoms, {level.estimated_time:.1f}s")

        if len(plan) > 10:
            print(f"    ... ({len(plan) - 10} more levels)")

    def optimize_plan(self, plan: List[ExecutionLevel]) -> List[ExecutionLevel]:
        """
        Optimize execution plan.

        Optimizations:
        1. Merge small levels
        2. Load balance parallel groups
        3. Prioritize critical path
        """
        optimized = []

        # Merge small levels (< 5 atoms)
        buffer = []

        for level in plan:
            if len(level.atom_ids) < 5 and buffer:
                # Merge with buffer
                buffer[-1].atom_ids.update(level.atom_ids)
                buffer[-1].estimated_time = max(
                    buffer[-1].estimated_time,
                    level.estimated_time
                )
            else:
                # Add to buffer
                buffer.append(level)

        return buffer

    def save_to_database(self, plan: List[ExecutionLevel], project_id: str):
        """
        Save execution plan to PostgreSQL.
        """
        import psycopg2
        import json

        conn = psycopg2.connect(
            host="localhost",
            database="devmatrix",
            user="devmatrix_user",
            password="password"
        )

        cursor = conn.cursor()

        # Create execution plan table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_plans (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL,
                level INTEGER NOT NULL,
                atom_ids UUID[] NOT NULL,
                parallelizable BOOLEAN NOT NULL,
                estimated_time FLOAT NOT NULL,
                dependencies_completed INTEGER[] NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Insert plan levels
        for level in plan:
            cursor.execute("""
                INSERT INTO execution_plans (
                    project_id, level, atom_ids, parallelizable,
                    estimated_time, dependencies_completed
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                project_id,
                level.level,
                list(level.atom_ids),
                level.parallelizable,
                level.estimated_time,
                list(level.dependencies_completed)
            ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"  ✅ Execution plan saved to database")
```

---

## Complete Pipeline

```python
class DependencyGraphPipeline:
    """
    Complete Phase 4 pipeline.
    """

    def __init__(self):
        self.analyzer = None
        self.graph = None
        self.cycle_breaker = None
        self.planner = None

    def process_atoms(
        self,
        atoms: List[AtomicUnit]
    ) -> Tuple[DependencyGraph, List[ExecutionLevel]]:
        """
        Complete dependency graph processing.

        Args:
            atoms: List of atomic units from Phase 3

        Returns:
            (graph, execution_plan)
        """
        print("=" * 60)
        print("🔗 PHASE 4: DEPENDENCY GRAPH")
        print("=" * 60)

        # Step 1: Analyze dependencies
        self.analyzer = DependencyAnalyzer(atoms)
        dependencies = self.analyzer.analyze_all_dependencies()

        # Step 2: Build graph
        self.graph = DependencyGraph()
        self.graph.build_from_atoms(atoms, dependencies)

        # Step 3: Validate graph
        is_valid, errors = self.graph.validate_graph()

        if not is_valid:
            print("\n⚠️ Graph validation errors:")
            for error in errors:
                print(f"  {error}")

            # Try to break cycles
            if "cycle" in ' '.join(errors).lower():
                print("\n🔧 Attempting to break cycles...")
                self.cycle_breaker = CycleBreaker(self.graph)
                removed_edges = self.cycle_breaker.break_cycles()

                # Re-validate
                is_valid, errors = self.graph.validate_graph()

                if is_valid:
                    print("  ✅ Cycles successfully broken")
                else:
                    raise ValueError("Could not break all cycles")

        # Step 4: Create execution plan
        self.planner = ExecutionPlanner(self.graph)
        execution_plan = self.planner.create_execution_plan()

        # Step 5: Optimize plan
        execution_plan = self.planner.optimize_plan(execution_plan)

        print("\n✅ Phase 4 complete!\n")

        return self.graph, execution_plan
```

---

## Testing

```python
def test_dependency_analysis():
    """Test dependency analyzer."""
    # Create test atoms
    atom1 = AtomicUnit(
        id='a1', task_id='t1', atom_number=1,
        name='User Model', description='User class',
        language='python', code='class User: pass',
        estimated_loc=5, complexity=1.0,
        node_type='class_definition', depends_on=[], context={}
    )

    atom2 = AtomicUnit(
        id='a2', task_id='t1', atom_number=2,
        name='Create User', description='Function to create user',
        language='python', code='def create_user(data): return User(**data)',
        estimated_loc=3, complexity=1.0,
        node_type='function_definition', depends_on=['a1'], context={}
    )

    analyzer = DependencyAnalyzer([atom1, atom2])
    dependencies = analyzer.analyze_all_dependencies()

    assert len(dependencies) >= 1
    assert dependencies[0].to_atom_id == 'a1'
    assert dependencies[0].from_atom_id == 'a2'

def test_topological_sort():
    """Test topological sorting."""
    atoms = [
        AtomicUnit(id='a1', task_id='t', atom_number=1, name='A', description='', language='python', code='', estimated_loc=5, complexity=1.0, node_type='', depends_on=[], context={}),
        AtomicUnit(id='a2', task_id='t', atom_number=2, name='B', description='', language='python', code='', estimated_loc=5, complexity=1.0, node_type='', depends_on=['a1'], context={}),
        AtomicUnit(id='a3', task_id='t', atom_number=3, name='C', description='', language='python', code='', estimated_loc=5, complexity=1.0, node_type='', depends_on=['a2'], context={})
    ]

    dependencies = [
        Dependency('a2', 'a1', DependencyType.DATA, 1.0, 'test'),
        Dependency('a3', 'a2', DependencyType.DATA, 1.0, 'test')
    ]

    graph = DependencyGraph()
    graph.build_from_atoms(atoms, dependencies)

    order = graph.topological_sort()

    # a1 should come before a2, a2 before a3
    assert order.index('a1') < order.index('a2')
    assert order.index('a2') < order.index('a3')
```

---

## Performance Metrics

| Metric | Target | Why |
|--------|--------|-----|
| **Graph build time** | <10 seconds | Fast preprocessing |
| **Cycle detection** | <5 seconds | Quick validation |
| **Topological sort** | <5 seconds | O(V+E) algorithm |
| **Parallel groups** | 20-30 levels | Balanced parallelization |
| **Max parallel atoms** | 100+ | Leverage concurrent LLM calls |

---

## Next Phase

**Phase 5: Hierarchical Validation** → 4-level validation system

---

**Next Document**: [07_PHASE_5_HIERARCHICAL_VALIDATION.md](07_PHASE_5_HIERARCHICAL_VALIDATION.md) - Multi-level validation strategy
