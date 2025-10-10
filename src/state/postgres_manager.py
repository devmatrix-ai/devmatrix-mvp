"""
PostgreSQL State Manager

Manages persistent state in PostgreSQL for audit trails, analytics, and learning.
Stores: projects, tasks, decisions, git commits, cost tracking.
"""

import os
from typing import Any, Optional
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

    def _execute(self, query: str, params: tuple = None, fetch: bool = False) -> Any:
        """
        Execute SQL query with error handling.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            Query results if fetch=True, None otherwise
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)

                if fetch:
                    return cursor.fetchall()

                self.conn.commit()
                return None

        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"Database error: {e}")
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

        result = self._execute(query, (name, description), fetch=True)
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

        results = self._execute(query, (str(project_id),), fetch=True)
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
            query, (str(project_id), agent_name, task_type, input_text, Json({})), fetch=True
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
            )
            return True

        except Exception as e:
            print(f"Error updating task status: {e}")
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

        results = self._execute(query, (str(task_id),), fetch=True)
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

        return self._execute(query, (str(project_id),), fetch=True)

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

        results = self._execute(query, (str(project_id),), fetch=True)
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

        results = self._execute(query, (year, month), fetch=True)

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
        )
        return result[0]["id"]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
