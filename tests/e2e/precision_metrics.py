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

    # Execution Order Validation (Task Group 8)
    execution_order_score: float = 1.0  # 0.0-1.0 (1.0 = no violations)

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


def validate_classification(
    actual: Dict[str, Any],
    expected: Dict[str, Any]
) -> bool:
    """
    Validate if requirement classification matches ground truth

    Task Group 1.3: Classification validator method from spec.md lines 175-196

    Args:
        actual: {domain: str, risk: str, ...} - Actual classification from RequirementsClassifier
        expected: {domain: str, risk: str} - Expected classification from ground truth

    Returns:
        True if domain and risk match, False otherwise
        Returns True if no ground truth is available (graceful handling)

    Examples:
        >>> validate_classification(
        ...     {"domain": "crud", "risk": "low"},
        ...     {"domain": "crud", "risk": "low"}
        ... )
        True

        >>> validate_classification(
        ...     {"domain": "workflow", "risk": "high"},
        ...     {"domain": "crud", "risk": "low"}
        ... )
        False

        >>> validate_classification(
        ...     {"domain": "crud", "risk": "low"},
        ...     None
        ... )
        True
    """
    if not expected:
        return True  # No ground truth = assume correct

    # Get domain and risk from both dicts
    actual_domain = actual.get('domain')
    expected_domain = expected.get('domain')
    actual_risk = actual.get('risk')
    expected_risk = expected.get('risk')

    # Both must match
    return (
        actual_domain == expected_domain and
        actual_risk == expected_risk
    )


def load_classification_ground_truth(spec_path: str) -> Dict[str, Dict[str, str]]:
    """
    Load classification ground truth from spec file

    Task Group 1.4: Helper to load ground truth from spec metadata

    Parses the "Classification Ground Truth" section in the spec file
    and extracts domain/risk labels for each requirement.

    Args:
        spec_path: Path to specification file

    Returns:
        Dictionary mapping requirement IDs to {domain, risk} dicts
        Example: {"F1_create_product": {"domain": "crud", "risk": "low"}}
        Returns empty dict if no ground truth section found

    Example spec format:
        ## Classification Ground Truth

        **F1_create_product**:
          - domain: crud
          - risk: low
    """
    import re
    from pathlib import Path

    ground_truth = {}

    try:
        spec_path_obj = Path(spec_path)
        if not spec_path_obj.exists():
            return ground_truth

        with open(spec_path_obj, 'r') as f:
            content = f.read()

        # Find Classification Ground Truth section
        if "## Classification Ground Truth" not in content:
            return ground_truth

        # Split into lines and parse
        lines = content.split('\n')
        in_ground_truth_section = False
        current_req_id = None

        for line in lines:
            # Check for start of ground truth section
            if "## Classification Ground Truth" in line:
                in_ground_truth_section = True
                continue

            # Check for end of section (next ## header)
            if in_ground_truth_section and line.startswith("## ") and "Classification Ground Truth" not in line:
                break

            if not in_ground_truth_section:
                continue

            # Parse requirement ID (e.g., **F1_create_product**:)
            req_match = re.match(r'\*\*([A-Z0-9_]+)\*\*:', line)
            if req_match:
                current_req_id = req_match.group(1)
                ground_truth[current_req_id] = {}
                continue

            # Parse domain line (e.g., "  - domain: crud")
            if current_req_id and "- domain:" in line:
                domain = line.split("domain:")[1].strip()
                ground_truth[current_req_id]["domain"] = domain

            # Parse risk line (e.g., "  - risk: low")
            if current_req_id and "- risk:" in line:
                risk = line.split("risk:")[1].strip()
                ground_truth[current_req_id]["risk"] = risk

    except Exception as e:
        print(f"Warning: Failed to load classification ground truth: {e}")

    return ground_truth


def load_dag_ground_truth(spec_path: str) -> Dict[str, Any]:
    """
    Load DAG ground truth from spec file

    Task Group 6.3: DAG ground truth parser

    Parses the "Expected Dependency Graph (Ground Truth)" section in the spec file
    and extracts nodes and edges.

    Args:
        spec_path: Path to specification file

    Returns:
        Dictionary with:
        {
            "nodes": int,              # Expected number of nodes
            "node_list": List[str],    # List of node names
            "edges": int,              # Expected number of edges
            "edge_list": List[tuple]   # List of (from, to) edge tuples
        }
        Returns empty dict if no ground truth section found

    Example spec format:
        ## Expected Dependency Graph (Ground Truth)

        ### Nodes (10 expected)

        ```yaml
        nodes: 10
        node_list:
          - create_product
          - list_products
        ```

        ### Edges (12 explicit dependencies)

        ```yaml
        edges: 12
        edge_list:
          - from: create_customer
            to: create_cart
            reason: "Cart requires customer to exist"
        ```
    """
    import re
    from pathlib import Path

    ground_truth = {
        "nodes": 0,
        "node_list": [],
        "edges": 0,
        "edge_list": []
    }

    try:
        spec_path_obj = Path(spec_path)
        if not spec_path_obj.exists():
            return ground_truth

        with open(spec_path_obj, 'r') as f:
            content = f.read()

        # Find DAG Ground Truth section
        if "## Expected Dependency Graph (Ground Truth)" not in content:
            return ground_truth

        # Split into lines and parse
        lines = content.split('\n')
        in_ground_truth_section = False
        in_nodes_yaml = False
        in_edges_yaml = False
        current_edge_from = None

        for i, line in enumerate(lines):
            # Check for start of ground truth section
            if "## Expected Dependency Graph (Ground Truth)" in line:
                in_ground_truth_section = True
                continue

            # Check for end of section (next ## header that's not part of ground truth)
            if in_ground_truth_section and line.startswith("## ") and "Expected Dependency Graph" not in line:
                break

            if not in_ground_truth_section:
                continue

            # Parse nodes section
            if "### Nodes" in line:
                # Extract node count from header (e.g., "### Nodes (10 expected)")
                node_match = re.search(r'\((\d+)\s+expected\)', line)
                if node_match:
                    ground_truth["nodes"] = int(node_match.group(1))
                continue

            # Detect start of nodes YAML block (check previous lines for context)
            if line.strip() == "```yaml":
                # Look back to see if we're in nodes section
                lookback = '\n'.join(lines[max(0, i-10):i])
                if "### Nodes" in lookback and "### Edges" not in lookback:
                    in_nodes_yaml = True
                    in_edges_yaml = False
                elif "### Edges" in lookback:
                    in_edges_yaml = True
                    in_nodes_yaml = False
                continue

            # Parse nodes YAML content
            if in_nodes_yaml:
                if line.strip() == "```":
                    in_nodes_yaml = False
                    continue

                # Parse "nodes: 10"
                if line.strip().startswith("nodes:"):
                    node_count = line.split(":")[1].strip()
                    ground_truth["nodes"] = int(node_count)

                # Parse node list items (e.g., "  - create_product")
                if line.strip().startswith("- "):
                    node_name = line.strip()[2:].split("#")[0].strip()  # Remove "- " and comments
                    if node_name and not node_name.startswith("from") and not node_name.startswith("to"):
                        ground_truth["node_list"].append(node_name)

            # Parse edges section
            if "### Edges" in line:
                # Extract edge count from header (e.g., "### Edges (12 explicit dependencies)")
                edge_match = re.search(r'\((\d+)\s+explicit', line)
                if edge_match:
                    ground_truth["edges"] = int(edge_match.group(1))
                continue

            # Parse edges YAML content
            if in_edges_yaml:
                if line.strip() == "```":
                    in_edges_yaml = False
                    continue

                # Parse "edges: 12"
                if line.strip().startswith("edges:"):
                    edge_count = line.split(":")[1].strip()
                    ground_truth["edges"] = int(edge_count)

                # Parse edge "from" field
                if line.strip().startswith("- from:"):
                    from_node = line.split("from:")[1].strip()
                    current_edge_from = from_node

                # Parse edge "to" field
                if line.strip().startswith("to:") and current_edge_from:
                    to_node = line.split("to:")[1].strip()
                    ground_truth["edge_list"].append((current_edge_from, to_node))
                    current_edge_from = None  # Reset for next edge

        # Validate ground truth format
        if ground_truth["nodes"] > 0 and len(ground_truth["node_list"]) != ground_truth["nodes"]:
            print(f"Warning: DAG ground truth nodes mismatch - expected {ground_truth['nodes']}, got {len(ground_truth['node_list'])}")

        if ground_truth["edges"] > 0 and len(ground_truth["edge_list"]) != ground_truth["edges"]:
            print(f"Warning: DAG ground truth edges mismatch - expected {ground_truth['edges']}, got {len(ground_truth['edge_list'])}")

    except Exception as e:
        print(f"Warning: Failed to load DAG ground truth: {e}")

    return ground_truth
