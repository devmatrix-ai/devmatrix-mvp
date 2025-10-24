"""
Topological Sorter - Execution Order and Wave Generation

Performs topological sort on dependency graph to determine execution order.
Groups atoms into waves for parallel execution.

Wave Properties:
- Wave 0: Atoms with no dependencies (can execute immediately)
- Wave N: Atoms whose dependencies are in waves 0..N-1
- Atoms in same wave can execute in parallel

Cycle Handling:
- Detects circular dependencies
- Breaks cycles by identifying minimum feedback arc set
- Logs cycle warnings for manual review

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
import logging
import networkx as nx

from src.models import AtomicUnit

logger = logging.getLogger(__name__)


@dataclass
class ExecutionWave:
    """Group of atoms that can execute in parallel"""
    wave_number: int
    atom_ids: List[uuid.UUID]
    total_atoms: int
    estimated_duration: float = 0.0  # Seconds (based on complexity)
    dependencies_satisfied: bool = True


@dataclass
class ExecutionPlan:
    """Complete execution plan with waves"""
    waves: List[ExecutionWave]
    total_waves: int
    total_atoms: int
    max_parallelism: int  # Max atoms in any wave
    avg_parallelism: float
    has_cycles: bool
    cycle_info: List[str] = field(default_factory=list)


class TopologicalSorter:
    """
    Topological sorter for execution planning

    Converts dependency graph into execution waves:
    1. Topological sort (handle cycles)
    2. Level-based grouping (wave generation)
    3. Optimization (balance waves)
    """

    def __init__(self) -> None:
        """Initialize topological sorter"""
        logger.info("TopologicalSorter initialized")

    def create_execution_plan(
        self,
        graph: nx.DiGraph,
        atoms: List[AtomicUnit]
    ) -> ExecutionPlan:
        """
        Create execution plan with waves

        Args:
            graph: Dependency graph (from GraphBuilder)
            atoms: List of atomic units

        Returns:
            ExecutionPlan with waves for parallel execution
        """
        logger.info(f"Creating execution plan for {len(atoms)} atoms")

        # Handle cycles if present
        has_cycles = False
        cycle_info: List[str] = []

        if not nx.is_directed_acyclic_graph(graph):
            logger.warning("Graph contains cycles, attempting to break them")
            has_cycles = True
            cycle_info = self._handle_cycles(graph)

        # Perform topological sort
        try:
            sorted_nodes = list(nx.topological_sort(graph))
            logger.info(f"Topological sort successful: {len(sorted_nodes)} nodes ordered")
        except nx.NetworkXError as e:
            logger.error(f"Topological sort failed: {e}")
            # Fallback: use node list as-is
            sorted_nodes = list(graph.nodes())

        # Create atom lookup
        atom_lookup = {str(atom.atom_id): atom for atom in atoms}

        # Generate waves (level-based grouping)
        waves = self._generate_waves(graph, sorted_nodes, atom_lookup)

        # Calculate statistics
        total_atoms = sum(wave.total_atoms for wave in waves)
        max_parallelism = max((wave.total_atoms for wave in waves), default=0)
        avg_parallelism = total_atoms / len(waves) if waves else 0

        plan = ExecutionPlan(
            waves=waves,
            total_waves=len(waves),
            total_atoms=total_atoms,
            max_parallelism=max_parallelism,
            avg_parallelism=avg_parallelism,
            has_cycles=has_cycles,
            cycle_info=cycle_info
        )

        logger.info(f"Execution plan created: {plan.total_waves} waves, "
                   f"max parallelism: {plan.max_parallelism}, "
                   f"avg parallelism: {plan.avg_parallelism:.1f}")

        return plan

    def _generate_waves(
        self,
        graph: nx.DiGraph,
        sorted_nodes: List[str],
        atom_lookup: Dict[str, AtomicUnit]
    ) -> List[ExecutionWave]:
        """
        Generate execution waves using level-based grouping

        Algorithm:
        - Wave 0: Nodes with in_degree = 0 (no dependencies)
        - Wave N: Nodes whose predecessors are all in waves < N
        """
        waves: List[ExecutionWave] = []
        node_to_wave: Dict[str, int] = {}
        processed: Set[str] = set()

        wave_number = 0

        while len(processed) < len(sorted_nodes):
            # Find nodes ready for this wave
            current_wave_nodes: List[str] = []

            for node in sorted_nodes:
                if node in processed:
                    continue

                # Check if all dependencies are satisfied
                predecessors = list(graph.predecessors(node))
                if all(pred in processed for pred in predecessors):
                    current_wave_nodes.append(node)
                    node_to_wave[node] = wave_number

            if not current_wave_nodes:
                # No nodes ready - shouldn't happen with DAG
                logger.warning(f"No nodes ready for wave {wave_number}, remaining: {len(sorted_nodes) - len(processed)}")
                # Add remaining nodes to force progress
                for node in sorted_nodes:
                    if node not in processed:
                        current_wave_nodes.append(node)
                        node_to_wave[node] = wave_number

            # Create wave
            atom_ids = [uuid.UUID(node) for node in current_wave_nodes]

            # Estimate duration (sum of complexities)
            estimated_duration = sum(
                atom_lookup[node].complexity * 10  # 10 seconds per complexity point
                for node in current_wave_nodes
                if node in atom_lookup
            )

            wave = ExecutionWave(
                wave_number=wave_number,
                atom_ids=atom_ids,
                total_atoms=len(atom_ids),
                estimated_duration=estimated_duration,
                dependencies_satisfied=True
            )

            waves.append(wave)
            processed.update(current_wave_nodes)

            logger.debug(f"Wave {wave_number}: {len(current_wave_nodes)} atoms, "
                        f"estimated {estimated_duration:.0f}s")

            wave_number += 1

        return waves

    def _handle_cycles(self, graph: nx.DiGraph) -> List[str]:
        """
        Handle circular dependencies

        Strategy:
        1. Find all simple cycles
        2. Identify minimum feedback arc set (edges to remove)
        3. Remove edges to break cycles
        4. Log warnings for manual review

        Returns:
            List of cycle descriptions for logging
        """
        cycle_info: List[str] = []

        try:
            cycles = list(nx.simple_cycles(graph))
            logger.warning(f"Found {len(cycles)} cycles in dependency graph")

            # Log first 10 cycles
            for i, cycle in enumerate(cycles[:10]):
                cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
                cycle_info.append(f"Cycle {i+1}: {cycle_str}")
                logger.warning(f"  {cycle_info[-1]}")

            if len(cycles) > 10:
                logger.warning(f"  ... and {len(cycles) - 10} more cycles")

            # Find minimum feedback arc set (edges to remove)
            # This is an NP-hard problem, use approximation
            feedback_edges = self._find_feedback_arc_set(graph, cycles)

            # Remove edges
            for source, target in feedback_edges:
                logger.warning(f"Breaking cycle: removing edge {source} → {target}")
                graph.remove_edge(source, target)
                cycle_info.append(f"Removed dependency: {source} → {target}")

            logger.info(f"Removed {len(feedback_edges)} edges to break cycles")

        except Exception as e:
            logger.error(f"Error handling cycles: {e}")
            cycle_info.append(f"Error: {str(e)}")

        return cycle_info

    def _find_feedback_arc_set(
        self,
        graph: nx.DiGraph,
        cycles: List[List[str]]
    ) -> List[Tuple[str, str]]:
        """
        Find minimum feedback arc set (edges to remove to break cycles)

        Simple heuristic: Remove edge with highest betweenness centrality
        in cycle subgraph
        """
        if not cycles:
            return []

        # Collect all edges involved in cycles
        cycle_edges: Set[Tuple[str, str]] = set()
        for cycle in cycles:
            for i in range(len(cycle)):
                source = cycle[i]
                target = cycle[(i + 1) % len(cycle)]
                if graph.has_edge(source, target):
                    cycle_edges.add((source, target))

        # Count how many cycles each edge participates in
        edge_cycle_count: Dict[Tuple[str, str], int] = {}
        for edge in cycle_edges:
            edge_cycle_count[edge] = 0
            for cycle in cycles:
                for i in range(len(cycle)):
                    if (cycle[i], cycle[(i + 1) % len(cycle)]) == edge:
                        edge_cycle_count[edge] += 1

        # Select edges that break most cycles
        feedback_edges: List[Tuple[str, str]] = []
        remaining_cycles = set(range(len(cycles)))

        while remaining_cycles:
            # Find edge that breaks most remaining cycles
            best_edge = None
            best_count = 0

            for edge, count in edge_cycle_count.items():
                if edge not in feedback_edges:
                    cycles_broken = sum(
                        1 for cycle_idx in remaining_cycles
                        if any(
                            (cycles[cycle_idx][i], cycles[cycle_idx][(i+1) % len(cycles[cycle_idx])]) == edge
                            for i in range(len(cycles[cycle_idx]))
                        )
                    )
                    if cycles_broken > best_count:
                        best_count = cycles_broken
                        best_edge = edge

            if not best_edge:
                break

            feedback_edges.append(best_edge)

            # Update remaining cycles
            broken_cycles = set()
            for cycle_idx in remaining_cycles:
                cycle = cycles[cycle_idx]
                if any(
                    (cycle[i], cycle[(i+1) % len(cycle)]) == best_edge
                    for i in range(len(cycle))
                ):
                    broken_cycles.add(cycle_idx)

            remaining_cycles -= broken_cycles

        return feedback_edges

    def optimize_waves(
        self,
        waves: List[ExecutionWave],
        max_wave_size: int = 100
    ) -> List[ExecutionWave]:
        """
        Optimize wave distribution

        Strategies:
        - Split large waves (>max_wave_size)
        - Balance wave sizes
        - Minimize total execution time

        Args:
            waves: Original waves
            max_wave_size: Maximum atoms per wave

        Returns:
            Optimized waves
        """
        optimized_waves: List[ExecutionWave] = []

        for wave in waves:
            if wave.total_atoms <= max_wave_size:
                # Wave is fine as-is
                optimized_waves.append(wave)
            else:
                # Split large wave
                logger.info(f"Splitting wave {wave.wave_number} ({wave.total_atoms} atoms) into sub-waves")

                chunks = [
                    wave.atom_ids[i:i + max_wave_size]
                    for i in range(0, len(wave.atom_ids), max_wave_size)
                ]

                for i, chunk in enumerate(chunks):
                    sub_wave = ExecutionWave(
                        wave_number=wave.wave_number + (i / 10),  # 0.1, 0.2, etc.
                        atom_ids=chunk,
                        total_atoms=len(chunk),
                        estimated_duration=wave.estimated_duration / len(chunks),
                        dependencies_satisfied=wave.dependencies_satisfied
                    )
                    optimized_waves.append(sub_wave)

        return optimized_waves
