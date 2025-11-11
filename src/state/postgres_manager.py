"""
PostgreSQL State Manager

Manages persistent state in PostgreSQL for audit trails, analytics, and learning.
Stores: projects, tasks, decisions, git commits, cost tracking.
"""

import os
from typing import Any, Optional
from src.observability import get_logger
from datetime import datetime
from uuid import UUID, uuid4

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PostgresManager:
    """
    Manages persistent state in PostgreSQL.

    Usage:
        manager = PostgresManager()
        task_id = manager.create_task(project_id, "planning", "Generate spec")
        manager.update_task_status(task_id, "completed")
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
    ):
        """
        Initialize PostgreSQL connection.

        Args:
            host: Database host (defaults to env POSTGRES_HOST)
            port: Database port (defaults to env POSTGRES_PORT)
            database: Database name (defaults to env POSTGRES_DB)
            user: Database user (defaults to env POSTGRES_USER)
            password: Database password (defaults to env POSTGRES_PASSWORD)
        """
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(port or os.getenv("POSTGRES_PORT", 5432))
        self.database = database or os.getenv("POSTGRES_DB", "devmatrix")
        self.user = user or os.getenv("POSTGRES_USER", "devmatrix")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "devmatrix")

        # Initialize logger
        self.logger = get_logger(__name__)

        # Create connection
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor,  # Return rows as dicts
            )
            self.conn.autocommit = False  # Use transactions

        except psycopg2.Error as e:
            raise ConnectionError(
                f"Failed to connect to PostgreSQL at {self.host}:{self.port}"
            ) from e

    def _execute(
        self,
        query: str,
        params: tuple = None,
        fetch: bool = False,
        operation: str = "unknown"
    ) -> Any:
        """
        Execute SQL query with contextual error handling and logging.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            operation: Human-readable operation name for logging

        Returns:
            Query results if fetch=True, None otherwise
        """
        # Extract operation type from query if not provided
        if operation == "unknown":
            query_lower = query.strip().lower()
            if query_lower.startswith("insert"):
                operation = "insert"
            elif query_lower.startswith("update"):
                operation = "update"
            elif query_lower.startswith("delete"):
                operation = "delete"
            elif query_lower.startswith("select"):
                operation = "select"
            else:
                operation = "query"

        try:
            with self.conn.cursor() as cursor:
                # Log query execution for debugging
                self.logger.debug(
                    "Executing database operation",
                    operation=operation,
                    fetch=fetch
                )

                cursor.execute(query, params)

                if fetch:
                    results = cursor.fetchall()
                    self.conn.commit()  # Commit even when fetching results
                    self.logger.debug(
                        "Query executed successfully",
                        operation=operation,
                        rows_returned=len(results)
                    )
                    return results

                self.conn.commit()
                self.logger.debug(
                    "Transaction committed successfully",
                    operation=operation
                )
                return None

        except psycopg2.Error as e:
            self.conn.rollback()

            # Contextual error logging with useful information
            error_context = {
                "operation": operation,
                "error_type": type(e).__name__,
                "error_code": getattr(e, 'pgcode', None),
                "error_message": str(e),
                "query_type": query.strip().split()[0].upper() if query else "UNKNOWN"
            }

            # Add parameter info if available (but sanitize sensitive data)
            if params:
                # Don't log passwords or sensitive data
                safe_params = []
                for p in params:
                    if isinstance(p, str) and len(p) > 50:
                        safe_params.append(f"{p[:20]}...{p[-10:]}")
                    else:
                        safe_params.append(str(p)[:50])
                error_context["params_preview"] = safe_params

            self.logger.error(
                "Database transaction failed and rolled back",
                **error_context
            )
            raise

    # ========================================
    # Project Operations
    # ========================================

    def create_project(
        self, name: str, description: str = ""
    ) -> UUID:
        """
        Create a new project.

        Args:
            name: Project name
            description: Project description

        Returns:
            Project UUID
        """
        query = """
            INSERT INTO devmatrix.projects (name, description, status)
            VALUES (%s, %s, 'in_progress')
            RETURNING id
        """

        result = self._execute(
            query,
            (name, description),
            fetch=True,
            operation=f"create_project:{name}"
        )
        return result[0]["id"]

    def get_project(self, project_id: UUID) -> Optional[dict]:
        """
        Retrieve project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project dict if found, None otherwise
        """
        query = """
            SELECT * FROM devmatrix.projects
            WHERE id = %s
        """

        results = self._execute(
            query,
            (str(project_id),),
            fetch=True,
            operation=f"get_project:{project_id}"
        )
        return results[0] if results else None

    # ========================================
    # Task Operations
    # ========================================

    def create_task(
        self,
        project_id: UUID,
        agent_name: str,
        task_type: str,
        input_data: dict = None,
    ) -> UUID:
        """
        Create a new task.

        Args:
            project_id: Project UUID
            agent_name: Name of the agent executing the task
            task_type: Type of task (e.g., "planning", "code_generation")
            input_data: Task input data

        Returns:
            Task UUID
        """
        query = """
            INSERT INTO devmatrix.tasks
            (project_id, agent_name, task_type, status, input, metadata)
            VALUES (%s, %s, %s, 'pending', %s, %s)
            RETURNING id
        """

        import json as json_lib
        input_text = json_lib.dumps(input_data) if input_data else ""

        result = self._execute(
            query,
            (str(project_id), agent_name, task_type, input_text, Json({})),
            fetch=True,
            operation=f"create_task:{task_type}:{agent_name}"
        )
        return result[0]["id"]

    def update_task_status(
        self,
        task_id: UUID,
        status: str,
        output_data: dict = None,
        error: str = None,
    ) -> bool:
        """
        Update task status and output.

        Args:
            task_id: Task UUID
            status: New status (pending, running, completed, failed)
            output_data: Task output data
            error: Error message if failed

        Returns:
            True if updated, False otherwise
        """
        query = """
            UPDATE devmatrix.tasks
            SET status = %s,
                output = COALESCE(%s, output),
                completed_at = CASE
                    WHEN %s IN ('completed', 'failed') THEN NOW()
                    ELSE completed_at
                END
            WHERE id = %s
        """

        import json as json_lib
        output_text = json_lib.dumps(output_data) if output_data else None

        try:
            self._execute(
                query,
                (
                    status,
                    output_text,
                    status,
                    str(task_id),
                ),
                operation=f"update_task_status:{task_id}:{status}"
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to update task status",
                task_id=str(task_id),
                status=status,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    def get_task(self, task_id: UUID) -> Optional[dict]:
        """
        Retrieve task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task dict if found, None otherwise
        """
        query = """
            SELECT * FROM devmatrix.tasks
            WHERE id = %s
        """

        results = self._execute(
            query,
            (str(task_id),),
            fetch=True,
            operation=f"get_task:{task_id}"
        )
        return results[0] if results else None

    def get_project_tasks(self, project_id: UUID) -> list[dict]:
        """
        Get all tasks for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of task dicts
        """
        query = """
            SELECT * FROM devmatrix.tasks
            WHERE project_id = %s
            ORDER BY created_at DESC
        """

        return self._execute(
            query,
            (str(project_id),),
            fetch=True,
            operation=f"get_project_tasks:{project_id}"
        )

    # ========================================
    # Cost Tracking
    # ========================================

    def track_cost(
        self,
        task_id: UUID,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> UUID:
        """
        Track LLM API cost for a task.

        Args:
            task_id: Task UUID
            model_name: LLM model name
            input_tokens: Input token count
            output_tokens: Output token count
            cost_usd: Cost in USD (schema uses total_cost_usd)

        Returns:
            Cost tracking entry UUID
        """
        query = """
            INSERT INTO devmatrix.cost_tracking
            (task_id, model_name, input_tokens, output_tokens, total_cost_usd)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """

        result = self._execute(
            query,
            (
                str(task_id),
                model_name,
                input_tokens,
                output_tokens,
                cost_usd,
            ),
            fetch=True,
            operation=f"track_cost:{model_name}:${cost_usd:.4f}"
        )
        return result[0]["id"]

    def get_project_costs(self, project_id: UUID) -> dict[str, Any]:
        """
        Get cost summary for a project.

        Args:
            project_id: Project UUID

        Returns:
            Cost summary dict
        """
        query = """
            SELECT
                SUM(ct.total_cost_usd) as total_cost,
                SUM(ct.input_tokens) as total_input_tokens,
                SUM(ct.output_tokens) as total_output_tokens,
                COUNT(*) as api_calls
            FROM devmatrix.cost_tracking ct
            JOIN devmatrix.tasks t ON ct.task_id = t.id
            WHERE t.project_id = %s
        """

        results = self._execute(
            query,
            (str(project_id),),
            fetch=True,
            operation=f"get_project_costs:{project_id}"
        )
        return results[0] if results else {}

    def get_monthly_costs(self, year: int = None, month: int = None) -> dict[str, Any]:
        """
        Get monthly cost summary.

        Args:
            year: Year (defaults to current year)
            month: Month (defaults to current month)

        Returns:
            Monthly cost summary
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        query = """
            SELECT
                SUM(total_cost_usd) as total_cost,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                COUNT(*) as api_calls,
                model_name,
                COUNT(*) as calls_per_model
            FROM devmatrix.cost_tracking
            WHERE EXTRACT(YEAR FROM created_at) = %s
              AND EXTRACT(MONTH FROM created_at) = %s
            GROUP BY model_name
        """

        results = self._execute(
            query,
            (year, month),
            fetch=True,
            operation=f"get_monthly_costs:{year}-{month:02d}"
        )

        # Calculate totals
        total_cost = sum(r["total_cost"] or 0 for r in results)
        total_calls = sum(r["calls_per_model"] for r in results)

        return {
            "year": year,
            "month": month,
            "total_cost_usd": float(total_cost),
            "total_api_calls": total_calls,
            "by_model": results,
        }

    # ========================================
    # Agent Decisions
    # ========================================

    def log_decision(
        self,
        task_id: UUID,
        decision_type: str,
        reasoning: str,
        approved: bool = None,
        metadata: dict = None,
    ) -> UUID:
        """
        Log an agent decision.

        Args:
            task_id: Task UUID
            decision_type: Type of decision being made
            reasoning: Reasoning behind the decision
            approved: Whether decision was approved (optional)
            metadata: Additional metadata (optional)

        Returns:
            Decision UUID
        """
        query = """
            INSERT INTO devmatrix.agent_decisions
            (task_id, decision_type, reasoning, approved, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """

        result = self._execute(
            query,
            (
                str(task_id),
                decision_type,
                reasoning,
                approved,
                Json(metadata or {}),
            ),
            fetch=True,
            operation=f"log_decision:{decision_type}:{'approved' if approved else 'pending'}"
        )
        return result[0]["id"]

    # ========================================
    # Conversation Operations
    # ========================================

    def create_conversation(
        self,
        conversation_id: str,
        session_id: str,
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Create a new conversation.

        Args:
            conversation_id: Unique conversation identifier
            session_id: WebSocket session ID
            metadata: Additional conversation metadata
            user_id: User ID (optional). If not provided, uses demo user.

        Returns:
            Conversation ID

        Note:
            TEMPORARY: This method uses a fallback demo user (demo@devmatrix.com)
            when user_id is not provided. This is for development/demo purposes only.

            TODO (Phase 2 - WebSocket Authentication):
            - Implement JWT authentication for WebSocket connections
            - Extract user_id from authenticated WebSocket session
            - Remove demo user fallback
            - Enforce user_id requirement

            See: agent-os/specs/2025-10-26-phase-2-high-priority-security-reliability/
        """
        # Require authenticated user_id from WebSocket connection
        if user_id is None:
            raise ValueError(
                "user_id is required. WebSocket connection must be authenticated with JWT token."
            )

        query = """
            INSERT INTO conversations (conversation_id, user_id, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            ON CONFLICT (conversation_id) DO NOTHING
            RETURNING conversation_id
        """

        result = self._execute(
            query,
            (conversation_id, user_id),
            fetch=True,
            operation=f"create_conversation:{conversation_id}"
        )
        return result[0]["conversation_id"] if result else conversation_id

    def update_conversation_metadata(
        self,
        conversation_id: str,
        metadata: dict
    ):
        """
        Update conversation metadata.

        Args:
            conversation_id: Conversation identifier
            metadata: Updated metadata dictionary
        """
        query = """
            UPDATE conversations
            SET metadata = %s, updated_at = NOW()
            WHERE conversation_id = %s
        """

        self._execute(
            query,
            (Json(metadata), conversation_id),
            fetch=False,
            operation=f"update_conversation_metadata:{conversation_id}"
        )

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """
        Retrieve conversation by ID.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Conversation dict if found, None otherwise
        """
        query = """
            SELECT * FROM conversations
            WHERE conversation_id = %s
        """

        results = self._execute(
            query,
            (conversation_id,),
            fetch=True,
            operation=f"get_conversation:{conversation_id}"
        )
        return results[0] if results else None

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict = None,  # Accepted but not used (messages table has no metadata column)
    ) -> str:
        """
        Save a message to a conversation.

        Args:
            conversation_id: Conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional message metadata (accepted for API compatibility but not stored)

        Returns:
            Message ID (UUID as string)
        """
        import uuid

        message_id = str(uuid.uuid4())
        query = """
            INSERT INTO messages (message_id, conversation_id, role, content, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING message_id
        """

        result = self._execute(
            query,
            (message_id, conversation_id, role, content),
            fetch=True,
            operation=f"save_message:{conversation_id}:{role}"
        )
        return result[0]["message_id"]

    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> list[dict]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return

        Returns:
            List of message dicts ordered by creation time
        """
        query = """
            SELECT * FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """

        return self._execute(
            query,
            (conversation_id, limit),
            fetch=True,
            operation=f"get_conversation_messages:{conversation_id}"
        )

    def update_conversation(
        self,
        conversation_id: str,
        metadata: dict = None,
    ) -> bool:
        """
        Update conversation metadata.

        Args:
            conversation_id: Conversation identifier
            metadata: Updated metadata

        Returns:
            True if updated, False otherwise
        """
        query = """
            UPDATE conversations
            SET metadata = %s
            WHERE id = %s
        """

        try:
            self._execute(
                query,
                (Json(metadata or {}), conversation_id),
                operation=f"update_conversation:{conversation_id}"
            )
            return True
        except Exception as e:
            self.logger.error(
                "Failed to update conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            return False

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
