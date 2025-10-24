"""
Task Validator - Level 2: Task Coherence Validation

Validates task-level properties for atoms grouped under a MasterPlanTask:
- Consistency between atoms within the task
- Integration coherence (atoms work together)
- Import resolution and usage
- Naming consistency
- Task-level contracts

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import logging
import re

from src.models import AtomicUnit, MasterPlanTask

logger = logging.getLogger(__name__)


@dataclass
class TaskIssue:
    """Task-level validation issue"""
    level: str  # 'error', 'warning', 'info'
    category: str  # 'consistency', 'integration', 'imports', 'naming', 'contracts'
    message: str
    affected_atoms: List[uuid.UUID] = field(default_factory=list)
    suggestion: Optional[str] = None


@dataclass
class TaskValidationResult:
    """Result of task validation"""
    task_id: uuid.UUID
    is_valid: bool
    validation_score: float  # 0.0-1.0
    consistency_valid: bool
    integration_valid: bool
    imports_valid: bool
    naming_valid: bool
    contracts_valid: bool
    issues: List[TaskIssue] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TaskValidator:
    """
    Task validator - Level 2 (formerly ModuleValidator)

    Validates task coherence for atoms grouped under MasterPlanTask:
    1. Consistency: Atoms follow same patterns and conventions
    2. Integration: Atoms integrate properly (dependencies resolved)
    3. Imports: All imports are valid and used
    4. Naming: Consistent naming conventions
    5. Contracts: Task interfaces are well-defined

    Score calculation:
    - Consistency: 25%
    - Integration: 25%
    - Imports: 20%
    - Naming: 15%
    - Contracts: 15%
    """

    def __init__(self, db: Session):
        """
        Initialize task validator

        Args:
            db: Database session
        """
        self.db = db
        logger.info("TaskValidator initialized")

    def validate_task(self, task_id: uuid.UUID) -> TaskValidationResult:
        """
        Validate task coherence

        Args:
            task_id: MasterPlanTask UUID

        Returns:
            TaskValidationResult with validation details
        """
        logger.info(f"Validating task: {task_id}")

        # Load task and its atoms
        task = self.db.query(MasterPlanTask).filter(
            MasterPlanTask.task_id == task_id
        ).first()

        if not task:
            return TaskValidationResult(
                task_id=task_id,
                is_valid=False,
                validation_score=0.0,
                consistency_valid=False,
                integration_valid=False,
                imports_valid=False,
                naming_valid=False,
                contracts_valid=False,
                errors=["Task not found"]
            )

        # Load atoms in task
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.task_id == task_id
        ).all()

        if not atoms:
            # Tasks without atoms are valid (not all tasks need atomization)
            return TaskValidationResult(
                task_id=task_id,
                is_valid=True,
                validation_score=1.0,
                consistency_valid=True,
                integration_valid=True,
                imports_valid=True,
                naming_valid=True,
                contracts_valid=True,
                warnings=["Task has no atoms - may not require atomization"]
            )

        issues = []
        errors = []
        warnings = []
        score = 0.0

        # 1. Consistency validation (25%)
        consistency_valid, consistency_issues = self._validate_consistency(atoms)
        issues.extend(consistency_issues)
        if consistency_valid:
            score += 0.25
        else:
            warnings.extend([i.message for i in consistency_issues if i.level == 'warning'])

        # 2. Integration validation (25%)
        integration_valid, integration_issues = self._validate_integration(atoms)
        issues.extend(integration_issues)
        if integration_valid:
            score += 0.25
        else:
            errors.extend([i.message for i in integration_issues if i.level == 'error'])

        # 3. Imports validation (20%)
        imports_valid, import_issues = self._validate_imports(atoms)
        issues.extend(import_issues)
        if imports_valid:
            score += 0.20
        else:
            warnings.extend([i.message for i in import_issues if i.level == 'warning'])

        # 4. Naming validation (15%)
        naming_valid, naming_issues = self._validate_naming(atoms)
        issues.extend(naming_issues)
        if naming_valid:
            score += 0.15
        else:
            warnings.extend([i.message for i in naming_issues if i.level == 'warning'])

        # 5. Contracts validation (15%)
        contracts_valid, contract_issues = self._validate_contracts(atoms)
        issues.extend(contract_issues)
        if contracts_valid:
            score += 0.15
        else:
            warnings.extend([i.message for i in contract_issues if i.level == 'warning'])

        # Determine overall validity
        is_valid = integration_valid and score >= 0.7

        result = TaskValidationResult(
            task_id=task_id,
            is_valid=is_valid,
            validation_score=score,
            consistency_valid=consistency_valid,
            integration_valid=integration_valid,
            imports_valid=imports_valid,
            naming_valid=naming_valid,
            contracts_valid=contracts_valid,
            issues=issues,
            errors=errors,
            warnings=warnings
        )

        logger.info(f"Task validation complete: score={score:.2f}, valid={is_valid}")
        return result

    def _validate_consistency(self, atoms: List[AtomicUnit]) -> tuple[bool, List[TaskIssue]]:
        """Validate consistency across atoms"""
        issues = []

        # Check language consistency
        languages = set(atom.language for atom in atoms)
        if len(languages) > 1:
            issues.append(TaskIssue(
                level='warning',
                category='consistency',
                message=f"Multiple languages in task: {', '.join(languages)}",
                affected_atoms=[atom.atom_id for atom in atoms],
                suggestion="Keep task in single language"
            ))

        # Check code style consistency (indentation)
        indentations = set()
        for atom in atoms:
            # Detect indentation (spaces vs tabs)
            if '\t' in atom.code_to_generate:
                indentations.add('tabs')
            elif '    ' in atom.code_to_generate:
                indentations.add('spaces')

        if len(indentations) > 1:
            issues.append(TaskIssue(
                level='info',
                category='consistency',
                message="Inconsistent indentation (tabs vs spaces)",
                affected_atoms=[atom.atom_id for atom in atoms],
                suggestion="Use consistent indentation"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_integration(self, atoms: List[AtomicUnit]) -> tuple[bool, List[TaskIssue]]:
        """Validate atom integration"""
        issues = []

        # Build symbol table
        defined_symbols = set()
        used_symbols = set()
        atom_definitions: Dict[str, uuid.UUID] = {}
        atom_uses: Dict[str, List[uuid.UUID]] = {}

        for atom in atoms:
            # Find definitions (functions, classes, variables)
            code = atom.code_to_generate

            # Python functions
            for match in re.finditer(r'def\s+(\w+)', code):
                symbol = match.group(1)
                defined_symbols.add(symbol)
                atom_definitions[symbol] = atom.atom_id

            # Python classes
            for match in re.finditer(r'class\s+(\w+)', code):
                symbol = match.group(1)
                defined_symbols.add(symbol)
                atom_definitions[symbol] = atom.atom_id

            # Find uses (function calls)
            for match in re.finditer(r'(\w+)\s*\(', code):
                symbol = match.group(1)
                if symbol not in {'if', 'for', 'while', 'def', 'class'}:
                    used_symbols.add(symbol)
                    if symbol not in atom_uses:
                        atom_uses[symbol] = []
                    atom_uses[symbol].append(atom.atom_id)

        # Check for undefined symbols (cross-atom references)
        undefined = used_symbols - defined_symbols
        # Filter out builtins
        builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'range', 'enumerate'}
        undefined = undefined - builtins

        if undefined:
            issues.append(TaskIssue(
                level='warning',
                category='integration',
                message=f"Undefined symbols: {', '.join(list(undefined)[:5])}",
                affected_atoms=list(set(aid for sym in undefined for aid in atom_uses.get(sym, []))),
                suggestion="Ensure all referenced symbols are defined"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_imports(self, atoms: List[AtomicUnit]) -> tuple[bool, List[TaskIssue]]:
        """Validate import statements"""
        issues = []

        all_imports = set()
        import_atoms = []

        for atom in atoms:
            code = atom.code_to_generate

            # Find Python imports
            for match in re.finditer(r'^(?:import|from)\s+(\S+)', code, re.MULTILINE):
                module = match.group(1)
                all_imports.add(module)
                import_atoms.append((module, atom.atom_id))

        # Check for duplicate imports
        import_counts: Dict[str, int] = {}
        for module, _ in import_atoms:
            import_counts[module] = import_counts.get(module, 0) + 1

        duplicates = {mod: count for mod, count in import_counts.items() if count > 1}
        if duplicates:
            issues.append(TaskIssue(
                level='info',
                category='imports',
                message=f"Duplicate imports: {', '.join(duplicates.keys())}",
                suggestion="Consolidate imports in single location"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_naming(self, atoms: List[AtomicUnit]) -> tuple[bool, List[TaskIssue]]:
        """Validate naming conventions"""
        issues = []

        # Check naming convention consistency
        snake_case = 0
        camel_case = 0

        for atom in atoms:
            code = atom.code_to_generate

            # Find function names
            functions = re.findall(r'def\s+(\w+)', code)
            for func in functions:
                if '_' in func:
                    snake_case += 1
                elif any(c.isupper() for c in func[1:]):
                    camel_case += 1

        if snake_case > 0 and camel_case > 0:
            issues.append(TaskIssue(
                level='info',
                category='naming',
                message=f"Mixed naming conventions (snake_case: {snake_case}, camelCase: {camel_case})",
                suggestion="Use consistent naming convention"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_contracts(self, atoms: List[AtomicUnit]) -> tuple[bool, List[TaskIssue]]:
        """Validate task contracts (interfaces)"""
        issues = []

        # Check for public API definition (functions with type hints)
        public_functions = []
        private_functions = []

        for atom in atoms:
            code = atom.code_to_generate

            # Find function definitions
            for match in re.finditer(r'def\s+(\w+)', code):
                func_name = match.group(1)
                if func_name.startswith('_'):
                    private_functions.append(func_name)
                else:
                    public_functions.append(func_name)

        # Task should have clear public API
        if not public_functions and len(atoms) > 1:
            issues.append(TaskIssue(
                level='info',
                category='contracts',
                message="No public functions defined",
                suggestion="Define clear public API"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues
