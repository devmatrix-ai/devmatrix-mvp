"""
Dependency API Endpoints - MGE V2

FastAPI router for dependency graph operations.

Endpoints:
- POST /api/v2/dependency/build - Build dependency graph
- GET /api/v2/dependency/graph/{masterplan_id} - Get graph
- GET /api/v2/dependency/waves/{masterplan_id} - Get execution waves
- GET /api/v2/dependency/atom/{atom_id} - Get atom dependencies

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.services.dependency_service import DependencyService

# Create router
router = APIRouter(
    prefix="/api/v2",
    tags=["dependency"],
)


# Request/Response Models
class BuildGraphRequest(BaseModel):
    """Request to build dependency graph"""
    masterplan_id: str = Field(..., description="MasterPlan UUID")


class BuildGraphResponse(BaseModel):
    """Response with graph statistics"""
    success: bool
    masterplan_id: str
    total_atoms: int
    graph_stats: Dict
    execution_plan: Dict
    waves: List[Dict]


class GraphResponse(BaseModel):
    """Dependency graph response"""
    graph_id: str
    masterplan_id: str
    total_atoms: int
    total_dependencies: int
    has_cycles: bool
    max_parallelism: int
    waves: List[Dict]


class WaveResponse(BaseModel):
    """Execution wave response"""
    wave_id: str
    wave_number: int
    total_atoms: int
    atom_ids: List[str]
    estimated_duration: float
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]


class AtomDependenciesResponse(BaseModel):
    """Atom dependencies response"""
    atom_id: str
    depends_on: List[Dict]
    required_by: List[Dict]
    total_dependencies: int
    total_dependents: int


# Endpoints
@router.post("/dependency/build", response_model=BuildGraphResponse)
def build_dependency_graph(
    request: BuildGraphRequest,
    db: Session = Depends(get_db)
):
    """
    Build dependency graph for masterplan

    Pipeline:
    1. Load all atoms for masterplan
    2. Analyze dependencies (imports, function calls, variables)
    3. Build NetworkX directed graph
    4. Create execution waves (topological sort)
    5. Persist to database

    Returns:
        BuildGraphResponse with graph statistics and execution plan
    """
    try:
        # Convert string UUID to UUID
        masterplan_id = uuid.UUID(request.masterplan_id)

        # Create service
        service = DependencyService(db)

        # Build graph
        result = service.build_dependency_graph(masterplan_id)

        return BuildGraphResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MasterPlan not found or no atoms: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph build failed: {str(e)}"
        )


@router.get("/dependency/graph/{masterplan_id}", response_model=GraphResponse)
def get_dependency_graph(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Get dependency graph for masterplan

    Args:
        masterplan_id: MasterPlan UUID

    Returns:
        GraphResponse with graph data and waves
    """
    try:
        # Convert string UUID to UUID
        masterplan_uuid = uuid.UUID(masterplan_id)

        # Create service
        service = DependencyService(db)

        # Get graph
        result = service.get_dependency_graph(masterplan_uuid)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dependency graph not found for masterplan {masterplan_id}"
            )

        return GraphResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph: {str(e)}"
        )


@router.get("/dependency/waves/{masterplan_id}", response_model=List[WaveResponse])
def get_execution_waves(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Get execution waves for masterplan

    Execution waves group atoms that can run in parallel.
    Wave 0 has no dependencies, Wave N depends on waves 0..N-1.

    Args:
        masterplan_id: MasterPlan UUID

    Returns:
        List of WaveResponse with wave details
    """
    try:
        # Convert string UUID to UUID
        masterplan_uuid = uuid.UUID(masterplan_id)

        # Create service
        service = DependencyService(db)

        # Get waves
        waves = service.get_execution_waves(masterplan_uuid)

        return [WaveResponse(**wave) for wave in waves]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get waves: {str(e)}"
        )


@router.get("/dependency/atom/{atom_id}", response_model=AtomDependenciesResponse)
def get_atom_dependencies(
    atom_id: str,
    db: Session = Depends(get_db)
):
    """
    Get dependencies for specific atom

    Shows:
    - depends_on: Atoms this atom depends on
    - required_by: Atoms that depend on this atom

    Args:
        atom_id: Atom UUID

    Returns:
        AtomDependenciesResponse with dependency details
    """
    try:
        # Convert string UUID to UUID
        atom_uuid = uuid.UUID(atom_id)

        # Create service
        service = DependencyService(db)

        # Get dependencies
        result = service.get_atom_dependencies(atom_uuid)

        return AtomDependenciesResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get atom dependencies: {str(e)}"
        )
