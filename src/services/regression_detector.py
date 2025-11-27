"""
Regression Detector - Known Bug Pattern Detection

Detects known anti-patterns and bugs BEFORE code is:
1. Stored in PatternBank
2. Promoted from LLM → AST → TEMPLATE
3. Deployed to production

Design: Fail fast, block bad patterns from propagating.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class BugSeverity(str, Enum):
    """Severity levels for detected bugs."""
    CRITICAL = "critical"   # Blocks promotion, requires immediate fix
    HIGH = "high"           # Blocks promotion
    MEDIUM = "medium"       # Warning, may block promotion
    LOW = "low"             # Warning only


class BugCategory(str, Enum):
    """Categories of known bugs."""
    SQL_INJECTION = "sql_injection"
    SERVER_DEFAULT = "server_default"
    PATH_PARAM = "path_param"
    ASYNC_PATTERN = "async_pattern"
    TYPE_ERROR = "type_error"
    IMPORT_ERROR = "import_error"
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC_ERROR = "logic_error"


@dataclass
class KnownBug:
    """Definition of a known bug pattern."""
    bug_id: str
    name: str
    description: str
    category: BugCategory
    severity: BugSeverity
    pattern: str  # Regex pattern to detect
    fix_hint: str
    discovered_date: str
    file_patterns: List[str] = field(default_factory=list)  # Files where this bug applies
    fixed: bool = False


@dataclass
class BugDetection:
    """Result of bug detection."""
    bug: KnownBug
    file_path: str
    line_number: Optional[int]
    matched_code: str
    blocked: bool


# =============================================================================
# KNOWN BUGS REGISTRY
# =============================================================================

KNOWN_BUGS: Dict[str, KnownBug] = {
    # BUG-001: server_default with sa.text for string literals
    "BUG-001": KnownBug(
        bug_id="BUG-001",
        name="server_default_string_literal",
        description=(
            "Using sa.text() for string literal defaults like 'OPEN'. "
            "sa.text() should only be used for SQL functions like now()."
        ),
        category=BugCategory.SERVER_DEFAULT,
        severity=BugSeverity.HIGH,
        pattern=r"server_default\s*=\s*sa\.text\s*\(\s*['\"](?!now\(\)|gen_random_uuid\(\)|current_timestamp|uuid_generate_v4\(\))[A-Z_]+['\"]\s*\)",
        fix_hint="Use server_default='VALUE' (plain string) instead of server_default=sa.text('VALUE')",
        discovered_date="2025-11-26",
        file_patterns=["**/entities.py", "**/models.py"],
    ),

    # BUG-002: Path param mismatch
    "BUG-002": KnownBug(
        bug_id="BUG-002",
        name="path_param_mismatch",
        description=(
            "Path parameter names in routes don't match IR definitions. "
            "E.g., route has {product_id} but IR has {id}."
        ),
        category=BugCategory.PATH_PARAM,
        severity=BugSeverity.MEDIUM,
        pattern=r"@router\.\w+\(['\"][^'\"]*\{(\w+)\}[^'\"]*['\"]",  # Captures param name
        fix_hint="Normalize path params: use {id} or {entity_id} consistently",
        discovered_date="2025-11-26",
        file_patterns=["**/routes/*.py", "**/api/**/*.py"],
    ),

    # BUG-003: Async context manager not awaited
    "BUG-003": KnownBug(
        bug_id="BUG-003",
        name="async_context_not_awaited",
        description=(
            "Using async context manager without await. "
            "async with session: should be used for async sessions."
        ),
        category=BugCategory.ASYNC_PATTERN,
        severity=BugSeverity.HIGH,
        pattern=r"with\s+async_session\s*\(",
        fix_hint="Use 'async with async_session() as session:' instead of 'with async_session()'",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-004: Raw SQL without parameterization
    "BUG-004": KnownBug(
        bug_id="BUG-004",
        name="sql_string_formatting",
        description=(
            "SQL query uses string formatting instead of parameterized queries. "
            "This is a SQL injection vulnerability."
        ),
        category=BugCategory.SQL_INJECTION,
        severity=BugSeverity.CRITICAL,
        pattern=r"execute\s*\(\s*f['\"]|execute\s*\(\s*['\"].*%s|execute\s*\(\s*['\"].*\.format\s*\(",
        fix_hint="Use parameterized queries: execute(text('SELECT * FROM x WHERE id = :id'), {'id': value})",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-005: Missing await on async function
    "BUG-005": KnownBug(
        bug_id="BUG-005",
        name="missing_await",
        description=(
            "Async function called without await. "
            "Results in coroutine object instead of actual result."
        ),
        category=BugCategory.ASYNC_PATTERN,
        severity=BugSeverity.HIGH,
        pattern=r"(?<!await\s)(?<!return\s)(?<!yield\s)(?<!=\s)session\.(execute|commit|rollback|flush|refresh)\s*\(",
        fix_hint="Add 'await' before async session methods",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-006: Hardcoded secrets
    "BUG-006": KnownBug(
        bug_id="BUG-006",
        name="hardcoded_secrets",
        description=(
            "Hardcoded secrets, passwords, or API keys in code. "
            "Should use environment variables."
        ),
        category=BugCategory.SECURITY,
        severity=BugSeverity.CRITICAL,
        pattern=r"(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]{8,}['\"]",
        fix_hint="Use environment variables: os.getenv('SECRET_KEY') or settings.secret_key",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-007: Sync operation in async function
    "BUG-007": KnownBug(
        bug_id="BUG-007",
        name="sync_in_async",
        description=(
            "Blocking sync operation inside async function. "
            "Will block the event loop."
        ),
        category=BugCategory.PERFORMANCE,
        severity=BugSeverity.MEDIUM,
        pattern=r"async\s+def\s+\w+[^:]+:.*?(?:time\.sleep|requests\.get|open\s*\([^)]*\)\.read)",
        fix_hint="Use async equivalents: asyncio.sleep, httpx.AsyncClient, aiofiles",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-008: Import from wrong module
    "BUG-008": KnownBug(
        bug_id="BUG-008",
        name="wrong_import_path",
        description=(
            "Importing from incorrect module path. "
            "Common: importing from src.models when should be from src.models.entities."
        ),
        category=BugCategory.IMPORT_ERROR,
        severity=BugSeverity.HIGH,
        pattern=r"from\s+src\.models\s+import\s+(?!entities|schemas|base)",
        fix_hint="Import from specific submodule: from src.models.entities import Model",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-009: N+1 query pattern
    "BUG-009": KnownBug(
        bug_id="BUG-009",
        name="n_plus_1_query",
        description=(
            "N+1 query pattern: loading related entities in a loop. "
            "Use eager loading with selectinload/joinedload."
        ),
        category=BugCategory.PERFORMANCE,
        severity=BugSeverity.MEDIUM,
        pattern=r"for\s+\w+\s+in\s+\w+:.*?await.*?session\.(get|execute)",
        fix_hint="Use selectinload() or joinedload() to eagerly load relationships",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),

    # BUG-010: Mutable default argument
    "BUG-010": KnownBug(
        bug_id="BUG-010",
        name="mutable_default_arg",
        description=(
            "Mutable default argument in function definition. "
            "Lists and dicts should use None as default."
        ),
        category=BugCategory.LOGIC_ERROR,
        severity=BugSeverity.MEDIUM,
        pattern=r"def\s+\w+\s*\([^)]*:\s*(?:List|Dict|list|dict)\s*=\s*(?:\[\]|\{\})",
        fix_hint="Use None as default: def func(items: List = None): items = items or []",
        discovered_date="2025-11-26",
        file_patterns=["**/*.py"],
    ),
}


class RegressionDetector:
    """
    Detects known bug patterns in generated code.

    Use before:
    - Storing patterns in PatternBank
    - Promoting patterns between strata
    - Deploying to production
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize detector.

        Args:
            strict_mode: If True, CRITICAL and HIGH bugs block operations
        """
        self.strict_mode = strict_mode
        self.known_bugs = KNOWN_BUGS.copy()
        self._detections: List[BugDetection] = []

    def scan_code(
        self,
        code: str,
        file_path: str,
        categories: Optional[Set[BugCategory]] = None
    ) -> List[BugDetection]:
        """
        Scan code for known bug patterns.

        Args:
            code: Source code to scan
            file_path: Path of the file (for pattern matching)
            categories: Optional set of categories to check (None = all)

        Returns:
            List of detected bugs
        """
        detections = []

        for bug_id, bug in self.known_bugs.items():
            # Skip if category filter doesn't match
            if categories and bug.category not in categories:
                continue

            # Skip if file pattern doesn't match
            if bug.file_patterns and not self._matches_file_pattern(file_path, bug.file_patterns):
                continue

            # Scan for pattern
            matches = list(re.finditer(bug.pattern, code, re.MULTILINE | re.DOTALL))

            for match in matches:
                # Calculate line number
                line_number = code[:match.start()].count('\n') + 1

                # Determine if this should block
                blocked = (
                    self.strict_mode and
                    bug.severity in [BugSeverity.CRITICAL, BugSeverity.HIGH]
                )

                detection = BugDetection(
                    bug=bug,
                    file_path=file_path,
                    line_number=line_number,
                    matched_code=match.group(0)[:100],  # First 100 chars
                    blocked=blocked,
                )
                detections.append(detection)

                logger.warning(
                    f"🐛 {bug.severity.value.upper()}: {bug.name} in {file_path}:{line_number}\n"
                    f"   Match: {match.group(0)[:50]}...\n"
                    f"   Fix: {bug.fix_hint}"
                )

        self._detections.extend(detections)
        return detections

    def scan_files(
        self,
        files: Dict[str, str],
        categories: Optional[Set[BugCategory]] = None
    ) -> Dict[str, List[BugDetection]]:
        """
        Scan multiple files for known bugs.

        Args:
            files: Dict mapping file paths to content
            categories: Optional category filter

        Returns:
            Dict mapping file paths to their detections
        """
        results = {}

        for file_path, code in files.items():
            detections = self.scan_code(code, file_path, categories)
            if detections:
                results[file_path] = detections

        return results

    def check_promotion_eligibility(
        self,
        code: str,
        file_path: str
    ) -> Tuple[bool, List[BugDetection]]:
        """
        Check if code is eligible for stratum promotion.

        Code with CRITICAL or HIGH severity bugs cannot be promoted.

        Args:
            code: Source code
            file_path: File path

        Returns:
            Tuple of (is_eligible, blocking_detections)
        """
        detections = self.scan_code(code, file_path)

        blocking = [d for d in detections if d.blocked]

        is_eligible = len(blocking) == 0

        if not is_eligible:
            logger.error(
                f"❌ Code not eligible for promotion: {len(blocking)} blocking bugs found\n"
                f"   File: {file_path}\n"
                f"   Bugs: {[d.bug.name for d in blocking]}"
            )

        return (is_eligible, blocking)

    def add_known_bug(self, bug: KnownBug) -> None:
        """Add a new known bug pattern."""
        self.known_bugs[bug.bug_id] = bug
        logger.info(f"Added known bug: {bug.bug_id} - {bug.name}")

    def get_bug_by_category(self, category: BugCategory) -> List[KnownBug]:
        """Get all bugs in a category."""
        return [b for b in self.known_bugs.values() if b.category == category]

    def get_detection_summary(self) -> Dict[str, any]:
        """Get summary of all detections."""
        if not self._detections:
            return {
                "total": 0,
                "by_severity": {},
                "by_category": {},
                "blocked": 0,
            }

        by_severity = {}
        by_category = {}

        for d in self._detections:
            sev = d.bug.severity.value
            cat = d.bug.category.value

            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total": len(self._detections),
            "by_severity": by_severity,
            "by_category": by_category,
            "blocked": sum(1 for d in self._detections if d.blocked),
        }

    def clear_detections(self) -> None:
        """Clear detection history."""
        self._detections.clear()

    def _matches_file_pattern(self, file_path: str, patterns: List[str]) -> bool:
        """Check if file matches any of the patterns."""
        import fnmatch
        for pattern in patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False


# =============================================================================
# DECORATOR FOR AUTOMATIC SCANNING
# =============================================================================

def scan_for_regressions(func):
    """
    Decorator to automatically scan generated code for regressions.

    Usage:
        @scan_for_regressions
        def generate_code(file_path: str) -> str:
            return generated_code
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if result and isinstance(result, str):
            # Try to extract file_path from args/kwargs
            file_path = kwargs.get('file_path') or (args[0] if args else 'unknown')

            detector = get_regression_detector()
            is_eligible, blocking = detector.check_promotion_eligibility(result, file_path)

            if not is_eligible:
                logger.error(
                    f"Generated code has {len(blocking)} blocking bugs. "
                    f"Review and fix before proceeding."
                )

        return result

    return wrapper


# Singleton instance
_detector: Optional[RegressionDetector] = None


def get_regression_detector(strict_mode: bool = True) -> RegressionDetector:
    """Get singleton RegressionDetector instance."""
    global _detector
    if _detector is None:
        _detector = RegressionDetector(strict_mode=strict_mode)
    return _detector
