"""
Workspace Manager

Manages temporary isolated workspaces for Devmatrix operations.
Creates workspaces in /tmp/devmatrix-workspace-{timestamp}/
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


class WorkspaceManager:
    """
    Manages temporary workspaces for agent operations.

    Usage:
        with WorkspaceManager() as workspace:
            file_path = workspace.get_path("test.py")
            workspace.write_file("test.py", "print('hello')")
    """

    def __init__(self, workspace_id: str = None, auto_cleanup: bool = True):
        """
        Initialize workspace manager.

        Args:
            workspace_id: Optional workspace ID (generates timestamp if None)
            auto_cleanup: Whether to cleanup workspace on exit
        """
        self.workspace_id = workspace_id or self._generate_workspace_id()
        self.auto_cleanup = auto_cleanup
        self.base_path = Path(f"/tmp/devmatrix-workspace-{self.workspace_id}")
        self._created = False

    def _generate_workspace_id(self) -> str:
        """Generate unique workspace ID from timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def create(self) -> Path:
        """
        Create workspace directory.

        Returns:
            Path to workspace directory
        """
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._created = True
        return self.base_path

    def get_path(self, relative_path: str = "") -> Path:
        """
        Get absolute path within workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            Absolute path within workspace
        """
        if not self._created:
            self.create()

        if not relative_path:
            return self.base_path

        full_path = self.base_path / relative_path
        # Security: ensure path is within workspace
        full_path.resolve().relative_to(self.base_path.resolve())
        return full_path

    def write_file(self, relative_path: str, content: str) -> Path:
        """
        Write file to workspace.

        Args:
            relative_path: Relative path within workspace
            content: File content

        Returns:
            Path to created file
        """
        file_path = self.get_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def read_file(self, relative_path: str) -> str:
        """
        Read file from workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            File content
        """
        file_path = self.get_path(relative_path)
        return file_path.read_text(encoding="utf-8")

    def file_exists(self, relative_path: str) -> bool:
        """
        Check if file exists in workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            True if file exists
        """
        try:
            file_path = self.get_path(relative_path)
            return file_path.exists() and file_path.is_file()
        except ValueError:
            return False

    def dir_exists(self, relative_path: str) -> bool:
        """
        Check if directory exists in workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            True if directory exists
        """
        try:
            dir_path = self.get_path(relative_path)
            return dir_path.exists() and dir_path.is_dir()
        except ValueError:
            return False

    def list_files(self, relative_path: str = "", pattern: str = "*") -> list[Path]:
        """
        List files in workspace directory.

        Args:
            relative_path: Relative path within workspace
            pattern: Glob pattern (default: *)

        Returns:
            List of file paths relative to workspace
        """
        dir_path = self.get_path(relative_path)
        if not dir_path.exists():
            return []

        files = []
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                # Return path relative to workspace base
                relative = file_path.relative_to(self.base_path)
                files.append(relative)

        return sorted(files)

    def list_dirs(self, relative_path: str = "") -> list[Path]:
        """
        List directories in workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            List of directory paths relative to workspace
        """
        dir_path = self.get_path(relative_path)
        if not dir_path.exists():
            return []

        dirs = []
        for item in dir_path.iterdir():
            if item.is_dir():
                relative = item.relative_to(self.base_path)
                dirs.append(relative)

        return sorted(dirs)

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete file from workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            True if deleted, False if not found
        """
        try:
            file_path = self.get_path(relative_path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    def delete_dir(self, relative_path: str) -> bool:
        """
        Delete directory from workspace.

        Args:
            relative_path: Relative path within workspace

        Returns:
            True if deleted, False if not found
        """
        try:
            dir_path = self.get_path(relative_path)
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                return True
            return False
        except Exception:
            return False

    def cleanup(self) -> bool:
        """
        Remove entire workspace.

        Returns:
            True if cleaned up successfully
        """
        try:
            if self.base_path.exists():
                shutil.rmtree(self.base_path)
                self._created = False
                return True
            return False
        except Exception as e:
            print(f"Error cleaning up workspace: {e}")
            return False

    def get_size(self) -> int:
        """
        Get total size of workspace in bytes.

        Returns:
            Total size in bytes
        """
        total_size = 0
        if not self.base_path.exists():
            return 0

        for item in self.base_path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size

        return total_size

    def __enter__(self):
        """Context manager entry."""
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with optional cleanup."""
        if self.auto_cleanup:
            self.cleanup()

    def __str__(self) -> str:
        """String representation."""
        return f"Workspace({self.workspace_id}, path={self.base_path})"
