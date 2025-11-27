"""
LLM Guardrails - Constraint System for LLM Code Generation

Ensures LLM can ONLY write to allowed slots:
- Business flow methods
- Business rules
- Custom (non-CRUD) endpoints
- Repair patches

NEVER allows LLM to write:
- Infrastructure files (docker, config)
- Core modules (database, main)
- Static templates

This is a SAFETY LAYER - violations should fail loudly.
"""

import re
import logging
from typing import Set, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import fnmatch

logger = logging.getLogger(__name__)


class GuardrailViolation(Exception):
    """Raised when LLM attempts to violate guardrails."""
    pass


class ViolationType(str, Enum):
    """Types of guardrail violations."""
    FORBIDDEN_FILE = "forbidden_file"
    OUTSIDE_ALLOWED_SLOTS = "outside_allowed_slots"
    INFRASTRUCTURE_MODIFICATION = "infrastructure_modification"
    CORE_MODULE_MODIFICATION = "core_module_modification"


@dataclass
class ViolationReport:
    """Report of a guardrail violation."""
    violation_type: ViolationType
    file_path: str
    reason: str
    blocked: bool = True


# =============================================================================
# CONSTRAINT DEFINITIONS
# =============================================================================

# Files LLM is ABSOLUTELY FORBIDDEN to modify
LLM_FORBIDDEN_FILES: Set[str] = {
    # Infrastructure
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "prometheus.yml",
    "grafana/*",

    # Config
    "requirements.txt",
    "pyproject.toml",
    ".env",
    ".env.example",
    ".env.production",
    "alembic.ini",

    # Core modules
    "src/core/config.py",
    "src/core/database.py",
    "core/config.py",
    "core/database.py",

    # Main app
    "src/main.py",
    "main.py",

    # Base classes (immutable)
    "src/models/base.py",
    "src/repositories/base.py",
    "models/base.py",
    "repositories/base.py",

    # Health endpoints (standard)
    "src/api/routes/health.py",
    "src/routes/health.py",
    "api/routes/health.py",
    "routes/health.py",

    # Alembic env
    "alembic/env.py",

    # Init files (structure)
    "__init__.py",
}

# Patterns for forbidden directories
LLM_FORBIDDEN_DIRECTORIES: Set[str] = {
    "grafana/",
    ".github/",
    "scripts/",
    "docs/",
}

# Files LLM IS ALLOWED to modify (whitelist approach)
LLM_ALLOWED_SLOTS: Set[str] = {
    # Business logic files
    "src/services/*_flow_methods.py",
    "src/services/*_business_rules.py",
    "services/*_flow_methods.py",
    "services/*_business_rules.py",

    # Custom endpoints (non-CRUD)
    "src/routes/*_custom.py",
    "src/api/routes/*_custom.py",
    "routes/*_custom.py",

    # Repair patches (localized fixes)
    "repair_patches/*.py",
    "patches/*.py",

    # Business logic in services (specific methods only)
    "src/services/*_service.py:business_*",  # Only business_ prefixed methods
    "services/*_service.py:business_*",
}

# Patterns that indicate business logic (LLM can enhance)
BUSINESS_LOGIC_INDICATORS: Set[str] = {
    "business_",
    "workflow_",
    "process_",
    "calculate_",
    "validate_complex_",
    "handle_",
    "orchestrate_",
}


class LLMGuardrails:
    """
    Enforces constraints on LLM code generation.

    Design principle: DENY BY DEFAULT, ALLOW EXPLICITLY
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize guardrails.

        Args:
            strict_mode: If True, violations raise exceptions.
                        If False, violations are logged but allowed.
        """
        self.strict_mode = strict_mode
        self._violations: List[ViolationReport] = []

    def check_write_permission(
        self,
        file_path: str,
        context: Optional[str] = None
    ) -> Tuple[bool, Optional[ViolationReport]]:
        """
        Check if LLM is allowed to write to a file.

        Args:
            file_path: Path to file
            context: Optional context (e.g., method name being modified)

        Returns:
            Tuple of (is_allowed, violation_report)
        """
        # Normalize path
        normalized = self._normalize_path(file_path)

        # Check 1: Forbidden files (absolute block)
        if self._is_forbidden_file(normalized):
            violation = ViolationReport(
                violation_type=ViolationType.FORBIDDEN_FILE,
                file_path=file_path,
                reason=f"File {file_path} is in LLM_FORBIDDEN_FILES list",
            )
            self._violations.append(violation)
            return (False, violation)

        # Check 2: Forbidden directories
        if self._is_in_forbidden_directory(normalized):
            violation = ViolationReport(
                violation_type=ViolationType.INFRASTRUCTURE_MODIFICATION,
                file_path=file_path,
                reason=f"File {file_path} is in a forbidden directory",
            )
            self._violations.append(violation)
            return (False, violation)

        # Check 3: Must be in allowed slots
        if not self._is_in_allowed_slot(normalized, context):
            violation = ViolationReport(
                violation_type=ViolationType.OUTSIDE_ALLOWED_SLOTS,
                file_path=file_path,
                reason=f"File {file_path} is not in LLM_ALLOWED_SLOTS",
            )
            self._violations.append(violation)
            return (False, violation)

        # All checks passed
        logger.debug(f"✅ LLM write allowed: {file_path}")
        return (True, None)

    def enforce_write_permission(
        self,
        file_path: str,
        context: Optional[str] = None
    ) -> None:
        """
        Enforce write permission - raises if not allowed.

        Args:
            file_path: Path to file
            context: Optional context

        Raises:
            GuardrailViolation: If write is not allowed in strict mode
        """
        is_allowed, violation = self.check_write_permission(file_path, context)

        if not is_allowed and self.strict_mode:
            raise GuardrailViolation(
                f"🚫 LLM GUARDRAIL VIOLATION: {violation.reason}\n"
                f"   File: {file_path}\n"
                f"   Type: {violation.violation_type.value}\n"
                f"   Action: Use TEMPLATE or AST stratum instead"
            )

        if not is_allowed:
            logger.warning(
                f"⚠️ LLM guardrail violation (non-strict): {violation.reason}"
            )

    def validate_generated_code(
        self,
        file_path: str,
        code: str
    ) -> List[ViolationReport]:
        """
        Validate generated code for additional guardrail violations.

        Checks:
        - No imports of forbidden modules
        - No modification of protected patterns
        - No security-sensitive code in wrong places

        Args:
            file_path: Target file path
            code: Generated code content

        Returns:
            List of violations found
        """
        violations = []

        # Check for forbidden imports in non-security files
        if not self._is_security_file(file_path):
            forbidden_imports = self._check_forbidden_imports(code)
            if forbidden_imports:
                violations.append(ViolationReport(
                    violation_type=ViolationType.INFRASTRUCTURE_MODIFICATION,
                    file_path=file_path,
                    reason=f"Forbidden imports detected: {forbidden_imports}",
                    blocked=False,  # Warning only
                ))

        # Check for modification of core patterns
        if self._modifies_core_patterns(code):
            violations.append(ViolationReport(
                violation_type=ViolationType.CORE_MODULE_MODIFICATION,
                file_path=file_path,
                reason="Code appears to modify core infrastructure patterns",
                blocked=False,
            ))

        return violations

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for comparison."""
        # Remove leading ./
        if file_path.startswith("./"):
            file_path = file_path[2:]
        # Remove leading /
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        return file_path

    def _is_forbidden_file(self, file_path: str) -> bool:
        """Check if file is in forbidden list."""
        for pattern in LLM_FORBIDDEN_FILES:
            if fnmatch.fnmatch(file_path, pattern):
                return True
            if fnmatch.fnmatch(file_path, f"*/{pattern}"):
                return True
            # Exact match
            if file_path.endswith(pattern):
                return True
        return False

    def _is_in_forbidden_directory(self, file_path: str) -> bool:
        """Check if file is in a forbidden directory."""
        for directory in LLM_FORBIDDEN_DIRECTORIES:
            if file_path.startswith(directory):
                return True
            if f"/{directory}" in file_path:
                return True
        return False

    def _is_in_allowed_slot(
        self,
        file_path: str,
        context: Optional[str] = None
    ) -> bool:
        """Check if file is in an allowed slot for LLM."""
        for pattern in LLM_ALLOWED_SLOTS:
            # Handle method-level patterns (e.g., *_service.py:business_*)
            if ":" in pattern:
                file_pattern, method_pattern = pattern.split(":", 1)
                if fnmatch.fnmatch(file_path, file_pattern) or \
                   fnmatch.fnmatch(file_path, f"*/{file_pattern}"):
                    if context and fnmatch.fnmatch(context, method_pattern):
                        return True
            else:
                # File-level pattern
                if fnmatch.fnmatch(file_path, pattern):
                    return True
                if fnmatch.fnmatch(file_path, f"*/{pattern}"):
                    return True

        # Check for business logic indicators in the file name
        for indicator in BUSINESS_LOGIC_INDICATORS:
            if indicator in file_path.lower():
                return True

        return False

    def _is_security_file(self, file_path: str) -> bool:
        """Check if file is a security-related file."""
        security_patterns = [
            "*auth*",
            "*security*",
            "*permission*",
            "*middleware*",
        ]
        return any(fnmatch.fnmatch(file_path, p) for p in security_patterns)

    def _check_forbidden_imports(self, code: str) -> List[str]:
        """Check for forbidden imports in generated code."""
        forbidden = []

        # Patterns that shouldn't be in business logic files
        forbidden_patterns = [
            r"from\s+src\.core\.database\s+import.*engine",
            r"import\s+subprocess",
            r"import\s+os\.system",
            r"exec\s*\(",
            r"eval\s*\(",
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                forbidden.append(pattern)

        return forbidden

    def _modifies_core_patterns(self, code: str) -> bool:
        """Check if code modifies core infrastructure patterns."""
        core_patterns = [
            "DeclarativeBase",
            "create_async_engine",
            "BaseSettings",
            "CORSMiddleware",
        ]

        # If code defines these, it might be modifying core patterns
        for pattern in core_patterns:
            if f"class {pattern}" in code or f"def {pattern}" in code:
                return True

        return False

    def get_violations(self) -> List[ViolationReport]:
        """Get all recorded violations."""
        return self._violations.copy()

    def clear_violations(self) -> None:
        """Clear recorded violations."""
        self._violations.clear()

    def get_violation_summary(self) -> str:
        """Get a summary of all violations."""
        if not self._violations:
            return "✅ No guardrail violations recorded"

        summary = f"⚠️ {len(self._violations)} guardrail violations:\n"
        for v in self._violations:
            status = "🚫 BLOCKED" if v.blocked else "⚠️ WARNING"
            summary += f"  {status} [{v.violation_type.value}] {v.file_path}: {v.reason}\n"

        return summary


# =============================================================================
# DECORATOR FOR AUTOMATIC ENFORCEMENT
# =============================================================================

def enforce_llm_guardrails(func):
    """
    Decorator to enforce guardrails on LLM generation functions.

    Usage:
        @enforce_llm_guardrails
        def generate_with_llm(file_path: str, ...) -> str:
            ...
    """
    def wrapper(file_path: str, *args, **kwargs):
        guardrails = LLMGuardrails(strict_mode=True)
        guardrails.enforce_write_permission(file_path)
        return func(file_path, *args, **kwargs)

    return wrapper


# Singleton instance
_guardrails: Optional[LLMGuardrails] = None


def get_guardrails(strict_mode: bool = True) -> LLMGuardrails:
    """Get singleton LLMGuardrails instance."""
    global _guardrails
    if _guardrails is None:
        _guardrails = LLMGuardrails(strict_mode=strict_mode)
    return _guardrails


# =============================================================================
# CONVENIENCE FUNCTIONS (Phase 0.5.4)
# =============================================================================

class LLMSlotViolation(GuardrailViolation):
    """Specific exception for LLM slot violations."""
    pass


def assert_llm_slot(file_path: str, context: Optional[str] = None) -> bool:
    """
    Assert that LLM is allowed to write to this file path.

    Phase 0.5.4: Simple assertion function for use before LLM calls.

    Args:
        file_path: Path to file being written
        context: Optional method name context

    Returns:
        True if allowed

    Raises:
        LLMSlotViolation: If LLM is not allowed to write
    """
    guardrails = get_guardrails(strict_mode=True)
    is_allowed, violation = guardrails.check_write_permission(file_path, context)

    if not is_allowed:
        raise LLMSlotViolation(
            f"🚫 LLM cannot write to '{file_path}'. "
            f"Reason: {violation.reason if violation else 'Unknown'}. "
            f"Use TEMPLATE or AST stratum instead."
        )

    return True


def is_llm_slot(file_path: str, context: Optional[str] = None) -> bool:
    """
    Check if file path is a valid LLM slot (non-raising).

    Args:
        file_path: Path to check
        context: Optional method context

    Returns:
        True if LLM can write, False otherwise
    """
    guardrails = get_guardrails(strict_mode=False)
    is_allowed, _ = guardrails.check_write_permission(file_path, context)
    return is_allowed
