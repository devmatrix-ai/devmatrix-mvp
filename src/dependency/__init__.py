"""
Dependency Graph Module - MGE V2

Builds and manages dependency graphs for atomic execution.

Components:
- GraphBuilder: Constructs dependency graphs from atoms
- TopologicalSorter: Orders atoms for execution and creates waves

Author: DevMatrix Team
Date: 2025-10-23
"""

from .graph_builder import GraphBuilder, DependencyType
from .topological_sorter import TopologicalSorter, ExecutionWave

__all__ = [
    'GraphBuilder',
    'DependencyType',
    'TopologicalSorter',
    'ExecutionWave',
]
