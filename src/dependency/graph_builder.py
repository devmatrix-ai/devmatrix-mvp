"""
Graph Builder - Dependency Graph Construction

Analyzes atomic units and builds NetworkX dependency graph.

Dependency Detection:
1. Import dependencies (module A imports module B)
2. Function call dependencies (atom A calls function in atom B)
3. Variable dependencies (atom A uses variable defined in atom B)
4. Type dependencies (atom A uses type defined in atom B)

Graph Properties:
- Nodes: Atomic units (atom_id)
- Edges: Dependencies with type and weight
- Attributes: Node metadata, edge metadata

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import networkx as nx

from src.models import AtomicUnit

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies between atoms"""
    IMPORT = "import"           # Module import dependency
    FUNCTION_CALL = "function_call"  # Function call dependency
    VARIABLE = "variable"       # Variable usage dependency
    TYPE = "type"               # Type usage dependency
    DATA_FLOW = "data_flow"     # Data flow dependency


@dataclass
class Dependency:
    """Represents a dependency between two atoms"""
    source_atom_id: uuid.UUID
    target_atom_id: uuid.UUID
    dependency_type: DependencyType
    details: str
    weight: float = 1.0  # Dependency strength (0.0-1.0)


class GraphBuilder:
    """
    Graph builder for atomic dependency analysis

    Builds NetworkX directed graph where:
    - Nodes: Atomic units
    - Edges: Dependencies (source depends on target)

    Algorithm:
    1. Extract symbols from each atom (functions, variables, types)
    2. Match symbol usage across atoms
    3. Create edges for dependencies
    4. Calculate dependency weights
    """

    def __init__(self) -> None:
        """Initialize graph builder"""
        logger.info("GraphBuilder initialized")

    def build_graph(self, atoms: List[AtomicUnit]) -> nx.DiGraph:
        """
        Build dependency graph from atomic units

        Args:
            atoms: List of atomic units

        Returns:
            NetworkX directed graph with dependencies
        """
        logger.info(f"Building dependency graph for {len(atoms)} atoms")

        # Create graph
        graph = nx.DiGraph()

        # Add nodes (atoms)
        for atom in atoms:
            graph.add_node(
                str(atom.atom_id),
                atom_number=atom.atom_number,
                name=atom.name,
                loc=atom.loc,
                complexity=atom.complexity,
                file_path=atom.file_path,
                language=atom.language
            )

        # Extract symbols from each atom
        atom_symbols = self._extract_symbols(atoms)

        # Detect dependencies
        dependencies = self._detect_dependencies(atoms, atom_symbols)

        # Add edges (dependencies)
        for dep in dependencies:
            graph.add_edge(
                str(dep.source_atom_id),
                str(dep.target_atom_id),
                dependency_type=dep.dependency_type.value,
                details=dep.details,
                weight=dep.weight
            )

        logger.info(f"Graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        # Validate graph (check for issues)
        self._validate_graph(graph)

        return graph

    def _extract_symbols(self, atoms: List[AtomicUnit]) -> Dict[uuid.UUID, Dict[str, Set[str]]]:
        """
        Extract symbols (functions, variables, types) from each atom

        Returns:
            Dict mapping atom_id to symbols:
            {
                atom_id: {
                    'defines_functions': {'func1', 'func2'},
                    'defines_variables': {'var1', 'var2'},
                    'defines_types': {'Type1', 'Type2'},
                    'uses_functions': {'func3', 'func4'},
                    'uses_variables': {'var3', 'var4'},
                    'uses_types': {'Type3', 'Type4'},
                    'imports': {'module1', 'module2'}
                }
            }
        """
        symbols: Dict[uuid.UUID, Dict[str, Set[str]]] = {}

        for atom in atoms:
            atom_symbols: Dict[str, Set[str]] = {
                'defines_functions': set(),
                'defines_variables': set(),
                'defines_types': set(),
                'uses_functions': set(),
                'uses_variables': set(),
                'uses_types': set(),
                'imports': set()
            }

            code = atom.code_to_generate
            language = atom.language

            # Extract imports
            if atom.imports:
                for module in atom.imports.keys():
                    atom_symbols['imports'].add(module)

            # Extract definitions
            if language == "python":
                # Functions: def function_name(
                for match in re.finditer(r'def\s+(\w+)\s*\(', code):
                    atom_symbols['defines_functions'].add(match.group(1))

                # Variables: var = value
                for match in re.finditer(r'(\w+)\s*=', code):
                    var_name = match.group(1)
                    if not var_name.isupper():  # Skip constants
                        atom_symbols['defines_variables'].add(var_name)

                # Classes/Types: class TypeName
                for match in re.finditer(r'class\s+(\w+)', code):
                    atom_symbols['defines_types'].add(match.group(1))

            elif language in ["typescript", "javascript"]:
                # Functions: function name( or const name = function( or const name = (
                for match in re.finditer(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:function|\())', code):
                    func_name = match.group(1) or match.group(2)
                    if func_name:
                        atom_symbols['defines_functions'].add(func_name)

                # Variables: const/let/var name =
                for match in re.finditer(r'(?:const|let|var)\s+(\w+)\s*=', code):
                    atom_symbols['defines_variables'].add(match.group(1))

                # Types/Interfaces: interface Name or type Name
                for match in re.finditer(r'(?:interface|type|class)\s+(\w+)', code):
                    atom_symbols['defines_types'].add(match.group(1))

            # Extract usages (function calls, variable refs)
            # Function calls: name(
            for match in re.finditer(r'(\w+)\s*\(', code):
                func_name = match.group(1)
                if func_name not in atom_symbols['defines_functions']:
                    atom_symbols['uses_functions'].add(func_name)

            # Variable references (simple heuristic)
            for match in re.finditer(r'\b([a-z_]\w*)\b', code):
                var_name = match.group(1)
                if (var_name not in atom_symbols['defines_variables'] and
                    var_name not in ['if', 'else', 'for', 'while', 'return', 'def', 'class',
                                    'const', 'let', 'var', 'function', 'true', 'false', 'null',
                                    'undefined', 'None', 'True', 'False', 'self', 'this']):
                    atom_symbols['uses_variables'].add(var_name)

            symbols[atom.atom_id] = atom_symbols

        return symbols

    def _detect_dependencies(
        self,
        atoms: List[AtomicUnit],
        symbols: Dict[uuid.UUID, Dict[str, Set[str]]]
    ) -> List[Dependency]:
        """
        Detect dependencies between atoms based on symbol usage

        Algorithm:
        - If atom A uses function defined in atom B → dependency
        - If atom A uses variable defined in atom B → dependency
        - If atom A uses type defined in atom B → dependency
        - If atom A imports module that atom B provides → dependency
        """
        dependencies: List[Dependency] = []

        # Create lookup: symbol → atom_id that defines it
        function_providers: Dict[str, uuid.UUID] = {}
        variable_providers: Dict[str, uuid.UUID] = {}
        type_providers: Dict[str, uuid.UUID] = {}
        module_providers: Dict[str, uuid.UUID] = {}

        for atom in atoms:
            atom_symbols = symbols[atom.atom_id]

            for func in atom_symbols['defines_functions']:
                function_providers[func] = atom.atom_id

            for var in atom_symbols['defines_variables']:
                variable_providers[var] = atom.atom_id

            for typ in atom_symbols['defines_types']:
                type_providers[typ] = atom.atom_id

            for module in atom_symbols['imports']:
                module_providers[module] = atom.atom_id

        # Detect dependencies
        for atom in atoms:
            atom_symbols = symbols[atom.atom_id]

            # Function call dependencies
            for func in atom_symbols['uses_functions']:
                if func in function_providers:
                    provider_id = function_providers[func]
                    if provider_id != atom.atom_id:  # Not self-dependency
                        dependencies.append(Dependency(
                            source_atom_id=atom.atom_id,
                            target_atom_id=provider_id,
                            dependency_type=DependencyType.FUNCTION_CALL,
                            details=f"Calls function '{func}'",
                            weight=1.0
                        ))

            # Variable dependencies
            for var in atom_symbols['uses_variables']:
                if var in variable_providers:
                    provider_id = variable_providers[var]
                    if provider_id != atom.atom_id:
                        dependencies.append(Dependency(
                            source_atom_id=atom.atom_id,
                            target_atom_id=provider_id,
                            dependency_type=DependencyType.VARIABLE,
                            details=f"Uses variable '{var}'",
                            weight=0.8
                        ))

            # Type dependencies
            for typ in atom_symbols['uses_types']:
                if typ in type_providers:
                    provider_id = type_providers[typ]
                    if provider_id != atom.atom_id:
                        dependencies.append(Dependency(
                            source_atom_id=atom.atom_id,
                            target_atom_id=provider_id,
                            dependency_type=DependencyType.TYPE,
                            details=f"Uses type '{typ}'",
                            weight=0.9
                        ))

        logger.info(f"Detected {len(dependencies)} dependencies")
        return dependencies

    def _validate_graph(self, graph: nx.DiGraph) -> None:
        """
        Validate graph for issues

        Checks:
        - Circular dependencies (cycles)
        - Isolated nodes (no connections)
        - Strong connectivity
        """
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                logger.warning(f"Graph contains {len(cycles)} cycles")
                for cycle in cycles[:5]:  # Log first 5
                    logger.warning(f"  Cycle: {' → '.join(cycle)} → {cycle[0]}")
        except Exception as e:
            logger.error(f"Error checking cycles: {e}")

        # Check for isolated nodes
        isolated = list(nx.isolates(graph))
        if isolated:
            logger.info(f"Graph has {len(isolated)} isolated nodes (no dependencies)")

        # Check connectivity
        if graph.number_of_nodes() > 0:
            weakly_connected = nx.number_weakly_connected_components(graph)
            logger.info(f"Graph has {weakly_connected} weakly connected components")

    def get_graph_stats(self, graph: nx.DiGraph) -> Dict[str, any]:
        """Get statistics about the dependency graph"""
        if graph.number_of_nodes() == 0:
            return {
                "nodes": 0,
                "edges": 0,
                "avg_dependencies": 0,
                "max_dependencies": 0,
                "cycles": 0,
                "isolated_nodes": 0
            }

        # Calculate stats
        degrees = dict(graph.out_degree())
        cycles = list(nx.simple_cycles(graph))
        isolated = list(nx.isolates(graph))

        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "avg_dependencies": sum(degrees.values()) / len(degrees) if degrees else 0,
            "max_dependencies": max(degrees.values()) if degrees else 0,
            "cycles": len(cycles),
            "isolated_nodes": len(isolated),
            "density": nx.density(graph)
        }
