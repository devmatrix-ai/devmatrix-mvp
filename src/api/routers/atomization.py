"""
Atomization API Endpoints - MGE V2

FastAPI router for atomization operations.

Endpoints:
- POST /api/v2/atomization/decompose - Decompose task into atoms
- GET /api/v2/atoms/{atom_id} - Get atom by ID
- GET /api/v2/atoms/by-task/{task_id} - Get all atoms for task
- PUT /api/v2/atoms/{atom_id} - Update atom
- DELETE /api/v2/atoms/{atom_id} - Delete atom

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.services.atom_service import AtomService
from src.models import AtomicUnit

# Create router
router = APIRouter(
    prefix="/api/v2",
    tags=["atomization"],
)


# Request/Response Models
class DecomposeRequest(BaseModel):
    """Request to decompose task"""
    task_id: str = Field(..., description="Task UUID to decompose")


class DecomposeResponse(BaseModel):
    """Response with decomposed atoms"""
    success: bool
    task_id: str
    total_atoms: int
    atoms: List[Dict]
    stats: Dict
    errors: List[str] = []


class AtomResponse(BaseModel):
    """Single atom response"""
    atom_id: str
    atom_number: int
    name: str
    description: str
    language: str
    loc: int
    complexity: float
    atomicity_score: float
    context_completeness: float
    is_atomic: bool
    needs_review: bool
    status: str


class AtomListResponse(BaseModel):
    """List of atoms response"""
    atoms: List[AtomResponse]
    total: int


class AtomUpdateRequest(BaseModel):
    """Request to update atom"""
    name: str | None = None
    description: str | None = None
    code_to_generate: str | None = None
    status: str | None = None


# Endpoints
@router.post("/atomization/decompose", response_model=DecomposeResponse)
def decompose_task(
    request: DecomposeRequest,
    db: Session = Depends(get_db)
):
    """
    Decompose a task into atomic units

    Pipeline:
    1. Load task from database
    2. Parse task code (MultiLanguageParser)
    3. Decompose into atoms (RecursiveDecomposer)
    4. Inject context (ContextInjector)
    5. Validate atomicity (AtomicityValidator)
    6. Persist atoms to database

    Returns:
        DecomposeResponse with atoms and statistics
    """
    try:
        # Convert string UUID to UUID
        task_id = uuid.UUID(request.task_id)

        # Create service
        service = AtomService(db)

        # Decompose task
        result = service.decompose_task(task_id)

        return DecomposeResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decomposition failed: {str(e)}"
        )


@router.get("/atoms/{atom_id}", response_model=AtomResponse)
def get_atom(
    atom_id: str,
    db: Session = Depends(get_db)
):
    """
    Get atom by ID

    Args:
        atom_id: Atom UUID

    Returns:
        AtomResponse with atom details
    """
    try:
        # Convert string UUID to UUID
        atom_uuid = uuid.UUID(atom_id)

        # Create service
        service = AtomService(db)

        # Get atom
        atom = service.get_atom(atom_uuid)

        if not atom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Atom {atom_id} not found"
            )

        return AtomResponse(
            atom_id=str(atom.atom_id),
            atom_number=atom.atom_number,
            name=atom.name,
            description=atom.description,
            language=atom.language,
            loc=atom.loc,
            complexity=atom.complexity,
            atomicity_score=atom.atomicity_score,
            context_completeness=atom.context_completeness,
            is_atomic=atom.is_atomic,
            needs_review=atom.needs_review,
            status=atom.status.value
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get atom: {str(e)}"
        )


@router.get("/atoms/by-task/{task_id}", response_model=AtomListResponse)
def get_atoms_by_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all atoms for a task

    Args:
        task_id: Task UUID

    Returns:
        AtomListResponse with list of atoms
    """
    try:
        # Convert string UUID to UUID
        task_uuid = uuid.UUID(task_id)

        # Create service
        service = AtomService(db)

        # Get atoms
        atoms = service.get_atoms_by_task(task_uuid)

        return AtomListResponse(
            atoms=[
                AtomResponse(
                    atom_id=str(atom.atom_id),
                    atom_number=atom.atom_number,
                    name=atom.name,
                    description=atom.description,
                    language=atom.language,
                    loc=atom.loc,
                    complexity=atom.complexity,
                    atomicity_score=atom.atomicity_score,
                    context_completeness=atom.context_completeness,
                    is_atomic=atom.is_atomic,
                    needs_review=atom.needs_review,
                    status=atom.status.value
                )
                for atom in atoms
            ],
            total=len(atoms)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get atoms: {str(e)}"
        )


@router.put("/atoms/{atom_id}", response_model=AtomResponse)
def update_atom(
    atom_id: str,
    request: AtomUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update atom

    Args:
        atom_id: Atom UUID
        request: Update data

    Returns:
        AtomResponse with updated atom
    """
    try:
        # Convert string UUID to UUID
        atom_uuid = uuid.UUID(atom_id)

        # Create service
        service = AtomService(db)

        # Get update data (only non-None fields)
        update_data = {k: v for k, v in request.dict().items() if v is not None}

        # Update atom
        atom = service.update_atom(atom_uuid, update_data)

        if not atom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Atom {atom_id} not found"
            )

        return AtomResponse(
            atom_id=str(atom.atom_id),
            atom_number=atom.atom_number,
            name=atom.name,
            description=atom.description,
            language=atom.language,
            loc=atom.loc,
            complexity=atom.complexity,
            atomicity_score=atom.atomicity_score,
            context_completeness=atom.context_completeness,
            is_atomic=atom.is_atomic,
            needs_review=atom.needs_review,
            status=atom.status.value
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update atom: {str(e)}"
        )


@router.delete("/atoms/{atom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_atom(
    atom_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete atom

    Args:
        atom_id: Atom UUID

    Returns:
        204 No Content on success
    """
    try:
        # Convert string UUID to UUID
        atom_uuid = uuid.UUID(atom_id)

        # Create service
        service = AtomService(db)

        # Delete atom
        success = service.delete_atom(atom_uuid)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Atom {atom_id} not found"
            )

        return None

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete atom: {str(e)}"
        )


@router.get("/atoms/by-task/{task_id}/stats")
def get_decomposition_stats(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get decomposition statistics for a task

    Args:
        task_id: Task UUID

    Returns:
        Dict with statistics
    """
    try:
        # Convert string UUID to UUID
        task_uuid = uuid.UUID(task_id)

        # Create service
        service = AtomService(db)

        # Get stats
        stats = service.get_decomposition_stats(task_uuid)

        return stats

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
