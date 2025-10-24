"""
Milestone Validator - Level 3: Milestone Integration Validation

Validates milestone-level properties for tasks grouped under a Milestone:
- Inter-task interfaces (tasks within milestone work together)
- Milestone contracts (milestone achieves its goal)
- Task API consistency
- Task integration
- Task dependencies within milestone

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import logging
import re

from src.models import MasterPlanMilestone, MasterPlanTask, AtomicUnit

logger = logging.getLogger(__name__)


@dataclass
class MilestoneIssue:
    """Milestone-level validation issue"""
    level: str  # 'error', 'warning', 'info'
    category: str  # 'interfaces', 'contracts', 'api', 'integration', 'dependencies'
    message: str
    affected_tasks: List[uuid.UUID] = field(default_factory=list)
    suggestion: Optional[str] = None


@dataclass
class MilestoneValidationResult:
    """Result of milestone validation"""
    milestone_id: uuid.UUID
    is_valid: bool
    validation_score: float  # 0.0-1.0
    interfaces_valid: bool
    contracts_valid: bool
    api_consistent: bool
    integration_valid: bool
    dependencies_valid: bool
    issues: List[MilestoneIssue] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class MilestoneValidator:
    """
    Milestone validator - Level 3 (formerly ComponentValidator)

    Validates milestone integration for tasks grouped under Milestone:
    1. Interfaces: Task interfaces are compatible
    2. Contracts: Milestone-level contracts are respected
    3. API consistency: APIs are consistent across tasks
    4. Integration: Tasks integrate properly within milestone
    5. Dependencies: Task dependencies are valid and resolved

    Score calculation:
    - Interfaces: 25%
    - Contracts: 20%
    - API consistency: 20%
    - Integration: 20%
    - Dependencies: 15%
    """

    def __init__(self, db: Session):
        """
        Initialize milestone validator

        Args:
            db: Database session
        """
        self.db = db
        logger.info("MilestoneValidator initialized")

    def validate_milestone(self, milestone_id: uuid.UUID) -> MilestoneValidationResult:
        """
        Validate milestone integration

        Args:
            milestone_id: MasterPlanMilestone UUID

        Returns:
            MilestoneValidationResult with validation details
        """
        logger.info(f"Validating milestone: {milestone_id}")

        # Load milestone and its tasks
        milestone = self.db.query(MasterPlanMilestone).filter(
            MasterPlanMilestone.milestone_id == milestone_id
        ).first()

        if not milestone:
            return MilestoneValidationResult(
                milestone_id=milestone_id,
                is_valid=False,
                validation_score=0.0,
                interfaces_valid=False,
                contracts_valid=False,
                api_consistent=False,
                integration_valid=False,
                dependencies_valid=False,
                errors=["Milestone not found"]
            )

        # Load tasks in milestone
        tasks = self.db.query(MasterPlanTask).filter(
            MasterPlanTask.milestone_id == milestone_id
        ).all()

        if not tasks:
            # Milestones without tasks are valid (milestone planning phase)
            return MilestoneValidationResult(
                milestone_id=milestone_id,
                is_valid=True,
                validation_score=1.0,
                interfaces_valid=True,
                contracts_valid=True,
                api_consistent=True,
                integration_valid=True,
                dependencies_valid=True,
                warnings=["Milestone has no tasks - may be in planning phase"]
            )

        issues = []
        errors = []
        warnings = []
        score = 0.0

        # 1. Interfaces validation (25%)
        interfaces_valid, interface_issues = self._validate_interfaces(tasks)
        issues.extend(interface_issues)
        if interfaces_valid:
            score += 0.25
        else:
            errors.extend([i.message for i in interface_issues if i.level == 'error'])

        # 2. Contracts validation (20%)
        contracts_valid, contract_issues = self._validate_contracts(tasks)
        issues.extend(contract_issues)
        if contracts_valid:
            score += 0.20
        else:
            warnings.extend([i.message for i in contract_issues if i.level == 'warning'])

        # 3. API consistency (20%)
        api_consistent, api_issues = self._validate_api_consistency(tasks)
        issues.extend(api_issues)
        if api_consistent:
            score += 0.20
        else:
            warnings.extend([i.message for i in api_issues if i.level == 'warning'])

        # 4. Integration validation (20%)
        integration_valid, integration_issues = self._validate_integration(tasks)
        issues.extend(integration_issues)
        if integration_valid:
            score += 0.20
        else:
            errors.extend([i.message for i in integration_issues if i.level == 'error'])

        # 5. Dependencies validation (15%)
        dependencies_valid, dependency_issues = self._validate_dependencies(tasks)
        issues.extend(dependency_issues)
        if dependencies_valid:
            score += 0.15
        else:
            warnings.extend([i.message for i in dependency_issues if i.level == 'warning'])

        # Determine overall validity
        is_valid = interfaces_valid and integration_valid and score >= 0.75

        result = MilestoneValidationResult(
            milestone_id=milestone_id,
            is_valid=is_valid,
            validation_score=score,
            interfaces_valid=interfaces_valid,
            contracts_valid=contracts_valid,
            api_consistent=api_consistent,
            integration_valid=integration_valid,
            dependencies_valid=dependencies_valid,
            issues=issues,
            errors=errors,
            warnings=warnings
        )

        logger.info(f"Component validation complete: score={score:.2f}, valid={is_valid}")
        return result

    def _validate_interfaces(self, tasks: List[MasterPlanTask]) -> tuple[bool, List[MilestoneIssue]]:
        """Validate inter-module interfaces"""
        issues = []

        # Get all atoms for all tasks
        task_atoms: Dict[uuid.UUID, List[AtomicUnit]] = {}
        for task in tasks:
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.task_id == task.task_id
            ).all()
            task_atoms[task.task_id] = atoms

        # Build public API for each module
        task_apis: Dict[uuid.UUID, Set[str]] = {}
        for task_id, atoms in task_atoms.items():
            public_functions = set()
            for atom in atoms:
                # Find public functions (not starting with _)
                for match in re.finditer(r'def\s+([a-zA-Z]\w*)', atom.code_to_generate):
                    func_name = match.group(1)
                    if not func_name.startswith('_'):
                        public_functions.add(func_name)
            task_apis[task_id] = public_functions

        # Check for API conflicts (same function name with different signatures)
        all_functions: Dict[str, List[uuid.UUID]] = {}
        for task_id, functions in task_apis.items():
            for func in functions:
                if func not in all_functions:
                    all_functions[func] = []
                all_functions[func].append(task_id)

        # Flag potential conflicts
        for func, task_ids in all_functions.items():
            if len(task_ids) > 1:
                issues.append(MilestoneIssue(
                    level='warning',
                    category='interfaces',
                    message=f"Function '{func}' defined in multiple tasks",
                    affected_tasks=task_ids,
                    suggestion="Ensure consistent signatures or rename"
                ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_contracts(self, tasks: List[MasterPlanTask]) -> tuple[bool, List[MilestoneIssue]]:
        """Validate component contracts"""
        issues = []

        # Check that each module has clear public API
        for task in tasks:
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.task_id == task.task_id
            ).all()

            has_public_api = False
            for atom in atoms:
                # Check for public functions with type hints
                if re.search(r'def\s+[a-zA-Z]\w*\s*\([^)]*\)\s*->', atom.code_to_generate):
                    has_public_api = True
                    break

            if not has_public_api and len(atoms) > 0:
                issues.append(MilestoneIssue(
                    level='info',
                    category='contracts',
                    message=f"MasterPlanTask '{module.task_type}' lacks clear public API",
                    affected_tasks=[task.task_id],
                    suggestion="Add type-hinted public functions"
                ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_api_consistency(self, tasks: List[MasterPlanTask]) -> tuple[bool, List[MilestoneIssue]]:
        """Validate API consistency across tasks"""
        issues = []

        # Check naming convention consistency
        naming_styles = set()

        for task in tasks:
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.task_id == task.task_id
            ).all()

            for atom in atoms:
                functions = re.findall(r'def\s+(\w+)', atom.code_to_generate)
                for func in functions:
                    if not func.startswith('_'):
                        if '_' in func:
                            naming_styles.add('snake_case')
                        elif any(c.isupper() for c in func[1:]):
                            naming_styles.add('camelCase')

        if len(naming_styles) > 1:
            issues.append(MilestoneIssue(
                level='info',
                category='api',
                message=f"Mixed API naming styles: {', '.join(naming_styles)}",
                affected_tasks=[m.task_id for m in tasks],
                suggestion="Use consistent naming convention"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_integration(self, tasks: List[MasterPlanTask]) -> tuple[bool, List[MilestoneIssue]]:
        """Validate module integration"""
        issues = []

        # Build symbol tables for all tasks
        task_exports: Dict[uuid.UUID, Set[str]] = {}
        task_imports: Dict[uuid.UUID, Set[str]] = {}

        for task in tasks:
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.task_id == task.task_id
            ).all()

            exports = set()
            imports = set()

            for atom in atoms:
                code = atom.code_to_generate

                # Find exports (public functions)
                for match in re.finditer(r'def\s+([a-zA-Z]\w*)', code):
                    exports.add(match.group(1))

                # Find imports
                for match in re.finditer(r'from\s+\S+\s+import\s+(\w+)', code):
                    imports.add(match.group(1))

            task_exports[task.task_id] = exports
            task_imports[task.task_id] = imports

        # Check if imports are satisfied by other tasks
        all_exports = set()
        for exports in task_exports.values():
            all_exports.update(exports)

        for task_id, imports in task_imports.items():
            unsatisfied = imports - all_exports
            # Filter out standard library
            std_lib = {'os', 'sys', 'json', 'datetime', 'typing', 'dataclasses', 're'}
            unsatisfied = unsatisfied - std_lib

            if unsatisfied:
                issues.append(MilestoneIssue(
                    level='warning',
                    category='integration',
                    message=f"Unsatisfied imports: {', '.join(list(unsatisfied)[:5])}",
                    affected_tasks=[task_id],
                    suggestion="Ensure imports are available"
                ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_dependencies(self, tasks: List[MasterPlanTask]) -> tuple[bool, List[MilestoneIssue]]:
        """Validate component dependencies"""
        issues = []

        # Check for circular dependencies between tasks
        dependencies: Dict[uuid.UUID, Set[uuid.UUID]] = {}

        for task in tasks:
            dependencies[task.task_id] = set()

            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.task_id == task.task_id
            ).all()

            # Find what this module imports
            imported_symbols = set()
            for atom in atoms:
                for match in re.finditer(r'from\s+(\S+)\s+import', atom.code_to_generate):
                    imported_symbols.add(match.group(1))

            # Map imports to tasks
            for other_task in tasks:
                if other_task.task_id == task.task_id:
                    continue

                # Check if this module imports from other module
                if other_task.task_type in imported_symbols:
                    dependencies[task.task_id].add(other_task.task_id)

        # Detect cycles
        def has_cycle(node: uuid.UUID, visited: Set[uuid.UUID], rec_stack: Set[uuid.UUID]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for task in tasks:
            if task.task_id not in visited:
                if has_cycle(task.task_id, visited, set()):
                    issues.append(MilestoneIssue(
                        level='error',
                        category='dependencies',
                        message="Circular dependency detected between tasks",
                        affected_tasks=list(dependencies.keys()),
                        suggestion="Refactor to remove circular dependencies"
                    ))
                    break

        return len([i for i in issues if i.level == 'error']) == 0, issues
