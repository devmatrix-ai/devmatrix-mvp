"""
Workspace Service

Manages file operations, project structure, and workspace metadata.
"""

import os
import shutil
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import aiofiles

from src.observability import StructuredLogger


class FileNode:
    """Represents a file or directory in the workspace."""

    def __init__(
        self,
        name: str,
        path: str,
        is_directory: bool,
        size: int = 0,
        modified_at: Optional[datetime] = None,
    ):
        self.name = name
        self.path = path
        self.is_directory = is_directory
        self.size = size
        self.modified_at = modified_at or datetime.now()
        self.children: List[FileNode] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "path": self.path,
            "is_directory": self.is_directory,
            "size": self.size,
            "modified_at": self.modified_at.isoformat(),
            "children": [child.to_dict() for child in self.children],
        }


class Workspace:
    """Workspace model with metadata and file structure."""

    def __init__(
        self,
        workspace_id: str,
        name: str,
        base_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.workspace_id = workspace_id
        self.name = name
        self.base_path = base_path
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert workspace to dictionary."""
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "path": str(self.base_path),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class WorkspaceService:
    """
    Service for managing workspaces and file operations.

    Provides safe file operations, directory traversal,
    and workspace lifecycle management.
    """

    def __init__(self, base_workspace_dir: str = "./workspace"):
        """
        Initialize workspace service.

        Args:
            base_workspace_dir: Base directory for all workspaces
        """
        self.logger = StructuredLogger("workspace_service")
        self.base_dir = Path(base_workspace_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces: Dict[str, Workspace] = {}

        # Load existing workspaces
        self._discover_workspaces()

    def _discover_workspaces(self) -> None:
        """Discover existing workspaces in base directory."""
        if not self.base_dir.exists():
            return

        for workspace_dir in self.base_dir.iterdir():
            if workspace_dir.is_dir():
                workspace_id = workspace_dir.name
                workspace = Workspace(
                    workspace_id=workspace_id,
                    name=workspace_id,
                    base_path=workspace_dir,
                )
                self.workspaces[workspace_id] = workspace

        self.logger.info(f"Discovered {len(self.workspaces)} existing workspaces")

    def create_workspace(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Workspace:
        """
        Create new workspace.

        Args:
            name: Workspace name
            metadata: Additional metadata

        Returns:
            Created workspace

        Raises:
            ValueError: If workspace creation fails
        """
        workspace_id = f"{name}_{uuid.uuid4().hex[:8]}"
        workspace_path = self.base_dir / workspace_id

        try:
            workspace_path.mkdir(parents=True, exist_ok=False)

            workspace = Workspace(
                workspace_id=workspace_id,
                name=name,
                base_path=workspace_path,
                metadata=metadata,
            )

            self.workspaces[workspace_id] = workspace

            self.logger.info(
                f"Created workspace {workspace_id}",
                extra={"path": str(workspace_path)}
            )

            return workspace

        except Exception as e:
            self.logger.error(f"Failed to create workspace: {e}")
            raise ValueError(f"Failed to create workspace: {e}")

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID."""
        return self.workspaces.get(workspace_id)

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all workspaces."""
        return [ws.to_dict() for ws in self.workspaces.values()]

    def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete workspace and all its contents.

        Args:
            workspace_id: Workspace to delete

        Returns:
            True if deleted, False if not found

        Raises:
            PermissionError: If deletion fails
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False

        try:
            shutil.rmtree(workspace.base_path)
            del self.workspaces[workspace_id]

            self.logger.info(f"Deleted workspace {workspace_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete workspace: {e}")
            raise PermissionError(f"Failed to delete workspace: {e}")

    def get_file_tree(self, workspace_id: str) -> Optional[FileNode]:
        """
        Get file tree for workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            Root file node or None if workspace not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return None

        return self._build_file_tree(workspace.base_path)

    def _build_file_tree(self, path: Path) -> FileNode:
        """Recursively build file tree."""
        stat = path.stat()
        node = FileNode(
            name=path.name,
            path=str(path.relative_to(self.base_dir)),
            is_directory=path.is_dir(),
            size=stat.st_size if path.is_file() else 0,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )

        if path.is_dir():
            try:
                for child_path in sorted(path.iterdir()):
                    # Skip hidden files and __pycache__
                    if child_path.name.startswith('.') or child_path.name == '__pycache__':
                        continue
                    node.children.append(self._build_file_tree(child_path))
            except PermissionError:
                pass

        return node

    async def read_file(self, workspace_id: str, file_path: str) -> Optional[str]:
        """
        Read file content.

        Args:
            workspace_id: Workspace ID
            file_path: Relative file path within workspace

        Returns:
            File content or None if not found

        Raises:
            ValueError: If path is invalid or outside workspace
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return None

        full_path = self._resolve_path(workspace, file_path)
        if not full_path or not full_path.is_file():
            return None

        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return None

    async def write_file(
        self,
        workspace_id: str,
        file_path: str,
        content: str,
    ) -> bool:
        """
        Write file content.

        Args:
            workspace_id: Workspace ID
            file_path: Relative file path within workspace
            content: File content

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If path is invalid or outside workspace
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False

        full_path = self._resolve_path(workspace, file_path, create_parents=True)
        if not full_path:
            return False

        try:
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            workspace.updated_at = datetime.now()
            self.logger.info(f"Wrote file {file_path} in workspace {workspace_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            return False

    async def delete_file(self, workspace_id: str, file_path: str) -> bool:
        """
        Delete file or directory.

        Args:
            workspace_id: Workspace ID
            file_path: Relative file path within workspace

        Returns:
            True if deleted, False otherwise
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False

        full_path = self._resolve_path(workspace, file_path)
        if not full_path or not full_path.exists():
            return False

        try:
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()

            workspace.updated_at = datetime.now()
            self.logger.info(f"Deleted {file_path} in workspace {workspace_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete {file_path}: {e}")
            return False

    def _resolve_path(
        self,
        workspace: Workspace,
        file_path: str,
        create_parents: bool = False,
    ) -> Optional[Path]:
        """
        Resolve and validate file path within workspace.

        Args:
            workspace: Workspace instance
            file_path: Relative file path
            create_parents: Create parent directories if they don't exist

        Returns:
            Resolved path or None if invalid

        Raises:
            ValueError: If path is outside workspace
        """
        try:
            # Remove leading slash if present
            file_path = file_path.lstrip('/')

            # Resolve full path
            full_path = (workspace.base_path / file_path).resolve()

            # Security check: ensure path is within workspace
            if not str(full_path).startswith(str(workspace.base_path)):
                raise ValueError(f"Path {file_path} is outside workspace")

            # Create parent directories if requested
            if create_parents and not full_path.parent.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)

            return full_path

        except Exception as e:
            self.logger.error(f"Invalid path {file_path}: {e}")
            return None

    def get_workspace_stats(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workspace statistics.

        Args:
            workspace_id: Workspace ID

        Returns:
            Statistics dictionary or None if workspace not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return None

        total_size = 0
        file_count = 0
        dir_count = 0

        def walk_directory(path: Path):
            nonlocal total_size, file_count, dir_count

            if not path.exists():
                return

            for item in path.iterdir():
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
                    walk_directory(item)

        walk_directory(workspace.base_path)

        return {
            "workspace_id": workspace_id,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "directory_count": dir_count,
        }
