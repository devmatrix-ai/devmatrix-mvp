"""
MasterPlan Execution Service

Orchestrates masterplan execution with workspace creation, task execution,
and database persistence.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.masterplan import MasterPlan, MasterPlanStatus
from src.services.workspace_service import WorkspaceService
from src.observability import StructuredLogger


class MasterplanExecutionService:
    """
    Service for executing masterplans.

    Responsibilities:
    - Create workspace for masterplan execution
    - Store workspace_path in database
    - Coordinate task execution with OrchestratorAgent
    - Update masterplan and task status during execution
    - Emit WebSocket events for real-time monitoring
    """

    def __init__(self, db_session: Session, workspace_base_dir: str = "./workspace"):
        """
        Initialize execution service.

        Args:
            db_session: SQLAlchemy database session
            workspace_base_dir: Base directory for workspace creation
        """
        self.db = db_session
        self.logger = StructuredLogger("masterplan_execution")
        self.workspace_service = WorkspaceService(base_workspace_dir=workspace_base_dir)

    def create_workspace(self, masterplan_id: UUID) -> str:
        """
        Create workspace for masterplan execution and store path in database.

        Args:
            masterplan_id: UUID of the masterplan

        Returns:
            Absolute path to created workspace

        Raises:
            ValueError: If masterplan not found or workspace creation fails
        """
        # Load masterplan from database
        masterplan = self.db.query(MasterPlan).filter_by(masterplan_id=masterplan_id).first()

        if not masterplan:
            self.logger.error("Masterplan not found", masterplan_id=str(masterplan_id))
            raise ValueError(f"Masterplan {masterplan_id} not found")

        try:
            # Create workspace using WorkspaceService
            workspace_name = f"masterplan_{masterplan.project_name}".replace(" ", "_").lower()
            workspace = self.workspace_service.create_workspace(
                name=workspace_name,
                metadata={
                    "masterplan_id": str(masterplan_id),
                    "project_name": masterplan.project_name,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

            # Store workspace_path in masterplans table
            workspace_path = str(workspace.base_path.absolute())
            masterplan.workspace_path = workspace_path
            self.db.commit()

            self.logger.info(
                "Workspace created for masterplan",
                masterplan_id=str(masterplan_id),
                workspace_path=workspace_path,
                workspace_id=workspace.workspace_id,
            )

            return workspace_path

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "Failed to create workspace",
                masterplan_id=str(masterplan_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ValueError(f"Failed to create workspace: {e}")

    def get_workspace_path(self, masterplan_id: UUID) -> Optional[str]:
        """
        Get workspace path for masterplan.

        Args:
            masterplan_id: UUID of the masterplan

        Returns:
            Workspace path if set, None otherwise
        """
        masterplan = self.db.query(MasterPlan).filter_by(masterplan_id=masterplan_id).first()

        if not masterplan:
            return None

        return masterplan.workspace_path

    def update_masterplan_status(
        self, masterplan_id: UUID, status: MasterPlanStatus
    ) -> bool:
        """
        Update masterplan execution status.

        Args:
            masterplan_id: UUID of the masterplan
            status: New status

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            masterplan = self.db.query(MasterPlan).filter_by(masterplan_id=masterplan_id).first()

            if not masterplan:
                self.logger.error("Masterplan not found", masterplan_id=str(masterplan_id))
                return False

            masterplan.status = status
            masterplan.updated_at = datetime.utcnow()

            # Set started_at or completed_at based on status
            if status == MasterPlanStatus.IN_PROGRESS and not masterplan.started_at:
                masterplan.started_at = datetime.utcnow()
            elif status == MasterPlanStatus.COMPLETED and not masterplan.completed_at:
                masterplan.completed_at = datetime.utcnow()

            self.db.commit()

            self.logger.info(
                "Masterplan status updated",
                masterplan_id=str(masterplan_id),
                old_status=masterplan.status.value if hasattr(masterplan.status, 'value') else str(masterplan.status),
                new_status=status.value,
            )

            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "Failed to update masterplan status",
                masterplan_id=str(masterplan_id),
                status=status.value,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
