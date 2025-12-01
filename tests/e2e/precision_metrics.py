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


class ComplianceMode(Enum):
    """Compliance validation modes for IR checking."""
    SEMANTIC = "semantic"      # High-level spec compliance (entities, endpoints, validations)
    IR_STRICT = "ir_strict"    # Exact IR matching (technical validation)
    IR_RELAXED = "ir_relaxed"  # Fuzzy/semantic IR matching (dashboard/investors)


@dataclass
class IRComplianceMetrics:
    """
    IR Compliance metrics with STRICT/RELAXED dual-mode support.

    Provides three compliance perspectives:
    - semantic: High-level spec compliance (100% = all entities/endpoints/validations present)
    - ir_strict: Exact IR matching (for technical validation, CI/CD)
    - ir_relaxed: Semantic IR matching (for dashboard, investors)
    """

    # Semantic Compliance (existing spec-level validation)
    semantic_entities: float = 0.0      # % entities present
    semantic_endpoints: float = 0.0     # % endpoints working
    semantic_validations: float = 0.0   # % validations applied
    semantic_overall: float = 0.0       # Weighted average

    # IR Compliance - STRICT (exact matching)
    strict_entities: float = 0.0        # Exact entity name match
    strict_flows: float = 0.0           # Exact method name match
    strict_constraints: float = 0.0     # Exact constraint match
    strict_overall: float = 0.0         # Average

    # IR Compliance - RELAXED (semantic matching)
    relaxed_entities: float = 0.0       # Fuzzy entity matching
    relaxed_flows: float = 0.0          # Semantic flow matching
    relaxed_constraints: float = 0.0    # Semantic constraint matching
    relaxed_overall: float = 0.0        # Average

    # Match details for trazabilidad
    entity_match_details: Dict[str, Any] = field(default_factory=dict)
    flow_match_details: Dict[str, Any] = field(default_factory=dict)
    constraint_match_details: Dict[str, Any] = field(default_factory=dict)

    def calculate_semantic_overall(self) -> float:
        """Calculate weighted semantic compliance."""
        weights = {"entities": 0.4, "endpoints": 0.4, "validations": 0.2}
        self.semantic_overall = (
            self.semantic_entities * weights["entities"] +
            self.semantic_endpoints * weights["endpoints"] +
            self.semantic_validations * weights["validations"]
        )
        return self.semantic_overall

    def calculate_strict_overall(self) -> float:
        """Calculate average STRICT IR compliance."""
        scores = [self.strict_entities, self.strict_flows, self.strict_constraints]
        non_zero = [s for s in scores if s > 0] or scores
        self.strict_overall = sum(non_zero) / len(non_zero) if non_zero else 0.0
        return self.strict_overall

    def calculate_relaxed_overall(self) -> float:
        """Calculate average RELAXED IR compliance."""
        scores = [self.relaxed_entities, self.relaxed_flows, self.relaxed_constraints]
        non_zero = [s for s in scores if s > 0] or scores
        self.relaxed_overall = sum(non_zero) / len(non_zero) if non_zero else 0.0
        return self.relaxed_overall

    def get_comparison(self) -> Dict[str, Any]:
        """
        Get comparison between different compliance modes.

        Returns metrics summary for dashboard display.
        """
        self.calculate_semantic_overall()
        self.calculate_strict_overall()
        self.calculate_relaxed_overall()

        return {
            "semantic_compliance": {
                "overall": round(self.semantic_overall, 1),
                "entities": round(self.semantic_entities, 1),
                "endpoints": round(self.semantic_endpoints, 1),
                "validations": round(self.semantic_validations, 1)
            },
            "ir_compliance": {
                "strict": {
                    "overall": round(self.strict_overall, 1),
                    "entities": round(self.strict_entities, 1),
                    "flows": round(self.strict_flows, 1),
                    "constraints": round(self.strict_constraints, 1)
                },
                "relaxed": {
                    "overall": round(self.relaxed_overall, 1),
                    "entities": round(self.relaxed_entities, 1),
                    "flows": round(self.relaxed_flows, 1),
                    "constraints": round(self.relaxed_constraints, 1)
                }
            },
            "compliance_comparison": {
                "semantic_vs_ir_relaxed_delta": round(
                    self.semantic_overall - self.relaxed_overall, 1
                ),
                "strict_vs_relaxed_delta": round(
                    self.relaxed_overall - self.strict_overall, 1
                ),
                "explanation": self._generate_gap_explanation()
            }
        }

    def _generate_gap_explanation(self) -> str:
        """Generate explanation for compliance gaps."""
        explanations = []

        # Semantic vs IR_RELAXED gap
        semantic_gap = abs(self.semantic_overall - self.relaxed_overall)
        if semantic_gap > 5:
            explanations.append(
                f"Semantic-IR gap ({semantic_gap:.0f}%): "
                "Naming conventions or flow structure differences"
            )

        # STRICT vs RELAXED gap
        strict_gap = self.relaxed_overall - self.strict_overall
        if strict_gap > 10:
            explanations.append(
                f"STRICT-RELAXED gap ({strict_gap:.0f}%): "
                "Entity suffixes, action synonyms, or constraint equivalences"
            )

        if not explanations:
            return "All compliance metrics aligned"

        return "; ".join(explanations)

    def format_dashboard(self) -> str:
        """
        Format compliance metrics for terminal dashboard display.

        Returns:
            Formatted string for terminal output
        """
        self.calculate_semantic_overall()
        self.calculate_strict_overall()
        self.calculate_relaxed_overall()

        # Status indicators
        def status(score: float) -> str:
            if score >= 90: return "✅"
            if score >= 70: return "⚠️"
            return "❌"

        lines = [
            "┌─────────────────────────────────────────────────┐",
            "│          Compliance Metrics Dashboard           │",
            "├─────────────────────────────────────────────────┤",
            f"│ Semantic Compliance:     {self.semantic_overall:5.1f}% {status(self.semantic_overall)}              │",
            f"│ IR Compliance (Relaxed): {self.relaxed_overall:5.1f}% {status(self.relaxed_overall)}              │",
            f"│ IR Compliance (Strict):  {self.strict_overall:5.1f}% {status(self.strict_overall)} (dev-only)   │",
            "├─────────────────────────────────────────────────┤",
            f"│ Entities:  {self._format_triple(self.semantic_entities, self.relaxed_entities, self.strict_entities)}│",
            f"│ Flows:     {self._format_triple(self.semantic_endpoints, self.relaxed_flows, self.strict_flows)}│",
            f"│ Constraints:{self._format_triple(self.semantic_validations, self.relaxed_constraints, self.strict_constraints)}│",
            "└─────────────────────────────────────────────────┘"
        ]
        return "\n".join(lines)

    def _format_triple(self, sem: float, rel: float, strict: float) -> str:
        """Format triple of scores: semantic/relaxed/strict."""
        return f"sem={sem:3.0f}% rel={rel:3.0f}% str={strict:3.0f}%    "

    @classmethod
    def from_ir_reports(
        cls,
        strict_reports: Dict[str, Any],
        relaxed_reports: Dict[str, Any],
        semantic_scores: Optional[Dict[str, float]] = None
    ) -> "IRComplianceMetrics":
        """
        Create IRComplianceMetrics from IR compliance checker reports.

        Args:
            strict_reports: Reports from check_full_ir_compliance(mode=STRICT)
            relaxed_reports: Reports from check_full_ir_compliance(mode=RELAXED)
            semantic_scores: Optional pre-calculated semantic compliance scores
                {"entities": 100.0, "endpoints": 100.0, "validations": 100.0}
        """
        metrics = cls()

        # Extract STRICT scores
        if "entities" in strict_reports:
            metrics.strict_entities = strict_reports["entities"].compliance_score
            metrics.entity_match_details["strict"] = strict_reports["entities"].details
        if "flows" in strict_reports:
            metrics.strict_flows = strict_reports["flows"].compliance_score
            metrics.flow_match_details["strict"] = strict_reports["flows"].details
        if "constraints" in strict_reports:
            metrics.strict_constraints = strict_reports["constraints"].compliance_score
            metrics.constraint_match_details["strict"] = strict_reports["constraints"].details

        # Extract RELAXED scores
        if "entities" in relaxed_reports:
            metrics.relaxed_entities = relaxed_reports["entities"].compliance_score
            metrics.entity_match_details["relaxed"] = relaxed_reports["entities"].details
        if "flows" in relaxed_reports:
            metrics.relaxed_flows = relaxed_reports["flows"].compliance_score
            metrics.flow_match_details["relaxed"] = relaxed_reports["flows"].details
        if "constraints" in relaxed_reports:
            metrics.relaxed_constraints = relaxed_reports["constraints"].compliance_score
            metrics.constraint_match_details["relaxed"] = relaxed_reports["constraints"].details

        # Set semantic scores (from existing validator or default to relaxed)
        if semantic_scores:
            metrics.semantic_entities = semantic_scores.get("entities", metrics.relaxed_entities)
            metrics.semantic_endpoints = semantic_scores.get("endpoints", metrics.relaxed_flows)
            metrics.semantic_validations = semantic_scores.get("validations", metrics.relaxed_constraints)
        else:
            # Default: use relaxed as proxy for semantic
            metrics.semantic_entities = metrics.relaxed_entities
            metrics.semantic_endpoints = metrics.relaxed_flows
            metrics.semantic_validations = metrics.relaxed_constraints

        # Calculate overall scores
        metrics.calculate_semantic_overall()
        metrics.calculate_strict_overall()
        metrics.calculate_relaxed_overall()

        return metrics


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
    """
    Validates contracts between pipeline phases.

    Contract Philosophy (Bug #172 Redesign):
    =========================================

    Contracts have 3 levels:
    1. STRUCTURAL - Fields exist with correct types (always enforced)
    2. SEMANTIC - Values make sense (warnings, not failures)
    3. QUALITY - Meets quality thresholds (gating for production)

    Each phase outputs data that becomes input for the next phase.
    Contracts ensure the "handoff" between phases is valid.
    """

    violations: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    # Quality thresholds (can be adjusted per environment)
    QUALITY_THRESHOLDS = {
        "min_requirements": 3,           # At least 3 requirements for real spec
        "min_functional_reqs": 1,        # At least 1 functional requirement
        "min_entities": 1,               # At least 1 entity
        "min_endpoints": 1,              # At least 1 endpoint
        "max_complexity": 1.0,           # Complexity 0-1
        "min_success_rate": 0.50,        # 50% minimum success rate
        "target_success_rate": 0.80,     # 80% target for warnings
        "min_smoke_pass_rate": 0.70,     # 70% smoke test minimum
        "target_smoke_pass_rate": 0.95,  # 95% target
    }

    # ==========================================================================
    # PHASE 1: Spec Ingestion
    # Input: Raw spec file (markdown, yaml, json)
    # Output: Parsed content, extracted requirements, complexity score
    # ==========================================================================
    SPEC_INGESTION_CONTRACT = {
        "required_fields": ["spec_content", "requirements", "complexity"],
        "types": {
            "spec_content": str,
            "requirements": list,
            "complexity": float
        },
        "structural": {
            "spec_content": lambda x: len(x) > 0,  # Non-empty content
        },
        "semantic": {
            # Semantic checks - generate warnings, not failures
            "complexity": lambda x: x > 0.0,  # 0.0 suggests parsing issue
            "requirements": lambda x: len(x) >= 3,  # Real specs have multiple reqs
        },
        "quality": {
            # Quality gates - can block pipeline if strict mode
            "requirements": lambda x: any(
                hasattr(r, 'domain') or isinstance(r, dict) and 'domain' in r
                for r in x[:5] if x  # At least some reqs have domains
            ) if x else False,
        }
    }

    # ==========================================================================
    # PHASE 2: Requirements Analysis
    # Input: Raw requirements from spec
    # Output: Classified requirements (functional, non-functional, patterns)
    # ==========================================================================
    REQUIREMENTS_ANALYSIS_CONTRACT = {
        "required_fields": ["functional_reqs", "non_functional_reqs", "patterns_matched", "dependencies"],
        "types": {
            "functional_reqs": list,
            "non_functional_reqs": list,
            "patterns_matched": int,
            "dependencies": list
        },
        "structural": {
            "functional_reqs": lambda x: isinstance(x, list),
        },
        "semantic": {
            "functional_reqs": lambda x: len(x) >= 1,  # At least 1 functional req
            "patterns_matched": lambda x: x >= 0,
        },
        "quality": {
            # Quality: Good classification should match patterns
            "patterns_matched": lambda x: x >= 1,  # Should match at least 1 pattern
        }
    }

    # ==========================================================================
    # PHASE 3: Multi-Pass Planning (DAG)
    # Input: Classified requirements
    # Output: Dependency graph (DAG) with execution waves
    # ==========================================================================
    PLANNING_CONTRACT = {
        "required_fields": ["dag", "node_count", "edge_count", "is_acyclic", "waves"],
        "types": {
            "dag": dict,
            "node_count": int,
            "edge_count": int,
            "is_acyclic": bool,
            "waves": int
        },
        "structural": {
            "node_count": lambda x: x > 0,
            "is_acyclic": lambda x: x == True,  # MUST be acyclic
        },
        "semantic": {
            "waves": lambda x: x >= 1,  # At least 1 wave
            "edge_count": lambda x: x >= 0,  # Can have 0 edges (independent nodes)
        },
        "quality": {
            # Quality: Edges should exist for connected requirements
            # Ratio: edges/nodes - too few edges = poor dependency analysis
            # Skip if node_count is 0 (will fail structural anyway)
        }
    }

    # ==========================================================================
    # PHASE 4: Atomization
    # Input: DAG with requirements
    # Output: Atomic execution units
    # ==========================================================================
    ATOMIZATION_CONTRACT = {
        "required_fields": ["atomic_units", "unit_count", "avg_complexity"],
        "types": {
            "atomic_units": list,
            "unit_count": int,
            "avg_complexity": float
        },
        "structural": {
            "unit_count": lambda x: x > 0,
            "avg_complexity": lambda x: 0.0 <= x <= 1.0,
        },
        "semantic": {
            "atomic_units": lambda x: all(
                isinstance(u, dict) and 'id' in u for u in x[:5]
            ) if x else True,  # Units should have IDs
        },
        "quality": {}
    }

    # ==========================================================================
    # PHASE 5: DAG Construction
    # Input: Atomic units
    # Output: Execution-ready DAG with waves
    # ==========================================================================
    DAG_CONSTRUCTION_CONTRACT = {
        "required_fields": ["nodes", "edges", "waves", "wave_count"],
        "types": {
            "nodes": list,
            "edges": list,
            "waves": list,
            "wave_count": int
        },
        "structural": {
            "wave_count": lambda x: x > 0,
        },
        "semantic": {
            "nodes": lambda x: len(x) > 0,
        },
        "quality": {}
    }

    # ==========================================================================
    # PHASE 6: Wave Execution (Code Generation)
    # Input: DAG with waves
    # Output: Generated code files
    # ==========================================================================
    EXECUTION_CONTRACT = {
        "required_fields": ["atoms_executed", "atoms_succeeded", "atoms_failed"],
        "types": {
            "atoms_executed": int,
            "atoms_succeeded": int,
            "atoms_failed": int
        },
        "structural": {
            "atoms_executed": lambda x: x > 0,
        },
        "semantic": {
            "atoms_succeeded": lambda x: x >= 0,
            "atoms_failed": lambda x: x >= 0,
        },
        "quality": {
            # Success rate should be high
            # This is checked separately with thresholds
        }
    }

    # ==========================================================================
    # PHASE 7+: Validation (Smoke Tests)
    # Input: Generated code
    # Output: Test results, coverage, quality score
    # ==========================================================================
    VALIDATION_CONTRACT = {
        "required_fields": ["tests_run", "tests_passed", "coverage", "quality_score"],
        "types": {
            "tests_run": int,
            "tests_passed": int,
            "coverage": float,
            "quality_score": float
        },
        "structural": {
            "coverage": lambda x: 0.0 <= x <= 1.0,
            "quality_score": lambda x: 0.0 <= x <= 1.0,
        },
        "semantic": {
            "tests_run": lambda x: x >= 0,  # Can be 0 if tests not generated
        },
        "quality": {
            # Pass rate is the key quality metric
            # Checked separately: tests_passed / tests_run >= threshold
        }
    }

    # ==========================================================================
    # NEW: Smoke Test Contract (the one that really matters for MVP)
    # ==========================================================================
    SMOKE_TEST_CONTRACT = {
        "required_fields": ["total_scenarios", "passed", "failed", "pass_rate"],
        "types": {
            "total_scenarios": int,
            "passed": int,
            "failed": int,
            "pass_rate": float
        },
        "structural": {
            "total_scenarios": lambda x: x > 0,
            "pass_rate": lambda x: 0.0 <= x <= 1.0,
        },
        "semantic": {
            # passed + failed should equal total
            # (checked in validate method)
        },
        "quality": {
            "pass_rate": lambda x: x >= 0.70,  # 70% minimum
        },
        "excellent": {
            "pass_rate": lambda x: x >= 0.95,  # 95% = excellent
        }
    }

    def validate_phase_output(self, phase: str, output: Dict[str, Any]) -> bool:
        """
        Validate phase output against contract using 3-tier system.

        Tiers:
        - STRUCTURAL: Required fields, types (hard fail)
        - SEMANTIC: Values make sense (warnings only)
        - QUALITY: Quality thresholds (gating)

        Returns True only if STRUCTURAL passes.
        SEMANTIC failures are logged as warnings.
        QUALITY failures are logged but don't block.
        """
        contract_map = {
            "spec_ingestion": self.SPEC_INGESTION_CONTRACT,
            "requirements_analysis": self.REQUIREMENTS_ANALYSIS_CONTRACT,
            "multi_pass_planning": self.PLANNING_CONTRACT,
            "atomization": self.ATOMIZATION_CONTRACT,
            "dag_construction": self.DAG_CONSTRUCTION_CONTRACT,
            "wave_execution": self.EXECUTION_CONTRACT,
            "validation": self.VALIDATION_CONTRACT,
            "smoke_test": self.SMOKE_TEST_CONTRACT
        }

        contract = contract_map.get(phase)
        if not contract:
            return True  # No contract defined

        structural_ok = True

        # TIER 1: STRUCTURAL - Required fields exist
        for field in contract["required_fields"]:
            if field not in output:
                self.violations.append({
                    "phase": phase,
                    "tier": "STRUCTURAL",
                    "type": ContractViolationType.MISSING_FIELD.value,
                    "field": field,
                    "message": f"Required field '{field}' missing"
                })
                structural_ok = False

        # TIER 1: STRUCTURAL - Type checks
        for field, expected_type in contract["types"].items():
            if field in output:
                if not isinstance(output[field], expected_type):
                    self.violations.append({
                        "phase": phase,
                        "tier": "STRUCTURAL",
                        "type": ContractViolationType.TYPE_ERROR.value,
                        "field": field,
                        "expected": expected_type.__name__,
                        "actual": type(output[field]).__name__,
                        "message": f"Type mismatch for '{field}'"
                    })
                    structural_ok = False

        # TIER 1: STRUCTURAL - Hard constraints
        if "structural" in contract:
            for field, constraint_fn in contract["structural"].items():
                if field in output:
                    try:
                        if not constraint_fn(output[field]):
                            self.violations.append({
                                "phase": phase,
                                "tier": "STRUCTURAL",
                                "type": ContractViolationType.CONSTRAINT_VIOLATION.value,
                                "field": field,
                                "value": str(output[field])[:100],
                                "message": f"Structural constraint failed for '{field}'"
                            })
                            structural_ok = False
                    except Exception as e:
                        self.violations.append({
                            "phase": phase,
                            "tier": "STRUCTURAL",
                            "type": ContractViolationType.CONSTRAINT_VIOLATION.value,
                            "field": field,
                            "message": f"Structural check error: {str(e)}"
                        })
                        structural_ok = False

        # TIER 2: SEMANTIC - Warnings only (don't block)
        if "semantic" in contract:
            for field, constraint_fn in contract["semantic"].items():
                if field in output:
                    try:
                        if not constraint_fn(output[field]):
                            self.warnings.append({
                                "phase": phase,
                                "tier": "SEMANTIC",
                                "type": "semantic_warning",
                                "field": field,
                                "value": str(output[field])[:100],
                                "message": f"Semantic warning for '{field}'"
                            })
                    except Exception:
                        pass  # Semantic checks are best-effort

        # TIER 3: QUALITY - Gating (logged but doesn't block structural)
        if "quality" in contract:
            for field, constraint_fn in contract["quality"].items():
                if field in output:
                    try:
                        if not constraint_fn(output[field]):
                            self.warnings.append({
                                "phase": phase,
                                "tier": "QUALITY",
                                "type": "quality_gate_failed",
                                "field": field,
                                "value": str(output[field])[:100],
                                "message": f"Quality gate failed for '{field}'"
                            })
                    except Exception:
                        pass

        # Legacy: Check old-style constraints for backward compatibility
        if "constraints" in contract:
            for field, constraint_fn in contract["constraints"].items():
                if field in output:
                    try:
                        if not constraint_fn(output[field]):
                            self.warnings.append({
                                "phase": phase,
                                "tier": "LEGACY",
                                "type": "constraint_warning",
                                "field": field,
                                "value": str(output[field])[:100],
                                "message": f"Legacy constraint warning for '{field}'"
                            })
                    except Exception:
                        pass

        return structural_ok

    def validate_smoke_test_against_ir(
        self,
        smoke_result: Dict[str, Any],
        application_ir: Any
    ) -> Dict[str, Any]:
        """
        Validate smoke test results against ApplicationIR (the source of truth).

        Args:
            smoke_result: Dict with keys: total_scenarios, passed, failed, pass_rate, violations
            application_ir: ApplicationIR instance with api_model.endpoints

        Returns:
            ValidationResult dict with tiers, passed, warnings, etc.
        """
        result = {
            "phase": "smoke_test",
            "structural_passed": True,
            "semantic_passed": True,
            "quality_passed": True,
            "violations": [],
            "warnings": [],
            "coverage": 0.0,
            "pass_rate": 0.0
        }

        # Extract IR endpoints (source of truth)
        ir_endpoints = set()
        if application_ir and hasattr(application_ir, 'api_model') and application_ir.api_model:
            for ep in application_ir.api_model.endpoints:
                method = ep.method.value if hasattr(ep.method, 'value') else str(ep.method)
                ir_endpoints.add(f"{method} {ep.path}")

        # Extract tested endpoints from smoke result
        tested_endpoints = set()
        if 'tested_endpoints' in smoke_result:
            tested_endpoints = set(smoke_result['tested_endpoints'])
        elif 'violations' in smoke_result:
            # Infer from violations + passed count
            for v in smoke_result['violations']:
                ep = v.get('endpoint', '')
                method = v.get('method', 'GET')
                if ep:
                    tested_endpoints.add(f"{method} {ep}")

        # STRUCTURAL: Check we have test results
        total = smoke_result.get('total_scenarios', smoke_result.get('endpoints_tested', 0))
        if total == 0:
            result["structural_passed"] = False
            result["violations"].append({
                "tier": "STRUCTURAL",
                "field": "total_scenarios",
                "message": "No scenarios tested"
            })
            self.violations.append({
                "phase": "smoke_test",
                "tier": "STRUCTURAL",
                "type": "no_scenarios",
                "message": "No smoke test scenarios executed"
            })

        # STRUCTURAL: pass_rate must be valid
        pass_rate = smoke_result.get('pass_rate', 0.0)
        if not (0.0 <= pass_rate <= 1.0):
            result["structural_passed"] = False
            result["violations"].append({
                "tier": "STRUCTURAL",
                "field": "pass_rate",
                "message": f"Invalid pass_rate: {pass_rate}"
            })

        result["pass_rate"] = pass_rate

        # SEMANTIC: Check coverage of IR endpoints
        if ir_endpoints:
            missing = ir_endpoints - tested_endpoints
            coverage = 1.0 - (len(missing) / len(ir_endpoints)) if ir_endpoints else 1.0
            result["coverage"] = coverage

            if missing and len(missing) > len(ir_endpoints) * 0.1:  # >10% missing
                result["semantic_passed"] = False
                result["warnings"].append({
                    "tier": "SEMANTIC",
                    "field": "coverage",
                    "message": f"{len(missing)} IR endpoints not tested",
                    "missing": list(missing)[:5]
                })
                self.warnings.append({
                    "phase": "smoke_test",
                    "tier": "SEMANTIC",
                    "type": "low_coverage",
                    "message": f"Only {coverage:.1%} of IR endpoints tested"
                })

        # QUALITY: Pass rate thresholds
        min_pass_rate = self.QUALITY_THRESHOLDS.get("min_smoke_pass_rate", 0.70)
        target_pass_rate = self.QUALITY_THRESHOLDS.get("target_smoke_pass_rate", 0.95)

        if pass_rate < min_pass_rate:
            result["quality_passed"] = False
            result["warnings"].append({
                "tier": "QUALITY",
                "field": "pass_rate",
                "message": f"Pass rate {pass_rate:.1%} < {min_pass_rate:.0%} minimum",
                "threshold": min_pass_rate
            })
            self.warnings.append({
                "phase": "smoke_test",
                "tier": "QUALITY",
                "type": "below_minimum",
                "message": f"Pass rate {pass_rate:.1%} below {min_pass_rate:.0%} threshold"
            })
        elif pass_rate < target_pass_rate:
            result["warnings"].append({
                "tier": "QUALITY",
                "field": "pass_rate",
                "message": f"Pass rate {pass_rate:.1%} < {target_pass_rate:.0%} target",
                "threshold": target_pass_rate
            })

        return result

    def get_violations_summary(self) -> Dict[str, Any]:
        """Get summary of all contract violations and warnings"""
        by_phase: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_tier: Dict[str, int] = {}

        for v in self.violations:
            phase = v.get("phase", "unknown")
            vtype = v.get("type", "unknown")
            tier = v.get("tier", "LEGACY")

            by_phase[phase] = by_phase.get(phase, 0) + 1
            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_violations": len(self.violations),
            "total_warnings": len(self.warnings),
            "by_phase": by_phase,
            "by_type": by_type,
            "by_tier": by_tier,
            "violations": self.violations,
            "warnings": self.warnings
        }

    def print_validation_report(self):
        """Print comprehensive validation report with tiers"""
        print("\n" + "="*80)
        print("                         CONTRACT VALIDATION REPORT")
        print("="*80)

        # Summary
        v_count = len(self.violations)
        w_count = len(self.warnings)

        if v_count == 0 and w_count == 0:
            print("\n  ✅ All contracts validated successfully!")
            return

        # Group by tier
        structural = [v for v in self.violations if v.get("tier") == "STRUCTURAL"]
        semantic = [w for w in self.warnings if w.get("tier") == "SEMANTIC"]
        quality = [w for w in self.warnings if w.get("tier") == "QUALITY"]

        print(f"\n  📊 Summary:")
        print(f"     STRUCTURAL failures: {len(structural)} {'❌' if structural else '✅'}")
        print(f"     SEMANTIC warnings:   {len(semantic)} {'⚠️' if semantic else '✅'}")
        print(f"     QUALITY warnings:    {len(quality)} {'⚠️' if quality else '✅'}")

        # Details
        if structural:
            print(f"\n  ❌ STRUCTURAL FAILURES (blocking):")
            for v in structural[:5]:
                print(f"     • [{v.get('phase', '?')}] {v.get('message', 'No message')}")

        if semantic:
            print(f"\n  ⚠️  SEMANTIC WARNINGS:")
            for w in semantic[:5]:
                print(f"     • [{w.get('phase', '?')}] {w.get('message', 'No message')}")

        if quality:
            print(f"\n  ⚠️  QUALITY GATES:")
            for w in quality[:5]:
                print(f"     • [{w.get('phase', '?')}] {w.get('message', 'No message')}")

        print("\n" + "="*80)

    def print_violations(self):
        """Print all contract violations (legacy method)"""
        if not self.violations:
            print("✅ No contract violations detected")
            return

        print(f"\n⚠️  Contract Violations Detected: {len(self.violations)}")
        print("="*70)

        for i, v in enumerate(self.violations, 1):
            tier = v.get('tier', 'LEGACY')
            print(f"\n{i}. [{tier}] {v.get('phase', 'unknown').upper()}")
            print(f"   Type: {v.get('type', 'unknown')}")
            print(f"   Field: {v.get('field', 'N/A')}")
            print(f"   Message: {v.get('message', 'No message')}")
            if 'expected' in v:
                print(f"   Expected: {v['expected']}, Actual: {v.get('actual', '?')}")


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
            # Use search instead of match to allow leading whitespace
            req_match = re.search(r'\*\*([A-Z0-9_a-z]+)\*\*:', line)
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
