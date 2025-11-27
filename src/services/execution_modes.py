"""
Execution Modes - Stratified Generation Control

Phase 1: Implements Safe/Hybrid/Research execution modes.

SAFE Mode:
- Only TEMPLATE + AST strata allowed
- LLM completely disabled
- Zero generative risk
- PatternBank read-only

HYBRID Mode (Default):
- All strata enabled
- LLM constrained to allowed slots
- PatternBank write enabled
- Production-ready output

RESEARCH Mode:
- All strata enabled
- LLM has more freedom (experimental)
- PatternBank writes to sandbox only
- For testing new patterns
"""

import os
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from src.services.stratum_classification import Stratum, AtomKind, get_stratum_by_kind

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Execution modes for stratified generation."""
    SAFE = "safe"        # TEMPLATE + AST only, no LLM
    HYBRID = "hybrid"    # Default: LLM constrained to slots
    RESEARCH = "research"  # LLM with more freedom, sandbox


@dataclass
class ModeCapabilities:
    """Capabilities enabled for each execution mode."""
    template_enabled: bool = True
    ast_enabled: bool = True
    llm_enabled: bool = False
    llm_constrained: bool = True
    pattern_bank_write: bool = False
    pattern_bank_sandbox: bool = False
    max_llm_calls: Optional[int] = None
    allowed_llm_slots: List[str] = field(default_factory=list)


# Mode capability definitions
MODE_CAPABILITIES: Dict[ExecutionMode, ModeCapabilities] = {
    ExecutionMode.SAFE: ModeCapabilities(
        template_enabled=True,
        ast_enabled=True,
        llm_enabled=False,
        llm_constrained=True,
        pattern_bank_write=False,
        pattern_bank_sandbox=False,
        max_llm_calls=0,
        allowed_llm_slots=[],
    ),
    ExecutionMode.HYBRID: ModeCapabilities(
        template_enabled=True,
        ast_enabled=True,
        llm_enabled=True,
        llm_constrained=True,  # Only allowed slots
        pattern_bank_write=True,
        pattern_bank_sandbox=False,
        max_llm_calls=None,  # Unlimited
        allowed_llm_slots=[
            "src/services/*_flow_methods.py",
            "src/services/*_business_rules.py",
            "src/routes/*_custom.py",
            "repair_patches/*.py",
        ],
    ),
    ExecutionMode.RESEARCH: ModeCapabilities(
        template_enabled=True,
        ast_enabled=True,
        llm_enabled=True,
        llm_constrained=False,  # More freedom
        pattern_bank_write=False,  # Only sandbox
        pattern_bank_sandbox=True,
        max_llm_calls=None,
        allowed_llm_slots=["*"],  # All files
    ),
}


@dataclass
class ModeContext:
    """Runtime context for execution mode."""
    mode: ExecutionMode
    capabilities: ModeCapabilities
    llm_calls_made: int = 0
    stratum_usage: Dict[str, int] = field(default_factory=dict)
    blocked_operations: List[str] = field(default_factory=list)

    def can_use_stratum(self, stratum: Stratum) -> bool:
        """Check if stratum is allowed in current mode."""
        if stratum == Stratum.TEMPLATE:
            return self.capabilities.template_enabled
        if stratum == Stratum.AST:
            return self.capabilities.ast_enabled
        if stratum == Stratum.LLM:
            return self.capabilities.llm_enabled
        return True

    def can_make_llm_call(self) -> bool:
        """Check if another LLM call is allowed."""
        if not self.capabilities.llm_enabled:
            return False
        if self.capabilities.max_llm_calls is not None:
            return self.llm_calls_made < self.capabilities.max_llm_calls
        return True

    def record_llm_call(self) -> None:
        """Record an LLM call."""
        self.llm_calls_made += 1

    def record_stratum_usage(self, stratum: Stratum) -> None:
        """Record stratum usage for metrics."""
        key = stratum.value
        self.stratum_usage[key] = self.stratum_usage.get(key, 0) + 1

    def record_blocked(self, operation: str, reason: str) -> None:
        """Record a blocked operation."""
        self.blocked_operations.append(f"{operation}: {reason}")


class ExecutionModeManager:
    """
    Manages execution mode for code generation.

    Usage:
        manager = ExecutionModeManager(ExecutionMode.HYBRID)

        if manager.can_use_llm(file_path):
            # Generate with LLM
        else:
            # Use AST generator
    """

    def __init__(self, mode: Optional[ExecutionMode] = None):
        """
        Initialize execution mode manager.

        Args:
            mode: Execution mode (defaults to env EXECUTION_MODE or HYBRID)
        """
        if mode is None:
            mode_str = os.getenv("EXECUTION_MODE", "hybrid")
            mode = ExecutionMode(mode_str)

        self.mode = mode
        self.capabilities = MODE_CAPABILITIES[mode]
        self.context = ModeContext(
            mode=mode,
            capabilities=self.capabilities,
        )

        logger.info(f"🎚️ Execution mode: {mode.value.upper()}")
        self._log_capabilities()

    def _log_capabilities(self) -> None:
        """Log mode capabilities."""
        cap = self.capabilities
        logger.info(f"   TEMPLATE: {'✅' if cap.template_enabled else '❌'}")
        logger.info(f"   AST: {'✅' if cap.ast_enabled else '❌'}")
        logger.info(f"   LLM: {'✅' if cap.llm_enabled else '❌'} {'(constrained)' if cap.llm_constrained else '(free)'}")
        logger.info(f"   PatternBank: {'✅ write' if cap.pattern_bank_write else '📦 sandbox' if cap.pattern_bank_sandbox else '❌ read-only'}")

    def get_stratum_for_atom(self, atom_kind: AtomKind) -> Stratum:
        """
        Get the effective stratum for an atom kind in current mode.

        In SAFE mode, LLM atoms are downgraded to AST.

        Args:
            atom_kind: The kind of code atom

        Returns:
            Effective stratum to use
        """
        natural_stratum = get_stratum_by_kind(atom_kind)

        # In SAFE mode, downgrade LLM to AST
        if self.mode == ExecutionMode.SAFE and natural_stratum == Stratum.LLM:
            logger.debug(f"🔒 SAFE mode: {atom_kind.value} downgraded LLM→AST")
            self.context.record_blocked(
                f"LLM for {atom_kind.value}",
                "SAFE mode - LLM disabled"
            )
            return Stratum.AST

        return natural_stratum

    def can_use_llm(self, file_path: Optional[str] = None) -> bool:
        """
        Check if LLM can be used (optionally for a specific file).

        Args:
            file_path: Optional file path to check against allowed slots

        Returns:
            True if LLM usage is allowed
        """
        if not self.capabilities.llm_enabled:
            return False

        if not self.context.can_make_llm_call():
            return False

        # Check slot constraints in HYBRID mode
        if self.capabilities.llm_constrained and file_path:
            import fnmatch
            for pattern in self.capabilities.allowed_llm_slots:
                if fnmatch.fnmatch(file_path, pattern):
                    return True
                if fnmatch.fnmatch(file_path, f"*/{pattern}"):
                    return True
            return False

        return True

    def can_write_pattern_bank(self) -> bool:
        """Check if writing to PatternBank is allowed."""
        return self.capabilities.pattern_bank_write

    def get_pattern_bank_target(self) -> str:
        """Get the PatternBank target (main or sandbox)."""
        if self.capabilities.pattern_bank_write:
            return "main"
        if self.capabilities.pattern_bank_sandbox:
            return "sandbox"
        return "none"

    def record_generation(
        self,
        file_path: str,
        stratum: Stratum,
        used_llm: bool = False,
    ) -> None:
        """
        Record a generation operation for metrics.

        Args:
            file_path: Generated file path
            stratum: Stratum used
            used_llm: Whether LLM was used
        """
        self.context.record_stratum_usage(stratum)
        if used_llm:
            self.context.record_llm_call()

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "mode": self.mode.value,
            "llm_calls": self.context.llm_calls_made,
            "stratum_usage": self.context.stratum_usage,
            "blocked_operations": len(self.context.blocked_operations),
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        stats = self.get_stats()
        blocked = len(self.context.blocked_operations)

        return (
            f"🎚️ Mode: {self.mode.value.upper()} | "
            f"LLM calls: {stats['llm_calls']} | "
            f"Blocked: {blocked} | "
            f"Strata: {stats['stratum_usage']}"
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_manager: Optional[ExecutionModeManager] = None


def get_execution_mode_manager(
    mode: Optional[ExecutionMode] = None
) -> ExecutionModeManager:
    """Get singleton execution mode manager."""
    global _manager
    if _manager is None or mode is not None:
        _manager = ExecutionModeManager(mode)
    return _manager


def get_current_mode() -> ExecutionMode:
    """Get current execution mode."""
    return get_execution_mode_manager().mode


def is_safe_mode() -> bool:
    """Check if running in SAFE mode."""
    return get_current_mode() == ExecutionMode.SAFE


def is_hybrid_mode() -> bool:
    """Check if running in HYBRID mode."""
    return get_current_mode() == ExecutionMode.HYBRID


def is_research_mode() -> bool:
    """Check if running in RESEARCH mode."""
    return get_current_mode() == ExecutionMode.RESEARCH


def can_use_llm(file_path: Optional[str] = None) -> bool:
    """Check if LLM can be used."""
    return get_execution_mode_manager().can_use_llm(file_path)


def get_effective_stratum(atom_kind: AtomKind) -> Stratum:
    """Get effective stratum for atom kind in current mode."""
    return get_execution_mode_manager().get_stratum_for_atom(atom_kind)


# =============================================================================
# MODE-AWARE DECORATORS
# =============================================================================

def requires_llm(func: Callable) -> Callable:
    """
    Decorator that checks if LLM is available before calling function.

    If LLM is not available, returns None or raises based on mode.
    """
    def wrapper(*args, **kwargs):
        manager = get_execution_mode_manager()
        file_path = kwargs.get('file_path') or (args[0] if args else None)

        if not manager.can_use_llm(file_path):
            logger.warning(
                f"🚫 LLM blocked in {manager.mode.value} mode for {func.__name__}"
            )
            manager.context.record_blocked(
                func.__name__,
                f"LLM not available in {manager.mode.value} mode"
            )
            return None

        result = func(*args, **kwargs)
        manager.record_generation(
            file_path=file_path or "unknown",
            stratum=Stratum.LLM,
            used_llm=True,
        )
        return result

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def mode_aware(fallback_stratum: Stratum = Stratum.AST) -> Callable:
    """
    Decorator that routes to appropriate stratum based on mode.

    Args:
        fallback_stratum: Stratum to use if LLM is not available
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            manager = get_execution_mode_manager()
            file_path = kwargs.get('file_path') or (args[0] if args else None)

            # Check if we can use LLM
            if manager.can_use_llm(file_path):
                result = func(*args, **kwargs)
                manager.record_generation(
                    file_path=file_path or "unknown",
                    stratum=Stratum.LLM,
                    used_llm=True,
                )
                return result
            else:
                # Return None to signal caller should use fallback
                logger.info(
                    f"🔄 {func.__name__} using {fallback_stratum.value} fallback"
                )
                manager.context.record_blocked(
                    func.__name__,
                    f"Falling back to {fallback_stratum.value}"
                )
                return None

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
