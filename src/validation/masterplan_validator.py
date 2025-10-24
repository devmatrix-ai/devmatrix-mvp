"""
System Validator - Level 4: System-Wide Validation

Validates system-level properties:
- Architecture compliance
- Cross-component dependencies
- System-wide contracts
- Performance characteristics
- Security posture

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import logging
import networkx as nx

from src.models import MasterPlan, MasterPlanPhase, MasterPlanMilestone, MasterPlanTask, AtomicUnit, DependencyGraph

logger = logging.getLogger(__name__)


@dataclass
class MasterPlanIssue:
    """System-level validation issue"""
    level: str  # 'error', 'warning', 'info'
    category: str  # 'architecture', 'dependencies', 'contracts', 'performance', 'security'
    message: str
    affected_phases: List[uuid.UUID] = field(default_factory=list)
    suggestion: Optional[str] = None


@dataclass
class MasterPlanValidationResult:
    """Result of system validation"""
    masterplan_id: uuid.UUID
    is_valid: bool
    validation_score: float  # 0.0-1.0
    architecture_valid: bool
    dependencies_valid: bool
    contracts_valid: bool
    performance_acceptable: bool
    security_acceptable: bool
    issues: List[MasterPlanIssue] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_atoms: int = 0
    total_tasks: int = 0
    total_milestones: int = 0


class MasterPlanValidator:
    """
    System validator - Level 4

    Validates system-wide properties:
    1. Architecture: System follows architectural patterns
    2. Dependencies: Dependency graph is valid (no cycles, proper structure)
    3. Contracts: System-level contracts are satisfied
    4. Performance: System meets performance requirements
    5. Security: System meets security standards

    Score calculation:
    - Architecture: 25%
    - Dependencies: 25%
    - Contracts: 20%
    - Performance: 15%
    - Security: 15%
    """

    def __init__(self, db: Session):
        """
        Initialize system validator

        Args:
            db: Database session
        """
        self.db = db
        logger.info("MasterPlanValidator initialized")

    def validate_system(self, masterplan_id: uuid.UUID) -> MasterPlanValidationResult:
        """
        Validate entire system

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            MasterPlanValidationResult with validation details
        """
        logger.info(f"Validating system: {masterplan_id}")

        # Load masterplan
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            return MasterPlanValidationResult(
                masterplan_id=masterplan_id,
                is_valid=False,
                validation_score=0.0,
                architecture_valid=False,
                dependencies_valid=False,
                contracts_valid=False,
                performance_acceptable=False,
                security_acceptable=False,
                errors=["MasterPlan not found"]
            )

        # Load all phases, milestones, tasks, atoms
        from src.models import MasterPlanPhase, MasterPlanMilestone

        phases = self.db.query(MasterPlanPhase).filter(
            MasterPlanPhase.masterplan_id == masterplan_id
        ).all()

        milestones = self.db.query(MasterPlanMilestone).join(MasterPlanPhase).filter(
            MasterPlanPhase.masterplan_id == masterplan_id
        ).all()

        tasks = self.db.query(MasterPlanTask).join(MasterPlanMilestone).join(MasterPlanPhase).filter(
            MasterPlanPhase.masterplan_id == masterplan_id
        ).all()

        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        if not atoms and not tasks:
            # MasterPlan without atoms or tasks is valid (planning phase)
            return MasterPlanValidationResult(
                masterplan_id=masterplan_id,
                is_valid=True,
                validation_score=1.0,
                architecture_valid=True,
                dependencies_valid=True,
                contracts_valid=True,
                performance_acceptable=True,
                security_acceptable=True,
                warnings=["MasterPlan has no atoms or tasks - may be in planning phase"],
                total_atoms=0,
                total_tasks=0,
                total_milestones=len(milestones)
            )

        issues = []
        errors = []
        warnings = []
        score = 0.0

        # 1. Architecture validation (25%)
        architecture_valid, arch_issues = self._validate_architecture(
            masterplan, phases, milestones, tasks, atoms
        )
        issues.extend(arch_issues)
        if architecture_valid:
            score += 0.25
        else:
            warnings.extend([i.message for i in arch_issues if i.level == 'warning'])

        # 2. Dependencies validation (25%)
        dependencies_valid, dep_issues = self._validate_dependencies(
            masterplan_id, tasks, atoms
        )
        issues.extend(dep_issues)
        if dependencies_valid:
            score += 0.25
        else:
            errors.extend([i.message for i in dep_issues if i.level == 'error'])

        # 3. Contracts validation (20%)
        contracts_valid, contract_issues = self._validate_contracts(
            milestones, tasks
        )
        issues.extend(contract_issues)
        if contracts_valid:
            score += 0.20
        else:
            warnings.extend([i.message for i in contract_issues if i.level == 'warning'])

        # 4. Performance validation (15%)
        performance_acceptable, perf_issues = self._validate_performance(
            atoms, tasks
        )
        issues.extend(perf_issues)
        if performance_acceptable:
            score += 0.15
        else:
            warnings.extend([i.message for i in perf_issues if i.level == 'warning'])

        # 5. Security validation (15%)
        security_acceptable, sec_issues = self._validate_security(atoms)
        issues.extend(sec_issues)
        if security_acceptable:
            score += 0.15
        else:
            warnings.extend([i.message for i in sec_issues if i.level == 'warning'])

        # Determine overall validity
        is_valid = dependencies_valid and architecture_valid and score >= 0.75

        result = MasterPlanValidationResult(
            masterplan_id=masterplan_id,
            is_valid=is_valid,
            validation_score=score,
            architecture_valid=architecture_valid,
            dependencies_valid=dependencies_valid,
            contracts_valid=contracts_valid,
            performance_acceptable=performance_acceptable,
            security_acceptable=security_acceptable,
            issues=issues,
            errors=errors,
            warnings=warnings,
            total_atoms=len(atoms),
            total_tasks=len(tasks),
            total_milestones=len(milestones)
        )

        logger.info(f"MasterPlan validation complete: score={score:.2f}, valid={is_valid}")
        return result

    def _validate_architecture(
        self,
        masterplan: MasterPlan,
        phases: List,
        milestones: List,
        tasks: List[MasterPlanTask],
        atoms: List[AtomicUnit]
    ) -> tuple[bool, List[MasterPlanIssue]]:
        """Validate architectural patterns"""
        issues = []

        # Check component organization
        if len(phases) == 0:
            issues.append(MasterPlanIssue(
                level='warning',
                category='architecture',
                message="No phases defined in system",
                suggestion="Organize code into logical phases"
            ))

        # Check module organization
        if len(tasks) == 0:
            issues.append(MasterPlanIssue(
                level='error',
                category='architecture',
                message="No tasks defined in system",
                suggestion="Organize code into tasks"
            ))
            return False, issues

        # Check atoms-per-module ratio
        avg_atoms_per_module = len(atoms) / len(tasks) if tasks else 0
        if avg_atoms_per_module > 20:
            issues.append(MasterPlanIssue(
                level='warning',
                category='architecture',
                message=f"Average {avg_atoms_per_module:.0f} atoms per module, consider splitting",
                suggestion="Keep tasks focused (5-15 atoms per module)"
            ))

        # Check layering (all atoms should be in tasks, all tasks in phases)
        atoms_without_module = sum(1 for atom in atoms if atom.module_id is None)
        if atoms_without_module > 0:
            issues.append(MasterPlanIssue(
                level='error',
                category='architecture',
                message=f"{atoms_without_module} atoms not assigned to tasks",
                suggestion="Assign all atoms to tasks"
            ))
            return False, issues

        tasks_without_component = sum(1 for module in tasks if module.component_id is None)
        if tasks_without_component > 0:
            issues.append(MasterPlanIssue(
                level='warning',
                category='architecture',
                message=f"{tasks_without_component} tasks not assigned to phases",
                suggestion="Assign all tasks to phases"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_dependencies(
        self,
        masterplan_id: uuid.UUID,
        phases: List[MasterPlanPhase],
        tasks: List[MasterPlanTask],
        atoms: List[AtomicUnit]
    ) -> tuple[bool, List[MasterPlanIssue]]:
        """Validate dependency graph"""
        issues = []

        # Load dependency graph
        dep_graph = self.db.query(DependencyGraph).filter(
            DependencyGraph.masterplan_id == masterplan_id
        ).first()

        if not dep_graph:
            issues.append(MasterPlanIssue(
                level='warning',
                category='dependencies',
                message="Dependency graph not built",
                suggestion="Build dependency graph for validation"
            ))
            return True, issues  # Not critical

        # Check for cycles
        if dep_graph.has_cycles:
            issues.append(MasterPlanIssue(
                level='error',
                category='dependencies',
                message="Circular dependencies detected in system",
                affected_phases=[c.component_id for c in phases],
                suggestion="Refactor to eliminate circular dependencies"
            ))
            return False, issues

        # Check max parallelism
        if dep_graph.max_parallelism < 2:
            issues.append(MasterPlanIssue(
                level='info',
                category='dependencies',
                message=f"Low parallelism ({dep_graph.max_parallelism}), mostly sequential execution",
                suggestion="Review dependencies to enable more parallelism"
            ))

        # Check dependency density
        if dep_graph.total_atoms > 0:
            dependency_density = dep_graph.total_dependencies / dep_graph.total_atoms
            if dependency_density > 3.0:
                issues.append(MasterPlanIssue(
                    level='warning',
                    category='dependencies',
                    message=f"High dependency density ({dependency_density:.1f} per atom)",
                    suggestion="Reduce coupling between atoms"
                ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_contracts(
        self,
        phases: List[MasterPlanPhase],
        tasks: List[MasterPlanTask]
    ) -> tuple[bool, List[MasterPlanIssue]]:
        """Validate system-level contracts"""
        issues = []

        # Check that phases have clear interfaces
        for component in phases:
            component_tasks = [m for m in tasks if m.component_id == component.component_id]

            if not component_tasks:
                issues.append(MasterPlanIssue(
                    level='warning',
                    category='contracts',
                    message=f"MasterPlanPhase '{component.component_path}' has no tasks",
                    affected_phases=[component.component_id],
                    suggestion="Add tasks to component or remove empty component"
                ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_performance(
        self,
        atoms: List[AtomicUnit],
        tasks: List[MasterPlanTask]
    ) -> tuple[bool, List[MasterPlanIssue]]:
        """Validate performance characteristics"""
        issues = []

        # Check complexity distribution
        high_complexity_atoms = [a for a in atoms if a.complexity > 5.0]
        if len(high_complexity_atoms) > len(atoms) * 0.2:
            issues.append(MasterPlanIssue(
                level='warning',
                category='performance',
                message=f"{len(high_complexity_atoms)} atoms have high complexity (>5.0)",
                suggestion="Refactor complex atoms for better performance"
            ))

        # Check LOC distribution
        large_atoms = [a for a in atoms if len(a.generated_code.split('\n')) > 20]
        if len(large_atoms) > len(atoms) * 0.1:
            issues.append(MasterPlanIssue(
                level='info',
                category='performance',
                message=f"{len(large_atoms)} atoms exceed 20 LOC",
                suggestion="Consider splitting large atoms"
            ))

        # Check total system size
        total_loc = sum(len(a.generated_code.split('\n')) for a in atoms)
        if total_loc > 10000:
            issues.append(MasterPlanIssue(
                level='info',
                category='performance',
                message=f"System has {total_loc} total LOC",
                suggestion="Large system, ensure proper modularization"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_security(self, atoms: List[AtomicUnit]) -> tuple[bool, List[MasterPlanIssue]]:
        """Validate security posture"""
        issues = []

        # Check for dangerous patterns across all atoms
        dangerous_patterns = {
            'eval(': 'dangerous_eval',
            'exec(': 'dangerous_exec',
            'import *': 'wildcard_import',
            '__import__': 'dynamic_import',
        }

        violations: Dict[str, int] = {}

        for atom in atoms:
            code = atom.generated_code
            for pattern, violation_type in dangerous_patterns.items():
                if pattern in code:
                    violations[violation_type] = violations.get(violation_type, 0) + 1

        if violations:
            issues.append(MasterPlanIssue(
                level='warning',
                category='security',
                message=f"Security issues detected: {violations}",
                suggestion="Review and mitigate security risks"
            ))

        # Check for SQL injection risks (basic check)
        sql_atoms = [a for a in atoms if 'execute(' in a.generated_code and 'f"' in a.generated_code]
        if sql_atoms:
            issues.append(MasterPlanIssue(
                level='warning',
                category='security',
                message=f"{len(sql_atoms)} atoms may have SQL injection risks",
                suggestion="Use parameterized queries"
            ))

        return len([i for i in issues if i.level == 'error']) == 0, issues
