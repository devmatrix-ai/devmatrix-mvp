"""
Tests for PerformanceMonitor

Tests performance tracking and metrics collection.
"""

import pytest
import time
from unittest.mock import patch, Mock

from src.performance.performance_monitor import PerformanceMonitor, PerformanceMetrics


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass."""

    def test_initialization(self):
        """Test PerformanceMetrics initialization."""
        metrics = PerformanceMetrics()

        assert metrics.total_execution_time == 0.0
        assert metrics.agent_execution_times == {}
        assert metrics.task_execution_times == {}
        assert metrics.total_input_tokens == 0
        assert metrics.total_output_tokens == 0
        assert metrics.tokens_by_agent == {}
        assert metrics.peak_memory_mb == 0.0
        assert metrics.avg_cpu_percent == 0.0
        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 0
        assert metrics.tasks_skipped == 0
        assert metrics.parallel_time_saved == 0.0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0

    def test_total_tokens(self):
        """Test total tokens calculation."""
        metrics = PerformanceMetrics(
            total_input_tokens=1000,
            total_output_tokens=2000
        )
        assert metrics.total_tokens == 3000

    def test_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = PerformanceMetrics(cache_hits=80, cache_misses=20)
        assert metrics.hit_rate == 0.8

    def test_hit_rate_no_requests(self):
        """Test cache hit rate with no requests."""
        metrics = PerformanceMetrics()
        assert metrics.hit_rate == 0.0

    def test_success_rate(self):
        """Test task success rate calculation."""
        metrics = PerformanceMetrics(tasks_completed=8, tasks_failed=2)
        assert metrics.success_rate == 0.8

    def test_success_rate_no_tasks(self):
        """Test task success rate with no tasks."""
        metrics = PerformanceMetrics()
        assert metrics.success_rate == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from datetime import datetime
        start = datetime.now()
        end = datetime.now()

        metrics = PerformanceMetrics(
            total_execution_time=10.5,
            total_input_tokens=1000,
            total_output_tokens=2000,
            cache_hits=10,
            cache_misses=5,
            tasks_completed=8,
            tasks_failed=2,
            start_time=start,
            end_time=end
        )

        data = metrics.to_dict()

        assert data["total_execution_time"] == 10.5
        assert data["total_tokens"] == 3000
        assert pytest.approx(data["cache_hit_rate"], rel=1e-9) == 10 / 15
        assert data["task_success_rate"] == 0.8
        assert isinstance(data["start_time"], str)
        assert isinstance(data["end_time"], str)


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor."""

    @pytest.fixture
    def monitor(self):
        """Create PerformanceMonitor instance."""
        return PerformanceMonitor()

    def test_initialization(self, monitor):
        """Test PerformanceMonitor initialization."""
        assert isinstance(monitor.metrics, PerformanceMetrics)
        assert monitor._cpu_samples == []
        assert monitor._memory_samples == []

    def test_start_monitoring(self, monitor):
        """Test starting monitoring session."""
        monitor.start()

        assert monitor.metrics.start_time is not None

    def test_end_monitoring(self, monitor):
        """Test ending monitoring session."""
        monitor.start()
        time.sleep(0.1)
        monitor.end()

        assert monitor.metrics.end_time is not None
        assert monitor.metrics.total_execution_time > 0

    def test_track_agent_execution(self, monitor):
        """Test tracking agent execution."""
        with monitor.track_agent("TestAgent") as timer:
            time.sleep(0.1)
            timer.record_tokens(input_tokens=100, output_tokens=200)

        assert "TestAgent" in monitor.metrics.agent_execution_times
        assert monitor.metrics.agent_execution_times["TestAgent"] >= 0.1
        assert monitor.metrics.total_input_tokens == 100
        assert monitor.metrics.total_output_tokens == 200
        assert "TestAgent" in monitor.metrics.tokens_by_agent
        assert monitor.metrics.tokens_by_agent["TestAgent"]["input"] == 100
        assert monitor.metrics.tokens_by_agent["TestAgent"]["output"] == 200

    def test_track_multiple_agent_executions(self, monitor):
        """Test tracking multiple executions of same agent."""
        with monitor.track_agent("TestAgent") as timer:
            timer.record_tokens(input_tokens=100, output_tokens=200)

        with monitor.track_agent("TestAgent") as timer:
            timer.record_tokens(input_tokens=50, output_tokens=100)

        # Times should accumulate
        assert monitor.metrics.agent_execution_times["TestAgent"] > 0
        # Tokens should accumulate
        assert monitor.metrics.total_input_tokens == 150
        assert monitor.metrics.total_output_tokens == 300
        assert monitor.metrics.tokens_by_agent["TestAgent"]["input"] == 150
        assert monitor.metrics.tokens_by_agent["TestAgent"]["output"] == 300

    def test_track_task_execution(self, monitor):
        """Test tracking task execution."""
        with monitor.track_task("task_1"):
            time.sleep(0.1)

        assert "task_1" in monitor.metrics.task_execution_times
        assert monitor.metrics.task_execution_times["task_1"] >= 0.1

    def test_record_task_completion_success(self, monitor):
        """Test recording successful task completion."""
        monitor.record_task_completion(success=True)

        assert monitor.metrics.tasks_completed == 1
        assert monitor.metrics.tasks_failed == 0
        assert monitor.metrics.tasks_skipped == 0

    def test_record_task_completion_failure(self, monitor):
        """Test recording failed task completion."""
        monitor.record_task_completion(success=False)

        assert monitor.metrics.tasks_completed == 0
        assert monitor.metrics.tasks_failed == 1
        assert monitor.metrics.tasks_skipped == 0

    def test_record_task_completion_skipped(self, monitor):
        """Test recording skipped task."""
        monitor.record_task_completion(success=False, skipped=True)

        assert monitor.metrics.tasks_completed == 0
        assert monitor.metrics.tasks_failed == 0
        assert monitor.metrics.tasks_skipped == 1

    def test_record_parallel_time_saved(self, monitor):
        """Test recording parallel time saved."""
        monitor.record_parallel_time_saved(5.5)

        assert monitor.metrics.parallel_time_saved == 5.5

    def test_record_cache_hit(self, monitor):
        """Test recording cache hit."""
        monitor.record_cache_hit()

        assert monitor.metrics.cache_hits == 1
        assert monitor.metrics.cache_misses == 0

    def test_record_cache_miss(self, monitor):
        """Test recording cache miss."""
        monitor.record_cache_miss()

        assert monitor.metrics.cache_hits == 0
        assert monitor.metrics.cache_misses == 1

    def test_get_metrics(self, monitor):
        """Test getting current metrics."""
        monitor.record_task_completion(success=True)

        metrics = monitor.get_metrics()

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.tasks_completed == 1

    def test_generate_report(self, monitor):
        """Test generating performance report."""
        monitor.start()

        with monitor.track_agent("TestAgent") as timer:
            time.sleep(0.05)
            timer.record_tokens(input_tokens=1000, output_tokens=2000)

        monitor.record_task_completion(success=True)
        monitor.record_parallel_time_saved(2.5)
        monitor.record_cache_hit()
        monitor.record_cache_miss()

        monitor.end()

        report = monitor.generate_report()

        assert "PERFORMANCE REPORT" in report
        assert "TIMING METRICS" in report
        assert "TASK METRICS" in report
        assert "TOKEN USAGE" in report
        assert "CACHE PERFORMANCE" in report
        assert "SYSTEM METRICS" in report
        assert "TestAgent" in report

    def test_generate_report_no_cache_stats(self, monitor):
        """Test report generation without cache stats."""
        monitor.start()
        monitor.record_task_completion(success=True)
        monitor.end()

        report = monitor.generate_report()

        assert "CACHE PERFORMANCE" not in report

    def test_identify_bottlenecks_slow_agent(self, monitor):
        """Test bottleneck identification for slow agent."""
        monitor.metrics.agent_execution_times["SlowAgent"] = 15.0

        bottlenecks = monitor._identify_bottlenecks()

        assert len(bottlenecks) > 0
        assert any("Slow agent" in b for b in bottlenecks)

    def test_identify_bottlenecks_low_cache_hit_rate(self, monitor):
        """Test bottleneck identification for low cache hit rate."""
        monitor.metrics.cache_hits = 2
        monitor.metrics.cache_misses = 10

        bottlenecks = monitor._identify_bottlenecks()

        assert any("Low cache hit rate" in b for b in bottlenecks)

    def test_identify_bottlenecks_high_memory(self, monitor):
        """Test bottleneck identification for high memory usage."""
        monitor.metrics.peak_memory_mb = 600.0

        bottlenecks = monitor._identify_bottlenecks()

        assert any("High memory usage" in b for b in bottlenecks)

    def test_identify_bottlenecks_high_token_usage(self, monitor):
        """Test bottleneck identification for high token usage."""
        monitor.metrics.total_input_tokens = 80000
        monitor.metrics.total_output_tokens = 30000

        bottlenecks = monitor._identify_bottlenecks()

        assert any("High token usage" in b for b in bottlenecks)

    def test_identify_bottlenecks_low_success_rate(self, monitor):
        """Test bottleneck identification for low success rate."""
        monitor.metrics.tasks_completed = 6
        monitor.metrics.tasks_failed = 4

        bottlenecks = monitor._identify_bottlenecks()

        assert any("Low success rate" in b for b in bottlenecks)

    def test_export_metrics_json(self, monitor):
        """Test exporting metrics as JSON."""
        monitor.metrics.tasks_completed = 5
        monitor.metrics.total_input_tokens = 1000

        json_output = monitor.export_metrics(format="json")

        assert '"tasks_completed": 5' in json_output
        assert '"total_input_tokens": 1000' in json_output

    def test_export_metrics_csv(self, monitor):
        """Test exporting metrics as CSV."""
        monitor.metrics.tasks_completed = 5
        monitor.metrics.tasks_failed = 1
        monitor.metrics.total_execution_time = 10.5

        csv_output = monitor.export_metrics(format="csv")

        assert "metric,value" in csv_output
        assert "total_execution_time,10.5" in csv_output
        assert "tasks_completed,5" in csv_output
        assert "tasks_failed,1" in csv_output

    def test_export_metrics_unsupported_format(self, monitor):
        """Test exporting metrics with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            monitor.export_metrics(format="xml")

    def test_reset_metrics(self, monitor):
        """Test resetting all metrics."""
        monitor.metrics.tasks_completed = 10
        monitor.metrics.total_input_tokens = 5000
        monitor._cpu_samples = [50.0, 60.0]

        monitor.reset()

        assert monitor.metrics.tasks_completed == 0
        assert monitor.metrics.total_input_tokens == 0
        assert len(monitor._cpu_samples) == 0

    @patch('psutil.cpu_percent')
    @patch('psutil.Process')
    def test_sample_system_metrics(self, mock_process_class, mock_cpu_percent, monitor):
        """Test sampling system metrics."""
        # Mock CPU and memory
        mock_cpu_percent.return_value = 75.5
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100 MB
        mock_process_class.return_value = mock_process

        monitor._sample_system_metrics()

        assert len(monitor._cpu_samples) == 1
        assert monitor._cpu_samples[0] == 75.5
        assert len(monitor._memory_samples) == 1
        assert monitor._memory_samples[0] == 100.0

    @patch('psutil.cpu_percent')
    @patch('psutil.Process')
    def test_end_calculates_averages(self, mock_process_class, mock_cpu_percent, monitor):
        """Test that end() calculates average CPU and peak memory."""
        mock_cpu_percent.return_value = 50.0
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 50 * 1024 * 1024
        mock_process_class.return_value = mock_process

        monitor.start()

        # Sample metrics multiple times
        monitor._sample_system_metrics()
        monitor._cpu_samples.append(60.0)
        monitor._memory_samples.append(80.0)

        monitor.end()

        assert monitor.metrics.avg_cpu_percent == pytest.approx(55.0)  # (50 + 60) / 2
        assert monitor.metrics.peak_memory_mb == 80.0  # max(50, 80)

    def test_nested_tracking(self, monitor):
        """Test nested tracking contexts."""
        with monitor.track_agent("OuterAgent") as timer1:
            timer1.record_tokens(input_tokens=100, output_tokens=200)

            with monitor.track_task("task_1"):
                time.sleep(0.05)

                with monitor.track_agent("InnerAgent") as timer2:
                    timer2.record_tokens(input_tokens=50, output_tokens=100)

        assert "OuterAgent" in monitor.metrics.agent_execution_times
        assert "InnerAgent" in monitor.metrics.agent_execution_times
        assert "task_1" in monitor.metrics.task_execution_times
        assert monitor.metrics.total_input_tokens == 150
        assert monitor.metrics.total_output_tokens == 300
