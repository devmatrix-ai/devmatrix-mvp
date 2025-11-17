# MasterPlan Validation Rules - Testing Enforcement

**Date**: 2025-11-16
**Author**: DevMatrix Cognitive Architecture Team
**Purpose**: Validation logic to enforce testing task generation in MasterPlans

---

## Overview

Este documento especifica las reglas de validación que deben agregarse al método `_validate_masterplan()` en `masterplan_generator.py` para garantizar que TODOS los MasterPlans generen tareas de testing específicas.

---

## 1. Validation Rule: Minimum Testing Tasks

### Rule Definition

**Rule ID**: `VAL-TEST-001`
**Severity**: 🔴 CRITICAL
**Description**: MasterPlan MUST contain minimum 10% testing tasks (minimum 12 tasks for typical 100-task plan)

### Implementation

```python
def _validate_testing_tasks(self, masterplan_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that MasterPlan contains sufficient testing tasks.

    Args:
        masterplan_data: Parsed MasterPlan JSON

    Returns:
        Tuple[bool, List[str]]: (is_valid, error_messages)
    """
    errors = []
    tasks = masterplan_data.get("tasks", [])
    total_tasks = len(tasks)

    # Count testing tasks by name and target files
    testing_keywords = [
        "test", "testing", "unit test", "integration test",
        "e2e test", "contract test", "pytest"
    ]

    testing_tasks = []
    for task in tasks:
        task_name = task.get("name", "").lower()
        target_files = task.get("target_files", [])

        # Check if task name contains testing keywords
        is_testing_by_name = any(keyword in task_name for keyword in testing_keywords)

        # Check if target files are in test directories
        is_testing_by_path = any(
            "test" in str(file_path).lower()
            for file_path in target_files
        )

        if is_testing_by_name or is_testing_by_path:
            testing_tasks.append(task)

    testing_count = len(testing_tasks)
    testing_percentage = (testing_count / total_tasks * 100) if total_tasks > 0 else 0

    # Validation thresholds
    MIN_TESTING_TASKS = 12
    MIN_TESTING_PERCENTAGE = 10.0

    # Validate minimum count
    if testing_count < MIN_TESTING_TASKS:
        errors.append(
            f"❌ CRITICAL: Only {testing_count} testing tasks found. "
            f"Minimum required: {MIN_TESTING_TASKS} tasks"
        )

    # Validate minimum percentage
    if testing_percentage < MIN_TESTING_PERCENTAGE:
        errors.append(
            f"❌ CRITICAL: Testing tasks are {testing_percentage:.1f}% of total. "
            f"Minimum required: {MIN_TESTING_PERCENTAGE}%"
        )

    is_valid = len(errors) == 0

    if is_valid:
        self.logger.info(
            f"✅ Testing validation passed: {testing_count} tasks ({testing_percentage:.1f}%)"
        )
    else:
        self.logger.error(
            f"❌ Testing validation failed",
            extra={"errors": errors, "testing_count": testing_count}
        )

    return is_valid, errors
```

---

## 2. Validation Rule: Test File Path Structure

### Rule Definition

**Rule ID**: `VAL-TEST-002`
**Severity**: 🟡 IMPORTANT
**Description**: Testing tasks MUST specify target files in proper test directories

### Implementation

```python
def _validate_test_file_paths(self, masterplan_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that testing tasks specify proper test file paths.

    Expected patterns:
    - tests/models/test_*.py (unit tests)
    - tests/api/test_*.py (integration tests)
    - tests/e2e/test_*.py (e2e tests)
    - tests/contracts/test_*.py (contract tests)
    """
    errors = []
    warnings = []
    tasks = masterplan_data.get("tasks", [])

    # Valid test directory patterns
    valid_patterns = [
        r"tests/models/test_.*\.py$",
        r"tests/api/test_.*\.py$",
        r"tests/e2e/test_.*\.py$",
        r"tests/contracts/test_.*\.py$",
        r"__tests__/.*\.test\.(js|ts|jsx|tsx)$",  # JavaScript/TypeScript
    ]

    # Find testing tasks
    testing_tasks = [
        task for task in tasks
        if "test" in task.get("name", "").lower()
    ]

    for task in testing_tasks:
        task_name = task.get("name", "")
        target_files = task.get("target_files", [])

        if not target_files:
            errors.append(
                f"❌ Task '{task_name}' has no target_files specified"
            )
            continue

        # Validate each target file
        for file_path in target_files:
            file_path_str = str(file_path)

            # Check if matches any valid pattern
            is_valid_path = any(
                re.match(pattern, file_path_str)
                for pattern in valid_patterns
            )

            if not is_valid_path:
                warnings.append(
                    f"⚠️ Task '{task_name}' has non-standard test path: {file_path_str}"
                )

    # Warnings don't fail validation, but are logged
    is_valid = len(errors) == 0

    if warnings:
        self.logger.warning(
            f"Test path warnings: {len(warnings)}",
            extra={"warnings": warnings}
        )

    return is_valid, errors
```

---

## 3. Validation Rule: Test Type Coverage

### Rule Definition

**Rule ID**: `VAL-TEST-003`
**Severity**: 🟡 IMPORTANT
**Description**: MasterPlan SHOULD include multiple test types (unit, integration, e2e)

### Implementation

```python
def _validate_test_type_coverage(self, masterplan_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that MasterPlan includes diverse test types.

    Test Type Distribution:
    - Unit tests: 50-60% (6-8 tasks)
    - Integration tests: 25-35% (3-5 tasks)
    - E2E tests: 15-20% (2-3 tasks)
    - Contract tests: 10-15% (1-2 tasks)
    """
    warnings = []
    tasks = masterplan_data.get("tasks", [])

    # Categorize testing tasks by type
    test_types = {
        "unit": [],
        "integration": [],
        "e2e": [],
        "contract": []
    }

    for task in tasks:
        task_name = task.get("name", "").lower()
        target_files = task.get("target_files", [])

        if "unit test" in task_name or any("tests/models/" in str(f) for f in target_files):
            test_types["unit"].append(task)
        elif "integration test" in task_name or any("tests/api/" in str(f) for f in target_files):
            test_types["integration"].append(task)
        elif "e2e test" in task_name or any("tests/e2e/" in str(f) for f in target_files):
            test_types["e2e"].append(task)
        elif "contract test" in task_name or any("tests/contracts/" in str(f) for f in target_files):
            test_types["contract"].append(task)

    # Validate coverage
    total_test_tasks = sum(len(tasks) for tasks in test_types.values())

    if total_test_tasks == 0:
        # This should be caught by VAL-TEST-001, but double-check
        warnings.append("⚠️ No test tasks found with type classification")
        return True, warnings  # Don't fail, just warn

    # Check for missing test types
    if len(test_types["unit"]) == 0:
        warnings.append("⚠️ No unit tests found (tests/models/)")

    if len(test_types["integration"]) == 0:
        warnings.append("⚠️ No integration tests found (tests/api/)")

    if len(test_types["e2e"]) == 0:
        warnings.append("⚠️ No E2E tests found (tests/e2e/)")

    # Log distribution
    self.logger.info(
        "Test type distribution",
        extra={
            "unit_tests": len(test_types["unit"]),
            "integration_tests": len(test_types["integration"]),
            "e2e_tests": len(test_types["e2e"]),
            "contract_tests": len(test_types["contract"])
        }
    )

    # Warnings don't fail validation
    return True, warnings
```

---

## 4. Validation Rule: Test Task Dependencies

### Rule Definition

**Rule ID**: `VAL-TEST-004`
**Severity**: 🟡 IMPORTANT
**Description**: Testing tasks MUST depend on implementation tasks (avoid orphan tests)

### Implementation

```python
def _validate_test_dependencies(self, masterplan_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that testing tasks have proper dependencies on implementation tasks.

    A test task should depend on the task that creates the code being tested.
    """
    warnings = []
    tasks = masterplan_data.get("tasks", [])

    # Build task lookup
    task_lookup = {task["task_number"]: task for task in tasks}

    # Find testing tasks
    testing_tasks = [
        task for task in tasks
        if "test" in task.get("name", "").lower()
    ]

    for test_task in testing_tasks:
        depends_on = test_task.get("depends_on_tasks", [])

        if not depends_on:
            warnings.append(
                f"⚠️ Test task #{test_task['task_number']} '{test_task['name']}' "
                f"has no dependencies (orphan test)"
            )
            continue

        # Validate dependencies are implementation tasks (not other tests)
        for dep_task_num in depends_on:
            dep_task = task_lookup.get(dep_task_num)
            if dep_task and "test" in dep_task.get("name", "").lower():
                warnings.append(
                    f"⚠️ Test task #{test_task['task_number']} depends on another test "
                    f"task #{dep_task_num} (should depend on implementation)"
                )

    # Warnings don't fail validation
    return True, warnings
```

---

## 5. Integration into _validate_masterplan()

### Updated Method

```python
def _validate_masterplan(self, masterplan_data: Dict[str, Any]) -> bool:
    """
    Enhanced validation with testing requirements.

    Validation Hierarchy:
    - 🔴 CRITICAL (MUST): Testing tasks minimum count and percentage
    - 🟡 IMPORTANT (SHOULD): Test file paths, type coverage, dependencies
    """
    all_errors = []
    all_warnings = []

    # Existing validations
    # ... (keep existing validation logic)

    # NEW: Testing task validations

    # 🔴 CRITICAL: Minimum testing tasks
    is_valid, errors = self._validate_testing_tasks(masterplan_data)
    if not is_valid:
        all_errors.extend(errors)

    # 🟡 IMPORTANT: Test file paths
    is_valid, errors = self._validate_test_file_paths(masterplan_data)
    if not is_valid:
        all_errors.extend(errors)
    else:
        all_warnings.extend(errors)  # File path errors are warnings

    # 🟡 IMPORTANT: Test type coverage
    is_valid, warnings = self._validate_test_type_coverage(masterplan_data)
    all_warnings.extend(warnings)

    # 🟡 IMPORTANT: Test dependencies
    is_valid, warnings = self._validate_test_dependencies(masterplan_data)
    all_warnings.extend(warnings)

    # Log summary
    if all_errors:
        self.logger.error(
            f"MasterPlan validation FAILED: {len(all_errors)} errors",
            extra={"errors": all_errors}
        )
        for error in all_errors:
            self.logger.error(error)

    if all_warnings:
        self.logger.warning(
            f"MasterPlan validation warnings: {len(all_warnings)}",
            extra={"warnings": all_warnings}
        )
        for warning in all_warnings:
            self.logger.warning(warning)

    # Fail only on CRITICAL errors
    return len(all_errors) == 0
```

---

## 6. Validation Error Messages

### Error Message Templates

```python
VALIDATION_MESSAGES = {
    "no_testing_tasks": """
❌ CRITICAL VALIDATION ERROR: No testing tasks found in MasterPlan

The MasterPlan must include specific testing tasks that generate test files.

Required:
- Minimum 12 testing tasks (10% of total)
- Unit tests: tests/models/test_*.py
- Integration tests: tests/api/test_*.py
- E2E tests: tests/e2e/test_*.py
- Contract tests: tests/contracts/test_*.py

Example testing task:
{
  "task_number": 95,
  "name": "Generate unit tests for User model",
  "target_files": ["tests/models/test_user.py"],
  "depends_on_tasks": [15]
}

This is a CRITICAL error because:
1. Tests are required for quality validation
2. Precision measurement requires executable tests
3. Cognitive Feedback Loop needs validated patterns
""",

    "insufficient_testing_tasks": """
❌ CRITICAL VALIDATION ERROR: Insufficient testing tasks

Found: {testing_count} testing tasks ({testing_percentage:.1f}%)
Required: Minimum {MIN_TESTING_TASKS} tasks ({MIN_TESTING_PERCENTAGE}% of total)

Missing test types:
{missing_types}

Add more specific testing tasks to meet the minimum requirement.
""",

    "invalid_test_paths": """
⚠️ WARNING: Invalid test file paths detected

The following tasks have non-standard test file paths:
{invalid_paths}

Expected patterns:
- tests/models/test_*.py (unit tests)
- tests/api/test_*.py (integration tests)
- tests/e2e/test_*.py (e2e tests)
- tests/contracts/test_*.py (contract tests)
"""
}
```

---

## 7. Validation Metrics

### Success Criteria

```python
VALIDATION_METRICS = {
    "critical_pass_rate": {
        "target": 1.0,  # 100% - all critical validations must pass
        "description": "All CRITICAL validations (testing tasks minimum)"
    },
    "important_pass_rate": {
        "target": 0.95,  # 95% - most important validations should pass
        "description": "File paths, type coverage, dependencies"
    },
    "warning_rate": {
        "acceptable": 0.1,  # 10% - some warnings are acceptable
        "description": "Non-blocking validation warnings"
    }
}
```

### Validation Report

```python
def _generate_validation_report(
    self,
    masterplan_data: Dict[str, Any],
    errors: List[str],
    warnings: List[str]
) -> Dict[str, Any]:
    """Generate comprehensive validation report."""
    tasks = masterplan_data.get("tasks", [])
    total_tasks = len(tasks)

    # Count testing tasks
    testing_tasks = [
        task for task in tasks
        if "test" in task.get("name", "").lower()
    ]
    testing_count = len(testing_tasks)
    testing_percentage = (testing_count / total_tasks * 100) if total_tasks > 0 else 0

    # Categorize by test type
    test_types = {
        "unit": sum(1 for t in testing_tasks if "unit" in t.get("name", "").lower()),
        "integration": sum(1 for t in testing_tasks if "integration" in t.get("name", "").lower()),
        "e2e": sum(1 for t in testing_tasks if "e2e" in t.get("name", "").lower()),
        "contract": sum(1 for t in testing_tasks if "contract" in t.get("name", "").lower())
    }

    return {
        "validation_status": "PASSED" if len(errors) == 0 else "FAILED",
        "total_tasks": total_tasks,
        "testing_tasks": {
            "count": testing_count,
            "percentage": testing_percentage,
            "types": test_types
        },
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "meets_minimum": testing_count >= 12,
            "meets_percentage": testing_percentage >= 10.0,
            "has_unit_tests": test_types["unit"] > 0,
            "has_integration_tests": test_types["integration"] > 0,
            "has_e2e_tests": test_types["e2e"] > 0
        }
    }
```

---

## 8. Testing the Validation

### Unit Test for Validation Logic

```python
def test_validate_testing_tasks_success():
    """Test validation passes with sufficient testing tasks."""
    masterplan_data = {
        "tasks": [
            # ... 88 implementation tasks ...
            {
                "task_number": 89,
                "name": "Generate unit tests for User model",
                "target_files": ["tests/models/test_user.py"],
                "depends_on_tasks": [15]
            },
            {
                "task_number": 90,
                "name": "Generate unit tests for Product model",
                "target_files": ["tests/models/test_product.py"],
                "depends_on_tasks": [20]
            },
            # ... 10 more testing tasks (total 12) ...
        ]
    }

    validator = MasterPlanGenerator()
    is_valid, errors = validator._validate_testing_tasks(masterplan_data)

    assert is_valid == True
    assert len(errors) == 0


def test_validate_testing_tasks_failure():
    """Test validation fails with insufficient testing tasks."""
    masterplan_data = {
        "tasks": [
            # ... 100 implementation tasks, 0 testing tasks ...
        ]
    }

    validator = MasterPlanGenerator()
    is_valid, errors = validator._validate_testing_tasks(masterplan_data)

    assert is_valid == False
    assert len(errors) > 0
    assert "CRITICAL" in errors[0]
```

---

## 9. Migration Strategy

### Phase 1: Add Validation Logic
1. Add new validation methods to `masterplan_generator.py`
2. Update `_validate_masterplan()` to call new validators
3. Add validation error messages

### Phase 2: Test Validation
1. Create unit tests for validation logic
2. Test with historical MasterPlans (should fail)
3. Test with manually created valid MasterPlans (should pass)

### Phase 3: Deploy with Improved Prompt
1. Deploy improved MASTERPLAN_SYSTEM_PROMPT (from masterplan-testing-improvement.md)
2. Enable validation enforcement
3. Monitor first 5 MasterPlans

### Phase 4: Quality Monitoring
1. Track validation pass rate
2. Analyze validation failures
3. Refine validation thresholds if needed

---

## 10. Expected Impact

### Before Implementation
```python
validation_results_before = {
    "testing_tasks_generated": 0,
    "validation_would_fail": True,
    "error_message": "❌ CRITICAL: 0 testing tasks found. Minimum required: 12"
}
```

### After Implementation
```python
validation_results_after = {
    "testing_tasks_generated": 15,  # 12-18 range
    "validation_passes": True,
    "test_type_distribution": {
        "unit": 8,
        "integration": 4,
        "e2e": 2,
        "contract": 1
    },
    "validation_report": {
        "status": "✅ PASSED",
        "testing_percentage": 15.0,
        "meets_all_criteria": True
    }
}
```

---

**Next Steps**:
1. Implement validation methods in `masterplan_generator.py`
2. Create unit tests for validation logic
3. Deploy with improved MASTERPLAN_SYSTEM_PROMPT
4. Monitor validation results for first 10 MasterPlans
