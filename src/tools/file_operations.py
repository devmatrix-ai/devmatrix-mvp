"""
File Operations

Safe file operation utilities for Devmatrix agents.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class FileOperations:
    """
    Safe file operation utilities.

    Usage:
        file_ops = FileOperations(base_path="/path/to/workspace")
        content = file_ops.read_file("test.py")
        file_ops.write_file("output.txt", "Hello World")
    """

    def __init__(self, base_path: str):
        """
        Initialize file operations.

        Args:
            base_path: Base directory for operations
        """
        self.base_path = Path(base_path).resolve()
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, relative_path: str) -> Path:
        """
        Resolve relative path within base path.

        Args:
            relative_path: Relative path

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path escapes base directory
        """
        full_path = (self.base_path / relative_path).resolve()
        # Security check: ensure path is within base_path
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Path {relative_path} escapes base directory")
        return full_path

    def read_file(self, relative_path: str, encoding: str = "utf-8") -> str:
        """
        Read file content.

        Args:
            relative_path: Relative path to file
            encoding: Text encoding (default: utf-8)

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self._resolve_path(relative_path)
        return file_path.read_text(encoding=encoding)

    def write_file(
        self,
        relative_path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
    ) -> Path:
        """
        Write content to file.

        Args:
            relative_path: Relative path to file
            content: Content to write
            encoding: Text encoding (default: utf-8)
            create_dirs: Create parent directories if needed

        Returns:
            Path to written file
        """
        file_path = self._resolve_path(relative_path)

        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding=encoding)
        return file_path

    def append_file(
        self, relative_path: str, content: str, encoding: str = "utf-8"
    ) -> Path:
        """
        Append content to file.

        Args:
            relative_path: Relative path to file
            content: Content to append
            encoding: Text encoding

        Returns:
            Path to file
        """
        file_path = self._resolve_path(relative_path)

        with open(file_path, "a", encoding=encoding) as f:
            f.write(content)

        return file_path

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete file.

        Args:
            relative_path: Relative path to file

        Returns:
            True if deleted, False if not found
        """
        try:
            file_path = self._resolve_path(relative_path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    def file_exists(self, relative_path: str) -> bool:
        """
        Check if file exists.

        Args:
            relative_path: Relative path to file

        Returns:
            True if file exists
        """
        try:
            file_path = self._resolve_path(relative_path)
            return file_path.exists() and file_path.is_file()
        except ValueError:
            return False

    def list_files(
        self,
        relative_path: str = "",
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[str]:
        """
        List files in directory.

        Args:
            relative_path: Relative path to directory
            pattern: Glob pattern (default: *)
            recursive: Recursive search

        Returns:
            List of relative file paths
        """
        dir_path = self._resolve_path(relative_path) if relative_path else self.base_path

        if not dir_path.exists():
            return []

        glob_method = dir_path.rglob if recursive else dir_path.glob
        files = []

        for file_path in glob_method(pattern):
            if file_path.is_file():
                relative = file_path.relative_to(self.base_path)
                files.append(str(relative))

        return sorted(files)

    def list_dirs(self, relative_path: str = "") -> List[str]:
        """
        List directories.

        Args:
            relative_path: Relative path to directory

        Returns:
            List of relative directory paths
        """
        dir_path = self._resolve_path(relative_path) if relative_path else self.base_path

        if not dir_path.exists():
            return []

        dirs = []
        for item in dir_path.iterdir():
            if item.is_dir():
                relative = item.relative_to(self.base_path)
                dirs.append(str(relative))

        return sorted(dirs)

    def create_dir(self, relative_path: str) -> Path:
        """
        Create directory.

        Args:
            relative_path: Relative path to directory

        Returns:
            Path to created directory
        """
        dir_path = self._resolve_path(relative_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_file_info(self, relative_path: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            relative_path: Relative path to file

        Returns:
            Dictionary with file metadata
        """
        file_path = self._resolve_path(relative_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        stat = file_path.stat()

        return {
            "name": file_path.name,
            "path": str(relative_path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
            "extension": file_path.suffix,
        }

    def get_file_hash(self, relative_path: str, algorithm: str = "sha256") -> str:
        """
        Calculate file hash.

        Args:
            relative_path: Relative path to file
            algorithm: Hash algorithm (sha256, md5)

        Returns:
            Hexadecimal hash string
        """
        file_path = self._resolve_path(relative_path)

        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def copy_file(self, source: str, destination: str) -> Path:
        """
        Copy file within workspace.

        Args:
            source: Source relative path
            destination: Destination relative path

        Returns:
            Path to destination file
        """
        import shutil

        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)

        return dst_path

    def move_file(self, source: str, destination: str) -> Path:
        """
        Move file within workspace.

        Args:
            source: Source relative path
            destination: Destination relative path

        Returns:
            Path to destination file
        """
        import shutil

        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

        return dst_path

    def get_tree(self, relative_path: str = "", max_depth: int = 3) -> Dict[str, Any]:
        """
        Get directory tree structure.

        Args:
            relative_path: Relative path to directory
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary representing tree structure
        """
        dir_path = self._resolve_path(relative_path) if relative_path else self.base_path

        def _build_tree(path: Path, depth: int) -> Dict[str, Any]:
            if depth > max_depth:
                return {"name": path.name, "type": "truncated"}

            if path.is_file():
                return {
                    "name": path.name,
                    "type": "file",
                    "size": path.stat().st_size,
                }

            children = []
            try:
                for item in sorted(path.iterdir()):
                    children.append(_build_tree(item, depth + 1))
            except PermissionError:
                pass

            return {"name": path.name, "type": "directory", "children": children}

        return _build_tree(dir_path, 0)
