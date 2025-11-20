"""
Test Suite for PipelineMetrics Extension (Task Group 2)

Tests for new repair-related fields added to PipelineMetrics dataclass.
Following TDD approach: write tests first, then extend dataclass.
"""

import pytest
from tests.e2e.metrics_framework import PipelineMetrics


class TestPipelineMetricsRepairFields:
    """Tests for repair-related fields in PipelineMetrics (Task Group 2.1)"""

    def test_metrics_initialization_with_defaults(self):
        """Test that new repair fields initialize with correct default values"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec"
        )

        # All new fields should have default values
        assert metrics.repair_applied is False
        assert metrics.repair_iterations == 0
        assert metrics.repair_improvement == 0.0
        assert metrics.tests_fixed == 0
        assert metrics.regressions_detected == 0
        assert metrics.pattern_reuse_count == 0
        assert metrics.repair_time_ms == 0.0
        assert metrics.repair_skipped is False
        assert metrics.repair_skip_reason == ""

    def test_metrics_initialization_with_repair_values(self):
        """Test that repair fields can be set during initialization"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec",
            repair_applied=True,
            repair_iterations=3,
            repair_improvement=0.25,
            tests_fixed=5,
            regressions_detected=1,
            pattern_reuse_count=2,
            repair_time_ms=15000.0,
            repair_skipped=False,
            repair_skip_reason=""
        )

        assert metrics.repair_applied is True
        assert metrics.repair_iterations == 3
        assert metrics.repair_improvement == 0.25
        assert metrics.tests_fixed == 5
        assert metrics.regressions_detected == 1
        assert metrics.pattern_reuse_count == 2
        assert metrics.repair_time_ms == 15000.0
        assert metrics.repair_skipped is False
        assert metrics.repair_skip_reason == ""

    def test_metrics_serialization_includes_repair_fields(self):
        """Test that to_dict() includes all new repair fields"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec",
            repair_applied=True,
            repair_iterations=2,
            repair_improvement=0.15,
            tests_fixed=3,
            regressions_detected=0,
            pattern_reuse_count=1,
            repair_time_ms=12000.0,
            repair_skipped=False,
            repair_skip_reason=""
        )

        metrics_dict = metrics.to_dict()

        # Verify all repair fields are in serialized output
        assert "repair_applied" in metrics_dict
        assert "repair_iterations" in metrics_dict
        assert "repair_improvement" in metrics_dict
        assert "tests_fixed" in metrics_dict
        assert "regressions_detected" in metrics_dict
        assert "pattern_reuse_count" in metrics_dict
        assert "repair_time_ms" in metrics_dict
        assert "repair_skipped" in metrics_dict
        assert "repair_skip_reason" in metrics_dict

        # Verify values are correct
        assert metrics_dict["repair_applied"] is True
        assert metrics_dict["repair_iterations"] == 2
        assert metrics_dict["repair_improvement"] == 0.15
        assert metrics_dict["tests_fixed"] == 3
        assert metrics_dict["regressions_detected"] == 0
        assert metrics_dict["pattern_reuse_count"] == 1
        assert metrics_dict["repair_time_ms"] == 12000.0
        assert metrics_dict["repair_skipped"] is False
        assert metrics_dict["repair_skip_reason"] == ""

    def test_metrics_backward_compatibility(self):
        """Test that existing code creating PipelineMetrics without repair fields still works"""
        # This simulates existing code that creates PipelineMetrics
        # without knowing about the new repair fields
        metrics = PipelineMetrics(
            pipeline_id="legacy_pipeline",
            spec_name="legacy_spec"
        )

        # Should work without errors
        assert metrics.pipeline_id == "legacy_pipeline"
        assert metrics.spec_name == "legacy_spec"

        # New fields should have defaults
        assert metrics.repair_applied is False
        assert metrics.repair_iterations == 0

    def test_metrics_skip_scenario(self):
        """Test metrics when repair phase is skipped"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec",
            repair_skipped=True,
            repair_skip_reason="Compliance 0.85 exceeds threshold 0.80"
        )

        assert metrics.repair_skipped is True
        assert metrics.repair_skip_reason == "Compliance 0.85 exceeds threshold 0.80"
        assert metrics.repair_applied is False  # Not applied when skipped
        assert metrics.repair_iterations == 0  # No iterations when skipped

    def test_metrics_regression_detection_scenario(self):
        """Test metrics when regressions are detected during repair"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec",
            repair_applied=True,
            repair_iterations=3,
            repair_improvement=0.10,  # Some improvement
            tests_fixed=4,
            regressions_detected=2,  # 2 rollbacks
            pattern_reuse_count=1,
            repair_time_ms=20000.0
        )

        assert metrics.regressions_detected == 2
        assert metrics.repair_iterations == 3
        assert metrics.repair_improvement > 0  # Still some improvement

    def test_metrics_pattern_reuse_scenario(self):
        """Test metrics when RAG patterns are reused"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec",
            repair_applied=True,
            repair_iterations=2,
            pattern_reuse_count=3,  # 3 patterns reused from RAG
            repair_improvement=0.20
        )

        assert metrics.pattern_reuse_count == 3
        assert metrics.repair_improvement == 0.20

    def test_metrics_dashboard_compatibility(self):
        """Test that serialized metrics are compatible with dashboard format"""
        metrics = PipelineMetrics(
            pipeline_id="test_pipeline",
            spec_name="test_spec",
            repair_applied=True,
            repair_iterations=2,
            repair_improvement=0.18,
            tests_fixed=6,
            regressions_detected=1,
            pattern_reuse_count=2,
            repair_time_ms=14500.0,
            repair_skipped=False,
            repair_skip_reason=""
        )

        metrics_dict = metrics.to_dict()

        # Dashboard requires all fields to be JSON-serializable
        import json
        try:
            json_str = json.dumps(metrics_dict, default=str)
            assert json_str is not None
            assert len(json_str) > 0
        except (TypeError, ValueError) as e:
            pytest.fail(f"Metrics dict is not JSON-serializable: {e}")

        # Dashboard requires timestamp field
        assert "timestamp" in metrics_dict
