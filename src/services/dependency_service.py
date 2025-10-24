"""
Dependency Service - Dependency Graph Orchestration

Orchestrates dependency graph operations:
1. Build graph from atoms (GraphBuilder)
2. Create execution plan (TopologicalSorter)
3. Persist graph to database
4. Manage execution waves

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import logging
import networkx as nx
from networkx.readwrite import json_graph

from src.dependency import GraphBuilder, TopologicalSorter
from src.models import (
    AtomicUnit,
    DependencyGraph,
    AtomDependency,
    ExecutionWave as ExecutionWaveModel,
    MasterPlan
)

logger = logging.getLogger(__name__)


class DependencyService:
    """
    Dependency service - Graph and execution plan management

    Coordinates:
    - GraphBuilder: Dependency detection
    - TopologicalSorter: Execution planning
    - Database persistence
    """

    def __init__(self, db: Session):
        """
        Initialize dependency service

        Args:
            db: Database session
        """
        self.db = db
        self.graph_builder = GraphBuilder()
        self.sorter = TopologicalSorter()

        logger.info("DependencyService initialized")

    def build_dependency_graph(self, masterplan_id: uuid.UUID) -> Dict:
        """
        Build dependency graph for all atoms in masterplan

        Pipeline:
        1. Load all atoms for masterplan
        2. Build dependency graph (GraphBuilder)
        3. Create execution plan (TopologicalSorter)
        4. Persist graph and waves to database

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            Dict with graph statistics and execution plan
        """
        logger.info(f"Building dependency graph for masterplan: {masterplan_id}")

        # Step 1: Load atoms
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        if not atoms:
            raise ValueError(f"No atoms found for masterplan {masterplan_id}")

        logger.info(f"Loaded {len(atoms)} atoms")

        # Step 2: Build graph
        graph = self.graph_builder.build_graph(atoms)
        graph_stats = self.graph_builder.get_graph_stats(graph)

        logger.info(f"Graph built: {graph_stats}")

        # Step 3: Create execution plan
        execution_plan = self.sorter.create_execution_plan(graph, atoms)

        logger.info(f"Execution plan: {execution_plan.total_waves} waves, "
                   f"max parallelism: {execution_plan.max_parallelism}")

        # Step 4: Persist to database
        self._persist_graph(masterplan_id, graph, execution_plan)

        logger.info("Graph persisted to database")

        # Return results
        return {
            "success": True,
            "masterplan_id": str(masterplan_id),
            "total_atoms": len(atoms),
            "graph_stats": graph_stats,
            "execution_plan": {
                "total_waves": execution_plan.total_waves,
                "max_parallelism": execution_plan.max_parallelism,
                "avg_parallelism": execution_plan.avg_parallelism,
                "has_cycles": execution_plan.has_cycles,
                "cycle_warnings": execution_plan.cycle_info if execution_plan.has_cycles else []
            },
            "waves": [
                {
                    "wave_number": wave.wave_number,
                    "total_atoms": wave.total_atoms,
                    "atom_ids": [str(aid) for aid in wave.atom_ids],
                    "estimated_duration": wave.estimated_duration
                }
                for wave in execution_plan.waves
            ]
        }

    def _persist_graph(
        self,
        masterplan_id: uuid.UUID,
        graph: nx.DiGraph,
        execution_plan
    ) -> None:
        """
        Persist graph and execution plan to database

        Creates:
        - DependencyGraph record with NetworkX graph as JSONB
        - AtomDependency records for each edge
        - ExecutionWave records for each wave
        """
        # Serialize NetworkX graph to JSON
        graph_data = json_graph.node_link_data(graph)
        graph_json = json.dumps(graph_data)

        # Create or update DependencyGraph
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if dep_graph:
            # Update existing
            dep_graph.graph_data = graph_json
            dep_graph.total_atoms = graph.number_of_nodes()
            dep_graph.total_dependencies = graph.number_of_edges()
            dep_graph.has_cycles = execution_plan.has_cycles
            dep_graph.max_parallelism = execution_plan.max_parallelism
            dep_graph.updated_at = datetime.utcnow()
        else:
            # Create new
            dep_graph = DependencyGraph(
                masterplan_id=masterplan_id,
                graph_data=graph_json,
                total_atoms=graph.number_of_nodes(),
                total_edges=graph.number_of_edges(),
                total_waves=execution_plan.total_waves,
                has_cycles=execution_plan.has_cycles,
                max_parallelism=execution_plan.max_parallelism,
                created_at=datetime.utcnow()
            )
            self.db.add(dep_graph)

        self.db.flush()  # Get graph_id

        # Delete existing dependencies and waves
        self.db.query(AtomDependency).filter(
            AtomDependency.graph_id == dep_graph.graph_id
        ).delete()

        self.db.query(ExecutionWaveModel).filter(
            ExecutionWaveModel.graph_id == dep_graph.graph_id
        ).delete()

        # Create AtomDependency records
        for source, target, edge_data in graph.edges(data=True):
            dependency = AtomDependency(
                graph_id=dep_graph.graph_id,
                source_atom_id=uuid.UUID(source),
                target_atom_id=uuid.UUID(target),
                dependency_type=edge_data.get('dependency_type', 'unknown'),
                details=edge_data.get('details', ''),
                weight=edge_data.get('weight', 1.0)
            )
            self.db.add(dependency)

        # Create ExecutionWave records
        for wave in execution_plan.waves:
            # For SQL Lite compatibility, serialize arrays to JSON string
            atom_ids_value = wave.atom_ids
            if isinstance(atom_ids_value, list):
                # Check if we're using SQLite by checking the dialect
                if 'sqlite' in str(self.db.bind.dialect.name).lower():
                    atom_ids_value = json.dumps([str(aid) if not isinstance(aid, str) else aid for aid in atom_ids_value])
                else:
                    atom_ids_value = [uuid.UUID(aid) if isinstance(aid, str) else aid for aid in atom_ids_value]

            wave_model = ExecutionWaveModel(
                graph_id=dep_graph.graph_id,
                wave_number=wave.wave_number,
                atom_ids=atom_ids_value,
                total_atoms=wave.total_atoms
            )
            self.db.add(wave_model)

        self.db.commit()

    def get_dependency_graph(self, masterplan_id: uuid.UUID) -> Optional[Dict]:
        """Get dependency graph for masterplan"""
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if not dep_graph:
            return None

        # Deserialize graph
        graph_data = json.loads(dep_graph.graph_data)
        graph = json_graph.node_link_graph(graph_data, directed=True)

        # Get waves
        waves = self.db.query(ExecutionWaveModel).filter(
            ExecutionWaveModel.graph_id == dep_graph.graph_id
        ).order_by(ExecutionWaveModel.wave_number).all()

        return {
            "graph_id": str(dep_graph.graph_id),
            "masterplan_id": str(dep_graph.masterplan_id),
            "total_atoms": dep_graph.total_atoms,
            "total_dependencies": dep_graph.total_dependencies,
            "has_cycles": dep_graph.has_cycles,
            "max_parallelism": dep_graph.max_parallelism,
            "waves": [
                {
                    "wave_number": wave.wave_number,
                    "total_atoms": wave.total_atoms,
                    "atom_ids": wave.atom_ids,
                    "estimated_duration": wave.estimated_duration
                }
                for wave in waves
            ],
            "graph_data": graph_data
        }

    def get_execution_waves(self, masterplan_id: uuid.UUID) -> List[Dict]:
        """Get execution waves for masterplan"""
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if not dep_graph:
            return []

        waves = self.db.query(ExecutionWaveModel).filter(
            ExecutionWaveModel.graph_id == dep_graph.graph_id
        ).order_by(ExecutionWaveModel.wave_number).all()

        return [
            {
                "wave_id": str(wave.wave_id),
                "wave_number": wave.wave_number,
                "total_atoms": wave.total_atoms,
                "atom_ids": wave.atom_ids,
                "estimated_duration": wave.estimated_duration,
                "status": wave.status,
                "started_at": wave.started_at.isoformat() if wave.started_at else None,
                "completed_at": wave.completed_at.isoformat() if wave.completed_at else None
            }
            for wave in waves
        ]

    def get_atom_dependencies(self, atom_id: uuid.UUID) -> Dict:
        """Get dependencies for a specific atom"""
        # Find dependencies where this atom is the source
        dependencies = self.db.query(AtomDependency).filter(
            AtomDependency.source_atom_id == atom_id
        ).all()

        # Find dependencies where this atom is the target
        dependents = self.db.query(AtomDependency).filter(
            AtomDependency.target_atom_id == atom_id
        ).all()

        return {
            "atom_id": str(atom_id),
            "depends_on": [
                {
                    "target_atom_id": str(dep.target_atom_id),
                    "dependency_type": dep.dependency_type,
                    "details": dep.details,
                    "weight": dep.weight
                }
                for dep in dependencies
            ],
            "required_by": [
                {
                    "source_atom_id": str(dep.source_atom_id),
                    "dependency_type": dep.dependency_type,
                    "details": dep.details,
                    "weight": dep.weight
                }
                for dep in dependents
            ],
            "total_dependencies": len(dependencies),
            "total_dependents": len(dependents)
        }
