"""
Atom Service - MGE V2 Atomization Orchestration

Orchestrates the complete atomization pipeline:
1. Parse task code (MultiLanguageParser)
2. Decompose into atoms (RecursiveDecomposer)
3. Inject context (ContextInjector)
4. Validate atomicity (AtomicityValidator)
5. Persist to database

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import logging

from src.atomization import (
    MultiLanguageParser,
    RecursiveDecomposer,
    ContextInjector,
    AtomicityValidator
)
from src.models import (
    AtomicUnit,
    MasterPlanTask,
    MasterPlan,
    AtomStatus
)

logger = logging.getLogger(__name__)


class AtomService:
    """
    Atom Service - Atomization orchestration

    Coordinates:
    - MultiLanguageParser: AST extraction
    - RecursiveDecomposer: Task → Atoms
    - ContextInjector: Context extraction
    - AtomicityValidator: Quality validation
    - Database persistence
    """

    def __init__(self, db: Session):
        """
        Initialize atom service

        Args:
            db: Database session
        """
        self.db = db
        self.parser = MultiLanguageParser()
        self.decomposer = RecursiveDecomposer(target_loc=10, max_loc=15, max_complexity=3.0)
        self.context_injector = ContextInjector()
        self.validator = AtomicityValidator(max_loc=15, max_complexity=3.0, min_score_threshold=0.8)

        logger.info("AtomService initialized")

    def decompose_task(self, task_id: uuid.UUID) -> Dict:
        """
        Decompose a task into atomic units

        Pipeline:
        1. Load task from database
        2. Parse task code
        3. Decompose into atoms
        4. Inject context for each atom
        5. Validate atomicity
        6. Persist atoms to database

        Args:
            task_id: Task UUID

        Returns:
            Dict with decomposition results
        """
        logger.info(f"Starting task decomposition: {task_id}")

        # Step 1: Load task
        task = self.db.query(MasterPlanTask).filter(MasterPlanTask.task_id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Get task details
        task_code = self._get_task_code(task)
        language = self._detect_language(task)
        description = task.description

        logger.info(f"Task: {task.name}, Language: {language}, Code length: {len(task_code)}")

        # Step 2 & 3: Parse and decompose
        decomposition_result = self.decomposer.decompose(task_code, language, description)

        if not decomposition_result.success:
            logger.error(f"Decomposition failed: {decomposition_result.errors}")
            return {
                "success": False,
                "errors": decomposition_result.errors,
                "atoms": []
            }

        logger.info(f"Decomposed into {decomposition_result.total_atoms} atoms")

        # Step 4 & 5 & 6: Context injection, validation, persistence
        atoms = []
        atom_number_base = self._get_next_atom_number(task.milestone.phase.masterplan_id)

        for i, atom_candidate in enumerate(decomposition_result.atoms):
            # Inject context
            context = self.context_injector.inject_context(
                atom_candidate,
                task_code,
                language,
                decomposition_result.atoms
            )

            # Validate atomicity
            validation_result = self.validator.validate(atom_candidate, context, decomposition_result.atoms)

            # Create atomic unit
            atom = AtomicUnit(
                masterplan_id=task.milestone.phase.masterplan_id,
                task_id=task.task_id,
                atom_number=atom_number_base + i + 1,
                name=atom_candidate.description,
                description=atom_candidate.description,

                # Code
                code_to_generate=atom_candidate.code,
                file_path=task.target_files[0] if task.target_files else None,
                line_start=atom_candidate.start_line,
                line_end=atom_candidate.end_line,
                language=language,
                loc=atom_candidate.loc,
                complexity=atom_candidate.complexity,

                # Context
                imports=context.imports,
                type_schema=context.type_schema,
                preconditions=context.preconditions,
                postconditions=context.postconditions,
                test_cases=context.test_cases,
                context_completeness=context.completeness_score,

                # Atomicity
                atomicity_score=validation_result.score,
                atomicity_violations=[{
                    'criterion': v.criterion_name,
                    'severity': v.severity,
                    'description': v.description,
                    'suggestion': v.suggestion
                } for v in validation_result.violations],
                is_atomic=validation_result.is_atomic,

                # Status
                status=AtomStatus.PENDING,
                attempts=0,
                max_attempts=3,

                # Confidence (initial estimate based on atomicity)
                confidence_score=validation_result.score,
                needs_review=(validation_result.score < 0.85),

                # Timestamps
                created_at=datetime.utcnow(),
            )

            self.db.add(atom)
            atoms.append(atom)

            logger.debug(f"Created atom {atom.atom_number}: {atom.name} (atomicity: {validation_result.score:.2%})")

        # Commit all atoms
        self.db.commit()

        logger.info(f"Persisted {len(atoms)} atoms to database")

        # Return results
        return {
            "success": True,
            "task_id": str(task_id),
            "total_atoms": len(atoms),
            "atoms": [self._atom_to_dict(a) for a in atoms],
            "stats": {
                "avg_loc": decomposition_result.avg_loc,
                "avg_complexity": decomposition_result.avg_complexity,
                "avg_atomicity_score": sum(a.atomicity_score for a in atoms) / len(atoms) if atoms else 0,
                "avg_context_completeness": sum(a.context_completeness for a in atoms) / len(atoms) if atoms else 0,
                "needs_review_count": sum(1 for a in atoms if a.needs_review),
            }
        }

    def get_atom(self, atom_id: uuid.UUID) -> Optional[AtomicUnit]:
        """Get atom by ID"""
        return self.db.query(AtomicUnit).filter(AtomicUnit.atom_id == atom_id).first()

    def get_atoms_by_task(self, task_id: uuid.UUID) -> List[AtomicUnit]:
        """Get all atoms for a task"""
        return self.db.query(AtomicUnit).filter(AtomicUnit.task_id == task_id).all()

    def get_atoms_by_masterplan(self, masterplan_id: uuid.UUID) -> List[AtomicUnit]:
        """Get all atoms for a masterplan"""
        return self.db.query(AtomicUnit).filter(AtomicUnit.masterplan_id == masterplan_id).all()

    def update_atom(self, atom_id: uuid.UUID, data: Dict) -> Optional[AtomicUnit]:
        """Update atom"""
        atom = self.get_atom(atom_id)
        if not atom:
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(atom, key):
                setattr(atom, key, value)

        atom.updated_at = datetime.utcnow()
        self.db.commit()
        return atom

    def delete_atom(self, atom_id: uuid.UUID) -> bool:
        """Delete atom"""
        atom = self.get_atom(atom_id)
        if not atom:
            return False

        self.db.delete(atom)
        self.db.commit()
        return True

    def get_decomposition_stats(self, task_id: uuid.UUID) -> Dict:
        """Get decomposition statistics for a task"""
        atoms = self.get_atoms_by_task(task_id)

        if not atoms:
            return {
                "total_atoms": 0,
                "avg_loc": 0,
                "avg_complexity": 0,
                "avg_atomicity_score": 0,
                "avg_context_completeness": 0,
                "needs_review_count": 0,
            }

        return {
            "total_atoms": len(atoms),
            "avg_loc": sum(a.loc for a in atoms) / len(atoms),
            "avg_complexity": sum(a.complexity for a in atoms) / len(atoms),
            "avg_atomicity_score": sum(a.atomicity_score for a in atoms) / len(atoms),
            "avg_context_completeness": sum(a.context_completeness for a in atoms) / len(atoms),
            "needs_review_count": sum(1 for a in atoms if a.needs_review),
        }

    def _get_task_code(self, task: MasterPlanTask) -> str:
        """Get code to decompose from task"""
        # For now, use description as placeholder
        # In production, would load actual code from files or LLM response
        return task.description

    def _detect_language(self, task: MasterPlanTask) -> str:
        """Detect programming language from task"""
        if task.target_files:
            file_path = task.target_files[0]
            return self.parser.detect_language(file_path)
        return "python"  # Default

    def _get_next_atom_number(self, masterplan_id: uuid.UUID) -> int:
        """Get next atom number for masterplan"""
        last_atom = (
            self.db.query(AtomicUnit)
            .filter(AtomicUnit.masterplan_id == masterplan_id)
            .order_by(AtomicUnit.atom_number.desc())
            .first()
        )

        return last_atom.atom_number if last_atom else 0

    def _atom_to_dict(self, atom: AtomicUnit) -> Dict:
        """Convert atom to dictionary"""
        return {
            "atom_id": str(atom.atom_id),
            "atom_number": atom.atom_number,
            "name": atom.name,
            "description": atom.description,
            "language": atom.language,
            "loc": atom.loc,
            "complexity": atom.complexity,
            "atomicity_score": atom.atomicity_score,
            "context_completeness": atom.context_completeness,
            "is_atomic": atom.is_atomic,
            "needs_review": atom.needs_review,
            "status": atom.status.value,
        }
