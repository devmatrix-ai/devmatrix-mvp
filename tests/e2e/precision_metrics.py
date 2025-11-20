"""
E2E Precision Metrics & Contract Validation
Comprehensive accuracy, precision, recall, and contract testing
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json
from enum import Enum


class ContractViolationType(Enum):
    SCHEMA_MISMATCH = "schema_mismatch"
    TYPE_ERROR = "type_error"
    MISSING_FIELD = "missing_field"
    INVALID_VALUE = "invalid_value"
    CONSTRAINT_VIOLATION = "constraint_violation"


@dataclass
class PrecisionMetrics:
    """E2E Pipeline Precision Metrics"""

    # Overall Pipeline Accuracy
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0

    # Pattern Matching Precision
    patterns_expected: int = 0
    patterns_found: int = 0
    patterns_correct: int = 0  # True positives
    patterns_incorrect: int = 0  # False positives
    patterns_missed: int = 0  # False negatives

    # Classification Metrics
    classifications_total: int = 0
    classifications_correct: int = 0
    classifications_incorrect: int = 0

    # DAG Construction Accuracy
    dag_nodes_expected: int = 0
    dag_nodes_created: int = 0
    dag_edges_expected: int = 0
    dag_edges_created: int = 0
    dag_cycles_detected: int = 0
    dag_cycles_fixed: int = 0

    # Atomization Quality
    atoms_generated: int = 0
    atoms_valid: int = 0
    atoms_invalid: int = 0
    atoms_too_large: int = 0  # >50 LOC
    atoms_too_small: int = 0  # <5 LOC

    # Execution Precision
    atoms_executed: int = 0
    atoms_succeeded: int = 0
    atoms_failed_first_try: int = 0
    atoms_recovered: int = 0
    atoms_permanently_failed: int = 0

    # Validation Metrics
    tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0

    # Contract Violations
    contract_violations: List[Dict[str, Any]] = field(default_factory=list)

    def calculate_accuracy(self) -> float:
        """Overall pipeline accuracy"""
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations

    def calculate_pattern_precision(self) -> float:
        """Precision of pattern matching (TP / (TP + FP))"""
        total_found = self.patterns_correct + self.patterns_incorrect
        if total_found == 0:
            return 0.0
        return self.patterns_correct / total_found

    def calculate_pattern_recall(self) -> float:
        """Recall of pattern matching (TP / (TP + FN))"""
        total_relevant = self.patterns_correct + self.patterns_missed
        if total_relevant == 0:
            return 0.0
        return self.patterns_correct / total_relevant

    def calculate_pattern_f1(self) -> float:
        """F1 score for pattern matching"""
        precision = self.calculate_pattern_precision()
        recall = self.calculate_pattern_recall()
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def calculate_classification_accuracy(self) -> float:
        """Classification accuracy"""
        if self.classifications_total == 0:
            return 0.0
        return self.classifications_correct / self.classifications_total

    def calculate_dag_accuracy(self) -> float:
        """DAG construction accuracy"""
        if self.dag_nodes_expected == 0 and self.dag_edges_expected == 0:
            return 0.0

        nodes_correct = min(self.dag_nodes_created, self.dag_nodes_expected)
        edges_correct = min(self.dag_edges_created, self.dag_edges_expected)

        total_expected = self.dag_nodes_expected + self.dag_edges_expected
        total_correct = nodes_correct + edges_correct

        return total_correct / total_expected if total_expected > 0 else 0.0

    def calculate_atomization_quality(self) -> float:
        """Quality of atomization (valid atoms / total atoms)"""
        if self.atoms_generated == 0:
            return 0.0
        return self.atoms_valid / self.atoms_generated

    def calculate_execution_success_rate(self) -> float:
        """Success rate of atom execution"""
        if self.atoms_executed == 0:
            return 0.0
        return self.atoms_succeeded / self.atoms_executed

    def calculate_recovery_rate(self) -> float:
        """Rate of successful error recovery"""
        if self.atoms_failed_first_try == 0:
            return 0.0
        return self.atoms_recovered / self.atoms_failed_first_try

    def calculate_test_pass_rate(self) -> float:
        """Test pass rate"""
        if self.tests_executed == 0:
            return 0.0
        return self.tests_passed / self.tests_executed

    def calculate_overall_precision(self) -> float:
        """Overall E2E precision score (weighted average)"""
        weights = {
            'accuracy': 0.20,
            'pattern_f1': 0.15,
            'classification': 0.15,
            'dag': 0.10,
            'atomization': 0.10,
            'execution': 0.20,
            'tests': 0.10
        }

        scores = {
            'accuracy': self.calculate_accuracy(),
            'pattern_f1': self.calculate_pattern_f1(),
            'classification': self.calculate_classification_accuracy(),
            'dag': self.calculate_dag_accuracy(),
            'atomization': self.calculate_atomization_quality(),
            'execution': self.calculate_execution_success_rate(),
            'tests': self.calculate_test_pass_rate()
        }

        weighted_sum = sum(scores[k] * weights[k] for k in weights)
        return weighted_sum

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            "overall_accuracy": self.calculate_accuracy(),
            "overall_precision": self.calculate_overall_precision(),

            "pattern_matching": {
                "precision": self.calculate_pattern_precision(),
                "recall": self.calculate_pattern_recall(),
                "f1_score": self.calculate_pattern_f1(),
                "true_positives": self.patterns_correct,
                "false_positives": self.patterns_incorrect,
                "false_negatives": self.patterns_missed
            },

            "classification": {
                "accuracy": self.calculate_classification_accuracy(),
                "correct": self.classifications_correct,
                "incorrect": self.classifications_incorrect,
                "total": self.classifications_total
            },

            "dag_construction": {
                "accuracy": self.calculate_dag_accuracy(),
                "nodes_accuracy": self.dag_nodes_created / self.dag_nodes_expected if self.dag_nodes_expected > 0 else 0.0,
                "edges_accuracy": self.dag_edges_created / self.dag_edges_expected if self.dag_edges_expected > 0 else 0.0,
                "cycles_fixed_rate": self.dag_cycles_fixed / self.dag_cycles_detected if self.dag_cycles_detected > 0 else 1.0
            },

            "atomization": {
                "quality_score": self.calculate_atomization_quality(),
                "valid_rate": self.atoms_valid / self.atoms_generated if self.atoms_generated > 0 else 0.0,
                "invalid_rate": self.atoms_invalid / self.atoms_generated if self.atoms_generated > 0 else 0.0,
                "oversized_rate": self.atoms_too_large / self.atoms_generated if self.atoms_generated > 0 else 0.0
            },

            "execution": {
                "success_rate": self.calculate_execution_success_rate(),
                "recovery_rate": self.calculate_recovery_rate(),
                "first_try_success_rate": (self.atoms_succeeded - self.atoms_recovered) / self.atoms_executed if self.atoms_executed > 0 else 0.0,
                "permanent_failure_rate": self.atoms_permanently_failed / self.atoms_executed if self.atoms_executed > 0 else 0.0
            },

            "validation": {
                "test_pass_rate": self.calculate_test_pass_rate(),
                "tests_passed": self.tests_passed,
                "tests_failed": self.tests_failed,
                "tests_skipped": self.tests_skipped
            },

            "contract_violations": {
                "total": len(self.contract_violations),
                "by_type": self._count_violations_by_type()
            }
        }

    def _count_violations_by_type(self) -> Dict[str, int]:
        """Count contract violations by type"""
        counts = {}
        for violation in self.contract_violations:
            vtype = violation.get("type", "unknown")
            counts[vtype] = counts.get(vtype, 0) + 1
        return counts


@dataclass
class ContractValidator:
    """Validates contracts between pipeline phases"""

    violations: List[Dict[str, Any]] = field(default_factory=list)

    # Phase contracts
    SPEC_INGESTION_CONTRACT = {
        "required_fields": ["spec_content", "requirements", "complexity"],
        "types": {
            "spec_content": str,
            "requirements": list,
            "complexity": float
        },
        "constraints": {
            "complexity": lambda x: 0.0 <= x <= 1.0,
            "requirements": lambda x: len(x) > 0
        }
    }

    REQUIREMENTS_ANALYSIS_CONTRACT = {
        "required_fields": ["functional_reqs", "non_functional_reqs", "patterns_matched", "dependencies"],
        "types": {
            "functional_reqs": list,
            "non_functional_reqs": list,
            "patterns_matched": int,
            "dependencies": list
        },
        "constraints": {
            "patterns_matched": lambda x: x >= 0
        }
    }

    PLANNING_CONTRACT = {
        "required_fields": ["dag", "node_count", "edge_count", "is_acyclic", "waves"],
        "types": {
            "dag": dict,
            "node_count": int,
            "edge_count": int,
            "is_acyclic": bool,
            "waves": int
        },
        "constraints": {
            "node_count": lambda x: x > 0,
            "edge_count": lambda x: x >= 0,
            "is_acyclic": lambda x: x == True,
            "waves": lambda x: x > 0
        }
    }

    ATOMIZATION_CONTRACT = {
        "required_fields": ["atomic_units", "unit_count", "avg_complexity"],
        "types": {
            "atomic_units": list,
            "unit_count": int,
            "avg_complexity": float
        },
        "constraints": {
            "unit_count": lambda x: x > 0,
            "avg_complexity": lambda x: 0.0 <= x <= 1.0
        }
    }

    DAG_CONSTRUCTION_CONTRACT = {
        "required_fields": ["nodes", "edges", "waves", "wave_count"],
        "types": {
            "nodes": list,
            "edges": list,
            "waves": list,
            "wave_count": int
        },
        "constraints": {
            "wave_count": lambda x: x > 0
        }
    }

    EXECUTION_CONTRACT = {
        "required_fields": ["atoms_executed", "atoms_succeeded", "atoms_failed"],
        "types": {
            "atoms_executed": int,
            "atoms_succeeded": int,
            "atoms_failed": int
        },
        "constraints": {
            "atoms_executed": lambda x: x > 0,
            "atoms_succeeded": lambda x: x >= 0,
            "atoms_failed": lambda x: x >= 0
        }
    }

    VALIDATION_CONTRACT = {
        "required_fields": ["tests_run", "tests_passed", "coverage", "quality_score"],
        "types": {
            "tests_run": int,
            "tests_passed": int,
            "coverage": float,
            "quality_score": float
        },
        "constraints": {
            "tests_run": lambda x: x > 0,
            "coverage": lambda x: 0.0 <= x <= 1.0,
            "quality_score": lambda x: 0.0 <= x <= 1.0
        }
    }

    def validate_phase_output(self, phase: str, output: Dict[str, Any]) -> bool:
        """Validate phase output against contract"""
        contract_map = {
            "spec_ingestion": self.SPEC_INGESTION_CONTRACT,
            "requirements_analysis": self.REQUIREMENTS_ANALYSIS_CONTRACT,
            "multi_pass_planning": self.PLANNING_CONTRACT,
            "atomization": self.ATOMIZATION_CONTRACT,
            "dag_construction": self.DAG_CONSTRUCTION_CONTRACT,
            "wave_execution": self.EXECUTION_CONTRACT,
            "validation": self.VALIDATION_CONTRACT
        }

        contract = contract_map.get(phase)
        if not contract:
            return True  # No contract defined

        is_valid = True

        # Check required fields
        for field in contract["required_fields"]:
            if field not in output:
                self.violations.append({
                    "phase": phase,
                    "type": ContractViolationType.MISSING_FIELD.value,
                    "field": field,
                    "message": f"Required field '{field}' missing"
                })
                is_valid = False

        # Check types
        for field, expected_type in contract["types"].items():
            if field in output:
                if not isinstance(output[field], expected_type):
                    self.violations.append({
                        "phase": phase,
                        "type": ContractViolationType.TYPE_ERROR.value,
                        "field": field,
                        "expected": expected_type.__name__,
                        "actual": type(output[field]).__name__,
                        "message": f"Type mismatch for '{field}'"
                    })
                    is_valid = False

        # Check constraints
        if "constraints" in contract:
            for field, constraint_fn in contract["constraints"].items():
                if field in output:
                    try:
                        if not constraint_fn(output[field]):
                            self.violations.append({
                                "phase": phase,
                                "type": ContractViolationType.CONSTRAINT_VIOLATION.value,
                                "field": field,
                                "value": output[field],
                                "message": f"Constraint violation for '{field}'"
                            })
                            is_valid = False
                    except Exception as e:
                        self.violations.append({
                            "phase": phase,
                            "type": ContractViolationType.CONSTRAINT_VIOLATION.value,
                            "field": field,
                            "message": f"Constraint check failed: {str(e)}"
                        })
                        is_valid = False

        return is_valid

    def get_violations_summary(self) -> Dict[str, Any]:
        """Get summary of all contract violations"""
        by_phase = {}
        by_type = {}

        for v in self.violations:
            phase = v["phase"]
            vtype = v["type"]

            by_phase[phase] = by_phase.get(phase, 0) + 1
            by_type[vtype] = by_type.get(vtype, 0) + 1

        return {
            "total_violations": len(self.violations),
            "by_phase": by_phase,
            "by_type": by_type,
            "violations": self.violations
        }

    def print_violations(self):
        """Print all contract violations"""
        if not self.violations:
            print("✅ No contract violations detected")
            return

        print(f"\n⚠️  Contract Violations Detected: {len(self.violations)}")
        print("="*70)

        for i, v in enumerate(self.violations, 1):
            print(f"\n{i}. {v['phase'].upper()}")
            print(f"   Type: {v['type']}")
            print(f"   Field: {v.get('field', 'N/A')}")
            print(f"   Message: {v['message']}")
            if 'expected' in v:
                print(f"   Expected: {v['expected']}, Actual: {v['actual']}")
