"""
Performance Monitor for System Metrics

Tracks and reports performance metrics across the multi-agent system.
Features:
- Execution time tracking
- Memory usage monitoring
- Token usage tracking
- Agent performance metrics
- Workflow bottleneck identification
"""

import time
import psutil
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    # Timing metrics
    total_execution_time: float = 0.0
    agent_execution_times: Dict[str, float] = field(default_factory=dict)
    task_execution_times: Dict[str, float] = field(default_factory=dict)

    # Token usage metrics
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    tokens_by_agent: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # System metrics
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0

    # Task metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0

    # Workflow metrics
    parallel_time_saved: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    # Timestamps
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def hit_rate(self) -> float:
        """Cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Task success rate."""
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties."""
        data = asdict(self)
        data.update({
            "total_tokens": self.total_tokens,
            "cache_hit_rate": self.hit_rate,
            "task_success_rate": self.success_rate
        })
        # Convert datetime to ISO string
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data


class PerformanceMonitor:
    """
    Monitors and tracks performance metrics across system execution.

    Usage:
        monitor = PerformanceMonitor()

        # Track agent execution
        with monitor.track_agent("ImplementationAgent") as timer:
            result = agent.execute(task, context)
            timer.record_tokens(input_tokens=100, output_tokens=500)

        # Track task execution
        with monitor.track_task("task_1"):
            execute_task()

        # Get metrics
        metrics = monitor.get_metrics()
        report = monitor.generate_report()
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics = PerformanceMetrics()
        self._cpu_samples: List[float] = []
        self._memory_samples: List[float] = []
        self._start_cpu_percent: Optional[float] = None

    def start(self):
        """Start monitoring session."""
        self.metrics.start_time = datetime.now()
        self._start_cpu_percent = psutil.cpu_percent(interval=None)

    def end(self):
        """End monitoring session."""
        self.metrics.end_time = datetime.now()

        # Calculate average CPU usage
        if self._cpu_samples:
            self.metrics.avg_cpu_percent = sum(self._cpu_samples) / len(self._cpu_samples)

        # Set peak memory
        if self._memory_samples:
            self.metrics.peak_memory_mb = max(self._memory_samples)

        # Calculate total execution time
        if self.metrics.start_time and self.metrics.end_time:
            delta = self.metrics.end_time - self.metrics.start_time
            self.metrics.total_execution_time = delta.total_seconds()

    @contextmanager
    def track_agent(self, agent_name: str):
        """
        Context manager for tracking agent execution.

        Args:
            agent_name: Name of the agent being tracked

        Yields:
            AgentTimer: Timer object with record_tokens method

        Usage:
            with monitor.track_agent("ImplementationAgent") as timer:
                result = agent.execute(task, context)
                timer.record_tokens(input_tokens=100, output_tokens=500)
        """
        class AgentTimer:
            def __init__(self, monitor, agent_name):
                self.monitor = monitor
                self.agent_name = agent_name
                self.start_time = None
                self.input_tokens = 0
                self.output_tokens = 0

            def record_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
                """Record token usage for this agent execution."""
                self.input_tokens = input_tokens
                self.output_tokens = output_tokens

        timer = AgentTimer(self, agent_name)
        start_time = time.time()

        # Sample system metrics
        self._sample_system_metrics()

        try:
            yield timer
        finally:
            elapsed = time.time() - start_time

            # Record timing
            if agent_name not in self.metrics.agent_execution_times:
                self.metrics.agent_execution_times[agent_name] = 0.0
            self.metrics.agent_execution_times[agent_name] += elapsed

            # Record tokens
            self.metrics.total_input_tokens += timer.input_tokens
            self.metrics.total_output_tokens += timer.output_tokens

            if agent_name not in self.metrics.tokens_by_agent:
                self.metrics.tokens_by_agent[agent_name] = {
                    "input": 0,
                    "output": 0
                }
            self.metrics.tokens_by_agent[agent_name]["input"] += timer.input_tokens
            self.metrics.tokens_by_agent[agent_name]["output"] += timer.output_tokens

    @contextmanager
    def track_task(self, task_id: str):
        """
        Context manager for tracking task execution.

        Args:
            task_id: ID of the task being tracked

        Usage:
            with monitor.track_task("task_1"):
                execute_task()
        """
        start_time = time.time()

        # Sample system metrics
        self._sample_system_metrics()

        try:
            yield
        finally:
            elapsed = time.time() - start_time
            self.metrics.task_execution_times[task_id] = elapsed

    def _sample_system_metrics(self):
        """Sample CPU and memory usage."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self._cpu_samples.append(cpu_percent)

        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self._memory_samples.append(memory_mb)

    def record_task_completion(self, success: bool, skipped: bool = False):
        """
        Record task completion status.

        Args:
            success: Whether task completed successfully
            skipped: Whether task was skipped
        """
        if skipped:
            self.metrics.tasks_skipped += 1
        elif success:
            self.metrics.tasks_completed += 1
        else:
            self.metrics.tasks_failed += 1

    def record_parallel_time_saved(self, time_saved: float):
        """
        Record time saved through parallel execution.

        Args:
            time_saved: Seconds saved by running tasks in parallel
        """
        self.metrics.parallel_time_saved += time_saved

    def record_cache_hit(self):
        """Record cache hit."""
        self.metrics.cache_hits += 1

    def record_cache_miss(self):
        """Record cache miss."""
        self.metrics.cache_misses += 1

    def get_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics.

        Returns:
            PerformanceMetrics object
        """
        return self.metrics

    def generate_report(self) -> str:
        """
        Generate human-readable performance report.

        Returns:
            Formatted report string
        """
        m = self.metrics

        report_lines = [
            "=" * 60,
            "PERFORMANCE REPORT",
            "=" * 60,
            "",
            "⏱️  TIMING METRICS",
            f"  Total execution time: {m.total_execution_time:.2f}s",
            f"  Parallel time saved: {m.parallel_time_saved:.2f}s",
            ""
        ]

        # Agent execution times
        if m.agent_execution_times:
            report_lines.append("  Agent execution times:")
            for agent, elapsed in sorted(m.agent_execution_times.items(),
                                        key=lambda x: x[1], reverse=True):
                report_lines.append(f"    {agent}: {elapsed:.2f}s")
            report_lines.append("")

        # Task metrics
        report_lines.extend([
            "📊 TASK METRICS",
            f"  Completed: {m.tasks_completed}",
            f"  Failed: {m.tasks_failed}",
            f"  Skipped: {m.tasks_skipped}",
            f"  Success rate: {m.success_rate:.1%}",
            ""
        ])

        # Token usage
        report_lines.extend([
            "🔤 TOKEN USAGE",
            f"  Input tokens: {m.total_input_tokens:,}",
            f"  Output tokens: {m.total_output_tokens:,}",
            f"  Total tokens: {m.total_tokens:,}",
            ""
        ])

        # Token usage by agent
        if m.tokens_by_agent:
            report_lines.append("  Tokens by agent:")
            for agent, tokens in sorted(m.tokens_by_agent.items(),
                                       key=lambda x: x[1]["input"] + x[1]["output"],
                                       reverse=True):
                total = tokens["input"] + tokens["output"]
                report_lines.append(
                    f"    {agent}: {total:,} "
                    f"(in: {tokens['input']:,}, out: {tokens['output']:,})"
                )
            report_lines.append("")

        # Cache performance
        if m.cache_hits > 0 or m.cache_misses > 0:
            report_lines.extend([
                "💾 CACHE PERFORMANCE",
                f"  Hits: {m.cache_hits}",
                f"  Misses: {m.cache_misses}",
                f"  Hit rate: {m.hit_rate:.1%}",
                ""
            ])

        # System metrics
        report_lines.extend([
            "💻 SYSTEM METRICS",
            f"  Peak memory: {m.peak_memory_mb:.1f} MB",
            f"  Avg CPU usage: {m.avg_cpu_percent:.1f}%",
            ""
        ])

        # Bottleneck identification
        bottlenecks = self._identify_bottlenecks()
        if bottlenecks:
            report_lines.extend([
                "⚠️  BOTTLENECKS IDENTIFIED",
                *[f"  {bottleneck}" for bottleneck in bottlenecks],
                ""
            ])

        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def _identify_bottlenecks(self) -> List[str]:
        """
        Identify performance bottlenecks.

        Returns:
            List of bottleneck descriptions
        """
        bottlenecks = []

        # Slow agents (>10s execution time)
        for agent, elapsed in self.metrics.agent_execution_times.items():
            if elapsed > 10.0:
                bottlenecks.append(
                    f"Slow agent: {agent} took {elapsed:.1f}s"
                )

        # Low cache hit rate (<30%)
        if self.metrics.cache_hits + self.metrics.cache_misses > 10:
            if self.metrics.hit_rate < 0.3:
                bottlenecks.append(
                    f"Low cache hit rate: {self.metrics.hit_rate:.1%}"
                )

        # High memory usage (>500MB)
        if self.metrics.peak_memory_mb > 500:
            bottlenecks.append(
                f"High memory usage: {self.metrics.peak_memory_mb:.1f} MB"
            )

        # High token usage (>100k tokens)
        if self.metrics.total_tokens > 100000:
            bottlenecks.append(
                f"High token usage: {self.metrics.total_tokens:,} tokens"
            )

        # Low task success rate (<80%)
        if self.metrics.tasks_completed + self.metrics.tasks_failed > 0:
            if self.metrics.success_rate < 0.8:
                bottlenecks.append(
                    f"Low success rate: {self.metrics.success_rate:.1%}"
                )

        return bottlenecks

    def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics in specified format.

        Args:
            format: Export format (json, csv)

        Returns:
            Formatted metrics string
        """
        if format == "json":
            import json
            return json.dumps(self.metrics.to_dict(), indent=2)
        elif format == "csv":
            # Simple CSV export for key metrics
            lines = [
                "metric,value",
                f"total_execution_time,{self.metrics.total_execution_time}",
                f"tasks_completed,{self.metrics.tasks_completed}",
                f"tasks_failed,{self.metrics.tasks_failed}",
                f"total_tokens,{self.metrics.total_tokens}",
                f"cache_hit_rate,{self.metrics.hit_rate}",
                f"peak_memory_mb,{self.metrics.peak_memory_mb}"
            ]
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def reset(self):
        """Reset all metrics."""
        self.metrics = PerformanceMetrics()
        self._cpu_samples.clear()
        self._memory_samples.clear()
        self._start_cpu_percent = None
