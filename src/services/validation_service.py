"""
Validation Service - Hierarchical Validation Orchestration

Orchestrates 4-level validation:
1. Atomic: Individual atoms
2. Task: Task coherence
3. Milestone: Milestone integration
4. MasterPlan: System-wide validation

Author: DevMatrix Team
Date: 2025-10-23
Updated: 2025-10-23 (Schema alignment)
"""

import uuid
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import logging

from src.validation.atomic_validator import AtomicValidator, AtomicValidationResult
from src.validation.task_validator import TaskValidator, TaskValidationResult
from src.validation.milestone_validator import MilestoneValidator, MilestoneValidationResult
from src.validation.masterplan_validator import MasterPlanValidator, MasterPlanValidationResult
from src.models import AtomicUnit, MasterPlanTask, MasterPlanMilestone, MasterPlanPhase, MasterPlan

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Validation service - Orchestrates hierarchical validation

    Provides:
    - Individual validation at each level
    - Full hierarchical validation (all levels)
    - Batch validation
    - Validation reports
    """

    def __init__(self, db: Session):
        """
        Initialize validation service

        Args:
            db: Database session
        """
        self.db = db
        self.atomic_validator = AtomicValidator(db)
        self.task_validator = TaskValidator(db)
        self.milestone_validator = MilestoneValidator(db)
        self.masterplan_validator = MasterPlanValidator(db)

        logger.info("ValidationService initialized")

    def validate_atom(self, atom_id: uuid.UUID) -> Dict[str, Any]:
        """
        Validate individual atom (Level 1)

        Args:
            atom_id: Atom UUID

        Returns:
            Validation result as dict
        """
        logger.info(f"Validating atom: {atom_id}")
        result = self.atomic_validator.validate_atom(atom_id)
        return self._format_atomic_result(result)

    def validate_task(self, task_id: uuid.UUID) -> Dict[str, Any]:
        """
        Validate task (Level 2)

        Args:
            task_id: MasterPlanTask UUID

        Returns:
            Validation result as dict
        """
        logger.info(f"Validating task: {task_id}")
        result = self.task_validator.validate_task(task_id)
        return self._format_task_result(result)

    def validate_milestone(self, milestone_id: uuid.UUID) -> Dict[str, Any]:
        """
        Validate milestone (Level 3)

        Args:
            milestone_id: MasterPlanMilestone UUID

        Returns:
            Validation result as dict
        """
        logger.info(f"Validating milestone: {milestone_id}")
        result = self.milestone_validator.validate_milestone(milestone_id)
        return self._format_milestone_result(result)

    def validate_masterplan(self, masterplan_id: uuid.UUID) -> Dict[str, Any]:
        """
        Validate entire masterplan (Level 4)

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            Validation result as dict
        """
        logger.info(f"Validating masterplan: {masterplan_id}")
        result = self.masterplan_validator.validate_system(masterplan_id)
        return self._format_masterplan_result(result)

    def validate_hierarchical(
        self,
        masterplan_id: uuid.UUID,
        levels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate all levels hierarchically

        Args:
            masterplan_id: MasterPlan UUID
            levels: Specific levels to validate (default: all)
                   Options: ['atomic', 'task', 'milestone', 'masterplan']

        Returns:
            Combined validation results
        """
        logger.info(f"Starting hierarchical validation for: {masterplan_id}")

        if levels is None:
            levels = ['atomic', 'task', 'milestone', 'masterplan']

        results = {
            'masterplan_id': str(masterplan_id),
            'levels_validated': levels,
            'overall_valid': True,
            'overall_score': 0.0,
            'results': {}
        }

        # Level 1: Atomic
        if 'atomic' in levels:
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.masterplan_id == masterplan_id
            ).all()

            atomic_results = []
            atomic_scores = []

            for atom in atoms:
                result = self.atomic_validator.validate_atom(atom.atom_id)
                atomic_results.append(self._format_atomic_result(result))
                atomic_scores.append(result.validation_score)

            results['results']['atomic'] = {
                'total_atoms': len(atoms),
                'valid_atoms': sum(1 for r in atomic_results if r['is_valid']),
                'avg_score': sum(atomic_scores) / len(atomic_scores) if atomic_scores else 0.0,
                'atoms': atomic_results
            }

            if results['results']['atomic']['valid_atoms'] < len(atoms):
                results['overall_valid'] = False

        # Level 2: Task
        if 'task' in levels:
            tasks = self.db.query(MasterPlanTask).join(MasterPlanMilestone).join(MasterPlanPhase).filter(
                MasterPlanPhase.masterplan_id == masterplan_id
            ).all()

            task_results = []
            task_scores = []

            for task in tasks:
                result = self.task_validator.validate_task(task.task_id)
                task_results.append(self._format_task_result(result))
                task_scores.append(result.validation_score)

            results['results']['task'] = {
                'total_tasks': len(tasks),
                'valid_tasks': sum(1 for r in task_results if r['is_valid']),
                'avg_score': sum(task_scores) / len(task_scores) if task_scores else 0.0,
                'tasks': task_results
            }

            if results['results']['task']['valid_tasks'] < len(tasks):
                results['overall_valid'] = False

        # Level 3: Milestone
        if 'milestone' in levels:
            milestones = self.db.query(MasterPlanMilestone).join(MasterPlanPhase).filter(
                MasterPlanPhase.masterplan_id == masterplan_id
            ).all()

            milestone_results = []
            milestone_scores = []

            for milestone in milestones:
                result = self.milestone_validator.validate_milestone(milestone.milestone_id)
                milestone_results.append(self._format_milestone_result(result))
                milestone_scores.append(result.validation_score)

            results['results']['milestone'] = {
                'total_milestones': len(milestones),
                'valid_milestones': sum(1 for r in milestone_results if r['is_valid']),
                'avg_score': sum(milestone_scores) / len(milestone_scores) if milestone_scores else 0.0,
                'milestones': milestone_results
            }

            if results['results']['milestone']['valid_milestones'] < len(milestones):
                results['overall_valid'] = False

        # Level 4: MasterPlan
        if 'masterplan' in levels:
            masterplan_result = self.masterplan_validator.validate_system(masterplan_id)
            results['results']['masterplan'] = self._format_masterplan_result(masterplan_result)

            if not masterplan_result.is_valid:
                results['overall_valid'] = False

        # Calculate overall score
        level_scores = []
        for level in levels:
            if level in results['results']:
                if level == 'masterplan':
                    level_scores.append(results['results'][level]['validation_score'])
                else:
                    level_scores.append(results['results'][level]['avg_score'])

        results['overall_score'] = sum(level_scores) / len(level_scores) if level_scores else 0.0

        logger.info(f"Hierarchical validation complete: score={results['overall_score']:.2f}, valid={results['overall_valid']}")
        return results

    def batch_validate_atoms(self, atom_ids: List[uuid.UUID]) -> Dict[str, Any]:
        """
        Batch validate multiple atoms

        Args:
            atom_ids: List of atom UUIDs

        Returns:
            Batch validation results
        """
        logger.info(f"Batch validating {len(atom_ids)} atoms")

        results = []
        scores = []

        for atom_id in atom_ids:
            result = self.atomic_validator.validate_atom(atom_id)
            results.append(self._format_atomic_result(result))
            scores.append(result.validation_score)

        return {
            'total_atoms': len(atom_ids),
            'valid_atoms': sum(1 for r in results if r['is_valid']),
            'avg_score': sum(scores) / len(scores) if scores else 0.0,
            'atoms': results
        }

    # Formatting methods

    def _format_atomic_result(self, result: AtomicValidationResult) -> Dict[str, Any]:
        """Format atomic validation result"""
        return {
            'atom_id': str(result.atom_id),
            'is_valid': result.is_valid,
            'validation_score': result.validation_score,
            'checks': {
                'syntax': result.syntax_valid,
                'semantics': result.semantic_valid,
                'atomicity': result.atomicity_valid,
                'type_safety': result.type_safe,
                'runtime_safety': result.runtime_safe
            },
            'issues': [
                {
                    'level': issue.level,
                    'category': issue.category,
                    'message': issue.message,
                    'line': issue.line,
                    'column': issue.column,
                    'suggestion': issue.suggestion
                }
                for issue in result.issues
            ],
            'errors': result.errors,
            'warnings': result.warnings
        }

    def _format_task_result(self, result: TaskValidationResult) -> Dict[str, Any]:
        """Format task validation result"""
        return {
            'task_id': str(result.task_id),
            'is_valid': result.is_valid,
            'validation_score': result.validation_score,
            'checks': {
                'consistency': result.consistency_valid,
                'integration': result.integration_valid,
                'imports': result.imports_valid,
                'naming': result.naming_valid,
                'contracts': result.contracts_valid
            },
            'issues': [
                {
                    'level': issue.level,
                    'category': issue.category,
                    'message': issue.message,
                    'affected_atoms': [str(aid) for aid in issue.affected_atoms],
                    'suggestion': issue.suggestion
                }
                for issue in result.issues
            ],
            'errors': result.errors,
            'warnings': result.warnings
        }

    def _format_milestone_result(self, result: MilestoneValidationResult) -> Dict[str, Any]:
        """Format milestone validation result"""
        return {
            'milestone_id': str(result.milestone_id),
            'is_valid': result.is_valid,
            'validation_score': result.validation_score,
            'checks': {
                'interfaces': result.interfaces_valid,
                'contracts': result.contracts_valid,
                'api_consistency': result.api_consistent,
                'integration': result.integration_valid,
                'dependencies': result.dependencies_valid
            },
            'issues': [
                {
                    'level': issue.level,
                    'category': issue.category,
                    'message': issue.message,
                    'affected_tasks': [str(tid) for tid in issue.affected_tasks],
                    'suggestion': issue.suggestion
                }
                for issue in result.issues
            ],
            'errors': result.errors,
            'warnings': result.warnings
        }

    def _format_masterplan_result(self, result: MasterPlanValidationResult) -> Dict[str, Any]:
        """Format masterplan validation result"""
        return {
            'masterplan_id': str(result.masterplan_id),
            'is_valid': result.is_valid,
            'validation_score': result.validation_score,
            'checks': {
                'architecture': result.architecture_valid,
                'dependencies': result.dependencies_valid,
                'contracts': result.contracts_valid,
                'performance': result.performance_acceptable,
                'security': result.security_acceptable
            },
            'statistics': {
                'total_atoms': result.total_atoms,
                'total_tasks': result.total_tasks,
                'total_milestones': result.total_milestones
            },
            'issues': [
                {
                    'level': issue.level,
                    'category': issue.category,
                    'message': issue.message,
                    'affected_phases': [str(pid) for pid in issue.affected_phases],
                    'suggestion': issue.suggestion
                }
                for issue in result.issues
            ],
            'errors': result.errors,
            'warnings': result.warnings
        }
