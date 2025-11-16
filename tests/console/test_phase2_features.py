"""Tests for Phase 2 features: tokens, artifacts, autocomplete, logging."""

import pytest
from src.console.token_tracker import TokenTracker, ModelPricing
from src.console.artifact_previewer import ArtifactPreviewer
from src.console.autocomplete import CommandAutocomplete, CommandHistory
from src.console.log_viewer import LogViewer, LogLevel
from src.console.command_dispatcher import CommandDispatcher


class TestTokenTracker:
    """Tests for token tracking."""

    def test_tracker_initialization(self):
        """Test token tracker initializes correctly."""
        tracker = TokenTracker(default_model="claude-opus-4", budget=100000)

        assert tracker.default_model == "claude-opus-4"
        assert tracker.budget == 100000
        assert tracker.metrics.total_tokens == 0

    def test_add_tokens(self):
        """Test adding token usage."""
        tracker = TokenTracker()

        tracker.add_tokens(100, 50, model="gpt-3.5-turbo", operation="test")

        assert tracker.metrics.total_tokens == 150
        assert tracker.metrics.prompt_tokens == 100
        assert tracker.metrics.completion_tokens == 50

    def test_cost_calculation(self):
        """Test cost calculation."""
        tracker = TokenTracker()

        # Add tokens for cheaper model
        tracker.add_tokens(1000, 1000, model="gpt-3.5-turbo")

        assert tracker.cost_metrics.total_cost > 0
        assert "gpt-3.5-turbo" in tracker.cost_metrics.by_model

    def test_budget_tracking(self):
        """Test budget tracking."""
        tracker = TokenTracker(budget=1000)

        tracker.add_tokens(600, 300)  # 900 tokens
        status = tracker.get_status()

        assert status["tokens"]["total"] == 900
        assert status["tokens"]["budget_percent"] is not None
        assert status["tokens"]["budget_percent"] > 80  # Should be 90%

    def test_budget_alert(self):
        """Test budget alert generation."""
        tracker = TokenTracker(budget=1000)

        tracker.add_tokens(950, 0)  # 950 tokens, 95% of budget
        status = tracker.get_status()

        assert len(status["alerts"]) > 0
        assert "90%" in status["alerts"][0]["message"]

    def test_cost_limit_tracking(self):
        """Test cost limit tracking."""
        tracker = TokenTracker(cost_limit=1.0)

        # Add enough tokens to exceed cost
        for _ in range(10):
            tracker.add_tokens(1000, 1000, model="claude-opus-4")

        status = tracker.get_status()
        assert status["cost"]["total"] > 0

    def test_model_pricing(self):
        """Test model pricing."""
        pricing = ModelPricing()

        cost = pricing.get_cost("claude-opus-4", 1000, 1000)
        assert cost > 0

        # Cheaper model should cost less
        cost_cheap = pricing.get_cost("gpt-3.5-turbo", 1000, 1000)
        assert cost_cheap < cost

    def test_export_metrics(self):
        """Test exporting metrics."""
        tracker = TokenTracker()

        tracker.add_tokens(100, 50, model="gpt-3.5-turbo")
        exported = tracker.export_metrics()

        assert exported["tokens"]["total"] == 150
        assert "gpt-3.5-turbo" in exported["by_model"]


class TestArtifactPreviewer:
    """Tests for artifact preview."""

    def test_previewer_initialization(self):
        """Test previewer initializes."""
        previewer = ArtifactPreviewer()

        assert len(previewer.artifacts) == 0
        assert previewer.max_preview_lines == 20

    def test_add_artifact(self):
        """Test adding artifact."""
        previewer = ArtifactPreviewer()

        previewer.add_artifact(
            path="/test/auth.py",
            file_type="file",
            size=1024,
            timestamp="2025-11-16T10:00:00",
            preview="def login():\n    pass",
        )

        assert "/test/auth.py" in previewer.artifacts
        assert previewer.artifacts["/test/auth.py"].size == 1024

    def test_language_detection(self):
        """Test language detection for code files."""
        previewer = ArtifactPreviewer()

        previewer.add_artifact("/test/auth.py", file_type="file")
        artifact = previewer.artifacts["/test/auth.py"]

        assert artifact.language == "python"

    def test_artifact_stats(self):
        """Test artifact statistics."""
        previewer = ArtifactPreviewer()

        previewer.add_artifact("/test/file1.py", size=1024)
        previewer.add_artifact("/test/file2.py", size=2048)

        stats = previewer.get_stats()
        assert stats["total_count"] == 2
        assert stats["total_size"] == 3072

    def test_format_size(self):
        """Test size formatting."""
        size_1k = ArtifactPreviewer._format_size(1024)
        size_1m = ArtifactPreviewer._format_size(1024 * 1024)

        assert "KB" in size_1k
        assert "MB" in size_1m

    def test_export_artifacts(self):
        """Test exporting artifacts."""
        previewer = ArtifactPreviewer()

        previewer.add_artifact("/test/auth.py", size=1024)
        exported = previewer.export_artifacts()

        assert len(exported) == 1
        assert exported[0]["path"] == "/test/auth.py"


class TestCommandAutocomplete:
    """Tests for command autocomplete."""

    def test_autocomplete_initialization(self):
        """Test autocomplete initializes."""
        dispatcher = CommandDispatcher()
        autocomplete = CommandAutocomplete(dispatcher)

        assert autocomplete.history is not None
        assert len(autocomplete.command_options) > 0

    def test_command_history(self):
        """Test command history."""
        history = CommandHistory()

        history.add("run feature_name")
        history.add("plan architecture")

        recent = history.get_recent(2)
        assert len(recent) == 2

    def test_history_search(self):
        """Test history search."""
        history = CommandHistory()

        history.add("run auth_feature")
        history.add("run test_feature")
        history.add("plan architecture")

        results = history.search("run")
        assert len(results) == 2

    def test_autocomplete_suggestions(self):
        """Test autocomplete suggestions."""
        dispatcher = CommandDispatcher()
        autocomplete = CommandAutocomplete(dispatcher)

        suggestions, prefix = autocomplete.complete("ru")
        assert "run" in suggestions

    def test_autocomplete_empty(self):
        """Test autocomplete with empty input."""
        dispatcher = CommandDispatcher()
        autocomplete = CommandAutocomplete(dispatcher)

        suggestions, prefix = autocomplete.complete("")
        assert "run" in suggestions
        assert "help" in suggestions

    def test_history_export(self):
        """Test exporting history."""
        dispatcher = CommandDispatcher()
        autocomplete = CommandAutocomplete(dispatcher)

        autocomplete.add_to_history("run feature", status="success")
        exported = autocomplete.export_history()

        assert len(exported) == 1
        assert exported[0]["command"] == "run feature"


class TestLogViewer:
    """Tests for advanced logging."""

    def test_log_viewer_initialization(self):
        """Test log viewer initializes."""
        viewer = LogViewer()

        assert len(viewer.logs) == 0

    def test_add_log(self):
        """Test adding log entry."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "Test message", source="test")

        assert len(viewer.logs) == 1
        assert viewer.logs[0].message == "Test message"

    def test_filter_by_level(self):
        """Test filtering by level."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "Info message")
        viewer.add_log(LogLevel.ERROR, "Error message")
        viewer.add_log(LogLevel.ERROR, "Another error")

        errors = viewer.filter_logs(level=LogLevel.ERROR)
        assert len(errors) == 2

    def test_filter_by_source(self):
        """Test filtering by source."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "msg1", source="api")
        viewer.add_log(LogLevel.INFO, "msg2", source="websocket")

        api_logs = viewer.filter_logs(source="api")
        assert len(api_logs) == 1

    def test_search_logs(self):
        """Test searching logs."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "Connection established")
        viewer.add_log(LogLevel.INFO, "Processing request")

        results = viewer.filter_logs(query="connection")
        assert len(results) == 1

    def test_log_stats(self):
        """Test log statistics."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "msg1")
        viewer.add_log(LogLevel.ERROR, "msg2")
        viewer.add_log(LogLevel.WARN, "msg3")

        stats = viewer.get_stats()
        assert stats["total_logs"] == 3
        assert stats["by_level"]["ERROR"] == 1
        assert stats["by_level"]["WARN"] == 1

    def test_error_logs_retrieval(self):
        """Test getting error logs."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "info")
        viewer.add_log(LogLevel.ERROR, "error1")
        viewer.add_log(LogLevel.ERROR, "error2")

        errors = viewer.get_error_logs()
        assert len(errors) == 2

    def test_export_logs(self):
        """Test exporting logs."""
        viewer = LogViewer()

        viewer.add_log(LogLevel.INFO, "Test log", source="test")
        exported = viewer.export_logs()

        assert len(exported) == 1
        assert exported[0]["message"] == "Test log"
        assert exported[0]["level"] == "INFO"
