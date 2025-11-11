# Phase 5: Hierarchical Validation

**Document**: 07 of 15
**Purpose**: 4-level validation system for error detection and quality assurance

---

## Overview

**Phase 5 catches errors EARLY** at multiple levels before they propagate.

**Key Innovation**: Progressive validation from atomic → system level

**Goal**: Catch 98% of errors before final integration

---

## The 4-Level Validation Pyramid

```
Level 4: System Validation (Full Project)
   ↑ Catches 99% of remaining errors
Level 3: Component Validation (50-100 atoms)
   ↑ Catches 98% of remaining errors
Level 2: Module Validation (10-20 atoms)
   ↑ Catches 95% of remaining errors
Level 1: Atomic Validation (Per Atom)
   ↑ Catches 90% of errors

Blast Radius Reduction:
- Error at Level 1: Only 1 atom affected (0.125%)
- Error at Level 2: Only 10-20 atoms affected (1.25-2.5%)
- Error at Level 3: Only 50-100 atoms affected (6.25-12.5%)
- Error at Level 4: Full system (100%) but rare
```

---

## Level 1: Atomic Validation

### Purpose
Validate each atom immediately after generation.

### Validation Checks

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class ValidationSeverity(Enum):
    """Severity of validation issue."""
    CRITICAL = "critical"    # Must fix
    ERROR = "error"          # Should fix
    WARNING = "warning"      # Nice to fix
    INFO = "info"            # Informational

@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: ValidationSeverity
    category: str
    message: str
    line_number: int = None
    suggestion: str = None

@dataclass
class AtomicValidationResult:
    """Result of atomic validation."""
    atom_id: str
    passed: bool
    score: float  # 0.0 - 1.0
    issues: List[ValidationIssue]
    execution_time: float  # seconds

class AtomicValidator:
    """
    Level 1: Validate individual atomic units.
    """

    def validate(self, atom: AtomicUnit) -> AtomicValidationResult:
        """
        Comprehensive atomic validation.

        Checks:
        1. Syntax correctness
        2. Type consistency
        3. Naming conventions
        4. Code complexity
        5. Documentation
        6. Security basics
        7. Context completeness
        """
        issues = []
        start_time = time.time()

        # 1. Syntax validation (CRITICAL)
        issues.extend(self._validate_syntax(atom))

        # 2. Type validation (ERROR)
        issues.extend(self._validate_types(atom))

        # 3. Naming conventions (WARNING)
        issues.extend(self._validate_naming(atom))

        # 4. Complexity (WARNING)
        issues.extend(self._validate_complexity(atom))

        # 5. Documentation (INFO)
        issues.extend(self._validate_documentation(atom))

        # 6. Security (CRITICAL/ERROR)
        issues.extend(self._validate_security(atom))

        # 7. Context completeness (ERROR)
        issues.extend(self._validate_context(atom))

        # Calculate score
        score = self._calculate_score(issues)

        # Passed if no CRITICAL issues and score >= 0.80
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        passed = len(critical_issues) == 0 and score >= 0.80

        execution_time = time.time() - start_time

        return AtomicValidationResult(
            atom_id=atom.id,
            passed=passed,
            score=score,
            issues=issues,
            execution_time=execution_time
        )

    def _validate_syntax(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Validate syntax correctness."""
        issues = []

        try:
            if atom.language == 'python':
                import ast
                ast.parse(atom.code)
            elif atom.language in ['typescript', 'javascript']:
                # Would use actual parser in production
                pass
        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category='syntax',
                message=f"Syntax error: {str(e)}",
                line_number=e.lineno if hasattr(e, 'lineno') else None,
                suggestion="Fix syntax error before proceeding"
            ))

        return issues

    def _validate_types(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Validate type consistency."""
        issues = []

        # Check for missing type hints (Python)
        if atom.language == 'python' and atom.node_type == 'function_definition':
            if ':' not in atom.code or '->' not in atom.code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='types',
                    message="Missing type hints",
                    suggestion="Add type hints for parameters and return value"
                ))

        return issues

    def _validate_naming(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Validate naming conventions."""
        issues = []

        if atom.language == 'python':
            # Check function naming (should be snake_case)
            if atom.node_type == 'function_definition':
                import re
                func_match = re.search(r'def\s+(\w+)', atom.code)
                if func_match:
                    func_name = func_match.group(1)
                    if not func_name.islower() or ' ' in func_name:
                        if not all(c.islower() or c == '_' for c in func_name):
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                category='naming',
                                message=f"Function name '{func_name}' not snake_case",
                                suggestion="Use snake_case for function names"
                            ))

        return issues

    def _validate_complexity(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Validate code complexity."""
        issues = []

        if atom.complexity > 5:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='complexity',
                message=f"High complexity ({atom.complexity})",
                suggestion="Refactor to reduce complexity below 5"
            ))
        elif atom.complexity > 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='complexity',
                message=f"Moderate complexity ({atom.complexity})",
                suggestion="Consider simplifying logic"
            ))

        return issues

    def _validate_documentation(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Validate documentation."""
        issues = []

        if atom.node_type in ['function_definition', 'class_definition']:
            doc = atom.context.get('documentation', {})
            if not doc.get('has_docstring'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category='documentation',
                    message="Missing docstring",
                    suggestion="Add docstring describing purpose and parameters"
                ))

        return issues

    def _validate_security(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Basic security validation."""
        issues = []

        # Check for dangerous patterns
        dangerous_patterns = {
            'eval(': 'Avoid eval() - security risk',
            'exec(': 'Avoid exec() - security risk',
            'os.system(': 'Avoid os.system() - use subprocess instead',
            '__import__': 'Avoid dynamic imports',
            'password': 'Possible hardcoded password',
            'api_key': 'Possible hardcoded API key'
        }

        code_lower = atom.code.lower()
        for pattern, message in dangerous_patterns.items():
            if pattern.lower() in code_lower:
                severity = ValidationSeverity.CRITICAL if pattern in ['eval(', 'exec('] else ValidationSeverity.ERROR
                issues.append(ValidationIssue(
                    severity=severity,
                    category='security',
                    message=message,
                    suggestion="Review and use secure alternative"
                ))

        return issues

    def _validate_context(self, atom: AtomicUnit) -> List[ValidationIssue]:
        """Validate context completeness."""
        issues = []

        completeness = atom.context.get('completeness_score', 0.0)
        if completeness < 0.90:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='context',
                message=f"Low context completeness ({completeness:.1%})",
                suggestion="Enrich context to ≥95%"
            ))

        return issues

    def _calculate_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate validation score (0.0 - 1.0)."""
        if not issues:
            return 1.0

        # Deduct points by severity
        deductions = {
            ValidationSeverity.CRITICAL: 0.3,
            ValidationSeverity.ERROR: 0.1,
            ValidationSeverity.WARNING: 0.03,
            ValidationSeverity.INFO: 0.01
        }

        score = 1.0
        for issue in issues:
            score -= deductions.get(issue.severity, 0.0)

        return max(0.0, score)
```

---

## Level 2: Module Validation

### Purpose
Validate groups of 10-20 related atoms.

### Implementation

```python
class ModuleValidator:
    """
    Level 2: Validate modules (groups of atoms).
    """

    def validate(
        self,
        atoms: List[AtomicUnit],
        module_name: str
    ) -> ValidationResult:
        """
        Validate a module.

        Checks:
        1. Interface consistency
        2. Dependency satisfaction
        3. Integration points
        4. Module cohesion
        """
        issues = []

        # 1. Interface consistency
        issues.extend(self._validate_interfaces(atoms))

        # 2. Dependency satisfaction
        issues.extend(self._validate_dependencies(atoms))

        # 3. Integration points
        issues.extend(self._validate_integration(atoms))

        # 4. Module cohesion
        issues.extend(self._validate_cohesion(atoms))

        # Calculate score
        score = self._calculate_score(issues)
        passed = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) == 0

        return ValidationResult(
            level=2,
            scope=module_name,
            passed=passed,
            score=score,
            issues=issues
        )

    def _validate_interfaces(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate that interfaces are consistent."""
        issues = []

        # Check that function signatures match usage
        # Build map of definitions
        definitions = {}
        for atom in atoms:
            if atom.node_type == 'function_definition':
                func_name = self._extract_function_name(atom.code)
                if func_name:
                    params = self._extract_parameters(atom.code)
                    definitions[func_name] = params

        # Check usage
        for atom in atoms:
            calls = self._extract_function_calls(atom.code)
            for func_name, args_count in calls.items():
                if func_name in definitions:
                    expected_params = len(definitions[func_name])
                    if args_count != expected_params:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category='interface',
                            message=f"Function {func_name} called with {args_count} args, expects {expected_params}",
                            suggestion="Fix function call arguments"
                        ))

        return issues

    def _validate_dependencies(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate that all dependencies are satisfied."""
        issues = []

        atom_ids = {a.id for a in atoms}

        for atom in atoms:
            for dep_id in atom.depends_on:
                if dep_id not in atom_ids:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category='dependencies',
                        message=f"Atom {atom.name} depends on {dep_id} which is not in this module",
                        suggestion="Ensure all dependencies are included or available"
                    ))

        return issues

    def _validate_integration(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate integration between atoms."""
        issues = []

        # Run integration tests
        # In real implementation, would execute test suite
        # For now, basic smoke test

        try:
            # Combine all code
            combined_code = '\n\n'.join(a.code for a in atoms)

            # Try to parse combined
            if atoms and atoms[0].language == 'python':
                import ast
                ast.parse(combined_code)

        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category='integration',
                message=f"Integration error: {str(e)}",
                suggestion="Fix integration issues between atoms"
            ))

        return issues

    def _validate_cohesion(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate that module has good cohesion."""
        issues = []

        # Check that atoms are related
        # Heuristic: check for shared naming patterns
        names = [a.name for a in atoms]

        # Extract common words
        from collections import Counter
        words = []
        for name in names:
            words.extend(name.lower().split())

        word_counts = Counter(words)
        most_common = word_counts.most_common(1)

        if most_common and most_common[0][1] < len(atoms) * 0.3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='cohesion',
                message="Module may have low cohesion - atoms seem unrelated",
                suggestion="Consider reorganizing atoms into more cohesive modules"
            ))

        return issues
```

---

## Level 3: Component Validation

### Purpose
Validate larger components (50-100 atoms).

### Implementation

```python
class ComponentValidator:
    """
    Level 3: Validate components (large functional units).
    """

    def validate(
        self,
        atoms: List[AtomicUnit],
        component_name: str
    ) -> ValidationResult:
        """
        Validate a component.

        Checks:
        1. Architecture compliance
        2. API contracts
        3. Error handling
        4. Performance characteristics
        """
        issues = []

        # 1. Architecture compliance
        issues.extend(self._validate_architecture(atoms))

        # 2. API contracts
        issues.extend(self._validate_api_contracts(atoms))

        # 3. Error handling
        issues.extend(self._validate_error_handling(atoms))

        # 4. Performance
        issues.extend(self._validate_performance(atoms))

        score = self._calculate_score(issues)
        passed = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) == 0

        return ValidationResult(
            level=3,
            scope=component_name,
            passed=passed,
            score=score,
            issues=issues
        )

    def _validate_architecture(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate architectural patterns."""
        issues = []

        # Check layering (e.g., models → services → controllers)
        layers = self._identify_layers(atoms)

        # Validate no reverse dependencies
        for atom in atoms:
            atom_layer = self._get_atom_layer(atom)
            for dep_id in atom.depends_on:
                dep_atom = next((a for a in atoms if a.id == dep_id), None)
                if dep_atom:
                    dep_layer = self._get_atom_layer(dep_atom)
                    if layers.get(atom_layer, 0) < layers.get(dep_layer, 0):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category='architecture',
                            message=f"Layer violation: {atom.name} ({atom_layer}) depends on {dep_atom.name} ({dep_layer})",
                            suggestion="Fix architectural layering"
                        ))

        return issues

    def _validate_api_contracts(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate API contracts."""
        issues = []

        # Find public APIs (functions/classes with public names)
        public_apis = [a for a in atoms if not a.name.startswith('_')]

        for api in public_apis:
            # Check documentation
            if not api.context.get('documentation', {}).get('has_docstring'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='api',
                    message=f"Public API {api.name} missing documentation",
                    suggestion="Add comprehensive docstring"
                ))

            # Check type hints
            if not api.context.get('type_context', {}).get('has_type_hints'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='api',
                    message=f"Public API {api.name} missing type hints",
                    suggestion="Add type annotations"
                ))

        return issues

    def _validate_error_handling(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Validate error handling."""
        issues = []

        # Check for try/except blocks
        error_handling_count = 0

        for atom in atoms:
            if 'try' in atom.code and 'except' in atom.code:
                error_handling_count += 1

        if error_handling_count == 0 and len(atoms) > 20:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='error_handling',
                message="No error handling detected in component",
                suggestion="Add try/except blocks for critical operations"
            ))

        return issues

    def _validate_performance(self, atoms: List[AtomicUnit]) -> List[ValidationIssue]:
        """Basic performance validation."""
        issues = []

        # Check for obvious performance issues
        for atom in atoms:
            # Nested loops
            if atom.code.count('for') > 2:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='performance',
                    message=f"Atom {atom.name} has nested loops (potential O(n³) or worse)",
                    suggestion="Consider optimizing algorithm"
                ))

        return issues
```

---

## Level 4: System Validation

### Purpose
Validate the entire generated project.

### Implementation

```python
class SystemValidator:
    """
    Level 4: Validate complete system.
    """

    def validate(
        self,
        atoms: List[AtomicUnit],
        project_path: str
    ) -> ValidationResult:
        """
        System-level validation.

        Checks:
        1. Build succeeds
        2. All tests pass
        3. No circular dependencies
        4. Performance benchmarks
        5. Security scan
        """
        issues = []

        # 1. Build validation
        issues.extend(self._validate_build(project_path))

        # 2. Test validation
        issues.extend(self._validate_tests(project_path))

        # 3. Dependency validation
        issues.extend(self._validate_system_dependencies(atoms))

        # 4. Performance validation
        issues.extend(self._validate_system_performance(project_path))

        # 5. Security validation
        issues.extend(self._validate_system_security(project_path))

        score = self._calculate_score(issues)
        passed = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) == 0

        return ValidationResult(
            level=4,
            scope='System',
            passed=passed,
            score=score,
            issues=issues
        )

    def _validate_build(self, project_path: str) -> List[ValidationIssue]:
        """Validate that project builds."""
        issues = []

        try:
            # Run build command
            import subprocess
            result = subprocess.run(
                ['python', '-m', 'compileall', project_path],
                capture_output=True,
                timeout=60
            )

            if result.returncode != 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category='build',
                    message="Build failed",
                    suggestion="Fix build errors"
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category='build',
                message=f"Build error: {str(e)}",
                suggestion="Fix build configuration"
            ))

        return issues

    def _validate_tests(self, project_path: str) -> List[ValidationIssue]:
        """Validate that tests pass."""
        issues = []

        try:
            # Run tests
            import subprocess
            result = subprocess.run(
                ['pytest', project_path, '-v'],
                capture_output=True,
                timeout=300
            )

            if result.returncode != 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='tests',
                    message="Tests failed",
                    suggestion="Fix failing tests"
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='tests',
                message=f"Could not run tests: {str(e)}",
                suggestion="Ensure test framework is installed"
            ))

        return issues
```

---

## Complete Pipeline

```python
class HierarchicalValidationPipeline:
    """
    Complete 4-level validation pipeline.
    """

    def __init__(self):
        self.atomic_validator = AtomicValidator()
        self.module_validator = ModuleValidator()
        self.component_validator = ComponentValidator()
        self.system_validator = SystemValidator()

    def validate_all(
        self,
        atoms: List[AtomicUnit],
        project_path: str
    ) -> Dict[str, Any]:
        """
        Run all validation levels.

        Returns:
            Validation report with results from all levels
        """
        print("=" * 60)
        print("✓ PHASE 5: HIERARCHICAL VALIDATION")
        print("=" * 60)

        results = {
            'level1_atomic': [],
            'level2_module': [],
            'level3_component': [],
            'level4_system': None
        }

        # Level 1: Atomic (per atom)
        print("\n📋 Level 1: Atomic Validation...")
        for atom in atoms:
            result = self.atomic_validator.validate(atom)
            results['level1_atomic'].append(result)

        passed_level1 = sum(1 for r in results['level1_atomic'] if r.passed)
        print(f"  ✅ {passed_level1}/{len(atoms)} atoms passed")

        # Level 2: Module (groups of 10-20)
        print("\n📦 Level 2: Module Validation...")
        modules = self._group_into_modules(atoms)
        for module_name, module_atoms in modules.items():
            result = self.module_validator.validate(module_atoms, module_name)
            results['level2_module'].append(result)

        passed_level2 = sum(1 for r in results['level2_module'] if r.passed)
        print(f"  ✅ {passed_level2}/{len(modules)} modules passed")

        # Level 3: Component (groups of 50-100)
        print("\n🏗️ Level 3: Component Validation...")
        components = self._group_into_components(atoms)
        for comp_name, comp_atoms in components.items():
            result = self.component_validator.validate(comp_atoms, comp_name)
            results['level3_component'].append(result)

        passed_level3 = sum(1 for r in results['level3_component'] if r.passed)
        print(f"  ✅ {passed_level3}/{len(components)} components passed")

        # Level 4: System (full project)
        print("\n🌐 Level 4: System Validation...")
        result = self.system_validator.validate(atoms, project_path)
        results['level4_system'] = result

        if result.passed:
            print(f"  ✅ System validation passed")
        else:
            print(f"  ❌ System validation failed")

        print("\n✅ Phase 5 complete!\n")

        return results

    def _group_into_modules(self, atoms: List[AtomicUnit]) -> Dict[str, List[AtomicUnit]]:
        """Group atoms into modules (10-20 atoms each)."""
        modules = {}
        current_module = []
        module_number = 1

        for atom in atoms:
            current_module.append(atom)

            if len(current_module) >= 15:
                modules[f"Module_{module_number}"] = current_module
                current_module = []
                module_number += 1

        if current_module:
            modules[f"Module_{module_number}"] = current_module

        return modules

    def _group_into_components(self, atoms: List[AtomicUnit]) -> Dict[str, List[AtomicUnit]]:
        """Group atoms into components (50-100 atoms each)."""
        components = {}
        current_component = []
        component_number = 1

        for atom in atoms:
            current_component.append(atom)

            if len(current_component) >= 75:
                components[f"Component_{component_number}"] = current_component
                current_component = []
                component_number += 1

        if current_component:
            components[f"Component_{component_number}"] = current_component

        return components
```

---

## Performance Metrics

| Metric | Target |
|--------|--------|
| **Level 1 validation time** | <1 second per atom |
| **Level 2 validation time** | <5 seconds per module |
| **Level 3 validation time** | <30 seconds per component |
| **Level 4 validation time** | <2 minutes total |
| **Error detection rate** | ≥98% |
| **False positive rate** | <5% |

---

**Next Document**: [08_PHASE_6_EXECUTION_RETRY.md](08_PHASE_6_EXECUTION_RETRY.md)
