"""
Convergence Monitor - Guarantees repair loop termination.

Problems this solves:
- Same violation appearing 3+ times
- Repair causing regression that triggers self-repair
- Business logic error treated as schema error (infinite loop)

Guarantees:
- Max 2 repairs per constraint
- Detect repair cycles
- Escalation when deterministic repair fails
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ConvergenceStatus(str, Enum):
    """Status of convergence check."""
    CONVERGING = "converging"      # Making progress
    STABLE = "stable"              # No more violations
    NON_CONVERGENT = "non_convergent"  # Same violations repeating
    CYCLE_DETECTED = "cycle_detected"  # Repair→Regression→Repair loop
    LIMIT_REACHED = "limit_reached"    # Max iterations hit


class EscalationAction(str, Enum):
    """Actions when convergence fails."""
    CONTINUE = "continue"          # Keep trying
    SKIP_CONSTRAINT = "skip"       # Skip this constraint
    ESCALATE_LLM = "escalate_llm"  # Use LLM for complex fix
    ABORT = "abort"                # Stop repair loop


@dataclass
class ConvergenceState:
    """State of convergence monitoring."""
    iteration: int = 0
    violations_per_iteration: List[Set[str]] = field(default_factory=list)
    repairs_per_constraint: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    repair_sequence: List[str] = field(default_factory=list)  # For cycle detection
    status: ConvergenceStatus = ConvergenceStatus.CONVERGING


@dataclass
class ConvergenceResult:
    """Result of convergence check."""
    status: ConvergenceStatus
    action: EscalationAction
    reason: str
    problematic_constraints: List[str] = field(default_factory=list)


class ConvergenceMonitor:
    """
    Monitors repair loop for convergence.
    
    Rules:
    - Max 5 iterations total
    - Max 2 repairs per constraint
    - If same violations appear 3x → non-convergent
    - If repair A→B→A pattern → cycle detected
    """
    
    MAX_ITERATIONS = 5
    MAX_REPAIRS_PER_CONSTRAINT = 2
    REPEAT_THRESHOLD = 3  # Same violation appearing this many times
    
    def __init__(self):
        self.state = ConvergenceState()
        self._violation_history: Dict[str, int] = defaultdict(int)  # violation → count
    
    def reset(self):
        """Reset state for new repair session."""
        self.state = ConvergenceState()
        self._violation_history.clear()
    
    def record_iteration(self, violations: List[str]) -> ConvergenceResult:
        """Record violations for an iteration and check convergence."""
        self.state.iteration += 1
        violation_set = set(violations)
        self.state.violations_per_iteration.append(violation_set)
        
        # Update violation counts
        for v in violations:
            self._violation_history[v] += 1
        
        # Check for stability (no violations)
        if not violations:
            return ConvergenceResult(
                status=ConvergenceStatus.STABLE,
                action=EscalationAction.CONTINUE,
                reason="No violations remaining"
            )
        
        # Check iteration limit
        if self.state.iteration >= self.MAX_ITERATIONS:
            return ConvergenceResult(
                status=ConvergenceStatus.LIMIT_REACHED,
                action=EscalationAction.ABORT,
                reason=f"Max iterations ({self.MAX_ITERATIONS}) reached",
                problematic_constraints=violations
            )
        
        # Check for repeating violations
        repeating = [v for v, count in self._violation_history.items() 
                     if count >= self.REPEAT_THRESHOLD]
        if repeating:
            return ConvergenceResult(
                status=ConvergenceStatus.NON_CONVERGENT,
                action=EscalationAction.ESCALATE_LLM,
                reason=f"Violations repeating {self.REPEAT_THRESHOLD}+ times",
                problematic_constraints=repeating
            )
        
        # Check for cycles (same violation set as 2 iterations ago)
        if len(self.state.violations_per_iteration) >= 3:
            current = self.state.violations_per_iteration[-1]
            two_ago = self.state.violations_per_iteration[-3]
            if current == two_ago:
                return ConvergenceResult(
                    status=ConvergenceStatus.CYCLE_DETECTED,
                    action=EscalationAction.SKIP_CONSTRAINT,
                    reason="Repair cycle detected (A→B→A pattern)",
                    problematic_constraints=list(current)
                )
        
        # Still converging
        return ConvergenceResult(
            status=ConvergenceStatus.CONVERGING,
            action=EscalationAction.CONTINUE,
            reason=f"Iteration {self.state.iteration}: {len(violations)} violations"
        )
    
    def record_repair(self, constraint_id: str) -> ConvergenceResult:
        """Record a repair attempt and check if limit reached."""
        self.state.repairs_per_constraint[constraint_id] += 1
        self.state.repair_sequence.append(constraint_id)
        
        count = self.state.repairs_per_constraint[constraint_id]
        if count > self.MAX_REPAIRS_PER_CONSTRAINT:
            return ConvergenceResult(
                status=ConvergenceStatus.NON_CONVERGENT,
                action=EscalationAction.SKIP_CONSTRAINT,
                reason=f"Constraint {constraint_id} repaired {count} times (max: {self.MAX_REPAIRS_PER_CONSTRAINT})",
                problematic_constraints=[constraint_id]
            )
        
        # Check for immediate cycle (same repair twice in a row)
        if len(self.state.repair_sequence) >= 2:
            if self.state.repair_sequence[-1] == self.state.repair_sequence[-2]:
                return ConvergenceResult(
                    status=ConvergenceStatus.CYCLE_DETECTED,
                    action=EscalationAction.SKIP_CONSTRAINT,
                    reason=f"Same repair applied twice: {constraint_id}",
                    problematic_constraints=[constraint_id]
                )
        
        return ConvergenceResult(
            status=ConvergenceStatus.CONVERGING,
            action=EscalationAction.CONTINUE,
            reason=f"Repair {count}/{self.MAX_REPAIRS_PER_CONSTRAINT} for {constraint_id}"
        )
    
    def should_continue(self) -> bool:
        """Check if repair loop should continue."""
        return self.state.status in (ConvergenceStatus.CONVERGING, ConvergenceStatus.STABLE)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of convergence state."""
        return {
            'iterations': self.state.iteration,
            'status': self.state.status.value,
            'total_repairs': sum(self.state.repairs_per_constraint.values()),
            'constraints_repaired': len(self.state.repairs_per_constraint),
            'repeating_violations': [v for v, c in self._violation_history.items() if c >= 2]
        }

