"""Tests for session manager."""

import pytest
import tempfile
from pathlib import Path
from src.console.session_manager import SessionManager, PipelineState


@pytest.fixture
def temp_session_dir():
    """Create temporary session directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_session_manager_initialization(temp_session_dir):
    """Test session manager initializes correctly."""
    manager = SessionManager(temp_session_dir)
    assert manager.session_dir == temp_session_dir
    assert manager.db_path.exists()


def test_create_session(temp_session_dir):
    """Test creating a new session."""
    manager = SessionManager(temp_session_dir)
    session_id = manager.create_session("/some/project")

    assert session_id is not None
    assert manager.current_session_id == session_id


def test_list_sessions(temp_session_dir):
    """Test listing sessions."""
    manager = SessionManager(temp_session_dir)
    manager.create_session("/project1")
    manager.create_session("/project2")

    sessions = manager.list_sessions()
    assert len(sessions) >= 2


def test_save_command(temp_session_dir):
    """Test saving command execution."""
    manager = SessionManager(temp_session_dir)
    session_id = manager.create_session()

    cmd_id = manager.save_command(
        command="run",
        args={"task": "test"},
        output="Success",
        status="success",
        duration_ms=100.5,
    )

    assert cmd_id is not None


def test_save_command_without_session(temp_session_dir):
    """Test saving command without active session raises error."""
    manager = SessionManager(temp_session_dir)

    with pytest.raises(RuntimeError):
        manager.save_command(
            command="run",
            args={},
            output="",
            status="success",
            duration_ms=0,
        )


def test_save_pipeline_state(temp_session_dir):
    """Test saving pipeline state."""
    manager = SessionManager(temp_session_dir)
    manager.create_session()

    state = PipelineState(
        timestamp="2025-11-16T10:00:00",
        current_task="test_task",
        progress_percent=50,
        tasks_completed=2,
        tasks_total=4,
        tree_state={"root": "test"},
    )

    record_id = manager.save_pipeline_state(state)
    assert record_id is not None


def test_load_session(temp_session_dir):
    """Test loading a session."""
    manager = SessionManager(temp_session_dir)
    session_id = manager.create_session("/project")
    manager.save_command("test", {}, "output", "success", 10.0)

    # Create new manager instance and load session
    manager2 = SessionManager(temp_session_dir)
    session_data = manager2.load_session(session_id)

    assert session_data["session"]["id"] == session_id
    assert len(session_data["commands"]) > 0


def test_get_session_stats(temp_session_dir):
    """Test getting session statistics."""
    manager = SessionManager(temp_session_dir)
    session_id = manager.create_session()

    manager.save_command("run", {}, "output", "success", 10.0)
    manager.save_command("test", {}, "output", "error", 5.0)

    stats = manager.get_session_stats(session_id)
    assert stats["total_commands"] == 2
    assert "success" in stats["by_status"]
    assert "error" in stats["by_status"]


def test_cleanup_old_sessions(temp_session_dir):
    """Test cleaning up old sessions."""
    manager = SessionManager(temp_session_dir)
    manager.create_session()

    # Create a session and immediately clean up
    count = manager.cleanup_old_sessions(days=0)
    # Should delete at least the one we just created
    assert count >= 1
