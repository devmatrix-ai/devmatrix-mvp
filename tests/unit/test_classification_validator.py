"""
Unit tests for classification validation functionality

Task Group 1.1: Focused tests for classification validation
Tests cover core validation logic only, not exhaustive edge cases.
"""
import pytest
from tests.e2e.precision_metrics import validate_classification


class TestClassificationValidator:
    """Test classification validation logic"""

    def test_classification_matches_expected_domain(self):
        """Classification validator matches expected domain"""
        actual = {"domain": "crud", "risk": "low"}
        expected = {"domain": "crud", "risk": "low"}

        result = validate_classification(actual, expected)

        assert result is True

    def test_classification_matches_expected_risk(self):
        """Classification validator matches expected risk"""
        actual = {"domain": "payment", "risk": "high"}
        expected = {"domain": "payment", "risk": "high"}

        result = validate_classification(actual, expected)

        assert result is True

    def test_classification_fails_on_wrong_domain(self):
        """Classification validator detects wrong domain"""
        actual = {"domain": "workflow", "risk": "medium"}
        expected = {"domain": "crud", "risk": "medium"}

        result = validate_classification(actual, expected)

        assert result is False

    def test_classification_fails_on_wrong_risk(self):
        """Classification validator detects wrong risk level"""
        actual = {"domain": "crud", "risk": "high"}
        expected = {"domain": "crud", "risk": "low"}

        result = validate_classification(actual, expected)

        assert result is False

    def test_classification_handles_missing_ground_truth(self):
        """Classification validator handles missing ground truth gracefully"""
        actual = {"domain": "crud", "risk": "low"}
        expected = None

        result = validate_classification(actual, expected)

        # Should return True when no ground truth is available
        assert result is True

    def test_classification_handles_empty_ground_truth(self):
        """Classification validator handles empty ground truth dict"""
        actual = {"domain": "crud", "risk": "low"}
        expected = {}

        result = validate_classification(actual, expected)

        # Should return True when ground truth is empty
        assert result is True

    def test_classification_accuracy_calculation(self):
        """Classification accuracy calculation is correct"""
        # Test data: 3 correct, 2 incorrect out of 5 total
        classifications = [
            ({"domain": "crud", "risk": "low"}, {"domain": "crud", "risk": "low"}),      # Correct
            ({"domain": "workflow", "risk": "medium"}, {"domain": "workflow", "risk": "medium"}),  # Correct
            ({"domain": "payment", "risk": "high"}, {"domain": "payment", "risk": "high"}),  # Correct
            ({"domain": "crud", "risk": "high"}, {"domain": "crud", "risk": "low"}),     # Wrong risk
            ({"domain": "workflow", "risk": "low"}, {"domain": "payment", "risk": "high"}),  # Wrong both
        ]

        correct = sum(1 for actual, expected in classifications if validate_classification(actual, expected))
        total = len(classifications)
        accuracy = correct / total

        assert correct == 3
        assert total == 5
        assert accuracy == 0.6  # 60% accuracy

    def test_classification_with_missing_domain_field(self):
        """Classification validator handles missing domain field in actual"""
        actual = {"risk": "low"}  # Missing 'domain'
        expected = {"domain": "crud", "risk": "low"}

        result = validate_classification(actual, expected)

        # Should return False when actual is missing required field
        assert result is False
