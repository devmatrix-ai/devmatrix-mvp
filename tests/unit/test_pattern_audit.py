"""
Unit tests for pattern auditing logic.

Tests critical behaviors for pattern database cleanup:
- Patterns with empty purpose are identified
- Framework filtering works correctly
- Pattern count before/after is reported
- Clean patterns are valid

Spec Reference: Task Group 3.1 (spec.md lines 140-148)
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime


class MockPattern:
    """Mock pattern for testing without Qdrant dependency."""

    def __init__(
        self,
        pattern_id: str,
        purpose: str,
        framework: str,
        code: str = "def test(): pass",
        domain: str = "general",
        success_rate: float = 0.95
    ):
        self.pattern_id = pattern_id
        self.purpose = purpose
        self.framework = framework
        self.code = code
        self.domain = domain
        self.success_rate = success_rate
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (simulating Qdrant payload)."""
        return {
            "pattern_id": self.pattern_id,
            "purpose": self.purpose,
            "framework": self.framework,
            "code": self.code,
            "domain": self.domain,
            "success_rate": self.success_rate,
            "created_at": self.created_at
        }


class PatternAuditor:
    """
    Pattern auditor for database cleanup.

    Implements audit logic:
    - Identify patterns with empty purpose
    - Filter patterns by framework
    - Report statistics
    """

    def __init__(self, patterns: List[MockPattern]):
        self.patterns = patterns
        self.removed_empty = 0
        self.removed_framework = 0
        self.cleaned_patterns = []

    def audit(self, framework_filter: str = "fastapi") -> Dict[str, Any]:
        """
        Audit patterns and return statistics.

        Args:
            framework_filter: Only keep patterns for this framework

        Returns:
            Statistics dictionary with counts
        """
        self.cleaned_patterns = []
        self.removed_empty = 0
        self.removed_framework = 0

        for pattern in self.patterns:
            # Remove empty purpose
            if not pattern.purpose or pattern.purpose.strip() == "":
                self.removed_empty += 1
                continue

            # Filter by framework
            if framework_filter and pattern.framework != framework_filter:
                self.removed_framework += 1
                continue

            self.cleaned_patterns.append(pattern)

        return {
            "total_before": len(self.patterns),
            "removed_empty": self.removed_empty,
            "removed_framework": self.removed_framework,
            "total_after": len(self.cleaned_patterns)
        }

    def get_cleaned_patterns(self) -> List[MockPattern]:
        """Get cleaned patterns after audit."""
        return self.cleaned_patterns


# Tests

def test_identifies_empty_purpose_patterns():
    """Test that patterns with empty purpose are identified."""
    patterns = [
        MockPattern("p1", "Valid purpose", "fastapi"),
        MockPattern("p2", "", "fastapi"),  # Empty purpose
        MockPattern("p3", "   ", "fastapi"),  # Whitespace only
        MockPattern("p4", "Another valid", "fastapi"),
    ]

    auditor = PatternAuditor(patterns)
    stats = auditor.audit(framework_filter="fastapi")

    assert stats["removed_empty"] == 2
    assert stats["total_after"] == 2

    # Verify only valid patterns remain
    cleaned = auditor.get_cleaned_patterns()
    assert all(p.purpose.strip() != "" for p in cleaned)


def test_framework_filtering_works():
    """Test that framework filtering works correctly."""
    patterns = [
        MockPattern("p1", "FastAPI endpoint", "fastapi"),
        MockPattern("p2", "React component", "nextjs"),
        MockPattern("p3", "FastAPI middleware", "fastapi"),
        MockPattern("p4", "Next.js page", "nextjs"),
        MockPattern("p5", "Django view", "django"),
    ]

    auditor = PatternAuditor(patterns)
    stats = auditor.audit(framework_filter="fastapi")

    assert stats["removed_framework"] == 3
    assert stats["total_after"] == 2

    # Verify only fastapi patterns remain
    cleaned = auditor.get_cleaned_patterns()
    assert all(p.framework == "fastapi" for p in cleaned)


def test_pattern_count_reporting():
    """Test that pattern count before/after is reported correctly."""
    patterns = [
        MockPattern("p1", "Valid", "fastapi"),
        MockPattern("p2", "", "fastapi"),  # Empty
        MockPattern("p3", "Valid", "nextjs"),  # Wrong framework
        MockPattern("p4", "Valid", "fastapi"),
    ]

    auditor = PatternAuditor(patterns)
    stats = auditor.audit(framework_filter="fastapi")

    assert stats["total_before"] == 4
    assert stats["removed_empty"] == 1
    assert stats["removed_framework"] == 1
    assert stats["total_after"] == 2

    # Verify math: before = after + removed_empty + removed_framework
    assert stats["total_before"] == (
        stats["total_after"] +
        stats["removed_empty"] +
        stats["removed_framework"]
    )


def test_clean_patterns_are_valid():
    """Test that cleaned patterns have valid purpose and framework."""
    patterns = [
        MockPattern("p1", "Valid purpose", "fastapi"),
        MockPattern("p2", "", "fastapi"),  # Invalid: empty
        MockPattern("p3", "   ", "nextjs"),  # Invalid: whitespace + wrong framework
        MockPattern("p4", "Another valid", "fastapi"),
        MockPattern("p5", "Valid nextjs", "nextjs"),  # Invalid: wrong framework
    ]

    auditor = PatternAuditor(patterns)
    auditor.audit(framework_filter="fastapi")
    cleaned = auditor.get_cleaned_patterns()

    # All cleaned patterns should have non-empty purpose
    for pattern in cleaned:
        assert pattern.purpose.strip() != "", f"Pattern {pattern.pattern_id} has empty purpose"

    # All cleaned patterns should match framework filter
    for pattern in cleaned:
        assert pattern.framework == "fastapi", f"Pattern {pattern.pattern_id} has wrong framework"

    # Verify count
    assert len(cleaned) == 2


def test_no_framework_filter_keeps_all_frameworks():
    """Test that omitting framework filter keeps all frameworks."""
    patterns = [
        MockPattern("p1", "FastAPI", "fastapi"),
        MockPattern("p2", "Next.js", "nextjs"),
        MockPattern("p3", "Django", "django"),
    ]

    auditor = PatternAuditor(patterns)
    stats = auditor.audit(framework_filter=None)

    assert stats["removed_framework"] == 0
    assert stats["total_after"] == 3


def test_empty_pattern_list():
    """Test audit with empty pattern list."""
    patterns = []

    auditor = PatternAuditor(patterns)
    stats = auditor.audit(framework_filter="fastapi")

    assert stats["total_before"] == 0
    assert stats["removed_empty"] == 0
    assert stats["removed_framework"] == 0
    assert stats["total_after"] == 0


def test_all_patterns_valid():
    """Test audit when all patterns are valid."""
    patterns = [
        MockPattern("p1", "Valid 1", "fastapi"),
        MockPattern("p2", "Valid 2", "fastapi"),
        MockPattern("p3", "Valid 3", "fastapi"),
    ]

    auditor = PatternAuditor(patterns)
    stats = auditor.audit(framework_filter="fastapi")

    assert stats["removed_empty"] == 0
    assert stats["removed_framework"] == 0
    assert stats["total_after"] == 3

    # All patterns should be preserved
    cleaned = auditor.get_cleaned_patterns()
    assert len(cleaned) == len(patterns)
