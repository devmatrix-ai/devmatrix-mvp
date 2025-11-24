"""
Unit tests for adaptive threshold functionality (TG4).

Tests domain-specific threshold selection for pattern matching.
"""

import pytest
from src.cognitive.inference.cpie import get_adaptive_threshold


class TestAdaptiveThresholds:
    """Test adaptive threshold selection based on requirement domain."""

    def test_crud_threshold_is_lower(self):
        """CRUD requirements should get lower threshold (0.60) for simple patterns."""
        threshold = get_adaptive_threshold("crud")
        assert threshold == 0.60

    def test_payment_threshold_is_higher(self):
        """Payment requirements should get higher threshold (0.70) for complex patterns."""
        threshold = get_adaptive_threshold("payment")
        assert threshold == 0.70

    def test_custom_threshold_is_medium(self):
        """Custom requirements should get medium threshold (0.65)."""
        threshold = get_adaptive_threshold("custom")
        assert threshold == 0.65

    def test_workflow_threshold_is_medium(self):
        """Workflow requirements should get medium threshold (0.65)."""
        threshold = get_adaptive_threshold("workflow")
        assert threshold == 0.65

    def test_unknown_domain_gets_default(self):
        """Unknown domains should get default threshold (0.60)."""
        threshold = get_adaptive_threshold("unknown_domain")
        assert threshold == 0.60

    def test_empty_domain_gets_default(self):
        """Empty domain should get default threshold (0.60)."""
        threshold = get_adaptive_threshold("")
        assert threshold == 0.60

    def test_none_domain_gets_default(self):
        """None domain should get default threshold (0.60)."""
        threshold = get_adaptive_threshold(None)
        assert threshold == 0.60

    def test_threshold_selection_is_consistent(self):
        """Multiple calls with same domain should return same threshold."""
        threshold1 = get_adaptive_threshold("crud")
        threshold2 = get_adaptive_threshold("crud")
        assert threshold1 == threshold2
