"""
Unit tests for GateValidator

Tests Gate S validation logic without database access.
"""
import pytest

from src.testing.gate_validator import GateValidator


class TestGateValidator:
    """Test GateValidator functionality"""

    def test_init_thresholds(self):
        """Test validator initializes with correct thresholds"""
        validator = GateValidator()
        assert validator.must_threshold == 1.0  # 100%
        assert validator.should_threshold == 0.95  # 95%

    def test_gate_passes_100_must_100_should(self):
        """Test gate passes with 100% MUST and 100% SHOULD"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=1.0,
            should_pass_rate=1.0
        )

        assert result['passed'] is True
        assert "Gate S PASSED" in result['message']
        assert len(result['failures']) == 0
        assert "100.0%" in result['message']

    def test_gate_passes_100_must_95_should(self):
        """Test gate passes with 100% MUST and exactly 95% SHOULD"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=1.0,
            should_pass_rate=0.95
        )

        assert result['passed'] is True
        assert "Gate S PASSED" in result['message']
        assert len(result['failures']) == 0
        assert "95.0%" in result['message']

    def test_gate_fails_must_below_threshold(self):
        """Test gate fails when MUST < 100%"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=0.99,  # 99%
            should_pass_rate=1.0
        )

        assert result['passed'] is False
        assert "Gate S FAILED" in result['message']
        assert len(result['failures']) == 1
        assert "MUST pass rate" in result['failures'][0]
        assert "99.0%" in result['failures'][0]
        assert "100.0%" in result['failures'][0]

    def test_gate_fails_should_below_threshold(self):
        """Test gate fails when SHOULD < 95%"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=1.0,
            should_pass_rate=0.94  # 94%
        )

        assert result['passed'] is False
        assert "Gate S FAILED" in result['message']
        assert len(result['failures']) == 1
        assert "SHOULD pass rate" in result['failures'][0]
        assert "94.0%" in result['failures'][0]
        assert "95.0%" in result['failures'][0]

    def test_gate_fails_both_below_threshold(self):
        """Test gate fails when both MUST and SHOULD are below thresholds"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=0.90,  # 90%
            should_pass_rate=0.85  # 85%
        )

        assert result['passed'] is False
        assert "Gate S FAILED" in result['message']
        assert len(result['failures']) == 2
        assert any("MUST pass rate" in f for f in result['failures'])
        assert any("SHOULD pass rate" in f for f in result['failures'])

    def test_gate_edge_case_zero_rates(self):
        """Test gate with 0% pass rates"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=0.0,
            should_pass_rate=0.0
        )

        assert result['passed'] is False
        assert len(result['failures']) == 2
        assert "0.0%" in result['message']

    def test_gate_edge_case_just_below_should_threshold(self):
        """Test gate with SHOULD just below 95% threshold"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=1.0,
            should_pass_rate=0.9499  # Just below 95%
        )

        assert result['passed'] is False
        assert len(result['failures']) == 1
        assert "SHOULD pass rate" in result['failures'][0]

    def test_gate_message_format_pass(self):
        """Test gate message format when passing"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=1.0,
            should_pass_rate=0.98
        )

        assert "Gate S PASSED" in result['message']
        assert "MUST 100.0%" in result['message']
        assert "SHOULD 98.0%" in result['message']

    def test_gate_message_format_fail(self):
        """Test gate message format when failing"""
        validator = GateValidator()
        result = validator.validate_gate_s(
            must_pass_rate=0.95,
            should_pass_rate=0.90
        )

        assert "Gate S FAILED" in result['message']
        assert "MUST 95.0%" in result['message']
        assert "SHOULD 90.0%" in result['message']
