"""Session persistence and management for DevMatrix Console."""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Executed command record."""

    id: str
    timestamp: str
    command: str
    args: Dict[str, Any]
    output: str
    status: str  # success, error, warning
    duration_ms: float


@dataclass
class PipelineState:
    """Pipeline execution state snapshot."""

    timestamp: str
    current_task: str
    progress_percent: int
    tasks_completed: int
    tasks_total: int
    tree_state: Dict[str, Any]


class SessionManager:
    """Manages session persistence using SQLite."""

    def __init__(self, session_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            session_dir: Directory for session storage. Defaults to ~/.devmatrix/sessions/
        """
        self.session_dir = session_dir or Path.home() / ".devmatrix" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.session_dir / "sessions.db"
        self.current_session_id: Optional[str] = None
        self._init_db()
        logger.info(f"SessionManager initialized: {self.db_path}")

    def _init_db(self) -> None:
        """Initialize database schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Sessions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    project_path TEXT,
                    status TEXT DEFAULT 'active',
                    metadata JSON
                )
                """
            )

            # Commands history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    command TEXT NOT NULL,
                    args JSON,
                    output TEXT,
                    status TEXT,
                    duration_ms REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
                """
            )

            # Pipeline state snapshots
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pipeline_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    current_task TEXT,
                    progress_percent INTEGER,
                    tasks_completed INTEGER,
                    tasks_total INTEGER,
                    tree_state JSON,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
                """
            )

            # Indexes for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_commands_session ON commands(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pipeline_session ON pipeline_states(session_id)"
            )

            conn.commit()

    def create_session(self, project_path: Optional[str] = None) -> str:
        """Create a new session.

        Args:
            project_path: Optional project path to associate with session

        Returns:
            Session ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        session_id = f"{timestamp}_{unique_id}"
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (id, created_at, updated_at, project_path, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (session_id, now, now, project_path),
            )
            conn.commit()

        self.current_session_id = session_id
        logger.info(f"Session created: {session_id}")
        return session_id

    def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load session data.

        Args:
            session_id: ID of session to load

        Returns:
            Session data including commands and state
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get session metadata
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session = dict(cursor.fetchone() or {})

            # Get command history
            cursor.execute(
                "SELECT * FROM commands WHERE session_id = ? ORDER BY timestamp DESC LIMIT 100",
                (session_id,),
            )
            commands = [dict(row) for row in cursor.fetchall()]

            # Get latest pipeline state
            cursor.execute(
                """
                SELECT * FROM pipeline_states
                WHERE session_id = ?
                ORDER BY timestamp DESC LIMIT 1
                """,
                (session_id,),
            )
            latest_state = dict(cursor.fetchone() or {})

        self.current_session_id = session_id
        logger.info(f"Session loaded: {session_id}")

        return {"session": session, "commands": commands, "latest_state": latest_state}

    def save_command(
        self, command: str, args: Dict[str, Any], output: str, status: str, duration_ms: float
    ) -> str:
        """Save command execution record.

        Args:
            command: Command name
            args: Command arguments
            output: Command output
            status: success, error, warning
            duration_ms: Execution duration in milliseconds

        Returns:
            Command ID
        """
        if not self.current_session_id:
            raise RuntimeError("No active session")

        cmd_id = f"{self.current_session_id}_{datetime.now().timestamp()}"
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO commands (id, session_id, timestamp, command, args, output, status, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cmd_id,
                    self.current_session_id,
                    now,
                    command,
                    json.dumps(args),
                    output,
                    status,
                    duration_ms,
                ),
            )
            conn.commit()

        return cmd_id

    def save_pipeline_state(self, state: PipelineState) -> int:
        """Save pipeline state snapshot.

        Args:
            state: Pipeline state to save

        Returns:
            Record ID
        """
        if not self.current_session_id:
            raise RuntimeError("No active session")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pipeline_states
                (session_id, timestamp, current_task, progress_percent, tasks_completed, tasks_total, tree_state)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.current_session_id,
                    state.timestamp,
                    state.current_task,
                    state.progress_percent,
                    state.tasks_completed,
                    state.tasks_total,
                    json.dumps(state.tree_state),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, created_at, updated_at, project_path, status
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Remove sessions older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM sessions WHERE created_at < ?", (cutoff_date,))
            old_sessions = [row[0] for row in cursor.fetchall()]

            if old_sessions:
                placeholders = ",".join("?" * len(old_sessions))
                cursor.execute(f"DELETE FROM commands WHERE session_id IN ({placeholders})", old_sessions)
                cursor.execute(f"DELETE FROM pipeline_states WHERE session_id IN ({placeholders})", old_sessions)
                cursor.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", old_sessions)
                conn.commit()

        logger.info(f"Cleaned up {len(old_sessions)} old sessions")
        return len(old_sessions)

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            Session statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM commands WHERE session_id = ?", (session_id,)
            )
            command_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM pipeline_states WHERE session_id = ?", (session_id,)
            )
            state_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT status, COUNT(*) FROM commands WHERE session_id = ? GROUP BY status",
                (session_id,),
            )
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "session_id": session_id,
            "total_commands": command_count,
            "state_snapshots": state_count,
            "by_status": status_counts,
        }
