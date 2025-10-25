"""
Validation Models (Stub)

Temporary models for testing. Real implementation from Phase 2.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue."""
    severity: ValidationSeverity
    category: str
    message: str
    location: Dict[str, Any]
